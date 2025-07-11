"""
Community UI Components for the integrated TrackPro Community
Essential widgets and components copied from the existing UI system.
"""

import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any

# Import our new theme
from .community_theme import CommunityTheme


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
                color: white;
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
        
        name_label = QLabel(self.event_data.get('name', 'Event'))
        name_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        name_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_primary']};")
        
        # Event date/time
        event_date = self.event_data.get('start_time', datetime.now())
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            except:
                event_date = datetime.now()
                
        date_label = QLabel(event_date.strftime('%Y-%m-%d %H:%M'))
        date_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        date_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        
        # Participant count
        participant_count = len(self.event_data.get('participants', []))
        max_participants = self.event_data.get('max_participants', 100)
        participants_label = QLabel(f"{participant_count}/{max_participants} participants")
        participants_label.setFont(QFont(*CommunityTheme.FONTS['caption']))
        participants_label.setStyleSheet(f"color: {CommunityTheme.COLORS['primary']};")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(date_label)
        info_layout.addWidget(participants_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Description
        description = self.event_data.get('description', 'No description available.')
        desc_label = QLabel(description)
        desc_label.setFont(QFont(*CommunityTheme.FONTS['body']))
        desc_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        desc_label.setMaximumHeight(40)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        view_button = QPushButton("View Details")
        view_button.clicked.connect(lambda: self.event_clicked.emit(self.event_data))
        
        if self.is_registered:
            action_button = QPushButton("Unregister")
            action_button.clicked.connect(lambda: self.unregister_requested.emit(self.event_data['id']))
        else:
            action_button = QPushButton("Register")
            action_button.clicked.connect(lambda: self.register_requested.emit(self.event_data['id']))
            
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
            self.event_clicked.emit(self.event_data) 