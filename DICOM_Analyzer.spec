# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_app\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('desktop_app\\uploads', 'uploads'), ('desktop_app\\outputs', 'outputs')],
    hiddenimports=['flet', 'flet.core', 'flet_desktop', 'fastapi', 'uvicorn', 'multipart'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas.tests', 'numpy.tests', 'scipy.tests', 'skimage.tests', 'skimage.data.tests'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DICOM_Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DICOM_Analyzer',
)
