import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTabWidget, QGroupBox,
                             QSplitter, QComboBox, QStatusBar, QMainWindow, QMessageBox, QApplication, QGridLayout, QFrame, QFormLayout, QCheckBox, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QConicalGradient
import time
import threading
import weakref
import numpy as np  # Add numpy import for array handling

logger = logging.getLogger(__name__)

class GaugeBase(QWidget):
    """Base class for custom gauge widgets."""
    def __init__(self, min_value=0, max_value=100, parent=None):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value
        
        # Appearance settings
        self.gauge_color = QColor(0, 122, 204)  # #007ACC
        self.background_color = QColor(45, 45, 48)  # #2D2D30
        self.text_color = QColor(255, 255, 255)  # White
        
        # Set minimum size for proper rendering
        self.setMinimumSize(200, 150)
        
    def set_value(self, value):
        """Set the current value of the gauge."""
        # Clamp value to range
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()  # Trigger a repaint
        
    def get_normalized_value(self):
        """Get the normalized value (0-1) for drawing."""
        range_value = self.max_value - self.min_value
        if range_value == 0:
            return 0
        return (self.value - self.min_value) / range_value
        
    def paintEvent(self, event):
        """Override to implement custom painting."""
        # Base class does nothing - override in subclasses
        pass
        
class SpeedGauge(GaugeBase):
    """Custom gauge widget for displaying vehicle speed."""
    def __init__(self, parent=None):
        super().__init__(0, 300, parent)  # Speed from 0-300 km/h
        self.setObjectName("SpeedGauge")
        self.title = "Speed"
        self.units = "km/h"
        
        # Special colors for speed display
        self.low_speed_color = QColor(0, 150, 200)
        self.high_speed_color = QColor(255, 50, 50)
        
    def paintEvent(self, event):
        """Paint the speed gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Calculate dimensions
        padding = 10
        gauge_width = width - (padding * 2)
        gauge_height = 30
        
        # Draw gauge background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.background_color.darker(120)))
        painter.drawRoundedRect(padding, height - gauge_height - padding, 
                               gauge_width, gauge_height, 5, 5)
        
        # Draw gauge fill - gradient from blue to red based on speed
        normalized = self.get_normalized_value()
        if normalized > 0:
            # Create gradient
            gradient = QLinearGradient(padding, 0, padding + gauge_width, 0)
            gradient.setColorAt(0, self.low_speed_color)
            gradient.setColorAt(1, self.high_speed_color)
            
            painter.setBrush(QBrush(gradient))
            fill_width = int(normalized * gauge_width)
            painter.drawRoundedRect(padding, height - gauge_height - padding, 
                                   fill_width, gauge_height, 5, 5)
        
        # Draw title
        title_font = painter.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(self.text_color))
        painter.drawText(padding, padding, gauge_width, 30, 
                        Qt.AlignLeft | Qt.AlignVCenter, self.title)
        
        # Draw value
        value_font = painter.font()
        value_font.setPointSize(22)
        value_font.setBold(True)
        painter.setFont(value_font)
        value_text = f"{self.value:.1f} {self.units}"
        painter.drawText(padding, 40, gauge_width, 50, 
                        Qt.AlignCenter, value_text)
        
        # Draw tick marks
        painter.setPen(QPen(self.text_color.lighter(150), 1))
        tick_y = height - gauge_height - padding - 5
        
        # Major ticks every 50 km/h
        for speed in range(0, int(self.max_value) + 1, 50):
            tick_x = padding + (speed / self.max_value) * gauge_width
            painter.drawLine(int(tick_x), tick_y, int(tick_x), tick_y - 10)
            
            # Draw tick label
            painter.drawText(int(tick_x) - 15, tick_y - 15, 30, 20, 
                            Qt.AlignCenter, str(speed))
        
        # Minor ticks every 10 km/h
        painter.setPen(QPen(self.text_color.lighter(120), 0.5))
        for speed in range(0, int(self.max_value) + 1, 10):
            if speed % 50 != 0:  # Skip major ticks
                tick_x = padding + (speed / self.max_value) * gauge_width
                painter.drawLine(int(tick_x), tick_y, int(tick_x), tick_y - 5)
        
class RPMGauge(GaugeBase):
    """Custom gauge widget for displaying engine RPM."""
    def __init__(self, parent=None):
        super().__init__(0, 10000, parent)  # RPM from 0-10000
        self.setObjectName("RPMGauge")
        self.title = "RPM"
        self.redline = 7500  # Default redline
        
    def set_redline(self, redline):
        """Set the redline RPM value."""
        self.redline = redline
        self.update()
        
    def paintEvent(self, event):
        """Paint the RPM gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Calculate dimensions and center point
        margin = 10
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - margin
        
        # Draw gauge background - arc from 135° to 405° (270° span)
        start_angle = 135
        span_angle = 270
        arc_rect = QRect(int(center_x - radius), int(center_y - radius),
                        int(radius * 2), int(radius * 2))
        
        # Draw outer ring
        painter.setPen(QPen(self.text_color.darker(120), 5))
        painter.drawArc(arc_rect, start_angle * 16, span_angle * 16)
        
        # Calculate normalized position for current value and redline
        normalized = self.get_normalized_value()
        redline_normalized = (self.redline - self.min_value) / (self.max_value - self.min_value)
        
        # Draw filled arc for current RPM
        if normalized > 0:
            # Determine color based on whether RPM is approaching redline
            if normalized < redline_normalized * 0.8:
                gauge_color = QColor(0, 150, 200)  # Blue for normal operation
            elif normalized < redline_normalized:
                gauge_color = QColor(255, 150, 0)  # Orange for approaching redline
            else:
                gauge_color = QColor(255, 50, 50)  # Red for at/beyond redline
                
            # Draw filled arc
            painter.setPen(QPen(gauge_color, 10, Qt.SolidLine, Qt.RoundCap))
            span = normalized * span_angle
            painter.drawArc(arc_rect, start_angle * 16, int(span * 16))
        
        # Draw redline marker
        if redline_normalized > 0 and redline_normalized <= 1:
            redline_angle = start_angle + (redline_normalized * span_angle)
            redline_x = center_x + radius * 0.95 * math.cos(math.radians(redline_angle))
            redline_y = center_y + radius * 0.95 * math.sin(math.radians(redline_angle))
            
            painter.setPen(QPen(QColor(255, 0, 0), 3))  # Thick red pen
            painter.drawLine(int(center_x), int(center_y), int(redline_x), int(redline_y))
        
        # Draw RPM text in center
        value_font = painter.font()
        value_font.setPointSize(18)
        value_font.setBold(True)
        painter.setFont(value_font)
        painter.setPen(QPen(self.text_color))
        
        # Format RPM text - show in thousands with one decimal place
        rpm_text = f"{self.value/1000:.1f}k"
        painter.drawText(arc_rect, Qt.AlignCenter, rpm_text)
        
        # Draw title text
        title_font = painter.font()
        title_font.setPointSize(12)
        painter.setFont(title_font)
        title_rect = QRect(arc_rect.left(), arc_rect.top() + arc_rect.height() // 2 + 10,
                          arc_rect.width(), 30)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)

# Import the required classes here
import math

