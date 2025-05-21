"""
Simplified module for saving iRacing lap times to Supabase.
"""

import logging
import time
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

class SimpleLapSaver:
    """
    Simplified class to save iRacing lap times to Supabase.
    """
    def __init__(self, supabase_client=None):
        """Initialize with a Supabase client."""
        self._supabase = supabase_client
        self._user_email = None
        self._user_id = None
        self._session_id = None
        self._track_id = None
        self._car_id = None
        self._current_lap_number = 0
        self._last_track_position = 0
        self._lap_time = 0
        self._best_lap_time = float('inf')
        self._lap_start_time = 0
        self._telemetry_points = []
        
        # For detecting new laps
        self._is_first_telemetry = True
        
        logger.info("SimpleLapSaver initialized")
        
    def set_user_email(self, email):
        """Set the user email for identification."""
        self._user_email = email
        logger.info(f"Set user email to: {email}")
        
    def set_user_id(self, user_id):
        """Set the user ID for identification."""
        self._user_id = user_id
        logger.info(f"Set user ID to: {user_id}")
        
    def start_session(self, track_name, car_name, session_type="Race"):
        """Start a new session with track and car info."""
        if not self._supabase:
            logger.warning("Cannot start session: No Supabase client provided")
            return None
            
        # Reset session state
        self._session_id = None
        self._current_lap_number = 0
        self._is_first_telemetry = True
        self._telemetry_points = []
        self._best_lap_time = float('inf')
        
        # Get or create track
        try:
            # Try to find the track
            track_resp = self._supabase.table("tracks").select("id").eq("name", track_name).execute()
            if track_resp.data and len(track_resp.data) > 0:
                self._track_id = track_resp.data[0]["id"]
                logger.info(f"Found track: {track_name} (ID: {self._track_id})")
            else:
                # Create new track
                track_insert = self._supabase.table("tracks").insert({"name": track_name}).execute()
                if track_insert.data and len(track_insert.data) > 0:
                    self._track_id = track_insert.data[0]["id"]
                    logger.info(f"Created track: {track_name} (ID: {self._track_id})")
                else:
                    logger.error(f"Failed to create track: {track_name}")
                    return None
        except Exception as e:
            logger.error(f"Error with track: {e}")
            return None
            
        # Get or create car
        try:
            # Try to find the car
            car_resp = self._supabase.table("cars").select("id").eq("name", car_name).execute()
            if car_resp.data and len(car_resp.data) > 0:
                self._car_id = car_resp.data[0]["id"]
                logger.info(f"Found car: {car_name} (ID: {self._car_id})")
            else:
                # Create new car
                car_insert = self._supabase.table("cars").insert({"name": car_name}).execute()
                if car_insert.data and len(car_insert.data) > 0:
                    self._car_id = car_insert.data[0]["id"]
                    logger.info(f"Created car: {car_name} (ID: {self._car_id})")
                else:
                    logger.error(f"Failed to create car: {car_name}")
                    return None
        except Exception as e:
            logger.error(f"Error with car: {e}")
            return None
            
        # Create session
        session_data = {
            "track_id": self._track_id,
            "car_id": self._car_id,
            "session_type": session_type,
            "session_date": datetime.now().isoformat(),
        }
        
        # Add email if available
        if self._user_email:
            session_data["email"] = self._user_email
            
        try:
            # Create session
            session_resp = self._supabase.table("sessions").insert(session_data).execute()
            if session_resp.data and len(session_resp.data) > 0:
                self._session_id = session_resp.data[0]["id"]
                logger.info(f"Started session: {self._session_id}")
                return self._session_id
            else:
                # If PostgREST API fails, try direct SQL (fallback)
                logger.warning("Failed to create session via API, trying SQL fallback")
                # Just use a direct insert - simplest approach
                session_id = self._execute_sql_insert("sessions", session_data)
                if session_id:
                    self._session_id = session_id
                    logger.info(f"Started session via SQL: {session_id}")
                    return session_id
                else:
                    logger.error("Failed to create session")
                    return None
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
            
    def _execute_sql_insert(self, table, data):
        """Execute a simple SQL INSERT and return the ID."""
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in data.values()])
            # Remove explicit column name assumption in RETURNING clause - will now return the UUID column
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *"
            
            # Use direct SQL query
            resp = self._supabase.rpc("execute_sql", {"sql": query}).execute()
            if resp.data and len(resp.data) > 0:
                # The UUID column in the database is 'id', but we access it by string key
                # rather than assuming it's there
                inserted_id = resp.data[0].get("id")
                if inserted_id:
                    return inserted_id
                else:
                    logger.warning(f"No 'id' column found in response: {resp.data[0]}")
                    # Return first column as fallback if available
                    first_key = next(iter(resp.data[0]), None)
                    if first_key:
                        return resp.data[0][first_key]
                    return None
        except Exception as e:
            logger.error(f"SQL insert error: {e}")
        return None
    
    def process_telemetry(self, telemetry_data):
        """Process telemetry data and detect laps."""
        if not self._session_id:
            if not self._is_first_telemetry:
                logger.debug("No active session for telemetry")
            return None
            
        # Get track position (0-1 range)
        track_position = None
        
        # Try different field names to find track position
        for field in ['track_position', 'LapDistPct', 'lap_dist_pct', 'track_pos']:
            if field in telemetry_data:
                track_position = float(telemetry_data[field])
                break
                
        if track_position is None:
            logger.debug("No track position in telemetry")
            return None
            
        # Normalize to 0-1 range if needed
        if track_position > 1:
            track_position = track_position / 100.0 if track_position <= 100 else track_position % 1.0
        
        # Store timestamp for lap time calculation
        current_time = time.time()
        
        # For first update, just store position
        if self._is_first_telemetry:
            self._last_track_position = track_position
            self._lap_start_time = current_time
            self._is_first_telemetry = False
            
            # Initialize position buffer for enhanced detection
            if not hasattr(self, "_position_buffer"):
                self._position_buffer = []
                self._timestamp_buffer = []
            
            self._position_buffer.append(track_position)
            self._timestamp_buffer.append(current_time)
            
            # For debug counting
            if not hasattr(self, "_debug_counter"):
                self._debug_counter = 0
            
            return None
            
        # Update position buffer for enhanced detection
        if not hasattr(self, "_position_buffer"):
            self._position_buffer = []
            self._timestamp_buffer = []
        
        self._position_buffer.append(track_position)
        self._timestamp_buffer.append(current_time)
        
        # Keep buffer at a reasonable size (last 20 positions)
        buffer_size = 20
        if len(self._position_buffer) > buffer_size:
            self._position_buffer.pop(0)
            self._timestamp_buffer.pop(0)
        
        # Increment debug counter
        if not hasattr(self, "_debug_counter"):
            self._debug_counter = 0
        self._debug_counter += 1
        
        # Enhanced lap detection - use multiple methods
        is_new_lap = False
        
        # Log near S/F line for debugging - use more relaxed thresholds
        if self._last_track_position > 0.8 or track_position < 0.2 or abs(self._last_track_position - track_position) > 0.7:
            if self._debug_counter % 30 == 0:  # Log periodically near S/F line
                logger.debug(f"Near S/F Line: Last={self._last_track_position:.3f}, Current={track_position:.3f}")
        
        # METHOD 1: Classical threshold detection (more lenient)
        # Check if we've crossed the S/F line (position going from 0.85+ to < 0.15)
        method1_detected = self._last_track_position > 0.85 and track_position < 0.15
        
        # METHOD 2: Position buffer pattern detection
        # Look for a pattern of positions being mostly high and then suddenly low
        method2_detected = False
        if len(self._position_buffer) >= 6:
            # Check if we have recent high positions followed by recent low positions
            recent_high = any(pos > 0.8 for pos in self._position_buffer[:-3])
            recent_low = all(pos < 0.2 for pos in self._position_buffer[-2:])
            
            # Minimum time since last lap
            min_lap_time = 10  # seconds
            if not hasattr(self, "_last_lap_time_stamp"):
                self._last_lap_time_stamp = 0
                
            time_since_last_lap = current_time - self._last_lap_time_stamp
            min_time_passed = time_since_last_lap > min_lap_time
            
            if recent_high and recent_low and min_time_passed:
                method2_detected = True
        
        # METHOD 3: Detect large position jumps (wrap-around)
        method3_detected = False
        if abs(self._last_track_position - track_position) > 0.7:
            # Only consider large jumps from high to low (not low to high)
            if self._last_track_position > 0.7 and track_position < 0.3:
                # Check if enough time has passed since last lap detection
                if not hasattr(self, "_last_lap_time_stamp"):
                    self._last_lap_time_stamp = 0
                
                time_since_last_lap = current_time - self._last_lap_time_stamp
                if time_since_last_lap > 10:  # 10 seconds minimum lap time
                    method3_detected = True
        
        # Combine detection methods - detect a lap if ANY method is positive
        if method1_detected or method2_detected or method3_detected:
            # Completed a lap
            self._current_lap_number += 1
            lap_time = current_time - self._lap_start_time
            self._lap_time = lap_time
            
            # Track which method triggered the detection
            detection_methods = []
            if method1_detected:
                detection_methods.append("Threshold")
            if method2_detected:
                detection_methods.append("Pattern")
            if method3_detected:
                detection_methods.append("Jump")
            
            logger.info(f"New lap detected by methods: {', '.join(detection_methods)} - Lap {self._current_lap_number}, Time: {lap_time:.3f}s")
            
            # Save lap data
            self._save_lap_data(lap_time)
            
            # Reset for next lap
            self._lap_start_time = current_time
            self._telemetry_points = []
            self._last_lap_time_stamp = current_time
            
            is_new_lap = True
        
        # Save current position for next iteration
        self._last_track_position = track_position
        
        # Add current telemetry to points buffer, assuming we have essential data
        try:
            telemetry_point = {
                'timestamp': current_time,
                'session_time': telemetry_data.get('SessionTime', current_time),
                'track_position': track_position
            }
            
            # Copy any additional data fields
            for key, value in telemetry_data.items():
                if key not in telemetry_point and key not in ['SessionTime']:
                    telemetry_point[key] = value
            
            self._telemetry_points.append(telemetry_point)
        except Exception as e:
            logger.error(f"Error storing telemetry point: {e}")
        
        if is_new_lap:
            return True, self._current_lap_number, self._lap_time
        
        return None
        
    def _save_lap_data(self, lap_time):
        """Save lap data to database."""
        if not self._supabase or not self._session_id:
            logger.warning("Cannot save lap: No session or Supabase client")
            return None
            
        # Check if personal best
        is_personal_best = lap_time < self._best_lap_time
        if is_personal_best:
            self._best_lap_time = lap_time
            
        # Create lap data
        lap_data = {
            "session_id": self._session_id,
            "lap_number": self._current_lap_number,
            "lap_time": lap_time,
            "is_valid": True,
            "is_personal_best": is_personal_best,
        }
        
        # Add email if available
        if self._user_email:
            lap_data["email"] = self._user_email
            
        try:
            # Save lap
            lap_resp = self._supabase.table("laps").insert(lap_data).execute()
            if lap_resp.data and len(lap_resp.data) > 0:
                lap_id = lap_resp.data[0]["id"]
                logger.info(f"Saved lap {self._current_lap_number}: {lap_time:.3f}s")
                
                # Save telemetry points
                if self._telemetry_points:
                    self._save_telemetry(lap_id)
                    
                return lap_id
            else:
                # Try SQL fallback
                lap_id = self._execute_sql_insert("laps", lap_data)
                if lap_id:
                    logger.info(f"Saved lap via SQL: {lap_id}")
                    
                    # Save telemetry points
                    if self._telemetry_points:
                        self._save_telemetry(lap_id)
                        
                    return lap_id
                else:
                    logger.error("Failed to save lap")
        except Exception as e:
            logger.error(f"Error saving lap: {e}")
            
        return None
        
    def _save_telemetry(self, lap_id):
        """Save telemetry points for a lap."""
        if not self._supabase or not lap_id or not self._telemetry_points:
            return False
            
        # Batch telemetry to avoid overloading API
        batch_size = 20
        success = True
        
        # Log telemetry count
        logger.info(f"Saving {len(self._telemetry_points)} telemetry points")
        
        # Process in batches
        for i in range(0, len(self._telemetry_points), batch_size):
            batch = self._telemetry_points[i:i+batch_size]
            
            # Format telemetry points for database
            telemetry_batch = []
            for point in batch:
                # Extract relevant fields
                telemetry_point = {
                    "lap_id": lap_id,
                    "track_position": point.get("track_position", 0),
                    "timestamp": point.get("timestamp", 0) - self._lap_start_time,
                }
                
                # Add user_id if available
                if self._user_id:
                    telemetry_point["user_id"] = self._user_id
                
                # Add optional fields if present
                for field in ["speed", "rpm", "gear", "throttle", "brake", "clutch", "steering"]:
                    if field in point:
                        telemetry_point[field] = point[field]
                        
                telemetry_batch.append(telemetry_point)
                
            try:
                # Save batch
                self._supabase.table("telemetry_points").insert(telemetry_batch).execute()
            except Exception as e:
                logger.error(f"Error saving telemetry batch: {e}")
                success = False
                
        return success
        
    def close_session(self):
        """Close the current session."""
        self._session_id = None
        self._current_lap_number = 0
        logger.info("Closed session") 