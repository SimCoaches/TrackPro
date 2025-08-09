import logging
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QComboBox, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QProgressBar, QSizePolicy
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
                self.telemetry_loaded.emit(left_data, right_data, left_error, right_error)
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
        
        # Reference session (Others)
        ref_session_label = QLabel("Ref Session:")
        self.ref_session_combo = QComboBox()
        self.ref_session_combo.setMinimumWidth(300)
        self.ref_session_combo.setMaximumWidth(400)
        self.ref_session_combo.currentIndexChanged.connect(self.ref_session_changed.emit)

        lap_b_label = QLabel("Lap B:")
        self.right_lap_combo = QComboBox()
        self.right_lap_combo.setMinimumWidth(120)
        self.right_lap_combo.setMaximumWidth(150)
        self.right_lap_combo.currentIndexChanged.connect(self.lap_selection_changed.emit)
        
        layout.addWidget(lap_a_label)
        layout.addWidget(self.left_lap_combo)
        layout.addWidget(vs_label)
        layout.addWidget(ref_session_label)
        layout.addWidget(self.ref_session_combo)
        layout.addWidget(lap_b_label)
        layout.addWidget(self.right_lap_combo)
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
        self.my_sessions = []
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
            
            # Load my sessions
            try:
                sessions_result = get_sessions(user_only=True, only_with_laps=True)
                if sessions_result[0] is not None:
                    sessions = sessions_result[0]
                    self._on_sessions_loaded(sessions, "Sessions loaded successfully")
                    logger.info(f"Loaded {len(sessions)} MY sessions from database")
                else:
                    sessions = []
                    self._on_sessions_loaded(sessions, "No sessions found")
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self._on_initial_load_error(f"Error loading sessions: {str(e)}")
                sessions = []
            
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
                            
                            # Start preloading telemetry for initial session
                            self._preload_session_telemetry(session_id, laps)
                        else:
                            self._on_my_laps_loaded(recent_session, [])
                except Exception as e:
                    logger.error(f"Error loading laps: {e}")
                    self._on_my_laps_loaded(recent_session, [])

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
        self.my_sessions = sessions or []
        logger.info(f"My sessions loaded: {len(self.my_sessions)} sessions")

        # Update 'My Session' combo
        self.controls.session_combo.clear()
        for session in self.my_sessions:
            session_text = f"{session.get('track_name', 'Unknown Track')} - {session.get('session_date', 'Unknown Date')}"
            self.controls.session_combo.addItem(session_text, session.get('id'))

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
        """Handle reference sessions (Lap B). Now replaced by fastest laps listing based on track/car."""
        # When my sessions are loaded, use the first session's track/car to load fastest laps
        try:
            target_session = self.my_sessions[0] if self.my_sessions else None
            if not target_session:
                self._on_ref_fastest_laps_loaded([])
                return
            track_id = target_session.get('track_id') or (target_session.get('tracks') or {}).get('id')
            car_id = target_session.get('car_id') or (target_session.get('cars') or {}).get('id')
            if track_id and car_id:
                self._load_fastest_ref_laps_for_track_car(track_id, car_id)
            else:
                self._on_ref_fastest_laps_loaded([])
        except Exception as e:
            logger.error(f"Error computing fastest laps request: {e}")
            self._on_ref_fastest_laps_loaded([])

    def _on_ref_laps_loaded(self, laps):
        """Handle reference laps (Lap B)."""
        self.ref_laps = laps or []
        logger.info(f"Reference laps loaded: {len(self.ref_laps)} laps")
        self._update_right_lap_combo()
    
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
        """Populate Lap B (reference)."""
        self.controls.right_lap_combo.clear()
        if not self.ref_laps:
            return
        for lap in self.ref_laps:
            if lap.get('is_valid', True):
                lap_time = lap.get('lap_time', 0)
                formatted_time = self._format_lap_time(lap_time) if lap_time else 'No Time'
                lap_text = f"Lap {lap.get('lap_number', '?')} - {formatted_time}"
                self.controls.right_lap_combo.addItem(lap_text, lap.get('id'))
        self.controls.right_lap_combo.setCurrentIndex(0)
    
    def on_session_changed(self, index):
        """Handle session selection change."""
        if index < 0 or index >= len(self.my_sessions):
            return
            
        session = self.my_sessions[index]
        self.current_my_session_id = session.get('id')
        logger.info(f"My Session changed to: {session.get('track_name')} (ID: {self.current_my_session_id})")
        
        # Load laps for this session
        self._load_my_laps_for_session(self.current_my_session_id)
        
        # Load fastest reference laps for this session's track/car
        track_id = session.get('track_id') or (session.get('tracks') or {}).get('id')
        car_id = session.get('car_id') or (session.get('cars') or {}).get('id')
        if track_id and car_id:
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
                
                # Start preloading telemetry for all laps in background
                self._preload_session_telemetry(session_id, self.my_laps)
            else:
                logger.warning(f"get_laps returned None for MY session {session_id}: {laps_result[1]}")
                self.my_laps = []
            self._update_left_lap_combo()
        except Exception as e:
            logger.error(f"Error loading laps: {e}")
            self.my_laps = []
            self._update_left_lap_combo()

    def on_ref_session_changed(self, index):
        """When fastest lap selection changes, set Lap B to that lap directly."""
        lap_id = self.controls.ref_session_combo.currentData()
        if not lap_id:
            return
        # Mirror selection to Lap B combo with the same label
        label = self.controls.ref_session_combo.currentText()
        self.controls.right_lap_combo.clear()
        self.controls.right_lap_combo.addItem(label, lap_id)
        # Trigger compare
        self.on_lap_selection_changed()

    def _load_ref_laps_for_session(self, session_id):
        """Deprecated: using fastest lap list instead."""
        return

    def _load_fastest_ref_laps_for_track_car(self, track_id: str, car_id: str):
        """Load top-10 fastest laps globally for track/car and populate Ref Session combo."""
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
        combo = self.controls.ref_session_combo
        combo.clear()
        for item in fastest_laps:
            username = item.get('username', 'Unknown')
            lap_time = item.get('lap_time') or 0
            label = f"{username} – {self._format_lap_time(lap_time)}"
            icon = self._make_avatar_icon(item.get('avatar_url'))
            if icon is not None:
                combo.addItem(icon, label, item.get('id'))
            else:
                combo.addItem(label, item.get('id'))

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
        right_lap_id = self.controls.right_lap_combo.currentData()
        
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
                # Disconnect signals to prevent crashes during shutdown
                try:
                    worker.disconnect()
                    thread.disconnect()
                except Exception:
                    pass
                
                if thread.isRunning():
                    thread.quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        logger.warning(f"Thread {thread_id} did not stop gracefully")
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
            
            # First disconnect all signals to prevent any more events
            try:
                worker.disconnect()
                thread.disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting signals during cleanup: {e}")
            
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
                
                # Disconnect all signals to prevent race conditions during shutdown
                try:
                    worker.disconnect()
                    thread.disconnect()
                except Exception as disconnect_error:
                    logger.debug(f"Error disconnecting signals for {thread_id}: {disconnect_error}")
                
                if thread.isRunning():
                    logger.info(f"Stopping thread: {thread_id}")
                    thread.quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        logger.warning(f"Thread {thread_id} did not stop gracefully, terminating...")
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