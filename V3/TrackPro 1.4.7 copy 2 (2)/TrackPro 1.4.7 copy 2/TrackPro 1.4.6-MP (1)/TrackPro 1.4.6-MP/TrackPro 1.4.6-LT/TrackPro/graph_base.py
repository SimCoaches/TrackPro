# If there's existing lap detection logic here, it might need to be replaced or refactored
# to use an instance of iRacingLapProcessor.

class iRacingLapProcessor:
    """
    Processes iRacing telemetry data to detect and record laps, aligning with iRacing's
    lap counting (0-indexed for out-lap) and handling pit stops.
    """
    def __init__(self, track_name=None, car_name=None):
        self.track_name = track_name
        self.car_name = car_name
        
        self.laps = []  # Stores dicts of completed lap info
        
        # Stores the current lap number as reported by iRacing (0-indexed).
        # Initialized to -2 to correctly process the very first lap update from iRacing.
        self.current_iracing_lap_number = -2 
        self.current_lap_start_session_time = None # Session time when the current iRacing lap started
        self.current_lap_telemetry_data = [] # List of telemetry points for the current lap

        # Pit stop detection state
        self.in_pits = False # True if the car is currently considered to be in a pit stop
        self.speed_below_threshold_start_time = None # Session time when speed first dropped below PIT_SPEED_THRESHOLD_KMH
        self.last_received_session_time = None # Tracks the session time of the last processed sample

        # Constants for lap detection and pit stops
        self.PIT_SPEED_THRESHOLD_KMH = 5.0  # Speed below which a car might be pitting
        self.PIT_MIN_DURATION_S = 5.0       # How long speed must be low to confirm a pit stop

        # Track position state for S/F line detection (complementary to iRacing's lap counter)
        self.track_pos_state = "UNKNOWN"  # Possible states: "UNKNOWN", "APPROACHING_SF", "CROSSED_SF_RECENTLY", "ON_LAP"
        self.HIGH_TRACK_POS_THRESHOLD = 0.90 # Track position considered near end of lap
        self.LOW_TRACK_POS_THRESHOLD = 0.10  # Track position considered just past S/F line
        
        self.is_first_lap_after_pit_exit = False # Flag to manage S/F crossing logic after a pit stop

    def _reset_pit_detection_state(self):
        """Resets variables related to detecting if the car is stationary or in pits."""
        self.speed_below_threshold_start_time = None
        self.in_pits = False

    def _reset_lap_detection_logic_after_pit(self):
        """
        Resets internal state after a pit stop is confirmed.
        This helps ensure that exiting the pits doesn't immediately trigger a false lap
        if the car crosses the S/F line near the pit exit.
        """
        self.track_pos_state = "BELOW_HIGH_THRESHOLD" # Reset track position state
        self.is_first_lap_after_pit_exit = True
        # Note: current_lap_start_session_time and current_lap_telemetry_data for the lap
        # leading into the pits are preserved until iRacing's lap counter confirms its completion.
        print(f"INFO: Lap detection logic prepared for pit exit.")

    def process_telemetry_sample(self, session_time, track_pos_normalized, speed_kmh, iracing_reported_lapnum):
        """
        Processes a single telemetry sample to detect pit stops and lap completions.

        Args:
            session_time (float): Current session time in seconds.
            track_pos_normalized (float): Normalized track position (0.0 to 1.0).
            speed_kmh (float): Current speed in km/h.
            iracing_reported_lapnum (int): Lap number reported by iRacing (0-indexed).
                                           Example: 'Lap' from the iRacing SDK.
        """

        if self.last_received_session_time is None:
            self.last_received_session_time = session_time

        # --- Pit Stop Detection ---
        if speed_kmh < self.PIT_SPEED_THRESHOLD_KMH:
            if self.speed_below_threshold_start_time is None: # If speed just dropped
                self.speed_below_threshold_start_time = session_time
            
            # Check if speed has been low for long enough to be considered a pit stop
            if (session_time - self.speed_below_threshold_start_time) >= self.PIT_MIN_DURATION_S:
                if not self.in_pits: # If we weren't already in pits, mark it now
                    print(f"INFO: Pit stop entered at session time {session_time:.2f}s. Speed: {speed_kmh:.1f} km/h.")
                    self.in_pits = True
                    self._reset_lap_detection_logic_after_pit()
        else: # Speed is above threshold
            if self.in_pits: # If we were in pits and now moving, means we exited.
                print(f"INFO: Exited pits at session time {session_time:.2f}s. Speed: {speed_kmh:.1f} km/h.")
            self._reset_pit_detection_state() # Reset pit detection as car is moving

        # --- Telemetry Data Collection for Current Lap ---
        # Start collecting data only once the first lap (iRacing Lap 0 - out-lap) has officially begun.
        if self.current_lap_start_session_time is not None:
            self.current_lap_telemetry_data.append({
                "session_time": session_time,
                "track_pos": track_pos_normalized,
                "speed_kmh": speed_kmh,
                # Other relevant telemetry can be added here (e.g., throttle, brake)
            })

        # --- Lap Completion Logic (Primarily driven by iRacing's lap counter) ---
        if iracing_reported_lapnum != self.current_iracing_lap_number:
            # This block executes when iRacing's lap counter changes.

            if self.current_iracing_lap_number == -2: # Initial synchronization
                print(f"INFO: Telemetry sync. iRacing reports current Lap {iracing_reported_lapnum}. Initializing...")
                self.current_iracing_lap_number = iracing_reported_lapnum
                self.current_lap_start_session_time = session_time # This is the start of iRacing's Lap 0 (out-lap)
                self.current_lap_telemetry_data = [{ # Add first data point for this lap
                    "session_time": session_time, "track_pos": track_pos_normalized, "speed_kmh": speed_kmh,
                }]
                lap_type_msg = "Out Lap" if self.current_iracing_lap_number == 0 else f"Lap {self.current_iracing_lap_number}"
                print(f"INFO: Starting iRacing {lap_type_msg} at {session_time:.2f}s.")

            elif iracing_reported_lapnum > self.current_iracing_lap_number:
                # iRacing indicates a lap has been completed.
                # The lap that just FINISHED is `self.current_iracing_lap_number`.
                completed_lap_num_from_iracing = self.current_iracing_lap_number
                lap_end_time = session_time
                
                if self.current_lap_start_session_time is not None:
                    lap_duration = lap_end_time - self.current_lap_start_session_time
                    
                    completed_lap_info = {
                        "lap_number_iracing": completed_lap_num_from_iracing, # 0 for out-lap, 1 for first timed lap
                        "lap_time_seconds": lap_duration,
                        "start_session_time": self.current_lap_start_session_time,
                        "end_session_time": lap_end_time,
                        "telemetry_data": list(self.current_lap_telemetry_data), # Store a copy
                        "completed_by": "iracing_counter",
                        "is_out_lap": (completed_lap_num_from_iracing == 0),
                        # If in_pits is true when iRacing increments lap, this completed lap was an in-lap.
                        "is_in_lap": self.in_pits and (iracing_reported_lapnum == completed_lap_num_from_iracing + 1)
                    }
                    self.laps.append(completed_lap_info)
                    
                    lap_type_str = "Out Lap" if completed_lap_info["is_out_lap"] else f"Lap {completed_lap_info['lap_number_iracing']}"
                    if completed_lap_info["is_in_lap"]: lap_type_str += " (In Lap)"
                    print(f"INFO: Completed iRacing {lap_type_str}. Time: {lap_duration:.3f}s. Data points: {len(self.current_lap_telemetry_data)}")
                else:
                    print(f"WARNING: iRacing lap {iracing_reported_lapnum} completed, but no start time recorded for lap {self.current_iracing_lap_number}.")

                # Prepare for the NEW lap (which is `iracing_reported_lapnum`)
                self.current_iracing_lap_number = iracing_reported_lapnum
                self.current_lap_start_session_time = lap_end_time # New lap starts when old one ended
                self.current_lap_telemetry_data = [{ # Add first data point for the new lap
                    "session_time": session_time, "track_pos": track_pos_normalized, "speed_kmh": speed_kmh,
                }]
                self.is_first_lap_after_pit_exit = False # A new lap officially started
                new_lap_type_msg = "Out Lap" if self.current_iracing_lap_number == 0 else f"Lap {self.current_iracing_lap_number}" # Should not be outlap here unless reset
                print(f"INFO: Starting iRacing {new_lap_type_msg} at {session_time:.2f}s.")
            
            elif iracing_reported_lapnum < self.current_iracing_lap_number:
                # iRacing's lap counter decreased (e.g., reset to pits, new session segment).
                print(f"WARNING: iRacing lap number decreased from {self.current_iracing_lap_number} to {iracing_reported_lapnum}. Resetting lap tracking.")
                # Treat as a full reset for lap timing purposes
                self.current_iracing_lap_number = iracing_reported_lapnum
                self.current_lap_start_session_time = session_time
                self.current_lap_telemetry_data = [{
                    "session_time": session_time, "track_pos": track_pos_normalized, "speed_kmh": speed_kmh,
                }]
                self._reset_pit_detection_state()
                self.is_first_lap_after_pit_exit = False
                print(f"INFO: Reset and starting iRacing Lap {self.current_iracing_lap_number} at {session_time:.2f}s.")

        # --- Track Position S/F Line Crossing Logic (Complementary) ---
        # This helps manage state, especially for pit exits, but iRacing's counter is the primary trigger.
        if track_pos_normalized > self.HIGH_TRACK_POS_THRESHOLD:
            if self.track_pos_state != "APPROACHING_SF":
                # print(f"DEBUG: TrackPos changed to APPROACHING_SF at {session_time:.2f} (Pos: {track_pos_normalized:.3f})")
                self.track_pos_state = "APPROACHING_SF"
        elif track_pos_normalized < self.LOW_TRACK_POS_THRESHOLD:
            if self.track_pos_state == "APPROACHING_SF":
                # print(f"DEBUG: TrackPos changed to CROSSED_SF_RECENTLY at {session_time:.2f} (Pos: {track_pos_normalized:.3f})")
                self.track_pos_state = "CROSSED_SF_RECENTLY"
                # This S/F crossing is noted. If `is_first_lap_after_pit_exit` is true,
                # it means we crossed S/F after pitting. The actual lap start time and number
                # will still be governed by iRacing's lap counter update.
            elif self.track_pos_state == "UNKNOWN": # e.g. initial state before first high threshold cross
                 self.track_pos_state = "ON_LAP" # or some other state indicating it's not approaching S/F from high side
        else: # track_pos_normalized is between LOW_TRACK_POS_THRESHOLD and HIGH_TRACK_POS_THRESHOLD
            if self.track_pos_state == "CROSSED_SF_RECENTLY":
                # Moved away from S/F line after crossing
                # print(f"DEBUG: TrackPos changed to ON_LAP at {session_time:.2f} (Pos: {track_pos_normalized:.3f})")
                self.track_pos_state = "ON_LAP"
            elif self.track_pos_state == "UNKNOWN":
                 self.track_pos_state = "ON_LAP"


        self.last_received_session_time = session_time

    def get_completed_laps(self):
        """Returns a list of all completed lap data dictionaries."""
        return list(self.laps) # Return a copy

    def finalize_session(self, final_session_time):
        """
        Call when the telemetry session ends to process any ongoing, incomplete lap.
        This is important for capturing data for the lap the car was on when the session ended (e.g., an in-lap).
        """
        if self.current_lap_start_session_time is not None and self.current_lap_telemetry_data:
            # If there's data for a lap that hasn't been officially 'completed' by iRacing's counter changing
            lap_duration = final_session_time - self.current_lap_start_session_time
            
            # Determine if this final segment could be considered an in-lap or genuinely incomplete
            is_final_segment_in_lap = self.in_pits # If car was in pits at session end
            
            final_lap_info = {
                "lap_number_iracing": self.current_iracing_lap_number,
                "lap_time_seconds": lap_duration,
                "start_session_time": self.current_lap_start_session_time,
                "end_session_time": final_session_time,
                "telemetry_data": list(self.current_lap_telemetry_data),
                "completed_by": "session_end", # Indicates this lap was closed due to session ending
                "is_out_lap": (self.current_iracing_lap_number == 0),
                "is_in_lap": is_final_segment_in_lap or True, # Assume final lap is an in-lap or incomplete
                "is_incomplete": True # Mark as incomplete as it wasn't confirmed by iRacing counter
            }
            self.laps.append(final_lap_info)
            
            lap_type_str = "Out Lap" if final_lap_info["is_out_lap"] else f"Lap {final_lap_info['lap_number_iracing']}"
            print(f"INFO: Finalizing session. Saved ongoing iRacing {lap_type_str} as incomplete/in-lap. Time: {lap_duration:.3f}s")

        self.current_lap_start_session_time = None
        self.current_lap_telemetry_data = []
        
        print(f"INFO: Session finalized. Total laps recorded: {len(self.laps)}")
        return list(self.laps)

