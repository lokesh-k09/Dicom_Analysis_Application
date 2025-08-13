# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_app\\desktop_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('desktop_app/gui_app.py', 'desktop_app')],
    hiddenimports=['gui_app'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['desktop_app/rthook_dat_gui.py'],
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
    name='MRI_DICOM_Analysis',
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
)
