import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTabWidget, QGroupBox,
                             QSplitter, QComboBox, QStatusBar, QMainWindow, QMessageBox, QApplication, QGridLayout, QFrame, QFormLayout, QCheckBox, QProgressBar, QSizePolicy, QSpacerItem, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QConicalGradient
import time
import threading
import weakref
import numpy as np  # Add numpy import for array handling
import json
import platform
import math
from datetime import datetime
from pathlib import Path  # Add Path import for file handling

# Try to import QPointF and QRectF from QtCore
try:
    from PyQt5.QtCore import QPointF, QRectF, QSizeF
except ImportError:
    # Define fallback classes if imports fail
    class QPointF:
        """Simple replacement for QPointF when not available."""
        def __init__(self, x, y):
            self._x = x
            self._y = y
            
        def x(self):
            return self._x
            
        def y(self):
            return self._y
            
    class QRectF:
        """Simple replacement for QRectF when not available."""
        def __init__(self, *args):
            if len(args) == 4:  # (x, y, width, height)
                self._x = args[0]
                self._y = args[1]
                self._width = args[2]
                self._height = args[3]
            elif len(args) == 2:  # (QPointF, QSizeF)
                point, size = args
                self._x = point.x() if hasattr(point, 'x') and callable(point.x) else point.x
                self._y = point.y() if hasattr(point, 'y') and callable(point.y) else point.y
                self._width = size.width() if hasattr(size, 'width') and callable(size.width) else size.width
                self._height = size.height() if hasattr(size, 'height') and callable(size.height) else size.height
            else:
                raise TypeError("QRectF requires either (x, y, width, height) or (QPointF, QSizeF)")
            
        def left(self):
            return self._x
            
        def top(self):
            return self._y
            
        def width(self):
            return self._width
            
        def height(self):
            return self._height
    
    class QSizeF:
        """Simple replacement for QSizeF when not available."""
        def __init__(self, width, height):
            self._width = width
            self._height = height
            
        def width(self):
            return self._width
            
        def height(self):
            return self._height

# Try to import QPainterPath
try:
    from PyQt5.QtGui import QPainterPath
