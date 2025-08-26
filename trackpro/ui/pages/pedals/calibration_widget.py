import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QProgressBar, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPointF, QRect
from PyQt6.QtGui import QPainter, QPen, QBrush
from ...modern.shared.base_page import GlobalManagers
from ....pedals.mapping import map_raw, eval_curve
from ....pedals.input_processing import apply_deadzones_norm

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
        
        # Endpoint x-anchors (will be synced to min/max deadzones)
        self.first_x_anchor = 0.0
        self.last_x_anchor = 100.0
        
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
        
        # Force endpoints to respect current anchors
        if self.curve_x:
            self.curve_x[0] = self.first_x_anchor
            # First dot output is fixed at 0% and is only moved by deadzone
            self.curve_y[0] = 0.0
        if len(self.curve_x) >= 2:
            self.curve_x[-1] = self.last_x_anchor
            self.curve_y[-1] = max(0, min(100, self.curve_y[-1]))
        
        # Update or create line and scatter without clearing the plot (preserves response dot and overlays)
        if self.curve_line is None:
            self.curve_line = self.plot_widget.plot(self.curve_x, self.curve_y,
                                                    pen=self.pg.mkPen('#fba43b', width=2))
            try:
                self.curve_line.setDownsampling(mode='peak')
                self.curve_line.setClipToView(True)
            except Exception:
                pass
        else:
            try:
                self.curve_line.setData(self.curve_x, self.curve_y)
            except Exception:
                # Fallback: re-create if setData fails
                try:
                    self.plot_widget.removeItem(self.curve_line)
                except Exception:
                    pass
                self.curve_line = self.plot_widget.plot(self.curve_x, self.curve_y,
                                                        pen=self.pg.mkPen('#fba43b', width=2))
                try:
                    self.curve_line.setDownsampling(mode='peak')
                    self.curve_line.setClipToView(True)
                except Exception:
                    pass

        if self.scatter is None:
            self.scatter = self.pg.ScatterPlotItem(x=self.curve_x, y=self.curve_y,
                                                   symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                                   pen=self.pg.mkPen('#00ff00', width=2))
            self.plot_widget.addItem(self.scatter)
        else:
            try:
                self.scatter.setData(self.curve_x, self.curve_y)
            except Exception:
                try:
                    self.plot_widget.removeItem(self.scatter)
                except Exception:
                    pass
                self.scatter = self.pg.ScatterPlotItem(x=self.curve_x, y=self.curve_y,
                                                       symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                                       pen=self.pg.mkPen('#00ff00', width=2))
                self.plot_widget.addItem(self.scatter)

    def set_endpoints(self, first_x: float, last_x: float):
        """Anchor the first and last control points to the given x positions."""
        # Clamp inputs
        first_x = max(0.0, min(100.0, float(first_x)))
        last_x = max(0.0, min(100.0, float(last_x)))
        if last_x < first_x:
            last_x = first_x
        self.first_x_anchor = first_x
        self.last_x_anchor = last_x
        
        if not self.curve_x:
            return
        
        # Apply anchors to endpoints
        self.curve_x[0] = self.first_x_anchor
        if len(self.curve_x) >= 2:
            self.curve_x[-1] = self.last_x_anchor
        
        # Keep interior points within anchored bounds
        buffer = 2.0
        if len(self.curve_x) >= 3:
            # Second point cannot be left of first + buffer
            if self.curve_x[1] < self.first_x_anchor + buffer:
                self.curve_x[1] = min(self.first_x_anchor + buffer, self.last_x_anchor)
            # Second-to-last cannot be right of last - buffer
            if self.curve_x[-2] > self.last_x_anchor - buffer:
                self.curve_x[-2] = max(self.first_x_anchor, self.last_x_anchor - buffer)
        
        # Refresh plot
        if self.curve_line is not None:
            self.curve_line.setData(self.curve_x, self.curve_y)
        if self.scatter is not None:
            self.scatter.setData(self.curve_x, self.curve_y)
    
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
            
            # Prevent dragging of the first control point; it is controlled by deadzone only
            if nearest_point == 0:
                event.accept()
                return
            
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
            # First point must stay at anchored x and y=0%
            return self.first_x_anchor, 0.0
        elif point_index == len(self.curve_x) - 1:
            # Last point must stay at anchored x
            return self.last_x_anchor, max(0, min(100, y))
        
        # Get the x-coordinates of all other points
        other_x_coords = [self.curve_x[i] for i in range(len(self.curve_x)) if i != point_index]
        
        # Find the closest points on either side
        left_points = [cx for cx in other_x_coords if cx < x]
        right_points = [cx for cx in other_x_coords if cx > x]
        
        # Constrain x position to prevent crossing over
        min_x = max(left_points) if left_points else self.first_x_anchor
        max_x = min(right_points) if right_points else self.last_x_anchor
        
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
        # Deadzone percentages for visualization and output calculation
        self.min_deadzone = 0
        self.max_deadzone = 0
        
        # Curve data
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        self.curve_line = None
        self.scatter = None
        self.response_dot = None
        
        # Caches to avoid redundant UI updates (reduce perceived lag)
        self._last_input_progress = -1
        self._last_output_progress = -1
        self._last_input_label = None
        self._last_output_label = None
        self._last_dot_x = None
        self._last_dot_y = None
        
        # Flag to prevent recursive validation
        self._is_fixing_curve = False
        
        self.init_ui()
        
        # Load existing calibration data from hardware
        self.load_existing_calibration_data()
        
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
        
    def load_existing_calibration_data(self):
        """Load existing calibration data from hardware input."""
        try:
            if not self.global_managers:
                return
                
            hardware = getattr(self.global_managers, 'hardware', None)
            if not hardware:
                return
                
            # Load calibration curve if it exists
            if hasattr(hardware, 'calibration') and hardware.calibration:
                pedal_calibration = hardware.calibration.get(self.pedal_name, {})
                if pedal_calibration:
                    # Load curve points
                    points = pedal_calibration.get('points', [])
                    if points and len(points) > 0:
                        # Convert points to x,y arrays
                        try:
                            self.curve_x = [pt[0] for pt in points]
                            self.curve_y = [pt[1] for pt in points]
                            logger.info(f"Loaded existing curve for {self.pedal_name}: {len(points)} points")
                        except (IndexError, TypeError) as e:
                            logger.debug(f"Invalid curve points format for {self.pedal_name}: {e}")
                    
                    # Load curve type
                    curve_type = pedal_calibration.get('curve', 'Linear (Default)')
                    if self.curve_selector:
                        # Find and set the curve type in the selector
                        for i in range(self.curve_selector.count()):
                            if self.curve_selector.itemText(i) == curve_type:
                                self.curve_selector.setCurrentIndex(i)
                                break
            
            # Load axis ranges (calibration min/max)
            if hasattr(hardware, 'axis_ranges') and hardware.axis_ranges:
                axis_data = hardware.axis_ranges.get(self.pedal_name, {})
                if axis_data:
                    min_val = axis_data.get('min', 0)
                    max_val = axis_data.get('max', 65535)
                    self.set_calibration_range(min_val, max_val)
                    logger.info(f"Loaded calibration range for {self.pedal_name}: {min_val}-{max_val}")
                    
                    # Load deadzones from axis ranges
                    min_deadzone = axis_data.get('min_deadzone', 0)
                    max_deadzone = axis_data.get('max_deadzone', 0)
                    self.set_deadzone_values(min_deadzone, max_deadzone)
                    logger.info(f"Loaded deadzones for {self.pedal_name}: min={min_deadzone}%, max={max_deadzone}%")
            
            # Update the chart with loaded data
            if hasattr(self, 'calibration_chart') and self.calibration_chart:
                self.calibration_chart.set_curve_data(
                    self.curve_x, 
                    self.curve_y, 
                    self.on_point_moved
                )
                self.update_deadzone_visualization()
                logger.debug(f"Updated calibration chart for {self.pedal_name}")
                
        except Exception as e:
            logger.debug(f"Failed to load existing calibration data for {self.pedal_name}: {e}")
        
        # Ensure the response dot is present and positioned after loading
        try:
            self._ensure_response_dot()
            self.update_input_value(self.current_input)
        except Exception:
            pass
    

    
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
            
            # Apply pyqtgraph performance optimizations
            try:
                plot_item = self.calibration_chart.getPlotItem()
                plot_item.setClipToView(True)          # draw only visible region
                plot_item.setDownsampling(mode='peak') # keep detail without overdraw
            except Exception:
                pass
            try:
                vb = self.calibration_chart.getViewBox()
                if hasattr(vb, 'setMouseEnabled'):
                    vb.setMouseEnabled(x=False, y=False)
                if hasattr(vb, 'setDefaultPadding'):
                    vb.setDefaultPadding(0.0)
                if hasattr(vb, 'enableAutoRange'):
                    vb.enableAutoRange(x=False, y=False)
                if hasattr(vb, 'setOptimumAxisRange'):
                    # not available in all versions; ignore if missing
                    vb.setOptimumAxisRange()
            except Exception:
                pass
            
            # Add grid
            self.calibration_chart.showGrid(x=True, y=True, alpha=0.3)
            
            # Initialize deadzone visualization
            self.min_deadzone_rect = None
            self.max_deadzone_rect = None
            self.min_deadzone = 0
            self.max_deadzone = 0
            
            # Set up the curve data with callback
            self.draggable_plot.set_curve_data(self.curve_x, self.curve_y, self.on_curve_points_changed)
            
            # Disable chart dragging/zooming
            self.calibration_chart.setMouseEnabled(x=False, y=False)
            
            chart_layout.addWidget(self.calibration_chart)
            
            # Add live response dot with persistent PlotDataItem for smooth updates
            # pyqtgraph recommends updating existing items rather than re-adding new ones
            try:
                import pyqtgraph as pg
                self.response_dot = pg.PlotDataItem([], [], symbol='o', pen=None)  # pen=None = just the symbol
                self.response_dot.setSymbolSize(10)
                self.response_dot.setSymbolBrush('#ffffff')
                self.response_dot.setSymbolPen('#000000', width=1)
                self.response_dot.setZValue(1000)  # draw on top
                self.calibration_chart.addItem(self.response_dot)
            except Exception:
                self.response_dot = None
            
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
                
                # Update existing items without clearing (preserves overlays/response dot)
                if getattr(self.draggable_plot, 'curve_line', None) is None:
                    self.draggable_plot.curve_line = self.draggable_plot.plot_widget.plot(
                        self.curve_x, self.curve_y,
                        pen=self.draggable_plot.pg.mkPen('#fba43b', width=2)
                    )
                    try:
                        self.draggable_plot.curve_line.setDownsampling(mode='peak')
                        self.draggable_plot.curve_line.setClipToView(True)
                    except Exception:
                        pass
                else:
                    try:
                        self.draggable_plot.curve_line.setData(self.curve_x, self.curve_y)
                    except Exception:
                        try:
                            self.draggable_plot.plot_widget.removeItem(self.draggable_plot.curve_line)
                        except Exception:
                            pass
                        self.draggable_plot.curve_line = self.draggable_plot.plot_widget.plot(
                            self.curve_x, self.curve_y,
                            pen=self.draggable_plot.pg.mkPen('#fba43b', width=2)
                        )

                if getattr(self.draggable_plot, 'scatter', None) is None:
                    self.draggable_plot.scatter = self.draggable_plot.pg.ScatterPlotItem(
                        x=self.curve_x, y=self.curve_y,
                        symbol='o', symbolBrush='#00ff00', symbolSize=12,
                        pen=self.draggable_plot.pg.mkPen('#00ff00', width=2)
                    )
                    self.draggable_plot.plot_widget.addItem(self.draggable_plot.scatter)
                else:
                    try:
                        self.draggable_plot.scatter.setData(self.curve_x, self.curve_y)
                    except Exception:
                        try:
                            self.draggable_plot.plot_widget.removeItem(self.draggable_plot.scatter)
                        except Exception:
                            pass
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
            
            # Resolve deadzone values (prefer live widget values)
            min_deadzone = getattr(self, 'min_deadzone', 0)
            max_deadzone = getattr(self, 'max_deadzone', 0)

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
                    min_deadzone = deadzone_values.get('min_deadzone', min_deadzone)
                    max_deadzone = deadzone_values.get('max_deadzone', max_deadzone)
                except Exception as e:
                    logger.debug(f"Error getting deadzone values: {e}")

            # Draw min deadzone rectangle - red barrier always visible when deadzone > 0
            if min_deadzone > 0 and hasattr(self, 'draggable_plot') and self.draggable_plot:
                self.min_deadzone_rect = self.draggable_plot.pg.LinearRegionItem(
                    values=[0, float(min_deadzone)],
                    orientation='vertical',
                    brush=self.draggable_plot.pg.mkBrush(200, 50, 50, 120),  # More opaque red
                    pen=self.draggable_plot.pg.mkPen(200, 50, 50, width=2),
                    movable=False  # Prevent accidental dragging
                )
                self.calibration_chart.addItem(self.min_deadzone_rect)

            # Draw max deadzone rectangle - red barrier always visible when deadzone > 0
            if max_deadzone > 0 and hasattr(self, 'draggable_plot') and self.draggable_plot:
                self.max_deadzone_rect = self.draggable_plot.pg.LinearRegionItem(
                    values=[100.0 - float(max_deadzone), 100.0],
                    orientation='vertical',
                    brush=self.draggable_plot.pg.mkBrush(200, 50, 50, 120),  # More opaque red
                    pen=self.draggable_plot.pg.mkPen(200, 50, 50, width=2),
                    movable=False  # Prevent accidental dragging
                )
                self.calibration_chart.addItem(self.max_deadzone_rect)

            # Persist and anchor endpoints
            self.min_deadzone = int(min_deadzone)
            self.max_deadzone = int(max_deadzone)
            try:
                if hasattr(self, 'draggable_plot') and self.draggable_plot:
                    lower_anchor = float(min_deadzone)
                    upper_anchor = 100.0 - float(max_deadzone)
                    if upper_anchor < lower_anchor:
                        upper_anchor = lower_anchor
                    self.draggable_plot.set_endpoints(lower_anchor, upper_anchor)
            except Exception:
                pass
                
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
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QCursor
        
        set_min_btn = QPushButton("Set Min")
        set_min_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        set_max_btn = QPushButton("Set Max")
        set_max_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_btn = QPushButton("Reset")
        reset_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
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
            text = f"Raw Input: {value}"
            if text != self._last_input_label:
                self.input_label.setText(text)
                self._last_input_label = text
        
        if self.input_progress:
            if value != self._last_input_progress:
                self.input_progress.setValue(value)
                self._last_input_progress = value
        
        # Calculate output based on current curve
        output_percentage = self.calculate_output_with_curve(value)
        
        if self.output_label:
            out_text = f"Output: {output_percentage:.1f}%"
            if out_text != self._last_output_label:
                self.output_label.setText(out_text)
                self._last_output_label = out_text
        
        if self.output_progress:
            out_int = int(output_percentage)
            if out_int != self._last_output_progress:
                self.output_progress.setValue(out_int)
                self._last_output_progress = out_int
        
        # Update the response dot - stays exactly on the orange curve line (deadzone-aware)
        try:
            if PYTQTGRAPH_AVAILABLE and self.response_dot:
                # 1) Normalize raw input to 0..1
                if self.max_value > self.min_value:
                    n = (value - self.min_value) / (self.max_value - self.min_value)
                else:
                    n = value / 65535
                n = 0.0 if n < 0.0 else (1.0 if n > 1.0 else n)

                # 2) Apply deadzones to get effective position in 0..1
                eff = apply_deadzones_norm(
                    v=n,
                    dz_min=getattr(self, 'min_deadzone', 0) / 100.0,
                    dz_max=getattr(self, 'max_deadzone', 0) / 100.0,
                )

                # 3) Map effective 0..1 into the anchored chart domain [min_dz .. 100-max_dz]
                anchor_min = float(getattr(self, 'min_deadzone', 0))
                anchor_max = 100.0 - float(getattr(self, 'max_deadzone', 0))
                span = anchor_max - anchor_min
                if span <= 0.0:
                    # Degenerate span: pin to anchor_min
                    x_pos = anchor_min
                else:
                    x_pos = anchor_min + eff * span

                # 4) Evaluate orange curve at that anchored X position for Y
                # Use the ACTUAL points being rendered by the draggable plot (anchored endpoints)
                if hasattr(self, 'draggable_plot') and self.draggable_plot:
                    px = self.draggable_plot.curve_x
                    py = self.draggable_plot.curve_y
                else:
                    px = self.curve_x
                    py = self.curve_y
                curve_points_01 = [(x/100.0, y/100.0) for x, y in zip(px, py)]
                y_pos = eval_curve(x_pos / 100.0, curve_points_01) * 100.0

                # 5) Move the dot (fast path)
                self.response_dot.setData([x_pos], [y_pos])
        except Exception:
            pass
    
    def calculate_output_with_curve(self, raw_value: int) -> float:
        """Calculate output percentage based on input and current curve using unified math."""
        try:
            # Use unified curve math for consistency
            rng = AxisRanges(self.min_value, self.max_value)
            dz = Deadzone(
                getattr(self, 'min_deadzone', 0) / 100.0,
                getattr(self, 'max_deadzone', 0) / 100.0
            )
            
            # Convert curve points to 0..1 range for eval_piecewise_linear
            curve_points = [(x/100.0, y/100.0) for x, y in zip(self.curve_x, self.curve_y)]
            
            # Use the unified mapping pipeline
            _, _, output_norm = map_raw(
                raw=float(raw_value),
                rmin=float(rng.raw_min),
                rmax=float(rng.raw_max),
                dz_min=dz.min_pct,
                dz_max=dz.max_pct,
                curve_points=curve_points
            )
            
            # Convert back to percentage for UI display
            return output_norm * 100.0
            
        except Exception:
            # Fallback to linear if anything fails
            if self.max_value == self.min_value:
                return 0.0
            normalized = ((raw_value - self.min_value) / (self.max_value - self.min_value)) * 100
            return max(0.0, min(100.0, normalized))
    
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
        
        # Reset deadzones to zero when resetting response curve
        self.min_deadzone = 0
        self.max_deadzone = 0
        
        # Find and reset deadzone widget if available
        try:
            deadzone_widget = self._find_deadzone_widget()
            if deadzone_widget and hasattr(deadzone_widget, 'reset_deadzones'):
                deadzone_widget.reset_deadzones()
        except Exception as e:
            logger.debug(f"Could not reset deadzone widget: {e}")
        
        # Update the chart if available
        if hasattr(self, 'draggable_plot') and self.draggable_plot:
            self.draggable_plot.set_curve_data(self.curve_x, self.curve_y, self.on_curve_points_changed)
        
        # Update deadzone visualization to remove red barriers
        self.update_deadzone_visualization()
        
        # Re-add the response dot after clearing the chart
        self._ensure_response_dot()
        
        self.emit_calibration_update()
        # logger.info(f"Reset calibration for {self.pedal_name}")
    
    def set_deadzone_values(self, min_deadzone: int, max_deadzone: int):
        """Set deadzone values and update visualization immediately."""
        self.min_deadzone = min_deadzone
        self.max_deadzone = max_deadzone
        # Immediate visualization update - no delays or debouncing
        try:
            from PyQt6.QtCore import QTimer
            # Use QTimer.singleShot(0) to ensure this runs on the next event loop cycle
            # This prevents any blocking and ensures immediate visual feedback
            QTimer.singleShot(0, self.update_deadzone_visualization)
        except:
            # Fallback to direct call if timer fails
            self.update_deadzone_visualization()
    
    def _find_deadzone_widget(self):
        """Find the deadzone widget for this pedal."""
        try:
            if hasattr(self.parent(), 'layout') and self.parent() is not None:
                layout = self.parent().layout()
                if layout:
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget():
                            widget = item.widget()
                            if hasattr(widget, 'pedal_name') and widget.pedal_name == self.pedal_name:
                                if hasattr(widget, '__class__') and 'DeadzoneWidget' in widget.__class__.__name__:
                                    return widget
        except Exception as e:
            logger.debug(f"Error finding deadzone widget: {e}")
        return None
    
    def _ensure_response_dot(self):
        """Ensure the response dot exists and is added to the chart."""
        try:
            if PYTQTGRAPH_AVAILABLE and hasattr(self, 'calibration_chart') and self.calibration_chart:
                # Remove existing dot if it exists
                if hasattr(self, 'response_dot') and self.response_dot:
                    try:
                        self.calibration_chart.removeItem(self.response_dot)
                    except:
                        pass
                
                # Create new response dot
                import pyqtgraph as pg
                self.response_dot = pg.PlotDataItem([], [], symbol='o', pen=None)  # pen=None = just the symbol
                self.response_dot.setSymbolSize(10)
                self.response_dot.setSymbolBrush('#ffffff')
                self.response_dot.setSymbolPen('#000000', width=1)
                self.response_dot.setZValue(1000)  # draw on top
                self.calibration_chart.addItem(self.response_dot)
                
                # Reset dot position cache
                self._last_dot_x = None
                self._last_dot_y = None
        except Exception as e:
            logger.debug(f"Error ensuring response dot: {e}")
    
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
        
        # Make sure the response dot remains and is repositioned to the new curve immediately
        try:
            self._ensure_response_dot()
            self.update_input_value(self.current_input)
        except Exception:
            pass
    
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

    def set_deadzone_values(self, min_deadzone: int, max_deadzone: int):
        """Set deadzone percentages and refresh overlays/dot constraints."""
        try:
            self.min_deadzone = max(0, min(50, int(min_deadzone)))
            self.max_deadzone = max(0, min(50, int(max_deadzone)))
            self.update_deadzone_visualization()
        except Exception:
            pass

    def cleanup(self):
        """Clean up Qt resources to prevent handle exhaustion."""
        try:
            # Clean up plot widget
            if hasattr(self, 'plot') and self.plot:
                if hasattr(self.plot, 'plot_widget'):
                    self.plot.plot_widget.deleteLater()
                self.plot = None

            # Clean up combo boxes
            for attr in ['curve_combo', 'curve_selector']:
                if hasattr(self, attr):
                    widget = getattr(self, attr)
                    if widget:
                        widget.clear()
                        widget.deleteLater()
                        setattr(self, attr, None)

            # Clean up buttons
            for attr in ['reset_btn', 'save_btn', 'load_btn']:
                if hasattr(self, attr):
                    widget = getattr(self, attr)
                    if widget:
                        widget.deleteLater()
                        setattr(self, attr, None)

            # Clean up labels and progress bars
            for attr in ['value_label', 'output_label', 'progress_bar', 'title_label']:
                if hasattr(self, attr):
                    widget = getattr(self, attr)
                    if widget:
                        widget.deleteLater()
                        setattr(self, attr, None)

        except Exception as e:
            logger.debug(f"Error cleaning up calibration widget: {e}")

    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None