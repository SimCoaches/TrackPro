import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

class HandbrakeCurveManagerWidget(QWidget):
    curve_changed = pyqtSignal(str)  # curve_name
    
    def __init__(self, handbrake_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.handbrake_name = handbrake_name
        self.global_managers = global_managers
        
        self.current_curve = "Linear (Default)"
        self.available_curves = [
            "Linear (Default)",
            "Progressive", 
            "Aggressive",
            "Smooth"
        ]
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        group = QGroupBox("Response Curve")
        group.setMaximumHeight(100)
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
        
        # Curve selection
        curve_layout = QHBoxLayout()
        
        curve_label = QLabel("Curve Type:")
        curve_label.setMinimumWidth(80)
        curve_label.setStyleSheet("color: #fefefe; font-size: 11px;")
        
        self.curve_combo = QComboBox()
        self.curve_combo.addItems(self.available_curves)
        self.curve_combo.setCurrentText(self.current_curve)
        self.curve_combo.currentTextChanged.connect(self.on_curve_changed)
        self.curve_combo.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 3px;
                color: #fefefe;
                font-size: 11px;
                padding: 4px;
                min-width: 100px;
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
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                border: 1px solid #444444;
                color: #fefefe;
                selection-background-color: #e74c3c;
            }
        """)
        
        save_btn = QPushButton("Save Curve")
        save_btn.setMaximumWidth(80)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.save_curve)
        
        curve_layout.addWidget(curve_label)
        curve_layout.addWidget(self.curve_combo)
        curve_layout.addWidget(save_btn)
        curve_layout.addStretch()
        
        # Curve description
        self.curve_description = QLabel(self.get_curve_description(self.current_curve))
        self.curve_description.setStyleSheet("""
            QLabel {
                color: #bdc3c7;
                font-size: 10px;
                font-style: italic;
                padding: 2px;
            }
        """)
        
        group_layout.addLayout(curve_layout)
        group_layout.addWidget(self.curve_description)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def get_curve_description(self, curve_name: str) -> str:
        """Get description for the selected curve."""
        descriptions = {
            "Linear (Default)": "Direct 1:1 response - no modification",
            "Progressive": "Gentle start, stronger at the end",
            "Aggressive": "Strong start, levels off quickly", 
            "Smooth": "Smooth progressive response curve"
        }
        return descriptions.get(curve_name, "Custom response curve")
    
    def on_curve_changed(self, curve_name: str):
        """Handle curve selection change."""
        self.current_curve = curve_name
        self.curve_description.setText(self.get_curve_description(curve_name))
        self.curve_changed.emit(curve_name)
        logger.info(f"Handbrake curve changed to: {curve_name}")
    
    def save_curve(self):
        """Save the current curve settings."""
        # This would save the curve to the calibration system
        logger.info(f"Saving handbrake curve: {self.current_curve}")
        
        # Emit signal to notify parent
        self.curve_changed.emit(self.current_curve)
    
    def set_curve(self, curve_name: str):
        """Set the curve from external source."""
        if curve_name in self.available_curves:
            self.current_curve = curve_name
            self.curve_combo.blockSignals(True)
            self.curve_combo.setCurrentText(curve_name)
            self.curve_combo.blockSignals(False)
            self.curve_description.setText(self.get_curve_description(curve_name))
    
    def get_current_curve(self) -> str:
        """Get the currently selected curve."""
        return self.current_curve
    
    def add_custom_curve(self, curve_name: str):
        """Add a custom curve to the available options."""
        if curve_name not in self.available_curves:
            self.available_curves.append(curve_name)
            self.curve_combo.addItem(curve_name)
            logger.info(f"Added custom handbrake curve: {curve_name}")
    
    def remove_curve(self, curve_name: str):
        """Remove a curve from available options."""
        if curve_name in self.available_curves and curve_name != "linear":
            self.available_curves.remove(curve_name)
            index = self.curve_combo.findText(curve_name)
            if index >= 0:
                self.curve_combo.removeItem(index)
            
            # If we removed the current curve, switch to linear
            if self.current_curve == curve_name:
                self.set_curve("Linear (Default)")
            
            logger.info(f"Removed handbrake curve: {curve_name}")
    
    def get_curve_settings(self):
        """Get current curve settings."""
        return {
            'curve_type': self.current_curve,
            'available_curves': self.available_curves.copy()
        }