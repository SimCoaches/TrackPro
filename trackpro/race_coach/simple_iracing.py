import irsdk
import time
import logging
import math
import threading
import traceback
from pathlib import Path
from .telemetry_saver import TelemetrySaver
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt, pyqtSlot

logger = logging.getLogger(__name__)

# Our simple state class similar to the example
class State:
    ir_connected = False
    last_car_setup_tick = -1

class SimpleIRacingAPI(QObject):
    """A simpler implementation of iRacing API based on the pyirsdk example."""
    
    # Define the signals
    sessionInfoUpdated = pyqtSignal(dict)
    new_trackpro_session_created = pyqtSignal(str, str, str)  # Signal emitted when a new TrackPro session is created: (session_id, track_name, car_name)
    
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
        self._actual_irsdk_connected = False # New flag for true irsdk connection state
        
        # Telemetry rate tracking
        self._telemetry_count = 0
        self._telemetry_start_time = None
        self._last_rate_check_time = None
        
        # Add flag to track if disconnect has been called
        self._disconnected = False
        
        logger.info("SimpleIRacingAPI initialized")
    
    def __del__(self):
        """Clean up resources when this object is garbage collected."""
        try:
            logger.info("SimpleIRacingAPI.__del__ called - cleaning up resources")
            self.disconnect()
        except Exception as e:
            logger.error(f"Error in SimpleIRacingAPI.__del__: {e}")
    
    def connect(self, on_connected=None, on_disconnected=None, on_session_info_changed=None, on_telemetry_update=None):
        """Register callbacks and attempt to connect to iRacing."""
        logger.info("SimpleIRacingAPI.connect called - registering callbacks and attempting connection.")
        # Register callbacks if provided
        if on_connected: self.register_on_connection_changed(on_connected)
        if on_disconnected:
            def on_disconnected_wrapper(is_connected, session_info):
                if not is_connected: on_disconnected()
            self.register_on_connection_changed(on_disconnected_wrapper)
        # if on_session_info_changed: self.register_on_session_info_changed(on_session_info_changed) # Legacy
        if on_telemetry_update: self.register_on_telemetry_data(on_telemetry_update)

        # Attempt to startup irsdk
        logger.info("SimpleIRacingAPI: Attempting self.ir.startup()...")
        try:
            if not self.ir.is_initialized:
                self.ir.startup()
                logger.info(f"SimpleIRacingAPI: After startup() attempt - initialized={self.ir.is_initialized}, connected={self.ir.is_connected}")
            elif not self.ir.is_connected: # Already initialized, but not connected
                self.ir.startup() # Try startup again, it might connect an initialized but disconnected instance
                logger.info(f"SimpleIRacingAPI: Re-attempted startup() on initialized but disconnected irsdk - initialized={self.ir.is_initialized}, connected={self.ir.is_connected}")
            else:
                logger.info("SimpleIRacingAPI: irsdk already initialized and connected.")

            self._actual_irsdk_connected = self.ir.is_connected and self.ir.is_initialized
            self._is_connected = self._actual_irsdk_connected # Sync internal API flag
            self.state.ir_connected = self._actual_irsdk_connected # Sync legacy state flag

            if self._actual_irsdk_connected:
                logger.info("SimpleIRacingAPI: Successfully connected to iRacing SDK.")
                if not self._telemetry_timer or not self._telemetry_timer.is_alive():
                    logger.info("SimpleIRacingAPI: Connection established, queueing telemetry polling start on main thread.")
                    QMetaObject.invokeMethod(self, "_start_telemetry_timer", Qt.QueuedConnection)
            else:
                logger.warning("SimpleIRacingAPI: Failed to establish connection to iRacing SDK after startup attempt.")
        except Exception as e:
            logger.error(f"SimpleIRacingAPI: Error during self.ir.startup(): {e}", exc_info=True)
            self._actual_irsdk_connected = False
            self._is_connected = False
            self.state.ir_connected = False

        # Notify monitor (or UI if it called connect directly) about the current connection status
        # This might be redundant if monitor calls this, but good for direct UI calls
        # Let's use the signal for consistency
        current_info_for_signal = self._session_info.copy() if self._session_info else {}
        self.update_info_from_monitor(current_info_for_signal, is_connected=self._actual_irsdk_connected)

        logger.info(f"SimpleIRacingAPI.connect finished. Actual irsdk connected state: {self._actual_irsdk_connected}")
        return self._actual_irsdk_connected # Return the true connection status
    
    @pyqtSlot()
    def _start_telemetry_timer(self):
        """Start a timer to process telemetry data periodically."""
        if not hasattr(self, '_telemetry_timer') or self._telemetry_timer is None or not self._telemetry_timer.is_alive():
            def telemetry_worker():
                logger.info("Starting telemetry worker thread")
                try:
                    loop_count = 0
                    while not self._stop_event.is_set():
                        loop_count += 1
                        if loop_count % 300 == 0: # Log every 5 seconds approx
                             logger.debug(f"Telemetry worker loop running. Connected: {self._is_connected}")

                        # Use internal _is_connected flag set by monitor
                        if self._is_connected:
                            start_time = time.time()
                            self.process_telemetry()
                            processing_time = time.time() - start_time
                            
                            # Log processing time periodically
                            if loop_count % 600 == 0:  # Every ~10 seconds
                                logger.info(f"Telemetry processing time: {processing_time*1000:.2f}ms")
                            
                            # Dynamic sleep to maintain 60Hz more precisely
                            target_frame_time = 1/60
                            sleep_time = max(0.001, target_frame_time - processing_time)  # Ensure at least a minimal sleep
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
                    logger.info("Connection established, waiting 1s before starting telemetry polling...")
                    time.sleep(1.0)  # Reduced from 3s to 1s for better performance
                    self._start_telemetry_timer()
            elif not self._is_connected and self._telemetry_timer and self._telemetry_timer.is_alive():
                # Signal telemetry thread to stop if disconnecting
                # self._stop_event.set() # This might be too aggressive if monitor reconnects quickly
                pass

        # Check if session info has changed
        session_changed = False
        if session_info != self._session_info:
             old_session_info = self._session_info.copy() if self._session_info else {}
             self._session_info = session_info.copy() # Update with a copy
             session_changed = True
             
             # Only log at debug level for performance
             logger.debug(f"API session info updated by monitor: {self._session_info}")

        # Prepare payload for signal
        signal_payload = {
            'is_connected': self._is_connected,
            'session_info': self._session_info.copy()
        }

        # Emit session info signal if we have it
        if hasattr(self, 'sessionInfoUpdated'):
             self.sessionInfoUpdated.emit(signal_payload)
             logger.debug("Emitted sessionInfoUpdated signal")
        else:
             logger.warning("sessionInfoUpdated signal does not exist on API instance")
             
        # Call handle_new_session_data when session info changes to update lap_saver
        # Only if significant session data has changed to improve performance
        if session_changed and self.lap_saver and hasattr(self, 'handle_new_session_data'):
            # Check for specific changes that require a session update
            session_id_changed = old_session_info.get('session_id') != self._session_info.get('session_id')
            track_changed = old_session_info.get('current_track') != self._session_info.get('current_track')
            car_changed = old_session_info.get('current_car') != self._session_info.get('current_car')
            
            if session_id_changed or track_changed or car_changed or not old_session_info:
                logger.info("Session info significantly changed, calling handle_new_session_data to update lap_saver")
                try:
                    self.handle_new_session_data(self._session_info)
                except Exception as e:
                    logger.error(f"Error calling handle_new_session_data: {e}")
            else:
                logger.debug("Minor session info changes - not calling handle_new_session_data")
        elif session_changed and self.lap_saver and not hasattr(self, 'handle_new_session_data'):
            logger.error("handle_new_session_data method does not exist on API instance")
    
    def process_telemetry(self):
        """Process telemetry data from iRacing."""
        # Check if we're connected first
        if not self._is_connected:
            return

        # Initialize telemetry rate tracking if not already done
        if self._telemetry_start_time is None:
            self._telemetry_start_time = time.time()
            self._last_rate_check_time = self._telemetry_start_time
            self._telemetry_count = 0
            
        # Increment the telemetry counter and check rate periodically
        self._telemetry_count += 1
        
        # Measure rate every 10 seconds instead of 5
        now = time.time()
        if now - self._last_rate_check_time >= 10.0:
            duration = now - self._last_rate_check_time
            rate = self._telemetry_count / duration
            logger.info(f"Telemetry collection rate: {rate:.2f} Hz (collected {self._telemetry_count} points over {duration:.2f}s)")
            self._telemetry_count = 0
            self._last_rate_check_time = now

        # Get current telemetry data
        start_time = time.time()
        ir_data = {}
        
        try:
            # Get core telemetry values 
            telemetry_keys = [
                'SessionTime', 'SessionTimeRemain', 'SessionTimeOfDay',
                'LapDistPct', 'Lap', 'LapCompleted', 'LapCurrentLapTime', 'LapLastLapTime',
                'Speed', 'RPM', 'Gear', 'Throttle', 'Brake', 'Clutch', 'SteeringWheelAngle',
                'SessionState', 'IsOnTrack', 'OnPitRoad'
            ]
            
            for key in telemetry_keys:
                try:
                    ir_data[key] = self.ir[key]
                except (KeyError, TypeError, IndexError):
                    # Skip missing keys instead of failing
                    pass
                    
            # Add our custom calculated fields
            ir_data['SessionTimeSecs'] = self.ir['SessionTime']
            ir_data['LapDistPct'] = self.ir['LapDistPct']  
            
            # Add calculated/additional fields
            ir_data['speed'] = self.ir['Speed']  # In m/s
            ir_data['brake'] = self.ir['Brake']  # Normalized 0-1
            
            # Add track and car info
            if self.current_track_name:
                ir_data['track_name'] = self.current_track_name
            if self.current_car_name:
                ir_data['car_name'] = self.current_car_name
                
            # Only log full data dump occasionally to reduce spam
            if self._telemetry_count % 300 == 0:  # Log every ~5 seconds at 60Hz
                logger.info(f"Telemetry data: {self._format_telemetry_for_logging(ir_data)}")
            
            # Process using telemetry saver if available
            self._save_telemetry_data(ir_data)
            
            # Send telemetry to lap_saver if available
            self._process_lap_data(ir_data)
                
            # Emit telemetry data signal if needed (reduce this if UI is slow)
            if hasattr(self, 'telemetryUpdated'):
                self.telemetryUpdated.emit(ir_data)
                
            # Call any registered telemetry callbacks
            for callback in self._telemetry_callbacks:
                try:
                    callback(ir_data)
                except Exception as e:
                    logger.error(f"Error in telemetry callback: {e}")
        
        except Exception as e:
            logger.error(f"Error in process_telemetry: {e}")
            
        finally:
            # Measure processing time for performance tuning
            elapsed = (time.time() - start_time) * 1000
            if elapsed > 30.0:  # Only log when slow (>30ms)
                logger.info(f"Telemetry processing time: {elapsed:.2f}ms")
                
    def _format_telemetry_for_logging(self, telemetry_data):
        """Format telemetry data for logging to reduce verbosity"""
        result = {}
        for key, value in telemetry_data.items():
            if isinstance(value, float):
                # Round floats to 2 decimal places for logging
                result[key] = f"{value:.2f}"
            else:
                result[key] = value
        return result
        
    def _save_telemetry_data(self, telemetry_data):
        """Save telemetry data using TelemetrySaver if available"""
        if hasattr(self, 'telemetry_saver') and self.telemetry_saver:
            try:
                # TelemetrySaver uses process_telemetry, not add_frame
                self.telemetry_saver.process_telemetry(telemetry_data)
            except Exception as e:
                logger.error(f"Error saving telemetry data: {e}")
                
    def _process_lap_data(self, telemetry_data):
        """Process lap data using lap_saver if available"""
        if hasattr(self, 'lap_saver') and self.lap_saver:
            try:
                self.lap_saver.process_telemetry(telemetry_data)
            except Exception as e:
                logger.error(f"Error processing lap data: {e}")
    
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
        """Set the lap saver to use for storing lap data in Supabase.
        
        Args:
            lap_saver: The IRacingLapSaver instance
        """
        self.lap_saver = lap_saver
        
        # First check if user_id is in session info
        user_id = None
        if self._session_info and 'user_id' in self._session_info:
            user_id = self._session_info['user_id']
            
        # If not found in session info, try to get from user_manager
        if not user_id:
            try:
                from ..auth.user_manager import get_current_user
                user = get_current_user()
                if user and hasattr(user, 'id'):
                    user_id = user.id
                    # Store it in session info for future use
                    if not self._session_info:
                        self._session_info = {}
                    self._session_info['user_id'] = user_id
            except Exception as e:
                logger.error(f"Error getting current user: {e}")
        
        # Set the user ID if we have it
        if user_id and lap_saver:
            if hasattr(lap_saver, 'set_user_id'):
                lap_saver.set_user_id(user_id)
                logger.info(f"Set user ID for lap saver: {user_id}")
            else:
                logger.warning("lap_saver does not have set_user_id method")
            
        # Start a session if we're already connected
        if self.state.ir_connected and self._is_connected and lap_saver:
            # Get current session data
            track_name = self.get_current_track()
            car_name = self.get_current_car()
            session_type = self.get_session_type()
            
            if track_name and car_name and hasattr(lap_saver, 'start_session'):
                try:
                    session_id = lap_saver.start_session(track_name, car_name, session_type)
                    if session_id:
                        logger.info(f"Started Supabase session with ID: {session_id}")
                        # Store the ID for future reference
                        self._current_db_session_id = session_id
                        
                        # Emit signal if available
                        if hasattr(self, 'new_trackpro_session_created'):
                            self.new_trackpro_session_created.emit(session_id, track_name, car_name)
                    else:
                        logger.warning("Failed to start a new session during set_lap_saver")
                except Exception as e:
                    logger.error(f"Error starting session during set_lap_saver: {e}")
        
        logger.info("Lap saver set for telemetry processing")
        
        return True

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

    def is_api_connected_to_iracing(self):
        """Returns the true connection state of the internal irsdk instance."""
        if self.ir:
            return self.ir.is_connected and self.ir.is_initialized
        return False 

    def handle_new_session_data(self, session_data):
        """
        Processes new session data, updates internal state, and ensures lap_saver session is handled.
        This is typically called by IRacingSessionMonitor when iRacing session info changes.
        """
        # Update core attributes from session_data
        self.current_track_name = session_data.get('current_track')
        self.current_car_name = session_data.get('current_car')
        self.current_config_name = session_data.get('current_config')
        self.current_session_type_name = session_data.get('session_type')
        self.current_iracing_session_id = session_data.get('session_id')
        self.current_iracing_subsession_id = session_data.get('subsession_id')
        self.current_iracing_track_id = session_data.get('track_id')
        self.current_iracing_car_id = session_data.get('car_id')
        self.current_track_length = session_data.get('track_length')
        self.current_track_location = session_data.get('track_location')
        
        logger.info(f"SimpleIRacingAPI.handle_new_session_data: Track='{self.current_track_name}', Car='{self.current_car_name}', Type='{self.current_session_type_name}'")
        
        # Only start a new Supabase session if we have all the required data
        if not all([self.current_track_name, self.current_car_name, self.current_session_type_name]):
            logger.warning("Missing required session data. Cannot start new session in Supabase.")
            return False
            
        # Ensure we have a lap_saver instance
        if not hasattr(self, 'lap_saver') or self.lap_saver is None:
            logger.warning("No lap_saver instance set. Cannot start new session in Supabase.")
            return False
            
        # Start a new session in the lap_saver
        try:
            logger.info(f"Starting session in lap_saver with Track: {self.current_track_name}, Car: {self.current_car_name}, Type: {self.current_session_type_name}")
            session_id = self.lap_saver.start_session(
                track_name=self.current_track_name,
                car_name=self.current_car_name,
                session_type=self.current_session_type_name
            )
            
            if session_id:
                logger.info(f"Lap saver started/confirmed session. DB Session ID: {session_id}")
                
                # Emit the signal if it exists
                if hasattr(self, 'new_trackpro_session_created'):
                    self.new_trackpro_session_created.emit(session_id, self.current_track_name, self.current_car_name)
                    
                return True
            else:
                logger.error("Failed to start session in lap_saver.")
                return False
                
        except Exception as e:
            logger.error(f"Exception in handle_new_session_data: {e}", exc_info=True)
            return False