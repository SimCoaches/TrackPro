#!/usr/bin/env python
"""
Test for ToastNotification with animated icons.
This demonstrates the different icon animations in the toast notification.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

# Import the ToastNotification class
from toast_notification import ToastNotification

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toast Notification Animation Test")
        self.setGeometry(100, 100, 500, 400)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Button for XP notification
        xp_button = QPushButton("Show XP Toast (Rotating Icon)")
        xp_button.clicked.connect(self.show_xp_toast)
        xp_button.setMinimumHeight(40)
        layout.addWidget(xp_button)
        
        # Button for RP XP notification
        rp_button = QPushButton("Show RP XP Toast (Pulsing Icon)")
        rp_button.clicked.connect(self.show_rp_toast)
        rp_button.setMinimumHeight(40)
        layout.addWidget(rp_button)
        
        # Button for multiple notifications at once
        multi_button = QPushButton("Show Both Notifications")
        multi_button.clicked.connect(self.show_multiple_toasts)
        multi_button.setMinimumHeight(40)
        layout.addWidget(multi_button)
    
    def show_xp_toast(self):
        """Show toast with rotating XP icon."""
        ToastNotification.show_notification(
            self,
            "+150 XP",
            "trackpro/resources/icons/xp_icon.png",
            duration_ms=5000,  # Longer duration to see animation
            icon_type='xp'
        )
    
    def show_rp_toast(self):
        """Show toast with pulsing RP XP icon."""
        ToastNotification.show_notification(
            self,
            "+50 RP XP",
            "trackpro/resources/icons/rp_xp_icon.png",
            duration_ms=5000,  # Longer duration to see animation
            icon_type='rp_xp'
        )
    
    def show_multiple_toasts(self):
        """Show both toasts with a slight delay between them."""
        self.show_xp_toast()
        # The second toast will be positioned correctly by the toast notification class
        self.show_rp_toast()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for consistent appearance
    
    # Set dark theme similar to TrackPro
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #333333;
            color: white;
        }
        QPushButton {
            background-color: #444444;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #555555;
        }
        QPushButton:pressed {
            background-color: #666666;
        }
    """)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec_()) 