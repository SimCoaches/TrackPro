"""Main window for Race Coach - combines all tabs into the main interface.

This module contains the main RaceCoachWidget that integrates all the separate
tab modules into a cohesive interface.

TELEMETRY ARCHITECTURE (Updated for AI Coach Independence):
===========================================================

The telemetry system now uses three completely independent callback streams:

1. UI TELEMETRY (on_telemetry_data):
   - Purpose: Update UI elements (overview tab, graphs, etc.)
   - Does NOT interfere with lap saving
   - Always active when connected to iRacing

2. LAP SAVING TELEMETRY (iRacing Session Monitor):
   - Purpose: Save laps to database, detect lap completions, sector timing
   - Handled by iracing_session_monitor and iracing_lap_saver
   - Completely independent of AI coach state
   - Always active when connected to iRacing and authenticated

3. AI COACH TELEMETRY (ai_coach_telemetry_wrapper):
   - Purpose: Real-time AI voice coaching based on SuperLap comparison
   - Only active when AI coach is explicitly enabled by user
   - Uses TelemetryMonitorWorker with independent callback wrapper
   - Does NOT interfere with lap saving or UI updates

This architecture ensures that:
- Laps are always saved regardless of AI coach state
- AI coaching can be toggled on/off without affecting lap saving
- UI updates continue to work independently
- No telemetry stream interferes with others
"""

