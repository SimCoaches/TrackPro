"""Calibration chart widget for visualizing and editing pedal response curves."""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor, QPainterPath

class CalibrationChart:
    """Chart for visualizing and editing pedal calibration curves."""
    
    def __init__(self, parent_widget):
        """Initialize the calibration chart.
        
        Args:
            parent_widget: The parent widget to attach the chart to
        """
        self.parent = parent_widget
        self.points = [QPointF(0, 0), QPointF(50, 50), QPointF(100, 100)]
        self.min_deadzone = 0
        self.max_deadzone = 0
        
        # Current input position
        self.current_input = 0
        self.current_output = 0
        
        # Setup scene and view
        self.setup_chart()
    
    def setup_chart(self):
        """Set up the chart graphics scene and view."""
        # Create a scene for our chart
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 100, 100)
        
        # Create view to display the scene
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(self.view.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Add to parent
        if hasattr(self.parent, 'layout'):
            self.parent.layout().addWidget(self.view)
    
    def update_chart(self):
        """Update the chart visualization with current points and state."""
        # Clear the scene
        self.scene.clear()
        
        # Draw background grid
        self.draw_grid()
        
        # Draw the curve
        self.draw_curve()
        
        # Draw control points
        self.draw_points()
        
        # Draw deadzones
        self.draw_deadzones()
        
        # Draw current input position
        self.draw_input_position()
    
    def draw_grid(self):
        """Draw background grid."""
        # Draw grid lines
        grid_pen = QPen(QColor(50, 50, 50))
        grid_pen.setWidth(1)
        
        # Vertical grid lines
        for x in range(0, 101, 10):
            self.scene.addLine(x, 0, x, 100, grid_pen)
        
        # Horizontal grid lines
        for y in range(0, 101, 10):
            self.scene.addLine(0, y, 100, 100-y, grid_pen)
        
        # Draw border
        border_pen = QPen(QColor(100, 100, 100))
        border_pen.setWidth(2)
        self.scene.addRect(0, 0, 100, 100, border_pen)
    
    def draw_curve(self):
        """Draw the response curve."""
        if not self.points:
            return
        
        # Sort points by x-coordinate
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Create path for curve
        path = QPainterPath()
        path.moveTo(sorted_points[0].x(), 100 - sorted_points[0].y())
        
        # Add line segments through all points
        for i in range(1, len(sorted_points)):
            path.lineTo(sorted_points[i].x(), 100 - sorted_points[i].y())
        
        # Draw the path
        curve_pen = QPen(QColor(0, 120, 210))
        curve_pen.setWidth(2)
        self.scene.addPath(path, curve_pen)
    
    def draw_points(self):
        """Draw the control points."""
        point_brush = QBrush(QColor(210, 50, 50))
        point_pen = QPen(QColor(0, 0, 0))
        point_size = 4
        
        for point in self.points:
            self.scene.addEllipse(
                point.x() - point_size,
                100 - point.y() - point_size,
                point_size * 2,
                point_size * 2,
                point_pen,
                point_brush
            )
    
    def draw_deadzones(self):
        """Draw the deadzone markers."""
        if self.min_deadzone > 0:
            # Draw min deadzone
            deadzone_brush = QBrush(QColor(200, 50, 50, 100))
            deadzone_pen = QPen(QColor(200, 50, 50))
            self.scene.addRect(0, 0, self.min_deadzone, 100, deadzone_pen, deadzone_brush)
        
        if self.max_deadzone > 0:
            # Draw max deadzone
            deadzone_brush = QBrush(QColor(200, 50, 50, 100))
            deadzone_pen = QPen(QColor(200, 50, 50))
            self.scene.addRect(100 - self.max_deadzone, 0, self.max_deadzone, 100, deadzone_pen, deadzone_brush)
    
    def draw_input_position(self):
        """Draw the current input position indicator."""
        if self.current_input < 0 or self.current_input > 100:
            return
        
        # Draw input position
        input_pen = QPen(QColor(0, 200, 0))
        input_brush = QBrush(QColor(0, 200, 0))
        
        # Draw a marker at input position
        marker_size = 3
        self.scene.addEllipse(
            self.current_input - marker_size,
            100 - self.current_output - marker_size,
            marker_size * 2,
            marker_size * 2,
            input_pen,
            input_brush
        )
    
    def set_points(self, points):
        """Set the control points for the curve.
        
        Args:
            points: List of QPointF points
        """
        self.points = points
        self.update_chart()
    
    def get_points(self):
        """Get the current control points.
        
        Returns:
            List of QPointF points
        """
        return self.points
    
    def set_input_position(self, input_value, output_value=None):
        """Set the current input position.
        
        Args:
            input_value: Input value (0-100)
            output_value: Output value (0-100), or None to calculate from curve
        """
        self.current_input = input_value
        
        # Calculate output from curve if not provided
        if output_value is None:
            output_value = self.calculate_output(input_value)
        
        self.current_output = output_value
        self.update_chart()
    
    def calculate_output(self, input_value):
        """Calculate output value for a given input based on the curve.
        
        Args:
            input_value: Input value (0-100)
            
        Returns:
            Output value (0-100)
        """
        if not self.points:
            return input_value
        
        # Sort points by x-coordinate
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Handle input value before first point
        if input_value <= sorted_points[0].x():
            return sorted_points[0].y()
        
        # Handle input value after last point
        if input_value >= sorted_points[-1].x():
            return sorted_points[-1].y()
        
        # Find the two points that the input falls between
        for i in range(len(sorted_points) - 1):
            if sorted_points[i].x() <= input_value <= sorted_points[i+1].x():
                # Linear interpolation between points
                x1 = sorted_points[i].x()
                y1 = sorted_points[i].y()
                x2 = sorted_points[i+1].x()
                y2 = sorted_points[i+1].y()
                
                # Avoid division by zero
                if x2 == x1:
                    return y1
                
                # Linear interpolation formula
                t = (input_value - x1) / (x2 - x1)
                return y1 + t * (y2 - y1)
        
        # Fallback
        return input_value
    
    def set_deadzones(self, min_deadzone, max_deadzone):
        """Set the deadzone values.
        
        Args:
            min_deadzone: Minimum deadzone percentage (0-100)
            max_deadzone: Maximum deadzone percentage (0-100)
        """
        self.min_deadzone = min_deadzone
        self.max_deadzone = max_deadzone
        self.update_chart()
    
    def reset_to_linear(self):
        """Reset the curve to a linear response."""
        self.points = [QPointF(0, 0), QPointF(100, 100)]
        self.update_chart() 