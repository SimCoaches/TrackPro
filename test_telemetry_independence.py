#!/usr/bin/env python3
"""
Test script to verify telemetry independence after AI coach architecture changes.

This script will help verify that:
1. Laps are saved regardless of AI coach state
2. AI coach telemetry doesn't interfere with lap saving
3. All telemetry streams work independently

Run this script while iRacing is running to test the independence.
"""

import logging
import time
import sys
import os

# Add the TrackPro directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackpro.race_coach.ui.main_window import RaceCoachWidget
from trackpro.logging_config import setup_logging

def test_telemetry_independence():
    """Test that telemetry streams are independent."""
    print("🧪 Testing Telemetry Independence")
    print("=" * 50)
    
    # Setup logging to see debug output
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    try:
        # Create a race coach widget
        print("📱 Creating RaceCoachWidget...")
        race_coach = RaceCoachWidget()
        
        # Wait for initialization
        print("⏳ Waiting for initialization...")
        time.sleep(5)
        
        # Get initial telemetry status
        print("\n📊 Initial Telemetry Status:")
        status = race_coach.get_telemetry_status()
        for stream, info in status.items():
            print(f"  {stream}: {info}")
        
        # Test 1: Check if lap saving works without AI coach
        print("\n🧪 Test 1: Lap saving without AI coach")
        print("AI Coach should be OFF, but lap saving should still work")
        
        ai_active = race_coach.is_ai_coaching_active()
        print(f"  AI Coach Active: {ai_active}")
        print("  → Drive a lap in iRacing and check if it gets saved to database")
        
        # Wait and check telemetry
        print("\n⏳ Monitoring for 30 seconds...")
        for i in range(6):
            time.sleep(5)
            status = race_coach.get_telemetry_status()
            ui_points = status['ui_telemetry']['points_received']
            ai_points = status['ai_coach_telemetry']['points_received']
            print(f"  {(i+1)*5}s: UI telemetry points: {ui_points}, AI telemetry points: {ai_points}")
        
        # Test 2: Enable AI coach and verify independence
        print("\n🧪 Test 2: AI coach independence test")
        print("This would require a valid SuperLap ID - skipping for automated test")
        print("  → Manually test: Enable AI coach and verify laps still save")
        print("  → Expected: Both AI coaching AND lap saving should work simultaneously")
        
        print("\n✅ Test completed!")
        print("🔍 Check the log output above for:")
        print("  - UI telemetry points increasing (should always work)")
        print("  - Lap saving telemetry working independently")
        print("  - AI telemetry only active when AI coach is enabled")
        
        # Final status
        print("\n📊 Final Telemetry Status:")
        status = race_coach.get_telemetry_status()
        for stream, info in status.items():
            print(f"  {stream}: {info}")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("🚀 TrackPro Telemetry Independence Test")
    print("Make sure iRacing is running before starting this test!")
    input("Press Enter to continue...")
    
    success = test_telemetry_independence()
    
    if success:
        print("\n🎉 Test completed! Check the output above for results.")
    else:
        print("\n💥 Test failed! Check the error messages above.")
    
    input("Press Enter to exit...") 