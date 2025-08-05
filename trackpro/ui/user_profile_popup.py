"""User Profile Popup Dialog

This module provides a popup dialog that displays user profile information
when clicking on users in the online users sidebar. Shows profile picture,
name, username, join date, and provides actions like viewing profile and
sending friend requests.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QMessageBox, QWidget, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QFont, QPen

logger = logging.getLogger(__name__)


class UserProfilePopup(QDialog):
    """Popup dialog for displaying user profile information."""
    
    # Signals
    view_profile_requested = pyqtSignal(str)  # Emits user_id
    friend_request_sent = pyqtSignal(str)  # Emits user_id
    private_message_requested = pyqtSignal(dict)  # Emits user_data
    
    def __init__(self, user_data: Dict[str, Any], current_user_id: str, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.current_user_id = current_user_id
        self.setModal(False)  # Change to non-modal for better click-outside handling
        self.setFixedSize(520, 420)  # Increased width for header image, height to prevent text clipping
        self.click_outside_enabled = False  # Disable click-outside initially
        self.setup_ui()
        self.load_user_data()
        self.update_auth_state()  # Ensure authentication state is properly checked
        
        # Enable click-outside detection after a short delay
        QTimer.singleShot(200, self.enable_click_outside)
    
    def setup_ui(self):
        """Setup the popup UI."""
        self.setWindowTitle("User Profile")
        # Note: Window flags will be set later for click-outside functionality
        
        # Enable click outside to close
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
        # Main container with Discord-like styling
        self.setStyleSheet("""
            QDialog {
                background-color: #252525;
                border-radius: 8px;
                border: 1px solid #202225;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header section (profile picture and basic info)
        self.create_header_section(layout)
        
        # Info section (username, join date, etc.)
        self.create_info_section(layout)
        
        # Actions section (buttons)
        self.create_actions_section(layout)
        
        # Update authentication-dependent UI elements
        self.update_auth_state()
        
        # Set focus policy and window flags for better handling
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        
        # Install global event filter for click-outside detection
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)
    
    def enable_click_outside(self):
        """Enable click-outside detection after popup is fully shown."""
        self.click_outside_enabled = True
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Handle global events to close popup when clicking outside."""
        if event.type() == QEvent.Type.MouseButtonPress and self.click_outside_enabled:
            try:
                # Get global position of the click
                if hasattr(event, 'globalPos'):
                    global_pos = event.globalPos()
                elif hasattr(event, 'globalPosition'):
                    global_pos = event.globalPosition().toPoint()
                else:
                    return False
                
                # Get the widget that was clicked
                widget = QApplication.widgetAt(global_pos)
                
                # Check if the clicked widget is this dialog or a child of it
                if widget is not None:
                    current_widget = widget
                    while current_widget is not None:
                        if current_widget is self:
                            return False  # Click is inside this dialog
                        next_widget = current_widget.parent()
                        if next_widget is None:
                            break
                        current_widget = next_widget
                    
                    # Click is outside - close the dialog
                    self.close()
                    return False
            except Exception as e:
                logger.debug(f"Error in click-outside detection: {e}")
        
        return False
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Remove global event filter when closing
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)
    
    def create_header_section(self, parent_layout):
        """Create the header section with profile picture and name."""
        header = QFrame()
        header.setFixedHeight(120)
        header.setStyleSheet("""
            QFrame {
                background-color: #5865f2;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 8)
        header_layout.setSpacing(8)
        
        # Close button in top-right corner
        close_button = QPushButton("×")
        close_button.setFixedSize(24, 24)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        close_button.clicked.connect(self.close)
        
        # Position close button in top-right
        close_container = QWidget()
        close_container.setStyleSheet("QWidget { background-color: transparent; }")
        close_layout = QHBoxLayout(close_container)
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_layout.addStretch()
        close_layout.addWidget(close_button)
        header_layout.addWidget(close_container)
        
        # Profile picture container
        avatar_container = QWidget()
        avatar_container.setFixedHeight(80)
        avatar_container.setStyleSheet("QWidget { background-color: transparent; }")
        avatar_layout = QHBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Profile picture
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(64, 64)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_layout.addWidget(self.avatar_label)
        
        # Name and status
        name_container = QWidget()
        name_container.setStyleSheet("QWidget { background-color: transparent; }")
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(12, 8, 0, 0)
        name_layout.setSpacing(2)
        
        # Display name
        self.display_name_label = QLabel()
        self.display_name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        name_layout.addWidget(self.display_name_label)
        
        # Online status
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
            }
        """)
        name_layout.addWidget(self.status_label)
        
        name_layout.addStretch()
        avatar_layout.addWidget(name_container, 1)
        
        header_layout.addWidget(avatar_container)
        parent_layout.addWidget(header)
    
    def create_info_section(self, parent_layout):
        """Create the user information section."""
        info_container = QFrame()
        info_container.setMinimumHeight(140)  # Ensure minimum height for text
        info_container.setStyleSheet("""
            QFrame {
                background-color: #252525;
                padding: 16px;
            }
        """)
        
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(16, 16, 16, 16)  # More bottom margin
        info_layout.setSpacing(16)  # More spacing between rows
        
        # Username
        username_container = self.create_info_row("Username", "")
        self.username_value = username_container.findChild(QLabel, "value_label")
        info_layout.addWidget(username_container)
        
        # Member since
        member_since_container = self.create_info_row("Member Since", "")
        self.member_since_value = member_since_container.findChild(QLabel, "value_label")
        info_layout.addWidget(member_since_container)
        
        # Friend status
        friend_status_container = self.create_info_row("Friendship", "")
        self.friend_status_value = friend_status_container.findChild(QLabel, "value_label")
        info_layout.addWidget(friend_status_container)
        
        parent_layout.addWidget(info_container)
    
    def create_info_row(self, label_text: str, value_text: str) -> QWidget:
        """Create a row with label and value."""
        container = QWidget()
        container.setMinimumHeight(32)  # Ensure adequate height for text
        container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 4)  # Add vertical padding
        layout.setSpacing(12)
        
        # Label
        label = QLabel(label_text)
        label.setMinimumHeight(24)  # Ensure label has enough height
        label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
                font-weight: 600;
                min-width: 90px;
                padding: 2px 0px;
            }
        """)
        layout.addWidget(label)
        
        # Value
        value = QLabel(value_text)
        value.setObjectName("value_label")
        value.setMinimumHeight(24)  # Ensure value has enough height
        value.setWordWrap(True)  # Allow text wrapping if needed
        value.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 13px;
                padding: 2px 0px;
            }
        """)
        layout.addWidget(value, 1)
        
        return container
    
    def create_actions_section(self, parent_layout):
        """Create the actions section with buttons."""
        actions_container = QFrame()
        actions_container.setFixedHeight(70)  # Slightly taller for better button spacing
        actions_container.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(16, 12, 16, 16)  # More top margin
        actions_layout.setSpacing(12)  # More spacing between buttons
        
        # View Profile button
        self.view_profile_btn = QPushButton("View Profile")
        self.view_profile_btn.setFixedHeight(36)  # Slightly taller buttons
        self.view_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f545c;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #5d6269;
            }
            QPushButton:pressed {
                background-color: #484d54;
            }
        """)
        self.view_profile_btn.clicked.connect(self.on_view_profile)
        actions_layout.addWidget(self.view_profile_btn)
        
        # Send Friend Request button
        self.friend_request_btn = QPushButton("Send Friend Request")
        self.friend_request_btn.setFixedHeight(36)  # Slightly taller buttons
        self.friend_request_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
            QPushButton:disabled {
                background-color: #4f545c;
                color: #72767d;
            }
        """)
        self.friend_request_btn.clicked.connect(self.on_send_friend_request)
        actions_layout.addWidget(self.friend_request_btn)
        
        # Send Private Message button
        self.private_message_btn = QPushButton("Send Private Message")
        self.private_message_btn.setFixedHeight(36)
        self.private_message_btn.setStyleSheet("""
            QPushButton {
                background-color: #3ba55c;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
                padding: 0px 16px;
            }
            QPushButton:hover {
                background-color: #2d7d46;
            }
            QPushButton:pressed {
                background-color: #1f5f35;
            }
            QPushButton:disabled {
                background-color: #4f545c;
                color: #72767d;
            }
        """)
        self.private_message_btn.clicked.connect(self.on_send_private_message)
        actions_layout.addWidget(self.private_message_btn)
        
        parent_layout.addWidget(actions_container)
    
    def is_user_authenticated(self) -> bool:
        """Check if the current user is authenticated."""
        try:
            from ..auth.user_manager import get_current_user
            user = get_current_user()
            if user is None:
                # User manager not ready yet - return False
                return False
            return user and user.is_authenticated and user.name != "Anonymous User"
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False
    
    def update_auth_state(self):
        """Update UI elements based on authentication state."""
        is_authenticated = self.is_user_authenticated()
        
        # Update friend request button based on authentication
        if hasattr(self, 'friend_request_btn'):
            if not is_authenticated or not self.current_user_id:
                # Not authenticated - always show sign in message
                self.friend_request_btn.setText("Sign in to add friends")
                self.friend_request_btn.setEnabled(False)
                # Reset to disabled style
                self.friend_request_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #72767d;
                        border: none;
                        border-radius: 4px;
                        color: #dcddde;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0px 16px;
                    }
                """)
            else:
                # Authenticated - restore normal button styling first
                self.friend_request_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #5865f2;
                        border: none;
                        border-radius: 4px;
                        color: #ffffff;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0px 16px;
                    }
                    QPushButton:hover {
                        background-color: #4752c4;
                    }
                    QPushButton:pressed {
                        background-color: #3c45a5;
                    }
                    QPushButton:disabled {
                        background-color: #4f545c;
                        color: #72767d;
                    }
                """)
                
                # Then use normal button logic
                is_friend = self.user_data.get('is_friend', False)
                is_self = self.user_data.get('user_id') == self.current_user_id
                
                if is_self:
                    self.friend_request_btn.setText("Edit Profile")
                    self.friend_request_btn.setEnabled(False)
                elif is_friend:
                    self.friend_request_btn.setText("Already Friends")
                    self.friend_request_btn.setEnabled(False)
                else:
                    self.friend_request_btn.setText("Send Friend Request")
                    self.friend_request_btn.setEnabled(True)
        
        # Update private message button based on authentication
        if hasattr(self, 'private_message_btn'):
            if not is_authenticated or not self.current_user_id:
                # Not authenticated - always show sign in message
                self.private_message_btn.setText("Sign in to message")
                self.private_message_btn.setEnabled(False)
                # Reset to disabled style
                self.private_message_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #72767d;
                        border: none;
                        border-radius: 4px;
                        color: #dcddde;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0px 16px;
                    }
                """)
            else:
                # Authenticated - restore normal button styling first
                self.private_message_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3ba55c;
                        border: none;
                        border-radius: 4px;
                        color: #ffffff;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0px 16px;
                    }
                    QPushButton:hover {
                        background-color: #2d7d46;
                    }
                    QPushButton:pressed {
                        background-color: #1f5f35;
                    }
                    QPushButton:disabled {
                        background-color: #4f545c;
                        color: #72767d;
                    }
                """)
                
                # Then use normal button logic
                is_friend = self.user_data.get('is_friend', False)
                is_self = self.user_data.get('user_id') == self.current_user_id
                
                if is_self:
                    self.private_message_btn.setText("Account Settings")
                    self.private_message_btn.setEnabled(False)
                else:
                    self.private_message_btn.setText("Send Private Message")
                    self.private_message_btn.setEnabled(True)
    
    def create_avatar(self, size: int = 64) -> QPixmap:
        """Create a circular avatar with user initials or load from URL."""
        # Check if user has an avatar URL
        avatar_url = self.user_data.get('avatar_url')
        if avatar_url:
            # Load avatar from URL
            return self.load_avatar_from_url(avatar_url, size)
        
        # Fallback to initials if no avatar URL
        # Use real name for current user, fallback to display name or username
        name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'U')
        
        # For current user, try to use first and last name if available
        if self.user_data.get('user_id') == self.current_user_id:
            first_name = self.user_data.get('first_name', '')
            last_name = self.user_data.get('last_name', '')
            if first_name or last_name:
                name = f"{first_name} {last_name}".strip()
        
        # Generate initials from the name
        initials = self._generate_initials(name)
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(size // 3)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        # Draw online status indicator
        is_online = self.user_data.get('is_online', False)
        if is_online:
            status_size = size // 5
            status_x = size - status_size - 2
            status_y = size - status_size - 2
            
            painter.setBrush(QBrush(QColor('#3ba55c')))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(status_x, status_y, status_size, status_size)
        
        painter.end()
        return pixmap
    
    def load_avatar_from_url(self, url: str, size: int = 64) -> QPixmap:
        """Load and display avatar from URL."""
        try:
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt6.QtCore import QUrl
            
            # Create network manager if it doesn't exist
            if not hasattr(self, 'network_manager'):
                self.network_manager = QNetworkAccessManager(self)
            
            # Download image
            request = QNetworkRequest(QUrl(url))
            reply = self.network_manager.get(request)
            
            def on_avatar_downloaded():
                try:
                    if reply.error() == reply.NetworkError.NoError:
                        image_data = reply.readAll()
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        
                        # Scale and crop to circle
                        if not pixmap.isNull():
                            # Scale to fit avatar size
                            scaled_pixmap = pixmap.scaled(
                                size, size, 
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation
                            )
                            
                            # Create circular mask
                            circular_pixmap = QPixmap(size, size)
                            circular_pixmap.fill(Qt.GlobalColor.transparent)
                            
                            painter = QPainter(circular_pixmap)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                            painter.setBrush(QBrush(scaled_pixmap))
                            painter.setPen(QPen(Qt.GlobalColor.transparent))
                            painter.drawEllipse(0, 0, size, size)
                            
                            # Draw online status indicator if needed
                            is_online = self.user_data.get('is_online', False)
                            if is_online:
                                status_size = size // 5
                                status_x = size - status_size - 2
                                status_y = size - status_size - 2
                                
                                painter.setBrush(QBrush(QColor('#3ba55c')))
                                painter.setPen(Qt.PenStyle.NoPen)
                                painter.drawEllipse(status_x, status_y, status_size, status_size)
                            
                            painter.end()
                            
                            # Update avatar display
                            self.avatar_label.setPixmap(circular_pixmap)
                    
                    reply.deleteLater()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    fallback_pixmap = self.create_fallback_avatar(size)
                    self.avatar_label.setPixmap(fallback_pixmap)
            
            reply.finished.connect(on_avatar_downloaded)
            
            # Return a placeholder pixmap while loading
            placeholder = QPixmap(size, size)
            placeholder.fill(Qt.GlobalColor.transparent)
            return placeholder
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading avatar from URL: {e}")
            # Fallback to initials
            return self.create_fallback_avatar(size)
    
    def create_fallback_avatar(self, size: int = 64) -> QPixmap:
        """Create a fallback avatar with initials when image loading fails."""
        # Use real name for current user, fallback to display name or username
        name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'U')
        
        # For current user, try to use first and last name if available
        if self.user_data.get('user_id') == self.current_user_id:
            first_name = self.user_data.get('first_name', '')
            last_name = self.user_data.get('last_name', '')
            if first_name or last_name:
                name = f"{first_name} {last_name}".strip()
        
        # Generate initials from the name
        initials = self._generate_initials(name)
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(size // 3)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        # Draw online status indicator
        is_online = self.user_data.get('is_online', False)
        if is_online:
            status_size = size // 5
            status_x = size - status_size - 2
            status_y = size - status_size - 2
            
            painter.setBrush(QBrush(QColor('#3ba55c')))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(status_x, status_y, status_size, status_size)
        
        painter.end()
        return pixmap
    
    def load_user_data(self):
        """Load and display user data."""
        # Check if this is the current user and fetch real data
        is_current_user = self.user_data.get('user_id') == self.current_user_id
        
        if is_current_user and self.current_user_id:
            # Fetch real user data from database for current user
            real_user_data = self.get_current_user_data()
            if real_user_data:
                self.user_data.update(real_user_data)
        
        # Set avatar
        avatar_pixmap = self.create_avatar(64)
        self.avatar_label.setPixmap(avatar_pixmap)
        self.avatar_label.setStyleSheet("border-radius: 32px;")
        
        # Set display name
        display_name = self.user_data.get('display_name') or self.user_data.get('username', 'Unknown User')
        self.display_name_label.setText(display_name)
        
        # Set status
        status = self.user_data.get('status', 'Offline')
        is_online = self.user_data.get('is_online', False)
        status_text = f"🟢 {status}" if is_online else f"⚫ {status}"
        self.status_label.setText(status_text)
        
        # Set username
        username = self.user_data.get('username', 'Unknown')
        self.username_value.setText(f"@{username}")
        
        # Set member since
        member_since = self.format_join_date()
        self.member_since_value.setText(member_since)
        
        # Set friendship status (only show if authenticated)
        if self.current_user_id:
            is_friend = self.user_data.get('is_friend', False)
            friend_status = "Friends" if is_friend else "Not friends"
            self.friend_status_value.setText(friend_status)
        else:
            # Not authenticated - don't show friendship status
            self.friend_status_value.setText("Sign in to see friendship status")
        
        # Update button states
        self.update_button_states()
    
    def get_current_user_data(self) -> Optional[Dict[str, Any]]:
        """Get current user's real data from database."""
        try:
            # Try to get complete user profile first (includes avatar_url)
            try:
                from ....social import enhanced_user_manager
                complete_profile = enhanced_user_manager.get_complete_user_profile()
                if complete_profile:
                    # Generate display name from real data
                    display_name = self._generate_display_name(complete_profile)
                    
                    # Get current iRacing status if available
                    iracing_status = self.get_current_user_iracing_status()
                    
                    return {
                        'user_id': complete_profile.get('user_id'),
                        'username': complete_profile.get('username', 'currentuser'),
                        'display_name': display_name,
                        'email': complete_profile.get('email'),
                        'first_name': complete_profile.get('first_name', ''),
                        'last_name': complete_profile.get('last_name', ''),
                        'bio': complete_profile.get('bio'),
                        'created_at': complete_profile.get('created_at'),
                        'avatar_url': complete_profile.get('avatar_url'),  # Include avatar URL
                        'status': iracing_status or 'Online',
                        'is_online': True,  # Current user is always online
                        'is_friend': False  # Can't be friends with yourself
                    }
            except Exception as profile_error:
                logger.debug(f"Could not get complete user profile: {profile_error}")
            
            # Fallback to basic database query
            from ..database.supabase_client import get_supabase_client
            client = get_supabase_client()
            
            if not client or not self.current_user_id:
                return None
            
            # Fetch user profile from database - handle missing columns gracefully
            try:
                # Try to fetch with all fields first
                response = client.table("user_profiles").select(
                    "user_id, username, display_name, email, first_name, last_name, bio, created_at, avatar_url"
                ).eq("user_id", self.current_user_id).single().execute()
            except Exception as column_error:
                # If some columns don't exist, try without them
                logger.warning(f"Some columns may not exist, trying fallback query: {column_error}")
                response = client.table("user_profiles").select(
                    "user_id, username, display_name, email, bio, created_at"
                ).eq("user_id", self.current_user_id).single().execute()
            
            if response.data:
                user_data = response.data
                
                # Generate display name from real data
                display_name = self._generate_display_name(user_data)
                
                # Get current iRacing status if available
                iracing_status = self.get_current_user_iracing_status()
                
                return {
                    'user_id': user_data['user_id'],
                    'username': user_data.get('username', 'currentuser'),
                    'display_name': display_name,
                    'email': user_data.get('email'),
                    'first_name': user_data.get('first_name', ''),  # Safe fallback
                    'last_name': user_data.get('last_name', ''),    # Safe fallback
                    'bio': user_data.get('bio'),
                    'created_at': user_data.get('created_at'),
                    'avatar_url': user_data.get('avatar_url'),  # Include avatar URL
                    'status': iracing_status or 'Online',
                    'is_online': True,  # Current user is always online
                    'is_friend': False  # Can't be friends with yourself
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current user data: {e}")
            return None
    
    def _generate_display_name(self, user_data: Dict[str, Any]) -> str:
        """Generate display name from user data."""
        # Try first_name + last_name first
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        if first_name or last_name:
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                return full_name
        
        # Fallback to display_name
        display_name = user_data.get('display_name', '')
        if display_name:
            return display_name
        
        # Fallback to username
        username = user_data.get('username', '')
        if username:
            return username
        
        # Final fallback
        return 'User'
    
    def _generate_initials(self, name: str) -> str:
        """Generate initials from a name."""
        if not name or name.strip() == '':
            return 'U'
        
        # Split name and get first letter of each word
        words = name.strip().split()
        if not words:
            return 'U'
        
        # Get first letter of first word
        first_initial = words[0][0].upper() if words[0] else 'U'
        
        # Get first letter of last word if different from first word
        if len(words) > 1 and words[-1] != words[0]:
            last_initial = words[-1][0].upper() if words[-1] else ''
            return f"{first_initial}{last_initial}"
        else:
            return first_initial
    
    def get_current_user_iracing_status(self) -> str:
        """Get the current user's iRacing status from telemetry."""
        try:
            # Try to get global iRacing API
            global_iracing_api = None
            
            # Look for global iRacing API in different ways
            try:
                from PyQt6.QtWidgets import QApplication
                for widget in QApplication.topLevelWidgets():
                    if hasattr(widget, 'get_shared_iracing_api'):
                        global_iracing_api = widget.get_shared_iracing_api()
                        break
                    elif hasattr(widget, 'global_iracing_api'):
                        global_iracing_api = widget.global_iracing_api
                        break
            except:
                pass
            
            # Alternative: try to import and get global API
            if not global_iracing_api:
                try:
                    import new_ui
                    if hasattr(new_ui, 'get_global_iracing_api'):
                        global_iracing_api = new_ui.get_global_iracing_api()
                except:
                    pass
            
            if global_iracing_api and hasattr(global_iracing_api, 'ir') and global_iracing_api.ir:
                ir = global_iracing_api.ir
                if ir and ir.is_connected:
                    # Get current session info
                    try:
                        weekend_info = ir['WeekendInfo']
                        driver_info = ir['DriverInfo']
                        session_info = ir['SessionInfo']
                        
                        track_name = weekend_info.get('TrackDisplayName', 'Unknown Track')
                        
                        # Get car name from player's driver info
                        drivers = driver_info.get('Drivers', [])
                        player_car_idx = driver_info.get('DriverCarIdx', 0)
                        car_name = 'Unknown Car'
                        
                        if 0 <= player_car_idx < len(drivers):
                            car_name = drivers[player_car_idx].get('CarScreenName', 'Unknown Car')
                        
                        # Get session type
                        sessions = session_info.get('Sessions', [])
                        current_session_num = session_info.get('CurrentSessionNum', 0)
                        session_type = 'Practice'
                        
                        if 0 <= current_session_num < len(sessions):
                            session_type = sessions[current_session_num].get('SessionType', 'Practice')
                        
                        # Format the status based on session type
                        if session_type == 'Race':
                            return f"Racing - {track_name}"
                        elif session_type == 'Practice':
                            return f"Practicing - {track_name}"
                        elif session_type == 'Qualify':
                            return f"Qualifying - {track_name}"
                        elif session_type == 'Warmup':
                            return f"Warming up - {track_name}"
                        else:
                            return f"In session - {track_name}"
                            
                    except Exception as e:
                        logger.debug(f"Error getting detailed iRacing session info: {e}")
                        return "In iRacing"
                else:
                    # Not connected to iRacing but TrackPro is running
                    return "Online"
            else:
                # No iRacing API available
                return "Online"
                
        except Exception as e:
            logger.debug(f"Error getting iRacing status: {e}")
            return "Online"
    
    def format_join_date(self) -> str:
        """Format the join date for display."""
        join_date = self.user_data.get('created_at')
        if join_date:
            try:
                # Parse ISO format date
                dt = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
                return dt.strftime("%B %d, %Y")
            except:
                pass
        
        # Fallback to mock date if no real data available
        return "January 15, 2024"
    
    def update_button_states(self):
        """Update button states based on user relationship."""
        # Check authentication first - if not authenticated, don't set relationship-based states
        if not self.current_user_id:
            # Not authenticated - will be handled by update_auth_state()
            return
            
        is_friend = self.user_data.get('is_friend', False)
        is_self = self.user_data.get('user_id') == self.current_user_id
        
        if is_self:
            # For own profile, show more useful actions
            self.friend_request_btn.setEnabled(False)
            self.friend_request_btn.setText("Edit Profile")
            self.friend_request_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4f545c;
                    border: none;
                    border-radius: 4px;
                    color: #72767d;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0px 16px;
                }
            """)
            # Can't send private message to yourself
            self.private_message_btn.setEnabled(False)
            self.private_message_btn.setText("Account Settings")
            self.private_message_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4f545c;
                    border: none;
                    border-radius: 4px;
                    color: #72767d;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0px 16px;
                }
            """)
        elif is_friend:
            # Already friends
            self.friend_request_btn.setEnabled(False)
            self.friend_request_btn.setText("Already Friends")
            # Can send private message to friends
            self.private_message_btn.setEnabled(True)
            self.private_message_btn.setText("Send Private Message")
        else:
            # Can send friend request
            self.friend_request_btn.setEnabled(True)
            self.friend_request_btn.setText("Send Friend Request")
            # Can send private message to any user
            self.private_message_btn.setEnabled(True)
            self.private_message_btn.setText("Send Private Message")
    
    def on_view_profile(self):
        """Handle view profile button click."""
        user_id = self.user_data.get('user_id')
        if user_id:
            logger.info(f"Viewing profile for user: {user_id}")
            self.view_profile_requested.emit(user_id)
        self.accept()
    
    def on_send_friend_request(self):
        """Handle send friend request button click."""
        if not self.friend_request_btn.isEnabled():
            return
        
        # Check authentication first
        if not self.is_user_authenticated():
            QMessageBox.warning(self, "Authentication Required", 
                              "You must be signed in to send friend requests.\n\n"
                              "Please sign in to your account first.")
            return
        
        user_id = self.user_data.get('user_id')
        username = self.user_data.get('username', 'Unknown')
        
        if not user_id:
            QMessageBox.warning(self, "Error", "User ID not found.")
            return
        
        try:
            # Import the friends manager
            from trackpro.social.friends_manager import FriendsManager
            
            friends_manager = FriendsManager()
            result = friends_manager.send_friend_request(self.current_user_id, user_id)
            
            if result.get('success', False):
                display_name = self.user_data.get('display_name') or username
                QMessageBox.information(self, "Success", f"Friend request sent to {display_name}!")
                
                # Update button state
                self.friend_request_btn.setEnabled(False)
                self.friend_request_btn.setText("Request Sent")
                
                # Emit signal
                self.friend_request_sent.emit(user_id)
            else:
                error_message = result.get('message', 'Failed to send friend request.')
                
                # Show specific popup for already sent friend request
                if error_message == "Friend request already sent":
                    QMessageBox.information(self, "Friend Request", "You've already sent this user a request!")
                else:
                    QMessageBox.warning(self, "Error", error_message)
                
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while sending the friend request.")
    
    def on_send_private_message(self):
        """Handle send private message button click."""
        if not self.is_user_authenticated():
            QMessageBox.information(self, "Authentication Required", 
                                  "Please sign in to send private messages.")
            return
        
        if not self.current_user_id:
            QMessageBox.information(self, "Authentication Required", 
                                  "Please sign in to send private messages.")
            return
        
        # Try to find a widget with start_direct_private_message method
        # Start from current widget and traverse up the parent hierarchy
        current_widget = self
        while current_widget is not None:
            if hasattr(current_widget, 'start_direct_private_message'):
                current_widget.start_direct_private_message(self.user_data)
                self.close()
                return
            
            # Get the parent widget safely
            try:
                current_widget = current_widget.parent()
            except Exception as e:
                logger.error(f"Error traversing parent hierarchy: {e}")
                break
        
        # If we can't find the method in parent hierarchy, try to find the main window
        # and look for the community page
        try:
            # Find the main window
            main_window = self.window()
            if main_window and hasattr(main_window, 'content_stack'):
                # Look for CommunityPage in the content stack
                for i in range(main_window.content_stack.count()):
                    widget = main_window.content_stack.widget(i)
                    if hasattr(widget, 'start_direct_private_message'):
                        widget.start_direct_private_message(self.user_data)
                        self.close()
                        return
        except Exception as e:
            logger.error(f"Error finding main window or community page: {e}")
        
        # Fallback to emitting signal if direct method not found
        self.private_message_requested.emit(self.user_data)
        self.close()
    
    def mousePressEvent(self, event):
        """Handle mouse press to close popup when clicking outside."""
        # Close the dialog when clicking outside the main content
        if event.button() == Qt.MouseButton.LeftButton:
            self.accept()
        super().mousePressEvent(event)