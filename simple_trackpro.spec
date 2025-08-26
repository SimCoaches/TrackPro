# -*- mode: python ; coding: utf-8 -*-
import os
import re
import site

def _read_version():
    try:
        with open(os.path.join('trackpro', '__init__.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return '1.0.0'

TP_VERSION = _read_version()

# Get PyQt6 installation path
pyqt6_path = None
for path in site.getsitepackages():
    qt6_path = os.path.join(path, 'PyQt6', 'Qt6')
    if os.path.exists(qt6_path):
        pyqt6_path = qt6_path
        break

# Build binaries list
binaries_list = []

# Add Qt WebEngine Process and DLLs - CRITICAL for web functionality
if pyqt6_path:
    qt_bin_path = os.path.join(pyqt6_path, 'bin')
    
    # Essential Qt WebEngine binaries only
    webengine_files = [
        'QtWebEngineProcess.exe',
        'Qt6WebEngineCore.dll',
        'Qt6WebEngineWidgets.dll',
    ]
    
    for webengine_file in webengine_files:
        webengine_path = os.path.join(qt_bin_path, webengine_file)
        if os.path.exists(webengine_path):
            binaries_list.append((webengine_path, '.'))
            # print(f"Found Qt WebEngine file: {webengine_file}")
        else:
            pass
            # print(f"WARNING: Missing Qt WebEngine file: {webengine_file}")

    # Include OpenSSL DLLs required by QtNetwork/TLS on some systems
    openssl_candidates = [
        'libssl-3-x64.dll', 'libcrypto-3-x64.dll',
        'libssl-3.dll', 'libcrypto-3.dll'
    ]
    for dll_name in openssl_candidates:
        dll_path = os.path.join(qt_bin_path, dll_name)
        if os.path.exists(dll_path):
            binaries_list.append((dll_path, '.'))

    # Include software OpenGL and D3D compiler for broader GPU compatibility
    angle_candidates = [
        'opengl32sw.dll',
        'D3Dcompiler_47.dll',
    ]
    for dll_name in angle_candidates:
        dll_path = os.path.join(qt_bin_path, dll_name)
        if os.path.exists(dll_path):
            binaries_list.append((dll_path, '.'))

# Check for vJoy DLL (optional - don't fail build if not found)
vjoy_paths = [
    'C:\\Program Files\\vJoy\\x64\\vJoyInterface.dll',
    'C:\\Program Files (x86)\\vJoy\\x64\\vJoyInterface.dll'
]

vjoy_found = False
for vjoy_path in vjoy_paths:
    if os.path.exists(vjoy_path):
        binaries_list.append((vjoy_path, '.'))
        vjoy_found = True
        # print(f"Found vJoy DLL: {vjoy_path}")
        break

if not vjoy_found:
    pass
    # print("vJoy DLL not found on build machine - this is OK, users will install it via installer")

# Check for HidHide executables (optional)
hidhide_paths = ['trackpro/pedals/HidHideCLI.exe', 'trackpro/pedals/HidHideClient.exe']
for hidhide_path in hidhide_paths:
    if os.path.exists(hidhide_path):
        binaries_list.append((hidhide_path, '.'))
        # print(f"Found HidHide executable: {hidhide_path}")

# Essential data files for runtime
datas_list = [
    # Core code
    ('trackpro', 'trackpro'),
    
    # Essential configuration files
    ('config.ini', '.'),
    
    # Essential resources
    ('trackpro/resources/terms_of_service.txt', 'trackpro/resources'),
    ('trackpro/database/migrations', 'trackpro/database/migrations'),
    
    # Core UI resources - include minimal icons needed for functionality
    ('ui_resources/fonts', 'ui_resources/fonts'),
    ('ui_resources/generated-files', 'ui_resources/generated-files'),
    ('ui_resources/json-styles', 'ui_resources/json-styles'),
]

# Add optional files only if they exist
optional_files = [
    ('.env', '.'),
    ('race_coach.db', '.'),
    ('curve_cache.json', '.'),
    ('ai_coach_volume.json', '.'),
    ('centerline_track_map.json', '.'),
    ('data.txt', '.'),
    ('trackpro/resources/icons/trackpro_tray-1.ico', 'trackpro/resources/icons'),
]

for file_path, dest in optional_files:
    if os.path.exists(file_path):
        datas_list.append((file_path, dest))

# Add Qt WebEngine resources if available
if pyqt6_path:
    qt_resources_path = os.path.join(pyqt6_path, 'resources')
    if os.path.exists(qt_resources_path):
        datas_list.append((qt_resources_path, 'PyQt6/Qt6/resources'))
        # print("Added Qt WebEngine resources")
        
        # Add specific V8 context files that are critical for WebEngine
        v8_context_file = os.path.join(qt_resources_path, 'v8_context_snapshot.bin')
        if os.path.exists(v8_context_file):
            datas_list.append((v8_context_file, '.'))
            # print("Added V8 context snapshot")

# Essential hidden imports for runtime - balanced approach
optimize_hiddenimports = [
        # Core TrackPro modules that must be explicitly imported
        'trackpro',
        'trackpro.modern_main',
        'trackpro.config',
        'trackpro.logging_config',
        'trackpro.updater',
        
        # Core functionality modules
        'trackpro.race_coach.utils.data_processing',
        'trackpro.race_coach.ui.integrated_track_builder_dialog',
        'future.eye_tracking.eye_tracking_manager',
        'future.eye_tracking.eye_tracking_overlay',
        'future.eye_tracking.eye_tracking_settings',
        'future.gamification.trackpro_gamification.ui.overview_elements',
        'trackpro.database.force_update_user_level',
        'trackpro.database.refresh_user_cache',
        'trackpro.database.run_migrations',
        'trackpro.database.update_lawrence_to_team',
        'trackpro.database.update_lawrence_to_team_direct',
        'trackpro.ui.theme_engine',
        'trackpro.community.community_main_widget',
        'trackpro.community.main_widget',
        'trackpro.utils.performance_optimizer',
        
        # Essential UI and auth modules
        'trackpro.auth',
        'trackpro.auth.oauth_handler',
        'trackpro.auth.user_manager',
        'trackpro.ui',
        'trackpro.ui.modern',
        'trackpro.ui.pages',
        
        # Pedal system
        'trackpro.pedals',
        'trackpro.pedals.calibration',
        'trackpro.pedals.hardware_input',
        'trackpro.pedals.output',
        
        # Database essentials
        'trackpro.database',
        'trackpro.database.supabase_client',
        'Supabase',
        'Supabase.auth',
        'Supabase.client',
        'Supabase.database',
        
        # Fix matplotlib backend import issue
        'matplotlib.backends.backend_qtagg',
        
        # Essential PyQt6 modules for functionality
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtMultimedia',
        'PyQt6.QtOpenGL',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        
        # Essential third-party modules
        'numpy',
        'requests',
        'psutil',
        'sqlite3',
        'win32api',
        
        # Essential standard library modules for Race Coach
        'cProfile',
        'profile',
        'pstats',
        'pydoc',
        'help',
        'threading',
        'queue',
        'concurrent.futures',
        'multiprocessing',
        'logging',
        'json',
        'pickle',
        'traceback',
        'time',
        'datetime',
        'pathlib',
        'os',
        'sys',
        'subprocess',
        'inspect',
        'types',
        'collections',
        'itertools',
        'functools',
        'operator',
        
        # Network and HTTP for Supabase/API calls
        'aiohttp',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
]

# Optional: include UPX if available to reduce binary size
enable_upx = False
try:
    import shutil as _shutil
    if _shutil.which('upx'):
        enable_upx = True
except Exception:
    enable_upx = False

a = Analysis(
    ['tp_boot.py'],
    pathex=[],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=optimize_hiddenimports,
    hookspath=[],
    hooksconfig={
        # Disable matplotlib backend auto-detection to prevent hanging
        'matplotlib': {
            'backends': ['QtAgg'],  # Use QtAgg instead of Qt6Agg
        },
    },
    runtime_hooks=[],
    excludes=[
        # Only exclude truly heavy packages that we definitely don't need
        'scipy', 'sklearn', 'scikit-learn', 'pandas', 'seaborn',
        'tensorflow', 'torch', 'jax', 'keras', 'xgboost',
        'IPython', 'jupyter', 'notebook', 'jupyterlab',
        'pytest', 'nose', 'mock',
        'mediapipe', 'cv2.data', 'opencv-python',
        'tkinter', 'Tkinter',
        'sounddevice', 'soundfile', 'pyaudio',
        
        # Specific matplotlib backends we don't use
        'matplotlib.backends.backend_pdf',
        'matplotlib.backends.backend_ps', 
        'matplotlib.backends.backend_svg',
        'matplotlib.backends.backend_cairo',
        'matplotlib.backends.backend_gtk3agg',
        'matplotlib.backends.backend_gtk4agg',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.backends.backend_webagg',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_qt6agg',
        
        # Problematic packages that cause hanging
        'pyqtgraph.opengl',
        
        # Large Qt6 modules definitely not needed
        'PyQt6.Qt3DAnimation', 'PyQt6.Qt3DCore', 'PyQt6.Qt3DExtras',
        'PyQt6.Qt3DInput', 'PyQt6.Qt3DLogic', 'PyQt6.Qt3DRender',
        'PyQt6.QtBluetooth', 'PyQt6.QtDataVisualization', 'PyQt6.QtDesigner',
        'PyQt6.QtNfc', 'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
        'PyQt6.QtPositioning', 'PyQt6.QtQml', 'PyQt6.QtQuick3D',
        'PyQt6.QtRemoteObjects', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort',
        'PyQt6.QtSpatialAudio', 'PyQt6.QtSql', 'PyQt6.QtStateMachine',
        'PyQt6.QtTest', 'PyQt6.QtTextToSpeech', 'PyQt6.QtWebSockets',
        
        # Truly unused modules
        'turtle', 'turtledemo', 'idlelib',
        'antigravity',
    ],
    noarchive=False,
    # Use optimize=1 (-O). optimize=2 (-OO) strips docstrings and can break numpy/pyqtgraph
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'TrackPro_v{TP_VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=enable_upx,
    upx_exclude=[],
    runtime_tmpdir=None,
    # Enable console so startup errors are visible in built versions
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
    icon='trackpro/resources/icons/trackpro_tray-1.ico',
)