"""Online Users Sidebar Widget

This module provides a collapsible sidebar for displaying online users,
similar to Discord's user list functionality. Users can see who's online
and eventually will be able to chat with each other.
"""

import logging
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QButtonGroup, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor

logger = logging.getLogger(__name__)


class OnlineUserItem(QWidget):
    """Individual user item widget for the online users list."""
    
    user_clicked = pyqtSignal(dict)  # Emits user data when clicked
    
    def __init__(self, user_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user item UI."""
        self.setFixedHeight(48)
        self.setStyleSheet("""
            OnlineUserItem {
                background-color: transparent;
                border-radius: 6px;
                margin: 2px 4px;
            }
            OnlineUserItem:hover {
                background-color: rgba(79, 84, 92, 0.16);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(6)
        
        # Avatar container with online status indicator
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(32, 32)
        avatar_container_layout = QHBoxLayout(self.avatar_container)
        avatar_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # User avatar (circle with initials)
        self.avatar_label = self.create_avatar()
        avatar_container_layout.addWidget(self.avatar_label)
        
        # Online status dot on avatar (positioned absolutely)
        self.avatar_status_dot = QLabel(self.avatar_container)
        self.avatar_status_dot.setFixedSize(10, 10)
        is_online = self.user_data.get('is_online', False)
        dot_color = "#3ba55c" if is_online else "#747f8d"
        self.avatar_status_dot.setStyleSheet(f"""
            QLabel {{
                background-color: {dot_color};
                border: 2px solid #252525;
                border-radius: 5px;
            }}
        """)
        self.avatar_status_dot.move(22, 22)  # Position at bottom-right of avatar
        
        layout.addWidget(self.avatar_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # User info container
        user_info = QWidget()
        user_info_layout = QVBoxLayout(user_info)
        user_info_layout.setContentsMargins(0, 2, 0, 2)
        user_info_layout.setSpacing(2)
        
        # Username (show display_name if available, fallback to username)
        display_name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'Unknown User')
        self.username_label = QLabel(display_name)
        self.username_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        user_info_layout.addWidget(self.username_label)
        
        # Status
        status = self.user_data.get('status', 'Online' if is_online else 'Offline')
        self.status_label = QLabel(status)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
            }
        """)
        user_info_layout.addWidget(self.status_label)
        
        layout.addWidget(user_info, 1)
        
        # Legacy online indicator (hidden since we use avatar dot now)
        self.online_indicator = QLabel()
        self.online_indicator.setFixedSize(0, 0)
        self.online_indicator.setVisible(False)
        layout.addWidget(self.online_indicator)
        
        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def create_avatar(self) -> QLabel:
        """Create a circular avatar with user initials."""
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        
        # Create circular avatar with initials
        name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'U')
        initials = ''.join([word[0].upper() for word in name.split()][:2])
        
        # Create pixmap for avatar 
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background
        colors = ['#7289da', '#99aab5', '#2c2f33', '#23272a', '#f04747', '#faa61a']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 32, 32)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        painter.setFont(painter.font())
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        
        avatar_label.setPixmap(pixmap)
        avatar_label.setStyleSheet("border-radius: 16px;")
        
        return avatar_label
    
    def mousePressEvent(self, event):
        """Handle mouse press for user selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.user_clicked.emit(self.user_data)
        super().mousePressEvent(event)


class OnlineUsersSidebar(QWidget):
    """Collapsible sidebar for displaying online users."""
    
    # Signals
    sidebar_toggled = pyqtSignal(bool)  # True when expanded, False when collapsed
    user_selected = pyqtSignal(dict)  # Emits user data when user is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State tracking
        self.is_expanded = False
        self.is_animating = False
        
        # Dimensions
        self.collapsed_width = 44
        self.expanded_width = 180
        
        # Animation
        self.animation = None
        self.animation_duration = 300
        
        # User data
        self.all_users = []
        self.friends_list = []
        self.current_user_id = None
        self.user_widgets = []
        
        # Setup UI
        self.setup_ui()
        
        # Load current user immediately for instant display
        self.load_current_user_instantly()
        
        # Load other users asynchronously
        QTimer.singleShot(100, self.load_users_from_database)
        
        # Auto-refresh timer for online status and user data
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_users_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self):
        """Setup the main UI structure."""
        self.setFixedWidth(self.collapsed_width)
        self.setMaximumWidth(self.collapsed_width)
        self.setMinimumWidth(self.collapsed_width)
        self.setProperty("class", "OnlineUsersSidebar")
        self.setStyleSheet("""
            QWidget[class="OnlineUsersSidebar"] {
                background-color: #252525 !important;
                border-left: 1px solid #202225 !important;
                margin: 0px !important;
                padding: 0px !important;
            }
        """)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 8, 0, 8)
        self.main_layout.setSpacing(4)
        
        # Header with toggle button
        self.create_header()
        
        # Add Friend search bar (shown when expanded)
        self.create_add_friend_bar()
        
        # Separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #40444b; margin: 6px 0px;")
        separator.setFixedHeight(1)
        self.main_layout.addWidget(separator)
        
        # Users list container
        self.create_users_container()
        
        # Footer with user count
        self.create_footer()
    
    def create_header(self):
        """Create the header with toggle button and title."""
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(2, 4, 2, 4)
        header_layout.setSpacing(8)
        
        # Toggle button
        self.toggle_btn = QPushButton("👥")
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #40444b;
                border: none;
                border-radius: 16px;
                color: #dcddde;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5865f2;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Title (hidden when collapsed)
        self.title_label = QLabel("Online Users")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.title_label.setVisible(False)
        header_layout.addWidget(self.title_label, 1)
        
        self.main_layout.addWidget(header_container)
    
    def create_add_friend_bar(self):
        """Create the 'Add a Friend' search bar."""
        self.add_friend_container = QWidget()
        self.add_friend_container.setVisible(False)  # Hidden when collapsed
        
        add_friend_layout = QVBoxLayout(self.add_friend_container)
        add_friend_layout.setContentsMargins(8, 4, 8, 4)
        add_friend_layout.setSpacing(2)
        
        # Search input
        self.friend_search_input = QLineEdit()
        self.update_add_friend_ui_state()  # Set initial state based on auth
        self.friend_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #40444b;
                border: 1px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                color: #dcddde;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #5865f2;
                background-color: #252525;
            }
            QLineEdit::placeholder {
                color: #72767d;
            }
            QLineEdit:disabled {
                background-color: #252525;
                color: #72767d;
                border-color: #252525;
            }
        """)
        self.friend_search_input.returnPressed.connect(self.send_friend_request_by_username)
        add_friend_layout.addWidget(self.friend_search_input)
        
        # Add friend button (small, inline)
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        
        self.add_friend_btn = QPushButton("Send Request")
        self.add_friend_btn.setFixedHeight(24)
        self.add_friend_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
                padding: 0px 12px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
            QPushButton:disabled {
                background-color: #4f545c;
                color: #72767d;
            }
        """)
        self.add_friend_btn.clicked.connect(self.send_friend_request_by_username)
        
        button_layout.addStretch()
        button_layout.addWidget(self.add_friend_btn)
        add_friend_layout.addWidget(button_container)
        
        self.main_layout.addWidget(self.add_friend_container)
    
    def create_users_container(self):
        """Create the scrollable users list container."""
        # Scroll area for users
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2e3338;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #5865f2;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Users list widget
        self.users_widget = QWidget()
        self.users_layout = QVBoxLayout(self.users_widget)
        self.users_layout.setContentsMargins(0, 4, 0, 4)
        self.users_layout.setSpacing(4)
        self.users_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        self.scroll_area.setWidget(self.users_widget)
        self.main_layout.addWidget(self.scroll_area, 1)
    
    def create_footer(self):
        """Create the footer with user count."""
        self.footer_container = QWidget()
        footer_layout = QHBoxLayout(self.footer_container)
        footer_layout.setContentsMargins(4, 4, 4, 4)
        
        # User count label
        self.user_count_label = QLabel("0")
        self.user_count_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.user_count_label.setVisible(False)
        footer_layout.addWidget(self.user_count_label)
        
        # User count icon (always visible)
        self.count_icon = QLabel("0")
        self.count_icon.setFixedSize(20, 20)
        self.count_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_icon.setStyleSheet("""
            QLabel {
                background-color: #5865f2;
                color: white;
                font-size: 9px;
                font-weight: bold;
                border-radius: 10px;
            }
        """)
        footer_layout.addWidget(self.count_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.main_layout.addWidget(self.footer_container)
    
    def toggle_sidebar(self):
        """Toggle between collapsed and expanded states."""
        if self.is_animating:
            return
        
        target_width = self.expanded_width if not self.is_expanded else self.collapsed_width
        self.animate_to_width(target_width)
    
    def animate_to_width(self, target_width: int):
        """Animate the sidebar to target width."""
        if self.animation:
            self.animation.stop()
        
        self.is_animating = True
        
        # Create width animation
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        
        # Connect animation finished
        self.animation.finished.connect(self.on_animation_finished)
        
        # Update state and UI elements during animation
        if target_width == self.expanded_width:
            self.is_expanded = True
            # Show elements immediately for smooth transition
            self.title_label.setVisible(True)
            self.user_count_label.setVisible(True)
            self.add_friend_container.setVisible(True)
            self.update_toggle_button()
        
        self.animation.start()
    
    def on_animation_finished(self):
        """Handle animation completion."""
        self.is_animating = False
        
        # Update fixed width
        if self.animation:
            final_width = self.animation.endValue()
            self.setFixedWidth(final_width)
            self.setMaximumWidth(final_width)
            self.setMinimumWidth(final_width)
            
            # Update UI visibility based on final state
            if final_width == self.collapsed_width:
                self.is_expanded = False
                self.title_label.setVisible(False)
                self.user_count_label.setVisible(False)
                self.add_friend_container.setVisible(False)
            
            self.update_toggle_button()
            
            # Refresh user list after animation completes to show proper layout
            self.refresh_users_list()
            
            # Force layout update
            self.updateGeometry()
            if self.parent():
                self.parent().update()
        
        # Emit signal
        self.sidebar_toggled.emit(self.is_expanded)
    
    def update_toggle_button(self):
        """Update the toggle button appearance."""
        if self.is_expanded:
            self.toggle_btn.setText("▶")
        else:
            self.toggle_btn.setText("👥")
    
    def get_current_user_id(self) -> Optional[str]:
        """Get the current user's ID."""
        try:
            from ..auth.user_manager import get_current_user
            user = get_current_user()
            if user and user.is_authenticated:
                return user.id
        except Exception as e:
            logger.warning(f"Error getting current user: {e}")
        return None
    
    def load_current_user_instantly(self):
        """Load current user immediately for instant display."""
        try:
            self.current_user_id = self.get_current_user_id()
            if self.current_user_id:
                # Add current user instantly
                current_user_data = {
                    'user_id': self.current_user_id,
                    'username': 'currentuser',
                    'display_name': 'You',
                    'avatar_url': None,
                    'is_friend': False,
                    'is_online': True,
                    'status': 'Online'
                }
                self.all_users = [current_user_data]
                self.refresh_users_list()
                logger.info("✅ Current user loaded instantly")
            else:
                logger.warning("No authenticated user found")
        except Exception as e:
            logger.error(f"Error loading current user instantly: {e}")
    
    def load_users_from_database(self):
        """Load all users from database with friends prioritized."""
        try:
            # Get current user ID if not already set
            if not self.current_user_id:
                self.current_user_id = self.get_current_user_id()
                if not self.current_user_id:
                    logger.warning("No authenticated user found")
                    return
            
            # Import database managers
            from ..social.friends_manager import FriendsManager
            from ..social.user_manager import EnhancedUserManager
            
            # Get friends list (non-blocking)
            friends_manager = FriendsManager()
            self.friends_list = friends_manager.get_friends_list(self.current_user_id, include_online_status=True)
            
            # Get all users from database (optimized query)
            user_manager = EnhancedUserManager()
            response = user_manager.client.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, last_active"
            ).execute()
            
            # Start with current user (already loaded)
            current_user_in_list = False
            friends_ids = [friend['friend_id'] for friend in self.friends_list]
            
            # Process all users except current user (already shown)
            for user in (response.data or []):
                is_current_user = user['user_id'] == self.current_user_id
                
                if is_current_user:
                    current_user_in_list = True
                    continue  # Skip current user as it's already loaded
                
                user_data = {
                    'user_id': user['user_id'],
                    'username': user.get('username', 'Unknown'),
                    'display_name': user.get('display_name'),
                    'avatar_url': user.get('avatar_url'),
                    'is_friend': user['user_id'] in friends_ids,
                    'is_online': self._simulate_online_status(user['user_id']),
                    'status': self._get_user_status(user['user_id'], user.get('last_active'))
                }
                self.all_users.append(user_data)
            
            # Update the UI with new users
            self.refresh_users_list()
            logger.info(f"✅ Loaded {len(self.all_users)} users from database")
            
        except Exception as e:
            logger.error(f"Error loading users from database: {e}")
            # Don't call load_fallback_users() as current user is already shown
    
    def load_fallback_users(self):
        """Load fallback users when database is unavailable."""
        # Only include current user if authenticated
        fallback_users = []
        
        if self.current_user_id:
            # Add current user with real iRacing status
            fallback_users.append({
                'user_id': self.current_user_id,
                'username': 'currentuser',
                'display_name': 'You',
                'avatar_url': None,
                'is_friend': False,  # Can't be friends with yourself
                'is_online': True,   # Always online if authenticated
                'last_active': None
            })
        
        # Set dynamic status for each user
        for user in fallback_users:
            user_id = user.get('user_id')
            last_active = user.get('last_active', '')
            user['status'] = self._get_user_status(user_id, last_active)
        
        self.all_users = fallback_users
        self.refresh_users_list()
    
    def _simulate_online_status(self, user_id: str) -> bool:
        """Simulate online status until real-time presence is implemented."""
        # Simple hash-based simulation for consistent results
        return hash(user_id) % 3 != 0  # ~67% online rate
    
    def _get_user_status(self, user_id: str, last_active: str) -> str:
        """Get user status based on activity and iRacing telemetry."""
        # Check if this is the current user and get their iRacing status
        if user_id == self.current_user_id:
            iracing_status = self._get_current_user_iracing_status()
            if iracing_status:
                return iracing_status
        
        # For other users, check their last activity or mock status for now
        # TODO: Implement user activity tracking via database
        from datetime import datetime, timedelta
        try:
            if last_active:
                # Parse last active time and determine if user is online
                # This would come from actual user session tracking
                return "Online"  # Placeholder - would be based on actual session data
        except:
            pass
        
        # Fallback to mock status for demonstration
        statuses = ['Online', 'Racing - Silverstone', 'Practicing', 'In Lobby', 'Watching Replay', 'Offline']
        return statuses[hash(user_id) % len(statuses)]
    
    def _get_current_user_iracing_status(self) -> str:
        """Get the current user's iRacing status from telemetry."""
        try:
            # Try to get global iRacing API
            global_iracing_api = None
            
            # Look for global iRacing API in different ways
            try:
                from PyQt6.QtWidgets import QApplication
                for widget in QApplication.topLevelWidgets():
                    if hasattr(widget, 'get_shared_iracing_api'):
                        global_iracing_api = widget.get_shared_iracing_api()
                        break
                    elif hasattr(widget, 'global_iracing_api'):
                        global_iracing_api = widget.global_iracing_api
                        break
            except:
                pass
            
            # Alternative: try to import and get global API
            if not global_iracing_api:
                try:
                    import new_ui
                    if hasattr(new_ui, 'get_global_iracing_api'):
                        global_iracing_api = new_ui.get_global_iracing_api()
                except:
                    pass
            
            if global_iracing_api and hasattr(global_iracing_api, 'ir') and global_iracing_api.ir:
                ir = global_iracing_api.ir
                if ir and ir.is_connected:
                    # Get current session info
                    try:
                        weekend_info = ir['WeekendInfo']
                        driver_info = ir['DriverInfo']
                        session_info = ir['SessionInfo']
                        
                        track_name = weekend_info.get('TrackDisplayName', 'Unknown Track')
                        
                        # Get car name from player's driver info
                        drivers = driver_info.get('Drivers', [])
                        player_car_idx = driver_info.get('DriverCarIdx', 0)
                        car_name = 'Unknown Car'
                        
                        if 0 <= player_car_idx < len(drivers):
                            car_name = drivers[player_car_idx].get('CarScreenName', 'Unknown Car')
                        
                        # Get session type
                        sessions = session_info.get('Sessions', [])
                        current_session_num = session_info.get('CurrentSessionNum', 0)
                        session_type = 'Practice'
                        
                        if 0 <= current_session_num < len(sessions):
                            session_type = sessions[current_session_num].get('SessionType', 'Practice')
                        
                        # Format the status based on session type
                        if session_type == 'Race':
                            return f"Racing - {track_name}"
                        elif session_type == 'Practice':
                            return f"Practicing - {track_name}"
                        elif session_type == 'Qualify':
                            return f"Qualifying - {track_name}"
                        elif session_type == 'Warmup':
                            return f"Warming up - {track_name}"
                        else:
                            return f"In session - {track_name}"
                            
                    except Exception as e:
                        logger.debug(f"Error getting detailed iRacing session info: {e}")
                        return "In iRacing"
                else:
                    # Not connected to iRacing but TrackPro is running
                    return "Online"
            else:
                # No iRacing API available
                return "Online"
                
        except Exception as e:
            logger.debug(f"Error getting iRacing status: {e}")
            return "Online"
    
    def is_user_authenticated(self) -> bool:
        """Check if the current user is authenticated."""
        try:
            from ..auth.user_manager import get_current_user
            user = get_current_user()
            return user and user.is_authenticated and user.name != "Anonymous User"
        except Exception as e:
            logger.warning(f"Failed to check authentication status: {e}")
            return False
    
    def get_current_user_id(self) -> Optional[str]:
        """Get the current authenticated user's ID."""
        try:
            from ..auth.user_manager import get_current_user
            user = get_current_user()
            if user and user.is_authenticated and user.name != "Anonymous User":
                return user.id
        except Exception as e:
            logger.warning(f"Failed to get current user ID: {e}")
        return None
    
    def update_add_friend_ui_state(self):
        """Update the Add Friend UI state based on authentication status."""
        is_authenticated = self.is_user_authenticated()
        
        if hasattr(self, 'friend_search_input'):
            self.friend_search_input.setEnabled(is_authenticated)
            
            if is_authenticated:
                self.friend_search_input.setPlaceholderText("Add a friend by username...")
            else:
                self.friend_search_input.setPlaceholderText("Sign in to add friends")
    
    def send_friend_request_by_username(self):
        """Send a friend request using the entered username."""
        username = self.friend_search_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Error", "Please enter a username.")
            return
        
        # Check if user is authenticated
        if not self.is_user_authenticated():
            QMessageBox.warning(self, "Authentication Required", 
                              "You must be signed in to send friend requests.\n\n"
                              "Please sign in to your account first.")
            return
        
        try:
            # Import the friends manager
            from ..social.friends_manager import FriendsManager
            
            # First, get the user ID by username
            friends_manager = FriendsManager()
            response = friends_manager.client.from_("user_profiles").select(
                "user_id, username, display_name"
            ).eq("username", username).single().execute()
            
            if not response.data:
                QMessageBox.warning(self, "Error", f"User '{username}' not found.")
                self.friend_search_input.clear()
                return
            
            target_user = response.data
            target_user_id = target_user['user_id']
            
            # Check if trying to add themselves
            if target_user_id == self.current_user_id:
                QMessageBox.warning(self, "Error", "You cannot send a friend request to yourself.")
                self.friend_search_input.clear()
                return
            
            # Send the friend request
            result = friends_manager.send_friend_request(self.current_user_id, target_user_id)
            
            if result.get('success', False):
                display_name = target_user.get('display_name') or username
                QMessageBox.information(self, "Success", f"Friend request sent to {display_name}!")
                self.friend_search_input.clear()
                
                # Refresh the users list to reflect any changes
                self.refresh_users_data()
            else:
                error_message = result.get('message', 'Failed to send friend request.')
                QMessageBox.warning(self, "Error", error_message)
                
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while sending the friend request.")
        
        # Clear the input field
        self.friend_search_input.clear()
    
    def refresh_users_list(self):
        """Refresh the users list display with friends prioritized."""
        # Clear existing widgets from layout completely
        while self.users_layout.count():
            child = self.users_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # Clear our widget tracking
        self.user_widgets.clear()
        
        # Sort users: friends first (by online status), then others (by online status)
        sorted_users = sorted(
            self.all_users,
            key=lambda u: (
                not u.get('is_friend', False),  # Friends first (False sorts before True)
                not u.get('is_online', False),  # Online users first within each group
                u.get('display_name', '').lower() or u.get('username', '').lower()  # Alphabetical by name
            )
        )
        
        # Add user widgets
        for user_data in sorted_users:
            user_widget = OnlineUserItem(user_data)
            user_widget.user_clicked.connect(self.on_user_selected)
            self.user_widgets.append(user_widget)
            
            # Create container for centering when collapsed
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            
            if not self.is_expanded:
                # When collapsed, center the avatar container (which includes the status dot)
                container_layout.addStretch()
                container_layout.addWidget(user_widget.avatar_container)
                container_layout.addStretch()
                # Hide text elements
                user_widget.username_label.setVisible(False)
                user_widget.status_label.setVisible(False)
                user_widget.online_indicator.setVisible(False)
            else:
                # When expanded, show full item
                container_layout.addWidget(user_widget)
            
            self.users_layout.addWidget(container)
        
        # Update user count - show online users count
        online_count = len([u for u in self.all_users if u.get('is_online', False)])
        total_count = len(self.all_users)
        self.user_count_label.setText(f"{online_count}/{total_count} online")
        self.count_icon.setText(str(online_count))
    
    def refresh_users_data(self):
        """Refresh users data including online status from the backend."""
        logger.debug("Refreshing users data...")
        # Only refresh if we have users loaded
        if self.all_users:
            self.load_users_from_database()
        self.update_add_friend_ui_state()  # Update UI based on auth status
    
    def on_user_selected(self, user_data: Dict[str, Any]):
        """Handle user selection - show user profile popup."""
        user_name = user_data.get('display_name') or user_data.get('username', 'Unknown User')
        logger.info(f"User selected: {user_name}")
        
        # Show user profile popup
        self.show_user_profile_popup(user_data)
        
        # Still emit the signal for other components that might need it
        self.user_selected.emit(user_data)
    
    def show_user_profile_popup(self, user_data: Dict[str, Any]):
        """Show the user profile popup dialog."""
        try:
            from .user_profile_popup import UserProfilePopup
            
            # Pass current_user_id even if None - popup will handle authentication state
            popup = UserProfilePopup(user_data, self.current_user_id, self)
            popup.view_profile_requested.connect(self.on_view_profile_requested)
            popup.friend_request_sent.connect(self.on_friend_request_sent)
            popup.show()
            
        except Exception as e:
            logger.error(f"Error showing user profile popup: {e}")
    
    def on_view_profile_requested(self, user_id: str):
        """Handle view profile request from popup."""
        logger.info(f"View profile requested for user: {user_id}")
        # TODO: Navigate to user profile page
        # This would typically emit a signal to the main window to navigate
        # to the user's profile page
    
    def on_friend_request_sent(self, user_id: str):
        """Handle friend request sent from popup."""
        logger.info(f"Friend request sent to user: {user_id}")
        # Refresh the users list to update friend status
        self.refresh_users_data()
    
    def add_user(self, user_data: Dict[str, Any]):
        """Add a new user to the list."""
        if user_data not in self.all_users:
            self.all_users.append(user_data)
            self.refresh_users_list()
    
    def remove_user(self, user_id: str):
        """Remove a user from the list."""
        self.all_users = [user for user in self.all_users if user.get('user_id') != user_id]
        self.refresh_users_list()
    
    def update_user_status(self, user_id: str, status: str, is_online: bool = None):
        """Update a user's status and online state."""
        for user in self.all_users:
            if user.get('user_id') == user_id:
                user['status'] = status
                if is_online is not None:
                    user['is_online'] = is_online
                break
        self.refresh_users_list()