#!/usr/bin/env python3
"""Test script for the online users sidebar functionality."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from trackpro.ui.online_users_sidebar import OnlineUsersSidebar
    
    def test_sidebar():
        """Test the online users sidebar."""
        app = QApplication(sys.argv)
        
        # Create and show the sidebar
        sidebar = OnlineUsersSidebar()
        sidebar.setWindowTitle("Online Users Sidebar Test")
        sidebar.show()
        
        # Connect signals for testing
        sidebar.user_selected.connect(lambda user: print(f"User selected: {user['name']}"))
        sidebar.sidebar_toggled.connect(lambda expanded: print(f"Sidebar {'expanded' if expanded else 'collapsed'}"))
        
        print("Online Users Sidebar Test Started")
        print("- Click the toggle button to expand/collapse")
        print("- Click on users to test selection")
        print("- Close the window to exit")
        
        return app.exec()
    
    if __name__ == "__main__":
        sys.exit(test_sidebar())
        
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Make sure PyQt6 is installed: pip install PyQt6")
    sys.exit(1)