#!/usr/bin/env python3
"""
Test script for the update notification dialog.
Run this to see how the custom update dialog looks.
"""

import sys
import os

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt
from trackpro.ui.update_notification_dialog import UpdateNotificationDialog

def test_update_dialog():
    """Test the update notification dialog."""
    app = QApplication(sys.argv)
    
    # Create a main window to serve as parent
    main_window = QMainWindow()
    main_window.setWindowTitle("TrackPro - Update Test")
    main_window.setGeometry(100, 100, 800, 600)
    main_window.setStyleSheet("""
        QMainWindow {
            background-color: #2d2d2d;
            color: #ffffff;
        }
    """)
    main_window.show()
    
    # Create and show the dialog
    dialog = UpdateNotificationDialog("1.6.0", main_window)
    
    # Connect signals to test handlers
    def on_download():
        print("Download button clicked!")
        dialog.close()
    
    def on_cancel():
        print("Cancel button clicked!")
        dialog.close()
    
    dialog.download_clicked.connect(on_download)
    dialog.cancel_clicked.connect(on_cancel)
    
    # Show the dialog after a short delay to see the animation
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.singleShot(500, dialog.show)
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    test_update_dialog() 