# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller onedir specification for aura.exe (Management CLI).
"""

import sys
from pathlib import Path

block_cipher = None

workspace_root = Path(SPECPATH).parent.resolve()

a = Analysis(
    [str(workspace_root / "aura" / "entrypoints" / "cli_main.py")],
    pathex=[str(workspace_root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "streamlit"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="aura",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Interactive console utility
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="aura-cli",
)
