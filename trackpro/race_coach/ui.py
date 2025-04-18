import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTabWidget, QGroupBox,
                             QSplitter, QComboBox, QStatusBar, QMainWindow, QMessageBox, QApplication, QGridLayout, QFrame, QFormLayout, QCheckBox, QProgressBar, QSizePolicy, QSpacerItem, QScrollArea, QStackedWidget, QLineEdit, QSlider)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QUrl  # Import QUrl
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient, QConicalGradient, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView  # Add direct import
import time
import threading
import weakref
import numpy as np  # Add numpy import for array handling
import json
import platform
import math
import random  # Import random module for demo animations
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

class SteeringWheelWidget(GaugeBase):
    """Widget for steering wheel visualization."""
    
    def __init__(self, parent=None):
        super().__init__(-1.0, 1.0, parent)  # Steering ranges from -1.0 to 1.0
        self.setObjectName("SteeringWheelWidget")
        self.title = "Steering"
        
        # Special colors and settings for the steering display
        self.wheel_color = QColor(50, 50, 50)  # Dark gray for wheel
        self.wheel_rim_color = QColor(80, 80, 80)  # Lighter gray for rim
        self.wheel_marker_color = QColor(255, 0, 0)  # Red for center marker
        self.steering_angle = 0.0  # Current steering angle in radians
        # Set max rotation to handle 1080-degree wheels (convert to radians)
        # 1080 degrees = 3 * 360 degrees = 3 * 2π radians ≈ 18.85 radians 
        self.max_rotation = 3.0 * math.pi  # Maximum steering wheel rotation in radians (1080 degrees)
        
        # Set minimum size for proper rendering
        self.setMinimumSize(180, 180)
        
        # Performance optimization: cache the rendered wheel
        self._cached_wheel = None
        self._last_size = (0, 0)
        self._last_angle = None
        
    def set_value(self, value):
        """Set the current steering wheel angle (-1.0 to 1.0)."""
        # Call the parent method to handle normalization
        old_value = self.value
        super().set_value(value)
        
        # Only update the angle if the value has actually changed
        if old_value != self.value:
            self.steering_angle = value * self.max_rotation
            self._last_angle = None  # Invalidate the cache when angle changes
            self.update()  # Trigger a repaint
        
    def set_max_rotation(self, max_rotation):
        """Set the maximum rotation angle in radians."""
        if self.max_rotation != max_rotation:
            self.max_rotation = max_rotation
            self._last_angle = None  # Invalidate the cache
            self.update()
        
    def paintEvent(self, event):
        """Paint the steering wheel visualization."""
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
            
            # Draw a simple line indicating steering direction
            if width >= 40 and height >= 40:
                center_x = width / 2
                center_y = height / 2
                line_length = min(width, height) / 2 - 5
                
                # Calculate the steering angle for visualization
                angle = self.steering_angle
                
                # Line endpoint
                end_x = center_x + line_length * math.sin(angle)
                end_y = center_y - line_length * math.cos(angle)
                
                # Draw the line
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawLine(int(center_x), int(center_y), int(end_x), int(end_y))
            
            return
        
        # Regular rendering for normal sizes
        # Calculate dimensions and center point
        center_x = width / 2
        center_y = height / 2
        
        # Check if we need to redraw the cached wheel
        current_size = (width, height)
        if self._cached_wheel is None or self._last_size != current_size or self._last_angle != self.steering_angle:
            # Clear the old cache if size changed
            if self._last_size != current_size:
                self._cached_wheel = None
                
            self._last_size = current_size
            self._last_angle = self.steering_angle
            
            # Create new pixmap cache for the wheel at current size and angle
            self._cached_wheel = QPixmap(width, height)
            self._cached_wheel.fill(Qt.transparent)
            
            # Create a painter for the cached wheel
            cache_painter = QPainter(self._cached_wheel)
            cache_painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw the wheel on the cached pixmap
            self._draw_wheel(cache_painter, width, height, center_x, center_y)
            
            # End painting on the cache
            cache_painter.end()
        
        # Draw the cached wheel to the widget
        painter.drawPixmap(0, 0, self._cached_wheel)
        
        # Draw the steering angle indicator and bar - always draw these directly
        self._draw_angle_indicator(painter, width, height, center_x, center_y)
        
    def _draw_wheel(self, painter, width, height, center_x, center_y):
        """Draw the steering wheel on the given painter."""
        wheel_radius = min(width, height) / 2 * 0.85  # 85% of the available space
        
        # Save the painter state to restore later
        painter.save()
        
        # Set up transformation for wheel rotation
        painter.translate(center_x, center_y)
        painter.rotate(-self.steering_angle * 180 / math.pi)  # Convert to degrees for rotate()
        
        # Draw steering wheel outer rim
        pen_width = max(2, min(5, wheel_radius / 20))
        painter.setPen(QPen(self.wheel_rim_color, pen_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), wheel_radius, wheel_radius)
        
        # Draw wheel spokes
        spoke_width = max(2, min(4, wheel_radius / 30))
        painter.setPen(QPen(self.wheel_rim_color, spoke_width))
        
        # Cross spokes
        inner_radius = wheel_radius * 0.2  # Small central hub
        
        # Horizontal spoke
        painter.drawLine(int(-wheel_radius), 0, int(-inner_radius), 0)
        painter.drawLine(int(inner_radius), 0, int(wheel_radius), 0)
        
        # Vertical spoke
        painter.drawLine(0, int(-wheel_radius), 0, int(-inner_radius))
        painter.drawLine(0, int(inner_radius), 0, int(wheel_radius))
        
        # Diagonal spokes
        angle = math.pi / 4  # 45 degrees
        x1 = wheel_radius * math.cos(angle)
        y1 = wheel_radius * math.sin(angle)
        x2 = inner_radius * math.cos(angle)
        y2 = inner_radius * math.sin(angle)
        
        # Draw 4 diagonal spokes
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.drawLine(int(-x1), int(y1), int(-x2), int(y2))
        painter.drawLine(int(x1), int(-y1), int(x2), int(-y2))
        painter.drawLine(int(-x1), int(-y1), int(-x2), int(-y2))
        
        # Draw central hub
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.wheel_color))
        painter.drawEllipse(QPointF(0, 0), inner_radius, inner_radius)
        
        # Draw center marker
        painter.setPen(QPen(self.wheel_marker_color, spoke_width))
        marker_size = inner_radius * 0.6
        painter.drawLine(0, int(-marker_size), 0, int(marker_size))
        
        # Restore painter state
        painter.restore()
        
    def _draw_angle_indicator(self, painter, width, height, center_x, center_y):
        """Draw the angle indicator and steering bar."""
        wheel_radius = min(width, height) / 2 * 0.85
        
        # Draw steering angle indicator outside the wheel
        angle_text = f"{(self.steering_angle * 180 / math.pi):.1f}°"
        painter.setPen(QPen(self.text_color))
        painter.setFont(QFont("Arial", 10))
        
        # Position text below the wheel
        text_y = center_y + wheel_radius + 20
        painter.drawText(0, int(text_y), width, 20, Qt.AlignCenter, angle_text)
        
        # Draw title
        title_font = painter.font()
        title_font.setPointSize(12)
        painter.setFont(title_font)
        painter.drawText(0, 15, width, 20, Qt.AlignCenter, self.title)
        
        # Draw steering angle bar at the bottom
        bar_width = width * 0.8
        bar_height = max(8, min(12, height / 20))
        bar_x = (width - bar_width) / 2
        bar_y = height - bar_height - 10
        
        # Draw the bar background
        painter.setPen(QPen(QColor(60, 60, 60)))
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(int(bar_x), int(bar_y), int(bar_width), int(bar_height))
        
        # Draw the center line
        center_line_x = bar_x + bar_width / 2
        painter.setPen(QPen(QColor(150, 150, 150)))
        painter.drawLine(int(center_line_x), int(bar_y - 3), int(center_line_x), int(bar_y + bar_height + 3))
        
        # Draw the current position indicator
        # Apply a visualization scaling factor to make the bar more responsive 
        # This makes the bar show more reasonable deflection for typical steering inputs
        # Most racing games only use a fraction of the wheel's physical rotation range
        visualization_scale = 0.4  # This means full bar deflection at 40% of max rotation
        
        # Map the range [-max_rotation*visualization_scale, +max_rotation*visualization_scale] to [0, 1]
        # This provides better visual feedback for actual in-game steering
        if self.max_rotation > 0:
            scaled_rotation = self.max_rotation * visualization_scale
            true_normalized = (self.steering_angle / scaled_rotation + 1.0) / 2.0
            # Clamp to ensure the bar stays within bounds
            true_normalized = max(0.0, min(1.0, true_normalized))
        else:
            true_normalized = 0.5 # Center if max_rotation is zero
            
        position = bar_x + bar_width * true_normalized
        
        # Use different colors for left and right
        if self.steering_angle < 0:
            indicator_color = QColor(0, 150, 255)  # Blue for left turns
        else:
            indicator_color = QColor(255, 100, 0)  # Orange for right turns
            
        indicator_width = bar_width / 10
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(indicator_color))
        painter.drawRect(int(center_line_x), int(bar_y), int((position - center_line_x)), int(bar_height))

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
            # Reverse clutch value to make it display in the same direction as throttle and brake
            self.clutch_data[-1] = 1.0 - clutch  # Reverse the clutch value
        
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
        
        # Calculate drawing area - increase padding for better spacing
        padding = 20
        left_padding = 35  # More space for y-axis labels
        right_padding = 15
        top_padding = 20   # More space for title
        bottom_padding = 25  # More space for x-axis label
        
        graph_width = width - (left_padding + right_padding)
        graph_height = height - (top_padding + bottom_padding)
        
        # Draw background (already handled by palette)
        
        # Draw title text at top with better positioning
        title_font = painter.font()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.white))
        painter.drawText(int(width/2 - 75), 15, "Input Trace")
        
        # Draw axis labels
        axis_font = painter.font()
        axis_font.setPointSize(8)
        painter.setFont(axis_font)
        
        # Y-axis labels with better positioning
        painter.drawText(5, top_padding - 5, "100%")
        painter.drawText(5, int(top_padding + graph_height / 2), "50%")
        painter.drawText(5, top_padding + graph_height + 5, "0%")
        
        # X-axis label - Time with better positioning
        painter.drawText(int(width / 2 - 15), height - 5, "Time →")
        
        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1, Qt.DashLine))
        
        # Horizontal grid lines at 25%, 50%, 75%
        for y_pct in [0.25, 0.5, 0.75]:
            y = top_padding + (1.0 - y_pct) * graph_height
            painter.drawLine(left_padding, int(y), left_padding + graph_width, int(y))
        
        # Vertical grid lines every 25% of width
        for x_pct in [0.25, 0.5, 0.75]:
            x = left_padding + x_pct * graph_width
            painter.drawLine(int(x), top_padding, int(x), top_padding + graph_height)
            
        # Draw border
        painter.setPen(QPen(self.grid_color.lighter(120), 1))
        painter.drawRect(left_padding, top_padding, graph_width, graph_height)
        
        # Draw data traces if we have any data
        if np.max(throttle_data) > 0 or np.max(brake_data) > 0 or np.max(clutch_data) > 0:
            # Calculate points for each data set
            data_len = len(throttle_data)
            x_step = graph_width / (data_len - 1) if data_len > 1 else graph_width
            
            # Draw throttle trace
            throttle_pen = QPen(self.throttle_color, 2)
            painter.setPen(throttle_pen)
            
            for i in range(data_len - 1):
                x1 = left_padding + i * x_step
                y1 = top_padding + graph_height - (throttle_data[i] * graph_height)
                x2 = left_padding + (i + 1) * x_step
                y2 = top_padding + graph_height - (throttle_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
            # Draw brake trace
            brake_pen = QPen(self.brake_color, 2)
            painter.setPen(brake_pen)
            
            for i in range(data_len - 1):
                x1 = left_padding + i * x_step
                y1 = top_padding + graph_height - (brake_data[i] * graph_height)
                x2 = left_padding + (i + 1) * x_step
                y2 = top_padding + graph_height - (brake_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
            # Draw clutch trace
            clutch_pen = QPen(self.clutch_color, 2)
            painter.setPen(clutch_pen)
            
            for i in range(data_len - 1):
                x1 = left_padding + i * x_step
                y1 = top_padding + graph_height - (clutch_data[i] * graph_height)
                x2 = left_padding + (i + 1) * x_step
                y2 = top_padding + graph_height - (clutch_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                
        # Draw legend with better positioning and spacing
        legend_width = 80
        legend_padding = 10
        legend_height = 15
        legend_spacing = 15
        # Move legend to top-left corner instead of right side
        legend_x = left_padding + 10
        legend_y = top_padding + 10
        
        # Draw legend background for better visibility
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30, 180)))
        painter.drawRect(legend_x - 5, legend_y - 5, legend_width, 3 * legend_height + 2 * legend_spacing + 10)
        
        # Throttle
        painter.setPen(self.throttle_color)
        painter.drawLine(legend_x, legend_y, legend_x + 15, legend_y)
        painter.drawText(legend_x + 20, legend_y + 5, "Throttle")
        
        # Brake
        painter.setPen(self.brake_color)
        painter.drawLine(legend_x, legend_y + legend_height + legend_spacing, legend_x + 15, legend_y + legend_height + legend_spacing)
        painter.drawText(legend_x + 20, legend_y + legend_height + legend_spacing + 5, "Brake")
        
        # Clutch
        painter.setPen(self.clutch_color)
        painter.drawLine(legend_x, legend_y + 2 * (legend_height + legend_spacing), legend_x + 15, legend_y + 2 * (legend_height + legend_spacing))
        painter.drawText(legend_x + 20, legend_y + 2 * (legend_height + legend_spacing) + 5, "Clutch")

