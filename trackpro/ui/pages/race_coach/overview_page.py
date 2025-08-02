import logging
import math
import statistics
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QComboBox, QSpinBox, QSlider, QGroupBox, QTextEdit, QScrollArea,
    QFrame, QSizePolicy, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPixmap
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class SessionSummaryCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 6px;
                border: 2px solid #2a82da;
            }
        """)
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel("🏁 LAST SESSION")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin: 0px;
            padding: 1px 0px;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.session_time_label = QLabel("")
        self.session_time_label.setStyleSheet("color: #888; font-size: 10px;")
        header_layout.addWidget(self.session_time_label)
        
        layout.addLayout(header_layout)
        
        info_layout = QGridLayout()
        info_layout.setSpacing(2)
        
        self.track_car_label = QLabel("Track & Car: Loading...")
        self.track_car_label.setStyleSheet("font-size: 18px; color: #e0e0e0; font-weight: bold;")
        info_layout.addWidget(self.track_car_label, 0, 0, 1, 2)
        
        self.duration_label = QLabel("Duration: --")
        self.laps_label = QLabel("Laps: --")
        self.best_lap_label = QLabel("Best: --:--.---")
        self.improvement_label = QLabel("Improvement: --")
        
        labels = [self.duration_label, self.laps_label, self.best_lap_label, self.improvement_label]
        for i, label in enumerate(labels):
            label.setStyleSheet("color: #e0e0e0; font-size: 18px;")
            row, col = divmod(i, 2)
            info_layout.addWidget(label, row + 1, col)
        
        layout.addLayout(info_layout)

class PerformanceAnalysisWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #505050;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        
        title = QLabel("📊 PERFORMANCE ANALYSIS")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2a82da;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 14px;
                padding: 8px;
            }
        """)
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMinimumHeight(120)
        layout.addWidget(self.analysis_text)

class NextSessionPlanWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #505050;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        
        title = QLabel("🎯 NEXT SESSION PLAN")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #28a745;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)
        
        self.plan_text = QTextEdit()
        self.plan_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 14px;
                padding: 8px;
            }
        """)
        self.plan_text.setReadOnly(True)
        self.plan_text.setMinimumHeight(120)
        layout.addWidget(self.plan_text)

class OverviewPage(BasePage):
    def __init__(self, global_managers=None):
        super().__init__("Race Coach Overview", global_managers)
        
    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QLabel("🏁 Race Coach Overview")
        header.setObjectName("page-header")
        header.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #2a82da;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        self.session_summary = SessionSummaryCard()
        content_layout.addWidget(self.session_summary)
        
        analysis_plan_layout = QHBoxLayout()
        analysis_plan_layout.setSpacing(15)
        
        self.performance_analysis = PerformanceAnalysisWidget()
        analysis_plan_layout.addWidget(self.performance_analysis)
        
        self.next_session_plan = NextSessionPlanWidget()
        analysis_plan_layout.addWidget(self.next_session_plan)
        
        content_layout.addLayout(analysis_plan_layout)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        self.load_initial_data()
    
    def lazy_init(self):
        logger.info("🏁 Lazy initializing Race Coach Overview page...")
        if self.iracing_monitor:
            self.load_session_data()
    
    def load_initial_data(self):
        self.session_summary.track_car_label.setText("Connect to iRacing to view session data")
        self.performance_analysis.analysis_text.setHtml("""
            <h3>📊 Performance Analysis</h3>
            <p>Connect to iRacing and complete a session to see detailed analysis including:</p>
            <ul>
                <li>Sector time comparison</li>
                <li>Speed analysis through corners</li>
                <li>Consistency metrics</li>
                <li>Areas for improvement</li>
            </ul>
        """)
        
        self.next_session_plan.plan_text.setHtml("""
            <h3>🎯 Next Session Recommendations</h3>
            <p>After completing a session, your AI racing engineer will provide:</p>
            <ul>
                <li>Specific corners to focus on</li>
                <li>Recommended practice drills</li>
                <li>Setup suggestions</li>
                <li>Personalized coaching tips</li>
            </ul>
        """)
    
    def load_session_data(self):
        if not self.iracing_monitor:
            return
            
        try:
            logger.info("Loading session data for overview...")
        except Exception as e:
            logger.error(f"Error loading session data: {e}")
    
    def update_telemetry_data(self, data):
        pass
    
    def on_page_activated(self):
        super().on_page_activated()
        if self.iracing_monitor:
            self.load_session_data()