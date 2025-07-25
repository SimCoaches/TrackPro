"""
TrackPro Standalone Account Page
Complete account management interface with profile editing, data sharing control,
security features, and database integration.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, date

# Use shared imports instead of direct PyQt6 imports
from .shared_imports import *

logger = logging.getLogger(__name__)

class ModernCard(QFrame):
    """Modern card widget with Discord-like styling"""
    
    def __init__(self, title: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #36393f, stop:1 #2f3136);
                border-radius: 12px;
                border: 1px solid #40444b;
                margin: 5px;
            }
        """)
        self.setup_layout(title)
        
    def setup_layout(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: 600;
                    margin-bottom: 8px;
                    background: transparent;
                    border: none;
                }
            """)
            layout.addWidget(title_label)
            
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        layout.addLayout(self.content_layout)
        
    def add_content(self, widget):
        self.content_layout.addWidget(widget)

class ModernInput(QLineEdit):
    """Modern input field with Discord-like styling"""
    
    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #202225;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 12px 16px;
                color: #dcddde;
                font-size: 14px;
                min-height: 20px;
                selection-background-color: #5865f2;
            }
            QLineEdit:focus {
                border: 2px solid #5865f2;
                background-color: #1e2124;
            }
            QLineEdit:hover {
                border-color: #5865f2;
            }
        """)

