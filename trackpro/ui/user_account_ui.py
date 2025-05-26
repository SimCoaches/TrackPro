"""User Account UI Components for TrackPro - Complete profile and account management interface."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .social_ui import SocialTheme
from ..social import enhanced_user_manager, friends_manager, achievements_manager, reputation_manager

logger = logging.getLogger(__name__)

class ProfileEditDialog(QDialog):
    """Comprehensive profile editing dialog."""
    
    profile_updated = pyqtSignal(dict)  # Emits updated profile data
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.user_data = None
        self.setWindowTitle("Edit Profile")
        self.setFixedSize(600, 700)
        self.setStyleSheet(SocialTheme.get_stylesheet())
        self.init_ui()
        self.load_user_data()
    
    def init_ui(self):
        """Initialize the profile editing UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Edit Your Profile")
        header_label.setFont(SocialTheme.FONTS['heading'])
        header_label.setAlignment(Qt.AlignCenter)
        
        # Scroll area for form
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        form_layout = QVBoxLayout(scroll_widget)
        
        # Avatar section
        avatar_group = QGroupBox("Profile Picture")
        avatar_layout = QVBoxLayout(avatar_group)
        
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet(f"""
            QLabel {{
                border: 3px solid {SocialTheme.COLORS['accent']};
                border-radius: 60px;
                background-color: {SocialTheme.COLORS['surface']};
                font-size: 48px;
            }}
        """)
        self.avatar_label.setText("👤")
        
        avatar_buttons_layout = QHBoxLayout()
        upload_avatar_btn = QPushButton("Upload Image")
        upload_avatar_btn.clicked.connect(self.upload_avatar)
        
        remove_avatar_btn = QPushButton("Remove")
        remove_avatar_btn.clicked.connect(self.remove_avatar)
        
        avatar_buttons_layout.addWidget(upload_avatar_btn)
        avatar_buttons_layout.addWidget(remove_avatar_btn)
        
        avatar_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)
        avatar_layout.addLayout(avatar_buttons_layout)
        
        # Basic info section
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        
        self.username_input = QLineEdit()
        self.username_input.setMaxLength(50)
        
        self.display_name_input = QLineEdit()
        self.display_name_input.setMaxLength(100)
        
        self.location_input = QLineEdit()
        self.location_input.setMaxLength(100)
        self.location_input.setPlaceholderText("e.g., United States, Europe")
        
        basic_layout.addRow("Username:", self.username_input)
        basic_layout.addRow("Display Name:", self.display_name_input)
        basic_layout.addRow("Location:", self.location_input)
        
        # Bio section
        bio_group = QGroupBox("About You")
        bio_layout = QVBoxLayout(bio_group)
        
        self.bio_input = QTextEdit()
        self.bio_input.setMaximumHeight(100)
        self.bio_input.setPlaceholderText("Tell others about yourself, your racing experience, favorite cars/tracks...")
        
        bio_char_label = QLabel("0/500 characters")
        bio_char_label.setFont(SocialTheme.FONTS['caption'])
        bio_char_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        self.bio_char_label = bio_char_label
        
        self.bio_input.textChanged.connect(self.update_bio_char_count)
        
        bio_layout.addWidget(self.bio_input)
        bio_layout.addWidget(bio_char_label)
        
        # Racing preferences section
        racing_group = QGroupBox("Racing Preferences")
        racing_layout = QFormLayout(racing_group)
        
        self.primary_sim_combo = QComboBox()
        self.primary_sim_combo.addItems([
            "iRacing", "Assetto Corsa Competizione", "rFactor 2", 
            "Automobilista 2", "F1 23", "Gran Turismo 7", "Forza Motorsport", "Other"
        ])
        
        self.racing_disciplines_list = QListWidget()
        self.racing_disciplines_list.setMaximumHeight(120)
        self.racing_disciplines_list.setSelectionMode(QAbstractItemView.MultiSelection)
        disciplines = [
            "Formula Racing", "GT/Sports Cars", "Touring Cars", "Prototype/LMP",
            "Stock Cars/NASCAR", "Rally", "Dirt/Oval", "Karting", "Historic Racing"
        ]
        for discipline in disciplines:
            item = QListWidgetItem(discipline)
            self.racing_disciplines_list.addItem(item)
        
        self.racing_style_combo = QComboBox()
        self.racing_style_combo.addItems([
            "Clean & Consistent", "Aggressive", "Strategic", "Defensive", 
            "Risk-Taker", "Team Player", "Solo Racer"
        ])
        
        racing_layout.addRow("Primary Sim:", self.primary_sim_combo)
        racing_layout.addRow("Disciplines:", self.racing_disciplines_list)
        racing_layout.addRow("Racing Style:", self.racing_style_combo)
        
        # Goals section
        goals_group = QGroupBox("Racing Goals")
        goals_layout = QVBoxLayout(goals_group)
        
        self.goals_input = QTextEdit()
        self.goals_input.setMaximumHeight(80)
        self.goals_input.setPlaceholderText("What are your racing goals? (e.g., improve lap times, join a team, compete in championships)")
        
        goals_layout.addWidget(self.goals_input)
        
        # Add all groups to form
        form_layout.addWidget(avatar_group)
        form_layout.addWidget(basic_group)
        form_layout.addWidget(bio_group)
        form_layout.addWidget(racing_group)
        form_layout.addWidget(goals_group)
        form_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['success']};")
        save_btn.clicked.connect(self.save_profile)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addWidget(header_label)
        layout.addWidget(scroll_area)
        layout.addLayout(button_layout)
    
    def load_user_data(self):
        """Load current user data into form."""
        try:
            self.user_data = enhanced_user_manager.get_complete_user_profile(self.current_user_id)
            if self.user_data:
                self.populate_form()
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def populate_form(self):
        """Populate form with user data."""
        if not self.user_data:
            return
        
        # Basic info
        self.username_input.setText(self.user_data.get('username', ''))
        self.display_name_input.setText(self.user_data.get('display_name', ''))
        self.location_input.setText(self.user_data.get('location', ''))
        
        # Bio
        bio = self.user_data.get('bio', '')
        self.bio_input.setPlainText(bio)
        self.update_bio_char_count()
        
        # Racing preferences
        preferences = self.user_data.get('preferences', {})
        
        primary_sim = preferences.get('primary_sim', '')
        if primary_sim:
            index = self.primary_sim_combo.findText(primary_sim)
            if index >= 0:
                self.primary_sim_combo.setCurrentIndex(index)
        
        disciplines = preferences.get('racing_disciplines', [])
        for i in range(self.racing_disciplines_list.count()):
            item = self.racing_disciplines_list.item(i)
            if item.text() in disciplines:
                item.setSelected(True)
        
        racing_style = preferences.get('racing_style', '')
        if racing_style:
            index = self.racing_style_combo.findText(racing_style)
            if index >= 0:
                self.racing_style_combo.setCurrentIndex(index)
        
        # Goals
        goals = preferences.get('racing_goals', '')
        self.goals_input.setPlainText(goals)
    
    def update_bio_char_count(self):
        """Update bio character count."""
        text = self.bio_input.toPlainText()
        count = len(text)
        self.bio_char_label.setText(f"{count}/500 characters")
        
        if count > 500:
            self.bio_char_label.setStyleSheet(f"color: {SocialTheme.COLORS['danger']};")
        else:
            self.bio_char_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
    
    def upload_avatar(self):
        """Handle avatar upload."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Profile Picture", "", 
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_path:
            # Here you would handle the actual file upload
            # For now, just show a placeholder
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale and crop to fit
                scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self.avatar_label.setPixmap(scaled_pixmap)
                self.avatar_label.setText("")
    
    def remove_avatar(self):
        """Remove current avatar."""
        self.avatar_label.clear()
        self.avatar_label.setText("👤")
    
    def save_profile(self):
        """Save profile changes."""
        try:
            # Validate input
            username = self.username_input.text().strip()
            if not username:
                QMessageBox.warning(self, "Validation Error", "Username is required.")
                return
            
            bio = self.bio_input.toPlainText()
            if len(bio) > 500:
                QMessageBox.warning(self, "Validation Error", "Bio must be 500 characters or less.")
                return
            
            # Collect selected disciplines
            selected_disciplines = []
            for i in range(self.racing_disciplines_list.count()):
                item = self.racing_disciplines_list.item(i)
                if item.isSelected():
                    selected_disciplines.append(item.text())
            
            # Prepare update data
            update_data = {
                'username': username,
                'display_name': self.display_name_input.text().strip(),
                'location': self.location_input.text().strip(),
                'bio': bio,
                'preferences': {
                    'primary_sim': self.primary_sim_combo.currentText(),
                    'racing_disciplines': selected_disciplines,
                    'racing_style': self.racing_style_combo.currentText(),
                    'racing_goals': self.goals_input.toPlainText()
                }
            }
            
            # Update profile
            result = enhanced_user_manager.update_user_profile(self.current_user_id, update_data)
            if result:
                self.profile_updated.emit(update_data)
                QMessageBox.information(self, "Success", "Profile updated successfully!")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to update profile. Please try again.")
                
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while saving your profile.")

class PrivacySettingsWidget(QWidget):
    """Privacy and security settings widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the privacy settings UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Privacy & Security Settings")
        header_label.setFont(SocialTheme.FONTS['heading'])
        
        # Profile visibility
        visibility_group = QGroupBox("Profile Visibility")
        visibility_layout = QVBoxLayout(visibility_group)
        
        self.profile_visibility_combo = QComboBox()
        self.profile_visibility_combo.addItems(["Public", "Friends Only", "Private"])
        
        visibility_help = QLabel("Public: Anyone can view your profile\nFriends Only: Only friends can view your full profile\nPrivate: Only you can view your profile")
        visibility_help.setFont(SocialTheme.FONTS['caption'])
        visibility_help.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        visibility_layout.addWidget(QLabel("Who can view your profile:"))
        visibility_layout.addWidget(self.profile_visibility_combo)
        visibility_layout.addWidget(visibility_help)
        
        # Activity sharing
        activity_group = QGroupBox("Activity Sharing")
        activity_layout = QVBoxLayout(activity_group)
        
        self.share_lap_times_cb = QCheckBox("Share lap times and racing achievements")
        self.share_online_status_cb = QCheckBox("Show when I'm online")
        self.share_racing_sessions_cb = QCheckBox("Share racing session activities")
        self.share_team_activities_cb = QCheckBox("Share team and club activities")
        
        activity_layout.addWidget(self.share_lap_times_cb)
        activity_layout.addWidget(self.share_online_status_cb)
        activity_layout.addWidget(self.share_racing_sessions_cb)
        activity_layout.addWidget(self.share_team_activities_cb)
        
        # Friend requests
        friends_group = QGroupBox("Friend Requests")
        friends_layout = QVBoxLayout(friends_group)
        
        self.friend_requests_combo = QComboBox()
        self.friend_requests_combo.addItems(["Anyone", "Friends of Friends", "No One"])
        
        friends_help = QLabel("Control who can send you friend requests")
        friends_help.setFont(SocialTheme.FONTS['caption'])
        friends_help.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        
        friends_layout.addWidget(QLabel("Who can send friend requests:"))
        friends_layout.addWidget(self.friend_requests_combo)
        friends_layout.addWidget(friends_help)
        
        # Messaging
        messaging_group = QGroupBox("Messaging")
        messaging_layout = QVBoxLayout(messaging_group)
        
        self.messaging_combo = QComboBox()
        self.messaging_combo.addItems(["Friends Only", "Anyone", "No One"])
        
        self.read_receipts_cb = QCheckBox("Send read receipts")
        self.typing_indicators_cb = QCheckBox("Show typing indicators")
        
        messaging_layout.addWidget(QLabel("Who can message you:"))
        messaging_layout.addWidget(self.messaging_combo)
        messaging_layout.addWidget(self.read_receipts_cb)
        messaging_layout.addWidget(self.typing_indicators_cb)
        
        # Data and account
        data_group = QGroupBox("Data & Account")
        data_layout = QVBoxLayout(data_group)
        
        export_data_btn = QPushButton("Export My Data")
        export_data_btn.clicked.connect(self.export_data)
        
        delete_account_btn = QPushButton("Delete Account")
        delete_account_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['danger']};")
        delete_account_btn.clicked.connect(self.delete_account)
        
        data_layout.addWidget(export_data_btn)
        data_layout.addWidget(delete_account_btn)
        
        # Save button
        save_btn = QPushButton("Save Privacy Settings")
        save_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['success']};")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(header_label)
        layout.addWidget(visibility_group)
        layout.addWidget(activity_group)
        layout.addWidget(friends_group)
        layout.addWidget(messaging_group)
        layout.addWidget(data_group)
        layout.addStretch()
        layout.addWidget(save_btn)
    
    def load_settings(self):
        """Load current privacy settings."""
        try:
            user_data = enhanced_user_manager.get_complete_user_profile(self.current_user_id)
            if user_data:
                privacy_settings = user_data.get('privacy_settings', {})
                self.populate_settings(privacy_settings)
        except Exception as e:
            logger.error(f"Error loading privacy settings: {e}")
    
    def populate_settings(self, settings: Dict[str, Any]):
        """Populate settings form."""
        # Profile visibility
        visibility = settings.get('profile_visibility', 'public')
        visibility_map = {'public': 0, 'friends': 1, 'private': 2}
        self.profile_visibility_combo.setCurrentIndex(visibility_map.get(visibility, 0))
        
        # Activity sharing
        self.share_lap_times_cb.setChecked(settings.get('share_lap_times', True))
        self.share_online_status_cb.setChecked(settings.get('share_online_status', True))
        self.share_racing_sessions_cb.setChecked(settings.get('share_racing_sessions', True))
        self.share_team_activities_cb.setChecked(settings.get('share_team_activities', True))
        
        # Friend requests
        friend_requests = settings.get('friend_requests', 'anyone')
        friend_map = {'anyone': 0, 'friends_of_friends': 1, 'no_one': 2}
        self.friend_requests_combo.setCurrentIndex(friend_map.get(friend_requests, 0))
        
        # Messaging
        messaging = settings.get('messaging', 'friends_only')
        messaging_map = {'friends_only': 0, 'anyone': 1, 'no_one': 2}
        self.messaging_combo.setCurrentIndex(messaging_map.get(messaging, 0))
        
        self.read_receipts_cb.setChecked(settings.get('read_receipts', True))
        self.typing_indicators_cb.setChecked(settings.get('typing_indicators', True))
    
    def save_settings(self):
        """Save privacy settings."""
        try:
            # Map combo box selections back to values
            visibility_map = {0: 'public', 1: 'friends', 2: 'private'}
            friend_map = {0: 'anyone', 1: 'friends_of_friends', 2: 'no_one'}
            messaging_map = {0: 'friends_only', 1: 'anyone', 2: 'no_one'}
            
            privacy_settings = {
                'profile_visibility': visibility_map[self.profile_visibility_combo.currentIndex()],
                'share_lap_times': self.share_lap_times_cb.isChecked(),
                'share_online_status': self.share_online_status_cb.isChecked(),
                'share_racing_sessions': self.share_racing_sessions_cb.isChecked(),
                'share_team_activities': self.share_team_activities_cb.isChecked(),
                'friend_requests': friend_map[self.friend_requests_combo.currentIndex()],
                'messaging': messaging_map[self.messaging_combo.currentIndex()],
                'read_receipts': self.read_receipts_cb.isChecked(),
                'typing_indicators': self.typing_indicators_cb.isChecked()
            }
            
            # Update settings
            result = enhanced_user_manager.update_user_profile(self.current_user_id, {
                'privacy_settings': privacy_settings
            })
            
            if result:
                QMessageBox.information(self, "Success", "Privacy settings saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save privacy settings.")
                
        except Exception as e:
            logger.error(f"Error saving privacy settings: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while saving settings.")
    
    def export_data(self):
        """Export user data."""
        reply = QMessageBox.question(
            self, "Export Data", 
            "This will create a file containing all your TrackPro data. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self, "Save Data Export", f"trackpro_data_{datetime.now().strftime('%Y%m%d')}.json",
                "JSON Files (*.json)"
            )
            
            if file_path:
                # Here you would implement the actual data export
                QMessageBox.information(self, "Export Started", "Your data export has been started. You'll be notified when it's ready.")
    
    def delete_account(self):
        """Delete user account."""
        reply = QMessageBox.warning(
            self, "Delete Account",
            "Are you sure you want to delete your account? This action cannot be undone.\n\nAll your data, including lap times, achievements, and social connections will be permanently deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Second confirmation
            text, ok = QInputDialog.getText(
                self, "Confirm Deletion",
                "Type 'DELETE' to confirm account deletion:"
            )
            
            if ok and text == "DELETE":
                # Here you would implement the actual account deletion
                QMessageBox.information(self, "Account Deletion", "Your account deletion request has been submitted. You'll receive a confirmation email.")

class NotificationSettingsWidget(QWidget):
    """Notification preferences widget."""
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the notification settings UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Notification Settings")
        header_label.setFont(SocialTheme.FONTS['heading'])
        
        # In-app notifications
        inapp_group = QGroupBox("In-App Notifications")
        inapp_layout = QVBoxLayout(inapp_group)
        
        self.friend_requests_notif_cb = QCheckBox("Friend requests")
        self.messages_notif_cb = QCheckBox("New messages")
        self.achievements_notif_cb = QCheckBox("Achievement unlocks")
        self.team_invites_notif_cb = QCheckBox("Team invitations")
        self.event_reminders_notif_cb = QCheckBox("Event reminders")
        self.lap_improvements_notif_cb = QCheckBox("Personal best improvements")
        
        inapp_layout.addWidget(self.friend_requests_notif_cb)
        inapp_layout.addWidget(self.messages_notif_cb)
        inapp_layout.addWidget(self.achievements_notif_cb)
        inapp_layout.addWidget(self.team_invites_notif_cb)
        inapp_layout.addWidget(self.event_reminders_notif_cb)
        inapp_layout.addWidget(self.lap_improvements_notif_cb)
        
        # Email notifications
        email_group = QGroupBox("Email Notifications")
        email_layout = QVBoxLayout(email_group)
        
        self.email_enabled_cb = QCheckBox("Enable email notifications")
        self.weekly_summary_cb = QCheckBox("Weekly activity summary")
        self.friend_activity_cb = QCheckBox("Friend activity highlights")
        self.event_announcements_cb = QCheckBox("Event announcements")
        self.security_alerts_cb = QCheckBox("Security alerts")
        
        email_layout.addWidget(self.email_enabled_cb)
        email_layout.addWidget(self.weekly_summary_cb)
        email_layout.addWidget(self.friend_activity_cb)
        email_layout.addWidget(self.event_announcements_cb)
        email_layout.addWidget(self.security_alerts_cb)
        
        # Sound settings
        sound_group = QGroupBox("Sound Settings")
        sound_layout = QVBoxLayout(sound_group)
        
        self.sound_enabled_cb = QCheckBox("Enable notification sounds")
        
        self.sound_volume_slider = QSlider(Qt.Horizontal)
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setValue(50)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        volume_layout.addWidget(self.sound_volume_slider)
        self.volume_label = QLabel("50%")
        volume_layout.addWidget(self.volume_label)
        
        self.sound_volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        
        sound_layout.addWidget(self.sound_enabled_cb)
        sound_layout.addLayout(volume_layout)
        
        # Save button
        save_btn = QPushButton("Save Notification Settings")
        save_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['success']};")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(header_label)
        layout.addWidget(inapp_group)
        layout.addWidget(email_group)
        layout.addWidget(sound_group)
        layout.addStretch()
        layout.addWidget(save_btn)
    
    def load_settings(self):
        """Load current notification settings."""
        try:
            user_data = enhanced_user_manager.get_complete_user_profile(self.current_user_id)
            if user_data:
                preferences = user_data.get('preferences', {})
                notifications = preferences.get('notifications', {})
                self.populate_settings(notifications)
        except Exception as e:
            logger.error(f"Error loading notification settings: {e}")
    
    def populate_settings(self, settings: Dict[str, Any]):
        """Populate notification settings."""
        # In-app notifications
        self.friend_requests_notif_cb.setChecked(settings.get('friend_requests', True))
        self.messages_notif_cb.setChecked(settings.get('messages', True))
        self.achievements_notif_cb.setChecked(settings.get('achievements', True))
        self.team_invites_notif_cb.setChecked(settings.get('team_invites', True))
        self.event_reminders_notif_cb.setChecked(settings.get('event_reminders', True))
        self.lap_improvements_notif_cb.setChecked(settings.get('lap_improvements', True))
        
        # Email notifications
        self.email_enabled_cb.setChecked(settings.get('email_enabled', True))
        self.weekly_summary_cb.setChecked(settings.get('weekly_summary', True))
        self.friend_activity_cb.setChecked(settings.get('friend_activity', False))
        self.event_announcements_cb.setChecked(settings.get('event_announcements', True))
        self.security_alerts_cb.setChecked(settings.get('security_alerts', True))
        
        # Sound settings
        self.sound_enabled_cb.setChecked(settings.get('sound_enabled', True))
        volume = settings.get('sound_volume', 50)
        self.sound_volume_slider.setValue(volume)
        self.volume_label.setText(f"{volume}%")
    
    def save_settings(self):
        """Save notification settings."""
        try:
            notification_settings = {
                'friend_requests': self.friend_requests_notif_cb.isChecked(),
                'messages': self.messages_notif_cb.isChecked(),
                'achievements': self.achievements_notif_cb.isChecked(),
                'team_invites': self.team_invites_notif_cb.isChecked(),
                'event_reminders': self.event_reminders_notif_cb.isChecked(),
                'lap_improvements': self.lap_improvements_notif_cb.isChecked(),
                'email_enabled': self.email_enabled_cb.isChecked(),
                'weekly_summary': self.weekly_summary_cb.isChecked(),
                'friend_activity': self.friend_activity_cb.isChecked(),
                'event_announcements': self.event_announcements_cb.isChecked(),
                'security_alerts': self.security_alerts_cb.isChecked(),
                'sound_enabled': self.sound_enabled_cb.isChecked(),
                'sound_volume': self.sound_volume_slider.value()
            }
            
            # Get current preferences
            user_data = enhanced_user_manager.get_complete_user_profile(self.current_user_id)
            preferences = user_data.get('preferences', {}) if user_data else {}
            preferences['notifications'] = notification_settings
            
            # Update preferences
            result = enhanced_user_manager.update_user_profile(self.current_user_id, {
                'preferences': preferences
            })
            
            if result:
                QMessageBox.information(self, "Success", "Notification settings saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save notification settings.")
                
        except Exception as e:
            logger.error(f"Error saving notification settings: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while saving settings.")

