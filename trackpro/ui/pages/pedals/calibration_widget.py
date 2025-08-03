import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QProgressBar, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPointF
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

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
        
        # Dragging state
        self.dragging = False
        self.dragging_point = None
        
        # Curve data
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        self.curve_line = None
        self.scatter = None
        
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
            import pyqtgraph as pg
            self.calibration_chart = pg.PlotWidget()
            self.calibration_chart.setLabel('left', 'Output %')
            self.calibration_chart.setLabel('bottom', 'Input %')
            self.calibration_chart.setTitle(f'{self.pedal_name.title()} Response Curve')
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
            self.curve_line = self.calibration_chart.plot(self.curve_x, self.curve_y, pen=pg.mkPen('#fba43b', width=2))
            
            # Create draggable scatter points
            self.scatter = pg.ScatterPlotItem(x=self.curve_x, y=self.curve_y, 
                                            symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                            pen=pg.mkPen('#00ff00', width=2))
            self.calibration_chart.addItem(self.scatter)
            
            # Disable chart dragging/zooming
            self.calibration_chart.setMouseEnabled(x=False, y=False)
            
            # Install event filter
            self.calibration_chart.installEventFilter(self)
            logger.debug(f"🔍 INSTALLED event filter on {self.pedal_name} chart")
            
            # Test if event filter is working by adding a simple mouse press handler
            self.calibration_chart.mousePressEvent = lambda event: logger.debug(f"🔍 MOUSE PRESS EVENT on {self.pedal_name} chart: {event.button()}")
            
            chart_layout.addWidget(self.calibration_chart)
            logger.info(f"Created pyqtgraph chart for {self.pedal_name}")
        except ImportError:
            chart_placeholder = QLabel("Chart not available - pyqtgraph not installed")
            chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_placeholder.setMinimumHeight(200)
            chart_layout.addWidget(chart_placeholder)
            logger.warning(f"No charting library available for {self.pedal_name}")
        
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
        self.emit_calibration_update()
    
    def on_curve_changed(self, curve_name: str):
        logger.info(f"Curve changed for {self.pedal_name}: {curve_name}")
        
        # Get the points for this curve
        curve_points = self.get_curve_points(curve_name)
        
        # Apply to chart if available
        if self.calibration_chart and hasattr(self.calibration_chart, 'clear'):
            try:
                import pyqtgraph as pg
                
                # Extract x and y coordinates
                x = [point[0] for point in curve_points]
                y = [point[1] for point in curve_points]
                
                # Update curve data
                self.curve_x = x
                self.curve_y = y
                
                # Clear existing items
                self.calibration_chart.clear()
                
                # Plot the line
                self.curve_line = self.calibration_chart.plot(x, y, pen=pg.mkPen('#fba43b', width=2))
                
                # Create new draggable scatter points
                self.scatter = pg.ScatterPlotItem(x=x, y=y, 
                                                symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                                pen=pg.mkPen('#00ff00', width=2))
                self.calibration_chart.addItem(self.scatter)
                
                # Reinstall event filter
                self.calibration_chart.installEventFilter(self)
                
                logger.debug(f"Applied {len(x)} points to {self.pedal_name} chart")
            except ImportError:
                pass
        
        self.emit_calibration_update()
    
    def find_nearest_point(self, mouse_x: float, mouse_y: float) -> int:
        """Find the nearest control point to the mouse position."""
        logger.debug(f"🔍 FIND_NEAREST: mouse=({mouse_x:.2f}, {mouse_y:.2f})")
        
        if not self.scatter:
            logger.debug("🔍 No scatter plot available")
            return -1
        
        min_distance = float('inf')
        nearest_point = -1
        
        logger.debug(f"🔍 Current curve points: {list(zip(self.curve_x, self.curve_y))}")
        
        for i, (x, y) in enumerate(zip(self.curve_x, self.curve_y)):
            distance = ((mouse_x - x) ** 2 + (mouse_y - y) ** 2) ** 0.5
            logger.debug(f"🔍 Point {i}: ({x}, {y}) - distance: {distance:.2f}")
            if distance < min_distance:
                min_distance = distance
                nearest_point = i
        
        # Use a reasonable threshold for chart coordinates
        threshold = 10.0  # 10% of chart size
        logger.debug(f"🔍 Min distance: {min_distance:.2f}, threshold: {threshold}")
        
        if min_distance <= threshold:
            logger.debug(f"🔍 Found nearest point: {nearest_point}")
            return nearest_point
        else:
            logger.debug(f"🔍 No point within threshold")
            return -1
    
    def eventFilter(self, obj, event):
        """Handle mouse events for dragging points."""
        # Debug: Log all events - this should show up for ANY event
        logger.debug(f"🔍 EVENT: obj={type(obj).__name__}, event_type={event.type()}, dragging={self.dragging}")
        
        # Check if this is the right object
        if obj == self.calibration_chart:
            logger.debug(f"🔍 CORRECT OBJECT: {self.pedal_name} chart")
        else:
            logger.debug(f"🔍 WRONG OBJECT: expected calibration_chart, got {type(obj).__name__}")
        
        if obj == self.calibration_chart and hasattr(self, 'calibration_chart'):
            try:
                import pyqtgraph as pg
                
                if event.type() == QEvent.Type.MouseButtonPress:
                    logger.debug("🔍 MOUSE PRESS DETECTED")
                    if event.button() == Qt.MouseButton.LeftButton:
                        logger.debug("🔍 LEFT BUTTON PRESS")
                        # Get mouse position in chart coordinates
                        pos = event.pos()
                        logger.debug(f"🔍 Raw mouse pos: ({pos.x()}, {pos.y()})")
                        
                        view_box = self.calibration_chart.getViewBox()
                        logger.debug(f"🔍 ViewBox: {view_box}")
                        
                        # Convert QPoint to QPointF for pyqtgraph compatibility
                        pos_f = QPointF(pos.x(), pos.y())
                        logger.debug(f"🔍 Converted to QPointF: ({pos_f.x()}, {pos_f.y()})")
                        
                        try:
                            chart_pos = view_box.mapSceneToView(view_box.mapFromParent(pos_f))
                            logger.debug(f"🔍 Chart coordinates: ({chart_pos.x():.2f}, {chart_pos.y():.2f})")
                        except Exception as e:
                            logger.error(f"🔍 Error in coordinate conversion: {e}")
                            return False
                        
                        # Find nearest point
                        nearest_point = self.find_nearest_point(chart_pos.x(), chart_pos.y())
                        logger.debug(f"🔍 Nearest point: {nearest_point}")
                        
                        if nearest_point >= 0:
                            logger.debug(f"🔍 STARTING DRAG for point {nearest_point}")
                            self.dragging = True
                            self.dragging_point = nearest_point
                            return True
                        else:
                            logger.debug("🔍 No nearby point found")
                    else:
                        logger.debug(f"🔍 Wrong button: {event.button()}")
                
                elif event.type() == QEvent.Type.MouseMove:
                    logger.debug(f"🔍 MOUSE MOVE - dragging={self.dragging}")
                    if self.dragging:
                        logger.debug("🔍 DRAGGING - processing move")
                        # Get mouse position in chart coordinates
                        pos = event.pos()
                        view_box = self.calibration_chart.getViewBox()
                        # Convert QPoint to QPointF for pyqtgraph compatibility
                        pos_f = QPointF(pos.x(), pos.y())
                        chart_pos = view_box.mapSceneToView(view_box.mapFromParent(pos_f))
                        
                        # Constrain to chart bounds (0-100)
                        x = max(0, min(100, chart_pos.x()))
                        y = max(0, min(100, chart_pos.y()))
                        logger.debug(f"🔍 Dragging to: ({x:.2f}, {y:.2f})")
                        
                        # Update the curve data
                        if self.dragging_point is not None and self.dragging_point < len(self.curve_x):
                            logger.debug(f"🔍 Updating point {self.dragging_point}")
                            self.curve_x[self.dragging_point] = x
                            self.curve_y[self.dragging_point] = y
                            
                            # Sort points by x-coordinate to maintain order
                            points = list(zip(self.curve_x, self.curve_y))
                            points.sort(key=lambda p: p[0])
                            self.curve_x, self.curve_y = zip(*points)
                            
                            # Update the scatter plot
                            self.scatter.setData(self.curve_x, self.curve_y)
                            
                            # Update the line
                            self.curve_line.setData(self.curve_x, self.curve_y)
                            logger.debug(f"🔍 Updated chart with new data")
                        
                        return True
                    else:
                        logger.debug("🔍 Mouse move but not dragging")
                
                elif event.type() == QEvent.Type.MouseButtonRelease:
                    logger.debug("🔍 MOUSE RELEASE")
                    if self.dragging:
                        logger.debug("🔍 STOPPING DRAG")
                        # Stop dragging
                        self.dragging = False
                        self.dragging_point = None
                        self.emit_calibration_update()
                        return True
                    else:
                        logger.debug("🔍 Mouse release but not dragging")
                
                else:
                    logger.debug(f"🔍 Other event type: {event.type()}")
                        
            except ImportError:
                logger.error("🔍 ImportError in eventFilter")
                pass
            except Exception as e:
                logger.error(f"🔍 Error in eventFilter: {e}")
        else:
            logger.debug(f"🔍 Event not from calibration chart: obj={type(obj).__name__}")
        
        return super().eventFilter(obj, event)
    
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