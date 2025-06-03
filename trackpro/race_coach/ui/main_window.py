"""Main window for Race Coach - combines all tabs into the main interface.

This module contains the main RaceCoachWidget that integrates all the separate
tab modules into a cohesive interface.
"""

import logging
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QFrame, QSizePolicy, QMessageBox, QDialog,
    QTextEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer

# Import the individual tab modules
from .overview_tab import OverviewTab
from .telemetry_tab import TelemetryTab
from .superlap_tab import SuperLapWidget
from .videos_tab import VideosTab

logger = logging.getLogger(__name__)


class RaceCoachWidget(QWidget):
    """Main container widget for Race Coach functionality.

    This widget integrates iRacing telemetry data with AI-powered analysis and visualization.
    """

    def __init__(self, parent=None, iracing_api=None):
        super().__init__(parent)
        self.setObjectName("RaceCoachWidget")
        
        logger.info("🔍 RaceCoachWidget.__init__() called")
        logger.info(f"🔍 iracing_api parameter: {iracing_api}")

        # Lazy initialization flags
        self._lazy_init_completed = False
        self._lazy_init_in_progress = False

        # Store reference to the iRacing API
        self.iracing_api = iracing_api
        logger.info(f"🔍 Set self.iracing_api to: {self.iracing_api}")

        # Track connection state
        self.is_connected = False
        self.session_info = {}

        # Attributes for background telemetry fetching
        self.telemetry_fetch_thread = None
        self.telemetry_fetch_worker = None

        # Attributes for background initial data loading
        self.initial_load_thread = None
        self.initial_load_worker = None
        self._is_initial_loading = False

        # Flag to track if initial lap list load has happened
        self._initial_lap_load_done = False

        # Flags to prevent duplicate operations
        self._initial_load_in_progress = False
        self._show_event_in_progress = False
        self._initialization_complete = False
        self._initial_connection_attempted = False

        # Initialize UI
        logger.info("🔍 Calling setup_ui()...")
        self.setup_ui()
        logger.info("✅ setup_ui() completed")

        # Mark basic initialization as complete
        self._initialization_complete = True
        logger.info("✅ Basic initialization complete")

        # Only connect to iRacing API if we have one (non-lazy mode)
        if self.iracing_api is not None:
            logger.info("🔍 Non-lazy mode: setting up iRacing API connections...")
            self._setup_iracing_api_connections()
        else:
            logger.info("🔍 RaceCoachWidget created in lazy initialization mode")
            # Start lazy initialization immediately
            logger.info("🔍 Starting lazy initialization work...")
            self._do_lazy_initialization_work()

    def showEvent(self, event):
        """Handle the widget being shown - start deferred monitoring if needed."""
        logger.info("🔍 RaceCoachWidget.showEvent() called - widget is being shown")
        super().showEvent(event)
        
        # Start deferred monitoring if we have an iRacing API and haven't started monitoring yet
        if (hasattr(self, 'iracing_api') and self.iracing_api and 
            hasattr(self.iracing_api, 'start_deferred_monitoring') and
            not hasattr(self, '_monitoring_started')):
            
            logger.info("🚀 Race Coach widget shown - starting deferred iRacing monitoring...")
            try:
                success = self.iracing_api.start_deferred_monitoring()
                if success:
                    logger.info("✅ Deferred iRacing monitoring started successfully")
                    self._monitoring_started = True
                else:
                    logger.warning("⚠️ Failed to start deferred iRacing monitoring")
            except Exception as e:
                logger.error(f"❌ Error starting deferred monitoring: {e}")

    def _setup_iracing_api_connections(self):
        """Set up connections to the iRacing API."""
        try:
            # Try SimpleIRacingAPI method names first
            if hasattr(self.iracing_api, "register_on_connection_changed"):
                logger.info("Using SimpleIRacingAPI callback methods")
                self.iracing_api.register_on_connection_changed(self.on_iracing_connected)
                self.iracing_api.register_on_telemetry_data(self.on_telemetry_data)

                # Connect the new signal
                if hasattr(self.iracing_api, "sessionInfoUpdated"):
                    logger.info("Connecting sessionInfoUpdated signal to UI update slot.")
                    self.iracing_api.sessionInfoUpdated.connect(self._update_connection_status)
                else:
                    logger.warning("iRacing API instance does not have sessionInfoUpdated signal.")

                logger.info("Deferring iRacing connection until Race Coach tab is shown")

            # Fall back to IRacingAPI method names
            elif hasattr(self.iracing_api, "register_connection_callback"):
                logger.warning("Legacy IRacingAPI callback registration attempted - this might not work as expected.")
            else:
                logger.warning("Unable to register callbacks with iRacing API - incompatible implementation")
        except Exception as e:
            logger.error(f"Error setting up callbacks for iRacing API: {e}")

    def _do_lazy_initialization_work(self):
        """Do the actual heavy initialization work in the background."""
        logger.info("🔍 Starting _do_lazy_initialization_work()")
        try:
            # Create data manager
            try:
                logger.info("🔍 Creating DataManager...")
                from ..data_manager import DataManager
                self.data_manager = DataManager()
                logger.info("✅ DataManager initialized successfully")
            except Exception as data_error:
                logger.error(f"❌ Error initializing DataManager: {data_error}")
                self.data_manager = None

            # Create TelemetrySaver for local saving
            try:
                logger.info("🔍 Creating TelemetrySaver...")
                from ..telemetry_saver import TelemetrySaver
                self.telemetry_saver = TelemetrySaver(data_manager=self.data_manager)
                logger.info("✅ TelemetrySaver initialized successfully")
            except Exception as telemetry_error:
                logger.error(f"❌ Error initializing TelemetrySaver: {telemetry_error}")
                self.telemetry_saver = None
                
            # Create a Supabase client for lap saving
            try:
                from ...database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                if supabase_client:
                    logger.info("Created Supabase client for lap saving")
                else:
                    logger.warning("Failed to create Supabase client")
                    
                from ..iracing_lap_saver import IRacingLapSaver
                self.iracing_lap_saver = IRacingLapSaver()
                if supabase_client:
                    self.iracing_lap_saver.set_supabase_client(supabase_client)
                    logger.info("Successfully passed Supabase client to IRacingLapSaver")
                else:
                    logger.warning("Could not pass Supabase client to IRacingLapSaver")
                logger.info("IRacingLapSaver initialized successfully")
                
                logger.info("🎯 IMMEDIATE SAVING AUTOMATICALLY ACTIVATED - Zero lag lap saving enabled!")
            except Exception as e:
                logger.error(f"Failed to initialize IRacingLapSaver: {e}")
                self.iracing_lap_saver = None
            
            # Create IRacingAPI
            try:
                logger.info("🔍 Attempting to initialize SimpleIRacingAPI...")
                from ..simple_iracing import SimpleIRacingAPI
                self.iracing_api = SimpleIRacingAPI()
                
                logger.info("✅ SimpleIRacingAPI initialized successfully")
                logger.info(f"🔍 SimpleIRacingAPI object: {self.iracing_api}")
                
                # Connect the data manager to the API for telemetry saving
                if self.data_manager is not None:
                    try:
                        self.iracing_api.set_data_manager(self.data_manager)
                        logger.info("Connected data manager to SimpleIRacingAPI for telemetry saving")
                    except Exception as connect_error:
                        logger.error(f"Error connecting data manager to SimpleIRacingAPI: {connect_error}")
                
                # Connect the telemetry saver to the API
                if self.telemetry_saver is not None:
                    try:
                        self.iracing_api.set_telemetry_saver(self.telemetry_saver)
                        logger.info("Connected telemetry saver to SimpleIRacingAPI")
                    except Exception as ts_error:
                        logger.error(f"Error connecting telemetry saver to SimpleIRacingAPI: {ts_error}")
                
                # Connect the Supabase lap saver to the API
                if self.iracing_lap_saver is not None:
                    try:
                        from ...auth.user_manager import get_current_user
                        user = get_current_user()
                        if user and hasattr(user, 'id') and user.is_authenticated:
                            user_id = user.id
                            self.iracing_lap_saver.set_user_id(user_id)
                            logger.info(f"Set user ID for lap saver: {user_id}")

                            # Store the parameters needed to start monitoring later
                            self.iracing_api._deferred_monitor_params = {
                                'supabase_client': supabase_client,
                                'user_id': user_id,
                                'lap_saver': self.iracing_lap_saver
                            }
                            logger.info("✅ Deferred iRacing session monitor thread start until needed")

                            if hasattr(self.iracing_api, '_session_info'):
                                self.iracing_api._session_info['user_id'] = user_id
                                logger.debug(f"Added user_id to session_info: {user_id}")
                        else:
                            logger.warning("No authenticated user available from auth module")
                    except Exception as user_error:
                        logger.error(f"Error getting current user for lap saver: {user_error}")
                    
                    try:
                        if hasattr(self.iracing_api, 'set_lap_saver'):
                            result = self.iracing_api.set_lap_saver(self.iracing_lap_saver)
                            if result:
                                logger.info("Successfully connected Supabase lap saver to SimpleIRacingAPI")
                            else:
                                logger.error("Failed to connect lap saver to SimpleIRacingAPI")
                    except Exception as ls_error:
                        logger.error(f"Error connecting Supabase lap saver to SimpleIRacingAPI: {ls_error}")
                
                # Set up API connections
                self._setup_iracing_api_connections()
                
            except Exception as simple_api_error:
                logger.error(f"Error initializing SimpleIRacingAPI: {simple_api_error}")
                # Fall back to original IRacingAPI if SimpleIRacingAPI fails
                try:
                    logger.info("Falling back to IRacingAPI...")
                    from ..iracing_api import IRacingAPI
                    self.iracing_api = IRacingAPI()
                    logger.info("IRacingAPI initialized successfully")
                    self._setup_iracing_api_connections()
                except Exception as api_error:
                    logger.error(f"Error initializing IRacingAPI: {api_error}")
                    self.iracing_api = None
            
            # Mark lazy initialization as complete
            self._lazy_init_completed = True
            self._lazy_init_in_progress = False
            
            logger.info("Lazy initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during lazy initialization: {e}")
            self._lazy_init_in_progress = False

    def setup_ui(self):
        """Set up the race coach UI components."""
        main_layout = QVBoxLayout(self)

        # Status bar at the top
        self.status_bar = QWidget()
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(5, 5, 5, 5)

        self.connection_label = QLabel("iRacing: Disconnected")
        self.connection_label.setStyleSheet("""
            color: red;
            font-weight: bold;
        """)
        status_layout.addWidget(self.connection_label)

        self.driver_label = QLabel("No Driver")
        status_layout.addWidget(self.driver_label)

        self.track_label = QLabel("No Track")
        status_layout.addWidget(self.track_label)

        status_layout.addStretch()

        # Add diagnostic mode toggle button
        self.diagnostic_mode_button = QPushButton("🔍 Diagnostics: OFF")
        self.diagnostic_mode_button.setStyleSheet("""
            background-color: #333;
            color: #AAA;
            padding: 5px 10px;
            border-radius: 3px;
        """)
        self.diagnostic_mode_button.setToolTip("Toggle detailed lap detection diagnostics")
        self.diagnostic_mode_button.clicked.connect(self.toggle_diagnostic_mode)
        status_layout.addWidget(self.diagnostic_mode_button)

        # Add lap debug button
        self.lap_debug_button = QPushButton("🏁 Lap Debug")
        self.lap_debug_button.setStyleSheet("""
            background-color: #333;
            color: #AAA;
            padding: 5px 10px;
            border-radius: 3px;
        """)
        self.lap_debug_button.setToolTip("View lap recording status and save partial laps")
        self.lap_debug_button.clicked.connect(self.show_lap_debug_dialog)
        status_layout.addWidget(self.lap_debug_button)

        main_layout.addWidget(self.status_bar)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #222;
                border-radius: 3px;
            }
            QTabBar::tab {
                background-color: #333;
                color: #CCC;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #444;
                color: white;
            }
        """)

        # Create and add tabs
        self.overview_tab = OverviewTab(self)
        self.tab_widget.addTab(self.overview_tab, "Overview")

        self.telemetry_tab = TelemetryTab(self)
        self.tab_widget.addTab(self.telemetry_tab, "Telemetry")

        # Create the SuperLap Tab with lazy loading
        superlap_tab = QWidget()  # Placeholder widget initially
        superlap_layout = QVBoxLayout(superlap_tab)
        superlap_placeholder = QLabel("SuperLap analysis will load when you switch to this tab")
        superlap_placeholder.setAlignment(Qt.AlignCenter)
        superlap_placeholder.setStyleSheet("color: #666; font-style: italic; padding: 50px;")
        superlap_layout.addWidget(superlap_placeholder)
        
        # Store reference for lazy loading later
        self._superlap_tab_widget = superlap_tab
        self._superlap_widget = None  # Will be created when needed
        self.tab_widget.addTab(superlap_tab, "SuperLap")

        # Create the Videos Tab
        videos_tab = VideosTab(self)
        self.tab_widget.addTab(videos_tab, "RaceFlix")

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Connect tab change signal for lazy loading
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Save operation progress indicator
        self.save_progress_dialog = None

    def _on_tab_changed(self, index):
        """Handle tab changes to implement lazy loading for SuperLap tab."""
        try:
            # Check if this is the SuperLap tab (index 2, since we removed Sector Timing)
            if index == 2 and self._superlap_widget is None:
                logger.info("SuperLap tab accessed for first time - creating widget asynchronously")
                
                # Check network connectivity first
                try:
                    from ...database.supabase_client import supabase as main_supabase
                    if not main_supabase or not main_supabase.is_authenticated():
                        # Show offline message instead of trying to load
                        self._show_superlap_offline_message()
                        return
                except Exception as connectivity_error:
                    logger.warning(f"SuperLap: Network connectivity issue, showing offline mode: {connectivity_error}")
                    self._show_superlap_offline_message()
                    return
                
                # Create a loading placeholder first
                loading_widget = QWidget()
                loading_layout = QVBoxLayout(loading_widget)
                loading_label = QLabel("🔄 Loading SuperLap Analysis...")
                loading_label.setAlignment(Qt.AlignCenter)
                loading_label.setStyleSheet("color: #00ff88; font-size: 18px; font-weight: bold; padding: 50px;")
                loading_layout.addWidget(loading_label)
                
                # Replace placeholder with loading widget immediately
                while self._superlap_tab_widget.layout().count():
                    child = self._superlap_tab_widget.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                self._superlap_tab_widget.layout().addWidget(loading_widget)
                
                # Use QTimer to defer the actual widget creation to avoid blocking
                QTimer.singleShot(100, self._create_superlap_widget_deferred)
                
        except Exception as e:
            logger.error(f"Error in _on_tab_changed: {e}")

    def _show_superlap_offline_message(self):
        """Show offline message for SuperLap tab."""
        try:
            offline_widget = QWidget()
            offline_layout = QVBoxLayout(offline_widget)
            offline_layout.setAlignment(Qt.AlignCenter)
            
            # Icon
            icon_label = QLabel("🌐")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 48px; margin-bottom: 20px;")
            offline_layout.addWidget(icon_label)
            
            # Title
            title_label = QLabel("SuperLap Analysis - Offline Mode")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("color: #ffaa00; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
            offline_layout.addWidget(title_label)
            
            # Message
            message_label = QLabel("SuperLap analysis requires an internet connection to access AI-powered lap optimization data.\n\nPlease check your connection and try again.")
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setStyleSheet("color: #cccccc; font-size: 14px; line-height: 1.5; padding: 20px;")
            message_label.setWordWrap(True)
            offline_layout.addWidget(message_label)
            
            # Retry button
            retry_button = QPushButton("Retry Connection")
            retry_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            retry_button.clicked.connect(self._retry_superlap_connection)
            offline_layout.addWidget(retry_button, 0, Qt.AlignCenter)
            
            # Replace placeholder with offline widget
            while self._superlap_tab_widget.layout().count():
                child = self._superlap_tab_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            self._superlap_tab_widget.layout().addWidget(offline_widget)
            
        except Exception as e:
            logger.error(f"Error showing SuperLap offline message: {e}")

    def _retry_superlap_connection(self):
        """Retry SuperLap connection."""
        try:
            # Reset the widget state
            self._superlap_widget = None
            
            # Trigger tab change again to retry loading
            self._on_tab_changed(2)  # SuperLap tab index
            
        except Exception as e:
            logger.error(f"Error retrying SuperLap connection: {e}")

    def _create_superlap_widget_deferred(self):
        """Create the SuperLap widget in a deferred manner to avoid blocking the UI."""
        try:
            logger.info("Creating SuperLap widget in deferred execution")
            
            # Create the actual SuperLap widget
            self._superlap_widget = SuperLapWidget(self)
            
            # Replace the loading widget with the real widget
            while self._superlap_tab_widget.layout().count():
                child = self._superlap_tab_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Add the real SuperLap widget
            self._superlap_tab_widget.layout().addWidget(self._superlap_widget)
            
            logger.info("SuperLap widget created and added to tab successfully")
            
        except Exception as e:
            logger.error(f"Error creating SuperLap widget: {e}")
            
            # Show error message in the tab
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"❌ Error loading SuperLap: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #ff6666; font-size: 16px; padding: 50px;")
            error_layout.addWidget(error_label)
            
            # Replace with error widget
            while self._superlap_tab_widget.layout().count():
                child = self._superlap_tab_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            self._superlap_tab_widget.layout().addWidget(error_widget)

    def on_iracing_connected(self, is_connected, session_info=None):
        """Handle connection status changes from iRacing API."""
        logger.info(f"UI: on_iracing_connected called with is_connected={is_connected}")
        self.is_connected = is_connected
        self._update_connection_status()

    def on_session_info_changed(self, session_info):
        """Handle session info changes from iRacing API callbacks."""
        logger.info("UI: on_session_info_changed (legacy callback) called.")
        self.session_info = session_info

    def _update_connection_status(self, payload: dict = None):
        """Update UI based on connection status and session info signal payload."""
        if payload is None:
            payload = {"is_connected": self.is_connected, "session_info": self.session_info}
            
        logger.debug(f"UI received update signal with payload: {payload}")
        # Extract info from the payload sent by the signal
        is_connected = payload.get("is_connected", False)
        session_info = payload.get("session_info", {})

        # Update internal state
        self.is_connected = is_connected
        self.session_info = session_info

        if self.is_connected:
            self.connection_label.setText("iRacing: Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")

            # Get latest track/car/config from the received session_info dictionary
            track_name = session_info.get("current_track", "No Track")
            config_name = session_info.get("current_config")
            car_name = session_info.get("current_car", "No Car")

            # Format track display text
            track_display_text = f"Track: {track_name}"
            if config_name and config_name != "Default":
                track_display_text += f" ({config_name})"

            # Update labels in the status bar
            self.track_label.setText(track_display_text)
            self.driver_label.setText(f"Car: {car_name}")

        else:
            # Disconnected state
            self.connection_label.setText("iRacing: Disconnected")
            self.driver_label.setText("No Driver")
            self.track_label.setText("No Track")

    def on_telemetry_data(self, telemetry_data):
        """Handle telemetry data from iRacing API."""
        # Update overview tab with telemetry data
        if hasattr(self, 'overview_tab'):
            self.overview_tab.update_telemetry(telemetry_data)

    def toggle_diagnostic_mode(self):
        """Toggle diagnostic mode for lap detection."""
        # Implementation would go here
        current_text = self.diagnostic_mode_button.text()
        if "OFF" in current_text:
            self.diagnostic_mode_button.setText("🔍 Diagnostics: ON")
            self.diagnostic_mode_button.setStyleSheet("background-color: #0A5A0A; color: #00FF00; padding: 5px 10px; border-radius: 3px;")
        else:
            self.diagnostic_mode_button.setText("🔍 Diagnostics: OFF")
            self.diagnostic_mode_button.setStyleSheet("background-color: #333; color: #AAA; padding: 5px 10px; border-radius: 3px;")

    def show_lap_debug_dialog(self):
        """Show lap debug dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Lap Debug Information")
        dialog.setModal(True)
        dialog.resize(500, 400)

        layout = QVBoxLayout(dialog)

        # Debug text area
        debug_text = QTextEdit()
        debug_text.setReadOnly(True)
        debug_text.setPlainText("Lap debug information would be displayed here...")
        layout.addWidget(debug_text)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec_()

    def reset_iracing_connection(self):
        """Reset iRacing connection."""
        if hasattr(self, 'iracing_api') and self.iracing_api:
            try:
                # Implementation would depend on the API
                logger.info("Resetting iRacing connection...")
                QMessageBox.information(self, "Connection Reset", "iRacing connection reset attempted.")
            except Exception as e:
                logger.error(f"Error resetting iRacing connection: {e}")
                QMessageBox.warning(self, "Reset Error", f"Error resetting connection: {str(e)}")
        else:
            QMessageBox.information(self, "No Connection", "No iRacing API connection to reset.")

    def get_track_length(self):
        """Get track length for telemetry widgets."""
        # Implementation would get track length from session info
        return None 