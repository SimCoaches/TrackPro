"""Social UI Framework for TrackPro - Comprehensive social interface components."""

import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from ..social import (
    enhanced_user_manager, friends_manager, messaging_manager, 
    activity_manager, community_manager, achievements_manager, 
    reputation_manager, content_manager
)

logger = logging.getLogger(__name__)

class SocialTheme:
    """Racing-inspired theme for social UI components."""
    
    # Color scheme
    COLORS = {
        'primary': '#FF6B35',      # Racing orange
        'secondary': '#1A1A1A',    # Dark background
        'accent': '#00D4FF',       # Electric blue
        'success': '#00FF88',      # Neon green
        'warning': '#FFD700',      # Gold
        'danger': '#FF3366',       # Red
        'text_primary': '#FFFFFF', # White text
        'text_secondary': '#CCCCCC', # Light gray text
        'background': '#0D1117',   # Very dark background
        'surface': '#21262D',      # Card background
        'border': '#30363D'        # Border color
    }
    
    # Fonts
    FONTS = {
        'heading': QFont('Segoe UI', 16, QFont.Weight.Bold),
        'subheading': QFont('Segoe UI', 14, QFont.Weight.Bold),
        'body': QFont('Segoe UI', 12),
        'caption': QFont('Segoe UI', 10),
        'button': QFont('Segoe UI', 11, QFont.Weight.Bold)
    }
    
    @staticmethod
    def get_stylesheet() -> str:
        """Get the main stylesheet for social components."""
        return f"""
        QWidget {{
            background-color: {SocialTheme.COLORS['background']};
            color: {SocialTheme.COLORS['text_primary']};
            font-family: 'Segoe UI';
        }}
        
        QFrame {{
            background-color: {SocialTheme.COLORS['surface']};
            border: 1px solid {SocialTheme.COLORS['border']};
            border-radius: 8px;
            padding: 12px;
        }}
        
        QPushButton {{
            background-color: {SocialTheme.COLORS['primary']};
            color: {SocialTheme.COLORS['text_primary']};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: #FF8555;
        }}
        
        QPushButton:pressed {{
            background-color: #E55A2B;
        }}
        
        QPushButton:disabled {{
            background-color: #555555;
            color: #888888;
        }}
        
        QLineEdit, QTextEdit {{
            background-color: {SocialTheme.COLORS['surface']};
            border: 2px solid {SocialTheme.COLORS['border']};
            border-radius: 6px;
            padding: 8px;
            color: {SocialTheme.COLORS['text_primary']};
        }}
        
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {SocialTheme.COLORS['accent']};
        }}
        
        QListWidget, QTreeWidget {{
            background-color: {SocialTheme.COLORS['surface']};
            border: 1px solid {SocialTheme.COLORS['border']};
            border-radius: 6px;
            alternate-background-color: #2A2A2A;
        }}
        
        QListWidget::item, QTreeWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {SocialTheme.COLORS['border']};
        }}
        
        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {SocialTheme.COLORS['primary']};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {SocialTheme.COLORS['border']};
            background-color: {SocialTheme.COLORS['surface']};
        }}
        
        QTabBar::tab {{
            background-color: {SocialTheme.COLORS['background']};
            color: {SocialTheme.COLORS['text_secondary']};
            padding: 8px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {SocialTheme.COLORS['primary']};
            color: {SocialTheme.COLORS['text_primary']};
        }}
        
        QScrollBar:vertical {{
            background-color: {SocialTheme.COLORS['background']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {SocialTheme.COLORS['border']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {SocialTheme.COLORS['accent']};
        }}
        """

