import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSlider, QSpinBox
from PyQt6.QtCore import pyqtSignal, Qt
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

class HandbrakeDeadzoneWidget(QWidget):
    deadzone_changed = pyqtSignal(str, int, int)  # handbrake_name, min_deadzone, max_deadzone
    
    def __init__(self, handbrake_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.handbrake_name = handbrake_name
        self.global_managers = global_managers
        
        self.min_deadzone = 0
        self.max_deadzone = 0
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        group = QGroupBox("Deadzone Settings")
        group.setMaximumHeight(120)
        group.setStyleSheet("""
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
        
        group_layout = QVBoxLayout()
        
        # Min deadzone
        min_layout = QHBoxLayout()
        min_label = QLabel("Min Deadzone:")
        min_label.setMinimumWidth(100)
        min_label.setStyleSheet("color: #fefefe; font-size: 11px;")
        
        self.min_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_slider.setMinimum(0)
        self.min_slider.setMaximum(20)
        self.min_slider.setValue(0)
        self.min_slider.valueChanged.connect(self.on_min_deadzone_changed)
        self.min_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #444444;
                height: 8px;
                background: #252525;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #e74c3c;
                border: 1px solid #c0392b;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #e74c3c;
                border-radius: 4px;
            }
        """)
        
        self.min_spinbox = QSpinBox()
        self.min_spinbox.setMinimum(0)
        self.min_spinbox.setMaximum(20)
        self.min_spinbox.setValue(0)
        self.min_spinbox.setSuffix("%")
        self.min_spinbox.setMaximumWidth(60)
        self.min_spinbox.valueChanged.connect(self.on_min_deadzone_spinbox_changed)
        self.min_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 3px;
                color: #fefefe;
                font-size: 11px;
                padding: 2px;
            }
        """)
        
        min_layout.addWidget(min_label)
        min_layout.addWidget(self.min_slider)
        min_layout.addWidget(self.min_spinbox)
        
        # Max deadzone
        max_layout = QHBoxLayout()
        max_label = QLabel("Max Deadzone:")
        max_label.setMinimumWidth(100)
        max_label.setStyleSheet("color: #fefefe; font-size: 11px;")
        
        self.max_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_slider.setMinimum(0)
        self.max_slider.setMaximum(20)
        self.max_slider.setValue(0)
        self.max_slider.valueChanged.connect(self.on_max_deadzone_changed)
        self.max_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #444444;
                height: 8px;
                background: #252525;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #e74c3c;
                border: 1px solid #c0392b;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #e74c3c;
                border-radius: 4px;
            }
        """)
        
        self.max_spinbox = QSpinBox()
        self.max_spinbox.setMinimum(0)
        self.max_spinbox.setMaximum(20)
        self.max_spinbox.setValue(0)
        self.max_spinbox.setSuffix("%")
        self.max_spinbox.setMaximumWidth(60)
        self.max_spinbox.valueChanged.connect(self.on_max_deadzone_spinbox_changed)
        self.max_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 3px;
                color: #fefefe;
                font-size: 11px;
                padding: 2px;
            }
        """)
        
        max_layout.addWidget(max_label)
        max_layout.addWidget(self.max_slider)
        max_layout.addWidget(self.max_spinbox)
        
        group_layout.addLayout(min_layout)
        group_layout.addLayout(max_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def on_min_deadzone_changed(self, value):
        """Handle min deadzone slider change."""
        self.min_deadzone = value
        self.min_spinbox.blockSignals(True)
        self.min_spinbox.setValue(value)
        self.min_spinbox.blockSignals(False)
        self.emit_deadzone_change()
    
    def on_min_deadzone_spinbox_changed(self, value):
        """Handle min deadzone spinbox change."""
        self.min_deadzone = value
        self.min_slider.blockSignals(True)
        self.min_slider.setValue(value)
        self.min_slider.blockSignals(False)
        self.emit_deadzone_change()
    
    def on_max_deadzone_changed(self, value):
        """Handle max deadzone slider change."""
        self.max_deadzone = value
        self.max_spinbox.blockSignals(True)
        self.max_spinbox.setValue(value)
        self.max_spinbox.blockSignals(False)
        self.emit_deadzone_change()
    
    def on_max_deadzone_spinbox_changed(self, value):
        """Handle max deadzone spinbox change."""
        self.max_deadzone = value
        self.max_slider.blockSignals(True)
        self.max_slider.setValue(value)
        self.max_slider.blockSignals(False)
        self.emit_deadzone_change()
    
    def emit_deadzone_change(self):
        """Emit deadzone change signal."""
        self.deadzone_changed.emit(self.handbrake_name, self.min_deadzone, self.max_deadzone)
        logger.debug(f"Handbrake deadzone changed: min={self.min_deadzone}%, max={self.max_deadzone}%")
    
    def set_deadzone_values(self, min_deadzone: int, max_deadzone: int):
        """Set deadzone values from external source."""
        self.min_deadzone = min_deadzone
        self.max_deadzone = max_deadzone
        
        # Update UI without triggering signals
        self.min_slider.blockSignals(True)
        self.min_spinbox.blockSignals(True)
        self.max_slider.blockSignals(True)
        self.max_spinbox.blockSignals(True)
        
        self.min_slider.setValue(min_deadzone)
        self.min_spinbox.setValue(min_deadzone)
        self.max_slider.setValue(max_deadzone)
        self.max_spinbox.setValue(max_deadzone)
        
        self.min_slider.blockSignals(False)
        self.min_spinbox.blockSignals(False)
        self.max_slider.blockSignals(False)
        self.max_spinbox.blockSignals(False)
    
    def get_deadzone_values(self):
        """Get current deadzone values."""
        return {
            'min_deadzone': self.min_deadzone,
            'max_deadzone': self.max_deadzone
        }