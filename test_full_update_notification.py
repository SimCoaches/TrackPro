#!/usr/bin/env python3
"""
Test script for the full update notification in TrackPro application context.
This simulates the main application startup and shows the update notification.
"""

import sys
import os

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer
from trackpro.ui.modern.main_window import ModernMainWindow

def test_full_update_notification():
    """Test the update notification in the full application context."""
    app = QApplication(sys.argv)
    
    # Create the main window (this will initialize the updater)
    main_window = ModernMainWindow()
    main_window.setWindowTitle("TrackPro - Full Update Test")
    main_window.setGeometry(100, 100, 1200, 800)
    main_window.show()
    
    # The updater should automatically check for updates on startup
    # Since we set the version to 1.2.5 and GitHub has 1.3.0, it should show the notification
    
    print("TrackPro application started with version 1.2.5")
    print("GitHub has version 1.3.0 available")
    print("The update notification should appear in the bottom-left corner...")
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    test_full_update_notification() 