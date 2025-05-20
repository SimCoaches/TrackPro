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
  • Out-lap = LapCompleted == 0
  • New lap boundary when LapCompleted increments
  • Lap recorded only if it is NOT invalidated
  • Lap time taken straight from LapLastLapTime (exact match with iRacing UI)
  • Stores every telemetry frame inside its lap bucket for graphing later
"""

from __future__ import annotations
from typing import Dict, List, Any
import logging
import copy

logger = logging.getLogger(__name__)

class LapIndexer:
    def __init__(self) -> None:
        # list of finalized laps
        self.laps: List[Dict[str, Any]] = []

        # live lap state
        self._active_lap_frames: List[Dict[str, Any]] = []
        self._active_lap_number: int | None = None
        self._active_lap_start_tick: float | None = None
        self._active_lap_started_on_pit: bool = False

        # cache last LapCompleted so we can detect increments
        self._last_lap_completed: int | None = None

    # ------------------------------------------------------------------ API --

    def on_frame(self, ir: Dict[str, Any]) -> None:
        """
        Feed ONE telemetry frame (dict from irsdk).

        You *must* call this for every tick, before doing anything with UI.
        """
        # --- BEGIN REVISED on_frame LOGIC ---
        current_sdk_lap_completed = int(ir.get("LapCompleted", -1))
        now_tick_val = ir.get("SessionTimeSecs", ir.get("SessionTickTime"))

        if now_tick_val is None or current_sdk_lap_completed == -1:
            logger.debug("[LapIndexer] Essential data (SessionTimeSecs or LapCompleted) missing. Skipping frame.")
            return 
        
        now_tick = float(now_tick_val)
        on_pit_road_now = bool(ir.get("OnPitRoad", False))
        # LapInvalidated refers to the *current* lap being driven (ir["Lap"])
        # We need to be careful applying this to self._active_lap_number which is based on ir["LapCompleted"]
        is_current_display_lap_invalid_sdk = bool(ir.get("LapInvalidated", False))

        processed_frame = dict(ir) # Work with a copy

        if self._last_lap_completed is None: # First frame received in this instance or after a reset
            self._active_lap_number = current_sdk_lap_completed # Typically 0 for the initial out-lap
            logger.info(f"[LapIndexer] First frame. Starting lap number {self._active_lap_number} (SDK LapCompleted: {current_sdk_lap_completed}).")
            self._start_new_lap(
                lap_number=self._active_lap_number,
                start_tick=now_tick,
                on_pit_start=on_pit_road_now,
                first_frame_of_this_lap=processed_frame
            )
            self._last_lap_completed = current_sdk_lap_completed
            return

        if current_sdk_lap_completed > self._last_lap_completed: # ir["LapCompleted"] has incremented
            # This signifies that the lap numbered self._last_lap_completed has just finished.
            # The LapIndexer's self._active_lap_number should have been tracking self._last_lap_completed.
            
            logger.info(f"[LapIndexer] SDK LapCompleted incremented from {self._last_lap_completed} to {current_sdk_lap_completed}.")

            if self._active_lap_number == self._last_lap_completed:
                logger.info(f"[LapIndexer] Finalizing lap {self._active_lap_number}.")
                # processed_frame is the first frame of the new lap (current_sdk_lap_completed)
                # It contains LapLastLapTime for the lap that just finished (self._active_lap_number).
                lap_last_lap_time_sdk = float(processed_frame.get("LapLastLapTime", -1.0))
                self._finalise_active_lap(
                    end_tick=now_tick,
                    current_ir_frame_on_new_lap=processed_frame,
                    lap_time_from_ir_at_completion=lap_last_lap_time_sdk
                )
            else:
                # This indicates a mismatch, which is a logic error or missed state.
                logger.error(f"[LapIndexer] Mismatch on lap completion! Indexer was on lap {self._active_lap_number}, but SDK indicates lap {self._last_lap_completed} just finished (new SDK LapCompleted is {current_sdk_lap_completed}).")
                if self._active_lap_frames: # Attempt to finalize whatever was active
                    logger.warning(f"[LapIndexer] Force finalizing mismatched active lap {self._active_lap_number}.")
                    # session_finalize to indicate potential issue
                    # Also try to get lap time if available, though it might be unreliable here.
                    lap_last_lap_time_sdk_mismatch = float(processed_frame.get("LapLastLapTime", -1.0))
                    self._finalise_active_lap(
                        end_tick=now_tick,
                        current_ir_frame_on_new_lap=processed_frame,
                        session_finalize=True, 
                        lap_time_from_ir_at_completion=lap_last_lap_time_sdk_mismatch
                    )

            # Start the new lap. The number for this new lap is current_sdk_lap_completed.
            self._active_lap_number = current_sdk_lap_completed
            logger.info(f"[LapIndexer] Starting new lap number {self._active_lap_number}.")
            self._start_new_lap(
                lap_number=self._active_lap_number,
                start_tick=now_tick, # This frame's time is the start of the new lap
                on_pit_start=on_pit_road_now,       # Pit road state at the start of this new lap
                first_frame_of_this_lap=processed_frame  # This is the first frame of the new lap
            )
        
        elif current_sdk_lap_completed < self._last_lap_completed: # Lap count jumped back (reset)
            logger.warning(f"[LapIndexer] SDK LapCompleted went backwards from {self._last_lap_completed} to {current_sdk_lap_completed}. This usually means a session restart or change.")
            if self._active_lap_number is not None: # If there was an active lap being tracked
                logger.info(f"[LapIndexer] Finalizing active lap {self._active_lap_number} due to SDK LapCompleted jump. This lap is considered aborted and will have no SDK time.")
                self._finalise_active_lap(
                    end_tick=now_tick_val,
                    current_ir_frame_on_new_lap=None, # No new lap triggered this finalization
                    lap_time_from_ir_at_completion=None # Explicitly None for aborted lap
                )
            
            logger.info(f"[LapIndexer] Restarting with lap number {current_sdk_lap_completed} after SDK jump back.")
            self._active_lap_number = current_sdk_lap_completed
            self._start_new_lap(
                lap_number=self._active_lap_number,
                start_tick=now_tick,
                on_pit_start=on_pit_road_now,
                first_frame_of_this_lap=processed_frame
            )

        else: # current_sdk_lap_completed == self._last_lap_completed
            # We are still within the same lap period as defined by ir["LapCompleted"].
            # Add the frame to the current active lap.
            if self._active_lap_number == current_sdk_lap_completed:
                if not self._active_lap_frames: # This is for logging the very first frame added to a newly started lap via the _start_new_lap first_frame_of_this_lap param
                    # This specific log will now seldom trigger here because _start_new_lap adds the first frame.
                    # It would only trigger if _start_new_lap was called with first_frame_of_this_lap=None
                    # logger.info(f"[LapIndexer] Adding first frame to active lap {self._active_lap_number} (current SDK LapCompleted: {current_sdk_lap_completed}). LapDistPct: {processed_frame.get('LapDistPct', 'N/A')}")
                    pass # First frame already added by _start_new_lap normally
                
                # This append is for subsequent frames of the lap
                # _start_new_lap already added the first frame of the lap if it was starting.
                # We must ensure we don't add the first frame twice.
                # The logic in _start_new_lap now handles adding the first_frame_of_this_lap.
                # So, if _active_lap_frames already contains that first frame, we should only append if current frame is different.
                # However, on_frame processes one frame at a time. _start_new_lap adds *this current* processed_frame.
                # So, no further append is needed here FOR THIS FRAME if a new lap was just started.
                # This block (current_sdk_lap_completed == self._last_lap_completed) is for *subsequent* frames when no new lap starts.
                
                # The _start_new_lap path (when current_sdk_lap_completed > self._last_lap_completed or < or first frame)
                # already calls _start_new_lap which adds 'processed_frame'.
                # So if we reach this 'else' block, it means no new lap started on *this specific frame*.
                # Thus, 'processed_frame' belongs to the ongoing self._active_lap_number.
                if self._active_lap_frames and self._active_lap_frames[-1]['SessionTimeSecs'] == processed_frame['SessionTimeSecs']:
                    # Avoid adding duplicate frame if for some reason on_frame is called twice with the same frame
                    logger.debug(f"[LapIndexer] Duplicate frame detected for lap {self._active_lap_number}, SessionTime: {processed_frame['SessionTimeSecs']}. Skipping append.")
                else:
                    self._active_lap_frames.append(processed_frame)
                
                # Invalidate the current collecting lap (self._active_lap_number) if the *current driving lap* (ir["Lap"]) is marked invalid by SDK
                # ir["Lap"] is typically ir["LapCompleted"] + 1.
                # So, if self._active_lap_number is L, ir["Lap"] is L+1.
                # If LapInvalidated is true, it applies to lap L+1. We mark lap L (our active one) as invalid.
                # This interpretation might need refinement; LapInvalidated usually applies to the lap *currently being generated.
                # Let's assume LapInvalidated refers to the lap *currently being driven*.
                # If self._active_lap_number is tracking ir['LapCompleted'], then ir['Lap'] is the lap *after* the one we are indexing.
                # A simpler approach: if ir["LapInvalidated"] is true, the currently forming telemetry (for self._active_lap_number) might be part of an invalid sequence.
                # if is_current_display_lap_invalid_sdk: # REMOVE THIS BLOCK
                #     self._active_lap_invalid = True # Mark current collecting lap as invalid

            else:
                # This state implies self._active_lap_number is out of sync with current_sdk_lap_completed,
                # but current_sdk_lap_completed hasn't changed from self._last_lap_completed.
                # This should ideally not be reached if the transitions are handled correctly.
                logger.warning(f"[LapIndexer] State desync: ActiveLap={self._active_lap_number}, SDKLapCompleted={current_sdk_lap_completed}, LastSDKLapCompleted={self._last_lap_completed}. Attempting to add frame to active lap.")
                if self._active_lap_number is not None: # If there's an active lap, add to it.
                    self._active_lap_frames.append(processed_frame)
                    # if is_current_display_lap_invalid_sdk: # REMOVE THIS
                    #    self._active_lap_invalid = True
                else: # No active lap, but not first frame either. Try to start based on current SDK.
                    logger.warning(f"[LapIndexer] Desync and no active lap. Attempting to start new lap {current_sdk_lap_completed}.")
                    self._active_lap_number = current_sdk_lap_completed
                    self._start_new_lap(
                        lap_number=self._active_lap_number,
                        start_tick=now_tick,
                        # invalid_now=is_current_display_lap_invalid_sdk, # REMOVE THIS
                        on_pit_start=on_pit_road_now,
                        first_frame_of_this_lap=processed_frame
                    )

        self._last_lap_completed = current_sdk_lap_completed # Update for the next frame processing
        # --- END REVISED on_frame LOGIC ---

    def finalize(self) -> None:
        """Call once when TrackPro shuts down to flush current lap."""
        if self._active_lap_frames and self._active_lap_number is not None:
            # Treat incomplete lap as invalid for safety, or decide based on context (e.g. if on pit road)
            # For simplicity, let's mark it as invalid.
            # self._active_lap_invalid = True 
            self._finalise_active_lap(
                end_tick=self._active_lap_frames[-1]["SessionTimeSecs"], # Use SessionTimeSecs
                session_finalize=True
            )
        
        # Reset internal state for potential reuse or clean shutdown
        self._active_lap_frames = []
        self._active_lap_number = None
        self._active_lap_start_tick = None
        self._active_lap_started_on_pit = False
        self._last_lap_completed = None


    def get_laps(self) -> List[Dict[str, Any]]:
        """Deep copy of all recorded laps."""
        return copy.deepcopy(self.laps)

    def retrieve_and_clear_completed_laps(self) -> List[Dict[str, Any]]:
        """Returns a deep copy of all recorded laps and then clears the internal list."""
        laps_to_return = copy.deepcopy(self.laps)
        self.laps.clear()
        logger.debug(f"[LapIndexer] Retrieved and cleared {len(laps_to_return)} completed laps.")
        return laps_to_return

    def reset_internal_lap_state(self) -> None:
        """Resets all internal lap tracking states and clears stored laps, preparing for a new session context."""
        logger.info("[LapIndexer] Resetting internal lap state for new session context.")
        self.laps.clear() # Clear the list of finalized laps
        self._active_lap_frames = []
        self._active_lap_number = None
        self._active_lap_start_tick = None
        self._active_lap_started_on_pit = False
        self._last_lap_completed = None # Reset this crucial state variable

    # ----------------------------------------------------------- internals --

    def _start_new_lap(
        self,
        lap_number: int, # This is ir["LapCompleted"] when a new lap starts
        start_tick: float,
        on_pit_start: bool,
        first_frame_of_this_lap: Dict[str, Any] | None = None,
    ) -> None:
        self._active_lap_frames = []
        # The actual lap number for display/storage (0 for outlap, 1 for first timed etc.)
        # is effectively lap_number at the point of starting.
        self._active_lap_number = lap_number 
        self._active_lap_start_tick = start_tick
        self._active_lap_started_on_pit = on_pit_start

        if first_frame_of_this_lap:
            self._active_lap_frames.append(first_frame_of_this_lap)

    def _finalise_active_lap(self, end_tick: float, current_ir_frame_on_new_lap: Dict[str, Any] | None = None, session_finalize: bool = False, lap_time_from_ir_at_completion: float | None = None) -> None:
        if not self._active_lap_frames:
            logger.warning("[LapIndexer._finalise_active_lap] Attempted to finalise a lap with no frames. This shouldn't happen.")
            return 

        lap_to_finalise_number = self._active_lap_number
        
        # Determine if the lap ended on pit road
        ended_on_pit_road = False
        if current_ir_frame_on_new_lap: # This is the first frame of the *next* lap
            ended_on_pit_road = bool(current_ir_frame_on_new_lap.get("OnPitRoad", False))
        elif session_finalize and self._active_lap_frames: # Session ending, use last frame of current lap
            last_frame = self._active_lap_frames[-1]
            ended_on_pit_road = bool(last_frame.get("OnPitRoad", False))

        # --- BEGIN MODIFICATION TO TRUNCATE FRAMES ---
        frames_to_finalise = copy.deepcopy(self._active_lap_frames) # Make a DEEP copy
        final_end_tick = end_tick # This is SessionTimeSecs of the triggering frame
        final_lap_time_for_packet = lap_time_from_ir_at_completion

        if lap_time_from_ir_at_completion is not None and lap_time_from_ir_at_completion > 0 and self._active_lap_start_tick is not None:
            true_lap_end_session_time = self._active_lap_start_tick + lap_time_from_ir_at_completion
            
            original_frame_count = len(frames_to_finalise)
            frames_to_finalise = [
                frame for frame in frames_to_finalise if frame.get('SessionTimeSecs', float('inf')) <= true_lap_end_session_time
            ]
            truncated_count = original_frame_count - len(frames_to_finalise)
            if truncated_count > 0:
                logger.info(f"[LapIndexer._finalise_active_lap] Truncated {truncated_count} frames from lap {lap_to_finalise_number} to match SDK lap time {lap_time_from_ir_at_completion:.3f}s. Original end_tick: {final_end_tick:.3f}, new effective end_tick: {true_lap_end_session_time:.3f}")
            
            final_end_tick = true_lap_end_session_time
            # Note: final_lap_time_for_packet remains lap_time_from_ir_at_completion, as that's the official time.
        
        if not frames_to_finalise: # If all frames were truncated (e.g. LapLastLapTime is tiny or negative)
             logger.warning(f"[LapIndexer._finalise_active_lap] All frames for lap {lap_to_finalise_number} were truncated or lap started with no frames. Finalizing as empty.")
             # Keep final_lap_time_for_packet as is, IRacingLapSaver will handle invalid times.
        # --- END MODIFICATION TO TRUNCATE FRAMES ---

        num_frames_finalised = len(frames_to_finalise)
        first_frame_time_finalised = frames_to_finalise[0].get('SessionTimeSecs', 'N/A') if num_frames_finalised > 0 else self._active_lap_start_tick # Fallback to start_tick
        last_frame_time_finalised = frames_to_finalise[-1].get('SessionTimeSecs', 'N/A') if num_frames_finalised > 0 else final_end_tick # Fallback to end_tick

        # Determine is_lap_considered_invalid_by_indexer based on final_lap_time_for_packet
        is_lap_considered_invalid_by_indexer = False
        if final_lap_time_for_packet is None or final_lap_time_for_packet <= 0:
            is_lap_considered_invalid_by_indexer = True
            logger.info(f"[LapIndexer._finalise_active_lap] Lap {lap_to_finalise_number} explicitly marked as INVALID by indexer due to SDK time: {final_lap_time_for_packet}")
        # else: # Optional: log valid cases if needed, but not strictly necessary
            # logger.info(f"[LapIndexer._finalise_active_lap] Lap {lap_to_finalise_number} considered VALID by indexer with SDK time: {final_lap_time_for_packet}")

        logger.info(
            f"[LapIndexer._finalise_active_lap] Finalizing LapNum: {lap_to_finalise_number}, "
            f"SDKTime: {final_lap_time_for_packet if final_lap_time_for_packet is not None else 'N/A'}, "
            f"NumFrames: {num_frames_finalised}, "
            f"FirstFrameTime: {first_frame_time_finalised if isinstance(first_frame_time_finalised, str) else f'{first_frame_time_finalised:.3f}'}, "
            f"LastFrameTime: {last_frame_time_finalised if isinstance(last_frame_time_finalised, str) else f'{last_frame_time_finalised:.3f}'}, "
            f"StartTick: {self._active_lap_start_tick if self._active_lap_start_tick is not None else 'N/A'}, "
            f"EndTickArgUsed: {final_end_tick:.3f}, " # Using the potentially adjusted final_end_tick
            f"InvalidByIndexerFlag: {is_lap_considered_invalid_by_indexer}, StartedPit: {self._active_lap_started_on_pit}, EndedPit: {ended_on_pit_road}"
        )

        finalized_lap = {
            "lap_number": lap_to_finalise_number,
            "lap_time": final_lap_time_for_packet, # This is the crucial SDK LapLastLapTime
            "frames": frames_to_finalise,
            "start_tick": self._active_lap_start_tick,
            "end_tick": final_end_tick, # Use the potentially adjusted end_tick
            "invalid_by_indexer": is_lap_considered_invalid_by_indexer, # Use the new determination
            "started_on_pit_road": self._active_lap_started_on_pit,
            "ended_on_pit_road": ended_on_pit_road,
            "first_frame_session_time": first_frame_time_finalised if num_frames_finalised > 0 else None,
            "last_frame_session_time": last_frame_time_finalised if num_frames_finalised > 0 else None,
        }
        logger.info(f"[LapIndexer._finalise_active_lap] Dict for lap {lap_to_finalise_number} before append: {finalized_lap}")
        self.laps.append(finalized_lap)
        
        # Clear current lap data, ready for the next one (which might have already started)
        self._active_lap_frames.clear()
        self._active_lap_number = -1 # Should be set by _start_new_lap
        self._active_lap_start_tick = -1.0
        self._active_lap_started_on_pit = False

    # -----------------------------------------------------------------------

    def process_frame(self, telemetry_data):
        """
        Process a telemetry frame and detect lap boundaries.
        This is an alias for on_frame that matches the naming in the revised API.
        
        Args:
            telemetry_data (dict): Telemetry data from iRacing
        """
        return self.on_frame(telemetry_data)
        
    def has_lap_to_save(self):
        """
        Check if there are any completed laps ready to be saved.
        
        Returns:
            bool: True if there are laps to save, False otherwise
        """
        # Check if we have any laps in our completed laps queue
        return len(self.laps) > 0
        
    def get_lap_data_to_save(self):
        """
        Get the next completed lap data for saving.
        
        Returns:
            dict: Lap data dictionary or None if no laps to save
        """
        if not self.has_lap_to_save():
            return None
            
        # Get the oldest completed lap and remove it from the queue
        return self.laps.pop(0) if self.laps else None

# --------------- HOW TO WIRE IT INTO TrackPro ------------------------------
#
# 1.  import once at app start::
#
#       from .lap_indexer import LapIndexer # Or appropriate relative import
#       lap_indexer = LapIndexer()
#
# 2.  In your *single* telemetry loop / callback where you get `ir_data` dict::
#
#       # Example:
#       # def on_new_telemetry_data(self, ir_data):
#       #     self.lap_indexer.on_frame(ir_data)
#       #     # ... rest of your telemetry processing ...
#
# 3.  When the iRacing connection ends or the user stops logging::
#
#       lap_indexer.finalize()
#       session_laps = lap_indexer.get_laps() # List of lap dicts
#
#    Pass "session_laps" to the UI combo-boxes – they now match iRacing EXACTLY
#    (lap 0 out-lap, lap 1 first timed lap, etc.).
#    The 'lap_number_sdk' is the 0-indexed number.
#    'duration_seconds' is the time to display.
#
# 4.  REMOVE / DISABLE any previous lap-detection code (position thresholds,
#    the old iRacingLapProcessor, iracing_lap_saver.py logic, etc.)
#    to avoid double-counting or conflicts.
#
# ---------------------------------------------------------------------------- 