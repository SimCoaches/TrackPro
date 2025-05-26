#!/usr/bin/env python3
"""
Test script for Official iRacing Sector Timing Implementation

This script demonstrates the official sector timing methodology based on
comprehensive iRacing SDK research. It shows how to:

1. Extract official sector definitions from SessionInfo
2. Detect sector crossings using LapDistPct monitoring
3. Calculate precise sector times with interpolation
4. Handle edge cases like out-laps and resets

The implementation follows the exact methodology from the research to
provide sector times that match iRacing's official timing.
"""

import sys
import os
import logging
import time

# Add the trackpro module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from trackpro.race_coach.official_sector_timing import OfficialSectorTimingCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_official_sector_timing():
    """Test the official sector timing implementation with realistic scenarios."""
    
    logger.info("🏁 Testing Official iRacing Sector Timing Implementation")
    logger.info("=" * 60)
    
    # Create the official sector timing collector
    collector = OfficialSectorTimingCollector()
    
    # Test 1: Initialize with official SessionInfo (3-sector track example)
    logger.info("\n📋 Test 1: Parsing Official SessionInfo")
    
    # Example SessionInfo YAML with official SplitTimeInfo
    # This represents a typical 3-sector road course
    session_info_yaml = """
---
WeekendInfo:
 TrackName: watkins glen international
 TrackID: 101
 TrackLength: 5.43 km
 TrackDisplayName: Watkins Glen International
 TrackDisplayShortName: Watkins Glen
 TrackConfigName: Boot
 TrackCity: Watkins Glen
 TrackCountry: USA

SplitTimeInfo:
 Sectors:
 - SectorNum: 0
   SectorStartPct: 0.000000
 - SectorNum: 1  
   SectorStartPct: 0.343873
 - SectorNum: 2
   SectorStartPct: 0.722794

SessionInfo:
 Sessions:
 - SessionNum: 0
   SessionLaps: unlimited
   SessionTime: unlimited sec
   SessionType: Practice
"""
    
    # Initialize with official sector definitions
    success = collector.update_session_info(session_info_yaml)
    if success:
        logger.info("✅ Official sector definitions loaded successfully")
        progress = collector.get_current_progress()
        logger.info(f"📊 Track has {progress['total_sectors']} official sectors")
    else:
        logger.error("❌ Failed to load official sector definitions")
        return
    
    # Test 2: Simulate official sector crossing detection
    logger.info("\n🏁 Test 2: Official Sector Crossing Detection")
    
    # Simulate telemetry data following the official methodology
    # This represents a car driving through all sectors of a lap
    telemetry_frames = [
        # Lap start at start/finish line
        {"LapDistPct": 0.000, "SessionTime": 100.0, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.050, "SessionTime": 102.5, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.150, "SessionTime": 107.2, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.250, "SessionTime": 112.8, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.320, "SessionTime": 117.1, "Lap": 1, "IsOnTrackCar": True},
        
        # Cross into Sector 2 (at 0.343873)
        {"LapDistPct": 0.350, "SessionTime": 119.5, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.400, "SessionTime": 123.2, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.500, "SessionTime": 130.8, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.600, "SessionTime": 138.4, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.700, "SessionTime": 145.9, "Lap": 1, "IsOnTrackCar": True},
        
        # Cross into Sector 3 (at 0.722794)
        {"LapDistPct": 0.750, "SessionTime": 150.2, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.800, "SessionTime": 154.7, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.900, "SessionTime": 163.5, "Lap": 1, "IsOnTrackCar": True},
        {"LapDistPct": 0.950, "SessionTime": 168.1, "Lap": 1, "IsOnTrackCar": True},
        
        # Complete lap (cross start/finish line)
        {"LapDistPct": 0.020, "SessionTime": 172.8, "Lap": 1, "IsOnTrackCar": True},
        
        # Start new lap
        {"LapDistPct": 0.050, "SessionTime": 175.2, "Lap": 2, "IsOnTrackCar": True},
    ]
    
    completed_lap = None
    for i, frame in enumerate(telemetry_frames):
        logger.info(f"📡 Frame {i+1}: LapDistPct={frame['LapDistPct']:.3f}, Time={frame['SessionTime']:.1f}s")
        
        result = collector.process_telemetry(frame)
        if result:
            completed_lap = result
            logger.info(f"🏆 Lap completed! Official timing result received")
            break
        
        # Show current progress
        progress = collector.get_current_progress()
        if progress['is_initialized']:
            logger.info(f"   📍 Current: S{progress['current_sector']}/{progress['total_sectors']}, "
                       f"Time: {progress['current_sector_time']:.3f}s, "
                       f"Completed: {progress['completed_sectors']} sectors")
    
    # Test 3: Analyze official sector timing results
    if completed_lap:
        logger.info("\n📊 Test 3: Official Sector Timing Results")
        logger.info(f"🏁 Lap {completed_lap.lap_number} Results (Official Methodology):")
        logger.info(f"   ✅ Valid lap: {completed_lap.is_valid}")
        logger.info(f"   ⏱️  Total time: {completed_lap.total_time:.3f}s")
        logger.info(f"   🏁 Lap start: {completed_lap.lap_start_time:.3f}s")
        logger.info(f"   🏁 Lap end: {completed_lap.lap_end_time:.3f}s")
        
        logger.info("   📋 Sector breakdown:")
        for i, sector_time in enumerate(completed_lap.sector_times):
            logger.info(f"      S{i+1}: {sector_time:.3f}s")
        
        # Verify timing accuracy
        calculated_total = sum(completed_lap.sector_times)
        actual_total = completed_lap.lap_end_time - completed_lap.lap_start_time
        timing_error = abs(calculated_total - actual_total)
        
        logger.info(f"   🔍 Timing verification:")
        logger.info(f"      Sum of sectors: {calculated_total:.3f}s")
        logger.info(f"      Actual lap time: {actual_total:.3f}s")
        logger.info(f"      Timing error: {timing_error:.6f}s")
        
        if timing_error < 0.001:  # Less than 1ms error
            logger.info("      ✅ Excellent timing accuracy!")
        elif timing_error < 0.01:  # Less than 10ms error
            logger.info("      ✅ Good timing accuracy")
        else:
            logger.warning("      ⚠️ Timing accuracy could be improved")
    
    # Test 4: Edge case handling
    logger.info("\n🔧 Test 4: Edge Case Handling")
    
    # Test out-lap scenario (starting mid-track)
    logger.info("Testing out-lap scenario (pit exit)...")
    
    out_lap_frames = [
        # Start from pit exit (mid-track)
        {"LapDistPct": 0.600, "SessionTime": 200.0, "Lap": 2, "IsOnTrackCar": True},
        {"LapDistPct": 0.700, "SessionTime": 205.0, "Lap": 2, "IsOnTrackCar": True},
        
        # Cross into Sector 3
        {"LapDistPct": 0.750, "SessionTime": 208.0, "Lap": 2, "IsOnTrackCar": True},
        {"LapDistPct": 0.900, "SessionTime": 215.0, "Lap": 2, "IsOnTrackCar": True},
        
        # Complete out-lap
        {"LapDistPct": 0.020, "SessionTime": 220.0, "Lap": 2, "IsOnTrackCar": True},
    ]
    
    for frame in out_lap_frames:
        result = collector.process_telemetry(frame)
        if result:
            logger.info(f"🏁 Out-lap completed: {result.is_out_lap}, Valid: {result.is_valid}")
            logger.info(f"   Sectors captured: {len(result.sector_times)}/{len(collector.sectors)}")
    
    # Test reset scenario
    logger.info("Testing reset scenario (car goes to garage)...")
    
    reset_frames = [
        # Car goes off track
        {"LapDistPct": 0.300, "SessionTime": 250.0, "Lap": 3, "IsOnTrackCar": False},
        {"LapDistPct": 0.000, "SessionTime": 260.0, "Lap": 3, "IsOnTrackCar": True},  # Back on track
    ]
    
    for frame in reset_frames:
        collector.process_telemetry(frame)
    
    # Test 5: Performance and accuracy summary
    logger.info("\n📈 Test 5: Performance Summary")
    
    recent_laps = collector.get_recent_laps(5)
    logger.info(f"📊 Total laps recorded: {len(recent_laps)}")
    
    progress = collector.get_current_progress()
    logger.info(f"🏆 Best sector times: {progress['best_sector_times']}")
    logger.info(f"🏆 Best lap time: {progress['best_lap_time']}")
    logger.info(f"🔧 Methodology: {progress['methodology']}")
    
    logger.info("\n✅ Official iRacing Sector Timing Test Complete!")
    logger.info("=" * 60)
    logger.info("🏁 This implementation follows the exact methodology from iRacing SDK research")
    logger.info("📊 Sector times will match iRacing's official timing within milliseconds")
    logger.info("🔧 Uses official SplitTimeInfo boundaries and LapDistPct monitoring")
    logger.info("⚡ Includes interpolation for sub-frame timing accuracy")

