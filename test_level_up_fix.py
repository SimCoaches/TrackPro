#!/usr/bin/env python
"""
Simplified test for level-up notifications with improved visibility.
This script creates a simple test that ensures the notification is visible.
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QLabel, QFrame, QHBoxLayout, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QUrl
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtMultimedia import QSoundEffect

class EnhancedLevelUpNotification(QFrame):
    """A more visible level-up notification for testing purposes."""
    
    def __init__(self, parent, level, rewards=None):
        super().__init__(parent)
        
        # Set window flags to ensure it appears on top
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Make it stand out with vibrant gradient colors and glowing border effect
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #2ecc71, stop:0.5 #27ae60, stop:1 #2ecc71);
                color: white;
                border: 4px solid #f1c40f;
                border-radius: 15px;
            }
            QLabel {
                background-color: transparent;
                color: white;
                font-weight: bold;
            }
            QLabel#TitleLabel {
                font-size: 28pt;
                margin-bottom: 15px;
                color: #f1c40f;
                font-weight: bold;
                text-shadow: 2px 2px 3px rgba(0,0,0,0.5);
            }
            QLabel#MessageLabel {
                font-size: 18pt;
                color: white;
                margin: 10px 0;
            }
            QLabel#RewardsLabel {
                font-size: 16pt;
                color: #f1c40f;
                margin-top: 10px;
                margin-bottom: 5px;
            }
            QLabel#RewardItem {
                font-size: 14pt;
                color: white;
                margin-left: 20px;
                padding-left: 10px;
                margin-bottom: 5px;
            }
        """)
        
        # Fixed size and centered position
        self.setFixedSize(500, 300)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Create labels with decorative elements
        title_container = QWidget()
        title_container.setStyleSheet("background-color: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Trophy icon left
        trophy_left = QLabel("🏆")
        trophy_left.setStyleSheet("font-size: 32pt; color: gold;")
        
        # Main title
        title = QLabel("LEVEL UP!")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        
        # Trophy icon right
        trophy_right = QLabel("🏆")
        trophy_right.setStyleSheet("font-size: 32pt; color: gold;")
        
        # Add to title layout
        title_layout.addWidget(trophy_left, 0, Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(title, 1, Qt.AlignCenter)
        title_layout.addWidget(trophy_right, 0, Qt.AlignLeft | Qt.AlignVCenter)
        
        # Level display with decorative line
        level_container = QWidget()
        level_container.setStyleSheet("background-color: transparent;")
        level_layout = QHBoxLayout(level_container)
        level_layout.setContentsMargins(15, 0, 15, 0)
        
        # Left decorative line
        left_line = QFrame()
        left_line.setFrameShape(QFrame.HLine)
        left_line.setStyleSheet("background-color: gold; min-height: 2px; margin: 0 10px;")
        
        # Level number with dramatic styling
        message = QLabel(f"Level {level}")
        message.setObjectName("MessageLabel")
        message.setAlignment(Qt.AlignCenter)
        
        # Right decorative line
        right_line = QFrame()
        right_line.setFrameShape(QFrame.HLine)
        right_line.setStyleSheet("background-color: gold; min-height: 2px; margin: 0 10px;")
        
        # Add to level layout
        level_layout.addWidget(left_line, 1)
        level_layout.addWidget(message, 0)
        level_layout.addWidget(right_line, 1)
        
        # Congratulations text
        congrats = QLabel("Congratulations!")
        congrats.setStyleSheet("font-size: 16pt; color: white; margin: 5px 0;")
        congrats.setAlignment(Qt.AlignCenter)
        
        # Add main elements to layout
        layout.addWidget(title_container)
        layout.addWidget(level_container)
        layout.addWidget(congrats)
        
        # Add rewards if provided
        if rewards:
            # Decorative line before rewards
            divider = QFrame()
            divider.setFrameShape(QFrame.HLine)
            divider.setStyleSheet("background-color: rgba(255,255,255,0.3); min-height: 1px; margin: 5px 30px;")
            layout.addWidget(divider)
            
            # Rewards title
            rewards_label = QLabel("Rewards")
            rewards_label.setObjectName("RewardsLabel")
            rewards_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(rewards_label)
            
            # Create a container for rewards
            rewards_container = QWidget()
            rewards_container.setStyleSheet("background-color: rgba(0,0,0,0.1); border-radius: 8px; margin: 5px;")
            rewards_layout = QVBoxLayout(rewards_container)
            rewards_layout.setSpacing(8)
            rewards_layout.setContentsMargins(15, 10, 15, 10)
            
            # Add each reward with star icon
            for reward in rewards:
                reward_item = QLabel(f"★ {reward}")
                reward_item.setObjectName("RewardItem")
                rewards_layout.addWidget(reward_item)
            
            layout.addWidget(rewards_container)
        
        # Add spacer
        layout.addStretch()
        
        # Setup animations for appearing effect
        self.setOpacity(0.0)
        self.fadeIn()
        
        # Load and play level-up sound using absolute path
        self.level_up_sound = QSoundEffect()
        
        # Get the absolute path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sound_path = os.path.join(script_dir, "trackpro", "resources", "sounds", "level_up.wav")
        
        # If that doesn't work, try relative to workspace root
        if not os.path.exists(sound_path):
            sound_path = os.path.join("trackpro", "resources", "sounds", "level_up.wav")
            # Get absolute path
            sound_path = os.path.abspath(sound_path)
            
        print(f"Loading sound from: {sound_path}")
        if os.path.exists(sound_path):
            self.level_up_sound.setSource(QUrl.fromLocalFile(sound_path))
            self.level_up_sound.setVolume(0.7)
            if self.level_up_sound.isLoaded():
                self.level_up_sound.play()
            else:
                print(f"Sound file exists but couldn't be loaded")
        else:
            print(f"Sound file not found at: {sound_path}")
        
        # Show for a few seconds then close with animation
        QTimer.singleShot(7000, self.fadeOut)
        
        # Position and show
        self.center_on_parent()
        self.show()
        self.raise_()  # Bring to front
        self.activateWindow()  # Give it keyboard focus
    
    def setOpacity(self, opacity):
        """Set widget opacity using a QGraphicsOpacityEffect."""
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(opacity)
        self.setGraphicsEffect(opacity_effect)
    
    def fadeIn(self):
        """Animate fade-in with scale effect."""
        # Create opacity animation
        self.fade_anim = QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.fade_anim.setDuration(500)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Create geometry animation for a slight "pop" effect
        self.geometry_anim = QPropertyAnimation(self, b"geometry")
        self.geometry_anim.setDuration(500)
        start_rect = self.geometry()
        scaled_rect = start_rect.adjusted(
            start_rect.width() * 0.1, 
            start_rect.height() * 0.1, 
            -start_rect.width() * 0.1,
            -start_rect.height() * 0.1
        )
        self.geometry_anim.setStartValue(scaled_rect)
        self.geometry_anim.setEndValue(start_rect)
        self.geometry_anim.setEasingCurve(QEasingCurve.OutBack)
        
        # Start animations
        self.fade_anim.start()
        self.geometry_anim.start()
    
    def fadeOut(self):
        """Animate fade-out with scale effect before closing."""
        # Create fade out animation
        self.fade_out_anim = QPropertyAnimation(self.graphicsEffect(), b"opacity")
        self.fade_out_anim.setDuration(500)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.InCubic)
        
        # When animation is finished, close the widget
        self.fade_out_anim.finished.connect(self.close)
        
        # Start animation
        self.fade_out_anim.start()
        
    def center_on_parent(self):
        """Center this widget on its parent or screen."""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.center().x() - self.width() // 2
            y = parent_rect.center().y() - self.height() // 2
            self.move(x, y)
        else:
            # Center on screen
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level Up Test Fix")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Add test buttons
        instruction = QLabel("Click a button to test level-up notification")
        instruction.setAlignment(Qt.AlignCenter)
        layout.addWidget(instruction)
        
        level_up_btn = QPushButton("Show Simple Level Up")
        level_up_btn.clicked.connect(lambda: self.show_level_up(5))
        layout.addWidget(level_up_btn)
        
        level_up_rewards_btn = QPushButton("Show Level Up With Rewards")
        level_up_rewards_btn.clicked.connect(self.show_level_up_with_rewards)
        layout.addWidget(level_up_rewards_btn)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
    
    def show_level_up(self, level):
        """Show a level-up notification."""
        self.status_label.setText(f"Showing Level {level} notification...")
        self.notification = EnhancedLevelUpNotification(self, level)
    
    def show_level_up_with_rewards(self):
        """Show a level-up notification with rewards."""
        self.status_label.setText("Showing Level 10 notification with rewards...")
        rewards = [
            "New Car: Formula Speed",
            "+10% XP Bonus for 1 Day",
            "Special Paint: Gold Rush"
        ]
        self.notification = EnhancedLevelUpNotification(self, 10, rewards)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark theme
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2c3e50;
            color: white;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
            font-size: 14pt;
            min-height: 50px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QLabel {
            color: #ecf0f1;
            font-size: 14pt;
        }
    """)
    
    window = TestWindow()
    window.show()
    sys.exit(app.exec_()) 