# --- New Widget for Speed Trace Graph ---
class SpeedTraceGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_data_left = []
        self.speed_data_right = []
        self.left_driver_color = QColor(255, 0, 0)
        self.right_driver_color = QColor(255, 215, 0)
        self.left_driver_name = "Driver 1"
        self.right_driver_name = "Driver 2"
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """)

    def set_data(self, speed_left, speed_right, left_color, right_color, left_name, right_name):
        self.speed_data_left = speed_left
        self.speed_data_right = speed_right
        self.left_driver_color = left_color
        self.right_driver_color = right_color
        self.left_driver_name = left_name
        self.right_driver_name = right_name
        self.update() # Trigger repaint when data changes

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()

        # Define graph area (relative to this widget's coordinates)
        speed_top = 0
        speed_height = height
        speed_bottom = height

        # Draw background is handled by stylesheet

        # Add subtle grid pattern for F1 style
        painter.setPen(QPen(QColor(40, 40, 40, 180), 1))
        grid_spacing_h = width / 20 if width > 0 else 0
        for i in range(21):
            x = i * grid_spacing_h
            painter.drawLine(int(x), int(speed_top), int(x), int(speed_bottom))

        # Draw speed trace labels (every 50 km/h)
        max_speed = 350  # Default headroom
        # Safely calculate max_speed
        all_speeds = []
        if self.speed_data_left: all_speeds.extend(filter(lambda x: isinstance(x, (int, float)), self.speed_data_left))
        if self.speed_data_right: all_speeds.extend(filter(lambda x: isinstance(x, (int, float)), self.speed_data_right))
        if all_speeds:
             max_speed = max(max_speed, max(all_speeds) * 1.1)
        max_speed = math.ceil(max_speed / 50.0) * 50 if max_speed > 0 else 50

        painter.setPen(QPen(QColor(70, 70, 70)))
        painter.setFont(QFont("Arial", 8))
        if max_speed > 0:
            for speed in range(0, int(max_speed) + 50, 50):
                y = speed_bottom - (speed / max_speed) * speed_height
                painter.drawLine(0, int(y), width, int(y))
                painter.setPen(QPen(QColor(180, 180, 180)))
                painter.drawText(5, int(y - 2), f"{speed}")
                painter.setPen(QPen(QColor(70, 70, 70)))

        # Label the speed trace
        painter.setPen(QPen(QColor(220, 220, 220)))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(10, int(speed_top + 20), "SPEED (km/h)")

        # Draw segment labels for speed categories
        segment_labels = ["LOW SPEED", "MEDIUM SPEED", "HIGH SPEED", "HIGH SPEED", "MEDIUM SPEED", "LOW SPEED"]
        if width > 0 and len(segment_labels) > 0:
            segment_width = width / len(segment_labels)
            segment_colors = {
                "LOW SPEED": QColor(200, 40, 40, 20),
                "MEDIUM SPEED": QColor(200, 200, 40, 20),
                "HIGH SPEED": QColor(40, 200, 40, 20)
            }
            painter.setFont(QFont("Arial", 8))
            for i, label in enumerate(segment_labels):
                x = i * segment_width
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(segment_colors.get(label, QColor(0,0,0,0))))
                painter.drawRect(int(x), int(speed_top), int(segment_width), int(speed_height))
                painter.setPen(QPen(QColor(180, 180, 180)))
                text_width = painter.fontMetrics().width(label)
                painter.drawText(int(x + (segment_width - text_width)/2), int(speed_top + 15), label)
                if i > 0:
                    painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
                    painter.drawLine(int(i * segment_width), int(speed_top), int(i * segment_width), int(speed_bottom))

        # Draw speed traces with improved styling
        line_width = 3
        # Check if data exists and has enough points
        has_left_data = self.speed_data_left and len(self.speed_data_left) > 1
        has_right_data = self.speed_data_right and len(self.speed_data_right) > 1

        if not has_left_data or not has_right_data:
            painter.setPen(QPen(QColor(240, 240, 240)))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(QRectF(0, speed_top, width, speed_height), Qt.AlignCenter, "Speed Comparison Data Missing")
        else:
            # Draw left driver's speed trace
            if max_speed > 0:
                try:
                    points = []
                    x_step = width / (len(self.speed_data_left) - 1)
                    for i, speed in enumerate(self.speed_data_left):
                        # Ensure speed is a number before calculating y
                        if isinstance(speed, (int, float)):
                             y = speed_bottom - (speed / max_speed) * speed_height
                             points.append((i * x_step, y))
                        else:
                             logger.warning(f"Non-numeric speed value in left data at index {i}: {speed}")

                    shadow_pen = QPen(QColor(0, 0, 0, 150), line_width + 2)
                    painter.setPen(shadow_pen)
                    for i in range(len(points) - 1):
                        painter.drawLine(int(points[i][0]), int(points[i][1]) + 2, int(points[i+1][0]), int(points[i+1][1]) + 2)
                    left_color = QColor(self.left_driver_color)
                    left_color.setAlpha(255)
                    painter.setPen(QPen(left_color, line_width))
                    for i in range(len(points) - 1):
                        painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i+1][0]), int(points[i+1][1]))
                except Exception as e:
                    logger.error(f"Error drawing left driver speed trace: {e}")
            
            # Draw right driver's speed trace
            if max_speed > 0:
                try:
                    points = []
                    x_step = width / (len(self.speed_data_right) - 1)
                    for i, speed in enumerate(self.speed_data_right):
                         # Ensure speed is a number before calculating y
                        if isinstance(speed, (int, float)):
                             y = speed_bottom - (speed / max_speed) * speed_height
                             points.append((i * x_step, y))
                        else:
                             logger.warning(f"Non-numeric speed value in right data at index {i}: {speed}")

                    shadow_pen = QPen(QColor(0, 0, 0, 150), line_width + 2)
                    painter.setPen(shadow_pen)
                    for i in range(len(points) - 1):
                        painter.drawLine(int(points[i][0]), int(points[i][1]) + 2, int(points[i+1][0]), int(points[i+1][1]) + 2)
                    right_color = QColor(self.right_driver_color)
                    right_color.setAlpha(255)
                    painter.setPen(QPen(right_color, line_width))
                    for i in range(len(points) - 1):
                        painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i+1][0]), int(points[i+1][1]))
                except Exception as e:
                    logger.error(f"Error drawing right driver speed trace: {e}")
            
            # Add driver color indicators
            try:
                legend_y = speed_top + 20
                legend_width = 30
                legend_height = 2
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.left_driver_color))
                painter.drawRect(int(width - 120), int(legend_y), legend_width, legend_height)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawText(int(width - 120 + legend_width + 5), int(legend_y + 4), self.left_driver_name)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.right_driver_color))
                painter.drawRect(int(width - 120), int(legend_y + 15), legend_width, legend_height)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawText(int(width - 120 + legend_width + 5), int(legend_y + 19), self.right_driver_name)
            except Exception as e:
                logger.error(f"Error drawing speed trace legend: {e}")
# --- End New Widget ---

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
        
        # Speed trace widget (custom class)
        self.speed_trace_widget = SpeedTraceGraphWidget()
        # Stylesheet is now set within SpeedTraceGraphWidget
        
        # Delta widget (custom class)
        self.delta_widget = DeltaGraphWidget()
        # Stylesheet is now set within DeltaGraphWidget
        
        bottom_section.addWidget(self.speed_trace_widget, 3)
        bottom_section.addWidget(self.delta_widget, 1)
        
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
    
    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        minutes = int(time_in_seconds // 60)
        seconds = int(time_in_seconds % 60)
        milliseconds = int((time_in_seconds % 1) * 1000)
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"
    
    def set_speed_data(self, left_data, right_data):
        """Set the speed data for both drivers and update the child widget."""
        self.speed_data_left = left_data
        self.speed_data_right = right_data
        
        # Pass data to the child widget
        if hasattr(self, 'speed_trace_widget'):
            self.speed_trace_widget.set_data(
                self.speed_data_left,
                self.speed_data_right,
                self.left_driver.get("color", QColor(255,0,0)),
                self.right_driver.get("color", QColor(255,215,0)),
                self.left_driver.get("name", "Driver 1"),
                self.right_driver.get("name", "Driver 2")
            )
        
        # Auto analyze the telemetry when new data is set (if needed)
        # self.analyze_telemetry() 
        self.update() # Update parent widget if necessary
        
    def set_delta_data(self, delta_data):
        """Set the delta time data and update the child widget."""
        self.delta_data = delta_data
        
        # Pass data to the child widget
        if hasattr(self, 'delta_widget'):
            self.delta_widget.set_data(delta_data)
            
        # Re-analyze with new delta data (if needed)
        # self.analyze_telemetry()
        self.update() # Update parent widget if necessary

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
            
            # Define areas for speed and delta graphs (These are now handled by child widgets)
            # speed_top = track_map_bottom + 20
            # speed_height = height * 0.25
            # speed_bottom = speed_top + speed_height
            
            # delta_top = speed_bottom + 10
            # delta_height = height * 0.15
            # delta_bottom = delta_top + delta_height
            
            # --- Speed and Delta graph drawing logic is now in child widgets ---
            # --- REMOVED all drawing code from here down related to speed/delta graphs --- 
            
        except Exception as e:
            # Log error but don't crash the application
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in TelemetryComparisonWidget.paintEvent: {e}")
            import traceback
            logger.error(traceback.format_exc())

# --- New Widget for Delta Graph ---
class DeltaGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.delta_data = []
        self.setMinimumHeight(50)
        self.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """)

    def set_data(self, delta_data):
        # Ensure delta_data is a list of numbers, handle potential None or non-numeric values
        if isinstance(delta_data, list):
            self.delta_data = [d for d in delta_data if isinstance(d, (int, float))]
        else:
            self.delta_data = []
            logger.warning(f"Received non-list delta_data: {type(delta_data)}")
        self.update() # Trigger repaint when data changes

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        
        # Define graph area (relative to this widget's coordinates)
        delta_top = 0
        delta_height = height
        delta_bottom = height
        
        # Draw background is handled by stylesheet

        # Add subtle grid pattern for delta graph too
        painter.setPen(QPen(QColor(40, 40, 40, 180), 1))
        grid_spacing_h = width / 20 if width > 0 else 0
        for i in range(21):
            x = i * grid_spacing_h
            painter.drawLine(int(x), int(delta_top), int(x), int(delta_bottom))

        # Draw delta graph with F1-style enhancements
        line_width = 3
        # Check if delta_data exists and has enough points
        if not self.delta_data or len(self.delta_data) <= 1:
            painter.setPen(QPen(QColor(240, 240, 240)))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(QRectF(0, delta_top, width, delta_height), Qt.AlignCenter, "Delta Time Data Missing")
        else:
            # Find max delta for scaling
            max_delta = 0.5 # Default scale
            try: 
                 min_val = min(self.delta_data)
                 max_val = max(self.delta_data)
                 max_abs_delta = max(abs(min_val), abs(max_val))
                 max_delta = max(max_abs_delta, 0.5) 
                 max_delta = math.ceil(max_delta / 0.5) * 0.5 
            except (ValueError, TypeError): 
                 logger.warning(f"Could not calculate max delta from data: {self.delta_data[:10]}...")
                 pass # Keep default max_delta
            
            # Draw horizontal bands
            band_colors = [
                QColor(0, 150, 0, 15),  # Green band for faster
                QColor(150, 0, 0, 15)   # Red band for slower
            ]
            painter.setPen(Qt.NoPen)
            zero_y = delta_top + delta_height / 2
            painter.setBrush(band_colors[0]) 
            painter.drawRect(0, int(zero_y), int(width), int(delta_height / 2))
            painter.setBrush(band_colors[1]) 
            painter.drawRect(0, int(delta_top), int(width), int(delta_height / 2))
            
            # Draw horizontal line at zero
            painter.setPen(QPen(QColor(220, 220, 220), 1))
            painter.drawLine(0, int(zero_y), width, int(zero_y))
            
            # Labels
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(10, int(delta_top + 15), "DELTA (seconds)")
            painter.setFont(QFont("Arial", 8))
            painter.setPen(QPen(QColor(0, 200, 0)))
            painter.drawText(int(width - 70), int(delta_bottom - 5), "FASTER")
            painter.setPen(QPen(QColor(200, 0, 0)))
            painter.drawText(int(width - 70), int(delta_top + 15), "SLOWER")
            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.drawText(5, int(delta_top + 15), f"+{max_delta:.2f}")
            painter.drawText(5, int(delta_bottom - 5), f"-{max_delta:.2f}")
            painter.drawText(5, int(zero_y + 4), "0.00")
            
            # Horizontal grid lines
            painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
            if max_delta > 0: 
                step = max_delta / 2
                for i in range(1, 3):
                    y_pos = zero_y - (i * step / max_delta) * (delta_height / 2)
                    painter.drawLine(0, int(y_pos), width, int(y_pos))
                    y_neg = zero_y + (i * step / max_delta) * (delta_height / 2)
                    painter.drawLine(0, int(y_neg), width, int(y_neg))
            
            # Draw the delta line segments
            if width > 0 and max_delta > 0:
                x_step = width / (len(self.delta_data) - 1) if len(self.delta_data) > 1 else 0
                current_segment = []
                last_state = None

                for i, delta in enumerate(self.delta_data):
                     x = i * x_step
                     # Calculate y-position: zero in the middle, negative (faster) below, positive (slower) above
                     y = zero_y - (delta / max_delta) * (delta_height / 2)
                     
                     # Determine point state for coloring
                     state = "zero" if abs(delta) < 0.01 else "positive" if delta > 0 else "negative"
                     
                     # If state changes or first point, start a new segment
                     if state != last_state or i == 0:
                         if current_segment:
                             # Draw the segment with a color based on its state
                             if last_state == "positive":
                                 painter.setPen(QPen(QColor(200, 50, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                             elif last_state == "negative":
                                 painter.setPen(QPen(QColor(50, 200, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                             else:
                                 painter.setPen(QPen(QColor(200, 200, 200), line_width, Qt.SolidLine, Qt.RoundCap))
                             
                             # Draw lines between points in the segment
                             for j in range(len(current_segment) - 1):
                                 p1, p2 = current_segment[j], current_segment[j+1]
                                 painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
                         
                         # Start new segment
                         current_segment = [(x, y)]
                         last_state = state
                     else:
                         # Continue the segment
                         current_segment.append((x, y))
                
                # Draw the final segment if any
                if current_segment:
                    if last_state == "positive":
                        painter.setPen(QPen(QColor(200, 50, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                    elif last_state == "negative":
                        painter.setPen(QPen(QColor(50, 200, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                    else:
                        painter.setPen(QPen(QColor(200, 200, 200), line_width, Qt.SolidLine, Qt.RoundCap))
                    
                    for j in range(len(current_segment) - 1):
                        p1, p2 = current_segment[j], current_segment[j+1]
                        painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

    def load_demo_data(self):
        """Load demo telemetry data for visualization testing."""
        try:
            import random
            import math
            
            logger.info("Loading F1-style demo visualization data")
            
            # Set driver information
            left_driver_info = {
                "name": "CHARLES", "lastname": "LECLERC", "team": "FERRARI", "position": "1",
                "lap_time": 83.456, "gap": -0.321, "full_throttle": 81, "heavy_braking": 5,
                "cornering": 14, "color": QColor(255, 0, 0)
            }
            right_driver_info = {
                "name": "CARLOS", "lastname": "SAINZ", "team": "FERRARI", "position": "2",
                "lap_time": 83.777, "gap": 0.321, "full_throttle": 79, "heavy_braking": 6,
                "cornering": 15, "color": QColor(255, 215, 0)
            }
            
            # Update the driver displays
            self.set_driver_data(True, left_driver_info)
            self.set_driver_data(False, right_driver_info)

            # Generate track data
            track_points = []
            num_points = 100
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                x = 200 * math.cos(angle) * (1 + 0.3 * math.cos(2 * angle))
                y = 150 * math.sin(angle) * (1 + 0.1 * math.sin(2 * angle))
                track_points.append((x, y))
            
            # Generate turn data
            turn_data = {}
            for turn in range(1, 12):
                idx = (turn - 1) * (num_points // 11)
                turn_data[turn] = {"position": track_points[idx], "name": f"Turn {turn}"}
            
            # Set track data
            sector_data = {}  # Would populate in a real implementation
            self.set_track_data(track_points, turn_data, sector_data)
            
            # Generate speed data
            base_profile = []
            num_speed_points = 200
            for i in range(num_speed_points):
                angle = i / num_speed_points * 2 * math.pi
                speed = 250 + 70 * math.sin(angle) - 50 * math.sin(2 * angle)
                speed += random.uniform(-5, 5)
                speed = max(speed, 80)
                base_profile.append(speed)
            
            speed_data_left = base_profile[:]
            speed_data_right = [s + math.sin(i/num_speed_points*2*math.pi*3)*10 for i, s in enumerate(base_profile)]
            
            # Generate delta data
            delta_data = [0]
            if speed_data_left and speed_data_right:
                min_len = min(len(speed_data_left), len(speed_data_right))
                for i in range(1, min_len):
                    # Avoid division by zero for delta calculation
                    speed_l = max(1, speed_data_left[i])
                    speed_r = max(1, speed_data_right[i])
                    segment_time_left = 1 / speed_l
                    segment_time_right = 1 / speed_r
                    segment_delta = segment_time_right - segment_time_left
                    delta_data.append(delta_data[-1] + segment_delta)
                
                # Scale delta
                max_abs_delta = max(abs(min(delta_data)), abs(max(delta_data)))
                if max_abs_delta > 0:
                    scale = 0.5 / max_abs_delta
                    delta_data = [d * scale for d in delta_data]
            
            # Pass data to the child widgets
            if hasattr(self, 'speed_trace_widget') and self.speed_trace_widget:
                self.speed_trace_widget.set_data(
                    speed_data_left,
                    speed_data_right,
                    left_driver_info["color"],
                    right_driver_info["color"],
                    left_driver_info["name"],
                    right_driver_info["name"]
                )
            
            if hasattr(self, 'delta_widget') and self.delta_widget:
                self.delta_widget.set_data(delta_data)
            
            # Update display
            self.update()
            QApplication.processEvents()
            
            logger.info("F1-style demo visualization data loaded")
            
        except Exception as e:
            logger.error(f"Error in load_demo_data: {e}")
            import traceback
            logger.error(traceback.format_exc())

# --- End New Widget ---

class RaceCoachWidget(QWidget):
    """Main container widget for Race Coach functionality.
    
    This widget integrates iRacing telemetry data with AI-powered analysis and visualization.
    """
    
    def __init__(self, parent=None, iracing_api=None):
        super().__init__(parent)
        self.setObjectName("RaceCoachWidget")
        
        # Store reference to the iRacing API
        self.iracing_api = iracing_api
        
        # Track connection state
        self.is_connected = False
        self.session_info = {}
        
        # Initialize UI
        self.setup_ui()
        
        # Connect to iRacing API if available
        if self.iracing_api is not None:
            try:
                # Try SimpleIRacingAPI method names first
                if hasattr(self.iracing_api, 'register_on_connection_changed'):
                    logger.info("Using SimpleIRacingAPI callback methods")
                    self.iracing_api.register_on_connection_changed(self.on_iracing_connected)
                    self.iracing_api.register_on_session_info_changed(self.on_session_info_changed)
                    self.iracing_api.register_on_telemetry_data(self.on_telemetry_data) # Corrected method name
                    
                    # Explicitly connect to iRacing
                    self.iracing_api.connect()
                    
                # Fall back to IRacingAPI method names
                elif hasattr(self.iracing_api, 'register_connection_callback'):
                    logger.info("Using IRacingAPI callback methods")
                    self.iracing_api.register_connection_callback(self.on_iracing_connected)
                    self.iracing_api.register_session_info_callback(self.on_session_info_changed)
                    self.iracing_api.register_telemetry_callback(self.on_telemetry_data)
                else:
                    logger.warning("Unable to register callbacks with iRacing API - incompatible implementation")
            except Exception as e:
                logger.error(f"Error connecting to iRacing API: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def setup_ui(self):
        """Set up the race coach UI components."""
        main_layout = QVBoxLayout(self)
        
        # Status bar at the top
        self.status_bar = QWidget()
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(5, 5, 5, 5)
        
        self.connection_label = QLabel("iRacing: Disconnected")
        self.connection_label.setStyleSheet("""
            color: red;
            font-weight: bold;
        """)
        status_layout.addWidget(self.connection_label)
        
        self.driver_label = QLabel("No Driver")
        status_layout.addWidget(self.driver_label)
        
        self.track_label = QLabel("No Track")
        status_layout.addWidget(self.track_label)
        
        status_layout.addStretch()
        
        self.demo_button = QPushButton("Load Demo Data")
        self.demo_button.clicked.connect(self.load_demo_data)
        status_layout.addWidget(self.demo_button)
        
        main_layout.addWidget(self.status_bar)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #222;
                border-radius: 3px;
            }
            QTabBar::tab {
                background-color: #333;
                color: #CCC;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #444;
                color: white;
            }
        """)
        
        # Create the Overview Tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Add some basic information to the overview tab
        overview_info = QLabel("Race Coach Overview")
        overview_info.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            padding: 10px;
        """)
        overview_layout.addWidget(overview_info)
        
        # Add a simple dashboard to the overview tab
        dashboard_frame = QFrame()
        dashboard_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        dashboard_frame.setStyleSheet("background-color: #2D2D30; border-radius: 5px;")
        dashboard_layout = QVBoxLayout(dashboard_frame)
        
        # Create a descriptive text
        dashboard_info = QLabel("Connect to iRacing or use the 'Load Demo Data' button to see telemetry visualization in the Telemetry tab.")
        dashboard_info.setWordWrap(True)
        dashboard_info.setStyleSheet("color: #CCC; font-size: 14px;")
        dashboard_layout.addWidget(dashboard_info)
        
        # Add dashboard to overview layout
        overview_layout.addWidget(dashboard_frame)
        overview_layout.addStretch()
        
        # Create the Telemetry Tab
        telemetry_tab = QWidget()
        telemetry_layout = QVBoxLayout(telemetry_tab)

        # Telemetry comparison widget
        self.telemetry_widget = TelemetryComparisonWidget(self)
        telemetry_layout.addWidget(self.telemetry_widget)

        # Create the Live Telemetry Tab
        # Live telemetry window
        live_telemetry_tab = QWidget()
        live_telemetry_tab_layout = QVBoxLayout(live_telemetry_tab)
        
        self.live_telemetry_frame = QFrame()
        self.live_telemetry_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.live_telemetry_frame.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """)
        
        live_telemetry_layout = QHBoxLayout(self.live_telemetry_frame)
        
        # Left side - Input trace visualization
        self.input_trace = InputTraceWidget(self)
        live_telemetry_layout.addWidget(self.input_trace, 2)
        
        # Right side - Current values
        values_frame = QFrame()
        values_layout = QFormLayout(values_frame)
        values_layout.setContentsMargins(15, 10, 15, 10)
        values_layout.setSpacing(5)
        values_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # Style for labels
        label_style = """
            color: #DDD;
            font-weight: bold;
            font-size: 11px;
        """
        
        value_style = """
            color: #FFF;
            font-size: 14px;
            font-weight: bold;
        """
        
        # Create value displays
        self.speed_value = QLabel("0")
        self.speed_value.setStyleSheet(value_style)
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet(label_style)
        values_layout.addRow(speed_label, self.speed_value)
        
        self.throttle_value = QLabel("0%")
        self.throttle_value.setStyleSheet(value_style)
        throttle_label = QLabel("Throttle:")
        throttle_label.setStyleSheet(label_style)
        values_layout.addRow(throttle_label, self.throttle_value)
        
        self.brake_value = QLabel("0%")
        self.brake_value.setStyleSheet(value_style)
        brake_label = QLabel("Brake:")
        brake_label.setStyleSheet(label_style)
        values_layout.addRow(brake_label, self.brake_value)
        
        self.clutch_value = QLabel("0%")
        self.clutch_value.setStyleSheet(value_style)
        clutch_label = QLabel("Clutch:")
        clutch_label.setStyleSheet(label_style)
        values_layout.addRow(clutch_label, self.clutch_value)
        
        self.gear_value = QLabel("N")
        self.gear_value.setStyleSheet(value_style)
        gear_label = QLabel("Gear:")
        gear_label.setStyleSheet(label_style)
        values_layout.addRow(gear_label, self.gear_value)
        
        self.rpm_value = QLabel("0")
        self.rpm_value.setStyleSheet(value_style)
        rpm_label = QLabel("RPM:")
        rpm_label.setStyleSheet(label_style)
        values_layout.addRow(rpm_label, self.rpm_value)
        
        self.lap_value = QLabel("0")
        self.lap_value.setStyleSheet(value_style)
        lap_label = QLabel("Lap:")
        lap_label.setStyleSheet(label_style)
        values_layout.addRow(lap_label, self.lap_value)
        
        self.laptime_value = QLabel("00:00.000")
        self.laptime_value.setStyleSheet(value_style)
        laptime_label = QLabel("Lap Time:")
        laptime_label.setStyleSheet(label_style)
        values_layout.addRow(laptime_label, self.laptime_value)
        
        live_telemetry_layout.addWidget(values_frame, 1)
        
        # Right side - Gauges
        gauges_frame = QFrame()
        gauges_layout = QVBoxLayout(gauges_frame)
        
        self.speed_gauge = SpeedGauge()
        self.rpm_gauge = RPMGauge()
        
        gauges_layout.addWidget(self.speed_gauge)
        gauges_layout.addWidget(self.rpm_gauge)
        
        live_telemetry_layout.addWidget(gauges_frame, 2)
        
        # Add live telemetry frame to the tab
        live_telemetry_tab_layout.addWidget(self.live_telemetry_frame)

        # Add a steering wheel widget to the live telemetry tab
        steering_frame = QFrame()
        steering_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        steering_frame.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """)
        steering_layout = QHBoxLayout(steering_frame)
        
        # Create steering wheel widget
        self.steering_wheel = SteeringWheelWidget(self)
        steering_layout.addWidget(self.steering_wheel)
        
        # Add steering frame to live telemetry tab
        live_telemetry_tab_layout.addWidget(steering_frame)
        
        # Create the Videos Tab
        videos_tab = VideosTab(self)

        # Add tabs to the tab widget
        self.tab_widget.addTab(overview_tab, "Overview")
        self.tab_widget.addTab(telemetry_tab, "Telemetry")
        self.tab_widget.addTab(live_telemetry_tab, "Live Telemetry")
        self.tab_widget.addTab(videos_tab, "RaceFlix") # Renamed tab

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Initialize with demo data if not connected
        if not self.is_connected:
            # QTimer.singleShot(500, self.load_demo_data) # Demo data loading disabled
            pass
            
    def _update_telemetry(self, telemetry_data):
        """Process telemetry data and update visualizations."""
        try:
            # Stop demo steering timer if it's running and we receive real data
            # if hasattr(self, '_demo_steer_timer') and self._demo_steer_timer.isActive():
            #     logger.info("Stopping demo steering animation timer.")
            #     # Queue the stop call on the main thread to avoid cross-thread issues
            #     QTimer.singleShot(0, self._demo_steer_timer.stop)
            
            # Log telemetry data periodically to check if it's being received properly
            if not hasattr(self, '_telemetry_log_count'):
                self._telemetry_log_count = 0
            
            self._telemetry_log_count += 1
            if self._telemetry_log_count % 60 == 0:  # Log once per second at 60Hz
                logger.info(f"Received telemetry data: {telemetry_data}")
                
            # Update input trace
            if hasattr(self, 'input_trace') and telemetry_data:
                # Make sure we're using the right keys for the telemetry data  
                throttle = telemetry_data.get('Throttle', telemetry_data.get('throttle', 0))
                brake = telemetry_data.get('Brake', telemetry_data.get('brake', 0))
                clutch = telemetry_data.get('Clutch', telemetry_data.get('clutch', 0))
                
                # Log telemetry values 
                if self._telemetry_log_count % 60 == 0:
                    logger.info(f"Driver inputs: Throttle={throttle:.2f}, Brake={brake:.2f}, Clutch={clutch:.2f}")
                
                self.input_trace.add_data_point(throttle, brake, clutch)
                
                # Update current values and gauges
                speed = telemetry_data.get('Speed', telemetry_data.get('speed', 0))
                if isinstance(speed, (int, float)) and speed > 0:
                    speed *= 3.6  # Convert to km/h
                
                rpm = telemetry_data.get('RPM', telemetry_data.get('rpm', 0))
                gear = telemetry_data.get('Gear', telemetry_data.get('gear', 0))
                gear_text = "R" if gear == -1 else "N" if gear == 0 else str(gear)
                lap = telemetry_data.get('Lap', telemetry_data.get('lap_count', 0))
                laptime = telemetry_data.get('LapCurrentLapTime', telemetry_data.get('lap_time', 0))
                
                # Get steering data - keys could be different depending on source
                steering = telemetry_data.get('steering', 
                           telemetry_data.get('SteeringWheelAngle', 
                           telemetry_data.get('Steer', 
                           telemetry_data.get('steer', 0))))
                
                # Update text values
                self.speed_value.setText(f"{speed:.1f} km/h")
                self.throttle_value.setText(f"{throttle*100:.0f}%")
                self.brake_value.setText(f"{brake*100:.0f}%")
                self.clutch_value.setText(f"{(1-clutch)*100:.0f}%")  # Invert clutch for display
                self.gear_value.setText(gear_text)
                self.rpm_value.setText(f"{rpm:.0f}")
                self.lap_value.setText(str(lap))
                self.laptime_value.setText(self._format_time(laptime))
                
                # Update gauges
                if hasattr(self, 'speed_gauge'):
                    self.speed_gauge.set_value(speed)
                    
                if hasattr(self, 'rpm_gauge'):
                    self.rpm_gauge.set_value(rpm)
                    # Check if we have session info for redline
                    if hasattr(self, 'session_info') and 'DriverInfo' in self.session_info:
                        driver_info = self.session_info['DriverInfo']
                        if 'DriverCarRedLine' in driver_info:
                            redline = driver_info['DriverCarRedLine']
                            self.rpm_gauge.set_redline(redline)
            
                # Update steering wheel widget
                if hasattr(self, 'steering_wheel'):
                    # Normalize steering value to -1.0 to 1.0 range if needed
                    # Some APIs provide steering in radians, others in a normalized range
                    if abs(steering) > 1.0:
                        # Convert from radians to normalized value
                        # For 1080-degree wheels (3 full rotations), max rotation is 3*pi radians
                        # Use max rotation value from the SteeringWheelAngleMax if available, 
                        # or calculate based on 1080 degrees (3*pi) as default for sim racing wheels
                        max_rotation = telemetry_data.get('SteeringWheelAngleMax', 
                                                         telemetry_data.get('steering_max', 3.0 * math.pi))
                        
                        # Ensure max_rotation is positive and reasonable
                        if max_rotation > 0:
                            # Clamp steering angle to max_rotation to prevent bar overflow
                            clamped_steering = max(-max_rotation, min(max_rotation, steering))
                            steering_normalized = clamped_steering / max_rotation
                            
                            # Make sure steering_normalized stays in [-1, 1] range
                            steering_normalized = max(-1.0, min(1.0, steering_normalized))
                            
                            self.steering_wheel.set_max_rotation(max_rotation)
                            self.steering_wheel.set_value(steering_normalized)
                            
                            # Add logging
                            if self._telemetry_log_count % 60 == 0:
                                logger.info(f"Steering (rad): {steering:.2f}, MaxRotation: {max_rotation:.2f}, " +
                                           f"Normalized: {steering_normalized:.2f}, Clamped: {clamped_steering:.2f}")
                    else:
                        # Already normalized between -1 and 1
                        # Still clamp to ensure it's within range
                        steering_normalized = max(-1.0, min(1.0, steering))
                        self.steering_wheel.set_value(steering_normalized)
                        
                        # Add logging
                        if self._telemetry_log_count % 60 == 0:
                            logger.info(f"Steering (normalized): {steering_normalized:.2f}")
            
            # TODO: Process telemetry for telemetry comparison if needed
            
        except Exception as e:
            logger.error(f"Error updating telemetry: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_iracing_connected(self, is_connected, session_info=None):
        """Handle connection status changes from iRacing API."""
        logger.info(f"iRacing connection status changed: {is_connected}")
        self.is_connected = is_connected
        
        if session_info:
            self.session_info = session_info
        
        self._update_connection_status(is_connected)
    
    def on_session_info_changed(self, session_info):
        """Handle session info changes from iRacing API."""
        logger.info("Session info changed")
        self.session_info = session_info
        self._update_session_info(session_info)
    
    def _update_connection_status(self, is_connected):
        """Update UI based on connection status."""
        if is_connected:
            self.connection_label.setText("iRacing: Connected")
            self.connection_label.setStyleSheet("""
                color: green;
                font-weight: bold;
            """)
            
            # If we have session info, update it
            if self.session_info:
                self._update_session_info(self.session_info)
        else:
            self.connection_label.setText("iRacing: Disconnected")
            self.connection_label.setStyleSheet("""
                color: red;
                font-weight: bold;
            """)
            self.driver_label.setText("No Driver")
            self.track_label.setText("No Track")
    
    def _update_session_info(self, session_info):
        """Update UI with session information."""
        try:
            # Extract and display driver name
            if 'DriverInfo' in session_info and 'DriverUserID' in session_info['DriverInfo']:
                driver_id = session_info['DriverInfo']['DriverUserID']
                driver_name = session_info['DriverInfo'].get('DriverName', 'Unknown Driver')
                self.driver_label.setText(f"Driver: {driver_name}")
            
            # Extract and display track name
            if 'WeekendInfo' in session_info and 'TrackDisplayName' in session_info['WeekendInfo']:
                track_name = session_info['WeekendInfo']['TrackDisplayName']
                self.track_label.setText(f"Track: {track_name}")
        except Exception as e:
            logger.error(f"Error updating session info: {e}")
    
    def load_demo_data(self):
        """Demo data loading disabled to prevent performance issues."""
        logger.info("Demo data loading is disabled")
        pass
    
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
    
    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        minutes = int(time_in_seconds // 60)
        seconds = int(time_in_seconds % 60)
        milliseconds = int((time_in_seconds % 1) * 1000)
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"
    
    def set_speed_data(self, left_data, right_data):
        """Set the speed data for both drivers and update the child widget."""
        self.speed_data_left = left_data
        self.speed_data_right = right_data
        
        # Pass data to the child widget
        if hasattr(self, 'speed_trace_widget'):
            self.speed_trace_widget.set_data(
                self.speed_data_left,
                self.speed_data_right,
                self.left_driver.get("color", QColor(255,0,0)),
                self.right_driver.get("color", QColor(255,215,0)),
                self.left_driver.get("name", "Driver 1"),
                self.right_driver.get("name", "Driver 2")
            )
        
        # Auto analyze the telemetry when new data is set (if needed)
        # self.analyze_telemetry() 
        self.update() # Update parent widget if necessary
        
    def set_delta_data(self, delta_data):
        """Set the delta time data and update the child widget."""
        self.delta_data = delta_data
        
        # Pass data to the child widget
        if hasattr(self, 'delta_widget'):
            self.delta_widget.set_data(delta_data)
            
        # Re-analyze with new delta data (if needed)
        # self.analyze_telemetry()
        self.update() # Update parent widget if necessary

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
            
            # Define areas for speed and delta graphs (These are now handled by child widgets)
            # speed_top = track_map_bottom + 20
            # speed_height = height * 0.25
            # speed_bottom = speed_top + speed_height
            
            # delta_top = speed_bottom + 10
            # delta_height = height * 0.15
            # delta_bottom = delta_top + delta_height
            
            # --- Speed and Delta graph drawing logic is now in child widgets ---
            # --- REMOVED all drawing code from here down related to speed/delta graphs --- 
            
        except Exception as e:
            # Log error but don't crash the application
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in TelemetryComparisonWidget.paintEvent: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_telemetry_data(self, telemetry_data):
        """Handle telemetry data updates from iRacing API."""
        # Just forward to our existing update method
        self._update_telemetry(telemetry_data)
        
    def closeEvent(self, event):
        """Handle widget close event to properly clean up resources."""
        try:
            logger.info("RaceCoachWidget closeEvent triggered - cleaning up resources")
            
            # Stop the demo steering timer if it's running
            # if hasattr(self, '_demo_steer_timer') and self._demo_steer_timer and self._demo_steer_timer.isActive():
            #     logger.info("Stopping demo steering animation timer")
            #     self._demo_steer_timer.stop()
                
            # Disconnect from iRacing API if it exists
            if hasattr(self, 'iracing_api') and self.iracing_api:
                logger.info("Disconnecting from iRacing API")
                self.iracing_api.disconnect()
                
            # Accept the event to allow the widget to be closed
            event.accept()
        except Exception as e:
            logger.error(f"Error during RaceCoachWidget closeEvent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            event.accept()  # Still accept the event even if there's an error
    
    def hideEvent(self, event):
        """Handle widget hide event (happens when switching tabs)."""
        try:
            logger.info("RaceCoachWidget hideEvent triggered - pausing resources")
            
            # Stop the demo steering timer if it's running
            # if hasattr(self, '_demo_steer_timer') and self._demo_steer_timer and self._demo_steer_timer.isActive():
            #     logger.info("Pausing demo steering animation timer")
            #     self._demo_steer_timer.stop()
                
            # Leave API connection active but log the state change
            if hasattr(self, 'iracing_api') and self.iracing_api:
                logger.info("Race Coach widget hidden but keeping iRacing API connection active")
        except Exception as e:
            logger.error(f"Error during RaceCoachWidget hideEvent: {e}")
        
        # Call the parent class implementation
        super().hideEvent(event)
    
    def showEvent(self, event):
        """Handle widget show event (happens when switching back to this tab)."""
        try:
            logger.info("RaceCoachWidget showEvent triggered - resuming resources")
            
            # Check connection status and reconnect if needed
            if hasattr(self, 'iracing_api') and self.iracing_api:
                if not self.iracing_api.is_connected():
                    logger.info("Reconnecting to iRacing API")
                    self.iracing_api.connect(
                        on_connected=self.on_iracing_connected,
                        on_disconnected=lambda: self.on_iracing_connected(False),
                        on_session_info_changed=self.on_session_info_changed,
                        on_telemetry_update=self.on_telemetry_data
                    )
                else:
                    logger.info("iRacing API already connected")
        except Exception as e:
            logger.error(f"Error during RaceCoachWidget showEvent: {e}")
        
        # Call the parent class implementation
        super().showEvent(event)

# This duplicate class is removed - we already have a complete DeltaGraphWidget implementation earlier in the file

class CourseCard(QFrame):
    """Widget to display a course card with thumbnail, title and description."""
    
    clicked = pyqtSignal(dict)  # Signal when card is clicked, passes course data
    
    def __init__(self, course_data, parent=None):
        super().__init__(parent)
        self.course_data = course_data
        self.setFixedSize(280, 320)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setObjectName("CourseCard")
        self.setStyleSheet("""
            #CourseCard {
                background-color: #222;
                border-radius: 8px;
                border: 1px solid #444;
            }
            #CourseCard:hover {
                border: 1px solid #666;
                background-color: #2a2a2a;
            }
            QLabel {
                color: white;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)
        
        # Thumbnail
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(280, 180)
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setStyleSheet("border-top-left-radius: 8px; border-top-right-radius: 8px;")
        
        # Load thumbnail if provided
        if "thumbnail" in course_data and course_data["thumbnail"]:
            pixmap = QPixmap(course_data["thumbnail"])
            if not pixmap.isNull():
                self.thumbnail.setPixmap(pixmap.scaled(280, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.thumbnail.setText("Thumbnail Not Found")
                self.thumbnail.setStyleSheet("background-color: #333; color: white;")
        else:
            self.thumbnail.setText("No Thumbnail")
            self.thumbnail.setStyleSheet("background-color: #333; color: white;")
            
        layout.addWidget(self.thumbnail)
        
        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 0, 12, 0)
        content_layout.setSpacing(8)
        
        # Title
        self.title_label = QLabel(course_data.get("title", "Untitled Course"))
        self.title_label.setWordWrap(True)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self.title_label.setFont(title_font)
        content_layout.addWidget(self.title_label)
        
        # Description 
        description = course_data.get("description", "No description available")
        # Truncate description if too long
        if len(description) > 120:
            description = description[:117] + "..."
            
        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #aaa; font-size: 11px;")
        content_layout.addWidget(self.desc_label)
        
        # Stats row (lessons, duration)
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        lessons_count = course_data.get("lessons", 0)
        lessons_label = QLabel(f"{lessons_count} lesson{'s' if lessons_count != 1 else ''}")
        lessons_label.setStyleSheet("color: #888; font-size: 10px;")
        
        duration = course_data.get("duration", "")
        duration_label = QLabel(duration)
        duration_label.setStyleSheet("color: #888; font-size: 10px;")
        
        stats_layout.addWidget(lessons_label)
        stats_layout.addStretch()
        stats_layout.addWidget(duration_label)
        
        content_layout.addWidget(stats_widget)
        layout.addWidget(content_widget)
        
    def mousePressEvent(self, event):
        self.clicked.emit(self.course_data)
        super().mousePressEvent(event)
        
class VideoPlayer(QWidget):
    """Video player widget for course lessons with YouTube support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 360) # Reverted minimum size
        self.current_video = None
        
        # Set size policy to indicate height depends on width
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main content area - either web view or fallback
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Try to import QtWebEngineWidgets for YouTube embedding
        logger.info("Attempting to import PyQt5.QtWebEngineWidgets...")
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            logger.info("PyQt5.QtWebEngineWidgets imported successfully.")
            self.web_view = QWebEngineView()
            self.web_view.setStyleSheet("background-color: #111;")
            self.stack.addWidget(self.web_view)
            self.has_web_engine = True
        except ImportError as e:
            logger.warning(f"Failed to import PyQt5.QtWebEngineWidgets: {e}. Using fallback player.")
            self.has_web_engine = False
        
        # Create a fallback player using QLabel and HTML
        self.html_view = QLabel()
        # self.html_view.setAlignment(Qt.AlignCenter) # Removed alignment
        self.html_view.setScaledContents(True) # Added scaling
        self.html_view.setStyleSheet("""
            background-color: #111;
            color: white;
            font-size: 16px;
            border-radius: 4px;
            padding: 10px;
        """)
        self.html_view.setTextFormat(Qt.RichText)
        self.html_view.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.html_view.setOpenExternalLinks(True)
        
        # Add the fallback view to the stack
        self.stack.addWidget(self.html_view)
        
    def get_youtube_embed_url(self, url):
        """Convert YouTube URL to embed URL."""
        # Handle various YouTube URL formats
        import re
        video_id = None
        
        # Full youtube.com URL
        match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
        if match:
            video_id = match.group(1)
        
        # Shortened youtu.be URL
        if not video_id:
            match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
            if match:
                video_id = match.group(1)
        
        # Direct video ID
        if not video_id and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            video_id = url
            
        if video_id:
            # Ensure autoplay=1 is removed
            return f"https://www.youtube.com/embed/{video_id}", video_id 
        
        # If we couldn't extract a video ID, return the original URL
        return url, None
    
    def load_video(self, video_url):
        """Load a video into the player."""
        self.current_video = video_url
        
        # Get YouTube embed URL and video ID
        embed_url, video_id = self.get_youtube_embed_url(video_url)
        
        # Directly load into web_view, assuming it works
        logger.info(f"Loading video in QWebEngineView: {embed_url}")
        self.web_view.load(QUrl(embed_url)) # Convert string to QUrl
    
    def open_in_browser(self):
        """Open the video in a web browser."""
        if self.current_video:
            import webbrowser
            webbrowser.open(self.current_video)

    def heightForWidth(self, width):
        """Return the preferred height for a given width to maintain 16:9 ratio."""
        return int(width * 9.0 / 16.0)

    def hasHeightForWidth(self):
        """Indicate that the widget's height depends on its width."""
        return True

    def sizeHint(self):
        """Provide a reasonable default size hint."""
        # Base the hint on a common 16:9 size like 720p
        width = 640 
        return QSize(width, self.heightForWidth(width))

class CourseView(QWidget):
    """Widget for displaying the course content and video player."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        # Back button
        self.back_button = QPushButton("← Back to Courses")
        self.back_button.setFixedHeight(36)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #3498db;
                border: none;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #2980b9;
            }
        """)
        layout.addWidget(self.back_button)
        
        # Course header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        
        self.course_title = QLabel("Course Title")
        self.course_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
        """)
        header_layout.addWidget(self.course_title)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # Main content area - split between video player and lessons
        content = QSplitter(Qt.Horizontal)
        
        # Video player (left side)
        self.video_player = VideoPlayer()
        
        # Lessons list (right side)
        lessons_widget = QWidget()
        lessons_layout = QVBoxLayout(lessons_widget)
        
        lessons_header = QLabel("Course Content")
        lessons_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        lessons_layout.addWidget(lessons_header)
        
        self.lessons_list = QScrollArea()
        self.lessons_list.setWidgetResizable(True)
        self.lessons_list.setStyleSheet("""
            background-color: #222;
            border: 1px solid #444;
            border-radius: 4px;
        """)
        
        lessons_container = QWidget()
        self.lessons_container_layout = QVBoxLayout(lessons_container)
        self.lessons_container_layout.setAlignment(Qt.AlignTop)
        self.lessons_list.setWidget(lessons_container)
        
        lessons_layout.addWidget(self.lessons_list)
        
        content.addWidget(self.video_player)
        content.addWidget(lessons_widget)
        content.setSizes([600, 300])  # Initial sizes
        
        # Give the splitter vertical stretch factor
        layout.addWidget(content, 1)
        
    def set_course(self, course_data):
        """Load a course into the view."""
        self.course_title.setText(course_data.get("title", "Untitled Course"))
        
        # Clear existing lessons
        while self.lessons_container_layout.count():
            item = self.lessons_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new lessons
        lessons = course_data.get("lessons_data", [])
        for i, lesson in enumerate(lessons):
            lesson_widget = QWidget()
            lesson_layout = QHBoxLayout(lesson_widget)
            lesson_layout.setContentsMargins(8, 12, 8, 12)
            
            # Lesson number
            num_label = QLabel(f"{i+1}")
            num_label.setStyleSheet("""
                background-color: #333;
                color: white;
                border-radius: 12px;
                padding: 4px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                font-weight: bold;
                text-align: center;
            """)
            num_label.setAlignment(Qt.AlignCenter)
            
            # Lesson info
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(2)
            
            title_label = QLabel(lesson.get("title", f"Lesson {i+1}"))
            title_label.setStyleSheet("color: white; font-weight: bold;")
            
            duration = lesson.get("duration", "")
            desc_label = QLabel(f"Duration: {duration}")
            desc_label.setStyleSheet("color: #aaa; font-size: 11px;")
            
            info_layout.addWidget(title_label)
            info_layout.addWidget(desc_label)
            
            lesson_layout.addWidget(num_label)
            lesson_layout.addWidget(info_widget, 1)
            
            # Make lessons clickable
            lesson_frame = QFrame()
            lesson_frame.setLayout(lesson_layout)
            lesson_frame.setCursor(Qt.PointingHandCursor)
            lesson_frame.setStyleSheet("""
                QFrame {
                    background-color: #2a2a2a;
                    border-radius: 4px;
                }
                QFrame:hover {
                    background-color: #333;
                }
            """)
            
            # Use a lambda to create a closure with the current lesson
            lesson_video_url = lesson.get("video_url", "")
            lesson_frame.mousePressEvent = lambda event, url=lesson_video_url, title=lesson.get("title", ""): self.play_lesson(url, title)
            
            self.lessons_container_layout.addWidget(lesson_frame)
        
        # Add a spacer at the end
        self.lessons_container_layout.addStretch()
        
        # Load the first lesson if available
        if lessons and "video_url" in lessons[0]:
            self.play_lesson(lessons[0]["video_url"], lessons[0].get("title", "Lesson 1"))
    
    def play_lesson(self, video_url, title):
        """Play a specific lesson."""
        self.video_player.load_video(video_url)

class VideosTab(QWidget):
    """Tab for displaying video courses in a Kajabi-like interface."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget to switch between courses list and individual course view
        self.stacked_widget = QStackedWidget()
        
        # Create courses list view
        self.courses_view = QWidget()
        courses_layout = QVBoxLayout(self.courses_view)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        title = QLabel("Racing Courses")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        
        search_box = QWidget()
        search_layout = QHBoxLayout(search_box)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        search_icon = QLabel("🔍")
        search_field = QLineEdit()
        search_field.setPlaceholderText("Search courses...")
        search_field.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: white;
                border-radius: 4px;
                padding: 8px;
                min-width: 200px;
            }
        """)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(search_field)
        header_layout.addWidget(search_box)
        
        courses_layout.addWidget(header)
        
        # Categories tabs
        categories = QTabWidget()
        categories.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #aaa;
                padding: 8px 16px;
                margin-right: 4px;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: #3498db;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover:!selected {
                color: white;
            }
        """)
        
        # Add category tabs
        all_courses_tab = QWidget()
        racing_basics_tab = QWidget()
        advanced_techniques_tab = QWidget()
        track_guides_tab = QWidget()
        
        categories.addTab(all_courses_tab, "All Courses")
        categories.addTab(racing_basics_tab, "Racing Basics")
        categories.addTab(advanced_techniques_tab, "Advanced Techniques")
        categories.addTab(track_guides_tab, "Track Guides")
        
        courses_layout.addWidget(categories)
        
        # Course grid layout for each tab
        self.setup_course_grid(all_courses_tab, "all")
        self.setup_course_grid(racing_basics_tab, "racing_basics")
        self.setup_course_grid(advanced_techniques_tab, "advanced")
        self.setup_course_grid(track_guides_tab, "track_guides")
        
        # Create course detail view
        self.course_view = CourseView()
        self.course_view.back_button.clicked.connect(self.show_courses_list)
        
        # Add both views to the stacked widget
        self.stacked_widget.addWidget(self.courses_view)
        self.stacked_widget.addWidget(self.course_view)
        
        layout.addWidget(self.stacked_widget)
        
        # Start with courses list
        self.stacked_widget.setCurrentIndex(0)
        
    def setup_course_grid(self, tab_widget, category):
        """Set up a grid of course cards for a category tab."""
        # Create a scroll area for the courses
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        grid_layout = QGridLayout(scroll_content)
        grid_layout.setContentsMargins(20, 10, 20, 20)
        grid_layout.setSpacing(20)
        
        # Get sample courses for this category
        courses = self.get_sample_courses(category)
        
        # Add courses to grid
        row, col = 0, 0
        max_cols = 3  # Number of columns in the grid
        
        for course in courses:
            course_card = CourseCard(course)
            course_card.clicked.connect(self.show_course_detail)
            
            grid_layout.addWidget(course_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        # Add stretchers to keep grid aligned
        grid_layout.setRowStretch(row + 1, 1)
        grid_layout.setColumnStretch(max_cols, 1)
        
        scroll_area.setWidget(scroll_content)
        
        # Set up the tab layout
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll_area)
    
    def get_sample_courses(self, category):
        """Return sample courses for the given category."""
        all_courses = [
            {
                "id": "racing101",
                "title": "Racing Fundamentals",
                "description": "Learn the basics of performance driving with this comprehensive course for beginners.",
                "category": "racing_basics",
                "thumbnail": None,  # Would be a path to an image
                "lessons": 8,
                "duration": "2h 15m",
                "lessons_data": [
                    {"title": "Introduction to Racing", "duration": "12:30", "video_url": "https://www.youtube.com/watch?v=6-sGV2XXUeU"},
                    {"title": "Car Control Basics", "duration": "18:45", "video_url": "https://www.youtube.com/watch?v=ewQwgL76lFo"},
                    {"title": "Racing Lines Explained", "duration": "22:10", "video_url": "https://www.youtube.com/watch?v=VEJh4lLCvRc"},
                    {"title": "Braking Techniques", "duration": "16:55", "video_url": "https://www.youtube.com/watch?v=zXPSj56lavE"},
                    {"title": "Throttle Control", "duration": "14:20", "video_url": "https://www.youtube.com/watch?v=N8qBdOs0s1E"},
                    {"title": "Cornering Fundamentals", "duration": "19:40", "video_url": "https://www.youtube.com/watch?v=6si3T6-6K7o"},
                    {"title": "Race Day Preparation", "duration": "15:15", "video_url": "https://www.youtube.com/watch?v=5xkqOX_9Iqk"},
                    {"title": "Practice Drills", "duration": "17:30", "video_url": "https://www.youtube.com/watch?v=b9cK7h3UhOs"}
                ]
            },
            {
                "id": "advanced_braking",
                "title": "Advanced Braking Techniques",
                "description": "Master the art of braking with this advanced course for experienced drivers.",
                "category": "advanced",
                "thumbnail": None,
                "lessons": 5,
                "duration": "1h 45m",
                "lessons_data": [
                    {"title": "The Science of Braking", "duration": "18:20", "video_url": "https://www.youtube.com/watch?v=PgLz6WuCrTY"},
                    {"title": "Trail Braking Mastery", "duration": "24:15", "video_url": "https://www.youtube.com/watch?v=k73GhFLRP9Y"},
                    {"title": "Threshold Braking", "duration": "22:30", "video_url": "https://www.youtube.com/watch?v=zQvMrCRiPjA"},
                    {"title": "Wet Weather Braking", "duration": "19:40", "video_url": "https://www.youtube.com/watch?v=TJ2UAj3CaBU"},
                    {"title": "Race Scenario Applications", "duration": "20:15", "video_url": "https://www.youtube.com/watch?v=xGdLCfYcIn4"}
                ]
            },
            {
                "id": "nurburgring",
                "title": "Conquering the Nürburgring",
                "description": "Learn every corner of the legendary Nürburgring Nordschleife with our detailed track guide.",
                "category": "track_guides",
                "thumbnail": None,
                "lessons": 6,
                "duration": "3h 20m",
                "lessons_data": [
                    {"title": "Nürburgring History", "duration": "12:40", "video_url": "https://www.youtube.com/watch?v=vfpVLqVmRgc"},
                    {"title": "Sectors Overview", "duration": "15:50", "video_url": "https://www.youtube.com/watch?v=C0st2ST_WPs"},
                    {"title": "North Section Deep Dive", "duration": "35:20", "video_url": "https://www.youtube.com/watch?v=KhvnkU71MX8"},
                    {"title": "Carousel and Challenging Corners", "duration": "42:15", "video_url": "https://www.youtube.com/watch?v=3lMUoiWeBE0"},
                    {"title": "Final Sectors", "duration": "28:30", "video_url": "https://www.youtube.com/watch?v=9m-S5Mn_BF4"},
                    {"title": "Full Lap Analysis", "duration": "65:25", "video_url": "https://www.youtube.com/watch?v=GD3yC9OJ2xQ"}
                ]
            },
            {
                "id": "car_setup",
                "title": "Race Car Setup Fundamentals",
                "description": "Understanding and optimizing your car's setup for maximum performance on any track.",
                "category": "advanced",
                "thumbnail": None,
                "lessons": 7,
                "duration": "2h 30m",
                "lessons_data": [
                    {"title": "Setup Philosophy", "duration": "14:30", "video_url": "https://www.youtube.com/watch?v=6Z_G7cfcJzE"},
                    {"title": "Suspension Tuning", "duration": "25:15", "video_url": "https://www.youtube.com/watch?v=jURy5TJ7OKk"},
                    {"title": "Tire Pressure and Camber", "duration": "22:40", "video_url": "https://www.youtube.com/watch?v=GDvF89Bh27Y"},
                    {"title": "Aero Adjustments", "duration": "18:55", "video_url": "https://www.youtube.com/watch?v=AYMvaRKNlO4"},
                    {"title": "Gearing Strategy", "duration": "21:10", "video_url": "https://www.youtube.com/watch?v=79V3QS0vCuY"},
                    {"title": "Brake Bias Tuning", "duration": "16:45", "video_url": "https://www.youtube.com/watch?v=QdY7YuN8XVE"},
                    {"title": "Creating a Setup Worksheet", "duration": "20:55", "video_url": "https://www.youtube.com/watch?v=8y3Vu-FnlPE"}
                ]
            },
            {
                "id": "racing_weather",
                "title": "Racing in Different Weather Conditions",
                "description": "Master the skills needed to excel in rain, heat, and changing weather conditions.",
                "category": "advanced",
                "thumbnail": None,
                "lessons": 4,
                "duration": "1h 50m",
                "lessons_data": [
                    {"title": "Rain Racing Fundamentals", "duration": "28:15", "video_url": "https://www.youtube.com/watch?v=WRtYnJMVnzA"},
                    {"title": "Transitioning Conditions", "duration": "24:30", "video_url": "https://www.youtube.com/watch?v=UkM7KdRHzuY"},
                    {"title": "Hot Weather Techniques", "duration": "26:45", "video_url": "https://www.youtube.com/watch?v=j_HA8QMqaVU"},
                    {"title": "Weather Strategy and Planning", "duration": "30:30", "video_url": "https://www.youtube.com/watch?v=XdDtW6oecPE"}
                ]
            },
            {
                "id": "mental_training",
                "title": "Mental Training for Racers",
                "description": "Develop the mental skills and mindset needed to perform at your best behind the wheel.",
                "category": "racing_basics",
                "thumbnail": None,
                "lessons": 6,
                "duration": "2h 10m",
                "lessons_data": [
                    {"title": "Concentration and Focus", "duration": "18:20", "video_url": "https://www.youtube.com/watch?v=11JxHSQNmzs"},
                    {"title": "Managing Race Day Anxiety", "duration": "22:15", "video_url": "https://www.youtube.com/watch?v=wcKFujbNhLg"},
                    {"title": "Visualization Techniques", "duration": "20:40", "video_url": "https://www.youtube.com/watch?v=A9RpwbQdJyk"},
                    {"title": "Decision Making Under Pressure", "duration": "24:55", "video_url": "https://www.youtube.com/watch?v=7SehQ-UjpRQ"},
                    {"title": "Goal Setting for Racers", "duration": "19:30", "video_url": "https://www.youtube.com/watch?v=IgBF2hRHFHw"},
                    {"title": "Post-Race Analysis", "duration": "24:20", "video_url": "https://www.youtube.com/watch?v=i1I7B9Q6kGw"}
                ]
            }
        ]
        
        if category == "all":
            return all_courses
        
        return [course for course in all_courses if course["category"] == category]
    
    def show_course_detail(self, course_data):
        """Show the detailed view for a course."""
        self.course_view.set_course(course_data)
        self.stacked_widget.setCurrentIndex(1)
    
    def show_courses_list(self):
        """Return to the courses list view."""
        self.stacked_widget.setCurrentIndex(0)

# ... existing code ...

def setup_ui(self):
    """Set up the race coach UI components."""
    # ... existing code ...
    
    # Create the Videos Tab
    videos_tab = VideosTab(self)
    
    # Add tabs to the tab widget
    self.tab_widget.addTab(overview_tab, "Overview")
    self.tab_widget.addTab(telemetry_tab, "Telemetry")
    self.tab_widget.addTab(live_telemetry_tab, "Live Telemetry")
    self.tab_widget.addTab(videos_tab, "RaceFlix") # Add the new videos tab

    # ... rest of existing code ...
