import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from ..discord_navigation import DiscordNavigation
from ..online_users_sidebar import OnlineUsersSidebar
from .shared.base_page import GlobalManagers
from .performance_manager import PerformanceManager, ThreadPriorityManager, CPUCoreManager
# Import only what we need immediately to avoid circular imports
from ..pages.home import HomePage
from ..pages.community import CommunityPage
# App tracking
from trackpro.utils.app_tracker import start_app_tracking, stop_app_tracking, update_user_online_status

logger = logging.getLogger(__name__)

class ModernMainWindow(QMainWindow):
    auth_state_changed = pyqtSignal(bool)
    calibration_updated = pyqtSignal(str)
    window_state_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, oauth_handler=None):
        super().__init__(parent)
        self.oauth_handler = oauth_handler
        
        self.global_managers = GlobalManagers()
        self.content_stack = None
        self.pages = {}
        self.current_page = None
        self._is_shutting_down = False
        
        # Global system references
        self.global_iracing_api = None
        self.global_hardware = None
        self.global_output = None
        self.global_pedal_data_queue = None
        
        # UI update timer for pedal data
        self.ui_update_timer = None
        
        # Custom title bar variables
        self.custom_title_bar = None
        self.drag_position = QPoint()
        
        # PERFORMANCE: Prevent multiple auth checks during startup
        self._startup_auth_check_completed = False
        self._cached_user_info = None
        
        self.init_performance_optimization()
        self.init_global_managers()
        self.init_modern_ui()
        
        # Start app tracking
        self.start_app_tracking()
        
        logger.info("🚀 Modern TrackPro UI initialized with modular architecture")
    
    def start_app_tracking(self, user_id: str = None):
        """Start tracking the app session."""
        try:
            # Get current user ID if not provided
            if not user_id:
                current_user = self.get_current_user_info()
                user_id = current_user.get('id') if current_user else None
            
            # Start app tracking
            success = start_app_tracking(user_id)
            if success:
                logger.info(f"✅ App tracking started for user: {user_id}")
            else:
                logger.warning("⚠️ Failed to start app tracking (this is normal if Supabase is not available)")
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting app tracking: {e}")
            return False
    
    def stop_app_tracking(self):
        """Stop tracking the app session."""
        try:
            success = stop_app_tracking()
            if success:
                logger.info("✅ App tracking stopped")
            else:
                logger.warning("⚠️ Failed to stop app tracking")
            
            return success
            
        except Exception as e:
            logger.error(f"Error stopping app tracking: {e}")
            return False
    
    def update_user_online_status(self, user_id: str, is_online: bool = True):
        """Update user's online status."""
        try:
            success = update_user_online_status(user_id, is_online)
            if success:
                logger.debug(f"Updated online status: {is_online} for user {user_id}")
            else:
                logger.warning(f"Failed to update online status for user {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating online status: {e}")
            return False
    
    def get_online_users(self):
        """Get list of currently online users."""
        try:
            from trackpro.utils.app_tracker import get_online_users
            online_users = get_online_users()
            logger.debug(f"Retrieved {len(online_users)} online users")
            return online_users
        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return []
    
    def get_user_session_stats(self, user_id: str = None):
        """Get session statistics for a user."""
        try:
            from trackpro.utils.app_tracker import get_user_stats
            if not user_id:
                current_user = self.get_current_user_info()
                user_id = current_user.get('id') if current_user else None
            
            if user_id:
                stats = get_user_stats(user_id)
                logger.debug(f"Retrieved session stats for user {user_id}")
                return stats
            else:
                logger.warning("No user ID provided for session stats")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user session stats: {e}")
            return {}
    
    def enable_dark_title_bar(self):
        """Enable dark title bar on Windows 10/11."""
        try:
            import ctypes
            from ctypes import wintypes
            import sys
            
            if sys.platform == "win32":
                # Get window handle
                hwnd = int(self.winId())
                
                # Constants for Windows 10/11 dark mode
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                
                # Try the newer API first (Windows 11)
                try:
                    value = ctypes.c_int(1)  # 1 = enable dark mode
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, 
                        DWMWA_USE_IMMERSIVE_DARK_MODE,
                        ctypes.byref(value),
                        ctypes.sizeof(value)
                    )
                    logger.info("✅ Dark title bar enabled (Windows 11 API)")
                    return
                except:
                    pass
                
                # Fallback to older API (Windows 10)
                try:
                    value = ctypes.c_int(1)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd,
                        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                        ctypes.byref(value),
                        ctypes.sizeof(value)
                    )
                    logger.info("✅ Dark title bar enabled (Windows 10 API)")
                    return
                except:
                    pass
                
                logger.warning("⚠️ Could not enable dark title bar - Windows API not available")
            else:
                logger.info("ℹ️ Dark title bar not needed on non-Windows platform")
                
        except Exception as e:
            logger.error(f"❌ Error enabling dark title bar: {e}")
    
    def showEvent(self, event):
        """Override showEvent to enable dark title bar when window is shown."""
        super().showEvent(event)
        # No longer needed since we have custom title bar
        pass
    
    def create_custom_title_bar(self):
        """Create a custom title bar that matches our theme perfectly."""
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: none;
                border-bottom: 1px solid #2d2d2d;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 5, 0)
        title_layout.setSpacing(5)
        
        # App icon and title
        title_label = QLabel("TrackPro V1.5.5")
        title_label.setStyleSheet("""
            QLabel {
                color: #fefefe;
                font-size: 14px;
                font-weight: 500;
                background-color: transparent;
                border: none;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Window control buttons
        self.create_window_controls(title_layout)
        
        # Make title bar draggable
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        
        return title_bar
    
    def create_window_controls(self, layout):
        """Create minimize, maximize, and close buttons."""
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #fefefe;
                font-size: 16px;
                font-weight: bold;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """
        
        close_button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #fefefe;
                font-size: 16px;
                font-weight: bold;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                background-color: #e81123;
                color: white;
            }
        """
        
        # Minimize button
        minimize_btn = QPushButton("−")
        minimize_btn.setStyleSheet(button_style)
        minimize_btn.clicked.connect(self.showMinimized)
        layout.addWidget(minimize_btn)
        
        # Maximize/Restore button
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setStyleSheet(button_style)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.maximize_btn)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(close_button_style)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.showMaximized()
            self.maximize_btn.setText("❐")
    
    def title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def init_performance_optimization(self):
        try:
            if CPUCoreManager:
                CPUCoreManager.set_process_affinity()
                recommendations = CPUCoreManager.get_performance_recommendations()
                for rec in recommendations:
                    logger.info(rec)
            
            if ThreadPriorityManager:
                ThreadPriorityManager.set_ui_thread_priority()
            
            if PerformanceManager:
                self.global_managers.performance = PerformanceManager()
                self.global_managers.performance.ui_update_ready.connect(self.handle_optimized_ui_update)
                self.global_managers.performance.performance_warning.connect(self.handle_performance_warning)
                logger.info("🚀 PERFORMANCE: Modern UI optimized for ultra-smooth operation")
            else:
                logger.warning("Performance manager not available - using basic UI updates")
                
        except Exception as e:
            logger.error(f"Performance optimization setup failed: {e}")
    
    def init_global_managers(self):
        try:
            from trackpro.pedals.hardware_input import HardwareInput
            self.global_managers.hardware = HardwareInput()
            logger.info("✅ Hardware input manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize hardware manager: {e}")
        
        # Defer iRacing API initialization to when global API is ready
        # This prevents early access attempts that fail during startup
        self.global_managers.iracing = None
        
        self.global_managers.auth = self.oauth_handler
        logger.info("✅ Global managers initialized")
    
    def set_global_iracing_api(self, iracing_api):
        """Set the global iRacing API instance."""
        self.global_iracing_api = iracing_api
        self.global_managers.iracing = iracing_api
        logger.info("✅ Global iRacing API set for modern window")
        
        # Pass to pages
        for page in self.pages.values():
            if hasattr(page, 'set_global_iracing_api'):
                page.set_global_iracing_api(iracing_api)
    
    def set_global_pedal_system(self, hardware, output, data_queue):
        """Set the global pedal system instances."""
        self.global_hardware = hardware
        self.global_output = output
        self.global_pedal_data_queue = data_queue
        self.global_managers.hardware = hardware
        logger.info("✅ Global pedal system set for modern window")
        
        # Start UI update timer for real-time pedal visualization
        self.start_ui_update_timer()
        
        # Pass to pages
        for page in self.pages.values():
            if hasattr(page, 'set_global_pedal_system'):
                page.set_global_pedal_system(hardware, output, data_queue)
    
    def set_global_handbrake_system(self, handbrake_hardware, handbrake_data_queue):
        """Set the global handbrake system instances."""
        self.global_handbrake_hardware = handbrake_hardware
        self.global_handbrake_data_queue = handbrake_data_queue
        self.global_managers.handbrake_hardware = handbrake_hardware
        logger.info("✅ Global handbrake system set for modern window")
        
        # Start handbrake UI update timer
        self.start_handbrake_ui_update_timer()
        
        # Pass to pages
        for page in self.pages.values():
            if hasattr(page, 'set_handbrake_input'):
                page.set_handbrake_input(handbrake_hardware)
            if hasattr(page, 'set_global_handbrake_system'):
                page.set_global_handbrake_system(handbrake_hardware, handbrake_data_queue)
    
    def start_ui_update_timer(self):
        """Start the UI update timer for real-time pedal data visualization."""
        if self.ui_update_timer is None:
            from PyQt6.QtCore import QTimer
            self.ui_update_timer = QTimer()
            self.ui_update_timer.timeout.connect(self.update_pedal_ui)
            self.ui_update_timer.setInterval(17)  # ~60Hz UI updates for smooth visualization
            self.ui_update_timer.start()
            logger.info("🖥️ UI update timer started at 60Hz for smooth pedal visualization")
    
    def update_pedal_ui(self):
        """Update the UI with the latest pedal data from the global queue."""
        if not self.global_pedal_data_queue:
            return
            
        try:
            from queue import Empty
            # Get the latest data from the queue, non-blocking
            raw_values = self.global_pedal_data_queue.get_nowait()
            
            # Update current page if it has pedal update methods
            current_widget = self.content_stack.currentWidget()
            if current_widget and hasattr(current_widget, 'update_pedal_values'):
                current_widget.update_pedal_values(raw_values)
                
        except Empty:
            # This is normal, means no new data from the pedal thread
            pass
        except Exception as e:
            logger.error(f"❌ Error updating pedal UI: {e}")
    
    def start_handbrake_ui_update_timer(self):
        """Start the UI update timer for real-time handbrake data visualization."""
        if not hasattr(self, 'handbrake_ui_update_timer') or self.handbrake_ui_update_timer is None:
            from PyQt6.QtCore import QTimer
            self.handbrake_ui_update_timer = QTimer()
            self.handbrake_ui_update_timer.timeout.connect(self.update_handbrake_ui)
            self.handbrake_ui_update_timer.setInterval(50)  # ~20Hz UI updates for handbrake
            self.handbrake_ui_update_timer.start()
            logger.info("🤚 Handbrake UI update timer started at 20Hz")
    
    def update_handbrake_ui(self):
        """Update the UI with the latest handbrake data from the global queue."""
        if not hasattr(self, 'global_handbrake_data_queue') or not self.global_handbrake_data_queue:
            return
        
        try:
            from queue import Empty
            # Get the latest data (non-blocking)
            latest_data = None
            while True:
                try:
                    latest_data = self.global_handbrake_data_queue.get_nowait()
                except Empty:
                    break
            
            # Update handbrake page if we have data
            if latest_data and "handbrake" in self.pages:
                handbrake_page = self.pages["handbrake"]
                if hasattr(handbrake_page, 'handle_hardware_update'):
                    handbrake_page.handle_hardware_update(latest_data)
                
        except Exception as e:
            logger.error(f"Error updating handbrake UI: {e}")
    
    def init_modern_ui(self):
        # Remove the default title bar to create custom one
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Set dark theme for the main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #fefefe;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #fefefe;
            }
            /* Allow child widgets to override styles */
            QWidget[class="OnlineUsersSidebar"] {
                background-color: transparent;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout that includes custom title bar
        main_container_layout = QVBoxLayout(central_widget)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.setSpacing(0)
        
        # Add custom title bar
        self.custom_title_bar = self.create_custom_title_bar()
        main_container_layout.addWidget(self.custom_title_bar)
        
        # Create content area layout
        content_widget = QWidget()
        main_layout = QHBoxLayout(content_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_container_layout.addWidget(content_widget)
        
        self.navigation = self.create_navigation()
        self.content_stack = QStackedWidget()
        
        main_layout.addWidget(self.navigation, 0)
        main_layout.addWidget(self.content_stack, 1)
        
        # Add online users sidebar
        self.online_users_sidebar = self.create_online_users_sidebar()
        main_layout.addWidget(self.online_users_sidebar, 0)
        
        self.create_pages()
        self.switch_to_page("home")
        
        # Refresh authentication state after UI is fully initialized
        # This ensures navigation shows correct user info
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self.refresh_auth_state)
        
        # Set up keyboard shortcuts
        self.setup_keyboard_shortcuts()
    
    def create_navigation(self):
        nav_widget = DiscordNavigation()
        nav_widget.page_requested.connect(self.switch_to_page)
        return nav_widget
    
    def create_online_users_sidebar(self):
        """Create the online users sidebar."""
        sidebar = OnlineUsersSidebar()
        sidebar.user_selected.connect(self.on_user_selected)
        sidebar.private_message_requested.connect(self.on_private_message_requested)
        sidebar.sidebar_toggled.connect(self.on_sidebar_toggled)
        
        # Connect authentication state changes to sidebar
        self.auth_state_changed.connect(sidebar.on_authentication_changed)
        
        return sidebar
    
    def create_pages(self):
        """PERFORMANCE OPTIMIZATION: Only create Home page immediately, lazy-load others."""
        # Create the actual Home page immediately (it's always the first one shown)
        self.pages["home"] = HomePage(self.global_managers)
        self.content_stack.addWidget(self.pages["home"])
        
        # Connect auth state changes to home page refresh
        if hasattr(self.pages["home"], 'on_auth_state_changed'):
            self.auth_state_changed.connect(self.pages["home"].on_auth_state_changed)
        
        logger.info("✅ Home page integrated into modern UI")
        
        # LAZY LOADING: Don't create other pages yet - they'll be created when first accessed
        # This dramatically speeds up startup time
        self._lazy_pages = {
            "pedals": {"class": None, "created": False},  # Dynamic import
            "race_coach": {"class": None, "created": False},  # Dynamic import
            "overlays": {"class": None, "created": False},  # Dynamic import
            "race_pass": {"class": None, "created": False},  # Dynamic import
            "handbrake": {"class": None, "created": False},  # Special handling needed
            "support": {"class": None, "created": False},  # Special handling needed
            "community": {"class": CommunityPage, "created": False},
            "account": {"class": None, "created": False}
        }
        
        logger.info("🚀 PERFORMANCE: Page lazy-loading configured - pages will be created when accessed")
    
    def create_placeholder_page(self, page_name: str):
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt
        
        # Special handling for account page - create actual account page
        if page_name == "account":
            return self.create_account_page()
        
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        
        label = QLabel(f"{page_name.title().replace('_', ' ')} Page")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #fefefe;")
        
        sublabel = QLabel("Coming Soon...")
        sublabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sublabel.setStyleSheet("font-size: 16px; color: #c0c0c0;")
        
        layout.addStretch()
        layout.addWidget(label)
        layout.addWidget(sublabel)
        layout.addStretch()
        
        return placeholder
    
    def switch_to_page(self, page_name: str):
        # Don't switch pages if we're shutting down
        if getattr(self, '_is_shutting_down', False):
            return
        
        # LAZY LOADING: Create page if it doesn't exist yet
        if page_name not in self.pages:
            self._create_lazy_page(page_name)
        
        # Special handling for account page - check authentication first
        if page_name == "account":
            try:
                from trackpro.database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                is_authenticated = False
                
                if supabase_client:
                    user_response = supabase_client.auth.get_user()
                    is_authenticated = bool(user_response and user_response.user)
                    logger.info(f"🔐 Account page auth check: user_response={user_response is not None}, has_user={user_response.user is not None if user_response else False}")
                
                # Additional check: if the home page shows a user name, we're authenticated
                # This handles cases where the session might be temporarily inconsistent
                if not is_authenticated:
                    # Check if we have user info that indicates authentication
                    user_info = self.get_current_user_info()
                    if user_info and user_info.get('email'):
                        logger.info(f"🔐 Auth check bypass: Found user info {user_info.get('email')}, treating as authenticated")
                        is_authenticated = True
                
                if not is_authenticated:
                    # Show login dialog immediately when user clicks account
                    logger.info("🔐 User clicked account but not authenticated - showing login dialog")
                    login_success = self.show_login_dialog()
                    
                    # Only proceed to account page if login was successful
                    if not login_success:
                        # Don't switch to account page if login failed/cancelled
                        logger.info("🔐 Login cancelled or failed - staying on current page")
                        return
                    else:
                        # Update authentication state after successful login
                        self.update_auth_state(True)
                else:
                    # User is authenticated, update the auth state UI
                    logger.info("🔐 User is authenticated, proceeding to account page")
                    self.update_auth_state(True)
                    
            except Exception as e:
                logger.error(f"Error checking authentication for account page: {e}")
                # Fall through to normal page switching if there's an error
        
        if page_name in self.pages:
            page_widget = self.pages[page_name]
            self.content_stack.setCurrentWidget(page_widget)
            
            if hasattr(page_widget, 'on_page_activated'):
                page_widget.on_page_activated()
            
            # Update navigation button state
            if hasattr(self.navigation, 'set_active_page'):
                self.navigation.set_active_page(page_name)
            
            self.current_page = page_name
            logger.info(f"📄 Switched to page: {page_name}")
    
    def _create_lazy_page(self, page_name: str):
        """Create a page on-demand for lazy loading."""
        if not hasattr(self, '_lazy_pages') or page_name not in self._lazy_pages:
            logger.warning(f"⚠️ Unknown page requested: {page_name}")
            return
        
        page_config = self._lazy_pages[page_name]
        if page_config.get("created", False):
            return  # Already created
        
        try:
            logger.info(f"🏗️ LAZY LOADING: Creating {page_name} page...")
            
            if page_config.get("placeholder", False):
                # Create placeholder pages
                page_widget = self.create_placeholder_page(page_name)
            elif page_name == "pedals":
                # Dynamic import for pedals page
                from ..pages.pedals import PedalsPage
                page_widget = PedalsPage(self.global_managers)
            elif page_name == "race_coach":
                # Dynamic import for race coach page
                from ..pages.race_coach import CoachPage
                page_widget = CoachPage(self.global_managers)
            elif page_name == "overlays":
                # Dynamic import for overlays page
                from ..pages.overlays import OverlaysPage
                page_widget = OverlaysPage(self.global_managers)
            elif page_name == "race_pass":
                # Dynamic import for race pass page
                from ..pages.race_pass import RacePassPage
                page_widget = RacePassPage(self.global_managers)
            elif page_name == "handbrake":
                # Special handling for handbrake page
                from ..pages.handbrake import HandbrakePage
                page_widget = HandbrakePage(self.global_managers)
            elif page_name == "support":
                # Special handling for support page
                from ..pages.support import SupportPage
                page_widget = SupportPage(self.global_managers)
            elif page_name == "account":
                # Special handling for account page
                page_widget = self.create_account_page()
            elif page_config["class"]:
                # Standard page creation
                page_widget = page_config["class"](self.global_managers)
            else:
                logger.error(f"❌ No creation method for page: {page_name}")
                return
            
            # Add to content stack and store reference
            self.content_stack.addWidget(page_widget)
            self.pages[page_name] = page_widget
            
            # Special signal connections
            if page_name == "pedals" and hasattr(page_widget, 'pedal_calibrated'):
                page_widget.pedal_calibrated.connect(
                    lambda pedal, data: self.calibration_updated.emit(pedal)
                )
            
            page_config["created"] = True
            logger.info(f"✅ LAZY LOADING: {page_name} page created successfully")
            
        except Exception as e:
            logger.error(f"❌ LAZY LOADING: Failed to create {page_name} page: {e}")
            # Create a placeholder as fallback
            placeholder = self.create_placeholder_page(page_name)
            self.content_stack.addWidget(placeholder)
            self.pages[page_name] = placeholder
    
    def handle_optimized_ui_update(self, pedal_data):
        if self.current_page == "pedals" and "pedals" in self.pages:
            self.pages["pedals"].handle_hardware_update(pedal_data)
    
    def handle_performance_warning(self, warning_type: str, time_ms: float):
        if time_ms > 20.0:
            logger.warning(f"⚠️ PERFORMANCE WARNING: {warning_type} took {time_ms:.1f}ms (target <16ms)")
    
    def set_input_value(self, pedal: str, value: int):
        if self.global_managers.performance:
            self.global_managers.performance.queue_ui_update({pedal: value})
        elif self.current_page == "pedals" and "pedals" in self.pages:
            self.pages["pedals"].handle_hardware_update({pedal: value})
    
    def set_pedal_available(self, pedal: str, available: bool):
        if "pedals" in self.pages:
            self.pages["pedals"].set_pedal_available(pedal, available)
    
    def get_pedal_calibration(self, pedal: str):
        if "pedals" in self.pages:
            return self.pages["pedals"].get_pedal_calibration(pedal)
        return None
    
    def statusBar(self):
        return super().statusBar()
    
    @property
    def stacked_widget(self):
        return self.content_stack
    
    def create_account_page(self):
        """Create the modern account page with sidebar navigation."""
        from ..pages.account.account_page import AccountPage
        
        # Create the account page with global managers
        account_page = AccountPage(self.global_managers)
        
        # Store reference for authentication updates
        account_page.update_auth_status = lambda authenticated: self.update_account_page_auth_status(authenticated)
        
        logger.info("✅ Modern Account page created with sidebar navigation")
        return account_page
    
    def create_user_profile_form(self):
        """Create a user profile form for entering personal information."""
        from PyQt6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, 
                                     QLineEdit, QPushButton, QTextEdit, QFrame)
        from PyQt6.QtCore import Qt
        
        # Main profile group
        profile_group = QGroupBox("User Profile")
        profile_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #fefefe;
                border: 2px solid #444;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        profile_layout = QVBoxLayout(profile_group)
        profile_layout.setSpacing(15)
        
        # Form container
        form_container = QFrame()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(12)
        
        # First Name
        first_name_layout = QHBoxLayout()
        first_name_label = QLabel("First Name:")
        first_name_label.setFixedWidth(100)
        first_name_label.setStyleSheet("color: #fefefe; font-weight: bold; font-size: 14px;")
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Enter your first name")
        self.first_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        first_name_layout.addWidget(first_name_label)
        first_name_layout.addWidget(self.first_name_input)
        form_layout.addLayout(first_name_layout)
        
        # Last Name
        last_name_layout = QHBoxLayout()
        last_name_label = QLabel("Last Name:")
        last_name_label.setFixedWidth(100)
        last_name_label.setStyleSheet("color: #fefefe; font-weight: bold; font-size: 14px;")
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Enter your last name")
        self.last_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        last_name_layout.addWidget(last_name_label)
        last_name_layout.addWidget(self.last_name_input)
        form_layout.addLayout(last_name_layout)
        
        # Display Name (optional)
        display_name_layout = QHBoxLayout()
        display_name_label = QLabel("Display Name:")
        display_name_label.setFixedWidth(100)
        display_name_label.setStyleSheet("color: #fefefe; font-weight: bold; font-size: 14px;")
        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Optional: How you want to appear to others")
        self.display_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2c;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        display_name_layout.addWidget(display_name_label)
        display_name_layout.addWidget(self.display_name_input)
        form_layout.addLayout(display_name_layout)
        
        # Bio (optional)
        bio_label = QLabel("Bio:")
        bio_label.setStyleSheet("color: #fefefe; font-weight: bold; font-size: 14px; margin-top: 8px;")
        form_layout.addWidget(bio_label)
        
        self.bio_input = QTextEdit()
        self.bio_input.setPlaceholderText("Tell us about yourself (optional)")
        self.bio_input.setMaximumHeight(80)
        self.bio_input.setStyleSheet("""
            QTextEdit {
                background-color: #2c2c2c;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #0066cc;
            }
        """)
        form_layout.addWidget(self.bio_input)
        
        profile_layout.addWidget(form_container)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        # Save Profile Button
        self.save_profile_button = QPushButton("💾 Save Profile")
        self.save_profile_button.setMinimumHeight(40)
        self.save_profile_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
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
        self.save_profile_button.clicked.connect(self.save_user_profile)
        buttons_layout.addWidget(self.save_profile_button)
        
        # Load Profile Button
        self.load_profile_button = QPushButton("🔄 Reload Profile")
        self.load_profile_button.setMinimumHeight(40)
        self.load_profile_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """)
        self.load_profile_button.clicked.connect(self.load_user_profile)
        buttons_layout.addWidget(self.load_profile_button)
        
        buttons_layout.addStretch()
        profile_layout.addLayout(buttons_layout)
        
        return profile_group
    
    def update_account_page_auth_status(self, authenticated):
        """Update the account page UI based on authentication status."""
        try:
            # Check if account page elements exist before updating
            if not hasattr(self, 'auth_status_label'):
                logger.debug("🔍 Account page elements not created yet - skipping auth status update")
                return
                
            if authenticated:
                # Show user as logged in
                self.auth_status_label.setText("✅ You are logged in")
                self.auth_status_label.setStyleSheet("font-size: 14px; color: #28a745; padding: 10px; font-weight: bold;")
                
                # Try to get user info
                try:
                    from trackpro.database.supabase_client import supabase
                    user = supabase.get_user()
                    if user and hasattr(user, 'user') and user.user:
                        email = user.user.email or "No email available"
                        # Get user metadata for name
                        metadata = getattr(user.user, 'user_metadata', {})
                        name = metadata.get('full_name') or metadata.get('name') or "No name available"
                        
                        if hasattr(self, 'user_email_label'):
                            self.user_email_label.setText(f"📧 {email}")
                        if hasattr(self, 'user_name_label'):
                            self.user_name_label.setText(f"👤 {name}")
                        if hasattr(self, 'user_info_container'):
                            self.user_info_container.setVisible(True)
                    else:
                        if hasattr(self, 'user_info_container'):
                            self.user_info_container.setVisible(False)
                except Exception as e:
                    logger.error(f"Error getting user info: {e}")
                    if hasattr(self, 'user_info_container'):
                        self.user_info_container.setVisible(False)
                
                # Show logout button, hide login/signup
                if hasattr(self, 'login_button'):
                    self.login_button.setVisible(False)
                if hasattr(self, 'signup_button'):
                    self.signup_button.setVisible(False)
                if hasattr(self, 'logout_button'):
                    self.logout_button.setVisible(True)
                
                # Show profile form and load profile data
                if hasattr(self, 'profile_group'):
                    self.profile_group.setVisible(True)
                    self.load_user_profile()
                
            else:
                # Show user as not logged in
                self.auth_status_label.setText("❌ You are not logged in")
                self.auth_status_label.setStyleSheet("font-size: 14px; color: #dc3545; padding: 10px; font-weight: bold;")
                
                # Hide user info
                if hasattr(self, 'user_info_container'):
                    self.user_info_container.setVisible(False)
                
                # Show login/signup buttons, hide logout
                if hasattr(self, 'login_button'):
                    self.login_button.setVisible(True)
                if hasattr(self, 'signup_button'):
                    self.signup_button.setVisible(True)
                if hasattr(self, 'logout_button'):
                    self.logout_button.setVisible(False)
                
                # Hide profile form when not authenticated
                if hasattr(self, 'profile_group'):
                    self.profile_group.setVisible(False)
                
        except Exception as e:
            logger.error(f"Error updating account page auth status: {e}")
    
    def save_user_profile(self):
        """Save user profile information to the database."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            from trackpro.database.supabase_client import supabase
            
            # Get form data
            first_name = self.first_name_input.text().strip()
            last_name = self.last_name_input.text().strip()
            display_name = self.display_name_input.text().strip()
            bio = self.bio_input.toPlainText().strip()
            
            # Validate required fields
            if not first_name or not last_name:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please enter both first name and last name."
                )
                return
            
            # Get current user
            user = supabase.get_user()
            if not user or not hasattr(user, 'user') or not user.user:
                QMessageBox.critical(
                    self,
                    "Authentication Error", 
                    "You must be logged in to save your profile."
                )
                return
            
            user_id = user.user.id
            email = user.user.email
            
            # Prepare profile data for user_details table
            profile_data = {
                'user_id': user_id,
                'first_name': first_name,
                'last_name': last_name,
                'updated_at': 'now()'
            }
            
            # Note: user_details table doesn't have display_name or bio fields
            # Those would go in user_profiles table if needed later
            
            # Save to database (upsert to handle both insert and update)
            result = supabase.client.table('user_details').upsert(profile_data).execute()
            
            if result.data:
                QMessageBox.information(
                    self,
                    "Profile Saved",
                    "Your profile has been saved successfully!"
                )
                
                # Update navigation with new name immediately
                self.update_auth_state(True)
                logger.info(f"✅ Profile saved for user: {first_name} {last_name}")
                
            else:
                QMessageBox.warning(
                    self,
                    "Save Error",
                    "There was an issue saving your profile. Please try again."
                )
                
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save profile: {str(e)}"
            )
    
    def load_user_profile(self):
        """Load user profile information from the database."""
        try:
            from trackpro.database.supabase_client import supabase
            
            # Get current user
            user = supabase.get_user()
            if not user or not hasattr(user, 'user') or not user.user:
                logger.debug("No authenticated user to load profile for")
                return
            
            user_id = user.user.id
            
            # Fetch profile from database
            result = supabase.client.table('user_details').select('*').eq('user_id', user_id).execute()
            
            if result.data and len(result.data) > 0:
                profile = result.data[0]
                
                # Populate form fields from user_details table
                self.first_name_input.setText(profile.get('first_name', ''))
                self.last_name_input.setText(profile.get('last_name', ''))
                # Note: display_name and bio are not in user_details table
                self.display_name_input.setText('')  # Clear since not stored in user_details
                self.bio_input.setPlainText('')  # Clear since not stored in user_details
                
                logger.info(f"✅ Profile loaded for user: {profile.get('first_name', '')} {profile.get('last_name', '')}")
                
            else:
                # No profile found - clear form fields
                self.first_name_input.clear()
                self.last_name_input.clear()
                self.display_name_input.clear()
                self.bio_input.clear()
                
                logger.info("📝 No existing profile found - ready for user to enter information")
                
        except Exception as e:
            logger.error(f"Error loading user profile: {e}")
    
    def show_login_dialog(self):
        """Show the login dialog."""
        try:
            from trackpro.auth.login_dialog import LoginDialog
            
            login_dialog = LoginDialog(self, oauth_handler=self.oauth_handler)
            result = login_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user logged in)
                # Get user info and start app tracking
                user_info = self.get_current_user_info()
                if user_info and user_info.get('id'):
                    self.start_app_tracking(user_info['id'])
                    self.update_user_online_status(user_info['id'], True)
                    
                    # Force refresh sidebar to show current user
                    if hasattr(self, 'online_users_sidebar'):
                        self.online_users_sidebar.force_refresh()
                
                # Update authentication state immediately
                self.update_auth_state(True)
                logger.info("🔐 User successfully logged in - updating navigation")
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
    
    def show_signup_dialog(self):
        """Show the signup dialog."""
        try:
            from trackpro.auth.signup_dialog import SignupDialog
            
            signup_dialog = SignupDialog(self, oauth_handler=self.oauth_handler)
            result = signup_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user signed up)
                # Get user info and start app tracking
                user_info = self.get_current_user_info()
                if user_info and user_info.get('id'):
                    self.start_app_tracking(user_info['id'])
                    self.update_user_online_status(user_info['id'], True)
                    
                    # Force refresh sidebar to show current user
                    if hasattr(self, 'online_users_sidebar'):
                        self.online_users_sidebar.force_refresh()
                
                # Update authentication state immediately
                self.update_auth_state(True)
                logger.info("🔐 User successfully signed up - updating navigation")
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
    
    def logout_user(self):
        """Log out the current user."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # Confirm logout
            reply = QMessageBox.question(
                self,
                "Confirm Logout",
                "Are you sure you want to log out?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Stop app tracking before logout
                self.stop_app_tracking()
                
                # Perform logout
                from trackpro.database.supabase_client import supabase
                supabase.sign_out()
                
                # Update UI immediately
                self.update_auth_state(False)
                logger.info("🔐 User successfully logged out - updating navigation")
                
                # Navigate to home page after logout
                self.switch_to_page("home")
                logger.info("🏠 Navigated to home page after logout")
                
                # Show confirmation
                QMessageBox.information(
                    self,
                    "Logged Out",
                    "You have been successfully logged out."
                )
                
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, 
                "Logout Error", 
                f"Could not log out: {str(e)}"
            )
    
    def update_auth_state(self, authenticated):
        """Update the entire UI based on authentication state."""
        try:
            # PERFORMANCE: Skip if this is a duplicate call during startup
            if not self._startup_auth_check_completed and hasattr(self, '_last_auth_state'):
                if self._last_auth_state == authenticated:
                    logger.debug("🔄 Skipping duplicate auth state update during startup")
                    return
            
            logger.info(f"🔐 Updating UI auth state: {authenticated}")
            
            # Cache the auth state to prevent duplicate calls
            self._last_auth_state = authenticated
            
            # Get user information if authenticated (cache it to avoid repeated calls)
            user_info = None
            if authenticated:
                if self._cached_user_info is None:
                    self._cached_user_info = self.get_current_user_info()
                user_info = self._cached_user_info
            
            # Update navigation with authentication state
            if hasattr(self, 'navigation') and hasattr(self.navigation, 'update_authentication_state'):
                self.navigation.update_authentication_state(authenticated, user_info)
                logger.info(f"🔐 Updated navigation with user info: {user_info}")
            
            # Update account page if it exists
            if "account" in self.pages and hasattr(self.pages["account"], 'update_auth_status'):
                self.pages["account"].update_auth_status(authenticated)
            else:
                # Call the method directly
                self.update_account_page_auth_status(authenticated)
            
            # Update menu bar logout action visibility
            if hasattr(self, 'logout_action'):
                self.logout_action.setVisible(authenticated)
            
            # Update menu bar logout button visibility
            if hasattr(self, 'logout_btn'):
                self.logout_btn.setVisible(authenticated)
            
            # Update menu bar login/signup button visibility
            if hasattr(self, 'login_btn'):
                self.login_btn.setVisible(not authenticated)
            if hasattr(self, 'signup_btn'):
                self.signup_btn.setVisible(not authenticated)
            
            # Emit signal for other components
            self.auth_state_changed.emit(authenticated)
            
            # Force refresh sidebar when authentication state changes
            self.force_refresh_sidebar()
            
            # Update all pages that need authentication state
            for page_name, page in self.pages.items():
                if hasattr(page, 'on_auth_state_changed'):
                    page.on_auth_state_changed()
            
            # Mark startup auth check as completed
            self._startup_auth_check_completed = True
            
        except Exception as e:
            logger.error(f"Error updating auth state: {e}")
    
    def refresh_auth_state(self):
        """Manually refresh authentication state - useful for fixing sync issues."""
        try:
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            
            if supabase_client:
                # Check if we have a valid user
                user_response = supabase_client.auth.get_user()
                session = supabase_client.auth.get_session()
                
                is_authenticated = bool(
                    (user_response and user_response.user) or 
                    (session and session.user)
                )
                
                logger.info(f"🔄 Auth state refresh: authenticated={is_authenticated}")
                self.update_auth_state(is_authenticated)
            else:
                # If Supabase client is not available, try to initialize it
                logger.info("🔄 Supabase client not available, attempting to initialize...")
                # The client should auto-initialize on first access, so just try again
                supabase_client = get_supabase_client()
                if supabase_client:
                    user_response = supabase_client.auth.get_user()
                    session = supabase_client.auth.get_session()
                    
                    is_authenticated = bool(
                        (user_response and user_response.user) or 
                        (session and session.user)
                    )
                    
                    logger.info(f"🔄 Auth state refresh after init: authenticated={is_authenticated}")
                    self.update_auth_state(is_authenticated)
                else:
                    logger.info("ℹ️ Supabase client not available - continuing without authentication")
                
        except Exception as e:
            logger.error(f"Error refreshing auth state: {e}")
    
    def force_auth_refresh_after_login(self):
        """Force refresh authentication state after successful login."""
        try:
            logger.info("🔄 Force refreshing authentication state after login...")
            
            # First, ensure Supabase client is initialized
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            
            if not supabase_client:
                logger.info("ℹ️ Supabase client not available, trying to initialize...")
                # The client should auto-initialize on first access, so just try again
                supabase_client = get_supabase_client()
            
            if supabase_client:
                # Force a session refresh
                try:
                    session = supabase_client.auth.get_session()
                    if session and session.user:
                        logger.info("✅ Found valid session, updating UI...")
                        self.update_auth_state(True)
                        
                                    # Also update all pages that need authentication state
                        if "home" in self.pages:
                            self.pages["home"].refresh_header()
                            # Also call the auth state changed method
                            if hasattr(self.pages["home"], 'on_auth_state_changed'):
                                self.pages["home"].on_auth_state_changed()
                        
                        return True
                except Exception as session_error:
                    logger.error(f"Error getting session: {session_error}")
            
            # Fallback: try user manager
            try:
                from trackpro.auth.user_manager import get_current_user
                current_user = get_current_user()
                if current_user is None:
                    # User manager not ready yet - skip authentication check
                    logger.info("🔍 User manager not ready yet - skipping authentication check")
                    return False
                if current_user and current_user.is_authenticated:
                    logger.info("✅ Found authenticated user via user manager")
                    self.update_auth_state(True)
                    return True
            except Exception as user_error:
                logger.error(f"Error checking user manager: {user_error}")
            
            logger.warning("⚠️ Could not verify authentication state")
            return False
            
        except Exception as e:
            logger.error(f"Error in force_auth_refresh_after_login: {e}")
            return False
    
    def get_current_user_info(self):
        """Get current user information from the authentication system and profile database."""
        try:
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            if not supabase_client:
                # Fallback to user manager if Supabase client isn't available
                try:
                    from trackpro.auth.user_manager import get_current_user
                    current_user = get_current_user()
                    if current_user is None:
                        return None
                    if current_user and current_user.is_authenticated:
                        return {
                            'email': current_user.email,
                            'name': current_user.name,
                            'user_id': current_user.id
                        }
                except Exception as fallback_error:
                    logger.error(f"Error getting user from user manager: {fallback_error}")
                return None
            
            # Use the correct auth.get_user method
            user_response = supabase_client.auth.get_user()
            
            # Also try to get session info as fallback
            if not user_response or not user_response.user:
                session = supabase_client.auth.get_session()
                if session and session.user:
                    user_response = session
            
            if user_response and hasattr(user_response, 'user') and user_response.user:
                user = user_response.user
                
                email = user.email or "No email available"
                user_id = user.id
                
                name = "User"  # Default fallback
                
                # First, try to get name from user metadata (fastest and already available)
                metadata = getattr(user, 'user_metadata', {})
                
                # Try different metadata fields for name
                if metadata.get('full_name'):
                    name = metadata['full_name']
                elif metadata.get('name'):
                    name = metadata['name']
                elif metadata.get('first_name') and metadata.get('last_name'):
                    # Handle case sensitivity - first_name might be uppercase
                    first_name = metadata['first_name']
                    last_name = metadata['last_name']
                    # Convert to proper case if all caps
                    if first_name.isupper():
                        first_name = first_name.title()
                    if last_name.isupper():
                        last_name = last_name.title()
                    name = f"{first_name} {last_name}"
                elif metadata.get('first_name'):
                    first_name = metadata['first_name']
                    if first_name.isupper():
                        first_name = first_name.title()
                    name = first_name
                elif metadata.get('display_name'):
                    name = metadata['display_name']
                elif metadata.get('username'):
                    name = metadata['username']
                elif metadata.get('preferred_username'):
                    name = metadata['preferred_username']
                
                # If no name from metadata, fallback to user_details table
                if name == "User":
                    try:
                        profile_result = supabase_client.table('user_details').select('first_name, last_name').eq('user_id', user_id).execute()
                        
                        if profile_result.data and len(profile_result.data) > 0:
                            profile = profile_result.data[0]
                            
                            # Combine first and last name from user_details table
                            if profile.get('first_name') and profile.get('last_name'):
                                name = f"{profile['first_name']} {profile['last_name']}"
                            elif profile.get('first_name'):
                                name = profile['first_name']
                    except Exception as db_error:
                        logger.debug(f"Could not get user details from database: {db_error}")
                
                return {
                    'email': email,
                    'name': name,
                    'user_id': user_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current user info: {e}")
            return None
    

    def check_authentication_on_account_click(self):
        """Check authentication when account page is requested."""
        try:
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            
            is_authenticated = False
            
            # Try Supabase client first
            if supabase_client:
                try:
                    session = supabase_client.auth.get_session()
                    is_authenticated = bool(session and session.user)
                except Exception as supabase_error:
                    logger.warning(f"Error checking Supabase auth: {supabase_error}")
            
            # Fallback to user manager
            if not is_authenticated:
                try:
                    from trackpro.auth.user_manager import get_current_user
                    current_user = get_current_user()
                    is_authenticated = current_user and current_user.is_authenticated
                    logger.info(f"🔍 Account click auth check via user manager: {is_authenticated}")
                except Exception as user_manager_error:
                    logger.warning(f"Error checking user manager auth: {user_manager_error}")
            
            if not is_authenticated:
                # Show login dialog immediately
                logger.info("🔐 User clicked account but not authenticated - showing login dialog")
                self.show_login_dialog()
            
            return is_authenticated
            
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False
    
    def on_user_selected(self, user_data):
        """Handle user selection from the online users sidebar."""
        logger.info(f"👤 User selected: {user_data.get('name', 'Unknown')}")
        # Eventually this will open a chat window or user profile
        # For now, just log the selection
    
    def on_private_message_requested(self, user_data):
        """Handle private message request from sidebar."""
        logger.info(f"Private message requested for user: {user_data.get('display_name', 'Unknown')}")
        
        # Switch to community page and start private conversation
        self.switch_to_page("community")
        
        # Get the community page and start private conversation
        community_page = self.get_page("community")
        if community_page and hasattr(community_page, 'start_private_conversation_with_user'):
            community_page.start_private_conversation_with_user(user_data)
    
    def on_sidebar_toggled(self, is_expanded):
        """Handle online users sidebar toggle."""
        logger.info(f"📱 Online users sidebar {'expanded' if is_expanded else 'collapsed'}")
    
    def force_refresh_sidebar(self):
        """Force refresh the online users sidebar."""
        if hasattr(self, 'online_users_sidebar'):
            self.online_users_sidebar.force_refresh()
            logger.info("🔄 Forced refresh of online users sidebar")
        # Could save preference or adjust layout here if needed
    
    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for the application."""
        try:
            from PyQt6.QtGui import QKeySequence, QShortcut
            
            # Force refresh authentication state (Ctrl+Shift+R)
            refresh_auth_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
            refresh_auth_shortcut.activated.connect(self.force_auth_refresh_after_login)
            
            logger.info("✅ Keyboard shortcuts configured")
            
        except Exception as e:
            logger.error(f"Error setting up keyboard shortcuts: {e}")
    
    def cleanup(self):
        """Clean up resources before window closes."""
        if self._is_shutting_down:
            return
            
        logger.info("🧹 Starting main window cleanup...")
        self._is_shutting_down = True
        
        try:
            # Stop UI update timer first
            if self.ui_update_timer:
                try:
                    self.ui_update_timer.stop()
                    self.ui_update_timer = None
                    logger.info("✅ UI update timer stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping UI update timer: {e}")
            
            # Set destruction flag on all pages first to prevent new thread creation
            for page_name, page in self.pages.items():
                if hasattr(page, '_is_being_destroyed'):
                    page._is_being_destroyed = True
                # Also set flag on sub-pages if they exist
                if hasattr(page, 'sub_pages'):
                    for sub_page in page.sub_pages.values():
                        if hasattr(sub_page, '_is_being_destroyed'):
                            sub_page._is_being_destroyed = True
            
            # Now cleanup all pages
            for page_name, page in self.pages.items():
                if hasattr(page, 'cleanup'):
                    try:
                        page.cleanup()
                        logger.info(f"✅ Cleaned up {page_name} page")
                    except Exception as e:
                        logger.error(f"Error cleaning up {page_name}: {e}")
            
            # Cleanup global managers
            if hasattr(self.global_managers, 'iracing') and self.global_managers.iracing:
                try:
                    if hasattr(self.global_managers.iracing, 'stop'):
                        self.global_managers.iracing.stop()
                    logger.info("✅ Cleaned up iRacing monitor")
                except Exception as e:
                    logger.error(f"Error cleaning up iRacing monitor: {e}")
            
            if hasattr(self.global_managers, 'performance') and self.global_managers.performance:
                try:
                    if hasattr(self.global_managers.performance, 'stop'):
                        self.global_managers.performance.stop()
                    logger.info("✅ Cleaned up performance manager")
                except Exception as e:
                    logger.error(f"Error cleaning up performance manager: {e}")
                    
            logger.info("🧹 Main window cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during main window cleanup: {e}")
    
    def _emergency_exit(self):
        """Emergency exit method when normal shutdown fails."""
        try:
            logger.warning("🚨 Emergency exit triggered - forcing system exit")
            import sys
            import os
            # Try to kill all related processes first
            try:
                import psutil
                current_process = psutil.Process()
                for child in current_process.children(recursive=True):
                    try:
                        child.terminate()
                    except:
                        pass
            except ImportError:
                pass
            
            # Force exit
            os._exit(0)
        except Exception as e:
            logger.error(f"Error in emergency exit: {e}")
            # Last resort
            import sys
            sys.exit(1)
    
    def closeEvent(self, event):
        """Handle application closing with proper cleanup."""
        logger.info("🧹 Window close event triggered...")
        
        try:
            # Stop app tracking before cleanup
            self.stop_app_tracking()
            
            # Call our cleanup method
            self.cleanup()
        except Exception as e:
            logger.error(f"Error during closeEvent cleanup: {e}")
        
        # Accept the close event
        event.accept()
        super().closeEvent(event)
        
        # Force quit the application to ensure it closes properly
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        app = QApplication.instance()
        if app:
            logger.info("🚪 Forcing application quit...")
            # Schedule application quit to happen after cleanup is complete
            QTimer.singleShot(100, app.quit)
            # Also ensure the app exits even if quit() doesn't work
            QTimer.singleShot(500, lambda: app.exit(0))
            # Emergency exit if all else fails
            QTimer.singleShot(2000, self._emergency_exit)