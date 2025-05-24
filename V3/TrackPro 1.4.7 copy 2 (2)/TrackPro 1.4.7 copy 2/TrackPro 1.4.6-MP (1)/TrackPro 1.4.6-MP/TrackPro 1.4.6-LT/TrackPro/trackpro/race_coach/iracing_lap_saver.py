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
from typing import Dict, Any

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

        # Health monitoring
        self._last_activity_time = time.time()
        self._total_processed = 0
        self._total_failed = 0
        self._is_healthy = True
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3

    def run(self):
        logger.info("[SaveLapWorker] Entered run() method.")
        if not self.running:
            logger.error("[SaveLapWorker] Exiting run() because self.running is initially False.")
            return
            
        logger.info("[SaveLapWorker] Starting lap saving worker thread (self.running is True at this point)")
        
        logger.info(f"[SaveLapWorker] IMMEDIATELY BEFORE while loop. self.running = {self.running}")
        while self.running:
            logger.debug("[SaveLapWorker] Entered while self.running loop.")
            lap_data = None
            try:
                logger.debug("[SaveLapWorker] Top of try block in while loop. Attempting to get lap from queue...")
                lap_data = self.lap_queue.get(timeout=1.0)
                
                # Update activity time
                self._last_activity_time = time.time()
                
                # Enhanced debug logging about the item retrieved
                if lap_data is None:
                    logger.warning("[SaveLapWorker] Retrieved None item from queue, which is unexpected")
                elif isinstance(lap_data, dict):
                    logger.info(f"[SaveLapWorker] Successfully got dictionary item from queue. Keys: {lap_data.keys()}")
                elif isinstance(lap_data, tuple):
                    logger.info(f"[SaveLapWorker] Retrieved tuple item from queue, length: {len(lap_data)}")
                else:
                    logger.warning(f"[SaveLapWorker] Retrieved unexpected item type from queue: {type(lap_data)}")
                
                logger.info(f"[SaveLapWorker] Successfully got item from queue. Type: {type(lap_data)}, Item (first 100 chars): {str(lap_data)[:100]}")
                
                if not self.running: 
                    logger.info("[SaveLapWorker] Worker stopping after getting item from queue (self.running became False).")
                    if lap_data: 
                         self.lap_queue.task_done()
                    break

                # Try/except for dictionary access - log more details if it fails
                lap_number_sdk = None
                try:
                    if isinstance(lap_data, dict):
                        lap_number_sdk = lap_data.get("lap_number_sdk")
                        if lap_number_sdk is None:
                            logger.error(f"[SaveLapWorker] Key 'lap_number_sdk' not found in lap_data. Available keys: {lap_data.keys()}")
                    elif isinstance(lap_data, tuple) and len(lap_data) > 0:
                        lap_number_sdk = lap_data[0]
                    else:
                        logger.error(f"[SaveLapWorker] Could not extract lap_number_sdk from data of type {type(lap_data)}")
                except Exception as ke:
                    logger.error(f"[SaveLapWorker] Error extracting lap_number_sdk: {ke}", exc_info=True)
                
                if lap_number_sdk is None:
                    logger.error(f"[SaveLapWorker] Could not determine lap_number_sdk from data: {str(lap_data)[:200]}")
                    self.lap_queue.task_done()
                    self._total_failed += 1
                    self._consecutive_failures += 1
                    continue

                logger.info(f"[SaveLapWorker] Raw lap_data from queue (first 200 chars): {str(lap_data)[:200]}")
                sdk_lap_number = lap_data["lap_number_sdk"]
                logger.info(f"[SaveLapWorker] Extracted sdk_lap_number: {sdk_lap_number}")
                
                if sdk_lap_number in self._processed_lap_numbers:
                    logger.warning(f"[SaveLapWorker] Lap {sdk_lap_number} already processed by worker, skipping")
                    self.lap_queue.task_done()
                    continue
                
                logger.info(f"[SaveLapWorker] Entering save lock for lap {sdk_lap_number}")
                with self.lap_save_lock:
                    logger.info(f"[SaveLapWorker] Processing lap {sdk_lap_number} (queue size: {self.lap_queue.qsize()})")
                    
                    lap_duration = lap_data["duration_seconds"]
                    lap_frames = lap_data["telemetry_frames"]
                    lap_state = lap_data.get("lap_state", "TIMED")
                    is_valid_from_sdk_flag = lap_data.get("is_valid_from_sdk", True) # Renamed to avoid conflict
                    is_valid_for_leaderboard_flag = lap_data.get("is_valid_for_leaderboard", False) # Renamed
                    is_complete_by_sdk = lap_data.get("is_complete_by_sdk_increment", True)

                    lap_frames_with_extra_data = []
                    for frame in lap_frames: # Removed frame_idx as it wasn't used
                        frame_copy = dict(frame)
                        frame_copy["lap_state"] = lap_state
                        frame_copy["is_valid_for_leaderboard"] = is_valid_for_leaderboard_flag 
                        frame_copy["is_complete_by_sdk_increment"] = is_complete_by_sdk
                        lap_frames_with_extra_data.append(frame_copy)
                    
                    self.parent._current_lap_data = lap_frames_with_extra_data 
                    self.parent._current_lap_number = sdk_lap_number 
                    
                    logger.info(f"[SaveLapWorker] Calling parent._save_lap_data for lap {sdk_lap_number}")
                    saved_lap_id = self.parent._save_lap_data(sdk_lap_number, lap_duration, lap_frames_with_extra_data)
                    
                    if saved_lap_id:
                        logger.info(f"[SaveLapWorker] Successfully saved lap {sdk_lap_number} (ID: {saved_lap_id}) in background thread")
                        self._processed_lap_numbers.add(sdk_lap_number)
                        # CRITICAL FIX: Only mark as processed in main thread AFTER successful save
                        self.parent._mark_lap_as_processed(sdk_lap_number, success=True)
                        self._total_processed += 1
                        self._consecutive_failures = 0  # Reset failure counter on success
                        self._is_healthy = True
                    else:
                        logger.error(f"[SaveLapWorker] Parent _save_lap_data returned failure for lap {sdk_lap_number}")
                        # CRITICAL FIX: Notify parent of failure so it can retry or handle appropriately
                        self.parent._mark_lap_as_processed(sdk_lap_number, success=False)
                        self._total_failed += 1
                        self._consecutive_failures += 1
                        
                        # Check if worker should be considered unhealthy
                        if self._consecutive_failures >= self._max_consecutive_failures:
                            self._is_healthy = False
                            logger.error(f"[SaveLapWorker] Worker marked as unhealthy due to {self._consecutive_failures} consecutive failures")
                
                logger.info(f"[SaveLapWorker] Finished processing lap {sdk_lap_number}, marking task done.")
                self.lap_queue.task_done()
                
            except queue.Empty:
                # Update activity time even on empty queue
                self._last_activity_time = time.time()
                continue
            except KeyError as ke:
                logger.error(f"[SaveLapWorker] KeyError processing lap data: {ke}. Data was (first 200 chars): {str(lap_data)[:200]}", exc_info=True)
                self._total_failed += 1
                self._consecutive_failures += 1
                if lap_data: 
                    try:
                        self.lap_queue.task_done()
                        # Try to notify parent of failure
                        lap_num = lap_data.get("lap_number_sdk", -1) if isinstance(lap_data, dict) else -1
                        if lap_num != -1:
                            self.parent._mark_lap_as_processed(lap_num, success=False)
                    except Exception as tde:
                        logger.error(f"[SaveLapWorker] Error calling task_done after KeyError: {tde}")
            except Exception as e:
                logger.error(f"[SaveLapWorker] Generic error in lap saving worker. Data (first 200 chars): {str(lap_data)[:200]}", exc_info=True)
                import traceback
                logger.error(f"[SaveLapWorker] Exception details: {traceback.format_exc()}")
                self._total_failed += 1
                self._consecutive_failures += 1
                if lap_data: 
                    try:
                        self.lap_queue.task_done()
                        # Try to notify parent of failure
                        lap_num = lap_data.get("lap_number_sdk", -1) if isinstance(lap_data, dict) else -1
                        if lap_num != -1:
                            self.parent._mark_lap_as_processed(lap_num, success=False)
                    except Exception as tde:
                        logger.error(f"[SaveLapWorker] Error calling task_done after generic error: {tde}")
        
        logger.info("[SaveLapWorker] Worker thread loop finished.")
    
    def stop(self):
        logger.info(f"[SaveLapWorker] stop() called. Current self.running: {self.running}")
        self.running = False
        logger.info(f"[SaveLapWorker] self.running set to False. Worker thread loop should terminate.")
        
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
    
    def get_health_status(self):
        """Get worker thread health status.
        
        Returns:
            Dictionary with health information
        """
        current_time = time.time()
        time_since_activity = current_time - self._last_activity_time
        
        return {
            "is_healthy": self._is_healthy,
            "is_alive": self.is_alive(),
            "is_running": self.running,
            "total_processed": self._total_processed,
            "total_failed": self._total_failed,
            "consecutive_failures": self._consecutive_failures,
            "time_since_activity": time_since_activity,
            "queue_size": self.get_queue_size(),
            "last_activity_time": self._last_activity_time
        }
    
    def reset_health(self):
        """Reset health status (called after worker restart)."""
        self._consecutive_failures = 0
        self._is_healthy = True
        self._last_activity_time = time.time()
        logger.info("[SaveLapWorker] Health status reset")

