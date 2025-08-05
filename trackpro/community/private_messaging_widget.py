"""Private messaging widget for community system."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame, 
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush

logger = logging.getLogger(__name__)

class PrivateMessageWidget(QWidget):
    """Individual private message widget."""
    
    def __init__(self, message_data, is_own_message=False):
        super().__init__()
        self.message_data = message_data
        self.is_own_message = is_own_message
        self.setup_ui()
    
    def create_avatar(self, user_name, user_data=None):
        """Create a circular avatar with user profile picture or initials."""
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Check if user has an avatar URL
        avatar_url = None
        if user_data:
            avatar_url = user_data.get('avatar_url')
        
        # Load avatar from URL if available
        if avatar_url:
            return self.load_avatar_from_url(avatar_url, size)
        
        # Fallback to initials
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in user_name.split()][:2])
        
        # Create pixmap for avatar
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(user_name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        return pixmap
    
    def load_avatar_from_url(self, url: str, size: int = 32) -> QPixmap:
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
                            painter.end()
                            
                            # Update avatar display if this widget is still valid
                            if hasattr(self, 'avatar_label') and self.avatar_label:
                                self.avatar_label.setPixmap(circular_pixmap)
                    
                    reply.deleteLater()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    fallback_pixmap = self.create_fallback_avatar(size, user_name)
                    if hasattr(self, 'avatar_label') and self.avatar_label:
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
            return self.create_fallback_avatar(size, user_name)
    
    def create_fallback_avatar(self, size: int = 32, user_name: str = 'U') -> QPixmap:
        """Create a fallback avatar with initials when image loading fails."""
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in user_name.split()][:2])
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(user_name) % len(colors)
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
        
        painter.end()
        return pixmap
    
    def setup_ui(self):
        """Setup the message UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        if self.is_own_message:
            # Own message: content on right, avatar on right
            layout.addStretch()
            
            # Message content
            content_layout = QVBoxLayout()
            content_layout.setSpacing(2)
            
            # Message text
            message_label = QLabel(self.message_data.get('content', ''))
            message_label.setWordWrap(True)
            message_label.setStyleSheet("""
                color: #ffffff; 
                font-size: 13px; 
                line-height: 1.4;
                background-color: #3498db;
                border-radius: 8px;
                padding: 8px 12px;
            """)
            content_layout.addWidget(message_label)
            
            # Timestamp
            timestamp = self.message_data.get('created_at', '')
            if timestamp:
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%H:%M')
                time_label = QLabel(time_str)
                time_label.setStyleSheet("color: #888888; font-size: 11px; text-align: right;")
                time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                content_layout.addWidget(time_label)
            
            layout.addLayout(content_layout)
            
            # User avatar
            user_profiles = self.message_data.get('user_profiles', {})
            user_name = user_profiles.get('display_name') or user_profiles.get('username') or 'You'
            self.avatar_label = QLabel()
            self.avatar_label.setFixedSize(32, 32)
            self.avatar_label.setPixmap(self.create_avatar(user_name, user_profiles))
            layout.addWidget(self.avatar_label)
            
        else:
            # Other's message: avatar on left, content on left
            # User avatar
            user_profiles = self.message_data.get('user_profiles', {})
            user_name = user_profiles.get('display_name') or user_profiles.get('username') or 'User'
            self.avatar_label = QLabel()
            self.avatar_label.setFixedSize(32, 32)
            self.avatar_label.setPixmap(self.create_avatar(user_name, user_profiles))
            layout.addWidget(self.avatar_label)
            
            # Message content
            content_layout = QVBoxLayout()
            content_layout.setSpacing(2)
            
            # Username
            username_label = QLabel(user_name)
            username_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 12px;")
            content_layout.addWidget(username_label)
            
            # Message text
            message_label = QLabel(self.message_data.get('content', ''))
            message_label.setWordWrap(True)
            message_label.setStyleSheet("""
                color: #ffffff; 
                font-size: 13px; 
                line-height: 1.4;
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 8px 12px;
            """)
            content_layout.addWidget(message_label)
            
            # Timestamp
            timestamp = self.message_data.get('created_at', '')
            if timestamp:
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%H:%M')
                time_label = QLabel(time_str)
                time_label.setStyleSheet("color: #888888; font-size: 11px;")
                content_layout.addWidget(time_label)
            
            layout.addLayout(content_layout, 1)
            layout.addStretch()
        
        # Set background
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)


