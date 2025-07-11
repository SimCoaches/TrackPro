"""
TrackPro Main Community UI Integration
Unified interface combining all community features with the main application
"""

import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from datetime import datetime
import json
from typing import Dict, List, Optional, Any

# Import all community UI components
from .community_ui import CommunityMainWidget, CommunityTheme
from .content_management_ui import ContentManagementMainWidget
from .social_ui import SocialMainWidget
from .achievements_ui import GamificationMainWidget
from .user_account_ui import UserAccountMainWidget

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
                background-color: {CommunityTheme.COLORS['surface']};
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
                background-color: {CommunityTheme.COLORS['primary']};
                border-bottom: 1px solid {CommunityTheme.COLORS['border']};
            }}
        """)
        
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(4)
        
        title_label = QLabel("Community")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        subtitle_label = QLabel("Connect • Compete • Share")
        subtitle_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        subtitle_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        # Navigation buttons
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 16, 0, 16)
        nav_layout.setSpacing(4)
        
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
            nav_layout.addWidget(button)
            
        nav_layout.addStretch()
        
        # Quick stats
        stats_widget = self.create_stats_widget()
        nav_layout.addWidget(stats_widget)
        
        layout.addWidget(header_widget)
        layout.addWidget(nav_widget)
        
        # Set initial selection
        self.set_active_section("social")
        
    def create_nav_button(self, section_id: str, title: str, description: str) -> QPushButton:
        """Create a navigation button"""
        button = QPushButton()
        button.setFixedHeight(80)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.select_section(section_id))
        
        # Create custom widget for button content
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        desc_label.setWordWrap(True)
        
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        
        # Set button layout
        button_layout = QVBoxLayout(button)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(widget)
        
        return button
        
    def create_stats_widget(self) -> QWidget:
        """Create quick stats widget"""
        stats_widget = QWidget()
        stats_widget.setFixedHeight(120)
        stats_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['accent']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                margin: 16px;
            }}
        """)
        
        layout = QVBoxLayout(stats_widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        title_label = QLabel("Quick Stats")
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Placeholder stats
        stats_text = """
        🏆 Level 12 • 2,450 XP
        👥 23 Friends Online
        📁 156 Content Items
        """
        
        stats_label = QLabel(stats_text.strip())
        stats_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        stats_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        layout.addWidget(title_label)
        layout.addWidget(stats_label)
        
        return stats_widget
        
    def select_section(self, section_id: str):
        """Select a navigation section"""
        if section_id != self.current_section:
            self.set_active_section(section_id)
            self.section_changed.emit(section_id)
            
    def set_active_section(self, section_id: str):
        """Set the active section and update button styles"""
        self.current_section = section_id
        
        for btn_id, button in self.nav_buttons.items():
            if btn_id == section_id:
                # Active button style
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {CommunityTheme.COLORS['primary']};
                        border: none;
                        border-radius: 0px;
                        text-align: left;
                        color: {CommunityTheme.COLORS['text_primary']};
                    }}
                    QPushButton:hover {{
                        background-color: {CommunityTheme.COLORS['hover']};
                    }}
                """)
            else:
                # Inactive button style
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 0px;
                        text-align: left;
                        color: {CommunityTheme.COLORS['text_secondary']};
                    }}
                    QPushButton:hover {{
                        background-color: {CommunityTheme.COLORS['accent']};
                        color: {CommunityTheme.COLORS['text_primary']};
                    }}
                """)

