#!/usr/bin/env python3
"""
Modern TrackPro UI with complete authentication system and iRacing telemetry integration.
Usage: python new_ui.py

GLOBAL iRACING TELEMETRY INTEGRATION:
=====================================

This application now includes the same global iRacing telemetry system that run_app.py uses.
All screens within the application can access real-time telemetry data from iRacing.

How to access telemetry in your screens:
--------------------------------------

1. Import the access function:
   from new_ui import get_global_iracing_api

2. Get the global iRacing API instance:
   iracing_api = get_global_iracing_api()

3. Check if iRacing is connected:
   if iracing_api and iracing_api.is_connected():
       # iRacing is connected, can access telemetry

4. Register for telemetry callbacks:
   def on_telemetry_data(telemetry):
       speed = telemetry.get('Speed', 0)
       throttle = telemetry.get('Throttle', 0)
       # Process telemetry data...
   
   iracing_api.register_on_telemetry_data(on_telemetry_data)

5. Register for connection status changes:
   def on_connection_changed(is_connected, session_info):
       if is_connected:
           print("Connected to iRacing!")
       else:
           print("Disconnected from iRacing")
   
   iracing_api.register_on_connection_changed(on_connection_changed)

6. Access current telemetry data directly:
   current_data = iracing_api.current_telemetry
   speed = current_data.get('Speed', 0)

The global iRacing connection automatically:
- Connects to iRacing when it's running
- Saves telemetry data to Supabase (if authenticated)
- Handles session monitoring and lap saving
- Provides real-time telemetry data to all UI components

This is the same system used by the original TrackPro application.
"""

import sys
import os
import logging
import time
import ctypes  # PERFORMANCE FIX: Move from hot path to module level
import multiprocessing  # PERFORMANCE FIX: For CPU affinity optimization
from pathlib import Path
from typing import Optional
from queue import Empty  # PERFORMANCE FIX: Move from hot path to module level
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import Qt
import msvcrt
import tempfile

# CRITICAL: Set Qt attributes BEFORE any QApplication instance can be created AND before importing QtWebEngineWidgets
# Only set attributes if no QApplication exists yet (to avoid runtime warnings when imported after app creation)
if QApplication.instance() is None:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    # Respect persisted GL preference; fallback to software if enabled
    try:
        from trackpro.config import config as global_config
        if getattr(global_config, 'prefer_software_opengl', False):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
        else:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)
    except Exception:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)
    # Ensure Qt Quick uses OpenGL RHI when available to satisfy WebEngine plugin
    try:
        from PyQt6.QtGui import QSGRendererInterface
        from PyQt6.QtQuick import QQuickWindow
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGLRhi)
    except Exception:
        pass

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Centralized logging: env-driven + rotating file
try:
    from trackpro.logging_config import setup_logging
    setup_logging()
except Exception:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global iRacing API instance for sharing across all screens/components
global_iracing_api = None

# Global pedal hardware and output instances
global_hardware = None
global_output = None
global_hidhide = None
global_pedal_thread = None
global_pedal_stop_event = None
global_pedal_data_queue = None

# Global handbrake hardware instance
global_handbrake_hardware = None
global_handbrake_thread = None
global_handbrake_stop_event = None
global_handbrake_data_queue = None

_single_instance_lock_handle = None

def _build_brand_splash_pixmap(width: int = 600, height: int = 320):
    """Create a branded splash pixmap with gradient background and logo."""
    try:
        from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QLinearGradient
        from PyQt6.QtCore import QRect, QPointF
        pix = QPixmap(width, height)
        pix.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Background gradient
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, height))
        grad.setColorAt(0.0, QColor(16, 16, 22))
        grad.setColorAt(1.0, QColor(44, 25, 69))
        painter.fillRect(QRect(0, 0, width, height), grad)

        # Try to draw logo centered
        logo_path_candidates = []
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path_candidates.append(os.path.join(base_dir, "trackpro", "resources", "icons", "trackpro_tray.png"))
            logo_path_candidates.append(os.path.join(base_dir, "trackpro", "resources", "images", "login_image.png"))
        except Exception:
            pass

        logo_drawn = False
        for candidate in logo_path_candidates:
            if os.path.exists(candidate):
                logo = QPixmap(candidate)
                if not logo.isNull():
                    # Scale logo to fit nicely
                    target_w = min(260, int(width * 0.42))
                    target_h = int(target_w * (logo.height() / max(1, logo.width())))
                    logo_scaled = logo.scaled(target_w, target_h)
                    x = (width - logo_scaled.width()) // 2
                    y = int(height * 0.18)
                    painter.drawPixmap(x, y, logo_scaled)
                    logo_drawn = True
                    break

        # Title text
        painter.setPen(QColor(235, 235, 245))
        painter.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title = "TrackPro"
        painter.drawText(QRect(0, int(height * 0.58), width, 40),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, title)

        # Subtitle
        painter.setPen(QColor(180, 180, 200))
        painter.setFont(QFont("Arial", 10))
        subtitle = "by Sim Coaches"
        painter.drawText(QRect(0, int(height * 0.58) + 28, width, 24),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, subtitle)

        # Bottom message bar placeholder (message text will be set via showMessage)
        painter.setPen(QColor(255, 255, 255, 140))
        painter.setFont(QFont("Arial", 11))
        painter.drawText(QRect(12, height - 30, width - 24, 20),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Starting...")

        painter.end()
        return pix
    except Exception:
        # Fallback to simple dark pixmap if anything goes wrong
        from PyQt6.QtGui import QPixmap, QPainter, QFont
        pix = QPixmap(400, 200)
        pix.fill(Qt.GlobalColor.darkGray)
        p = QPainter(pix)
        p.setPen(Qt.GlobalColor.white)
        p.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "TrackPro\nStarting...")
        p.end()
        return pix

