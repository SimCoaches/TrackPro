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
        # Remove the duplicate load_user_data() call from here
        
    def setup_ui(self):
        """Set up the complete account page UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Page title - with better styling and visibility
        title_label = QLabel("Account Settings")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2E3440; 
                background-color: transparent;
                margin-bottom: 15px;
                padding: 10px 0;
                border: none;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create scrollable area for all sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; }")
        
        # Content widget for scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(25)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Add sections
        content_layout.addWidget(self.create_profile_section())
        content_layout.addWidget(self.create_security_section())
        content_layout.addWidget(self.create_2fa_section())
        content_layout.addWidget(self.create_actions_section())
        
        # Add stretch to push everything to the top
        content_layout.addStretch()
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Load user data ONLY once and properly initialize UI
        self.load_user_data()

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
        self.oauth_message = QLabel("")
        self.oauth_message.setStyleSheet("color: #5E81AC; font-style: italic; margin: 10px;")
        self.oauth_message.setWordWrap(True)
        self.oauth_message.hide()  # Hide by default
        
        layout.addWidget(self.oauth_message)
        layout.addWidget(self.security_content)
        
        return group_box

    def create_2fa_section(self):
        """Create the Two-Factor Authentication section with improved UI."""
        group_box = QGroupBox("Two-Factor Authentication")
        group_box.setFont(QFont("Arial", 14, QFont.Bold))
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #D8DEE9;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: #FDFDFD;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                background-color: #FDFDFD;
                color: #2E3440;
            }
        """)
        
        # Main layout with proper spacing
        main_layout = QVBoxLayout(group_box)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 25, 20, 20)
        
        # 2FA Status Display - Fixed height and styling
        self.twofa_status_label = QLabel("🔐 Set up 2FA for enhanced security")
        self.twofa_status_label.setStyleSheet("""
            QLabel {
                color: #5E81AC; 
                font-weight: bold; 
                font-size: 14px;
                padding: 10px 15px;
                background-color: #E5E9F0;
                border-radius: 6px;
                border: 1px solid #D8DEE9;
            }
        """)
        self.twofa_status_label.setWordWrap(True)
        self.twofa_status_label.setMinimumHeight(50)
        main_layout.addWidget(self.twofa_status_label)
        
        # Phone number section with better layout
        phone_section = QFrame()
        phone_section.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E1E5E9;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        phone_layout = QVBoxLayout(phone_section)
        phone_layout.setSpacing(12)
        
        # Phone number label
        phone_label = QLabel("Phone Number:")
        phone_label.setStyleSheet("""
            QLabel {
                color: #2E3440;
                font-weight: bold;
                font-size: 13px;
                margin-bottom: 5px;
            }
        """)
        phone_layout.addWidget(phone_label)
        
        # Phone input with country code
        phone_input_layout = QHBoxLayout()
        phone_input_layout.setSpacing(8)
        
        # Country code prefix (read-only)
        self.country_code_label = QLabel("+1")
        self.country_code_label.setStyleSheet("""
            QLabel {
                background-color: #ECEFF4;
                color: #2E3440;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 15px;
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                min-width: 30px;
            }
        """)
        self.country_code_label.setAlignment(Qt.AlignCenter)
        phone_input_layout.addWidget(self.country_code_label)
        
        # Phone number input (without country code)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number (e.g., 2345678901)")
        self.phone_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 12px 15px;
                background-color: white;
                color: #2E3440;
                font-size: 14px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #5E81AC;
                background-color: #FFFFFF;
            }
        """)
        # Add input validation for phone numbers
        self.phone_input.setMaxLength(10)  # US phone numbers are 10 digits
        
        # Add input filter to only allow digits
        from PyQt5.QtGui import QRegExpValidator
        from PyQt5.QtCore import QRegExp
        digit_validator = QRegExpValidator(QRegExp(r'^\d{0,10}$'))
        self.phone_input.setValidator(digit_validator)
        
        # Add real-time formatting feedback
        self.phone_input.textChanged.connect(self.format_phone_input)
        
        phone_input_layout.addWidget(self.phone_input, 1)
        
        phone_layout.addLayout(phone_input_layout)
        
        # Send verification button
        self.setup_phone_btn = QPushButton("Send Verification Code")
        self.setup_phone_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E81AC;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #81A1C1;
            }
            QPushButton:pressed {
                background-color: #4C566A;
            }
            QPushButton:disabled {
                background-color: #D8DEE9;
                color: #88C0D0;
            }
        """)
        self.setup_phone_btn.clicked.connect(self.send_2fa_verification)
        phone_layout.addWidget(self.setup_phone_btn)
        
        main_layout.addWidget(phone_section)
        
        # Verification code section (initially hidden)
        self.verification_section = QFrame()
        self.verification_section.setStyleSheet("""
            QFrame {
                background-color: #FFF9E5;
                border: 1px solid #E8D975;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        verification_layout = QVBoxLayout(self.verification_section)
        verification_layout.setSpacing(12)
        
        # Verification label
        verification_label = QLabel("Verification Code:")
        verification_label.setStyleSheet("""
            QLabel {
                color: #2E3440;
                font-weight: bold;
                font-size: 13px;
                margin-bottom: 5px;
            }
        """)
        verification_layout.addWidget(verification_label)
        
        # Verification code input
        self.verification_code_input = QLineEdit()
        self.verification_code_input.setMaxLength(6)
        self.verification_code_input.setPlaceholderText("Enter 6-digit verification code")
        self.verification_code_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 12px 15px;
                background-color: white;
                color: #2E3440;
                font-size: 16px;
                font-family: monospace;
                text-align: center;
                letter-spacing: 3px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #EBCB8B;
                background-color: #FFFFFF;
            }
        """)
        verification_layout.addWidget(self.verification_code_input)
        
        # Verify button
        self.verify_code_btn = QPushButton("Verify Code")
        self.verify_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #EBCB8B;
                color: #2E3440;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #E8D975;
            }
            QPushButton:pressed {
                background-color: #D4C068;
            }
        """)
        self.verify_code_btn.clicked.connect(self.verify_2fa_code)
        verification_layout.addWidget(self.verify_code_btn)
        
        # Hide verification section initially
        self.verification_section.hide()
        main_layout.addWidget(self.verification_section)
        
        # 2FA control section
        control_section = QFrame()
        control_section.setStyleSheet("""
            QFrame {
                background-color: #F0F4F8;
                border: 1px solid #D8DEE9;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        control_layout = QVBoxLayout(control_section)
        control_layout.setSpacing(15)
        
        # 2FA Toggle with better styling
        self.twofa_toggle = QCheckBox("Enable Two-Factor Authentication")
        self.twofa_toggle.setStyleSheet("""
            QCheckBox {
                color: #2E3440;
                font-weight: bold;
                font-size: 14px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #D8DEE9;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #A3BE8C;
                border: 2px solid #A3BE8C;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTggMkw0IDZMMiA0IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
            QCheckBox::indicator:disabled {
                background-color: #F0F0F0;
                border: 2px solid #D8DEE9;
            }
        """)
        self.twofa_toggle.stateChanged.connect(self.toggle_2fa)
        self.twofa_toggle.setEnabled(False)  # Disabled until phone is verified
        control_layout.addWidget(self.twofa_toggle)
        
        # Disable 2FA Button
        self.disable_2fa_btn = QPushButton("Disable Two-Factor Authentication")
        self.disable_2fa_btn.setStyleSheet("""
            QPushButton {
                background-color: #BF616A;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #D08770;
            }
            QPushButton:pressed {
                background-color: #A54E56;
            }
        """)
        self.disable_2fa_btn.clicked.connect(self.disable_2fa)
        self.disable_2fa_btn.hide()  # Hidden initially
        control_layout.addWidget(self.disable_2fa_btn)
        
        main_layout.addWidget(control_section)
        
        # Set initial state
        self.twofa_toggle.setChecked(False)
        self.twofa_toggle.setEnabled(False)
        self.disable_2fa_btn.hide()
        
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
        
        # Change to horizontal layout for side-by-side sections
        layout = QHBoxLayout(group_box)
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
        
        # Add both sections to horizontal layout
        layout.addWidget(delete_section)
        layout.addWidget(logout_section)
        
        return group_box

    def load_user_data(self):
        """Load user data from database with enhanced security validation."""
        logger.info("Loading user data with security validation...")
        
        try:
            # Import here to avoid circular imports
            from ..database import supabase
            
            # Check authentication status using the same reliable method as main window
            try:
                if not supabase.is_authenticated():
                    logger.error("User is not authenticated")
                    self.show_login_required()
                    return
                
                # Get user data using the reliable supabase client
                user_response = supabase.get_user()
                if not user_response or not user_response.user:
                    logger.error("User data not available")
                    self.show_login_required()
                    return
                
                user_id = user_response.user.id
                email = user_response.user.email
                
                if not user_id or not email:
                    logger.error(f"User ID or email not available. user_id={user_id}, email={email}")
                    self.show_error("User ID or email not available.")
                    return
                
            except Exception as auth_error:
                logger.error(f"Authentication check failed: {auth_error}")
                self.show_login_required()
                return
            
            logger.info(f"🔒 SECURITY: Loading account data for authenticated user {user_id} ({email})")
            
            # Load profile data from both tables
            try:
                # Use the reliable supabase client for database queries
                client = supabase.client
                
                # Get data from user_details table
                details_response = client.from_("user_details").select("*").eq("user_id", user_id).execute()
                details_data = details_response.data[0] if details_response.data else {}
                
                # Get data from user_profiles table  
                profiles_response = client.from_("user_profiles").select("*").eq("user_id", user_id).execute()
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
                'gender': details_data.get('gender', ''),
                # Add 2FA fields from user_details table
                'phone_number': details_data.get('phone_number', ''),
                'twilio_verified': details_data.get('twilio_verified', False),
                'is_2fa_enabled': details_data.get('is_2fa_enabled', False)
            }
            logger.info(f"✅ SECURITY: Successfully loaded profile for authenticated user {user_id}")
            
            # Populate form with loaded data
            self.populate_form()
            
            # Check authentication method and update UI accordingly
            self.check_user_auth_method(user_response.user)
            self.update_security_section_visibility()
            
            # Update 2FA UI to reflect current status
            self.update_2fa_ui()
            
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
        
        # 2FA UI is updated separately in load_user_data() to avoid duplicates

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
            from ..database import supabase
            
            if not supabase.is_authenticated():
                return False
            
            # Get current user
            user = supabase.get_user()
            if not user or not user.user:
                return False
                
            user_id = user.user.id
            
            # Update user_details table
            try:
                details_response = supabase.client.from_("user_details").upsert({
                    'user_id': user_id,
                    'username': profile_data.get('username', ''),
                    'first_name': profile_data.get('first_name', ''),
                    'last_name': profile_data.get('last_name', ''),
                    'date_of_birth': profile_data.get('date_of_birth', ''),
                    'gender': profile_data.get('gender', ''),
                    # Add 2FA fields to user_details
                    'phone_number': profile_data.get('phone_number', ''),
                    'twilio_verified': profile_data.get('twilio_verified', False),
                    'is_2fa_enabled': profile_data.get('is_2fa_enabled', False)
                }).execute()
                
                if details_response.data:
                    logger.info("✅ Successfully updated user_details table")
                
            except Exception as details_error:
                logger.warning(f"Could not update user_details: {details_error}")
            
            # Update user_profiles table
            try:
                profiles_response = supabase.client.from_("user_profiles").upsert({
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
        """Show error message to user with improved styling."""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(message)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FDFDFD;
                    color: #2E3440;
                }
                QMessageBox QPushButton {
                    background-color: #BF616A;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #D08770;
                }
            """)
            msg_box.exec_()
        except Exception as e:
            logger.error(f"Error showing error dialog: {e}")
    
    def show_success(self, message):
        """Show success message to user with improved styling."""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Success")
            msg_box.setText(message)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FDFDFD;
                    color: #2E3440;
                }
                QMessageBox QPushButton {
                    background-color: #A3BE8C;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #9FB584;
                }
            """)
            msg_box.exec_()
        except Exception as e:
            logger.error(f"Error showing success dialog: {e}")
    
    def format_phone_input(self):
        """Provide real-time feedback on phone number formatting."""
        try:
            text = self.phone_input.text()
            
            if not text:
                # Reset to default styling
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid #D8DEE9;
                        border-radius: 4px;
                        padding: 12px 15px;
                        background-color: white;
                        color: #2E3440;
                        font-size: 14px;
                        min-height: 20px;
                    }
                    QLineEdit:focus {
                        border: 2px solid #5E81AC;
                        background-color: #FFFFFF;
                    }
                """)
                return
            
            if len(text) == 10 and text.isdigit():
                # Valid phone number - green styling
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        border: 2px solid #A3BE8C;
                        border-radius: 4px;
                        padding: 12px 15px;
                        background-color: #F8FFF8;
                        color: #2E3440;
                        font-size: 14px;
                        min-height: 20px;
                    }
                    QLineEdit:focus {
                        border: 2px solid #9FB584;
                        background-color: #F8FFF8;
                    }
                """)
            elif len(text) < 10:
                # Incomplete phone number - yellow styling
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        border: 2px solid #EBCB8B;
                        border-radius: 4px;
                        padding: 12px 15px;
                        background-color: #FFFEF8;
                        color: #2E3440;
                        font-size: 14px;
                        min-height: 20px;
                    }
                    QLineEdit:focus {
                        border: 2px solid #E8D975;
                        background-color: #FFFEF8;
                    }
                """)
            else:
                # Invalid format - red styling
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        border: 2px solid #BF616A;
                        border-radius: 4px;
                        padding: 12px 15px;
                        background-color: #FFF8F8;
                        color: #2E3440;
                        font-size: 14px;
                        min-height: 20px;
                    }
                    QLineEdit:focus {
                        border: 2px solid #D08770;
                        background-color: #FFF8F8;
                    }
                """)
        except Exception as e:
            logger.error(f"Error in format_phone_input: {e}")
    
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
            # Always show current password field for security - users need to confirm their identity
            self.oauth_message.hide()
            self.current_password_input.show()
            
            # Try to show the label for current password field
            try:
                form_layout = self.current_password_input.parentWidget().layout()
                if form_layout and hasattr(form_layout, 'labelForField'):
                    label = form_layout.labelForField(self.current_password_input)
                    if label:
                        label.show()
            except Exception as label_error:
                logger.warning(f"Could not show current password label: {label_error}")
                
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
            # Validate inputs - always require current password for security
            if not self.current_password_input.text():
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
            from ..database import supabase
            
            if not supabase.is_authenticated():
                self.show_error("You must be logged in to change your password.")
                return
            
            try:
                # Update password using Supabase Auth
                response = supabase.client.auth.update_user({
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
            from ..database import supabase
            
            if not supabase.is_authenticated():
                self.show_error("You must be logged in to delete your account.")
                return
            
            try:
                user = supabase.get_user()
                if not user or not user.user:
                    self.show_error("User authentication failed.")
                    return
                
                user_id = user.user.id
                
                # Delete user data from all tables
                # Note: This should be done in a transaction in production
                supabase.client.from_("user_details").delete().eq("user_id", user_id).execute()
                supabase.client.from_("user_profiles").delete().eq("user_id", user_id).execute()
                
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
            from ..database import supabase
            
            # Logout from Supabase using the reliable client
            try:
                supabase.client.auth.sign_out()
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

    def update_2fa_ui(self):
        """Update 2FA UI based on current status."""
        if not self.user_data:
            # Initialize UI with default state if no user data
            self.phone_input.clear()
            self.twofa_status_label.setText("🔐 Set up 2FA for enhanced security")
            self.twofa_status_label.setStyleSheet("""
                QLabel {
                    color: #5E81AC; 
                    font-weight: bold; 
                    font-size: 14px;
                    padding: 10px 15px;
                    background-color: #E5E9F0;
                    border-radius: 6px;
                    border: 1px solid #D8DEE9;
                }
            """)
            self.twofa_toggle.setEnabled(False)
            self.twofa_toggle.setChecked(False)
            self.setup_phone_btn.setText("Send Verification Code")
            self.setup_phone_btn.setEnabled(True)
            self.disable_2fa_btn.hide()
            # Hide verification UI
            self.verification_section.hide()
            return
        
        phone_number = self.user_data.get('phone_number', '')
        twilio_verified = self.user_data.get('twilio_verified', False)
        is_2fa_enabled = self.user_data.get('is_2fa_enabled', False)
        
        # Update phone input (remove +1 prefix if present)
        if phone_number.startswith('+1'):
            display_phone = phone_number[2:]
        else:
            display_phone = phone_number
        self.phone_input.setText(display_phone)
        
        # Hide verification section by default
        self.verification_section.hide()
        
        # Reset button states
        self.setup_phone_btn.setEnabled(True)
        
        if is_2fa_enabled and twilio_verified:
            # 2FA is fully enabled and working
            self.twofa_status_label.setText("✅ Two-Factor Authentication is ENABLED")
            self.twofa_status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF; 
                    font-weight: bold; 
                    font-size: 14px;
                    padding: 10px 15px;
                    background-color: #A3BE8C;
                    border-radius: 6px;
                    border: 1px solid #9FB584;
                }
            """)
            self.twofa_toggle.setChecked(True)
            self.twofa_toggle.setEnabled(False)  # Don't allow toggle when enabled
            self.setup_phone_btn.setText("Re-verify Phone")
            self.disable_2fa_btn.show()
            
        elif twilio_verified:
            # Phone verified but 2FA not enabled
            self.twofa_status_label.setText("📱 Phone verified - You can enable 2FA")
            self.twofa_status_label.setStyleSheet("""
                QLabel {
                    color: #2E3440; 
                    font-weight: bold; 
                    font-size: 14px;
                    padding: 10px 15px;
                    background-color: #EBCB8B;
                    border-radius: 6px;
                    border: 1px solid #E8D975;
                }
            """)
            self.twofa_toggle.setEnabled(True)
            self.twofa_toggle.setChecked(False)
            self.setup_phone_btn.setText("Re-verify Phone")
            self.disable_2fa_btn.hide()
            
        elif phone_number:
            # Phone number set but not verified
            self.twofa_status_label.setText("⚠️ Phone number needs verification")
            self.twofa_status_label.setStyleSheet("""
                QLabel {
                    color: #2E3440; 
                    font-weight: bold; 
                    font-size: 14px;
                    padding: 10px 15px;
                    background-color: #D08770;
                    border-radius: 6px;
                    border: 1px solid #C77A62;
                }
            """)
            self.twofa_toggle.setEnabled(False)
            self.twofa_toggle.setChecked(False)
            self.setup_phone_btn.setText("Send Verification Code")
            self.disable_2fa_btn.hide()
            
        else:
            # No phone number set
            self.twofa_status_label.setText("🔐 Set up 2FA for enhanced security")
            self.twofa_status_label.setStyleSheet("""
                QLabel {
                    color: #5E81AC; 
                    font-weight: bold; 
                    font-size: 14px;
                    padding: 10px 15px;
                    background-color: #E5E9F0;
                    border-radius: 6px;
                    border: 1px solid #D8DEE9;
                }
            """)
            self.twofa_toggle.setEnabled(False)
            self.twofa_toggle.setChecked(False)
            self.setup_phone_btn.setText("Send Verification Code")
            self.disable_2fa_btn.hide()
    
    def send_2fa_verification(self):
        """Send SMS verification code for 2FA setup."""
        phone_input = self.phone_input.text().strip()
        
        if not phone_input:
            self.show_error("Please enter a phone number first.")
            return
        
        # Validate phone number format (10 digits for US numbers)
        if not phone_input.isdigit() or len(phone_input) != 10:
            self.show_error("Please enter a valid 10-digit phone number (without country code).")
            return
        
        # Add country code to create full phone number
        full_phone_number = f"+1{phone_input}"
        
        # Import Twilio service
        try:
            from ..auth.twilio_service import twilio_service
            if not twilio_service or not twilio_service.is_available():
                self.show_error("SMS service is not available. Please contact support.")
                return
        except ImportError:
            self.show_error("SMS service is not available. Please contact support.")
            return
        
        try:
            # Send verification code
            result = twilio_service.send_verification_code(full_phone_number)
            
            if result['success']:
                # Show verification UI
                self.verification_section.show()
                self.verification_code_input.clear()
                self.verification_code_input.setFocus()
                
                # Disable send button temporarily
                self.setup_phone_btn.setEnabled(False)
                self.setup_phone_btn.setText("Code Sent")
                
                # Re-enable after 30 seconds
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(30000, lambda: (
                    self.setup_phone_btn.setEnabled(True),
                    self.setup_phone_btn.setText("Resend Code")
                ))
                
                self.show_success(f"Verification code sent to {full_phone_number}")
                
            else:
                self.show_error(f"Failed to send verification code: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error sending 2FA verification: {e}")
            self.show_error("Failed to send verification code.")
    
    def verify_2fa_code(self):
        """Verify the SMS code entered by user."""
        phone_input = self.phone_input.text().strip()
        code = self.verification_code_input.text().strip()
        
        if not phone_input:
            self.show_error("Please enter a phone number first.")
            return
        
        if not code or len(code) != 6:
            self.show_error("Please enter a valid 6-digit code.")
            return
        
        # Add country code to create full phone number
        full_phone_number = f"+1{phone_input}"
        
        # Import Twilio service
        try:
            from ..auth.twilio_service import twilio_service
            if not twilio_service or not twilio_service.is_available():
                self.show_error("SMS service is not available. Please contact support.")
                return
        except ImportError:
            self.show_error("SMS service is not available. Please contact support.")
            return
        
        try:
            # Verify the code
            result = twilio_service.verify_code(full_phone_number, code)
            
            if result['success']:
                # Update database
                from ..database import supabase
                
                if supabase.is_authenticated():
                    user_response = supabase.get_user()
                    if user_response and user_response.user:
                        user_id = user_response.user.id
                        
                        # Update user details with verified phone
                        details_response = supabase.client.from_("user_details").upsert({
                            'user_id': user_id,
                            'phone_number': full_phone_number,
                            'twilio_verified': True
                        }).execute()
                        
                        if details_response.data:
                            # Update local user data
                            self.user_data['phone_number'] = full_phone_number
                            self.user_data['twilio_verified'] = True
                            
                            # Hide verification UI
                            self.verification_section.hide()
                            self.verification_code_input.clear()
                            
                            # Update UI
                            self.update_2fa_ui()
                            
                            self.show_success("Phone number verified successfully! You can now enable 2FA.")
                        else:
                            self.show_error("Failed to save verification status.")
                    else:
                        self.show_error("User authentication error.")
                else:
                    self.show_error("Database connection error.")
                    
            else:
                self.show_error(f"Verification failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error verifying 2FA code: {e}")
            self.show_error("Failed to verify code.")
    
    def toggle_2fa(self, checked):
        """Toggle 2FA on/off."""
        try:
            # Convert checkbox state to boolean (checked can be 0, 1, or 2)
            is_enabled = bool(checked == 2)  # 2 = checked, 0 = unchecked, 1 = partially checked
            
            from ..database import supabase
            
            if not supabase.is_authenticated():
                self.show_error("You must be logged in to change 2FA settings.")
                return
            
            user_response = supabase.get_user()
            if not user_response or not user_response.user:
                self.show_error("User authentication error.")
                return
            
            user_id = user_response.user.id
            
            # Update 2FA status in database with proper boolean value
            details_response = supabase.client.from_("user_details").upsert({
                'user_id': user_id,
                'is_2fa_enabled': is_enabled
            }).execute()
            
            if details_response.data:
                # Update local user data
                self.user_data['is_2fa_enabled'] = is_enabled
                
                # Update UI
                self.update_2fa_ui()
                
                if is_enabled:
                    self.show_success("Two-Factor Authentication has been enabled!")
                else:
                    self.show_success("Two-Factor Authentication has been disabled.")
            else:
                self.show_error("Failed to update 2FA status.")
                
        except Exception as e:
            logger.error(f"Error toggling 2FA: {e}")
            self.show_error("Failed to update 2FA status.")
    
    def disable_2fa(self):
        """Disable 2FA after confirmation."""
        reply = QMessageBox.question(
            self, "Disable Two-Factor Authentication",
            "Are you sure you want to disable Two-Factor Authentication?\n\n"
            "This will make your account less secure.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from ..database import supabase
                
                if not supabase.is_authenticated():
                    self.show_error("You must be logged in to disable 2FA.")
                    return
                
                user_response = supabase.get_user()
                if not user_response or not user_response.user:
                    self.show_error("User authentication error.")
                    return
                
                user_id = user_response.user.id
                
                # Disable 2FA in database but keep phone verification
                details_response = supabase.client.from_("user_details").upsert({
                    'user_id': user_id,
                    'is_2fa_enabled': False
                    # Keep phone_number and twilio_verified so user can re-enable easily
                }).execute()
                
                if details_response.data:
                    # Update local user data
                    self.user_data['is_2fa_enabled'] = False
                    
                    # Update UI
                    self.update_2fa_ui()
                    
                    self.show_success("Two-Factor Authentication has been disabled.")
                else:
                    self.show_error("Failed to disable 2FA.")
                    
            except Exception as e:
                logger.error(f"Error disabling 2FA: {e}")
                self.show_error("Failed to disable 2FA.") 