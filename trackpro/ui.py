from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QGroupBox, QMessageBox, QProgressBar, QToolTip,
                           QTabWidget, QComboBox, QSpinBox, QDialog, QDialogButtonBox, QStackedWidget, QRadioButton, QButtonGroup)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries, QValueAxis
from PyQt5.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QPalette, QMouseEvent
import logging
from trackpro import __version__
import pygame
from .calibration import CalibrationWizard

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
        wizard_layout.addStretch()
        wizard_layout.addWidget(self.calibration_wizard_btn)
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
        curve_selector.currentTextChanged.connect(lambda t: self.change_response_curve(pedal_key, t))
        controls_layout.addWidget(curve_selector)
        
        cal_layout.addLayout(controls_layout)
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
        
        # Calculate input percentage
        min_val = data['min_value']
        max_val = data['max_value']
        if max_val > min_val:
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
        self._pedal_data[pedal]['curve_type'] = curve_type
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
            
        data['min_value'] = current_value
        data['min_label'].setText(f"Min: {current_value}")
        self.calibration_updated.emit(pedal)
    
    def set_current_as_max(self, pedal: str):
        """Set the current input value as the maximum for calibration."""
        data = self._pedal_data[pedal]
        current_value = data['input_value']
        
        # Don't allow max to be lower than min
        if current_value <= data['min_value']:
            self.show_message("Calibration Error", "Maximum value must be greater than minimum value")
            return
            
        data['max_value'] = current_value
        data['max_label'].setText(f"Max: {current_value}")
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