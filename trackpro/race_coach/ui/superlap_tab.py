"""SuperLap tab for Race Coach - AI-powered lap analysis.

This module contains the SuperLap analysis tab that helps drivers understand
exactly how to improve their lap times using AI-optimized racing lines.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFrame, QGridLayout, QProgressBar, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QTextEdit, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject
from PyQt5.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


# --- SuperLap Session Worker ---
class SuperLapSessionWorker(QObject):
    """Worker to load SuperLap sessions in the background."""
    
    sessions_loaded = pyqtSignal(list)  # (sessions_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_cancelled = False

    def run(self):
        """Load sessions with ML data available."""
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                self.error.emit("Authentication required")
                self.finished.emit()
                return
            
            # Get user sessions with car/track info
            sessions_result = (
                main_supabase.client.table("sessions")
                .select("id,car_id,track_id,created_at,cars(name),tracks(name)")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            
            if not sessions_result.data:
                self.sessions_loaded.emit([])
                self.finished.emit()
                return
            
            # Filter sessions that have matching ML data available
            valid_sessions = []
            
            for session in sessions_result.data:
                if self.is_cancelled:
                    return
                    
                car_id = session.get('car_id')
                track_id = session.get('track_id')
                
                if car_id and track_id:
                    # Check if ML data exists for this car/track combo
                    try:
                        ml_check = (
                            main_supabase.client.table("laps_ml")
                            .select("id")
                            .eq("car_id", car_id)
                            .eq("track_id", track_id)
                            .limit(1)
                            .execute()
                        )
                        
                        if ml_check.data:  # ML data exists for this car/track
                            valid_sessions.append(session)
                    except Exception as ml_error:
                        print(f"Error checking ML data for session {session.get('id')}: {ml_error}")
                        # Include session anyway for now during development
                        valid_sessions.append(session)
                        continue
            
            # Sort sessions by date (newest first) and limit
            valid_sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
            
            if len(valid_sessions) > 25:
                valid_sessions = valid_sessions[:25]
            
            self.sessions_loaded.emit(valid_sessions)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- SuperLap User Lap Worker ---
class SuperLapUserLapWorker(QObject):
    """Worker to load user laps for a session in the background."""
    
    laps_loaded = pyqtSignal(list)  # (laps_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id
        self.is_cancelled = False

    def run(self):
        """Load user laps for the session."""
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                self.error.emit("Authentication required")
                self.finished.emit()
                return
            
            # Get laps for this session
            laps_result = (
                main_supabase.client.table("laps")
                .select("id,lap_number,lap_time,is_valid")
                .eq("session_id", self.session_id)
                .eq("is_valid", True)  # Only show valid laps
                .order("lap_number")
                .execute()
            )
            
            if self.is_cancelled:
                return
            
            if laps_result.data:
                self.laps_loaded.emit(laps_result.data)
            else:
                self.laps_loaded.emit([])
            
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- SuperLap ML Lap Worker ---
class SuperLapMLLapWorker(QObject):
    """Worker to load ML laps for a car/track combination in the background."""
    
    laps_loaded = pyqtSignal(list)  # (ml_laps_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self, car_id, track_id):
        super().__init__()
        self.car_id = car_id
        self.track_id = track_id
        self.is_cancelled = False

    def run(self):
        """Load ML laps for the car/track combination."""
        try:
            ml_laps_data = self._get_filtered_ml_laps(self.car_id, self.track_id)
            
            if self.is_cancelled:
                return
            
            self.laps_loaded.emit(ml_laps_data)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def _get_filtered_ml_laps(self, car_id, track_id):
        """Get ML laps filtered by car and track from Supabase laps_ml table."""
        if not car_id or not track_id:
            return []
            
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available for ML laps")
                return []
            
            # Query the laps_ml table for ML-optimized laps matching this car/track combo
            ml_laps_result = (
                main_supabase.client.table("laps_ml")
                .select("*")
                .eq("car_id", car_id)
                .eq("track_id", track_id)
                .order("confidence_score", desc=True)  # Best confidence first
                .limit(10)  # Limit to top 10 ML laps
                .execute()
            )
            
            if not ml_laps_result.data:
                print(f"No ML laps found for car_id={car_id}, track_id={track_id}")
                return []
            
            ml_laps = []
            for ml_lap in ml_laps_result.data:
                if self.is_cancelled:
                    return []
                
                # Get additional optimization details if available
                optimization_details = {}
                
                # Try to get brake points from ml_optimizations table
                try:
                    opt_result = (
                        main_supabase.client.table("ml_optimizations")
                        .select("optimization_type,details")
                        .eq("ml_lap_id", ml_lap.get("id"))
                        .execute()
                    )
                    
                    if opt_result.data:
                        for opt in opt_result.data:
                            opt_type = opt.get("optimization_type")
                            details = opt.get("details", {})
                            
                            if isinstance(details, str):
                                import json
                                try:
                                    details = json.loads(details)
                                except:
                                    details = {}
                            
                            if opt_type == "brake_points":
                                optimization_details["brake_points"] = details.get("points", [])
                            elif opt_type == "throttle_points":
                                optimization_details["throttle_points"] = details.get("points", [])
                            elif opt_type == "racing_line":
                                optimization_details["racing_line"] = details.get("sections", [])
                                
                except Exception as opt_error:
                    print(f"Error fetching optimization details: {opt_error}")
                
                # Build the ML lap data structure
                ml_lap_data = {
                    'id': ml_lap.get('id'),
                    'lap_time': ml_lap.get('lap_time', 0),
                    'predicted_improvement_ms': ml_lap.get('predicted_improvement_ms', 0),
                    'confidence_score': ml_lap.get('confidence_score', 0),
                    'optimization_method': ml_lap.get('optimization_method', 'ml_analysis'),
                    'model_used': ml_lap.get('model_used', 'AI Model'),
                    'car_id': car_id,
                    'track_id': track_id,
                    'created_at': ml_lap.get('created_at'),
                    **optimization_details  # Add brake_points, throttle_points, racing_line
                }
                
                ml_laps.append(ml_lap_data)
            
            print(f"Found {len(ml_laps)} ML laps for car_id={car_id}, track_id={track_id}")
            return ml_laps
            
        except Exception as e:
            print(f"Error fetching ML laps from Supabase: {e}")
            return []

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


class SuperLapWidget(QWidget):
    """Advanced SuperLap analysis widget - helping drivers understand exactly how to improve."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.ml_laps = []
        self.user_laps = []
        self.current_user_lap = None
        self.current_ml_lap = None
        self.current_session_info = None
        
        # Track active threads for cleanup
        self.active_threads = []
        self._is_being_destroyed = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the comprehensive SuperLap analysis UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Compact header section with session context
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        header_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(3)
        
        # Title
        title_label = QLabel("SuperLap Analysis")
        title_label.setStyleSheet("""
            color: #00ff88;
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 2px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Session context
        self.session_context_label = QLabel("Select a session to see AI-optimized racing lines for your car/track combo")
        self.session_context_label.setStyleSheet("""
            color: #cccccc;
            font-size: 12px;
            font-style: normal;
            background-color: transparent;
        """)
        self.session_context_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.session_context_label)
        
        main_layout.addWidget(header_frame)
        
        # Combined session and lap selection in one compact frame
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        controls_frame.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
            padding: 8px;
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(6)
        
        # Session selection row
        session_row = QHBoxLayout()
        session_label = QLabel("Session:")
        session_label.setStyleSheet("color: #DDD; font-weight: bold; min-width: 70px;")
        session_row.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
            }
        """)
        self.session_combo.currentTextChanged.connect(self.on_session_changed)
        session_row.addWidget(self.session_combo, 1)
        
        # Refresh button
        refresh_button = QPushButton("🔄")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px 8px;
                min-width: 30px;
                max-width: 30px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        refresh_button.clicked.connect(self.refresh_data)
        session_row.addWidget(refresh_button)
        
        # Add iRacing connection reset button
        self.reset_connection_button = QPushButton("🔌 Reset iRacing")
        self.reset_connection_button.setToolTip("Reset iRacing connection if showing as disconnected")
        self.reset_connection_button.setStyleSheet("padding: 5px 10px; background-color: #444; color: #FFA500;")
        self.reset_connection_button.clicked.connect(self._reset_iracing_connection)
        session_row.addWidget(self.reset_connection_button)
        
        controls_layout.addLayout(session_row)
        
        # Lap selection row
        lap_row = QHBoxLayout()
        
        # User lap selection
        user_lap_label = QLabel("Your Lap:")
        user_lap_label.setStyleSheet("color: #DDD; font-weight: bold; min-width: 70px;")
        lap_row.addWidget(user_lap_label)
        
        self.user_lap_combo = QComboBox()
        self.user_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
            }
        """)
        self.user_lap_combo.currentTextChanged.connect(self.on_user_lap_changed)
        lap_row.addWidget(self.user_lap_combo, 1)
        
        lap_row.addSpacing(10)
        
        # ML lap selection
        ml_lap_label = QLabel("SuperLap:")
        ml_lap_label.setStyleSheet("color: #00ff88; font-weight: bold; min-width: 70px;")
        lap_row.addWidget(ml_lap_label)
        
        self.ml_lap_combo = QComboBox()
        self.ml_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a3d1a;
                color: #00ff88;
                border: 1px solid #00ff88;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #00ff88;
            }
        """)
        self.ml_lap_combo.currentTextChanged.connect(self.on_ml_lap_changed)
        lap_row.addWidget(self.ml_lap_combo, 1)
        
        lap_row.addSpacing(10)
        
        # Analyze button (renamed from Compare)
        self.compare_button = QPushButton("Analyze Performance")
        self.compare_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff88;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #00cc6a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        self.compare_button.clicked.connect(self.analyze_performance)
        self.compare_button.setEnabled(False)
        lap_row.addWidget(self.compare_button)
        
        controls_layout.addLayout(lap_row)
        
        main_layout.addWidget(controls_frame)
        
        # Create tabbed analysis view with reduced margins
        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #111;
                border-radius: 3px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background-color: #333;
                color: #CCC;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: #444;
                color: #00ff88;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # Performance Overview Tab
        self.overview_tab = self.create_overview_tab()
        self.analysis_tabs.addTab(self.overview_tab, "Overview")
        
        # Sector Analysis Tab
        self.sector_tab = self.create_sector_analysis_tab()
        self.analysis_tabs.addTab(self.sector_tab, "Sectors")
        
        # Driving Technique Tab
        self.technique_tab = self.create_technique_analysis_tab()
        self.analysis_tabs.addTab(self.technique_tab, "Technique")
        
        # Telemetry Comparison Tab
        self.telemetry_tab = self.create_telemetry_comparison_tab()
        self.analysis_tabs.addTab(self.telemetry_tab, "Telemetry")
        
        main_layout.addWidget(self.analysis_tabs)
        
        # Load initial data
        self.refresh_data()
    
    def create_overview_tab(self):
        """Create the performance overview tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Performance metrics grid
        metrics_frame = QFrame()
        metrics_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        metrics_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setSpacing(8)
        
        # Lap time comparison
        self.user_time_label = QLabel("Your Time: --:--.---")
        self.user_time_label.setStyleSheet("color: #DDDDDD; font-size: 16px; font-weight: bold; background-color: transparent;")
        metrics_layout.addWidget(self.user_time_label, 0, 0)
        
        self.ml_time_label = QLabel("SuperLap Time: --:--.---")
        self.ml_time_label.setStyleSheet("color: #00ff88; font-size: 16px; font-weight: bold; background-color: transparent;")
        metrics_layout.addWidget(self.ml_time_label, 0, 1)
        
        self.time_diff_label = QLabel("Potential Improvement: --:--.---")
        self.time_diff_label.setStyleSheet("color: #ff6666; font-size: 16px; font-weight: bold; background-color: transparent;")
        metrics_layout.addWidget(self.time_diff_label, 0, 2)
        
        # AI Analysis info
        self.confidence_label = QLabel("AI Confidence: --%")
        self.confidence_label.setStyleSheet("color: #ffaa00; font-size: 12px; background-color: transparent;")
        metrics_layout.addWidget(self.confidence_label, 1, 0)
        
        self.method_label = QLabel("Analysis Method: --")
        self.method_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        metrics_layout.addWidget(self.method_label, 1, 1)
        
        self.model_label = QLabel("AI Model: --")
        self.model_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        metrics_layout.addWidget(self.model_label, 1, 2)
        
        layout.addWidget(metrics_frame)
        
        # Create a horizontal layout for insights and breakdown to use space more efficiently
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # Key insights section
        insights_frame = QFrame()
        insights_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        insights_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        insights_layout = QVBoxLayout(insights_frame)
        insights_layout.setSpacing(5)
        
        insights_title = QLabel("🎯 Key Areas for Improvement")
        insights_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        insights_layout.addWidget(insights_title)
        
        self.insights_list = QLabel("Select laps to see personalized improvement suggestions")
        self.insights_list.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.insights_list.setWordWrap(True)
        insights_layout.addWidget(self.insights_list)
        
        content_layout.addWidget(insights_frame, 1)
        
        # Performance breakdown
        breakdown_frame = QFrame()
        breakdown_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        breakdown_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        breakdown_layout = QVBoxLayout(breakdown_frame)
        breakdown_layout.setSpacing(5)
        
        breakdown_title = QLabel("📊 Performance Breakdown")
        breakdown_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        breakdown_layout.addWidget(breakdown_title)
        
        # Create progress bars for different aspects
        self.create_performance_bars(breakdown_layout)
        
        content_layout.addWidget(breakdown_frame, 1)
        
        layout.addLayout(content_layout)
        
        layout.addStretch()
        return tab
    
    def create_performance_bars(self, layout):
        """Create performance comparison bars."""
        aspects = [
            ("Braking Efficiency", "brake_efficiency"),
            ("Cornering Speed", "cornering_speed"), 
            ("Throttle Application", "throttle_application"),
            ("Racing Line", "racing_line"),
            ("Consistency", "consistency")
        ]
        
        self.performance_bars = {}
        
        for aspect_name, aspect_key in aspects:
            aspect_layout = QHBoxLayout()
            
            # Label
            label = QLabel(aspect_name)
            label.setStyleSheet("color: #dddddd; font-size: 12px; min-width: 120px; background-color: transparent;")
            aspect_layout.addWidget(label)
            
            # Progress bar
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(0)
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 3px;
                    background-color: #333;
                    color: white;
                    text-align: center;
                    font-weight: bold;
                    height: 16px;
                    font-size: 10px;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ff4444, stop:0.5 #ffaa00, stop:1 #00ff88);
                    border-radius: 3px;
                }
            """)
            aspect_layout.addWidget(progress)
            
            # Score label
            score_label = QLabel("--/100")
            score_label.setStyleSheet("color: #cccccc; font-size: 10px; min-width: 50px; background-color: transparent;")
            aspect_layout.addWidget(score_label)
            
            self.performance_bars[aspect_key] = (progress, score_label)
            layout.addLayout(aspect_layout)
    
    def create_sector_analysis_tab(self):
        """Create the sector analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Sector comparison table
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        table_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setSpacing(5)
        
        table_title = QLabel("🏁 Sector-by-Sector Analysis")
        table_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        table_layout.addWidget(table_title)
        
        self.sector_table = QTableWidget()
        self.sector_table.setColumnCount(5)
        self.sector_table.setHorizontalHeaderLabels(["Sector", "Your Time", "SuperLap Time", "Difference", "Improvement"])
        self.sector_table.setStyleSheet("""
            QTableWidget {
                background-color: #222;
                color: white;
                gridline-color: #444;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            QTableWidget::item:selected {
                background-color: #444;
            }
            QHeaderView::section {
                background-color: #333;
                color: #00ff88;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.sector_table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.sector_table)
        
        layout.addWidget(table_frame)
        
        # Sector insights
        insights_frame = QFrame()
        insights_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        insights_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        insights_layout = QVBoxLayout(insights_frame)
        insights_layout.setSpacing(5)
        
        insights_title = QLabel("💡 Sector-Specific Tips")
        insights_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        insights_layout.addWidget(insights_title)
        
        self.sector_tips = QLabel("Analyze your laps to see specific tips for each sector")
        self.sector_tips.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.sector_tips.setWordWrap(True)
        insights_layout.addWidget(self.sector_tips)
        
        layout.addWidget(insights_frame)
        
        layout.addStretch()
        return tab
    
    def create_technique_analysis_tab(self):
        """Create the driving technique analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Brake points analysis
        brake_frame = QFrame()
        brake_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        brake_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        brake_layout = QVBoxLayout(brake_frame)
        brake_layout.setSpacing(5)
        
        brake_title = QLabel("🛑 Braking Analysis")
        brake_title.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        brake_layout.addWidget(brake_title)
        
        self.brake_analysis = QLabel("Brake point analysis will appear here")
        self.brake_analysis.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.brake_analysis.setWordWrap(True)
        brake_layout.addWidget(self.brake_analysis)
        
        layout.addWidget(brake_frame)
        
        # Throttle analysis
        throttle_frame = QFrame()
        throttle_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        throttle_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        throttle_layout = QVBoxLayout(throttle_frame)
        throttle_layout.setSpacing(5)
        
        throttle_title = QLabel("⚡ Throttle Application")
        throttle_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        throttle_layout.addWidget(throttle_title)
        
        self.throttle_analysis = QLabel("Throttle application analysis will appear here")
        self.throttle_analysis.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.throttle_analysis.setWordWrap(True)
        throttle_layout.addWidget(self.throttle_analysis)
        
        layout.addWidget(throttle_frame)
        
        # Racing line analysis
        line_frame = QFrame()
        line_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        line_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        line_layout = QVBoxLayout(line_frame)
        line_layout.setSpacing(5)
        
        line_title = QLabel("🏎️ Racing Line")
        line_title.setStyleSheet("color: #ffaa00; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        line_layout.addWidget(line_title)
        
        self.line_analysis = QLabel("Racing line analysis will appear here")
        self.line_analysis.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.line_analysis.setWordWrap(True)
        line_layout.addWidget(self.line_analysis)
        
        layout.addWidget(line_frame)
        
        layout.addStretch()
        return tab
    
    def create_telemetry_comparison_tab(self):
        """Create the telemetry comparison tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Placeholder for telemetry graphs
        graphs_frame = QFrame()
        graphs_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        graphs_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        graphs_layout = QVBoxLayout(graphs_frame)
        graphs_layout.setSpacing(5)
        
        graphs_title = QLabel("📈 Telemetry Comparison")
        graphs_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        graphs_layout.addWidget(graphs_title)
        
        self.telemetry_placeholder = QLabel("Detailed telemetry comparison graphs will be displayed here.\nThis will include throttle, brake, steering, and speed traces overlaid with the SuperLap data.")
        self.telemetry_placeholder.setStyleSheet("""
            color: #666;
            font-size: 12px;
            font-style: italic;
            padding: 30px;
            text-align: center;
        """)
        self.telemetry_placeholder.setAlignment(Qt.AlignCenter)
        graphs_layout.addWidget(self.telemetry_placeholder)
        
        layout.addWidget(graphs_frame)
        
        layout.addStretch()
        return tab
    
    def refresh_data(self):
        """Refresh the session and lap data from Supabase asynchronously."""
        try:
            # Load sessions asynchronously to avoid blocking UI
            QTimer.singleShot(0, self.load_sessions_async)
        except Exception as e:
            print(f"Error refreshing SuperLap data: {e}")
    
    def load_sessions_async(self):
        """Load user sessions asynchronously to avoid blocking the UI."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if session loading is already in progress
        if self._is_thread_running('session_load'):
            logger.info("Session loading already in progress, skipping duplicate request")
            return
            
        # Create a worker thread to handle the database operations
        session_load_thread = QThread()
        session_load_worker = SuperLapSessionWorker()
        session_load_worker.moveToThread(session_load_thread)
        
        # Track this thread for cleanup with unique identifier
        thread_id = f'session_load_{id(session_load_thread)}'
        self.active_threads.append((thread_id, session_load_thread, session_load_worker))
        
        # Connect signals
        session_load_thread.started.connect(session_load_worker.run)
        session_load_worker.sessions_loaded.connect(self.on_sessions_loaded)
        session_load_worker.error.connect(self.on_sessions_error)
        session_load_worker.finished.connect(session_load_thread.quit)
        session_load_worker.finished.connect(session_load_worker.deleteLater)
        session_load_thread.finished.connect(session_load_thread.deleteLater)
        session_load_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
        
        # Start the thread
        session_load_thread.start()
    
    def on_sessions_loaded(self, sessions):
        """Handle loaded sessions from worker thread."""
        try:
            if hasattr(self, 'session_combo'):
                # Temporarily block signals to prevent on_session_changed during programmatic population
                self.session_combo.blockSignals(True)
                
                self.session_combo.clear()
                
                if sessions:
                    for session in sessions:
                        display_text = self._format_session_display(session)
                        self.session_combo.addItem(display_text, session)
                    
                    # Select first session by default
                    if self.session_combo.count() > 0:
                        self.session_combo.setCurrentIndex(0)
                else:
                    self.session_combo.addItem("No sessions found", None)
                
                self.session_combo.blockSignals(False)
                    
            logger.info(f"Loaded {len(sessions) if sessions else 0} sessions")
            
        except Exception as e:
            logger.error(f"Error handling loaded sessions: {e}")
    
    def on_sessions_error(self, error_message):
        """Handle session loading errors."""
        self.session_combo.clear()
        self.session_combo.addItem(f"Error: {error_message}", None)
        self.session_context_label.setText("Error loading session data. Please try again.")
    
    def on_session_changed(self):
        """Handle session selection change."""
        current_session = self.session_combo.currentData()
        if current_session:
            self.current_session_info = current_session
            # Extract car and track names from the nested objects
            car_name = current_session.get('cars', {}).get('name', 'Unknown Car') if current_session.get('cars') else 'Unknown Car'
            track_name = current_session.get('tracks', {}).get('name', 'Unknown Track') if current_session.get('tracks') else 'Unknown Track'
            
            self.session_context_label.setText(f"Analyzing: {car_name} at {track_name}")
            
            # Load laps for this session
            self.load_user_laps()
            self.load_ml_laps()
        else:
            self.current_session_info = None
            self.session_context_label.setText("Select a session to see AI-optimized racing lines")
            self.user_lap_combo.clear()
            self.ml_lap_combo.clear()
    
    def load_user_laps(self):
        """Load user laps for the selected session asynchronously."""
        if not self.current_session_info:
            return
        
        # Use QTimer to defer the database operation
        QTimer.singleShot(0, self._load_user_laps_async)
    
    def _load_user_laps_async(self):
        """Load user laps asynchronously to avoid blocking UI."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if user lap loading is already in progress
        if self._is_thread_running('user_lap'):
            logger.info("User lap loading already in progress, skipping duplicate request")
            return
            
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available for user laps")
                self.user_lap_combo.clear()
                self.user_lap_combo.addItem("Authentication required", None)
                return
            
            session_id = self.current_session_info.get('id')
            
            # Show loading state
            self.user_lap_combo.clear()
            self.user_lap_combo.addItem("Loading laps...", None)
            
            # Create worker for lap loading
            user_lap_thread = QThread()
            user_lap_worker = SuperLapUserLapWorker(session_id)
            user_lap_worker.moveToThread(user_lap_thread)
            
            # Track this thread for cleanup with unique identifier
            thread_id = f'user_lap_{id(user_lap_thread)}'
            self.active_threads.append((thread_id, user_lap_thread, user_lap_worker))
            
            # Connect signals
            user_lap_thread.started.connect(user_lap_worker.run)
            user_lap_worker.laps_loaded.connect(self.on_user_laps_loaded)
            user_lap_worker.error.connect(self.on_user_laps_error)
            user_lap_worker.finished.connect(user_lap_thread.quit)
            user_lap_worker.finished.connect(user_lap_worker.deleteLater)
            user_lap_thread.finished.connect(user_lap_thread.deleteLater)
            user_lap_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
            
            # Start the thread
            user_lap_thread.start()
                
        except Exception as e:
            print(f"Error loading user laps: {e}")
            self.user_lap_combo.clear()
            self.user_lap_combo.addItem("Error loading laps", None)
    
    def on_user_laps_loaded(self, laps):
        """Handle loaded user laps."""
        self.user_lap_combo.clear()
        
        if laps:
            self.user_laps = laps
            for lap in laps:
                lap_number = lap.get('lap_number', 0)
                lap_time = lap.get('lap_time', 0)
                time_str = self._format_time(lap_time) if lap_time > 0 else "Invalid"
                display_text = f"Lap {lap_number} - {time_str}"
                self.user_lap_combo.addItem(display_text, lap['id'])
        else:
            self.user_laps = []
            self.user_lap_combo.addItem("No valid laps available", None)
    
    def on_user_laps_error(self, error_message):
        """Handle user lap loading errors."""
        self.user_lap_combo.clear()
        self.user_lap_combo.addItem(f"Error: {error_message}", None)
    
    def load_ml_laps(self):
        """Load ML-optimized laps that match the current session's car/track combination asynchronously."""
        if not self.current_session_info:
            return
        
        # Use QTimer to defer the database operation
        QTimer.singleShot(0, self._load_ml_laps_async)
    
    def _load_ml_laps_async(self):
        """Load ML laps asynchronously to avoid blocking UI."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if ML lap loading is already in progress
        if self._is_thread_running('ml_lap'):
            logger.info("ML lap loading already in progress, skipping duplicate request")
            return
            
        try:
            # Get car and track IDs from session
            car_id = self.current_session_info.get('car_id')
            track_id = self.current_session_info.get('track_id')
            
            # Show loading state
            self.ml_lap_combo.clear()
            self.ml_lap_combo.addItem("Loading SuperLaps...", None)
            
            # Create worker for ML lap loading
            ml_lap_thread = QThread()
            ml_lap_worker = SuperLapMLLapWorker(car_id, track_id)
            ml_lap_worker.moveToThread(ml_lap_thread)
            
            # Track this thread for cleanup with unique identifier
            thread_id = f'ml_lap_{id(ml_lap_thread)}'
            self.active_threads.append((thread_id, ml_lap_thread, ml_lap_worker))
            
            # Connect signals
            ml_lap_thread.started.connect(ml_lap_worker.run)
            ml_lap_worker.laps_loaded.connect(self.on_ml_laps_loaded)
            ml_lap_worker.error.connect(self.on_ml_laps_error)
            ml_lap_worker.finished.connect(ml_lap_thread.quit)
            ml_lap_worker.finished.connect(ml_lap_worker.deleteLater)
            ml_lap_thread.finished.connect(ml_lap_thread.deleteLater)
            ml_lap_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
            
            # Start the thread
            ml_lap_thread.start()
            
        except Exception as e:
            print(f"Error loading ML laps: {e}")
            self.ml_lap_combo.clear()
            self.ml_lap_combo.addItem("Error loading SuperLaps", None)
    
    def on_ml_laps_loaded(self, ml_laps_data):
        """Handle loaded ML laps."""
        self.ml_lap_combo.clear()
        
        if ml_laps_data:
            self.ml_laps = ml_laps_data
            for lap in ml_laps_data:
                lap_time = lap.get('lap_time', 0)
                improvement = lap.get('predicted_improvement_ms', 0)
                confidence = lap.get('confidence_score', 0)
                model = lap.get('model_used', 'AI Model')
                
                time_str = self._format_time(lap_time) if lap_time > 0 else "Invalid"
                improvement_str = f"-{improvement/1000:.3f}s" if improvement > 0 else "No improvement"
                display_text = f"{model}: {time_str} ({improvement_str}, {confidence*100:.0f}% confidence)"
                self.ml_lap_combo.addItem(display_text, lap['id'])
        else:
            self.ml_laps = []
            self.ml_lap_combo.addItem("No SuperLaps available for this car/track", None)
    
    def on_ml_laps_error(self, error_message):
        """Handle ML lap loading errors."""
        self.ml_lap_combo.clear()
        self.ml_lap_combo.addItem(f"Error: {error_message}", None)
    
    def on_user_lap_changed(self):
        """Handle user lap selection change."""
        self._check_analysis_ready()
    
    def on_ml_lap_changed(self):
        """Handle ML lap selection change."""
        self._check_analysis_ready()
    
    def _check_analysis_ready(self):
        """Check if both laps are selected and enable/disable analyze button."""
        user_lap_id = self.user_lap_combo.currentData()
        ml_lap_id = self.ml_lap_combo.currentData()
        
        self.compare_button.setEnabled(user_lap_id is not None and ml_lap_id is not None)
    
    def analyze_performance(self):
        """Analyze the selected user lap against the SuperLap."""
        user_lap_id = self.user_lap_combo.currentData()
        ml_lap_id = self.ml_lap_combo.currentData()
        
        if not user_lap_id or not ml_lap_id:
            return
        
        # Find the selected laps in our data
        self.current_user_lap = next((lap for lap in self.user_laps if lap.get('id') == user_lap_id), None)
        self.current_ml_lap = next((lap for lap in self.ml_laps if lap.get('id') == ml_lap_id), None)
        
        if not self.current_user_lap or not self.current_ml_lap:
            return
        
        # Update the overview tab
        self._update_overview_tab()
        
        # TODO: Update other tabs with detailed analysis
        # For now, show placeholder messages
        self._update_placeholder_tabs()
    
    def _update_overview_tab(self):
        """Update the overview tab with analysis results."""
        if not self.current_user_lap or not self.current_ml_lap:
            return
        
        # Update lap times
        user_time = self.current_user_lap.get('lap_time', 0)
        ml_time = self.current_ml_lap.get('lap_time', 0)
        time_diff = user_time - ml_time
        
        self.user_time_label.setText(f"Your Time: {self._format_time(user_time)}")
        self.ml_time_label.setText(f"SuperLap Time: {self._format_time(ml_time)}")
        self.time_diff_label.setText(f"Potential Improvement: {self._format_time(abs(time_diff))}")
        
        # Update AI analysis info
        confidence = self.current_ml_lap.get('confidence_score', 0)
        method = self.current_ml_lap.get('optimization_method', 'ml_analysis')
        model = self.current_ml_lap.get('model_used', 'AI Model')
        
        self.confidence_label.setText(f"AI Confidence: {confidence*100:.0f}%")
        self.method_label.setText(f"Analysis Method: {method}")
        self.model_label.setText(f"AI Model: {model}")
        
        # Update insights
        insights_text = self._generate_insights()
        self.insights_list.setText(insights_text)
        
        # Update performance bars (placeholder values for now)
        self._update_performance_bars()
    
    def _generate_insights(self):
        """Generate personalized insights based on the lap comparison."""
        if not self.current_ml_lap:
            return "No analysis available"
        
        insights = []
        
        # Check for brake points
        brake_points = self.current_ml_lap.get('brake_points', [])
        if brake_points:
            insights.append(f"• Found {len(brake_points)} optimized brake points")
        
        # Check for throttle points
        throttle_points = self.current_ml_lap.get('throttle_points', [])
        if throttle_points:
            insights.append(f"• Identified {len(throttle_points)} throttle application improvements")
        
        # Check for racing line
        racing_line = self.current_ml_lap.get('racing_line', [])
        if racing_line:
            insights.append(f"• Racing line optimization available for {len(racing_line)} sections")
        
        # Add general improvement potential
        improvement_ms = self.current_ml_lap.get('predicted_improvement_ms', 0)
        if improvement_ms > 0:
            insights.append(f"• Total potential improvement: {improvement_ms/1000:.3f} seconds")
        
        return "\n".join(insights) if insights else "Analyzing lap data..."
    
    def _update_performance_bars(self):
        """Update the performance comparison bars."""
        # Placeholder implementation - in a real app, these would be calculated from telemetry
        aspects = {
            'brake_efficiency': 75,
            'cornering_speed': 82,
            'throttle_application': 68,
            'racing_line': 90,
            'consistency': 85
        }
        
        for aspect_key, score in aspects.items():
            if aspect_key in self.performance_bars:
                progress_bar, score_label = self.performance_bars[aspect_key]
                progress_bar.setValue(score)
                score_label.setText(f"{score}/100")
    
    def _update_placeholder_tabs(self):
        """Update placeholder tabs with temporary messages."""
        # Sector analysis placeholder
        self.sector_tips.setText(
            "Sector analysis coming soon!\n\n"
            "This will show:\n"
            "• Sector-by-sector time comparison\n"
            "• Specific areas where time is lost\n"
            "• Targeted improvement suggestions for each sector"
        )
        
        # Technique analysis placeholder
        self.brake_analysis.setText(
            "Brake point analysis will show:\n"
            "• Optimal brake points for each corner\n"
            "• Comparison with your current brake points\n"
            "• Specific distance/speed recommendations"
        )
        
        self.throttle_analysis.setText(
            "Throttle application analysis will show:\n"
            "• Corner exit throttle application timing\n"
            "• Throttle modulation through corners\n"
            "• Areas where earlier throttle application is possible"
        )
        
        self.line_analysis.setText(
            "Racing line analysis will show:\n"
            "• Optimal racing line visualization\n"
            "• Comparison with your current line\n"
            "• Specific apex and track-out point recommendations"
        )
    
    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if time_in_seconds is None or time_in_seconds < 0:
            return "--:--.---"
        minutes = int(time_in_seconds // 60)
        seconds = time_in_seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"
    
    def _format_session_display(self, session):
        """Format session data for display in combo box."""
        try:
            # Extract nested car and track names
            car_name = session.get('cars', {}).get('name', 'Unknown Car') if session.get('cars') else 'Unknown Car'
            track_name = session.get('tracks', {}).get('name', 'Unknown Track') if session.get('tracks') else 'Unknown Track'
            created_at = session.get('created_at', '')
            
            # Format date
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                display_text = f"{timestamp.strftime('%Y-%m-%d %H:%M')} - {track_name} ({car_name})"
            except (ValueError, TypeError):
                display_text = f"{created_at} - {track_name} ({car_name})"
            
            return display_text
            
        except Exception as e:
            logger.error(f"Error formatting session display: {e}")
            return f"Session {session.get('id', 'Unknown')}"
    
    def _is_thread_running(self, thread_type):
        """Check if a thread of the given type is already running."""
        for thread_id, thread, worker in self.active_threads:
            if thread_type in thread_id and thread.isRunning():
                return True
        return False
    
    def _remove_thread_from_tracking(self, thread_id):
        """Remove a thread from the active threads list."""
        self.active_threads = [(tid, t, w) for tid, t, w in self.active_threads if tid != thread_id]
    
    def _reset_iracing_connection(self):
        """Reset iRacing connection - delegate to parent if available."""
        if hasattr(self.parent_widget, 'reset_iracing_connection'):
            self.parent_widget.reset_iracing_connection()
        else:
            QMessageBox.information(self, "Reset Connection", "iRacing connection reset functionality not available in this context.")
    
    def cleanup(self):
        """Clean up any running threads when the widget is destroyed."""
        self._is_being_destroyed = True
        
        # Cancel all running workers
        for thread_id, thread, worker in self.active_threads:
            if hasattr(worker, 'cancel'):
                worker.cancel()
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # Wait up to 1 second
        
        self.active_threads.clear() 