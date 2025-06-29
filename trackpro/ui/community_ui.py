"""
TrackPro Community UI Components
Racing-themed community interface for teams, clubs, events, and content management
"""

import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any

class CommunityTheme:
    """Racing-inspired theme for community components"""
    
    # Color scheme
    COLORS = {
        'primary': '#FF6B35',           # Racing orange
        'secondary': '#1A1A2E',        # Dark navy
        'accent': '#16213E',           # Darker navy
        'success': '#00D4AA',          # Teal green
        'warning': '#FFD23F',          # Racing yellow
        'danger': '#FF4757',           # Racing red
        'info': '#3742FA',             # Electric blue
        'background': '#0F0F23',       # Very dark navy
        'surface': '#16213E',          # Card background
        'text_primary': '#FFFFFF',     # White text
        'text_secondary': '#B8BCC8',   # Light gray
        'text_muted': '#6C7293',       # Muted gray
        'border': '#2A2D47',           # Border color
        'hover': '#FF8A65',            # Hover orange
        'selected': '#FF6B35',         # Selected orange
        'online': '#00D4AA',           # Online green
        'offline': '#6C7293',          # Offline gray
        'gradient_start': '#FF6B35',   # Gradient start
        'gradient_end': '#FF8A65'      # Gradient end
    }
    
    # Typography
    FONTS = {
        'heading': ('Segoe UI', 16, QFont.Weight.Bold),
        'subheading': ('Segoe UI', 14, QFont.Weight.Bold),
        'body': ('Segoe UI', 10, QFont.Weight.Normal),
        'caption': ('Segoe UI', 9, QFont.Weight.Normal),
        'button': ('Segoe UI', 10, QFont.Weight.Medium)
    }
    
    @staticmethod
    def get_stylesheet() -> str:
        """Get the complete stylesheet for community components"""
        return f"""
        /* Base styling */
        QWidget {{
            background-color: {CommunityTheme.COLORS['background']};
            color: {CommunityTheme.COLORS['text_primary']};
            font-family: 'Segoe UI';
        }}
        
        /* Cards and containers */
        .community-card {{
            background-color: {CommunityTheme.COLORS['surface']};
            border: 1px solid {CommunityTheme.COLORS['border']};
            border-radius: 8px;
            padding: 16px;
            margin: 8px;
        }}
        
        .community-card:hover {{
            border-color: {CommunityTheme.COLORS['primary']};
            background-color: {CommunityTheme.COLORS['accent']};
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {CommunityTheme.COLORS['primary']};
            color: {CommunityTheme.COLORS['text_primary']};
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10px;
        }}
        
        QPushButton:hover {{
            background-color: {CommunityTheme.COLORS['hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {CommunityTheme.COLORS['accent']};
        }}
        
        QPushButton:disabled {{
            background-color: {CommunityTheme.COLORS['text_muted']};
            color: {CommunityTheme.COLORS['text_secondary']};
        }}
        
        /* Secondary buttons */
        .secondary-button {{
            background-color: transparent;
            border: 2px solid {CommunityTheme.COLORS['primary']};
            color: {CommunityTheme.COLORS['primary']};
        }}
        
        .secondary-button:hover {{
            background-color: {CommunityTheme.COLORS['primary']};
            color: {CommunityTheme.COLORS['text_primary']};
        }}
        
        /* Input fields */
        QLineEdit, QTextEdit, QComboBox {{
            background-color: {CommunityTheme.COLORS['accent']};
            border: 2px solid {CommunityTheme.COLORS['border']};
            border-radius: 6px;
            padding: 8px;
            color: {CommunityTheme.COLORS['text_primary']};
            font-size: 10px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border-color: {CommunityTheme.COLORS['primary']};
        }}
        
        /* Lists and tables */
        QListWidget, QTableWidget {{
            background-color: {CommunityTheme.COLORS['surface']};
            border: 1px solid {CommunityTheme.COLORS['border']};
            border-radius: 6px;
            alternate-background-color: {CommunityTheme.COLORS['accent']};
        }}
        
        QListWidget::item, QTableWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {CommunityTheme.COLORS['border']};
        }}
        
        QListWidget::item:selected, QTableWidget::item:selected {{
            background-color: {CommunityTheme.COLORS['primary']};
            color: {CommunityTheme.COLORS['text_primary']};
        }}
        
        QListWidget::item:hover, QTableWidget::item:hover {{
            background-color: {CommunityTheme.COLORS['hover']};
        }}
        
        /* Headers */
        QHeaderView::section {{
            background-color: {CommunityTheme.COLORS['primary']};
            color: {CommunityTheme.COLORS['text_primary']};
            padding: 8px;
            border: none;
            font-weight: bold;
        }}
        
        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {CommunityTheme.COLORS['border']};
            background-color: {CommunityTheme.COLORS['surface']};
        }}
        
        QTabBar::tab {{
            background-color: {CommunityTheme.COLORS['accent']};
            color: {CommunityTheme.COLORS['text_secondary']};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {CommunityTheme.COLORS['primary']};
            color: {CommunityTheme.COLORS['text_primary']};
        }}
        
        QTabBar::tab:hover {{
            background-color: {CommunityTheme.COLORS['hover']};
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {CommunityTheme.COLORS['accent']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {CommunityTheme.COLORS['primary']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {CommunityTheme.COLORS['hover']};
        }}
        
        /* Progress bars */
        QProgressBar {{
            background-color: {CommunityTheme.COLORS['accent']};
            border: 1px solid {CommunityTheme.COLORS['border']};
            border-radius: 6px;
            text-align: center;
            color: {CommunityTheme.COLORS['text_primary']};
        }}
        
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {CommunityTheme.COLORS['gradient_start']},
                stop:1 {CommunityTheme.COLORS['gradient_end']});
            border-radius: 6px;
        }}
        
        /* Status indicators */
        .status-online {{
            color: {CommunityTheme.COLORS['online']};
        }}
        
        .status-offline {{
            color: {CommunityTheme.COLORS['offline']};
        }}
        
        .status-success {{
            color: {CommunityTheme.COLORS['success']};
        }}
        
        .status-warning {{
            color: {CommunityTheme.COLORS['warning']};
        }}
        
        .status-danger {{
            color: {CommunityTheme.COLORS['danger']};
        }}
        """

