"""TrackPro Race Coach - AI-powered racing coach and performance analyzer"""

import logging

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
    from .superlap import SuperLap
    from .telemetry_saver import TelemetrySaver  # Import the new telemetry saver
    
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
        """Factory function to create a RaceCoachWidget with error handling.
        
        This factory function abstracts away the complexity of creating all the 
        necessary components for the Race Coach feature, handling errors gracefully.
        
        Args:
            parent: The parent widget, typically a QWidget.
            
        Returns:
            A fully initialized RaceCoachWidget or None if initialization failed.
        """
        try:
            # Create data manager
            # If a database path is needed, add it as parameter here later
            try:
                from .data_manager import DataManager
                data_manager = DataManager()
                logger.info("DataManager initialized successfully")
            except Exception as data_error:
                logger.error(f"Error initializing DataManager: {data_error}")
                data_manager = None

            # Create model components if needed
            try:
                from .model import RacingModel
                model = RacingModel()
                logger.info("RacingModel initialized successfully")
            except Exception as model_error:
                logger.error(f"Error initializing RacingModel: {model_error}")
                model = None
            
            # Create analysis
            try:
                from .analysis import LapAnalysis
                lap_analysis = LapAnalysis()
                logger.info("LapAnalysis initialized successfully")
            except Exception as analysis_error:
                logger.error(f"Error initializing LapAnalysis: {analysis_error}")
                lap_analysis = None
            
            # Create SuperLap
            try:
                from .superlap import SuperLap
                super_lap = SuperLap()
                logger.info("SuperLap initialized successfully")
            except Exception as superlap_error:
                logger.error(f"Error initializing SuperLap: {superlap_error}")
                super_lap = None
            
            # Create IRacingAPI
            iracing_api = None  # Initialize to None for safety
            try:
                logger.info("Attempting to initialize SimpleIRacingAPI...")
                iracing_api = SimpleIRacingAPI()  # Try the simpler implementation first
                logger.info("SimpleIRacingAPI initialized successfully")
                
                # Connect the data manager to the API for telemetry saving
                if data_manager is not None:
                    try:
                        iracing_api.set_data_manager(data_manager)
                        logger.info("Connected data manager to SimpleIRacingAPI for telemetry saving")
                    except Exception as connect_error:
                        logger.error(f"Error connecting data manager to SimpleIRacingAPI: {connect_error}")
                
            except Exception as simple_api_error:
                logger.error(f"Error initializing SimpleIRacingAPI: {simple_api_error}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Fall back to original IRacingAPI if SimpleIRacingAPI fails
                try:
                    logger.info("Falling back to IRacingAPI...")
                    from .iracing_api import IRacingAPI
                    iracing_api = IRacingAPI()
                    logger.info("IRacingAPI initialized successfully")
                except Exception as api_error:
                    logger.error(f"Error initializing IRacingAPI: {api_error}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # If both implementations fail, there's likely a deeper issue
                    raise RuntimeError("Failed to create any iRacing API connection")
            
            # Verify we have an API instance before creating the widget
            if iracing_api is None:
                logger.critical("Failed to create any IRacingAPI implementation")
                return None
                
            logger.info(f"Creating RaceCoachWidget with API: {type(iracing_api).__name__}")
            
            # Create the widget with the API instance
            widget = RaceCoachWidget(parent=parent, iracing_api=iracing_api)
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
           'LapAnalysis', 'SuperLap', 'TelemetrySaver', 'create_race_coach_widget'] 