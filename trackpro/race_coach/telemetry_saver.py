import logging
import os
import json
import time
import datetime
import numpy as np
from pathlib import Path
from trackpro.race_coach.utils.telemetry_validation import validate_lap_telemetry

logger = logging.getLogger(__name__)

class TelemetrySaver:
    """Manages saving telemetry data per lap for later review."""
    
    def __init__(self, data_manager=None, save_dir=None, eye_tracking_manager=None):
        """Initialize the telemetry saver.
        
        Args:
            data_manager: The data manager instance (optional)
            save_dir: Directory to save telemetry data (optional, default is user's documents)
            eye_tracking_manager: Eye tracking manager instance (optional)
        """
        self.data_manager = data_manager
        self.eye_tracking_manager = eye_tracking_manager
        
        # Set up the save directory
        if save_dir is None:
            # Create default path in user's documents folder
            docs_path = Path(os.path.expanduser("~/Documents/TrackPro/Telemetry"))
            try:
                docs_path.mkdir(parents=True, exist_ok=True)
                self.save_dir = docs_path
            except Exception as e:
                logger.warning(f"Could not create directory in Documents: {e}")
                # Fall back to a local directory
                local_path = Path("./telemetry_data")
                local_path.mkdir(exist_ok=True)
                self.save_dir = local_path
        else:
            self.save_dir = Path(save_dir)
            self.save_dir.mkdir(parents=True, exist_ok=True)
            
        # Initialize state variables for lap detection
        self._current_lap_data = []
        self._current_lap_number = 0
        self._last_track_position = 0.0
        self._lap_start_time = 0.0
        self._session_id = None
        self._is_first_telemetry = True
        self._current_session_folder = None
        self._current_track = "Unknown Track"
        self._current_car = "Unknown Car"
        
        logger.info(f"Telemetry saver initialized with save directory: {self.save_dir}")
    
    def start_session(self, session_id=None, track_name=None, car_name=None):
        """Start a new telemetry recording session.
        
        Args:
            session_id: The database session ID (if available)
            track_name: Name of the track (for folder organization)
            car_name: Name of the car (for folder organization)
        """
        self._session_id = session_id
        self._current_lap_data = []
        self._current_lap_number = 0
        self._last_track_position = 0.0
        self._lap_start_time = 0.0
        self._is_first_telemetry = True
        
        # Store track and car names
        if track_name:
            self._current_track = track_name
        if car_name:
            self._current_car = car_name
        
        # Create session folder with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"Session_{timestamp}"
        
        if track_name:
            track_name = track_name.replace(" ", "_")
            session_name = f"{track_name}_{session_name}"
        
        if car_name:
            car_name = car_name.replace(" ", "_")
            session_name = f"{session_name}_{car_name}"
            
        self._current_session_folder = self.save_dir / session_name
        self._current_session_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Started new telemetry recording session: {session_name}")
        
        # Start eye tracking if available
        if self.eye_tracking_manager and self.eye_tracking_manager.is_available():
            try:
                # Set session info for eye tracking
                self.eye_tracking_manager.set_session_info(session_id, "racing_session")
                
                # Only start recording if auto_start is disabled (manual control)
                # If auto_start is enabled, it will start automatically when driving begins
                if not self.eye_tracking_manager.auto_start:
                    ready, message = self.eye_tracking_manager.is_ready_to_record()
                    if ready:
                        self.eye_tracking_manager.start_recording(session_id)
                        logger.info("Eye tracking started for session (manual mode)")
                    else:
                        logger.info(f"Eye tracking not started: {message}")
                else:
                    logger.info("Eye tracking in auto-start mode - will start when driving begins")
                
            except Exception as e:
                logger.warning(f"Failed to start eye tracking: {e}")
        
        return self._current_session_folder
    
    def process_telemetry(self, telemetry_data):
        """Process incoming telemetry data and save per lap.
        
        Args:
            telemetry_data: Dictionary containing telemetry data
            
        Returns:
            Tuple of (is_new_lap, lap_number, lap_time) or None if not a new lap
        """
        # Ensure we have a session folder
        if self._current_session_folder is None:
            self.start_session()
            
        # Check if we have required data for lap detection
        if 'track_position' not in telemetry_data:
            # Can't detect lap without track position
            return None
        
        # Get current track position (0.0 to 1.0)
        current_position = telemetry_data['track_position']
        
        # Deep copy telemetry data to avoid reference issues
        telemetry_point = telemetry_data.copy()
        
        # Add timestamp to the telemetry data
        telemetry_point['timestamp'] = time.time()
        
        # Initialize the position buffer for enhanced detection
        if not hasattr(self, "_position_buffer"):
            self._position_buffer = []
            self._timestamp_buffer = []
        
        # Add current position to buffer
        self._position_buffer.append(current_position)
        self._timestamp_buffer.append(telemetry_point['timestamp'])
        
        # Keep buffer at a reasonable size
        buffer_size = 20
        if len(self._position_buffer) > buffer_size:
            self._position_buffer.pop(0)
            self._timestamp_buffer.pop(0)
        
        # Initialize debug counter if needed
        if not hasattr(self, "_debug_counter"):
            self._debug_counter = 0
        self._debug_counter += 1
        
        # Initialize last lap timestamp if needed
        if not hasattr(self, "_last_lap_timestamp"):
            self._last_lap_timestamp = 0
        
        # Detect if we've crossed the start/finish line
        is_new_lap = False
        lap_time = 0.0
        
        # Log near S/F line for debugging
        if self._last_track_position > 0.8 or current_position < 0.2 or abs(self._last_track_position - current_position) > 0.7:
            if self._debug_counter % 30 == 0:  # Log periodically near S/F line
                logger.debug(f"Near S/F Line: Last={self._last_track_position:.3f}, Current={current_position:.3f}")
        
        # METHOD 1: Classical threshold detection (more lenient)
        # Check for crossing the start/finish line (track position goes from > 0.85 to < 0.15)
        method1_detected = False
        if not self._is_first_telemetry and self._last_track_position > 0.85 and current_position < 0.15:
            method1_detected = True
            
        # METHOD 2: Position buffer pattern detection
        method2_detected = False
        if len(self._position_buffer) >= 6 and not self._is_first_telemetry:
            # Check if we have recent high positions followed by recent low positions
            recent_high = any(pos > 0.8 for pos in self._position_buffer[:-3])
            recent_low = all(pos < 0.2 for pos in self._position_buffer[-2:])
            
            # Check if enough time has passed since last lap
            min_lap_time = 10  # seconds
            time_since_last_lap = telemetry_point['timestamp'] - self._last_lap_timestamp
            min_time_passed = time_since_last_lap > min_lap_time
            
            if recent_high and recent_low and min_time_passed:
                method2_detected = True
        
        # METHOD 3: Detect large position jumps (wrap-around)
        method3_detected = False
        if not self._is_first_telemetry and abs(self._last_track_position - current_position) > 0.7:
            # Only consider large jumps from high to low (not low to high)
            if self._last_track_position > 0.7 and current_position < 0.3:
                # Check if enough time has passed since last lap detection
                time_since_last_lap = telemetry_point['timestamp'] - self._last_lap_timestamp
                if time_since_last_lap > 10:  # 10 seconds minimum lap time
                    method3_detected = True
        
        # Combine detection methods - detect a lap if ANY method is positive
        if method1_detected or method2_detected or method3_detected:
            # We've crossed the start/finish line
            self._current_lap_number += 1
            is_new_lap = True
            
            # Calculate lap time if we have a valid lap start time
            if self._lap_start_time > 0:
                lap_time = telemetry_point['timestamp'] - self._lap_start_time
            
            # Track which method triggered the detection
            detection_methods = []
            if method1_detected:
                detection_methods.append("Threshold")
            if method2_detected:
                detection_methods.append("Pattern")
            if method3_detected:
                detection_methods.append("Jump")
            
            logger.info(f"New lap detected by methods: {', '.join(detection_methods)} - Lap {self._current_lap_number}, Time: {lap_time:.3f}s")
            
            # Save the current lap data if we have any
            if len(self._current_lap_data) > 0:
                self._save_lap_data(self._current_lap_number - 1, lap_time)
                
            # Update eye tracking with new lap
            if self.eye_tracking_manager and self.eye_tracking_manager.is_recording:
                self.eye_tracking_manager.update_lap_id(self._current_lap_number)
                
            # Reset for new lap
            self._current_lap_data = []
            self._lap_start_time = telemetry_point['timestamp']
            self._last_lap_timestamp = telemetry_point['timestamp']
        
        # Save the first lap start time
        if self._is_first_telemetry:
            self._lap_start_time = telemetry_point['timestamp']
            self._last_lap_timestamp = telemetry_point['timestamp']
            self._is_first_telemetry = False
        
        # Add data point to current lap
        self._current_lap_data.append(telemetry_point)
        
        # Sync with eye tracking
        if self.eye_tracking_manager and self.eye_tracking_manager.is_recording:
            self.eye_tracking_manager.update_telemetry_sync(telemetry_point)
        
        # Update eye tracking session state (for auto-start/stop)
        if self.eye_tracking_manager and self.eye_tracking_manager.enabled:
            self.eye_tracking_manager.update_session_state(telemetry_point)
        
        # Update last track position
        self._last_track_position = current_position
        
        # Return new lap info if a new lap was detected
        if is_new_lap:
            return (is_new_lap, self._current_lap_number, lap_time)
            
        return None
    
    def _save_lap_data(self, lap_number, lap_time):
        """Save the collected lap data to disk.
        
        Args:
            lap_number: The lap number
            lap_time: The lap time in seconds
        """
        if not self._current_lap_data:
            logger.warning("No lap data to save")
            return
        
        # Validate the lap data before saving
        lap_is_valid, validation_message, validation_diagnostics = validate_lap_telemetry(self._current_lap_data)
        
        if not lap_is_valid:
            logger.warning(f"Lap {lap_number} is incomplete based on validation: {validation_message}. Diagnostics: {validation_diagnostics}")
            # Decide handling for invalid laps:
            # Option 1: Don't save at all
            # return 
            # Option 2: Save with metadata indicating incompleteness (current approach)
        else:
            logger.info(f"Lap {lap_number} validated as complete. Message: {validation_message}")

        # Create enhanced metadata
        metadata = {
            "lap_number": lap_number,
            "lap_time": lap_time,
            "timestamp": time.time(),
            "point_count": len(self._current_lap_data),
            "is_complete_validated": lap_is_valid,  # Add validation status to metadata
            "validation_message": validation_message, # Add validation message
            "validation_diagnostics": validation_diagnostics, # Add validation diagnostics
            # Additional metadata fields for better organization
            "track_name": self._current_track if hasattr(self, '_current_track') else None,
            "car_name": self._current_car if hasattr(self, '_current_car') else None,
            "session_id": self._session_id
        }
        
        # Create new data structure with objects instead of separate arrays
        data_points = []
        
        # Get the start timestamp to calculate relative times
        start_timestamp = self._current_lap_data[0].get("timestamp", 0) if self._current_lap_data else 0
        
        # Process each telemetry point into a single object with all values
        for point in self._current_lap_data:
            timestamp = point.get("timestamp", 0)
            
            # Create a data point object with relative time for ease of use
            data_point = {
                "timestamp": timestamp,
                "relative_time": timestamp - start_timestamp if timestamp and start_timestamp else 0,
                "throttle": point.get("throttle", 0),
                "brake": point.get("brake", 0),
                "steering": point.get("steering", 0),
                "speed": point.get("speed", 0),
                "track_position": point.get("track_position", 0),
                "session_time": point.get("session_time", 0),
                "rpm": point.get("rpm", 0),
                "clutch": point.get("clutch", 0) if "clutch" in point else 0
            }
            
            data_points.append(data_point)
        
        # Create the new JSON structure
        organized_data = {
            "metadata": metadata,
            "data": data_points
        }
        
        # Keep the old structure as well for backward compatibility
        organized_data["timestamps"] = [point.get("timestamp", 0) for point in self._current_lap_data]
        organized_data["throttle"] = [point.get("throttle", 0) for point in self._current_lap_data]
        organized_data["brake"] = [point.get("brake", 0) for point in self._current_lap_data]
        organized_data["steering"] = [point.get("steering", 0) for point in self._current_lap_data]
        organized_data["speed"] = [point.get("speed", 0) for point in self._current_lap_data]
        organized_data["track_position"] = [point.get("track_position", 0) for point in self._current_lap_data]
        organized_data["session_time"] = [point.get("session_time", 0) for point in self._current_lap_data]
        organized_data["rpm"] = [point.get("rpm", 0) for point in self._current_lap_data]
        
        # Create filename
        filename = f"lap_{lap_number:03d}_{lap_time:.3f}s.json"
        file_path = self._current_session_folder / filename
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(organized_data, f)
            
        logger.info(f"Saved lap {lap_number} data to {file_path} ({len(self._current_lap_data)} data points)")
        
        # If data manager is available, add the lap to the database
        if self.data_manager and self._session_id:
            try:
                # Add lap to database with path to telemetry file
                self.data_manager.add_lap(
                    self._session_id,
                    lap_number,
                    lap_time,
                    is_valid=lap_is_valid, # Use the validation result here
                    telemetry=str(file_path),
                    # Consider adding validation_message to the database schema if useful
                    # validation_details=validation_message 
                )
                logger.info(f"Added lap {lap_number} to database (Valid: {lap_is_valid})")
            except Exception as e:
                logger.error(f"Error adding lap to database: {e}")
    
    def end_session(self):
        """End the current session and save any remaining lap data."""
        if len(self._current_lap_data) > 0:
            # Save the current incomplete lap
            # For end_session, lap_time is 0.0, it will likely fail validation if not a full lap.
            # The _save_lap_data method will now handle validation.
            logger.info(f"Ending session. Processing remaining data for lap {self._current_lap_number}...")
            self._save_lap_data(self._current_lap_number, 0.0) # Lap time is unknown here
            
        # Reset state
        self._current_lap_data = []
        self._is_first_telemetry = True
        
        logger.info("Telemetry recording session ended")
        
        return self._current_session_folder
    
    def get_lap_data(self, session_folder, lap_number=None):
        """Get saved lap data from a session.
        
        Args:
            session_folder: Path to the session folder
            lap_number: Specific lap number to retrieve, or None for all laps
            
        Returns:
            Dictionary with lap data or list of lap data
        """
        if not isinstance(session_folder, Path):
            session_folder = Path(session_folder)
            
        if not session_folder.exists():
            logger.error(f"Session folder does not exist: {session_folder}")
            return None
        
        if lap_number is not None:
            # Find the specific lap file
            lap_files = list(session_folder.glob(f"lap_{lap_number:03d}_*.json"))
            if not lap_files:
                logger.error(f"No data found for lap {lap_number} in {session_folder}")
                return None
                
            # Load the lap data
            with open(lap_files[0], 'r') as f:
                return json.load(f)
        else:
            # Return all laps in this session
            lap_files = sorted(session_folder.glob("lap_*.json"))
            laps = []
            
            for lap_file in lap_files:
                with open(lap_file, 'r') as f:
                    laps.append(json.load(f))
                    
            return laps 