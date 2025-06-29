"""
Gaming-style transparent overlay for eye tracking visualization.

This creates a transparent, click-through overlay that shows the gaze dot
floating over any application (like iRacing) without interfering with gameplay.
"""

import logging
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor

logger = logging.getLogger(__name__)


class EyeTrackingGamingOverlay(QWidget):
    """Transparent gaming overlay that shows eye tracking gaze dot over any application."""
    
    overlay_closed = pyqtSignal()  # Signal when overlay is closed
    
    def __init__(self):
        super().__init__()
        
        # Gaze position data
        self.gaze_x = 0
        self.gaze_y = 0
        self.is_blink = False
        self.is_tracking = False
        
        # Visual settings
        self.dot_size = 15
        self.dot_color_normal = QColor(50, 255, 50, 200)    # Semi-transparent bright green
        self.dot_color_blink = QColor(255, 50, 50, 200)     # Semi-transparent red
        self.dot_outline_color = QColor(0, 0, 0, 150)       # Semi-transparent black outline
        
        # Initialize the overlay
        self.setup_overlay()
        
        logger.info("🎮 Gaming overlay initialized")
    
    def setup_overlay(self):
        """Set up the transparent gaming overlay window."""
        # Get screen dimensions
        desktop = QApplication.desktop()
        screen_rect = desktop.screenGeometry()
        
        # Window flags for transparent, always-on-top, click-through overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |           # No window frame
            Qt.WindowType.WindowStaysOnTopHint |          # Always on top
            Qt.WindowType.Tool |                          # Tool window (doesn't appear in taskbar)
            Qt.X11BypassWindowManagerHint      # Bypass window manager (Linux compatibility)
        )
        
        # Make window transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # Click-through
        
        # Set window to cover entire screen
        self.setGeometry(screen_rect)
        
        # Set window title (for debugging)
        self.setWindowTitle("TrackPro Eye Tracking Overlay")
        
        logger.info(f"🎮 Gaming overlay setup: {screen_rect.width()}x{screen_rect.height()}")
    
    def update_gaze_position(self, x, y, is_blink=False):
        """Update the gaze position and trigger a repaint."""
        self.gaze_x = int(x)
        self.gaze_y = int(y)
        self.is_blink = is_blink
        self.is_tracking = True
        
        # Update the entire overlay to clear old dots and show only current position
        self.update()
    
    def set_tracking_status(self, is_tracking):
        """Set whether eye tracking is active."""
        was_tracking = self.is_tracking
        self.is_tracking = is_tracking
        
        # If tracking status changed, repaint the whole overlay
        if was_tracking != is_tracking:
            self.update()
    
    def paintEvent(self, event):
        """Paint the gaze dot on the transparent overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Clear the entire overlay first (make it transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Only draw if we're tracking
        if not self.is_tracking:
            return
        
        # Choose colors based on blink state
        if self.is_blink:
            dot_color = self.dot_color_blink
        else:
            dot_color = self.dot_color_normal
        
        # Draw dot with outline for better visibility
        # Outline
        painter.setPen(QPen(self.dot_outline_color, 2))
        painter.setBrush(QBrush(self.dot_outline_color))
        painter.drawEllipse(self.gaze_x - self.dot_size - 1, 
                           self.gaze_y - self.dot_size - 1, 
                           (self.dot_size + 1) * 2, 
                           (self.dot_size + 1) * 2)
        
        # Main dot
        painter.setPen(QPen(dot_color, 1))
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(self.gaze_x - self.dot_size, 
                           self.gaze_y - self.dot_size, 
                           self.dot_size * 2, 
                           self.dot_size * 2)
    
    def keyPressEvent(self, event):
        """Handle key presses (like 'q' to quit)."""
        if event.key() == Qt.Key.Key_Q:
            logger.info("🎮 Gaming overlay closed by user (pressed 'Q')")
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("🎮 Gaming overlay closing")
        self.overlay_closed.emit()
        event.accept()
    
    def show_overlay(self):
        """Show the gaming overlay."""
        self.show()
        self.raise_()  # Bring to front
        self.activateWindow()  # Activate (but clicks still pass through)
        logger.info("🎮 Gaming overlay shown - gaze dot will appear over all applications")
    
    def hide_overlay(self):
        """Hide the gaming overlay."""
        self.hide()
        logger.info("🎮 Gaming overlay hidden")
    
    def set_dot_size(self, size):
        """Set the size of the gaze dot."""
        self.dot_size = max(5, min(50, size))  # Clamp between 5-50 pixels
        self.update()
    
    def set_dot_opacity(self, opacity):
        """Set the opacity of the gaze dot (0-255)."""
        opacity = max(50, min(255, opacity))  # Clamp between 50-255
        
        # Update colors with new opacity
        self.dot_color_normal.setAlpha(opacity)
        self.dot_color_blink.setAlpha(opacity)
        self.dot_outline_color.setAlpha(max(100, opacity - 50))  # Outline slightly less visible
        
        self.update()


class EyeTrackingGamingOverlayManager:
    """Manager for the gaming overlay - handles creation, positioning, and cleanup."""
    
    def __init__(self):
        self.overlay = None
        self.is_active = False
        
    def create_overlay(self):
        """Create the gaming overlay."""
        if self.overlay is None:
            self.overlay = EyeTrackingGamingOverlay()
            self.overlay.overlay_closed.connect(self.on_overlay_closed)
            logger.info("🎮 Gaming overlay manager created")
    
    def show_overlay(self):
        """Show the gaming overlay."""
        if self.overlay is None:
            self.create_overlay()
        
        self.overlay.show_overlay()
        self.is_active = True
        logger.info("🎮 Gaming overlay activated")
    
    def hide_overlay(self):
        """Hide the gaming overlay."""
        if self.overlay:
            self.overlay.hide_overlay()
        self.is_active = False
        logger.info("🎮 Gaming overlay deactivated")
    
    def update_gaze(self, x, y, is_blink=False):
        """Update gaze position on overlay."""
        if self.overlay and self.is_active:
            self.overlay.update_gaze_position(x, y, is_blink)
    
    def set_tracking_active(self, is_tracking):
        """Set whether eye tracking is active."""
        if self.overlay:
            self.overlay.set_tracking_status(is_tracking)
    
    def on_overlay_closed(self):
        """Handle overlay being closed by user."""
        self.is_active = False
        logger.info("🎮 Gaming overlay closed by user")
    
    def cleanup(self):
        """Clean up the overlay."""
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.is_active = False
        logger.info("🎮 Gaming overlay cleaned up") 