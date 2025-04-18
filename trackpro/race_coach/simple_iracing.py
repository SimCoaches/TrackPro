import irsdk
import time
import logging
import math
import threading
from pathlib import Path
from .telemetry_saver import TelemetrySaver

logger = logging.getLogger(__name__)

# Our simple state class similar to the example
class State:
    ir_connected = False
    last_car_setup_tick = -1

class SimpleIRacingAPI:
    """A simpler implementation of iRacing API based on the pyirsdk example."""
    
    def __init__(self):
        """Initialize the API."""
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
        """Connect to iRacing."""
        logger.info("Attempting to connect to iRacing")
        
        # Register callbacks if provided
        if on_connected:
            self.register_on_connection_changed(on_connected)
        if on_disconnected:
            # Create a wrapper to call the on_disconnected callback
            def on_disconnected_wrapper(is_connected, session_info):
                if not is_connected:
                    on_disconnected()
            self.register_on_connection_changed(on_disconnected_wrapper)
        if on_session_info_changed:
            self.register_on_session_info_changed(on_session_info_changed)
        if on_telemetry_update:
            self.register_on_telemetry_data(on_telemetry_update)
        
        # Attempt to connect directly
        connected = self.check_iracing()
        
        # Notify about the connection status
        if connected:
            logger.info("Successfully connected to iRacing")
            self._is_connected = True
            for callback in self._connection_callbacks:
                try:
                    callback(True, self._session_info)
                except Exception as e:
                    logger.error(f"Error in connection callback: {e}")
            
            # Start a timer to periodically update session info
            self._start_session_info_timer()
        else:
            logger.warning("Failed to connect to iRacing - simulator may not be running")
        
        return connected
    
    def check_iracing(self):
        """Check if we are connected to iRacing and update the connection state."""
        if self.state.ir_connected and not (self.ir.is_initialized and self.ir.is_connected):
            self.state.ir_connected = False
            self.state.last_car_setup_tick = -1
            self.ir.shutdown()
            logger.info('irsdk disconnected')
            self._is_connected = False
            
            # End telemetry saving session
            if hasattr(self, 'telemetry_saver'):
                self.telemetry_saver.end_session()
            
            # Notify callbacks about disconnect
            for callback in self._connection_callbacks:
                try:
                    callback(False, None)
                except Exception as e:
                    logger.error(f"Error in connection callback on disconnect: {e}")
            return False
        elif not self.state.ir_connected and self.ir.startup() and self.ir.is_initialized and self.ir.is_connected:
            self.state.ir_connected = True
            logger.info('irsdk connected')
            self._is_connected = True
            
            # Update session info
            self._update_session_info()
            
            # Start telemetry timer
            self._start_telemetry_timer()
            
            # Start session info update timer
            self._start_session_info_timer()
            
            # Start a new telemetry saving session
            track_name = self.get_current_track()
            car_name = self.get_current_car()
            self.telemetry_saver.start_session(None, track_name, car_name)
            
            # Notify callbacks about successful connect
            for callback in self._connection_callbacks:
                try:
                    callback(True, self._session_info)
                except Exception as e:
                    logger.error(f"Error in connection callback on connect: {e}")
            return True
        return False
    
    def _start_telemetry_timer(self):
        """Start a timer to process telemetry data periodically."""
        if not hasattr(self, '_telemetry_timer') or self._telemetry_timer is None:
            
            def telemetry_worker():
                logger.info("Starting telemetry worker thread")
                try:
                    # Use stop event instead of state flag
                    while not self._stop_event.is_set():
                        # Process telemetry if connected
                        if self.state.ir_connected:
                            self.process_telemetry()
                        # Sleep for a short time (60 Hz update rate)
                        # Use event wait for faster shutdown
                        self._stop_event.wait(1/60) 
                except Exception as e:
                    logger.error(f"Error in telemetry worker: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                logger.info("Telemetry worker thread stopped")
            
            # Create and start the thread
            self._stop_event.clear() # Ensure event is clear before starting
            self._telemetry_timer = threading.Thread(target=telemetry_worker, daemon=True)
            self._telemetry_timer.start()
            logger.info("Telemetry worker thread started")
    
    def _start_session_info_timer(self):
        """Start a timer to periodically update session info."""
        if not hasattr(self, '_session_info_timer') or self._session_info_timer is None:
            
            def session_info_worker():
                logger.info("Starting session info worker thread")
                try:
                    # Wait a bit for the initial connection to settle
                    time.sleep(2)
                    
                    # Use stop event instead of state flag
                    while not self._stop_event.is_set(): 
                        if self.state.ir_connected:
                            # Try to update session info
                            try:
                                self._update_session_info()
                            except Exception as e:
                                logger.error(f"Error in session info update: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                        # Sleep to avoid too frequent updates
                        # Use event wait for faster shutdown
                        self._stop_event.wait(5) 
                except Exception as e:
                    logger.error(f"Error in session info worker: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                logger.info("Session info worker thread stopped")
            
            # Create and start the thread
            self._stop_event.clear() # Ensure event is clear
            self._session_info_timer = threading.Thread(target=session_info_worker, daemon=True)
            self._session_info_timer.start()
            logger.info("Session info update timer started")
    
    def _update_session_info(self):
        """Update session information from iRacing, optimized for car name retrieval."""
        if not self.state.ir_connected:
            return False
        
        track_name = None
        car_name = None
        
        try:
            logger.info("Updating session info from iRacing")
            
            # Primary method: Try PlayerInfo for car name first
            if hasattr(self.ir, 'PlayerInfo'):
                try:
                    player_info = self.ir.PlayerInfo
                    if isinstance(player_info, dict) and 'CarScreenName' in player_info:
                        car_name = player_info['CarScreenName']
                        logger.info(f"SUCCESS! Found car name via PlayerInfo: {car_name}")
                    else:
                        logger.debug(f"PlayerInfo available but no CarScreenName: {player_info}")
                except Exception as e:
                    logger.error(f"Error accessing PlayerInfo: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
            
            # Fallback: Use parsed session info if PlayerInfo fails
            if not car_name:
                logger.info("Falling back to session info parsing for car name")
                try:
                    # This is a critical fix - for iRacing API version compatibility:
                    # The _get_session_info method requires a key parameter in some versions
                    # Let's handle this by creating helper function
                    def get_session_info_safe(key=None):
                        try:
                            if hasattr(self.ir, '_get_session_info'):
                                # Pass the key if the method requires it
                                if key is not None:
                                    return self.ir._get_session_info(key)
                                else:
                                    # Try calling with no arguments
                                    try:
                                        return self.ir._get_session_info()
                                    except TypeError:
                                        # If that fails, try with an empty string key
                                        return self.ir._get_session_info('')
                            elif hasattr(self.ir, 'session_info'):
                                # Direct access if available
                                return self.ir.session_info
                        except Exception as e:
                            logger.error(f"Error accessing session info: {e}")
                            return None
                    
                    # Try to get driver info from session info
                    session_info = get_session_info_safe()
                    if session_info and 'DriverInfo' in session_info:
                        driver_info = session_info['DriverInfo']
                        if 'Drivers' in driver_info and driver_info['Drivers']:
                            car_name = driver_info['Drivers'][0].get('CarScreenName', None)
                            if car_name:
                                logger.info(f"SUCCESS! Found car name via DriverInfo: {car_name}")
                            else:
                                logger.debug(f"DriverInfo available but no CarScreenName: {driver_info}")
                except Exception as e:
                    logger.error(f"Error parsing session info for car name: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
            
            # Final fallback: Default if no car name found
            if not car_name:
                car_name = "iRacing Vehicle"
                logger.warning("No car name found; using default: iRacing Vehicle")
            
            # Update track name using the same session info helper
            try:
                session_info = get_session_info_safe()
                if session_info and 'WeekendInfo' in session_info:
                    weekend_info = session_info['WeekendInfo']
                    for track_field in ['TrackDisplayName', 'TrackName']:
                        if track_field in weekend_info:
                            track_name = weekend_info[track_field]
                            logger.info(f"Found track name: {track_name}")
                            break
            except Exception as e:
                logger.debug(f"Error getting track name: {e}")
            
            # Update session info dictionary
            self._session_info['current_track'] = track_name if track_name else "Brands Hatch Circuit"  # Fallback
            self._session_info['current_car'] = car_name
            
            # IMPORTANT FIX: Make sure we start a Supabase session if we have car and track info
            if self.lap_saver and track_name and car_name:
                # Check if we need to start a new session
                if not getattr(self.lap_saver, '_current_session_id', None):
                    logger.info(f"Starting Supabase session for {track_name} with {car_name}")
                    session_type = self.get_session_type()
                    session_id = self.lap_saver.start_session(track_name, car_name, session_type)
                    if session_id:
                        logger.info(f"Started Supabase session with ID: {session_id}")
                    else:
                        logger.error("Failed to start Supabase session")
            
            logger.info(f"Final session info: Track={self._session_info['current_track']}, Car={self._session_info['current_car']}")
            
            # Notify callbacks
            for callback in self._session_info_callbacks:
                try:
                    callback(self._session_info)
                except Exception as e:
                    logger.error(f"Error in session info callback: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error updating session info: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return False
    
    def process_telemetry(self):
        """Process telemetry data from iRacing."""
        if not self.state.ir_connected:
            return
        
        # We'll use a flag to track if we've frozen the buffer
        buffer_frozen = False
        
        try:
            # Freeze the buffer to get consistent data
            self.ir.freeze_var_buffer_latest()
            buffer_frozen = True
            
            # Try to get various telemetry values with fallbacks
            # Speed - try multiple possible field names
            telemetry = {}
            
            for speed_field in ['Speed', 'DisplayedSpeed', 'speed', 'CarIdxVel']:
                speed = self.ir[speed_field]
                if speed is not None:
                    telemetry['speed'] = speed * 3.6  # Convert to km/h
                    break
            
            # RPM
            for rpm_field in ['RPM', 'EngineRPM', 'rpm', 'engine_rpm']:
                rpm = self.ir[rpm_field]
                if rpm is not None:
                    telemetry['rpm'] = rpm
                    break
            
            # Gear
            for gear_field in ['Gear', 'gear', 'CarIdxGear']:
                gear = self.ir[gear_field]
                if gear is not None:
                    telemetry['gear'] = gear
                    break
            
            # Current Lap Time (time in current lap)
            for current_lap_field in ['LapCurrentLapTime', 'lap_time', 'current_lap_time']:
                current_lap_time = self.ir[current_lap_field]
                if current_lap_time is not None:
                    telemetry['lap_time'] = current_lap_time
                    break
            
            # Last Lap Time (completed lap time)
            for last_lap_field in ['LapLastLapTime', 'last_lap_time']:
                last_lap_time = self.ir[last_lap_field]
                if last_lap_time is not None and last_lap_time > 0:
                    # Only log when the last lap time changes
                    if not hasattr(self, '_last_recorded_lap_time') or self._last_recorded_lap_time != last_lap_time:
                        logger.info(f"Updated last lap time: {last_lap_time:.3f} seconds")
                        self._last_recorded_lap_time = last_lap_time
                    telemetry['last_lap_time'] = last_lap_time
                    break
            
            # Best Lap Time
            for best_lap_field in ['LapBestLapTime', 'best_lap_time']:
                best_lap_time = self.ir[best_lap_field]
                if best_lap_time is not None and best_lap_time > 0:
                    telemetry['best_lap_time'] = best_lap_time
                    # Only log when the best lap time changes
                    if not hasattr(self, '_last_best_lap') or self._last_best_lap != best_lap_time:
                        logger.info(f"New best lap time: {best_lap_time:.3f} seconds")
                        self._last_best_lap = best_lap_time
                    break
            
            # Lap Count
            for lap_count_field in ['Lap', 'LapCompleted', 'lap', 'lap_completed']:
                lap_count = self.ir[lap_count_field]
                if lap_count is not None:
                    telemetry['lap_count'] = lap_count
                    break
            
            # Session Time
            for session_time_field in ['SessionTime', 'session_time']:
                session_time = self.ir[session_time_field]
                if session_time is not None:
                    telemetry['session_time'] = session_time
                    break
            
            # Track Position (percentage around track)
            for track_pos_field in ['LapDistPct', 'lap_dist_pct']:
                track_pos = self.ir[track_pos_field]
                if track_pos is not None:
                    telemetry['track_position'] = track_pos
                    break
            
            # Throttle input - add driver input data 
            for throttle_field in ['Throttle', 'throttle', 'ThrottleRaw']:
                throttle = self.ir[throttle_field]
                if throttle is not None:
                    telemetry['throttle'] = throttle  # Value between 0-1
                    break
            
            # Brake input
            for brake_field in ['Brake', 'brake', 'BrakeRaw']:
                brake = self.ir[brake_field]
                if brake is not None:
                    telemetry['brake'] = brake  # Value between 0-1
                    break
            
            # Clutch input
            for clutch_field in ['Clutch', 'clutch', 'ClutchRaw']:
                clutch = self.ir[clutch_field]
                if clutch is not None:
                    telemetry['clutch'] = clutch  # Value between 0-1
                    break
            
            # Steering wheel angle input
            for steering_field in ['SteeringWheelAngle', 'steeringWheelAngle']:
                steering = self.ir[steering_field]
                if steering is not None:
                    telemetry['steering'] = steering  # Value in radians
                    break
            
            # Also get max steering wheel angle if available
            for max_steering_field in ['SteeringWheelAngleMax', 'steeringWheelAngleMax']:
                max_steering = self.ir[max_steering_field]
                if max_steering is not None and max_steering > 0:
                    telemetry['steering_max'] = max_steering  # Value in radians
                    break
            
            # Only log telemetry occasionally to avoid flooding logs
            if not hasattr(self, '_telemetry_log_counter'):
                self._telemetry_log_counter = 0
            
            self._telemetry_log_counter += 1
            if self._telemetry_log_counter % 600 == 0:  # Log every 10 seconds (at 60Hz)
                # Log what we found
                log_values = {k: v for k, v in telemetry.items() if v is not None}
                logger.debug(f"Telemetry data: {log_values}")
                
                # Specifically log lap times for debugging
                if 'lap_time' in telemetry:
                    logger.info(f"Current lap time: {telemetry['lap_time']:.3f}")
                if 'last_lap_time' in telemetry:
                    logger.info(f"Last lap time: {telemetry['last_lap_time']:.3f}")
                if 'best_lap_time' in telemetry:
                    logger.info(f"Best lap time: {telemetry['best_lap_time']:.3f}")
                
                # Log driver inputs when available
                if 'throttle' in telemetry:
                    logger.info(f"Throttle input: {telemetry['throttle']:.2f}")
                if 'brake' in telemetry:
                    logger.info(f"Brake input: {telemetry['brake']:.2f}")
                if 'clutch' in telemetry:
                    logger.info(f"Clutch input: {telemetry['clutch']:.2f}")
                if 'steering' in telemetry:
                    # Convert radians to degrees for more readable logs
                    steering_degrees = telemetry['steering'] * 180 / math.pi
                    logger.info(f"Steering angle: {steering_degrees:.2f}° ({telemetry['steering']:.2f} rad)")
            
            # Process telemetry with the telemetry saver
            if hasattr(self, 'telemetry_saver') and telemetry and 'track_position' in telemetry:
                lap_result = self.telemetry_saver.process_telemetry(telemetry)
                if lap_result:
                    # New lap detected
                    is_new_lap, lap_number, lap_time = lap_result
                    logger.info(f"New lap completed: Lap {lap_number}, Time: {lap_time:.3f}s")
                    
                    # Update telemetry with the manually calculated lap time if it's better
                    if 'best_lap_time' in telemetry:
                        if telemetry['best_lap_time'] <= 0 or lap_time < telemetry['best_lap_time']:
                            telemetry['best_lap_time'] = lap_time
                    else:
                        telemetry['best_lap_time'] = lap_time
            
            # Process telemetry with IRacingLapSaver for Supabase
            if self.lap_saver is not None and telemetry and 'track_position' in telemetry:
                # Add track and car name to telemetry for auto-session creation if needed
                if 'track_name' not in telemetry:
                    telemetry['track_name'] = self.get_current_track()
                if 'car_name' not in telemetry:
                    telemetry['car_name'] = self.get_current_car()
                
                # Process telemetry with lap saver
                try:
                    # Log once every 10 seconds to avoid spam
                    if self._telemetry_log_counter % 600 == 0:
                        logger.debug(f"Sending telemetry to Supabase lap saver: track_pos={telemetry.get('track_position', 'N/A')}")
                    
                    lap_result = self.lap_saver.process_telemetry(telemetry)
                    if lap_result:
                        # New lap detected in Supabase
                        is_new_lap, lap_number, lap_time = lap_result
                        logger.info(f"New lap completed in Supabase: Lap {lap_number}, Time: {lap_time:.3f}s")
                except Exception as e:
                    logger.error(f"Error processing telemetry with Supabase lap saver: {e}")
            
            # Notify callbacks if we have at least some data
            if telemetry and len(telemetry) > 0:
                # Update session info with lap times if they exist
                if 'best_lap_time' in telemetry and telemetry['best_lap_time'] > 0:
                    self._session_info['best_lap_time'] = telemetry['best_lap_time']
                
                if 'last_lap_time' in telemetry and telemetry['last_lap_time'] > 0:
                    self._session_info['last_lap_time'] = telemetry['last_lap_time']
                
                # Call telemetry callbacks
                for callback in self._telemetry_callbacks:
                    try:
                        # Add debug logging for driver inputs to track what's being sent
                        driver_inputs = {}
                        for input_name in ['throttle', 'brake', 'clutch']:
                            if input_name in telemetry:
                                driver_inputs[input_name] = telemetry[input_name]
                        
                        if driver_inputs and not hasattr(self, '_last_driver_inputs_log') or time.time() - self._last_driver_inputs_log > 10:
                            logger.debug(f"Sending driver inputs to UI: {driver_inputs}")
                            self._last_driver_inputs_log = time.time()
                            
                        callback(telemetry)
                    except Exception as e:
                        logger.error(f"Error in telemetry callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Always unfreeze the buffer, even if there was an error
            if buffer_frozen and hasattr(self.ir, 'unfreeze_var_buffer_latest'):
                try:
                    self.ir.unfreeze_var_buffer_latest()
                    buffer_frozen = False
                except Exception as e:
                    logger.error(f"Error unfreezing buffer: {e}")
    
    def register_on_connection_changed(self, callback):
        """Register a callback for connection status changes."""
        if callback not in self._connection_callbacks:
            self._connection_callbacks.append(callback)
    
    def register_on_session_info_changed(self, callback):
        """Register a callback for session info changes."""
        if callback not in self._session_info_callbacks:
            self._session_info_callbacks.append(callback)
    
    def register_on_telemetry_data(self, callback):
        """Register a callback for telemetry data updates."""
        if callback not in self._telemetry_callbacks:
            self._telemetry_callbacks.append(callback)
    
    def is_connected(self):
        """Check if connected to iRacing."""
        return self._is_connected and self.ir and self.ir.is_connected
    
    def disconnect(self):
        """Disconnect from iRacing."""
        if self.state.ir_connected:
            logger.info("Disconnecting from iRacing...")
            
            # Signal threads to stop
            self._stop_event.set()
            
            # Wait for threads to finish (with a timeout)
            try:
                if self._telemetry_timer and self._telemetry_timer.is_alive():
                    logger.info("Waiting for telemetry worker thread to stop...")
                    self._telemetry_timer.join(timeout=1.0) # Wait up to 1 second
                    if self._telemetry_timer.is_alive():
                         logger.warning("Telemetry worker thread did not stop gracefully.")
                    else:
                         logger.info("Telemetry worker thread stopped.")
                self._telemetry_timer = None # Clear reference
                
                if self._session_info_timer and self._session_info_timer.is_alive():
                    logger.info("Waiting for session info worker thread to stop...")
                    self._session_info_timer.join(timeout=1.0) # Wait up to 1 second
                    if self._session_info_timer.is_alive():
                         logger.warning("Session info worker thread did not stop gracefully.")
                    else:
                         logger.info("Session info worker thread stopped.")
                self._session_info_timer = None # Clear reference
            except Exception as e:
                 logger.error(f"Error joining worker threads: {e}")
            
            # End telemetry saving session
            if hasattr(self, 'telemetry_saver'):
                session_folder = self.telemetry_saver.end_session()
                logger.info(f"Saved telemetry data to {session_folder}")
            
            # Close Supabase session if lap saver exists
            if self.lap_saver is not None:
                try:
                    self.lap_saver.close_session()
                    logger.info("Closed Supabase lap session")
                except Exception as e:
                    logger.error(f"Error closing Supabase lap session: {e}")
            
            # Shutdown irsdk connection
            self.ir.shutdown()
            self.state.ir_connected = False
            self._is_connected = False
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