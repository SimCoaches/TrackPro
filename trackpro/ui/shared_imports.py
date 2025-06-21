"""Shared imports and constants for UI modules."""

import os
import sys
import logging
import traceback
import time
import math
from typing import Optional, Any

# Version information - hardcoded to avoid cyclic imports
__version__ = "1.5.2"

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QLabel, QPushButton, QVBoxLayout, 
    QHBoxLayout, QFrame, QSplitter, QWidget, QMessageBox, 
    QSlider, QComboBox, QSpinBox, QCheckBox, QProgressBar,
    QDialog, QFileDialog, QFormLayout, QLineEdit, QAction,
    QMenu, QApplication, QStyleFactory, QGridLayout, QTextEdit,
    QMenuBar, QMenu, QDialogButtonBox, QStackedWidget, QRadioButton, 
    QButtonGroup, QGroupBox, QStatusBar, QProgressDialog, QSizePolicy,
    QSystemTrayIcon
)
from PyQt5.QtCore import (
    Qt, QPointF, QTimer, pyqtSignal, QSettings, QThread, 
    pyqtSlot, QSize, QRectF, QMargins, QObject
)
from PyQt5.QtGui import (
    QPalette, QColor, QIcon, QPen, QBrush, QPainterPath, QFont,
    QPainter, QLinearGradient, QMouseEvent, QHideEvent, QShowEvent,
    QKeySequence, QDesktopServices, QPixmap
)
from PyQt5.QtWidgets import QGraphicsOpacityEffect
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries, QAreaSeries

# Import from parent module
from ..config import config
from ..pedals.calibration import CalibrationWizard
from ..pedals.profile_dialog import PedalProfileDialog
from ..race_coach.ui import RaceCoachWidget
from trackpro.gamification.ui.race_pass_view import RacePassViewWidget
from trackpro.gamification.ui.enhanced_quest_view import EnhancedQuestViewWidget

# Set up logging
logger = logging.getLogger(__name__)

# Default curve types
DEFAULT_CURVE_TYPES = ["Linear", "S-Curve", "Aggressive", "Progressive", "Custom"]

# Community UI imports - import the real implementations
try:
    # Add the ui directory to Python path temporarily for importing
    ui_dir = os.path.join(os.path.dirname(__file__))
    if ui_dir not in sys.path:
        sys.path.insert(0, ui_dir)
    
    # Import the real community UI functions directly from the file
    import importlib.util
    
    # Load all UI component modules first to resolve dependencies
    ui_modules = {}
    ui_files = [
        'community_ui.py',
        'social_ui.py', 
        'content_management_ui.py',
        'achievements_ui.py',
        'user_account_ui.py',
        'main_community_ui.py'
    ]
    
    # Load each module and add to sys.modules to resolve relative imports
    for ui_file in ui_files:
        module_name = ui_file[:-3]  # Remove .py extension
        ui_file_path = os.path.join(ui_dir, ui_file)
        if os.path.exists(ui_file_path):
            spec = importlib.util.spec_from_file_location(f"trackpro.ui.{module_name}", ui_file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"trackpro.ui.{module_name}"] = module
            ui_modules[module_name] = module
    
    # Now execute the modules in dependency order
    for module_name in ['community_ui', 'social_ui', 'content_management_ui', 'achievements_ui', 'user_account_ui']:
        if module_name in ui_modules:
            ui_modules[module_name].__spec__.loader.exec_module(ui_modules[module_name])
    
    # Finally execute main_community_ui which depends on the others
    if 'main_community_ui' in ui_modules:
        ui_modules['main_community_ui'].__spec__.loader.exec_module(ui_modules['main_community_ui'])
        main_community_ui = ui_modules['main_community_ui']
        
        # Import the functions we need
        open_community_dialog = main_community_ui.open_community_dialog
        create_community_menu_action = main_community_ui.create_community_menu_action
        open_social_features = main_community_ui.open_social_features
        open_community_features = main_community_ui.open_community_features
        open_content_management = main_community_ui.open_content_management
        open_achievements = main_community_ui.open_achievements
        open_account_settings = main_community_ui.open_account_settings
    
    COMMUNITY_UI_AVAILABLE = True
    print("✅ Successfully imported real community UI functions")
    
except ImportError as e:
    print(f"❌ Failed to import community UI: {e}")
    COMMUNITY_UI_AVAILABLE = False
    
    # Fallback implementations only if import fails
    def open_community_dialog(parent, managers, user_id, tab="social"):
        """Fallback implementation."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(parent, "Community Features", "Community features are not available in this build.")

    def create_community_menu_action(parent, managers, user_id):
        """Fallback implementation."""
        from PyQt5.QtWidgets import QAction
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