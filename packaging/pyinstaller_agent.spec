# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller onedir specification for aura-agent.exe (Background Daemon).
"""

import sys
from pathlib import Path

block_cipher = None

workspace_root = Path(SPECPATH).parent.resolve()

added_files = [
    (str(workspace_root / "web"), "web"),
    (str(workspace_root / "data" / "baseline.csv"), "data"),
]

a = Analysis(
    [str(workspace_root / "aura" / "entrypoints" / "agent_main.py")],
    pathex=[str(workspace_root)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "sklearn.utils._typedefs",
        "sklearn.neighbors._typedefs",
    ],
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
    name="aura-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Headless background execution (no console window)
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
    name="aura-agent",
)
