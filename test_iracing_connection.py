#!/usr/bin/env python3
"""
Quick test to check if iRacing is running and sending telemetry data.
This will help diagnose if the AI coach can receive real-time data.
"""

import sys
import time
from pathlib import Path

# Add the trackpro module to the path
sys.path.append(str(Path(__file__).parent / "trackpro"))

def test_iracing_connection():
    """Test iRacing connection and telemetry."""
    print("🏁 Testing iRacing Connection...")
    print("=" * 50)
    
    try:
        # Import iRacing SDK
        from trackpro.race_coach.pyirsdk.irsdk import IRSDK
        
        # Create iRacing SDK instance
        ir = IRSDK()
        
        # Check if iRacing is running
        if ir.startup():
            print("✅ iRacing is running!")
            
            # Check if connected to a session
            if ir.is_connected:
                print("✅ Connected to iRacing session!")
                
                # Get some basic telemetry
                speed = ir['Speed']
                throttle = ir['Throttle'] 
                brake = ir['Brake']
                steering = ir['SteeringWheelAngle']
                lap_dist = ir['LapDist']
                
                if speed is not None:
                    print(f"🏎️  Current Speed: {speed:.1f} km/h")
                    print(f"🚗 Throttle: {throttle:.2f}")
                    print(f"🛑 Brake: {brake:.2f}")
                    print(f"🎯 Steering: {steering:.3f}")
                    print(f"📍 Lap Distance: {lap_dist:.1f}")
                    
                    print("\n✅ Telemetry data is available!")
                    print("🎙️ AI Coach should work if configured properly.")
                    
                    # Test for a few seconds to see if data changes
                    print("\n🔄 Monitoring telemetry for 5 seconds...")
                    initial_speed = speed
                    for i in range(5):
                        time.sleep(1)
                        try:
                            new_speed = ir['Speed']
                            if new_speed is not None and abs(new_speed - initial_speed) > 1.0:
                                print(f"   Speed changed: {new_speed:.1f} km/h")
                                break
                        except:
                            pass
                    else:
                        print("   ⚠️  No significant telemetry changes detected")
                        print("   (Car might be stationary or paused)")
                    
                else:
                    print("❌ iRacing is running but no telemetry data available")
                    print("   Check that you're in a session (practice, race, etc.)")
            else:
                print("⚠️  iRacing is running but not connected to a session")
                print("   Please load into a practice session, race, or replay")
                
        else:
            print("❌ iRacing is not running or not connected")
            print("   Please start iRacing and load into a session")
            
        # Cleanup
        ir.shutdown()
        
    except ImportError as e:
        print(f"❌ Error importing iRacing SDK: {e}")
        print("   The iRacing SDK module might not be available")
    except Exception as e:
        print(f"❌ Error testing iRacing connection: {e}")
    
    print("\n" + "=" * 50)

def main():
    print("🔧 iRacing Connection Test")
    print("This will check if TrackPro can receive telemetry from iRacing\n")
    
    test_iracing_connection()
    
    print("\n📋 Next Steps:")
    print("1. If iRacing is not running → Start iRacing and load into a practice session")
    print("2. If no telemetry → Check iRacing settings for telemetry output")
    print("3. If working → The issue is likely with superlap data or coach configuration")
    print("4. Run: python diagnose_ai_coach.py YOUR_SUPERLAP_ID")

if __name__ == "__main__":
    main() 