# lap_indexer.py
"""
Absolute-truth lap indexer for TrackPro.

This module relies *exclusively* on iRacing's own lap counters:
  • ir["LapCompleted"]      – integer, increases when a lap is fully scored
  • ir["Lap"]               – current live lap index ( = LapCompleted + 1 )
  • ir["LapLastLapTime"]    – time of the lap that just finished
  • ir["LapInvalidated"]    – flag, 1 if the *current* lap will be invalid
  • ir["OnPitRoad"]         – informational only

Behaviour:
  • Out-lap = LapCompleted == 0 at the start of the lap.
  • New lap boundary when LapCompleted increments.
  • Lap time taken from LapLastLapTime of the frame where LapCompleted increments.
  • Stores every telemetry frame inside its lap bucket.
"""

from __future__ import annotations
from typing import Dict, List, Any
from enum import Enum, auto
import logging
import time

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
        self._active_lap_number_internal: int | None = None # Stores ir["LapCompleted"] value at START of this lap
        self._active_lap_start_tick: float | None = None
        self._active_lap_invalid_sdk: bool = False # True if ir["LapInvalidated"] was seen during this lap
        self._active_lap_started_on_pit: bool = False
        self._active_lap_state: LapState = LapState.INCOMPLETE

        # SDK state from the PREVIOUS telemetry frame
        self._last_lap_completed_sdk: int | None = None
        self._previous_frame_ir_data: Dict[str, Any] | None = None
        
        # Rate limiting for warnings
        self._last_sdk_data_warning_time: float = 0.0
        self._last_sdk_data_warning_message: str = ""
        self._warning_interval: float = 5.0  # seconds
        
        # Previous lap distance to detect wrap-around and resets
        self._previous_lap_dist_pct: float = -1.0
        self._previous_speed: float = 0.0
        
        # Variables to prevent double wrap-around detection
        self._last_wrap_around_time: float = 0.0
        self._wrap_around_cooldown: float = 2.0  # seconds
        
        # Early boundary detection to capture lap starts better
        self._approaching_boundary: bool = False
        self._boundary_approach_threshold: float = 0.95  # Start watching when we reach 95% of lap
        
        # New variables for delayed lap finalization
        self._pending_wrap_around_lap: Dict[str, Any] | None = None
        self._pending_wrap_around_lap_frames: List[Dict[str, Any]] = []
        self._recently_started_by_wrap_around: bool = False
        self._wrap_around_start_time: float = 0.0
        
        # New lap debug tracking system
        self._lap_debug_tracker: Dict[int, Dict[str, Any]] = {}
        self._iracing_to_internal_lap_mapping: Dict[int, int] = {}

    def _log_sdk_warning(self, message: str):
        current_time = time.time()
        if (current_time - self._last_sdk_data_warning_time > self._warning_interval or
            message != self._last_sdk_data_warning_message):
            logger.warning(message)
            self._last_sdk_data_warning_time = current_time
            self._last_sdk_data_warning_message = message

    def _log_lap_debug_info(self, event_type: str, ir_data: Dict[str, Any], message: str = "") -> None:
        """Log detailed lap debugging information to track iRacing vs internal lap numbers.
        
        Args:
            event_type: Type of event (e.g., 'WRAPAROUND', 'INCREMENT', 'NEW_LAP', 'FINALIZE')
            ir_data: Current iRacing telemetry data
            message: Optional additional debug message
        """
        # Extract key data from iRacing frame
        ir_lap = ir_data.get("Lap", -1)  # Current lap (N+1)
        ir_lap_completed = ir_data.get("LapCompleted", -1)  # Last completed lap (N)
        lap_dist_pct = ir_data.get("LapDistPct", -1.0)
        on_pit_road = ir_data.get("OnPitRoad", False)
        lap_invalidated = ir_data.get("LapInvalidated", False)
        session_time = ir_data.get("SessionTimeSecs", 0.0)
        
        # Get internal state
        internal_lap_num = self._active_lap_number_internal
        lap_state = self._active_lap_state.name if self._active_lap_state else "NONE"
        
        # Create debug entry
        debug_entry = {
            "timestamp": time.time(),
            "session_time": session_time,
            "event_type": event_type,
            "iracing_lap": ir_lap,
            "iracing_lap_completed": ir_lap_completed,
            "internal_lap_num": internal_lap_num,
            "lap_state": lap_state,
            "lap_dist_pct": lap_dist_pct,
            "on_pit_road": on_pit_road,
            "lap_invalidated": lap_invalidated,
            "message": message
        }
        
        # Track the mapping between iRacing laps and internal laps
        if internal_lap_num is not None:
            self._iracing_to_internal_lap_mapping[ir_lap_completed] = internal_lap_num
        
        # Store in debug tracker
        if internal_lap_num not in self._lap_debug_tracker:
            self._lap_debug_tracker[internal_lap_num or -1] = []
        
        self._lap_debug_tracker[internal_lap_num or -1].append(debug_entry)
        
        # Log the debug information
        mapping_info = f"iRacing#{ir_lap_completed}→Internal#{internal_lap_num}" if internal_lap_num is not None else "No mapping"
        log_message = (
            f"[LAP DEBUG] {event_type} - {mapping_info} - "
            f"iRacing state: Lap={ir_lap}, LapCompleted={ir_lap_completed}, "
            f"LapDistPct={lap_dist_pct:.3f}, OnPit={on_pit_road}, Invalid={lap_invalidated} - "
            f"Internal state: Current={internal_lap_num}, State={lap_state}"
        )
        
        if message:
            log_message += f" - {message}"
            
        logger.info(log_message)

    def on_frame(self, ir_data: Dict[str, Any]) -> None:
        """Process one telemetry frame from iRacing."""
        # --- Validate and Extract Key SDK Data ---
        try:
            now_tick = float(ir_data["SessionTimeSecs"])
            current_lap_completed_sdk = int(ir_data["LapCompleted"])
            # current_lap_driving_sdk = int(ir_data["Lap"]) # Lap player is currently on
            lap_last_lap_time_sdk = float(ir_data["LapLastLapTime"]) # Time of the lap that just finished
            
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
            
            # Determine if this is a mid-session join by checking LapCompleted
            # If it's not 0, we've joined an ongoing session and need to set lap state accordingly
            is_mid_session_join = current_lap_completed_sdk > 0
            
            self._start_new_lap(
                lap_number_internal=current_lap_completed_sdk, # Starts at 0 for the out-lap
                start_tick=now_tick,
                on_pit_start=on_pit_road_now,
                # LapInvalidated refers to ir["Lap"], which is current_lap_completed_sdk + 1 here.
                # So, this flag is for the lap we are *just starting*.
                invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now,
                # Pass initial lap distance for correct classification on first frame
                initial_lap_dist_pct=current_lap_dist_pct_initial,
                is_mid_session_join=is_mid_session_join
            )
            self._active_lap_frames.append(frame_copy)
            self._last_lap_completed_sdk = current_lap_completed_sdk
            self._previous_frame_ir_data = frame_copy
            
            # Initialize previous values for wrap-around and reset detection
            self._previous_lap_dist_pct = frame_copy.get("LapDistPct", 0.0)
            self._previous_speed = frame_copy.get("Speed", 0.0)
            
            # Log initial lap state for debugging
            self._log_lap_debug_info("INITIALIZE", frame_copy, "First frame initialization")
            return

        # Get current lap distance to check for wrap-around
        current_lap_dist = float(frame_copy.get("LapDistPct", 0.0))
        current_speed = float(frame_copy.get("Speed", 0.0))

        # --- Main Lap Transition Logic ---
        # Check if ir["LapCompleted"] has incremented, meaning iRacing has officially scored a lap
        lap_completed_incremented = current_lap_completed_sdk > self._last_lap_completed_sdk
        
        # If we have an active lap pending after wrap-around detection and LapCompleted incremented,
        # now we have the official lap time and can finalize it properly
        if lap_completed_incremented and self._recently_started_by_wrap_around:
            logger.info(f"[LapIndexer] LapCompleted incremented after wrap-around: {self._last_lap_completed_sdk} -> {current_lap_completed_sdk}")
            
            # Sync our internal lap number with iRacing's LapCompleted
            self._active_lap_number_internal = current_lap_completed_sdk
            
            # Now we have the official lap time from iRacing for the lap we already detected via wrap-around
            # Update the most recently added lap with the correct time
            if self.laps and len(self.laps) > 0:
                last_lap = self.laps[-1]
                prev_time = last_lap.get("duration_seconds", 0)
                if prev_time > 0 and lap_last_lap_time_sdk > 0:
                    logger.info(f"[LapIndexer] Updating wrap-around lap time from {prev_time:.3f}s to SDK value {lap_last_lap_time_sdk:.3f}s")
                    last_lap["duration_seconds"] = lap_last_lap_time_sdk
                    
                    # Ensure lap number matches iRacing by using the just-completed lap number
                    last_lap["lap_number_sdk"] = current_lap_completed_sdk - 1
            
            # Clear the wrap-around flag since we've now processed the official time
            self._recently_started_by_wrap_around = False
            
            # No need to do regular lap transition handling below since we already transitioned
            # via wrap-around detection
        elif lap_completed_incremented:
            # Normal case: ir["LapCompleted"] incremented, meaning the lap whose internal number was
            # self._last_lap_completed_sdk has now officially finished.
            logger.info(f"[LapIndexer] LapCompleted incremented: {self._last_lap_completed_sdk} -> {current_lap_completed_sdk}")
            
            # Determine if the lap that just finished ended on pit road
            # This uses the OnPitRoad status from the *previous* frame, which was the last frame of that lap
            ended_on_pit = False
            if self._previous_frame_ir_data:
                # Handle gracefully if OnPitRoad was missing in previous frame too
                ended_on_pit = self._previous_frame_ir_data.get("OnPitRoad", False)

            self._finalise_active_lap(
                end_tick=now_tick,  # The current frame's time is the end of the previous lap
                lap_last_lap_time_from_sdk=lap_last_lap_time_sdk, # From current frame, for the lap that just ended
                ended_on_pit_road=ended_on_pit,
                session_finalize=False
            )

            # Start the new lap. The lap_number_internal is current_lap_completed_sdk.
            # The LapInvalidated flag (lap_invalidated_flag_now) in the current frame
            # applies to this new lap we are starting.
            self._start_new_lap(
                lap_number_internal=current_lap_completed_sdk,
                start_tick=now_tick,
                on_pit_start=on_pit_road_now,
                invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now
            )
        else:
            # No SDK lap transition, check for wrap-around or reset
            # Only do this if we're not already tracking a wrap-around transition
            if not self._recently_started_by_wrap_around:
                reset_handled = self.handle_reset(frame_copy, current_lap_dist, current_speed, on_pit_road_now)
                if not reset_handled:
                    self.close_if_needed(current_lap_dist, on_pit_road_now, now_tick, frame_copy)
                    
        # --- LAP NUMBER VALIDATION SYSTEM ---
        # Final check to ensure our internal lap number stays synchronized with iRacing
        self._validate_lap_synchronization(frame_copy)

        # --- Collect Telemetry & Update Invalidity for Active Lap ---
        self._active_lap_frames.append(frame_copy)
        
        # The LapInvalidated flag in ir_data applies to the lap ir["Lap"] (current driving lap).
        # Our self._active_lap_number_internal is ir["LapCompleted"] from the *start* of this lap.
        # So, if ir["Lap"] == self._active_lap_number_internal + 1, then lap_invalidated_flag_now applies to our active lap.
        # This check is implicitly handled because LapInvalidated always refers to the current *driving* lap.
        # If LapInvalidated is true at any point while we are collecting frames for _active_lap_number_internal,
        # then _active_lap_invalid_sdk should become true.
        if lap_invalidated_flag_now:
            if not self._active_lap_invalid_sdk: # Log only on first sight for this lap
                 logger.info(f"[LapIndexer] Lap {self._active_lap_number_internal} (driving as {ir_data.get('Lap', -1)}) marked invalid by SDK in this frame.")
            self._active_lap_invalid_sdk = True

        # --- Update State for Next Iteration ---
        self._last_lap_completed_sdk = current_lap_completed_sdk
        self._previous_frame_ir_data = frame_copy
        self._previous_lap_dist_pct = current_lap_dist
        self._previous_speed = current_speed
        
    def _validate_lap_synchronization(self, frame_copy: Dict[str, Any]) -> None:
        """Validate that our internal lap numbering stays synchronized with iRacing.
        
        This method catches edge cases where lap numbers can drift apart and corrects them.
        """
        if self._active_lap_number_internal is None:
            return
            
        iracing_lap = frame_copy.get("Lap", 0)
        iracing_completed = frame_copy.get("LapCompleted", 0)
        
        # Calculate what iRacing thinks the current lap should be
        expected_current_lap = iracing_completed + 1
        
        # Our internal lap should generally match iRacing's LapCompleted
        # but we need to handle cases where they diverge
        
        # Case 1: Our internal lap is significantly behind iRacing's completed count
        if self._active_lap_number_internal < iracing_completed - 1:
            logger.warning(f"[LAP SYNC] Internal lap {self._active_lap_number_internal} is behind iRacing completed {iracing_completed}")
            logger.info(f"[LAP SYNC] Syncing internal lap to {iracing_completed} to match iRacing")
            self._active_lap_number_internal = iracing_completed
            
        # Case 2: Our internal lap is ahead of what iRacing thinks should be completed
        elif self._active_lap_number_internal > iracing_completed + 1:
            logger.warning(f"[LAP SYNC] Internal lap {self._active_lap_number_internal} is ahead of iRacing completed {iracing_completed}")
            logger.info(f"[LAP SYNC] Adjusting internal lap to {iracing_completed} to match iRacing")
            self._active_lap_number_internal = iracing_completed
            
        # Case 3: Check consistency with iRacing's current driving lap
        # The driving lap (ir["Lap"]) should be our internal lap + 1 in most cases
        if (iracing_lap > 0 and 
            self._active_lap_number_internal is not None and 
            abs(iracing_lap - (self._active_lap_number_internal + 1)) > 1):
            
            logger.info(f"[LAP SYNC] Potential driving lap inconsistency: "
                       f"iRacing driving lap {iracing_lap}, internal lap {self._active_lap_number_internal}")
            
            # If the inconsistency is large, sync with iRacing's completed count
            if abs(iracing_lap - (self._active_lap_number_internal + 1)) > 2:
                logger.warning(f"[LAP SYNC] Large driving lap inconsistency detected, syncing with iRacing completed count")
                self._active_lap_number_internal = iracing_completed

    def _start_new_lap(
        self,
        lap_number_internal: int, # This is ir["LapCompleted"] value at the moment this lap physically starts
        start_tick: float,
        on_pit_start: bool,
        invalid_sdk_flag_for_this_lap: bool, # ir["LapInvalidated"] status for this new lap
        initial_lap_dist_pct: float = None, # Optional initial lap distance for classification
        is_mid_session_join: bool = False # Whether we're joining mid-session
    ) -> None:
        # CRITICAL BUG FIX: Prevent truly invalid lap numbers (negative values)
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
        if on_pit_start:
            # If we're starting on pit road, it's an OUT lap
            self._active_lap_state = LapState.OUT
            logger.info(f"[LapIndexer] Lap {lap_number_internal} classified as OUT due to starting on pit road")
        elif is_mid_session_join:
            # If we're joining mid-session, consider it INCOMPLETE unless it's on pit road
            self._active_lap_state = LapState.INCOMPLETE
            logger.info(f"[LapIndexer] Lap {lap_number_internal} classified as INCOMPLETE due to mid-session join")
        elif initial_lap_dist_pct is not None and initial_lap_dist_pct > 0.5:
            # If we're starting in the second half of the track, consider it a partial lap
            self._active_lap_state = LapState.INCOMPLETE
            logger.info(f"[LapIndexer] Lap {lap_number_internal} classified as INCOMPLETE due to starting at {initial_lap_dist_pct:.3f}")
        else:
            # Otherwise it's a normal TIMED lap
            self._active_lap_state = LapState.TIMED
            logger.info(f"[LapIndexer] Lap {lap_number_internal} classified as TIMED (normal racing lap)")
        
        # Additional validation: If lap 0, it should always be OUT regardless of other factors
        if lap_number_internal == 0 and self._active_lap_state != LapState.OUT:
            logger.info(f"[LapIndexer] Lap 0 reclassified from {self._active_lap_state.name} to OUT (lap 0 is always outlap)")
            self._active_lap_state = LapState.OUT
            
        # Additional validation: If we're clearly not on pit road but classified as OUT, log a warning
        if not on_pit_start and self._active_lap_state == LapState.OUT and lap_number_internal > 0:
            logger.warning(f"[LapIndexer] Lap {lap_number_internal} classified as OUT but not starting on pit road - this may be incorrect")
        
        logger.info(f"[LapIndexer] Starting new lap data collection. LapInternalNum: {self._active_lap_number_internal}, "
                    f"Type: {self._active_lap_state.name}, StartTick: {start_tick:.3f}, OnPitStart: {on_pit_start}, "
                    f"InitialSDKInvalid: {invalid_sdk_flag_for_this_lap}")

    def _finalise_active_lap(
        self,
        end_tick: float,
        lap_last_lap_time_from_sdk: float,
        ended_on_pit_road: bool,
        session_finalize: bool # True if called from session shutdown
    ) -> None:
        if self._active_lap_number_internal is None or self._active_lap_start_tick is None or not self._active_lap_frames:
            logger.warning("[LapIndexer] Attempted to finalize lap but active lap state is incomplete or has no frames.")
            return

        lap_to_finalize_sdk_num = self._active_lap_number_internal # This is the LapCompleted value of the lap being finalized
        
        # Log finalization for debugging
        if self._previous_frame_ir_data:
            finalize_msg = f"Finalizing lap {lap_to_finalize_sdk_num}, SDK state: irLap={self._previous_frame_ir_data.get('Lap', -1)}, irCompleted={self._previous_frame_ir_data.get('LapCompleted', -1)}"
            self._log_lap_debug_info("FINALIZE", self._previous_frame_ir_data, finalize_msg)
        
        calculated_duration = end_tick - self._active_lap_start_tick
        final_lap_duration = calculated_duration # Default to calculated

        # Only use SDK time if it's valid (positive) and we're not in a session end
        # Special case: If this is an OUT lap or INCOMPLETE lap, prefer our calculated time
        # since iRacing may not have a valid time for these lap types
        is_timed_lap = self._active_lap_state == LapState.TIMED
        
        # For normally completed laps (not session end), prefer SDK time if valid and positive,
        # but only for TIMED laps. For OUT/IN/INCOMPLETE laps, use our calculated time.
        if not session_finalize and lap_last_lap_time_from_sdk > 0 and is_timed_lap:
            final_lap_duration = lap_last_lap_time_from_sdk
            logger.info(f"[LapIndexer] Using SDK lap time {final_lap_duration:.3f}s for lap {lap_to_finalize_sdk_num}.")
        else:
            logger.info(f"[LapIndexer] Using calculated lap time {final_lap_duration:.3f}s for lap {lap_to_finalize_sdk_num}. "
                        f"(SDK time: {lap_last_lap_time_from_sdk:.3f}s, SessionFinalize: {session_finalize}, LapType: {self._active_lap_state.name})")

        # Determine lap state
        current_lap_state = self._active_lap_state
        if not self._active_lap_started_on_pit and ended_on_pit_road:
            current_lap_state = LapState.IN
            logger.info(f"[LapIndexer] Lap {lap_to_finalize_sdk_num} reclassified as IN (StartedTrack:True, EndedPit:{ended_on_pit_road}).")
        elif session_finalize and current_lap_state != LapState.IN: # If session ends and not a clear IN lap
             current_lap_state = LapState.INCOMPLETE
             logger.info(f"[LapIndexer] Lap {lap_to_finalize_sdk_num} marked INCOMPLETE due to session finalize.")

        # Validity: is_valid_from_sdk is true if self._active_lap_invalid_sdk remained false throughout the lap.
        is_lap_valid_according_to_sdk = not self._active_lap_invalid_sdk
        is_valid_for_leaderboard = (current_lap_state == LapState.TIMED and is_lap_valid_according_to_sdk)

        # Ensure we have some telemetry frames and a positive duration to consider it a lap
        if self._active_lap_frames and final_lap_duration > 0.1: # Small threshold for duration
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
                "frame_count": len(self._active_lap_frames) # Store frame count for debugging
            }
            self.laps.append(lap_dict)
            logger.info(f"[LapIndexer] Successfully finalized lap {lap_to_finalize_sdk_num} "
                        f"({current_lap_state.name}). Time: {final_lap_duration:.3f}s, "
                        f"Frames: {len(self._active_lap_frames)}, ValidSDK: {is_lap_valid_according_to_sdk}, "
                        f"Leaderboard: {is_valid_for_leaderboard}.")
        else:
            logger.warning(f"[LapIndexer] Did NOT finalize lap {lap_to_finalize_sdk_num}. "
                           f"Reason: No. Frames: {len(self._active_lap_frames)}, Duration: {final_lap_duration:.3f}s, "
                           f"ValidSDK: {is_lap_valid_according_to_sdk}, State: {current_lap_state.name}")
        
        # active_lap_frames will be reset by _start_new_lap (if not session_finalize)
        # or by finalize() itself.

    def finalize(self) -> None:
        """Call once at session end to flush the current lap."""
        logger.info("[LapIndexer] Session finalize() called.")
        if self._active_lap_number_internal is not None and self._active_lap_frames:
            logger.info(f"[LapIndexer] Processing active lap {self._active_lap_number_internal} during session finalize.")
            
            # Use the last available frame's data for timing and state
            last_frame = self._active_lap_frames[-1]
            end_tick = float(last_frame.get("SessionTimeSecs", self._active_lap_start_tick or 0))
            
            # LapLastLapTime is unlikely to be relevant or correct for a lap interrupted by session end
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
                session_finalize=True
            )
        else:
            logger.info("[LapIndexer] No active lap data to process during session finalize.")

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
        self._last_wrap_around_time = 0.0
        self._recently_started_by_wrap_around = False
        self._wrap_around_start_time = 0.0
        self._approaching_boundary = False
        logger.info("[LapIndexer] Internal state reset, but lap data preserved.")

    def get_laps(self) -> List[Dict[str, Any]]:
        """Return a deep copy of all finalized laps."""
        # This method might be called multiple times by IRacingLapSaver.
        # It should return the current state of finalized laps.
        import copy
        
        # Only log once every 30 seconds regardless of lap count
        current_time = time.time()
        should_log = not hasattr(self, '_last_get_laps_log_time') or (current_time - getattr(self, '_last_get_laps_log_time', 0) > 30.0)
        
        if should_log:
            logger.info(f"[LapIndexer] get_laps() called, returning {len(self.laps)} laps.")
            self._last_get_laps_log_time = current_time
                
        return copy.deepcopy(self.laps)
        
    def reset(self) -> None:
        """Explicitly reset the LapIndexer state including lap data.
        This should be called when starting a new session if reusing the same LapIndexer instance.
        """
        logger.info("[LapIndexer] Explicitly resetting all state including lap data.")
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
        self._last_wrap_around_time = 0.0
        self._recently_started_by_wrap_around = False
        self._wrap_around_start_time = 0.0
        self._approaching_boundary = False

    def close_if_needed(self, current_lap_dist: float, on_pit_road: bool, now_tick: float, current_frame: Dict[str, Any] = None) -> bool:
        """Check if wrap-around has occurred even if OnPitRoad is True.
        
        Args:
            current_lap_dist: Current LapDistPct value (0.0-1.0)
            on_pit_road: Current OnPitRoad status
            now_tick: Current session time in seconds
            current_frame: Current telemetry frame data for proper association
            
        Returns:
            True if lap was closed, False otherwise
        """
        # Only need to check if we have an active lap
        if self._active_lap_number_internal is None or not self._active_lap_frames:
            return False
            
        # EARLY BOUNDARY DETECTION: Track when we're approaching the start/finish line
        if not self._approaching_boundary and current_lap_dist > self._boundary_approach_threshold:
            self._approaching_boundary = True
            logger.info(f"[LapIndexer] 🏁 Approaching S/F line at {current_lap_dist:.3f} - Enhanced monitoring active")
        elif self._approaching_boundary and current_lap_dist < 0.50:
            # We've wrapped around and are now in the first half of the new lap
            self._approaching_boundary = False
            
        # CRITICAL FIX: Tighter wrap-around detection to capture the very start of laps
        # Detect wrap-around much earlier to avoid missing the beginning of laps
        
        # Primary detection: Near end of lap to very start of lap (most common case)
        wrap_detected = (self._previous_lap_dist_pct > 0.97 and current_lap_dist < 0.01)
        
        # Secondary detection: Large position drop (catches any remaining cases)
        # This catches cases where position jumps from say 0.99 to 0.01 (dropping by 0.98)
        big_drop_detected = (self._previous_lap_dist_pct - current_lap_dist >= 0.90)
        
        # Tertiary detection: Very tight detection for small jumps that cross zero
        # This catches cases where we go from 0.995 to 0.001 (very small window)
        precise_wrap_detected = (self._previous_lap_dist_pct > 0.995 and current_lap_dist < 0.005)
        
        # Check for cooldown period to prevent multiple detections of the same boundary
        time_since_last_wrap = now_tick - self._last_wrap_around_time
        if time_since_last_wrap < self._wrap_around_cooldown:
            # Still in cooldown period, ignore this potential wrap-around
            if wrap_detected or big_drop_detected:
                logger.debug(f"[LapIndexer] Ignoring potential wrap-around during cooldown: {self._previous_lap_dist_pct:.3f} → {current_lap_dist:.3f} "
                           f"(Time since last wrap: {time_since_last_wrap:.3f}s)")
            return False
        
        # Enhanced logging when approaching boundary for debugging
        if self._approaching_boundary and (self._previous_lap_dist_pct > 0.98 or current_lap_dist < 0.02):
            logger.info(f"[LapIndexer] 🎯 CRITICAL ZONE: {self._previous_lap_dist_pct:.6f} → {current_lap_dist:.6f} "
                       f"(Δ={self._previous_lap_dist_pct - current_lap_dist:.6f})")
        
        if wrap_detected or big_drop_detected or precise_wrap_detected:
            # Log which detection method triggered
            detection_method = []
            if wrap_detected: detection_method.append("PRIMARY(0.97→0.01)")
            if big_drop_detected: detection_method.append("SECONDARY(≥0.90_drop)")
            if precise_wrap_detected: detection_method.append("TERTIARY(0.995→0.005)")
            
            logger.info(f"[LapIndexer] ⚡ EARLY LAP DETECTION: {self._previous_lap_dist_pct:.6f} → {current_lap_dist:.6f} "
                       f"Methods: {', '.join(detection_method)} (OnPitRoad: {on_pit_road})")
            
            # Update the last wrap-around time
            self._last_wrap_around_time = now_tick
            
            # First, finalize the lap that's ending - this is critical to ensure we properly
            # capture the lap time and state before moving to the next lap
            self._finalise_active_lap(
                end_tick=now_tick,
                lap_last_lap_time_from_sdk=-1.0, # Temporary placeholder, will be updated when LapCompleted increments
                ended_on_pit_road=on_pit_road,
                session_finalize=False
            )
            
            # Prepare the next lap - increment the internal lap number but we'll sync with iRacing's
            # LapCompleted when it increments in a subsequent frame
            next_lap_num = (self._active_lap_number_internal or 0) + 1
            lap_invalidated = False
            if self._previous_frame_ir_data:
                lap_invalidated = self._previous_frame_ir_data.get("LapInvalidated", False)
                
            self._start_new_lap(
                lap_number_internal=next_lap_num,
                start_tick=now_tick,
                on_pit_start=on_pit_road,  # Correctly pass the current pit road status
                invalid_sdk_flag_for_this_lap=lap_invalidated
            )
            
            # Mark this as a lap started by wrap-around detection for proper handling in the next frame
            self._recently_started_by_wrap_around = True
            self._wrap_around_start_time = now_tick
            
            # CRITICAL FIX: Ensure we capture the start of the lap properly with CURRENT frame data
            # This fixes the telemetry data offset issue
            
            # First, add a synthetic "zero crossing" frame if we jumped over it
            if self._previous_lap_dist_pct > 0.99 and current_lap_dist > 0.01:
                # We jumped over the zero crossing, interpolate a frame at position 0.000
                boundary_frame = dict(self._previous_frame_ir_data) if self._previous_frame_ir_data else {}
                boundary_frame.update({
                    "LapDistPct": 0.000,  # Synthetic start-of-lap frame
                    "lap_boundary_interpolated": True  # Mark as interpolated for debugging
                })
                self._active_lap_frames.append(boundary_frame)
                logger.info(f"[LapIndexer] 🎯 Added interpolated start-of-lap frame at 0.000")
            
            # CRITICAL FIX: Use the CURRENT frame data for the new lap, not previous frame data
            if current_frame is not None:
                # Use the actual current frame data
                new_lap_frame = dict(current_frame)
                new_lap_frame.update({"LapDistPct": current_lap_dist})  # Ensure correct lap distance
                self._active_lap_frames.append(new_lap_frame)
                logger.info(f"[LapIndexer] ✅ Added CURRENT frame data to new lap {next_lap_num} at {current_lap_dist:.6f}")
            else:
                # Fallback to previous frame data if current frame not available (should not happen)
                fallback_frame = dict(self._previous_frame_ir_data) if self._previous_frame_ir_data else {}
                fallback_frame.update({"LapDistPct": current_lap_dist})
                self._active_lap_frames.append(fallback_frame)
                logger.warning(f"[LapIndexer] ⚠️ Used fallback frame data for new lap {next_lap_num} - this may cause telemetry offset")
            
            return True
            
        return False

    def _finalise_active_lap_delayed(self, lap_last_lap_time_from_sdk: float) -> None:
        """Finalize a lap that was marked for delayed finalization."""
        if not self._pending_wrap_around_lap or not self._pending_wrap_around_lap_frames:
            logger.warning("Cannot finalize delayed lap - no pending lap data available")
            return
            
        lap_dict = self._pending_wrap_around_lap.copy()
        
        # Update with the correct lap time from iRacing if available
        if lap_last_lap_time_from_sdk > 0:
            logger.info(f"Updating delayed lap time from {lap_dict.get('duration_seconds', 0):.3f}s "
                       f"to SDK value {lap_last_lap_time_from_sdk:.3f}s")
            lap_dict["duration_seconds"] = lap_last_lap_time_from_sdk
        
        # Add to finalized laps
        self.laps.append(lap_dict)
        
        logger.info(f"Successfully finalized delayed lap {lap_dict.get('lap_number_sdk', -1)} "
                   f"({lap_dict.get('lap_state', 'UNKNOWN')}). "
                   f"Time: {lap_dict.get('duration_seconds', 0):.3f}s, "
                   f"Frames: {len(self._pending_wrap_around_lap_frames)}")
                   
        # Clear pending data
        self._pending_wrap_around_lap = None
        self._pending_wrap_around_lap_frames = []

    def handle_reset(self, frame: Dict[str, Any], current_lap_dist: float, current_speed: float, on_pit_road: bool) -> bool:
        """Enhanced reset detection that catches ESC->Reset to Pits scenarios more reliably.
        
        This method should detect actual resets to pits (like ESC->Reset to Pits),
        especially when they happen after completing a lap.
        
        Args:
            frame: Current telemetry frame
            current_lap_dist: Current LapDistPct value (0.0-1.0)
            current_speed: Current Speed value in m/s
            on_pit_road: Current OnPitRoad status
            
        Returns:
            True if an actual reset was detected and handled, False otherwise
        """
        # Only need to check if we have previous data
        if self._previous_lap_dist_pct < 0 or not self._active_lap_frames:
            return False
            
        now_tick = float(frame.get("SessionTimeSecs", 0.0))
        
        # Get previous pit road status for transition detection
        prev_on_pit_road = False
        if self._previous_frame_ir_data:
            prev_on_pit_road = self._previous_frame_ir_data.get("OnPitRoad", False)
        
        # --- ENHANCED RESET DETECTION SCENARIOS ---
        
        # Scenario 1: Classic teleport to pits (speed drop + position jump + now on pit road)
        # This is the traditional "ESC -> Reset to Pits" scenario
        speed_drop = (self._previous_speed > 10.0 and current_speed < 5.0)  # Significant speed drop
        position_jump = abs(current_lap_dist - self._previous_lap_dist_pct) > 0.20  # Position jump
        now_on_pit_road = on_pit_road and not prev_on_pit_road  # Just entered pit road
        
        teleport_to_pits = speed_drop and position_jump and now_on_pit_road
        
        # Scenario 2: Sudden pit road entry with large position jump (relaxed criteria)
        # This catches "ESC -> Reset to Pits" even when speed criteria aren't met
        sudden_pit_entry = (not prev_on_pit_road and on_pit_road and 
                           abs(current_lap_dist - self._previous_lap_dist_pct) > 0.15 and  # Lowered threshold
                           not self._is_likely_sf_crossing(current_lap_dist))
        
        # Scenario 3: Major speed reset while on pit road (like car getting stuck and resetting)
        speed_reset_in_pits = (prev_on_pit_road and on_pit_road and 
                              self._previous_speed > 1.0 and current_speed < 0.1)
        
        # Scenario 4: NEW - Position-based reset detection (catches ESC->Reset after lap completion)
        # This detects when someone suddenly appears in pit area regardless of speed
        # Common when using ESC->Reset to Pits after completing a lap
        position_based_reset = (not prev_on_pit_road and on_pit_road and 
                               abs(current_lap_dist - self._previous_lap_dist_pct) > 0.10 and  # Any significant jump
                               current_lap_dist < 0.50)  # Now in first half of track (pit area)
        
        # Scenario 5: NEW - Track position discontinuity with pit entry
        # This catches cases where position suddenly changes AND we're now on pit road
        # This is very common with reset actions
        position_discontinuity = (not prev_on_pit_road and on_pit_road and
                                 abs(current_lap_dist - self._previous_lap_dist_pct) > 0.05)  # Even smaller jumps
        
        # Scenario 6: NEW - Speed-independent pit teleport
        # For cases where speed doesn't drop dramatically but position changes significantly with pit entry
        pit_teleport = (not prev_on_pit_road and on_pit_road and
                       abs(current_lap_dist - self._previous_lap_dist_pct) > 0.08 and
                       current_speed < 20.0)  # Reasonable speed (not necessarily dropped)
        
        # --- DETERMINE IF RESET OCCURRED ---
        reset_detected = (teleport_to_pits or sudden_pit_entry or speed_reset_in_pits or 
                         position_based_reset or position_discontinuity or pit_teleport)
        
        if reset_detected:
            # Log which scenario triggered the reset detection
            triggers = []
            if teleport_to_pits: triggers.append("TeleportToPits")
            if sudden_pit_entry: triggers.append("SuddenPitEntry") 
            if speed_reset_in_pits: triggers.append("SpeedResetInPits")
            if position_based_reset: triggers.append("PositionBasedReset")
            if position_discontinuity: triggers.append("PositionDiscontinuity")
            if pit_teleport: triggers.append("PitTeleport")
            
            logger.info(f"[LapIndexer] 🔄 RESET DETECTED - Triggers: {', '.join(triggers)}")
            logger.info(f"[LapIndexer] Reset details: Speed {self._previous_speed:.1f}→{current_speed:.1f} m/s, "
                       f"Position {self._previous_lap_dist_pct:.3f}→{current_lap_dist:.3f}, "
                       f"OnPit {prev_on_pit_road}→{on_pit_road}")
            
            # --- HANDLE THE ACTUAL RESET ---
            
            if self._active_lap_number_internal is not None and len(self._active_lap_frames) > 0:
                # Use the PREVIOUS frame's timestamp as the end time
                end_time = self._previous_frame_ir_data.get("SessionTimeSecs", now_tick) if self._previous_frame_ir_data else now_tick
                
                logger.info(f"[LapIndexer] Finalizing lap {self._active_lap_number_internal} due to RESET "
                           f"({len(self._active_lap_frames)} frames, ending at {end_time:.3f})")
                
                self._finalise_active_lap(
                    end_tick=end_time,
                    lap_last_lap_time_from_sdk=-1.0,  # No valid lap time for interrupted lap
                    ended_on_pit_road=True,  # Reset implies ending in pit area
                    session_finalize=False
                )
                
                # Start new lap after reset - this should be an OUT lap since we reset to pits
                next_lap_number = self._active_lap_number_internal + 1
                lap_invalidated = frame.get("LapInvalidated", False)
                
                logger.info(f"[LapIndexer] Starting new OUT lap {next_lap_number} after RESET (on_pit_start=True)")
                
                self._start_new_lap(
                    lap_number_internal=next_lap_number,
                    start_tick=now_tick,
                    on_pit_start=True,  # TRUE reset means starting on pit road = OUT lap
                    invalid_sdk_flag_for_this_lap=lap_invalidated
                )
                
            return True
            
        return False

    def _is_likely_sf_crossing(self, current_lap_dist: float) -> bool:
        """Helper method to determine if a position change is likely a start/finish line crossing.
        
        Args:
            current_lap_dist: Current lap distance percentage
            
        Returns:
            True if this looks like an S/F line crossing, False otherwise
        """
        # S/F line crossings typically involve going from high position (>0.95) to low position (<0.05)
        # or the reverse for backward movement
        prev_dist = self._previous_lap_dist_pct
        
        # Forward S/F crossing: high to low
        forward_crossing = (prev_dist > 0.95 and current_lap_dist < 0.05)
        
        # Backward S/F crossing: low to high (rare but possible)
        backward_crossing = (prev_dist < 0.05 and current_lap_dist > 0.95)
        
        return forward_crossing or backward_crossing

    # -----------------------------------------------------------------------
    # How to wire (Updated):
    # 1. Instantiate: lap_indexer = LapIndexer()
    # 2. In telemetry loop: lap_indexer.on_frame(ir_data)
    # 3. To get laps for IRacingLapSaver (periodically or on demand):
    #    newly_completed_laps = lap_indexer.get_laps() 
    #    Process these, keeping track of which ones IRacingLapSaver has already saved.
    #    The `lap_indexer.laps` list will grow. `get_laps()` gives a snapshot.
    # 4. At session end (e.g., iRacing disconnects, app closes):
    #    lap_indexer.finalize() # This finalizes the very last lap being collected
    #    final_laps_data = lap_indexer.get_laps() # Get all laps including the one just finalized
    #    Process `final_laps_data`