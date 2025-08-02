"""Professional telemetry hover information widget.

This widget provides a centralized display for telemetry hover information,
designed to match professional racing telemetry software aesthetics.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TelemetryHoverInfoWidget(QWidget):
    """Professional centralized hover information for telemetry graphs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Default values
        self._distance = 0.0
        self._lap_a_data = {}
        self._lap_b_data = {}
        self._comparison_mode = False
        
        self.setup_ui()
        self.setup_styling()
        
    def setup_ui(self):
        """Setup the hover info UI layout - completely horizontal."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(3)  # Very tight spacing
        
        # Distance info
        self.distance_label = QLabel("Distance: 0.0m")
        self.distance_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.distance_label.setMinimumWidth(110)
        self.main_layout.addWidget(self.distance_label)
        
        # Vertical separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #30363d; margin: 0px 2px;")
        self.main_layout.addWidget(separator1)
        
        # Lap A data (horizontal)
        self.lap_a_title = QLabel("Lap A:")
        self.lap_a_title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.lap_a_title.setStyleSheet("color: #00BFFF; margin-right: 2px;")
        self.main_layout.addWidget(self.lap_a_title)
        
        self.lap_a_throttle = QLabel("Throttle: --")
        self.lap_a_brake = QLabel("Brake: --")
        self.lap_a_speed = QLabel("Speed: --")
        self.lap_a_gear = QLabel("Gear: --")
        self.lap_a_steering = QLabel("Steering: --")
        
        for label in [self.lap_a_throttle, self.lap_a_brake, self.lap_a_speed, self.lap_a_gear, self.lap_a_steering]:
            label.setFont(QFont("Arial", 8))
            label.setStyleSheet("margin: 0px 1px;")
            self.main_layout.addWidget(label)
        
        # Lap B data (horizontal, initially hidden)
        self.lap_b_separator = QLabel("|")
        self.lap_b_separator.setStyleSheet("color: #30363d; margin: 0px 2px;")
        self.main_layout.addWidget(self.lap_b_separator)
        
        self.lap_b_title = QLabel("Lap B:")
        self.lap_b_title.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.lap_b_title.setStyleSheet("color: #FF8C00; margin-right: 2px;")
        self.main_layout.addWidget(self.lap_b_title)
        
        self.lap_b_throttle = QLabel("Throttle: --")
        self.lap_b_brake = QLabel("Brake: --")
        self.lap_b_speed = QLabel("Speed: --")
        self.lap_b_gear = QLabel("Gear: --")
        self.lap_b_steering = QLabel("Steering: --")
        
        self.lap_b_labels = [self.lap_b_throttle, self.lap_b_brake, self.lap_b_speed, self.lap_b_gear, self.lap_b_steering]
        for label in self.lap_b_labels:
            label.setFont(QFont("Arial", 8))
            label.setStyleSheet("margin: 0px 1px;")
            self.main_layout.addWidget(label)
        
        # Initially hide Lap B (comparison mode)
        self.lap_b_separator.setVisible(False)
        self.lap_b_title.setVisible(False)
        for label in self.lap_b_labels:
            label.setVisible(False)
        
        # Add stretch to push everything to the left
        self.main_layout.addStretch()
        
    def setup_styling(self):
        """Setup professional styling for the hover info widget."""
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 6px;
                color: #e6edf3;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #e6edf3;
            }
        """)
        
        self.setFixedHeight(40)  # Much shorter since it's horizontal now
        
    def update_distance(self, distance):
        """Update the distance display."""
        self._distance = distance
        self.distance_label.setText(f"Distance: {distance:.1f}m")
        
    def update_lap_data(self, lap_a_data=None, lap_b_data=None):
        """Update lap data display."""
        if lap_a_data:
            self._lap_a_data = lap_a_data
            self.lap_a_throttle.setText(f"<b>Throttle:</b> {lap_a_data.get('throttle', '--')}")
            self.lap_a_brake.setText(f"<b>Brake:</b> {lap_a_data.get('brake', '--')}")
            self.lap_a_speed.setText(f"<b>Speed:</b> {lap_a_data.get('speed', '--')}")
            self.lap_a_gear.setText(f"<b>Gear:</b> {lap_a_data.get('gear', '--')}")
            self.lap_a_steering.setText(f"<b>Steering:</b> {lap_a_data.get('steering', '--')}")
            
        if lap_b_data:
            self._lap_b_data = lap_b_data
            self.lap_b_throttle.setText(f"<b>Throttle:</b> {lap_b_data.get('throttle', '--')}")
            self.lap_b_brake.setText(f"<b>Brake:</b> {lap_b_data.get('brake', '--')}")
            self.lap_b_speed.setText(f"<b>Speed:</b> {lap_b_data.get('speed', '--')}")
            self.lap_b_gear.setText(f"<b>Gear:</b> {lap_b_data.get('gear', '--')}")
            self.lap_b_steering.setText(f"<b>Steering:</b> {lap_b_data.get('steering', '--')}")
            
    def set_comparison_mode(self, enabled):
        """Show/hide Lap B data based on comparison mode."""
        self._comparison_mode = enabled
        self.lap_b_separator.setVisible(enabled)
        self.lap_b_title.setVisible(enabled)
        for label in self.lap_b_labels:
            label.setVisible(enabled)
        
    def clear_data(self):
        """Clear all data display."""
        self.distance_label.setText("Distance: --")
        
        for label in [self.lap_a_throttle, self.lap_a_brake, self.lap_a_speed, self.lap_a_gear, self.lap_a_steering]:
            label.setText(label.text().split(':')[0] + ": --")
            
        for label in [self.lap_b_throttle, self.lap_b_brake, self.lap_b_speed, self.lap_b_gear, self.lap_b_steering]:
            label.setText(label.text().split(':')[0] + ": --")