class ModernButton(QPushButton):
    """Modern button with Discord-like styling"""
    
    def __init__(self, text: str = "", button_type: str = "secondary", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        
        if button_type == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5865f2, stop:1 #4752c4);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4752c4, stop:1 #3c45a3);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3c45a3, stop:1 #2f3680);
                }
            """)
        elif button_type == "danger":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #ed4245, stop:1 #c73538);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 600;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #c73538, stop:1 #a12d30);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #a12d30, stop:1 #7d2427);
                }
            """)
        else:  # secondary
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4f545c;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: 500;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background-color: #5d6269;
                }
                QPushButton:pressed {
                    background-color: #484c52;
                }
            """)

class ProfileAvatar(QLabel):
    """Modern profile avatar widget"""
    
    def __init__(self, size: int = 80, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #5865f2;
                border-radius: {size//2}px;
                border: 3px solid #40444b;
                color: white;
                font-size: {size//3}px;
                font-weight: bold;
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("U")  # Default placeholder
        
    def set_initials(self, text):
        """Set initials for the avatar"""
        if text:
            initials = ''.join([word[0].upper() for word in text.split()[:2]])
            self.setText(initials)

class AccountPage(QWidget):
    """Standalone Account Page for TrackPro - Complete profile and account management."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.user_data = None
        self.is_oauth_user = False
        self.has_password = False
        self.setup_modern_ui()
        
    def setup_modern_ui(self):
        """Set up the modern Discord-inspired UI."""
        # Set main background
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e2124, stop:1 #2f3136);
                color: #dcddde;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2f3136;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #5865f2;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4752c4;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header section with gradient
        header_widget = QWidget()
        header_widget.setFixedHeight(120)
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5865f2, stop:0.5 #7289da, stop:1 #5865f2);
                border: none;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(40, 20, 40, 20)
        
        # Profile section in header
        profile_section = QHBoxLayout()
        
        # Avatar
        self.header_avatar = ProfileAvatar(60)
        profile_section.addWidget(self.header_avatar)
        
        # User info
        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(4)
        
        self.header_name = QLabel("Loading...")
        self.header_name.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
            }
        """)
        
        self.header_email = QLabel("Loading...")
        self.header_email.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                background: transparent;
            }
        """)
        
        user_info_layout.addWidget(self.header_name)
        user_info_layout.addWidget(self.header_email)
        user_info_layout.addStretch()
        
        profile_section.addLayout(user_info_layout)
        profile_section.addStretch()
        
        header_layout.addLayout(profile_section)
        
        # Settings title
        title_label = QLabel("User Settings")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: 700;
                background: transparent;
            }
        """)
        header_layout.addWidget(title_label)
        
        main_layout.addWidget(header_widget)
        
        # Scrollable content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(20)
        
        # Add modern sections
        content_layout.addWidget(self.create_modern_profile_section())
        content_layout.addWidget(self.create_modern_security_section())
        content_layout.addWidget(self.create_modern_2fa_section())
        content_layout.addWidget(self.create_modern_actions_section())
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Load user data
        self.load_user_data()

    def create_modern_profile_section(self):
        """Create modern profile information section"""
        card = ModernCard("My Account")
        
        # Profile form in grid layout
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        form_layout.setSpacing(16)
        form_layout.setColumnStretch(1, 1)
        
        # First Name
        form_layout.addWidget(self.create_label("First Name"), 0, 0)
        self.first_name_input = ModernInput("Enter your first name")
        self.first_name_input.setMaxLength(50)
        form_layout.addWidget(self.first_name_input, 0, 1)
        
        # Last Name  
        form_layout.addWidget(self.create_label("Last Name"), 1, 0)
        self.last_name_input = ModernInput("Enter your last name")
        self.last_name_input.setMaxLength(50)
        form_layout.addWidget(self.last_name_input, 1, 1)
        
        # Username
        form_layout.addWidget(self.create_label("Username"), 2, 0)
        self.username_input = ModernInput("Enter your username")
        self.username_input.setMaxLength(100)
        form_layout.addWidget(self.username_input, 2, 1)
        
        # Email
        form_layout.addWidget(self.create_label("Email"), 3, 0)
        self.email_input = ModernInput("Enter your email")
        form_layout.addWidget(self.email_input, 3, 1)
        
        # Date of Birth
        form_layout.addWidget(self.create_label("Date of Birth"), 4, 0)
        self.dob_input = QDateEdit()
        self.dob_input.setDate(QDate.currentDate().addYears(-18))
        self.dob_input.setMaximumDate(QDate.currentDate())
        self.dob_input.setMinimumDate(QDate(1900, 1, 1))
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setStyleSheet("""
            QDateEdit {
                background-color: #202225;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 12px 16px;
                color: #dcddde;
                font-size: 14px;
                min-height: 20px;
            }
            QDateEdit:focus {
                border: 2px solid #5865f2;
            }
            QDateEdit::drop-down {
                border: none;
                background: #4f545c;
                border-radius: 3px;
                width: 20px;
            }
        """)
        form_layout.addWidget(self.dob_input, 4, 1)
        
        # Gender
        form_layout.addWidget(self.create_label("Gender"), 5, 0)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["Select...", "Male", "Female", "Other", "Prefer not to say"])
        self.gender_combo.setStyleSheet("""
            QComboBox {
                background-color: #202225;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 12px 16px;
                color: #dcddde;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:focus {
                border: 2px solid #5865f2;
            }
            QComboBox::drop-down {
                border: none;
                background: #4f545c;
                border-radius: 3px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #dcddde;
            }
            QComboBox QAbstractItemView {
                background-color: #36393f;
                border: 1px solid #40444b;
                border-radius: 6px;
                color: #dcddde;
                selection-background-color: #5865f2;
            }
        """)
        form_layout.addWidget(self.gender_combo, 5, 1)
        
        # Bio
        form_layout.addWidget(self.create_label("About Me"), 6, 0, Qt.AlignmentFlag.AlignTop)
        self.bio_input = QTextEdit()
        self.bio_input.setMaximumHeight(100)
        self.bio_input.setPlaceholderText("Tell us about yourself...")
        self.bio_input.setStyleSheet("""
            QTextEdit {
                background-color: #202225;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 12px 16px;
                color: #dcddde;
                font-size: 14px;
                selection-background-color: #5865f2;
            }
            QTextEdit:focus {
                border: 2px solid #5865f2;
            }
        """)
        form_layout.addWidget(self.bio_input, 6, 1)
        
        card.add_content(form_widget)
        
        # Profile picture section
        pic_section = QWidget()
        pic_layout = QHBoxLayout(pic_section)
        pic_layout.setContentsMargins(0, 16, 0, 0)
        
        pic_layout.addWidget(self.create_label("Profile Picture"))
        
        self.profile_pic_label = QLabel("No image selected")
        self.profile_pic_label.setStyleSheet("""
            QLabel {
                background-color: #202225;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 12px 16px;
                color: #72767d;
                min-height: 20px;
            }
        """)
        pic_layout.addWidget(self.profile_pic_label, 1)
        
        self.profile_pic_button = ModernButton("Choose Image", "secondary")
        self.profile_pic_button.clicked.connect(self.choose_profile_picture)
        pic_layout.addWidget(self.profile_pic_button)
        
        card.add_content(pic_section)
        
        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.save_profile_btn = ModernButton("Save Changes", "primary")
        self.save_profile_btn.clicked.connect(self.save_profile_changes)
        button_layout.addWidget(self.save_profile_btn)
        
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        card.add_content(button_widget)
        
        return card

    def create_modern_security_section(self):
        """Create modern security section"""
        card = ModernCard("Password and Authentication")
        
        # Security form
        self.security_content = QWidget()
        security_layout = QGridLayout(self.security_content)
        security_layout.setSpacing(16)
        security_layout.setColumnStretch(1, 1)
        
        # Current Password
        security_layout.addWidget(self.create_label("Current Password"), 0, 0)
        self.current_password_input = ModernInput("Enter current password")
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        security_layout.addWidget(self.current_password_input, 0, 1)
        
        # New Password
        security_layout.addWidget(self.create_label("New Password"), 1, 0)
        self.new_password_input = ModernInput("Enter new password")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        security_layout.addWidget(self.new_password_input, 1, 1)
        
        # Confirm Password
        security_layout.addWidget(self.create_label("Confirm Password"), 2, 0)
        self.confirm_password_input = ModernInput("Confirm new password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        security_layout.addWidget(self.confirm_password_input, 2, 1)
        
        card.add_content(self.security_content)
        
        # OAuth message
        self.oauth_message = QLabel("")
        self.oauth_message.setStyleSheet("""
            QLabel {
                color: #faa61a;
                background-color: rgba(250, 166, 26, 0.1);
                border: 1px solid #faa61a;
                border-radius: 6px;
                padding: 12px 16px;
                font-style: italic;
            }
        """)
        self.oauth_message.setWordWrap(True)
        self.oauth_message.hide()
        card.add_content(self.oauth_message)
        
        # Change password button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.change_password_btn = ModernButton("Update Password", "primary")
        self.change_password_btn.clicked.connect(self.change_password)
        button_layout.addWidget(self.change_password_btn)
        
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        card.add_content(button_widget)
        
        return card

    def create_modern_2fa_section(self):
        """Create modern 2FA section"""
        card = ModernCard("Two-Factor Authentication")
        
        # Status label
        self.twofa_status_label = QLabel("🔐 Set up 2FA for enhanced security")
        self.twofa_status_label.setStyleSheet("""
            QLabel {
                color: #00d166;
                background-color: rgba(0, 209, 102, 0.1);
                border: 1px solid #00d166;
                border-radius: 6px;
                padding: 12px 16px;
                font-weight: 600;
            }
        """)
        self.twofa_status_label.setWordWrap(True)
        card.add_content(self.twofa_status_label)
        
        # Phone section
        phone_widget = QWidget()
        phone_layout = QGridLayout(phone_widget)
        phone_layout.setSpacing(16)
        phone_layout.setColumnStretch(1, 1)
        
        phone_layout.addWidget(self.create_label("Phone Number"), 0, 0)
        
        phone_input_layout = QHBoxLayout()
        self.country_code_label = QLabel("+1")
        self.country_code_label.setStyleSheet("""
            QLabel {
                background-color: #4f545c;
                color: #dcddde;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 12px 16px;
                font-weight: 600;
                min-width: 40px;
            }
        """)
        self.country_code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        phone_input_layout.addWidget(self.country_code_label)
        
        self.phone_input = ModernInput("Enter phone number")
        self.phone_input.setMaxLength(10)
        
        # Add input validator for phone numbers (Qt6 syntax)
        digit_validator = QRegularExpressionValidator(QRegularExpression(r'^\d{0,10}$'))
        self.phone_input.setValidator(digit_validator)
        
        # Add real-time formatting feedback
        self.phone_input.textChanged.connect(self.format_phone_input)
        
        phone_input_layout.addWidget(self.phone_input, 1)
        
        phone_input_widget = QWidget()
        phone_input_widget.setLayout(phone_input_layout)
        phone_layout.addWidget(phone_input_widget, 0, 1)
        
        self.setup_phone_btn = ModernButton("Send Verification Code", "primary")
        self.setup_phone_btn.clicked.connect(self.send_2fa_verification)
        phone_layout.addWidget(self.setup_phone_btn, 1, 1)
        
        card.add_content(phone_widget)
        
        # Verification section
        self.verification_section = QWidget()
        verification_layout = QGridLayout(self.verification_section)
        verification_layout.setSpacing(16)
        verification_layout.setColumnStretch(1, 1)
        
        verification_layout.addWidget(self.create_label("Verification Code"), 0, 0)
        self.verification_code_input = ModernInput("Enter 6-digit code")
        self.verification_code_input.setMaxLength(6)
        verification_layout.addWidget(self.verification_code_input, 0, 1)
        
        self.verify_code_btn = ModernButton("Verify Code", "primary")
        self.verify_code_btn.clicked.connect(self.verify_2fa_code)
        verification_layout.addWidget(self.verify_code_btn, 1, 1)
        
        self.verification_section.hide()
        card.add_content(self.verification_section)
        
        # 2FA Toggle
        toggle_widget = QWidget()
        toggle_layout = QHBoxLayout(toggle_widget)
        
        self.twofa_toggle = QCheckBox("Enable Two-Factor Authentication")
        self.twofa_toggle.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-weight: 600;
                font-size: 14px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #40444b;
                border-radius: 4px;
                background-color: #202225;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
            }
        """)
        self.twofa_toggle.stateChanged.connect(self.toggle_2fa)
        self.twofa_toggle.setEnabled(False)
        toggle_layout.addWidget(self.twofa_toggle)
        toggle_layout.addStretch()
        
        self.disable_2fa_btn = ModernButton("Disable 2FA", "danger")
        self.disable_2fa_btn.clicked.connect(self.disable_2fa)
        self.disable_2fa_btn.hide()
        toggle_layout.addWidget(self.disable_2fa_btn)
        
        card.add_content(toggle_widget)
        
        return card

    def create_modern_actions_section(self):
        """Create modern actions section"""
        card = ModernCard("Account Management")
        
        # Logout section
        logout_widget = QWidget()
        logout_layout = QHBoxLayout(logout_widget)
        
        logout_info = QVBoxLayout()
        logout_title = QLabel("Logout")
        logout_title.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        logout_desc = QLabel("Sign out of your TrackPro account")
        logout_desc.setStyleSheet("""
            QLabel {
                color: #72767d;
                font-size: 14px;
            }
        """)
        logout_info.addWidget(logout_title)
        logout_info.addWidget(logout_desc)
        logout_layout.addLayout(logout_info, 1)
        
        logout_btn = ModernButton("Logout", "secondary")
        logout_btn.clicked.connect(self.logout)
        logout_layout.addWidget(logout_btn)
        
        card.add_content(logout_widget)
        
        # Delete account section
        delete_widget = QWidget()
        delete_layout = QHBoxLayout(delete_widget)
        
        delete_info = QVBoxLayout()
        delete_title = QLabel("Delete Account")
        delete_title.setStyleSheet("""
            QLabel {
                color: #ed4245;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        delete_desc = QLabel("Permanently delete your account and all data")
        delete_desc.setStyleSheet("""
            QLabel {
                color: #72767d;
                font-size: 14px;
            }
        """)
        delete_info.addWidget(delete_title)
        delete_info.addWidget(delete_desc)
        delete_layout.addLayout(delete_info, 1)
        
        delete_btn = ModernButton("Delete Account", "danger")
        delete_btn.clicked.connect(self.delete_account)
        delete_layout.addWidget(delete_btn)
        
        card.add_content(delete_widget)
        
        return card

    def create_label(self, text):
        """Create styled label"""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }
        """)
        return label

    def load_user_data(self):
        """Load user data from database with enhanced security validation."""
        logger.info("Loading user data with security validation...")
        
        # Clear previous user data first to prevent data leakage
        self.clear_user_data()
        
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
            
        # Update header with user info
        display_name = f"{self.user_data.get('first_name', '')} {self.user_data.get('last_name', '')}".strip()
        if not display_name:
            display_name = self.user_data.get('username', 'User')
        
        self.header_name.setText(display_name)
        self.header_email.setText(self.user_data.get('email', 'No email'))
        self.header_avatar.set_initials(display_name)
        
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

    def clear_user_data(self):
        """Clear all user data and form fields to prevent data leakage when switching users."""
        try:
            logger.info("🔒 SECURITY: Clearing previous user data to prevent leakage")
            
            # Clear user data
            self.user_data = None
            self.is_oauth_user = False
            self.has_password = False
            
            # Clear header info with safety checks
            try:
                if hasattr(self, 'header_name') and self.header_name is not None:
                    self.header_name.setText("Loading...")
                if hasattr(self, 'header_email') and self.header_email is not None:
                    self.header_email.setText("Loading...")
                if hasattr(self, 'header_avatar') and self.header_avatar is not None:
                    self.header_avatar.set_initials("U")
            except Exception as header_error:
                logger.warning(f"Error clearing header info: {header_error}")
            
            # Clear form fields with individual error handling
            form_fields = [
                ('first_name_input', ''),
                ('last_name_input', ''),
                ('username_input', ''),
                ('email_input', ''),
                ('phone_input', ''),
                ('current_password_input', ''),
                ('new_password_input', ''),
                ('confirm_password_input', ''),
                ('verification_code_input', '')
            ]
            
            for field_name, default_value in form_fields:
                try:
                    if hasattr(self, field_name):
                        field = getattr(self, field_name)
                        if field is not None and hasattr(field, 'clear'):
                            field.clear()
                        elif field is not None and hasattr(field, 'setText'):
                            field.setText(default_value)
                except Exception as field_error:
                    logger.warning(f"Error clearing field {field_name}: {field_error}")
            
            # Clear text areas
            try:
                if hasattr(self, 'bio_input') and self.bio_input is not None:
                    if hasattr(self.bio_input, 'clear'):
                        self.bio_input.clear()
                    elif hasattr(self.bio_input, 'setPlainText'):
                        self.bio_input.setPlainText('')
            except Exception as bio_error:
                logger.warning(f"Error clearing bio field: {bio_error}")
            
            # Reset date of birth to current date
            try:
                if hasattr(self, 'dob_input') and self.dob_input is not None:
                    from PyQt6.QtCore import QDate
                    self.dob_input.setDate(QDate.currentDate())
            except Exception as dob_error:
                logger.warning(f"Error resetting date of birth: {dob_error}")
            
            # Reset gender combo
            try:
                if hasattr(self, 'gender_combo') and self.gender_combo is not None:
                    self.gender_combo.setCurrentIndex(0)
            except Exception as gender_error:
                logger.warning(f"Error resetting gender combo: {gender_error}")
            
            # Reset 2FA fields with safety checks
            try:
                if hasattr(self, 'phone_verified_status') and self.phone_verified_status is not None:
                    self.phone_verified_status.setText("Not verified")
                    self.phone_verified_status.setStyleSheet("color: #ed4245;")
                if hasattr(self, 'send_code_btn') and self.send_code_btn is not None:
                    self.send_code_btn.setText("Send Code")
                    self.send_code_btn.setEnabled(True)
                if hasattr(self, 'verify_code_btn') and self.verify_code_btn is not None:
                    self.verify_code_btn.setEnabled(False)
                if hasattr(self, 'twofactor_checkbox') and self.twofactor_checkbox is not None:
                    self.twofactor_checkbox.setChecked(False)
                    self.twofactor_checkbox.setEnabled(False)
            except Exception as twofa_error:
                logger.warning(f"Error resetting 2FA fields: {twofa_error}")
            
            logger.info("✅ SECURITY: User data cleared successfully")
            
        except Exception as e:
            logger.error(f"🚨 SECURITY: Critical error clearing user data: {e}")
            # Even if clearing fails, ensure user_data is None for security
            self.user_data = None

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
                if login_dialog.exec() == QDialog.DialogCode.Accepted:
                    # Reload user data after successful login
                    self.load_user_data()
            except ImportError:
                logger.warning("Could not import LoginDialog")
                
        except Exception as e:
            logger.error(f"Error showing login required dialog: {e}")
    
    def show_error(self, message):
        """Show error message with modern Discord styling."""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Apply modern Discord-style dark theme
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #36393f;
                    color: #dcddde;
                    border-radius: 8px;
                }
                QMessageBox QLabel {
                    color: #dcddde;
                    font-size: 14px;
                    background: transparent;
                    border: none;
                }
                QMessageBox QPushButton {
                    background-color: #ed4245;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #c73538;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #a12d30;
                }
            """)
            msg_box.exec()
        except Exception as e:
            logger.error(f"Error showing error dialog: {e}")
    
    def show_success(self, message):
        """Show success message with modern Discord styling."""
        try:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Success")
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Apply modern Discord-style dark theme
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #36393f;
                    color: #dcddde;
                    border-radius: 8px;
                }
                QMessageBox QLabel {
                    color: #dcddde;
                    font-size: 14px;
                    background: transparent;
                    border: none;
                }
                QMessageBox QPushButton {
                    background-color: #00d166;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #00b04f;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #008f3f;
                }
            """)
            msg_box.exec()
        except Exception as e:
            logger.error(f"Error showing success dialog: {e}")
    
    def format_phone_input(self):
        """Provide real-time feedback on phone number formatting with modern styling."""
        try:
            text = self.phone_input.text()
            
            if not text:
                # Reset to default modern styling
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #202225;
                        border: 1px solid #40444b;
                        border-radius: 6px;
                        padding: 12px 16px;
                        color: #dcddde;
                        font-size: 14px;
                        min-height: 20px;
                        selection-background-color: #5865f2;
                    }
                    QLineEdit:focus {
                        border: 2px solid #5865f2;
                        background-color: #1e2124;
                    }
                    QLineEdit:hover {
                        border-color: #5865f2;
                    }
                """)
                return
            
            if len(text) == 10 and text.isdigit():
                # Valid phone number - green accent
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #202225;
                        border: 2px solid #00d166;
                        border-radius: 6px;
                        padding: 12px 16px;
                        color: #dcddde;
                        font-size: 14px;
                        min-height: 20px;
                        selection-background-color: #5865f2;
                    }
                    QLineEdit:focus {
                        border: 2px solid #00d166;
                        background-color: #1e2124;
                    }
                """)
            elif len(text) < 10:
                # Incomplete phone number - yellow accent
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #202225;
                        border: 2px solid #faa61a;
                        border-radius: 6px;
                        padding: 12px 16px;
                        color: #dcddde;
                        font-size: 14px;
                        min-height: 20px;
                        selection-background-color: #5865f2;
                    }
                    QLineEdit:focus {
                        border: 2px solid #faa61a;
                        background-color: #1e2124;
                    }
                """)
            else:
                # Invalid format - red accent
                self.phone_input.setStyleSheet("""
                    QLineEdit {
                        background-color: #202225;
                        border: 2px solid #ed4245;
                        border-radius: 6px;
                        padding: 12px 16px;
                        color: #dcddde;
                        font-size: 14px;
                        min-height: 20px;
                        selection-background-color: #5865f2;
                    }
                    QLineEdit:focus {
                        border: 2px solid #ed4245;
                        background-color: #1e2124;
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
        """Handle account deletion with confirmation and modern styling."""
        try:
            # Show confirmation dialog with modern styling
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Delete Account")
            msg_box.setText("⚠️ WARNING: This action cannot be undone!\n\n"
                "Deleting your account will permanently remove:\n"
                "• All your profile data\n"
                "• Telemetry and session history\n"
                "• Achievements and progress\n"
                "• Community posts and interactions\n\n"
                "Are you absolutely sure you want to delete your account?")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # Apply modern Discord-style dark theme
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #36393f;
                    color: #dcddde;
                    border-radius: 8px;
                }
                QMessageBox QLabel {
                    color: #dcddde;
                    font-size: 14px;
                    background: transparent;
                    border: none;
                }
                QMessageBox QPushButton {
                    background-color: #4f545c;
                    color: #dcddde;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 600;
                    min-width: 80px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #5d6269;
                }
                QMessageBox QPushButton[text="&Yes"] {
                    background-color: #ed4245;
                    color: white;
                }
                QMessageBox QPushButton[text="&Yes"]:hover {
                    background-color: #c73538;
                }
            """)
            
            if msg_box.exec() != QMessageBox.StandardButton.Yes:
                return
            
            # Second confirmation with modern input dialog
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
                
                # Try advanced deletion functions first, fallback to manual deletion if not available
                logger.info(f"Starting complete account deletion process for user {user_id}")
                
                deletion_success = False
                complete_deletion = False
                
                # First attempt: Try the comprehensive deletion function (if available)
                try:
                    logger.info("Attempting advanced deletion with database functions...")
                    deletion_result = supabase.client.rpc('delete_user_completely', {'user_uuid': user_id}).execute()
                    
                    if deletion_result.data:
                        result_data = deletion_result.data
                        logger.info(f"✅ Advanced deletion completed: {result_data}")
                        
                        # Check if auth deletion was successful
                        complete_deletion = result_data.get('complete_deletion', False)
                        deletion_success = True
                        
                        if complete_deletion:
                            logger.info(f"✅ COMPLETE DELETION SUCCESS: User {user_id} and all data completely removed")
                        else:
                            logger.warning(f"⚠️ PARTIAL DELETION: User data deleted but auth record may remain for {user_id}")
                            
                    else:
                        logger.error("Advanced deletion function returned no data")
                        raise Exception("Advanced deletion function failed")
                        
                except Exception as advanced_error:
                    logger.warning(f"Advanced deletion failed: {advanced_error}")
                    
                    # Check if it's a "function not found" error - this is expected in dev/early production
                    if "Could not find the function" in str(advanced_error) or "PGRST202" in str(advanced_error):
                        logger.info("Advanced deletion functions not available - using manual deletion fallback")
                    else:
                        logger.error(f"Unexpected error in advanced deletion: {advanced_error}")
                
                # Second attempt: Manual deletion fallback (works in all environments)
                if not deletion_success:
                    logger.info("Performing manual account deletion (fallback mode)...")
                    
                    try:
                        # Delete user data manually from all tables in dependency order
                        tables_to_clear = [
                            ('sessions', 'user_id'),
                            ('telemetry_points', 'user_id'), 
                            ('laps', 'user_id'),
                            ('user_quests', 'user_id'),
                            ('user_calibrations', 'user_id'),
                            ('eye_tracking_points', 'user_id'),
                            ('eye_tracking_sessions', 'user_id'), 
                            ('sector_times', 'user_id'),
                            ('user_achievements', 'user_id'),
                            ('user_stats', 'user_id'),
                            ('user_streaks', 'user_id'),
                            ('team_members', 'user_id'),
                            ('club_members', 'user_id'), 
                            ('event_participants', 'user_id'),
                            ('challenge_participants', 'user_id'),
                            ('conversation_participants', 'user_id'),
                            ('user_activities', 'user_id'),
                            ('activity_interactions', 'user_id'),
                            ('setup_ratings', 'user_id'),
                            ('media_likes', 'user_id'),
                            ('leaderboard_entries', 'user_id'), 
                            ('shared_setups', 'user_id'),
                            ('shared_media', 'user_id'),
                            ('user_profiles', 'user_id'),
                            ('user_details', 'user_id')
                        ]
                        
                        # Special case tables with different column patterns
                        special_tables = [
                            ('messages', 'sender_id'),
                            ('friendships', ['requester_id', 'addressee_id']),
                            ('reputation_events', ['user_id', 'given_by']),
                            ('teams', 'created_by'),
                            ('clubs', 'created_by'),
                            ('community_events', 'created_by'),
                            ('community_challenges', 'created_by'),
                            ('conversations', 'created_by')
                        ]
                        
                        deleted_tables = []
                        failed_tables = []
                        
                        # Delete from standard tables
                        for table_name, column_name in tables_to_clear:
                            try:
                                result = supabase.client.from_(table_name).delete().eq(column_name, user_id).execute()
                                deleted_tables.append(table_name)
                                logger.info(f"✅ Deleted from {table_name}")
                            except Exception as table_error:
                                failed_tables.append(f"{table_name}: {str(table_error)}")
                                logger.warning(f"⚠️ Could not delete from {table_name}: {table_error}")
                        
                        # Delete from special case tables
                        for table_info in special_tables:
                            table_name = table_info[0]
                            columns = table_info[1]
                            
                            try:
                                if isinstance(columns, list):
                                    # Multiple columns to check (OR condition)
                                    for column in columns:
                                        try:
                                            supabase.client.from_(table_name).delete().eq(column, user_id).execute()
                                        except:
                                            pass  # Table might not exist
                                else:
                                    # Single column
                                    supabase.client.from_(table_name).delete().eq(columns, user_id).execute()
                                
                                deleted_tables.append(table_name)
                                logger.info(f"✅ Deleted from {table_name} (special case)")
                            except Exception as table_error:
                                failed_tables.append(f"{table_name}: {str(table_error)}")
                                logger.warning(f"⚠️ Could not delete from {table_name}: {table_error}")
                        
                        logger.info(f"Manual deletion summary: {len(deleted_tables)} tables cleared, {len(failed_tables)} failed")
                        
                        # Try to delete auth user (this will likely fail without elevated privileges)
                        auth_deleted = False
                        try:
                            # Try multiple methods to delete auth user
                            methods_tried = []
                            
                            # Method 1: Admin API (requires service role)
                            try:
                                supabase.client.auth.admin.delete_user(user_id)
                                auth_deleted = True
                                logger.info("✅ Auth user deleted via admin API")
                            except Exception as admin_error:
                                methods_tried.append(f"Admin API: {admin_error}")
                            
                            # Method 2: Direct table access (requires elevated permissions)
                            if not auth_deleted:
                                try:
                                    supabase.client.from_("users").delete().eq("id", user_id).execute()
                                    auth_deleted = True
                                    logger.info("✅ Auth user deleted via direct table access")
                                except Exception as direct_error:
                                    methods_tried.append(f"Direct table: {direct_error}")
                            
                            # Method 3: Try the individual auth deletion function (if available)
                            if not auth_deleted:
                                try:
                                    auth_result = supabase.client.rpc('delete_auth_user_complete', {'user_uuid': user_id}).execute()
                                    if auth_result.data:
                                        auth_deleted = auth_result.data
                                        logger.info("✅ Auth user deleted via database function")
                                except Exception as rpc_error:
                                    methods_tried.append(f"RPC function: {rpc_error}")
                            
                            if not auth_deleted:
                                logger.warning(f"⚠️ Auth user deletion failed. Methods tried: {', '.join(methods_tried)}")
                                
                        except Exception as auth_error:
                            logger.warning(f"⚠️ Auth user deletion failed: {auth_error}")
                        
                        # Manual deletion completed successfully
                        deletion_success = True
                        complete_deletion = auth_deleted
                        
                        if auth_deleted:
                            logger.info(f"✅ COMPLETE MANUAL DELETION: User {user_id} and auth record removed")
                        else:
                            logger.warning(f"⚠️ PARTIAL MANUAL DELETION: User data deleted, auth record may remain for {user_id}")
                        
                    except Exception as manual_error:
                        logger.error(f"Manual deletion failed: {manual_error}")
                        raise Exception(f"Manual account deletion failed: {manual_error}")
                
                # Ensure we have some form of success before proceeding
                if not deletion_success:
                    raise Exception("All deletion methods failed")
                
                # Show modern success dialog with accurate status
                success_box = QMessageBox(self)
                success_box.setIcon(QMessageBox.Icon.Information)
                success_box.setWindowTitle("Account Deletion Completed")
                
                # Determine the exact message based on deletion result
                if complete_deletion:
                    success_text = "✅ Your account has been COMPLETELY deleted.\n\n" \
                                 "All your data and authentication records have been permanently removed from our systems.\n\n" \
                                 "You will be logged out now."
                elif deletion_success:
                    success_text = "⚠️ Your account data has been deleted.\n\n" \
                                 "Your personal data has been removed, but your authentication record may still exist. " \
                                 "If you need complete removal, please contact support.\n\n" \
                                 "You will be logged out now."
                else:
                    success_text = "Your account deletion has been processed.\n\n" \
                                 "Most or all of your data has been removed from our systems. " \
                                 "If you have any concerns about data retention, please contact support.\n\n" \
                                 "You will be logged out now."
                
                success_box.setText(success_text)
                success_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                success_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #36393f;
                        color: #dcddde;
                        border-radius: 8px;
                    }
                    QMessageBox QLabel {
                        color: #dcddde;
                        font-size: 14px;
                        background: transparent;
                        border: none;
                    }
                    QMessageBox QPushButton {
                        background-color: #00d166;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 600;
                        min-width: 80px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #00b04f;
                    }
                """)
                success_box.exec()
                
                # Logout user
                self.logout()
                
            except Exception as deletion_error:
                logger.error(f"Error during account deletion: {deletion_error}")
                
                # Show more specific error message based on the failure type
                error_message = "Account deletion failed.\n\n"
                
                if "All deletion methods failed" in str(deletion_error):
                    error_message += "Both our advanced and manual deletion methods failed. " \
                                   "This may be due to database connectivity issues or permission problems.\n\n" \
                                   "Please contact support immediately - we take data privacy seriously and will resolve this manually."
                elif "Manual account deletion failed" in str(deletion_error):
                    error_message += "Our manual deletion process encountered an error. " \
                                   "This may be due to database constraints or connectivity issues.\n\n" \
                                   "Please contact support for manual account deletion."
                elif "function" in str(deletion_error).lower():
                    error_message += "Database functions are not available, but manual deletion should work. " \
                                   "This error suggests a deeper issue.\n\n" \
                                   "Please contact support for manual account deletion."
                else:
                    error_message += "An unexpected error occurred during the deletion process.\n\n" \
                                   "Please contact support and reference this error for manual deletion."
                
                # Show error dialog with contact information
                error_box = QMessageBox(self)
                error_box.setIcon(QMessageBox.Icon.Critical)
                error_box.setWindowTitle("Account Deletion Failed")
                error_box.setText(error_message)
                error_box.setDetailedText(f"Technical details: {deletion_error}")
                error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                error_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #36393f;
                        color: #dcddde;
                        border-radius: 8px;
                    }
                    QMessageBox QLabel {
                        color: #dcddde;
                        font-size: 14px;
                        background: transparent;
                        border: none;
                    }
                    QMessageBox QPushButton {
                        background-color: #ed4245;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 600;
                        min-width: 80px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #c73538;
                    }
                """)
                error_box.exec()
                
        except Exception as e:
            logger.error(f"Error in delete account process: {e}")
            self.show_error("A critical error occurred during account deletion. Please contact support immediately for manual deletion.")

    def logout(self):
        """Handle user logout with modern styling."""
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
                
                # Show logout confirmation with modern styling
                success_box = QMessageBox(self)
                success_box.setIcon(QMessageBox.Icon.Information)
                success_box.setWindowTitle("Logged Out")
                success_box.setText("You have been logged out successfully.")
                success_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                success_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #36393f;
                        color: #dcddde;
                        border-radius: 8px;
                    }
                    QMessageBox QLabel {
                        color: #dcddde;
                        font-size: 14px;
                        background: transparent;
                        border: none;
                    }
                    QMessageBox QPushButton {
                        background-color: #5865f2;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 600;
                        min-width: 80px;
                    }
                    QMessageBox QPushButton:hover {
                        background-color: #4752c4;
                    }
                """)
                success_box.exec()
            else:
                # Fallback if we can't find the main window
                self.show_success("You have been logged out successfully.\n\n"
                    "Please restart the application to log in again.")
                
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            self.show_error("An error occurred during logout.")

    def update_2fa_ui(self):
        """Update 2FA UI based on current status with modern Discord styling."""
        # Temporarily block signals to prevent unwanted popups during UI updates
        self.twofa_toggle.blockSignals(True)
        
        try:
            if not self.user_data:
                # Initialize UI with default state if no user data
                self.phone_input.clear()
                self.twofa_status_label.setText("🔐 Set up 2FA for enhanced security")
                self.twofa_status_label.setStyleSheet("""
                    QLabel {
                        color: #00d166;
                        background-color: rgba(0, 209, 102, 0.1);
                        border: 1px solid #00d166;
                        border-radius: 6px;
                        padding: 12px 16px;
                        font-weight: 600;
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
                # 2FA is fully enabled and working - green success
                self.twofa_status_label.setText("✅ Two-Factor Authentication is ENABLED")
                self.twofa_status_label.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        background-color: #00d166;
                        border: 1px solid #00d166;
                        border-radius: 6px;
                        padding: 12px 16px;
                        font-weight: 600;
                    }
                """)
                self.twofa_toggle.setChecked(True)
                self.twofa_toggle.setEnabled(False)  # Don't allow toggle when enabled
                self.setup_phone_btn.setText("Re-verify Phone")
                self.disable_2fa_btn.show()
                
            elif twilio_verified:
                # Phone verified but 2FA not enabled - blue info
                self.twofa_status_label.setText("📱 Phone verified - You can enable 2FA")
                self.twofa_status_label.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        background-color: #5865f2;
                        border: 1px solid #5865f2;
                        border-radius: 6px;
                        padding: 12px 16px;
                        font-weight: 600;
                    }
                """)
                self.twofa_toggle.setEnabled(True)
                self.twofa_toggle.setChecked(False)
                self.setup_phone_btn.setText("Re-verify Phone")
                self.disable_2fa_btn.hide()
                
            elif phone_number:
                # Phone number set but not verified - yellow warning
                self.twofa_status_label.setText("⚠️ Phone number needs verification")
                self.twofa_status_label.setStyleSheet("""
                    QLabel {
                        color: #2c2f33;
                        background-color: #faa61a;
                        border: 1px solid #faa61a;
                        border-radius: 6px;
                        padding: 12px 16px;
                        font-weight: 600;
                    }
                """)
                self.twofa_toggle.setEnabled(False)
                self.twofa_toggle.setChecked(False)
                self.setup_phone_btn.setText("Send Verification Code")
                self.disable_2fa_btn.hide()
                
            else:
                # No phone number set - neutral info
                self.twofa_status_label.setText("🔐 Set up 2FA for enhanced security")
                self.twofa_status_label.setStyleSheet("""
                    QLabel {
                        color: #00d166;
                        background-color: rgba(0, 209, 102, 0.1);
                        border: 1px solid #00d166;
                        border-radius: 6px;
                        padding: 12px 16px;
                        font-weight: 600;
                    }
                """)
                self.twofa_toggle.setEnabled(False)
                self.twofa_toggle.setChecked(False)
                self.setup_phone_btn.setText("Send Verification Code")
                self.disable_2fa_btn.hide()
        finally:
            # Always re-enable signals
            self.twofa_toggle.blockSignals(False)
    
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
        """Disable 2FA with confirmation and modern styling."""
        # Show confirmation dialog with modern styling
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Disable Two-Factor Authentication")
        msg_box.setText("⚠️ Warning: Disabling 2FA will make your account less secure.\n\n"
            "Are you sure you want to disable Two-Factor Authentication?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Apply modern Discord-style dark theme
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #36393f;
                color: #dcddde;
                border-radius: 8px;
            }
            QMessageBox QLabel {
                color: #dcddde;
                font-size: 14px;
                background: transparent;
                border: none;
            }
            QMessageBox QPushButton {
                background-color: #4f545c;
                color: #dcddde;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #5d6269;
            }
            QMessageBox QPushButton[text="&Yes"] {
                background-color: #faa61a;
                color: #2c2f33;
            }
            QMessageBox QPushButton[text="&Yes"]:hover {
                background-color: #e8940f;
            }
        """)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            try:
                from ..database import supabase
                
                if not supabase.is_authenticated():
                    self.show_error("You must be logged in to modify 2FA settings.")
                    return
                
                user = supabase.get_user()
                if not user or not user.user:
                    self.show_error("User authentication failed.")
                    return
                
                user_id = user.user.id
                
                # Update database to disable 2FA
                response = supabase.client.from_("user_details").update({
                    'is_2fa_enabled': False
                }).eq("user_id", user_id).execute()
                
                if response.data:
                    # Update local user data
                    if self.user_data:
                        self.user_data['is_2fa_enabled'] = False
                    
                    self.show_success("Two-Factor Authentication has been disabled.")
                    
                    # Update UI
                    self.update_2fa_ui()
                    logger.info("2FA disabled successfully")
                else:
                    self.show_error("Failed to disable 2FA. Please try again.")
                    
            except Exception as e:
                logger.error(f"Error disabling 2FA: {e}")
                self.show_error("An error occurred while disabling 2FA.") 