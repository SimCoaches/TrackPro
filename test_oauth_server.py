#!/usr/bin/env python3
"""
Test OAuth Server Setup
"""

import sys
import time
import socket
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_oauth_server():
    """Test OAuth server setup."""
    try:
        from trackpro.auth.oauth_handler import OAuthHandler
        
        print("Creating OAuth handler...")
        oauth_handler = OAuthHandler()
        
        print("Setting up callback server...")
        server = oauth_handler.setup_callback_server(port=3000)
        
        if server:
            print("✅ OAuth callback server started successfully")
            
            # Test if server is responding
            time.sleep(1)
            try:
                import urllib.request
                response = urllib.request.urlopen('http://localhost:3000/', timeout=5)
                print(f"✅ Server is responding (status: {response.getcode()})")
            except Exception as e:
                print(f"⚠️ Server not responding to test request: {e}")
            
            # Clean up
            server.server_close()
            print("✅ Server cleaned up")
            return True
        else:
            print("❌ Failed to start OAuth callback server")
            return False
            
    except Exception as e:
        print(f"❌ Error testing OAuth server setup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing OAuth server setup...")
    success = test_oauth_server()
    if success:
        print("✅ OAuth server test passed!")
    else:
        print("❌ OAuth server test failed!") 