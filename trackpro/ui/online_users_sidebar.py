"""Online Users Sidebar Widget

This module provides a collapsible sidebar for displaying online users,
similar to Discord's user list functionality. Users can see who's online
and eventually will be able to chat with each other.
"""

import logging
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QButtonGroup, QLineEdit, QMessageBox,
    QMenu, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QParallelAnimationGroup, QSize, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QFont, QIcon
from PyQt6.QtGui import QPainterPath
from .avatar_manager import AvatarManager

logger = logging.getLogger(__name__)


class OnlineUserItem(QWidget):
    """Individual user item widget for the online users list."""
    
    user_clicked = pyqtSignal(dict)  # Emits user data when clicked
    private_message_requested = pyqtSignal(dict)  # Emits user data for private message
    
    def __init__(self, user_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.user_data = user_data
        logger.debug(f"Creating OnlineUserItem for user: {user_data.get('display_name', 'Unknown')}")
        logger.debug(f"User data: {user_data}")
        self.setup_ui()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def setup_ui(self):
        """Setup the user item UI."""
        logger.debug(f"Setting up UI for user: {self.user_data.get('display_name', 'Unknown')}")
        
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
        # Keep a reference for compact/expanded toggling
        self.main_layout = layout
        
        # Avatar container with online status indicator
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(32, 32)
        avatar_container_layout = QHBoxLayout(self.avatar_container)
        avatar_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # User avatar (circle with initials)
        logger.debug(f"Creating avatar for user: {self.user_data.get('display_name', 'Unknown')}")
        self.avatar_label = self.create_avatar()
        avatar_container_layout.addWidget(self.avatar_label)
        logger.debug(f"Avatar created and added to container for user: {self.user_data.get('display_name', 'Unknown')}")

        # Ensure the avatar has no background/border that could cover the pixmap
        try:
            self.avatar_label.setStyleSheet("QLabel { background: transparent; border: none; }")
        except Exception:
            pass
        
        # Online status dot on avatar (positioned absolutely)
        self.avatar_status_dot = QLabel(self.avatar_container)
        self.avatar_status_dot.setFixedSize(10, 10)
        is_online = self.user_data.get('is_online', False)
        dot_color = "#3ba55c" if is_online else "#747f8d"
        logger.debug(f"🎯 Setting online status dot for {self.user_data.get('display_name', 'Unknown')}: is_online={is_online}, color={dot_color}")
        self.avatar_status_dot.setStyleSheet(f"""
            QLabel {{
                background-color: {dot_color};
                border: 2px solid #252525;
                border-radius: 5px;
            }}
        """)
        self.avatar_status_dot.move(22, 22)  # Position at bottom-right of avatar
        
        # Holder for optional glow effect
        self._glow_effect = None

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

    def set_unread_glow(self, enabled: bool) -> None:
        """Toggle yellow glow around the avatar for unread DMs."""
        try:
            if enabled:
                if self._glow_effect is None:
                    eff = QGraphicsDropShadowEffect(self.avatar_container)
                    eff.setBlurRadius(28)
                    eff.setOffset(0, 0)
                    eff.setColor(QColor("#f1c40f"))
                    self.avatar_container.setGraphicsEffect(eff)
                    self._glow_effect = eff
            else:
                if self._glow_effect is not None:
                    self.avatar_container.setGraphicsEffect(None)
                    self._glow_effect = None
        except Exception:
            pass

    def set_compact_mode(self, is_compact: bool) -> None:
        """Toggle compact (collapsed) mode: hide text and center avatar.

        This avoids re-parenting child widgets which caused layout glitches.
        """
        # Lazily create spacers
        if not hasattr(self, '_left_spacer'):
            self._left_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        if not hasattr(self, '_right_spacer'):
            self._right_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Ensure labels exist
        has_labels = hasattr(self, 'username_label') and hasattr(self, 'status_label')
        if has_labels:
            self.username_label.setVisible(not is_compact)
            self.status_label.setVisible(not is_compact)

        # Remove spacers if already present to avoid duplicates
        # Note: removeItem is safe even if the item is not currently in the layout
        self.main_layout.removeItem(getattr(self, '_left_spacer', None))
        self.main_layout.removeItem(getattr(self, '_right_spacer', None))

        if is_compact:
            # Center the avatar within the row
            self.main_layout.insertItem(0, self._left_spacer)
            # Ensure avatar container stays sized tightly
            self.avatar_container.setFixedSize(32, 32)
            self.main_layout.setAlignment(self.avatar_container, Qt.AlignmentFlag.AlignHCenter)
            self.main_layout.addItem(self._right_spacer)
        else:
            # Expanded mode: avatar on the left, text visible
            self.main_layout.setAlignment(self.avatar_container, Qt.AlignmentFlag.AlignLeft)
    
    def refresh_online_status(self):
        """Refresh the online status dot based on current user data."""
        is_online = self.user_data.get('is_online', False)
        dot_color = "#3ba55c" if is_online else "#747f8d"
        logger.debug(f"🔄 Refreshing online status dot for {self.user_data.get('display_name', 'Unknown')}: is_online={is_online}, color={dot_color}")
        self.avatar_status_dot.setStyleSheet(f"""
            QLabel {{
                background-color: {dot_color};
                border: 2px solid #252525;
                border-radius: 5px;
            }}
        """)
    
    def refresh_avatar(self):
        """Refresh the avatar display with current user data."""
        try:
            logger.debug(f"🔄 Refreshing avatar for user: {self.user_data.get('display_name', 'Unknown')}")
            
            # Get fresh avatar URL
            avatar_url = self.user_data.get('avatar_url')
            name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'U')
            
            if avatar_url:
                # Load avatar from URL
                self.load_avatar_from_url(avatar_url, 32, self.avatar_label)
                logger.debug(f"✅ Started loading avatar from URL: {avatar_url}")
            else:
                # Create fallback avatar with initials
                fallback_avatar = self.create_fallback_avatar(name)
                self.avatar_label.setPixmap(fallback_avatar.pixmap())
                logger.debug(f"✅ Updated fallback avatar for user: {name}")
                
        except Exception as e:
            logger.error(f"❌ Error refreshing avatar: {e}")
    
    def create_avatar(self) -> QLabel:
        """Create a circular avatar with user profile image or initials."""
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        
        # Get user name for avatar
        name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'U')
        logger.debug(f"Creating avatar for user: {name}")
        
        # Unified avatar setting
        # Let the pixmap draw without label background interference
        try:
            avatar_label.setStyleSheet("QLabel { background: transparent; border: none; }")
        except Exception:
            pass
        AvatarManager.instance().set_label_avatar(avatar_label, self.user_data.get('avatar_url'), name, size=32)
        return avatar_label
    
    def load_avatar_from_url(self, url: str, size: int = 32, avatar_label: QLabel = None) -> QPixmap:
        """Deprecated: use AvatarManager via create_avatar/set_label_avatar instead."""
        if avatar_label is None:
            return QPixmap()
        name = self.user_data.get('display_name') or self.user_data.get('username') or self.user_data.get('name', 'User')
        AvatarManager.instance().set_label_avatar(avatar_label, url, name, size=size)
        return QPixmap()
    
    def make_circular_pixmap(self, pixmap: QPixmap, size: int) -> QPixmap:
        """Make a pixmap circular with a border."""
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create circular path
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Draw the image
        painter.drawPixmap(0, 0, size, size, pixmap)
        
        # Draw border
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(1, 1, size-2, size-2)
        
        painter.end()
        return circular_pixmap
    
    def create_fallback_avatar(self, name: str) -> QLabel:
        """Create a fallback avatar with user initials."""
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        
        # Generate initials
        initials = self._generate_initials(name)
        
        # Create pixmap for avatar 
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 32, 32)
        
        # Draw initials
        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        
        # Center the text
        text_rect = painter.boundingRect(0, 0, 32, 32, Qt.AlignmentFlag.AlignCenter, initials)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        avatar_label.setPixmap(pixmap)
        logger.debug(f"Created fallback avatar with initials: {initials}")
        return avatar_label
    

    

    

    
    def _generate_initials(self, name: str) -> str:
        """Generate initials from a name."""
        logger.debug(f"Generating initials for name: '{name}'")
        
        if not name or name == 'Unknown User':
            return "U"
        
        # Split by spaces and get first letter of each word
        words = name.strip().split()
        logger.debug(f"Split words: {words}")
        
        if len(words) == 1:
            # Single word - take first two letters if available
            word = words[0]
            if len(word) >= 2:
                result = word[:2].upper()
                logger.debug(f"Single word '{word}' -> '{result}'")
                return result
            else:
                result = word.upper()
                logger.debug(f"Single word '{word}' -> '{result}'")
                return result
        else:
            # Multiple words - take first letter of first word and first letter of last word
            first_initial = words[0][0].upper() if words[0] else ""
            last_initial = words[-1][0].upper() if words[-1] and words[-1] != words[0] else ""
            
            logger.debug(f"First word: '{words[0]}', Last word: '{words[-1]}'")
            logger.debug(f"First initial: '{first_initial}', Last initial: '{last_initial}'")
            
            # If first and last are the same, just return first initial
            if first_initial == last_initial:
                logger.debug(f"First and last initials are the same, returning: '{first_initial}'")
                return first_initial
            
            result = first_initial + last_initial
            logger.debug(f"Combined initials: '{result}'")
            return result
    
    def mousePressEvent(self, event):
        """Handle mouse press for user selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.user_clicked.emit(self.user_data)
        super().mousePressEvent(event)

    def show_context_menu(self, position):
        """Show context menu on right-click."""
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #2f3136;
                border: 1px solid #202225;
                border-radius: 4px;
                padding: 4px 0px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 8px 16px;
                color: #dcddde;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #5865f2;
            }
            QMenu::separator {
                height: 1px;
                background-color: #40444b;
                margin: 4px 8px;
            }
        """)
        
        # Separator (kept even without DM for visual grouping)
        context_menu.addSeparator()
        
        # View Profile action
        view_profile_action = QAction("View Profile", self)
        view_profile_action.triggered.connect(self.on_view_profile_requested)
        context_menu.addAction(view_profile_action)
        
        # Send Friend Request action
        friend_request_action = QAction("Send Friend Request", self)
        friend_request_action.triggered.connect(self.on_friend_request_requested)
        context_menu.addAction(friend_request_action)
        
        # Show menu at cursor position
        context_menu.exec(self.mapToGlobal(position))
    
    def on_private_message_requested(self):
        """Handle private message request."""
        # Try to find a widget with start_direct_private_message method
        # Start from current widget and traverse up the parent hierarchy
        current_widget = self
        while current_widget is not None:
            if hasattr(current_widget, 'start_direct_private_message'):
                current_widget.start_direct_private_message(self.user_data)
                return
            
            # Get the parent widget safely
            try:
                current_widget = current_widget.parent()
            except Exception as e:
                logger.error(f"Error traversing parent hierarchy: {e}")
                break
        
        # If we can't find the method in parent hierarchy, try to find the main window
        # and look for the community page
        try:
            # Find the main window
            main_window = self.window()
            if main_window and hasattr(main_window, 'content_stack'):
                # Look for CommunityPage in the content stack
                for i in range(main_window.content_stack.count()):
                    widget = main_window.content_stack.widget(i)
                    if hasattr(widget, 'start_direct_private_message'):
                        widget.start_direct_private_message(self.user_data)
                        return
        except Exception as e:
            logger.error(f"Error finding main window or community page: {e}")
        
        # Fallback to emitting signal if direct method not found
        self.private_message_requested.emit(self.user_data)
    
    def on_view_profile_requested(self):
        """Handle view profile request."""
        try:
            user_id = self.user_data.get('user_id')
            if not user_id:
                self.user_clicked.emit(self.user_data)
                return
            main_window = self.window()
            if not main_window or not hasattr(main_window, 'content_stack'):
                self.user_clicked.emit(self.user_data)
                return
            page_key = f"public_profile:{user_id}"
            if hasattr(main_window, 'pages') and page_key in getattr(main_window, 'pages', {}):
                main_window.content_stack.setCurrentWidget(main_window.pages[page_key])
                main_window.current_page = page_key
                return
            from .pages.profile.public_profile_page import PublicProfilePage
            profile_widget = PublicProfilePage(getattr(main_window, 'global_managers', None), user_id, parent=main_window)
            main_window.content_stack.addWidget(profile_widget)
            if hasattr(main_window, 'pages') and isinstance(main_window.pages, dict):
                main_window.pages[page_key] = profile_widget
            main_window.content_stack.setCurrentWidget(profile_widget)
            main_window.current_page = page_key
        except Exception as e:
            logger.error(f"Failed to open profile from item: {e}")
            # Fallback to legacy behavior
            self.user_clicked.emit(self.user_data)
    
    def on_friend_request_requested(self):
        """Handle friend request request."""
        # This will be handled by the parent widget
        pass


