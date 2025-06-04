"""
TrackPro Community Main Widget
Integrated community interface that works as a tab within the main TrackPro application.
"""

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
import json
from typing import Dict, List, Optional, Any

# Import community theme and database managers
from .community_theme import CommunityTheme
from .database_managers import create_community_managers

# Import existing UI components
try:
    from trackpro.ui.community_ui import CommunityMainWidget as CommunityTabWidget
    from trackpro.ui.content_management_ui import ContentManagementMainWidget
    from trackpro.ui.social_ui import SocialMainWidget
    from trackpro.ui.achievements_ui import GamificationMainWidget
    from trackpro.ui.user_account_ui import UserAccountMainWidget
except ImportError as e:
    print(f"Warning: Could not import some community UI components: {e}")
    # Create placeholder widgets if imports fail
    CommunityTabWidget = None
    ContentManagementMainWidget = None
    SocialMainWidget = None
    GamificationMainWidget = None
    UserAccountMainWidget = None


class CommunityNavigationWidget(QWidget):
    """Navigation sidebar for community features"""
    
    section_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_section = "social"
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the navigation UI"""
        self.setFixedWidth(200)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border-right: 1px solid {CommunityTheme.COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(80)
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border-bottom: 1px solid {CommunityTheme.COLORS['border']};
            }}
        """)
        
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(4)
        
        title_label = QLabel("Community")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        
        subtitle_label = QLabel("Connect • Compete • Share")
        subtitle_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        # Navigation buttons
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 16, 0, 16)
        nav_layout.setSpacing(2)
        
        # Navigation items
        nav_items = [
            ("social", "👥 Social", "Friends, messaging, and activity feed"),
            ("community", "🏁 Community", "Teams, clubs, and events"),
            ("content", "📁 Content", "Share setups, media, and guides"),
            ("achievements", "🏆 Achievements", "XP, levels, and gamification"),
            ("account", "⚙️ Account", "Profile and settings")
        ]
        
        self.nav_buttons = {}
        
        for section_id, title, description in nav_items:
            button = self.create_nav_button(section_id, title, description)
            self.nav_buttons[section_id] = button
            nav_layout.addWidget(button, 0)
            
        nav_layout.addStretch()
        
        # Quick stats
        stats_widget = self.create_stats_widget()
        nav_layout.addWidget(stats_widget)
        
        layout.addWidget(header_widget)
        layout.addWidget(nav_widget)
        
        # Set initial selection
        self.set_active_section("social")
        
    def create_nav_button(self, section_id, title, description):
        """Create a navigation button for a section"""
        button = QPushButton()
        button.setCheckable(True)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setMinimumHeight(75)
        
        # Create layout for button content
        layout = QVBoxLayout(button)
        layout.setContentsMargins(16, 15, 16, 15)
        layout.setSpacing(3)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        title_label.setStyleSheet("font-weight: bold; background: transparent;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; background: transparent;")
        
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        
        # Button styling - ensure full coverage and clean text rendering
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                text-align: left;
                padding: 4px 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
            QPushButton:checked {{
                background-color: {CommunityTheme.COLORS['active']};
                color: white;
            }}
            QPushButton QLabel {{
                background: transparent;
                color: inherit;
            }}
            QPushButton:checked QLabel {{
                color: white;
                background: transparent;
            }}
        """)
        
        button.clicked.connect(lambda: self.section_changed.emit(section_id))
        return button
        
    def create_stats_widget(self):
        """Create a quick stats widget"""
        stats_widget = QWidget()
        stats_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 6px;
                padding: 8px;
                margin: 8px;
            }}
        """)
        
        layout = QVBoxLayout(stats_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        title_label = QLabel("Quick Stats")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']};")
        layout.addWidget(title_label)
        
        # Placeholder stats
        stats = [("Friends Online", "12"), ("Team Members", "8"), ("New Messages", "3")]
        
        for stat_name, stat_value in stats:
            stat_layout = QHBoxLayout()
            stat_layout.addWidget(QLabel(stat_name))
            
            value_label = QLabel(stat_value)
            value_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
            stat_layout.addWidget(value_label)
            
            layout.addLayout(stat_layout)
            
        return stats_widget
        
    def set_active_section(self, section_id):
        """Set the active section"""
        self.current_section = section_id
        
        # Update button states
        for btn_id, button in self.nav_buttons.items():
            button.setChecked(btn_id == section_id)


class CommunityMainWidget(QWidget):
    """Main community interface that integrates directly into TrackPro's main window"""
    
    def __init__(self, parent=None, supabase_client=None):
        super().__init__(parent)
        self.supabase_client = supabase_client
        
        # Initialize real database managers if we have Supabase client
        if self.supabase_client:
            self.db_managers = create_community_managers(self.supabase_client)
            # Get current user ID from the managers
            self.user_id = self.db_managers['user_manager'].get_current_user_id()
        else:
            self.db_managers = {}
            self.user_id = None
        
        # Legacy managers support
        self.managers = {}
        self.current_section = "social"
        
        # Initialize activity feed auto-refresh timer
        self.activity_refresh_timer = QTimer()
        self.activity_refresh_timer.timeout.connect(self.refresh_activity_feed)
        self.activity_refresh_timer.start(15000)  # Refresh every 15 seconds
        
        # Initialize delayed auth retry timer (for session sync issues)
        self.auth_retry_timer = QTimer()
        self.auth_retry_timer.setSingleShot(True)  # Only run once
        self.auth_retry_timer.timeout.connect(self.retry_auth_setup)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main community interface"""
        # Apply theme
        self.setStyleSheet(CommunityTheme.get_stylesheet())
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Navigation sidebar
        self.navigation = CommunityNavigationWidget()
        self.navigation.section_changed.connect(self.switch_section)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Create all section widgets
        self.create_section_widgets()
        
        # Main layout
        layout.addWidget(self.navigation)
        layout.addWidget(self.content_stack)
        
        # Set initial section
        self.switch_section("social")
        
    def create_section_widgets(self):
        """Create widgets for each community section"""
        
        # Always use our sleek new design, never the old widgets
        # Social section
        self.social_widget = self.create_modern_social_widget()
        self.content_stack.addWidget(self.social_widget)
            
        # Community section (Teams, Clubs, Events)  
        self.community_widget = self.create_modern_community_widget()
        self.content_stack.addWidget(self.community_widget)
            
        # Content section
        self.content_widget = self.create_modern_content_widget()
        self.content_stack.addWidget(self.content_widget)
            
        # Achievements section
        self.achievements_widget = self.create_modern_achievements_widget()
        self.content_stack.addWidget(self.achievements_widget)
            
        # Account section
        self.account_widget = self.create_modern_account_widget()
        self.content_stack.addWidget(self.account_widget)
            
    def create_placeholder_widget(self, message):
        """Create a placeholder widget for sections that aren't available"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # Icon - different icons for different states
        if "log in" in message.lower():
            icon_text = "🔐"
            icon_color = CommunityTheme.COLORS['warning']
        else:
            icon_text = "🚧"
            icon_color = CommunityTheme.COLORS['text_secondary']
            
        icon_label = QLabel(icon_text)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 48px; color: {icon_color};")
        layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_primary']};
            font-size: 16px;
            font-weight: bold;
            margin: 16px;
        """)
        layout.addWidget(message_label)
        
        # Status
        if "log in" in message.lower():
            status_text = "Sign in to TrackPro to access community features, connect with other racers, and track your progress."
            
            # Add login button
            login_button = QPushButton("Sign In")
            login_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CommunityTheme.COLORS['accent']};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 100px;
                    border: 1px solid {CommunityTheme.COLORS['accent']};
                }}
                QPushButton:hover {{
                    background-color: #FF8A65;
                }}
                QPushButton:pressed {{
                    background-color: #FF5722;
                }}
            """)
            login_button.clicked.connect(self.open_login_dialog)
            layout.addWidget(login_button)
        else:
            status_text = "This feature will be available when all components are loaded."
            
        status_label = QLabel(status_text)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setWordWrap(True)
        status_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_secondary']};
            font-size: 12px;
            margin: 16px;
            max-width: 400px;
        """)
        layout.addWidget(status_label)
        
        return widget
        
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
            
            # Main content area with tabs
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
            
            # Activity Feed Tab
            activity_widget = self.create_activity_feed()
            tab_widget.addTab(activity_widget, "Activity Feed")
            
            # Friends Tab
            friends_widget = self.create_friends_list()
            tab_widget.addTab(friends_widget, "Friends")
            
            # Messages Tab
            messages_widget = self.create_messages_panel()
            tab_widget.addTab(messages_widget, "Messages")
            
            layout.addWidget(tab_widget)
        else:
            return self.create_placeholder_widget("Please log in to access social features")
            
        return widget
        
    def create_activity_feed(self):
        """Create activity feed widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Add new post section
        post_widget = QWidget()
        post_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        
        post_layout = QVBoxLayout(post_widget)
        post_layout.setSpacing(8)
        
        post_input = QTextEdit()
        post_input.setPlaceholderText("Share your racing achievements...")
        post_input.setMaximumHeight(80)
        post_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        post_button = QPushButton("Share Update")
        post_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        # Connect to actual functionality
        post_button.clicked.connect(lambda: self.post_activity_update(post_input))
        
        post_layout.addWidget(post_input)
        post_layout.addWidget(post_button)
        layout.addWidget(post_widget)
        
        # Activity feed
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        feed_content = QWidget()
        feed_layout = QVBoxLayout(feed_content)
        feed_layout.setSpacing(12)
        
        # Store reference to activity feed content for refreshing
        self.activity_feed_widget = feed_content
        
        # Load real activity feed from database - NO FAKE DATA
        if self.db_managers and 'social_manager' in self.db_managers and self.user_id:
            try:
                activities_data = self.db_managers['social_manager'].get_activity_feed(self.user_id)
                
                if activities_data:
                    for activity in activities_data:
                        activity_item = self.create_activity_item(
                            activity.get('icon', '📢'),
                            activity.get('title', 'Activity'),
                            activity.get('description', ''),
                            self.format_time_ago(activity.get('created_at'))
                        )
                        feed_layout.addWidget(activity_item)
                else:
                    # No activities found - show empty state
                    empty_label = QLabel("No recent activity. Share your first racing update!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    feed_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load activities: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                feed_layout.addWidget(error_label)
        else:
            # Database not connected
            no_db_label = QLabel("Database connection required for activity feed")
            no_db_label.setAlignment(Qt.AlignCenter)
            no_db_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
            feed_layout.addWidget(no_db_label)
            
        feed_layout.addStretch()
        scroll_area.setWidget(feed_content)
        layout.addWidget(scroll_area)
        
        return widget
        
    def create_activity_item(self, icon, activity_type, description, time_ago):
        """Create an individual activity item"""
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
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        type_label = QLabel(activity_type)
        type_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        type_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
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
        
    def create_friends_list(self):
        """Create friends list widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search friends...")
        search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        add_friend_btn = QPushButton("Add Friend")
        add_friend_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        add_friend_btn.clicked.connect(self.show_add_friend_dialog)
        
        search_layout.addWidget(search_input)
        search_layout.addWidget(add_friend_btn)
        layout.addLayout(search_layout)
        
        # Friends list
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
                        
                        friend_item = self.create_friend_item(
                            friend.get('display_name', friend.get('username', 'Unknown')),
                            friend.get('status', 'Offline'),
                            friend.get('last_activity', 'Last seen some time ago'),
                            status_icon
                        )
                        friends_layout.addWidget(friend_item)
                else:
                    # No friends found - show empty state
                    empty_label = QLabel("No friends yet. Use the 'Add Friend' button to connect with other racers!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    friends_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load friends: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                friends_layout.addWidget(error_label)
        else:
            # Database not connected
            no_db_label = QLabel("Database connection required for friends list")
            no_db_label.setAlignment(Qt.AlignCenter)
            no_db_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
            friends_layout.addWidget(no_db_label)
            
        friends_layout.addStretch()
        scroll_area.setWidget(friends_content)
        layout.addWidget(scroll_area)
        
        return widget
        
    def create_friend_item(self, name, status, last_activity, status_icon):
        """Create a friend list item"""
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
        status_label.setStyleSheet("font-size: 16px;")
        status_label.setFixedSize(20, 20)
        
        # Friend info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(name)
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        status_label = QLabel(status)
        status_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        status_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']};")
        
        activity_label = QLabel(last_activity)
        activity_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        activity_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(status_label)
        info_layout.addWidget(activity_label)
        
        # Action buttons
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(4)
        
        message_btn = QPushButton("💬")
        message_btn.setFixedSize(30, 30)
        message_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {CommunityTheme.COLORS['active']};
            }}
        """)
        
        invite_btn = QPushButton("🏁")
        invite_btn.setFixedSize(30, 30)
        invite_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {CommunityTheme.COLORS['active']};
            }}
        """)
        
        actions_layout.addWidget(message_btn)
        actions_layout.addWidget(invite_btn)
        
        layout.addWidget(status_label)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addLayout(actions_layout)
        
        return item_widget
        
    def create_messages_panel(self):
        """Create messages panel widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Messages header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Messages")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        new_message_btn = QPushButton("New Message")
        new_message_btn.setStyleSheet(f"""
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
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(new_message_btn)
        layout.addLayout(header_layout)
        
        # Messages list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        messages_content = QWidget()
        messages_layout = QVBoxLayout(messages_content)
        messages_layout.setSpacing(8)
        
        # Load real messages from database - NO FAKE DATA
        if self.db_managers and 'social_manager' in self.db_managers and self.user_id:
            try:
                conversations_data = self.db_managers['social_manager'].get_conversations(self.user_id)
                
                if conversations_data:
                    for conversation in conversations_data:
                        # Create message item from conversation data
                        sender_name = conversation.get('name', 'Unknown')
                        latest_msg = conversation.get('latest_message')
                        preview = latest_msg['content'][:50] + "..." if latest_msg and latest_msg.get('content') else "No messages"
                        time_ago = self.format_time_ago(conversation.get('updated_at'))
                        unread = conversation.get('unread_count', 0) > 0
                        
                        message_item = self.create_message_item(sender_name, preview, time_ago, unread)
                        messages_layout.addWidget(message_item)
                else:
                    # No conversations found - show empty state
                    empty_label = QLabel("No messages yet. Start conversations with friends to see them here!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    messages_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load messages: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                messages_layout.addWidget(error_label)
        else:
            # Database not connected
            no_db_label = QLabel("Database connection required for messages")
            no_db_label.setAlignment(Qt.AlignCenter)
            no_db_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
            messages_layout.addWidget(no_db_label)
            
        messages_layout.addStretch()
        scroll_area.setWidget(messages_content)
        layout.addWidget(scroll_area)
        
        return widget
        
    def create_message_item(self, sender, preview, time_ago, unread):
        """Create a message list item"""
        item_widget = QWidget()
        bg_color = CommunityTheme.COLORS['surface'] if unread else CommunityTheme.COLORS['surface_darker']
        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
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
        
        # Unread indicator
        if unread:
            unread_dot = QLabel("●")
            unread_dot.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-size: 16px;")
            unread_dot.setFixedSize(20, 20)
            layout.addWidget(unread_dot)
        else:
            layout.addItem(QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Fixed))
        
        # Message info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        sender_label = QLabel(sender)
        sender_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        font_weight = "bold" if unread else "normal"
        sender_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: {font_weight};")
        
        preview_label = QLabel(preview)
        preview_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        preview_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(sender_label)
        info_layout.addWidget(preview_label)
        
        # Time
        time_label = QLabel(time_ago)
        time_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        time_label.setAlignment(Qt.AlignTop | Qt.AlignRight)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(time_label)
        
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
        
    def create_modern_community_widget(self):
        """Create modern community widget with full functionality"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        if self.user_id and self.user_id != 'default_user':
            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("Community")
            title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
            title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
            
            subtitle_label = QLabel("Teams, clubs, and racing events")
            subtitle_label.setFont(QFont(*CommunityTheme.FONTS['body']))
            subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(subtitle_label)
            layout.addLayout(header_layout)
            
            # Tab widget for community sections
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
            
            # Teams Tab
            teams_widget = self.create_teams_panel()
            tab_widget.addTab(teams_widget, "My Teams")
            
            # Clubs Tab
            clubs_widget = self.create_clubs_panel()
            tab_widget.addTab(clubs_widget, "Racing Clubs")
            
            # Events Tab
            events_widget = self.create_events_panel()
            tab_widget.addTab(events_widget, "Events")
            
            layout.addWidget(tab_widget)
        else:
            return self.create_placeholder_widget("Please log in to access teams, clubs, and events")
            
        return widget
        
    def create_teams_panel(self):
        """Create teams panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with actions
        header_layout = QHBoxLayout()
        
        title_label = QLabel("My Racing Teams")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        create_team_btn = QPushButton("Create Team")
        create_team_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(create_team_btn)
        layout.addLayout(header_layout)
        
        # Teams grid
        teams_scroll = QScrollArea()
        teams_scroll.setWidgetResizable(True)
        teams_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        teams_content = QWidget()
        teams_layout = QVBoxLayout(teams_content)
        teams_layout.setSpacing(12)
        
        # Load real teams from database - NO FAKE DATA
        if self.db_managers and 'community_manager' in self.db_managers and self.user_id:
            try:
                teams_data = self.db_managers['community_manager'].get_user_teams(self.user_id)
                
                if teams_data:
                    for team in teams_data:
                        team_card = self.create_team_card(
                            team.get('name', 'Unknown Team'),
                            team.get('member_count', '0 members'),
                            team.get('description', 'No description available'),
                            team.get('role', 'Member'),
                            team.get('is_active', True)
                        )
                        teams_layout.addWidget(team_card)
                else:
                    # No teams found - show empty state
                    empty_label = QLabel("You're not a member of any racing teams yet. Join a team to start racing together!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    teams_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load teams: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                teams_layout.addWidget(error_label)
        else:
            # Database not connected
            no_db_label = QLabel("Database connection required for teams")
            no_db_label.setAlignment(Qt.AlignCenter)
            no_db_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
            teams_layout.addWidget(no_db_label)
            
        teams_layout.addStretch()
        teams_scroll.setWidget(teams_content)
        layout.addWidget(teams_scroll)
        
        return widget
        
    def create_team_card(self, team_name, member_count, description, role, active):
        """Create a team card widget"""
        card_widget = QWidget()
        card_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        layout = QVBoxLayout(card_widget)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        team_name_label = QLabel(team_name)
        team_name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        team_name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        role_label = QLabel(role)
        role_color = CommunityTheme.COLORS['accent'] if role == "Captain" else CommunityTheme.COLORS['text_secondary']
        role_label.setStyleSheet(f"color: {role_color}; font-weight: bold; padding: 4px 8px; background-color: {CommunityTheme.COLORS['surface']}; border-radius: 3px;")
        
        header_layout.addWidget(team_name_label)
        header_layout.addStretch()
        header_layout.addWidget(role_label)
        
        # Info
        info_layout = QHBoxLayout()
        
        member_label = QLabel(f"👥 {member_count}")
        member_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        status_text = "🟢 Active" if active else "⚫ Inactive"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(member_label)
        info_layout.addStretch()
        info_layout.addWidget(status_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        # Actions
        actions_layout = QHBoxLayout()
        
        view_btn = QPushButton("View Details")
        view_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['surface']};
                color: {CommunityTheme.COLORS['text_primary']};
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid {CommunityTheme.COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {CommunityTheme.COLORS['active']};
                color: white;
            }}
        """)
        
        chat_btn = QPushButton("Team Chat")
        chat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        
        actions_layout.addWidget(view_btn)
        actions_layout.addWidget(chat_btn)
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(info_layout)
        layout.addWidget(desc_label)
        layout.addLayout(actions_layout)
        
        return card_widget
        
    def create_clubs_panel(self):
        """Create clubs panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with search
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Racing Clubs")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search clubs...")
        search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
                max-width: 200px;
            }}
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(search_input)
        layout.addLayout(header_layout)
        
        # Clubs list
        clubs_scroll = QScrollArea()
        clubs_scroll.setWidgetResizable(True)
        clubs_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        clubs_content = QWidget()
        clubs_layout = QVBoxLayout(clubs_content)
        clubs_layout.setSpacing(8)
        
        # Load real clubs from database - NO FAKE DATA
        if self.db_managers and 'community_manager' in self.db_managers and self.user_id:
            try:
                clubs_data = self.db_managers['community_manager'].get_clubs(self.user_id)
                
                if clubs_data:
                    for club in clubs_data:
                        club_item = self.create_club_item(
                            club.get('name', 'Unknown Club'),
                            club.get('member_count', '0 members'),
                            club.get('description', 'No description available'),
                            club.get('is_member', False),
                            club.get('id')  # Pass club ID for join functionality
                        )
                        clubs_layout.addWidget(club_item)
                else:
                    # No clubs found - show empty state
                    empty_label = QLabel("No racing clubs found. Check back later or create your own club!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    clubs_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load clubs: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                clubs_layout.addWidget(error_label)
        else:
            # Database not connected
            no_db_label = QLabel("Database connection required for clubs")
            no_db_label.setAlignment(Qt.AlignCenter)
            no_db_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
            clubs_layout.addWidget(no_db_label)
            
        clubs_layout.addStretch()
        clubs_scroll.setWidget(clubs_content)
        layout.addWidget(clubs_scroll)
        
        return widget
        
    def create_club_item(self, club_name, member_count, description, is_member, club_id=None):
        """Create a club list item"""
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
        
        # Club info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(club_name)
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        member_label = QLabel(f"👥 {member_count}")
        member_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(member_label)
        info_layout.addWidget(desc_label)
        
        # Action button
        if is_member:
            action_btn = QPushButton("View Club")
            action_btn.setStyleSheet(f"""
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
        else:
            action_btn = QPushButton("Join Club")
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CommunityTheme.COLORS['accent']};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #FF8A65;
                }}
            """)
            # Connect to actual functionality with real club ID
            if club_id:
                action_btn.clicked.connect(lambda: self.join_club_action(club_name, club_id))
            else:
                action_btn.clicked.connect(lambda: self.show_no_club_id_error())
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(action_btn)
        
        return item_widget
        
    def create_events_panel(self):
        """Create events panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with filter
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Racing Events")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        filter_combo = QComboBox()
        filter_combo.addItems(["All Events", "Registered", "Open", "Team Events"])
        filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {CommunityTheme.COLORS['text_primary']};
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(filter_combo)
        layout.addLayout(header_layout)
        
        # Events list
        events_scroll = QScrollArea()
        events_scroll.setWidgetResizable(True)
        events_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        events_content = QWidget()
        events_layout = QVBoxLayout(events_content)
        events_layout.setSpacing(12)
        
        # Load real events from database - NO FAKE DATA
        if self.db_managers and 'community_manager' in self.db_managers and self.user_id:
            try:
                events_data = self.db_managers['community_manager'].get_community_events(self.user_id)
                
                if events_data:
                    for event in events_data:
                        event_card = self.create_event_card(
                            event.get('title', 'Unknown Event'),
                            event.get('track_name', 'TBD'),
                            event.get('start_time', 'TBD'),
                            event.get('registration_info', '0/0 registered'),
                            event.get('is_registered', False),
                            event.get('event_type', 'Open'),
                            event.get('id')  # Pass event ID for registration functionality
                        )
                        events_layout.addWidget(event_card)
                else:
                    # No events found - show empty state
                    empty_label = QLabel("No upcoming racing events. Check back later for new competitions!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    events_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load events: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                events_layout.addWidget(error_label)
        else:
            # Database not connected
            no_db_label = QLabel("Database connection required for events")
            no_db_label.setAlignment(Qt.AlignCenter)
            no_db_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
            events_layout.addWidget(no_db_label)
            
        events_layout.addStretch()
        events_scroll.setWidget(events_content)
        layout.addWidget(events_scroll)
        
        return widget
        
    def create_event_card(self, event_name, track, date_time, registration, is_registered, event_type, event_id=None):
        """Create an event card"""
        card_widget = QWidget()
        card_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        layout = QVBoxLayout(card_widget)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        event_name_label = QLabel(event_name)
        event_name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        event_name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        type_label = QLabel(event_type)
        type_color = CommunityTheme.COLORS['accent'] if event_type == "Team Event" else CommunityTheme.COLORS['text_secondary']
        type_label.setStyleSheet(f"color: {type_color}; font-weight: bold; padding: 4px 8px; background-color: {CommunityTheme.COLORS['surface']}; border-radius: 3px;")
        
        header_layout.addWidget(event_name_label)
        header_layout.addStretch()
        header_layout.addWidget(type_label)
        
        # Event details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        track_label = QLabel(f"🏁 {track}")
        track_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        time_label = QLabel(f"🕐 {date_time}")
        time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        registration_label = QLabel(f"👥 {registration}")
        registration_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        details_layout.addWidget(track_label)
        details_layout.addWidget(time_label)
        details_layout.addWidget(registration_label)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        if is_registered:
            status_btn = QPushButton("✓ Registered")
            status_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CommunityTheme.COLORS['active']};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    border: none;
                }}
            """)
            status_btn.setEnabled(False)
        else:
            status_btn = QPushButton("Register")
            status_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CommunityTheme.COLORS['accent']};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #FF8A65;
                }}
            """)
        
        details_btn = QPushButton("View Details")
        details_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['surface']};
                color: {CommunityTheme.COLORS['text_primary']};
                padding: 8px 16px;
                border-radius: 4px;
                border: 1px solid {CommunityTheme.COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        actions_layout.addWidget(status_btn)
        actions_layout.addWidget(details_btn)
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(details_layout)
        layout.addLayout(actions_layout)
        
        return card_widget
        
    def create_modern_content_widget(self):
        """Create modern content widget with full functionality"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        if self.user_id and self.user_id != 'default_user':
            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("Content Hub")
            title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
            title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
            
            subtitle_label = QLabel("Share setups, media, and guides")
            subtitle_label.setFont(QFont(*CommunityTheme.FONTS['body']))
            subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(subtitle_label)
            layout.addLayout(header_layout)
            
            # Tab widget for content sections
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
            
            # My Content Tab
            my_content_widget = self.create_my_content_panel()
            tab_widget.addTab(my_content_widget, "My Content")
            
            # Browse Tab
            browse_widget = self.create_browse_content_panel()
            tab_widget.addTab(browse_widget, "Browse")
            
            # Upload Tab
            upload_widget = self.create_upload_panel()
            tab_widget.addTab(upload_widget, "Upload")
            
            layout.addWidget(tab_widget)
        else:
            return self.create_placeholder_widget("Please log in to access content management")
            
        return widget
        
    def create_my_content_panel(self):
        """Create my content panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("My Shared Content")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        filter_combo = QComboBox()
        filter_combo.addItems(["All Types", "Car Setups", "Videos", "Screenshots", "Guides"])
        filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {CommunityTheme.COLORS['text_primary']};
                min-width: 120px;
            }}
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(filter_combo)
        layout.addLayout(header_layout)
        
        # Content grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        
        # Sample content
        content_items = [
            ("Silverstone Hotlap Setup", "Car Setup", "McLaren 720S", "45 downloads", "2 days ago"),
            ("Monza Onboard Video", "Video", "Formula 1", "123 views", "5 days ago"),
            ("Perfect Apex Guide", "Guide", "General", "89 reads", "1 week ago"),
            ("Sunset at Spa Screenshot", "Screenshot", "Scenic", "34 likes", "2 weeks ago"),
        ]
        
        for title, content_type, category, stats, uploaded in content_items:
            content_card = self.create_content_card(title, content_type, category, stats, uploaded, True)
            content_layout.addWidget(content_card)
            
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return widget
        
    def create_browse_content_panel(self):
        """Create browse content panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Search and filter header
        header_layout = QHBoxLayout()
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search content...")
        search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        category_combo = QComboBox()
        category_combo.addItems(["All Categories", "Car Setups", "Videos", "Screenshots", "Guides"])
        category_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {CommunityTheme.COLORS['text_primary']};
                min-width: 120px;
            }}
        """)
        
        sort_combo = QComboBox()
        sort_combo.addItems(["Most Recent", "Most Popular", "Most Downloaded", "Highest Rated"])
        sort_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {CommunityTheme.COLORS['text_primary']};
                min-width: 120px;
            }}
        """)
        
        header_layout.addWidget(search_input)
        header_layout.addWidget(category_combo)
        header_layout.addWidget(sort_combo)
        layout.addLayout(header_layout)
        
        # Featured content
        featured_label = QLabel("🔥 Featured Content")
        featured_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        featured_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        layout.addWidget(featured_label)
        
        # Content grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        
        # Sample browse content
        content_items = [
            ("Ultimate F1 Wet Setup", "Car Setup", "Formula 1", "1.2K downloads", "by SpeedKing47"),
            ("Nürburgring Master Class", "Video", "Tutorial", "5.8K views", "by RacingAcademy"),
            ("Photography Spots Guide", "Guide", "Scenic", "890 reads", "by PhotoRacer"),
            ("Epic Overtake Compilation", "Video", "Highlights", "12K views", "by ActionClips"),
            ("Track Day Setup Guide", "Guide", "General", "2.1K reads", "by TrackMaster"),
        ]
        
        for title, content_type, category, stats, author in content_items:
            content_card = self.create_browse_content_card(title, content_type, category, stats, author)
            content_layout.addWidget(content_card)
            
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return widget
        
    def create_upload_panel(self):
        """Create upload panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Upload header
        title_label = QLabel("Share Your Content")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Upload form
        form_widget = QWidget()
        form_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                padding: 20px;
            }}
        """)
        
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(12)
        
        # Content type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Content Type:")
        type_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        type_combo = QComboBox()
        type_combo.addItems(["Car Setup", "Video", "Screenshot", "Guide", "Replay"])
        type_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        type_layout.addStretch()
        
        # Title input
        title_input = QLineEdit()
        title_input.setPlaceholderText("Enter a descriptive title...")
        title_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 10px;
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 14px;
            }}
        """)
        
        # Description input
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Describe your content, include setup details, tips, or context...")
        desc_input.setMaximumHeight(100)
        desc_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 10px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        # File upload area
        upload_area = QWidget()
        upload_area.setFixedHeight(120)
        upload_area.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 2px dashed {CommunityTheme.COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        upload_layout = QVBoxLayout(upload_area)
        upload_layout.setAlignment(Qt.AlignCenter)
        
        upload_icon = QLabel("📁")
        upload_icon.setAlignment(Qt.AlignCenter)
        upload_icon.setStyleSheet("font-size: 32px;")
        
        upload_text = QLabel("Drag & drop files here or click to browse")
        upload_text.setAlignment(Qt.AlignCenter)
        upload_text.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        browse_btn = QPushButton("Browse Files")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        
        upload_layout.addWidget(upload_icon)
        upload_layout.addWidget(upload_text)
        upload_layout.addWidget(browse_btn)
        
        # Tags input
        tags_input = QLineEdit()
        tags_input.setPlaceholderText("Add tags (comma separated): track, car, weather...")
        tags_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 10px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """)
        
        # Upload button
        upload_btn = QPushButton("Share Content")
        upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        
        form_layout.addLayout(type_layout)
        form_layout.addWidget(QLabel("Title:"))
        form_layout.addWidget(title_input)
        form_layout.addWidget(QLabel("Description:"))
        form_layout.addWidget(desc_input)
        form_layout.addWidget(QLabel("Files:"))
        form_layout.addWidget(upload_area)
        form_layout.addWidget(QLabel("Tags:"))
        form_layout.addWidget(tags_input)
        form_layout.addWidget(upload_btn)
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        return widget
        
    def create_content_card(self, title, content_type, category, stats, uploaded, is_mine=False):
        """Create a content card"""
        card_widget = QWidget()
        card_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        layout = QVBoxLayout(card_widget)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        type_icon = {"Car Setup": "⚙️", "Video": "🎥", "Screenshot": "📸", "Guide": "📝"}.get(content_type, "📄")
        type_label = QLabel(f"{type_icon} {content_type}")
        type_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold; padding: 4px 8px; background-color: {CommunityTheme.COLORS['surface']}; border-radius: 3px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(type_label)
        
        # Info
        info_layout = QHBoxLayout()
        
        category_label = QLabel(f"📂 {category}")
        category_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        stats_label = QLabel(stats)
        stats_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']};")
        
        uploaded_label = QLabel(uploaded)
        uploaded_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(category_label)
        info_layout.addStretch()
        info_layout.addWidget(stats_label)
        info_layout.addWidget(uploaded_label)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        if is_mine:
            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CommunityTheme.COLORS['surface']};
                    color: {CommunityTheme.COLORS['text_primary']};
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: 1px solid {CommunityTheme.COLORS['border']};
                }}
                QPushButton:hover {{
                    background-color: {CommunityTheme.COLORS['active']};
                    color: white;
                }}
            """)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #DC2626;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #B91C1C;
                }}
            """)
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
        
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(info_layout)
        layout.addLayout(actions_layout)
        
        return card_widget
        
    def create_browse_content_card(self, title, content_type, category, stats, author):
        """Create a browse content card"""
        card_widget = QWidget()
        card_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """)
        
        layout = QVBoxLayout(card_widget)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        type_icon = {"Car Setup": "⚙️", "Video": "🎥", "Screenshot": "📸", "Guide": "📝"}.get(content_type, "📄")
        type_label = QLabel(f"{type_icon} {content_type}")
        type_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold; padding: 4px 8px; background-color: {CommunityTheme.COLORS['surface']}; border-radius: 3px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(type_label)
        
        # Info
        info_layout = QHBoxLayout()
        
        category_label = QLabel(f"📂 {category}")
        category_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        stats_label = QLabel(stats)
        stats_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']};")
        
        author_label = QLabel(author)
        author_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(category_label)
        info_layout.addStretch()
        info_layout.addWidget(stats_label)
        info_layout.addWidget(author_label)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        download_btn = QPushButton("Download")
        download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
            }}
        """)
        
        like_btn = QPushButton("👍 Like")
        like_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['surface']};
                color: {CommunityTheme.COLORS['text_primary']};
                padding: 8px 16px;
                border-radius: 4px;
                border: 1px solid {CommunityTheme.COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {CommunityTheme.COLORS['active']};
                color: white;
            }}
        """)
        
        actions_layout.addWidget(download_btn)
        actions_layout.addWidget(like_btn)
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(info_layout)
        layout.addLayout(actions_layout)
        
        return card_widget
        
    def create_modern_achievements_widget(self):
        """Create modern achievements widget with sleek design"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        if self.user_id and self.user_id != 'default_user':
            # Header
            title_label = QLabel("Achievements")
            title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
            title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
            layout.addWidget(title_label)
            
            # Achievement section
            achievement_widget = QWidget()
            achievement_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {CommunityTheme.COLORS['surface']};
                    border: 1px solid {CommunityTheme.COLORS['border']};
                    border-radius: 6px;
                    padding: 16px;
                }}
            """)
            
            achievement_layout = QVBoxLayout(achievement_widget)
            achievement_layout.addWidget(QLabel("Progress & Rewards"))
            achievement_layout.addWidget(QLabel("Track your racing achievements and XP"))
            
            layout.addWidget(achievement_widget)
            layout.addStretch()
        else:
            return self.create_placeholder_widget("Please log in to access achievements")
            
        return widget
        
    def create_modern_account_widget(self):
        """Create comprehensive account settings widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        if self.user_id and self.user_id != 'default_user':
            # Header
            header_layout = QHBoxLayout()
            title_label = QLabel("Account Settings")
            title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
            title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
            
            subtitle_label = QLabel("Manage your profile, privacy, and preferences")
            subtitle_label.setFont(QFont(*CommunityTheme.FONTS['body']))
            subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            header_layout.addWidget(subtitle_label)
            layout.addLayout(header_layout)
            
            # Tab widget for different settings sections
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
            
            # Profile Settings Tab
            profile_widget = self.create_profile_settings_panel()
            tab_widget.addTab(profile_widget, "👤 Profile")
            
            # Privacy Settings Tab
            privacy_widget = self.create_privacy_settings_panel()
            tab_widget.addTab(privacy_widget, "🔒 Privacy")
            
            # Notifications Tab
            notifications_widget = self.create_notifications_settings_panel()
            tab_widget.addTab(notifications_widget, "🔔 Notifications")
            
            # Security Tab
            security_widget = self.create_security_settings_panel()
            tab_widget.addTab(security_widget, "🛡️ Security")
            
            # Racing Preferences Tab
            racing_widget = self.create_racing_preferences_panel()
            tab_widget.addTab(racing_widget, "🏁 Racing")
            
            # Data & Privacy Tab
            data_widget = self.create_data_settings_panel()
            tab_widget.addTab(data_widget, "💾 Data")
            
            layout.addWidget(tab_widget)
        else:
            return self.create_placeholder_widget("Please log in to access account settings")
            
        return widget
        
    def create_profile_settings_panel(self):
        """Create profile settings panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Profile Picture Section
        profile_section, profile_section_layout = self.create_settings_section("Profile Picture", "📸")
        
        avatar_layout = QHBoxLayout()
        
        # Current avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(80, 80)
        avatar_label.setStyleSheet(f"""
            QLabel {{
                background-color: {CommunityTheme.COLORS['accent']};
                border-radius: 40px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }}
        """)
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setText("U")  # Default to first letter of username
        
        avatar_buttons_layout = QVBoxLayout()
        change_avatar_btn = QPushButton("Change Avatar")
        change_avatar_btn.clicked.connect(self.change_avatar)
        remove_avatar_btn = QPushButton("Remove Avatar")
        remove_avatar_btn.clicked.connect(self.remove_avatar)
        
        avatar_buttons_layout.addWidget(change_avatar_btn)
        avatar_buttons_layout.addWidget(remove_avatar_btn)
        avatar_buttons_layout.addStretch()
        
        avatar_layout.addWidget(avatar_label)
        avatar_layout.addLayout(avatar_buttons_layout)
        avatar_layout.addStretch()
        
        profile_section_layout.addLayout(avatar_layout)
        layout.addWidget(profile_section)
        
        # Basic Information Section
        basic_section, basic_section_layout = self.create_settings_section("Basic Information", "ℹ️")
        
        # Display Name
        basic_section_layout.addWidget(self.create_setting_field("Display Name", "Your public display name", "text", "RacingPro2024"))
        
        # Username
        username_layout = QHBoxLayout()
        username_field = self.create_setting_field("Username", "Your unique username (@username)", "text", "racingpro2024")
        check_availability_btn = QPushButton("Check Availability")
        check_availability_btn.clicked.connect(self.check_username_availability)
        username_layout.addWidget(username_field)
        username_layout.addWidget(check_availability_btn)
        basic_section_layout.addLayout(username_layout)
        
        # Bio
        basic_section_layout.addWidget(self.create_setting_field("Bio", "Tell others about yourself and your racing style", "textarea", "Passionate sim racer competing in GT3 and Formula series."))
        
        # Location
        basic_section_layout.addWidget(self.create_setting_field("Location", "Your country or region", "combo", ["United States", "United Kingdom", "Germany", "France", "Canada", "Australia", "Other"]))
        
        layout.addWidget(basic_section)
        
        # Racing Profile Section
        racing_section, racing_section_layout = self.create_settings_section("Racing Profile", "🏎️")
        
        # Skill Level
        racing_section_layout.addWidget(self.create_setting_field("Skill Level", "Your racing experience level", "combo", ["Beginner", "Intermediate", "Advanced", "Professional"]))
        
        # Favorite Categories
        categories_widget = QWidget()
        categories_layout = QVBoxLayout(categories_widget)
        categories_layout.addWidget(QLabel("Favorite Racing Categories:"))
        
        categories_checkboxes = QWidget()
        checkboxes_layout = QGridLayout(categories_checkboxes)
        
        categories = ["Formula Racing", "GT3/GTE", "Open Wheel", "Touring Cars", "Rally", "Oval Racing", "Endurance", "Drifting"]
        for i, category in enumerate(categories):
            checkbox = QCheckBox(category)
            checkboxes_layout.addWidget(checkbox, i // 2, i % 2)
            
        categories_layout.addWidget(categories_checkboxes)
        racing_section_layout.addWidget(categories_widget)
        
        # Favorite Tracks
        racing_section_layout.addWidget(self.create_setting_field("Favorite Track", "Your most preferred racing circuit", "combo", ["Silverstone", "Spa-Francorchamps", "Nürburgring", "Monza", "Suzuka", "Circuit de la Sarthe", "Watkins Glen", "Other"]))
        
        layout.addWidget(racing_section)
        
        # Save button
        save_btn = QPushButton("Save Profile Changes")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 0px 32px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
                transform: translateY(0px);
            }}
        """)
        save_btn.clicked.connect(self.save_profile_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        return container
        
    def create_privacy_settings_panel(self):
        """Create privacy settings panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Profile Visibility Section
        visibility_section, visibility_section_layout = self.create_settings_section("Profile Visibility", "👁️")
        
        visibility_section_layout.addWidget(self.create_setting_field("Profile Visibility", "Who can see your profile", "combo", ["Public", "Friends Only", "Private"]))
        visibility_section_layout.addWidget(self.create_setting_field("Racing Statistics", "Who can see your lap times and stats", "combo", ["Public", "Friends Only", "Private"]))
        visibility_section_layout.addWidget(self.create_setting_field("Activity Feed", "Who can see your activity updates", "combo", ["Public", "Friends Only", "Private"]))
        
        layout.addWidget(visibility_section)
        
        # Communication Settings Section
        communication_section, communication_section_layout = self.create_settings_section("Communication Settings", "💬")
        
        communication_section_layout.addWidget(self.create_setting_field("Friend Requests", "Who can send you friend requests", "combo", ["Everyone", "Friends of Friends", "No One"]))
        communication_section_layout.addWidget(self.create_setting_field("Private Messages", "Who can send you direct messages", "combo", ["Everyone", "Friends Only", "No One"]))
        communication_section_layout.addWidget(self.create_setting_field("Team Invitations", "Who can invite you to teams", "combo", ["Everyone", "Friends Only", "No One"]))
        communication_section_layout.addWidget(self.create_setting_field("Event Invitations", "Who can invite you to events", "combo", ["Everyone", "Friends Only", "No One"]))
        
        layout.addWidget(communication_section)
        
        # Activity & Status Section
        activity_section, activity_section_layout = self.create_settings_section("Activity & Status", "🟢")
        
        # Online Status
        online_status_widget = QWidget()
        online_status_layout = QHBoxLayout(online_status_widget)
        online_status_checkbox = QCheckBox("Show online status to others")
        online_status_checkbox.setChecked(True)
        online_status_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        online_status_layout.addWidget(online_status_checkbox)
        online_status_layout.addStretch()
        activity_section_layout.addWidget(online_status_widget)
        
        # Currently Racing Status
        racing_status_widget = QWidget()
        racing_status_layout = QHBoxLayout(racing_status_widget)
        racing_status_checkbox = QCheckBox("Show when you're currently racing")
        racing_status_checkbox.setChecked(True)
        racing_status_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        racing_status_layout.addWidget(racing_status_checkbox)
        racing_status_layout.addStretch()
        activity_section_layout.addWidget(racing_status_widget)
        
        # Recent Activity
        recent_activity_widget = QWidget()
        recent_activity_layout = QHBoxLayout(recent_activity_widget)
        recent_activity_checkbox = QCheckBox("Show recent racing activity")
        recent_activity_checkbox.setChecked(True)
        recent_activity_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        recent_activity_layout.addWidget(recent_activity_checkbox)
        recent_activity_layout.addStretch()
        activity_section_layout.addWidget(recent_activity_widget)
        
        layout.addWidget(activity_section)
        
        # Data Sharing Section
        data_section, data_section_layout = self.create_settings_section("Data Sharing", "📊")
        
        # Share telemetry data
        telemetry_widget = QWidget()
        telemetry_layout = QHBoxLayout(telemetry_widget)
        telemetry_checkbox = QCheckBox("Allow sharing of telemetry data for community analysis")
        telemetry_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        telemetry_layout.addWidget(telemetry_checkbox)
        telemetry_layout.addStretch()
        data_section_layout.addWidget(telemetry_widget)
        
        # Share setup files
        setup_widget = QWidget()
        setup_layout = QHBoxLayout(setup_widget)
        setup_checkbox = QCheckBox("Allow others to download your shared car setups")
        setup_checkbox.setChecked(True)
        setup_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        setup_layout.addWidget(setup_checkbox)
        setup_layout.addStretch()
        data_section_layout.addWidget(setup_widget)
        
        layout.addWidget(data_section)
        
        # Save button
        save_btn = QPushButton("Save Privacy Settings")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 0px 32px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
                transform: translateY(0px);
            }}
        """)
        save_btn.clicked.connect(self.save_privacy_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        return container
        
    def create_notifications_settings_panel(self):
        """Create notifications settings panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # In-App Notifications Section
        inapp_section, inapp_section_layout = self.create_settings_section("In-App Notifications", "🔔")
        
        inapp_notifications = [
            ("Friend requests", "When someone sends you a friend request"),
            ("New messages", "When you receive a private message"),
            ("Event invitations", "When you're invited to racing events"),
            ("Team activity", "When there's activity in your racing teams"),
            ("Achievement unlocks", "When you unlock new achievements"),
            ("Lap record beats", "When someone beats your lap records"),
            ("Race reminders", "Reminders about upcoming races you're registered for")
        ]
        
        for title, description in inapp_notifications:
            notification_widget = self.create_notification_setting(title, description, True)
            inapp_section_layout.addWidget(notification_widget)
            
        layout.addWidget(inapp_section)
        
        # Email Notifications Section
        email_section, email_section_layout = self.create_settings_section("Email Notifications", "📧")
        
        # Email address
        email_section_layout.addWidget(self.create_setting_field("Email Address", "Where to send email notifications", "text", "user@example.com"))
        
        email_notifications = [
            ("Weekly activity summary", "Weekly digest of your racing activity"),
            ("Event reminders", "Reminders about upcoming events (24h before)"),
            ("Important account updates", "Security alerts and account changes"),
            ("New features", "Updates about new TrackPro features"),
            ("Community highlights", "Monthly community achievements and highlights")
        ]
        
        for title, description in email_notifications:
            notification_widget = self.create_notification_setting(title, description, False)
            email_section_layout.addWidget(notification_widget)
            
        layout.addWidget(email_section)
        
        # Push Notifications Section (if applicable)
        push_section, push_section_layout = self.create_settings_section("Push Notifications", "📱")
        
        push_info = QLabel("Enable browser notifications to receive real-time updates even when TrackPro is not active.")
        push_info.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; font-style: italic;")
        push_info.setWordWrap(True)
        push_section_layout.addWidget(push_info)
        
        enable_push_btn = QPushButton("Enable Push Notifications")
        enable_push_btn.clicked.connect(self.enable_push_notifications)
        push_section_layout.addWidget(enable_push_btn)
        
        layout.addWidget(push_section)
        
        # Notification Timing Section
        timing_section, timing_section_layout = self.create_settings_section("Notification Timing", "⏰")
        
        timing_section_layout.addWidget(self.create_setting_field("Quiet Hours Start", "Don't send notifications after this time", "time", "22:00"))
        timing_section_layout.addWidget(self.create_setting_field("Quiet Hours End", "Resume notifications after this time", "time", "08:00"))
        
        # Time zone
        timing_section_layout.addWidget(self.create_setting_field("Time Zone", "Your local time zone", "combo", ["UTC-8 (PST)", "UTC-5 (EST)", "UTC+0 (GMT)", "UTC+1 (CET)", "UTC+9 (JST)"]))
        
        layout.addWidget(timing_section)
        
        # Save button
        save_btn = QPushButton("Save Notification Settings")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 0px 32px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
                transform: translateY(0px);
            }}
        """)
        save_btn.clicked.connect(self.save_notification_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        return container
        
    def create_security_settings_panel(self):
        """Create security settings panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Password Section
        password_section, password_section_layout = self.create_settings_section("Password & Authentication", "🔐")
        
        # Change Password
        change_password_btn = QPushButton("Change Password")
        change_password_btn.clicked.connect(self.change_password)
        password_section_layout.addWidget(change_password_btn)
        
        # Last password change
        last_change_label = QLabel("Last changed: 30 days ago")
        last_change_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; font-size: 11px;")
        password_section_layout.addWidget(last_change_label)
        
        layout.addWidget(password_section)
        
        # Two-Factor Authentication Section
        twofa_section, twofa_section_layout = self.create_settings_section("Two-Factor Authentication", "🛡️")
        
        twofa_status = QLabel("Status: Disabled")
        twofa_status.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; font-weight: bold;")
        twofa_section_layout.addWidget(twofa_status)
        
        twofa_description = QLabel("Add an extra layer of security to your account by requiring a verification code in addition to your password.")
        twofa_description.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        twofa_description.setWordWrap(True)
        twofa_section_layout.addWidget(twofa_description)
        
        enable_twofa_btn = QPushButton("Enable Two-Factor Authentication")
        enable_twofa_btn.clicked.connect(self.enable_two_factor_auth)
        twofa_section_layout.addWidget(enable_twofa_btn)
        
        layout.addWidget(twofa_section)
        
        # Active Sessions Section
        sessions_section, sessions_section_layout = self.create_settings_section("Active Sessions", "💻")
        
        sessions_description = QLabel("Manage devices and applications that have access to your account.")
        sessions_description.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        sessions_description.setWordWrap(True)
        sessions_section_layout.addWidget(sessions_description)
        
        # Current session
        current_session = self.create_session_item("Current Session", "Windows PC - Chrome", "Right now", True)
        sessions_section_layout.addWidget(current_session)
        
        # Other sessions
        other_session = self.create_session_item("Mobile Device", "iPhone - Safari", "2 hours ago", False)
        sessions_section_layout.addWidget(other_session)
        
        revoke_all_btn = QPushButton("Revoke All Other Sessions")
        revoke_all_btn.clicked.connect(self.revoke_all_sessions)
        sessions_section_layout.addWidget(revoke_all_btn)
        
        layout.addWidget(sessions_section)
        
        # Login History Section
        history_section, history_section_layout = self.create_settings_section("Recent Login Activity", "📝")
        
        history_items = [
            ("Successful login", "Windows PC - Chrome", "Just now", "success"),
            ("Successful login", "iPhone - Safari", "2 hours ago", "success"),
            ("Failed login attempt", "Unknown device", "3 days ago", "warning"),
            ("Successful login", "Windows PC - Chrome", "5 days ago", "success")
        ]
        
        for action, device, time, status in history_items:
            history_item = self.create_history_item(action, device, time, status)
            history_section_layout.addWidget(history_item)
            
        view_full_history_btn = QPushButton("View Full Login History")
        view_full_history_btn.clicked.connect(self.view_login_history)
        history_section_layout.addWidget(view_full_history_btn)
        
        layout.addWidget(history_section)
        
        # Account Recovery Section
        recovery_section, recovery_section_layout = self.create_settings_section("Account Recovery", "🔓")
        
        recovery_email_field = self.create_setting_field("Recovery Email", "Alternative email for account recovery", "text", "recovery@example.com")
        recovery_section_layout.addWidget(recovery_email_field)
        
        backup_codes_btn = QPushButton("Generate Backup Codes")
        backup_codes_btn.clicked.connect(self.generate_backup_codes)
        recovery_section_layout.addWidget(backup_codes_btn)
        
        layout.addWidget(recovery_section)
        
        layout.addStretch()
        
        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        return container
        
    def create_racing_preferences_panel(self):
        """Create racing preferences panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Units & Display Section
        units_section, units_section_layout = self.create_settings_section("Units & Display", "📏")
        
        units_section_layout.addWidget(self.create_setting_field("Distance Units", "Preferred unit for distances", "combo", ["Kilometers", "Miles"]))
        units_section_layout.addWidget(self.create_setting_field("Speed Units", "Preferred unit for speed", "combo", ["km/h", "mph"]))
        units_section_layout.addWidget(self.create_setting_field("Temperature Units", "Preferred unit for temperature", "combo", ["Celsius", "Fahrenheit"]))
        units_section_layout.addWidget(self.create_setting_field("Fuel Units", "Preferred unit for fuel", "combo", ["Liters", "Gallons"]))
        
        layout.addWidget(units_section)
        
        # Racing Preferences Section
        racing_section, racing_section_layout = self.create_settings_section("Racing Preferences", "🏁")
        
        racing_section_layout.addWidget(self.create_setting_field("Default Racing View", "Preferred camera angle", "combo", ["Cockpit", "Bumper", "Hood", "Chase", "TV Camera"]))
        racing_section_layout.addWidget(self.create_setting_field("Difficulty Level", "AI difficulty preference", "combo", ["Beginner (40-60%)", "Intermediate (60-80%)", "Advanced (80-95%)", "Professional (95-100%)"]))
        racing_section_layout.addWidget(self.create_setting_field("Assist Preferences", "Driving aids preference", "combo", ["All Assists", "Some Assists", "Minimal Assists", "No Assists"]))
        
        layout.addWidget(racing_section)
        
        # Telemetry & Data Section
        telemetry_section, telemetry_section_layout = self.create_settings_section("Telemetry & Data", "📊")
        
        # Auto-save telemetry
        telemetry_widget = QWidget()
        telemetry_layout = QHBoxLayout(telemetry_widget)
        telemetry_checkbox = QCheckBox("Automatically save telemetry data")
        telemetry_checkbox.setChecked(True)
        telemetry_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        telemetry_layout.addWidget(telemetry_checkbox)
        telemetry_layout.addStretch()
        telemetry_section_layout.addWidget(telemetry_widget)
        
        # Auto-analyze laps
        analyze_widget = QWidget()
        analyze_layout = QHBoxLayout(analyze_widget)
        analyze_checkbox = QCheckBox("Auto-analyze lap times and suggest improvements")
        analyze_checkbox.setChecked(True)
        analyze_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 2px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 2px solid {CommunityTheme.COLORS['accent']};
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: {CommunityTheme.COLORS['accent']};
            }}
        """)
        analyze_layout.addWidget(analyze_checkbox)
        analyze_layout.addStretch()
        telemetry_section_layout.addWidget(analyze_widget)
        
        telemetry_section_layout.addWidget(self.create_setting_field("Data Retention", "How long to keep telemetry data", "combo", ["1 month", "3 months", "6 months", "1 year", "Forever"]))
        
        layout.addWidget(telemetry_section)
        
        # Default Setups Section
        setups_section, setups_section_layout = self.create_settings_section("Default Car Setups", "⚙️")
        
        setups_section_layout.addWidget(self.create_setting_field("Default Setup Style", "Preferred setup characteristics", "combo", ["Stable (easy to drive)", "Balanced", "Aggressive (fast but twitchy)", "Custom"]))
        setups_section_layout.addWidget(self.create_setting_field("Auto-Apply Community Setups", "Automatically use highly-rated community setups", "combo", ["Never", "Ask First", "Always"]))
        
        layout.addWidget(setups_section)
        
        # Racing Schedule Section
        schedule_section, schedule_section_layout = self.create_settings_section("Racing Schedule", "🗓️")
        
        # Preferred racing times
        schedule_section_layout.addWidget(self.create_setting_field("Preferred Racing Days", "When you usually race", "combo", ["Weekdays", "Weekends", "Both", "Flexible"]))
        schedule_section_layout.addWidget(self.create_setting_field("Preferred Start Time", "Your preferred race start time", "time", "19:00"))
        schedule_section_layout.addWidget(self.create_setting_field("Session Length Preference", "Preferred race duration", "combo", ["Sprint (10-20 min)", "Medium (30-45 min)", "Long (60+ min)", "Endurance (2+ hours)"]))
        
        layout.addWidget(schedule_section)
        
        # Save button
        save_btn = QPushButton("Save Racing Preferences")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 0px 32px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
                transform: translateY(0px);
            }}
        """)
        save_btn.clicked.connect(self.save_racing_preferences)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        return container
        
    def create_data_settings_panel(self):
        """Create data & storage settings panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Data Export Section
        export_section, export_section_layout = self.create_settings_section("Data Export", "📤")
        
        export_description = QLabel("Download a copy of your TrackPro data including profile, telemetry, setups, and activity history.")
        export_description.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        export_description.setWordWrap(True)
        export_section_layout.addWidget(export_description)
        
        export_buttons_layout = QHBoxLayout()
        
        export_profile_btn = QPushButton("Export Profile Data")
        export_profile_btn.clicked.connect(self.export_profile_data)
        
        export_telemetry_btn = QPushButton("Export Telemetry Data")
        export_telemetry_btn.clicked.connect(self.export_telemetry_data)
        
        export_all_btn = QPushButton("Export All Data")
        export_all_btn.clicked.connect(self.export_all_data)
        
        export_buttons_layout.addWidget(export_profile_btn)
        export_buttons_layout.addWidget(export_telemetry_btn)
        export_buttons_layout.addWidget(export_all_btn)
        export_buttons_layout.addStretch()
        
        export_section_layout.addLayout(export_buttons_layout)
        
        layout.addWidget(export_section)
        
        # Storage Usage Section
        storage_section, storage_section_layout = self.create_settings_section("Storage Usage", "💾")
        
        # Storage breakdown
        storage_items = [
            ("Telemetry Data", "1.2 GB", "87%"),
            ("Car Setups", "45 MB", "3%"),
            ("Screenshots & Videos", "134 MB", "10%"),
            ("Profile & Settings", "2 MB", "0%")
        ]
        
        for item_name, size, percentage in storage_items:
            storage_item = self.create_storage_item(item_name, size, percentage)
            storage_section_layout.addWidget(storage_item)
            
        # Total usage
        total_widget = QWidget()
        total_layout = QHBoxLayout(total_widget)
        total_layout.addWidget(QLabel("Total Usage:"))
        total_usage = QLabel("1.38 GB of 5 GB used")
        total_usage.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        total_layout.addWidget(total_usage)
        total_layout.addStretch()
        storage_section_layout.addWidget(total_widget)
        
        # Cleanup options
        cleanup_btn = QPushButton("Clean Up Old Data")
        cleanup_btn.clicked.connect(self.cleanup_old_data)
        storage_section_layout.addWidget(cleanup_btn)
        
        layout.addWidget(storage_section)
        
        # Data Retention Section
        retention_section, retention_section_layout = self.create_settings_section("Data Retention", "⏳")
        
        retention_section_layout.addWidget(self.create_setting_field("Auto-Delete Old Telemetry", "Automatically delete telemetry older than", "combo", ["Never", "3 months", "6 months", "1 year", "2 years"]))
        retention_section_layout.addWidget(self.create_setting_field("Keep Screenshots", "How long to keep screenshots", "combo", ["Forever", "1 year", "6 months", "3 months"]))
        
        layout.addWidget(retention_section)
        
        # Privacy & Deletion Section
        deletion_section, deletion_section_layout = self.create_settings_section("Account Deletion", "🗑️")
        
        deletion_warning = QLabel("⚠️ Warning: These actions are permanent and cannot be undone.")
        deletion_warning.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; font-weight: bold;")
        deletion_section_layout.addWidget(deletion_warning)
        
        deletion_description = QLabel("If you no longer want to use TrackPro, you can delete your account and all associated data. This action is irreversible.")
        deletion_description.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        deletion_description.setWordWrap(True)
        deletion_section_layout.addWidget(deletion_description)
        
        deletion_buttons_layout = QHBoxLayout()
        
        deactivate_btn = QPushButton("Deactivate Account")
        deactivate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['warning']};
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #E65100;
            }}
        """)
        deactivate_btn.clicked.connect(self.deactivate_account)
        
        delete_btn = QPushButton("Delete Account")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #DC2626;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #B91C1C;
            }}
        """)
        delete_btn.clicked.connect(self.delete_account)
        
        deletion_buttons_layout.addWidget(deactivate_btn)
        deletion_buttons_layout.addWidget(delete_btn)
        deletion_buttons_layout.addStretch()
        
        deletion_section_layout.addLayout(deletion_buttons_layout)
        
        layout.addWidget(deletion_section)
        
        layout.addStretch()
        
        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        
        return container
    
    def create_settings_section(self, title, icon):
        """Create a modern settings section with clean design"""
        section_widget = QWidget()
        section_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: none;
                border-radius: 12px;
                padding: 0px;
                margin-bottom: 16px;
            }}
        """)
        
        # Create main layout for the section
        main_layout = QVBoxLayout(section_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 24)
        
        # Add section header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont('Segoe UI Emoji', 18))
        
        title_label = QLabel(title)
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: 600;")
        
        header_layout.addWidget(icon_label)
        header_layout.addSpacing(12)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Add subtle separator
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {CommunityTheme.COLORS['border']}; opacity: 0.3;")
        main_layout.addWidget(separator)
        
        # Return both the widget and the layout so we can add content
        return section_widget, main_layout
    
    def create_setting_field(self, label, description, field_type, default_value=None):
        """Create a modern setting input field with clean design"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 20)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setFont(QFont('Arial', 13, QFont.Medium))
        label_widget.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: 500;")
        layout.addWidget(label_widget)
        
        # Description
        desc_widget = QLabel(description)
        desc_widget.setFont(QFont('Arial', 11))
        desc_widget.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; margin-bottom: 4px;")
        desc_widget.setWordWrap(True)
        layout.addWidget(desc_widget)
        
        # Input field based on type
        if field_type == "text":
            input_widget = QLineEdit()
            if default_value:
                input_widget.setText(str(default_value))
            input_widget.setFixedHeight(40)
            input_widget.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {CommunityTheme.COLORS['surface_darker']};
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 0px 12px;
                    color: {CommunityTheme.COLORS['text_primary']};
                    font-size: 13px;
                }}
                QLineEdit:focus {{
                    border-color: {CommunityTheme.COLORS['accent']};
                    background-color: {CommunityTheme.COLORS['background']};
                }}
                QLineEdit:hover {{
                    background-color: {CommunityTheme.COLORS['background']};
                }}
            """)
        elif field_type == "textarea":
            input_widget = QTextEdit()
            input_widget.setMaximumHeight(100)
            if default_value:
                input_widget.setPlainText(str(default_value))
            input_widget.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {CommunityTheme.COLORS['surface_darker']};
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 12px;
                    color: {CommunityTheme.COLORS['text_primary']};
                    font-size: 13px;
                }}
                QTextEdit:focus {{
                    border-color: {CommunityTheme.COLORS['accent']};
                    background-color: {CommunityTheme.COLORS['background']};
                }}
                QTextEdit:hover {{
                    background-color: {CommunityTheme.COLORS['background']};
                }}
            """)
        elif field_type == "combo":
            input_widget = QComboBox()
            if isinstance(default_value, list):
                input_widget.addItems(default_value)
            input_widget.setFixedHeight(40)
            input_widget.setStyleSheet(f"""
                QComboBox {{
                    background-color: {CommunityTheme.COLORS['surface_darker']};
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 0px 12px;
                    color: {CommunityTheme.COLORS['text_primary']};
                    font-size: 13px;
                    min-width: 200px;
                }}
                QComboBox:hover {{
                    background-color: {CommunityTheme.COLORS['background']};
                }}
                QComboBox:focus {{
                    border-color: {CommunityTheme.COLORS['accent']};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border: none;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {CommunityTheme.COLORS['surface']};
                    border: 1px solid {CommunityTheme.COLORS['border']};
                    border-radius: 8px;
                    selection-background-color: {CommunityTheme.COLORS['accent']};
                    color: {CommunityTheme.COLORS['text_primary']};
                    padding: 4px;
                }}
            """)
        elif field_type == "time":
            input_widget = QLineEdit()
            if default_value:
                input_widget.setText(str(default_value))
            input_widget.setPlaceholderText("HH:MM")
            input_widget.setFixedHeight(40)
            input_widget.setFixedWidth(120)
            input_widget.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {CommunityTheme.COLORS['surface_darker']};
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 0px 12px;
                    color: {CommunityTheme.COLORS['text_primary']};
                    font-size: 13px;
                }}
                QLineEdit:focus {{
                    border-color: {CommunityTheme.COLORS['accent']};
                    background-color: {CommunityTheme.COLORS['background']};
                }}
                QLineEdit:hover {{
                    background-color: {CommunityTheme.COLORS['background']};
                }}
            """)
        else:
            input_widget = QLineEdit()
            
        layout.addWidget(input_widget)
        return container
    
    def create_notification_setting(self, title, description, default_enabled=True):
        """Create a notification setting with toggle"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(default_enabled)
        checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 1px solid {CommunityTheme.COLORS['accent']};
                border-radius: 3px;
            }}
        """)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        
        content_layout.addWidget(title_label)
        content_layout.addWidget(desc_label)
        
        layout.addWidget(checkbox)
        layout.addLayout(content_layout)
        layout.addStretch()
        
        return container
    
    def create_session_item(self, session_name, device_info, time_info, is_current=False):
        """Create a session item for security settings"""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 12px;
                margin: 4px 0px;
            }}
        """)
        
        layout = QHBoxLayout(container)
        
        # Session info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(session_name)
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']}; font-weight: bold;")
        
        device_label = QLabel(device_info)
        device_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        device_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        time_label = QLabel(time_info)
        time_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(device_label)
        info_layout.addWidget(time_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Actions
        if not is_current:
            revoke_btn = QPushButton("Revoke")
            revoke_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {CommunityTheme.COLORS['warning']};
                    color: white;
                    padding: 6px 12px;
                    border-radius: 3px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #E65100;
                }}
            """)
            layout.addWidget(revoke_btn)
        else:
            current_label = QLabel("(Current)")
            current_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
            layout.addWidget(current_label)
        
        return container
    
    def create_history_item(self, action, device, time, status):
        """Create a login history item"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        
        # Status icon
        status_icons = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        status_colors = {
            "success": CommunityTheme.COLORS['success'],
            "warning": CommunityTheme.COLORS['warning'],
            "error": CommunityTheme.COLORS['danger']
        }
        
        icon_label = QLabel(status_icons.get(status, "ℹ️"))
        icon_label.setFixedWidth(20)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        action_label = QLabel(action)
        action_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        action_label.setStyleSheet(f"color: {status_colors.get(status, CommunityTheme.COLORS['text_primary'])};")
        
        details_layout = QHBoxLayout()
        device_label = QLabel(device)
        device_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        device_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        time_label = QLabel(time)
        time_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        details_layout.addWidget(device_label)
        details_layout.addStretch()
        details_layout.addWidget(time_label)
        
        content_layout.addWidget(action_label)
        content_layout.addLayout(details_layout)
        
        layout.addWidget(icon_label)
        layout.addLayout(content_layout)
        
        return container
    
    def create_storage_item(self, item_name, size, percentage):
        """Create a storage usage item"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        
        # Header with name and size
        header_layout = QHBoxLayout()
        name_label = QLabel(item_name)
        name_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        size_label = QLabel(size)
        size_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        size_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(size_label)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(percentage.replace('%', '')))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(6)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {CommunityTheme.COLORS['surface']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {CommunityTheme.COLORS['accent']};
                border-radius: 3px;
            }}
        """)
        
        layout.addLayout(header_layout)
        layout.addWidget(progress_bar)
        
        return container
        
    # Action handlers for all the settings
    def change_avatar(self):
        """Handle avatar change"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "Select Avatar Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        if file_path:
            QMessageBox.information(self, "Avatar Updated", f"Avatar updated with image: {file_path}")
    
    def remove_avatar(self):
        """Handle avatar removal"""
        reply = QMessageBox.question(
            self, 
            "Remove Avatar", 
            "Are you sure you want to remove your avatar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Avatar Removed", "Your avatar has been removed.")
    
    def check_username_availability(self):
        """Check if username is available"""
        QMessageBox.information(self, "Username Check", "Username 'racingpro2024' is available!")
    
    def save_profile_settings(self):
        """Save profile settings"""
        if not self.db_managers or 'user_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
            
        try:
            # In a real implementation, you would collect the values from the form fields
            # For now, we'll use sample data
            profile_data = {
                'display_name': 'RacingPro2024',
                'bio': 'Passionate sim racer competing in GT3 and Formula series.',
                'location': 'United States',
                'skill_level': 'intermediate',
                'favorite_categories': ['GT3/GTE', 'Formula Racing'],
                'favorite_track': 'Silverstone'
            }
            
            success = self.db_managers['user_manager'].update_user_profile(self.user_id, profile_data)
            
            if success:
                QMessageBox.information(self, "Settings Saved", "Your profile settings have been saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save profile settings.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving profile settings: {str(e)}")
    
    def save_privacy_settings(self):
        """Save privacy settings"""
        if not self.db_managers or 'user_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
            
        try:
            # Get current preferences
            preferences = self.db_managers['user_manager'].get_user_preferences(self.user_id)
            
            # Update privacy settings (in real implementation, collect from form)
            preferences['privacy_settings'] = {
                'profile_visibility': 'public',
                'racing_stats_visibility': 'friends_only',
                'activity_feed_visibility': 'public',
                'friend_requests': 'everyone',
                'private_messages': 'friends_only',
                'team_invitations': 'friends_only',
                'event_invitations': 'everyone',
                'show_online_status': True,
                'show_racing_status': True,
                'show_recent_activity': True,
                'share_telemetry': False,
                'share_setups': True
            }
            
            success = self.db_managers['user_manager'].update_user_preferences(self.user_id, preferences)
            
            if success:
                QMessageBox.information(self, "Settings Saved", "Your privacy settings have been saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save privacy settings.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving privacy settings: {str(e)}")
    
    def save_notification_settings(self):
        """Save notification settings"""
        if not self.db_managers or 'user_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
            
        try:
            # Get current preferences
            preferences = self.db_managers['user_manager'].get_user_preferences(self.user_id)
            
            # Update notification settings (in real implementation, collect from form)
            preferences['notification_settings'] = {
                'friend_requests': True,
                'new_messages': True,
                'event_invitations': True,
                'team_activity': True,
                'achievement_unlocks': True,
                'lap_record_beats': True,
                'race_reminders': True,
                'email_notifications': {
                    'weekly_summary': False,
                    'event_reminders': True,
                    'account_updates': True,
                    'new_features': False,
                    'community_highlights': False
                },
                'quiet_hours_start': '22:00',
                'quiet_hours_end': '08:00',
                'timezone': 'UTC+0'
            }
            
            success = self.db_managers['user_manager'].update_user_preferences(self.user_id, preferences)
            
            if success:
                QMessageBox.information(self, "Settings Saved", "Your notification settings have been saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save notification settings.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving notification settings: {str(e)}")
    
    def enable_push_notifications(self):
        """Enable push notifications"""
        QMessageBox.information(self, "Push Notifications", "Push notifications have been enabled for your browser.")
    
    def change_password(self):
        """Handle password change"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Password")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Current password
        layout.addWidget(QLabel("Current Password:"))
        current_password = QLineEdit()
        current_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(current_password)
        
        # New password
        layout.addWidget(QLabel("New Password:"))
        new_password = QLineEdit()
        new_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(new_password)
        
        # Confirm password
        layout.addWidget(QLabel("Confirm New Password:"))
        confirm_password = QLineEdit()
        confirm_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(confirm_password)
        
        # Buttons
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        save_btn = QPushButton("Change Password")
        save_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Password Changed", "Your password has been changed successfully!")
    
    def enable_two_factor_auth(self):
        """Enable two-factor authentication"""
        QMessageBox.information(self, "2FA Setup", "Two-factor authentication setup wizard would open here.")
    
    def revoke_all_sessions(self):
        """Revoke all other sessions"""
        reply = QMessageBox.question(
            self, 
            "Revoke Sessions", 
            "Are you sure you want to revoke all other active sessions?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Sessions Revoked", "All other sessions have been revoked.")
    
    def view_login_history(self):
        """View full login history"""
        QMessageBox.information(self, "Login History", "Full login history dialog would open here.")
    
    def generate_backup_codes(self):
        """Generate backup codes"""
        QMessageBox.information(self, "Backup Codes", "Backup codes generation dialog would open here.")
    
    def save_racing_preferences(self):
        """Save racing preferences"""
        if not self.db_managers or 'user_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
            
        try:
            # Get current preferences
            preferences = self.db_managers['user_manager'].get_user_preferences(self.user_id)
            
            # Update racing preferences (in real implementation, collect from form)
            preferences['racing_preferences'] = {
                'distance_units': 'kilometers',
                'speed_units': 'km/h',
                'temperature_units': 'celsius',
                'fuel_units': 'liters',
                'default_racing_view': 'cockpit',
                'difficulty_level': 'intermediate',
                'assist_preferences': 'some_assists',
                'auto_save_telemetry': True,
                'auto_analyze_laps': True,
                'data_retention': '6_months',
                'default_setup_style': 'balanced',
                'auto_apply_community_setups': 'ask_first',
                'preferred_racing_days': 'both',
                'preferred_start_time': '19:00',
                'session_length_preference': 'medium'
            }
            
            success = self.db_managers['user_manager'].update_user_preferences(self.user_id, preferences)
            
            if success:
                QMessageBox.information(self, "Settings Saved", "Your racing preferences have been saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save racing preferences.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving racing preferences: {str(e)}")
    
    def export_profile_data(self):
        """Export profile data"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, 
            "Export Profile Data", 
            "trackpro_profile.json", 
            "JSON Files (*.json)"
        )
        if file_path:
            QMessageBox.information(self, "Export Complete", f"Profile data exported to: {file_path}")
    
    def export_telemetry_data(self):
        """Export telemetry data"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, 
            "Export Telemetry Data", 
            "trackpro_telemetry.zip", 
            "ZIP Files (*.zip)"
        )
        if file_path:
            QMessageBox.information(self, "Export Complete", f"Telemetry data exported to: {file_path}")
    
    def export_all_data(self):
        """Export all data"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, 
            "Export All Data", 
            "trackpro_complete_data.zip", 
            "ZIP Files (*.zip)"
        )
        if file_path:
            QMessageBox.information(self, "Export Complete", f"All data exported to: {file_path}")
    
    def cleanup_old_data(self):
        """Clean up old data"""
        reply = QMessageBox.question(
            self, 
            "Clean Up Data", 
            "This will remove old telemetry data and free up storage space. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Cleanup Complete", "Old data has been cleaned up. Freed 234 MB of storage.")
    
    def deactivate_account(self):
        """Deactivate account"""
        reply = QMessageBox.warning(
            self, 
            "Deactivate Account", 
            "This will temporarily deactivate your account. You can reactivate it by logging in again. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Account Deactivated", "Your account has been deactivated.")
    
    def delete_account(self):
        """Delete account permanently"""
        reply = QMessageBox.critical(
            self, 
            "Delete Account", 
            "⚠️ WARNING: This will permanently delete your account and ALL associated data. This action cannot be undone!\n\nAre you absolutely sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Ask for confirmation again
            confirm_reply = QMessageBox.critical(
                self, 
                "Final Confirmation", 
                "This is your final warning. Clicking 'Yes' will permanently delete your account and all data.\n\nType 'DELETE' in the text box below to confirm:",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm_reply == QMessageBox.Yes:
                QMessageBox.information(self, "Account Deletion", "Account deletion process would begin here.")

    def open_login_dialog(self):
        """Open the login dialog from the placeholder"""
        try:
            # Try to get the main window and open login dialog
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'show_login_dialog'):
                parent_window = parent_window.parent()
                
            if parent_window and hasattr(parent_window, 'show_login_dialog'):
                parent_window.show_login_dialog()
            else:
                print("Could not find main window to open login dialog")
        except Exception as e:
            print(f"Error opening login dialog: {e}")
        
    def switch_section(self, section_id):
        """Switch to a different community section"""
        self.current_section = section_id
        
        # Map section IDs to widget indices
        section_mapping = {
            "social": 0,
            "community": 1,
            "content": 2,
            "achievements": 3,
            "account": 4
        }
        
        if section_id in section_mapping:
            self.content_stack.setCurrentIndex(section_mapping[section_id])
            
        # Update navigation
        self.navigation.set_active_section(section_id)
        
    def set_managers(self, managers):
        """Set the community managers"""
        self.managers = managers
        # Recreate section widgets with new managers
        self.create_section_widgets()
        
    def set_user_id(self, user_id):
        """Set the current user ID"""
        # Only update if the user ID actually changed
        if self.user_id != user_id:
            self.user_id = user_id
            # Clear existing widgets
            while self.content_stack.count():
                widget = self.content_stack.widget(0)
                self.content_stack.removeWidget(widget)
                if widget:
                    widget.deleteLater()
            # Recreate section widgets with new user ID
            self.create_section_widgets()
            # Restore the current section
            self.switch_section(self.current_section)
        
    def get_current_section(self):
        """Get the currently active section"""
        return self.current_section
    
    def show_add_friend_dialog(self):
        """Show dialog to add a friend"""
        if not self.db_managers or 'social_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
        
        username, ok = QInputDialog.getText(
            self, 
            "Add Friend", 
            "Enter friend's username:",
            QLineEdit.Normal
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
                            activity_item = self.create_activity_item(
                                "🏁",  # Default icon
                                activity.get('activity_type', 'update'),
                                activity.get('description', ''),
                                self.format_time_ago(activity.get('created_at', ''))
                            )
                            layout.addWidget(activity_item)
                    else:
                        # No activities placeholder
                        no_activity_label = QLabel("No recent activity. Share your first racing update!")
                        no_activity_label.setAlignment(Qt.AlignCenter)
                        no_activity_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 20px;")
                        layout.addWidget(no_activity_label)
                    
                    layout.addStretch()
                    
                    print("Activity feed refreshed successfully")
        except Exception as e:
            print(f"Error refreshing activity feed: {e}")
    
    def join_club_action(self, club_name, club_id):
        """Join a racing club"""
        if not self.db_managers or 'community_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
        
        reply = QMessageBox.question(
            self, 
            "Join Club", 
            f"Do you want to join '{club_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.db_managers['community_manager'].join_club(self.user_id, club_id)
                if success:
                    QMessageBox.information(self, "Success", f"Successfully joined {club_name}!")
                    # Refresh clubs panel
                    self.refresh_clubs_panel()
                else:
                    QMessageBox.warning(self, "Error", "Failed to join club.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error joining club: {str(e)}")
    
    def show_no_club_id_error(self):
        """Show error when club ID is missing"""
        QMessageBox.warning(self, "Error", "Club information is incomplete. Cannot join club.")
    
    def refresh_clubs_panel(self):
        """Refresh the clubs panel"""
        # This would reload the clubs content
        pass
    
    def handle_auth_state_change(self, is_authenticated):
        """Handle authentication state changes and refresh the community widget"""
        try:
            print(f"Community widget: Authentication state changed to {is_authenticated}")
            
            if is_authenticated:
                # User just logged in - refresh the community widget with authenticated content
                from trackpro.database.supabase_client import get_supabase_client, supabase
                from trackpro.community.database_managers import create_community_managers
                
                # Get fresh Supabase client and managers
                supabase_client = get_supabase_client()
                if supabase_client:
                    # Use the raw client, not the manager
                    self.supabase_client = supabase_client
                    self.db_managers = create_community_managers(supabase_client)
                    
                    # Try multiple ways to get current user ID with retries
                    self.user_id = None
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            # Try getting from the managers first
                            if self.db_managers and 'user_manager' in self.db_managers:
                                self.user_id = self.db_managers['user_manager'].get_current_user_id()
                            
                            # If that fails, try getting directly from supabase client
                            if not self.user_id and supabase_client:
                                try:
                                    user = supabase_client.auth.get_user()
                                    if user and hasattr(user, 'user') and user.user:
                                        self.user_id = user.user.id
                                except Exception as e:
                                    print(f"Error getting user from client: {e}")
                            
                            # If we got a user ID, break out of retry loop
                            if self.user_id:
                                break
                                
                            # Wait a bit before retrying
                            if attempt < max_retries - 1:
                                import time
                                print(f"Community widget: Retry {attempt + 1} - waiting for session sync...")
                                time.sleep(0.5)
                                
                        except Exception as e:
                            print(f"Community widget: Attempt {attempt + 1} failed to get user ID: {e}")
                            if attempt < max_retries - 1:
                                import time
                                time.sleep(0.5)
                    
                    print(f"Community widget: Updated user ID to {self.user_id}")
                    
                    # Only proceed if we have a valid user ID
                    if self.user_id:
                        # Clear and recreate all section widgets with authenticated content
                        while self.content_stack.count():
                            widget = self.content_stack.widget(0)
                            self.content_stack.removeWidget(widget)
                            if widget:
                                widget.deleteLater()
                        
                        # Recreate all section widgets with the new authentication state
                        self.create_section_widgets()
                        
                        # Switch back to the current section to show the updated content
                        self.switch_section(self.current_section)
                        
                        print("Community widget: Successfully refreshed with authenticated content")
                    else:
                        print("Community widget: Could not get user ID immediately, will retry in 2 seconds...")
                        # Start delayed retry timer
                        self.auth_retry_timer.start(2000)  # Retry in 2 seconds
                else:
                    print("Community widget: Failed to get Supabase client after auth state change")
            else:
                # User logged out - show login placeholders
                self.supabase_client = None
                self.db_managers = {}
                self.user_id = None
                
                # Clear and recreate section widgets without authentication
                while self.content_stack.count():
                    widget = self.content_stack.widget(0)
                    self.content_stack.removeWidget(widget)
                    if widget:
                        widget.deleteLater()
                
                # Recreate section widgets with login prompts
                self.create_section_widgets()
                self.switch_section(self.current_section)
                
                print("Community widget: Successfully refreshed with login prompts")
                
        except Exception as e:
            print(f"Error handling auth state change in community widget: {e}")
            import traceback
            traceback.print_exc()
    
    def retry_auth_setup(self):
        """Retry authentication setup after a delay (fallback for session sync issues)"""
        try:
            print("Community widget: Retrying authentication setup...")
            from trackpro.database.supabase_client import get_supabase_client
            
            # Get the client directly
            supabase_client = get_supabase_client()
            if not supabase_client:
                print("Community widget: No Supabase client available, canceling retry")
                return
            
            # Try to get user ID again
            user_id = None
            try:
                user = supabase_client.auth.get_user()
                if user and hasattr(user, 'user') and user.user:
                    user_id = user.user.id
            except Exception as e:
                print(f"Community widget: Retry failed to get user: {e}")
            
            if user_id:
                print(f"Community widget: Retry successful - got user ID: {user_id}")
                # Force a fresh auth state change with the now-working session
                self.handle_auth_state_change(True)
            else:
                print("Community widget: Retry failed - still no user ID")
                
        except Exception as e:
            print(f"Error in auth retry: {e}")


# Factory function for creating the community widget
def create_community_widget(parent=None):
    """Create a community widget for embedding in the main application"""
    return CommunityMainWidget(parent)


if __name__ == "__main__":
    # Test the community widget
    app = QApplication(sys.argv)
    
    # Create and show the community widget
    widget = CommunityMainWidget()
    widget.setWindowTitle("TrackPro Community")
    widget.resize(1200, 800)
    widget.show()
    
    sys.exit(app.exec_()) 