class UserProfileWidget(QFrame):
    """Enhanced user profile display widget."""
    
    def __init__(self, user_id: str, compact: bool = False, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.compact = compact
        self.user_data = None
        self.init_ui()
        self.load_user_data()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self) if self.compact else QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(64 if self.compact else 120, 64 if self.compact else 120)
        self.avatar_label.setStyleSheet(f"""
            QLabel {{
                border: 3px solid {SocialTheme.COLORS['accent']};
                border-radius: {32 if self.compact else 60}px;
                background-color: {SocialTheme.COLORS['surface']};
            }}
        """)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setText("👤")  # Default avatar
        
        # User info
        info_layout = QVBoxLayout()
        
        # Username and display name
        self.username_label = QLabel()
        self.username_label.setFont(SocialTheme.FONTS['subheading'])
        
        self.display_name_label = QLabel()
        self.display_name_label.setFont(SocialTheme.FONTS['body'])
        self.display_name_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        # Level and XP
        self.level_label = QLabel()
        self.level_label.setFont(SocialTheme.FONTS['caption'])
        
        # Reputation
        self.reputation_label = QLabel()
        self.reputation_label.setFont(SocialTheme.FONTS['caption'])
        
        info_layout.addWidget(self.username_label)
        info_layout.addWidget(self.display_name_label)
        info_layout.addWidget(self.level_label)
        info_layout.addWidget(self.reputation_label)
        
        if not self.compact:
            # Bio
            self.bio_label = QLabel()
            self.bio_label.setFont(SocialTheme.FONTS['body'])
            self.bio_label.setWordWrap(True)
            info_layout.addWidget(self.bio_label)
            
            # Stats
            stats_layout = QHBoxLayout()
            self.stats_labels = {}
            for stat in ['Friends', 'Teams', 'Achievements']:
                stat_widget = QVBoxLayout()
                count_label = QLabel("0")
                count_label.setFont(SocialTheme.FONTS['subheading'])
                count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                name_label = QLabel(stat)
                name_label.setFont(SocialTheme.FONTS['caption'])
                name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stat_widget.addWidget(count_label)
                stat_widget.addWidget(name_label)
                stats_layout.addLayout(stat_widget)
                self.stats_labels[stat.lower()] = count_label
            
            info_layout.addLayout(stats_layout)
        
        layout.addWidget(self.avatar_label)
        layout.addLayout(info_layout)
        
        if self.compact:
            layout.addStretch()
    
    def load_user_data(self):
        """Load and display user data."""
        try:
            self.user_data = enhanced_user_manager.get_complete_user_profile(self.user_id)
            if self.user_data:
                self.update_display()
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def update_display(self):
        """Update the display with user data."""
        if not self.user_data:
            return
        
        # Update labels
        self.username_label.setText(self.user_data.get('username', 'Unknown'))
        self.display_name_label.setText(self.user_data.get('display_name', ''))
        
        level = self.user_data.get('level', 1)
        total_xp = self.user_data.get('total_xp', 0)
        self.level_label.setText(f"Level {level} • {total_xp:,} XP")
        
        reputation = self.user_data.get('reputation_score', 0)
        rep_level = reputation_manager.get_reputation_level(reputation)
        self.reputation_label.setText(f"{rep_level.title()} • {reputation} Rep")
        
        if not self.compact:
            self.bio_label.setText(self.user_data.get('bio', 'No bio available'))
            
            # Update stats
            friend_count = friends_manager.get_friend_count(self.user_id)
            team_count = len(community_manager.get_user_teams(self.user_id))
            achievement_count = len(achievements_manager.get_user_achievements(self.user_id, unlocked_only=True))
            
            self.stats_labels['friends'].setText(str(friend_count))
            self.stats_labels['teams'].setText(str(team_count))
            self.stats_labels['achievements'].setText(str(achievement_count))

