# -*- mode: python ; coding: utf-8 -*-
import os
import site

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
            print(f"Found Qt WebEngine file: {webengine_file}")
        else:
            print(f"WARNING: Missing Qt WebEngine file: {webengine_file}")

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
        print(f"Found vJoy DLL: {vjoy_path}")
        break

if not vjoy_found:
    print("vJoy DLL not found on build machine - this is OK, users will install it via installer")

# Check for HidHide executables (optional)
hidhide_paths = ['trackpro/pedals/HidHideCLI.exe', 'trackpro/pedals/HidHideClient.exe']
for hidhide_path in hidhide_paths:
    if os.path.exists(hidhide_path):
        binaries_list.append((hidhide_path, '.'))
        print(f"Found HidHide executable: {hidhide_path}")

# Build datas list - minimal and essential only
datas_list = [
    # Core TrackPro files
    ('trackpro', 'trackpro'),
    ('race_coach.db', '.'),
    ('config.ini', '.'),
    ('curve_cache.json', '.'),
    *([('.env', '.')] if os.path.exists('.env') else []),
    ('trackpro/resources/terms_of_service.txt', 'trackpro/resources'),
    ('trackpro/database/migrations', 'trackpro/database/migrations'),
    # Core resources only
    ('trackpro/resources', 'trackpro/resources'),
    ('ai_coach_volume.json', '.'),
    ('centerline_track_map.json', '.'),
    ('data.txt', '.'),
    ('future', 'future'),
    ('ui_resources', 'ui_resources'),
    ('Supabase', 'Supabase'),
]

# Add Qt WebEngine resources if available
if pyqt6_path:
    qt_resources_path = os.path.join(pyqt6_path, 'resources')
    if os.path.exists(qt_resources_path):
        datas_list.append((qt_resources_path, 'PyQt6/Qt6/resources'))
        print("Added Qt WebEngine resources")
        
        # Add specific V8 context files that are critical for WebEngine
        v8_context_file = os.path.join(qt_resources_path, 'v8_context_snapshot.bin')
        if os.path.exists(v8_context_file):
            datas_list.append((v8_context_file, '.'))
            print("Added V8 context snapshot")

