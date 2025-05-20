#!/usr/bin/env python
"""
Test script for level-up notifications with sound.
This script demonstrates the level-up notification and sound effect.
"""

import sys
import time
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QSoundEffect

# Import the level up notification function
from notifications import show_level_up_notification, NotificationManager

# Fix the sound path when running from UI directory
class CustomNotificationManager(NotificationManager):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create absolute path to level_up.wav
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        level_up_sound_path = os.path.join(base_dir, "resources", "sounds", "level_up.wav")
        print(f"Loading sound from: {level_up_sound_path}")
        self.level_up_sound = QSoundEffect()
        self.level_up_sound.setSource(QUrl.fromLocalFile(level_up_sound_path))
        self.level_up_sound.setVolume(0.5)

# Override the _get_notification_manager function
original_get_notification_manager = None
_custom_notification_manager = None

def _get_custom_notification_manager(parent=None):
    global _custom_notification_manager
    if _custom_notification_manager is None:
        _custom_notification_manager = CustomNotificationManager(parent)
    elif parent is not None and _custom_notification_manager.parent is None:
        _custom_notification_manager.parent = parent
    return _custom_notification_manager

# Replace the manager function in notifications module
import notifications
original_get_notification_manager = notifications._get_notification_manager
notifications._get_notification_manager = _get_custom_notification_manager

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level Up Notification Test")
        self.setGeometry(100, 100, 500, 400)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Add instructions
        instructions = QLabel("Click the buttons below to test level-up notifications")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
        # Button for simple level up notification
        level_up_button = QPushButton("Show Level Up Notification")
        level_up_button.clicked.connect(self.show_level_up)
        level_up_button.setMinimumHeight(40)
        layout.addWidget(level_up_button)
        
        # Button for level up with rewards
        level_up_rewards_button = QPushButton("Show Level Up with Rewards")
        level_up_rewards_button.clicked.connect(self.show_level_up_rewards)
        level_up_rewards_button.setMinimumHeight(40)
        layout.addWidget(level_up_rewards_button)
        
        # Button for multiple level ups (testing multiple sounds)
        multiple_level_ups_button = QPushButton("Show Multiple Level Ups (Sequence)")
        multiple_level_ups_button.clicked.connect(self.show_multiple_level_ups)
        multiple_level_ups_button.setMinimumHeight(40)
        layout.addWidget(multiple_level_ups_button)
        
        # Status label
        self.status_label = QLabel("Ready for testing")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def show_level_up(self):
        """Show a basic level up notification."""
        self.status_label.setText("Showing level up notification...")
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
    
    def show_multiple_level_ups(self):
        """Simulate multiple level ups in sequence to test sound handling."""
        self.status_label.setText("Showing multiple level ups...")
        for level in range(5, 8):
            # Update status
            self.status_label.setText(f"Level up {level}...")
            # Show notification for this level
            show_level_up_notification(self, level)
            # Brief delay to allow sound to play
            app.processEvents()  # Process UI events to display notification
            time.sleep(2.0)  # Wait to let sound play
        self.status_label.setText("Multiple level up sequence completed")

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
        QLabel {
            color: #CCCCCC;
            font-size: 12pt;
        }
    """)
    
    window = TestWindow()
    window.show()
    
    try:
        sys.exit(app.exec_())
    finally:
        # Restore original function when done
        if original_get_notification_manager:
            notifications._get_notification_manager = original_get_notification_manager 