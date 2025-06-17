#!/usr/bin/env python3
"""
Quick test to verify AI Coach console output is working
"""

import sys
import time
from pathlib import Path

# Add trackpro to path
sys.path.append(str(Path(__file__).parent / "trackpro"))

def test_ai_coach_console_output():
    """Test AI coach with console output for debugging."""
    print("🔧 Testing AI Coach Console Output")
    print("=" * 50)
    
    try:
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        
        # Your superlap ID
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        
        print(f"Creating AI Coach with superlap: {superlap_id}")
        coach = AICoach(superlap_id=superlap_id, advice_interval=1.0)  # Very short interval for testing
        
        print("\n🧪 Testing with mock telemetry that should trigger coaching:")
        
        # Test telemetry that should definitely trigger coaching
        mock_telemetry = {
            'track_position': 0.25,  # Quarter way around track  
            'speed': 80,             # Much slower than SuperLap
            'throttle': 0.5,         # Not enough throttle
            'brake': 0.0,
            'steering': 0.1
        }
        
        print(f"\nSending telemetry: {mock_telemetry}")
        coach.process_realtime_telemetry(mock_telemetry)
        
        print("\n✅ Console output test completed!")
        print("Look for AI coach messages above. If you see them, console output is working!")
        
    except Exception as e:
        print(f"❌ Error testing AI coach: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_coach_console_output() 