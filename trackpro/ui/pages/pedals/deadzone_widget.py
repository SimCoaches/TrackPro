import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

class DeadzoneWidget(QWidget):
    deadzone_changed = pyqtSignal(str, int, int)
    
    def __init__(self, pedal_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.pedal_name = pedal_name
        self.global_managers = global_managers
        
        self.min_deadzone = 0
        self.max_deadzone = 0
        
        self.min_deadzone_label = None
        self.max_deadzone_label = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        group = QGroupBox("Deadzone Controls")
        group.setMaximumHeight(75)
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
        
        deadzone_controls = QHBoxLayout()
        deadzone_controls.setSpacing(12)
        
        # Min deadzone - compact horizontal layout
        min_deadzone_layout = QHBoxLayout()
        self.min_deadzone_label = QLabel("Min Deadzone: 0%")
        self.min_deadzone_label.setMinimumWidth(120)
        self.min_deadzone_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 3px 4px;
                margin: 1px 0px;
            }
        """)
        min_deadzone_minus = QPushButton("-")
        min_deadzone_plus = QPushButton("+")
        min_deadzone_minus.setFixedSize(20, 20)
        min_deadzone_plus.setFixedSize(20, 20)
        
        # Blue styling for deadzone buttons
        deadzone_btn_style = """
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """
        min_deadzone_minus.setStyleSheet(deadzone_btn_style)
        min_deadzone_plus.setStyleSheet(deadzone_btn_style)
        
        min_deadzone_minus.clicked.connect(lambda: self.adjust_min_deadzone(-1))
        min_deadzone_plus.clicked.connect(lambda: self.adjust_min_deadzone(1))
        
        min_deadzone_layout.addWidget(self.min_deadzone_label)
        min_deadzone_layout.addWidget(min_deadzone_minus)
        min_deadzone_layout.addWidget(min_deadzone_plus)
        
        # Max deadzone - compact horizontal layout
        max_deadzone_layout = QHBoxLayout()
        self.max_deadzone_label = QLabel("Max Deadzone: 0%")
        self.max_deadzone_label.setMinimumWidth(120)
        self.max_deadzone_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 3px 4px;
                margin: 1px 0px;
            }
        """)
        max_deadzone_minus = QPushButton("-")
        max_deadzone_plus = QPushButton("+")
        max_deadzone_minus.setFixedSize(20, 20)
        max_deadzone_plus.setFixedSize(20, 20)
        max_deadzone_minus.setStyleSheet(deadzone_btn_style)
        max_deadzone_plus.setStyleSheet(deadzone_btn_style)
        
        max_deadzone_minus.clicked.connect(lambda: self.adjust_max_deadzone(-1))
        max_deadzone_plus.clicked.connect(lambda: self.adjust_max_deadzone(1))
        
        max_deadzone_layout.addWidget(self.max_deadzone_label)
        max_deadzone_layout.addWidget(max_deadzone_minus)
        max_deadzone_layout.addWidget(max_deadzone_plus)
        
        deadzone_controls.addLayout(min_deadzone_layout)
        deadzone_controls.addStretch()
        deadzone_controls.addLayout(max_deadzone_layout)
        
        group_layout.addLayout(deadzone_controls)
        layout.addWidget(group)
    
    def adjust_min_deadzone(self, direction: int):
        self.min_deadzone = max(0, min(50, self.min_deadzone + direction))
        self.min_deadzone_label.setText(f"Min Deadzone: {self.min_deadzone}%")
        self.emit_deadzone_update()
        logger.debug(f"Min deadzone adjusted for {self.pedal_name}: {self.min_deadzone}%")
    
    def adjust_max_deadzone(self, direction: int):
        self.max_deadzone = max(0, min(50, self.max_deadzone + direction))
        self.max_deadzone_label.setText(f"Max Deadzone: {self.max_deadzone}%")
        self.emit_deadzone_update()
        logger.debug(f"Max deadzone adjusted for {self.pedal_name}: {self.max_deadzone}%")
    
    def emit_deadzone_update(self):
        self.deadzone_changed.emit(self.pedal_name, self.min_deadzone, self.max_deadzone)
    
    def set_deadzone_values(self, min_deadzone: int, max_deadzone: int):
        self.min_deadzone = max(0, min(50, min_deadzone))
        self.max_deadzone = max(0, min(50, max_deadzone))
        
        self.min_deadzone_label.setText(f"Min Deadzone: {self.min_deadzone}%")
        self.max_deadzone_label.setText(f"Max Deadzone: {self.max_deadzone}%")
    
    def get_deadzone_values(self):
        return {
            'min_deadzone': self.min_deadzone,
            'max_deadzone': self.max_deadzone
        }