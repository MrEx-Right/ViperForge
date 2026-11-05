# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — windowed, single-file Windows build of the ViperForge GUI.
#   pip install pyinstaller
#   pyinstaller ViperForge.spec      →  dist/ViperForge.exe
#
# Templates and assets are bundled at the archive root so the
# Path(__file__)-relative lookups in engine.py / compiler.py / main_window.py
# resolve the same way they do when running from source.

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("assets/images", "assets/images"),
    ("templates/exploits", "templates/exploits"),
    ("templates/payloads", "templates/payloads"),
]
datas += collect_data_files("qtawesome")

a = Analysis(
    ["viperforge.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ViperForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["assets/images/logo.ico"],
)
