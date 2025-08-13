# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_app\\desktop_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('desktop_app\\gui_app.py', '.')],
    hiddenimports=['desktop_backend', 'multipart'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='MRI DICOM Analysis',
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
    version='C:\\Users\\lokes\\AppData\\Local\\Temp\\3506392c-60cf-4e9c-99a8-c6e98564dfac',
)