class FriendsListWidget(QWidget):
    """Friends list and management widget."""
    
    friend_selected = pyqtSignal(str)  # Emits friend user_id
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_friends()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Friends")
        title_label.setFont(SocialTheme.FONTS['heading'])
        
        add_friend_btn = QPushButton("Add Friend")
        add_friend_btn.clicked.connect(self.show_add_friend_dialog)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_friend_btn)
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search friends...")
        self.search_input.textChanged.connect(self.filter_friends)
        
        # Friends list
        self.friends_list = QListWidget()
        self.friends_list.itemClicked.connect(self.on_friend_selected)
        
        # Friend requests section
        requests_label = QLabel("Friend Requests")
        requests_label.setFont(SocialTheme.FONTS['subheading'])
        
        self.requests_list = QListWidget()
        self.requests_list.setMaximumHeight(150)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.search_input)
        layout.addWidget(self.friends_list)
        layout.addWidget(requests_label)
        layout.addWidget(self.requests_list)
    
    def load_friends(self):
        """Load and display friends list."""
        try:
            friends = friends_manager.get_friends_list(self.current_user_id, include_online_status=True)
            self.friends_list.clear()
            
            for friend in friends:
                item = QListWidgetItem()
                widget = self.create_friend_item(friend)
                item.setSizeHint(widget.sizeHint())
                self.friends_list.addItem(item)
                self.friends_list.setItemWidget(item, widget)
            
            # Load friend requests
            requests = friends_manager.get_pending_friend_requests(self.current_user_id, sent=False)
            self.requests_list.clear()
            
            for request in requests:
                item = QListWidgetItem()
                widget = self.create_request_item(request)
                item.setSizeHint(widget.sizeHint())
                self.requests_list.addItem(item)
                self.requests_list.setItemWidget(item, widget)
                
        except Exception as e:
            logger.error(f"Error loading friends: {e}")
    
    def create_friend_item(self, friend_data: Dict[str, Any]) -> QWidget:
        """Create a friend list item widget."""
        widget = QFrame()
        layout = QHBoxLayout(widget)
        
        # Avatar
        avatar = QLabel("👤")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {SocialTheme.COLORS['accent']};
                border-radius: 20px;
                background-color: {SocialTheme.COLORS['surface']};
            }}
        """)
        
        # Info
        info_layout = QVBoxLayout()
        username_label = QLabel(friend_data.get('friend_username', 'Unknown'))
        username_label.setFont(SocialTheme.FONTS['body'])
        
        status_text = "🟢 Online" if friend_data.get('is_online', False) else "⚫ Offline"
        status_label = QLabel(status_text)
        status_label.setFont(SocialTheme.FONTS['caption'])
        status_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(username_label)
        info_layout.addWidget(status_label)
        
        # Actions
        message_btn = QPushButton("💬")
        message_btn.setFixedSize(30, 30)
        message_btn.clicked.connect(lambda: self.start_conversation(friend_data['friend_id']))
        
        layout.addWidget(avatar)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(message_btn)
        
        return widget
    
    def create_request_item(self, request_data: Dict[str, Any]) -> QWidget:
        """Create a friend request item widget."""
        widget = QFrame()
        layout = QHBoxLayout(widget)
        
        # Info
        username = request_data.get('user_profiles', {}).get('username', 'Unknown')
        info_label = QLabel(f"{username} wants to be friends")
        info_label.setFont(SocialTheme.FONTS['body'])
        
        # Actions
        accept_btn = QPushButton("Accept")
        accept_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['success']};")
        accept_btn.clicked.connect(lambda: self.respond_to_request(request_data['id'], True))
        
        decline_btn = QPushButton("Decline")
        decline_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['danger']};")
        decline_btn.clicked.connect(lambda: self.respond_to_request(request_data['id'], False))
        
        layout.addWidget(info_label)
        layout.addStretch()
        layout.addWidget(accept_btn)
        layout.addWidget(decline_btn)
        
        return widget
    
    def filter_friends(self, text: str):
        """Filter friends list based on search text."""
        for i in range(self.friends_list.count()):
            item = self.friends_list.item(i)
            widget = self.friends_list.itemWidget(item)
            if widget:
                username_label = widget.findChild(QLabel)
                if username_label:
                    visible = text.lower() in username_label.text().lower()
                    item.setHidden(not visible)
    
    def show_add_friend_dialog(self):
        """Show add friend dialog."""
        dialog = AddFriendDialog(self.current_user_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_friends()
    
    def start_conversation(self, friend_id: str):
        """Start a conversation with a friend."""
        # This would open the messaging interface
        pass
    
    def respond_to_request(self, request_id: str, accept: bool):
        """Respond to a friend request."""
        try:
            result = friends_manager.respond_to_friend_request(request_id, self.current_user_id, accept)
            if result['success']:
                self.load_friends()
            else:
                QMessageBox.warning(self, "Error", result['message'])
        except Exception as e:
            logger.error(f"Error responding to friend request: {e}")
    
    def on_friend_selected(self, item):
        """Handle friend selection."""
        widget = self.friends_list.itemWidget(item)
        if widget:
            # Extract friend_id from widget data
            pass

class MessagingWidget(QWidget):
    """Comprehensive messaging interface."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.current_conversation_id = None
        self.init_ui()
        self.load_conversations()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        
        # Conversations list (left panel)
        conversations_panel = QFrame()
        conversations_panel.setFixedWidth(300)
        conversations_layout = QVBoxLayout(conversations_panel)
        
        conversations_title = QLabel("Conversations")
        conversations_title.setFont(SocialTheme.FONTS['heading'])
        
        self.conversations_list = QListWidget()
        self.conversations_list.itemClicked.connect(self.on_conversation_selected)
        
        conversations_layout.addWidget(conversations_title)
        conversations_layout.addWidget(self.conversations_list)
        
        # Chat panel (right panel)
        chat_panel = QFrame()
        chat_layout = QVBoxLayout(chat_panel)
        
        # Chat header
        self.chat_header = QLabel("Select a conversation")
        self.chat_header.setFont(SocialTheme.FONTS['subheading'])
        self.chat_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Messages area
        self.messages_area = QScrollArea()
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.addStretch()
        self.messages_area.setWidget(self.messages_widget)
        self.messages_area.setWidgetResizable(True)
        
        # Message input
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.returnPressed.connect(self.send_message)
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        
        chat_layout.addWidget(self.chat_header)
        chat_layout.addWidget(self.messages_area)
        chat_layout.addLayout(input_layout)
        
        layout.addWidget(conversations_panel)
        layout.addWidget(chat_panel)
    
    def load_conversations(self):
        """Load user's conversations."""
        try:
            conversations = messaging_manager.get_user_conversations(self.current_user_id)
            self.conversations_list.clear()
            
            for conversation in conversations:
                item = QListWidgetItem()
                widget = self.create_conversation_item(conversation)
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.ItemDataRole.UserRole, conversation['id'])
                self.conversations_list.addItem(item)
                self.conversations_list.setItemWidget(item, widget)
                
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
    
    def create_conversation_item(self, conversation: Dict[str, Any]) -> QWidget:
        """Create a conversation list item."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        # Conversation name
        if conversation['type'] == 'direct':
            other_participant = conversation.get('other_participant', {})
            name = other_participant.get('display_name') or other_participant.get('username', 'Unknown')
        else:
            name = conversation.get('name', 'Group Chat')
        
        name_label = QLabel(name)
        name_label.setFont(SocialTheme.FONTS['body'])
        
        # Last message preview
        last_message = conversation.get('last_message', {})
        if last_message:
            preview = last_message.get('content', '')[:50] + ('...' if len(last_message.get('content', '')) > 50 else '')
            preview_label = QLabel(preview)
            preview_label.setFont(SocialTheme.FONTS['caption'])
            preview_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        else:
            preview_label = QLabel("No messages")
            preview_label.setFont(SocialTheme.FONTS['caption'])
            preview_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        # Unread indicator
        unread_count = conversation.get('unread_count', 0)
        if unread_count > 0:
            unread_label = QLabel(str(unread_count))
            unread_label.setFixedSize(20, 20)
            unread_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            unread_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {SocialTheme.COLORS['primary']};
                    color: white;
                    border-radius: 10px;
                    font-weight: bold;
                }}
            """)
        
        layout.addWidget(name_label)
        layout.addWidget(preview_label)
        
        return widget
    
    def on_conversation_selected(self, item):
        """Handle conversation selection."""
        conversation_id = item.data(Qt.ItemDataRole.UserRole)
        self.current_conversation_id = conversation_id
        self.load_messages()
    
    def load_messages(self):
        """Load messages for current conversation."""
        if not self.current_conversation_id:
            return
        
        try:
            messages = messaging_manager.get_messages(self.current_conversation_id, self.current_user_id)
            
            # Clear existing messages
            for i in reversed(range(self.messages_layout.count())):
                child = self.messages_layout.itemAt(i).widget()
                if child and child != self.messages_layout.itemAt(-1).widget():  # Don't remove stretch
                    child.setParent(None)
            
            # Add messages
            for message in messages:
                message_widget = self.create_message_widget(message)
                self.messages_layout.insertWidget(self.messages_layout.count() - 1, message_widget)
            
            # Scroll to bottom
            QTimer.singleShot(100, lambda: self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            ))
            
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
    
    def create_message_widget(self, message: Dict[str, Any]) -> QWidget:
        """Create a message widget."""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        is_own_message = message['sender_id'] == self.current_user_id
        
        # Message content
        content_label = QLabel(message['content'])
        content_label.setWordWrap(True)
        content_label.setFont(SocialTheme.FONTS['body'])
        
        if is_own_message:
            content_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            content_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {SocialTheme.COLORS['primary']};
                    padding: 8px 12px;
                    border-radius: 12px;
                    margin-left: 50px;
                }}
            """)
        else:
            content_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            content_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {SocialTheme.COLORS['surface']};
                    padding: 8px 12px;
                    border-radius: 12px;
                    margin-right: 50px;
                }}
            """)
        
        # Timestamp
        timestamp = datetime.fromisoformat(message['created_at'].replace('Z', '+00:00'))
        time_label = QLabel(timestamp.strftime('%H:%M'))
        time_label.setFont(SocialTheme.FONTS['caption'])
        time_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        if is_own_message:
            time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            time_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(content_label)
        layout.addWidget(time_label)
        
        return widget
    
    def send_message(self):
        """Send a message."""
        if not self.current_conversation_id or not self.message_input.text().strip():
            return
        
        try:
            content = self.message_input.text().strip()
            result = messaging_manager.send_message(
                self.current_conversation_id,
                self.current_user_id,
                content
            )
            
            if result:
                self.message_input.clear()
                self.load_messages()
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")

