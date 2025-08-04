import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QProgressBar, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPointF
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

# Try to import pyqtgraph, but don't fail if it's not available
try:
    import pyqtgraph as pg
    PYTQTGRAPH_AVAILABLE = True
except ImportError:
    PYTQTGRAPH_AVAILABLE = False
    pg = None

class DraggablePlotWidget:
    """A simple wrapper for pyqtgraph PlotWidget with drag functionality."""
    
    def __init__(self, parent=None):
        if not PYTQTGRAPH_AVAILABLE:
            raise ImportError("pyqtgraph is required for the calibration chart")
        
        self.plot_widget = pg.PlotWidget(parent)
        self.dragging = False
        self.dragging_point = None
        self.dragging_original_coords = None  # Store original coordinates
        self.curve_x = []
        self.curve_y = []
        self.scatter = None
        self.curve_line = None
        self.on_point_moved = None
        self.pg = pg  # Store pg reference
        
        # Override mouse events
        self.plot_widget.mousePressEvent = self.mousePressEvent
        self.plot_widget.mouseMoveEvent = self.mouseMoveEvent
        self.plot_widget.mouseReleaseEvent = self.mouseReleaseEvent
        
    def set_curve_data(self, x, y, on_point_moved=None):
        """Set the curve data and callback for when points are moved."""
        self.curve_x = list(x)
        self.curve_y = list(y)
        self.on_point_moved = on_point_moved
        
        # Validate curve monotonicity (only log if actually fixing)
        if not self._is_monotonic_curve(self.curve_x, self.curve_y):
            # logger.warning("Non-monotonic curve detected, resetting to linear")
            self._reset_to_linear()
        
        # Clear existing items
        self.plot_widget.clear()
        
        # Plot the line
        self.curve_line = self.plot_widget.plot(self.curve_x, self.curve_y, 
                                               pen=self.pg.mkPen('#fba43b', width=2))
        
        # Create scatter points
        self.scatter = self.pg.ScatterPlotItem(x=self.curve_x, y=self.curve_y,
                                          symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                          pen=self.pg.mkPen('#00ff00', width=2))
        self.plot_widget.addItem(self.scatter)
    
    def _reset_to_linear(self):
        """Reset the curve to a safe linear response."""
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        # logger.info("Reset curve to linear response")
        
    def find_nearest_point(self, mouse_x, mouse_y):
        """Find the nearest control point to the mouse position."""
        if not self.curve_x:
            return -1
            
        min_distance = float('inf')
        nearest_point = -1
        
        for i, (x, y) in enumerate(zip(self.curve_x, self.curve_y)):
            distance = ((mouse_x - x) ** 2 + (mouse_y - y) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_point = i
        
        # Use a threshold of 8 units (8% of chart size)
        threshold = 8.0
        if min_distance <= threshold:
            return nearest_point
        return -1
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Get mouse position in chart coordinates
            pos = event.pos()
            view_box = self.plot_widget.getViewBox()
            # Convert QPoint to QPointF
            pos_f = QPointF(pos.x(), pos.y())
            chart_pos = view_box.mapSceneToView(pos_f)
            
            # Find nearest point
            nearest_point = self.find_nearest_point(chart_pos.x(), chart_pos.y())
            
            if nearest_point >= 0:
                self.dragging = True
                self.dragging_point = nearest_point
                # Store original coordinates for this point
                self.dragging_original_coords = (self.curve_x[nearest_point], self.curve_y[nearest_point])
                # Only log in debug mode if needed
                # logger.debug(f"Started dragging point {nearest_point} at ({self.dragging_original_coords[0]:.1f}, {self.dragging_original_coords[1]:.1f})")
                event.accept()
                return
                
        # If we didn't handle it, pass to parent
        super(self.plot_widget.__class__, self.plot_widget).mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.dragging and self.dragging_point is not None:
            # Get mouse position in chart coordinates
            pos = event.pos()
            view_box = self.plot_widget.getViewBox()
            # Convert QPoint to QPointF
            pos_f = QPointF(pos.x(), pos.y())
            chart_pos = view_box.mapSceneToView(pos_f)
            
            # Constrain to chart bounds (0-100)
            x = max(0, min(100, chart_pos.x()))
            y = max(0, min(100, chart_pos.y()))
            
            # Apply constraints to prevent crossing over other dots
            constrained_x, constrained_y = self.constrain_point_position(self.dragging_point, x, y)
            
            # Update the point directly using the dragging_point index
            if self.dragging_point < len(self.curve_x):
                self.curve_x[self.dragging_point] = constrained_x
                self.curve_y[self.dragging_point] = constrained_y
                
                # Update the scatter plot
                self.scatter.setData(self.curve_x, self.curve_y)
                
                # Update the line
                self.curve_line.setData(self.curve_x, self.curve_y)
                
                # Call callback if provided
                if self.on_point_moved:
                    self.on_point_moved(self.curve_x, self.curve_y)
                    
                # Only log in debug mode if needed
                # logger.debug(f"Dragged point {self.dragging_point} to ({constrained_x:.1f}, {constrained_y:.1f})")
            
            event.accept()
            return
            
        # If we didn't handle it, pass to parent
        super(self.plot_widget.__class__, self.plot_widget).mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if self.dragging:
            # Call callback if provided
            if self.on_point_moved:
                self.on_point_moved(self.curve_x, self.curve_y)
            
            self.dragging = False
            self.dragging_point = None
            self.dragging_original_coords = None
            # Only log in debug mode if needed
            # logger.debug("Stopped dragging")
            event.accept()
            return
            
        # If we didn't handle it, pass to parent
        super(self.plot_widget.__class__, self.plot_widget).mouseReleaseEvent(event)
        
    def constrain_point_position(self, point_index, x, y):
        """Constrain a point's position to maintain a monotonic curve."""
        if len(self.curve_x) < 2:
            return x, y
            
        # Special constraints for first and last points
        if point_index == 0:
            # First point must stay at x=0
            return 0, max(0, min(100, y))
        elif point_index == len(self.curve_x) - 1:
            # Last point must stay at x=100
            return 100, max(0, min(100, y))
        
        # Get the x-coordinates of all other points
        other_x_coords = [self.curve_x[i] for i in range(len(self.curve_x)) if i != point_index]
        
        # Find the closest points on either side
        left_points = [cx for cx in other_x_coords if cx < x]
        right_points = [cx for cx in other_x_coords if cx > x]
        
        # Constrain x position to prevent crossing over
        min_x = max(left_points) if left_points else 0
        max_x = min(right_points) if right_points else 100
        
        # Apply constraints with a small buffer
        buffer = 2.0  # 2% buffer to prevent overlap
        constrained_x = max(min_x + buffer, min(max_x - buffer, x))
        
        # Constrain y to reasonable bounds
        constrained_y = max(0, min(100, y))
        
        # Additional validation: ensure the curve remains monotonic
        # Create a temporary list with the new position
        temp_x = self.curve_x.copy()
        temp_y = self.curve_y.copy()
        temp_x[point_index] = constrained_x
        temp_y[point_index] = constrained_y
        
        # Check if this creates a valid monotonic curve
        if not self._is_monotonic_curve(temp_x, temp_y):
            # If not monotonic, revert to original position
            # logger.warning(f"Point {point_index} movement would create non-monotonic curve, reverting")
            return self.curve_x[point_index], self.curve_y[point_index]
        
        return constrained_x, constrained_y
    
    def _is_monotonic_curve(self, x_coords, y_coords):
        """Check if the curve is monotonically increasing."""
        if len(x_coords) < 2:
            return True
            
        # Sort by x-coordinate to check monotonicity
        sorted_points = sorted(zip(x_coords, y_coords), key=lambda p: p[0])
        
        # Check if y-values are monotonically increasing
        for i in range(1, len(sorted_points)):
            if sorted_points[i][1] < sorted_points[i-1][1]:
                return False
                
        return True

class PedalCalibrationWidget(QWidget):
    calibration_updated = pyqtSignal(dict)
    
    def __init__(self, pedal_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.pedal_name = pedal_name
        self.global_managers = global_managers
        
        self.min_value = 0
        self.max_value = 65535
        self.current_input = 0
        
        self.input_progress = None
        self.input_label = None
        self.output_label = None
        self.output_progress = None
        self.min_label = None
        self.max_label = None
        self.curve_selector = None
        self.calibration_chart = None
        
        # Curve data
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        self.curve_line = None
        self.scatter = None
        
        # Flag to prevent recursive validation
        self._is_fixing_curve = False
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        group = QGroupBox(f"{self.pedal_name.title()} Calibration")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #666666;
                border-radius: 6px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        
        self.create_input_monitor(group_layout)
        self.create_calibration_chart(group_layout)
        self.create_calibration_controls(group_layout)
        self.create_curve_selector(group_layout)
        
        layout.addWidget(group)
        
        # Update deadzone visualization after UI is created
        self.update_deadzone_visualization()
    
    def create_input_monitor(self, parent_layout):
        input_group = QGroupBox("Input Monitor")
        input_group.setMaximumHeight(125)
        input_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        input_layout = QVBoxLayout()
        input_layout.setSpacing(8)
        input_layout.setContentsMargins(12, 12, 12, 12)
        
        self.input_label = QLabel("Raw Input: 0")
        self.input_label.setMinimumHeight(20)
        self.input_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 4px 2px;
                margin: 1px 0px;
            }
        """)
        self.input_progress = QProgressBar()
        self.input_progress.setMaximum(65535)
        self.input_progress.setValue(0)
        self.input_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #666666;
                border-radius: 3px;
                text-align: center;
                background-color: #1a1a1a;
                color: #fefefe;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 2px;
            }
        """)
        
        self.output_label = QLabel("Output: 0%")
        self.output_label.setMinimumHeight(20)
        self.output_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 4px 2px;
                margin: 1px 0px;
            }
        """)
        self.output_progress = QProgressBar()
        self.output_progress.setMaximum(100)
        self.output_progress.setValue(0)
        self.output_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #666666;
                border-radius: 3px;
                text-align: center;
                background-color: #1a1a1a;
                color: #fefefe;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #fba43b;
                border-radius: 2px;
            }
        """)
        
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_progress)
        input_layout.addWidget(self.output_label)
        input_layout.addWidget(self.output_progress)
        
        input_group.setLayout(input_layout)
        parent_layout.addWidget(input_group)
    
    def create_calibration_chart(self, parent_layout):
        chart_group = QGroupBox("Calibration Chart")
        chart_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        chart_layout = QVBoxLayout()
        
        try:
            if not PYTQTGRAPH_AVAILABLE:
                raise ImportError("pyqtgraph not available")
            
            # Create our custom draggable plot widget
            self.draggable_plot = DraggablePlotWidget()
            self.calibration_chart = self.draggable_plot.plot_widget
            
            # Configure the chart
            self.calibration_chart.setLabel('left', 'Output %')
            self.calibration_chart.setLabel('bottom', 'Input %')
            self.calibration_chart.setTitle(f'{self.pedal_name.title()} Response Curve')
            self.calibration_chart.setBackground('#252525')
            self.calibration_chart.getAxis('left').setPen('#fefefe')
            self.calibration_chart.getAxis('bottom').setPen('#fefefe')
            self.calibration_chart.getAxis('left').setTextPen('#fefefe')
            self.calibration_chart.getAxis('bottom').setTextPen('#fefefe')
            
            # Set axis ranges and lock them to prevent zooming/panning
            self.calibration_chart.setXRange(0, 100)
            self.calibration_chart.setYRange(0, 100)
            self.calibration_chart.setLimits(xMin=0, xMax=100, yMin=0, yMax=100)
            
            # Add grid
            self.calibration_chart.showGrid(x=True, y=True, alpha=0.3)
            
            # Initialize deadzone visualization
            self.min_deadzone_rect = None
            self.max_deadzone_rect = None
            
            # Set up the curve data with callback
            self.draggable_plot.set_curve_data(self.curve_x, self.curve_y, self.on_curve_points_changed)
            
            # Disable chart dragging/zooming
            self.calibration_chart.setMouseEnabled(x=False, y=False)
            
            chart_layout.addWidget(self.calibration_chart)
            # logger.info(f"Created draggable pyqtgraph chart for {self.pedal_name}")
        except ImportError:
            chart_placeholder = QLabel("Chart not available - pyqtgraph not installed")
            chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_placeholder.setMinimumHeight(200)
            chart_layout.addWidget(chart_placeholder)
            # logger.warning(f"No charting library available for {self.pedal_name}")
        
        chart_group.setLayout(chart_layout)
        parent_layout.addWidget(chart_group)
    
    def on_curve_points_changed(self, x, y):
        """Callback when curve points are moved."""
        self.curve_x = list(x)
        self.curve_y = list(y)
        
        # Validate and fix non-monotonic curves (only if not already fixing)
        if not self._is_fixing_curve and not self._is_monotonic_curve(self.curve_x, self.curve_y):
            # logger.warning(f"Non-monotonic curve detected for {self.pedal_name}, attempting to fix")
            self._fix_monotonic_curve()
        
        self.emit_calibration_update()
        # Only log in debug mode if needed
        # logger.debug(f"Curve points changed for {self.pedal_name}")
    
    def _is_monotonic_curve(self, x_coords, y_coords):
        """Check if the curve is monotonically increasing."""
        if len(x_coords) < 2:
            return True
            
        # Sort by x-coordinate to check monotonicity
        sorted_points = sorted(zip(x_coords, y_coords), key=lambda p: p[0])
        
        # Check if y-values are monotonically increasing
        for i in range(1, len(sorted_points)):
            if sorted_points[i][1] < sorted_points[i-1][1]:
                return False
                
        return True
    
    def _fix_monotonic_curve(self):
        """Fix a non-monotonic curve by adjusting y-values to be monotonically increasing."""
        if len(self.curve_x) < 2 or self._is_fixing_curve:
            return
            
        self._is_fixing_curve = True
        
        try:
            # Sort points by x-coordinate
            sorted_points = sorted(zip(self.curve_x, self.curve_y), key=lambda p: p[0])
            
            # Fix y-values to be monotonically increasing
            fixed_y = [sorted_points[0][1]]  # Start with first y-value
            
            for i in range(1, len(sorted_points)):
                current_y = sorted_points[i][1]
                prev_y = fixed_y[-1]
                
                # Ensure current y is not less than previous y
                if current_y < prev_y:
                    current_y = prev_y  # Make it equal to previous to maintain monotonicity
                
                fixed_y.append(current_y)
            
            # Update the curve data with fixed values
            self.curve_x = [p[0] for p in sorted_points]
            self.curve_y = fixed_y
            
            # Update the chart directly without triggering validation
            if hasattr(self, 'draggable_plot') and self.draggable_plot:
                # Temporarily disable the callback to prevent recursion
                original_callback = self.draggable_plot.on_point_moved
                self.draggable_plot.on_point_moved = None
                
                # Update the chart data
                self.draggable_plot.curve_x = self.curve_x.copy()
                self.draggable_plot.curve_y = self.curve_y.copy()
                
                # Clear and redraw
                self.draggable_plot.plot_widget.clear()
                self.draggable_plot.curve_line = self.draggable_plot.plot_widget.plot(
                    self.curve_x, self.curve_y, 
                    pen=self.draggable_plot.pg.mkPen('#fba43b', width=2)
                )
                self.draggable_plot.scatter = self.draggable_plot.pg.ScatterPlotItem(
                    x=self.curve_x, y=self.curve_y,
                    symbol='o', symbolBrush='#00ff00', symbolSize=12,
                    pen=self.draggable_plot.pg.mkPen('#00ff00', width=2)
                )
                self.draggable_plot.plot_widget.addItem(self.draggable_plot.scatter)
                
                # Restore the callback
                self.draggable_plot.on_point_moved = original_callback
            
            # logger.info(f"Fixed non-monotonic curve for {self.pedal_name}")
            
        finally:
            self._is_fixing_curve = False
    
    def update_deadzone_visualization(self):
        """Update the deadzone visualization on the chart."""
        if not hasattr(self, 'calibration_chart') or not self.calibration_chart:
            return
            
        try:
            if not PYTQTGRAPH_AVAILABLE:
                return
            
            # Remove existing deadzone rectangles
            if hasattr(self, 'min_deadzone_rect') and self.min_deadzone_rect:
                self.calibration_chart.removeItem(self.min_deadzone_rect)
                self.min_deadzone_rect = None
            if hasattr(self, 'max_deadzone_rect') and self.max_deadzone_rect:
                self.calibration_chart.removeItem(self.max_deadzone_rect)
                self.max_deadzone_rect = None
            
            # Get deadzone values from the deadzone widget
            deadzone_widget = None
            try:
                if hasattr(self.parent(), 'layout') and self.parent() is not None:
                    layout = self.parent().layout()
                    if layout:
                        for i in range(layout.count()):
                            item = layout.itemAt(i)
                            if item and item.widget():
                                widget = item.widget()
                                if hasattr(widget, 'pedal_name') and widget.pedal_name == self.pedal_name:
                                    if hasattr(widget, 'layout'):
                                        widget_layout = widget.layout()
                                        if widget_layout:
                                            for j in range(widget_layout.count()):
                                                child_item = widget_layout.itemAt(j)
                                                if child_item and child_item.widget():
                                                    child_widget = child_item.widget()
                                                    if hasattr(child_widget, 'get_deadzone_values'):
                                                        deadzone_widget = child_widget
                                                        break
                                    break
            except Exception as e:
                logger.debug(f"Error finding deadzone widget: {e}")
                deadzone_widget = None
            
            if deadzone_widget:
                try:
                    deadzone_values = deadzone_widget.get_deadzone_values()
                    min_deadzone = deadzone_values.get('min_deadzone', 0)
                    max_deadzone = deadzone_values.get('max_deadzone', 0)
                except Exception as e:
                    logger.debug(f"Error getting deadzone values: {e}")
                    min_deadzone = 0
                    max_deadzone = 0
                
                # Add min deadzone rectangle
                if min_deadzone > 0 and hasattr(self, 'draggable_plot') and self.draggable_plot:
                    self.min_deadzone_rect = self.draggable_plot.pg.LinearRegionItem(
                        values=[0, min_deadzone],
                        orientation='vertical',
                        brush=self.draggable_plot.pg.mkBrush(200, 50, 50, 100),
                        pen=self.draggable_plot.pg.mkPen(200, 50, 50)
                    )
                    self.calibration_chart.addItem(self.min_deadzone_rect)
                
                # Add max deadzone rectangle
                if max_deadzone > 0 and hasattr(self, 'draggable_plot') and self.draggable_plot:
                    self.max_deadzone_rect = self.draggable_plot.pg.LinearRegionItem(
                        values=[100 - max_deadzone, 100],
                        orientation='vertical',
                        brush=self.draggable_plot.pg.mkBrush(200, 50, 50, 100),
                        pen=self.draggable_plot.pg.mkPen(200, 50, 50)
                    )
                    self.calibration_chart.addItem(self.max_deadzone_rect)
                
                # Only log in debug mode if needed
                # logger.debug(f"Updated deadzone visualization for {self.pedal_name}: min={min_deadzone}%, max={max_deadzone}%")
                
        except ImportError:
            pass
        except Exception as e:
            # logger.error(f"Error updating deadzone visualization: {e}")
            pass
    
    def create_calibration_controls(self, parent_layout):
        controls_group = QGroupBox("Calibration Controls")
        controls_group.setMaximumHeight(85)
        controls_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        
        range_layout = QHBoxLayout()
        self.min_label = QLabel(f"Min: {self.min_value}")
        self.min_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 4px 6px;
                margin: 2px 0px;
            }
        """)
        self.max_label = QLabel(f"Max: {self.max_value}")
        self.max_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 4px 6px;
                margin: 2px 0px;
            }
        """)
        range_layout.addWidget(self.min_label)
        range_layout.addStretch()
        range_layout.addWidget(self.max_label)
        
        button_layout = QHBoxLayout()
        set_min_btn = QPushButton("Set Min")
        set_max_btn = QPushButton("Set Max")
        reset_btn = QPushButton("Reset")
        
        # Blue styling for Set Min/Max buttons
        blue_style = """
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e6bb8;
            }
            QPushButton:pressed {
                background-color: #155a9e;
            }
        """
        
        # Red styling for Reset button
        red_style = """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """
        
        set_min_btn.setStyleSheet(blue_style)
        set_max_btn.setStyleSheet(blue_style)
        reset_btn.setStyleSheet(red_style)
        
        set_min_btn.clicked.connect(self.set_current_as_min)
        set_max_btn.clicked.connect(self.set_current_as_max)
        reset_btn.clicked.connect(self.reset_calibration)
        
        button_layout.addWidget(set_min_btn)
        button_layout.addWidget(set_max_btn)
        button_layout.addWidget(reset_btn)
        
        controls_layout.addLayout(range_layout)
        controls_layout.addLayout(button_layout)
        
        controls_group.setLayout(controls_layout)
        parent_layout.addWidget(controls_group)
    
    def create_curve_selector(self, parent_layout):
        curve_group = QGroupBox("Response Curve")
        curve_group.setMaximumHeight(120)
        curve_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        curve_layout = QVBoxLayout()
        curve_layout.setSpacing(8)
        curve_layout.setContentsMargins(12, 12, 12, 12)
        
        # Curve type selector
        self.curve_selector = QComboBox()
        self.curve_selector.addItems([
            "Linear (Default)",
            "Exponential",
            "Logarithmic",
            "S-Curve",
            "Custom"
        ])
        self.curve_selector.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                color: #fefefe;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #fefefe;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                color: #fefefe;
                border: 1px solid #666666;
                selection-background-color: #2a82da;
            }
        """)
        self.curve_selector.currentTextChanged.connect(self.on_curve_changed)
        
        curve_layout.addWidget(self.curve_selector)
        
        curve_group.setLayout(curve_layout)
        parent_layout.addWidget(curve_group)
    
    def get_pedal_curves(self):
        """Get available curves for this pedal."""
        curves = {
            "Linear (Default)": [(0, 0), (25, 25), (50, 50), (75, 75), (100, 100)],
            "Exponential": [(0, 0), (25, 10), (50, 25), (75, 50), (100, 100)],
            "Logarithmic": [(0, 0), (25, 40), (50, 60), (75, 80), (100, 100)],
            "S-Curve": [(0, 0), (25, 15), (50, 50), (75, 85), (100, 100)]
        }
        return curves
    
    def get_curve_points(self, curve_name: str):
        """Get the points for a specific curve."""
        curves = self.get_pedal_curves()
        if curve_name in curves:
            return curves[curve_name]
        return curves["Linear (Default)"]
    
    def update_input_value(self, value: int):
        """Update the input value display and calculate output."""
        self.current_input = value
        
        if self.input_label:
            self.input_label.setText(f"Raw Input: {value}")
        
        if self.input_progress:
            self.input_progress.setValue(value)
        
        # Calculate output based on current curve
        output_percentage = self.calculate_output_with_curve(value)
        
        if self.output_label:
            self.output_label.setText(f"Output: {output_percentage:.1f}%")
        
        if self.output_progress:
            self.output_progress.setValue(int(output_percentage))
    
    def calculate_output_with_curve(self, raw_value: int) -> float:
        """Calculate output percentage based on input and current curve."""
        if self.max_value == self.min_value:
            return 0.0
        
        # Normalize input to 0-100 range
        normalized_input = ((raw_value - self.min_value) / (self.max_value - self.min_value)) * 100
        normalized_input = max(0, min(100, normalized_input))
        
        # Sort points by x-coordinate for proper interpolation
        points = list(zip(self.curve_x, self.curve_y))
        points.sort(key=lambda p: p[0])
        sorted_x, sorted_y = zip(*points)
        
        # Interpolate between curve points
        if normalized_input <= 0:
            return sorted_y[0]
        elif normalized_input >= 100:
            return sorted_y[-1]
        else:
            # Find the two points to interpolate between
            for i in range(len(sorted_x) - 1):
                x1, y1 = sorted_x[i], sorted_y[i]
                x2, y2 = sorted_x[i + 1], sorted_y[i + 1]
                
                if x1 <= normalized_input <= x2:
                    # Linear interpolation
                    ratio = (normalized_input - x1) / (x2 - x1)
                    return y1 + ratio * (y2 - y1)
        
        return normalized_input  # Fallback to linear
    
    def set_current_as_min(self):
        """Set current input value as minimum."""
        self.min_value = self.current_input
        if self.min_label:
            self.min_label.setText(f"Min: {self.min_value}")
        self.emit_calibration_update()
    
    def set_current_as_max(self):
        """Set current input value as maximum."""
        self.max_value = self.current_input
        if self.max_label:
            self.max_label.setText(f"Max: {self.max_value}")
        self.emit_calibration_update()
    
    def reset_calibration(self):
        self.min_value = 0
        self.max_value = 65535
        if self.min_label:
            self.min_label.setText(f"Min: {self.min_value}")
        if self.max_label:
            self.max_label.setText(f"Max: {self.max_value}")
        
        # Reset curve to safe linear state
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        
        # Update the chart if available
        if hasattr(self, 'draggable_plot') and self.draggable_plot:
            self.draggable_plot.set_curve_data(self.curve_x, self.curve_y, self.on_curve_points_changed)
        
        self.emit_calibration_update()
        # logger.info(f"Reset calibration for {self.pedal_name}")
    
    def on_curve_changed(self, curve_name: str):
        # logger.info(f"Curve changed for {self.pedal_name}: {curve_name}")
        
        # Get the points for this curve
        curve_points = self.get_curve_points(curve_name)
        
        # Apply to chart if available
        if hasattr(self, 'draggable_plot') and self.draggable_plot:
            try:
                # Extract x and y coordinates
                x = [point[0] for point in curve_points]
                y = [point[1] for point in curve_points]
                
                # Validate curve monotonicity before applying
                if not self._is_monotonic_curve(x, y):
                    # logger.warning(f"Non-monotonic curve '{curve_name}' detected for {self.pedal_name}, using linear fallback")
                    # Use linear curve as fallback
                    x = [0, 25, 50, 75, 100]
                    y = [0, 25, 50, 75, 100]
                
                # Update curve data
                self.curve_x = x
                self.curve_y = y
                
                # Update the draggable plot
                self.draggable_plot.set_curve_data(x, y, self.on_curve_points_changed)
                
                # Update deadzone visualization
                self.update_deadzone_visualization()
                
                # Only log in debug mode if needed
                # logger.debug(f"Applied {len(x)} points to {self.pedal_name} chart")
            except ImportError:
                pass
        
        self.emit_calibration_update()
    
    def emit_calibration_update(self):
        data = {
            'min_value': self.min_value,
            'max_value': self.max_value,
            'curve_type': self.curve_selector.currentText() if self.curve_selector else "Linear (Default)",
            'curve_points': list(zip(self.curve_x, self.curve_y))
        }
        self.calibration_updated.emit(data)
    
    def set_calibration_range(self, min_val: int, max_val: int):
        self.min_value = min_val
        self.max_value = max_val
        if self.min_label:
            self.min_label.setText(f"Min: {min_val}")
        if self.max_label:
            self.max_label.setText(f"Max: {max_val}")
        self.emit_calibration_update()
    
    def get_calibration_data(self):
        return {
            'min_value': self.min_value,
            'max_value': self.max_value,
            'curve_type': self.curve_selector.currentText() if self.curve_selector else "Linear (Default)",
            'current_input': self.current_input,
            'curve_points': list(zip(self.curve_x, self.curve_y))
        }