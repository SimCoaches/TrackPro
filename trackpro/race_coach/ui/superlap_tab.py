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
from PyQt5.QtGui import QFont, QColor, QPixmap
import os

# Import the new function
from Supabase.database import get_sessions

# Import for AI coaching type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..utils.telemetry_worker import TelemetryMonitorWorker

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
            # We will use get_sessions instead of a direct call
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                self.error.emit("Authentication required")
                self.finished.emit()
                return

            # Use the get_sessions function to fetch only the user's sessions
            user_sessions, msg = get_sessions(limit=100, user_only=True)

            if user_sessions is None:
                self.error.emit(msg or "Failed to load sessions.")
                self.finished.emit()
                return
            
            if not user_sessions:
                self.sessions_loaded.emit([])
                self.finished.emit()
                return
            
            # Filter sessions that have matching ML data available
            valid_sessions = []
            
            for session in user_sessions:
                if self.is_cancelled:
                    return
                    
                car_id = session.get('car_id')
                track_id = session.get('track_id')
                
                if car_id and track_id:
                    # Check if SuperLap data exists for this car/track combo
                    try:
                        super_lap_check = (
                            main_supabase.client.table("super_laps_ml")
                            .select("id")
                            .eq("car_id", car_id)
                            .eq("track_id", track_id)
                            .limit(1)
                            .execute()
                        )
                        
                        if super_lap_check.data:  # SuperLap data exists for this car/track
                            valid_sessions.append(session)
                    except Exception as super_lap_error:
                        # In case of error, we can log it but shouldn't add the session
                        logger.error(f"Error checking SuperLap data for session {session.get('id')}: {super_lap_error}")
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
        """Get SuperLaps filtered by car and track from Supabase super_laps_ml table."""
        if not car_id or not track_id:
            return []
            
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available for SuperLaps")
                return []
            
            # Query the super_laps_ml table for SuperLaps matching this car/track combo
            super_laps_result = (
                main_supabase.client.table("super_laps_ml")
                .select("*")
                .eq("car_id", car_id)
                .eq("track_id", track_id)
                .order("confidence_level", desc=True)  # Best confidence first
                .limit(10)  # Limit to top 10 SuperLaps
                .execute()
            )
            
            if not super_laps_result.data:
                print(f"No SuperLaps found for car_id={car_id}, track_id={track_id}")
                return []
            
            super_laps = []
            for super_lap in super_laps_result.data:
                if self.is_cancelled:
                    return []
                
                # Build the SuperLap data structure
                super_lap_data = {
                    'id': super_lap.get('id'),
                    'lap_time': super_lap.get('total_time', 0),  # Use total_time from super_laps_ml
                    'confidence_score': super_lap.get('confidence_level', 0),  # Use confidence_level
                    'optimization_method': 'super_lap_analysis',
                    'model_used': 'SuperLap AI',
                    'car_id': car_id,
                    'track_id': track_id,
                    'created_at': super_lap.get('created_at'),
                    'sector_combination': super_lap.get('sector_combination', {}),
                    'sector_1_time': super_lap.get('sector_1_time'),
                    'sector_2_time': super_lap.get('sector_2_time'),
                    'sector_3_time': super_lap.get('sector_3_time'),
                }
                
                super_laps.append(super_lap_data)
            
            print(f"Found {len(super_laps)} SuperLaps for car_id={car_id}, track_id={track_id}")
            return super_laps
            
        except Exception as e:
            print(f"Error fetching SuperLaps from Supabase: {e}")
            return []

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- SuperLap Telemetry Worker ---
class SuperLapTelemetryWorker(QObject):
    """Worker to fetch telemetry data for both user lap and super lap in the background."""
    
    telemetry_loaded = pyqtSignal(object, object)  # (user_data, super_lap_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self, user_lap_id, super_lap_id):
        super().__init__()
        self.user_lap_id = user_lap_id
        self.super_lap_id = super_lap_id
        self.is_cancelled = False

    def _calculate_lap_stats(self, telemetry_points):
        """Calculate statistics for a lap from telemetry points."""
        if not telemetry_points:
            return None
            
        stats = {
            'max_speed': 0,
            'avg_speed': 0,
            'max_throttle': 0,
            'avg_throttle': 0,
            'max_brake': 0,
            'avg_brake': 0,
            'max_rpm': 0,
            'avg_rpm': 0,
            'point_count': len(telemetry_points)
        }
        
        # Calculate stats
        speeds = []
        throttles = []
        brakes = []
        rpms = []
        
        for point in telemetry_points:
            if 'speed' in point and point['speed'] is not None:
                speeds.append(point['speed'])
            if 'throttle' in point and point['throttle'] is not None:
                throttles.append(point['throttle'])
            if 'brake' in point and point['brake'] is not None:
                brakes.append(point['brake'])
            if 'rpm' in point and point['rpm'] is not None:
                rpms.append(point['rpm'])
        
        if speeds:
            stats['max_speed'] = max(speeds)
            stats['avg_speed'] = sum(speeds) / len(speeds)
        
        if throttles:
            stats['max_throttle'] = max(throttles)
            stats['avg_throttle'] = sum(throttles) / len(throttles)
            
        if brakes:
            stats['max_brake'] = max(brakes)
            stats['avg_brake'] = sum(brakes) / len(brakes)
            
        if rpms:
            stats['max_rpm'] = max(rpms)
            stats['avg_rpm'] = sum(rpms) / len(rpms)
        
        return stats

    def run(self):
        """Fetch telemetry data for both user lap and super lap."""
        try:
            from Supabase.database import get_telemetry_points, get_super_lap_telemetry_points
            
            user_result = None
            super_lap_result = None
            error_messages = []
            
            # Fetch user lap data
            if self.user_lap_id and not self.is_cancelled:
                try:
                    logger.info(f"Fetching user lap telemetry for lap_id: {self.user_lap_id}")
                    user_result_tuple = get_telemetry_points(self.user_lap_id)
                    if user_result_tuple[0] is not None:
                        user_points = user_result_tuple[0]
                        user_stats = self._calculate_lap_stats(user_points)
                        user_result = {
                            'points': user_points,
                            'stats': user_stats
                        }
                        logger.info(f"Successfully loaded {len(user_points)} user telemetry points")
                    else:
                        error_msg = f"User lap telemetry: {user_result_tuple[1]}"
                        error_messages.append(error_msg)
                        logger.warning(error_msg)
                except Exception as e:
                    error_msg = f"Error fetching user lap telemetry: {str(e)}"
                    error_messages.append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            # Fetch super lap data with enhanced debugging
            if self.super_lap_id and not self.is_cancelled:
                try:
                    logger.info(f"Fetching SuperLap telemetry for super_lap_id: {self.super_lap_id}")
                    super_lap_result_tuple = get_super_lap_telemetry_points(self.super_lap_id)
                    if super_lap_result_tuple[0] is not None:
                        super_lap_points = super_lap_result_tuple[0]
                        super_lap_stats = self._calculate_lap_stats(super_lap_points)
                        super_lap_result = {
                            'points': super_lap_points,
                            'stats': super_lap_stats
                        }
                        logger.info(f"Successfully loaded {len(super_lap_points)} SuperLap telemetry points")
                        
                        # Debug: Log first few points to verify data structure
                        if super_lap_points and len(super_lap_points) > 0:
                            sample_point = super_lap_points[0]
                            logger.info(f"SuperLap telemetry sample point fields: {list(sample_point.keys())}")
                            logger.info(f"SuperLap telemetry sample values: {dict(list(sample_point.items())[:5])}")
                    else:
                        error_msg = f"Super lap telemetry: {super_lap_result_tuple[1]}"
                        error_messages.append(error_msg)
                        logger.warning(error_msg)
                        
                        # Additional debugging for SuperLap telemetry failures
                        logger.info(f"SuperLap telemetry reconstruction failed for super_lap_id: {self.super_lap_id}")
                        logger.info(f"Error details: {super_lap_result_tuple[1]}")
                        
                except Exception as e:
                    error_msg = f"Error fetching super lap telemetry: {str(e)}"
                    error_messages.append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            if not self.is_cancelled:
                if error_messages and not user_result and not super_lap_result:
                    # Only emit error if we have no data at all
                    self.error.emit("; ".join(error_messages))
                else:
                    # Emit what we have, even if partial
                    self.telemetry_loaded.emit(user_result, super_lap_result)
                    if error_messages:
                        logger.warning(f"Partial telemetry data loaded with warnings: {'; '.join(error_messages)}")
                    
        except Exception as e:
            logger.error(f"Error in SuperLap telemetry fetch worker: {e}", exc_info=True)
            self.error.emit(str(e))
        
        self.finished.emit()

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
        self.telemetry_monitor: TelemetryMonitorWorker = None
        
        # Track active threads for cleanup
        self.active_threads = []
        self._is_being_destroyed = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the comprehensive SuperLap analysis UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)
        
        # MINIMAL header section - maximum space for telemetry!
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        header_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #FF4500, stop:0.3 #FF6600, stop:0.7 #FF8800, stop:1 #FF4500);
            border-radius: 6px;
            padding: 3px;
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(0)
        header_layout.setContentsMargins(3, 3, 3, 3)
        
        # Header title (logo now in tab title)
        title_label = QLabel("AI-POWERED LAP ANALYSIS")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            color: #FF4500;
            background-color: transparent;
            font-size: 18px;
            font-weight: bold;
            margin: 5px;
        """)
        header_layout.addWidget(title_label)
        
        # Remove session context to save space - info is already in the session dropdown
        
        main_layout.addWidget(header_frame)
        
        # Minimal controls frame
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        controls_frame.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
            padding: 4px;
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(2)
        controls_layout.setContentsMargins(3, 3, 3, 3)
        
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
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)
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
        
        # Add AI Coaching button
        self.coach_button = QPushButton("🎙️ Start AI Coach")
        self.coach_button.setToolTip("Start real-time AI coaching for the selected SuperLap")
        self.coach_button.setStyleSheet("padding: 5px 10px; background-color: #0055A4; color: white; font-weight: bold;")
        self.coach_button.setCheckable(True)
        self.coach_button.clicked.connect(self.toggle_ai_coaching)
        session_row.addWidget(self.coach_button)
        
        # Add SuperLap diagnostic button
        self.diagnostic_button = QPushButton("🔍 Diagnose")
        self.diagnostic_button.setToolTip("Run diagnostics on selected SuperLap telemetry")
        self.diagnostic_button.setStyleSheet("padding: 5px 10px; background-color: #444; color: #00FFFF;")
        self.diagnostic_button.clicked.connect(self._run_superlap_diagnostics)
        session_row.addWidget(self.diagnostic_button)
        
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
        ml_lap_label.setStyleSheet("color: #00ffff; font-weight: bold; min-width: 70px;")
        lap_row.addWidget(ml_lap_label)
        
        self.ml_lap_combo = QComboBox()
        self.ml_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a3d3d;
                color: #00ffff;
                border: 1px solid #00ffff;
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
                border-top: 5px solid #00ffff;
            }
        """)
        self.ml_lap_combo.currentTextChanged.connect(self.on_ml_lap_changed)
        lap_row.addWidget(self.ml_lap_combo, 1)
        
        lap_row.addSpacing(10)
        
        # Analyze button
        self.compare_button = QPushButton("Analyze Performance")
        self.compare_button.setStyleSheet("""
            QPushButton {
                background-color: #00ffff;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #00cccc;
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
        
        # Create telemetry comparison interface directly (no tabs)
        self.telemetry_comparison_widget = self.create_telemetry_comparison_interface()
        main_layout.addWidget(self.telemetry_comparison_widget)
        
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
    
    def create_telemetry_comparison_interface(self):
        """Create the main telemetry comparison interface."""
        from trackpro.race_coach.widgets.throttle_graph import ThrottleGraphWidget
        from trackpro.race_coach.widgets.brake_graph import BrakeGraphWidget
        from trackpro.race_coach.widgets.steering_graph import SteeringGraphWidget
        from trackpro.race_coach.widgets.speed_graph import SpeedGraphWidget
        from trackpro.race_coach.widgets.gear_graph import GearGraphWidget
        from PyQt5.QtWidgets import QScrollArea
        
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # Lap times comparison header
        times_frame = QFrame()
        times_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        times_frame.setStyleSheet("""
            background-color: #2d2d30;
            border: 1px solid #3c3c3c;
            border-radius: 6px;
            padding: 6px;
        """)
        times_layout = QHBoxLayout(times_frame)
        times_layout.setSpacing(15)
        times_layout.setContentsMargins(8, 4, 8, 4)
        
        # User lap time
        self.user_lap_time_label = QLabel("Your Lap: --:--.---")
        self.user_lap_time_label.setStyleSheet("""
            color: #e0e0e0;
            font-size: 14px;
            font-weight: bold;
            background-color: transparent;
        """)
        times_layout.addWidget(self.user_lap_time_label)
        
        # VS separator
        vs_label = QLabel("VS")
        vs_label.setStyleSheet("""
            color: #58a6ff;
            font-size: 12px;
            font-weight: bold;
            background-color: transparent;
        """)
        times_layout.addWidget(vs_label)
        
        # Super lap time
        self.super_lap_time_label = QLabel("SuperLap: --:--.---")
        self.super_lap_time_label.setStyleSheet("""
            color: #00d4ff;
            font-size: 14px;
            font-weight: bold;
            background-color: transparent;
        """)
        times_layout.addWidget(self.super_lap_time_label)
        
        # Delta
        self.delta_label = QLabel("Δ: --:--.---")
        self.delta_label.setStyleSheet("""
            color: #ff6b6b;
            font-size: 14px;
            font-weight: bold;
            background-color: transparent;
        """)
        times_layout.addWidget(self.delta_label)
        
        times_layout.addStretch()
        main_layout.addWidget(times_frame)
        
        # Create scroll area for graphs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
            QScrollBar:vertical {
                background-color: #21262d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #58a6ff;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #79c0ff;
            }
        """)
        
        # Content widget for the scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        
        # Speed graph
        self.speed_graph = SpeedGraphWidget()
        speed_container = self._create_graph_container(self.speed_graph, "Speed Comparison")
        content_layout.addWidget(speed_container)
        
        # Throttle graph
        self.throttle_graph = ThrottleGraphWidget()
        throttle_container = self._create_graph_container(self.throttle_graph, "Throttle Comparison")
        content_layout.addWidget(throttle_container)
        
        # Brake graph
        self.brake_graph = BrakeGraphWidget()
        brake_container = self._create_graph_container(self.brake_graph, "Brake Comparison")
        content_layout.addWidget(brake_container)
        
                # Steering graph
        self.steering_graph = SteeringGraphWidget()
        steering_container = self._create_graph_container(self.steering_graph, "Steering Comparison")
        content_layout.addWidget(steering_container)

        # Gear graph
        self.gear_graph = GearGraphWidget()
        gear_container = self._create_graph_container(self.gear_graph, "Gear Comparison")
        content_layout.addWidget(gear_container)

        # Message/status label
        self.telemetry_status_label = QLabel("Select laps above and click 'Analyze Performance' to compare telemetry")
        self.telemetry_status_label.setStyleSheet("""
            color: #e0e0e0;
            font-size: 14px;
            font-style: italic;
            padding: 20px;
            text-align: center;
            background-color: transparent;
        """)
        self.telemetry_status_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.telemetry_status_label)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        return widget
    
    def _create_graph_container(self, graph_widget, title):
        """Create a styled container for a graph widget."""
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        container.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #58a6ff;
            font-size: 12px;
            font-weight: bold;
            background-color: transparent;
            margin-bottom: 4px;
        """)
        layout.addWidget(title_label)
        
        # Graph widget
        graph_widget.setMinimumHeight(180)
        graph_widget.setMaximumHeight(220)
        layout.addWidget(graph_widget)
        
        return container
    
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
                
                # BUGFIX: Manually trigger session change after auto-selecting first session
                # This ensures laps are loaded for the auto-selected session
                if sessions and self.session_combo.count() > 0:
                    self.on_session_changed()
                    
            logger.info(f"Loaded {len(sessions) if sessions else 0} sessions")
            
        except Exception as e:
            logger.error(f"Error handling loaded sessions: {e}")
    
    def on_sessions_error(self, error_message):
        """Handle session loading errors."""
        self.session_combo.clear()
        self.session_combo.addItem(f"Error: {error_message}", None)
    
    def on_session_changed(self):
        """Handle session selection change."""
        current_session = self.session_combo.currentData()
        if current_session:
            self.current_session_info = current_session
            # Load laps for this session
            self.load_user_laps()
            self.load_ml_laps()
        else:
            self.current_session_info = None
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
                model = lap.get('model_used', 'AI Model')
                
                time_str = self._format_time(lap_time) if lap_time > 0 else "Invalid"
                display_text = f"{model}: {time_str}"
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
        """Analyze the selected user lap against the SuperLap with telemetry comparison."""
        user_lap_id = self.user_lap_combo.currentData()
        ml_lap_id = self.ml_lap_combo.currentData()
        
        if not user_lap_id or not ml_lap_id:
            return
        
        # Find the selected laps in our data
        self.current_user_lap = next((lap for lap in self.user_laps if lap.get('id') == user_lap_id), None)
        self.current_ml_lap = next((lap for lap in self.ml_laps if lap.get('id') == ml_lap_id), None)
        
        if not self.current_user_lap or not self.current_ml_lap:
            return
        
        try:
            # Update status
            self.telemetry_status_label.setText("Loading telemetry data for comparison...")
            
            # Load telemetry comparison data
            self._load_telemetry_comparison(user_lap_id, ml_lap_id)
            
            logger.info(f"Starting telemetry comparison for User Lap {self.current_user_lap.get('lap_number')} vs ML Lap")
            
        except Exception as e:
            logger.error(f"Error in performance analysis: {e}")
            QMessageBox.warning(self, "Analysis Error", f"Error analyzing performance: {str(e)}")
    
    def _load_telemetry_comparison(self, user_lap_id, super_lap_id):
        """Load telemetry data for comparison between user lap and super lap."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if telemetry loading is already in progress
        if self._is_thread_running('telemetry_comparison'):
            logger.info("Telemetry comparison loading already in progress, skipping duplicate request")
            return
        
        # Show detailed loading status
        if user_lap_id and super_lap_id:
            self.telemetry_status_label.setText("Loading telemetry data for both user lap and SuperLap...")
        elif user_lap_id:
            self.telemetry_status_label.setText("Loading user lap telemetry data...")
        elif super_lap_id:
            self.telemetry_status_label.setText("Loading SuperLap telemetry data...")
        else:
            self.telemetry_status_label.setText("No laps selected for comparison")
            return
            
        # Create worker for telemetry loading
        telemetry_thread = QThread()
        telemetry_worker = SuperLapTelemetryWorker(user_lap_id, super_lap_id)
        telemetry_worker.moveToThread(telemetry_thread)
        
        # Track this thread for cleanup with unique identifier
        thread_id = f'telemetry_comparison_{id(telemetry_thread)}'
        self.active_threads.append((thread_id, telemetry_thread, telemetry_worker))
        
        # Connect signals
        telemetry_thread.started.connect(telemetry_worker.run)
        telemetry_worker.telemetry_loaded.connect(self._on_telemetry_comparison_loaded)
        telemetry_worker.error.connect(self._on_telemetry_comparison_error)
        telemetry_worker.finished.connect(telemetry_thread.quit)
        telemetry_worker.finished.connect(telemetry_worker.deleteLater)
        telemetry_thread.finished.connect(telemetry_thread.deleteLater)
        telemetry_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
        
        # Start the thread
        telemetry_thread.start()
        logger.info(f"Started telemetry loading thread for user_lap_id={user_lap_id}, super_lap_id={super_lap_id}")
    
    def _on_telemetry_comparison_loaded(self, user_data, super_lap_data):
        """Handle loaded telemetry comparison data."""
        try:
            if not user_data and not super_lap_data:
                self.telemetry_status_label.setText("No telemetry data available for comparison")
                return
            
            # Enhanced status messages based on what data we have
            status_parts = []
            if user_data:
                user_points_count = len(user_data.get('points', []))
                status_parts.append(f"User lap: {user_points_count} points")
            else:
                status_parts.append("User lap: No data")
            
            if super_lap_data:
                super_points_count = len(super_lap_data.get('points', []))
                status_parts.append(f"SuperLap: {super_points_count} points")
            else:
                status_parts.append("SuperLap: No data")
            
            # Update lap times in header
            if self.current_user_lap and self.current_ml_lap:
                user_time = self.current_user_lap.get('lap_time', 0)
                super_time = self.current_ml_lap.get('lap_time', 0)
                
                self.user_lap_time_label.setText(f"Your Lap: {self._format_time(user_time)}")
                self.super_lap_time_label.setText(f"SuperLap: {self._format_time(super_time)}")
                
                # Calculate delta
                if user_time > 0 and super_time > 0:
                    delta = user_time - super_time
                    delta_text = f"Δ: {'+' if delta > 0 else ''}{self._format_time(abs(delta))}"
                    self.delta_label.setText(delta_text)
                    
                    # Update color based on delta
                    if delta > 0:
                        self.delta_label.setStyleSheet("""
                            color: #ff6b6b;
                            font-size: 16px;
                            font-weight: bold;
                            background-color: transparent;
                        """)
                    else:
                        self.delta_label.setStyleSheet("""
                            color: #00d4ff;
                            font-size: 16px;
                            font-weight: bold;
                            background-color: transparent;
                        """)
            
            # Get track length for graph scaling
            track_length = 0
            if self.current_session_info and self.current_session_info.get('tracks'):
                track_length = self.current_session_info['tracks'].get('length_meters', 0)
            
            # Update all graphs with comparison data
            if user_data and super_lap_data:
                self._update_graphs_with_comparison(user_data, super_lap_data, track_length)
                status_message = f"Telemetry comparison loaded: {' | '.join(status_parts)}"
                self.telemetry_status_label.setText(status_message)
                logger.info(status_message)
            elif user_data:
                self._update_graphs_with_single_data(user_data, track_length, is_user=True)
                status_message = f"Only user telemetry available: {status_parts[0]}"
                self.telemetry_status_label.setText(status_message)
                logger.warning(status_message)
            elif super_lap_data:
                self._update_graphs_with_single_data(super_lap_data, track_length, is_user=False)
                status_message = f"Only SuperLap telemetry available: {status_parts[1]}"
                self.telemetry_status_label.setText(status_message)
                logger.warning(status_message)
            
            logger.info("Telemetry comparison updated successfully")
            
        except Exception as e:
            error_message = f"Error processing telemetry comparison: {str(e)}"
            logger.error(error_message, exc_info=True)
            self.telemetry_status_label.setText(error_message)
    
    def _on_telemetry_comparison_error(self, error_message):
        """Handle telemetry comparison loading errors with enhanced messaging."""
        # Parse the error message to provide more specific feedback
        if "SuperLap" in error_message and "not found" in error_message:
            user_friendly_message = "SuperLap telemetry reconstruction failed - sector data may be incomplete"
        elif "No telemetry points found" in error_message:
            user_friendly_message = "No telemetry data available for the selected laps"
        elif "Authentication" in error_message:
            user_friendly_message = "Database authentication required for telemetry access"
        elif "sector combination" in error_message:
            user_friendly_message = "SuperLap sector data is missing or invalid"
        else:
            user_friendly_message = f"Telemetry loading error: {error_message}"
        
        self.telemetry_status_label.setText(user_friendly_message)
        logger.error(f"Telemetry comparison error: {error_message}")
        
        # If it's a SuperLap-specific error, suggest trying a different SuperLap
        if "SuperLap" in error_message:
            logger.info("Suggestion: Try selecting a different SuperLap or user lap for comparison")
    
    def _update_graphs_with_comparison(self, user_data, super_lap_data, track_length):
        """Update all graphs with comparison data using proper field mapping."""
        try:
            # Prepare lap data format for graph widgets with field mapping (same as telemetry tab)
            user_lap_data = None
            super_lap_data_mapped = None
            
            # Map user data fields
            if user_data and user_data.get('points'):
                mapped_points = []
                for point in user_data['points']:
                    mapped_point = point.copy()
                    
                    # Critical mapping: Convert database field names to graph widget expectations
                    if 'track_position' in mapped_point:
                        # Convert track_position to actual distance in meters
                        track_pos = mapped_point['track_position']
                        if 0 <= track_pos <= 1:
                            # Normalized position, convert to actual distance
                            mapped_point['LapDist'] = track_pos * track_length
                        else:
                            # Already in meters
                            mapped_point['LapDist'] = track_pos
                    
                    # Ensure all required fields exist with defaults and correct capitalization
                    mapped_point.setdefault('LapDist', 0)
                    
                    # Map lowercase to titlecase field names that graph widgets expect
                    if 'throttle' in mapped_point:
                        mapped_point['Throttle'] = mapped_point['throttle']
                    if 'brake' in mapped_point:
                        mapped_point['Brake'] = mapped_point['brake']
                    if 'steering' in mapped_point:
                        # Use raw steering values directly - they appear to already be normalized
                        raw_steering = mapped_point['steering']
                        if raw_steering is not None:
                            # Clamp to -1 to 1 range but don't scale since values are already appropriate
                            normalized_steering = max(-1.0, min(1.0, raw_steering))
                            mapped_point['Steering'] = normalized_steering
                        else:
                            mapped_point['Steering'] = 0.0
                    if 'speed' in mapped_point:
                        mapped_point['Speed'] = mapped_point['speed']
                    if 'gear' in mapped_point:
                        mapped_point['Gear'] = mapped_point['gear']
                    if 'rpm' in mapped_point:
                        mapped_point['RPM'] = mapped_point['rpm']
                    
                    # Set defaults for titlecase fields
                    mapped_point.setdefault('Throttle', 0)
                    mapped_point.setdefault('Brake', 0)
                    mapped_point.setdefault('Steering', 0)
                    mapped_point.setdefault('Speed', 0)
                    mapped_point.setdefault('timestamp', 0)
                    mapped_point.setdefault('rpm', 0)
                    mapped_point.setdefault('Gear', 0)
                    
                    mapped_points.append(mapped_point)
                
                user_lap_data = {'points': mapped_points}
                logger.info(f"Mapped {len(mapped_points)} points for user lap")
            
            # Map super lap data fields
            if super_lap_data and super_lap_data.get('points'):
                mapped_points = []
                for point in super_lap_data['points']:
                    mapped_point = point.copy()
                    
                    # Critical mapping: Convert database field names to graph widget expectations
                    if 'track_position' in mapped_point:
                        track_pos = mapped_point['track_position']
                        
                        # SUPERLAP FIX: After the database fix, superlap data is now always in actual meters
                        # Check if this looks like normalized data (0-1 range) vs actual distance
                        # For superlap data, we expect it to be in meters after the fix
                        if track_pos <= 1.0 and all(p.get('track_position', 0) <= 1.0 for p in super_lap_data['points'][:10]):
                            # This appears to be normalized data (0-1), convert to actual distance
                            mapped_point['LapDist'] = track_pos * track_length
                            logger.debug("SuperLap: Converting normalized position to meters")
                        else:
                            # This is already in meters (expected after the database fix)
                            mapped_point['LapDist'] = track_pos
                            logger.debug("SuperLap: Using position data already in meters")
                    
                    # Ensure all required fields exist with defaults and correct capitalization
                    mapped_point.setdefault('LapDist', 0)
                    
                    # Map lowercase to titlecase field names that graph widgets expect
                    if 'throttle' in mapped_point:
                        mapped_point['Throttle'] = mapped_point['throttle']
                    if 'brake' in mapped_point:
                        mapped_point['Brake'] = mapped_point['brake']
                    if 'steering' in mapped_point:
                        # Use raw steering values directly - they appear to already be normalized
                        raw_steering = mapped_point['steering']
                        if raw_steering is not None:
                            # Clamp to -1 to 1 range but don't scale since values are already appropriate
                            normalized_steering = max(-1.0, min(1.0, raw_steering))
                            mapped_point['Steering'] = normalized_steering
                        else:
                            mapped_point['Steering'] = 0.0
                    if 'speed' in mapped_point:
                        mapped_point['Speed'] = mapped_point['speed']
                    if 'gear' in mapped_point:
                        mapped_point['Gear'] = mapped_point['gear']
                    if 'rpm' in mapped_point:
                        mapped_point['RPM'] = mapped_point['rpm']
                    
                    # Set defaults for titlecase fields
                    mapped_point.setdefault('Throttle', 0)
                    mapped_point.setdefault('Brake', 0)
                    mapped_point.setdefault('Steering', 0)
                    mapped_point.setdefault('Speed', 0)
                    mapped_point.setdefault('timestamp', 0)
                    mapped_point.setdefault('rpm', 0)
                    mapped_point.setdefault('Gear', 0)
                    
                    mapped_points.append(mapped_point)
                
                super_lap_data_mapped = {'points': mapped_points}
                logger.info(f"Mapped {len(mapped_points)} points for super lap")
                
                # Log distance range for verification
                if mapped_points:
                    distances = [p.get('LapDist', 0) for p in mapped_points]
                    min_dist = min(distances)
                    max_dist = max(distances)
                    logger.info(f"SuperLap distance range: {min_dist:.1f}m to {max_dist:.1f}m (span: {max_dist - min_dist:.1f}m)")
            
            # Update graphs with properly mapped data and SuperLap-specific labels
            if user_lap_data and super_lap_data_mapped:
                # Update speed graph
                if hasattr(self, 'speed_graph'):
                    self.speed_graph.update_graph_comparison(user_lap_data, super_lap_data_mapped, track_length, label_a="Your Lap", label_b="SuperLap")
                
                # Update throttle graph
                if hasattr(self, 'throttle_graph'):
                    self.throttle_graph.update_graph_comparison(user_lap_data, super_lap_data_mapped, track_length, label_a="Your Lap", label_b="SuperLap")
                
                # Update brake graph
                if hasattr(self, 'brake_graph'):
                    self.brake_graph.update_graph_comparison(user_lap_data, super_lap_data_mapped, track_length, label_a="Your Lap", label_b="SuperLap")
                
                # Update steering graph
                if hasattr(self, 'steering_graph'):
                    self.steering_graph.update_graph_comparison(user_lap_data, super_lap_data_mapped, track_length, label_a="Your Lap", label_b="SuperLap")
                
                # Update gear graph
                if hasattr(self, 'gear_graph'):
                    self.gear_graph.update_graph_comparison(user_lap_data, super_lap_data_mapped, track_length, label_a="Your Lap", label_b="SuperLap")
                
        except Exception as e:
            logger.error(f"Error updating graphs with comparison data: {e}")
    
    def _update_graphs_with_single_data(self, lap_data, track_length, is_user=True):
        """Update all graphs with single lap data using proper field mapping."""
        try:
            # Map data fields (same as telemetry tab)
            mapped_lap_data = None
            
            if lap_data and lap_data.get('points'):
                mapped_points = []
                for point in lap_data['points']:
                    mapped_point = point.copy()
                    
                    # Critical mapping: Convert database field names to graph widget expectations
                    if 'track_position' in mapped_point:
                        # Convert track_position to actual distance in meters
                        track_pos = mapped_point['track_position']
                        if 0 <= track_pos <= 1:
                            # Normalized position, convert to actual distance
                            mapped_point['LapDist'] = track_pos * track_length
                        else:
                            # Already in meters
                            mapped_point['LapDist'] = track_pos
                    
                    # Ensure all required fields exist with defaults and correct capitalization
                    mapped_point.setdefault('LapDist', 0)
                    
                    # Map lowercase to titlecase field names that graph widgets expect
                    if 'throttle' in mapped_point:
                        mapped_point['Throttle'] = mapped_point['throttle']
                    if 'brake' in mapped_point:
                        mapped_point['Brake'] = mapped_point['brake']
                    if 'steering' in mapped_point:
                        # Use raw steering values directly - they appear to already be normalized
                        raw_steering = mapped_point['steering']
                        if raw_steering is not None:
                            # Clamp to -1 to 1 range but don't scale since values are already appropriate
                            normalized_steering = max(-1.0, min(1.0, raw_steering))
                            mapped_point['Steering'] = normalized_steering
                        else:
                            mapped_point['Steering'] = 0.0
                    if 'speed' in mapped_point:
                        mapped_point['Speed'] = mapped_point['speed']
                    if 'gear' in mapped_point:
                        mapped_point['Gear'] = mapped_point['gear']
                    if 'rpm' in mapped_point:
                        mapped_point['RPM'] = mapped_point['rpm']
                    
                    # Set defaults for titlecase fields
                    mapped_point.setdefault('Throttle', 0)
                    mapped_point.setdefault('Brake', 0)
                    mapped_point.setdefault('Steering', 0)
                    mapped_point.setdefault('Speed', 0)
                    mapped_point.setdefault('timestamp', 0)
                    mapped_point.setdefault('rpm', 0)
                    mapped_point.setdefault('Gear', 0)
                    
                    mapped_points.append(mapped_point)
                
                mapped_lap_data = {'points': mapped_points}
                logger.info(f"Mapped {len(mapped_points)} points for {'user' if is_user else 'super'} lap")
            
            # Update graphs with properly mapped data
            if mapped_lap_data:
                # Update speed graph
                if hasattr(self, 'speed_graph'):
                    self.speed_graph.update_graph(mapped_lap_data, track_length)
                
                # Update throttle graph
                if hasattr(self, 'throttle_graph'):
                    self.throttle_graph.update_graph(mapped_lap_data, track_length)
                
                # Update brake graph
                if hasattr(self, 'brake_graph'):
                    self.brake_graph.update_graph(mapped_lap_data, track_length)
                
                # Update steering graph
                if hasattr(self, 'steering_graph'):
                    self.steering_graph.update_graph(mapped_lap_data, track_length)
                
                # Update gear graph
                if hasattr(self, 'gear_graph'):
                    self.gear_graph.update_graph(mapped_lap_data, track_length)
                
        except Exception as e:
            logger.error(f"Error updating graphs with single data: {e}")
    
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
    
    def _run_superlap_diagnostics(self):
        """Run comprehensive diagnostics on the selected SuperLap."""
        try:
            super_lap_id = self.ml_lap_combo.currentData()
            
            if not super_lap_id:
                QMessageBox.information(self, "Diagnostics", "Please select a SuperLap first.")
                return
            
            # Create diagnostic dialog
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle("SuperLap Telemetry Diagnostics")
            dialog.setFixedSize(800, 600)
            
            layout = QVBoxLayout(dialog)
            
            # Text area for diagnostic output
            diagnostic_text = QTextEdit()
            diagnostic_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1a1a1a;
                    color: #e0e0e0;
                    border: 1px solid #444;
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                }
            """)
            layout.addWidget(diagnostic_text)
            
            # Close button
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            # Run diagnostics
            diagnostic_text.append("🔍 SUPERLAP TELEMETRY DIAGNOSTICS")
            diagnostic_text.append("=" * 50)
            diagnostic_text.append(f"SuperLap ID: {super_lap_id}")
            diagnostic_text.append("")
            
            # Get SuperLap info
            try:
                from trackpro.database.supabase_client import supabase as main_supabase
                
                if main_supabase and main_supabase.is_authenticated():
                    # Get SuperLap details
                    super_lap_result = (
                        main_supabase.client.table("super_laps_ml")
                        .select("*")
                        .eq("id", super_lap_id)
                        .execute()
                    )
                    
                    if super_lap_result.data:
                        super_lap = super_lap_result.data[0]
                        diagnostic_text.append("📊 SuperLap Details:")
                        diagnostic_text.append(f"   Car ID: {super_lap.get('car_id')}")
                        diagnostic_text.append(f"   Track ID: {super_lap.get('track_id')}")
                        diagnostic_text.append(f"   Total Time: {super_lap.get('total_time', 'N/A')}")
                        diagnostic_text.append(f"   Confidence Level: {super_lap.get('confidence_level', 'N/A')}")
                        diagnostic_text.append(f"   Created: {super_lap.get('created_at', 'N/A')}")
                        diagnostic_text.append("")
                        
                        # Check sector combination
                        sector_combination = super_lap.get('sector_combination')
                        diagnostic_text.append("🏁 Sector Combination Analysis:")
                        if sector_combination:
                            diagnostic_text.append(f"   Type: {type(sector_combination).__name__}")
                            if isinstance(sector_combination, list):
                                diagnostic_text.append(f"   Format: List of lap/sector references")
                                diagnostic_text.append(f"   Count: {len(sector_combination)} entries")
                                for i, entry in enumerate(sector_combination[:3]):  # Show first 3
                                    diagnostic_text.append(f"   Entry {i+1}: {entry}")
                                if len(sector_combination) > 3:
                                    diagnostic_text.append(f"   ... and {len(sector_combination) - 3} more")
                            elif isinstance(sector_combination, dict):
                                diagnostic_text.append(f"   Format: Dictionary of sector times")
                                diagnostic_text.append(f"   Keys: {list(sector_combination.keys())}")
                            else:
                                diagnostic_text.append(f"   Format: Unknown ({sector_combination})")
                        else:
                            diagnostic_text.append("   ❌ No sector combination data found!")
                        diagnostic_text.append("")
                        
                        # Try telemetry reconstruction
                        diagnostic_text.append("🔧 Telemetry Reconstruction Test:")
                        try:
                            from Supabase.database import get_super_lap_telemetry_points
                            
                            result = get_super_lap_telemetry_points(super_lap_id)
                            if result[0] is not None:
                                points = result[0]
                                diagnostic_text.append(f"   ✅ Success: {len(points)} telemetry points retrieved")
                                diagnostic_text.append(f"   Message: {result[1]}")
                                
                                if points:
                                    sample_point = points[0]
                                    diagnostic_text.append(f"   Sample point fields: {list(sample_point.keys())}")
                                    diagnostic_text.append(f"   Track position range: {min(p.get('track_position', 0) for p in points):.3f} - {max(p.get('track_position', 0) for p in points):.3f}")
                                    
                                    # Check for sector data in points
                                    has_sector_data = any('current_sector' in p for p in points)
                                    diagnostic_text.append(f"   Has sector data: {has_sector_data}")
                                    
                            else:
                                diagnostic_text.append(f"   ❌ Failed: {result[1]}")
                                
                        except Exception as e:
                            diagnostic_text.append(f"   ❌ Exception: {str(e)}")
                        
                        diagnostic_text.append("")
                        
                        # Check for related telemetry data
                        car_id = super_lap.get('car_id')
                        track_id = super_lap.get('track_id')
                        
                        if car_id and track_id:
                            diagnostic_text.append("🔍 Related Data Check:")
                            
                            # Check for sessions
                            sessions_result = (
                                main_supabase.client.table("sessions")
                                .select("id,created_at")
                                .eq("car_id", car_id)
                                .eq("track_id", track_id)
                                .limit(5)
                                .order("created_at", desc=True)
                                .execute()
                            )
                            
                            if sessions_result.data:
                                diagnostic_text.append(f"   Sessions found: {len(sessions_result.data)}")
                                for session in sessions_result.data[:3]:
                                    diagnostic_text.append(f"     - {session['id']} ({session['created_at']})")
                                
                                # Check laps in first session
                                first_session_id = sessions_result.data[0]['id']
                                laps_result = (
                                    main_supabase.client.table("laps")
                                    .select("id,lap_time,is_valid")
                                    .eq("session_id", first_session_id)
                                    .limit(3)
                                    .execute()
                                )
                                
                                if laps_result.data:
                                    diagnostic_text.append(f"   Laps in latest session: {len(laps_result.data)}")
                                    for lap in laps_result.data:
                                        # Check for telemetry points
                                        telemetry_count = (
                                            main_supabase.client.table("telemetry_points")
                                            .select("id", count="exact")
                                            .eq("lap_id", lap['id'])
                                            .execute()
                                        )
                                        count = telemetry_count.count if telemetry_count.count else 0
                                        diagnostic_text.append(f"     - Lap {lap['id']}: {count} telemetry points")
                                
                            else:
                                diagnostic_text.append("   ❌ No sessions found for this car/track combination")
                    
                    else:
                        diagnostic_text.append("❌ SuperLap not found in database!")
                
                else:
                    diagnostic_text.append("❌ Database connection not available!")
                    
            except Exception as e:
                diagnostic_text.append(f"❌ Diagnostic error: {str(e)}")
                import traceback
                diagnostic_text.append("\nFull traceback:")
                diagnostic_text.append(traceback.format_exc())
            
            diagnostic_text.append("")
            diagnostic_text.append("🎯 Recommendations:")
            diagnostic_text.append("1. Check if sector combination data is properly formatted")
            diagnostic_text.append("2. Verify that referenced laps have telemetry data")
            diagnostic_text.append("3. Ensure current_sector field is populated in telemetry points")
            diagnostic_text.append("4. Try selecting a different SuperLap if this one fails")
            
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error running SuperLap diagnostics: {e}", exc_info=True)
            QMessageBox.critical(self, "Diagnostic Error", f"Error running diagnostics: {str(e)}")
    
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

    def set_telemetry_monitor(self, monitor: 'TelemetryMonitorWorker'):
        """Sets the telemetry monitor instance for the widget."""
        self.telemetry_monitor = monitor
        logger.info("Telemetry monitor instance set in SuperLapWidget.")

    def toggle_ai_coaching(self, checked):
        """Starts or stops the AI coaching session."""
        if not self.telemetry_monitor:
            logger.error("Cannot start coaching: Telemetry monitor is not available.")
            self.coach_button.setChecked(False)
            return

        if checked:
            if not self.current_ml_lap:
                logger.warning("No SuperLap selected. Cannot start coaching.")
                QMessageBox.warning(self, "No SuperLap", "Please select a SuperLap before starting the AI coach.")
                self.coach_button.setChecked(False)
                return

            superlap_id = self.current_ml_lap.get('id')
            if not superlap_id:
                logger.error("Selected SuperLap has no ID. Cannot start coaching.")
                self.coach_button.setChecked(False)
                return
            
            logger.info(f"Starting AI coaching with superlap_id: {superlap_id}")
            try:
                self.telemetry_monitor.ai_coach = AICoach(superlap_id=superlap_id)
                self.telemetry_monitor.start_monitoring()
                self.coach_button.setText("🛑 Stop AI Coach")
                self.coach_button.setStyleSheet("padding: 5px 10px; background-color: #D22B2B; color: white; font-weight: bold;")
            except Exception as e:
                logger.error(f"Failed to start AI Coach: {e}", exc_info=True)
                QMessageBox.critical(self, "Error", f"Failed to start AI Coach: {e}")
                self.coach_button.setChecked(False)
        else:
            logger.info("Stopping AI coaching.")
            self.telemetry_monitor.stop_monitoring()
            self.telemetry_monitor.ai_coach = None
            self.coach_button.setText("🎙️ Start AI Coach")
            self.coach_button.setStyleSheet("padding: 5px 10px; background-color: #0055A4; color: white; font-weight: bold;")