"""Signup dialog for creating a new user account."""

from PyQt5.QtWidgets import (
    QLineEdit, QLabel, QFormLayout, QMessageBox
)
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
import logging
import socket

logger = logging.getLogger(__name__)

class SignupDialog(BaseAuthDialog):
    """Dialog for creating a new user account."""
    
    def __init__(self, parent=None):
        """Initialize the signup dialog."""
        # Initialize fields
        self.display_name_input = None
        self.confirm_password_input = None
        self.offline_warning = None
        
        # Call parent constructor
        super().__init__(parent, title="Create Account")
        
        # Add offline warning if needed
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
        # Display name field
        self.display_name_input = QLineEdit()
        form_layout.addRow("Display Name:", self.display_name_input)
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        form_layout.addRow("Email:", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_input)
        
        # Confirm password field
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Confirm Password:", self.confirm_password_input)
    
    def set_tab_order(self):
        """Set the tab order for form fields."""
        self.setTabOrder(self.display_name_input, self.email_input)
        self.setTabOrder(self.email_input, self.password_input)
        self.setTabOrder(self.password_input, self.confirm_password_input)
        self.setTabOrder(self.confirm_password_input, self.submit_button)
    
    def validate_form(self):
        """Validate form inputs.
        
        Returns:
            bool: True if valid, False otherwise
        """
        # Display name validation
        if not self.display_name_input.text():
            self.show_error("Display name is required")
            return False
        
        # Email validation
        if not self.email_input.text() or '@' not in self.email_input.text():
            self.show_error("Please enter a valid email address")
            return False
        
        # Password validation
        if not self.password_input.text():
            self.show_error("Password is required")
            return False
        
        if len(self.password_input.text()) < 6:
            self.show_error("Password must be at least 6 characters long")
            return False
        
        # Confirm password validation
        if self.password_input.text() != self.confirm_password_input.text():
            self.show_error("Passwords do not match")
            return False
        
        return True
    
    def submit(self):
        """Submit the form and create a new user."""
        if not self.validate_form():
            return
        
        # Get form values
        display_name = self.display_name_input.text()
        email = self.email_input.text()
        password = self.password_input.text()
        
        logger.info(f"Creating account for {email}")
        
        # Verify connection one more time before trying
        if not supabase.check_connection():
            if self.show_network_error("Cannot connect to server. Continue in offline mode?"):
                return
            # User chose to try again, so continue with the signup attempt
        
        try:
            # Create user
            response = supabase.sign_up(email, password)
            
            if response:
                logger.info(f"Account created for {email}")
                
                # Check if email confirmation is required
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Account Created")
                
                # Determine if confirmation email was sent
                if hasattr(response, 'user') and response.user and response.user.email_confirmed_at is None:
                    # Email not confirmed yet, likely needs confirmation
                    msg_box.setText("Your account has been created!")
                    msg_box.setInformativeText(
                        "Please check your email and click the confirmation link "
                        "before signing in. If you don't receive the email within "
                        "a few minutes, please check your spam folder."
                    )
                else:
                    # Account created and no confirmation needed
                    msg_box.setText("Your account has been created successfully!")
                    msg_box.setInformativeText("You can now sign in with your credentials.")
                
                msg_box.exec_()
                
                self.auth_completed.emit(True, response)
                self.accept()
            else:
                self.show_error("Failed to create account. Please try again.")
                
        except ValueError as e:
            # This is likely a validation error from our client
            self.show_error(str(e))
            
        except socket.gaierror:
            if self.show_network_error("DNS resolution failed. Check your internet connection."):
                return
                
        except ConnectionError:
            if self.show_network_error("Connection to server failed. Check your internet connection."):
                return
                
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            self.show_error(f"Error creating account: {str(e)}") 