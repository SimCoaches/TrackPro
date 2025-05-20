"""Main application UI module."""

import os
import sys
import logging
import traceback
import time
import math

# Version information - hardcoded to avoid cyclic imports
__version__ = "1.4.6"

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QFrame, QSplitter, QWidget, QMessageBox, 
    QSlider, QComboBox, QSpinBox, QCheckBox, QProgressBar,
    QDialog, QFileDialog, QFormLayout, QLineEdit, QAction,
    QMenu, QApplication, QStyleFactory, QGridLayout, QTextEdit,
    QMenuBar, QMenu, QDialogButtonBox, QStackedWidget, QRadioButton, 
    QButtonGroup, QGroupBox, QStatusBar, QProgressDialog, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QPointF, QTimer, pyqtSignal, QSettings, QThread, 
    pyqtSlot, QSize, QRectF, QMargins, QObject
)
from PyQt5.QtGui import (
    QPalette, QColor, QIcon, QPen, QBrush, QPainterPath, QFont,
    QPainter, QLinearGradient, QMouseEvent, QHideEvent, QShowEvent,
    QKeySequence, QDesktopServices, QPixmap
)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries, QAreaSeries
import pyqtgraph as pg
from .calibration_chart import CalibrationChart
from .config import config
from .pedals.calibration import CalibrationWizard # Added this import
from .pedals.profile_dialog import PedalProfileDialog
from .race_coach.ui import RaceCoachWidget # Add import
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from trackpro.gamification.ui.race_pass_view import RacePassViewWidget
from trackpro.gamification.ui.quest_view import QuestViewWidget
from trackpro.gamification.ui.overview_elements import GamificationOverviewWidget

# Set up logging
logger = logging.getLogger(__name__)

# Default curve types
DEFAULT_CURVE_TYPES = ["Linear", "S-Curve", "Aggressive", "Progressive", "Custom"]

