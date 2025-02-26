# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[('C:\\Program Files\\vJoy\\x64\\vJoyInterface.dll', '.')],
    datas=[('trackpro', 'trackpro'), ('trackpro.manifest', '.')],
    hiddenimports=['trackpro', 'trackpro.main', 'trackpro.ui', 'trackpro.hardware_input', 'trackpro.output', 'trackpro.hidhide', 'PyQt5.QtChart', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'pygame', 'win32serviceutil', 'win32service'],
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
    name='TrackPro_v1.0.1',
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
    uac_admin=True,
    manifest='trackpro.manifest',
)
