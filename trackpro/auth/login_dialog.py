"""Login dialog for user authentication."""

from PyQt5.QtWidgets import (
    QLineEdit, QCheckBox, QFormLayout, QLabel
)
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
import logging
import socket

logger = logging.getLogger(__name__)

class LoginDialog(BaseAuthDialog):
    """Dialog for user login."""
    
    def __init__(self, parent=None):
        """Initialize the login dialog."""
        # Initialize fields
        self.remember_me_checkbox = None
        
        # Call parent constructor
        super().__init__(parent, title="Sign In")
    
    def setup_form_fields(self, form_layout):
        """Set up the form fields.
        
        Args:
            form_layout: The form layout to add fields to
        """
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
        form_layout.addRow("", self.remember_me_checkbox)
    
    def check_connection(self):
        """Check if we have a connection to the Supabase server.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return supabase.check_connection()
    
    def submit(self):
        """Submit the form and authenticate user."""
        if not self.validate_form():
            return
        
        # Get form values
        email = self.email_input.text()
        password = self.password_input.text()
        remember_me = self.remember_me_checkbox.isChecked()
        
        logger.info(f"Signing in user: {email}")
        
        # Check connection
        if not self.check_connection():
            if self.show_network_error("Cannot connect to server. Continue in offline mode?"):
                return
        
        try:
            # Authenticate user
            response = supabase.sign_in(email, password)
            
            if response:
                logger.info(f"User {email} signed in successfully")
                
                # Store the remember me preference
                if remember_me:
                    # TODO: Implement remember me functionality
                    pass
                
                self.auth_completed.emit(True, response)
                self.accept()
            else:
                self.show_error("Authentication failed. Please check your credentials.")
                
        except socket.gaierror:
            if self.show_network_error("DNS resolution failed. Check your internet connection."):
                return
                
        except ConnectionError:
            if self.show_network_error("Connection to server failed. Check your internet connection."):
                return
                
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            self.show_error(f"Error signing in: {str(e)}") 