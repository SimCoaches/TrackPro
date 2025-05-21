"""
Module for saving iRacing lap times and telemetry data to Supabase.
"""

import os
import time
import logging
import uuid
import json
import threading
import queue
from datetime import datetime
from pathlib import Path

# Import the Supabase singleton client instead of creating a new one
from ..database.supabase_client import supabase

# Import the new LapIndexer
from .lap_indexer import LapIndexer

# Setup logging
logger = logging.getLogger(__name__)

class SaveLapWorker(threading.Thread):
    """Worker thread for saving laps to the database without blocking telemetry collection."""
    
    def __init__(self, parent_saver):
        """Initialize the worker thread.
        
        Args:
            parent_saver: Reference to the IRacingLapSaver instance that created this worker
        """
        super().__init__(daemon=True)  # Daemon thread dies when main thread exits
        self.parent = parent_saver
        self.lap_queue = queue.Queue()
        self.running = True
        self.lap_save_lock = threading.Lock()  # Lock for thread safety
        self._processed_lap_numbers = set()  # Track processed laps in this thread

    def run(self):
        """Main worker thread loop."""
        logger.info("[SaveLapWorker] Starting lap saving worker thread")
        
        while self.running:
            try:
                # Try to get a lap from the queue, timeout after 1 second to allow checking if we should stop
                try:
                    lap_data = self.lap_queue.get(timeout=1.0)
                except queue.Empty:
                    # No lap in queue, continue loop and check if we should stop
                    continue
                
                # Process the lap data
                sdk_lap_number = lap_data["lap_number_sdk"]
                
                # Skip if this lap was already processed (belt and suspenders check)
                if sdk_lap_number in self._processed_lap_numbers:
                    logger.warning(f"[SaveLapWorker] Lap {sdk_lap_number} already processed, skipping")
                    self.lap_queue.task_done()
                    continue
                
                # Process the lap
                with self.lap_save_lock:
                    logger.info(f"[SaveLapWorker] Processing lap {sdk_lap_number} (queue size: {self.lap_queue.qsize()})")
                    
                    # Call the parent's _save_lap_data method
                    lap_duration = lap_data["duration_seconds"]
                    lap_frames = lap_data["telemetry_frames"]
                    lap_state = lap_data.get("lap_state", "TIMED")
                    is_valid = lap_data.get("is_valid_from_sdk", True)
                    is_valid_for_leaderboard = lap_data.get("is_valid_for_leaderboard", False)
                    
                    # Add lap state and metadata to each frame first
                    lap_frames_with_extra_data = []
                    for frame in lap_frames:
                        frame_copy = dict(frame)
                        frame_copy["lap_state"] = lap_state
                        frame_copy["is_valid_for_leaderboard"] = is_valid_for_leaderboard
                        frame_copy["is_complete_by_sdk_increment"] = lap_data.get("is_complete_by_sdk_increment", True)
                        lap_frames_with_extra_data.append(frame_copy)
                    
                    # Set up context for saving - we're in a separate thread so it's okay to modify these
                    self.parent._current_lap_data = lap_frames_with_extra_data
                    self.parent._current_lap_number = sdk_lap_number
                    
                    # Call the parent's save method
                    saved_lap_id = self.parent._save_lap_data(sdk_lap_number, lap_duration, lap_frames_with_extra_data)
                    
                    if saved_lap_id:
                        logger.info(f"[SaveLapWorker] Successfully saved lap {sdk_lap_number} (ID: {saved_lap_id}) in background thread")
                        # Keep track of this lap number locally and in the parent
                        self._processed_lap_numbers.add(sdk_lap_number)
                        with self.parent._processing_lock:
                            self.parent._processed_lap_indexer_lap_numbers.add(sdk_lap_number)
                    else:
                        logger.error(f"[SaveLapWorker] Failed to save lap {sdk_lap_number}")
                
                # Mark task as done
                self.lap_queue.task_done()
                
            except Exception as e:
                logger.error(f"[SaveLapWorker] Error in lap saving worker: {e}", exc_info=True)
                # Try to mark the task as done if possible to avoid blocking the queue
                try:
                    self.lap_queue.task_done()
                except:
                    pass
    
    def stop(self):
        """Stop the worker thread."""
        logger.info("[SaveLapWorker] Stopping lap saving worker thread")
        self.running = False
        
    def enqueue_lap(self, lap_data):
        """Add a lap to the processing queue.
        
        Args:
            lap_data: Dictionary with all lap data needed for saving
            
        Returns:
            True if lap was queued, False if it was already processed
        """
        lap_number = lap_data["lap_number_sdk"]
        
        # Check if we've already processed this lap
        if lap_number in self._processed_lap_numbers:
            logger.warning(f"[SaveLapWorker] Lap {lap_number} already processed, not queuing again")
            return False
            
        logger.info(f"[SaveLapWorker] Enqueueing lap {lap_number} for background processing")
        self.lap_queue.put(lap_data)
        return True
        
    def get_queue_size(self):
        """Get the current queue size."""
        return self.lap_queue.qsize()
        
    def wait_until_empty(self, timeout=None):
        """Wait until the queue is empty and all tasks are processed.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if queue is empty, False if timeout occurred
        """
        try:
            self.lap_queue.join(timeout=timeout)
            return True
        except:
            return False