class ActivityFeedWidget(QWidget):
    """Social activity feed widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_activities()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Activity Feed")
        title_label.setFont(SocialTheme.FONTS['heading'])
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.clicked.connect(self.load_activities)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        
        # Feed type tabs
        self.feed_tabs = QTabWidget()
        
        # User feed
        self.user_feed = QScrollArea()
        self.user_feed_widget = QWidget()
        self.user_feed_layout = QVBoxLayout(self.user_feed_widget)
        self.user_feed_layout.addStretch()
        self.user_feed.setWidget(self.user_feed_widget)
        self.user_feed.setWidgetResizable(True)
        
        # Public feed
        self.public_feed = QScrollArea()
        self.public_feed_widget = QWidget()
        self.public_feed_layout = QVBoxLayout(self.public_feed_widget)
        self.public_feed_layout.addStretch()
        self.public_feed.setWidget(self.public_feed_widget)
        self.public_feed.setWidgetResizable(True)
        
        self.feed_tabs.addTab(self.user_feed, "My Feed")
        self.feed_tabs.addTab(self.public_feed, "Public")
        self.feed_tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.feed_tabs)
    
    def load_activities(self):
        """Load activities for current feed."""
        current_tab = self.feed_tabs.currentIndex()
        
        try:
            if current_tab == 0:  # User feed
                activities = activity_manager.get_user_feed(self.current_user_id)
                self.populate_feed(activities, self.user_feed_layout)
            else:  # Public feed
                activities = activity_manager.get_public_feed()
                self.populate_feed(activities, self.public_feed_layout)
                
        except Exception as e:
            logger.error(f"Error loading activities: {e}")
    
    def populate_feed(self, activities: List[Dict[str, Any]], layout: QVBoxLayout):
        """Populate a feed with activities."""
        # Clear existing activities
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i).widget()
            if child and child != layout.itemAt(-1).widget():  # Don't remove stretch
                child.setParent(None)
        
        # Add activities
        for activity in activities:
            activity_widget = self.create_activity_widget(activity)
            layout.insertWidget(layout.count() - 1, activity_widget)
    
    def create_activity_widget(self, activity: Dict[str, Any]) -> QWidget:
        """Create an activity widget."""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['surface']};
                border: 1px solid {SocialTheme.COLORS['border']};
                border-radius: 8px;
                margin-bottom: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        
        # Header with user info
        header_layout = QHBoxLayout()
        
        user_info = activity.get('user_profiles', {})
        username = user_info.get('username', 'Unknown')
        
        user_label = QLabel(username)
        user_label.setFont(SocialTheme.FONTS['body'])
        
        timestamp = datetime.fromisoformat(activity['created_at'].replace('Z', '+00:00'))
        time_label = QLabel(timestamp.strftime('%H:%M • %b %d'))
        time_label.setFont(SocialTheme.FONTS['caption'])
        time_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        header_layout.addWidget(user_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)
        
        # Activity content
        title_label = QLabel(activity['title'])
        title_label.setFont(SocialTheme.FONTS['subheading'])
        
        if activity.get('description'):
            desc_label = QLabel(activity['description'])
            desc_label.setFont(SocialTheme.FONTS['body'])
            desc_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
            desc_label.setWordWrap(True)
        
        # Interaction buttons
        interaction_layout = QHBoxLayout()
        
        like_btn = QPushButton("👍 Like")
        like_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        
        comment_btn = QPushButton("💬 Comment")
        comment_btn.setStyleSheet("QPushButton { background: transparent; border: none; }")
        
        interaction_layout.addWidget(like_btn)
        interaction_layout.addWidget(comment_btn)
        interaction_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addWidget(title_label)
        if activity.get('description'):
            layout.addWidget(desc_label)
        layout.addLayout(interaction_layout)
        
        return widget
    
    def on_tab_changed(self, index):
        """Handle tab change."""
        self.load_activities()

class AddFriendDialog(QDialog):
    """Dialog for adding friends."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.setWindowTitle("Add Friend")
        self.setFixedSize(400, 300)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by username...")
        self.search_input.textChanged.connect(self.search_users)
        
        # Results list
        self.results_list = QListWidget()
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(QLabel("Search for users to add as friends:"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.results_list)
        layout.addLayout(button_layout)
    
    def search_users(self, query: str):
        """Search for users."""
        if len(query) < 3:
            self.results_list.clear()
            return
        
        try:
            users = enhanced_user_manager.search_users(query)
            self.results_list.clear()
            
            for user in users:
                if user['user_id'] != self.current_user_id:
                    item = QListWidgetItem()
                    widget = self.create_user_result_item(user)
                    item.setSizeHint(widget.sizeHint())
                    self.results_list.addItem(item)
                    self.results_list.setItemWidget(item, widget)
                    
        except Exception as e:
            logger.error(f"Error searching users: {e}")
    
    def create_user_result_item(self, user: Dict[str, Any]) -> QWidget:
        """Create a user search result item."""
        widget = QFrame()
        layout = QHBoxLayout(widget)
        
        # User info
        username_label = QLabel(user.get('username', 'Unknown'))
        username_label.setFont(SocialTheme.FONTS['body'])
        
        level_label = QLabel(f"Level {user.get('level', 1)}")
        level_label.setFont(SocialTheme.FONTS['caption'])
        level_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        info_layout = QVBoxLayout()
        info_layout.addWidget(username_label)
        info_layout.addWidget(level_label)
        
        # Add friend button
        add_btn = QPushButton("Add Friend")
        add_btn.clicked.connect(lambda: self.send_friend_request(user['user_id']))
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(add_btn)
        
        return widget
    
    def send_friend_request(self, user_id: str):
        """Send a friend request."""
        try:
            result = friends_manager.send_friend_request(self.current_user_id, user_id)
            if result['success']:
                QMessageBox.information(self, "Success", "Friend request sent!")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", result['message'])
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")

class SocialMainWidget(QWidget):
    """Main social interface widget."""
    
    def __init__(self, user_manager=None, friends_manager=None, messaging_manager=None, activity_manager=None, current_user_id: str = None, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.friends_manager = friends_manager
        self.messaging_manager = messaging_manager
        self.activity_manager = activity_manager
        self.current_user_id = current_user_id
        self.setStyleSheet(SocialTheme.get_stylesheet())
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        
        # Left sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # User profile
        self.profile_widget = UserProfileWidget(self.current_user_id, compact=True)
        
        # Navigation
        nav_layout = QVBoxLayout()
        
        self.nav_buttons = {}
        nav_items = [
            ("Activity Feed", "📰"),
            ("Friends", "👥"),
            ("Messages", "💬"),
            ("Teams", "🏁"),
            ("Achievements", "🏆"),
            ("Content", "📁")
        ]
        
        for name, icon in nav_items:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self.switch_view(n))
            self.nav_buttons[name] = btn
            nav_layout.addWidget(btn)
        
        nav_layout.addStretch()
        
        sidebar_layout.addWidget(self.profile_widget)
        sidebar_layout.addLayout(nav_layout)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Initialize views
        self.views = {
            "Activity Feed": ActivityFeedWidget(self.current_user_id),
            "Friends": FriendsListWidget(self.current_user_id),
            "Messages": MessagingWidget(self.current_user_id),
            # Add other views as needed
        }
        
        for view in self.views.values():
            self.content_stack.addWidget(view)
        
        layout.addWidget(sidebar)
        layout.addWidget(self.content_stack)
        
        # Set default view
        self.switch_view("Activity Feed")
    
    def switch_view(self, view_name: str):
        """Switch to a different view."""
        # Update button states
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == view_name)
        
        # Switch content
        if view_name in self.views:
            self.content_stack.setCurrentWidget(self.views[view_name])

# Export main components
__all__ = [
    'SocialTheme',
    'UserProfileWidget', 
    'FriendsListWidget',
    'MessagingWidget',
    'ActivityFeedWidget',
    'SocialMainWidget'
] 