import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from ...modern.shared.base_page import BasePage
from ...shared_imports import RacePassViewWidget, GAMIFICATION_AVAILABLE

logger = logging.getLogger(__name__)

class RacePassPage(BasePage):
    """
    Race Pass page
    """
    
    # Signals for communication with parent window
    premium_pass_purchased = pyqtSignal()
    trackcoins_updated = pyqtSignal(int)
    
    def __init__(self, global_managers=None):
        super().__init__("Race Pass", global_managers)
        
    def init_page(self):
        """Initialize the Race Pass page layout with real view when available."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if GAMIFICATION_AVAILABLE and RacePassViewWidget is not None:
            try:
                self.view = RacePassViewWidget()
                layout.addWidget(self.view)
                logger.info("🎟️ Race Pass view loaded")
                return
            except Exception as e:
                logger.warning(f"Race Pass view failed to load, using placeholder: {e}")

        # Fallback placeholder
        fallback_layout = QVBoxLayout()
        fallback_layout.setContentsMargins(40, 40, 40, 40)
        fallback_layout.setSpacing(30)
        self.create_coming_soon_content(fallback_layout)
        layout.addLayout(fallback_layout)
        
    def create_coming_soon_content(self, layout):
        """Create the coming soon UI content."""
        # Main container frame
        main_frame = QFrame()
        main_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #333;
                border-radius: 12px;
                padding: 40px;
            }
        """)
        main_layout = QVBoxLayout(main_frame)
        main_layout.setSpacing(25)
        
        # Title
        title_label = QLabel("Race Pass")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 36px;
            font-weight: bold;
            text-align: center;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Coming Soon badge
        coming_soon_label = QLabel("COMING SOON")
        coming_soon_label.setStyleSheet("""
            color: #00d4ff;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            background-color: rgba(0, 212, 255, 0.1);
            border: 2px solid #00d4ff;
            border-radius: 20px;
            padding: 8px 20px;
        """)
        coming_soon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(coming_soon_label)
        
        # Description
        desc_label = QLabel(
            "We're working hard to bring you an amazing Race Pass experience!\n\n"
            "Get ready for:\n"
            "• Battle Pass progression with exclusive rewards\n"
            "• Premium pass with enhanced benefits\n"
            "• TrackCoins store with unique cosmetics\n"
            "• Daily and weekly challenges\n"
            "• Milestone rewards and achievements"
        )
        desc_label.setStyleSheet("""
            color: #cccccc;
            font-size: 16px;
            text-align: center;
            line-height: 1.6;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Progress indicator
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 20px;
            }
        """)
        progress_layout = QVBoxLayout(progress_frame)
        
        progress_title = QLabel("Development Progress")
        progress_title.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
        """)
        progress_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(progress_title)
        
        # Progress bar simulation
        progress_bar_frame = QFrame()
        progress_bar_frame.setStyleSheet("""
            QFrame {
                background-color: #333;
                border-radius: 10px;
                padding: 3px;
            }
        """)
        progress_bar_layout = QHBoxLayout(progress_bar_frame)
        progress_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress fill (simulated)
        progress_fill = QFrame()
        progress_fill.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00d4ff, stop:1 #0099cc);
                border-radius: 7px;
            }
        """)
        progress_fill.setFixedWidth(100)
        progress_bar_layout.addWidget(progress_fill)
        progress_bar_layout.addStretch()
        
        progress_layout.addWidget(progress_bar_frame)
        
        # Progress text
        progress_text = QLabel("30% Complete")
        progress_text.setStyleSheet("""
            color: #00d4ff;
            font-size: 14px;
            font-weight: bold;
            text-align: center;
            margin-top: 5px;
        """)
        progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(progress_text)
        
        main_layout.addWidget(progress_frame)
        
        # Add some spacing
        main_layout.addStretch()
        
        # Add the main frame to the layout
        layout.addWidget(main_frame)
        
    def on_page_activated(self):
        """Called when the page becomes active."""
        super().on_page_activated()
        logger.info("🎟️ Race Pass Coming Soon page activated")
    
    def lazy_init(self):
        """Perform lazy initialization when page is first activated."""
        logger.info("🎟️ Race Pass Coming Soon page lazy initialization")
    
    def get_race_pass_progress(self):
        """Get current race pass progression data (coming soon)."""
        return {
            'current_tier': 0,
            'max_tier': 50,
            'premium_active': False,
            'status': 'coming_soon'
        }
    
    def refresh_data(self):
        """Refresh data (no-op for coming soon)."""
        logger.info("🔄 Race Pass Coming Soon - no data to refresh")
    
    def cleanup(self):
        """Clean up resources when page is destroyed."""
        logger.info("🧹 Race Pass Coming Soon page cleanup")
        super().cleanup()