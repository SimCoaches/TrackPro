import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class RacePassPage(BasePage):
    """
    Complete Race Pass page that integrates all Race Pass functionality
    including battle pass progression, premium purchases, quests, and TrackCoins store.
    """
    
    # Signals for communication with parent window
    premium_pass_purchased = pyqtSignal()
    trackcoins_updated = pyqtSignal(int)
    
    def __init__(self, global_managers=None):
        self.race_pass_widget = None
        self._is_authenticated = False
        super().__init__("Race Pass", global_managers)
        
    def init_page(self):
        """Initialize the Race Pass page layout and components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Initialize the main Race Pass widget
        self.init_race_pass_widget(layout)
        

    def init_race_pass_widget(self, layout):
        """Initialize the main Race Pass widget with all functionality."""
        try:
            # Import the existing Race Pass widget
            from trackpro.gamification.ui.race_pass_view import RacePassViewWidget
            
            # Create the race pass widget
            self.race_pass_widget = RacePassViewWidget(self)
            
            # Connect signals if the widget has them
            if hasattr(self.race_pass_widget, 'premium_pass_purchased'):
                self.race_pass_widget.premium_pass_purchased.connect(self.on_premium_pass_purchased)
            
            if hasattr(self.race_pass_widget, 'trackcoins_updated'):
                self.race_pass_widget.trackcoins_updated.connect(self.on_trackcoins_updated)
            
            # Add the widget to layout
            layout.addWidget(self.race_pass_widget)
            
            logger.info("✅ Race Pass widget initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import Race Pass widget: {e}")
            self.create_fallback_ui(layout)
        except Exception as e:
            logger.error(f"Error initializing Race Pass widget: {e}")
            self.create_fallback_ui(layout)
    
    def create_fallback_ui(self, layout):
        """Create a fallback UI when the main Race Pass widget fails to load."""
        fallback_frame = QFrame()
        fallback_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                padding: 30px;
            }
        """)
        fallback_layout = QVBoxLayout(fallback_frame)
        
        error_label = QLabel("⚠️ Race Pass Temporarily Unavailable")
        error_label.setStyleSheet("""
            color: #e74c3c;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 15px;
        """)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fallback_layout.addWidget(error_label)
        
        info_label = QLabel(
            "The Race Pass system is currently unavailable.\n\n"
            "This could be due to:\n"
            "• Network connectivity issues\n"
            "• Authentication requirements\n"
            "• System maintenance\n\n"
            "Please try again later or check the logs for more details."
        )
        info_label.setStyleSheet("""
            color: #ccc;
            font-size: 14px;
            text-align: center;
            line-height: 1.5;
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fallback_layout.addWidget(info_label)
        
        layout.addWidget(fallback_frame)
        
    def on_page_activated(self):
        """Called when the page becomes active."""
        super().on_page_activated()
        
        # Refresh Race Pass data when page is activated
        if self.race_pass_widget and hasattr(self.race_pass_widget, 'load_race_pass_data'):
            try:
                self.race_pass_widget.load_race_pass_data()
            except Exception as e:
                logger.warning(f"Failed to refresh Race Pass data: {e}")
    
    def lazy_init(self):
        """Perform lazy initialization when page is first activated."""
        logger.info("🎟️ Race Pass page lazy initialization")
        
        # Check authentication status
        self.check_authentication()
        
        # Load initial data if not already loaded
        if self.race_pass_widget:
            try:
                if hasattr(self.race_pass_widget, 'load_race_pass_data'):
                    self.race_pass_widget.load_race_pass_data()
            except Exception as e:
                logger.warning(f"Failed to load Race Pass data during lazy init: {e}")
    
    def check_authentication(self):
        """Check if user is authenticated for Race Pass features."""
        try:
            # Check if auth handler is available
            if self.auth_handler:
                self._is_authenticated = self.auth_handler.is_authenticated()
            else:
                # Try to check authentication via supabase directly
                from trackpro.database import supabase
                self._is_authenticated = supabase.is_authenticated()
            
            logger.info(f"Race Pass authentication status: {self._is_authenticated}")
            
        except Exception as e:
            logger.warning(f"Could not check authentication: {e}")
            # Default to allowing access (offline mode)
            self._is_authenticated = True
    
    def on_premium_pass_purchased(self):
        """Handle premium pass purchase event."""
        logger.info("🎉 Premium Race Pass purchased!")
        self.premium_pass_purchased.emit()
        
        # Show success message
        QMessageBox.information(
            self,
            "Premium Pass Activated",
            "🎉 Your Premium Race Pass has been activated!\n\n"
            "You now have access to:\n"
            "• Exclusive premium rewards\n"
            "• Double XP progression\n" 
            "• Premium cosmetics\n"
            "• Special milestone bonuses\n\n"
            "Enjoy your enhanced Race Pass experience!"
        )
    
    def on_trackcoins_updated(self, new_balance):
        """Handle TrackCoins balance update."""
        logger.info(f"💰 TrackCoins updated: {new_balance}")
        self.trackcoins_updated.emit(new_balance)
    
    def get_race_pass_progress(self):
        """Get current race pass progression data."""
        if self.race_pass_widget:
            try:
                # Try to get progress from the widget
                if hasattr(self.race_pass_widget, 'overview_widget'):
                    # Return basic progress info
                    return {
                        'current_tier': 5,  # Default values
                        'max_tier': 50,
                        'premium_active': getattr(self.race_pass_widget, 'premium_active', False)
                    }
            except Exception as e:
                logger.warning(f"Failed to get race pass progress: {e}")
        
        return None
    
    def refresh_data(self):
        """Refresh all Race Pass data."""
        if self.race_pass_widget and hasattr(self.race_pass_widget, 'load_race_pass_data'):
            try:
                self.race_pass_widget.load_race_pass_data()
                logger.info("🔄 Race Pass data refreshed")
            except Exception as e:
                logger.error(f"Failed to refresh Race Pass data: {e}")
    
    def cleanup(self):
        """Clean up resources when page is destroyed."""
        logger.info("🧹 Race Pass page cleanup")
        
        # Clean up the race pass widget if it exists
        if self.race_pass_widget:
            try:
                if hasattr(self.race_pass_widget, 'cleanup'):
                    self.race_pass_widget.cleanup()
            except Exception as e:
                logger.warning(f"Error during Race Pass widget cleanup: {e}")
        
        super().cleanup()