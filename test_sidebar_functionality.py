#!/usr/bin/env python3
"""
Test script to verify online users sidebar functionality.
This script tests the authentication and user loading logic.
"""

import os
import sys
import logging

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sidebar_authentication():
    """Test the sidebar authentication logic."""
    print("🧪 Testing sidebar authentication functionality...")
    
    try:
        # Import the sidebar
        from trackpro.ui.online_users_sidebar import OnlineUsersSidebar
        from PyQt6.QtWidgets import QApplication
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create sidebar
        sidebar = OnlineUsersSidebar()
        print("✅ Sidebar created successfully")
        
        # Test authentication check
        is_authenticated = sidebar.is_user_authenticated()
        current_user_id = sidebar.get_current_user_id()
        
        print(f"🔐 Authentication status: {is_authenticated}")
        print(f"👤 Current user ID: {current_user_id}")
        
        if is_authenticated and current_user_id:
            print("✅ User is authenticated and should appear in sidebar")
        else:
            print("⚠️ User not authenticated - this is expected if not logged in")
        
        # Test user loading
        sidebar.load_current_user_instantly()
        print(f"📊 Users in sidebar: {len(sidebar.all_users)}")
        
        for user in sidebar.all_users:
            print(f"  - {user.get('display_name', 'Unknown')} ({user.get('user_id', 'No ID')})")
        
        print("✅ Sidebar authentication test completed")
        
    except Exception as e:
        print(f"❌ Error testing sidebar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sidebar_authentication()
    print("\n�� Test completed") 