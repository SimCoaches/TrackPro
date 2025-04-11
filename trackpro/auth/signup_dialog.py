"""Signup dialog for creating a new user account."""

from PyQt5.QtWidgets import (
    QLineEdit, QLabel, QFormLayout, QMessageBox, QDateEdit, QCheckBox,
    QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QWidget
)
from PyQt5.QtCore import QDate, Qt, QSize
from PyQt5.QtGui import QIcon
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
import logging
import socket
import time
import os
from datetime import datetime, timedelta
from .oauth_handler import OAuthHandler

logger = logging.getLogger(__name__)

class SignupDialog(BaseAuthDialog):
    """Dialog for creating a new user account."""
    
    def __init__(self, parent=None, oauth_handler=None):
        """Initialize the signup dialog."""
        # Store the main OAuth handler
        self.oauth_handler = oauth_handler

        # Initialize fields
        self.display_name_input = None
        self.first_name_input = None
        self.last_name_input = None
        self.date_of_birth_input = None
        self.confirm_password_input = None
        self.offline_warning = None
        self.agree_terms_checkbox = None
        
        # Multi-step form control
        self.current_step = 1
        self.stacked_widget = None
        self.step1_form = None
        self.step2_form = None
        
        # Call parent constructor
        super().__init__(parent, title="Create Account")
        
        # Set larger size
        self.setMinimumWidth(450)
        
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
        # Create a stacked widget to hold both steps
        self.stacked_widget = QStackedWidget()
        form_layout.addRow(self.stacked_widget)
        
        # Create layouts for each step
        self.step1_form = QFormLayout()
        self.step2_form = QFormLayout()
        
        # Create widgets to hold each form
        step1_widget = QWidget()
        step2_widget = QWidget()
        step1_widget.setLayout(self.step1_form)
        step2_widget.setLayout(self.step2_form)
        
        # Add widgets to stacked widget
        self.stacked_widget.addWidget(step1_widget)
        self.stacked_widget.addWidget(step2_widget)
        
        # Set up step 1 fields (email & password)
        self.setup_step1_fields()
        
        # Set up step 2 fields (personal info)
        self.setup_step2_fields()
    
    def setup_step1_fields(self):
        """Set up fields for step 1 (email & password)."""
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.step1_form.addRow("Email: *", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.step1_form.addRow("Password: *", self.password_input)
        
        # Confirm password field
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.step1_form.addRow("Confirm Password: *", self.confirm_password_input)
    
    def setup_step2_fields(self):
        """Set up fields for step 2 (personal info)."""
        # Header for step 2
        step2_header = QLabel("Please complete your profile")
        step2_header.setStyleSheet("font-weight: bold; color: #2980b9;")
        self.step2_form.addRow("", step2_header)
        
        # Display name field (username)
        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Choose a username")
        self.step2_form.addRow("Username:", self.display_name_input)
        
        # First name field
        self.first_name_input = QLineEdit()
        self.step2_form.addRow("First Name:", self.first_name_input)
        
        # Last name field
        self.last_name_input = QLineEdit()
        self.step2_form.addRow("Last Name:", self.last_name_input)
        
        # Date of birth field
        self.date_of_birth_input = QDateEdit()
        self.date_of_birth_input.setDisplayFormat("yyyy-MM-dd")
        self.date_of_birth_input.setCalendarPopup(True)
        self.date_of_birth_input.setMaximumDate(QDate.currentDate())
        # Set default date to 18 years ago
        default_date = QDate.currentDate().addYears(-18)
        self.date_of_birth_input.setDate(default_date)
        self.step2_form.addRow("Date of Birth:", self.date_of_birth_input)
        
        # Terms checkbox
        self.agree_terms_checkbox = QCheckBox("I agree to the terms and conditions")
        self.step2_form.addRow("", self.agree_terms_checkbox)
    
    def setup_ui(self):
        """Set up the dialog UI with additional social login buttons."""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Form layout for signup
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)
        
        # Set up form fields in steps
        self.setup_form_fields(form_layout)
        
        # Add OR divider
        divider_layout = QHBoxLayout()
        divider_layout.addStretch()
        divider_layout.addWidget(QLabel("OR"))
        divider_layout.addStretch()
        main_layout.addLayout(divider_layout)
        
        # Add Sign Up With header
        header_label = QLabel("Sign Up With:")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(header_label)
        
        # Social login buttons layout
        social_layout = QHBoxLayout()
        social_layout.addStretch()
        
        # Get the icons directory path
        icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        
        # Google login button
        self.google_button = QPushButton()
        self.google_button.setToolTip("Sign up with Google")
        self.google_button.setFlat(True)
        self.google_button.setCursor(Qt.PointingHandCursor)
        self.google_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: transparent;
            }
            QPushButton:pressed {
                background-color: transparent;
            }
        """)
        
        # Set icon if the file exists
        google_icon_path = os.path.join(icons_dir, "google.png")
        if os.path.exists(google_icon_path):
            self.google_button.setIcon(QIcon(google_icon_path))
            self.google_button.setIconSize(QSize(45, 45))
            self.google_button.setFixedSize(QSize(45, 45))
        else:
            self.google_button.setText("Sign up with Google")
        self.google_button.clicked.connect(self.handle_google_signup)
        social_layout.addWidget(self.google_button)
        
        # Add spacing between buttons
        social_layout.addSpacing(40)
        
        # Discord login button
        self.discord_button = QPushButton()
        self.discord_button.setToolTip("Sign up with Discord")
        self.discord_button.setFlat(True)
        self.discord_button.setCursor(Qt.PointingHandCursor)
        self.discord_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: transparent;
            }
            QPushButton:pressed {
                background-color: transparent;
            }
        """)
        
        # Set icon if the file exists
        discord_icon_path = os.path.join(icons_dir, "discord.png")
        if os.path.exists(discord_icon_path):
            self.discord_button.setIcon(QIcon(discord_icon_path))
            self.discord_button.setIconSize(QSize(45, 45))
            self.discord_button.setFixedSize(QSize(45, 45))
        else:
            self.discord_button.setText("Sign up with Discord")
        self.discord_button.clicked.connect(self.handle_discord_signup)
        social_layout.addWidget(self.discord_button)
        
        social_layout.addStretch()
        main_layout.addLayout(social_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        # Set up buttons
        self.setup_buttons(button_layout)
        
        # Set tab order for accessible navigation
        self.set_tab_order()
        
        # Show the first step
        self.stacked_widget.setCurrentIndex(0)
        self.update_button_labels()
    
    def update_button_labels(self):
        """Update button labels based on current step."""
        if self.current_step == 1:
            self.submit_button.setText("Next")
        else:
            self.submit_button.setText("Create Account")
    
    def setup_buttons(self, button_layout):
        """Set up the dialog buttons."""
        # Call parent method first to get base buttons
        super().setup_buttons(button_layout)
        
        # Back button (only visible in step 2)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setVisible(False)  # Hidden initially
        # Insert back button after cancel button
        button_layout.insertWidget(1, self.back_button)
        
        # Update the submit button text
        self.submit_button.setText("Next")  # Will change to "Create Account" in step 2
        
        # Disconnect and reconnect submit button (safely)
        try:
            self.submit_button.clicked.disconnect()  # Disconnect from parent's method
        except TypeError:
            # Signal was not connected
            pass
            
        self.submit_button.clicked.connect(self.handle_submit_button)
    
    def handle_submit_button(self):
        """Handle the submit button click based on current step."""
        if self.current_step == 1:
            if self.validate_step1():
                self.go_to_step2()
        else:
            self.submit()
    
    def go_to_step2(self):
        """Switch to step 2 of the form."""
        self.current_step = 2
        self.stacked_widget.setCurrentIndex(1)
        self.back_button.setVisible(True)
        self.update_button_labels()
        
        # Focus on first field in step 2
        self.display_name_input.setFocus()
    
    def go_back(self):
        """Go back to the previous step."""
        self.current_step = 1
        self.stacked_widget.setCurrentIndex(0)
        self.back_button.setVisible(False)
        self.update_button_labels()
        
        # Focus on a field from step 1
        self.email_input.setFocus()
    
    def handle_google_signup(self):
        """Handle signup with Google."""
        # Disable button immediately to prevent double-clicks
        self.google_button.setEnabled(False)
        try:
            # Make sure we have the shared OAuth handler
            if not self.oauth_handler:
                logger.error("OAuth handler not provided to SignupDialog")
                self.show_error("Internal error: OAuth handler is missing.")
                return

            # Make sure we're connected
            if not supabase.check_connection():
                if self.show_network_error("Cannot connect to server."):
                    return
            
            # Connect to the existing handler's signal
            # Disconnect first to avoid duplicate connections if called multiple times
            try:
                self.oauth_handler.auth_completed.disconnect(self.on_oauth_completed)
            except TypeError:
                pass # Signal not connected
            self.oauth_handler.auth_completed.connect(self.on_oauth_completed)
            
            # Use the shared handler to start the Google OAuth flow
            logger.info("Using shared OAuth handler to start Google signup")
            response = self.oauth_handler.start_google_auth("http://localhost:3000")
            
            if response and hasattr(response, 'url'):
                # Open browser with the URL
                import webbrowser
                webbrowser.open(response.url)
                
                # Show message to the user
                self.show_info("A browser window will open for you to sign in with Google.\n\n"
                              "Once completed, you'll be redirected back to the application.")
            else:
                self.show_error("Failed to start Google authentication flow.")
                
        except Exception as e:
            logger.error(f"Google signup error: {e}")
            self.show_error(f"Error during Google signup: {str(e)}")
        finally:
            # Re-enable button will happen in on_oauth_completed
            pass
    
    def handle_discord_signup(self):
        """Handle signup with Discord."""
        # Disable button immediately
        self.discord_button.setEnabled(False)
        try:
            # Make sure we have the shared OAuth handler
            if not self.oauth_handler:
                logger.error("OAuth handler not provided to SignupDialog")
                self.show_error("Internal error: OAuth handler is missing.")
                return

            # Make sure we're connected
            if not supabase.check_connection():
                if self.show_network_error("Cannot connect to server."):
                    return

            # Connect to the existing handler's signal
            # Disconnect first to avoid duplicate connections if called multiple times
            try:
                self.oauth_handler.auth_completed.disconnect(self.on_oauth_completed)
            except TypeError:
                pass # Signal not connected
            self.oauth_handler.auth_completed.connect(self.on_oauth_completed)

            # Use the shared handler to start the Discord OAuth flow with PKCE
            # The server is already running, so we don't need to manage it here
            logger.info("Using shared OAuth handler to start Discord signup")
            response = self.oauth_handler.start_discord_auth("http://localhost:3000")

            if response and hasattr(response, 'url'):
                # Here you would typically open a web browser with the URL
                # For desktop apps, a custom URL handler would be needed
                import webbrowser
                webbrowser.open(response.url)
                
                # Show message to the user
                self.show_info("A browser window will open for you to sign in with Discord.\n\n"
                              "Once completed, you'll be redirected back to the application.")
            else:
                self.show_error("Failed to start Discord authentication flow.")
                
        except Exception as e:
            logger.error(f"Discord signup error: {e}", exc_info=True)
            self.show_error(f"Error during Discord signup: {str(e)}")
        finally:
            # Simplified fallback: Re-enable button if an error occurred *before* the signal handler is called.
            # The main re-enable happens in on_oauth_completed.
            # We cannot reliably check connection status here easily.
            pass
    
    def on_oauth_completed(self, success, response):
        """Handle OAuth authentication completion."""
        # Re-enable the buttons now that the flow is complete
        self.discord_button.setEnabled(True)
        self.google_button.setEnabled(True)

        logger.info(f"OAuth completed: success={success}")
        if success and response:
            # Authentication successful - emit our own signal
            logger.info("Discord authentication successful - emitting auth_completed signal")
            self.auth_completed.emit(True, response)
            self.accept()
        else:
            logger.error("OAuth authentication failed")
            self.show_error("Authentication failed. Please try again.")
    
    def set_tab_order(self):
        """Set the tab order for form fields."""
        # Step 1 tab order
        self.setTabOrder(self.email_input, self.password_input)
        self.setTabOrder(self.password_input, self.confirm_password_input)
        
        # Step 2 tab order
        self.setTabOrder(self.display_name_input, self.first_name_input)
        self.setTabOrder(self.first_name_input, self.last_name_input)
        self.setTabOrder(self.last_name_input, self.date_of_birth_input)
        self.setTabOrder(self.date_of_birth_input, self.agree_terms_checkbox)
        self.setTabOrder(self.agree_terms_checkbox, self.submit_button)
    
    def validate_step1(self):
        """Validate step 1 form inputs.
        
        Returns:
            bool: True if valid, False otherwise
        """
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
    
    def validate_step2(self):
        """Validate step 2 form inputs.
        
        Returns:
            bool: True if valid, False otherwise
        """
        # Display name validation
        if not self.display_name_input.text():
            self.show_error("Username is required")
            return False
        
        # First name validation
        if not self.first_name_input.text():
            self.show_error("First name is required")
            return False
        
        # Last name validation
        if not self.last_name_input.text():
            self.show_error("Last name is required")
            return False
        
        # Date of birth validation
        dob_date = self.date_of_birth_input.date()
        if dob_date > QDate.currentDate():
            self.show_error("Date of birth cannot be in the future")
            return False
        
        # Terms validation
        if not self.agree_terms_checkbox.isChecked():
            self.show_error("You must agree to the terms and conditions")
            return False
        
        return True
    
    def validate_form(self):
        """Validate all form inputs.
        
        Returns:
            bool: True if valid, False otherwise
        """
        # For step 2, we only need to validate the current step
        # Step 1 was already validated when moving to step 2
        return self.validate_step2()
    
    def submit(self):
        """Submit the form and create a new user."""
        if not self.validate_form():
            return
        
        # Get form values
        email = self.email_input.text()
        password = self.password_input.text()
        
        # Get user profile information
        username = self.display_name_input.text()
        first_name = self.first_name_input.text()
        last_name = self.last_name_input.text()
        date_of_birth = self.date_of_birth_input.date().toString("yyyy-MM-dd")
        
        # Prepare user metadata
        metadata = {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth
        }
        
        logger.info(f"Creating account for {email} with username {username} and name {first_name} {last_name}")
        
        # Verify connection one more time before trying
        if not supabase.check_connection():
            logger.error("Signup attempt while offline - no connection to Supabase")
            if self.show_network_error("Cannot connect to server. Continue in offline mode?"):
                return
            # User chose to try again, so continue with the signup attempt
        
        try:
            logger.debug(f"Submitting signup with metadata: {metadata}")
            
            # Set cursor to wait state
            self.setCursor(Qt.WaitCursor)
            
            # Attempt signup
            response = supabase.sign_up(email, password, metadata)
            
            # Restore cursor
            self.unsetCursor()
            
            if response:
                logger.info(f"Account created for {email}")
                
                # Show verification message
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("Account Created")
                msg_box.setText("Your account has been created!")
                msg_box.setInformativeText(
                    "<b>IMPORTANT:</b> Please check your email and click the verification link " 
                    "before attempting to sign in. This step is required.\n\n"
                    "If you don't receive the email within a few minutes, please check your spam folder."
                )
                # Show details about what to expect
                msg_box.setDetailedText(
                    "Email verification process:\n"
                    "1. Check your inbox for an email from TrackPro\n"
                    "2. Click the verification link in the email\n"
                    "3. Once verified, you can return to the app and log in\n\n"
                    "If you don't receive the email, you can try to sign in again and request a new verification email."
                )
                
                msg_box.exec_()
                
                # Close dialog
                self.reject()
            else:
                logger.error("Signup failed - response was None")
                self.show_error("Failed to create account. Please try again.")
                
        except ValueError as e:
            # Restore cursor
            self.unsetCursor()
            
            # This is likely a validation error with a specific message
            error_msg = str(e)
            logger.error(f"Signup validation error: {error_msg}")
            self.show_error(error_msg)
            
        except socket.gaierror as e:
            # Restore cursor
            self.unsetCursor()
            
            logger.error(f"DNS resolution failed during signup: {e}")
            if self.show_network_error("DNS resolution failed. Check your internet connection."):
                return
                
        except ConnectionError as e:
            # Restore cursor
            self.unsetCursor()
            
            logger.error(f"Connection error during signup: {e}")
            if self.show_network_error("Connection to server failed. Check your internet connection."):
                return
                
        except Exception as e:
            # Restore cursor
            self.unsetCursor()
            
            # Detailed logging of unexpected errors
            error_msg = str(e)
            logger.error(f"Unexpected error creating account: {error_msg}")
            logger.exception("Exception traceback:")
            
            # Show user-friendly error
            self.show_error(f"Error creating account: {error_msg}") 