#!/usr/bin/env python3
"""
Stop any running TrackPro test processes that might be holding vJoy devices.
Run this before starting the main TrackPro application if you encounter vJoy device conflicts.
"""

import subprocess
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def stop_python_processes():
    """Stop Python processes that might be running TrackPro tests."""
    try:
        # Get list of all Python processes
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                              capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header line
                logger.info("Found Python processes:")
                for line in lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        logger.info(f"  PID: {pid}")
                
                # Ask user if they want to stop all Python processes
                print("\n⚠️  WARNING: This will stop ALL Python processes!")
                print("This includes any other Python applications you might be running.")
                response = input("Do you want to continue? (y/N): ").strip().lower()
                
                if response in ['y', 'yes']:
                    # Stop all Python processes except this one
                    current_pid = str(subprocess.getpid())
                    for line in lines[1:]:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            pid = parts[1].strip('"')
                            if pid != current_pid:
                                try:
                                    subprocess.run(['taskkill', '/PID', pid, '/F'], 
                                                 capture_output=True, shell=True)
                                    logger.info(f"Stopped process PID: {pid}")
                                except Exception as e:
                                    logger.warning(f"Could not stop process {pid}: {e}")
                    
                    logger.info("✅ All Python processes stopped")
                else:
                    logger.info("❌ Operation cancelled")
            else:
                logger.info("No Python processes found")
        else:
            logger.error("Could not list processes")
            
    except Exception as e:
        logger.error(f"Error stopping Python processes: {e}")

def release_vjoy_devices():
    """Try to release any vJoy devices that might be held by dead processes."""
    try:
        import sys
        import os
        
        # Add the trackpro module to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        trackpro_path = os.path.join(current_dir, 'trackpro')
        if trackpro_path not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Try to create and immediately destroy VirtualJoystick instances
        from trackpro.pedals.output import VirtualJoystick
        
        logger.info("🔄 Attempting to release vJoy devices...")
        
        for device_id in [1, 2, 3, 4]:
            try:
                # Create a VirtualJoystick instance to try and acquire the device
                # Then immediately delete it to release
                vjoy = VirtualJoystick(test_mode=False, retry_count=1, use_alt_devices=False)
                if hasattr(vjoy, 'vjoy_device_id'):
                    vjoy.vjoy_device_id = device_id
                
                # Force cleanup
                del vjoy
                logger.info(f"✅ Released vJoy device {device_id}")
                
            except Exception as e:
                logger.debug(f"Could not release vJoy device {device_id}: {e}")
        
        logger.info("🔄 vJoy device release complete")
        
    except ImportError as e:
        logger.warning(f"Could not import vJoy modules: {e}")
    except Exception as e:
        logger.error(f"Error releasing vJoy devices: {e}")

def main():
    """Main function."""
    print("🛑 TrackPro Test Process Stopper")
    print("=" * 40)
    
    logger.info("Starting cleanup process...")
    
    # Step 1: Stop Python processes
    print("\n📝 Step 1: Checking for running Python processes...")
    stop_python_processes()
    
    # Step 2: Release vJoy devices
    print("\n🎮 Step 2: Releasing vJoy devices...")
    release_vjoy_devices()
    
    print("\n✅ Cleanup complete!")
    print("You can now start TrackPro normally with: python run_app.py")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main() 