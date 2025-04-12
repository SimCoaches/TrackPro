#!/usr/bin/env python3
"""
Test script to verify that telemetry data can be sent to Supabase.
This script simulates a few laps of telemetry data and sends it to Supabase.
"""

import os
import sys
import time
import uuid
import logging
import random
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupabaseTelemetryTest")

# Add the parent directory to the path so we can import trackpro
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
except ImportError:
    logger.error("Could not import IRacingLapSaver. Make sure you're running this script from the project root.")
    sys.exit(1)

def generate_test_lap(num_points=100):
    """Generate test telemetry data for a single lap."""
    lap_data = []
    
    for i in range(num_points):
        # Generate track position from 0 to 1 (around the track)
        track_position = i / num_points
        
        # Generate random telemetry data
        telemetry_point = {
            'track_position': track_position,
            'speed': random.uniform(100, 250),  # Speed in km/h
            'rpm': random.uniform(3000, 8000),  # Engine RPM
            'gear': random.randint(1, 6),       # Gear 1-6
            'throttle': random.uniform(0, 1),   # Throttle 0-1
            'brake': random.uniform(0, 1),      # Brake 0-1
            'clutch': 0,                        # Clutch 0-1
            'steering': random.uniform(-1, 1),  # Steering -1 to 1
            'timestamp': time.time() + i * 0.1,  # Timestamp increases for each point
        }
        lap_data.append(telemetry_point)
    
    return lap_data

def test_supabase_connection():
    """Test the connection to Supabase."""
    logger.info("Testing Supabase connection...")
    
    # Create an instance of IRacingLapSaver
    lap_saver = IRacingLapSaver()
    
    # Test the connection
    connection_result = lap_saver.test_connection()
    logger.info(f"Connection test result: {connection_result['connection_status']}")
    
    # Log more details
    if connection_result.get('connected'):
        logger.info("Successfully connected to Supabase")
        
        # Check if tables are accessible
        for table, info in connection_result.get('tables_accessible', {}).items():
            if info.get('accessible'):
                logger.info(f"Table '{table}' is accessible, contains {info.get('count', 0)} records")
            else:
                logger.error(f"Table '{table}' is NOT accessible: {info.get('error', 'Unknown error')}")
    else:
        logger.error("Failed to connect to Supabase")
    
    # Log any errors
    if connection_result.get('errors'):
        for error in connection_result['errors']:
            logger.error(f"Connection error: {error}")
    
    # Check if connection is disabled
    logger.debug(f"Connection disabled status: {lap_saver._connection_disabled}")
        
    return connection_result['connection_status'] == 'success'

def send_test_data():
    """Generate and send test telemetry data to Supabase."""
    logger.info("Starting test of telemetry data saving to Supabase...")
    
    # Create an instance of IRacingLapSaver
    lap_saver = IRacingLapSaver()
    
    # Check initial state
    logger.debug(f"Initial connection state: connection_disabled={lap_saver._connection_disabled}, user_id={lap_saver._user_id}")
    
    # Set a test user ID (random UUID)
    test_user_id = str(uuid.uuid4())
    logger.info(f"Using test user ID: {test_user_id}")
    lap_saver.set_user_id(test_user_id)
    
    # Verify user ID was set
    logger.debug(f"After setting, user_id={lap_saver._user_id}")
    
    # Start a test session
    track_name = "Test Track"
    car_name = "Test Car"
    session_type = "Test"
    
    logger.info(f"Creating session with track={track_name}, car={car_name}, session_type={session_type}")
    session_id = lap_saver.start_session(track_name, car_name, session_type)
    if not session_id:
        logger.error("Failed to create test session in Supabase")
        return False
    
    logger.info(f"Created test session with ID: {session_id}")
    logger.debug(f"Session state: session_id={lap_saver._current_session_id}, track_id={lap_saver._current_track_id}, car_id={lap_saver._current_car_id}")
    
    # Generate and send telemetry for 3 laps
    for lap_num in range(1, 4):
        lap_data = generate_test_lap(num_points=100)
        
        logger.info(f"Processing lap {lap_num} with {len(lap_data)} telemetry points...")
        
        # Process first point to initialize the lap
        first_result = lap_saver.process_telemetry(lap_data[0])
        logger.debug(f"First telemetry point result: {first_result}")
        
        # Process the rest of the points
        for point in lap_data[1:]:
            # Process each telemetry point
            lap_saver.process_telemetry(point)
        
        # Force a lap break for testing purposes
        # This simulates finishing a lap by crossing the start/finish line
        logger.info("Simulating lap completion (crossing start/finish line)...")
        final_point = lap_data[-1].copy()
        final_point['track_position'] = 0.95  # End of lap
        lap_saver.process_telemetry(final_point)
        
        next_point = lap_data[0].copy()
        next_point['track_position'] = 0.05  # Start of next lap
        next_point['timestamp'] = time.time()  # Update timestamp
        result = lap_saver.process_telemetry(next_point)
        
        if result:
            is_new_lap, lap_number, lap_time = result
            logger.info(f"Completed lap {lap_number} with time {lap_time:.3f}s")
        else:
            logger.warning(f"No lap completion detected for lap {lap_num}")
        
        # Small delay between laps
        time.sleep(1)
    
    # Close the session
    logger.info("Closing session...")
    lap_saver.close_session()
    
    # Check if we can retrieve the lap data
    logger.info(f"Retrieving lap data for session {session_id}...")
    lap_times = lap_saver.get_lap_times(session_id)
    if lap_times:
        logger.info(f"Retrieved {len(lap_times)} laps from Supabase:")
        for lap in lap_times:
            logger.info(f"Lap {lap['lap_number']}: {lap['lap_time']}s")
            
            # Check if there's telemetry data for this lap
            telemetry = lap_saver.get_telemetry_data(lap['id'])
            logger.info(f"  Telemetry points: {len(telemetry)}")
    else:
        logger.warning("No lap data retrieved from Supabase")
    
    return True

if __name__ == "__main__":
    # Test Supabase connection
    if test_supabase_connection():
        logger.info("Successfully connected to Supabase!")
        
        # Send test telemetry data
        if send_test_data():
            logger.info("Successfully sent test telemetry data to Supabase!")
        else:
            logger.error("Failed to send test telemetry data to Supabase.")
    else:
        logger.error("Failed to connect to Supabase.") 