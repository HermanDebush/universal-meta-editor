"""
Read and write filesystem timestamps (the "File" section in Windows properties).

These are separate from the XML metadata inside the docx/xlsx/pptx archive:
  - fs_created  → "Дата создания"   (st_ctime on Windows)
  - fs_modified → "Дата изменения"  (st_mtime)
  - fs_accessed → "Дата доступа"    (st_atime)

Windows: uses ctypes → kernel32.SetFileTime  (no extra dependencies)
Linux / macOS: only mtime + atime are settable via os.utime
"""

import ctypes
import ctypes.wintypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── ISO helpers ───────────────────────────────────────────────────────────────

def _iso_to_dt(iso: str) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _ts_to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Read ──────────────────────────────────────────────────────────────────────

def read_file_times(path: Path) -> dict[str, str]:
    """Return filesystem timestamps as ISO-8601 UTC strings."""
    stat = os.stat(path)
    return {
        "fs_created":  _ts_to_iso(stat.st_ctime),   # creation time on Windows
        "fs_modified": _ts_to_iso(stat.st_mtime),
        "fs_accessed": _ts_to_iso(stat.st_atime),
    }


# ── Write ─────────────────────────────────────────────────────────────────────

def write_file_times(
    path: Path,
    created:  str = "",
    modified: str = "",
    accessed: str = "",
) -> None:
    """Apply filesystem timestamps to *path*. Empty strings leave that field unchanged."""
    if sys.platform == "win32":
        _write_windows(path, created, modified, accessed)
    else:
        _write_posix(path, modified, accessed)


# ── Windows implementation ────────────────────────────────────────────────────

# 100-nanosecond intervals between 1601-01-01 and 1970-01-01
_EPOCH_DIFF = 116_444_736_000_000_000


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime",  ctypes.c_ulong),
        ("dwHighDateTime", ctypes.c_ulong),
    ]


def _dt_to_ft(iso: str) -> "_FILETIME | None":
    dt = _iso_to_dt(iso)
    if dt is None:
        return None
    ticks = int(dt.timestamp() * 10_000_000) + _EPOCH_DIFF
    ft = _FILETIME()
    ft.dwLowDateTime  =  ticks        & 0xFFFFFFFF
    ft.dwHighDateTime = (ticks >> 32) & 0xFFFFFFFF
    return ft


def _write_windows(path: Path, created: str, modified: str, accessed: str) -> None:
    GENERIC_WRITE       = 0x40000000
    FILE_SHARE_READ     = 0x00000001
    OPEN_EXISTING       = 3
    FILE_ATTRIBUTE_NORMAL = 0x00000080
    INVALID_HANDLE      = ctypes.c_void_p(-1).value

    handle = ctypes.windll.kernel32.CreateFileW(
        str(path),
        GENERIC_WRITE,
        FILE_SHARE_READ,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE:
        raise OSError(f"Cannot open file for timestamp writing: {path}")

    try:
        ft_c = _dt_to_ft(created)
        ft_m = _dt_to_ft(modified)
        ft_a = _dt_to_ft(accessed)

        # SetFileTime(hFile, lpCreationTime, lpLastAccessTime, lpLastWriteTime)
        ok = ctypes.windll.kernel32.SetFileTime(
            handle,
            ctypes.byref(ft_c) if ft_c else None,
            ctypes.byref(ft_a) if ft_a else None,
            ctypes.byref(ft_m) if ft_m else None,
        )
        if not ok:
            err = ctypes.windll.kernel32.GetLastError()
            raise OSError(f"SetFileTime failed (error {err})")
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


# ── POSIX fallback ────────────────────────────────────────────────────────────

def _write_posix(path: Path, modified: str, accessed: str) -> None:
    """On Linux/macOS only mtime and atime are freely settable."""
    dt_m = _iso_to_dt(modified)
    dt_a = _iso_to_dt(accessed)
    if dt_m or dt_a:
        stat = os.stat(path)
        m = dt_m.timestamp() if dt_m else stat.st_mtime
        a = dt_a.timestamp() if dt_a else stat.st_atime
        os.utime(path, (a, m))
