import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton, QComboBox, QLabel
from PyQt6.QtCore import pyqtSignal
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

class CurveManagerWidget(QWidget):
    curve_saved = pyqtSignal(str, str)
    curve_deleted = pyqtSignal(str, str)
    curve_changed = pyqtSignal(str)
    
    def __init__(self, pedal_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.pedal_name = pedal_name
        self.global_managers = global_managers
        
        self.curve_name_input = None
        self.custom_curves_selector = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        group = QGroupBox("Curve Management")
        group.setMaximumHeight(90)
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
        group_layout.setSpacing(6)
        group_layout.setContentsMargins(8, 8, 8, 8)
        group.setLayout(group_layout)
        
        # Save curve section - compact horizontal layout
        save_layout = QHBoxLayout()
        save_layout.setSpacing(6)
        curve_name_label = QLabel("Curve Name:")
        curve_name_label.setMaximumWidth(80)
        curve_name_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 3px 4px;
                margin: 1px 0px;
            }
        """)
        self.curve_name_input = QLineEdit()
        self.curve_name_input.setPlaceholderText("Enter custom curve name...")
        self.curve_name_input.setMaximumHeight(22)
        self.curve_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px 8px;
                color: #fefefe;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #fba43b;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        save_curve_btn = QPushButton("Save Current Curve")
        save_curve_btn.setMaximumHeight(22)
        save_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        save_curve_btn.clicked.connect(self.save_custom_curve)
        
        save_layout.addWidget(curve_name_label)
        save_layout.addWidget(self.curve_name_input)
        save_layout.addWidget(save_curve_btn)
        
        # Load curve section - compact horizontal layout
        load_layout = QHBoxLayout()
        load_layout.setSpacing(6)
        curve_selector_label = QLabel("Load Curve:")
        curve_selector_label.setMaximumWidth(80)
        curve_selector_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 3px 4px;
                margin: 1px 0px;
            }
        """)
        self.custom_curves_selector = QComboBox()
        self.custom_curves_selector.setMaximumHeight(22)
        self.custom_curves_selector.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px 8px;
                color: #fefefe;
                font-size: 11px;
            }
            QComboBox:focus {
                border-color: #fba43b;
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
            }
        """)
        delete_curve_btn = QPushButton("Delete Selected")
        delete_curve_btn.setMaximumHeight(22)
        delete_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_curve_btn.clicked.connect(self.delete_selected_curve)
        
        load_layout.addWidget(curve_selector_label)
        load_layout.addWidget(self.custom_curves_selector)
        load_layout.addWidget(delete_curve_btn)
        
        group_layout.addLayout(save_layout)
        group_layout.addLayout(load_layout)
        layout.addWidget(group)
        
        # Populate the curve selector
        self.refresh_custom_curves()
        
        # Connect curve selection change
        self.custom_curves_selector.currentTextChanged.connect(self.on_curve_selected)
    
    def set_global_pedal_system(self, hardware, output, data_queue):
        """Update the hardware input when it becomes available."""
        # Store the hardware reference for potential future use
        self.hardware_input = hardware
        logger.info(f"✅ Hardware input updated for {self.pedal_name} curve manager widget")
    
    def save_custom_curve(self):
        curve_name = self.curve_name_input.text().strip()
        if not curve_name:
            logger.warning(f"Cannot save curve for {self.pedal_name}: empty name")
            return
        
        if curve_name in self.get_default_curves():
            logger.warning(f"Cannot save curve for {self.pedal_name}: '{curve_name}' conflicts with default curve")
            return
        
        logger.info(f"Saving custom curve '{curve_name}' for {self.pedal_name}")
        
        self.curve_saved.emit(self.pedal_name, curve_name)
        self.curve_name_input.clear()
        self.refresh_custom_curves()
    
    def delete_selected_curve(self):
        selected_curve = self.custom_curves_selector.currentText()
        if selected_curve == "No custom curves":
            return
        
        logger.info(f"Deleting custom curve '{selected_curve}' for {self.pedal_name}")
        
        self.curve_deleted.emit(self.pedal_name, selected_curve)
        self.refresh_custom_curves()
    
    def refresh_custom_curves(self):
        current_text = self.custom_curves_selector.currentText()
        self.custom_curves_selector.clear()
        
        custom_curves = self.get_custom_curves()
        if custom_curves:
            self.custom_curves_selector.addItems(custom_curves)
            self.custom_curves_selector.setEnabled(True)
            
            if current_text in custom_curves:
                self.custom_curves_selector.setCurrentText(current_text)
        else:
            self.custom_curves_selector.addItem("No custom curves")
            self.custom_curves_selector.setEnabled(False)
    
    def get_default_curves(self):
        if self.pedal_name == 'brake':
            return ["Linear (Default)", "Threshold", "Trail Brake", "Endurance", "Rally", "ABS Friendly"]
        elif self.pedal_name == 'throttle':
            return ["Linear (Default)", "Track Mode", "Turbo Lag", "NA Engine", "Feathering", "Progressive"]
        elif self.pedal_name == 'clutch':
            return ["Linear (Default)", "Quick Engage", "Heel-Toe", "Bite Point Focus"]
        else:
            return ["Linear (Default)", "Progressive", "Threshold"]
    
    def get_custom_curves(self):
        try:
            from ....pedals.curve_cache import CurveCache
            cache = CurveCache()
            # CurveCache doesn't have get_custom_curves method, return empty for now
            # TODO: Implement custom curve loading from the cache
            return []
        except ImportError:
            logger.warning("CurveCache not available - custom curves disabled")
            return []
        except Exception as e:
            logger.debug(f"Custom curves not implemented yet for {self.pedal_name}")
            return []
    
    def add_custom_curve(self, curve_name: str):
        self.refresh_custom_curves()
        if curve_name in [self.custom_curves_selector.itemText(i) for i in range(self.custom_curves_selector.count())]:
            self.custom_curves_selector.setCurrentText(curve_name)
    
    def remove_custom_curve(self, curve_name: str):
        self.refresh_custom_curves()
    
    def on_curve_selected(self, curve_name: str):
        """Handle curve selection change."""
        if curve_name and curve_name != "No custom curves":
            logger.info(f"Curve selected for {self.pedal_name}: {curve_name}")
            self.curve_changed.emit(curve_name)