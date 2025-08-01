"""Chart widgets for TrackPro using pyqtgraph for reliable cross-platform compatibility."""

import time
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QMargins, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QMouseEvent, QWheelEvent, QFont

# Use pyqtgraph for all chart functionality
import pyqtgraph as pg

from .shared_imports import *

class DraggableChartView(QWidget):
    """Custom chart view using pyqtgraph that supports point dragging."""
    
    point_moved = pyqtSignal()  # Signal emitted when a point is moved
    
    def __init__(self, chart=None, parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1a1a')  # Match application dark theme
        self.plot_widget.setLabel('left', 'Output (%)', color='white')
        self.plot_widget.setLabel('bottom', 'Input (%)', color='white')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.getPlotItem().getViewBox().setBackgroundColor('#1a1a1a')
        # Set exact range with no padding/margins
        self.plot_widget.setXRange(0, 100, padding=0)
        self.plot_widget.setYRange(0, 100, padding=0)
        # Disable auto-ranging to maintain exact boundaries
        self.plot_widget.enableAutoRange(False)
        # Set view limits to prevent zooming/panning outside 0-100
        self.plot_widget.setLimits(xMin=0, xMax=100, yMin=0, yMax=100)
        self.plot_widget.setMinimumHeight(240)
        # Remove maximum height restriction to allow vertical expansion
        # self.plot_widget.setMaximumHeight(260)
        
        # Set size policy to allow both horizontal and vertical expansion
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Style the axes to match dark theme
        axis_pen = pg.mkPen(color='#666666', width=1)
        self.plot_widget.getAxis('left').setPen(axis_pen)
        self.plot_widget.getAxis('bottom').setPen(axis_pen)
        self.plot_widget.getAxis('left').setTextPen(pg.mkPen(color='white'))
        self.plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='white'))
        
        # Set explicit tick values to ensure 0 and 100 are always visible
        self.plot_widget.getAxis('left').setTickSpacing(major=25, minor=5)
        self.plot_widget.getAxis('bottom').setTickSpacing(major=25, minor=5)
        # Force the range to show exactly 0-100
        self.plot_widget.getPlotItem().getViewBox().setRange(xRange=[0, 100], yRange=[0, 100], padding=0)
        
        # Disable default mouse interactions (pan/zoom) so we can handle point dragging
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()
        
        # Add to layout
        layout.addWidget(self.plot_widget)
        
        # Dragging state
        self.dragging_point = None
        self.dragging_active = False
        self.control_points = []
        self.curve_line = None
        self.indicator_point = None
        self.deadzone_areas = []
        
        # Create plot items with improved styling for dark theme
        self.curve_line = self.plot_widget.plot([], [], pen=pg.mkPen(color='#00aaff', width=3), name='Calibration Curve')
        self.control_scatter = self.plot_widget.plot([], [], pen=None, symbol='o', symbolSize=15, 
                                                    symbolBrush='#ff4444', symbolPen='#ffffff', name='Control Points')
        self.indicator_scatter = self.plot_widget.plot([], [], pen=None, symbol='o', symbolSize=12,
                                                      symbolBrush='#44ff44', symbolPen='#ffffff', name='Current Position')
        
        # Create deadzone visual indicators  
        self.min_deadzone_item = None
        self.max_deadzone_item = None
        
        # Add 0 and 100 reference markers
        self.zero_marker = None
        self.hundred_marker = None
        self._add_reference_markers()
        
        # Override mouse events directly on the plot widget for better control
        self.plot_widget.mousePressEvent = self.mousePressEvent
        self.plot_widget.mouseMoveEvent = self.mouseMoveEvent
        self.plot_widget.mouseReleaseEvent = self.mouseReleaseEvent
        
        # Store initial points - ensure exact 0,0 to 100,100 boundary
        self.points = [QPointF(0, 0), QPointF(33, 33), QPointF(67, 67), QPointF(100, 100)]
        self.min_deadzone = 0
        self.max_deadzone = 0
        self.input_percentage = 0
        
        self.update_plot()
    
    def _add_reference_markers(self):
        """Add 0 and 100 reference markers to the chart."""
        # Add text labels for 0 and 100
        self.zero_marker = pg.TextItem(text='0', color='white', anchor=(0.5, 0.5))
        self.zero_marker.setPos(0, -5)  # Position below the chart
        self.plot_widget.addItem(self.zero_marker)
        
        self.hundred_marker = pg.TextItem(text='100', color='white', anchor=(0.5, 0.5))
        self.hundred_marker.setPos(100, -5)  # Position below the chart
        self.plot_widget.addItem(self.hundred_marker)
    
    def set_scatter_series(self, series, line_series=None):
        """Compatibility method for QtCharts interface."""
        pass
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert mouse position to plot coordinates
            pos = event.pos()
            # Convert QPoint to QPointF for pyqtgraph compatibility
            scene_pos = self.plot_widget.mapToScene(pos)
            view_pos = self.plot_widget.plotItem.vb.mapSceneToView(scene_pos)
            x, y = view_pos.x(), view_pos.y()
            
            # Find closest control point
            closest_idx = None
            min_distance = float('inf')
            
            for i, point in enumerate(self.points):
                dist = ((point.x() - x) ** 2 + (point.y() - y) ** 2) ** 0.5
                if dist < 8.0 and dist < min_distance:  # 8% tolerance for easier clicking
                    min_distance = dist
                    closest_idx = i
            
            if closest_idx is not None:
                self.dragging_point = closest_idx
                self.dragging_active = True
                event.accept()
                return
        
        # If we didn't start dragging, reset any active dragging
        self.dragging_point = None
        self.dragging_active = False
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.dragging_active and self.dragging_point is not None:
            # Convert mouse position to plot coordinates
            pos = event.pos()
            # Convert QPoint to QPointF for pyqtgraph compatibility
            scene_pos = self.plot_widget.mapToScene(pos)
            view_pos = self.plot_widget.plotItem.vb.mapSceneToView(scene_pos)
            x, y = max(0, min(100, view_pos.x())), max(0, min(100, view_pos.y()))
            
            # Constrain x position based on deadzone boundaries and neighboring points
            usable_start = self.min_deadzone
            usable_end = 100 - self.max_deadzone
            
            if self.dragging_point == 0:
                # First point: X is fixed at usable_start, Y can move freely
                x = usable_start
                # Y can move freely from 0 to 100
                y = max(0, min(100, y))
            elif self.dragging_point == len(self.points) - 1:
                # Last point: X can move from previous point to usable_end, Y can move freely
                min_x = self.points[-2].x() + 1 if len(self.points) > 1 else usable_start
                max_x = usable_end
                x = max(min_x, min(max_x, x))
                # Y can move freely from 0 to 100
                y = max(0, min(100, y))
            else:
                # Middle points constrained by neighbors and usable range
                min_x = max(usable_start, self.points[self.dragging_point - 1].x() + 1)
                max_x = min(usable_end, self.points[self.dragging_point + 1].x() - 1)
                x = max(min_x, min(max_x, x))
                # Y can move freely from 0 to 100
                y = max(0, min(100, y))
            
            # Update point
            self.points[self.dragging_point] = QPointF(x, y)
            self.update_plot()
            self.point_moved.emit()
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_active = False
            self.dragging_point = None
            event.accept()
    

    
    def update_plot(self):
        """Update the plot with current data."""
        # Remove old deadzone items if they exist
        if self.min_deadzone_item is not None:
            self.plot_widget.removeItem(self.min_deadzone_item)
            self.min_deadzone_item = None
        if self.max_deadzone_item is not None:
            self.plot_widget.removeItem(self.max_deadzone_item)
            self.max_deadzone_item = None
        
        # Add deadzone visual indicators
        if self.min_deadzone > 0:
            # Create filled area for min deadzone
            x_fill = [0, self.min_deadzone, self.min_deadzone, 0, 0]
            y_fill = [0, 0, 100, 100, 0]
            self.min_deadzone_item = self.plot_widget.plot(x_fill, y_fill, 
                                                         pen=None, 
                                                         fillLevel=0, 
                                                         brush=pg.mkBrush(255, 100, 100, 60))
        
        if self.max_deadzone > 0:
            # Create filled area for max deadzone
            max_start = 100 - self.max_deadzone
            x_fill = [max_start, 100, 100, max_start, max_start]
            y_fill = [0, 0, 100, 100, 0]
            self.max_deadzone_item = self.plot_widget.plot(x_fill, y_fill, 
                                                         pen=None, 
                                                         fillLevel=0, 
                                                         brush=pg.mkBrush(255, 100, 100, 60))
        
        # Adjust control points to respect deadzone boundaries
        adjusted_points = []
        usable_start = self.min_deadzone
        usable_end = 100 - self.max_deadzone
        usable_range = usable_end - usable_start
        
        if usable_range > 0 and (self.min_deadzone > 0 or self.max_deadzone > 0):
            # Only adjust points when deadzones are active
            for i, point in enumerate(self.points):
                # Map point positions to the usable range
                if i == 0:
                    # First point always at start of usable range
                    adjusted_x = usable_start
                elif i == len(self.points) - 1:
                    # Last point always at end of usable range
                    adjusted_x = usable_end
                else:
                    # Middle points proportionally distributed
                    original_x = point.x()
                    adjusted_x = usable_start + (original_x / 100.0) * usable_range
                
                adjusted_points.append(QPointF(adjusted_x, point.y()))
        else:
            # No deadzones - use original points, ensure first point starts at X=0
            adjusted_points = self.points.copy()
            # Ensure first point is exactly at X=0, but preserve user's Y value
            if len(adjusted_points) > 0:
                adjusted_points[0] = QPointF(0, adjusted_points[0].y())
            # Don't force last point to X=100 - user can set it to limit max output
        
        # Sort points by x-coordinate for proper curve
        sorted_points = sorted(adjusted_points, key=lambda p: p.x())
        
        # Update curve line
        x_data = [p.x() for p in sorted_points]
        y_data = [p.y() for p in sorted_points]
        self.curve_line.setData(x_data, y_data)
        
        # Update control points
        self.control_scatter.setData(x_data, y_data)
        
        # Update indicator if we have valid input
        if hasattr(self, 'input_percentage'):
            display_x = self.input_percentage
            output_y = self.calculate_output_for_input(display_x)
            self.indicator_scatter.setData([display_x], [output_y])
    
    def calculate_output_for_input(self, input_percentage):
        """Calculate output for given input using linear interpolation."""
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        if input_percentage <= self.min_deadzone:
            return 0.0
        if input_percentage >= (100 - self.max_deadzone):
            return 100.0
        
        # Find surrounding points for interpolation
        for i in range(len(sorted_points) - 1):
            p1, p2 = sorted_points[i], sorted_points[i + 1]
            if p1.x() <= input_percentage <= p2.x():
                if p1.x() == p2.x():
                    return p1.y()
                t = (input_percentage - p1.x()) / (p2.x() - p1.x())
                return p1.y() + t * (p2.y() - p1.y())
        
        return input_percentage  # Fallback
    
    def setMinimumHeight(self, height):
        """Set minimum height for the widget."""
        super().setMinimumHeight(height)
        if hasattr(self, 'plot_widget'):
            self.plot_widget.setMinimumHeight(height)
    
    def setSizePolicy(self, horizontal, vertical):
        """Set size policy for the widget."""
        super().setSizePolicy(horizontal, vertical)
    
    # Compatibility methods for QtCharts interface
    def setPlotAreaBackgroundVisible(self, visible):
        """Compatibility method - pyqtgraph handles background automatically."""
        pass
    
    def setBackgroundVisible(self, visible):
        """Compatibility method - pyqtgraph handles background automatically."""
        pass
    
    def setMargins(self, margins):
        """Compatibility method - pyqtgraph handles margins automatically."""
        pass