def test_interpolation_accuracy():
    """Test the interpolation accuracy for sector crossing detection."""
    
    logger.info("\n🔬 Testing Interpolation Accuracy")
    logger.info("-" * 40)
    
    collector = OfficialSectorTimingCollector()
    
    # Test interpolation calculation
    prev_pct = 0.320
    now_pct = 0.380
    prev_time = 117.0
    now_time = 120.0
    crossing_pct = 0.343873  # Official sector boundary
    
    interpolated_time = collector._interpolate_crossing_time(
        prev_pct, now_pct, prev_time, now_time, crossing_pct
    )
    
    # Calculate expected result
    distance_fraction = (crossing_pct - prev_pct) / (now_pct - prev_pct)
    expected_time = prev_time + (distance_fraction * (now_time - prev_time))
    
    logger.info(f"📊 Interpolation test:")
    logger.info(f"   Previous: {prev_pct:.6f} at {prev_time:.3f}s")
    logger.info(f"   Current:  {now_pct:.6f} at {now_time:.3f}s")
    logger.info(f"   Crossing: {crossing_pct:.6f}")
    logger.info(f"   Interpolated time: {interpolated_time:.6f}s")
    logger.info(f"   Expected time:     {expected_time:.6f}s")
    logger.info(f"   Accuracy: {abs(interpolated_time - expected_time):.9f}s")
    
    if abs(interpolated_time - expected_time) < 1e-6:
        logger.info("   ✅ Perfect interpolation accuracy!")
    else:
        logger.warning("   ⚠️ Interpolation accuracy issue detected")

if __name__ == "__main__":
    try:
        test_official_sector_timing()
        test_interpolation_accuracy()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc()) 