except ImportError:
    # This is more complex to replace, might need more involved fallback
    class QPainterPath:
        """Simple replacement for QPainterPath - limited functionality."""
        def __init__(self):
            self._points = []
            self._current_point = (0, 0)
            
        def moveTo(self, x, y=None):
            """Move to position without drawing a line."""
            if y is None and isinstance(x, (QPointF, tuple)):
                # Handle QPointF or tuple
                if isinstance(x, QPointF):
                    x_val = x.x() if callable(x.x) else x.x
                    y_val = x.y() if callable(x.y) else x.y
                else:
                    x_val, y_val = x
            else:
                x_val, y_val = x, y
                
            self._current_point = (x_val, y_val)
            self._points = [self._current_point]
            
        def lineTo(self, x, y=None):
            """Draw line from current position to specified point."""
            if y is None and isinstance(x, (QPointF, tuple)):
                # Handle QPointF or tuple
                if isinstance(x, QPointF):
                    x_val = x.x() if callable(x.x) else x.x
                    y_val = x.y() if callable(x.y) else x.y
                else:
                    x_val, y_val = x
            else:
                x_val, y_val = x, y
                
            self._current_point = (x_val, y_val)
            self._points.append(self._current_point)
            
        def closeSubpath(self):
            """Close the current subpath by drawing a line to the beginning point."""
            if self._points and len(self._points) > 0:
                self._points.append(self._points[0])
                self._current_point = self._points[0]
                
        def isEmpty(self):
            """Return True if the path contains no elements."""
            return len(self._points) == 0
            
        def elementCount(self):
            """Return the number of path elements."""
            return len(self._points)

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
        
        # Enforce minimum size for proper rendering
        if width < 100 or height < 50:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.background_color))
            painter.drawRect(0, 0, width, height)
            
            # Draw a simple horizontal bar for speed
            normalized = self.get_normalized_value()
            if normalized > 0:
                fill_width = int(normalized * width)
                
                # Simple gradient from blue to red
                gradient = QLinearGradient(0, 0, width, 0)
                gradient.setColorAt(0, self.low_speed_color)
                gradient.setColorAt(1, self.high_speed_color)
                
                painter.setBrush(QBrush(gradient))
                painter.drawRect(0, 0, fill_width, height)
            
            # Add basic speed text if there's enough room
            if width >= 40 and height >= 20:
                painter.setPen(QPen(self.text_color))
                painter.drawText(0, 0, width, height, Qt.AlignCenter, f"{self.value:.0f}")
            
            return
        
        # Regular rendering for normal sizes
        # Calculate dimensions
        padding = max(5, min(10, width / 20))  # Adaptive padding
        gauge_width = width - (padding * 2)
        gauge_height = max(10, min(30, height / 5))  # Adaptive height
        
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
        
        # Draw title if there's enough room
        if height >= 80:
            title_font = painter.font()
            title_font.setPointSize(max(8, min(12, width / 20)))  # Adaptive font size
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QPen(self.text_color))
            painter.drawText(padding, padding, gauge_width, 30, 
                            Qt.AlignLeft | Qt.AlignVCenter, self.title)
        
        # Draw value with adaptive font size
        value_font = painter.font()
        value_font.setPointSize(max(10, min(22, width / 10)))  # Adaptive font size
        value_font.setBold(True)
        painter.setFont(value_font)
        value_text = f"{self.value:.1f} {self.units}"
        painter.drawText(padding, 40, gauge_width, 50, 
                        Qt.AlignCenter, value_text)
        
        # Only draw tick marks if there's enough room
        if width >= 200 and height >= 100:
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
        
        # Enforce minimum size for proper rendering
        if width < 100 or height < 100:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.background_color))
            painter.drawRect(0, 0, width, height)
            
            # Draw a simple arc for RPM if possible
            if width >= 40 and height >= 40:
                center_x = width / 2
                center_y = height / 2
                radius = min(width, height) / 2 - 2
                
                # Draw background arc
                arc_rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
                painter.setPen(QPen(self.text_color.darker(120), 2))
                painter.drawArc(arc_rect, 135 * 16, 270 * 16)
                
                # Draw filled arc for current RPM
                normalized = self.get_normalized_value()
                if normalized > 0:
                    redline_normalized = (self.redline - self.min_value) / (self.max_value - self.min_value)
                    
                    # Determine color based on whether RPM is approaching redline
                    if normalized < redline_normalized * 0.8:
                        gauge_color = QColor(0, 150, 200)  # Blue for normal operation
                    elif normalized < redline_normalized:
                        gauge_color = QColor(255, 150, 0)  # Orange for approaching redline
                    else:
                        gauge_color = QColor(255, 50, 50)  # Red for at/beyond redline
                        
                    # Draw filled arc
                    painter.setPen(QPen(gauge_color, 2, Qt.SolidLine, Qt.RoundCap))
                    span = normalized * 270
                    painter.drawArc(arc_rect, 135 * 16, int(span * 16))
            
            # Add basic RPM text
            painter.setPen(QPen(self.text_color))
            rpm_text = f"{self.value/1000:.1f}k"
            painter.drawText(0, 0, width, height, Qt.AlignCenter, rpm_text)
            
            return
        
        # Regular rendering for normal sizes
        # Calculate dimensions and center point
        margin = max(5, min(10, width / 20))  # Adaptive margin
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - margin
        
        # Draw gauge background - arc from 135° to 405° (270° span)
        start_angle = 135
        span_angle = 270
        arc_rect = QRectF(QPointF(center_x - radius, center_y - radius), QSizeF(radius * 2, radius * 2))
        
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
            pen_width = max(5, min(10, width / 30))  # Adaptive pen width
            painter.setPen(QPen(gauge_color, pen_width, Qt.SolidLine, Qt.RoundCap))
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
        title_rect = QRectF(arc_rect.left(), arc_rect.top() + arc_rect.height() // 2 + 10,
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

class TelemetryComparisonWidget(QWidget):
    """Widget to display F1-style telemetry comparison between two laps."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TelemetryComparisonWidget")
        
        # Initialize data attributes first to prevent attribute errors
        self.speed_data_left = []
        self.speed_data_right = []
        self.delta_data = []
        self.track_map_points = []
        self.track_turns = {}  # Dictionary mapping turn numbers to positions on track
        self.track_sectors = {}  # For sector classifications (low/medium/high speed)
        
        # Store data for both drivers/laps
        self.left_driver = {
            "name": "",
            "team": "",
            "position": "",
            "lap_time": 0.0,  # in seconds
            "gap": 0.0,       # in seconds (negative means faster)
            "full_throttle": 0,  # percentage
            "heavy_braking": 0,  # percentage
            "cornering": 0,      # percentage
            "color": QColor(255, 0, 0)  # red for left driver (like Leclerc)
        }
        
        self.right_driver = {
            "name": "",
            "team": "",
            "position": "",
            "lap_time": 0.0,
            "gap": 0.0,
            "full_throttle": 0,
            "heavy_braking": 0,
            "cornering": 0,
            "color": QColor(255, 215, 0)  # gold for right driver (like Sainz)
        }
        
        # UI setup
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the comparison layout UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Top section: Driver comparison and track map
        top_section = QHBoxLayout()
        
        # Left driver section
        left_driver_widget = QWidget()
        left_driver_layout = QVBoxLayout(left_driver_widget)
        left_driver_layout.setContentsMargins(10, 10, 10, 10)
        left_driver_layout.setSpacing(5)
        
        # Driver position and name
        left_position_layout = QHBoxLayout()
        self.left_position_label = QLabel("1")
        self.left_position_label.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: white;
        """)
        
        left_driver_info = QVBoxLayout()
        self.left_driver_name = QLabel("CHARLES")
        self.left_driver_name.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        
        self.left_driver_lastname = QLabel("LECLERC")
        self.left_driver_lastname.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #FF0000;
        """)
        
        self.left_driver_team = QLabel("FERRARI")
        self.left_driver_team.setStyleSheet("""
            font-size: 12px;
            color: white;
        """)
        
        left_driver_info.addWidget(self.left_driver_name)
        left_driver_info.addWidget(self.left_driver_lastname)
        left_driver_info.addWidget(self.left_driver_team)
        
        left_position_layout.addWidget(self.left_position_label)
        left_position_layout.addLayout(left_driver_info)
        left_driver_layout.addLayout(left_position_layout)
        
        # Driver lap time and gap
        left_time_layout = QHBoxLayout()
        
        left_time_header = QLabel("LAP TIME")
        left_time_header.setStyleSheet("font-size: 12px; color: gray;")
        
        self.left_lap_time = QLabel("1:23.456")
        self.left_lap_time.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        left_time_column = QVBoxLayout()
        left_time_column.addWidget(left_time_header)
        left_time_column.addWidget(self.left_lap_time)
        
        left_gap_header = QLabel("GAP")
        left_gap_header.setStyleSheet("font-size: 12px; color: gray;")
        
        self.left_gap = QLabel("-0.321s")
        self.left_gap.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        left_gap_column = QVBoxLayout()
        left_gap_column.addWidget(left_gap_header)
        left_gap_column.addWidget(self.left_gap)
        
        left_time_layout.addLayout(left_time_column)
        left_time_layout.addLayout(left_gap_column)
        left_driver_layout.addLayout(left_time_layout)
        
        # Driver statistics
        left_stats_layout = QVBoxLayout()
        
        # Full throttle
        left_throttle_header = QLabel("FULL THROTTLE")
        left_throttle_header.setStyleSheet("font-size: 10px; color: gray;")
        
        left_throttle_layout = QHBoxLayout()
        left_throttle_bar = QProgressBar()
        left_throttle_bar.setRange(0, 100)
        left_throttle_bar.setValue(80)
        left_throttle_bar.setTextVisible(False)
        left_throttle_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #FF0000;
                border-radius: 5px;
            }
        """)
        
        self.left_throttle_value = QLabel("81%")
        self.left_throttle_value.setStyleSheet("font-size: 12px; color: white;")
        
        left_throttle_layout.addWidget(left_throttle_bar)
        left_throttle_layout.addWidget(self.left_throttle_value)
        
        # Heavy braking
        left_braking_header = QLabel("HEAVY BRAKING")
        left_braking_header.setStyleSheet("font-size: 10px; color: gray;")
        
        left_braking_layout = QHBoxLayout()
        left_braking_bar = QProgressBar()
        left_braking_bar.setRange(0, 100)
        left_braking_bar.setValue(5)
        left_braking_bar.setTextVisible(False)
        left_braking_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #FF0000;
                border-radius: 5px;
            }
        """)
        
        self.left_braking_value = QLabel("5%")
        self.left_braking_value.setStyleSheet("font-size: 12px; color: white;")
        
        left_braking_layout.addWidget(left_braking_bar)
        left_braking_layout.addWidget(self.left_braking_value)
        
        # Cornering
        left_cornering_header = QLabel("CORNERING")
        left_cornering_header.setStyleSheet("font-size: 10px; color: gray;")
        
        left_cornering_layout = QHBoxLayout()
        left_cornering_bar = QProgressBar()
        left_cornering_bar.setRange(0, 100)
        left_cornering_bar.setValue(14)
        left_cornering_bar.setTextVisible(False)
        left_cornering_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #FF0000;
                border-radius: 5px;
            }
        """)
        
        self.left_cornering_value = QLabel("14%")
        self.left_cornering_value.setStyleSheet("font-size: 12px; color: white;")
        
        left_cornering_layout.addWidget(left_cornering_bar)
        left_cornering_layout.addWidget(self.left_cornering_value)
        
        left_stats_layout.addWidget(left_throttle_header)
        left_stats_layout.addLayout(left_throttle_layout)
        left_stats_layout.addWidget(left_braking_header)
        left_stats_layout.addLayout(left_braking_layout)
        left_stats_layout.addWidget(left_cornering_header)
        left_stats_layout.addLayout(left_cornering_layout)
        
        left_driver_layout.addLayout(left_stats_layout)
        
        # CENTRAL TRACK MAP PLACEHOLDER
        track_map_widget = QWidget()
        track_map_widget.setMinimumSize(350, 200)
        track_map_widget.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)
        
        # No layout or label needed, just an empty space that paintEvent will draw on
        
        # RIGHT DRIVER SECTION (mirror of left)
        right_driver_widget = QWidget()
        right_driver_layout = QVBoxLayout(right_driver_widget)
        right_driver_layout.setContentsMargins(10, 10, 10, 10)
        right_driver_layout.setSpacing(5)
        
        # Driver position and name
        right_position_layout = QHBoxLayout()
        self.right_position_label = QLabel("2")
        self.right_position_label.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: white;
        """)
        
        right_driver_info = QVBoxLayout()
        self.right_driver_name = QLabel("CARLOS")
        self.right_driver_name.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        
        self.right_driver_lastname = QLabel("SAINZ")
        self.right_driver_lastname.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #FFD700;
        """)
        
        self.right_driver_team = QLabel("FERRARI")
        self.right_driver_team.setStyleSheet("""
            font-size: 12px;
            color: white;
        """)
        
        right_driver_info.addWidget(self.right_driver_name)
        right_driver_info.addWidget(self.right_driver_lastname)
        right_driver_info.addWidget(self.right_driver_team)
        
        right_position_layout.addLayout(right_driver_info)
        right_position_layout.addWidget(self.right_position_label)
        right_driver_layout.addLayout(right_position_layout)
        
        # Driver lap time and gap
        right_time_layout = QHBoxLayout()
        
        right_gap_header = QLabel("GAP")
        right_gap_header.setStyleSheet("font-size: 12px; color: gray;")
        
        self.right_gap = QLabel("+0.321s")
        self.right_gap.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        right_gap_column = QVBoxLayout()
        right_gap_column.addWidget(right_gap_header)
        right_gap_column.addWidget(self.right_gap)
        
        right_time_header = QLabel("LAP TIME")
        right_time_header.setStyleSheet("font-size: 12px; color: gray;")
        
        self.right_lap_time = QLabel("1:23.777")
        self.right_lap_time.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        right_time_column = QVBoxLayout()
        right_time_column.addWidget(right_time_header)
        right_time_column.addWidget(self.right_lap_time)
        
        right_time_layout.addLayout(right_gap_column)
        right_time_layout.addLayout(right_time_column)
        right_driver_layout.addLayout(right_time_layout)
        
        # Driver statistics
        right_stats_layout = QVBoxLayout()
        
        # Full throttle
        right_throttle_header = QLabel("FULL THROTTLE")
        right_throttle_header.setStyleSheet("font-size: 10px; color: gray;")
        
        right_throttle_layout = QHBoxLayout()
        self.right_throttle_value = QLabel("81%")
        self.right_throttle_value.setStyleSheet("font-size: 12px; color: white;")
        
        right_throttle_bar = QProgressBar()
        right_throttle_bar.setRange(0, 100)
        right_throttle_bar.setValue(80)
        right_throttle_bar.setTextVisible(False)
        right_throttle_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #FFD700;
                border-radius: 5px;
            }
        """)
        
        right_throttle_layout.addWidget(self.right_throttle_value)
        right_throttle_layout.addWidget(right_throttle_bar)
        
        # Heavy braking
        right_braking_header = QLabel("HEAVY BRAKING")
        right_braking_header.setStyleSheet("font-size: 10px; color: gray;")
        
        right_braking_layout = QHBoxLayout()
        self.right_braking_value = QLabel("5%")
        self.right_braking_value.setStyleSheet("font-size: 12px; color: white;")
        
        right_braking_bar = QProgressBar()
        right_braking_bar.setRange(0, 100)
        right_braking_bar.setValue(5)
        right_braking_bar.setTextVisible(False)
        right_braking_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #FFD700;
                border-radius: 5px;
            }
        """)
        
        right_braking_layout.addWidget(self.right_braking_value)
        right_braking_layout.addWidget(right_braking_bar)
        
        # Cornering
        right_cornering_header = QLabel("CORNERING")
        right_cornering_header.setStyleSheet("font-size: 10px; color: gray;")
        
        right_cornering_layout = QHBoxLayout()
        self.right_cornering_value = QLabel("14%")
        self.right_cornering_value.setStyleSheet("font-size: 12px; color: white;")
        
        right_cornering_bar = QProgressBar()
        right_cornering_bar.setRange(0, 100)
        right_cornering_bar.setValue(14)
        right_cornering_bar.setTextVisible(False)
        right_cornering_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #FFD700;
                border-radius: 5px;
            }
        """)
        
        right_cornering_layout.addWidget(self.right_cornering_value)
        right_cornering_layout.addWidget(right_cornering_bar)
        
        right_stats_layout.addWidget(right_throttle_header)
        right_stats_layout.addLayout(right_throttle_layout)
        right_stats_layout.addWidget(right_braking_header)
        right_stats_layout.addLayout(right_braking_layout)
        right_stats_layout.addWidget(right_cornering_header)
        right_stats_layout.addLayout(right_cornering_layout)
        
        right_driver_layout.addLayout(right_stats_layout)
        
        # Add all sections to top layout
        top_section.addWidget(left_driver_widget, 1)
        top_section.addWidget(track_map_widget, 2)
        top_section.addWidget(right_driver_widget, 1)
        
        # Bottom section: Speed trace and delta
        bottom_section = QVBoxLayout()
        
        # Speed trace and turn markers
        speed_trace_widget = QWidget()
        speed_trace_widget.setMinimumHeight(200)
        speed_trace_widget.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """)
        
        # Delta section
        delta_widget = QWidget()
        delta_widget.setMinimumHeight(50)
        delta_widget.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """)
        
        bottom_section.addWidget(speed_trace_widget, 3)
        bottom_section.addWidget(delta_widget, 1)
        
        # Add sections to main layout
        main_layout.addLayout(top_section, 1)
        main_layout.addLayout(bottom_section, 1)
        
        # Initialize with sample data for development/testing
        self._generate_sample_track_data()
        
    def _generate_sample_track_data(self):
        """Generate sample track data for visualization testing."""
        import math
        
        # Create a simple oval track with 11 turns
        track_points = []
        radius_x = 100
        radius_y = 60
        center_x = 120
        center_y = 80
        
        # Create the main oval shape
        for angle in range(0, 360, 5):
            rad = math.radians(angle)
            x = center_x + radius_x * math.cos(rad)
            y = center_y + radius_y * math.sin(rad)
            track_points.append((x, y))
            
        self.track_map_points = track_points
        
        # Define turn positions
        self.track_turns = {}
        turn_angles = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 330]
        
        for i, angle in enumerate(turn_angles, 1):
            rad = math.radians(angle)
            x = center_x + radius_x * math.cos(rad)
            y = center_y + radius_y * math.sin(rad)
            self.track_turns[i] = {"position": (x, y)}
        
        # Define speed sectors
        self.track_sectors = {
            "sector1": {
                "speed_category": "LOW",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(0, 60, 5)
                ]
            },
            "sector2": {
                "speed_category": "LOW",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(60, 120, 5)
                ]
            },
            "sector3": {
                "speed_category": "HIGH",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(120, 180, 5)
                ]
            },
            "sector4": {
                "speed_category": "HIGH",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(180, 270, 5)
                ]
            },
            "sector5": {
                "speed_category": "MEDIUM",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(270, 360, 5)
                ]
            }
        }
        
        # Generate sample speed data
        self.speed_data_left = []
        self.speed_data_right = []
        
        for angle in range(0, 360, 5):
            # Simulate speed patterns: faster in straights, slower in corners
            base_speed = 200
            
            # Slow down in turns (around 0, 90, 180, 270 degrees)
            for turn_angle in [0, 90, 180, 270]:
                if abs((angle % 360) - turn_angle) < 30:
                    turn_factor = 1.0 - (30 - abs((angle % 360) - turn_angle)) / 30.0 * 0.7
                    base_speed *= turn_factor
            
            # Add small variations between drivers
            self.speed_data_left.append(base_speed * (0.95 + 0.1 * math.sin(math.radians(angle * 2))))
            self.speed_data_right.append(base_speed * (0.97 + 0.1 * math.sin(math.radians(angle * 2 + 20))))
        
        # Generate delta data
        self.delta_data = []
        overall_delta = 0
        
        for i in range(len(self.speed_data_left)):
            # Calculate delta based on speed difference
            speed_delta = (self.speed_data_left[i] - self.speed_data_right[i]) * 0.001
            overall_delta += speed_delta
            self.delta_data.append(overall_delta)
        
        # Initialize driver data
        self.left_driver = {
            "name": "CHARLES",
            "lastname": "LECLERC",
            "team": "FERRARI",
            "position": "1",
            "lap_time": 83.456,  # 1:23.456
            "gap": -0.321,       # -0.321s
            "full_throttle": 81,  # 81%
            "heavy_braking": 5,   # 5%
            "cornering": 14,      # 14%
            "color": QColor(255, 0, 0)  # red for left driver
        }
        
        self.right_driver = {
            "name": "CARLOS",
            "lastname": "SAINZ",
            "team": "FERRARI",
            "position": "2",
            "lap_time": 83.777,  # 1:23.777
            "gap": 0.321,        # +0.321s
            "full_throttle": 81,  # 81%
            "heavy_braking": 5,   # 5%
            "cornering": 14,      # 14%
            "color": QColor(255, 215, 0)  # gold for right driver
        }
        
        # Update the UI with this data
        self.update_driver_display(True)  # Update left driver
        self.update_driver_display(False) # Update right driver
        
        # Trigger repaint
        self.update()
    
    def set_driver_data(self, is_left_driver, data):
        """Update driver data and refresh display.
        
        Args:
            is_left_driver: True for left driver, False for right driver
            data: Dictionary with driver data
        """
        driver = self.left_driver if is_left_driver else self.right_driver
        
        # Update driver data
        if "name" in data:
            name_parts = data["name"].split()
            if len(name_parts) > 1:
                driver["name"] = name_parts[0]
                driver["lastname"] = " ".join(name_parts[1:])
            else:
                driver["name"] = data["name"]
                driver["lastname"] = ""
                
        if "team" in data:
            driver["team"] = data["team"]
            
        if "position" in data:
            driver["position"] = data["position"]
            
        if "lap_time" in data:
            driver["lap_time"] = data["lap_time"]
            
        if "gap" in data:
            driver["gap"] = data["gap"]
            
        if "full_throttle" in data:
            driver["full_throttle"] = data["full_throttle"]
            
        if "heavy_braking" in data:
            driver["heavy_braking"] = data["heavy_braking"]
            
        if "cornering" in data:
            driver["cornering"] = data["cornering"]
            
        # Refresh UI
        self.update_driver_display(is_left_driver)
        
    def update_driver_display(self, is_left_driver):
        """Update the UI display for a driver.
        
        Args:
            is_left_driver: True for left driver, False for right driver
        """
        driver = self.left_driver if is_left_driver else self.right_driver
        
        if is_left_driver:
            # Update left driver display
            self.left_position_label.setText(str(driver["position"]))
            self.left_driver_name.setText(driver["name"].upper())
            self.left_driver_lastname.setText(driver["lastname"].upper())
            self.left_driver_team.setText(driver["team"].upper())
            
            # Format lap time as M:SS.MMM
            self.left_lap_time.setText(self._format_time(driver["lap_time"]))
            
            # Format gap
            if driver["gap"] <= 0:
                self.left_gap.setText(f"{driver['gap']:.3f}s")
            else:
                self.left_gap.setText(f"+{driver['gap']:.3f}s")
                
            # Update stats
            self.left_throttle_value.setText(f"{driver['full_throttle']}%")
            self.left_braking_value.setText(f"{driver['heavy_braking']}%")
            self.left_cornering_value.setText(f"{driver['cornering']}%")
        else:
            # Update right driver display
            self.right_position_label.setText(str(driver["position"]))
            self.right_driver_name.setText(driver["name"].upper())
            self.right_driver_lastname.setText(driver["lastname"].upper())
            self.right_driver_team.setText(driver["team"].upper())
            
            # Format lap time as M:SS.MMM
            self.right_lap_time.setText(self._format_time(driver["lap_time"]))
            
            # Format gap
            if driver["gap"] <= 0:
                self.right_gap.setText(f"{driver['gap']:.3f}s")
            else:
                self.right_gap.setText(f"+{driver['gap']:.3f}s")
                
            # Update stats
            self.right_throttle_value.setText(f"{driver['full_throttle']}%")
            self.right_braking_value.setText(f"{driver['heavy_braking']}%")
            self.right_cornering_value.setText(f"{driver['cornering']}%")
    
    def set_speed_data(self, left_data, right_data):
        """Set the speed data for both drivers.
        
        Args:
            left_data: List of speed values for left driver
            right_data: List of speed values for right driver
        """
        self.speed_data_left = left_data
        self.speed_data_right = right_data
        
        # Auto analyze the telemetry when new data is set
        self.analyze_telemetry()
        self.update()
        
    def set_delta_data(self, delta_data):
        """Set the delta time data.
        
        Args:
            delta_data: List of delta time values (positive means right driver is slower)
        """
        self.delta_data = delta_data
        
        # Re-analyze with new delta data
        self.analyze_telemetry()
        self.update()
        
    def set_track_data(self, track_map_points, turn_data, sector_data):
        """Set the track map data.
        
        Args:
            track_map_points: List of (x, y) points defining the track outline
            turn_data: Dictionary mapping turn numbers to track positions
            sector_data: Dictionary defining speed sectors
        """
        self.track_map_points = track_map_points
        self.track_turns = turn_data
        self.track_sectors = sector_data
        self.update()
        
    def analyze_telemetry(self):
        """Analyze the speed data to generate enhanced telemetry visualization.
        
        This method:
        1. Identifies key sections of the track based on speed profiles
        2. Calculates sector-specific delta times
        3. Auto-categorizes track sections by speed (LOW/MEDIUM/HIGH)
        """
        if not hasattr(self, 'speed_data_left') or not self.speed_data_left:
            return
            
        if not hasattr(self, 'speed_data_right') or not self.speed_data_right:
            return
            
        # Normalize data lengths if needed
        min_length = min(len(self.speed_data_left), len(self.speed_data_right))
        if min_length == 0:
            return
            
        self.speed_data_left = self.speed_data_left[:min_length]
        self.speed_data_right = self.speed_data_right[:min_length]
        
        # Calculate the average speed at each point
        avg_speeds = [(self.speed_data_left[i] + self.speed_data_right[i]) / 2 
                     for i in range(min_length)]
        
        # Find the max speed to determine thresholds
        max_speed = max(avg_speeds)
        
        # Define thresholds for speed categories
        low_speed_threshold = max_speed * 0.4  # Below 40% of max speed
        high_speed_threshold = max_speed * 0.8  # Above 80% of max speed
        
        # Identify continuous sections by speed category
        current_category = "MEDIUM SPEED"  # Default
        section_start = 0
        sections = []
        
        for i, speed in enumerate(avg_speeds):
            category = "MEDIUM SPEED"
            if speed < low_speed_threshold:
                category = "LOW SPEED"
            elif speed > high_speed_threshold:
                category = "HIGH SPEED"
                
            # If category changes, end the previous section
            if category != current_category or i == len(avg_speeds) - 1:
                sections.append({
                    "start": section_start,
                    "end": i - 1 if i < len(avg_speeds) - 1 else i,
                    "category": current_category
                })
                section_start = i
                current_category = category
        
        # Combine small sections (less than 5% of track) with neighbors
        min_section_size = min_length * 0.05
        cleaned_sections = []
        i = 0
        
        while i < len(sections):
            section = sections[i]
            size = section["end"] - section["start"] + 1
            
            # If section is too small and not the only section
            if size < min_section_size and len(sections) > 1:
                # If not the first section, merge with previous
                if i > 0:
                    prev_section = cleaned_sections[-1]
                    prev_section["end"] = section["end"]
                # If last section, merge with next
                elif i < len(sections) - 1:
                    next_section = sections[i+1]
                    next_section["start"] = section["start"]
                    cleaned_sections.append(next_section)
                    i += 1
            else:
                cleaned_sections.append(section)
            i += 1
            
        # Update the track sectors data structure
        self.track_sectors = {}
        
        for i, section in enumerate(cleaned_sections):
            start_idx = section["start"]
            end_idx = section["end"]
            category = section["category"]
            
            # Create track sector data
            # In a real implementation, we'd map this to actual track points
            self.track_sectors[i] = {
                "speed_category": category,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "points": [] # This would be filled with actual track points in a full implementation
            }
            
        # Now calculate delta time per section
        if hasattr(self, 'delta_data') and self.delta_data:
            for sector_id, sector in self.track_sectors.items():
                start_idx = sector["start_idx"]
                end_idx = sector["end_idx"]
                
                if start_idx < len(self.delta_data) and end_idx < len(self.delta_data):
                    # Calculate delta gain/loss in this sector
                    sector_delta = self.delta_data[end_idx] - (self.delta_data[start_idx] if start_idx > 0 else 0)
                    self.track_sectors[sector_id]["delta"] = sector_delta
        
        self.update()  # Refresh the display
        
    def paintEvent(self, event):
        """Paint the comparison widget with real data.
        
        This will draw:
        1. Speed trace with custom rendering
        2. Track map (when implemented)
        3. Delta time graph
        """
        try:
            super().paintEvent(event)
            
            # Only proceed if we have data to display
            if not hasattr(self, 'speed_data_left') or not hasattr(self, 'speed_data_right'):
                return
                
            if not self.speed_data_left or not self.speed_data_right:
                return
                
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Get widget dimensions
            width = self.width()
            height = self.height()
            
            # Draw track map in the center top area
            track_map_top = height * 0.05
            track_map_height = height * 0.45
            track_map_bottom = track_map_top + track_map_height
            track_map_left = width * 0.3
            track_map_width = width * 0.4
            track_map_right = track_map_left + track_map_width
            
            # Background for track map
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(25, 25, 25)))
            painter.drawRect(int(track_map_left), int(track_map_top), int(track_map_width), int(track_map_height))
            
            # Draw track map if we have track data
            if hasattr(self, 'track_map_points') and self.track_map_points:
                # Scale track points to fit our drawing area
                # First determine the bounds of the track points
                min_x = min(p[0] for p in self.track_map_points)
                max_x = max(p[0] for p in self.track_map_points)
                min_y = min(p[1] for p in self.track_map_points)
                max_y = max(p[1] for p in self.track_map_points)
                
                # Determine scale and offset to fit in our drawing area
                scale_x = (track_map_width * 0.8) / (max_x - min_x)
                scale_y = (track_map_height * 0.8) / (max_y - min_y)
                scale = min(scale_x, scale_y)  # Use the same scale for both dimensions
                
                # Center the track in the map area
                offset_x = track_map_left + track_map_width / 2 - (min_x + max_x) / 2 * scale
                offset_y = track_map_top + track_map_height / 2 - (min_y + max_y) / 2 * scale
                
                # Draw the track outline
                track_path = QPainterPath()
                first_point = True
                
                for x, y in self.track_map_points:
                    screen_x = offset_x + x * scale
                    screen_y = offset_y + y * scale
                    
                    if first_point:
                        try:
                            track_path.moveTo(screen_x, screen_y)
                        except Exception as e:
                            # If our fallback implementation fails, draw directly
                            first_point_coords = (screen_x, screen_y)
                            polygon_points = [first_point_coords]
                            break
                        first_point = False
                    else:
                        try:
                            track_path.lineTo(screen_x, screen_y)
                        except Exception as e:
                            # If our fallback implementation fails, collect points for direct drawing
                            polygon_points.append((screen_x, screen_y))
                
                # Close the path
                try:
                    track_path.closeSubpath()
                    
                    # Draw track outline
                    painter.setPen(QPen(QColor(100, 100, 100), 2))
                    painter.setBrush(QBrush(QColor(40, 40, 40)))
                    painter.drawPath(track_path)
                except Exception as e:
                    # Fallback: Draw as polygon if QPainterPath fails
                    if 'polygon_points' in locals():
                        # Close the polygon
                        if polygon_points[0] != polygon_points[-1]:
                            polygon_points.append(polygon_points[0])
                        
                        # Draw as lines
                        painter.setPen(QPen(QColor(100, 100, 100), 2))
                        painter.setBrush(QBrush(QColor(40, 40, 40)))
                        
                        # Draw the polygon as a series of lines
                        for i in range(len(polygon_points) - 1):
                            painter.drawLine(
                                int(polygon_points[i][0]), int(polygon_points[i][1]),
                                int(polygon_points[i+1][0]), int(polygon_points[i+1][1])
                            )
                
                # Draw speed sectors if available
                if hasattr(self, 'track_sectors') and self.track_sectors:
                    # Define colors for different speed categories
                    speed_colors = {
                        "LOW": QColor(255, 0, 0, 60),     # Red with transparency
                        "MEDIUM": QColor(255, 165, 0, 60), # Orange with transparency
                        "HIGH": QColor(0, 255, 0, 60)      # Green with transparency
                    }
                    
                    # Draw each sector with appropriate color
                    for sector_id, sector_data in self.track_sectors.items():
                        if "speed_category" in sector_data and "points" in sector_data:
                            category = sector_data["speed_category"]
                            sector_points = sector_data["points"]
                            
                            if category in speed_colors and len(sector_points) > 2:
                                # Create path for this sector
                                sector_path = QPainterPath()
                                first_point = True
                                
                                for x, y in sector_points:
                                    screen_x = offset_x + x * scale
                                    screen_y = offset_y + y * scale
                                    
                                    if first_point:
                                        sector_path.moveTo(screen_x, screen_y)
                                        first_point = False
                                    else:
                                        sector_path.lineTo(screen_x, screen_y)
                                
                                sector_path.closeSubpath()
                                
                                # Draw colored sector
                                painter.setPen(Qt.NoPen)
                                painter.setBrush(QBrush(speed_colors[category]))
                                painter.drawPath(sector_path)
                
                # Draw turn markers and numbers if available
                if hasattr(self, 'track_turns') and self.track_turns:
                    painter.setPen(QPen(QColor(255, 255, 255)))
                    painter.setFont(QFont("Arial", 8, QFont.Bold))
                    
                    for turn_num, turn_data in self.track_turns.items():
                        if "position" in turn_data:
                            x, y = turn_data["position"]
                            screen_x = offset_x + x * scale
                            screen_y = offset_y + y * scale
                            
                            # Draw turn marker
                            painter.setBrush(QBrush(QColor(200, 200, 200)))
                            painter.drawEllipse(int(screen_x - 3), int(screen_y - 3), 6, 6)
                            
                            # Draw turn number
                            painter.drawText(int(screen_x + 5), int(screen_y + 3), str(turn_num))
            
            # Define areas for speed and delta graphs
            speed_top = track_map_bottom + 20
            speed_height = height * 0.25
            speed_bottom = speed_top + speed_height
            
            delta_top = speed_bottom + 10
            delta_height = height * 0.15
            delta_bottom = delta_top + delta_height
            
            # Draw background for speed trace - F1 style dark background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(17, 17, 17)))
            painter.drawRect(0, speed_top, width, speed_height)
            
            # Add subtle grid pattern for F1 style
            painter.setPen(QPen(QColor(40, 40, 40), 1))
            grid_spacing_h = width / 20
            for i in range(21):
                x = i * grid_spacing_h
                painter.drawLine(x, speed_top, x, speed_bottom)
            
            # Draw background for delta graph
            painter.setBrush(QBrush(QColor(17, 17, 17)))
            painter.drawRect(0, delta_top, width, delta_height)
            
            # Add subtle grid pattern for delta graph too
            for i in range(21):
                x = i * grid_spacing_h
                painter.drawLine(x, delta_top, x, delta_bottom)
            
            # Draw speed trace labels (every 50 km/h)
            max_speed = 350  # More headroom for speed scale
            
            if self.speed_data_left and len(self.speed_data_left) > 0:
                max_speed = max(max_speed, max(self.speed_data_left) * 1.1)  # Add 10% headroom
                
            if self.speed_data_right and len(self.speed_data_right) > 0:
                max_speed = max(max_speed, max(self.speed_data_right) * 1.1)  # Add 10% headroom
            
            # Round max speed to nearest 50 for clean labels
            max_speed = math.ceil(max_speed / 50) * 50
            
            # Draw horizontal grid lines and labels for speed
            painter.setPen(QPen(QColor(70, 70, 70)))
            painter.setFont(QFont("Arial", 8))
            
            for speed in range(0, int(max_speed) + 50, 50):
                y = speed_bottom - (speed / max_speed) * speed_height
                painter.drawLine(0, y, width, y)
                
                # Draw speed labels with better styling
                text_rect = painter.boundingRect(0, 0, 30, 15, Qt.AlignRight, f"{speed}")
                painter.setPen(QPen(QColor(180, 180, 180)))
                painter.drawText(5, y - 2, f"{speed}")
                painter.setPen(QPen(QColor(70, 70, 70)))
            
            # Label the speed trace
            painter.setPen(QPen(QColor(220, 220, 220)))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(10, speed_top + 20, "SPEED (km/h)")
            
            # Draw turn markers with F1-style numbering
            # F1 style has clear turn markers at the top of the graph
            turn_labels = {1: "TURN 1", 2: "2", 3: "3", 4: "4", 5: "5", 
                           6: "6", 7: "7", 8: "8", 9: "9", 10: "10", 11: "11"}
                           
            # Get the positions for the turn markers (for now, equally spaced)
            num_points = min(len(self.speed_data_left), len(self.speed_data_right))
            if num_points == 0:
                return
                
            # Draw segment labels for speed categories - more F1-like segments
            segment_labels = ["LOW SPEED", "MEDIUM SPEED", "HIGH SPEED", "HIGH SPEED", "MEDIUM SPEED", "LOW SPEED"]
            segment_width = width / len(segment_labels)
            
            # Draw segment backgrounds with subtle color coding
            segment_colors = {
                "LOW SPEED": QColor(200, 40, 40, 20),     # Red tint
                "MEDIUM SPEED": QColor(200, 200, 40, 20),  # Yellow tint
                "HIGH SPEED": QColor(40, 200, 40, 20)      # Green tint
            }
            
            painter.setFont(QFont("Arial", 8))
            
            for i, label in enumerate(segment_labels):
                x = i * segment_width
                
                # Draw subtle background
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(segment_colors[label]))
                painter.drawRect(x, speed_top, segment_width, speed_height)
                
                # Draw label
                painter.setPen(QPen(QColor(180, 180, 180)))
                text_width = painter.fontMetrics().width(label)
                painter.drawText(x + (segment_width - text_width)/2, speed_top + 15, label)
                
                # Draw vertical separator lines
                if i > 0:
                    painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
                    painter.drawLine(i * segment_width, speed_top, i * segment_width, speed_bottom)
            
            # Draw turn markers with improved styling
            spacing = width / (len(turn_labels) + 1)
            
            # Draw turn marker background
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(40, 40, 40)))
            painter.drawRect(0, speed_top - 25, width, 25)
            
            # Draw turn labels
            painter.setPen(QPen(QColor(220, 220, 220)))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            for i, (turn, label) in enumerate(turn_labels.items()):
                x = (i + 1) * spacing
                
                # Draw turn number
                painter.drawText(x - 15, speed_top - 8, label)
                
                # Draw marker line down to graph
                painter.setPen(QPen(QColor(100, 100, 100), 1, Qt.DashLine))
                painter.drawLine(x, speed_top - 5, x, speed_top)
            
            # Draw speed traces with improved styling
            line_width = 2  # Thicker lines for better visibility
            
            if self.speed_data_left and len(self.speed_data_left) > 1:
                # Normalize the data to our drawing space
                points = []
                x_step = width / (len(self.speed_data_left) - 1)
                for i, speed in enumerate(self.speed_data_left):
                    x = i * x_step
                    y = speed_bottom - (speed / max_speed) * speed_height
                    points.append((x, y))
                
                # Draw the line with shadow effect for F1 style
                # First draw shadow
                shadow_pen = QPen(QColor(0, 0, 0, 100), line_width + 2)
                painter.setPen(shadow_pen)
                for i in range(len(points) - 1):
                    painter.drawLine(int(points[i][0]), int(points[i][1]) + 2, 
                                     int(points[i+1][0]), int(points[i+1][1]) + 2)
                
                # Then draw actual line
                painter.setPen(QPen(self.left_driver["color"], line_width))
                for i in range(len(points) - 1):
                    painter.drawLine(int(points[i][0]), int(points[i][1]), 
                                     int(points[i+1][0]), int(points[i+1][1]))
            
            if self.speed_data_right and len(self.speed_data_right) > 1:
                # Normalize the data to our drawing space
                points = []
                x_step = width / (len(self.speed_data_right) - 1)
                for i, speed in enumerate(self.speed_data_right):
                    x = i * x_step
                    y = speed_bottom - (speed / max_speed) * speed_height
                    points.append((x, y))
                
                # Draw the line with shadow effect
                # First draw shadow
                shadow_pen = QPen(QColor(0, 0, 0, 100), line_width + 2)
                painter.setPen(shadow_pen)
                for i in range(len(points) - 1):
                    painter.drawLine(int(points[i][0]), int(points[i][1]) + 2, 
                                     int(points[i+1][0]), int(points[i+1][1]) + 2)
                
                # Then draw actual line
                painter.setPen(QPen(self.right_driver["color"], line_width))
                for i in range(len(points) - 1):
                    painter.drawLine(int(points[i][0]), int(points[i][1]), 
                                     int(points[i+1][0]), int(points[i+1][1]))
                    
                # Add driver color indicators
                legend_y = speed_top + 20
                legend_width = 30
                legend_height = 2
                
                # Left driver indicator
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.left_driver["color"]))
                painter.drawRect(width - 120, legend_y, legend_width, legend_height)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawText(width - 120 + legend_width + 5, legend_y + 4, self.left_driver["name"])
                
                # Right driver indicator
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.right_driver["color"]))
                painter.drawRect(width - 120, legend_y + 15, legend_width, legend_height)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawText(width - 120 + legend_width + 5, legend_y + 19, self.right_driver["name"])
            
            # Draw delta graph with F1-style enhancements
            if hasattr(self, 'delta_data') and self.delta_data and len(self.delta_data) > 1:
                # Find max delta for scaling
                max_delta = max(abs(min(self.delta_data)), abs(max(self.delta_data)), 0.5)  # At least 0.5s scale
                
                # Round max delta to clean value (0.5s increments)
                max_delta = math.ceil(max_delta / 0.5) * 0.5
                
                # Draw horizontal bands for clarity
                band_colors = [
                    QColor(0, 150, 0, 15),  # Green band for faster
                    QColor(150, 0, 0, 15)   # Red band for slower
                ]
                
                # Draw bands
                painter.setPen(Qt.NoPen)
                zero_y = delta_top + delta_height / 2
                
                # Faster zone (bottom half)
                painter.setBrush(band_colors[0])
                painter.drawRect(0, zero_y, width, delta_height / 2)
                
                # Slower zone (top half)
                painter.setBrush(band_colors[1])
                painter.drawRect(0, delta_top, width, delta_height / 2)
                
                # Draw horizontal line at zero
                painter.setPen(QPen(QColor(220, 220, 220), 1))
                painter.drawLine(0, zero_y, width, zero_y)
                
                # Label the delta graph
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.drawText(10, delta_top + 15, "DELTA (seconds)")
                
                # Add FASTER/SLOWER indicators
                painter.setFont(QFont("Arial", 8))
                painter.setPen(QPen(QColor(0, 200, 0)))
                painter.drawText(width - 70, delta_bottom - 5, "FASTER")
                painter.setPen(QPen(QColor(200, 0, 0)))
                painter.drawText(width - 70, delta_top + 15, "SLOWER")
                
                # Draw positive and negative labels
                painter.setFont(QFont("Arial", 8))
                painter.setPen(QPen(QColor(200, 200, 200)))
                painter.drawText(5, delta_top + 15, f"+{max_delta:.2f}")
                painter.drawText(5, delta_bottom - 5, f"-{max_delta:.2f}")
                painter.drawText(5, zero_y + 4, "0.00")
                
                # Add horizontal grid lines
                painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
                step = max_delta / 2
                for i in range(1, 3):
                    # Positive lines (slower)
                    y_pos = zero_y - (i * step / max_delta) * (delta_height / 2)
                    painter.drawLine(0, y_pos, width, y_pos)
                    
                    # Negative lines (faster)
                    y_neg = zero_y + (i * step / max_delta) * (delta_height / 2)
                    painter.drawLine(0, y_neg, width, y_neg)
                
                # Draw the delta line
                points = []
                x_step = width / (len(self.delta_data) - 1)
                
                # Draw the negative (faster) values in green, positive (slower) in red
                faster_points = []
                slower_points = []
                
                for i, delta in enumerate(self.delta_data):
                    x = i * x_step
                    # Invert the delta so positive (slower) is up
                    y = zero_y - (delta / max_delta) * (delta_height / 2)
                    
                    if delta <= 0:
                        faster_points.append((x, y))
                    else:
                        slower_points.append((x, y))
                
                # Draw faster segments (green) with shadow
                shadow_pen = QPen(QColor(0, 0, 0, 100), line_width + 2)
                painter.setPen(shadow_pen)
                for i in range(len(faster_points) - 1):
                    painter.drawLine(int(faster_points[i][0]), int(faster_points[i][1]) + 2, 
                                    int(faster_points[i+1][0]), int(faster_points[i+1][1]) + 2)
                
                painter.setPen(QPen(QColor(0, 200, 0), line_width))
                for i in range(len(faster_points) - 1):
                    painter.drawLine(int(faster_points[i][0]), int(faster_points[i][1]), 
                                    int(faster_points[i+1][0]), int(faster_points[i+1][1]))
                
                # Draw slower segments (red) with shadow
                painter.setPen(shadow_pen)
                for i in range(len(slower_points) - 1):
                    painter.drawLine(int(slower_points[i][0]), int(slower_points[i][1]) + 2, 
                                    int(slower_points[i+1][0]), int(slower_points[i+1][1]) + 2)
                
                painter.setPen(QPen(QColor(200, 0, 0), line_width))
                for i in range(len(slower_points) - 1):
                    painter.drawLine(int(slower_points[i][0]), int(slower_points[i][1]), 
                                    int(slower_points[i+1][0]), int(slower_points[i+1][1]))
                    
            # Draw the time loss values below track sections
            if hasattr(self, 'delta_data') and self.delta_data:
                # Show overall delta at different sections
                section_deltas = []
                section_size = len(self.delta_data) // 11
                
                for i in range(11):
                    start = i * section_size
                    end = min((i + 1) * section_size, len(self.delta_data))
                    if start < end:
                        section_delta = self.delta_data[end-1] - (self.delta_data[start] if start > 0 else 0)
                        section_deltas.append(section_delta)
                    else:
                        section_deltas.append(0)
                        
                # Draw the section delta values with F1-style boxes
                painter.setFont(QFont("Arial", 9, QFont.Bold))
                spacing = width / (len(section_deltas) + 1)
                
                for i, delta in enumerate(section_deltas):
                    x = (i + 1) * spacing
                    # Format with sign, -0.000 for negative (gains), +0.000 for positive (losses)
                    if delta < 0:
                        text = f"-{abs(delta):.3f}"
                        bg_color = QColor(0, 150, 0)
                        text_color = QColor(255, 255, 255)
                    else:
                        text = f"+{delta:.3f}"
                        bg_color = QColor(150, 0, 0)
                        text_color = QColor(255, 255, 255)
                    
                    # Get text dimensions
                    text_rect = painter.boundingRect(0, 0, 100, 20, 0, text)
                    text_width = text_rect.width() + 10
                    text_height = text_rect.height() + 2
                    
                    # Draw background box
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(bg_color))
                    painter.drawRect(x - text_width/2, delta_bottom + 5, text_width, text_height)
                    
                    # Draw text
                    painter.setPen(QPen(text_color))
                    painter.drawText(x - text_width/2 + 5, delta_bottom + 5 + text_height - 3, text)
        except Exception as e:
            # Log error but don't crash the application
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in TelemetryComparisonWidget.paintEvent: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def load_demo_data(self):
        """Load demo telemetry data for visualization testing.
        
        This creates realistic sample data to demonstrate the F1-style visualization
        without requiring real telemetry data.
        """
        import random
        import math
        
        # Set driver information
        self.left_driver = {
            "name": "CHARLES",
            "lastname": "LECLERC",
            "team": "FERRARI",
            "position": "1",
            "lap_time": 83.456,  # 1:23.456
            "gap": -0.321,
            "full_throttle": 81,
            "heavy_braking": 5,
            "cornering": 14,
            "color": QColor(255, 0, 0)  # red for left driver
        }
        
        self.right_driver = {
            "name": "CARLOS",
            "lastname": "SAINZ",
            "team": "FERRARI",
            "position": "2",
            "lap_time": 83.777,  # 1:23.777
            "gap": 0.321,
            "full_throttle": 79,
            "heavy_braking": 6,
            "cornering": 15,
            "color": QColor(255, 215, 0)  # gold for right driver
        }
        
        # Update the UI with driver data
        self.update_driver_display(True)  # Update left driver
        self.update_driver_display(False)  # Update right driver
        
        # Generate simple oval track map with 11 turns
        track_points = []
        num_points = 100
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            # Create oval shape by modifying circle
            x = 200 * math.cos(angle) * (1 + 0.3 * math.cos(2 * angle))
            y = 150 * math.sin(angle) * (1 + 0.1 * math.sin(2 * angle))
            track_points.append((x, y))
            
        # Create turn data
        turn_data = {}
        for turn in range(1, 12):
            idx = (turn - 1) * (num_points // 11)
            turn_data[turn] = {
                "position": track_points[idx],
                "name": f"Turn {turn}"
            }
        
        # Define speed sectors
        sector_data = {
            "sector1": {
                "speed_category": "LOW",
                "points": [track_points[i] for i in range(0, 20)]
            },
            "sector2": {
                "speed_category": "MEDIUM",
                "points": [track_points[i] for i in range(20, 40)]
            },
            "sector3": {
                "speed_category": "HIGH",
                "points": [track_points[i] for i in range(40, 60)]
            },
            "sector4": {
                "speed_category": "HIGH",
                "points": [track_points[i] for i in range(60, 80)]
            },
            "sector5": {
                "speed_category": "MEDIUM",
                "points": [track_points[i] for i in range(80, 100)]
            }
        }
            
        # Generate speed data for both drivers
        # Base speed profile with realistic acceleration/braking patterns
        base_profile = []
        for i in range(200):
            angle = i / 200 * 2 * math.pi
            
            # Create a speed profile that varies with track position
            speed = 250 + 70 * math.sin(angle) - 50 * math.sin(2 * angle)
            
            # Add small random variations
            speed += random.uniform(-5, 5)
            
            # Ensure minimum speed
            speed = max(speed, 80)
            
            base_profile.append(speed)
            
        # Create slightly different profiles for each driver
        speed_data_left = base_profile.copy()
        speed_data_right = []
        
        for i, speed in enumerate(base_profile):
            # Right driver slightly slower in some sections, faster in others
            modifier = math.sin(i / 200 * 2 * math.pi * 3) * 10
            speed_data_right.append(speed + modifier)
            
        # Generate delta data (positive means right driver is slower)
        delta_data = [0]
        for i in range(1, len(speed_data_left)):
            # Calculate time spent on this segment (distance / speed)
            segment_time_left = 1 / speed_data_left[i]  # Assuming equal distance segments
            segment_time_right = 1 / speed_data_right[i]
            
            # Accumulate the delta time
            segment_delta = segment_time_right - segment_time_left
            delta_data.append(delta_data[-1] + segment_delta)
            
        # Scale delta to realistic values (-0.5s to +0.5s range)
        scale = 0.5 / max(abs(min(delta_data)), abs(max(delta_data)))
        delta_data = [d * scale for d in delta_data]
        
        # Set the data
        self.track_map_points = track_points
        self.track_turns = turn_data
        self.track_sectors = sector_data
        self.speed_data_left = speed_data_left
        self.speed_data_right = speed_data_right
        self.delta_data = delta_data
        
        # Force update
        self.update()

    def _format_time(self, seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if seconds is None or seconds <= 0:
            return "--:--.---" 
            
        minutes = int(seconds / 60)
        seconds_remainder = seconds % 60
        
        return f"{minutes}:{seconds_remainder:06.3f}"

class RaceCoachWidget(QWidget):
    """Main widget for the Race Coach feature that can be embedded as a tab."""
    
    # Add signal for telemetry updates from background thread
    # Define signal at class level with correct parameter type
    telemetry_update_signal = pyqtSignal(object)
    
    def __init__(self, parent=None, iracing_api=None):
        """
        Initialize the Race Coach Widget.
        
        Args:
            parent: Parent widget
            iracing_api: Instance of iRacing API for telemetry access
        """
        super().__init__(parent)
        
        # Set up internal state
        self._is_destroying = False
        self._is_connected = False  # Initialize connection status
        self.telemetry_data = {}
        self.previous_telemetry = {}
        self.last_speed = 0
        self.last_rpm = 0
        self.lap_start_time = None
        self.current_lap_time = 0
        self.last_lap_time = 0
        self.best_lap_time = 0
        self.current_lap = 0
        self.in_pit_lane = False
        self.lap_valid = True
        self.is_braking = False
        self.prev_brake_value = 0
        self.prev_throttle_value = 0
        self.throttle_history = []
        self.brake_history = []
        self.clutch_history = []
        self.steering_history = []
        self.speed_history = []
        self.rpm_history = []
        self.gear_history = []
        
        # Connect the telemetry update signal to the handler method
        # Make sure signal is connected properly with instance method
        self.telemetry_update_signal.connect(self._on_telemetry_update_main_thread)
        
        # If API is provided, use it
        if iracing_api:
            logger.info(f"Using provided iracing_api: {type(iracing_api).__name__}")
            self.iracing_api = iracing_api
        else:
            logger.info("No iRacing API provided, creating new SimpleIRacingAPI")
            try:
                from .simple_iracing import SimpleIRacingAPI
                self.iracing_api = SimpleIRacingAPI()
            except Exception as e:
                logger.error(f"Failed to create SimpleIRacingAPI: {e}")
                self.iracing_api = None
                
        # Create a Supabase lap saver for the widget
        try:
            logger.info("Creating IRacingLapSaver in widget initialization")
            from .iracing_lap_saver import IRacingLapSaver
            self.lap_saver = IRacingLapSaver()
            
            # Set user ID for lap saver if we have it
            try:
                from ..auth.user_manager import get_current_user
                user = get_current_user()
                if user and hasattr(user, 'id'):
                    user_id = user.id
                    logger.info(f"Set user ID for widget's lap saver: {user_id}")
                    self.lap_saver.set_user_id(user_id)
            except Exception as e:
                logger.error(f"Failed to set user ID for lap saver: {e}")
                
            # Connect lap saver to the API
            if self.iracing_api:
                logger.info("Connected lap saver to iRacing API in widget initialization")
                self.iracing_api.set_lap_saver(self.lap_saver)
        except Exception as e:
            logger.error(f"Failed to create or connect lap saver: {e}")
            self.lap_saver = None
                
        # Create a safe telemetry callback to register with the API
        self._safe_telemetry_callback = self._create_safe_telemetry_callback()
        
        # Connect to the API if available
        if self.iracing_api:
            try:
                # Check if the API has the on_telemetry_data method
                if hasattr(self.iracing_api, 'register_on_telemetry_data'):
                    logger.info("Registering widget's telemetry callback with iRacing API")
                    self.iracing_api.register_on_telemetry_data(self._safe_telemetry_callback)
                else:
                    logger.warning("API does not have register_on_telemetry_data method")
            except Exception as e:
                logger.error(f"Error registering callbacks with iRacing API: {e}")
                
            # Create a timer to periodically check iRacing connection
            self.connection_check_timer = QTimer()
            self.connection_check_timer.timeout.connect(self._check_iracing_connection)
            self.connection_check_timer.start(1000)  # Check every 1 second
                
        try:
            self.setup_ui()
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
        self.setup_telemetry_review_tab()  # Add new telemetry review tab
        
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
        
        # Steering wheel angle display - row 8
        steering_label = QLabel("Steering:")
        steering_label.setStyleSheet("color: white; font-size: 12px;")
        self.steering_value = QLabel("0°")
        self.steering_value.setStyleSheet("color: #2196F3; font-size: 12px; font-weight: bold;")  # Blue color
        telemetry_info_layout.addWidget(steering_label, 8, 0)
        telemetry_info_layout.addWidget(self.steering_value, 8, 1)
        
        # Steering angle progress bar
        self.steering_bar = QProgressBar()
        self.steering_bar.setRange(-100, 100)  # Allow for negative values (left) and positive values (right)
        self.steering_bar.setValue(0)
        self.steering_bar.setTextVisible(False)
        self.steering_bar.setFixedHeight(12)
        self.steering_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 30, 30, 0.5);
                border-radius: 3px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        telemetry_info_layout.addWidget(self.steering_bar, 8, 2, 1, 2)
        
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
    
    def setup_telemetry_review_tab(self):
        """Set up the Telemetry Review tab for viewing saved lap data."""
        telemetry_review_widget = QWidget()
        layout = QVBoxLayout(telemetry_review_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create simple control panel with refresh button
        control_panel = QHBoxLayout()
        
        # Add a refresh button to reload available laps
        refresh_button = QPushButton("Refresh Lap Data")
        refresh_button.setFixedWidth(150)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                padding: 6px 12px;
                border: 1px solid #444;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        refresh_button.clicked.connect(self._reload_lap_data)
        
        # Simple label to show status
        self.lap_info_label = QLabel("No data manager available - showing sample data")
        self.lap_info_label.setStyleSheet("color: white; font-size: 12px;")
        
        control_panel.addWidget(refresh_button)
        control_panel.addWidget(self.lap_info_label)
        control_panel.addStretch()
        
        # Add control panel to main layout
        layout.addLayout(control_panel)
        
        # Add session and lap selection UI
        selection_layout = QHBoxLayout()
        
        # Left lap selection
        left_lap_group = QGroupBox("Reference Lap (Left)")
        left_lap_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid rgba(255, 0, 0, 0.5);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        left_lap_layout = QVBoxLayout(left_lap_group)
        
        # Session dropdown for left lap
        left_session_layout = QHBoxLayout()
        left_session_layout.addWidget(QLabel("Session:"))
        self.left_session_combo = QComboBox()
        self.left_session_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        left_session_combo_width = 200
        self.left_session_combo.setMinimumWidth(left_session_combo_width)
        self.left_session_combo.currentIndexChanged.connect(self._on_left_session_changed)
        left_session_layout.addWidget(self.left_session_combo)
        left_lap_layout.addLayout(left_session_layout)
        
        # Lap dropdown for left lap
        left_lap_select_layout = QHBoxLayout()
        left_lap_select_layout.addWidget(QLabel("Lap:"))
        self.left_lap_combo = QComboBox()
        self.left_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        self.left_lap_combo.setMinimumWidth(left_session_combo_width)
        left_lap_select_layout.addWidget(self.left_lap_combo)
        left_lap_layout.addLayout(left_lap_select_layout)
        
        # Right lap selection
        right_lap_group = QGroupBox("Comparison Lap (Right)")
        right_lap_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid rgba(255, 215, 0, 0.5);
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        right_lap_layout = QVBoxLayout(right_lap_group)
        
        # Session dropdown for right lap
        right_session_layout = QHBoxLayout()
        right_session_layout.addWidget(QLabel("Session:"))
        self.right_session_combo = QComboBox()
        self.right_session_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        self.right_session_combo.setMinimumWidth(left_session_combo_width)
        self.right_session_combo.currentIndexChanged.connect(self._on_right_session_changed)
        right_session_layout.addWidget(self.right_session_combo)
        right_lap_layout.addLayout(right_session_layout)
        
        # Lap dropdown for right lap
        right_lap_select_layout = QHBoxLayout()
        right_lap_select_layout.addWidget(QLabel("Lap:"))
        self.right_lap_combo = QComboBox()
        self.right_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
            }
        """)
        self.right_lap_combo.setMinimumWidth(left_session_combo_width)
        right_lap_select_layout.addWidget(self.right_lap_combo)
        right_lap_layout.addLayout(right_lap_select_layout)
        
        # Add lap groups to selection layout
        selection_layout.addWidget(left_lap_group)
        selection_layout.addWidget(right_lap_group)
        
        # Add selection layout to main layout
        layout.addLayout(selection_layout)
        
        # Add a button to load lap data
        load_button = QPushButton("Compare Selected Laps")
        load_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        load_button.clicked.connect(self._load_comparison_laps)
        load_button_layout = QHBoxLayout()
        load_button_layout.addStretch()
        load_button_layout.addWidget(load_button)
        load_button_layout.addStretch()
        
        # Add load button to main layout
        layout.addLayout(load_button_layout)
        
        # Create the F1-style telemetry comparison widget
        self.telemetry_comparison_widget = TelemetryComparisonWidget()
        self.telemetry_comparison_widget.setMinimumHeight(500)
        
        # Add the comparison widget to the main layout
        layout.addWidget(self.telemetry_comparison_widget, 1)  # Give it stretch factor priority
        
        # Add a demo button to quickly load visualization test data
        demo_button = QPushButton("Load F1 Demo Visualization")
        demo_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        demo_button.clicked.connect(self._load_demo_data)
        layout.addWidget(demo_button)
        
        # Add tab to widget
        self.tab_widget.addTab(telemetry_review_widget, "Telemetry")
        
        # Load available sessions
        self._load_available_sessions()
        
    def _reload_lap_data(self):
        """Reload lap data from the data manager and update the comparison widget."""
        logger.info("Reloading lap data...")
        self._load_available_sessions()
        self.lap_info_label.setText("Lap data reloaded")
        
    def _load_available_sessions(self):
        """Load available telemetry sessions from the data manager."""
        try:
            # Clear current items
            self.left_session_combo.clear()
            self.right_session_combo.clear()
            
            # Check if we have a data manager
            if not hasattr(self, 'data_manager') or self.data_manager is None:
                logger.warning("No data manager available to load sessions")
                self.left_session_combo.addItem("No sessions available")
                self.right_session_combo.addItem("No sessions available")
                self.lap_info_label.setText("No data manager available - showing sample data")
                self._set_sample_comparison_data()
                return
            
            # Get available sessions from data manager
            sessions = self.data_manager.get_sessions()
            if not sessions or len(sessions) == 0:
                logger.warning("No sessions found in data manager")
                self.left_session_combo.addItem("No sessions available")
                self.right_session_combo.addItem("No sessions available")
                self.lap_info_label.setText("No sessions available - showing sample data")
                self._set_sample_comparison_data()
                return
                
            # Add sessions to combos with their details
            for session_id, session_data in sessions.items():
                # Create a display name like: "2023-05-15 - Car @ Track"
                date_str = session_data.get('date', 'Unknown Date')
                car = session_data.get('car', 'Unknown Car')
                track = session_data.get('track', 'Unknown Track')
                display_name = f"{date_str} - {car} @ {track}"
                
                # Store session ID as user data
                self.left_session_combo.addItem(display_name, session_id)
                self.right_session_combo.addItem(display_name, session_id)
                
            # Select first item
            if self.left_session_combo.count() > 0:
                self.left_session_combo.setCurrentIndex(0)
                
            if self.right_session_combo.count() > 0:
                self.right_session_combo.setCurrentIndex(0)
                
            logger.info(f"Loaded {self.left_session_combo.count()} sessions for comparison")
            self.lap_info_label.setText(f"Found {self.left_session_combo.count()} sessions")
                
        except Exception as e:
            logger.error(f"Error loading available sessions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.lap_info_label.setText("Error loading sessions - showing sample data")
            self._set_sample_comparison_data()
            
    def _on_left_session_changed(self, index):
        """Handle changing the selected session for the left lap."""
        try:
            # Get selected session ID
            session_id = self.left_session_combo.itemData(index)
            if not session_id:
                logger.warning("No session ID in left session combobox")
                return
                
            # Clear current laps
            self.left_lap_combo.clear()
            
            # Get laps from this session
            if not hasattr(self, 'data_manager') or self.data_manager is None:
                logger.warning("No data manager available to load laps")
                return
                
            laps = self.data_manager.get_laps_for_session(session_id)
            if not laps or len(laps) == 0:
                logger.warning(f"No laps found for session {session_id}")
                self.left_lap_combo.addItem("No laps available")
                return
                
            # Add laps to combo with their details
            for lap_id, lap_data in laps.items():
                # Create a display name like: "Lap 1 - 1:23.456"
                lap_num = lap_data.get('lap_number', 'Unknown')
                lap_time = lap_data.get('lap_time', 0)
                
                # Format lap time as M:SS.mmm
                if lap_time > 0:
                    minutes = int(lap_time / 60)
                    seconds = lap_time % 60
                    time_str = f"{minutes}:{seconds:06.3f}"
                else:
                    time_str = "No time"
                    
                display_name = f"Lap {lap_num} - {time_str}"
                
                # Store lap ID as user data
                self.left_lap_combo.addItem(display_name, lap_id)
                
            # Select fastest lap if available
            fastest_lap_index = 0
            fastest_lap_time = float('inf')
            
            for i in range(self.left_lap_combo.count()):
                lap_id = self.left_lap_combo.itemData(i)
                lap_data = laps.get(lap_id, {})
                lap_time = lap_data.get('lap_time', float('inf'))
                
                if lap_time < fastest_lap_time:
                    fastest_lap_time = lap_time
                    fastest_lap_index = i
                    
            self.left_lap_combo.setCurrentIndex(fastest_lap_index)
            
            logger.info(f"Loaded {self.left_lap_combo.count()} laps for left comparison")
            
        except Exception as e:
            logger.error(f"Error loading laps for left session: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _on_right_session_changed(self, index):
        """Handle changing the selected session for the right lap."""
        try:
            # Get selected session ID
            session_id = self.right_session_combo.itemData(index)
            if not session_id:
                logger.warning("No session ID in right session combobox")
                return
                
            # Clear current laps
            self.right_lap_combo.clear()
            
            # Get laps from this session
            if not hasattr(self, 'data_manager') or self.data_manager is None:
                logger.warning("No data manager available to load laps")
                return
                
            laps = self.data_manager.get_laps_for_session(session_id)
            if not laps or len(laps) == 0:
                logger.warning(f"No laps found for session {session_id}")
                self.right_lap_combo.addItem("No laps available")
                return
                
            # Add laps to combo with their details
            for lap_id, lap_data in laps.items():
                # Create a display name like: "Lap 1 - 1:23.456"
                lap_num = lap_data.get('lap_number', 'Unknown')
                lap_time = lap_data.get('lap_time', 0)
                
                # Format lap time as M:SS.mmm
                if lap_time > 0:
                    minutes = int(lap_time / 60)
                    seconds = lap_time % 60
                    time_str = f"{minutes}:{seconds:06.3f}"
                else:
                    time_str = "No time"
                    
                display_name = f"Lap {lap_num} - {time_str}"
                
                # Store lap ID as user data
                self.right_lap_combo.addItem(display_name, lap_id)
                
            # Select fastest lap if available
            fastest_lap_index = 0
            fastest_lap_time = float('inf')
            
            for i in range(self.right_lap_combo.count()):
                lap_id = self.right_lap_combo.itemData(i)
                lap_data = laps.get(lap_id, {})
                lap_time = lap_data.get('lap_time', float('inf'))
                
                if lap_time < fastest_lap_time:
                    fastest_lap_time = lap_time
                    fastest_lap_index = i
                    
            self.right_lap_combo.setCurrentIndex(fastest_lap_index)
            
            logger.info(f"Loaded {self.right_lap_combo.count()} laps for right comparison")
            
        except Exception as e:
            logger.error(f"Error loading laps for right session: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _load_comparison_laps(self):
        """Load the selected lap data and update the comparison widget."""
        try:
            # Check if we have a valid data manager
            if not hasattr(self, 'data_manager') or self.data_manager is None:
                logger.error("No data manager available to load lap data")
                self.status_message.setText("Error: No data manager available")
                self._set_sample_comparison_data()
                return
                
            # Get selected lap IDs
            left_lap_id = self.left_lap_combo.currentData()
            right_lap_id = self.right_lap_combo.currentData()
            
            if not left_lap_id or not right_lap_id:
                logger.warning("No lap selected for comparison")
                self.status_message.setText("Please select laps for comparison")
                return
                
            # Load lap data
            left_lap_data = self.data_manager.get_lap_telemetry(left_lap_id)
            right_lap_data = self.data_manager.get_lap_telemetry(right_lap_id)
            
            if not left_lap_data or not right_lap_data:
                logger.warning("Failed to load telemetry data for selected laps")
                self.status_message.setText("Error loading telemetry data")
                return
                
            # Get lap information for the display
            left_lap_info = self.data_manager.get_lap_info(left_lap_id)
            right_lap_info = self.data_manager.get_lap_info(right_lap_id)
            
            # Get session info to get car/driver details
            left_session_id = self.left_session_combo.currentData()
            right_session_id = self.right_session_combo.currentData()
            
            left_session_info = self.data_manager.get_session_info(left_session_id)
            right_session_info = self.data_manager.get_session_info(right_session_id)
            
            # Create driver data for left driver
            left_driver_data = {
                'name': left_session_info.get('driver_name', 'Driver 1'),
                'team': left_session_info.get('team', left_session_info.get('car', 'Team 1')),
                'position': '1',  # Always position 1 for left driver
                'lap_time': left_lap_info.get('lap_time', 0),
                'gap': 0,  # Will be calculated after loading both laps
                'full_throttle': left_lap_info.get('full_throttle_pct', 0),
                'heavy_braking': left_lap_info.get('heavy_braking_pct', 0),
                'cornering': left_lap_info.get('cornering_pct', 0)
            }
            
            # Create driver data for right driver
            right_driver_data = {
                'name': right_session_info.get('driver_name', 'Driver 2'),
                'team': right_session_info.get('team', right_session_info.get('car', 'Team 2')),
                'position': '2',  # Always position 2 for right driver
                'lap_time': right_lap_info.get('lap_time', 0),
                'gap': 0,  # Will be calculated
                'full_throttle': right_lap_info.get('full_throttle_pct', 0),
                'heavy_braking': right_lap_info.get('heavy_braking_pct', 0),
                'cornering': right_lap_info.get('cornering_pct', 0)
            }
            
            # Calculate gap
            left_time = left_driver_data['lap_time']
            right_time = right_driver_data['lap_time']
            
            if left_time > 0 and right_time > 0:
                gap = right_time - left_time  # Positive if right is slower
                left_driver_data['gap'] = -gap if gap > 0 else 0  # Left driver is reference
                right_driver_data['gap'] = gap if gap > 0 else 0  # Right driver shows gap to left
            
            # Extract speed data series
            left_speed_data = [point.get('speed', 0) for point in left_lap_data]
            right_speed_data = [point.get('speed', 0) for point in right_lap_data]
            
            # Create delta data
            delta_data = self._calculate_delta_between_laps(left_lap_data, right_lap_data)
            
            # Get track data if available
            track_map_points = self._generate_track_map_points(left_session_id)
            turn_data = self._generate_turn_data()
            sector_data = self._generate_sector_data()
            
            # Update the comparison widget
            self.telemetry_comparison_widget.set_driver_data(True, left_driver_data)
            self.telemetry_comparison_widget.set_driver_data(False, right_driver_data)
            self.telemetry_comparison_widget.set_speed_data(left_speed_data, right_speed_data)
            self.telemetry_comparison_widget.set_delta_data(delta_data)
            
            if track_map_points:
                self.telemetry_comparison_widget.set_track_data(track_map_points, turn_data, sector_data)
                
            # Update status message and info label
            left_name = left_driver_data.get('name', 'Left Lap')
            right_name = right_driver_data.get('name', 'Right Lap')
            self.lap_info_label.setText(f"Comparing: {left_name} vs {right_name}")
            self.status_message.setText("Lap comparison loaded successfully")
            
            logger.info(f"Loaded comparison data for laps {left_lap_id} and {right_lap_id}")
            
        except Exception as e:
            logger.error(f"Error loading comparison laps: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.status_message.setText(f"Error loading lap data: {str(e)}")
            self._set_sample_comparison_data()

    def _calculate_delta_between_laps(self, lap1_data, lap2_data):
        """Calculate delta time between two lap telemetry datasets.
        
        Args:
            lap1_data: List of telemetry points for first lap
            lap2_data: List of telemetry points for second lap
            
        Returns:
            List of delta time values
        """
        try:
            if not lap1_data or not lap2_data:
                return [0]
                
            # Simple implementation - in reality would need sophisticated alignment
            min_len = min(len(lap1_data), len(lap2_data))
            
            # Normalize lengths
            lap1_data = lap1_data[:min_len]
            lap2_data = lap2_data[:min_len]
            
            # Create evenly spaced relative time values if not present
            if not lap1_data or not lap2_data or 'time' not in lap1_data[0] or 'time' not in lap2_data[0]:
                # Simple approximation based on position in the lap
                lap1_times = [i/min_len for i in range(min_len)]
                lap2_times = [i/min_len for i in range(min_len)]
            else:
                lap1_times = [point.get('time', 0) for point in lap1_data]
                lap2_times = [point.get('time', 0) for point in lap2_data]
            
            # Calculate delta at each point (lap2 - lap1)
            delta_data = []
            for i in range(min_len):
                delta = lap2_times[i] - lap1_times[i]
                delta_data.append(delta)
                
            return delta_data
            
        except Exception as e:
            logger.error(f"Error calculating lap delta: {e}")
            return [0]
            
    def _generate_track_map_points(self, session_id=None):
        """Generate track map points for visualization.
        
        Args:
            session_id: Optional session ID to attempt to load track data
            
        Returns:
            List of (x, y) points defining the track outline
        """
        # In a real implementation, would get actual track data from database
        import math
        
        # Create a simple oval track 
        track_points = []
        radius_x = 100
        radius_y = 60
        center_x = 120
        center_y = 80
        
        # Create the main oval shape
        for angle in range(0, 360, 5):
            rad = math.radians(angle)
            x = center_x + radius_x * math.cos(rad)
            y = center_y + radius_y * math.sin(rad)
            track_points.append((x, y))
            
        return track_points
        
    def _generate_turn_data(self):
        """Generate turn data for visualization.
        
        Returns:
            Dictionary mapping turn numbers to positions on track
        """
        import math
        
        # Create sample turn data for visualization
        turn_data = {}
        radius_x = 100
        radius_y = 60
        center_x = 120
        center_y = 80
        
        # Define turn positions
        turn_angles = [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 330]
        
        for i, angle in enumerate(turn_angles, 1):
            rad = math.radians(angle)
            x = center_x + radius_x * math.cos(rad)
            y = center_y + radius_y * math.sin(rad)
            turn_data[i] = {"position": (x, y)}
            
        return turn_data
        
    def _generate_sector_data(self):
        """Generate sector data for visualization.
        
        Returns:
            Dictionary defining speed sectors
        """
        import math
        
        # Create sample sector data for visualization
        radius_x = 100
        radius_y = 60
        center_x = 120
        center_y = 80
        
        # Define speed sectors
        sector_data = {
            "sector1": {
                "speed_category": "LOW",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(0, 60, 5)
                ]
            },
            "sector2": {
                "speed_category": "LOW",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(60, 120, 5)
                ]
            },
            "sector3": {
                "speed_category": "HIGH",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(120, 180, 5)
                ]
            },
            "sector4": {
                "speed_category": "HIGH",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(180, 270, 5)
                ]
            },
            "sector5": {
                "speed_category": "MEDIUM",
                "points": [
                    (center_x + radius_x * math.cos(math.radians(angle)), 
                     center_y + radius_y * math.sin(math.radians(angle)))
                    for angle in range(270, 360, 5)
                ]
            }
        }
        
        return sector_data
        
    def _set_sample_comparison_data(self):
        """Set sample comparison data for the telemetry widget when no real data is available."""
        # Safety check - ensure the widget exists and is properly initialized
        if not hasattr(self, 'telemetry_comparison_widget') or self.telemetry_comparison_widget is None:
            logger.error("Cannot set sample data - telemetry_comparison_widget not initialized")
            return
        
        # Sample driver data
        driver1_data = {
            'name': 'CHARLES LECLERC',
            'team': 'FERRARI',
            'position': '1',
            'lap_time': 83.456,  # 1:23.456
            'gap': -0.321,
            'full_throttle': 81,
            'heavy_braking': 5,
            'cornering': 14
        }
        
        driver2_data = {
            'name': 'CARLOS SAINZ',
            'team': 'FERRARI',
            'position': '2',
            'lap_time': 83.777,  # 1:23.777
            'gap': 0.321,
            'full_throttle': 81,
            'heavy_braking': 5,
            'cornering': 14
        }
        
        try:
            # Set driver data in comparison widget
            self.telemetry_comparison_widget.set_driver_data(True, driver1_data)
            self.telemetry_comparison_widget.set_driver_data(False, driver2_data)
            
            # Create sample speed data (simplified version)
            speed1 = [0]
            speed2 = [0]
            
            # Create a simple speed profile with 100 points
            for i in range(1, 100):
                # Simple example of speed through a lap
                point = i / 100.0
                # Create a basic speed profile with some differences between drivers
                base_speed = 100 + 200 * math.sin(point * math.pi * 3) ** 2
                speed1.append(base_speed + 10 * math.cos(point * math.pi * 10))
                speed2.append(base_speed - 5 * math.sin(point * math.pi * 8))
            
            # Create sample delta data
            delta = [0]
            for i in range(1, 100):
                # Simulate delta time between drivers
                delta.append(delta[-1] + 0.01 * math.sin(i / 5.0))
            
            # Set the data in the comparison widget
            self.telemetry_comparison_widget.set_speed_data(speed1, speed2)
            self.telemetry_comparison_widget.set_delta_data(delta)
            
            # Set track map data
            track_map_points = self._generate_track_map_points()
            turn_data = self._generate_turn_data()
            sector_data = self._generate_sector_data()
            
            if track_map_points:
                self.telemetry_comparison_widget.set_track_data(track_map_points, turn_data, sector_data)
            
            logger.info("Sample telemetry comparison data set successfully")
        except Exception as e:
            logger.error(f"Error setting sample telemetry data: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _setup_monitoring_timer(self):
        """Set up a timer to periodically log pedal values for monitoring."""
        try:
            self.monitor_timer = QTimer()
            self.monitor_timer.timeout.connect(self._log_pedal_values)
            self.monitor_timer.start(30000)  # Log every 30 seconds instead of 5 seconds
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
                    # Fix the format string to properly handle None values
                    throttle_str = f"{throttle:.2f}" if throttle is not None else "N/A"
                    brake_str = f"{brake:.2f}" if brake is not None else "N/A"
                    clutch_str = f"{clutch:.2f}" if clutch is not None else "N/A"
                    
                    logger.debug(f"MONITORING - Current pedal values: Throttle={throttle_str}, "
                              f"Brake={brake_str}, "
                              f"Clutch={clutch_str}")
                else:
                    logger.debug("MONITORING - No pedal values found in latest telemetry")
            else:
                logger.debug("MONITORING - No telemetry data available")
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
                # Only try to update button if it exists
                if hasattr(self, 'connect_button'):
                    self.connect_button.setText("Connect")
                self._update_iracing_status(False)
            return
            
        # Only try to connect if we're not already connected and the method exists
        if hasattr(self.iracing_api, 'check_iracing'):
            try:
                is_connected = self.iracing_api.check_iracing()
                if is_connected:
                    self._is_connected = True
                    # Only try to update button if it exists
                    if hasattr(self, 'connect_button'):
                        self.connect_button.setText("Disconnect")
                    self._update_iracing_status(True)
                    if hasattr(self, 'status_message'):
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
        """Handle raw telemetry updates.
        
        This method is called by the API on a background thread.
        To prevent threading issues, it emits a signal to handle the update on the main thread.
        
        Args:
            telemetry_data (dict): Telemetry data from iRacing
        """
        try:
            # Skip if widget is being destroyed
            if self._is_destroying:
                return
                
            # Emit signal to handle telemetry on main thread
            self.telemetry_update_signal.emit(telemetry_data)
        except Exception as e:
            logger.error(f"Error in telemetry update background handler: {e}")
    
    def _update_iracing_status(self, connected):
        """Update iRacing connection status in UI."""
        # Skip if iracing_status label doesn't exist
        if not hasattr(self, 'iracing_status'):
            logger.debug("Cannot update iRacing status - UI element not found")
            return
            
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
            if has_speed and (not hasattr(self, '_last_display_update') or time.time() - self._last_display_update > 30):
                # Reduced from 5 to 30 seconds
                logger.debug(f"Updating telemetry display with speed: {telemetry_data.get('speed', 0):.1f} km/h")
                self._last_display_update = time.time()
                
            # Update speed value directly in labels
            speed = telemetry_data.get('speed', 0)
            if isinstance(speed, (int, float)):
                # Update speed value text
                if hasattr(self, 'speed_value'):
                    self.speed_value.setText(f"{speed:.1f} km/h")
                    # Removed debug log
                
                # Also update speed gauge if it exists
                if hasattr(self, 'speed_gauge'):
                    self.speed_gauge.set_value(speed)
            
            # Update RPM value directly in labels
            rpm = telemetry_data.get('rpm', 0)
            if isinstance(rpm, (int, float)):
                # Update RPM value text
                if hasattr(self, 'rpm_value'):
                    self.rpm_value.setText(f"{rpm:.0f}")
                    # Removed debug log
                
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
                    # Removed debug log
            
            # Update driver input displays - Throttle, Brake, Clutch
            # Extract input values with defaults
            throttle = telemetry_data.get('throttle', 0)
            brake = telemetry_data.get('brake', 0)
            clutch = telemetry_data.get('clutch', 0)
            steering = telemetry_data.get('steering', 0)
            
            # Ensure values are numerical
            if isinstance(throttle, (int, float)) and isinstance(brake, (int, float)) and isinstance(clutch, (int, float)):
                # Update input trace widget if it exists
                if hasattr(self, 'input_trace'):
                    # Removed debug log
                    self.input_trace.add_data_point(throttle, brake, clutch)
                    # No need to force repaint - the widget handles this safely now
                
                # Update throttle display
                throttle_pct = int(throttle * 100)
                if hasattr(self, 'throttle_value'):
                    self.throttle_value.setText(f"{throttle_pct}%")
                    # No need for forced repaint
                    # Removed debug log
                if hasattr(self, 'throttle_bar'):
                    self.throttle_bar.setValue(throttle_pct)
                    # No need for forced repaint
                
                # Update brake display
                brake_pct = int(brake * 100)
                if hasattr(self, 'brake_value'):
                    self.brake_value.setText(f"{brake_pct}%")
                    # No need for forced repaint
                    # Removed debug log
                if hasattr(self, 'brake_bar'):
                    self.brake_bar.setValue(brake_pct)
                    # No need for forced repaint
                
                # Update clutch display
                clutch_pct = int(clutch * 100)
                if hasattr(self, 'clutch_value'):
                    self.clutch_value.setText(f"{clutch_pct}%")
                    # No need for forced repaint
                    # Removed debug log
                if hasattr(self, 'clutch_bar'):
                    self.clutch_bar.setValue(clutch_pct)
                    # No need for forced repaint
                
                # Update steering angle display
                if isinstance(steering, (int, float)):
                    # Convert radians to degrees for display
                    steering_degrees = steering * 180 / math.pi
                    
                    # Update the text value display
                    if hasattr(self, 'steering_value'):
                        self.steering_value.setText(f"{steering_degrees:.1f}°")
                        # Removed debug log
                    
                    # Update the progress bar - scale to percentage for display (-100 to 100)
                    # Assuming typical max steering angle is ±90 degrees
                    if hasattr(self, 'steering_bar'):
                        # Clamp to -100, 100 range for progress bar
                        steering_pct = max(-100, min(100, int(steering_degrees * (100/90))))
                        self.steering_bar.setValue(steering_pct)
            
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
                    # Removed debug log
            
            # Update last lap time information
            lap_time = telemetry_data.get('lap_time', 0)
            if lap_time and lap_time > 0:
                formatted_time = self._format_time(lap_time)
                if hasattr(self, 'lap_time_value'):
                    self.lap_time_value.setText(formatted_time)
                    # Removed debug log
            
            # Update last lap time information
            last_lap_time = telemetry_data.get('last_lap_time', 0)
            if last_lap_time and last_lap_time > 0:
                formatted_time = self._format_time(last_lap_time)
                if hasattr(self, 'last_lap_value'):
                    self.last_lap_value.setText(formatted_time)
                    if not hasattr(self, '_last_displayed_lap_time') or self._last_displayed_lap_time != last_lap_time:
                        logger.debug(f"Updated last lap time to {formatted_time}")
                        self._last_displayed_lap_time = last_lap_time
            
            # Update best lap time information
            best_lap_time = telemetry_data.get('best_lap_time', 0)
            if best_lap_time and best_lap_time > 0:
                formatted_time = self._format_time(best_lap_time)
                if hasattr(self, 'best_lap_value'):
                    self.best_lap_value.setText(formatted_time)
                    if not hasattr(self, '_best_displayed_lap_time') or self._best_displayed_lap_time != best_lap_time:
                        logger.debug(f"Updated best lap time to {formatted_time}")
                        self._best_displayed_lap_time = best_lap_time
            
            # Update lap count if available
            lap_count = telemetry_data.get('lap_count', 0)
            if lap_count and lap_count > 0:
                if hasattr(self, 'lap_info'):
                    self.lap_info.setText(str(lap_count))
                    if not hasattr(self, '_last_displayed_lap_count') or self._last_displayed_lap_count != lap_count:
                        logger.debug(f"Updated lap count to {lap_count}")
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

    def load_demo_data(self):
        """Load demo telemetry data for visualization testing.
        
        This creates realistic sample data to demonstrate the F1-style visualization
        without requiring real telemetry data.
        """
        import random
        import math
        
        # Set driver information
        self.left_driver = {
            "name": "CHARLES",
            "lastname": "LECLERC",
            "team": "FERRARI",
            "position": "1",
            "lap_time": 83.456,  # 1:23.456
            "gap": -0.321,
            "full_throttle": 81,
            "heavy_braking": 5,
            "cornering": 14,
            "color": QColor(255, 0, 0)  # red for left driver
        }
        
        self.right_driver = {
            "name": "CARLOS",
            "lastname": "SAINZ",
            "team": "FERRARI",
            "position": "2",
            "lap_time": 83.777,  # 1:23.777
            "gap": 0.321,
            "full_throttle": 79,
            "heavy_braking": 6,
            "cornering": 15,
            "color": QColor(255, 215, 0)  # gold for right driver
        }
        
        # Update the UI with driver data
        self.update_driver_display(True)  # Update left driver
        self.update_driver_display(False)  # Update right driver
        
        # Generate simple oval track map with 11 turns
        track_points = []
        num_points = 100
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            # Create oval shape by modifying circle
            x = 200 * math.cos(angle) * (1 + 0.3 * math.cos(2 * angle))
            y = 150 * math.sin(angle) * (1 + 0.1 * math.sin(2 * angle))
            track_points.append((x, y))
            
        # Create turn data
        turn_data = {}
        for turn in range(1, 12):
            idx = (turn - 1) * (num_points // 11)
            turn_data[turn] = {
                "position": track_points[idx],
                "name": f"Turn {turn}"
            }
        
        # Define speed sectors
        sector_data = {
            "sector1": {
                "speed_category": "LOW",
                "points": [track_points[i] for i in range(0, 20)]
            },
            "sector2": {
                "speed_category": "MEDIUM",
                "points": [track_points[i] for i in range(20, 40)]
            },
            "sector3": {
                "speed_category": "HIGH",
                "points": [track_points[i] for i in range(40, 60)]
            },
            "sector4": {
                "speed_category": "HIGH",
                "points": [track_points[i] for i in range(60, 80)]
            },
            "sector5": {
                "speed_category": "MEDIUM",
                "points": [track_points[i] for i in range(80, 100)]
            }
        }
            
        # Generate speed data for both drivers
        # Base speed profile with realistic acceleration/braking patterns
        base_profile = []
        for i in range(200):
            angle = i / 200 * 2 * math.pi
            
            # Create a speed profile that varies with track position
            speed = 250 + 70 * math.sin(angle) - 50 * math.sin(2 * angle)
            
            # Add small random variations
            speed += random.uniform(-5, 5)
            
            # Ensure minimum speed
            speed = max(speed, 80)
            
            base_profile.append(speed)
            
        # Create slightly different profiles for each driver
        speed_data_left = base_profile.copy()
        speed_data_right = []
        
        for i, speed in enumerate(base_profile):
            # Right driver slightly slower in some sections, faster in others
            modifier = math.sin(i / 200 * 2 * math.pi * 3) * 10
            speed_data_right.append(speed + modifier)
            
        # Generate delta data (positive means right driver is slower)
        delta_data = [0]
        for i in range(1, len(speed_data_left)):
            # Calculate time spent on this segment (distance / speed)
            segment_time_left = 1 / speed_data_left[i]  # Assuming equal distance segments
            segment_time_right = 1 / speed_data_right[i]
            
            # Accumulate the delta time
            segment_delta = segment_time_right - segment_time_left
            delta_data.append(delta_data[-1] + segment_delta)
            
        # Scale delta to realistic values (-0.5s to +0.5s range)
        scale = 0.5 / max(abs(min(delta_data)), abs(max(delta_data)))
        delta_data = [d * scale for d in delta_data]
        
        # Set the data
        self.track_map_points = track_points
        self.track_turns = turn_data
        self.track_sectors = sector_data
        self.speed_data_left = speed_data_left
        self.speed_data_right = speed_data_right
        self.delta_data = delta_data
        
        # Force update
        self.update()
        
    def _on_compare_button_clicked(self):
        """Compare the selected laps and show the visualization."""
        # Get selected laps
        left_session_idx = self.left_session_combo.currentIndex()
        left_lap_idx = self.left_lap_combo.currentIndex()
        
        right_session_idx = self.right_session_combo.currentIndex()
        right_lap_idx = self.right_lap_combo.currentIndex()
        
        # Validate selections
        if left_session_idx < 0 or left_lap_idx < 0 or right_session_idx < 0 or right_lap_idx < 0:
            logger.warning("Invalid lap selections for comparison")
            self.lap_info_label.setText("Please select valid laps for comparison")
            return
            
        left_session_id = self.left_session_combo.itemData(left_session_idx)
        left_lap_id = self.left_lap_combo.itemData(left_lap_idx)
        
        right_session_id = self.right_session_combo.itemData(right_session_idx)
        right_lap_id = self.right_lap_combo.itemData(right_lap_idx)
        
        # Check if we have IDs
        if not left_session_id or not left_lap_id or not right_session_id or not right_lap_id:
            logger.warning("Missing data for lap comparison")
            self.lap_info_label.setText("Missing data for selected laps")
            return
            
        # Show comparison
        self.lap_info_label.setText(f"Comparing {self.left_lap_combo.currentText()} vs {self.right_lap_combo.currentText()}")
        self._update_comparison_visualization(left_session_id, left_lap_id, right_session_id, right_lap_id)
        
    def _format_time(self, seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if seconds is None or seconds <= 0:
            return "--:--.---" 
            
        minutes = int(seconds / 60)
        seconds_remainder = seconds % 60
        
        return f"{minutes:02d}:{seconds_remainder:06.3f}"
        
    def _load_demo_data(self):
        """Load demo data to showcase the F1-style telemetry visualization."""
        if hasattr(self, 'telemetry_comparison_widget') and self.telemetry_comparison_widget:
            self.telemetry_comparison_widget.load_demo_data()
            if hasattr(self, 'lap_info_label'):
                self.lap_info_label.setText("Showing F1-style demo visualization")
            logger.info("Loaded F1-style demo visualization data")
        
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

    def load_demo_data(self):
        """Load demo telemetry data for visualization testing.
        
        This creates realistic sample data to demonstrate the F1-style visualization
        without requiring real telemetry data.
        """
        import random
        import math
        
        # Set driver information
        self.left_driver = {
            "name": "CHARLES",
            "lastname": "LECLERC",
            "team": "FERRARI",
            "position": "1",
            "lap_time": 83.456,  # 1:23.456
            "gap": -0.321,
            "full_throttle": 81,
            "heavy_braking": 5,
            "cornering": 14,
            "color": QColor(255, 0, 0)  # red for left driver
        }
        
        self.right_driver = {
            "name": "CARLOS",
            "lastname": "SAINZ",
            "team": "FERRARI",
            "position": "2",
            "lap_time": 83.777,  # 1:23.777
            "gap": 0.321,
            "full_throttle": 79,
            "heavy_braking": 6,
            "cornering": 15,
            "color": QColor(255, 215, 0)  # gold for right driver
        }
        
        # Update the UI with driver data
        self.update_driver_display(True)  # Update left driver
        self.update_driver_display(False)  # Update right driver
        
        # Generate simple oval track map with 11 turns
        track_points = []
        num_points = 100
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            # Create oval shape by modifying circle
            x = 200 * math.cos(angle) * (1 + 0.3 * math.cos(2 * angle))
            y = 150 * math.sin(angle) * (1 + 0.1 * math.sin(2 * angle))
            track_points.append((x, y))
            
        # Create turn data
        turn_data = {}
        for turn in range(1, 12):
            idx = (turn - 1) * (num_points // 11)
            turn_data[turn] = {
                "position": track_points[idx],
                "name": f"Turn {turn}"
            }
        
        # Define speed sectors
        sector_data = {
            "sector1": {
                "speed_category": "LOW",
                "points": [track_points[i] for i in range(0, 20)]
            },
            "sector2": {
                "speed_category": "MEDIUM",
                "points": [track_points[i] for i in range(20, 40)]
            },
            "sector3": {
                "speed_category": "HIGH",
                "points": [track_points[i] for i in range(40, 60)]
            },
            "sector4": {
                "speed_category": "HIGH",
                "points": [track_points[i] for i in range(60, 80)]
            },
            "sector5": {
                "speed_category": "MEDIUM",
                "points": [track_points[i] for i in range(80, 100)]
            }
        }
            
        # Generate speed data for both drivers
        # Base speed profile with realistic acceleration/braking patterns
        base_profile = []
        for i in range(200):
            angle = i / 200 * 2 * math.pi
            
            # Create a speed profile that varies with track position
            speed = 250 + 70 * math.sin(angle) - 50 * math.sin(2 * angle)
            
            # Add small random variations
            speed += random.uniform(-5, 5)
            
            # Ensure minimum speed
            speed = max(speed, 80)
            
            base_profile.append(speed)
            
        # Create slightly different profiles for each driver
        speed_data_left = base_profile.copy()
        speed_data_right = []
        
        for i, speed in enumerate(base_profile):
            # Right driver slightly slower in some sections, faster in others
            modifier = math.sin(i / 200 * 2 * math.pi * 3) * 10
            speed_data_right.append(speed + modifier)
            
        # Generate delta data (positive means right driver is slower)
        delta_data = [0]
        for i in range(1, len(speed_data_left)):
            # Calculate time spent on this segment (distance / speed)
            segment_time_left = 1 / speed_data_left[i]  # Assuming equal distance segments
            segment_time_right = 1 / speed_data_right[i]
            
            # Accumulate the delta time
            segment_delta = segment_time_right - segment_time_left
            delta_data.append(delta_data[-1] + segment_delta)
            
        # Scale delta to realistic values (-0.5s to +0.5s range)
        scale = 0.5 / max(abs(min(delta_data)), abs(max(delta_data)))
        delta_data = [d * scale for d in delta_data]
        
        # Set the data
        self.track_map_points = track_points
        self.track_turns = turn_data
        self.track_sectors = sector_data
        self.speed_data_left = speed_data_left
        self.speed_data_right = speed_data_right
        self.delta_data = delta_data
        
        # Force update
        self.update()

    def _update_gear_display(self, gear_value):
        """Update the gear display."""
        try:
            if gear_value == 0:
                gear_text = "N"
            elif gear_value == -1:
                gear_text = "R"
            else:
                gear_text = str(gear_value)
                
            self.gear_value.setText(gear_text)
            logger.debug(f"Updated gear display to {gear_text}")
        except Exception as e:
            logger.error(f"Error updating gear display: {e}")
            
    def _update_pedal_displays(self, throttle, brake, clutch, steering):
        """Update the pedal input displays."""
        try:
            # Update throttle display
            if throttle is not None:
                throttle_pct = int(throttle * 100)
                self.throttle_value.setText(f"{throttle_pct}%")
                self.throttle_bar.setValue(throttle_pct)
                logger.debug(f"Updated throttle display to {throttle_pct}%")
            
            # Update brake display
            if brake is not None:
                brake_pct = int(brake * 100)
                self.brake_value.setText(f"{brake_pct}%")
                self.brake_bar.setValue(brake_pct)
                logger.debug(f"Updated brake display to {brake_pct}%")
            
            # Update clutch display
            if clutch is not None:
                clutch_pct = int(clutch * 100)
                self.clutch_value.setText(f"{clutch_pct}%")
                self.clutch_bar.setValue(clutch_pct)
                logger.debug(f"Updated clutch display to {clutch_pct}%")
            
            # Update steering display
            if steering is not None:
                # Convert to degrees with 1 decimal place
                steering_deg = round(steering * 450, 1)  # Assuming 450 degrees lock-to-lock
                self.steering_value.setText(f"{steering_deg}°")
                logger.debug(f"Updated steering display to {steering_deg}°")
                
        except Exception as e:
            logger.error(f"Error updating pedal displays: {e}")