class IntegratedCalibrationChart:
    """
    Chart system using pyqtgraph for reliable cross-platform compatibility.
    """
    def __init__(self, parent_layout, pedal_name, on_curve_changed_callback):
        self.pedal_name = pedal_name
        self.on_curve_changed = on_curve_changed_callback
        self.input_percentage = 0
        self.points = []  # Calibration points
        self.min_deadzone = 0  # Minimum deadzone percentage
        self.max_deadzone = 0  # Maximum deadzone percentage
        self.last_update_time = 0  # Timestamp of last update
        self.update_interval = 33  # ~30fps for better performance
        self.update_scheduled = False  # Track whether an update is already scheduled
        
        # Always use pyqtgraph implementation
        self._create_pyqtgraph_implementation(parent_layout)
        
        # Initialize with default points
        self.reset_to_linear()
    
    def _create_pyqtgraph_implementation(self, parent_layout):
        """Create chart using pyqtgraph."""
        self.chart_view = DraggableChartView()
        self.chart_view.point_moved.connect(self.on_control_point_moved)
        self.chart_view.setMinimumHeight(240)
        # Remove maximum height restriction to allow vertical expansion
        # self.chart_view.setMaximumHeight(260)
        # Change size policy to allow vertical expansion
        self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Add to layout
        parent_layout.addWidget(self.chart_view)
        
        # Create compatibility attributes
        self.chart = self.chart_view  # Make chart point to chart_view for compatibility
        self.curve_series = None
        self.control_points_series = None
        self.indicator_series = None
    
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
        new_points = []
        for point in points:
            if isinstance(point, QPointF):
                new_points.append(point)
            else:
                x, y = point
                new_points.append(QPointF(x, y))
        
        self.points = new_points
        self.update_chart()
    
    def get_points(self):
        """Get calibration points."""
        return [(point.x(), point.y()) for point in self.points]
    
    def update_input_position(self, input_percentage):
        """Update the current input position and calculate the corresponding output position."""
        self.input_percentage = max(0, min(100, input_percentage))
        
        current_time = int(time.time() * 1000)
        if current_time - self.last_update_time < self.update_interval:
            if not self.update_scheduled:
                QTimer.singleShot(self.update_interval, self.update_indicator)
                self.update_scheduled = True
            return
            
        self.last_update_time = current_time
        self.update_scheduled = False
        self.update_indicator()
    
    def update_indicator(self):
        """Update the position of the green indicator dot."""
        if len(self.points) < 2:
            return
        
        display_x = self.input_percentage
        
        if self.input_percentage <= self.min_deadzone:
            display_x = self.min_deadzone
            output_percentage = 0
        elif self.input_percentage >= (100 - self.max_deadzone):
            display_x = 100 - self.max_deadzone
            output_percentage = 100
        else:
            if self.min_deadzone > 0 or self.max_deadzone > 0:
                usable_range = 100.0 - self.min_deadzone - self.max_deadzone
                if usable_range > 0:
                    display_x = self.min_deadzone + (self.input_percentage - self.min_deadzone)
            output_percentage = self.calculate_output_for_input(display_x)
        
        # Update pyqtgraph chart
        self.chart_view.input_percentage = display_x
        self.chart_view.update_plot()
    
    def calculate_output_for_input(self, input_percentage):
        """Calculate the precise output percentage for a given input percentage."""
        sorted_points = self.points
            
        if self.input_percentage <= self.min_deadzone:
            return 0.0
        if self.input_percentage >= (100 - self.max_deadzone):
            return 100.0
            
        if self.min_deadzone > 0 or self.max_deadzone > 0:
            usable_range = 100.0 - self.min_deadzone - self.max_deadzone
            if usable_range > 0:
                scaled_input = ((input_percentage - self.min_deadzone) / usable_range) * 100.0
                input_percentage = max(0.0, min(100.0, scaled_input))
        
        if not sorted_points:
            return input_percentage
        
        if input_percentage <= sorted_points[0].x():
            return sorted_points[0].y()
        if input_percentage >= sorted_points[-1].x():
            return sorted_points[-1].y()
        
        for i in range(len(sorted_points) - 1):
            if sorted_points[i].x() <= input_percentage <= sorted_points[i + 1].x():
                p1 = sorted_points[i]
                p2 = sorted_points[i + 1]
                
                if p1.x() == p2.x():
                    return p1.y()
                
                t = (input_percentage - p1.x()) / (p2.x() - p1.x())
                return p1.y() + t * (p2.y() - p1.y())
        
        return input_percentage
    
    def update_chart(self):
        """Update the chart with current calibration points."""
        if hasattr(self.chart_view, 'points'):
            self.chart_view.points = self.points.copy()
            self.chart_view.update_plot()
        self.update_indicator()
    
    def on_control_point_moved(self):
        """Handle when a control point is moved."""
        # For pyqtgraph, points are already updated in the view
        self.points = self.chart_view.points.copy()
        
        if self.on_curve_changed:
            QTimer.singleShot(300, self.on_curve_changed)
    
    def get_output_value(self, scale=65535):
        """Get the current output value as an integer scaled to the given range."""
        if len(self.points) < 2:
            output_percentage = self.input_percentage
        else:
            output_percentage = self.calculate_output_for_input(self.input_percentage)
        return int((output_percentage / 100) * scale)
    
    def set_deadzones(self, min_deadzone, max_deadzone):
        """Set the deadzone values and update the chart."""
        self.min_deadzone = min_deadzone
        self.max_deadzone = max_deadzone
        self.chart_view.min_deadzone = min_deadzone
        self.chart_view.max_deadzone = max_deadzone
        # Force immediate update of the visual representation
        self.chart_view.update_plot()
        self.update_chart() 