from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QGroupBox, QMessageBox, QProgressBar, QToolTip,
                           QTabWidget, QComboBox, QSpinBox, QDialog, QDialogButtonBox, QStackedWidget, QRadioButton, QButtonGroup, QLineEdit, QStatusBar, QGridLayout, QAction)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries, QAreaSeries
from PyQt5.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QPalette, QMouseEvent, QFont, QBrush
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
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QChartView.FullViewportUpdate)
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

# Completely new implementation for the plot graph system
class IntegratedCalibrationChart:
    """
    A completely redesigned chart system that guarantees the indicator dot
    is always perfectly aligned with the curve.
    """
    def __init__(self, parent_layout, pedal_name, on_curve_changed_callback):
        self.pedal_name = pedal_name
        self.on_curve_changed = on_curve_changed_callback
        self.input_percentage = 0
        self.points = []  # Calibration points
        self.min_deadzone = 0  # Minimum deadzone percentage
        self.max_deadzone = 0  # Maximum deadzone percentage
        
        # Create chart with dark theme
        self.chart = QChart()
        self.chart.setTitle(f"{pedal_name} Input/Output Mapping")
        self.chart.setBackgroundVisible(True)
        self.chart.setBackgroundBrush(QColor(53, 53, 53))
        self.chart.setPlotAreaBackgroundVisible(True)
        self.chart.setPlotAreaBackgroundBrush(QColor(35, 35, 35))
        self.chart.setTitleBrush(QColor(255, 255, 255))
        self.chart.setAnimationOptions(QChart.NoAnimation)  # Disable animations for precise positioning
        self.chart.legend().hide()
        
        # Create axes with grid
        self.axis_x = QValueAxis()
        self.axis_x.setRange(0, 100)
        self.axis_x.setTitleText("Input Value")
        self.axis_x.setGridLineVisible(True)
        self.axis_x.setMinorGridLineVisible(True)
        self.axis_x.setLabelsVisible(True)
        self.axis_x.setTickCount(6)
        self.axis_x.setLabelFormat("%.0f%%")
        self.axis_x.setTitleBrush(QColor(255, 255, 255))
        self.axis_x.setLabelsBrush(QColor(255, 255, 255))
        self.axis_x.setGridLinePen(QPen(QColor(70, 70, 70), 1))
        self.axis_x.setMinorGridLinePen(QPen(QColor(60, 60, 60), 1))
        
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setTitleText("Output Value")
        self.axis_y.setGridLineVisible(True)
        self.axis_y.setMinorGridLineVisible(True)
        self.axis_y.setLabelsVisible(True)
        self.axis_y.setTickCount(6)
        self.axis_y.setLabelFormat("%.0f%%")
        self.axis_y.setTitleBrush(QColor(255, 255, 255))
        self.axis_y.setLabelsBrush(QColor(255, 255, 255))
        self.axis_y.setGridLinePen(QPen(QColor(70, 70, 70), 1))
        self.axis_y.setMinorGridLinePen(QPen(QColor(60, 60, 60), 1))
        
        # Create a SINGLE path-based series for the curve that includes the indicator
        # This is key to ensuring the dot stays on the line
        self.curve_series = QLineSeries()
        self.curve_series.setPen(QPen(QColor(0, 120, 255), 3))
        self.chart.addSeries(self.curve_series)
        
        # Create a separate series for the draggable control points
        self.control_points_series = QScatterSeries()
        self.control_points_series.setMarkerSize(12)
        self.control_points_series.setColor(QColor(255, 0, 0))
        self.control_points_series.setBorderColor(QColor(255, 255, 255))
        self.chart.addSeries(self.control_points_series)
        
        # Create series for deadzone visualization
        self.min_deadzone_series = QAreaSeries()
        self.min_deadzone_pen = QPen(QColor(230, 100, 0, 150))
        self.min_deadzone_pen.setWidth(1)
        self.min_deadzone_series.setPen(self.min_deadzone_pen)
        self.min_deadzone_series.setBrush(QBrush(QColor(230, 100, 0, 80)))
        self.chart.addSeries(self.min_deadzone_series)
        
        self.max_deadzone_series = QAreaSeries()
        self.max_deadzone_pen = QPen(QColor(230, 100, 0, 150))
        self.max_deadzone_pen.setWidth(1)
        self.max_deadzone_series.setPen(self.max_deadzone_pen)
        self.max_deadzone_series.setBrush(QBrush(QColor(230, 100, 0, 80)))
        self.chart.addSeries(self.max_deadzone_series)
        
        # Create a separate series for the indicator dot that will be precisely positioned
        self.indicator_series = QScatterSeries()
        self.indicator_series.setMarkerSize(10)
        self.indicator_series.setColor(QColor(0, 255, 0))
        self.indicator_series.setBorderColor(QColor(255, 255, 255))
        self.indicator_series.setUseOpenGL(True)
        self.chart.addSeries(self.indicator_series)
        
        # Attach axes
        self.chart.setAxisX(self.axis_x, self.curve_series)
        self.chart.setAxisY(self.axis_y, self.curve_series)
        self.chart.setAxisX(self.axis_x, self.control_points_series)
        self.chart.setAxisY(self.axis_y, self.control_points_series)
        self.chart.setAxisX(self.axis_x, self.indicator_series)
        self.chart.setAxisY(self.axis_y, self.indicator_series)
        
        # Attach axes to deadzone series
        self.chart.setAxisX(self.axis_x, self.min_deadzone_series)
        self.chart.setAxisY(self.axis_y, self.min_deadzone_series)
        self.chart.setAxisX(self.axis_x, self.max_deadzone_series)
        self.chart.setAxisY(self.axis_y, self.max_deadzone_series)
        
        # Create the chart view
        self.chart_view = DraggableChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.set_scatter_series(self.control_points_series, self.curve_series)
        self.chart_view.point_moved.connect(self.on_control_point_moved)
        
        # Add to layout
        parent_layout.addWidget(self.chart_view)
        
        # Initialize with default points
        self.reset_to_linear()
    
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
        self.points = points.copy()
        self.update_chart()
    
    def get_points(self):
        """Get current calibration points."""
        return self.points.copy()
    
    def update_input_position(self, input_percentage):
        """
        Update the current input position and calculate the exact 
        corresponding output position on the curve.
        """
        self.input_percentage = max(0, min(100, input_percentage))
        self.update_indicator()
    
    def update_indicator(self):
        """Update the position of the green indicator dot to be exactly on the curve."""
        # Ensure we have valid points
        if len(self.points) < 2:
            return
        
        # Sort points by x-value for proper interpolation
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Find the output percentage for the current input
        output_percentage = self.calculate_output_for_input(self.input_percentage, sorted_points)
        
        # Update the indicator dot
        self.indicator_series.clear()
        self.indicator_series.append(self.input_percentage, output_percentage)
    
    def calculate_output_for_input(self, input_percentage, sorted_points=None):
        """Calculate the precise output percentage for a given input percentage."""
        if sorted_points is None:
            sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Handle edge cases
        if not sorted_points:
            return input_percentage
        
        if input_percentage <= sorted_points[0].x():
            return sorted_points[0].y()
        
        if input_percentage >= sorted_points[-1].x():
            return sorted_points[-1].y()
        
        # Find the segment containing our input percentage
        for i in range(len(sorted_points) - 1):
            if sorted_points[i].x() <= input_percentage <= sorted_points[i + 1].x():
                # Get the segment points
                p1 = sorted_points[i]
                p2 = sorted_points[i + 1]
                
                # Handle vertical segments
                if p1.x() == p2.x():
                    return p1.y()
                
                # Use precise linear interpolation to find the output
                t = (input_percentage - p1.x()) / (p2.x() - p1.x())
                return p1.y() + t * (p2.y() - p1.y())
        
        # Fallback - should not reach here with the edge case handling
        return input_percentage
    
    def update_chart(self):
        """Update the chart with current calibration points and deadzones."""
        # Clear series
        self.curve_series.clear()
        self.control_points_series.clear()
        
        # Sort points by x for proper curve drawing
        sorted_points = sorted(self.points, key=lambda p: p.x())
        
        # Add sorted points to both series
        for point in sorted_points:
            self.curve_series.append(point)
            self.control_points_series.append(point)
        
        # Update deadzone visualization
        self._update_deadzone_visualization()
        
        # Update the indicator to ensure it stays on the curve
        self.update_indicator()
    
    def _update_deadzone_visualization(self):
        """Update the visualization of min and max deadzones."""
        # Clear existing deadzone series
        min_lower_series = QLineSeries()
        min_upper_series = QLineSeries()
        
        max_lower_series = QLineSeries()
        max_upper_series = QLineSeries()
        
        # Visualize min deadzone if it's greater than 0
        if self.min_deadzone > 0:
            # Create vertical area from 0 to 100% output at min_deadzone
            min_lower_series.append(0, 0)
            min_lower_series.append(self.min_deadzone, 0)
            
            min_upper_series.append(0, 100)
            min_upper_series.append(self.min_deadzone, 100)
            
            self.min_deadzone_series.setLowerSeries(min_lower_series)
            self.min_deadzone_series.setUpperSeries(min_upper_series)
        else:
            # No min deadzone to display
            self.min_deadzone_series.setLowerSeries(None)
            self.min_deadzone_series.setUpperSeries(None)
        
        # Visualize max deadzone if it's greater than 0
        if self.max_deadzone > 0:
            # Create vertical area from 0 to 100% output at (100 - max_deadzone)
            max_lower_series.append(100 - self.max_deadzone, 0)
            max_lower_series.append(100, 0)
            
            max_upper_series.append(100 - self.max_deadzone, 100)
            max_upper_series.append(100, 100)
            
            self.max_deadzone_series.setLowerSeries(max_lower_series)
            self.max_deadzone_series.setUpperSeries(max_upper_series)
        else:
            # No max deadzone to display
            self.max_deadzone_series.setLowerSeries(None)
            self.max_deadzone_series.setUpperSeries(None)
    
    def on_control_point_moved(self):
        """Handle when a control point is moved by the user."""
        # Get updated points from the control points series
        updated_points = []
        for i in range(self.control_points_series.count()):
            point = self.control_points_series.at(i)
            updated_points.append(QPointF(point))
        
        # Update our internal points list
        self.points = updated_points
        
        # Update the curve
        self.update_chart()
        
        # Notify parent about the change
        if self.on_curve_changed:
            self.on_curve_changed()
            
    def get_output_value(self, scale=65535):
        """
        Get the current output value as an integer scaled to the given range.
        Default scale is 0-65535 (16-bit).
        """
        if len(self.points) < 2:
            # Use linear mapping if no valid curve
            output_percentage = self.input_percentage
        else:
            # Calculate output based on the curve
            output_percentage = self.calculate_output_for_input(self.input_percentage)
            
        # Scale to the desired range and return as integer
        return int((output_percentage / 100) * scale)
    
    def set_deadzones(self, min_deadzone, max_deadzone):
        """Set the deadzone values and update the chart."""
        self.min_deadzone = min_deadzone
        self.max_deadzone = max_deadzone
        self.update_chart()

