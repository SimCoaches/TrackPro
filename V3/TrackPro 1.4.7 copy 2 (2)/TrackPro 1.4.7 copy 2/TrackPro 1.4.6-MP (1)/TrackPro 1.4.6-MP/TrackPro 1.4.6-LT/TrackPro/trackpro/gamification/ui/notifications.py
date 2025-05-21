from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QGraphicsOpacityEffect, QFrame)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtMultimedia import QSoundEffect
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

class NotificationWidget(QFrame):
    """A popup notification widget that slides in from the corner, displays a message, and slides out."""
    
    closed = pyqtSignal()  # Signal emitted when notification is closed
    
    def __init__(self, title, message, notification_type="info", parent=None, duration=5000):
        """
        Initialize a notification popup widget.
        
        Args:
            title (str): Title of the notification
            message (str): Message content of the notification
            notification_type (str): Type of notification (info, success, warning, error)
            parent (QWidget): Parent widget
            duration (int): Display duration in milliseconds
        """
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("NotificationWidget")
        
        self.parent = parent
        self.duration = duration
        self.notification_type = notification_type
        
        # Style the notification based on type
        style_color = "#5E81AC"  # Default info color (Nord blue)
        icon_char = "ℹ️"  # Default info icon
        
        if notification_type == "success":
            style_color = "#A3BE8C"  # Nord aurora green
            icon_char = "✓"
        elif notification_type == "warning":
            style_color = "#EBCB8B"  # Nord aurora yellow
            icon_char = "⚠️"
        elif notification_type == "error":
            style_color = "#BF616A"  # Nord aurora red 
            icon_char = "✗"
        
        # Setup widget look
        self.setStyleSheet(f"""
            QFrame#NotificationWidget {{
                background-color: #2E3440;
                border-radius: 6px;
                border: 1px solid {style_color};
            }}
            QLabel#NotificationTitle {{
                color: {style_color};
                font-weight: bold;
                font-size: 14px;
            }}
            QLabel#NotificationMessage {{
                color: #E5E9F0;
                font-size: 12px;
            }}
            QPushButton#CloseButton {{
                background-color: transparent;
                color: #D8DEE9;
                border: none;
                padding: 2px;
            }}
            QPushButton#CloseButton:hover {{
                color: #ECEFF4;
            }}
        """)
        
        # Create the layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        
        # Title row with icon and close button
        title_row = QHBoxLayout()
        
        # Icon (optional - could be replaced with QIcon with proper resources)
        icon_label = QLabel(icon_char)
        icon_label.setStyleSheet(f"color: {style_color}; font-size: 16px;")
        
        # Title
        title_label = QLabel(title)
        title_label.setObjectName("NotificationTitle")
        
        # Close button
        close_button = QPushButton("×")  # Unicode × character
        close_button.setObjectName("CloseButton")
        close_button.setFixedSize(20, 20)
        close_button.clicked.connect(self.close_notification)
        
        # Add widgets to title row
        title_row.addWidget(icon_label)
        title_row.addWidget(title_label, 1)  # 1 = stretch factor
        title_row.addWidget(close_button)
        
        # Message
        message_label = QLabel(message)
        message_label.setObjectName("NotificationMessage")
        message_label.setWordWrap(True)
        
        # Add rows to main layout
        layout.addLayout(title_row)
        layout.addWidget(message_label)
        
        # Set a fixed width
        self.setFixedWidth(300)
        
        # Timer for auto-closing
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close_notification)
        
        # Animation objects (initialized in show_notification)
        self.show_animation = None
        self.hide_animation = None
    
    def show_notification(self):
        """Displays the notification with a slide-in animation."""
        # Calculate position (bottom right by default)
        if self.parent:
            parent_rect = self.parent.geometry()
            x = parent_rect.right() - self.width() - 20
            y = parent_rect.bottom() - self.height() - 20
            self.move(x, parent_rect.bottom() + 10)  # Start below the visible area
            end_pos = QPoint(x, y)
        else:
            # If no parent, just center on screen
            from PyQt5.QtWidgets import QApplication
            desktop = QApplication.desktop()
            screen_rect = desktop.screenGeometry()
            x = screen_rect.width() - self.width() - 20
            y = screen_rect.height() - self.height() - 40
            self.move(x, screen_rect.height() + 10)  # Start below screen
            end_pos = QPoint(x, y)
        
        # Setup and start show animation
        self.show_animation = QPropertyAnimation(self, b"pos")
        self.show_animation.setDuration(500)
        self.show_animation.setEndValue(end_pos)
        self.show_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Show the widget and start animation
        self.show()
        self.show_animation.start()
        
        # Start auto-close timer
        if self.duration > 0:
            self.timer.start(self.duration)
    
    def close_notification(self):
        """Closes the notification with a slide-out animation."""
        # Cancel timer if it's running
        if self.timer.isActive():
            self.timer.stop()
        
        # Setup and start hide animation
        current_pos = self.pos()
        
        if self.parent:
            end_pos = QPoint(current_pos.x(), self.parent.geometry().bottom() + 10)
        else:
            # Assuming screen
            from PyQt5.QtWidgets import QApplication
            desktop = QApplication.desktop()
            end_pos = QPoint(current_pos.x(), desktop.screenGeometry().height() + 10)
        
        self.hide_animation = QPropertyAnimation(self, b"pos")
        self.hide_animation.setDuration(500)
        self.hide_animation.setEndValue(end_pos)
        self.hide_animation.setEasingCurve(QEasingCurve.InCubic)
        self.hide_animation.finished.connect(self.on_animation_finished)
        self.hide_animation.start()
    
    def on_animation_finished(self):
        """Called when hide animation finishes."""
        self.hide()
        self.closed.emit()
        self.deleteLater()  # Clean up the widget

