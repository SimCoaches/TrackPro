"""Login dialog for user authentication."""

from PyQt6.QtWidgets import (
    QLineEdit, QCheckBox, QFormLayout, QLabel, 
    QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QWidget, QSizePolicy, QInputDialog, QDialog, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QFont
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
from ..config import config
from ..social import enhanced_user_manager
import logging
import socket
import webbrowser
import os

from .terms_handler import check_and_prompt_for_terms

# Add Twilio import for 2FA
try:
    from twilio.rest import Client as TwilioClient
    from .twilio_service import twilio_service
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None
    twilio_service = None

logger = logging.getLogger(__name__)


class ForgotPasswordDialog(QDialog):
    """Simple dialog to collect email for password reset."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        # Initialize UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Reset Your Password")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Instructions
        instructions = QLabel("Enter your email address and we'll send you a link to reset your password.")
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("margin-bottom: 15px; color: #666;")
        layout.addWidget(instructions)
        
        # Email input
        form_layout = QFormLayout()
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        self.email_input.setStyleSheet("""
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
                color: #ddd;
            }
            QLineEdit:focus {
                border: 1px solid #77aaff;
                background-color: #4a4a4a;
            }
        """)
        form_layout.addRow("Email:", self.email_input)
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.send_button = QPushButton("Send Reset Email")
        self.send_button.clicked.connect(self.send_reset_email)
        self.send_button.setDefault(True)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
        """)
        button_layout.addWidget(self.send_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Set focus to email input
        self.email_input.setFocus()
        
        # Allow Enter key to submit
        self.email_input.returnPressed.connect(self.send_reset_email)
    
    def send_reset_email(self):
        """Send the password reset email."""
        email = self.email_input.text().strip()
        
        if not email:
            QMessageBox.warning(self, "Email Required", "Please enter your email address.")
            return
        
        # Basic email validation
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return
        
        # Disable the send button to prevent multiple clicks
        self.send_button.setEnabled(False)
        self.send_button.setText("Sending...")
        
        try:
            # Get the OAuth port from the parent window (main app)
            oauth_port = 3000
            try:
                from PyQt6.QtWidgets import QApplication
                for widget in QApplication.topLevelWidgets():
                    if hasattr(widget, 'oauth_port') and widget.oauth_port:
                        oauth_port = widget.oauth_port
                        break
            except:
                pass
            
            # Use localhost for the redirect URL since it will be handled by our callback server
            redirect_url = f"http://localhost:{oauth_port}/auth/reset-password"
            
            # Send the password reset email with our callback URL
            result = supabase.reset_password_for_email(email, redirect_url)
            
            if result.get("success"):
                QMessageBox.information(self, "Reset Email Sent", 
                    f"A password reset email has been sent to {email}.\n\n"
                    "Please check your email and click the link to reset your password.\n\n"
                    "Note: If you're checking email on your phone, please copy the link and open it on this computer where TrackPro is running.")
                self.accept()
            else:
                error_msg = result.get("error", "Unknown error occurred")
                QMessageBox.warning(self, "Reset Failed", f"Failed to send reset email:\n\n{error_msg}")
                
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n\n{str(e)}")
        finally:
            # Re-enable the send button
            self.send_button.setEnabled(True)
            self.send_button.setText("Send Reset Email")


class PasswordResetCompletionDialog(QDialog):
    """Dialog for completing password reset after clicking email link."""
    
    def __init__(self, parent=None, access_token=None, refresh_token=None):
        super().__init__(parent)
        self.setWindowTitle("Complete Password Reset")
        self.setModal(True)
        self.setFixedSize(450, 300)
        
        self.access_token = access_token
        self.refresh_token = refresh_token
        
        # Initialize UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Set New Password")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title_label)
        
        # Instructions
        instructions = QLabel("Please enter your new password below.")
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("margin-bottom: 20px; color: #666;")
        layout.addWidget(instructions)
        
        # Form layout
        form_layout = QFormLayout()
        
        # New password input
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("Enter new password")
        self.new_password_input.setStyleSheet("""
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 10px;
                border-radius: 4px;
                color: #ddd;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #77aaff;
                background-color: #4a4a4a;
            }
        """)
        form_layout.addRow("New Password:", self.new_password_input)
        
        # Confirm password input
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm new password")
        self.confirm_password_input.setStyleSheet("""
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 10px;
                border-radius: 4px;
                color: #ddd;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #77aaff;
                background-color: #4a4a4a;
            }
        """)
        form_layout.addRow("Confirm Password:", self.confirm_password_input)
        
        layout.addLayout(form_layout)
        
        # Password requirements
        requirements = QLabel("Password must be at least 8 characters long.")
        requirements.setStyleSheet("color: #999; font-size: 12px; margin: 10px 0;")
        requirements.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(requirements)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.reset_button = QPushButton("Reset Password")
        self.reset_button.clicked.connect(self.reset_password)
        self.reset_button.setDefault(True)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Set focus to password input
        self.new_password_input.setFocus()
        
        # Allow Enter key to submit
        self.new_password_input.returnPressed.connect(self.reset_password)
        self.confirm_password_input.returnPressed.connect(self.reset_password)
    
    def reset_password(self):
        """Reset the user's password."""
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Validate inputs
        if not new_password:
            QMessageBox.warning(self, "Password Required", "Please enter a new password.")
            return
        
        if len(new_password) < 8:
            QMessageBox.warning(self, "Password Too Short", "Password must be at least 8 characters long.")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "Passwords Don't Match", "The passwords you entered don't match. Please try again.")
            return
        
        # Disable the reset button to prevent multiple clicks
        self.reset_button.setEnabled(False)
        self.reset_button.setText("Resetting...")
        
        try:
            # Set the session using the tokens from the email link
            if self.access_token and self.refresh_token:
                # Set the session in Supabase client
                supabase.client.auth.set_session(self.access_token, self.refresh_token)
                
                # Update the password
                response = supabase.client.auth.update_user({
                    "password": new_password
                })
                
                if response and response.user:
                    QMessageBox.information(self, "Password Reset Successful", 
                        "Your password has been reset successfully!\n\n"
                        "You can now log in with your new password.")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Reset Failed", "Failed to reset password. Please try again.")
            else:
                QMessageBox.warning(self, "Invalid Reset Link", 
                    "This reset link is invalid or has expired. Please request a new password reset email.")
                
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            error_msg = str(e)
            if "expired" in error_msg.lower() or "invalid" in error_msg.lower():
                QMessageBox.warning(self, "Reset Link Expired", 
                    "This password reset link has expired. Please request a new password reset email.")
            else:
                QMessageBox.critical(self, "Error", f"An error occurred while resetting your password:\n\n{error_msg}")
        finally:
            # Re-enable the reset button
            self.reset_button.setEnabled(True)
            self.reset_button.setText("Reset Password")


