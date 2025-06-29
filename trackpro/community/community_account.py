"""
Community Account Settings Components
Contains all account settings, profile management, and user preferences for TrackPro Community.
"""

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from .community_theme import CommunityTheme


class CommunityAccountMixin:
    """Mixin class containing all account settings and profile functionality"""
    
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
            tab_widget.setStyleSheet(self._get_tab_style())
            
            # Profile Settings Tab
            profile_widget = self.create_profile_settings_panel()
            tab_widget.addTab(profile_widget, "👤 Profile")
            
            # Privacy Settings Tab
            privacy_widget = self.create_privacy_settings_panel()
            tab_widget.addTab(privacy_widget, "🔒 Privacy")
            
            # Notifications Tab
            notifications_widget = self.create_notifications_settings_panel()
            tab_widget.addTab(notifications_widget, "🔔 Notifications")
            
            # Racing Preferences Tab
            racing_widget = self.create_racing_preferences_panel()
            tab_widget.addTab(racing_widget, "🏁 Racing")
            
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
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setText("U")  # Default to first letter of username
        
        avatar_buttons_layout = QVBoxLayout()
        change_avatar_btn = QPushButton("Change Avatar")
        change_avatar_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent']))
        change_avatar_btn.clicked.connect(self.change_avatar)
        
        remove_avatar_btn = QPushButton("Remove Avatar")
        remove_avatar_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['surface'], secondary=True))
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
        check_availability_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['active']))
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
        
        # Favorite Track
        racing_section_layout.addWidget(self.create_setting_field("Favorite Track", "Your most preferred racing circuit", "combo", ["Silverstone", "Spa-Francorchamps", "Nürburgring", "Monza", "Suzuka", "Circuit de la Sarthe", "Watkins Glen", "Other"]))
        
        layout.addWidget(racing_section)
        
        # Save button
        save_btn = QPushButton("Save Profile Changes")
        save_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent'], large=True))
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
        
        layout.addWidget(communication_section)
        
        # Activity & Status Section
        activity_section, activity_section_layout = self.create_settings_section("Activity & Status", "🟢")
        
        # Online Status
        online_status_widget = QWidget()
        online_status_layout = QHBoxLayout(online_status_widget)
        online_status_checkbox = QCheckBox("Show online status to others")
        online_status_checkbox.setChecked(True)
        online_status_checkbox.setStyleSheet(self._get_checkbox_style())
        online_status_layout.addWidget(online_status_checkbox)
        online_status_layout.addStretch()
        activity_section_layout.addWidget(online_status_widget)
        
        # Currently Racing Status
        racing_status_widget = QWidget()
        racing_status_layout = QHBoxLayout(racing_status_widget)
        racing_status_checkbox = QCheckBox("Show when you're currently racing")
        racing_status_checkbox.setChecked(True)
        racing_status_checkbox.setStyleSheet(self._get_checkbox_style())
        racing_status_layout.addWidget(racing_status_checkbox)
        racing_status_layout.addStretch()
        activity_section_layout.addWidget(racing_status_widget)
        
        layout.addWidget(activity_section)
        
        # Save button
        save_btn = QPushButton("Save Privacy Settings")
        save_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent'], large=True))
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
        ]
        
        for title, description in email_notifications:
            notification_widget = self.create_notification_setting(title, description, False)
            email_section_layout.addWidget(notification_widget)
            
        layout.addWidget(email_section)
        
        # Notification Timing Section
        timing_section, timing_section_layout = self.create_settings_section("Notification Timing", "⏰")
        
        timing_section_layout.addWidget(self.create_setting_field("Quiet Hours Start", "Don't send notifications after this time", "time", "22:00"))
        timing_section_layout.addWidget(self.create_setting_field("Quiet Hours End", "Resume notifications after this time", "time", "08:00"))
        
        # Time zone
        timing_section_layout.addWidget(self.create_setting_field("Time Zone", "Your local time zone", "combo", ["UTC-8 (PST)", "UTC-5 (EST)", "UTC+0 (GMT)", "UTC+1 (CET)", "UTC+9 (JST)"]))
        
        layout.addWidget(timing_section)
        
        # Save button
        save_btn = QPushButton("Save Notification Settings")
        save_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent'], large=True))
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
        telemetry_checkbox.setStyleSheet(self._get_checkbox_style())
        telemetry_layout.addWidget(telemetry_checkbox)
        telemetry_layout.addStretch()
        telemetry_section_layout.addWidget(telemetry_widget)
        
        # Auto-analyze laps
        analyze_widget = QWidget()
        analyze_layout = QHBoxLayout(analyze_widget)
        analyze_checkbox = QCheckBox("Auto-analyze lap times and suggest improvements")
        analyze_checkbox.setChecked(True)
        analyze_checkbox.setStyleSheet(self._get_checkbox_style())
        analyze_layout.addWidget(analyze_checkbox)
        analyze_layout.addStretch()
        telemetry_section_layout.addWidget(analyze_widget)
        
        telemetry_section_layout.addWidget(self.create_setting_field("Data Retention", "How long to keep telemetry data", "combo", ["1 month", "3 months", "6 months", "1 year", "Forever"]))
        
        layout.addWidget(telemetry_section)
        
        # Save button
        save_btn = QPushButton("Save Racing Preferences")
        save_btn.setStyleSheet(self._get_button_style(CommunityTheme.COLORS['accent'], large=True))
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
        title_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
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
        label_widget.setFont(QFont('Arial', 13, QFont.Weight.Medium))
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
            input_widget.setStyleSheet(self._get_input_style())
        elif field_type == "textarea":
            input_widget = QTextEdit()
            input_widget.setMaximumHeight(100)
            if default_value:
                input_widget.setPlainText(str(default_value))
            input_widget.setStyleSheet(self._get_input_style())
        elif field_type == "combo":
            input_widget = QComboBox()
            if isinstance(default_value, list):
                input_widget.addItems(default_value)
            input_widget.setFixedHeight(40)
            input_widget.setStyleSheet(self._get_combo_style())
        elif field_type == "time":
            input_widget = QLineEdit()
            if default_value:
                input_widget.setText(str(default_value))
            input_widget.setPlaceholderText("HH:MM")
            input_widget.setFixedHeight(40)
            input_widget.setFixedWidth(120)
            input_widget.setStyleSheet(self._get_input_style())
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
        checkbox.setStyleSheet(self._get_checkbox_style())
        
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
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
                'show_online_status': True,
                'show_racing_status': True,
                'show_recent_activity': True,
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
                'email_notifications': {
                    'weekly_summary': False,
                    'event_reminders': True,
                    'account_updates': True,
                    'new_features': False,
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
                'default_racing_view': 'cockpit',
                'difficulty_level': 'intermediate',
                'assist_preferences': 'some_assists',
                'auto_save_telemetry': True,
                'auto_analyze_laps': True,
                'data_retention': '6_months',
            }
            
            success = self.db_managers['user_manager'].update_user_preferences(self.user_id, preferences)
            
            if success:
                QMessageBox.information(self, "Settings Saved", "Your racing preferences have been saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save racing preferences.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving racing preferences: {str(e)}")
    
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
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 0px 12px;
                color: {CommunityTheme.COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {CommunityTheme.COLORS['accent']};
                background-color: {CommunityTheme.COLORS['background']};
            }}
            QLineEdit:hover, QTextEdit:hover {{
                background-color: {CommunityTheme.COLORS['background']};
            }}
            QTextEdit {{
                padding: 12px;
            }}
        """
    
    def _get_combo_style(self):
        """Get combo box style"""
        return f"""
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
        """
    
    def _get_checkbox_style(self):
        """Get checkbox style"""
        return f"""
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
        """ 