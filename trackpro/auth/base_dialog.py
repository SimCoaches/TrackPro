"""Base authentication dialog."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from ..database.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

class BaseAuthDialog(QDialog):
    """Base class for authentication dialogs."""
    
    # Signal to emit when authentication is completed
    auth_completed = pyqtSignal(bool, object)
    
    def __init__(self, parent=None, title="Authentication"):
        """Initialize the dialog."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        # Set up form fields (to be overridden)
        self.email_input = None
        self.password_input = None
        
        # Set up UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Form layout
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)
        
        # Set up form fields
        self.setup_form_fields(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        # Set up buttons
        self.setup_buttons(button_layout)
        
        # Set tab order
        self.set_tab_order()
    
    def setup_form_fields(self, form_layout):
        """Set up the form fields."""
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        form_layout.addRow("Email:", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_input)
    
    def setup_buttons(self, button_layout):
        """Set up the dialog buttons."""
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        # Spacer
        button_layout.addStretch()
        
        # Submit button
        self.submit_button = QPushButton("Submit")
        self.submit_button.setDefault(True)
        self.submit_button.clicked.connect(self.submit)
        button_layout.addWidget(self.submit_button)
        
        # Enable offline button if needed
        if not supabase.check_connection():
            self.offline_button = QPushButton("Continue Offline")
            self.offline_button.clicked.connect(self.continue_offline)
            button_layout.addWidget(self.offline_button)
    
    def continue_offline(self):
        """Continue in offline mode."""
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("You will continue in offline mode.")
        msgBox.setInformativeText("You can sync your data later when you have a connection.")
        msgBox.setWindowTitle("Offline Mode")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msgBox.exec_()
        
        if result == QMessageBox.Ok:
            # Disable Supabase client
            supabase.disable()
            self.auth_completed.emit(False, None)
            self.accept()
    
    def set_tab_order(self):
        """Set the tab order for form fields."""
        if self.email_input and self.password_input:
            self.setTabOrder(self.email_input, self.password_input)
            self.setTabOrder(self.password_input, self.submit_button)
            self.setTabOrder(self.submit_button, self.cancel_button)
    
    def submit(self):
        """Submit the form (to be overridden)."""
        pass
    
    def validate_form(self):
        """Validate the form inputs."""
        # Email validation
        if not self.email_input.text():
            self.show_error("Email is required")
            return False
        
        # Password validation
        if not self.password_input.text():
            self.show_error("Password is required")
            return False
        
        return True
    
    def show_error(self, message):
        """Show an error message box."""
        logger.error(f"Auth error: {message}")
        QMessageBox.critical(self, "Error", message)
    
    def show_network_error(self, message):
        """Show a network error with offline option."""
        logger.error(f"Network error: {message}")
        
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(f"Network Error: {message}")
        msgBox.setInformativeText("Would you like to continue in offline mode?")
        msgBox.setWindowTitle("Network Error")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msgBox.exec_()
        
        if result == QMessageBox.Yes:
            # Disable Supabase client
            supabase.disable()
            self.auth_completed.emit(False, None)
            self.accept()
            return True
        
        return False 