class PasswordDialog(QDialog):
    """Dialog to request password before accessing protected features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add message label
        message_label = QLabel("Please enter the password to access Race Coach:")
        layout.addWidget(message_label)
        
        # Add password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_password(self):
        """Get the entered password."""
        return self.password_input.text()

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
        
        # Create menu bar
        self.create_menu_bar()
        
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
                background-color: #5DBF61;
            }
        """)
        self.save_calibration_btn.clicked.connect(self.save_calibration)
        
        # Add buttons to the layout
        wizard_layout.addWidget(self.calibration_wizard_btn)
        wizard_layout.addWidget(self.save_calibration_btn)
        wizard_layout.addStretch()
        layout.addLayout(wizard_layout)
        
        # Create a stacked widget for switching between screens
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create the main pedals screen
        pedals_screen = QWidget()
        pedals_layout = QVBoxLayout(pedals_screen)
        
        # Add pedal controls section
        pedals_section_layout = QHBoxLayout()
        pedals_layout.addLayout(pedals_section_layout)
        
        # Initialize pedal data
        self._init_pedal_data()
        
        # Create a widget for each pedal
        for pedal in ['throttle', 'brake', 'clutch']:
            pedal_widget = QWidget()
            pedal_widget.setObjectName(f"{pedal}_widget")
            pedal_layout = QVBoxLayout(pedal_widget)
            pedal_layout.setContentsMargins(5, 5, 5, 5)
            
            # Add pedal name as header
            header = QLabel(pedal)
            header.setStyleSheet("font-size: 16px; font-weight: bold;")
            header.setAlignment(Qt.AlignCenter)
            pedal_layout.addWidget(header)
            
            self.create_pedal_controls(pedal, pedal_layout)
            pedals_section_layout.addWidget(pedal_widget)
            
        # Make the layout stretch evenly
        pedals_section_layout.setStretch(0, 1)
        pedals_section_layout.setStretch(1, 1)
        pedals_section_layout.setStretch(2, 1)
        
        # Add the pedals screen to the stacked widget
        self.stacked_widget.addWidget(pedals_screen)
        
        # Add update notification label at the bottom
        self.update_notification = QLabel("")
        self.update_notification.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                padding: 5px;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                background-color: rgba(76, 175, 80, 0.1);
            }
        """)
        self.update_notification.setVisible(False)
        layout.addWidget(self.update_notification, 0, Qt.AlignLeft)
        
        # Create status bar with pedal connection indicator
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Add pedal connection indicator to status bar
        self.pedal_status_label = QLabel("Pedals: Not Connected")
        self.pedal_status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
                background-color: #FF5252;
                color: white;
            }
        """)
        self.statusBar.addPermanentWidget(self.pedal_status_label)
        
        # Add version information to status bar
        version_label = QLabel(f"Version: {__version__}")
        self.statusBar.addWidget(version_label)
        
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
                'position_indicator': None,  # Using the new CurvePositionIndicator
                'min_control': None,
                'max_control': None,
                'min_deadzone': 0,
                'max_deadzone': 0
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
                padding: 5px 10px;
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
                min-width: 200px;
                padding: 5px;
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
        
        # Create the integrated calibration chart - this replaces all the old chart code
        calibration_chart = IntegratedCalibrationChart(
            cal_layout, 
            pedal_name,
            lambda: self.on_point_moved(pedal_key)
        )
        
        # Store the chart in the pedal data
        data['calibration_chart'] = calibration_chart
        
        # Calibration controls
        controls_layout = QHBoxLayout()
        
        # Add min/max calibration controls
        min_layout = QVBoxLayout()
        min_label = QLabel("Min: 0")
        set_min_btn = QPushButton("Set Min")
        set_min_btn.clicked.connect(lambda: self.set_current_as_min(pedal_key))
        min_layout.addWidget(min_label)
        min_layout.addWidget(set_min_btn)
        
        # Remove fine-tuning buttons for min value
        controls_layout.addLayout(min_layout)
        
        max_layout = QVBoxLayout()
        max_label = QLabel("Max: 65535")
        set_max_btn = QPushButton("Set Max")
        set_max_btn.clicked.connect(lambda: self.set_current_as_max(pedal_key))
        max_layout.addWidget(max_label)
        max_layout.addWidget(set_max_btn)
        
        # Remove fine-tuning buttons for max value
        controls_layout.addLayout(max_layout)
        
        # Add reset button in a vertical layout for alignment
        reset_layout = QVBoxLayout()
        reset_label = QLabel("Reset Curve")
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(lambda: self.reset_calibration(pedal_key))
        reset_layout.addWidget(reset_label)
        reset_layout.addWidget(reset_btn)
        controls_layout.addLayout(reset_layout)
        
        # Add spacer
        controls_layout.addStretch()
        
        # Response curve selector in a vertical layout for alignment
        curve_layout = QVBoxLayout()
        curve_label = QLabel("Curve Type")
        curve_selector = QComboBox()
        curve_selector.addItems(["Linear", "Exponential", "Logarithmic", "S-Curve"])
        curve_selector.setCurrentText("Linear")
        curve_selector.setMinimumWidth(180) 
        curve_selector.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView {
                min-width: 220px;
                padding: 5px;
            }
        """)
        curve_selector.currentTextChanged.connect(lambda text: self.on_curve_selector_changed(pedal_key, text))
        curve_layout.addWidget(curve_label)
        curve_layout.addWidget(curve_selector)
        controls_layout.addLayout(curve_layout)
        
        # Store the calibration controls
        data['min_label'] = min_label
        data['max_label'] = max_label
        data['min_value'] = 0
        data['max_value'] = 65535
        data['curve_type_selector'] = curve_selector
        
        # First add the main controls layout to the calibration layout
        cal_layout.addLayout(controls_layout)
        
        # Add deadzone controls
        deadzone_group = QGroupBox("Deadzones (%)")
        deadzone_layout = QVBoxLayout()
        
        # Min deadzone controls
        min_deadzone_layout = QHBoxLayout()
        min_deadzone_label = QLabel("Min Deadzone:")
        min_deadzone_layout.addWidget(min_deadzone_label)
        
        min_deadzone_value = QLabel("0%")
        min_deadzone_value.setMinimumWidth(40)
        min_deadzone_layout.addWidget(min_deadzone_value)
        
        min_deadzone_minus = QPushButton("-")
        min_deadzone_minus.setFixedWidth(30)
        min_deadzone_minus.setStyleSheet("padding: 2px 5px;")
        min_deadzone_minus.clicked.connect(lambda: self.adjust_min_deadzone(pedal_key, -1))
        min_deadzone_layout.addWidget(min_deadzone_minus)
        
        min_deadzone_plus = QPushButton("+")
        min_deadzone_plus.setFixedWidth(30)
        min_deadzone_plus.setStyleSheet("padding: 2px 5px;")
        min_deadzone_plus.clicked.connect(lambda: self.adjust_min_deadzone(pedal_key, 1))
        min_deadzone_layout.addWidget(min_deadzone_plus)
        
        deadzone_layout.addLayout(min_deadzone_layout)
        
        # Max deadzone controls
        max_deadzone_layout = QHBoxLayout()
        max_deadzone_label = QLabel("Max Deadzone:")
        max_deadzone_layout.addWidget(max_deadzone_label)
        
        max_deadzone_value = QLabel("0%")
        max_deadzone_value.setMinimumWidth(40)
        max_deadzone_layout.addWidget(max_deadzone_value)
        
        max_deadzone_minus = QPushButton("-")
        max_deadzone_minus.setFixedWidth(30)
        max_deadzone_minus.setStyleSheet("padding: 2px 5px;")
        max_deadzone_minus.clicked.connect(lambda: self.adjust_max_deadzone(pedal_key, -1))
        max_deadzone_layout.addWidget(max_deadzone_minus)
        
        max_deadzone_plus = QPushButton("+")
        max_deadzone_plus.setFixedWidth(30)
        max_deadzone_plus.setStyleSheet("padding: 2px 5px;")
        max_deadzone_plus.clicked.connect(lambda: self.adjust_max_deadzone(pedal_key, 1))
        max_deadzone_layout.addWidget(max_deadzone_plus)
        
        deadzone_layout.addLayout(max_deadzone_layout)
        
        deadzone_group.setLayout(deadzone_layout)
        cal_layout.addWidget(deadzone_group)
        
        # Store deadzone controls in data for updating
        data['min_deadzone_value'] = min_deadzone_value
        data['max_deadzone_value'] = max_deadzone_value
        data['min_deadzone'] = 0
        data['max_deadzone'] = 0
        
        # Finalize the calibration group
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
        
        # Curve Management
        manager_group = QGroupBox("Curve Management")
        manager_layout = QGridLayout()
        
        # Curve Name Input
        name_label = QLabel("Curve Name:")
        manager_layout.addWidget(name_label, 0, 0)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter curve name...")
        manager_layout.addWidget(name_input, 0, 1, 1, 2)
        
        # Save Button
        save_btn = QPushButton("Save Curve")
        save_btn.clicked.connect(lambda: self.save_custom_curve(pedal_key, name_input.text()))
        manager_layout.addWidget(save_btn, 0, 3)
        
        # Curve Selector
        selector_label = QLabel("Saved Curves:")
        manager_layout.addWidget(selector_label, 1, 0)
        
        curve_list = QComboBox()
        curve_list.setMinimumWidth(180)
        curve_list.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView {
                min-width: 220px;
                padding: 5px;
            }
        """)
        manager_layout.addWidget(curve_list, 1, 1)
        
        # Load Button
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(lambda: self.load_custom_curve(pedal_key, curve_list.currentText()))
        manager_layout.addWidget(load_btn, 1, 2)
        
        # Delete Button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("background-color: #882222;")
        delete_btn.clicked.connect(lambda: self.delete_custom_curve(pedal_key, curve_list.currentText()))
        manager_layout.addWidget(delete_btn, 1, 3)
        
        # Store references for curve management
        data['curve_name_input'] = name_input
        data['saved_curves_selector'] = curve_list
        data['saved_curves_selector'].currentTextChanged.connect(
            lambda text: self.on_curve_selector_changed(pedal_key, text)
        )
        
        # Set up the layout
        manager_group.setLayout(manager_layout)
        parent_layout.addWidget(manager_group)
        
        # Store the QGroupBox for the pedal
        data['group_box'] = cal_group
    
    def set_input_value(self, pedal: str, value: int):
        """Set the input value for a pedal."""
        data = self._pedal_data[pedal]
        data['input_value'] = value
        data['input_progress'].setValue(value)
        data['input_label'].setText(f"Raw Input: {value}")
        
        # Calculate input percentage based on calibration range
        min_val = data['min_value']
        max_val = data['max_value']
        
        # Map the raw input value to a percentage based on calibration range
        if max_val > min_val:
            if value <= min_val:
                input_percentage = 0
            elif value >= max_val:
                input_percentage = 100
            else:
                input_percentage = ((value - min_val) / (max_val - min_val)) * 100
        else:
            input_percentage = 0
            
        input_percentage = max(0, min(100, input_percentage))  # Clamp to 0-100
        
        # Update the integrated chart with the new input position
        # This handles the green dot position and output calculation in one step
        calibration_chart = data['calibration_chart']
        calibration_chart.update_input_position(input_percentage)
        
        # Get the output value directly from the chart
        output_value = calibration_chart.get_output_value()
        
        # Update output display
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
    
    def set_output_value(self, pedal: str, value: int):
        """
        Set the output value for a pedal.
        Only updates the UI elements - no longer used for indicator updates.
        """
        data = self._pedal_data[pedal]
        
        # Just update the UI output display values
        data['output_value'] = value
        data['output_progress'].setValue(value)
        data['output_label'].setText(f"Mapped Output: {value}")
    
    def get_calibration_points(self, pedal: str):
        """Get the calibration points for a pedal."""
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            return data['calibration_chart'].points
        return []
    
    def set_calibration_points(self, pedal: str, points: list):
        """Set the calibration points for a pedal."""
        data = self._pedal_data[pedal]
        if 'calibration_chart' in data:
            data['calibration_chart'].points = points
            data['calibration_chart'].update_chart()
    
    def get_curve_type(self, pedal: str):
        """Get the curve type for a pedal."""
        data = self._pedal_data[pedal]
        return data.get('curve_type', 'Linear')
    
    def set_curve_type(self, pedal: str, curve_type: str):
        """Set the curve type for a pedal."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        if 'curve_type_selector' in data:
            data['curve_type_selector'].setCurrentText(curve_type)
    
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
        """Update the visualization of the calibration curve."""
        data = self._pedal_data[pedal]
        calibration_chart = data['calibration_chart']
        
        # Update the chart with the current points
        calibration_chart.set_points(data['points'])
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def change_response_curve(self, pedal: str, curve_type: str):
        """Change the response curve type for a pedal."""
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        calibration_chart = data['calibration_chart']
        
        # Generate new points based on the curve type
        if curve_type in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
            new_points = []
            
            if curve_type == "Linear":
                # Linear curve: y = x
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = x  # Linear mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Exponential":
                # Exponential curve: y = x^2
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = (x / 100) ** 2 * 100  # x^2 mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Logarithmic":
                # Logarithmic curve: y = sqrt(x)
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    y = math.sqrt(x / 100) * 100  # sqrt(x) mapping
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "S-Curve":
                # S-Curve: combination of exponential and logarithmic
                # Using a sigmoid function: y = 1 / (1 + e^(-k*(x-50)))
                k = 0.1  # Controls the steepness of the curve
                for i in range(5):
                    x = i * 25  # 5 points at 0%, 25%, 50%, 75%, 100%
                    # Sigmoid function scaled to 0-100 range
                    y = 100 / (1 + math.exp(-k * (x - 50)))
                    new_points.append(QPointF(x, y))
            
            # Update the chart with the new points
            calibration_chart.set_points(new_points)
            
            # Update stored points
            data['points'] = new_points.copy()
        else:
            # This is a preset curve, load it from hardware
            try:
                if hasattr(self, 'hardware') and self.hardware:
                    curve_data = self.hardware.load_custom_curve(pedal, curve_type)
                    if curve_data and 'points' in curve_data:
                        # Convert points to QPointF objects
                        new_points = [QPointF(x, y) for x, y in curve_data['points']]
                        
                        # Update the chart with the loaded points
                        calibration_chart.set_points(new_points)
                        
                        # Update stored points
                        data['points'] = new_points.copy()
                    else:
                        logger.warning(f"Could not load curve data for {curve_type}")
                        self.show_message("Error", f"Could not load curve data for '{curve_type}'")
                else:
                    logger.warning("Hardware not initialized, cannot load curve")
                    self.show_message("Error", "Hardware not initialized, cannot load curve")
            except Exception as e:
                logger.error(f"Error loading curve {curve_type}: {e}")
                self.show_message("Error", f"Failed to load curve: {e}")
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def on_point_moved(self, pedal: str):
        """Handle when a calibration point is moved by the user."""
        data = self._pedal_data[pedal]
        calibration_chart = data['calibration_chart']
        
        # The chart has already been updated internally in its own on_control_point_moved method
        # Just get the updated points for storage and signal purposes
        points = calibration_chart.get_points()
        data['points'] = points
        
        # Get the current output value from the chart
        output_value = calibration_chart.get_output_value()
        
        # Update output display
        data['output_value'] = output_value
        data['output_progress'].setValue(output_value)
        data['output_label'].setText(f"Mapped Output: {output_value}")
        
        # Mark as custom curve type
        data['curve_type'] = "Custom"
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def show_message(self, title: str, message: str):
        """Show a message box with the given title and message."""
        QMessageBox.information(self, title, message)
    
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
        
        # Reset deadzone values when changing min/max
        data['min_deadzone'] = 0
        data['max_deadzone'] = 0
        data['min_deadzone_value'].setText("0%")
        data['max_deadzone_value'].setText("0%")
        
        # Update hardware deadzone
        if hasattr(self, 'hardware') and pedal in self.hardware.axis_ranges:
            self.hardware.axis_ranges[pedal]['min_deadzone'] = 0
            self.hardware.axis_ranges[pedal]['max_deadzone'] = 0
        
        # Update chart visualization
        if 'calibration_chart' in data:
            data['calibration_chart'].set_deadzones(0, 0)
            
        self.calibration_updated.emit(pedal)
    
    def adjust_min_deadzone(self, pedal: str, delta: int):
        """Adjust the minimum deadzone percentage."""
        data = self._pedal_data[pedal]
        current_min_deadzone = data.get('min_deadzone', 0)
        current_max_deadzone = data.get('max_deadzone', 0)
        
        # Calculate new value ensuring it doesn't exceed 50% and total doesn't exceed 80%
        new_min_deadzone = max(0, min(current_min_deadzone + delta, 50))
        
        # Ensure total deadzone doesn't exceed 80% of range
        if new_min_deadzone + current_max_deadzone > 80:
            new_min_deadzone = 80 - current_max_deadzone
        
        # Only update if value changed
        if new_min_deadzone != current_min_deadzone:
            data['min_deadzone'] = new_min_deadzone
            data['min_deadzone_value'].setText(f"{new_min_deadzone}%")
            
            # Update visualization on the chart
            if 'calibration_chart' in data:
                data['calibration_chart'].set_deadzones(new_min_deadzone, current_max_deadzone)
            
            # Update hardware deadzone
            if hasattr(self, 'hardware') and pedal in self.hardware.axis_ranges:
                self.hardware.axis_ranges[pedal]['min_deadzone'] = new_min_deadzone
                self.hardware.save_axis_ranges()
            
            # Signal that calibration has been updated
            self.calibration_updated.emit(pedal)
    
    def adjust_max_deadzone(self, pedal: str, delta: int):
        """Adjust the maximum deadzone percentage."""
        data = self._pedal_data[pedal]
        current_min_deadzone = data.get('min_deadzone', 0)
        current_max_deadzone = data.get('max_deadzone', 0)
        
        # Calculate new value ensuring it doesn't exceed 50% and total doesn't exceed 80%
        new_max_deadzone = max(0, min(current_max_deadzone + delta, 50))
        
        # Ensure total deadzone doesn't exceed 80% of range
        if current_min_deadzone + new_max_deadzone > 80:
            new_max_deadzone = 80 - current_min_deadzone
        
        # Only update if value changed
        if new_max_deadzone != current_max_deadzone:
            data['max_deadzone'] = new_max_deadzone
            data['max_deadzone_value'].setText(f"{new_max_deadzone}%")
            
            # Update visualization on the chart
            if 'calibration_chart' in data:
                data['calibration_chart'].set_deadzones(current_min_deadzone, new_max_deadzone)
            
            # Update hardware deadzone
            if hasattr(self, 'hardware') and pedal in self.hardware.axis_ranges:
                self.hardware.axis_ranges[pedal]['max_deadzone'] = new_max_deadzone
                self.hardware.save_axis_ranges()
            
            # Signal that calibration has been updated
            self.calibration_updated.emit(pedal)
    
    def on_calibration_load(self):
        """Handle loading of calibration data."""
        if hasattr(self, 'hardware'):
            # For each pedal, load calibration data
            for pedal_key in ['throttle', 'brake', 'clutch']:
                pedal_data = self._pedal_data[pedal_key]
                if pedal_key in self.hardware.axis_ranges:
                    axis_range = self.hardware.axis_ranges[pedal_key]
                    # Load min/max values
                    min_val = axis_range.get('min', 0)
                    max_val = axis_range.get('max', 65535)
                    
                    # Update UI
                    pedal_data['min_value'] = min_val
                    pedal_data['max_value'] = max_val
                    pedal_data['min_label'].setText(f"Min: {min_val}")
                    pedal_data['max_label'].setText(f"Max: {max_val}")
                    
                    # Load deadzone values if they exist
                    min_deadzone = axis_range.get('min_deadzone', 0)
                    max_deadzone = axis_range.get('max_deadzone', 0)
                    
                    # Update UI for deadzones
                    pedal_data['min_deadzone'] = min_deadzone
                    pedal_data['max_deadzone'] = max_deadzone
                    pedal_data['min_deadzone_value'].setText(f"{min_deadzone}%")
                    pedal_data['max_deadzone_value'].setText(f"{max_deadzone}%")
                    
                    # Update chart visualization with deadzones
                    if 'calibration_chart' in pedal_data:
                        pedal_data['calibration_chart'].set_deadzones(min_deadzone, max_deadzone)
                    
                # Also load calibration curve points
                if pedal_key in self.hardware.calibration:
                    points = self.hardware.calibration[pedal_key].get('points', [])
                    curve_type = self.hardware.calibration[pedal_key].get('curve', 'Linear')
                    
                    # Update curve type selection
                    curve_selector = pedal_data['curve_type_selector']
                    for i in range(curve_selector.count()):
                        if curve_selector.itemText(i) == curve_type:
                            curve_selector.setCurrentIndex(i)
                            break
                    
                    # Update calibration points
                    chart = pedal_data['calibration_chart']
                    chart.set_points(points)
        
        # Reflect the loaded calibration in the monitor display
        self.update_monitor_display()

    def create_menu_bar(self):
        """Create the menu bar with file options."""
        menu_bar = self.menuBar()
        
        # Create File menu
        file_menu = menu_bar.addMenu("File")
        
        # Add Check for Updates option
        update_action = QAction("Check for Updates", self)
        update_action.triggered.connect(self.check_for_updates)
        file_menu.addAction(update_action)
        
        # Add separator
        file_menu.addSeparator()
        
        # Add Exit option
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Add Pedal Config button to menu bar
        pedal_config_action = QAction("Pedal Config", self)
        pedal_config_action.triggered.connect(self.open_pedal_config)
        menu_bar.addAction(pedal_config_action)
        
        # Add Race Coach button to menu bar
        race_coach_action = QAction("Race Coach", self)
        race_coach_action.triggered.connect(self.open_race_coach)
        menu_bar.addAction(race_coach_action)
        
        # Style the menu bar for dark theme
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #353535;
                color: #ffffff;
            }
            QMenuBar::item {
                background-color: #353535;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #2a82da;
            }
            QMenu {
                background-color: #353535;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #2a82da;
            }
        """)
    
    def check_for_updates(self):
        """Manually check for updates."""
        logger.info("Manual update check requested")
        
        # Show a message that we're checking for updates
        QMessageBox.information(
            self,
            "Checking for Updates",
            "TrackPro is checking for updates. You will be notified when the check is complete."
        )
        
        if hasattr(self, 'updater'):
            logger.info("Using existing updater instance")
            self.updater.check_for_updates(silent=False, manual_check=True)
        else:
            logger.info("Creating new updater instance")
            from .updater import Updater
            updater = Updater(self)
            updater.check_for_updates(silent=False, manual_check=True)
            self.updater = updater
            logger.info("Updater instance created and stored")

    def show_update_notification(self, version):
        """Show a notification that an update is available."""
        logger.info(f"Showing update notification for version: {version}")
        self.update_notification.setText(f"Update Available: v{version} - Click File > Check for Updates")
        self.update_notification.setVisible(True)
        
    def hide_update_notification(self):
        """Hide the update notification."""
        logger.info("Hiding update notification")
        self.update_notification.setVisible(False)
        
    def open_race_coach(self):
        """Open the Race Coach screen with password protection."""
        try:
            # Show password dialog
            password_dialog = PasswordDialog(self)
            result = password_dialog.exec_()
            
            # Check if dialog was accepted and password is correct
            if result == QDialog.Accepted:
                entered_password = password_dialog.get_password()
                # Replace 'trackpro' with your desired password
                correct_password = 'lt'
                
                if entered_password != correct_password:
                    QMessageBox.warning(self, "Access Denied", 
                                     "Incorrect password. Access to Race Coach denied.")
                    logger.warning("Race Coach access denied - incorrect password entered")
                    return
            else:
                # User cancelled the dialog
                logger.info("Race Coach access cancelled by user")
                return
            
            # Import Race Coach components
            from .race_coach import RaceCoachWidget
            
            logger.info("Imported Race Coach modules successfully")
            
            # Check if Race Coach widget already exists in stacked widget
            if self.stacked_widget.count() > 1:
                logger.info("Race Coach screen already exists, switching to it")
                self.stacked_widget.setCurrentIndex(1)
                return
            
            # Create and add the Race Coach widget
            try:
                race_coach_widget = RaceCoachWidget(self)
                self.stacked_widget.addWidget(race_coach_widget)
                # Switch to the Race Coach screen
                self.stacked_widget.setCurrentIndex(1)
                logger.info("Race Coach screen added and switched to")
                
            except Exception as component_error:
                logger.error(f"Error creating Race Coach components: {component_error}")
                QMessageBox.critical(
                    self,
                    "Component Error",
                    f"Failed to initialize Race Coach components: {str(component_error)}",
                    QMessageBox.Ok
                )
                
        except ImportError as import_error:
            logger.error(f"Error importing Race Coach modules: {import_error}")
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import Race Coach modules: {str(import_error)}",
                QMessageBox.Ok
            )
        except Exception as e:
            logger.error(f"Error opening Race Coach: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open Race Coach: {str(e)}",
                QMessageBox.Ok
            )

    def open_pedal_config(self):
        """Switch to the pedal configuration screen."""
        # Switch to the pedal config screen (index 0)
        self.stacked_widget.setCurrentIndex(0)
        logger.info("Switched to Pedal Config screen")
    
    def reset_calibration(self, pedal: str):
        """Reset calibration to a linear curve."""
        data = self._pedal_data[pedal]
        
        # Reset the calibration chart to linear
        calibration_chart = data['calibration_chart']
        calibration_chart.reset_to_linear()
        
        # Get the updated points for storage
        data['points'] = calibration_chart.get_points()
        
        # Set curve type back to linear
        data['curve_type'] = 'Linear'
        
        # Update UI to match
        if 'curve_type_selector' in data:
            data['curve_type_selector'].setCurrentText("Linear")
        
        # Signal that calibration has changed
        self.calibration_updated.emit(pedal)
    
    def set_pedal_available(self, pedal: str, available: bool):
        """Enable or disable UI elements for a pedal based on availability."""
        if pedal in self._pedal_data:
            # Get all UI elements for this pedal
            elements = self._pedal_data[pedal]
            
            # Set enabled state for all interactive elements
            for key, element in elements.items():
                # Skip non-widget elements like 'min_value', 'max_value', 'points', 'curve_type', etc.
                if key in ['min_value', 'max_value', 'points', 'curve_type', 'line_series', 'scatter_series',
                           'min_deadzone', 'max_deadzone']:
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
    
    def update_monitor_display(self):
        """Update the monitor display to reflect the loaded calibration."""
        # Implement the logic to update the monitor display
        pass

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
                    
                    # Get current deadzone values
                    min_deadzone = self._pedal_data[pedal].get('min_deadzone', 0)
                    max_deadzone = self._pedal_data[pedal].get('max_deadzone', 0)
                    
                    # Update hardware ranges
                    self.hardware.axis_ranges[pedal] = {
                        'min': min_val,
                        'max': max_val,
                        'min_deadzone': min_deadzone,
                        'max_deadzone': max_deadzone
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
                    
                    logger.info(f"Saved {pedal} calibration: min={min_val}, max={max_val}, min_deadzone={min_deadzone}%, max_deadzone={max_deadzone}%, points={len(point_tuples)}, curve={curve_type}")
            
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

    def set_hardware(self, hardware):
        """Set the hardware interface for the application."""
        self.hardware = hardware
        
        # Initialize UI with hardware state if available
        if hardware:
            for pedal in ['throttle', 'brake', 'clutch']:
                if pedal in hardware.axis_ranges:
                    # Update UI with hardware values
                    if hasattr(self, '_pedal_data') and pedal in self._pedal_data:
                        # Set min/max values
                        min_val = hardware.axis_ranges[pedal].get('min', 0)
                        max_val = hardware.axis_ranges[pedal].get('max', 65535)
                        self._pedal_data[pedal]['min_value'] = min_val
                        self._pedal_data[pedal]['max_value'] = max_val
                        
                        # Set deadzone values
                        min_deadzone = hardware.axis_ranges[pedal].get('min_deadzone', 0)
                        max_deadzone = hardware.axis_ranges[pedal].get('max_deadzone', 0)
                        if 'min_deadzone' in self._pedal_data[pedal]:
                            self._pedal_data[pedal]['min_deadzone'] = min_deadzone
                        if 'max_deadzone' in self._pedal_data[pedal]:
                            self._pedal_data[pedal]['max_deadzone'] = max_deadzone
                        
                        # Update calibration chart
                        if 'calibration_chart' in self._pedal_data[pedal]:
                            self._pedal_data[pedal]['calibration_chart'].set_deadzones(min_deadzone, max_deadzone)
            
            # Refresh the curve lists to show available custom curves
            try:
                # Wait until hardware is fully initialized and curves are created
                QTimer.singleShot(500, self.refresh_curve_lists)
            except Exception as e:
                logger.error(f"Error scheduling curve list refresh: {e}")
    
    def refresh_curve_lists(self):
        """Refresh the curve selection lists for all pedals with available curves."""
        if not hasattr(self, 'hardware') or not self.hardware:
            return
            
        # Check if hardware has curve lists
        if not hasattr(self.hardware, 'list_available_curves'):
            return
        
        # Set flag to prevent unnecessary callbacks during population
        self._is_populating_curves = True
        
        # Refresh curve lists for each pedal
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in self._pedal_data:
                # Get available curves for this pedal
                try:
                    available_curves = self.hardware.list_available_curves(pedal)
                    logger.info(f"Available curves for {pedal}: {available_curves}")
                    
                    # Update Curve Type selector (main dropdown)
                    if 'curve_type_selector' in self._pedal_data[pedal]:
                        curve_type_selector = self._pedal_data[pedal]['curve_type_selector']
                        
                        # Save current selection if possible
                        current_curve_type = curve_type_selector.currentText()
                        
                        # Clear and repopulate the selector
                        curve_type_selector.clear()
                        
                        # Add standard curves
                        curve_type_selector.addItem("Linear")
                        curve_type_selector.addItem("Exponential")  
                        curve_type_selector.addItem("Logarithmic")
                        curve_type_selector.addItem("S-Curve")
                        
                        # Add all available custom curves
                        for curve in available_curves:
                            if curve not in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
                                curve_type_selector.addItem(curve)
                        
                        # Restore previous selection if it still exists
                        index = curve_type_selector.findText(current_curve_type)
                        if index >= 0:
                            curve_type_selector.setCurrentIndex(index)
                    
                    # Update Saved Curves selector (in Curve Management section)
                    if 'saved_curves_selector' in self._pedal_data[pedal]:
                        saved_curves_selector = self._pedal_data[pedal]['saved_curves_selector']
                        
                        # Save current selection if possible
                        current_saved_curve = saved_curves_selector.currentText()
                        
                        # Clear and repopulate the selector
                        saved_curves_selector.clear()
                        
                        # Only add custom curves to the saved curves selector
                        for curve in available_curves:
                            if curve not in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
                                saved_curves_selector.addItem(curve)
                        
                        # Restore previous selection if it still exists
                        index = saved_curves_selector.findText(current_saved_curve)
                        if index >= 0:
                            saved_curves_selector.setCurrentIndex(index)
                    
                except Exception as e:
                    logger.error(f"Error refreshing curve list for {pedal}: {e}")
        
        # Clear the flag after population is complete
        self._is_populating_curves = False
    
    def on_curve_selector_changed(self, pedal: str, curve_name: str):
        """Handle when the user selects a curve from a dropdown list."""
        if not curve_name:
            return
            
        # Check if this is a programmatic change (during list population)
        if hasattr(self, '_is_populating_curves') and self._is_populating_curves:
            return
            
        logger.info(f"Curve selection changed for {pedal}: {curve_name}")
        
        # Determine which selector triggered this change
        data = self._pedal_data[pedal]
        
        # Update the curve type in our data
        self.set_curve_type(pedal, curve_name)
        
        # Apply the curve change using the change_response_curve method
        self.change_response_curve(pedal, curve_name)
        
        # Make sure both selectors are in sync
        if 'curve_type_selector' in data and data['curve_type_selector'].currentText() != curve_name:
            # Check if the curve exists in the dropdown
            if data['curve_type_selector'].findText(curve_name) == -1:
                data['curve_type_selector'].addItem(curve_name)
            data['curve_type_selector'].setCurrentText(curve_name)
            
        if 'saved_curves_selector' in data and data['saved_curves_selector'].currentText() != curve_name:
            # Only update saved curves selector for custom curves
            if curve_name not in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
                if data['saved_curves_selector'].findText(curve_name) == -1:
                    data['saved_curves_selector'].addItem(curve_name)
                data['saved_curves_selector'].setCurrentText(curve_name)
    
    def load_custom_curve(self, pedal: str, curve_name: str):
        """Load a custom curve from the saved curves."""
        if not curve_name:
            return
            
        logger.info(f"Loading curve '{curve_name}' for {pedal}")
        
        try:
            if hasattr(self, 'hardware') and self.hardware:
                # Load the curve from the hardware
                curve_data = self.hardware.load_custom_curve(pedal, curve_name)
                
                if curve_data and 'points' in curve_data:
                    # Convert points to QPointF objects
                    points = [QPointF(x, y) for x, y in curve_data['points']]
                    
                    # Update the chart with the loaded points
                    data = self._pedal_data[pedal]
                    data['calibration_chart'].set_points(points)
                    
                    # Update stored points
                    data['points'] = points.copy()
                    
                    # Update curve type
                    data['curve_type'] = curve_name
                    
                    # Update both curve selectors to match
                    if 'curve_type_selector' in data:
                        # First make sure the curve exists in the dropdown
                        if data['curve_type_selector'].findText(curve_name) == -1:
                            data['curve_type_selector'].addItem(curve_name)
                        data['curve_type_selector'].setCurrentText(curve_name)
                    
                    if 'saved_curves_selector' in data:
                        # Also update the saved curves dropdown
                        if data['saved_curves_selector'].findText(curve_name) == -1:
                            data['saved_curves_selector'].addItem(curve_name)
                        data['saved_curves_selector'].setCurrentText(curve_name)
                    
                    # Signal that calibration has changed
                    self.calibration_updated.emit(pedal)
                    
                    # Show success message
                    self.show_message("Curve Loaded", f"Successfully loaded curve '{curve_name}' for {pedal}")
                else:
                    logger.warning(f"Could not load curve data for {curve_name}")
                    self.show_message("Error", f"Could not load curve data for '{curve_name}'")
            else:
                logger.warning("Hardware not initialized, cannot load curve")
                self.show_message("Error", "Hardware not initialized, cannot load curve")
        except Exception as e:
            logger.error(f"Error loading curve {curve_name}: {e}")
            self.show_message("Error", f"Failed to load curve: {e}")
    
    def delete_custom_curve(self, pedal: str, curve_name: str):
        """Delete a custom curve from the saved curves."""
        if not curve_name or curve_name in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
            logger.warning(f"Cannot delete built-in curve type: {curve_name}")
            self.show_message("Error", "Cannot delete built-in curve types")
            return
            
        logger.info(f"Deleting curve '{curve_name}' for {pedal}")
        
        try:
            if hasattr(self, 'hardware') and self.hardware:
                # Confirm deletion with the user
                confirm = QMessageBox.question(
                    self,
                    "Confirm Deletion",
                    f"Are you sure you want to delete the curve '{curve_name}' for {pedal}?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if confirm == QMessageBox.Yes:
                    # Delete the curve using the hardware
                    success = self.hardware.delete_custom_curve(pedal, curve_name)
                    
                    if success:
                        # Refresh the curve list
                        self.refresh_curve_lists()
                        
                        # Show success message
                        self.show_message("Curve Deleted", f"Successfully deleted curve '{curve_name}' for {pedal}")
                    else:
                        logger.warning(f"Failed to delete curve {curve_name}")
                        self.show_message("Error", f"Failed to delete curve '{curve_name}'")
            else:
                logger.warning("Hardware not initialized, cannot delete curve")
                self.show_message("Error", "Hardware not initialized, cannot delete curve")
        except Exception as e:
            logger.error(f"Error deleting curve {curve_name}: {e}")
            self.show_message("Error", f"Failed to delete curve: {e}")
    
    def save_custom_curve(self, pedal: str, name: str):
        """Save the current curve configuration as a custom curve."""
        if not name:
            self.show_message("Error", "Please enter a name for the curve")
            return
            
        logger.info(f"Saving curve '{name}' for {pedal}")
        
        try:
            if hasattr(self, 'hardware') and self.hardware:
                data = self._pedal_data[pedal]
                
                # Get the points from the calibration chart
                points = data['calibration_chart'].get_points()
                
                # Convert QPointF objects to tuples for JSON serialization
                point_tuples = [(int(p.x()), int(p.y())) for p in points]
                
                # Save the curve using the hardware
                success = self.hardware.save_custom_curve(
                    pedal=pedal,
                    name=name,
                    points=point_tuples,
                    curve_type=name
                )
                
                if success:
                    # Update curve type
                    data['curve_type'] = name
                    
                    # Refresh the curve list
                    self.refresh_curve_lists()
                    
                    # Clear the name input
                    data['curve_name_input'].clear()
                    
                    # Show success message
                    self.show_message("Curve Saved", f"Successfully saved curve '{name}' for {pedal}")
                else:
                    logger.warning(f"Failed to save curve {name}")
                    self.show_message("Error", f"Failed to save curve '{name}'")
            else:
                logger.warning("Hardware not initialized, cannot save curve")
                self.show_message("Error", "Hardware not initialized, cannot save curve")
        except Exception as e:
            logger.error(f"Error saving curve {name}: {e}")
            self.show_message("Error", f"Failed to save curve: {e}") 