class IRacingLapSaver:
    """
    Manages saving iRacing lap times and telemetry data to Supabase.
    """
    def __init__(self, supabase_client=None, user_id=None, diagnostic_mode=False):
        """Initialize the saver."""
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize LapIndexer
        self.lap_indexer = LapIndexer()
        
        # Keep track of lap numbers processed from LapIndexer to avoid duplicates
        self._processed_lap_indexer_lap_numbers = set()
        self._processing_lock = threading.Lock()  # Lock for thread safety
        
        # CRITICAL FIX: Track lap processing state properly
        self._failed_lap_numbers = set()  # Track laps that failed to save
        self._pending_lap_numbers = set()  # Track laps currently being processed
        self._expected_next_lap_number = 0  # For sequence validation
        self._lap_sequence_gaps = []  # Track any gaps in lap sequence
        
        # CIRCUIT BREAKER: Prevent infinite retry loops
        self._lap_retry_count = {}  # Track retry attempts per lap
        self._max_lap_retries = 3  # Maximum retries before giving up
        
        # Set up the background worker for lap saving
        self._save_worker = SaveLapWorker(self)
        self._save_worker.start()
        
        # Add reference to the worker's lap queue
        self._lap_queue = self._save_worker.lap_queue
        
        # Configuration for saving behavior
        self._use_direct_save = True  # BUGFIX: Set to True to bypass the worker thread and save laps directly (worker thread has issues)
        self._save_rejects_to_disk = True  # Save failed laps to disk for debugging
        
        # Log the fix
        logger.info(f"🔧 BUGFIX: IRacingLapSaver initialized with direct save mode enabled to bypass worker thread issues")
        
        # Worker health monitoring
        self._last_health_check_time = time.time()
        self._health_check_interval = 30.0  # Check worker health every 30 seconds
        self._worker_restart_count = 0
        self._max_worker_restarts = 3
        
        # Supabase connection
        self._supabase_client = supabase_client
        self._connection_disabled = False
        
        # User identification
        self._user_id = user_id
        
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
        self._position_buffer_size = 10
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
        self._diagnostic_mode = diagnostic_mode
        self._position_log_file = None
        self._telemetry_debug_counter = 0
        
        # Setup telemetry debug counter
        self._debug_interval = 300  # Log debug info every ~300 iterations

        # Rate limiting for warnings
        self._last_invalid_lap_number_warning_time: float = 0.0
        self._last_invalid_lap_number_warning_message: str = ""
        self._warning_interval: float = 5.0  # seconds

        # Initialize connection state
        self._is_connected = False
        self._authenticated = False
        
        # Initialize lap tracking
        self._current_track_config = None
        
        # Enhanced lap debugging for sync issues
        self._lap_debug_mapping = {}  # Maps iRacing LapCompleted to our internal lap numbers
        self._lap_sync_issues = []    # Tracks detected synchronization issues
        self._debug_mode = True       # Enable detailed debugging by default
        
        # CRITICAL THREADING FIX: Asynchronous save system to prevent blocking telemetry collection
        self._async_save_thread = None
        self._async_save_queue = queue.Queue()
        self._async_save_running = False
        self._start_async_save_thread()

    def set_supabase_client(self, client):
        """Set the Supabase client instance."""
        self._supabase_client = client
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
        if not self._supabase_client:
            try:
                # Import here to avoid circular imports
                from ..database.supabase_client import supabase as global_client
                if global_client:
                    logger.info("Using global Supabase client instance as fallback")
                    self._supabase_client = global_client
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
            # The LapIndexer now has improved reset detection and telemetry association
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
                # Get current lap from LapIndexer (authoritative source)
                lap_indexer_current = getattr(self.lap_indexer, '_active_lap_number_internal', 'N/A')
                logger.info(f"🔧 LAP SYNC DEBUG: LapDistPct={lap_dist_pct:.3f}, Last={self._last_track_position:.3f}, " +
                           f"iRacing Current={iracing_current_lap}, iRacing Completed={iracing_completed_lap}, " + 
                           f"LapIndexer Current={lap_indexer_current}, Internal (deprecated)={self._current_lap_number}, SessionTime={session_time:.3f}")

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
                # CRITICAL FIX: Sync internal counter with iRacing's completed lap number
                # This ensures we start with the correct lap numbering from iRacing
                self._current_lap_number = iracing_completed_lap
                self._is_first_telemetry = False
                self._current_lap_data = []
                logger.info(f"🔧 LAP SYNC FIX: First telemetry - iRacing Current={iracing_current_lap}, Completed={iracing_completed_lap}, Setting internal to {self._current_lap_number}. Session: {self._current_session_id}")

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

            # CRITICAL FIX: Check worker health before processing laps
            self._check_worker_health()

            # Process any laps we haven't seen yet (using thread-safe check)
            for indexed_lap in indexed_laps:
                sdk_lap_number = indexed_lap["lap_number_sdk"]
                
                # CRITICAL FIX: Skip laps we've already processed OR are currently pending OR have failed
                with self._processing_lock:
                    if (sdk_lap_number in self._processed_lap_indexer_lap_numbers or 
                        sdk_lap_number in self._pending_lap_numbers):
                        continue
                    
                    # Mark as pending (will be marked as processed by callback after actual save)
                    self._pending_lap_numbers.add(sdk_lap_number)
                    
                lap_duration = indexed_lap["duration_seconds"]
                lap_telemetry_frames = indexed_lap["telemetry_frames"]
                is_valid_from_indexer = indexed_lap.get("is_valid_from_sdk", True)  # Use is_valid_from_sdk flag
                lap_state_from_indexer = indexed_lap.get("lap_state", "TIMED")  # Get lap state (OUT, TIMED, IN, INCOMPLETE)
                is_valid_for_leaderboard = indexed_lap.get("is_valid_for_leaderboard", False)  # Get leaderboard validity flag
                is_complete_by_sdk = indexed_lap.get("is_complete_by_sdk_increment", True)
                
                # Extract iRacing lap information from the first frame of this lap
                # This is crucial for mapping our internal lap numbers to iRacing's numbers
                iracing_lap_info = {}
                if lap_telemetry_frames and len(lap_telemetry_frames) > 0:
                    first_frame = lap_telemetry_frames[0]
                    iracing_lap_info = {
                        "ir_lap": first_frame.get("Lap", -1),
                        "ir_completed": first_frame.get("LapCompleted", -1),
                        "lap_dist": first_frame.get("LapDistPct", -1.0),
                        "session_time": first_frame.get("SessionTimeSecs", 0.0)
                    }
                
                # Debug logging for lap synchronization
                self._debug_lap_sync(
                    f"Processing new lap from LapIndexer: SDK#{sdk_lap_number}, Type={lap_state_from_indexer}, Valid={is_valid_from_indexer}",
                    iracing_lap_info if iracing_lap_info else {"Lap": -1, "LapCompleted": sdk_lap_number},
                    sdk_lap_number
                )
                
                # IMPORTANT FIX FOR LAP NUMBER SYNCHRONIZATION:
                # The correct lap number to use is the lap_number_sdk from the LapIndexer
                # This ensures we're using iRacing's lap numbering system
                correct_lap_number = sdk_lap_number
                
                # CRITICAL FIX: Keep internal counter synchronized with iRacing
                if correct_lap_number != self._current_lap_number:
                    logger.info(f"🔧 [LAP SYNC FIX] Correcting internal lap counter from {self._current_lap_number} to iRacing {correct_lap_number}")
                    self._current_lap_number = correct_lap_number  # Keep internal counter in sync
                
                # Now process this lap with the correct lap number
                logger.info(f"[LapIndexer] New lap {correct_lap_number} to process. Time: {lap_duration:.3f}s, Type: {lap_state_from_indexer}, Valid: {is_valid_from_indexer}, Valid for Leaderboard: {is_valid_for_leaderboard}")
                
                # CRITICAL BUG FIX: Skip only truly invalid lap numbers (negative laps)
                # Note: lap 0 is valid in iRacing (it's the outlap)
                if correct_lap_number < 0:
                    logger.warning(f"[LAP VALIDATION] Skipping invalid lap number {correct_lap_number} - negative lap numbers are invalid")
                    # Mark as processed to prevent infinite retry
                    self._mark_lap_as_processed(sdk_lap_number, success=False)
                    continue
                
                # Create a properly formatted lap data dictionary
                # CRITICAL: Always use the LapIndexer's SDK lap number (from iRacing) as the authoritative lap number
                lap_data_dict = {
                    "lap_number_sdk": correct_lap_number,  # This is iRacing's LapCompleted value - authoritative
                    "lap_number": correct_lap_number,      # Also set regular lap_number for consistency
                    "duration_seconds": lap_duration,
                    "telemetry_frames": lap_telemetry_frames,
                    "lap_state": lap_state_from_indexer,
                    "is_valid_from_sdk": is_valid_from_indexer,
                    "is_valid_for_leaderboard": is_valid_for_leaderboard,
                    "is_complete_by_sdk_increment": is_complete_by_sdk
                }
                
                # CRITICAL FIX: Update all telemetry frames with the correct final lap classification
                # This ensures that validation gets the correct lap type from the LapIndexer's final decision
                updated_telemetry_frames = []
                for frame in lap_telemetry_frames:
                    frame_copy = dict(frame)
                    # Override any stale lap_state data with the LapIndexer's final classification
                    frame_copy["lap_state"] = lap_state_from_indexer
                    frame_copy["is_valid_for_leaderboard"] = is_valid_for_leaderboard
                    frame_copy["is_complete_by_sdk_increment"] = is_complete_by_sdk
                    updated_telemetry_frames.append(frame_copy)
                
                # Update the lap data dict with corrected frames
                lap_data_dict["telemetry_frames"] = updated_telemetry_frames
                
                # Check if direct saving is enabled
                if self._use_direct_save:
                    # CRITICAL THREADING FIX: Use truly asynchronous saving to avoid blocking telemetry collection
                    logger.info(f"[ASYNC] Using non-blocking asynchronous save for lap {correct_lap_number}")
                    self.save_lap_async(lap_data_dict)
                    # Mark as pending immediately, will be marked as processed by async callback
                    # Don't mark as processed here since it's asynchronous
                else:
                    # Monitor queue size - if it's getting too large, something might be wrong with the worker
                    queue_size = self._lap_queue.qsize() if self._lap_queue else 0
                    if queue_size >= 5:  # If we have 5+ laps queued, the worker might be stuck
                        logger.warning(f"[QUEUE HEALTH] Queue size has reached {queue_size} items. Worker thread may be stuck. Saving directly as fallback.")
                        success = self.save_lap_directly(lap_data_dict)
                        # CRITICAL FIX: Mark as processed based on actual result
                        self._mark_lap_as_processed(correct_lap_number, success=(success is not None))
                        
                        # Check if we should force-enable direct saving
                        if queue_size >= 10:  # If queue has 10+ items, permanently switch to direct saving
                            logger.error(f"[QUEUE HEALTH] Queue size is {queue_size}, which is unacceptably high. Enabling direct saving mode permanently.")
                            self.enable_direct_save(True)
                    else:
                        # Queue lap for background saving using correct lap number 
                        # (only if worker thread doesn't seem to be having problems)
                        with self._lap_queue.mutex:
                            # Check if the lap is already in the queue
                            existing_lap_nums = []
                            for item in list(self._lap_queue.queue):
                                if isinstance(item, dict):
                                    existing_lap_nums.append(item.get("lap_number_sdk", -1))
                                elif isinstance(item, tuple) and len(item) > 0:
                                    existing_lap_nums.append(item[0])
                            
                            if correct_lap_number not in existing_lap_nums:
                                logger.info(f"[SaveLapWorker] Enqueueing lap {correct_lap_number} for background processing")
                                # IMPORTANT: Make sure we always put a dictionary in the queue
                                self._lap_queue.put(lap_data_dict)
                                # Debug verify what was placed in the queue
                                logger.info(f"[QUEUE DEBUG] Added item to queue. Type: {type(lap_data_dict)}, Keys: {lap_data_dict.keys()}")
                            else:
                                logger.warning(f"[SaveLapWorker] Lap {correct_lap_number} already in queue, skipping duplicate")
                                # CRITICAL FIX: If already in queue, remove from pending since we're not processing it again
                                with self._processing_lock:
                                    self._pending_lap_numbers.discard(correct_lap_number)
                
                # Get the last section of telemetry for this lap to return to UI immediately
                # The full telemetry will be processed and saved in the background
                if len(lap_telemetry_frames) > 0:
                    last_section = lap_telemetry_frames[-10:] if len(lap_telemetry_frames) > 10 else lap_telemetry_frames
                    laps_to_return_to_ui.append({
                        "lap_number": correct_lap_number,
                        "lap_time": lap_duration,
                        "telemetry": last_section,
                        "is_new_lap": True,
                        "lap_state": lap_state_from_indexer
                    })

            # Return the most recent lap completion if there is one
            if laps_to_return_to_ui:
                # Get most recent lap based on session time
                most_recent = max(laps_to_return_to_ui, key=lambda x: x["telemetry"][-1].get("SessionTimeSecs", 0) if x["telemetry"] else 0)
                lap_number = most_recent["lap_number"]
                lap_time = most_recent["lap_time"]
                
                # Basic telemetry frame with just the completion notification
                telemetry_with_completion = {**telemetry_data, "is_new_lap": True, "completed_lap_number": lap_number, "completed_lap_time": lap_time}
                return telemetry_with_completion

        except Exception as e:
            logger.error(f"Error processing telemetry: {e}", exc_info=True)

        return telemetry_data
        
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
        logger.info(f"Attempting to save lap {lap_number} (time: {lap_time:.3f}s)")
        
        # Verify that we have a Supabase client and session
        if not self._supabase_client:
            logger.error("[CRITICAL] Supabase client not available, cannot save lap data. Make sure client is set properly at initialization.")
            return None
            
        if not self._current_session_id:
            logger.error("[CRITICAL] No active session ID, cannot save lap data. Ensure a session is created before saving laps.")
            
            # Log additional debug information about session state
            logger.error(f"[DEBUG] Session state: _current_session_id={self._current_session_id}, _current_car_id={self._current_car_id}, _current_track_id={self._current_track_id}")
            
            # Special case for handling missing session ID
            if not self._current_session_id and not self._connection_disabled:
                logger.warning("[RECOVERY] No session ID but connection is available. This could indicate the session wasn't properly created.")
                
            return None
            
        # Log connection state for debugging
        logger.info(f"Connection state: Supabase client exists: {self._supabase_client is not None}, Session ID: {self._current_session_id}")
        
        # Check that the client has the 'table' method before using it
        if not hasattr(self._supabase_client, 'table'):
            logger.error("[CRITICAL] Supabase client does not have 'table' method, cannot save lap data. Check client initialization.")
            return None
        logger.info("Supabase client has 'table' method")
        
        # Validate lap telemetry data before saving
        is_valid, validation_message = self._validate_lap_data(lap_frames_from_indexer, lap_number)
        logger.info(f"Lap {lap_number} validation: {validation_message}")

        # CRITICAL FIX: Get lap type directly from the method parameters instead of from frames
        # The lap frames should now have the correct lap_state thanks to our fix above
        lap_type = "TIMED"  # Default fallback
        is_valid_for_leaderboard = False # Default fallback
        
        if lap_frames_from_indexer and len(lap_frames_from_indexer) > 0:
            # Use the first frame which should now have the correct final lap classification
            first_frame = lap_frames_from_indexer[0]
            lap_type = first_frame.get("lap_state", "TIMED")
            # Get the leaderboard validity from the frame (updated by our fix above)
            is_valid_for_leaderboard_from_indexer = first_frame.get("is_valid_for_leaderboard", False)
            
            # The final is_valid_for_leaderboard depends on BOTH LapIndexer's view AND _validate_lap_data's result
            is_valid_for_leaderboard = is_valid and is_valid_for_leaderboard_from_indexer
            
            logger.info(f"[LAP TYPE FIX] Lap {lap_number} type from corrected frames: {lap_type}, leaderboard: {is_valid_for_leaderboard_from_indexer}")
        else:
            logger.warning(f"[LAP TYPE FIX] Lap {lap_number} has no frames - using fallback classification")
        
        # Add debugging for lap number consistency
        if lap_frames_from_indexer and len(lap_frames_from_indexer) > 0:
            ir_lap = first_frame.get("Lap", -1)
            ir_completed = first_frame.get("LapCompleted", -1)
            logger.info(f"[LAP SYNC] Saving lap {lap_number} with iRacing Lap={ir_lap}, LapCompleted={ir_completed}")
            
            # Additional debugging for lap number mismatch
            if ir_completed > 0 and ir_completed - 1 != lap_number:
                logger.warning(f"[LAP SYNC] Potential lap number mismatch: saving lap {lap_number} but iRacing LapCompleted={ir_completed}")
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
            response = self._supabase_client.table("laps").insert(lap_data).execute()
                
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
        if not self._supabase_client or not lap_uuid or not telemetry_points_from_indexer:
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
                    response = self._supabase_client.table("telemetry_points").insert(telemetry_data_to_insert).execute()
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
                self._supabase_client.table("laps").update({
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
        if not self._supabase_client:
            logger.error("Cannot get lap times: Supabase connection not available")
            return []
        
        session_id = session_id or self._current_session_id
        if not session_id:
            logger.error("Cannot get lap times: No session ID specified")
            return []
        
        try:
            result = self._supabase_client.table("laps").select("*").eq("session_id", session_id).order("lap_number").execute()
            
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
        if not self._supabase_client:
            logger.error("Cannot get telemetry data: Supabase connection not available")
            return []
        
        try:
            result = self._supabase_client.table("telemetry_points").select("*").eq("lap_id", lap_id).order("track_position").execute()
            
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
        if not self._supabase_client:
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
                    response = self._supabase_client.table(table).select("id").limit(1).execute()
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
            
            # CRITICAL FIX: Skip laps we've already processed OR are currently pending
            with self._processing_lock:
                if (sdk_lap_number in self._processed_lap_indexer_lap_numbers or 
                    sdk_lap_number in self._pending_lap_numbers):
                    continue
                
                # Mark as pending for session end processing
                self._pending_lap_numbers.add(sdk_lap_number)
                
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
                
                # CRITICAL FIX: Use direct save for session end to ensure completion
                logger.info(f"[SESSION END] Using direct save for lap {sdk_lap_number} to ensure completion")
                success = self.save_lap_directly(lap_data_for_queue)
                self._mark_lap_as_processed(sdk_lap_number, success=(success is not None))
                
                if success:
                    newly_processed_laps += 1
            else:
                logger.info(f"[SESSION END] Lap {sdk_lap_number} (Type: {lap_state_from_indexer}) from LapIndexer was invalid. Skipping save.")
                # Mark as processed (failed) to remove from pending
                self._mark_lap_as_processed(sdk_lap_number, success=False)

        if newly_processed_laps > 0:
            logger.info(f"[SESSION END] Processed {newly_processed_laps} additional lap(s) from LapIndexer data at session close.")
        else:
            logger.info(f"[SESSION END] No new laps from LapIndexer needed saving at session close.")

        # Wait for any remaining worker tasks to complete (but don't wait too long)
        if self._save_worker and self._save_worker.is_alive():
            logger.info(f"[SESSION END] Waiting for worker to process {self._save_worker.get_queue_size()} remaining queued laps...")
            if self._save_worker.wait_until_empty(timeout=10.0):
                logger.info("[SESSION END] All queued laps successfully processed by worker")
            else:
                logger.warning("[SESSION END] Timeout waiting for worker to finish - some laps may still be processing")

        # Log session end statistics
        with self._processing_lock:
            total_processed = len(self._processed_lap_indexer_lap_numbers)
            total_failed = len(self._failed_lap_numbers)
            total_pending = len(self._pending_lap_numbers)
            logger.info(f"[SESSION END] Final session statistics: Processed: {total_processed}, Failed: {total_failed}, Still Pending: {total_pending}")
            
            if self._lap_sequence_gaps:
                logger.warning(f"[SESSION END] Detected {len(self._lap_sequence_gaps)} lap sequence gaps during session")
                for gap in self._lap_sequence_gaps:
                    logger.warning(f"[SESSION END] Gap: laps {gap['gap_start']} to {gap['gap_end']} (missing {gap['missing_count']} laps)")

        # Reset session state for IRacingLapSaver
        logger.info(f"[SESSION END] Resetting for potential new session. Processed laps history retained.")
        self._is_first_telemetry = True 
        self._current_lap_number = 0
        self._lap_start_time = 0
        self._last_track_position = 0
        self._current_lap_data = []
        
        # CRITICAL FIX: Reset lap tracking state for new session
        with self._processing_lock:
            self._pending_lap_numbers.clear()
            self._failed_lap_numbers.clear()
            self._expected_next_lap_number = 0
            self._lap_sequence_gaps.clear()
            self._lap_retry_count.clear()  # Reset retry counters
            # Keep _processed_lap_indexer_lap_numbers for potential reconnect to same session

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

    def _debug_lap_sync(self, message: str, ir_data: Dict[str, Any], internal_lap: int = None):
        """Log detailed lap synchronization debug information.
        
        Args:
            message: Debug message
            ir_data: Current iRacing data frame
            internal_lap: Our internal lap number (if available)
        """
        if not self._debug_mode:
            return
            
        ir_lap = ir_data.get("Lap", -1)
        ir_completed = ir_data.get("LapCompleted", -1)
        
        if internal_lap is None:
            internal_lap = self._current_lap_number
            
        # Store mapping information
        self._lap_debug_mapping[ir_completed] = internal_lap
        
        # Check for potential sync issues
        if ir_completed > 0 and ir_completed - 1 != internal_lap:
            issue = {
                "timestamp": time.time(),
                "ir_completed": ir_completed,
                "internal_lap": internal_lap,
                "message": f"Sync issue: iRacing LapCompleted={ir_completed}, our internal lap={internal_lap}"
            }
            self._lap_sync_issues.append(issue)
            logger.warning(f"[LAP SYNC] {issue['message']}")
            
        session_time = ir_data.get("SessionTimeSecs", 0)
        lap_dist = ir_data.get("LapDistPct", -1.0)
        
        # Format a detailed debug message
        debug_msg = (
            f"[LAP SYNC] {message} - "
            f"iRacing: Lap={ir_lap}, Completed={ir_completed}, Dist={lap_dist:.3f} - "
            f"Internal: CurrentLap={internal_lap} - "
            f"Time: {session_time:.2f}s"
        )
        
        logger.info(debug_msg)

    def enable_direct_save(self, enabled=True):
        """Enable or disable direct lap saving, bypassing the worker thread.
        
        Args:
            enabled: Whether to enable direct saving
        """
        old_value = self._use_direct_save
        self._use_direct_save = enabled
        logger.info(f"Direct lap saving {'enabled' if enabled else 'disabled'} (was: {'enabled' if old_value else 'disabled'})")
        
    def save_lap_directly(self, lap_data_dict):
        """Save a lap directly without using the worker thread.
        
        This is a fallback mechanism for when the worker thread is not functioning properly.
        
        Args:
            lap_data_dict: Dictionary with lap data in the same format used by the worker
            
        Returns:
            Lap UUID if saved successfully, None otherwise
        """
        try:
            # CRITICAL BUG FIX: Validate lap_data_dict structure
            if not isinstance(lap_data_dict, dict):
                logger.error(f"[DIRECT SAVE] Invalid lap_data_dict type: {type(lap_data_dict)}")
                return None
                
            logger.info(f"[DIRECT SAVE] Attempting to directly save lap {lap_data_dict.get('lap_number_sdk', 'unknown')}")
            
            sdk_lap_number = lap_data_dict.get("lap_number_sdk")
            if not sdk_lap_number or sdk_lap_number <= 0:
                logger.error(f"[DIRECT SAVE] Invalid lap_number_sdk: {sdk_lap_number}. Available keys: {list(lap_data_dict.keys())}")
                return None
                
            # CRITICAL FIX: Don't skip if already processed - let the callback system handle that
            # if sdk_lap_number in self._processed_lap_indexer_lap_numbers:
            #     logger.warning(f"[DIRECT SAVE] Lap {sdk_lap_number} already processed, skipping")
            #     return None
                
            lap_duration = lap_data_dict.get("duration_seconds", 0)
            lap_frames = lap_data_dict.get("telemetry_frames", [])
            
            # Call the internal save method directly
            saved_lap_id = self._save_lap_data(sdk_lap_number, lap_duration, lap_frames)
            
            if saved_lap_id:
                logger.info(f"[DIRECT SAVE] Successfully saved lap {sdk_lap_number} directly")
                # CRITICAL FIX: Don't mark as processed here - let the caller handle it via callback
                return saved_lap_id
            else:
                logger.error(f"[DIRECT SAVE] Failed to save lap {sdk_lap_number} directly")
                
                # If configured to save to disk, do that as a fallback
                if self._save_rejects_to_disk:
                    self._save_lap_to_disk(sdk_lap_number, lap_duration, lap_frames)
                    
                return None
                
        except Exception as e:
            logger.error(f"[DIRECT SAVE] Error saving lap directly: {e}", exc_info=True)
            return None
            
    def _save_lap_to_disk(self, lap_number, lap_duration, lap_frames):
        """Save a lap to disk as JSON (fallback when database saving fails)."""
        try:
            if not lap_frames:
                logger.warning(f"[DISK SAVE] No frames to save for lap {lap_number}")
                return False
                
            # Create directory if it doesn't exist
            fallback_dir = Path(os.path.expanduser("~/Documents/TrackPro/FallbackLaps"))
            fallback_dir.mkdir(parents=True, exist_ok=True)
            
            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = fallback_dir / f"lap_{lap_number}_{timestamp}.json"
            
            # Save to file
            lap_data = {
                "lap_number": lap_number,
                "lap_time": lap_duration,
                "timestamp": time.time(),
                "session_id": self._current_session_id,
                "track_id": self._current_track_id,
                "car_id": self._current_car_id,
                "user_id": self._user_id,
                "point_count": len(lap_frames),
                "points": lap_frames
            }
            
            with open(filename, 'w') as f:
                json.dump(lap_data, f)
                
            logger.info(f"[DISK SAVE] Saved lap {lap_number} to disk: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"[DISK SAVE] Error saving lap {lap_number} to disk: {e}")
            return False

    def _mark_lap_as_processed(self, lap_number, success=True):
        """CRITICAL FIX: Callback method to mark laps as processed after actual completion.
        
        This fixes the race condition where laps were marked as processed before they were actually saved.
        
        Args:
            lap_number: The lap number that was processed
            success: Whether the processing was successful
        """
        with self._processing_lock:
            # Remove from pending
            self._pending_lap_numbers.discard(lap_number)
            
            if success:
                self._processed_lap_indexer_lap_numbers.add(lap_number)
                # Remove from failed set if it was there
                self._failed_lap_numbers.discard(lap_number)
                # Reset retry count on success
                self._lap_retry_count.pop(lap_number, None)
                logger.info(f"[LAP PROCESSING] Lap {lap_number} successfully processed and marked as complete")
                
                # Update expected sequence
                self._validate_lap_sequence(lap_number)
            else:
                # CIRCUIT BREAKER: Track retry attempts
                retry_count = self._lap_retry_count.get(lap_number, 0) + 1
                self._lap_retry_count[lap_number] = retry_count
                
                if retry_count >= self._max_lap_retries:
                    logger.error(f"[CIRCUIT BREAKER] Lap {lap_number} failed {retry_count} times - giving up to prevent infinite loop")
                    self._failed_lap_numbers.add(lap_number)
                    self._processed_lap_indexer_lap_numbers.add(lap_number)  # Mark as processed to stop retries
                    self._lap_retry_count.pop(lap_number, None)  # Clean up
                else:
                    logger.warning(f"[LAP PROCESSING] Lap {lap_number} failed (attempt {retry_count}/{self._max_lap_retries})")
                    
                    # Only consider retrying if under the limit
                    if self._use_direct_save and retry_count < self._max_lap_retries:
                        logger.info(f"[LAP PROCESSING] Will retry failed lap {lap_number} (attempt {retry_count + 1})")
    
    def _validate_lap_sequence(self, lap_number):
        """Validate lap sequence and detect gaps.
        
        Args:
            lap_number: The lap number to validate in sequence
        """
        if self._expected_next_lap_number == 0:
            # First lap, initialize expected sequence
            self._expected_next_lap_number = lap_number + 1
            logger.info(f"[LAP SEQUENCE] Initializing sequence at lap {lap_number}")
        elif lap_number == self._expected_next_lap_number - 1:
            # Expected sequence, no action needed
            pass
        elif lap_number == self._expected_next_lap_number:
            # Next in sequence
            self._expected_next_lap_number = lap_number + 1
        elif lap_number > self._expected_next_lap_number:
            # Gap detected
            gap_start = self._expected_next_lap_number
            gap_end = lap_number - 1
            gap_info = {
                "gap_start": gap_start,
                "gap_end": gap_end,
                "missing_count": gap_end - gap_start + 1,
                "detected_at": time.time()
            }
            self._lap_sequence_gaps.append(gap_info)
            logger.warning(f"[LAP SEQUENCE] Gap detected: missing laps {gap_start} to {gap_end} (received lap {lap_number})")
            self._expected_next_lap_number = lap_number + 1
        else:
            # Received older lap - could be out of order processing
            logger.info(f"[LAP SEQUENCE] Received older lap {lap_number} (expected {self._expected_next_lap_number})")
    
    def _check_worker_health(self):
        """Check worker thread health and restart if necessary.
        
        Returns:
            bool: True if worker is healthy, False if restarted or failed
        """
        current_time = time.time()
        
        # Only check health periodically
        if current_time - self._last_health_check_time < self._health_check_interval:
            return True
            
        self._last_health_check_time = current_time
        
        # Get health status from worker
        if not self._save_worker or not self._save_worker.is_alive():
            logger.error("[WORKER HEALTH] Worker thread is not alive")
            return self._restart_worker("Thread not alive")
            
        health_status = self._save_worker.get_health_status()
        logger.debug(f"[WORKER HEALTH] Status: {health_status}")
        
        # Check if worker is unhealthy
        if not health_status["is_healthy"]:
            logger.error(f"[WORKER HEALTH] Worker marked as unhealthy: {health_status}")
            return self._restart_worker("Worker marked as unhealthy")
            
        # Check if worker has been inactive too long
        if health_status["time_since_activity"] > 300:  # 5 minutes
            logger.warning(f"[WORKER HEALTH] Worker inactive for {health_status['time_since_activity']:.1f} seconds")
            
        # Check if queue is backing up excessively
        if health_status["queue_size"] > 20:
            logger.error(f"[WORKER HEALTH] Queue backing up excessively: {health_status['queue_size']} items")
            return self._restart_worker("Queue backing up")
            
        return True
    
    def _restart_worker(self, reason):
        """Restart the worker thread.
        
        Args:
            reason: Reason for restart
            
        Returns:
            bool: True if restart successful, False if max restarts exceeded
        """
        self._worker_restart_count += 1
        
        if self._worker_restart_count > self._max_worker_restarts:
            logger.error(f"[WORKER RESTART] Max restart attempts ({self._max_worker_restarts}) exceeded. Enabling direct save mode.")
            self.enable_direct_save(True)
            return False
            
        logger.info(f"[WORKER RESTART] Restarting worker thread (attempt {self._worker_restart_count}/{self._max_worker_restarts}). Reason: {reason}")
        
        # Stop old worker
        if self._save_worker:
            self._save_worker.stop()
            # Don't wait too long for it to stop
            if self._save_worker.is_alive():
                self._save_worker.join(timeout=5.0)
                
        # Create new worker
        self._save_worker = SaveLapWorker(self)
        self._save_worker.reset_health()
        self._save_worker.start()
        
        # Update reference
        self._lap_queue = self._save_worker.lap_queue
        
        logger.info("[WORKER RESTART] New worker thread started")
        return True

    def retry_failed_laps(self):
        """Attempt to retry laps that failed to save.
        
        Returns:
            Dictionary with retry results
        """
        with self._processing_lock:
            failed_laps = self._failed_lap_numbers.copy()
            
        if not failed_laps:
            return {"success": True, "message": "No failed laps to retry", "retried": 0, "succeeded": 0}
            
        logger.info(f"[RETRY] Attempting to retry {len(failed_laps)} failed laps")
        
        retried = 0
        succeeded = 0
        
        # Get current laps from indexer to find the failed ones
        all_indexed_laps = self.lap_indexer.get_laps()
        lap_data_by_number = {lap["lap_number_sdk"]: lap for lap in all_indexed_laps}
        
        for failed_lap_number in failed_laps:
            if failed_lap_number not in lap_data_by_number:
                logger.warning(f"[RETRY] Failed lap {failed_lap_number} not found in indexer data")
                continue
                
            lap_data = lap_data_by_number[failed_lap_number]
            lap_data_dict = {
                "lap_number_sdk": failed_lap_number,
                "duration_seconds": lap_data["duration_seconds"],
                "telemetry_frames": lap_data["telemetry_frames"],
                "lap_state": lap_data.get("lap_state", "TIMED"),
                "is_valid_from_sdk": lap_data.get("is_valid_from_sdk", True),
                "is_valid_for_leaderboard": lap_data.get("is_valid_for_leaderboard", False),
                "is_complete_by_sdk_increment": lap_data.get("is_complete_by_sdk_increment", True)
            }
            
            logger.info(f"[RETRY] Retrying failed lap {failed_lap_number}")
            success = self.save_lap_directly(lap_data_dict)
            retried += 1
            
            if success:
                succeeded += 1
                self._mark_lap_as_processed(failed_lap_number, success=True)
                logger.info(f"[RETRY] Successfully retried lap {failed_lap_number}")
            else:
                logger.error(f"[RETRY] Retry failed for lap {failed_lap_number}")
                
        return {
            "success": succeeded > 0,
            "message": f"Retried {retried} laps, {succeeded} succeeded",
            "retried": retried,
            "succeeded": succeeded
        }

    def get_processing_status(self):
        """Get comprehensive processing status for diagnostics.
        
        Returns:
            Dictionary with processing statistics
        """
        with self._processing_lock:
            processed_count = len(self._processed_lap_indexer_lap_numbers)
            failed_count = len(self._failed_lap_numbers)
            pending_count = len(self._pending_lap_numbers)
            gap_count = len(self._lap_sequence_gaps)
            
            # Get worker health if available
            worker_health = None
            if self._save_worker and self._save_worker.is_alive():
                try:
                    worker_health = self._save_worker.get_health_status()
                except:
                    worker_health = {"error": "Could not get worker health"}
            
            return {
                "processed_laps": processed_count,
                "failed_laps": failed_count,
                "pending_laps": pending_count,
                "sequence_gaps": gap_count,
                "expected_next_lap": self._expected_next_lap_number,
                "worker_restarts": self._worker_restart_count,
                "direct_save_mode": self._use_direct_save,
                "worker_health": worker_health,
                "failed_lap_numbers": list(self._failed_lap_numbers),
                "pending_lap_numbers": list(self._pending_lap_numbers),
                "sequence_gap_details": self._lap_sequence_gaps.copy()
            }

    def shutdown(self):
        """Clean shutdown of the IRacingLapSaver.
        
        Call this when the application is closing to ensure all laps are saved.
        """
        logger.info("[SHUTDOWN] IRacingLapSaver shutting down")
        
        # Finalize any outstanding laps
        self.end_session()
        
        # Get final processing status
        status = self.get_processing_status()
        logger.info(f"[SHUTDOWN] Final processing status: {status}")
        
        # Stop the worker thread
        if hasattr(self, '_save_worker') and self._save_worker:
            # Wait for up to 10 seconds for the queue to finish
            logger.info(f"[SHUTDOWN] Waiting for worker to finish processing {self._save_worker.get_queue_size()} remaining laps...")
            self._save_worker.wait_until_empty(timeout=10.0)
            
            # Now stop the worker
            self._save_worker.stop()
            
            # Wait for worker thread to actually stop
            if self._save_worker.is_alive():
                logger.info("[SHUTDOWN] Waiting for worker thread to stop...")
                self._save_worker.join(timeout=5.0)
                if self._save_worker.is_alive():
                    logger.warning("[SHUTDOWN] Worker thread did not stop gracefully")
                else:
                    logger.info("[SHUTDOWN] Worker thread stopped successfully")
            
        # Attempt to retry any failed laps one more time
        retry_result = self.retry_failed_laps()
        if retry_result["retried"] > 0:
            logger.info(f"[SHUTDOWN] Final retry attempt: {retry_result['message']}")
            
        # Stop the async save thread
        if hasattr(self, '_async_save_running') and self._async_save_running:
            logger.info("🧵 [ASYNC SAVE] Stopping async save thread...")
            self._async_save_running = False
            
            # Signal shutdown
            try:
                self._async_save_queue.put(None, timeout=1.0)
            except:
                pass
            
            # Wait for thread to finish
            if hasattr(self, '_async_save_thread') and self._async_save_thread and self._async_save_thread.is_alive():
                self._async_save_thread.join(timeout=5.0)
                if self._async_save_thread.is_alive():
                    logger.warning("🧵 [ASYNC SAVE] Thread did not stop within timeout")
                else:
                    logger.info("🧵 [ASYNC SAVE] Thread stopped successfully")
            
        logger.info("[SHUTDOWN] IRacingLapSaver shutdown complete")

    def _start_async_save_thread(self):
        """Start the asynchronous save thread."""
        if hasattr(self, '_async_save_thread') and self._async_save_thread and self._async_save_thread.is_alive():
            return  # Thread already running
        
        self._async_save_running = True
        self._async_save_thread = threading.Thread(target=self._async_save_worker, daemon=True)
        self._async_save_thread.start()
        logger.info("🧵 [ASYNC SAVE] Asynchronous save thread started")
    
    def _async_save_worker(self):
        """Worker method that runs in the async save thread to handle saving without blocking telemetry."""
        logger.info("🧵 [ASYNC SAVE] Worker thread started")
        
        while self._async_save_running:
            try:
                # Wait for lap data with timeout
                lap_data_dict = self._async_save_queue.get(timeout=1.0)
                
                if lap_data_dict is None:  # Shutdown signal
                    break
                
                sdk_lap_number = lap_data_dict.get("lap_number_sdk")
                logger.info(f"🧵 [ASYNC SAVE] Processing lap {sdk_lap_number} asynchronously")
                
                start_time = time.time()
                
                # Call the actual save method (this can take several seconds)
                saved_lap_id = self.save_lap_directly(lap_data_dict)
                
                end_time = time.time()
                save_duration = end_time - start_time
                
                # Mark as processed based on result
                success = (saved_lap_id is not None)
                self._mark_lap_as_processed(sdk_lap_number, success=success)
                
                if success:
                    logger.info(f"🧵 [ASYNC SAVE] Successfully saved lap {sdk_lap_number} in {save_duration:.2f}s (async)")
                else:
                    logger.error(f"🧵 [ASYNC SAVE] Failed to save lap {sdk_lap_number} after {save_duration:.2f}s (async)")
                
                self._async_save_queue.task_done()
                
            except queue.Empty:
                continue  # Timeout - keep running
            except Exception as e:
                logger.error(f"🧵 [ASYNC SAVE] Error in async save worker: {e}", exc_info=True)
                # Continue running even if there's an error
        
        logger.info("🧵 [ASYNC SAVE] Worker thread exiting")
    
    def save_lap_async(self, lap_data_dict):
        """Queue a lap for asynchronous saving without blocking the telemetry thread.
        
        Args:
            lap_data_dict: Dictionary containing lap data to save
        """
        if not hasattr(self, '_async_save_running') or not self._async_save_running:
            logger.warning("🧵 [ASYNC SAVE] Async save system not running, falling back to direct save")
            return self.save_lap_directly(lap_data_dict)
        
        sdk_lap_number = lap_data_dict.get("lap_number_sdk")
        
        try:
            # Queue the lap for async processing - this is non-blocking
            self._async_save_queue.put(lap_data_dict, block=False)
            logger.info(f"🧵 [ASYNC SAVE] Queued lap {sdk_lap_number} for asynchronous processing (queue size: {self._async_save_queue.qsize()})")
            
            # Check queue health
            queue_size = self._async_save_queue.qsize()
            if queue_size > 10:
                logger.warning(f"🧵 [ASYNC SAVE] Queue size is high ({queue_size}), async save may be falling behind")
            
        except queue.Full:
            logger.error(f"🧵 [ASYNC SAVE] Queue is full, falling back to direct save for lap {sdk_lap_number}")
            return self.save_lap_directly(lap_data_dict)
        except Exception as e:
            logger.error(f"🧵 [ASYNC SAVE] Error queuing lap {sdk_lap_number}: {e}")
            return self.save_lap_directly(lap_data_dict)