def _show_instant_splash(app: QApplication):
    """Show a fast splash immediately, reusing it later in main()."""
    from PyQt6.QtWidgets import QSplashScreen
    from PyQt6.QtCore import Qt
    pix = _build_brand_splash_pixmap()
    splash = QSplashScreen(pix)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
    splash.show()
    splash.showMessage("Loading...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, Qt.GlobalColor.white)
    app.processEvents()
    return splash

def _acquire_single_instance_lock() -> bool:
    """Prevent multiple app instances by locking a file for the process lifetime."""
    global _single_instance_lock_handle
    try:
        lock_dir = os.path.join(os.path.expanduser("~"), ".trackpro")
        os.makedirs(lock_dir, exist_ok=True)
        lock_path = os.path.join(lock_dir, "trackpro_app.lock")
        _single_instance_lock_handle = open(lock_path, "w")
        # _LK_NBLCK: non-blocking exclusive lock on Windows
        msvcrt.locking(_single_instance_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        _single_instance_lock_handle.write(str(os.getpid()))
        _single_instance_lock_handle.flush()
        return True
    except Exception:
        return False

def initialize_global_handbrake_system():
    """Initialize the global handbrake hardware system."""
    global global_handbrake_hardware, global_handbrake_thread, global_handbrake_stop_event, global_handbrake_data_queue
    
    try:
        logger.info("🤚 Initializing handbrake system...")
        
        # Initialize handbrake hardware input
        logger.info("🎛️ Initializing handbrake hardware input...")
        from trackpro.pedals.handbrake_input import HandbrakeInput
        global_handbrake_hardware = HandbrakeInput()
        logger.info("✅ Handbrake hardware input initialized")
        
        # Initialize data queue for UI updates (maxsize=1 for auto-dropping old data)
        from queue import Queue
        from threading import Event
        global_handbrake_data_queue = Queue(maxsize=1)  # PERFORMANCE FIX: Auto-drops old data
        global_handbrake_stop_event = Event()
        
        # Start the handbrake processing thread
        logger.info("🚀 Starting handbrake processing thread...")
        start_global_handbrake_thread()
        
        logger.info("🤚 Handbrake system initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize handbrake system: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

def initialize_global_pedal_system():
    """Initialize the global pedal hardware system for ultra-high performance."""
    global global_hardware, global_output, global_hidhide, global_pedal_thread, global_pedal_stop_event, global_pedal_data_queue
    
    try:
        logger.info("🎮 Initializing ULTRA-HIGH PERFORMANCE pedal system...")
        
        # Ensure a known vJoy device is enabled/configured before attempting to acquire it
        def _ensure_vjoy_device_enabled(device_id: int = 1) -> None:
            try:
                from trackpro.pedals.vjoy_installer import VJoyInstaller
                installer = VJoyInstaller(fail_silently=True)
                installed, _ = installer.is_vjoy_installed()
                if installed:
                    installer.configure_vjoy_device(device_id=device_id, axes=8, buttons=32)
            except Exception as e:
                logger.warning(f"Could not auto-configure vJoy device {device_id}: {e}")

        # Prefer vJoy Device 4 per user preference
        _ensure_vjoy_device_enabled(device_id=4)

        # Initialize vJoy output first
        logger.info("🕹️ Initializing vJoy virtual joystick...")
        from trackpro.pedals.output import VirtualJoystick
        try:
            global_output = VirtualJoystick()
            logger.info("✅ vJoy initialized successfully")
        except RuntimeError as e:
            logger.warning(f"vJoy initialization failed: {e}")
            logger.info("Initializing vJoy in test mode")
            global_output = VirtualJoystick(test_mode=True)
        
        # Initialize hardware input
        logger.info("🎛️ Initializing pedal hardware input...")
        from trackpro.pedals.hardware_input import HardwareInput
        global_hardware = HardwareInput()
        logger.info("✅ Pedal hardware input initialized")
        
        # Initialize HidHide for device management
        logger.info("🔒 Initializing HidHide device management...")
        try:
            from trackpro.pedals.hidhide import HidHideClient
            global_hidhide = HidHideClient(fail_silently=True)
            if hasattr(global_hidhide, 'functioning') and global_hidhide.functioning:
                logger.info("✅ HidHide client initialized successfully")
                # Hide the pedal device from other applications
                _hide_pedal_device()
            else:
                logger.warning("⚠️ HidHide initialized with limited functionality")
        except Exception as hidhide_error:
            logger.error(f"❌ HidHide initialization failed: {hidhide_error}")
            global_hidhide = None
        
        # Initialize data queue for UI updates (maxsize=1 for auto-dropping old data)
        from queue import Queue
        from threading import Event
        global_pedal_data_queue = Queue(maxsize=1)  # PERFORMANCE FIX: Auto-drops old data
        global_pedal_stop_event = Event()
        
        # Start the ultra-high performance pedal processing thread
        logger.info("🚀 Starting ULTRA-HIGH PERFORMANCE pedal thread...")
        start_global_pedal_thread()
        
        logger.info("🎮 ULTRA-HIGH PERFORMANCE pedal system initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize pedal system: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

def _hide_pedal_device():
    """Hide the Sim Coaches P1 Pro Pedals device from other applications."""
    if not global_hidhide:
        return
        
    try:
        device_name = "Sim Coaches P1 Pro Pedals"
        logger.info(f"🔒 Attempting to hide device: {device_name}")
        
        # Get the device instance path
        device_path = global_hidhide.get_device_instance_path(device_name)
        if device_path:
            logger.info(f"Found device path: {device_path}")
            
            # Hide the device
            success = global_hidhide.hide_device(device_path)
            if success:
                logger.info(f"✅ Successfully hid device: {device_name}")
            else:
                logger.warning(f"⚠️ Failed to hide device: {device_name}")
        else:
            logger.info(f"Device not found (normal if not connected): {device_name}")
            
    except Exception as e:
        logger.error(f"❌ Error hiding pedal device: {e}")

def start_global_handbrake_thread():
    """Start the dedicated handbrake polling thread."""
    global global_handbrake_thread
    
    from threading import Thread
    
    # Create thread for handbrake processing
    global_handbrake_thread = Thread(
        target=global_handbrake_polling_loop, 
        name="TrackPro-Modern-Handbrake-Thread",
        daemon=False  # Don't make it daemon so we can control shutdown
    )
    
    # Start the thread
    global_handbrake_thread.start()
    logger.info("🚀 HANDBRAKE THREAD: Started for modern UI")

def start_global_pedal_thread():
    """Start the dedicated ultra-high priority pedal polling thread."""
    global global_pedal_thread
    
    from threading import Thread
    
    # Create thread with ultra-high priority
    global_pedal_thread = Thread(
        target=global_pedal_polling_loop, 
        name="TrackPro-Modern-Pedal-Thread",
        daemon=False  # Don't make it daemon so we can control shutdown
    )
    
    # Start the thread
    global_pedal_thread.start()
    logger.info("🚀 ULTRA-FAST PEDAL THREAD: Started with maximum priority for modern UI")

def global_pedal_polling_loop():
    """
    Ultra-high priority pedal polling loop for modern UI.
    Optimized for 500Hz with minimal overhead and maximum responsiveness.
    """
    # PERFORMANCE FIX: Move imports to module level to avoid 500 imports/second
    # These were being imported every loop iteration!
    
    # PERFORMANCE FIX: Set Windows timer precision for accurate sleep timing
    try:
        # Set timer resolution to 1ms for precise timing (Windows default is 15.6ms)
        ctypes.windll.winmm.timeBeginPeriod(1)
        logger.info("🎯 TIMER PRECISION: Set Windows timer resolution to 1ms")
    except Exception as e:
        logger.warning(f"Could not set timer precision: {e}")
    
    # Set optimal thread priority and CPU affinity for Windows
    try:
        thread_handle = ctypes.windll.kernel32.GetCurrentThread()
        # PERFORMANCE FIX: Use ABOVE_NORMAL instead of TIME_CRITICAL to avoid system starvation
        if not ctypes.windll.kernel32.SetThreadPriority(thread_handle, 2):  # THREAD_PRIORITY_ABOVE_NORMAL
            # Get error code for better debugging
            error_code = ctypes.windll.kernel32.GetLastError()
            logger.warning(f"Failed to set pedal thread priority to ABOVE_NORMAL. Error code: {error_code}")
        else:
            logger.info("🏎️ OPTIMIZED PEDAL THREAD: Set to ABOVE_NORMAL priority for balanced performance")
            
        # PERFORMANCE FIX: Set CPU affinity to bind thread to a specific core (reduces context switching)
        try:
            cpu_count = multiprocessing.cpu_count()
            if cpu_count >= 4:  # Only set affinity if we have enough cores
                # FIXED: Use safe bit manipulation to avoid overflow
                # Bind to the last CPU core, but cap at core 63 to avoid overflow
                target_core = min(cpu_count - 1, 63)  # Windows API supports up to 64 cores
                core_mask = ctypes.c_ulonglong(1 << target_core).value  # Safe conversion
                if ctypes.windll.kernel32.SetThreadAffinityMask(thread_handle, core_mask):
                    logger.info(f"🎯 CPU AFFINITY: Bound pedal thread to CPU core {target_core}")
                else:
                    logger.debug("Could not set CPU affinity (may need admin privileges)")
        except Exception as e:
            logger.debug(f"CPU affinity not available: {e}")
            
        # FIXED: Set process priority to ABOVE_NORMAL (doesn't require admin privileges)
        process_handle = ctypes.windll.kernel32.GetCurrentProcess()
        if not ctypes.windll.kernel32.SetPriorityClass(process_handle, 0x00008000):  # ABOVE_NORMAL_PRIORITY_CLASS
            error_code = ctypes.windll.kernel32.GetLastError()
            logger.debug(f"Could not set process priority to ABOVE_NORMAL. Error code: {error_code}")
        else:
            logger.info("🚀 OPTIMIZED PROCESS: Set TrackPro to ABOVE_NORMAL priority class")
        
    except Exception as e:
        logger.warning(f"Could not set thread/process priority on Windows: {e}")

    # Ultra-fast pedal processing variables
    loop_count = 0
    timer_precision_set = False
    target_frequency = 500  # PERFORMANCE FIX: 500Hz for excellent responsiveness without system stress
    performance_log_interval = target_frequency * 10  # Log every 10 seconds
    target_frame_time = 1.0 / target_frequency  # 2ms per frame
    
    # PERFORMANCE FIX: Pre-allocate dictionaries to avoid 500 allocations/second
    vjoy_values = {'throttle': 0, 'brake': 0, 'clutch': 0}
    pedal_list = ['throttle', 'brake', 'clutch']  # Pre-allocate list to avoid recreation
    
    # PERFORMANCE FIX: Cache frequently used method references to avoid attribute lookups
    dict_get = dict.get  # Cache dict.get method reference
    
    logger.info(f"🎯 OPTIMIZED PEDAL PROCESSING: Starting at {target_frequency}Hz (2ms response time)")
    
    # Performance tracking
    slow_frame_count = 0
    missed_frame_count = 0
    
    while not global_pedal_stop_event.is_set():
        start_time = time.perf_counter()
        loop_count += 1

        # CRITICAL PATH: Ultra-fast pedal reading
        if global_hardware:
            raw_values = global_hardware.read_pedals()
            
            # ULTRA-OPTIMIZED: Single queue put (maxsize=1 auto-drops old data)
            try:
                global_pedal_data_queue.put_nowait(raw_values)  # Auto-drops if queue full
            except:
                pass  # Queue full, old data auto-dropped - continue processing

            # ULTRA-FAST: Direct calibration and vJoy output
            if global_output:
                # PERFORMANCE FIX: Reuse pre-allocated dictionary and list + cached method
                for pedal in pedal_list:
                    raw_value = dict_get(raw_values, pedal, 0)  # Use cached method reference
                    output_value = global_hardware.apply_calibration(pedal, raw_value)
                    vjoy_values[pedal] = output_value  # Remove redundant int() conversion
                
                # Get handbrake value if available  
                handbrake_value = 0
                if global_handbrake_hardware:
                    try:
                        handbrake_data = global_handbrake_hardware.read_handbrake()
                        handbrake_raw = dict_get(handbrake_data, 'handbrake', 0)  # Use cached method
                        handbrake_value = global_handbrake_hardware.apply_calibration('handbrake', handbrake_raw)
                    except:
                        handbrake_value = 0
                
                # PERFORMANCE FIX: Always call update_axis (it now handles change detection internally)
                global_output.update_axis(vjoy_values['throttle'], vjoy_values['brake'], vjoy_values['clutch'], handbrake_value)

        # PERFORMANCE MONITORING: Track actual performance
        elapsed = time.perf_counter() - start_time
        
        if elapsed > target_frame_time * 2:  # More than 2ms
            slow_frame_count += 1
        if elapsed > target_frame_time * 5:  # More than 5ms
            missed_frame_count += 1
        
        # PERFORMANCE FIX: Minimal logging to avoid I/O overhead in critical path
        if loop_count % performance_log_interval == 0:
            actual_frequency = 1.0 / elapsed if elapsed > 0 else float('inf')
            slow_percentage = (slow_frame_count / performance_log_interval) * 100
            miss_percentage = (missed_frame_count / performance_log_interval) * 100
            
            # Only log if there are significant performance issues
            if miss_percentage > 5.0:  # Only log severe issues (>5%)
                logger.error(f"🚨 PEDAL LAG: {miss_percentage:.1f}% severe delays, {actual_frequency:.0f}Hz")
            elif slow_percentage > 20.0:  # Only log major slowdowns (>20%)
                logger.warning(f"⚠️ PEDAL SLOW: {slow_percentage:.1f}% slow frames")
            # Remove debug logging completely to avoid I/O in critical path
            
            # Reset counters
            slow_frame_count = 0
            missed_frame_count = 0
        
        # PERFORMANCE FIX: High-precision sleep using Windows multimedia timer
        sleep_time = target_frame_time - elapsed
        if sleep_time > 0:
            # Use high-precision sleep (timer resolution was set to 1ms above)
            if sleep_time >= 0.001:  # Only sleep if we have at least 1ms to spare
                time.sleep(sleep_time)
            else:
                # For sub-millisecond precision, use busy wait (only for very short periods)
                end_time = start_time + target_frame_time
                while time.perf_counter() < end_time:
                    pass
    
    # CLEANUP: Restore Windows timer precision when thread exits
    try:
        ctypes.windll.winmm.timeEndPeriod(1)
        logger.info("🎯 CLEANUP: Restored Windows timer resolution")
    except Exception as e:
        logger.debug(f"Could not restore timer resolution: {e}")
        
    logger.info("✅ PEDAL PROCESSING: Thread completed successfully")

def global_handbrake_polling_loop():
    """The main loop for polling handbrake and updating UI queue."""
    # PERFORMANCE FIX: Imports moved to module level
    
    logger.info("🤚 HANDBRAKE PROCESSING: Starting at 100Hz")
    
    loop_count = 0
    target_frequency = 100  # 100Hz for handbrake (less critical than pedals)
    target_frame_time = 1.0 / target_frequency  # 10ms per frame
    
    while not global_handbrake_stop_event.is_set():
        start_time = time.perf_counter()
        loop_count += 1

        # Read handbrake data
        if global_handbrake_hardware:
            try:
                handbrake_data = global_handbrake_hardware.read_handbrake()
                
                # ULTRA-OPTIMIZED: Single queue put (maxsize=1 auto-drops old data)
                try:
                    global_handbrake_data_queue.put_nowait(handbrake_data)  # Auto-drops if queue full
                except:
                    pass  # Queue full, old data auto-dropped - continue processing
                    
            except Exception as e:
                if loop_count % 1000 == 0:  # Log errors occasionally
                    logger.error(f"Error reading handbrake: {e}")

        # Performance timing
        elapsed = time.perf_counter() - start_time
        
        # Performance logging every 10 seconds
        if loop_count % (target_frequency * 10) == 0:
            actual_frequency = 1.0 / elapsed if elapsed > 0 else float('inf')
            logger.debug(f"✅ HANDBRAKE PERFORMANCE: {actual_frequency:.0f}Hz")
        
        # Sleep for precise timing
        sleep_time = target_frame_time - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

def stop_global_handbrake_thread():
    """Stop the global handbrake processing thread."""
    global global_handbrake_thread, global_handbrake_stop_event
    
    if global_handbrake_thread is not None and global_handbrake_thread.is_alive():
        logger.info("🛑 Stopping global handbrake thread...")
        global_handbrake_stop_event.set()
        global_handbrake_thread.join(timeout=2.0)
        if global_handbrake_thread.is_alive():
            logger.warning("Handbrake thread did not stop gracefully")
        else:
            logger.info("✅ Global handbrake thread stopped successfully")

def stop_global_pedal_thread():
    """Stop the global pedal processing thread."""
    global global_pedal_thread, global_pedal_stop_event
    
    if global_pedal_thread is not None and global_pedal_thread.is_alive():
        logger.info("🛑 Stopping global pedal thread...")
        global_pedal_stop_event.set()
        global_pedal_thread.join(timeout=2.0)
        if global_pedal_thread.is_alive():
            logger.warning("Pedal thread did not stop gracefully")
        else:
            logger.info("✅ Global pedal thread stopped successfully")

def get_global_hardware():
    """Get the global hardware instance."""
    return global_hardware

def get_global_output():
    """Get the global vJoy output instance."""
    return global_output

def get_global_pedal_data_queue():
    """Get the global pedal data queue for UI updates."""
    return global_pedal_data_queue

def get_global_handbrake_hardware():
    """Get the global handbrake hardware instance."""
    return global_handbrake_hardware

def get_global_handbrake_data_queue():
    """Get the global handbrake data queue for UI updates."""
    return global_handbrake_data_queue

def initialize_global_iracing_connection():
    """Initialize the global iRacing connection that all screens can access."""
    global global_iracing_api
    
    try:
        if global_iracing_api is None:
            logger.info("🏁 Initializing global iRacing connection...")
            
            # Import the SimpleIRacingAPI
            from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
            global_iracing_api = SimpleIRacingAPI()
            
            # Set up telemetry saving with Supabase integration
            logger.info("🎯 Setting up telemetry saving for global iRacing connection...")
            
            # Get Supabase client for saving telemetry data
            try:
                from trackpro.database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                
                # If deferred initialization prevented client creation, try again after forcing init
                if not supabase_client:
                    logger.info("🚀 TELEMETRY SETUP: Supabase client not ready, triggering initialization...")
                    # Force initialization by trying again
                    supabase_client = get_supabase_client()
                
                if supabase_client:
                    logger.info("✅ Got Supabase client for global telemetry saving")
                    
                    # Create lap saver for the global connection
                    from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
                    global_lap_saver = IRacingLapSaver()
                    global_lap_saver.set_supabase_client(supabase_client)
                    
                    # Set user ID if authenticated
                    try:
                        from trackpro.auth.user_manager import get_current_user
                        user = get_current_user()
                        if user is None:
                            # User manager not ready yet - skip user ID setting
                            logger.info("ℹ️ User manager not ready yet - skipping user ID setting")
                        elif user and hasattr(user, 'id') and user.is_authenticated:
                            user_id = user.id
                            global_lap_saver.set_user_id(user_id)
                            logger.info(f"✅ Set user ID for global lap saver: {user_id}")
                        else:
                            logger.info("ℹ️ No authenticated user - running in offline mode")
                    except Exception as user_error:
                        logger.warning(f"Could not get user for global lap saver: {user_error}")
                    
                    # Connect lap saver to iRacing API
                    if hasattr(global_iracing_api, 'set_lap_saver'):
                        global_iracing_api.set_lap_saver(global_lap_saver)
                        logger.info("✅ Connected global lap saver to iRacing API")
                    
                    # Set up deferred monitoring params for background session monitoring
                    user_id_for_monitoring = 'anonymous'
                    if user and hasattr(user, 'id') and user.is_authenticated:
                        user_id_for_monitoring = user.id
                    global_iracing_api._deferred_monitor_params = {
                        'supabase_client': supabase_client,
                        'user_id': user_id_for_monitoring,
                        'lap_saver': global_lap_saver
                    }
                    logger.info("✅ Global telemetry saving configured")
                else:
                    logger.warning("⚠️ No Supabase client - telemetry will not save to cloud")
            except Exception as save_error:
                logger.error(f"❌ Error setting up telemetry saving: {save_error}")
            
            # Start telemetry monitoring
            global_iracing_api._start_telemetry_timer()
            
            # Start deferred monitoring for background session tracking
            logger.info("🚀 Starting deferred iRacing session monitoring...")
            monitoring_started = global_iracing_api.start_deferred_monitoring()
            if monitoring_started:
                logger.info("✅ Deferred monitoring started successfully")
            else:
                logger.warning("⚠️ Failed to start deferred monitoring - running in basic mode only")
            
            logger.info("🏁 Global iRacing connection initialized with telemetry saving")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize global iRacing connection: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

def get_global_iracing_api():
    """Get the global iRacing API instance. All screens should use this to access telemetry data."""
    global global_iracing_api
    return global_iracing_api

def cleanup_global_handbrake_system():
    """Clean up the global handbrake system when shutting down."""
    global global_handbrake_hardware, global_handbrake_thread, global_handbrake_stop_event
    
    try:
        logger.info("🤚 Cleaning up global handbrake system...")
        
        # Stop the handbrake thread first
        stop_global_handbrake_thread()
        
        # Save calibration before cleaning up hardware
        if global_handbrake_hardware:
            try:
                logger.info("💾 Saving handbrake calibration data...")
                calibration_data = global_handbrake_hardware.calibration
                if calibration_data:
                    global_handbrake_hardware.save_calibration(calibration_data)
                logger.info("✅ Handbrake calibration data saved")
            except Exception as e:
                logger.error(f"❌ Error saving handbrake calibration: {e}")
        
        # Clean up hardware
        if global_handbrake_hardware:
            try:
                logger.info("🧹 Cleaning up handbrake hardware...")
                global_handbrake_hardware.cleanup()
                global_handbrake_hardware = None
                logger.info("✅ Handbrake hardware cleaned up")
            except Exception as e:
                logger.error(f"❌ Error cleaning up handbrake hardware: {e}")
        
        logger.info("✅ Global handbrake system cleaned up")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up global handbrake system: {e}")

def cleanup_global_pedal_system():
    """Clean up the global pedal system when shutting down."""
    global global_hardware, global_output, global_hidhide, global_pedal_thread, global_pedal_stop_event
    
    try:
        logger.info("🎮 Cleaning up global pedal system...")
        
        # Stop the pedal thread first
        stop_global_pedal_thread()
        
        # Clean up vJoy output
        if global_output:
            try:
                logger.info("🕹️ Releasing vJoy device...")
                output = global_output
                global_output = None
                del output
                logger.info("✅ vJoy device released")
            except Exception as e:
                logger.error(f"❌ Error releasing vJoy device: {e}")
        
        # Save calibration before cleaning up hardware
        if global_hardware:
            try:
                logger.info("💾 Saving calibration data...")
                global_hardware.save_calibration(global_hardware.calibration)
                logger.info("✅ Calibration data saved")
            except Exception as e:
                logger.error(f"❌ Error saving calibration: {e}")
        
        # Disable HidHide cloaking
        if global_hidhide:
            logger.info("🔓 Disabling HidHide cloaking...")
            try:
                # Use CLI as primary method - most reliable
                cli_result = global_hidhide._run_cli(["--cloak-off"])
                logger.info(f"✅ Cloak disabled via CLI: {cli_result}")
                
                # Also try to unhide specific devices as a backup
                device_name = "Sim Coaches P1 Pro Pedals"
                matching_devices = global_hidhide.find_all_matching_devices(device_name)
                for device_path in matching_devices:
                    try:
                        unhide_result = global_hidhide._run_cli(["--unhide-by-id", device_path])
                        logger.info(f"✅ Unhid device via CLI: {unhide_result}")
                    except Exception as e2:
                        logger.error(f"❌ Error unhiding device via CLI: {e2}")
                
            except Exception as e:
                logger.error(f"❌ Error disabling HidHide cloaking: {e}")
        
        # Clean up pygame resources
        if global_hardware and hasattr(global_hardware, 'pedals_connected') and global_hardware.pedals_connected:
            try:
                import pygame
                logger.info("🎮 Cleaning up pygame resources...")
                # Release the joystick object first
                if hasattr(global_hardware, 'joystick') and global_hardware.joystick:
                    try:
                        global_hardware.joystick.quit()
                    except:
                        pass
                    global_hardware.joystick = None
                pygame.joystick.quit()
                logger.info("✅ Pygame resources cleaned up")
            except Exception as e:
                logger.error(f"❌ Error cleaning up pygame resources: {e}")
        
        # Clear global references
        global_hardware = None
        global_hidhide = None
        
        logger.info("✅ Global pedal system cleaned up")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up global pedal system: {e}")

def cleanup_global_iracing_connection():
    """Clean up the global iRacing connection when shutting down."""
    global global_iracing_api
    
    try:
        if global_iracing_api:
            logger.info("🏁 Cleaning up global iRacing connection...")
            
            # First stop the session monitoring thread
            try:
                from trackpro.race_coach.iracing_session_monitor import stop_monitoring
                logger.info("🛑 Stopping iRacing session monitor...")
                stop_monitoring()
                logger.info("✅ iRacing session monitor stopped")
            except Exception as monitor_error:
                logger.error(f"❌ Error stopping session monitor: {monitor_error}")
            
            # Stop lap saver worker if it exists
            try:
                if hasattr(global_iracing_api, 'lap_saver') and global_iracing_api.lap_saver:
                    logger.info("🛑 Stopping lap saver worker...")
                    if hasattr(global_iracing_api.lap_saver, '_save_worker') and global_iracing_api.lap_saver._save_worker:
                        global_iracing_api.lap_saver._save_worker.stop()
                        logger.info("✅ Lap saver worker stopped")
            except Exception as lap_error:
                logger.error(f"❌ Error stopping lap saver: {lap_error}")
            
            # Then disconnect the API
            global_iracing_api.disconnect()
            global_iracing_api = None
            
            # Force cleanup any remaining iRacing SDK instances
            try:
                import irsdk
                # Try to shutdown any remaining iRacing SDK instances
                logger.info("🧹 Final iRacing SDK cleanup...")
                # This ensures the SDK properly releases resources
                temp_ir = irsdk.IRSDK()
                temp_ir.shutdown()
                logger.info("✅ Final iRacing SDK cleanup completed")
            except Exception as sdk_error:
                logger.error(f"❌ Error in final SDK cleanup: {sdk_error}")
            
            logger.info("✅ Global iRacing connection cleaned up")
    except Exception as e:
        logger.error(f"❌ Error cleaning up global iRacing connection: {e}")

def cleanup_all_global_systems():
    """Clean up all global systems when shutting down."""
    logger.info("🧹 Starting comprehensive system cleanup...")
    cleanup_global_pedal_system()
    cleanup_global_handbrake_system()
    cleanup_global_iracing_connection()
    logger.info("✅ All global systems cleaned up")

def main(app: Optional[QApplication] = None, existing_splash = None):
    """Launch the modern TrackPro UI with full authentication system and iRacing telemetry."""
    start_time = time.time()
    logger.info("🚀 Starting Modern TrackPro UI with Authentication and iRacing Telemetry...")
    
    # Single-instance guard
    if not _acquire_single_instance_lock():
        logger.info("⚠️ TrackPro is already running. Exiting this instance.")
        return 0

    # Create QApplication only if not provided; auto OpenGL fallback on failure
    created_app = False
    if app is None:
        try:
            app = QApplication(sys.argv)
            created_app = True
        except Exception as gl_err:
            logger.warning(f"OpenGL init failed with desktop GL: {gl_err}. Falling back to software OpenGL.")
            try:
                from trackpro.config import config as global_config
                # Persist fallback and re-run
                if hasattr(global_config, 'set_prefer_software_opengl'):
                    global_config.set_prefer_software_opengl(True)
            except Exception:
                pass
            # Set attribute and retry
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
            app = QApplication(sys.argv)
            created_app = True
    # Centralize app identity here to avoid duplicates elsewhere
    from trackpro import __version__ as TRACKPRO_VERSION
    app.setApplicationName("TrackPro by Sim Coaches")
    app.setApplicationVersion(TRACKPRO_VERSION)
    app.setOrganizationName("Sim Coaches")
    app.setOrganizationDomain("simcoaches.com")

    # Global font: Product Sans (available in repo)
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(base_dir, "ui_resources", "fonts", "google-sans-cufonfonts")
        loaded = []
        for fname in [
            "ProductSans-Regular.ttf",
            "ProductSans-Bold.ttf",
            "ProductSans-Italic.ttf",
            "ProductSans-Medium.ttf",
        ]:
            fpath = os.path.join(font_dir, fname)
            if os.path.exists(fpath):
                loaded_id = QFontDatabase.addApplicationFont(fpath)
                loaded.append((fname, loaded_id))
        if loaded:
            app.setFont(QFont("Product Sans", 11))
            logger.info(f"✅ Loaded Product Sans fonts: {[n for n,_ in loaded]}")
        else:
            logger.warning("⚠️ Product Sans fonts not found; using system default")
    except Exception as font_err:
        logger.warning(f"⚠️ Could not load Product Sans fonts: {font_err}")
    
    # Set application icon to prevent Python icon from showing in taskbar
    try:
        # Try ICO first (user preference)
        icon_path = os.path.join(os.path.dirname(__file__), "trackpro", "resources", "icons", "trackpro_tray-1.ico")
        logger.info(f"🔍 Looking for application icon at: {icon_path}")
        logger.info(f"🔍 File exists: {os.path.exists(icon_path)}")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            icon = QIcon(icon_path)
            app.setWindowIcon(icon)
            logger.info(f"✅ Set application icon from: {icon_path}")
            logger.info(f"✅ Icon is null: {icon.isNull()}")
            
            # Also set the icon as a property to ensure it persists
            app.setProperty("windowIcon", icon)
            logger.info("✅ Set application icon as property")
        else:
            # Try PNG as fallback
            png_icon_path = os.path.join(os.path.dirname(__file__), "trackpro", "resources", "icons", "trackpro_tray.png")
            logger.info(f"🔍 Looking for PNG fallback at: {png_icon_path}")
            if os.path.exists(png_icon_path):
                from PyQt6.QtGui import QIcon
                icon = QIcon(png_icon_path)
                app.setWindowIcon(icon)
                logger.info(f"✅ Set application icon from: {png_icon_path}")
                logger.info(f"✅ Icon is null: {icon.isNull()}")
                
                # Also set the icon as a property to ensure it persists
                app.setProperty("windowIcon", icon)
                logger.info("✅ Set application icon as property")
            else:
                logger.warning("⚠️ Could not find application icon")
    except Exception as e:
        logger.warning(f"⚠️ Error setting application icon: {e}")
        import traceback
        logger.warning(f"⚠️ Traceback: {traceback.format_exc()}")
    
    # PERFORMANCE: Use existing splash if provided, otherwise create
    from PyQt6.QtWidgets import QSplashScreen, QLabel
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap, QPainter

    if existing_splash is not None:
        splash = existing_splash
        try:
            splash.showMessage("Initializing TrackPro...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
            app.processEvents()
        except Exception:
            pass
    else:
        splash_pixmap = _build_brand_splash_pixmap()
        splash = QSplashScreen(splash_pixmap)
        splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        splash.show()
        splash.showMessage("Initializing TrackPro...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
    
    # Register cleanup function to run when app shuts down
    app.aboutToQuit.connect(cleanup_all_global_systems)
    
    try:
        # Set up OAuth handler (non-blocking)
        splash.showMessage("Setting up authentication system...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        from trackpro.auth import oauth_handler
        oauth_handler_instance = oauth_handler.OAuthHandler()

        # Create the main application and show window ASAP
        splash.showMessage("Loading database connections...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        from trackpro.modern_main import ModernTrackProApp
        logger.info("🏗️ Creating modern TrackPro application with non-blocking authentication...")
        splash.showMessage("Creating main application...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        trackpro_app = ModernTrackProApp(oauth_handler=oauth_handler_instance, start_time=start_time, app=app)

        # Initialize optimized user service for faster startups  
        splash.showMessage("Loading user profiles...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        try:
            from trackpro.ui.optimized_user_service import get_user_service
            user_service = get_user_service()
            user_service.preload_current_user()
            logger.info("🚀 STARTUP OPTIMIZATION: User service initialized with background preloading")
        except Exception as e:
            logger.debug(f"User service preload failed (normal during first startup): {e}")

        # Show UI is ready
        splash.showMessage("Preparing interface...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()

        # Ensure splash stays until UI is ready (handled by readiness + visibility check below)

        # PERFORMANCE: Defer non-critical UI initialization until after window is shown
        def defer_non_critical_init():
            """Initialize non-critical components after main UI is ready."""
            try:
                # These can happen after the main window is visible
                if hasattr(trackpro_app, 'main_window') and trackpro_app.main_window:
                    logger.info("🔄 Starting deferred non-critical initialization...")
                    # Any additional non-critical setup can go here
                    logger.info("✅ Deferred non-critical initialization completed")
            except Exception as e:
                logger.debug(f"Deferred initialization error (non-critical): {e}")
        
        # Schedule deferred initialization with correct import
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, defer_non_critical_init)

        # Start background initialization without blocking the UI
        splash.showMessage("Starting background initialization...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        logger.info("🚀 Starting background initialization of hardware and telemetry...")

        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        futures = {
            'pedal': executor.submit(initialize_global_pedal_system),
            'handbrake': executor.submit(initialize_global_handbrake_system),
            'iracing': executor.submit(initialize_global_iracing_connection),
        }

        # Periodically attach globals to the app as they become available
        from PyQt6.QtCore import QTimer
        
        # Progress tracking for splash updates
        _splash_progress = {"step": 0, "total": 3}
        
        def _attach_when_ready():
            should_reschedule = False
            progress_made = False
            try:
                # Attach pedal system once
                if not getattr(trackpro_app, "_pedal_attached", False):
                    if hasattr(trackpro_app, 'set_global_pedal_system') and get_global_hardware() and get_global_output() and get_global_pedal_data_queue():
                        trackpro_app.set_global_pedal_system(get_global_hardware(), get_global_output(), get_global_pedal_data_queue())
                        setattr(trackpro_app, "_pedal_attached", True)
                        _splash_progress["step"] += 1
                        progress_made = True
                    else:
                        should_reschedule = True

                # Attach handbrake system once
                if not getattr(trackpro_app, "_handbrake_attached", False):
                    if hasattr(trackpro_app, 'set_global_handbrake_system') and get_global_handbrake_hardware() and get_global_handbrake_data_queue():
                        trackpro_app.set_global_handbrake_system(get_global_handbrake_hardware(), get_global_handbrake_data_queue())
                        setattr(trackpro_app, "_handbrake_attached", True)
                        _splash_progress["step"] += 1
                        progress_made = True
                    else:
                        should_reschedule = True

                # Attach iRacing API once
                if not getattr(trackpro_app, "_iracing_attached", False):
                    if hasattr(trackpro_app, 'set_global_iracing_api') and get_global_iracing_api():
                        trackpro_app.set_global_iracing_api(get_global_iracing_api())
                        setattr(trackpro_app, "_iracing_attached", True)
                        _splash_progress["step"] += 1
                        progress_made = True
                    else:
                        should_reschedule = True
                
                # Update splash with progress
                if progress_made:
                    step = _splash_progress["step"]
                    total = _splash_progress["total"]
                    try:
                        if step == 1:
                            splash.showMessage("Hardware systems loading... (1/3)", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
                        elif step == 2:
                            splash.showMessage("Racing systems loading... (2/3)", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
                        elif step == 3:
                            splash.showMessage("Finalizing setup... (3/3)", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
                        app.processEvents()
                    except Exception:
                        pass
                        
            except Exception:
                # In case of transient errors, try again shortly
                should_reschedule = True
            finally:
                # Only keep checking while not all systems are attached
                if should_reschedule:
                    QTimer.singleShot(500, _attach_when_ready)

        QTimer.singleShot(500, _attach_when_ready)

        # Keep executor alive for the duration of startup
        try:
            setattr(trackpro_app, "_background_init_executor", executor)
        except Exception:
            pass

        # Close splash only when the main window becomes visible AND a minimum time has elapsed (prevents flashing)
        from PyQt6.QtCore import QTimer
        splash_shown_t0 = time.perf_counter()
        min_visible_seconds = 2.5  # Increased from 0.8s to 2.5s for better UX
        _ui_ready_flag = {'ready': False}

        try:
            if hasattr(trackpro_app, 'window') and hasattr(trackpro_app.window, 'ui_ready'):
                trackpro_app.window.ui_ready.connect(lambda: _ui_ready_flag.__setitem__('ready', True))
        except Exception:
            pass

        def _close_splash_when_ready():
            try:
                elapsed = time.perf_counter() - splash_shown_t0
                if (getattr(trackpro_app, 'window', None) and trackpro_app.window.isVisible() and _ui_ready_flag['ready'] and elapsed >= min_visible_seconds):
                    # Show final "Ready!" message briefly before closing
                    splash.showMessage("Ready!", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
                    app.processEvents()
                    QTimer.singleShot(500, lambda: splash.close())  # Close after 0.5s delay
                else:
                    QTimer.singleShot(500, _close_splash_when_ready)
            except Exception:
                QTimer.singleShot(2000, lambda: splash.close())
        QTimer.singleShot(500, _close_splash_when_ready)

        total_startup_time = time.time() - start_time
        logger.info(f"✅ Modern TrackPro UI initial window ready in {total_startup_time:.2f} seconds (background init continues)")

        # Install a simple crash handler to write a single report
        try:
            import sys as _sys
            import traceback as _traceback
            from pathlib import Path as _Path
            def _except_hook(exc_type, exc, tb):
                try:
                    local_appdata = os.getenv('LOCALAPPDATA') or os.path.join(Path.home(), 'AppData', 'Local')
                    crash_dir = _Path(local_appdata) / 'TrackPro' / 'crash'
                    crash_dir.mkdir(parents=True, exist_ok=True)
                    crash_file = crash_dir / 'last_crash.txt'
                    with open(crash_file, 'w', encoding='utf-8') as f:
                        f.write(''.join(_traceback.format_exception(exc_type, exc, tb)))
                except Exception:
                    pass
                # Also log
                logger.error('Unhandled exception', exc_info=(exc_type, exc, tb))
            _sys.excepthook = _except_hook
        except Exception:
            pass

        return trackpro_app.run()
        
    except ImportError as e:
        logger.error(f"❌ Failed to import required modules: {e}")
        # Fallback to basic modern UI without authentication
        logger.info("🔄 Falling back to basic modern UI...")
        try:
            from trackpro.ui.modern import ModernMainWindow
            
            window = ModernMainWindow()
            
            # Try to make global iRacing API available to the fallback window too
            if hasattr(window, 'set_global_iracing_api'):
                window.set_global_iracing_api(get_global_iracing_api())
            
            # Try to make global pedal system available to the fallback window too
            if hasattr(window, 'set_global_pedal_system'):
                window.set_global_pedal_system(get_global_hardware(), get_global_output(), get_global_pedal_data_queue())
            
            # Try to make global handbrake system available to the fallback window too
            if hasattr(window, 'set_global_handbrake_system'):
                window.set_global_handbrake_system(get_global_handbrake_hardware(), get_global_handbrake_data_queue())
            
            # Ensure window cleanup is called when app quits
            app.aboutToQuit.connect(lambda: window.cleanup() if hasattr(window, 'cleanup') else None)
            
            window.show()
            window.raise_()
            window.activateWindow()
            
            return app.exec()
        except Exception as fallback_e:
            logger.error(f"❌ Fallback also failed: {fallback_e}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error launching modern UI: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Developer-friendly bootstrap: show splash immediately, then hand off
    # Critical Qt attributes were set above at import-time.
    app = QApplication(sys.argv)
    splash = _show_instant_splash(app)
    rc = 0
    try:
        rc = main(app=app, existing_splash=splash)
    except Exception:
        import traceback
        print("\n\n==== TrackPro crashed during startup ====")
        traceback.print_exc()
        print("========================================\n")
        rc = 1

    if getattr(sys, 'frozen', False) and rc != 0:
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
    sys.exit(rc)