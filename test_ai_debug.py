#!/usr/bin/env python3
"""
Quick debug script to test AI coach with real telemetry data
"""
import logging
logging.basicConfig(level=logging.DEBUG)

# Add the project to the path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from trackpro.race_coach.ai_coach.ai_coach import AICoach

# Test with a known superlap ID (from the logs)
SUPERLAP_ID = "e5c615d9-73fa-4e28-8499-3541a037ce77"

print(f"🤖 Testing AI Coach with SuperLap: {SUPERLAP_ID}")

try:
    # Initialize AI Coach
    coach = AICoach(superlap_id=SUPERLAP_ID)
    
    if coach.superlap_points:
        print(f"✅ AI Coach loaded with {len(coach.superlap_points)} points")
        
        # Test with mock telemetry similar to what iRacing sends
        mock_telemetry = {
            'track_position': 0.5,  # Middle of track
            'speed': 150.0,         # 150 km/h
            'throttle': 0.8,        # 80% throttle
            'brake': 0.0,           # No braking
            'steering': 0.1         # Slight steering
        }
        
        print(f"🔍 Testing with mock telemetry: {mock_telemetry}")
        print("🎙️ Calling process_realtime_telemetry...")
        
        # This should trigger coaching if there's a significant difference
        coach.process_realtime_telemetry(mock_telemetry)
        
        print("✅ Test completed - check above for any coaching output")
        
    else:
        print("❌ Failed to load superlap data")
        
except Exception as e:
    print(f"❌ Error testing AI coach: {e}")
    import traceback
    traceback.print_exc() 