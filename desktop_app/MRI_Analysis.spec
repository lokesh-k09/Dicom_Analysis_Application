# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['desktop_app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Copy desktop_backend.py to bundle root
        ('desktop_app/desktop_backend.py', '.'),

        # Keep other modules in their folder
        ('desktop_app/desktop_gui.py', 'desktop_app'),
        ('desktop_app/gui_app.py', 'desktop_app'),
        ('desktop_app/outputs/*', 'desktop_app/outputs'),
        ('desktop_app/uploads/*', 'desktop_app/uploads'),
        ('desktop_app/twixtools/*', 'desktop_app/twixtools'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MRI_Analysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True  # Keep console visible until we confirm it's working
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='MRI_Analysis'
)
