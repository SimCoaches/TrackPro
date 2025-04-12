#!/usr/bin/env python3
"""
Direct test of Supabase connection without relying on TrackPro's import structure.
This script creates tables and tests saving telemetry data directly to Supabase.
"""

import os
import sys
import time
import uuid
import logging
import supabase
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupabaseTelemetryTest")

# Supabase credentials - hardcoded for testing
SUPABASE_URL = "https://xbfotxwpntqplvvsffrr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhiZm90eHdwbnRxcGx2dnNmZnJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQzMTM5NjUsImV4cCI6MjA1OTg4OTk2NX0.AwLUhaxQQn9xnpTwgOrRIdWQYsVI9-ikC2Qb-6SR2h8"

class SupabaseTester:
    def __init__(self):
        """Initialize the Supabase tester."""
        self.supabase_client = None
        self.test_user_id = str(uuid.uuid4())
        self.session_id = None
        self.track_id = None
        self.car_id = None
        self.current_lap_id = None
        
    def connect(self):
        """Connect to Supabase."""
        try:
            if not SUPABASE_URL or not SUPABASE_KEY:
                logger.error("Missing Supabase credentials")
                return False
                
            logger.info(f"Connecting to Supabase: {SUPABASE_URL}")
            self.supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Successfully connected to Supabase")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            return False
            
    def test_connection(self):
        """Test the Supabase connection."""
        if not self.supabase_client:
            logger.error("No Supabase client available")
            return False
            
        try:
            # Test with a simple query
            result = self.supabase_client.table("tracks").select("*").limit(1).execute()
            logger.info(f"Connection test successful: {len(result.data)} tracks found")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def create_test_track(self):
        """Create a test track in Supabase."""
        if not self.supabase_client:
            return None
            
        track_name = f"Test Track {uuid.uuid4().hex[:8]}"
        
        try:
            # Create track
            track_data = {"name": track_name}
            result = self.supabase_client.table("tracks").insert(track_data).execute()
            
            if result.data and len(result.data) > 0:
                self.track_id = result.data[0]["id"]
                logger.info(f"Created test track: {track_name} (ID: {self.track_id})")
                return self.track_id
            else:
                logger.error("Failed to create test track: No data returned")
                return None
        except Exception as e:
            logger.error(f"Failed to create test track: {e}")
            return None
    
    def create_test_car(self):
        """Create a test car in Supabase."""
        if not self.supabase_client:
            return None
            
        car_name = f"Test Car {uuid.uuid4().hex[:8]}"
        
        try:
            # Create car
            car_data = {"name": car_name}
            result = self.supabase_client.table("cars").insert(car_data).execute()
            
            if result.data and len(result.data) > 0:
                self.car_id = result.data[0]["id"]
                logger.info(f"Created test car: {car_name} (ID: {self.car_id})")
                return self.car_id
            else:
                logger.error("Failed to create test car: No data returned")
                return None
        except Exception as e:
            logger.error(f"Failed to create test car: {e}")
            return None
    
    def create_test_session(self):
        """Create a test session in Supabase."""
        if not self.supabase_client or not self.track_id or not self.car_id:
            logger.error("Missing required data to create session")
            return None
            
        try:
            # Create session
            session_id = str(uuid.uuid4())
            session_data = {
                "id": session_id,
                "user_id": self.test_user_id,
                "track_id": self.track_id,
                "car_id": self.car_id,
                "session_type": "Test",
                "session_date": datetime.now().isoformat()
            }
            
            result = self.supabase_client.table("sessions").insert(session_data).execute()
            
            if result.data and len(result.data) > 0:
                self.session_id = session_id
                logger.info(f"Created test session: {session_id}")
                return session_id
            else:
                logger.error("Failed to create test session: No data returned")
                return None
        except Exception as e:
            logger.error(f"Failed to create test session: {e}")
            return None
    
    def create_test_lap(self, lap_number, lap_time):
        """Create a test lap in Supabase."""
        if not self.supabase_client or not self.session_id:
            logger.error("Missing required data to create lap")
            return None
            
        try:
            # Create lap
            lap_id = str(uuid.uuid4())
            lap_data = {
                "id": lap_id,
                "session_id": self.session_id,
                "user_id": self.test_user_id,
                "lap_number": lap_number,
                "lap_time": lap_time,
                "is_valid": True,
                "is_personal_best": False
            }
            
            result = self.supabase_client.table("laps").insert(lap_data).execute()
            
            if result.data and len(result.data) > 0:
                self.current_lap_id = lap_id
                logger.info(f"Created test lap: {lap_number} with time {lap_time:.3f}s")
                return lap_id
            else:
                logger.error("Failed to create test lap: No data returned")
                return None
        except Exception as e:
            logger.error(f"Failed to create test lap: {e}")
            return None
    
    def save_telemetry_point(self, track_position, speed, throttle, brake, steering, timestamp):
        """Save a telemetry point to Supabase."""
        if not self.supabase_client or not self.current_lap_id:
            logger.error("Missing required data to save telemetry point")
            return False
            
        try:
            # Create telemetry point
            point_data = {
                "lap_id": self.current_lap_id,
                "track_position": track_position,
                "speed": speed,
                "throttle": throttle,
                "brake": brake,
                "steering": steering,
                "timestamp": timestamp
            }
            
            result = self.supabase_client.table("telemetry_points").insert(point_data).execute()
            
            if result.data and len(result.data) > 0:
                return True
            else:
                logger.error("Failed to save telemetry point: No data returned")
                return False
        except Exception as e:
            logger.error(f"Failed to save telemetry point: {e}")
            return False
    
    def save_test_telemetry(self, num_points=10):
        """Save test telemetry data for a lap."""
        if not self.current_lap_id:
            logger.error("No lap created yet")
            return False
            
        success_count = 0
        
        # Create telemetry points along a lap
        for i in range(num_points):
            track_position = i / num_points
            timestamp = time.time() + i * 0.1
            
            if self.save_telemetry_point(
                track_position=track_position,
                speed=100 + i * 5,
                throttle=0.8,
                brake=0.2,
                steering=0.0,
                timestamp=timestamp
            ):
                success_count += 1
                
        logger.info(f"Saved {success_count}/{num_points} telemetry points")
        return success_count == num_points
        
    def retrieve_lap_data(self):
        """Retrieve lap data from Supabase."""
        if not self.supabase_client or not self.session_id:
            logger.error("Missing required data to retrieve laps")
            return None
            
        try:
            result = self.supabase_client.table("laps").select("*").eq("session_id", self.session_id).execute()
            
            if result.data:
                logger.info(f"Retrieved {len(result.data)} laps")
                return result.data
            else:
                logger.warning("No laps found")
                return []
        except Exception as e:
            logger.error(f"Failed to retrieve laps: {e}")
            return None
            
    def retrieve_telemetry_points(self, lap_id):
        """Retrieve telemetry points for a lap from Supabase."""
        if not self.supabase_client:
            logger.error("No Supabase client available")
            return None
            
        try:
            result = self.supabase_client.table("telemetry_points").select("*").eq("lap_id", lap_id).execute()
            
            if result.data:
                logger.info(f"Retrieved {len(result.data)} telemetry points for lap {lap_id}")
                return result.data
            else:
                logger.warning(f"No telemetry points found for lap {lap_id}")
                return []
        except Exception as e:
            logger.error(f"Failed to retrieve telemetry points: {e}")
            return None
            
    def run_full_test(self):
        """Run a full test of saving telemetry data to Supabase."""
        # Connect to Supabase
        if not self.connect():
            logger.error("Failed to connect to Supabase")
            return False
            
        # Test connection
        if not self.test_connection():
            logger.error("Failed to test Supabase connection")
            return False
            
        # Create test track
        if not self.create_test_track():
            logger.error("Failed to create test track")
            return False
            
        # Create test car
        if not self.create_test_car():
            logger.error("Failed to create test car")
            return False
            
        # Create test session
        if not self.create_test_session():
            logger.error("Failed to create test session")
            return False
            
        # Create and save laps with telemetry
        for lap_num in range(1, 4):
            lap_time = 60.0 + lap_num * 0.5  # Simulated lap times
            
            # Create lap
            lap_id = self.create_test_lap(lap_num, lap_time)
            if not lap_id:
                logger.error(f"Failed to create lap {lap_num}")
                continue
                
            # Save telemetry data
            if not self.save_test_telemetry(num_points=20):
                logger.error(f"Failed to save telemetry for lap {lap_num}")
                continue
                
            logger.info(f"Successfully saved lap {lap_num} with telemetry data")
            
        # Retrieve lap data
        laps = self.retrieve_lap_data()
        if not laps:
            logger.error("Failed to retrieve lap data")
            return False
            
        # Retrieve telemetry points for each lap
        for lap in laps:
            points = self.retrieve_telemetry_points(lap["id"])
            if points is None:
                logger.error(f"Failed to retrieve telemetry points for lap {lap['lap_number']}")
                continue
                
        logger.info("Full test completed successfully")
        return True
        
if __name__ == "__main__":
    tester = SupabaseTester()
    success = tester.run_full_test()
    
    if success:
        logger.info("Successfully tested Supabase telemetry saving!")
        sys.exit(0)
    else:
        logger.error("Failed to test Supabase telemetry saving")
        sys.exit(1) 