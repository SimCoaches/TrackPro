"""Shared imports and constants for UI modules."""

# Shared imports for UI components

# Standard library imports
import sys
import os
import logging
import time
import traceback
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Third party imports - PyQt6 (updated from PyQt5)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QRadioButton, QGroupBox, QTabWidget, QStackedWidget, QSplitter,
    QScrollArea, QFrame, QSizePolicy, QSpacerItem, QMessageBox,
    QDialog, QDialogButtonBox, QProgressBar, QSlider, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDateEdit, QFileDialog, QInputDialog, QGridLayout, QFormLayout,
    QSystemTrayIcon, QMenu, QStatusBar
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QSize, QRect, QPoint,
    QPropertyAnimation, QEasingCurve, QRectF, QPointF, QDate,
    QRegularExpression
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QPen, QBrush,
    QLinearGradient, QGradient, QMouseEvent, QWheelEvent, QPaintEvent,
    QRegularExpressionValidator, QScreen, QAction
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

# Optional chart imports - may not be available in all PyQt6 installations
try:
    from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries, QAreaSeries
    CHARTS_AVAILABLE = True
except ImportError:
    # Create dummy classes with required methods if charts not available
    CHARTS_AVAILABLE = False
    
    class QChart:
        def __init__(self): pass
        def setBackgroundVisible(self, visible): pass
        def setBackgroundBrush(self, brush): pass
        def setPlotAreaBackgroundVisible(self, visible): pass
        def setPlotAreaBackgroundBrush(self, brush): pass
        def setTitleBrush(self, brush): pass
        def setAnimationOptions(self, options): pass
        def legend(self): return self
        def hide(self): pass
        def setContentsMargins(self, left, top, right, bottom): pass
        def addSeries(self, series): pass
        def addAxis(self, axis, alignment): pass  # PyQt6 API
        def removeAxis(self, axis): pass  # PyQt6 API
        def setMargins(self, margins): pass
        def mapToPosition(self, point): 
            from PyQt6.QtCore import QPoint
            return QPoint(0, 0)
        def mapToValue(self, point): 
            from PyQt6.QtCore import QPointF
            return QPointF(0, 0)
        
        class AnimationOptions:
            NoAnimation = 0
        NoAnimation = 0
    
    class QChartView(QWidget):
        class ViewportUpdateMode:
            MinimalViewportUpdate = 0
        def __init__(self, chart=None, parent=None): 
            super().__init__(parent)
            self.chart_obj = chart
        def setRenderHint(self, hint): pass
        def setViewportUpdateMode(self, mode): pass
        def setMouseTracking(self, enable): pass
        def setMinimumHeight(self, height): pass
        def setSizePolicy(self, policy1, policy2): pass
        def setContentsMargins(self, left, top, right, bottom): pass
        def chart(self): return self.chart_obj or QChart()
        
    class QLineSeries:
        def __init__(self): self.points = []
        def clear(self): self.points = []
        def append(self, x, y=None): 
            if y is None and hasattr(x, 'x') and hasattr(x, 'y'):
                self.points.append((x.x(), x.y()))
            else:
                self.points.append((x, y))
        def setPen(self, pen): pass
        def setUseOpenGL(self, use): pass
        def count(self): return len(self.points)
        def at(self, index): 
            if index < len(self.points):
                return QPointF(self.points[index][0], self.points[index][1])
            return QPointF(0, 0)
        def attachAxis(self, axis): pass  # PyQt6 API
        def detachAxis(self, axis): pass  # PyQt6 API
            
    class QValueAxis:
        def __init__(self): pass
        def setRange(self, min_val, max_val): pass
        def setMin(self, min_val): pass
        def setMax(self, max_val): pass
        def setTitleText(self, text): pass
        def setTitleBrush(self, brush): pass
        def setLabelsBrush(self, brush): pass
        def setLabelsFont(self, font): pass
        def setTitleFont(self, font): pass
        def setGridLineVisible(self, visible): pass
        def setMinorGridLineVisible(self, visible): pass
        def setLabelsVisible(self, visible): pass
        def setTickCount(self, count): pass
        def setLabelFormat(self, format): pass
        def setGridLinePen(self, pen): pass
        def setMinorGridLinePen(self, pen): pass
        
    class QScatterSeries:
        def __init__(self): self.points = []
        def clear(self): self.points = []
        def append(self, x, y=None):
            if y is None and hasattr(x, 'x') and hasattr(x, 'y'):
                self.points.append((x.x(), x.y()))
            else:
                self.points.append((x, y))
        def setMarkerSize(self, size): pass
        def setColor(self, color): pass
        def setBorderColor(self, color): pass
        def setUseOpenGL(self, use): pass
        def count(self): return len(self.points)
        def at(self, index):
            if index < len(self.points):
                return QPointF(self.points[index][0], self.points[index][1])
            return QPointF(0, 0)
        def attachAxis(self, axis): pass  # PyQt6 API
        def detachAxis(self, axis): pass  # PyQt6 API
            
    class QAreaSeries:
        def __init__(self): pass
        def setPen(self, pen): pass
        def setBrush(self, brush): pass
        def setUseOpenGL(self, use): pass
        def setLowerSeries(self, series): pass
        def setUpperSeries(self, series): pass
        def attachAxis(self, axis): pass  # PyQt6 API
        def detachAxis(self, axis): pass  # PyQt6 API

