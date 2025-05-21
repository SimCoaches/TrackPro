#!/usr/bin/env python
"""
Test script for the lap type classification system.

This script creates synthetic telemetry data that simulates different
lap scenarios (out-lap, in-lap, timed lap) and tests how the LapIndexer
classifies them.
"""

import os
import sys
import logging
import time
from datetime import datetime

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the LapIndexer
from trackpro.race_coach.lap_indexer import LapIndexer, LapState

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_synthetic_frame(session_time, lap_completed, lap_number, lap_dist_pct, on_pit_road, lap_invalidated=False, lap_last_lap_time=-1.0):
    """Create a synthetic telemetry frame for testing."""
    return {
        "SessionTimeSecs": session_time,
        "LapCompleted": lap_completed,
        "Lap": lap_number, 
        "LapDistPct": lap_dist_pct,
        "OnPitRoad": on_pit_road,
        "LapInvalidated": lap_invalidated,
        "LapLastLapTime": lap_last_lap_time,
        # Add other telemetry values typical in iRacing frames
        "Speed": 100.0 * (1.0 - on_pit_road * 0.7),  # Slower on pit road
        "RPM": 5000.0 * (1.0 - on_pit_road * 0.7),
        "Gear": 3 if not on_pit_road else 1,
        "Throttle": 0.8 if not on_pit_road else 0.3,
        "Brake": 0.0,
        "LatAccel": 0.0,
        "LongAccel": 0.0,
        "SteeringWheelAngle": 0.0
    }

def generate_standard_out_lap():
    """Generate telemetry for a standard out-lap (starts on pit, ends on track)."""
    frames = []
    session_time = 0.0
    lap_completed = 0
    lap_number = 1  # LapCompleted + 1
    
    # Start on pit road
    for i in range(10):
        lap_dist = i * 0.01  # 0.00 to 0.09
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=True
        ))
    
    # Exit pit road
    session_time += 10
    for i in range(10):
        lap_dist = 0.1 + i * 0.01  # 0.10 to 0.19
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=(i < 5)
        ))
    
    # Rest of the out-lap on track
    session_time += 10
    for i in range(81):
        lap_dist = 0.2 + i * 0.01  # 0.20 to 1.00
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=False
        ))
    
    return frames

def generate_standard_timed_lap():
    """Generate telemetry for a standard timed lap (whole lap on track)."""
    frames = []
    session_time = 100.0  # Continue from where out-lap ended
    lap_completed = 1
    lap_number = 2  # LapCompleted + 1
    lap_last_lap_time = 90.0  # Time for the out-lap
    
    # Full lap on track
    for i in range(101):
        lap_dist = i * 0.01  # 0.00 to 1.00
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=False,
            lap_last_lap_time=lap_last_lap_time if i == 0 else -1.0  # First frame has lap time
        ))
    
    return frames

def generate_standard_in_lap():
    """Generate telemetry for a standard in-lap (starts on track, ends on pit)."""
    frames = []
    session_time = 200.0  # Continue from where timed lap ended
    lap_completed = 2
    lap_number = 3  # LapCompleted + 1
    lap_last_lap_time = 100.0  # Time for the timed lap
    
    # Start on track
    for i in range(80):
        lap_dist = i * 0.01  # 0.00 to 0.79
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=False,
            lap_last_lap_time=lap_last_lap_time if i == 0 else -1.0  # First frame has lap time
        ))
    
    # Enter pit road
    session_time += 80
    for i in range(10):
        lap_dist = 0.8 + i * 0.01  # 0.80 to 0.89
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=(i >= 5)
        ))
    
    # Rest of in-lap on pit road
    session_time += 10
    for i in range(11):
        lap_dist = 0.9 + i * 0.01  # 0.90 to 1.00
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, lap_dist, on_pit_road=True
        ))
    
    return frames

def generate_lap_with_early_finalize():
    """Generate telemetry for a timed lap with immediate tow after S/F line."""
    frames = []
    session_time = 300.0  # Continue from where in-lap ended
    lap_completed = 3
    lap_number = 4  # LapCompleted + 1
    lap_last_lap_time = 110.0  # Time for the in-lap
    
    # Start on track
    for i in range(101):
        lap_dist = i * 0.01  # 0.00 to 1.00
        current_session_time = session_time + i
        
        # Set the LapLastLapTime on the last frame to simulate crossing S/F
        is_last_frame = (i == 100)
        current_lap_last_lap_time = lap_last_lap_time if i == 0 else (-1.0 if not is_last_frame else 100.0)
        
        frames.append(create_synthetic_frame(
            current_session_time, lap_completed, lap_number, lap_dist, on_pit_road=False,
            lap_last_lap_time=current_lap_last_lap_time
        ))
    
    # Add a few frames after finish with LapLastLapTime set
    # But LapCompleted doesn't increment because the driver immediately towed
    session_time += 101
    lap_last_lap_time = 100.0  # Time for the just completed lap
    
    # A few frames with the new lap time
    for i in range(5):
        frames.append(create_synthetic_frame(
            session_time + i, lap_completed, lap_number, 0.01, on_pit_road=True,
            lap_last_lap_time=lap_last_lap_time
        ))
    
    return frames

