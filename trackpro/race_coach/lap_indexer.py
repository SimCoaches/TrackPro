# lap_indexer.py
"""
Absolute-truth lap indexer for TrackPro.

This module relies *exclusively* on iRacing's own lap counters:
  • ir["LapCompleted"]      – integer, increases when a lap is fully scored
  • ir["Lap"]               – current live lap index ( = LapCompleted + 1 )
  • ir["CarIdxLastLapTime"] – EXACT lap times for each car (PRIMARY timing source)
  • ir["LapLastLapTime"]    – fallback timing source when CarIdx data unavailable
  • ir["LapInvalidated"]    – flag, 1 if the *current* lap will be invalid
  • ir["OnPitRoad"]         – informational only

CRITICAL NEW TRACKING APPROACH:
  • We track the lap that will complete NEXT, not the current driving lap
  • When LapCompleted increments from X to Y, lap Y just finished
  • We save the telemetry data we collected as lap Y (the completed lap)
  • We then start tracking lap Y+1 (the next lap that will complete)

Behaviour:
  • Out-lap = LapCompleted == 0 at the start of the lap.
  • New lap boundary when LapCompleted increments.
  • Lap time taken from CarIdxLastLapTime[PlayerCarIdx] for EXACT iRacing timing.
  • Stores every telemetry frame inside its lap bucket.
"""

from __future__ import annotations
from typing import Dict, List, Any
from enum import Enum, auto
import logging
import time
import threading
import queue
from typing import Optional, Callable

# Setup logging
logger = logging.getLogger(__name__)

class LapState(Enum):
    """Enum to track the type of lap."""
    OUT = auto()
    TIMED = auto()
    IN = auto()
    INCOMPLETE = auto()

