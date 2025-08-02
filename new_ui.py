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
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# CRITICAL: Set Qt attributes BEFORE any QApplication instance can be created AND before importing QtWebEngineWidgets
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        
        # Initialize data queue for UI updates
        from queue import Queue
        from threading import Event
        global_handbrake_data_queue = Queue()
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
        
        # Initialize data queue for UI updates
        from queue import Queue
        from threading import Event
        global_pedal_data_queue = Queue()
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
    """The main loop for polling pedals and sending output to vJoy - ULTRA HIGH PERFORMANCE."""
    import time
    import ctypes
    from queue import Empty
    
    # Set absolute maximum thread priority for Windows
    try:
        thread_handle = ctypes.windll.kernel32.GetCurrentThread()
        # Set to TIME_CRITICAL priority (highest possible)
        if not ctypes.windll.kernel32.SetThreadPriority(thread_handle, 15):  # THREAD_PRIORITY_TIME_CRITICAL
            logger.warning("Failed to set pedal thread priority to TIME_CRITICAL.")
        else:
            logger.info("🏎️ MODERN PEDAL THREAD: Set to TIME_CRITICAL priority for ultra-low latency")
            
        # Set process priority to HIGH for the entire TrackPro process
        process_handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(process_handle, 0x00000080)  # HIGH_PRIORITY_CLASS
        logger.info("🚀 MODERN PROCESS: Set TrackPro to HIGH priority class")
        
    except Exception as e:
        logger.warning(f"Could not set thread/process priority on Windows: {e}")

    # Ultra-fast pedal processing variables
    last_vjoy_values = {'throttle': -1, 'brake': -1, 'clutch': -1, 'handbrake': -1}
    loop_count = 0
    performance_log_interval = 10000  # Log every 10 seconds at 1000Hz
    target_frequency = 1000  # 1000Hz for ultimate responsiveness
    target_frame_time = 1.0 / target_frequency  # 1ms per frame
    
    logger.info(f"🎯 MODERN ULTRA-FAST PEDAL PROCESSING: Starting at {target_frequency}Hz (1ms response time)")
    
    # Performance tracking
    slow_frame_count = 0
    missed_frame_count = 0
    
    while not global_pedal_stop_event.is_set():
        start_time = time.perf_counter()
        loop_count += 1

        # CRITICAL PATH: Ultra-fast pedal reading
        if global_hardware:
            raw_values = global_hardware.read_pedals()
            
            # OPTIMIZED: Only update UI queue if needed (don't block on UI)
            try:
                # Clear old data from queue to prevent lag accumulation
                while not global_pedal_data_queue.empty():
                    try:
                        global_pedal_data_queue.get_nowait()
                    except Empty:
                        break
                # Add latest data non-blocking
                global_pedal_data_queue.put_nowait(raw_values)
            except:
                pass  # Don't let UI queue issues slow down pedal processing

            # ULTRA-FAST: Direct calibration and vJoy output
            if global_output:
                vjoy_values = {}
                for pedal in ['throttle', 'brake', 'clutch']:
                    raw_value = raw_values.get(pedal, 0)
                    output_value = global_hardware.apply_calibration(pedal, raw_value)
                    vjoy_values[pedal] = int(output_value)
                
                # Get handbrake value if available
                handbrake_value = 0
                if global_handbrake_hardware:
                    try:
                        handbrake_data = global_handbrake_hardware.read_handbrake()
                        handbrake_raw = handbrake_data.get('handbrake', 0)
                        handbrake_value = global_handbrake_hardware.apply_calibration('handbrake', handbrake_raw)
                    except:
                        handbrake_value = 0
                
                # CRITICAL OPTIMIZATION: Only send to vJoy if values changed
                current_values = {**vjoy_values, 'handbrake': handbrake_value}
                values_changed = current_values != last_vjoy_values
                if values_changed:
                    global_output.update_axis(vjoy_values['throttle'], vjoy_values['brake'], vjoy_values['clutch'], handbrake_value)
                    last_vjoy_values = current_values.copy()

        # PERFORMANCE MONITORING: Track actual performance
        elapsed = time.perf_counter() - start_time
        
        if elapsed > target_frame_time * 2:  # More than 2ms
            slow_frame_count += 1
        if elapsed > target_frame_time * 5:  # More than 5ms
            missed_frame_count += 1
        
        # Performance logging every 10 seconds
        if loop_count % performance_log_interval == 0:
            actual_frequency = 1.0 / elapsed if elapsed > 0 else float('inf')
            slow_percentage = (slow_frame_count / performance_log_interval) * 100
            miss_percentage = (missed_frame_count / performance_log_interval) * 100
            
            if miss_percentage > 1.0:
                logger.error(f"🚨 MODERN PEDAL LAG: {miss_percentage:.1f}% severe delays, {actual_frequency:.0f}Hz actual")
            elif slow_percentage > 10.0:
                logger.warning(f"⚠️ MODERN PEDAL PERFORMANCE: {slow_percentage:.1f}% slow frames")
            else:
                logger.debug(f"✅ MODERN PEDAL PERFORMANCE: {actual_frequency:.0f}Hz, {elapsed*1000:.1f}ms")
            
            # Reset counters
            slow_frame_count = 0
            missed_frame_count = 0
        
        # PRECISION TIMING: Sleep for exact timing
        sleep_time = target_frame_time - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