class PrivateConversationWidget(QWidget):
    """Widget for displaying a private conversation."""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self, conversation_data):
        super().__init__()
        self.conversation_data = conversation_data
        self.conversation_id = conversation_data.get('conversation_id')
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the conversation UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Conversation header
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-bottom: 1px solid #2d2d2d;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 16)
        
        # Other user info
        other_user = self.conversation_data.get('other_user', {})
        user_name = other_user.get('display_name') or other_user.get('username') or 'Unknown User'
        
        # User avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(32, 32)
        self.avatar_label.setPixmap(self.create_user_avatar(user_name, other_user))
        header_layout.addWidget(self.avatar_label)
        
        # User name
        name_label = QLabel(user_name)
        name_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
        # Messages area
        self.messages_list = QListWidget()
        self.messages_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
            }
        """)
        layout.addWidget(self.messages_list)
        
        # Message input area
        input_widget = QWidget()
        input_widget.setFixedHeight(80)
        input_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-top: 1px solid #2d2d2d;
            }
        """)
        
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(16, 16, 16, 16)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setFixedHeight(40)
        self.message_input.setPlaceholderText(f"Message {user_name}")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #2d2d2d;
                border-radius: 4px;
                color: #ffffff;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        
        layout.addWidget(input_widget)
    
    def create_user_avatar(self, user_name, user_data=None):
        """Create a circular avatar with user profile picture or initials."""
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Check if user has an avatar URL
        avatar_url = None
        if user_data:
            avatar_url = user_data.get('avatar_url')
        
        # Load avatar from URL if available
        if avatar_url:
            return self.load_avatar_from_url(avatar_url, size)
        
        # Fallback to initials
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in user_name.split()][:2])
        
        # Create pixmap for avatar
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(user_name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        return pixmap
    
    def load_avatar_from_url(self, url: str, size: int = 32) -> QPixmap:
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
                            painter.end()
                            
                            # Update avatar display if this widget is still valid
                            if hasattr(self, 'avatar_label') and self.avatar_label:
                                self.avatar_label.setPixmap(circular_pixmap)
                    
                    reply.deleteLater()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    fallback_pixmap = self.create_fallback_avatar(size, user_name)
                    if hasattr(self, 'avatar_label') and self.avatar_label:
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
            return self.create_fallback_avatar(size, user_name)
    
    def create_fallback_avatar(self, size: int = 32, user_name: str = 'U') -> QPixmap:
        """Create a fallback avatar with initials when image loading fails."""
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in user_name.split()][:2])
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(user_name) % len(colors)
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
        
        painter.end()
        return pixmap
    
    def send_message(self):
        """Send a message."""
        text = self.message_input.text().strip()
        if text:
            self.message_sent.emit(text)
            self.message_input.clear()
    
    def add_message(self, message_data, is_own_message=False):
        """Add a message to the conversation."""
        try:
            message_widget = PrivateMessageWidget(message_data, is_own_message)
            item = QListWidgetItem()
            item.setSizeHint(message_widget.sizeHint())
            
            self.messages_list.addItem(item)
            self.messages_list.setItemWidget(item, message_widget)
            
            # Scroll to bottom
            self.messages_list.scrollToBottom()
        except Exception as e:
            logger.error(f"Error adding message to conversation: {e}")


class PrivateConversationListItem(QWidget):
    """List item widget for private conversations."""
    
    conversation_selected = pyqtSignal(str)  # conversation_id
    
    def __init__(self, conversation_data):
        super().__init__()
        self.conversation_data = conversation_data
        self.conversation_id = conversation_data.get('conversation_id')
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the conversation list item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # User avatar
        other_user = self.conversation_data.get('other_user', {})
        user_name = other_user.get('display_name') or other_user.get('username') or 'Unknown User'
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_label.setPixmap(self.create_user_avatar(user_name, other_user))
        layout.addWidget(self.avatar_label)
        
        # Conversation info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # User name
        name_label = QLabel(user_name)
        name_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # Last message preview
        last_message = self.conversation_data.get('last_message', {})
        if last_message:
            message_preview = last_message.get('content', '')
            if len(message_preview) > 50:
                message_preview = message_preview[:50] + "..."
            
            preview_label = QLabel(message_preview)
            preview_label.setStyleSheet("color: #888888; font-size: 12px;")
            preview_label.setWordWrap(True)
            info_layout.addWidget(preview_label)
        else:
            preview_label = QLabel("No messages yet")
            preview_label.setStyleSheet("color: #888888; font-size: 12px; font-style: italic;")
            info_layout.addWidget(preview_label)
        
        layout.addLayout(info_layout, 1)
        
        # Right side info
        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)
        
        # Time
        last_message = self.conversation_data.get('last_message', {})
        if last_message and last_message.get('created_at'):
            time_str = datetime.fromisoformat(last_message['created_at'].replace('Z', '+00:00')).strftime('%H:%M')
            time_label = QLabel(time_str)
            time_label.setStyleSheet("color: #888888; font-size: 11px;")
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            right_layout.addWidget(time_label)
        
        # Unread count
        unread_count = self.conversation_data.get('unread_count', 0)
        if unread_count > 0:
            unread_label = QLabel(str(unread_count))
            unread_label.setStyleSheet("""
                color: #ffffff;
                background-color: #e74c3c;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
            unread_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            unread_label.setFixedSize(20, 20)
            right_layout.addWidget(unread_label)
        else:
            right_layout.addStretch()
        
        layout.addLayout(right_layout)
        
        # Set background and click handling
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
            QWidget:hover {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
        """)
        
        # Make clickable
        self.mousePressEvent = self.on_click
    
    def create_user_avatar(self, user_name, user_data=None):
        """Create a circular avatar with user profile picture or initials."""
        size = 40
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Check if user has an avatar URL
        avatar_url = None
        if user_data:
            avatar_url = user_data.get('avatar_url')
        
        # Load avatar from URL if available
        if avatar_url:
            return self.load_avatar_from_url(avatar_url, size)
        
        # Fallback to initials
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in user_name.split()][:2])
        
        # Create pixmap for avatar
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(user_name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        return pixmap
    
    def load_avatar_from_url(self, url: str, size: int = 40) -> QPixmap:
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
                            painter.end()
                            
                            # Update avatar display if this widget is still valid
                            if hasattr(self, 'avatar_label') and self.avatar_label:
                                self.avatar_label.setPixmap(circular_pixmap)
                    
                    reply.deleteLater()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    fallback_pixmap = self.create_fallback_avatar(size, user_name)
                    if hasattr(self, 'avatar_label') and self.avatar_label:
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
            return self.create_fallback_avatar(size, user_name)
    
    def create_fallback_avatar(self, size: int = 40, user_name: str = 'U') -> QPixmap:
        """Create a fallback avatar with initials when image loading fails."""
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in user_name.split()][:2])
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(user_name) % len(colors)
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
        
        painter.end()
        return pixmap
    
    def on_click(self, event):
        """Handle click event."""
        self.conversation_selected.emit(self.conversation_id) 