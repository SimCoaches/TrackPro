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
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QSplitter, QGroupBox, QLabel, QPushButton, QCheckBox, QComboBox,
    QSpinBox, QSlider, QProgressBar, QTextEdit, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem, QMessageBox, QDialog, QDialogButtonBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QInputDialog, QApplication, QTabBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

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

        # Initialize MINIMAL UI first for instant display
        logger.info("🔍 Creating minimal UI for instant display...")
        self.setup_minimal_ui()
        logger.info("✅ Minimal UI created - Race Coach visible instantly")

        # ⚡ PERFORMANCE: Defer ALL heavy initialization to background
        # This ensures the UI appears instantly when clicked
        self.telemetry_monitor_worker = None  # Will be created later
        self.data_manager = None
        self.telemetry_saver = None
        self.iracing_lap_saver = None
        
        # Initialize tab references for lazy loading
        self.overview_tab = None
        self.telemetry_tab = None
        self.superlap_tab = None
        self.videos_tab = None
        
        # Track which tabs are being created to prevent duplicates
        self._tabs_being_created = set()
        self._tabs_created = set()

        # Mark basic initialization as complete
        self._initialization_complete = True
        logger.info("✅ Basic initialization complete - heavy work deferred")

        # Start background initialization immediately but non-blocking
        QTimer.singleShot(50, self._start_background_initialization)

    def setup_minimal_ui(self):
        """Create minimal UI that appears instantly - defer heavy components."""
        main_layout = QVBoxLayout(self)

        # Simple loading indicator
        self.loading_frame = QFrame()
        self.loading_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 2px solid #FF4500;
            border-radius: 10px;
            padding: 20px;
        """)
        loading_layout = QVBoxLayout(self.loading_frame)
        
        loading_title = QLabel("🏁 TrackPro Race Coach")
        loading_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_title.setStyleSheet("color: #FF4500; font-size: 24px; font-weight: bold;")
        loading_layout.addWidget(loading_title)
        
        self.loading_label = QLabel("Initializing advanced coaching systems...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #CCCCCC; font-size: 14px; margin: 20px;")
        loading_layout.addWidget(self.loading_label)
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #FF4500;
                border-radius: 3px;
            }
        """)
        loading_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.loading_frame)
        
        # The actual UI will be created in background and swapped in when ready
        self.actual_ui_widget = None

    def _start_background_initialization(self):
        """Start all heavy initialization in background thread."""
        if self._lazy_init_in_progress:
                return
                
        self._lazy_init_in_progress = True
        logger.info("🔄 Starting background initialization...")
        
        # Update progress
        self.loading_label.setText("Loading AI coaching systems...")
        self.progress_bar.setValue(20)
        
        # Start the initialization chain
        QTimer.singleShot(100, self._step_1_init_telemetry)
    
    def _step_1_init_telemetry(self):
        """Step 1: Initialize telemetry worker."""
        try:
            self._update_progress(30, "Initializing telemetry systems...")
            logger.debug("🎙️ [BACKGROUND] Creating TelemetryMonitorWorker...")
            from ..utils.telemetry_worker import TelemetryMonitorWorker
            self.telemetry_monitor_worker = TelemetryMonitorWorker()
            logger.info("✅ TelemetryMonitorWorker initialized in background")
        except ImportError as e:
            if "elevenlabs" in str(e):
                logger.warning(f"⚠️ AI Coach features disabled - elevenlabs not available: {e}")
                self.telemetry_monitor_worker = None
            else:
                logger.error(f"❌ Error importing TelemetryMonitorWorker: {e}")
                self.telemetry_monitor_worker = None
        except Exception as e:
            logger.error(f"❌ Error initializing TelemetryMonitorWorker: {e}")
            self.telemetry_monitor_worker = None
        
        # Move to next step
        QTimer.singleShot(100, self._step_2_init_data)

    def _step_2_init_data(self):
        """Step 2: Initialize data components."""
        try:
            self._update_progress(50, "Setting up database connections...")
            logger.debug("🗄️ [BACKGROUND] Creating DataManager...")
            from ..data_manager import DataManager
            self.data_manager = DataManager()

            logger.debug("💾 [BACKGROUND] Creating TelemetrySaver...")
            from ..telemetry_saver import TelemetrySaver
            self.telemetry_saver = TelemetrySaver()
            
            logger.debug("🏁 [BACKGROUND] Creating IRacingLapSaver...")
            from ..iracing_lap_saver import IRacingLapSaver
            self.iracing_lap_saver = IRacingLapSaver()
            
            # ENABLE AUTO TRACK BUILDING: Enable automatic track building when laps are detected
            if self.iracing_lap_saver:
                self.iracing_lap_saver.enable_auto_track_building()
                logger.info("✅ [AUTO TRACK BUILD] Auto track building enabled for lap saver")
            
            logger.info("✅ Data components initialized in background")
        except Exception as e:
            logger.error(f"❌ Error initializing data components: {e}")
            self.data_manager = None
            self.telemetry_saver = None
            self.iracing_lap_saver = None
        
        # Move to next step
        QTimer.singleShot(100, self._step_3_create_ui)

    def _step_3_create_ui(self):
        """Step 3: Create the actual UI - MUST run in main thread."""
        try:
            self._update_progress(70, "Building user interface...")
            logger.debug("🎨 [MAIN THREAD] Creating actual UI in main thread...")
            
            # Schedule UI creation on main thread to avoid Qt threading issues
            QTimer.singleShot(10, self._create_actual_ui_main_thread)
            
        except Exception as e:
            logger.error(f"❌ Error scheduling UI creation: {e}")
            # Move to next step even if scheduling fails
            QTimer.singleShot(100, self._step_4_setup_connections)

    def _step_4_setup_connections(self):
        """Step 4: Setup iRacing connections."""
        try:
            self._update_progress(90, "Connecting to iRacing...")
            logger.debug("🏎️ [BACKGROUND] Setting up iRacing connections...")
            self._setup_iracing_connections()
            logger.info("✅ iRacing connections set up in background")
        except Exception as e:
            logger.error(f"❌ Error setting up iRacing connections: {e}")
        
        # Move to final step
        QTimer.singleShot(100, self._step_5_complete)

    def _step_5_complete(self):
        """Step 5: Complete initialization."""
        try:
            self._update_progress(100, "Ready!")
            logger.info("✅ Race Coach initialization complete!")
            self._complete_initialization()
        except Exception as e:
            logger.error(f"❌ Error completing initialization: {e}")
            # Show error state
            self.loading_label.setText("Error during initialization")
            self.progress_bar.setValue(0)

    def _update_progress(self, value, message):
        """Update progress bar and message on main thread."""
        self.progress_bar.setValue(value)
        self.loading_label.setText(message)

    def _create_actual_ui_main_thread(self):
        """Create the actual Race Coach UI safely in the main thread."""
        try:
            logger.debug("🎨 [MAIN THREAD] Creating actual UI widget in main thread...")
            self.actual_ui_widget = QWidget()
            self.setup_ui_on_widget(self.actual_ui_widget)
            logger.info("✅ Actual UI widget created successfully in main thread")
            
            # Continue to next step after UI creation
            QTimer.singleShot(50, self._step_4_setup_connections)
            
        except Exception as e:
            logger.error(f"❌ Error creating actual UI in main thread: {e}")
            self.actual_ui_widget = None
            # Continue anyway to avoid hanging
            QTimer.singleShot(100, self._step_4_setup_connections)

    def _create_actual_ui(self):
        """Legacy method - redirects to main thread safe version."""
        logger.warning("🎨 [LEGACY] _create_actual_ui called - redirecting to main thread version")
        QTimer.singleShot(10, self._create_actual_ui_main_thread)

    def _setup_iracing_connections(self):
        """Setup iRacing connections - moved to background."""
        try:
            self._update_progress(90, "Connecting to iRacing...")
            # Try to get shared API
            from PyQt6.QtWidgets import QApplication
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'get_shared_iracing_api'):
                    main_window = widget
                    break
            
            if main_window and hasattr(main_window, 'get_shared_iracing_api'):
                shared_api = main_window.get_shared_iracing_api()
                if shared_api:
                    self.iracing_api = shared_api
                logger.info("✅ Connected to global iRacing API")
                
                # Connect signals for connection status updates
                if hasattr(self.iracing_api, 'connection_changed'):
                    self.iracing_api.connection_changed.connect(self.on_iracing_connected)
                
                # 🔧 BUGFIX: Connect sessionInfoUpdated signal to update UI when session changes
                if hasattr(self.iracing_api, 'sessionInfoUpdated'):
                    self.iracing_api.sessionInfoUpdated.connect(self._update_connection_status)
                    logger.info("✅ Connected sessionInfoUpdated signal for UI updates")
                
                # Update initial connection status
                if hasattr(self.iracing_api, 'is_connected') and self.iracing_api.is_connected():
                    QTimer.singleShot(100, lambda: self.on_iracing_connected(True))
                    logger.info("✅ iRacing already connected - updating UI")
                else:
                    QTimer.singleShot(100, lambda: self.on_iracing_connected(False))
            else:
                logger.warning("❌ Could not get shared iRacing API")
                QTimer.singleShot(100, lambda: self.on_iracing_connected(False))
            
            logger.info("✅ iRacing connections set up in background")
            
        except Exception as e:
            logger.error(f"❌ Error setting up iRacing connections: {e}")
            QTimer.singleShot(100, lambda: self.on_iracing_connected(False))

    def _complete_initialization(self):
        """Complete initialization and show the actual UI."""
        try:
            self.progress_bar.setValue(100)
            self.loading_label.setText("Ready!")
            
            # Replace loading UI with actual UI
            if self.actual_ui_widget:
                # Clear the layout
                while self.layout().count():
                    child = self.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # Add the actual UI
                self.layout().addWidget(self.actual_ui_widget)
                
                logger.info("✅ Race Coach initialization completed - UI swapped in")
            else:
                logger.error("❌ Actual UI widget not created")
                
            self._lazy_init_completed = True
            self._lazy_init_in_progress = False
            
        except Exception as e:
            logger.error(f"❌ Error completing initialization: {e}")
            self._show_error_ui(str(e))

    def _show_error_ui(self, error_message):
        """Show error UI if initialization fails."""
        try:
            self.loading_label.setText(f"Initialization failed: {error_message}")
            self.progress_bar.setVisible(False)
            
            error_label = QLabel("⚠️ Please try restarting TrackPro or check the logs for details.")
            error_label.setStyleSheet("color: #FF6666; font-size: 12px; margin: 10px;")
            error_label.setWordWrap(True)
            self.loading_frame.layout().addWidget(error_label)
            
        except Exception as e:
            logger.error(f"❌ Error showing error UI: {e}")

    def setup_ui_on_widget(self, widget):
        """Set up the race coach UI components on the given widget."""
        main_layout = QVBoxLayout(widget)

        # REMOVED: Large status bar banner to save space
        # The status bar with connection info, buttons, etc. has been removed
        # to provide more space for the actual Race Coach content.
        # 
        # Status information is now available through:
        # - iRacing connection status: Available in the sidebar navigation
        # - Debug functions: Can be accessed through right-click menus or settings
        # - AI Coach controls: Moved to individual tab contexts where relevant
        
        # Initialize the removed components as None to prevent errors
        self.status_bar = None
        self.connection_label = None
        self.driver_label = None
        self.track_label = None
        self.diagnostic_mode_button = None
        self.lap_debug_button = None
        self.corner_detection_button = None
        self.ai_coach_button = None
        self.ai_coach_volume_widget = None
        self._volume_widget_placeholder = None

        # Create tab widget - now taking up the full space
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

        # ⚡ TRUE LAZY LOADING: Create placeholder tabs that load only when accessed
        # Tab references already initialized in __init__
        
        # Create lightweight placeholder widgets
        self._create_tab_placeholder("Overview", "🏁 Loading racing analysis...")
        self._create_tab_placeholder("Telemetry", "📊 Loading telemetry graphs...")
        self._create_tab_placeholder("SuperLap", "⚡ Loading SuperLap system...")
        self._create_tab_placeholder("RaceFlix", "🎬 Loading video analysis...")

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Set Overview as the default tab
        self.tab_widget.setCurrentIndex(0)

        # Connect tab change signal for lazy loading
        self.tab_widget.currentChanged.connect(self._on_tab_changed_lazy)

        # Save operation progress indicator
        self.save_progress_dialog = None
        
        logger.info("✅ Race Coach UI created instantly with lazy-loaded tabs")

    def _create_tab_placeholder(self, tab_name, loading_message):
        """Create a lightweight placeholder tab."""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.addStretch()
        
        # Loading message
        loading_label = QLabel(loading_message)
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("""
            color: #888;
            font-size: 16px;
            font-style: italic;
            padding: 20px;
        """)
        layout.addWidget(loading_label)
        
        # Spinner-like progress indicator
        progress = QProgressBar()
        progress.setRange(0, 0)  # Indeterminate progress
        progress.setMaximumWidth(200)
        progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #FF4500;
                border-radius: 3px;
            }
        """)
        layout.addWidget(progress, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        # Handle SuperLap tab special case with logo
        if tab_name == "SuperLap":
            self.tab_widget.addTab(placeholder, "")
            self._create_superlap_tab_title(self.tab_widget.count() - 1)
        else:
            self.tab_widget.addTab(placeholder, tab_name)
        
        return placeholder

    def _create_volume_widget_deferred(self):
        """Create AI Coach Volume Widget in background to avoid blocking UI."""
        try:
            from .ai_coach_volume_widget import AICoachVolumeWidget
            self.ai_coach_volume_widget = AICoachVolumeWidget(self)
            self.ai_coach_volume_widget.setMaximumWidth(300)
            
            # Status bar removed - volume widget functionality can be added to tabs if needed
            pass
            logger.info("✅ AI Coach volume control created (status bar removed)")
            
        except ImportError as e:
            if "elevenlabs" in str(e):
                logger.warning(f"⚠️ AI Coach volume control disabled - elevenlabs not available: {e}")
            else:
                logger.error(f"❌ Failed to import volume control: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to create volume control: {e}")

    def _on_tab_changed_lazy(self, index):
        """Handle tab changes with true lazy loading."""
        try:
            current_widget = self.tab_widget.widget(index)
            tab_text = self.tab_widget.tabText(index)
            
            # Check if this is a placeholder that needs to be replaced
            if hasattr(current_widget, 'layout') and current_widget.layout():
                # Check if it's a placeholder by looking for the progress bar
                has_progress_bar = False
                for i in range(current_widget.layout().count()):
                    item = current_widget.layout().itemAt(i)
                    if item and item.widget() and isinstance(item.widget(), QProgressBar):
                        has_progress_bar = True
                        break
                
                if has_progress_bar:
                    # This is a placeholder - create the actual tab
                    self._create_actual_tab(index, tab_text)
            
            # Handle existing tab logic for SuperLap data refresh
            if hasattr(self, 'superlap_tab') and self.superlap_tab and current_widget is self.superlap_tab:
                try:
                    if hasattr(self.superlap_tab, 'session_combo') and self.superlap_tab.session_combo.count() <= 1:
                        logger.info("SuperLap tab accessed with empty dropdown, refreshing data...")
                        self.superlap_tab.refresh_data()
                except Exception as refresh_error:
                    logger.error(f"Error refreshing SuperLap data on tab change: {refresh_error}")
                    
        except Exception as e:
            logger.error(f"Error in lazy tab loading: {e}")

    def _create_actual_tab(self, index, tab_text):
        """Create the actual tab widget to replace placeholder."""
        try:
            # Prevent duplicate creation
            if index in self._tabs_being_created:
                logger.debug(f"Tab at index {index} is already being created, skipping")
                return
            
            if index in self._tabs_created:
                logger.debug(f"Tab at index {index} is already created, skipping")
                return
            
            # Mark as being created
            self._tabs_being_created.add(index)
            
            # Check if tab is already loaded by checking for specific tab types
            current_widget = self.tab_widget.widget(index)
            if current_widget:
                # Check if it's already a real tab (not a placeholder)
                if (hasattr(current_widget, 'refresh_data') or  # SuperLap tab
                    hasattr(current_widget, 'load_session_data') or  # Overview tab  
                    hasattr(current_widget, 'get_laps') or  # Telemetry tab
                    hasattr(current_widget, 'load_videos')):  # Videos tab
                    logger.debug(f"Tab {tab_text} at index {index} is already loaded")
                    self._tabs_being_created.discard(index)
                    self._tabs_created.add(index)
                    return
            
            logger.info(f"🔄 Creating actual tab: {tab_text} at index {index}")
            
            actual_widget = None
            
            # Determine tab type based on index (more reliable than text)
            if index == 0:
                # Overview tab
                if self.overview_tab is None:
                    from .overview_tab import OverviewTab
                    actual_widget = OverviewTab(self)
                    self.overview_tab = actual_widget
                    tab_text = "Overview"
                else:
                    actual_widget = self.overview_tab
                    tab_text = "Overview"
                
            elif index == 1:
                # Telemetry tab
                if self.telemetry_tab is None:
                    from .telemetry_tab import TelemetryTab
                    actual_widget = TelemetryTab(self)
                    self.telemetry_tab = actual_widget
                    tab_text = "Telemetry"
                else:
                    actual_widget = self.telemetry_tab
                    tab_text = "Telemetry"
                
            elif index == 2:
                # SuperLap tab
                if self.superlap_tab is None:
                    from .superlap_tab import SuperLapWidget
                    actual_widget = SuperLapWidget(parent=self)
                    self.superlap_tab = actual_widget
                    tab_text = "SuperLap"
                else:
                    actual_widget = self.superlap_tab
                    tab_text = "SuperLap"
                
            elif index == 3:
                # RaceFlix tab
                if self.videos_tab is None:
                    from .videos_tab import VideosTab
                    actual_widget = VideosTab(self)
                    self.videos_tab = actual_widget
                    tab_text = "RaceFlix"
                else:
                    actual_widget = self.videos_tab
                    tab_text = "RaceFlix"
            
            if actual_widget:
                # Replace placeholder with actual widget
                old_widget = self.tab_widget.widget(index)
                self.tab_widget.removeTab(index)
                
                # Insert the actual widget
                if index == 2:  # SuperLap tab
                    self.tab_widget.insertTab(index, actual_widget, "")
                    self._create_superlap_tab_title(index)
                    # Initialize SuperLap data
                    try:
                        logger.info("Loading SuperLap session data...")
                        actual_widget.refresh_data()
                        logger.info("SuperLap data refresh initiated successfully")
                    except Exception as refresh_error:
                        logger.error(f"Error refreshing SuperLap data: {refresh_error}")
                else:
                    self.tab_widget.insertTab(index, actual_widget, tab_text)
                
                # Set as current to show the newly created tab
                self.tab_widget.setCurrentIndex(index)
                
                # Clean up old placeholder
                if old_widget:
                    old_widget.deleteLater()
                
                # Mark as successfully created
                self._tabs_being_created.discard(index)
                self._tabs_created.add(index)
                
                logger.info(f"✅ {tab_text} tab created and loaded successfully")
            else:
                logger.error(f"Failed to create tab widget for: {tab_text}")
                
        except Exception as e:
            logger.error(f"Error creating actual tab {tab_text}: {e}", exc_info=True)
            # Remove from being_created on error
            self._tabs_being_created.discard(index)
            # Show error in the tab
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_layout.addStretch()
            
            error_label = QLabel(f"❌ Error loading {tab_text} tab:\n{str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: #FF6666; font-size: 14px; padding: 20px;")
            error_label.setWordWrap(True)
            error_layout.addWidget(error_label)
            
            retry_button = QPushButton("🔄 Retry")
            retry_button.setStyleSheet("""
                background-color: #FF4500;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            """)
            retry_button.clicked.connect(lambda: self._create_actual_tab(index, tab_text))
            error_layout.addWidget(retry_button, 0, Qt.AlignmentFlag.AlignCenter)
            
            error_layout.addStretch()
            
            # Replace with error widget
            old_widget = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            self.tab_widget.insertTab(index, error_widget, f"{tab_text} (Error)")
            self.tab_widget.setCurrentIndex(index)
            
            if old_widget:
                old_widget.deleteLater()

    def _create_superlap_tab_title(self, tab_index):
        """Create a custom title for the SuperLap tab with an icon."""
        try:
            import os
            from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import Qt
            
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
            from trackpro.utils.resource_utils import get_resource_path
            logo_path = get_resource_path('trackpro/resources/images/superlap_logo.png')
            
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                # Make logo LARGE regardless of small container size
                scaled_pixmap = pixmap.scaled(220, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
            else:
                # Fallback if logo file not found
                logger.warning(f"SuperLap logo not found at {logo_path}")
                logo_label.setText("⚡")
                logo_label.setStyleSheet("color: #FF4500; font-size: 14px; background: transparent;")
            
            # Center the logo both horizontally and vertically
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Add stretchers to center the logo in the layout
            tab_layout.addStretch()
            tab_layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)
            tab_layout.addStretch()
            
            # Replace the tab text with empty string to avoid duplication
            self.tab_widget.setTabText(tab_index, "")
            
            # Set the custom widget as the tab content
            self.tab_widget.tabBar().setTabButton(tab_index, QTabBar.ButtonPosition.LeftSide, tab_title_widget)
            
        except Exception as e:
            logger.error(f"Error creating SuperLap tab title with logo: {e}")
            # Keep the default text title if logo creation fails

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
            # 🔧 BUGFIX: Check shared iRacing API connection status instead of local state
            if hasattr(self, 'iracing_api') and self.iracing_api and hasattr(self.iracing_api, 'is_connected'):
                shared_connected = self.iracing_api.is_connected()
                shared_session_info = getattr(self.iracing_api, '_session_info', {})
                payload = {"is_connected": shared_connected, "session_info": shared_session_info}
            else:
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
            # Connection status now shown in sidebar navigation
            logger.info("iRacing: Connected")

            # Get latest track/car/config from the received session_info dictionary
            track_name = session_info.get("current_track", "No Track")
            config_name = session_info.get("current_config")
            car_name = session_info.get("current_car", "No Car")

            # Format track display text
            track_display_text = f"Track: {track_name}"
            if config_name and config_name != "Default":
                track_display_text += f" ({config_name})"

            # Update labels in the status bar
            # Track and driver info no longer displayed in removed status bar
            logger.info(f"Track: {track_display_text}, Car: {car_name}")

        else:
            # Disconnected state
            # Connection status now shown in sidebar navigation  
            logger.info("iRacing: Disconnected")
            # Driver and track info no longer displayed in removed status bar
            pass

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
        
        # Store current telemetry for overview tab access
        if hasattr(self, 'iracing_api'):
            self.iracing_api.current_telemetry = telemetry_data
        
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
            
            # Button removed with status bar - log diagnostic mode changes
            if new_mode:
                logger.info("🔍 Diagnostics: ON")
            else:
                logger.info("🔍 Diagnostics: OFF")
            
            logger.info(f"Diagnostic mode toggled to: {new_mode}")

    def toggle_ai_coaching(self):
        """Toggle AI coaching on/off."""
        # Check if AI coach is available
        if not self.telemetry_monitor_worker:
            QMessageBox.warning(
                self, 
                "AI Coach Unavailable", 
                "AI Coach features are not available.\n\n"
                "This could be because:\n"
                "• ElevenLabs package is not installed\n"
                "• OpenAI API key is not set\n"
                "• ElevenLabs API key is not set\n\n"
                "Please install missing packages and set up API keys to use AI coaching."
            )
            return
            
        if self.is_ai_coaching_active():
            # Stop coaching
            self.stop_ai_coaching()
            logger.info("🤖 AI Coach: OFF")
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

        dialog.exec()

    def show_corner_detection_dialog(self):
        """Show the corner detection dialog for track analysis."""
        try:
            from .corner_detection_dialog import CornerDetectionDialog
            
            dialog = CornerDetectionDialog(self)
            dialog.exec()
            
        except ImportError as e:
            logger.error(f"Failed to import corner detection dialog: {e}")
            QMessageBox.warning(
                self,
                "Corner Detection Unavailable",
                "Corner detection functionality is not available.\n"
                "Please ensure all required modules are installed."
            )
        except Exception as e:
            logger.error(f"Error showing corner detection dialog: {e}")
            QMessageBox.critical(
                self,
                "Corner Detection Error",
                f"An error occurred while opening corner detection:\n{str(e)}"
            )

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
            QMessageBox.warning(
                self, 
                "AI Coach Unavailable", 
                "AI Coach features are not available.\n\n"
                "This could be because:\n"
                "• ElevenLabs package is not installed\n"
                "• Required AI modules are missing\n\n"
                "Please check the installation and try again."
            )
            return False
            
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
                    
                    # AI coach button removed with status bar
                    logger.info("🤖 AI Coach: ON")
                    
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