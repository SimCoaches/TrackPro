"""
TrackPro Community Main Widget
Integrated community interface that works as a tab within the main TrackPro application.
"""

import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from datetime import datetime
import json
from typing import Dict, List, Optional, Any

# Import community theme and database managers
from .community_theme import CommunityTheme
from .database_managers import create_community_managers
from .discord_integration import DiscordIntegrationWidget

# Import the split components
from .community_social import CommunitySocialMixin
from .community_content import CommunityContentMixin
from .community_account import CommunityAccountMixin

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

# Import the automated achievement system
from .racing_achievements_automation import create_racing_achievement_monitor
import random


class CommunityNotificationManager(QObject):
    """Manages notifications for community features"""
    
    # Signals for notification updates
    notification_updated = pyqtSignal(str, int)  # section_id, count
    total_notifications_updated = pyqtSignal(int)  # total count
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notification_counts = {
            "social": 0,
            "discord": 0,
            "community": 0,
            "content": 0,
            "achievements": 0,
            "account": 0
        }
        
        # NO FAKE NOTIFICATIONS - real notifications come from actual user activity only
        
    def update_notification_count(self, section_id: str, count: int):
        """Update notification count for a specific section"""
        if section_id in self.notification_counts:
            old_count = self.notification_counts[section_id]
            self.notification_counts[section_id] = count
            
            if old_count != count:
                self.notification_updated.emit(section_id, count)
                # Update total count
                total = sum(self.notification_counts.values())
                self.total_notifications_updated.emit(total)
    
    def get_notification_count(self, section_id: str) -> int:
        """Get notification count for a specific section"""
        return self.notification_counts.get(section_id, 0)
    
    def get_total_notifications(self) -> int:
        """Get total notification count"""
        return sum(self.notification_counts.values())
    
    def check_discord_notifications(self):
        """NO FAKE DATA - real Discord notifications come from JavaScript monitoring only"""
        pass
    
    def check_general_notifications(self):
        """NO FAKE DATA - real notifications come from actual user activity only"""
        pass
    
    def clear_notifications(self, section_id: str):
        """Clear notifications for a specific section"""
        self.update_notification_count(section_id, 0)
    
    def mark_discord_read(self):
        """Mark Discord notifications as read"""
        self.clear_notifications("discord")
    
    def mark_social_read(self):
        """Mark social notifications as read"""
        self.clear_notifications("social")


class CommunityNavigationWidget(QWidget):
    """Navigation sidebar for community features with notification badges"""
    
    section_changed = pyqtSignal(str)
    
    def __init__(self, notification_manager, parent=None):
        super().__init__(parent)
        self.current_section = "social"
        self.notification_manager = notification_manager
        self.notification_badges = {}
        self.setup_ui()
        
        # Connect to notification updates
        self.notification_manager.notification_updated.connect(self.update_notification_badge)
        
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
            ("social", "👥 Social", "Live racing achievements and friends"),
            ("discord", "🎮 Discord", "Server chat and voice channels"),
            ("community", "🏁 Community", "Teams, clubs, and events"),
            ("content", "📁 Content", "Share setups, media, and guides"),
            ("achievements", "🏆 Achievements", "XP, levels, and gamification"),
            ("account", "⚙️ Account", "Profile and settings")
        ]
        
        self.nav_buttons = {}
        
        for section_id, title, description in nav_items:
            button_widget = self.create_nav_button_with_badge(section_id, title, description)
            nav_layout.addWidget(button_widget, 0)
            
        nav_layout.addStretch()
        
        # Quick stats
        stats_widget = self.create_stats_widget()
        nav_layout.addWidget(stats_widget)
        
        layout.addWidget(header_widget)
        layout.addWidget(nav_widget)
        
        # Set initial selection
        self.set_active_section("social")
        
    def create_nav_button_with_badge(self, section_id, title, description):
        """Create a navigation button with notification badge support"""
        container = QWidget()
        container.setMinimumHeight(75)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Main button
        button = QPushButton()
        button.setCheckable(True)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setMinimumHeight(75)
        
        # Create layout for button content
        button_layout = QVBoxLayout(button)
        button_layout.setContentsMargins(16, 15, 16, 15)
        button_layout.setSpacing(3)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        title_label.setStyleSheet("font-weight: bold; background: transparent;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; background: transparent;")
        
        button_layout.addWidget(title_label)
        button_layout.addWidget(desc_label)
        
        # Button styling
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
        
        # Notification badge
        badge = QLabel()
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: #FF4444;
                color: white;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        badge.hide()  # Initially hidden
        
        # Position badge in top-right corner
        badge_container = QWidget()
        badge_container.setFixedSize(30, 75)
        badge_layout = QVBoxLayout(badge_container)
        badge_layout.setContentsMargins(5, 10, 5, 0)
        badge_layout.addWidget(badge)
        badge_layout.addStretch()
        
        # Add to container
        container_layout.addWidget(button)
        container_layout.addWidget(badge_container)
        
        # Store references
        self.nav_buttons[section_id] = button
        self.notification_badges[section_id] = badge
        
        # Connect click event
        button.clicked.connect(lambda: self.on_section_clicked(section_id))
        
        return container
        
    def on_section_clicked(self, section_id):
        """Handle section click and clear notifications if appropriate"""
        self.section_changed.emit(section_id)
        
        # Auto-clear notifications for certain sections when viewed
        if section_id == "discord":
            # Clear Discord notifications when user views Discord tab
            QTimer.singleShot(1000, self.notification_manager.mark_discord_read)
        elif section_id == "social":
            # Clear social notifications when user views social tab
            QTimer.singleShot(1000, self.notification_manager.mark_social_read)
        
    def update_notification_badge(self, section_id, count):
        """Update the notification badge for a specific section"""
        if section_id in self.notification_badges:
            badge = self.notification_badges[section_id]
            if count > 0:
                if count > 99:
                    badge.setText("99+")
                else:
                    badge.setText(str(count))
                badge.show()
                
                # Add pulsing effect for Discord notifications
                if section_id == "discord" and count > 0:
                    self.add_pulse_effect(badge)
            else:
                badge.hide()
    
    def add_pulse_effect(self, badge):
        """Add a subtle pulse effect to notification badges"""
        effect = QGraphicsOpacityEffect()
        badge.setGraphicsEffect(effect)
        
        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.5)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(lambda: self.fade_animation.setDirection(
            QPropertyAnimation.Forward if self.fade_animation.direction() == QPropertyAnimation.Backward 
            else QPropertyAnimation.Backward
        ))
        self.fade_animation.finished.connect(self.fade_animation.start)
        self.fade_animation.start()
        
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
        
        # REAL STATS ONLY - no fake placeholder data
        # Real stats would be loaded from database when that functionality is implemented
        real_stats_label = QLabel("Real stats will appear here")
        real_stats_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; font-style: italic; font-size: 10px;")
        layout.addWidget(real_stats_label)
            
        return stats_widget
        
    def set_active_section(self, section_id):
        """Set the active section"""
        self.current_section = section_id
        
        # Update button states
        for btn_id, button in self.nav_buttons.items():
            button.setChecked(btn_id == section_id)