class CommunityStatusBar(QWidget):
    """Status bar showing community information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the status bar UI"""
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface']};
                border-top: 1px solid {CommunityTheme.COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)
        
        # Connection status
        self.connection_label = QLabel("🟢 Connected")
        self.connection_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        self.connection_label.setStyleSheet(f"color: {CommunityTheme.COLORS['success']};")
        
        # Online friends count
        self.friends_label = QLabel("👥 23 friends online")
        self.friends_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        self.friends_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        # Notifications
        self.notifications_label = QLabel("🔔 3 new notifications")
        self.notifications_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        self.notifications_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']};")
        self.notifications_label.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Last sync time
        self.sync_label = QLabel("Last sync: Just now")
        self.sync_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        self.sync_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_muted']};")
        
        layout.addWidget(self.connection_label)
        layout.addWidget(self.friends_label)
        layout.addWidget(self.notifications_label)
        layout.addStretch()
        layout.addWidget(self.sync_label)
        
    def update_connection_status(self, connected: bool):
        """Update connection status"""
        if connected:
            self.connection_label.setText("🟢 Connected")
            self.connection_label.setStyleSheet(f"color: {CommunityTheme.COLORS['success']};")
        else:
            self.connection_label.setText("🔴 Disconnected")
            self.connection_label.setStyleSheet(f"color: {CommunityTheme.COLORS['danger']};")
            
    def update_friends_count(self, count: int):
        """Update online friends count"""
        self.friends_label.setText(f"👥 {count} friends online")
        
    def update_notifications(self, count: int):
        """Update notifications count"""
        if count > 0:
            self.notifications_label.setText(f"🔔 {count} new notifications")
            self.notifications_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']};")
        else:
            self.notifications_label.setText("🔔 No new notifications")
            self.notifications_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_muted']};")
            
    def update_sync_time(self):
        """Update last sync time"""
        current_time = datetime.now().strftime("%H:%M")
        self.sync_label.setText(f"Last sync: {current_time}")

