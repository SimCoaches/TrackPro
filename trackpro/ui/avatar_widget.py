"""
Reusable Avatar Widget for TrackPro

This module provides a standardized avatar widget that uses the centralized
avatar management system. It can be used across the entire application
for consistent avatar display.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QMetaObject, QThread, QApplication
from PyQt6.QtGui import QPixmap

from .avatar_manager import get_avatar_manager, AvatarSize

logger = logging.getLogger(__name__)

class AvatarWidget(QLabel):
    """
    Reusable avatar widget that uses the centralized avatar manager.
    
    Features:
    - Automatic loading and caching
    - Fallback to initials
    - Standardized sizes
    - Error handling
    - Click events
    """
    
    # Signals
    avatar_clicked = pyqtSignal()  # Emitted when avatar is clicked
    avatar_loaded = pyqtSignal(QPixmap)  # Emitted when avatar is successfully loaded
    avatar_load_failed = pyqtSignal(str)  # Emitted when avatar load fails
    
    def __init__(self, size: AvatarSize = AvatarSize.MEDIUM, parent=None):
        super().__init__(parent)
        
        self.size = size
        self.avatar_url = None
        self.user_name = "User"
        self.clickable = False
        
        # Set up the widget
        self.setFixedSize(size.value, size.value)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border-radius: 50%;")
        
        # Show initial fallback
        self._show_fallback()
    
    def set_avatar(self, url: str, user_name: str = "User"):
        """
        Set the avatar URL and user name.
        
        Args:
            url: Avatar URL (can be None for fallback)
            user_name: User name for fallback initials
        """
        self.avatar_url = url
        self.user_name = user_name
        
        # Get avatar from centralized manager
        avatar_manager = get_avatar_manager()
        avatar_manager.get_avatar(
            url=url,
            size=self.size,
            callback=self._on_avatar_loaded,
            user_name=user_name
        )
    
    def set_clickable(self, clickable: bool = True):
        """Enable or disable click events."""
        self.clickable = clickable
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _on_avatar_loaded(self, pixmap: QPixmap):
        """Handle avatar loaded callback with thread safety."""
        try:
            # Ensure we're on the main thread for UI updates
            if QThread.currentThread() == QApplication.instance().thread():
                # We're on the main thread, update directly
                self.setPixmap(pixmap)
                self.avatar_loaded.emit(pixmap)
                logger.debug(f"Avatar loaded for {self.user_name}")
            else:
                # We're on a background thread, invoke on main thread
                QMetaObject.invokeMethod(
                    self,
                    lambda: self._update_avatar_safe(pixmap),
                    Qt.ConnectionType.QueuedConnection
                )
        except Exception as e:
            logger.error(f"Error setting avatar pixmap: {e}")
            self._show_fallback()
    
    def _update_avatar_safe(self, pixmap: QPixmap):
        """Safely update avatar on the main thread."""
        try:
            self.setPixmap(pixmap)
            self.avatar_loaded.emit(pixmap)
            logger.debug(f"Avatar loaded for {self.user_name}")
        except Exception as e:
            logger.error(f"Error updating avatar safely: {e}")
            self._show_fallback()
    
    def _show_fallback(self):
        """Show fallback avatar with initials."""
        try:
            # Create fallback using avatar manager
            avatar_manager = get_avatar_manager()
            fallback = avatar_manager._create_fallback_avatar(self.user_name, self.size.value)
            self.setPixmap(fallback)
        except Exception as e:
            logger.error(f"Error creating fallback avatar: {e}")
            # Create simple fallback
            pixmap = QPixmap(self.size.value, self.size.value)
            pixmap.fill(Qt.GlobalColor.transparent)
            self.setPixmap(pixmap)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.avatar_clicked.emit()
        super().mousePressEvent(event)
    
    def set_user_info(self, user_data: dict):
        """
        Set avatar from user data dictionary.
        
        Args:
            user_data: Dictionary containing 'avatar_url' and name fields
        """
        avatar_url = user_data.get('avatar_url')
        
        # Determine user name from various fields
        user_name = (
            user_data.get('display_name') or 
            user_data.get('username') or 
            user_data.get('name') or
            user_data.get('first_name', '') + ' ' + user_data.get('last_name', '') or
            'User'
        ).strip()
        
        self.set_avatar(avatar_url, user_name)

class AvatarButton(AvatarWidget):
    """
    Clickable avatar button widget.
    
    This is a convenience class that creates an avatar widget
    that's clickable by default.
    """
    
    def __init__(self, size: AvatarSize = AvatarSize.MEDIUM, parent=None):
        super().__init__(size, parent)
        self.set_clickable(True)