# Example Usage (conceptual - integrate into your telemetry processing loop)
# if __name__ == '__main__':
#     # This is a conceptual example. You'll integrate this into your actual telemetry data feed.
#     lap_processor = iRacingLapProcessor(track_name="Example Track", car_name="Example Car")
# 
#     # Simulate telemetry data stream
#     # (session_time, track_pos, speed_kmh, iracing_lap_num)
#     sim_data = [
#         (0.0, 0.01, 80, 0),   # Start of Out Lap (Lap 0)
#         (1.0, 0.05, 150, 0),
#         # ... more data for out lap ...
#         (85.0, 0.98, 200, 0),  # Approaching S/F line at end of Out Lap
#         (85.5, 0.02, 200, 1),  # Crossed S/F, iRacing now reports Lap 1. Out Lap (Lap 0) ended. Lap 1 starts.
#         (86.0, 0.05, 201, 1),
#         # ... data for Lap 1 ...
#         (165.0, 0.99, 210, 1), # Approaching S/F at end of Lap 1
#         (165.7, 0.03, 208, 2), # Crossed S/F, iRacing reports Lap 2. Lap 1 ended. Lap 2 starts.
#         # ... data for Lap 2 ...
#         (200.0, 0.50, 30, 2),  # Slowing down for pits
#         (201.0, 0.52, 4, 2),   # Speed below threshold
#         (202.0, 0.53, 3, 2),
#         (203.0, 0.53, 3, 2),
#         (204.0, 0.53, 3, 2),
#         (205.0, 0.53, 3, 2),
#         (206.0, 0.53, 3, 2),   # Pit stop confirmed (speed < 5kmh for > 5s)
#         (210.0, 0.53, 3, 2),   # Still in pits
#         (212.0, 0.55, 60, 2),  # Exiting pits
#         (215.0, 0.80, 180, 2), # Back on track
#         (240.0, 0.95, 200, 2), # Approaching S/F on current Lap 2 (which was an in-lap then out from pits)
#         (240.6, 0.01, 190, 3), # Crossed S/F, iRacing reports Lap 3. Lap 2 (the one with pit stop) ended. Lap 3 starts.
#         # ... more data ...
#     ]
# 
#     for t_data in sim_data:
#         lap_processor.process_telemetry_sample(t_data[0], t_data[1], t_data[2], t_data[3])
# 
#     # At the end of the session (e.g., iRacing disconnects or user stops)
#     final_time = sim_data[-1][0] + 10.0 # Simulate some time after last data point
#     all_recorded_laps = lap_processor.finalize_session(final_time)
# 
#     print("\\n--- Final Laps Recorded ---")
#     for i, lap_rec in enumerate(all_recorded_laps):
#         lap_type = "Out Lap" if lap_rec['is_out_lap'] else f"Lap {lap_rec['lap_number_iracing']}"
#         if lap_rec.get('is_in_lap'): lap_type += " (In Lap)"
#         if lap_rec.get('is_incomplete'): lap_type += " [Incomplete]"
#             
#         print(f"  {i+1}. {lap_type}: {lap_rec['lap_time_seconds']:.3f}s "
#               f"(iRacing Lap Num: {lap_rec['lap_number_iracing']}) "
#               f"Start: {lap_rec['start_session_time']:.2f} End: {lap_rec['end_session_time']:.2f} "
#               f"Points: {len(lap_rec['telemetry_data'])}") 