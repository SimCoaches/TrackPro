"""Common widgets used across Race Coach UI tabs.

This module contains reusable widgets like gauges, input trace displays,
and other UI components shared between different tabs.
"""

import logging
import math
import threading
import numpy as np
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QSizeF
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient,
    QPixmap, QPainterPath
)

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Enforce minimum size for proper rendering
        if width < 100 or height < 50:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.PenStyle.NoPen)
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
                painter.drawText(0, 0, width, height, Qt.AlignmentFlag.AlignCenter, f"{self.value:.0f}")

            return

        # Regular rendering for normal sizes
        # Calculate dimensions
        padding = max(5, min(10, width / 20))  # Adaptive padding
        gauge_width = width - (padding * 2)
        gauge_height = max(10, min(30, height / 5))  # Adaptive height

        # Draw gauge background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.background_color.darker(120)))
        painter.drawRoundedRect(padding, height - gauge_height - padding, gauge_width, gauge_height, 5, 5)

        # Draw gauge fill - gradient from blue to red based on speed
        normalized = self.get_normalized_value()
        if normalized > 0:
            # Create gradient
            gradient = QLinearGradient(padding, 0, padding + gauge_width, 0)
            gradient.setColorAt(0, self.low_speed_color)
            gradient.setColorAt(1, self.high_speed_color)

            painter.setBrush(QBrush(gradient))
            fill_width = int(normalized * gauge_width)
            painter.drawRoundedRect(padding, height - gauge_height - padding, fill_width, gauge_height, 5, 5)

        # Draw title if there's enough room
        if height >= 80:
            title_font = painter.font()
            title_font.setPointSize(max(8, min(12, width / 20)))  # Adaptive font size
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QPen(self.text_color))
            painter.drawText(padding, padding, gauge_width, 30, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

        # Draw value with adaptive font size
        value_font = painter.font()
        value_font.setPointSize(max(10, min(22, width / 10)))  # Adaptive font size
        value_font.setBold(True)
        painter.setFont(value_font)
        value_text = f"{self.value:.1f} {self.units}"
        painter.drawText(padding, 40, gauge_width, 50, Qt.AlignmentFlag.AlignCenter, value_text)

        # Only draw tick marks if there's enough room
        if width >= 200 and height >= 100:
            painter.setPen(QPen(self.text_color.lighter(150), 1))
            tick_y = height - gauge_height - padding - 5

            # Major ticks every 50 km/h
            for speed in range(0, int(self.max_value) + 1, 50):
                tick_x = padding + (speed / self.max_value) * gauge_width
                painter.drawLine(int(tick_x), tick_y, int(tick_x), tick_y - 10)

                # Draw tick label
                painter.drawText(int(tick_x) - 15, tick_y - 15, 30, 20, Qt.AlignmentFlag.AlignCenter, str(speed))

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Enforce minimum size for proper rendering
        if width < 100 or height < 100:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.PenStyle.NoPen)
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
                    painter.setPen(QPen(gauge_color, 2, Qt.PenStyle.SolidLine, Qt.RoundCap))
                    span = normalized * 270
                    painter.drawArc(arc_rect, 135 * 16, int(span * 16))

            # Add basic RPM text
            painter.setPen(QPen(self.text_color))
            rpm_text = f"{self.value/1000:.1f}k"
            painter.drawText(0, 0, width, height, Qt.AlignmentFlag.AlignCenter, rpm_text)

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
            painter.setPen(QPen(gauge_color, pen_width, Qt.PenStyle.SolidLine, Qt.RoundCap))
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
        painter.drawText(arc_rect, Qt.AlignmentFlag.AlignCenter, rpm_text)

        # Draw title text
        title_font = painter.font()
        title_font.setPointSize(12)
        painter.setFont(title_font)
        title_rect = QRectF(arc_rect.left(), arc_rect.top() + arc_rect.height() // 2 + 10, arc_rect.width(), 30)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)


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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Enforce minimum size for proper rendering
        if width < 100 or height < 100:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.PenStyle.NoPen)
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
            cache_painter.setRenderHint(QPainter.RenderHint.Antialiasing)

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
        painter.setPen(Qt.PenStyle.NoPen)
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
        painter.drawText(0, int(text_y), width, 20, Qt.AlignmentFlag.AlignCenter, angle_text)

        # Draw title
        title_font = painter.font()
        title_font.setPointSize(12)
        painter.setFont(title_font)
        painter.drawText(0, 15, width, 20, Qt.AlignmentFlag.AlignCenter, self.title)

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
            true_normalized = 0.5  # Center if max_rotation is zero

        position = bar_x + bar_width * true_normalized

        # Use different colors for left and right
        if self.steering_angle < 0:
            indicator_color = QColor(0, 150, 255)  # Blue for left turns
        else:
            indicator_color = QColor(255, 100, 0)  # Orange for right turns

        indicator_width = bar_width / 10
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(indicator_color))
        painter.drawRect(int(center_line_x), int(bar_y), int((position - center_line_x)), int(bar_height))


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
        self.brake_color = QColor("#FF5252")  # Red
        self.clutch_color = QColor("#FFC107")  # Amber
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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Calculate drawing area - increase padding for better spacing
        padding = 20
        left_padding = 35  # More space for y-axis labels
        right_padding = 15
        top_padding = 20  # More space for title
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
        painter.drawText(int(width / 2 - 75), 15, "Input Trace")

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
        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DashLine))

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
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30, 180)))
        painter.drawRect(legend_x - 5, legend_y - 5, legend_width, 3 * legend_height + 2 * legend_spacing + 10)

        # Throttle
        painter.setPen(self.throttle_color)
        painter.drawLine(legend_x, legend_y, legend_x + 15, legend_y)
        painter.drawText(legend_x + 20, legend_y + 5, "Throttle")

        # Brake
        painter.setPen(self.brake_color)
        painter.drawLine(
            legend_x,
            legend_y + legend_height + legend_spacing,
            legend_x + 15,
            legend_y + legend_height + legend_spacing,
        )
        painter.drawText(legend_x + 20, legend_y + legend_height + legend_spacing + 5, "Brake")

        # Clutch
        painter.setPen(self.clutch_color)
        painter.drawLine(
            legend_x,
            legend_y + 2 * (legend_height + legend_spacing),
            legend_x + 15,
            legend_y + 2 * (legend_height + legend_spacing),
        )
        painter.drawText(legend_x + 20, legend_y + 2 * (legend_height + legend_spacing) + 5, "Clutch") 