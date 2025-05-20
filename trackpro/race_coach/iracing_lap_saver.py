"""
Module for saving iRacing lap times and telemetry data to Supabase.
"""

import os
import time
import logging
import uuid
import json
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool

# Import the Supabase singleton client instead of creating a new one
from ..database.supabase_client import supabase

# Import the new LapIndexer
from .lap_indexer import LapIndexer

# Setup logging
logger = logging.getLogger(__name__)

class SaveLapWorkerSignals(QObject):
    """
    Defines signals available from a running SaveLapWorker thread.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str, str)  # lap_number_str, error_message
    lap_saved = pyqtSignal(str, str, float, str, bool)  # lap_uuid, lap_number_str, lap_time, session_id, telemetry_saved_successfully
    progress = pyqtSignal(str) # message

class SaveLapWorker(QRunnable):
    """
    Worker thread for saving lap data and telemetry to Supabase.
    """
    def __init__(self, supabase_client, user_id, session_id, lap_payload, lap_frames, lap_number_str):
        super().__init__()
        self.supabase = supabase_client
        self.user_id = user_id
        self.session_id = session_id
        self.lap_payload = lap_payload
        self.lap_frames = lap_frames
        self.lap_number_str = lap_number_str # Keep as string for signals if needed
        self.signals = SaveLapWorkerSignals()

    def run(self):
        try:
            lap_uuid = self.lap_payload.get("lap_uuid")
            session_id = self.lap_payload.get("session_id")
            # self.lap_number_str is already an attribute
            lap_time = self.lap_payload.get("lap_time")
            is_valid_for_leaderboard = self.lap_payload.get("is_valid_for_leaderboard", True)
            is_complete_lap = self.lap_payload.get("is_complete_lap", True)
            track_coverage = self.lap_payload.get("track_coverage")
            # started_on_pit_road = self.lap_payload.get("started_on_pit_road") # Not in DB schema for 'laps'
            # ended_on_pit_road = self.lap_payload.get("ended_on_pit_road") # Not in DB schema for 'laps'

            # --- BEGIN ADDED LOGGING ---
            num_frames_to_save = len(self.lap_frames) if self.lap_frames else 0
            first_frame_session_time = 'N/A'
            last_frame_session_time = 'N/A'
            if num_frames_to_save > 0:
                first_frame_session_time = self.lap_frames[0].get('SessionTimeSecs', 'N/A')
                last_frame_session_time = self.lap_frames[-1].get('SessionTimeSecs', 'N/A')

            logger.info(
                f"[SaveLapWorker.run] Attempting to save. LapUUID: {lap_uuid}, LapNumStr: {self.lap_number_str}, "
                f"SessionID: {session_id}, NumFramesToSave: {num_frames_to_save}, "
                f"FirstFrameTime: {first_frame_session_time}, LastFrameTime: {last_frame_session_time}"
            )
            # --- END ADDED LOGGING ---

            # 1. Insert the lap record
            lap_insert_data = {
                "id": lap_uuid,
                "session_id": session_id,
                "lap_number": int(self.lap_number_str) if self.lap_number_str.isdigit() else None,
                "lap_time": lap_time,
                "user_id": self.user_id,
                "is_valid_for_leaderboard": is_valid_for_leaderboard,
                "is_complete": is_complete_lap,
                "track_coverage_percent": track_coverage,
                "lap_number_str": self.lap_number_str # Store the string version for robustness
                # Note: started_on_pit_road and ended_on_pit_road are not in the 'laps' table schema
            }
            
            self.signals.progress.emit(f"Saving lap {self.lap_number_str} record...")
            
            response = self.supabase.table("laps").insert(lap_insert_data).execute()

            if hasattr(response, 'error') and response.error:
                logger.error(f"Error saving lap record for lap {self.lap_number_str} (UUID: {lap_uuid}): {response.error.message}")
                self.signals.error.emit(self.lap_number_str, f"DB error (lap record): {response.error.message}")
                self.signals.finished.emit()
                return
                
            logger.info(f"Lap record for lap {self.lap_number_str} (UUID: {lap_uuid}) saved successfully.")

            # 2. Save telemetry points if frames are available
            telemetry_saved_successfully = False # Default to failure
            saved_count = 0
            failed_count = 0

            if self.lap_frames:
                logger.info(f"Worker: Initiating save of {len(self.lap_frames)} telemetry points for lap {lap_uuid}")
                
                telemetry_points_to_save = []
                for frame in self.lap_frames:
                    # Ensure all required fields are present, provide defaults if not
                    point_data = {
                        'lap_id': lap_uuid,
                        'timestamp': frame.get('SessionTimeSecs', 0.0),
                        'track_position': frame.get('LapDistPct', 0.0),
                        'speed': frame.get('Speed', 0.0),
                        'throttle': frame.get('Throttle', 0.0),
                        'brake': frame.get('Brake', 0.0),
                        'steering_angle': frame.get('SteeringWheelAngle', 0.0),
                        'gear': frame.get('Gear', 0),
                        'rpm': frame.get('RPM', 0.0)
                    }
                    telemetry_points_to_save.append(point_data)
                
                # _save_telemetry_points_to_db returns: (bool_overall_success, int_total_saved_points)
                # It internally logs detailed batch save/fail counts.
                overall_db_success, total_points_saved_in_db = self._save_telemetry_points_to_db(lap_uuid, telemetry_points_to_save)
                
                telemetry_saved_successfully = overall_db_success # Directly use the success flag
                
                # Log the outcome from the perspective of the run() method after calling the batch processor.
                logger.info(f"Worker: Telemetry database operation finished for {lap_uuid}. Overall success: {telemetry_saved_successfully}. Points reported as saved by batch processor: {total_points_saved_in_db} (out of {len(self.lap_frames)} total frames for this lap).")

            else: # No frames to save
                logger.info(f"Worker: No telemetry frames to save for lap {lap_uuid}")
                telemetry_saved_successfully = True # Vacuously true as no save was needed/attempted for telemetry.
            
            # Emit lap_saved signal
            self.signals.lap_saved.emit(lap_uuid, self.lap_number_str, lap_time, session_id, telemetry_saved_successfully)

        except Exception as e:
            lap_uuid_for_error = self.lap_payload.get("lap_uuid", "UNKNOWN_UUID") if hasattr(self, 'lap_payload') else "UNKNOWN_PAYLOAD_UUID"
            logger.exception(f"Unhandled exception in SaveLapWorker for lap {self.lap_number_str} (UUID: {lap_uuid_for_error}): {e}")
            self.signals.error.emit(self.lap_number_str, f"Worker exception: {str(e)}")
        finally:
            self.signals.finished.emit()

    def _save_telemetry_points_to_db(self, lap_uuid, telemetry_points):
        """Internal helper to save telemetry points, mirrors original logic."""
        # This method is essentially a copy of the original _save_telemetry_points' core logic
        # Ensure self.supabase and self.user_id are used from the worker's attributes
        if not self.supabase or not lap_uuid or not telemetry_points:
            logger.warning("Worker: Cannot save telemetry: Missing Supabase client, lap ID, or telemetry data.")
            return False, 0
    
        logger.info(f"Worker: Saving {len(telemetry_points)} telemetry points for lap {lap_uuid}")
        batch_size = 100 
        saved_count = 0
        failed_count = 0
        failed_batch_indices = []
        
        def get_sort_key(point):
            if 'track_position' in point: return point['track_position']
            return point.get('LapDistPct', 0)

        sorted_points = sorted(telemetry_points, key=get_sort_key)
        
        for i in range(0, len(sorted_points), batch_size):
            batch = sorted_points[i:i + batch_size]
            telemetry_data_to_insert = []
            for point in batch:
                telemetry_data_to_insert.append({
                    "lap_id": lap_uuid,
                    "user_id": self.user_id,
                    "timestamp": point.get('timestamp', point.get('SessionTimeSecs', point.get('SessionTickTime', 0))),
                    "track_position": point.get('track_position', point.get('LapDistPct', 0)),
                    "speed": point.get('speed', point.get('Speed', 0)),
                    "rpm": point.get('rpm', point.get('RPM', 0)),
                    "gear": point.get('gear', point.get('Gear', 0)),
                    "throttle": point.get('throttle', point.get('Throttle', 0)),
                    "brake": point.get('brake', point.get('Brake', 0)),
                    "clutch": point.get('clutch', point.get('Clutch', 0)),
                    "steering": point.get('steering', point.get('SteeringWheelAngle', 0)),
                    "lat_accel": point.get('lat_accel', point.get('LatAccel', 0)),
                    "long_accel": point.get('long_accel', point.get('LongAccel', 0)),
                    "batch_index": i // batch_size
                })
            
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = self.supabase.table("telemetry_points").insert(telemetry_data_to_insert).execute()
                    if response.data:
                        saved_count += len(response.data)
                        break 
                    else:
                        logger.warning(f"Worker: Batch {i // batch_size} save attempt {retry+1} returned no data")
                        if retry == max_retries - 1:
                            failed_count += len(telemetry_data_to_insert)
                            failed_batch_indices.append(i // batch_size)
                except Exception as e:
                    logger.error(f"Worker: Error saving batch {i // batch_size}, attempt {retry+1}: {e}")
                    if retry == max_retries - 1:
                        failed_count += len(telemetry_data_to_insert)
                        failed_batch_indices.append(i // batch_size)
        
        success = failed_count == 0
        logger.info(f"Worker: Telemetry saving complete for {lap_uuid}: Saved: {saved_count}, Failed: {failed_count}, Success: {success}")
        
        if failed_count > 0:
            try:
                self.supabase.table("laps").update({
                    "metadata": json.dumps({
                        "telemetry_incomplete": True,
                        "failed_batches": failed_batch_indices,
                        "points_saved": saved_count,
                        "points_failed": failed_count
                    })
                }).eq("id", lap_uuid).execute()
                logger.warning(f"Worker: Marked lap {lap_uuid} as having incomplete telemetry")
            except Exception as e:
                logger.error(f"Worker: Error updating lap record for incomplete telemetry: {e}")
        
        return success, saved_count

class IRacingLapSaver:
    """
    Manages saving iRacing lap times and telemetry data to Supabase.
    """
    # Add signals for IRacingLapSaver itself if it needs to communicate save status upwards
    # For now, we'll handle worker signals internally or log them.

    @property
    def user_id(self):
        """Get the current user ID"""
        return self._user_id
    
    @property
    def session_id(self):
        """Get the current session ID"""
        return self._current_session_id
        
    def __init__(self):
        """Initialize the saver."""
        # Logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("IRACING_LAP_SAVER_INIT_V_001 --- RELOAD TEST ---") # Unique debug print
        self.threadpool = QThreadPool()
        self.logger.info(f"IRacingLapSaver initialized with QThreadPool. Max threads: {self.threadpool.maxThreadCount()}")
        
        # Initialize LapIndexer
        self.lap_indexer = LapIndexer()
        
        # Keep track of lap numbers processed from LapIndexer to avoid duplicates
        self._processed_lap_indexer_lap_numbers = set()
        
        # Supabase connection
        self._supabase = None
        self._connection_disabled = False
        
        # User identification
        self._user_id = None
        
        # Session tracking
        self._current_session_id = None
        self._current_car_id = None
        self._current_track_id = None
        self._current_session_type = None
        
        # Lap tracking
        self._is_first_telemetry = True
        self._current_lap_data = []
        self._current_lap_number = 0
        self._last_track_position = 0
        self._lap_start_time = 0
        self._current_lap_id = None
        self._best_lap_time = float('inf')
        
        # Stats tracking
        self._total_laps_detected = 0
        self._total_laps_saved = 0
        self._total_laps_skipped = 0
        self._lap_recording_status = {}
        self._partial_laps = {}
        
        # Enhanced detection with buffer
        self._position_buffer_size = 20  # Increased from original value for more robust detection
        self._recent_positions = []
        self._recent_timestamps = []
        
        # Minimum lap time in seconds to prevent double-counts
        self._min_lap_time = 10  # Increased for safety
        self._last_lap_end_time = 0
        
        # Lap validation thresholds
        self._track_coverage_threshold = 0.6  # Require 60% coverage for a valid lap
        
        # Car status tracking
        self._is_in_pit = False
        self._last_pit_state = False
        self._pit_entry_time = 0
        self._short_lap_times = []  # Store short lap times that might be pit entries/exits
        
        # Diagnostics
        self._diagnostic_mode = False
        self._position_log_file = None
        self._telemetry_debug_counter = 0
        
        # Setup telemetry debug counter
        self._debug_interval = 300  # Log debug info every ~300 iterations

        self.last_auth_nag_time = 0.0

        self.supabase_client = None
        self.pending_saves = {} # lap_uuid -> SaveLapWorker

        # Internal state
        self._supabase = None
        self._user_id = None
        self._current_session_id = None
        self._current_car_id = None
        self._current_track_id = None
        self._current_session_type = None
        self._in_valid_session_state = False
        self._telemetry_warning_count = 0
        
        # Lap indexing
        self.lap_indexer = LapIndexer()
        
        # Diagnostics
        self._diagnostics_enabled = False
        self._partial_lap_save_enabled = True
        
        # State for tracking whether we're on pit road
        self._on_pit_road = False
        self._last_lap_started_on_pit = False
        
        # Session tracking
        self._active_session_start_time = None
        self._session_lap_counts = {}

    def set_supabase_client(self, client):
        """Set the Supabase client instance."""
        self._supabase = client
        if client:
            logger.info(f"Supabase client set for IRacingLapSaver: {client is not None}")
            self._connection_disabled = False
            
            # Test connection immediately to verify it's working
            try:
                if hasattr(self._supabase, 'table'):
                    # Try a simple query to verify the connection works
                    test_result = self._supabase.table('tracks').select('id').limit(1).execute()
                    if hasattr(test_result, 'data'):
                        logger.info(f"Supabase connection test successful: Got {len(test_result.data)} tracks")
                    else:
                        logger.warning("Supabase connection test returned no data attribute")
                else:
                    logger.warning("Supabase client has no 'table' method")
            except Exception as e:
                logger.error(f"Supabase connection test failed: {e}")
                
        else:
            logger.warning("Supabase client removed or not set - client is None")
            self._connection_disabled = True

        # Fallback: if no client provided, try to get from global singleton
        if not self._supabase:
            try:
                # Import here to avoid circular imports
                from ..database.supabase_client import supabase as global_client
                if global_client:
                    logger.info("Using global Supabase client instance as fallback")
                    self._supabase = global_client
                    self._connection_disabled = False
                    # No return here, let it flow to the end
            except Exception as e:
                logger.error(f"Error getting global Supabase client: {e}")
                self._connection_disabled = True

    def set_user_id(self, user_id):
        """Set the current user ID for associating data."""
        self._user_id = user_id
        logger.info(f"Set user ID to: {user_id}")
        
    def start_session(self, track_name, car_name, session_type="Race"):
        """
        Initialize a new session for tracking laps.
        
        Args:
            track_name (str): The name of the track
            car_name (str): The name of the car
            session_type (str): Type of session (e.g., "Race", "Practice", "Qualify")
            
        Returns:
            str: The session ID if successful, None if failed
        """
        self.logger.info(f"Starting new session: Track={track_name}, Car={car_name}, Type={session_type}")
        
        # Validate required parameters
        if not all([track_name, car_name]):
            self.logger.error("Missing required parameters for start_session (track_name, car_name)")
            return None
        
        # Find or create track in database
        track_id = self._find_or_create_track(track_name)
        if not track_id:
            self.logger.error(f"Failed to find or create track: {track_name}")
            return None
            
        # Find or create car in database
        car_id = self._find_or_create_car(car_name)
        if not car_id:
            self.logger.error(f"Failed to find or create car: {car_name}")
            return None
        
        # Create session in Supabase
        try:
            session_id = self._create_session_in_db(track_id, car_id, session_type)
            if not session_id:
                self.logger.error("Failed to create session in database")
                return None
                
            # Initialize session context with the new session ID
            self.start_new_session_context(session_id, car_id, track_id, session_type)
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            return None
            
    def _create_session_in_db(self, track_id, car_id, session_type):
        """Creates a session record in the database and returns the ID"""
        if not self.supabase or not self.user_id:
            self.logger.error("Cannot create session: Supabase client or user ID not set")
            return None
            
        try:
            # Create session record in Supabase
            response = self.supabase.table('sessions').insert({
                'user_id': self.user_id,
                'track_id': track_id,
                'car_id': car_id,
                'session_type': session_type,
                'started_at': datetime.now().isoformat(),
            }).execute()
            
            # Get the ID of the created session
            if response.data and len(response.data) > 0:
                session_id = response.data[0].get('id')
                self.logger.info(f"Created new session: {session_id}")
                return session_id
            else:
                self.logger.error(f"Failed to get session ID from response: {response}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating session in database: {str(e)}")
            return None

    def start_new_session_context(self, session_id, car_id, track_id, session_type=None):
        """Start a new lap recording session context.
        
        This method is called directly by the IRacingSessionMonitor or via start_session
        to initialize or update the current session context.
        
        Args:
            session_id: The Supabase UUID for the session
            car_id: The Supabase ID for the car
            track_id: The Supabase ID for the track
            session_type: The type of session (Race, Practice, etc.)
        """
        # Store current session info
        self._current_session_id = session_id
        self._current_car_id = car_id
        self._current_track_id = track_id
        self._current_session_type = session_type
        
        # Reset internal state
        self._is_first_telemetry = True
        
        # Reset lap indexer
        logger.info("Resetting lap indexer for new session context")
        if hasattr(self, 'lap_indexer') and self.lap_indexer:
            self.lap_indexer.reset_internal_lap_state()
        
        logger.info(f"Starting new session context: SessionID={session_id}, CarID={car_id}, TrackID={track_id}, SessionType='{session_type}'")
        
        return True

    def enable_diagnostics(self, enabled=True):
        """Enable detailed diagnostic mode for troubleshooting."""
        self._diagnostic_mode = enabled
        if enabled:
            logger.setLevel(logging.DEBUG)
            # Create a diagnostic log file in user's documents
            docs_path = Path(os.path.expanduser("~/Documents/TrackPro/Diagnostics"))
            docs_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = docs_path / f"lap_diagnostics_{timestamp}.log"
            
            file_handler = logging.FileHandler(str(log_file), mode='w')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"Diagnostic logging enabled to {log_file}")
            
            # Create CSV file for detailed position tracking
            self._position_log_file = docs_path / f"position_log_{timestamp}.csv"
            with open(self._position_log_file, 'w') as f:
                f.write("timestamp,session_time,lap_dist_pct,lap_number,lap_state\n")
            
            logger.info(f"Position log enabled to {self._position_log_file}")
        else:
            logger.setLevel(logging.INFO)
            self._position_log_file = None
            logger.info("Diagnostic logging disabled")

    def _process_session_state(self, telemetry_data):
        """Process session state changes to detect race end conditions.
        
        This method handles detection of checkered flag, final laps, etc.
        
        Args:
            telemetry_data: Dictionary containing telemetry data from iRacing
        """
        if not telemetry_data:
            return
            
        # Get the current session state
        session_state = telemetry_data.get('SessionState', -1)
        previous_state = getattr(self, '_previous_session_state', -1)
        
        # Check for transition to checkered flag (state 4)
        if session_state == 4 and previous_state != 4:
            logger.info(f"[SESSION STATE] Detected checkered flag (transition to SessionState 4)")
            self._session_flagged = True
            
            # Mark the current lap as potentially the final racing lap
            self._is_final_racing_lap = True
            logger.info(f"[SESSION STATE] Marking current lap {self._current_lap_number} as potentially the final racing lap")
        
        # Special handling for state transitions
        if session_state != previous_state:
            logger.info(f"[SESSION STATE] Session state changed from {previous_state} to {session_state}")
            
            # State 5 is often "cool down" after the checkered flag
            if session_state == 5 and previous_state == 4:
                logger.info(f"[SESSION STATE] Entered cool-down period after checkered flag")
                
                # This is a good time to ensure the final racing lap was saved
                if hasattr(self, '_current_lap_data') and len(self._current_lap_data) > 10:
                    logger.info(f"[SESSION STATE] Cool-down detected with {len(self._current_lap_data)} points in current lap")
                    # Consider auto-saving the final lap here with special validation
        
        # Store previous state for next comparison
        self._previous_session_state = session_state
    
    def process_telemetry(self, telemetry_data):
        """
        Process iRacing telemetry data to detect and save laps.
        
        Args:
            telemetry_data (dict): Telemetry data from iRacing
        """
        # Check if we have the necessary session info
        if not self.user_id or not self.session_id:
            if self._telemetry_warning_count % 100 == 0:  # Only log every 100th occurrence to reduce spam
                self.logger.warning("[IRacingLapSaver.process_telemetry] User ID or Session ID not set. Cannot process telemetry.")
                self._telemetry_warning_count += 1
            return
            
        try:
            # Reset the warning counter if we're processing telemetry
            self._telemetry_warning_count = 0
            
            # Detect session state changes before handling lap-specific logic
            self._process_session_state(telemetry_data)
            
            # Only process lap detection if we're in a valid session state
            if not self._in_valid_session_state:
                return
                
            # Extract lap data from telemetry
            lap_dist_pct = telemetry_data.get('LapDistPct', -1)
            current_lap_num = telemetry_data.get('Lap', 0)
            lap_completed = telemetry_data.get('LapCompleted', 0)
            
            # Skip processing if we have invalid data
            if lap_dist_pct < 0 or current_lap_num <= 0:
                return
                
            # Let the lap indexer process the telemetry data (this will handle detecting lap starts/ends)
            self.lap_indexer.process_frame(telemetry_data)
            
            # Check if we have a completed lap to save
            if self.lap_indexer.has_lap_to_save():
                lap_data = self.lap_indexer.get_lap_data_to_save()
                self._handle_completed_lap(lap_data)
                
        except Exception as e:
            self.logger.error(f"Error processing telemetry: {str(e)}", exc_info=True)

    def _calculate_track_coverage(self, lap_data):
        """Calculate the percentage of track covered by the data points."""
        if not lap_data or len(lap_data) < 5: # Added a minimum point check
            return 0.0
            
        positions = []
        for point in lap_data:
            if 'track_position' in point:
                positions.append(point['track_position'])
            elif 'LapDistPct' in point:
                positions.append(point['LapDistPct'])
            else:
                # If no position data, cannot calculate coverage based on position
                # Consider logging a warning or returning a specific value indicating this
                pass # Skip points without position data for coverage calculation

        if not positions: # If no points had position data
            logger.warning("[CoverageCalc] No telemetry points with track_position or LapDistPct found.")
            return 0.0

        min_pos = min(positions)
        max_pos = max(positions)

        # If the lap spans from very close to start to very close to finish, consider it 100%
        # Thresholds like 0.01 for start and 0.99 for end define "very close"
        if min_pos < 0.015 and max_pos > 0.985:
            return 1.0 # Report as 100% coverage

        # Fallback to segment-based calculation if not a full span by the above simple check,
        # but ensure it accurately reflects the proportion of the 0-1 range covered.
        # The original segment calculation is reasonable for partial laps.
        # For "complete" laps that don't hit the 0.015/0.985 criteria perfectly,
        # we might still want a high coverage if many segments are hit.
        
        segments = [0] * 100
        for pos in positions:
            # Ensure pos is a float or int before multiplication
            if isinstance(pos, (float, int)):
                segment = min(99, max(0, int(pos * 100)))
                segments[segment] = 1
            else:
                # Log if pos is not a number, this indicates a data issue
                logger.warning(f"[CoverageCalc] Non-numeric position value encountered: {pos}")


        coverage = sum(segments) / 100.0 # This ensures it's a float between 0.0 and 1.0
        return coverage
        
    def _validate_lap_data(self, lap_frames, lap_number_for_validation, is_timed_by_sdk: bool):
        """Validate lap data. Prioritize laps timed by SDK.

        Args:
            lap_frames: List of telemetry frames for the lap.
            lap_number_for_validation: The lap number for logging.
            is_timed_by_sdk: Boolean indicating if iRacing provided a time for this lap.

        Returns:
            tuple: (bool, str) indicating if lap is valid and a status message.
        """
        # Initial checks (e.g., for None or empty lap_frames)
        if lap_frames is None:
            self._debug_lap_validation(False, "No lap data provided", 0, 0, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: No lap_frames provided.")
            return False, "No lap data collected"
            
        # Check number of data points
        if len(lap_frames) < 20:  # Lowered from 50
            # If SDK timed it, a few points might be okay if it was a very short S/F crossing before pitting.
            if not is_timed_by_sdk:
                self._debug_lap_validation(False, f"Too few data points: {len(lap_frames)}", len(lap_frames), 0, lap_number_for_validation)
                logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: Too few data points: {len(lap_frames)} (threshold: 20) and not timed by SDK.")
                return False, f"Too few data points: {len(lap_frames)} and not timed by SDK"
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} has few points ({len(lap_frames)}) but is timed by SDK. Proceeding.")

        # Check track coverage
        coverage = self._calculate_track_coverage(lap_frames)
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} track coverage: {coverage:.2f}")
        
        # Get track position range for diagnostic logging
        try:
            min_pos = min(point.get('track_position', 1.0) for point in lap_frames)
            max_pos = max(point.get('track_position', 0.0) for point in lap_frames)
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} track position range: {min_pos:.2f} to {max_pos:.2f}")
        except (ValueError, TypeError):
            min_pos = max_pos = 0
            logger.warning(f"[LAP VALIDATION] Could not determine track position range for lap {lap_number_for_validation}")
        
        # Detect if this is an in-lap (car entering pits)
        is_in_lap = False # This specific logic is now effectively bypassed by checks in process_telemetry
        # pit_points = 0
        # track_points = 0
        
        # Check the last few points to see if car entered pits
        # This logic might need refinement based on how 'is_in_pit' is set in LapIndexer's frames
        # or if LapIndexer directly provides this classification.
        # For now, assuming 'is_in_pit' is present in telemetry_frames from LapIndexer if relevant.
        # if len(lap_frames) > 0:
            # Check if it ended on pit road and wasn't on pit road at the start to confirm it's an IN-lap
            # ended_on_pit_road = lap_frames[-1].get('OnPitRoad', False) or lap_frames[-1].get('is_in_pit', False)
            # started_on_pit_road = lap_frames[0].get('OnPitRoad', False) or lap_frames[0].get('is_in_pit', False)
            # if ended_on_pit_road and not started_on_pit_road:
                # is_in_lap = True
                # logger.info(f"[LAP VALIDATION] Detected in-lap for lap {lap_number_for_validation} (ended on pit road, started on track)")

        # if is_in_lap: # This will likely always be false here due to prior filtering
            # logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} is an IN-LAP. Failing validation as per rule.") # This message might be confusing if reached
            # self._debug_lap_validation(False, "In-lap, not saved by rule", len(lap_frames), coverage, lap_number_for_validation)
            # return False, "In-lap, not saved by rule"

        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} is a NORMAL LAP (not identified as out/in-lap by prior checks)")
        
        # Standard threshold for laps that are not out-laps or in-laps
        effective_threshold = 0.5 # Default threshold for normal laps
        
        # Enhanced logging for threshold comparison
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} coverage ({coverage:.2f}) vs. threshold ({effective_threshold})")
            
        if coverage < effective_threshold:
            # Check if the lap was timed by the SDK
            if is_timed_by_sdk:
                logger.warning(
                    f"[LAP VALIDATION] Lap {lap_number_for_validation} has low coverage ({coverage:.2f}), "
                    f"but is timed by SDK. Marking as VALID despite low coverage."
                )
                # Lap is considered valid because SDK provided a time, but we log the coverage issue.
                # The success_reason will later reflect this nuance.
            else:
                failure_reason = f"Insufficient track coverage: {coverage:.2f} (threshold: {effective_threshold})"
                self._debug_lap_validation(False, failure_reason, len(lap_frames), coverage, lap_number_for_validation)
                logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: {failure_reason}")
                
                # Store the actual lap data for potential later recovery
                if not hasattr(self, '_stored_partial_laps'):
                    self._stored_partial_laps = {}
                self._stored_partial_laps[lap_number_for_validation] = {
                    'points': lap_frames.copy(),
                    'lap_time': 0,  # This would need to be passed in; placeholder
                    'coverage': coverage,
                    'skipped_reason': failure_reason
                }
                return False, failure_reason
        
        # Check for reasonable speed values
        speeds = [point.get("speed", 0) for point in lap_frames]
        max_speed = max(speeds) if speeds else 0
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} speed stats: max={max_speed:.1f}, avg={avg_speed:.1f}")
        
        if not speeds or max_speed <= 0:
            failure_reason = "No valid speed data"
            self._debug_lap_validation(False, failure_reason, len(lap_frames), coverage, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: {failure_reason}")
            return False, failure_reason
        
        # Handle special case for laps with pit entry/exit - mark them clearly
        lap_status = ""
        # if is_out_lap: # Out-laps are filtered before this stage
            # lap_status = "Out lap"
        # elif is_in_lap: # In-laps are filtered before this stage
            # lap_status = "In lap (pit entry)"
        # else:
        lap_status = "Full lap" # All laps reaching here are considered "Full" or "Normal"
        
        success_reason = f"Valid {lap_status} with {len(lap_frames)} points, {coverage:.2f} coverage"
        # Add a note if SDK time was prioritized over low coverage
        if is_timed_by_sdk and coverage < effective_threshold:
            success_reason += " (SDK lap time prioritized over low coverage)"
            
        self._debug_lap_validation(True, success_reason, len(lap_frames), coverage, lap_number_for_validation)
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} PASSED: {success_reason}")
        return True, success_reason

    def _debug_lap_validation(self, is_valid, message, point_count, coverage, lap_number_to_debug):
        """Debug method for lap validation decisions."""
        validation_type = "VALID" if is_valid else "INVALID"
        
        # Store lap recording status
        self._lap_recording_status[lap_number_to_debug] = {
            "status": validation_type,
            "message": message,
            "point_count": point_count,
            "coverage": coverage,
            "timestamp": time.time()
        }
        
        # Log more details for invalid laps
        if not is_valid:
            logger.warning(f"Lap {lap_number_to_debug} validation: {validation_type} - {message} (points: {point_count}, coverage: {coverage:.2f})")
            
            # Store partial lap data for debugging
            self._partial_laps[lap_number_to_debug] = {
                "point_count": point_count,
                "coverage": coverage,
                "reason": message,
                "timestamp": time.time()
            }
            
            self._total_laps_skipped += 1
        else:
            logger.info(f"Lap {lap_number_to_debug} validation: {validation_type} - {message}")
            self._total_laps_saved += 1

    def save_partial_laps(self, force=False):
        """Save partial laps that didn't meet validation criteria.
        
        Args:
            force: If True, save all partial laps regardless of diagnostic_mode
                  
        Returns:
            Dictionary with results of the operation
        """
        if not force and not self._diagnostic_mode:
            return {"success": False, "message": "Diagnostic mode not enabled, use force=True to override"}
        
        # Initialize partial laps storage if not done already
        if not hasattr(self, '_stored_partial_laps'):
            self._stored_partial_laps = {}
        
        results = {
            "success": True,
            "message": "",
            "laps_saved": 0,
            "laps_failed": 0,
            "details": {}
        }
        
        # First check if we have any partial laps from validation
        if not self._partial_laps and not self._stored_partial_laps:
            results["message"] = "No partial laps to save"
            return results
            
        # For each partial lap that didn't get saved
        all_partial_laps = {**self._partial_laps}  # Make a copy to avoid modification during iteration
        
        # Add any stored data we have
        if hasattr(self, '_stored_partial_laps'):
            all_partial_laps.update({k: {"points": v['points'], "reason": v.get('skipped_reason', "Unknown")} 
                              for k, v in self._stored_partial_laps.items()})
        
        for lap_number, partial_info in all_partial_laps.items():
            lap_num_str = str(lap_number)  # For using as a key in the results
            
            try:
                logger.info(f"FORCE SAVING partial lap {lap_number} with debug info: {partial_info}")
                
                # Skip if we don't have actual points data
                if not hasattr(self, '_stored_partial_laps') or lap_number not in self._stored_partial_laps:
                    logger.warning(f"Cannot save partial lap {lap_number}: No telemetry data stored")
                    results["details"][lap_num_str] = {"success": False, "message": "No telemetry data found"}
                    results["laps_failed"] += 1
                    continue
                
                # Get the stored points data
                lap_data = self._stored_partial_laps[lap_number]['points']
                
                # Generate a lap time - either use stored or estimate based on point timestamps
                if self._stored_partial_laps[lap_number].get('lap_time', 0) > 0:
                    lap_time = self._stored_partial_laps[lap_number]['lap_time']
                else:
                    # Try to estimate from timestamps if available
                    timestamps = [p.get('timestamp', 0) for p in lap_data]
                    if timestamps and max(timestamps) > min(timestamps):
                        lap_time = max(timestamps) - min(timestamps)
                    else:
                        # Just use a placeholder
                        lap_time = 999.999
                
                # Create a unique filename for this partial lap
                partial_folder = Path(os.path.expanduser("~/Documents/TrackPro/PartialLaps"))
                partial_folder.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = partial_folder / f"partial_lap_{lap_number}_{timestamp}.json"
                
                # Save to file
                organized_data = {
                    "lap_number": lap_number,
                    "lap_time": lap_time,
                    "timestamp": time.time(),
                    "point_count": len(lap_data),
                    "is_valid": False,
                    "force_saved": True,
                    "debug_info": {
                        "coverage": self._stored_partial_laps[lap_number].get('coverage', 0),
                        "skipped_reason": self._stored_partial_laps[lap_number].get('skipped_reason', "Unknown")
                    },
                    "points": lap_data
                }
                
                with open(filename, 'w') as f:
                    json.dump(organized_data, f)
                
                logger.info(f"Saved partial lap {lap_number} to {filename} ({len(lap_data)} points)")
                results["details"][lap_num_str] = {
                    "success": True, 
                    "file": str(filename),
                    "points": len(lap_data)
                }
                results["laps_saved"] += 1
                
            except Exception as e:
                logger.error(f"Error saving partial lap {lap_number}: {e}", exc_info=True)
                results["details"][lap_num_str] = {"success": False, "message": str(e)}
                results["laps_failed"] += 1
                results["success"] = False  # Mark the overall operation as failed if any lap fails
        
        # Update summary message
        if results["laps_saved"] > 0:
            results["message"] = f"Successfully saved {results['laps_saved']} partial laps"
            if results["laps_failed"] > 0:
                results["message"] += f", {results['laps_failed']} failed"
        else:
            results["message"] = f"Failed to save any partial laps ({results['laps_failed']} attempted)"
            results["success"] = False
            
        return results

    def get_lap_recording_status(self):
        """Get detailed status information about lap recording."""
        status = {
            "total_laps_detected": self._total_laps_detected,
            "total_laps_saved": self._total_laps_saved,
            "total_laps_skipped": self._total_laps_skipped,
            "lap_statuses": self._lap_recording_status,
            "diagnostic_mode": self._diagnostic_mode,
            "track_coverage_threshold": self._track_coverage_threshold,
            "partial_laps": self._partial_laps
        }
        
        # Log the current status
        logger.info(f"Lap Recording Status: Detected: {self._total_laps_detected}, Saved: {self._total_laps_saved}, Skipped: {self._total_laps_skipped}")
        
        return status

    def _handle_worker_lap_saved(self, lap_uuid, lap_number_str, lap_time, session_id, telemetry_saved_successfully):
        self.logger.info(f"WORKER SIGNAL: Lap {lap_number_str} (UUID: {lap_uuid}, Time: {lap_time:.3f}s) saved for session {session_id}. Telemetry saved: {telemetry_saved_successfully}")
        # Potentially update internal state or emit further signals if UI needs to know

    def _handle_worker_error(self, lap_number_str, error_message):
        self.logger.error(f"WORKER ERROR for lap {lap_number_str}: {error_message}")
        # Potentially update UI or internal state

    def _handle_worker_progress(self, message):
        self.logger.debug(f"WORKER PROGRESS: {message}")

    def _handle_worker_finished(self):
        self.logger.debug("SaveLapWorker finished.")

    def _save_lap_data(self, lap_number, lap_time, lap_frames_from_indexer, end_tick_for_lap, started_on_pit_road, ended_on_pit_road):
        """
        Validates and INITIATES saving of a single lap's data and its telemetry points to Supabase via a worker thread.
        This method now contains the definitive validation check before handing off to the worker.
        """
        # --- BEGIN ADDED LOGGING ---
        num_frames_arg = len(lap_frames_from_indexer) if lap_frames_from_indexer else 0
        first_frame_time_arg = lap_frames_from_indexer[0].get('SessionTimeSecs', 'N/A') if num_frames_arg > 0 else 'N/A'
        last_frame_time_arg = lap_frames_from_indexer[-1].get('SessionTimeSecs', 'N/A') if num_frames_arg > 0 else 'N/A'
        logger.info(
            f"[IRacingLapSaver._save_lap_data] ENTERED FOR SDK Lap {lap_number}: "
            f"Time={lap_time:.3f}, Frames_Count_Arg={num_frames_arg}, "
            f"FirstFrameTimeArg={first_frame_time_arg}, LastFrameTimeArg={last_frame_time_arg}, "
            f"EndTick={end_tick_for_lap}, StartedOnPit={started_on_pit_road}, EndedOnPit={ended_on_pit_road}"
        )
        # --- END ADDED LOGGING ---

        if not self._current_session_id:
            logger.error("No active session ID. Cannot save lap.")
            return False, lap_number, lap_time, None, False 

        if not self._supabase or not hasattr(self._supabase, 'table') or not self._user_id:
            logger.error("Supabase client not configured, user ID not set, or client invalid. Cannot save lap.")
            return False, lap_number, lap_time, None, False

        logger.info(f"Attempting to save lap {lap_number} (time: {lap_time:.3f}s, session_time_completed: {end_tick_for_lap}) via worker.")

        is_valid_lap, validation_message = self._validate_lap_data(lap_frames_from_indexer, lap_number, lap_time > 0)
        logger.info(f"Lap {lap_number} validation result: {validation_message}")

        if not is_valid_lap:
            logger.warning(f"Lap {lap_number} is invalid based on internal validation: {validation_message}. Not queueing for save.")
            return False, lap_number, None, None, False 

        logger.info(f"Lap {lap_number} passed validation. Queueing for save to database for session {self._current_session_id}.")
        
        lap_uuid = str(uuid.uuid4()) # Generate UUID here
        
        lap_payload = {
            'lap_uuid': lap_uuid, # Add the generated UUID
            'session_id': self._current_session_id,
            'user_id': self._user_id,
            'lap_number': lap_number,
            'lap_time': lap_time,
            'is_complete': True,
            'session_time_completed': end_tick_for_lap, 
            'started_on_pit_road': started_on_pit_road,
            'ended_on_pit_road': ended_on_pit_road,
            'is_valid': True 
        }

        # Create and configure the worker
        # Note: lap_number is passed as string for signal consistency if needed, though payload uses int
        worker = SaveLapWorker(
            supabase_client=self._supabase,
            user_id=self._user_id,
            session_id=self._current_session_id,
            lap_payload=lap_payload,
            lap_frames=lap_frames_from_indexer,
            lap_number_str=str(lap_number) 
        )

        # Connect signals
        worker.signals.lap_saved.connect(self._handle_worker_lap_saved)
        worker.signals.error.connect(self._handle_worker_error)
        worker.signals.progress.connect(self._handle_worker_progress)
        worker.signals.finished.connect(self._handle_worker_finished)
        
        # Execute
        self.threadpool.start(worker)
        logger.info(f"Queued lap {lap_number} for saving in background.")

        # IMPORTANT: This method now returns information about the *initiation* of the save.
        # The actual success/failure and lap_uuid will come via signals.
        # The tuple returned to process_telemetry needs to be considered.
        # For now, let's return that it was initiated and considered valid for UI (as per old logic),
        # but the UUID will be None initially. The UI might need to adapt to this async flow.
        # (was_saved_to_db, lap_number_from_save, lap_time_from_save, actual_lap_uuid, is_valid_for_ui_from_validation)
        return True, lap_number, lap_time, None, True # True for "save initiated", None for UUID (it's async)
                                                      # True for is_valid_for_ui because it passed validation.

    def get_lap_times(self, session_id=None):
        """
        Get all lap times for a session.
        
        Args:
            session_id: The session ID (defaults to current session)
            
        Returns:
            List of lap time data
        """
        if not self._supabase:
            logger.error("Cannot get lap times: Supabase connection not available")
            return []
        
        session_id = session_id or self._current_session_id
        if not session_id:
            logger.error("Cannot get lap times: No session ID specified")
            return []
        
        try:
            result = self._supabase.table("laps").select("*").eq("session_id", session_id).order("lap_number").execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"Error getting lap times: {e}")
            return []

    def get_telemetry_data(self, lap_id):
        """
        Get telemetry data for a specific lap.
        
        Args:
            lap_id: The lap ID
            
        Returns:
            List of telemetry data points
        """
        if not self._supabase:
            logger.error("Cannot get telemetry data: Supabase connection not available")
            return []
        
        try:
            result = self._supabase.table("telemetry_points").select("*").eq("lap_id", lap_id).order("track_position").execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"Error getting telemetry data: {e}")
            return []

    def test_connection(self):
        """Test the Supabase connection and return diagnostic information."""
        result = {
            "connection_status": "unknown",
            "env_vars_set": {},
            "connected": False,
            "tables_accessible": {},
            "errors": []
        }
        
        # Check Supabase client exists
        if not self._supabase:
            result["connection_status"] = "failed"
            result["errors"].append("Supabase client not initialized")
            return result
        
        # Try to connect to Supabase
        try:
            # Test connection (no need to call _connect_to_supabase again)
            result["connected"] = True
            
            # Test database access by checking if tables exist
            tables_to_check = ["tracks", "cars", "sessions", "laps", "telemetry_points"]
            for table in tables_to_check:
                try:
                    response = self._supabase.table(table).select("id").limit(1).execute()
                    result["tables_accessible"][table] = {
                        "accessible": True,
                        "count": len(response.data) if hasattr(response, 'data') else 0
                    }
                except Exception as e:
                    result["tables_accessible"][table] = {
                        "accessible": False,
                        "error": str(e)
                    }
                    result["errors"].append(f"Failed to access table {table}: {e}")
            result["connection_status"] = "success" if not result["errors"] else "partial_success"
            
        except Exception as e:
            result["connection_status"] = "failed"
            result["errors"].append(f"General connection error: {e}")
            result["connected"] = False

            return result 

    def end_session(self):
        """End the current session and save any remaining lap data."""
        logger.info(f"[SESSION END] Processing session end. Calling LapIndexer.finalize().")
        self.lap_indexer.finalize() # Finalize LapIndexer first

        all_indexed_laps = self.lap_indexer.get_laps()
        newly_finalized_laps_processed_in_session_end = 0

        logger.info(f"[SESSION END] LapIndexer has {len(all_indexed_laps)} total laps after finalize.")

        for indexed_lap in all_indexed_laps:
            sdk_lap_number = indexed_lap["lap_number_sdk"]
            lap_duration = indexed_lap["duration_seconds"]
            lap_telemetry_frames = indexed_lap["telemetry_frames"]
            
            # Get all relevant flags from LapIndexer
            is_valid_from_sdk_rules = indexed_lap.get("is_valid_from_sdk", True)
            is_timed_by_sdk_rules = indexed_lap.get("is_timed_by_sdk", False)
            is_out_lap_rule = indexed_lap.get("is_out_lap", False)
            is_incomplete_session_end_rule = indexed_lap.get("is_incomplete_session_end", False)
            started_on_pit = indexed_lap.get("started_on_pit_road", False)
            ended_on_pit = indexed_lap.get("ended_on_pit_road", False)

            if sdk_lap_number not in self._processed_lap_indexer_lap_numbers:
                logger.info(f"[SESSION END] Evaluating lap {sdk_lap_number} from LapIndexer at session end.")
                
                should_attempt_save_and_validate_at_session_end = False
                rejection_reason_at_session_end = ""
                use_validation_override = False

                if is_incomplete_session_end_rule:
                    logger.info(f"[SESSION END] Lap {sdk_lap_number} is an INCOMPLETE SESSION-END LAP. Overriding normal validation for saving telemetry.")
                    should_attempt_save_and_validate_at_session_end = True
                    use_validation_override = True # Key for the flushed final lap
                elif is_out_lap_rule:
                    logger.info(f"[SESSION END] Lap {sdk_lap_number} is an OUT-LAP. Passing to normal validation.")
                    should_attempt_save_and_validate_at_session_end = True
                elif not is_valid_from_sdk_rules:
                    rejection_reason_at_session_end = "marked invalid by SDK (LapInvalidated flag during lap)"
                    logger.info(f"[SESSION END] Lap {sdk_lap_number} {rejection_reason_at_session_end}. Skipping.")
                elif not is_timed_by_sdk_rules:
                    rejection_reason_at_session_end = "not positively timed by SDK (LapLastLapTime <= 0)"
                    logger.info(f"[SESSION END] Lap {sdk_lap_number} {rejection_reason_at_session_end}. Skipping as displayable/comparable lap.")
                else: 
                    # A normally completed lap that somehow wasn't processed during the session
                    logger.info(f"[SESSION END] Lap {sdk_lap_number} is a normal, valid, SDK-timed lap missed during session. Passing to normal validation.")
                    should_attempt_save_and_validate_at_session_end = True

                if should_attempt_save_and_validate_at_session_end:
                    self._override_validation = True # Ensure last lap is processed by validation
                    logger.info(f"[SESSION END] Attempting to save indexed lap {sdk_lap_number} (Dur: {lap_duration:.2f}s) from session end.")
                    
                    end_tick_for_final_lap = indexed_lap.get("end_tick")
                    started_on_pit_final = indexed_lap.get("started_on_pit_road", False)
                    ended_on_pit_final = indexed_lap.get("ended_on_pit_road", False)

                    if end_tick_for_final_lap is None:
                        logger.warning(f"[SESSION END] end_tick missing for lap {sdk_lap_number}. Cannot save.")
                        continue 

                    saved_status, _, _, saved_uuid, _ = self._save_lap_data(
                        lap_number=sdk_lap_number,
                        lap_time=lap_duration,
                        lap_frames_from_indexer=lap_telemetry_frames,
                        end_tick_for_lap=end_tick_for_final_lap,
                        started_on_pit_road=started_on_pit_final,
                        ended_on_pit_road=ended_on_pit_final
                    )
                    if saved_status and saved_uuid:
                        newly_finalized_laps_processed_in_session_end += 1
                        logger.info(f"[SESSION END] Successfully saved lap {sdk_lap_number} (UUID: {saved_uuid}) during session finalization.")
                    else:
                        # Use the flags from indexed_lap for more detailed logging if save fails
                        is_valid_from_sdk_rules = indexed_lap.get("is_valid_from_sdk", True)
                        is_timed_by_sdk_rules = indexed_lap.get("is_timed_by_sdk", False)
                        logger.warning(f"[SESSION END] Failed to save lap {sdk_lap_number} during session finalization. SDK Valid: {is_valid_from_sdk_rules}, SDK Timed: {is_timed_by_sdk_rules}")
                else:
                    logger.info(f"[SESSION END] Lap {sdk_lap_number} already processed ({sdk_lap_number in self._processed_lap_indexer_lap_numbers}) or did not meet other criteria for session-end save.")
            
            self._override_validation = False # Reset the flag

        if newly_finalized_laps_processed_in_session_end > 0:
            logger.info(f"[SESSION END] Processed and saved {newly_finalized_laps_processed_in_session_end} additional lap(s) from LapIndexer data at session close.")
        else:
            logger.info(f"[SESSION END] No new laps from LapIndexer needed saving at session close.")

        # Log final stats from IRacingLapSaver perspective
        logger.info(f"[SESSION END] Final IRacingLapSaver stats: Total laps processed via LapIndexer and saved by IRacingLapSaver: {len(self._processed_lap_indexer_lap_numbers)}")
        
        # Reset session state for IRacingLapSaver
        self._is_first_telemetry = True # Reset for a potential new session with the same IRacingLapSaver instance
        self._current_lap_number = 0 # Reset internal lap counter
        self._lap_start_time = 0
        self._last_track_position = 0
        self._current_lap_data = [] # Clear any residual data here too
        self._processed_lap_indexer_lap_numbers.clear() # Clear for next session
        # Keep other stats like _total_laps_saved if they are meant to be cumulative across app lifetime or re-init them if per session.
        # For now, assuming they are cumulative or handled elsewhere if this instance is reused.

        session_folder = getattr(self, '_current_session_folder', None)
        logger.info(f"[SESSION END] Telemetry recording session ended. Session folder: {session_folder}")
        
        return session_folder

    def _find_or_create_track(self, track_name):
        """Find or create a track in the database.
        
        Args:
            track_name: The name of the track to find or create
            
        Returns:
            The track ID if successful, None otherwise
        """
        if not self._supabase:
            logger.error("No Supabase client available")
            return None
            
        if not track_name:
            logger.error("No track name provided")
            return None
            
        try:
            # First try to find the track by exact name
            track_resp = self._supabase.table("tracks").select("id").eq("name", track_name).execute()
            if track_resp.data and len(track_resp.data) > 0:
                return track_resp.data[0]["id"]
                
            # If not found, try finding by similar name (case insensitive)
            track_resp = self._supabase.table("tracks").select("id").ilike("name", f"%{track_name}%").execute()
            if track_resp.data and len(track_resp.data) > 0:
                return track_resp.data[0]["id"]
                
            # If still not found, create a new track
            track_insert = self._supabase.table("tracks").insert({"name": track_name}).execute()
            if track_insert.data and len(track_insert.data) > 0:
                return track_insert.data[0]["id"]
                
            # If we get here, something went wrong
            logger.error(f"Failed to create track: {track_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _find_or_create_track: {e}")
            return None
            
    def _find_or_create_car(self, car_name):
        """Find or create a car in the database.
        
        Args:
            car_name: The name of the car to find or create
            
        Returns:
            The car ID if successful, None otherwise
        """
        if not self._supabase:
            logger.error("No Supabase client available")
            return None
            
        if not car_name:
            logger.error("No car name provided")
            return None
            
        try:
            # First try to find the car by exact name
            car_resp = self._supabase.table("cars").select("id").eq("name", car_name).execute()
            if car_resp.data and len(car_resp.data) > 0:
                return car_resp.data[0]["id"]
                
            # If not found, try finding by similar name (case insensitive)
            car_resp = self._supabase.table("cars").select("id").ilike("name", f"%{car_name}%").execute()
            if car_resp.data and len(car_resp.data) > 0:
                return car_resp.data[0]["id"]
                
            # If still not found, create a new car
            car_insert = self._supabase.table("cars").insert({"name": car_name}).execute()
            if car_insert.data and len(car_insert.data) > 0:
                return car_insert.data[0]["id"]
                
            # If we get here, something went wrong
            logger.error(f"Failed to create car: {car_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _find_or_create_car: {e}")
            return None

    def _handle_completed_lap(self, lap_data):
        """Handle a completed lap from the lap indexer"""
        if not lap_data:
            return
            
        lap_number = lap_data.get("lap_number")
        is_invalid = lap_data.get("invalid_by_indexer", True)
        
        # Skip laps already marked as invalid by the indexer
        if is_invalid:
            self.logger.debug(f"Lap {lap_number} flagged as invalid by lap indexer. Skipping save.")
            return
            
        # Extract lap data
        lap_frames = lap_data.get("frames", [])
        lap_time = lap_data.get("lap_time", 0.0)
        started_on_pit_road = lap_data.get("started_on_pit_road", False)
        ended_on_pit_road = lap_data.get("ended_on_pit_road", False)
        end_tick = lap_data.get("end_tick")
        
        # Log lap details
        frame_count = len(lap_frames) if lap_frames else 0
        self.logger.info(f"Processing completed lap: Lap={lap_number}, Time={lap_time:.3f}s, Frames={frame_count}")
        
        # Don't save laps that start or end on pit road (out/in laps)
        if started_on_pit_road or ended_on_pit_road:
            self.logger.info(f"Lap {lap_number} started/ended on pit road. Not saving as a timed lap.")
            return
            
        # Validate and save the lap
        if lap_time > 0:
            self.logger.info(f"Saving timed lap {lap_number} with time {lap_time:.3f}s")
            self._save_lap_data(
                lap_number=lap_number,
                lap_time=lap_time,
                lap_frames_from_indexer=lap_frames,
                end_tick_for_lap=end_tick,
                started_on_pit_road=started_on_pit_road,
                ended_on_pit_road=ended_on_pit_road
            )