class IRacingLapSaver:
    """
    Manages saving iRacing lap times and telemetry data to Supabase.
    """
    def __init__(self):
        """Initialize the saver."""
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize LapIndexer
        self.lap_indexer = LapIndexer()
        
        # Keep track of lap numbers processed from LapIndexer to avoid duplicates
        self._processed_lap_indexer_lap_numbers = set()
        self._processing_lock = threading.Lock()  # Lock for thread safety
        
        # Set up the background worker for lap saving
        self._save_worker = SaveLapWorker(self)
        self._save_worker.start()
        
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

        # Rate limiting for warnings
        self._last_invalid_lap_number_warning_time: float = 0.0
        self._last_invalid_lap_number_warning_message: str = ""
        self._warning_interval: float = 5.0  # seconds

    def set_supabase_client(self, client):
        """Set the Supabase client instance."""
        self._supabase = client
        if client:
            logger.info(f"Supabase client set for IRacingLapSaver: {client is not None}")
            self._connection_disabled = False
            
            # Test connection immediately to verify it's working
            try:
                if hasattr(client, 'table'):
                    # Try a simple query to verify the connection works
                    test_result = client.table('tracks').select('id').limit(1).execute()
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
                    return
            except Exception as e:
                logger.error(f"Error getting global Supabase client: {e}")
                self._connection_disabled = True

    def set_user_id(self, user_id):
        """Set the current user ID for associating data."""
        self._user_id = user_id
        logger.info(f"Set user ID to: {user_id}")
        
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
        """Process incoming telemetry data to detect laps and save telemetry.
        
        Args:
            telemetry_data: Dictionary containing telemetry data
            
        Returns:
            Tuple of (is_new_lap, lap_number, lap_time, lap_state) if a new lap is detected, None otherwise
        """
        # Check session state changes first
        self._process_session_state(telemetry_data)
        # Increment debug counter
        self._telemetry_debug_counter += 1
        
        # Ensure we have a session ID from the monitor
        if not self._current_session_id:
            # Log periodically if no session is active
            if self._telemetry_debug_counter % 300 == 0:
                logger.debug("Cannot process telemetry: No active session set by monitor.")
            return None

        # --- Enhanced Lap Detection Logic ---
        try:
            lap_dist_pct = telemetry_data.get('LapDistPct', -1)
            session_time = telemetry_data.get('SessionTimeSecs', 0)
            
            # IMPORTANT: Get the current lap number directly from iRacing whenever possible
            # This is more reliable than our internal tracking
            iracing_current_lap = telemetry_data.get('Lap', 0)
            iracing_completed_lap = telemetry_data.get('LapCompleted', 0)
            
            # --- Feed data to the LapIndexer ---
            self.lap_indexer.on_frame(telemetry_data)
            
            # Safety check on lap numbers
            if iracing_current_lap < 0 or iracing_completed_lap < 0:
                current_time = time.time()
                message = f"Invalid lap numbers from iRacing: Current={iracing_current_lap}, Completed={iracing_completed_lap}"
                if (current_time - self._last_invalid_lap_number_warning_time > self._warning_interval or
                    message != self._last_invalid_lap_number_warning_message):
                    logger.warning(message)
                    self._last_invalid_lap_number_warning_time = current_time
                    self._last_invalid_lap_number_warning_message = message
                # Use our internal counter if iRacing gives invalid data
                iracing_current_lap = max(1, self._current_lap_number)
                iracing_completed_lap = max(0, self._current_lap_number - 1)
            
            # The lap we're currently on according to iRacing
            current_lap = iracing_current_lap
                
            # DEBUG: Log key telemetry values every ~5 seconds
            if self._telemetry_debug_counter % 300 == 0:
                logger.info(f"Lap Detection Debug: LapDistPct={lap_dist_pct:.3f}, Last={self._last_track_position:.3f}, " +
                           f"iRacing Current={iracing_current_lap}, iRacing Completed={iracing_completed_lap}, " + 
                           f"Internal Current={self._current_lap_number}, SessionTime={session_time:.3f}")

            if lap_dist_pct < 0:
                if self._telemetry_debug_counter % 300 == 0:
                    logger.warning(f"Invalid track position: {lap_dist_pct}")
                return None # Invalid track position

            # Diagnostic position logging
            if self._diagnostic_mode and self._position_log_file:
                try:
                    with open(self._position_log_file, 'a') as f:
                        real_time = time.time()
                        lap_state = "START" if self._is_first_telemetry else "NORMAL"
                        f.write(f"{real_time},{session_time},{lap_dist_pct},{current_lap},{lap_state}\n")
                except Exception as e:
                    logger.error(f"Error writing to position log: {e}")
                    
            # Handle initial telemetry point
            if self._is_first_telemetry:
                self._last_track_position = lap_dist_pct
                self._lap_start_time = session_time
                # IMPORTANT: Start with iRacing's current lap number rather than our own
                self._current_lap_number = iracing_current_lap
                self._is_first_telemetry = False
                self._current_lap_data = []
                logger.info(f"Lap Saver: First telemetry received for Lap {self._current_lap_number}. Session: {self._current_session_id}")

            # Add to position history buffer for enhanced detection
            self._recent_positions.append(lap_dist_pct)
            self._recent_timestamps.append(session_time)
            if len(self._recent_positions) > self._position_buffer_size:
                self._recent_positions.pop(0)
                self._recent_timestamps.pop(0)
            
            # Update last position
            self._last_track_position = lap_dist_pct

            # --- NEW LAP PROCESSING AND SAVING FLOW USING LapIndexer ---
            # This gets all laps that LapIndexer has processed so far
            indexed_laps = self.lap_indexer.get_laps()
            laps_to_return_to_ui = []

            # Process any laps we haven't seen yet (using thread-safe check)
            for indexed_lap in indexed_laps:
                sdk_lap_number = indexed_lap["lap_number_sdk"]
                
                # Skip laps we've already processed - use thread-safe check
                with self._processing_lock:
                    if sdk_lap_number in self._processed_lap_indexer_lap_numbers:
                        continue
                    
                    # Mark it as "being processed" to prevent duplicate processing
                    self._processed_lap_indexer_lap_numbers.add(sdk_lap_number)
                    
                lap_duration = indexed_lap["duration_seconds"]
                lap_telemetry_frames = indexed_lap["telemetry_frames"]
                is_valid_from_indexer = indexed_lap.get("is_valid_from_sdk", True)  # Use is_valid_from_sdk flag
                lap_state_from_indexer = indexed_lap.get("lap_state", "TIMED")  # Get lap state (OUT, TIMED, IN, INCOMPLETE)
                is_valid_for_leaderboard = indexed_lap.get("is_valid_for_leaderboard", False)  # Get leaderboard validity flag
                is_complete_by_sdk = indexed_lap.get("is_complete_by_sdk_increment", True)  # Whether lap completed normally

                logger.info(f"[LapIndexer] New lap {sdk_lap_number} to process. Time: {lap_duration:.3f}s, Type: {lap_state_from_indexer}, Valid: {is_valid_from_indexer}, Valid for Leaderboard: {is_valid_for_leaderboard}")
                
                # Only queue the lap for saving if it's valid according to LapIndexer
                if is_valid_from_indexer:
                    # Queue the lap data for the background worker
                    # Make a copy of the indexed_lap with only what we need
                    lap_data_for_queue = {
                        "lap_number_sdk": sdk_lap_number,
                        "duration_seconds": lap_duration,
                        "telemetry_frames": lap_telemetry_frames.copy(),  # Deep copy the frames
                        "is_valid_from_sdk": is_valid_from_indexer,
                        "lap_state": lap_state_from_indexer,
                        "is_valid_for_leaderboard": is_valid_for_leaderboard,
                        "is_complete_by_sdk_increment": is_complete_by_sdk
                    }
                    
                    # Queue the lap for processing
                    self._save_worker.enqueue_lap(lap_data_for_queue)
                    
                    # Add it to laps_to_return_to_ui - this is used for callbacks to UI
                    laps_to_return_to_ui.append((True, sdk_lap_number, lap_duration, lap_state_from_indexer))
                    self._total_laps_detected += 1
                else:
                    logger.info(f"[LapIndexer] Lap {sdk_lap_number} was marked invalid by LapIndexer (type: {lap_state_from_indexer}). Skipping save.")
                    self._total_laps_skipped += 1
            
            if laps_to_return_to_ui:
                # For simplicity, returning the first new lap info. UI might need to handle multiple.
                # The tuple now includes lap type as the fourth element
                return laps_to_return_to_ui[0]
            # --- END NEW LAP PROCESSING ---

        except Exception as e:
            logger.error(f"Error processing telemetry: {e}", exc_info=True)

        return None # No new lap completed
        
    def _calculate_track_coverage(self, lap_data):
        """Calculate the percentage of track covered by the data points."""
        if not lap_data:
            return 0.0
            
        # Extract track positions (using LapDistPct as fallback)
        positions = [point.get('track_position', point.get('LapDistPct', 0)) for point in lap_data]
        
        # Calculate coverage by dividing track into 100 segments and checking presence
        segments = [0] * 100
        for pos in positions:
            segment = min(99, max(0, int(pos * 100)))
            segments[segment] = 1
        
        coverage = sum(segments) / 100.0
        return coverage
        
    def _validate_lap_data(self, lap_frames, lap_number_for_validation):
        """Validate lap data for completeness and quality."""
        # Enhanced logging - record validation start
        logger.info(f"[LAP VALIDATION] Starting validation for lap {lap_number_for_validation} with {len(lap_frames)} points")
        
        # Check for validation override flag (used for final lap)
        if hasattr(self, '_override_validation') and self._override_validation:
            coverage = self._calculate_track_coverage(lap_frames)
            point_count = len(lap_frames)
            self._debug_lap_validation(True, f"Validation overridden for lap with {point_count} points, {coverage:.2f} coverage", point_count, coverage, lap_number_for_validation)
            logger.info(f"[LAP VALIDATION] Override enabled for lap {lap_number_for_validation} - bypassing normal validation")
            return True, f"Validation overridden: {point_count} points, {coverage:.2f} coverage"
        
        if not lap_frames:
            self._debug_lap_validation(False, "No lap data collected", 0, 0, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: No lap data collected")
            return False, "No lap data collected"
            
        # Check number of data points
        lap_state_from_indexer = "TIMED" # Default if not found

        if lap_frames and len(lap_frames) > 0:
            # LapIndexer should have added 'lap_state' to frames in our wrapper code
            first_frame = lap_frames[0]
            lap_state_from_indexer = first_frame.get("lap_state", "TIMED")
            is_complete_by_sdk = first_frame.get("is_complete_by_sdk_increment", True)

        # For normal racing timed laps, require more points
        min_points_threshold = 5
        if lap_state_from_indexer == "TIMED":
            min_points_threshold = 20
        elif lap_state_from_indexer in ["OUT", "IN"]:
            min_points_threshold = 10  # More lenient for OUT/IN laps
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} is {lap_state_from_indexer}. Using min points threshold: {min_points_threshold}")

        if len(lap_frames) < min_points_threshold:
            self._debug_lap_validation(False, f"Too few data points: {len(lap_frames)}", len(lap_frames), 0, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: Too few data points: {len(lap_frames)} (threshold: {min_points_threshold}, type: {lap_state_from_indexer})")
            return False, f"Too few data points: {len(lap_frames)}"

        # Check track coverage
        coverage = self._calculate_track_coverage(lap_frames)
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} track coverage: {coverage:.2f}")
        
        # Get track position range for diagnostic logging
        try:
            min_pos = min(point.get('track_position', point.get('LapDistPct', 1.0)) for point in lap_frames)
            max_pos = max(point.get('track_position', point.get('LapDistPct', 0.0)) for point in lap_frames)
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} track position range: {min_pos:.2f} to {max_pos:.2f}")
        except (ValueError, TypeError):
            min_pos = max_pos = 0
            logger.warning(f"[LAP VALIDATION] Could not determine track position range for lap {lap_number_for_validation}")
        
        # Log lap type for diagnostics based on LapIndexer's classification
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} classified by LapIndexer as: {lap_state_from_indexer}")
        
        # Adjust coverage threshold based on lap type
        effective_threshold = 0.5 # Default for TIMED laps
        if lap_state_from_indexer == "OUT":
            effective_threshold = 0.35
            logger.info(f"[LAP VALIDATION] Using reduced coverage threshold of {effective_threshold} for OUT lap {lap_number_for_validation}")
        elif lap_state_from_indexer == "IN":
            effective_threshold = 0.35
            logger.info(f"[LAP VALIDATION] Using reduced coverage threshold of {effective_threshold} for IN lap {lap_number_for_validation}")
        elif lap_state_from_indexer == "INCOMPLETE":
            effective_threshold = 0.1 # Very lenient for incomplete laps, usually session end
            logger.info(f"[LAP VALIDATION] Using reduced coverage threshold of {effective_threshold} for INCOMPLETE lap {lap_number_for_validation}")

        # Enhanced logging for threshold comparison
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} coverage ({coverage:.2f}) vs. threshold ({effective_threshold}) for type {lap_state_from_indexer}")
            
        if coverage < effective_threshold:
            failure_reason = f"Insufficient track coverage: {coverage:.2f} (threshold: {effective_threshold} for type {lap_state_from_indexer})"
            self._debug_lap_validation(False, failure_reason, len(lap_frames), coverage, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: {failure_reason}")
            
            # Store the actual lap data for potential later recovery
            if not hasattr(self, '_stored_partial_laps'):
                self._stored_partial_laps = {}
            self._stored_partial_laps[lap_number_for_validation] = {
                'points': lap_frames.copy(),
                'lap_time': 0,  # This would need to be passed in
                'coverage': coverage,
                'skipped_reason': failure_reason
            }
            
            return False, failure_reason
        
        # Check for reasonable speed values
        speeds = [point.get("speed", point.get("Speed", 0)) for point in lap_frames]
        max_speed = max(speeds) if speeds else 0
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} speed stats: max={max_speed:.1f}, avg={avg_speed:.1f}")
        
        # For OUT/IN/INCOMPLETE laps, speed check might not be as critical if they are short or involve pit stops
        if lap_state_from_indexer == "TIMED" and (not speeds or max_speed <= 0):
            failure_reason = "No valid speed data for TIMED lap"
            self._debug_lap_validation(False, failure_reason, len(lap_frames), coverage, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: {failure_reason}")
            return False, failure_reason
        
        # Handle special case for laps with pit entry/exit - mark them clearly
        lap_status_message = f"{lap_state_from_indexer} lap"
        
        success_reason = f"Valid {lap_status_message} with {len(lap_frames)} points, {coverage:.2f} coverage"
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

    def _save_lap_data(self, lap_number, lap_time, lap_frames_from_indexer):
        """Save lap data to Supabase with retry capability."""
        # Debug connection state
        logger.info(f"Attempting to save lap {lap_number} (time: {lap_time:.3f}s)")
        logger.info(f"Connection state: Supabase client exists: {self._supabase is not None}, Session ID: {self._current_session_id}")
        
        # First check: is connection disabled flag set?
        if self._connection_disabled:
            logger.error("Cannot save lap: connection is explicitly disabled")
            return None
        
        # Check if we have a Supabase client
        logger.debug(f"[SAVE_DEBUG] Checking self._supabase. Value: {self._supabase}, Type: {type(self._supabase)}")
        if not self._supabase:
            logger.error("Cannot save lap: No Supabase client available")
            
            # Try to get the global client as a fallback
            try:
                from ..database.supabase_client import supabase as global_client
                logger.debug(f"[SAVE_DEBUG] Fallback: Got global_client. Value: {global_client}, Type: {type(global_client)}")
                if global_client:
                    logger.info("Attempting to use global Supabase client for lap save")
                    self._supabase = global_client
                    logger.debug(f"[SAVE_DEBUG] Fallback: Set self._supabase. Value: {self._supabase}, Type: {type(self._supabase)}")
                    if not self._supabase:
                        logger.error("Global client retrieval failed")
                        return None
                else:
                    logger.error("Global Supabase client not available")
                    return None
            except Exception as e:
                logger.error(f"Error getting global Supabase client: {e}")
                self._connection_disabled = True

        # Check if we have a session ID
        if not self._current_session_id:
            logger.error(f"Cannot save lap: No session ID available")
            return None

        # Check if we have a user ID
        if not self._user_id:
            logger.error("Cannot save lap data: User ID not set")
            return None

        # Debug client capabilities
        logger.debug(f"[SAVE_DEBUG] Checking capabilities of self._supabase. Value: {self._supabase}, Type: {type(self._supabase)}")
        if hasattr(self._supabase, 'table'):
            logger.info("Supabase client has 'table' method")
        else:
            logger.error("Supabase client missing 'table' method - cannot save")
            return None

        # Validate lap data before saving
        is_valid, validation_message = self._validate_lap_data(lap_frames_from_indexer, lap_number)
        logger.info(f"Lap {lap_number} validation: {validation_message}")

        # Determine lap type and leaderboard validity STRICTLY from LapIndexer's output in the frames
        lap_type = "TIMED"  # Default, but should be overwritten by frame data
        is_valid_for_leaderboard = False # Default, should be overwritten
        
        if lap_frames_from_indexer and len(lap_frames_from_indexer) > 0:
            # Use the first frame as representative for these flags, as LapIndexer adds them to all frames of a lap
            first_frame = lap_frames_from_indexer[0]
            lap_type = first_frame.get("lap_state", "TIMED")
            # is_valid_for_leaderboard is now directly taken from what LapIndexer determined and passed in frames
            is_valid_for_leaderboard_from_indexer = first_frame.get("is_valid_for_leaderboard", False)
            
            # The final is_valid_for_leaderboard depends on BOTH LapIndexer's view AND _validate_lap_data's result
            is_valid_for_leaderboard = is_valid and is_valid_for_leaderboard_from_indexer
        else:
            # Fallback if no frames (should not happen for a processed lap from LapIndexer)
            logger.warning(f"Lap {lap_number} has no telemetry frames for determining lap_type/leaderboard_validity in _save_lap_data. Defaulting type to TIMED, leaderboard to False.")
            is_valid_for_leaderboard = False # Cannot be valid if no frames and validation (is_valid) likely failed

        # Log the determined type and leaderboard status
        logger.info(f"Lap {lap_number} final classification for DB: Type={lap_type}, ValidForLeaderboard={is_valid_for_leaderboard} (Validation result: {is_valid})")

        # Prepare lap data
        is_personal_best = lap_time < self._best_lap_time
        if is_personal_best and is_valid_for_leaderboard:
            self._best_lap_time = lap_time
        
        # Generate a UUID for the lap to ensure insert-only approach
        lap_uuid = str(uuid.uuid4())
        
        lap_data = {
            "id": lap_uuid,  # Use UUID as primary key for insert-only approach
            "session_id": self._current_session_id,
            "lap_number": lap_number,
            "lap_time": lap_time,
            "is_valid": is_valid, # Based on validation
            "is_valid_for_leaderboard": is_valid_for_leaderboard, # Based on lap type and validation
            "lap_type": lap_type, # Add the lap type to the database
            "is_personal_best": is_personal_best and is_valid_for_leaderboard, # Only consider valid timed laps
            "user_id": self._user_id, # Include user_id directly
            "metadata": json.dumps({
                 "track_db_id": self._current_track_id,
                 "car_db_id": self._current_car_id,
                 "session_type": self._current_session_type,
                 "validation_message": validation_message,  # Store validation info
                 "point_count": len(lap_frames_from_indexer),
                 "track_coverage": self._calculate_track_coverage(lap_frames_from_indexer)
            })
        }
        
        # Make the save attempt
        try:
            logger.info(f"Saving Lap {lap_number} ({lap_time:.3f}s, Type: {lap_type}) for session {self._current_session_id} with UUID {lap_uuid}")
            
            # Try to insert the lap data
            response = self._supabase.table("laps").insert(lap_data).execute()
                
            if response.data and len(response.data) > 0:
                saved_lap_uuid = response.data[0].get('id', lap_uuid)
                logger.info(f"Successfully saved lap {lap_number} (UUID: {saved_lap_uuid}, Type: {lap_type}, Valid for Leaderboard: {is_valid_for_leaderboard})")
                    
                # Save associated telemetry points
                if lap_frames_from_indexer:
                    self._save_telemetry_points(saved_lap_uuid, lap_frames_from_indexer)

                self._total_laps_saved += 1
                return saved_lap_uuid
            else:
                logger.error(f"Failed to save lap {lap_number}. Response: {response}")
                return None
                
        except Exception as e:
            # Check if the error is a unique constraint violation (session_id, lap_number)
            if "duplicate key value violates unique constraint" in str(e) or "violates unique constraint" in str(e):
                logger.warning(f"Lap {lap_number} for session {self._current_session_id} already exists in database (unique constraint violated)")
                logger.warning(f"This is expected behavior with the new insert-only approach preventing lap overwriting")
                # Record that we attempted to save this lap but it was a duplicate
                self._lap_recording_status[lap_number] = {
                    "status": "duplicate",
                    "message": "Lap already exists in database with this session_id and lap_number"
                }
                return None
            else:
                logger.error(f"Error saving lap {lap_number}: {e}", exc_info=True)
                return None

    def _save_telemetry_points(self, lap_uuid, telemetry_points_from_indexer):
        if not self._supabase or not lap_uuid or not telemetry_points_from_indexer:
            logger.warning("Cannot save telemetry: Missing Supabase client, lap ID, or telemetry data.")
            return False
    
        logger.info(f"Saving {len(telemetry_points_from_indexer)} telemetry points for lap {lap_uuid}")
        batch_size = 100  # Reduced from 500 to allow faster processing of smaller batches
        saved_count = 0
        failed_count = 0
        failed_batch_indices = []  # Track which batches failed
        
        # First ensure points are sorted by track position for consistency
        # The frames from LapIndexer should already include 'track_position' if it was in the raw ir_data
        # LapIndexer stores copies of ir_data, so if 'LapDistPct' was used, it should be there.
        # Assuming 'track_position' key exists, if not, this might need adjustment or LapIndexer guarantees it.
        # For now, let's assume the frames have a comparable field, e.g. 'LapDistPct' if 'track_position' isn't added by LapIndexer itself.
        # The provided LapIndexer code stores the raw ir_data copy, so it will contain 'LapDistPct'.
        # Let's use 'LapDistPct' as the key if 'track_position' (used by original code) is not present.
        def get_sort_key(point):
            if 'track_position' in point: return point['track_position']
            return point.get('LapDistPct', 0) # Fallback to LapDistPct from raw ir_data

        sorted_points = sorted(telemetry_points_from_indexer, key=get_sort_key)
        
        # Then process in batches
        for i in range(0, len(sorted_points), batch_size):
            batch = sorted_points[i:i + batch_size]
            telemetry_data_to_insert = []
            
            for point in batch:
                # Extract key fields, ensuring defaults if missing
                telemetry_data_to_insert.append({
                    "lap_id": lap_uuid,
                    "user_id": self._user_id,
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
                    "batch_index": i // batch_size  # Store batch index for debugging
                })
                
            # Retry logic for batch saving
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = self._supabase.table("telemetry_points").insert(telemetry_data_to_insert).execute()
                    if response.data:
                        saved_count += len(response.data)
                        break  # Success
                    else:
                        logger.warning(f"Batch {i // batch_size} save attempt {retry+1} returned no data")
                        if retry == max_retries - 1:
                            failed_count += len(telemetry_data_to_insert)
                            failed_batch_indices.append(i // batch_size)
                except Exception as e:
                    logger.error(f"Error saving batch {i // batch_size}, attempt {retry+1}: {e}")
                    if retry == max_retries - 1:
                        failed_count += len(telemetry_data_to_insert)
                        failed_batch_indices.append(i // batch_size)
        
        success = failed_count == 0
        logger.info(f"Telemetry saving complete: Saved: {saved_count}, Failed: {failed_count}, Success: {success}")
        
        # If some batches failed, update the lap record to mark it as potentially incomplete
        if failed_count > 0:
            try:
                self._supabase.table("laps").update({
                    "metadata": json.dumps({
                        "telemetry_incomplete": True,
                        "failed_batches": failed_batch_indices,
                        "points_saved": saved_count,
                        "points_failed": failed_count
                    })
                }).eq("id", lap_uuid).execute()
                logger.warning(f"Marked lap {lap_uuid} as having incomplete telemetry")
            except Exception as e:
                logger.error(f"Error updating lap record for incomplete telemetry: {e}")
        
        return success

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
        self.lap_indexer.finalize() # Finalize LapIndexer first to process any remaining laps

        # Get all laps from the indexer, including any that were just finalized
        all_indexed_laps = self.lap_indexer.get_laps()
        newly_processed_laps = 0

        logger.info(f"[SESSION END] LapIndexer has {len(all_indexed_laps)} total laps after finalize.")

        # Process any laps we haven't saved yet
        for indexed_lap in all_indexed_laps:
            sdk_lap_number = indexed_lap["lap_number_sdk"]
            
            # Skip laps we've already processed - use thread-safe check
            with self._processing_lock:
                if sdk_lap_number in self._processed_lap_indexer_lap_numbers:
                    continue
                
                # Mark it as "being processed" to prevent duplicate processing
                self._processed_lap_indexer_lap_numbers.add(sdk_lap_number)
                
            lap_duration = indexed_lap["duration_seconds"]
            lap_telemetry_frames = indexed_lap["telemetry_frames"]
            is_valid_from_indexer = indexed_lap.get("is_valid_from_sdk", True)
            lap_state_from_indexer = indexed_lap.get("lap_state", "TIMED")
            is_valid_for_leaderboard = indexed_lap.get("is_valid_for_leaderboard", False)
            is_incomplete = indexed_lap.get("is_incomplete_session_end", False)

            logger.info(f"[SESSION END] Processing lap {sdk_lap_number} from LapIndexer at session end.")
            logger.info(f"[SESSION END] Lap Details: Time={lap_duration:.3f}s, Type={lap_state_from_indexer}, Frames: {len(lap_telemetry_frames)}, ValidSDK={is_valid_from_indexer}, ValidLeaderboard={is_valid_for_leaderboard}") 
            logger.info(f"[SESSION END] Lap Status: Incomplete={is_incomplete}")

            # Only save valid laps
            if is_valid_from_indexer:
                # Create lap data for queue
                lap_data_for_queue = {
                    "lap_number_sdk": sdk_lap_number,
                    "duration_seconds": lap_duration,
                    "telemetry_frames": lap_telemetry_frames.copy(),
                    "is_valid_from_sdk": is_valid_from_indexer,
                    "lap_state": lap_state_from_indexer,
                    "is_valid_for_leaderboard": is_valid_for_leaderboard,
                    "is_incomplete_session_end": is_incomplete
                }
                
                # Queue the lap for processing
                self._save_worker.enqueue_lap(lap_data_for_queue)
                newly_processed_laps += 1
            else:
                logger.info(f"[SESSION END] Lap {sdk_lap_number} (Type: {lap_state_from_indexer}) from LapIndexer was invalid. Skipping save.")

        if newly_processed_laps > 0:
            logger.info(f"[SESSION END] Queued {newly_processed_laps} additional lap(s) from LapIndexer data at session close.")
            
            # Wait for the worker to finish processing the queue (with timeout)
            logger.info(f"[SESSION END] Waiting for worker to process {self._save_worker.get_queue_size()} queued laps...")
            if self._save_worker.wait_until_empty(timeout=30.0):
                logger.info("[SESSION END] All laps successfully processed by worker")
            else:
                logger.warning("[SESSION END] Timeout waiting for worker to finish - some laps may still be processing")
        else:
            logger.info(f"[SESSION END] No new laps from LapIndexer needed saving at session close.")

        # Reset session state for IRacingLapSaver
        logger.info(f"[SESSION END] Resetting for potential new session. Processed laps history retained.")
        self._is_first_telemetry = True 
        self._current_lap_number = 0
        self._lap_start_time = 0
        self._last_track_position = 0
        self._current_lap_data = []
        # We do NOT clear _processed_lap_indexer_lap_numbers since it's possible
        # we'll reconnect to the same iRacing session after a brief disconnect

        session_folder = getattr(self, '_current_session_folder', None)
        logger.info(f"[SESSION END] Telemetry recording session ended. Session folder: {session_folder}")
        
        return session_folder
        
    def shutdown(self):
        """Clean shutdown of the IRacingLapSaver.
        
        Call this when the application is closing to ensure all laps are saved.
        """
        logger.info("[SHUTDOWN] IRacingLapSaver shutting down")
        
        # Finalize any outstanding laps
        self.end_session()
        
        # Stop the worker thread
        if hasattr(self, '_save_worker'):
            # Wait for up to 5 seconds for the queue to finish
            logger.info(f"[SHUTDOWN] Waiting for worker to finish processing {self._save_worker.get_queue_size()} remaining laps...")
            self._save_worker.wait_until_empty(timeout=5.0)
            
            # Now stop the worker
            self._save_worker.stop()
            
        logger.info("[SHUTDOWN] IRacingLapSaver shutdown complete")