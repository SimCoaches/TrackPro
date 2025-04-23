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
        
    def set_supabase_client(self, client):
        """Set the Supabase client instance."""
        self._supabase = client
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
        if not self._supabase:
            try:
                # Import here to avoid circular imports
                from ..database.supabase_client import supabase as global_client
                if global_client:
                    logger.info("Using global Supabase client instance as fallback")
                    self._supabase = global_client
                    self._connection_disabled = False
                    return
            except Exception as e:
                logger.error(f"Error getting global Supabase client: {e}")
                self._connection_disabled = True

    def set_user_id(self, user_id):
        """Set the current user ID for associating data."""
        self._user_id = user_id
        logger.info(f"Set user ID to: {user_id}")

    def process_telemetry(self, telemetry_data):
        """Process incoming telemetry data to detect laps and save telemetry.
        
        Args:
            telemetry_data: A dictionary containing telemetry values.
            
        Returns:
            A tuple (is_new_lap, lap_number, lap_time) if a lap is completed,
            None otherwise.
        """
        # Increment debug counter
        if not hasattr(self, '_telemetry_debug_counter'):
            self._telemetry_debug_counter = 0
        self._telemetry_debug_counter += 1
        
        # Skip all Supabase operations if connection is disabled
        if self._connection_disabled:
            # Only log periodically to avoid spam
            if self._telemetry_debug_counter % 300 == 0:
                logger.warning("Supabase connection is disabled, skipping telemetry processing")
            return None
        
        # Ensure we have a session ID from the monitor
        if not self._current_session_id:
            # Log periodically if no session is active
            if self._telemetry_debug_counter % 300 == 0:
                logger.debug("Cannot process telemetry: No active session set by monitor.")
            return None

        # --- Lap Detection Logic (remains mostly the same) ---
        try:
            lap_dist_pct = telemetry_data.get('LapDistPct', -1)
            session_time = telemetry_data.get('SessionTimeSecs', 0)
            current_lap = telemetry_data.get('Lap', 0)
            
            # DEBUG: Log key telemetry values every ~5 seconds
            if self._telemetry_debug_counter % 300 == 0:
                logger.info(f"Lap Detection Debug: LapDistPct={lap_dist_pct:.3f}, Last={self._last_track_position:.3f}, Lap={current_lap}, SessionTime={session_time:.3f}")

            if lap_dist_pct < 0:
                if self._telemetry_debug_counter % 300 == 0:
                    logger.warning(f"Invalid track position: {lap_dist_pct}")
                return None # Invalid track position

            # Handle initial telemetry point
            if self._is_first_telemetry:
                self._last_track_position = lap_dist_pct
                self._lap_start_time = session_time
                self._current_lap_number = current_lap
                self._is_first_telemetry = False
                self._current_lap_data = []
                logger.info(f"Lap Saver: First telemetry received for Lap {self._current_lap_number}. Session: {self._current_session_id}")

            # Detect lap crossing (passing start/finish line)
            # Handles cases where LapDistPct might jump slightly above 1 or below 0 near the line
            crossed_line_forward = self._last_track_position > 0.9 and lap_dist_pct < 0.1
            crossed_line_backward = self._last_track_position < 0.1 and lap_dist_pct > 0.9 # Less common, but possible

            # DEBUG: If close to crossing, log more detail
            if self._last_track_position > 0.85 or lap_dist_pct < 0.15:
                if self._telemetry_debug_counter % 60 == 0:  # Log more frequently near the line
                    logger.debug(f"Near S/F Line: Last={self._last_track_position:.3f}, Current={lap_dist_pct:.3f}, CrossDetected={crossed_line_forward}")

            is_new_lap = False
            lap_time = 0
            completed_lap_number = self._current_lap_number
        
            if crossed_line_forward:
                is_new_lap = True
                lap_time = session_time - self._lap_start_time
                logger.info(f"Lap Saver: Detected potential new lap crossing S/F. Prev Lap: {completed_lap_number}, Lap Time: {lap_time:.3f}s")

                # Use iRacing's Lap value if available and seems correct
                iracing_reported_lap = telemetry_data.get('LapCompleted', completed_lap_number) # Use LapCompleted if exists
                if iracing_reported_lap >= completed_lap_number :
                    completed_lap_number = iracing_reported_lap
                    logger.info(f"Lap Saver: Using iRacing reported completed lap number: {completed_lap_number}")
                else:
                    logger.warning(f"Lap Saver: iRacing reported lap ({iracing_reported_lap}) is less than internal count ({completed_lap_number}). Using internal count.")
        
                # Get official lap time if available
                official_lap_time = telemetry_data.get('LapLastLapTime', lap_time)
                if official_lap_time > 0:
                    lap_time = official_lap_time
                    logger.info(f"Lap Saver: Using iRacing reported last lap time: {lap_time:.3f}s")

            # Store telemetry point for the current lap
            # Optimization: Consider sampling or storing only key fields
            self._current_lap_data.append(telemetry_data)
        
            # Update last position
            self._last_track_position = lap_dist_pct

            if is_new_lap and lap_time > 0:
                # Save the completed lap data
                saved_lap_id = self._save_lap_data(completed_lap_number, lap_time)

                # Start the next lap
                self._current_lap_number = current_lap # Use iRacing's current lap number
                self._lap_start_time = session_time
                self._current_lap_data = [] # Clear data for the new lap
                self._current_lap_id = saved_lap_id # Store the ID of the lap just saved
                logger.info(f"Lap Saver: Starting Lap {self._current_lap_number}")

                return True, completed_lap_number, lap_time

        except Exception as e:
            logger.error(f"Error processing telemetry: {e}", exc_info=True)

        return None # No new lap completed

    def _save_lap_data(self, lap_number, lap_time):
        """Save lap data to Supabase with retry capability."""
        # Debug connection state
        logger.info(f"Attempting to save lap {lap_number} (time: {lap_time:.3f}s)")
        logger.info(f"Connection state: Supabase client exists: {self._supabase is not None}, Session ID: {self._current_session_id}")
        
        # First check: is connection disabled flag set?
        if self._connection_disabled:
            logger.error("Cannot save lap: connection is explicitly disabled")
            return None
        
        # Check if we have a Supabase client
        logger.debug(f"[SAVE_DEBUG] Checking self._supabase. Value: {self._supabase}, Type: {type(self._supabase)}")
        if not self._supabase:
            logger.error("Cannot save lap: No Supabase client available")
            
            # Try to get the global client as a fallback
            try:
                from ..database.supabase_client import supabase as global_client
                logger.debug(f"[SAVE_DEBUG] Fallback: Got global_client. Value: {global_client}, Type: {type(global_client)}")
                if global_client:
                    logger.info("Attempting to use global Supabase client for lap save")
                    self._supabase = global_client
                    logger.debug(f"[SAVE_DEBUG] Fallback: Set self._supabase. Value: {self._supabase}, Type: {type(self._supabase)}")
                    if not self._supabase:
                        logger.error("Global client retrieval failed")
                        return None
                else:
                    logger.error("Global Supabase client not available")
                    return None
            except Exception as e:
                logger.error(f"Error getting global Supabase client: {e}")
                self._connection_disabled = True

        # Check if we have a session ID
        if not self._current_session_id:
            logger.error(f"Cannot save lap: No session ID available")
            return None

        # Check if we have a user ID
        if not self._user_id:
            logger.error("Cannot save lap data: User ID not set")
            return None

        # Debug client capabilities
        logger.debug(f"[SAVE_DEBUG] Checking capabilities of self._supabase. Value: {self._supabase}, Type: {type(self._supabase)}")
        if hasattr(self._supabase, 'table'):
            logger.info("Supabase client has 'table' method")
        else:
            logger.error("Supabase client missing 'table' method - cannot save")
            return None

        # Prepare lap data
        is_personal_best = lap_time < self._best_lap_time
        if is_personal_best:
            self._best_lap_time = lap_time
        
        lap_data = {
            "session_id": self._current_session_id,
            "lap_number": lap_number,
            "lap_time": lap_time,
            "is_valid": True, # Placeholder
            "is_personal_best": is_personal_best,
            "user_id": self._user_id, # Include user_id directly
            "metadata": json.dumps({
                 "track_db_id": self._current_track_id,
                 "car_db_id": self._current_car_id,
                "session_type": self._current_session_type
            })
        }
        
        # Make the save attempt
        try:
            logger.info(f"Saving Lap {lap_number} ({lap_time:.3f}s) for session {self._current_session_id}")
            response = self._supabase.table("laps").insert(lap_data).execute()
                
            if response.data and response.data[0].get('id'):
                saved_lap_uuid = response.data[0]['id']
                logger.info(f"Successfully saved lap {lap_number} (UUID: {saved_lap_uuid})")
                    
                # Save associated telemetry points
                if self._current_lap_data:
                    self._save_telemetry_points(saved_lap_uuid, self._current_lap_data)

                return saved_lap_uuid
            else:
                logger.error(f"Failed to save lap {lap_number}. Response: {response}")
        except Exception as e:
            logger.error(f"Error saving lap {lap_number}: {e}", exc_info=True)
            return None

    def _save_telemetry_points(self, lap_uuid, telemetry_points):
        if not self._supabase or not lap_uuid or not telemetry_points:
            logger.warning("Cannot save telemetry: Missing Supabase client, lap ID, or telemetry data.")
            return

        logger.info(f"Saving {len(telemetry_points)} telemetry points for lap {lap_uuid}")
        batch_size = 500 # Adjust batch size as needed
        saved_count = 0
        failed_count = 0

        for i in range(0, len(telemetry_points), batch_size):
            batch = telemetry_points[i:i + batch_size]
            telemetry_data_to_insert = []
            for point in batch:
                # Extract only the relevant fields needed for the database
                telemetry_data_to_insert.append({
                    "lap_id": lap_uuid,
                    "user_id": self._user_id, # Include user_id
                    "timestamp": point.get('SessionTimeSecs'), # Assuming this is the primary time key
                    "track_position": point.get('LapDistPct'),
                    "speed": point.get('Speed'),
                    "rpm": point.get('RPM'),
                    "gear": point.get('Gear'),
                    "throttle": point.get('Throttle'),
                    "brake": point.get('Brake'),
                    "clutch": point.get('Clutch'),
                    "steering": point.get('SteeringWheelAngle'),
                    # Add other relevant fields if your DB schema includes them
                })

            if not telemetry_data_to_insert:
                continue

            try:
                response = self._supabase.table("telemetry_points").insert(telemetry_data_to_insert).execute()
                if response.data:
                    saved_count += len(response.data)
                else:
                    failed_count += len(telemetry_data_to_insert)
                    logger.error(f"Failed to save telemetry batch. Response: {response}")
            except Exception as e:
                failed_count += len(telemetry_data_to_insert)
                logger.error(f"Error saving telemetry batch: {e}")

        logger.info(f"Telemetry saving complete for lap {lap_uuid}. Saved: {saved_count}, Failed: {failed_count}")

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
        if not self._supabase:
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
                    response = self._supabase.table(table).select("id").limit(1).execute()
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