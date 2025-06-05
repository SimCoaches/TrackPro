#!/usr/bin/env python3
"""
Quick vJoy Brake Test - Move brake axis to test iRacing detection
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackpro.pedals.output import VirtualJoystick

def main():
    print("🎮 Quick vJoy Brake Test")
    print("=" * 30)
    
    try:
        vjoy = VirtualJoystick(test_mode=False)
        print("✅ vJoy connected")
    except:
        print("❌ vJoy failed - check if simple_brake_tester.py is running")
        return
    
    print("📋 Instructions:")
    print("1. In iRacing → Options → Controls")
    print("2. Select 'vJoy Device' as controller")
    print("3. Watch for brake axis movement below")
    print("4. Map the moving axis as your brake")
    print()
    
    try:
        for i in range(10):
            # Pulse brake from 0% to 100% and back
            progress = i / 9.0
            brake_value = abs(2 * progress - 1)  # 0→1→0 triangle wave
            
            # Send to vJoy (0-32767 range)
            brake_vjoy = int(brake_value * 32767)
            vjoy.update_axis(0, brake_vjoy, 0)  # throttle=0, brake=moving, clutch=0
            
            print(f"⚡ Brake: {brake_value:5.1%} (vJoy: {brake_vjoy:5d})")
            time.sleep(0.5)
        
        # Reset to zero
        vjoy.update_axis(0, 0, 0)
        print("✅ Test complete - brake should have pulsed")
        print("🎯 If you saw movement in iRacing, map that axis as brake!")
        
    except KeyboardInterrupt:
        vjoy.update_axis(0, 0, 0)
        print("\n🛑 Test stopped")

if __name__ == "__main__":
    main() 