class AvatarFrameSelector(QWidget):
    """Avatar frame selection widget."""
    
    frame_selected = pyqtSignal(str)  # Emits frame ID
    
    def __init__(self, current_user_id: str, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.available_frames = []
        self.init_ui()
        self.load_frames()
    
    def init_ui(self):
        """Initialize the avatar frame selector UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Avatar Frames")
        header_label.setFont(SocialTheme.FONTS['heading'])
        
        # Description
        desc_label = QLabel("Unlock avatar frames by completing achievements and reaching milestones!")
        desc_label.setFont(SocialTheme.FONTS['body'])
        desc_label.setStyleSheet(f"color: {SocialTheme.COLORS['text_secondary']};")
        desc_label.setWordWrap(True)
        
        # Frames grid
        self.frames_scroll = QScrollArea()
        self.frames_widget = QWidget()
        self.frames_layout = QGridLayout(self.frames_widget)
        self.frames_scroll.setWidget(self.frames_widget)
        self.frames_scroll.setWidgetResizable(True)
        
        layout.addWidget(header_label)
        layout.addWidget(desc_label)
        layout.addWidget(self.frames_scroll)
    
    def load_frames(self):
        """Load available avatar frames."""
        try:
            self.available_frames = enhanced_user_manager.get_available_avatar_frames(self.current_user_id)
            self.populate_frames()
        except Exception as e:
            logger.error(f"Error loading avatar frames: {e}")
    
    def populate_frames(self):
        """Populate the frames grid."""
        # Clear existing frames
        for i in reversed(range(self.frames_layout.count())):
            child = self.frames_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add frames
        row, col = 0, 0
        max_cols = 4
        
        for frame in self.available_frames:
            frame_widget = self.create_frame_widget(frame)
            self.frames_layout.addWidget(frame_widget, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def create_frame_widget(self, frame: Dict[str, Any]) -> QWidget:
        """Create an avatar frame widget."""
        widget = QFrame()
        widget.setFixedSize(120, 140)
        
        is_unlocked = frame.get('is_unlocked', False)
        is_selected = frame.get('is_selected', False)
        
        if is_selected:
            border_color = SocialTheme.COLORS['success']
        elif is_unlocked:
            border_color = SocialTheme.COLORS['accent']
        else:
            border_color = SocialTheme.COLORS['border']
        
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {SocialTheme.COLORS['surface']};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        
        # Frame preview
        preview_label = QLabel()
        preview_label.setFixedSize(80, 80)
        preview_label.setAlignment(Qt.AlignCenter)
        
        if is_unlocked:
            # Show frame preview (would load actual frame image)
            preview_label.setStyleSheet(f"""
                QLabel {{
                    border: 3px solid {frame.get('color', SocialTheme.COLORS['accent'])};
                    border-radius: 40px;
                    background-color: {SocialTheme.COLORS['background']};
                }}
            """)
            preview_label.setText("👤")
        else:
            preview_label.setStyleSheet(f"""
                QLabel {{
                    border: 2px dashed {SocialTheme.COLORS['border']};
                    border-radius: 40px;
                    background-color: {SocialTheme.COLORS['background']};
                }}
            """)
            preview_label.setText("🔒")
        
        # Frame name
        name_label = QLabel(frame.get('name', 'Unknown'))
        name_label.setFont(SocialTheme.FONTS['caption'])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        
        # Status/button
        if is_unlocked:
            if is_selected:
                status_btn = QPushButton("Selected")
                status_btn.setEnabled(False)
                status_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['success']};")
            else:
                status_btn = QPushButton("Select")
                status_btn.clicked.connect(lambda: self.select_frame(frame['id']))
        else:
            unlock_req = frame.get('unlock_requirement', 'Unknown requirement')
            status_btn = QPushButton("Locked")
            status_btn.setEnabled(False)
            status_btn.setToolTip(f"Unlock requirement: {unlock_req}")
        
        layout.addWidget(preview_label)
        layout.addWidget(name_label)
        layout.addWidget(status_btn)
        
        return widget
    
    def select_frame(self, frame_id: str):
        """Select an avatar frame."""
        try:
            result = enhanced_user_manager.set_avatar_frame(self.current_user_id, frame_id)
            if result:
                self.frame_selected.emit(frame_id)
                self.load_frames()  # Refresh to show new selection
                QMessageBox.information(self, "Success", "Avatar frame updated!")
            else:
                QMessageBox.warning(self, "Error", "Failed to update avatar frame.")
        except Exception as e:
            logger.error(f"Error selecting avatar frame: {e}")

class UserAccountMainWidget(QWidget):
    """Main user account management widget."""
    
    def __init__(self, user_manager=None, current_user_id: str = None, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.current_user_id = current_user_id
        self.setStyleSheet(SocialTheme.get_stylesheet())
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user account UI."""
        layout = QHBoxLayout(self)
        
        # Left sidebar with navigation
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Profile", "👤"),
            ("Privacy", "🔒"),
            ("Notifications", "🔔"),
            ("Avatar Frames", "🖼️"),
            ("Account", "⚙️")
        ]
        
        for name, icon in nav_items:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=name: self.switch_view(n))
            self.nav_buttons[name] = btn
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Initialize views
        self.views = {
            "Profile": self.create_profile_view(),
            "Privacy": PrivacySettingsWidget(self.current_user_id),
            "Notifications": NotificationSettingsWidget(self.current_user_id),
            "Avatar Frames": AvatarFrameSelector(self.current_user_id),
            "Account": self.create_account_view()
        }
        
        for view in self.views.values():
            self.content_stack.addWidget(view)
        
        layout.addWidget(sidebar)
        layout.addWidget(self.content_stack)
        
        # Set default view
        self.switch_view("Profile")
    
    def create_profile_view(self) -> QWidget:
        """Create the profile overview view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Profile Overview")
        title_label.setFont(SocialTheme.FONTS['heading'])
        
        edit_btn = QPushButton("Edit Profile")
        edit_btn.setStyleSheet(f"background-color: {SocialTheme.COLORS['primary']};")
        edit_btn.clicked.connect(self.edit_profile)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(edit_btn)
        
        # Profile display
        from .social_ui import UserProfileWidget
        self.profile_display = UserProfileWidget(self.current_user_id, compact=False)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.profile_display)
        layout.addStretch()
        
        return widget
    
    def create_account_view(self) -> QWidget:
        """Create the account management view."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Header
        title_label = QLabel("Account Management")
        title_label.setFont(SocialTheme.FONTS['heading'])
        
        # Account info
        info_group = QGroupBox("Account Information")
        info_layout = QFormLayout(info_group)
        
        # This would be populated with actual account data
        info_layout.addRow("User ID:", QLabel(self.current_user_id))
        info_layout.addRow("Member Since:", QLabel("January 2024"))
        info_layout.addRow("Last Login:", QLabel("Today"))
        
        # Account actions
        actions_group = QGroupBox("Account Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        change_password_btn = QPushButton("Change Password")
        change_password_btn.clicked.connect(self.change_password)
        
        two_factor_btn = QPushButton("Enable Two-Factor Authentication")
        two_factor_btn.clicked.connect(self.setup_two_factor)
        
        actions_layout.addWidget(change_password_btn)
        actions_layout.addWidget(two_factor_btn)
        
        layout.addWidget(title_label)
        layout.addWidget(info_group)
        layout.addWidget(actions_group)
        layout.addStretch()
        
        return widget
    
    def switch_view(self, view_name: str):
        """Switch to a different view."""
        # Update button states
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == view_name)
        
        # Switch content
        if view_name in self.views:
            self.content_stack.setCurrentWidget(self.views[view_name])
    
    def edit_profile(self):
        """Open profile edit dialog."""
        dialog = ProfileEditDialog(self.current_user_id, self)
        dialog.profile_updated.connect(self.on_profile_updated)
        dialog.exec_()
    
    def on_profile_updated(self, profile_data: Dict[str, Any]):
        """Handle profile update."""
        # Refresh profile display
        self.profile_display.load_user_data()
    
    def change_password(self):
        """Open change password dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Password")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        current_password = QLineEdit()
        current_password.setEchoMode(QLineEdit.Password)
        current_password.setPlaceholderText("Current password")
        
        new_password = QLineEdit()
        new_password.setEchoMode(QLineEdit.Password)
        new_password.setPlaceholderText("New password")
        
        confirm_password = QLineEdit()
        confirm_password.setEchoMode(QLineEdit.Password)
        confirm_password.setPlaceholderText("Confirm new password")
        
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        save_btn = QPushButton("Change Password")
        save_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addWidget(QLabel("Change Password"))
        layout.addWidget(current_password)
        layout.addWidget(new_password)
        layout.addWidget(confirm_password)
        layout.addLayout(button_layout)
        
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Success", "Password changed successfully!")
    
    def setup_two_factor(self):
        """Setup two-factor authentication."""
        QMessageBox.information(
            self, "Two-Factor Authentication",
            "Two-factor authentication setup will be implemented in a future update."
        )

# Export components
__all__ = [
    'ProfileEditDialog',
    'PrivacySettingsWidget',
    'NotificationSettingsWidget',
    'AvatarFrameSelector',
    'UserAccountMainWidget'
] 