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

# Check for bundled HidHide CLI executables
hidhide_paths = [
    'trackpro/pedals/HidHideCLI.exe',
    'trackpro/pedals/HidHideClient.exe',
    'trackpro/HidHideCLI.exe',
    'trackpro/HidHideClient.exe'
]

hidhide_found = False
for hidhide_path in hidhide_paths:
    if os.path.exists(hidhide_path):
        print(f"Found HidHide executable: {hidhide_path}")
        binaries_list.append((hidhide_path, '.'))
        hidhide_found = True
        
# Add both CLI and Client if found
if hidhide_found:
    # Try to find both CLI and Client executables
    for cli_path in ['trackpro/pedals/HidHideCLI.exe', 'trackpro/HidHideCLI.exe']:
        if os.path.exists(cli_path) and (cli_path, '.') not in binaries_list:
            binaries_list.append((cli_path, '.'))
            
    for client_path in ['trackpro/pedals/HidHideClient.exe', 'trackpro/HidHideClient.exe']:
        if os.path.exists(client_path) and (client_path, '.') not in binaries_list:
            binaries_list.append((client_path, '.'))
else:
    print("WARNING: No HidHide executables found for bundling!")

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
        # Include environment file if it exists (for Twilio credentials)
        *([('.env', '.')] if os.path.exists('.env') else []),
        # Include new resource files
        ('trackpro/resources/terms_of_service.txt', 'trackpro/resources'),
        ('trackpro/database/migrations', 'trackpro/database/migrations'),
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
        # Include Twilio and other new dependencies (if they have data files)
        *collect_data_files('twilio'),
        # Include resources directories
        ('trackpro/resources', 'trackpro/resources'),
        ('Supabase', 'Supabase'),
    ],
    hiddenimports=[
        # === CORE TRACKPRO MODULES ===
        'trackpro',
        'trackpro.main',
        'trackpro.config',
        'trackpro.logging_config',
        'trackpro.updater',
        
        # === AUTHENTICATION MODULES (Updated - all new auth features) ===
        'trackpro.auth',
        'trackpro.auth.login_dialog',
        'trackpro.auth.signup_dialog',
        'trackpro.auth.base_dialog',
        'trackpro.auth.oauth_handler',
        'trackpro.auth.user_manager',
        'trackpro.auth.phone_verification_dialog',
        'trackpro.auth.sms_verification_dialog',
        'trackpro.auth.profile_completion_dialog',
        'trackpro.auth.secure_session',
        'trackpro.auth.twilio_service',
        'trackpro.auth.terms_handler',
        
        # === UI MODULES (Updated for PyQt6) ===
        'trackpro.ui',
        'trackpro.ui.main_window',
        'trackpro.ui.shared_imports',
        'trackpro.ui.chart_widgets',
        'trackpro.ui.auth_dialogs',
        'trackpro.ui.theme',
        'trackpro.ui.menu_bar',
        'trackpro.ui.system_tray',
        'trackpro.ui.community_ui',
        'trackpro.ui.social_ui',
        'trackpro.ui.user_account_ui',
        'trackpro.ui.achievements_ui',
        'trackpro.ui.content_management_ui',
        'trackpro.ui.standalone_account_page',
        'trackpro.ui.terms_dialog',
        'trackpro.ui.eye_tracking_settings',
        'trackpro.ui.track_map_overlay_settings',
        
        # === DATABASE MODULES (Updated) ===
        'trackpro.database',
        'trackpro.database.base',
        'trackpro.database.supabase_client',
        'trackpro.database.user_manager',
        'trackpro.database.calibration_manager',
        'trackpro.database.pedal_profiles',
        'trackpro.database.run_migrations',
        
        # === RACE COACH MODULES (Comprehensive) ===
        'trackpro.race_coach',
        'trackpro.race_coach.ui',
        'trackpro.race_coach.ui.main_window',
        'trackpro.race_coach.ui.overview_tab',
        'trackpro.race_coach.ui.telemetry_tab',
        'trackpro.race_coach.ui.superlap_tab',
        'trackpro.race_coach.ui.videos_tab',
        'trackpro.race_coach.ui.overview_data_manager',
        'trackpro.race_coach.ui.coaching_data_manager',
        'trackpro.race_coach.ui.common_widgets',
        'trackpro.race_coach.ui.corner_detection_dialog',
        'trackpro.race_coach.ui.integrated_track_builder_dialog',
        'trackpro.race_coach.ui.track_map_overlay_settings',
        'trackpro.race_coach.ui.track_visualization_window',
        'trackpro.race_coach.ui.ai_coach_volume_widget',
        'trackpro.race_coach.model',
        'trackpro.race_coach.data_manager',
        'trackpro.race_coach.iracing_api',
        'trackpro.race_coach.simple_iracing',
        'trackpro.race_coach.analysis',
        'trackpro.race_coach.connection_manager',
        'trackpro.race_coach.corner_detection_manager',
        'trackpro.race_coach.corner_segmentation',
        'trackpro.race_coach.debouncer',
        'trackpro.race_coach.eye_tracking_manager',
        'trackpro.race_coach.eye_tracking_overlay',
        'trackpro.race_coach.integrated_track_builder',
        'trackpro.race_coach.iracing_lap_saver',
        'trackpro.race_coach.iracing_session_monitor',
        'trackpro.race_coach.lap_indexer',
        'trackpro.race_coach.lazy_loader',
        'trackpro.race_coach.performance_monitor',
        'trackpro.race_coach.sector_timing',
        'trackpro.race_coach.telemetry_playback',
        'trackpro.race_coach.telemetry_saver',
        'trackpro.race_coach.telemetry_stats',
        'trackpro.race_coach.track_map_generator',
        'trackpro.race_coach.track_map_manager',
        'trackpro.race_coach.track_map_overlay',
        'trackpro.race_coach.pyirsdk',
        'trackpro.race_coach.pyirsdk.irsdk',
        'trackpro.race_coach.ai_coach',
        'trackpro.race_coach.ai_coach.ai_coach',
        'trackpro.race_coach.ai_coach.elevenlabs_client',
        'trackpro.race_coach.ai_coach.openai_client',
        'trackpro.race_coach.utils',
        'trackpro.race_coach.utils.data_processing',
        'trackpro.race_coach.utils.telemetry_validation',
        'trackpro.race_coach.utils.telemetry_worker',
        'trackpro.race_coach.widgets',
        'trackpro.race_coach.widgets.brake_graph',
        'trackpro.race_coach.widgets.gaze_graph',
        'trackpro.race_coach.widgets.gear_graph',
        'trackpro.race_coach.widgets.graph_base',
        'trackpro.race_coach.widgets.sector_timing_widget',
        'trackpro.race_coach.widgets.speed_graph',
        'trackpro.race_coach.widgets.steering_graph',
        'trackpro.race_coach.widgets.throttle_graph',
        
        # === PEDALS MODULES ===
        'trackpro.pedals',
        'trackpro.pedals.calibration',
        'trackpro.pedals.calibration_chart',
        'trackpro.pedals.curve_cache',
        'trackpro.pedals.hardware_input',
        'trackpro.pedals.hidhide',
        'trackpro.pedals.output',
        'trackpro.pedals.profile_dialog',
        'trackpro.pedals.vjoy_installer',
        
        # === COMMUNITY MODULES (New) ===
        'trackpro.community',
        'trackpro.community.community_main_widget',
        'trackpro.community.community_social',
        'trackpro.community.community_content',
        'trackpro.community.community_account',
        'trackpro.community.community_theme',
        'trackpro.community.database_managers',
        'trackpro.community.discord_integration',
        'trackpro.community.discord_setup_dialog',
        'trackpro.community.main_widget',
        'trackpro.community.racing_achievements_automation',
        'trackpro.community.ui_components',
        
        # === SOCIAL MODULES (New) ===
        'trackpro.social',
        'trackpro.social.achievements_manager',
        'trackpro.social.activity_manager',
        'trackpro.social.community_manager',
        'trackpro.social.content_manager',
        'trackpro.social.friends_manager',
        'trackpro.social.messaging_manager',
        'trackpro.social.reputation_manager',
        'trackpro.social.user_manager',
        
        # === GAMIFICATION MODULES (New) ===
        'trackpro.gamification',
        'trackpro.gamification.stripe_integration',
        'trackpro.gamification.supabase_gamification',
        'trackpro.gamification.ui',
        'trackpro.gamification.ui.enhanced_quest_view',
        'trackpro.gamification.ui.notifications',
        'trackpro.gamification.ui.overview_elements',
        'trackpro.gamification.ui.quest_card_widget',
        'trackpro.gamification.ui.race_pass_view',
        'trackpro.gamification.ui.trackcoins_store',
        
        # === UTILITIES MODULES ===
        'trackpro.utils',
        'trackpro.utils.performance_optimizer',
        'trackpro.utils.subprocess_utils',
        
        # === PYQT6 MODULES (Updated for PyQt6) ===
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        'PyQt6.QtCharts',
        'PyQt6.sip',
        
        # === SCIENTIFIC COMPUTING MODULES ===
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        'numpy.core.umath',
        'numpy.lib',
        'numpy.linalg',
        'numpy.fft',
        'numpy.polynomial',
        'numpy.random',
        'numpy.distutils',
        'numpy.ma',
        'scipy',
        'scipy.stats',
        'scipy.interpolate',
        'scipy.optimize',
        'sklearn',
        'sklearn.cluster',
        'filterpy',
        'filterpy.kalman',
        
        # === MATPLOTLIB MODULES (Updated for PyQt6) ===
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_qt6agg',  # Updated for PyQt6
        'matplotlib.backends.backend_agg',
        'matplotlib.figure',
        
        # === NETWORKING AND HTTP MODULES ===
        'requests',
        'urllib3',
        'httpx',
        'httpcore', 
        'h11',
        'h2',
        'websockets',
        'python_socketio',
        
        # === AUTHENTICATION AND SECURITY MODULES ===
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'jwt',
        'pydantic',
        
        # === SUPABASE MODULES ===
        'supabase',
        'gotrue',
        'postgrest',
        'supafunc',
        'realtime',
        'storage3',
        
        # === TWILIO MODULES (New for 2FA) ===
        'twilio',
        'twilio.rest',
        'twilio.base',
        'twilio.base.exceptions',
        
        # === PAYMENT MODULES (New) ===
        'stripe',
        
        # === AI MODULES (New) ===
        'openai',
        'elevenlabs',
        
        # === AUDIO MODULES ===
        'pygame',
        'pygame.mixer',
        'pygame.display',
        'pygame.joystick',
        'soundfile',
        'sounddevice',
        'pydub',
        
        # === EYE TRACKING MODULES (Optional - only if properly working) ===
        'cv2',
        'opencv-python',
        
        # === WINDOWS API MODULES ===
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
        
        # === STANDARD LIBRARY MODULES ===
        'sqlite3',
        'json',
        'yaml',
        'csv',
        'pickle',
        'threading',
        'multiprocessing',
        'subprocess',
        'logging',
        'datetime',
        'pathlib',
        'os',
        'sys',
        'time',
        're',
        'base64',
        'hashlib',
        'urllib',
        'urllib.parse',
        'socket',
        'psutil',
        
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
        # Exclude problematic eye tracking dependencies that cause build issues
        'mediapipe',
        'mediapipe.python',
        'mediapipe.python._framework_bindings',
        'jax',
        'jax._src',
        'jaxlib',
        'eyetrax',
        # Exclude TensorFlow dependencies that MediaPipe pulls in
        'tensorflow',
        'tensorflow_intel',
        'tflite',
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
    console=False,  # Disable console for GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
    manifest='trackpro.manifest',
)