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

# Import PyQt for signals
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

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
            lap_data = None
            try:
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

        # IMMEDIATE SAVING INTEGRATION - Always enabled
        self._immediate_saves_processed = 0
        self._immediate_saves_successful = 0
        
        # Set up immediate save callback
        self.lap_indexer.set_immediate_save_callback(self._immediate_save_callback)
        self.lap_indexer.start_save_worker()
        
        # CRITICAL FIX: Buffer for completed sector data to handle timing delays
        self._sector_data_buffer = {}  # lap_number -> sector_data
        self._max_buffer_size = 10  # Keep last 10 laps of sector data
        
        # AUTO-START TRACK BUILDING: Initialize track building when laps are detected
        self._track_builder_manager = None
        self._track_building_enabled = False
        self._auto_start_attempted = False
        
        logger.info("🔌 IRacingLapSaver ready with immediate saving enabled")
        logger.info("✅ Immediate save callback registered")
        logger.info("✅ Immediate save worker thread started")
        
    def _auto_start_track_building(self):
        """Auto-start track building when first valid lap is detected."""
        if self._auto_start_attempted or not self._track_building_enabled:
            return
            
        try:
            self._auto_start_attempted = True
            logger.info("🗺️ [AUTO TRACK BUILD] First valid lap detected - auto-starting track building...")
            
            # Import the track building system
            from .integrated_track_builder import IntegratedTrackBuilderManager
            
            # Get the global iRacing connection
            simple_iracing_api = None
            if hasattr(self, 'simple_iracing_api'):
                simple_iracing_api = self.simple_iracing_api
            elif hasattr(self.lap_indexer, 'simple_iracing_api'):
                simple_iracing_api = self.lap_indexer.simple_iracing_api
            
            # Create and start the track builder manager
            self._track_builder_manager = IntegratedTrackBuilderManager(simple_iracing_api)
            
            # Connect signals for logging (if PyQt is available)
            if PYQT_AVAILABLE:
                self._track_builder_manager.status_update.connect(self._on_track_builder_status)
                self._track_builder_manager.progress_update.connect(self._on_track_builder_progress)
                self._track_builder_manager.completion_ready.connect(self._on_track_builder_complete)
            
            # Start the track building
            self._track_builder_manager.start_building()
            
            logger.info("✅ [AUTO TRACK BUILD] Track building system started successfully!")
            
        except Exception as e:
            logger.error(f"❌ [AUTO TRACK BUILD] Failed to start track building: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_track_builder_status(self, status):
        """Handle track builder status updates."""
        logger.info(f"🗺️ [TRACK BUILD] {status}")
    
    def _on_track_builder_progress(self, status, progress):
        """Handle track builder progress updates."""
        logger.info(f"🗺️ [TRACK BUILD] {status} (Progress: {progress})")
    
    def _on_track_builder_complete(self, centerline, corners):
        """Handle track builder completion."""
        logger.info(f"✅ [TRACK BUILD] Track map completed! {len(centerline)} centerline points, {len(corners)} corners")
    
    def enable_auto_track_building(self):
        """Enable automatic track building when laps are detected."""
        self._track_building_enabled = True
        logger.info("✅ [AUTO TRACK BUILD] Auto track building enabled")
    
    def set_simple_iracing_api(self, simple_iracing_api):
        """Set the SimpleIRacingAPI instance for track building."""
        self.simple_iracing_api = simple_iracing_api
        logger.info("✅ [AUTO TRACK BUILD] SimpleIRacingAPI reference set for track building")
        logger.info("🎯 IMMEDIATE SAVING ACTIVATED - Zero lag lap saving enabled!")

    # Immediate saving is now always enabled by default - no need for separate enable method

    def _test_immediate_save_system(self):
        """Test that the immediate save system is properly configured."""
        try:
            # Check if callback is properly set
            if hasattr(self.lap_indexer, '_save_callback') and self.lap_indexer._save_callback:
                logger.info("✅ Immediate save callback is properly registered")
            else:
                logger.error("❌ Immediate save callback is NOT registered!")
                
            # Check if worker is running
            if hasattr(self.lap_indexer, '_save_worker_running') and self.lap_indexer._save_worker_running:
                logger.info("✅ Immediate save worker thread is running")
            else:
                logger.error("❌ Immediate save worker thread is NOT running!")
                
            # Check if we have a session for saving
            if self._current_session_id:
                logger.info(f"✅ Active session ready for lap saving: {self._current_session_id}")
            else:
                logger.warning("⚠️  No active session - laps will queue until session is created")
                
        except Exception as e:
            logger.error(f"❌ Error testing immediate save system: {e}")

    def _immediate_save_callback(self, lap_data):
        """
        Immediate callback triggered when a lap completes.
        
        This callback is triggered by the LapIndexer immediately when a lap finishes,
        eliminating the polling delay that caused synchronization issues.
        
        Args:
            lap_data: Complete lap dictionary from LapIndexer
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            self._immediate_saves_processed += 1
            
            # Extract key information
            lap_number = lap_data.get("lap_number_sdk", -1)
            lap_time = lap_data.get("duration_seconds", 0.0)
            lap_state = lap_data.get("lap_state", "UNKNOWN")
            frame_count = len(lap_data.get("telemetry_frames", []))
            was_reset = lap_data.get("was_reset_to_pits", False)
            
            # DIAGNOSTIC: Always log lap detection
            print(f"🏁 [LAP DETECTED] Lap {lap_number} completed! State: {lap_state}, Time: {lap_time:.3f}s, Frames: {frame_count}")
            if was_reset:
                print(f"⚠️ [LAP DETECTED] Lap {lap_number} was interrupted by reset to pits")
            
            if was_reset:
                logger.warning(f"⚡ IMMEDIATE SAVE (RESET): Lap {lap_number} ({lap_state}) - {lap_time:.3f}s, {frame_count} frames - INTERRUPTED BY RESET")
            else:
                logger.info(f"⚡ IMMEDIATE SAVE TRIGGERED: Lap {lap_number} ({lap_state}) - {lap_time:.3f}s, {frame_count} frames")
            
            # Validate that we have essential data
            if lap_number < 0:
                print(f"❌ [LAP DETECTED] Invalid lap number {lap_number} - skipping")
                logger.error(f"❌ IMMEDIATE SAVE SKIPPED: Invalid lap number {lap_number}")
                return False
                
            if frame_count == 0:
                print(f"⚠️ [LAP DETECTED] Lap {lap_number} has no telemetry frames!")
                logger.warning(f"⚠️  IMMEDIATE SAVE WARNING: Lap {lap_number} has no telemetry frames")
            
            # DIAGNOSTIC: Check session state
            print(f"🔧 [LAP DETECTED] Session check - Current session ID: {self._current_session_id}")
            print(f"🔧 [LAP DETECTED] Session check - Track ID: {self._current_track_id}, Car ID: {self._current_car_id}")
            
            # Ensure session is set up
            if not self._current_session_id:
                print(f"❌ [LAP DETECTED] No active session for lap {lap_number} - will queue for later")
                logger.warning(f"⚠️  IMMEDIATE SAVE QUEUED: No active session for lap {lap_number} - will save when session is created")
                # Store for later processing when session becomes available
                if not hasattr(self, '_queued_immediate_laps'):
                    self._queued_immediate_laps = []
                self._queued_immediate_laps.append(lap_data)
                return False  # Return False since we couldn't save now
                
            # DIAGNOSTIC: Confirm we're about to save
            print(f"✅ [LAP DETECTED] About to save lap {lap_number} to session {self._current_session_id}")
            
            # Use existing validation and save logic
            if was_reset:
                logger.warning(f"💾 IMMEDIATE SAVE PROCESSING (RESET): Lap {lap_number} with session {self._current_session_id}")
            else:
                logger.info(f"💾 IMMEDIATE SAVE PROCESSING: Lap {lap_number} with session {self._current_session_id}")
            success = self._process_immediate_lap(lap_data)
            
            if success:
                self._immediate_saves_successful += 1
                if was_reset:
                    logger.warning(f"✅ IMMEDIATE SAVE SUCCESS (RESET): Lap {lap_number} saved to Supabase")
                else:
                    logger.info(f"✅ IMMEDIATE SAVE SUCCESS: Lap {lap_number} saved to Supabase")
                # Trigger gamification updates in background (non-blocking)
                try:
                    threading.Thread(target=self._handle_post_lap_gamification, args=(lap_data,), daemon=True).start()
                except Exception as _e:
                    logger.debug(f"Gamification post-lap hook failed to start: {_e}")
            else:
                logger.error(f"❌ IMMEDIATE SAVE FAILED: Lap {lap_number} could not be saved")
                
            # Log statistics periodically
            if self._immediate_saves_processed % 5 == 0:
                success_rate = (self._immediate_saves_successful / self._immediate_saves_processed) * 100
                logger.info(f"📊 IMMEDIATE SAVE STATS: {self._immediate_saves_successful}/{self._immediate_saves_processed} successful ({success_rate:.1f}%)")
                
            return success  # CRITICAL FIX: Return the actual success status
                
        except Exception as e:
            logger.error(f"💥 IMMEDIATE SAVE ERROR: {e}", exc_info=True)
            return False  # Return False on exception

    def _handle_post_lap_gamification(self, lap_data):
        """Award base XP and Race Pass XP after a lap is saved. Non-blocking background hook."""
        try:
            base_xp = 50
            race_pass_xp = 50
            try:
                from future.gamification.trackpro_gamification.supabase_gamification import award_xp as rpc_award_xp
                ok, _ = rpc_award_xp(base_xp, race_pass_xp)
                if not ok:
                    logger.debug("Post-lap XP award RPC returned unsuccessful status")
            except Exception as e:
                logger.debug(f"Post-lap XP award failed: {e}")
        except Exception as e:
            logger.debug(f"Gamification post-lap hook error: {e}")

    def _process_immediate_lap(self, lap_data):
        """
        Process an immediately saved lap using existing infrastructure.
        
        Args:
            lap_data: Complete lap data from LapIndexer
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract data
            lap_number = lap_data["lap_number_sdk"]
            lap_time = lap_data["duration_seconds"]
            lap_frames = lap_data["telemetry_frames"]
            lap_state = lap_data.get("lap_state", "TIMED")
            is_valid_for_leaderboard = lap_data.get("is_valid_for_leaderboard", False)
            
            # Mark as processed to avoid duplicates
            with self._processing_lock:
                if lap_number in self._processed_lap_indexer_lap_numbers:
                    logger.warning(f"Lap {lap_number} already processed, skipping")
                    return True
                self._processed_lap_indexer_lap_numbers.add(lap_number)
                self._pending_lap_numbers.discard(lap_number)
            
            # CRITICAL FIX: Check if sector data is already in the frames (from our enhanced integration)
            sector_times = None
            sector_data_found_in_frames = False
            
            # 🔧 CRITICAL COORDINATION FIX: First check if LapIndexer already found sector data
            if "sector_times" in lap_data and lap_data.get("has_sector_data", False):
                sector_times = lap_data["sector_times"]
                sector_data_found_in_frames = True
                logger.info(f"✅ [COORDINATION] Using sector data from LapIndexer for lap {lap_number}: {sector_times}")
            else:
                # Fallback: Search frames for sector data (legacy approach)
                logger.debug(f"[SECTOR] Checking {len(lap_frames)} frames for sector data")
                
                # CRITICAL FIX: Exhaustive search for complete sector data with multiple passes
                # Pass 1: Look for COMPLETE sector data (10 sectors) with highest priority
                # But prioritize frames that match the current lap to avoid cross-lap contamination
                best_sector_data = None
                best_frame_index = -1
                
                for i in reversed(range(len(lap_frames))):
                    frame = lap_frames[i]
                    if isinstance(frame, dict):
                        # PRIORITY 1: Complete sector_times array with exactly 10 sectors
                        if 'sector_times' in frame and frame['sector_times'] and len(frame['sector_times']) == 10:
                            frame_lap = frame.get('Lap', 0)
                            source_lap = frame.get('_source_lap', frame_lap)
                            
                            # Prefer sector data that matches this lap number
                            if source_lap == lap_number or frame_lap == lap_number:
                                sector_times = frame['sector_times']
                                sector_data_found_in_frames = True
                                logger.info(f"✅ [SECTOR FIX] Found MATCHING lap {lap_number} sector data (10 sectors) in frame {i}: {sector_times}")
                                break
                            elif best_sector_data is None:
                                # Store as fallback but keep looking for exact match
                                best_sector_data = frame['sector_times']
                                best_frame_index = i
                        
                        # PRIORITY 2: Complete individual sector fields (all 10 sectors present)
                        elif all(f'sector{j+1}_time' in frame for j in range(10)):
                            individual_sectors = [frame.get(f'sector{j+1}_time') for j in range(10)]
                            if all(s is not None for s in individual_sectors):
                                sector_times = individual_sectors
                                sector_data_found_in_frames = True
                                logger.info(f"✅ [SECTOR FIX] Found COMPLETE individual sector fields (10 sectors) in frame {i} for lap {lap_number}: {sector_times}")
                                break
            
            # If we didn't find an exact match, use the best fallback
            if not sector_data_found_in_frames and best_sector_data is not None:
                sector_times = best_sector_data
                sector_data_found_in_frames = True
                logger.warning(f"⚠️ [SECTOR FIX] Using fallback sector data (10 sectors) from frame {best_frame_index} for lap {lap_number}: {sector_times}")
                logger.warning(f"⚠️ [SECTOR WARNING] This may indicate cross-lap contamination - sector data might be from wrong lap")
            
            # Pass 2: If no complete data found, look for near-complete data (9+ sectors)
            if not sector_data_found_in_frames:
                for i in reversed(range(len(lap_frames))):
                    frame = lap_frames[i]
                    if isinstance(frame, dict):
                        # Near-complete sector_times array (9+ sectors)
                        if 'sector_times' in frame and frame['sector_times'] and len(frame['sector_times']) >= 9:
                            sector_times = frame['sector_times']
                            sector_data_found_in_frames = True
                            logger.info(f"✅ [SECTOR FIX] Found NEAR-COMPLETE sector data array ({len(sector_times)} sectors) in frame {i} for lap {lap_number}: {sector_times}")
                            break
                        
                        # Near-complete individual sector fields (9+ sectors)
                        elif any(key.startswith('sector') and key.endswith('_time') for key in frame.keys()):
                            individual_sectors = [frame.get(f'sector{j+1}_time') for j in range(10)]
                            non_none_sectors = [s for s in individual_sectors if s is not None]
                            if len(non_none_sectors) >= 9:
                                sector_times = non_none_sectors
                                sector_data_found_in_frames = True
                                logger.info(f"✅ [SECTOR FIX] Found NEAR-COMPLETE individual sector fields ({len(non_none_sectors)} sectors) in frame {i} for lap {lap_number}: {sector_times}")
                                break
            
            # Pass 3: If still no data found, look for partial data (3+ sectors) as last resort
            if not sector_data_found_in_frames:
                for i in reversed(range(len(lap_frames))):
                    frame = lap_frames[i]
                    if isinstance(frame, dict):
                        # Partial sector_times array (3+ sectors)
                        if 'sector_times' in frame and frame['sector_times'] and len(frame['sector_times']) >= 3:
                            sector_times = frame['sector_times']
                            sector_data_found_in_frames = True
                            logger.info(f"✅ [SECTOR FIX] Found PARTIAL sector data array ({len(sector_times)} sectors) in frame {i} for lap {lap_number}: {sector_times}")
                            break
                        
                        # Partial individual sector fields (3+ sectors)
                        elif any(key.startswith('sector') and key.endswith('_time') for key in frame.keys()):
                            individual_sectors = [frame.get(f'sector{j+1}_time') for j in range(10)]
                            non_none_sectors = [s for s in individual_sectors if s is not None]
                            if len(non_none_sectors) >= 3:
                                sector_times = non_none_sectors
                                sector_data_found_in_frames = True
                                logger.info(f"✅ [SECTOR FIX] Found PARTIAL individual sector fields ({len(non_none_sectors)} sectors) in frame {i} for lap {lap_number}: {sector_times}")
                                break

            # FALLBACK: Check for current lap sector progress (only if no completed data found)
            if not sector_data_found_in_frames:
                logger.info(f"🔧 [SECTOR DEBUG] No completed sector data found, checking progress data...")
                
                # Check frames in reverse order for the most recent progress
                for i in reversed(range(len(lap_frames))):
                    frame = lap_frames[i]
                    if (isinstance(frame, dict) and 
                        'current_lap_sector_times' in frame and 
                        frame.get('sector_timing_initialized', False) and
                        frame.get('current_lap_sector_times')):
                        
                        current_lap_splits = frame.get('current_lap_sector_times', [])
                        current_sector_time = frame.get('current_sector_time', 0.0)
                        total_sectors = frame.get('total_sectors', 0)
                        
                        logger.info(f"🔧 [SECTOR DEBUG] Frame {i} progress: {len(current_lap_splits)}/{total_sectors} sectors, current: {current_sector_time:.3f}s")
                        
                        # Reconstruct sector times from progress data
                        if len(current_lap_splits) == total_sectors:
                            # Complete lap
                            sector_times = current_lap_splits
                            sector_data_found_in_frames = True
                            logger.info(f"✅ [SECTOR FIX] Reconstructed complete sector data from progress in frame {i} for lap {lap_number}: {sector_times}")
                            break
                        elif len(current_lap_splits) >= 8 and current_sector_time > 0.1:
                            # Near-complete lap with current sector time
                            sector_times = current_lap_splits + [current_sector_time]
                            sector_data_found_in_frames = True
                            logger.info(f"✅ [SECTOR FIX] Reconstructed near-complete sector data from progress in frame {i} for lap {lap_number}: {sector_times}")
                            break
                        elif len(current_lap_splits) >= 3:
                            # Partial lap with multiple sectors
                            sector_times = current_lap_splits
                            sector_data_found_in_frames = True
                            logger.info(f"✅ [SECTOR FIX] Using partial sector progress from frame {i} for lap {lap_number}: {sector_times}")
                            break
            
            # CRITICAL FIX: Get sector data directly by lap number from the API
            if not sector_data_found_in_frames:
                logger.info(f"🔍 [LAP SECTOR] Checking for lap-specific sector data for lap {lap_number}")
                
                # Get sector data from the iRacing API using lap number
                if hasattr(self, '_iracing_api') and self._iracing_api:
                    lap_sector_data = self._iracing_api.get_lap_sector_data(lap_number)
                    if lap_sector_data and 'sector_times' in lap_sector_data:
                        sector_times = lap_sector_data['sector_times']
                        logger.info(f"✅ [LAP SECTOR] Found exact sector data for lap {lap_number}: {sector_times}")
                    else:
                        logger.warning(f"❌ [LAP SECTOR] No exact sector data found for lap {lap_number}")
                else:
                    logger.warning(f"❌ [LAP SECTOR] No iRacing API reference available")
                    
                # Fallback to buffered data if API doesn't have it
                if not sector_times:
                    logger.info(f"🔍 [BACKFILL] Checking buffered sector data for lap {lap_number}")
                    buffered_data = self._get_buffered_sector_data(lap_number)
                    if buffered_data:
                        buffered_sector_times = buffered_data.get('sector_times', [])
                        if buffered_sector_times:
                            sector_times = buffered_sector_times
                            logger.info(f"✅ [BACKFILL] Using buffered sector data for lap {lap_number}: {sector_times}")
                        else:
                            logger.warning(f"❌ [BACKFILL] Buffered data found but no sector_times for lap {lap_number}")
                    else:
                        logger.info(f"❌ [BACKFILL] No buffered sector data found for lap {lap_number}")

            # Fallback: Try to get sector data from timing system if not found in frames, API, or buffer
            # Debug: If no sector data found, log what's in the frames  
            if not sector_times:
                logger.warning(f"❌ [SECTOR DEBUG] No sector data found in frames or buffer for lap {lap_number}")
                # Log sample frame keys for debugging
                if lap_frames:
                    sample_frame = lap_frames[-1] if isinstance(lap_frames[-1], dict) else {}
                    sector_keys = [k for k in sample_frame.keys() if 'sector' in k.lower()]
                    timing_keys = [k for k in sample_frame.keys() if 'timing' in k.lower()]
                    logger.warning(f"🔍 [SECTOR DEBUG] Sample frame sector keys: {sector_keys}")
                    logger.warning(f"🔍 [SECTOR DEBUG] Sample frame timing keys: {timing_keys}")
                    logger.warning(f"🔍 [SECTOR DEBUG] Sample frame has sector_timing_initialized: {sample_frame.get('sector_timing_initialized', False)}")
            
            if not sector_times and hasattr(self, '_sector_timing_system') and self._sector_timing_system:
                try:
                    # Get the most recent completed lap from the sector timing system
                    recent_laps = self._sector_timing_system.get_recent_laps(1)
                    if recent_laps:
                        latest_lap = recent_laps[-1]
                        
                        # Handle both dictionary and object formats
                        if isinstance(latest_lap, dict):
                            # Dictionary format from SimpleSectorTimingIntegration
                            lap_sector_times = latest_lap.get('sector_times', [])
                            is_complete = latest_lap.get('is_complete', False)
                            lap_number_from_timing = latest_lap.get('lap_number', 0)
                        else:
                            # Object format (legacy support)
                            lap_sector_times = getattr(latest_lap, 'sector_times', [])
                            is_complete = getattr(latest_lap, 'is_valid', False)
                            lap_number_from_timing = getattr(latest_lap, 'lap_number', 0)
                        
                        if lap_sector_times and is_complete and lap_number_from_timing == lap_number:
                            sector_times = lap_sector_times
                            logger.info(f"🔧 [SECTOR FALLBACK] Retrieved sector data from timing system for lap {lap_number}: {sector_times}")
                        else:
                            logger.warning(f"🔧 [SECTOR FALLBACK] Latest lap from timing system doesn't match (lap {lap_number_from_timing} vs {lap_number}) or invalid (complete: {is_complete})")
                    else:
                        logger.warning(f"🔧 [SECTOR FALLBACK] No recent laps available from timing system")
                except Exception as e:
                    logger.error(f"🔧 [SECTOR FALLBACK] Error getting sector data: {e}")
            
            # Add lap state and sector data to all frames for validation
            updated_frames = []
            for frame in lap_frames:
                frame_copy = dict(frame)
                frame_copy["lap_state"] = lap_state
                frame_copy["is_valid_for_leaderboard"] = is_valid_for_leaderboard
                
                # CRITICAL FIX: Add sector data to ALL frames if available
                if sector_times:
                    frame_copy["sector_times"] = sector_times
                    frame_copy["sector_total_time"] = sum(sector_times)
                    # Removed individual frame logging to reduce spam
                
                updated_frames.append(frame_copy)
            
            if sector_times:
                source = "frames" if sector_data_found_in_frames else "timing system fallback"
                logger.info(f"✅ [SECTOR FIX] Added sector data from {source} to all {len(updated_frames)} frames for lap {lap_number}: {sector_times}")
            else:
                logger.warning(f"❌ [SECTOR FIX] No sector data available for lap {lap_number} - frames and fallback both failed")
            
            # Use existing save method
            saved_lap_id = self._save_lap_data(lap_number, lap_time, updated_frames)
            
            if saved_lap_id:
                # Update statistics
                self._total_laps_saved += 1
                self._mark_lap_as_processed(lap_number, success=True)
                
                # AUTO-START TRACK BUILDING: Start track building when first valid lap is detected
                if lap_state == "TIMED" and is_valid_for_leaderboard:
                    self._auto_start_track_building()
                
                return True
            else:
                self._mark_lap_as_processed(lap_number, success=False)
                return False
                
        except Exception as e:
            logger.error(f"Error processing immediate lap {lap_data.get('lap_number_sdk', 'unknown')}: {e}")
            return False

    def get_immediate_saving_stats(self):
        """
        Get immediate saving statistics for performance monitoring.
        
        Returns:
            Dictionary with immediate saving performance data
        """
        success_rate = 0
        if self._immediate_saves_processed > 0:
            success_rate = (self._immediate_saves_successful / self._immediate_saves_processed) * 100
            
        # Check worker status
        worker_running = False
        queue_size = 0
        if hasattr(self.lap_indexer, '_save_worker_running'):
            worker_running = self.lap_indexer._save_worker_running
        if hasattr(self.lap_indexer, '_immediate_save_queue'):
            queue_size = self.lap_indexer._immediate_save_queue.qsize()
            
        # Check for queued laps waiting for session
        queued_laps = 0
        if hasattr(self, '_queued_immediate_laps'):
            queued_laps = len(self._queued_immediate_laps)
            
        stats = {
            "enabled": True,  # Always enabled now
            "processed": self._immediate_saves_processed,
            "successful": self._immediate_saves_successful,
            "failed": self._immediate_saves_processed - self._immediate_saves_successful,
            "success_rate": success_rate,
            "worker_running": worker_running,
            "queue_size": queue_size,
            "queued_for_session": queued_laps,
            "current_session": self._current_session_id,
            "callback_registered": hasattr(self.lap_indexer, '_save_callback') and self.lap_indexer._save_callback is not None
        }
        
        return stats

    def _process_queued_immediate_laps(self):
        """Process any laps that were queued while waiting for a session to be created."""
        if not hasattr(self, '_queued_immediate_laps') or not self._queued_immediate_laps:
            return
            
        if not self._current_session_id:
            logger.warning("Cannot process queued laps - no active session")
            return
            
        logger.info(f"🔄 PROCESSING {len(self._queued_immediate_laps)} QUEUED IMMEDIATE LAPS")
        
        processed = 0
        failed = 0
        
        for lap_data in self._queued_immediate_laps:
            try:
                lap_number = lap_data.get("lap_number_sdk", -1)
                logger.info(f"💾 Processing queued lap {lap_number}")
                
                success = self._process_immediate_lap(lap_data)
                if success:
                    processed += 1
                    logger.info(f"✅ Queued lap {lap_number} processed successfully")
                else:
                    failed += 1
                    logger.error(f"❌ Failed to process queued lap {lap_number}")
                    
            except Exception as e:
                failed += 1
                lap_number = lap_data.get("lap_number_sdk", "unknown")
                logger.error(f"❌ Error processing queued lap {lap_number}: {e}")
        
        # Clear the queue
        self._queued_immediate_laps = []
        
        logger.info(f"🔄 QUEUED LAP PROCESSING COMPLETE: {processed} successful, {failed} failed")
        
    def debug_immediate_save_system(self):
        """Debug method to check the status of the immediate save system."""
        logger.info("🔍 DEBUGGING IMMEDIATE SAVE SYSTEM")
        
        # Immediate saving is always enabled now
        logger.info("Immediate saving enabled: True (always enabled)")
        
        # Check LapIndexer status
        if hasattr(self, 'lap_indexer') and self.lap_indexer:
            logger.info("✅ LapIndexer exists")
            
            # Check callback registration
            if hasattr(self.lap_indexer, '_save_callback'):
                if self.lap_indexer._save_callback:
                    logger.info("✅ Immediate save callback is registered")
                else:
                    logger.error("❌ Immediate save callback is None")
            else:
                logger.error("❌ LapIndexer has no _save_callback attribute")
            
            # Check worker thread
            if hasattr(self.lap_indexer, '_save_worker_running'):
                if self.lap_indexer._save_worker_running:
                    logger.info("✅ Save worker thread is running")
                else:
                    logger.error("❌ Save worker thread is NOT running")
            else:
                logger.error("❌ LapIndexer has no _save_worker_running attribute")
                
            # Check queue
            if hasattr(self.lap_indexer, '_immediate_save_queue'):
                queue_size = self.lap_indexer._immediate_save_queue.qsize()
                logger.info(f"📊 Immediate save queue size: {queue_size}")
            else:
                logger.error("❌ LapIndexer has no _immediate_save_queue attribute")
                
        else:
            logger.error("❌ LapIndexer is None or missing")
        
        # Check session status
        if self._current_session_id:
            logger.info(f"✅ Active session: {self._current_session_id}")
        else:
            logger.warning("⚠️  No active session")
            
        # Check statistics
        stats = self.get_immediate_saving_stats()
        logger.info(f"📊 Immediate save statistics: {stats}")
        
        # Check for common issues
        if hasattr(self, 'lap_indexer') and self.lap_indexer:
            if not hasattr(self.lap_indexer, '_save_callback') or not self.lap_indexer._save_callback:
                logger.error("🚨 ISSUE: Immediate save callback is not registered!")
                logger.info("💡 SOLUTION: Restart the application - callback should auto-register")
                
            if hasattr(self.lap_indexer, '_save_worker_running') and not self.lap_indexer._save_worker_running:
                logger.error("🚨 ISSUE: Save worker thread is not running!")
                logger.info("💡 SOLUTION: Restart the application - worker should auto-start")
        
        return stats

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
            Telemetry data (unchanged)
        """
        # Check session state changes first
        self._process_session_state(telemetry_data)
        
        # Increment debug counter
        self._telemetry_debug_counter += 1
        
        # DIAGNOSTIC: Log telemetry reception every 18000 frames (5 minutes at 60Hz)
        if self._telemetry_debug_counter % 18000 == 0:
            lap_number = telemetry_data.get('Lap', 0)
            lap_dist_pct = telemetry_data.get('LapDistPct', -1)
            speed = telemetry_data.get('Speed', 0)
            print(f"🔧 [TELEMETRY DIAGNOSTIC] Frame {self._telemetry_debug_counter}: Lap={lap_number}, LapDistPct={lap_dist_pct:.3f}, Speed={speed:.1f}")
            print(f"🔧 [TELEMETRY DIAGNOSTIC] Session ID: {self._current_session_id}")
            print(f"🔧 [TELEMETRY DIAGNOSTIC] Track ID: {self._current_track_id}, Car ID: {self._current_car_id}")
        
        # Ensure we have a session ID from the monitor
        if not self._current_session_id:
            # Log periodically if no session is active
            if self._telemetry_debug_counter % 18000 == 0:
                print(f"❌ [TELEMETRY DIAGNOSTIC] Cannot process telemetry: No active session set by monitor.")
                print(f"❌ [TELEMETRY DIAGNOSTIC] Session state: session_id={self._current_session_id}, track_id={self._current_track_id}, car_id={self._current_car_id}")
            return telemetry_data

        # DIAGNOSTIC: Confirm telemetry processing is active
        if self._telemetry_debug_counter % 36000 == 0:  # Every 10 minutes
            print(f"✅ [TELEMETRY DIAGNOSTIC] Processing telemetry with valid session {self._current_session_id}")

        # --- Enhanced Lap Detection Logic ---
        try:
            # CLEAN: Always feed telemetry to LapIndexer for immediate lap saving
            # The LapIndexer detects lap completions and triggers immediate save callbacks
            self.lap_indexer.on_frame(telemetry_data)
            
            # CLEAN: Simple debug logging (reduced frequency)
            if self._telemetry_debug_counter % 7200 == 0:  # Every 2 minutes at 60Hz
                iracing_current_lap = telemetry_data.get('Lap', 0)
                iracing_completed_lap = telemetry_data.get('LapCompleted', 0)
                lap_dist_pct = telemetry_data.get('LapDistPct', -1)
                session_time = telemetry_data.get('SessionTimeSecs', 0)
                
                # Get current lap from LapIndexer (authoritative source)
                lap_indexer_current = getattr(self.lap_indexer, '_active_lap_number_internal', 'N/A')
                print(f"🔧 LAP SYNC (2min): LapDistPct={lap_dist_pct:.3f}, " +
                           f"iRacing Current={iracing_current_lap}, iRacing Completed={iracing_completed_lap}, " + 
                           f"LapIndexer Current={lap_indexer_current}, SessionTime={session_time:.3f}")

        except Exception as e:
            print(f"❌ [TELEMETRY DIAGNOSTIC] Error processing telemetry: {e}")
            import traceback
            traceback.print_exc()

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
        # Enhanced logging - record validation start - REDUCED TO DEBUG
        logger.debug(f"[LAP VALIDATION] Starting validation for lap {lap_number_for_validation} with {len(lap_frames)} points")
        
        # Check for validation override flag (used for final lap)
        if hasattr(self, '_override_validation') and self._override_validation:
            coverage = self._calculate_track_coverage(lap_frames)
            point_count = len(lap_frames)
            self._debug_lap_validation(True, f"Validation overridden for lap with {point_count} points, {coverage:.2f} coverage")
            return True
            
        # Defensive check
        if not lap_frames or len(lap_frames) == 0:
            self._debug_lap_validation(False, "No telemetry points to validate")
            return False
        
        # Check number of data points
        lap_state_from_indexer = "TIMED" # Default if not found
        was_reset_to_pits = False

        if lap_frames and len(lap_frames) > 0:
            # LapIndexer should have added 'lap_state' to frames in our wrapper code
            first_frame = lap_frames[0]
            lap_state_from_indexer = first_frame.get("lap_state", "TIMED")
            was_reset_to_pits = first_frame.get("was_reset_to_pits", False)
            is_complete_by_sdk = first_frame.get("is_complete_by_sdk_increment", True)

        # For normal racing timed laps, require more points
        min_points_threshold = 5
        if lap_state_from_indexer == "TIMED":
            min_points_threshold = 20
        elif lap_state_from_indexer in ["OUT", "IN"]:
            min_points_threshold = 10  # More lenient for OUT/IN laps
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} is {lap_state_from_indexer}. Using min points threshold: {min_points_threshold}")
        elif lap_state_from_indexer == "INCOMPLETE":
            if was_reset_to_pits:
                min_points_threshold = 5  # Very lenient for reset laps
                logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} is INCOMPLETE due to reset to pits. Using min points threshold: {min_points_threshold}")
            else:
                min_points_threshold = 10  # Slightly more lenient for incomplete laps
                logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} is INCOMPLETE. Using min points threshold: {min_points_threshold}")

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
        if was_reset_to_pits:
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} classified by LapIndexer as: {lap_state_from_indexer} (RESET TO PITS)")
        else:
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} classified by LapIndexer as: {lap_state_from_indexer}")
        
        # Adjust coverage threshold based on lap type
        effective_threshold = 0.5
        if lap_state_from_indexer == "OUT":
            effective_threshold = 0.35
            logger.info(f"[LAP VALIDATION] Using reduced coverage threshold of {effective_threshold} for OUT lap {lap_number_for_validation}")
        elif lap_state_from_indexer == "IN":
            effective_threshold = 0.35
            logger.info(f"[LAP VALIDATION] Using reduced coverage threshold of {effective_threshold} for IN lap {lap_number_for_validation}")
        elif lap_state_from_indexer == "INCOMPLETE":
            if was_reset_to_pits:
                effective_threshold = 0.05  # Very lenient for reset laps - just need some data
                logger.warning(f"[LAP VALIDATION] Using very reduced coverage threshold of {effective_threshold} for RESET INCOMPLETE lap {lap_number_for_validation}")
            else:
                effective_threshold = 0.1  # Lenient for incomplete laps, usually session end
                logger.info(f"[LAP VALIDATION] Using reduced coverage threshold of {effective_threshold} for INCOMPLETE lap {lap_number_for_validation}")

        # Enhanced logging for threshold comparison
        if was_reset_to_pits:
            logger.warning(f"[LAP VALIDATION] RESET LAP {lap_number_for_validation} coverage ({coverage:.2f}) vs. threshold ({effective_threshold}) for type {lap_state_from_indexer}")
        else:
            logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} coverage ({coverage:.2f}) vs. threshold ({effective_threshold}) for type {lap_state_from_indexer}")
            
        if coverage < effective_threshold:
            failure_reason = f"Insufficient track coverage: {coverage:.2f} (threshold: {effective_threshold} for type {lap_state_from_indexer})"
            self._debug_lap_validation(False, failure_reason, len(lap_frames), coverage, lap_number_for_validation)
            if was_reset_to_pits:
                logger.error(f"[LAP VALIDATION] RESET LAP {lap_number_for_validation} failed: {failure_reason}")
            else:
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
        
        # Check for reasonable speed values (more lenient for reset laps)
        speeds = [point.get("speed", point.get("Speed", 0)) for point in lap_frames]
        max_speed = max(speeds) if speeds else 0
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        logger.info(f"[LAP VALIDATION] Lap {lap_number_for_validation} speed stats: max={max_speed:.1f}, avg={avg_speed:.1f}")
        
        # For OUT/IN/INCOMPLETE laps, speed check might not be as critical if they are short or involve pit stops
        # For reset laps, be even more lenient with speed validation
        if lap_state_from_indexer == "TIMED" and not was_reset_to_pits and (not speeds or max_speed <= 0):
            failure_reason = "No valid speed data for TIMED lap"
            self._debug_lap_validation(False, failure_reason, len(lap_frames), coverage, lap_number_for_validation)
            logger.warning(f"[LAP VALIDATION] Lap {lap_number_for_validation} failed: {failure_reason}")
            return False, failure_reason
        
        # Handle special case for laps with pit entry/exit - mark them clearly
        lap_status_message = f"{lap_state_from_indexer} lap"
        if was_reset_to_pits:
            lap_status_message += " (RESET)"
        
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
            
        # CRITICAL FIX: Ensure session exists before saving lap
        if not self._current_session_id:
            logger.error("[CRITICAL] No active session ID, cannot save lap data. Ensure a session is created before saving laps.")
            
            # Log additional debug information about session state
            logger.error(f"[DEBUG] Session state: _current_session_id={self._current_session_id}, _current_car_id={self._current_car_id}, _current_track_id={self._current_track_id}")
            
            # Special case for handling missing session ID
            if not self._current_session_id and not self._connection_disabled:
                logger.warning("[RECOVERY] No session ID but connection is available. This could indicate the session wasn't properly created.")
                
            return None
        
        # Validate that the session exists in the database
        if not self._ensure_session_exists():
            logger.error(f"[CRITICAL] Session {self._current_session_id} does not exist in database and could not be created")
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

        # Check for OUT lap (lap_time = -1) and mark as invalid
        if lap_time == -1:
            is_valid = False
            validation_message += " | OUT lap (lap_time = -1)"
            logger.info(f"Lap {lap_number} marked as invalid: OUT lap detected (lap_time = -1)")

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
                # Check if this is a mid-session join or session reset scenario
                is_mid_session_condition = (
                    ir_completed > 5 or  # Likely joined a session in progress
                    abs(ir_completed - 1 - lap_number) > 3  # Large gap suggests reset/rejoin
                )
                
                if is_mid_session_condition:
                    # This is expected for mid-session joins - log as info, not warning
                    logger.info(f"[LAP SYNC] Mid-session condition detected: saving lap {lap_number}, iRacing LapCompleted={ir_completed} (expected for session joins)")
                else:
                    # Only warn for small mismatches that might indicate a real sync issue
                    logger.warning(f"[LAP SYNC] Potential lap sync issue: saving lap {lap_number} but iRacing LapCompleted={ir_completed} (difference: {abs(ir_completed - 1 - lap_number)})")
        else:
            # Fallback if no frames (should not happen for a processed lap from LapIndexer)
            logger.warning(f"Lap {lap_number} has no telemetry frames for determining lap_type/leaderboard_validity in _save_lap_data. Defaulting type to TIMED, leaderboard to False.")
            is_valid_for_leaderboard = False # Cannot be valid if no frames and validation (is_valid) likely failed

        # Log the determined type and leaderboard status
        logger.info(f"Lap {lap_number} final classification for DB: Type={lap_type}, ValidForLeaderboard={is_valid_for_leaderboard} (Validation result: {is_valid})")

        # 🔧 ENHANCED LAP VALIDATION: Add comprehensive validation checks
        validation_issues = []
        
        # Validate lap time is reasonable
        if lap_time <= 0:
            validation_issues.append(f"Invalid lap time: {lap_time}")
        elif lap_time > 3600:  # More than 1 hour
            validation_issues.append(f"Extremely long lap time: {lap_time}s")
        
        # Validate lap frames exist and have reasonable data
        if not lap_frames_from_indexer:
            validation_issues.append("No telemetry frames available")
        elif len(lap_frames_from_indexer) < 10:
            validation_issues.append(f"Very few telemetry frames: {len(lap_frames_from_indexer)}")
        
        # Validate session context
        if not self._current_session_id:
            validation_issues.append("No active session ID")
        if not self._user_id:
            validation_issues.append("No user ID set")
        
        # Log validation issues but don't necessarily fail the lap
        if validation_issues:
            logger.warning(f"[LAP VALIDATION] Lap {lap_number} has validation issues: {'; '.join(validation_issues)}")
            # Update validation message to include these issues
            if validation_message:
                validation_message += f" | Issues: {'; '.join(validation_issues)}"
            else:
                validation_message = f"Issues: {'; '.join(validation_issues)}"

        # Prepare lap data
        is_personal_best = lap_time < self._best_lap_time
        if is_personal_best and is_valid_for_leaderboard:
            self._best_lap_time = lap_time
        
        # Generate a UUID for the lap to ensure insert-only approach
        lap_uuid = str(uuid.uuid4())
        
        # Check for sector timing data in the lap frames
        sector_times = None
        for frame in lap_frames_from_indexer[::-1]:  # Check frames in reverse order
            if isinstance(frame, dict) and 'sector_times' in frame and frame['sector_times']:
                sector_times = frame['sector_times']
                logger.info(f"✅ [SECTOR INTEGRATION] Found sector data for lap {lap_number}: {sector_times}")
                break
        
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
        
        # Add sector times directly to the lap record if available
        if sector_times:
            for sector_num, sector_time in enumerate(sector_times, 1):
                if sector_num <= 10:  # Only save up to 10 sectors
                    lap_data[f"sector{sector_num}_time"] = sector_time
            logger.info(f"✅ [SECTOR INTEGRATION] Added {len(sector_times)} sector times directly to lap record")
        
        # Make the save attempt
        try:
            print(f"💾 [LAP SAVE] Attempting to save lap {lap_number} to database...")
            print(f"💾 [LAP SAVE] Lap details: Time={lap_time:.3f}s, Type={lap_type}, Session={self._current_session_id}")
            logger.info(f"Saving Lap {lap_number} ({lap_time:.3f}s, Type: {lap_type}) for session {self._current_session_id} with UUID {lap_uuid}")
            
            # Try to insert the lap data
            response = self._supabase_client.table("laps").insert(lap_data).execute()
                
            if response.data and len(response.data) > 0:
                saved_lap_uuid = response.data[0].get('id', lap_uuid)
                print(f"✅ [LAP SAVE] Lap {lap_number} record saved successfully! UUID: {saved_lap_uuid}")
                logger.info(f"Successfully saved lap {lap_number} (UUID: {saved_lap_uuid}, Type: {lap_type}, Valid for Leaderboard: {is_valid_for_leaderboard})")
                    
                # Save associated telemetry points
                if lap_frames_from_indexer:
                    print(f"💾 [LAP SAVE] Now saving telemetry points for lap {lap_number}...")
                    self._save_telemetry_points(saved_lap_uuid, lap_frames_from_indexer)
                
                # Save sector times if available in the lap frames (only if not already included in lap record)
                if not sector_times:
                    self._save_sector_times(saved_lap_uuid, lap_frames_from_indexer)
                else:
                    logger.info(f"✅ [SECTOR INTEGRATION] Sector times already included in lap record, skipping separate sector save")

                self._total_laps_saved += 1
                print(f"✅ [LAP SAVE] Lap {lap_number} completely saved! Total laps saved: {self._total_laps_saved}")
                return saved_lap_uuid
            else:
                print(f"❌ [LAP SAVE] Failed to save lap {lap_number} - no data returned from database")
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
            # 🔧 ENHANCED ERROR HANDLING: Check for specific database constraint violations
            elif "check constraint" in str(e).lower():
                if "check_lap_type" in str(e):
                    logger.error(f"[LAP VALIDATION] Invalid lap_type '{lap_type}' for lap {lap_number}. Must be OUT, TIMED, IN, or INCOMPLETE")
                    # Try to save with corrected lap type
                    corrected_lap_type = "TIMED" if lap_type not in ["OUT", "TIMED", "IN", "INCOMPLETE"] else lap_type
                    if corrected_lap_type != lap_type:
                        logger.info(f"[LAP VALIDATION] Retrying lap {lap_number} save with corrected lap_type: {corrected_lap_type}")
                        lap_data["lap_type"] = corrected_lap_type
                        try:
                            response = self._supabase_client.table("laps").insert(lap_data).execute()
                            if response.data and len(response.data) > 0:
                                saved_lap_uuid = response.data[0].get('id', lap_uuid)
                                logger.info(f"✅ [LAP VALIDATION] Successfully saved lap {lap_number} with corrected lap_type: {corrected_lap_type}")
                                return saved_lap_uuid
                        except Exception as retry_e:
                            logger.error(f"[LAP VALIDATION] Retry with corrected lap_type also failed: {retry_e}")
                else:
                    logger.error(f"[LAP VALIDATION] Database constraint violation for lap {lap_number}: {e}")
            elif "connection" in str(e).lower() or "timeout" in str(e).lower():
                logger.error(f"[DATABASE] Connection/timeout error saving lap {lap_number}: {e}")
                # Record for potential retry later
                self._lap_recording_status[lap_number] = {
                    "status": "connection_error",
                    "message": str(e),
                    "lap_data": lap_data,  # Store data for retry
                    "telemetry_frames": lap_frames_from_indexer
                }
            else:
                logger.error(f"Error saving lap {lap_number}: {e}", exc_info=True)
                return None

    def _save_telemetry_points(self, lap_uuid, telemetry_points_from_indexer):
        if not self._supabase_client or not lap_uuid or not telemetry_points_from_indexer:
            print(f"❌ [TELEMETRY SAVE] Cannot save telemetry: supabase={bool(self._supabase_client)}, lap_uuid={bool(lap_uuid)}, points={len(telemetry_points_from_indexer) if telemetry_points_from_indexer else 0}")
            logger.warning("Cannot save telemetry: Missing Supabase client, lap ID, or telemetry data.")
            return False
    
        print(f"💾 [TELEMETRY SAVE] Starting save of {len(telemetry_points_from_indexer)} telemetry points for lap {lap_uuid}")
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
        
        print(f"💾 [TELEMETRY SAVE] Sorted telemetry points, processing in batches of {batch_size}")
        
        # Then process in batches
        for i in range(0, len(sorted_points), batch_size):
            batch = sorted_points[i:i + batch_size]
            telemetry_data_to_insert = []
            
            for point in batch:
                # Extract key fields, ensuring defaults if missing
                telemetry_point = {
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
                }
                
                # Debug gear data for first point in each batch
                if len(telemetry_data_to_insert) == 0:  # First point in batch
                    gear_value = telemetry_point["gear"]
                    original_gear = point.get('gear', 'MISSING')
                    fallback_gear = point.get('Gear', 'MISSING')
                    print(f"🔧 [TELEMETRY SAVE GEAR DEBUG] Batch {i // batch_size + 1}: gear={gear_value}, original_gear={original_gear}, fallback_Gear={fallback_gear}")
                
                # Add sector timing data if available
                if 'current_sector' in point:
                    telemetry_point['current_sector'] = point['current_sector']
                if 'current_sector_time' in point:
                    telemetry_point['current_sector_time'] = point['current_sector_time']
                
                telemetry_data_to_insert.append(telemetry_point)
                
            print(f"💾 [TELEMETRY SAVE] Processing batch {i // batch_size + 1}/{(len(sorted_points) + batch_size - 1) // batch_size} ({len(batch)} points)")
                
            # Retry logic for batch saving
            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = self._supabase_client.table("telemetry_points").insert(telemetry_data_to_insert).execute()
                    if response.data:
                        saved_count += len(response.data)
                        print(f"✅ [TELEMETRY SAVE] Batch {i // batch_size + 1} saved successfully ({len(response.data)} points)")
                        break  # Success
                    else:
                        print(f"⚠️ [TELEMETRY SAVE] Batch {i // batch_size + 1} save attempt {retry+1} returned no data")
                        logger.warning(f"Batch {i // batch_size} save attempt {retry+1} returned no data")
                        if retry == max_retries - 1:
                            failed_count += len(telemetry_data_to_insert)
                            failed_batch_indices.append(i // batch_size)
                except Exception as e:
                    print(f"❌ [TELEMETRY SAVE] Batch {i // batch_size + 1} save attempt {retry+1} failed: {e}")
                    logger.error(f"Error saving batch {i // batch_size}, attempt {retry+1}: {e}")
                    if retry == max_retries - 1:
                        failed_count += len(telemetry_data_to_insert)
                        failed_batch_indices.append(i // batch_size)
        
        success = failed_count == 0
        print(f"📊 [TELEMETRY SAVE] Complete! Saved: {saved_count}, Failed: {failed_count}, Success: {success}")
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

    def _save_sector_times(self, lap_uuid, lap_frames):
        """Save sector timing data for a completed lap.
        
        Args:
            lap_uuid: The lap UUID
            lap_frames: List of telemetry frames for the lap
        """
        if not self._supabase_client or not lap_uuid or not lap_frames:
            logger.warning(f"🔍 [SECTOR DEBUG] Cannot save sector times - missing requirements: supabase={bool(self._supabase_client)}, lap_uuid={bool(lap_uuid)}, frames={len(lap_frames) if lap_frames else 0}")
            return False
        
        try:
            # Look for sector timing data in the lap frames
            sector_times = None
            sector_total_time = None
            
            logger.debug(f"[SECTOR] Checking {len(lap_frames)} lap frames for sector data")
            
            # Check the last few frames for completed sector data first
            frames_to_check = min(10, len(lap_frames))
            for i, frame in enumerate(reversed(lap_frames[-frames_to_check:])):
                frame_index = len(lap_frames) - 1 - i
                
                if isinstance(frame, dict) and 'sector_times' in frame and frame['sector_times']:
                    sector_times = frame['sector_times']
                    sector_total_time = frame.get('sector_total_time')
                    logger.debug(f"[SECTOR] Found completed sector data in frame {frame_index}: {sector_times}")
                    break
            
            # If no completed sector data found, try to reconstruct from current lap progress
            if not sector_times:
                logger.debug(f"[SECTOR] No completed sector data found, attempting reconstruction from lap progress")
                
                # Look for frames with sector timing data
                sector_progress_frames = []
                for i, frame in enumerate(lap_frames):
                    if (isinstance(frame, dict) and 
                        frame.get('sector_timing_initialized', False) and
                        'current_lap_sector_times' in frame):
                        sector_progress_frames.append((i, frame))
                
                if sector_progress_frames:
                    # Use the last frame with the most complete sector data
                    last_frame_index, last_frame = sector_progress_frames[-1]
                    current_lap_splits = last_frame.get('current_lap_sector_times', [])
                    completed_sectors = last_frame.get('completed_sectors_count', 0)
                    current_sector_time = last_frame.get('current_sector_time', 0.0)
                    total_sectors = last_frame.get('total_sectors', 0)
                    
                    logger.debug(f"[SECTOR] Found sector progress in frame {last_frame_index}: {completed_sectors}/{total_sectors} sectors completed")
                    
                    # If we have completed sectors, use them
                    if current_lap_splits and len(current_lap_splits) > 0:
                        # Check if this looks like a complete lap (all sectors completed)
                        if len(current_lap_splits) == total_sectors:
                            sector_times = current_lap_splits
                            sector_total_time = sum(sector_times)
                            logger.debug(f"[SECTOR] Reconstructed complete sector data: {len(sector_times)} sectors")
                        else:
                            # Partial lap - include current sector time if significant
                            if current_sector_time > 0.1:  # Only if we've been in current sector for more than 0.1s
                                reconstructed_times = current_lap_splits + [current_sector_time]
                                sector_times = reconstructed_times
                                sector_total_time = sum(sector_times)
                                logger.debug(f"[SECTOR] Reconstructed partial sector data: {len(sector_times)} sectors")
                            else:
                                sector_times = current_lap_splits
                                sector_total_time = sum(sector_times) if sector_times else 0.0
                                logger.debug(f"[SECTOR] Using completed sectors only: {len(sector_times)} sectors")
                    else:
                        logger.warning(f"❌ [SECTOR DEBUG] No usable sector progress data found in frames")
                else:
                    logger.warning(f"❌ [SECTOR DEBUG] No frames with sector timing data found")
            
            if not sector_times:
                logger.warning(f"❌ [SECTOR DEBUG] No sector timing data found in lap frames for lap {lap_uuid}")
                
                # FALLBACK: Try to get sector data from the sector timing system directly
                if hasattr(self, '_get_sector_data_from_timing_system'):
                    sector_times = self._get_sector_data_from_timing_system(lap_uuid)
                    if sector_times:
                        logger.warning(f"🔧 [SECTOR FALLBACK] Retrieved sector data from timing system fallback: {sector_times}")
                        logger.warning(f"🔧 [SECTOR FALLBACK] This indicates the primary integration needs fixing!")
                    else:
                        logger.warning(f"❌ [SECTOR DEBUG] Fallback sector data retrieval also failed")
                        return False
                else:
                    logger.warning(f"❌ [SECTOR DEBUG] No fallback method available for sector data retrieval")
                    return False
            else:
                logger.info(f"✅ [SECTOR PRIMARY] Found sector data in lap frames - primary integration working!")
            
            logger.info(f"💾 [SECTOR DEBUG] Saving sector times for lap {lap_uuid}: {sector_times}")
            
            # Update the laps table with sector times instead of inserting into separate table
            sector_updates = {}
            for sector_num, sector_time in enumerate(sector_times, 1):
                if sector_num <= 10:  # Only save up to 10 sectors
                    sector_updates[f"sector{sector_num}_time"] = sector_time
            
            logger.info(f"💾 [SECTOR DEBUG] Updating lap {lap_uuid} with sector columns: {sector_updates}")
            
            # Add a small delay to ensure the lap record exists before updating
            import time
            time.sleep(0.1)
            
            try:
                response = self._supabase_client.table("laps").update(sector_updates).eq("id", lap_uuid).execute()
                
                logger.info(f"💾 [SECTOR DEBUG] Update response received - data: {bool(response.data)}, count: {getattr(response, 'count', 'N/A')}")
                
                if response.data:
                    logger.info(f"✅ [SECTOR DEBUG] Successfully updated lap {lap_uuid} with {len(sector_updates)} sector columns")
                    return True
                else:
                    logger.error(f"❌ [SECTOR DEBUG] Failed to update sector times for lap {lap_uuid}")
                    logger.error(f"❌ [SECTOR DEBUG] Response data: {response.data}")
                    logger.error(f"❌ [SECTOR DEBUG] Response count: {getattr(response, 'count', 'N/A')}")
                    
                    # Try to verify if the lap record exists
                    try:
                        check_response = self._supabase_client.table("laps").select("id").eq("id", lap_uuid).execute()
                        if check_response.data:
                            logger.error(f"❌ [SECTOR DEBUG] Lap record exists but update failed - possible data type issue")
                            logger.error(f"❌ [SECTOR DEBUG] Sector updates attempted: {sector_updates}")
                        else:
                            logger.error(f"❌ [SECTOR DEBUG] Lap record does not exist - timing issue")
                    except Exception as check_error:
                        logger.error(f"❌ [SECTOR DEBUG] Error checking lap record existence: {check_error}")
                    
                    return False
                    
            except Exception as update_error:
                logger.error(f"❌ [SECTOR DEBUG] Exception during sector update: {update_error}")
                logger.error(f"❌ [SECTOR DEBUG] Update data attempted: {sector_updates}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [SECTOR DEBUG] Error saving sector times for lap {lap_uuid}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

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
            
        # Shutdown immediate saving if enabled
        if hasattr(self.lap_indexer, 'stop_save_worker'):
            logger.info("🛑 Stopping immediate save worker")
            self.lap_indexer.stop_save_worker()
            
            # Log final immediate saving statistics
            stats = self.get_immediate_saving_stats()
            logger.info(f"📊 Immediate saving final stats: {stats['successful']}/{stats['processed']} "
                       f"saves successful ({stats['success_rate']:.1f}%)")

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

    def set_sector_timing_system(self, sector_timing):
        """Set the sector timing system for direct sector data access.
        
        Args:
            sector_timing: The SectorTimingCollector instance
        """
        self._sector_timing_system = sector_timing
        logger.info("✅ [SECTOR DEBUG] Sector timing system connected to lap saver")
        
    def set_iracing_api(self, iracing_api):
        """Set the iRacing API for direct lap-specific sector data access.
        
        Args:
            iracing_api: The SimpleIRacingAPI instance
        """
        self._iracing_api = iracing_api
        logger.info("✅ [SECTOR DEBUG] iRacing API connected to lap saver for lap-specific sector data")
    
    def _get_sector_data_from_timing_system(self, lap_uuid):
        """Fallback method to get sector data directly from the sector timing system.
        
        Args:
            lap_uuid: The lap UUID (not used in this fallback, but kept for consistency)
            
        Returns:
            List of sector times or None if not available
        """
        if not hasattr(self, '_sector_timing_system') or not self._sector_timing_system:
            logger.warning("❌ [SECTOR DEBUG] No sector timing system available for fallback")
            return None
        
        try:
            # Get the most recent completed lap from the sector timing system
            recent_laps = self._sector_timing_system.get_recent_laps(1)
            if recent_laps:
                latest_lap = recent_laps[-1]
                
                # Handle both dictionary and object formats
                if isinstance(latest_lap, dict):
                    # Dictionary format from SimpleSectorTimingIntegration
                    sector_times = latest_lap.get('sector_times', [])
                    is_complete = latest_lap.get('is_complete', False)
                    lap_number = latest_lap.get('lap_number', 0)
                else:
                    # Object format (legacy support)
                    sector_times = getattr(latest_lap, 'sector_times', [])
                    is_complete = getattr(latest_lap, 'is_valid', False)
                    lap_number = getattr(latest_lap, 'lap_number', 0)
                
                if sector_times and is_complete:
                    logger.info(f"✅ [SECTOR DEBUG] Retrieved sector data from timing system for lap {lap_number}: {sector_times}")
                    return sector_times
                else:
                    logger.warning(f"❌ [SECTOR DEBUG] Latest lap from timing system has no valid sector data (lap {lap_number}, complete: {is_complete})")
            else:
                logger.warning(f"❌ [SECTOR DEBUG] No recent laps available from timing system")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [SECTOR DEBUG] Error getting sector data from timing system: {e}")
            return None

    def _ensure_session_exists(self):
        """
        Ensure the current session exists in the database.
        Create it if it doesn't exist.
        
        Returns:
            bool: True if session exists or was created successfully, False otherwise
        """
        if not self._current_session_id:
            logger.error("[SESSION VALIDATION] No current session ID set")
            return False
            
        if not self._supabase_client:
            logger.error("[SESSION VALIDATION] No Supabase client available")
            return False
            
        try:
            # Check if session exists
            logger.info(f"[SESSION VALIDATION] Checking if session {self._current_session_id} exists in database")
            
            response = self._supabase_client.table("sessions").select("id").eq("id", self._current_session_id).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"[SESSION VALIDATION] ✅ Session {self._current_session_id} exists in database")
                return True
            
            # Session doesn't exist - try to create it
            logger.warning(f"[SESSION VALIDATION] ❌ Session {self._current_session_id} does not exist in database")
            return self._create_missing_session()
            
        except Exception as e:
            logger.error(f"[SESSION VALIDATION] Error checking session existence: {e}")
            return False
    
    def _create_missing_session(self):
        """
        Create a missing session record in the database.
        
        Returns:
            bool: True if session was created successfully, False otherwise
        """
        try:
            # We need track_id, car_id, and user_id to create a session
            if not all([self._current_track_id, self._current_car_id, self._user_id]):
                logger.error(f"[SESSION CREATION] Missing required data for session creation:")
                logger.error(f"[SESSION CREATION]   Track ID: {self._current_track_id}")
                logger.error(f"[SESSION CREATION]   Car ID: {self._current_car_id}")
                logger.error(f"[SESSION CREATION]   User ID: {self._user_id}")
                return False
            
            logger.info(f"[SESSION CREATION] Creating missing session {self._current_session_id}")
            
            # Create session data matching the schema
            session_data = {
                'id': self._current_session_id,  # Use the existing session ID from monitor
                'user_id': self._user_id,
                'track_id': self._current_track_id,
                'car_id': self._current_car_id,
                'session_type': self._current_session_type or 'Practice',
                'session_date': 'now()',
                'created_at': 'now()'
            }
            
            logger.info(f"[SESSION CREATION] Session data: {session_data}")
            
            # Insert the session
            response = self._supabase_client.table("sessions").insert(session_data).execute()
            
            if response.data and len(response.data) > 0:
                created_session_id = response.data[0].get('id')
                logger.info(f"[SESSION CREATION] ✅ Successfully created session {created_session_id}")
                
                # Process any queued immediate laps now that we have a session
                if hasattr(self, '_queued_immediate_laps') and self._queued_immediate_laps:
                    logger.info(f"[SESSION CREATION] Processing {len(self._queued_immediate_laps)} queued immediate laps")
                    self._process_queued_immediate_laps()
                
                return True
            else:
                logger.error(f"[SESSION CREATION] ❌ Failed to create session - no data returned")
                return False
                
        except Exception as e:
            # Check if it's a duplicate key error (session was created by another process)
            if "duplicate key value violates unique constraint" in str(e) or "violates unique constraint" in str(e):
                logger.info(f"[SESSION CREATION] ✅ Session {self._current_session_id} was created by another process")
                return True
            else:
                logger.error(f"[SESSION CREATION] ❌ Error creating session: {e}")
                return False
    
    def set_session_context(self, session_id, track_id, car_id, session_type=None):
        """
        Set the session context for lap saving.
        
        Args:
            session_id: The session UUID
            track_id: The track database ID
            car_id: The car database ID
            session_type: The session type (Practice, Qualifying, Race, etc.)
        """
        self._current_session_id = session_id
        self._current_track_id = track_id
        self._current_car_id = car_id
        self._current_session_type = session_type
        
        logger.info(f"[SESSION CONTEXT] Set session context:")
        logger.info(f"[SESSION CONTEXT]   Session ID: {session_id}")
        logger.info(f"[SESSION CONTEXT]   Track ID: {track_id}")
        logger.info(f"[SESSION CONTEXT]   Car ID: {car_id}")
        logger.info(f"[SESSION CONTEXT]   Session Type: {session_type}")
        
        # Validate the session exists
        if session_id:
            session_valid = self._ensure_session_exists()
            if session_valid:
                logger.info(f"[SESSION CONTEXT] ✅ Session {session_id} validated successfully")
            else:
                logger.error(f"[SESSION CONTEXT] ❌ Session {session_id} validation failed")

    def backfill_sector_data(self, sector_data_package, frames_back=200):
        """Store completed sector data in buffer for later use when processing delayed laps.
        
        This method is called when a lap is completed with sector timing data,
        storing that data so it can be retrieved when the lap saver processes
        the lap (which happens with a 3-second delay due to the LapIndexer).
        
        Args:
            sector_data_package: Dictionary containing all sector timing data
            frames_back: Number of frames back to consider (for logging only)
        """
        try:
            # Extract lap number from sector data
            sector_completion_frame_id = sector_data_package.get('sector_completion_frame_id')
            sector_times = sector_data_package.get('sector_times', [])
            
            if not sector_times:
                logger.warning(f"❌ [BACKFILL] No sector times in sector data package")
                return
                
            # Store the sector data with frame ID as key (we'll match by proximity)
            if sector_completion_frame_id:
                self._sector_data_buffer[sector_completion_frame_id] = sector_data_package
                logger.debug(f"🔧 [BACKFILL] Stored sector data for frame {sector_completion_frame_id}: {len(sector_times)} sectors")
                
                # Clean up old entries to prevent memory leak
                if len(self._sector_data_buffer) > self._max_buffer_size:
                    # Remove oldest entries (smallest frame IDs)
                    old_keys = sorted(self._sector_data_buffer.keys())[:-self._max_buffer_size]
                    for old_key in old_keys:
                        del self._sector_data_buffer[old_key]
                    logger.debug(f"🧹 [BACKFILL] Cleaned up {len(old_keys)} old sector data entries")
            else:
                logger.warning(f"❌ [BACKFILL] No sector_completion_frame_id in sector data package")
                
        except Exception as e:
            logger.error(f"❌ [BACKFILL] Error storing sector data: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _get_buffered_sector_data(self, lap_number, frame_range=None):
        """Retrieve buffered sector data for a lap.
        
        Args:
            lap_number: The lap number to find sector data for
            frame_range: Optional tuple of (start_frame, end_frame) to search within
            
        Returns:
            dict: Sector data package if found, None otherwise
        """
        try:
            if not self._sector_data_buffer:
                logger.debug(f"🔍 [BACKFILL] No buffered sector data available for lap {lap_number}")
                return None
                
            logger.debug(f"🔍 [BACKFILL] Searching buffered sector data for lap {lap_number}")
            logger.debug(f"🔍 [BACKFILL] Available buffer keys: {list(self._sector_data_buffer.keys())}")
            
            # If we have a frame range, look for sector data within that range
            if frame_range:
                start_frame, end_frame = frame_range
                for frame_id in sorted(self._sector_data_buffer.keys(), reverse=True):
                    if start_frame <= frame_id <= end_frame:
                        sector_data = self._sector_data_buffer[frame_id]
                        logger.info(f"✅ [BACKFILL] Found matching sector data at frame {frame_id} for lap {lap_number}")
                        return sector_data
            
            # Otherwise, return the most recent sector data (highest frame ID)
            if self._sector_data_buffer:
                latest_frame_id = max(self._sector_data_buffer.keys())
                sector_data = self._sector_data_buffer[latest_frame_id]
                logger.info(f"✅ [BACKFILL] Using latest buffered sector data from frame {latest_frame_id} for lap {lap_number}")
                return sector_data
                
            logger.debug(f"❌ [BACKFILL] No matching buffered sector data found for lap {lap_number}")
            return None
            
        except Exception as e:
            logger.error(f"❌ [BACKFILL] Error retrieving buffered sector data for lap {lap_number}: {e}")
            return None