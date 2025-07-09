"""SMS verification dialog for login 2FA."""

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from .twilio_service import twilio_service, TWILIO_AVAILABLE

logger = logging.getLogger(__name__)

class SMSVerificationDialog(QDialog):
    """Dialog for SMS verification during login."""
    
    def __init__(self, parent=None, phone_number=None):
        super().__init__(parent)
        self.phone_number = phone_number
        self.verification_successful = False
        self.setup_ui()
        
        # Send verification code automatically
        if self.phone_number:
            self.send_verification_code()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Verify Phone Number")
        self.setFixedSize(320, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Enter verification code")
        title.setFont(QFont("Segoe UI", 14))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Phone number info
        masked_phone = self.mask_phone_number(self.phone_number) if self.phone_number else "your phone"
        info_label = QLabel(f"Sent to {masked_phone}")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Code input
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("6-digit code")
        self.code_input.setMaxLength(6)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setFont(QFont("Segoe UI", 16))
        self.code_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ddd;
                border-radius: 6px;
                padding: 12px;
                font-size: 16px;
                text-align: center;
            }
            QLineEdit:focus {
                border-color: #4285f4;
                outline: none;
            }
        """)
        self.code_input.returnPressed.connect(self.verify_code)
        layout.addWidget(self.code_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Resend button
        self.resend_btn = QPushButton("Resend")
        self.resend_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px 16px;
                color: #4285f4;
            }
            QPushButton:hover {
                background: #f8f9fa;
            }
        """)
        self.resend_btn.clicked.connect(self.send_verification_code)
        
        # Verify button
        self.verify_btn = QPushButton("Verify")
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background: #4285f4;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3367d6;
            }
            QPushButton:disabled {
                background: #ccc;
            }
        """)
        self.verify_btn.clicked.connect(self.verify_code)
        
        button_layout.addWidget(self.resend_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.verify_btn)
        
        layout.addLayout(button_layout)
        
        # Focus on input
        self.code_input.setFocus()
        
        # Check if Twilio is available
        if not TWILIO_AVAILABLE or not twilio_service.is_available():
            self.show_twilio_unavailable()
    
    def mask_phone_number(self, phone_number):
        """Mask phone number for display."""
        if not phone_number or len(phone_number) < 6:
            return phone_number
        
        if phone_number.startswith('+'):
            return phone_number[:2] + '***' + phone_number[-4:]
        else:
            return '***' + phone_number[-4:]
    
    def show_twilio_unavailable(self):
        """Show message when Twilio is not available."""
        self.code_input.setEnabled(False)
        self.verify_btn.setEnabled(False)
        self.resend_btn.setEnabled(False)
        
        error_label = QLabel("SMS verification unavailable")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: #d93025; font-size: 12px;")
        self.layout().insertWidget(2, error_label)
    
    def send_verification_code(self):
        """Send verification code to the phone number."""
        if not self.phone_number:
            QMessageBox.warning(self, "Error", "No phone number available.")
            return
        
        self.resend_btn.setEnabled(False)
        self.resend_btn.setText("Sending...")
        
        try:
            result = twilio_service.send_verification_code(self.phone_number)
            
            if result['success']:
                # Re-enable after 30 seconds
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(30000, lambda: (
                    self.resend_btn.setEnabled(True),
                    self.resend_btn.setText("Resend")
                ))
            else:
                QMessageBox.critical(self, "Error", f"Failed to send code: {result['message']}")
                self.resend_btn.setEnabled(True)
                self.resend_btn.setText("Resend")
                
        except Exception as e:
            logger.error(f"Error sending verification code: {e}")
            QMessageBox.critical(self, "Error", "Failed to send code. Please try again.")
            self.resend_btn.setEnabled(True)
            self.resend_btn.setText("Resend")
    
    def verify_code(self):
        """Verify the entered code."""
        code = self.code_input.text().strip()
        if not code or len(code) != 6:
            QMessageBox.warning(self, "Invalid Code", "Please enter a 6-digit code.")
            self.code_input.setFocus()
            return
        
        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Verifying...")
        self.code_input.setEnabled(False)
        
        try:
            result = twilio_service.verify_code(self.phone_number, code)
            
            if result['success']:
                self.verification_successful = True
                self.accept()
            else:
                QMessageBox.warning(self, "Invalid Code", f"Verification failed: {result['message']}")
                self.verify_btn.setEnabled(True)
                self.verify_btn.setText("Verify")
                self.code_input.setEnabled(True)
                self.code_input.clear()
                self.code_input.setFocus()
                
        except Exception as e:
            logger.error(f"Error verifying code: {e}")
            QMessageBox.critical(self, "Error", "Verification failed. Please try again.")
            self.verify_btn.setEnabled(True)
            self.verify_btn.setText("Verify")
            self.code_input.setEnabled(True)
            self.code_input.setFocus() 