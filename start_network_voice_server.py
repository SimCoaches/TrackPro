#!/usr/bin/env python3
"""
Network Voice Server Launcher for TrackPro

This script starts a persistent voice chat server that allows multiple users
on the same WiFi network to connect and chat together.

Usage:
    python start_network_voice_server.py

The server will:
- Start on all network interfaces (accessible to other users on same WiFi)
- Display the IP address that other users need to connect to
- Run continuously until you press Ctrl+C
- Support multiple voice channels
- Handle high-quality audio with speaking detection

For other users to connect:
1. They need to be on the same WiFi network
2. They need to use the IP address shown when the server starts
3. They connect through TrackPro's community page
"""

import sys
import os
import subprocess
import socket

def get_local_ip():
    """Get the local IP address for network access."""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "0.0.0.0"

def main():
    """Launch the network voice server."""
    print("🎤 TrackPro Network Voice Server Launcher")
    print("=" * 50)
    print()
    print("This will start a voice chat server that allows multiple users")
    print("on the same WiFi network to connect and chat together.")
    print()
    
    # Get local IP for display
    local_ip = get_local_ip()
    print(f"Your local IP address: {local_ip}")
    print(f"Other users on the same WiFi will connect to: {local_ip}:8080")
    print()
    print("The server will start in 3 seconds...")
    print("Press Ctrl+C to stop the server when you're done.")
    print()
    
    # Countdown
    import time
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    
    print("🎤 Starting network voice server...")
    print()
    
    # Get the path to the network voice server script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(current_dir, "trackpro", "network_voice_server.py")
    
    if not os.path.exists(server_script):
        print(f"❌ Error: Voice server script not found at {server_script}")
        return 1
    
    try:
        # Start the server process
        print(f"🎤 Launching server: {server_script}")
        print()
        
        # Run the server directly
        result = subprocess.run([
            sys.executable, server_script
        ], cwd=current_dir)
        
        if result.returncode == 0:
            print("🎤 Voice server stopped normally")
        else:
            print(f"🎤 Voice server stopped with code: {result.returncode}")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n🎤 Voice server stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error starting voice server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 