"""
Community Content and Teams Components
Contains community features and content management functionality for TrackPro Community.
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .community_theme import CommunityTheme


class CommunityContentMixin:
    """Mixin class containing community and content management functionality"""
    
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
            tab_widget.setStyleSheet(self._get_tab_style())
            
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
            tab_widget.setStyleSheet(self._get_tab_style())
            
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
        create_team_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent']))
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(create_team_btn)
        layout.addLayout(header_layout)
        
        # Teams scroll area
        teams_scroll = QScrollArea()
        teams_scroll.setWidgetResizable(True)
        teams_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        teams_content = QWidget()
        teams_layout = QVBoxLayout(teams_content)
        teams_layout.setSpacing(12)
        
        # Sample teams for demo
        sample_teams = [
            ("Velocity Racing", "5 members", "Competitive GT3 racing team", "Member", True),
            ("Track Masters", "12 members", "Multi-class endurance racing", "Captain", True),
        ]
        
        for team_name, member_count, description, role, active in sample_teams:
            team_card = self.create_team_card(team_name, member_count, description, role, active)
            teams_layout.addWidget(team_card)
            
        teams_layout.addStretch()
        teams_scroll.setWidget(teams_content)
        layout.addWidget(teams_scroll)
        
        return widget
    
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
        search_input.setStyleSheet(self._get_input_style())
        search_input.setMaximumWidth(200)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(search_input)
        layout.addLayout(header_layout)
        
        # Create scroll area with sample clubs
        clubs_scroll = QScrollArea()
        clubs_scroll.setWidgetResizable(True)
        clubs_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        clubs_content = QWidget()
        clubs_layout = QVBoxLayout(clubs_content)
        clubs_layout.setSpacing(8)
        
        # Sample clubs for demo
        sample_clubs = [
            ("Formula Masters", "150 members", "Open wheel racing specialists", False, "club_1"),
            ("GT Legends", "87 members", "GT3 and GTE racing community", True, "club_2"),
        ]
        
        for club_name, member_count, description, is_member, club_id in sample_clubs:
            club_item = self.create_club_item(club_name, member_count, description, is_member, club_id)
            clubs_layout.addWidget(club_item)
            
        clubs_layout.addStretch()
        clubs_scroll.setWidget(clubs_content)
        layout.addWidget(clubs_scroll)
        
        return widget
    
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
        filter_combo.setStyleSheet(self._get_combo_style())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(filter_combo)
        layout.addLayout(header_layout)
        
        # Events scroll area with sample events
        events_scroll = QScrollArea()
        events_scroll.setWidgetResizable(True)
        events_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        events_content = QWidget()
        self.events_layout = QVBoxLayout(events_content)
        self.events_layout.setSpacing(12)
        
        self.refresh_events()

        events_scroll.setWidget(events_content)
        layout.addWidget(events_scroll)
        
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
        filter_combo.setStyleSheet(self._get_combo_style())
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(filter_combo)
        layout.addLayout(header_layout)
        
        # Create content with real data from database
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        self.my_content_layout = QVBoxLayout(content_widget)
        self.my_content_layout.setSpacing(12)
        
        self.refresh_my_content()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return widget
    
    def refresh_my_content(self):
        """Refreshes the 'My Content' panel with data from the database."""
        if not hasattr(self, 'my_content_layout'):
            return

        # Clear existing widgets
        while self.my_content_layout.count():
            child = self.my_content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Load real content from database
        if hasattr(self, 'db_managers') and self.db_managers and 'content_manager' in self.db_managers and hasattr(self, 'user_id') and self.user_id:
            try:
                content_items = self.db_managers['content_manager'].get_user_content(self.user_id)
                
                if content_items:
                    for item in content_items:
                        content_card = self.create_content_card(
                            item['id'],
                            item['title'],
                            item.get('type', 'Media'),
                            item.get('category', 'General'),
                            item.get('stats', '0 views'),
                            self.format_time_ago(item.get('uploaded')),
                            is_mine=True
                        )
                        self.my_content_layout.addWidget(content_card)
                else:
                    empty_label = QLabel("You haven't shared any content yet. Go to the Upload tab to share!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    empty_label.setWordWrap(True)
                    self.my_content_layout.addWidget(empty_label)

            except Exception as e:
                error_label = QLabel(f"Could not load your content: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                self.my_content_layout.addWidget(error_label)
        else:
            placeholder_label = QLabel("Log in and connect to the database to see your content.")
            placeholder_label.setAlignment(Qt.AlignCenter)
            placeholder_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
            self.my_content_layout.addWidget(placeholder_label)

        self.my_content_layout.addStretch()

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
        search_input.setStyleSheet(self._get_input_style())
        
        category_combo = QComboBox()
        category_combo.addItems(["All Categories", "Car Setups", "Videos", "Screenshots", "Guides"])
        category_combo.setStyleSheet(self._get_combo_style())
        
        sort_combo = QComboBox()
        sort_combo.addItems(["Most Recent", "Most Popular", "Most Downloaded", "Highest Rated"])
        sort_combo.setStyleSheet(self._get_combo_style())
        
        header_layout.addWidget(search_input)
        header_layout.addWidget(category_combo)
        header_layout.addWidget(sort_combo)
        layout.addLayout(header_layout)
        
        # Featured content label
        featured_label = QLabel("🔥 Featured Content")
        featured_label.setFont(QFont(*CommunityTheme.FONTS['subheading']))
        featured_label.setStyleSheet(f"color: {CommunityTheme.COLORS['accent']}; font-weight: bold;")
        layout.addWidget(featured_label)
        
        # Browse content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        
        # Load real featured content from database
        if hasattr(self, 'db_managers') and self.db_managers and 'content_manager' in self.db_managers:
            try:
                content_items = self.db_managers['content_manager'].get_featured_content()
                if content_items:
                    for item in content_items:
                        content_card = self.create_browse_content_card(
                            item['title'],
                            item.get('type', 'Media'),
                            item.get('category', 'General'),
                            item.get('stats', '0 views'),
                            item.get('author', 'by Anonymous')
                        )
                        content_layout.addWidget(content_card)
                else:
                    empty_label = QLabel("No featured content available right now. Check back later!")
                    empty_label.setAlignment(Qt.AlignCenter)
                    empty_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
                    content_layout.addWidget(empty_label)
            except Exception as e:
                error_label = QLabel(f"Could not load featured content: {str(e)}")
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet(f"color: {CommunityTheme.COLORS['warning']}; padding: 40px;")
                content_layout.addWidget(error_label)
        else:
            placeholder_label = QLabel("Connect to the database to browse community content.")
            placeholder_label.setAlignment(Qt.AlignCenter)
            placeholder_label.setStyleSheet(f"color: {CommunityTheme.COLORS['text_secondary']}; padding: 40px;")
            content_layout.addWidget(placeholder_label)

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
        
        # Simple upload form
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
        
        # Content type
        type_combo = QComboBox()
        type_combo.addItems(["Car Setup", "Video", "Screenshot", "Guide", "Replay"])
        type_combo.setStyleSheet(self._get_combo_style())
        
        # Title and description
        title_input = QLineEdit()
        title_input.setPlaceholderText("Enter a descriptive title...")
        title_input.setStyleSheet(self._get_input_style())
        
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Describe your content...")
        desc_input.setMaximumHeight(100)
        desc_input.setStyleSheet(self._get_input_style())
        
        # Upload button
        upload_btn = QPushButton("Select File & Share Content")
        upload_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent'], large=True))
        upload_btn.clicked.connect(self.upload_content_action)
        
        form_layout.addWidget(QLabel("Content Type:"))
        form_layout.addWidget(type_combo)
        form_layout.addWidget(QLabel("Title:"))
        form_layout.addWidget(title_input)
        form_layout.addWidget(QLabel("Description:"))
        form_layout.addWidget(desc_input)
        form_layout.addWidget(upload_btn)
        
        # Store references for upload_content_action
        self.upload_type_combo = type_combo
        self.upload_title_input = title_input
        self.upload_desc_input = desc_input
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        return widget
    
    def upload_content_action(self):
        """Handle content upload."""
        if not hasattr(self, 'db_managers') or not self.db_managers or 'content_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return

        # Get data from upload form
        content_type = self.upload_type_combo.currentText()
        title = self.upload_title_input.text()
        description = self.upload_desc_input.toPlainText()

        if not title:
            QMessageBox.warning(self, "Error", "Title is required.")
            return

        # Open file dialog to select the file to upload
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select {content_type} file")

        if not file_path:
            return  # User cancelled

        # In a real scenario, you would upload the file to Supabase Storage and get a URL.
        # For now, we use the local file path as a placeholder to show the UI is connected.
        file_url = f"file:///{file_path}"
        
        content_data = {
            'type': content_type,
            'title': title,
            'description': description,
            'file_url': file_url
        }

        try:
            success = self.db_managers['content_manager'].upload_content(self.user_id, content_data)
            if success:
                QMessageBox.information(self, "Success", f"'{title}' has been shared successfully!")
                self.upload_title_input.clear()
                self.upload_desc_input.clear()
                self.refresh_my_content()  # Refresh the content panel
            else:
                QMessageBox.warning(self, "Error", "Failed to share content.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while uploading: {str(e)}")

    # Helper methods for creating cards and items
    def create_team_card(self, team_name, member_count, description, role, active):
        """Create a team card widget"""
        card_widget = QWidget()
        card_widget.setStyleSheet(self._get_card_style())
        
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
        view_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['surface'], secondary=True))
        
        chat_btn = QPushButton("Team Chat")
        chat_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent']))
        
        actions_layout.addWidget(view_btn)
        actions_layout.addWidget(chat_btn)
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(info_layout)
        layout.addWidget(desc_label)
        layout.addLayout(actions_layout)
        
        return card_widget
    
    def create_club_item(self, club_name, member_count, description, is_member, club_id=None):
        """Create a club list item"""
        item_widget = QWidget()
        item_widget.setStyleSheet(self._get_card_style())
        
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
            action_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['active']))
        else:
            action_btn = QPushButton("Join Club")
            action_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent']))
            if club_id:
                action_btn.clicked.connect(lambda: self.join_club_action(club_name, club_id))
        
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(action_btn)
        
        return item_widget
    
    def create_event_card(self, event_name, track, date_time, registration, is_registered, event_type, event_id=None):
        """Create an event card"""
        card_widget = QWidget()
        card_widget.setStyleSheet(self._get_card_style())
        
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
            status_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['active']))
            status_btn.setEnabled(False)
        else:
            status_btn = QPushButton("Register")
            status_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent']))
            if event_id:
                status_btn.clicked.connect(lambda: self.register_for_event_action(event_id, event_name))
        
        details_btn = QPushButton("View Details")
        details_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['surface'], secondary=True))
        
        actions_layout.addWidget(status_btn)
        actions_layout.addWidget(details_btn)
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(details_layout)
        layout.addLayout(actions_layout)
        
        return card_widget
    
    def create_content_card(self, content_id, title, content_type, category, stats, uploaded, is_mine=False):
        """Create a content card"""
        card_widget = QWidget()
        card_widget.setStyleSheet(self._get_card_style())
        
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
            edit_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['surface'], secondary=True))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet(self._get_button_style("#DC2626"))
            delete_btn.clicked.connect(lambda: self.delete_content_action(content_id, title, content_type))
            
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
        card_widget.setStyleSheet(self._get_card_style())
        
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
        download_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent']))
        
        like_btn = QPushButton("👍 Like")
        like_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['surface'], secondary=True))
        
        actions_layout.addWidget(download_btn)
        actions_layout.addWidget(like_btn)
        actions_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addLayout(info_layout)
        layout.addLayout(actions_layout)
        
        return card_widget
    
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
                else:
                    QMessageBox.warning(self, "Error", "Failed to join club.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error joining club: {str(e)}")
    
    def delete_content_action(self, content_id, title, content_type):
        """Handle content deletion."""
        if not hasattr(self, 'db_managers') or not self.db_managers or 'content_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Content",
            f"Are you sure you want to delete '{title}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                success = self.db_managers['content_manager'].delete_content(self.user_id, content_id, content_type)
                if success:
                    QMessageBox.information(self, "Success", f"'{title}' has been deleted.")
                    self.refresh_my_content()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete content. You may not have permission or it may have already been deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting content: {str(e)}")
    
    def register_for_event_action(self, event_id, event_name):
        """Register for an event."""
        if not hasattr(self, 'db_managers') or not self.db_managers or 'community_manager' not in self.db_managers:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return
        
        try:
            success = self.db_managers['community_manager'].register_for_event(self.user_id, event_id)
            if success:
                QMessageBox.information(self, "Success", f"Successfully registered for {event_name}!")
                self.refresh_events()
            else:
                QMessageBox.warning(self, "Error", "Failed to register for event. It might be full or you might already be registered.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error registering for event: {str(e)}")

    # Helper style methods
    def _get_tab_style(self):
        """Get tab widget style"""
        return f"""
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
        """
    
    def _get_button_style(self, bg_color, secondary=False, large=False):
        """Get button style"""
        padding = "12px 24px" if large else "8px 16px"
        border = f"1px solid {CommunityTheme.COLORS['border']}" if secondary else "none"
        text_color = CommunityTheme.COLORS['text_primary'] if secondary else "white"
        hover_color = CommunityTheme.COLORS['active'] if secondary else "#FF8A65"
        
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                padding: {padding};
                border-radius: 4px;
                font-weight: bold;
                border: {border};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                color: white;
            }}
        """
    
    def _get_input_style(self):
        """Get input field style"""
        return f"""
            QLineEdit, QTextEdit {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                color: {CommunityTheme.COLORS['text_primary']};
            }}
        """
    
    def _get_combo_style(self):
        """Get combo box style"""
        return f"""
            QComboBox {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 4px;
                padding: 6px 12px;
                color: {CommunityTheme.COLORS['text_primary']};
                min-width: 120px;
            }}
        """
    
    def _get_card_style(self):
        """Get card widget style"""
        return f"""
            QWidget {{
                background-color: {CommunityTheme.COLORS['surface_darker']};
                border: 1px solid {CommunityTheme.COLORS['border']};
                border-radius: 8px;
                padding: 16px;
            }}
            QWidget:hover {{
                background-color: {CommunityTheme.COLORS['surface']};
            }}
        """

    def refresh_events(self):
        """Refreshes the events panel with data from the database."""
        if not hasattr(self, 'events_layout'):
            return

        while self.events_layout.count():
            child = self.events_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if hasattr(self, 'db_managers') and self.db_managers and 'community_manager' in self.db_managers and hasattr(self, 'user_id') and self.user_id:
            try:
                event_items = self.db_managers['community_manager'].get_community_events(self.user_id)
                if event_items:
                    for item in event_items:
                        event_card = self.create_event_card(
                            item['title'],
                            item.get('track_name', 'TBD'),
                            self.format_time_ago(item.get('start_time')),
                            item.get('registration_info', '0/0 registered'),
                            item.get('is_registered', False),
                            item.get('event_type', 'Open'),
                            item.get('id')
                        )
                        self.events_layout.addWidget(event_card)
                else:
                    self.events_layout.addWidget(QLabel("No upcoming events found."))
            except Exception as e:
                self.events_layout.addWidget(QLabel(f"Error loading events: {e}"))
        else:
            self.events_layout.addWidget(QLabel("Connect to DB to see events."))
        
        self.events_layout.addStretch() 