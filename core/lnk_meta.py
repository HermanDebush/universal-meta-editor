"""
Windows shortcut (.lnk) metadata — read via binary [MS-SHLLINK] parser,
write via WScript.Shell COM through PowerShell.
Reading is done purely in Python to avoid WScript.Shell ANSI/Unicode encoding bugs.
Windows only. No extra dependencies.
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_IS_WIN = sys.platform == "win32"

_TIMEOUT = 12  # seconds for PowerShell calls


@dataclass
class LnkMeta:
    target_path:   str = ""   # Объект — путь к программе/файлу
    arguments:     str = ""   # Аргументы командной строки
    working_dir:   str = ""   # Рабочая папка
    description:   str = ""   # Комментарий (всплывающая подсказка)
    icon_location: str = ""   # Значок в формате "путь,индекс"
    window_style:  int = 1    # 1 = обычное, 3 = развёрнутое, 7 = свёрнутое


# Window style int → i18n key (label resolved at display time)
WINDOW_STYLE_ORDER: list[int] = [1, 3, 7]
WINDOW_STYLE_KEYS: dict[int, str] = {
    1: "ws.normal",     # обычное
    3: "ws.maximized",  # развёрнутое
    7: "ws.minimized",  # свёрнутое
}


def is_lnk_file(path: Path) -> bool:
    """True if the file is a Windows shortcut (starts with LNK magic bytes)."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x4C\x00\x00\x00"
    except OSError:
        return False


# ── Binary [MS-SHLLINK] reader ────────────────────────────────────────────────

# LinkFlags bit positions
_FL_HAS_ID_LIST      = 1 << 0
_FL_HAS_LINK_INFO    = 1 << 1
_FL_HAS_NAME         = 1 << 2
_FL_HAS_REL_PATH     = 1 << 3
_FL_HAS_WORKING_DIR  = 1 << 4
_FL_HAS_ARGUMENTS    = 1 << 5
_FL_HAS_ICON         = 1 << 6
_FL_IS_UNICODE       = 1 << 7


def _read_counted_string(data: bytes, pos: int, unicode: bool) -> tuple[str, int]:
    """Read a CountCharacters-prefixed string from StringData. Returns (string, new_pos)."""
    count = struct.unpack_from("<H", data, pos)[0]
    pos += 2
    if unicode:
        raw = data[pos: pos + count * 2]
        text = raw.decode("utf-16-le", errors="replace")
        pos += count * 2
    else:
        raw = data[pos: pos + count]
        text = raw.decode("mbcs", errors="replace")
        pos += count
    return text, pos


def _parse_lnk_binary(data: bytes) -> LnkMeta:
    """Parse .lnk binary according to [MS-SHLLINK] spec."""
    if len(data) < 76 or data[:4] != b"\x4C\x00\x00\x00":
        return LnkMeta()

    link_flags   = struct.unpack_from("<I", data, 20)[0]
    show_command = struct.unpack_from("<I", data, 60)[0]

    window_style = show_command if show_command in WINDOW_STYLE_KEYS else 1
    unicode      = bool(link_flags & _FL_IS_UNICODE)

    pos = 76  # skip fixed header

    # Skip IDList if present
    if link_flags & _FL_HAS_ID_LIST:
        id_list_size = struct.unpack_from("<H", data, pos)[0]
        pos += 2 + id_list_size

    # Parse LinkInfo for TargetPath
    target_path = ""
    if link_flags & _FL_HAS_LINK_INFO:
        link_info_size   = struct.unpack_from("<I", data, pos)[0]
        li_header_size   = struct.unpack_from("<I", data, pos + 4)[0]
        li_flags         = struct.unpack_from("<I", data, pos + 8)[0]
        local_base_off   = struct.unpack_from("<I", data, pos + 16)[0]

        if li_header_size >= 0x24 and (li_flags & 1):
            # Prefer Unicode LocalBasePath
            unicode_base_off = struct.unpack_from("<I", data, pos + 28)[0]
            raw = data[pos + unicode_base_off:]
            end = raw.find(b"\x00\x00")
            # align to even boundary for proper UTF-16 LE terminator
            if end % 2 != 0:
                end = raw.find(b"\x00\x00", end + 1)
            target_path = raw[:end].decode("utf-16-le", errors="replace") if end >= 0 else ""
        elif li_flags & 1:
            raw = data[pos + local_base_off:]
            end = raw.find(b"\x00")
            target_path = raw[:end].decode("mbcs", errors="replace") if end >= 0 else ""

        pos += link_info_size

    # Parse StringData in fixed order
    description   = ""
    working_dir   = ""
    arguments     = ""
    icon_location = ""

    if link_flags & _FL_HAS_NAME:
        description, pos = _read_counted_string(data, pos, unicode)

    if link_flags & _FL_HAS_REL_PATH:
        _, pos = _read_counted_string(data, pos, unicode)  # skip RelativePath

    if link_flags & _FL_HAS_WORKING_DIR:
        working_dir, pos = _read_counted_string(data, pos, unicode)

    if link_flags & _FL_HAS_ARGUMENTS:
        arguments, pos = _read_counted_string(data, pos, unicode)

    if link_flags & _FL_HAS_ICON:
        icon_location, pos = _read_counted_string(data, pos, unicode)

    return LnkMeta(
        target_path   = target_path,
        arguments     = arguments,
        working_dir   = working_dir,
        description   = description,
        icon_location = icon_location,
        window_style  = window_style,
    )


# ── Reader ────────────────────────────────────────────────────────────────────

def read_lnk_meta(path: str | Path) -> LnkMeta:
    try:
        data = Path(path).read_bytes()
        return _parse_lnk_binary(data)
    except Exception:
        return LnkMeta()


# ── PowerShell writer ─────────────────────────────────────────────────────────

_WRITE_SCRIPT = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
try {
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK_DST)
    $s.TargetPath       = $env:LNK_TARGET
    $s.Arguments        = $env:LNK_ARGS
    $s.WorkingDirectory = $env:LNK_WORKDIR
    $s.Description      = $env:LNK_DESC
    $s.WindowStyle      = [int]$env:LNK_WINSTYLE
    if ($env:LNK_ICON) { $s.IconLocation = $env:LNK_ICON }
    $s.Save()
    Write-Output "OK"
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
"""


def _ps(script: str, extra_env: dict[str, str]) -> tuple[str, str, int]:
    env = os.environ.copy()
    env.update(extra_env)
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", timeout=_TIMEOUT, env=env,
    )
    return r.stdout, r.stderr, r.returncode


def write_lnk_meta(source: str | Path, dest: str | Path, meta: LnkMeta) -> Path:
    """
    Copy *source* to *dest*, then update shortcut properties via WScript.Shell.
    Original file is never modified. Returns path to the new file.
    """
    if not _IS_WIN:
        raise OSError("Создание ярлыков поддерживается только на Windows")

    src, dst = Path(source), Path(dest)
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)

    _, stderr, rc = _ps(_WRITE_SCRIPT, {
        "LNK_DST":      str(dst),
        "LNK_TARGET":   meta.target_path,
        "LNK_ARGS":     meta.arguments,
        "LNK_WORKDIR":  meta.working_dir,
        "LNK_DESC":     meta.description,
        "LNK_ICON":     meta.icon_location,
        "LNK_WINSTYLE": str(meta.window_style or 1),
    })
    if rc != 0:
        dst.unlink(missing_ok=True)
        raise OSError(stderr.strip() or "PowerShell завершился с ошибкой")

    return dst
