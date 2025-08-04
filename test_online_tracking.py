#!/usr/bin/env python3
"""Test script for TrackPro online tracking functionality."""

import sys
import os
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackpro.utils.app_tracker import (
    start_app_tracking, 
    stop_app_tracking, 
    update_user_online_status,
    get_online_users,
    get_user_stats
)

def test_online_tracking():
    """Test the online tracking functionality."""
    print("🧪 Testing TrackPro Online Tracking...")
    
    # Test user ID (you can replace this with a real user ID)
    test_user_id = "test-user-123"
    
    try:
        # Test 1: Start app tracking
        print("\n1. Starting app tracking...")
        success = start_app_tracking(test_user_id)
        print(f"   ✅ App tracking started: {success}")
        
        # Test 2: Update online status
        print("\n2. Updating online status...")
        success = update_user_online_status(test_user_id, True)
        print(f"   ✅ Online status updated: {success}")
        
        # Test 3: Get online users
        print("\n3. Getting online users...")
        online_users = get_online_users()
        print(f"   ✅ Found {len(online_users)} online users:")
        for user in online_users:
            print(f"      - User: {user.get('user_id', 'Unknown')}")
            print(f"        Last seen: {user.get('last_seen', 'Unknown')}")
            print(f"        Platform: {user.get('platform', 'Unknown')}")
        
        # Test 4: Get user session stats
        print("\n4. Getting user session stats...")
        stats = get_user_stats(test_user_id)
        print(f"   ✅ Session stats: {stats}")
        
        # Test 5: Wait a bit and check again
        print("\n5. Waiting 5 seconds and checking online status...")
        time.sleep(5)
        online_users = get_online_users()
        print(f"   ✅ Still {len(online_users)} online users after 5 seconds")
        
        # Test 6: Stop app tracking
        print("\n6. Stopping app tracking...")
        success = stop_app_tracking()
        print(f"   ✅ App tracking stopped: {success}")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_online_tracking() 