class CommunityMainWidget(QWidget, CommunitySocialMixin, CommunityContentMixin, CommunityAccountMixin):
    """Main community interface that integrates directly into TrackPro's main window"""
    
    # Signal for notifying main app about notification changes
    notification_count_changed = pyqtSignal(int)
    
    def __init__(self, parent=None, supabase_client=None):
        super().__init__(parent)
        self.supabase_client = supabase_client
        
        # Initialize notification manager
        self.notification_manager = CommunityNotificationManager(self)
        self.notification_manager.total_notifications_updated.connect(
            self.notification_count_changed.emit
        )
        
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
        
        # Initialize automated racing achievement system
        self.racing_achievement_monitor = None
        
        self.setup_ui()
        
        # IMPORTANT: Start Discord monitoring immediately, even if community tab isn't visible
        # This ensures users get notifications on the main Community button 
        self.start_immediate_discord_monitoring()
        
    def setup_ui(self):
        """Setup the main community interface"""
        # Apply theme
        self.setStyleSheet(CommunityTheme.get_stylesheet())
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Navigation sidebar with notification support
        self.navigation = CommunityNavigationWidget(self.notification_manager)
        self.navigation.section_changed.connect(self.switch_section)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Create all section widgets
        self.create_section_widgets()
        
        # Main layout
        layout.addWidget(self.navigation)
        layout.addWidget(self.content_stack)
        
        # Set initial section - this will check authentication state
        self.switch_section("social")
        
    def create_section_widgets(self):
        """Create widgets for each community section - using lazy loading for performance"""
        
        # Initialize widget references to None - they'll be created when needed
        self.social_widget = None
        self.discord_widget = None
        self.community_widget = None
        self.content_widget = None
        self.achievements_widget = None
        self.account_widget = None
        
        # Track which sections have been loaded
        self.loaded_sections = set()
            
    def create_login_required_widget(self, section_id):
        """Create a login required widget that blocks all content until user signs in"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Large lock icon
        icon_label = QLabel("🔐")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 64px; color: {CommunityTheme.COLORS['accent']};")
        layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Sign In Required")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_primary']};
            font-size: 24px;
            font-weight: bold;
            margin: 20px 0px 10px 0px;
        """)
        layout.addWidget(title_label)
        
        # Section-specific message
        section_messages = {
            "social": "Connect with fellow racers and share achievements",
            "discord": "Set up Discord integration for real-time communication",
            "community": "Join racing teams, clubs, and community events", 
            "content": "Share and discover car setups, guides, and media",
            "achievements": "Track your racing progress and unlock achievements",
            "account": "Manage your profile and racing statistics"
        }
        
        section_message = section_messages.get(section_id, "Access community features")
        message_label = QLabel(f"Sign in to {section_message}")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_secondary']};
            font-size: 14px;
            margin: 0px 0px 30px 0px;
            max-width: 400px;
        """)
        layout.addWidget(message_label)
        
        # Login button
        login_button = QPushButton("🔑 Sign In to TrackPro")
        login_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {CommunityTheme.COLORS['accent']};
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 150px;
                border: 2px solid {CommunityTheme.COLORS['accent']};
            }}
            QPushButton:hover {{
                background-color: #FF8A65;
                border-color: #FF8A65;
            }}
            QPushButton:pressed {{
                background-color: #FF5722;
                border-color: #FF5722;
            }}
        """)
        login_button.clicked.connect(self.open_login_dialog)
        layout.addWidget(login_button)
        
        # Additional info
        info_label = QLabel("All community features require authentication to protect user privacy and enable personalized experiences.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_secondary']};
            font-size: 11px;
            margin: 20px 0px 0px 0px;
            max-width: 500px;
            font-style: italic;
        """)
        layout.addWidget(info_label)
        
        return widget

    def create_placeholder_widget(self, message):
        """Create a placeholder widget for sections that aren't available"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon - different icons for different states
        if "log in" in message.lower():
            icon_text = "🔐"
            icon_color = CommunityTheme.COLORS['warning']
        else:
            icon_text = "🚧"
            icon_color = CommunityTheme.COLORS['text_secondary']
            
        icon_label = QLabel(icon_text)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 48px; color: {icon_color};")
        layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setWordWrap(True)
        status_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_secondary']};
            font-size: 12px;
            margin: 16px;
            max-width: 400px;
        """)
        layout.addWidget(status_label)
        
        return widget
    
    def create_discord_widget(self):
        """Create Discord integration widget."""
        try:
            # Create the Discord integration widget
            discord_widget = DiscordIntegrationWidget(self)
            
            # Connect notification manager to Discord widget
            if hasattr(self, 'notification_manager'):
                discord_widget.set_notification_manager(self.notification_manager)
            
            # Wrapper with padding for better visual integration
            wrapper = QWidget()
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # Add the Discord widget
            layout.addWidget(discord_widget)
            
            # Store reference for notification testing
            self.discord_widget_instance = discord_widget
            
            # Notification testing panel REMOVED for production to save screen space
            
            return wrapper
            
        except Exception as e:
            print(f"Error creating Discord widget: {e}")
            return self.create_placeholder_widget("Discord integration temporarily unavailable")

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
        """Switch to a different community section with lazy loading"""
        self.current_section = section_id
        
        # Lazy load the widget if it hasn't been created yet
        if section_id not in self.loaded_sections:
            self._load_section_widget(section_id)
        
        # Map section IDs to widget references
        widget_mapping = {
            "social": self.social_widget,
            "discord": self.discord_widget,
            "community": self.community_widget,
            "content": self.content_widget,
            "achievements": self.achievements_widget,
            "account": self.account_widget
        }
        
        # Get the widget for this section
        widget = widget_mapping.get(section_id)
        if widget:
            # Find the widget's index in the stack or add it
            index = self.content_stack.indexOf(widget)
            if index == -1:
                # Widget not in stack yet, add it
                index = self.content_stack.addWidget(widget)
            
            self.content_stack.setCurrentIndex(index)
            
        # Update navigation
        self.navigation.set_active_section(section_id)
    
    def _load_section_widget(self, section_id):
        """Load a specific section widget on demand"""
        if section_id in self.loaded_sections:
            return  # Already loaded
        
        print(f"Loading community section: {section_id}")
        
        try:
            # CHECK AUTHENTICATION FIRST - if not authenticated, show login screen for ALL sections
            if not self.user_id or not self.supabase_client:
                print(f"User not authenticated, showing login screen for {section_id}")
                # Create login screen for this section
                login_widget = self.create_login_required_widget(section_id)
                
                # Assign to the appropriate section
                if section_id == "social":
                    self.social_widget = login_widget
                elif section_id == "discord":
                    self.discord_widget = login_widget
                elif section_id == "community":
                    self.community_widget = login_widget
                elif section_id == "content":
                    self.content_widget = login_widget
                elif section_id == "achievements":
                    self.achievements_widget = login_widget
                elif section_id == "account":
                    self.account_widget = login_widget
            else:
                # User is authenticated, create the actual content widget
                print(f"User authenticated, loading real content for {section_id}")
                if section_id == "social":
                    self.social_widget = self.create_modern_social_widget()
                elif section_id == "discord":
                    self.discord_widget = self.create_discord_widget()
                elif section_id == "community":
                    self.community_widget = self.create_modern_community_widget()
                elif section_id == "content":
                    self.content_widget = self.create_modern_content_widget()
                elif section_id == "achievements":
                    self.achievements_widget = self.create_modern_achievements_widget()
                elif section_id == "account":
                    self.account_widget = self.create_modern_account_widget()
            
            # Mark as loaded
            self.loaded_sections.add(section_id)
            print(f"Successfully loaded section: {section_id}")
            
        except Exception as e:
            print(f"Error loading section {section_id}: {e}")
            import traceback
            traceback.print_exc()
        
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
            # Reset section widgets for lazy loading
            self.create_section_widgets()
            # Restore the current section (will lazy load if needed)
            self.switch_section(self.current_section)
        
    def get_current_section(self):
        """Get the currently active section"""
        return self.current_section
    
    def handle_auth_state_change(self, user_or_bool: Optional[Any]):
        """
        Handle authentication state changes and refresh the community widget.
        Can receive either a user object OR a boolean indicating auth state.
        """
        try:
            # Debug: Print received object structure
            print(f"🔍 Community widget: Received auth data: {type(user_or_bool)} = {user_or_bool}")
            
            # Handle both user objects and boolean auth states
            is_authenticated = False
            user_id = None
            
            # Check if this is a boolean auth state signal
            if isinstance(user_or_bool, bool):
                print(f"🔍 Received boolean auth state: {user_or_bool}")
                if user_or_bool:
                    # Boolean True means authenticated, but we need to get the actual user
                    print("🔍 Boolean True received, fetching actual user data...")
                    try:
                        from trackpro.database.supabase_client import supabase
                        # Use the supabase manager instance, not the raw client
                        if supabase and supabase.is_authenticated():
                            user_response = supabase.get_user()
                            if user_response and hasattr(user_response, 'user') and user_response.user:
                                is_authenticated = True
                                user_id = user_response.user.id
                                print(f"🔍 Retrieved user ID from manager: {user_id}")
                            elif user_response and hasattr(user_response, 'id') and user_response.id:
                                is_authenticated = True
                                user_id = user_response.id
                                print(f"🔍 Retrieved user ID directly: {user_id}")
                            else:
                                print("⚠️ Manager authenticated but couldn't get user details")
                                # Keep existing user if we have one
                                if self.user_id:
                                    is_authenticated = True
                                    user_id = self.user_id
                                    print(f"🔍 Keeping existing user ID: {user_id}")
                        else:
                            print("⚠️ Manager not authenticated despite boolean True")
                    except Exception as e:
                        print(f"⚠️ Error fetching user from boolean signal: {e}")
                        # Fallback: if we have an existing user and boolean is True, keep them
                        if self.user_id:
                            is_authenticated = True
                            user_id = self.user_id
                            print(f"🔍 Fallback: keeping existing user ID: {user_id}")
                else:
                    # Boolean False means logged out
                    is_authenticated = False
                    user_id = None
                    print("🔍 Boolean False received - user logged out")
            else:
                # Handle user object (existing logic)
                if user_or_bool is not None:
                    # Try different possible user object structures
                    if hasattr(user_or_bool, 'id') and user_or_bool.id:
                        # Direct user object
                        is_authenticated = True
                        user_id = user_or_bool.id
                        print(f"🔍 Found user ID directly: {user_id}")
                    elif hasattr(user_or_bool, 'user') and user_or_bool.user and hasattr(user_or_bool.user, 'id') and user_or_bool.user.id:
                        # Nested user object (common in Supabase responses)
                        is_authenticated = True
                        user_id = user_or_bool.user.id
                        print(f"🔍 Found user ID in nested structure: {user_id}")
                    elif hasattr(user_or_bool, 'email'):
                        # Alternative: user object with email but no id
                        is_authenticated = True
                        user_id = getattr(user_or_bool, 'id', user_or_bool.email)  # Fallback to email if no id
                        print(f"🔍 Found user with email: {user_or_bool.email}, using ID: {user_id}")
                    else:
                        print(f"🔍 User object structure not recognized: {dir(user_or_bool) if hasattr(user_or_bool, '__dict__') else str(user_or_bool)}")
            
            print(f"🔐 Community widget: Auth state change processed. Authenticated: {is_authenticated}, User ID: {user_id}")

            if is_authenticated and user_id:
                # Check if the user ID has actually changed to prevent unnecessary reloads
                if self.user_id == user_id and self.supabase_client is not None:
                    print("✅ Community widget: User ID and client already set. No refresh needed.")
                    return

                self.user_id = user_id
                print(f"🔑 Community widget: User ID set to {self.user_id}")

                from trackpro.database.supabase_client import get_supabase_client
                from trackpro.community.database_managers import create_community_managers
                
                supabase_client = get_supabase_client()
                if supabase_client:
                    self.supabase_client = supabase_client
                    self.db_managers = create_community_managers(supabase_client)
                    
                    # Reload all content for the new user - this will replace login screens with real content
                    print("🔄 Community widget: Reloading all sections with authenticated content...")
                    self.reload_all_sections()
                    self.setup_racing_achievement_monitor()
                    
                    print("✅ Community widget: Successfully unlocked all community features!")
                else:
                    print("❌ Community widget: Failed to get Supabase client after auth state change.")
            else:
                # User logged out or no valid user data
                if self.user_id is None and self.supabase_client is None:
                    print("✅ Community widget: Already logged out. No refresh needed.")
                    return # Already logged out

                print("🔒 Community widget: User logged out or invalid, locking all sections...")
                self.supabase_client = None
                self.db_managers = {}
                self.user_id = None
                
                # Reload all sections - this will show login screens for all sections
                self.reload_all_sections()
                print("🔐 Community widget: All sections locked. Login required to access content.")
                
        except Exception as e:
            print(f"❌ Error handling auth state change in community widget: {e}")
            import traceback
            traceback.print_exc()

    def reload_all_sections(self):
        """Clears and reloads all section widgets."""
        # Clear existing widgets from the stack
        while self.content_stack.count():
            widget = self.content_stack.widget(0)
            self.content_stack.removeWidget(widget)
            if widget:
                widget.deleteLater()
        
        # Reset the tracking of loaded sections and widget references
        self.loaded_sections.clear()
        self.create_section_widgets()
        
        # Restore the currently selected section, which will trigger a lazy load
        self.switch_section(self.current_section)
    
    def get_notification_manager(self):
        """Get the notification manager for external access"""
        return self.notification_manager
    
    def setup_racing_achievement_monitor(self):
        """Set up the automated racing achievement monitor."""
        try:
            if not self.user_id or not self.db_managers:
                return
                
            # Create the racing achievement monitor
            self.racing_achievement_monitor = create_racing_achievement_monitor(
                self.user_id, 
                self.db_managers, 
                self
            )
            
            # Connect achievement signals to UI updates
            self.racing_achievement_monitor.achievement_posted.connect(self.on_automated_achievement)
            
            # Try to connect to the race coach system for real-time monitoring
            self.connect_to_race_coach()
            
            print("✅ Racing achievement automation enabled!")
            
        except Exception as e:
            print(f"❌ Error setting up racing achievement monitor: {e}")
            
    def connect_to_race_coach(self):
        """Connect to the race coach BACKEND telemetry system (works for all users, even without Race Coach UI access)."""
        try:
            # Connect to the BACKGROUND telemetry processing system that runs for all users
            # This works even if users don't have Race Coach UI access
            
            # Try to get the main window and find the iRacing API backend
            success = False
            
            # Method 1: Try to find the SimpleIRacingAPI instance
            try:
                # Look for the main window's iRacing API
                parent_widget = self.parent()
                while parent_widget:
                    # Look for the main window that should have the iRacing API
                    if hasattr(parent_widget, 'iracing_api') or hasattr(parent_widget, 'simple_iracing_api'):
                        iracing_api = getattr(parent_widget, 'iracing_api', None) or getattr(parent_widget, 'simple_iracing_api', None)
                        if iracing_api:
                            print(f"🔗 Found iRacing API backend: {iracing_api.__class__.__name__}")
                            self.hook_into_telemetry_backend(iracing_api)
                            success = True
                            break
                    parent_widget = parent_widget.parent()
                    
            except Exception as e:
                print(f"⚠️ Method 1 failed: {e}")
            
            # Method 2: Try to find the lap saver backend directly
            if not success:
                try:
                    # Import and check if there's a global lap saver instance
                    from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
                    
                    # Check if we can find an active lap saver instance
                    parent_widget = self.parent()
                    while parent_widget:
                        # Look for any object that might have a lap_saver
                        for attr_name in dir(parent_widget):
                            if 'lap' in attr_name.lower() and 'saver' in attr_name.lower():
                                lap_saver = getattr(parent_widget, attr_name, None)
                                if lap_saver and hasattr(lap_saver, 'lap_indexer'):
                                    print(f"🔗 Found lap saver backend: {lap_saver.__class__.__name__}")
                                    self.hook_into_lap_saver(lap_saver)
                                    success = True
                                    break
                        if success:
                            break
                        parent_widget = parent_widget.parent()
                        
                except Exception as e:
                    print(f"⚠️ Method 2 failed: {e}")
            
            # Method 3: Try to hook into the database directly for lap saves
            if not success:
                try:
                    self.setup_database_monitoring()
                    success = True
                    print("🔗 Connected to database monitoring for lap detection")
                except Exception as e:
                    print(f"⚠️ Method 3 failed: {e}")
            
            if success:
                print("✅ Achievement automation connected to backend telemetry system!")
                print("🏁 All users will now get automated racing achievements!")
            else:
                print("⚠️ Could not connect to telemetry backend - using manual triggers only")
                
        except Exception as e:
            print(f"❌ Error connecting to race coach backend: {e}")
    
    def hook_into_telemetry_backend(self, iracing_api):
        """Hook into the SimpleIRacingAPI telemetry processing."""
        try:
            # Check if the API has a lap saver
            if hasattr(iracing_api, 'lap_saver') and iracing_api.lap_saver:
                lap_saver = iracing_api.lap_saver
                print(f"🎯 Found lap saver in iRacing API: {lap_saver.__class__.__name__}")
                self.hook_into_lap_saver(lap_saver)
            
            # Also try to connect to telemetry updates
            if hasattr(iracing_api, 'telemetry_updated'):
                # This would be a signal for real-time telemetry
                iracing_api.telemetry_updated.connect(self.on_telemetry_update)
                print("✅ Connected to real-time telemetry updates")
                
        except Exception as e:
            print(f"❌ Error hooking into telemetry backend: {e}")
    
    def hook_into_lap_saver(self, lap_saver):
        """Hook into the IRacingLapSaver to detect lap completions."""
        try:
            # The lap saver has an immediate save callback system
            if hasattr(lap_saver, 'lap_indexer') and lap_saver.lap_indexer:
                lap_indexer = lap_saver.lap_indexer
                
                # Hook into the immediate save system
                if hasattr(lap_indexer, '_save_lap_immediately'):
                    # Store the original save method
                    original_save = lap_indexer._save_lap_immediately
                    
                    # Create our enhanced save method
                    def enhanced_save_with_achievements(lap_dict):
                        # Call the original save first
                        result = original_save(lap_dict)
                        
                        # Then process achievements
                        try:
                            self.process_lap_completion(lap_dict)
                        except Exception as e:
                            print(f"❌ Error processing achievements for lap: {e}")
                        
                        return result
                    
                    # Replace the save method
                    lap_indexer._save_lap_immediately = enhanced_save_with_achievements
                    self.connected_lap_indexer = lap_indexer
                    print("✅ Hooked into lap indexer immediate save system")
                    
                # Also hook into the callback system if available
                if hasattr(lap_indexer, '_save_callback') and hasattr(lap_indexer, 'set_immediate_save_callback'):
                    original_callback = lap_indexer._save_callback
                    
                    def enhanced_callback(lap_data):
                        # Call original callback if it exists
                        result = None
                        if original_callback:
                            result = original_callback(lap_data)
                        
                        # Process achievements
                        try:
                            self.process_lap_completion(lap_data)
                        except Exception as e:
                            print(f"❌ Error processing achievements in callback: {e}")
                        
                        return result
                    
                    lap_indexer.set_immediate_save_callback(enhanced_callback)
                    print("✅ Enhanced lap completion callback with achievements")
                    
        except Exception as e:
            print(f"❌ Error hooking into lap saver: {e}")
    
    def setup_database_monitoring(self):
        """Set up database monitoring for new lap entries (fallback method)."""
        try:
            # This would monitor the database for new lap entries
            # and trigger achievements when new laps are detected
            
            # Set up a timer to periodically check for new laps
            if not hasattr(self, 'db_monitor_timer'):
                self.db_monitor_timer = QTimer()
                self.db_monitor_timer.timeout.connect(self.check_for_new_laps)
                self.db_monitor_timer.start(10000)  # Check every 10 seconds
                
                # Track last seen lap for comparison
                self.last_seen_lap_id = None
                
            print("✅ Database monitoring set up for lap detection")
            
        except Exception as e:
            print(f"❌ Error setting up database monitoring: {e}")
    
    def check_for_new_laps(self):
        """Check database for new laps and trigger achievements."""
        try:
            if not self.db_managers or 'social_manager' not in self.db_managers:
                return
            
            # This would query for the most recent lap and compare with last seen
            # Implementation would depend on your database schema
            
        except Exception as e:
            print(f"❌ Error checking for new laps: {e}")
    
    def process_lap_completion(self, lap_data):
        """Process a completed lap and trigger achievements."""
        try:
            if not self.racing_achievement_monitor:
                return
            
            # Extract lap information from the lap_data dictionary
            lap_number = lap_data.get('lap_number_sdk', 0)
            lap_time = lap_data.get('duration_seconds', 0)
            lap_state = lap_data.get('lap_state', 'UNKNOWN')
            is_valid = lap_data.get('is_valid_for_leaderboard', False)
            
            # Skip invalid laps
            if not is_valid or lap_time <= 0:
                print(f"🚫 Skipping invalid lap {lap_number}: {lap_state}, {lap_time}s")
                return
            
            # Try to get track and car information from telemetry frames
            track_name = "Unknown Track"
            car_name = "Unknown Car"
            track_id = "unknown"
            sector_times = []
            
            frames = lap_data.get('telemetry_frames', [])
            if frames:
                # Get track/car info from the last frame
                last_frame = frames[-1]
                
                # Extract track and car info if available
                # These field names might need adjustment based on your telemetry structure
                track_name = last_frame.get('TrackDisplayName', last_frame.get('track_name', 'Unknown Track'))
                car_name = last_frame.get('CarName', last_frame.get('car_name', 'Unknown Car'))
                track_id = last_frame.get('TrackId', last_frame.get('track_id', 'unknown'))
                
                # Look for sector times in any frame
                for frame in frames:
                    if 'sector_times' in frame and frame['sector_times']:
                        sector_times = frame['sector_times']
                        break
            
            # Create achievement data
            achievement_lap_data = {
                'lap_time': lap_time,
                'track_id': str(track_id),
                'track_name': track_name,
                'car_name': car_name,
                'lap_number': lap_number,
                'is_valid': is_valid,
                'sector_times': sector_times
            }
            
            print(f"🏁 Processing lap completion for achievements: Lap {lap_number} at {track_name} - {lap_time:.3f}s")
            
            # Trigger the achievement system
            self.racing_achievement_monitor.on_lap_completed(achievement_lap_data)
            
        except Exception as e:
            print(f"❌ Error processing lap completion: {e}")
            import traceback
            traceback.print_exc()
    
    def on_telemetry_update(self, telemetry_data):
        """Handle real-time telemetry updates."""
        try:
            # This could be used for real-time monitoring
            # For now, we mainly care about lap completions
            pass
        except Exception as e:
            print(f"❌ Error handling telemetry update: {e}")
    
    def on_race_coach_personal_best(self, lap_data):
        """Handle personal best signal from race coach."""
        try:
            if self.racing_achievement_monitor:
                # Ensure lap_data has required fields
                enhanced_lap_data = {
                    'lap_time': lap_data.get('lap_time', 0),
                    'track_id': lap_data.get('track_id', 'unknown'),
                    'track_name': lap_data.get('track_name', 'Unknown Track'),
                    'car_name': lap_data.get('car_name', 'Unknown Car'),
                    'lap_number': lap_data.get('lap_number', 0),
                    'is_valid': lap_data.get('is_valid', True),
                    'sector_times': lap_data.get('sector_times', [])
                }
                
                self.racing_achievement_monitor.on_lap_completed(enhanced_lap_data)
                
        except Exception as e:
            print(f"❌ Error handling race coach personal best: {e}")
    
    def on_automated_achievement(self, achievement_type: str, message: str, metadata: dict):
        """Handle automated achievement posting."""
        try:
            print(f"🎉 Automated achievement posted: {achievement_type} - {message}")
            
            # Refresh the activity feed to show the new achievement
            if hasattr(self, 'activity_feed_widget'):
                QTimer.singleShot(1000, self.refresh_activity_feed)  # Delay to allow database update
                
            # Update notification count if this was a significant achievement
            if achievement_type in ['personal_best', 'race_result', 'achievement']:
                current_count = self.notification_manager.get_notification_count("social")
                self.notification_manager.update_notification_count("social", current_count + 1)
                
        except Exception as e:
            print(f"❌ Error handling automated achievement: {e}")
    
    def trigger_test_achievement(self):
        """Test function to check connection status ONLY - NO FAKE DATA POSTING."""
        try:
            print("🧪 ACHIEVEMENT SYSTEM TEST - CONNECTION DIAGNOSTICS ONLY")
            print("🚫 NO FAKE DATA WILL BE POSTED - REAL RACING DATA ONLY")
            
            if self.racing_achievement_monitor:
                print("✅ Racing achievement monitor is active")
                
                # Show diagnosis info only
                if hasattr(self.racing_achievement_monitor, 'diagnose_connection'):
                    self.racing_achievement_monitor.diagnose_connection()
                
                # Show stats about real achievements
                if hasattr(self.racing_achievement_monitor, 'get_achievement_stats'):
                    stats = self.racing_achievement_monitor.get_achievement_stats()
                    print(f"📊 Real Achievement Stats: {stats}")
                
                print("🏁 To see achievements, complete real laps in iRacing!")
            else:
                print("❌ Racing achievement monitor not available")
                
        except Exception as e:
            print(f"❌ Error checking achievement system: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_all_notifications(self):
        """Clear all notifications"""
        for section in ["social", "discord", "community", "content", "achievements", "account"]:
            self.notification_manager.clear_notifications(section)
    
    def start_immediate_discord_monitoring(self):
        """DISABLED: Background monitoring for performance reasons.
        
        Discord loading is too slow and laggy when running background monitoring.
        Notifications will only work when users visit the Discord tab directly.
        """
        print("⚡ Background Discord monitoring DISABLED for performance - notifications will work when Discord tab is visited")
    
    def on_background_discord_loaded(self, success):
        """Handle when background Discord monitor finishes loading."""
        if success:
            print("✅ Background Discord monitor loaded - injecting monitoring script...")
            # Wait for Discord to initialize, then inject monitoring
            QTimer.singleShot(7000, self.inject_background_discord_monitoring)
        else:
            print("❌ Background Discord monitor failed to load")
    
    def inject_background_discord_monitoring(self):
        """Inject monitoring script into background Discord view."""
        try:
            print("🔧 Injecting background Discord monitoring script...")
            
            # Load Discord server ID from config
            import os
            import json
            discord_config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
            discord_server_id = "680606980875747344"  # Default fallback
            
            if os.path.exists(discord_config_path):
                try:
                    with open(discord_config_path, 'r') as f:
                        config = json.load(f)
                        discord_server_id = config.get('server_id', discord_server_id)
                except Exception as e:
                    print(f"⚠️ Error loading Discord config for monitoring: {e}")
            
            # SIMPLIFIED monitoring script for better performance
            background_monitoring_script = """
            console.log('TrackPro: Lightweight Discord monitoring starting...');
            
            // Lightweight notification detection - ONLY for Sim Coaches server
            var bgSeenNotifications = new Set();
            var targetServerId = '""" + str(discord_server_id) + """';  // Only monitor this server
            
            function isInTargetServer() {
                // Check if we're in the correct server context
                var currentUrl = window.location.href;
                return currentUrl.includes('/channels/' + targetServerId);
            }
            
            function checkBackgroundNotifications() {
                try {
                    // SIMPLIFIED: Quick check for any notification badges
                    if (!window.location.href.includes('/channels/' + targetServerId)) {
                        return; // Not in target server
                    }
                    
                    // Simple badge check - look for any obvious notification indicators
                    var badges = document.querySelectorAll('[class*="numberBadge"]:not([class*="inactive"])');
                    
                    if (badges.length > 0) {
                        var totalNotifications = 0;
                        
                        badges.forEach(function(badge) {
                            var text = badge.textContent ? badge.textContent.trim() : '';
                            if (text && /^\\d+$/.test(text)) {
                                totalNotifications += parseInt(text);
                            } else if (text) {
                                totalNotifications += 1; // Non-numeric badges count as 1
                            }
                        });
                        
                        if (totalNotifications > 0) {
                            window.trackproBgNotification = {
                                type: 'simple',
                                content: totalNotifications.toString(),
                                server: targetServerId,
                                timestamp: Date.now()
                            };
                        }
                    }
                    
                } catch(e) {
                    console.log('TrackPro BG: Monitor error:', e);
                }
            }
            
            // Start monitoring immediately
            checkBackgroundNotifications();
            
            // Continue monitoring every 10 seconds (reduced frequency for performance)
            setInterval(checkBackgroundNotifications, 10000);
            
            // Add debug info to page (temporarily)
            var debugDiv = document.createElement('div');
            debugDiv.style.cssText = 'position: fixed; top: 5px; left: 5px; background: rgba(255,0,0,0.8); color: white; padding: 5px; z-index: 99999; font-size: 10px;';
            debugDiv.innerHTML = 'TrackPro Background Monitor: ACTIVE';
            document.body.appendChild(debugDiv);
            
            setTimeout(function() {
                if (debugDiv.parentNode) {
                    debugDiv.parentNode.removeChild(debugDiv);
                }
            }, 3000);
            
            console.log('TrackPro: Background Discord monitoring is now active');
            """
            
            # Inject the script
            self.background_discord_monitor.page().runJavaScript(background_monitoring_script)
            
            # Start polling for background notifications
            if not hasattr(self, 'background_notification_timer'):
                self.background_notification_timer = QTimer()
                self.background_notification_timer.timeout.connect(self.check_background_discord_notifications)
                self.background_notification_timer.start(2000)  # Check every 2 seconds
                
            print("✅ Background Discord monitoring script injected and polling started")
            
        except Exception as e:
            print(f"❌ Error injecting background monitoring: {e}")
            import traceback
            traceback.print_exc()
    
    def check_background_discord_notifications(self):
        """Check for notifications from background Discord monitor."""
        if hasattr(self, 'background_discord_monitor') and self.background_discord_monitor:
            try:
                # Poll for background notifications
                self.background_discord_monitor.page().runJavaScript(
                    """
                    if (window.trackproBgNotification) {
                        var notif = window.trackproBgNotification;
                        window.trackproBgNotification = null; // Clear it
                        notif;
                    } else {
                        null;
                    }
                    """,
                    self.handle_background_discord_notification
                )
            except Exception as e:
                # Don't spam the console with errors
                pass
    
    def handle_background_discord_notification(self, notification_data):
        """Handle notification from background Discord monitor."""
        if notification_data and self.notification_manager:
            try:
                content = notification_data.get('content', 'Unknown')
                notif_type = notification_data.get('type', 'unknown')
                server_id = notification_data.get('server', '')
                
                # CRITICAL: Only process notifications from our Sim Coaches server
                import os
                import json
                discord_config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
                expected_server_id = None
                
                if os.path.exists(discord_config_path):
                    try:
                        with open(discord_config_path, 'r') as f:
                            config = json.load(f)
                            expected_server_id = config.get('server_id')
                    except Exception as e:
                        print(f"⚠️ Error loading Discord config: {e}")
                
                # Validate server ID matches our configuration
                if expected_server_id and server_id != expected_server_id:
                    print(f"🚫 Ignoring notification from other server: {server_id} (expected: {expected_server_id})")
                    return
                
                print(f"🔔 Background Discord notification from Sim Coaches server: {notif_type} - {content}")
                
                # Increment Discord notifications
                current = self.notification_manager.get_notification_count("discord")
                
                # Give different weights based on notification type
                if notif_type == 'new_badge' or 'NEW' in content:
                    increment = 2  # NEW badges are important
                elif notif_type == 'badge' and content.isdigit():
                    increment = int(content) if int(content) <= 10 else 10  # Cap at 10
                else:
                    increment = 1  # Default increment
                
                self.notification_manager.update_notification_count("discord", current + increment)
                
                # CRITICAL: Emit signal to update main UI badge immediately
                total_notifications = self.notification_manager.get_total_notifications()
                print(f"📊 Total notifications: {total_notifications} - Emitting signal to main UI")
                self.notification_count_changed.emit(total_notifications)
                
                # Also try to directly update main window if accessible
                if hasattr(self, 'parent') and self.parent():
                    main_window = self.parent()
                    if hasattr(main_window, 'update_community_notification_badge'):
                        print(f"🎯 Directly updating main window badge: {total_notifications}")
                        main_window.update_community_notification_badge(total_notifications)
                
            except Exception as e:
                print(f"❌ Error handling background notification: {e}")
    
    def check_discord_notifications(self):
        """Manually check Discord for new notifications"""
        if hasattr(self, 'discord_widget_instance'):
            try:
                # Get the Discord web view
                discord_web_view = None
                if hasattr(self.discord_widget_instance, 'discord_web_view'):
                    discord_web_view = self.discord_widget_instance.discord_web_view
                
                if discord_web_view:
                    # Call the manual check function in JavaScript
                    discord_web_view.page().runJavaScript("""
                        console.log('TrackPro: Manual check requested from Qt');
                        if (window.trackproManualCheck) {
                            window.trackproManualCheck();
                        } else {
                            console.log('TrackPro: Manual check function not available - monitoring may not be initialized');
                        }
                    """)
                    
                    # Also trigger status check for debugging
                    discord_web_view.page().runJavaScript("""
                        if (window.trackproStatus) {
                            window.trackproStatus();
                        }
                    """)
                    
                    print("✅ Manual Discord check triggered")
                else:
                    print("❌ Discord web view not available")
                    
            except Exception as e:
                print(f"❌ Error triggering Discord check: {e}")
        else:
            print("❌ Discord widget not available")
            # Fallback: directly update notification for testing
            current = self.notification_manager.get_notification_count("discord")
            self.notification_manager.update_notification_count("discord", current + 1)

    def force_auth_refresh(self):
        """Force refresh of authentication state - called by main app after successful login"""
        try:
            print("Community widget: Force refreshing authentication state...")
            from trackpro.database.supabase_client import get_supabase_client
            
            # Get the authenticated client
            supabase_client = get_supabase_client()
            if supabase_client:
                # Check if we can get user info immediately
                user_id = None
                try:
                    user_response = supabase_client.auth.get_user()
                    if user_response and hasattr(user_response, 'user') and user_response.user:
                        user_id = user_response.user.id
                        print(f"Community widget: Force refresh - got user ID: {user_id}")
                except Exception as e:
                    print(f"Community widget: Force refresh - couldn't get user immediately: {e}")
                
                # Force a fresh authentication handling
                self.handle_auth_state_change(True)
                return True
            else:
                print("Community widget: Force refresh - no client available")
                return False
        except Exception as e:
            print(f"Error in force auth refresh: {e}")
            return False


# Factory function for creating the community widget
def create_community_widget(parent=None):
    """Create a community widget for embedding in the main application"""
    # Check if QApplication exists before creating widgets
    from PyQt6.QtWidgets import QApplication
    if QApplication.instance() is None:
        print("No QApplication instance available - cannot create community widget")
        return None
        
    return CommunityMainWidget(parent)


if __name__ == "__main__":
    # Test the community widget
    app = QApplication(sys.argv)
    
    # Create and show the community widget
    widget = CommunityMainWidget()
    widget.setWindowTitle("TrackPro Community")
    widget.resize(1200, 800)
    widget.show()
    
    sys.exit(app.exec()) 