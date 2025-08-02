import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import pyqtSignal, Qt
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
        self.input_progress.setMaximumHeight(20)
        self.input_progress.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 3px;
                text-align: center;
                color: #fefefe;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #e74c3c;
                border-radius: 2px;
            }
        """)
        
        self.output_label = QLabel("Calibrated Output: 0")
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
        self.output_progress.setMaximum(65535)
        self.output_progress.setValue(0)
        self.output_progress.setMaximumHeight(20)
        self.output_progress.setStyleSheet("""
            QProgressBar {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 3px;
                text-align: center;
                color: #fefefe;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
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
        chart_group = QGroupBox("Handbrake Response Curve")
        chart_group.setMinimumHeight(250)  # Make it bigger for the interactive chart
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
        
        # Add range labels at the top
        range_layout = QHBoxLayout()
        self.min_label = QLabel(f"Min: {self.min_value}")
        self.max_label = QLabel(f"Max: {self.max_value}")
        
        self.min_label.setStyleSheet("color: #fefefe; font-size: 11px;")
        self.max_label.setStyleSheet("color: #fefefe; font-size: 11px;")
        
        range_layout.addWidget(self.min_label)
        range_layout.addStretch()
        range_layout.addWidget(self.max_label)
        
        chart_layout.addLayout(range_layout)
        
        # Try to create the interactive chart
        try:
            from ...chart_widgets import IntegratedCalibrationChart
            self.calibration_chart = IntegratedCalibrationChart(
                chart_layout,
                self.handbrake_name,
                self.on_chart_point_moved
            )
            logger.info(f"Created IntegratedCalibrationChart for {self.handbrake_name}")
        except ImportError:
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
                
                # Add grid
                self.calibration_chart.showGrid(x=True, y=True, alpha=0.3)
                
                # Create initial linear curve
                x = [0, 25, 50, 75, 100]
                y = [0, 25, 50, 75, 100]
                self.calibration_chart.plot(x, y, pen=pg.mkPen('#e74c3c', width=2), symbol='o', symbolBrush='#e74c3c')
                
                chart_layout.addWidget(self.calibration_chart)
                logger.info(f"Created pyqtgraph chart for {self.handbrake_name}")
            except ImportError:
                # Fallback to simple visualization
                chart_placeholder = QLabel("📈 Interactive Chart\n(Requires pyqtgraph)\n\nUse curve selector below\nto choose response type")
                chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chart_placeholder.setMinimumHeight(180)
                chart_placeholder.setStyleSheet("""
                    QLabel {
                        color: #bdc3c7;
                        font-size: 12px;
                        background-color: #252525;
                        border: 1px solid #444444;
                        border-radius: 4px;
                        padding: 10px;
                    }
                """)
                chart_layout.addWidget(chart_placeholder)
                self.calibration_chart = chart_placeholder
                logger.warning(f"No charting library available for {self.handbrake_name}")
        
        chart_group.setLayout(chart_layout)
        parent_layout.addWidget(chart_group)
    
    def create_calibration_controls(self, parent_layout):
        """Create calibration control buttons."""
        controls_layout = QHBoxLayout()
        
        set_min_btn = QPushButton("Set Min")
        set_min_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        set_min_btn.clicked.connect(self.set_min_value)
        
        set_max_btn = QPushButton("Set Max")
        set_max_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        set_max_btn.clicked.connect(self.set_max_value)
        
        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        reset_btn.clicked.connect(self.reset_calibration)
        
        controls_layout.addWidget(set_min_btn)
        controls_layout.addWidget(set_max_btn)
        controls_layout.addWidget(reset_btn)
        controls_layout.addStretch()
        
        parent_layout.addLayout(controls_layout)
    
    def update_input_value(self, value: int):
        """Update the current input value and displays."""
        self.current_input = value
        
        if self.input_progress:
            self.input_progress.setValue(value)
        
        if self.input_label:
            self.input_label.setText(f"Raw Input: {value}")
        
        # Calculate calibrated output
        calibrated_value = self.apply_calibration(value)
        
        if self.output_progress:
            self.output_progress.setValue(calibrated_value)
        
        if self.output_label:
            self.output_label.setText(f"Calibrated Output: {calibrated_value}")
    
    def apply_calibration(self, raw_value: int) -> int:
        """Apply current calibration to raw value."""
        if self.max_value > self.min_value:
            # Normalize to 0-1 range
            normalized = (raw_value - self.min_value) / (self.max_value - self.min_value)
            normalized = max(0.0, min(1.0, normalized))
            return int(normalized * 65535)
        return raw_value
    
    def set_min_value(self):
        """Set the minimum calibration value to current input."""
        self.min_value = self.current_input
        self.min_label.setText(f"Min: {self.min_value}")
        self.emit_calibration_update()
        logger.info(f"Set handbrake min value to {self.min_value}")
    
    def set_max_value(self):
        """Set the maximum calibration value to current input."""
        self.max_value = self.current_input
        self.max_label.setText(f"Max: {self.max_value}")
        self.emit_calibration_update()
        logger.info(f"Set handbrake max value to {self.max_value}")
    
    def reset_calibration(self):
        """Reset calibration to default values."""
        self.min_value = 0
        self.max_value = 65535
        self.min_label.setText(f"Min: {self.min_value}")
        self.max_label.setText(f"Max: {self.max_value}")
        self.emit_calibration_update()
        logger.info("Reset handbrake calibration to defaults")
    
    def emit_calibration_update(self):
        """Emit calibration update signal."""
        calibration_data = {
            'min': self.min_value,
            'max': self.max_value,
            'curve': 'linear',
            'deadzone_min': 0,
            'deadzone_max': 0,
            'sensitivity': 1.0
        }
        self.calibration_updated.emit(calibration_data)
    
    def set_calibration_range(self, min_val: int, max_val: int):
        """Set calibration range from external source."""
        self.min_value = min_val
        self.max_value = max_val
        self.min_label.setText(f"Min: {self.min_value}")
        self.max_label.setText(f"Max: {self.max_value}")
    
    def get_calibration_data(self):
        """Get current calibration data."""
        return {
            'min': self.min_value,
            'max': self.max_value,
            'curve': 'linear',
            'deadzone_min': 0,
            'deadzone_max': 0,
            'sensitivity': 1.0
        }
    
    def set_deadzones(self, min_deadzone: int, max_deadzone: int):
        """Set deadzone values (compatibility method)."""
        # This method is called by the deadzone widget
        pass
    
    def on_chart_point_moved(self):
        """Handle when chart points are moved by user."""
        logger.debug(f"Chart point moved for {self.handbrake_name}")
        self.emit_calibration_update()
    
    def get_handbrake_curves(self):
        """Get available curve types for handbrake."""
        return ["Linear (Default)", "Progressive", "Aggressive", "Smooth"]
    
    def get_curve_points(self, curve_name: str):
        """Get the predefined points for a given curve type."""
        curve_definitions = {
            "Linear (Default)": [(0, 0), (25, 25), (50, 50), (75, 75), (100, 100)],
            "Progressive": [(0, 0), (25, 15), (50, 35), (75, 65), (100, 100)],
            "Aggressive": [(0, 0), (25, 45), (50, 70), (75, 85), (100, 100)],
            "Smooth": [(0, 0), (25, 20), (50, 45), (75, 70), (100, 100)]
        }
        return curve_definitions.get(curve_name, [(0, 0), (25, 25), (50, 50), (75, 75), (100, 100)])
    
    def update_chart_curve(self, curve_name: str):
        """Update the chart with a new curve."""
        if not self.calibration_chart:
            return
        
        curve_points = self.get_curve_points(curve_name)
        
        # If it's an IntegratedCalibrationChart, use set_points
        if hasattr(self.calibration_chart, 'set_points'):
            from PyQt6.QtCore import QPointF
            qpoints = [QPointF(x, y) for x, y in curve_points]
            self.calibration_chart.set_points(qpoints)
            logger.debug(f"Applied {len(qpoints)} points to {self.handbrake_name} chart")
        
        # If it's a pyqtgraph widget, clear and re-plot
        elif hasattr(self.calibration_chart, 'clear'):
            try:
                import pyqtgraph as pg
                self.calibration_chart.clear()
                x = [point[0] for point in curve_points]
                y = [point[1] for point in curve_points]
                self.calibration_chart.plot(x, y, pen=pg.mkPen('#e74c3c', width=2), symbol='o', symbolBrush='#e74c3c')
                logger.debug(f"Updated pyqtgraph chart with {curve_name} curve")
            except ImportError:
                pass