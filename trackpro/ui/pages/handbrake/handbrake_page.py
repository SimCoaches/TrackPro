import logging
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QPushButton, QLabel, QFrame
from PyQt6.QtCore import pyqtSignal, Qt
from ...modern.shared.base_page import BasePage
from .handbrake_calibration_widget import HandbrakeCalibrationWidget
from .handbrake_deadzone_widget import HandbrakeDeadzoneWidget
from .handbrake_curve_manager_widget import HandbrakeCurveManagerWidget

logger = logging.getLogger(__name__)

class HandbrakePage(BasePage):
    handbrake_calibrated = pyqtSignal(str, dict)
    curve_changed = pyqtSignal(str, str)
    
    def __init__(self, global_managers=None):
        self.handbrake_widget = None
        super().__init__("handbrake", global_managers)
    
    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.status_label = QLabel("")
        self._create_coming_soon_content(layout)

    def _create_coming_soon_content(self, layout: QVBoxLayout) -> None:
        main_frame = QFrame()
        main_frame.setStyleSheet(
            """
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #333;
                border-radius: 12px;
                padding: 40px;
            }
            """
        )
        main_layout = QVBoxLayout(main_frame)
        main_layout.setSpacing(25)

        title_label = QLabel("Handbrake")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            """
            color: #ffffff;
            font-size: 36px;
            font-weight: bold;
            text-align: center;
            """
        )
        main_layout.addWidget(title_label)

        coming_soon_label = QLabel("COMING SOON")
        coming_soon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        coming_soon_label.setStyleSheet(
            """
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            background-color: rgba(0, 212, 255, 0.1);
            border: 2px solid #00d4ff;
            border-radius: 20px;
            padding: 8px 20px;
            """
        )
        main_layout.addWidget(coming_soon_label)

        desc_label = QLabel(
            "We're building a polished Handbrake configuration experience!\n\n"
            "Coming soon:\n"
            "• Guided calibration wizard\n"
            "• Deadzone and sensitivity tuning\n"
            "• Curve editor with live preview\n"
            "• Hardware status and diagnostics"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            """
            color: #cccccc;
            font-size: 16px;
            text-align: center;
            line-height: 1.6;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            """
        )
        main_layout.addWidget(desc_label)

        progress_frame = QFrame()
        progress_frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 20px;
            }
            """
        )
        progress_layout = QVBoxLayout(progress_frame)

        progress_title = QLabel("Development Progress")
        progress_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_title.setStyleSheet(
            """
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
            """
        )
        progress_layout.addWidget(progress_title)

        progress_bar_frame = QFrame()
        progress_bar_frame.setStyleSheet(
            """
            QFrame {
                background-color: #333;
                border-radius: 10px;
                padding: 3px;
            }
            """
        )
        progress_bar_layout = QHBoxLayout(progress_bar_frame)
        progress_bar_layout.setContentsMargins(0, 0, 0, 0)

        progress_fill = QFrame()
        progress_fill.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff, stop:1 #0099cc);
                border-radius: 7px;
            }
            """
        )
        progress_fill.setFixedWidth(200)
        progress_bar_layout.addWidget(progress_fill)
        progress_bar_layout.addStretch()
        progress_layout.addWidget(progress_bar_frame)

        progress_text = QLabel("In Progress")
        progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_text.setStyleSheet(
            """
            color: #00d4ff;
            font-size: 14px;
            font-weight: bold;
            text-align: center;
            margin-top: 5px;
            """
        )
        progress_layout.addWidget(progress_text)

        main_layout.addWidget(progress_frame)
        main_layout.addStretch()
        layout.addWidget(main_frame)

    def on_page_activated(self):
        super().on_page_activated()
        logger.info("Handbrake Coming Soon page activated")

    def lazy_init(self):
        logger.info("Handbrake Coming Soon page lazy initialization")

    def cleanup(self):
        logger.info("Handbrake Coming Soon page cleanup")
        super().cleanup()
    
    def create_handbrake_widget(self, parent_layout):
        """Create the main handbrake configuration widget."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        main_widget.setLayout(layout)
        
        # Create handbrake configuration widgets
        calibration_widget = HandbrakeCalibrationWidget("handbrake", self.global_managers)
        deadzone_widget = HandbrakeDeadzoneWidget("handbrake", self.global_managers)
        curve_manager_widget = HandbrakeCurveManagerWidget("handbrake", self.global_managers)
        
        layout.addWidget(calibration_widget)
        layout.addWidget(deadzone_widget)
        layout.addWidget(curve_manager_widget)
        layout.addStretch()
        
        # Connect signals
        calibration_widget.calibration_updated.connect(
            lambda data: self.handbrake_calibrated.emit("handbrake", data)
        )
        curve_manager_widget.curve_changed.connect(
            lambda curve: self.curve_changed.emit("handbrake", curve)
        )
        
        # Connect curve changes to update the chart
        curve_manager_widget.curve_changed.connect(
            lambda curve: calibration_widget.update_chart_curve(curve)
        )
        
        # Connect curve editing to update calibration widget
        curve_manager_widget.curve_edited.connect(
            lambda x_points, y_points: self.update_calibration_curve(calibration_widget, x_points, y_points)
        )
        
        deadzone_widget.deadzone_changed.connect(
            lambda handbrake, min_dz, max_dz: self.update_deadzone("handbrake", min_dz, max_dz, calibration_widget)
        )
        
        scroll_area.setWidget(main_widget)
        parent_layout.addWidget(scroll_area)
        
        self.handbrake_widget = scroll_area
    
    def open_calibration_wizard(self):
        """Open the handbrake calibration wizard."""
        # For now, show a simple message - wizard can be implemented later
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Handbrake Calibration")
        msg.setText("Use the manual calibration controls below.\n\n"
                   "1. Pull and hold the handbrake fully\n"
                   "2. Click 'Set Max' button\n"
                   "3. Release the handbrake completely\n"
                   "4. Click 'Set Min' button")
        msg.exec()
        logger.info("Handbrake calibration wizard placeholder shown")
    
    def update_deadzone(self, handbrake_name: str, min_deadzone: int, max_deadzone: int, calibration_widget):
        """Update the deadzone values in the calibration chart."""
        logger.info(f"Updating deadzone for {handbrake_name}: min={min_deadzone}%, max={max_deadzone}%")
        
        if hasattr(calibration_widget, 'calibration_chart') and calibration_widget.calibration_chart:
            chart = calibration_widget.calibration_chart
            if hasattr(chart, 'set_deadzones'):
                chart.set_deadzones(min_deadzone, max_deadzone)
                logger.debug(f"Applied deadzone to chart for {handbrake_name}")
    
    def update_calibration_curve(self, calibration_widget, x_points, y_points):
        """Update the calibration widget with new curve points from the editor."""
        logger.debug(f"Updating calibration curve with points: {x_points}, {y_points}")
        
        if hasattr(calibration_widget, 'curve_x') and hasattr(calibration_widget, 'curve_y'):
            calibration_widget.curve_x = x_points
            calibration_widget.curve_y = y_points
            
            # Update the chart if available
            if hasattr(calibration_widget, 'curve_line') and calibration_widget.curve_line:
                calibration_widget.curve_line.setData(x_points, y_points)
            
            if hasattr(calibration_widget, 'scatter') and calibration_widget.scatter:
                calibration_widget.scatter.setData(x_points, y_points)
            
            # Emit calibration update
            calibration_widget.emit_calibration_update()
            logger.debug("Updated calibration widget curve points")
    
    def on_calibration_complete(self, calibration_data):
        """Handle calibration completion."""
        logger.info(f"Handbrake calibration completed with data: {calibration_data}")
        
        # Update the calibration widget with new data
        if 'handbrake' in calibration_data and self.handbrake_widget:
            data = calibration_data['handbrake']
            if hasattr(self.handbrake_widget.widget(), 'layout'):
                calibration_widget = self.handbrake_widget.widget().layout().itemAt(0).widget()
                if hasattr(calibration_widget, 'set_calibration_range'):
                    min_val = data.get('min', 0)
                    max_val = data.get('max', 65535)
                    calibration_widget.set_calibration_range(min_val, max_val)
    
    def handle_hardware_update(self, handbrake_data):
        """Handle hardware updates for real-time visualization."""
        if 'handbrake' in handbrake_data and self.handbrake_widget:
            value = handbrake_data['handbrake']
            if hasattr(self.handbrake_widget.widget(), 'layout'):
                calibration_widget = self.handbrake_widget.widget().layout().itemAt(0).widget()
                if hasattr(calibration_widget, 'update_input_value'):
                    calibration_widget.update_input_value(value)
    
    def update_connection_status(self):
        """Update the connection status display."""
        if hasattr(self, 'handbrake_input') and self.handbrake_input:
            status = self.handbrake_input.get_handbrake_status()
            if status['connected']:
                self.status_label.setText(f"✅ Connected: {status['device_name']} ({status['axes']} axes)")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #27ae60;
                        margin-bottom: 15px;
                    }
                """)
            else:
                self.status_label.setText("❌ Arduino Leonardo handbrake not detected")
                self.status_label.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #e74c3c;
                        margin-bottom: 15px;
                    }
                """)
        else:
            self.status_label.setText("⚠️ Handbrake system not initialized")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #f39c12;
                    margin-bottom: 15px;
                }
            """)
    
    def set_handbrake_input(self, handbrake_input):
        """Set the handbrake input instance."""
        self.handbrake_input = handbrake_input
        self.update_connection_status()
    
    def set_handbrake_available(self, available: bool):
        """Set handbrake availability."""
        if self.handbrake_widget:
            self.handbrake_widget.setEnabled(available)
    
    def get_handbrake_calibration(self):
        """Get current handbrake calibration data."""
        if self.handbrake_widget and hasattr(self.handbrake_widget.widget(), 'layout'):
            calibration_widget = self.handbrake_widget.widget().layout().itemAt(0).widget()
            if hasattr(calibration_widget, 'get_calibration_data'):
                return calibration_widget.get_calibration_data()
        return None