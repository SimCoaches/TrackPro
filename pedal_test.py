#!/usr/bin/env python3
"""
MINIMAL PEDAL TEST - Pure hardware to output, no dependencies
"""
import pygame
import time
import ctypes
from threading import Thread, Event

def main():
    print("🎯 Starting MINIMAL PEDAL TEST - Pure hardware access")

    try:
        # Initialize pygame
        pygame.init()
        pygame.joystick.init()

        # Set high priority
        try:
            thread_handle = ctypes.windll.kernel32.GetCurrentThread()
            ctypes.windll.kernel32.SetThreadPriority(thread_handle, 15)
            process_handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(process_handle, 0x00000080)
            print("🏎️ High priority set successfully")
        except Exception as e:
            print(f"⚠️ Could not set priority: {e}")

        # Find joystick
        joystick = None
        joystick_count = pygame.joystick.get_count()
        print(f"🎮 Found {joystick_count} joysticks")

        if joystick_count > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            print(f"🎮 Initialized: {joystick.get_name()}")
            print(f"🎮 Axes: {joystick.get_numaxes()}, Buttons: {joystick.get_numbuttons()}")
        else:
            print("⚠️ No joysticks found - pedal test will show zeros")

        # Pedal loop
        loop_count = 0
        stop_event = Event()

        def pedal_loop():
            nonlocal loop_count
            while not stop_event.is_set():
                loop_count += 1

                try:
                    # Pump events periodically
                    if loop_count % 10 == 0:
                        pygame.event.pump()

                    # Read axes
                    if joystick:
                        num_axes = joystick.get_numaxes()
                        throttle = int((joystick.get_axis(0) + 1) * 32767) if num_axes > 0 else 0
                        brake = int((joystick.get_axis(1) + 1) * 32767) if num_axes > 1 else 0
                        clutch = int((joystick.get_axis(2) + 1) * 32767) if num_axes > 2 else 0

                        # Show values periodically
                        if loop_count % 500 == 0:
                            print("8d")
                    else:
                        throttle = brake = clutch = 0
                        if loop_count % 500 == 0:
                            print("🎮 No joystick - T:00000 B:00000 C:00000")

                    # Performance indicator
                    if loop_count % 10000 == 0:
                        print(f"🎯 LOOP: {loop_count} iterations completed")

                except Exception as e:
                    if loop_count % 1000 == 0:
                        print(f"⚠️ Loop error: {e}")

        # Start thread
        print("🚀 Starting pedal processing thread...")
        pedal_thread = Thread(target=pedal_loop, daemon=True)
        pedal_thread.start()

        print("✅ Pedal test running at maximum speed!")
        print("Press Ctrl+C to exit...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping pedal test...")
            stop_event.set()
            pedal_thread.join(timeout=2)
            print("✅ Pedal test stopped")

        pygame.quit()

    except Exception as e:
        import traceback
        print(f"\n❌ Pedal test failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
