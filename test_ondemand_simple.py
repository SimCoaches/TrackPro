#!/usr/bin/env python3
"""
Simple test for on-demand voice server startup.
"""

import time
import sys
import os

# Add trackpro to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'trackpro'))

try:
    from trackpro.voice_server_manager import start_voice_server, stop_voice_server, is_voice_server_running
    print("Voice server manager imported successfully")
    
    # Test 1: Check if server is not running initially
    print(f"Server running initially: {is_voice_server_running()}")
    
    # Test 2: Start server on-demand
    print("Starting voice server on-demand...")
    start_voice_server()
    time.sleep(3)
    
    # Test 3: Check if server is now running
    print(f"Server running after start: {is_voice_server_running()}")
    
    # Test 4: Stop server
    print("Stopping voice server...")
    stop_voice_server()
    time.sleep(1)
    
    # Test 5: Check if server stopped
    print(f"Server running after stop: {is_voice_server_running()}")
    
    print("All tests completed successfully!")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Test error: {e}") 