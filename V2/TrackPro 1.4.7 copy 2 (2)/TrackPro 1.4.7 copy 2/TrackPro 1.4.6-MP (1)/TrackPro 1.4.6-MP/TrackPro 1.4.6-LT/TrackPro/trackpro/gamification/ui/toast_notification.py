"""toast_notification.py
A lightweight toast notification widget for TrackPro.
Displays a message (and optional icon) that fades in, stays for a short
period, then fades out. Intended for quick reward feedback.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPalette, QTransform
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect


class ToastNotification(QWidget):
    _MARGIN = 20
    _PADDING = 10
    _MAX_WIDTH = 300
    _DEFAULT_ICON_SIZE = 24  # Default icon size in pixels

    def __init__(self, parent: QWidget, message: str, icon_path: Optional[str] = None, duration_ms: int = 3000, icon_type: str = 'default'):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Ensure toast is on top of regular widgets but not truly a separate window
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self._duration_ms = duration_ms
        self._icon_label = None  # Store icon label reference for animations
        self._icon_type = icon_type  # Store icon type for animation selection

        # Build layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(self._PADDING, self._PADDING, self._PADDING, self._PADDING)
        layout.setSpacing(8)

        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self._icon_label = QLabel()
                self._icon_label.setPixmap(pixmap.scaled(self._DEFAULT_ICON_SIZE, self._DEFAULT_ICON_SIZE, 
                                                  Qt.KeepAspectRatio, Qt.SmoothTransformation))
                # Use fixed size to prevent layout changes during animation
                self._icon_label.setFixedSize(self._DEFAULT_ICON_SIZE, self._DEFAULT_ICON_SIZE)
                # Enable transform for rotation animation if needed
                self._icon_label.setAttribute(Qt.WA_TranslucentBackground)
                layout.addWidget(self._icon_label)

        text_label = QLabel(message)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("color: white; font-size: 10pt;")
        layout.addWidget(text_label)

        # Style the toast background via stylesheet
        self.setStyleSheet(
            "background-color: rgba(60, 60, 60, 220);"
            "border-radius: 6px;"
        )

        # Opacity effect for fade in/out
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)

        # Position toast (top-right of parent)
        self.adjustSize()
        self._position_to_parent()

        # Start animations
        self._fade_in_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_in_anim.setDuration(300)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._fade_in_anim.finished.connect(self._start_icon_animation)  # Start icon animation after fade-in
        self._fade_in_anim.start()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @classmethod
    def show_notification(
        cls,
        parent: QWidget,
        message: str,
        icon_path: Optional[str] = None,
        duration_ms: int = 3000,
        icon_type: str = 'default',
    ) -> "ToastNotification":
        """Convenience wrapper to create, show, and manage a toast."""
        # Determine icon type from path if not specified
        if icon_type == 'default' and icon_path:
            if 'xp_icon' in icon_path:
                icon_type = 'xp'
            elif 'rp_xp_icon' in icon_path:
                icon_type = 'rp_xp'

        toast = cls(parent, message, icon_path, duration_ms, icon_type)
        toast.show()
        return toast

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _position_to_parent(self):
        parent_geom = self.parent().rect()
        x = parent_geom.right() - self.width() - self._MARGIN
        y = parent_geom.top() + self._MARGIN
        self.move(x, y)

    def _start_icon_animation(self):
        """Start the appropriate icon animation based on type, then start stay timer."""
        if self._icon_label:
            if self._icon_type == 'xp':
                self._start_rotation_animation()
            elif self._icon_type == 'rp_xp':
                self._start_pulse_animation()
            # Default case: no animation

        # Continue with normal stay timer
        self._start_stay_timer()

    def _start_rotation_animation(self):
        """XP icon rotates 360 degrees."""
        # Create property animation
        self._rotation_anim = QPropertyAnimation(self._icon_label, b"geometry")
        self._rotation_anim.setDuration(2000)  # 2 seconds for full rotation
        
        # Get current geometry
        current_geo = self._icon_label.geometry()
        
        # Set keyframes (we'll use same geometry but add transformation inside)
        self._rotation_anim.setStartValue(current_geo)
        self._rotation_anim.setEndValue(current_geo)
        
        # Custom animation steps
        def update_rotation(step):
            angle = step * 360.0 / 100.0  # 0 to 360 degrees
            pixmap = self._icon_label.pixmap()
            if pixmap:
                # Create transform
                transform = QTransform()
                transform.translate(pixmap.width()/2, pixmap.height()/2)
                transform.rotate(angle)
                transform.translate(-pixmap.width()/2, -pixmap.height()/2)
                
                # Apply transform to pixmap
                rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                
                # Crop to original size (centered)
                center_x = rotated_pixmap.width() / 2
                center_y = rotated_pixmap.height() / 2
                crop_x = center_x - pixmap.width() / 2
                crop_y = center_y - pixmap.height() / 2
                cropped = rotated_pixmap.copy(
                    int(crop_x), int(crop_y), 
                    pixmap.width(), pixmap.height()
                )
                
                # Set the pixmap
                self._icon_label.setPixmap(cropped)
        
        # Connect to value changed signal
        self._rotation_anim.valueChanged.connect(update_rotation)
        
        # Start the animation
        self._rotation_anim.start()

    def _start_pulse_animation(self):
        """RP_XP icon pulses (scales up/down)."""
        self._pulse_anim = QPropertyAnimation(self._icon_label, b"geometry")
        self._pulse_anim.setDuration(1500)  # 1.5 seconds
        
        # Get original size and position
        original_geo = self._icon_label.geometry()
        x = original_geo.x()
        y = original_geo.y()
        width = original_geo.width()
        height = original_geo.height()
        
        # Calculate expanded size (25% larger)
        expand_factor = 1.25
        expanded_width = int(width * expand_factor)
        expanded_height = int(height * expand_factor)
        
        # Calculate offsets to keep centered
        x_offset = (expanded_width - width) // 2
        y_offset = (expanded_height - height) // 2
        
        # Set keyframes
        self._pulse_anim.setKeyValueAt(0.0, original_geo)
        self._pulse_anim.setKeyValueAt(0.5, original_geo.adjusted(-x_offset, -y_offset, x_offset, y_offset))
        self._pulse_anim.setKeyValueAt(1.0, original_geo)
        
        # Use ease in/out for smooth animation
        self._pulse_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Start the animation
        self._pulse_anim.start()

    def _start_stay_timer(self):
        QTimer.singleShot(self._duration_ms, self._fade_out)

    def _fade_out(self):
        fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        fade_out_anim.setDuration(400)
        fade_out_anim.setStartValue(1.0)
        fade_out_anim.setEndValue(0.0)
        fade_out_anim.setEasingCurve(QEasingCurve.InQuad)
        fade_out_anim.finished.connect(self.deleteLater)
        fade_out_anim.start() 