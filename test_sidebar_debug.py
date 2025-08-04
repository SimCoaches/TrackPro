#!/usr/bin/env python3
"""
Test script to debug online users sidebar issues.
This script will help diagnose why user images aren't showing up and positioning issues.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sidebar():
    """Test the online users sidebar functionality."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("TrackPro Sidebar Debug")
    window.resize(800, 600)
    
    # Create central widget
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Import and create sidebar
    try:
        from trackpro.ui.online_users_sidebar import OnlineUsersSidebar
        sidebar = OnlineUsersSidebar()
        layout.addWidget(sidebar)
        
        # Add test buttons
        test_button = QPushButton("Force Refresh Sidebar")
        test_button.clicked.connect(sidebar.force_refresh)
        layout.addWidget(test_button)
        
        # Add button to expand/collapse
        toggle_button = QPushButton("Toggle Sidebar")
        toggle_button.clicked.connect(sidebar.toggle_sidebar)
        layout.addWidget(toggle_button)
        
        # Add button to load test user
        def add_test_user():
            test_user = {
                'user_id': 'test_user_123',
                'username': 'testuser',
                'display_name': 'Test User',
                'avatar_url': 'https://via.placeholder.com/32x32/3498db/ffffff?text=T',
                'is_friend': False,
                'is_online': True,
                'status': 'Online'
            }
            sidebar.add_user(test_user)
            logger.info("Added test user to sidebar")
        
        test_user_button = QPushButton("Add Test User")
        test_user_button.clicked.connect(add_test_user)
        layout.addWidget(test_user_button)
        
        # Force initial refresh
        QTimer.singleShot(1000, sidebar.force_refresh)
        
        logger.info("✅ Sidebar test window created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating sidebar: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    window.show()
    return app.exec()

if __name__ == "__main__":
    test_sidebar() 