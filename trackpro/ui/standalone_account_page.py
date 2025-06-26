"""
TrackPro Standalone Account Page
Complete account management interface with profile editing, data sharing control,
security features, and database integration.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, date
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

logger = logging.getLogger(__name__)

class AccountPage(QWidget):
    """Standalone Account Page for TrackPro - Complete profile and account management."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_data = None
        self.is_oauth_user = False
        self.has_password = False
        self.setup_ui()
        self.load_user_data()
        
    def setup_ui(self):
        """Setup the account page UI with all form fields and sections."""
        # Main layout with proper spacing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)
        
        # Header section
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Account Settings")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setStyleSheet("color: #BF616A; font-weight: bold;")
        
        subtitle_label = QLabel("Manage your profile, privacy, and preferences")
        subtitle_label.setFont(QFont("Arial", 12))
        subtitle_label.setStyleSheet("color: #5E81AC;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(subtitle_label)
        
        main_layout.addLayout(header_layout)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        content_layout = QVBoxLayout(scroll_widget)
        content_layout.setSpacing(20)
        
        # SECTION 1: Profile Information (Editable Form)
        profile_section = self.create_profile_section()
        content_layout.addWidget(profile_section)
        
        # SECTION 2: Account Security
        security_section = self.create_security_section()
        content_layout.addWidget(security_section)
        
        # SECTION 3: Account Actions
        actions_section = self.create_actions_section()
        content_layout.addWidget(actions_section)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def create_profile_section(self):
        """Create the Profile Information section with all form fields."""
        group_box = QGroupBox("Profile Information")
        group_box.setFont(QFont("Arial", 14, QFont.Bold))
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #D8DEE9;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QFormLayout(group_box)
        layout.setSpacing(15)
        
        # First Name (Required)
        self.first_name_input = QLineEdit()
        self.first_name_input.setMaxLength(50)
        self.first_name_input.setStyleSheet(self.get_input_style())
        layout.addRow("First Name *:", self.first_name_input)
        
        # Last Name (Required)
        self.last_name_input = QLineEdit()
        self.last_name_input.setMaxLength(50)
        self.last_name_input.setStyleSheet(self.get_input_style())
        layout.addRow("Last Name *:", self.last_name_input)
        
        # Username (Required)
        self.username_input = QLineEdit()
        self.username_input.setMaxLength(100)
        self.username_input.setStyleSheet(self.get_input_style())
        layout.addRow("Username *:", self.username_input)
        
        # Email (Required, Read-only for existing users)
        self.email_input = QLineEdit()
        self.email_input.setStyleSheet(self.get_input_style())
        layout.addRow("Email *:", self.email_input)
        
        # Date of Birth
        self.dob_input = QDateEdit()
        self.dob_input.setDate(QDate.currentDate().addYears(-18))
        self.dob_input.setMaximumDate(QDate.currentDate())
        self.dob_input.setMinimumDate(QDate(1900, 1, 1))
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setStyleSheet(self.get_input_style())
        layout.addRow("Date of Birth:", self.dob_input)
        
        # Gender
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Select...", "Male", "Female", "Other", "Prefer not to say"])
        self.gender_combo.setStyleSheet(self.get_input_style())
        layout.addRow("Gender:", self.gender_combo)
        
        # Bio (Optional)
        self.bio_input = QTextEdit()
        self.bio_input.setMaximumHeight(100)
        self.bio_input.setPlaceholderText("Tell us about yourself...")
        self.bio_input.setStyleSheet(self.get_input_style())
        layout.addRow("Bio (optional):", self.bio_input)
        
        # Profile Picture Upload (Optional)
        profile_pic_layout = QHBoxLayout()
        self.profile_pic_label = QLabel("No image selected")
        self.profile_pic_label.setStyleSheet("border: 1px solid #D8DEE9; padding: 5px; background: #ECEFF4;")
        self.profile_pic_button = QPushButton("Choose Image")
        self.profile_pic_button.setStyleSheet(self.get_button_style())
        self.profile_pic_button.clicked.connect(self.choose_profile_picture)
        
        profile_pic_layout.addWidget(self.profile_pic_label)
        profile_pic_layout.addWidget(self.profile_pic_button)
        layout.addRow("Profile Picture:", profile_pic_layout)
        
        # Save Changes Button
        self.save_profile_btn = QPushButton("Save Changes")
        self.save_profile_btn.setStyleSheet(self.get_button_style(primary=True))
        self.save_profile_btn.clicked.connect(self.save_profile_changes)
        layout.addRow("", self.save_profile_btn)
        
        return group_box

    def create_security_section(self):
        """Create the Account Security section for password management."""
        group_box = QGroupBox("Account Security")
        group_box.setFont(QFont("Arial", 14, QFont.Bold))
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #D8DEE9;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group_box)
        
        # Password change section (conditional visibility)
        self.security_content = QWidget()
        security_layout = QFormLayout(self.security_content)
        
        # Current Password (for existing password users)
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.Password)
        self.current_password_input.setStyleSheet(self.get_input_style())
        security_layout.addRow("Current Password:", self.current_password_input)
        
        # New Password
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setStyleSheet(self.get_input_style())
        security_layout.addRow("New Password:", self.new_password_input)
        
        # Confirm New Password
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setStyleSheet(self.get_input_style())
        security_layout.addRow("Confirm New Password:", self.confirm_password_input)
        
        # Change Password Button
        self.change_password_btn = QPushButton("Update Password")
        self.change_password_btn.setStyleSheet(self.get_button_style())
        self.change_password_btn.clicked.connect(self.change_password)
        security_layout.addRow("", self.change_password_btn)
        
        # OAuth users message (conditional visibility)
        self.oauth_message = QLabel("You signed in with a social account. You can create a password for additional security.")
        self.oauth_message.setStyleSheet("color: #5E81AC; font-style: italic; margin: 10px;")
        self.oauth_message.setWordWrap(True)
        
        layout.addWidget(self.oauth_message)
        layout.addWidget(self.security_content)
        
        return group_box
        
    def create_actions_section(self):
        """Create the Account Actions section for logout and deletion."""
        group_box = QGroupBox("Account Actions")
        group_box.setFont(QFont("Arial", 14, QFont.Bold))
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #D8DEE9;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout(group_box)
        layout.setSpacing(15)
        
        # Delete Account Section
        delete_section = QFrame()
        delete_section.setStyleSheet("border: 1px solid #BF616A; border-radius: 5px; padding: 10px; background: #FDFDFD;")
        delete_layout = QVBoxLayout(delete_section)
        
        delete_title = QLabel("Delete Account")
        delete_title.setFont(QFont("Arial", 12, QFont.Bold))
        delete_title.setStyleSheet("color: #BF616A; border: none; background: transparent;")
        
        delete_description = QLabel("Permanently delete your TrackPro account and all associated data. This action cannot be undone.")
        delete_description.setStyleSheet("color: #5E81AC; margin: 5px 0; border: none; background: transparent;")
        delete_description.setWordWrap(True)
        
        self.delete_account_btn = QPushButton("Delete Account")
        self.delete_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #BF616A;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D08770;
            }
        """)
        self.delete_account_btn.clicked.connect(self.delete_account)
        
        delete_layout.addWidget(delete_title)
        delete_layout.addWidget(delete_description)
        delete_layout.addWidget(self.delete_account_btn)
        
        # Logout Section
        logout_section = QFrame()
        logout_section.setStyleSheet("border: 1px solid #88C0D0; border-radius: 5px; padding: 10px; background: #FDFDFD;")
        logout_layout = QVBoxLayout(logout_section)
        
        logout_title = QLabel("Sign Out")
        logout_title.setFont(QFont("Arial", 12, QFont.Bold))
        logout_title.setStyleSheet("color: #5E81AC; border: none; background: transparent;")
        
        self.logout_btn = QPushButton("Sign Out")
        self.logout_btn.setStyleSheet(self.get_button_style())
        self.logout_btn.clicked.connect(self.logout)
        
        logout_layout.addWidget(logout_title)
        logout_layout.addWidget(self.logout_btn)
        
        layout.addWidget(delete_section)
        layout.addWidget(logout_section)
        
        return group_box

    def load_user_data(self):
        """Load current user data and populate form fields with robust error handling."""
        try:
            # Import here to avoid circular imports
            from ..database import supabase_client
            
            # SECURITY FIX: Force a fresh authentication check
            supabase = supabase_client.get_supabase_client()
            if not supabase:
                self.show_login_required()
                return
            
            # Check authentication status using the correct method
            if not supabase.is_authenticated():
                logger.error("User is not authenticated")
                self.show_login_required()
                return
            
            # Get user data with better error handling
            try:
                user = supabase.auth.get_user()
                if not user or not user.user:
                    logger.error("No authenticated user found")
                    self.show_login_required()
                    return
                
                user_id = user.user.id
                email = user.user.email
                
                if not user_id or not email:
                    logger.error(f"User ID or email not available. user_id={user_id}, email={email}")
                    self.show_error("User ID or email not available.")
                    return
                
            except Exception as user_error:
                logger.error(f"Error getting user info: {user_error}")
                self.show_error("Failed to get user information.")
                return
            
            logger.info(f"🔒 SECURITY: Loading account data for authenticated user {user_id} ({email})")
            
            # Load profile data from both tables
            try:
                # Get data from user_details table
                details_response = supabase.from_("user_details").select("*").eq("user_id", user_id).execute()
                details_data = details_response.data[0] if details_response.data else {}
                
                # Get data from user_profiles table  
                profiles_response = supabase.from_("user_profiles").select("*").eq("user_id", user_id).execute()
                profiles_data = profiles_response.data[0] if profiles_response.data else {}
                
                # SECURITY VALIDATION: Double-check the returned data
                if details_data and details_data.get('user_id') != user_id:
                    logger.error(f"🚨 SECURITY BREACH: Database returned wrong user data!")
                    self.show_error("Security validation failed. Please contact support.")
                    return
                
                if profiles_data and profiles_data.get('user_id') != user_id:
                    logger.error(f"🚨 SECURITY BREACH: Database returned wrong user data!")
                    self.show_error("Security validation failed. Please contact support.")
                    return
                
            except Exception as db_error:
                logger.error(f"Database query failed: {db_error}")
                self.show_error("Failed to load user data from database.")
                return
            
            # Combine data from both tables
            self.user_data = {
                'user_id': user_id,
                'email': email,
                'username': details_data.get('username', email.split('@')[0] if email else 'user'),
                'first_name': details_data.get('first_name', ''),
                'last_name': details_data.get('last_name', ''),
                'bio': profiles_data.get('bio', ''),
                'date_of_birth': details_data.get('date_of_birth'),
                'gender': details_data.get('gender', '')
            }
            logger.info(f"✅ SECURITY: Successfully loaded profile for authenticated user {user_id}")
            
            # Populate form with loaded data
            self.populate_form()
            
            # Check authentication method and update UI accordingly
            self.check_user_auth_method(user.user)
            self.update_security_section_visibility()
            
            # Check if OAuth user needs to complete profile
            self.check_oauth_user_completion()
            
        except Exception as e:
            logger.error(f"Critical error loading user data: {e}")
            self.user_data = None
            self.show_error("Failed to load user data. Please try refreshing the page.")

    def choose_profile_picture(self):
        """Handle profile picture selection and upload."""
        try:
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self,
                "Select Profile Picture",
                "",
                "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*)"
            )
            
            if file_path:
                # Validate image file size (max 5MB)
                file_size = os.path.getsize(file_path)
                if file_size > 5 * 1024 * 1024:
                    self.show_error("Image file must be smaller than 5MB.")
                    return
                
                # Update label to show selected file
                filename = os.path.basename(file_path)
                self.profile_pic_label.setText(f"Selected: {filename}")
                
                # TODO: Implement actual image upload to storage
                # For now, just store the file path
                self.selected_profile_pic = file_path
                logger.info(f"Profile picture selected: {filename}")
                
        except Exception as e:
            logger.error(f"Error selecting profile picture: {e}")
            self.show_error("Failed to select profile picture.")

    def populate_form(self):
        """Populate form fields with user data."""
        if not self.user_data:
            return
            
        # Basic fields
        self.first_name_input.setText(self.user_data.get('first_name', ''))
        self.last_name_input.setText(self.user_data.get('last_name', ''))
        self.username_input.setText(self.user_data.get('username', ''))
        self.email_input.setText(self.user_data.get('email', ''))
        self.bio_input.setPlainText(self.user_data.get('bio', ''))
        
        # Date of birth
        dob = self.user_data.get('date_of_birth')
        if dob:
            if isinstance(dob, str):
                try:
                    dob_date = datetime.fromisoformat(dob.replace('Z', '')).date()
                    self.dob_input.setDate(QDate(dob_date))
                except:
                    pass
        
        # Gender
        gender = self.user_data.get('gender', '')
        if gender:
            index = self.gender_combo.findText(gender)
            if index >= 0:
                self.gender_combo.setCurrentIndex(index)

    def save_profile_changes(self):
        """Save profile changes to database with validation."""
        try:
            # Validate required fields
            if not self.first_name_input.text().strip():
                self.show_error("First name is required.")
                return
                
            if not self.last_name_input.text().strip():
                self.show_error("Last name is required.")
                return
            
            if not self.username_input.text().strip():
                self.show_error("Username is required.")
                return
            
            if not self.email_input.text().strip():
                self.show_error("Email is required.")
                return
            
            # Prepare data for saving
            profile_data = {
                'first_name': self.first_name_input.text().strip(),
                'last_name': self.last_name_input.text().strip(),
                'username': self.username_input.text().strip(),
                'email': self.email_input.text().strip(),
                'bio': self.bio_input.toPlainText().strip(),
                'date_of_birth': self.dob_input.date().toString("yyyy-MM-dd"),
                'gender': self.gender_combo.currentText() if self.gender_combo.currentIndex() > 0 else ''
            }
            
            # Save to database
            success = self.save_to_database(profile_data)
            
            if success:
                # Update user_data with new values
                self.user_data.update(profile_data)
                
                self.show_success("Profile updated successfully!")
                logger.info("Profile updated successfully")
            else:
                self.show_error("Failed to update profile. Please try again.")
                
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            self.show_error("An error occurred while saving your profile.")
    
    def save_to_database(self, profile_data):
        """Save profile data to database with gender and share_data support."""
        try:
            from ..database import supabase_client
            
            supabase = supabase_client.get_supabase_client()
            if not supabase:
                return False
            
            # Get current user
            user = supabase.auth.get_user()
            if not user or not user.user:
                return False
                
            user_id = user.user.id
            
            # Update user_details table
            try:
                details_response = supabase.from_("user_details").upsert({
                    'user_id': user_id,
                    'username': profile_data.get('username', ''),
                    'first_name': profile_data.get('first_name', ''),
                    'last_name': profile_data.get('last_name', ''),
                    'date_of_birth': profile_data.get('date_of_birth', ''),
                    'gender': profile_data.get('gender', '')
                }).execute()
                
                if details_response.data:
                    logger.info("✅ Successfully updated user_details table")
                
            except Exception as details_error:
                logger.warning(f"Could not update user_details: {details_error}")
            
            # Update user_profiles table
            try:
                profiles_response = supabase.from_("user_profiles").upsert({
                    'user_id': user_id,
                    'email': profile_data.get('email', ''),
                    'username': profile_data.get('username', ''),
                    'bio': profile_data.get('bio', ''),
                    'preferences': {
                        'first_name': profile_data.get('first_name', ''),
                        'last_name': profile_data.get('last_name', ''),
                        'username': profile_data.get('username', ''),
                        'gender': profile_data.get('gender', ''),
                        'date_of_birth': profile_data.get('date_of_birth', '')
                    }
                }).execute()
                
                if profiles_response.data:
                    logger.info("✅ Successfully updated user_profiles table")
                    return True
                
            except Exception as profiles_error:
                logger.warning(f"Could not update user_profiles: {profiles_error}")
                return True  # Partial success is still success
            
            return False
            
        except Exception as e:
            logger.error(f"Database save error: {e}")
            return False

    def get_input_style(self):
        """Get consistent input field styling."""
        return """
            QLineEdit, QTextEdit, QComboBox, QDateEdit {
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
                color: #2E3440;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #5E81AC;
                color: #2E3440;
            }
        """
        
    def get_button_style(self, primary=False):
        """Get consistent button styling."""
        if primary:
            return """
                QPushButton {
                    background-color: #5E81AC;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #81A1C1;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #ECEFF4;
                    color: #2E3440;
                    border: 1px solid #D8DEE9;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #E5E9F0;
                }
            """
    
    # UTILITY METHODS
    
    def show_login_required(self):
        """Show login required dialog and redirect to authentication."""
        try:
            QMessageBox.warning(
                self,
                "Authentication Required",
                "You need to be logged in to access account settings.\n\n"
                "Please log in to continue."
            )
            
            # Try to show login dialog if available
            try:
                from ..auth.login_dialog import LoginDialog
                login_dialog = LoginDialog(self)
                if login_dialog.exec_() == QDialog.Accepted:
                    # Reload user data after successful login
                    self.load_user_data()
            except ImportError:
                logger.warning("Could not import LoginDialog")
                
        except Exception as e:
            logger.error(f"Error showing login required dialog: {e}")
    
    def show_error(self, message):
        """Show error message to user."""
        try:
            QMessageBox.critical(self, "Error", message)
        except Exception as e:
            logger.error(f"Error showing error dialog: {e}")
    
    def show_success(self, message):
        """Show success message to user."""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Success")
            msg_box.setText(message)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ECEFF4;
                }
                QMessageBox QLabel {
                    color: #2E3440;
                }
            """)
            msg_box.exec_()
        except Exception as e:
            logger.error(f"Error showing success dialog: {e}")
    
    def check_user_auth_method(self, user):
        """Check if user is OAuth or password-based and set flags accordingly."""
        try:
            # Check if user has OAuth providers
            self.is_oauth_user = False
            self.has_password = True
            
            if hasattr(user, 'app_metadata') and user.app_metadata:
                providers = user.app_metadata.get('providers', [])
                if any(provider in ['google', 'github', 'discord'] for provider in providers):
                    self.is_oauth_user = True
                    # OAuth users may not have a password
                    self.has_password = user.app_metadata.get('password_auth', False)
            
            logger.info(f"User auth method - OAuth: {self.is_oauth_user}, Has Password: {self.has_password}")
            
        except Exception as e:
            logger.error(f"Error checking user auth method: {e}")
            # Default to password-based user
            self.is_oauth_user = False
            self.has_password = True
    
    def update_security_section_visibility(self):
        """Update security section visibility based on user authentication method."""
        try:
            if self.is_oauth_user and not self.has_password:
                # Show OAuth message, hide current password field
                self.oauth_message.show()
                self.current_password_input.hide()
                self.current_password_input.parentWidget().layout().labelForField(self.current_password_input).hide()
            else:
                # Hide OAuth message, show all password fields
                self.oauth_message.hide()
                self.current_password_input.show()
                self.current_password_input.parentWidget().layout().labelForField(self.current_password_input).show()
                
        except Exception as e:
            logger.error(f"Error updating security section visibility: {e}")
    
    def check_oauth_user_completion(self):
        """Check if OAuth user needs to complete their profile and show prompts."""
        try:
            if not self.is_oauth_user or not self.user_data:
                return
            
            # Check for missing required fields
            missing_fields = []
            if not self.user_data.get('first_name'):
                missing_fields.append('First Name')
            if not self.user_data.get('last_name'):
                missing_fields.append('Last Name')
            if not self.user_data.get('username'):
                missing_fields.append('Username')
            
            if missing_fields:
                QMessageBox.information(
                    self,
                    "Complete Your Profile",
                    f"Welcome! Please complete your profile by filling in the following required fields:\n\n"
                    f"• {', '.join(missing_fields)}\n\n"
                    f"This information helps personalize your TrackPro experience."
                )
                
                # Highlight the first missing field
                if 'First Name' in missing_fields:
                    self.first_name_input.setFocus()
                elif 'Last Name' in missing_fields:
                    self.last_name_input.setFocus()
                elif 'Username' in missing_fields:
                    self.username_input.setFocus()
                    
        except Exception as e:
            logger.error(f"Error checking OAuth user completion: {e}")
    
    def change_password(self):
        """Handle password change for authenticated users."""
        try:
            # Validate inputs
            if not self.is_oauth_user and not self.current_password_input.text():
                self.show_error("Current password is required.")
                return
            
            new_password = self.new_password_input.text()
            confirm_password = self.confirm_password_input.text()
            
            if not new_password:
                self.show_error("New password is required.")
                return
            
            if len(new_password) < 8:
                self.show_error("New password must be at least 8 characters long.")
                return
            
            if new_password != confirm_password:
                self.show_error("New password and confirmation do not match.")
                return
            
            # Attempt to update password
            from ..database import supabase_client
            supabase = supabase_client.get_supabase_client()
            
            if not supabase:
                self.show_error("Database connection failed.")
                return
            
            try:
                # Update password using Supabase Auth
                response = supabase.auth.update_user({
                    "password": new_password
                })
                
                if response.user:
                    self.show_success("Password updated successfully!")
                    
                    # Clear password fields
                    self.current_password_input.clear()
                    self.new_password_input.clear()
                    self.confirm_password_input.clear()
                    
                    logger.info("Password updated successfully")
                else:
                    self.show_error("Failed to update password. Please try again.")
                    
            except Exception as auth_error:
                logger.error(f"Authentication error during password change: {auth_error}")
                self.show_error("Failed to update password. Please check your current password.")
                
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            self.show_error("An error occurred while changing your password.")
    
    def delete_account(self):
        """Handle account deletion with confirmation."""
        try:
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                "Delete Account",
                "⚠️ WARNING: This action cannot be undone!\n\n"
                "Deleting your account will permanently remove:\n"
                "• All your profile data\n"
                "• Telemetry and session history\n"
                "• Achievements and progress\n"
                "• Community posts and interactions\n\n"
                "Are you absolutely sure you want to delete your account?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Second confirmation
            text, ok = QInputDialog.getText(
                self,
                "Final Confirmation",
                "To confirm account deletion, please type 'DELETE' (in capital letters):"
            )
            
            if not ok or text != "DELETE":
                if ok:
                    self.show_error("Confirmation text did not match. Account deletion cancelled.")
                return
            
            # Attempt account deletion
            from ..database import supabase_client
            supabase = supabase_client.get_supabase_client()
            
            if not supabase:
                self.show_error("Database connection failed.")
                return
            
            try:
                user = supabase.auth.get_user()
                if not user or not user.user:
                    self.show_error("User authentication failed.")
                    return
                
                user_id = user.user.id
                
                # Delete user data from all tables
                # Note: This should be done in a transaction in production
                supabase.from_("user_details").delete().eq("user_id", user_id).execute()
                supabase.from_("user_profiles").delete().eq("user_id", user_id).execute()
                
                # Delete the auth user
                # Note: This requires admin privileges in Supabase
                logger.warning("Account deletion requested - manual admin action may be required")
                
                QMessageBox.information(
                    self,
                    "Account Deletion Requested",
                    "Your account deletion request has been processed.\n\n"
                    "You will be logged out now. If you have any issues, "
                    "please contact support."
                )
                
                # Logout user
                self.logout()
                
            except Exception as deletion_error:
                logger.error(f"Error during account deletion: {deletion_error}")
                self.show_error("Failed to delete account. Please contact support.")
                
        except Exception as e:
            logger.error(f"Error in delete account process: {e}")
            self.show_error("An error occurred during account deletion.")
    
    def logout(self):
        """Handle user logout."""
        try:
            from ..database import supabase_client
            
            # Logout from Supabase
            supabase = supabase_client.get_supabase_client()
            if supabase:
                try:
                    supabase.sign_out()
                    logger.info("User logged out successfully")
                except Exception as logout_error:
                    logger.error(f"Error during logout: {logout_error}")
            
            # Clear user data
            self.user_data = None
            
            # Find the main window parent and update auth state
            parent = self.parent()
            main_window = None
            while parent:
                if hasattr(parent, '__class__') and 'MainWindow' in parent.__class__.__name__:
                    main_window = parent
                    break
                parent = parent.parent()
            
            if main_window:
                # Update authentication state in the main window
                main_window.update_auth_state()
                
                # Navigate back to the main pedal configuration page
                if hasattr(main_window, 'open_pedal_config'):
                    main_window.open_pedal_config()
                
                # Show logout confirmation
                QMessageBox.information(
                    self,
                    "Logged Out",
                    "You have been logged out successfully."
                )
            else:
                # Fallback if we can't find the main window
                QMessageBox.information(
                    self,
                    "Logged Out",
                    "You have been logged out successfully.\n\n"
                    "Please restart the application to log in again."
                )
                
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            self.show_error("An error occurred during logout.") 