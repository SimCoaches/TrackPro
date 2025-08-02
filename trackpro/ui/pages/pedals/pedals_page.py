import logging
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QScrollArea, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from ...modern.shared.base_page import BasePage
from .calibration_widget import PedalCalibrationWidget
from .deadzone_widget import DeadzoneWidget
from .curve_manager_widget import CurveManagerWidget

logger = logging.getLogger(__name__)

class PedalsPage(BasePage):
    pedal_calibrated = pyqtSignal(str, dict)
    curve_changed = pyqtSignal(str, str)
    
    def __init__(self, global_managers=None):
        self.pedal_widgets = {}
        self.pedal_tabs = None
        super().__init__("pedals", global_managers)
    
    def init_page(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add calibration wizard button
        wizard_layout = QHBoxLayout()
        wizard_btn = QPushButton("🧙 Calibration Wizard")
        wizard_btn.setMaximumWidth(180)  # Make button much smaller
        wizard_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                max-width: 180px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
        """)
        wizard_btn.clicked.connect(self.open_calibration_wizard)
        wizard_layout.addWidget(wizard_btn)  # Left-aligned (no stretch before)
        wizard_layout.addStretch()  # Stretch after to push button left
        layout.addLayout(wizard_layout)
        
        # Side-by-side pedal layout
        pedals_layout = QHBoxLayout()
        layout.addLayout(pedals_layout)
        
        self.create_side_by_side_pedals(pedals_layout)
        
        if self.performance_manager:
            self.performance_manager.ui_update_ready.connect(self.handle_hardware_update)
    
    def create_side_by_side_pedals(self, parent_layout):
        pedals = ['throttle', 'brake', 'clutch']
        
        for pedal in pedals:
            pedal_widget = self.create_pedal_widget(pedal)
            parent_layout.addWidget(pedal_widget, 1)  # Equal stretch
            self.pedal_widgets[pedal] = pedal_widget
    
    def create_pedal_widget(self, pedal_name: str):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)  # Reduced spacing between sections
        layout.setContentsMargins(6, 6, 6, 6)  # Reduced margins
        main_widget.setLayout(layout)
        
        calibration_widget = PedalCalibrationWidget(pedal_name, self.global_managers)
        deadzone_widget = DeadzoneWidget(pedal_name, self.global_managers)
        curve_manager_widget = CurveManagerWidget(pedal_name, self.global_managers)
        
        layout.addWidget(calibration_widget)
        layout.addWidget(deadzone_widget)
        layout.addWidget(curve_manager_widget)
        layout.addStretch()
        
        calibration_widget.calibration_updated.connect(
            lambda data, p=pedal_name: self.pedal_calibrated.emit(p, data)
        )
        curve_manager_widget.curve_changed.connect(
            lambda curve, p=pedal_name: self.curve_changed.emit(p, curve)
        )
        deadzone_widget.deadzone_changed.connect(
            lambda pedal, min_dz, max_dz: self.update_deadzone(pedal, min_dz, max_dz, calibration_widget)
        )
        
        scroll_area.setWidget(main_widget)
        return scroll_area
    
    def open_calibration_wizard(self):
        try:
            from ....pedals.calibration import CalibrationWizard
            
            if not self.hardware_input:
                logger.warning("Hardware input not available - cannot open calibration wizard")
                return
            
            wizard = CalibrationWizard(self.hardware_input, self)
            wizard.calibration_complete.connect(self.on_calibration_complete)
            
            result = wizard.exec()
            if result == wizard.DialogCode.Accepted:
                logger.info("Calibration wizard completed successfully")
            else:
                logger.info("Calibration wizard cancelled")
                
        except ImportError as e:
            logger.error(f"Failed to import CalibrationWizard: {e}")
        except Exception as e:
            logger.error(f"Error opening calibration wizard: {e}")
    
    def update_deadzone(self, pedal_name: str, min_deadzone: int, max_deadzone: int, calibration_widget):
        """Update the deadzone values in the calibration chart."""
        logger.info(f"Updating deadzone for {pedal_name}: min={min_deadzone}%, max={max_deadzone}%")
        
        if hasattr(calibration_widget, 'calibration_chart') and calibration_widget.calibration_chart:
            chart = calibration_widget.calibration_chart
            if hasattr(chart, 'set_deadzones'):
                chart.set_deadzones(min_deadzone, max_deadzone)
                logger.debug(f"Applied deadzone to chart for {pedal_name}")
    
    def on_calibration_complete(self, calibration_data):
        logger.info(f"Calibration completed with data: {calibration_data}")
        
        # Update the individual calibration widgets with new data
        for pedal, data in calibration_data.items():
            if pedal in self.pedal_widgets:
                widget = self.pedal_widgets[pedal]
                if hasattr(widget.widget(), 'layout'):
                    calibration_widget = widget.widget().layout().itemAt(0).widget()
                    if hasattr(calibration_widget, 'set_calibration_range'):
                        min_val = data.get('min', 0)
                        max_val = data.get('max', 65535)
                        calibration_widget.set_calibration_range(min_val, max_val)
    
    def handle_hardware_update(self, pedal_data):
        for pedal, value in pedal_data.items():
            if pedal in self.pedal_widgets:
                widget = self.pedal_widgets[pedal]
                if hasattr(widget.widget(), 'layout'):
                    calibration_widget = widget.widget().layout().itemAt(0).widget()
                    if hasattr(calibration_widget, 'update_input_value'):
                        calibration_widget.update_input_value(value)
    
    def set_pedal_available(self, pedal: str, available: bool):
        if pedal in self.pedal_widgets:
            widget = self.pedal_widgets[pedal]
            widget.setEnabled(available)
    
    def get_pedal_calibration(self, pedal: str):
        if pedal in self.pedal_widgets:
            widget = self.pedal_widgets[pedal]
            if hasattr(widget.widget(), 'layout'):
                calibration_widget = widget.widget().layout().itemAt(0).widget()
                if hasattr(calibration_widget, 'get_calibration_data'):
                    return calibration_widget.get_calibration_data()
        return None