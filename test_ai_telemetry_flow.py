#!/usr/bin/env python3
"""
Simple test to verify telemetry flow to AI coach.
Run this while iRacing is running to see if telemetry reaches the AI coach.
"""

import logging
import time
import sys
import os

# Add the TrackPro directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_telemetry_flow():
    """Test the complete telemetry flow to AI coach."""
    print("\n" + "="*60)
    print("TESTING AI COACH TELEMETRY FLOW")
    print("="*60)
    print("\nThis test will:")
    print("1. Initialize AI coach with superlap")
    print("2. Create telemetry monitor worker")
    print("3. Send test telemetry points")
    print("4. Verify AI coach receives and processes them")
    
    try:
        # Initialize AI Coach
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        from trackpro.race_coach.utils.telemetry_worker import TelemetryMonitorWorker
        
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        
        print(f"\n1. Initializing AI Coach with superlap: {superlap_id}")
        ai_coach = AICoach(superlap_id=superlap_id)
        print(f"   ✅ AI Coach initialized with {len(ai_coach.superlap_points)} reference points")
        
        print("\n2. Creating TelemetryMonitorWorker")
        telemetry_worker = TelemetryMonitorWorker()
        telemetry_worker.ai_coach = ai_coach
        telemetry_worker.start_monitoring()
        print("   ✅ Telemetry monitor created and monitoring started")
        
        print("\n3. Sending test telemetry points...")
        print("   (These simulate what iRacing would send)")
        
        # Simulate iRacing telemetry format
        test_points = [
            # Slow in a braking zone
            {'LapDistPct': 0.3, 'Speed': 35.0, 'Throttle': 0.0, 'Brake': 0.8, 'SteeringWheelAngle': 0.1},
            # Too slow mid-corner
            {'LapDistPct': 0.35, 'Speed': 25.0, 'Throttle': 0.2, 'Brake': 0.0, 'SteeringWheelAngle': 0.3},
            # Missing apex speed
            {'LapDistPct': 0.4, 'Speed': 30.0, 'Throttle': 0.6, 'Brake': 0.0, 'SteeringWheelAngle': 0.2},
            # Late on throttle
            {'LapDistPct': 0.45, 'Speed': 35.0, 'Throttle': 0.4, 'Brake': 0.0, 'SteeringWheelAngle': 0.1},
            # Good exit
            {'LapDistPct': 0.5, 'Speed': 45.0, 'Throttle': 1.0, 'Brake': 0.0, 'SteeringWheelAngle': 0.0},
        ]
        
        for i, point in enumerate(test_points):
            print(f"\n   Point {i+1}: pos={point['LapDistPct']:.2f}, speed={point['Speed']:.1f} km/h")
            
            # Send through telemetry worker (simulating iRacing callback)
            telemetry_worker.add_telemetry_point(point)
            
            # Give AI coach time to process and speak
            time.sleep(3)
        
        print("\n4. Test complete!")
        print(f"   Telemetry points sent: {telemetry_worker._telemetry_point_count}")
        print(f"   AI coach active: {telemetry_worker.ai_coach is not None}")
        print(f"   Monitoring active: {telemetry_worker.is_monitoring}")
        
        # Stop monitoring
        telemetry_worker.stop_monitoring()
        print("\n✅ Telemetry monitoring stopped")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🎯 AI COACH TELEMETRY FLOW TEST")
    print("This simulates telemetry being sent to the AI coach")
    print("You should see/hear coaching advice if everything is working")
    
    test_telemetry_flow()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60) 