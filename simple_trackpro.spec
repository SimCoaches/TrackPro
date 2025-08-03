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
    qt_resources_path = os.path.join(pyqt6_path, 'resources')
    
    # Essential Qt WebEngine binaries
    webengine_files = [
        'QtWebEngineProcess.exe',
        'Qt6WebEngineCore.dll',
        'Qt6WebEngineWidgets.dll',
        'Qt6WebEngineQuick.dll',
        'Qt6WebEngineQuickDelegatesQml.dll'
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

# Build datas list with Qt WebEngine resources
datas_list = [
    # Core TrackPro files
    ('trackpro', 'trackpro'),
    ('race_coach.db', '.'),
    ('config.ini', '.'),
    ('curve_cache.json', '.'),
    *([('.env', '.')] if os.path.exists('.env') else []),
    ('trackpro/resources/terms_of_service.txt', 'trackpro/resources'),
    ('trackpro/database/migrations', 'trackpro/database/migrations'),
    # Explicitly include all resource files
    ('trackpro/resources', 'trackpro/resources'),
    # Explicitly include individual image files for safety
    ('trackpro/resources/images/splash_background.png', 'trackpro/resources/images'),
    ('trackpro/resources/images/trackpro_logo_small.png', 'trackpro/resources/images'),
    ('trackpro/resources/images/2_pedal_set.png', 'trackpro/resources/images'),
    ('trackpro/resources/images/3_pedal_set.png', 'trackpro/resources/images'),
    ('trackpro/resources/images/trackpro_logo.png', 'trackpro/resources/images'),
    ('trackpro/resources/icons/trackpro_tray.ico', 'trackpro/resources/icons'),
    ('Supabase', 'Supabase'),
]

# Debug: Print what files we're including
print("="*50)
print("SPEC FILE: Including these data files:")
for src, dst in datas_list:
    if os.path.exists(src):
        if os.path.isfile(src):
            print(f"  FILE: {src} -> {dst}")
        else:
            print(f"  DIR:  {src} -> {dst}")
    else:
        print(f"  MISSING: {src}")
print("="*50)

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
    
    # Add Qt WebEngine translations
    qt_translations_path = os.path.join(pyqt6_path, 'translations')
    if os.path.exists(qt_translations_path):
        datas_list.append((qt_translations_path, 'PyQt6/Qt6/translations'))
        print("Added Qt WebEngine translations")

a = Analysis(
    ['new_ui.py'],
    pathex=[],
    binaries=binaries_list,
    datas=datas_list,
    hiddenimports=[
        # Core TrackPro modules
        'trackpro',
        'trackpro.modern_main',
        'trackpro.config',
        'trackpro.logging_config',
        
        # Essential PyQt6 modules for TrackPro
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtWebChannel',  # Required by TrackPro
        'PyQt6.QtWebEngineCore',    # Web engine core
        'PyQt6.QtWebEngineWidgets', # Web engine widgets
        'PyQt6.QtWebEngineQuick',   # Quick web engine
        'PyQt6.QtNetwork',     # For network communication
        'PyQt6.QtMultimedia',  # For audio/sound effects
        'PyQt6.QtOpenGL',      # For 3D graphics/charts
        'PyQt6.QtOpenGLWidgets', # For OpenGL widgets
        'PyQt6.QtPrintSupport', # For printing reports
        'PyQt6.QtSvg',         # For vector graphics
        'PyQt6.QtSvgWidgets',  # For SVG widgets
        'PyQt6.QtCharts',      # For telemetry charts
        'PyQt6.sip',
        
        # Core scientific computing
        'numpy',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        'numpy.core.umath',
        'numpy.lib',
        'requests',
        
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
        
        # Windows API
        'win32api',
        'win32con',
        'win32gui',
        
        # Database essentials
        'supabase',
        'sqlite3',
        'numpy.core.overrides',
        
        # Essential modules for TrackPro
        'psutil',
        'json',
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
