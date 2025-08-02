"""Modern main window using the new UI framework.

This module contains the modernized main window that integrates TrackPro's
existing functionality with the new sliding menu UI framework.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

# Import the new UI framework
from .custom_widgets import QCustomQStackedWidget
from .discord_navigation import DiscordNavigation


# Import existing TrackPro components
from .main_window import MainWindow as OriginalMainWindow

logger = logging.getLogger(__name__)


class ModernMainWindow(QMainWindow):
    """Modern main window with sliding menu UI."""
    
    # Keep the same signals as the original
    calibration_updated = pyqtSignal(str)
    auth_state_changed = pyqtSignal(bool)
    window_state_changed = pyqtSignal(object)
    
    def __init__(self, parent=None, oauth_handler=None):
        """Initialize the modern main window."""
        super().__init__(parent)
        
        # Store oauth handler for later use
        self.oauth_handler = oauth_handler
        
        # Initialize the original window functionality (but don't show it)
        try:
            self.original_window = OriginalMainWindow(oauth_handler=oauth_handler)
            # Hide the original window immediately
            self.original_window.hide()
        except Exception as e:
            logger.error(f"Error creating original window: {e}")
            self.original_window = None
        
        # Set up paths
        self.ui_resources_path = Path(__file__).parent.parent.parent / "ui_resources"
        
        # Initialize modern UI components
        self.theme_engine = None
        self.icon_manager = None
        self.theme_manager = None
        self.left_menu = None
        self.content_stack = None
        
        # Page references
        self.pages = {}
        
        # Initialize the UI
        self.init_modern_ui()
        self.setup_connections()
        
    def init_modern_ui(self):
        """Initialize the modern UI framework."""
        try:
            # Initialize theme and icon systems (TODO: Implement these components)
            # self.theme_engine = ThemeEngine(str(self.ui_resources_path))
            # self.icon_manager = IconManager(str(self.ui_resources_path))
            # self.theme_manager = ThemeManager(
            #     theme_engine=self.theme_engine,
            #     icon_manager=self.icon_manager
            # )
            
            # Apply initial theme
            # self.theme_manager.apply_theme()
            
            # Set window properties
            self.setWindowTitle("TrackPro V1.5.5")
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)
            
            # Create the main layout structure
            self.create_main_layout()
            
            # Create pages with TrackPro content
            self.create_pages()
            
            # Set initial page
            self.content_stack.setCurrentIndex(0)  # Home page
            
            logger.info("Modern UI initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing modern UI: {e}")
            # Fallback to a basic layout if modern UI fails
            self.create_fallback_ui()
    
    def create_main_layout(self):
        """Create the main layout with sliding menus."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create Discord-style navigation
        self.left_menu = DiscordNavigation()
        self.left_menu.page_requested.connect(self.switch_to_page)
        
        # Create content area with smooth transitions
        self.content_stack = QCustomQStackedWidget(
            transition_type="slide_horizontal",
            animation_duration=250
        )
        
        # Add components to main layout
        main_layout.addWidget(self.left_menu)
        main_layout.addWidget(self.content_stack, 1)  # Content takes remaining space
    
    def create_pages(self):
        """Create all the TrackPro pages."""
        # Home Dashboard
        self.pages["home"] = self.create_home_page()
        self.content_stack.addWidget(self.pages["home"])
        
        # Pedals Page - Extract from original window
        self.pages["pedals"] = self.create_pedals_page()
        self.content_stack.addWidget(self.pages["pedals"])
        
        # Handbrake Page
        self.pages["handbrake"] = self.create_handbrake_page()
        self.content_stack.addWidget(self.pages["handbrake"])
        
        # Race Coach Page - Extract race coach functionality
        self.pages["race_coach"] = self.create_race_coach_page()
        self.content_stack.addWidget(self.pages["race_coach"])
        
        # Race Pass Page
        self.pages["race_pass"] = self.create_race_pass_page()
        self.content_stack.addWidget(self.pages["race_pass"])
        
        # Community Page
        self.pages["community"] = self.create_community_page()
        self.content_stack.addWidget(self.pages["community"])
        
        # Account Page
        self.pages["account"] = self.create_account_page()
        self.content_stack.addWidget(self.pages["account"])
    
    def create_home_page(self):
        """Create the home dashboard page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Header
        header = QLabel("TrackPro Dashboard")
        header.setObjectName("page-header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Quick access tiles
        tiles_widget = QWidget()
        tiles_layout = QHBoxLayout(tiles_widget)
        
        # Create quick access tiles for main features
        tile_configs = [
            {"title": "Pedal Setup", "desc": "Configure pedal calibration", "page": "pedals"},
            {"title": "Race Coach", "desc": "AI coaching & telemetry", "page": "race_coach"},
            {"title": "Community", "desc": "Connect with racers", "page": "community"}
        ]
        
        for config in tile_configs:
            tile = self.create_dashboard_tile(config["title"], config["desc"], config["page"])
            tiles_layout.addWidget(tile)
        
        layout.addWidget(tiles_widget)
        layout.addStretch()
        
        return page
    
    def create_dashboard_tile(self, title: str, description: str, target_page: str):
        """Create a dashboard tile for quick navigation."""
        tile = QPushButton()
        tile.setObjectName("dashboard-tile")
        tile.setMinimumSize(200, 150)
        tile.setText(f"{title}\n\n{description}")
        tile.clicked.connect(lambda: self.switch_to_page(target_page))
        return tile
    
    def create_pedals_page(self):
        """Create the pedals configuration page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Header
        header = QLabel("🦶 Pedal Configuration")
        header.setObjectName("page-header")
        layout.addWidget(header)
        
        # Extract pedal widgets from original window if available
        if hasattr(self.original_window, 'pedal_frame'):
            try:
                # Clone or reference the existing pedal configuration
                pedal_content = QLabel("Pedal calibration interface will be migrated here...")
                layout.addWidget(pedal_content)
            except Exception as e:
                logger.warning(f"Could not extract pedal interface: {e}")
                fallback = QLabel("Pedal configuration coming soon...")
                layout.addWidget(fallback)
        else:
            placeholder = QLabel("Advanced pedal calibration and curve configuration")
            layout.addWidget(placeholder)
        
        layout.addStretch()
        return page
    
    def create_handbrake_page(self):
        """Create the handbrake configuration page.""" 
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        header = QLabel("🤚 Handbrake Setup")
        header.setObjectName("page-header")
        layout.addWidget(header)
        
        content = QLabel("Handbrake calibration and configuration tools")
        layout.addWidget(content)
        layout.addStretch()
        
        return page
    
    def create_race_coach_page(self):
        """Create the Race Coach page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        header = QLabel("🏁 Race Coach")
        header.setObjectName("page-header")
        layout.addWidget(header)
        
        # Extract race coach functionality if available
        if hasattr(self.original_window, 'race_coach'):
            try:
                coach_content = QLabel("AI coaching and telemetry analysis interface")
                layout.addWidget(coach_content)
            except Exception as e:
                logger.warning(f"Could not extract race coach interface: {e}")
        
        layout.addStretch()
        return page
    
    def create_race_pass_page(self):
        """Create the Race Pass subscription page with full functionality."""
        try:
            # Import and create the actual Race Pass page
            from trackpro.ui.pages.race_pass import RacePassPage
            page = RacePassPage()
            return page
        except Exception as e:
            logger.error(f"Failed to create Race Pass page: {e}")
            # Fallback to placeholder
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(40, 40, 40, 40)
            
            header = QLabel("🎟️ Race Pass")
            header.setObjectName("page-header")
            layout.addWidget(header)
            
            error_label = QLabel("Race Pass temporarily unavailable. Check logs for details.")
            error_label.setStyleSheet("color: #e74c3c; font-size: 14px;")
            layout.addWidget(error_label)
            layout.addStretch()
            
            return page
    
    def create_community_page(self):
        """Create the Community page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        header = QLabel("👥 Community")
        header.setObjectName("page-header")
        layout.addWidget(header)
        
        content = QLabel("Social features, Discord integration, and achievements")
        layout.addWidget(content)
        layout.addStretch()
        
        return page
    
    def create_account_page(self):
        """Create the Account management page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        header = QLabel("👤 Account")
        header.setObjectName("page-header")
        layout.addWidget(header)
        
        content = QLabel("User profile and account settings")
        layout.addWidget(content)
        layout.addStretch()
        
        return page
    
    def create_fallback_ui(self):
        """Create a basic fallback UI if modern UI fails."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        label = QLabel("TrackPro - Modern UI failed to load")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        logger.warning("Using fallback UI due to modern UI initialization failure")
    
    def switch_to_page(self, page_name: str):
        """Switch to the specified page."""
        try:
            if page_name in self.pages:
                page_index = list(self.pages.keys()).index(page_name)
                self.content_stack.setCurrentIndex(page_index)
                # Update navigation button state
                if hasattr(self.left_menu, 'set_active_page'):
                    self.left_menu.set_active_page(page_name)
                logger.debug(f"Switched to {page_name} page")
            else:
                logger.warning(f"Page '{page_name}' not found")
        except Exception as e:
            logger.error(f"Error switching to page {page_name}: {e}")
    
    def setup_connections(self):
        """Set up signal connections."""
        try:
            # Connect original window signals to this window
            if self.original_window:
                self.original_window.calibration_updated.connect(self.calibration_updated.emit)
                self.original_window.auth_state_changed.connect(self.auth_state_changed.emit)
                self.original_window.window_state_changed.connect(self.window_state_changed.emit)
        except Exception as e:
            logger.error(f"Error setting up connections: {e}")
    
    def get_original_window(self):
        """Get reference to the original window for compatibility."""
        return self.original_window
    
    # ===== COMPATIBILITY METHODS =====
    # These methods delegate to the original window to maintain compatibility
    
    def set_input_value(self, pedal: str, value: int):
        """Set the input value for a pedal - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'set_input_value'):
                self.original_window.set_input_value(pedal, value)
        except Exception as e:
            logger.error(f"Error setting input value for {pedal}: {e}")
    
    def set_calibration_points(self, pedal: str, points):
        """Set calibration points - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'set_calibration_points'):
                self.original_window.set_calibration_points(pedal, points)
        except Exception as e:
            logger.error(f"Error setting calibration points for {pedal}: {e}")
    
    def set_curve_type(self, pedal: str, curve_type: str):
        """Set curve type - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'set_curve_type'):
                self.original_window.set_curve_type(pedal, curve_type)
        except Exception as e:
            logger.error(f"Error setting curve type for {pedal}: {e}")
    
    def set_calibration_range(self, pedal: str, min_val: int, max_val: int):
        """Set calibration range - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'set_calibration_range'):
                self.original_window.set_calibration_range(pedal, min_val, max_val)
        except Exception as e:
            logger.error(f"Error setting calibration range for {pedal}: {e}")
    
    def set_pedal_available(self, pedal: str, available: bool):
        """Set pedal availability - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'set_pedal_available'):
                self.original_window.set_pedal_available(pedal, available)
        except Exception as e:
            logger.error(f"Error setting pedal availability for {pedal}: {e}")
    
    def get_calibration_points(self, pedal: str):
        """Get calibration points - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'get_calibration_points'):
                return self.original_window.get_calibration_points(pedal)
        except Exception as e:
            logger.error(f"Error getting calibration points for {pedal}: {e}")
        return []
    
    def get_curve_type(self, pedal: str):
        """Get curve type - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'get_curve_type'):
                return self.original_window.get_curve_type(pedal)
        except Exception as e:
            logger.error(f"Error getting curve type for {pedal}: {e}")
        return "Linear (Default)"
    
    def get_calibration_range(self, pedal: str):
        """Get calibration range - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'get_calibration_range'):
                return self.original_window.get_calibration_range(pedal)
        except Exception as e:
            logger.error(f"Error getting calibration range for {pedal}: {e}")
        return (0, 65535)
    
    def set_hardware(self, hardware):
        """Set hardware reference - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'set_hardware'):
                self.original_window.set_hardware(hardware)
        except Exception as e:
            logger.error(f"Error setting hardware: {e}")
    
    def refresh_curve_lists(self):
        """Refresh curve lists - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, 'refresh_curve_lists'):
                self.original_window.refresh_curve_lists()
        except Exception as e:
            logger.error(f"Error refreshing curve lists: {e}")
    
    @property
    def statusBar(self):
        """Get status bar - delegate to original window."""
        if self.original_window and hasattr(self.original_window, 'statusBar'):
            return self.original_window.statusBar
        return super().statusBar()
    
    @property 
    def stacked_widget(self):
        """Get stacked widget - delegate to original window."""
        if self.original_window and hasattr(self.original_window, 'stacked_widget'):
            return self.original_window.stacked_widget
        return self.content_stack
    
    @property
    def _pedal_data(self):
        """Get pedal data - delegate to original window."""
        if self.original_window and hasattr(self.original_window, '_pedal_data'):
            return self.original_window._pedal_data
        return {}
    
    def __getattr__(self, name):
        """Fallback for any missing attributes - delegate to original window."""
        try:
            if self.original_window and hasattr(self.original_window, name):
                return getattr(self.original_window, name)
        except Exception as e:
            logger.debug(f"Could not delegate attribute {name} to original window: {e}")
        
        # If we can't find it, raise the normal AttributeError
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Ensure proper cleanup of original window
            if self.original_window:
                self.original_window.close()
        except Exception as e:
            logger.error(f"Error during close: {e}")
        finally:
            event.accept()