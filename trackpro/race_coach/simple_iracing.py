import irsdk
import time
import logging
import math
import threading
from pathlib import Path
from .telemetry_saver import TelemetrySaver
# from .integrate_simple_timing import SimpleSectorTimingIntegration  # REMOVED: Use main sector timing instead
from .sector_timing import SectorTimingCollector
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
        
        logger.info("SimpleIRacingAPI initialized")
    
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
        now = time.time()
        if now - self._last_rate_check_time >= 30.0:  # Check every 30 seconds instead of 5
            duration = now - self._telemetry_start_time
            rate = self._telemetry_count / duration if duration > 0 else 0
            logger.info(f"Telemetry collection rate: {rate:.2f} Hz (collected {self._telemetry_count} points over {duration:.2f}s)")
            self._last_rate_check_time = now

        # Debug: Check if IR object exists at all
        if not self.ir:
            logger.warning("IR object is None")
            return
        
        # Check if we are connected to iracing properly
        if not hasattr(self.ir, 'is_connected') or not self.ir.is_connected:
            if not hasattr(self, '_conn_error_counter'):
                self._conn_error_counter = 0
            self._conn_error_counter += 1
            if self._conn_error_counter % 1800 == 0:  # Every 30 seconds instead of 5
                logger.warning("IRSDK not connected")
            return

        try:
            # Freeze buffer to get consistent data as shown in example
            self.ir.freeze_var_buffer_latest()
            
            # Debug: Log all available variables occasionally
            if not hasattr(self, '_debug_counter'):
                self._debug_counter = 0
            self._debug_counter += 1
            
            # Every ~5 minutes call the debug function instead of 10 seconds
            if self._debug_counter % 18000 == 0:
                logger.info("Running iRacing variable debug function...")
                self.debug_ir_vars()
            
                            # ABS debug functionality removed
            
            # Create telemetry dictionary with DIRECT dictionary access
            # based on the example code pattern
            telemetry = {}
            
            # Session time is a good test variable
            session_time = None
            try:
                session_time = self.ir['SessionTime']
                if session_time is not None:
                    # Debug timing every 5 seconds instead of every frame
                    if hasattr(self, '_timing_debug_counter'):
                        self._timing_debug_counter += 1
                    else:
                        self._timing_debug_counter = 1
                    
                    # Only log session time every 300 frames (5 seconds at 60Hz)
                    if self._timing_debug_counter % 1800 == 0:  # Every 30 seconds instead of 5
                        logger.debug(f"Session time retrieved: {session_time}")
                    telemetry['SessionTimeSecs'] = session_time
            except Exception as e:
                if self._debug_counter % 1800 == 0:  # Every 30 seconds instead of 5
                    logger.warning(f"Failed to get SessionTime: {e}")
                    
            # Try to get LapDistPct - critical for lap detection
            try:
                lap_dist_pct = self.ir['LapDistPct']
                telemetry['LapDistPct'] = lap_dist_pct
                # Log this less frequently 
                if self._debug_counter % 3600 == 0:  # Every ~60 seconds instead of 2
                    logger.debug(f"LapDistPct: {lap_dist_pct}")
            except Exception as e:
                if self._debug_counter % 1800 == 0:  # Every 30 seconds instead of 5
                    logger.warning(f"Failed to get LapDistPct: {e}")
            
            # Try to get lap info - critical for lap tracking
            try:
                current_lap = self.ir['Lap']
                lap_completed = self.ir['LapCompleted']
                lap_current_time = self.ir['LapCurrentLapTime']
                lap_last_time = self.ir['LapLastLapTime']
                
                # EXACT TIMING: Get CarIdxLastLapTime array for precise lap timing
                car_idx_last_lap_times = self.ir['CarIdxLastLapTime']
                player_car_idx = self.ir['PlayerCarIdx']
                
                telemetry['Lap'] = current_lap
                telemetry['LapCompleted'] = lap_completed
                telemetry['LapCurrentLapTime'] = lap_current_time
                telemetry['LapLastLapTime'] = lap_last_time
                telemetry['CarIdxLastLapTime'] = car_idx_last_lap_times  # For exact timing
                telemetry['PlayerCarIdx'] = player_car_idx  # For indexing into car arrays
                
                # Log lap info much less frequently
                if self._debug_counter % 3600 == 0:  # Every 60 seconds instead of 1 second
                    logger.debug(f"Lap info: Current={current_lap}, Completed={lap_completed}, CurrentTime={lap_current_time}, LastTime={lap_last_time}")
                    if isinstance(car_idx_last_lap_times, (list, tuple)) and len(car_idx_last_lap_times) > player_car_idx:
                        our_exact_time = car_idx_last_lap_times[player_car_idx]
                        logger.debug(f"Exact timing: CarIdxLastLapTime[{player_car_idx}] = {our_exact_time:.3f}s")
            except Exception as e:
                if self._debug_counter % 1800 == 0:  # Every 30 seconds instead of 5
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
            
            # Ensure brake data is captured with proper case handling
            try:
                brake_value = float(self.ir['Brake'])  # Get raw brake value
                telemetry['Brake'] = brake_value  # Store with capital B for consistency
                telemetry['brake'] = brake_value  # Also store lowercase for compatibility
            except Exception as e:
                logger.warning(f"Failed to get brake value: {e}")
                telemetry['Brake'] = 0.0
                telemetry['brake'] = 0.0
            
            try: telemetry['Clutch'] = self.ir['Clutch']
            except: telemetry['Clutch'] = None
            
            try: telemetry['SteeringWheelAngle'] = self.ir['SteeringWheelAngle']
            except: telemetry['SteeringWheelAngle'] = None
            
            try: telemetry['SteeringWheelAngleMax'] = self.ir['SteeringWheelAngleMax']
            except: telemetry['SteeringWheelAngleMax'] = None

            # --- WHEEL RPM DATA FOR TELEMETRY --- #
                            # Wheel RPM data for telemetry
            wheel_rpm_fields = ['WheelLFRPM', 'WheelRFRPM', 'WheelLRRPM', 'WheelRRRPM']
            wheel_rpms_found = []
            
            for wheel_field in wheel_rpm_fields:
                try:
                    wheel_rpm = self.ir[wheel_field]
                    telemetry[wheel_field] = float(wheel_rpm)
                    wheel_rpms_found.append(wheel_field)
                except:
                    # Try alternative field names
                    alt_field = wheel_field.replace('RPM', 'Rpm').replace('WheelLF', 'WheelLF').replace('WheelRF', 'WheelRF').replace('WheelLR', 'WheelLR').replace('WheelRR', 'WheelRR')
                    try:
                        wheel_rpm = self.ir[alt_field]
                        telemetry[wheel_field] = float(wheel_rpm)
                        wheel_rpms_found.append(f"{wheel_field} (as {alt_field})")
                    except:
                        telemetry[wheel_field] = 0.0
            
            # Log wheel RPM status occasionally
            if self._debug_counter % 10800 == 0 and wheel_rpms_found:  # Every 3 minutes instead of 5 seconds
                logger.info(f"✅ Found wheel RPMs: {wheel_rpms_found}")
            elif self._debug_counter % 21600 == 0 and len(wheel_rpms_found) < 4:  # Every 6 minutes instead of 10 seconds
                logger.warning(f"⚠️ Missing wheel RPMs: {[f for f in wheel_rpm_fields if f not in [w.split(' ')[0] for w in wheel_rpms_found]]}")

            # ABS field detection removed - no longer needed for lockup detection
            
            # Try multiple possible field names for longitudinal acceleration
            accel_found = False
            for accel_field in ['LongAccel', 'AccelLongitudinal', 'AccelLong', 'LongitudalAccel']:
                try: 
                    long_accel = self.ir[accel_field]
                    telemetry['LongAccel'] = float(long_accel)
                    accel_found = True
                    if self._debug_counter % 21600 == 0:  # Log success every 6 minutes instead of 10 seconds
                        logger.info(f"✅ Found acceleration field: {accel_field} = {long_accel}")
                    break
                except: 
                    continue
            
            if not accel_found:
                if self._debug_counter % 10800 == 0:  # Every 3 minutes instead of 5 seconds
                    logger.warning(f"❌ No acceleration field found - tried: LongAccel, AccelLongitudinal, AccelLong, LongitudalAccel")
                telemetry['LongAccel'] = 0.0
            
            try: 
                lat_accel = self.ir['LatAccel']
                telemetry['LatAccel'] = float(lat_accel)
            except Exception as e: 
                telemetry['LatAccel'] = 0.0
            
            try: 
                vert_accel = self.ir['VelocityZ']  # Alternative for vertical velocity
                telemetry['VelocityZ'] = float(vert_accel)
            except Exception as e: 
                telemetry['VelocityZ'] = 0.0

            # --- Handle OnPitRoad (Critical for Lap Classification) --- #
            try:
                # Try multiple possible key variations for pit road status
                # First try the standard name with exact case
                pit_status = self.ir['OnPitRoad']
                telemetry['OnPitRoad'] = bool(pit_status)
                if self._debug_counter % 300 == 0:
                    logger.info(f"Got OnPitRoad status: {pit_status}")
            except Exception as e1:
                try:
                    # Try lowercase variation
                    pit_status = self.ir['onpitroad']
                    telemetry['OnPitRoad'] = bool(pit_status)
                    if self._debug_counter % 300 == 0:
                        logger.info(f"Got onpitroad status (lowercase): {pit_status}")
                except Exception as e2:
                    try:
                        # Try alternative keys that might contain pit status
                        pit_status = self.ir['CarIdxOnPitRoad']
                        # If it's an array for multiple cars, get the player's status
                        if isinstance(pit_status, (list, tuple)) and len(pit_status) > 0:
                            # Get the player's car index
                            player_idx = self._get_player_car_idx()
                            if player_idx < len(pit_status):
                                telemetry['OnPitRoad'] = bool(pit_status[player_idx])
                                if self._debug_counter % 300 == 0:
                                    logger.info(f"Got CarIdxOnPitRoad status for player idx {player_idx}: {pit_status[player_idx]}")
                            else:
                                # Fallback to index 0 if player index is out of range
                                telemetry['OnPitRoad'] = bool(pit_status[0])
                                if self._debug_counter % 300 == 0:
                                    logger.info(f"Player idx {player_idx} out of range, using CarIdxOnPitRoad[0]: {pit_status[0]}")
                        else:
                            telemetry['OnPitRoad'] = bool(pit_status)
                    except Exception as e3:
                        try:
                            # Try checking if we're off track as a last resort
                            off_track = self.ir['IsOnTrack']
                            # If we're not on track, assume we might be in pits
                            telemetry['OnPitRoad'] = not bool(off_track)
                            if self._debug_counter % 300 == 0:
                                logger.info(f"Used IsOnTrack ({off_track}) as fallback for pit status")
                        except Exception as e4:
                            # Try to get pit status from session info as a last resort
                            pit_from_session = self._try_get_pit_status_from_session_info()
                            if pit_from_session is not None:
                                telemetry['OnPitRoad'] = pit_from_session
                                if self._debug_counter % 300 == 0:
                                    logger.info(f"Used session info for pit status: {pit_from_session}")
                            else:
                                # All attempts failed, log warning and use default
                                if self._debug_counter % 300 == 0:
                                    logger.warning(f"Failed to get pit road status through all methods")
                                # Keep as None or False
                                telemetry['OnPitRoad'] = False

            # --- Handle LapInvalidated (Also Critical) --- #
            try:
                lap_invalidated = self.ir['LapInvalidated']
                telemetry['LapInvalidated'] = bool(lap_invalidated)
            except Exception as e:
                try:
                    # Try lowercase variation
                    lap_invalidated = self.ir['lapinvalidated']
                    telemetry['LapInvalidated'] = bool(lap_invalidated)
                except Exception as e2:
                    # All attempts failed, log warning and use default
                    if self._debug_counter % 300 == 0:
                        logger.warning(f"Failed to get lap invalidated status: {e}, {e2}")
                    # Keep as None or False
                    telemetry['LapInvalidated'] = False

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

            # EXACT TIMING HELPER: Calculate our car's exact lap time for UI consistency
            # This matches the approach used in lap_indexer.py
            def get_our_exact_lap_time():
                """Get our car's exact lap time using CarIdxLastLapTime approach."""
                try:
                    car_idx_times = telemetry.get('CarIdxLastLapTime', [])
                    player_idx = telemetry.get('PlayerCarIdx', 0)
                    
                    if isinstance(car_idx_times, (list, tuple)) and len(car_idx_times) > player_idx:
                        return float(car_idx_times[player_idx])
                    else:
                        # Fallback to regular LapLastLapTime if CarIdx data not available
                        return telemetry.get('LapLastLapTime', 0.0)
                except Exception:
                    return telemetry.get('LapLastLapTime', 0.0)
            
            # CRITICAL FIX: Only log telemetry data occasionally, not every frame
            current_time = time.time()
            should_log_telemetry = not hasattr(self, '_last_telemetry_log_time') or (current_time - (getattr(self, '_last_telemetry_log_time', None) or 0) > 30.0)
            
            if should_log_telemetry:
                logger.info(f"Telemetry sample: Lap {telemetry.get('Lap', 'N/A')}, LapCompleted {telemetry.get('LapCompleted', 'N/A')}, Speed {telemetry.get('Speed', 'N/A')}")
                self._last_telemetry_log_time = current_time
            
            # --- Pass to TelemetrySaver, LapSaver, and SectorTiming --- #
            # Ensure essential data exists before passing
            if telemetry.get('LapDistPct') is not None and telemetry.get('SessionTimeSecs') is not None:
                
                # NOTE: Removed frame-based future sector data application
                # Sector data is now stored by lap number and retrieved by the lap saver
                
                lap_info_to_pass_to_ui = None
                
                # Process sector timing
                if hasattr(self, 'sector_timing') and self.sector_timing and self.sector_timing.is_enabled:
                    # Add debug logging about sector timing
                    if not hasattr(self, '_sector_debug_counter'):
                        self._sector_debug_counter = 0
                    self._sector_debug_counter += 1
                    
                    # Only log sector timing debug every 5 minutes instead of every frame
                    if self._sector_debug_counter % 18000 == 0:  # 60Hz * 60s * 5min = 18000
                        logger.debug(f"🔧 [SIMPLE SECTOR] About to call sector_timing.process_telemetry() - enabled: {self.sector_timing.is_enabled}")
                        logger.debug(f"🔧 [SIMPLE SECTOR] Telemetry data keys: {list(telemetry.keys())}")
                        logger.debug(f"🔧 [SIMPLE SECTOR] LapDistPct: {telemetry.get('LapDistPct')}, Lap: {telemetry.get('Lap')}")
                    
                    sector_result = self.sector_timing.process_telemetry(telemetry)
                    
                    # Only log sector result every 5 minutes instead of every frame
                    if self._sector_debug_counter % 18000 == 0:
                        logger.debug(f"🔧 [SIMPLE SECTOR] sector_timing.process_telemetry() returned: {sector_result}")
                    
                    if sector_result:
                        # Add current sector progress to telemetry
                        telemetry['current_sector'] = sector_result.get('current_sector', 1)
                        telemetry['current_sector_time'] = sector_result.get('current_sector_time', 0.0)
                        telemetry['best_sector_times'] = sector_result.get('best_sector_times', [])
                        telemetry['current_lap_splits'] = sector_result.get('current_lap_splits', [])
                        telemetry['completed_sectors_count'] = sector_result.get('completed_sectors', 0)
                        telemetry['sector_timing_initialized'] = True
                        telemetry['total_sectors'] = sector_result.get('total_sectors', 0)
                        
                        # CRITICAL FIX: Add current lap sector timing data that lap saver expects
                        telemetry['current_lap_sector_times'] = sector_result.get('current_lap_splits', [])
                        telemetry['sector_timing_method'] = sector_result.get('timing_method', '10_equal_sectors')
                        
                        # Check if a lap was completed
                        completed_lap = sector_result.get('completed_lap')
                        if completed_lap:
                            logger.info(f"🏁 SIMPLE sector timing completed lap {completed_lap['lap_number']}: {completed_lap['total_time']:.3f}s")
                            
                            # CRITICAL FIX: Create complete sector data package for this and recent frames
                            sector_data_package = {
                                'sector_times': completed_lap['sector_times'],
                                'sector_total_time': completed_lap['total_time'],
                                'sector_lap_completed': True,
                                'sector_completion_frame_id': self._telemetry_count
                            }
                            
                            # Add individual sector fields that lap saver expects
                            for i, sector_time in enumerate(completed_lap['sector_times']):
                                sector_data_package[f'sector{i+1}_time'] = sector_time
                            
                            # Also copy any other sector-related fields from the result
                            for key, value in sector_result.items():
                                if key.startswith('sector') and key.endswith('_time'):
                                    sector_data_package[key] = value
                            
                            # Add to current telemetry frame
                            telemetry.update(sector_data_package)
                            
                            # CRITICAL: Store completed sector data with lap-specific identification
                            if not hasattr(self, '_lap_sector_data'):
                                self._lap_sector_data = {}
                            
                            lap_number = completed_lap['lap_number']
                            
                            # Store sector data with lap number as key (not frame-based)
                            self._lap_sector_data[lap_number] = {
                                'sector_times': completed_lap['sector_times'],
                                'sector_total_time': completed_lap['total_time'],
                                'timestamp': time.time(),
                                'frame_id': self._telemetry_count
                            }
                            
                            # Clean up old lap data (keep only last 5 laps)
                            if len(self._lap_sector_data) > 5:
                                old_laps = sorted(self._lap_sector_data.keys())[:-5]
                                for old_lap in old_laps:
                                    del self._lap_sector_data[old_lap]
                            
                            logger.info(f"🔧 [LAP SECTOR STORAGE] Stored complete sector data for lap {lap_number}: {completed_lap['sector_times']}")
                            logger.info(f"🔧 [SIMPLE SECTOR] Added completed sector data to frame: {completed_lap['sector_times']}")
                            logger.debug(f"✅ [SECTOR FIX] Added individual sector fields: sector1_time through sector{len(completed_lap['sector_times'])}_time")
                        else:
                            # Mark that no lap was completed this frame
                            telemetry['sector_lap_completed'] = False
                        
                        # Log sector progress occasionally
                        if not hasattr(self, '_last_sector_log_time') or (current_time - self._last_sector_log_time > 10):
                            logger.info(f"🏁 SIMPLE Current sector: {sector_result.get('current_sector', 'N/A')}/{sector_result.get('total_sectors', 'N/A')}, Time: {sector_result.get('current_sector_time', 0):.2f}s")
                            logger.debug(f"🔧 [SIMPLE SECTOR] Adding to frame: current_lap_splits={sector_result.get('current_lap_splits', [])}, completed_sectors={sector_result.get('completed_sectors', 0)}")
                            self._last_sector_log_time = current_time
                    else:
                        # Don't add sector data if not initialized
                        telemetry['current_sector'] = None
                        telemetry['current_sector_time'] = None
                        telemetry['best_sector_times'] = None
                        telemetry['sector_timing_initialized'] = False
                
                if self.telemetry_saver: 
                    lap_info_to_pass_to_ui = self.telemetry_saver.process_telemetry(telemetry)
                if self.lap_saver:
                    try:
                         # Process telemetry through the improved LapIndexer (which now has conservative reset detection)
                         # The LapIndexer.on_frame() method handles all reset detection and lap boundary detection internally
                         lap_result_supabase = self.lap_saver.process_telemetry(telemetry)
                         if lap_result_supabase: lap_info_to_pass_to_ui = lap_result_supabase
                    except Exception as e:
                        logger.error(f"Error processing telemetry with Supabase lap saver: {e}")

                # --- Notify Callbacks --- #
                if telemetry:
                    # Always trigger callbacks for real-time telemetry (AI coach needs this!)
                    display_telemetry = telemetry.copy()
                    display_telemetry['speed'] = speed * 3.6  # Convert for UI
                    
                    # Store current telemetry for external access
                    self.current_telemetry = telemetry.copy()
                    
                    # Always trigger telemetry callbacks for real-time data (regardless of lap processing)
                    # Only log callback debug info every 10 seconds to reduce spam
                    if self._telemetry_count % 600 == 0:  # Every 10 seconds at ~60Hz
                        logger.debug(f"🎙️ [TELEMETRY CALLBACKS] Triggering {len(self._telemetry_callbacks)} callbacks with telemetry data")
                    for callback in self._telemetry_callbacks:
                        try: 
                            callback(display_telemetry)
                        except Exception as e: 
                            logger.error(f"Error in telemetry callback: {e}")
                    
                    # Process lap information for UI display if available
                    if lap_info_to_pass_to_ui:
                        # Properly handle different formats of lap_info_to_pass_to_ui
                        if isinstance(lap_info_to_pass_to_ui, (list, tuple)) and len(lap_info_to_pass_to_ui) > 0:
                            # Handle the expected list/tuple format
                            telemetry['is_new_lap'] = lap_info_to_pass_to_ui[0]
                            if len(lap_info_to_pass_to_ui) > 1:
                                telemetry['completed_lap_number'] = lap_info_to_pass_to_ui[1]
                            if len(lap_info_to_pass_to_ui) > 2:
                                telemetry['completed_lap_time'] = lap_info_to_pass_to_ui[2]
                        elif isinstance(lap_info_to_pass_to_ui, dict):
                            # Handle when it's a dictionary (directly from telemetry)
                            # Use EXACT timing approach consistent with lap_indexer
                            telemetry['is_new_lap'] = lap_info_to_pass_to_ui.get('is_new_lap', False)
                            telemetry['completed_lap_number'] = lap_info_to_pass_to_ui.get('LapCompleted', telemetry.get('LapCompleted', 0))
                            telemetry['completed_lap_time'] = get_our_exact_lap_time()  # Use exact timing
                            # Only log once per ~10 seconds to reduce spam
                            if self._telemetry_count % 600 == 0:
                                logger.debug(f"Handled dictionary format for lap_info: {telemetry['is_new_lap']}, {telemetry['completed_lap_number']}, {telemetry['completed_lap_time']}")
                        else:
                            # Set default values if lap_info_to_pass_to_ui is not in the expected format
                            # Use EXACT timing approach consistent with lap_indexer
                            telemetry['is_new_lap'] = False
                            telemetry['completed_lap_number'] = telemetry.get('LapCompleted', 0)
                            telemetry['completed_lap_time'] = get_our_exact_lap_time()  # Use exact timing
                            # Only log once per ~10 seconds to reduce spam
                            if self._telemetry_count % 600 == 0:
                                logger.warning(f"lap_info_to_pass_to_ui in unexpected format: {type(lap_info_to_pass_to_ui)}")
                        
                        # Lap information processed successfully - no additional callback processing needed
                        # (callbacks were already triggered above regardless of lap processing)
            elif self._telemetry_count % 60 == 0:
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