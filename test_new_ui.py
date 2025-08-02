"""Test script for the new UI framework.

This script creates a simple test window using the new UI components
to verify that all the foundation pieces are working correctly.
"""

import sys
import os
from pathlib import Path

# Add trackpro to the path
current_dir = Path(__file__).parent
trackpro_path = current_dir / "trackpro"
sys.path.insert(0, str(trackpro_path))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

# Import our new UI components
from trackpro.ui.custom_widgets import QCustomSlideMenu, QCustomQStackedWidget, ThemeManager
from trackpro.ui.icon_manager import initialize_icon_manager, get_icon
from trackpro.ui.theme_engine import create_theme_engine


class TestMainWindow(QMainWindow):
    """Test window for the new UI framework."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("TrackPro - New UI Test")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize the theme system
        ui_resources_path = current_dir / "ui_resources"
        self.icon_manager = initialize_icon_manager(str(ui_resources_path))
        self.theme_engine = create_theme_engine(str(ui_resources_path))
        self.theme_engine.set_icon_manager(self.icon_manager)
        
        # Load theme variables and stylesheet
        self.load_theme()
        
        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create main layout
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        
        # Create left menu
        self.left_menu = QCustomSlideMenu()
        self.setup_left_menu()
        
        # Create main content area
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        
        # Header
        header = self.create_header()
        main_content_layout.addWidget(header)
        
        # Content stack
        self.content_stack = QCustomQStackedWidget()
        self.setup_content_stack()
        main_content_layout.addWidget(self.content_stack)
        
        # Add to main layout
        layout.addWidget(self.left_menu)
        layout.addWidget(main_content)
        
        # Configure widgets from JSON
        self.configure_widgets()
        
    def load_theme(self):
        """Load the theme and apply stylesheet."""
        try:
            # Load variables
            if not self.theme_engine.load_variables():
                print("Warning: Could not load theme variables")
                
            # Try to get precompiled CSS first
            stylesheet = self.theme_engine.get_precompiled_css()
            
            if not stylesheet:
                print("Warning: Could not load precompiled CSS, trying SCSS processing")
                stylesheet = self.theme_engine.process_scss_to_qss("defaultStyle.scss")
                
            if stylesheet:
                self.setStyleSheet(stylesheet)
                print("✅ Theme loaded successfully")
            else:
                print("❌ Could not load theme")
                
        except Exception as e:
            print(f"Error loading theme: {e}")
            
    def setup_left_menu(self):
        """Setup the left sliding menu."""
        layout = QVBoxLayout(self.left_menu)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Menu toggle button
        self.menu_btn = QPushButton()
        menu_icon = get_icon("material_design/menu.png")
        if menu_icon:
            self.menu_btn.setIcon(menu_icon)
        else:
            self.menu_btn.setText("☰")
        self.menu_btn.setToolTip("Toggle Menu")
        self.menu_btn.clicked.connect(self.left_menu.toggle_menu)
        layout.addWidget(self.menu_btn)
        
        # Navigation buttons
        nav_buttons = [
            ("🏠", "Home", "homePage"),
            ("🦶", "Pedals", "pedalsPage"),
            ("🤚", "Handbrake", "handbrakePage"),
            ("🏁", "Race Coach", "raceCoachPage"),
            ("🎟️", "Race Pass", "racePassPage"),
            ("👥", "Community", "communityPage"),
            ("❓", "Support", "supportPage"),
            ("👤", "Account", "accountPage")
        ]
        
        self.nav_buttons = {}
        for icon, text, page_name in nav_buttons:
            btn = QPushButton(f"{icon} {text}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=page_name: self.switch_page(p))
            layout.addWidget(btn)
            self.nav_buttons[page_name] = btn
            
        layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
        layout.addWidget(settings_btn)
        
    def create_header(self):
        """Create the header widget."""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #F2F2F2; border-bottom: 1px solid #D8D8D8;")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Title
        title = QLabel("TrackPro - Modern UI")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Test buttons
        test_btn = QPushButton("Test Animation")
        test_btn.clicked.connect(self.test_animations)
        layout.addWidget(test_btn)
        
        return header
        
    def setup_content_stack(self):
        """Setup the content stack widget."""
        # Create test pages
        pages = [
            ("homePage", "🏠 Home", "Welcome to TrackPro!\n\nThis is the new modern interface."),
            ("pedalsPage", "🦶 Pedals", "Pedal calibration and configuration will be here."),
            ("handbrakePage", "🤚 Handbrake", "Handbrake calibration and setup will be here."),
            ("raceCoachPage", "🏁 Race Coach", "Telemetry analysis and AI coaching will be here."),
            ("racePassPage", "🎟️ Race Pass", "Subscription and premium features will be here."),
            ("communityPage", "👥 Community", "Social features and Discord integration will be here."),
            ("accountPage", "👤 Account", "User profile and account management will be here.")
        ]
        
        for page_name, title, description in pages:
            page = QWidget()
            page.setObjectName(page_name)
            
            layout = QVBoxLayout(page)
            layout.setContentsMargins(40, 40, 40, 40)
            
            # Page title
            title_label = QLabel(title)
            title_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)
            
            # Page description
            desc_label = QLabel(description)
            desc_label.setFont(QFont("Arial", 12))
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
            
            layout.addStretch()
            
            self.content_stack.addWidget(page)
            
    def configure_widgets(self):
        """Configure widgets from JSON configuration."""
        try:
            # Load style configuration
            config_path = current_dir / "ui_resources" / "json-styles" / "style.json"
            config = ThemeManager.load_style_config(str(config_path))
            
            if config:
                # Apply configurations
                widgets = {
                    "leftMenu": self.left_menu,
                    "mainPages": self.content_stack
                }
                
                ThemeManager.apply_custom_widget_configs(widgets, config)
                
                # Connect navigation buttons
                for page_name, btn in self.nav_buttons.items():
                    self.content_stack.connect_navigation_button(btn.text().split()[1].lower() + "Btn", btn)
                    
                print("✅ Widget configuration applied")
            else:
                print("❌ Could not load widget configuration")
                
        except Exception as e:
            print(f"Error configuring widgets: {e}")
            
    def switch_page(self, page_name: str):
        """Switch to a specific page."""
        # Update button states
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == page_name)
            
        # Switch page
        self.content_stack.switch_to_page_by_name(page_name)
        
    def test_animations(self):
        """Test animation functionality."""
        print("Testing animations...")
        
        # Toggle menu
        self.left_menu.toggle_menu()
        
        # Switch to random page after a delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.switch_page("raceCoachPage"))


def main():
    """Main function."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("TrackPro UI Test")
    app.setApplicationVersion("1.0")
    
    # Create and show window
    window = TestMainWindow()
    window.show()
    
    # Start with home page
    window.switch_page("homePage")
    
    print("🚀 TrackPro New UI Test Started!")
    print("✨ Testing modern interface components...")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()