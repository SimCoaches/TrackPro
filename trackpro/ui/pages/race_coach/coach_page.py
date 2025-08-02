import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage
from .overview_page import OverviewPage
from .telemetry_page import TelemetryPage
from .superlap_page import SuperLapPage
from .videos_page import VideosPage

logger = logging.getLogger(__name__)

class CoachPage(BasePage):
    def __init__(self, global_managers=None):
        self.sub_pages = {}
        super().__init__("Race Coach", global_managers)
        
    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1a1a1a;
                border-radius: 6px;
                margin-top: 5px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #CCC;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
                border-bottom: 2px solid #2a82da;
            }
        """)
        
        self.create_coach_tabs()
        
        layout.addWidget(self.tab_widget)
        
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def create_coach_tabs(self):
        self.overview_page = OverviewPage(self.global_managers)
        self.tab_widget.addTab(self.overview_page, "🏁 Overview")
        self.sub_pages["overview"] = self.overview_page
        
        self.telemetry_page = TelemetryPage(self.global_managers)
        self.tab_widget.addTab(self.telemetry_page, "📊 Telemetry")
        self.sub_pages["telemetry"] = self.telemetry_page
        
        self.superlap_page = SuperLapPage(self.global_managers)
        self.tab_widget.addTab(self.superlap_page, "⚡ SuperLap")
        self.sub_pages["superlap"] = self.superlap_page
        
        self.videos_page = VideosPage(self.global_managers)
        self.tab_widget.addTab(self.videos_page, "🎬 RaceFlix")
        self.sub_pages["videos"] = self.videos_page
        
        logger.info("✅ Race Coach tabs created with modular pages")
    
    def lazy_init(self):
        logger.info("🏁 Lazy initializing Race Coach main page...")
        current_page = self.get_current_sub_page()
        if current_page and hasattr(current_page, 'lazy_init'):
            current_page.lazy_init()
    
    def on_tab_changed(self, index):
        current_page = self.tab_widget.widget(index)
        if current_page and hasattr(current_page, 'on_page_activated'):
            QTimer.singleShot(50, current_page.on_page_activated)
        
        tab_names = ["Overview", "Telemetry", "SuperLap", "RaceFlix"]
        if 0 <= index < len(tab_names):
            logger.info(f"🔄 Race Coach tab changed to: {tab_names[index]}")
    
    def get_current_sub_page(self):
        current_index = self.tab_widget.currentIndex()
        return self.tab_widget.widget(current_index)
    
    def on_page_activated(self):
        super().on_page_activated()
        current_page = self.get_current_sub_page()
        if current_page and hasattr(current_page, 'on_page_activated'):
            current_page.on_page_activated()
    
    def cleanup(self):
        for page in self.sub_pages.values():
            if hasattr(page, 'cleanup'):
                page.cleanup()
    
    def update_telemetry_data(self, data):
        if hasattr(self.telemetry_page, 'update_telemetry_data'):
            self.telemetry_page.update_telemetry_data(data)
        if hasattr(self.overview_page, 'update_telemetry_data'):
            self.overview_page.update_telemetry_data(data)