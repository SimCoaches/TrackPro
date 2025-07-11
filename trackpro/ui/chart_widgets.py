"""Chart widgets for TrackPro with enhanced calibration functionality."""

import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QMargins, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QMouseEvent, QWheelEvent, QFont
from .shared_imports import *

class DraggableChartView(QChartView):
    """Custom chart view that supports point dragging."""
    
    point_moved = pyqtSignal()  # Signal emitted when a point is moved
    
    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        try:
            self.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        except AttributeError:
            # Fallback for PyQt6 compatibility
            try:
                self.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            except AttributeError:
                # Skip render hints if not available
                pass
        self.setViewportUpdateMode(QChartView.ViewportUpdateMode.MinimalViewportUpdate)  # Use minimal updates for better performance
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
        if event.button() == Qt.MouseButton.LeftButton and self.scatter_series:
            # Find closest point within 20 pixels
            closest_point = None
            min_distance = float('inf')
            
            for i in range(self.scatter_series.count()):
                point = self.scatter_series.at(i)
                screen_point = self.chart().mapToPosition(point)
                distance = (screen_point - QPointF(event.pos())).manhattanLength()
                
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
            
        value = self.chart().mapToValue(QPointF(pos))
        
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
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_point is not None:
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
        try:
            self.chart.setBackgroundVisible(True)
        except AttributeError:
            # Fallback for PyQt6 compatibility - method may have different name
            pass
        try:
            self.chart.setBackgroundBrush(QColor(53, 53, 53))
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        try:
            self.chart.setPlotAreaBackgroundVisible(True)
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        try:
            self.chart.setPlotAreaBackgroundBrush(QColor(35, 35, 35))
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        try:
            self.chart.setTitleBrush(QColor(255, 255, 255))
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        try:
            self.chart.setAnimationOptions(QChart.AnimationOptions.NoAnimation)  # Disable animations for precise positioning
        except AttributeError:
            # Fallback for PyQt6 compatibility - try without AnimationOptions prefix
            try:
                self.chart.setAnimationOptions(QChart.NoAnimation)
            except AttributeError:
                # Final fallback - skip animation options entirely
                pass
        try:
            self.chart.legend().hide()
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        
        # Adjust chart margins - reduce top and sides, increase bottom substantially
        try:
            self.chart.setContentsMargins(10, 10, 10, 40)  # Restore reasonable margins
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        
        # Create persistent line series for deadzone visualization
        self.min_deadzone_lower_series = QLineSeries()
        self.min_deadzone_upper_series = QLineSeries()
        try:
            self.min_deadzone_lower_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        try:
            self.min_deadzone_upper_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        
        self.max_deadzone_lower_series = QLineSeries()
        self.max_deadzone_upper_series = QLineSeries()
        try:
            self.max_deadzone_lower_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        try:
            self.max_deadzone_upper_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        
        # Create axes with grid
        self.axis_x = QValueAxis()
        try:
            self.axis_x.setRange(0, 100)
        except AttributeError:
            # PyQt6 compatibility - use setMin/setMax instead of setRange
            self.axis_x.setMin(0)
            self.axis_x.setMax(100)
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
        try:
            self.axis_y.setRange(0, 100)
        except AttributeError:
            # PyQt6 compatibility - use setMin/setMax instead of setRange
            self.axis_y.setMin(0)
            self.axis_y.setMax(100)
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
        try:
            self.curve_series.setUseOpenGL(False)  # Disable OpenGL for better performance with frequent updates
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        self.chart.addSeries(self.curve_series)
        
        # Create a separate series for the draggable control points
        self.control_points_series = QScatterSeries()
        self.control_points_series.setMarkerSize(12)
        self.control_points_series.setColor(QColor(255, 0, 0))
        self.control_points_series.setBorderColor(QColor(255, 255, 255))
        try:
            self.control_points_series.setUseOpenGL(False)  # Keep disabled for interaction
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        self.chart.addSeries(self.control_points_series)
        
        # Create series for deadzone visualization
        self.min_deadzone_series = QAreaSeries()
        self.min_deadzone_pen = QPen(QColor(230, 100, 0, 150))
        self.min_deadzone_pen.setWidth(1)
        self.min_deadzone_series.setPen(self.min_deadzone_pen)
        self.min_deadzone_series.setBrush(QBrush(QColor(230, 100, 0, 80)))
        try:
            self.min_deadzone_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        self.chart.addSeries(self.min_deadzone_series)
        
        self.max_deadzone_series = QAreaSeries()
        self.max_deadzone_pen = QPen(QColor(230, 100, 0, 150))
        self.max_deadzone_pen.setWidth(1)
        self.max_deadzone_series.setPen(self.max_deadzone_pen)
        self.max_deadzone_series.setBrush(QBrush(QColor(230, 100, 0, 80)))
        try:
            self.max_deadzone_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        self.chart.addSeries(self.max_deadzone_series)
        
        # Create a separate series for the indicator dot that will be precisely positioned
        self.indicator_series = QScatterSeries()
        self.indicator_series.setMarkerSize(10)
        self.indicator_series.setColor(QColor(0, 255, 0))
        self.indicator_series.setBorderColor(QColor(255, 255, 255))
        try:
            self.indicator_series.setUseOpenGL(False)  # Disable OpenGL for better performance
        except AttributeError:
            pass  # Fallback for PyQt6 compatibility
        self.chart.addSeries(self.indicator_series)
        
        # PyQt6.QtCharts API: Add axes to chart and attach to series
        # Add axes to chart (only once each)
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        
        # Attach axes to all series
        self.curve_series.attachAxis(self.axis_x)
        self.curve_series.attachAxis(self.axis_y)
        self.control_points_series.attachAxis(self.axis_x)
        self.control_points_series.attachAxis(self.axis_y)
        self.indicator_series.attachAxis(self.axis_x)
        self.indicator_series.attachAxis(self.axis_y)
        
        # Attach axes to deadzone series
        self.min_deadzone_series.attachAxis(self.axis_x)
        self.min_deadzone_series.attachAxis(self.axis_y)
        self.max_deadzone_series.attachAxis(self.axis_x)
        self.max_deadzone_series.attachAxis(self.axis_y)
        
        # Create the chart view
        self.chart_view = DraggableChartView(self.chart)
        try:
            self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        except AttributeError:
            try:
                self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            except AttributeError:
                pass  # Skip if not available
        self.chart_view.setViewportUpdateMode(QChartView.ViewportUpdateMode.MinimalViewportUpdate)
        self.chart_view.set_scatter_series(self.control_points_series, self.curve_series)
        self.chart_view.point_moved.connect(self.on_control_point_moved)
        
        # Set minimum height significantly larger to ensure space for axes
        self.chart_view.setMinimumHeight(320)  # Increased from 280 to 320 for larger chart
        # Set vertical size policy to ensure it takes the space
        try:
            self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Let it expand/shrink
        except AttributeError:
            try:
                self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Let it expand/shrink
            except AttributeError:
                pass  # Skip if not available
        self.chart_view.setContentsMargins(5, 0, 5, 0)  # Minimize vertical margins
        
        # Add some bottom margin to the chart itself - REDUCED
        try:
            self.chart.setMargins(QMargins(10, 5, 10, 5))  # Reduce top and bottom margins
        except AttributeError:
            # Fallback for PyQt6 compatibility
            pass
        
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