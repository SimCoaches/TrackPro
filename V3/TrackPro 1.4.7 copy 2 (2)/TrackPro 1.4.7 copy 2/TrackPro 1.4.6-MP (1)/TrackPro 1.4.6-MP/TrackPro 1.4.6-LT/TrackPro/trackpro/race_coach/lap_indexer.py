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

    def _log_sdk_warning(self, message: str):
        current_time = time.time()
        if (current_time - self._last_sdk_data_warning_time > self._warning_interval or
            message != self._last_sdk_data_warning_message):
            logger.warning(message)
            self._last_sdk_data_warning_time = current_time
            self._last_sdk_data_warning_message = message

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
            self._start_new_lap(
                lap_number_internal=current_lap_completed_sdk, # Starts at 0 for the out-lap
                start_tick=now_tick,
                on_pit_start=on_pit_road_now,
                # LapInvalidated refers to ir["Lap"], which is current_lap_completed_sdk + 1 here.
                # So, this flag is for the lap we are *just starting*.
                invalid_sdk_flag_for_this_lap=lap_invalidated_flag_now
            )
            self._active_lap_frames.append(frame_copy)
            self._last_lap_completed_sdk = current_lap_completed_sdk
            self._previous_frame_ir_data = frame_copy
            
            # Initialize previous values for wrap-around and reset detection
            self._previous_lap_dist_pct = frame_copy.get("LapDistPct", 0.0)
            self._previous_speed = frame_copy.get("Speed", 0.0)
            return

        # --- Check for Reset/Teleport and Track Position Wrap-Around ---
        # First check if handle_reset should be called
        current_lap_dist = frame_copy.get("LapDistPct", 0.0)
        current_speed = frame_copy.get("Speed", 0.0)
        
        # Now check for wrap-around or reset
        reset_handled = self.handle_reset(frame_copy, current_lap_dist, current_speed, on_pit_road_now)
        wraparound_handled = self.close_if_needed(current_lap_dist, on_pit_road_now, now_tick)
        
        # If either reset or wrap-around was handled, return now as the frame has already been processed
        if reset_handled or wraparound_handled:
            # The frame has already been added to the new lap in handle_reset or close_if_needed
            # Update state for next iteration
            self._last_lap_completed_sdk = current_lap_completed_sdk
            self._previous_frame_ir_data = frame_copy
            self._previous_lap_dist_pct = current_lap_dist
            self._previous_speed = current_speed
            return

        # --- Main Lap Transition Logic ---
        # ir["LapCompleted"] has incremented, meaning the lap whose internal number was
        # self._last_lap_completed_sdk has now officially finished.
        if current_lap_completed_sdk > self._last_lap_completed_sdk:
            logger.info(f"[LapIndexer] LapCompleted incremented: {self._last_lap_completed_sdk} -> {current_lap_completed_sdk}")
            
            # Determine if the lap that just finished ended on pit road
            # This uses the OnPitRoad status from the *previous* frame, which was the last frame of that lap.
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

    def _start_new_lap(
        self,
        lap_number_internal: int, # This is ir["LapCompleted"] value at the moment this lap physically starts
        start_tick: float,
        on_pit_start: bool,
        invalid_sdk_flag_for_this_lap: bool # ir["LapInvalidated"] status for this new lap
    ) -> None:
        self._active_lap_frames = []
        self._active_lap_number_internal = lap_number_internal
        self._active_lap_start_tick = start_tick
        self._active_lap_invalid_sdk = invalid_sdk_flag_for_this_lap # Initial invalid state for this lap
        self._active_lap_started_on_pit = on_pit_start

        if on_pit_start:
            self._active_lap_state = LapState.OUT
        else:
            self._active_lap_state = LapState.TIMED
        
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
        
        calculated_duration = end_tick - self._active_lap_start_tick
        final_lap_duration = calculated_duration # Default to calculated

        # For normally completed laps (not session end), prefer SDK time if valid and positive.
        # Lap 0 (out-lap) often has LapLastLapTime == -1 from SDK.
        if not session_finalize and lap_last_lap_time_from_sdk > 0 and lap_to_finalize_sdk_num >= 0 : # SDK time is valid
            final_lap_duration = lap_last_lap_time_from_sdk
            logger.info(f"[LapIndexer] Using SDK lap time {final_lap_duration:.3f}s for lap {lap_to_finalize_sdk_num}.")
        else:
            logger.info(f"[LapIndexer] Using calculated lap time {final_lap_duration:.3f}s for lap {lap_to_finalize_sdk_num}. "
                        f"(SDK time: {lap_last_lap_time_from_sdk:.3f}s, SessionFinalize: {session_finalize})")

        # Determine lap state
        current_lap_state = self._active_lap_state
        if not self._active_lap_started_on_pit and ended_on_pit_road:
            current_lap_state = LapState.IN
            logger.info(f"[LapIndexer] Lap {lap_to_finalize_sdk_num} reclassified as IN (StartedTrack:True, EndedPit:{ended_on_pit_road}).")
        elif session_finalize and current_lap_state != LapState.IN : # If session ends and not a clear IN lap
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

    def close_if_needed(self, current_lap_dist: float, on_pit_road: bool, now_tick: float) -> bool:
        """Check if wrap-around has occurred even if OnPitRoad is True.
        
        Args:
            current_lap_dist: Current LapDistPct value (0.0-1.0)
            on_pit_road: Current OnPitRoad status
            now_tick: Current session time in seconds
            
        Returns:
            True if lap was closed, False otherwise
        """
        # Only need to check if we have an active lap
        if self._active_lap_number_internal is None or not self._active_lap_frames:
            return False
            
        # Check for wrap-around - if we were near the end of the lap and now near the start
        # Use 0.02 hysteresis to avoid jitter at the start/finish line
        wrap_detected = (self._previous_lap_dist_pct > 0.98 and current_lap_dist < 0.02)
        
        # Also detect if we experienced a huge drop in position (≥0.95) which indicates S/F crossing
        # This catches cases where position jumps from say 0.99 to 0.04 (dropping by 0.95)
        big_drop_detected = (self._previous_lap_dist_pct - current_lap_dist >= 0.95)
        
        # Check for cooldown period to prevent multiple detections of the same boundary
        time_since_last_wrap = now_tick - self._last_wrap_around_time
        if time_since_last_wrap < self._wrap_around_cooldown:
            # Still in cooldown period, ignore this potential wrap-around
            if wrap_detected or big_drop_detected:
                logger.debug(f"[LapIndexer] Ignoring potential wrap-around during cooldown: {self._previous_lap_dist_pct:.3f} → {current_lap_dist:.3f} "
                           f"(Time since last wrap: {time_since_last_wrap:.3f}s)")
            return False
        
        if wrap_detected or big_drop_detected:
            logger.info(f"[LapIndexer] Detected lap wrap-around: {self._previous_lap_dist_pct:.3f} → {current_lap_dist:.3f} "
                       f"(OnPitRoad: {on_pit_road})")
            
            # Update the last wrap-around time
            self._last_wrap_around_time = now_tick
            
            # Determine if the lap ended on pit road
            ended_on_pit = on_pit_road
            
            # We won't have a valid LapLastLapTime from SDK for this wrap-around
            # since iRacing's LapCompleted counter didn't increment
            lap_last_lap_time_from_sdk = -1.0
            
            # Save the current active frames before finalizing the lap
            saved_frames = self._active_lap_frames.copy()
            
            # Finalize the current lap
            self._finalise_active_lap(
                end_tick=now_tick,
                lap_last_lap_time_from_sdk=lap_last_lap_time_from_sdk,
                ended_on_pit_road=ended_on_pit,
                session_finalize=False
            )
            
            # Start a new lap
            next_lap_num = (self._active_lap_number_internal or 0) + 1
            lap_invalidated = False
            if self._previous_frame_ir_data:
                lap_invalidated = self._previous_frame_ir_data.get("LapInvalidated", False)
                
            self._start_new_lap(
                lap_number_internal=next_lap_num,
                start_tick=now_tick,
                on_pit_start=on_pit_road,
                invalid_sdk_flag_for_this_lap=lap_invalidated
            )
            
            # Add the current frame to the new lap, which is important
            # to make sure we don't miss the first point after crossing S/F
            if self._previous_frame_ir_data:
                self._active_lap_frames.append(self._previous_frame_ir_data.copy())
            
            return True
            
        return False
        
    def handle_reset(self, frame: Dict[str, Any], current_lap_dist: float, current_speed: float, on_pit_road: bool) -> bool:
        """Detect teleport: prev_speed > 2 m/s && speed < 0.5 AND ΔLapDistPct > 0.20 while OnPitRoad == True
        
        Args:
            frame: Current telemetry frame
            current_lap_dist: Current LapDistPct value (0.0-1.0)
            current_speed: Current Speed value in m/s
            on_pit_road: Current OnPitRoad status
            
        Returns:
            True if reset was detected and handled, False otherwise
        """
        # Only check if we're on pit road - resets elsewhere are handled differently
        if not on_pit_road:
            return False
            
        # Only need to check if we have previous data
        if self._previous_lap_dist_pct < 0 or not self._active_lap_frames:
            return False
            
        # Check for sudden drop in speed (car was moving but now almost stopped)
        speed_drop = (self._previous_speed > 2.0 and current_speed < 0.5)
        
        # Check for significant position jump (teleport)
        position_jump = abs(current_lap_dist - self._previous_lap_dist_pct) > 0.20
        
        # Combined check for reset/teleport while on pit road
        if speed_drop and position_jump and on_pit_road:
            now_tick = float(frame.get("SessionTimeSecs", 0.0))
            
            logger.info(f"[LapIndexer] Detected reset/teleport: Speed {self._previous_speed:.1f} → {current_speed:.1f} m/s, "
                       f"Position {self._previous_lap_dist_pct:.3f} → {current_lap_dist:.3f} (OnPitRoad: {on_pit_road})")
            
            # Save the current active frames before finalizing the lap
            saved_frames = self._active_lap_frames.copy()
            
            # Finalize the current lap
            self._finalise_active_lap(
                end_tick=now_tick,
                lap_last_lap_time_from_sdk=-1.0,  # No valid lap time for a reset
                ended_on_pit_road=True,  # We know we're on pit road
                session_finalize=False
            )
            
            # Start a new OUT lap at the teleport position
            next_lap_num = (self._active_lap_number_internal or 0) + 1
            self._start_new_lap(
                lap_number_internal=next_lap_num,
                start_tick=now_tick,
                on_pit_start=True,  # We're on pit road
                invalid_sdk_flag_for_this_lap=False  # Reset the flag for the new lap
            )
            
            # Add the current frame to the new lap
            self._active_lap_frames.append(frame.copy())
            
            return True
            
        return False

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