class TeamCard(QWidget):
    """Racing team display card with join/leave functionality"""
    
    team_clicked = pyqtSignal(dict)
    join_requested = pyqtSignal(str)
    leave_requested = pyqtSignal(str)
    
    def __init__(self, team_data: Dict[str, Any], user_id: str, parent=None):
        super().__init__(parent)
        self.team_data = team_data
        self.user_id = user_id
        self.is_member = self._check_membership()
        self.setup_ui()
        
    def _check_membership(self) -> bool:
        """Check if current user is a member of this team"""
        members = self.team_data.get('members', [])
        return any(member.get('user_id') == self.user_id for member in members)
        
    def setup_ui(self):
        """Setup the team card UI"""
        self.setFixedHeight(200)
        self.setObjectName("community-card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with logo and name
        header_layout = QHBoxLayout()
        
        # Team logo
        logo_label = QLabel()
        logo_label.setFixedSize(48, 48)
        logo_label.setStyleSheet(f"""
            QLabel {{
                background-color: {CommunityTheme.COLORS['primary']};
                border-radius: 24px;
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Use first letter of team name as logo if no image
        team_name = self.team_data.get('name', 'Team')
        logo_label.setText(team_name[0].upper())
        
        # Team info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(team_name)
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Member count and privacy
        member_count = len(self.team_data.get('members', []))
        max_members = self.team_data.get('max_members', 50)
        privacy = self.team_data.get('privacy_level', 'public')
        
        stats_text = f"{member_count}/{max_members} members • {privacy.title()}"
        stats_label = QLabel(stats_text)
        stats_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        stats_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(stats_label)
        info_layout.addStretch()
        
        header_layout.addWidget(logo_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Description
        description = self.team_data.get('description', 'No description available.')
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        view_button = QPushButton("View Team")
        view_button.clicked.connect(lambda: self.team_clicked.emit(self.team_data))
        
        if self.is_member:
            action_button = QPushButton("Leave Team")
            action_button.setObjectName("secondary-button")
            action_button.clicked.connect(lambda: self.leave_requested.emit(self.team_data['id']))
        else:
            action_button = QPushButton("Join Team")
            action_button.clicked.connect(lambda: self.join_requested.emit(self.team_data['id']))
            
        button_layout.addWidget(view_button)
        button_layout.addWidget(action_button)
        button_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.team_clicked.emit(self.team_data)

class ClubCard(QWidget):
    """Racing club display card"""
    
    club_clicked = pyqtSignal(dict)
    join_requested = pyqtSignal(str)
    leave_requested = pyqtSignal(str)
    
    def __init__(self, club_data: Dict[str, Any], user_id: str, parent=None):
        super().__init__(parent)
        self.club_data = club_data
        self.user_id = user_id
        self.is_member = self._check_membership()
        self.setup_ui()
        
    def _check_membership(self) -> bool:
        """Check if current user is a member of this club"""
        members = self.club_data.get('members', [])
        return any(member.get('user_id') == self.user_id for member in members)
        
    def setup_ui(self):
        """Setup the club card UI"""
        self.setFixedHeight(180)
        self.setObjectName("community-card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Club category icon
        category = self.club_data.get('category', 'General')
        category_icons = {
            'GT3': '🏎️',
            'Formula': '🏁',
            'Oval': '🏟️',
            'Rally': '🚗',
            'Endurance': '⏱️',
            'General': '🏆'
        }
        
        icon_label = QLabel(category_icons.get(category, '🏆'))
        icon_label.setFont(QFont('Segoe UI Emoji', 24))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Club info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_label = QLabel(self.club_data.get('name', 'Club'))
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        category_label = QLabel(f"{category} Club")
        category_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        category_label.setStyleSheet(f"color: {CommunityTheme.COLORS['primary']};")
        
        member_count = self.club_data.get('member_count', 0)
        members_label = QLabel(f"{member_count} members")
        members_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        members_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(category_label)
        info_layout.addWidget(members_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Description
        description = self.club_data.get('description', 'No description available.')
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        view_button = QPushButton("View Club")
        view_button.clicked.connect(lambda: self.club_clicked.emit(self.club_data))
        
        if self.is_member:
            action_button = QPushButton("Leave Club")
            action_button.setObjectName("secondary-button")
            action_button.clicked.connect(lambda: self.leave_requested.emit(self.club_data['id']))
        else:
            action_button = QPushButton("Join Club")
            action_button.clicked.connect(lambda: self.join_requested.emit(self.club_data['id']))
            
        button_layout.addWidget(view_button)
        button_layout.addWidget(action_button)
        button_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.club_clicked.emit(self.club_data)

class EventCard(QWidget):
    """Community event display card"""
    
    event_clicked = pyqtSignal(dict)
    register_requested = pyqtSignal(str)
    unregister_requested = pyqtSignal(str)
    
    def __init__(self, event_data: Dict[str, Any], user_id: str, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.user_id = user_id
        self.is_registered = self._check_registration()
        self.setup_ui()
        
    def _check_registration(self) -> bool:
        """Check if current user is registered for this event"""
        participants = self.event_data.get('participants', [])
        return any(p.get('user_id') == self.user_id for p in participants)
        
    def setup_ui(self):
        """Setup the event card UI"""
        self.setFixedHeight(220)
        self.setObjectName("community-card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header with event type and status
        header_layout = QHBoxLayout()
        
        # Event type icon
        event_type = self.event_data.get('event_type', 'race')
        type_icons = {
            'time_trial': '⏱️',
            'race': '🏁',
            'championship': '🏆',
            'practice': '🔧',
            'endurance': '⏳'
        }
        
        icon_label = QLabel(type_icons.get(event_type, '🏁'))
        icon_label.setFont(QFont('Segoe UI Emoji', 20))
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Event info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        title_label = QLabel(self.event_data.get('title', 'Event'))
        title_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        type_label = QLabel(event_type.replace('_', ' ').title())
        type_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        type_label.setStyleSheet(f"color: {CommunityTheme.COLORS['primary']};")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(type_label)
        
        # Status indicator
        status = self.event_data.get('status', 'upcoming')
        status_colors = {
            'upcoming': CommunityTheme.COLORS['info'],
            'active': CommunityTheme.COLORS['success'],
            'completed': CommunityTheme.COLORS['text_muted'],
            'cancelled': CommunityTheme.COLORS['danger']
        }
        
        status_label = QLabel(status.title())
        status_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        status_label.setStyleSheet(f"color: {status_colors.get(status, CommunityTheme.COLORS['text_secondary'])};")
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        header_layout.addWidget(status_label)
        
        # Event details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)
        
        # Date and time
        start_time = self.event_data.get('start_time')
        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = start_time.strftime("%B %d, %Y at %I:%M %p")
            time_label = QLabel(f"📅 {time_str}")
            time_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            time_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            details_layout.addWidget(time_label)
        
        # Track and car info
        track_id = self.event_data.get('track_id')
        car_id = self.event_data.get('car_id')
        if track_id or car_id:
            track_car_text = []
            if track_id:
                track_car_text.append(f"Track: {track_id}")
            if car_id:
                track_car_text.append(f"Car: {car_id}")
            
            track_car_label = QLabel(f"🏎️ {' • '.join(track_car_text)}")
            track_car_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            track_car_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            details_layout.addWidget(track_car_label)
        
        # Participants
        participant_count = len(self.event_data.get('participants', []))
        max_participants = self.event_data.get('max_participants')
        if max_participants:
            participants_text = f"👥 {participant_count}/{max_participants} participants"
        else:
            participants_text = f"👥 {participant_count} participants"
            
        participants_label = QLabel(participants_text)
        participants_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        participants_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        details_layout.addWidget(participants_label)
        
        # Description
        description = self.event_data.get('description', '')
        if description:
            desc_label = QLabel(description)
            desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
            desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            desc_label.setWordWrap(True)
            desc_label.setMaximumHeight(30)
            details_layout.addWidget(desc_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        view_button = QPushButton("View Details")
        view_button.clicked.connect(lambda: self.event_clicked.emit(self.event_data))
        
        # Registration button (only for upcoming events)
        if status == 'upcoming':
            if self.is_registered:
                action_button = QPushButton("Unregister")
                action_button.setObjectName("secondary-button")
                action_button.clicked.connect(lambda: self.unregister_requested.emit(self.event_data['id']))
            else:
                action_button = QPushButton("Register")
                action_button.clicked.connect(lambda: self.register_requested.emit(self.event_data['id']))
            button_layout.addWidget(action_button)
            
        button_layout.addWidget(view_button)
        button_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(details_layout)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def mousePressEvent(self, event):
        """Handle card click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.event_clicked.emit(self.event_data)

class TeamsWidget(QWidget):
    """Widget for browsing and managing racing teams"""
    
    def __init__(self, community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.community_manager = community_manager
        self.user_id = user_id
        self.teams = []
        self.setup_ui()
        self.load_teams()
        
    def setup_ui(self):
        """Setup the teams widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header with search and filters
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Racing Teams")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search teams...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self.filter_teams)
        
        # Create team button
        create_button = QPushButton("Create Team")
        create_button.clicked.connect(self.show_create_team_dialog)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(create_button)
        
        # Filter tabs
        self.tab_widget = QTabWidget()
        
        # All teams tab
        self.all_teams_scroll = QScrollArea()
        self.all_teams_scroll.setWidgetResizable(True)
        self.all_teams_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.all_teams_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.all_teams_widget = QWidget()
        self.all_teams_layout = QVBoxLayout(self.all_teams_widget)
        self.all_teams_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.all_teams_scroll.setWidget(self.all_teams_widget)
        
        # My teams tab
        self.my_teams_scroll = QScrollArea()
        self.my_teams_scroll.setWidgetResizable(True)
        self.my_teams_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.my_teams_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.my_teams_widget = QWidget()
        self.my_teams_layout = QVBoxLayout(self.my_teams_widget)
        self.my_teams_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.my_teams_scroll.setWidget(self.my_teams_widget)
        
        self.tab_widget.addTab(self.all_teams_scroll, "All Teams")
        self.tab_widget.addTab(self.my_teams_scroll, "My Teams")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.tab_widget)
        
    def load_teams(self):
        """Load teams from the community manager"""
        try:
            # Get all teams
            all_teams_result = self.community_manager.search_teams()
            if all_teams_result['success']:
                self.teams = all_teams_result['teams']
                self.display_teams()
            else:
                self.show_error("Failed to load teams")
                
        except Exception as e:
            self.show_error(f"Error loading teams: {str(e)}")
            
    def display_teams(self):
        """Display teams in the appropriate tabs"""
        # Clear existing widgets
        self.clear_layout(self.all_teams_layout)
        self.clear_layout(self.my_teams_layout)
        
        my_teams = []
        all_teams = []
        
        for team in self.teams:
            team_card = TeamCard(team, self.user_id)
            team_card.team_clicked.connect(self.show_team_details)
            team_card.join_requested.connect(self.join_team)
            team_card.leave_requested.connect(self.leave_team)
            
            all_teams.append(team_card)
            
            # Check if user is a member
            if team_card.is_member:
                my_team_card = TeamCard(team, self.user_id)
                my_team_card.team_clicked.connect(self.show_team_details)
                my_team_card.join_requested.connect(self.join_team)
                my_team_card.leave_requested.connect(self.leave_team)
                my_teams.append(my_team_card)
        
        # Add cards to layouts
        for card in all_teams:
            self.all_teams_layout.addWidget(card)
            
        for card in my_teams:
            self.my_teams_layout.addWidget(card)
            
        # Add stretch to push cards to top
        self.all_teams_layout.addStretch()
        self.my_teams_layout.addStretch()
        
        # Update tab titles with counts
        self.tab_widget.setTabText(0, f"All Teams ({len(all_teams)})")
        self.tab_widget.setTabText(1, f"My Teams ({len(my_teams)})")
        
    def filter_teams(self):
        """Filter teams based on search input"""
        search_text = self.search_input.text().lower()
        
        for i in range(self.all_teams_layout.count() - 1):  # -1 for stretch
            widget = self.all_teams_layout.itemAt(i).widget()
            if isinstance(widget, TeamCard):
                team_name = widget.team_data.get('name', '').lower()
                team_desc = widget.team_data.get('description', '').lower()
                visible = search_text in team_name or search_text in team_desc
                widget.setVisible(visible)
                
    def clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def show_create_team_dialog(self):
        """Show dialog to create a new team"""
        dialog = CreateTeamDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            team_data = dialog.get_team_data()
            self.create_team(team_data)
            
    def create_team(self, team_data: Dict[str, Any]):
        """Create a new team"""
        try:
            result = self.community_manager.create_team(
                name=team_data['name'],
                description=team_data['description'],
                max_members=team_data['max_members'],
                privacy_level=team_data['privacy_level']
            )
            
            if result['success']:
                self.show_success("Team created successfully!")
                self.load_teams()  # Refresh the list
            else:
                self.show_error(f"Failed to create team: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error creating team: {str(e)}")
            
    def join_team(self, team_id: str):
        """Join a team"""
        try:
            result = self.community_manager.join_team(team_id)
            if result['success']:
                self.show_success("Successfully joined team!")
                self.load_teams()  # Refresh the list
            else:
                self.show_error(f"Failed to join team: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error joining team: {str(e)}")
            
    def leave_team(self, team_id: str):
        """Leave a team"""
        reply = QMessageBox.question(
            self, "Leave Team",
            "Are you sure you want to leave this team?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.community_manager.leave_team(team_id)
                if result['success']:
                    self.show_success("Successfully left team!")
                    self.load_teams()  # Refresh the list
                else:
                    self.show_error(f"Failed to leave team: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.show_error(f"Error leaving team: {str(e)}")
                
    def show_team_details(self, team_data: Dict[str, Any]):
        """Show detailed team information"""
        dialog = TeamDetailsDialog(team_data, self.community_manager, self.user_id, self)
        dialog.exec()
        
    def show_success(self, message: str):
        """Show success message"""
        QMessageBox.information(self, "Success", message)
        
    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)

class ClubsWidget(QWidget):
    """Widget for browsing and managing racing clubs"""
    
    def __init__(self, community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.community_manager = community_manager
        self.user_id = user_id
        self.clubs = []
        self.setup_ui()
        self.load_clubs()
        
    def setup_ui(self):
        """Setup the clubs widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header with search and filters
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Racing Clubs")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search clubs...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self.filter_clubs)
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItems(['All Categories', 'GT3', 'Formula', 'Oval', 'Rally', 'Endurance', 'General'])
        self.category_combo.currentTextChanged.connect(self.filter_clubs)
        
        # Create club button
        create_button = QPushButton("Create Club")
        create_button.clicked.connect(self.show_create_club_dialog)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.category_combo)
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(create_button)
        
        # Filter tabs
        self.tab_widget = QTabWidget()
        
        # All clubs tab
        self.all_clubs_scroll = QScrollArea()
        self.all_clubs_scroll.setWidgetResizable(True)
        self.all_clubs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.all_clubs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.all_clubs_widget = QWidget()
        self.all_clubs_layout = QGridLayout(self.all_clubs_widget)
        self.all_clubs_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.all_clubs_scroll.setWidget(self.all_clubs_widget)
        
        # My clubs tab
        self.my_clubs_scroll = QScrollArea()
        self.my_clubs_scroll.setWidgetResizable(True)
        self.my_clubs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.my_clubs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.my_clubs_widget = QWidget()
        self.my_clubs_layout = QGridLayout(self.my_clubs_widget)
        self.my_clubs_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.my_clubs_scroll.setWidget(self.my_clubs_widget)
        
        self.tab_widget.addTab(self.all_clubs_scroll, "All Clubs")
        self.tab_widget.addTab(self.my_clubs_scroll, "My Clubs")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.tab_widget)
        
    def load_clubs(self):
        """Load clubs from the community manager"""
        try:
            # Get all clubs
            all_clubs_result = self.community_manager.search_clubs()
            if all_clubs_result['success']:
                self.clubs = all_clubs_result['clubs']
                self.display_clubs()
            else:
                self.show_error("Failed to load clubs")
                
        except Exception as e:
            self.show_error(f"Error loading clubs: {str(e)}")
            
    def display_clubs(self):
        """Display clubs in grid layout"""
        # Clear existing widgets
        self.clear_layout(self.all_clubs_layout)
        self.clear_layout(self.my_clubs_layout)
        
        my_clubs = []
        all_clubs = []
        
        for club in self.clubs:
            club_card = ClubCard(club, self.user_id)
            club_card.club_clicked.connect(self.show_club_details)
            club_card.join_requested.connect(self.join_club)
            club_card.leave_requested.connect(self.leave_club)
            
            all_clubs.append(club_card)
            
            # Check if user is a member
            if club_card.is_member:
                my_club_card = ClubCard(club, self.user_id)
                my_club_card.club_clicked.connect(self.show_club_details)
                my_club_card.join_requested.connect(self.join_club)
                my_club_card.leave_requested.connect(self.leave_club)
                my_clubs.append(my_club_card)
        
        # Add cards to grid layouts (3 columns)
        for i, card in enumerate(all_clubs):
            row = i // 3
            col = i % 3
            self.all_clubs_layout.addWidget(card, row, col)
            
        for i, card in enumerate(my_clubs):
            row = i // 3
            col = i % 3
            self.my_clubs_layout.addWidget(card, row, col)
            
        # Update tab titles with counts
        self.tab_widget.setTabText(0, f"All Clubs ({len(all_clubs)})")
        self.tab_widget.setTabText(1, f"My Clubs ({len(my_clubs)})")
        
    def filter_clubs(self):
        """Filter clubs based on search input and category"""
        search_text = self.search_input.text().lower()
        selected_category = self.category_combo.currentText()
        
        for i in range(self.all_clubs_layout.count()):
            widget = self.all_clubs_layout.itemAt(i).widget()
            if isinstance(widget, ClubCard):
                club_name = widget.club_data.get('name', '').lower()
                club_desc = widget.club_data.get('description', '').lower()
                club_category = widget.club_data.get('category', '')
                
                text_match = search_text in club_name or search_text in club_desc
                category_match = (selected_category == 'All Categories' or 
                                selected_category == club_category)
                
                visible = text_match and category_match
                widget.setVisible(visible)
                
    def clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def show_create_club_dialog(self):
        """Show dialog to create a new club"""
        dialog = CreateClubDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            club_data = dialog.get_club_data()
            self.create_club(club_data)
            
    def create_club(self, club_data: Dict[str, Any]):
        """Create a new club"""
        try:
            result = self.community_manager.create_club(
                name=club_data['name'],
                description=club_data['description'],
                category=club_data['category'],
                privacy_level=club_data['privacy_level']
            )
            
            if result['success']:
                self.show_success("Club created successfully!")
                self.load_clubs()  # Refresh the list
            else:
                self.show_error(f"Failed to create club: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error creating club: {str(e)}")
            
    def join_club(self, club_id: str):
        """Join a club"""
        try:
            result = self.community_manager.join_club(club_id)
            if result['success']:
                self.show_success("Successfully joined club!")
                self.load_clubs()  # Refresh the list
            else:
                self.show_error(f"Failed to join club: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error joining club: {str(e)}")
            
    def leave_club(self, club_id: str):
        """Leave a club"""
        reply = QMessageBox.question(
            self, "Leave Club",
            "Are you sure you want to leave this club?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.community_manager.leave_club(club_id)
                if result['success']:
                    self.show_success("Successfully left club!")
                    self.load_clubs()  # Refresh the list
                else:
                    self.show_error(f"Failed to leave club: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.show_error(f"Error leaving club: {str(e)}")
                
    def show_club_details(self, club_data: Dict[str, Any]):
        """Show detailed club information"""
        dialog = ClubDetailsDialog(club_data, self.community_manager, self.user_id, self)
        dialog.exec()
        
    def show_success(self, message: str):
        """Show success message"""
        QMessageBox.information(self, "Success", message)
        
    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)

class EventsWidget(QWidget):
    """Widget for browsing and managing community events"""
    
    def __init__(self, community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.community_manager = community_manager
        self.user_id = user_id
        self.events = []
        self.setup_ui()
        self.load_events()
        
    def setup_ui(self):
        """Setup the events widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Header with search and filters
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Community Events")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search events...")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self.filter_events)
        
        # Event type filter
        self.type_combo = QComboBox()
        self.type_combo.addItems(['All Types', 'Time Trial', 'Race', 'Championship', 'Practice', 'Endurance'])
        self.type_combo.currentTextChanged.connect(self.filter_events)
        
        # Status filter
        self.status_combo = QComboBox()
        self.status_combo.addItems(['All Status', 'Upcoming', 'Active', 'Completed'])
        self.status_combo.currentTextChanged.connect(self.filter_events)
        
        # Create event button
        create_button = QPushButton("Create Event")
        create_button.clicked.connect(self.show_create_event_dialog)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_combo)
        header_layout.addWidget(self.type_combo)
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(create_button)
        
        # Filter tabs
        self.tab_widget = QTabWidget()
        
        # All events tab
        self.all_events_scroll = QScrollArea()
        self.all_events_scroll.setWidgetResizable(True)
        self.all_events_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.all_events_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.all_events_widget = QWidget()
        self.all_events_layout = QVBoxLayout(self.all_events_widget)
        self.all_events_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.all_events_scroll.setWidget(self.all_events_widget)
        
        # My events tab
        self.my_events_scroll = QScrollArea()
        self.my_events_scroll.setWidgetResizable(True)
        self.my_events_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.my_events_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.my_events_widget = QWidget()
        self.my_events_layout = QVBoxLayout(self.my_events_widget)
        self.my_events_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.my_events_scroll.setWidget(self.my_events_widget)
        
        self.tab_widget.addTab(self.all_events_scroll, "All Events")
        self.tab_widget.addTab(self.my_events_scroll, "My Events")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.tab_widget)
        
    def load_events(self):
        """Load events from the community manager"""
        try:
            # Get all events
            all_events_result = self.community_manager.get_events()
            if all_events_result['success']:
                self.events = all_events_result['events']
                self.display_events()
            else:
                self.show_error("Failed to load events")
                
        except Exception as e:
            self.show_error(f"Error loading events: {str(e)}")
            
    def display_events(self):
        """Display events in the appropriate tabs"""
        # Clear existing widgets
        self.clear_layout(self.all_events_layout)
        self.clear_layout(self.my_events_layout)
        
        my_events = []
        all_events = []
        
        for event in self.events:
            event_card = EventCard(event, self.user_id)
            event_card.event_clicked.connect(self.show_event_details)
            event_card.register_requested.connect(self.register_for_event)
            event_card.unregister_requested.connect(self.unregister_from_event)
            
            all_events.append(event_card)
            
            # Check if user is registered or created the event
            if (event_card.is_registered or 
                event.get('created_by') == self.user_id):
                my_event_card = EventCard(event, self.user_id)
                my_event_card.event_clicked.connect(self.show_event_details)
                my_event_card.register_requested.connect(self.register_for_event)
                my_event_card.unregister_requested.connect(self.unregister_from_event)
                my_events.append(my_event_card)
        
        # Add cards to layouts
        for card in all_events:
            self.all_events_layout.addWidget(card)
            
        for card in my_events:
            self.my_events_layout.addWidget(card)
            
        # Add stretch to push cards to top
        self.all_events_layout.addStretch()
        self.my_events_layout.addStretch()
        
        # Update tab titles with counts
        self.tab_widget.setTabText(0, f"All Events ({len(all_events)})")
        self.tab_widget.setTabText(1, f"My Events ({len(my_events)})")
        
    def filter_events(self):
        """Filter events based on search input, type, and status"""
        search_text = self.search_input.text().lower()
        selected_type = self.type_combo.currentText()
        selected_status = self.status_combo.currentText()
        
        for i in range(self.all_events_layout.count() - 1):  # -1 for stretch
            widget = self.all_events_layout.itemAt(i).widget()
            if isinstance(widget, EventCard):
                event_title = widget.event_data.get('title', '').lower()
                event_desc = widget.event_data.get('description', '').lower()
                event_type = widget.event_data.get('event_type', '').replace('_', ' ').title()
                event_status = widget.event_data.get('status', '').title()
                
                text_match = search_text in event_title or search_text in event_desc
                type_match = (selected_type == 'All Types' or selected_type == event_type)
                status_match = (selected_status == 'All Status' or selected_status == event_status)
                
                visible = text_match and type_match and status_match
                widget.setVisible(visible)
                
    def clear_layout(self, layout):
        """Clear all widgets from a layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def show_create_event_dialog(self):
        """Show dialog to create a new event"""
        dialog = CreateEventDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            event_data = dialog.get_event_data()
            self.create_event(event_data)
            
    def create_event(self, event_data: Dict[str, Any]):
        """Create a new event"""
        try:
            result = self.community_manager.create_event(
                title=event_data['title'],
                description=event_data['description'],
                event_type=event_data['event_type'],
                start_time=event_data['start_time'],
                end_time=event_data['end_time'],
                track_id=event_data.get('track_id'),
                car_id=event_data.get('car_id'),
                max_participants=event_data.get('max_participants'),
                entry_requirements=event_data.get('entry_requirements', {}),
                prizes=event_data.get('prizes', {})
            )
            
            if result['success']:
                self.show_success("Event created successfully!")
                self.load_events()  # Refresh the list
            else:
                self.show_error(f"Failed to create event: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error creating event: {str(e)}")
            
    def register_for_event(self, event_id: str):
        """Register for an event"""
        try:
            result = self.community_manager.register_for_event(event_id)
            if result['success']:
                self.show_success("Successfully registered for event!")
                self.load_events()  # Refresh the list
            else:
                self.show_error(f"Failed to register: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.show_error(f"Error registering for event: {str(e)}")
            
    def unregister_from_event(self, event_id: str):
        """Unregister from an event"""
        reply = QMessageBox.question(
            self, "Unregister from Event",
            "Are you sure you want to unregister from this event?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.community_manager.unregister_from_event(event_id)
                if result['success']:
                    self.show_success("Successfully unregistered from event!")
                    self.load_events()  # Refresh the list
                else:
                    self.show_error(f"Failed to unregister: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self.show_error(f"Error unregistering from event: {str(e)}")
                
    def show_event_details(self, event_data: Dict[str, Any]):
        """Show detailed event information"""
        dialog = EventDetailsDialog(event_data, self.community_manager, self.user_id, self)
        dialog.exec()
        
    def show_success(self, message: str):
        """Show success message"""
        QMessageBox.information(self, "Success", message)
        
    def show_error(self, message: str):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)

class CommunityMainWidget(QWidget):
    """Main community interface combining all community features"""
    
    def __init__(self, community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.community_manager = community_manager
        self.user_id = user_id
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the main community interface"""
        # Apply theme
        self.setStyleSheet(CommunityTheme.get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("TrackPro Community")
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        title_label.setStyleSheet(f"""
            color: {CommunityTheme.COLORS['text_primary']};
            font-size: 24px;
            font-weight: bold;
        """)
        
        # Community stats
        stats_layout = QHBoxLayout()
        
        # Placeholder stats - these would be loaded from the community manager
        stats_data = [
            ("Teams", "42"),
            ("Clubs", "18"),
            ("Events", "7"),
            ("Members", "1,234")
        ]
        
        for stat_name, stat_value in stats_data:
            stat_widget = QWidget()
            stat_widget.setFixedSize(100, 60)
            stat_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {CommunityTheme.COLORS['surface']};
                    border: 1px solid {CommunityTheme.COLORS['border']};
                    border-radius: 8px;
                }}
            """)
            
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(8, 8, 8, 8)
            stat_layout.setSpacing(2)
            
            value_label = QLabel(stat_value)
            value_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
            value_label.setStyleSheet(f"color: {CommunityTheme.COLORS['primary']};")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            name_label = QLabel(stat_name)
            name_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
            name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            stat_layout.addWidget(value_label)
            stat_layout.addWidget(name_label)
            
            stats_layout.addWidget(stat_widget)
            
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addLayout(stats_layout)
        
        # Main content tabs
        self.tab_widget = QTabWidget()
        
        # Teams tab
        self.teams_widget = TeamsWidget(self.community_manager, self.user_id)
        self.tab_widget.addTab(self.teams_widget, "🏁 Teams")
        
        # Clubs tab
        self.clubs_widget = ClubsWidget(self.community_manager, self.user_id)
        self.tab_widget.addTab(self.clubs_widget, "🏆 Clubs")
        
        # Events tab
        self.events_widget = EventsWidget(self.community_manager, self.user_id)
        self.tab_widget.addTab(self.events_widget, "📅 Events")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.tab_widget)

# Dialog classes for creating teams, clubs, and events would go here
# These are simplified placeholders - full implementations would include
# comprehensive forms with validation

class CreateTeamDialog(QDialog):
    """Dialog for creating a new racing team"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Racing Team")
        self.setFixedSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the create team dialog UI"""
        layout = QVBoxLayout(self)
        
        # Team name
        layout.addWidget(QLabel("Team Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter team name...")
        layout.addWidget(self.name_input)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe your team...")
        self.description_input.setMaximumHeight(100)
        layout.addWidget(self.description_input)
        
        # Max members
        layout.addWidget(QLabel("Maximum Members:"))
        self.max_members_input = QSpinBox()
        self.max_members_input.setRange(2, 100)
        self.max_members_input.setValue(20)
        layout.addWidget(self.max_members_input)
        
        # Privacy level
        layout.addWidget(QLabel("Privacy Level:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(['public', 'private'])
        layout.addWidget(self.privacy_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        create_button = QPushButton("Create Team")
        create_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(create_button)
        
        layout.addLayout(button_layout)
        
    def get_team_data(self) -> Dict[str, Any]:
        """Get the team data from the form"""
        return {
            'name': self.name_input.text(),
            'description': self.description_input.toPlainText(),
            'max_members': self.max_members_input.value(),
            'privacy_level': self.privacy_combo.currentText()
        }

class CreateClubDialog(QDialog):
    """Dialog for creating a new racing club"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Racing Club")
        self.setFixedSize(400, 350)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the create club dialog UI"""
        layout = QVBoxLayout(self)
        
        # Club name
        layout.addWidget(QLabel("Club Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter club name...")
        layout.addWidget(self.name_input)
        
        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(['GT3', 'Formula', 'Oval', 'Rally', 'Endurance', 'General'])
        layout.addWidget(self.category_combo)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe your club...")
        self.description_input.setMaximumHeight(100)
        layout.addWidget(self.description_input)
        
        # Privacy level
        layout.addWidget(QLabel("Privacy Level:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(['public', 'private'])
        layout.addWidget(self.privacy_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        create_button = QPushButton("Create Club")
        create_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(create_button)
        
        layout.addLayout(button_layout)
        
    def get_club_data(self) -> Dict[str, Any]:
        """Get the club data from the form"""
        return {
            'name': self.name_input.text(),
            'description': self.description_input.toPlainText(),
            'category': self.category_combo.currentText(),
            'privacy_level': self.privacy_combo.currentText()
        }

class CreateEventDialog(QDialog):
    """Dialog for creating a new community event"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Community Event")
        self.setFixedSize(500, 600)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the create event dialog UI"""
        layout = QVBoxLayout(self)
        
        # Event title
        layout.addWidget(QLabel("Event Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter event title...")
        layout.addWidget(self.title_input)
        
        # Event type
        layout.addWidget(QLabel("Event Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['time_trial', 'race', 'championship', 'practice', 'endurance'])
        layout.addWidget(self.type_combo)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe the event...")
        self.description_input.setMaximumHeight(80)
        layout.addWidget(self.description_input)
        
        # Start time
        layout.addWidget(QLabel("Start Time:"))
        self.start_time_input = QDateTimeEdit()
        self.start_time_input.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.start_time_input.setCalendarPopup(True)
        layout.addWidget(self.start_time_input)
        
        # End time
        layout.addWidget(QLabel("End Time:"))
        self.end_time_input = QDateTimeEdit()
        self.end_time_input.setDateTime(QDateTime.currentDateTime().addDays(1).addSecs(3600))
        self.end_time_input.setCalendarPopup(True)
        layout.addWidget(self.end_time_input)
        
        # Track ID (simplified)
        layout.addWidget(QLabel("Track ID (optional):"))
        self.track_input = QLineEdit()
        self.track_input.setPlaceholderText("Enter track ID...")
        layout.addWidget(self.track_input)
        
        # Car ID (simplified)
        layout.addWidget(QLabel("Car ID (optional):"))
        self.car_input = QLineEdit()
        self.car_input.setPlaceholderText("Enter car ID...")
        layout.addWidget(self.car_input)
        
        # Max participants
        layout.addWidget(QLabel("Maximum Participants (optional):"))
        self.max_participants_input = QSpinBox()
        self.max_participants_input.setRange(0, 1000)
        self.max_participants_input.setValue(0)  # 0 means unlimited
        self.max_participants_input.setSpecialValueText("Unlimited")
        layout.addWidget(self.max_participants_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        create_button = QPushButton("Create Event")
        create_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(create_button)
        
        layout.addLayout(button_layout)
        
    def get_event_data(self) -> Dict[str, Any]:
        """Get the event data from the form"""
        data = {
            'title': self.title_input.text(),
            'description': self.description_input.toPlainText(),
            'event_type': self.type_combo.currentText(),
            'start_time': self.start_time_input.dateTime().toPyDateTime(),
            'end_time': self.end_time_input.dateTime().toPyDateTime()
        }
        
        # Optional fields
        if self.track_input.text():
            data['track_id'] = int(self.track_input.text()) if self.track_input.text().isdigit() else None
            
        if self.car_input.text():
            data['car_id'] = int(self.car_input.text()) if self.car_input.text().isdigit() else None
            
        if self.max_participants_input.value() > 0:
            data['max_participants'] = self.max_participants_input.value()
            
        return data

# Placeholder detail dialogs
class TeamDetailsDialog(QDialog):
    """Dialog showing detailed team information"""
    
    def __init__(self, team_data: Dict[str, Any], community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.team_data = team_data
        self.community_manager = community_manager
        self.user_id = user_id
        self.setWindowTitle(f"Team: {team_data.get('name', 'Unknown')}")
        self.setFixedSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the team details dialog UI"""
        layout = QVBoxLayout(self)
        
        # Team name and description
        name_label = QLabel(self.team_data.get('name', 'Unknown Team'))
        name_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        layout.addWidget(name_label)
        
        desc_label = QLabel(self.team_data.get('description', 'No description available.'))
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Members list (simplified)
        layout.addWidget(QLabel("Members:"))
        members_list = QListWidget()
        for member in self.team_data.get('members', []):
            members_list.addItem(f"{member.get('username', 'Unknown')} ({member.get('role', 'member')})")
        layout.addWidget(members_list)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class ClubDetailsDialog(QDialog):
    """Dialog showing detailed club information"""
    
    def __init__(self, club_data: Dict[str, Any], community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.club_data = club_data
        self.community_manager = community_manager
        self.user_id = user_id
        self.setWindowTitle(f"Club: {club_data.get('name', 'Unknown')}")
        self.setFixedSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the club details dialog UI"""
        layout = QVBoxLayout(self)
        
        # Club name and description
        name_label = QLabel(self.club_data.get('name', 'Unknown Club'))
        name_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        layout.addWidget(name_label)
        
        category_label = QLabel(f"Category: {self.club_data.get('category', 'General')}")
        layout.addWidget(category_label)
        
        desc_label = QLabel(self.club_data.get('description', 'No description available.'))
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Members count
        member_count = self.club_data.get('member_count', 0)
        members_label = QLabel(f"Members: {member_count}")
        layout.addWidget(members_label)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class EventDetailsDialog(QDialog):
    """Dialog showing detailed event information"""
    
    def __init__(self, event_data: Dict[str, Any], community_manager, user_id: str, parent=None):
        super().__init__(parent)
        self.event_data = event_data
        self.community_manager = community_manager
        self.user_id = user_id
        self.setWindowTitle(f"Event: {event_data.get('title', 'Unknown')}")
        self.setFixedSize(600, 500)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the event details dialog UI"""
        layout = QVBoxLayout(self)
        
        # Event title and type
        title_label = QLabel(self.event_data.get('title', 'Unknown Event'))
        title_label.setFont(QFont(*CommunityTheme.FONTS['heading']))
        layout.addWidget(title_label)
        
        type_label = QLabel(f"Type: {self.event_data.get('event_type', 'Unknown').replace('_', ' ').title()}")
        layout.addWidget(type_label)
        
        # Description
        desc_label = QLabel(self.event_data.get('description', 'No description available.'))
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Event details
        start_time = self.event_data.get('start_time')
        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_str = start_time.strftime("%B %d, %Y at %I:%M %p")
            time_label = QLabel(f"Start Time: {time_str}")
            layout.addWidget(time_label)
        
        # Participants
        participants = self.event_data.get('participants', [])
        participants_label = QLabel(f"Participants: {len(participants)}")
        layout.addWidget(participants_label)
        
        # Participants list
        if participants:
            layout.addWidget(QLabel("Registered Participants:"))
            participants_list = QListWidget()
            for participant in participants:
                participants_list.addItem(participant.get('username', 'Unknown'))
            participants_list.setMaximumHeight(150)
            layout.addWidget(participants_list)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

if __name__ == "__main__":
    # Test the community UI components
    app = QApplication(sys.argv)
    
    # Mock community manager for testing
    class MockCommunityManager:
        def search_teams(self):
            return {
                'success': True,
                'teams': [
                    {
                        'id': '1',
                        'name': 'Speed Demons',
                        'description': 'Fast and competitive racing team',
                        'max_members': 20,
                        'privacy_level': 'public',
                        'members': [{'user_id': 'test_user', 'role': 'member'}]
                    }
                ]
            }
        
        def search_clubs(self):
            return {
                'success': True,
                'clubs': [
                    {
                        'id': '1',
                        'name': 'GT3 Masters',
                        'description': 'GT3 racing enthusiasts',
                        'category': 'GT3',
                        'member_count': 45,
                        'privacy_level': 'public',
                        'members': []
                    }
                ]
            }
        
        def get_events(self):
            return {
                'success': True,
                'events': [
                    {
                        'id': '1',
                        'title': 'Weekly Time Trial',
                        'description': 'Weekly time trial challenge',
                        'event_type': 'time_trial',
                        'start_time': datetime.now() + timedelta(days=1),
                        'status': 'upcoming',
                        'participants': []
                    }
                ]
            }
    
    mock_manager = MockCommunityManager()
    
    # Create and show the main community widget
    community_widget = CommunityMainWidget(mock_manager, 'test_user')
    community_widget.show()
    
    sys.exit(app.exec()) 