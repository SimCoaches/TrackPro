"""Login dialog for user authentication."""

from PyQt5.QtWidgets import (
    QLineEdit, QCheckBox, QFormLayout, QLabel, 
    QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap
from .base_dialog import BaseAuthDialog
from ..database.supabase_client import supabase
import logging
import socket
import webbrowser
import os

logger = logging.getLogger(__name__)

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
        heading_label.setAlignment(Qt.AlignCenter)
        heading_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 5px;")
        left_column_layout.addWidget(heading_label)
        
        # Add Subheading
        subheading_label = QLabel("Making Drivers Faster One Lap At A Time")
        subheading_label.setAlignment(Qt.AlignCenter)
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
        header_label.setAlignment(Qt.AlignCenter)
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
        google_icon_path = os.path.join(icons_dir, "google.png")
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
        discord_icon_path = os.path.join(icons_dir, "discord.png")
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
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        image_label.setStyleSheet("color: #ccc; font-size: 16px;")
        
        # Optional: Load an actual image if available
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "images", "login_image.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            image_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            image_label.setText("Image not found")
        
        right_column_layout.addWidget(image_label)
        
        # Add right column widget to main layout
        main_h_layout.addWidget(right_column_widget, 1) # Assign stretch factor 1
        
        # Set tab order (consider how it flows across columns if needed)
        self.set_tab_order()
    
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
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(input_style)
        form_layout.addRow("Password:", self.password_input)
        
        # Remember me checkbox
        self.remember_me_checkbox = QCheckBox("Remember me")
        form_layout.addRow("", self.remember_me_checkbox)
    
    def handle_google_login(self):
        """Handle login with Google."""
        try:
            # Set the pending provider
            self.pending_provider = "google"
            
            # Check if OAuth is available and get the port
            oauth_port = getattr(self.oauth_handler, 'oauth_port', 3000) if self.oauth_handler else 3000
            
            # Check if the callback server is actually running
            if not self.oauth_handler or not hasattr(self.oauth_handler, 'oauth_port'):
                self.show_error("Google login is currently unavailable. The OAuth callback server failed to start.\n\nPlease try restarting TrackPro or use email/password login instead.")
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
                
                # Connect to the oauth handler's signal if available
                if self.oauth_handler:
                    # Disconnect first to avoid duplicate connections if called multiple times
                    try:
                        self.oauth_handler.auth_completed.disconnect(self.on_oauth_completed)
                    except TypeError:
                        pass # Signal not connected
                    self.oauth_handler.auth_completed.connect(self.on_oauth_completed)
                
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
                        from PyQt5.QtWidgets import QApplication
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
                                      f"You are now logged in as {user_response.user.email if hasattr(user_response.user, 'email') else 'User'}")
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
                self.show_error("Discord login is currently unavailable. The OAuth callback server failed to start.\n\nPlease try restarting TrackPro or use email/password login instead.")
                return

            # Make sure we're connected
            if not self.check_connection():
                self.discord_button.setEnabled(True)
                if self.show_network_error("Cannot connect to server to authenticate with Discord."):
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
                    from PyQt5.QtWidgets import QApplication
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
            
            # Determine user email for the confirmation message
            user_email = "User"
            if hasattr(response, 'user') and hasattr(response.user, 'email'):
                user_email = response.user.email
            elif hasattr(response, 'email'):
                user_email = response.email
            
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
            response = supabase.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response and response.user:
                logger.info(f"User {email} signed in successfully")
                
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
                        from PyQt5.QtWidgets import QApplication
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