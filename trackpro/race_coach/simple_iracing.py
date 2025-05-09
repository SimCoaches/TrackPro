import irsdk
import time
import logging
import math
import threading
from pathlib import Path
from .telemetry_saver import TelemetrySaver
from PyQt5.QtCore import QObject, pyqtSignal

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
        
        logger.info("SimpleIRacingAPI initialized")
    
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
                    while not self._stop_event.is_set():
                        loop_count += 1
                        if loop_count % 300 == 0: # Log every 5 seconds approx
                             logger.debug(f"Telemetry worker loop running. Connected: {self._is_connected}")

                        # Use internal _is_connected flag set by monitor
                        if self._is_connected:
                            self.process_telemetry()
                        else:
                            # Sleep longer if not connected
                            self._stop_event.wait(0.5)
                            continue
                        self._stop_event.wait(1/60) 
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
             logger.debug(f"API session info updated by monitor: {self._session_info}")

        # Prepare payload for signal
        signal_payload = {
            'is_connected': self._is_connected,
            'session_info': self._session_info.copy()
        }

        # Emit session info signal (containing connection status and session info)
        if hasattr(self, 'sessionInfoUpdated'):
             self.sessionInfoUpdated.emit(signal_payload)
             logger.debug("Emitted sessionInfoUpdated signal")
        else:
             logger.warning("sessionInfoUpdated signal does not exist on API instance")
    
    def process_telemetry(self):
        """Process telemetry data from iRacing."""
        # Check if we're connected first
        if not self._is_connected:
            return

        # Debug: Check if IR object exists at all
        if not self.ir:
            logger.warning("IR object is None")
            return
        
        # Check if we are connected to iracing properly
        if not hasattr(self.ir, 'is_connected') or not self.ir.is_connected:
            if not hasattr(self, '_conn_error_counter'):
                self._conn_error_counter = 0
            self._conn_error_counter += 1
            if self._conn_error_counter % 300 == 0:
                logger.warning("IRSDK not connected")
            return

        try:
            # Freeze buffer to get consistent data as shown in example
            self.ir.freeze_var_buffer_latest()
            
            # Debug: Log all available variables occasionally
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1
            
            # Every ~10 seconds call the debug function
            if self._debug_counter % 600 == 0:
                logger.info("Running iRacing variable debug function...")
                self.debug_ir_vars()
            
            # Create telemetry dictionary with DIRECT dictionary access
            # based on the example code pattern
            telemetry = {}
            
            # Session time is a good test variable
            session_time = None
            try:
                session_time = self.ir['SessionTime']
                if session_time is not None:
                    logger.debug(f"Session time retrieved: {session_time}")
                    telemetry['SessionTimeSecs'] = session_time
            except Exception as e:
                if self._debug_counter % 300 == 0:
                    logger.warning(f"Failed to get SessionTime: {e}")
                    
            # Try to get LapDistPct - critical for lap detection
            try:
                lap_dist_pct = self.ir['LapDistPct']
                telemetry['LapDistPct'] = lap_dist_pct
                # Log this more frequently as it's crucial for lap detection
                if self._debug_counter % 120 == 0:  # Every ~2 seconds
                    logger.debug(f"LapDistPct: {lap_dist_pct}")
            except Exception as e:
                if self._debug_counter % 300 == 0:
                    logger.warning(f"Failed to get LapDistPct: {e}")
            
            # Try to get lap info - critical for lap tracking
            try:
                current_lap = self.ir['Lap']
                lap_completed = self.ir['LapCompleted']
                lap_current_time = self.ir['LapCurrentLapTime']
                lap_last_time = self.ir['LapLastLapTime']
                
                telemetry['Lap'] = current_lap
                telemetry['LapCompleted'] = lap_completed
                telemetry['LapCurrentLapTime'] = lap_current_time
                telemetry['LapLastLapTime'] = lap_last_time
                
                # Log lap info more frequently
                if self._debug_counter % 60 == 0:  # Every second
                    logger.debug(f"Lap info: Current={current_lap}, Completed={lap_completed}, CurrentTime={lap_current_time}, LastTime={lap_last_time}")
            except Exception as e:
                if self._debug_counter % 300 == 0:
                    logger.warning(f"Failed to get lap information: {e}")
            
            # Now do the same for all other variables, with direct dictionary access
            try: telemetry['Speed'] = self.ir['Speed']
            except: telemetry['Speed'] = 0.0
            
            try: telemetry['RPM'] = self.ir['RPM']
            except: telemetry['RPM'] = 0.0
            
            try: telemetry['Gear'] = self.ir['Gear'] 
            except: telemetry['Gear'] = 0
            
            try: telemetry['LapBestLapTime'] = self.ir['LapBestLapTime']
            except: telemetry['LapBestLapTime'] = None
            
            try: telemetry['Throttle'] = self.ir['Throttle']
            except: telemetry['Throttle'] = None
            
            try: telemetry['Brake'] = self.ir['Brake']
            except: telemetry['Brake'] = None
            
            try: telemetry['Clutch'] = self.ir['Clutch']
            except: telemetry['Clutch'] = None
            
            try: telemetry['SteeringWheelAngle'] = self.ir['SteeringWheelAngle']
            except: telemetry['SteeringWheelAngle'] = None
            
            try: telemetry['SteeringWheelAngleMax'] = self.ir['SteeringWheelAngleMax']
            except: telemetry['SteeringWheelAngleMax'] = None

            # --- Handle Speed Type (Sequence vs Number) --- #
            speed = telemetry['Speed'] # Use the retrieved value
            if isinstance(speed, (list, tuple)):
                speed = speed[0] if len(speed)>0 and isinstance(speed[0], (int, float)) else 0.0
            elif not isinstance(speed, (int, float)): speed = 0.0
            # Update the speed value after potential type correction
            telemetry['speed'] = speed # Keep in m/s
            
            # Add current track/car from internal state
            telemetry['track_name'] = self._session_info.get('current_track')
            telemetry['car_name'] = self._session_info.get('current_car')

            # Dump telemetry to log occasionally
            if not hasattr(self, '_telemetry_log_counter'):
                self._telemetry_log_counter = 0
            self._telemetry_log_counter += 1
            if self._telemetry_log_counter % 60 == 0:
                if session_time is not None:
                    formatted_values = {k: f"{v:.2f}" if isinstance(v, float) else v 
                                       for k, v in telemetry.items() if v is not None}
                    logger.info(f"Telemetry data: {formatted_values}")
                else:
                    logger.warning("No session time available in telemetry")

            # --- Pass to TelemetrySaver and LapSaver --- #
            # Ensure essential data exists before passing
            if telemetry.get('LapDistPct') is not None and telemetry.get('SessionTimeSecs') is not None:
                lap_info_to_pass_to_ui = None
                if self.telemetry_saver: 
                    lap_info_to_pass_to_ui = self.telemetry_saver.process_telemetry(telemetry)
                if self.lap_saver:
                    try:
                         lap_result_supabase = self.lap_saver.process_telemetry(telemetry)
                         if lap_result_supabase: lap_info_to_pass_to_ui = lap_result_supabase
                    except Exception as e:
                        logger.error(f"Error processing telemetry with Supabase lap saver: {e}")

                # --- Notify Callbacks --- #
                if telemetry:
                    if lap_info_to_pass_to_ui:
                        telemetry['is_new_lap'] = lap_info_to_pass_to_ui[0]
                        telemetry['completed_lap_number'] = lap_info_to_pass_to_ui[1]
                        telemetry['completed_lap_time'] = lap_info_to_pass_to_ui[2]
                    display_telemetry = telemetry.copy()
                    display_telemetry['speed'] = speed * 3.6 # Convert for UI
                    for callback in self._telemetry_callbacks:
                         try: callback(display_telemetry)
                         except Exception as e: logger.error(f"Error in telemetry callback: {e}")
            elif self._telemetry_log_counter % 60 == 0:
                logger.warning(f"Missing essential telemetry: LapDistPct={telemetry.get('LapDistPct')}, SessionTimeSecs={telemetry.get('SessionTimeSecs')}")
                        
        except Exception as e:
            logger.error(f"Error in process_telemetry: {e}", exc_info=True)
    
    def register_on_connection_changed(self, callback):
        if callback not in self._connection_callbacks: self._connection_callbacks.append(callback)
    def register_on_session_info_changed(self, callback):
        if callback not in self._session_info_callbacks: self._session_info_callbacks.append(callback)
    def register_on_telemetry_data(self, callback):
        if callback not in self._telemetry_callbacks: self._telemetry_callbacks.append(callback)
    def is_connected(self):
        return self._is_connected # Use internal flag set by monitor
    def disconnect(self):
        if self.state.ir_connected:
            logger.info("Disconnecting from iRacing...")
            self._stop_event.set()
            try:
                if self._telemetry_timer and self._telemetry_timer.is_alive(): self._telemetry_timer.join(timeout=1.0)
                self._telemetry_timer = None
                # No session timer to join
            except Exception as e: logger.error(f"Error joining worker threads: {e}")
            if hasattr(self, 'telemetry_saver'): self.telemetry_saver.end_session()
            self.ir.shutdown()
            self.state.ir_connected = False # Keep state object in sync
            # Notify UI of disconnect via the update method
            self.update_info_from_monitor({}, is_connected=False)
            logger.info("Disconnected from iRacing")
            return True
        return False
    
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
        if user_id:
            lap_saver.set_user_id(user_id)
            logger.info(f"Set user ID for lap saver: {user_id}")
        else:
            logger.warning("No user ID available to set for lap saver")
            
        # Start a session if we're already connected
        if self.state.ir_connected:
            track_name = self.get_current_track()
            car_name = self.get_current_car()
            session_type = self.get_session_type()
            session_id = lap_saver.start_session(track_name, car_name, session_type)
            logger.info(f"Started Supabase session with ID: {session_id}")
        
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