class CommunityMainInterface(QWidget):
    """Main community interface integrating all features"""
    
    def __init__(self, managers: Dict[str, Any], user_id: str, parent=None):
        super().__init__(parent)
        self.managers = managers
        self.user_id = user_id
        self.current_widget = None
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
        
        # Status bar
        self.status_bar = CommunityStatusBar()
        
        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_layout.addWidget(self.content_stack)
        main_layout.addWidget(self.status_bar)
        
        layout.addWidget(self.navigation)
        layout.addWidget(main_widget)
        
        # Set initial section
        self.switch_section("social")
        
    def create_section_widgets(self):
        """Create widgets for each community section"""
        # Social section
        if 'user_manager' in self.managers and 'friends_manager' in self.managers:
            self.social_widget = SocialMainWidget(
                self.managers['user_manager'],
                self.managers['friends_manager'],
                self.managers['messaging_manager'],
                self.managers['activity_manager'],
                self.user_id
            )
            self.content_stack.addWidget(self.social_widget)
        else:
            # Placeholder if managers not available
            placeholder = self.create_placeholder_widget("Social features will be available when managers are loaded.")
            self.content_stack.addWidget(placeholder)
            
        # Community section
        if 'community_manager' in self.managers:
            self.community_widget = CommunityMainWidget(
                self.managers['community_manager'],
                self.user_id
            )
            self.content_stack.addWidget(self.community_widget)
        else:
            placeholder = self.create_placeholder_widget("Community features will be available when managers are loaded.")
            self.content_stack.addWidget(placeholder)
            
        # Content section
        if 'content_manager' in self.managers:
            self.content_widget = ContentManagementMainWidget(
                self.managers['content_manager'],
                self.user_id
            )
            self.content_stack.addWidget(self.content_widget)
        else:
            placeholder = self.create_placeholder_widget("Content management will be available when managers are loaded.")
            self.content_stack.addWidget(placeholder)
            
        # Achievements section
        if 'achievements_manager' in self.managers:
            self.achievements_widget = GamificationMainWidget(
                self.managers['achievements_manager'],
                self.managers.get('reputation_manager'),
                self.user_id
            )
            self.content_stack.addWidget(self.achievements_widget)
        else:
            placeholder = self.create_placeholder_widget("Achievements will be available when managers are loaded.")
            self.content_stack.addWidget(placeholder)
            
        # Account section
        if 'user_manager' in self.managers:
            self.account_widget = UserAccountMainWidget(
                self.managers['user_manager'],
                self.user_id
            )
            self.content_stack.addWidget(self.account_widget)
        else:
            placeholder = self.create_placeholder_widget("Account settings will be available when managers are loaded.")
            self.content_stack.addWidget(placeholder)
            
    def create_placeholder_widget(self, message: str) -> QWidget:
        """Create a placeholder widget with a message"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel("🚧")
        icon_label.setFont(QFont('Segoe UI Emoji', 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_muted']};")
        
        message_label = QLabel(message)
        message_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        message_label.setWordWrap(True)
        
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        
        return widget
        
    def switch_section(self, section_id: str):
        """Switch to a different community section"""
        section_indices = {
            "social": 0,
            "community": 1,
            "content": 2,
            "achievements": 3,
            "account": 4
        }
        
        if section_id in section_indices:
            index = section_indices[section_id]
            self.content_stack.setCurrentIndex(index)
            self.current_widget = self.content_stack.currentWidget()
            
            # Update navigation
            self.navigation.set_active_section(section_id)
            
    def get_current_section(self) -> str:
        """Get the currently active section"""
        return self.navigation.current_section
        
    def refresh_current_section(self):
        """Refresh the current section"""
        if hasattr(self.current_widget, 'refresh'):
            self.current_widget.refresh()
            
    def update_status(self, **kwargs):
        """Update status bar information"""
        if 'connected' in kwargs:
            self.status_bar.update_connection_status(kwargs['connected'])
        if 'friends_online' in kwargs:
            self.status_bar.update_friends_count(kwargs['friends_online'])
        if 'notifications' in kwargs:
            self.status_bar.update_notifications(kwargs['notifications'])
        if 'sync_time' in kwargs and kwargs['sync_time']:
            self.status_bar.update_sync_time()

class CommunityIntegrationDialog(QDialog):
    """Dialog for integrating community features into the main application"""
    
    def __init__(self, managers: Dict[str, Any], user_id: str, parent=None):
        super().__init__(parent)
        self.managers = managers
        self.user_id = user_id
        self.setWindowTitle("TrackPro Community")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the integration dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main community interface
        self.community_interface = CommunityMainInterface(self.managers, self.user_id)
        layout.addWidget(self.community_interface)
        
        # Apply theme
        self.setStyleSheet(CommunityTheme.get_stylesheet())
        
    def show_section(self, section_id: str):
        """Show a specific community section"""
        self.community_interface.switch_section(section_id)
        
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Save any pending changes or state
        event.accept()

# Integration functions for the main TrackPro application

def create_community_menu_action(parent, managers: Dict[str, Any], user_id: str) -> QAction:
    """Create a menu action for opening the community interface"""
    action = QAction("🌐 Community", parent)
    action.setStatusTip("Open TrackPro Community features")
    action.triggered.connect(lambda: open_community_dialog(parent, managers, user_id))
    return action

def create_community_toolbar_button(parent, managers: Dict[str, Any], user_id: str) -> QPushButton:
    """Create a toolbar button for quick access to community features"""
    button = QPushButton("🌐 Community")
    button.setToolTip("Open TrackPro Community")
    button.clicked.connect(lambda: open_community_dialog(parent, managers, user_id))
    return button

def open_community_dialog(parent, managers: Dict[str, Any], user_id: str, section: str = "social"):
    """Open the community dialog"""
    dialog = CommunityIntegrationDialog(managers, user_id, parent)
    dialog.show_section(section)
    dialog.exec()

def create_community_widget(managers: Dict[str, Any], user_id: str, parent=None) -> CommunityMainInterface:
    """Create a community widget for embedding in the main application"""
    return CommunityMainInterface(managers, user_id, parent)

# Quick access functions for specific community features

def open_social_features(parent, managers: Dict[str, Any], user_id: str):
    """Quick access to social features"""
    open_community_dialog(parent, managers, user_id, "social")

def open_community_features(parent, managers: Dict[str, Any], user_id: str):
    """Quick access to community features (teams, clubs, events)"""
    open_community_dialog(parent, managers, user_id, "community")

def open_content_management(parent, managers: Dict[str, Any], user_id: str):
    """Quick access to content management"""
    open_community_dialog(parent, managers, user_id, "content")

def open_achievements(parent, managers: Dict[str, Any], user_id: str):
    """Quick access to achievements and gamification"""
    open_community_dialog(parent, managers, user_id, "achievements")

def open_account_settings(parent, managers: Dict[str, Any], user_id: str):
    """Quick access to account settings"""
    open_community_dialog(parent, managers, user_id, "account")

if __name__ == "__main__":
    # Test the main community interface
    app = QApplication(sys.argv)
    
    # Mock managers for testing
    mock_managers = {
        'user_manager': None,
        'friends_manager': None,
        'messaging_manager': None,
        'activity_manager': None,
        'community_manager': None,
        'content_manager': None,
        'achievements_manager': None,
        'reputation_manager': None
    }
    
    # Create and show the community interface
    dialog = CommunityIntegrationDialog(mock_managers, 'test_user')
    dialog.show()
    
    sys.exit(app.exec()) 