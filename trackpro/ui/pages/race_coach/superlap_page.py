import logging
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QScrollArea, QProgressBar,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QPainter, QPen, QBrush, QColor
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class SuperLapTelemetryWorker(QObject):
    """Worker to load telemetry data for SuperLap comparison."""
    
    telemetry_loaded = pyqtSignal(dict, dict, str, str)  # (user_data, super_data, user_error, super_error)
    finished = pyqtSignal()
    
    def __init__(self, user_lap_id, super_lap_id):
        super().__init__()
        self.user_lap_id = user_lap_id
        self.super_lap_id = super_lap_id
        self.is_cancelled = False
        
    def run(self):
        """Fetch telemetry data for both user lap and super lap."""
        user_result = None
        super_lap_result = None
        user_error = ""
        super_error = ""
        
        try:
            from Supabase.database import get_telemetry_points, get_super_lap_telemetry_points
            
            # Fetch user lap data
            if self.user_lap_id and not self.is_cancelled:
                try:
                    user_result_tuple = get_telemetry_points(self.user_lap_id)
                    if user_result_tuple[0] is not None:
                        user_result = {'points': user_result_tuple[0]}
                        logger.info(f"Loaded {len(user_result_tuple[0])} user telemetry points")
                    else:
                        user_error = user_result_tuple[1] or "No user telemetry data found"
                except Exception as e:
                    user_error = f"Error loading user lap: {str(e)}"
            
            # Fetch super lap data
            if self.super_lap_id and not self.is_cancelled:
                try:
                    super_result_tuple = get_super_lap_telemetry_points(self.super_lap_id)
                    if super_result_tuple[0] is not None:
                        super_lap_result = {'points': super_result_tuple[0]}
                        logger.info(f"Loaded {len(super_result_tuple[0])} SuperLap telemetry points")
                    else:
                        super_error = super_result_tuple[1] or "No SuperLap telemetry data found"
                except Exception as e:
                    super_error = f"Error loading SuperLap: {str(e)}"
                    
        except Exception as e:
            logger.error(f"Critical error in SuperLap telemetry worker: {e}")
            user_error = f"Critical error: {str(e)}"
            super_error = f"Critical error: {str(e)}"
        
        if not self.is_cancelled:
            self.telemetry_loaded.emit(user_result, super_lap_result, user_error, super_error)
        
        self.finished.emit()
    
    def cancel(self):
        self.is_cancelled = True

