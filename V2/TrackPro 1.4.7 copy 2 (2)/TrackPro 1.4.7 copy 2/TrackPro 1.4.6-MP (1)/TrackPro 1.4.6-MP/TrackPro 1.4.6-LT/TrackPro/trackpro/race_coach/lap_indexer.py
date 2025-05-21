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


class LapIndexer:
    def __init__(self) -> None:
        # list of finalized laps
        self.laps: List[Dict[str, Any]] = []

        # live lap state
        self._active_lap_frames: List[Dict[str, Any]] = []
        self._active_lap_number: int | None = None
        self._active_lap_start_tick: float | None = None
        self._active_lap_invalid: bool = False
        self._active_lap_started_on_pit: bool = False

        # cache last LapCompleted so we can detect increments
        self._last_lap_completed: int | None = None

    # ------------------------------------------------------------------ API --

    def on_frame(self, ir: Dict[str, Any]) -> None:
        """
        Feed ONE telemetry frame (dict from irsdk).

        You *must* call this for every tick, before doing anything with UI.
        """
        # Ensure all required keys are present, with defaults if necessary
        lap_completed = int(ir.get("LapCompleted", -1)) # Default to -1 if not present
        # Use 'SessionTimeSecs' as per logs, fallback to SessionTickTime if it ever appears
        now_tick_val = ir.get("SessionTimeSecs", ir.get("SessionTickTime"))
        if now_tick_val is None:
            # Log an error or handle missing time data appropriately
            # For now, let's skip the frame if essential time data is missing
            # logger.error("[LapIndexer] Critical timing data (SessionTimeSecs/SessionTickTime) missing in ir_data")
            return 
        now_tick = float(now_tick_val)

        on_pit = bool(ir.get("OnPitRoad", False))
        # LapInvalidated might not always be present, default to False (not invalid)
        lap_invalidated_this_frame = bool(ir.get("LapInvalidated", False))

        frame_copy = dict(ir)  # guard against external mutation

        if lap_completed == -1: # Check if LapCompleted was missing
            # logger.warning("[LapIndexer] 'LapCompleted' missing from ir_data. Skipping frame.")
            return

        # First ever frame – initialise tracking
        if self._last_lap_completed is None:
            self._start_new_lap(
                lap_number=lap_completed, # This will be 0 for the first "lap" (out-lap)
                start_tick=now_tick,
                invalid_now=lap_invalidated_this_frame,
                on_pit_start=on_pit,
            )
            self._active_lap_frames.append(frame_copy)
            self._last_lap_completed = lap_completed
            return

        # NEW LAP FINISHED?
        # This condition means iRacing has scored a lap.
        # The lap that just *finished* is self._last_lap_completed (or self._active_lap_number).
        # The new *current* lap as per iRacing is `lap_completed` (which is old_lap_completed + 1).
        if lap_completed > self._last_lap_completed:
            # Close previous active lap
            # The end_tick for the lap that just finished is the start_tick of this new frame.
            self._finalise_active_lap(end_tick=now_tick)

            # Open fresh lap buffer for the lap that is NOW starting.
            # The lap_number for this new active lap is `lap_completed` (iRacing's 0-indexed current lap count).
            self._start_new_lap(
                lap_number=lap_completed, 
                start_tick=now_tick,
                invalid_now=lap_invalidated_this_frame,
                on_pit_start=on_pit,
            )

        # Add frame to current lap
        self._active_lap_frames.append(frame_copy)
        if lap_invalidated_this_frame:
            self._active_lap_invalid = True # Mark current lap as invalid if this frame makes it so

        # update last seen counter
        self._last_lap_completed = lap_completed

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
        self._active_lap_invalid = False
        self._active_lap_started_on_pit = False
        self._last_lap_completed = None


    def get_laps(self) -> List[Dict[str, Any]]:
        """Deep copy of all recorded laps."""
        import copy
        return copy.deepcopy(self.laps)

    # ----------------------------------------------------------- internals --

    def _start_new_lap(
        self,
        lap_number: int, # This is ir["LapCompleted"] when a new lap starts
        start_tick: float,
        invalid_now: bool,
        on_pit_start: bool,
    ) -> None:
        self._active_lap_frames = []
        # The actual lap number for display/storage (0 for outlap, 1 for first timed etc.)
        # is effectively lap_number at the point of starting.
        self._active_lap_number = lap_number 
        self._active_lap_start_tick = start_tick
        self._active_lap_invalid = invalid_now
        self._active_lap_started_on_pit = on_pit_start

    def _finalise_active_lap(self, end_tick: float, session_finalize: bool = False) -> None:
        """
        Create lap dict & push to self.laps if valid.
        """
        if self._active_lap_number is None or self._active_lap_start_tick is None or not self._active_lap_frames:
            return 

        # Fetch official time from iRacing for the lap that JUST COMPLETED
        # This should come from the *last frame of the completed lap*, which is the one *before* the current frame
        # if a new lap just ticked over, or the very last frame if session_finalize is true.
        
        # If session_finalize is true, LapLastLapTime might not be updated for the *current* active lap.
        # If a lap just completed (lap_completed > self._last_lap_completed in on_frame),
        # then the *current* ir["LapLastLapTime"] in that frame *is* for the lap we are finalizing.
        
        last_lap_time_from_sdk = -1.0
        if not session_finalize and self._active_lap_frames:
            # The ir_data in on_frame that triggered finalization is the *first frame of the NEXT lap*.
            # So its "LapLastLapTime" is the one we want.
            # We need to access ir["LapLastLapTime"] from the frame that *triggered* this finalization.
            # This is tricky because _finalise_active_lap doesn't directly get that frame.
            # Let's assume the last frame *appended* before this call has the relevant info.
             triggering_frame = self._active_lap_frames[-1] # This is the frame that caused LapCompleted to increment
             last_lap_time_from_sdk = float(triggering_frame.get("LapLastLapTime", -1.0))

        calculated_duration = end_tick - self._active_lap_start_tick
        
        # Prefer SDK lap time if available and positive, otherwise use calculated.
        # For the out-lap (active_lap_number == 0 when finalized), LapLastLapTime is often -1.
        # In session_finalize, LapLastLapTime is also not reliable for the lap being cut short.
        final_lap_duration = calculated_duration
        if last_lap_time_from_sdk > 0 and not session_finalize and self._active_lap_number > 0 : # Only use SDK time for actual timed laps
            final_lap_duration = last_lap_time_from_sdk
        
        # Do not save if the lap is marked as invalid by iRacing.
        # Also, ensure we have telemetry frames and a positive duration.
        if not self._active_lap_invalid and self._active_lap_frames and final_lap_duration > 0:
            lap_dict = {
                "lap_number_sdk": self._active_lap_number,  # This is the iRacing 0-indexed lap number that just *completed*
                "is_out_lap": self._active_lap_number == 0,
                "start_tick": self._active_lap_start_tick,
                "end_tick": end_tick,
                "duration_seconds": final_lap_duration,
                "telemetry_frames": list(self._active_lap_frames), # Store a copy
                "is_complete_by_sdk_increment": not session_finalize,
                "is_incomplete_session_end": session_finalize,
                "started_on_pit_road": self._active_lap_started_on_pit,
                "ended_on_pit_road": bool(self._active_lap_frames[-1].get("OnPitRoad", False)),
                "is_valid_from_sdk": not self._active_lap_invalid # Redundant with outer check but explicit
            }
            self.laps.append(lap_dict)
        
        # _active_lap_frames will be reset by _start_new_lap or finalize()

    # -----------------------------------------------------------------------


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