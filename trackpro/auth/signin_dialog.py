"""Signin dialog for user authentication."""

from PyQt5.QtWidgets import (
    QLineEdit, QCheckBox, QFormLayout, QHBoxLayout, QPushButton, QLabel
)
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
import logging
import socket

logger = logging.getLogger(__name__)

class SigninDialog(BaseAuthDialog):
    """Dialog for user authentication."""
    
    def __init__(self, parent=None):
        """Initialize the signin dialog."""
        # Initialize fields
        self.remember_me_checkbox = None
        self.persistence_label = None
        self.offline_warning = None
        
        # Call parent constructor
        super().__init__(parent, title="Sign In")
        
        # Check offline status
        self.check_offline_status()
    
    def check_offline_status(self):
        """Check if we're in offline mode and update UI accordingly."""
        connected = supabase.check_connection()
        
        if not connected:
            # Create warning label if it doesn't exist
            if not self.offline_warning:
                self.offline_warning = QLabel("Warning: Unable to connect to server. You are in offline mode.")
                self.offline_warning.setStyleSheet("color: orange; font-weight: bold;")
                self.layout().insertWidget(1, self.offline_warning)  # Insert after title
    
    def setup_form_fields(self, form_layout):
        """Set up the form fields.
        
        Args:
            form_layout: The form layout to add fields to
        """
        # Add persistence message
        self.persistence_label = QLabel("Your session will remain active until you sign out,\neven if you close the application.")
        self.persistence_label.setStyleSheet("color: #27ae60; font-style: italic;")
        form_layout.addRow("", self.persistence_label)
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        form_layout.addRow("Email:", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_input)
        
        # Remember me checkbox
        self.remember_me_checkbox = QCheckBox("Remember me")
        self.remember_me_checkbox.setChecked(True)  # Default to checked
        form_layout.addRow("", self.remember_me_checkbox)
    
    def setup_buttons(self, button_layout):
        """Set up the dialog buttons."""
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # Spacer
        button_layout.addStretch()
        
        # Submit button
        self.submit_button = QPushButton("Sign In")
        self.submit_button.setDefault(True)
        self.submit_button.clicked.connect(self.submit)
        button_layout.addWidget(self.submit_button)
        
        # Enable offline button if needed
        if not supabase.check_connection():
            self.offline_button = QPushButton("Continue Offline")
            self.offline_button.clicked.connect(self.continue_offline)
            button_layout.addWidget(self.offline_button)
    
    def submit(self):
        """Submit the form and authenticate user."""
        if not self.validate_form():
            return
        
        # Get form values
        email = self.email_input.text()
        password = self.password_input.text()
        remember_me = self.remember_me_checkbox.isChecked()
        
        logger.info(f"Signing in user: {email}")
        
        # Verify connection one more time before trying
        if not supabase.check_connection():
            if self.show_network_error("Cannot connect to server. Continue in offline mode?"):
                return
            # User chose to try again, so continue with the signin attempt
        
        try:
            # Authenticate user
            response = supabase.sign_in(email, password)
            
            if response:
                logger.info(f"User {email} signed in successfully")
                
                # Note: Remember me is always true now since we save the session
                # but we keep the checkbox for user experience
                
                self.auth_completed.emit(True, response)
                self.accept()
            else:
                self.show_error("Authentication failed. Please check your credentials.")
                
        except ValueError as e:
            # This is likely a validation error like email confirmation required
            self.show_error(str(e))
            
            # If it's an email confirmation error, show additional help
            if "confirmation link" in str(e).lower() or "email not confirmed" in str(e).lower():
                self.show_resend_confirmation_dialog(email)
            
        except socket.gaierror:
            if self.show_network_error("DNS resolution failed. Check your internet connection."):
                return
                
        except ConnectionError:
            if self.show_network_error("Connection to server failed. Check your internet connection."):
                return
                
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            self.show_error(f"Error signing in: {str(e)}")
    
    def show_resend_confirmation_dialog(self, email):
        """Show dialog offering to resend confirmation email."""
        from PyQt5.QtWidgets import QMessageBox
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Email Confirmation Required")
        msg_box.setText("Your account requires email confirmation.")
        msg_box.setInformativeText(
            "Please check your email and follow the confirmation link.\n\n"
            "If you didn't receive the email, check your spam folder or try signing up again."
        )
        msg_box.addButton("OK", QMessageBox.AcceptRole)
        msg_box.exec_() 