class LapIndexer:
    def __init__(self) -> None:
        self.laps: List[Dict[str, Any]] = []
        self._finalized_laps: List[Dict[str, Any]] = []
        self._is_finalized: bool = False

        # Live lap state for the lap currently being recorded
        self._active_lap_frames: List[Dict[str, Any]] = []
        self._active_lap_number_internal: int | None = None # Stores the lap number that will complete next (ir["LapCompleted"] + 1)
        self._active_lap_start_tick: float | None = None
        self._active_lap_invalid_sdk: bool = False # True if ir["LapInvalidated"] was seen during this lap
        self._active_lap_started_on_pit: bool = False
        self._active_lap_state: LapState = LapState.INCOMPLETE

        # SDK state from the PREVIOUS telemetry frame
        self._last_lap_completed_sdk: int | None = None
        self._previous_frame_ir_data: Dict[str, Any] | None = None
        
        # TIMING FIX: Pending lap completion to delay timing read
        self._pending_lap_completion: Dict[str, Any] | None = None
        
        # Rate limiting for warnings
        self._last_sdk_data_warning_time: float = 0.0
        self._last_sdk_data_warning_message: str = ""
        self._warning_interval: float = 5.0  # seconds
        
        # IMMEDIATE SAVING INFRASTRUCTURE
        self._immediate_save_queue: queue.Queue = queue.Queue()
        self._save_worker_thread: Optional[threading.Thread] = None
        self._save_worker_running: bool = False
        self._save_callback: Optional[Callable] = None
        self._stop_worker_event: threading.Event = threading.Event()
        
        # Track saved laps for backward compatibility with get_laps()
        self._saved_laps: List[Dict[str, Any]] = []

    def set_immediate_save_callback(self, save_callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set the callback function for immediate lap saving.
        
        Args:
            save_callback: Function that takes a lap dict and saves it immediately
        """
        self._save_callback = save_callback
        logger.info("[LapIndexer] Immediate save callback registered")
    
    def start_save_worker(self) -> None:
        """Start the background worker thread for immediate lap saving."""
        if self._save_worker_running:
            logger.warning("[LapIndexer] Save worker already running")
            return
            
        self._save_worker_running = True
        self._stop_worker_event.clear()
        self._save_worker_thread = threading.Thread(target=self._save_worker_loop, daemon=True)
        self._save_worker_thread.start()
        logger.info("[LapIndexer] ✅ Immediate save worker thread started")
    
    def stop_save_worker(self) -> None:
        """Stop the background worker thread."""
        if not self._save_worker_running:
            return
            
        self._save_worker_running = False
        self._stop_worker_event.set()
        
        # Add a poison pill to wake up the worker
        self._immediate_save_queue.put(None)
        
        if self._save_worker_thread and self._save_worker_thread.is_alive():
            self._save_worker_thread.join(timeout=2.0)
            logger.info("[LapIndexer] ✅ Immediate save worker thread stopped")
    
    def _save_worker_loop(self) -> None:
        """Background worker thread that processes immediate lap saves."""
        logger.info("[LapIndexer] 🚀 Save worker thread running")
        
        while self._save_worker_running:
            try:
                # Wait for lap data to save
                lap_data = self._immediate_save_queue.get(timeout=1.0)
                
                # Check for poison pill (stop signal)
                if lap_data is None:
                    break
                    
                # Process the lap
                lap_num = lap_data.get("lap_number_sdk", "unknown")
                lap_state = lap_data.get("lap_state", "UNKNOWN")
                lap_time = lap_data.get("duration_seconds", 0)
                
                logger.info(f"[SaveWorker] 💾 SAVING lap {lap_num} ({lap_state}, {lap_time:.3f}s)")
                
                # Call the save callback and check if it succeeded
                if self._save_callback:
                    try:
                        # The callback should return True/False to indicate success
                        result = self._save_callback(lap_data)
                        # Handle different return types (some callbacks may not return anything)
                        save_success = result if result is not None else True
                        
                        if save_success:
                            # Track saved laps for backward compatibility
                            self._saved_laps.append(lap_data)
                            logger.info(f"[SaveWorker] ✅ Successfully saved lap {lap_num}")
                        else:
                            logger.error(f"[SaveWorker] ❌ Failed to save lap {lap_num}")
                    except Exception as e:
                        logger.error(f"[SaveWorker] ❌ Save callback threw exception for lap {lap_num}: {e}")
                else:
                    logger.warning(f"[SaveWorker] ⚠️ No save callback registered - lap {lap_num} not saved")
                    
                # Mark task as done
                self._immediate_save_queue.task_done()
                
            except queue.Empty:
                # Timeout - check if we should continue
                if self._stop_worker_event.is_set():
                    break
                continue
                
            except Exception as e:
                lap_num = lap_data.get("lap_number_sdk", "unknown") if 'lap_data' in locals() else "unknown"
                logger.error(f"[SaveWorker] ❌ Failed to save lap {lap_num}: {e}")
        
        logger.info("[LapIndexer] 🛑 Save worker thread finished")
    
    def _save_lap_immediately(self, lap_data: Dict[str, Any]) -> None:
        """Queue a lap for immediate saving by the background worker.
        
        Args:
            lap_data: Complete lap dictionary to save
        """
        try:
            if not self._save_worker_running:
                logger.warning("[LapIndexer] ⚠️ Save worker not running - starting automatically")
                self.start_save_worker()
            
            # Queue the lap for immediate saving
            self._immediate_save_queue.put(lap_data, timeout=1.0)
            
            lap_num = lap_data.get("lap_number_sdk", "unknown")
            logger.info(f"[LapIndexer] ⚡ QUEUED lap {lap_num} for immediate save")
            
        except queue.Full:
            lap_num = lap_data.get("lap_number_sdk", "unknown")
            logger.error(f"[LapIndexer] ❌ Save queue full - couldn't queue lap {lap_num}")
        except Exception as e:
            lap_num = lap_data.get("lap_number_sdk", "unknown")
            logger.error(f"[LapIndexer] ❌ Failed to queue lap {lap_num} for saving: {e}")

    def _log_sdk_warning(self, message: str):
        current_time = time.time()
        if (current_time - self._last_sdk_data_warning_time > self._warning_interval or
            message != self._last_sdk_data_warning_message):
            logger.warning(message)
            self._last_sdk_data_warning_time = current_time
            self._last_sdk_data_warning_message = message

    def on_frame(self, ir_data: Dict[str, Any]) -> None:
        """Process a single telemetry frame to detect laps and boundaries.
        
        Args:
            ir_data: Raw telemetry data dictionary from iRacing
        """
        if not ir_data:
            return
        
        # --- Validate and Extract Key SDK Data ---
        try:
            now_tick = float(ir_data["SessionTimeSecs"])
            current_lap_completed_sdk = int(ir_data["LapCompleted"])
            current_lap_driving_sdk = int(ir_data["Lap"]) # Lap player is currently driving
            lap_last_lap_time_sdk = float(ir_data["LapLastLapTime"]) # Time of the lap that just finished
            
            # BETTER TIMING SOURCE: Use CarIdxLastLapTime for our own car
            # This is likely more accurate and matches iRacing's internal timing
            player_car_idx = int(ir_data.get("PlayerCarIdx", 0))
            car_idx_last_lap_times = ir_data.get("CarIdxLastLapTime", [])
            
            # Get our car's lap time from the car index array
            our_car_lap_time = 0.0
            if isinstance(car_idx_last_lap_times, (list, tuple)) and len(car_idx_last_lap_times) > player_car_idx:
                our_car_lap_time = float(car_idx_last_lap_times[player_car_idx])
                
                # Rate limit these logs to prevent spam - only log every 300 frames (~5 seconds at 60Hz)
                current_time = time.time()
                should_log_timing = not hasattr(self, '_last_timing_log_time') or (current_time - getattr(self, '_last_timing_log_time', 0) > 5.0)
                
                if should_log_timing:
                    logger.info(f"[ACCURATE TIMING] 🎯 CarIdxLastLapTime[{player_car_idx}] = {our_car_lap_time:.3f}s")
                    logger.info(f"[ACCURATE TIMING] 📊 Comparison: LapLastLapTime = {lap_last_lap_time_sdk:.3f}s")
                    self._last_timing_log_time = current_time
            else:
                # Fallback to regular LapLastLapTime if CarIdx data not available
                our_car_lap_time = lap_last_lap_time_sdk
                logger.warning(f"[ACCURATE TIMING] ⚠️ CarIdxLastLapTime not available, using LapLastLapTime = {lap_last_lap_time_sdk:.3f}s")
            
            # Handle OnPitRoad gracefully if missing
            on_pit_road_now = False  # Default value
            if "OnPitRoad" in ir_data:
                on_pit_road_now = bool(ir_data["OnPitRoad"])
            else:
                # Log once per session or at reduced frequency
                current_time = time.time()
                if not hasattr(self, '_last_missing_pit_road_warning') or (current_time - getattr(self, '_last_missing_pit_road_warning', 0) > 10.0):
                    logger.info("[LapIndexer] 'OnPitRoad' key missing in ir_data, using default value: False")
                    self._last_missing_pit_road_warning = current_time
                
            # Handle LapInvalidated gracefully if missing
            lap_invalidated_flag_now = False  # Default value
            if "LapInvalidated" in ir_data:
                lap_invalidated_flag_now = bool(ir_data["LapInvalidated"])
            else:
                # Log once per session or at reduced frequency
                current_time = time.time()
                if not hasattr(self, '_last_missing_lap_invalidated_warning') or (current_time - getattr(self, '_last_missing_lap_invalidated_warning', 0) > 10.0):
                    logger.info("[LapIndexer] 'LapInvalidated' key missing in ir_data, using default value: False")
                    self._last_missing_lap_invalidated_warning = current_time
                
        except KeyError as e:
            # Check if it's a key we're already handling gracefully
            key_name = str(e).strip("'")
            if key_name not in ["OnPitRoad", "LapInvalidated"]:  # If it's a different missing key
                self._log_sdk_warning(f"[LapIndexer] Missing essential key in ir_data: {e}. Skipping frame.")
                return
        except (TypeError, ValueError) as e:
            self._log_sdk_warning(f"[LapIndexer] Type error in essential ir_data: {e}. Skipping frame.")
            return

        frame_copy = dict(ir_data) # Guard against external mutation
        
        # Add lap metadata to this frame for analysis
        if self._active_lap_number_internal is not None:
            frame_copy["lap_internal_number"] = self._active_lap_number_internal
            frame_copy["lap_state"] = self._active_lap_state.name
            frame_copy["lap_is_valid_sdk"] = not self._active_lap_invalid_sdk
            frame_copy["is_valid_for_leaderboard"] = (self._active_lap_state == LapState.TIMED and not self._active_lap_invalid_sdk)

        # --- Initialization (First Frame) ---
        if self._last_lap_completed_sdk is None:
            logger.info("[LapIndexer] First frame received. Initializing lap tracking.")
            # Get current lap distance for initial classification
            current_lap_dist_pct_initial = float(frame_copy.get("LapDistPct", 0.0))
            
            # Always track the lap that's currently in progress (ir["Lap"])
            # This is the lap we're collecting telemetry for RIGHT NOW
            is_mid_session_join = current_lap_completed_sdk > 0
            
            # Track the lap that will be completed next
            # When we join mid-session, we want to track the lap that will complete next
            lap_to_track = current_lap_completed_sdk + 1
            
            logger.info(f"[LapIndexer] 🔧 INITIALIZATION: iRacing Lap={current_lap_driving_sdk}, LapCompleted={current_lap_completed_sdk}")
            logger.info(f"[LapIndexer] 🎯 TRACKING STRATEGY: Track lap {lap_to_track} (will complete next)")
            logger.info(f"[LapIndexer] 📊 LOGIC: Collect telemetry for lap {lap_to_track}, save as lap {lap_to_track}")
            
            self._start_new_lap(
                lap_number_internal=lap_to_track, # Track the lap that will complete next
                start_tick=now_tick,
                on_pit_start=on_pit_road_now,
                # LapInvalidated refers to ir["Lap"], which is current_lap_driving_sdk here.
                # So, this flag is for the lap we are *just starting*.
                invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now,
                # Pass initial lap distance for correct classification on first frame
                initial_lap_dist_pct=current_lap_dist_pct_initial,
                is_mid_session_join=is_mid_session_join
            )
            # Add metadata to the initialization frame
            init_frame = dict(frame_copy)
            init_frame["_assigned_to_lap"] = lap_to_track
            init_frame["_frame_type"] = "initialization"
            init_frame["_is_mid_session_join"] = is_mid_session_join
            self._active_lap_frames.append(init_frame)
            self._last_lap_completed_sdk = current_lap_completed_sdk
            self._previous_frame_ir_data = frame_copy
            
            return

        # --- Main Lap Transition Logic ---
        # TIMING FIX: Process any pending lap completion after 3-second delay
        if self._pending_lap_completion is not None:
            # Check if 3 seconds have passed since the lap completion was detected
            completion_time = self._pending_lap_completion['completion_timestamp']
            time_elapsed = now_tick - completion_time
            
            if time_elapsed >= 3.0:  # 3-second delay
                logger.info(f"[TIMING FIX] 🎯 Processing pending lap timing after {time_elapsed:.1f}s delay")
                
                # Get the stored lap data
                stored_lap_data = self._pending_lap_completion
                lap_that_finished = stored_lap_data['lap_number']
                
                logger.info(f"[TIMING FIX] 📊 CarIdxLastLapTime[{player_car_idx}] for completed lap {lap_that_finished}: {our_car_lap_time:.3f}s")
                logger.info(f"[TIMING FIX] 📊 LapLastLapTime for comparison: {lap_last_lap_time_sdk:.3f}s")
                
                # Process the stored lap data with the updated timing
                self._finalize_stored_lap_with_timing(stored_lap_data, our_car_lap_time)
                
                logger.info(f"[TIMING FIX] ✅ COMPLETED: Lap {lap_that_finished} finalized with proper timing {our_car_lap_time:.3f}s after 3s delay")
                
                # Clear pending completion
                self._pending_lap_completion = None
            else:
                # Still waiting for the 3-second delay - log progress occasionally
                if not hasattr(self, '_last_delay_log_time') or (now_tick - getattr(self, '_last_delay_log_time', 0) > 1.0):
                    logger.info(f"[TIMING FIX] ⏳ Waiting for timing delay: {time_elapsed:.1f}s / 3.0s for lap {self._pending_lap_completion['lap_number']}")
                    self._last_delay_log_time = now_tick
        
        # When LapCompleted increments, it means the lap we were tracking just finished
        # The new driving lap is now current_lap_driving_sdk
        lap_completed_incremented = current_lap_completed_sdk > self._last_lap_completed_sdk
        
        # Detect if we missed multiple lap completions (gap in polling)
        missed_increments = 0
        if lap_completed_incremented:
            missed_increments = current_lap_completed_sdk - self._last_lap_completed_sdk
            if missed_increments > 1:
                logger.warning(f"[LapIndexer] 🚨 MISSED LAP COMPLETIONS: Detected gap of {missed_increments} laps! "
                              f"Last tracked: {self._last_lap_completed_sdk}, Current: {current_lap_completed_sdk}")
        
        # Check if our internal tracking matches iRacing's driving lap
        expected_driving_lap = self._active_lap_number_internal
        lap_number_desync = False
        
        # Handle session restart detection
        # When iRacing reports Lap=0 and LapCompleted=0, it means session restarted
        if current_lap_driving_sdk == 0 and current_lap_completed_sdk == 0:
            if self._active_lap_number_internal is not None and self._active_lap_number_internal > 0:
                logger.warning(f"[LapIndexer] 🔄 SESSION RESTART DETECTED: iRacing reset to Lap=0, LapCompleted=0")
                logger.warning(f"[LapIndexer] 🔄 Current tracking state: lap {self._active_lap_number_internal}")
                
                # Handle the restart by resetting our state
                logger.info(f"[LapIndexer] 🔄 RESTART HANDLING: Resetting lap tracking state")
                self._active_lap_frames = []
                self._active_lap_number_internal = None
                self._active_lap_start_tick = None
                self._active_lap_state = LapState.INCOMPLETE
                self._pending_lap_completion = None  # Clear any pending completion
                
                # Skip further processing for this frame and let the next frame start fresh
                self._last_lap_completed_sdk = current_lap_completed_sdk
                self._previous_frame_ir_data = frame_copy
                logger.info(f"[LapIndexer] 🔄 RESTART COMPLETE: Ready for fresh initialization on next frame")
                return
        
        if current_lap_driving_sdk > 0 and expected_driving_lap is not None:
            if current_lap_driving_sdk != expected_driving_lap:
                # Rate limit desync logging to prevent spam
                current_time = time.time()
                should_log_desync = not hasattr(self, '_last_desync_log_time') or (current_time - getattr(self, '_last_desync_log_time', 0) > 10.0)
                
                if should_log_desync:
                    logger.warning(f"[LapIndexer] 🚨 LAP DESYNC: Tracking lap {expected_driving_lap}, "
                                  f"but iRacing driving lap {current_lap_driving_sdk} (completed: {current_lap_completed_sdk})")
                    self._last_desync_log_time = current_time
                
                lap_number_desync = True
                
                # If we're behind, we need to catch up
                if current_lap_driving_sdk > expected_driving_lap:
                    laps_behind = current_lap_driving_sdk - expected_driving_lap
                    if should_log_desync:
                        logger.warning(f"[LapIndexer] 🔧 RECOVERY: We're {laps_behind} laps behind iRacing")
                    
                    # Force lap completion to catch up
                    if not lap_completed_incremented and laps_behind >= 1:
                        logger.info(f"[LapIndexer] 🔧 FORCED SYNC: Treating as missed lap completion")
                        lap_completed_incremented = True
                        missed_increments = laps_behind
        
        # LAP COMPLETION HANDLING
        # When LapCompleted increments, it means the lap we were tracking just finished
        # We need to finalize that lap and start tracking the new driving lap
        if lap_completed_incremented:
            # TIMING FIX: Don't read CarIdxLastLapTime immediately - it might not be updated yet
            # But DO start tracking the new lap immediately to avoid sync issues
            logger.info(f"[TIMING FIX] 🕐 LAP COMPLETION DETECTED: LapCompleted {self._last_lap_completed_sdk} → {current_lap_completed_sdk}")
            logger.info(f"[TIMING FIX] 🕐 Delaying timing read for proper CarIdxLastLapTime update")
            
            if missed_increments == 1:
                # NORMAL SINGLE LAP COMPLETION - Store completed lap data for delayed timing processing
                lap_that_just_finished = current_lap_completed_sdk
                next_lap_to_collect = current_lap_driving_sdk
                
                # Store the completed lap's telemetry data for delayed timing processing
                completed_lap_data = {
                    'lap_number': lap_that_just_finished,
                    'telemetry_frames': list(self._active_lap_frames),  # Copy existing frames
                    'start_tick': self._active_lap_start_tick,
                    'end_tick': now_tick,
                    'ended_on_pit_road': on_pit_road_now,
                    'started_on_pit_road': self._active_lap_started_on_pit,
                    'lap_state': self._active_lap_state,
                    'invalid_sdk': self._active_lap_invalid_sdk,
                    'completion_timestamp': now_tick
                }
                
                # Store for delayed timing processing
                self._pending_lap_completion = completed_lap_data
                
                logger.info(f"[TIMING FIX] 📝 PENDING: Lap {lap_that_just_finished} data stored for 3-second delayed timing")
                
                # IMMEDIATELY start tracking the new lap to avoid sync issues
                self._start_new_lap(
                    lap_number_internal=next_lap_to_collect,
                    start_tick=now_tick,
                    on_pit_start=on_pit_road_now,
                    invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now
                )
                
                logger.info(f"[TIMING FIX] 🚀 IMMEDIATE: Started tracking lap {next_lap_to_collect} (no sync delay)")
                
            else:
                # MULTIPLE MISSED INCREMENTS - Handle immediately (fallback)
                logger.warning(f"[TIMING FIX] ⚠️ Multiple increments ({missed_increments}) - processing immediately as fallback")
                
                if missed_increments > 10:
                    logger.warning(f"[LapIndexer] 🚨 HUGE GAP DETECTED: {missed_increments} missed increments - likely reset")
                    self._start_new_lap(
                        lap_number_internal=current_lap_driving_sdk,
                        start_tick=now_tick,
                        on_pit_start=on_pit_road_now,
                        invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now
                    )
                else:
                    logger.warning(f"[LapIndexer] 🔧 MULTIPLE COMPLETIONS: Processing {missed_increments} missed laps")
                    
                    # Add the boundary frame to the lap that just finished
                    if self._active_lap_number_internal is not None:
                        # Add metadata to identify this as a boundary frame
                        boundary_frame = dict(frame_copy)
                        boundary_frame["_is_boundary_frame"] = True
                        boundary_frame["_lap_transition"] = f"Lap {self._active_lap_number_internal} completed"
                        boundary_frame["_recovery_frame"] = True
                        boundary_frame["_missed_increments"] = missed_increments
                        self._active_lap_frames.append(boundary_frame)
                        
                        # Use fallback timing approach for multiple increments
                        lap_that_just_finished = current_lap_completed_sdk
                        
                        self._finalise_active_lap(
                            end_tick=now_tick,
                            lap_last_lap_time_from_sdk=lap_last_lap_time_sdk,  # Use LapLastLapTime as fallback
                            ended_on_pit_road=on_pit_road_now,
                            session_finalize=False,
                            current_lap_completed_sdk=lap_that_just_finished
                        )
                        
                        logger.info(f"[TIMING FIX] ✅ FALLBACK: Lap {lap_that_just_finished} saved with LapLastLapTime")
                        
                        # Start collecting telemetry for the next lap
                        next_lap_to_collect = current_lap_driving_sdk
                        
                        self._start_new_lap(
                            lap_number_internal=next_lap_to_collect,
                            start_tick=now_tick,
                            on_pit_start=on_pit_road_now,
                            invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now
                        )
        
        # --- Collect Telemetry for Active Lap ---
        if self._active_lap_number_internal is not None and not lap_completed_incremented:
            # Normal telemetry collection - always track the current driving lap
            expected_tracking_lap = current_lap_driving_sdk  # We should be tracking the lap we're driving
            if self._active_lap_number_internal != expected_tracking_lap:
                logger.error(f"[LapIndexer] 🚨 FRAME ASSIGNMENT ERROR: Tracking={self._active_lap_number_internal}, Expected={expected_tracking_lap}")
                # Force sync
                self._active_lap_number_internal = expected_tracking_lap
                logger.info(f"[LapIndexer] 🔧 SYNC CORRECTED: Now tracking lap {expected_tracking_lap}")
            
            # Add metadata to track frame assignment with validation
            normal_frame = dict(frame_copy)
            normal_frame["_assigned_to_lap"] = self._active_lap_number_internal
            normal_frame["_frame_type"] = "normal"
            normal_frame["_iracing_driving_lap"] = current_lap_driving_sdk
            normal_frame["_assignment_validated"] = True
            normal_frame["_has_pending_completion"] = self._pending_lap_completion is not None
            self._active_lap_frames.append(normal_frame)
            
            # Minimal debug logging for frame assignment (only every 500 frames to reduce spam)
            if len(self._active_lap_frames) % 500 == 1:  # Log on frames 1, 501, 1001, etc.
                pending_status = f" (pending timing for lap {self._pending_lap_completion['lap_number']})" if self._pending_lap_completion else ""
                logger.debug(f"[LapIndexer] Frame {len(self._active_lap_frames)} → Lap {self._active_lap_number_internal} (iRacing driving: {current_lap_driving_sdk}, completed: {current_lap_completed_sdk}){pending_status}")
        
        # The LapInvalidated flag in ir_data applies to the current driving lap.
        # Since we're now tracking the driving lap correctly, this should work properly.
        if lap_invalidated_flag_now:
            if not self._active_lap_invalid_sdk: # Log only on first sight for this lap
                 logger.info(f"[LapIndexer] Lap {self._active_lap_number_internal} (driving lap {current_lap_driving_sdk}) marked invalid by SDK")
            self._active_lap_invalid_sdk = True

        # --- Final Validation & State Update ---
        # Enhanced validation after all processing
        # Our internal lap should now match the lap we're currently driving
        if self._active_lap_number_internal is not None:
            expected_tracking_lap = current_lap_driving_sdk  # Simplified: track what we're driving
            
            if self._active_lap_number_internal != expected_tracking_lap:
                # Rate limit validation logging to prevent spam
                current_time = time.time()
                should_log_validation = not hasattr(self, '_last_validation_log_time_corrected') or (current_time - getattr(self, '_last_validation_log_time_corrected', 0) > 5.0)
                
                if should_log_validation:
                    logger.warning(f"[LapIndexer] 🚨 CRITICAL SYNC ISSUE: Tracking lap {self._active_lap_number_internal} != expected lap {expected_tracking_lap}")
                    logger.warning(f"[LapIndexer] 🚨 SYNC CONTEXT: iRacing LapCompleted={current_lap_completed_sdk}, Driving={current_lap_driving_sdk}")
                    
                    # Log frame analysis for debugging
                    frames_collected = len(self._active_lap_frames) if self._active_lap_frames else 0
                    logger.warning(f"[LapIndexer] 🚨 SYNC STATE: {frames_collected} frames collected for internal lap {self._active_lap_number_internal}")
                    self._last_validation_log_time_corrected = current_time
                
                # Force synchronization when we're clearly off
                frames_collected = len(self._active_lap_frames) if self._active_lap_frames else 0
                
                # If we have substantial data but are out of sync, force correction
                if frames_collected > 10:
                    logger.error(f"[LapIndexer] 🔧 SYNC CORRECTION: Forcing sync from {self._active_lap_number_internal} to {expected_tracking_lap}")
                    self._active_lap_number_internal = expected_tracking_lap
            else:
                # Perfect sync - log occasionally for confirmation
                current_time = time.time()
                should_log_sync_success = not hasattr(self, '_last_sync_success_log_time') or (current_time - getattr(self, '_last_sync_success_log_time', 0) > 30.0)
                
                if should_log_sync_success:
                    logger.debug(f"[LapIndexer] ✅ PERFECT SYNC: Tracking lap {self._active_lap_number_internal} matches expected lap {expected_tracking_lap}")
                    self._last_sync_success_log_time = current_time
        
        # --- Update State for Next Iteration ---
        self._last_lap_completed_sdk = current_lap_completed_sdk
        self._previous_frame_ir_data = frame_copy

    def _start_new_lap(
        self,
        lap_number_internal: int, # This is ir["LapCompleted"] value at the moment this lap physically starts
        start_tick: float,
        on_pit_start: bool,
        invalid_sdk_flag_for_this_lap: bool, # ir["LapInvalidated"] status for this new lap
        initial_lap_dist_pct: float = None, # Optional initial lap distance for classification
        is_mid_session_join: bool = False # Whether we're joining mid-session
    ) -> None:
        # Prevent truly invalid lap numbers (negative values)
        # Note: lap_number_internal of 0 is valid in iRacing (it's the outlap)
        if lap_number_internal < 0:
            logger.warning(f"[LapIndexer] Refusing to start invalid lap number {lap_number_internal}")
            return
            
        self._active_lap_frames = []
        self._active_lap_number_internal = lap_number_internal
        self._active_lap_start_tick = start_tick
        self._active_lap_invalid_sdk = invalid_sdk_flag_for_this_lap # Initial invalid state for this lap
        self._active_lap_started_on_pit = on_pit_start

        # Enhanced lap state classification with detailed logging
        logger.info(f"[LapIndexer] Classifying lap {lap_number_internal}: on_pit_start={on_pit_start}, "
                   f"is_mid_session_join={is_mid_session_join}, initial_lap_dist_pct={initial_lap_dist_pct}")

        # Determine lap state based on starting conditions and initial position
        if is_mid_session_join:
            # Mid-session join classification based on actual conditions
            # If we're on pit road OR starting at significant distance, it's likely an OUT lap
            if on_pit_start or (initial_lap_dist_pct is not None and initial_lap_dist_pct > 0.1):
                self._active_lap_state = LapState.OUT
                logger.info(f"[LapIndexer] 🎯 Lap {lap_number_internal} classified as OUT (mid-session join: on_pit={on_pit_start}, dist={initial_lap_dist_pct:.3f})")
            else:
                self._active_lap_state = LapState.TIMED
                logger.info(f"[LapIndexer] 🔧 Lap {lap_number_internal} classified as TIMED (mid-session join at {initial_lap_dist_pct:.3f})")
        elif on_pit_start and lap_number_internal == 0:
            # Only classify as OUT if it's truly lap 0 (the actual outlap)
            self._active_lap_state = LapState.OUT
            logger.info(f"[LapIndexer] ✅ Lap {lap_number_internal} classified as OUT (true outlap - lap 0)")
        elif on_pit_start:
            # For other laps starting on pit road, let iRacing decide via lap time
            self._active_lap_state = LapState.TIMED
            logger.info(f"[LapIndexer] 🔧 Lap {lap_number_internal} classified as TIMED (starting on pit road, will recheck with iRacing)")
        elif initial_lap_dist_pct is not None and initial_lap_dist_pct > 0.5:
            # If we're starting in the second half of the track, consider it a partial lap
            self._active_lap_state = LapState.INCOMPLETE
            logger.info(f"[LapIndexer] ✅ Lap {lap_number_internal} classified as INCOMPLETE due to starting at {initial_lap_dist_pct:.3f}")
        else:
            # Otherwise it's a normal TIMED lap
            self._active_lap_state = LapState.TIMED
            logger.info(f"[LapIndexer] ✅ Lap {lap_number_internal} classified as TIMED (normal racing lap)")
        
        # Additional validation: If lap 0, it should always be OUT regardless of other factors
        if lap_number_internal == 0 and self._active_lap_state != LapState.OUT:
            logger.info(f"[LapIndexer] Lap 0 reclassified from {self._active_lap_state.name} to OUT (lap 0 is always outlap)")
            self._active_lap_state = LapState.OUT
        
        logger.info(f"[LapIndexer] Starting new lap data collection. LapInternalNum: {self._active_lap_number_internal}, "
                    f"Type: {self._active_lap_state.name}, StartTick: {start_tick:.3f}, OnPitStart: {on_pit_start}, "
                    f"InitialSDKInvalid: {invalid_sdk_flag_for_this_lap}")

    def _finalize_stored_lap_with_timing(self, stored_lap_data: Dict[str, Any], updated_lap_time: float) -> None:
        """Process a stored lap with updated timing information after the 3-second delay.
        
        Args:
            stored_lap_data: Pre-stored lap data from when completion was detected
            updated_lap_time: Updated lap time from CarIdxLastLapTime after delay
        """
        lap_number = stored_lap_data['lap_number']
        telemetry_frames = stored_lap_data['telemetry_frames']
        start_tick = stored_lap_data['start_tick']
        end_tick = stored_lap_data['end_tick']
        ended_on_pit_road = stored_lap_data['ended_on_pit_road']
        started_on_pit_road = stored_lap_data['started_on_pit_road']
        lap_state = stored_lap_data['lap_state']
        invalid_sdk = stored_lap_data['invalid_sdk']
        
        logger.info(f"[LapIndexer] 🎯 PROCESSING STORED LAP: Lap {lap_number} with {len(telemetry_frames)} frames")
        
        # Validate timing data before calculation
        if start_tick is None or end_tick is None:
            logger.error(f"[LapIndexer] ❌ Invalid timing data for lap {lap_number}: start_tick={start_tick}, end_tick={end_tick}")
            logger.error(f"[LapIndexer] ❌ Skipping lap processing due to invalid timing data")
            return
        
        # Calculate our timing for comparison
        calculated_duration = end_tick - start_tick
        
        # Log comprehensive timing analysis
        logger.info(f"[RELIABLE TIMING] 🎯 LAP {lap_number} TIMING ANALYSIS:")
        logger.info(f"[RELIABLE TIMING]   📊 Calculated Duration: {calculated_duration:.3f}s")
        logger.info(f"[RELIABLE TIMING]   📊 CarIdxLastLapTime: {updated_lap_time:.3f}s (EXACT iRacing timing)")
        
        # Use the same timing logic as the regular finalization
        if abs(updated_lap_time) > 300:  # Extremely long times are usually session-related
            final_lap_duration = calculated_duration
            logger.info(f"[RELIABLE TIMING] 🎯 Using calculated time - iRacing time appears to be session time ({updated_lap_time:.3f}s)")
        elif updated_lap_time < 0:  # Negative times for OUT laps
            final_lap_duration = updated_lap_time
            logger.info(f"[RELIABLE TIMING] 🎯 Using iRacing negative time for OUT lap classification")
        elif updated_lap_time == 0.0:  # Zero times are incomplete
            final_lap_duration = calculated_duration
            logger.info(f"[RELIABLE TIMING] 🎯 Zero iRacing time - Using calculated time {calculated_duration:.3f}s")
        elif calculated_duration < 5.0:  # Very short calculated laps are suspicious
            final_lap_duration = updated_lap_time
            logger.warning(f"[RELIABLE TIMING] ⚠️ Calculated time very short ({calculated_duration:.3f}s), using iRacing time as fallback")
        else:
            # Normal case: Use iRacing's exact timing
            final_lap_duration = updated_lap_time
            logger.info(f"[RELIABLE TIMING] ✅ Using iRacing CarIdxLastLapTime - exact match to iRacing display")
        
        logger.info(f"[LapIndexer] 🏁 LAP {lap_number}: Using RELIABLE time {final_lap_duration:.3f}s")
        
        # Apply the same classification logic as regular finalization
        current_lap_state = lap_state
        
        logger.info(f"[CLASSIFICATION] Lap {lap_number}: Initial classification = {lap_state.name}")
        logger.info(f"[CLASSIFICATION] Lap {lap_number}: Started on pit road = {started_on_pit_road}")
        logger.info(f"[CLASSIFICATION] Lap {lap_number}: CarIdxLastLapTime = {updated_lap_time:.3f}s")
        
        # PRIORITY 1: If lap started on pit road, it's ALWAYS an OUT lap
        if started_on_pit_road:
            current_lap_state = LapState.OUT
            logger.info(f"[CLASSIFICATION] Lap {lap_number}: FORCED OUT - Started on pit road (overrides iRacing time)")
        else:
            # PRIORITY 2: Use iRacing's lap time for laps that didn't start on pit road
            if updated_lap_time > 0:
                current_lap_state = LapState.TIMED
                logger.info(f"[CLASSIFICATION] Lap {lap_number}: Confirmed TIMED (iRacing positive time {updated_lap_time:.3f}s)")
            elif updated_lap_time < 0:
                current_lap_state = LapState.OUT
                logger.info(f"[CLASSIFICATION] Lap {lap_number}: Confirmed OUT (iRacing negative time {updated_lap_time:.3f}s)")
            else:
                current_lap_state = LapState.INCOMPLETE
                logger.info(f"[CLASSIFICATION] Lap {lap_number}: INCOMPLETE (iRacing zero time)")
        
        logger.info(f"[CLASSIFICATION DEBUG] 🔍 LAP {lap_number} PRIORITY-BASED CLASSIFICATION:")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Initial Classification: {lap_state.name}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Started on Pit Road: {started_on_pit_road}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 CarIdxLastLapTime: {updated_lap_time:.3f}s")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Classification Priority: {'Pit road start' if started_on_pit_road else 'CarIdxLastLapTime'}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Final Classification: {current_lap_state.name}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Based on pit road priority: {started_on_pit_road}")
        
        logger.info(f"[LapIndexer] 🏁 Lap {lap_number} using final state: {current_lap_state.name}")
        
        # Create the lap dictionary
        is_lap_valid_according_to_sdk = not invalid_sdk
        is_valid_for_leaderboard = (current_lap_state == LapState.TIMED and is_lap_valid_according_to_sdk)
        
        lap_dict = {
            "lap_number_sdk": lap_number,
            "lap_state": current_lap_state.name,
            "start_tick": start_tick,
            "end_tick": end_tick,
            "duration_seconds": final_lap_duration,
            "telemetry_frames": telemetry_frames,
            "is_valid_from_sdk": is_lap_valid_according_to_sdk,
            "is_valid_for_leaderboard": is_valid_for_leaderboard,
            "started_on_pit_road": started_on_pit_road,
            "ended_on_pit_road": ended_on_pit_road,
            "is_complete_by_sdk_increment": True,
            "is_incomplete_session_end": False,
            "calculated_duration": calculated_duration,
            "frame_count": len(telemetry_frames),
        }
        
        # Save the lap immediately
        self._save_lap_immediately(lap_dict)
        
        # Also maintain local laps list for backward compatibility
        self.laps.append(lap_dict)
        
        logger.info(f"[LapIndexer] ✅ LAP {lap_number} SAVED: {current_lap_state.name}, {final_lap_duration:.3f}s, {len(telemetry_frames)} frames")

    def _finalise_active_lap(
        self,
        end_tick: float,
        lap_last_lap_time_from_sdk: float,
        ended_on_pit_road: bool,
        session_finalize: bool, # True if called from session shutdown
        current_lap_completed_sdk: int = None  # Add this parameter
    ) -> None:
        if self._active_lap_number_internal is None or self._active_lap_start_tick is None or not self._active_lap_frames:
            logger.warning("[LapIndexer] Attempted to finalize lap but active lap state is incomplete or has no frames.")
            return

        # Initialize calculated_duration as fallback
        calculated_duration = 0.0
        
        # Save the lap with the CORRECT lap number from iRacing
        # When LapCompleted increments, the lap that just finished should be saved with that completed lap number
        if not session_finalize and current_lap_completed_sdk is not None:
            # Use the current LapCompleted value - this is the lap that just finished
            lap_to_finalize_sdk_num = current_lap_completed_sdk
            logger.info(f"[LapIndexer] 🎯 SAVING: Lap {lap_to_finalize_sdk_num} (iRacing completed lap number)")
        elif not session_finalize:
            # Fallback to internal tracking if current completed lap not provided
            lap_to_finalize_sdk_num = self._active_lap_number_internal  
            logger.info(f"[LapIndexer] 🎯 SAVING: Lap {lap_to_finalize_sdk_num} (fallback - no current completed)")
        else:
            # Fallback to internal tracking for session finalization
            lap_to_finalize_sdk_num = self._active_lap_number_internal
            logger.info(f"[LapIndexer] 🎯 SAVING: Lap {lap_to_finalize_sdk_num} (internal tracking - session end)")
        
        # RELIABLE TIMING STRATEGY: Use calculated duration as primary (proven most accurate)
        # With validation and smart fallbacks for edge cases
        if not session_finalize and lap_last_lap_time_from_sdk != 0:
            # Validate timing data before calculation
            if self._active_lap_start_tick is None:
                logger.error(f"[LapIndexer] ❌ Invalid start_tick for lap {lap_to_finalize_sdk_num}: {self._active_lap_start_tick}")
                calculated_duration = 0.0
            else:
                # Calculate our timing (proven to match iRacing display perfectly)
                calculated_duration = end_tick - self._active_lap_start_tick
            
            # Get iRacing's timing variables for comparison
            iracing_last_time = lap_last_lap_time_from_sdk
            
            # Log comprehensive timing analysis
            logger.info(f"[RELIABLE TIMING] 🎯 LAP {lap_to_finalize_sdk_num} TIMING ANALYSIS:")
            logger.info(f"[RELIABLE TIMING]   📊 Calculated Duration: {calculated_duration:.3f}s")
            logger.info(f"[RELIABLE TIMING]   📊 CarIdxLastLapTime: {iracing_last_time:.3f}s (EXACT iRacing timing)")
            
            # STRATEGY: Use CarIdxLastLapTime as primary (it's the most accurate iRacing timing)
            # Only use calculated timing for special cases or validation
            if abs(iracing_last_time) > 300:  # Extremely long times are usually session-related, not lap times
                logger.info(f"[RELIABLE TIMING] 🎯 Using calculated time - iRacing time appears to be session time ({iracing_last_time:.3f}s)")
                final_lap_duration = calculated_duration
            elif iracing_last_time < 0:  # Negative times for OUT laps
                logger.info(f"[RELIABLE TIMING] 🎯 Using iRacing negative time for OUT lap classification")
                final_lap_duration = iracing_last_time
            elif iracing_last_time == 0.0:  # Zero times are incomplete
                logger.info(f"[RELIABLE TIMING] 🎯 Zero iRacing time - Using calculated time {calculated_duration:.3f}s")
                final_lap_duration = calculated_duration
            elif calculated_duration < 5.0:  # Very short calculated laps are suspicious
                logger.warning(f"[RELIABLE TIMING] ⚠️ Calculated time very short ({calculated_duration:.3f}s), using iRacing time as fallback")
                final_lap_duration = iracing_last_time
            else:
                # Normal case: Use iRacing's exact timing (CarIdxLastLapTime)
                final_lap_duration = iracing_last_time
                logger.info(f"[RELIABLE TIMING] ✅ Using iRacing CarIdxLastLapTime - exact match to iRacing display")
                
                # Log difference for analysis
                time_difference = abs(calculated_duration - iracing_last_time)
                if time_difference > 0.1:  # More than 100ms difference
                    logger.info(f"[RELIABLE TIMING] 📊 Timing comparison: iRacing={iracing_last_time:.3f}s, Calculated={calculated_duration:.3f}s, Diff={time_difference:.3f}s")
            
            logger.info(f"[LapIndexer] 🏁 LAP {lap_to_finalize_sdk_num}: Using RELIABLE time {final_lap_duration:.3f}s")
        
        elif not session_finalize and lap_last_lap_time_from_sdk == 0:
            # Zero time from iRacing - use calculated time
            if self._active_lap_start_tick is None:
                logger.error(f"[LapIndexer] ❌ Invalid start_tick for lap {lap_to_finalize_sdk_num}: {self._active_lap_start_tick}")
                calculated_duration = 0.0
            else:
                calculated_duration = end_tick - self._active_lap_start_tick
            final_lap_duration = calculated_duration
            logger.info(f"[RELIABLE TIMING] 🎯 Zero iRacing time - Using calculated time {final_lap_duration:.3f}s")
        
        else:
            # Session finalization or when iRacing time is not available
            if self._active_lap_start_tick is None:
                logger.error(f"[LapIndexer] ❌ Invalid start_tick for lap {lap_to_finalize_sdk_num}: {self._active_lap_start_tick}")
                calculated_duration = 0.0
            else:
                calculated_duration = end_tick - self._active_lap_start_tick
            final_lap_duration = calculated_duration
            if session_finalize:
                logger.info(f"[RELIABLE TIMING] 🎯 Session finalization - Using calculated time {final_lap_duration:.3f}s")
            else:
                logger.info(f"[RELIABLE TIMING] 🎯 iRacing time unavailable - Using calculated time {final_lap_duration:.3f}s")
        
        logger.debug(f"[LapIndexer] Final lap time for lap {lap_to_finalize_sdk_num}: {final_lap_duration:.3f}s")
        
        # CLASSIFICATION FIX: Prioritize pit road start condition over iRacing's lap time
        # If a lap starts on pit road, it should ALWAYS be an OUT lap
        
        # Start with our initial classification for context
        initial_classification = self._active_lap_state
        current_lap_state = self._active_lap_state
        
        # Log our initial classification decision
        logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: Initial classification = {initial_classification.name}")
        logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: Started on pit road = {self._active_lap_started_on_pit}")
        logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: CarIdxLastLapTime = {lap_last_lap_time_from_sdk:.3f}s")
        
        # PRIORITY 1: If lap started on pit road, it's ALWAYS an OUT lap
        if self._active_lap_started_on_pit:
            current_lap_state = LapState.OUT
            logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: FORCED OUT - Started on pit road (overrides iRacing time)")
        elif not session_finalize:
            # PRIORITY 2: Use iRacing's lap time only for laps that didn't start on pit road
            if lap_last_lap_time_from_sdk > 0:
                # Positive time = TIMED lap (normal racing lap)
                current_lap_state = LapState.TIMED
                if initial_classification != LapState.TIMED:
                    logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: {initial_classification.name} → TIMED (iRacing positive time {lap_last_lap_time_from_sdk:.3f}s)")
                else:
                    logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: Confirmed TIMED (iRacing positive time {lap_last_lap_time_from_sdk:.3f}s)")
            elif lap_last_lap_time_from_sdk < 0:
                # Negative time = OUT lap (pit exit, invalid lap, etc.)
                current_lap_state = LapState.OUT
                if initial_classification != LapState.OUT:
                    logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: {initial_classification.name} → OUT (iRacing negative time {lap_last_lap_time_from_sdk:.3f}s)")
                else:
                    logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: Confirmed OUT (iRacing negative time {lap_last_lap_time_from_sdk:.3f}s)")
            else:
                # Zero time = INCOMPLETE lap (session ended, disconnected, etc.)
                current_lap_state = LapState.INCOMPLETE
                logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: {initial_classification.name} → INCOMPLETE (iRacing zero time)")
        else:
            # Session finalization - mark as INCOMPLETE
            current_lap_state = LapState.INCOMPLETE
            logger.info(f"[CLASSIFICATION] Lap {lap_to_finalize_sdk_num}: INCOMPLETE - Session ended")
        
        # Log classification with full context
        logger.info(f"[CLASSIFICATION DEBUG] 🔍 LAP {lap_to_finalize_sdk_num} PRIORITY-BASED CLASSIFICATION:")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Initial Classification: {initial_classification.name}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Started on Pit Road: {self._active_lap_started_on_pit}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 CarIdxLastLapTime: {lap_last_lap_time_from_sdk:.3f}s")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Classification Priority: {'Pit road start' if self._active_lap_started_on_pit else 'CarIdxLastLapTime'}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Final Classification: {current_lap_state.name}")
        logger.info(f"[CLASSIFICATION DEBUG]   📊 Based on pit road priority: {self._active_lap_started_on_pit}")
        
        # Apply session finalization reclassification if needed
        if session_finalize and current_lap_state == LapState.TIMED:
            current_lap_state = LapState.INCOMPLETE
            logger.info(f"[LapIndexer] 🏁 Lap {lap_to_finalize_sdk_num} reclassified: TIMED → INCOMPLETE (Session ended)")
        
        # Final classification log
        logger.info(f"[LapIndexer] 🏁 Lap {lap_to_finalize_sdk_num} using final state: {current_lap_state.name}")
        
        # Log final validation status
        is_leaderboard_lap = current_lap_state == LapState.TIMED and not self._active_lap_invalid_sdk

        # Validity: is_valid_from_sdk is true if self._active_lap_invalid_sdk remained false throughout the lap.
        is_lap_valid_according_to_sdk = not self._active_lap_invalid_sdk
        is_valid_for_leaderboard = (current_lap_state == LapState.TIMED and is_lap_valid_according_to_sdk)

        lap_dict = {
            "lap_number_sdk": lap_to_finalize_sdk_num, # This is the ir["LapCompleted"] value for the lap
            "lap_state": current_lap_state.name,
            "start_tick": self._active_lap_start_tick,
            "end_tick": end_tick,
            "duration_seconds": final_lap_duration,
            "telemetry_frames": list(self._active_lap_frames), # Store a copy
            "is_valid_from_sdk": is_lap_valid_according_to_sdk, # Based on ir["LapInvalidated"] during the lap
            "is_valid_for_leaderboard": is_valid_for_leaderboard,
            "started_on_pit_road": self._active_lap_started_on_pit,
            "ended_on_pit_road": ended_on_pit_road,
            # Context flags for IRacingLapSaver
            "is_complete_by_sdk_increment": not session_finalize,
            "is_incomplete_session_end": session_finalize,
            "calculated_duration": calculated_duration, # Store calculated time for reference
            "frame_count": len(self._active_lap_frames), # Store frame count for debugging
        }
        
        # IMMEDIATE SAVE: Save lap data immediately when lap completes
        # This eliminates the N+1 dependency and lag issues
        self._save_lap_immediately(lap_dict)
        
        # Also maintain local laps list for backward compatibility
        # The immediate save handles Supabase persistence, but we need local list for get_laps()
        self.laps.append(lap_dict)
        
        # ONLY LOG CRITICAL LAP COMPLETION EVENTS, NOT DETAILS
        logger.info(f"[LapIndexer] ✅ LAP {lap_to_finalize_sdk_num} SAVED: {current_lap_state.name}, {final_lap_duration:.3f}s, {len(self._active_lap_frames)} frames")

    def finalize(self) -> None:
        """Call once at session end to flush the current lap."""
        logger.info("[LapIndexer] Session finalize() called.")
        if self._active_lap_number_internal is not None and self._active_lap_frames:
            logger.info(f"[LapIndexer] Processing active lap {self._active_lap_number_internal} during session finalize.")
            
            # Use the last available frame's data for timing and state
            last_frame = self._active_lap_frames[-1]
            end_tick = float(last_frame.get("SessionTimeSecs", self._active_lap_start_tick or 0))
            
            # CarIdxLastLapTime is unlikely to be relevant or correct for a lap interrupted by session end
            lap_last_lap_time_from_sdk = -1.0
            
            # Handle gracefully if OnPitRoad is missing in the last frame
            ended_on_pit_road = False
            if "OnPitRoad" in last_frame:
                ended_on_pit_road = bool(last_frame.get("OnPitRoad", False))
            else:
                logger.info("[LapIndexer] 'OnPitRoad' key missing in last frame during session finalize, using default: False")

            self._finalise_active_lap(
                end_tick=end_tick,
                lap_last_lap_time_from_sdk=lap_last_lap_time_from_sdk, # Will likely use calculated duration
                ended_on_pit_road=ended_on_pit_road,
                session_finalize=True,
                current_lap_completed_sdk=None  # Session finalization - no specific completed lap
            )
        else:
            logger.info("[LapIndexer] No active lap data to process during session finalize.")

        # IMMEDIATE SAVE: Wait for any pending saves to complete
        if self._save_worker_running:
            logger.info("[LapIndexer] 💾 Waiting for pending lap saves to complete...")
            # Wait for queue to empty
            self._immediate_save_queue.join()
            logger.info("[LapIndexer] ✅ All pending saves completed")
        
        # Stop the save worker
        self.stop_save_worker()

        # Store a copy of the laps before resetting state
        self._finalized_laps = list(self.laps)
        
        # Reset all internal state for potential reuse or clean shutdown
        # Note: We don't clear self.laps here anymore to ensure get_laps() works correctly
        # even after finalize() is called. Instead, we set _is_finalized flag.
        self._is_finalized = True
        
        self._active_lap_frames = []
        self._active_lap_number_internal = None
        self._active_lap_start_tick = None
        self._active_lap_invalid_sdk = False
        self._active_lap_started_on_pit = False
        self._active_lap_state = LapState.INCOMPLETE
        self._last_lap_completed_sdk = None
        self._previous_frame_ir_data = None
        self._pending_lap_completion = None  # Clear pending completion
        logger.info("[LapIndexer] Internal state reset, but lap data preserved.")

    def get_laps(self) -> List[Dict[str, Any]]:
        """Return a deep copy of all finalized laps.
        
        🚨 DEPRECATION WARNING: This polling-based method is deprecated!
        Use set_immediate_save_callback() for real-time lap processing instead.
        """
        import copy
        
        # Deprecation warning for polling-based lap retrieval
        current_time = time.time()
        should_log_deprecation = not hasattr(self, '_last_deprecation_warning_time') or (current_time - getattr(self, '_last_deprecation_warning_time', 0) > 60.0)
        
        if should_log_deprecation:
            logger.warning(f"[LapIndexer] 🚨 DEPRECATED: get_laps() polling is deprecated! "
                          f"Use set_immediate_save_callback() for immediate lap processing instead.")
            logger.warning(f"[LapIndexer] 📚 See immediate_save_integration_guide.md for migration instructions")
            self._last_deprecation_warning_time = current_time
        
        # Log regular usage (reduced frequency)
        should_log_usage = not hasattr(self, '_last_get_laps_log_time') or (current_time - getattr(self, '_last_get_laps_log_time', 0) > 300.0)
        if should_log_usage:
            logger.info(f"[LapIndexer] get_laps() called, returning {len(self.laps)} laps.")
            self._last_get_laps_log_time = current_time
                
        return copy.deepcopy(self.laps)
        
    def reset(self) -> None:
        """Explicitly reset the LapIndexer state including lap data.
        This should be called when starting a new session if reusing the same LapIndexer instance.
        """
        logger.info("[LapIndexer] Explicitly resetting all state including lap data.")
        
        # Stop the save worker first
        self.stop_save_worker()
        
        # Reset all state
        self.laps = []
        self._finalized_laps = []
        self._is_finalized = False
        self._active_lap_frames = []
        self._active_lap_number_internal = None
        self._active_lap_start_tick = None
        self._active_lap_invalid_sdk = False
        self._active_lap_started_on_pit = False
        self._active_lap_state = LapState.INCOMPLETE
        self._last_lap_completed_sdk = None
        self._previous_frame_ir_data = None
        self._pending_lap_completion = None  # Clear pending completion
        
        logger.info("[LapIndexer] ✅ Complete reset including immediate save system")