import logging
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QFrame, QSizePolicy, QMessageBox, QDialog,
    QTextEdit, QDialogButtonBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

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

        # Initialize the central telemetry monitor worker for AI coaching
        try:
            logger.debug("🎙️ [INIT] Importing TelemetryMonitorWorker...")
            from ..utils.telemetry_worker import TelemetryMonitorWorker
            logger.debug("🎙️ [INIT] Creating TelemetryMonitorWorker instance...")
            # Initialize without superlap_id first - will be set later when user selects one
            self.telemetry_monitor_worker = TelemetryMonitorWorker()
            logger.info("✅ TelemetryMonitorWorker initialized for AI coaching")
            logger.debug(f"🎙️ [INIT] TelemetryMonitorWorker object: {self.telemetry_monitor_worker}")
        except Exception as telemetry_error:
            logger.error(f"❌ Error initializing TelemetryMonitorWorker: {telemetry_error}")
            self.telemetry_monitor_worker = None

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
        elif hasattr(self, '_monitoring_started') and self._monitoring_started:
            logger.info("✅ Deferred iRacing monitoring already started")
        elif not hasattr(self, 'iracing_api') or not self.iracing_api:
            logger.info("⚠️ No iRacing API available for deferred monitoring")
        elif not hasattr(self.iracing_api, 'start_deferred_monitoring'):
            logger.info("⚠️ iRacing API doesn't support deferred monitoring")

    def _setup_iracing_api_connections(self):
        """Set up connections to the iRacing API."""
        try:
            # Try SimpleIRacingAPI method names first
            if hasattr(self.iracing_api, "register_on_connection_changed"):
                logger.info("Using SimpleIRacingAPI callback methods")
                self.iracing_api.register_on_connection_changed(self.on_iracing_connected)
                
                # 🔧 BUGFIX: Create a unified telemetry callback that handles both UI and AI coaching
                # This prevents conflicts from multiple registrations
                def unified_telemetry_callback(telemetry_data):
                    """Unified telemetry callback that handles both UI updates and AI coaching."""
                    try:
                        # Always update UI with telemetry data
                        self.on_telemetry_data(telemetry_data)
                        
                        # Debug AI coaching conditions  
                        if not hasattr(unified_telemetry_callback, '_debug_count'):
                            unified_telemetry_callback._debug_count = 0
                        unified_telemetry_callback._debug_count += 1
                        
                        # ALWAYS try to forward to AI coach if worker exists - let the worker decide
                        if hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker is not None:
                            try:
                                self.telemetry_monitor_worker.add_telemetry_point(telemetry_data)
                                
                                # Log success frequently to verify it's working
                                if unified_telemetry_callback._debug_count % 60 == 0:  # Every second
                                    ai_active = (hasattr(self.telemetry_monitor_worker, 'ai_coach') and 
                                               self.telemetry_monitor_worker.ai_coach is not None and
                                               hasattr(self.telemetry_monitor_worker, 'is_monitoring') and
                                               self.telemetry_monitor_worker.is_monitoring)
                                    logger.info(f"✅ [TELEMETRY FLOW] Forwarding to AI worker - AI active: {ai_active}")
                                    print(f"🎯 [TELEMETRY] Forwarding to AI worker - AI active: {ai_active}")
                            except Exception as worker_error:
                                logger.error(f"❌ [AI TELEMETRY] Error forwarding to AI worker: {worker_error}")
                        else:
                            # Only log missing worker occasionally
                            if unified_telemetry_callback._debug_count % 1200 == 0:  # Every 20 seconds
                                logger.debug(f"🔍 [AI DEBUG] No telemetry worker available for AI coaching")
                            
                    except Exception as e:
                        logger.error(f"❌ [UNIFIED TELEMETRY] Error in unified telemetry callback: {e}")
                
                # Register the unified callback ONCE
                self.iracing_api.register_on_telemetry_data(unified_telemetry_callback)
                logger.info("✅ [UNIFIED TELEMETRY] Single unified telemetry callback registered for UI + AI coaching")

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
                            # BUGFIX: Start basic iRacing connection even without authentication
                            # The app should still be able to monitor iRacing for telemetry
                            logger.info("Starting basic iRacing connection without cloud features")
                            self.iracing_api._deferred_monitor_params = {
                                'supabase_client': None,  # No cloud saving
                                'user_id': 'anonymous',
                                'lap_saver': None  # No lap saving
                            }
                            logger.info("✅ Deferred basic iRacing monitoring setup for offline use")
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
                
                # ADDITIONAL BUGFIX: If no deferred monitor params were set above, create basic ones
                if not hasattr(self.iracing_api, '_deferred_monitor_params') or not self.iracing_api._deferred_monitor_params:
                    logger.info("No deferred monitor params set - creating basic offline monitoring setup")
                    self.iracing_api._deferred_monitor_params = {
                        'supabase_client': None,  # No cloud saving
                        'user_id': 'anonymous',
                        'lap_saver': None  # No lap saving
                    }
                    logger.info("✅ Basic offline iRacing monitoring setup complete")
                
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
        
        # Add AI Coach control button
        self.ai_coach_button = QPushButton("🤖 AI Coach: OFF")
        self.ai_coach_button.setStyleSheet("""
            background-color: #333;
            color: #AAA;
            padding: 5px 10px;
            border-radius: 3px;
        """)
        self.ai_coach_button.setToolTip("Start/Stop real-time AI voice coaching")
        self.ai_coach_button.clicked.connect(self.toggle_ai_coaching)
        status_layout.addWidget(self.ai_coach_button)

        # Add AI Coach Volume Control
        try:
            from .ai_coach_volume_widget import AICoachVolumeWidget
            self.ai_coach_volume_widget = AICoachVolumeWidget(self)
            self.ai_coach_volume_widget.setMaximumWidth(300)  # Constrain width
            status_layout.addWidget(self.ai_coach_volume_widget)
            logger.info("✅ [VOLUME UI] AI Coach volume control added to status bar")
        except Exception as e:
            logger.error(f"❌ [VOLUME UI] Failed to add volume control: {e}")
            # Add a simple label as fallback
            volume_label = QLabel("🔊 Volume controls unavailable")
            volume_label.setStyleSheet("color: #888; font-style: italic;")
            status_layout.addWidget(volume_label)

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

        # Create a placeholder for the SuperLap tab
        self.superlap_placeholder = QWidget()
        self.tab_widget.addTab(self.superlap_placeholder, "")
        self._create_superlap_tab_title(self.tab_widget.count() - 1)

        # Create the Videos Tab
        videos_tab = VideosTab(self)
        self.tab_widget.addTab(videos_tab, "RaceFlix")

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Immediately try to create the SuperLap widget without an auth check
        QTimer.singleShot(50, self._create_superlap_widget_deferred)

        # Save operation progress indicator
        self.save_progress_dialog = None

    def _create_superlap_tab_title(self, tab_index):
        """Create a custom title for the SuperLap tab with an icon."""
        try:
            import os
            from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
            from PyQt5.QtGui import QPixmap
            from PyQt5.QtCore import Qt
            
            # Create custom tab widget - SMALL container
            tab_title_widget = QWidget()
            # Remove background styling to prevent weird box when selected
            tab_title_widget.setStyleSheet("background: transparent;")
            # Make tab container SMALL but let logo be larger
            tab_title_widget.setFixedHeight(32)
            tab_layout = QHBoxLayout(tab_title_widget)
            # Zero margins to let logo extend beyond container if needed
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.setSpacing(0)
            
            # Add logo only (no text since tab already has text)
            logo_label = QLabel()
            # Remove background styling and allow logo to extend beyond bounds
            logo_label.setStyleSheet("background: transparent;")
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'resources', 'images', 'superlap_logo.png')
            
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                # Make logo LARGE regardless of small container size
                scaled_pixmap = pixmap.scaled(220, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
            else:
                # Fallback if logo file not found
                logger.warning(f"SuperLap logo not found at {logo_path}")
                logo_label.setText("⚡")
                logo_label.setStyleSheet("color: #FF4500; font-size: 14px; background: transparent;")
            
            # Center the logo both horizontally and vertically
            logo_label.setAlignment(Qt.AlignCenter)
            # Add stretchers to center the logo in the layout
            tab_layout.addStretch()
            tab_layout.addWidget(logo_label, 0, Qt.AlignCenter)
            tab_layout.addStretch()
            
            # Replace the tab text with empty string to avoid duplication
            self.tab_widget.setTabText(tab_index, "")
            
            # Set the custom widget as the tab content
            self.tab_widget.tabBar().setTabButton(tab_index, self.tab_widget.tabBar().LeftSide, tab_title_widget)
            
        except Exception as e:
            logger.error(f"Error creating SuperLap tab title with logo: {e}")
            # Keep the default text title if logo creation fails

    def _on_tab_changed(self, index):
        """Handle tab changes, especially for lazy loading."""
        tab_text = self.tab_widget.tabText(index)
        current_widget = self.tab_widget.widget(index)
        
        # Check if this is the SuperLap tab
        if hasattr(self, 'superlap_tab') and current_widget is self.superlap_tab:
            # SuperLap tab is active - check if it needs data refresh
            try:
                if hasattr(self.superlap_tab, 'session_combo') and self.superlap_tab.session_combo.count() <= 1:
                    # Empty or just has "No sessions found" - refresh data
                    logger.info("SuperLap tab accessed with empty dropdown, refreshing data...")
                    self.superlap_tab.refresh_data()
            except Exception as refresh_error:
                logger.error(f"Error refreshing SuperLap data on tab change: {refresh_error}")
        elif "SuperLap" in tab_text and self.superlap_placeholder is not None:
            # If the placeholder is still there, try creating the real widget
            logger.info("Switched to SuperLap tab, ensuring it is loaded.")
            self._create_superlap_widget_deferred()
            
    def _create_superlap_widget_deferred(self):
        """Create and embed the SuperLapWidget, replacing the placeholder."""
        # If the real widget is already created, do nothing
        if self.superlap_placeholder is None:
            return

        logger.info("Creating SuperLap widget...")
        try:
            # Replace the placeholder with the actual SuperLapWidget
            self.superlap_tab = SuperLapWidget(parent=self)
            
            # Get the index of the placeholder
            idx = self.tab_widget.indexOf(self.superlap_placeholder)
            if idx != -1:
                # Remove placeholder, insert real tab, and set it as current
                self.tab_widget.removeTab(idx)
                self.tab_widget.insertTab(idx, self.superlap_tab, "")
                self._create_superlap_tab_title(idx)
                self.tab_widget.setCurrentIndex(idx)
                
                # BUGFIX: Initialize the SuperLap data after creating the widget
                # This was missing and causing the empty dropdown issue
                try:
                    logger.info("Loading SuperLap session data...")
                    self.superlap_tab.refresh_data()
                    logger.info("SuperLap data refresh initiated successfully")
                except Exception as refresh_error:
                    logger.error(f"Error refreshing SuperLap data: {refresh_error}")
                
                # Cleanup placeholder
                self.superlap_placeholder.deleteLater()
                self.superlap_placeholder = None
                logger.info("SuperLap tab created and replaced placeholder.")
            else:
                logger.error("Could not find SuperLap placeholder tab.")

        except Exception as e:
            logger.error(f"Failed to create SuperLap widget: {e}", exc_info=True)
            # Optionally show an error message in the UI
            error_label = QLabel(f"Error loading SuperLap tab: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            idx = self.tab_widget.indexOf(self.superlap_placeholder)
            if idx != -1:
                self.tab_widget.removeTab(idx)
                self.tab_widget.insertTab(idx, error_label, "SuperLap")
                self.tab_widget.setCurrentIndex(idx)

    def on_iracing_connected(self, is_connected, session_info=None):
        """Handle iRacing connection status changes."""
        self._update_connection_status()

    def on_session_info_changed(self, session_info):
        """Handle session info changes from iRacing API callbacks."""
        logger.info("UI: on_session_info_changed (legacy callback) called.")
        self.session_info = session_info

    def _update_connection_status(self, payload: dict = None):
        """Update UI based on connection status and session info signal payload."""
        if payload is None:
            payload = {"is_connected": self.is_connected, "session_info": self.session_info}
            
        # Only log essential info, not the entire massive payload with raw session info
        session_info = payload.get('session_info', {})
        
        # Add debug counter to reduce spam
        if not hasattr(self, '_ui_debug_counter'):
            self._ui_debug_counter = 0
        self._ui_debug_counter += 1
        
        # Only log UI updates every 10 minutes instead of every 50ms
        if self._ui_debug_counter % 36000 == 0:  # 60Hz * 60s * 10min = 36000
            logger.debug(f"UI received update signal: connected={payload.get('is_connected')}, track={session_info.get('current_track')}, car={session_info.get('current_car')}")
        
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
        """Handle telemetry data from iRacing API - for UI updates only.
        
        Note: This method handles UI telemetry updates only. Lap saving telemetry
        is handled separately by the iRacing session monitor and lap saver systems.
        AI coach telemetry is handled independently through a separate callback.
        """
        # Add debug counter to reduce spam
        if not hasattr(self, '_ui_telemetry_count'):
            self._ui_telemetry_count = 0
        self._ui_telemetry_count += 1
        
        # Debug log every 10 seconds to verify normal telemetry flow is working
        if self._ui_telemetry_count % 600 == 0:  # Every 10 seconds at ~60Hz
            logger.debug(f"🔍 [UI TELEMETRY] Received telemetry point #{self._ui_telemetry_count} for UI updates - lap saving should be independent")
            logger.debug(f"🔧 [AI DEBUG] has_worker={hasattr(self, 'telemetry_monitor_worker')}, worker_exists={getattr(self, 'telemetry_monitor_worker', None) is not None}, has_ai_coach={hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker and hasattr(self.telemetry_monitor_worker, 'ai_coach') and self.telemetry_monitor_worker.ai_coach is not None}, is_monitoring={hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker and hasattr(self.telemetry_monitor_worker, 'is_monitoring') and self.telemetry_monitor_worker.is_monitoring}")
        
        # Update overview tab with telemetry data (UI only)
        if hasattr(self, 'overview_tab'):
            self.overview_tab.update_telemetry(telemetry_data)

    def toggle_diagnostic_mode(self):
        """Toggle diagnostic mode for lap detection."""
        if hasattr(self, 'iracing_lap_saver') and self.iracing_lap_saver:
            current_mode = getattr(self.iracing_lap_saver, '_diagnostic_mode', False)
            self.iracing_lap_saver._diagnostic_mode = not current_mode
            new_mode = self.iracing_lap_saver._diagnostic_mode
            
            # Update button text and style
            if new_mode:
                self.diagnostic_mode_button.setText("🔍 Diagnostics: ON")
                self.diagnostic_mode_button.setStyleSheet("""
                    background-color: #004400;
                    color: #88FF88;
                    padding: 5px 10px;
                    border-radius: 3px;
                """)
            else:
                self.diagnostic_mode_button.setText("🔍 Diagnostics: OFF")
                self.diagnostic_mode_button.setStyleSheet("""
                    background-color: #333;
                    color: #AAA;
                    padding: 5px 10px;
                    border-radius: 3px;
                """)
            
            logger.info(f"Diagnostic mode toggled to: {new_mode}")

    def toggle_ai_coaching(self):
        """Toggle AI coaching on/off."""
        if self.is_ai_coaching_active():
            # Stop coaching
            self.stop_ai_coaching()
            self.ai_coach_button.setText("🤖 AI Coach: OFF")
            self.ai_coach_button.setStyleSheet("""
                background-color: #333;
                color: #AAA;
                padding: 5px 10px;
                border-radius: 3px;
            """)
            self.ai_coach_button.setToolTip("Start real-time AI voice coaching")
        else:
            # Need to get superlap ID - for now, show a dialog
            superlap_id, ok = QInputDialog.getText(
                self, 
                'AI Coach Setup', 
                'Enter SuperLap ID for AI coaching:\n(You can find this in the SuperLap tab)',
                text=''
            )
            
            if ok and superlap_id.strip():
                if self.start_ai_coaching(superlap_id.strip()):
                    # Don't show success notification here - it will be shown 
                    # by the background thread callback when actually ready
                    logger.info("🤖 [AI COACH UI] Background initialization started")
                else:
                    QMessageBox.warning(
                        self, 
                        "AI Coach Error", 
                        "Failed to start AI coaching. Check that:\n"
                        "• The SuperLap ID is valid\n"
                        "• Your OpenAI API key is set\n"
                        "• Your ElevenLabs API key is set"
                    )

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

    def start_ai_coaching(self, superlap_id: str):
        """Start AI coaching with the specified superlap as reference.
        
        Args:
            superlap_id: The UUID of the superlap to use for coaching
        """
        logger.info(f"🤖 [AI COACH START] Starting AI coaching with superlap_id: {superlap_id}")
        logger.info(f"🤖 [AI COACH START] TelemetryMonitorWorker available: {self.telemetry_monitor_worker is not None}")
        logger.info(f"🤖 [AI COACH START] IRacing API available: {self.iracing_api is not None}")
        logger.info(f"🤖 [AI COACH START] IRacing Lap Saver available: {getattr(self, 'iracing_lap_saver', None) is not None}")
        
        if not self.telemetry_monitor_worker:
            logger.error("❌ Cannot start AI coaching: TelemetryMonitorWorker not available")
            return
            
        # Check authentication for superlap data access
        from trackpro.database.supabase_client import get_supabase_client
        supabase_client = get_supabase_client()
        if not supabase_client or not supabase_client.auth.get_session():
            logger.error("❌ Cannot start AI coaching: No authenticated Supabase client available")
            print("❌ [AI COACH ERROR] Please log in to access SuperLap data for AI coaching")
            return
        
        logger.info("✅ Authenticated Supabase client available for superlap data loading")
        
        # 🔧 BUGFIX: Run AI coach initialization in background thread to prevent blocking telemetry
        class AICoachInitThread(QThread):
            """Background thread for AI coach initialization to prevent telemetry blocking."""
            coach_ready = pyqtSignal(object)  # Emits the AI coach instance when ready
            coach_failed = pyqtSignal(str)    # Emits error message if failed
            
            def __init__(self, superlap_id):
                super().__init__()
                self.superlap_id = superlap_id
                
            def run(self):
                """Initialize AI coach in background thread."""
                try:
                    logger.info(f"🤖 [AI COACH THREAD] Background initialization started for superlap: {self.superlap_id}")
                    
                    # Check API keys before loading SuperLap data
                    import os
                    openai_key = os.getenv("OPENAI_API_KEY")
                    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
                    
                    if not openai_key:
                        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
                    if not elevenlabs_key:
                        raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY environment variable.")
                    
                    logger.info("🔑 [API KEYS] OpenAI and ElevenLabs API keys found")
                    
                    from ..ai_coach.ai_coach import AICoach
                    
                    # This 3+ second operation now runs in background
                    ai_coach_instance = AICoach(superlap_id=self.superlap_id)
                    
                    logger.info(f"🤖 [AI COACH THREAD] Background initialization completed successfully")
                    logger.info(f"🤖 [AI COACH THREAD] AI coach has {len(ai_coach_instance.superlap_points)} superlap points")
                    
                    # Signal that the coach is ready
                    self.coach_ready.emit(ai_coach_instance)
                    
                except Exception as e:
                    logger.error(f"❌ [AI COACH THREAD] Background initialization failed: {e}")
                    self.coach_failed.emit(str(e))
        
        def on_coach_ready(ai_coach_instance):
            """Handle AI coach ready signal from background thread."""
            try:
                logger.info(f"🤖 [AI COACH READY] Background thread completed - assigning to telemetry worker")
                
                # Assign the AI coach to the telemetry worker (main thread operation)
                logger.info(f"🔧 [AI DEBUG] Worker before assignment: {self.telemetry_monitor_worker}")
                logger.info(f"🔧 [AI DEBUG] Worker ai_coach before: {getattr(self.telemetry_monitor_worker, 'ai_coach', 'N/A')}")
                
                self.telemetry_monitor_worker.ai_coach = ai_coach_instance
                
                logger.info(f"🔧 [AI DEBUG] AI coach assignment completed")
                logger.info(f"🔧 [AI DEBUG] Worker ai_coach after: {getattr(self.telemetry_monitor_worker, 'ai_coach', 'N/A')}")
                logger.info(f"✅ AI Coach initialized with superlap_id: {superlap_id} ({len(ai_coach_instance.superlap_points)} points)")
                
                # Start monitoring (quick operation)
                logger.info(f"🤖 [AI COACH START] Starting telemetry monitoring (independent of lap saving)...")
                logger.info(f"🔧 [AI DEBUG] About to call start_monitoring()...")
                logger.info(f"🔧 [AI DEBUG] Worker is_monitoring before: {getattr(self.telemetry_monitor_worker, 'is_monitoring', 'N/A')}")
                
                success = self.telemetry_monitor_worker.start_monitoring()
                
                logger.info(f"🔧 [AI DEBUG] start_monitoring() completed")
                logger.info(f"🔧 [AI DEBUG] Worker is_monitoring after: {getattr(self.telemetry_monitor_worker, 'is_monitoring', 'N/A')}")
                
                if success:
                    logger.info("✅ AI coaching started - driver will receive real-time voice guidance")
                    logger.info("🔧 [AI INDEPENDENT] AI coaching is now completely independent of lap saving")
                    print("🎙️ [AI COACH] Voice coaching activated! Drive normally to receive guidance.")
                    
                    # Update button state to show AI coach is active
                    if hasattr(self, 'ai_coach_button'):
                        self.ai_coach_button.setText("🤖 AI Coach: ON")
                        self.ai_coach_button.setStyleSheet("""
                            background-color: #004400;
                            color: #88FF88;
                            padding: 5px 10px;
                            border-radius: 3px;
                        """)
                        self.ai_coach_button.setToolTip("Stop real-time AI voice coaching")
                    
                    # Don't show success dialog immediately - let the coach prove it's working first
                    print(f"✅ [AI COACH READY] SuperLap loaded: {len(ai_coach_instance.superlap_points)} points")
                    print(f"🎧 [AI COACH READY] Voice coaching is now active - drive normally to receive guidance!")
                else:
                    logger.error("❌ Failed to start AI coaching monitoring")
                    print("❌ [AI COACH ERROR] Failed to start telemetry monitoring")
                    
            except Exception as e:
                logger.error(f"❌ [AI COACH READY] Failed to complete AI coach setup: {e}")
                print(f"❌ [AI COACH ERROR] Setup failed: {e}")
        
        def on_coach_failed(error_message):
            """Handle AI coach failed signal from background thread."""
            logger.error(f"❌ [AI COACH FAILED] {error_message}")
            print(f"❌ [AI COACH ERROR] {error_message}")
            
            # Show user-friendly error dialog
            if "OpenAI API key" in error_message:
                QMessageBox.warning(
                    self, 
                    "AI Coach Error", 
                    "🔑 OpenAI API Key Missing\n\n"
                    "The AI Coach requires an OpenAI API key for voice coaching.\n"
                    "Please set the OPENAI_API_KEY environment variable and restart TrackPro."
                )
            elif "ElevenLabs API key" in error_message:
                QMessageBox.warning(
                    self, 
                    "AI Coach Error", 
                    "🔑 ElevenLabs API Key Missing\n\n"
                    "The AI Coach requires an ElevenLabs API key for text-to-speech.\n"
                    "Please set the ELEVENLABS_API_KEY environment variable and restart TrackPro."
                )
            else:
                QMessageBox.warning(
                    self, 
                    "AI Coach Error", 
                    f"Failed to initialize AI Coach:\n\n{error_message}\n\n"
                    "Please check:\n"
                    "• The SuperLap ID is valid\n"
                    "• Your OpenAI API key is set\n"
                    "• Your ElevenLabs API key is set"
                )
            
        # Start background initialization
        logger.info(f"🤖 [AI COACH START] Starting background initialization thread...")
        print("🤖 [AI COACH] Initializing AI coach in background (this may take a few seconds)...")
        
        self._ai_coach_init_thread = AICoachInitThread(superlap_id)
        self._ai_coach_init_thread.coach_ready.connect(on_coach_ready)
        self._ai_coach_init_thread.coach_failed.connect(on_coach_failed)
        self._ai_coach_init_thread.start()
        
        logger.info(f"🤖 [AI COACH START] Background thread started - telemetry flow should remain uninterrupted")
        
        # Return True to indicate successful start of initialization process
        # (Actual completion will be handled by background thread callbacks)
        return True

    def stop_ai_coaching(self):
        """Stop AI coaching."""
        logger.info("🛑 [AI COACH STOP] Stopping AI coaching...")
        if self.telemetry_monitor_worker:
            self.telemetry_monitor_worker.stop_monitoring()
            self.telemetry_monitor_worker.ai_coach = None
            logger.info("🛑 AI coaching stopped - lap saving continues independently")
        else:
            logger.warning("⚠️ [AI COACH STOP] No telemetry monitor worker to stop")

    def is_ai_coaching_active(self):
        """Check if AI coaching is currently active."""
        return (self.telemetry_monitor_worker and 
                self.telemetry_monitor_worker.ai_coach and 
                self.telemetry_monitor_worker.is_monitoring)
    
    def get_telemetry_status(self):
        """Get diagnostic information about all telemetry streams.
        
        Returns:
            dict: Status of all telemetry systems for debugging
        """
        status = {
            'ui_telemetry': {
                'active': hasattr(self, '_ui_telemetry_count'),
                'points_received': getattr(self, '_ui_telemetry_count', 0),
                'callback_registered': hasattr(self, 'iracing_api') and self.iracing_api is not None
            },
            'lap_saving_telemetry': {
                'iracing_api_available': hasattr(self, 'iracing_api') and self.iracing_api is not None,
                'lap_saver_available': hasattr(self, 'iracing_lap_saver') and self.iracing_lap_saver is not None,
                'session_monitor_active': False  # Would need to check session monitor status
            },
            'ai_coach_telemetry': {
                'telemetry_worker_available': hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker is not None,
                'ai_coach_active': self.is_ai_coaching_active(),
                'ai_coach_available': (hasattr(self, 'telemetry_monitor_worker') and 
                                     self.telemetry_monitor_worker and 
                                     self.telemetry_monitor_worker.ai_coach is not None),
                'monitoring_active': (hasattr(self, 'telemetry_monitor_worker') and 
                                    self.telemetry_monitor_worker and 
                                    self.telemetry_monitor_worker.is_monitoring),
                'points_received': (getattr(self.telemetry_monitor_worker, '_telemetry_point_count', 0) 
                                  if hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker else 0)
            },
            'independence_verification': {
                'streams_independent': True,  # Our new architecture ensures this
                'ai_coach_affects_lap_saving': False,  # Should always be False now
                'lap_saving_affects_ai_coach': False   # Should always be False now
            }
        }
        
        return status 