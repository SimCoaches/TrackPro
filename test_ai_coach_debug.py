#!/usr/bin/env python3
"""
Debug test for AI Coach to verify it's working with real superlap data.
This script will manually send telemetry data to the AI coach to test the pipeline.
"""

import sys
import time
import logging
from pathlib import Path

# Setup logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add trackpro to path
sys.path.append(str(Path(__file__).parent / "trackpro"))

def test_ai_coach_manually():
    """Test AI coach with your specific superlap."""
    print("🎙️ Testing AI Coach with Manual Telemetry Data")
    print("=" * 60)
    
    try:
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        
        # Your superlap ID
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        
        print(f"Initializing AI Coach with superlap: {superlap_id}")
        coach = AICoach(superlap_id=superlap_id)
        
        if not coach.superlap_points:
            print("❌ Failed to load superlap data")
            return
            
        print(f"✅ AI Coach loaded with {len(coach.superlap_points)} superlap points")
        
        # Test with mock telemetry that should trigger coaching
        print("\n🧪 Testing with mock telemetry data:")
        
        mock_telemetry_tests = [
            {
                'name': 'Significantly too slow',
                'data': {
                    'track_position': 0.25,  # Quarter way around track  
                    'speed': 50,             # Very slow (should trigger)
                    'throttle': 0.3,         # Not enough throttle
                    'brake': 0.0,
                    'steering': 0.1
                }
            },
            {
                'name': 'Braking when should not',
                'data': {
                    'track_position': 0.5,   # Halfway around track
                    'speed': 120,            # Reasonable speed
                    'throttle': 0.0,         # No throttle
                    'brake': 0.8,            # Heavy braking (might be wrong)
                    'steering': 0.0
                }
            },
            {
                'name': 'Good telemetry (should not trigger)',
                'data': {
                    'track_position': 0.75,  # 3/4 around track
                    'speed': 150,            # Good speed
                    'throttle': 1.0,         # Full throttle
                    'brake': 0.0,
                    'steering': -0.1
                }
            }
        ]
        
        for i, test in enumerate(mock_telemetry_tests, 1):
            print(f"\n--- Test {i}: {test['name']} ---")
            print(f"Sending telemetry: {test['data']}")
            
            coach.process_realtime_telemetry(test['data'])
            
            # Wait between tests
            time.sleep(3)
            
        print("\n✅ Manual AI Coach test completed!")
        print("Check the logs above for debug information.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the TrackPro directory")
    except Exception as e:
        print(f"❌ Error testing AI coach: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_coach_manually() 