# Version information - hardcoded to avoid cyclic imports
__version__ = "1.5.5"

# Import from parent module
from ..config import config
from ..pedals.calibration import CalibrationWizard
from ..pedals.profile_dialog import PedalProfileDialog
from ..race_coach.ui import RaceCoachWidget
# Gamification imports - these are in the future directory
try:
    from future.gamification.trackpro_gamification.ui.race_pass_view import RacePassViewWidget
    from future.gamification.trackpro_gamification.ui.enhanced_quest_view import EnhancedQuestViewWidget
    GAMIFICATION_AVAILABLE = True
except ImportError:
    # Fallback implementations if gamification is not available
    class RacePassViewWidget:
        def __init__(self, *args, **kwargs):
            from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
            super().__init__()
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("Race Pass features not available"))
    
    class EnhancedQuestViewWidget:
        def __init__(self, *args, **kwargs):
            from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
            super().__init__()
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("Quest features not available"))
    
    GAMIFICATION_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

# Default curve types
DEFAULT_CURVE_TYPES = ["Linear", "S-Curve", "Aggressive", "Progressive", "Custom"]

# Community UI imports - use standard imports to avoid circular import issues
try:
    from .community_ui import CommunityMainWidget
    from .social_ui import SocialMainWidget
    from .achievements_ui import GamificationMainWidget
    from .content_management_ui import ContentManagementMainWidget
    from .user_account_ui import UserAccountMainWidget
    
    # Import community dialog functions
    def open_community_dialog(parent, managers, user_id, tab="social"):
        """Open the community dialog with the specified tab."""
        # Check if QApplication exists before creating widgets
        if QApplication.instance() is None:
            print("No QApplication instance available - cannot create community dialog")
            return
            
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("TrackPro Community")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        community_widget = CommunityMainWidget(managers, user_id)
        layout.addWidget(community_widget)
        
        dialog.exec()

    def create_community_menu_action(parent, managers, user_id):
        """Create a community menu action."""
        action = QAction("🌐 Community", parent)
        action.setStatusTip("Access community features")
        action.triggered.connect(lambda: open_community_dialog(parent, managers, user_id))
        return action

    def open_social_features(parent, managers, user_id):
        """Open social features."""
        open_community_dialog(parent, managers, user_id, "social")

    def open_community_features(parent, managers, user_id):
        """Open community features."""
        open_community_dialog(parent, managers, user_id, "community")

    def open_content_management(parent, managers, user_id):
        """Open content management."""
        open_community_dialog(parent, managers, user_id, "content")

    def open_achievements(parent, managers, user_id):
        """Open achievements."""
        open_community_dialog(parent, managers, user_id, "achievements")

    def open_account_settings(parent, managers, user_id):
        """Open account settings."""
        open_community_dialog(parent, managers, user_id, "account")
    
    COMMUNITY_UI_AVAILABLE = True
    print("✅ Successfully imported community UI functions")
    
except ImportError as e:
    print(f"❌ Failed to import community UI: {e}")
    COMMUNITY_UI_AVAILABLE = False
    
    # Fallback implementations only if import fails
    def open_community_dialog(parent, managers, user_id, tab="social"):
        """Fallback implementation."""
        # Check if QApplication exists before creating widgets
        if QApplication.instance() is None:
            print("No QApplication instance available - cannot show community dialog")
            return
            
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Community Features", "Community features are not available in this build.")

    def create_community_menu_action(parent, managers, user_id):
        """Fallback implementation."""
        action = QAction("🌐 Community", parent)
        action.setStatusTip("Community features not available")
        action.triggered.connect(lambda: open_community_dialog(parent, managers, user_id))
        return action

    def open_social_features(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "social")

    def open_community_features(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "community")

    def open_content_management(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "content")

    def open_achievements(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "achievements")

    def open_account_settings(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "account")

except Exception as e:
    print(f"❌ Unexpected error importing community UI: {e}")
    COMMUNITY_UI_AVAILABLE = False
    
    # Same fallback implementations for unexpected errors
    def open_community_dialog(parent, managers, user_id, tab="social"):
        """Fallback implementation."""
        # Check if QApplication exists before creating widgets
        if QApplication.instance() is None:
            print("No QApplication instance available - cannot show community dialog")
            return
            
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Community Features", "Community features are not available in this build.")

    def create_community_menu_action(parent, managers, user_id):
        """Fallback implementation."""
        action = QAction("🌐 Community", parent)
        action.setStatusTip("Community features not available")
        action.triggered.connect(lambda: open_community_dialog(parent, managers, user_id))
        return action

    def open_social_features(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "social")

    def open_community_features(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "community")

    def open_content_management(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "content")

    def open_achievements(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "achievements")

    def open_account_settings(parent, managers, user_id):
        """Fallback implementation."""
        open_community_dialog(parent, managers, user_id, "account") 