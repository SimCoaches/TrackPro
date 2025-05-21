#!/usr/bin/env python
"""
Test script for level-up notifications with sound.
Run this script from the project root directory.
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt

# Import the needed notification modules
from trackpro.gamification.ui.notifications import show_level_up_notification
from trackpro.gamification.ui.toast_notification import ToastNotification

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TrackPro Notification Tests")
        self.setGeometry(100, 100, 600, 500)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title = QLabel("TrackPro Notification Tests")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Section: Toast Notification Tests
        toast_section = QLabel("Toast Notification Tests")
        toast_section.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 20px;")
        layout.addWidget(toast_section)
        
        # Buttons for toast notifications
        xp_toast_button = QPushButton("Show XP Toast (Rotating Icon)")
        xp_toast_button.clicked.connect(self.show_xp_toast)
        layout.addWidget(xp_toast_button)
        
        rp_toast_button = QPushButton("Show RP XP Toast (Pulsing Icon)")
        rp_toast_button.clicked.connect(self.show_rp_toast)
        layout.addWidget(rp_toast_button)
        
        # Section: Level Up Notification Tests
        level_up_section = QLabel("Level Up Notification Tests")
        level_up_section.setStyleSheet("font-size: 14pt; font-weight: bold; margin-top: 20px;")
        layout.addWidget(level_up_section)
        
        # Buttons for level up notifications
        level_up_button = QPushButton("Show Level Up Notification")
        level_up_button.clicked.connect(self.show_level_up)
        layout.addWidget(level_up_button)
        
        level_up_rewards_button = QPushButton("Show Level Up with Rewards")
        level_up_rewards_button.clicked.connect(self.show_level_up_rewards)
        layout.addWidget(level_up_rewards_button)
        
        # Status label
        self.status_label = QLabel("Click a button to test notifications")
        self.status_label.setStyleSheet("margin-top: 20px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def show_xp_toast(self):
        """Show a toast with XP animation."""
        self.status_label.setText("Showing XP toast notification...")
        ToastNotification.show_notification(
            self,
            "+150 XP",
            "trackpro/resources/icons/xp_icon.png",
            duration_ms=5000,
            icon_type='xp'
        )
    
    def show_rp_toast(self):
        """Show a toast with RP XP animation."""
        self.status_label.setText("Showing RP XP toast notification...")
        ToastNotification.show_notification(
            self,
            "+50 RP XP",
            "trackpro/resources/icons/rp_xp_icon.png",
            duration_ms=5000,
            icon_type='rp_xp'
        )
    
    def show_level_up(self):
        """Show a basic level up notification."""
        self.status_label.setText("Showing level up notification with sound...")
        show_level_up_notification(self, 5)
    
    def show_level_up_rewards(self):
        """Show a level up notification with rewards list."""
        self.status_label.setText("Showing level up with rewards...")
        rewards = [
            "New Driver Title: Weekend Warrior",
            "+10% XP Bonus for next quest",
            "Unlocked: TrackPro Premium Theme"
        ]
        show_level_up_notification(self, 10, rewards)

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
            padding: 8px;
            border-radius: 3px;
            font-size: 11pt;
            min-height: 40px;
        }
        QPushButton:hover {
            background-color: #555555;
        }
        QPushButton:pressed {
            background-color: #666666;
        }
        QLabel {
            color: #CCCCCC;
            font-size: 12pt;
        }
    """)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec_()) 