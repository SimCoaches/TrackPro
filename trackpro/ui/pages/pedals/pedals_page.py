import logging
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor
from ...modern.shared.base_page import BasePage
from .calibration_widget import PedalCalibrationWidget
from .deadzone_widget import DeadzoneWidget
from .curve_manager_widget import CurveManagerWidget

logger = logging.getLogger(__name__)

class PedalsPage(BasePage):
    pedal_calibrated = pyqtSignal(str, dict)
    curve_changed = pyqtSignal(str, str)
    
    def __init__(self, global_managers=None):
        logger.info("🏗️ Initializing PedalsPage...")
        self.pedal_widgets = {}
        self.pedal_tabs = None
        self.connection_status_label = None
        self.connection_timer = None
        super().__init__("pedals", global_managers)
        logger.info("✅ PedalsPage initialized successfully")
    
    def init_page(self):
        """Initialize the pedals page."""
        logger.info("🏗️ Initializing pedals page UI...")
        # Don't call super().init_page() as it raises NotImplementedError
        
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create top controls layout (center-aligned, limited width)
        top_controls_layout = QVBoxLayout()
        top_controls_layout.setSpacing(5)
        
        # Create connection status indicator
        self.connection_status_label = QLabel("⚪ Hardware Unavailable")
        self.connection_status_label.setStyleSheet("""
            QLabel {
                background-color: #6b7280;
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                max-height: 24px;
                max-width: 400px;
            }
        """)
        self.connection_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create calibration wizard button
        calibration_button = QPushButton("Open Calibration Wizard")
        calibration_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                max-height: 32px;
                max-width: 400px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        calibration_button.clicked.connect(self.open_calibration_wizard)
        
        # Add widgets to top controls layout
        top_controls_layout.addWidget(self.connection_status_label, alignment=Qt.AlignmentFlag.AlignLeft)
        top_controls_layout.addWidget(calibration_button, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # Add the top controls layout to main layout
        main_layout.addLayout(top_controls_layout)
        
        # Create pedals layout
        pedals_layout = QHBoxLayout()
        self.create_side_by_side_pedals(pedals_layout)
        main_layout.addLayout(pedals_layout)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # Set up connection status timer
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.update_connection_status)
        self.connection_timer.start(1000)  # Update every second
        
        # Initial connection status update
        self.update_connection_status()
        
        if self.performance_manager:
            self.performance_manager.ui_update_ready.connect(self.handle_hardware_update)
        
        logger.info("✅ Pedals page UI initialized successfully")
    
    def set_global_pedal_system(self, hardware, output, data_queue):
        """Update the hardware input when it becomes available."""
        self.hardware_input = hardware
        logger.info("✅ Hardware input updated for pedals page")
        
        # Update connection status immediately
        self.update_connection_status()
        
        # Pass hardware input to all child widgets
        for pedal_name, pedal_widget in self.pedal_widgets.items():
            if hasattr(pedal_widget, 'layout'):
                layout = pedal_widget.layout()
                # Pass to calibration widget
                if layout.itemAt(0) and layout.itemAt(0).widget():
                    calibration_widget = layout.itemAt(0).widget()
                    if hasattr(calibration_widget, 'set_global_pedal_system'):
                        calibration_widget.set_global_pedal_system(hardware, output, data_queue)
                
                # Pass to deadzone widget
                if layout.itemAt(1) and layout.itemAt(1).widget():
                    deadzone_widget = layout.itemAt(1).widget()
                    if hasattr(deadzone_widget, 'set_global_pedal_system'):
                        deadzone_widget.set_global_pedal_system(hardware, output, data_queue)
                
                # Pass to curve manager widget
                if layout.itemAt(2) and layout.itemAt(2).widget():
                    curve_widget = layout.itemAt(2).widget()
                    if hasattr(curve_widget, 'set_global_pedal_system'):
                        curve_widget.set_global_pedal_system(hardware, output, data_queue)
        
        logger.info("✅ Hardware input passed to all child widgets")
    
    def update_connection_status(self):
        """Update the connection status indicator."""
        if not self.connection_status_label:
            return
            
        if hasattr(self, 'global_managers') and self.global_managers and hasattr(self.global_managers, 'hardware'):
            hardware = self.global_managers.hardware
            
            # Debug logging to diagnose the issue
            logger.info(f"🔍 Connection check - Hardware object: {hardware}")
            logger.info(f"🔍 Connection check - Has pedals_connected: {hasattr(hardware, 'pedals_connected')}")
            if hasattr(hardware, 'pedals_connected'):
                logger.info(f"🔍 Connection check - pedals_connected value: {hardware.pedals_connected}")
            
            # Simple check: if pedals_connected is True, then connected
            if hasattr(hardware, 'pedals_connected') and hardware.pedals_connected:
                # Pedals connected
                self.connection_status_label.setText("🟢 Pedals Connected")
                self.connection_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #22c55e;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                        max-height: 24px;
                        max-width: 400px;
                    }
                """)
                logger.info("🟢 UI Status: Pedals Connected")
            else:
                # Pedals disconnected
                self.connection_status_label.setText("🔴 Pedals Disconnected")
                self.connection_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #ef4444;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                        max-height: 24px;
                        max-width: 400px;
                    }
                """)
                logger.warning("🔴 UI Status: Pedals Disconnected")
        else:
            # Hardware manager not available
            self.connection_status_label.setText("⚪ Hardware Unavailable")
            self.connection_status_label.setStyleSheet("""
                QLabel {
                    background-color: #6b7280;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    max-height: 24px;
                    max-width: 400px;
                }
            """)
            logger.warning("⚪ UI Status: Hardware Unavailable")
            logger.info(f"🔍 Debug - Has global_managers: {hasattr(self, 'global_managers')}")
            logger.info(f"🔍 Debug - global_managers: {getattr(self, 'global_managers', 'NOT_FOUND')}")
            if hasattr(self, 'global_managers') and self.global_managers:
                logger.info(f"🔍 Debug - Has hardware attr: {hasattr(self.global_managers, 'hardware')}")
    
    def create_side_by_side_pedals(self, parent_layout):
        pedals = ['throttle', 'brake', 'clutch']
        
        for pedal in pedals:
            pedal_widget = self.create_pedal_widget(pedal)
            parent_layout.addWidget(pedal_widget, 1)  # Equal stretch
            self.pedal_widgets[pedal] = pedal_widget
    
    def create_pedal_widget(self, pedal_name: str):
        # Create main widget without scroll area - no scroll bars!
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        main_widget.setLayout(layout)
        
        # Create child widgets
        calibration_widget = PedalCalibrationWidget(pedal_name, self.global_managers)
        deadzone_widget = DeadzoneWidget(pedal_name, self.global_managers)
        curve_manager_widget = CurveManagerWidget(pedal_name, self.global_managers)
        
        # Add widgets to layout
        layout.addWidget(calibration_widget)
        layout.addWidget(deadzone_widget)
        layout.addWidget(curve_manager_widget)
        
        # Connect signals
        calibration_widget.calibration_updated.connect(
            lambda data, p=pedal_name: self.pedal_calibrated.emit(p, data)
        )
        curve_manager_widget.curve_changed.connect(
            lambda curve, p=pedal_name: self.curve_changed.emit(p, curve)
        )
        deadzone_widget.deadzone_changed.connect(
            lambda pedal, min_dz, max_dz: self.update_deadzone(pedal, min_dz, max_dz, calibration_widget)
        )
        
        return main_widget
    
    def open_calibration_wizard(self):
        try:
            from ....pedals.calibration import CalibrationWizard
            
            # Try to get hardware input from multiple sources
            hardware_input = None
            if self.hardware_input:
                hardware_input = self.hardware_input
            elif hasattr(self, 'global_managers') and self.global_managers and hasattr(self.global_managers, 'hardware'):
                hardware_input = self.global_managers.hardware
            
            if not hardware_input:
                logger.warning("Hardware input not available - cannot open calibration wizard")
                return
            
            wizard = CalibrationWizard(hardware_input, self)
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
        # Update the deadzone visualization directly with the values
        if hasattr(calibration_widget, 'draggable_plot') and calibration_widget.draggable_plot:
            calibration_widget.draggable_plot.update_deadzone_visualization(min_deadzone, max_deadzone)
    
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
        """Handle hardware updates from the main window."""
        for pedal, value in pedal_data.items():
            if pedal in self.pedal_widgets:
                widget = self.pedal_widgets[pedal]
                if hasattr(widget, 'layout'):
                    calibration_widget = widget.layout().itemAt(0).widget()
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
    
    def cleanup(self):
        """Clean up resources when the page is destroyed."""
        if self.connection_timer:
            self.connection_timer.stop()
            self.connection_timer.deleteLater()
            self.connection_timer = None
    
    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None
    
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self.cleanup()
        except Exception as e:
            logger.debug(f"Error in pedals page destructor: {e}")