class OnlineUsersSidebar(QWidget):
    """Collapsible sidebar for displaying online users."""
    
    # Signals
    sidebar_toggled = pyqtSignal(bool)  # True when expanded, False when collapsed
    user_selected = pyqtSignal(dict)  # Emits user data when user is selected
    private_message_requested = pyqtSignal(dict)  # Emits user data for private message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # State
        self.is_expanded = False
        self.is_animating = False
        
        # Dimensions
        self.collapsed_width = 60
        self.expanded_width = 240
        
        # Animation
        self.animation = None
        self.animation_duration = 300
        
        # User data
        self.all_users = []
        self.current_user_id = None
        self.user_widgets = []  # Initialize user_widgets list
        self._user_id_to_widget: dict[str, OnlineUserItem] = {}
        
        # PERFORMANCE: Cache auth state to prevent duplicate calls
        self._cached_auth_state = None
        self._last_refresh_time = 0
        
        # Setup UI
        self.setup_ui()
        
        # Load current user immediately
        self.load_current_user_instantly()
        
        # Load other users asynchronously
        QTimer.singleShot(100, self.load_users_from_database)
        
        # Auto-refresh timer for online status and user data
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_users_data)
        self.refresh_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        # Force refresh timer for authentication state
        self.auth_check_timer = QTimer()
        self.auth_check_timer.timeout.connect(self.check_authentication_and_load_user)
        self.auth_check_timer.start(30000)  # Check every 30 seconds instead of 5
    
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
        self.main_layout.setContentsMargins(0, 0, 0, 8)
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
        
        # Toggle button (use custom white icons instead of emoji for better contrast)
        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(32, 32)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #40444b;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #5865f2;
            }
        """)
        # Pre-create icons
        self._people_icon = QIcon(self._create_people_icon_pixmap(18, "#ffffff"))
        self._arrow_icon = QIcon(self._create_arrow_icon_pixmap(18, "#ffffff"))
        self.toggle_btn.setIcon(self._people_icon)
        self.toggle_btn.setIconSize(QSize(18, 18))
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

        # Add Friend toggle button (reveals the search bar without shifting on open)
        self.add_friend_toggle_btn = QPushButton("Add")
        self.add_friend_toggle_btn.setFixedHeight(28)
        self.add_friend_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 0px 10px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
        """)
        self.add_friend_toggle_btn.setVisible(False)
        self.add_friend_toggle_btn.clicked.connect(self.toggle_add_friend_bar)
        header_layout.addWidget(self.add_friend_toggle_btn)
        
        self.main_layout.addWidget(header_container)
    
    def create_add_friend_bar(self):
        """Create the 'Add a Friend' search bar."""
        self.add_friend_container = QWidget()
        # Keep it in the layout but collapsed to avoid layout jumps
        self.add_friend_container.setVisible(True)
        self.add_friend_container.setMaximumHeight(0)
        self.add_friend_is_open = False
        self.add_friend_anim = None
        
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

    def toggle_add_friend_bar(self):
        """Toggle the visibility of the Add Friend bar with a smooth slide."""
        target_open = not getattr(self, 'add_friend_is_open', False)
        # Stop any ongoing animation
        if getattr(self, 'add_friend_anim', None):
            try:
                self.add_friend_anim.stop()
            except Exception:
                pass
        # Animate maximumHeight for smooth expand/collapse
        self.add_friend_anim = QPropertyAnimation(self.add_friend_container, b"maximumHeight")
        self.add_friend_anim.setDuration(200)
        self.add_friend_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        start_h = self.add_friend_container.maximumHeight()
        end_h = 80 if target_open else 0
        self.add_friend_anim.setStartValue(start_h)
        self.add_friend_anim.setEndValue(end_h)
        self.add_friend_anim.start()
        self.add_friend_is_open = target_open
        if target_open:
            # Focus input shortly after animation starts
            QTimer.singleShot(220, self.friend_search_input.setFocus)
    
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
        if getattr(self, 'animation', None):
            try:
                self.animation.stop()
            except Exception:
                pass
        
        self.is_animating = True
        
        # Build a parallel animation group to keep min/max in sync (prevents layout thrash)
        group = QParallelAnimationGroup(self)

        anim_min = QPropertyAnimation(self, b"minimumWidth")
        anim_min.setDuration(self.animation_duration)
        anim_min.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_min.setStartValue(self.width())
        anim_min.setEndValue(target_width)
        group.addAnimation(anim_min)

        anim_max = QPropertyAnimation(self, b"maximumWidth")
        anim_max.setDuration(self.animation_duration)
        anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_max.setStartValue(self.width())
        anim_max.setEndValue(target_width)
        group.addAnimation(anim_max)

        # Keep a reference for lifecycle and connect completion
        self.animation = group
        self.animation.finished.connect(self.on_animation_finished)

        # Update state for toggle icon, but defer heavy child visibility until finished
        self.is_expanded = (target_width == self.expanded_width)
        self.update_toggle_button()

        self.animation.start()
    
    def on_animation_finished(self):
        """Handle animation completion."""
        self.is_animating = False
        
        # Update fixed width
        if self.animation:
            # All animations in the group end at the same value
            try:
                # Read from one of the child animations
                final_width = self.expanded_width if self.is_expanded else self.collapsed_width
            except Exception:
                final_width = self.width()
            self.setFixedWidth(final_width)
            self.setMaximumWidth(final_width)
            self.setMinimumWidth(final_width)
            
            # Update UI visibility based on final state
            if final_width == self.collapsed_width:
                self.is_expanded = False
                self.title_label.setVisible(False)
                self.user_count_label.setVisible(False)
                if hasattr(self, 'add_friend_toggle_btn'):
                    self.add_friend_toggle_btn.setVisible(False)
                # Ensure the add-friend bar is collapsed when sidebar is collapsed
                self.add_friend_is_open = False
                try:
                    self.add_friend_container.setMaximumHeight(0)
                except Exception:
                    pass
            else:
                # Now that width is settled, reveal heavier child widgets to reduce repaint churn during resize
                self.title_label.setVisible(True)
                self.user_count_label.setVisible(True)
                if hasattr(self, 'add_friend_toggle_btn'):
                    self.add_friend_toggle_btn.setVisible(True)
            
            self.update_toggle_button()
            
            # Refresh user list after animation completes to show proper layout
            self.refresh_users_list()
            
            # Force layout update
            self.updateGeometry()
            try:
                parent_widget = self.parent()
                if parent_widget is not None:
                    parent_update = getattr(parent_widget, 'update', None)
                    if callable(parent_update):
                        parent_update()
            except Exception as e:
                logger.error(f"Error updating parent widget: {e}")
        
        # Emit signal
        self.sidebar_toggled.emit(self.is_expanded)
    
    def update_toggle_button(self):
        """Update the toggle button appearance."""
        if self.is_expanded:
            # Show collapse arrow when expanded
            self.toggle_btn.setIcon(self._arrow_icon)
        else:
            # Show people icon when collapsed
            self.toggle_btn.setIcon(self._people_icon)

    def _create_people_icon_pixmap(self, size: int = 18, color: str = "#ffffff") -> QPixmap:
        """Create a simple 'people' glyph as a white icon pixmap."""
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        # Heads
        head_r = size * 0.18
        painter.drawEllipse(
            QPointF(size * 0.38, size * 0.35), head_r, head_r
        )
        painter.drawEllipse(
            QPointF(size * 0.68, size * 0.35), head_r, head_r
        )
        # Bodies (rounded rectangles approximated with ellipses)
        body_w = size * 0.28
        body_h = size * 0.22
        painter.drawRoundedRect(
            int(size * 0.24), int(size * 0.55), int(body_w), int(body_h), 3, 3
        )
        painter.drawRoundedRect(
            int(size * 0.56), int(size * 0.55), int(body_w), int(body_h), 3, 3
        )
        painter.end()
        return pix

    def _create_arrow_icon_pixmap(self, size: int = 18, color: str = "#ffffff") -> QPixmap:
        """Create a simple right-pointing arrow icon pixmap."""
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        path = QPainterPath()
        path.moveTo(size * 0.35, size * 0.25)
        path.lineTo(size * 0.75, size * 0.50)
        path.lineTo(size * 0.35, size * 0.75)
        path.closeSubpath()
        painter.drawPath(path)
        painter.end()
        return pix
    
    def get_current_user_id(self) -> Optional[str]:
        """Get the current user's ID."""
        try:
            from ..auth.user_manager import get_current_user
            user = get_current_user()
            if user is None:
                # User manager not ready yet - return None
                return None
            if user and user.is_authenticated:
                return user.id
            return None
        except Exception as e:
            logger.error(f"Error getting current user ID: {e}")
            return None
    
    def load_current_user_instantly(self):
        """Load current user immediately for instant display."""
        try:
            # Check if user is authenticated
            is_authenticated = self.is_user_authenticated()
            self.current_user_id = self.get_current_user_id()
            
            if is_authenticated and self.current_user_id:
                # Get real user data for current user
                current_user_data = self.get_current_user_real_data()
                if current_user_data:
                    self.all_users = [current_user_data]
                    self.refresh_users_list()
                    logger.info("✅ Current user loaded instantly")
                else:
                    # Fallback if we can't get real data
                    current_user_data = {
                        'user_id': self.current_user_id,
                        'username': 'currentuser',
                        'display_name': 'User',
                        'avatar_url': None,
                        'is_friend': False,
                        'is_online': True,
                        'status': 'Online'
                    }
                    self.all_users = [current_user_data]
                    self.refresh_users_list()
                    logger.info("✅ Current user loaded with fallback data")
                
                # Immediately load all other users as well
                QTimer.singleShot(100, self.load_users_from_database)
            else:
                # User not authenticated yet - schedule a re-check soon
                logger.info("🔍 User not authenticated yet - scheduling auth re-check")
                QTimer.singleShot(2000, self.check_authentication_and_load_user)
        except Exception as e:
            logger.error(f"Error loading current user instantly: {e}")
    
    def get_current_user_real_data(self) -> Optional[Dict[str, Any]]:
        """Get current user's real data from database."""
        try:
            from ..database.supabase_client import get_supabase_client
            client = get_supabase_client()
            
            if not client or not self.current_user_id:
                return None
            
            # Fetch user profile from database - handle missing columns gracefully
            try:
                # Try to fetch with all fields first
                response = client.table("user_profiles").select(
                    "user_id, username, display_name, email, first_name, last_name, bio, created_at, avatar_url"
                ).eq("user_id", self.current_user_id).single().execute()
            except Exception as column_error:
                # If first_name column doesn't exist, try without it
                logger.warning(f"Some columns may not exist, trying fallback query: {column_error}")
                response = client.table("user_profiles").select(
                    "user_id, username, display_name, email, bio, created_at"
                ).eq("user_id", self.current_user_id).single().execute()
            
            if response.data:
                user_data = response.data
                logger.debug(f"Raw user data from database: {user_data}")
                
                # Generate display name from real data
                display_name = self._generate_display_name(user_data)
                logger.debug(f"Generated display name: '{display_name}'")
                
                # Get current iRacing status if available
                iracing_status = self._get_current_user_iracing_status()
                
                result = {
                    'user_id': user_data['user_id'],
                    'username': user_data.get('username', 'currentuser'),
                    'display_name': display_name,
                    'email': user_data.get('email'),
                    'first_name': user_data.get('first_name', ''),  # Safe fallback
                    'last_name': user_data.get('last_name', ''),    # Safe fallback
                    'bio': user_data.get('bio'),
                    'created_at': user_data.get('created_at'),
                    'status': iracing_status or 'Online',
                    'is_online': True,  # Current user is always online
                    'is_friend': False,  # Can't be friends with yourself
                    'avatar_url': user_data.get('avatar_url')
                }
                logger.debug(f"Final user data for sidebar: {result}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current user data: {e}")
            return None
    
    def _generate_display_name(self, user_data: Dict[str, Any]) -> str:
        """Generate display name from user data."""
        logger.debug(f"Generating display name from user data: {user_data}")
        
        # First, try to get name from auth metadata (like the account bubble does)
        try:
            from ..database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if client and hasattr(client, 'auth') and client.auth.get_session():
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    user = session.user
                    metadata = getattr(user, 'user_metadata', {})
                    
                    # Try different metadata fields for name (same logic as account bubble)
                    if metadata.get('full_name'):
                        name = metadata['full_name']
                        logger.debug(f"Using auth metadata full_name: '{name}'")
                        return name
                    elif metadata.get('name'):
                        name = metadata['name']
                        logger.debug(f"Using auth metadata name: '{name}'")
                        return name
                    elif metadata.get('first_name') and metadata.get('last_name'):
                        first_name = metadata['first_name']
                        last_name = metadata['last_name']
                        # Convert to proper case if all caps
                        if first_name.isupper():
                            first_name = first_name.title()
                        if last_name.isupper():
                            last_name = last_name.title()
                        name = f"{first_name} {last_name}"
                        logger.debug(f"Using auth metadata first_name + last_name: '{name}'")
                        return name
                    elif metadata.get('first_name'):
                        first_name = metadata['first_name']
                        if first_name.isupper():
                            first_name = first_name.title()
                        logger.debug(f"Using auth metadata first_name: '{first_name}'")
                        return first_name
        except Exception as e:
            logger.debug(f"Error getting auth metadata: {e}")
        
        # Try first_name + last_name from database
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        logger.debug(f"First name: '{first_name}', Last name: '{last_name}'")
        
        if first_name or last_name:
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                logger.debug(f"Using full name: '{full_name}'")
                return full_name
        
        # Fallback to display_name
        display_name = user_data.get('display_name', '')
        if display_name:
            logger.debug(f"Using display_name: '{display_name}'")
            return display_name
        
        # Fallback to username
        username = user_data.get('username', '')
        if username:
            logger.debug(f"Using username: '{username}'")
            return username
        
        # Final fallback
        logger.debug("Using fallback 'User'")
        return 'User'
    
    def check_authentication_and_load_user(self):
        """Check if user has been authenticated and load them if so."""
        try:
            is_authenticated = self.is_user_authenticated()
            current_user_id = self.get_current_user_id()
            
            if is_authenticated and current_user_id:
                # User is now authenticated - load all users
                self.current_user_id = current_user_id
                logger.info("✅ User authenticated - loading all users")
                
                # Load all users from database
                self.load_users_from_database()
            else:
                # User not authenticated - only log once per minute to reduce spam
                import time
                current_time = time.time()
                if not hasattr(self, '_last_unauth_log') or current_time - self._last_unauth_log > 60:
                    self._last_unauth_log = current_time
                    logger.info("✅ User not authenticated - cleared user list")
                
                # Clear the list silently
                self.all_users = []
                self.current_user_id = None
                self.refresh_users_list()
        except Exception as e:
            logger.error(f"Error checking authentication and loading user: {e}")
    
    def load_users_from_database(self):
        """Load all users from database with friends prioritized.
        Runs in a background thread and applies results on the UI thread to avoid stalling rendering.
        """
        import threading

        if getattr(self, "_refresh_in_progress", False):
            return
        self._refresh_in_progress = True

        def worker():
            try:
                # Build fresh snapshot off the UI thread
                users_snapshot = self._build_users_snapshot()
            except Exception as e:
                logger.error(f"Error loading users from database (bg): {e}")
                users_snapshot = None

            # Apply on UI thread
            def apply_result():
                try:
                    if users_snapshot is not None:
                        self.all_users = users_snapshot
                        self.refresh_users_list()
                        logger.info(f"✅ Loaded {len(self.all_users)} real users from database (async)")
                finally:
                    self._refresh_in_progress = False

            QTimer.singleShot(0, apply_result)

        threading.Thread(target=worker, name="SidebarUsersLoader", daemon=True).start()

    def _build_users_snapshot(self):
        """Blocking implementation: fetches data and returns the composed users list."""
        # Get current user ID if not already set
        if not self.current_user_id:
            self.current_user_id = self.get_current_user_id()

        # Import database managers
        from trackpro.social.friends_manager import FriendsManager
        from trackpro.social.user_manager import EnhancedUserManager

        friends_manager = FriendsManager()
        friends_list = friends_manager.get_friends_list(self.current_user_id, include_online_status=True)

        user_manager = EnhancedUserManager()
        if not user_manager.supabase:
            logger.error("No Supabase client available for user query")
            return self.all_users

        # Prefer public view when available for avatar_url/display info
        try:
            response = user_manager.supabase.from_("public_user_profiles").select(
                "user_id, username, display_name, avatar_url, is_online, last_seen"
            ).limit(500).execute()
        except Exception:
            response = user_manager.supabase.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, user_stats(last_active)"
            ).execute()

        # Get real online status for all users (best effort)
        try:
            from trackpro.utils.app_tracker import get_online_users
            online_users_data = get_online_users()
            online_user_ids = {user['user_id'] for user in online_users_data}
        except Exception:
            online_user_ids = set()

        users: list = []
        # Start with current user if authenticated
        if self.current_user_id:
            current_user_data = self.get_current_user_real_data()
            if current_user_data:
                users.append(current_user_data)

        friends_ids = [friend['friend_id'] for friend in friends_list]

        for user in (response.data or []):
            if user['user_id'] == self.current_user_id:
                continue
            last_active = user.get('last_seen') or (
                (user.get('user_stats') or {}).get('last_active') if isinstance(user.get('user_stats'), dict) else None
            )
            is_online = user.get('is_online') or (user['user_id'] in online_user_ids)
            user_data = {
                'user_id': user['user_id'],
                'username': user.get('username', 'Unknown'),
                'display_name': user.get('display_name'),
                'avatar_url': user.get('avatar_url'),
                'is_friend': user['user_id'] in friends_ids,
                'is_online': is_online,
                'status': self._get_user_status(user['user_id'], last_active, is_online)
            }
            users.append(user_data)

        return users
    
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
            user['status'] = self._get_user_status(user_id, last_active, True)
        
        self.all_users = fallback_users
        self.refresh_users_list()
    
    def _get_user_status(self, user_id: str, last_active: str, is_online: bool = False) -> str:
        """Get user status based on activity and iRacing telemetry."""
        # Check if this is the current user and get their iRacing status
        if user_id == self.current_user_id:
            iracing_status = self._get_current_user_iracing_status()
            if iracing_status:
                return iracing_status
        
        # For other users, check their actual online status
        if not is_online:
            return "Offline"
        
        # For online users, check their last activity
        from datetime import datetime, timedelta
        try:
            if last_active:
                # Parse last active time and determine if user is online
                # This would come from actual user session tracking
                return "Online"  # Placeholder - would be based on actual session data
        except:
            pass
        
        # Default status for online users
        return "Online"
    
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
            if user is None:
                # User manager not ready yet - return False
                return False
            return user and user.is_authenticated and user.name != "Anonymous User"
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
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
            from ...social.friends_manager import FriendsManager
            
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
                
                # Show specific popup for already sent friend request
                if error_message == "Friend request already sent":
                    QMessageBox.information(self, "Friend Request", "You've already sent this user a request!")
                else:
                    QMessageBox.warning(self, "Error", error_message)
                
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            QMessageBox.critical(self, "Error", "An error occurred while sending the friend request.")
        
        # Clear the input field
        self.friend_search_input.clear()
    
    def refresh_users_list(self):
        """Refresh the users list display with friends prioritized."""
        logger.debug(f"Refreshing users list with {len(self.all_users)} users")
        
        # Clear existing widgets from layout completely
        while self.users_layout.count():
            child = self.users_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # Clear our widget tracking
        self.user_widgets.clear()
        self._user_id_to_widget.clear()
        
        # Sort users: friends first (by online status), then others (by online status)
        sorted_users = sorted(
            self.all_users,
            key=lambda u: (
                not u.get('is_friend', False),  # Friends first (False sorts before True)
                not u.get('is_online', False),  # Online users first within each group
                u.get('display_name', '').lower() or u.get('username', '').lower()  # Alphabetical by name
            )
        )
        
        logger.debug(f"Adding {len(sorted_users)} user widgets to UI")
        
        # Add user widgets
        for i, user_data in enumerate(sorted_users):
            logger.debug(f"Creating user widget {i+1}/{len(sorted_users)}: {user_data.get('display_name', 'Unknown')}")
            user_widget = OnlineUserItem(user_data)
            user_widget.user_clicked.connect(self.on_user_selected)
            user_widget.private_message_requested.connect(self.on_private_message_requested)
            self.user_widgets.append(user_widget)
            try:
                uid = user_data.get('user_id')
                if uid:
                    self._user_id_to_widget[uid] = user_widget
            except Exception:
                pass
            
            # Create container for centering when collapsed
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            
            if not self.is_expanded:
                # Collapsed: show compact user item centered
                user_widget.set_compact_mode(True)
                container_layout.addWidget(user_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
            else:
                # Expanded: show full item
                user_widget.set_compact_mode(False)
                container_layout.addWidget(user_widget)
            
            self.users_layout.addWidget(container)
            logger.debug(f"Added user widget to layout: {user_data.get('display_name', 'Unknown')}")
        
        # Update user count - show online users count
        online_count = len([u for u in self.all_users if u.get('is_online', False)])
        total_count = len(self.all_users)
        self.user_count_label.setText(f"{online_count}/{total_count} online")
        self.count_icon.setText(str(online_count))
        
        logger.debug(f"Users list refresh complete. Online: {online_count}, Total: {total_count}")

    # ----------------------------
    # Unread DM glow management
    # ----------------------------
    def set_unread_glow_for_user(self, user_id: str, enabled: bool) -> None:
        try:
            widget = self._user_id_to_widget.get(user_id)
            if widget and hasattr(widget, 'set_unread_glow'):
                widget.set_unread_glow(enabled)
        except Exception:
            pass

    def clear_unread_glow_for_user(self, user_id: str) -> None:
        self.set_unread_glow_for_user(user_id, False)
    
    def refresh_users_data(self):
        """Refresh users data including online status from the backend.
        This method is timer-driven on the UI thread, so it schedules background work and returns immediately.
        """
        logger.debug("Refreshing users data (async)...")
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
            # Private messages moved to profile; do not connect DM action
            popup.show()
            
        except Exception as e:
            logger.error(f"Error showing user profile popup: {e}")
    
    def on_view_profile_requested(self, user_id: str):
        """Handle view profile request from popup."""
        logger.info(f"View profile requested for user: {user_id}")
        try:
            # Find the main window and switch to a public profile page
            main_window = self.window()
            if not main_window:
                return
            # Create or switch to profile page dynamically
            # Page key includes user id to allow multiple distinct profiles in stack
            page_key = f"public_profile:{user_id}"
            if hasattr(main_window, 'pages') and page_key in getattr(main_window, 'pages', {}):
                main_window.content_stack.setCurrentWidget(main_window.pages[page_key])
                main_window.current_page = page_key
                return

            # Lazy-create profile page
            try:
                from .pages.profile.public_profile_page import PublicProfilePage
            except Exception as import_error:
                logger.error(f"Could not import PublicProfilePage: {import_error}")
                return

            if hasattr(main_window, 'global_managers') and hasattr(main_window, 'content_stack'):
                profile_widget = PublicProfilePage(main_window.global_managers, user_id, parent=main_window)
                main_window.content_stack.addWidget(profile_widget)
                if hasattr(main_window, 'pages') and isinstance(main_window.pages, dict):
                    main_window.pages[page_key] = profile_widget
                main_window.content_stack.setCurrentWidget(profile_widget)
                main_window.current_page = page_key
        except Exception as e:
            logger.error(f"Failed to open public profile page: {e}")
    
    def on_friend_request_sent(self, user_id: str):
        """Handle friend request sent from popup."""
        logger.info(f"Friend request sent to user: {user_id}")
        # Refresh the users list to update friend status
        self.refresh_users_data()
    
    def on_private_message_requested(self, user_data: Dict[str, Any]):
        """Handle private message request from user item."""
        logger.info(f"Private message requested for user: {user_data.get('display_name', 'Unknown')}")
        
        # Try to find a widget with start_direct_private_message method
        # Start from current widget and traverse up the parent hierarchy
        current_widget = self
        while current_widget is not None:
            if hasattr(current_widget, 'start_direct_private_message'):
                current_widget.start_direct_private_message(user_data)
                return
            
            # Get the parent widget safely
            try:
                current_widget = current_widget.parent()
            except Exception as e:
                logger.error(f"Error traversing parent hierarchy: {e}")
                break
        
        # If we can't find the method in parent hierarchy, try to find the main window
        # and look for the community page
        try:
            # Find the main window
            main_window = self.window()
            if main_window and hasattr(main_window, 'content_stack'):
                # Look for CommunityPage in the content stack
                for i in range(main_window.content_stack.count()):
                    widget = main_window.content_stack.widget(i)
                    if hasattr(widget, 'start_direct_private_message'):
                        widget.start_direct_private_message(user_data)
                        return
        except Exception as e:
            logger.error(f"Error finding main window or community page: {e}")
        
        # Fallback to emitting signal if direct method not found
        self.private_message_requested.emit(user_data)
    
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
        
        # Also update the widget if it exists
        for user_widget in self.user_widgets:
            if user_widget.user_data.get('user_id') == user_id:
                user_widget.user_data['status'] = status
                if is_online is not None:
                    user_widget.user_data['is_online'] = is_online
                user_widget.refresh_online_status()
                break
        
        self.refresh_users_list()
    
    def on_authentication_changed(self):
        """Handle authentication state changes (login/logout)."""
        # PERFORMANCE: Enhanced debouncing to prevent redundant auth state updates
        import time
        current_time = time.time()
        
        # Skip if called too frequently (within 500ms)
        if current_time - self._last_refresh_time < 0.5:
            logger.debug("🔄 Skipping auth change - called too frequently")
            return
            
        current_auth_state = self.is_user_authenticated()
        if self._cached_auth_state == current_auth_state:
            logger.debug("🔄 Skipping auth change - state unchanged")
            return
            
        self._cached_auth_state = current_auth_state
        self._last_refresh_time = current_time
        logger.info("🔄 Authentication state changed - refreshing user list")
        
        # Check if user is now authenticated
        current_user_id = self.get_current_user_id()
        
        if current_auth_state and current_user_id:
            # User just logged in - immediately load all users
            self.current_user_id = current_user_id
            logger.info("✅ User authenticated - immediately loading all users")
            
            # Immediately load all users from database
            self.load_users_from_database()
        else:
            # User just logged out - clear the list
            self.all_users = []
            self.current_user_id = None
            logger.info("✅ User logged out - cleared user list")
        
        # Refresh the UI
        self.refresh_users_list()
        self.update_add_friend_ui_state()
    
    def force_refresh(self):
        """Force refresh the user list (re-enabled)."""
        try:
            logger.info("🔄 Online users sidebar force refresh started...")
            self.load_users_from_database()
            logger.info("✅ Online users sidebar force refresh completed")
        except Exception as e:
            logger.error(f"❌ Error in online users sidebar force refresh: {e}")

    def load_users_from_database(self):
        """Load users from the database and update the list for both authenticated and anonymous users."""
        try:
            logger.info("🔄 Loading users from database...")

            # Fetch all known users (increase limit to capture more members)
            from trackpro.social.user_manager import EnhancedUserManager
            user_manager = EnhancedUserManager()
            users = user_manager.get_all_users(limit=500) or []
            logger.info(f"✅ Retrieved {len(users)} users from database")

            # Fallback for anonymous users: use public online view if main list is empty
            if not users:
                try:
                    public_online = user_manager.get_online_users(limit=200) or []
                    logger.info(f"🔄 Fallback to public online users: {len(public_online)} found")
                    users = public_online
                except Exception as e_pub:
                    logger.warning(f"⚠️ Public online users fallback failed: {e_pub}")

            # Determine online users from app tracker (works without auth)
            try:
                from trackpro.utils.app_tracker import get_online_users
                online_info = get_online_users() or []
                online_user_ids = {u.get('user_id') for u in online_info}
            except Exception as e_online:
                logger.warning(f"⚠️ Could not fetch online user info: {e_online}")
                online_user_ids = set()

            # Determine friend relationships if authenticated (optional)
            friends_ids = set()
            try:
                current_user_id = self.get_current_user_id()
                if current_user_id:
                    from trackpro.social.friends_manager import FriendsManager
                    fm = FriendsManager()
                    flist = fm.get_friends_list(current_user_id, include_online_status=False) or []
                    friends_ids = {f.get('friend_id') for f in flist}
            except Exception as e_friends:
                logger.debug(f"Friends lookup skipped or failed: {e_friends}")

            # Build unified list used by refresh for counts and rendering
            self.all_users = []
            for u in users:
                uid = u.get('user_id') or u.get('id')
                if not uid:
                    continue
                # Build sensible display values even when some fields are missing
                uname = (u.get('username') or '').strip()
                dname = (u.get('display_name') or '').strip()
                display_name = dname or uname or 'Member'
                is_online = uid in online_user_ids
                self.all_users.append({
                    'user_id': uid,
                    'username': uname,
                    'display_name': display_name,
                    'avatar_url': u.get('avatar_url'),
                    'is_friend': uid in friends_ids,
                    'is_online': is_online,
                    'status': 'Online' if is_online else 'Offline',
                })

            # Drive UI update through the centralized refresher
            self.refresh_users_list()
            logger.info("✅ Users loaded from database successfully")

            # Keep add-friend bar in correct enabled/disabled state
            self.update_add_friend_ui_state()

        except Exception as e:
            logger.error(f"❌ Error loading users from database: {e}")

    def add_user_to_list(self, user_data):
        """Add a user to the list."""
        try:
            logger.info(f"🔄 Adding user to list: {user_data.get('display_name', 'Unknown')}")
            
            # Create user widget
            user_widget = self.create_user_widget(user_data)
            if user_widget:
                self.users_layout.addWidget(user_widget)
                logger.info(f"✅ User widget added to layout: {user_data.get('display_name', 'Unknown')}")
            else:
                logger.warning(f"⚠️ Failed to create user widget for: {user_data.get('display_name', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"❌ Error adding user to list: {e}")

    def create_user_widget(self, user_data):
        """Create a user widget for the list."""
        try:
            logger.info(f"🔄 Creating user widget for: {user_data.get('display_name', 'Unknown')}")
            user_widget = OnlineUserItem(user_data, self)
            
            # Connect signals
            user_widget.user_clicked.connect(self.on_user_selected)
            user_widget.private_message_requested.connect(self.on_private_message_requested)
            
            # Add to user_widgets list for tracking
            self.user_widgets.append(user_widget)
            
            logger.info(f"✅ User widget created successfully for: {user_data.get('display_name', 'Unknown')}")
            return user_widget
            
        except Exception as e:
            logger.error(f"❌ Error creating user widget: {e}")
            return None

    def clear_user_list(self):
        """Clear the user list."""
        try:
            logger.info("🔄 Clearing user list...")
            
            # Remove all widgets from the layout
            while self.users_layout.count():
                child = self.users_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                    logger.info("✅ Removed user widget from layout")
            
            logger.info("✅ User list cleared successfully")
            
        except Exception as e:
            logger.error(f"❌ Error clearing user list: {e}")
    
    def on_avatar_updated(self, avatar_url: str):
        """Handle avatar updates from other components."""
        try:
            logger.info(f"🔄 Avatar updated in sidebar: {avatar_url}")
            # Refresh the current user's avatar in the sidebar
            self.refresh_existing_avatars()
            logger.info("✅ Avatar refresh completed")
        except Exception as e:
            logger.error(f"❌ Error updating avatar in sidebar: {e}")
    
    def refresh_existing_avatars(self):
        """Refresh avatars for existing user widgets without recreating them."""
        current_user_id = self.get_current_user_id()
        if not current_user_id:
            return
            
        # Find the current user's widget and refresh its avatar
        for user_widget in self.user_widgets:
            if user_widget.user_data.get('user_id') == current_user_id:
                # Get fresh user data
                fresh_user_data = self.get_current_user_real_data()
                if fresh_user_data:
                    # Update the widget's user data
                    user_widget.user_data = fresh_user_data
                    
                    # Refresh the avatar display
                    user_widget.refresh_avatar()
                    
                    logger.info("✅ Refreshed avatar for existing user widget")
                break
    
    def _ensure_current_user_online_status(self):
        """Ensure the current user is marked as online in the database."""
        try:
            if not self.current_user_id:
                return
                
            from ..utils.app_tracker import update_user_online_status
            success = update_user_online_status(self.current_user_id, True)
            if success:
                logger.debug(f"✅ Ensured current user {self.current_user_id} is marked as online")
            else:
                logger.warning(f"⚠️ Failed to mark current user {self.current_user_id} as online")
                
        except Exception as e:
            logger.error(f"Error ensuring current user online status: {e}")
    
    def force_current_user_heartbeat(self):
        """Force a heartbeat for the current user (for testing)."""
        try:
            if not self.current_user_id:
                logger.warning("No current user ID available for heartbeat")
                return False
            
            from trackpro.utils.app_tracker import force_heartbeat
            success = force_heartbeat(self.current_user_id)
            if success:
                logger.info(f"✅ Forced heartbeat for current user {self.current_user_id}")
                # Refresh the users list to show updated status
                QTimer.singleShot(1000, self.load_users_from_database)
            else:
                logger.warning(f"⚠️ Failed to force heartbeat for current user {self.current_user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error forcing heartbeat: {e}")
            return False
    
    def check_heartbeat_status(self):
        """Check heartbeat status for the current user."""
        try:
            if not self.current_user_id:
                logger.warning("No current user ID available for heartbeat check")
                return None
            
            from trackpro.utils.app_tracker import get_heartbeat_status
            status = get_heartbeat_status(self.current_user_id)
            logger.info(f"💓 Heartbeat status for user {self.current_user_id}: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Error checking heartbeat status: {e}")
            return None