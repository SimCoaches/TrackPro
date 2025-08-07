"""Homepage with user welcome, date, and announcements."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QPen
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class HomePage(BasePage):
    """Home page with welcome message, date, and announcements."""
    
    def __init__(self, global_managers=None):
        super().__init__("home", global_managers)
        self._auth_check_completed = False
        self._cached_auth_state = None
        self.setup_ui()
        
    def init_page(self):
        """Initialize the page - called by BasePage."""
        # This is called by BasePage, but we do our setup in setup_ui
        pass
        
    def setup_ui(self):
        """Set up the home page UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Main content area with two columns
        main_content = QHBoxLayout()
        main_content.setSpacing(30)
        
        # Left column - User welcome section
        left_column = self.create_welcome_section()
        main_content.addWidget(left_column)
        
        # Right column - Upcoming events section
        right_column = self.create_events_section()
        main_content.addWidget(right_column)
        
        layout.addLayout(main_content)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Update date and events
        self.update_date()
        self.load_events()
        
        # Initialize avatar with default or current user
        self.initialize_avatar()
        
        # Set up timer to update date every minute
        self.date_timer = QTimer()
        self.date_timer.timeout.connect(self.update_date)
        self.date_timer.start(60000)  # Update every minute
        
    def create_welcome_section(self):
        """Create the left column welcome section."""
        welcome_frame = QFrame()
        welcome_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        welcome_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 15px;
                border: 1px solid #3a3a3a;
            }
        """)
        welcome_frame.setFixedWidth(400)
        
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setContentsMargins(30, 30, 30, 30)
        welcome_layout.setSpacing(20)
        
        # User avatar - optimized sizing
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(100, 100)  # Reduced from 120x120
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet("""
            QLabel {
                border: 3px solid #3498db;
                border-radius: 50px;
                background-color: #3498db;
                color: white;
                font-size: 36px;
                font-weight: bold;
            }
        """)
        # Don't set default text - will be replaced by dynamic avatar
        welcome_layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Welcome message
        self.welcome_label = QLabel("Welcome to TrackPro!")
        self.welcome_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))  # Slightly smaller
        self.welcome_label.setStyleSheet("color: #ffffff; margin: 10px;")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setWordWrap(True)
        welcome_layout.addWidget(self.welcome_label)
        
        # Date and time
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Arial", 13))  # Slightly smaller
        self.date_label.setStyleSheet("color: #cccccc; margin: 5px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(self.date_label)
        
        # Authentication buttons container (initially hidden)
        self.auth_buttons_container = QWidget()
        self.auth_buttons_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        auth_buttons_layout = QVBoxLayout(self.auth_buttons_container)
        auth_buttons_layout.setSpacing(10)
        auth_buttons_layout.setContentsMargins(0, 10, 0, 0)
        
        # Sign Up button
        self.signup_button = QPushButton("Sign Up")
        self.signup_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.signup_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                padding: 12px;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.signup_button.clicked.connect(self.show_signup_dialog)
        auth_buttons_layout.addWidget(self.signup_button)
        
        # Log In button
        self.login_button = QPushButton("Log In")
        self.login_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                border: none;
                padding: 12px;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.login_button.clicked.connect(self.show_login_dialog)
        auth_buttons_layout.addWidget(self.login_button)
        
        # Add auth buttons to welcome layout
        welcome_layout.addWidget(self.auth_buttons_container)
        
        # Show auth buttons by default for non-authenticated users
        self.auth_buttons_container.setVisible(True)
        
        return welcome_frame
        
    def create_events_section(self):
        """Create the right column events section."""
        events_frame = QFrame()
        events_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        events_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 15px;
                border: 1px solid #3a3a3a;
            }
        """)
        
        events_layout = QVBoxLayout(events_frame)
        events_layout.setContentsMargins(30, 30, 30, 30)
        events_layout.setSpacing(20)
        
        # Events title
        events_title = QLabel("Upcoming Events")
        events_title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        events_title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        events_layout.addWidget(events_title)
        
        # Events container
        self.events_container = QVBoxLayout()
        self.events_container.setSpacing(15)
        events_layout.addLayout(self.events_container)
        
        return events_frame
        
    def create_event_card(self, title, subtitle, description, event_image=None):
        """Create an individual event card."""
        event_frame = QFrame()
        event_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        event_frame.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 10px;
                border: 1px solid #444444;
            }
            QFrame:hover {
                background-color: #3a3a3a;
                border: 1px solid #555555;
            }
        """)
        
        event_layout = QHBoxLayout(event_frame)
        event_layout.setContentsMargins(15, 15, 15, 15)
        event_layout.setSpacing(15)
        
        # Event image
        image_label = QLabel()
        image_label.setFixedSize(50, 50)  # Smaller icon
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if event_image:
            pixmap = QPixmap(event_image)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
            else:
                # Fallback to default event icon
                image_label.setStyleSheet("""
                    QLabel {
                        background-color: #3498db;
                        border-radius: 25px;
                        color: white;
                        font-size: 20px;
                    }
                """)
                image_label.setText("🏁")
        else:
            # Default event icon
            image_label.setStyleSheet("""
                QLabel {
                    background-color: #3498db;
                    border-radius: 25px;
                    color: white;
                    font-size: 20px;
                }
            """)
            image_label.setText("🏁")
        
        event_layout.addWidget(image_label)
        
        # Event details - no borders around text
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)  # Tighter spacing
        details_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        title_label.setWordWrap(True)
        details_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(QFont("Arial", 11))
        subtitle_label.setStyleSheet("color: #3498db; background: transparent; border: none;")
        subtitle_label.setWordWrap(True)
        details_layout.addWidget(subtitle_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Arial", 10))
        desc_label.setStyleSheet("color: #cccccc; background: transparent; border: none;")
        desc_label.setWordWrap(True)
        details_layout.addWidget(desc_label)
        
        event_layout.addLayout(details_layout)
        event_layout.addStretch()
        
        return event_frame
        
    def update_date(self):
        """Update the date and time display."""
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        self.date_label.setText(f"{date_str}\n{time_str}")
        
    def load_events(self):
        """Load and display upcoming events."""
        # Clear existing events
        while self.events_container.count():
            child = self.events_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Sample events with title, subtitle, description, and image
        events = [
            {
                'title': 'Weekly Racing League',
                'subtitle': 'Every Saturday at 2 PM',
                'description': 'Join our weekly racing league featuring competitive races across various tracks and car classes.',
                'image': None  # Will use default icon
            },
            {
                'title': 'Spa-Francorchamps Open Practice',
                'subtitle': 'This Sunday',
                'description': 'Open practice session on the legendary Spa-Francorchamps circuit. Perfect for improving your lap times.',
                'image': None
            },
            {
                'title': 'TrackPro Community Challenge',
                'subtitle': 'Next Week',
                'description': 'Special community event with unique challenges and rewards for all participants.',
                'image': None
            }
        ]
        
        for event in events:
            event_card = self.create_event_card(
                event['title'],
                event['subtitle'],
                event['description'],
                event['image']
            )
            self.events_container.addWidget(event_card)
        
    def update_user_avatar(self, user_data):
        """Update the user avatar with user data."""
        if not user_data:
            return
            
        # Check if user has an avatar URL
        avatar_url = user_data.get('avatar_url')
        if avatar_url:
            # Load avatar from URL
            self.load_avatar_from_url(avatar_url)
            return
            
        # Fallback to initials if no avatar URL
        # Get user name for initials
        name = user_data.get('display_name') or user_data.get('username') or user_data.get('name', 'U')
        
        # For current user, try to use first and last name if available
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        if first_name or last_name:
            name = f"{first_name} {last_name}".strip()
        
        # Generate initials from the name
        initials = self._generate_initials(name)
        
        # Create avatar with initials
        self.create_avatar_with_initials(initials, name)
    
    def load_avatar_from_url(self, url: str):
        """Load and display avatar from URL."""
        # TEMPORARILY DISABLE AVATAR LOADING TO PREVENT CRASHES
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ TEMPORARILY SKIPPING AVATAR LOADING TO PREVENT CRASHES")
        return
        
        try:
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt6.QtCore import QUrl
            
            # Create network manager if it doesn't exist
            if not hasattr(self, 'network_manager'):
                self.network_manager = QNetworkAccessManager(self)
            
            # Download image
            request = QNetworkRequest(QUrl(url))
            reply = self.network_manager.get(request)
            
            def on_avatar_downloaded():
                try:
                    if reply.error() == reply.NetworkError.NoError:
                        image_data = reply.readAll()
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        
                        # Scale and crop to circle
                        if not pixmap.isNull():
                            # Scale to fit avatar size (100x100)
                            avatar_size = 100
                            scaled_pixmap = pixmap.scaled(
                                avatar_size, avatar_size, 
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation
                            )
                            
                            # Create circular mask
                            circular_pixmap = QPixmap(avatar_size, avatar_size)
                            circular_pixmap.fill(Qt.GlobalColor.transparent)
                            
                            painter = QPainter(circular_pixmap)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                            painter.setBrush(QBrush(scaled_pixmap))
                            painter.setPen(QPen(Qt.GlobalColor.transparent))
                            painter.drawEllipse(0, 0, avatar_size, avatar_size)
                            painter.end()
                            
                            # Update avatar display
                            self.avatar_label.setPixmap(circular_pixmap)
                    
                    reply.deleteLater()
                except Exception as e:
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    self.create_avatar_with_initials("U", "User")
            
            reply.finished.connect(on_avatar_downloaded)
            
        except Exception as e:
            logger.error(f"Error loading avatar from URL: {e}")
            # Fallback to initials
            self.create_avatar_with_initials("U", "User")
            
    def _generate_initials(self, name):
        """Generate initials from a name."""
        if not name:
            return "U"
        
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
        else:
            return "U"
            
    def create_avatar_with_initials(self, initials, name):
        """Create a circular avatar with user initials."""
        size = 100  # Updated to match the new avatar size
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(size // 3)  # Adjusted for new size
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        
        self.avatar_label.setPixmap(pixmap)
        
    def initialize_avatar(self):
        """Initialize the avatar with current user or default."""
        try:
            # Try to get complete user profile first (includes avatar_url)
            try:
                from ....social import enhanced_user_manager
                complete_profile = enhanced_user_manager.get_complete_user_profile()
                if complete_profile:
                    # Update welcome message
                    name = complete_profile.get('display_name') or complete_profile.get('username') or complete_profile.get('name', 'User')
                    self.welcome_label.setText(f"Welcome back, {name}!")
                    
                    # Update avatar with complete user data (includes avatar_url)
                    self.update_user_avatar(complete_profile)
                    
                    logger.info(f"✅ Avatar initialized with complete profile: {name}")
                    return
            except Exception as profile_error:
                logger.debug(f"Could not get complete user profile: {profile_error}")
            
            # Fallback to basic user manager
            from ....auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                # Update welcome message
                self.welcome_label.setText(f"Welcome back, {current_user.name}!")
                
                # Update avatar with user data
                user_data = {
                    'name': current_user.name,
                    'email': current_user.email,
                    'user_id': current_user.id
                }
                self.update_user_avatar(user_data)
                
                logger.info(f"✅ Avatar initialized with user: {current_user.name}")
            else:
                # Use default avatar with "TP" for TrackPro
                self.create_avatar_with_initials("TP", "TrackPro")
                logger.info("ℹ️ Avatar initialized with default TrackPro initials")
                
        except Exception as e:
            logger.error(f"Error initializing avatar: {e}")
            # Fallback to default
            self.create_avatar_with_initials("TP", "TrackPro")
            
    def show_signup_dialog(self):
        """Show the signup dialog."""
        try:
            from trackpro.auth.signup_dialog import SignupDialog
            
            # Get oauth_handler from global managers if available
            oauth_handler = None
            if self.global_managers and hasattr(self.global_managers, 'auth'):
                oauth_handler = self.global_managers.auth
            
            signup_dialog = SignupDialog(self, oauth_handler=oauth_handler)
            result = signup_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user signed up)
                logger.info("🔐 User successfully signed up")
                # Update authentication state
                self.on_auth_state_changed()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error showing signup dialog: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, 
                "Authentication Error", 
                f"Could not open signup dialog: {str(e)}"
            )
            return False
    
    def show_login_dialog(self):
        """Show the login dialog."""
        try:
            from trackpro.auth.login_dialog import LoginDialog
            
            # Get oauth_handler from global managers if available
            oauth_handler = None
            if self.global_managers and hasattr(self.global_managers, 'auth'):
                oauth_handler = self.global_managers.auth
            
            login_dialog = LoginDialog(self, oauth_handler=oauth_handler)
            result = login_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user logged in)
                logger.info("🔐 User successfully logged in")
                # Update authentication state
                self.on_auth_state_changed()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error showing login dialog: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, 
                "Authentication Error", 
                f"Could not open login dialog: {str(e)}"
            )
            return False

    def on_auth_state_changed(self):
        """Handle authentication state changes."""
        try:
            logger.info("🔄 Home page auth state changed - starting...")
            
            # Check if user is authenticated
            from trackpro.auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                logger.info(f"✅ User authenticated: {current_user.email}")
                self.refresh_header()
                logger.info("✅ Home page header refreshed after auth state change")
            else:
                logger.info("ℹ️ User not authenticated")
                self.refresh_header()
                logger.info("✅ Home page header refreshed (not authenticated)")
                
        except Exception as e:
            logger.error(f"❌ Error in home page auth state change: {e}")

    def refresh_header(self):
        """Refresh the header with current user information."""
        try:
            logger.info("🔄 Home page refresh_header started...")
            
            # Get current user
            from trackpro.auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                logger.info(f"✅ User authenticated: {current_user.email}")
                
                # Update welcome message
                if hasattr(self, 'welcome_label'):
                    try:
                        self.welcome_label.setText(f"Welcome back, {current_user.name or current_user.email}!")
                        logger.info("✅ Welcome label updated")
                    except Exception as welcome_error:
                        logger.error(f"❌ Error updating welcome label: {welcome_error}")
                
                # Hide auth buttons container for authenticated users
                if hasattr(self, 'auth_buttons_container'):
                    try:
                        self.auth_buttons_container.setVisible(False)
                        logger.info("✅ Auth buttons container hidden")
                    except Exception as auth_error:
                        logger.error(f"❌ Error hiding auth buttons container: {auth_error}")
                
                logger.info("✅ Authenticated with complete profile: {current_user.name or current_user.email}")
            else:
                logger.info("ℹ️ User not authenticated")
                
                # Update welcome message for non-authenticated users
                if hasattr(self, 'welcome_label'):
                    try:
                        self.welcome_label.setText("Welcome to TrackPro! Please log in to get started.")
                        logger.info("✅ Welcome label updated for non-authenticated user")
                    except Exception as welcome_error:
                        logger.error(f"❌ Error updating welcome label: {welcome_error}")
                
                # Show auth buttons container for non-authenticated users
                if hasattr(self, 'auth_buttons_container'):
                    try:
                        self.auth_buttons_container.setVisible(True)
                        logger.info("✅ Auth buttons container shown")
                    except Exception as auth_error:
                        logger.error(f"❌ Error showing auth buttons container: {auth_error}")
                
                logger.info("ℹ️ Not authenticated")
            
            logger.info("✅ Home page refresh_header completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in home page refresh_header: {e}")
            
    def on_external_auth_change(self):
        """Handle external authentication state changes."""
        # Reset completion flag to allow re-checking
        self._auth_check_completed = False
        self._cached_auth_state = None
        self.on_auth_state_changed()
    
    def on_page_activated(self):
        """Called when the home page is activated."""
        # Reset completion flag to allow re-checking when page is activated
        self._auth_check_completed = False
        self._cached_auth_state = None
        # Check authentication state when page is activated
        self.on_auth_state_changed()