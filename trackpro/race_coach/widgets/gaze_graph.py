# Eye tracking gaze visualization widget
import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor

logger = logging.getLogger(__name__)


class GazeGraphWidget(QWidget):
    """Widget to visualize eye tracking gaze data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gaze_data = []
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Gaze Analysis")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Placeholder for gaze visualization
        self.gaze_display = QLabel("Eye tracking data will be displayed here")
        self.gaze_display.setAlignment(Qt.AlignCenter)
        self.gaze_display.setMinimumHeight(200)
        self.gaze_display.setStyleSheet("border: 1px solid gray; background-color: #2a2a2a; color: white;")
        layout.addWidget(self.gaze_display)
        
        self.setLayout(layout)
        
    def set_data(self, gaze_data):
        """Set gaze data for visualization."""
        self.gaze_data = gaze_data
        if gaze_data:
            self.gaze_display.setText(f"Gaze data points: {len(gaze_data)}")
        else:
            self.gaze_display.setText("No eye tracking data available")
    
    def clear_data(self):
        """Clear all data from visualization."""
        self.set_data([]) 