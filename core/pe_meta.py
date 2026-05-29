"""
Windows PE (EXE/DLL/SYS) metadata — read and write VERSIONINFO string table.
Windows only; uses ctypes → version.dll / kernel32.dll. No extra dependencies.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

_IS_WIN = sys.platform == "win32"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class PEMeta:
    file_description:  str = ""
    file_version:      str = ""
    product_name:      str = ""
    product_version:   str = ""
    company_name:      str = ""
    legal_copyright:   str = ""
    original_filename: str = ""
    internal_name:     str = ""
    comments:          str = ""


# VERSIONINFO string key → PEMeta field name
_PE_FIELDS: dict[str, str] = {
    "FileDescription":  "file_description",
    "FileVersion":      "file_version",
    "ProductName":      "product_name",
    "ProductVersion":   "product_version",
    "CompanyName":      "company_name",
    "LegalCopyright":   "legal_copyright",
    "OriginalFilename": "original_filename",
    "InternalName":     "internal_name",
    "Comments":         "comments",
}


# ── Detection ─────────────────────────────────────────────────────────────────

def is_pe_file(path: Path) -> bool:
    """True if the file starts with the MZ magic bytes (Windows PE executable)."""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"MZ"
    except OSError:
        return False


# ── Reader ────────────────────────────────────────────────────────────────────

def read_pe_meta(path: str | Path) -> PEMeta:
    """
    Read the VERSIONINFO string table from a Windows PE file.
    Returns an empty PEMeta on failure or on non-Windows platforms.
    """
    if not _IS_WIN:
        return PEMeta()

    path_str = str(path)
    ver = ctypes.windll.version

    sz = ver.GetFileVersionInfoSizeW(path_str, None)
    if not sz:
        return PEMeta()

    buf = ctypes.create_string_buffer(sz)
    if not ver.GetFileVersionInfoW(path_str, 0, sz, buf):
        return PEMeta()

    def query(name: str) -> str:
        p, n = ctypes.c_void_p(), ctypes.c_uint()
        for lc in ("040904B0", "040904E4", "000004B0", "080404B0", "040C04B0"):
            try:
                sub = f"\\StringFileInfo\\{lc}\\{name}"
                if ver.VerQueryValueW(buf, sub, ctypes.byref(p), ctypes.byref(n)) and n.value:
                    return ctypes.wstring_at(p.value, n.value).rstrip("\x00").strip()
            except Exception:
                pass
        return ""

    return PEMeta(**{field: query(key) for key, field in _PE_FIELDS.items()})


# ── VERSIONINFO binary builder ────────────────────────────────────────────────

def _wstr(s: str) -> bytes:
    return (s + "\x00").encode("utf-16-le")


def _pad4(data: bytes) -> bytes:
    r = len(data) % 4
    return data + bytes((4 - r) % 4)


def _hdr(body: bytes, val_len: int, typ: int) -> bytes:
    return struct.pack("<HHH", 6 + len(body), val_len, typ) + body


def _pack_string(name: str, value: str) -> bytes:
    nb  = _wstr(name)
    vb  = _wstr(value)
    pad = bytes((4 - (6 + len(nb)) % 4) % 4)
    return _hdr(nb + pad + vb, len(value) + 1, 1)


def _pack_string_table(strings: dict[str, str]) -> bytes:
    kb  = _wstr("040904B0")
    pad = bytes((4 - (6 + len(kb)) % 4) % 4)
    children = b"".join(_pad4(_pack_string(k, v)) for k, v in strings.items())
    return _hdr(kb + pad + children, 0, 1)


def _pack_sfi(strings: dict[str, str]) -> bytes:
    kb  = _wstr("StringFileInfo")
    pad = bytes((4 - (6 + len(kb)) % 4) % 4)
    return _hdr(kb + pad + _pad4(_pack_string_table(strings)), 0, 1)


def _pack_vfi() -> bytes:
    kb  = _wstr("VarFileInfo")
    pad = bytes((4 - (6 + len(kb)) % 4) % 4)
    tk_ = _wstr("Translation")
    tp  = bytes((4 - (6 + len(tk_)) % 4) % 4)
    tv  = struct.pack("<I", 0x04B00409)   # English US + Unicode
    tvar = _pad4(_hdr(tk_ + tp + tv, 4, 0))
    return _hdr(kb + pad + tvar, 0, 1)


def _default_fixed_info() -> bytes:
    """Minimal valid VS_FIXEDFILEINFO (52 bytes, version 0.0.0.0)."""
    return struct.pack(
        "<13I",
        0xFEEF04BD,   # dwSignature
        0x00010000,   # dwStrucVersion
        0x00000000,   # dwFileVersionMS
        0x00000000,   # dwFileVersionLS
        0x00000000,   # dwProductVersionMS
        0x00000000,   # dwProductVersionLS
        0x0000003F,   # dwFileFlagsMask
        0x00000000,   # dwFileFlags
        0x00040004,   # dwFileOS (VOS_NT_WINDOWS32)
        0x00000001,   # dwFileType (VFT_APP)
        0x00000000,   # dwFileSubtype
        0x00000000,   # dwFileDateMS
        0x00000000,   # dwFileDateLS
    )


def _read_fixed_info(path: str | Path) -> bytes:
    """Read VS_FIXEDFILEINFO from a PE file; returns a valid default on failure."""
    if not _IS_WIN:
        return _default_fixed_info()
    ver = ctypes.windll.version
    sz  = ver.GetFileVersionInfoSizeW(str(path), None)
    if sz:
        buf = ctypes.create_string_buffer(sz)
        if ver.GetFileVersionInfoW(str(path), 0, sz, buf):
            p, n = ctypes.c_void_p(), ctypes.c_uint()
            if ver.VerQueryValueW(buf, "\\", ctypes.byref(p), ctypes.byref(n)) and n.value >= 52:
                return bytes((ctypes.c_char * 52).from_address(p.value))
    return _default_fixed_info()


def _build_versioninfo(strings: dict[str, str], fixed: bytes) -> bytes:
    kb  = _wstr("VS_VERSION_INFO")
    pad = bytes((4 - (6 + len(kb)) % 4) % 4)
    body = kb + pad + fixed + _pad4(_pack_sfi(strings)) + _pad4(_pack_vfi())
    return _hdr(body, len(fixed), 0)


# ── Low-level resource patcher (in-place, no file copy) ──────────────────────

def patch_pe_resource(path: Path, rt_type: int, name_id: int, data: bytes) -> None:
    """
    Update a single PE resource in *path* in-place (no file copy).
    rt_type: resource type  (e.g. 16 = RT_VERSION, 24 = RT_MANIFEST)
    name_id: resource name  (integer, e.g. 1)
    Raises OSError on failure.
    """
    if not _IS_WIN:
        raise OSError("Редактирование PE-ресурсов поддерживается только на Windows")

    k32 = ctypes.windll.kernel32
    k32.BeginUpdateResourceW.restype  = ctypes.wintypes.HANDLE
    k32.BeginUpdateResourceW.argtypes = [ctypes.c_wchar_p, ctypes.wintypes.BOOL]
    k32.UpdateResourceW.restype  = ctypes.wintypes.BOOL
    k32.UpdateResourceW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.c_void_p, ctypes.c_void_p,
        ctypes.wintypes.WORD,
        ctypes.c_void_p, ctypes.wintypes.DWORD,
    ]
    k32.EndUpdateResourceW.restype  = ctypes.wintypes.BOOL
    k32.EndUpdateResourceW.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.BOOL]

    h = k32.BeginUpdateResourceW(str(path), False)
    if not h:
        raise OSError(f"BeginUpdateResource не удался (ошибка {k32.GetLastError()})")

    buf = (ctypes.c_char * len(data))(*data)
    ok  = bool(k32.UpdateResourceW(h, rt_type, name_id, 0, buf, len(data)))
    if not bool(k32.EndUpdateResourceW(h, not ok)):
        raise OSError("EndUpdateResource не удался")
    if not ok:
        raise OSError(f"UpdateResource не удался (ошибка {k32.GetLastError()})")


# ── Writer ────────────────────────────────────────────────────────────────────

def write_pe_meta(source: str | Path, dest: str | Path, meta: PEMeta) -> Path:
    """
    Copy *source* to *dest*, then update its VERSIONINFO string table.
    Original file is never modified. Returns the path to the new file.
    Raises OSError on Windows API failure.
    """
    if not _IS_WIN:
        raise OSError("Запись метаданных PE поддерживается только на Windows")

    src, dst = Path(source), Path(dest)
    shutil.copy2(src, dst)

    strings = {
        key: getattr(meta, field)
        for key, field in _PE_FIELDS.items()
        if getattr(meta, field)
    }
    if not strings:
        return dst  # nothing to update — copy is enough

    fixed    = _read_fixed_info(src)
    new_data = _build_versioninfo(strings, fixed)

    try:
        patch_pe_resource(dst, 16, 1, new_data)   # RT_VERSION = 16
    except OSError:
        dst.unlink(missing_ok=True)
        raise

    return dst


# ── Manifest reader / writer ──────────────────────────────────────────────────

def read_pe_manifest(path: str | Path) -> str:
    """
    Extract the embedded application manifest (RT_MANIFEST=24, id=1) from a PE file.
    Returns the XML string, or "" if not found / not Windows.
    """
    if not _IS_WIN:
        return ""

    LOAD_LIBRARY_AS_DATAFILE = 0x00000002
    k32 = ctypes.windll.kernel32
    k32.LoadLibraryExW.restype  = ctypes.wintypes.HMODULE
    k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    k32.FindResourceW.restype   = ctypes.c_void_p
    k32.FindResourceW.argtypes  = [ctypes.wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p]
    k32.LoadResource.restype    = ctypes.c_void_p
    k32.LoadResource.argtypes   = [ctypes.wintypes.HMODULE, ctypes.c_void_p]
    k32.LockResource.restype    = ctypes.c_void_p
    k32.LockResource.argtypes   = [ctypes.c_void_p]
    k32.SizeofResource.restype  = ctypes.wintypes.DWORD
    k32.SizeofResource.argtypes = [ctypes.wintypes.HMODULE, ctypes.c_void_p]
    k32.FreeLibrary.restype     = ctypes.wintypes.BOOL
    k32.FreeLibrary.argtypes    = [ctypes.wintypes.HMODULE]

    h = k32.LoadLibraryExW(str(path), None, LOAD_LIBRARY_AS_DATAFILE)
    if not h:
        return ""
    try:
        res  = k32.FindResourceW(h, 1, 24)   # MAKEINTRESOURCE(1), RT_MANIFEST=24
        if not res:
            return ""
        hres = k32.LoadResource(h, res)
        if not hres:
            return ""
        ptr  = k32.LockResource(hres)
        size = k32.SizeofResource(h, res)
        if not ptr or not size:
            return ""
        data = bytes((ctypes.c_char * size).from_address(ptr))
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return data.decode(enc)
            except Exception:
                pass
        return ""
    finally:
        k32.FreeLibrary(h)


def write_pe_manifest(source: str | Path, dest: str | Path, manifest_xml: str) -> Path:
    """
    Copy *source* to *dest*, then write *manifest_xml* as the embedded manifest
    (RT_MANIFEST=24, id=1). Returns the path to the new file.
    """
    if not _IS_WIN:
        raise OSError("Запись манифеста PE поддерживается только на Windows")

    src, dst = Path(source), Path(dest)
    shutil.copy2(src, dst)

    try:
        patch_pe_resource(dst, 24, 1, manifest_xml.encode("utf-8"))
    except OSError:
        dst.unlink(missing_ok=True)
        raise

    return dst