class NotificationManager:
    """Manages the creation and display of multiple notifications."""
    
    def __init__(self, parent=None):
        """Initialize the notification manager.
        
        Args:
            parent (QWidget): Parent widget for notifications (usually main window)
        """
        self.parent = parent
        self.active_notifications = []
        
        # Initialize sound effects
        self.level_up_sound = QSoundEffect()
        
        # Get the absolute path to the sound file
        level_up_sound_path = os.path.join("trackpro", "resources", "sounds", "level_up.wav")
        
        # First try relative path
        if os.path.exists(level_up_sound_path):
            absolute_path = os.path.abspath(level_up_sound_path)
            logger.info(f"Loading level up sound from relative path: {absolute_path}")
            self.level_up_sound.setSource(QUrl.fromLocalFile(absolute_path))
        else:
            # Try to find it using the file's directory as a reference
            try:
                current_file_path = os.path.abspath(__file__)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))))
                alternative_path = os.path.join(project_root, "trackpro", "resources", "sounds", "level_up.wav")
                
                if os.path.exists(alternative_path):
                    logger.info(f"Loading level up sound from alternate path: {alternative_path}")
                    self.level_up_sound.setSource(QUrl.fromLocalFile(alternative_path))
                else:
                    logger.warning(f"Level up sound file not found at: {alternative_path}")
            except Exception as e:
                logger.error(f"Error finding level up sound file: {e}")
        
        self.level_up_sound.setVolume(0.5)  # Set at 50% volume
        
    def show_notification(self, title, message, notification_type="info", duration=5000):
        """Show a new notification.
        
        Args:
            title (str): Title of the notification
            message (str): Message content of the notification
            notification_type (str): Type of notification (info, success, warning, error)
            duration (int): Display duration in milliseconds
        """
        notification = NotificationWidget(
            title, message, notification_type, self.parent, duration
        )
        
        notification.closed.connect(lambda: self._remove_notification(notification))
        self.active_notifications.append(notification)
        notification.show_notification()
        
        # Return the notification object in case caller wants to connect to its signals
        return notification
    
    def _remove_notification(self, notification):
        """Remove a notification from the active list."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
    
    def show_level_up(self, new_level, rewards=None):
        """Show a level up notification.
        
        Args:
            new_level (int): The new level achieved
            rewards (list): Optional list of rewards gained
        """
        title = "LEVEL UP!"
        message = f"Congratulations! You've reached Level {new_level}."
        
        if rewards:
            message += " Rewards:\n" + "\n".join([f"• {reward}" for reward in rewards])
        
        # Play level up sound if it's loaded
        if self.level_up_sound.isLoaded():
            logger.info(f"Playing level up sound for level {new_level}")
            self.level_up_sound.play()
        else:
            logger.warning(f"Level up sound not loaded")
        
        # Create a more prominent notification for level ups
        notification = NotificationWidget(
            title, message, "level_up", self.parent, 8000
        )
        
        # Add to tracked notifications
        notification.closed.connect(lambda: self._remove_notification(notification))
        self.active_notifications.append(notification)
        
        # Show the notification
        notification.show_notification()
        
        return notification
    
    def show_quest_complete(self, quest_name, reward=None):
        """Show a quest completion notification.
        
        Args:
            quest_name (str): Name of the completed quest
            reward (str): Optional reward description
        """
        title = "Quest Complete!"
        message = f"{quest_name}"
        
        if reward:
            message += f"\nReward: {reward}"
        
        return self.show_notification(title, message, "success")
    
    def show_race_pass_tier_up(self, new_tier, rewards=None):
        """Show a notification for advancing a Race Pass tier.
        
        Args:
            new_tier (int): The new tier reached
            rewards (list): Optional list of rewards gained
        """
        title = f"Race Pass Tier {new_tier} Unlocked!"
        message = f"You've advanced to Tier {new_tier}."
        
        if rewards:
            message += " Rewards:\n" + "\n".join([f"• {reward}" for reward in rewards])
        
        return self.show_notification(title, message, "success", 7000)
    
    def show_reward_unlocked(self, reward_name, reward_type="item"):
        """Show a notification for unlocking a reward.
        
        Args:
            reward_name (str): Name of the unlocked reward
            reward_type (str): Type of reward (e.g., title, badge, cosmetic)
        """
        title = f"New {reward_type.title()} Unlocked!"
        message = f"You've unlocked: {reward_name}"
        
        return self.show_notification(title, message, "info")


# Example usage (for testing standalone)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
    app = QApplication(sys.argv)
    
    # Create a simple test window
    main_window = QMainWindow()
    main_window.setWindowTitle("Notification Test")
    main_window.setGeometry(100, 100, 800, 600)
    
    # Create content
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Create a notification manager
    manager = NotificationManager(main_window)
    
    # Add some test buttons
    info_button = QPushButton("Show Info Notification")
    info_button.clicked.connect(lambda: manager.show_notification(
        "Information", "This is an informational message.", "info"))
    
    success_button = QPushButton("Show Success Notification")
    success_button.clicked.connect(lambda: manager.show_notification(
        "Success", "Operation completed successfully!", "success"))
    
    warning_button = QPushButton("Show Warning Notification")
    warning_button.clicked.connect(lambda: manager.show_notification(
        "Warning", "This action might cause problems.", "warning"))
    
    error_button = QPushButton("Show Error Notification")
    error_button.clicked.connect(lambda: manager.show_notification(
        "Error", "An error occurred while processing your request.", "error"))
    
    level_up_button = QPushButton("Show Level Up Notification")
    level_up_button.clicked.connect(lambda: manager.show_level_up(
        5, ["Title: Race Rookie", "+1 Race Pass Tier Skip"]))
    
    quest_button = QPushButton("Show Quest Complete Notification")
    quest_button.clicked.connect(lambda: manager.show_quest_complete(
        "Complete 10 Laps at Monza", "+200 XP, +1 Race Pass Star"))
    
    # Add buttons to layout
    layout.addWidget(info_button)
    layout.addWidget(success_button)
    layout.addWidget(warning_button)
    layout.addWidget(error_button)
    layout.addWidget(level_up_button)
    layout.addWidget(quest_button)
    
    main_window.setCentralWidget(central_widget)
    main_window.show()
    
    sys.exit(app.exec_()) 


# --- Standalone Notification Functions ---
# These are imported directly by other modules

# Cache a single notification manager instance
_notification_manager = None

def _get_notification_manager(parent=None):
    """Get or create a notification manager singleton."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager(parent)
    elif parent is not None and _notification_manager.parent is None:
        # Update parent if we have one now
        _notification_manager.parent = parent
    return _notification_manager

def show_level_up_notification(parent, new_level, rewards=None):
    """Show a level up notification with sound.
    
    Args:
        parent (QWidget): Parent widget for the notification
        new_level (int): The new level achieved
        rewards (list, optional): List of rewards gained
    """
    logger.info(f"Showing level up notification for level {new_level}")
    manager = _get_notification_manager(parent)
    return manager.show_level_up(new_level, rewards)

def show_quest_completed_notification(parent, quest_name, reward=None):
    """Show a quest completion notification.
    
    Args:
        parent (QWidget): Parent widget for the notification
        quest_name (str): Name of the completed quest
        reward (str, optional): Reward description
    """
    logger.info(f"Showing quest completion notification for {quest_name}")
    manager = _get_notification_manager(parent)
    return manager.show_quest_complete(quest_name, reward) 