import irsdk
import time
import logging
import math
import threading
from pathlib import Path
from collections import deque
from .telemetry_saver import TelemetrySaver
# from .integrate_simple_timing import SimpleSectorTimingIntegration  # REMOVED: Use main sector timing instead
from .sector_timing import SectorTimingCollector
from PyQt5.QtCore import QObject, pyqtSignal
import queue

logger = logging.getLogger(__name__)

# Our simple state class similar to the example
class State:
    ir_connected = False
    last_car_setup_tick = -1

class SimpleIRacingAPI(QObject):
    """A simpler implementation of iRacing API based on the pyirsdk example."""
    
    # Define the signal
    sessionInfoUpdated = pyqtSignal(dict)
    
    def __init__(self):
        """Initialize the API."""
        super().__init__()
        self.ir = irsdk.IRSDK()
        self.state = State()
        self._is_connected = False
        self._connection_callbacks = []
        self._session_info_callbacks = []
        self._telemetry_callbacks = []
        self._session_info = {}
        self._last_driver_inputs_log = 0
        
        # Thread control event
        self._stop_event = threading.Event()
        self._telemetry_timer = None
        self._session_info_timer = None
        
        # Initialize telemetry saver
        self.telemetry_saver = TelemetrySaver()
        self._current_session_id = None
        
        # Add lap saver reference
        self.lap_saver = None
        
        # Initialize main sector timing (replaces deleted simple integration)
        self.sector_timing = SectorTimingCollector()
        logger.info("✅ Main sector timing initialized")
        
        # Telemetry rate tracking
        self._telemetry_count = 0
        self._telemetry_start_time = None
        self._last_rate_check_time = None
        
        # Add flag to track if disconnect has been called
        self._disconnected = False
        
        # CRITICAL FIX: Initialize telemetry log time to 0.0 instead of None to prevent TypeError
        self._last_telemetry_log_time = 0.0
        
        # Add deferred monitoring parameters
        self._deferred_monitor_params = None
        
        # Store current telemetry for external access (needed for ABS system)
        self.current_telemetry = {}
        
        # TASK 1.1: OPTIMIZED circular buffer for actual telemetry rate
        # Since actual rate may be lower than 60Hz, dynamically size buffer
        self.telemetry_buffer_seconds = 60
        self.telemetry_buffer_size = 360  # Start with smaller buffer, will auto-adjust
        self.telemetry_buffer = deque(maxlen=self.telemetry_buffer_size)
        self._buffer_lock = threading.Lock()
        self._last_buffer_resize = time.time()
        
        # PERFORMANCE FIX: Producer-Consumer Architecture
        # Fast producer thread only collects telemetry
        # Slow consumer threads handle processing
        self._telemetry_queue = queue.Queue(maxsize=1000)  # Buffer for worker threads
        self._processing_workers = []
        self._start_processing_workers()
        
        logger.info("SimpleIRacingAPI initialized with producer-consumer architecture")
    
    def __del__(self):
        """Clean up resources when this object is garbage collected."""
        try:
            logger.info("SimpleIRacingAPI.__del__ called - cleaning up resources")
            self.disconnect()
        except Exception as e:
            logger.error(f"Error in SimpleIRacingAPI.__del__: {e}")
    
    def connect(self, on_connected=None, on_disconnected=None, on_session_info_changed=None, on_telemetry_update=None):
        """Register callbacks. Connection is handled by the monitor thread."""
        logger.info("SimpleIRacingAPI.connect called - registering callbacks.")
        # Register callbacks if provided
        if on_connected: self.register_on_connection_changed(on_connected)
        if on_disconnected:
            def on_disconnected_wrapper(is_connected, session_info):
                if not is_connected: on_disconnected()
            self.register_on_connection_changed(on_disconnected_wrapper)
        # if on_session_info_changed: self.register_on_session_info_changed(on_session_info_changed) # Legacy
        if on_telemetry_update: self.register_on_telemetry_data(on_telemetry_update)

        # DO NOT attempt connection here - monitor thread handles it.
        # DO NOT start timers here - monitor thread handles session info, telemetry timer is separate.
        # self._start_telemetry_timer() # Telemetry timer can start if needed, but monitor should confirm connection first.
        logger.info("Callbacks registered. Waiting for monitor thread to establish connection.")
        return True # Indicate registration happened, not actual connection.
    
    def _start_telemetry_timer(self):
        """Start a timer to process telemetry data periodically."""
        if not hasattr(self, '_telemetry_timer') or self._telemetry_timer is None:
            def telemetry_worker():
                logger.info("Starting telemetry worker thread")
                try:
                    loop_count = 0
                    connection_attempts = 0
                    while not self._stop_event.is_set():
                        loop_count += 1
                        # Reduce debug frequency - only log every 30 seconds instead of 5
                        if loop_count % 1800 == 0: # Log every 30 seconds approx
                             logger.debug(f"Telemetry worker loop running. Connected: {self._is_connected}")

                        # BUGFIX: Check for iRacing connection in basic mode
                        # If we don't have monitor thread, check iRacing directly
                        if not self._is_connected:
                            try:
                                # Try to initialize iRacing connection if not already connected
                                if not hasattr(self.ir, 'is_connected') or not self.ir.is_connected:
                                    startup_result = self.ir.startup()
                                    if startup_result and self.ir.is_connected:
                                        self._is_connected = True
                                        self.state.ir_connected = True
                                        logger.info("✅ Basic iRacing connection established")
                                        # Notify connection callbacks
                                        for callback in self._connection_callbacks:
                                            try:
                                                callback(True, {})
                                            except Exception as cb_error:
                                                logger.error(f"Error in connection callback: {cb_error}")
                            except Exception as conn_error:
                                connection_attempts += 1
                                # Only log connection errors every 60 seconds instead of 5
                                if connection_attempts % 3600 == 0:  # Log every 60 seconds
                                    logger.debug(f"iRacing not available: {conn_error}")

                        # Use internal _is_connected flag set by monitor or basic connection check above
                        if self._is_connected:
                            start_time = time.time()
                            self.process_telemetry()
                            processing_time = time.time() - start_time
                            
                                                        # Log processing time much less frequently - every 2 minutes instead of 10 seconds
                            if loop_count % 7200 == 0:  # Every ~2 minutes
                                logger.info(f"Telemetry processing time: {processing_time*1000:.2f}ms")
                            
                            # OPTIMIZED: Fixed 60Hz timing with minimal processing overhead
                            target_frame_time = 1/60  # 16.67ms per frame
                            sleep_time = max(0.005, target_frame_time - processing_time)  # Minimum 5ms sleep
                            self._stop_event.wait(sleep_time)
                        else:
                            # Sleep longer if not connected
                            self._stop_event.wait(0.5)
                            continue
                except Exception as e:
                    logger.error(f"Error in telemetry worker: {e}", exc_info=True)
                logger.info("Telemetry worker thread stopped")
            self._stop_event.clear()
            self._telemetry_timer = threading.Thread(target=telemetry_worker, daemon=True)
            self._telemetry_timer.start()
            logger.info("Telemetry worker thread started")
    
    def _start_session_info_timer(self):
        """(DISABLED) Start a timer to periodically update session info."""
        logger.info("Session info timer/polling is DISABLED in SimpleIRacingAPI.")
    
    def _update_session_info(self):
        """(DISABLED) Start a timer to periodically update session info."""
    
    def update_info_from_monitor(self, session_info: dict, is_connected: bool):
        """Update internal state from the monitor thread and emit signals."""
        connection_changed = False
        if self._is_connected != is_connected:
            self._is_connected = is_connected
            self.state.ir_connected = is_connected # Keep state in sync
            connection_changed = True
            logger.info(f"API Connection state updated by monitor: {self._is_connected}")
            
                        # If connected, properly initialize irsdk
            if self._is_connected:
                logger.info("Initializing/reinitializing irsdk connection...")
                try:
                    # Shutdown the irsdk instance if it exists
                    if self.ir:
                        try:
                            self.ir.shutdown()
                            logger.info("Shut down existing irsdk instance")
                        except Exception as e:
                            logger.warning(f"Error shutting down irsdk: {e}")
                    
                    # Create a new instance and initialize it
                    self.ir = irsdk.IRSDK()
                    startup_result = self.ir.startup()
                    logger.info(f"irsdk startup result: {startup_result}")
                    
                    # Check if initialization was successful
                    if startup_result and hasattr(self.ir, 'is_initialized') and self.ir.is_initialized:
                        logger.info("irsdk successfully initialized")
                    else:
                        logger.warning("irsdk initialization failed or incomplete")
                except Exception as e:
                    logger.error(f"Error during irsdk initialization: {e}")
                    
                # Start/Stop telemetry timer based on connection state
                if not self._telemetry_timer or not self._telemetry_timer.is_alive():
                    # Add a small delay to allow irsdk internal state to settle
                    logger.info("Connection established, waiting 3s before starting telemetry polling...")
                    time.sleep(3.0)
                    self._start_telemetry_timer()
            elif not self._is_connected and self._telemetry_timer and self._telemetry_timer.is_alive():
                # Signal telemetry thread to stop if disconnecting
                # self._stop_event.set() # This might be too aggressive if monitor reconnects quickly
                pass

        # Update session info dictionary
        session_changed = False
        if session_info != self._session_info:
             self._session_info = session_info.copy() # Update with a copy
             session_changed = True
             # Only log when session actually changes, not every update
             if not hasattr(self, '_session_info_debug_counter'):
                 self._session_info_debug_counter = 0
             self._session_info_debug_counter += 1
             
             # Only log session info updates every 10 minutes instead of every 50ms
             if self._session_info_debug_counter % 36000 == 0:  # 60Hz * 60s * 10min = 36000
                 logger.debug("🏁 Simple sector timing is ready (no SessionInfo processing needed)")

             # API session info updated by monitor: track={session_info.get('current_track')}, car={session_info.get('current_car')}
             if self._session_info_debug_counter % 36000 == 0:  # Every 10 minutes instead of every 50ms
                 logger.debug(f"API session info updated by monitor: track={session_info.get('current_track')}, car={session_info.get('current_car')}")
             
             # Simple sector timing is already initialized from data.txt, no SessionInfo needed
             # REMOVED: This was spamming every 50ms - debug message removed

        # Only emit signal and prepare payload when something actually changed
        if session_changed or connection_changed:
            # Prepare payload for signal
            signal_payload = {
                'is_connected': self._is_connected,
                'session_info': self._session_info.copy()
            }

            # Emit session info signal (containing connection status and session info)
            if hasattr(self, 'sessionInfoUpdated'):
                 self.sessionInfoUpdated.emit(signal_payload)
                 # REMOVED: This was spamming every 50ms - debug message removed
            else:
                 logger.warning("sessionInfoUpdated signal does not exist on API instance")
    
    def process_telemetry(self):
        """FAST PRODUCER: Collect telemetry data and queue for worker threads.
        
        This method is optimized for 60Hz collection rate by doing minimal work:
        1. Get essential telemetry fields from iRacing
        2. Store in circular buffer  
        3. Queue for worker threads
        
        All heavy processing (file I/O, database, callbacks) happens in worker threads.
        """
        # Check if we're connected first
        if not self._is_connected:
            return

        # FAST: Initialize telemetry rate tracking 
        if self._telemetry_start_time is None:
            self._telemetry_start_time = time.time()
            self._last_rate_check_time = self._telemetry_start_time
            self._telemetry_count = 0
            
        # FAST: Increment counter and occasional rate reporting
        self._telemetry_count += 1
        now = time.time()
        if now - self._last_rate_check_time >= 30.0:
            duration = now - self._telemetry_start_time
            rate = self._telemetry_count / duration if duration > 0 else 0
            logger.info(f"PRODUCER: Telemetry collection rate: {rate:.2f} Hz (collected {self._telemetry_count} points)")
            self._last_rate_check_time = now
            self._adjust_buffer_size_for_rate()

        # FAST: Basic connection check
        if not self.ir or not hasattr(self.ir, 'is_connected') or not self.ir.is_connected:
            return

        try:
            # FAST: Freeze buffer and extract essential fields only
            self.ir.freeze_var_buffer_latest()
            
            # FAST: Create minimal telemetry dictionary with only essential fields
            telemetry = {'timestamp': time.time()}
            
            # FAST: Extract fields with minimal overhead (no 'in' checks)
            essential_fields = [
                'SessionTime', 'LapDistPct', 'Lap', 'LapCompleted', 'Speed', 'RPM', 'Gear',
                'Throttle', 'Brake', 'Clutch', 'SteeringWheelAngle', 'LongAccel', 'LatAccel', 'YawRate',
                'VelocityX', 'VelocityY'  # Added for real track shape calculation
            ]
            
            for field in essential_fields:
                try:
                    telemetry[field] = self.ir[field]
                except:
                    telemetry[field] = 0
            
            # FAST: Extract Task 1.1 fields
            task_fields = [
                'LFshockDefl', 'RFshockDefl', 'LRshockDefl', 'RRshockDefl',
                'WheelLFRPM', 'WheelRFRPM', 'WheelLRRPM', 'WheelRRRPM',
                'LFtempCM', 'RFtempCM', 'LRtempCM', 'RRtempCM'
            ]
            
            for field in task_fields:
                try:
                    telemetry[field] = self.ir[field]
                except:
                    telemetry[field] = 0
            
            # FAST: Add derived fields and field name mapping
            track_position = telemetry.get('LapDistPct', 0.0)
            telemetry['sector_number'] = 1 if track_position < 0.333 else (2 if track_position < 0.667 else 3)
            
            # FAST: Add field aliases for worker compatibility
            telemetry['SessionTimeSecs'] = telemetry.get('SessionTime', 0)
            telemetry['speed'] = telemetry.get('Speed', 0)  # m/s for internal use
            
            # FAST: Store in circular buffer (minimal lock time)
            with self._buffer_lock:
                self.telemetry_buffer.append(telemetry.copy())

            # FAST: Queue for worker threads (non-blocking)
            try:
                self._telemetry_queue.put_nowait(telemetry)
            except queue.Full:
                # Queue is full - workers are behind, but don't block the producer
                if self._telemetry_count % 600 == 0:  # Log occasionally
                    logger.warning("Telemetry queue full - workers falling behind")
            
            # FAST: Store current telemetry for immediate access
            self.current_telemetry = telemetry

        except Exception as e:
            logger.error(f"Error in FAST telemetry producer: {e}")
            
        # Total time should be <5ms for 60Hz capability
    
    def register_on_connection_changed(self, callback):
        if callback not in self._connection_callbacks: self._connection_callbacks.append(callback)
    def register_on_session_info_changed(self, callback):
        if callback not in self._session_info_callbacks: self._session_info_callbacks.append(callback)
    def register_on_telemetry_data(self, callback):
        if callback not in self._telemetry_callbacks: self._telemetry_callbacks.append(callback)
    def is_connected(self):
        return self._is_connected # Use internal flag set by monitor
    def disconnect(self):
        """Disconnect from iRacing and clean up resources."""
        if self._disconnected:
            # Already disconnected, avoid duplicate cleanup
            return False
            
        logger.info("SimpleIRacingAPI.disconnect called - cleaning up resources")
        self._disconnected = True
        
        # Signal all threads to stop
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
        
        # Wait for telemetry thread to finish with timeout
        if hasattr(self, '_telemetry_timer') and self._telemetry_timer and self._telemetry_timer.is_alive():
            try:
                logger.info("Waiting for telemetry timer thread to finish...")
                self._telemetry_timer.join(timeout=2.0)
                if self._telemetry_timer.is_alive():
                    logger.warning("Telemetry timer thread did not finish in time")
            except Exception as e:
                logger.error(f"Error waiting for telemetry timer thread: {e}")
        
        # Clean up irsdk connection if connected
        if self.state.ir_connected and hasattr(self, 'ir') and self.ir:
            try:
                logger.info("Shutting down irsdk connection...")
                self.ir.shutdown()
                self.state.ir_connected = False
                self._is_connected = False
            except Exception as e:
                logger.error(f"Error shutting down irsdk connection: {e}")
        
        # Clean up any other resources
        # ...
        
        logger.info("SimpleIRacingAPI disconnected")
        return True
    
    def get_current_track(self):
        """Get the current track name."""
        return self._session_info.get('current_track', 'Unknown Track')
    
    def get_current_car(self):
        """Get the current car name."""
        return self._session_info.get('current_car', 'Unknown Car')
    
    def get_session_type(self):
        """Get the current session type."""
        return self._session_info.get('session_type', 'Unknown')
    
    def explore_telemetry_variables(self):
        """Explore and return available telemetry variables from iRacing.
        
        Returns:
            dict: A dictionary of categorized variables and their values
        """
        if not self.state.ir_connected or not self.ir:
            logger.warning("Cannot explore variables - not connected to iRacing")
            return {"error": "Not connected to iRacing"}
            
        logger.info("Exploring telemetry variables from iRacing...")
        result = {
            "car_info": {},
            "track_info": {},
            "session_info": {},
            "telemetry": {},
            "player_info": {},
            "misc": {}
        }
        
        try:
            # Try to get all variables from ir directly
            if hasattr(self.ir, 'get_all_vars'):
                all_vars = self.ir.get_all_vars()
                if all_vars:
                    # Categorize variables by name/content
                    for var_name, value in all_vars.items():
                        var_name_lower = var_name.lower()
                        
                        # Categorize based on name
                        if 'car' in var_name_lower:
                            result["car_info"][var_name] = str(value)
                        elif 'track' in var_name_lower:
                            result["track_info"][var_name] = str(value)
                        elif 'session' in var_name_lower or 'lap' in var_name_lower:
                            result["session_info"][var_name] = str(value)
                        elif 'speed' in var_name_lower or 'rpm' in var_name_lower or 'gear' in var_name_lower:
                            result["telemetry"][var_name] = str(value)
                        elif 'player' in var_name_lower or 'driver' in var_name_lower:
                            result["player_info"][var_name] = str(value)
                        else:
                            result["misc"][var_name] = str(value)
                    
                    logger.info(f"Found {sum(len(category) for category in result.values())} variables")
            
            # Specifically try to access PlayerInfo
            if hasattr(self.ir, 'PlayerInfo'):
                player_info = self.ir.PlayerInfo
                if isinstance(player_info, dict):
                    result["player_info"]["PlayerInfo"] = {k: str(v) for k, v in player_info.items()}
                    logger.info(f"Found PlayerInfo with {len(player_info)} fields")
            
            # Get session info structure
            if hasattr(self.ir, '_get_session_info'):
                session_info = self.ir._get_session_info()
                if session_info:
                    # Just capture the keys to avoid huge data
                    result["session_info"]["SessionInfo"] = {"keys": list(session_info.keys())}
                    logger.info(f"Found session info with sections: {list(session_info.keys())}")
                    
                    # Capture more detailed info about drivers
                    if 'DriverInfo' in session_info:
                        driver_info = session_info['DriverInfo']
                        if 'Drivers' in driver_info and isinstance(driver_info['Drivers'], list):
                            # Just get first driver to avoid too much data
                            first_driver = driver_info['Drivers'][0] if driver_info['Drivers'] else {}
                            result["player_info"]["FirstDriver"] = {k: str(v) for k, v in first_driver.items()}
                            logger.info(f"Found first driver info with {len(first_driver)} fields")
            
            return result
            
        except Exception as e:
            logger.error(f"Error exploring telemetry variables: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def set_data_manager(self, data_manager):
        """Set the data manager to use for storing telemetry data.
        
        Args:
            data_manager: The data manager instance
        """
        if hasattr(self, 'telemetry_saver'):
            self.telemetry_saver.data_manager = data_manager
            logger.info("Data manager set for telemetry saver")
        else:
            logger.warning("Telemetry saver not initialized, cannot set data manager")

    def set_lap_saver(self, lap_saver):
        """Set the lap saver for telemetry processing."""
        self.lap_saver = lap_saver
        logger.info("Lap saver set for telemetry processing")
        
        # Connect the sector timing system to the lap saver for direct sector data access
        if hasattr(lap_saver, 'set_sector_timing_system') and hasattr(self, 'sector_timing'):
            lap_saver.set_sector_timing_system(self.sector_timing)
            logger.info("✅ [SECTOR DEBUG] Connected sector timing system to lap saver")
            
        # CRITICAL FIX: Connect the iRacing API to the lap saver for direct sector data access
        if hasattr(lap_saver, 'set_iracing_api'):
            lap_saver.set_iracing_api(self)
            logger.info("✅ [SECTOR DEBUG] Connected iRacing API to lap saver for lap-specific sector data")
        
        # If the lap saver has an update method for user data, call it
        if hasattr(lap_saver, 'set_user_id'):
            # Extract user ID from session info if available
            user_id = self._session_info.get('user_id')
            if user_id:
                lap_saver.set_user_id(user_id)
                logger.info(f"Set user ID for lap saver: {user_id}")
        
        return True
    
    def set_telemetry_saver(self, telemetry_saver):
        """Set the telemetry saver for processing telemetry data."""
        if telemetry_saver:
            self.telemetry_saver = telemetry_saver
            logger.info("External telemetry saver connected to SimpleIRacingAPI")
            return True
        return False

    def debug_ir_vars(self):
        """Debug function to print all available iRacing variables."""
        if not self.ir:
            logger.error("Cannot debug vars - IR object is None")
            return
            
        try:
            # Try to get all variables directly
            available_vars = {}
            
            # Check if get_all_vars is available
            if hasattr(self.ir, 'get_all_vars'):
                all_vars = self.ir.get_all_vars()
                if all_vars:
                    # Log the variable names and some values
                    logger.info(f"Found {len(all_vars)} variables through get_all_vars")
                    # Log first 10 variables and their values as example
                    sample = {k: all_vars[k] for k in list(all_vars.keys())[:10]}
                    logger.info(f"Sample variables: {sample}")
                    return
                
            # Alternative approach - check for the _var_headers_dict attribute
            if hasattr(self.ir, '_var_headers_dict'):
                headers = self.ir._var_headers_dict
                if headers:
                    logger.info(f"Found {len(headers)} variables in _var_headers_dict")
                    sample_keys = list(headers.keys())[:10]
                    sample = {k: headers[k] for k in sample_keys}
                    logger.info(f"Sample headers: {sample}")
                    return
                    
            # If nothing found
            logger.error("Could not find any variables in the IR object")
            
            # Try a direct test of common variables
            test_vars = ['SessionTime', 'Speed', 'RPM', 'Gear', 'Throttle', 'Brake']
            results = {}
            for var in test_vars:
                try:
                    value = self.ir[var]
                    results[var] = value
                except Exception as e:
                    results[var] = f"Error: {str(e)}"
            logger.info(f"Direct test of common variables: {results}")
            
        except Exception as e:
            logger.error(f"Error in debug_ir_vars: {e}", exc_info=True)
    
    # ABS debug function removed - no longer needed for lockup detection
    
    def _get_player_car_idx(self):
        """Helper method to get the player's car index in the array data.
        
        Returns:
            int: The player's car index, or 0 if not found
        """
        try:
            # Try to get the player's car index directly
            if hasattr(self.ir, 'PlayerCarIdx'):
                return self.ir.PlayerCarIdx
            
            # Try to access it as a variable
            car_idx = self.ir['PlayerCarIdx']
            if car_idx is not None:
                return car_idx
                
            # Try to get it from DriverInfo
            if hasattr(self.ir, 'DriverInfo'):
                driver_info = self.ir.DriverInfo
                if driver_info and 'DriverCarIdx' in driver_info:
                    return driver_info['DriverCarIdx']
                    
            # Default to 0 if nothing works
            return 0
        except Exception as e:
            logger.debug(f"Error getting player car index: {e}")
            return 0
    
    def _try_get_pit_status_from_session_info(self):
        """Helper method to try to extract pit road status from session info.
        
        Returns:
            bool: True if player is on pit road, False otherwise or if unknown
        """
        try:
            # Try to get session info
            if not hasattr(self.ir, '_get_session_info'):
                return None
                
            session_info = self.ir._get_session_info()
            if not session_info:
                return None
                
            # Look for DriverInfo section
            if 'DriverInfo' not in session_info:
                return None
                
            driver_info = session_info['DriverInfo']
            
            # Try to get player car or all cars
            player_cars = []
            
            # Check if Drivers collection exists
            if 'Drivers' not in driver_info:
                return None
                
            # Get all drivers
            drivers = driver_info['Drivers']
            if not drivers or not isinstance(drivers, list):
                return None
                
            # Find player's car
            player_idx = self._get_player_car_idx()
            player_car = None
            
            for driver in drivers:
                if driver.get('CarIdx', -1) == player_idx:
                    player_car = driver
                    break
            
            if not player_car:
                # If we couldn't find by CarIdx, try UserName or just use first car
                player_car = drivers[0] if drivers else None
            
            # Check if player car has pit status
            if player_car and 'InPitStall' in player_car:
                return bool(player_car['InPitStall'])
                
            # Check if player car has pit status in a different field
            if player_car and 'OnPitRoad' in player_car:
                return bool(player_car['OnPitRoad'])
                
            # Could not determine pit status from session info
            return None
            
        except Exception as e:
            logger.debug(f"Error getting pit status from session info: {e}")
            return None 
    
    def get_sector_timing_data(self):
        """Get current sector timing data."""
        if hasattr(self, 'sector_timing') and self.sector_timing:
            status = self.sector_timing.get_status()
            return {
                'current_progress': status,
                'recent_laps': self.sector_timing.get_recent_laps(10),
                'is_initialized': status.get('enabled', False)
            }
        return None
    
    def clear_sector_timing(self):
        """Clear sector timing data (for new session)."""
        if hasattr(self, 'sector_timing') and self.sector_timing:
            self.sector_timing.reset()
            logger.info("Simple sector timing data cleared")

    def force_session_info_update(self):
        """Force an immediate attempt to retrieve SessionInfo for sector timing.
        
        Returns:
            bool: True if SessionInfo was successfully retrieved and processed, False otherwise
        """
        logger.info("🔄 Force SessionInfo update requested for simple timing...")
        
        # Simple timing doesn't need SessionInfo - it reads from data.txt
        if hasattr(self, 'sector_timing') and self.sector_timing:
            status = self.sector_timing.get_status()
            if status.get('enabled', False):
                logger.info("✅ Simple sector timing is already initialized from data.txt")
                return True
            else:
                logger.warning("❌ Simple sector timing is not enabled")
                return False
        else:
            logger.warning("❌ Simple sector timing not available")
            return False

    def get_lap_sector_data(self, lap_number):
        """Get stored sector data for a specific lap number.
        
        Args:
            lap_number: The lap number to get sector data for
            
        Returns:
            Dictionary with sector data or None if not found
        """
        if hasattr(self, '_lap_sector_data') and lap_number in self._lap_sector_data:
            sector_data = self._lap_sector_data[lap_number]
            logger.info(f"🔧 [LAP SECTOR RETRIEVAL] Found sector data for lap {lap_number}: {sector_data['sector_times']}")
            return sector_data
        else:
            logger.warning(f"❌ [LAP SECTOR RETRIEVAL] No sector data found for lap {lap_number}")
            if hasattr(self, '_lap_sector_data'):
                available_laps = list(self._lap_sector_data.keys())
                logger.warning(f"❌ [LAP SECTOR RETRIEVAL] Available laps: {available_laps}")
            return None

    def start_deferred_monitoring(self):
        """Start the deferred iRacing session monitoring if parameters are available."""
        logger.info("🔍 start_deferred_monitoring() called")
        logger.info(f"🔍 Has _deferred_monitor_params: {hasattr(self, '_deferred_monitor_params')}")
        logger.info(f"🔍 _deferred_monitor_params is not None: {getattr(self, '_deferred_monitor_params', None) is not None}")
        
        if hasattr(self, '_deferred_monitor_params') and self._deferred_monitor_params:
            logger.info("🔍 Deferred monitor params found, proceeding with monitoring start...")
            try:
                params = self._deferred_monitor_params
                supabase_client = params.get('supabase_client')
                user_id = params.get('user_id')
                lap_saver = params.get('lap_saver')
                
                logger.info(f"🔍 Extracted params: supabase_client={supabase_client is not None}, user_id={user_id}, lap_saver={lap_saver is not None}")
                
                # BUGFIX: Allow starting basic monitoring without Supabase/cloud features
                if user_id == 'anonymous' or not supabase_client:
                    logger.info("🚀 Starting basic iRacing monitoring without cloud features...")
                    # Start basic telemetry monitoring without session saving
                    if not hasattr(self, '_telemetry_timer') or not self._telemetry_timer or not self._telemetry_timer.is_alive():
                        self._start_telemetry_timer()
                        logger.info("✅ Basic iRacing telemetry monitoring started successfully")
                        self._deferred_monitor_params = None
                        return True
                    else:
                        logger.info("✅ Basic iRacing monitoring already running")
                        self._deferred_monitor_params = None
                        return True
                
                # Original cloud monitoring path
                if supabase_client and user_id and lap_saver:
                    logger.info("🔍 Importing iracing_session_monitor...")
                    from .iracing_session_monitor import start_monitoring
                    logger.info("✅ Successfully imported start_monitoring")
                    
                    logger.info("🚀 Starting deferred iRacing session monitoring...")
                    monitor_thread = start_monitoring(supabase_client, user_id, lap_saver, self)
                    logger.info(f"🔍 start_monitoring returned: {monitor_thread}")
                    if monitor_thread:
                        logger.info("✅ iRacing session monitor started successfully")
                        # Clear the deferred params since we've started monitoring
                        self._deferred_monitor_params = None
                        return True
                    else:
                        logger.error("❌ Failed to start iRacing session monitor - start_monitoring returned None/False")
                        return False
                else:
                    logger.error(f"❌ Missing required parameters for deferred monitoring:")
                    logger.error(f"  - supabase_client: {supabase_client is not None}")
                    logger.error(f"  - user_id: {user_id}")
                    logger.error(f"  - lap_saver: {lap_saver is not None}")
                    return False
            except Exception as e:
                logger.error(f"❌ Error starting deferred monitoring: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
        else:
            logger.warning("⚠️ No deferred monitoring parameters available")
            if not hasattr(self, '_deferred_monitor_params'):
                logger.warning("  - No _deferred_monitor_params attribute")
            elif not self._deferred_monitor_params:
                logger.warning("  - _deferred_monitor_params is None or empty")
            
            # BUGFIX: Try to start basic monitoring anyway if iRacing is available
            logger.info("🔍 Attempting to start basic monitoring without deferred params...")
            try:
                if not hasattr(self, '_telemetry_timer') or not self._telemetry_timer or not self._telemetry_timer.is_alive():
                    self._start_telemetry_timer()
                    logger.info("✅ Started basic iRacing monitoring as fallback")
                    return True
                else:
                    logger.info("✅ Basic iRacing monitoring already running")
                    return True
            except Exception as e:
                logger.error(f"❌ Failed to start basic monitoring: {e}")
                return False
    
    # TASK 1.1: Methods for accessing telemetry data and circular buffer
    
    def get_telemetry_buffer(self):
        """
        Get a copy of the current telemetry buffer.
        
        Returns:
            list: Copy of telemetry buffer data
        """
        with self._buffer_lock:
            return list(self.telemetry_buffer)
    
    def get_latest_telemetry(self):
        """
        Get the most recent telemetry point with all Task 1.1 fields.
        
        Returns:
            dict: Latest telemetry data or None if no data available
        """
        with self._buffer_lock:
            if self.telemetry_buffer:
                latest = self.telemetry_buffer[-1].copy()
                return self._format_task_1_1_telemetry(latest)
            return None
    
    def get_telemetry_stats(self):
        """
        Get statistics about telemetry collection for Task 1.1.
        
        Returns:
            dict: Statistics including collection rate, buffer status, etc.
        """
        # Calculate actual collection rate
        actual_hz = 0.0
        if self._telemetry_start_time and self._telemetry_count > 0:
            duration = time.time() - self._telemetry_start_time
            if duration > 0:
                actual_hz = self._telemetry_count / duration
        
        # Calculate actual seconds of data in buffer
        buffer_seconds = 0.0
        if actual_hz > 0:
            buffer_seconds = len(self.telemetry_buffer) / actual_hz
        
        stats = {
            'buffer_size': len(self.telemetry_buffer),
            'buffer_capacity': self.telemetry_buffer_size,
            'buffer_seconds_target': self.telemetry_buffer_seconds,
            'buffer_seconds_actual': buffer_seconds,
            'is_connected': self._is_connected,
            'total_frames': self._telemetry_count,
            'actual_hz': actual_hz,
            'target_hz': 60.0,
            'performance_ratio': actual_hz / 60.0 if actual_hz > 0 else 0.0
        }
            
        return stats
    
    def _format_task_1_1_telemetry(self, telemetry_data):
        """
        Format telemetry data to include all 23 required Task 1.1 fields with consistent naming.
        
        Args:
            telemetry_data: Raw telemetry dictionary
            
        Returns:
            dict: Formatted telemetry with Task 1.1 field names
        """
        if not telemetry_data:
            return None
            
        formatted = {
            # Core driving data
            'speed': telemetry_data.get('Speed', 0.0),  # m/s
            'throttle': telemetry_data.get('Throttle', 0.0),  # 0-1
            'brake': telemetry_data.get('Brake', 0.0),  # 0-1
            'gear': telemetry_data.get('Gear', 0),  # gear number
            'steering_angle': telemetry_data.get('SteeringWheelAngle', 0.0),  # radians
            
            # G-forces and motion
            'lateral_g': telemetry_data.get('LatAccel', 0.0),  # m/s²
            'longitudinal_g': telemetry_data.get('LongAccel', 0.0),  # m/s²
            'yaw_rate': telemetry_data.get('YawRate', 0.0),  # rad/s
            
            # Position and lap data
            'track_position': telemetry_data.get('LapDistPct', 0.0),  # 0-1
            'lap_number': telemetry_data.get('Lap', 0),
            'sector_number': telemetry_data.get('sector_number', 1),
            
            # Suspension travel (all 4 corners) - meters
            'suspension_lf': telemetry_data.get('LFshockDefl', 0.0),
            'suspension_rf': telemetry_data.get('RFshockDefl', 0.0),
            'suspension_lr': telemetry_data.get('LRshockDefl', 0.0),
            'suspension_rr': telemetry_data.get('RRshockDefl', 0.0),
            
            # Wheel speeds (all 4 wheels) - RPM
            'wheel_speed_lf': telemetry_data.get('WheelLFRPM', 0.0),
            'wheel_speed_rf': telemetry_data.get('WheelRFRPM', 0.0),
            'wheel_speed_lr': telemetry_data.get('WheelLRRPM', 0.0),
            'wheel_speed_rr': telemetry_data.get('WheelRRRPM', 0.0),
            
            # Tire temperatures (all 4 tires) - Celsius
            'tire_temp_lf': telemetry_data.get('LFtempCM', 0.0),
            'tire_temp_rf': telemetry_data.get('RFtempCM', 0.0),
            'tire_temp_lr': telemetry_data.get('LRtempCM', 0.0),
            'tire_temp_rr': telemetry_data.get('RRtempCM', 0.0),
            
            # Additional useful data
            'timestamp': telemetry_data.get('timestamp', time.time()),
            'session_time': telemetry_data.get('SessionTimeSecs', 0.0),
            'rpm': telemetry_data.get('RPM', 0.0)
        }
        
        return formatted

    def _adjust_buffer_size_for_rate(self):
        """Dynamically adjust buffer size based on actual telemetry rate to maintain 60 seconds."""
        current_time = time.time()
        
        # Only adjust every 30 seconds to allow rate to stabilize
        if current_time - self._last_buffer_resize < 30.0:
            return
            
        # Calculate actual rate
        if self._telemetry_start_time and self._telemetry_count > 0:
            duration = current_time - self._telemetry_start_time
            if duration > 10.0:  # Only adjust after 10 seconds of data
                actual_rate = self._telemetry_count / duration
                
                # Calculate optimal buffer size for 60 seconds at actual rate
                optimal_size = int(actual_rate * self.telemetry_buffer_seconds)
                optimal_size = max(60, min(3600, optimal_size))  # Clamp between 60 and 3600
                
                # Only resize if difference is significant (>20%)
                if abs(optimal_size - self.telemetry_buffer_size) > (self.telemetry_buffer_size * 0.2):
                    logger.info(f"Adjusting buffer size: {self.telemetry_buffer_size} -> {optimal_size} (rate: {actual_rate:.1f}Hz)")
                    
                    # Create new buffer with adjusted size
                    old_data = list(self.telemetry_buffer)
                    self.telemetry_buffer_size = optimal_size
                    self.telemetry_buffer = deque(old_data[-optimal_size:], maxlen=optimal_size)
                    
                self._last_buffer_resize = current_time

    def _start_processing_workers(self):
        """Start processing workers for heavy telemetry operations."""
        # Start database/file I/O worker
        db_worker = threading.Thread(target=self._database_worker, daemon=True)
        db_worker.start()
        self._processing_workers.append(db_worker)
        
        # Start callback worker for UI updates and AI coach
        callback_worker = threading.Thread(target=self._callback_worker, daemon=True) 
        callback_worker.start()
        self._processing_workers.append(callback_worker)
        
        logger.info("Started 2 telemetry processing workers (database + callbacks)")

    def _database_worker(self):
        """Worker thread for database and file I/O operations."""
        logger.info("🧵 Database worker thread started")
        
        while not self._stop_event.is_set():
            try:
                # Get telemetry data from queue (blocking with timeout)
                telemetry_data = self._telemetry_queue.get(timeout=1.0)
                
                # Only process if we have valid telemetry data
                if telemetry_data and telemetry_data.get('LapDistPct') is not None:
                    # Process lap saving and file I/O in this dedicated thread
                    if hasattr(self, 'lap_saver') and self.lap_saver:
                        try:
                            self.lap_saver.process_telemetry(telemetry_data)
                        except Exception as e:
                            logger.error(f"Error in lap saver: {e}")
                    
                    if hasattr(self, 'telemetry_saver') and self.telemetry_saver:
                        try:
                            self.telemetry_saver.process_telemetry(telemetry_data)
                        except Exception as e:
                            logger.error(f"Error in telemetry saver: {e}")
                
                self._telemetry_queue.task_done()
                
            except queue.Empty:
                continue  # Timeout, check stop event
            except Exception as e:
                logger.error(f"Error in database worker: {e}")
        
        logger.info("🧵 Database worker thread stopped")

    def _callback_worker(self):
        """Worker thread for UI callbacks and AI coach."""
        logger.info("🧵 Callback worker thread started")
        telemetry_buffer = []  # Local buffer for this worker
        
        while not self._stop_event.is_set():
            try:
                # Process multiple items from queue in batches for efficiency
                batch_size = 10
                batch = []
                
                # Get first item (blocking)
                try:
                    first_item = self._telemetry_queue.get(timeout=1.0)
                    batch.append(first_item)
                except queue.Empty:
                    continue
                
                # Get additional items non-blocking
                for _ in range(batch_size - 1):
                    try:
                        item = self._telemetry_queue.get_nowait()
                        batch.append(item)
                    except queue.Empty:
                        break
                
                # Process the batch - only use the latest telemetry for callbacks
                if batch:
                    latest_telemetry = batch[-1]  # Use most recent data
                    
                    # Update UI with latest data only (don't spam with old data)
                    if latest_telemetry:
                        display_telemetry = latest_telemetry.copy()
                        speed = display_telemetry.get('Speed', 0.0)
                        if isinstance(speed, (list, tuple)):
                            speed = speed[0] if len(speed) > 0 else 0.0
                        display_telemetry['speed'] = speed * 3.6  # Convert to km/h for UI
                        
                        # Trigger callbacks with latest data
                        for callback in self._telemetry_callbacks:
                            try:
                                callback(display_telemetry)
                            except Exception as e:
                                logger.error(f"Error in telemetry callback: {e}")
                    
                    # Mark all items as done
                    for _ in batch:
                        self._telemetry_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in callback worker: {e}")
        
        logger.info("🧵 Callback worker thread stopped")