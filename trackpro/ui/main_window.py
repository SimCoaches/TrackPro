"""Main application window class."""

import os
import sys
import logging
import traceback
import math

from .shared_imports import *
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QToolTip
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, QPointF, QMargins, Qt
from PyQt6.QtGui import QHideEvent, QShowEvent, QPainter, QPixmap, QPen, QBrush, QFont
from .chart_widgets import IntegratedCalibrationChart
from .auth_dialogs import PasswordDialog
from .theme import setup_dark_theme
from .menu_bar import create_menu_bar
from .system_tray import setup_system_tray

# Import version from shared_imports
from .shared_imports import __version__

# Set up logging
logger = logging.getLogger(__name__)


class CurvePreviewTooltip(QWidget):
    """Custom tooltip widget that shows a curve preview and description."""
    
    def __init__(self, curve_type, pedal_type, parent=None):
        super().__init__(parent)
        # Clean the curve type string to avoid any whitespace issues
        self.curve_type = curve_type.strip()
        self.pedal_type = pedal_type
        
        # Debug logging
        logger.debug(f"Creating CurvePreviewTooltip for curve '{self.curve_type}' (pedal: {pedal_type})")
        
        # Set up the widget
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 180)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(f"{self.curve_type}")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(title_label)
        
        # Create curve preview
        self.curve_preview = self.create_curve_preview()
        preview_label = QLabel()
        preview_label.setPixmap(self.curve_preview)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(preview_label)
        
        # Description
        description_info = MainWindow.get_curve_description(self.curve_type, pedal_type)
        desc_text = f"{description_info['description']}\n\nUse case: {description_info['use_case']}"
        
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc; background: transparent; font-size: 9pt;")
        layout.addWidget(desc_label)
        
        # Set background style
        self.setStyleSheet("""
            CurvePreviewTooltip {
                background-color: rgba(45, 45, 45, 240);
                border: 1px solid #666666;
                border-radius: 8px;
            }
        """)
    
    def create_curve_preview(self):
        """Create a small pixmap showing the curve shape."""
        logger.debug(f"Creating curve preview for '{self.curve_type}'")
        
        width, height = 280, 80
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up drawing area with margins
        margin = 10
        draw_width = width - 2 * margin
        draw_height = height - 2 * margin
        
        # Draw grid
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        for i in range(5):
            x = margin + i * draw_width // 4
            y = margin + i * draw_height // 4
            painter.drawLine(x, margin, x, height - margin)
            painter.drawLine(margin, y, width - margin, y)
        
        # Generate curve points
        curve_points = []
        for i in range(100):
            x_percent = i
            y_percent = self.calculate_curve_value(x_percent, self.curve_type)
            
            x = margin + (x_percent / 100.0) * draw_width
            y = height - margin - (y_percent / 100.0) * draw_height
            curve_points.append(QPointF(x, y))
        
        # Log a few sample points for debugging
        if len(curve_points) > 0:
            logger.debug(f"Sample curve points for '{self.curve_type}': 0%={self.calculate_curve_value(0, self.curve_type):.1f}, 50%={self.calculate_curve_value(50, self.curve_type):.1f}, 100%={self.calculate_curve_value(100, self.curve_type):.1f}")
        
        # Draw curve
        painter.setPen(QPen(QColor(100, 150, 255), 2))
        for i in range(len(curve_points) - 1):
            painter.drawLine(curve_points[i], curve_points[i + 1])
        
        # Draw reference line (linear)
        painter.setPen(QPen(QColor(120, 120, 120), 1, Qt.PenStyle.DashLine))
        painter.drawLine(margin, height - margin, width - margin, margin)
        
        painter.end()
        return pixmap
    
    def calculate_curve_value(self, x_percent, curve_type):
        """Calculate the Y value for a given X percentage based on curve type."""
        x = x_percent / 100.0  # Normalize to 0-1
        
        # Debug logging
        if x_percent == 50:  # Log only at midpoint to avoid spam
            logger.debug(f"Calculating curve for '{curve_type}' at x=50%")
        
        # Clean the curve type string
        curve_type = curve_type.strip()
        
        if curve_type == "Linear (Default)":
            return x * 100
        elif curve_type == "Progressive":
            result = (x ** 3) * 100
            if x_percent == 50:
                logger.debug(f"Progressive curve at 50%: {result}")
            return result
        elif curve_type == "Threshold":
            if x <= 0.25:
                return (x / 0.25) * 40
            else:
                return 40 + ((x - 0.25) / 0.75) * 60
        elif curve_type == "Trail Brake":
            if x <= 0.5:
                return x * 100
            else:
                normalized = (x - 0.5) / 0.5
                return 50 + (normalized ** 2) * 50
        elif curve_type == "Endurance":
            return 100 * (3 * x**2 - 2 * x**3)
        elif curve_type == "Rally":
            return (x ** 0.6) * 100
        elif curve_type == "ABS Friendly":
            return (x ** 1.8) * 100
        elif curve_type == "Track Mode":
            return (x ** 1.2) * 100
        elif curve_type == "Turbo Lag":
            if x <= 0.25:
                return ((x / 0.25) ** 2) * 15
            else:
                normalized = (x - 0.25) / 0.75
                return 15 + (normalized ** 0.7) * 85
        elif curve_type == "NA Engine":
            return (x ** 0.8) * 100
        elif curve_type == "Feathering":
            if x <= 0.5:
                return ((x / 0.5) ** 0.3) * 30
            else:
                return 30 + ((x - 0.5) / 0.5) * 70
        elif curve_type == "Quick Engage":
            if x <= 0.4:
                return ((x / 0.4) ** 0.4) * 80
            else:
                return 80 + ((x - 0.4) / 0.6) * 20
        elif curve_type == "Heel-Toe":
            return 100 * (6 * x**2 - 8 * x**3 + 3 * x**4)
        elif curve_type == "Bite Point Focus":
            if x <= 0.6:
                return ((x / 0.6) ** 0.3) * 50
            else:
                return 50 + ((x - 0.6) / 0.4) * 50
        else:
            # Log when falling back to linear
            if x_percent == 50:
                logger.warning(f"Unknown curve type '{curve_type}', falling back to linear")
            return x * 100


class CurveComboBox(QComboBox):
    """Custom combobox that shows curve preview tooltips."""
    
    def __init__(self, pedal_type, main_window=None, parent=None):
        super().__init__(parent)
        self.pedal_type = pedal_type
        self.main_window = main_window
        self.tooltip_widget = None
        self.last_hovered_index = None
        
        # Create persistent timer for hover delay
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._show_pending_tooltip)
        self.pending_tooltip_data = None
        
        # Install event filter to catch mouse events
        self.view().setMouseTracking(True)
        self.view().installEventFilter(self)
        
        # Connect to main window state changes to hide tooltip
        if self.main_window:
            self.main_window.window_state_changed.connect(self._on_main_window_state_changed)
        
        # Connect to application quit to clean up tooltip
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().aboutToQuit.connect(self.hide_tooltip)
        
        # Hide tooltip when losing focus or when popup closes
        self.view().destroyed.connect(self.hide_tooltip)
    
    def _on_main_window_state_changed(self, state):
        """Hide tooltip when main window state changes."""
        from PyQt6.QtCore import Qt
        if state & Qt.WindowState.WindowMinimized or not self.main_window.isVisible():
            self.hide_tooltip()
    
    def _show_pending_tooltip(self):
        """Slot to show the tooltip when the hover_timer times out."""
        if self.pending_tooltip_data:
            curve_type, pos = self.pending_tooltip_data
            self.show_curve_tooltip_for_item(curve_type, pos)
            self.pending_tooltip_data = None  # Clear data after showing
    
    def eventFilter(self, obj, event):
        """Handle mouse events to show/hide tooltips."""
        if obj == self.view():
            if event.type() == event.Type.MouseMove:
                index = self.view().indexAt(event.pos())
                if index.isValid():
                    # Get the actual text from the model at this index
                    curve_text = self.model().data(index, 0)  # Use model data instead of itemText
                    # Also try getting it via itemText as a backup
                    item_text_backup = self.itemText(index.row()) if index.row() < self.count() else None
                    
                    print(f"DEBUG: Index row: {index.row()}, count: {self.count()}")  # Debug logging
                    print(f"DEBUG: Model data: '{curve_text}'")  # Debug logging
                    print(f"DEBUG: ItemText backup: '{item_text_backup}'")  # Debug logging
                    
                    # Try both methods and use the first one that gives us a valid result
                    final_curve_text = None
                    if curve_text and str(curve_text).strip():
                        final_curve_text = str(curve_text).strip()
                    elif item_text_backup and str(item_text_backup).strip():
                        final_curve_text = str(item_text_backup).strip()
                        print(f"DEBUG: Using backup method, got: '{final_curve_text}'")
                    
                    if final_curve_text:
                        print(f"DEBUG: Final curve text: '{final_curve_text}'")  # Debug logging
                        
                        # Skip separator items
                        if final_curve_text and "───" not in final_curve_text:
                            # Show tooltip whenever hovering over a different index
                            current_index = index.row()
                            if current_index != self.last_hovered_index:
                                print(f"DEBUG: Capturing curve text: '{final_curve_text}' for timer (index: {current_index})")  # Debug logging
                                self.hide_tooltip()  # Hide any existing tooltip immediately
                                self.hover_timer.stop()  # Stop any pending timer
                                
                                # Get global position from event
                                try:
                                    current_pos = event.globalPosition().toPoint()
                                except AttributeError:
                                    # Fallback for older PyQt versions
                                    current_pos = event.globalPos()
                                
                                # Store data and start the persistent timer
                                self.pending_tooltip_data = (final_curve_text, current_pos)
                                self.hover_timer.start(300)  # Start the persistent timer
                                self.last_hovered_index = current_index
                        else:
                            self.hide_tooltip()
                            self.hover_timer.stop()  # Stop timer for separators
                            self.last_hovered_index = None
                else:
                    self.hide_tooltip()
                    self.hover_timer.stop()  # Stop timer when no valid index
                    self.last_hovered_index = None
            elif event.type() == event.Type.Leave:
                self.hide_tooltip()
                self.hover_timer.stop()  # Stop timer when mouse leaves
                self.last_hovered_index = None
        
        return super().eventFilter(obj, event)
    
    def show_curve_tooltip_for_item(self, curve_type, pos):
        """Show the curve preview tooltip for a specific curve type and position."""
        print(f"DEBUG: show_curve_tooltip_for_item called with curve_type: '{curve_type}', pos: {pos}")  # Debug logging
        if curve_type:
            # Only show tooltip for built-in curves (not custom saved ones)
            built_in_curves = MainWindow.get_pedal_curves(self.pedal_type)
            print(f"DEBUG: Built-in curves for {self.pedal_type}: {built_in_curves}")  # Debug logging
            print(f"DEBUG: Checking if '{curve_type}' is in built_in_curves")  # Debug logging
            
            if curve_type in built_in_curves:
                print(f"DEBUG: Creating tooltip for: '{curve_type}'")  # Debug logging
                self.hide_tooltip()  # Hide any existing tooltip
                
                self.tooltip_widget = CurvePreviewTooltip(
                    curve_type, 
                    self.pedal_type, 
                    self
                )
                
                # Position tooltip based on pedal type to avoid blocking curve options
                if pos:
                    tooltip_pos = pos
                    
                    # Adjust horizontal position based on pedal type
                    if self.pedal_type == 'clutch':
                        # For clutch, move tooltip far to the left to avoid overlap
                        tooltip_pos.setX(tooltip_pos.x() - self.tooltip_widget.width() - 100)
                    else:
                        # For throttle and brake, move tooltip far to the right to completely clear dropdown
                        tooltip_pos.setX(tooltip_pos.x() + 250)
                    
                    # Move tooltip up to avoid cursor interference
                    tooltip_pos.setY(tooltip_pos.y() - 100)
                    self.tooltip_widget.move(tooltip_pos)
                
                self.tooltip_widget.show()
            else:
                print(f"DEBUG: '{curve_type}' not found in built-in curves")  # Debug logging
    
    def hide_tooltip(self):
        """Hide the curve preview tooltip."""
        self.hover_timer.stop()  # Stop any pending timer
        self.pending_tooltip_data = None  # Clear pending data
        if self.tooltip_widget:
            self.tooltip_widget.hide()
            self.tooltip_widget.deleteLater()
            self.tooltip_widget = None
    
    def hidePopup(self):
        """Override to hide tooltip when popup closes."""
        self.hide_tooltip()
        super().hidePopup()
    
    def hideEvent(self, event):
        """Hide tooltip when the combobox itself is hidden."""
        self.hide_tooltip()
        super().hideEvent(event)
    
    def showEvent(self, event):
        """Override showEvent for debugging."""
        print(f"DEBUG: CurveComboBox showEvent called")
        super().showEvent(event)


