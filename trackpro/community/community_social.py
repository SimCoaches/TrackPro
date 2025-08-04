"""
Community Social Components
Contains all social-related widgets and functionality for the TrackPro Community.
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from datetime import datetime
from .community_theme import CommunityTheme


class CommunitySocialMixin:
    """Mixin class containing all social-related functionality"""
    
    def create_modern_social_widget(self):
        """Create modern social widget with full functionality"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        if self.user_id and self.user_id != 'default_user':
            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("Social Hub")
            title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
            title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
            
            subtitle_label = QLabel("Connect with friends and track activity")
            subtitle_label.setFont(QFont(*CommunityTheme.FONTS['body']))
            subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(subtitle_label)
            layout.addLayout(header_layout)
            
            # Main content area with tabs - Focused on racing social features
            tab_widget = QTabWidget()
            tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {CommunityTheme.COLORS['border']};
                    background-color: {CommunityTheme.COLORS['surface']};
                    border-radius: 6px;
                }}
                QTabBar::tab {{
                    background-color: {CommunityTheme.COLORS['surface_darker']};
                    color: {CommunityTheme.COLORS['text_secondary']};
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }}
                QTabBar::tab:selected {{
                    background-color: {CommunityTheme.COLORS['active']};
                    color: white;
                }}
                QTabBar::tab:hover {{
                    background-color: {CommunityTheme.COLORS['surface']};
                }}
            """)
            
            # Live Achievement Feed Tab - 100% automated racing accomplishments
            activity_widget = self.create_racing_activity_feed()
            tab_widget.addTab(activity_widget, "Live Achievements")
            
            # Racing Friends Tab - Focus on racing stats and comparisons
            friends_widget = self.create_racing_friends_list()
            tab_widget.addTab(friends_widget, "Racing Friends")
            
            # Quick Chat Tab - Simplified for race coordination (note: use Discord for full chat)
            quick_chat_widget = self.create_quick_chat_panel()
            tab_widget.addTab(quick_chat_widget, "Quick Notes")
            
            layout.addWidget(tab_widget)
        else:
            return self.create_placeholder_widget("Please log in to access social features")
            
        return widget
        
    def create_racing_activity_feed(self):
        """Create racing-focused activity feed widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header for automated achievement feed
        header_layout = QVBoxLayout()
        
        title_label = QLabel("🏆 Live Racing Achievements")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        subtitle_label = QLabel("⚡ Automated feed of community racing accomplishments")
        subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; font-style: italic; padding: 4px 0px;")
        
        discord_note = QLabel("💬 For live chat and discussion, use the Discord tab →")
        discord_note.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-style: italic; padding: 4px 0px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(discord_note)
        layout.addLayout(header_layout)
        
        # Pure automated achievement feed - no manual posting
        # All racing achievements are automatically generated from real telemetry data
        
        # Racing activity feed with improved spacing
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{ 
                border: none; 
                background-color: {CommunityTheme.COLORS['background']};
            }}
        """)
        
        feed_content = QWidget()
        feed_layout = QVBoxLayout(feed_content)
        feed_layout.setContentsMargins(8, 8, 8, 8)  # Add margins around content
        feed_layout.setSpacing(16)  # Increase spacing between items
        
        # Store reference to activity feed content for refreshing
        self.activity_feed_widget = feed_content
        
        # Load real activity feed from database - NO FAKE DATA
        if self.db_managers and 'social_manager' in self.db_managers and self.user_id:
            try:
                activities_data = self.db_managers['social_manager'].get_activity_feed(self.user_id)
                
                if activities_data:
                    for activity in activities_data:
                        activity_item = self.create_racing_activity_item(
                            activity.get('icon', '📢'),
                            activity.get('title', 'Activity'),
                            activity.get('description', ''),
                            self.format_time_ago(activity.get('created_at'))
                        )
                        feed_layout.addWidget(activity_item)
                else:
                    # No activities found - show empty state
                    empty_label = QLabel("No achievements yet. Complete some laps in iRacing to see automated achievements appear here!")
                    empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    feed_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load activities: {str(e)}")
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                feed_layout.addWidget(error_label)
        else:
            # NO FAKE DATA - show empty state only
            empty_label = QLabel("No recent activity yet. Complete some laps to see achievements here!")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
            empty_label.setWordWrap(True)
            feed_layout.addWidget(empty_label)
            
        feed_layout.addStretch()
        scroll_area.setWidget(feed_content)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_racing_friends_list(self):
        """Create racing-focused friends list with lap time comparisons."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Racing Friends")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        add_friend_btn = QPushButton("+ Add Racing Friend")
        add_friend_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        add_friend_btn.clicked.connect(self.show_add_friend_dialog)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(add_friend_btn)
        layout.addLayout(header_layout)
        
        # Friends list with racing stats
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        friends_content = QWidget()
        friends_layout = QVBoxLayout(friends_content)
        friends_layout.setSpacing(8)
        
        # Load real friends from database - NO FAKE DATA
        if self.db_managers and 'social_manager' in self.db_managers and self.user_id:
            try:
                friends_data = self.db_managers['social_manager'].get_friends_list(self.user_id)
                
                if friends_data:
                    for friend in friends_data:
                        # Map status to icon
                        status_icons = {
                            "Online": "🟢",
                            "Away": "🟡", 
                            "Offline": "⚫"
                        }
                        status_icon = status_icons.get(friend.get('status', 'Offline'), "⚫")
                        
                        friend_item = self.create_racing_friend_item(
                            friend.get('display_name', friend.get('username', 'Unknown')),
                            friend.get('status', 'Offline'),
                            friend.get('last_activity', 'Last seen some time ago'),
                            status_icon
                        )
                        friends_layout.addWidget(friend_item)
                else:
                    # No friends found - show empty state
                    empty_label = QLabel("No friends yet. Use the 'Add Friend' button to connect with other racers!")
                    empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    friends_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load friends: {str(e)}")
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                friends_layout.addWidget(error_label)
        else:
            # NO FAKE DATA - show empty state only
            empty_label = QLabel("No friends yet. Add real racing friends to see their activity!")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
            empty_label.setWordWrap(True)
            friends_layout.addWidget(empty_label)
            
        friends_layout.addStretch()
        scroll_area.setWidget(friends_content)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_quick_chat_panel(self):
        """Create simplified quick notes panel (Discord handles full chat)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with Discord redirect
        header_layout = QVBoxLayout()
        
        title_label = QLabel("Quick Race Notes")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        discord_redirect = QLabel("💬 For full chat and voice communication, switch to the Discord tab")
        discord_redirect.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['accent']}; 
            font-style: italic; 
            padding: 8px; 
            background-color: {CommunityTheme.COLORS['surface_darker']};
            border-radius: 4px;
            border-left: 3px solid {CommunityTheme.COLORS['accent']};
        """)
        discord_redirect.setWordWrap(True)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(discord_redirect)
        layout.addLayout(header_layout)
        
        # Quick notes area - for brief race coordination
        notes_widget = QWidget()
        notes_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        
        notes_layout = QVBoxLayout(notes_widget)
        
        notes_input = QTextEdit()
        notes_input.setPlaceholderText("Quick race coordination notes (e.g., 'Meet at Silverstone in 10 mins', 'Setup available', etc.)")
        notes_input.setMaximumHeight(100)
        notes_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        send_note_btn = QPushButton("📝 Post Quick Note")
        send_note_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['active']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #1C64F2;
            }}
        """)
        
        notes_layout.addWidget(notes_input)
        notes_layout.addWidget(send_note_btn)
        layout.addWidget(notes_widget)

        self.quick_notes_input = notes_input
        send_note_btn.clicked.connect(self.send_quick_note)
        
        # Recent quick notes
        recent_notes_label = QLabel("Recent Quick Notes:")
        recent_notes_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        recent_notes_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold; margin-top: 8px;")
        layout.addWidget(recent_notes_label)
        
        # Real notes from database
        self.quick_notes_layout = QVBoxLayout()
        layout.addLayout(self.quick_notes_layout)

        self.refresh_quick_notes()
            
        layout.addStretch()
        
        return widget
        
    def refresh_quick_notes(self):
        """Refreshes the quick notes panel with recent messages."""
        if not hasattr(self, 'quick_notes_layout'):
            return

        # Clear existing notes
        while self.quick_notes_layout.count():
            child = self.quick_notes_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if hasattr(self, 'db_managers') and self.db_managers and 'social_manager' in self.db_managers and hasattr(self, 'user_id') and self.user_id:
            try:
                conversations = self.db_managers['social_manager'].get_conversations(self.user_id)
                if conversations:
                    # For simplicity, show messages from the most recent conversation
                    most_recent_conv = sorted(conversations, key=lambda c: c.get('updated_at', ''), reverse=True)[0]
                    self.current_conversation_id = most_recent_conv['id']

                    messages = self.db_managers['social_manager'].get_messages(self.current_conversation_id)
                    
                    for msg in messages[:5]: # Show last 5 messages
                        sender_name = msg['user_profiles']['display_name'] if msg.get('user_profiles') else 'Unknown'
                        note_item = self.create_quick_note_item(
                            sender_name,
                            msg['content'],
                            self.format_time_ago(msg['created_at'])
                        )
                        self.quick_notes_layout.addWidget(note_item)
                else:
                    self.quick_notes_layout.addWidget(QLabel("No recent conversations."))
                    self.current_conversation_id = None
            except Exception as e:
                self.quick_notes_layout.addWidget(QLabel(f"Error loading notes: {e}"))
                self.current_conversation_id = None
        else:
            self.quick_notes_layout.addWidget(QLabel("Connect to DB to see notes."))
            self.current_conversation_id = None
    
    def send_quick_note(self):
        """Sends a message in the current quick notes conversation."""
        if not hasattr(self, 'db_managers') or not self.db_managers or 'social_manager' in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return

        if not hasattr(self, 'current_conversation_id') or not self.current_conversation_id:
            QMessageBox.warning(self, "Error", "No active conversation to send a note to.")
            return

        note_content = self.quick_notes_input.toPlainText().strip()
        if not note_content:
            return

        try:
            success = self.db_managers['social_manager'].send_message(self.user_id, self.current_conversation_id, note_content)
            if success:
                self.quick_notes_input.clear()
                self.refresh_quick_notes()
            else:
                QMessageBox.warning(self, "Error", "Failed to send note.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error sending note: {e}")

    def create_racing_activity_item(self, icon, activity_type, description, time_ago):
        """Create a racing-specific activity item."""
        item_widget = QWidget()
        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 6px;
                padding: 12px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        layout = QHBoxLayout(item_widget)
        layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        type_label = QLabel(activity_type)
        type_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        type_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        desc_label.setWordWrap(True)
        
        time_label = QLabel(time_ago)
        time_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        content_layout.addWidget(type_label)
        content_layout.addWidget(desc_label)
        content_layout.addWidget(time_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(content_layout)
        layout.addStretch()
        
        return item_widget
    
    def create_racing_friend_item(self, name, status, racing_info, status_icon):
        """Create a racing-focused friend item with lap times."""
        item_widget = QWidget()
        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 6px;
                padding: 12px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        layout = QHBoxLayout(item_widget)
        layout.setSpacing(12)
        
        # Status icon
        status_label = QLabel(status_icon)
        status_label.setStyleSheet("font-size: 20px;")
        status_label.setFixedSize(30, 30)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Friend info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(name)
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        status_label_text = QLabel(status)
        status_label_text.setFont(QFont(*CommunityTheme.FONTS['caption']))
        status_label_text.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        racing_label = QLabel(racing_info)
        racing_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        racing_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(status_label_text)
        info_layout.addWidget(racing_label)
        
        # Action buttons
        actions_layout = QVBoxLayout()
        
        compare_btn = QPushButton("📊 Compare Times")
        compare_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['active']};
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #1C64F2;
            }}
        """)
        
        invite_btn = QPushButton("🏁 Invite to Race")
        invite_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        
        actions_layout.addWidget(compare_btn)
        actions_layout.addWidget(invite_btn)
        actions_layout.addStretch()
        
        layout.addWidget(status_label)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(actions_layout)
        
        return item_widget
    
    def create_quick_note_item(self, sender, note, time_ago):
        """Create a quick note item for race coordination."""
        item_widget = QWidget()
        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border-left: 3px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
                padding: 8px 12px;
                margin: 2px 0px;
            }}
        """)
        
        layout = QVBoxLayout(item_widget)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        
        sender_label = QLabel(sender)
        sender_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        sender_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        
        time_label = QLabel(time_ago)
        time_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        header_layout.addWidget(sender_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)
        
        note_label = QLabel(note)
        note_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        note_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        note_label.setWordWrap(True)
        
        layout.addLayout(header_layout)
        layout.addWidget(note_label)
        
        return item_widget
    
    def format_time_ago(self, timestamp_str):
        """Format a timestamp into a 'time ago' string"""
        if not timestamp_str:
            return "some time ago"
        
        try:
            # Parse the timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timestamp.tzinfo)
            diff = now - timestamp
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "just now"
        except Exception:
            return "some time ago"
    
    def show_add_friend_dialog(self):
        """Show dialog to add a friend"""
        if not self.db_managers or 'social_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
        
        username, ok = QInputDialog.getText(
            self, 
            "Add Friend", 
            "Enter friend's username:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and username:
            success = self.db_managers['social_manager'].send_friend_request(self.user_id, username)
            if success:
                QMessageBox.information(self, "Success", f"Friend request sent to {username}!")
                # Refresh friends list
                self.refresh_friends_list()
            else:
                QMessageBox.warning(self, "Error", "Could not send friend request. User may not exist or friendship already exists.")
    
    def post_activity_update(self, text_input):
        """Post an activity update"""
        if not self.db_managers or 'social_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
        
        content = text_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Error", "Please enter some content to share.")
            return
        
        success = self.db_managers['social_manager'].post_activity(
            self.user_id,
            "user_update",
            "Shared an update",
            content
        )
        
        if success:
            text_input.clear()
            QMessageBox.information(self, "Success", "Activity posted successfully!")
            # Refresh activity feed
            self.refresh_activity_feed()
        else:
            QMessageBox.warning(self, "Error", "Could not post activity update.")
    
    def refresh_friends_list(self):
        """Refresh the friends list"""
        # This would reload the friends tab content
        # For now, we could recreate the entire social widget
        pass
    
    def trigger_test_achievement(self):
        """Trigger a test achievement to demonstrate the automated system."""
        try:
            # Check if we have the racing achievement monitor available
            if hasattr(self, 'racing_achievement_monitor') and self.racing_achievement_monitor:
                self.racing_achievement_monitor.trigger_test_achievement()
            elif hasattr(self, 'parent') and hasattr(self.parent(), 'racing_achievement_monitor'):
                # Try to get it from parent widget
                parent_monitor = getattr(self.parent(), 'racing_achievement_monitor', None)
                if parent_monitor:
                    parent_monitor.trigger_test_achievement()
            else:
                # NO FAKE DATA - Test button should only test the connection, not post fake achievements
                print("🧪 Test Achievement: Connection test only - no fake data will be posted")
                print("❌ Use real racing data only - complete actual laps to see achievements")
                    
        except Exception as e:
            print(f"❌ Error triggering test achievement: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_activity_feed(self):
        """Refresh the activity feed"""
        try:
            if hasattr(self, 'activity_feed_widget') and self.activity_feed_widget:
                # Get fresh activity data
                if self.db_managers and 'social_manager' in self.db_managers:
                    activities = self.db_managers['social_manager'].get_activity_feed(self.user_id)
                    
                    # Clear existing content
                    layout = self.activity_feed_widget.layout()
                    if layout:
                        while layout.count():
                            child = layout.takeAt(0)
                            if child.widget():
                                child.widget().deleteLater()
                    
                    # Add refreshed activities
                    if activities:
                        for activity in activities[:10]:  # Show latest 10
                            activity_item = self.create_racing_activity_item(
                                "🏁",  # Default icon
                                activity.get('activity_type', 'update'),
                                activity.get('description', ''),
                                self.format_time_ago(activity.get('created_at', ''))
                            )
                            layout.addWidget(activity_item)
                    else:
                        # No activities placeholder
                        no_activity_label = QLabel("No achievements yet. Complete some laps in iRacing to see automated achievements!")
                        no_activity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        no_activity_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 20px;")
                        no_activity_label.setWordWrap(True)
                        layout.addWidget(no_activity_label)
                    
                    layout.addStretch()
                    
                    print("Activity feed refreshed successfully")
        except Exception as e:
            print(f"Error refreshing activity feed: {e}") 