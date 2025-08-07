"""Discord-style navigation widget with racing SVG icons."""

import os
from typing import Dict, Any, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QToolTip, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QRect
)
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QBrush, QPen
from PyQt6.QtSvgWidgets import QSvgWidget

class DiscordNavigationButton(QPushButton):
    """Individual navigation button with Discord-style styling."""
    
    def __init__(self, icon_path: str, text: str, page: str, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.text = text
        self.page = page
        self.is_collapsed = True
        
        self.setCheckable(True)
        self.setToolTip(text)
        self.setup_styling()
        self.update_button_content()
        
    def setup_styling(self):
        """Setup Discord-like button styling."""
        # Store base styles separately for clean switching
        self.base_styles = """
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 8px;
                color: #dcddde;
                font-size: 14px;
                font-weight: 600;
                margin: 1px;
            }
            QPushButton:hover {
                background-color: #40444b;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #5865f2;
                color: white;
                font-weight: 700;
            }
            QPushButton:checked:hover {
                background-color: #4752c4;
            }
        """
        
    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state of the button."""
        self.is_collapsed = collapsed
        self.update_button_content()
        
    def update_button_content(self):
        """Update button content based on collapsed state."""
        if self.is_collapsed:
            # Show only icon, centered
            if os.path.exists(self.icon_path):
                icon = QIcon(self.icon_path)
                self.setIcon(icon)
                self.setText("")
            else:
                # Fallback to first letter if icon not found
                self.setText(self.text[0])
                self.setIcon(QIcon())  # Clear any existing icon
            
            # Set collapsed state styling - perfectly centered with no padding
            self.setFixedSize(40, 40)  # Slightly smaller for better proportions in narrower nav
            collapsed_styles = self.base_styles + """
                QPushButton {
                    text-align: center;
                    padding: 0px;
                    qproperty-iconSize: 18px 18px;
                }
            """
            self.setStyleSheet(collapsed_styles)
        else:
            # Show icon + text, left-aligned
            if os.path.exists(self.icon_path):
                icon = QIcon(self.icon_path)
                self.setIcon(icon)
            self.setText(f"  {self.text}")
            self.setFixedSize(200, 44)
            
            # Set expanded state styling - left-aligned with padding
            expanded_styles = self.base_styles + """
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    qproperty-iconSize: 16px 16px;
                }
            """
            self.setStyleSheet(expanded_styles)

class DiscordNavigation(QWidget):
    """Discord-style navigation sidebar."""
    
    page_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.is_expanded = False
        self.buttons = []
        self.current_page = "home"
        
        # Dimensions
        self.collapsed_width = 56  # Narrower, more professional width for centered 44px buttons
        self.expanded_width = 220  # Wider to accommodate full text labels
        
        # Animation
        self.animation = None
        self.animation_duration = 300
        self.is_animating = False
        
        # Button group
        self.button_group = None
        
        # PERFORMANCE: Cache auth state to prevent duplicate calls
        self._cached_auth_state = None
        self._cached_user_info = None
        
        self.setup_ui()
        self.setup_menu_items()
        self.setup_iracing_status()
        self.setup_user_profile()
        
        # Start with collapsed state
        self.set_collapsed_state()
        
    def setup_ui(self):
        """Setup the main UI structure."""
        self.setFixedWidth(self.collapsed_width)
        self.setStyleSheet("""
            DiscordNavigation {
                background-color: #1e1e1e;
                border: none;
            }
            DiscordNavigation QWidget {
                background-color: #1e1e1e;
            }
            DiscordNavigation QFrame {
                background-color: #1e1e1e;
            }
        """)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 8, 0, 8)  # Remove horizontal margins to avoid centering conflicts
        self.main_layout.setSpacing(4)
        
        # Toggle button at top
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setFixedSize(36, 36)  # Smaller toggle button for narrower nav
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                border: none;
                border-radius: 18px;
                color: #dcddde;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5865f2;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_navigation)
        self.main_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #1e1e1e; margin: 6px 0px;")  # Slightly smaller margins for narrower nav
        separator.setFixedHeight(1)
        self.main_layout.addWidget(separator)
        
        # Buttons container  
        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 4, 0, 4)  # Remove horizontal margins, handle centering differently
        self.buttons_layout.setSpacing(4)
        self.buttons_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.main_layout.addWidget(self.buttons_container)
        self.main_layout.addStretch()
        
        # User profile section at bottom - will be called from __init__
        
    def setup_menu_items(self):
        """Setup the navigation menu items."""
        # Get the absolute path to the icons directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(os.path.dirname(current_dir), 'resources', 'icons')
        
        menu_items = [
            {"text": "Home", "icon": "home.svg", "page": "home"},
            {"text": "Pedals", "icon": "pedals.svg", "page": "pedals"},
            {"text": "Handbrake", "icon": "handbrake.svg", "page": "handbrake"},
            {"text": "Race Coach", "icon": "race_coach.svg", "page": "race_coach"},
            {"text": "Overlays", "icon": "overlays.svg", "page": "overlays"},
            {"text": "Race Pass", "icon": "race_pass.svg", "page": "race_pass"},
            {"text": "Community", "icon": "community.svg", "page": "community"},
            {"text": "Support", "icon": "support.svg", "page": "support"}
        ]
        
        from PyQt6.QtWidgets import QButtonGroup
        self.button_group = QButtonGroup(self)
        
        for item in menu_items:
            icon_path = os.path.join(icons_dir, item["icon"])
            button = DiscordNavigationButton(
                icon_path=icon_path,
                text=item["text"],
                page=item["page"]
            )
            button.clicked.connect(lambda checked, page=item["page"]: self.page_requested.emit(page))
            
            self.buttons.append(button)
            self.button_group.addButton(button)
            
            # Create horizontal container for each button to handle centering properly
            button_container = QWidget()
            button_h_layout = QHBoxLayout(button_container)
            button_h_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add button to horizontal layout with stretches for centering (collapsed state)
            button_h_layout.addStretch()
            button_h_layout.addWidget(button)
            button_h_layout.addStretch()
            
            self.buttons_layout.addWidget(button_container)
            
            # Store references for layout management
            button.parent_layout = self.buttons_layout
            button.h_container = button_container
            button.h_layout = button_h_layout
            
        # Set first button as checked by default
        if self.buttons:
            self.buttons[0].setChecked(True)
            
    def toggle_navigation(self):
        """Toggle between collapsed and expanded states."""
        if self.is_animating:
            return
            
        target_width = self.expanded_width if not self.is_expanded else self.collapsed_width
        self.animate_to_width(target_width)
        
    def animate_to_width(self, target_width: int):
        """Animate the navigation to target width."""
        if self.animation:
            self.animation.stop()
            
        self.is_animating = True
        
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        
        self.animation.valueChanged.connect(self.on_animation_step)
        self.animation.finished.connect(self.on_animation_finished)
        
        self.animation.start()
        
    def on_animation_step(self, value):
        """Handle animation step to update button states."""
        self.setFixedWidth(value)
        
        # Update button states during animation with proper alignment
        is_expanding = value > self.collapsed_width + 15  # Adjusted threshold for narrower nav
        for button in self.buttons:
            button.set_collapsed(not is_expanding)
        
        # Ensure container alignment is updated during animation to prevent shifting
        if hasattr(self, 'buttons_layout'):
            for button in self.buttons:
                if hasattr(button, 'h_layout'):
                    # Clear the horizontal layout
                    while button.h_layout.count():
                        child = button.h_layout.takeAt(0)
                        if child.widget():
                            child.widget().setParent(None)
                    
                    if is_expanding:
                        # Expanding: left-align buttons with margin
                        button.h_layout.setContentsMargins(8, 0, 0, 0)
                        button.h_layout.addWidget(button)
                        button.h_layout.addStretch()
                    else:
                        # Collapsing: center-align buttons with stretches
                        button.h_layout.setContentsMargins(0, 0, 0, 0)
                        button.h_layout.addStretch()
                        button.h_layout.addWidget(button)
                        button.h_layout.addStretch()
        
        # Update iRacing status visibility during animation (but don't rebuild layout)
        if hasattr(self, 'iracing_status_label'):
            self.iracing_status_label.setVisible(is_expanding)
            
    def on_animation_finished(self):
        """Handle animation completion."""
        self.is_animating = False
        self.is_expanded = self.width() > self.collapsed_width + 15  # Adjusted threshold for narrower nav
        self.set_collapsed_state()
        
    def setup_user_profile(self):
        """Setup the user profile section at the bottom."""
        # User profile container
        self.user_profile_container = QWidget()
        self.user_profile_layout = QHBoxLayout(self.user_profile_container)
        self.user_profile_layout.setContentsMargins(8, 8, 8, 8)  # Increased margins for larger avatar
        self.user_profile_layout.setSpacing(8)
        self.user_profile_container.setFixedHeight(80)  # Much taller to prevent chopping of larger avatar
        
        # User avatar button (now supports both text and images)
        self.user_avatar_btn = QPushButton()
        self.user_avatar_btn.setFixedSize(45, 45)  # Smaller avatar to fit the narrow sidebar width
        self.user_avatar_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                border: 3px solid #40444b;
                border-radius: 22.5px;
                color: white;
                font-size: 24px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #4752c4;
                border-color: #5865f2;
            }
        """)
        
        # Set default user initials (can be updated with actual user data)
        self.user_avatar_btn.setText("U")
        self.user_avatar_btn.setToolTip("Account Settings")
        self.user_avatar_btn.clicked.connect(lambda: self.page_requested.emit("account"))
        
        # Store avatar URL for updates
        self.current_avatar_url = None
        
        # User info label (only shown when expanded)
        self.user_info_label = QLabel("User")
        self.user_info_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        
        # Add to layout
        self.user_profile_layout.addWidget(self.user_avatar_btn)
        self.user_profile_layout.addWidget(self.user_info_label)
        self.user_profile_layout.addStretch()
        
        # Add separator above user profile
        user_separator = QFrame()
        user_separator.setFrameStyle(QFrame.Shape.HLine)
        user_separator.setStyleSheet("background-color: #252525; margin: 8px 0px;")
        user_separator.setFixedHeight(1)
        
        self.main_layout.addWidget(user_separator)
        self.main_layout.addWidget(self.user_profile_container)
        
        # Set initial layout state
        self.set_collapsed_state()
    
    def setup_iracing_status(self):
        """Setup the iRacing connection status indicator."""
        # iRacing status container
        self.iracing_status_container = QWidget()
        self.iracing_status_layout = QHBoxLayout(self.iracing_status_container)
        self.iracing_status_layout.setContentsMargins(8, 4, 8, 4)
        self.iracing_status_layout.setSpacing(8)
        self.iracing_status_container.setFixedHeight(32)
        
        # Connection status dot
        self.iracing_status_dot = QPushButton()
        self.iracing_status_dot.setFixedSize(12, 12)
        self.iracing_status_dot.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none;
                border-radius: 6px;
            }
        """)
        self.iracing_status_dot.setToolTip("iRacing: Disconnected")
        
        # Status label (only shown when expanded)
        self.iracing_status_label = QLabel("iRacing")
        self.iracing_status_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        
        # Add to layout
        self.iracing_status_layout.addWidget(self.iracing_status_dot)
        self.iracing_status_layout.addWidget(self.iracing_status_label)
        self.iracing_status_layout.addStretch()
        
        # Add to main layout (above user profile separator)
        self.main_layout.addWidget(self.iracing_status_container)
        
        # Add spacing between iRacing status and user profile
        spacing_widget = QWidget()
        spacing_widget.setFixedHeight(8)
        self.main_layout.addWidget(spacing_widget)
        
        # Initialize iRacing connection monitoring
        self.setup_iracing_monitoring()
        
    def setup_iracing_monitoring(self):
        """Setup real-time iRacing connection monitoring."""
        # Defer iRacing monitoring setup until the API is actually ready
        # This prevents early access attempts that fail during startup
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.singleShot(2000, self._setup_iracing_monitoring_delayed)
        
    def _setup_iracing_monitoring_delayed(self):
        """Setup iRacing monitoring after a delay to ensure API is ready."""
        try:
            # Import the global iRacing API access function
            from new_ui import get_global_iracing_api
            
            # Get the global iRacing API instance
            self.iracing_api = get_global_iracing_api()
            
            if self.iracing_api:
                # Register for connection status changes
                self.iracing_api.register_on_connection_changed(self.on_iracing_connection_changed)
                
                # Check initial connection status
                self.update_iracing_status(self.iracing_api.is_connected())
                
                # Set up a timer to periodically check connection status
                self.iracing_check_timer = QTimer()
                self.iracing_check_timer.timeout.connect(self.check_iracing_connection)
                self.iracing_check_timer.start(2000)  # Check every 2 seconds
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info("✅ iRacing connection monitoring initialized")
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug("ℹ️ Global iRacing API not ready yet - monitoring will be retried later")
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Failed to setup iRacing monitoring: {e}")
    
    def check_iracing_connection(self):
        """Periodically check iRacing connection status."""
        try:
            if hasattr(self, 'iracing_api') and self.iracing_api:
                is_connected = self.iracing_api.is_connected()
                self.update_iracing_status(is_connected)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error checking iRacing connection: {e}")
    
    def on_iracing_connection_changed(self, is_connected, session_info):
        """Handle iRacing connection status changes."""
        self.update_iracing_status(is_connected)
        
        import logging
        logger = logging.getLogger(__name__)
        if is_connected:
            logger.info("🏁 iRacing connected - status indicator updated to green")
        else:
            logger.info("🏁 iRacing disconnected - status indicator updated to red")
    
    def update_iracing_status(self, is_connected):
        """Update the iRacing connection status indicator."""
        if not hasattr(self, 'iracing_status_dot'):
            return
            
        if is_connected:
            # Green dot for connected
            self.iracing_status_dot.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    border: none;
                    border-radius: 6px;
                }
            """)
            self.iracing_status_dot.setToolTip("iRacing: Connected")
            if hasattr(self, 'iracing_status_label'):
                self.iracing_status_label.setText("iRacing: Connected")
                self.iracing_status_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-size: 12px;
                        font-weight: 500;
                    }
                """)
        else:
            # Red dot for disconnected
            self.iracing_status_dot.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    border: none;
                    border-radius: 6px;
                }
            """)
            self.iracing_status_dot.setToolTip("iRacing: Disconnected")
            if hasattr(self, 'iracing_status_label'):
                self.iracing_status_label.setText("iRacing: Disconnected")
                self.iracing_status_label.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-size: 12px;
                        font-weight: 500;
                    }
                """)
        
    def set_user_info(self, username: str = "User", avatar_text: str = "U", avatar_url: str = None):
        """Update user profile information."""
        self.user_info_label.setText(username)
        
        # If we have an avatar URL, load and display the image
        if avatar_url and avatar_url != self.current_avatar_url:
            self.load_avatar_from_url(avatar_url)
        else:
            # Fallback to initials
            self.user_avatar_btn.setText(avatar_text)
            self.user_avatar_btn.setIcon(QIcon())  # Clear any existing icon
        
        self.user_avatar_btn.setToolTip(f"{username} - Account Settings")
    
    def load_avatar_from_url(self, url: str):
        """Load and display avatar from URL."""
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
                            # Scale to fit avatar button size
                            avatar_size = 36
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
                            self.user_avatar_btn.setIcon(QIcon(circular_pixmap))
                            self.user_avatar_btn.setText("")  # Clear text
                            self.current_avatar_url = url
                    
                    reply.deleteLater()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    self.user_avatar_btn.setText("U")
            
            reply.finished.connect(on_avatar_downloaded)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading avatar from URL: {e}")
            # Fallback to initials
            self.user_avatar_btn.setText("U")
    
    def update_authentication_state(self, is_authenticated: bool, user_info: dict = None):
        """Update the navigation based on authentication state."""
        import logging
        logger = logging.getLogger(__name__)
        
        # PERFORMANCE: Cache auth state to prevent duplicate calls
        if self._cached_auth_state == is_authenticated and self._cached_user_info == user_info:
            return
        self._cached_auth_state = is_authenticated
        self._cached_user_info = user_info
        
        if is_authenticated and user_info:
            # User is logged in - show their name and initials
            username = user_info.get('name', 'User')
            email = user_info.get('email', '')
            avatar_url = user_info.get('avatar_url')  # Get avatar URL if available
            
            # If no name but has email, use email as display name
            if username == 'User' and email:
                username = email.split('@')[0]  # Use part before @ as display name
            
            # Generate avatar initials from name
            avatar_text = self._generate_avatar_initials(username)
            
            # TEMPORARILY DISABLE AVATAR LOADING TO PREVENT CRASHES
            # Update the display with avatar URL if available
            # self.set_user_info(username, avatar_text, avatar_url)
            # Use initials only to prevent network/image loading crashes
            self.set_user_info(username, avatar_text, None)
            logger.warning("⚠️ TEMPORARILY SKIPPING AVATAR LOADING TO PREVENT CRASHES")
            
        else:
            # User is not logged in - show default
            self.set_user_info("User", "U")
    
    def on_avatar_updated(self):
        """Handle avatar updates specifically - forces refresh of user info."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🔄 Avatar updated - refreshing navigation user info")
        
        # Clear cached user info to force refresh
        self._cached_user_info = None
        
        # Force refresh by calling update_authentication_state with current state
        # This will trigger a fresh fetch of user info including the new avatar
        self.update_authentication_state(self._cached_auth_state, None)
    
    def _generate_avatar_initials(self, name: str) -> str:
        """Generate avatar initials from a name."""
        if not name or name == "User":
            return "U"
        
        # Split name into words and take first letter of each
        words = name.strip().split()
        if len(words) == 0:
            return "U"
        elif len(words) == 1:
            # Single word - take first letter, or first 2 letters if longer
            word = words[0]
            if len(word) >= 2:
                return word[:2].upper()
            else:
                return word[0].upper()
        else:
            # Multiple words - take first letter of first and last word
            return (words[0][0] + words[-1][0]).upper()
        
    def set_collapsed_state(self):
        """Set the collapsed state for all components."""
        # Update button states and alignment
        for button in self.buttons:
            button.set_collapsed(not self.is_expanded)
            
        # Update button container alignment
        if hasattr(self, 'buttons_layout'):
            for button in self.buttons:
                if hasattr(button, 'h_layout'):
                    # Clear the horizontal layout
                    while button.h_layout.count():
                        child = button.h_layout.takeAt(0)
                        if child.widget():
                            child.widget().setParent(None)
                    
                    if self.is_expanded:
                        # Expanded: left-align buttons with margin
                        button.h_layout.setContentsMargins(8, 0, 0, 0)
                        button.h_layout.addWidget(button)
                        button.h_layout.addStretch()
                    else:
                        # Collapsed: center-align buttons with stretches
                        button.h_layout.setContentsMargins(0, 0, 0, 0)
                        button.h_layout.addStretch()
                        button.h_layout.addWidget(button)
                        button.h_layout.addStretch()
            
        # Update iRacing status visibility and layout
        if hasattr(self, 'iracing_status_label') and hasattr(self, 'iracing_status_layout'):
            self.iracing_status_label.setVisible(self.is_expanded)
            
            # Clear and rebuild iRacing status layout based on state
            while self.iracing_status_layout.count():
                child = self.iracing_status_layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
            
            if not self.is_expanded:
                # Collapsed: center the dot only
                self.iracing_status_layout.setContentsMargins(0, 4, 0, 4)
                self.iracing_status_layout.addStretch()
                self.iracing_status_layout.addWidget(self.iracing_status_dot)
                self.iracing_status_layout.addStretch()
            else:
                # Expanded: align left with status label
                self.iracing_status_layout.setContentsMargins(8, 4, 8, 4)
                self.iracing_status_layout.addWidget(self.iracing_status_dot)
                self.iracing_status_layout.addWidget(self.iracing_status_label)
                self.iracing_status_layout.addStretch()

        # Update user profile visibility and layout
        if hasattr(self, 'user_info_label') and hasattr(self, 'user_profile_layout'):
            self.user_info_label.setVisible(self.is_expanded)
            
            # Clear and rebuild layout based on state
            # Remove all widgets from layout
            while self.user_profile_layout.count():
                child = self.user_profile_layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
            
            if not self.is_expanded:
                # Collapsed: center the avatar
                self.user_profile_layout.setContentsMargins(0, 8, 0, 8)
                self.user_profile_layout.addStretch()
                self.user_profile_layout.addWidget(self.user_avatar_btn)
                self.user_profile_layout.addStretch()
            else:
                # Expanded: align left with user info
                self.user_profile_layout.setContentsMargins(8, 8, 8, 8)
                self.user_profile_layout.addWidget(self.user_avatar_btn)
                self.user_profile_layout.addWidget(self.user_info_label)
                self.user_profile_layout.addStretch()
            
        # Update toggle button
        if self.is_expanded:
            self.toggle_btn.setText("◀")
        else:
            self.toggle_btn.setText("☰")
            
    def set_active_page(self, page: str):
        """Set the active page button."""
        for button in self.buttons:
            button.setChecked(button.page == page)
    
    def closeEvent(self, event):
        """Clean up when the navigation widget is closed."""
        try:
            # Stop the iRacing connection check timer
            if hasattr(self, 'iracing_check_timer') and self.iracing_check_timer:
                self.iracing_check_timer.stop()
                
            # Unregister from iRacing callbacks to prevent memory leaks
            if hasattr(self, 'iracing_api') and self.iracing_api:
                try:
                    # Note: The SimpleIRacingAPI should have methods to unregister callbacks
                    # For now, we'll just clear the reference
                    pass
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error cleaning up iRacing callbacks: {e}")
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during navigation cleanup: {e}")
            
        super().closeEvent(event)