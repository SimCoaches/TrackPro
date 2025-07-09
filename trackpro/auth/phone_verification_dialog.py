"""Phone verification dialog for 2FA setup."""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QRegExpValidator
from PyQt5.QtCore import QRegExp
from .twilio_service import twilio_service, TWILIO_AVAILABLE

logger = logging.getLogger(__name__)

class PhoneVerificationDialog(QDialog):
    """Simple phone verification dialog for 2FA setup."""
    
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id
        self.phone_number = None
        self.verification_code = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Verify Phone Number")
        self.setFixedSize(400, 320)
        self.setModal(True)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Verify your phone number")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        description = QLabel("We'll send a 6-digit code to verify your number")
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Phone section
        phone_label = QLabel("Phone Number:")
        phone_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(phone_label)
        
        # Phone input container
        phone_container = QHBoxLayout()
        
        # Country code
        country_code = QLabel("+1")
        country_code.setFixedWidth(40)
        country_code.setMinimumHeight(35)  # Match phone input height
        country_code.setAlignment(Qt.AlignCenter)
        country_code.setFont(QFont("Arial", 12))  # Match phone input font
        country_code.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                color: #333333;
            }
        """)
        phone_container.addWidget(country_code)
        
        # Phone input
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number")
        self.phone_input.setMaxLength(10)
        self.phone_input.setMinimumHeight(35)  # Make it bigger
        self.phone_input.setFont(QFont("Arial", 12))  # Bigger font
        digit_validator = QRegExpValidator(QRegExp(r'^\d{0,10}$'))
        self.phone_input.setValidator(digit_validator)
        self.phone_input.textChanged.connect(self.validate_phone_input)
        phone_container.addWidget(self.phone_input)
        
        layout.addLayout(phone_container)
        
        # Send code button
        self.send_code_btn = QPushButton("Send Code")
        self.send_code_btn.setMinimumHeight(40)  # Make it bigger
        self.send_code_btn.setFont(QFont("Arial", 12, QFont.Bold))  # Bold font
        self.send_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.send_code_btn.clicked.connect(self.send_verification_code)
        self.send_code_btn.setEnabled(False)
        layout.addWidget(self.send_code_btn)
        
        # Verification section (initially hidden)
        self.verification_widget = QWidget()
        verification_layout = QVBoxLayout(self.verification_widget)
        verification_layout.setContentsMargins(0, 10, 0, 0)
        
        # Code label
        code_label = QLabel("Verification Code:")
        code_label.setFont(QFont("Arial", 10, QFont.Bold))
        verification_layout.addWidget(code_label)
        
        # Code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("6-digit code")
        self.code_input.setMaxLength(6)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setMinimumHeight(40)  # Make it bigger
        self.code_input.setFont(QFont("Arial", 14))  # Bigger font
        self.code_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #333333;
                border-radius: 5px;
                padding: 8px;
                color: #000000;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
        """)
        code_validator = QRegExpValidator(QRegExp(r'^\d{0,6}$'))
        self.code_input.setValidator(code_validator)
        self.code_input.textChanged.connect(self.validate_code_input)
        self.code_input.returnPressed.connect(self.verify_code)
        verification_layout.addWidget(self.code_input)
        
        # Verify button
        self.verify_btn = QPushButton("Verify & Enable 2FA")
        self.verify_btn.setMinimumHeight(45)  # Make it bigger
        self.verify_btn.setFont(QFont("Arial", 12, QFont.Bold))  # Bold font
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.verify_btn.clicked.connect(self.verify_code)
        self.verify_btn.setEnabled(False)
        verification_layout.addWidget(self.verify_btn)
        
        # Hide verification section initially
        self.verification_widget.hide()
        layout.addWidget(self.verification_widget)
        
        # Skip button
        skip_btn = QPushButton("Skip for Now")
        skip_btn.setMinimumHeight(35)
        skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 2px solid #cccccc;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999999;
            }
        """)
        skip_btn.clicked.connect(self.reject)
        layout.addWidget(skip_btn)
        
        # Focus on phone input
        self.phone_input.setFocus()
        
        # Check if Twilio is available
        if not TWILIO_AVAILABLE or not twilio_service.is_available():
            self.show_twilio_unavailable()
    
    def validate_phone_input(self):
        """Validate phone input."""
        text = self.phone_input.text()
        self.send_code_btn.setEnabled(len(text) == 10 and text.isdigit())
    
    def validate_code_input(self):
        """Validate code input."""
        text = self.code_input.text()
        self.verify_btn.setEnabled(len(text) == 6 and text.isdigit())
    
    def show_twilio_unavailable(self):
        """Show error for unavailable Twilio."""
        self.phone_input.setEnabled(False)
        self.send_code_btn.setEnabled(False)
        
        error_label = QLabel("SMS verification unavailable")
        error_label.setAlignment(Qt.AlignCenter)
        self.layout().insertWidget(2, error_label)
    
    def send_verification_code(self):
        """Send verification code."""
        phone_input = self.phone_input.text().strip()
        
        if not phone_input or len(phone_input) != 10:
            QMessageBox.warning(self, "Invalid Phone", "Please enter a valid 10-digit phone number.")
            return
        
        full_phone = f"+1{phone_input}"
        
        self.send_code_btn.setEnabled(False)
        self.send_code_btn.setText("Sending...")
        
        try:
            result = twilio_service.send_verification_code(full_phone)
            
            if result['success']:
                self.phone_number = full_phone
                self.phone_input.setEnabled(False)
                self.verification_widget.show()
                
                # Resize dialog to show verification section
                self.setFixedSize(400, 450)
                
                self.code_input.setFocus()
                
                self.send_code_btn.setText("Code Sent")
                QTimer.singleShot(60000, self.reset_send_button)
            else:
                QMessageBox.critical(self, "Error", f"Failed to send code: {result['message']}")
                self.reset_send_button()
                
        except Exception as e:
            logger.error(f"Error sending verification code: {e}")
            QMessageBox.critical(self, "Error", "Failed to send verification code.")
            self.reset_send_button()
    
    def reset_send_button(self):
        """Reset send button."""
        self.send_code_btn.setEnabled(True)
        self.send_code_btn.setText("Resend Code")
    
    def verify_code(self):
        """Verify the entered code."""
        code = self.code_input.text().strip()
        
        if not code or len(code) != 6:
            QMessageBox.warning(self, "Invalid Code", "Please enter a 6-digit verification code.")
            return
        
        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Verifying...")
        
        try:
            result = twilio_service.verify_code(self.phone_number, code)
            
            if result['success']:
                self.save_2fa_settings()
                QMessageBox.information(self, "Success", "Phone verification completed! Two-factor authentication is now enabled.")
                self.accept()
            else:
                QMessageBox.warning(self, "Invalid Code", f"Verification failed: {result['message']}")
                self.verify_btn.setEnabled(True)
                self.verify_btn.setText("Verify & Enable 2FA")
                self.code_input.clear()
                self.code_input.setFocus()
                
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            QMessageBox.critical(self, "Error", "Verification failed. Please try again.")
            self.verify_btn.setEnabled(True)
            self.verify_btn.setText("Verify & Enable 2FA")
    
    def save_2fa_settings(self):
        """Save 2FA settings to database."""
        if not self.user_id or not self.phone_number:
            return
        
        try:
            from ..database.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            if supabase:
                supabase.table('user_details').upsert({
                    'user_id': self.user_id,
                    'phone_number': self.phone_number,
                    'phone_verified': True,
                    'two_factor_enabled': True
                }).execute()
                
                logger.info(f"2FA enabled successfully for user {self.user_id}")
            else:
                logger.warning("Supabase client not available for saving 2FA settings")
                
        except Exception as e:
            logger.error(f"Error saving 2FA settings: {e}") 