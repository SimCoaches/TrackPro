import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from ..discord_navigation import DiscordNavigation
from ..online_users_sidebar import OnlineUsersSidebar
from .shared.base_page import GlobalManagers
from .performance_manager import PerformanceManager, ThreadPriorityManager, CPUCoreManager
from ..pages.pedals import PedalsPage
from ..pages.race_coach import CoachPage
from ..pages.race_pass import RacePassPage
from ..pages.overlays import OverlaysPage
from ..pages.home import HomePage

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
        
        self.init_performance_optimization()
        self.init_global_managers()
        self.init_modern_ui()
        
        logger.info("🚀 Modern TrackPro UI initialized with modular architecture")
    
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
            from ...pedals.hardware_input import HardwareInput
            self.global_managers.hardware = HardwareInput()
            logger.info("✅ Hardware input manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize hardware manager: {e}")
        
        try:
            from ...race_coach.simple_iracing import SimpleIRacingAPI
            self.global_managers.iracing = SimpleIRacingAPI()
            logger.info("✅ iRacing monitor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize iRacing monitor: {e}")
        
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
    
    def create_navigation(self):
        nav_widget = DiscordNavigation()
        nav_widget.page_requested.connect(self.switch_to_page)
        return nav_widget
    
    def create_online_users_sidebar(self):
        """Create the online users sidebar."""
        sidebar = OnlineUsersSidebar()
        sidebar.user_selected.connect(self.on_user_selected)
        sidebar.sidebar_toggled.connect(self.on_sidebar_toggled)
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
            "pedals": {"class": PedalsPage, "created": False},
            "race_coach": {"class": CoachPage, "created": False},
            "overlays": {"class": OverlaysPage, "created": False},
            "race_pass": {"class": RacePassPage, "created": False},
            "handbrake": {"class": None, "created": False},  # Special handling needed
            "support": {"class": None, "created": False},  # Special handling needed
            "community": {"class": None, "created": False, "placeholder": True},
            "account": {"class": None, "created": False, "placeholder": True}
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
                from ...database.supabase_client import supabase
                is_authenticated = supabase.is_authenticated()
                
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
            elif page_name == "handbrake":
                # Special handling for handbrake page
                from ..pages.handbrake import HandbrakePage
                page_widget = HandbrakePage(self.global_managers)
            elif page_name == "support":
                # Special handling for support page
                from ..pages.support import SupportPage
                page_widget = SupportPage(self.global_managers)
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
        """Create the account page with authentication features."""
        from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGroupBox, QFrame
        from PyQt6.QtCore import Qt
        
        account_page = QWidget()
        layout = QVBoxLayout(account_page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("👤 Account")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #fefefe; margin-bottom: 20px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Account status container
        self.account_status_container = QWidget()
        status_layout = QVBoxLayout(self.account_status_container)
        
        # Authentication status group
        auth_group = QGroupBox("Authentication Status")
        auth_group.setStyleSheet("""
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
        auth_layout = QVBoxLayout(auth_group)
        auth_layout.setSpacing(15)
        
        # Status label
        self.auth_status_label = QLabel("Checking authentication status...")
        self.auth_status_label.setStyleSheet("font-size: 14px; color: #c0c0c0; padding: 10px;")
        self.auth_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auth_layout.addWidget(self.auth_status_label)
        
        # User info container (hidden by default)
        self.user_info_container = QWidget()
        self.user_info_container.setVisible(False)
        user_info_layout = QVBoxLayout(self.user_info_container)
        
        self.user_email_label = QLabel("")
        self.user_email_label.setStyleSheet("font-size: 14px; color: #fefefe; padding: 5px;")
        user_info_layout.addWidget(self.user_email_label)
        
        self.user_name_label = QLabel("")
        self.user_name_label.setStyleSheet("font-size: 14px; color: #c0c0c0; padding: 5px;")
        user_info_layout.addWidget(self.user_name_label)
        
        auth_layout.addWidget(self.user_info_container)
        
        # Buttons container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(10)
        
        # Login button (shown when not authenticated)
        self.login_button = QPushButton("🔑 Login")
        self.login_button.setMinimumHeight(40)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 8px;
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
        
        # Signup button (shown when not authenticated)
        self.signup_button = QPushButton("📝 Sign Up")
        self.signup_button.setMinimumHeight(40)
        self.signup_button.setStyleSheet("""
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
        self.signup_button.clicked.connect(self.show_signup_dialog)
        buttons_layout.addWidget(self.signup_button)
        
        # Logout button (shown when authenticated)
        self.logout_button = QPushButton("🚪 Logout")
        self.logout_button.setMinimumHeight(40)
        self.logout_button.setVisible(False)
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.logout_button.clicked.connect(self.logout_user)
        buttons_layout.addWidget(self.logout_button)
        
        auth_layout.addWidget(buttons_container)
        status_layout.addWidget(auth_group)
        
        # User Profile Form (shown when authenticated)
        self.profile_group = self.create_user_profile_form()
        self.profile_group.setVisible(False)  # Hidden by default
        status_layout.addWidget(self.profile_group)
        
        layout.addWidget(self.account_status_container)
        
        layout.addStretch()
        
        # Store reference to account page for updates
        account_page.update_auth_status = lambda authenticated: self.update_account_page_auth_status(authenticated)
        
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
            if authenticated:
                # Show user as logged in
                self.auth_status_label.setText("✅ You are logged in")
                self.auth_status_label.setStyleSheet("font-size: 14px; color: #28a745; padding: 10px; font-weight: bold;")
                
                # Try to get user info
                try:
                    from ...database.supabase_client import supabase
                    user = supabase.get_user()
                    if user and hasattr(user, 'user') and user.user:
                        email = user.user.email or "No email available"
                        # Get user metadata for name
                        metadata = getattr(user.user, 'user_metadata', {})
                        name = metadata.get('full_name') or metadata.get('name') or "No name available"
                        
                        self.user_email_label.setText(f"📧 {email}")
                        self.user_name_label.setText(f"👤 {name}")
                        self.user_info_container.setVisible(True)
                    else:
                        self.user_info_container.setVisible(False)
                except Exception as e:
                    logger.error(f"Error getting user info: {e}")
                    self.user_info_container.setVisible(False)
                
                # Show logout button, hide login/signup
                self.login_button.setVisible(False)
                self.signup_button.setVisible(False)
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
                self.user_info_container.setVisible(False)
                
                # Show login/signup buttons, hide logout
                self.login_button.setVisible(True)
                self.signup_button.setVisible(True)
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
            from ...database.supabase_client import supabase
            
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
            from ...database.supabase_client import supabase
            
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
            from ...auth.login_dialog import LoginDialog
            
            login_dialog = LoginDialog(self, oauth_handler=self.oauth_handler)
            result = login_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user logged in)
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
            from ...auth.signup_dialog import SignupDialog
            
            signup_dialog = SignupDialog(self, oauth_handler=self.oauth_handler)
            result = signup_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user signed up)
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
                # Perform logout
                from ...database.supabase_client import supabase
                supabase.sign_out()
                
                # Update UI immediately
                self.update_auth_state(False)
                logger.info("🔐 User successfully logged out - updating navigation")
                
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
            logger.info(f"🔐 Updating UI auth state: {authenticated}")
            
            # Get user information if authenticated
            user_info = None
            if authenticated:
                user_info = self.get_current_user_info()
            
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
            
            # Emit signal for other components
            self.auth_state_changed.emit(authenticated)
            
        except Exception as e:
            logger.error(f"Error updating auth state: {e}")
    
    def get_current_user_info(self):
        """Get current user information from the authentication system and profile database."""
        try:
            from ...database.supabase_client import supabase
            # Use the SupabaseManager's get_user method
            user_response = supabase.get_user()
            
            logger.info(f"🔍 DEBUG: user_response = {user_response}")
            
            if user_response and hasattr(user_response, 'user') and user_response.user:
                user = user_response.user
                logger.info(f"🔍 DEBUG: user object = {user}")
                
                email = user.email or "No email available"
                user_id = user.id
                logger.info(f"🔍 DEBUG: email = {email}, user_id = {user_id}")
                
                name = "User"  # Default fallback
                
                # First, try to get name from user metadata (fastest and already available)
                metadata = getattr(user, 'user_metadata', {})
                logger.info(f"🔍 DEBUG: user_metadata = {metadata}")
                
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
                
                logger.info(f"✅ Got user name from metadata: {name}")
                
                # If no name from metadata, fallback to user_details table
                if name == "User":
                    try:
                        logger.info("📝 No name in metadata, checking database...")
                        profile_result = supabase.client.table('user_details').select('first_name, last_name').eq('user_id', user_id).execute()
                        
                        if profile_result.data and len(profile_result.data) > 0:
                            profile = profile_result.data[0]
                            logger.info(f"🔍 DEBUG: profile data = {profile}")
                            
                            # Combine first and last name from user_details table
                            if profile.get('first_name') and profile.get('last_name'):
                                name = f"{profile['first_name']} {profile['last_name']}"
                            elif profile.get('first_name'):
                                name = profile['first_name']
                            
                            logger.info(f"✅ Got user name from database: {name}")
                        
                    except Exception as profile_error:
                        logger.error(f"Error fetching user profile: {profile_error}")
                        # Continue with final fallback below
                
                # Final fallback: use email username if still no name
                if name == "User" and email and email != "No email available":
                    name = email.split('@')[0]
                    logger.info(f"🔍 DEBUG: Using email fallback name: {name}")
                
                user_info = {
                    'email': email,
                    'name': name or "User",
                    'user_id': user_id
                }
                
                logger.info(f"🔍 DEBUG: Final user_info = {user_info}")
                return user_info
            else:
                logger.warning(f"🔍 DEBUG: No valid user in response: {user_response}")
            
        except Exception as e:
            logger.error(f"Error getting current user info: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return None
    

    def check_authentication_on_account_click(self):
        """Check authentication when account page is requested."""
        try:
            from ...database.supabase_client import supabase
            is_authenticated = supabase.is_authenticated()
            
            if not is_authenticated:
                # Show login dialog immediately
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
    
    def on_sidebar_toggled(self, is_expanded):
        """Handle online users sidebar toggle."""
        logger.info(f"📱 Online users sidebar {'expanded' if is_expanded else 'collapsed'}")
        # Could save preference or adjust layout here if needed
    
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