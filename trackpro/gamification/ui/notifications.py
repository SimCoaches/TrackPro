from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QGraphicsOpacityEffect, QFrame)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal, QUrl, QRect, QParallelAnimationGroup, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QLinearGradient, QPen, QBrush, QPixmap
from PyQt6.QtMultimedia import QSoundEffect
import os
import logging
import math
import random

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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and app.screens():
                screen_rect = app.screens()[0].geometry()
            else:
                # Fallback if no screens found
                screen_rect = QRect(0, 0, 1920, 1080)
            x = screen_rect.width() - self.width() - 20
            y = screen_rect.height() - self.height() - 40
            self.move(x, screen_rect.height() + 10)  # Start below screen
            end_pos = QPoint(x, y)
        
        # Setup and start show animation
        self.show_animation = QPropertyAnimation(self, b"pos")
        self.show_animation.setDuration(500)
        self.show_animation.setEndValue(end_pos)
        self.show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
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
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app and app.screens():
                screen_height = app.screens()[0].geometry().height()
            else:
                screen_height = 1080  # Fallback
            end_pos = QPoint(current_pos.x(), screen_height + 10)
        
        self.hide_animation = QPropertyAnimation(self, b"pos")
        self.hide_animation.setDuration(500)
        self.hide_animation.setEndValue(end_pos)
        self.hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
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
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
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
    
    sys.exit(app.exec()) 


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