class DraggableChartView(QChartView):
    """Custom chart view that supports point dragging."""
    
    point_moved = pyqtSignal()  # Signal emitted when a point is moved
    
    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QChartView.MinimalViewportUpdate)  # Use minimal updates for better performance
        self.setMouseTracking(True)
        self.dragging_point = None
        self.scatter_series = None
        self.line_series = None
        self.original_points = []  # Store original point order
        self.dragging_active = False  # Flag to track active dragging state
        
        # Add mouse move throttling for better performance
        self.last_move_time = 0
        self.move_interval = 16  # More responsive (~60fps) while still preventing excessive updates
        self.pending_update = False
        self.current_drag_pos = None  # Store current drag position
    
    def set_scatter_series(self, series, line_series=None):
        """Set the scatter series and line series for dragging points."""
        self.scatter_series = series
        self.line_series = line_series
        # Store initial point order
        self.original_points = [self.scatter_series.at(i) for i in range(self.scatter_series.count())]
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press to start dragging points."""
        if event.button() == Qt.LeftButton and self.scatter_series:
            # Find closest point within 20 pixels
            closest_point = None
            min_distance = float('inf')
            
            for i in range(self.scatter_series.count()):
                point = self.scatter_series.at(i)
                screen_point = self.chart().mapToPosition(point)
                distance = (screen_point - event.pos()).manhattanLength()
                
                if distance < 20 and distance < min_distance:
                    min_distance = distance
                    closest_point = i
            
            if closest_point is not None:
                self.dragging_point = closest_point
                self.dragging_active = True
                # Store original points before drag starts
                self.original_points = [self.scatter_series.at(i) for i in range(self.scatter_series.count())]
                self.current_drag_pos = event.pos()
                event.accept()
                return
                
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle point dragging."""
        if self.dragging_point is not None and self.scatter_series and self.dragging_active:
            # Store current drag position
            self.current_drag_pos = event.pos()
            
            # Add throttling to prevent excessive updates, but keep it responsive
            current_time = int(time.time() * 1000)
            if current_time - self.last_move_time < self.move_interval:
                # Schedule an update if we don't have one already
                if not self.pending_update:
                    QTimer.singleShot(self.move_interval, self.process_pending_drag)
                    self.pending_update = True
                return
            
            self.last_move_time = current_time
            self.pending_update = False
            self.update_drag_position(self.current_drag_pos)
            event.accept()
            return
            
        super().mouseMoveEvent(event)
    
    def process_pending_drag(self):
        """Process any pending drag updates."""
        self.pending_update = False
        if self.dragging_active and self.current_drag_pos:
            self.update_drag_position(self.current_drag_pos)
    
    def update_drag_position(self, pos):
        """Update the dragged point position with the given mouse position."""
        if self.dragging_point is None or not self.scatter_series or not self.dragging_active:
            return
            
        value = self.chart().mapToValue(pos)
        
        # Get current points while maintaining order
        points = self.original_points.copy()
        
        # Calculate allowed x range for this point
        min_x = 0 if self.dragging_point == 0 else points[self.dragging_point - 1].x() + 1
        max_x = 100 if self.dragging_point == len(points) - 1 else points[self.dragging_point + 1].x() - 1
        
        # Constrain to valid range
        x = max(min_x, min(max_x, value.x()))
        y = max(0, min(100, value.y()))
        
        # Update only the dragged point
        points[self.dragging_point] = QPointF(x, y)
        
        # Update scatter series - clear and reload all points to avoid flickering
        self.scatter_series.clear()
        for point in points:
            self.scatter_series.append(point)
        
        # Update line series
        if self.line_series:
            self.line_series.clear()
            for point in points:
                self.line_series.append(point)
        
        # Update our stored points
        self.original_points = points
        
        self.point_moved.emit()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end point dragging."""
        if event.button() == Qt.LeftButton and self.dragging_point is not None:
            self.dragging_active = False
            self.dragging_point = None
            self.current_drag_pos = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

# Completely new implementation for the plot graph system
class IntegratedCalibrationChart:
    """
    A completely redesigned chart system that guarantees the indicator dot
    is always perfectly aligned with the curve.
    """
    def __init__(self, parent_layout, pedal_name, on_curve_changed_callback):
        self.pedal_name = pedal_name
        self.on_curve_changed = on_curve_changed_callback
        self.input_percentage = 0
        self.points = []  # Calibration points
        self.min_deadzone = 0  # Minimum deadzone percentage
        self.max_deadzone = 0  # Maximum deadzone percentage
        self.last_update_time = 0  # Timestamp of last update
        self.update_interval = 33  # Increased to ~30fps for better performance
        self.update_scheduled = False  # Track whether an update is already scheduled
        
        # Create chart with dark theme
        self.chart = QChart()
        # Remove title to save space since we already removed the pedal names
        # from the UI headers
        self.chart.setBackgroundVisible(True)
        self.chart.setBackgroundBrush(QColor(53, 53, 53))
        self.chart.setPlotAreaBackgroundVisible(True)
        self.chart.setPlotAreaBackgroundBrush(QColor(35, 35, 35))
        self.chart.setTitleBrush(QColor(255, 255, 255))
        self.chart.setAnimationOptions(QChart.NoAnimation)  # Disable animations for precise positioning
        self.chart.legend().hide()
        
        # Adjust chart margins - reduce top and sides, increase bottom substantially
        self.chart.setContentsMargins(10, 10, 10, 40)  # Restore reasonable margins
        
        # Create persistent line series for deadzone visualization
        self.min_deadzone_lower_series = QLineSeries()
        self.min_deadzone_upper_series = QLineSeries()
        self.min_deadzone_lower_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        self.min_deadzone_upper_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        
        self.max_deadzone_lower_series = QLineSeries()
        self.max_deadzone_upper_series = QLineSeries()
        self.max_deadzone_lower_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        self.max_deadzone_upper_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        
        # Create axes with grid
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 100)
        self.axis_x.setTitleText("Input")  # Shorter title
        
        # Use supported methods for styling with smaller font for x-axis to reduce space
        self.axis_x.setTitleBrush(QColor(255, 255, 255))
        self.axis_x.setLabelsBrush(QColor(255, 255, 255))
        self.axis_x.setLabelsFont(QFont("Arial", 7))  # Smaller labels
        self.axis_x.setTitleFont(QFont("Arial", 7))   # Smaller title
        
        self.axis_x.setGridLineVisible(True)
        self.axis_x.setMinorGridLineVisible(True)
        self.axis_x.setLabelsVisible(True)
        self.axis_x.setTickCount(6)
        self.axis_x.setLabelFormat("%.0f%%")
        self.axis_x.setGridLinePen(QPen(QColor(70, 70, 70), 1))
        self.axis_x.setMinorGridLinePen(QPen(QColor(60, 60, 60), 1))
        
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Output")  # Shorter title
        
        # Use supported methods for styling with smaller font for y-axis to match x-axis
        self.axis_y.setTitleBrush(QColor(255, 255, 255))
        self.axis_y.setLabelsBrush(QColor(255, 255, 255))
        self.axis_y.setLabelsFont(QFont("Arial", 7))  # Smaller labels to match x-axis
        self.axis_y.setTitleFont(QFont("Arial", 7))   # Smaller title to match x-axis
        # Remove unsupported methods
        # self.axis_y.setLabelsPadding(10)
        # self.axis_y.setTitleMargin(15)
        
        self.axis_y.setGridLineVisible(True)
        self.axis_y.setMinorGridLineVisible(True)
        self.axis_y.setLabelsVisible(True)
        self.axis_y.setTickCount(6)
        self.axis_y.setLabelFormat("%.0f%%")
        self.axis_y.setGridLinePen(QPen(QColor(70, 70, 70), 1))
        self.axis_y.setMinorGridLinePen(QPen(QColor(60, 60, 60), 1))
        
        # Create a SINGLE path-based series for the curve that includes the indicator
        # This is key to ensuring the dot stays on the line
        self.curve_series = QLineSeries()
        self.curve_series.setPen(QPen(QColor(0, 120, 255), 3))
        self.curve_series.setUseOpenGL(False)  # Disable OpenGL for better performance with frequent updates
        self.chart.addSeries(self.curve_series)
        
        # Create a separate series for the draggable control points
        self.control_points_series = QScatterSeries()
        self.control_points_series.setMarkerSize(12)
        self.control_points_series.setColor(QColor(255, 0, 0))
        self.control_points_series.setBorderColor(QColor(255, 255, 255))
        self.control_points_series.setUseOpenGL(False)  # Keep disabled for interaction
        self.chart.addSeries(self.control_points_series)
        
        # Create series for deadzone visualization
        self.min_deadzone_series = QAreaSeries()
        self.min_deadzone_pen = QPen(QColor(230, 100, 0, 150))
        self.min_deadzone_pen.setWidth(1)
        self.min_deadzone_series.setPen(self.min_deadzone_pen)
        self.min_deadzone_series.setBrush(QBrush(QColor(230, 100, 0, 80)))
        self.min_deadzone_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        self.chart.addSeries(self.min_deadzone_series)
        
        self.max_deadzone_series = QAreaSeries()
        self.max_deadzone_pen = QPen(QColor(230, 100, 0, 150))
        self.max_deadzone_pen.setWidth(1)
        self.max_deadzone_series.setPen(self.max_deadzone_pen)
        self.max_deadzone_series.setBrush(QBrush(QColor(230, 100, 0, 80)))
        self.max_deadzone_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        self.chart.addSeries(self.max_deadzone_series)
        
        # Create a separate series for the indicator dot that will be precisely positioned
        self.indicator_series = QScatterSeries()
        self.indicator_series.setMarkerSize(10)
        self.indicator_series.setColor(QColor(0, 255, 0))
        self.indicator_series.setBorderColor(QColor(255, 255, 255))
        self.indicator_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        self.chart.addSeries(self.indicator_series)
        
        # Attach axes
        self.chart.setAxisX(self.axis_x, self.curve_series)
        self.chart.setAxisY(self.axis_y, self.curve_series)
        self.chart.setAxisX(self.axis_x, self.control_points_series)
        self.chart.setAxisY(self.axis_y, self.control_points_series)
        self.chart.setAxisX(self.axis_x, self.indicator_series)
        self.chart.setAxisY(self.axis_y, self.indicator_series)
        
        # Attach axes to deadzone series
        self.chart.setAxisX(self.axis_x, self.min_deadzone_series)
        self.chart.setAxisY(self.axis_y, self.min_deadzone_series)
        self.chart.setAxisX(self.axis_x, self.max_deadzone_series)
        self.chart.setAxisY(self.axis_y, self.max_deadzone_series)
        
        # Create the chart view
        self.chart_view = DraggableChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setViewportUpdateMode(QChartView.MinimalViewportUpdate)
        self.chart_view.set_scatter_series(self.control_points_series, self.curve_series)
        self.chart_view.point_moved.connect(self.on_control_point_moved)
        
        # Set minimum height significantly larger to ensure space for axes
        self.chart_view.setMinimumHeight(320)  # Increased from 280 to 320 for larger chart
        # Set vertical size policy to ensure it takes the space
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Let it expand/shrink
        self.chart_view.setContentsMargins(5, 0, 5, 0)  # Minimize vertical margins
        
        # Add some bottom margin to the chart itself - REDUCED
        self.chart.setMargins(QMargins(10, 5, 10, 5))  # Reduce top and bottom margins
        
        # Debounce for control point updates
        self.point_move_timer = QTimer()
        self.point_move_timer.setSingleShot(True)
        self.point_move_timer.timeout.connect(self._delayed_control_point_moved)
        self.pending_update = False
        
        # Add to layout
        parent_layout.addWidget(self.chart_view)
        
        # Initialize with default points
        self.reset_to_linear()
    
    def reset_to_linear(self):
        """Reset to a linear calibration curve."""
        self.points = [
            QPointF(0, 0),      # Bottom left
            QPointF(33, 33),    # Lower middle
            QPointF(67, 67),    # Upper middle
            QPointF(100, 100)   # Top right
        ]
        self.update_chart()
    
    def set_points(self, points):
        """Set calibration points."""
        # Handle both tuples and QPointF objects
        new_points = []
        for point in points:
            if isinstance(point, QPointF):
                new_points.append(point)
            else:
                # Assume it's a tuple or sequence with x, y values
                x, y = point
                new_points.append(QPointF(x, y))
        
        self.points = new_points
        
        # Adjust points for deadzones
        self.update_chart()
    
    def get_points(self):
        """Get calibration points."""
        # Convert QPointF objects back to tuples
        return [(point.x(), point.y()) for point in self.points]
    
    def update_input_position(self, input_percentage):
        """
        Update the current input position and calculate the exact 
        corresponding output position on the curve.
        """
        # Store the input percentage immediately for calculations
        self.input_percentage = max(0, min(100, input_percentage))
        
        # Only update visual indicator with throttling
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        if current_time - self.last_update_time < self.update_interval:
            if not self.update_scheduled:
                # Schedule a single update after the throttle period
                QTimer.singleShot(self.update_interval, self.update_indicator)
                self.update_scheduled = True
            return  # Skip immediate visual update if not enough time has passed
            
        self.last_update_time = current_time
        self.update_scheduled = False
        self.update_indicator()
    
    def update_indicator(self):
        """Update the position of the green indicator dot to be exactly on the curve."""
        # Ensure we have valid points
        if len(self.points) < 2:
            return
        
        # Sort points by x-value for proper interpolation
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Adjust the display position based on deadzones
        display_x = self.input_percentage
        
        # If input is below min deadzone, position dot at the start of the curve
        if self.input_percentage <= self.min_deadzone:
            display_x = self.min_deadzone
            output_percentage = 0
        # If input is above max deadzone, position dot at the end of the curve
        elif self.input_percentage >= (100 - self.max_deadzone):
            display_x = 100 - self.max_deadzone
            output_percentage = 100
        else:
            # For inputs between deadzones, calculate proper position
            if self.min_deadzone > 0 or self.max_deadzone > 0:
                # Calculate the scaled x-position for the dot
                usable_range = 100.0 - self.min_deadzone - self.max_deadzone
                if usable_range > 0:  # Prevent division by zero
                    # Scale the input to the range between deadzones
                    display_x = self.min_deadzone + (self.input_percentage - self.min_deadzone)
            
            # Find the output percentage for the adjusted input
            output_percentage = self.calculate_output_for_input(display_x, sorted_points)
        
        # Update the indicator dot position
        self.indicator_series.clear()
        self.indicator_series.append(display_x, output_percentage)
    
    def calculate_output_for_input(self, input_percentage, sorted_points=None):
        """Calculate the precise output percentage for a given input percentage."""
        if sorted_points is None:
            sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Apply min deadzone - return 0 for any input below the min deadzone
        if input_percentage <= self.min_deadzone:
            return 0.0
        
        # Apply max deadzone
        if input_percentage >= (100 - self.max_deadzone):
            return 100.0
            
        # If between deadzones, rescale the input to use the full range
        if self.min_deadzone > 0 or self.max_deadzone > 0:
            usable_range = 100.0 - self.min_deadzone - self.max_deadzone
            if usable_range > 0:  # Prevent division by zero
                scaled_input = ((input_percentage - self.min_deadzone) / usable_range) * 100.0
                input_percentage = max(0.0, min(100.0, scaled_input))
        
        # Handle edge cases
        if not sorted_points:
            return input_percentage
        
        if input_percentage <= sorted_points[0].x():
            return sorted_points[0].y()
        
        if input_percentage >= sorted_points[-1].x():
            return sorted_points[-1].y()
        
        # Find the segment containing our input percentage
        for i in range(len(sorted_points) - 1):
            if sorted_points[i].x() <= input_percentage <= sorted_points[i + 1].x():
                # Get the segment points
                p1 = sorted_points[i]
                p2 = sorted_points[i + 1]
                
                # Handle vertical segments
                if p1.x() == p2.x():
                    return p1.y()
                
                # Use precise linear interpolation to find the output
                t = (input_percentage - p1.x()) / (p2.x() - p1.x())
                return p1.y() + t * (p2.y() - p1.y())
        
        # Fallback - should not reach here with the edge case handling
        return input_percentage
    
    def update_chart(self):
        """Update the chart with current calibration points and deadzones."""
        # This is a complete redraw - it should be called much less frequently than update_indicator
        
        # Set updating flag to avoid re-entrancy
        if hasattr(self, '_updating_chart') and self._updating_chart:
            return
            
        self._updating_chart = True
        
        # Clear series
        self.curve_series.clear()
        self.control_points_series.clear()
        
        # Sort points by x for proper curve drawing
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Ensure the curve is drawn properly with deadzones
        if self.min_deadzone > 0:
            # Add a point at the min deadzone boundary (0% output)
            # Find the original first point
            if sorted_points:
                # Add a point exactly at the deadzone boundary
                deadzone_point = QPointF(self.min_deadzone, 0)
                
                # If first point is to the left of deadzone, replace it
                if sorted_points[0].x() < self.min_deadzone:
                    for i, point in enumerate(sorted_points):
                        if point.x() >= self.min_deadzone:
                            # Keep existing points that are outside the deadzone
                            sorted_points = sorted_points[i:]
                            break
                    else:
                        # All points are inside the deadzone
                        sorted_points = []
                    
                    # Add the new deadzone boundary point at the start
                    sorted_points.insert(0, deadzone_point)
                elif not sorted_points or sorted_points[0].x() > self.min_deadzone:
                    # If no points or first point is beyond deadzone, add point at deadzone
                    sorted_points.insert(0, deadzone_point)
        
        # Handle max deadzone similarly
        if self.max_deadzone > 0:
            max_boundary = 100 - self.max_deadzone
            # Add a point at the max deadzone boundary (100% output)
            if sorted_points:
                # Add a point exactly at the max deadzone boundary
                deadzone_point = QPointF(max_boundary, 100)
                
                # If last point is to the right of max deadzone, replace it
                if sorted_points[-1].x() > max_boundary:
                    for i in range(len(sorted_points) - 1, -1, -1):
                        if sorted_points[i].x() <= max_boundary:
                            # Keep existing points that are outside the max deadzone
                            sorted_points = sorted_points[:i+1]
                            break
                    else:
                        # All points are inside the max deadzone
                        sorted_points = []
                    
                    # Add the new deadzone boundary point at the end
                    sorted_points.append(deadzone_point)
                elif not sorted_points or sorted_points[-1].x() < max_boundary:
                    # If no points or last point is before max deadzone, add point at max deadzone
                    sorted_points.append(deadzone_point)
        
        # Add sorted points to both series
        for point in sorted_points:
            self.curve_series.append(point)
            self.control_points_series.append(point)
        
        # Update deadzone visualization
        self._update_deadzone_visualization()
        
        # Update the indicator position
        self.update_indicator()
        
        # Clear the updating flag
        self._updating_chart = False
    
    def _update_deadzone_visualization(self):
        """Update the visualization of min and max deadzones."""
        # Clear existing points in the series (instead of creating new series)
        self.min_deadzone_lower_series.clear()
        self.min_deadzone_upper_series.clear()
        self.max_deadzone_lower_series.clear()
        self.max_deadzone_upper_series.clear()
        
        # Visualize min deadzone if it's greater than 0
        if self.min_deadzone > 0:
            # Create vertical area from 0 to 100% output at min_deadzone
            self.min_deadzone_lower_series.append(0, 0)
            self.min_deadzone_lower_series.append(self.min_deadzone, 0)
            
            self.min_deadzone_upper_series.append(0, 100)
            self.min_deadzone_upper_series.append(self.min_deadzone, 100)
            
            self.min_deadzone_series.setLowerSeries(self.min_deadzone_lower_series)
            self.min_deadzone_series.setUpperSeries(self.min_deadzone_upper_series)
        else:
            # No min deadzone to display
            self.min_deadzone_series.setLowerSeries(None)
            self.min_deadzone_series.setUpperSeries(None)
        
        # Visualize max deadzone if it's greater than 0
        if self.max_deadzone > 0:
            # Create vertical area from 0 to 100% output at (100 - max_deadzone)
            self.max_deadzone_lower_series.append(100 - self.max_deadzone, 0)
            self.max_deadzone_lower_series.append(100, 0)
            
            self.max_deadzone_upper_series.append(100 - self.max_deadzone, 100)
            self.max_deadzone_upper_series.append(100, 100)
            
            self.max_deadzone_series.setLowerSeries(self.max_deadzone_lower_series)
            self.max_deadzone_series.setUpperSeries(self.max_deadzone_upper_series)
        else:
            # No max deadzone to display
            self.max_deadzone_series.setLowerSeries(None)
            self.max_deadzone_series.setUpperSeries(None)
    
    def on_control_point_moved(self):
        """Handle when a control point is moved by the user."""
        # Get updated points from the control points series
        updated_points = []
        for i in range(self.control_points_series.count()):
            point = self.control_points_series.at(i)
            updated_points.append(QPointF(point))
        
        # Update our internal points list
        self.points = updated_points
        
        # Update the curve without modifying the control points - this ensures visual feedback is smooth
        self._update_curve_without_control_points()
        
        # Debounce the callback
        if not self.point_move_timer.isActive():
            self.point_move_timer.start(300)  # 300ms debounce for notifying parent
    
    def _delayed_control_point_moved(self):
        """Called after debounce period for control point movement."""
        if self.on_curve_changed:
            self.on_curve_changed()
    
    def _update_curve_without_control_points(self):
        """Update the curve line without changing the control points."""
        # Clear curve series for redraw
        self.curve_series.clear()
        
        # Sort points by x for proper curve drawing
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Add sorted points to curve series
        for point in sorted_points:
            self.curve_series.append(point)
        
        # Update deadzone visualization
        self._update_deadzone_visualization()
        
        # Update the indicator to ensure it stays on the curve
        self.update_indicator()
    
    def get_output_value(self, scale=65535):
        """
        Get the current output value as an integer scaled to the given range.
        Default scale is 0-65535 (16-bit).
        """
        if len(self.points) < 2:
            # Use linear mapping if no valid curve
            output_percentage = self.input_percentage
        else:
            # Calculate output based on the curve
            output_percentage = self.calculate_output_for_input(self.input_percentage)
            
        # Scale to the desired range and return as integer
        return int((output_percentage / 100) * scale)
    
    def set_deadzones(self, min_deadzone, max_deadzone):
        """Set the deadzone values and update the chart."""
        self.min_deadzone = min_deadzone
        self.max_deadzone = max_deadzone
        self.update_chart()

class PasswordDialog(QDialog):
    """Dialog to request password before accessing protected features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add message label
        message_label = QLabel("Please enter the password to access Race Coach:")
        layout.addWidget(message_label)
        
        # Add password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_password(self):
        """Get the entered password."""
        return self.password_input.text()