class LoginDialog(BaseAuthDialog):
    """Dialog for user login."""
    
    def __init__(self, parent=None, oauth_handler=None):
        """Initialize the login dialog."""
        # Store the main OAuth handler
        self.oauth_handler = oauth_handler
        
        # Initialize fields
        self.remember_me_checkbox = None
        
        # Track which provider is being used
        self.pending_provider = None
        
        # Call parent constructor
        super().__init__(parent, title="Sign In")
        
        # Set minimum width - adjust as needed for two columns
        self.setMinimumWidth(700) # Increased width for two columns
        self.setMinimumHeight(400) # Added minimum height
    
    def setup_ui(self):
        """Set up the dialog UI with a two-column layout."""
        # Main horizontal layout for two columns
        main_h_layout = QHBoxLayout()
        self.setLayout(main_h_layout)
        
        # --- Left Column (Login Form) ---
        left_column_widget = QWidget()
        left_column_layout = QVBoxLayout(left_column_widget)
        left_column_layout.setContentsMargins(10, 10, 20, 10) # Add some margin
        
        # Add Heading
        heading_label = QLabel("TrackPro")
        heading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 5px;")
        left_column_layout.addWidget(heading_label)
        
        # Add Subheading
        subheading_label = QLabel("Making Drivers Faster One Lap At A Time")
        subheading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subheading_label.setStyleSheet("font-size: 12px; color: #bbb; margin-bottom: 20px;")
        left_column_layout.addWidget(subheading_label)
        
        # Form layout for traditional login
        form_layout = QFormLayout()
        left_column_layout.addLayout(form_layout)
        
        # Set up traditional form fields
        self.setup_form_fields(form_layout)
        
        # Add some vertical spacing
        left_column_layout.addSpacing(15)
        
        # Add OR divider
        divider_layout = QHBoxLayout()
        divider_layout.addStretch()
        divider_layout.addWidget(QLabel("OR"))
        divider_layout.addStretch()
        left_column_layout.addLayout(divider_layout)
        
        # Add Sign In With header
        header_label = QLabel("Sign In With:")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("font-weight: bold; margin-top: 10px; margin-bottom: 5px;")
        left_column_layout.addWidget(header_label)
        
        # Social login buttons
        social_layout = QHBoxLayout()
        social_layout.addStretch() # Center buttons
        
        # Get the icons directory path
        icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        
        # Google login button
        google_button = QPushButton()
        google_button.setToolTip("Sign in with Google")
        # Set icon if the file exists
        from trackpro.utils.resource_utils import get_resource_path
        google_icon_path = get_resource_path("trackpro/resources/icons/google.png")
        if os.path.exists(google_icon_path):
            google_button.setIcon(QIcon(google_icon_path))
            google_button.setIconSize(google_button.sizeHint() * 1.5) # Make icon larger
            google_button.setFixedSize(google_button.iconSize() * 1.2) # Adjust button size
        else:
            google_button.setText("Google") # Shorter text
        google_button.clicked.connect(self.handle_google_login)
        social_layout.addWidget(google_button)
        
        social_layout.addSpacing(20) # Add spacing between social buttons
        
        # Discord login button
        self.discord_button = QPushButton()
        self.discord_button.setToolTip("Sign in with Discord")
        # Set icon if the file exists
        discord_icon_path = get_resource_path("trackpro/resources/icons/discord.png")
        if os.path.exists(discord_icon_path):
            self.discord_button.setIcon(QIcon(discord_icon_path))
            self.discord_button.setIconSize(self.discord_button.sizeHint() * 1.5) # Make icon larger
            self.discord_button.setFixedSize(self.discord_button.iconSize() * 1.2) # Adjust button size
        else:
            self.discord_button.setText("Discord") # Shorter text
        self.discord_button.clicked.connect(self.handle_discord_login)
        social_layout.addWidget(self.discord_button)
        
        social_layout.addStretch() # Center buttons
        left_column_layout.addLayout(social_layout)
        
        # Add stretch to push buttons to the bottom
        left_column_layout.addStretch(1)
        
        # Button layout (Cancel/Submit)
        button_layout = QHBoxLayout()
        # Set up buttons (calls parent method)
        self.setup_buttons(button_layout)
        left_column_layout.addLayout(button_layout)
        
        # Add left column widget to main layout
        main_h_layout.addWidget(left_column_widget, 1) # Assign stretch factor 1
        
        # --- Right Column (Image) ---
        right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(right_column_widget)
        right_column_layout.setContentsMargins(20, 10, 10, 10) # Add some margin
        right_column_widget.setStyleSheet("background-color: #3a3a3a; border-radius: 5px;") # Simple background for placeholder
        
        # Placeholder for image
        image_label = QLabel("Login Image Placeholder")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        image_label.setStyleSheet("color: #ccc; font-size: 16px;")
        
        # Optional: Load an actual image if available
        image_path = get_resource_path("trackpro/resources/images/login_image.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            image_label.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            image_label.setText("Image not found")
        
        right_column_layout.addWidget(image_label)
        
        # Add right column widget to main layout
        main_h_layout.addWidget(right_column_widget, 1) # Assign stretch factor 1
        
        # Set tab order (consider how it flows across columns if needed)
        self.set_tab_order()
    
    def show_forgot_password_dialog(self):
        """Show the forgot password dialog."""
        # Connect to the password reset signal before showing the dialog
        if self.oauth_handler:
            try:
                self.oauth_handler.password_reset_required.disconnect(self.on_password_reset_required)
            except TypeError:
                pass # Signal not connected
            self.oauth_handler.password_reset_required.connect(self.on_password_reset_required)
            logger.info("Connected to password reset signal for forgot password flow")
        
        dialog = ForgotPasswordDialog(self)
        dialog.exec()
    
    def setup_form_fields(self, form_layout):
        """Set up the form fields.
        
        Args:
            form_layout: The form layout to add fields to
        """
        # Common style for text inputs
        input_style = """
            QLineEdit {
                background-color: #444;
                border: 1px solid #555;
                padding: 6px;
                border-radius: 4px;
                color: #ddd; /* Text color */
            }
            QLineEdit:focus {
                border: 1px solid #77aaff; /* Highlight border on focus */
                background-color: #4a4a4a;
            }
        """
        
        # Email field
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setStyleSheet(input_style)
        form_layout.addRow("Email:", self.email_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(input_style)
        form_layout.addRow("Password:", self.password_input)
        
        # Remember me checkbox - checked by default for persistent sessions
        self.remember_me_checkbox = QCheckBox("Remember me")
        self.remember_me_checkbox.setChecked(True)  # Default to keeping users logged in
        form_layout.addRow("", self.remember_me_checkbox)
        
        # Forgot password link
        self.forgot_password_link = QPushButton("Forgot Password?")
        self.forgot_password_link.setFlat(True)
        self.forgot_password_link.setStyleSheet("""
            QPushButton {
                border: none;
                color: #77aaff;
                text-decoration: underline;
                text-align: left;
                padding: 2px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #99ccff;
            }
        """)
        self.forgot_password_link.clicked.connect(self.show_forgot_password_dialog)
        form_layout.addRow("", self.forgot_password_link)
    
    def handle_google_login(self):
        """Handle login with Google."""
        try:
            # Set the pending provider
            self.pending_provider = "google"
            
            # Check if OAuth is available and get the port
            oauth_port = getattr(self.oauth_handler, 'oauth_port', 3000) if self.oauth_handler else 3000
            
            # Check if the callback server is actually running
            if not self.oauth_handler or not hasattr(self.oauth_handler, 'oauth_port'):
                self._show_oauth_fallback_error("Google")
                return
            
            # Make sure we're connected
            if not self.check_connection():
                if self.show_network_error("Cannot connect to server to authenticate with Google."):
                    return
            
            # Open Google OAuth flow
            redirect_url = f"http://localhost:{oauth_port}"
            logger.info(f"Starting Google OAuth with redirect URL: {redirect_url}")
            response = supabase.sign_in_with_google(redirect_url)
            if response and hasattr(response, 'url'):
                # Open browser with the URL
                webbrowser.open(response.url)
                
                # Connect to the oauth handler's signals if available
                if self.oauth_handler:
                    # Disconnect first to avoid duplicate connections if called multiple times
                    try:
                        self.oauth_handler.auth_completed.disconnect(self.on_oauth_completed)
                    except TypeError:
                        pass # Signal not connected
                    try:
                        self.oauth_handler.password_reset_required.disconnect(self.on_password_reset_required)
                    except TypeError:
                        pass # Signal not connected
                    
                    self.oauth_handler.auth_completed.connect(self.on_oauth_completed)
                    self.oauth_handler.password_reset_required.connect(self.on_password_reset_required)
                
                # Show message to the user
                self.show_info("A browser window will open for you to sign in with Google.\n\n"
                              "Once completed, you'll be redirected back to the application.")
                
                # Set up a timer to check for authentication status periodically
                # This is needed because Google auth uses a different callback mechanism
                if not hasattr(self, '_google_auth_timer'):
                    self._google_auth_timer = QTimer()
                    self._google_auth_timer.timeout.connect(self.check_google_auth_status)
                    self._google_auth_timer.setInterval(1000)  # Check every second
                
                # Start the timer
                self._google_auth_timer.start()
                logger.info("Started timer to poll for Google authentication status")
            else:
                self.show_error("Failed to start Google authentication flow.")
                
        except Exception as e:
            logger.error(f"Google login error: {e}")
            self.show_error(f"Error during Google login: {str(e)}")
    
    def _show_oauth_fallback_error(self, provider_name):
        """Show enhanced error message with fallback instructions for OAuth failures."""
        error_message = f"""
{provider_name} login is currently unavailable due to Windows security restrictions.

🔒 This happens when Windows blocks the OAuth authentication server.

✅ QUICK SOLUTIONS:

1. Use Email/Password Login (recommended)
   - Works reliably without security issues
   - Provides the same features as {provider_name} login

2. Run TrackPro as Administrator
   - Close TrackPro completely
   - Right-click TrackPro executable
   - Select "Run as administrator"

3. Add TrackPro to Windows Defender exclusions
   - This prevents Windows from blocking the authentication

💡 TIP: Email/password login is often more reliable for installed applications!
        """
        
        # Create a more detailed message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"{provider_name} Login Unavailable")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(f"{provider_name} login is currently unavailable.")
        msg_box.setDetailedText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    # Make sure to stop the timer when the dialog is closed or destroyed
    def closeEvent(self, event):
        """Override close event to clean up resources."""
        if hasattr(self, '_google_auth_timer') and self._google_auth_timer.isActive():
            logger.info("Stopping Google auth timer during dialog close")
            self._google_auth_timer.stop()
        super().closeEvent(event)
    
    def check_google_auth_status(self):
        """Periodically check if the user has completed Google authentication."""
        try:
            # Check if user is authenticated now
            if supabase.is_authenticated():
                logger.info("Google authentication detected - user is now authenticated")
                
                # Get user info
                user_response = supabase.get_user()
                
                # Check 2FA before proceeding
                user_email = user_response.user.email if hasattr(user_response.user, 'email') else 'User'
                if not self.check_and_handle_2fa(user_response.user.id, user_email):
                    # 2FA failed, logout and return
                    try:
                        supabase.client.auth.sign_out()
                    except:
                        pass
                    # Stop the timer
                    if hasattr(self, '_google_auth_timer'):
                        self._google_auth_timer.stop()
                    return
                
                # Check profile completeness
                self.check_profile_completeness_and_redirect(user_response.user.id)
                
                # Get remember_me preference if checkbox exists
                remember_me = self.remember_me_checkbox.isChecked() if hasattr(self, 'remember_me_checkbox') and self.remember_me_checkbox else True
                
                # Ensure session is saved
                if hasattr(supabase, '_save_session') and user_response:
                    logger.info(f"Explicitly saving Google session with remember_me={remember_me}")
                    supabase._save_session(user_response, remember_me=remember_me)
                
                # Force the parent window to update if we can
                try:
                    parent = self.parent()
                    if parent:
                        from PyQt6.QtWidgets import QApplication
                        logger.info("Forcing parent window to update authentication state after Google login")
                        QApplication.processEvents()
                        
                        # If the parent has update_auth_state method, call it directly
                        if hasattr(parent, 'update_auth_state'):
                            logger.info("Parent has update_auth_state method, calling it")
                            parent.update_auth_state()
                            QApplication.processEvents()
                except Exception as e:
                    logger.error(f"Error updating parent window: {e}")
                
                # Show confirmation message and close dialog
                QMessageBox.information(self, "Login Successful", 
                                      f"You are now logged in as {user_email}")
                self.accept()
                
                # Emit our own signal for consistency
                self.auth_completed.emit(True, user_response)
                
                # Stop the timer
                if hasattr(self, '_google_auth_timer'):
                    self._google_auth_timer.stop()
                return
            
            # If we're still showing and the timer exists but no auth yet, keep checking
            if not self.isHidden() and hasattr(self, '_google_auth_timer'):
                # Still waiting for auth, keep timer running
                pass
                
        except Exception as e:
            logger.error(f"Error checking Google auth status: {e}")
            # Don't stop the timer on error, just keep trying
    
    def handle_discord_login(self):
        """Handle login with Discord."""
        # Disable button immediately to prevent double-clicks
        self.discord_button.setEnabled(False)
        try:
            # Set the pending provider
            self.pending_provider = "discord"
            
            # Make sure we have the shared OAuth handler
            if not self.oauth_handler:
                logger.error("OAuth handler not provided to LoginDialog")
                self.show_error("Internal error: OAuth handler is missing.")
                self.discord_button.setEnabled(True)
                return

            # Check if OAuth is available and get the port
            oauth_port = getattr(self.oauth_handler, 'oauth_port', 3000) if self.oauth_handler else 3000
            
            # Check if the callback server is actually running
            if not self.oauth_handler or not hasattr(self.oauth_handler, 'oauth_port'):
                self.discord_button.setEnabled(True)
                self._show_oauth_fallback_error("Discord")
                return

            # Make sure we're connected
            if not self.check_connection():
                self.discord_button.setEnabled(True)
                if self.show_network_error("Cannot connect to server to authenticate with Discord."):
                    return

            # Connect to the existing handler's signals
            # Disconnect first to avoid duplicate connections if called multiple times
            try:
                self.oauth_handler.auth_completed.disconnect(self.on_oauth_completed)
            except TypeError:
                pass # Signal not connected
            try:
                self.oauth_handler.password_reset_required.disconnect(self.on_password_reset_required)
            except TypeError:
                pass # Signal not connected
            
            self.oauth_handler.auth_completed.connect(self.on_oauth_completed)
            self.oauth_handler.password_reset_required.connect(self.on_password_reset_required)

            # Use the shared handler to start the Discord OAuth flow with PKCE
            # The server is already running, so we don't need to manage it here
            logger.info(f"Using shared OAuth handler to start Discord login on port {oauth_port}")
            try:
                response = self.oauth_handler.start_discord_auth(f"http://localhost:{oauth_port}")

                if response and hasattr(response, 'url'):
                    # Open browser with the URL
                    try:
                        webbrowser.open(response.url)
                        
                        # Show message to the user
                        self.show_info("A browser window will open for you to sign in with Discord.\n\n"
                                      "Once completed, you'll be redirected back to the application.")
                    except Exception as browser_e:
                        logger.error(f"Error opening browser: {browser_e}")
                        self.discord_button.setEnabled(True)
                        self.show_error(f"Could not open web browser: {str(browser_e)}\n\nPlease check your default browser settings.")
                else:
                    self.discord_button.setEnabled(True)
                    self.show_error("Failed to start Discord authentication flow. The response did not contain a valid authorization URL.")
            except ValueError as ve:
                # Specific error messages from the OAuth handler
                logger.error(f"Discord auth ValueError: {ve}")
                self.discord_button.setEnabled(True)
                self.show_error(str(ve))
            except Exception as auth_e:
                # Generic errors from the OAuth process
                logger.error(f"Discord auth error: {auth_e}", exc_info=True)
                self.discord_button.setEnabled(True)
                self.show_error(f"Discord authentication error: {str(auth_e)}")
                
        except Exception as e:
            logger.error(f"Discord login error: {e}", exc_info=True)
            self.discord_button.setEnabled(True)
            self.show_error(f"Error during Discord login: {str(e)}")
            
        # Don't re-enable button here, it will be re-enabled in on_oauth_completed after the flow is complete
        # If there was an error before the OAuth flow started, we've already re-enabled it above
    
    def on_oauth_completed(self, success, response):
        """Handle OAuth authentication completion."""
        # Re-enable any disabled buttons
        if hasattr(self, 'discord_button'):
            self.discord_button.setEnabled(True)
        
        # Stop Google auth timer if running
        if hasattr(self, '_google_auth_timer') and self._google_auth_timer.isActive():
            logger.info("Stopping Google auth timer due to OAuth completion")
            self._google_auth_timer.stop()

        logger.info(f"OAuth completed: success={success}, provider={getattr(response, 'provider', 'unknown') if response else 'none'}")
        if success and response:
            # Determine user email for the confirmation message
            user_email = "User"
            if hasattr(response, 'user') and hasattr(response.user, 'email'):
                user_email = response.user.email
            elif hasattr(response, 'email'):
                user_email = response.email
            
            # Check 2FA before proceeding
            user_id = response.user.id if hasattr(response, 'user') and hasattr(response.user, 'id') else None
            if user_id and not self.check_and_handle_2fa(user_id, user_email):
                # 2FA failed, logout and return
                try:
                    supabase.client.auth.sign_out()
                except:
                    pass
                return
            
            # Check profile completeness
            if user_id:
                self.check_profile_completeness_and_redirect(user_id)
            
            # Get remember_me preference if checkbox exists
            remember_me = self.remember_me_checkbox.isChecked() if hasattr(self, 'remember_me_checkbox') and self.remember_me_checkbox else True
            
            # Authentication successful - emit our own signal
            logger.info("Authentication successful - emitting auth_completed signal")
            self.auth_completed.emit(True, response)
            
            # Force save the session
            if hasattr(supabase, '_save_session'):
                logger.info(f"Explicitly saving session after OAuth completion with remember_me={remember_me}")
                supabase._save_session(response, remember_me=remember_me)
            
            # Force the parent window to update if we can
            try:
                parent = self.parent()
                if parent:
                    from PyQt6.QtWidgets import QApplication
                    logger.info("Forcing parent window to update authentication state")
                    QApplication.processEvents()
                    
                    # If the parent has update_auth_state method, call it directly
                    if hasattr(parent, 'update_auth_state'):
                        logger.info("Parent has update_auth_state method, calling it")
                        parent.update_auth_state()
                        QApplication.processEvents()
            except Exception as e:
                logger.error(f"Error updating parent window: {e}")
            
            # Close this dialog
            self.accept()
            
            # Show a brief confirmation
            QMessageBox.information(self, "Login Successful", 
                                   f"You are now logged in as {user_email}")
        else:
            logger.error("OAuth authentication failed")
            # Determine which provider failed
            provider = "authentication"
            if hasattr(self, 'pending_provider'):
                provider = self.pending_provider
            
            self.show_error(f"{provider.capitalize()} authentication failed. Please try again.")
    
    def on_password_reset_required(self, access_token, refresh_token):
        """Handle password reset completion - this follows the exact same pattern as OAuth."""
        logger.info(f"Password reset signal received - access_token: {access_token[:20]}...")
        
        try:
            # Create and show the password reset dialog - this runs on the main thread since it's a signal handler
            dialog = PasswordResetCompletionDialog(
                parent=self,
                access_token=access_token,
                refresh_token=refresh_token
            )
            
            logger.info("Showing password reset completion dialog...")
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                logger.info("Password reset completed successfully")
                # Show success message
                QMessageBox.information(self, "Password Reset Complete", 
                    "Your password has been reset successfully!\n\n"
                    "You can now log in with your new password.")
                
                # Optionally close the login dialog since password was reset
                # self.accept()
            else:
                logger.info("Password reset dialog was cancelled")
                
        except Exception as e:
            logger.error(f"Error showing password reset dialog: {e}", exc_info=True)
            QMessageBox.warning(self, "Password Reset Error", 
                f"An error occurred while processing your password reset:\n\n{str(e)}\n\n"
                "Please try requesting a new password reset email.")
    
    def check_connection(self):
        """Check if we have a connection to the Supabase server.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return supabase.check_connection()
    
    def check_and_handle_2fa(self, user_id, user_email="User"):
        """Check if user has 2FA enabled and handle the verification process.
        This includes fallback behavior when SMS service is unavailable.
        
        Args:
            user_id: The user's ID
            user_email: The user's email for display purposes
            
        Returns:
            bool: True if 2FA passed or not required, False if 2FA failed and user should be logged out.
        """
        try:
            # Check if Twilio is available - if not, use fallback mode
            if not TWILIO_AVAILABLE or not twilio_service or not twilio_service.is_available():
                # FALLBACK MODE: Allow login but warn user about limited 2FA features
                logger.warning(f"Twilio service unavailable for user {user_email} - proceeding with fallback mode")
                
                # Show informational message about limited features (not blocking)
                QMessageBox.information(self, "2FA Service Limited", 
                    "SMS verification service is temporarily unavailable.\n\n"
                    "You can still log in, but 2FA features will be limited.\n"
                    "Please contact support if this issue persists.\n\n"
                    "Login will proceed without SMS verification.")
                
                # Allow login to proceed - skip all 2FA checks
                return True
            
            profile_res = enhanced_user_manager.get_complete_user_profile(user_id)
            
            # The primary condition is whether the user's phone has been verified via Twilio.
            if profile_res and profile_res.get('twilio_verified'):
                # Phone is verified. Now, check if they have enabled 2FA for logins.
                if profile_res.get('is_2fa_enabled'):
                    phone_number = profile_res.get('phone_number')
                    if not phone_number:
                        QMessageBox.critical(self, "2FA Error", "2FA is enabled, but no phone number is on file. Please contact support.")
                        return False # Block login
                    
                    logger.info(f"User {user_email} has 2FA enabled. Sending verification code.")
                    return self.send_2fa_code_and_verify(phone_number, user_email)
                else:
                    # Phone is verified, but they haven't opted into 2FA for every login.
                    # This is fine, let them pass.
                    logger.info(f"User {user_email} has a verified phone but 2FA is not turned on. Allowing login.")
                    return True
            else:
                # This user has not verified their phone number. Force them to do so now.
                logger.info(f"User {user_email} has not verified their phone. Forcing verification process.")
                return self.force_phone_verification(user_id, user_email)
                
        except Exception as e:
            logger.error(f"Error checking 2FA status: {e}", exc_info=True)
            QMessageBox.critical(self, "2FA Error", f"An error occurred while checking your security status: {e}")
            return False # Fail safe: if check fails, don't allow login.

    def force_phone_verification(self, user_id, user_email="User"):
        """Forces the user to complete phone verification with fallback for unavailable service.
        
        Args:
            user_id: The user's ID
            user_email: The user's email for display purposes
            
        Returns:
            bool: True if verification is successful, False otherwise.
        """
        # Check if Twilio service is available for phone verification
        if not TWILIO_AVAILABLE or not twilio_service or not twilio_service.is_available():
            logger.warning(f"Phone verification skipped for user {user_email} - Twilio service unavailable")
            QMessageBox.information(self, 
                "Phone Verification Unavailable",
                "Phone verification is currently unavailable due to SMS service issues.\n\n"
                "You can log in for now, but we recommend trying again later when the service is restored.\n"
                "Contact support if this issue persists.")
            # Allow login to proceed without phone verification
            return True
        
        from .phone_verification_dialog import PhoneVerificationDialog

        QMessageBox.information(self, 
            "Account Security Update",
            "To enhance account security, all users are now required to verify a phone number.\n\n"
            "You will now be guided through the verification process. This is a one-time requirement."
        )
        
        dialog = PhoneVerificationDialog(self, user_id)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            logger.info(f"Phone verification dialog accepted for user {user_id}")
            
            # SIMPLE FIX: Direct query to user_details table instead of using the view
            try:
                from ..database.supabase_client import supabase
                response = supabase.client.from_("user_details").select("twilio_verified").eq("user_id", user_id).single().execute()
                
                if response.data and response.data.get('twilio_verified') == True:
                    logger.info(f"Direct query confirmed: User {user_id} is now verified")
                    return True
                else:
                    logger.warning(f"Direct query shows user {user_id} is still not verified: {response.data}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error checking verification status directly: {e}")
                # If direct query fails, assume success since dialog was accepted
                return True
        else:
            logger.warning(f"User {user_id} cancelled the mandatory phone verification. Logging out.")
            QMessageBox.warning(self, "Login Cancelled", "Phone verification is required to use TrackPro. You have been logged out.")
            return False # User chose to cancel, deny login.

    def send_2fa_code_and_verify(self, phone_number, user_email="User"):
        """Send 2FA code and prompt user for verification.
        
        Args:
            phone_number: The phone number to send the code to
            user_email: User email for display purposes
            
        Returns:
            bool: True if verification successful, False otherwise
        """
        if not TWILIO_AVAILABLE or not twilio_service or not twilio_service.is_available():
            QMessageBox.critical(self, "2FA Error", 
                "SMS 2FA is not available. Please contact support.")
            return False
        
        try:
            from .sms_verification_dialog import SMSVerificationDialog
            
            # Create and show the SMS verification dialog
            dialog = SMSVerificationDialog(self, phone_number)
            result = dialog.exec()
            
            # Return True if verification was successful
            return dialog.verification_successful
            
        except Exception as e:
            logger.error(f"Error in 2FA process: {e}")
            QMessageBox.critical(self, "2FA Error", f"2FA verification failed: {str(e)}")
            return False
    
    def check_profile_completeness_and_redirect(self, user_id):
        """Check if user profile is complete and redirect if needed.
        
        Args:
            user_id: The user's ID
            
        Returns:
            bool: True if profile is complete or user completed it, False if incomplete
        """
        try:
            profile_res = enhanced_user_manager.get_complete_user_profile(user_id)
            if not profile_res:
                # No profile, needs to be created (will happen in main app)
                return True
            
            # Check required fields - handle None values safely
            username = (profile_res.get('username') or '').strip()
            display_name = (profile_res.get('display_name') or '').strip()
            
            if not username:
                # Profile incomplete, inform user
                QMessageBox.information(self, "Complete Your Profile",
                    "Please complete your profile information (username) before proceeding.")
                
                # For now, just inform them - the main app will handle the redirect
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking profile completeness: {e}")
            return True  # Allow login and let main app handle it
    
    def submit(self):
        """Submit the form and authenticate user."""
        if not self.validate_form():
            return
        
        # Get form values
        email = self.email_input.text()
        password = self.password_input.text()
        remember_me = self.remember_me_checkbox.isChecked() if hasattr(self, 'remember_me_checkbox') and self.remember_me_checkbox else True
        
        logger.info(f"Signing in user: {email}")
        
        # Check connection
        if not self.check_connection():
            if self.show_network_error("Cannot connect to server. Continue in offline mode?"):
                return
        
        try:
            # Authenticate user
            response = supabase.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response and response.user:
                logger.info(f"User {email} signed in successfully")
                
                # Check for terms of service acceptance
                if not check_and_prompt_for_terms(response.user.id, self):
                    # User declined terms, so abort the login.
                    try:
                        supabase.client.auth.sign_out()
                    except:
                        pass
                    return

                # Check 2FA before proceeding
                if not self.check_and_handle_2fa(response.user.id, email):
                    # 2FA failed, logout and return
                    try:
                        supabase.client.auth.sign_out()
                    except:
                        pass
                    return
                
                # Check profile completeness
                self.check_profile_completeness_and_redirect(response.user.id)
                
                # Store the remember me preference
                if hasattr(supabase, '_save_session'):
                    logger.info(f"Explicitly saving session after login with remember_me={remember_me}")
                    supabase._save_session(response, remember_me=remember_me)
                
                # Emit our signal
                self.auth_completed.emit(True, response)
                
                # Force the parent window to update if we can
                try:
                    parent = self.parent()
                    if parent:
                        from PyQt6.QtWidgets import QApplication
                        logger.info("Forcing parent window to update authentication state")
                        QApplication.processEvents()
                        
                        # If the parent has update_auth_state method, call it directly
                        if hasattr(parent, 'update_auth_state'):
                            logger.info("Parent has update_auth_state method, calling it")
                            parent.update_auth_state()
                            QApplication.processEvents()
                except Exception as e:
                    logger.error(f"Error updating parent window: {e}")
                
                # Close this dialog
                self.accept()
                
                # Show a brief success message
                QMessageBox.information(self, "Login Successful", 
                                      f"You are now logged in as {email}")
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