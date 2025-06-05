#!/usr/bin/env python3
"""
Debug script to identify vJoy vs Xbox controller issue

This script will help determine if iRacing is reading from:
1. Your physical Xbox controller (bad - no ABS assist)
2. The vJoy virtual device (good - ABS assist works)
"""

import pygame
import time
from trackpro.pedals.output import VirtualJoystick

def main():
    print("🔧 vJoy vs Xbox Controller Diagnostic")
    print("=" * 50)
    
    # Initialize pygame for Xbox controller
    pygame.init()
    pygame.joystick.init()
    
    # Find Xbox controller
    xbox_controller = None
    for i in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(i)
        joy.init()
        if "xbox" in joy.get_name().lower() or "controller" in joy.get_name().lower():
            xbox_controller = joy
            print(f"✅ Found Xbox controller: {joy.get_name()}")
            break
    
    if not xbox_controller:
        print("❌ No Xbox controller found!")
        return
    
    # Initialize vJoy
    try:
        vjoy = VirtualJoystick(test_mode=False)
        print("✅ vJoy initialized successfully")
    except Exception as e:
        print(f"❌ vJoy initialization failed: {e}")
        return
    
    print()
    print("🎮 DIAGNOSTIC TEST:")
    print("1. Start iRacing")
    print("2. Go to Options > Controls")
    print("3. Look at the 'Brake' control")
    print("4. This script will send DIFFERENT values to Xbox vs vJoy")
    print("5. Watch which device iRacing shows is active")
    print()
    print("Press CTRL+C to stop...")
    print()
    
    try:
        test_count = 0
        while True:
            pygame.event.pump()
            
            # Get actual Xbox brake input
            xbox_brake_raw = xbox_controller.get_axis(4)  # RT trigger
            xbox_brake = max(0.0, xbox_brake_raw)
            
            # Create DIFFERENT vJoy output (easy to identify)
            test_count += 1
            if test_count % 120 == 0:  # Every 2 seconds
                # Send a distinctive pattern to vJoy
                vjoy_brake_value = 0.5  # Always 50% to make it obvious
            else:
                vjoy_brake_value = xbox_brake * 0.25  # 25% of Xbox input
            
            # Send to vJoy
            vjoy_brake_int = int(vjoy_brake_value * 65535)
            vjoy.update_axis(0, vjoy_brake_int, 0)  # throttle=0, brake=vjoy_brake_int, clutch=0
            
            # Print every 30 frames (~0.5 seconds)
            if test_count % 30 == 0:
                print(f"Xbox Brake: {xbox_brake:.3f} | vJoy Brake: {vjoy_brake_value:.3f}")
                print("👆 If iRacing shows Xbox value, it's using Xbox controller (BAD)")
                print("👆 If iRacing shows vJoy value, it's using vJoy (GOOD)")
                print()
            
            time.sleep(1/60)  # 60 FPS
            
    except KeyboardInterrupt:
        print("\n🛑 Diagnostic stopped")
        print()
        print("📋 WHAT TO CHECK:")
        print("1. In iRacing Controls, which device is bound to 'Brake'?")
        print("2. If it shows 'Xbox Controller' → BAD (ABS won't work)")
        print("3. If it shows 'vJoy Device' → GOOD (ABS will work)")
        print()
        print("🔧 TO FIX:")
        print("1. In iRacing: Options > Controls")
        print("2. Click on 'Brake' control")
        print("3. Press brake pedal while script is running")
        print("4. Select the vJoy device option (not Xbox)")
        print("5. Save and test again")

if __name__ == "__main__":
    main() 