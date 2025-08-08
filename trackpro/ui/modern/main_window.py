import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, QLabel, QSystemTrayIcon, QMenu
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QIcon, QAction
from ..discord_navigation import DiscordNavigation
from ..online_users_sidebar import OnlineUsersSidebar
from .shared.base_page import GlobalManagers
from .performance_manager import PerformanceManager, ThreadPriorityManager, CPUCoreManager
# Import only what we need immediately to avoid circular imports
from ..pages.home import HomePage
from ..pages.community import CommunityPage
# App tracking
from trackpro.utils.app_tracker import start_app_tracking, stop_app_tracking, update_user_online_status, update_app_tracker_user_id

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
        
        # Initialize updater and check for updates on startup
        self.init_updater()
        
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
        title_label = QLabel("TrackPro by Sim Coaches")
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
        """Initialize global managers without duplicating hardware systems."""
        # Defer hardware initialization until global systems are ready
        # This prevents creating duplicate HardwareInput instances
        self.global_managers.hardware = None
        
        # Defer iRacing API initialization to when global API is ready
        # This prevents early access attempts that fail during startup
        self.global_managers.iracing = None
        
        self.global_managers.auth = self.oauth_handler
        logger.info("✅ Global managers initialized (hardware deferred)")
    
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
        
        # Set window icon to match system tray icon (only if not already set by application)
        try:
            # Check if application already set an icon
            from PyQt6.QtWidgets import QApplication
            app_icon = QApplication.instance().windowIcon()
            if app_icon.isNull():
                import os
                current_dir = os.path.dirname(__file__)
                
                # Try ICO first (user preference)
                icon_path = os.path.join(current_dir, "..", "..", "resources", "icons", "trackpro-tray-1.ico")
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))
                    logger.info(f"✅ Set window icon from: {icon_path}")
                else:
                    # Try PNG as fallback
                    png_icon_path = os.path.join(current_dir, "..", "..", "resources", "icons", "trackpro_tray.png")
                    if os.path.exists(png_icon_path):
                        self.setWindowIcon(QIcon(png_icon_path))
                        logger.info(f"✅ Set window icon from: {png_icon_path}")
                    else:
                        logger.warning("⚠️ Could not find window icon, using default")
        except Exception as e:
            logger.warning(f"⚠️ Error setting window icon: {e}")
        
        # Force taskbar icon update on Windows
        try:
            import ctypes
            from ctypes import wintypes
            
            # Set the application ID for Windows taskbar
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TrackPro.TrackPro")
            
            # Force Windows to refresh the taskbar icon
            hwnd = self.winId().__int__()
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                wintypes.DWORD(0x0001 | 0x0002 | 0x0004 | 0x0040)  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED
            )
            
            logger.info("✅ Forced taskbar icon update")
        except Exception as e:
            logger.warning(f"⚠️ Error forcing taskbar icon update: {e}")
        
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
        
        # Set up system tray
        self.setup_system_tray()
    
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
        
        # Store reference to sidebar for later connections
        self.online_users_sidebar = sidebar
        
        return sidebar
    
    def create_pages(self):
        """PERFORMANCE OPTIMIZATION: Pre-load commonly used pages, lazy-load others."""
        # Create the actual Home page immediately (it's always the first one shown)
        self.pages["home"] = HomePage(self.global_managers)
        self.content_stack.addWidget(self.pages["home"])
        
        # Connect auth state changes to home page refresh
        if hasattr(self.pages["home"], 'on_auth_state_changed'):
            self.auth_state_changed.connect(self.pages["home"].on_auth_state_changed)
        
        logger.info("✅ Home page integrated into modern UI")
        
        # LAZY LOADING: Do not pre-load heavy pages on startup. Create on demand.
        self._lazy_pages = {
            "community": {"class": None, "created": False},  # Dynamic import
            "race_coach": {"class": None, "created": False},  # Dynamic import
            "pedals": {"class": None, "created": False},      # Dynamic import
            "overlays": {"class": None, "created": False},
            "race_pass": {"class": None, "created": False},
            "handbrake": {"class": None, "created": False},
            "support": {"class": None, "created": False},
            "account": {"class": None, "created": False},
        }
        
        logger.info("🚀 PERFORMANCE: Startup minimized. Pages will be created on first use (lazy-loaded)")
    
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
                
                # Remove unsafe bypass: rely strictly on Supabase manager auth state
                if not is_authenticated:
                    try:
                        from trackpro.database.supabase_client import supabase as supabase_manager
                        is_authenticated = supabase_manager.is_authenticated()
                        logger.info(f"🔐 Verified auth via manager: {is_authenticated}")
                    except Exception:
                        is_authenticated = False
                
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
        
        # Prevent creating pages that are already pre-loaded
        if page_name in self.pages:
            logger.info(f"🔄 {page_name} page already exists, skipping lazy creation")
            return
        
        page_config = self._lazy_pages[page_name]
        if page_config.get("created", False):
            return  # Already created
        
        try:
            logger.info(f"🏗️ LAZY LOADING: Creating {page_name} page...")
            
            if page_config.get("placeholder", False):
                page_widget = self.create_placeholder_page(page_name)
            elif page_name == "community":
                from ..pages.community import CommunityPage
                page_widget = CommunityPage(self.global_managers)
            elif page_name == "pedals":
                from ..pages.pedals import PedalsPage
                page_widget = PedalsPage(self.global_managers)
            elif page_name == "race_coach":
                from ..pages.race_coach.coming_soon_page import RaceCoachComingSoonPage
                page_widget = RaceCoachComingSoonPage(self.global_managers)
            elif page_name == "overlays":
                from ..pages.overlays import OverlaysPage
                page_widget = OverlaysPage(self.global_managers)
            elif page_name == "race_pass":
                from ..pages.race_pass import RacePassPage
                page_widget = RacePassPage(self.global_managers)
            elif page_name == "handbrake":
                from ..pages.handbrake import HandbrakePage
                page_widget = HandbrakePage(self.global_managers)
            elif page_name == "support":
                from ..pages.support import SupportPage
                page_widget = SupportPage(self.global_managers)
                # Keep support chat synced with auth changes for live updates
                try:
                    self.auth_state_changed.connect(page_widget.on_auth_state_changed)
                except Exception:
                    pass
            elif page_name == "account":
                page_widget = self.create_account_page()
                
                # Connect avatar upload signal to sidebar refresh
                if hasattr(self, 'online_users_sidebar') and hasattr(page_widget, 'avatar_uploaded'):
                    page_widget.avatar_uploaded.connect(self.online_users_sidebar.on_avatar_updated)
                
                # Connect avatar upload signal to navigation refresh
                if hasattr(self, 'navigation') and hasattr(page_widget, 'avatar_uploaded'):
                    page_widget.avatar_uploaded.connect(self.navigation.on_avatar_updated)
                
                # Connect avatar upload signal to home page refresh
                if hasattr(self, 'pages') and 'home' in self.pages:
                    page_widget.avatar_uploaded.connect(lambda: self.pages['home'].on_auth_state_changed())
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
        
        # Connect avatar upload signal to refresh navigation
        account_page.avatar_uploaded.connect(self.on_avatar_uploaded)
        
        # Connect avatar upload signal to sidebar refresh
        if hasattr(self, 'online_users_sidebar'):
            account_page.avatar_uploaded.connect(self.online_users_sidebar.on_avatar_updated)
        
        # Connect avatar upload signal to navigation refresh
        if hasattr(self, 'navigation'):
            account_page.avatar_uploaded.connect(self.navigation.on_avatar_updated)
        
        # Connect avatar upload signal to home page refresh
        if hasattr(self, 'pages') and 'home' in self.pages:
            account_page.avatar_uploaded.connect(lambda: self.pages['home'].on_auth_state_changed())
        
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
            logger.info("🔄 show_login_dialog started - logging entire process")
            
            from trackpro.auth.login_dialog import LoginDialog
            
            logger.info("✅ LoginDialog imported successfully")
            
            login_dialog = LoginDialog(self, oauth_handler=self.oauth_handler)
            logger.info("✅ LoginDialog created successfully")
            
            logger.info("🔄 Executing login dialog...")
            result = login_dialog.exec()
            logger.info(f"✅ Login dialog executed with result: {result}")
            
            if result == 1:  # Dialog was accepted (user logged in)
                logger.info("🔐 User successfully logged in - processing post-login tasks")
                
                # Get user info and start app tracking
                logger.info("🔍 Getting current user info...")
                user_info = self.get_current_user_info()
                if user_info and user_info.get('id'):
                    logger.info(f"✅ Got user info: {user_info.get('name', 'Unknown')}")
                    
                    logger.info("🔄 Starting app tracking...")
                    self.start_app_tracking(user_info['id'])
                    logger.info("✅ App tracking started")
                    
                    logger.info("🔄 Updating user online status...")
                    self.update_user_online_status(user_info['id'], True)
                    logger.info("✅ User online status updated")
                    
                    # Force refresh sidebar to show current user
                    logger.info("🔄 Forcing refresh of online users sidebar...")
                    if hasattr(self, 'online_users_sidebar'):
                        self.online_users_sidebar.force_refresh()
                        logger.info("✅ Online users sidebar refreshed")
                    else:
                        logger.warning("⚠️ No online_users_sidebar found")
                else:
                    logger.warning("⚠️ No user info available after login")
                
                # Update authentication state immediately
                logger.info("🔄 Updating authentication state...")
                self.update_auth_state(True)
                logger.info("✅ Authentication state updated")
                
                logger.info("🔐 User successfully logged in - updating navigation")
                return True
            else:
                logger.info("❌ Login dialog was cancelled or failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error showing login dialog: {e}")
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
                
                # Mark user offline (best effort) before clearing session
                try:
                    current = self.get_current_user_info()
                    if current and current.get('id'):
                        self.update_user_online_status(current.get('id'), False)
                except Exception:
                    pass
                
                # Perform logout with forced session clear and clear in user manager
                try:
                    # Use the Supabase manager directly to avoid attribute mismatches
                    from trackpro.database.supabase_client import supabase as supabase_manager
                    supabase_manager.sign_out(force_clear=True, respect_remember_me=False)
                except Exception:
                    # Fall back to global instance if available
                    try:
                        from trackpro.database.supabase_client import supabase
                        supabase.sign_out(force_clear=True, respect_remember_me=False)
                    except Exception:
                        pass
                
                # Clear cached/current user in local manager
                try:
                    from trackpro.auth.user_manager import logout_current_user
                    logout_current_user()
                except Exception:
                    pass
                
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
        logger.info(f"🔄 update_auth_state called with authenticated={authenticated}")
        
        # CRITICAL: Use defensive programming to prevent crashes
        # Each operation is isolated so failures don't cascade
        
        try:
            # PERFORMANCE: Enhanced debouncing to prevent redundant auth state updates
            import time
            current_time = time.time()
            
            # Skip if this is a duplicate call during startup
            if not self._startup_auth_check_completed and hasattr(self, '_last_auth_state'):
                if self._last_auth_state == authenticated:
                    logger.debug("🔄 Skipping duplicate auth state update during startup")
                    return
            
            # Skip if called too frequently (within 100ms)
            if hasattr(self, '_last_auth_update_time'):
                if current_time - self._last_auth_update_time < 0.1:
                    logger.debug("🔄 Skipping auth state update - called too frequently")
                    return
            
            # Skip if auth refresh is in progress
            if hasattr(self, '_auth_refresh_in_progress') and self._auth_refresh_in_progress:
                logger.debug("🔄 Skipping auth state update - refresh in progress")
                return
            
            logger.info(f"🔐 Updating UI auth state: {authenticated}")
            
            # Cache the auth state and timestamp to prevent duplicate calls
            self._last_auth_state = authenticated
            self._last_auth_update_time = current_time
            
        except Exception as setup_error:
            logger.error(f"❌ Error in auth state setup: {setup_error}")
            # Continue with auth update even if setup fails
        
        # Get user information if authenticated (ISOLATED)
        user_info = None
        if authenticated:
            try:
                logger.info("🔍 Getting user info for authenticated user...")
                if self._cached_user_info is None:
                    self._cached_user_info = self.get_current_user_info()
                user_info = self._cached_user_info
                logger.info(f"✅ User info retrieved: {user_info}")
            except Exception as user_info_error:
                logger.error(f"❌ Error getting user info: {user_info_error}")
                # Continue without user info
        
        # Update navigation with authentication state (ISOLATED)
        try:
            logger.info("🔄 Updating navigation...")
            if hasattr(self, 'navigation') and hasattr(self.navigation, 'update_authentication_state'):
                self.navigation.update_authentication_state(authenticated, user_info)
                logger.info(f"✅ Updated navigation with user info")
            else:
                logger.warning("⚠️ No navigation found or missing update_authentication_state method")
        except Exception as nav_error:
            logger.error(f"❌ Error updating navigation: {nav_error}")
            # Continue with other updates
        
        # Update account page (ISOLATED)
        try:
            logger.info("🔄 Updating account page...")
            if "account" in self.pages and hasattr(self.pages["account"], 'update_auth_status'):
                self.pages["account"].update_auth_status(authenticated)
                logger.info("✅ Account page auth status updated")
            else:
                # Call the method directly
                self.update_account_page_auth_status(authenticated)
                logger.info("✅ Account page auth status updated via direct method")
        except Exception as account_error:
            logger.error(f"❌ Error updating account page: {account_error}")
            # Continue with other updates
        
        # Update menu elements (ISOLATED)
        try:
            logger.info("🔄 Updating menu elements...")
            if hasattr(self, 'logout_action'):
                self.logout_action.setVisible(authenticated)
            if hasattr(self, 'logout_btn'):
                self.logout_btn.setVisible(authenticated)
            if hasattr(self, 'login_btn'):
                self.login_btn.setVisible(not authenticated)
            if hasattr(self, 'signup_btn'):
                self.signup_btn.setVisible(not authenticated)
            logger.info("✅ Menu elements updated")
        except Exception as menu_error:
            logger.error(f"❌ Error updating menu elements: {menu_error}")
            # Continue with other updates
        
        # Emit signal for other components (ISOLATED)
        try:
            logger.info("🔄 Emitting auth state changed signal...")
            self.auth_state_changed.emit(authenticated)
            logger.info("✅ Auth state changed signal emitted")
        except Exception as signal_error:
            logger.error(f"❌ Error emitting auth state signal: {signal_error}")
            import traceback
            logger.error(f"📋 Signal error traceback: {traceback.format_exc()}")
            # Continue with other updates
        
        # Handle app tracking (ISOLATED)
        try:
            logger.info("🔄 Handling app tracking...")
            if authenticated and user_info:
                user_id = user_info.get('id')
                if user_id:
                    logger.info(f"🔐 Starting app tracking for authenticated user: {user_id}")
                    success = update_app_tracker_user_id(user_id)
                    if success:
                        logger.info(f"✅ App tracking started for user: {user_id}")
                    else:
                        logger.warning(f"⚠️ Failed to start app tracking for user: {user_id}")
            else:
                logger.info("🔐 Stopping app tracking - user logged out")
                self.stop_app_tracking()
                logger.info("✅ App tracking stopped")
        except Exception as tracking_error:
            logger.error(f"❌ Error with app tracking: {tracking_error}")
            # Continue with other updates
        
        # Update pages (ISOLATED) - DEFER TO REDUCE CRASH RISK
        try:
            logger.info("🔄 Scheduling deferred page updates...")
            from PyQt6.QtCore import QTimer
            # Defer page updates to reduce immediate crash risk
            QTimer.singleShot(500, lambda: self._update_pages_auth_state())
            logger.info("✅ Page updates scheduled")
        except Exception as page_schedule_error:
            logger.error(f"❌ Error scheduling page updates: {page_schedule_error}")
        
        # Schedule sidebar refresh (deferred)
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self._deferred_sidebar_refresh())
        except Exception as sidebar_schedule_error:
            logger.error(f"❌ Error with sidebar refresh scheduling: {sidebar_schedule_error}")
        
        # Mark as completed
        try:
            self._startup_auth_check_completed = True
            logger.info("✅ Auth state update completed successfully")
        except Exception as completion_error:
            logger.error(f"❌ Error marking auth update complete: {completion_error}")
            try:
                # At minimum, try to emit the signal
                self.auth_state_changed.emit(False)
                logger.info("✅ Emitted fallback auth state signal")
            except:
                logger.error("❌ Failed to emit fallback auth state signal")
                pass
    
    def refresh_auth_state(self):
        """Manually refresh authentication state - useful for fixing sync issues."""
        try:
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            
            if supabase_client:
                try:
                    # Check if we have a valid user
                    user_response = supabase_client.auth.get_user()
                    session = supabase_client.auth.get_session()
                    
                    is_authenticated = bool(
                        (user_response and user_response.user) or 
                        (session and session.user)
                    )
                    
                    logger.info(f"🔄 Auth state refresh: authenticated={is_authenticated}")
                    self.update_auth_state(is_authenticated)
                except Exception as e:
                    logger.error(f"Error checking authentication state: {e}")
                    # If there's an error, assume not authenticated
                    self.update_auth_state(False)
            else:
                # If Supabase client is not available, try to initialize it
                logger.info("🔄 Supabase client not available, attempting to initialize...")
                try:
                    # Force reinitialization
                    from trackpro.database.supabase_client import _supabase_manager
                    if _supabase_manager:
                        _supabase_manager.initialize()
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
                            logger.info("ℹ️ Supabase client still not available after reinitialization")
                            self.update_auth_state(False)
                    else:
                        logger.info("ℹ️ Supabase manager not available - continuing without authentication")
                        self.update_auth_state(False)
                except Exception as e:
                    logger.error(f"Error during Supabase reinitialization: {e}")
                    self.update_auth_state(False)
                
        except Exception as e:
            logger.error(f"Error refreshing auth state: {e}")
            # On error, assume not authenticated
            self.update_auth_state(False)
    
    def force_auth_refresh_after_login(self):
        """Force refresh authentication state after successful login."""
        try:
            logger.info("🔄 Force auth refresh started - logging entire process")
            
            # PERFORMANCE: Prevent multiple simultaneous auth refreshes
            if hasattr(self, '_auth_refresh_in_progress') and self._auth_refresh_in_progress:
                logger.debug("🔄 Auth refresh already in progress, skipping duplicate call")
                return True
                
            # Set flag to prevent duplicate refreshes
            self._auth_refresh_in_progress = True
            logger.info("🔒 Set auth refresh flag to prevent duplicates")
            
            logger.info("🔄 Force refreshing authentication state after login...")
            
            # First, check if we have a user in the user manager
            logger.info("🔍 Checking user manager for authenticated user...")
            from trackpro.auth.user_manager import get_current_user
            current_user = get_current_user()
            if current_user and current_user.is_authenticated:
                logger.info(f"✅ Found authenticated user in user manager: {current_user.email}")
                logger.info("🔄 Updating auth state to True...")
                self.update_auth_state(True)
                logger.info("✅ Auth state updated successfully")
                
                # Also update all pages that need authentication state
                logger.info("🔄 Updating home page...")
                if "home" in self.pages:
                    try:
                        self.pages["home"].refresh_header()
                        logger.info("✅ Home page header refreshed")
                        # Also call the auth state changed method
                        if hasattr(self.pages["home"], 'on_auth_state_changed'):
                            self.pages["home"].on_auth_state_changed()
                            logger.info("✅ Home page auth state changed")
                    except Exception as home_error:
                        logger.error(f"❌ Error updating home page: {home_error}")
                
                # Clear the flag after successful completion
                self._auth_refresh_in_progress = False
                logger.info("🔓 Cleared auth refresh flag")
                return True
            
            # If no user in user manager, try Supabase client
            logger.info("🔍 No user in user manager, trying Supabase client...")
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            
            if not supabase_client:
                logger.info("ℹ️ Supabase client not available, trying to initialize...")
                try:
                    # Force reinitialization
                    from trackpro.database.supabase_client import _supabase_manager
                    if _supabase_manager:
                        _supabase_manager.initialize()
                        supabase_client = get_supabase_client()
                        logger.info("✅ Supabase client reinitialized")
                    else:
                        logger.warning("⚠️ No Supabase manager available")
                except Exception as e:
                    logger.error(f"❌ Error during Supabase reinitialization: {e}")
            
            if supabase_client:
                # Force a session refresh
                logger.info("🔍 Getting session from Supabase...")
                try:
                    session = supabase_client.auth.get_session()
                    if session and session.user:
                        logger.info("✅ Found valid session, updating UI...")
                        
                        # Ensure user is set in user manager
                        logger.info("🔍 Setting user in user manager...")
                        from trackpro.auth.user_manager import User, set_current_user
                        authenticated_user = User(
                            id=session.user.id,
                            email=session.user.email,
                            name=session.user.user_metadata.get('name', session.user.email),
                            is_authenticated=True
                        )
                        set_current_user(authenticated_user)
                        logger.info(f"✅ Set user in user manager from session: {authenticated_user.email}")
                        
                        logger.info("🔄 Updating auth state to True...")
                        self.update_auth_state(True)
                        logger.info("✅ Auth state updated successfully")
                        
                        # Also update all pages that need authentication state
                        logger.info("🔄 Updating home page...")
                        if "home" in self.pages:
                            try:
                                self.pages["home"].refresh_header()
                                logger.info("✅ Home page header refreshed")
                                # Also call the auth state changed method
                                if hasattr(self.pages["home"], 'on_auth_state_changed'):
                                    self.pages["home"].on_auth_state_changed()
                                    logger.info("✅ Home page auth state changed")
                            except Exception as home_error:
                                logger.error(f"❌ Error updating home page: {home_error}")
                        
                        # Clear the flag after successful completion
                        self._auth_refresh_in_progress = False
                        logger.info("🔓 Cleared auth refresh flag")
                        return True
                    else:
                        logger.warning("❌ No valid session found after login")
                        self.update_auth_state(False)
                        # Clear the flag after completion
                        self._auth_refresh_in_progress = False
                        return False
                except Exception as session_error:
                    logger.error(f"❌ Error getting session: {session_error}")
                    self.update_auth_state(False)
                    # Clear the flag after completion
                    self._auth_refresh_in_progress = False
                    return False
            else:
                logger.warning("⚠️ Supabase client not available after login")
                self.update_auth_state(False)
                # Clear the flag after completion
                self._auth_refresh_in_progress = False
                return False
            
        except Exception as e:
            logger.error(f"❌ Error in force_auth_refresh_after_login: {e}")
            self.update_auth_state(False)
            # Clear the flag after completion
            self._auth_refresh_in_progress = False
            return False
    
    def get_current_user_info(self):
        """Get current user information."""
        try:
            logger.info("🔄 get_current_user_info started...")
            
            # Try to get user from user manager first
            logger.info("🔍 Getting user from user manager...")
            from trackpro.auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                logger.info(f"✅ Found authenticated user in user manager: {current_user.email}")
                
                # Get complete user profile if available
                logger.info("🔍 Getting complete user profile...")
                try:
                    from trackpro.social.user_manager import EnhancedUserManager
                    user_manager = EnhancedUserManager()
                    complete_profile = user_manager.get_complete_user_profile(current_user.id)
                    
                    if complete_profile:
                        logger.info(f"✅ Got complete profile for user: {complete_profile.get('display_name', 'Unknown')}")
                        user_info = {
                            'id': current_user.id,
                            'email': current_user.email,
                            'name': complete_profile.get('display_name') or complete_profile.get('username') or current_user.name,
                            'avatar_url': complete_profile.get('avatar_url'),
                            'username': complete_profile.get('username'),
                            'display_name': complete_profile.get('display_name')
                        }
                        logger.info(f"✅ Returning complete user info: {user_info.get('name', 'Unknown')}")
                        return user_info
                    else:
                        logger.warning("⚠️ No complete profile found, using basic user info")
                except Exception as profile_error:
                    logger.error(f"❌ Error getting complete profile: {profile_error}")
                
                # Fallback to basic user info
                user_info = {
                    'id': current_user.id,
                    'email': current_user.email,
                    'name': current_user.name or current_user.email,
                    'avatar_url': None,
                    'username': None,
                    'display_name': current_user.name or current_user.email
                }
                logger.info(f"✅ Returning basic user info: {user_info.get('name', 'Unknown')}")
                return user_info
            else:
                logger.info("ℹ️ No authenticated user found in user manager")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error in get_current_user_info: {e}")
            return None
    
    def on_avatar_uploaded(self, avatar_url: str):
        """Handle avatar upload events and refresh navigation."""
        try:
            logger.info(f"Avatar uploaded: {avatar_url}")
            
            # Clear cached user info to force refresh
            self._cached_user_info = None
            
            # Refresh authentication state to update navigation with new avatar
            self.refresh_auth_state()
            
        except Exception as e:
            logger.error(f"Error handling avatar upload: {e}")
    
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
    
    def start_direct_private_message(self, user_data):
        """Start a direct private message with a user (called from other widgets)."""
        try:
            logger.info(f"🔄 Starting direct private message with user: {user_data.get('display_name', 'Unknown')}")
            
            # Switch to community page first
            self.switch_to_page("community")
            
            # Get the community page and start private conversation
            community_page = self.get_page("community")
            if community_page and hasattr(community_page, 'start_private_conversation_with_user'):
                community_page.start_private_conversation_with_user(user_data)
            else:
                logger.error("Community page not available for private messaging")
                
        except Exception as e:
            logger.error(f"Error starting direct private message: {e}")
    
    def get_page(self, page_name: str):
        """Get a page by name."""
        return self.pages.get(page_name)
    
    def on_sidebar_toggled(self, is_expanded):
        """Handle online users sidebar toggle."""
        logger.info(f"📱 Online users sidebar {'expanded' if is_expanded else 'collapsed'}")
    
    def force_refresh_sidebar(self):
        """Force refresh the online users sidebar."""
        try:
            logger.info("🔄 force_refresh_sidebar started...")
            
            if hasattr(self, 'online_users_sidebar'):
                logger.info("✅ Online users sidebar found")
                try:
                    self.online_users_sidebar.force_refresh()
                    logger.info("✅ Online users sidebar force refresh completed")
                except Exception as sidebar_error:
                    logger.error(f"❌ Error in online users sidebar force refresh: {sidebar_error}")
            else:
                logger.warning("⚠️ No online_users_sidebar found")
                
        except Exception as e:
            logger.error(f"❌ Error in force_refresh_sidebar: {e}")
    
    def _deferred_sidebar_refresh(self):
        """Deferred sidebar refresh to prevent immediate crashes."""
        try:
            logger.info("🔄 Executing deferred sidebar refresh...")
            self.force_refresh_sidebar()
            logger.info("✅ Deferred sidebar refresh completed")
        except Exception as e:
            logger.error(f"❌ Error in deferred sidebar refresh: {e}")
    
    def _update_pages_auth_state(self):
        """Deferred page auth state updates to prevent immediate crashes."""
        try:
            logger.info("🔄 Executing deferred page auth state updates...")
            for page_name, page in self.pages.items():
                if hasattr(page, 'on_auth_state_changed'):
                    try:
                        logger.info(f"🔄 Updating page: {page_name}")
                        page.on_auth_state_changed()
                        logger.info(f"✅ Updated page: {page_name}")
                    except Exception as page_error:
                        logger.error(f"❌ Error updating page {page_name}: {page_error}")
                        import traceback
                        logger.error(f"📋 Traceback for {page_name}: {traceback.format_exc()}")
                        # Continue with other pages even if one fails
                        continue
            logger.info("✅ Deferred page updates completed")
        except Exception as e:
            logger.error(f"❌ Error in deferred page updates: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def debug_sidebar_issues(self):
        """Debug method to help diagnose sidebar issues."""
        logger.info("🔍 Debugging sidebar issues...")
        
        if hasattr(self, 'online_users_sidebar'):
            sidebar = self.online_users_sidebar
            
            # Check if sidebar is visible
            logger.info(f"Sidebar visible: {sidebar.isVisible()}")
            logger.info(f"Sidebar width: {sidebar.width()}")
            logger.info(f"Sidebar expanded: {getattr(sidebar, 'is_expanded', 'Unknown')}")
            
            # Check user data
            logger.info(f"Number of users in sidebar: {len(getattr(sidebar, 'all_users', []))}")
            for i, user in enumerate(getattr(sidebar, 'all_users', [])):
                logger.info(f"User {i+1}: {user.get('display_name', 'Unknown')} - Avatar URL: {user.get('avatar_url', 'None')}")
            
            # Force refresh
            sidebar.force_refresh()
            logger.info("✅ Sidebar debug completed")
        else:
            logger.error("❌ Online users sidebar not found")
    
    def show_update_notification(self, version):
        """Show update notification in the UI."""
        # This method is called by the updater when an update is available
        # but the user chose not to download immediately
        logger.info(f"Update notification shown for version v{version}")
        
        # Show the update notification dialog
        try:
            from trackpro.ui.update_notification_dialog import UpdateNotificationDialog
            dialog = UpdateNotificationDialog(version, self)
            dialog.download_clicked.connect(lambda: self.updater._handle_download_choice())
            dialog.cancel_clicked.connect(lambda: self.updater._handle_cancel_choice())
            dialog.show()
        except Exception as e:
            logger.error(f"Error showing update notification: {e}")
    
    def init_updater(self):
        """Initialize the updater and check for updates on startup."""
        try:
            from trackpro.updater import Updater
            self.updater = Updater(self)
            # Check for updates silently on startup
            self.updater.check_for_updates(silent=True, manual_check=False)
            logger.info("✅ Updater initialized and checking for updates")
        except Exception as e:
            logger.error(f"Error initializing updater: {e}")
    
    def check_for_updates(self):
        """Check for updates manually."""
        # This method is called from the menu bar
        if not hasattr(self, 'updater'):
            self.init_updater()
        self.updater.check_for_updates(silent=False, manual_check=True)
    
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
    
    def setup_system_tray(self):
        """Set up system tray functionality."""
        try:
            import os
            
            # Check if system tray is available
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.warning("System tray is not available on this system, but will try to create tray icon anyway")
                # Don't return - try to create the tray icon anyway
            
            # Create system tray icon
            try:
                self.tray_icon = QSystemTrayIcon(self)
                logger.info("✅ System tray icon created successfully")
            except Exception as e:
                logger.error(f"Failed to create system tray icon: {e}")
                return
            
            # Set icon - try to use our custom TrackPro tray icon
            try:
                # Debug: Check current directory and file paths
                current_dir = os.path.dirname(__file__)
                logger.info(f"🔍 Current directory: {current_dir}")
                
                # Try multiple paths to find the tray icon (PNG first)
                possible_paths = [
                    # PNG first (preferred - same as window icon)
                    os.path.join(current_dir, "..", "..", "resources", "icons", "trackpro_tray.png"),
                    # ICO as fallback
                    os.path.join(current_dir, "..", "..", "resources", "icons", "trackpro_tray.ico"),
                    # Absolute paths from project root (PNG first)
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), "trackpro", "resources", "icons", "trackpro_tray.png"),
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), "trackpro", "resources", "icons", "trackpro_tray.ico"),
                    # Try resource utils
                    None  # Will be handled separately
                ]
                
                icon = None
                icon_path = None
                
                # Try each path
                for path in possible_paths:
                    if path and os.path.exists(path):
                        icon = QIcon(path)
                        icon_path = path
                        logger.info(f"✅ Loaded custom tray icon from: {icon_path}")
                        break
                
                # If no icon found via paths, try resource utils
                if not icon:
                    try:
                        from trackpro.utils.resource_utils import get_resource_path
                        resource_path = get_resource_path("trackpro/resources/icons/trackpro_tray.png")
                        logger.info(f"🔍 Looking via resource utils at: {resource_path}")
                        if os.path.exists(resource_path):
                            icon = QIcon(resource_path)
                            icon_path = resource_path
                            logger.info(f"✅ Loaded custom tray icon via resource utils: {icon_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ Resource utils failed: {e}")
                
                # If still no icon, use fallbacks
                if not icon:
                    # Fallback to window icon
                    icon = self.windowIcon()
                    if icon.isNull():
                        # Final fallback to system icon
                        icon = self.style().standardIcon(self.style().SP_ComputerIcon)
                        logger.warning("⚠️ Using system fallback icon for tray")
                    else:
                        logger.info("Using window icon for tray")
                
                self.tray_icon.setIcon(icon)
                
            except Exception as e:
                logger.warning(f"Could not set tray icon: {e}")
                # Use a standard system icon as fallback
                icon = self.style().standardIcon(self.style().SP_ComputerIcon)
                self.tray_icon.setIcon(icon)
            
            # Create tray menu
            tray_menu = QMenu()
            
            # Show/Hide action
            show_action = QAction("Show TrackPro", self)
            show_action.triggered.connect(self.show_from_tray)
            tray_menu.addAction(show_action)
            
            tray_menu.addSeparator()
            
            # Exit action
            exit_action = QAction("Exit TrackPro", self)
            exit_action.triggered.connect(self.force_exit_from_tray)
            tray_menu.addAction(exit_action)
            
            # Set the menu
            self.tray_icon.setContextMenu(tray_menu)
            
            # Connect double-click to show window
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Set tooltip
            self.tray_icon.setToolTip("TrackPro - Racing Telemetry System")
            
            # Show the tray icon
            self.tray_icon.show()
            
            # Verify tray icon is visible
            if self.tray_icon.isVisible():
                logger.info("✅ System tray initialized successfully and icon is visible")
            else:
                logger.warning("⚠️ System tray initialized but icon is not visible")
            
            logger.info("System tray initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up system tray: {e}")
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()
    
    def show_from_tray(self):
        """Show the main window from system tray."""
        self.show()
        self.raise_()
        self.activateWindow()
        logger.info("Window restored from system tray")
    
    def force_exit_from_tray(self):
        """Force exit the application completely from system tray."""
        logger.info("FORCE EXIT requested from system tray")
        
        # Clean up tray icon properly first
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
                logger.info("✅ System tray icon cleaned up during force exit")
            except Exception as e:
                logger.error(f"Error cleaning up tray icon during force exit: {e}")
        
        # Temporarily disable minimize to tray to force actual exit
        from trackpro.config import Config
        config = Config()
        original_setting = config.minimize_to_tray
        config.set('ui.minimize_to_tray', False)
        
        # Force kill all TrackPro processes immediately
        try:
            logger.info("🔫 System tray force killing all TrackPro processes...")
            
            # Use subprocess utility to hide windows
            from trackpro.utils.subprocess_utils import run_subprocess
            
            kill_commands = [
                ['taskkill', '/F', '/IM', 'TrackPro*.exe'],
                ['taskkill', '/F', '/T', '/IM', 'TrackPro_v1.5.6.exe'],
                # More specific PowerShell command that excludes IDEs
                ['powershell', '-Command', '''Get-Process | Where-Object {
                    ($_.ProcessName -eq "TrackPro" -or 
                     $_.ProcessName -like "TrackPro_v*" -or 
                     $_.ProcessName -like "TrackPro_Setup*") -and
                    $_.ProcessName -notlike "*Cursor*" -and
                    $_.ProcessName -notlike "*Code*" -and
                    $_.ProcessName -notlike "*Visual*" -and
                    $_.ProcessName -notlike "*Studio*"
                } | Stop-Process -Force'''],
            ]
            
            for cmd in kill_commands:
                try:
                    run_subprocess(cmd, hide_window=True, capture_output=True, text=True, check=False, timeout=3)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error during system tray force kill: {e}")
        
        # Clean up lock file
        try:
            import tempfile
            import os
            lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
            if os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass
        
        # Force quit application
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()
        except:
            import sys
            sys.exit(0)
    
    def cleanup(self):
        """Clean up resources before window closes."""
        if self._is_shutting_down:
            return
            
        logger.info("🧹 Starting main window cleanup...")
        self._is_shutting_down = True
        
        try:
            # Clean up system tray icon first
            if hasattr(self, 'tray_icon') and self.tray_icon:
                try:
                    self.tray_icon.hide()
                    self.tray_icon.deleteLater()
                    logger.info("✅ System tray icon cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up tray icon: {e}")
            
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
    
    def __del__(self):
        """Destructor to ensure tray icon is cleaned up."""
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
        except:
            pass
    
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
            # ALWAYS minimize to tray instead of closing the application
            # This ensures TrackPro stays running in the background
            logger.info("🔄 Always minimizing to system tray - TrackPro stays running")
            
            # Hide the window
            self.hide()
            
            # Ensure tray icon is visible if it exists
            if hasattr(self, 'tray_icon') and self.tray_icon:
                if not self.tray_icon.isVisible():
                    self.tray_icon.show()
                logger.info("✅ Window minimized to system tray")
            else:
                logger.warning("⚠️ No system tray icon available")
            
            event.ignore()  # Don't close the window
            return
            
        except Exception as e:
            logger.error(f"Error during closeEvent: {e}")
            # Even if there's an error, don't close the app
            event.ignore()
            return