#!/usr/bin/env python3
"""
Real-time test to debug AI coaching telemetry flow.
Run this while iRacing is running to see telemetry flow issues.
"""

import logging
import time
import sys
import os

# Add the TrackPro directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_realtime_flow():
    """Test real-time telemetry flow with debug."""
    print("\n" + "="*60)
    print("REAL-TIME AI COACHING DEBUG TEST")
    print("="*60)
    print("\nThis test will:")
    print("1. Start TrackPro in debug mode")
    print("2. Monitor telemetry callbacks")
    print("3. Check AI coach conditions")
    print("4. Run for 30 seconds")
    print("\nMake sure iRacing is running and you're on track!")
    print("="*60)
    
    try:
        # Import main components
        from trackpro.race_coach.ui.main_window import RaceCoachWidget
        from PyQt5.QtWidgets import QApplication
        
        # Create minimal app
        app = QApplication(sys.argv)
        
        print("✅ Created QApplication")
        
        # Create race coach widget with debug logging
        race_coach = RaceCoachWidget()
        
        print("✅ Created RaceCoachWidget")
        
        # Wait for initialization
        time.sleep(2)
        
        # Try to trigger showEvent to start monitoring
        race_coach.show()
        
        print("✅ Triggered race coach show event")
        
        # Wait for initialization
        time.sleep(3)
        
        # Check initial state
        print(f"\n📊 INITIAL STATE:")
        print(f"   iRacing API: {hasattr(race_coach, 'iracing_api') and race_coach.iracing_api is not None}")
        print(f"   Telemetry Worker: {hasattr(race_coach, 'telemetry_monitor_worker') and race_coach.telemetry_monitor_worker is not None}")
        
        if hasattr(race_coach, 'telemetry_monitor_worker') and race_coach.telemetry_monitor_worker:
            print(f"   AI Coach: {race_coach.telemetry_monitor_worker.ai_coach is not None}")
            print(f"   Is Monitoring: {race_coach.telemetry_monitor_worker.is_monitoring}")
        
        # Monitor for 30 seconds
        print(f"\n🔍 Monitoring telemetry flow for 30 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 30:
            app.processEvents()
            time.sleep(0.1)
            
            # Print status every 5 seconds
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and elapsed > 0:
                telemetry_status = race_coach.get_telemetry_status() if hasattr(race_coach, 'get_telemetry_status') else {}
                print(f"\n⏱️  [{int(elapsed)}s] Telemetry Status: {telemetry_status}")
        
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_realtime_flow() 