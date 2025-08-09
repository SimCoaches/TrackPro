"""Private messaging widget for community system."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame, 
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen
from ..ui.avatar_manager import AvatarManager

logger = logging.getLogger(__name__)

class PrivateMessageWidget(QWidget):
    """Individual private message widget."""
    
    def __init__(self, message_data, is_own_message=False):
        super().__init__()
        self.message_data = message_data
        self.is_own_message = is_own_message
        self.setup_ui()

    def contextMenuEvent(self, event):
        try:
            from PyQt6.QtWidgets import QMenu
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Message")
            action = menu.exec(event.globalPos())
            if action == delete_action:
                message_id = self.message_data.get("message_id")
                if message_id:
                    # Permission: TEAM/admin can delete any; otherwise only own
                    can_delete = False
                    try:
                        from trackpro.auth.user_manager import get_current_user
                        from trackpro.auth.hierarchy_manager import hierarchy_manager
                        user = get_current_user()
                        if user and user.is_authenticated:
                            if hierarchy_manager.is_admin(user.email):
                                can_delete = True
                            else:
                                can_delete = (self.message_data.get("sender_id") == user.id)
                    except Exception:
                        can_delete = False

                    if can_delete:
                        try:
                            from trackpro.community.community_manager import CommunityManager
                            mgr = CommunityManager()
                            if mgr.delete_private_message(message_id):
                                # Remove from UI list
                                try:
                                    from PyQt6.QtWidgets import QListWidget
                                    parent_list = self.parent()
                                    while parent_list and not isinstance(parent_list, QListWidget):
                                        parent_list = parent_list.parent()
                                    if parent_list:
                                        for idx in range(parent_list.count()):
                                            itm = parent_list.item(idx)
                                            if parent_list.itemWidget(itm) is self:
                                                parent_list.takeItem(idx)
                                                break
                                except Exception:
                                    pass
                        except Exception:
                            pass
        except Exception:
            pass
    
    def create_avatar(self, user_name, user_data=None):
        """Return a cached avatar pixmap and schedule async update via manager."""
        size = 32
        url = user_data.get('avatar_url') if user_data else None
        pix = AvatarManager.instance().get_cached_pixmap(url or "", user_name, size=size)
        # If label exists, schedule async update
        try:
            if hasattr(self, 'avatar_label') and self.avatar_label is not None:
                AvatarManager.instance().set_label_avatar(self.avatar_label, url, user_name, size=size)
        except Exception:
            pass
        return pix
    
    def load_avatar_from_url(self, url: str, size: int = 32) -> QPixmap:
        """Deprecated: use AvatarManager via create_avatar/set_label_avatar instead."""
        # Keep compatibility: return cached and schedule update if label is available
        pix = AvatarManager.instance().get_cached_pixmap(url or "", "U", size=size)
        try:
            if hasattr(self, 'avatar_label') and self.avatar_label is not None:
                AvatarManager.instance().set_label_avatar(self.avatar_label, url, "User", size=size)
        except Exception:
            pass
        return pix
    
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
        
        # Unified left-aligned layout for all messages (own and others)
        user_profiles = self.message_data.get('user_profiles', {})
        user_name = user_profiles.get('display_name') or user_profiles.get('username') or ('You' if self.is_own_message else 'User')
        
        # Avatar on left
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(32, 32)
        self.avatar_label.setPixmap(self.create_avatar(user_name, user_profiles))
        layout.addWidget(self.avatar_label)
        
        # Content on left
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        # Username
        username_label = QLabel(user_name)
        username_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 12px;")
        content_layout.addWidget(username_label)
        
        # Message text (consistent style)
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
    
    def __init__(self, conversation_data, parent=None):
        super().__init__(parent)
        self.conversation_data = conversation_data
        self.conversation_id = conversation_data.get('conversation_id')
        # Ensure this widget expands to fill its parent container
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Typing indicator state
        self._typing_users = {}
        self._typing_cleanup_timer = QTimer(self)
        self._typing_cleanup_timer.setInterval(1000)
        self._typing_cleanup_timer.timeout.connect(self._prune_typing_users)
        self._typing_cleanup_timer.start()
        self._send_typing_debounce = QTimer(self)
        self._send_typing_debounce.setSingleShot(True)
        self._send_typing_debounce.setInterval(1800)
        self._last_typing_sent_ms = 0
        # Short-lived dedupe for optimistically added own messages
        self._recent_sent_keys = {}
        self.setup_ui()
        self._setup_typing_channel()
        # Connect once
        self._send_typing_debounce.timeout.connect(self._send_stop_typing)
    
    def setup_ui(self):
        """Setup the conversation UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Conversation header
        header_widget = QWidget()
        header_widget.setFixedHeight(44)
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
        self.messages_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        layout.addWidget(self.messages_list, 1)
        
        # Message input area
        input_widget = QWidget()
        input_widget.setFixedHeight(64)
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
        self.message_input.setFixedHeight(38)
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
        # Send typing start on edits, debounce stop
        self.message_input.textEdited.connect(self._on_text_edited)
        
        input_layout.addWidget(self.message_input)

        # Typing indicator label above input
        self.typing_label = QLabel("")
        self.typing_label.setStyleSheet("color: #9aa0a6; font-size: 12px; padding: 6px 12px;")
        self.typing_label.setVisible(False)
        layout.addWidget(self.typing_label, 0)

        layout.addWidget(input_widget)
    
    def create_user_avatar(self, user_name, user_data=None):
        """Return a cached avatar pixmap and schedule async update via AvatarManager."""
        size = 32
        url = user_data.get('avatar_url') if user_data else None
        pix = AvatarManager.instance().get_cached_pixmap(url or "", user_name, size=size)
        try:
            if hasattr(self, 'avatar_label') and self.avatar_label is not None:
                AvatarManager.instance().set_label_avatar(self.avatar_label, url, user_name, size=size)
        except Exception:
            pass
        return pix
    
    def load_avatar_from_url(self, url: str, size: int = 32) -> QPixmap:
        """Deprecated: use AvatarManager via create_user_avatar/set_label_avatar instead."""
        try:
            if hasattr(self, 'avatar_label') and self.avatar_label is not None:
                AvatarManager.instance().set_label_avatar(self.avatar_label, url, "User", size=size)
        except Exception:
            pass
        placeholder = QPixmap(size, size)
        placeholder.fill(Qt.GlobalColor.transparent)
        return placeholder
    
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
            # Immediately broadcast stop typing
            try:
                from trackpro.community.community_manager import CommunityManager
                mgr = CommunityManager()
                mgr.send_typing_signal(self.conversation_id, False)
            except Exception:
                pass
            # Optimistically add message to UI and record for dedupe
            try:
                from trackpro.auth.user_manager import get_current_user
                user = get_current_user()
                current_user_id = user.id if (user and user.is_authenticated) else None
            except Exception:
                current_user_id = None
            try:
                # Prefer real user profile data for self (prevents initials "YO")
                display_name = 'You'
                username = 'You'
                avatar_url = None
                try:
                    if current_user_id:
                        from trackpro.community.community_manager import CommunityManager
                        _mgr = CommunityManager()
                        me_profile = _mgr._get_user_data(current_user_id) or {}
                        display_name = me_profile.get('display_name') or me_profile.get('username') or display_name
                        username = me_profile.get('username') or username
                        avatar_url = me_profile.get('avatar_url')
                except Exception:
                    pass
                from datetime import datetime as _dt
                local_msg = {
                    'conversation_id': self.conversation_id,
                    'sender_id': current_user_id,
                    'content': text,
                    'created_at': _dt.utcnow().isoformat() + 'Z',
                    'user_profiles': {
                        'user_id': current_user_id or 'me',
                        'display_name': display_name,
                        'username': username,
                        'avatar_url': avatar_url,
                    }
                }
                self.add_message(local_msg, is_own_message=True)
                # Record recent key for 7 seconds to avoid duplicate when realtime arrives
                import time
                key = f"{current_user_id}|{text}|{self.conversation_id}"
                self._recent_sent_keys[key] = time.time() + 7.0
            except Exception:
                pass
    
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

    # ----------------------------
    # Typing indicator helpers
    # ----------------------------
    def _setup_typing_channel(self):
        try:
            from trackpro.community.community_manager import CommunityManager
            self._community_manager = CommunityManager()
            # Ensure current user id is set on manager
            try:
                from trackpro.auth.user_manager import get_current_user
                me = get_current_user()
                if me and me.is_authenticated:
                    self._community_manager.set_current_user(me.id)
            except Exception:
                pass
            # Connect signal once per widget instance
            self._community_manager.typing_event.connect(self._on_typing_event)
            # Listen for private message inserts
            self._community_manager.private_message_received.connect(self._on_realtime_private_message)
            # Ensure channel is created/subscribed
            self._community_manager._get_or_create_typing_channel(self.conversation_id)
        except Exception as e:
            logger.debug(f"Typing channel setup failed: {e}")

    def _on_text_edited(self, _):
        try:
            from PyQt6.QtCore import QTime
            now_ms = QTime.currentTime().msecsSinceStartOfDay()
            # Throttle start typing every ~2000ms
            if now_ms - getattr(self, '_last_typing_sent_ms', 0) > 2000:
                from trackpro.community.community_manager import CommunityManager
                mgr = CommunityManager()
                mgr.send_typing_signal(self.conversation_id, True)
                self._last_typing_sent_ms = now_ms
            # Debounce stop typing by restarting the timer
            self._send_typing_debounce.stop()
            self._send_typing_debounce.start()
        except Exception:
            pass

    def _on_realtime_private_message(self, message_data: dict):
        try:
            if not message_data or message_data.get('conversation_id') != self.conversation_id:
                return
            # Determine own vs other
            is_own = False
            try:
                from trackpro.auth.user_manager import get_current_user
                me = get_current_user()
                is_own = bool(me and me.is_authenticated and message_data.get('sender_id') == me.id)
            except Exception:
                pass
            # Skip duplicate if we just optimistically added the same content (compare trimmed content)
            try:
                import time
                sender_id = message_data.get('sender_id')
                content = (message_data.get('content') or '').strip()
                key = f"{sender_id}|{content}|{self.conversation_id}"
                expiry = self._recent_sent_keys.get(key)
                if expiry and expiry > time.time():
                    # Consume the dedupe key and skip adding duplicate
                    self._recent_sent_keys.pop(key, None)
                    return
            except Exception:
                pass
            self.add_message(message_data, is_own_message=is_own)
            # Auto-scroll to newest after appending
            try:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.messages_list.scrollToBottom)
            except Exception:
                pass
            # Clear typing state for sender if present
            sender_id = message_data.get('sender_id')
            if sender_id in self._typing_users:
                self._typing_users.pop(sender_id, None)
                self._update_typing_label()
        except Exception:
            pass

    def _send_stop_typing(self):
        try:
            from trackpro.community.community_manager import CommunityManager
            mgr = CommunityManager()
            mgr.send_typing_signal(self.conversation_id, False)
        except Exception:
            pass

    def _on_typing_event(self, conversation_id: str, payload: dict):
        try:
            if conversation_id != self.conversation_id:
                return
            user_id = payload.get('user_id')
            is_typing = bool(payload.get('is_typing'))
            if not user_id:
                return
            # Do not show our own typing
            try:
                from trackpro.auth.user_manager import get_current_user
                me = get_current_user()
                if me and me.is_authenticated and me.id == user_id:
                    return
            except Exception:
                pass
            import time
            if is_typing:
                self._typing_users[user_id] = time.time() + 3.0
            else:
                self._typing_users.pop(user_id, None)
            self._update_typing_label()
        except Exception:
            pass

    def _prune_typing_users(self):
        try:
            import time
            now = time.time()
            removed = False
            for uid, expiry in list(self._typing_users.items()):
                if expiry < now:
                    self._typing_users.pop(uid, None)
                    removed = True
            if removed:
                self._update_typing_label()
            # Also prune recent sent dedupe keys
            for k, expiry in list(self._recent_sent_keys.items()):
                if expiry < now:
                    self._recent_sent_keys.pop(k, None)
        except Exception:
            pass

    def _update_typing_label(self):
        try:
            # Map user_ids to display names if we can
            names = []
            if not self._typing_users:
                self.typing_label.setVisible(False)
                self.typing_label.setText("")
                return
            try:
                from trackpro.community.community_manager import CommunityManager
                mgr = CommunityManager()
                for uid in self._typing_users.keys():
                    info = mgr._get_user_data(uid) or {}
                    name = info.get('display_name') or info.get('username') or 'User'
                    names.append(name)
            except Exception:
                names = ['User' for _ in self._typing_users.keys()]

            unique_names = list(dict.fromkeys(names))
            text = ""
            if len(unique_names) == 1:
                text = f"{unique_names[0]} is typing…"
            elif len(unique_names) == 2:
                text = f"{unique_names[0]} and {unique_names[1]} are typing…"
            else:
                text = f"{unique_names[0]}, {unique_names[1]} and {len(unique_names)-2} others are typing…"
            self.typing_label.setText(text)
            self.typing_label.setVisible(True)
        except Exception:
            pass


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
        """Return a cached avatar pixmap and schedule async update via AvatarManager."""
        size = 40
        url = user_data.get('avatar_url') if user_data else None
        pix = AvatarManager.instance().get_cached_pixmap(url or "", user_name, size=size)
        try:
            if hasattr(self, 'avatar_label') and self.avatar_label is not None:
                AvatarManager.instance().set_label_avatar(self.avatar_label, url, user_name, size=size)
        except Exception:
            pass
        return pix
    
    def load_avatar_from_url(self, url: str, size: int = 40) -> QPixmap:
        """Deprecated: use AvatarManager via create_user_avatar/set_label_avatar instead."""
        try:
            if hasattr(self, 'avatar_label') and self.avatar_label is not None:
                name = self.conversation_data.get('other_user', {}).get('display_name') or self.conversation_data.get('other_user', {}).get('username') or 'User'
                AvatarManager.instance().set_label_avatar(self.avatar_label, url, name, size=size)
        except Exception:
            pass
        placeholder = QPixmap(size, size)
        placeholder.fill(Qt.GlobalColor.transparent)
        return placeholder
    
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