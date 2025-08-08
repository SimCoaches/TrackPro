import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage
from .coming_soon_page import RaceCoachComingSoonPage

logger = logging.getLogger(__name__)

class CoachPage(BasePage):
    def __init__(self, global_managers=None):
        super().__init__("Race Coach", global_managers)
        
    def init_page(self):
        """Initialize the Race Coach Coming Soon page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Use the coming soon page
        self.coming_soon_page = RaceCoachComingSoonPage(self.global_managers)
        layout.addWidget(self.coming_soon_page)
        
        logger.info("✅ Race Coach Coming Soon page initialized")
    
    def lazy_init(self):
        logger.info("🏁 Lazy initializing Race Coach Coming Soon page...")
        if hasattr(self, 'coming_soon_page') and hasattr(self.coming_soon_page, 'lazy_init'):
            self.coming_soon_page.lazy_init()
    
    def on_page_activated(self):
        super().on_page_activated()
        if hasattr(self, 'coming_soon_page') and hasattr(self.coming_soon_page, 'on_page_activated'):
            self.coming_soon_page.on_page_activated()
    
    def cleanup(self):
        """Clean up resources when page is destroyed."""
        if hasattr(self, 'coming_soon_page') and hasattr(self.coming_soon_page, 'cleanup'):
            self.coming_soon_page.cleanup()
        super().cleanup()
    
    def update_telemetry_data(self, data):
        """Update telemetry data (no-op for coming soon)."""
        logger.info("🔄 Race Coach Coming Soon - telemetry updates not available yet")