import sys
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTabWidget, QGroupBox,
                             QSplitter, QComboBox, QStatusBar, QMainWindow, QMessageBox, QApplication, QGridLayout, QFrame, QFormLayout, QCheckBox, QProgressBar, QSizePolicy, QSpacerItem, QScrollArea, QStackedWidget, QLineEdit, QSlider, QTabBar)
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
from datetime import datetime, timedelta
from pathlib import Path  # Add Path import for file handling

# Need QObject and QThread for background tasks
from PyQt5.QtCore import QObject, QThread

# Import the auth update function directly here as well
from Supabase.auth import update_auth_state_from_client, is_logged_in

# Supabase helpers for laps and telemetry
try:
    from Supabase.database import get_laps, get_telemetry_points, get_sessions # Add get_sessions import
except Exception as _sup_err:
    logger = logging.getLogger(__name__)
    logger.warning(f"Supabase import failed ({_sup_err}), using fallback functions.")
    # When Supabase is not configured (offline demo) we still want UI to load.
    def get_laps(*_args, **_kwargs):
        return None, "Supabase unavailable"

    def get_telemetry_points(*_args, **_kwargs):
        return None, "Supabase unavailable"
        
    # Add fallback for get_sessions
    def get_sessions(*_args, **_kwargs):
        # Return some dummy session data for offline testing
        logger.info("Using fallback get_sessions")
        now = datetime.now()
        sessions = [
            {"id": "session_1", "created_at": (now - timedelta(hours=1)).isoformat(), "track_name": "Demo Track 1", "car_name": "Demo Car A"},
            {"id": "session_2", "created_at": (now - timedelta(days=1)).isoformat(), "track_name": "Demo Track 2", "car_name": "Demo Car B"},
            {"id": "session_3", "created_at": (now - timedelta(days=2)).isoformat(), "track_name": "Demo Track 1", "car_name": "Demo Car C"},
        ]
        return sessions, "Using fallback data"

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

# --- Worker for Background Telemetry Fetching (Phase 3, Step 7) ---
class TelemetryFetchWorker(QObject):
    # finished = pyqtSignal(object, object) # Pass two results (left_pts, right_pts) - Original
    # Modified finished signal to emit dictionaries containing stats and points
    finished = pyqtSignal(object, object)
    error = pyqtSignal(str, str)          # Pass two error messages

    def __init__(self, left_lap_id, right_lap_id):
        super().__init__()
        self.left_lap_id = left_lap_id
        self.right_lap_id = right_lap_id
        self.is_cancelled = False

    def _calculate_lap_stats(self, telemetry_points):
        """Calculate statistics from a list of telemetry points."""
        if not telemetry_points or len(telemetry_points) < 2:
            return None # Not enough data

        # Sort points by timestamp just in case
        telemetry_points.sort(key=lambda p: p.get('timestamp', 0))

        total_time = telemetry_points[-1].get('timestamp', 0) - telemetry_points[0].get('timestamp', 0)
        if total_time <= 0:
            return None # Invalid time range

        full_throttle_time = 0
        heavy_braking_time = 0
        cornering_time = 0

        # Define thresholds
        THROTTLE_THRESHOLD = 0.98
        BRAKE_THRESHOLD = 0.80
        STEERING_THRESHOLD = 0.1 # Radians, adjust as needed

        speeds = []
        track_positions = []

        for i in range(len(telemetry_points) - 1):
            p1 = telemetry_points[i]
            p2 = telemetry_points[i+1]

            dt = p2.get('timestamp', 0) - p1.get('timestamp', 0)
            if dt <= 0: continue # Skip invalid time steps

            # Calculate time spent in different states during this interval (use p1's value)
            throttle = p1.get('throttle', 0)
            brake = p1.get('brake', 0)
            steering = p1.get('steering', 0)

            if throttle is not None and throttle >= THROTTLE_THRESHOLD:
                full_throttle_time += dt
            if brake is not None and brake >= BRAKE_THRESHOLD:
                heavy_braking_time += dt
            if steering is not None and abs(steering) >= STEERING_THRESHOLD:
                 # Optional: Add conditions like not braking heavily?
                 # if brake is None or brake < BRAKE_THRESHOLD * 0.8:
                 cornering_time += dt

            # Collect data for graphs (using p1's values)
            speeds.append(p1.get('speed', 0))
            track_positions.append(p1.get('track_position', 0))

        # Add last point's data for graphs
        speeds.append(telemetry_points[-1].get('speed', 0))
        track_positions.append(telemetry_points[-1].get('track_position', 0))


        # Calculate percentages
        full_throttle_pct = int((full_throttle_time / total_time) * 100) if total_time > 0 else 0
        heavy_braking_pct = int((heavy_braking_time / total_time) * 100) if total_time > 0 else 0
        cornering_pct = int((cornering_time / total_time) * 100) if total_time > 0 else 0

        # Get overall lap time from the lap record itself (more accurate)
        # This needs to be passed or fetched separately if needed here.
        # For now, we'll just pass the stats.

        stats = {
            "full_throttle": full_throttle_pct,
            "heavy_braking": heavy_braking_pct,
            "cornering": cornering_pct,
            # Add lap time and gap later if fetched/calculated
        }
        points = {
            "speed": speeds,
            "track_position": track_positions
            # Add delta later if calculated
        }

        return {"stats": stats, "points": points}


    def run(self):
        """Fetch telemetry data for both laps and calculate stats."""
        logger.info(f"Worker thread starting fetch for {self.left_lap_id} and {self.right_lap_id}")
        left_data, right_data = None, None
        msg_left, msg_right = "", ""
        # Define columns needed for calculation and graphs
        required_columns = [
            "track_position", "speed", "throttle", "brake", "steering", "timestamp"
        ]

        try:
            # Fetch left lap
            if not self.is_cancelled:
                # Fetch all required columns
                left_pts, msg_left = get_telemetry_points(self.left_lap_id, columns=required_columns)
                if left_pts is None:
                    logger.warning(f"Failed fetching left lap telemetry: {msg_left}")
                else:
                    logger.info(f"Fetched {len(left_pts)} points for left lap {self.left_lap_id}")
                    left_data = self._calculate_lap_stats(left_pts)
                    if not left_data:
                         logger.warning(f"Could not calculate stats for left lap {self.left_lap_id}")
                         msg_left = "Stat calculation failed (left)"


            # Fetch right lap
            if not self.is_cancelled:
                # Fetch all required columns
                right_pts, msg_right = get_telemetry_points(self.right_lap_id, columns=required_columns)
                if right_pts is None:
                    logger.warning(f"Failed fetching right lap telemetry: {msg_right}")
                else:
                    logger.info(f"Fetched {len(right_pts)} points for right lap {self.right_lap_id}")
                    right_data = self._calculate_lap_stats(right_pts)
                    if not right_data:
                         logger.warning(f"Could not calculate stats for right lap {self.right_lap_id}")
                         msg_right = "Stat calculation failed (right)"


            # Check results and emit appropriate signal
            if self.is_cancelled:
                 logger.info("Telemetry fetch cancelled.")
                 self.error.emit("Operation Cancelled", "Operation Cancelled")
            elif left_data is None and right_data is None:
                 self.error.emit(msg_left or "Fetch/Calc failed", msg_right or "Fetch/Calc failed")
            else:
                 # Emit results (dictionaries with stats and points) even if one failed
                 logger.info(f"Emitting finished signal. Left valid: {left_data is not None}, Right valid: {right_data is not None}")
                 self.finished.emit(left_data, right_data)

        except Exception as e:
            logger.error(f"Exception in TelemetryFetchWorker: {e}", exc_info=True)
            self.error.emit(f"Worker Error: {e}", f"Worker Error: {e}")

    def cancel(self):
        self.is_cancelled = True