from .auth import LoginDialog, SignupDialog
from .database import supabase, user_manager

class MainWindow(QMainWindow):
    """Main application window."""
    
    # Signals
    calibration_updated = pyqtSignal(str)  # Emits pedal name when calibration changes
    auth_state_changed = pyqtSignal(bool)  # Emits when authentication state changes
    
    def __init__(self, oauth_handler=None):
        """Initialize the main window."""
        super().__init__()
        # Main window setup
        self.window_width = 1200
        self.window_height = 900  # Increased from 800 to 900
        self.setWindowTitle("TrackPro Configuration v1.4.6")
        self.setMinimumSize(1000, 875)  # Increased minimum height from 700 to 800
        self.setWindowIcon(QIcon(":/icons/app_icon.ico"))

        # Store the shared OAuth handler
        self.oauth_handler = oauth_handler

        # Attributes for calibration data
        self.pedal_data = {}
        
        # Set dark theme
        self.setup_dark_theme()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add authentication controls at the top
        auth_layout = QHBoxLayout()
        
        # Add user info label
        self.user_label = QLabel("Not logged in")
        self.user_label.setStyleSheet("color: #888;")
        auth_layout.addWidget(self.user_label)
        
        # Add cloud sync label
        self.cloud_sync_label = QLabel("☁️ Sign in to enable cloud sync")
        self.cloud_sync_label.setStyleSheet("color: #3498db; cursor: pointer;")
        auth_layout.addWidget(self.cloud_sync_label)
        
        # Add login/signup buttons
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        
        self.signup_btn = QPushButton("Sign Up")
        self.signup_btn.clicked.connect(self.show_signup_dialog)
        self.signup_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #37be70;
            }
        """)
        
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.handle_logout)
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0493b;
            }
        """)
        self.logout_btn.hide()
        
        auth_layout.addStretch()
        auth_layout.addWidget(self.login_btn)
        auth_layout.addWidget(self.signup_btn)
        auth_layout.addWidget(self.logout_btn)
        
        layout.addLayout(auth_layout)
        
        # Add calibration wizard button
        wizard_layout = QHBoxLayout()
        self.calibration_wizard_btn = QPushButton("Calibration Wizard")
        self.calibration_wizard_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
        """)
        self.calibration_wizard_btn.clicked.connect(self.open_calibration_wizard)
        
        # Add save calibration button
        self.save_calibration_btn = QPushButton("Save Calibration")
        self.save_calibration_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5DBF61;
            }
        """)
        self.save_calibration_btn.clicked.connect(self.save_calibration)
        
        # Add buttons to the layout
        wizard_layout.addWidget(self.calibration_wizard_btn)
        wizard_layout.addWidget(self.save_calibration_btn)
        wizard_layout.addStretch()
        layout.addLayout(wizard_layout)
        
        # Create a stacked widget for switching between screens
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create the main pedals screen
        pedals_screen = QWidget()
        pedals_layout = QVBoxLayout(pedals_screen)
        
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
        layout.addWidget(self.update_notification, 0, Qt.AlignLeft)
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Add version information to status bar
        version_label = QLabel(f"Version: {__version__}")
        self.statusBar.addWidget(version_label)

        # IMPORTANT: Update authentication state on startup to restore session
        # Use a longer delay to make sure all components are properly initialized
        logger.info("Scheduling authentication state update after initialization")
        QTimer.singleShot(500, self.update_auth_state)
    
    def _init_pedal_data(self):
        """Initialize data structures for all pedals."""
        self._pedal_data = {}
        # Initialize pedal groups dictionary to track pedal UI sections
        self.pedal_groups = {}
        
        for pedal in ['throttle', 'brake', 'clutch']:
            self._pedal_data[pedal] = {
                'input_value': 0,
                'output_value': 0,
                'points': [],
                'curve_type': 'Linear',
                'line_series': None,
                'point_series': None,
                'input_progress': None,
                'output_progress': None,
                'input_label': None,
                'output_label': None,
                'position_indicator': None,  # Using the new CurvePositionIndicator
                'min_control': None,
                'max_control': None,
                'min_deadzone': 0,
                'max_deadzone': 0
            }
    
    def setup_dark_theme(self):
        """Set up dark theme colors and styling."""
        # Set up dark palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        # Set stylesheet for custom styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #353535;
            }
            QWidget {
                background-color: #353535;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
                margin-top: 3px;
                margin-bottom: 3px;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 3px 0px 3px;
                top: -2px;
            }
            QPushButton {
                background-color: #444444;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                color: white;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 2px;
                text-align: center;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
            QComboBox {
                background-color: #444444;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 10px;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-width: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #444444;
                selection-background-color: #2a82da;
                min-width: 200px;
                padding: 5px;
            }
            QLabel {
                color: white;
            }
        """)
    
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
        calibration_chart = IntegratedCalibrationChart(
            cal_layout, 
            pedal_name,
            lambda: self.on_point_moved(pedal_key)
        )
        
        # Store the chart in the pedal data
        data['calibration_chart'] = calibration_chart
        
        # Update the calibration chart to have more space at the bottom
        # Use an alternative approach that doesn't require QMargins
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
        
        # Create the combo box for curve selection
        curve_selector = QComboBox()
        curve_selector.addItems(["Linear", "Exponential", "Logarithmic", "S-Curve", "Reverse Log", "Reverse Expo"])
        curve_selector.setCurrentText("Linear")
        
        # Size settings - strictly enforce the height with fixed size policy
        curve_selector.setMinimumWidth(130)  # Reduced from 180 to 130
        curve_selector.setMaximumWidth(140)  # Add maximum width constraint
        curve_selector.setFixedHeight(27)
        curve_selector.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Fixed in both directions
        
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
        
        # Connect signals
        curve_selector.currentTextChanged.connect(lambda text: self.on_curve_selector_changed(pedal_key, text))
        
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
        min_label.setAlignment(Qt.AlignCenter)
        max_label.setAlignment(Qt.AlignCenter)
        reset_label.setAlignment(Qt.AlignCenter)
        curve_label.setAlignment(Qt.AlignCenter)
        
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
        parent_layout.addWidget(cal_group)
        
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
        
        # Curve Selector
        selector_label = QLabel("Saved Curves:")
        manager_layout.addWidget(selector_label, 1, 0)
        
        # *** FIX: Create QComboBox with explicit parent ***
        curve_list = QComboBox(manager_group)
        curve_list.setMinimumWidth(130)  # Reduced width
        curve_list.setMaximumWidth(140)  # Add maximum width
        curve_list.setFixedHeight(27)
        curve_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # Fixed in both directions
        # *** FIX: Simplify stylesheet to remove potential issues ***
        curve_list.setStyleSheet("""
            QComboBox {
                background-color: #444444;
                border: 1px solid #555555;
                color: white;
                padding: 0px 5px;  /* Reduced padding */
                height: 27px;
                max-height: 27px;
                min-height: 27px;
                text-align: left;  /* Left align text */
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
        manager_layout.addWidget(curve_list, 1, 1)
        
        # *** FIX: Force some dummy items to verify dropdown works ***
        curve_list.addItem("Loading...")
        
        # Log widget creation
        logger.info(f"[{pedal_key}] Creating saved_curves_selector with ID: {id(curve_list)}")
        
        # Load Button
        load_btn = QPushButton("Load")
        load_btn.setFixedHeight(27)
        load_btn.setStyleSheet("background-color: #2196F3; color: white;")
        load_btn.clicked.connect(lambda: self.load_custom_curve(pedal_key, curve_list.currentText()))
        manager_layout.addWidget(load_btn, 1, 2)
        
        # Delete Button
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedHeight(27)
        delete_btn.setStyleSheet("background-color: #F44336; color: white;")
        delete_btn.clicked.connect(lambda: self.delete_custom_curve(pedal_key, curve_list.currentText()))
        manager_layout.addWidget(delete_btn, 1, 3)
        
        # Store references for curve management
        data['curve_name_input'] = name_input
        data['saved_curves_selector'] = curve_list # Store the reference
        data['saved_curves_selector'].currentTextChanged.connect(
            lambda text: self.on_curve_selector_changed(pedal_key, text)
        )
        
        # Set up the layout
        manager_group.setLayout(manager_layout)
        parent_layout.addWidget(manager_group)
        
        # Store the QGroupBox for the pedal
        data['group_box'] = cal_group
        
        # *** FIX: Make sure all widgets are properly shown ***
        manager_group.show()
        curve_list.show()
    
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
    
    def set_output_value(self, pedal: str, value: int):
        """
        Set the output value for a pedal.
        Only updates the UI elements - no longer used for indicator updates.
        """
        data = self._pedal_data[pedal]
        
        # Just update the UI output display values
        data['output_value'] = value
        data['output_progress'].setValue(value)
        data['output_label'].setText(f"Mapped Output: {value}")
    
    def get_calibration_points(self, pedal: str):
        """Get the calibration points for a pedal."""
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            return data['calibration_chart'].points
        return []
    
    def set_calibration_points(self, pedal: str, points: list):
        """Set the calibration points for a pedal."""
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            data['calibration_chart'].points = points
            data['calibration_chart'].update_chart()
    
    def get_curve_type(self, pedal: str):
        """Get the curve type for a pedal."""
        data = self._pedal_data[pedal]
        return data.get('curve_type', 'Linear')
    
    def set_curve_type(self, pedal: str, curve_type: str):
        """Set the curve type for a pedal."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        if 'curve_type_selector' in data:
            data['curve_type_selector'].setCurrentText(curve_type)
    
    def add_calibration_point(self, pedal: str):
        """Add current input/output values as a calibration point."""
        data = self._pedal_data[pedal]
        point = QPointF(data['input_value'], data['output_value'])
        data['points'].append(point)
        self.update_calibration_curve(pedal)
        self.calibration_updated.emit(pedal)
    
    def clear_calibration_points(self, pedal: str):
        """Clear all calibration points for a pedal."""
        data = self._pedal_data[pedal]
        data['points'].clear()
        self.update_calibration_curve(pedal)
        self.calibration_updated.emit(pedal)
    
    def update_calibration_curve(self, pedal: str):
        """Update the visualization of the calibration curve."""
        data = self._pedal_data[pedal]
        calibration_chart = data['calibration_chart']
        
        # Update the chart with the current points
        calibration_chart.set_points(data['points'])
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def change_response_curve(self, pedal: str, curve_type: str):
        """Change the response curve type for a pedal."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        calibration_chart = data['calibration_chart']
        
        # Generate new points based on the curve type
        if curve_type in ["Linear", "Exponential", "Logarithmic", "S-Curve", "Reverse Log", "Reverse Expo"]:
            new_points = []
            
            if curve_type == "Linear":
                # Linear curve: y = x
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = x  # Linear mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Exponential":
                # Exponential curve: y = x^2
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = (x / 100) ** 2 * 100  # x^2 mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Logarithmic":
                # Logarithmic curve: y = sqrt(x)
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = math.sqrt(x / 100) * 100  # sqrt(x) mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "S-Curve":
                # S-Curve: combination of exponential and logarithmic
                # Using a sigmoid function: y = 1 / (1 + e^(-k*(x-50)))
                k = 0.1  # Controls the steepness of the curve
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    # Sigmoid function scaled to 0-100 range
                    y = 100 / (1 + math.exp(-k * (x - 50)))
                    new_points.append(QPointF(x, y))
            
            # Add logic for Reverse Log curve
            elif curve_type == "Reverse Log":
                # Reverse Logarithmic curve: y = (1 - sqrt(1 - x/100)) * 100
                for i in range(5):
                    x = i * 25
                    if x == 100: # Avoid math domain error for sqrt(0) if x is exactly 100
                        y = 100.0 
                    elif x == 0: # Handle x=0 explicitly
                        y = 0.0
                    else:
                        y = (1 - math.sqrt(1 - x / 100)) * 100
                    new_points.append(QPointF(x, y))

            # Add logic for Reverse Expo curve
            elif curve_type == "Reverse Expo":
                # Reverse Exponential curve: y = (1 - (1 - x/100)^2) * 100
                for i in range(5):
                    x = i * 25
                    y = (1 - (1 - x / 100) ** 2) * 100
                    new_points.append(QPointF(x, y))

            # Update the chart with the new points
            calibration_chart.set_points(new_points)
            
            # Update stored points
            data['points'] = new_points.copy()
        else:
            # This is a preset curve, load it from hardware
            try:
                if hasattr(self, 'hardware') and self.hardware:
                    curve_data = self.hardware.load_custom_curve(pedal, curve_type)
                    if curve_data and 'points' in curve_data:
                        # Convert points to QPointF objects
                        new_points = [QPointF(x, y) for x, y in curve_data['points']]
                        
                        # Update the chart with the loaded points
                        calibration_chart.set_points(new_points)
                        
                        # Update stored points
                        data['points'] = new_points.copy()
                    else:
                        logger.warning(f"Could not load curve data for {curve_type}")
                        self.show_message("Error", f"Could not load curve data for '{curve_type}'")
                else:
                    logger.warning("Hardware not initialized, cannot load curve")
                    self.show_message("Error", "Hardware not initialized, cannot load curve")
            except Exception as e:
                logger.error(f"Error loading curve {curve_type}: {e}")
                self.show_message("Error", f"Failed to load curve: {e}")
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
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
    
    def show_message(self, title: str, message: str):
        """Show a message box with the given title and message."""
        QMessageBox.information(self, title, message)
    
    def set_current_as_min(self, pedal: str):
        """Set the current input value as the minimum for calibration."""
        data = self._pedal_data[pedal]
        current_value = data['input_value']
        
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
        current_value = data['input_value']
        
        # Don't allow max to be lower than min
        if current_value <= data['min_value']:
            self.show_message("Calibration Error", "Maximum value must be greater than minimum value")
            return
            
        # Update the calibration max value but don't change the raw input display
        data['max_value'] = current_value
        data['max_label'].setText(f"Max: {current_value}")
        
        # Emit signal to update calibration
        self.calibration_updated.emit(pedal)
    
    def get_calibration_range(self, pedal: str) -> tuple:
        """Get the min/max calibration range for a pedal."""
        data = self._pedal_data[pedal]
        return (data['min_value'], data['max_value'])
    
    def set_calibration_range(self, pedal: str, min_val: int, max_val: int):
        """Set the min/max calibration range for a pedal."""
        data = self._pedal_data[pedal]
        data['min_value'] = min_val
        data['max_value'] = max_val
        data['min_label'].setText(f"Min: {min_val}")
        data['max_label'].setText(f"Max: {max_val}")
        
        # Reset deadzone values when changing min/max
        data['min_deadzone'] = 0
        data['max_deadzone'] = 0
        data['min_deadzone_value'].setText("0%")
        data['max_deadzone_value'].setText("0%")
        
        # Update hardware deadzone
        if hasattr(self, 'hardware') and pedal in self.hardware.axis_ranges:
            self.hardware.axis_ranges[pedal]['min_deadzone'] = 0
            self.hardware.axis_ranges[pedal]['max_deadzone'] = 0
        
        # Update chart visualization
        if 'calibration_chart' in data:
            data['calibration_chart'].set_deadzones(0, 0)
            
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
            
            # Update hardware deadzone
            if hasattr(self, 'hardware') and pedal in self.hardware.axis_ranges:
                self.hardware.axis_ranges[pedal]['min_deadzone'] = new_min_deadzone
                self.hardware.save_axis_ranges()
            
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
            
            # Update hardware deadzone
            if hasattr(self, 'hardware') and pedal in self.hardware.axis_ranges:
                self.hardware.axis_ranges[pedal]['max_deadzone'] = new_max_deadzone
                self.hardware.save_axis_ranges()
            
            # Signal that calibration has been updated
            self.calibration_updated.emit(pedal)
    
    def on_calibration_load(self):
        """Handle loading of calibration data."""
        if hasattr(self, 'hardware'):
            # For each pedal, load calibration data
            for pedal_key in ['throttle', 'brake', 'clutch']:
                pedal_data = self._pedal_data[pedal_key]
                if pedal_key in self.hardware.axis_ranges:
                    axis_range = self.hardware.axis_ranges[pedal_key]
                    # Load min/max values
                    min_val = axis_range.get('min', 0)
                    max_val = axis_range.get('max', 65535)
                    
                    # Update UI
                    pedal_data['min_value'] = min_val
                    pedal_data['max_value'] = max_val
                    pedal_data['min_label'].setText(f"Min: {min_val}")
                    pedal_data['max_label'].setText(f"Max: {max_val}")
                    
                    # Load deadzone values if they exist
                    min_deadzone = axis_range.get('min_deadzone', 0)
                    max_deadzone = axis_range.get('max_deadzone', 0)
                    
                    # Update UI for deadzones
                    pedal_data['min_deadzone'] = min_deadzone
                    pedal_data['max_deadzone'] = max_deadzone
                    pedal_data['min_deadzone_value'].setText(f"{min_deadzone}%")
                    pedal_data['max_deadzone_value'].setText(f"{max_deadzone}%")
                    
                    # Update chart visualization with deadzones
                    if 'calibration_chart' in pedal_data:
                        pedal_data['calibration_chart'].set_deadzones(min_deadzone, max_deadzone)
                    
                # Also load calibration curve points
                if pedal_key in self.hardware.calibration:
                    points = self.hardware.calibration[pedal_key].get('points', [])
                    curve_type = self.hardware.calibration[pedal_key].get('curve', 'Linear')
                    
                    # Update curve type selection
                    curve_selector = pedal_data['curve_type_selector']
                    for i in range(curve_selector.count()):
                        if curve_selector.itemText(i) == curve_type:
                            curve_selector.setCurrentIndex(i)
                            break
                    
                    # Update calibration points
                    chart = pedal_data['calibration_chart']
                    chart.set_points(points)
        
        # Reflect the loaded calibration in the monitor display
        self.update_monitor_display()

    def create_menu_bar(self):
        """Create the main menu bar."""
        menu_bar = self.menuBar()
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        # Add Supabase configuration submenu
        supabase_menu = file_menu.addMenu("Supabase Configuration")
        
        # Add enable/disable action
        self.supabase_enabled_action = QAction("Enable Cloud Sync", self)
        self.supabase_enabled_action.setCheckable(True)
        self.supabase_enabled_action.setChecked(config.supabase_enabled)
        self.supabase_enabled_action.triggered.connect(self.toggle_supabase)
        supabase_menu.addAction(self.supabase_enabled_action)
        
        # Add configure action
        configure_supabase_action = QAction("Configure Credentials...", self)
        configure_supabase_action.triggered.connect(self.configure_supabase)
        supabase_menu.addAction(configure_supabase_action)
        
        file_menu.addSeparator()
        
        # Add authentication-related actions
        self.login_action = file_menu.addAction("Login")
        self.login_action.triggered.connect(self.show_login_dialog)
        self.login_action.setEnabled(config.supabase_enabled)
        
        self.signup_action = file_menu.addAction("Sign Up")
        self.signup_action.triggered.connect(self.show_signup_dialog)
        self.signup_action.setEnabled(config.supabase_enabled)
        
        self.logout_action = file_menu.addAction("Logout")
        self.logout_action.triggered.connect(self.handle_logout)
        self.logout_action.setVisible(False)

        # Add Refresh Login State option
        self.refresh_login_action = file_menu.addAction("Refresh Login State")
        self.refresh_login_action.triggered.connect(self.force_refresh_login_state)
        
        file_menu.addSeparator()
        
        # Add Pedal Profiles menu
        pedal_profiles_menu = file_menu.addMenu("Pedal Profiles")
        
        # Manage profiles action
        manage_profiles_action = QAction("Manage Profiles...", self)
        manage_profiles_action.triggered.connect(self.show_profile_manager)
        pedal_profiles_menu.addAction(manage_profiles_action)
        
        # Save current profile action
        save_profile_action = QAction("Save Current Settings as Profile...", self)
        save_profile_action.triggered.connect(self.save_current_profile)
        pedal_profiles_menu.addAction(save_profile_action)
        
        file_menu.addSeparator()
        
        # Add Check for Updates option
        update_action = QAction("Check for Updates", self)
        update_action.triggered.connect(self.check_for_updates)
        file_menu.addAction(update_action)
        
        # Add separator
        file_menu.addSeparator()
        
        # Add Exit option
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Add Pedal Config button to menu bar
        self.pedal_config_action = QAction("Pedal Config", self)
        self.pedal_config_action.triggered.connect(self.open_pedal_config)
        self.pedal_config_action.setCheckable(True)
        self.pedal_config_action.setChecked(True)  # Default active section
        menu_bar.addAction(self.pedal_config_action)
        
        # Add Race Coach button to menu bar
        self.race_coach_action = QAction("Race Coach", self)
        self.race_coach_action.triggered.connect(self.open_race_coach)
        self.race_coach_action.setCheckable(True)
        self.race_coach_action.setChecked(False)
        self.race_coach_action.setToolTip("Login required to access Race Coach features")
        menu_bar.addAction(self.race_coach_action)
        
        # Style the menu bar for dark theme
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #353535;
                color: #ffffff;
            }
            QMenuBar::item {
                background-color: #353535;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #2a82da;
            }
            QMenu {
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #2a82da;
            }
            QAction:checked {
                background-color: #2a82da;
                font-weight: bold;
            }
        """)

        # --- Add Race Pass menu item ---
        self.race_pass_action = QAction("&Race Pass", self)
        self.race_pass_action.setStatusTip("View your Race Pass progress")
        self.race_pass_action.triggered.connect(self.show_race_pass_dialog)
        file_menu.addAction(self.race_pass_action)
        # ------------------------------

        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # Add a new method to force refresh the login state
    def force_refresh_login_state(self):
        """Force a refresh of the authentication state."""
        logger.info("Manually refreshing authentication state")
        
        # Restore session from file first to ensure we have the latest data
        if hasattr(supabase, '_restore_session'):
            supabase._restore_session()
            
        # Force processEvents to update the UI
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Update the authentication state
        self.update_auth_state()
        
        # Force processEvents again to ensure UI updates
        QApplication.processEvents()
        
        # Get the current user for a message
        user = supabase.get_user()
        if user and ((hasattr(user, 'user') and user.user) or hasattr(user, 'email')):
            user_email = None
            if hasattr(user, 'email'):
                user_email = user.email
            elif hasattr(user, 'user') and hasattr(user.user, 'email'):
                user_email = user.user.email
                
            QMessageBox.information(
                self,
                "Authentication Refreshed",
                f"You are logged in as {user_email or 'User'}." 
            )
        else:
            QMessageBox.information(
                self,
                "Authentication Refreshed",
                "You are not currently logged in."
            )
    
    def check_for_updates(self):
        """Manually check for updates."""
        logger.info("Manual update check requested")
        
        # Show a message that we're checking for updates
        QMessageBox.information(
            self,
            "Checking for Updates",
            "TrackPro is checking for updates. You will be notified when the check is complete."
        )
        
        if hasattr(self, 'updater'):
            logger.info("Using existing updater instance")
            self.updater.check_for_updates(silent=False, manual_check=True)
        else:
            logger.info("Creating new updater instance")
            from .updater import Updater
            updater = Updater(self)
            updater.check_for_updates(silent=False, manual_check=True)
            self.updater = updater
            logger.info("Updater instance created and stored")

    def show_update_notification(self, version):
        """Show a notification that an update is available."""
        logger.info(f"Showing update notification for version: {version}")
        self.update_notification.setText(f"Update Available: v{version} - Click File > Check for Updates")
        self.update_notification.setVisible(True)
        
    def hide_update_notification(self):
        """Hide the update notification."""
        logger.info("Hiding update notification")
        self.update_notification.setVisible(False)
        
    def open_pedal_config(self):
        """Switch to pedal configuration screen."""
        # Find pedals screen index
        pedals_screen_index = 0  # Default to first screen which should be pedals
        
        self.stacked_widget.setCurrentIndex(pedals_screen_index)
        
        # Update menu action states
        self.pedal_config_action.setChecked(True)
        if hasattr(self, 'race_coach_action'):
            self.race_coach_action.setChecked(False)
            
        # Show calibration buttons
        self.calibration_wizard_btn.setVisible(True)
        self.save_calibration_btn.setVisible(True)
        
        logger.info("Switched to pedal configuration screen")
    
    def open_calibration_wizard(self):
        """Open the calibration wizard dialog."""
        logger.info("Opening Calibration Wizard")
        try:
            # Create an instance of the CalibrationWizard
            # Pass the hardware input instance required by the wizard's constructor
            wizard = CalibrationWizard(self.hardware, parent=self)
            
            # Connect signal to handle when wizard is completed
            wizard.calibration_complete.connect(self.on_calibration_wizard_completed)
            
            # Show the wizard dialog - it's modal so it will block until closed
            result = wizard.exec_()
            
            # Handle the result
            if result == QDialog.Accepted:
                logger.info("Calibration wizard completed successfully")
                # Refresh the UI with the new calibration
                self.refresh_curve_lists()
            else:
                logger.info("Calibration wizard cancelled")
        except Exception as e:
            logger.error(f"Error opening calibration wizard: {e}")
            self.show_message("Error", f"Could not open calibration wizard: {str(e)}")
        
        # Refresh UI if needed (e.g., if wizard modified things)
        # self.refresh_curve_lists() # Removed redundant call

    def save_calibration(self):
        """Save the current calibration settings."""
        logger.info("Saving calibration data manually")
        try:
            if hasattr(self, 'hardware') and self.hardware:
                # Trigger save in hardware module
                self.hardware.save_calibration(self.hardware.calibration)
                self.show_message("Calibration Saved", "Calibration settings saved successfully.")
                logger.info("Calibration saved manually by user")
            else:
                logger.warning("Cannot save calibration - hardware not available")
                self.show_message("Error", "Hardware not available to save calibration.")
        except Exception as e:
            logger.error(f"Error saving calibration: {e}")
            self.show_message("Error", f"Could not save calibration: {str(e)}")
        # Refresh curve lists after saving calibration - Removed redundant call
        # self.refresh_curve_lists()

    def reset_calibration(self, pedal: str):
        """Reset calibration for a specific pedal."""
        logger.info(f"Resetting calibration for pedal: {pedal}")
        try:
            # Reset the calibration points to a linear curve
            if pedal in self._pedal_data and 'calibration_chart' in self._pedal_data[pedal]:
                # Reset the calibration chart to linear
                self._pedal_data[pedal]['calibration_chart'].reset_to_linear()
                
                # Reset deadzones to 0%
                self._pedal_data[pedal]['calibration_chart'].set_deadzones(0, 0)
                self._pedal_data[pedal]['min_deadzone'] = 0
                self._pedal_data[pedal]['max_deadzone'] = 0
                
                # Update deadzone UI labels
                if 'min_deadzone_value' in self._pedal_data[pedal]:
                    self._pedal_data[pedal]['min_deadzone_value'].setText("0%")
                if 'max_deadzone_value' in self._pedal_data[pedal]:
                    self._pedal_data[pedal]['max_deadzone_value'].setText("0%")
                
                # Update hardware deadzones if hardware is available
                if hasattr(self, 'hardware') and self.hardware and pedal in self.hardware.axis_ranges:
                    self.hardware.axis_ranges[pedal]['min_deadzone'] = 0
                    self.hardware.axis_ranges[pedal]['max_deadzone'] = 0
                    self.hardware.save_axis_ranges()
                
                self.refresh_curve_lists()
                self.on_point_moved(pedal)
                
                # Update the UI
                QMessageBox.information(
                    self,
                    "Calibration Reset",
                    f"Calibration for {pedal} has been reset to linear response with 0% deadzones."
                )
                logger.info(f"Calibration for {pedal} reset successfully with deadzones set to 0%")
            else:
                logger.warning(f"Cannot reset calibration: pedal {pedal} not found")
        except Exception as e:
            logger.error(f"Failed to reset calibration for {pedal}: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to reset calibration for {pedal}: {str(e)}"
            )

    def set_pedal_available(self, pedal: str, available: bool):
        """Set whether a pedal is available (connected).
        Since we've removed all UI indicators, this now only handles enabling/disabling pedal controls.
        """
        # We're simplifying the connection logic, so this function is now a no-op
        pass
    
    def open_race_coach(self):
        """Open the Race Coach screen with password protection."""
        # First check if user is authenticated
        if not supabase.is_authenticated():
            # Create a custom message box with login button
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Login Required")
            msg_box.setText("You need to be logged in to access the Race Coach feature.")
            msg_box.setIcon(QMessageBox.Information)
            
            # Add a button to open login dialog
            login_button = msg_box.addButton("Login Now", QMessageBox.ActionRole)
            cancel_button = msg_box.addButton(QMessageBox.Cancel)
            
            msg_box.exec_()
            
            # Check which button was clicked
            if msg_box.clickedButton() == login_button:
                self.show_login_dialog()
            
            logger.info("Race Coach access attempted without login")
            return
        
        try:
            # Initialize gamification overview since we're logged in
            self.initialize_gamification_overview()
            
            # Show password dialog
            password_dialog = PasswordDialog(self)
            result = password_dialog.exec_()
            
            # Check if dialog was accepted and password is correct
            if result == QDialog.Accepted:
                entered_password = password_dialog.get_password()
                # Replace 'trackpro' with your desired password
                correct_password = 'lt'
                
                if entered_password != correct_password:
                    QMessageBox.warning(self, "Access Denied", 
                                     "Incorrect password. Access to Race Coach denied.")
                    logger.warning("Race Coach access denied - incorrect password entered")
                    return
            else:
                # User cancelled the dialog
                logger.info("Race Coach access cancelled by user")
                return
            
            # Try to import and initialize the Race Coach module
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
                    # Hide calibration buttons
                    self.calibration_wizard_btn.setVisible(False)
                    self.save_calibration_btn.setVisible(False)
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
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                self.save_calibration_btn.setVisible(False)
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
    
    def add_debug_button(self, callback):
        """Add a debug button to the window."""
        # Create a button at the bottom of the window
        debug_btn = QPushButton("Debug Information")
        debug_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                font-size: 12px;
                padding: 3px 8px;
                margin: 3px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        debug_btn.clicked.connect(callback)
        
        # Add to the main layout at the bottom
        self.centralWidget().layout().addWidget(debug_btn)

    def set_hardware(self, hardware):
        """Set the hardware interface for the application."""
        self.hardware = hardware
        
        # Initialize UI with hardware state if available
        if hardware:
            for pedal in ['throttle', 'brake', 'clutch']:
                if pedal in hardware.axis_ranges:
                    # Update UI with hardware values
                    if hasattr(self, '_pedal_data') and pedal in self._pedal_data:
                        # Set min/max values
                        min_val = hardware.axis_ranges[pedal].get('min', 0)
                        max_val = hardware.axis_ranges[pedal].get('max', 65535)
                        self._pedal_data[pedal]['min_value'] = min_val
                        self._pedal_data[pedal]['max_value'] = max_val
                        
                        # Set deadzone values
                        min_deadzone = hardware.axis_ranges[pedal].get('min_deadzone', 0)
                        max_deadzone = hardware.axis_ranges[pedal].get('max_deadzone', 0)
                        if 'min_deadzone' in self._pedal_data[pedal]:
                            self._pedal_data[pedal]['min_deadzone'] = min_deadzone
                        if 'max_deadzone' in self._pedal_data[pedal]:
                            self._pedal_data[pedal]['max_deadzone'] = max_deadzone
                        
                        # Update calibration chart
                        if 'calibration_chart' in self._pedal_data[pedal]:
                            self._pedal_data[pedal]['calibration_chart'].set_deadzones(min_deadzone, max_deadzone)
            
            # Refresh the curve lists to show available custom curves
            try:
                # Wait until hardware is fully initialized and curves are created
                QTimer.singleShot(500, self.refresh_curve_lists)
            except Exception as e:
                logger.error(f"Error scheduling curve list refresh: {e}")
    
    def on_curve_selector_changed(self, pedal: str, curve_name: str):
        """Handle when the user selects a curve from a dropdown list."""
        if not curve_name:
            return
            
        # Check if this is a programmatic change (during list population)
        if hasattr(self, '_is_populating_curves') and self._is_populating_curves:
            return
            
        logger.info(f"Curve selection changed for {pedal}: {curve_name}")
        
        # Determine which selector triggered this change
        data = self._pedal_data[pedal]
        
        # Update the curve type in our data
        self.set_curve_type(pedal, curve_name)
        
        # Apply the curve change using the change_response_curve method
        self.change_response_curve(pedal, curve_name)
        
        # Make sure both selectors are in sync
        if 'curve_type_selector' in data and data['curve_type_selector'].currentText() != curve_name:
            # Check if the curve exists in the dropdown
            if data['curve_type_selector'].findText(curve_name) == -1:
                data['curve_type_selector'].addItem(curve_name)
            data['curve_type_selector'].setCurrentText(curve_name)
            
        if 'saved_curves_selector' in data and data['saved_curves_selector'].currentText() != curve_name:
            # Only update saved curves selector for custom curves
            if curve_name not in ["Linear", "Exponential", "Logarithmic", "S-Curve", "Reverse Log", "Reverse Expo"]:
                if data['saved_curves_selector'].findText(curve_name) == -1:
                    data['saved_curves_selector'].addItem(curve_name)
                data['saved_curves_selector'].setCurrentText(curve_name)
    
    def load_custom_curve(self, pedal: str, curve_name: str):
        """Load a custom curve from the saved curves."""
        if not curve_name:
            return
            
        logger.info(f"Loading curve '{curve_name}' for {pedal}")
        
        try:
            if hasattr(self, 'hardware') and self.hardware:
                # Load the curve from the hardware
                curve_data = self.hardware.load_custom_curve(pedal, curve_name)
                
                if curve_data and 'points' in curve_data:
                    # Convert points to QPointF objects
                    points = [QPointF(x, y) for x, y in curve_data['points']]
                    
                    # Update the chart with the loaded points
                    data = self._pedal_data[pedal]
                    data['calibration_chart'].set_points(points)
                    
                    # Update stored points
                    data['points'] = points.copy()
                    
                    # Update curve type
                    data['curve_type'] = curve_name
                    
                    # Update both curve selectors to match
                    if 'curve_type_selector' in data:
                        # First make sure the curve exists in the dropdown
                        if data['curve_type_selector'].findText(curve_name) == -1:
                            data['curve_type_selector'].addItem(curve_name)
                        data['curve_type_selector'].setCurrentText(curve_name)
                    
                    if 'saved_curves_selector' in data:
                        # Also update the saved curves dropdown
                        if data['saved_curves_selector'].findText(curve_name) == -1:
                            data['saved_curves_selector'].addItem(curve_name)
                        data['saved_curves_selector'].setCurrentText(curve_name)
                    
                    # Signal that calibration has changed
                    self.calibration_updated.emit(pedal)
                    
                    # Show success message
                    self.show_message("Curve Loaded", f"Successfully loaded curve '{curve_name}' for {pedal}")
                else:
                    logger.warning(f"Could not load curve data for {curve_name}")
                    self.show_message("Error", f"Could not load curve data for '{curve_name}'")
            else:
                logger.warning("Hardware not initialized, cannot load curve")
                self.show_message("Error", "Hardware not initialized, cannot load curve")
        except Exception as e:
            logger.error(f"Error loading curve {curve_name}: {e}")
            self.show_message("Error", f"Failed to load curve: {e}")
    
    def delete_custom_curve(self, pedal: str, curve_name: str):
        """Delete a custom curve from the saved curves."""
        if not curve_name or curve_name in ["Linear", "Exponential", "Logarithmic", "S-Curve", "Reverse Log", "Reverse Expo"]:
            logger.warning(f"Cannot delete built-in curve type: {curve_name}")
            self.show_message("Error", "Cannot delete built-in curve types")
            return
            
        logger.info(f"Deleting curve '{curve_name}' for {pedal}")
        
        try:
            if hasattr(self, 'hardware') and self.hardware:
                # Confirm deletion with the user
                confirm = QMessageBox.question(
                    self,
                    "Confirm Deletion",
                    f"Are you sure you want to delete the curve '{curve_name}' for {pedal}?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if confirm == QMessageBox.Yes:
                    # Delete the curve using the hardware
                    success = self.hardware.delete_custom_curve(pedal, curve_name)
                    
                    if success:
                        # Refresh the curve list
                        self.refresh_curve_lists()
                        
                        # Show success message
                        self.show_message("Curve Deleted", f"Successfully deleted curve '{curve_name}' for {pedal}")
                    else:
                        logger.warning(f"Failed to delete curve {curve_name}")
                        self.show_message("Error", f"Failed to delete curve '{curve_name}'")
            else:
                logger.warning("Hardware not initialized, cannot delete curve")
                self.show_message("Error", "Hardware not initialized, cannot delete curve")
        except Exception as e:
            logger.error(f"Error deleting curve {curve_name}: {e}")
            self.show_message("Error", f"Failed to delete curve: {e}")
    
    def save_custom_curve(self, pedal: str, name: str):
        """Save the current curve configuration as a custom curve."""
        if not name:
            self.show_message("Error", "Please enter a name for the curve")
            return
            
        logger.info(f"Saving curve '{name}' for {pedal}")
        
        try:
            if hasattr(self, 'hardware') and self.hardware:
                data = self._pedal_data[pedal]
                
                # Get the points from the calibration chart
                points = data['calibration_chart'].get_points()
                
                # Convert QPointF objects to tuples for JSON serialization
                point_tuples = [(int(p.x()), int(p.y())) for p in points]
                
                # Save the curve using the hardware
                success = self.hardware.save_custom_curve(
                    pedal=pedal,
                    name=name,
                    points=point_tuples,
                    curve_type=name
                )
                
                if success:
                    # Update curve type
                    data['curve_type'] = name
                    
                    # Refresh the curve list
                    self.refresh_curve_lists()
                    
                    # Clear the name input
                    data['curve_name_input'].clear()
                    
                    # Show success message
                    self.show_message("Curve Saved", f"Successfully saved curve '{name}' for {pedal}")
                else:
                    logger.warning(f"Failed to save curve {name}")
                    self.show_message("Error", f"Failed to save curve '{name}'")
            else:
                logger.warning("Hardware not initialized, cannot save curve")
                self.show_message("Error", "Hardware not initialized, cannot save curve")
        except Exception as e:
            logger.error(f"Error saving curve {name}: {e}")
            self.show_message("Error", f"Failed to save curve: {e}") 

    def update_pedal_connection_status(self, connected: bool):
        """This method is kept as a no-op for compatibility with existing code."""
        # Simplified to do nothing since we're not showing connection status anymore
        pass

    def add_force_connected_button(self, callback):
        """Removed - this is a no-op stub for compatibility."""
        pass
    
    def update_force_connected_button(self, is_forced):
        """Removed - this is a no-op stub for compatibility."""
        pass

    def _on_tab_changed(self, index):
        """Handle tab change events."""
        # Update menu action states based on the current tab
        if index == 0:  # Pedal Config tab
            self.pedal_config_action.setChecked(True)
            self.race_coach_action.setChecked(False)
            self.calibration_wizard_btn.setVisible(True)
            self.save_calibration_btn.setVisible(True)
            
            # Send a hide event to Race Coach widget if it exists
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
                        
        elif index == 1:  # Race Coach tab
            self.pedal_config_action.setChecked(False)
            self.race_coach_action.setChecked(True)
            self.calibration_wizard_btn.setVisible(False)
            self.save_calibration_btn.setVisible(False)
            
            # Send a show event to the Race Coach widget
            widget = self.stacked_widget.widget(index)
            if hasattr(widget, 'showEvent'):
                try:
                    # Create a show event
                    show_event = QShowEvent()
                    # Call the widget's showEvent method
                    widget.showEvent(show_event)
                except Exception as e:
                    logger.error(f"Error sending show event to widget: {e}")
                
            # Initialize gamification overview if not already done
            self.initialize_gamification_overview()

    def initialize_gamification_overview(self):
        """Initialize the gamification overview widget if it doesn't exist already."""
        if not hasattr(self, 'gamification_overview') or not self.gamification_overview:
            logger.info("Initializing gamification overview widget")
            try:
                # Create the gamification overview widget
                self.gamification_overview = GamificationOverviewWidget(self)
                
                # If we already have quest view, connect it to the overview
                if hasattr(self, 'quest_view_widget') and self.quest_view_widget:
                    logger.info("Connecting existing quest view to gamification overview")
                    self.quest_view_widget.quest_claimed.connect(self.gamification_overview.on_quest_claimed)
                    
                # Store it in our reference store to prevent garbage collection
                if hasattr(self, 'store_reference'):
                    self.store_reference(self.gamification_overview)
                    
                logger.info("Gamification overview initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing gamification overview: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.gamification_overview = None

    def show_login_dialog(self):
        """Show the login dialog."""
        # Pass the stored oauth_handler to the dialog
        dialog = LoginDialog(self, oauth_handler=self.oauth_handler)
        if dialog.exec_() == QDialog.Accepted:
            self.update_auth_state()
    
    def show_signup_dialog(self):
        """Show the signup dialog."""
        # Pass the stored oauth_handler to the dialog
        dialog = SignupDialog(self, oauth_handler=self.oauth_handler)
        if dialog.exec_() == QDialog.Accepted:
            self.update_auth_state()
    
    def handle_logout(self):
        """Handle user logout."""
        try:
            # Force clear the session when explicitly logging out via the UI
            # This ensures that even with "Remember Me" checked, an explicit logout clears the session
            supabase.sign_out(force_clear=True)
            self.update_auth_state()
            QMessageBox.information(self, "Success", "Logged out successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to logout: {str(e)}")
            logger.error(f"Logout error: {e}")
    
    def update_auth_state(self):
        """Update the UI based on authentication state."""
        is_authenticated = supabase.is_authenticated()
        
        logger.info(f"Updating authentication state - User is authenticated: {is_authenticated}")
        
        # Update user label
        if is_authenticated:
            user = supabase.get_user()
            if user:
                try:
                    # Get user metadata through user_manager which now has better handling
                    metadata = user_manager.get_user_metadata(user)
                    user_email = None
                    
                    # Try to get email from different response structures
                    if hasattr(user, 'email'):
                        user_email = user.email
                    elif hasattr(user, 'user') and hasattr(user.user, 'email'):
                        user_email = user.user.email
                        
                    display_name = metadata.get('display_name', user_email or 'User')
                    self.user_label.setText(f"Logged in as: {display_name}")
                    self.user_label.setStyleSheet("color: #2ecc71;")
                    logger.info(f"Updated UI to show user: {display_name}")
                except Exception as e:
                    logger.error(f"Error updating user label: {e}")
                    self.user_label.setText("Logged in")
                    self.user_label.setStyleSheet("color: #2ecc71;")
        else:
            self.user_label.setText("Not logged in | Click to sign in")
            self.user_label.setStyleSheet("color: #3498db; text-decoration: underline; cursor: pointer;")
            # Make the label clickable to open login dialog
            self.user_label.mousePressEvent = lambda e: self.show_login_dialog()
            logger.info("Updated UI to show not logged in state")
        
        # Update button visibility
        self.login_btn.setVisible(not is_authenticated)
        self.signup_btn.setVisible(not is_authenticated)
        self.logout_btn.setVisible(is_authenticated)
        
        # Update menu actions
        self.login_action.setVisible(not is_authenticated)
        self.signup_action.setVisible(not is_authenticated)
        self.logout_action.setVisible(is_authenticated)
        
        # Update cloud sync status in menu if the label exists
        if hasattr(self, 'cloud_sync_label'):
            if is_authenticated:
                self.cloud_sync_label.setText("🔄 Cloud Sync Enabled")
                self.cloud_sync_label.setStyleSheet("color: #2ecc71;")
            else:
                self.cloud_sync_label.setText("☁️ Sign in to enable cloud sync")
                self.cloud_sync_label.setStyleSheet("color: #3498db; cursor: pointer;")
                # Make the label clickable to open login dialog
                self.cloud_sync_label.mousePressEvent = lambda e: self.show_login_dialog()
        
        # Emit auth state changed signal
        self.auth_state_changed.emit(is_authenticated)
        
        # Update protected features
        self.update_protected_features(is_authenticated)
    
    def update_protected_features(self, is_authenticated: bool):
        """Enable/disable features based on authentication state."""
        # Example: Enable/disable Race Coach tab or specific actions
        
        # Make Race Coach menu item checkable only when authenticated
        if hasattr(self, 'race_coach_action'):
            self.race_coach_action.setEnabled(True)  # Always enable to show login message
            if is_authenticated:
                self.race_coach_action.setToolTip("Access Race Coach features")
            else:
                self.race_coach_action.setToolTip("Login required to access Race Coach features")
                self.race_coach_action.setChecked(False)
                # Switch back to pedal config if Race Coach was active
                if self.stacked_widget.currentWidget() is not None and \
                   isinstance(self.stacked_widget.currentWidget(), RaceCoachWidget):
                    self.open_pedal_config()
        
        # Trigger initial load for RaceCoachWidget if authenticated and widget exists
        if is_authenticated:
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if isinstance(widget, RaceCoachWidget):
                    logger.info("Authentication ready, triggering RaceCoachWidget initial load.")
                    widget.perform_initial_load()
                    break # Assuming only one instance

    def toggle_supabase(self, enabled: bool):
        """Toggle Supabase integration on/off."""
        if enabled:
            # Show configuration dialog if credentials not set
            if not config.supabase_url or not config.supabase_key:
                self.configure_supabase()
                # Check if user cancelled or didn't set credentials
                if not config.supabase_url or not config.supabase_key:
                    self.supabase_enabled_action.setChecked(False)
                    return
            
            # Try to enable Supabase
            if supabase.enable():
                self.login_action.setEnabled(True)
                self.signup_action.setEnabled(True)
                QMessageBox.information(self, "Success", "Cloud sync enabled")
            else:
                self.supabase_enabled_action.setChecked(False)
                QMessageBox.warning(
                    self, 
                    "Error",
                    "Could not enable cloud sync. Please check your credentials."
                )
        else:
            # Confirm with user if they're logged in
            if supabase.is_authenticated():
                confirm = QMessageBox.question(
                    self,
                    "Confirm Disable",
                    "Disabling cloud sync will log you out. Continue?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    self.supabase_enabled_action.setChecked(True)
                    return
            
            # Disable Supabase
            supabase.disable()
            self.login_action.setEnabled(False)
            self.signup_action.setEnabled(False)
            self.update_auth_state()
            QMessageBox.information(self, "Success", "Cloud sync disabled")
    
    def configure_supabase(self):
        """Configure Supabase credentials."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Supabase")
        layout = QVBoxLayout(dialog)
        
        # URL input
        url_label = QLabel("Supabase URL:")
        url_input = QLineEdit()
        url_input.setText(config.supabase_url)
        layout.addWidget(url_label)
        layout.addWidget(url_input)
        
        # Key input
        key_label = QLabel("Supabase Key:")
        key_input = QLineEdit()
        key_input.setText(config.supabase_key)
        layout.addWidget(key_label)
        layout.addWidget(key_input)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            # Save new credentials
            config.set('supabase.url', url_input.text())
            config.set('supabase.key', key_input.text())
            
            # If Supabase is enabled, try to reconnect
            if config.supabase_enabled:
                if not supabase.enable():
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Could not connect with new credentials. Please check them and try again."
                    )
                    # Disable Supabase if connection failed
                    self.supabase_enabled_action.setChecked(False)
                    supabase.disable()
                else:
                    QMessageBox.information(
                        self,
                        "Success",
                        "Successfully connected with new credentials!"
                    )
    
    def show_profile_manager(self):
        """Show the pedal profile manager dialog."""
        try:
            # Check if profile_dialog module is imported
            try:
                from .pedals.profile_dialog import PedalProfileDialog
            except ImportError:
                # Fallback to absolute import
                from trackpro.pedals.profile_dialog import PedalProfileDialog
            
            # Get current calibration data
            calibration_data = {}
            for pedal in ['throttle', 'brake', 'clutch']:
                pedal_data = {}
                
                # Get curve type
                if hasattr(self, 'get_curve_type'):
                    pedal_data['curve'] = self.get_curve_type(pedal)
                
                # Get calibration points
                if hasattr(self, 'get_calibration_points'):
                    points = self.get_calibration_points(pedal)
                    # Convert QPointF to tuples
                    pedal_data['points'] = [(p.x(), p.y()) for p in points]
                
                # Get calibration range
                if hasattr(self, 'get_calibration_range'):
                    min_val, max_val = self.get_calibration_range(pedal)
                    pedal_data['min'] = min_val
                    pedal_data['max'] = max_val
                
                # Add to collection
                calibration_data[pedal] = pedal_data
            
            # Create and show the dialog
            dialog = PedalProfileDialog(self, calibration_data)
            
            # Connect the profile_selected signal
            dialog.profile_selected.connect(self.apply_profile)
            
            # Show the dialog
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing profile manager: {e}")
            self.show_message("Error", f"Could not open profile manager: {str(e)}")
    
    def save_current_profile(self):
        """Save current settings as a profile."""
        # This is a shortcut to open profile manager with current settings
        self.show_profile_manager()
    
    def apply_profile(self, profile):
        """Apply a selected pedal profile.
        
        Args:
            profile: The profile data dictionary
        """
        try:
            # Convert JSON strings to dictionaries if needed
            throttle_calibration = profile.get('throttle_calibration', {})
            brake_calibration = profile.get('brake_calibration', {})
            clutch_calibration = profile.get('clutch_calibration', {})
            
            # Apply to each pedal
            for pedal, data in [
                ('throttle', throttle_calibration),
                ('brake', brake_calibration),
                ('clutch', clutch_calibration)
            ]:
                if not data:
                    logger.warning(f"No calibration data for {pedal} in profile")
                    continue
                
                # Apply curve type
                if 'curve' in data and hasattr(self, 'set_curve_type'):
                    self.set_curve_type(pedal, data['curve'])
                
                # Apply calibration points
                if 'points' in data and hasattr(self, 'set_calibration_points'):
                    # Convert tuples to QPointF
                    points = [QPointF(x, y) for x, y in data['points']]
                    self.set_calibration_points(pedal, points)
                
                # Apply calibration range
                if 'min' in data and 'max' in data and hasattr(self, 'set_calibration_range'):
                    self.set_calibration_range(pedal, data['min'], data['max'])
                
                # Emit calibration updated signal
                if hasattr(self, 'calibration_updated'):
                    self.calibration_updated.emit(pedal)
            
            # Show confirmation
            profile_name = profile.get('name', 'Selected profile')
            self.show_message("Profile Applied", f"{profile_name} has been applied to your pedals.")
            
        except Exception as e:
            logger.error(f"Error applying profile: {e}")
            self.show_message("Error", f"Could not apply profile: {str(e)}")

    def on_calibration_wizard_completed(self, results):
        """Handle the results when the calibration wizard finishes."""
        logger.info(f"Calibration wizard completed with results: {results}")
        if not results:
            logger.warning("Calibration wizard returned no results.")
            return
            
        try:
            # Update the hardware object with the new calibration data
            if hasattr(self, 'hardware') and self.hardware:
                for pedal, data in results.items():
                    if pedal in self.hardware.axis_ranges:
                        logger.info(f"Updating {pedal} calibration: Axis={data.get('axis', -1)}, Min={data.get('min')}, Max={data.get('max')}")
                        self.hardware.axis_ranges[pedal]['min'] = data.get('min', 0)
                        self.hardware.axis_ranges[pedal]['max'] = data.get('max', 65535)
                        if data.get('axis', -1) != -1:
                            self.hardware.update_axis_mapping(pedal, data['axis'])
                    else:
                        logger.warning(f"Pedal {pedal} not found in hardware axis ranges during wizard completion handling.")
                
                # Optionally, re-save the configuration (though wizard might have already done it)
                # self.hardware.save_axis_ranges()
                # self.hardware.save_calibration() 

                # Refresh relevant UI elements
                logger.info("Refreshing UI after calibration.")
                self.refresh_curve_lists()
                for pedal in results.keys():
                    if pedal in self._pedal_data:
                        # Update min/max labels in UI
                        min_val = self.hardware.axis_ranges[pedal].get('min', 0)
                        max_val = self.hardware.axis_ranges[pedal].get('max', 65535)
                        self._pedal_data[pedal]['min_value_label'].setText(f"Min: {min_val}")
                        self._pedal_data[pedal]['max_value_label'].setText(f"Max: {max_val}")
                        # Trigger chart update if needed
                        self.on_point_moved(pedal)
            else:
                logger.error("Hardware object not available to apply calibration results.")

            QMessageBox.information(self, "Calibration Applied", "Pedal calibration settings have been applied.")
            
        except Exception as e:
            logger.error(f"Error applying calibration wizard results: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply calibration results: {str(e)}")

        # Refresh UI after applying results - Removed redundant call
        # self.refresh_curve_lists()

    def refresh_curve_lists(self):
        """Refresh the curve lists for all pedals."""
        if not hasattr(self, 'hardware') or not self.hardware:
            logger.warning("Cannot refresh curve lists - hardware not initialized")
            return
            
        try:
            # Set a flag to prevent triggering callbacks during list population
            self._is_populating_curves = True
            
            # Refresh curve lists for each pedal
            for pedal in ['throttle', 'brake', 'clutch']:
                if pedal in self._pedal_data:
                    data = self._pedal_data[pedal]
                    
                    # Get available curves from hardware
                    curves = self.hardware.list_available_curves(pedal)
                    logger.info(f"Found {len(curves)} curves for {pedal}: {curves}")
                    
                    # Update the saved curves dropdown if it exists
                    if 'saved_curves_selector' in data and data['saved_curves_selector']:
                        selector = data['saved_curves_selector']
                        
                        # Add Log for Widget Access ID
                        logger.info(f"[{pedal}] Accessing saved_curves_selector with ID: {id(selector)}")
                        
                        # Verify the widget is alive and visible
                        logger.info(f"[{pedal}] Selector isVisible: {selector.isVisible()}, isEnabled: {selector.isEnabled()}")
                        
                        current_text = selector.currentText()
                        selector.clear()
                        
                        # Add some dummy items if no curves
                        if not curves:
                            selector.addItem("No curves found")
                        
                        # Add actual curves
                        for curve in sorted(curves):
                            selector.addItem(curve)
                        
                        logger.info(f"[{pedal}] saved_curves_selector item count after adding: {selector.count()}")
                        
                        # Restore selection if possible
                        if current_text and current_text in curves:
                            selector.setCurrentText(current_text)
                        elif curves:
                            selector.setCurrentText(sorted(curves)[0])
                        else:
                            selector.setCurrentIndex(-1)
                            
                        # Force UI Update
                        selector.update()
                        selector.repaint()
                        selector.show()
                    
                    # *** FIX: Also update the curve_type_selector to include custom curves ***
                    if 'curve_type_selector' in data and data['curve_type_selector']:
                        # Get the main curve type selector
                        curve_selector = data['curve_type_selector']
                        
                        # Log access
                        logger.info(f"[{pedal}] Accessing curve_type_selector with ID: {id(curve_selector)}")
                        logger.info(f"[{pedal}] curve_type_selector isVisible: {curve_selector.isVisible()}, isEnabled: {curve_selector.isEnabled()}")
                        
                        # Save current selection
                        current_type = curve_selector.currentText()
                        
                        # Block signals to prevent unwanted callbacks
                        curve_selector.blockSignals(True)
                        
                        # Remember the built-in types
                        built_in_types = ["Linear", "Exponential", "Logarithmic", "S-Curve", "Reverse Log", "Reverse Expo"]
                        
                        # Clear and add built-in types 
                        curve_selector.clear()
                        curve_selector.addItems(built_in_types)
                        
                        # Add custom curves to the curve_type_selector
                        for curve in sorted(curves):
                            # Only add if not a built-in type
                            if curve not in built_in_types:
                                curve_selector.addItem(curve)
                        
                        # Log item count
                        logger.info(f"[{pedal}] curve_type_selector item count after adding: {curve_selector.count()}")
                        
                        # Restore selection if possible
                        if current_type and (current_type in built_in_types or current_type in curves):
                            curve_selector.setCurrentText(current_type)
                        else:
                            # Default to Linear if previous selection is not available
                            curve_selector.setCurrentText("Linear")
                        
                        # Unblock signals
                        curve_selector.blockSignals(False)
                        
                        # Force UI update
                        curve_selector.update()
                        curve_selector.repaint()
                        curve_selector.show()
            
            # Clear the flag after populating
            self._is_populating_curves = False
            logger.info("Curve lists refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing curve lists: {e}")
            self._is_populating_curves = False

    def show_race_pass_dialog(self):
        """Shows the Race Pass as a tab in the main window."""
        print("MainWindow: Switching to Race Pass view")
        try:
            # First check if user is authenticated
            if not supabase.is_authenticated():
                # Create a custom message box with login button
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Login Required")
                msg_box.setText("You need to be logged in to access the Race Pass feature.")
                msg_box.setIcon(QMessageBox.Information)
                
                # Add a button to open login dialog
                login_button = msg_box.addButton("Login Now", QMessageBox.ActionRole)
                cancel_button = msg_box.addButton(QMessageBox.Cancel)
                
                msg_box.exec_()
                
                # Check which button was clicked
                if msg_box.clickedButton() == login_button:
                    self.show_login_dialog()
                
                logger.info("Race Pass access attempted without login")
                return
            
            # Check if Race Pass widget already exists in stacked widget
            race_pass_index = -1
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if hasattr(widget, 'objectName') and widget.objectName() == "RacePassViewWidget":
                    race_pass_index = i
                    break
            
            if race_pass_index >= 0:
                logger.info(f"Race Pass screen already exists at index {race_pass_index}, switching to it")
                self.stacked_widget.setCurrentIndex(race_pass_index)
                # Update menu action states
                if hasattr(self, 'race_coach_action'):
                    self.race_coach_action.setChecked(False)
                if hasattr(self, 'pedal_config_action'):
                    self.pedal_config_action.setChecked(False)
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                self.save_calibration_btn.setVisible(False)
                return
            
            # Create and add the Race Pass widget if it doesn't exist
            from trackpro.gamification.ui.race_pass_view import RacePassViewWidget
            race_pass_widget = RacePassViewWidget(self)
            race_pass_widget.setObjectName("RacePassViewWidget")
                
            # Add to stacked widget and switch to it
            race_pass_index = self.stacked_widget.addWidget(race_pass_widget)
            # Switch to the Race Pass screen
            self.stacked_widget.setCurrentIndex(race_pass_index)
            # Update menu action states
            if hasattr(self, 'race_coach_action'):
                self.race_coach_action.setChecked(False)
            if hasattr(self, 'pedal_config_action'):
                self.pedal_config_action.setChecked(False)
                
            # Hide calibration buttons
            self.calibration_wizard_btn.setVisible(False)
            self.save_calibration_btn.setVisible(False)
            logger.info(f"Race Pass screen added at index {race_pass_index} and switched to")
            
        except Exception as e:
            logger.error(f"Error initializing Race Pass view: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Could not open Race Pass view: {str(e)}")
            
            # Fallback to dialog approach if we can't add a tab
            logger.info("Falling back to dialog approach for Race Pass")
            if not hasattr(self, 'race_pass_window_instance') or not self.race_pass_window_instance.isVisible():
                from trackpro.gamification.ui.race_pass_view import RacePassViewWidget
                self.race_pass_window_instance = RacePassViewWidget(self) # Parent to MainWindow
                self.race_pass_window_instance.setWindowTitle("TrackPro Race Pass")
                self.race_pass_window_instance.setGeometry(self.geometry().center().x() - 350, 
                                                    self.geometry().center().y() - 400, 
                                                    700, 800) # Center on main window
                self.race_pass_window_instance.show()
            else:
                self.race_pass_window_instance.activateWindow()

    def show_quest_dialog(self):
        """Show the quest view in the main window as a tab rather than a dialog."""
        print("MainWindow: Switching to Quests view")
        try:
            # First check if user is authenticated
            if not supabase.is_authenticated():
                # Create a custom message box with login button
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Login Required")
                msg_box.setText("You need to be logged in to access the Quests feature.")
                msg_box.setIcon(QMessageBox.Information)
                
                # Add a button to open login dialog
                login_button = msg_box.addButton("Login Now", QMessageBox.ActionRole)
                cancel_button = msg_box.addButton(QMessageBox.Cancel)
                
                msg_box.exec_()
                
                # Check which button was clicked
                if msg_box.clickedButton() == login_button:
                    self.show_login_dialog()
                
                logger.info("Quests access attempted without login")
                return
            
            # Check if Quests widget already exists in stacked widget
            quests_index = -1
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if hasattr(widget, 'objectName') and widget.objectName() == "QuestViewWidget":
                    quests_index = i
                    break
            
            if quests_index >= 0:
                logger.info(f"Quests screen already exists at index {quests_index}, switching to it")
                self.stacked_widget.setCurrentIndex(quests_index)
                # Update menu action states
                if hasattr(self, 'race_coach_action'):
                    self.race_coach_action.setChecked(False)
                if hasattr(self, 'pedal_config_action'):
                    self.pedal_config_action.setChecked(False)
                # Hide calibration buttons
                self.calibration_wizard_btn.setVisible(False)
                self.save_calibration_btn.setVisible(False)
                return
            
            # Create and add the Quests widget if it doesn't exist
            from trackpro.gamification.ui.quest_view import QuestViewWidget
            quests_widget = QuestViewWidget(self)
            quests_widget.setObjectName("QuestViewWidget")
            
            # Connect the quest_claimed signal to the gamification_overview
            if hasattr(self, 'gamification_overview') and self.gamification_overview:
                logger.info("Connecting quest_claimed signal to gamification_overview")
                quests_widget.quest_claimed.connect(self.gamification_overview.on_quest_claimed)
            else:
                logger.warning("No gamification_overview widget found to connect to quest_claimed signal")
                
            # Add to stacked widget and switch to it
            quests_index = self.stacked_widget.addWidget(quests_widget)
            # Switch to the Quests screen
            self.stacked_widget.setCurrentIndex(quests_index)
            # Update menu action states
            if hasattr(self, 'race_coach_action'):
                self.race_coach_action.setChecked(False)
            if hasattr(self, 'pedal_config_action'):
                self.pedal_config_action.setChecked(False)
                
            # Hide calibration buttons
            self.calibration_wizard_btn.setVisible(False)
            self.save_calibration_btn.setVisible(False)
            logger.info(f"Quests screen added at index {quests_index} and switched to")
            
            # Store a reference to prevent garbage collection
            self.quest_view_widget = quests_widget
            
        except Exception as e:
            logger.error(f"Error initializing Quests view: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Could not open Quests view: {str(e)}")
            
            # Fallback to dialog approach if we can't add a tab
            logger.info("Falling back to dialog approach for Quests")
            if not hasattr(self, 'quest_view_window') or not self.quest_view_window.isVisible():
                from trackpro.gamification.ui.quest_view import QuestViewWidget
                self.quest_view_window = QDialog(self)
                self.quest_view_window.setWindowTitle("Quests")
                self.quest_view_window.setMinimumSize(600, 500)
                dialog_layout = QVBoxLayout(self.quest_view_window)
                dialog_layout.setContentsMargins(0, 0, 0, 0)
                
                # Create quest view widget with the dialog as its parent
                quest_view = QuestViewWidget(self.quest_view_window)
                dialog_layout.addWidget(quest_view)
                
                # Connect the claim signals to update XP if needed
                if hasattr(self, 'gamification_overview') and self.gamification_overview:
                    quest_view.quest_claimed.connect(self.gamification_overview.on_quest_claimed)
                
                self.quest_view_widget = quest_view
                self.quest_view_window.show()
            else:
                self.quest_view_window.activateWindow()  # Bring to front if already open