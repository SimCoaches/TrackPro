#!/usr/bin/env python3
"""
vJoy Output Test Script

Simple test to verify vJoy is working and outputs values that iRacing can see.
Run this while iRacing is open to test if the virtual controller is working.
"""

import sys
import os
import time
import math

# Add trackpro to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from trackpro.pedals.output import VirtualJoystick
    print("✅ Successfully imported VirtualJoystick")
except ImportError as e:
    print(f"❌ Failed to import VirtualJoystick: {e}")
    exit(1)

def main():
    """Test vJoy output with animated values"""
    print("🎮 vJoy Output Test")
    print("=" * 50)
    
    # Initialize vJoy
    try:
        vjoy = VirtualJoystick(test_mode=False)
        print("✅ vJoy initialized successfully")
        print("🎮 iRacing should see a 'vJoy Device' in Controls")
    except Exception as e:
        print(f"❌ vJoy initialization failed: {e}")
        print("🔄 Trying test mode...")
        try:
            vjoy = VirtualJoystick(test_mode=True)
            print("⚠ vJoy running in test mode (simulation only)")
        except:
            print("❌ Complete vJoy failure")
            return
    
    print("\n🔍 Testing vJoy output...")
    print("📋 Instructions:")
    print("1. Open iRacing")
    print("2. Go to Options → Controls")
    print("3. Look for 'vJoy Device' in the controller list")
    print("4. Select 'vJoy Device' and map your axes")
    print("5. Watch for animated brake/throttle values below")
    print("\nPress Ctrl+C to stop...\n")
    
    try:
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            # Create animated test values
            # Sine wave for throttle (0-100%)
            throttle = (math.sin(elapsed * 0.5) + 1) / 2  # 0.0 to 1.0
            
            # Cosine wave for brake (0-100%) 
            brake = (math.cos(elapsed * 0.3) + 1) / 2     # 0.0 to 1.0
            
            # Slow triangle wave for clutch
            clutch = abs((elapsed * 0.2) % 2 - 1)         # 0.0 to 1.0
            
            # Convert to vJoy range (0-32767)
            throttle_vjoy = int(throttle * 32767)
            brake_vjoy = int(brake * 32767)
            clutch_vjoy = int(clutch * 32767)
            
            # Send to vJoy
            success = vjoy.update_axis(throttle_vjoy, brake_vjoy, clutch_vjoy)
            
            # Display current values
            status = "✅" if success else "❌"
            print(f"\r{status} T:{throttle:5.1%} B:{brake:5.1%} C:{clutch:5.1%} | vJoy: T:{throttle_vjoy:5d} B:{brake_vjoy:5d} C:{clutch_vjoy:5d}", end="", flush=True)
            
            time.sleep(0.05)  # 20Hz update rate
            
    except KeyboardInterrupt:
        print("\n\n🛑 Test stopped")
        print("✅ vJoy test complete")
        
        # Reset vJoy to neutral position
        try:
            vjoy.update_axis(0, 0, 0)
            print("🔄 vJoy reset to neutral position")
        except:
            pass

if __name__ == "__main__":
    main() 