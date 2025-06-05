#!/usr/bin/env python3
"""
Xbox Controller Input Test

Simple test to verify Xbox controller input detection.
This will show which axes move when you press controls.
"""

import pygame
import time
import sys
import os

# Windows-specific imports for controller detection
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

def check_windows_controllers():
    """Check Windows registry for connected controllers"""
    if not HAS_WINREG:
        print("❌ Cannot check Windows registry (winreg not available)")
        return
    
    print("\n🔍 Checking Windows Registry for controllers...")
    
    try:
        # Check HKEY_CURRENT_USER for XInput devices
        base_key = winreg.HKEY_CURRENT_USER
        dinput_path = r"System\CurrentControlSet\Control\MediaProperties\PrivateProperties\DirectInput\VID_045E&PID_02EA"
        xinput_path = r"System\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM"
        
        # Try to find Xbox controllers in registry
        try:
            with winreg.OpenKey(base_key, dinput_path):
                print("✅ Found Xbox controller in DirectInput registry")
        except WindowsError:
            print("❌ No Xbox controller found in DirectInput registry")
        
        # Also check device manager info
        print("\n🔧 Checking if HidHide is blocking controllers...")
        
    except Exception as e:
        print(f"❌ Registry check failed: {e}")

def check_device_manager():
    """Check what Device Manager sees"""
    print("\n🔍 Checking Device Manager devices...")
    
    try:
        import subprocess
        
        # Use PowerShell to check for connected controllers
        cmd = 'Get-PnpDevice | Where-Object {$_.FriendlyName -like "*controller*" -or $_.FriendlyName -like "*xbox*" -or $_.FriendlyName -like "*gamepad*"} | Select-Object FriendlyName, Status, InstanceId'
        
        result = subprocess.run(['powershell', '-Command', cmd], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            print("✅ Controllers found in Device Manager:")
            print(result.stdout)
        else:
            print("❌ No controllers found in Device Manager")
            if result.stderr:
                print(f"Error: {result.stderr}")
                
    except Exception as e:
        print(f"❌ Device Manager check failed: {e}")

def test_controller_detection():
    """Enhanced controller detection"""
    print("🎮 Enhanced Xbox Controller Detection Test")
    print("=" * 50)
    
    # Check Windows-level controller detection first
    check_windows_controllers()
    check_device_manager()
    
    print("\n" + "=" * 50)
    print("🎮 Pygame Controller Detection (Multiple Driver Attempts)")
    print("=" * 50)
    
    # Try different SDL joystick drivers
    drivers_to_try = [
        "windows",      # Windows native
        "directinput",  # DirectInput
        "xinput",       # XInput 
        "winmm",        # Windows Multimedia
        None            # Default
    ]
    
    for driver in drivers_to_try:
        print(f"\n🔄 Trying SDL joystick driver: {driver or 'default'}")
        
        # Quit pygame if already initialized
        if pygame.get_init():
            pygame.quit()
        
        # Set SDL hint for joystick driver
        if driver:
            os.environ['SDL_JOYSTICK_DRIVER'] = driver
        elif 'SDL_JOYSTICK_DRIVER' in os.environ:
            del os.environ['SDL_JOYSTICK_DRIVER']
        
        # Initialize pygame with all subsystems
        try:
            pygame.init()
            pygame.joystick.init()
            
            # Check joystick count
            joystick_count = pygame.joystick.get_count()
            print(f"   🔍 Found {joystick_count} controller(s)")
            
            xbox_found = False
            
            for i in range(joystick_count):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                
                name = joystick.get_name()
                axes = joystick.get_numaxes()
                buttons = joystick.get_numbuttons()
                
                print(f"      {i}: {name} - {axes} axes, {buttons} buttons")
                
                # Check if it's an Xbox controller (multiple possible names)
                xbox_keywords = ['xbox', 'controller', 'wireless controller', 'x-box', 'xinput']
                is_xbox = any(keyword.lower() in name.lower() for keyword in xbox_keywords)
                
                if is_xbox and 'vjoy' not in name.lower():
                    xbox_found = True
                    print(f"      ✅ Xbox controller found with {driver or 'default'} driver!")
                    
                    # Test this controller
                    print(f"\n🎮 Testing Xbox Controller: {name}")
                    print("   Move triggers and sticks to test (10 seconds)...")
                    
                    try:
                        start_time = time.time()
                        while time.time() - start_time < 10:
                            pygame.event.pump()
                            
                            # Get trigger values
                            axes_count = joystick.get_numaxes()
                            if axes_count >= 6:
                                left_trigger = (joystick.get_axis(4) + 1) / 2
                                right_trigger = (joystick.get_axis(5) + 1) / 2
                                left_stick_x = joystick.get_axis(0)
                                left_stick_y = joystick.get_axis(1)
                            else:
                                left_trigger = 0.0
                                right_trigger = 0.0
                                left_stick_x = joystick.get_axis(0) if axes_count > 0 else 0.0
                                left_stick_y = joystick.get_axis(1) if axes_count > 1 else 0.0
                            
                            print(f"\r   🎮 LT: {left_trigger:.3f} | RT: {right_trigger:.3f} | LX: {left_stick_x:.3f} | LY: {left_stick_y:.3f}", end="")
                            
                            time.sleep(0.1)
                        
                        print(f"\n   ✅ Controller test completed!")
                        return  # Success! Exit the function
                        
                    except KeyboardInterrupt:
                        print("\n   🛑 Test stopped")
                        return
                        
            if not xbox_found:
                print(f"   ❌ No Xbox controller found with {driver or 'default'} driver")
                
        except Exception as e:
            print(f"   ❌ Failed to initialize pygame with {driver or 'default'} driver: {e}")
    
    # If we get here, no Xbox controller was found with any driver
    print(f"\n❌ Xbox controller not detected with any SDL driver!")
    print(f"\n💡 SOLUTIONS:")
    print(f"   1. 🔌 Connect Xbox controller with USB cable (wired connection)")
    print(f"   2. 📱 Turn off Bluetooth on controller: Hold Xbox button + pair button for 3 seconds")
    print(f"   3. 🔄 Restart computer")
    print(f"   4. 🛠️ Check HidHide configuration")
    print(f"   5. 🎮 Try a different Xbox controller")
    
    pygame.quit()

if __name__ == "__main__":
    test_controller_detection() 