def run_test():
    """Run tests on the LapIndexer with different lap scenarios."""
    indexer = LapIndexer()
    
    # Generate test data
    out_lap_frames = generate_standard_out_lap()
    timed_lap_frames = generate_standard_timed_lap()
    in_lap_frames = generate_standard_in_lap()
    early_finalize_frames = generate_lap_with_early_finalize()
    
    # Combine all frames
    all_frames = out_lap_frames + timed_lap_frames + in_lap_frames + early_finalize_frames
    
    # Process frames through the indexer
    for frame in all_frames:
        indexer.on_frame(frame)
    
    # Finalize to make sure all laps are processed
    indexer.finalize()
    
    # Get processed laps and analyze them
    laps = indexer.get_laps()
    
    # Print analysis
    logger.info(f"Total frames processed: {len(all_frames)}")
    logger.info(f"Total laps detected: {len(laps)}")
    
    # Analyze each lap
    for i, lap in enumerate(laps):
        lap_num = lap["lap_number_sdk"]
        lap_state = lap["lap_state"]
        duration = lap["duration_seconds"]
        frame_count = len(lap["telemetry_frames"])
        started_on_pit = lap["started_on_pit_road"]
        ended_on_pit = lap["ended_on_pit_road"]
        is_valid_leaderboard = lap["is_valid_for_leaderboard"]
        
        logger.info(f"Lap {i+1}: SDK#{lap_num} - {lap_state}")
        logger.info(f"  Duration: {duration:.2f}s, Frames: {frame_count}")
        logger.info(f"  Started on pit: {started_on_pit}, Ended on pit: {ended_on_pit}")
        logger.info(f"  Valid for leaderboard: {is_valid_leaderboard}")
        
        # Check first and last position
        if frame_count > 0:
            first_pos = lap["telemetry_frames"][0]["LapDistPct"]
            last_pos = lap["telemetry_frames"][-1]["LapDistPct"]
            logger.info(f"  Track position: Start {first_pos:.2f}, End {last_pos:.2f}")

def test_quick_reset_after_finish():
    """Test scenario: Driver crosses line and immediately resets."""
    indexer = LapIndexer()
    session_time = 0.0
    
    # Start with 1 full normal lap
    for i in range(101):
        dist = i * 0.01
        indexer.on_frame({
            "SessionTimeSecs": session_time + i,
            "LapCompleted": 0,
            "Lap": 1,
            "LapDistPct": dist,
            "OnPitRoad": False,
            "LapLastLapTime": -1.0
        })
    
    # Next frame after crossing line - LapLastLapTime appears, but the driver resets immediately
    # before LapCompleted increments
    session_time += 101
    indexer.on_frame({
        "SessionTimeSecs": session_time,
        "LapCompleted": 0,  # Still 0 because driver reset before next frame
        "Lap": 1,  # Still 1
        "LapDistPct": 0.01,
        "OnPitRoad": False,
        "LapLastLapTime": 101.0  # Lap time appears
    })
    
    # The next few frames are after reset, on pit road
    session_time += 1
    for i in range(5):
        indexer.on_frame({
            "SessionTimeSecs": session_time + i,
            "LapCompleted": 0,  # Reset still on lap 0
            "Lap": 1,
            "LapDistPct": 0.01,
            "OnPitRoad": True,  # Now on pit road
            "LapLastLapTime": 101.0  # Lap time persists
        })
    
    # Finalize and check results
    indexer.finalize()
    laps = indexer.get_laps()
    
    logger.info("=== QUICK RESET AFTER FINISH TEST ===")
    logger.info(f"Laps detected: {len(laps)}")
    
    # Analyze each lap
    for i, lap in enumerate(laps):
        lap_num = lap["lap_number_sdk"]
        lap_state = lap["lap_state"]
        duration = lap["duration_seconds"]
        frame_count = len(lap["telemetry_frames"])
        is_early = lap.get("is_early_finalized", False)
        
        logger.info(f"Lap {i+1}: SDK#{lap_num} - {lap_state}")
        logger.info(f"  Duration: {duration:.2f}s, Frames: {frame_count}")
        logger.info(f"  Early finalized: {is_early}")

def main():
    """Main function to run the tests."""
    logger.info("Starting lap type classification tests")
    
    # Run the standard test with different lap types
    run_test()
    
    # Run specialized test for the immediate reset case
    test_quick_reset_after_finish()
    
    logger.info("Tests completed")

if __name__ == "__main__":
    main() 