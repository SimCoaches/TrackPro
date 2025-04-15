"""
Module for saving iRacing lap times and telemetry data to Supabase.
"""

import os
import time
import logging
import uuid
import json
from datetime import datetime

# Import the Supabase singleton client instead of creating a new one
from ..database.supabase_client import supabase

# Setup logging
logger = logging.getLogger(__name__)

class IRacingLapSaver:
    """
    Manages saving iRacing lap times and telemetry data to Supabase.
    """
    def __init__(self):
        """Initialize the lap saver with Supabase connection details."""
        self._supabase = None
        self._user_id = None
        self._connection_disabled = False  # Flag to track if Supabase operations should be completely disabled
        
        # Session tracking
        self._current_session_id = None
        self._current_track_id = None
        self._current_car_id = None
        self._current_session_type = None
        
        # Lap tracking
        self._current_lap_number = 0
        self._lap_start_time = 0
        self._last_track_position = 0
        self._is_first_telemetry = True
        self._current_lap_data = []
        self._current_lap_id = None
        self._best_lap_time = float('inf')
        
        # Connect to Supabase using the singleton client
        if not self._connect_to_supabase():
            self._connection_disabled = True  # If initial connection fails, completely disable Supabase operations
            logger.error("Supabase connection failed on startup. Lap saving to Supabase disabled.")

    def _connect_to_supabase(self):
        """Establish connection to Supabase using the singleton client."""
        try:
            # Get the Supabase client from the singleton
            try:
                # First, try to import from trackpro's package structure
                from ..database.supabase_client import supabase
            except (ImportError, ValueError):
                # Fall back to direct import if the relative import fails
                try:
                    from trackpro.database.supabase_client import supabase
                except ImportError:
                    # Final fallback - try to import directly without trackpro namespace
                    try:
                        from Supabase.client import supabase
                    except ImportError:
                        logger.error("Could not import Supabase client from any known location")
                        return False
                
            if not hasattr(supabase, 'client') or supabase.client is None:
                logger.error("Supabase client not initialized in the manager")
                return False
                
            self._supabase = supabase.client
            
            # Test the connection with a simple query
            try:
                # Use a simpler query that should work with any Supabase setup
                test_result = self._supabase.table("tracks").select("*").limit(1).execute()
                logger.info("Successfully connected to Supabase using TrackPro's client")
                return True
            except Exception as query_error:
                logger.error(f"Failed to query Supabase: {query_error}")
                return False
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to Supabase: {error_msg}")
            return False

    def set_user_id(self, user_id):
        """Set the current user ID for associating data."""
        self._user_id = user_id
        logger.info(f"Set user ID to: {user_id}")

    def start_session(self, track_name, car_name, session_type="Practice"):
        """
        Start a new racing session.
        
        Args:
            track_name: Name of the track
            car_name: Name of the car
            session_type: Type of session (Practice, Qualifying, Race)
        
        Returns:
            The session ID if successful, None otherwise
        """
        if self._connection_disabled:
            logger.warning("Cannot start session: Supabase connection is disabled.")
            return None
            
        if not self._supabase:
            logger.error("Cannot start session: Supabase connection not available")
            self._connection_disabled = True  # Disable future attempts
            return None
        
        # --- Robust User ID Retrieval with Retry ---
        retry_attempts = 3
        retry_delay = 0.5 # seconds
        
        for attempt in range(retry_attempts):
            if not self._user_id:
                try:
                    from ..auth.user_manager import get_current_user
                    user = get_current_user()
                    if user and hasattr(user, 'user_id') and user.user_id:
                        self._user_id = user.user_id
                        logger.info(f"Attempt {attempt+1}: Set user ID for session from user.user_id: {self._user_id}")
                        break # Exit loop if user_id found
                    elif user and hasattr(user, 'id') and user.id:
                        self._user_id = user.id
                        logger.info(f"Attempt {attempt+1}: Set user ID for session from user.id: {self._user_id}")
                        break # Exit loop if user_id found
                    else:
                         # Try checking user_details as a fallback (though less reliable right after signup)
                        try:
                            # Ensure we use the correct user_id field name based on previous migration
                            details_response = self._supabase.table("user_details").select("user_id").eq("user_id", user.id if user else None).limit(1).execute()
                            if details_response.data and len(details_response.data) > 0:
                                self._user_id = details_response.data[0].get('user_id')
                                if self._user_id:
                                     logger.info(f"Attempt {attempt+1}: Set user ID from user_details fallback: {self._user_id}")
                                     break # Exit loop if user_id found
                        except Exception as ud_error:
                            logger.debug(f"Attempt {attempt+1}: Could not get user ID from user_details: {ud_error}")
                            
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1}: Error getting current user: {e}")

            if self._user_id:
                 break # Exit loop if user_id found in this attempt

            if attempt < retry_attempts - 1:
                 logger.warning(f"Attempt {attempt+1}: User ID not found, retrying in {retry_delay}s...")
                 time.sleep(retry_delay)
            else:
                 logger.error(f"Failed to obtain user ID after {retry_attempts} attempts. Cannot create session.")
                 return None # Explicitly fail if no user_id after retries
        # --- End User ID Retrieval ---

        # Ensure we definitely have a user ID now
        if not self._user_id:
             logger.error("Cannot start session: User ID is missing.")
             return None

        # Check if track exists or create it
        track_id = self._get_or_create_track(track_name)
        if not track_id:
            logger.error(f"Failed to get or create track: {track_name}")
            return None
        
        # Check if car exists or create it
        car_id = self._get_or_create_car(car_name)
        if not car_id:
            logger.error(f"Failed to get or create car: {car_name}")
            return None
        
        # Create a new session
        try:
            session_id = str(uuid.uuid4())
            session_data = {
                "id": session_id,
                "user_id": self._user_id, # user_id is now guaranteed to be non-None
                "track_id": track_id,
                "car_id": car_id,
                "session_type": session_type,
                "session_date": datetime.now().isoformat()
            }
            
            # Optional: Add email if needed (though user_id should be primary)
            # try:
            #     user_response = self._supabase.table("user_profiles").select("email").eq("user_id", self._user_id).execute()
            #     if user_response.data and len(user_response.data) > 0 and 'email' in user_response.data[0]:
            #         session_data["email"] = user_response.data[0]['email']
            # except Exception as email_error:
            #     logger.warning(f"Could not get email for user {self._user_id}: {email_error}")

            logger.info(f"Attempting to create session with data: {session_data}")
            result = self._supabase.table("sessions").insert(session_data).execute()
                
            if result.data:
                self._current_session_id = session_id
                self._current_track_id = track_id
                self._current_car_id = car_id
                self._current_session_type = session_type
                self._current_lap_number = 0
                self._is_first_telemetry = True
                self._current_lap_data = []
                self._best_lap_time = float('inf')
                logger.info(f"Started new session: {session_id} - {track_name} - {car_name} - {session_type}")
                return session_id
            else:
                # Log the specific error if available in the response
                error_details = getattr(result, 'error', None) or getattr(result, 'message', 'No data returned')
                logger.error(f"Failed to create session in Supabase. Error: {error_details}")
                return None
                
        except Exception as insert_error:
            # Catch potential exceptions during insert (e.g., RLS violation, network issues)
            logger.error(f"Error inserting session into Supabase: {insert_error}")
            # Log the user ID that was attempted
            logger.error(f"Attempted insert with User ID: {self._user_id}")

            # Do NOT proceed or mask the error by returning a session ID
            # The session was not created successfully in the database.
            return None

    def _get_or_create_track(self, track_name):
        """
        Get a track ID by name or create it if it doesn't exist.
        
        Args:
            track_name: Name of the track
        
        Returns:
            The track ID if successful, None otherwise
        """
        if not track_name or not isinstance(track_name, str):
            logger.error("Invalid track name")
            return None
            
        try:
            # Try to find the track
            result = self._supabase.table("tracks").select("id").eq("name", track_name).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Found existing track: {track_name} (ID: {result.data[0]['id']})")
                return result.data[0]["id"]
            
            # Track not found, create it
            track_data = {
                "name": track_name
            }
            
            insert_result = self._supabase.table("tracks").insert(track_data).execute()
            
            if insert_result.data and len(insert_result.data) > 0:
                logger.info(f"Created new track: {track_name} (ID: {insert_result.data[0]['id']})")
                return insert_result.data[0]["id"]
            
            logger.error(f"Failed to create track: {track_name} - no data returned")
            return None
            
        except Exception as e:
            logger.error(f"Error getting or creating track: {e}")
            return None

    def _get_or_create_car(self, car_name):
        """
        Get a car ID by name or create it if it doesn't exist.
        
        Args:
            car_name: Name of the car
        
        Returns:
            The car ID if successful, None otherwise
        """
        if not car_name or not isinstance(car_name, str):
            logger.error("Invalid car name")
            return None
            
        try:
            # Try to find the car
            result = self._supabase.table("cars").select("id").eq("name", car_name).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Found existing car: {car_name} (ID: {result.data[0]['id']})")
                return result.data[0]["id"]
            
            # Car not found, create it
            car_data = {
                "name": car_name
            }
            
            insert_result = self._supabase.table("cars").insert(car_data).execute()
            
            if insert_result.data and len(insert_result.data) > 0:
                logger.info(f"Created new car: {car_name} (ID: {insert_result.data[0]['id']})")
                return insert_result.data[0]["id"]
            
            logger.error(f"Failed to create car: {car_name} - no data returned")
            return None
            
        except Exception as e:
            logger.error(f"Error getting or creating car: {e}")
            return None

    def process_telemetry(self, telemetry_data):
        """
        Process incoming telemetry data and save per lap.
        
        Args:
            telemetry_data: Dictionary containing telemetry data
            
        Returns:
            Tuple of (is_new_lap, lap_number, lap_time) or None if not a new lap
        """
        # Ensure we have a user ID - try to get it if not set
        if not self._user_id:
            try:
                # First try to get from telemetry_data if present
                if 'user_id' in telemetry_data:
                    self._user_id = telemetry_data['user_id']
                    logger.info(f"Setting user ID from telemetry data: {self._user_id}")
                else:
                    # Try to get from user_manager
                    try:
                        from ..auth.user_manager import get_current_user
                        user = get_current_user()
                        if user and hasattr(user, 'id'):
                            self._user_id = user.id
                            logger.info(f"Set user ID from user_manager: {self._user_id}")
                    except Exception as user_error:
                        logger.error(f"Error getting current user ID: {user_error}")
            except Exception as e:
                logger.error(f"Error setting user ID in process_telemetry: {e}")
        
        # Include detailed telemetry data diagnostics once in a while
        if not hasattr(self, '_telemetry_debug_counter'):
            self._telemetry_debug_counter = 0
        self._telemetry_debug_counter += 1
        
        if self._telemetry_debug_counter % 300 == 0:  # Log every ~5 seconds (at 60Hz)
            # Create a detailed debug log of all available data
            available_data = {k: v for k, v in telemetry_data.items() if k in ['track_position', 'speed', 'rpm', 'track_name', 'car_name']}
            logger.debug(f"Telemetry data details: {available_data}")
        
        # Skip all Supabase operations if connection is disabled
        if self._connection_disabled:
            if self._telemetry_debug_counter % 300 == 0:
                logger.warning("Supabase connection is disabled, skipping telemetry processing")
            return None
        
        # Ensure we have a session
        if not self._current_session_id:
            # Only log at warning level if this is the first time or state changed
            if not hasattr(self, '_no_session_logged') or not self._no_session_logged:
                logger.warning("Cannot process telemetry: No active session")
                self._no_session_logged = True
            else:
                # Use debug level for subsequent messages to reduce noise
                logger.debug("Cannot process telemetry: No active session")
                
            # Try to auto-recover if possible by looking for track and car information in the telemetry
            if 'track_name' in telemetry_data and 'car_name' in telemetry_data:
                logger.info(f"Attempting to auto-start session using telemetry: {telemetry_data['track_name']} / {telemetry_data['car_name']}")
                session_id = self.start_session(telemetry_data['track_name'], telemetry_data['car_name'])
                if not session_id:
                    # If session creation failed, disable Supabase operations to prevent more failures
                    self._connection_disabled = True
                    logger.error("Failed to create session in Supabase. Lap saving to Supabase disabled.")
                    return None
                if self._current_session_id:
                    # Reset the flag since we now have a session
                    self._no_session_logged = False
                else:
                    return None  # Still no session, can't continue
            else:
                if self._telemetry_debug_counter % 300 == 0:
                    logger.warning("Missing track_name or car_name in telemetry, cannot auto-start session")
                    logger.warning(f"Available keys in telemetry: {list(telemetry_data.keys())}")
                return None  # No way to auto-recover
        
        # Check if we have required data for lap detection
        track_position = telemetry_data.get('track_position')
        if track_position is None:
            # Try to find track position in alternative fields
            for alt_field in ['LapDistPct', 'lap_dist_pct', 'track_pos', 'TrackPos']:
                if alt_field in telemetry_data:
                    track_position = telemetry_data[alt_field]
                    telemetry_data['track_position'] = track_position
                    break
                    
            if track_position is None:
                # Can't detect lap without track position
                logger.debug("Cannot detect lap: track_position field missing in telemetry data")
                return None
        
        # Get current track position (0.0 to 1.0)
        current_position = float(track_position)
        if current_position < 0 or current_position > 1:
            # Normalize to 0-1 range if needed
            if current_position > 1:
                current_position = current_position / 100.0 if current_position <= 100 else current_position % 1.0
            logger.debug(f"Normalized track position from {track_position} to {current_position}")
            telemetry_data['track_position'] = current_position
        
        # Deep copy telemetry data to avoid reference issues
        telemetry_point = telemetry_data.copy()
        
        # Add timestamp to the telemetry data
        telemetry_point['timestamp'] = time.time()
        
        # Detect if we've crossed the start/finish line
        is_new_lap = False
        lap_time = 0.0
        
        # Check for crossing the start/finish line (track position goes from near 1.0 to near 0.0)
        if not self._is_first_telemetry and self._last_track_position > 0.9 and current_position < 0.1:
            # We've crossed the start/finish line
            self._current_lap_number += 1
            is_new_lap = True
            
            # Calculate lap time if we have a valid lap start time
            if self._lap_start_time > 0:
                lap_time = telemetry_point['timestamp'] - self._lap_start_time
            
            # Save the current lap data if we have any
            if len(self._current_lap_data) > 0:
                self._save_lap_data(self._current_lap_number - 1, lap_time)
                
            # Reset for new lap
            self._current_lap_data = []
            self._lap_start_time = telemetry_point['timestamp']
            self._current_lap_id = None
            
            logger.info(f"Detected new lap: {self._current_lap_number}, Lap time: {lap_time:.3f} seconds")
        
        # Save the first lap start time
        if self._is_first_telemetry:
            self._lap_start_time = telemetry_point['timestamp']
            self._is_first_telemetry = False
        
        # Add data point to current lap
        self._current_lap_data.append(telemetry_point)
        
        # Save telemetry point to database if we have a lap ID
        if self._current_lap_id:
            self._save_telemetry_point(self._current_lap_id, telemetry_point)
        
        # Update last track position
        self._last_track_position = current_position
        
        # Return new lap info if a new lap was detected
        if is_new_lap:
            return (is_new_lap, self._current_lap_number, lap_time)
        return None

    def _save_lap_data(self, lap_number, lap_time):
        """
        Save lap data to Supabase with retry capability.
        
        Args:
            lap_number: The lap number
            lap_time: The lap time in seconds
        
        Returns:
            The lap ID if successful, None otherwise
        """
        if not self._supabase or not self._current_session_id:
            logger.error("Cannot save lap data: Supabase connection or session ID not available")
            return None
        
        # Final check for user ID before saving lap data
        if not self._user_id:
            try:
                # Try to get from user_manager
                from ..auth.user_manager import get_current_user
                user = get_current_user()
                if user and hasattr(user, 'id'):
                    self._user_id = user.id
                    logger.info(f"Set user ID before saving lap: {self._user_id}")
            except Exception as e:
                logger.warning(f"Could not get user ID before saving lap: {e}")
        
        # Check if this is a personal best
        is_personal_best = lap_time < self._best_lap_time
        if is_personal_best:
            self._best_lap_time = lap_time
        
        # Create lap entry - no manual ID needed, Supabase will auto-generate it 
        lap_data = {
            "session_id": self._current_session_id,
            "lap_number": lap_number,
            "lap_time": lap_time,
            "is_valid": True,  # Assume all laps are valid for now
            "is_personal_best": is_personal_best,
            "metadata": json.dumps({
                "track_id": self._current_track_id,
                "car_id": self._current_car_id,
                "session_type": self._current_session_type
            })
        }
        
        # Add user_id if available
        if self._user_id:
            lap_data["user_id"] = self._user_id
            logger.info(f"Including user_id {self._user_id} in lap data")
        else:
            logger.warning("No user_id available for lap data")
        
        # Set up retry logic
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                result = self._supabase.table("laps").insert(lap_data).execute()
                
                if result.data and len(result.data) > 0:
                    # Get the generated ID from the result
                    lap_id = result.data[0]["id"]
                    logger.info(f"Saved lap {lap_number} with time {lap_time:.3f}s to Supabase")
                    
                    # Set current lap ID for telemetry data
                    self._current_lap_id = lap_id
                    
                    # Make sure any pending telemetry data is flushed
                    self._flush_telemetry_batch()
                    
                    # Save all telemetry points for this lap
                    telemetry_count = len(self._current_lap_data)
                    logger.info(f"Saving {telemetry_count} telemetry points for lap {lap_number}")
                    
                    # Process in smaller batches for better reliability
                    batch_size = 10
                    for i in range(0, len(self._current_lap_data), batch_size):
                        batch = self._current_lap_data[i:i+batch_size]
                        for point in batch:
                            self._save_telemetry_point(lap_id, point)
                        # Force a flush after each mini-batch
                        self._flush_telemetry_batch()
                    
                    logger.info(f"Successfully saved lap {lap_number} with all telemetry data")
                    return lap_id
                else:
                    retry_count += 1
                    error_msg = "No data returned from Supabase insert"
                    
                    if retry_count >= max_retries:
                        logger.error(f"Failed to save lap data after {max_retries} attempts: {error_msg}")
                        return None
                    else:
                        logger.warning(f"Lap data insert attempt {retry_count} failed: {error_msg}. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
            
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                if "HTTP/2 protocol error" in error_msg or "Connection terminated" in error_msg:
                    # If it's a connection error, try reconnecting to Supabase
                    logger.warning(f"Connection error while saving lap data. Reconnecting... Attempt {retry_count}")
                    self._connect_to_supabase()
                
                if retry_count >= max_retries:
                    logger.error(f"Failed to save lap data after {max_retries} attempts: {error_msg}")
                    return None
                else:
                    logger.warning(f"Lap data insert attempt {retry_count} failed: {error_msg}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
        
        return None

    # Keep track of points to batch insert them
    _telemetry_batch = []
    _max_batch_size = 20  # Adjust based on performance testing
    
    def _save_telemetry_point(self, lap_id, telemetry_point):
        """
        Save a telemetry data point to Supabase using batch processing.
        
        Args:
            lap_id: The UUID of the lap
            telemetry_point: Dictionary containing telemetry data
        """
        if not self._supabase:
            return False
        
        try:
            # Extract relevant fields
            point_data = {
                "lap_id": lap_id,
                "track_position": telemetry_point.get('track_position', 0),
                "speed": telemetry_point.get('speed', 0),
                "rpm": telemetry_point.get('rpm', 0),
                "gear": telemetry_point.get('gear', 0),
                "throttle": telemetry_point.get('throttle', 0),
                "brake": telemetry_point.get('brake', 0),
                "clutch": telemetry_point.get('clutch', 0),
                "steering": telemetry_point.get('steering', 0),
                "timestamp": telemetry_point.get('timestamp', 0) - self._lap_start_time,  # Relative to lap start
                "user_id": self._user_id  # Add user_id from the class instance
            }
            
            # Add to batch
            self._telemetry_batch.append(point_data)
            
            # If batch size reaches threshold, insert the batch
            if len(self._telemetry_batch) >= self._max_batch_size:
                return self._flush_telemetry_batch()
            
            return True
            
        except Exception as e:
            logger.error(f"Error preparing telemetry point: {e}")
            return False
    
    def _flush_telemetry_batch(self):
        """Flush the telemetry batch to Supabase."""
        if not self._telemetry_batch:
            return True
            
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                # Insert the batch
                result = self._supabase.table("telemetry_points").insert(self._telemetry_batch).execute()
                batch_size = len(self._telemetry_batch)
                self._telemetry_batch = []  # Clear the batch after successful insert
                
                logger.debug(f"Batch inserted {batch_size} telemetry points successfully")
                return True
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                if "HTTP/2 protocol error" in error_msg or "Connection terminated" in error_msg:
                    # If it's a connection error, try reconnecting to Supabase
                    logger.warning(f"Connection error on batch insert. Reconnecting... Attempt {retry_count}")
                    # Sleep before reconnecting to allow the connection to fully close
                    time.sleep(2)
                    # Try to reconnect
                    reconnect_success = self._connect_to_supabase()
                    if not reconnect_success:
                        logger.error("Failed to reconnect to Supabase")
                        # If we can't reconnect, reduce batch size for the next attempt
                        if len(self._telemetry_batch) > 5 and retry_count < max_retries - 1:
                            # Split the batch in half and try with fewer items
                            half_size = len(self._telemetry_batch) // 2
                            second_half = self._telemetry_batch[half_size:]
                            self._telemetry_batch = self._telemetry_batch[:half_size]
                            logger.warning(f"Reduced batch size to {len(self._telemetry_batch)} items")
                            # We'll retry with the first half, and store the second half for later
                            self._telemetry_batch.extend(second_half)  # Add back after the current attempt
                
                if retry_count >= max_retries:
                    logger.error(f"Failed to insert telemetry batch after {max_retries} attempts: {error_msg}")
                    # Don't clear the batch completely, save a few points for diagnostics
                    if len(self._telemetry_batch) > 10:
                        self._telemetry_batch = self._telemetry_batch[:10]
                        logger.warning("Kept 10 telemetry points for diagnostics")
                    return False
                else:
                    logger.warning(f"Batch insert attempt {retry_count} failed: {error_msg}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    
        return False

    def get_lap_times(self, session_id=None):
        """
        Get all lap times for a session.
        
        Args:
            session_id: The session ID (defaults to current session)
            
        Returns:
            List of lap time data
        """
        if not self._supabase:
            logger.error("Cannot get lap times: Supabase connection not available")
            return []
        
        session_id = session_id or self._current_session_id
        if not session_id:
            logger.error("Cannot get lap times: No session ID specified")
            return []
        
        try:
            result = self._supabase.table("laps").select("*").eq("session_id", session_id).order("lap_number").execute()
            
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
        if not self._supabase:
            logger.error("Cannot get telemetry data: Supabase connection not available")
            return []
        
        try:
            result = self._supabase.table("telemetry_points").select("*").eq("lap_id", lap_id).order("track_position").execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"Error getting telemetry data: {e}")
            return []

    def close_session(self):
        """Close the current session and flush any pending data."""
        # Flush any pending telemetry data
        if len(self._telemetry_batch) > 0:
            logger.info(f"Flushing {len(self._telemetry_batch)} pending telemetry points")
            self._flush_telemetry_batch()
        
        # Reset session state
        self._current_session_id = None
        self._current_track_id = None
        self._current_car_id = None
        self._current_session_type = None
        self._current_lap_number = 0
        self._is_first_telemetry = True
        self._current_lap_data = []
        logger.info("Closed current session")

    def test_connection(self):
        """Test the Supabase connection and return diagnostic information.
        
        Returns:
            dict: A dictionary containing connection status and diagnostic information
        """
        result = {
            "connection_status": "unknown",
            "env_vars_set": {},
            "connected": False,
            "tables_accessible": {},
            "errors": []
        }
        
        # Check Supabase client exists
        if not self._supabase:
            result["connection_status"] = "failed"
            result["errors"].append("Supabase client not initialized")
            return result
        
        # Try to connect to Supabase
        try:
            if not self._supabase:
                reconnected = self._connect_to_supabase()
                if not reconnected:
                    result["connection_status"] = "failed"
                    result["errors"].append("Failed to reconnect to Supabase")
                    return result
            
            result["connected"] = True
            
            # Test database access by checking if tables exist
            tables_to_check = ["tracks", "cars", "sessions", "laps", "telemetry_points"]
            for table in tables_to_check:
                try:
                    # Use a simple query that works with any table
                    response = self._supabase.table(table).select("*").limit(1).execute()
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
            
            # Check if all tables are accessible
            all_tables_accessible = all(info.get("accessible", False) for info in result["tables_accessible"].values())
            
            if all_tables_accessible:
                result["connection_status"] = "success"
            else:
                result["connection_status"] = "partial"
                
            return result
            
        except Exception as e:
            result["connection_status"] = "failed"
            result["errors"].append(f"Connection test error: {e}")
            return result 