class XPGainNotification(QWidget):
    """Animated notification for XP gains with particle effects"""
    
    def __init__(self, parent, quest_title, xp_amount):
        super().__init__(parent)
        self.quest_title = quest_title
        self.xp_amount = xp_amount
        self.particles = []
        
        # Animation properties
        self._opacity = 0.0
        self._scale = 0.5
        self._particle_progress = 0.0
        
        self.setFixedSize(350, 120)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self._init_ui()
        self._init_particles()
        
    def _init_ui(self):
        self.setStyleSheet("""
            XPGainNotification {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(52, 152, 219, 200),
                    stop:0.5 rgba(41, 128, 185, 220),
                    stop:1 rgba(52, 152, 219, 200));
                border: 3px solid #3498DB;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)
        
        # Quest title
        self.title_label = QLabel(self.quest_title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: white; background: transparent;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # XP amount with animated counter
        self.xp_label = QLabel(f"+{self.xp_amount} XP")
        self.xp_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.xp_label.setStyleSheet("""
            color: #F1C40F;
            background: transparent;
            font-weight: bold;
        """)
        self.xp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.xp_label)
        
        # Completion message
        completion_label = QLabel("Quest Completed!")
        completion_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        completion_label.setStyleSheet("color: #2ECC71; background: transparent;")
        completion_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(completion_label)
        
    def _init_particles(self):
        """Initialize particle system for visual effects"""
        for i in range(15):
            particle = {
                'x': self.width() // 2,
                'y': self.height() // 2,
                'vx': (random.random() - 0.5) * 4,
                'vy': (random.random() - 0.5) * 4,
                'life': 1.0,
                'size': random.random() * 4 + 2
            }
            self.particles.append(particle)
            
    @pyqtProperty(float)
    def opacity(self):
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(value)
        self.setGraphicsEffect(effect)
        
    @pyqtProperty(float)
    def scale(self):
        return self._scale
        
    @scale.setter
    def scale(self, value):
        self._scale = value
        self.resize(int(350 * value), int(120 * value))
        
    @pyqtProperty(float)
    def particleProgress(self):
        return self._particle_progress
        
    @particleProgress.setter
    def particleProgress(self, value):
        self._particle_progress = value
        self.update()  # Trigger repaint for particles
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw particles
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for particle in self.particles:
            # Update particle position based on progress
            progress = self._particle_progress
            x = particle['x'] + particle['vx'] * progress * 50
            y = particle['y'] + particle['vy'] * progress * 50
            
            # Calculate particle alpha based on life and progress
            alpha = int(255 * particle['life'] * (1 - progress))
            color = QColor(241, 196, 15, alpha)  # Gold color
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            size = particle['size'] * (1 + progress * 2)
            painter.drawEllipse(int(x - size/2), int(y - size/2), int(size), int(size))
            
    def show_notification(self):
        """Show the notification with animations"""
        # Position at top-right of parent
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(parent_rect.width() - self.width() - 20, 20)
        
        self.show()
        
        # Create animation group
        self.animation_group = QParallelAnimationGroup()
        
        # Fade in and scale animation
        self.opacity_anim = QPropertyAnimation(self, b"opacity")
        self.opacity_anim.setDuration(500)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.scale_anim = QPropertyAnimation(self, b"scale")
        self.scale_anim.setDuration(500)
        self.scale_anim.setStartValue(0.5)
        self.scale_anim.setEndValue(1.0)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Particle animation
        self.particle_anim = QPropertyAnimation(self, b"particleProgress")
        self.particle_anim.setDuration(2000)
        self.particle_anim.setStartValue(0.0)
        self.particle_anim.setEndValue(1.0)
        self.particle_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.animation_group.addAnimation(self.opacity_anim)
        self.animation_group.addAnimation(self.scale_anim)
        self.animation_group.addAnimation(self.particle_anim)
        
        # Fade out after delay
        self.fade_out_timer = QTimer()
        self.fade_out_timer.timeout.connect(self._fade_out)
        self.fade_out_timer.setSingleShot(True)
        self.fade_out_timer.start(2500)
        
        self.animation_group.start()
        
    def _fade_out(self):
        """Fade out the notification"""
        self.fade_out_anim = QPropertyAnimation(self, b"opacity")
        self.fade_out_anim.setDuration(500)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self.deleteLater)
        self.fade_out_anim.start()


class LevelUpNotification(QWidget):
    """Epic level up notification with burst effects"""
    
    def __init__(self, parent, old_level, new_level):
        super().__init__(parent)
        self.old_level = old_level
        self.new_level = new_level
        
        # Animation properties
        self._opacity = 0.0
        self._scale = 0.3
        self._burst_progress = 0.0
        self._glow_intensity = 0.0
        
        self.setFixedSize(400, 200)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self._init_ui()
        
    def _init_ui(self):
        self.setStyleSheet("""
            LevelUpNotification {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(155, 89, 182, 230),
                    stop:0.3 rgba(142, 68, 173, 250),
                    stop:0.7 rgba(155, 89, 182, 250),
                    stop:1 rgba(142, 68, 173, 230));
                border: 4px solid #9B59B6;
                border-radius: 20px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)
        
        # Level up title
        title_label = QLabel("LEVEL UP!")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("""
            color: #F1C40F;
            background: transparent;
            font-weight: bold;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Level progression
        level_layout = QHBoxLayout()
        
        old_level_label = QLabel(str(self.old_level))
        old_level_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        old_level_label.setStyleSheet("color: #BDC3C7; background: transparent;")
        old_level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        arrow_label = QLabel("→")
        arrow_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        arrow_label.setStyleSheet("color: white; background: transparent;")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        new_level_label = QLabel(str(self.new_level))
        new_level_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        new_level_label.setStyleSheet("""
            color: #F1C40F;
            background: transparent;
            font-weight: bold;
        """)
        new_level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        level_layout.addWidget(old_level_label)
        level_layout.addWidget(arrow_label)
        level_layout.addWidget(new_level_label)
        layout.addLayout(level_layout)
        
        # Congratulations message
        congrats_label = QLabel("Congratulations!")
        congrats_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        congrats_label.setStyleSheet("color: #2ECC71; background: transparent;")
        congrats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(congrats_label)
        
    @pyqtProperty(float)
    def opacity(self):
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(value)
        self.setGraphicsEffect(effect)
        
    @pyqtProperty(float)
    def scale(self):
        return self._scale
        
    @scale.setter
    def scale(self, value):
        self._scale = value
        self.resize(int(400 * value), int(200 * value))
        
    @pyqtProperty(float)
    def burstProgress(self):
        return self._burst_progress
        
    @burstProgress.setter
    def burstProgress(self, value):
        self._burst_progress = value
        self.update()
        
    @pyqtProperty(float)
    def glowIntensity(self):
        return self._glow_intensity
        
    @glowIntensity.setter
    def glowIntensity(self, value):
        self._glow_intensity = value
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw burst rays
        if self._burst_progress > 0:
            center_x = self.width() // 2
            center_y = self.height() // 2
            
            painter.setPen(QPen(QColor(241, 196, 15, int(255 * (1 - self._burst_progress))), 3))
            
            for i in range(12):
                angle = (i * 30) * math.pi / 180
                start_radius = 20 + self._burst_progress * 50
                end_radius = 50 + self._burst_progress * 100
                
                start_x = center_x + math.cos(angle) * start_radius
                start_y = center_y + math.sin(angle) * start_radius
                end_x = center_x + math.cos(angle) * end_radius
                end_y = center_y + math.sin(angle) * end_radius
                
                painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
                
        # Draw glow effect
        if self._glow_intensity > 0:
            glow_color = QColor(155, 89, 182, int(100 * self._glow_intensity))
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            glow_size = 50 + self._glow_intensity * 30
            painter.drawEllipse(
                int(self.width() // 2 - glow_size // 2),
                int(self.height() // 2 - glow_size // 2),
                int(glow_size),
                int(glow_size)
            )
            
    def show_notification(self):
        """Show the level up notification with epic animations"""
        # Center on parent
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.width() // 2 - self.width() // 2,
                parent_rect.height() // 2 - self.height() // 2
            )
        
        self.show()
        
        # Create animation sequence
        self.animation_group = QParallelAnimationGroup()
        
        # Dramatic entrance
        self.opacity_anim = QPropertyAnimation(self, b"opacity")
        self.opacity_anim.setDuration(800)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.scale_anim = QPropertyAnimation(self, b"scale")
        self.scale_anim.setDuration(800)
        self.scale_anim.setStartValue(0.3)
        self.scale_anim.setEndValue(1.0)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        
        # Burst effect
        self.burst_anim = QPropertyAnimation(self, b"burstProgress")
        self.burst_anim.setDuration(1500)
        self.burst_anim.setStartValue(0.0)
        self.burst_anim.setEndValue(1.0)
        self.burst_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Glow effect
        self.glow_anim = QPropertyAnimation(self, b"glowIntensity")
        self.glow_anim.setDuration(2000)
        self.glow_anim.setStartValue(0.0)
        self.glow_anim.setEndValue(1.0)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self.animation_group.addAnimation(self.opacity_anim)
        self.animation_group.addAnimation(self.scale_anim)
        self.animation_group.addAnimation(self.burst_anim)
        self.animation_group.addAnimation(self.glow_anim)
        
        # Auto-hide after delay
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self._fade_out)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(3500)
        
        self.animation_group.start()
        
    def _fade_out(self):
        """Fade out the notification"""
        self.fade_out_anim = QPropertyAnimation(self, b"opacity")
        self.fade_out_anim.setDuration(800)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self.deleteLater)
        self.fade_out_anim.start()


class ToastNotification(QWidget):
    """Simple toast notification for general messages"""
    
    def __init__(self, parent, message, duration=3000, notification_type="info"):
        super().__init__(parent)
        self.message = message
        self.duration = duration
        self.notification_type = notification_type
        
        self._opacity = 0.0
        
        self.setFixedSize(300, 80)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self._init_ui()
        
    def _init_ui(self):
        # Set style based on notification type
        colors = {
            "info": "#3498DB",
            "success": "#2ECC71", 
            "warning": "#F39C12",
            "error": "#E74C3C"
        }
        
        color = colors.get(self.notification_type, "#3498DB")
        
        self.setStyleSheet(f"""
            ToastNotification {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba{self._hex_to_rgba(color, 200)},
                    stop:1 rgba{self._hex_to_rgba(color, 180)});
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        message_label = QLabel(self.message)
        message_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        message_label.setStyleSheet("color: white; background: transparent;")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
    def _hex_to_rgba(self, hex_color, alpha):
        """Convert hex color to RGBA tuple"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"({r}, {g}, {b}, {alpha})"
        
    @pyqtProperty(float)
    def opacity(self):
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(value)
        self.setGraphicsEffect(effect)
        
    def show_notification(self):
        """Show the toast notification"""
        # Position at bottom-right of parent
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(parent_rect.width() - self.width() - 20, parent_rect.height() - self.height() - 20)
        
        self.show()
        
        # Fade in
        self.fade_in_anim = QPropertyAnimation(self, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in_anim.start()
        
        # Auto-hide
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self._fade_out)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(self.duration)
        
    def _fade_out(self):
        """Fade out the notification"""
        self.fade_out_anim = QPropertyAnimation(self, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self.deleteLater)
        self.fade_out_anim.start() 