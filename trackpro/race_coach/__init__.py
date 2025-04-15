"""TrackPro Race Coach - AI-powered racing coach and performance analyzer"""

import logging

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
    from .superlap import SuperLap
    from .telemetry_saver import TelemetrySaver  # Import the new telemetry saver
    from .iracing_lap_saver import IRacingLapSaver  # Import the Supabase lap saver
    
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
                
            # Create TelemetrySaver for local saving
            try:
                from .telemetry_saver import TelemetrySaver
                telemetry_saver = TelemetrySaver(data_manager=data_manager)
                logger.info("TelemetrySaver initialized successfully")
            except Exception as telemetry_error:
                logger.error(f"Error initializing TelemetrySaver: {telemetry_error}")
                telemetry_saver = None
                
            # Create a Supabase client for lap saving
            try:
                from ..database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                if supabase_client:
                    logger.info("Created Supabase client for lap saving")
                else:
                    logger.warning("Failed to create Supabase client")
                    
                from .iracing_lap_saver import IRacingLapSaver
                iracing_lap_saver = IRacingLapSaver()
                logger.info("IRacingLapSaver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize IRacingLapSaver: {e}")
                iracing_lap_saver = None
            
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
                
                # Connect the telemetry saver to the API
                if telemetry_saver is not None:
                    try:
                        iracing_api.set_telemetry_saver(telemetry_saver)
                        logger.info("Connected telemetry saver to SimpleIRacingAPI")
                    except Exception as ts_error:
                        logger.error(f"Error connecting telemetry saver to SimpleIRacingAPI: {ts_error}")
                
                # Connect the Supabase lap saver to the API
                if iracing_lap_saver is not None:
                    # Explicitly set user ID if available from the application context
                    try:
                        from ..auth.user_manager import get_current_user
                        user = get_current_user()
                        if user and hasattr(user, 'id') and user.is_authenticated:
                            user_id = user.id
                            iracing_lap_saver.set_user_id(user_id)
                            logger.info(f"Set user ID for lap saver: {user_id}")
                            
                            # Also set user ID in session info so it can be accessed later
                            if hasattr(iracing_api, '_session_info'):
                                iracing_api._session_info['user_id'] = user_id
                                logger.debug(f"Added user_id to session_info: {user_id}")
                        else:
                            logger.warning("No authenticated user available from auth module")
                    except Exception as user_error:
                        logger.error(f"Error getting current user for lap saver: {user_error}")
                        import traceback
                        logger.error(traceback.format_exc())
                    
                    try:
                        # IMPORTANT FIX: Always use the set_lap_saver method if available 
                        if hasattr(iracing_api, 'set_lap_saver'):
                            result = iracing_api.set_lap_saver(iracing_lap_saver)
                            if result:
                                logger.info("Successfully connected Supabase lap saver to SimpleIRacingAPI")
                            else:
                                logger.error("Failed to connect lap saver to SimpleIRacingAPI")
                        else:
                            # Legacy callback approach as fallback
                            def process_telemetry_with_supabase(telemetry_data):
                                try:
                                    result = iracing_lap_saver.process_telemetry(telemetry_data)
                                    if result:
                                        is_new_lap, lap_number, lap_time = result
                                        logger.info(f"New lap detected by Supabase saver: Lap {lap_number}, Time: {lap_time:.3f}s")
                                except Exception as e:
                                    logger.error(f"Error processing telemetry with Supabase: {e}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                            
                            # Add the callback to the API if it supports it
                            if hasattr(iracing_api, 'add_telemetry_callback'):
                                iracing_api.add_telemetry_callback(process_telemetry_with_supabase)
                                logger.info("Added Supabase telemetry processing callback to SimpleIRacingAPI")
                            else:
                                logger.warning("SimpleIRacingAPI does not support telemetry callbacks, Supabase integration limited")
                    except Exception as ls_error:
                        logger.error(f"Error connecting Supabase lap saver to SimpleIRacingAPI: {ls_error}")
                        import traceback
                        logger.error(traceback.format_exc())
                
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
                    
                    # Connect the Supabase lap saver to the original IRacingAPI as well
                    if iracing_lap_saver is not None:
                        try:
                            # Similar approach as with SimpleIRacingAPI
                            # Explicitly set user ID if available from the application context
                            try:
                                from ..auth.user_manager import get_current_user
                                user = get_current_user()
                                if user and hasattr(user, 'id') and user.is_authenticated:
                                    iracing_lap_saver.set_user_id(user.id)
                                    logger.info(f"Set user ID for lap saver with fallback IRacingAPI: {user.id}")
                                else:
                                    logger.warning("No authenticated user available from auth module for fallback IRacingAPI")
                            except Exception as user_error:
                                logger.error(f"Error getting current user for lap saver with fallback IRacingAPI: {user_error}")
                                
                            if hasattr(iracing_api, 'set_lap_saver'):
                                iracing_api.set_lap_saver(iracing_lap_saver)
                            elif hasattr(iracing_api, 'add_telemetry_callback'):
                                def process_telemetry_with_supabase(telemetry_data):
                                    try:
                                        result = iracing_lap_saver.process_telemetry(telemetry_data)
                                        if result:
                                            is_new_lap, lap_number, lap_time = result
                                            logger.info(f"New lap detected by Supabase saver (fallback): Lap {lap_number}, Time: {lap_time:.3f}s")
                                    except Exception as e:
                                        logger.error(f"Error processing telemetry with Supabase: {e}")
                                        
                                iracing_api.add_telemetry_callback(process_telemetry_with_supabase)
                                logger.info("Added Supabase telemetry processing callback to IRacingAPI")
                        except Exception as ls_error:
                            logger.error(f"Error connecting Supabase lap saver to IRacingAPI: {ls_error}")
                            
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
            
            # Store references to important components in the widget for access
            widget.data_manager = data_manager
            widget.telemetry_saver = telemetry_saver
            widget.iracing_lap_saver = iracing_lap_saver
            
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
           'LapAnalysis', 'SuperLap', 'TelemetrySaver', 'IRacingLapSaver', 'create_race_coach_widget'] 