def global_handbrake_polling_loop():
    """The main loop for polling handbrake and updating UI queue."""
    import time
    from queue import Empty
    
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
                
                # Update UI queue (non-blocking)
                try:
                    # Clear old data from queue to prevent lag accumulation
                    while not global_handbrake_data_queue.empty():
                        try:
                            global_handbrake_data_queue.get_nowait()
                        except Empty:
                            break
                    # Add latest data non-blocking
                    global_handbrake_data_queue.put_nowait(handbrake_data)
                except:
                    pass  # Don't let UI queue issues slow down handbrake processing
                    
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
                        if user and hasattr(user, 'id') and user.is_authenticated:
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
                    global_iracing_api._deferred_monitor_params = {
                        'supabase_client': supabase_client,
                        'user_id': user.id if user and hasattr(user, 'id') and user.is_authenticated else 'anonymous',
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
    if global_iracing_api is None:
        logger.warning("⚠️ Global iRacing API not initialized yet!")
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

def main():
    """Launch the modern TrackPro UI with full authentication system and iRacing telemetry."""
    start_time = time.time()
    logger.info("🚀 Starting Modern TrackPro UI with Authentication and iRacing Telemetry...")
    
    # STARTUP OPTIMIZATION: Enable fast startup mode to skip heavy operations
    os.environ['TRACKPRO_FAST_STARTUP'] = 'true'
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("TrackPro Modern")
    app.setApplicationVersion("1.5.5-modern")
    app.setOrganizationName("Sim Coaches")
    app.setOrganizationDomain("simcoaches.com")
    
    # PERFORMANCE: Show startup progress to user
    from PyQt6.QtWidgets import QSplashScreen, QLabel
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap, QPainter, QFont
    
    # Create a simple splash screen
    splash_pixmap = QPixmap(400, 200)
    splash_pixmap.fill(Qt.GlobalColor.darkGray)
    
    # Draw TrackPro logo/text on splash screen
    painter = QPainter(splash_pixmap)
    painter.setPen(Qt.GlobalColor.white)
    painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
    painter.drawText(splash_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "TrackPro\nStarting...")
    painter.end()
    
    splash = QSplashScreen(splash_pixmap)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
    splash.show()
    splash.showMessage("Initializing hardware systems...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    app.processEvents()
    
    # Register cleanup function to run when app shuts down
    app.aboutToQuit.connect(cleanup_all_global_systems)
    
    try:
        # Set up OAuth handler first (like run_app.py does)
        splash.showMessage("Setting up authentication...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        from trackpro.auth import oauth_handler
        oauth_handler_instance = oauth_handler.OAuthHandler()
        
        # PERFORMANCE OPTIMIZATION: Initialize hardware systems in parallel
        splash.showMessage("Initializing hardware systems...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        logger.info("🚀 Starting parallel initialization of hardware systems...")
        
        import concurrent.futures
        import threading
        
        # Create a thread pool for parallel initialization
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all hardware initialization tasks
            pedal_future = executor.submit(lambda: (
                logger.info("🎮 Initializing ULTRA-HIGH PERFORMANCE pedal system..."),
                initialize_global_pedal_system()
            ))
            
            handbrake_future = executor.submit(lambda: (
                logger.info("🤚 Initializing handbrake system..."),
                initialize_global_handbrake_system()
            ))
            
            iracing_future = executor.submit(lambda: (
                logger.info("🏁 Initializing global iRacing telemetry connection..."),
                initialize_global_iracing_connection()
            ))
            
            # Wait for all systems to complete (with timeout)
            try:
                concurrent.futures.wait([pedal_future, handbrake_future, iracing_future], timeout=30)
                logger.info("✅ All hardware systems initialized in parallel")
            except concurrent.futures.TimeoutError:
                logger.warning("⚠️ Some hardware systems took longer than 30 seconds to initialize")
            
            # Check for any exceptions
            for future_name, future in [("pedal", pedal_future), ("handbrake", handbrake_future), ("iracing", iracing_future)]:
                try:
                    future.result(timeout=1)  # Quick check for exceptions
                except Exception as e:
                    logger.error(f"❌ Error initializing {future_name} system: {e}")
        
        logger.info("🏁 Parallel hardware initialization completed")
        
        # Import the modern TrackPro app class
        splash.showMessage("Creating main application...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        from trackpro.modern_main import ModernTrackProApp
        
        # Create the modern TrackPro app with authentication and global iRacing access
        logger.info("🏗️ Creating modern TrackPro application with authentication...")
        trackpro_app = ModernTrackProApp(oauth_handler=oauth_handler_instance, start_time=start_time)
        
        # Make the global iRacing API available to the app
        if hasattr(trackpro_app, 'set_global_iracing_api'):
            trackpro_app.set_global_iracing_api(get_global_iracing_api())
        
        # Make the global pedal system available to the app
        if hasattr(trackpro_app, 'set_global_pedal_system'):
            trackpro_app.set_global_pedal_system(get_global_hardware(), get_global_output(), get_global_pedal_data_queue())
        
        # Make the global handbrake system available to the app
        if hasattr(trackpro_app, 'set_global_handbrake_system'):
            trackpro_app.set_global_handbrake_system(get_global_handbrake_hardware(), get_global_handbrake_data_queue())
        
        # Final initialization complete
        splash.showMessage("Ready to race!", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()
        
        # Close splash screen after a brief moment
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, splash.close)
        
        # Calculate total startup time
        total_startup_time = time.time() - start_time
        logger.info(f"✅ Modern TrackPro UI launched successfully in {total_startup_time:.2f} seconds!")
        
        # STARTUP OPTIMIZATION: Disable fast startup mode now that app is running
        if 'TRACKPRO_FAST_STARTUP' in os.environ:
            del os.environ['TRACKPRO_FAST_STARTUP']
        
        # Run the application
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
    sys.exit(main())