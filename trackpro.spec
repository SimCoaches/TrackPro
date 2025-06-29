# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from trackpro import __version__
import os

# Get all submodules for critical packages to prevent import errors
pygame_submodules = collect_submodules('pygame')
numpy_submodules = collect_submodules('numpy')
pyqt6_submodules = collect_submodules('PyQt6')
supabase_submodules = collect_submodules('supabase')

# Build binaries list dynamically to avoid None values
binaries_list = []

# Check for vJoy DLL in multiple locations
vjoy_paths = [
    'C:\\Program Files\\vJoy\\x64\\vJoyInterface.dll',
    'C:\\Program Files (x86)\\vJoy\\x64\\vJoyInterface.dll'
]

for vjoy_path in vjoy_paths:
    if os.path.exists(vjoy_path):
        binaries_list.append((vjoy_path, '.'))
        break  # Only add the first one found

# Check for bundled HidHide CLI
hidhide_paths = [
    'trackpro/HidHideCLI.exe',
    'trackpro/pedals/HidHideCLI.exe'
]

for hidhide_path in hidhide_paths:
    if os.path.exists(hidhide_path):
        binaries_list.append((hidhide_path, '.'))
        break  # Only add the first one found

# --- Analysis Configuration ---
a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries_list,
    datas=[
        ('trackpro', 'trackpro'),
        ('trackpro.manifest', '.'),
        ('race_coach.db', '.'),
        ('config.ini', '.'),
        ('curve_cache.json', '.'),
        # Include all data files for critical packages
        *collect_data_files('pygame'),
        *collect_data_files('pyqtgraph'),
        *collect_data_files('matplotlib'),
        *collect_data_files('scipy'),
        *collect_data_files('numpy'),
        *collect_data_files('PyQt6', include_py_files=True),
        *collect_data_files('supabase'),
        *collect_data_files('gotrue'),
        *collect_data_files('postgrest'),
        # Include resources directories
        ('trackpro/resources', 'trackpro/resources'),
        ('Supabase', 'Supabase'),
    ],
    hiddenimports=[
        # Core TrackPro modules
        'trackpro',
        'trackpro.main',
        'trackpro.ui',
        'trackpro.auth',
        'trackpro.auth.login_dialog',
        'trackpro.auth.oauth_handler',
        'trackpro.auth.user_manager',
        'trackpro.database',
        'trackpro.database.supabase_client',
        'trackpro.race_coach',
        'trackpro.race_coach.iracing_api',
        'trackpro.race_coach.ui',
        'trackpro.race_coach.ui.main_window',
        'trackpro.pedals',
        'trackpro.pedals.calibration',
        'trackpro.pedals.hidhide',
        'trackpro.community',
        'trackpro.gamification',
        
        # PyQt6 modules
        'PyQt6.QtCharts',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngine',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        
        # Game/input modules
        'pygame',
        'pygame.mixer',
        'pygame.display',
        'pygame.joystick',
        
        # Windows API modules
        'win32serviceutil', 
        'win32service',
        'win32api',
        'win32con',
        'win32file',
        'win32event',
        'winerror',
        'pywintypes',
        'win32security',
        'win32process',
        'win32gui',
        
        # Scientific computing
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.lib',
        'numpy.random',
        'scipy',
        'scipy.stats',
        'matplotlib',
        'matplotlib.backends',
        'matplotlib.backends.backend_qt6agg',
        'matplotlib.pyplot',
        
        # Network and HTTP
        'requests',
        'urllib3',
        'httpx',
        'httpcore',
        'h11',
        'h2',
        'websockets',
        
        # Supabase and authentication
        'supabase',
        'gotrue',
        'postgrest',
        'supafunc',
        'realtime',
        'storage3',
        
        # Data processing
        'psutil',
        'json',
        'sqlite3',
        'csv',
        'pickle',
        
        # Add all discovered submodules
        *pygame_submodules,
        *numpy_submodules,
        *pyqt6_submodules,
        *supabase_submodules,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test modules to reduce size
        'pytest',
        'unittest',
        'test',
        'tests',
        # Exclude development tools
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# --- Executable Configuration ---
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'TrackPro_v{__version__}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX to prevent corruption issues
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Enable console for debugging startup issues
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    manifest='trackpro.manifest',
)