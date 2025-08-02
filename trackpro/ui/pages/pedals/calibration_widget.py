import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QProgressBar, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt
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
        self.input_progress.setMaximumHeight(20)
        self.input_progress.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 3px;
                text-align: center;
                color: #fefefe;
            }
            QProgressBar::chunk {
                background-color: #fba43b;
                border-radius: 2px;
            }
        """)
        
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_progress)
        
        # Output monitor (what the game sees)
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
        self.output_progress.setRange(0, 100)
        self.output_progress.setValue(0)
        self.output_progress.setMaximumHeight(20)
        self.output_progress.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 3px;
                text-align: center;
                color: #fefefe;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 2px;
            }
        """)
        
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
            from ...chart_widgets import IntegratedCalibrationChart
            self.calibration_chart = IntegratedCalibrationChart(
                chart_layout,
                self.pedal_name,
                self.on_chart_point_moved
            )
            logger.info(f"Created IntegratedCalibrationChart for {self.pedal_name}")
        except ImportError:
            try:
                import pyqtgraph as pg
                self.calibration_chart = pg.PlotWidget()
                self.calibration_chart.setLabel('left', 'Output %')
                self.calibration_chart.setLabel('bottom', 'Input %')
                self.calibration_chart.setTitle(f'{self.pedal_name.title()} Response Curve')
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
                background-color: #3498db;
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
        """
        
        set_min_btn.setMaximumHeight(28)
        set_max_btn.setMaximumHeight(28)
        reset_btn.setMaximumHeight(28)
        
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
        curve_group.setMaximumHeight(65)
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
        
        self.curve_selector = QComboBox()
        self.curve_selector.setMaximumHeight(28)
        self.curve_selector.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 4px 8px;
                color: #fefefe;
                font-size: 11px;
            }
            QComboBox:hover {
                border-color: #fba43b;
            }
            QComboBox::drop-down {
                border: none;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 4px;
                color: #fefefe;
                selection-background-color: #fba43b;
                selection-color: #252525;
            }
        """)
        curves = self.get_pedal_curves()
        self.curve_selector.addItems(curves)
        self.curve_selector.currentTextChanged.connect(self.on_curve_changed)
        
        # Initialize with default curve
        self.on_curve_changed("Linear (Default)")
        
        curve_layout.addWidget(self.curve_selector)
        curve_group.setLayout(curve_layout)
        parent_layout.addWidget(curve_group)
    
    def get_pedal_curves(self):
        if self.pedal_name == 'brake':
            return ["Linear (Default)", "Threshold", "Trail Brake", "Endurance", "Rally", "ABS Friendly"]
        elif self.pedal_name == 'throttle':
            return ["Linear (Default)", "Track Mode", "Turbo Lag", "NA Engine", "Feathering", "Progressive"]
        elif self.pedal_name == 'clutch':
            return ["Linear (Default)", "Quick Engage", "Heel-Toe", "Bite Point Focus"]
        else:
            return ["Linear (Default)", "Progressive", "Threshold"]
    
    def get_curve_points(self, curve_name: str):
        """Get the predefined points for a given curve type."""
        curve_definitions = {
            # Throttle curves
            "Linear (Default)": [(0, 0), (33, 33), (67, 67), (100, 100)],
            "Track Mode": [(0, 0), (25, 10), (50, 30), (75, 60), (100, 100)],
            "Turbo Lag": [(0, 0), (25, 5), (50, 15), (75, 40), (100, 100)],
            "NA Engine": [(0, 0), (25, 35), (50, 65), (75, 85), (100, 100)],
            "Feathering": [(0, 0), (20, 5), (40, 15), (60, 35), (80, 70), (100, 100)],
            "Progressive": [(0, 0), (25, 15), (50, 35), (75, 65), (100, 100)],
            
            # Brake curves
            "Threshold": [(0, 0), (10, 5), (25, 15), (50, 45), (75, 80), (100, 100)],
            "Trail Brake": [(0, 0), (15, 25), (35, 50), (60, 75), (85, 95), (100, 100)],
            "Endurance": [(0, 0), (20, 15), (40, 30), (60, 50), (80, 75), (100, 95)],
            "Rally": [(0, 0), (30, 20), (50, 45), (70, 80), (85, 95), (100, 100)],
            "ABS Friendly": [(0, 0), (20, 10), (35, 22), (50, 38), (65, 55), (80, 75), (100, 90)],
            
            # Clutch curves
            "Quick Engage": [(0, 0), (10, 5), (30, 20), (60, 85), (100, 100)],
            "Heel-Toe": [(0, 0), (25, 10), (50, 40), (75, 80), (100, 100)],
            "Bite Point Focus": [(0, 0), (15, 5), (40, 15), (60, 60), (80, 90), (100, 100)],
        }
        
        return curve_definitions.get(curve_name, [(0, 0), (33, 33), (67, 67), (100, 100)])
    
    def update_input_value(self, value: int):
        self.current_input = value
        if self.input_progress:
            self.input_progress.setValue(value)
        if self.input_label:
            self.input_label.setText(f"Raw Input: {value}")
        
        # Calculate output percentage with deadzone consideration
        output_percentage = self.calculate_output_with_deadzone(value)
        
        # Update output display
        if self.output_progress:
            self.output_progress.setValue(int(output_percentage))
        if self.output_label:
            self.output_label.setText(f"Output: {output_percentage:.0f}%")
        
        if self.calibration_chart and hasattr(self.calibration_chart, 'update_input_position'):
            if self.max_value > self.min_value:
                percentage = ((value - self.min_value) / (self.max_value - self.min_value)) * 100
                percentage = max(0.0, min(100.0, percentage))
                self.calibration_chart.update_input_position(percentage)
    
    def calculate_output_with_deadzone(self, raw_value: int) -> float:
        """Calculate the output percentage considering calibration and deadzone."""
        if self.max_value <= self.min_value:
            return 0.0
        
        # Convert raw value to input percentage
        input_percentage = ((raw_value - self.min_value) / (self.max_value - self.min_value)) * 100
        input_percentage = max(0.0, min(100.0, input_percentage))
        
        # Get deadzone values from chart if available
        min_deadzone = 0
        max_deadzone = 0
        if self.calibration_chart and hasattr(self.calibration_chart, 'min_deadzone'):
            min_deadzone = self.calibration_chart.min_deadzone
            max_deadzone = self.calibration_chart.max_deadzone
        
        # Apply deadzone logic
        if input_percentage <= min_deadzone:
            return 0.0
        elif input_percentage >= (100 - max_deadzone):
            return 100.0
        else:
            # Scale the usable range
            usable_range = 100.0 - min_deadzone - max_deadzone
            if usable_range > 0:
                scaled_input = ((input_percentage - min_deadzone) / usable_range) * 100.0
                return max(0.0, min(100.0, scaled_input))
            else:
                return input_percentage
    
    def set_current_as_min(self):
        self.min_value = self.current_input
        if self.min_label:
            self.min_label.setText(f"Min: {self.min_value}")
        self.emit_calibration_update()
    
    def set_current_as_max(self):
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
        if self.calibration_chart and hasattr(self.calibration_chart, 'set_points'):
            # Convert to QPointF objects
            from PyQt6.QtCore import QPointF
            qpoints = [QPointF(x, y) for x, y in curve_points]
            self.calibration_chart.set_points(qpoints)
            logger.debug(f"Applied {len(qpoints)} points to {self.pedal_name} chart")
        
        self.emit_calibration_update()
    
    def on_chart_point_moved(self):
        logger.debug(f"Chart point moved for {self.pedal_name}")
        self.emit_calibration_update()
    
    def emit_calibration_update(self):
        data = {
            'min_value': self.min_value,
            'max_value': self.max_value,
            'curve_type': self.curve_selector.currentText() if self.curve_selector else "Linear (Default)"
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
            'current_input': self.current_input
        }