a = Analysis(
    ['new_ui.py'],
    pathex=[],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=[
        # Core TrackPro modules only
        'trackpro',
        'trackpro.modern_main',
        'trackpro.config',
        'trackpro.logging_config',
        'trackpro.updater',
        
        # Authentication system
        'trackpro.auth',
        'trackpro.auth.oauth_handler',
        'trackpro.auth.user_manager',
        'trackpro.auth.login_dialog',
        'trackpro.auth.signup_dialog',
        'trackpro.auth.base_dialog',
        'trackpro.auth.secure_session',
        
        # Pedal system
        'trackpro.pedals',
        'trackpro.pedals.handbrake_input',
        'trackpro.pedals.output',
        'trackpro.pedals.hardware_input',
        'trackpro.pedals.hidhide',
        'trackpro.pedals.calibration',
        'trackpro.pedals.calibration_chart',
        'trackpro.pedals.curve_cache',
        
        # Race coach and telemetry
        'trackpro.race_coach',
        'trackpro.race_coach.simple_iracing',
        'trackpro.race_coach.iracing_lap_saver',
        'trackpro.race_coach.iracing_session_monitor',
        'trackpro.race_coach.analysis',
        'trackpro.race_coach.connection_manager',
        'trackpro.race_coach.utils',
        'trackpro.race_coach.utils.data_processing',
        'trackpro.race_coach.utils.telemetry_validation',
        'trackpro.race_coach.utils.telemetry_worker',
        'trackpro.race_coach.widgets',
        'trackpro.race_coach.widgets.brake_graph',
        'trackpro.race_coach.widgets.gaze_graph',
        'trackpro.race_coach.widgets.gear_graph',
        'trackpro.race_coach.ui',
        'trackpro.race_coach.ui.coaching_data_manager',
        'trackpro.race_coach.ui.ai_coach_volume_widget',
        'trackpro.race_coach.ai_coach',
        'trackpro.race_coach.ai_coach.ai_coach',
        'trackpro.race_coach.ai_coach.elevenlabs_client',
        'trackpro.race_coach.pyirsdk',
        'trackpro.race_coach.pyirsdk.irsdk',
        
        # Future modules
        'future',
        'future.eye_tracking',
        'future.eye_tracking.eye_tracking_manager',
        'future.eye_tracking.eye_tracking_overlay',
        'future.eye_tracking.eye_tracking_settings',
        'future.gamification',
        'future.gamification.trackpro_gamification',
        'future.gamification.trackpro_gamification.stripe_integration',
        'future.gamification.trackpro_gamification.supabase_gamification',
        'future.gamification.trackpro_gamification.ui',
        'future.gamification.trackpro_gamification.ui.enhanced_quest_view',
        'future.gamification.trackpro_gamification.ui.notifications',
        'future.gamification.trackpro_gamification.ui.overview_elements',
        
        # Database
        'trackpro.database',
        'trackpro.database.supabase',
        'trackpro.database.supabase_client',
        'trackpro.database.base',
        'trackpro.database.user_manager',
        'trackpro.database.calibration_manager',
        
        # UI components
        'trackpro.ui',
        'trackpro.ui.modern',
        'trackpro.ui.pages',
        'trackpro.ui.pages.pedals',
        'trackpro.ui.pages.race_pass',
        'trackpro.ui.pages.support',
        'trackpro.ui.shared_imports',
        'trackpro.ui.theme',
        'trackpro.ui.theme_engine',
        
        # Community system
        'trackpro.community',
        'trackpro.community.community_manager',
        'trackpro.community.community_main_widget',
        
        # Social system
        'trackpro.social',
        'trackpro.social.achievements_manager',
        'trackpro.social.activity_manager',
        
        # Utils
        'trackpro.utils',
        'trackpro.utils.app_tracker',
        'trackpro.utils.performance_optimizer',
        
        # Essential PyQt6 modules for TrackPro only
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtMultimedia',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtCharts',
        'PyQt6.sip',
        
        # Core scientific computing
        'numpy',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        'numpy.core.umath',
        'numpy.lib',
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
        
        # Matplotlib for charts and graphs
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_agg',
        'matplotlib.figure',
        
        # Audio/game essentials
        'pygame',
        'pygame.mixer',
        'pygame.joystick',
        'pygame.event',
        
        # Windows API
        'win32api',
        'win32con',
        'win32gui',
        
        # Database essentials
        'supabase',
        'supabase.lib',
        'supabase.lib.client_options',
        'supabase.lib.realtime',
        'supabase.lib.auth',
        'sqlite3',
        
        # Essential modules for TrackPro
        'psutil',
        'json',
        'threading',
        'queue',
        'concurrent.futures',
        'time',
        'pathlib',
        'hashlib',
        'ctypes',
        'ctypes.wintypes',
        'logging',
        'traceback',
        'subprocess',
        'shutil',
        'os',
        'sys',
        're',
        'glob',
        'datetime',
        'calendar',
        'math',
        'statistics',
        'random',
        'uuid',
        'base64',
        'zlib',
        'pickle',
        'copy',
        'collections',
        'itertools',
        'functools',
        'operator',
        'typing',
        'typing_extensions',
        'asyncio',
        'aiohttp',
        'ssl',
        'socket',
        'http',
        'http.client',
        'urllib',
        'urllib.parse',
        'webbrowser',
        'tempfile',
        'platform',
        'getpass',
        'locale',
        'codecs',
        'struct',
        'binascii',
        'array',
        'mmap',
        'select',
        'signal',
        'errno',
        'fcntl',
        'pwd',
        'grp',
        'crypt',
        'termios',
        'tty',
        'pty',
        'resource',
        'pipes',
        'posix',
        'posixpath',
        'nt',
        'ntpath',
        'stat',
        'time',
        'calendar',
        'datetime',
        'email',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'email.mime.base',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Remove massive unnecessary packages
        'scipy', 'sklearn', 'scikit-learn', 'pandas',
        'matplotlib.backends.backend_pdf',
        'matplotlib.backends.backend_ps', 
        'matplotlib.backends.backend_svg',
        'matplotlib.tests',
        'scipy.spatial.transform',
        'scipy.optimize',
        'scipy.interpolate', 
        'scipy.integrate',
        'scipy.special',
        'scipy.stats',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'unittest', 'test', 'tests',
        'setuptools', 'pip',
        'wheel', 'distutils',
        'mediapipe', 'tensorflow', 'jax', 'torch',
        'cv2.data',  # OpenCV data files
        'PIL.ImageTk',  # Tkinter support
        'tkinter',
        # Qt6 modules we don't need
        'PyQt6.Qt3DAnimation',
        'PyQt6.Qt3DCore', 
        'PyQt6.Qt3DExtras',
        'PyQt6.Qt3DInput',
        'PyQt6.Qt3DLogic',
        'PyQt6.Qt3DRender',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDataVisualization',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtLocation',
        'PyQt6.QtNetworkAuth',
        'PyQt6.QtNfc',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
        'PyQt6.QtPositioning',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuick3D',
        'PyQt6.QtQuickWidgets',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSpatialAudio',
        'PyQt6.QtSql',
        'PyQt6.QtStateMachine',
        'PyQt6.QtTest',
        'PyQt6.QtTextToSpeech',
        'PyQt6.QtWebSockets',
        # Audio libraries we don't need
        'sounddevice',
        'soundfile',
        # Large development tools
        'babel',
        'jinja2',
        'markupsafe',
        'docutils',
        'sphinx',
    ],
    noarchive=False,
    optimize=1,  # Enable Python optimization
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TrackPro_v1.5.5',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Disabled for Windows compatibility
    upx=False,   # Disabled to avoid UPX dependency issues
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
)
