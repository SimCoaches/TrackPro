"""TrackPro Race Coach - AI-powered racing coach and performance analyzer"""

import logging
from PyQt6.QtWidgets import QApplication

# Set higher logging level for noisy HTTP and Supabase libraries
for library in ['urllib3', 'httpcore', 'httpx', 'hpack', 'gotrue', 'postgrest']:
    logging.getLogger(library).setLevel(logging.WARNING)

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

__version__ = "0.1.0"

# Import main components
try:
    from .ui import RaceCoachWidget
    from .iracing_api import IRacingAPI
    from .simple_iracing import SimpleIRacingAPI  # Import our new simple implementation
    from .data_manager import DataManager
    from .model import RacingModel
    from .analysis import LapAnalysis
    # from .superlap import SuperLap  # DISABLED: Module doesn't exist
    from .telemetry_saver import TelemetrySaver  # Import the new telemetry saver
    from .iracing_lap_saver import IRacingLapSaver  # Import the Supabase lap saver
    from .lazy_loader import lazy_loader  # Import Phase 3 lazy loading system
    
    # Apply patch to ensure compatibility functions are defined
    try:
        # Only apply patch if absolutely necessary - check more carefully
        if not hasattr(RaceCoachWidget, 'on_iracing_connected') or not callable(getattr(RaceCoachWidget, 'on_iracing_connected', None)):
            # Only patch if the method doesn't exist or isn't callable
            logger.warning("Adding compatibility methods to RaceCoachWidget")
            
            # Add missing methods for compatibility
            def on_iracing_connected(self, is_connected, session_info):
                """Handle connection status changes from iRacing API."""
                logger.info(f"iRacing connection status changed: {is_connected}")
                try:
                    if hasattr(self, '_update_connection_status'):
                        self._update_connection_status(is_connected)
                except Exception as e:
                    logger.error(f"Error in patched on_iracing_connected: {e}")
            
            def on_session_info_changed(self, session_info):
                """Handle session info changes from iRacing API."""
                logger.info("Session info changed")
                try:
                    if hasattr(self, '_update_session_info'):
                        self._update_session_info(session_info)
                except Exception as e:
                    logger.error(f"Error in patched on_session_info_changed: {e}")
            
            def on_telemetry_data(self, telemetry_data):
                """Handle telemetry data updates from iRacing API."""
                try:
                    if hasattr(self, '_update_telemetry'):
                        self._update_telemetry(telemetry_data)
                except Exception as e:
                    logger.error(f"Error in patched on_telemetry_data: {e}")
            
            # Add these methods to the class
            RaceCoachWidget.on_iracing_connected = on_iracing_connected
            RaceCoachWidget.on_session_info_changed = on_session_info_changed
            RaceCoachWidget.on_telemetry_data = on_telemetry_data
            
            logger.info("Compatibility methods added to RaceCoachWidget")
        else:
            logger.info("Compatibility methods already exist in RaceCoachWidget - no patching needed")
    except Exception as e:
        logger.error(f"Error patching RaceCoachWidget: {e}")

    def create_race_coach_widget(parent=None):
        """Factory function to create a RaceCoachWidget with LAZY initialization.
        
        This creates a minimal widget that initializes components only when needed.
        
        Args:
            parent: The parent widget, typically a QWidget.
            
        Returns:
            A RaceCoachWidget with lazy initialization or None if creation failed.
        """
        try:
            # Check if Qt application is available before creating widget
            if QApplication.instance() is None:
                logger.error("Cannot create Race Coach widget: No QApplication instance found")
                return None
                
            logger.info("Creating RaceCoachWidget with LAZY initialization")
            
            # Create the widget with NO heavy components - just the UI shell
            widget = RaceCoachWidget(parent=parent, iracing_api=None)
            
            # Mark it as needing lazy initialization
            widget._needs_lazy_init = True
            widget._lazy_init_completed = False
            
            logger.info("RaceCoachWidget created with lazy initialization pending")
            return widget
            
        except Exception as e:
            logger.error(f"Error creating Race Coach widget: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
except ImportError as e:
    logger.error(f"Error importing Race Coach modules: {e}")
    
    # Create a stub function that logs the error
    def create_race_coach_widget(parent=None):
        logger.error("Cannot create Race Coach widget - modules not properly imported")
        return None
    
__all__ = ['RaceCoachWidget', 'IRacingAPI', 'SimpleIRacingAPI', 'DataManager', 'RacingModel', 
           'LapAnalysis', 'TelemetrySaver', 'IRacingLapSaver', 'create_race_coach_widget'] 