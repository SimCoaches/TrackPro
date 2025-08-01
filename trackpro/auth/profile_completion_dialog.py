"""Profile completion dialog for new users after authentication."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QFrame, QComboBox, QCheckBox, QFormLayout, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
from ..config import config
import logging
import re

# Twilio import with fallback
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None
    TwilioException = Exception

logger = logging.getLogger(__name__)

class ProfileCompletionDialog(BaseAuthDialog):
    """Dialog for completing user profile setup after first login."""
    
    profile_completed = pyqtSignal(bool)  # Emitted when profile is completed
    
    def __init__(self, user_id, user_email, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.user_email = user_email
        self.twilio_client = None
        self.setup_twilio()
        self.setup_ui()
        
    def setup_twilio(self):
        """Initialize Twilio client if credentials are available."""
        if not TWILIO_AVAILABLE:
            logger.warning("Twilio library not available. 2FA features will be disabled.")
            return
            
        try:
            account_sid = config.twilio_account_sid
            auth_token = config.twilio_auth_token
            
            if account_sid and auth_token:
                self.twilio_client = TwilioClient(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            else:
                logger.warning("Twilio credentials not configured. 2FA features will be disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
    
    def setup_ui(self):
        """Set up the profile completion interface."""
        self.setWindowTitle("Complete Your TrackPro Profile")
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        title_label = QLabel("Welcome to TrackPro!")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel("Complete your profile to get started")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle_label)
        
        # Form
        form_layout = QFormLayout()
        
        # Username (required)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        form_layout.addRow("Username *", self.username_input)
        
        # Display name
        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Your display name")
        form_layout.addRow("Display Name", self.display_name_input)
        
        # Phone for 2FA (optional)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+1234567890 (optional for 2FA)")
        form_layout.addRow("Phone Number", self.phone_input)
        
        layout.addLayout(form_layout)
        
        # 2FA checkbox
        self.enable_2fa_checkbox = QCheckBox("Enable SMS-based 2FA (recommended)")
        layout.addWidget(self.enable_2fa_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        skip_button = QPushButton("Skip for Now")
        skip_button.clicked.connect(self.skip_profile)
        
        complete_button = QPushButton("Complete Profile")
        complete_button.clicked.connect(self.complete_profile)
        complete_button.setDefault(True)
        
        button_layout.addWidget(skip_button)
        button_layout.addWidget(complete_button)
        layout.addLayout(button_layout)
        
    def skip_profile(self):
        """Create minimal profile and continue."""
        self.create_profile(minimal=True)
        
    def complete_profile(self):
        """Create full profile with provided information."""
        self.create_profile(minimal=False)
        
    def create_profile(self, minimal=False):
        """Create user profile in database."""
        try:
            if minimal:
                username = f"racer_{self.user_id[:8]}"
                display_name = username
                phone_number = None
                twilio_verified = False
                is_2fa_enabled = False
            else:
                username = self.username_input.text().strip()
                if not username:
                    QMessageBox.warning(self, "Username Required", "Please enter a username.")
                    return
                    
                display_name = self.display_name_input.text().strip() or username
                phone_number = self.phone_input.text().strip() or None
                twilio_verified = False  # Would be verified in full implementation
                is_2fa_enabled = self.enable_2fa_checkbox.isChecked() and phone_number
            
            # Create profile
            profile_data = {
                'user_id': self.user_id,
                'email': self.user_email,
                'username': username,
                'display_name': display_name,
                'phone_number': phone_number,
                'twilio_verified': twilio_verified,
                'is_2fa_enabled': is_2fa_enabled,
                'current_xp': 0,
                'level': 1,
                'race_pass_xp': 0,
                'total_xp_earned': 0,
                'has_premium_pass': False,
                'social_xp': 0,
                'prestige_level': 0,
                'reputation_score': 0,
                'share_data': True,
                'privacy_settings': {},
                'preferences': {},
                'settings': {}
            }
            
            result = supabase.table('user_profiles').insert(profile_data).execute()
            
            if result.data:
                logger.info(f"Profile created for user {self.user_id}")
                QMessageBox.information(self, "Profile Created", 
                                      f"Welcome to TrackPro, {username}! 🏁")
                self.profile_completed.emit(True)
                self.accept()
            else:
                raise Exception("Failed to create profile")
                
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create profile: {str(e)}") 