class InputTraceWidget(QWidget):
    """Widget to display a history of driver inputs as a small graph."""
    
    # Add a signal for safer threaded updates
    data_updated = pyqtSignal()
    
    def __init__(self, parent=None, max_points=100):
        """Initialize the input trace widget."""
        super().__init__(parent)
        
        # Settings
        self.max_points = max_points
        self.throttle_color = QColor("#4CAF50")  # Green
        self.brake_color = QColor("#FF5252")     # Red
        self.clutch_color = QColor("#FFC107")    # Amber
        self.background_color = QColor(30, 30, 30, 180)
        self.grid_color = QColor(70, 70, 70, 100)
        
        # Initialize data arrays
        self.throttle_data = np.zeros(max_points, dtype=float)
        self.brake_data = np.zeros(max_points, dtype=float)
        self.clutch_data = np.zeros(max_points, dtype=float)
        
        # Set minimum size
        self.setMinimumSize(300, 120)
        
        # Visual settings
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, self.background_color)
        self.setPalette(palette)
        
        # Use a mutex to protect the data during updates
        self._data_mutex = threading.Lock()
        
        # Connect our signal to trigger update
        self.data_updated.connect(self.update)
        
    def add_data_point(self, throttle, brake, clutch):
        """Add a new data point to the trace display.
        
        Args:
            throttle: Throttle input (0-1)
            brake: Brake input (0-1)
            clutch: Clutch input (0-1)
        """
        # Lock the data during update
        with self._data_mutex:
            # Shift arrays and add new values
            self.throttle_data = np.roll(self.throttle_data, -1)
            self.brake_data = np.roll(self.brake_data, -1)
            self.clutch_data = np.roll(self.clutch_data, -1)
            
            self.throttle_data[-1] = throttle
            self.brake_data[-1] = brake
            self.clutch_data[-1] = clutch
        
        # Emit signal to trigger a repaint on the main thread
        self.data_updated.emit()
        
    def clear_data(self):
        """Clear all data from the trace display."""
        with self._data_mutex:
            self.throttle_data[:] = 0
            self.brake_data[:] = 0
            self.clutch_data[:] = 0
            
        # Emit signal to trigger a repaint on the main thread
        self.data_updated.emit()
        
    def paintEvent(self, event):
        """Paint the input trace visualization."""
        # Create a copy of the data to avoid threading issues during paint
        with self._data_mutex:
            throttle_data = self.throttle_data.copy()
            brake_data = self.brake_data.copy()
            clutch_data = self.clutch_data.copy()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Calculate drawing area
        padding = 10
        graph_width = width - (padding * 2)
        graph_height = height - (padding * 2)
        
        # Draw background (already handled by palette)
        
        # Draw title text at top
        title_font = painter.font()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.white))
        painter.drawText(padding, 5, graph_width, 20, Qt.AlignLeft, "Driver Inputs History")
        
        # Draw axis labels
        axis_font = painter.font()
        axis_font.setPointSize(8)
        painter.setFont(axis_font)
        
        # Y-axis labels
        painter.drawText(padding - 8, padding - 5, "100%")
        painter.drawText(padding - 8, int(padding + graph_height / 2), "50%")
        painter.drawText(padding - 8, padding + graph_height + 5, "0%")
        
        # X-axis label - Time
        painter.drawText(int(width / 2 - 15), padding + graph_height + 15, "Time →")
        
        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1, Qt.DashLine))
        
        # Horizontal grid lines at 25%, 50%, 75%
        for y_pct in [0.25, 0.5, 0.75]:
            y = padding + (1.0 - y_pct) * graph_height
            painter.drawLine(padding, int(y), padding + graph_width, int(y))
        
        # Vertical grid lines every 25% of width
        for x_pct in [0.25, 0.5, 0.75]:
            x = padding + x_pct * graph_width
            painter.drawLine(int(x), padding, int(x), padding + graph_height)
            
        # Draw border
        painter.setPen(QPen(self.grid_color.lighter(120), 1))
        painter.drawRect(padding, padding, graph_width, graph_height)
        
        # Draw data traces if we have any data
        if np.max(throttle_data) > 0 or np.max(brake_data) > 0 or np.max(clutch_data) > 0:
            # Calculate points for each data set
            data_len = len(throttle_data)
            x_step = graph_width / (data_len - 1) if data_len > 1 else graph_width
            
            # Draw throttle trace
            throttle_pen = QPen(self.throttle_color, 2)
            painter.setPen(throttle_pen)
            
            for i in range(data_len - 1):
                x1 = padding + i * x_step
                y1 = padding + graph_height - (throttle_data[i] * graph_height)
                x2 = padding + (i + 1) * x_step
                y2 = padding + graph_height - (throttle_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
            # Draw brake trace
            brake_pen = QPen(self.brake_color, 2)
            painter.setPen(brake_pen)
            
            for i in range(data_len - 1):
                x1 = padding + i * x_step
                y1 = padding + graph_height - (brake_data[i] * graph_height)
                x2 = padding + (i + 1) * x_step
                y2 = padding + graph_height - (brake_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
            # Draw clutch trace
            clutch_pen = QPen(self.clutch_color, 2)
            painter.setPen(clutch_pen)
            
            for i in range(data_len - 1):
                x1 = padding + i * x_step
                y1 = padding + graph_height - (clutch_data[i] * graph_height)
                x2 = padding + (i + 1) * x_step
                y2 = padding + graph_height - (clutch_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
        # Draw legend
        legend_padding = 5
        legend_height = 15
        legend_spacing = 10
        
        # Throttle
        painter.setPen(self.throttle_color)
        painter.drawLine(width - 60, legend_padding, width - 45, legend_padding)
        painter.drawText(width - 40, legend_padding + 5, "Throttle")
        
        # Brake
        painter.setPen(self.brake_color)
        painter.drawLine(width - 60, legend_padding + legend_height, width - 45, legend_padding + legend_height)
        painter.drawText(width - 40, legend_padding + legend_height + 5, "Brake")
        
        # Clutch
        painter.setPen(self.clutch_color)
        painter.drawLine(width - 60, legend_padding + 2 * legend_height, width - 45, legend_padding + 2 * legend_height)
        painter.drawText(width - 40, legend_padding + 2 * legend_height + 5, "Clutch")

class RaceCoachWidget(QWidget):
    """Main widget for the Race Coach feature that can be embedded as a tab."""
    
    # Add signal for telemetry updates from background thread
    telemetry_update_signal = pyqtSignal(dict)
    
    def __init__(self, parent=None, iracing_api=None, data_manager=None, model=None, lap_analysis=None, super_lap=None):
        """Initialize the Race Coach widget.
        
        Args:
            parent: Parent widget
            iracing_api: Instance of IRacingAPI class
            data_manager: Instance of DataManager class
            model: Instance of RacingModel class
            lap_analysis: Instance of LapAnalysis class
            super_lap: Instance of SuperLap class
        """
        super().__init__(parent)
        
        try:
            # Flag to indicate if the widget is being destroyed
            self._is_destroying = False
            
            # Store component references - use provided iracing_api
            if iracing_api is None:
                # Import our SimpleIRacingAPI instead of using a mock
                try:
                    from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
                    self.iracing_api = SimpleIRacingAPI()
                    logger.info("Created SimpleIRacingAPI for direct iRacing connection")
                except ImportError as e:
                    logger.error(f"Cannot import SimpleIRacingAPI: {e}")
                    # Only as a last resort, use IRacingAPI from the module
                    try:
                        from trackpro.race_coach.iracing_api import IRacingAPI
                        self.iracing_api = IRacingAPI()
                        logger.info("Created IRacingAPI as alternative for direct iRacing connection")
                    except ImportError as e2:
                        logger.error(f"Cannot import IRacingAPI: {e2}")
                        # We really don't want to end up here
                        raise RuntimeError("Failed to create any iRacing API connection")
            else:
                self.iracing_api = iracing_api
                logger.info(f"Using provided iracing_api: {type(self.iracing_api).__name__}")
                
            self.data_manager = data_manager
            self.model = model
            self.lap_analysis = lap_analysis
            self.super_lap = super_lap
            
            # Connect the telemetry update signal to the slot
            self.telemetry_update_signal.connect(self._on_telemetry_update_main_thread)
            
            # Initialize state
            self._is_connected = False
            self._current_track = "Unknown"
            self._current_car = "Unknown"
            self._driver_id = None
            self._session_type = "Practice"
            self._latest_telemetry = {}
            
            # Set up UI
            self.setup_ui()
            
            # Set up a monitoring timer to regularly log pedal values
            self._setup_monitoring_timer()
            
            # Get API class name for better logging
            api_class_name = self.iracing_api.__class__.__name__
            logger.info(f"Registering callbacks with IRacingAPI instance: {api_class_name}")
            
            # Register callbacks with iRacing API
            try:
                self.iracing_api.register_on_connection_changed(self._on_iracing_connected)
                self.iracing_api.register_on_session_info_changed(self._on_session_info_update)
                
                # Create a safe callback that won't access a deleted widget
                # We need to keep a reference to this function to be able to unregister it later
                self._safe_telemetry_callback = self._create_safe_telemetry_callback()
                self.iracing_api.register_on_telemetry_data(self._safe_telemetry_callback)
            except Exception as e:
                logger.error(f"Error registering callbacks with iRacing API: {e}")
                
            # Create a timer to periodically check iRacing connection
            self.connection_check_timer = QTimer()
            self.connection_check_timer.timeout.connect(self._check_iracing_connection)
            self.connection_check_timer.start(1000)  # Check every 1 second
                
        except Exception as e:
            logger.error(f"Error in RaceCoachWidget initialization: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Create a minimal UI with an error message
            layout = QVBoxLayout(self)
            error_label = QLabel(f"Failed to initialize Race Coach component: {str(e)}")
            error_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(error_label)

    def setup_ui(self):
        """Set up the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Create status section at the top
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        # iRacing connection status with improved visibility
        self.iracing_status = QLabel("iRacing: Not Connected")
        self.iracing_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.iracing_status.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
                background-color: #FF5252;
                color: white;
            }
        """)
        
        # Current track and car info with improved styling
        self.track_info = QLabel("Track: None")
        self.track_info.setFont(QFont("Arial", 11))
        self.track_info.setStyleSheet("""
            QLabel {
                padding: 6px 10px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        
        self.car_info = QLabel("Car: None")
        self.car_info.setFont(QFont("Arial", 11))
        self.car_info.setStyleSheet("""
            QLabel {
                padding: 6px 10px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        
        # Connect button with improved styling
        self.connect_button = QPushButton("Connect to iRacing")
        self.connect_button.setMinimumWidth(180)
        self.connect_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.connect_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border-radius: 6px;
                background-color: #2196F3;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #0D8BF2;
            }
            QPushButton:pressed {
                background-color: #0B7AD1;
            }
        """)
        self.connect_button.clicked.connect(self._on_connect_clicked)
        
        # Add widgets to status layout
        status_layout.addWidget(self.iracing_status)
        status_layout.addWidget(self.track_info)
        status_layout.addWidget(self.car_info)
        status_layout.addStretch()
        status_layout.addWidget(self.connect_button)
        
        # Container for status with border and background
        status_container = QWidget()
        status_container.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
        """)
        status_container.setLayout(status_layout)
        status_container.setMinimumHeight(70)
        
        # Add status container to main layout
        main_layout.addWidget(status_container)
        
        # Create tab widget for different functionalities
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Arial", 11))
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(100, 100, 100, 0.5);
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: rgba(60, 60, 60, 0.7);
                color: white;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: rgba(40, 40, 40, 0.9);
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-bottom: none;
            }
        """)
        
        # Create tabs
        self.setup_dashboard_tab()
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Add status message at the bottom with improved styling
        self.status_message = QLabel("Ready")
        self.status_message.setFont(QFont("Arial", 10))
        self.status_message.setStyleSheet("""
            QLabel {
                padding: 6px 10px;
                color: rgba(255, 255, 255, 0.8);
                background-color: rgba(40, 40, 40, 0.5);
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.status_message)
        
    def setup_dashboard_tab(self):
        """Set up the Dashboard tab with current session info."""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create header
        header = QLabel("Dashboard")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # Create telemetry dashboard with real-time data display
        telemetry_layout = QHBoxLayout()
        
        # Left column - Basic session info
        left_column = QVBoxLayout()
        session_group = QGroupBox("Session Info")
        session_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 5px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        session_layout = QVBoxLayout(session_group)
        
        # Session type
        session_type_layout = QHBoxLayout()
        session_type_label = QLabel("Session Type:")
        session_type_label.setStyleSheet("color: white; font-size: 12px;")
        self.session_type_value = QLabel("Unknown")
        self.session_type_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        session_type_layout.addWidget(session_type_label)
        session_type_layout.addWidget(self.session_type_value)
        session_layout.addLayout(session_type_layout)
        
        # Lap counter
        lap_layout = QHBoxLayout()
        lap_label = QLabel("Current Lap:")
        lap_label.setStyleSheet("color: white; font-size: 12px;")
        self.lap_info = QLabel("0")
        self.lap_info.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        lap_layout.addWidget(lap_label)
        lap_layout.addWidget(self.lap_info)
        session_layout.addLayout(lap_layout)
        
        # Add session group to left column
        left_column.addWidget(session_group)
        
        # Middle column - Current telemetry values
        middle_column = QVBoxLayout()
        telemetry_group = QGroupBox("Live Telemetry")
        telemetry_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 5px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        # Use grid layout for more compact display
        telemetry_info_layout = QGridLayout(telemetry_group)
        telemetry_info_layout.setVerticalSpacing(8)
        telemetry_info_layout.setHorizontalSpacing(15)
        
        # Speed display - row 0
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet("color: white; font-size: 12px;")
        self.speed_value = QLabel("0.0 km/h")
        self.speed_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        telemetry_info_layout.addWidget(speed_label, 0, 0)
        telemetry_info_layout.addWidget(self.speed_value, 0, 1)
        
        # RPM display - row 1
        rpm_label = QLabel("RPM:")
        rpm_label.setStyleSheet("color: white; font-size: 12px;")
        self.rpm_value = QLabel("0")
        self.rpm_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        telemetry_info_layout.addWidget(rpm_label, 1, 0)
        telemetry_info_layout.addWidget(self.rpm_value, 1, 1)
        
        # Gear display - row 2
        gear_label = QLabel("Gear:")
        gear_label.setStyleSheet("color: white; font-size: 12px;")
        self.gear_value = QLabel("N")
        self.gear_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        telemetry_info_layout.addWidget(gear_label, 2, 0)
        telemetry_info_layout.addWidget(self.gear_value, 2, 1)
        
        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: rgba(100, 100, 100, 0.5);")
        telemetry_info_layout.addWidget(separator, 3, 0, 1, 4)
        
        # Driver Inputs section header
        inputs_header = QLabel("Driver Inputs")
        inputs_header.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        telemetry_info_layout.addWidget(inputs_header, 4, 0, 1, 4, Qt.AlignCenter)
        
        # Throttle display - row 5
        throttle_label = QLabel("Throttle:")
        throttle_label.setStyleSheet("color: white; font-size: 12px;")
        self.throttle_value = QLabel("0%")
        self.throttle_value.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")  # Green color
        telemetry_info_layout.addWidget(throttle_label, 5, 0)
        telemetry_info_layout.addWidget(self.throttle_value, 5, 1)
        
        # Throttle progress bar
        self.throttle_bar = QProgressBar()
        self.throttle_bar.setRange(0, 100)
        self.throttle_bar.setValue(0)
        self.throttle_bar.setTextVisible(False)
        self.throttle_bar.setFixedHeight(12)
        self.throttle_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 30, 30, 0.5);
                border-radius: 3px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        telemetry_info_layout.addWidget(self.throttle_bar, 5, 2, 1, 2)
        
        # Brake display - row 6
        brake_label = QLabel("Brake:")
        brake_label.setStyleSheet("color: white; font-size: 12px;")
        self.brake_value = QLabel("0%")
        self.brake_value.setStyleSheet("color: #FF5252; font-size: 12px; font-weight: bold;")  # Red color
        telemetry_info_layout.addWidget(brake_label, 6, 0)
        telemetry_info_layout.addWidget(self.brake_value, 6, 1)
        
        # Brake progress bar
        self.brake_bar = QProgressBar()
        self.brake_bar.setRange(0, 100)
        self.brake_bar.setValue(0)
        self.brake_bar.setTextVisible(False)
        self.brake_bar.setFixedHeight(12)
        self.brake_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 30, 30, 0.5);
                border-radius: 3px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
            QProgressBar::chunk {
                background-color: #FF5252;
                border-radius: 3px;
            }
        """)
        telemetry_info_layout.addWidget(self.brake_bar, 6, 2, 1, 2)
        
        # Clutch display - row 7
        clutch_label = QLabel("Clutch:")
        clutch_label.setStyleSheet("color: white; font-size: 12px;")
        self.clutch_value = QLabel("0%")
        self.clutch_value.setStyleSheet("color: #FFC107; font-size: 12px; font-weight: bold;")  # Amber color
        telemetry_info_layout.addWidget(clutch_label, 7, 0)
        telemetry_info_layout.addWidget(self.clutch_value, 7, 1)
        
        # Clutch progress bar
        self.clutch_bar = QProgressBar()
        self.clutch_bar.setRange(0, 100)
        self.clutch_bar.setValue(0)
        self.clutch_bar.setTextVisible(False)
        self.clutch_bar.setFixedHeight(12)
        self.clutch_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 30, 30, 0.5);
                border-radius: 3px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
            QProgressBar::chunk {
                background-color: #FFC107;
                border-radius: 3px;
            }
        """)
        telemetry_info_layout.addWidget(self.clutch_bar, 7, 2, 1, 2)
        
        # Add column stretching to make progress bars fill available space
        telemetry_info_layout.setColumnStretch(2, 1)
        telemetry_info_layout.setColumnStretch(3, 1)
        
        # Add telemetry group to middle column
        middle_column.addWidget(telemetry_group)
        
        # Right column - Lap time information
        right_column = QVBoxLayout()
        timing_group = QGroupBox("Lap Timing")
        timing_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 5px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        timing_layout = QVBoxLayout(timing_group)
        
        # Current lap time
        current_lap_layout = QHBoxLayout()
        current_lap_label = QLabel("Current Lap:")
        current_lap_label.setStyleSheet("color: white; font-size: 12px;")
        self.lap_time_value = QLabel("0:00.000")
        self.lap_time_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        current_lap_layout.addWidget(current_lap_label)
        current_lap_layout.addWidget(self.lap_time_value)
        timing_layout.addLayout(current_lap_layout)
        
        # Last lap time
        last_lap_layout = QHBoxLayout()
        last_lap_label = QLabel("Last Lap:")
        last_lap_label.setStyleSheet("color: white; font-size: 12px;")
        self.last_lap_value = QLabel("0:00.000")
        self.last_lap_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        last_lap_layout.addWidget(last_lap_label)
        last_lap_layout.addWidget(self.last_lap_value)
        timing_layout.addLayout(last_lap_layout)
        
        # Best lap time
        best_lap_layout = QHBoxLayout()
        best_lap_label = QLabel("Best Lap:")
        best_lap_label.setStyleSheet("color: white; font-size: 12px;")
        self.best_lap_value = QLabel("0:00.000")
        self.best_lap_value.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        best_lap_layout.addWidget(best_lap_label)
        best_lap_layout.addWidget(self.best_lap_value)
        timing_layout.addLayout(best_lap_layout)
        
        # Add timing group to right column
        right_column.addWidget(timing_group)
        
        # Add all columns to telemetry layout
        telemetry_layout.addLayout(left_column)
        telemetry_layout.addLayout(middle_column)
        telemetry_layout.addLayout(right_column)
        
        # Add telemetry layout to main layout
        layout.addLayout(telemetry_layout)
        
        # Add input trace widget below the telemetry dashboard
        input_trace_group = QGroupBox("Input Trace")
        input_trace_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 5px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        input_trace_layout = QVBoxLayout(input_trace_group)
        
        # Create the input trace widget
        self.input_trace = InputTraceWidget(max_points=300)
        self.input_trace.setMinimumHeight(180)
        input_trace_layout.addWidget(self.input_trace)
        
        # Add input trace group to main layout
        layout.addWidget(input_trace_group)
        
        # Add a spacer to push everything to the top
        layout.addStretch()
        
        # Add tab to widget
        self.tab_widget.addTab(dashboard_widget, "Dashboard")

    def _setup_monitoring_timer(self):
        """Set up a timer to periodically log pedal values for monitoring."""
        try:
            self.monitor_timer = QTimer()
            self.monitor_timer.timeout.connect(self._log_pedal_values)
            self.monitor_timer.start(5000)  # Log every 5 seconds
            logger.info("Started pedal values monitoring timer")
        except Exception as e:
            logger.error(f"Error setting up monitoring timer: {e}")
            # Continue even if monitoring fails

    def _log_pedal_values(self):
        """Log current pedal values for monitoring."""
        try:
            # Skip if widget is being destroyed
            if hasattr(self, '_is_destroying') and self._is_destroying:
                return
                
            if hasattr(self, '_latest_telemetry') and self._latest_telemetry:
                throttle = self._latest_telemetry.get('throttle', None)
                brake = self._latest_telemetry.get('brake', None)
                clutch = self._latest_telemetry.get('clutch', None)
                
                if throttle is not None or brake is not None or clutch is not None:
                    logger.info(f"MONITORING - Current pedal values: Throttle={throttle:.2f if throttle is not None else 'N/A'}, "
                              f"Brake={brake:.2f if brake is not None else 'N/A'}, "
                              f"Clutch={clutch:.2f if clutch is not None else 'N/A'}")
                else:
                    logger.warning("MONITORING - No pedal values found in latest telemetry")
            else:
                logger.warning("MONITORING - No telemetry data available")
        except Exception as e:
            logger.error(f"Error in pedal monitoring: {e}")
            # Don't let monitoring errors crash the app

    def _check_iracing_connection(self):
        """Periodically check if iRacing is running and we can connect to it."""
        # Skip if widget is being destroyed
        if hasattr(self, '_is_destroying') and self._is_destroying:
            return
            
        # Skip if we're already connected
        if self._is_connected:
            # Just verify that we still have a connection
            if hasattr(self.iracing_api, 'is_connected') and not self.iracing_api.is_connected():
                # We lost the connection
                logger.warning("Lost connection to iRacing")
                self._is_connected = False
                self.connect_button.setText("Connect")
                self._update_iracing_status(False)
            return
            
        # Only try to connect if we're not already connected and the method exists
        if hasattr(self.iracing_api, 'check_iracing'):
            try:
                is_connected = self.iracing_api.check_iracing()
                if is_connected:
                    self._is_connected = True
                    self.connect_button.setText("Disconnect")
                    self._update_iracing_status(True)
                    self.status_message.setText("Successfully connected to iRacing")
                    logger.info("Automatically connected to iRacing")
            except Exception as e:
                logger.error(f"Error checking iRacing connection: {e}")

    def _on_connect_clicked(self):
        """Handle connection button click."""
        # Check if we have a valid IRacingAPI instance
        if not hasattr(self, 'iracing_api') or self.iracing_api is None:
            logger.error("Cannot connect - no IRacingAPI instance available")
            QMessageBox.warning(self, "Connection Error", 
                "No IRacingAPI instance available. Please restart the application.")
            return
            
        # Check if this is a mock API (created as a fallback when initialization failed)
        api_class_name = self.iracing_api.__class__.__name__
        if api_class_name == 'MockIRacingAPI' or api_class_name == 'MinimalMockAPI':
            logger.warning(f"Cannot connect - using {api_class_name}")
            QMessageBox.warning(self, "Connection Error", 
                "iRacing API initialization failed. Please check if iRacing is running and try again.")
            return
            
        try:
            if self.iracing_api.is_connected():
                logger.info("Disconnect button clicked")
                self.iracing_api.disconnect()
                self.connect_button.setText("Connect")
                self._update_iracing_status(False)
            else:
                logger.info("Connect button clicked")
                logger.info("Attempting to connect to iRacing API")
                
                # Connect to iRacing API - callbacks are already registered in __init__
                connected = self.iracing_api.connect()
                
                if connected:
                    logger.info("Successfully connected to iRacing")
                    self.connect_button.setText("Disconnect")
                    self._update_iracing_status(True)
                else:
                    logger.warning("Failed to connect to iRacing - simulator may not be running")
                    QMessageBox.warning(self, "Connection Error", 
                        "Failed to connect to iRacing. Please ensure iRacing is running.")
                
                logger.info("Connection to iRacing API initiated")
        except Exception as e:
            logger.error(f"Error during connect/disconnect: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "Connection Error", 
                f"Error connecting to iRacing: {str(e)}")
    
    def _on_iracing_connected(self, is_connected, session_info):
        """Handle iRacing connection."""
        logger.info(f"iRacing connection changed: connected={is_connected}, session_info={session_info}")
        
        # Update the connection state
        self._is_connected = is_connected
        
        if is_connected:
            # Set the connection information in the UI
            logger.info("iRacing connected callback received")
            self.connect_button.setText("Disconnect")
            self._update_iracing_status(True)
            
            # Populate car and track information if available
            if session_info:
                # Extract track name
                track = session_info.get('current_track', session_info.get('track', 'Unknown Track'))
                # Extract car name
                car = session_info.get('current_car', session_info.get('car', 'Unknown Car'))
                # Extract session type
                session_type = session_info.get('session_type', 'Unknown')
                
                # Update UI
                self.track_info.setText(f"Track: {track}")
                self.car_info.setText(f"Car: {car}")
                
                # Update session type if the label exists
                if hasattr(self, 'session_type_value'):
                    self.session_type_value.setText(session_type)
                
                logger.info(f"Session info updated - Track: {track}, Car: {car}, Session: {session_type}")
            else:
                self.track_info.setText("Track: None")
                self.car_info.setText("Car: None")
                if hasattr(self, 'session_type_value'):
                    self.session_type_value.setText("Unknown")
                logger.warning("Connected but no session info available yet")
        else:
            # Handle disconnection
            self.connect_button.setText("Connect")
            self._update_iracing_status(False)
            self.track_info.setText("Track: None")
            self.car_info.setText("Car: None")
            if hasattr(self, 'session_type_value'):
                self.session_type_value.setText("Unknown")
            logger.info("iRacing disconnected")
    
    def _on_iracing_disconnected(self):
        """Handle iRacing disconnection."""
        logger.info("iRacing disconnected callback received")
        self.connect_button.setText("Connect")
        self._update_iracing_status(False)
        self.track_info.setText("Track: None")
        self.car_info.setText("Car: None")
    
    def _on_session_info_update(self, session_info):
        """Handle session info updates."""
        logger.info(f"Session info update received: {session_info}")
        
        # Check if we have valid session info
        if not session_info or not isinstance(session_info, dict):
            logger.warning("Invalid session info received")
            return
            
        # Extract track name with fallbacks
        track = session_info.get('current_track')
        if not track:
            track = session_info.get('track', 'Unknown Track')
            
        # Extract car name with fallbacks    
        car = session_info.get('current_car')
        if not car:
            car = session_info.get('car', 'Unknown Car')
            
        # Extract session type with fallbacks    
        session_type = session_info.get('session_type', 'Unknown')
        
        # Store the values in the instance
        self._current_track = track
        self._current_car = car
        self._session_type = session_type
        
        # Update the UI elements - more direct approach
        logger.info(f"Updating UI with session info - Track: {track}, Car: {car}")
        
        # Update track info label
        if hasattr(self, 'track_info'):
            self.track_info.setText(f"Track: {track}")
            logger.info(f"Updated track_info label to: {track}")
            
        # Update car info label
        if hasattr(self, 'car_info'):
            self.car_info.setText(f"Car: {car}")
            logger.info(f"Updated car_info label to: {car}")
            
        # Update session type label
        if hasattr(self, 'session_type_value'):
            self.session_type_value.setText(session_type)
            logger.info(f"Updated session_type label to: {session_type}")
            
        # Update best lap time if available
        if 'best_lap_time' in session_info and session_info['best_lap_time'] > 0:
            best_time = session_info['best_lap_time']
            formatted_time = self._format_time(best_time)
            
            if hasattr(self, 'best_lap_value'):
                self.best_lap_value.setText(formatted_time)
                logger.info(f"Updated best lap time in UI: {formatted_time}")
        
        # Update status message
        if hasattr(self, 'status_message'):
            self.status_message.setText(f"Connected to iRacing - {car} @ {track}")
            
        # Log success
        logger.info("Successfully updated UI with session info")
    
    def _on_telemetry_update(self, telemetry_data):
        """Handle telemetry data updates from iRacing by emitting a signal to the main thread.
        
        Args:
            telemetry_data (dict): Telemetry data from iRacing
        """
        try:
            # Check if widget is being destroyed
            if hasattr(self, '_is_destroying') and self._is_destroying:
                logger.debug("Widget is being destroyed, ignoring telemetry update")
                return
                
            if not telemetry_data:
                logger.warning("Received empty telemetry data")
                return
                
            # Log telemetry data occasionally
            if not hasattr(self, '_telemetry_log_counter'):
                self._telemetry_log_counter = 0
            
            self._telemetry_log_counter += 1
            if self._telemetry_log_counter % 100 == 0:  # Log every ~10 seconds
                # Create a sanitized version for logging (only key values)
                log_data = {
                    'speed': telemetry_data.get('speed', 0),
                    'rpm': telemetry_data.get('rpm', 0),
                    'gear': telemetry_data.get('gear', 0),
                    'throttle': telemetry_data.get('throttle', 0),
                    'brake': telemetry_data.get('brake', 0),
                    'lap_time': telemetry_data.get('lap_time', 0),
                    'last_lap_time': telemetry_data.get('last_lap_time', 0),
                    'best_lap_time': telemetry_data.get('best_lap_time', 0),
                }
                logger.debug(f"Telemetry update: {log_data}")
            
            # Make a defensive copy of the telemetry data
            telemetry_copy = telemetry_data.copy() if isinstance(telemetry_data, dict) else telemetry_data
            
            # CRITICAL SAFETY CHECK: Use try-except to catch the case where the widget is deleted
            # This is a more robust way to handle the case where the C++ object is deleted
            try:
                # Double-check that the widget is still valid by accessing a Qt property
                # This will raise an exception if the C++ object is deleted
                _ = self.objectName()
                
                # Only emit signal if widget still exists and is not being destroyed
                if not self._is_destroying:
                    self.telemetry_update_signal.emit(telemetry_copy)
            except RuntimeError as e:
                # If we get here, the Qt C++ object has been deleted
                if "has been deleted" in str(e):
                    # Use a class variable to only log this message once
                    if not hasattr(RaceCoachWidget, '_widget_deleted_logged'):
                        logger.debug("Qt widget already deleted, skipping telemetry update (subsequent similar messages suppressed)")
                        # Set class variable to indicate we've logged this message
                        RaceCoachWidget._widget_deleted_logged = True
                else:
                    # Re-raise other runtime errors
                    raise
            
        except Exception as e:
            logger.error(f"Error in telemetry update handler: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't re-raise the exception - we want to keep the telemetry handler running

    def _update_iracing_status(self, connected):
        """Update iRacing connection status in UI."""
        if connected:
            self.iracing_status.setText("iRacing: Connected")
            self.iracing_status.setStyleSheet("""
                QLabel {
                    padding: 8px 15px;
                    border-radius: 6px;
                    font-weight: bold;
                    background-color: #4CAF50;
                    color: white;
                    font-size: 12pt;
                }
            """)
            logger.info("Updated UI to show iRacing connected")
        else:
            self.iracing_status.setText("iRacing: Not Connected")
            self.iracing_status.setStyleSheet("""
                QLabel {
                    padding: 8px 15px;
                    border-radius: 6px;
                    font-weight: bold;
                    background-color: #FF5252;
                    color: white;
                    font-size: 12pt;
                }
            """)
            logger.info("Updated UI to show iRacing disconnected")
    
    def _update_telemetry_display(self, telemetry_data):
        """Update the telemetry display widgets with the latest data.
        
        Args:
            telemetry_data (dict): Telemetry data from iRacing
        """
        # Verify required data is present
        if not telemetry_data:
            return
            
        try:
            # Check if we have driver input data and log it
            has_driver_inputs = all(key in telemetry_data for key in ['throttle', 'brake', 'clutch'])
            if has_driver_inputs and (not hasattr(self, '_last_inputs_log') or time.time() - self._last_inputs_log > 10):
                logger.info(f"Received driver inputs: Throttle={telemetry_data.get('throttle', 0):.2f}, "
                           f"Brake={telemetry_data.get('brake', 0):.2f}, "
                           f"Clutch={telemetry_data.get('clutch', 0):.2f}")
                self._last_inputs_log = time.time()
            
            # Log when we're actually updating the display (for debugging)
            has_speed = 'speed' in telemetry_data and telemetry_data['speed'] > 0
            if has_speed and (not hasattr(self, '_last_display_update') or time.time() - self._last_display_update > 5):
                logger.info(f"Updating telemetry display with speed: {telemetry_data.get('speed', 0):.1f} km/h")
                self._last_display_update = time.time()
                
            # Update speed value directly in labels
            speed = telemetry_data.get('speed', 0)
            if isinstance(speed, (int, float)):
                # Update speed value text
                if hasattr(self, 'speed_value'):
                    self.speed_value.setText(f"{speed:.1f} km/h")
                    logger.debug(f"Updated speed label to {speed:.1f} km/h")
                
                # Also update speed gauge if it exists
                if hasattr(self, 'speed_gauge'):
                    self.speed_gauge.set_value(speed)
            
            # Update RPM value directly in labels
            rpm = telemetry_data.get('rpm', 0)
            if isinstance(rpm, (int, float)):
                # Update RPM value text
                if hasattr(self, 'rpm_value'):
                    self.rpm_value.setText(f"{rpm:.0f}")
                    logger.debug(f"Updated RPM label to {rpm:.0f}")
                
                # Also update RPM gauge if it exists
                if hasattr(self, 'rpm_gauge'):
                    self.rpm_gauge.set_value(rpm)
            
            # Update gear display
            gear = telemetry_data.get('gear', 0)
            if isinstance(gear, (int, float)):
                # Convert gear number to display format
                if gear == 0:
                    gear_display = "N"
                elif gear == -1:
                    gear_display = "R"
                else:
                    gear_display = str(gear)
                
                # Update gear display text
                if hasattr(self, 'gear_value'):
                    self.gear_value.setText(gear_display)
                    logger.debug(f"Updated gear display to {gear_display}")
            
            # Update driver input displays - Throttle, Brake, Clutch
            # Extract input values with defaults
            throttle = telemetry_data.get('throttle', 0)
            brake = telemetry_data.get('brake', 0)
            clutch = telemetry_data.get('clutch', 0)
            
            # Ensure values are numerical
            if isinstance(throttle, (int, float)) and isinstance(brake, (int, float)) and isinstance(clutch, (int, float)):
                # Update input trace widget if it exists
                if hasattr(self, 'input_trace'):
                    logger.debug(f"Adding data points to input trace: T={throttle:.2f}, B={brake:.2f}, C={clutch:.2f}")
                    self.input_trace.add_data_point(throttle, brake, clutch)
                    # No need to force repaint - the widget handles this safely now
                
                # Update throttle display
                throttle_pct = int(throttle * 100)
                if hasattr(self, 'throttle_value'):
                    self.throttle_value.setText(f"{throttle_pct}%")
                    # No need for forced repaint
                    logger.debug(f"Updated throttle display to {throttle_pct}%")
                if hasattr(self, 'throttle_bar'):
                    self.throttle_bar.setValue(throttle_pct)
                    # No need for forced repaint
                
                # Update brake display
                brake_pct = int(brake * 100)
                if hasattr(self, 'brake_value'):
                    self.brake_value.setText(f"{brake_pct}%")
                    # No need for forced repaint
                    logger.debug(f"Updated brake display to {brake_pct}%")
                if hasattr(self, 'brake_bar'):
                    self.brake_bar.setValue(brake_pct)
                    # No need for forced repaint
                
                # Update clutch display
                clutch_pct = int(clutch * 100)
                if hasattr(self, 'clutch_value'):
                    self.clutch_value.setText(f"{clutch_pct}%")
                    # No need for forced repaint
                    logger.debug(f"Updated clutch display to {clutch_pct}%")
                if hasattr(self, 'clutch_bar'):
                    self.clutch_bar.setValue(clutch_pct)
                    # No need for forced repaint
            
            # Ensure the parent widget gets updated too
            if hasattr(self, 'throttle_bar') or hasattr(self, 'brake_bar') or hasattr(self, 'clutch_bar'):
                # No need to force parent updates - Qt will handle this
                pass
            
            # Update current lap time information
            lap_time = telemetry_data.get('lap_time', 0)
            if lap_time and lap_time > 0:
                formatted_time = self._format_time(lap_time)
                if hasattr(self, 'lap_time_value'):
                    self.lap_time_value.setText(formatted_time)
                    logger.debug(f"Updated current lap time to {formatted_time}")
            
            # Update last lap time information
            last_lap_time = telemetry_data.get('last_lap_time', 0)
            if last_lap_time and last_lap_time > 0:
                formatted_time = self._format_time(last_lap_time)
                if hasattr(self, 'last_lap_value'):
                    self.last_lap_value.setText(formatted_time)
                    if not hasattr(self, '_last_displayed_lap_time') or self._last_displayed_lap_time != last_lap_time:
                        logger.info(f"Updated last lap time to {formatted_time}")
                        self._last_displayed_lap_time = last_lap_time
            
            # Update best lap time information
            best_lap_time = telemetry_data.get('best_lap_time', 0)
            if best_lap_time and best_lap_time > 0:
                formatted_time = self._format_time(best_lap_time)
                if hasattr(self, 'best_lap_value'):
                    self.best_lap_value.setText(formatted_time)
                    if not hasattr(self, '_best_displayed_lap_time') or self._best_displayed_lap_time != best_lap_time:
                        logger.info(f"Updated best lap time to {formatted_time}")
                        self._best_displayed_lap_time = best_lap_time
            
            # Update lap count if available
            lap_count = telemetry_data.get('lap_count', 0)
            if lap_count and lap_count > 0:
                if hasattr(self, 'lap_info'):
                    self.lap_info.setText(str(lap_count))
                    if not hasattr(self, '_last_displayed_lap_count') or self._last_displayed_lap_count != lap_count:
                        logger.info(f"Updated lap count to {lap_count}")
                        self._last_displayed_lap_count = lap_count
            
            # Update status message occasionally
            if hasattr(self, 'status_message') and has_speed:
                # Create a more detailed status message if we have lap times
                if best_lap_time and best_lap_time > 0:
                    best_time_str = self._format_time(best_lap_time)
                    self.status_message.setText(f"Telemetry: Speed {speed:.1f} km/h, Best Lap: {best_time_str}")
                else:
                    self.status_message.setText(f"Receiving telemetry data - Speed: {speed:.1f} km/h, RPM: {rpm:.0f}")
                
        except Exception as e:
            logger.error(f"Error updating telemetry display: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def connect_to_iracing(self):
        """Compatibility method that forwards to _on_connect_clicked."""
        logger.warning("Using deprecated connect_to_iracing method - update to _on_connect_clicked")
        if hasattr(self, '_on_connect_clicked'):
            try:
                self._on_connect_clicked()
            except Exception as e:
                logger.error(f"Error in connect_to_iracing compatibility method: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
    def on_iracing_connected(self, track=None, car=None):
        """Compatibility method that forwards to _on_iracing_connected."""
        logger.warning("Using deprecated on_iracing_connected method - update to _on_iracing_connected")
        if hasattr(self, '_on_iracing_connected'):
            # Create a minimal session info dict with track and car info
            session_info = {}
            if track:
                session_info['track'] = track
            if car:
                session_info['car'] = car
            self._on_iracing_connected(True, session_info)

    def on_iracing_disconnected(self):
        """Compatibility method that forwards to _on_iracing_disconnected."""
        logger.warning("Using deprecated on_iracing_disconnected method - update to _on_iracing_disconnected")
        if hasattr(self, '_on_iracing_disconnected'):
            self._on_iracing_disconnected()

    def on_telemetry_update(self, telemetry_data):
        """Compatibility method that forwards to _on_telemetry_update."""
        logger.warning("Using deprecated on_telemetry_update method - update to _on_telemetry_update")
        if hasattr(self, '_on_telemetry_update'):
            self._on_telemetry_update(telemetry_data)

    def on_session_info_update(self, session_info):
        """Compatibility method that forwards to _on_session_info_update."""
        logger.warning("Using deprecated on_session_info_update method - update to _on_session_info_update")
        if hasattr(self, '_on_session_info_update'):
            self._on_session_info_update(session_info)

    def _format_time(self, seconds):
        """Format a time value in seconds to a readable string.
        
        Args:
            seconds (float): Time in seconds
            
        Returns:
            str: Formatted time string (M:SS.mmm)
        """
        if not seconds or seconds <= 0:
            return "0:00.000"
            
        minutes = int(seconds / 60)
        remaining_seconds = seconds - (minutes * 60)
        
        return f"{minutes}:{remaining_seconds:06.3f}"

    def _on_debug_button_clicked(self):
        """Handle the debug button click to explore iRacing variables."""
        logger.info("Debug button clicked - exploring iRacing variables")
        
        try:
            # Detailed diagnostic of the iracing_api attribute
            if not hasattr(self, 'iracing_api'):
                logger.error("Widget has no 'iracing_api' attribute at all")
                QMessageBox.warning(self, "Debug Error", 
                                   "No 'iracing_api' attribute found in the widget. Implementation error.")
                return
                
            if self.iracing_api is None:
                logger.error("iracing_api attribute exists but is None")
                # Try to recover by creating a mock API on the fly
                try:
                    from trackpro.race_coach import MockIRacingAPI
                    self.iracing_api = MockIRacingAPI()
                    logger.info("Created emergency MockIRacingAPI in debug button handler")
                    QMessageBox.information(self, "Debug Information", 
                        "Created emergency MockIRacingAPI. Limited functionality available.")
                except ImportError:
                    logger.error("Cannot import MockIRacingAPI - unable to recover")
                    QMessageBox.warning(self, "Debug Error", 
                        "The iRacing API is not available and recovery failed. Please restart the application.")
                    return
            
            # Get the API class name and details for better diagnostics
            api_class_name = self.iracing_api.__class__.__name__ if hasattr(self.iracing_api, '__class__') else 'Unknown'
            api_methods = [method for method in dir(self.iracing_api) if not method.startswith('_') and callable(getattr(self.iracing_api, method))]
            logger.info(f"Debug using API class: {api_class_name} with methods: {api_methods}")
                
            # Check if this is a mock API
            if api_class_name in ['MockIRacingAPI', 'MinimalMockAPI', 'EmergencyMockAPI']:
                logger.warning(f"Using {api_class_name} for debug - limited functionality")
                
                # Get mock variables if available
                if hasattr(self.iracing_api, 'explore_telemetry_variables') and callable(self.iracing_api.explore_telemetry_variables):
                    mock_vars = self.iracing_api.explore_telemetry_variables()
                    logger.info(f"Mock API variables: {mock_vars}")
                    
                QMessageBox.information(self, "Debug Information", 
                    f"Using {api_class_name} mock API. Real telemetry data is not available.\n\n"
                    "This happens when the iRacing API cannot be initialized. Check if iRacing is installed correctly.")
                return
    
            # Check if connected to iRacing
            if not self.iracing_api.is_connected():
                logger.error("Cannot explore variables - not connected to iRacing")
                QMessageBox.warning(self, "Debug Error", "Not connected to iRacing. Please connect first.")
                return
                
            # Start a separate thread to explore variables
            def explore_thread():
                try:
                    logger.info("Starting variable exploration")
                    # Call the explore method
                    variables = self.iracing_api.explore_telemetry_variables()
                    
                    # Show a message with the results
                    num_vars = sum(len(category) for category in variables.values())
                    logger.info(f"Variable exploration complete. Found {num_vars} variables.")
                    
                    # Log the variables categorized by type
                    for category, vars_dict in variables.items():
                        if vars_dict:
                            logger.info(f"{category.upper()} variables ({len(vars_dict)}):")
                            for var_name, value in vars_dict.items():
                                logger.info(f"  {var_name} = {value}")
                
                except Exception as e:
                    logger.error(f"Error exploring variables: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Create and start the thread
            self._exploration_thread = threading.Thread(target=explore_thread)
            self._exploration_thread.daemon = True
            self._exploration_thread.start()
            
            # Show a message to the user
            QMessageBox.information(self, "Debug Mode", 
                "Exploring iRacing variables in the background. Check the logs for results.")
                
        except Exception as e:
            logger.error(f"Error in debug button handler: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "Debug Error", f"An error occurred: {str(e)}")
    
    def _on_analyze_checkbox_changed(self, state):
        """Handle changes to the auto-analyze checkbox."""
        self._analyze_telemetry = (state == Qt.Checked)
        logger.info(f"Auto-analyze telemetry set to: {self._analyze_telemetry}")

    # Now create a new method that will be called on the main thread
    def _on_telemetry_update_main_thread(self, telemetry_data):
        """Handle telemetry updates on the main thread for thread-safe UI updates.
        This method is connected to our signal and will run on the main Qt thread.
        
        Args:
            telemetry_data (dict): Telemetry data from iRacing
        """
        try:
            # Skip if widget is being destroyed
            if hasattr(self, '_is_destroying') and self._is_destroying:
                logger.debug("Widget is being destroyed, ignoring main thread telemetry update")
                return
                
            # Just call the existing method with the data
            self._update_telemetry_display(telemetry_data)
            
            # Also store the data for our monitoring timer
            self._latest_telemetry = telemetry_data
            
            # Analyze the telemetry data if analysis is enabled and we have a lap_analysis object
            if hasattr(self, '_analyze_telemetry') and self._analyze_telemetry and hasattr(self, 'lap_analysis') and self.lap_analysis:
                try:
                    # Use a background thread for analysis to avoid blocking the UI
                    def analyze_in_thread(data):
                        try:
                            self.lap_analysis.process_telemetry(data)
                        except Exception as e:
                            logger.error(f"Error in telemetry analysis thread: {e}")
                    
                    # Create and start analysis thread
                    analysis_thread = threading.Thread(target=analyze_in_thread, args=(telemetry_data.copy(),))
                    analysis_thread.daemon = True
                    analysis_thread.start()
                except Exception as e:
                    logger.error(f"Failed to start analysis thread: {e}")
        except Exception as e:
            logger.error(f"Error in telemetry update main thread handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def closeEvent(self, event):
        """Override closeEvent to properly handle widget destruction."""
        logger.info("RaceCoachWidget closing, performing cleanup...")
        self._is_destroying = True
        
        # Disconnect signals first to prevent threading issues
        try:
            # First disconnect our signal to prevent further UI updates
            logger.info("Disconnecting telemetry update signal")
            self.telemetry_update_signal.disconnect()
        except Exception as e:
            logger.debug(f"Failed to disconnect signal: {e}")
            
        # Unregister callbacks from iracing_api
        if hasattr(self, 'iracing_api') and self.iracing_api is not None:
            try:
                logger.info("Unregistering callbacks from iRacing API")
                # Try to unregister callbacks - implementation depends on API design
                if hasattr(self.iracing_api, 'unregister_callbacks'):
                    self.iracing_api.unregister_callbacks()
                elif hasattr(self.iracing_api, 'unregister_on_telemetry_data'):
                    self.iracing_api.unregister_on_telemetry_data(self._safe_telemetry_callback)
            except Exception as e:
                logger.debug(f"Failed to unregister callbacks: {e}")
        
        # Stop monitoring timer
        if hasattr(self, 'monitor_timer') and self.monitor_timer is not None:
            logger.info("Stopping monitoring timer")
            self.monitor_timer.stop()
        
        # Disconnect from iRacing if connected
        if hasattr(self, 'iracing_api') and self.iracing_api is not None:
            if hasattr(self.iracing_api, 'is_connected') and self.iracing_api.is_connected():
                logger.info("Disconnecting from iRacing during cleanup")
                try:
                    self.iracing_api.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting from iRacing during cleanup: {e}")
        
        # Stop connection check timer
        if hasattr(self, 'connection_check_timer') and self.connection_check_timer is not None:
            logger.info("Stopping connection check timer")
            self.connection_check_timer.stop()
            
        logger.info("RaceCoachWidget cleanup completed")
        super().closeEvent(event)
        
    def __del__(self):
        """Destructor method to handle widget deletion."""
        try:
            logger.info("RaceCoachWidget being deleted")
            self._is_destroying = True
        except:
            # Avoid any exceptions in destructor
            pass 

    def _create_safe_telemetry_callback(self):
        """Create a thread-safe callback for telemetry data that won't crash if widget is deleted."""
        # Create a weak reference to self
        weak_self = weakref.ref(self)
        
        # Define a closure that uses the weak reference
        def safe_callback(telemetry_data):
            # Get the actual object from the weak reference
            self_obj = weak_self()
            # Only process if the object still exists
            if self_obj is not None and not getattr(self_obj, '_is_destroying', False):
                try:
                    self_obj._on_telemetry_update(telemetry_data)
                except Exception as e:
                    logger.error(f"Error in safe telemetry callback: {e}")
            else:
                logger.debug("Widget no longer exists, skipping telemetry update")
        
        return safe_callback 