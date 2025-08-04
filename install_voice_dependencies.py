#!/usr/bin/env python3
"""
Voice Chat Dependencies Installer

This script helps install the required dependencies for TrackPro's voice chat functionality.
PyAudio can be tricky to install on Windows, so this script provides multiple installation methods.
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n🔄 {description}...")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed:")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def check_package_installed(package_name):
    """Check if a package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def main():
    print("🎤 TrackPro Voice Chat Dependencies Installer")
    print("=" * 50)
    
    # Check current Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check if packages are already installed
    print("\n📋 Checking current installations...")
    pyaudio_installed = check_package_installed("pyaudio")
    numpy_installed = check_package_installed("numpy")
    websockets_installed = check_package_installed("websockets")
    
    print(f"PyAudio: {'✅ Installed' if pyaudio_installed else '❌ Not installed'}")
    print(f"NumPy: {'✅ Installed' if numpy_installed else '❌ Not installed'}")
    print(f"WebSockets: {'✅ Installed' if websockets_installed else '❌ Not installed'}")
    
    if pyaudio_installed and numpy_installed and websockets_installed:
        print("\n🎉 All voice chat dependencies are already installed!")
        print("You should now be able to access voice settings in TrackPro.")
        return
    
    print("\n🔧 Installing missing dependencies...")
    
    # Install numpy if needed
    if not numpy_installed:
        if not run_command("pip install --user numpy", "Installing NumPy"):
            print("❌ Failed to install NumPy. Please try manually: pip install numpy")
            return
    
    # Install websockets if needed
    if not websockets_installed:
        if not run_command("pip install --user websockets", "Installing WebSockets"):
            print("❌ Failed to install WebSockets. Please try manually: pip install websockets")
            return
    
    # Install PyAudio (the tricky one)
    if not pyaudio_installed:
        print("\n🎤 Installing PyAudio (this can be tricky on Windows)...")
        
        # Try different installation methods
        methods = [
            ("pip install --user pyaudio", "Standard pip installation"),
            ("pip install --user --upgrade pip", "Upgrading pip first"),
            ("pip install --user pyaudio --force-reinstall", "Force reinstall PyAudio"),
        ]
        
        # Add Windows-specific methods
        if platform.system() == "Windows":
            methods.extend([
                ("pip install --user pipwin", "Installing pipwin for Windows"),
                ("pipwin install pyaudio", "Installing PyAudio via pipwin"),
            ])
        
        success = False
        for command, description in methods:
            if run_command(command, description):
                # Test if PyAudio is now available
                if check_package_installed("pyaudio"):
                    print("✅ PyAudio installed successfully!")
                    success = True
                    break
                else:
                    print("⚠️  Command completed but PyAudio not detected, trying next method...")
        
        if not success:
            print("\n❌ Failed to install PyAudio using automated methods.")
            print("\n🔧 Manual installation options:")
            print("1. Download PyAudio wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/")
            print("   - Choose the correct version for your Python and system architecture")
            print("   - Example: PyAudio-0.2.11-cp39-cp39-win_amd64.whl")
            print("   - Install with: pip install --user <downloaded-file>.whl")
            print("\n2. Try conda installation:")
            print("   conda install pyaudio")
            print("\n3. On Windows, try:")
            print("   pip install --user pipwin")
            print("   pipwin install pyaudio")
            return
    
    print("\n🎉 Voice chat dependencies installation completed!")
    print("\n📋 Next steps:")
    print("1. Restart TrackPro")
    print("2. Go to Community page")
    print("3. Join a voice channel")
    print("4. Click the settings gear icon to configure voice settings")
    print("\n🎤 Voice chat should now work properly!")

if __name__ == "__main__":
    main() 