# --- End Worker ---

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

class VideosTab(QWidget):
    """Tab for displaying video courses in a Kajabi-like interface."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # COMPLETELY SIMPLIFIED UI FOR DEBUGGING - JUST A DIRECT LABEL TO SEE IF IT DISPLAYS
        layout = QVBoxLayout(self)
        
        # Add extremely visible debug label
        test_label = QLabel("CRITICAL DEBUG: THIS SHOULD BE VISIBLE")
        test_label.setStyleSheet("""
            background-color: red; 
            color: white; 
            font-size: 24px;
            padding: 20px;
            margin: 20px;
        """)
        test_label.setFixedHeight(100)
        test_label.setAlignment(Qt.AlignCenter)
        
        # Button to test interaction
        test_button = QPushButton("CLICK ME TO PROVE INTERACTION WORKS")
        test_button.setStyleSheet("""
            background-color: green;
            color: white;
            font-size: 18px;
            padding: 10px;
            margin: 20px;
        """)
        test_button.setFixedHeight(50)
        test_button.clicked.connect(lambda: test_label.setText("Button clicked! UI is working!"))
        
        # Add widgets directly to layout
        layout.addWidget(test_label)
        layout.addWidget(test_button)
        
        # Print to console for verification
        print("VideosTab COMPLETELY SIMPLIFIED UI CREATED")
        
        # Skip all the complex UI setup for now to isolate the problem


class CourseCard(QFrame):
    """Widget for displaying a course card in the grid."""
    
    # Signal emitted when card is clicked
    clicked = pyqtSignal(bool)
    
    def __init__(self, course_data, parent=None):
        super().__init__(parent)
        self.course_data = course_data
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Creating CourseCard for: {course_data['title']}")
        
        # Set fixed size to ensure consistent layout
        self.setFixedSize(300, 280)
        self.setStyleSheet("""
            CourseCard {
                background-color: #333;
                border-radius: 10px;
                margin: 5px;
                border: 2px solid #FF0000; /* RED DEBUGGING BORDER */
            }
            CourseCard:hover {
                background-color: #444;
                border: 2px solid #3498db;
            }
        """)
        
        # Make clickable
        self.setCursor(Qt.PointingHandCursor)
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Thumbnail area
        thumbnail = QLabel()
        thumbnail.setFixedHeight(150)
        thumbnail.setStyleSheet("""
            background-color: #555;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 0;
            margin: 0;
        """)
        
        # Create thumbnail image with consistent color based on course ID
        thumbnail_pixmap = self.create_thumbnail(course_data)
        thumbnail.setPixmap(thumbnail_pixmap)
        
        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 12, 15, 12)
        content_layout.setSpacing(5)
        
        # Title
        title = QLabel(course_data["title"])
        title.setStyleSheet("font-weight: bold; color: white; font-size: 16px;")
        title.setWordWrap(True)
        title.setFixedHeight(40)
        
        # Description (limited height)
        description = QLabel(course_data["description"])
        description.setStyleSheet("color: #CCC; font-size: 12px;")
        description.setWordWrap(True)
        description.setFixedHeight(40)
        
        # Meta info
        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(10)
        
        # Level badge
        level_label = QLabel(course_data["level"].capitalize())
        level_badge_style = {
            "beginner": "background-color: #27ae60;",
            "intermediate": "background-color: #f39c12;",
            "advanced": "background-color: #c0392b;"
        }
        level_style = level_badge_style.get(course_data["level"], "background-color: #3498db;")
        level_label.setStyleSheet(f"""
            padding: 3px 8px;
            {level_style}
            color: white;
            border-radius: 3px;
            font-size: 10px;
        """)
        
        # Duration
        duration_label = QLabel(f"🕒 {course_data['duration']}")
        duration_label.setStyleSheet("color: #999; font-size: 12px;")
        
        # Lessons
        lessons_label = QLabel(f"📚 {course_data['lessons']} Lessons")
        lessons_label.setStyleSheet("color: #999; font-size: 12px;")
        
        meta_layout.addWidget(level_label)
        meta_layout.addWidget(duration_label)
        meta_layout.addWidget(lessons_label)
        meta_layout.addStretch()
        
        # Add everything to the content layout
        content_layout.addWidget(title)
        content_layout.addWidget(description)
        content_layout.addWidget(meta_widget)
        
        # Add thumbnail and content to main layout
        layout.addWidget(thumbnail)
        layout.addWidget(content)
        
        # Ensure card is visible
        self.setVisible(True)
        
    def create_thumbnail(self, course_data):
        """Create a thumbnail for the course card."""
        try:
            # Generate a consistent color based on the course ID
            color_seed = course_data["id"] % 10
            colors = [
                QColor(255, 100, 100),  # Red
                QColor(100, 200, 100),  # Green
                QColor(100, 100, 255),  # Blue
                QColor(255, 200, 100),  # Orange
                QColor(200, 100, 255),  # Purple
                QColor(100, 200, 255),  # Light blue
                QColor(255, 100, 200),  # Pink
                QColor(200, 255, 100),  # Lime
                QColor(255, 200, 200),  # Light pink
                QColor(200, 200, 255)   # Light purple
            ]
            
            # Create a gradient for the thumbnail
            base_color = colors[color_seed]
            darker_color = QColor(int(base_color.red() * 0.7), int(base_color.green() * 0.7), int(base_color.blue() * 0.7))
            
            # Create the pixmap
            thumbnail_pixmap = QPixmap(300, 150)
            thumbnail_pixmap.fill(base_color)  # Fill with solid color first as fallback
            
            # Then try to add gradient and icon
            painter = QPainter(thumbnail_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create and draw gradient
            gradient = QLinearGradient(0, 0, 300, 150)
            gradient.setColorAt(0, base_color)
            gradient.setColorAt(1, darker_color)
            painter.fillRect(0, 0, 300, 150, gradient)
            
            # Draw course icon
            icon_color = QColor(255, 255, 255, 180)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(icon_color))
            
            # Draw different icon based on course level
            if course_data["level"] == "beginner":
                # Draw a flag icon for beginner courses
                painter.drawRect(135, 55, 30, 5)  # Flag pole
                painter.drawRect(135, 55, 5, 40)  # Flag pole
                painter.drawRect(140, 55, 25, 20)  # Flag
            elif course_data["level"] == "intermediate":
                # Draw a steering wheel for intermediate courses
                painter.drawEllipse(125, 45, 50, 50)  # Outer circle
                painter.setBrush(QBrush(darker_color))
                painter.drawEllipse(140, 60, 20, 20)  # Inner circle
            else:
                # Draw a trophy for advanced courses
                painter.drawRect(135, 60, 30, 35)  # Trophy cup
                painter.drawRect(145, 95, 10, 10)  # Trophy base
                painter.drawRect(140, 105, 20, 5)  # Trophy bottom
                
            # Add text label for type
            painter.setPen(QPen(Qt.white))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            if course_data["level"] == "beginner":
                painter.drawText(10, 20, "BEGINNER")
            elif course_data["level"] == "intermediate":
                painter.drawText(10, 20, "INTERMEDIATE")
            else:
                painter.drawText(10, 20, "ADVANCED")
            
            painter.end()
            return thumbnail_pixmap
            
        except Exception as e:
            self.logger.error(f"Error creating thumbnail: {e}")
            # Use a solid color as fallback
            thumbnail_pixmap = QPixmap(300, 150)
            thumbnail_pixmap.fill(QColor(80, 80, 80))
            return thumbnail_pixmap
        
    def mousePressEvent(self, event):
        """Handle mouse press events to emit clicked signal."""
        super().mousePressEvent(event)
        self.clicked.emit(True)


class CourseView(QWidget):
    """Widget for displaying detailed course information and video player."""
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with back button
        header = QWidget()
        header.setStyleSheet("background-color: #333;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        self.back_button = QPushButton("← Back to Courses")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setStyleSheet("""
            background: none;
            border: none;
            color: #3498db;
            font-size: 14px;
            font-weight: bold;
            padding: 5px;
            text-align: left;
        """)
        
        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        
        # Course content area
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Video player area (left side)
        video_area = QWidget()
        video_area.setMinimumWidth(640)
        video_layout = QVBoxLayout(video_area)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(15)
        
        # Video player placeholder
        self.video_player = QWebEngineView()
        self.video_player.setMinimumHeight(360)
        self.video_player.setStyleSheet("background-color: #111; border-radius: 5px;")
        # Load a placeholder initially
        self.video_player.setHtml("""
            <html>
                <body style="margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100%;background:#111;">
                    <div style="text-align:center;color:#666;font-family:Arial,sans-serif;">
                        <div style="font-size:48px;margin-bottom:10px;">▶️</div>
                        <div style="font-size:18px;">Select a lesson to start</div>
                    </div>
                </body>
            </html>
        """)
        
        # Current video info
        self.current_title = QLabel("Select a lesson to start")
        self.current_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        video_layout.addWidget(self.video_player)
        video_layout.addWidget(self.current_title)
        
        # Course modules area (right side)
        modules_area = QWidget()
        modules_layout = QVBoxLayout(modules_area)
        modules_layout.setContentsMargins(0, 0, 0, 0)
        modules_layout.setSpacing(5)
        
        # Course title
        self.course_title = QLabel("Course Title")
        self.course_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        
        # Instructor
        self.instructor = QLabel("Instructor: Instructor Name")
        self.instructor.setStyleSheet("color: #CCC; font-size: 14px;")
        
        # Course stats
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 10, 0, 10)
        stats_layout.setSpacing(15)
        
        self.level_label = QLabel("Level: Beginner")
        self.level_label.setStyleSheet("color: #CCC; font-size: 14px;")
        
        self.duration_label = QLabel("Duration: 3h 20m")
        self.duration_label.setStyleSheet("color: #CCC; font-size: 14px;")
        
        self.lessons_label = QLabel("Lessons: 12")
        self.lessons_label.setStyleSheet("color: #CCC; font-size: 14px;")
        
        stats_layout.addWidget(self.level_label)
        stats_layout.addWidget(self.duration_label)
        stats_layout.addWidget(self.lessons_label)
        stats_layout.addStretch()
        
        # Modules title
        modules_title = QLabel("Course Modules")
        modules_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-top: 10px;")
        
        # Modules list
        modules_scroll = QScrollArea()
        modules_scroll.setWidgetResizable(True)
        modules_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #333;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                border-radius: 5px;
            }
        """)
        
        self.modules_list = QWidget()
        self.modules_layout = QVBoxLayout(self.modules_list)
        self.modules_layout.setContentsMargins(0, 0, 0, 0)
        self.modules_layout.setSpacing(10)
        # self.modules_layout.addStretch() # REMOVED THIS LINE
        
        modules_scroll.setWidget(self.modules_list)
        
        # Add elements to modules area
        modules_layout.addWidget(self.course_title)
        modules_layout.addWidget(self.instructor)
        modules_layout.addWidget(stats_widget)
        modules_layout.addWidget(modules_title)
        modules_layout.addWidget(modules_scroll)
        
        # Add areas to content layout
        content_layout.addWidget(video_area, 2)
        content_layout.addWidget(modules_area, 1)
        
        # Add header and content to main layout
        layout.addWidget(header)
        layout.addWidget(content_area)
        
    def set_course(self, course_data):
        """Update the course view with new course data."""
        # Update course info
        self.course_title.setText(course_data["title"])
        self.instructor.setText(f"Instructor: {course_data['instructor']}")
        self.level_label.setText(f"Level: {course_data['level'].capitalize()}")
        self.duration_label.setText(f"Duration: {course_data['duration']}")
        self.lessons_label.setText(f"Lessons: {course_data['lessons']} lessons")
        
        # Clear existing modules
        # First, remove all widgets from the layout
        while self.modules_layout.count() > 0:
            item = self.modules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new modules
        for i, module in enumerate(course_data["modules"]):
            module_card = ModuleCard(module, i+1)
            module_card.clicked.connect(lambda checked, m=module: self.play_module(m))
            self.modules_layout.addWidget(module_card)
        
        # Add stretch at the end
        self.modules_layout.addStretch()
    
    def play_module(self, module):
        """Play the selected module video."""
        # Update the current title
        self.current_title.setText(module["title"])
        
        # Get the YouTube video ID
        video_id = module.get("video_id", "")
        
        # Create HTML for embedding YouTube video
        if video_id:
            # HTML template with YouTube embed
            html_content = f"""
            <html>
                <head>
                    <style>
                        body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #000; overflow: hidden; }}
                        .container {{ display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; }}
                        .video-container {{ width: 100%; height: 100%; position: relative; }}
                        iframe {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }}
                        .error-message {{ display: none; color: #FFF; text-align: center; padding: 20px; }}
                    </style>
                    <script>
                        // Add error handling for video loading
                        function showError() {{
                            document.getElementById('videoContainer').style.display = 'none';
                            document.getElementById('errorMessage').style.display = 'block';
                        }}
                        
                        // Check connection status
                        window.addEventListener('load', function() {{
                            if (!navigator.onLine) {{
                                showError();
                            }}
                        }});
                    </script>
                </head>
                <body>
                    <div class="container">
                        <div id="videoContainer" class="video-container">
                            <iframe 
                                src="https://www.youtube.com/embed/{video_id}?autoplay=0&rel=0" 
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                allowfullscreen
                                onerror="showError()">
                            </iframe>
                        </div>
                        <div id="errorMessage" class="error-message">
                            <h3>Unable to load video</h3>
                            <p>Please check your internet connection and try again.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            self.video_player.setHtml(html_content)
            
        else:
            # Fallback if no video ID is provided
            self.video_player.setHtml(f"""
                <html>
                    <body style="margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100%;background:#111;">
                        <div style="text-align:center;color:#EEE;font-family:Arial,sans-serif;">
                            <div style="font-size:24px;margin-bottom:20px;">{module["title"]}</div>
                            <div style="font-size:48px;margin-bottom:20px;">▶️</div>
                            <div style="font-size:16px;">Duration: {module["duration"]}</div>
                            <div style="font-size:14px;color:#999;margin-top:20px;">Video not available</div>
                        </div>
                    </body>
                </html>
            """)


class ModuleCard(QFrame):
    """Widget for displaying a module in the course view."""
    
    # Signal emitted when card is clicked
    clicked = pyqtSignal(bool)
    
    def __init__(self, module_data, module_number, parent=None):
        super().__init__(parent)
        self.module_data = module_data
        
        self.setStyleSheet("""
            ModuleCard {
                background-color: #333;
                border-radius: 5px;
                padding: 10px;
            }
            ModuleCard:hover {
                background-color: #444;
            }
        """)
        
        # Make clickable
        self.setCursor(Qt.PointingHandCursor)
        
        # Set up layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Module number
        number = QLabel(str(module_number))
        number.setStyleSheet("""
            background-color: #3498db;
            color: white;
            border-radius: 15px;
            min-width: 30px;
            min-height: 30px;
            max-width: 30px;
            max-height: 30px;
            font-weight: bold;
            qproperty-alignment: AlignCenter;
        """)
        
        # Module info
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(5)
        
        title = QLabel(module_data["title"])
        title.setStyleSheet("color: white; font-weight: bold;")
        
        duration = QLabel(f"Duration: {module_data['duration']}")
        duration.setStyleSheet("color: #CCC; font-size: 12px;")
        
        info_layout.addWidget(title)
        info_layout.addWidget(duration)
        
        # Play icon
        play = QLabel("▶")
        play.setStyleSheet("color: #3498db; font-size: 16px;")
        
        # Add everything to the layout
        layout.addWidget(number)
        layout.addWidget(info, 1)
        layout.addWidget(play)
        
    def mousePressEvent(self, event):
        """Handle mouse press events to emit clicked signal."""
        super().mousePressEvent(event)
        self.clicked.emit(True)


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

        # Attributes for background telemetry fetching
        self.telemetry_fetch_thread = None
        self.telemetry_fetch_worker = None

        # Flag to track if initial lap list load has happened
        self._initial_lap_load_done = False

        # Initialize UI
        self.setup_ui()
        
        # Connect to iRacing API if available
        if self.iracing_api is not None:
            try:
                # Try SimpleIRacingAPI method names first
                if hasattr(self.iracing_api, 'register_on_connection_changed'):
                    logger.info("Using SimpleIRacingAPI callback methods")
                    self.iracing_api.register_on_connection_changed(self.on_iracing_connected)
                    # self.iracing_api.register_on_session_info_changed(self.on_session_info_changed) # Legacy callback, use signal now
                    self.iracing_api.register_on_telemetry_data(self.on_telemetry_data)

                    # --- Connect the new signal --- #
                    if hasattr(self.iracing_api, 'sessionInfoUpdated'):
                        logger.info("Connecting sessionInfoUpdated signal to UI update slot.")
                        # Pass the dictionary payload from the signal to the slot
                        self.iracing_api.sessionInfoUpdated.connect(self._update_connection_status)
                    else:
                        logger.warning("iRacing API instance does not have sessionInfoUpdated signal.")
                    # ----------------------------- #

                    # Explicitly connect to iRacing (This will be passive now)
                    # self.iracing_api.connect() # Monitor thread handles connection
                    pass # Connect call only registers callbacks now

                # Fall back to IRacingAPI method names (This path likely won't be used anymore)
                elif hasattr(self.iracing_api, 'register_connection_callback'):
                    # logger.info("Using IRacingAPI callback methods")
                    # self.iracing_api.register_connection_callback(self.on_iracing_connected)
                    # self.iracing_api.register_session_info_callback(self.on_session_info_changed)
                    # self.iracing_api.register_telemetry_callback(self.on_telemetry_data)
                    logger.warning("Legacy IRacingAPI callback registration attempted - this might not work as expected.")
                else:
                    logger.warning("Unable to register callbacks with iRacing API - incompatible implementation")
            except Exception as e:
                logger.error(f"Error setting up callbacks for iRacing API: {e}")
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

        # -------- Lap selection controls (Phase 2, Step 4) --------
        controls_frame = QFrame() # Changed from lap_select_frame
        controls_layout = QGridLayout(controls_frame) # Use GridLayout for better arrangement
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setHorizontalSpacing(15) # Add horizontal spacing

        # -- Row 0: Session Selection --
        session_label = QLabel("Session:")
        session_label.setStyleSheet("color:#DDD")
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("background-color:#333;color:#EEE; padding: 3px;")
        self.session_combo.setMinimumWidth(400) # Give session combo more space
        self.session_combo.currentIndexChanged.connect(self.on_session_changed) # Connect signal

        self.refresh_button = QPushButton("🔄 Refresh All") # Combined refresh button
        self.refresh_button.setToolTip("Refresh session and lap lists from database")
        self.refresh_button.setStyleSheet("padding: 5px 10px;")
        self.refresh_button.clicked.connect(self.refresh_session_and_lap_lists) # Updated connection

        controls_layout.addWidget(session_label, 0, 0)
        controls_layout.addWidget(self.session_combo, 0, 1, 1, 2) # Span 2 columns
        controls_layout.addWidget(self.refresh_button, 0, 3)

        # -- Row 1: Lap Selection --
        left_label = QLabel("Lap A:")
        left_label.setStyleSheet("color:#DDD")
        self.left_lap_combo = QComboBox()
        self.left_lap_combo.setStyleSheet("background-color:#333;color:#EEE; padding: 3px;")
        self.left_lap_combo.setMinimumWidth(200)

        right_label = QLabel("Lap B:")
        right_label.setStyleSheet("color:#DDD")
        self.right_lap_combo = QComboBox()
        self.right_lap_combo.setStyleSheet("background-color:#333;color:#EEE; padding: 3px;")
        self.right_lap_combo.setMinimumWidth(200)

        self.compare_button = QPushButton("Compare Laps")
        self.compare_button.setStyleSheet("padding: 5px 10px;")
        self.compare_button.clicked.connect(self.on_compare_clicked)

        # Remove old refresh button
        # self.refresh_laps_button = QPushButton("🔄") # Refresh icon
        # self.refresh_laps_button.setToolTip("Refresh lap list from database")
        # self.refresh_laps_button.setStyleSheet("padding: 5px;")
        # self.refresh_laps_button.setFixedWidth(40)
        # self.refresh_laps_button.clicked.connect(self.refresh_lap_list)

        controls_layout.addWidget(left_label, 1, 0)
        controls_layout.addWidget(self.left_lap_combo, 1, 1)
        controls_layout.addWidget(right_label, 1, 2)
        controls_layout.addWidget(self.right_lap_combo, 1, 3)
        controls_layout.addWidget(self.compare_button, 1, 4)
        # Remove old refresh button widget add
        # lap_select_layout.addWidget(self.refresh_laps_button)

        telemetry_layout.addWidget(controls_frame) # Add the controls frame

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
        # This can still be called by the API's connection logic (e.g., via update_info_from_monitor)
        logger.info(f"UI: on_iracing_connected called with is_connected={is_connected}")
        self.is_connected = is_connected
        # No longer need to update session_info here, signal handler does it
        # if session_info:
        #     self.session_info = session_info
        self._update_connection_status() # Update UI based on new connection state

    def on_session_info_changed(self, session_info):
        """(Legacy/Fallback) Handle session info changes from iRacing API callbacks."""
        logger.info("UI: on_session_info_changed (legacy callback) called.")
        self.session_info = session_info # Store locally just in case
        # Let the signal handler _update_connection_status handle the UI update
        # self._update_session_info_ui(session_info)

    def _update_connection_status(self, payload: dict):
        """Update UI based on connection status and session info signal payload."""
        logger.debug(f"UI received update signal with payload: {payload}")
        # Extract info from the payload sent by the signal
        is_connected = payload.get('is_connected', False)
        session_info = payload.get('session_info', {})

        # Update internal state
        self.is_connected = is_connected
        self.session_info = session_info # Store the latest info

        if self.is_connected:
            self.connection_label.setText("iRacing: Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")

            # Get latest track/car from the received session_info dictionary
            track_name = session_info.get('current_track', "No Track")
            car_name = session_info.get('current_car', "No Car")
            # TODO: Get driver name if added to session_info
            driver_name = "N/A" # Placeholder

            # Update labels
            self.track_label.setText(f"Track: {track_name}")
            self.driver_label.setText(f"Car: {car_name}") # Using driver label for car for now

        else:
            self.connection_label.setText("iRacing: Disconnected")
            self.connection_label.setStyleSheet("color: red; font-weight: bold;")
            self.driver_label.setText("No Driver")
            self.track_label.setText("No Track")

    # def _update_session_info_ui(self, session_info):
    #    """(Deprecated) Update UI with session information."""
    #    # This logic is now merged into _update_connection_status
    #    pass

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

        # Trigger initial load only once
        if not self._initial_lap_load_done:
             logger.info("RaceCoachWidget shown, triggering initial lap list load.")
             # First, ensure the auth module state is synchronized with the client
             update_auth_state_from_client()
             # self.refresh_lap_list() # Auth check is now inside this method - THIS LINE IS WRONG
             self.perform_initial_load() # Call this instead to handle sessions and laps
             self._initial_lap_load_done = True

    def perform_initial_load(self):
        """Performs the initial authentication check and lap list load."""
        logger.info("RaceCoachWidget performing initial load.")

        # Explicitly check auth using the main client
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            is_authenticated = main_supabase.is_authenticated()
            logger.info(f"perform_initial_load: Authentication check via main client: {is_authenticated}")
        except Exception as e:
            logger.error(f"Error checking auth state in perform_initial_load: {e}")
            is_authenticated = False # Assume not logged in if check fails

        if not is_authenticated:
            logger.warning("User not authenticated (checked via main client). Cannot load sessions/laps.")
            self.session_combo.clear()
            self.session_combo.addItem("Log in to view sessions", None)
            self.left_lap_combo.clear()
            self.left_lap_combo.addItem("Log in first", None)
            self.right_lap_combo.clear()
            self.right_lap_combo.addItem("Log in first", None)
            return

        # If authenticated, proceed to refresh lists
        logger.info("User is authenticated, proceeding to refresh lists.")
        self.refresh_session_list() # Fetch sessions first
        current_session_id = self.session_combo.currentData() # Get the currently selected session ID
        if current_session_id:
             self.refresh_lap_list(current_session_id) # Fetch laps for that session
        else:
             # If no session is selected after refresh, update lap combos
             self.left_lap_combo.clear()
             self.left_lap_combo.addItem("Select session", None)
             self.right_lap_combo.clear()
             self.right_lap_combo.addItem("Select session", None)


    # -------- Lap Comparison Methods (Phase 2) --------

    def refresh_session_and_lap_lists(self):
        """Refreshes both the session list and the laps for the currently selected session."""
        logger.info("Refreshing session and lap lists...")
        
        # Explicitly check auth using the main client
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            is_authenticated = main_supabase.is_authenticated()
            logger.info(f"refresh_session_and_lap_lists: Auth check via main client: {is_authenticated}")
        except Exception as e:
            logger.error(f"Error checking auth state in refresh_session_and_lap_lists: {e}")
            is_authenticated = False # Assume not logged in if check fails

        if not is_authenticated:
            logger.warning("User not logged in (checked via main client). Cannot refresh sessions or laps.")
            self.session_combo.clear()
            self.session_combo.addItem("Log in to view sessions", None)
            self.left_lap_combo.clear()
            self.left_lap_combo.addItem("Log in first", None)
            self.right_lap_combo.clear()
            self.right_lap_combo.addItem("Log in first", None)
            return

        # Fetch and populate sessions
        self.refresh_session_list()

        # After sessions are loaded, trigger lap list refresh for the selected session
        # (The on_session_changed slot will handle this if the session index changes,
        # but we need to trigger it manually if the session list refreshes but the
        # selected index stays the same)
        current_session_id = self.session_combo.currentData()
        if current_session_id:
            self.refresh_lap_list(current_session_id)
        else:
            # No session selected or available, clear lap lists
            self.left_lap_combo.clear()
            self.left_lap_combo.addItem("Select a session", None)
            self.right_lap_combo.clear()
            self.right_lap_combo.addItem("Select a session", None)

    def refresh_session_list(self):
        """Fetch latest sessions from Supabase and populate the session combo box."""
        logger.info("Refreshing session list...")
        self.session_combo.clear()
        
        # REMOVED Redundant Auth Check - Now handled by calling functions
        # if not is_logged_in():
        #     self.session_combo.addItem("Log in to view sessions", None)
        #     return
            
        sessions, msg = get_sessions(limit=50, user_only=True) # Assuming get_sessions exists

        if sessions is None:
            logger.error(f"Failed to fetch sessions: {msg}")
            self.session_combo.addItem(f"Error: {msg}", None)
            return
        
        if not sessions:
            self.session_combo.addItem("No sessions found", None)
            return
            
        # Populate the session combo box
        logger.info(f"Populating session list with {len(sessions)} sessions.")
        for session in sessions:
            session_id = session.get("id")
            created_at_str = session.get("created_at", "")
            track_name = session.get("track_name", "Unknown Track")
            car_name = session.get("car_name", "Unknown Car")
            
            try:
                # Attempt to parse timestamp for display
                timestamp = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')) # Handle Z timezone
                display_text = f"{timestamp.strftime('%Y-%m-%d %H:%M')} - {track_name} ({car_name})"
            except (ValueError, TypeError):
                 display_text = f"{created_at_str} - {track_name} ({car_name})" # Fallback
                 
            self.session_combo.addItem(display_text, session_id)

    def refresh_lap_list(self, session_id):
        """Fetch latest laps from Supabase and populate combo boxes."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Refreshing lap list...")
        
        # Try multiple approaches to get laps - this is the most robust solution
        # that handles the case when the Race Coach module has its own Supabase client
        # that isn't fully initialized yet
        
        # First try the normal approach using module auth
        laps = None
        
        # 1. Try using our module's auth and client
        if is_logged_in():
            laps, msg = get_laps(limit=50, user_only=True, session_id=session_id) # Filter by session_id
            if laps:
                logger.info(f"Successfully fetched {len(laps)} laps for session {session_id} using module client")
                
        # 2. If that didn't work, try direct database access with main app's client
        if not laps:
            logger.info("Module client fetch failed, trying main app client")
            try:
                # Import the main app's Supabase client
                from trackpro.database.supabase_client import supabase as main_supabase
                
                if main_supabase and main_supabase.client:
                    # Check if user is authenticated in main app
                    try:
                        user = main_supabase.get_user()
                        if user:
                            # Debug the user object structure
                            user_repr = str(user)[:100] + "..." if len(str(user)) > 100 else str(user)
                            logger.info(f"Found user object: {user_repr}")
                            
                            # Determine user info - handle different response structures
                            user_id = None
                            if hasattr(user, 'id'):
                                user_id = user.id
                                logger.info(f"Found user ID directly: {user_id}")
                            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                                user_id = user.user.id
                                logger.info(f"Found user ID via user.user: {user_id}")
                            elif hasattr(user, 'data') and hasattr(user.data, 'user') and hasattr(user.data.user, 'id'):
                                user_id = user.data.user.id
                                logger.info(f"Found user ID via data.user: {user_id}")
                            
                            # Log success without trying to access email
                            logger.info("Successfully got authenticated user from main app")
                            
                            # Query laps directly - don't filter by user ID as we're already authenticated
                            response = main_supabase.client.table("laps").select("*").eq('session_id', session_id).limit(50).execute()
                            if response:
                                # Debug the response structure
                                resp_repr = str(response)[:100] + "..." if len(str(response)) > 100 else str(response)
                                logger.info(f"Got response: {resp_repr}")
                                
                                # Try different ways to access the data
                                if hasattr(response, 'data'):
                                    laps = response.data
                                elif hasattr(response, 'json') and callable(response.json):
                                    try:
                                        json_data = response.json()
                                        laps = json_data.get('data', [])
                                    except:
                                        laps = []
                                elif isinstance(response, dict) and 'data' in response:
                                    laps = response['data']
                                else:
                                    # Last resort - maybe response itself is the data array
                                    laps = response if isinstance(response, list) else []
                                
                                if laps:
                                    logger.info(f"Successfully fetched {len(laps)} laps for session {session_id} using main app client")
                    except Exception as e:
                        logger.warning(f"Error checking main app authentication: {e}")
                        # Log more details about the exception
                        import traceback
                        logger.debug(f"Authentication error traceback: {traceback.format_exc()}")
            except Exception as e:
                logger.warning(f"Error accessing main app Supabase client: {e}")
                # Log more details about the exception
                import traceback
                logger.debug(f"Supabase client error traceback: {traceback.format_exc()}")
                
        # Try yet another approach if all else fails - direct SQL query
        if not laps and hasattr(self, 'data_manager'):
            try:
                logger.info("Trying to fetch laps through local database")
                # Try to get laps from local database (assuming filter capability exists)
                local_laps = self.data_manager.get_laps(limit=50, session_id=session_id)
                if local_laps:
                    laps = local_laps
                    logger.info(f"Successfully fetched {len(laps)} laps from local database")
            except Exception as e:
                logger.warning(f"Error fetching local laps: {e}")
                
        # If still no laps for this session, show message
        if not laps:
            logger.warning("All lap fetch approaches failed - showing login message")
            self.left_lap_combo.addItem("No laps for this session", None)
            self.right_lap_combo.addItem("No laps for this session", None)
            return

        # Success! Update the combo boxes
        self.left_lap_combo.clear()
        self.right_lap_combo.clear()
        
        # Display lap number and time
        for lap in laps:
            lap_id = lap.get("id")
            lap_num = lap.get("lap_number", "N/A")
            lap_time = lap.get("lap_time")
            if lap_time is not None:
                display_text = f"Lap {lap_num}  -  {self._format_time(lap_time)}"
            else:
                display_text = f"Lap {lap_num}  -  (No Time)"
            self.left_lap_combo.addItem(display_text, lap_id)
            self.right_lap_combo.addItem(display_text, lap_id)
        logger.info(f"Populated lap lists with {len(laps)} laps.")

    def on_compare_clicked(self):
        """Initiates the background fetch for selected lap telemetry."""
        # Check if a fetch is already running
        if self.telemetry_fetch_thread is not None and self.telemetry_fetch_thread.isRunning():
            logger.warning("Comparison already in progress. Please wait.")
            # Optionally show a brief message to the user
            # QMessageBox.information(self, "In Progress", "Lap comparison already running.")
            return

        left_lap_id = self.left_lap_combo.currentData()
        right_lap_id = self.right_lap_combo.currentData()

        if not left_lap_id or not right_lap_id:
            logger.warning("Please select two laps to compare.")
            QMessageBox.warning(self, "Selection Missing", "Please select a lap for both Lap A and Lap B.")
            return

        logger.info(f"Starting telemetry fetch for Lap A ({left_lap_id}) and Lap B ({right_lap_id})")

        # Create worker and thread
        self.telemetry_fetch_worker = TelemetryFetchWorker(left_lap_id, right_lap_id)
        self.telemetry_fetch_thread = QThread()
        self.telemetry_fetch_worker.moveToThread(self.telemetry_fetch_thread)

        # Connect signals
        self.telemetry_fetch_worker.finished.connect(self._on_telemetry_fetch_finished) # Connect to new slot
        self.telemetry_fetch_worker.error.connect(self._on_telemetry_fetch_error)       # Connect to new slot
        self.telemetry_fetch_thread.started.connect(self.telemetry_fetch_worker.run)
        self.telemetry_fetch_worker.finished.connect(self.telemetry_fetch_thread.quit)
        self.telemetry_fetch_worker.finished.connect(self.telemetry_fetch_worker.deleteLater)
        self.telemetry_fetch_thread.finished.connect(self.telemetry_fetch_thread.deleteLater)
        # Add error signal connection for cleanup
        self.telemetry_fetch_worker.error.connect(self.telemetry_fetch_thread.quit)
        self.telemetry_fetch_worker.error.connect(self.telemetry_fetch_worker.deleteLater)


        # Start the thread
        self.telemetry_fetch_thread.start()

        # Optionally disable UI elements while loading
        self.compare_button.setEnabled(False)
        self.compare_button.setText("Loading...")


    def _on_telemetry_fetch_finished(self, left_data, right_data):
        """Handle the results from the TelemetryFetchWorker."""
        logger.info("Telemetry fetch finished. Processing results...")
        self.compare_button.setEnabled(True) # Re-enable button
        self.compare_button.setText("Compare Laps")

        # Check if data is valid before updating
        if left_data is None and right_data is None:
             logger.error("Both lap fetches failed or calculation failed.")
             QMessageBox.critical(self, "Error", "Failed to load telemetry data for both selected laps.")
             return
        elif left_data is None:
             logger.warning("Left lap data fetch or calculation failed.")
             # Proceed with right data only? Or show error? For now, show warning.
             QMessageBox.warning(self, "Warning", "Failed to load telemetry for Lap A. Displaying Lap B only.")
        elif right_data is None:
             logger.warning("Right lap data fetch or calculation failed.")
             QMessageBox.warning(self, "Warning", "Failed to load telemetry for Lap B. Displaying Lap A only.")

        # Update TelemetryComparisonWidget
        if hasattr(self, 'telemetry_widget'):
            if left_data and 'stats' in left_data:
                 # Also add lap time if available in combo box text
                 left_lap_text = self.left_lap_combo.currentText()
                 try:
                     lap_time_str = left_lap_text.split('-')[-1].strip()
                     if lap_time_str != '(No Time)':
                         # Convert M:SS.mmm to seconds
                         parts = lap_time_str.split(':')
                         if len(parts) == 2:
                              seconds_parts = parts[1].split('.')
                              if len(seconds_parts) == 2:
                                   minutes = int(parts[0])
                                   seconds = int(seconds_parts[0])
                                   milliseconds = int(seconds_parts[1])
                                   left_data['stats']['lap_time'] = minutes * 60 + seconds + milliseconds / 1000.0
                 except Exception as e:
                     logger.warning(f"Could not parse lap time from '{left_lap_text}': {e}")

                 self.telemetry_widget.set_driver_data(True, left_data['stats'])
            else:
                 # Clear left driver data if fetch failed
                 self.telemetry_widget.set_driver_data(True, {"full_throttle": 0, "heavy_braking": 0, "cornering": 0, "lap_time": 0, "gap": 0})


            if right_data and 'stats' in right_data:
                 # Add lap time if available
                 right_lap_text = self.right_lap_combo.currentText()
                 try:
                     lap_time_str = right_lap_text.split('-')[-1].strip()
                     if lap_time_str != '(No Time)':
                         parts = lap_time_str.split(':')
                         if len(parts) == 2:
                              seconds_parts = parts[1].split('.')
                              if len(seconds_parts) == 2:
                                   minutes = int(parts[0])
                                   seconds = int(seconds_parts[0])
                                   milliseconds = int(seconds_parts[1])
                                   right_data['stats']['lap_time'] = minutes * 60 + seconds + milliseconds / 1000.0
                 except Exception as e:
                     logger.warning(f"Could not parse lap time from '{right_lap_text}': {e}")

                 self.telemetry_widget.set_driver_data(False, right_data['stats'])
            else:
                 # Clear right driver data if fetch failed
                 self.telemetry_widget.set_driver_data(False, {"full_throttle": 0, "heavy_braking": 0, "cornering": 0, "lap_time": 0, "gap": 0})

            # Update speed graph
            left_speed = left_data['points']['speed'] if left_data and 'points' in left_data else []
            right_speed = right_data['points']['speed'] if right_data and 'points' in right_data else []
            self.telemetry_widget.set_speed_data(left_speed, right_speed)

            # --- Calculate and Update Delta Graph ---
            delta_data = []
            if left_data and right_data and left_data['points']['track_position'] and right_data['points']['track_position']:
                try:
                    # Ensure timestamps are aligned or interpolate?
                    # For simplicity, assume points roughly align by track position for now.
                    # This requires a more sophisticated alignment based on track_position
                    # Let's just calculate a simple delta based on time difference if timestamps exist
                    # (This part needs refinement for accurate delta calculation)

                    # Placeholder: Calculate time difference based on index for now
                    # Assuming left_lap is baseline
                    # Find total time for each lap first
                    left_total_time = left_data['stats'].get('lap_time', 0)
                    right_total_time = right_data['stats'].get('lap_time', 0)

                    if left_total_time > 0 and right_total_time > 0:
                         # Simplified delta - this isn't a proper per-point delta graph
                         delta_data = [0] * len(left_data['points']['track_position']) # Needs real calc
                         logger.warning("Delta calculation is currently a placeholder.")
                    else:
                         logger.warning("Cannot calculate delta without lap times.")

                except Exception as e:
                    logger.error(f"Error calculating delta: {e}")

            self.telemetry_widget.set_delta_data(delta_data)

            # Update the overall widget to redraw graphs
            self.telemetry_widget.update()


    def _on_telemetry_fetch_error(self, msg_left, msg_right):
        """Handle errors from the TelemetryFetchWorker."""
        logger.error(f"Telemetry fetch failed. Left: '{msg_left}', Right: '{msg_right}'")
        QMessageBox.critical(self, "Telemetry Error",
                             f"Could not load telemetry data.\\n\\nLap A: {msg_left}\\nLap B: {msg_right}")
        # Re-enable the compare button
        self.compare_button.setEnabled(True)
        self.compare_button.setText("Compare Laps")

    def on_session_changed(self, index):
        """Handle session selection changes from the combo box."""
        # Get the selected session ID (stored as data)
        session_id = self.session_combo.itemData(index)
        if session_id:
            logger.info(f"Session changed to: {session_id}")
            self.refresh_lap_list(session_id)
        else:
            # Handle case where "No sessions found" or error item is selected
            logger.info("Invalid session selected or no sessions available.")
            self.left_lap_combo.clear()
            self.right_lap_combo.clear()
            self.left_lap_combo.addItem("Select session first", None)
            self.right_lap_combo.addItem("Select session first", None)


# Example of how to use the RaceCoachWidget
if __name__ == '__main__':
    # Add pass or actual example code here
    pass
