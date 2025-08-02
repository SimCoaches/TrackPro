"""Professional telemetry legend widget for lap comparison.

This widget provides a centralized legend for telemetry graphs,
designed to match professional racing telemetry software aesthetics.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class TelemetryLegendWidget(QWidget):
    """Professional centralized legend for telemetry graphs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Default lap names - set before UI setup
        self._lap_a_name = "Lap A"
        self._lap_b_name = "Lap B"
        
        self.setup_ui()
        self.setup_styling()
        
    def setup_ui(self):
        """Setup the legend UI layout."""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 5)
        self.main_layout.setSpacing(20)
        
        # Legend title
        self.title_label = QLabel("Legend:")
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.main_layout.addWidget(self.title_label)
        
        # Lap A legend
        self.lap_a_container = QFrame()
        self.lap_a_layout = QHBoxLayout(self.lap_a_container)
        self.lap_a_layout.setContentsMargins(0, 0, 0, 0)
        self.lap_a_layout.setSpacing(5)
        
        self.lap_a_color_box = QLabel()
        self.lap_a_color_box.setFixedSize(16, 3)
        self.lap_a_color_box.setStyleSheet("background-color: #00BFFF; border: none;")
        
        self.lap_a_label = QLabel(self._lap_a_name)
        self.lap_a_label.setFont(QFont("Arial", 9))
        
        self.lap_a_layout.addWidget(self.lap_a_color_box)
        self.lap_a_layout.addWidget(self.lap_a_label)
        self.main_layout.addWidget(self.lap_a_container)
        
        # Lap B legend
        self.lap_b_container = QFrame()
        self.lap_b_layout = QHBoxLayout(self.lap_b_container)
        self.lap_b_layout.setContentsMargins(0, 0, 0, 0)
        self.lap_b_layout.setSpacing(5)
        
        self.lap_b_color_box = QLabel()
        self.lap_b_color_box.setFixedSize(16, 3)
        self.lap_b_color_box.setStyleSheet("background-color: #FF8C00; border: none;")
        
        self.lap_b_label = QLabel(self._lap_b_name)
        self.lap_b_label.setFont(QFont("Arial", 9))
        
        self.lap_b_layout.addWidget(self.lap_b_color_box)
        self.lap_b_layout.addWidget(self.lap_b_label)
        self.main_layout.addWidget(self.lap_b_container)
        
        # Add stretch to push everything to the left
        self.main_layout.addStretch()
        
        # Initially hide Lap B (comparison mode)
        self.lap_b_container.setVisible(False)
        
    def setup_styling(self):
        """Setup professional styling for the legend."""
        self.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #e6edf3;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #e6edf3;
            }
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        self.title_label.setStyleSheet("""
            QLabel {
                color: #7dd3fc;
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        
    def update_lap_names(self, lap_a_name=None, lap_b_name=None):
        """Update the lap names in the legend."""
        if lap_a_name:
            self._lap_a_name = lap_a_name
            self.lap_a_label.setText(lap_a_name)
            
        if lap_b_name:
            self._lap_b_name = lap_b_name
            self.lap_b_label.setText(lap_b_name)
            
    def set_comparison_mode(self, enabled):
        """Show/hide Lap B legend based on comparison mode."""
        self.lap_b_container.setVisible(enabled)
        
    def update_lap_times(self, lap_a_time=None, lap_b_time=None):
        """Update legend with lap times if provided."""
        lap_a_text = self._lap_a_name
        if lap_a_time:
            lap_a_text += f" ({lap_a_time})"
        self.lap_a_label.setText(lap_a_text)
        
        if lap_b_time and self.lap_b_container.isVisible():
            lap_b_text = self._lap_b_name + f" ({lap_b_time})"
            self.lap_b_label.setText(lap_b_text)