class MainWindow(QMainWindow):
    """Main application window."""
    
    # Signals
    calibration_updated = pyqtSignal(str)  # Emits pedal name when calibration changes
    auth_state_changed = pyqtSignal(bool)  # Emits when authentication state changes
    window_state_changed = pyqtSignal(object)  # Emits when window state changes
    
    @staticmethod
    def get_pedal_curves(pedal_type):
        """Get the list of curves specific to each pedal type."""
        if pedal_type == 'brake':
            return [
                "Linear (Default)", "Threshold", "Trail Brake", 
                "Endurance", "Rally", "ABS Friendly"
            ]
        elif pedal_type == 'throttle':
            return [
                "Linear (Default)", "Track Mode", "Turbo Lag", 
                "NA Engine", "Feathering", "Progressive"
            ]
        elif pedal_type == 'clutch':
            return [
                "Linear (Default)", "Quick Engage", "Heel-Toe", "Bite Point Focus"
            ]
        else:
            # Fallback to brake curves if unknown pedal type
            return MainWindow.get_pedal_curves('brake')
    
    @staticmethod
    def get_curve_description(curve_type, pedal_type):
        """Get description and use case for each curve type."""
        descriptions = {
            # Universal curves
            "Linear (Default)": {
                "description": "1:1 linear response, no modification",
                "use_case": "Baseline curve, good for most situations"
            },
            
            # Brake curves
            "Threshold": {
                "description": "Sharp initial response for maximum braking",
                "use_case": "Formula cars, prototypes - late braking into corners"
            },
            "Trail Brake": {
                "description": "Linear start, aggressive end for corner entry",
                "use_case": "Road racing - carry speed through corners"
            },
            "Endurance": {
                "description": "S-curve for consistent long-stint pressure",
                "use_case": "GT3, endurance racing - tire management"
            },
            "Rally": {
                "description": "Quick response designed for loose surfaces",
                "use_case": "Off-road, dirt oval - loose surface braking"
            },
            "ABS Friendly": {
                "description": "Smooth modulation works well with ABS",
                "use_case": "Modern cars with ABS systems"
            },
            
            # Throttle curves
            "Track Mode": {
                "description": "Balanced curve for precise racing control",
                "use_case": "Most road racing - balanced performance"
            },
            "Turbo Lag": {
                "description": "Mimics turbo spooling with delayed response",
                "use_case": "GT3, modern cars - turbocharged engines"
            },
            "NA Engine": {
                "description": "Smooth linear progression",
                "use_case": "NASCAR, classic cars - naturally aspirated"
            },
            "Feathering": {
                "description": "Precise low-speed control in first 50%",
                "use_case": "Off-road, tight courses - traction control"
            },
            "Progressive": {
                "description": "Starts slow, builds progressively",
                "use_case": "General racing, wet conditions - smooth buildup"
            },
            
            # Clutch curves
            "Quick Engage": {
                "description": "Fast clutch engagement for racing starts",
                "use_case": "Racing starts, quick shifts"
            },
            "Heel-Toe": {
                "description": "Optimized for heel-toe downshifting",
                "use_case": "Manual shifting, downshift technique"
            },
            "Bite Point Focus": {
                "description": "Emphasis on finding the engagement point",
                "use_case": "Learning clutch control, precise launches"
            }
        }
        
        return descriptions.get(curve_type, {
            "description": "Custom curve configuration",
            "use_case": "User-defined response curve"
        })
    
    def __init__(self, oauth_handler=None):
        """Initialize the main window."""
        # Import here to avoid circular imports
        from ..auth import LoginDialog, SignupDialog
        from ..database import supabase, user_manager
        
        super().__init__()
        # Main window setup with menu bar buttons - increased minimum size to prevent overlapping
        self.window_width = 1200
        self.window_height = 800
        self.setWindowTitle("TrackPro Configuration v1.5.4")
        self.setMinimumSize(1200, 850)  # Increased from 1000x700 to prevent overlapping
        # Set window icon using file path instead of Qt resource
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icons", "trackpro_tray.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                # Fallback for packaged application
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icons", "trackpro_tray.ico")
                if os.path.exists(icon_path):
                    self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            # If icon loading fails, continue without icon
            import logging
            logging.getLogger(__name__).warning(f"Could not load window icon: {e}")

        # Store the shared OAuth handler
        self.oauth_handler = oauth_handler

        # Attributes for calibration data
        self.pedal_data = {}
        
        # Initialize pedal group storage
        self.pedal_groups = {}
        
        # Add race_coach_widget and hardware attributes to track them
        self.race_coach_widget = None
        self.hardware = None
        
        # Track Map Overlay Manager - make it persistent
        self.track_map_overlay_manager = None
        
        # Initialize global iRacing connection manager
        self.global_iracing_api = None
        self.iracing_connection_active = False
        
        # Initialize system tray using extracted function
        setup_system_tray(self)
        
        # Set dark theme using extracted function
        setup_dark_theme(self)
        
        # Create authentication/navigation buttons FIRST (needed for menu bar)
        self.create_auth_buttons()
        
        # Create menu bar using extracted function
        create_menu_bar(self)
        
        # Create the main widget and layout - CLEAN, no extra headers
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add smaller calibration wizard button
        wizard_layout = QHBoxLayout()
        self.calibration_wizard_btn = QPushButton("Calibration Wizard")
        self.calibration_wizard_btn.setMaximumWidth(140)  # Make button smaller
        self.calibration_wizard_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                font-size: 11px;
                font-weight: bold;
                padding: 6px 12px;
                max-width: 140px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        self.calibration_wizard_btn.clicked.connect(self.open_calibration_wizard)
        
        wizard_layout.addWidget(self.calibration_wizard_btn)
        wizard_layout.addStretch()
        layout.addLayout(wizard_layout)
        
        # Create a stacked widget for switching between screens
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create the main pedals screen
        pedals_screen = QWidget()
        pedals_layout = QVBoxLayout(pedals_screen)
        pedals_layout.setContentsMargins(12, 12, 12, 12)  # Add margins for content
        pedals_layout.setSpacing(8)  # Add some spacing back
        
        # Add pedal controls section
        pedals_section_layout = QHBoxLayout()
        pedals_layout.addLayout(pedals_section_layout)
        
        # Initialize pedal data
        self._init_pedal_data()
        
        # Create a widget for each pedal
        for pedal in ['throttle', 'brake', 'clutch']:
            pedal_widget = QWidget()
            pedal_widget.setObjectName(f"{pedal}_widget")
            pedal_layout = QVBoxLayout(pedal_widget)
            pedal_layout.setContentsMargins(5, 5, 5, 5)
            pedal_layout.setSpacing(5)
            
            # Remove pedal name headers to save vertical space
            # and avoid redundancy as the UI is already structured by pedal
            
            self.create_pedal_controls(pedal, pedal_layout)
            pedals_section_layout.addWidget(pedal_widget)
        
        # Make the layout stretch evenly
        pedals_section_layout.setStretch(0, 1)
        pedals_section_layout.setStretch(1, 1)
        pedals_section_layout.setStretch(2, 1)
        
        # Add the pedals screen to the stacked widget
        self.stacked_widget.addWidget(pedals_screen)
        
        # Connect stacked widget's currentChanged signal to handle visibility of calibration buttons
        self.stacked_widget.currentChanged.connect(self._on_tab_changed)
        
        # Add update notification label at the bottom
        self.update_notification = QLabel("")
        self.update_notification.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                padding: 5px;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                background-color: rgba(76, 175, 80, 0.1);
            }
        """)
        self.update_notification.setVisible(False)
        layout.addWidget(self.update_notification, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Create enhanced status bar with login info
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Add version information to status bar (left side)
        version_label = QLabel(f"Version: {__version__}")
        self.statusBar.addWidget(version_label)
        
        # Add iRacing connection status to status bar
        self.iracing_status_label = QLabel("🏁 iRacing: Disconnected")
        self.iracing_status_label.setStyleSheet("color: #ff6b6b; font-size: 10px; padding: 2px 8px; font-weight: bold;")
        self.iracing_status_label.setToolTip("iRacing connection status - click to toggle")
        self.iracing_status_label.mousePressEvent = lambda event: self.toggle_iracing_connection()
        self.statusBar.addPermanentWidget(self.iracing_status_label)
        
        # Add user info and cloud sync status to right side of status bar
        self.user_label = QLabel("Not logged in")
        self.user_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 8px;")
        self.statusBar.addPermanentWidget(self.user_label)
        
        self.cloud_sync_label = QLabel("☁️ Sign in to enable cloud sync")
        self.cloud_sync_label.setStyleSheet("color: #3498db; cursor: pointer; font-size: 10px; padding: 2px 8px;")
        self.statusBar.addPermanentWidget(self.cloud_sync_label)
        
        # Add real-time pedal performance indicator
        self.pedal_status_label = QLabel("🎮 Pedals: Starting...")
        self.pedal_status_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        self.pedal_status_label.setFixedHeight(25)
        self.pedal_status_label.setMinimumWidth(200)
        self.statusBar.addPermanentWidget(self.pedal_status_label)
        
        # Timer to update pedal status display
        self.pedal_status_timer = QTimer()
        self.pedal_status_timer.timeout.connect(self.update_pedal_status_display)
        self.pedal_status_timer.start(1000)  # Update every second

        # IMPORTANT: Update authentication state on startup to restore session
        # Use a longer delay to make sure all components are properly initialized
        logger.info("Scheduling authentication state update after initialization")
        QTimer.singleShot(500, self.update_auth_state)
        
        # Defer early notification system setup until after window is shown
        QTimer.singleShot(1000, self.setup_early_notification_system)
        
        # Start global iRacing connection if user is authenticated
        QTimer.singleShot(2000, self.check_and_start_iracing_connection)
    
    # Keep all the MainWindow methods but remove the ones we extracted
    # setup_dark_theme, create_menu_bar, setup_system_tray methods are now in separate modules
    
    def changeEvent(self, event):
        """Handle window change events and emit custom signal for window state changes."""
        if event.type() == event.Type.WindowStateChange:
            self.window_state_changed.emit(self.windowState())
        super().changeEvent(event)
    
    def closeEvent(self, event):
        """Handle window close event - FORCE KILL ALL PROCESSES."""
        try:
            # Check if this should minimize to tray instead of closing
            from ..config import config
            if config.minimize_to_tray and hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                logger.info("Minimizing to tray instead of closing")
                self.hide()
                event.ignore()
                return
            
            logger.info("FORCE CLOSING - Killing all TrackPro processes...")
            
            # STEP 1: Force kill ALL TrackPro processes immediately
            self._force_kill_all_trackpro_processes()
            
            # STEP 2: Clean up single instance locks
            self._cleanup_single_instance_locks_immediate()
            
            # STEP 3: Hide tray icon
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
            
            # STEP 4: Force quit application immediately
            logger.info("Force quitting application...")
            event.accept()
            QApplication.instance().quit()
            
        except Exception as e:
            logger.error(f"Error during force close: {e}")
            # Force quit no matter what
            event.accept()
            try:
                QApplication.instance().quit()
            except:
                import sys
                sys.exit(0)
    

    
    def _force_kill_all_trackpro_processes(self):
        """Force kill ALL TrackPro processes using taskkill."""
        try:
            logger.info("🔫 FORCE KILLING all TrackPro processes...")
            
            # Use subprocess utility to hide windows
            from ..utils.subprocess_utils import run_subprocess
            
            # Kill ALL TrackPro processes with extreme prejudice (but protect IDEs)
            kill_commands = [
                ['taskkill', '/F', '/IM', 'TrackPro*.exe'],
                ['taskkill', '/F', '/T', '/IM', 'TrackPro_v1.5.4.exe'],
                # More specific PowerShell command that excludes IDEs
                ['powershell', '-Command', '''Get-Process | Where-Object {
                    (($_.ProcessName -eq "TrackPro" -or 
                      $_.ProcessName -like "TrackPro_v*" -or 
                      $_.ProcessName -like "TrackPro_Setup*") -or
                     ($_.MainWindowTitle -like "*TrackPro*" -and 
                      $_.ProcessName -eq "python" -or $_.ProcessName -eq "pythonw")) -and
                    $_.ProcessName -notlike "*Cursor*" -and
                    $_.ProcessName -notlike "*Code*" -and
                    $_.ProcessName -notlike "*Visual*" -and
                    $_.ProcessName -notlike "*Studio*" -and
                    $_.MainWindowTitle -notlike "*Cursor*" -and
                    $_.MainWindowTitle -notlike "*Visual Studio Code*" -and
                    $_.MainWindowTitle -notlike "*Visual Studio*"
                } | Stop-Process -Force'''],
            ]
            
            for cmd in kill_commands:
                try:
                    result = run_subprocess(cmd, hide_window=True, capture_output=True, text=True, check=False, timeout=5)
                    if result.returncode == 0:
                        logger.info(f"✅ Successfully killed processes with: {' '.join(cmd)}")
                    else:
                        logger.info(f"No processes found for: {' '.join(cmd)}")
                except Exception as e:
                    logger.warning(f"Kill command failed {cmd}: {e}")
            
            logger.info("🔫 Force kill completed")
            
        except Exception as e:
            logger.error(f"Error during force kill: {e}")
    
    def _cleanup_single_instance_locks_immediate(self):
        """Immediately clean up single instance locks."""
        try:
            logger.info("🔓 Cleaning up locks...")
            import tempfile
            import os
            
            # Remove lock file
            lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info("✅ Removed lock file")
                except Exception as e:
                    logger.warning(f"Could not remove lock file: {e}")
            
            logger.info("🔓 Lock cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during lock cleanup: {e}")
    
    def _init_pedal_data(self):
        """Initialize pedal data storage."""
        self._pedal_data = {
            'throttle': {},
            'brake': {},
            'clutch': {}
        }
        logger.info("Pedal data initialized")

    # NOTE: The rest of the MainWindow methods would go here, but I'm truncating for brevity
    # In the real implementation, ALL methods from the original MainWindow class would be included here
    # except for setup_dark_theme, create_menu_bar, and setup_system_tray which are now in separate modules
    
    # PLACEHOLDER: Add remaining methods from original MainWindow class
    # This would include all methods from create_pedal_controls through show_about
    # For now, I'll add just a few key methods to show the structure:
    
    def create_pedal_controls(self, pedal_name, parent_layout):
        """Create controls for a single pedal."""
        pedal_key = pedal_name.lower()
        data = self._pedal_data[pedal_key]
        
        # Input Monitor
        input_group = QGroupBox("Input Monitor")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(5, 5, 5, 5)
        
        progress = QProgressBar()
        progress.setRange(0, 65535)
        progress.setMinimumHeight(22)
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 2px;
                text-align: center;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        input_layout.addWidget(progress)
        data['input_progress'] = progress
        
        label = QLabel("Raw Input: 0")
        label.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(label)
        data['input_label'] = label
        
        input_group.setLayout(input_layout)
        parent_layout.addWidget(input_group)
        
        # Add spacing between Input Monitor and Calibration - REDUCED
        parent_layout.addSpacing(5)  # Reduced from 15 to 5
        
        # Store the group box for enabling/disabling the whole pedal section
        self.pedal_groups[pedal_key] = input_group
        
        # Calibration
        cal_group = QGroupBox("Calibration")
        cal_layout = QVBoxLayout()
        cal_layout.setContentsMargins(5, 5, 5, 5)  # Reduce top margin from 5 to 0
        cal_layout.setSpacing(5)  # Reduce spacing from 10 to 5
        
        # Add the integrated calibration chart - this replaces all the old chart code
        logger.info(f"Creating IntegratedCalibrationChart for {pedal_name}")
        try:
            calibration_chart = IntegratedCalibrationChart(
                cal_layout, 
                pedal_name,
                lambda: self.on_point_moved(pedal_key)
            )
            logger.info(f"Successfully created IntegratedCalibrationChart for {pedal_name}")
            
            # Store the chart in the pedal data
            data['calibration_chart'] = calibration_chart
        except Exception as e:
            logger.error(f"Failed to create IntegratedCalibrationChart for {pedal_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Create a placeholder widget so layout doesn't break
            placeholder = QLabel(f"Chart error for {pedal_name}")
            placeholder.setStyleSheet("background-color: red; color: white; padding: 10px;")
            cal_layout.addWidget(placeholder)
            data['calibration_chart'] = None
        
        # Update the calibration chart to have more space at the bottom
        # Use an alternative approach that doesn't require QMargins
        if data['calibration_chart'] is not None:
            data['calibration_chart'].chart.setPlotAreaBackgroundVisible(True)
            data['calibration_chart'].chart.setBackgroundVisible(True)
            
            # Try to add spacing without using QMargins
            try:
                # First try setting chart margins directly
                data['calibration_chart'].chart_view.setContentsMargins(10, 0, 10, 10)  # Reduce bottom margin from 40 to 10
                # Also set the chart's own margins
                data['calibration_chart'].chart.setMargins(QMargins(10, 10, 10, 10))  # Reduce bottom margin from 40 to 10
            except Exception as e:
                logger.error(f"Failed to set chart margins: {e}")
                pass
            
        # Add consistent spacing after the chart view - REDUCED
        cal_layout.addSpacing(10)  # Reduce from 70px to 10px
        
        # Calibration controls section - use vertical layout to stack rows
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(5, 20, 5, 5)  # Add more top margin to the controls section (increased from 15 to 20)
        controls_layout.setSpacing(12)  # Increase spacing between label row and button row (increased from 8 to 12)
        
        # First row: Labels aligned with their respective controls
        labels_row = QHBoxLayout()
        labels_row.setSpacing(10)
        
        # Min label
        min_label = QLabel("Min: 0")
        labels_row.addWidget(min_label, 1)
        
        # Max label
        max_label = QLabel("Max: 65535")
        labels_row.addWidget(max_label, 1)
        
        # Reset label
        reset_label = QLabel("Reset Curve")
        labels_row.addWidget(reset_label, 1)
        
        # Add spacer
        labels_row.addStretch(1)
        
        # Curve type label
        curve_label = QLabel("Curve Type")
        labels_row.addWidget(curve_label, 2)
        
        # Add labels row to main layout
        controls_layout.addLayout(labels_row)
        
        # Second row: Actual controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        
        # Set Min button
        set_min_btn = QPushButton("Set Min")
        set_min_btn.clicked.connect(lambda: self.set_current_as_min(pedal_key))
        set_min_btn.setFixedHeight(27)
        controls_row.addWidget(set_min_btn, 1)
        
        # Set Max button
        set_max_btn = QPushButton("Set Max")
        set_max_btn.clicked.connect(lambda: self.set_current_as_max(pedal_key))
        set_max_btn.setFixedHeight(27)
        controls_row.addWidget(set_max_btn, 1)
        
        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(lambda: self.reset_calibration(pedal_key))
        reset_btn.setFixedHeight(27)
        controls_row.addWidget(reset_btn, 1)
        
        # Add spacer to push curve selector to the right
        controls_row.addStretch(1)
        
        # Create the combo box for curve selection with pedal-specific curves
        curve_selector = CurveComboBox(pedal_key, self)
        pedal_curves = self.get_pedal_curves(pedal_key)
        curve_selector.addItems(pedal_curves)
        curve_selector.setCurrentText("Linear (Default)")
        
        # Size settings - strictly enforce the height with fixed size policy
        curve_selector.setMinimumWidth(130)  # Reduced from 180 to 130
        curve_selector.setMaximumWidth(140)  # Add maximum width constraint
        try:
            curve_selector.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fixed in both directions
        except AttributeError:
            try:
                curve_selector.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fixed in both directions
            except AttributeError:
                pass  # Skip if not available
        curve_selector.setFixedHeight(27)
        
        # Style with precise height control
        curve_selector.setStyleSheet("""
            QComboBox {
                background-color: #444444;
                border: 1px solid #777777;
                border-radius: 4px;
                color: white;
                padding: 0px 5px;  /* Reduced side padding */
                height: 27px;
                max-height: 27px;
                min-height: 27px;
                font-size: 12px;
                text-align: left;  /* Ensure text is left-aligned */
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 15px;
                height: 20px;
                border: none;  /* Remove border */
                background: transparent;  /* Make background transparent */
            }
            
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border: 4px solid transparent;
                border-top: 4px solid #aaa;  /* Lighter color */
                margin-right: 2px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #444444;
                border: 1px solid #777777;
                selection-background-color: #2a82da;
                selection-color: white;
                color: white;
                padding: 1px;  /* Minimal padding */
            }
        """)
        
        # Connect signals for built-in curve type changes
        curve_selector.currentTextChanged.connect(lambda text: self.on_curve_type_changed(pedal_key, text))
        
        # Add combo box to controls row
        controls_row.addWidget(curve_selector, 2)
        
        # Add controls row to main layout
        controls_layout.addLayout(controls_row)
        
        # Add spacer below the controls
        controls_layout.addSpacing(10)
        
        # Store the curve selector in data
        data['curve_type_selector'] = curve_selector
        
        # Log widget creation
        logger.info(f"[{pedal_key}] Creating curve_type_selector with ID: {id(curve_selector)}")
        
        # Store all calibration controls in the data dictionary
        data['min_label'] = min_label
        data['max_label'] = max_label
        data['min_value'] = 0
        data['max_value'] = 65535
        
        # Standardize button heights
        set_min_btn.setFixedHeight(27)
        set_max_btn.setFixedHeight(27)
        reset_btn.setFixedHeight(27)
        
        # Fix alignments
        min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        curve_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add the controls layout to the main layout
        cal_layout.addLayout(controls_layout)
        cal_layout.addSpacing(5)  # Reduced from 20 to 5
        
        # Add deadzone controls
        deadzone_group = QGroupBox("Deadzones (%)")
        deadzone_layout = QVBoxLayout()
        
        # Min deadzone controls
        min_deadzone_layout = QHBoxLayout()
        min_deadzone_label = QLabel("Min Deadzone:")
        min_deadzone_layout.addWidget(min_deadzone_label)
        
        min_deadzone_value = QLabel("0%")
        min_deadzone_value.setMinimumWidth(40)
        min_deadzone_layout.addWidget(min_deadzone_value)
        
        min_deadzone_minus = QPushButton("-")
        min_deadzone_minus.setFixedWidth(30)
        min_deadzone_minus.setStyleSheet("padding: 2px 5px;")
        min_deadzone_minus.clicked.connect(lambda: self.adjust_min_deadzone(pedal_key, -1))
        min_deadzone_layout.addWidget(min_deadzone_minus)
        
        min_deadzone_plus = QPushButton("+")
        min_deadzone_plus.setFixedWidth(30)
        min_deadzone_plus.setStyleSheet("padding: 2px 5px;")
        min_deadzone_plus.clicked.connect(lambda: self.adjust_min_deadzone(pedal_key, 1))
        min_deadzone_layout.addWidget(min_deadzone_plus)
        
        deadzone_layout.addLayout(min_deadzone_layout)
        
        # Max deadzone controls
        max_deadzone_layout = QHBoxLayout()
        max_deadzone_label = QLabel("Max Deadzone:")
        max_deadzone_layout.addWidget(max_deadzone_label)
        
        max_deadzone_value = QLabel("0%")
        max_deadzone_value.setMinimumWidth(40)
        max_deadzone_layout.addWidget(max_deadzone_value)
        
        max_deadzone_minus = QPushButton("-")
        max_deadzone_minus.setFixedWidth(30)
        max_deadzone_minus.setStyleSheet("padding: 2px 5px;")
        max_deadzone_minus.clicked.connect(lambda: self.adjust_max_deadzone(pedal_key, -1))
        max_deadzone_layout.addWidget(max_deadzone_minus)
        
        max_deadzone_plus = QPushButton("+")
        max_deadzone_plus.setFixedWidth(30)
        max_deadzone_plus.setStyleSheet("padding: 2px 5px;")
        max_deadzone_plus.clicked.connect(lambda: self.adjust_max_deadzone(pedal_key, 1))
        max_deadzone_layout.addWidget(max_deadzone_plus)
        
        deadzone_layout.addLayout(max_deadzone_layout)
        
        deadzone_group.setLayout(deadzone_layout)
        cal_layout.addWidget(deadzone_group)
        
        # Store deadzone controls in data for updating
        data['min_deadzone_value'] = min_deadzone_value
        data['max_deadzone_value'] = max_deadzone_value
        data['min_deadzone'] = 0
        data['max_deadzone'] = 0
        
        # Finalize the calibration group
        cal_group.setLayout(cal_layout)
        # Add the calibration group with stretch factor to prioritize vertical expansion
        parent_layout.addWidget(cal_group, 1)  # stretch factor of 1 to expand vertically
        
        # Add spacing between Calibration and Output Monitor - REDUCED
        parent_layout.addSpacing(5)  # Reduced from 15 to 5
        
        # Output Monitor
        output_group = QGroupBox("Output Monitor")
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(5, 5, 5, 5)
        
        progress = QProgressBar()
        progress.setRange(0, 65535)
        progress.setMinimumHeight(22)
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 2px;
                text-align: center;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        output_layout.addWidget(progress)
        data['output_progress'] = progress
        
        label = QLabel("Mapped Output: 0")
        label.setStyleSheet("font-weight: bold;")
        output_layout.addWidget(label)
        data['output_label'] = label
        
        output_group.setLayout(output_layout)
        parent_layout.addWidget(output_group)
        
        # Add spacing between Output Monitor and Curve Management - REDUCED
        parent_layout.addSpacing(5)  # Reduced from 15 to 5
        
        # Curve Management
        manager_group = QGroupBox("Curve Management")
        manager_layout = QGridLayout()
        manager_layout.setContentsMargins(5, 5, 5, 5)
        manager_layout.setVerticalSpacing(5)
        
        # Curve Name Input
        name_label = QLabel("Curve Name:")
        manager_layout.addWidget(name_label, 0, 0)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter curve name...")
        manager_layout.addWidget(name_input, 0, 1, 1, 2)
        
        # Save Button
        save_btn = QPushButton("Save Curve")
        save_btn.setFixedHeight(27)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        save_btn.clicked.connect(lambda: self.save_custom_curve(pedal_key, name_input.text()))
        manager_layout.addWidget(save_btn, 0, 3)
        
        # Delete Button (delete currently selected curve from the main Curve Type dropdown)
        delete_btn = QPushButton("Delete Selected Curve")
        delete_btn.setFixedHeight(27)
        delete_btn.setStyleSheet("background-color: #F44336; color: white;")
        delete_btn.clicked.connect(lambda: self.delete_current_curve(pedal_key))
        manager_layout.addWidget(delete_btn, 1, 0, 1, 4)  # Span across all columns
        
        # Store references for curve management
        data['curve_name_input'] = name_input
        
        # Set up the layout
        manager_group.setLayout(manager_layout)
        parent_layout.addWidget(manager_group)
        
        # Store the QGroupBox for the pedal
        data['group_box'] = cal_group
        
        # *** FIX: Make sure all widgets are properly shown ***
        manager_group.show()
    
    def set_input_value(self, pedal: str, value: int):
        """Set the input value for a pedal."""
        data = self._pedal_data[pedal]
        data['input_value'] = value
        data['input_progress'].setValue(value)
        data['input_label'].setText(f"Raw Input: {value}")
        
        # Calculate input percentage based on calibration range
        min_val = data['min_value']
        max_val = data['max_value']
        
        # Map the raw input value to a percentage based on calibration range
        if max_val > min_val:
            if value <= min_val:
                input_percentage = 0
            elif value >= max_val:
                input_percentage = 100
            else:
                input_percentage = ((value - min_val) / (max_val - min_val)) * 100
        else:
            input_percentage = 0
            
        input_percentage = max(0, min(100, input_percentage))  # Clamp to 0-100
        
        # Update the integrated chart with the new input position
        # This handles the green dot position and output calculation in one step
        calibration_chart = data['calibration_chart']
        calibration_chart.update_input_position(input_percentage)
        
        # Get the output value directly from the chart
        output_value = calibration_chart.get_output_value()
        
        # Update output display
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
    
    def create_auth_buttons(self):
        """Create authentication/navigation buttons."""
        # Create auth button container
        self.community_btn_container = QWidget()
        self.community_btn_container.setStyleSheet("background-color: transparent;")
        
        # Create individual auth buttons
        self.account_btn = QPushButton("Account")
        self.account_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        self.account_btn.clicked.connect(self.open_account_settings)
        self.account_btn.setVisible(False)  # Initially hidden until logged in
        
        self.login_btn = QPushButton("Login")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5DBF61;
            }
        """)
        self.login_btn.clicked.connect(self.show_login_dialog)
        
        self.signup_btn = QPushButton("Sign Up")
        self.signup_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #FFB74D;
            }
        """)
        self.signup_btn.clicked.connect(self.show_signup_dialog)
        
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #ef5350;
            }
        """)
        self.logout_btn.clicked.connect(self.handle_logout)
        self.logout_btn.setVisible(False)  # Initially hidden
    
    def show_message(self, title: str, message: str):
        """Show a message dialog."""
        QMessageBox.information(self, title, message)
    
    def set_input_value(self, pedal: str, value: int):
        """Set the input value for a pedal."""
        data = self._pedal_data[pedal]
        data['input_value'] = value
        data['input_progress'].setValue(value)
        data['input_label'].setText(f"Raw Input: {value}")
        
        # Calculate input percentage based on calibration range
        min_val = data['min_value']
        max_val = data['max_value']
        
        # Map the raw input value to a percentage based on calibration range
        if max_val > min_val:
            if value <= min_val:
                input_percentage = 0
            elif value >= max_val:
                input_percentage = 100
            else:
                input_percentage = ((value - min_val) / (max_val - min_val)) * 100
        else:
            input_percentage = 0
            
        input_percentage = max(0, min(100, input_percentage))  # Clamp to 0-100
        
        # Update the integrated chart with the new input position
        # This handles the green dot position and output calculation in one step
        calibration_chart = data['calibration_chart']
        calibration_chart.update_input_position(input_percentage)
        
        # Get the output value directly from the chart
        output_value = calibration_chart.get_output_value()
        
        # Update output display
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
    
    def on_point_moved(self, pedal: str):
        """Handle when a calibration point is moved by the user."""
        data = self._pedal_data[pedal]
        calibration_chart = data['calibration_chart']
        
        # The chart has already been updated internally in its own on_control_point_moved method
        # Just get the updated points for storage and signal purposes
        points = calibration_chart.get_points()
        data['points'] = points
        
        # Get the current output value from the chart
        output_value = calibration_chart.get_output_value()
        
        # Update output display
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
        
        # Mark as custom curve type
        data['curve_type'] = "Custom"
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def set_current_as_min(self, pedal: str):
        """Set the current input value as the minimum for calibration."""
        data = self._pedal_data[pedal]
        current_value = data.get('input_value', 0)
        
        # Don't allow min to be higher than max
        if current_value >= data['max_value']:
            self.show_message("Calibration Error", "Minimum value must be less than maximum value")
            return
            
        # Update the calibration min value but don't change the raw input display
        data['min_value'] = current_value
        data['min_label'].setText(f"Min: {current_value}")
        
        # Emit signal to update calibration
        self.calibration_updated.emit(pedal)
    
    def set_current_as_max(self, pedal: str):
        """Set the current input value as the maximum for calibration."""
        data = self._pedal_data[pedal]
        current_value = data.get('input_value', 0)
        
        # Don't allow max to be lower than min
        if current_value <= data['min_value']:
            self.show_message("Calibration Error", "Maximum value must be greater than minimum value")
            return
            
        # Update the calibration max value but don't change the raw input display
        data['max_value'] = current_value
        data['max_label'].setText(f"Max: {current_value}")
        
        # Emit signal to update calibration
        self.calibration_updated.emit(pedal)
    
    def reset_calibration(self, pedal: str):
        """Reset calibration for a pedal to linear."""
        data = self._pedal_data[pedal]
        
        # Reset to linear curve
        if 'calibration_chart' in data:
            calibration_chart = data['calibration_chart']
            calibration_chart.reset_to_linear()
        
        # Reset curve type selector
        if 'curve_type_selector' in data:
            data['curve_type_selector'].setCurrentText("Linear (Default)")
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def on_curve_type_changed(self, pedal: str, curve_type: str):
        """Handle curve type selection change (both built-in and saved curves)."""
        if not curve_type or curve_type in ["Loading...", "─── Saved Curves ───"]:
            return
        
        logger.info(f"Curve changed for {pedal}: {curve_type}")
        
        # Check if this is a built-in curve type or a saved curve
        built_in_curves = self.get_pedal_curves(pedal)
        
        if curve_type in built_in_curves:
            # Handle built-in curve types - generate curve points
            self.change_response_curve(pedal, curve_type)
        else:
            # Handle saved custom curves - load saved points
            self.load_custom_curve(pedal, curve_type)
    
    def delete_current_curve(self, pedal: str):
        """Delete the currently selected curve."""
        data = self._pedal_data[pedal]
        if 'curve_type_selector' not in data:
            return
            
        current_curve = data['curve_type_selector'].currentText()
        
        # Don't allow deleting built-in curves or separators
        # Get all built-in curves across all pedal types
        all_built_in_curves = set()
        for pedal_type in ['brake', 'throttle', 'clutch']:
            all_built_in_curves.update(self.get_pedal_curves(pedal_type))
        
        if current_curve in all_built_in_curves or current_curve in ["─── Saved Curves ───", ""]:
            self.show_message("Cannot Delete", "Cannot delete built-in curve types")
            return
        
        # Confirm deletion
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, 
            "Delete Curve", 
            f"Are you sure you want to delete the curve '{current_curve}' for {pedal}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete the curve
            self.delete_custom_curve(pedal, current_curve)
    
    def on_saved_curve_changed(self, pedal: str, curve_name: str):
        """Legacy method - now redirects to unified handler."""
        self.on_curve_type_changed(pedal, curve_name)
    
    def on_curve_selector_changed(self, pedal: str, curve_name: str):
        """Legacy method - now redirects to unified handler."""
        self.on_curve_type_changed(pedal, curve_name)
    
    def change_response_curve(self, pedal: str, curve_type: str):
        """Change the response curve type for a pedal (built-in curves only)."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        
        if 'calibration_chart' not in data:
            return
        
        calibration_chart = data['calibration_chart']
        
        # Only generate new points for built-in curve types
        built_in_curves = self.get_pedal_curves(pedal)
        if curve_type in built_in_curves:
            new_points = []
            
            logger.info(f"Generating {curve_type} curve for {pedal}")
            
            import math
            
            # Universal curves (available for all pedals)
            if curve_type == "Linear (Default)":
                # Linear curve: y = x
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = x  # Linear mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Progressive":
                # Progressive curve: starts slow, builds progressively
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    # Cubic curve for progressive response
                    y = ((x / 100) ** 3) * 100
                    new_points.append(QPointF(x, y))
            
            # Brake-specific curves
            elif curve_type == "Trail Brake":
                # Trail Brake curve: linear start, then aggressive, perfect for trail braking
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    if x <= 50:
                        # Linear first half for gentle braking
                        y = x
                    else:
                        # Exponential second half for trail braking control
                        normalized = (x - 50) / 50  # 0-1 range for second half
                        y = 50 + (normalized ** 2) * 50
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Threshold":
                # Threshold braking: sharp initial response for threshold braking
                for i in range(5):
                    x = i * 25
                    if x == 0:
                        y = 0
                    elif x <= 25:
                        # Quick initial rise
                        y = (x / 25) * 40
                    else:
                        # Linear after threshold
                        y = 40 + ((x - 25) / 75) * 60
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Endurance":
                # Endurance braking: consistent pressure for long stints
                for i in range(5):
                    x = i * 25
                    # Gentle S-curve for consistent control
                    normalized = x / 100
                    y = 100 * (3 * normalized**2 - 2 * normalized**3)
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Rally":
                # Rally braking: responsive for loose surfaces
                for i in range(5):
                    x = i * 25
                    # Quick response with controlled progression
                    y = ((x / 100) ** 0.6) * 100
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "ABS Friendly":
                # ABS Friendly: smooth modulation to work well with ABS
                for i in range(5):
                    x = i * 25
                    # Smooth exponential curve
                    y = ((x / 100) ** 1.8) * 100
                    new_points.append(QPointF(x, y))
            
            # Throttle-specific curves
            elif curve_type == "Turbo Lag":
                # Turbo Lag: mimics turbo spooling
                for i in range(5):
                    x = i * 25
                    if x <= 25:
                        # Minimal response during "lag"
                        y = ((x / 25) ** 2) * 15
                    else:
                        # Aggressive response after spool
                        normalized = (x - 25) / 75
                        y = 15 + (normalized ** 0.7) * 85
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "NA Engine":
                # NA Engine: naturally aspirated response
                for i in range(5):
                    x = i * 25
                    # Smooth linear-ish progression
                    y = ((x / 100) ** 0.8) * 100
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Track Mode":
                # Track Mode: precise control for racing
                for i in range(5):
                    x = i * 25
                    # Balanced curve with good control
                    y = ((x / 100) ** 1.2) * 100
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Feathering":
                # Feathering: precise low-speed control
                for i in range(5):
                    x = i * 25
                    if x <= 50:
                        # Very precise control in lower range
                        y = ((x / 50) ** 0.3) * 30
                    else:
                        # Normal progression in upper range
                        y = 30 + ((x - 50) / 50) * 70
                    new_points.append(QPointF(x, y))
            
            # Clutch-specific curves
            elif curve_type == "Quick Engage":
                # Quick Engage: fast clutch engagement
                for i in range(5):
                    x = i * 25
                    if x <= 40:
                        # Quick initial engagement
                        y = ((x / 40) ** 0.4) * 80
                    else:
                        # Complete engagement
                        y = 80 + ((x - 40) / 60) * 20
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Heel-Toe":
                # Heel-Toe: optimized for heel-toe downshifts
                for i in range(5):
                    x = i * 25
                    if x <= 20:
                        # Quick initial disengagement
                        y = 100 - ((x / 20) ** 0.5) * 30
                    elif x <= 80:
                        # Stable slip zone for heel-toe
                        y = 70 - ((x - 20) / 60) * 50
                    else:
                        # Final engagement
                        y = 20 - ((x - 80) / 20) * 20
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Bite Point Focus":
                # Bite Point Focus: emphasis on engagement point
                for i in range(5):
                    x = i * 25
                    if x <= 60:
                        # Gradual approach to bite point
                        y = ((x / 60) ** 0.3) * 50
                    else:
                        # Sharp engagement after bite point
                        y = 50 + ((x - 60) / 40) * 50
                    new_points.append(QPointF(x, y))
            
            # Update the chart with the new points
            calibration_chart.set_points(new_points)
            
            # Update stored points
            data['points'] = new_points.copy()
            
            # Update curve type selector to match
            if 'curve_type_selector' in data:
                data['curve_type_selector'].setCurrentText(curve_type)
            
            logger.info(f"Generated {len(new_points)} points for {curve_type} curve")
        else:
            logger.warning(f"Unknown curve type: {curve_type}")
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def adjust_min_deadzone(self, pedal: str, delta: int):
        """Adjust the minimum deadzone percentage."""
        data = self._pedal_data[pedal]
        current_min_deadzone = data.get('min_deadzone', 0)
        current_max_deadzone = data.get('max_deadzone', 0)
        
        # Calculate new value ensuring it doesn't exceed 50% and total doesn't exceed 80%
        new_min_deadzone = max(0, min(current_min_deadzone + delta, 50))
        
        # Ensure total deadzone doesn't exceed 80% of range
        if new_min_deadzone + current_max_deadzone > 80:
            new_min_deadzone = 80 - current_max_deadzone
        
        # Only update if value changed
        if new_min_deadzone != current_min_deadzone:
            data['min_deadzone'] = new_min_deadzone
            data['min_deadzone_value'].setText(f"{new_min_deadzone}%")
            
            # Update visualization on the chart
            if 'calibration_chart' in data:
                data['calibration_chart'].set_deadzones(new_min_deadzone, current_max_deadzone)
            
            # Signal that calibration has been updated
            self.calibration_updated.emit(pedal)
    
    def adjust_max_deadzone(self, pedal: str, delta: int):
        """Adjust the maximum deadzone percentage."""
        data = self._pedal_data[pedal]
        current_min_deadzone = data.get('min_deadzone', 0)
        current_max_deadzone = data.get('max_deadzone', 0)
        
        # Calculate new value ensuring it doesn't exceed 50% and total doesn't exceed 80%
        new_max_deadzone = max(0, min(current_max_deadzone + delta, 50))
        
        # Ensure total deadzone doesn't exceed 80% of range
        if current_min_deadzone + new_max_deadzone > 80:
            new_max_deadzone = 80 - current_min_deadzone
        
        # Only update if value changed
        if new_max_deadzone != current_max_deadzone:
            data['max_deadzone'] = new_max_deadzone
            data['max_deadzone_value'].setText(f"{new_max_deadzone}%")
            
            # Update visualization on the chart
            if 'calibration_chart' in data:
                data['calibration_chart'].set_deadzones(current_min_deadzone, new_max_deadzone)
            
            # Signal that calibration has been updated
            self.calibration_updated.emit(pedal)
    
    def save_custom_curve(self, pedal: str, name: str):
        """Save the current curve as a custom curve."""
        if not name.strip():
            self.show_message("Error", "Please enter a curve name")
            return
        
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            # Get current points from the chart
            points = data['calibration_chart'].get_points()
            
            # Save to hardware if available
            if hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'hardware'):
                try:
                    curve_data = {
                        'points': [(p.x(), p.y()) for p in points],
                        'curve_type': name
                    }
                    self.app_instance.hardware.save_custom_curve(pedal, name, curve_data)
                    self.show_message("Success", f"Curve '{name}' saved successfully")
                    
                    # Clear the name input field
                    if 'curve_name_input' in data:
                        data['curve_name_input'].clear()
                    
                    # Refresh the curve list to show the new curve
                    self.refresh_curve_lists()
                    
                    # Select the newly saved curve
                    if 'curve_type_selector' in data:
                        data['curve_type_selector'].setCurrentText(name)
                    
                except Exception as e:
                    self.show_message("Error", f"Failed to save curve: {e}")
            else:
                self.show_message("Error", "Hardware not available")
    
    def load_custom_curve(self, pedal: str, curve_name: str):
        """Load a custom curve."""
        if not curve_name or curve_name == "Loading...":
            return
        
        data = self._pedal_data[pedal]
        if hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'hardware'):
            try:
                curve_data = self.app_instance.hardware.load_custom_curve(pedal, curve_name)
                if curve_data and 'points' in curve_data:
                    # Convert points to QPointF objects
                    new_points = [QPointF(x, y) for x, y in curve_data['points']]
                    
                    # Update the chart with the loaded points
                    if 'calibration_chart' in data:
                        data['calibration_chart'].set_points(new_points)
                    
                    # Update stored points
                    data['points'] = new_points.copy()
                    
                    # Signal that calibration has changed
                    self.calibration_updated.emit(pedal)
                else:
                    self.show_message("Error", f"Could not load curve data for '{curve_name}'")
            except Exception as e:
                self.show_message("Error", f"Failed to load curve: {e}")
        else:
            self.show_message("Error", "Hardware not available")
    
    def delete_custom_curve(self, pedal: str, curve_name: str):
        """Delete a custom curve."""
        if not curve_name or curve_name == "Loading...":
            return
        
        if hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'hardware'):
            try:
                self.app_instance.hardware.delete_custom_curve(pedal, curve_name)
                self.show_message("Success", f"Curve '{curve_name}' deleted successfully")
                
                # Switch to Linear curve after deletion
                data = self._pedal_data[pedal]
                if 'curve_type_selector' in data:
                    data['curve_type_selector'].setCurrentText("Linear (Default)")
                
                # Apply Linear curve
                self.change_response_curve(pedal, "Linear (Default)")
                
                # Refresh the curve list to remove the deleted curve
                self.refresh_curve_lists()
                
            except Exception as e:
                self.show_message("Error", f"Failed to delete curve: {e}")
        else:
            self.show_message("Error", "Hardware not available")
    
    def refresh_curve_lists(self):
        """Refresh the curve lists for all pedals."""
        try:
            # Update curve type dropdowns for all pedals
            for pedal in ['throttle', 'brake', 'clutch']:
                if pedal not in self._pedal_data:
                    continue
                    
                data = self._pedal_data[pedal]
                if 'curve_type_selector' not in data:
                    continue
                
                curve_type_selector = data['curve_type_selector']
                
                # Get pedal-specific built-in curves
                built_in_curves = self.get_pedal_curves(pedal)
                
                # Save current selection
                current_selection = curve_type_selector.currentText()
                
                # Block signals to prevent unwanted callbacks during refresh
                curve_type_selector.blockSignals(True)
                
                # Clear existing items
                curve_type_selector.clear()
                
                # Add built-in curves first
                curve_type_selector.addItems(built_in_curves)
                
                # Get saved curves from hardware interface
                saved_curves = []
                if hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'hardware'):
                    hardware = self.app_instance.hardware
                    try:
                        if hasattr(hardware, 'list_available_curves'):
                            saved_curves = hardware.list_available_curves(pedal)
                    except Exception as curve_error:
                        logger.error(f"Error getting saved curves for {pedal}: {curve_error}")
                
                # Add saved curves to the dropdown
                if saved_curves:
                    # Add separator (visual divider)
                    curve_type_selector.addItem("─── Saved Curves ───")
                    
                    # Add each saved curve
                    for curve_name in sorted(saved_curves):
                        if curve_name not in built_in_curves:  # Don't duplicate built-in curves
                            curve_type_selector.addItem(curve_name)
                
                # Restore selection if possible
                if current_selection:
                    index = curve_type_selector.findText(current_selection)
                    if index >= 0:
                        curve_type_selector.setCurrentIndex(index)
                    else:
                        curve_type_selector.setCurrentText("Linear (Default)")  # Default fallback
                else:
                    curve_type_selector.setCurrentText("Linear (Default)")  # Default
                
                # Unblock signals
                curve_type_selector.blockSignals(False)
                
                logger.debug(f"Refreshed curve type selector for {pedal}: {len(built_in_curves)} built-in + {len(saved_curves)} saved curves")
            
            logger.info("Successfully refreshed curve lists for all pedals")
            
        except Exception as e:
            logger.error(f"Error refreshing curve lists: {e}")
            # Don't show error to user since this is a background operation
    
    def get_calibration_points(self, pedal: str):
        """Get the calibration points for a pedal."""
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            return data['calibration_chart'].get_points()
        return []
    
    def set_calibration_points(self, pedal: str, points: list):
        """Set the calibration points for a pedal."""
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            data['calibration_chart'].set_points(points)
    
    def set_curve_type(self, pedal: str, curve_type: str):
        """Set the curve type for a pedal."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        if 'curve_type_selector' in data:
            data['curve_type_selector'].setCurrentText(curve_type)
    
    def get_curve_type(self, pedal: str):
        """Get the curve type for a pedal."""
        data = self._pedal_data[pedal]
        return data.get('curve_type', 'Linear')
    
    def _check_authentication_required(self, feature_name: str) -> bool:
        """
        Check if authentication is required for a feature and handle login flow.
        
        Args:
            feature_name: Name of the feature requiring authentication
            
        Returns:
            True if user is authenticated, False if access should be blocked
        """
        try:
            from ..database import supabase
            is_authenticated = supabase.is_authenticated()
            
            if is_authenticated:
                logger.info(f"{feature_name}: User is authenticated, allowing access")
                return True
            else:
                logger.warning(f"{feature_name}: User not authenticated, blocking access")
                return False
                
        except Exception as auth_error:
            logger.error(f"{feature_name}: Authentication check failed: {auth_error}")
            # For critical features like Race Coach, block access on auth errors
            return False
    
    def get_calibration_range(self, pedal: str) -> tuple:
        """Get the min/max calibration range for a pedal."""
        data = self._pedal_data[pedal]
        return (data['min_value'], data['max_value'])
    
    def set_calibration_range(self, pedal: str, min_val: int, max_val: int):
        """Set the min/max calibration range for a pedal."""
        data = self._pedal_data[pedal]
        data['min_value'] = min_val
        data['max_value'] = max_val
        if 'min_label' in data:
            data['min_label'].setText(f"Min: {min_val}")
        if 'max_label' in data:
            data['max_label'].setText(f"Max: {max_val}")
        
        # Reset deadzone values when changing min/max
        data['min_deadzone'] = 0
        data['max_deadzone'] = 0
        if 'min_deadzone_value' in data:
            data['min_deadzone_value'].setText("0%")
        if 'max_deadzone_value' in data:
            data['max_deadzone_value'].setText("0%")
        
        # Update chart visualization
        if 'calibration_chart' in data:
            data['calibration_chart'].set_deadzones(0, 0)
            
        self.calibration_updated.emit(pedal)
    
    def set_pedal_available(self, pedal: str, available: bool):
        """Set whether a pedal is available."""
        pedal_key = pedal.lower()
        if pedal_key in self.pedal_groups:
            self.pedal_groups[pedal_key].setEnabled(available)
    
    # Delegate methods - these forward calls to the main application instance
    def show_profile_manager(self):
        """Show the pedal profile manager dialog."""
        if hasattr(self, 'app_instance') and self.app_instance:
            return self.app_instance.show_profile_manager()
        else:
            QMessageBox.warning(self, "Error", "Profile manager not available")
    
    def save_current_profile(self):
        """Save current settings as a profile."""
        if hasattr(self, 'app_instance') and self.app_instance:
            return self.app_instance.show_profile_manager()  # Same as show_profile_manager
        else:
            QMessageBox.warning(self, "Error", "Profile manager not available")
    
    def toggle_supabase(self, enabled):
        """Toggle Supabase connection."""
        try:
            from ..config import config
            config.set('supabase.enabled', enabled)
            logger.info(f"Supabase enabled: {enabled}")
            if hasattr(self, 'supabase_enabled_action'):
                self.supabase_enabled_action.setChecked(enabled)
        except Exception as e:
            logger.error(f"Error toggling Supabase: {e}")
            QMessageBox.warning(self, "Error", f"Failed to toggle Supabase: {str(e)}")
    
    def configure_supabase(self):
        """Configure Supabase credentials."""
        QMessageBox.information(self, "Configuration", "Supabase configuration dialog would open here")
    
    def show_login_dialog(self):
        """Show the login dialog."""
        try:
            from ..auth import LoginDialog
            dialog = LoginDialog(self, self.oauth_handler)
            dialog.exec()
            # Update auth state after dialog closes
            QTimer.singleShot(100, self.update_auth_state)
        except Exception as e:
            logger.error(f"Error showing login dialog: {e}")
            QMessageBox.warning(self, "Error", f"Could not open login dialog: {str(e)}")
    
    def show_signup_dialog(self):
        """Show the signup dialog."""
        try:
            from ..auth import SignupDialog
            dialog = SignupDialog(self, self.oauth_handler)
            dialog.exec()
            # Update auth state after dialog closes
            QTimer.singleShot(100, self.update_auth_state)
        except Exception as e:
            logger.error(f"Error showing signup dialog: {e}")
            QMessageBox.warning(self, "Error", f"Could not open signup dialog: {str(e)}")
    
    def handle_logout(self):
        """Handle user logout."""
        try:
            from ..database import supabase
            supabase.sign_out()
            logger.info("User logged out")
            self.update_auth_state()
            
            # Navigate back to the main pedal configuration page
            self.open_pedal_config()
            
            QMessageBox.information(self, "Logout", "You have been logged out successfully")
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            QMessageBox.warning(self, "Error", f"Error during logout: {str(e)}")
    
    def open_account_settings(self):
        """Open account settings page."""
        try:
            from ..database import supabase
            if not supabase.is_authenticated():
                QMessageBox.warning(self, "Authentication Required", "Please log in to access account settings.")
                return
            
            # Get current user ID for tracking user changes
            current_user = supabase.get_user()
            if not current_user or not current_user.user:
                QMessageBox.warning(self, "Authentication Error", "Unable to get user information.")
                return
            current_user_id = current_user.user.id
            
            # Check if Account page already exists in stacked widget
            account_index = -1
            existing_account_page = None
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if hasattr(widget, '__class__') and 'AccountPage' in widget.__class__.__name__:
                    account_index = i
                    existing_account_page = widget
                    break
            
            if account_index >= 0 and existing_account_page:
                # Check if the user has changed since the account page was created
                should_refresh = True
                if hasattr(existing_account_page, 'user_data') and existing_account_page.user_data:
                    existing_user_id = existing_account_page.user_data.get('user_id')
                    if existing_user_id == current_user_id:
                        should_refresh = False  # Same user, no need to refresh
                
                if should_refresh:
                    logger.info(f"User changed, refreshing account page data (previous: {existing_account_page.user_data.get('user_id') if existing_account_page.user_data else 'None'}, current: {current_user_id})")
                    # Force refresh the user data for the new user
                    try:
                        existing_account_page.load_user_data()
                    except Exception as refresh_error:
                        logger.error(f"Error refreshing account page data: {refresh_error}")
                        # If refresh fails, recreate the account page for safety
                        logger.info("Recreating account page due to refresh failure")
                        self.stacked_widget.removeWidget(existing_account_page)
                        existing_account_page.deleteLater()
                        # Clear account_index to force recreation below
                        account_index = -1
                else:
                    logger.info(f"Same user, reusing existing account page at index {account_index}")
                
                self.stacked_widget.setCurrentIndex(account_index)
                # Update menu action states
                self.pedal_config_action.setChecked(False)
                if hasattr(self, 'race_coach_action'):
                    self.race_coach_action.setChecked(False)
                if hasattr(self, 'race_pass_action'):
                    self.race_pass_action.setChecked(False)
                if hasattr(self, 'community_action'):
                    self.community_action.setChecked(False)
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                return
            
            # Import and create the standalone account page
            from .standalone_account_page import AccountPage
            
            # Create account page widget
            account_widget = AccountPage(self)
            
            # Add to stacked widget
            account_index = self.stacked_widget.addWidget(account_widget)
            self.stacked_widget.setCurrentIndex(account_index)
            
            # Update menu states
            self.pedal_config_action.setChecked(False)
            if hasattr(self, 'race_coach_action'):
                self.race_coach_action.setChecked(False)
            if hasattr(self, 'race_pass_action'):
                self.race_pass_action.setChecked(False)
            if hasattr(self, 'community_action'):
                self.community_action.setChecked(False)
            
            # Hide calibration buttons since they're not relevant for account page
            self.calibration_wizard_btn.setVisible(False)
            
            logger.info(f"✅ Account page created and added at index {account_index}")
            
        except Exception as e:
            logger.error(f"Error opening account settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open account settings: {str(e)}")
    
    def check_for_updates(self):
        """Check for application updates."""
        try:
            # Get the updater from the app instance
            if hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'updater'):
                updater = self.app_instance.updater
                if updater:
                    # Perform a manual update check (not silent, so user sees feedback)
                    updater.check_for_updates(silent=False, manual_check=True)
                else:
                    QMessageBox.warning(self, "Update Check", "Update checker is not available.")
            else:
                QMessageBox.warning(self, "Update Check", "Update functionality is not initialized.")
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            QMessageBox.critical(self, "Update Check Failed", f"An error occurred while checking for updates:\n{str(e)}")
    
    def show_update_notification(self, version):
        """Show update notification in the UI."""
        try:
            if hasattr(self, 'update_notification'):
                self.update_notification.setText(f"📦 Update available: v{version} - Click File > Check for Updates to install")
                self.update_notification.setVisible(True)
                logger.info(f"Showing update notification for version {version}")
            else:
                logger.warning("Update notification label not found")
        except Exception as e:
            logger.error(f"Error showing update notification: {e}")
    
    def open_pedal_config(self):
        """Open the pedal configuration screen."""
        self.stacked_widget.setCurrentIndex(0)  # Assuming pedal config is at index 0
        self.pedal_config_action.setChecked(True)
        self.race_coach_action.setChecked(False)
        self.race_pass_action.setChecked(False)
        self.community_action.setChecked(False)
    
    def open_race_coach(self):
        """Open the Race Coach screen - REQUIRES AUTHENTICATION AND PASSWORD."""
        logger.info("🏁 Race Coach access requested")
        
        # PASSWORD PROTECTION CHECK FIRST
        try:
            from .auth_dialogs import PasswordDialog
            password_dialog = PasswordDialog(self, "Race Coach")
            if password_dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info("Race Coach access denied - incorrect password")
                return
            logger.info("✅ Race Coach password validated successfully")
        except Exception as e:
            logger.error(f"Error showing password dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not verify password: {str(e)}")
            return
        
        # STRICT AUTHENTICATION REQUIREMENT
        is_authenticated = self._check_authentication_required("Race Coach")
        
        if not is_authenticated:
            # Create a custom message box with login button
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("🏁 Race Coach - Login Required")
            msg_box.setText(
                "🔐 You need to be logged in to access the Race Coach feature.\n\n"
                "🚀 Race Coach provides:\n"
                "   • Real-time telemetry analysis\n"
                "   • Lap time improvements\n"
                "   • Cloud sync for session data\n"
                "   • Performance tracking\n\n"
                "Please log in to continue."
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # Add buttons
            login_button = msg_box.addButton("🔑 Login Now", QMessageBox.ButtonRole.ActionRole)
            signup_button = msg_box.addButton("📝 Sign Up", QMessageBox.ButtonRole.ActionRole)
            cancel_button = msg_box.addButton("❌ Cancel", QMessageBox.ButtonRole.RejectRole)
            
            # Set default button
            msg_box.setDefaultButton(login_button)
            
            result = msg_box.exec()
            
            # Check which button was clicked
            if msg_box.clickedButton() == login_button:
                logger.info("User chose to login for Race Coach access")
                self.show_login_dialog()
                
                # Check again after login attempt
                try:
                    if supabase.is_authenticated():
                        logger.info("User successfully logged in, retrying Race Coach access")
                        # Retry opening Race Coach now that user is logged in
                        QTimer.singleShot(500, self.open_race_coach)  # Small delay to ensure auth state is updated
                        return
                except Exception as auth_check_error:
                    logger.warning(f"Could not verify authentication after login: {auth_check_error}")
                    
            elif msg_box.clickedButton() == signup_button:
                logger.info("User chose to sign up for Race Coach access")
                self.show_signup_dialog()
                
                # Check again after signup attempt
                try:
                    if supabase.is_authenticated():
                        logger.info("User successfully signed up, retrying Race Coach access")
                        # Retry opening Race Coach now that user is logged in
                        QTimer.singleShot(500, self.open_race_coach)  # Small delay to ensure auth state is updated
                        return
                except Exception as auth_check_error:
                    logger.warning(f"Could not verify authentication after signup: {auth_check_error}")
            
            logger.info("Race Coach access blocked - user not authenticated")
            return
        
        try:
            # Initialize gamification overview since we're accessing Race Coach
            self.initialize_gamification_overview()
            
            # Try to import and initialize the Race Coach module directly
            try:
                # First verify that numpy is available
                try:
                    import numpy
                    logger.info(f"Found numpy version: {numpy.__version__}")
                except ImportError as e:
                    logger.error(f"Race Coach requires numpy but it's not available: {e}")
                    QMessageBox.critical(
                        self,
                        "Missing Dependency",
                        "The Race Coach feature requires numpy which is not installed or is missing.\n\n"
                        "Error details: " + str(e) + "\n\n"
                        "Please reinstall the application to fix this issue."
                    )
                    return

                # Try to verify the race_coach.db exists
                db_path = "race_coach.db"
                if not os.path.exists(db_path):
                    alternative_paths = [
                        os.path.join(os.path.dirname(sys.executable), "race_coach.db"),
                        os.path.expanduser("~/Documents/TrackPro/race_coach.db")
                    ]
                    
                    found = False
                    for alt_path in alternative_paths:
                        if os.path.exists(alt_path):
                            logger.info(f"Found race_coach.db at alternative location: {alt_path}")
                            db_path = alt_path
                            found = True
                            break
                    
                    if not found:
                        logger.warning("race_coach.db not found, will attempt to create it")
                
                # Import Race Coach components
                from trackpro.race_coach import RaceCoachWidget, create_race_coach_widget
                logger.info("Imported Race Coach modules successfully")
                
                # Check if Race Coach widget already exists in stacked widget
                race_coach_index = -1
                for i in range(self.stacked_widget.count()):
                    widget = self.stacked_widget.widget(i)
                    if isinstance(widget, RaceCoachWidget):
                        race_coach_index = i
                        break
                
                if race_coach_index >= 0:
                    logger.info(f"Race Coach screen already exists at index {race_coach_index}, switching to it")
                    self.stacked_widget.setCurrentIndex(race_coach_index)
                    # Update menu action states
                    self.race_coach_action.setChecked(True)
                    self.pedal_config_action.setChecked(False)
                    if hasattr(self, 'race_pass_action'):
                        self.race_pass_action.setChecked(False)
                    if hasattr(self, 'community_action'):
                        self.community_action.setChecked(False)
                    # Hide calibration buttons
                    self.calibration_wizard_btn.setVisible(False)
                    return
                
                # Create and add the Race Coach widget if it doesn't exist
                # Use the factory function for better error handling
                race_coach_widget = create_race_coach_widget(self)
                if race_coach_widget is None:
                    logger.error("Failed to create the Race Coach widget")
                    QMessageBox.critical(
                        self,
                        "Component Error",
                        "Failed to initialize the Race Coach component. Check logs for more details."
                    )
                    return
                    
                # Add to stacked widget and switch to it
                race_coach_index = self.stacked_widget.addWidget(race_coach_widget)
                # Switch to the Race Coach screen
                self.stacked_widget.setCurrentIndex(race_coach_index)
                # Update menu action states
                self.race_coach_action.setChecked(True)
                self.pedal_config_action.setChecked(False)
                if hasattr(self, 'race_pass_action'):
                    self.race_pass_action.setChecked(False)
                if hasattr(self, 'community_action'):
                    self.community_action.setChecked(False)
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                logger.info(f"Race Coach screen added at index {race_coach_index} and switched to")
                
            except ImportError as import_error:
                logger.error(f"Failed to import Race Coach modules: {import_error}")
                # Provide more detailed error message to help troubleshoot
                error_module = str(import_error).split("'")[-2] if "'" in str(import_error) else str(import_error)
                QMessageBox.critical(
                    self,
                    "Missing Dependency",
                    f"The Race Coach feature requires dependencies that are missing.\n\n"
                    f"Missing module: {error_module}\n\n"
                    "Please reinstall the application to ensure all components are included."
                )
            except Exception as e:
                logger.error(f"Error initializing Race Coach: {e}")
                logger.error(traceback.format_exc())
                QMessageBox.critical(self, "Component Error", f"Failed to initialize Race Coach: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error opening Race Coach: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Unexpected error: {str(e)}")
    
    def open_race_pass(self):
        """Open the Race Pass screen - REQUIRES PASSWORD."""
        logger.info("🏁 Race Pass access requested")
        
        # PASSWORD PROTECTION CHECK FIRST
        try:
            from .auth_dialogs import PasswordDialog
            password_dialog = PasswordDialog(self, "Race Pass")
            if password_dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info("Race Pass access denied - incorrect password")
                return
            logger.info("✅ Race Pass password validated successfully")
        except Exception as e:
            logger.error(f"Error showing password dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not verify password: {str(e)}")
            return
        
        # Import here to avoid circular imports
        from ..database import supabase
        
        # Check authentication with error handling for network issues
        try:
            is_authenticated = supabase.is_authenticated()
        except Exception as auth_error:
            logger.warning(f"Race Pass: Could not check authentication due to network error: {auth_error}")
            # Allow access in offline mode
            is_authenticated = True
        
        if not is_authenticated:
            # Create a custom message box with login button
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Login Required")
            msg_box.setText("You need to be logged in to access the Race Pass feature.")
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # Add a button to open login dialog
            login_button = msg_box.addButton("Login Now", QMessageBox.ButtonRole.ActionRole)
            cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)
            
            msg_box.exec()
            
            # Check which button was clicked
            if msg_box.clickedButton() == login_button:
                self.show_login_dialog()
            
            logger.info("Race Pass access attempted without login")
            return
        
        try:
            # Import Race Pass components
            from trackpro.gamification.ui.race_pass_view import RacePassViewWidget
            logger.info("Imported Race Pass modules successfully")
            
            # Check if Race Pass widget already exists in stacked widget
            race_pass_index = -1
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if isinstance(widget, RacePassViewWidget):
                    race_pass_index = i
                    break
            
            if race_pass_index >= 0:
                logger.info(f"Race Pass screen already exists at index {race_pass_index}, switching to it")
                self.stacked_widget.setCurrentIndex(race_pass_index)
                # Update menu action states
                self.race_pass_action.setChecked(True)
                self.pedal_config_action.setChecked(False)
                if hasattr(self, 'race_coach_action'):
                    self.race_coach_action.setChecked(False)
                if hasattr(self, 'community_action'):
                    self.community_action.setChecked(False)
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                return
            
            # Create and add the Race Pass widget if it doesn't exist
            race_pass_widget = RacePassViewWidget(self)
            if race_pass_widget is None:
                logger.error("Failed to create the Race Pass widget")
                QMessageBox.critical(
                    self,
                    "Component Error",
                    "Failed to initialize the Race Pass component. Check logs for more details."
                )
                return
                
            # Add to stacked widget and switch to it
            race_pass_index = self.stacked_widget.addWidget(race_pass_widget)
            # Switch to the Race Pass screen
            self.stacked_widget.setCurrentIndex(race_pass_index)
            # Update menu action states
            self.race_pass_action.setChecked(True)
            self.pedal_config_action.setChecked(False)
            if hasattr(self, 'race_coach_action'):
                self.race_coach_action.setChecked(False)
            if hasattr(self, 'community_action'):
                self.community_action.setChecked(False)
            # Hide calibration buttons
            self.calibration_wizard_btn.setVisible(False)
            logger.info(f"Race Pass screen added at index {race_pass_index} and switched to")
            
        except ImportError as import_error:
            logger.error(f"Failed to import Race Pass modules: {import_error}")
            QMessageBox.critical(
                self,
                "Missing Dependency",
                f"The Race Pass feature requires dependencies that are missing.\n\n"
                f"Missing module: {str(import_error)}\n\n"
                "Please check that all gamification components are properly installed."
            )
        except Exception as e:
            logger.error(f"Error initializing Race Pass: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Component Error", f"Failed to initialize Race Pass: {str(e)}")
    
    def open_community_interface(self):
        """Open the main community interface in the stacked widget - REQUIRES PASSWORD."""
        logger.info("🌐 Community access requested")
        
        # PASSWORD PROTECTION CHECK FIRST
        try:
            from .auth_dialogs import PasswordDialog
            password_dialog = PasswordDialog(self, "Community")
            if password_dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info("Community access denied - incorrect password")
                return
            logger.info("✅ Community password validated successfully")
        except Exception as e:
            logger.error(f"Error showing password dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not verify password: {str(e)}")
            return
        
        # Import here to avoid circular imports
        from ..database import supabase
        
        # Prevent opening if not authenticated
        if not supabase.is_authenticated():
            self.show_login_dialog()
            # After login attempt, re-check authentication status
            if not supabase.is_authenticated():
                # If still not authenticated, show a message and switch to a default tab
                QMessageBox.warning(self, "Login Required", "You must be logged in to access the community.")
                if hasattr(self, 'community_action'):
                    self.community_action.setChecked(False)
                # Ensure pedal config action is checked
                if hasattr(self, 'pedal_config_action'):
                    self.pedal_config_action.setChecked(True)
                self.open_pedal_config()
                return

        # Check if community widget already exists
        if hasattr(self, 'community_widget') and self.community_widget:
            # If it exists, just switch to it
            self.stacked_widget.setCurrentWidget(self.community_widget)
            return

        # First check if user is authenticated for some features
        is_authenticated = False  # Default to false for safety
        try:
            # Import the global supabase instance that has the correct methods
            from ..database import supabase_client
            if hasattr(supabase_client, 'supabase') and supabase_client.supabase:
                is_authenticated = supabase_client.supabase.is_authenticated()
        except Exception as e:
            logger.warning(f"Could not check authentication status: {e}")
            is_authenticated = False
            
        try:
            # Check if Community widget already exists in stacked widget
            community_index = -1
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if hasattr(widget, '__class__') and 'Community' in widget.__class__.__name__:
                    community_index = i
                    break
            
            if community_index >= 0:
                logger.info(f"Community screen already exists at index {community_index}, switching to it")
                self.stacked_widget.setCurrentIndex(community_index)
                # Update menu action states
                self.community_action.setChecked(True)
                self.pedal_config_action.setChecked(False)
                if hasattr(self, 'race_coach_action'):
                    self.race_coach_action.setChecked(False)
                if hasattr(self, 'race_pass_action'):
                    self.race_pass_action.setChecked(False)
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                return
            
            # Create or reuse the integrated community widget
            try:
                # Check if background community widget already exists
                if hasattr(self, 'background_community_widget') and self.background_community_widget:
                    print("♻️ Reusing existing background community widget for UI")
                    community_widget = self.background_community_widget
                    
                    # Ensure it's parented correctly for UI display and reset geometry
                    community_widget.setParent(self)
                    community_widget.setVisible(True)
                    community_widget.show()
                    community_widget.setGeometry(0, 0, 800, 600)  # Reset to normal size
                else:
                    print("📱 Creating new community widget for UI")
                    from trackpro.community.community_main_widget import CommunityMainWidget
                    from trackpro.database.supabase_client import get_supabase_client
                    
                    # Get the Supabase client
                    supabase_client = get_supabase_client()
                    
                    # Create community widget with Supabase client
                    community_widget = CommunityMainWidget(parent=self, supabase_client=supabase_client)
                
                # Set up managers and user ID if available
                if is_authenticated:
                    try:
                        managers = self.get_community_managers()
                        user_id = self.get_current_user_id()
                        community_widget.set_managers(managers)
                        community_widget.set_user_id(user_id)
                        logger.info("Community widget configured with authenticated user data")
                    except Exception as e:
                        logger.warning(f"Could not set up community managers: {e}")
                
                # Connect authentication state changes to the community widget
                self.auth_state_changed.connect(community_widget.handle_auth_state_change)
                logger.info("Connected community widget to authentication state changes")
                
                # Store reference to community widget for later use
                self.community_widget = community_widget
                
                # Connect notification signals (only if not already connected)
                if hasattr(community_widget, 'notification_count_changed'):
                    # Check if we're reusing the background widget (signals already connected)
                    if hasattr(self, 'background_community_widget') and community_widget == self.background_community_widget:
                        print("🔗 Signals already connected for background widget")
                        # Reconnect authentication signals since parent changed
                        try:
                            self.auth_state_changed.disconnect(community_widget.handle_auth_state_change)
                        except:
                            pass  # Might not be connected
                        self.auth_state_changed.connect(community_widget.handle_auth_state_change)
                    else:
                        print("🔗 Connecting notification signals for new widget")
                        community_widget.notification_count_changed.connect(self.update_community_notification_badge)
                        
                # Add to stacked widget and switch to it
                community_index = self.stacked_widget.addWidget(community_widget)
                
                # Switch to the Community screen
                self.stacked_widget.setCurrentIndex(community_index)
                
                # Update menu action states
                self.community_action.setChecked(True)
                self.pedal_config_action.setChecked(False)
                if hasattr(self, 'race_coach_action'):
                    self.race_coach_action.setChecked(False)
                if hasattr(self, 'race_pass_action'):
                    self.race_pass_action.setChecked(False)
                    
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                
                logger.info(f"Community screen added at index {community_index} and switched to")
                
            except ImportError as import_error:
                logger.error(f"Failed to import Community widget: {import_error}")
                QMessageBox.critical(
                    self,
                    "Missing Component",
                    f"The Community feature could not be loaded.\n\n"
                    f"Error: {import_error}\n\n"
                    "Please check that all community components are properly installed."
                )
            except Exception as e:
                logger.error(f"Error creating Community widget: {e}")
                QMessageBox.critical(self, "Component Error", f"Failed to initialize Community: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error opening Community: {e}")
            QMessageBox.critical(self, "Error", f"Unexpected error: {str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
                        <h2>TrackPro v1.5.4</h2>
        <p>Racing Telemetry System</p>
        <p>© 2024 Sim Coaches</p>
        <p>A professional racing telemetry and pedal calibration system.</p>
        """
        QMessageBox.about(self, "About TrackPro", about_text)
    
    def show_eye_tracking_settings(self):
        """Show eye tracking settings dialog - REQUIRES PASSWORD."""
        # PASSWORD PROTECTION CHECK FIRST
        try:
            from .auth_dialogs import PasswordDialog
            password_dialog = PasswordDialog(self, "Eye Tracking")
            if password_dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info("Eye tracking settings access denied - incorrect password")
                return
            logger.info("✅ Eye tracking password validated successfully")
        except Exception as e:
            logger.error(f"Error showing password dialog: {e}")
            QMessageBox.critical(self, "Error", f"Could not verify password: {str(e)}")
            return
        
        try:
            from .eye_tracking_settings import EyeTrackingSettingsDialog
            
            # Get eye tracking manager from race coach if available
            eye_tracking_manager = None
            if hasattr(self, 'race_coach_widget') and self.race_coach_widget:
                # Try to get the eye tracking manager from telemetry saver
                if hasattr(self.race_coach_widget, 'telemetry_saver') and self.race_coach_widget.telemetry_saver:
                    eye_tracking_manager = self.race_coach_widget.telemetry_saver.eye_tracking_manager
            
            # If no eye tracking manager exists (e.g., eye tracking is disabled), 
            # create a temporary one for the settings dialog
            if not eye_tracking_manager:
                try:
                    from trackpro.race_coach.eye_tracking_manager import EyeTrackingManager
                    # Create a temporary eye tracking manager for settings access
                    # This allows users to enable and configure eye tracking even when it's disabled
                    eye_tracking_manager = EyeTrackingManager()
                    logger.info("Created temporary eye tracking manager for settings dialog")
                except Exception as e:
                    logger.warning(f"Could not create temporary eye tracking manager: {e}")
                    eye_tracking_manager = None
            
            dialog = EyeTrackingSettingsDialog(self, eye_tracking_manager)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing eye tracking settings: {e}")
            QMessageBox.critical(self, "Error", f"Could not open eye tracking settings: {str(e)}")
    
    def show_track_map_overlay_settings(self):
        """Show track map overlay settings dialog."""
        try:
            from ..race_coach.ui.track_map_overlay_settings import TrackMapOverlaySettingsDialog
            from ..race_coach.track_map_overlay import TrackMapOverlayManager
            
            # Create persistent overlay manager if it doesn't exist
            if not self.track_map_overlay_manager:
                self.track_map_overlay_manager = TrackMapOverlayManager()
                logger.info("🗺️ Created persistent track map overlay manager")
            
            # Create and show dialog, passing our persistent manager
            dialog = TrackMapOverlaySettingsDialog(self)
            # Replace the dialog's manager with our persistent one
            dialog.overlay_manager = self.track_map_overlay_manager
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing track map overlay settings: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Could not open track map overlay settings: {str(e)}")
    
    def test_email_setup(self):
        """Test email configuration."""
        QMessageBox.information(self, "Email Test", "Email configuration test would run here")
    
    def optimize_performance(self):
        """Optimize application performance."""
        QMessageBox.information(self, "Performance", "Performance optimization would run here")
    
    def update_auth_state(self):
        """Update UI elements based on authentication state."""
        # Import here to avoid circular imports
        from ..database import supabase
        
        try:
            # Check authentication status with proper error handling
            try:
                is_authenticated = supabase.is_authenticated()
                if is_authenticated:
                    user_response = supabase.get_user()
                    # Extract the actual user object from the response
                    if user_response and hasattr(user_response, 'user') and user_response.user:
                        user = user_response.user
                    elif user_response and hasattr(user_response, 'id'):
                        # Some responses have the user data directly
                        user = user_response
                    else:
                        user = None
                        
                    # MANDATORY 2FA CHECK FOR AUTHENTICATED USERS - REMOVED
                    # This check is now handled by the login dialog to prevent double verification
                    # if user and hasattr(user, 'id'):
                    #     logger.info(f"User authenticated from saved session, checking 2FA status for user {user.id}")
                    #     if not self._check_and_handle_2fa_on_startup(user.id, getattr(user, 'email', 'User')):
                    #         # 2FA check failed, force logout
                    #         logger.warning("2FA verification failed on startup, logging out user")
                    #         try:
                    #             supabase.client.auth.sign_out()
                    #             is_authenticated = False
                    #             user = None
                    #             QMessageBox.warning(self, "Authentication Required", 
                    #                 "Phone verification is required to use TrackPro. You have been logged out.")
                    #         except Exception as logout_error:
                    #             logger.error(f"Error logging out user after failed 2FA: {logout_error}")
                else:
                    user = None
            except Exception as auth_error:
                logger.warning(f"Error checking authentication state: {auth_error}")
                is_authenticated = False
                user = None
                # Still continue with UI updates in offline mode
        
            logger.info(f"Updating auth state: authenticated={is_authenticated}")
            
            # Update authentication buttons state
            if hasattr(self, 'login_btn'):
                self.login_btn.setVisible(not is_authenticated)
            if hasattr(self, 'signup_btn'):
                self.signup_btn.setVisible(not is_authenticated)
            if hasattr(self, 'logout_btn'):
                self.logout_btn.setVisible(is_authenticated)
            if hasattr(self, 'account_btn'):
                self.account_btn.setVisible(is_authenticated)
            
            # Update status bar user info
            if is_authenticated and user:
                try:
                    user_email = user.email if hasattr(user, 'email') else "Authenticated User"
                    if hasattr(user, 'user_metadata') and user.user_metadata:
                        display_name = user.user_metadata.get('display_name') or user.user_metadata.get('name') or user_email
                    else:
                        display_name = user_email
                    
                    # Limit display name length
                    if len(display_name) > 30:
                        display_name = display_name[:27] + "..."
                        
                    self.user_label.setText(f"👤 {display_name}")
                    self.user_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 2px 8px; font-weight: bold;")
                    
                    # Show cloud sync enabled
                    self.cloud_sync_label.setText("☁️ Cloud sync enabled")
                    self.cloud_sync_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 2px 8px;")
                except Exception as user_info_error:
                    logger.warning(f"Error updating user info display: {user_info_error}")
                    self.user_label.setText("👤 Authenticated")
                    self.user_label.setStyleSheet("color: #4CAF50; font-size: 10px; padding: 2px 8px; font-weight: bold;")
                    self.cloud_sync_label.setText("☁️ Cloud sync enabled")
                    
                    # Create a minimal user representation for other components
                    class MinimalUser:
                        def __init__(self):
                            self.is_authenticated = True
                            self.id = "authenticated_user"
                            self.email = "user@example.com"
                    
                    user = MinimalUser()
            else:
                self.user_label.setText("Not logged in")
                self.user_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px 8px;")
                self.cloud_sync_label.setText("☁️ Sign in to enable cloud sync")
                self.cloud_sync_label.setStyleSheet("color: #3498db; cursor: pointer; font-size: 10px; padding: 2px 8px;")
                user = None
            
            # Emit auth state changed signal for other components
            self.auth_state_changed.emit(is_authenticated)
            
            # Update protected features availability
            self.update_protected_features(is_authenticated)
            
            # Update existing community widgets if they exist
            self.update_existing_community_widgets(user)
            
            # 🔧 NEW: Start global iRacing connection if authenticated and not already running
            if is_authenticated and not self.iracing_connection_active:
                logger.info("🚀 User authenticated - starting global iRacing connection for continuous telemetry saving...")
                self.start_global_iracing_connection()
            elif not is_authenticated and self.iracing_connection_active:
                logger.info("🛑 User logged out - stopping global iRacing connection")
                self.stop_global_iracing_connection()
                
        except Exception as e:
            logger.error(f"Error updating authentication state: {e}", exc_info=True)
    
    def _check_and_handle_2fa_on_startup(self, user_id, user_email="User"):
        """Check and handle 2FA verification for users authenticated from saved sessions.
        
        Args:
            user_id: The user's ID
            user_email: The user's email for display purposes
            
        Returns:
            bool: True if 2FA passed or not required, False if 2FA failed
        """
        try:
            # Check if Twilio is available
            try:
                from ..auth.twilio_service import twilio_service
                TWILIO_AVAILABLE = twilio_service and twilio_service.is_available()
            except ImportError:
                TWILIO_AVAILABLE = False
                
            # MANDATORY: Check if Twilio is available - if not, block access
            if not TWILIO_AVAILABLE:
                QMessageBox.critical(self, "2FA Service Required", 
                    "TrackPro requires SMS verification for security.\n\n"
                    "The SMS service is currently not configured or unavailable.\n"
                    "Please contact support to enable SMS verification.\n\n"
                    "Access is not allowed without phone verification capability.")
                logger.error(f"Access blocked for user {user_email} - Twilio service not available on startup")
                return False  # Block access entirely
            
            # Get user profile to check verification status
            from ..social import enhanced_user_manager
            profile_res = enhanced_user_manager.get_complete_user_profile(user_id)
            
            # The primary condition is whether the user's phone has been verified via Twilio.
            if profile_res and profile_res.get('twilio_verified'):
                # Phone is verified. Now, check if they have enabled 2FA for logins.
                if profile_res.get('is_2fa_enabled'):
                    phone_number = profile_res.get('phone_number')
                    if not phone_number:
                        QMessageBox.critical(self, "2FA Error", "2FA is enabled, but no phone number is on file. Please contact support.")
                        return False # Block login
                    
                    logger.info(f"User {user_email} has 2FA enabled. Sending verification code on startup.")
                    return self._send_2fa_code_and_verify_on_startup(phone_number, user_email)
                else:
                    # Phone is verified, but they haven't opted into 2FA for every login.
                    # This is fine, let them pass.
                    logger.info(f"User {user_email} has a verified phone but 2FA is not turned on. Allowing access.")
                    return True
            else:
                # This user has not verified their phone number. Force them to do so now.
                logger.info(f"User {user_email} has not verified their phone. Forcing verification process on startup.")
                return self._force_phone_verification_on_startup(user_id, user_email)
                
        except Exception as e:
            logger.error(f"Error checking 2FA status on startup: {e}", exc_info=True)
            QMessageBox.critical(self, "2FA Error", f"An error occurred while checking your security status: {e}")
            return False # Fail safe: if check fails, don't allow access.
    
    def _force_phone_verification_on_startup(self, user_id, user_email="User"):
        """Forces the user to complete phone verification on startup. This is not optional.
        
        Args:
            user_id: The user's ID
            user_email: The user's email for display purposes
            
        Returns:
            bool: True if verification is successful, False otherwise.
        """
        try:
            from ..auth.phone_verification_dialog import PhoneVerificationDialog
            from ..social import enhanced_user_manager

            QMessageBox.information(self, 
                "Account Security Update",
                "To enhance account security, all users are now required to verify a phone number.\n\n"
                "You will now be guided through the verification process. This is a one-time requirement."
            )
            
            # Loop to allow user to retry if they enter wrong number etc.
            while True:
                dialog = PhoneVerificationDialog(self, user_id)
                dialog.exec()
                
                # Re-check the profile to see if verification was successful
                profile = enhanced_user_manager.get_complete_user_profile(user_id)
                if profile and profile.get('twilio_verified'):
                    logger.info(f"User {user_id} successfully verified their phone number on startup.")
                    QMessageBox.information(self, "Verification Successful", "Your phone number has been successfully verified.")
                    
                    # Automatically enable 2FA for them upon first verification
                    try:
                        enhanced_user_manager.update_user_profile(user_id, {'is_2fa_enabled': True})
                        logger.info(f"Automatically enabled 2FA for user {user_id} after first-time verification on startup.")
                    except Exception as e:
                        logger.error(f"Failed to auto-enable 2FA for user {user_id}: {e}")

                    return True # Verification successful

                # If we are here, verification failed or was cancelled.
                reply = QMessageBox.critical(
                    self, "Verification Required",
                    "You must verify your phone number to continue. Without verification, you will be logged out.\n\n"
                    "Do you want to try again?",
                    QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Retry
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    logger.warning(f"User {user_id} cancelled the mandatory phone verification on startup. Will be logged out.")
                    return False # User chose to cancel, deny access.
                    
        except Exception as e:
            logger.error(f"Error in startup phone verification: {e}", exc_info=True)
            QMessageBox.critical(self, "Verification Error", f"An error occurred during phone verification: {e}")
            return False
    
    def _send_2fa_code_and_verify_on_startup(self, phone_number, user_email="User"):
        """Send 2FA code and prompt user for verification on startup.
        
        Args:
            phone_number: The phone number to send the code to
            user_email: User email for display purposes
            
        Returns:
            bool: True if verification successful, False otherwise
        """
        try:
            from ..auth.twilio_service import twilio_service
            if not twilio_service or not twilio_service.is_available():
                QMessageBox.critical(self, "2FA Error", 
                    "SMS 2FA is not available. Please contact support.")
                return False
            
            from ..auth.sms_verification_dialog import SMSVerificationDialog
            
            # Create and show the SMS verification dialog
            dialog = SMSVerificationDialog(self, phone_number)
            result = dialog.exec()
            
            # Return True if verification was successful
            return dialog.verification_successful
            
        except Exception as e:
            logger.error(f"Error in 2FA process on startup: {e}")
            QMessageBox.critical(self, "2FA Error", f"2FA verification failed: {str(e)}")
            return False

    def setup_early_notification_system(self):
        """Set up early notification system."""
        # This would contain the early notification setup logic
        pass
    
    def open_calibration_wizard(self):
        """Open the calibration wizard."""
        try:
            from ..pedals.calibration import CalibrationWizard
            
            # Check if hardware is available
            if not (hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'hardware')):
                QMessageBox.warning(self, "Error", "Hardware not available for calibration")
                return
                
            wizard = CalibrationWizard(self.app_instance.hardware, self)
            if wizard.exec() == QDialog.DialogCode.Accepted:
                results = wizard.get_results()
                self.on_calibration_wizard_completed(results)
        except ImportError:
            QMessageBox.warning(self, "Error", "Calibration wizard not available")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open calibration wizard: {str(e)}")
    

    
    def on_calibration_wizard_completed(self, results):
        """Handle calibration wizard completion."""
        try:
            # Apply the calibration results from the wizard
            for pedal, data in results.items():
                if pedal in ['throttle', 'brake', 'clutch']:
                    if 'min' in data and 'max' in data:
                        self.set_calibration_range(pedal, data['min'], data['max'])
                    if 'curve_points' in data:
                        self.set_calibration_points(pedal, data['curve_points'])
                    if 'curve_type' in data:
                        self.set_curve_type(pedal, data['curve_type'])
            
            QMessageBox.information(self, "Calibration Complete", "Calibration wizard completed successfully!")
        except Exception as e:
            logger.error(f"Error processing calibration wizard results: {e}")
            QMessageBox.warning(self, "Error", f"Error applying calibration results: {str(e)}")
    
    def _on_tab_changed(self, index):
        """Handle tab change events."""
        # Get the current widget to determine its type
        current_widget = self.stacked_widget.widget(index)
        widget_class_name = current_widget.__class__.__name__ if current_widget else "Unknown"
        
        # Reset all menu action states
        self.pedal_config_action.setChecked(False)
        if hasattr(self, 'race_coach_action'):
            self.race_coach_action.setChecked(False)
        if hasattr(self, 'race_pass_action'):
            self.race_pass_action.setChecked(False)
        if hasattr(self, 'community_action'):
            self.community_action.setChecked(False)
        
        # Update menu action states and calibration button visibility based on the current tab
        if index == 0:  # Pedal Config tab
            self.pedal_config_action.setChecked(True)
            self.calibration_wizard_btn.setVisible(True)
            
            # Send a hide event to other widgets if they exist
            for i in range(1, self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if hasattr(widget, 'hideEvent'):
                    try:
                        # Create a hide event
                        hide_event = QHideEvent()
                        # Call the widget's hideEvent method
                        widget.hideEvent(hide_event)
                    except Exception as e:
                        logger.error(f"Error sending hide event to widget: {e}")
                        
        elif 'RaceCoach' in widget_class_name:  # Race Coach tab
            if hasattr(self, 'race_coach_action'):
                self.race_coach_action.setChecked(True)
            self.calibration_wizard_btn.setVisible(False)
            
            # Send a show event to the Race Coach widget
            if hasattr(current_widget, 'showEvent'):
                try:
                    # Create a show event
                    show_event = QShowEvent()
                    # Call the widget's showEvent method
                    current_widget.showEvent(show_event)
                except Exception as e:
                    logger.error(f"Error sending show event to widget: {e}")
                
            # Initialize gamification overview if not already done
            self.initialize_gamification_overview()
            
        elif 'RacePass' in widget_class_name:  # Race Pass tab
            if hasattr(self, 'race_pass_action'):
                self.race_pass_action.setChecked(True)
            self.calibration_wizard_btn.setVisible(False)
            
        elif 'Community' in widget_class_name:  # Community tab
            if hasattr(self, 'community_action'):
                self.community_action.setChecked(True)
            self.calibration_wizard_btn.setVisible(False)
            
        else:  # Any other tab
            # Hide calibration buttons for unknown tabs
            self.calibration_wizard_btn.setVisible(False)
            
        logger.debug(f"Tab changed to index {index}, widget: {widget_class_name}")
        
    def initialize_gamification_overview(self):
        """Initialize the gamification overview widget if it doesn't exist already."""
        # Gamification overview has been moved to the Race Pass tab
        # This method is kept for compatibility but no longer creates the overview widget
        logger.info("Gamification overview functionality has been moved to the Race Pass tab")
        self.gamification_overview = None
    
    def get_community_managers(self):
        """Get all community-related managers for the community interface."""
        managers = {}
        
        # Add user manager if available
        try:
            from ..database import user_manager
            managers['user_manager'] = user_manager
        except ImportError:
            managers['user_manager'] = None
        
        # Add other managers as they become available
        # For now, we'll use placeholders that can be filled in later
        managers['friends_manager'] = None
        managers['messaging_manager'] = None
        managers['activity_manager'] = None
        managers['community_manager'] = None
        managers['content_manager'] = None
        managers['achievements_manager'] = None
        managers['reputation_manager'] = None
        
        return managers
    
    def get_current_user_id(self):
        """Get the current user ID for community features."""
        try:
            # Import the global supabase instance that has the correct methods
            from ..database import supabase_client
            if hasattr(supabase_client, 'supabase') and supabase_client.supabase:
                # Check if user is authenticated first
                if not supabase_client.supabase.is_authenticated():
                    return None
                    
                user = supabase_client.supabase.get_user()
                if user and hasattr(user, 'id'):
                    return user.id
                elif user and hasattr(user, 'user') and hasattr(user.user, 'id'):
                    return user.user.id
                else:
                    return None
            else:
                return None
        except Exception as e:
            logger.warning(f"Could not get user ID: {e}")
            return None
    
    def update_community_notification_badge(self, count):
        """Update the community button notification badge."""
        try:
            if hasattr(self, 'community_notification_badge'):
                if count > 0:
                    if count > 99:
                        self.community_notification_badge.setText("99+")
                    else:
                        self.community_notification_badge.setText(str(count))
                    self.community_notification_badge.show()
                    
                    # Update tooltip to include notification info
                    tooltip = f"Access community features: social, teams, content sharing, and achievements ({count} notification{'s' if count != 1 else ''})"
                    if hasattr(self, 'community_btn'):
                        self.community_btn.setToolTip(tooltip)
                    
                    # Add subtle animation to draw attention
                    self.animate_community_badge()
                else:
                    self.community_notification_badge.hide()
                    # Reset tooltip
                    if hasattr(self, 'community_btn'):
                        self.community_btn.setToolTip("Access community features: social, teams, content sharing, and achievements")
                    
        except Exception as e:
            logger.warning(f"Error updating community notification badge: {e}")
    
    def animate_community_badge(self):
        """Add a subtle animation to the community notification badge."""
        try:
            if hasattr(self, 'community_notification_badge') and self.community_notification_badge.isVisible():
                # Create a fade effect
                effect = QGraphicsOpacityEffect()
                self.community_notification_badge.setGraphicsEffect(effect)
                
                self.badge_animation = QPropertyAnimation(effect, b"opacity")
                self.badge_animation.setDuration(800)
                self.badge_animation.setStartValue(1.0)
                self.badge_animation.setEndValue(0.6)
                self.badge_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
                
                # Set up auto-reverse
                self.badge_animation.finished.connect(lambda: self.badge_animation.setDirection(
                    QPropertyAnimation.Forward if self.badge_animation.direction() == QPropertyAnimation.Backward 
                    else QPropertyAnimation.Backward
                ))
                self.badge_animation.finished.connect(self.badge_animation.start)
                self.badge_animation.start()
                
        except Exception as e:
            logger.warning(f"Error animating community badge: {e}")
    
    def update_existing_community_widgets(self, user):
        """Update any existing community widgets with new user data."""
        try:
            # Update community widget if it exists
            if hasattr(self, 'community_widget') and self.community_widget:
                if hasattr(self.community_widget, 'handle_auth_state_change'):
                    self.community_widget.handle_auth_state_change(user is not None)
                    
            # Update background community widget if it exists
            if hasattr(self, 'background_community_widget') and self.background_community_widget:
                if hasattr(self.background_community_widget, 'handle_auth_state_change'):
                    self.background_community_widget.handle_auth_state_change(user is not None)
                    
        except Exception as e:
            logger.warning(f"Error updating existing community widgets: {e}")
    
    def update_protected_features(self, is_authenticated):
        """Update features that require authentication."""
        try:
            # Update Race Coach action tooltip and state
            if hasattr(self, 'race_coach_action'):
                if is_authenticated:
                    self.race_coach_action.setToolTip("Access Race Coach for real-time telemetry analysis")
                    self.race_coach_action.setEnabled(True)
                else:
                    self.race_coach_action.setToolTip("Login required to access Race Coach features")
                    self.race_coach_action.setEnabled(True)  # Still enabled to show login prompt
                    
            # Update Race Pass action tooltip and state  
            if hasattr(self, 'race_pass_action'):
                if is_authenticated:
                    self.race_pass_action.setToolTip("Access Race Pass for achievements and progression")
                    self.race_pass_action.setEnabled(True)
                else:
                    self.race_pass_action.setToolTip("Login required to access Race Pass features")
                    self.race_pass_action.setEnabled(True)  # Still enabled to show login prompt
                    
            # Update Community action tooltip and state
            if hasattr(self, 'community_action'):
                if is_authenticated:
                    self.community_action.setToolTip("Access community features: social, teams, content sharing, and achievements")
                    self.community_action.setEnabled(True)
                else:
                    self.community_action.setToolTip("Login required to access Community features")
                    self.community_action.setEnabled(True)  # Still enabled to show login prompt
                    
        except Exception as e:
            logger.warning(f"Error updating protected features: {e}")
    
    def check_and_start_iracing_connection(self):
        """Check if user is authenticated and start iRacing connection if needed."""
        try:
            from ..database import supabase
            is_authenticated = supabase.is_authenticated()
            
            if is_authenticated and not self.iracing_connection_active:
                logger.info("🏁 User is authenticated, starting global iRacing connection...")
                self.start_global_iracing_connection()
            elif not is_authenticated:
                logger.info("🏁 User not authenticated, skipping iRacing connection")
                self.update_iracing_status(False, "Login required")
            
        except Exception as e:
            logger.error(f"Error checking authentication for iRacing connection: {e}")
    
    def start_global_iracing_connection(self):
        """Start the global iRacing connection manager."""
        try:
            if self.global_iracing_api is None:
                from ..race_coach.simple_iracing import SimpleIRacingAPI
                self.global_iracing_api = SimpleIRacingAPI()
                
                # �� SET UP TELEMETRY SAVING with the global connection
                logger.info("🎯 Setting up telemetry saving for global iRacing connection...")
                
                # Get Supabase client for saving
                try:
                    from ..database.supabase_client import get_supabase_client
                    supabase_client = get_supabase_client()
                    if supabase_client:
                        logger.info("✅ Got Supabase client for global telemetry saving")
                        
                        # Create lap saver for the global connection
                        from ..race_coach.iracing_lap_saver import IRacingLapSaver
                        global_lap_saver = IRacingLapSaver()
                        global_lap_saver.set_supabase_client(supabase_client)
                        
                        # Set user ID if authenticated
                        try:
                            from ..auth.user_manager import get_current_user
                            user = get_current_user()
                            if user and hasattr(user, 'id') and user.is_authenticated:
                                user_id = user.id
                                global_lap_saver.set_user_id(user_id)
                                logger.info(f"✅ Set user ID for global lap saver: {user_id}")
                            else:
                                logger.info("ℹ️ No authenticated user - running in offline mode")
                        except Exception as user_error:
                            logger.warning(f"Could not get user for global lap saver: {user_error}")
                        
                        # Connect lap saver to the API
                        if hasattr(self.global_iracing_api, 'set_lap_saver'):
                            self.global_iracing_api.set_lap_saver(global_lap_saver)
                            logger.info("✅ Connected global lap saver to iRacing API")
                        
                        # Set up deferred monitoring params
                        self.global_iracing_api._deferred_monitor_params = {
                            'supabase_client': supabase_client,
                            'user_id': user.id if user and hasattr(user, 'id') and user.is_authenticated else 'anonymous',
                            'lap_saver': global_lap_saver
                        }
                        logger.info("✅ Global telemetry saving configured")
                    else:
                        logger.warning("⚠️ No Supabase client - telemetry will not save to cloud")
                except Exception as save_error:
                    logger.error(f"❌ Error setting up telemetry saving: {save_error}")
                
                # Register for connection status updates
                self.global_iracing_api.register_on_connection_changed(self.on_global_iracing_connection_changed)
                
                # Start telemetry monitoring
                self.global_iracing_api._start_telemetry_timer()
                
                # 🔧 CRITICAL FIX: Actually start the deferred monitoring
                logger.info("🚀 Starting deferred iRacing session monitoring...")
                monitoring_started = self.global_iracing_api.start_deferred_monitoring()
                if monitoring_started:
                    logger.info("✅ Deferred iRacing session monitoring started successfully")
                else:
                    logger.warning("⚠️ Failed to start deferred monitoring - running in basic mode only")
                
                self.iracing_connection_active = True
                logger.info("🏁 Global iRacing connection started with telemetry saving")
                
                # Update track map overlay manager to use shared API
                if not self.track_map_overlay_manager:
                    from ..race_coach.track_map_overlay import TrackMapOverlayManager
                    self.track_map_overlay_manager = TrackMapOverlayManager(self.global_iracing_api)
                    logger.info("🗺️ Created track map overlay manager with shared iRacing API")
                else:
                    self.track_map_overlay_manager.shared_iracing_api = self.global_iracing_api
                
        except Exception as e:
            logger.error(f"Failed to start global iRacing connection: {e}")
            self.update_iracing_status(False, "Connection failed")
    
    def stop_global_iracing_connection(self):
        """Stop the global iRacing connection manager."""
        try:
            if self.global_iracing_api:
                self.global_iracing_api.disconnect()
                self.global_iracing_api = None
                
            self.iracing_connection_active = False
            self.update_iracing_status(False, "Disconnected")
            logger.info("🏁 Global iRacing connection stopped")
            
        except Exception as e:
            logger.error(f"Error stopping global iRacing connection: {e}")
    
    def toggle_iracing_connection(self):
        """Toggle the iRacing connection on/off."""
        try:
            if self.iracing_connection_active:
                self.stop_global_iracing_connection()
            else:
                from ..database import supabase
                if supabase.is_authenticated():
                    self.start_global_iracing_connection()
                else:
                    # Show login dialog
                    QMessageBox.information(
                        self, 
                        "🏁 iRacing Connection", 
                        "You need to be logged in to connect to iRacing.\n\n"
                        "Telemetry data is automatically saved to the cloud when you're authenticated."
                    )
                    self.show_login_dialog()
                    
        except Exception as e:
            logger.error(f"Error toggling iRacing connection: {e}")
    
    def on_global_iracing_connection_changed(self, is_connected, session_info=None):
        """Handle global iRacing connection status changes."""
        try:
            self.update_iracing_status(is_connected)
            
            if is_connected:
                logger.info("🏁 Global iRacing connection established")
            else:
                logger.info("🏁 Global iRacing connection lost")
                
        except Exception as e:
            logger.error(f"Error handling global iRacing connection change: {e}")
    
    def update_iracing_status(self, is_connected, status_text=None):
        """Update the iRacing connection status in the status bar."""
        try:
            if is_connected:
                self.iracing_status_label.setText("🏁 iRacing: Connected")
                self.iracing_status_label.setStyleSheet("color: #28a745; font-size: 10px; padding: 2px 8px; font-weight: bold;")
                self.iracing_status_label.setToolTip("iRacing connected - telemetry data being saved")
            else:
                display_text = status_text or "Disconnected"
                self.iracing_status_label.setText(f"🏁 iRacing: {display_text}")
                self.iracing_status_label.setStyleSheet("color: #ff6b6b; font-size: 10px; padding: 2px 8px; font-weight: bold;")
                self.iracing_status_label.setToolTip("iRacing disconnected - click to connect (requires login)")
                
        except Exception as e:
            logger.error(f"Error updating iRacing status: {e}")
    
    def get_shared_iracing_api(self):
        """Get the shared iRacing API instance for other components."""
        return self.global_iracing_api
    
    # NOTE: In the actual implementation, ALL remaining methods from the original MainWindow 
    # would be copied here verbatim, except for the three methods we extracted.
    
    def update_pedal_status_display(self):
        """Update the real-time pedal performance indicator."""
        try:
            # Get performance stats from the main app if available
            if hasattr(self, 'app') and hasattr(self.app, 'pedal_performance_stats'):
                stats = self.app.pedal_performance_stats
                
                # Create status text based on performance
                if stats['severe_lag_percentage'] > 1.0:
                    icon = "🚨"
                    text = f"LAG! {stats['severe_lag_percentage']:.1f}% delays"
                    color = "#e74c3c"  # Red
                elif stats['slow_percentage'] > 5.0:
                    icon = "⚠️"
                    text = f"Slow: {stats['slow_percentage']:.1f}%"
                    color = "#f39c12"  # Orange
                elif stats['frequency'] < 500:
                    icon = "🐌"
                    text = f"{stats['frequency']:.0f}Hz (Low)"
                    color = "#f1c40f"  # Yellow
                else:
                    icon = "✅"
                    text = f"{stats['frequency']:.0f}Hz, {stats['latency_ms']:.1f}ms"
                    color = "#27ae60"  # Green
                
                # Update the label
                self.pedal_status_label.setText(f"{icon} Pedals: {text}")
                self.pedal_status_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {color};
                        color: white;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-weight: bold;
                        font-size: 11px;
                    }}
                """)
                
                # Set tooltip with detailed info
                tooltip = (f"Pedal Performance:\n"
                          f"• Frequency: {stats['frequency']:.0f}Hz (target: 1000Hz)\n"
                          f"• Latency: {stats['latency_ms']:.2f}ms (target: <1ms)\n"
                          f"• Slow frames: {stats['slow_percentage']:.1f}%\n"
                          f"• Severe lag: {stats['severe_lag_percentage']:.1f}%\n"
                          f"• vJoy responsive: {'Yes' if stats['vjoy_responsive'] else 'No'}")
                self.pedal_status_label.setToolTip(tooltip)
                
            else:
                # No stats available yet
                self.pedal_status_label.setText("🎮 Pedals: Initializing...")
                self.pedal_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #95a5a6;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                """)
                self.pedal_status_label.setToolTip("Pedal performance monitoring starting...")
                
        except Exception as e:
            # Fallback for any errors
            self.pedal_status_label.setText("🎮 Pedals: Unknown")
            self.pedal_status_label.setStyleSheet("""
                QLabel {
                    background-color: #7f8c8d;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11px;
                }
            """)
            self.pedal_status_label.setToolTip(f"Error updating pedal status: {e}")