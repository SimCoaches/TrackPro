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
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QFont

logger = logging.getLogger(__name__)


class UserProfilePopup(QDialog):
    """Popup dialog for displaying user profile information."""
    
    # Signals
    view_profile_requested = pyqtSignal(str)  # Emits user_id
    friend_request_sent = pyqtSignal(str)  # Emits user_id
    
    def __init__(self, user_data: Dict[str, Any], current_user_id: str, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.current_user_id = current_user_id
        self.setModal(False)  # Change to non-modal for better click-outside handling
        self.setFixedSize(320, 420)  # Increased height to prevent text clipping
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
                    while current_widget:
                        if current_widget is self:
                            return False  # Click is inside this dialog
                        current_widget = current_widget.parent()
                    
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
        
        parent_layout.addWidget(actions_container)
    
    def is_user_authenticated(self) -> bool:
        """Check if the current user is authenticated."""
        try:
            from ..auth.user_manager import get_current_user
            user = get_current_user()
            return user and user.is_authenticated and user.name != "Anonymous User"
        except Exception as e:
            logger.warning(f"Failed to check authentication status: {e}")
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
                    self.friend_request_btn.setText("That's You!")
                    self.friend_request_btn.setEnabled(False)
                elif is_friend:
                    self.friend_request_btn.setText("Already Friends")
                    self.friend_request_btn.setEnabled(False)
                else:
                    self.friend_request_btn.setText("Send Friend Request")
                    self.friend_request_btn.setEnabled(True)
    
    def create_avatar(self, size: int = 64) -> QPixmap:
        """Create a circular avatar with user initials."""
        name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'U')
        initials = ''.join([word[0].upper() for word in name.split()][:2])
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background
        colors = ['#7289da', '#99aab5', '#2c2f33', '#23272a', '#f04747', '#faa61a']
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
        
        # Set member since (mock data for now)
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
    
    def format_join_date(self) -> str:
        """Format the join date for display."""
        # For now, use mock data. In real implementation, this would come from user_data
        # or be fetched from the database
        join_date = self.user_data.get('created_at')
        if join_date:
            try:
                # Parse ISO format date
                dt = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
                return dt.strftime("%B %d, %Y")
            except:
                pass
        
        # Fallback to mock date
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
            # Can't send friend request to yourself
            self.friend_request_btn.setEnabled(False)
            self.friend_request_btn.setText("That's You!")
        elif is_friend:
            # Already friends
            self.friend_request_btn.setEnabled(False)
            self.friend_request_btn.setText("Already Friends")
        else:
            # Can send friend request
            self.friend_request_btn.setEnabled(True)
            self.friend_request_btn.setText("Send Friend Request")
    
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
            from ..social.friends_manager import FriendsManager
            
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
                QMessageBox.warning(self, "Error", error_message)
                
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while sending the friend request.")
    
    def mousePressEvent(self, event):
        """Handle mouse press to close popup when clicking outside."""
        # Close the dialog when clicking outside the main content
        if event.button() == Qt.MouseButton.LeftButton:
            self.accept()
        super().mousePressEvent(event)