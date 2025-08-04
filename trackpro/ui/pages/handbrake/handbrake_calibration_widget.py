import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPointF
from PyQt6.QtGui import QMouseEvent
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

class HandbrakeCalibrationWidget(QWidget):
    calibration_updated = pyqtSignal(dict)
    
    def __init__(self, handbrake_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.handbrake_name = handbrake_name
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
        self.calibration_chart = None
        
        # Dragging state variables
        self.dragging = False
        self.dragging_point = None
        self.drag_start_pos = None
        
        # Curve data
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        self.curve_line = None
        self.scatter = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        group = QGroupBox(f"{self.handbrake_name.title()} Calibration")
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
        
        layout.addWidget(group)
    
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
                background-color: #e74c3c;
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
        """Create an interactive calibration chart for curve manipulation."""
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
        
        # Add range display
        range_layout = QHBoxLayout()
        range_layout.addStretch()
        range_layout.addLayout(chart_layout)
        
        # Try to create the interactive chart
        try:
            import pyqtgraph as pg
            self.calibration_chart = pg.PlotWidget()
            self.calibration_chart.setLabel('left', 'Output %')
            self.calibration_chart.setLabel('bottom', 'Input %')
            self.calibration_chart.setTitle(f'{self.handbrake_name.title()} Response Curve')
            self.calibration_chart.setBackground('#252525')
            self.calibration_chart.getAxis('left').setPen('#fefefe')
            self.calibration_chart.getAxis('bottom').setPen('#fefefe')
            self.calibration_chart.getAxis('left').setTextPen('#fefefe')
            self.calibration_chart.getAxis('bottom').setTextPen('#fefefe')
            
            # Set axis ranges
            self.calibration_chart.setXRange(0, 100)
            self.calibration_chart.setYRange(0, 100)
            
            # Add grid
            self.calibration_chart.showGrid(x=True, y=True, alpha=0.3)
            
            # Plot the line
            self.curve_line = self.calibration_chart.plot(self.curve_x, self.curve_y, pen=pg.mkPen('#e74c3c', width=2))
            
            # Create draggable scatter points with larger size for better interaction
            self.scatter = pg.ScatterPlotItem(x=self.curve_x, y=self.curve_y, 
                                            symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                            pen=pg.mkPen('#00ff00', width=2))
            self.calibration_chart.addItem(self.scatter)
            
            # Enable mouse interaction for the scatter plot
            self.scatter.setAcceptHoverEvents(True)
            self.scatter.setAcceptTouchEvents(True)
            self.scatter.setAcceptDrops(True)
            
            # Disable chart dragging/zooming but keep scatter points interactive
            self.calibration_chart.setMouseEnabled(x=False, y=False)
            
            # Override mouse events directly instead of using event filter
            self.calibration_chart.mousePressEvent = self.chart_mousePressEvent
            self.calibration_chart.mouseMoveEvent = self.chart_mouseMoveEvent
            self.calibration_chart.mouseReleaseEvent = self.chart_mouseReleaseEvent
            
            # Enable mouse tracking for better drag detection
            self.calibration_chart.setMouseTracking(True)
            
            chart_layout.addWidget(self.calibration_chart)
            logger.info(f"Created interactive pyqtgraph chart for {self.handbrake_name}")
        except ImportError:
            try:
                from ...chart_widgets import IntegratedCalibrationChart
                # Create a container widget for the chart
                chart_container = QWidget()
                chart_layout.addWidget(chart_container)
                self.calibration_chart = IntegratedCalibrationChart(chart_container)
                logger.info(f"Created IntegratedCalibrationChart for {self.handbrake_name}")
            except ImportError:
                chart_placeholder = QLabel("Chart not available - pyqtgraph not installed")
                chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chart_placeholder.setMinimumHeight(200)
                chart_layout.addWidget(chart_placeholder)
                logger.warning(f"No charting library available for {self.handbrake_name}")
        
        chart_group.setLayout(chart_layout)
        parent_layout.addWidget(chart_group)
    
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
        
        set_min_btn.clicked.connect(self.set_min_value)
        set_max_btn.clicked.connect(self.set_max_value)
        reset_btn.clicked.connect(self.reset_calibration)
        
        button_layout.addWidget(set_min_btn)
        button_layout.addWidget(set_max_btn)
        button_layout.addWidget(reset_btn)
        
        controls_layout.addLayout(range_layout)
        controls_layout.addLayout(button_layout)
        
        controls_group.setLayout(controls_layout)
        parent_layout.addWidget(controls_group)
    
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
        
        # Interpolate between curve points
        if normalized_input <= 0:
            return self.curve_y[0]
        elif normalized_input >= 100:
            return self.curve_y[-1]
        else:
            # Find the two points to interpolate between
            for i in range(len(self.curve_x) - 1):
                x1, y1 = self.curve_x[i], self.curve_y[i]
                x2, y2 = self.curve_x[i + 1], self.curve_y[i + 1]
                
                if x1 <= normalized_input <= x2:
                    # Linear interpolation
                    ratio = (normalized_input - x1) / (x2 - x1)
                    return y1 + ratio * (y2 - y1)
        
        return normalized_input  # Fallback to linear
    
    def apply_calibration(self, raw_value: int) -> int:
        """Apply calibration to raw input value."""
        output_percentage = self.calculate_output_with_curve(raw_value)
        return int((output_percentage / 100.0) * 65535)
    
    def set_min_value(self):
        """Set current input value as minimum."""
        self.min_value = self.current_input
        if self.min_label:
            self.min_label.setText(f"Min: {self.min_value}")
        self.emit_calibration_update()
    
    def set_max_value(self):
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
        self.emit_calibration_update()
    
    def emit_calibration_update(self):
        data = {
            'min_value': self.min_value,
            'max_value': self.max_value,
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
            'current_input': self.current_input,
            'curve_points': list(zip(self.curve_x, self.curve_y))
        }
    
    def set_deadzones(self, min_deadzone: int, max_deadzone: int):
        """Set deadzone values (not used in current implementation)."""
        pass
    
    def find_nearest_point(self, mouse_x: float, mouse_y: float) -> int:
        """Find the nearest control point to the mouse position."""
        if not self.scatter:
            return -1
        
        min_distance = float('inf')
        nearest_point = -1
        
        for i, (x, y) in enumerate(zip(self.curve_x, self.curve_y)):
            distance = ((mouse_x - x) ** 2 + (mouse_y - y) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_point = i
        
        # Use a larger threshold for chart coordinates (5% of chart size)
        threshold = 5.0  # 5% of 100 = 5 units
        logger.debug(f"Distance to nearest point: {min_distance:.1f}, threshold: {threshold}")
        
        if min_distance <= threshold:
            logger.debug(f"Found nearest point: {nearest_point} at distance {min_distance:.1f}")
            return nearest_point
        return -1
    
    def chart_mousePressEvent(self, event):
        """Handle mouse press events for the chart."""
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug("Left mouse button press detected")
            # Get mouse position in chart coordinates using the view box
            pos = event.pos()
            view_box = self.calibration_chart.getViewBox()
            chart_pos = view_box.mapSceneToView(view_box.mapFromParent(pos))
            
            logger.debug(f"Mouse press at screen pos ({pos.x()}, {pos.y()}) -> chart pos ({chart_pos.x():.1f}, {chart_pos.y():.1f})")
            
            # Find nearest point
            nearest_point = self.find_nearest_point(chart_pos.x(), chart_pos.y())
            logger.debug(f"Nearest point: {nearest_point}")
            
            if nearest_point >= 0:
                self.dragging = True
                self.dragging_point = nearest_point
                self.drag_start_pos = chart_pos
                logger.debug(f"Started dragging point {nearest_point}")
                event.accept()
                return True
            else:
                logger.debug("No nearby point found")
        
        # If we didn't handle it, pass to parent
        super(self.calibration_chart.__class__, self.calibration_chart).mousePressEvent(event)
        return False
    
    def constrain_point_position(self, point_index, x, y):
        """Constrain a point's position to prevent crossing over other points."""
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
        
        # Constrain x position
        min_x = max(left_points) if left_points else 0
        max_x = min(right_points) if right_points else 100
        
        # Apply constraints with a small buffer
        buffer = 2.0  # 2% buffer to prevent overlap
        constrained_x = max(min_x + buffer, min(max_x - buffer, x))
        
        # Constrain y to reasonable bounds
        constrained_y = max(0, min(100, y))
        
        return constrained_x, constrained_y

    def chart_mouseMoveEvent(self, event):
        """Handle mouse move events for the chart."""
        if self.dragging and self.dragging_point is not None:
            logger.debug("Mouse move while dragging")
            # Get mouse position in chart coordinates
            pos = event.pos()
            view_box = self.calibration_chart.getViewBox()
            chart_pos = view_box.mapSceneToView(view_box.mapFromParent(pos))
            
            # Constrain to chart bounds (0-100)
            x = max(0, min(100, chart_pos.x()))
            y = max(0, min(100, chart_pos.y()))
            
            logger.debug(f"Mouse move while dragging: ({x:.1f}, {y:.1f})")
            
            # Apply constraints to prevent crossing over other dots
            constrained_x, constrained_y = self.constrain_point_position(self.dragging_point, x, y)
            
            # Update the curve data directly using the dragging_point index
            if self.dragging_point < len(self.curve_x):
                self.curve_x[self.dragging_point] = constrained_x
                self.curve_y[self.dragging_point] = constrained_y
                
                # Update the scatter plot
                self.scatter.setData(self.curve_x, self.curve_y)
                
                # Update the line
                self.curve_line.setData(self.curve_x, self.curve_y)
                
                logger.debug(f"Dragged point {self.dragging_point} to ({constrained_x:.1f}, {constrained_y:.1f})")
            
            event.accept()
            return True
        else:
            logger.debug("Mouse move but not dragging")
        
        # If we didn't handle it, pass to parent
        super(self.calibration_chart.__class__, self.calibration_chart).mouseMoveEvent(event)
        return False
    
    def chart_mouseReleaseEvent(self, event):
        """Handle mouse release events for the chart."""
        if self.dragging:
            logger.debug("Mouse button release while dragging")
            # Stop dragging
            self.dragging = False
            self.dragging_point = None
            self.drag_start_pos = None
            self.emit_calibration_update()
            logger.debug("Stopped dragging")
            event.accept()
            return True
        else:
            logger.debug("Mouse button release but not dragging")
        
        # If we didn't handle it, pass to parent
        super(self.calibration_chart.__class__, self.calibration_chart).mouseReleaseEvent(event)
        return False
    
    def get_handbrake_curves(self):
        """Get available curves for handbrake."""
        return ["Linear (Default)", "Progressive", "Threshold"]
    
    def get_curve_points(self, curve_name: str):
        """Get the points for a specific curve."""
        curve_definitions = {
            "Linear (Default)": [(0, 0), (25, 25), (50, 50), (75, 75), (100, 100)],
            "Progressive": [(0, 0), (25, 15), (50, 35), (75, 65), (100, 100)],
            "Threshold": [(0, 0), (10, 5), (25, 15), (50, 45), (75, 80), (100, 100)]
        }
        return curve_definitions.get(curve_name, curve_definitions["Linear (Default)"])
    
    def update_chart_curve(self, curve_name: str):
        """Update the chart with a new curve."""
        curve_points = self.get_curve_points(curve_name)
        
        # Extract x and y coordinates
        x = [point[0] for point in curve_points]
        y = [point[1] for point in curve_points]
        
        # Update curve data
        self.curve_x = x
        self.curve_y = y
        
        # Update chart if available
        if self.calibration_chart and hasattr(self.calibration_chart, 'clear'):
            try:
                import pyqtgraph as pg
                
                # Clear existing items
                self.calibration_chart.clear()
                
                # Plot the line
                self.curve_line = self.calibration_chart.plot(x, y, pen=pg.mkPen('#e74c3c', width=2))
                
                # Create new draggable scatter points
                self.scatter = pg.ScatterPlotItem(x=x, y=y, 
                                                symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                                pen=pg.mkPen('#00ff00', width=2))
                self.calibration_chart.addItem(self.scatter)
                
                # Reinstall mouse event handlers
                self.calibration_chart.mousePressEvent = self.chart_mousePressEvent
                self.calibration_chart.mouseMoveEvent = self.chart_mouseMoveEvent
                self.calibration_chart.mouseReleaseEvent = self.chart_mouseReleaseEvent
                
                logger.debug(f"Applied {len(x)} points to {self.handbrake_name} chart")
            except ImportError:
                pass
        
        self.emit_calibration_update()