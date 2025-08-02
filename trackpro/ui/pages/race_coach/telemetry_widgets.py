import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)

class TelemetryWidgetBase(QWidget):
    data_updated = pyqtSignal(str, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TelemetryWidget")
        
    def update_telemetry_data(self, data):
        pass
        
    def clear_data(self):
        pass

class QuickStatsWidget(TelemetryWidgetBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("📊 Quick Stats")
        title.setObjectName("widget-header")
        layout.addWidget(title)
        
        self.stats_container = QFrame()
        self.stats_container.setObjectName("stats-container")
        layout.addWidget(self.stats_container)
        
        layout.addStretch()

class DeltaGraphWidget(TelemetryWidgetBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("📈 Delta Analysis")
        title.setObjectName("widget-header")
        layout.addWidget(title)
        
        self.graph_container = QFrame()
        self.graph_container.setObjectName("graph-container")
        layout.addWidget(self.graph_container)
        
        layout.addStretch()