class SuperLapPage(BasePage):
    """Full-featured SuperLap analysis page with AI-powered lap comparison."""
    
    def __init__(self, global_managers=None):
        super().__init__("Race Coach SuperLap", global_managers)
        
        # Initialize data
        self.sessions = []
        self.user_laps = []
        self.ml_laps = []
        self.current_session_id = None
        self.current_user_lap = None
        self.current_ml_lap = None
        
        # Track active threads
        self.active_threads = []
        self._is_being_destroyed = False
        
    def init_page(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Controls
        self.create_controls(layout)
        
        # Comparison widget
        self.create_comparison_widget(layout)
        
        # Create graphs container
        self.create_graphs_container(layout)
        
        # Don't start initial data loading immediately - wait for page activation
        # QTimer.singleShot(100, self.load_initial_data)
    
    def create_controls(self, layout):
        """Create SuperLap controls."""
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #111;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        
        # Session selection
        session_label = QLabel("Session:")
        session_label.setStyleSheet("color: #DDD; font-weight: bold;")
        controls_layout.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-width: 200px;
            }
            QComboBox:hover { border-color: #FF4500; }
        """)
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)
        controls_layout.addWidget(self.session_combo)
        
        controls_layout.addStretch()
        
        # User lap selection
        user_lap_label = QLabel("Your Lap:")
        user_lap_label.setStyleSheet("color: #DDD; font-weight: bold;")
        controls_layout.addWidget(user_lap_label)
        
        self.user_lap_combo = QComboBox()
        self.user_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-width: 150px;
            }
        """)
        controls_layout.addWidget(self.user_lap_combo)
        
        # SuperLap selection
        vs_label = QLabel("vs SuperLap:")
        vs_label.setStyleSheet("color: #DDD; font-weight: bold;")
        controls_layout.addWidget(vs_label)
        
        self.ml_lap_combo = QComboBox()
        self.ml_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-width: 150px;
            }
        """)
        controls_layout.addWidget(self.ml_lap_combo)
        
        # Analyze button
        self.analyze_btn = QPushButton("🚀 ANALYZE SUPERLAP")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF4500;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FF6600; }
        """)
        self.analyze_btn.clicked.connect(self.analyze_performance)
        controls_layout.addWidget(self.analyze_btn)
        
        layout.addWidget(controls_frame)
    
    def create_comparison_widget(self, layout):
        """Create lap comparison display."""
        comparison_frame = QFrame()
        comparison_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF4500, stop:0.3 #FF6600, stop:0.7 #FF8800, stop:1 #FF4500);
                border-radius: 6px;
                padding: 15px;
            }
        """)
        comparison_layout = QVBoxLayout(comparison_frame)
        
        title = QLabel("🏁 SUPERLAP COMPARISON")
        title.setStyleSheet("""
            color: #FF4500;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        comparison_layout.addWidget(title)
        
        times_layout = QHBoxLayout()
        
        # User lap time
        user_col = QVBoxLayout()
        user_header = QLabel("👤 YOUR LAP")
        user_header.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 14px;")
        user_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_col.addWidget(user_header)
        
        self.user_time_label = QLabel("Select a lap")
        self.user_time_label.setStyleSheet("color: #00d4ff; font-size: 20px; font-weight: bold;")
        self.user_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_col.addWidget(self.user_time_label)
        
        times_layout.addLayout(user_col)
        
        # VS label
        vs_label = QLabel("VS")
        vs_label.setStyleSheet("color: #888; font-size: 16px; font-weight: bold;")
        vs_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        times_layout.addWidget(vs_label)
        
        # SuperLap time
        ai_col = QVBoxLayout()
        ai_header = QLabel("🤖 AI SUPERLAP")
        ai_header.setStyleSheet("color: #FF4500; font-weight: bold; font-size: 14px;")
        ai_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ai_col.addWidget(ai_header)
        
        self.ai_time_label = QLabel("Select a SuperLap")
        self.ai_time_label.setStyleSheet("color: #FF4500; font-size: 20px; font-weight: bold;")
        self.ai_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ai_col.addWidget(self.ai_time_label)
        
        times_layout.addLayout(ai_col)
        
        comparison_layout.addLayout(times_layout)
        
        # Delta display
        self.delta_label = QLabel("⏱️ DELTA: Select laps to compare")
        self.delta_label.setStyleSheet("""
            color: #888;
            font-size: 16px;
            font-weight: bold;
            border: 1px solid #888;
            border-radius: 4px;
            padding: 8px;
            text-align: center;
        """)
        self.delta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        comparison_layout.addWidget(self.delta_label)
        
        layout.addWidget(comparison_frame)
    
    def create_graphs_container(self, layout):
        """Create telemetry graphs container for SuperLap comparison."""
        graphs_scroll = QScrollArea()
        graphs_scroll.setWidgetResizable(True)
        graphs_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 4px;
            }
        """)
        
        graphs_container = QFrame()
        graphs_layout = QVBoxLayout(graphs_container)
        graphs_layout.setContentsMargins(5, 5, 5, 5)
        graphs_layout.setSpacing(5)
        
        # Import and create telemetry graph widgets
        try:
            from trackpro.race_coach.widgets.throttle_graph import ThrottleGraphWidget
            from trackpro.race_coach.widgets.brake_graph import BrakeGraphWidget
            from trackpro.race_coach.widgets.steering_graph import SteeringGraphWidget
            from trackpro.race_coach.widgets.speed_graph import SpeedGraphWidget
            from trackpro.race_coach.widgets.gear_graph import GearGraphWidget
            
            # Create telemetry graphs for SuperLap comparison
            self.throttle_graph = ThrottleGraphWidget()
            self.throttle_graph.setFixedHeight(120)
            graphs_layout.addWidget(self.throttle_graph)
            
            self.brake_graph = BrakeGraphWidget()
            self.brake_graph.setFixedHeight(120)
            graphs_layout.addWidget(self.brake_graph)
            
            self.steering_graph = SteeringGraphWidget()
            self.steering_graph.setFixedHeight(120)
            graphs_layout.addWidget(self.steering_graph)
            
            self.speed_graph = SpeedGraphWidget()
            self.speed_graph.setFixedHeight(120)
            graphs_layout.addWidget(self.speed_graph)
            
            self.gear_graph = GearGraphWidget()
            self.gear_graph.setFixedHeight(120)
            graphs_layout.addWidget(self.gear_graph)
            
            logger.info("✅ Created SuperLap telemetry graph widgets")
            
        except Exception as e:
            logger.error(f"Failed to create SuperLap graph widgets: {e}")
            placeholder = QLabel("SuperLap telemetry graphs will appear here after analysis")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #888; font-size: 14px; padding: 50px;")
            graphs_layout.addWidget(placeholder)
        
        graphs_layout.addStretch()
        graphs_scroll.setWidget(graphs_container)
        layout.addWidget(graphs_scroll)
    
    def load_initial_data(self):
        """Load initial sessions and setup combos."""
        if getattr(self, '_is_being_destroyed', False):
            return
        try:
            from Supabase.database import get_sessions
            
            # Load sessions
            sessions_result = get_sessions(user_only=True)
            if sessions_result[0] is not None:
                self.sessions = sessions_result[0]
                
                # Update session combo
                self.session_combo.clear()
                for session in self.sessions:
                    session_text = f"{session.get('track_name', 'Unknown')} - {session.get('session_date', 'Unknown')}"
                    self.session_combo.addItem(session_text, session.get('id'))
                
                if self.sessions:
                    self.session_combo.setCurrentIndex(0)
                    
            logger.info(f"SuperLap: Loaded {len(self.sessions)} sessions")
            
        except Exception as e:
            logger.error(f"Error loading SuperLap initial data: {e}")
    
    def on_session_changed(self, index):
        """Handle session selection change."""
        if index < 0 or index >= len(self.sessions):
            return
            
        session = self.sessions[index]
        self.current_session_id = session.get('id')
        logger.info(f"SuperLap session changed to: {session.get('track_name')} (ID: {self.current_session_id})")
        
        # Load laps for this session
        self.load_laps_for_session(self.current_session_id)
    
    def load_laps_for_session(self, session_id):
        """Load user laps and SuperLaps for the selected session."""
        if not session_id:
            return
            
        try:
            from Supabase.database import get_laps, get_super_laps_for_session
            
            # Load user laps
            laps_result = get_laps(session_id=session_id)
            if laps_result[0] is not None:
                self.user_laps = laps_result[0]
                
                # Update user lap combo
                self.user_lap_combo.clear()
                for lap in self.user_laps:
                    if lap.get('is_valid', True):
                        lap_text = f"Lap {lap.get('lap_number', '?')} - {self._format_time(lap.get('lap_time', 0))}"
                        self.user_lap_combo.addItem(lap_text, lap.get('id'))
            
            # Load SuperLaps
            ml_laps_result = get_super_laps_for_session(session_id)
            if ml_laps_result[0] is not None:
                self.ml_laps = ml_laps_result[0]
                
                # Update ML lap combo
                self.ml_lap_combo.clear()
                for lap in self.ml_laps:
                    lap_text = f"SuperLap {self._format_time(lap.get('lap_time', 0))}"
                    self.ml_lap_combo.addItem(lap_text, lap.get('id'))
            
            logger.info(f"SuperLap: Loaded {len(self.user_laps)} user laps, {len(self.ml_laps)} SuperLaps")
            
        except Exception as e:
            logger.error(f"Error loading laps for SuperLap session: {e}")
    
    def analyze_performance(self):
        """Analyze the selected user lap against the SuperLap."""
        user_lap_id = self.user_lap_combo.currentData()
        ml_lap_id = self.ml_lap_combo.currentData()
        
        if not user_lap_id or not ml_lap_id:
            QMessageBox.warning(self, "Selection Required", "Please select both a user lap and a SuperLap to analyze.")
            return
        
        # Find the selected laps
        self.current_user_lap = next((lap for lap in self.user_laps if lap.get('id') == user_lap_id), None)
        self.current_ml_lap = next((lap for lap in self.ml_laps if lap.get('id') == ml_lap_id), None)
        
        if not self.current_user_lap or not self.current_ml_lap:
            QMessageBox.warning(self, "Lap Data Error", "Could not find the selected lap data.")
            return
        
        # Update comparison display
        self.update_comparison_display()
        
        # Load telemetry comparison
        self.load_telemetry_comparison(user_lap_id, ml_lap_id)
        
        logger.info(f"Started SuperLap analysis: User Lap {self.current_user_lap.get('lap_number')} vs SuperLap")
    
    def update_comparison_display(self):
        """Update the lap comparison display."""
        if self.current_user_lap:
            user_time = self.current_user_lap.get('lap_time', 0)
            self.user_time_label.setText(self._format_time(user_time))
        
        if self.current_ml_lap:
            super_time = self.current_ml_lap.get('lap_time', 0)
            self.ai_time_label.setText(self._format_time(super_time))
        
        # Calculate and display delta
        if self.current_user_lap and self.current_ml_lap:
            user_time = self.current_user_lap.get('lap_time', 0)
            super_time = self.current_ml_lap.get('lap_time', 0)
            
            if user_time > 0 and super_time > 0:
                delta = user_time - super_time
                delta_text = f"⏱️ DELTA: {'+' if delta > 0 else ''}{self._format_time(abs(delta))}"
                self.delta_label.setText(delta_text)
                
                # Update color based on delta
                if delta > 0:
                    self.delta_label.setStyleSheet("""
                        color: #ff4444;
                        font-size: 16px;
                        font-weight: bold;
                        border: 1px solid #ff4444;
                        border-radius: 4px;
                        padding: 8px;
                        text-align: center;
                    """)
                else:
                    self.delta_label.setStyleSheet("""
                        color: #44ff44;
                        font-size: 16px;
                        font-weight: bold;
                        border: 1px solid #44ff44;
                        border-radius: 4px;
                        padding: 8px;
                        text-align: center;
                    """)
    
    def load_telemetry_comparison(self, user_lap_id, super_lap_id):
        """Load telemetry data for SuperLap comparison."""
        # Start telemetry comparison worker
        thread_id = str(uuid.uuid4())
        thread = QThread()
        worker = SuperLapTelemetryWorker(user_lap_id, super_lap_id)
        worker.moveToThread(thread)
        
        # Connect signals with Qt.QueuedConnection to prevent race conditions
        worker.telemetry_loaded.connect(self.on_telemetry_loaded, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(lambda: self._remove_thread_from_tracking(thread_id), Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(thread.quit, Qt.ConnectionType.QueuedConnection)
        thread.started.connect(worker.run, Qt.ConnectionType.QueuedConnection)
        
        # Track thread
        self.active_threads.append((thread_id, thread, worker))
        
        # Start thread
        thread.start()
    
    def on_telemetry_loaded(self, user_data, super_lap_data, user_error, super_error):
        """Handle telemetry comparison data loaded."""
        logger.info(f"SuperLap telemetry loaded - User: {user_data is not None}, SuperLap: {super_lap_data is not None}")
        
        if user_error or super_error:
            error_parts = []
            if user_error:
                error_parts.append(f"User: {user_error}")
            if super_error:
                error_parts.append(f"SuperLap: {super_error}")
            
            error_text = "Telemetry error: " + " | ".join(error_parts)
            logger.error(error_text)
            return
        
        # Get track length
        track_length = self.get_track_length() or 5000
        
        # Update graphs with comparison data
        self.update_graphs_with_comparison(user_data, super_lap_data, track_length)
    
    def update_graphs_with_comparison(self, user_data, super_lap_data, track_length):
        """Update telemetry graphs with SuperLap comparison data."""
        try:
            # Map data for graph widgets
            def map_telemetry_data(data):
                if not data or not data.get('points'):
                    return None
                    
                mapped_points = []
                for point in data['points']:
                    mapped_point = point.copy()
                    
                    # Convert track_position to LapDist
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
                    
                    # Set defaults
                    mapped_point.setdefault('Throttle', 0)
                    mapped_point.setdefault('Brake', 0)
                    mapped_point.setdefault('Steering', 0)
                    mapped_point.setdefault('Speed', 0)
                    mapped_point.setdefault('Gear', 0)
                    mapped_point.setdefault('LapDist', 0)
                    
                    mapped_points.append(mapped_point)
                
                return {'points': mapped_points}
            
            user_mapped = map_telemetry_data(user_data)
            super_mapped = map_telemetry_data(super_lap_data)
            
            # Update graphs with comparison
            if user_mapped and super_mapped:
                if hasattr(self, 'throttle_graph'):
                    self.throttle_graph.update_graph_comparison(user_mapped, super_mapped, track_length)
                if hasattr(self, 'brake_graph'):
                    self.brake_graph.update_graph_comparison(user_mapped, super_mapped, track_length)
                if hasattr(self, 'steering_graph'):
                    self.steering_graph.update_graph_comparison(user_mapped, super_mapped, track_length)
                if hasattr(self, 'speed_graph'):
                    self.speed_graph.update_graph_comparison(user_mapped, super_mapped, track_length)
                if hasattr(self, 'gear_graph'):
                    self.gear_graph.update_graph_comparison(user_mapped, super_mapped, track_length)
                    
                logger.info("✅ Updated all SuperLap graphs in comparison mode")
                
        except Exception as e:
            logger.error(f"Error updating SuperLap graphs: {e}")
    
    def get_track_length(self):
        """Get track length from current session."""
        if self.current_session_id and self.sessions:
            for session in self.sessions:
                if session.get('id') == self.current_session_id:
                    return session.get('track_length', None)
        return None
    
    def _format_time(self, lap_time_seconds):
        """Format lap time in MM:SS.mmm format."""
        if lap_time_seconds <= 0:
            return "--:--.---"
        
        minutes = int(lap_time_seconds // 60)
        seconds = lap_time_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    
    def _remove_thread_from_tracking(self, thread_id):
        """Remove a thread from the active threads list."""
        self.active_threads = [(tid, t, w) for tid, t, w in self.active_threads if tid != thread_id]
    
    def lazy_init(self):
        """Lazy initialization when page is first accessed."""
        logger.info("⚡ Lazy initializing SuperLap page with full AI analysis...")
    
    def on_page_activated(self):
        """Called when page becomes active."""
        super().on_page_activated()
        if not hasattr(self, '_sessions_loaded'):
            # Start data loading when page is actually accessed
            QTimer.singleShot(100, self.load_initial_data)
            self._sessions_loaded = True
    
    def cleanup(self):
        """Clean up any running threads."""
        self._is_being_destroyed = True
        logger.info("🧹 Starting SuperLap page cleanup...")
        
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
        logger.info("🧹 SuperLap page cleanup completed")