from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QGroupBox, QMessageBox, QProgressBar, QToolTip,
                           QTabWidget, QComboBox, QSpinBox, QDialog, QDialogButtonBox, QStackedWidget, QRadioButton, QButtonGroup, QLineEdit)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries, QValueAxis
from PyQt5.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QPalette, QMouseEvent
import logging
from trackpro import __version__
import pygame
from .calibration import CalibrationWizard
import math

logger = logging.getLogger(__name__)

class DraggableChartView(QChartView):
    """Custom chart view that supports point dragging."""
    
    point_moved = pyqtSignal()  # Signal emitted when a point is moved
    
    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.dragging_point = None
        self.scatter_series = None
        self.line_series = None
        self.original_points = []  # Store original point order
    
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
                event.accept()
                return
                
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle point dragging."""
        if self.dragging_point is not None and self.scatter_series:
            value = self.chart().mapToValue(event.pos())
            
            # Get current points while maintaining order
            points = [self.scatter_series.at(i) for i in range(self.scatter_series.count())]
            
            # Calculate allowed x range for this point
            min_x = 0 if self.dragging_point == 0 else points[self.dragging_point - 1].x() + 1
            max_x = 100 if self.dragging_point == len(points) - 1 else points[self.dragging_point + 1].x() - 1
            
            # Constrain to valid range
            x = max(min_x, min(max_x, value.x()))
            y = max(0, min(100, value.y()))
            
            # Update only the dragged point
            points[self.dragging_point] = QPointF(x, y)
            
            # Update scatter series
            self.scatter_series.clear()
            for point in points:
                self.scatter_series.append(point)
            
            # Update line series
            if self.line_series:
                self.line_series.clear()
                for point in points:
                    self.line_series.append(point)
            
            self.point_moved.emit()
            event.accept()
            return
            
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle end of point drag."""
        if self.dragging_point is not None:
            self.dragging_point = None
            event.accept()
            return
            
        super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    """Main application window."""
    
    # Signals
    calibration_updated = pyqtSignal(str)  # Emits pedal name when calibration changes
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"TrackPro Configuration v{__version__}")
        self.setMinimumSize(1200, 800)
        
        # Set dark theme
        self.setup_dark_theme()
        
        # Create the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add calibration wizard button at the top
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
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.save_calibration_btn.clicked.connect(self.save_calibration)
        
        wizard_layout.addStretch()
        wizard_layout.addWidget(self.calibration_wizard_btn)
        wizard_layout.addSpacing(20)  # Add spacing between buttons
        wizard_layout.addWidget(self.save_calibration_btn)
        wizard_layout.addStretch()
        layout.addLayout(wizard_layout)
        
        # Create horizontal layout for pedals
        pedals_layout = QHBoxLayout()
        layout.addLayout(pedals_layout)
        
        # Initialize pedal data structures
        self._init_pedal_data()
        
        # Create pedal sections side by side
        for pedal in ['Throttle', 'Brake', 'Clutch']:
            pedal_widget = QWidget()
            pedal_layout = QVBoxLayout(pedal_widget)
            
            # Add pedal name as header
            header = QLabel(pedal)
            header.setStyleSheet("font-size: 16px; font-weight: bold;")
            header.setAlignment(Qt.AlignCenter)
            pedal_layout.addWidget(header)
            
            self.create_pedal_controls(pedal, pedal_layout)
            pedals_layout.addWidget(pedal_widget)
            
        # Make the layout stretch evenly
        pedals_layout.setStretch(0, 1)
        pedals_layout.setStretch(1, 1)
        pedals_layout.setStretch(2, 1)
        
    def _init_pedal_data(self):
        """Initialize data structures for all pedals."""
        self._pedal_data = {}
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
                'current_pos_series': None,
                'min_control': None,
                'max_control': None
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
                padding: 10px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 5px 0px 5px;
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
                padding: 5px;
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
        
        progress = QProgressBar()
        progress.setRange(0, 65535)
        input_layout.addWidget(progress)
        data['input_progress'] = progress
        
        label = QLabel("Raw Input: 0")
        input_layout.addWidget(label)
        data['input_label'] = label
        
        input_group.setLayout(input_layout)
        parent_layout.addWidget(input_group)
        
        # Calibration
        cal_group = QGroupBox("Calibration")
        cal_layout = QVBoxLayout()
        
        # Create chart with dark theme
        chart = QChart()
        chart.setTitle(f"{pedal_name} Input/Output Mapping")
        chart.setBackgroundVisible(True)
        chart.setBackgroundBrush(QColor(53, 53, 53))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setPlotAreaBackgroundBrush(QColor(35, 35, 35))
        chart.setTitleBrush(QColor(255, 255, 255))
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().hide()
        
        # Create series for the line and points
        line_series = QLineSeries()
        line_series.setPen(QPen(QColor(0, 120, 255), 3))
        
        point_series = QScatterSeries()
        point_series.setMarkerSize(12)
        point_series.setColor(QColor(255, 0, 0))
        point_series.setBorderColor(QColor(255, 255, 255))
        
        # Create current position marker series
        current_pos_series = QScatterSeries()
        current_pos_series.setMarkerSize(8)
        current_pos_series.setColor(QColor(0, 255, 0))
        current_pos_series.setBorderColor(QColor(255, 255, 255))
        
        data['line_series'] = line_series
        data['point_series'] = point_series
        data['current_pos_series'] = current_pos_series
        
        # Create axes with grid
        axis_x = QValueAxis()
        axis_x.setRange(0, 100)
        axis_x.setTitleText("Input Value")
        axis_x.setGridLineVisible(True)
        axis_x.setMinorGridLineVisible(True)
        axis_x.setLabelsVisible(True)
        axis_x.setTickCount(6)
        axis_x.setLabelFormat("%.0f%%")
        axis_x.setTitleBrush(QColor(255, 255, 255))
        axis_x.setLabelsBrush(QColor(255, 255, 255))
        axis_x.setGridLinePen(QPen(QColor(70, 70, 70), 1))
        axis_x.setMinorGridLinePen(QPen(QColor(60, 60, 60), 1))
        
        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setTitleText("Output Value")
        axis_y.setGridLineVisible(True)
        axis_y.setMinorGridLineVisible(True)
        axis_y.setLabelsVisible(True)
        axis_y.setTickCount(6)
        axis_y.setLabelFormat("%.0f%%")
        axis_y.setTitleBrush(QColor(255, 255, 255))
        axis_y.setLabelsBrush(QColor(255, 255, 255))
        axis_y.setGridLinePen(QPen(QColor(70, 70, 70), 1))
        axis_y.setMinorGridLinePen(QPen(QColor(60, 60, 60), 1))
        
        # Add series to chart
        chart.addSeries(line_series)
        chart.addSeries(point_series)
        chart.addSeries(current_pos_series)
        
        # Attach axes to all series
        for series in [line_series, point_series, current_pos_series]:
            chart.setAxisX(axis_x, series)
            chart.setAxisY(axis_y, series)
        
        # Create draggable chart view
        chart_view = DraggableChartView(chart)
        chart_view.set_scatter_series(point_series, line_series)
        chart_view.point_moved.connect(lambda: self.on_point_moved(pedal_key))
        cal_layout.addWidget(chart_view)
        
        # Create default linear calibration points
        data['points'].clear()
        
        # Create 5 evenly spaced points from (0,0) to (100,100)
        for i in range(5):
            x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
            y = x  # Linear mapping for all pedals
            point = QPointF(x, y)
            data['points'].append(point)
            data['point_series'].append(point)
        
        # Update the curve with these points
        self.update_calibration_curve(pedal_key)
        
        # Calibration controls
        controls_layout = QHBoxLayout()
        
        # Add min/max calibration controls
        min_layout = QVBoxLayout()
        min_label = QLabel("Min: 0")
        set_min_btn = QPushButton("Set Min")
        set_min_btn.clicked.connect(lambda: self.set_current_as_min(pedal_key))
        min_layout.addWidget(min_label)
        min_layout.addWidget(set_min_btn)
        controls_layout.addLayout(min_layout)
        
        max_layout = QVBoxLayout()
        max_label = QLabel("Max: 65535")
        set_max_btn = QPushButton("Set Max")
        set_max_btn.clicked.connect(lambda: self.set_current_as_max(pedal_key))
        max_layout.addWidget(max_label)
        max_layout.addWidget(set_max_btn)
        controls_layout.addLayout(max_layout)
        
        # Add reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(lambda: self.reset_calibration(pedal_key))
        controls_layout.addWidget(reset_btn)
        
        # Store the calibration controls
        data['min_label'] = min_label
        data['max_label'] = max_label
        data['min_value'] = 0
        data['max_value'] = 65535
        
        # Add spacer
        controls_layout.addStretch()
        
        # Response curve selector
        curve_selector = QComboBox()
        curve_selector.addItems(["Linear", "Exponential", "Logarithmic", "S-Curve"])
        curve_selector.setCurrentText(data['curve_type'])
        curve_selector.currentTextChanged.connect(lambda t: self.on_curve_selector_changed(pedal_key, t))
        controls_layout.addWidget(curve_selector)
        
        # Store the curve selector for later access
        data['curve_selector'] = curve_selector
        
        cal_layout.addLayout(controls_layout)
        
        # Add curve management section
        curve_mgmt_layout = QHBoxLayout()
        
        # Curve name input
        curve_name_layout = QHBoxLayout()
        curve_name_layout.addWidget(QLabel("Curve Name:"))
        curve_name_input = QLineEdit()
        curve_name_input.setPlaceholderText("Enter curve name...")
        curve_name_layout.addWidget(curve_name_input)
        curve_mgmt_layout.addLayout(curve_name_layout)
        
        # Save button
        save_curve_btn = QPushButton("Save Curve")
        save_curve_btn.setMinimumWidth(100)  # Ensure text is fully visible
        save_curve_btn.clicked.connect(lambda: self.save_custom_curve(pedal_key, curve_name_input.text()))
        curve_mgmt_layout.addWidget(save_curve_btn)
        
        cal_layout.addLayout(curve_mgmt_layout)
        
        # Add delete button in its own centered layout
        delete_layout = QHBoxLayout()
        delete_curve_btn = QPushButton("Delete")
        delete_curve_btn.clicked.connect(lambda: self.delete_active_curve(pedal_key))
        
        # Improve button styling to ensure text is visible
        delete_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e9635f;
            }
        """)
        
        # Add the delete button to its layout with stretches on both sides to center it
        delete_layout.addStretch()
        delete_layout.addWidget(delete_curve_btn)
        delete_layout.addStretch()
        
        cal_layout.addLayout(delete_layout)
        
        # Store references to curve management controls
        data['curve_name_input'] = curve_name_input
        data['save_curve_btn'] = save_curve_btn
        data['delete_curve_btn'] = delete_curve_btn
        
        cal_group.setLayout(cal_layout)
        parent_layout.addWidget(cal_group)
        
        # Output Monitor
        output_group = QGroupBox("Output Monitor")
        output_layout = QVBoxLayout()
        
        progress = QProgressBar()
        progress.setRange(0, 65535)
        output_layout.addWidget(progress)
        data['output_progress'] = progress
        
        label = QLabel("Mapped Output: 0")
        output_layout.addWidget(label)
        data['output_label'] = label
        
        output_group.setLayout(output_layout)
        parent_layout.addWidget(output_group)
    
    def set_input_value(self, pedal: str, value: int):
        """Set the input value for a pedal."""
        data = self._pedal_data[pedal]
        data['input_value'] = value
        data['input_progress'].setValue(value)
        data['input_label'].setText(f"Raw Input: {value}")
        
        # Calculate input percentage based on calibration range
        min_val = data['min_value']
        max_val = data['max_value']
        
        # Only apply calibration to the output, not to the raw input display
        if max_val > min_val:
            # Map the raw input value to a percentage based on calibration range
            if value <= min_val:
                input_percentage = 0
            elif value >= max_val:
                input_percentage = 100
            else:
                input_percentage = ((value - min_val) / (max_val - min_val)) * 100
        else:
            input_percentage = 0
            
        input_percentage = max(0, min(100, input_percentage))  # Clamp to 0-100
        
        # Store the input percentage for use in set_output_value
        data['current_input_percentage'] = input_percentage
        
        # Get the calibration points
        points = sorted(data['points'], key=lambda p: p.x())
        if len(points) < 2:
            return
            
        # Calculate output percentage directly from the curve
        output_percentage = 0
        
        # Find the segment containing our input percentage
        for i in range(len(points) - 1):
            if points[i].x() <= input_percentage <= points[i + 1].x():
                segment_start = points[i]
                segment_end = points[i + 1]
                
                # Calculate position on the line segment
                if segment_start.x() == segment_end.x():
                    output_percentage = segment_start.y()
                else:
                    t = (input_percentage - segment_start.x()) / (segment_end.x() - segment_start.x())
                    output_percentage = segment_start.y() + t * (segment_end.y() - segment_start.y())
                break
        else:
            # If we're beyond the last point, use the last point's y value
            if input_percentage > points[-1].x():
                output_percentage = points[-1].y()
            elif input_percentage < points[0].x():
                output_percentage = points[0].y()
        
        output_percentage = max(0, min(100, output_percentage))  # Clamp to 0-100
        
        # Store the calculated output percentage
        data['current_output_percentage'] = output_percentage
        
        # Calculate and set the actual output value
        output_value = int((output_percentage / 100) * 65535)
        
        # Update the output value but not the marker (that's done in set_output_value)
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
    
    def set_output_value(self, pedal: str, value: int):
        """Set the output value for a pedal."""
        data = self._pedal_data[pedal]
        data['output_value'] = value
        data['output_progress'].setValue(value)
        data['output_label'].setText(f"Mapped Output: {value}")
        
        # Use the stored input percentage if available, otherwise recalculate
        if 'current_input_percentage' in data:
            input_percentage = data['current_input_percentage']
        else:
            # Calculate input percentage
            min_val = data['min_value']
            max_val = data['max_value']
            if max_val > min_val:
                input_percentage = ((data['input_value'] - min_val) / (max_val - min_val)) * 100
            else:
                input_percentage = 0
                
            input_percentage = max(0, min(100, input_percentage))  # Clamp to 0-100
        
        # ALWAYS recalculate the output percentage based on the calibration curve
        # This ensures the green dot is always on the blue line
        points = sorted(data['points'], key=lambda p: p.x())
        output_percentage = 0
        
        if len(points) >= 2:
            # Find the segment containing our input percentage
            for i in range(len(points) - 1):
                if points[i].x() <= input_percentage <= points[i + 1].x():
                    segment_start = points[i]
                    segment_end = points[i + 1]
                    
                    # Calculate position on the line segment
                    if segment_start.x() == segment_end.x():
                        output_percentage = segment_start.y()
                    else:
                        t = (input_percentage - segment_start.x()) / (segment_end.x() - segment_start.x())
                        output_percentage = segment_start.y() + t * (segment_end.y() - segment_start.y())
                    break
            else:
                # If we're beyond the last point, use the last point's y value
                if input_percentage > points[-1].x():
                    output_percentage = points[-1].y()
                elif input_percentage < points[0].x():
                    output_percentage = points[0].y()
        else:
            # No calibration points, use linear mapping
            output_percentage = input_percentage
        
        output_percentage = max(0, min(100, output_percentage))  # Clamp to 0-100
        
        # Store the calculated output percentage for consistency
        data['current_output_percentage'] = output_percentage
        
        # Update the current position marker to be exactly on the curve
        data['current_pos_series'].clear()
        data['current_pos_series'].append(input_percentage, output_percentage)
    
    def get_calibration_points(self, pedal: str):
        """Get calibration points for a pedal."""
        return self._pedal_data[pedal]['points']
    
    def set_calibration_points(self, pedal: str, points: list):
        """Set calibration points for a pedal."""
        self._pedal_data[pedal]['points'] = points
        self.update_calibration_curve(pedal)
    
    def get_curve_type(self, pedal: str):
        """Get the curve type for a pedal."""
        return self._pedal_data[pedal]['curve_type']
    
    def set_curve_type(self, pedal: str, curve_type: str):
        """Set the curve type for a pedal."""
        self._pedal_data[pedal]['curve_type'] = curve_type
    
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
        """Update the calibration curve for a pedal."""
        data = self._pedal_data[pedal]
        
        # Clear existing points and line
        data['point_series'].clear()
        data['line_series'].clear()
        
        # Sort points by x value to ensure proper line drawing
        sorted_points = sorted(data['points'], key=lambda p: p.x())
        
        # Add all points to both series to keep them in sync
        for point in sorted_points:
            data['point_series'].append(point)
            data['line_series'].append(point)
    
    def change_response_curve(self, pedal: str, curve_type: str):
        """Change the response curve type for a pedal."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        
        # Generate new points based on the curve type
        if curve_type != "Custom":
            # Clear existing points
            data['points'].clear()
            
            # Generate points based on curve type
            if curve_type == "Linear":
                # Linear curve: y = x
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = x  # Linear mapping
                    data['points'].append(QPointF(x, y))
            
            elif curve_type == "Exponential":
                # Exponential curve: y = x^2
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = (x / 100) ** 2 * 100  # x^2 mapping
                    data['points'].append(QPointF(x, y))
            
            elif curve_type == "Logarithmic":
                # Logarithmic curve: y = sqrt(x)
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = math.sqrt(x / 100) * 100  # sqrt(x) mapping
                    data['points'].append(QPointF(x, y))
            
            elif curve_type == "S-Curve":
                # S-Curve: combination of exponential and logarithmic
                # Using a sigmoid function: y = 1 / (1 + e^(-k*(x-50)))
                k = 0.1  # Controls the steepness of the curve
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    # Sigmoid function scaled to 0-100 range
                    y = 100 / (1 + math.exp(-k * (x - 50)))
                    data['points'].append(QPointF(x, y))
            
            # Update the curve
            self.update_calibration_curve(pedal)
        
        # Emit signal to update calibration
        self.calibration_updated.emit(pedal)
    
    def on_point_moved(self, pedal: str):
        """Handle when a calibration point is moved."""
        data = self._pedal_data[pedal]
        
        # Get points from the point series
        points = []
        for i in range(data['point_series'].count()):
            point = data['point_series'].at(i)
            points.append(QPointF(point.x(), point.y()))
        
        # Update the stored points
        data['points'] = points
        
        # Update the line to match exactly
        self.update_calibration_curve(pedal)
        
        # Get current input percentage (already calculated)
        input_percentage = data.get('current_input_percentage', 50)  # Default to 50% if not set
        
        # Recalculate output percentage based on new curve
        output_percentage = 0
        sorted_points = sorted(points, key=lambda p: p.x())
        
        if len(sorted_points) >= 2:
            # Find the segment containing our input percentage
            for i in range(len(sorted_points) - 1):
                if sorted_points[i].x() <= input_percentage <= sorted_points[i + 1].x():
                    segment_start = sorted_points[i]
                    segment_end = sorted_points[i + 1]
                    
                    # Calculate position on the line segment
                    if segment_start.x() == segment_end.x():
                        output_percentage = segment_start.y()
                    else:
                        t = (input_percentage - segment_start.x()) / (segment_end.x() - segment_start.x())
                        output_percentage = segment_start.y() + t * (segment_end.y() - segment_start.y())
                    break
            else:
                # If we're beyond the last point, use the last point's y value
                if input_percentage > sorted_points[-1].x():
                    output_percentage = sorted_points[-1].y()
                elif input_percentage < sorted_points[0].x():
                    output_percentage = sorted_points[0].y()
        else:
            # No calibration points, use linear mapping
            output_percentage = input_percentage
            
        output_percentage = max(0, min(100, output_percentage))  # Clamp to 0-100
        
        # Store the calculated output percentage
        data['current_output_percentage'] = output_percentage
        
        # Update the current position marker immediately
        data['current_pos_series'].clear()
        data['current_pos_series'].append(input_percentage, output_percentage)
        
        # Calculate and update the output value
        output_value = int((output_percentage / 100) * 65535)
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
        
        # Emit the calibration updated signal
        self.calibration_updated.emit(pedal)
    
    def show_message(self, title: str, message: str):
        """Display an information message box."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(f"TrackPro - {title}")
        msg.setText(message)
        msg.exec_()
    
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
        self.calibration_updated.emit(pedal)
    
    def set_pedal_available(self, pedal: str, available: bool):
        """Enable or disable UI elements for a pedal based on availability."""
        if pedal in self._pedal_data:
            # Get all UI elements for this pedal
            elements = self._pedal_data[pedal]
            
            # Set enabled state for all interactive elements
            for key, element in elements.items():
                # Skip non-widget elements like 'chart', 'range', etc.
                if key in ['min_value', 'max_value', 'points', 'curve_type', 'line_series', 'scatter_series']:
                    continue
                
                # Skip labels but update their appearance
                if key.endswith('_label'):
                    if not available:
                        element.setStyleSheet("color: #777777;")
                    else:
                        element.setStyleSheet("")
                    continue
                
                # Enable/disable interactive elements
                if hasattr(element, 'setEnabled'):
                    element.setEnabled(available)
            
            # Update progress bars with a visual indicator
            if 'input_progress' in elements:
                if not available:
                    elements['input_progress'].setStyleSheet("""
                        QProgressBar {
                            border: 1px solid #555555;
                            border-radius: 2px;
                            text-align: center;
                            background-color: #2d2d2d;
                        }
                        QProgressBar::chunk {
                            background-color: #555555;
                        }
                    """)
                else:
                    elements['input_progress'].setStyleSheet("")
            
            if 'output_progress' in elements:
                if not available:
                    elements['output_progress'].setStyleSheet("""
                        QProgressBar {
                            border: 1px solid #555555;
                            border-radius: 2px;
                            text-align: center;
                            background-color: #2d2d2d;
                        }
                        QProgressBar::chunk {
                            background-color: #555555;
                        }
                    """)
                else:
                    elements['output_progress'].setStyleSheet("")
            
            # Update the chart appearance
            if 'chart_view' in elements:
                chart_view = elements['chart_view']
                if not available:
                    chart_view.setEnabled(False)
                    chart_view.setOpacity(0.5)
                else:
                    chart_view.setEnabled(True)
                    chart_view.setOpacity(1.0)
            
            # Add a "Not Available" label if the pedal is not available
            if not available:
                if 'not_available_label' not in elements:
                    not_available_label = QLabel("Axis Not Available")
                    not_available_label.setStyleSheet("""
                        color: #ff5555;
                        font-weight: bold;
                        background-color: rgba(255, 85, 85, 0.1);
                        padding: 5px;
                        border-radius: 3px;
                    """)
                    not_available_label.setAlignment(Qt.AlignCenter)
                    
                    # Add to the layout
                    if 'group_box' in elements and hasattr(elements['group_box'], 'layout'):
                        elements['group_box'].layout().addWidget(not_available_label)
                    
                    # Store the label
                    self._pedal_data[pedal]['not_available_label'] = not_available_label
            else:
                # Remove the "Not Available" label if it exists
                if 'not_available_label' in elements:
                    elements['not_available_label'].deleteLater()
                    del self._pedal_data[pedal]['not_available_label']
    
    def reset_calibration(self, pedal: str):
        """Reset calibration to default values."""
        data = self._pedal_data[pedal]
        
        # Reset min/max values
        data['min_value'] = 0
        data['max_value'] = 65535
        data['min_label'].setText("Min: 0")
        data['max_label'].setText("Max: 65535")
        
        # Reset calibration points
        data['points'].clear()
        
        # Create default linear points
        for i in range(5):
            x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
            y = x  # Linear mapping
            point = QPointF(x, y)
            data['points'].append(point)
            
        # Update the curve
        self.update_calibration_curve(pedal)
        self.calibration_updated.emit(pedal)
    
    def add_debug_button(self, callback):
        """Add a debug button to the window."""
        # Create a button at the bottom of the window
        debug_btn = QPushButton("Debug Information")
        debug_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                font-size: 12px;
                padding: 5px 10px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        debug_btn.clicked.connect(callback)
        
        # Add to the main layout at the bottom
        self.centralWidget().layout().addWidget(debug_btn)
    
    def open_calibration_wizard(self):
        """Open the calibration wizard dialog."""
        wizard = CalibrationWizard(self)
        if wizard.exec_() == QDialog.Accepted:
            # Apply the calibration results
            for pedal in ['throttle', 'brake', 'clutch']:
                if pedal in wizard.results:
                    # Set the min/max values
                    min_val = wizard.results[pedal]['min']
                    max_val = wizard.results[pedal]['max']
                    self.set_calibration_range(pedal, min_val, max_val)
            
            # Notify that calibration has been updated
            for pedal in ['throttle', 'brake', 'clutch']:
                self.calibration_updated.emit(pedal)
            
            # Call the calibration wizard completed callback if it exists
            if hasattr(self, 'calibration_wizard_completed') and callable(self.calibration_wizard_completed):
                self.calibration_wizard_completed(wizard.results)
            
            self.show_message("Calibration Complete", "Pedal calibration has been successfully updated.")
    
    def save_calibration(self):
        """Save the current calibration settings."""
        try:
            # Emit calibration updated signals for all pedals to ensure latest data is saved
            for pedal in ['throttle', 'brake', 'clutch']:
                self.calibration_updated.emit(pedal)
                
                # Explicitly save the axis ranges to ensure they're persisted
                if hasattr(self, 'hardware'):
                    # Get the current min/max values
                    min_val, max_val = self.get_calibration_range(pedal)
                    
                    # Update hardware ranges
                    self.hardware.axis_ranges[pedal] = {
                        'min': min_val,
                        'max': max_val
                    }
                    
                    # Save the updated ranges
                    self.hardware.save_axis_ranges()
                    
                    # Get calibration points and curve type
                    points = self.get_calibration_points(pedal)
                    curve_type = self.get_curve_type(pedal)
                    
                    # Convert QPointF objects to tuples
                    point_tuples = [(p.x(), p.y()) for p in points]
                    
                    # Update hardware calibration
                    self.hardware.calibration[pedal] = {
                        'points': point_tuples,
                        'curve': curve_type
                    }
                    
                    # Save the calibration
                    self.hardware.save_calibration(self.hardware.calibration)
                    
                    logger.info(f"Saved {pedal} calibration: min={min_val}, max={max_val}, points={len(point_tuples)}, curve={curve_type}")
            
            # Show success message
            QMessageBox.information(
                self,
                "Calibration Saved",
                "Calibration settings have been saved successfully."
            )
            
            logger.info("Calibration saved manually by user from main UI")
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save calibration: {str(e)}"
            )
    
    def set_hardware(self, hardware):
        """Set the hardware reference for direct access to hardware functions."""
        self.hardware = hardware
        logger.info("Hardware reference set in MainWindow")
        
        # Update curve lists for each pedal
        self.refresh_curve_lists()
    
    def refresh_curve_lists(self):
        """Refresh the lists of available curves for all pedals."""
        if not hasattr(self, 'hardware'):
            logger.warning("Cannot refresh curve lists: hardware not accessible")
            return
            
        for pedal in ['throttle', 'brake', 'clutch']:
            self.refresh_curve_list(pedal)
    
    def refresh_curve_list(self, pedal):
        """Refresh the list of available curves for a specific pedal."""
        if not hasattr(self, 'hardware'):
            logger.warning(f"Cannot refresh curve list for {pedal}: hardware not accessible")
            return
            
        data = self._pedal_data[pedal]
        selector = data.get('curve_selector')
        
        if selector:
            # Remember current selection
            current_text = selector.currentText()
            logger.info(f"Current selection before refresh: '{current_text}'")
            
            # Get available curves
            curves = self.hardware.list_available_curves(pedal)
            
            # Log the available curves for debugging
            logger.info(f"Available curves for {pedal}: {curves}")
            
            # Remove all custom curves from the selector
            built_in_curves = ["Linear", "Exponential", "Logarithmic", "S-Curve"]
            for i in range(selector.count() - 1, -1, -1):
                if selector.itemText(i) not in built_in_curves:
                    selector.removeItem(i)
            
            if curves:
                # Add each curve individually for better debugging
                for curve in curves:
                    if selector.findText(curve) < 0:
                        selector.addItem(curve)
                        logger.info(f"Added curve to dropdown: '{curve}'")
                
                # Log the total count
                logger.info(f"Added {len(curves)} curves to dropdown for {pedal}")
                
                # Restore selection if possible
                index = selector.findText(current_text)
                if index >= 0:
                    selector.setCurrentIndex(index)
                    logger.info(f"Restored previous selection: '{current_text}'")
                else:
                    # If the previous selection is not available, select the first item
                    if selector.count() > 0:
                        selector.setCurrentIndex(0)
                        logger.info(f"Selected first curve: '{selector.currentText()}'")
            
            # Log all items in the selector for verification
            all_items = [selector.itemText(i) for i in range(selector.count())]
            logger.info(f"All items in dropdown after refresh: {all_items}")
        else:
            logger.warning(f"No curve selector found for {pedal}")
        
        # Force a repaint of the selector
        if selector:
            selector.update()
    
    def save_custom_curve(self, pedal, name):
        """Save the current curve as a custom curve."""
        if not name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Please enter a name for the curve."
            )
            return
            
        if not hasattr(self, 'hardware'):
            QMessageBox.warning(
                self,
                "Hardware Not Accessible",
                "Cannot save curve: hardware interface not accessible."
            )
            return
            
        # Get current points and curve type
        points = self.get_calibration_points(pedal)
        curve_type = self.get_curve_type(pedal)
        
        # Convert QPointF objects to tuples
        point_tuples = [(p.x(), p.y()) for p in points]
        
        # Get the save location for debugging
        curves_dir = self.hardware.get_pedal_curves_directory(pedal)
        save_path = curves_dir / f"{name}.json"
        
        # Save the curve
        if self.hardware.save_custom_curve(pedal, name, point_tuples, curve_type):
            # Show success message with the save location
            QMessageBox.information(
                self,
                "Curve Saved",
                f"Curve '{name}' has been saved successfully.\n\nSaved to: {save_path}"
            )
            
            # Clear the name input
            self._pedal_data[pedal]['curve_name_input'].clear()
            
            # Refresh the curve list immediately
            logger.info(f"Refreshing curve list after saving '{name}' for {pedal}")
            
            # Force a refresh of the curve list
            self.refresh_curve_list(pedal)
            
            # Update the curve selector dropdown to include the custom curve
            selector = self._pedal_data[pedal].get('curve_selector')
            if selector:
                # Check if the curve name already exists in the selector
                index = selector.findText(name)
                if index < 0:
                    # Add the curve name to the selector
                    selector.addItem(name)
                    logger.info(f"Added custom curve '{name}' to curve selector dropdown")
                # Select the curve in the selector
                selector.setCurrentText(name)
        else:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save curve '{name}'."
            )

    def _delayed_refresh_and_select(self, pedal, name):
        """Refresh the curve list and select the specified curve after a delay."""
        logger.info(f"Performing delayed refresh for {pedal} to find curve '{name}'")
        self.refresh_curve_list(pedal)
        
        # Update the curve selector dropdown
        selector = self._pedal_data[pedal].get('curve_selector')
        if selector:
            # Check if the curve name already exists in the selector
            index = selector.findText(name)
            if index < 0:
                # Add the curve name to the selector
                selector.addItem(name)
                logger.info(f"Added custom curve '{name}' to curve selector dropdown after delayed refresh")
            # Select the curve in the selector
            selector.setCurrentText(name)
    
    def load_custom_curve(self, pedal, name):
        """Load a custom curve."""
        if not name:
            QMessageBox.warning(
                self,
                "No Curve Selected",
                "Please select a curve to load."
            )
            return
            
        if not hasattr(self, 'hardware'):
            QMessageBox.warning(
                self,
                "Hardware Not Accessible",
                "Cannot load curve: hardware interface not accessible."
            )
            return
            
        # Load the curve
        curve_data = self.hardware.load_custom_curve(pedal, name)
        if not curve_data:
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Failed to load curve '{name}'."
            )
            return
            
        # Extract points and curve type
        points = curve_data.get('points', [])
        curve_type = curve_data.get('curve_type', 'Linear')
        
        # Convert tuples to QPointF objects
        qpoints = [QPointF(x, y) for x, y in points]
        
        # Update the UI
        self.set_calibration_points(pedal, qpoints)
        self.set_curve_type(pedal, curve_type)
        
        # Update the curve selector
        selector = self._pedal_data[pedal].get('curve_selector')
        if selector:
            index = selector.findText(curve_type)
            if index >= 0:
                selector.setCurrentIndex(index)
            else:
                # If the curve type is not in the selector, add it
                selector.addItem(curve_type)
                selector.setCurrentText(curve_type)
        
        # Notify that calibration has been updated
        self.calibration_updated.emit(pedal)
        
        QMessageBox.information(
            self,
            "Curve Loaded",
            f"Curve '{name}' has been loaded successfully."
        )
    
    def delete_custom_curve(self, pedal, name):
        """Delete a custom curve."""
        if not name:
            QMessageBox.warning(
                self,
                "No Curve Selected",
                "Please select a curve to delete."
            )
            return
            
        if not hasattr(self, 'hardware'):
            QMessageBox.warning(
                self,
                "Hardware Not Accessible",
                "Cannot delete curve: hardware interface not accessible."
            )
            return
            
        # Confirm deletion with a clear warning
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete curve '{name}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Delete the curve
        if self.hardware.delete_custom_curve(pedal, name):
            QMessageBox.information(
                self,
                "Curve Deleted",
                f"Curve '{name}' has been deleted successfully."
            )
            
            # Refresh the curve list
            self.refresh_curve_list(pedal)
            
            # Also remove the curve from the curve selector if it exists there
            selector = self._pedal_data[pedal].get('curve_selector')
            if selector:
                index = selector.findText(name)
                if index >= 0:
                    selector.removeItem(index)
                    logger.info(f"Removed deleted curve '{name}' from curve selector dropdown")
        else:
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Failed to delete curve '{name}'."
            )
    
    def on_curve_selector_changed(self, pedal: str, curve_name: str):
        """Handle when a curve is selected from the curve selector dropdown."""
        logger.info(f"Curve selector changed for {pedal} to '{curve_name}'")
        
        # Check if this is a built-in curve type
        built_in_curves = ["Linear", "Exponential", "Logarithmic", "S-Curve"]
        if curve_name in built_in_curves:
            # Use the existing method to change to a built-in curve type
            self.change_response_curve(pedal, curve_name)
            return
            
        # If it's not a built-in curve, it must be a custom curve
        # Try to load it from the custom curves
        if hasattr(self, 'hardware'):
            # Load the curve
            curve_data = self.hardware.load_custom_curve(pedal, curve_name)
            if curve_data:
                # Extract points and curve type
                points = curve_data.get('points', [])
                curve_type = curve_data.get('curve_type', 'Custom')
                
                # Convert tuples to QPointF objects
                qpoints = [QPointF(x, y) for x, y in points]
                
                # Update the UI
                self.set_calibration_points(pedal, qpoints)
                self.set_curve_type(pedal, 'Custom')  # Mark as custom curve
                
                # Notify that calibration has been updated
                self.calibration_updated.emit(pedal)
                
                logger.info(f"Loaded custom curve '{curve_name}' for {pedal} from selector")
            else:
                logger.error(f"Failed to load custom curve '{curve_name}' for {pedal}")
                # Revert to previous selection
                data = self._pedal_data[pedal]
                selector = data.get('curve_selector')
                if selector:
                    selector.blockSignals(True)
                    selector.setCurrentText(data['curve_type'])
                    selector.blockSignals(False)
    
    def delete_active_curve(self, pedal):
        """Delete the currently active curve for a pedal."""
        # Get the current curve type/name from the selector
        data = self._pedal_data[pedal]
        selector = data.get('curve_selector')
        
        if not selector:
            logger.error(f"Cannot delete curve: curve selector not found for {pedal}")
            return
            
        curve_name = selector.currentText()
        
        # Check if this is a built-in curve
        built_in_curves = ["Linear", "Exponential", "Logarithmic", "S-Curve"]
        if curve_name in built_in_curves:
            QMessageBox.warning(
                self,
                "Cannot Delete Built-in Curve",
                f"The curve '{curve_name}' is a built-in curve and cannot be deleted."
            )
            return
            
        # Now delete the custom curve
        self.delete_custom_curve(pedal, curve_name) 