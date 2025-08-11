import logging
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QComboBox, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QProgressBar, QSizePolicy,
    QToolButton, QMenu, QWidgetAction, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPixmap, QIcon
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class TelemetryFetchWorker(QObject):
    """Worker to load telemetry data for two laps from Supabase."""
    
    telemetry_loaded = pyqtSignal(dict, dict, str, str)  # (left_data, right_data, left_error, right_error)
    finished = pyqtSignal()
    
    def __init__(self, left_lap_id=None, right_lap_id=None):
        super().__init__()
        self.left_lap_id = left_lap_id
        self.right_lap_id = right_lap_id
        self.is_cancelled = False
        
    def run(self):
        """Load telemetry data for both laps with timeout handling."""
        import time
        left_data = None
        right_data = None
        left_error = ""
        right_error = ""
        
        start_time = time.time()
        max_load_time = 30  # 30 second timeout
        
        try:
            from Supabase.database import get_lap_telemetry_points
            
            # Load left lap telemetry with timeout and cancel checks
            if self.left_lap_id and not self.is_cancelled:
                try:
                    if time.time() - start_time > max_load_time or self.is_cancelled:
                        left_error = "Timeout or cancelled loading left lap telemetry"
                    else:
                        logger.info(f"Loading telemetry for left lap {self.left_lap_id}...")
                        left_result = get_lap_telemetry_points(self.left_lap_id)
                        if self.is_cancelled:
                            return  # Exit early if cancelled
                        if left_result[0] is not None:
                            left_data = {'points': left_result[0]}
                            logger.info(f"✅ Loaded {len(left_result[0])} points for left lap")
                        else:
                            left_error = left_result[1] or "No telemetry data found"
                            logger.warning(f"❌ Left lap telemetry: {left_error}")
                except Exception as e:
                    if not self.is_cancelled:
                        left_error = f"Error loading left lap: {str(e)}"
                        logger.error(f"Exception loading left lap telemetry: {e}")
            
            # Check cancellation before proceeding to right lap
            if self.is_cancelled:
                return
            
            # Load right lap telemetry with timeout and cancel checks
            if self.right_lap_id and not self.is_cancelled and time.time() - start_time <= max_load_time:
                try:
                    logger.info(f"Loading telemetry for right lap {self.right_lap_id}...")
                    right_result = get_lap_telemetry_points(self.right_lap_id)
                    if self.is_cancelled:
                        return  # Exit early if cancelled
                    if right_result[0] is not None:
                        right_data = {'points': right_result[0]}
                        logger.info(f"✅ Loaded {len(right_result[0])} points for right lap")
                    else:
                        right_error = right_result[1] or "No telemetry data found"
                        logger.warning(f"❌ Right lap telemetry: {right_error}")
                except Exception as e:
                    if not self.is_cancelled:
                        right_error = f"Error loading right lap: {str(e)}"
                        logger.error(f"Exception loading right lap telemetry: {e}")
            elif time.time() - start_time > max_load_time and not self.is_cancelled:
                right_error = "Timeout loading right lap telemetry"
                    
        except Exception as e:
            if not self.is_cancelled:
                logger.error(f"Critical error in telemetry worker: {e}")
                left_error = f"Critical error: {str(e)}"
                right_error = f"Critical error: {str(e)}"
        
        # Always emit finished, but only emit data if not cancelled
        try:
            if not self.is_cancelled:
                total_time = time.time() - start_time
                logger.info(f"Telemetry loading completed in {total_time:.1f}s")
                # Ensure signal payload types match declared signal (dict, dict, str, str)
                left_payload = left_data or {}
                right_payload = right_data or {}
                self.telemetry_loaded.emit(left_payload, right_payload, left_error, right_error)
            else:
                logger.info("Telemetry loading was cancelled")
        finally:
            # Always emit finished to prevent hanging threads
            self.finished.emit()
    
    def cancel(self):
        self.is_cancelled = True


class InitialLoadWorker(QObject):
    """Worker to load initial session and lap lists from Supabase."""
    
    sessions_loaded = pyqtSignal(list, str)  # (sessions_data, message)
    laps_loaded = pyqtSignal(list, str)  # (laps_data, message)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_cancelled = False
        
    def run(self):
        """Load sessions and laps from Supabase database."""
        try:
            from Supabase.database import get_sessions, get_laps
            
            # Load sessions
            if not self.is_cancelled:
                try:
                    sessions_result = get_sessions(user_only=True)
                    if sessions_result[0] is not None:
                        sessions = sessions_result[0]
                        self.sessions_loaded.emit(sessions, "Sessions loaded successfully")
                        logger.info(f"Loaded {len(sessions)} sessions from database")
                    else:
                        self.sessions_loaded.emit([], "No sessions found")
                        sessions = []
                except Exception as e:
                    logger.error(f"Error loading sessions: {e}")
                    self.error.emit(f"Error loading sessions: {str(e)}")
                    sessions = []
            
            # Load laps for the most recent session if available
            if sessions and not self.is_cancelled:
                try:
                    recent_session = sessions[0]  # Assuming sessions are ordered by date desc
                    session_id = recent_session.get('id')
                    if session_id:
                        laps_result = get_laps(session_id=session_id)
                        if laps_result[0] is not None:
                            laps = laps_result[0]
                            self.laps_loaded.emit(laps, f"Loaded {len(laps)} laps")
                            logger.info(f"Loaded {len(laps)} laps for session {session_id}")
                        else:
                            self.laps_loaded.emit([], "No laps found for session")
                except Exception as e:
                    logger.error(f"Error loading laps: {e}")
                    self.laps_loaded.emit([], f"Error loading laps: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Critical error in initial load worker: {e}")
            self.error.emit(f"Critical error: {str(e)}")
        finally:
            # Always emit finished signal to ensure thread cleanup
            self.finished.emit()
    
    def cancel(self):
        self.is_cancelled = True


