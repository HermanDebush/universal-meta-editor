# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Universal Meta Editor.

Build:
    pyinstaller UniversalMeta.spec --clean
    (or run build.bat)
"""

from PyInstaller.utils.hooks import collect_all

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=ctk_binaries,
    datas=ctk_datas + [("assets", "assets")],   # include icon + any future assets
    hiddenimports=ctk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "email", "http",
              "urllib", "xmlrpc", "pydoc"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="UniversalMetaEditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets\\icon.ico",
)
