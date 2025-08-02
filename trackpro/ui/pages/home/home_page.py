"""Homepage with user welcome, date, and announcements."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame, QSizePolicy, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class HomePage(BasePage):
    """HomePage with user welcome, current date, and announcements."""
    
    def __init__(self, global_managers=None):
        super().__init__("home", global_managers)
    
    def init_page(self):
        """Initialize the homepage layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        # Create header section (user section left, events section right) - TOP
        self.create_header_section(layout)
        
        # Create announcements section - BOTTOM  
        self.create_announcements_section(layout)
        
        # Set up timer to update date every minute
        self.date_timer = QTimer()
        self.date_timer.timeout.connect(self.update_date)
        self.date_timer.start(60000)  # Update every minute
    
    def create_header_section(self, layout):
        """Create the main container with user section (left) and events section (right)."""
        main_container = QHBoxLayout()
        main_container.setSpacing(20)
        
        # Blue box - User Profile section (left)
        blue_section = QFrame()
        blue_section.setMinimumHeight(200)
        blue_section.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        self.create_user_section_content(blue_section)
        
        # Red box - Upcoming Events section (right)
        red_section = QFrame()
        red_section.setMinimumHeight(280)  # Compact space for three events
        red_section.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                padding: 4px;
            }
        """)
        red_layout = QVBoxLayout(red_section)
        red_layout.setContentsMargins(6, 2, 6, 6)  # Minimal top margin for header
        red_layout.setSpacing(2)  # Ultra-tight spacing to maximize event space
        
        # Upcoming Events title
        events_title = QLabel("Upcoming Events")
        events_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
        """)
        red_layout.addWidget(events_title)
        
        # Add upcoming events directly in red box
        self.create_upcoming_events(red_layout)
        
        # Add both sections to main container
        main_container.addWidget(blue_section, 1)
        main_container.addWidget(red_section, 1)
        
        # Create container widget for the layout
        container_widget = QWidget()
        container_widget.setLayout(main_container)
        layout.addWidget(container_widget)
    
    def create_user_section_content(self, blue_section):
        """Create content for the user section based on authentication status."""
        blue_layout = QVBoxLayout(blue_section)
        blue_layout.setContentsMargins(0, 0, 0, 0)
        blue_layout.setSpacing(8)
        
        # Check if user is authenticated
        is_authenticated = self.is_user_authenticated()
        
        if is_authenticated:
            self.create_authenticated_user_content(blue_layout)
        else:
            self.create_unauthenticated_user_content(blue_layout)
    
    def create_authenticated_user_content(self, layout):
        """Create user section content for authenticated users."""
        # User image placeholder
        self.user_image = QLabel()
        self.user_image.setFixedSize(80, 80)
        self.user_image.setStyleSheet("""
            QLabel {
                background-color: #5865f2;
                border-radius: 40px;
                border: 3px solid #ffffff;
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        self.user_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_user_image()
        layout.addWidget(self.user_image, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Welcome message
        self.welcome_label = QLabel()
        self.welcome_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        self.update_welcome_message()
        layout.addWidget(self.welcome_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Date display (right below user name)
        self.date_label = QLabel()
        self.date_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 14px;
                font-weight: normal;
                background-color: transparent;
                border: none;
            }
        """)
        self.update_date()
        layout.addWidget(self.date_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()  # Push content to top
    
    def create_unauthenticated_user_content(self, layout):
        """Create user section content for unauthenticated users with login/signup buttons."""
        # Welcome title
        welcome_title = QLabel("Welcome to TrackPro")
        welcome_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin-bottom: 8px;
            }
        """)
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_title)
        
        # Date display
        self.date_label = QLabel()
        self.date_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 14px;
                font-weight: normal;
                background-color: transparent;
                border: none;
                margin-bottom: 15px;
            }
        """)
        self.update_date()
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.date_label)
        
        # Description
        desc_label = QLabel("Sign in to access your racing data and coaching features")
        desc_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                background-color: transparent;
                border: none;
                margin-bottom: 15px;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Buttons container
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Login button
        self.login_button = QPushButton("Log In")
        self.login_button.setMinimumHeight(35)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #004080;
            }
        """)
        self.login_button.clicked.connect(self.show_login_dialog)
        buttons_layout.addWidget(self.login_button)
        
        # Sign up button
        self.signup_button = QPushButton("Sign Up")
        self.signup_button.setMinimumHeight(35)
        self.signup_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.signup_button.clicked.connect(self.show_signup_dialog)
        buttons_layout.addWidget(self.signup_button)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()  # Push content to center
    

    
    def create_upcoming_events(self, layout):
        """Create upcoming events list."""
        # Sample events data with updated dates
        upcoming_events = [
            {
                "title": "Weekly Racing League",
                "date": "Jan 08, 2025",
                "time": "8:00 PM EST",
                "type": "League Race"
            },
            {
                "title": "Spa-Francorchamps Open Practice",
                "date": "Jan 09, 2025", 
                "time": "6:00 PM EST",
                "type": "Practice Session"
            },
            {
                "title": "TrackPro Community Challenge",
                "date": "Jan 10, 2025",
                "time": "7:30 PM EST",
                "type": "Community Event"
            }
        ]
        
        # Create each event item and add to layout
        for i, event in enumerate(upcoming_events):
            try:
                event_widget = self.create_event_widget(event)
                layout.addWidget(event_widget)
                
                # Add minimal spacing between events (except after the last one)
                if i < len(upcoming_events) - 1:
                    layout.addSpacing(2)
                
                logger.info(f"Added event {i+1}: {event['title']}")
            except Exception as e:
                logger.error(f"Error creating event {i+1}: {e}")
                # Add a fallback simple label if widget creation fails
                fallback_label = QLabel(f"Event: {event['title']} - {event['date']}")
                fallback_label.setStyleSheet("color: #ffffff; padding: 5px;")
                layout.addWidget(fallback_label)
    
    def create_event_widget(self, event):
        """Create a simple, reliable event widget with proper text display."""
        # Create main container with optimized height for professional look
        event_container = QWidget()
        event_container.setFixedHeight(65)  # Compact size for three text lines
        event_container.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border-radius: 8px;
                border: 1px solid #40444b;
            }
            QWidget:hover {
                background-color: #2f2f2f;
                border-color: #5865f2;
            }
        """)
        
        # Use simple QHBoxLayout for the main structure
        main_layout = QHBoxLayout(event_container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Left: Icon
        icon_label = QLabel("🏁")
        icon_label.setFixedSize(30, 30)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: #5865f2;
                border-radius: 15px;
                color: white;
                font-size: 14px;
            }
        """)
        main_layout.addWidget(icon_label)
        
        # Right: Text content with ultra-tight spacing for maximum content
        text_content = f"""<div style="color: white; line-height: 1.1;">
            <div style="font-size: 15px; font-weight: bold; margin-bottom: 1px;">{event["title"]}</div>
            <div style="color: #b9bbbe; font-size: 12px; margin-bottom: 0px;">{event['date']} • {event['time']}</div>
            <div style="color: #5865f2; font-size: 11px; font-weight: bold;">{event["type"]}</div>
        </div>"""
        
        text_label = QLabel(text_content)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        text_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """)
        main_layout.addWidget(text_label, 1)  # Take up remaining space
        
        # Right: Arrow
        arrow_label = QLabel("→")
        arrow_label.setFixedSize(20, 20)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 16px;
                background-color: transparent;
                border: none;
            }
        """)
        main_layout.addWidget(arrow_label)
        
        return event_container
    
    def create_compact_announcement_card(self, layout, announcement):
        """Create a readable announcement card."""
        card_frame = QFrame()
        card_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 8px;
                border-left: 4px solid #5865f2;
                padding: 18px;
                margin-bottom: 8px;
            }
        """)
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(0, 0, 0, 0)
        
        # Announcement title
        title_label = QLabel(announcement["title"])
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 3px 0px;
            }
        """)
        card_layout.addWidget(title_label)
        
        # Date
        date_label = QLabel(announcement["date"])
        date_label.setStyleSheet("""
            QLabel {
                color: #72767d;
                font-size: 11px;
                background-color: transparent;
                border: none;
                padding: 2px 0px;
            }
        """)
        card_layout.addWidget(date_label)
        
        # Content (readable size)
        content_label = QLabel(announcement["content"])
        content_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 13px;
                line-height: 1.5;
                background-color: transparent;
                border: none;
                padding: 4px 0px;
            }
        """)
        content_label.setWordWrap(True)
        card_layout.addWidget(content_label)
        
        layout.addWidget(card_frame)
    
    def add_limited_announcements(self, layout):
        """Add limited announcements without scrolling."""
        announcements = [
            {
                "title": "🏁 New Race Coach Features Available!",
                "date": "December 15, 2024",
                "content": "Advanced telemetry analysis and personalized coaching tips now available."
            },
            {
                "title": "🎯 Pedal Calibration Improvements",
                "date": "December 10, 2024", 
                "content": "Updated algorithms provide more accurate and responsive pedal mapping."
            }
        ]
        
        for announcement in announcements:
            self.create_compact_announcement_card(layout, announcement)
    
    def create_announcements_section(self, layout):
        """Create the announcements section in yellow box."""
        # Yellow box - News & Announcements
        yellow_section = QFrame()
        yellow_section.setMinimumHeight(280)  # Just enough space for content
        yellow_section.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                padding: 18px;
            }
        """)
        yellow_layout = QVBoxLayout(yellow_section)
        yellow_layout.setContentsMargins(0, 0, 0, 0)
        yellow_layout.setSpacing(12)
        
        # Section title
        announcements_title = QLabel("📢 Latest News & Announcements")
        announcements_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        yellow_layout.addWidget(announcements_title)
        
        # Add limited announcements (no scrolling)
        self.add_limited_announcements(yellow_layout)
        
        yellow_layout.addStretch()  # Push content to top
        
        layout.addWidget(yellow_section)
    
    def update_user_image(self):
        """Update the user image with initials."""
        try:
            user_name = self.get_user_name()
            # Get initials from user name
            name_parts = user_name.split()
            if len(name_parts) >= 2:
                initials = f"{name_parts[0][0]}{name_parts[1][0]}".upper()
            elif len(name_parts) == 1:
                initials = name_parts[0][:2].upper()
            else:
                initials = "U"
            
            self.user_image.setText(initials)
        except Exception as e:
            logger.error(f"Error updating user image: {e}")
            self.user_image.setText("U")
    
    def update_welcome_message(self):
        """Update the welcome message with the current user's name."""
        try:
            user_name = self.get_user_name()
            self.welcome_label.setText(f"Welcome {user_name}")
        except Exception as e:
            logger.error(f"Error updating welcome message: {e}")
            self.welcome_label.setText("Welcome User")
    
    def is_user_authenticated(self):
        """Check if the user is currently authenticated."""
        try:
            logger.info("🔍 Checking authentication status...")
            
            # First try to get from the auth handler
            if self.auth_handler:
                # Check if the main window has authentication status
                if hasattr(self.parent(), 'get_current_user_info'):
                    user_info = self.parent().get_current_user_info()
                    logger.info(f"🔍 Auth handler user info: {user_info}")
                    if user_info and user_info.get('name') and user_info.get('name') != "Anonymous User":
                        logger.info("✅ Authenticated via auth handler")
                        return True
            
            # Fallback to user manager
            from ....auth.user_manager import get_current_user
            user = get_current_user()
            logger.info(f"🔍 User manager user: authenticated={getattr(user, 'is_authenticated', False)}, name={getattr(user, 'name', 'None')}")
            if user and user.is_authenticated and user.name != "Anonymous User":
                logger.info("✅ Authenticated via user manager")
                return True
            
            # Final fallback to Supabase directly
            from ....database.supabase_client import supabase
            user_response = supabase.get_user()
            logger.info(f"🔍 Supabase user response: {user_response}")
            if user_response and hasattr(user_response, 'user') and user_response.user:
                logger.info("✅ Authenticated via Supabase")
                return True
            
            logger.info("❌ Not authenticated - should show login/signup buttons")
            return False
            
        except Exception as e:
            logger.error(f"Error checking authentication status: {e}")
            return False

    def get_user_name(self):
        """Get the current user's name from the authentication system."""
        try:
            # Try to get user info from the auth handler
            if self.auth_handler:
                # First try to get from the main window's method if available
                if hasattr(self.parent(), 'get_current_user_info'):
                    user_info = self.parent().get_current_user_info()
                    if user_info and user_info.get('name'):
                        return user_info['name']
            
            # Fallback to user manager
            from ....auth.user_manager import get_current_user
            user = get_current_user()
            if user and user.name and user.name != "Anonymous User":
                return user.name
            
            # Final fallback to Supabase directly
            from ....database.supabase_client import supabase
            user_response = supabase.get_user()
            if user_response and hasattr(user_response, 'user') and user_response.user:
                user = user_response.user
                if hasattr(user, 'user_metadata') and user.user_metadata:
                    metadata = user.user_metadata
                    if metadata.get('display_name'):
                        return metadata['display_name']
                    elif metadata.get('username'):
                        return metadata['username']
                    elif metadata.get('name'):
                        return metadata['name']
                
                # Use email username as fallback
                if user.email:
                    return user.email.split('@')[0].title()
            
            return "User"
            
        except Exception as e:
            logger.error(f"Error getting user name: {e}")
            return "User"
    
    def update_date(self):
        """Update the date display."""
        try:
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            self.date_label.setText(current_date)
        except Exception as e:
            logger.error(f"Error updating date: {e}")
    
    def on_page_activated(self):
        """Called when the page is activated."""
        super().on_page_activated()
        
        # Check if authentication state has changed since last activation
        current_auth_state = self.is_user_authenticated()
        if not hasattr(self, '_last_auth_state') or self._last_auth_state != current_auth_state:
            # Authentication state changed, refresh the header
            logger.info(f"🔄 Authentication state changed from {getattr(self, '_last_auth_state', 'unknown')} to {current_auth_state}")
            self.refresh_header()
            self._last_auth_state = current_auth_state
        else:
            # Only update individual components if they exist (for authenticated users)
            if hasattr(self, 'user_image'):
                self.update_user_image()
            if hasattr(self, 'welcome_label'):
                self.update_welcome_message()
            if hasattr(self, 'date_label'):
                self.update_date()
    
    def show_login_dialog(self):
        """Show the login dialog."""
        try:
            # Get the main window reference
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'show_login_dialog'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'show_login_dialog'):
                success = main_window.show_login_dialog()
                if success:
                    # Refresh the header section to show authenticated content
                    self.refresh_header()
                return success
            else:
                # Fallback to direct dialog creation
                from ....auth.login_dialog import LoginDialog
                login_dialog = LoginDialog(self)
                result = login_dialog.exec()
                if result == 1:
                    self.refresh_header()
                    return True
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
    
    def show_signup_dialog(self):
        """Show the signup dialog."""
        try:
            # Get the main window reference
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'show_signup_dialog'):
                main_window = main_window.parent()
            
            if main_window and hasattr(main_window, 'show_signup_dialog'):
                success = main_window.show_signup_dialog()
                if success:
                    # Refresh the header section to show authenticated content
                    self.refresh_header()
                return success
            else:
                # Fallback to direct dialog creation
                from ....auth.signup_dialog import SignupDialog
                signup_dialog = SignupDialog(self)
                result = signup_dialog.exec()
                if result == 1:
                    self.refresh_header()
                    return True
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
    
    def refresh_header(self):
        """Refresh the header section after authentication status changes."""
        try:
            # Clear the entire layout to prevent duplication
            layout = self.layout()
            if layout:
                # Remove all items from the layout
                while layout.count():
                    child = layout.takeAt(0)
                    if child and child.widget():
                        child.widget().deleteLater()
                
                # Recreate the entire page content
                self.create_header_section(layout)
                self.create_announcements_section(layout)
            
        except Exception as e:
            logger.error(f"Error refreshing header: {e}")
    
    def on_auth_state_changed(self):
        """Public method to call when authentication state changes externally."""
        logger.info("🔄 External authentication state change detected")
        # Reset the cached state so next activation will refresh
        if hasattr(self, '_last_auth_state'):
            delattr(self, '_last_auth_state')
        # Immediately refresh if the page is currently visible
        self.refresh_header()

    def cleanup(self):
        """Clean up resources when the page is destroyed."""
        if hasattr(self, 'date_timer'):
            self.date_timer.stop()
        super().cleanup()