class TelemetryControlsWidget(QFrame):
    """Compact telemetry controls with session and lap selection."""
    
    session_changed = pyqtSignal(int)
    ref_session_changed = pyqtSignal(int)
    lap_selection_changed = pyqtSignal()
    refresh_requested = pyqtSignal()
    track_filter_changed = pyqtSignal()
    car_filter_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                margin-bottom: 6px;
            }
            QLabel {
                color: #e0e0e0;
                font-weight: 500;
                font-size: 11px;
                margin: 0px;
                padding: 0px;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 11px;
                min-height: 12px;
                max-height: 20px;
            }
            QComboBox:hover {
                border-color: #00d4ff;
                background-color: #444;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #00d4ff;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)
        
        # Filters: moved into a popup to save horizontal space
        # Still create the combos so external code can populate/use them
        self.track_filter_combo = QComboBox()
        self.track_filter_combo.setMinimumWidth(220)
        self.track_filter_combo.currentIndexChanged.connect(self.track_filter_changed.emit)

        self.car_filter_combo = QComboBox()
        self.car_filter_combo.setMinimumWidth(200)
        self.car_filter_combo.currentIndexChanged.connect(self.car_filter_changed.emit)

        # Build popup widget for filters
        filter_popup = QWidget()
        grid = QGridLayout(filter_popup)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        grid.addWidget(QLabel("Track:"), 0, 0)
        grid.addWidget(self.track_filter_combo, 0, 1)
        grid.addWidget(QLabel("Car:"), 1, 0)
        grid.addWidget(self.car_filter_combo, 1, 1)
        # Clear button inside popup
        clear_btn = QPushButton("Clear Filters")
        def _clear_filters():
            try:
                if self.track_filter_combo.count() > 0:
                    self.track_filter_combo.setCurrentIndex(0)
                if self.car_filter_combo.count() > 0:
                    self.car_filter_combo.setCurrentIndex(0)
            except Exception:
                pass
        clear_btn.clicked.connect(_clear_filters)
        grid.addWidget(clear_btn, 2, 0, 1, 2)

        # Attach popup to a tool button
        self.filter_button = QToolButton()
        self.filter_button.setText("Filters")
        self.filter_button.setToolTip("Track and car filters")
        self.filter_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.filter_button.setStyleSheet("QToolButton { padding: 3px 8px; font-size: 11px; }")
        filter_menu = QMenu(self.filter_button)
        filter_action = QWidgetAction(filter_menu)
        filter_action.setDefaultWidget(filter_popup)
        filter_menu.addAction(filter_action)
        self.filter_button.setMenu(filter_menu)

        layout.addWidget(self.filter_button)
        layout.addWidget(QLabel("|"))  # Separator

        # Session selection (Mine)
        session_label = QLabel("My Session:")
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(300)
        self.session_combo.setMaximumWidth(400)
        self.session_combo.currentIndexChanged.connect(self.session_changed.emit)
        
        layout.addWidget(session_label)
        layout.addWidget(self.session_combo)
        layout.addWidget(QLabel("|"))  # Separator
        
        # Lap selection
        lap_a_label = QLabel("Lap A:")
        self.left_lap_combo = QComboBox()
        self.left_lap_combo.setMinimumWidth(120)
        self.left_lap_combo.setMaximumWidth(150)
        self.left_lap_combo.currentIndexChanged.connect(self.lap_selection_changed.emit)
        
        vs_label = QLabel("vs")
        vs_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px; margin: 0px 4px;")
        
        # Reference lap (Top fastest on same track)
        ref_session_label = QLabel("Reference Lap:")
        self.ref_session_combo = QComboBox()
        # Give this more room now that filters are tucked away
        self.ref_session_combo.setMinimumWidth(380)
        self.ref_session_combo.setMaximumWidth(700)
        self.ref_session_combo.currentIndexChanged.connect(self.ref_session_changed.emit)
        
        layout.addWidget(lap_a_label)
        layout.addWidget(self.left_lap_combo)
        layout.addWidget(vs_label)
        layout.addWidget(ref_session_label)
        layout.addWidget(self.ref_session_combo)
        layout.addWidget(QLabel("|"))  # Separator
        
        # Refresh button
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("Refresh session and lap lists from database")
        self.refresh_button.setMaximumWidth(30)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        
        layout.addWidget(self.refresh_button)
        layout.addStretch()


class TelemetryPage(BasePage):
    """Full-featured telemetry analysis page with Supabase integration."""
    
    def __init__(self, global_managers=None):
        super().__init__("Race Coach Telemetry", global_managers)
        
        # Initialize data
        self.sessions = []  # legacy combined list
        self.laps = []      # legacy combined list
        self.current_session_id = None  # legacy current session

        # Separate state for A (mine) and B (reference)
        self.all_my_sessions = []
        self.my_sessions = []  # filtered view
        self.community_sessions = []
        self.my_laps = []
        self.ref_laps = []
        self.current_my_session_id = None
        self.current_ref_session_id = None
        
        # Track active threads for cleanup
        self.active_threads = []
        self._is_being_destroyed = False
        
        # Initialize lazy loading flags
        self._initial_lap_load_done = False
        self._initial_load_in_progress = False
        
    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QLabel("📊 Telemetry Analysis")
        header.setObjectName("page-header")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin-bottom: 10px;
        """)
        layout.addWidget(header)
        
        # Controls
        self.controls = TelemetryControlsWidget()
        self.controls.session_changed.connect(self.on_session_changed)
        self.controls.ref_session_changed.connect(self.on_ref_session_changed)
        self.controls.lap_selection_changed.connect(self.on_lap_selection_changed)
        self.controls.refresh_requested.connect(self.refresh_session_and_lap_lists)
        layout.addWidget(self.controls)
        
        # Loading indicator
        self.loading_label = QLabel("🔄 Loading...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-style: italic;
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 8px;
                margin: 4px;
                font-size: 11px;
            }
        """)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # Live debug line (compact, always visible)
        self.debug_label = QLabel("Debug: --")
        self.debug_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.debug_label.setStyleSheet(
            """
            QLabel {
                color: #7dd3fc;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 11px;
                padding: 2px 4px;
                background: transparent;
            }
            """
        )
        layout.addWidget(self.debug_label)
        
        # Create professional telemetry legend
        self.create_telemetry_legend(layout)
        
        # Create professional hover info widget
        self.create_hover_info_widget(layout)
        
        # Create graphs container with scroll area
        self.create_graphs_container(layout)
        
        # Don't start initial data loading immediately - wait for page activation
        # QTimer.singleShot(100, self._start_initial_data_loading)
    
    def create_telemetry_legend(self, layout):
        """Create professional centralized legend for telemetry graphs."""
        try:
            from .telemetry_legend_widget import TelemetryLegendWidget
            
            self.telemetry_legend = TelemetryLegendWidget()
            self.telemetry_legend.setFixedHeight(35)
            layout.addWidget(self.telemetry_legend)
            
        except ImportError as e:
            logger.error(f"Failed to import TelemetryLegendWidget: {e}")
            # Fallback: create simple label
            legend_label = QLabel("Legend: Lap A (Blue) • Lap B (Orange)")
            legend_label.setStyleSheet("""
                QLabel {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    color: #e6edf3;
                    padding: 8px;
                    font-size: 11px;
                }
            """)
            layout.addWidget(legend_label)
            self.telemetry_legend = legend_label
            
    def create_hover_info_widget(self, layout):
        """Create professional centralized hover info widget for telemetry graphs."""
        try:
            from .telemetry_hover_info_widget import TelemetryHoverInfoWidget
            
            self.hover_info_widget = TelemetryHoverInfoWidget()
            layout.addWidget(self.hover_info_widget)
            
        except ImportError as e:
            logger.error(f"Failed to import TelemetryHoverInfoWidget: {e}")
            # Fallback: create simple label
            hover_info_label = QLabel("Hover over graphs to see detailed information")
            hover_info_label.setStyleSheet("""
                QLabel {
                    background-color: #0d1117;
                    border: 1px solid #21262d;
                    border-radius: 6px;
                    color: #7dd3fc;
                    padding: 8px;
                    font-size: 11px;
                }
            """)
            hover_info_label.setFixedHeight(40)
            layout.addWidget(hover_info_label)
            self.hover_info_widget = hover_info_label
    
    def create_graphs_container(self, layout):
        """Create the telemetry graphs container."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #21262d;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #58a6ff;
                border-radius: 4px;
                min-height: 15px;
            }
        """)
        
        graphs_container = QFrame()
        graphs_container.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: none;
                padding: 2px;
            }
        """)
        graphs_layout = QVBoxLayout(graphs_container)
        graphs_layout.setContentsMargins(2, 2, 2, 2)
        graphs_layout.setSpacing(1)  # Tighter spacing between graphs
        
        # Import and create actual graph widgets
        try:
            from trackpro.race_coach.widgets.throttle_graph import ThrottleGraphWidget
            from trackpro.race_coach.widgets.brake_graph import BrakeGraphWidget
            from trackpro.race_coach.widgets.steering_graph import SteeringGraphWidget
            from trackpro.race_coach.widgets.speed_graph import SpeedGraphWidget
            from trackpro.race_coach.widgets.gear_graph import GearGraphWidget
            
            # Create graph widgets with fixed height - compact for all graphs on screen
            GRAPH_HEIGHT = 100
            graph_size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            
            def create_graph_container(graph_widget):
                container = QFrame()
                container.setStyleSheet("""
                    QFrame {
                        background-color: #161b22;
                        border: 1px solid #30363d;
                        border-radius: 4px;
                        margin: 1px;
                    }
                """)
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(1, 1, 1, 1)  # Minimal margins
                container_layout.setSpacing(0)
                
                graph_widget.setSizePolicy(graph_size_policy)
                graph_widget.setFixedHeight(GRAPH_HEIGHT)
                container_layout.addWidget(graph_widget)
                
                return container
            
            # Create all telemetry graphs
            self.throttle_graph = ThrottleGraphWidget()
            throttle_container = create_graph_container(self.throttle_graph)
            graphs_layout.addWidget(throttle_container)
            
            # Connect hover signal to centralized hover info widget
            if hasattr(self, 'hover_info_widget'):
                self.throttle_graph.hover_data_changed.connect(self._update_hover_info)
            
            self.brake_graph = BrakeGraphWidget()
            brake_container = create_graph_container(self.brake_graph)
            graphs_layout.addWidget(brake_container)
            
            # Connect hover signal to centralized hover info widget
            if hasattr(self, 'hover_info_widget'):
                self.brake_graph.hover_data_changed.connect(self._update_hover_info)
            
            self.steering_graph = SteeringGraphWidget()
            steering_container = create_graph_container(self.steering_graph)
            graphs_layout.addWidget(steering_container)
            
            # Connect hover signal to centralized hover info widget
            if hasattr(self, 'hover_info_widget'):
                self.steering_graph.hover_data_changed.connect(self._update_hover_info)
            
            self.speed_graph = SpeedGraphWidget()
            speed_container = create_graph_container(self.speed_graph)
            graphs_layout.addWidget(speed_container)
            
            # Connect hover signal to centralized hover info widget
            if hasattr(self, 'hover_info_widget'):
                self.speed_graph.hover_data_changed.connect(self._update_hover_info)
            
            self.gear_graph = GearGraphWidget()
            gear_container = create_graph_container(self.gear_graph)
            graphs_layout.addWidget(gear_container)
            
            # Connect hover signal to centralized hover info widget
            if hasattr(self, 'hover_info_widget'):
                self.gear_graph.hover_data_changed.connect(self._update_hover_info)
            
            logger.info("✅ Created all telemetry graph widgets")
            
        except Exception as e:
            logger.error(f"Failed to create telemetry graph widgets: {e}")
            # Create placeholder if graphs fail to load
            placeholder = QLabel("Failed to load telemetry graphs")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #ff5555; font-size: 16px; padding: 50px;")
            graphs_layout.addWidget(placeholder)
        
        graphs_layout.addStretch()
        scroll_area.setWidget(graphs_container)
        layout.addWidget(scroll_area)
    
    def _start_initial_data_loading(self):
        """Start loading sessions and laps - using synchronous approach to avoid thread issues."""
        if self._initial_load_in_progress or getattr(self, '_is_being_destroyed', False):
            return
            
        self._initial_load_in_progress = True
        self.loading_label.setText("🔄 Loading sessions and laps...")
        self.loading_label.setVisible(True)
        
        # Load data synchronously to avoid thread issues
        try:
            from Supabase.database import get_sessions, get_laps
            from trackpro.database.supabase_client import supabase as main_supabase
            from trackpro.config import config as tp_config

            # Auth diagnostics
            try:
                is_auth = bool(main_supabase.is_authenticated())
                user_obj = main_supabase.get_user()
                email = None
                if user_obj:
                    email = getattr(getattr(user_obj, 'user', None), 'email', None) or getattr(user_obj, 'email', None)
                self.debug_label.setText(f"Debug: auth={is_auth} user={email or 'None'}")
                logger.info(f"[TELEM DEBUG] auth={is_auth}, user_email={email}")
                # Add environment/connectivity diagnostics to console
                try:
                    enabled = tp_config.supabase_enabled
                    url = tp_config.supabase_url
                    logger.info(f"[TELEM DEBUG] supabase_enabled={enabled}, url_set={bool(url)}")
                except Exception:
                    pass
                try:
                    conn_ok = main_supabase.check_connection()
                    logger.info(f"[TELEM DEBUG] connection_ok={conn_ok}")
                except Exception as ce:
                    logger.info(f"[TELEM DEBUG] connection_check_error={ce}")
                try:
                    sec = main_supabase.get_session_security_info()
                    logger.info(f"[TELEM DEBUG] session_security secure={sec.get('secure_session_active')} encrypted={sec.get('encryption_enabled')} exists={sec.get('session_exists')} migration_completed={sec.get('migration_completed')}")
                except Exception as se:
                    logger.info(f"[TELEM DEBUG] session_security_error={se}")

                # If we're offline, try enabling Supabase once and recheck
                try:
                    offline = getattr(main_supabase, '_offline_mode', False)
                    logger.info(f"[TELEM DEBUG] offline_mode={offline}")
                    if offline and bool(url):
                        logger.info("[TELEM DEBUG] Attempting to enable Supabase client...")
                        enabled_now = main_supabase.enable()
                        logger.info(f"[TELEM DEBUG] enable_result={enabled_now}")
                        # Re-check auth quickly to surface progress in logs
                        _ = main_supabase.is_authenticated()
                        _ = main_supabase.check_connection()
                except Exception as en_e:
                    logger.info(f"[TELEM DEBUG] enable_error={en_e}")
            except Exception as auth_e:
                self.debug_label.setText(f"Debug: auth=error {auth_e}")
                logger.warning(f"[TELEM DEBUG] Auth check error: {auth_e}")
            
            # Load my sessions
            try:
                sessions_result = get_sessions(user_only=True, only_with_laps=True)
                if sessions_result[0] is not None:
                    sessions = sessions_result[0]
                    self._on_sessions_loaded(sessions, "Sessions loaded successfully")
                    logger.info(f"Loaded {len(sessions)} MY sessions from database")
                    self.debug_label.setText(self.debug_label.text() + f" | my_sessions={len(sessions)}")
                else:
                    sessions = []
                    self._on_sessions_loaded(sessions, "No sessions found")
                    self.debug_label.setText(self.debug_label.text() + " | my_sessions=0")
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self._on_initial_load_error(f"Error loading sessions: {str(e)}")
                sessions = []
                self.debug_label.setText(self.debug_label.text() + f" | my_sessions_error={str(e)[:60]}")
            
            # Load laps for the most recent session if available
            if sessions:
                try:
                    recent_session = sessions[0]  # Assuming sessions are ordered by date desc
                    session_id = recent_session.get('id')
                    if session_id:
                        laps_result = get_laps(session_id=session_id)
                        if laps_result[0] is not None:
                            laps = laps_result[0]
                            self._on_my_laps_loaded(recent_session, laps)
                            logger.info(f"Loaded {len(laps)} laps for MY session {session_id}")
                            self.debug_label.setText(self.debug_label.text() + f" | laps={len(laps)}")
                            
                            # Avoid heavy preloading during startup to keep UI responsive
                            # Preloading can be re-enabled in a lighter form if needed
                        else:
                            self._on_my_laps_loaded(recent_session, [])
                            self.debug_label.setText(self.debug_label.text() + " | laps=0")
                except Exception as e:
                    logger.error(f"Error loading laps: {e}")
                    self._on_my_laps_loaded(recent_session, [])
                    self.debug_label.setText(self.debug_label.text() + f" | laps_error={str(e)[:60]}")

            # Load community sessions for Lap B selection
            try:
                all_sessions_result = get_sessions(user_only=False, only_with_laps=True)
                self._on_ref_sessions_loaded(all_sessions_result[0] or [])
            except Exception as e:
                logger.error(f"Error loading community sessions: {e}")
                self._on_ref_sessions_loaded([])
                    
        except Exception as e:
            logger.error(f"Critical error loading initial data: {e}")
            self._on_initial_load_error(f"Critical error: {str(e)}")
        finally:
            self._initial_load_in_progress = False
            self.loading_label.setVisible(False)
    
    def _on_sessions_loaded(self, sessions, message):
        """Handle MY sessions loaded from database (Lap A)."""
        self.all_my_sessions = sessions or []
        # Populate filter options from all sessions
        self._populate_filter_options(self.all_my_sessions)
        # Apply filters to compute visible sessions
        self._apply_filters_and_update_sessions()
        logger.info(f"My sessions loaded: {len(self.my_sessions)} sessions")
        # Select first session if available
        if self.my_sessions:
            self.controls.session_combo.setCurrentIndex(0)
    
    def _on_laps_loaded(self, laps, message):
        """Backward-compat no-op: route to MY laps handler."""
        self._on_my_laps_loaded(None, laps or [])
        self.loading_label.setVisible(False)

    def _on_my_laps_loaded(self, session, laps):
        """Handle MY laps (Lap A)."""
        self.my_laps = laps or []
        if session:
            self.current_my_session_id = session.get('id')
        logger.info(f"My laps loaded: {len(self.my_laps)} laps")
        self._update_left_lap_combo()

    def _on_ref_sessions_loaded(self, sessions):
        """Handle reference sessions (Lap B). Now replaced by fastest laps listing based on track only."""
        # When my sessions are loaded, use the first session's track/car to load fastest laps
        try:
            target_session = self.my_sessions[0] if self.my_sessions else None
            if not target_session:
                self._on_ref_fastest_laps_loaded([])
                return
            track_id = target_session.get('track_id') or (target_session.get('tracks') or {}).get('id')
            car_id = target_session.get('car_id') or (target_session.get('cars') or {}).get('id')
            if track_id:
                # Prefer same car if available to improve relevance
                self._load_fastest_ref_laps_for_track_car(track_id, car_id)
            else:
                self._on_ref_fastest_laps_loaded([])
        except Exception as e:
            logger.error(f"Error computing fastest laps request: {e}")
            self._on_ref_fastest_laps_loaded([])

    def _on_ref_laps_loaded(self, laps):
        """Handle reference laps (Lap B). Not directly used with fastest list approach."""
        self.ref_laps = laps or []
        logger.info(f"Reference laps loaded: {len(self.ref_laps)} laps (not directly used)")
    
    def _on_initial_load_error(self, error_message):
        """Handle initial load error."""
        logger.error(f"Initial load error: {error_message}")
        self.loading_label.setText(f"❌ {error_message}")
        QTimer.singleShot(3000, lambda: self.loading_label.setVisible(False))
    
    def _update_left_lap_combo(self):
        """Populate Lap A (mine)."""
        self.controls.left_lap_combo.clear()
        if not self.my_laps:
            return
        for lap in self.my_laps:
            if lap.get('is_valid', True):
                lap_time = lap.get('lap_time', 0)
                formatted_time = self._format_lap_time(lap_time) if lap_time else 'No Time'
                lap_text = f"Lap {lap.get('lap_number', '?')} - {formatted_time}"
                self.controls.left_lap_combo.addItem(lap_text, lap.get('id'))
        self.controls.left_lap_combo.setCurrentIndex(0)

    def _update_right_lap_combo(self):
        """Removed: Reference lap is selected directly from the Reference Lap combo."""
        return
    
    def on_session_changed(self, index):
        """Handle session selection change."""
        if index < 0 or index >= len(self.my_sessions):
            return
            
        session = self.my_sessions[index]
        self.current_my_session_id = session.get('id')
        logger.info(f"My Session changed to: {session.get('track_name')} (ID: {self.current_my_session_id})")
        
        # Load laps for this session
        self._load_my_laps_for_session(self.current_my_session_id)
        
        # Load fastest reference laps for this session's track only
        track_id = session.get('track_id') or (session.get('tracks') or {}).get('id')
        if track_id:
            # Also pass car_id to ensure comparable laps
            car_id = session.get('car_id') or (session.get('cars') or {}).get('id')
            self._load_fastest_ref_laps_for_track_car(track_id, car_id)
    
    def _load_laps_for_session(self, session_id):
        """Legacy API - map to _load_my_laps_for_session."""
        return self._load_my_laps_for_session(session_id)

    def _load_my_laps_for_session(self, session_id):
        """Load laps for the selected MY session (Lap A)."""
        if not session_id:
            return
            
        try:
            from Supabase.database import get_laps
            logger.info(f"Loading MY laps for session: {session_id}")
            
            laps_result = get_laps(session_id=session_id)
            if laps_result[0] is not None:
                self.my_laps = laps_result[0]
                logger.info(f"Found {len(self.my_laps)} MY laps for session {session_id}")
                
                # Avoid heavy preloading on session change to keep UI responsive
            else:
                logger.warning(f"get_laps returned None for MY session {session_id}: {laps_result[1]}")
                self.my_laps = []
            self._update_left_lap_combo()
        except Exception as e:
            logger.error(f"Error loading laps: {e}")
            self.my_laps = []
            self._update_left_lap_combo()

    def on_ref_session_changed(self, index):
        """When Reference Lap selection changes, trigger comparison with Lap A."""
        self.on_lap_selection_changed()

    def _load_ref_laps_for_session(self, session_id):
        """Deprecated: using fastest lap list instead."""
        return

    def _load_fastest_ref_laps_for_track_car(self, track_id: str, car_id: str | None):
        """Load top-10 fastest laps globally for a track (optionally filter by car) and populate Ref Session combo."""
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            my_user_id = None
            try:
                user = main_supabase.get_user()
                if user:
                    if hasattr(user, 'id'):
                        my_user_id = user.id
                    elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                        my_user_id = user.user.id
                    elif isinstance(user, dict):
                        my_user_id = user.get('id') or (user.get('user') or {}).get('id')
            except Exception:
                pass
            from Supabase.database import get_fastest_laps
            result = get_fastest_laps(track_id, car_id, limit=10, exclude_user_id=my_user_id)
            fastest = result[0] or []
            # Ensure fastest-first (ascending lap_time)
            fastest.sort(key=lambda x: x.get('lap_time', 999999))
            self._on_ref_fastest_laps_loaded(fastest)
        except Exception as e:
            logger.error(f"Error loading fastest ref laps: {e}")
            self._on_ref_fastest_laps_loaded([])

    def _on_ref_fastest_laps_loaded(self, fastest_laps):
        """Populate Ref Session combo from fastest laps (username + lap time)."""
        # Filter out laps from users who do not share telemetry and enrich with names/avatars
        filtered = []
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            user_ids = sorted({lap.get('user_id') for lap in fastest_laps if lap.get('user_id')})
            share_map: dict[str, bool] = {}
            info_map: dict[str, dict] = {}
            if user_ids and main_supabase and getattr(main_supabase, 'client', None):
                try:
                    res = (
                        main_supabase.client
                        .table('user_profiles')
                        .select('user_id, username, display_name, avatar_url, privacy_settings')
                        .in_('user_id', user_ids)
                        .execute()
                    )
                    for row in (res.data or []):
                        ps = row.get('privacy_settings') or {}
                        uid = row.get('user_id')
                        share_map[uid] = bool(ps.get('share_telemetry', True))
                        info_map[uid] = {
                            'username': row.get('username'),
                            'display_name': row.get('display_name'),
                            'avatar_url': row.get('avatar_url'),
                        }
                except Exception:
                    # If lookup fails, default to visible and no extra info
                    share_map = {uid: True for uid in user_ids}
            # Apply filtering and enrich items
            for item in fastest_laps:
                uid = item.get('user_id')
                if uid is None or share_map.get(uid, True):
                    info = info_map.get(uid, {})
                    # Prefer display_name, then username
                    name = info.get('display_name') or item.get('display_name') or info.get('username') or item.get('username')
                    if name:
                        item['username'] = name
                    # Fill avatar_url if missing
                    if not item.get('avatar_url') and info.get('avatar_url'):
                        item['avatar_url'] = info.get('avatar_url')
                    filtered.append(item)
        except Exception:
            # On any error, fall back to unfiltered list
            filtered = list(fastest_laps or [])

        combo = self.controls.ref_session_combo
        combo.clear()
        # Determine current context (track/car) for labeling clarity
        context_track = None
        context_car = None
        try:
            current_session = None
            if self.my_sessions:
                # Use currently selected session if possible
                idx = self.controls.session_combo.currentIndex()
                if 0 <= idx < len(self.my_sessions):
                    current_session = self.my_sessions[idx]
                else:
                    current_session = self.my_sessions[0]
            if current_session:
                context_track = (current_session.get('tracks') or {}).get('name') or current_session.get('track_name')
                context_car = (current_session.get('cars') or {}).get('name') or current_session.get('car_name')
        except Exception:
            pass

        for item in filtered:
            # Prefer display_name for readability; fallback to username; finally 'Unknown'
            name = item.get('display_name') or item.get('username') or 'Unknown'
            lap_time = item.get('lap_time') or 0
            # Include context track/car when available
            if context_track or context_car:
                parts = []
                if context_track:
                    parts.append(context_track)
                if context_car:
                    parts.append(context_car)
                label = f"({name}) - {' / '.join(parts)} - {self._format_lap_time(lap_time)}"
            else:
                label = f"({name}) - {self._format_lap_time(lap_time)}"
            icon = self._make_avatar_icon(item.get('avatar_url'))
            if icon is not None:
                combo.addItem(icon, label, item.get('id'))
            else:
                combo.addItem(label, item.get('id'))

        # Auto-select the fastest (first item) if available and none selected yet
        try:
            if combo.count() > 0 and combo.currentIndex() < 0:
                combo.setCurrentIndex(0)
                self.on_ref_session_changed(0)
        except Exception:
            pass

    # --- Filtering helpers ---
    def _populate_filter_options(self, sessions: list[dict]):
        """Populate track and car filter combos from available sessions."""
        try:
            # Collect unique tracks and cars
            track_items = {}
            car_items = {}
            for sess in sessions or []:
                tid = sess.get('track_id') or (sess.get('tracks') or {}).get('id')
                tname = (sess.get('tracks') or {}).get('name') or sess.get('track_name') or 'Unknown Track'
                if tid and tname and tid not in track_items:
                    track_items[tid] = tname
                cid = sess.get('car_id') or (sess.get('cars') or {}).get('id')
                cname = (sess.get('cars') or {}).get('name') or sess.get('car_name') or 'Unknown Car'
                if cid and cname and cid not in car_items:
                    car_items[cid] = cname

            # Populate controls
            self.controls.track_filter_combo.blockSignals(True)
            self.controls.car_filter_combo.blockSignals(True)
            self.controls.track_filter_combo.clear()
            self.controls.car_filter_combo.clear()
            self.controls.track_filter_combo.addItem("All Tracks", None)
            for tid, tname in sorted(track_items.items(), key=lambda kv: kv[1].lower()):
                self.controls.track_filter_combo.addItem(tname, tid)
            self.controls.car_filter_combo.addItem("All Cars", None)
            for cid, cname in sorted(car_items.items(), key=lambda kv: kv[1].lower()):
                self.controls.car_filter_combo.addItem(cname, cid)
            self.controls.track_filter_combo.blockSignals(False)
            self.controls.car_filter_combo.blockSignals(False)

            # Connect change handlers once
            try:
                self.controls.track_filter_combo.currentIndexChanged.disconnect()
            except Exception:
                pass
            self.controls.track_filter_combo.currentIndexChanged.connect(self._apply_filters_and_update_sessions)
            try:
                self.controls.car_filter_combo.currentIndexChanged.disconnect()
            except Exception:
                pass
            self.controls.car_filter_combo.currentIndexChanged.connect(self._apply_filters_and_update_sessions)
        except Exception as e:
            logger.debug(f"Error populating filter options: {e}")

    def _apply_filters_and_update_sessions(self):
        """Apply track/car filters to all_my_sessions and update the session combo."""
        try:
            selected_track = self.controls.track_filter_combo.currentData() if hasattr(self.controls, 'track_filter_combo') else None
            selected_car = self.controls.car_filter_combo.currentData() if hasattr(self.controls, 'car_filter_combo') else None

            def matches(sess: dict) -> bool:
                tid = sess.get('track_id') or (sess.get('tracks') or {}).get('id')
                cid = sess.get('car_id') or (sess.get('cars') or {}).get('id')
                if selected_track and tid != selected_track:
                    return False
                if selected_car and cid != selected_car:
                    return False
                return True

            self.my_sessions = [s for s in (self.all_my_sessions or []) if matches(s)]

            # Update combo
            self.controls.session_combo.blockSignals(True)
            self.controls.session_combo.clear()
            for session in self.my_sessions:
                tname = (session.get('tracks') or {}).get('name') or session.get('track_name', 'Unknown Track')
                cname = (session.get('cars') or {}).get('name') or session.get('car_name', 'Unknown Car')
                date_text = session.get('session_date', 'Unknown Date')
                session_text = f"{tname} • {cname} - {date_text}"
                self.controls.session_combo.addItem(session_text, session.get('id'))
            self.controls.session_combo.blockSignals(False)

            # If no sessions after filtering, clear laps too
            if not self.my_sessions:
                self.my_laps = []
                self._update_left_lap_combo()
                return

            # Ensure reference laps refresh to match the new visible/current session
            try:
                idx = self.controls.session_combo.currentIndex()
                if idx < 0:
                    idx = 0
                if 0 <= idx < len(self.my_sessions):
                    sess = self.my_sessions[idx]
                    track_id = sess.get('track_id') or (sess.get('tracks') or {}).get('id')
                    car_id = sess.get('car_id') or (sess.get('cars') or {}).get('id')
                    if track_id:
                        self._load_fastest_ref_laps_for_track_car(track_id, car_id)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Error applying filters: {e}")

    def _make_avatar_icon(self, avatar_url: str):
        """Create a small circular QIcon from an avatar URL if available."""
        try:
            if not avatar_url:
                return None
            # Load image data (simple QPixmap load; assumes local file path or Qt-supported URL)
            pixmap = QPixmap()
            if avatar_url.startswith('http'):
                # Remote fetch not implemented here; return None to keep UI responsive
                return None
            loaded = pixmap.load(avatar_url)
            if not loaded:
                return None
            # Resize and round
            size = 24
            pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            # Create circular mask
            mask = QPixmap(size, size)
            mask.fill(Qt.GlobalColor.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(Qt.GlobalColor.white))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, size, size)
            painter.end()
            pixmap.setMask(mask.createMaskFromColor(Qt.GlobalColor.transparent))
            return QIcon(pixmap)
        except Exception:
            return None
    
    def _preload_session_telemetry(self, session_id: str, laps: list):
        """Preload telemetry for all laps in the session for instant switching."""
        try:
            from trackpro.race_coach.telemetry_cache import get_telemetry_cache
            
            # Extract lap IDs
            lap_ids = [lap.get('id') for lap in laps if lap.get('id') and lap.get('is_valid', True)]
            
            if lap_ids:
                cache = get_telemetry_cache()
                cache.preload_session_telemetry(session_id, lap_ids)
                logger.info(f"🚀 PRELOAD: Started background loading for {len(lap_ids)} laps")
        except Exception as e:
            logger.warning(f"Failed to start telemetry preloading: {e}")
    
    def on_lap_selection_changed(self):
        """Handle lap selection change for comparison."""
        left_lap_id = self.controls.left_lap_combo.currentData()
        right_lap_id = self.controls.ref_session_combo.currentData()
        
        if left_lap_id or right_lap_id:
            self._compare_laps(left_lap_id, right_lap_id)
    
    def _compare_laps(self, left_lap_id, right_lap_id):
        """Compare two laps by loading their telemetry data."""
        if not left_lap_id and not right_lap_id:
            return
            
        # Cancel any existing telemetry fetch
        threads_to_remove = []
        for thread_id, thread, worker in self.active_threads:
            if isinstance(worker, TelemetryFetchWorker):
                worker.cancel()
                if thread.isRunning():
                    thread.quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        logger.debug(f"Thread {thread_id} did not stop gracefully")
                        thread.terminate()
                        thread.wait(1000)
                threads_to_remove.append((thread_id, thread, worker))
        
        # Remove stopped threads from tracking
        for thread_info in threads_to_remove:
            if thread_info in self.active_threads:
                self.active_threads.remove(thread_info)
        
        # Start new telemetry fetch
        thread_id = str(uuid.uuid4())
        thread = QThread()
        worker = TelemetryFetchWorker(left_lap_id, right_lap_id)
        worker.moveToThread(thread)
        
        # Connect signals with Qt.QueuedConnection to prevent race conditions
        worker.telemetry_loaded.connect(self._on_telemetry_loaded, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(lambda: self._safe_thread_cleanup(thread_id), Qt.ConnectionType.QueuedConnection)
        # Ensure graceful shutdown and deletion
        try:
            worker.finished.connect(thread.quit, Qt.ConnectionType.QueuedConnection)
            worker.finished.connect(worker.deleteLater, Qt.ConnectionType.QueuedConnection)
            thread.finished.connect(thread.deleteLater, Qt.ConnectionType.QueuedConnection)
        except Exception:
            pass
        thread.started.connect(worker.run, Qt.ConnectionType.QueuedConnection)
        
        # Track thread
        self.active_threads.append((thread_id, thread, worker))
        
        # Start thread
        thread.start()
        
        logger.info(f"Started telemetry comparison for laps {left_lap_id} vs {right_lap_id}")
    
    def _on_telemetry_loaded(self, left_data, right_data, left_error, right_error):
        """Handle telemetry data loaded for comparison."""
        logger.info(f"Telemetry loaded - Left: {left_data is not None}, Right: {right_data is not None}")
        
        if left_error or right_error:
            self._on_telemetry_error(left_error, right_error)
            return
        
        # Get track length for proper scaling
        track_length = self.get_track_length()
        if not track_length:
            track_length = self._estimate_track_length_from_telemetry(left_data, right_data)
        
        if not track_length:
            track_length = 5000  # Default fallback
        
        logger.info(f"Using track length: {track_length}m for telemetry display")
        
        # Update all graphs with the telemetry data
        self._update_graphs_with_telemetry(left_data, right_data, track_length)
    
    def _update_graphs_with_telemetry(self, left_data, right_data, track_length):
        """Update all telemetry graphs with the loaded data."""
        try:
            # Map and normalize the data for graph widgets
            if left_data and left_data.get('points'):
                mapped_points = []
                for point in left_data['points']:
                    mapped_point = point.copy()
                    
                    # Convert track_position to LapDist
                    if 'track_position' in mapped_point:
                        track_pos = mapped_point['track_position']
                        if 0 <= track_pos <= 1:
                            mapped_point['LapDist'] = track_pos * track_length
                        else:
                            mapped_point['LapDist'] = track_pos
                    
                    # Map field names to what graphs expect
                    if 'throttle' in mapped_point:
                        mapped_point['Throttle'] = mapped_point['throttle']
                    if 'brake' in mapped_point:
                        mapped_point['Brake'] = mapped_point['brake']
                    if 'steering' in mapped_point:
                        mapped_point['Steering'] = max(-1.0, min(1.0, mapped_point['steering']))
                    if 'speed' in mapped_point:
                        mapped_point['Speed'] = mapped_point['speed']
                    if 'gear' in mapped_point:
                        mapped_point['Gear'] = mapped_point['gear']
                    if 'rpm' in mapped_point:
                        mapped_point['RPM'] = mapped_point['rpm']
                    
                    # Set defaults
                    mapped_point.setdefault('Throttle', 0)
                    mapped_point.setdefault('Brake', 0)
                    mapped_point.setdefault('Steering', 0)
                    mapped_point.setdefault('Speed', 0)
                    mapped_point.setdefault('Gear', 0)
                    mapped_point.setdefault('LapDist', 0)
                    
                    mapped_points.append(mapped_point)
                
                left_data = {'points': mapped_points}
            
            # Same mapping for right data
            if right_data and right_data.get('points'):
                mapped_points = []
                for point in right_data['points']:
                    mapped_point = point.copy()
                    
                    if 'track_position' in mapped_point:
                        track_pos = mapped_point['track_position']
                        if 0 <= track_pos <= 1:
                            mapped_point['LapDist'] = track_pos * track_length
                        else:
                            mapped_point['LapDist'] = track_pos
                    
                    # Map field names
                    if 'throttle' in mapped_point:
                        mapped_point['Throttle'] = mapped_point['throttle']
                    if 'brake' in mapped_point:
                        mapped_point['Brake'] = mapped_point['brake']
                    if 'steering' in mapped_point:
                        mapped_point['Steering'] = max(-1.0, min(1.0, mapped_point['steering']))
                    if 'speed' in mapped_point:
                        mapped_point['Speed'] = mapped_point['speed']
                    if 'gear' in mapped_point:
                        mapped_point['Gear'] = mapped_point['gear']
                    if 'rpm' in mapped_point:
                        mapped_point['RPM'] = mapped_point['rpm']
                    
                    # Set defaults
                    mapped_point.setdefault('Throttle', 0)
                    mapped_point.setdefault('Brake', 0)
                    mapped_point.setdefault('Steering', 0)
                    mapped_point.setdefault('Speed', 0)
                    mapped_point.setdefault('Gear', 0)
                    mapped_point.setdefault('LapDist', 0)
                    
                    mapped_points.append(mapped_point)
                
                right_data = {'points': mapped_points}
            
            # Update graphs
            if left_data and right_data:
                # Comparison mode
                if hasattr(self, 'throttle_graph'):
                    self.throttle_graph.update_graph_comparison(left_data, right_data, track_length)
                if hasattr(self, 'brake_graph'):
                    self.brake_graph.update_graph_comparison(left_data, right_data, track_length)
                if hasattr(self, 'steering_graph'):
                    self.steering_graph.update_graph_comparison(left_data, right_data, track_length)
                if hasattr(self, 'speed_graph'):
                    self.speed_graph.update_graph_comparison(left_data, right_data, track_length)
                if hasattr(self, 'gear_graph'):
                    self.gear_graph.update_graph_comparison(left_data, right_data, track_length)
                    
                logger.info("✅ Updated all graphs in comparison mode")
                
                # Update legend for comparison mode
                if hasattr(self, 'telemetry_legend') and hasattr(self.telemetry_legend, 'set_comparison_mode'):
                    self.telemetry_legend.set_comparison_mode(True)
                
            elif left_data:
                # Single lap mode
                if hasattr(self, 'throttle_graph'):
                    self.throttle_graph.update_graph(left_data, track_length)
                if hasattr(self, 'brake_graph'):
                    self.brake_graph.update_graph(left_data, track_length)
                if hasattr(self, 'steering_graph'):
                    self.steering_graph.update_graph(left_data, track_length)
                if hasattr(self, 'speed_graph'):
                    self.speed_graph.update_graph(left_data, track_length)
                if hasattr(self, 'gear_graph'):
                    self.gear_graph.update_graph(left_data, track_length)
                    
                logger.info("✅ Updated all graphs in single lap mode")
                
                # Update legend for single lap mode
                if hasattr(self, 'telemetry_legend') and hasattr(self.telemetry_legend, 'set_comparison_mode'):
                    self.telemetry_legend.set_comparison_mode(False)
                
        except Exception as e:
            logger.error(f"Error updating graphs with telemetry: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_telemetry_error(self, left_error, right_error):
        """Handle telemetry loading errors."""
        error_parts = []
        if left_error:
            error_parts.append(f"Left lap: {left_error}")
        if right_error:
            error_parts.append(f"Right lap: {right_error}")
        
        error_text = "Error loading telemetry: " + " | ".join(error_parts)
        logger.error(error_text)
        try:
            self.debug_label.setText((self.debug_label.text() or "Debug:") + " | " + error_text)
        except Exception:
            pass
        
        # Clear the graphs on error
        self._clear_all_graphs()
    
    def _clear_all_graphs(self):
        """Clear all telemetry graphs."""
        graph_widgets = ['throttle_graph', 'brake_graph', 'steering_graph', 'speed_graph', 'gear_graph']
        
        for widget_name in graph_widgets:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if hasattr(widget, 'plot_widget'):
                    try:
                        for item in widget.plot_widget.listDataItems():
                            item.setData([], [])
                    except Exception as e:
                        logger.error(f"Error clearing {widget_name}: {e}")
    
    def get_track_length(self):
        """Get track length from current session."""
        if self.current_my_session_id and self.my_sessions:
            for session in self.my_sessions:
                if session.get('id') == self.current_my_session_id:
                    return session.get('track_length', None)
        return None
    
    def _estimate_track_length_from_telemetry(self, left_data, right_data):
        """Estimate track length from telemetry data."""
        try:
            all_positions = []
            
            for data in [left_data, right_data]:
                if data and data.get('points'):
                    positions = [p.get('track_position', 0) for p in data['points'] if p.get('track_position') is not None]
                    all_positions.extend(positions)
            
            if not all_positions:
                return None
                
            min_pos = min(all_positions)
            max_pos = max(all_positions)
            position_range = max_pos - min_pos
            
            # Estimate based on position range
            if 0 <= min_pos <= 1 and 0 <= max_pos <= 1:
                if position_range < 0.01:
                    return 10000  # 10km for large tracks
                elif position_range < 0.1:
                    return 6000   # 6km for typical road courses
                else:
                    return 3000   # 3km for shorter tracks
            else:
                return max_pos if max_pos > 100 else None
                
        except Exception as e:
            logger.error(f"Error estimating track length: {e}")
            return None
    
    def refresh_session_and_lap_lists(self):
        """Refresh both session and lap lists."""
        self._start_initial_data_loading()
    
    def _remove_thread_from_tracking(self, thread_id):
        """Remove a thread from the active threads list."""
        self.active_threads = [(tid, t, w) for tid, t, w in self.active_threads if tid != thread_id]
    
    def _format_lap_time(self, lap_time_seconds):
        """Format lap time in MM:SS.mmm format."""
        if lap_time_seconds <= 0:
            return "--:--.---"
        
        minutes = int(lap_time_seconds // 60)
        seconds = lap_time_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    
    def _safe_thread_cleanup(self, thread_id):
        """Safely clean up a completed thread to prevent crashes."""
        try:
            # Find the thread
            thread_to_cleanup = None
            for tid, thread, worker in self.active_threads:
                if tid == thread_id:
                    thread_to_cleanup = (tid, thread, worker)
                    break
            
            if not thread_to_cleanup:
                logger.debug(f"Thread {thread_id} already cleaned up")
                return
            
            tid, thread, worker = thread_to_cleanup
            logger.info(f"🧹 Safe cleanup for thread {thread_id}")
            
            # Then quit the thread gracefully
            if thread.isRunning():
                thread.quit()
                # Give it time to quit gracefully - but keep it fast
                if not thread.wait(500):  # 0.5 second timeout for faster UI
                    logger.debug(f"Thread {thread_id} taking longer to quit, terminating...")
                    thread.terminate()
                    thread.wait(200)  # Quick termination wait
            
            # Remove from tracking
            self._remove_thread_from_tracking(thread_id)
            logger.info(f"✅ Thread {thread_id} cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error in safe thread cleanup for {thread_id}: {e}")
            # Still try to remove from tracking even if cleanup failed
            self._remove_thread_from_tracking(thread_id)
    
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self.cleanup()
        except Exception as e:
            logger.debug(f"Error in telemetry page destructor: {e}")
    
    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None
    
    def lazy_init(self):
        """Lazy initialization when page is first accessed."""
        logger.info("📊 Lazy initializing Telemetry page with full Supabase integration...")
        # Don't start data loading here - wait for explicit page activation
    
    def on_auth_state_changed(self, authenticated: bool | None = None):
        """React to global auth changes by refreshing sessions/laps when logged in."""
        try:
            logger.info(f"🔄 TelemetryPage auth state changed: {authenticated}")
            # If authenticated, refresh sessions and laps immediately
            if authenticated is True:
                self.refresh_session_and_lap_lists()
        except Exception as e:
            logger.error(f"Error handling TelemetryPage auth change: {e}")

    def on_page_activated(self):
        """Called when page becomes active."""
        super().on_page_activated()
        if not self._initial_lap_load_done:
            # Start data loading when page is actually accessed
            QTimer.singleShot(100, self._start_initial_data_loading)
    
    def cleanup(self):
        """Clean up any running threads when the widget is destroyed."""
        self._is_being_destroyed = True
        logger.info("🧹 Starting telemetry page cleanup...")
        
        # Cancel all running workers
        for thread_id, thread, worker in self.active_threads:
            try:
                logger.info(f"Cancelling worker: {worker.__class__.__name__}")
                if hasattr(worker, 'cancel'):
                    worker.cancel()
                
                if thread.isRunning():
                    logger.info(f"Stopping thread: {thread_id}")
                    thread.quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        logger.debug(f"Thread {thread_id} did not stop gracefully, terminating...")
                        thread.terminate()
                        thread.wait(1000)  # Wait for termination
                else:
                    logger.info(f"Thread {thread_id} already stopped")
            except Exception as e:
                logger.error(f"Error cleaning up thread {thread_id}: {e}")
        
        self.active_threads.clear()
        logger.info("🧹 Telemetry page cleanup completed")
        
    def _update_hover_info(self, distance, lap_a_data, lap_b_data):
        """Update the centralized hover info widget with data from ALL graphs at the given distance."""
        if hasattr(self, 'hover_info_widget'):
            try:
                # Get data from ALL graphs at this distance point
                all_lap_a_data = {}
                all_lap_b_data = {}
                
                # Query each graph for data at this distance
                if hasattr(self, 'throttle_graph') and self.throttle_graph.throttle_curve.xData is not None:
                    throttle_data = self._get_graph_data_at_distance(self.throttle_graph, distance, 'throttle')
                    all_lap_a_data.update(throttle_data[0])
                    all_lap_b_data.update(throttle_data[1])
                
                if hasattr(self, 'brake_graph') and self.brake_graph.brake_curve.xData is not None:
                    brake_data = self._get_graph_data_at_distance(self.brake_graph, distance, 'brake')
                    all_lap_a_data.update(brake_data[0])
                    all_lap_b_data.update(brake_data[1])
                
                if hasattr(self, 'speed_graph') and self.speed_graph.speed_curve.xData is not None:
                    speed_data = self._get_graph_data_at_distance(self.speed_graph, distance, 'speed')
                    all_lap_a_data.update(speed_data[0])
                    all_lap_b_data.update(speed_data[1])
                
                if hasattr(self, 'gear_graph') and self.gear_graph.gear_curve.xData is not None:
                    gear_data = self._get_graph_data_at_distance(self.gear_graph, distance, 'gear')
                    all_lap_a_data.update(gear_data[0])
                    all_lap_b_data.update(gear_data[1])
                
                if hasattr(self, 'steering_graph') and self.steering_graph.steering_curve.xData is not None:
                    steering_data = self._get_graph_data_at_distance(self.steering_graph, distance, 'steering')
                    all_lap_a_data.update(steering_data[0])
                    all_lap_b_data.update(steering_data[1])
                
                # Update the widget with ALL telemetry data
                self.hover_info_widget.update_distance(distance)
                self.hover_info_widget.update_lap_data(all_lap_a_data, all_lap_b_data)
                
                # Set comparison mode if we have lap B data
                has_lap_b = bool(all_lap_b_data)
                self.hover_info_widget.set_comparison_mode(has_lap_b)
                
            except Exception as e:
                logger.debug(f"Error updating hover info: {e}")
                
    def _get_graph_data_at_distance(self, graph, distance, data_type):
        """Get data from a specific graph at the given distance."""
        lap_a_data = {}
        lap_b_data = {}
        
        try:
            # Get data from Lap A curve
            if hasattr(graph, f'{data_type}_curve') and getattr(graph, f'{data_type}_curve').xData is not None:
                curve_a = getattr(graph, f'{data_type}_curve')
                if len(curve_a.xData) > 0:
                    # Find closest point to the distance
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(curve_a.xData):
                        dist = abs(x_val - distance)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0 and closest_idx < len(curve_a.yData):
                        value = curve_a.yData[closest_idx]
                        
                        # Format the value based on data type
                        if data_type == 'throttle' or data_type == 'brake':
                            lap_a_data[data_type] = f"{value * 100:.0f}%"
                        elif data_type == 'speed':
                            lap_a_data[data_type] = f"{value:.1f} km/h"
                        elif data_type == 'gear':
                            # Format gear value
                            if value < 0:
                                lap_a_data[data_type] = "R"
                            elif value == 0:
                                lap_a_data[data_type] = "N"
                            else:
                                lap_a_data[data_type] = str(int(value))
                        elif data_type == 'steering':
                            direction = "Right" if value > 0 else "Left"
                            if abs(value) < 1.0:
                                direction = "Center"
                            lap_a_data[data_type] = f"{direction} {abs(value * 100):.0f}%"
            
            # Get data from Lap B curve (comparison mode)
            if hasattr(graph, f'{data_type}_curve_b') and getattr(graph, f'{data_type}_curve_b').xData is not None:
                curve_b = getattr(graph, f'{data_type}_curve_b')
                if len(curve_b.xData) > 0:
                    # Find closest point to the distance
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(curve_b.xData):
                        dist = abs(x_val - distance)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0 and closest_idx < len(curve_b.yData):
                        value = curve_b.yData[closest_idx]
                        
                        # Format the value based on data type
                        if data_type == 'throttle' or data_type == 'brake':
                            lap_b_data[data_type] = f"{value * 100:.0f}%"
                        elif data_type == 'speed':
                            lap_b_data[data_type] = f"{value:.1f} km/h"
                        elif data_type == 'gear':
                            # Format gear value
                            if value < 0:
                                lap_b_data[data_type] = "R"
                            elif value == 0:
                                lap_b_data[data_type] = "N"
                            else:
                                lap_b_data[data_type] = str(int(value))
                        elif data_type == 'steering':
                            direction = "Right" if value > 0 else "Left"
                            if abs(value) < 1.0:
                                direction = "Center"
                            lap_b_data[data_type] = f"{direction} {abs(value * 100):.0f}%"
                            
        except Exception as e:
            logger.debug(f"Error getting {data_type} data at distance {distance}: {e}")
        
        return lap_a_data, lap_b_data

    # --- Reference helpers ---
    def _populate_ref_session_combo(self):
        """Populate the reference session combo with community sessions."""
        try:
            self.controls.ref_session_combo.clear()
        except Exception:
            return
        for session in (self.community_sessions or []):
            session_text = f"{session.get('track_name', 'Unknown Track')} - {session.get('session_date', 'Unknown Date')}"
            self.controls.ref_session_combo.addItem(session_text, session.get('id'))

    def _auto_select_matching_ref_session(self, my_session):
        """Auto-select a reference session that matches my session's track/car if available."""
        try:
            if not my_session or not self.community_sessions:
                return
            target_track = my_session.get('tracks', {}).get('name') if my_session.get('tracks') else my_session.get('track_name')
            target_car = my_session.get('cars', {}).get('name') if my_session.get('cars') else my_session.get('car_name')
            best_index = -1
            for idx, sess in enumerate(self.community_sessions):
                track = sess.get('tracks', {}).get('name') if sess.get('tracks') else sess.get('track_name')
                car = sess.get('cars', {}).get('name') if sess.get('cars') else sess.get('car_name')
                if track == target_track and car == target_car:
                    best_index = idx
                    break
            if best_index >= 0:
                self.controls.ref_session_combo.setCurrentIndex(best_index)
                self.on_ref_session_changed(best_index)
        except Exception:
            pass