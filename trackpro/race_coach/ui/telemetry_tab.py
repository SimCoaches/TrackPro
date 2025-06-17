"""Telemetry tab for Race Coach - Lap comparison and telemetry visualization.

This module contains the telemetry comparison tab that allows drivers to compare
telemetry data between different laps.
"""

import logging
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFrame, QGridLayout, QSizePolicy, QDialog,
    QTextEdit, QDialogButtonBox, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush

# Import graph widgets from the widgets directory
from trackpro.race_coach.widgets.throttle_graph import ThrottleGraphWidget
from trackpro.race_coach.widgets.brake_graph import BrakeGraphWidget
from trackpro.race_coach.widgets.steering_graph import SteeringGraphWidget
from trackpro.race_coach.widgets.speed_graph import SpeedGraphWidget

logger = logging.getLogger(__name__)


class TelemetryFetchWorker(QObject):
    """Worker to fetch telemetry data in the background."""
    
    finished = pyqtSignal(object, object)  # (left_data, right_data)
    error = pyqtSignal(str, str)  # (left_error, right_error)

    def __init__(self, left_lap_id, right_lap_id):
        super().__init__()
        self.left_lap_id = left_lap_id
        self.right_lap_id = right_lap_id
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
        """Fetch telemetry data for both laps."""
        try:
            from Supabase.database import get_telemetry_points
            
            left_result = None
            right_result = None
            left_error = None
            right_error = None
            
            # Fetch left lap data
            if self.left_lap_id and not self.is_cancelled:
                try:
                    # get_telemetry_points returns (data, message) tuple
                    left_result_tuple = get_telemetry_points(self.left_lap_id)
                    if left_result_tuple[0] is not None:  # Check if data is not None
                        left_points = left_result_tuple[0]  # Extract data from tuple
                        left_stats = self._calculate_lap_stats(left_points)
                        left_result = {
                            'points': left_points,
                            'stats': left_stats
                        }
                    else:
                        left_error = left_result_tuple[1]  # Extract error message from tuple
                except Exception as e:
                    left_error = str(e)
                    logger.error(f"Error fetching left lap telemetry: {e}")
            
            # Fetch right lap data
            if self.right_lap_id and not self.is_cancelled:
                try:
                    # get_telemetry_points returns (data, message) tuple
                    right_result_tuple = get_telemetry_points(self.right_lap_id)
                    if right_result_tuple[0] is not None:  # Check if data is not None
                        right_points = right_result_tuple[0]  # Extract data from tuple
                        right_stats = self._calculate_lap_stats(right_points)
                        right_result = {
                            'points': right_points,
                            'stats': right_stats
                        }
                    else:
                        right_error = right_result_tuple[1]  # Extract error message from tuple
                except Exception as e:
                    right_error = str(e)
                    logger.error(f"Error fetching right lap telemetry: {e}")
            
            if not self.is_cancelled:
                if left_error or right_error:
                    self.error.emit(left_error or "", right_error or "")
                else:
                    self.finished.emit(left_result, right_result)
                    
        except Exception as e:
            logger.error(f"Error in telemetry fetch worker: {e}")
            self.error.emit(str(e), str(e))

    def cancel(self):
        self.is_cancelled = True

    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


class InitialLoadWorker(QObject):
    """Worker to load initial session and lap lists in the background."""

    sessions_loaded = pyqtSignal(list, str)  # (sessions_data, message)
    laps_loaded = pyqtSignal(list, str)  # (laps_data, message)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_cancelled = False

    def run(self):
        """Load sessions and laps from database."""
        try:
            from Supabase.database import get_sessions, get_laps
            
            # Load sessions
            if not self.is_cancelled:
                try:
                    # get_sessions returns (data, message) tuple
                    # Get ALL user sessions (like SuperLap tab) - don't filter by only_with_laps as it's unreliable
                    sessions_result = get_sessions(user_only=True)
                    if sessions_result[0] is not None:  # Check if data is not None
                        sessions = sessions_result[0]  # Extract data from tuple
                        self.sessions_loaded.emit(sessions, "Sessions with laps loaded successfully")
                    else:
                        self.sessions_loaded.emit([], "No sessions with laps found")
                        sessions = []  # Set sessions to empty list for the next step
                except Exception as e:
                    logger.error(f"Error loading sessions: {e}")
                    self.error.emit(f"Error loading sessions: {str(e)}")
                    sessions = []  # Set sessions to empty list for the next step
            
            # Load laps for the most recent session if available
            if not self.is_cancelled and sessions:
                try:
                    session_id = sessions[0].get('id')
                    # get_laps returns (data, message) tuple  
                    laps_result = get_laps(session_id=session_id)
                    if laps_result[0] is not None:  # Check if data is not None
                        laps = laps_result[0]  # Extract data from tuple
                        self.laps_loaded.emit(laps, "Laps loaded successfully")
                    else:
                        self.laps_loaded.emit([], "No laps found")
                except Exception as e:
                    logger.error(f"Error loading laps: {e}")
                    self.error.emit(f"Error loading laps: {str(e)}")
            
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"Error in initial load worker: {e}")
            self.error.emit(str(e))
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True

    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


class TelemetryComparisonWidget(QWidget):
    """Widget for comparing telemetry between two laps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.left_driver = {"name": "Driver A", "lastname": "", "team": ""}
        self.right_driver = {"name": "Driver B", "lastname": "", "team": ""}
        self.setup_ui()

    def setup_ui(self):
        """Set up the telemetry comparison UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Driver comparison header
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        header_frame.setStyleSheet("background-color: #2D2D30; border-radius: 5px;")
        header_layout = QHBoxLayout(header_frame)

        # Left driver info
        self.left_driver_label = QLabel("Driver A")
        self.left_driver_label.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.left_driver_label)

        header_layout.addStretch()

        # VS label
        vs_label = QLabel("VS")
        vs_label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        header_layout.addWidget(vs_label)

        header_layout.addStretch()

        # Right driver info
        self.right_driver_label = QLabel("Driver B")
        self.right_driver_label.setStyleSheet("color: #4ECDC4; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.right_driver_label)

        layout.addWidget(header_frame)

    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if time_in_seconds is None or time_in_seconds < 0:
            return "--:--.---"
        minutes = int(time_in_seconds // 60)
        seconds = time_in_seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"

    def get_track_length(self):
        """Get the current track length from parent if available."""
        if hasattr(self.parent_widget, 'get_track_length'):
            return self.parent_widget.get_track_length()
        return None

    def set_driver_data(self, is_left_driver, data):
        """Update driver data and refresh display."""
        driver = self.left_driver if is_left_driver else self.right_driver

        if "name" in data:
            name_parts = data["name"].split()
            if len(name_parts) > 1:
                driver["name"] = name_parts[0]
                driver["lastname"] = " ".join(name_parts[1:])
            else:
                driver["name"] = data["name"]
                driver["lastname"] = ""

        if "team" in data:
            driver["team"] = data["team"]

        self.update_driver_display(is_left_driver)

    def update_driver_display(self, is_left_driver):
        """Update the driver display label."""
        driver = self.left_driver if is_left_driver else self.right_driver
        label = self.left_driver_label if is_left_driver else self.right_driver_label

        display_name = driver["name"]
        if driver["lastname"]:
            display_name += f" {driver['lastname']}"

        label.setText(display_name)

    def set_track_data(self, track_map_points, turn_data, sector_data):
        """Set track data for visualization."""
        # This would be implemented if we had track visualization
        pass

    def paintEvent(self, event):
        """Custom paint event for any additional visualization."""
        # Currently not needed, but can be used for custom drawing
        super().paintEvent(event)


class DeltaGraphWidget(QWidget):
    """Widget to display lap time delta between two drivers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.delta_data = []
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)

    def set_data(self, delta_data):
        """Set the delta data to display."""
        if delta_data and isinstance(delta_data, list):
            # Filter out None values and ensure all are numeric
            self.delta_data = [d for d in delta_data if isinstance(d, (int, float))]
        else:
            self.delta_data = []
        self.update()

    def paintEvent(self, event):
        """Paint the delta graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Background
        painter.fillRect(0, 0, width, height, QColor(34, 34, 34))

        if not self.delta_data:
            # Draw "No Data" message
            painter.setPen(QPen(QColor(128, 128, 128)))
            painter.drawText(0, 0, width, height, Qt.AlignCenter, "No Delta Data")
            return

        # Draw grid
        painter.setPen(QPen(QColor(64, 64, 64), 1))
        
        # Horizontal center line
        center_y = height // 2
        painter.drawLine(0, center_y, width, center_y)

        # Vertical grid lines
        grid_spacing = width // 10
        for i in range(1, 10):
            x = i * grid_spacing
            painter.drawLine(x, 0, x, height)

        # Find max delta for scaling
        max_delta = max(abs(d) for d in self.delta_data) if self.delta_data else 1
        if max_delta == 0:
            max_delta = 1

        # Draw delta line
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        
        points_per_pixel = len(self.delta_data) / width if width > 0 else 1
        
        for x in range(width):
            # Calculate which data points to consider for this pixel
            start_idx = int(x * points_per_pixel)
            end_idx = int((x + 1) * points_per_pixel)
            
            if start_idx < len(self.delta_data) and end_idx <= len(self.delta_data):
                # Get the average delta for this pixel range
                if end_idx > start_idx:
                    avg_delta = sum(self.delta_data[start_idx:end_idx]) / (end_idx - start_idx)
                else:
                    avg_delta = self.delta_data[start_idx]
                
                # Scale to display
                y = center_y - (avg_delta / max_delta) * (height // 2 - 10)
                
                # Draw line segment
                if x > 0:
                    painter.drawLine(x - 1, prev_y, x, y)
                
                prev_y = y

        # Draw labels
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.drawText(5, 15, f"+{max_delta:.2f}s")
        painter.drawText(5, height - 5, f"-{max_delta:.2f}s")


class TelemetryTab(QWidget):
    """Main telemetry tab widget containing all telemetry comparison functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        
        # Track active threads for cleanup
        self.active_threads = []
        self._is_being_destroyed = False
        
        # Initialize data
        self.sessions = []
        self.laps = []
        self.current_session_id = None
        
        self.setup_ui()
        
        # Start initial data loading
        QTimer.singleShot(100, self._start_initial_data_loading)

    def setup_ui(self):
        """Set up the telemetry tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)  # Much tighter spacing
        layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins

        # COMPACT TOP CONTROLS - minimal space like RaceStudio3
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
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
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 1px solid #999;
                width: 0px;
                height: 0px;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid #999;
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
            QPushButton:pressed {
                background-color: #353535;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(6, 4, 6, 4)
        controls_layout.setSpacing(8)

        # Session selection - very compact
        session_label = QLabel("Session:")
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(300)
        self.session_combo.setMaximumWidth(400)
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)

        # Lap selection - inline and compact
        lap_a_label = QLabel("Lap A:")
        self.left_lap_combo = QComboBox()
        self.left_lap_combo.setMinimumWidth(120)
        self.left_lap_combo.setMaximumWidth(150)
        self.left_lap_combo.currentIndexChanged.connect(self.on_lap_selection_changed)

        vs_label = QLabel("vs")
        vs_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px; margin: 0px 4px;")

        lap_b_label = QLabel("Lap B:")
        self.right_lap_combo = QComboBox()
        self.right_lap_combo.setMinimumWidth(120)
        self.right_lap_combo.setMaximumWidth(150)
        self.right_lap_combo.currentIndexChanged.connect(self.on_lap_selection_changed)

        # Compact buttons
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("Refresh session and lap lists from database")
        self.refresh_button.setMaximumWidth(30)
        self.refresh_button.clicked.connect(self.refresh_session_and_lap_lists)

        self.reset_connection_button = QPushButton("🔌")
        self.reset_connection_button.setToolTip("Reset iRacing connection if disconnected")
        self.reset_connection_button.setMaximumWidth(30)
        self.reset_connection_button.clicked.connect(self.reset_iracing_connection)

        # Status label
        self.graph_status_label = QLabel()
        self.graph_status_label.setAlignment(Qt.AlignLeft)
        self.graph_status_label.setStyleSheet("""
            QLabel {
                color: #ffa500;
                font-weight: bold;
                background: transparent;
                padding-left: 8px;
                font-size: 11px;
            }
        """)
        self.graph_status_label.setVisible(False)

        # Add all controls to layout in a single row
        controls_layout.addWidget(session_label)
        controls_layout.addWidget(self.session_combo)
        controls_layout.addWidget(QLabel("|"))  # Separator
        controls_layout.addWidget(lap_a_label)
        controls_layout.addWidget(self.left_lap_combo)
        controls_layout.addWidget(vs_label)
        controls_layout.addWidget(lap_b_label)
        controls_layout.addWidget(self.right_lap_combo)
        controls_layout.addWidget(QLabel("|"))  # Separator
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addWidget(self.reset_connection_button)
        controls_layout.addWidget(self.graph_status_label)
        controls_layout.addStretch()

        layout.addWidget(controls_frame)

        # Loading indicator - much more compact
        self.loading_label = QLabel("🔄 Loading...")
        self.loading_label.setAlignment(Qt.AlignCenter)
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
        layout.insertWidget(1, self.loading_label)

        # COMPACT GRAPHS CONTAINER - like RaceStudio3 stacked view
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
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
            QScrollBar::handle:vertical:hover {
                background-color: #79c0ff;
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
        graphs_layout.setSpacing(3)  # Minimal spacing between graphs

        # COMPACT GRAPH SETTINGS - Larger heights since we removed headers
        base_graph_style = """
            QWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 4px;
            }
        """

        # LARGER heights now that we removed the header waste - more like RaceStudio3
        GRAPH_HEIGHT = 150  # Increased from 120 since we removed title headers
        graph_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Create graph containers WITHOUT title headers to maximize drawing area
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
            container_layout.setContentsMargins(2, 2, 2, 2)
            container_layout.setSpacing(0)  # No spacing for titles

            # NO TITLE LABEL - maximizes graph drawing area
            graph_widget.setFixedHeight(GRAPH_HEIGHT)
            graph_widget.setSizePolicy(graph_size_policy)
            graph_widget.setStyleSheet(base_graph_style)
            container_layout.addWidget(graph_widget)

            return container

        # All graphs without title headers - maximize drawing area
        self.throttle_graph = ThrottleGraphWidget(self)
        throttle_container = create_graph_container(self.throttle_graph)
        graphs_layout.addWidget(throttle_container)

        self.brake_graph = BrakeGraphWidget(self)
        brake_container = create_graph_container(self.brake_graph)
        graphs_layout.addWidget(brake_container)

        self.steering_graph = SteeringGraphWidget(self)
        steering_container = create_graph_container(self.steering_graph)
        graphs_layout.addWidget(steering_container)

        self.speed_graph = SpeedGraphWidget(self)
        speed_container = create_graph_container(self.speed_graph)
        graphs_layout.addWidget(speed_container)

        # Minimal bottom padding
        graphs_layout.addStretch(0)

        # Set the graphs container as the scroll area widget
        scroll_area.setWidget(graphs_container)
        layout.addWidget(scroll_area)

    def _start_initial_data_loading(self):
        """Start loading initial session and lap data in the background."""
        if self._is_being_destroyed:
            return
            
        # Show loading indicator
        self.loading_label.setVisible(True)
        
        # Create worker thread
        initial_load_thread = QThread()
        initial_load_worker = InitialLoadWorker()
        initial_load_worker.moveToThread(initial_load_thread)
        
        # Track this thread
        thread_id = f'initial_load_{id(initial_load_thread)}'
        self.active_threads.append((thread_id, initial_load_thread, initial_load_worker))
        
        # Connect signals
        initial_load_thread.started.connect(initial_load_worker.run)
        initial_load_worker.sessions_loaded.connect(self._on_sessions_loaded)
        initial_load_worker.laps_loaded.connect(self._on_laps_loaded)
        initial_load_worker.error.connect(self._on_initial_load_error)
        initial_load_worker.finished.connect(initial_load_thread.quit)
        initial_load_worker.finished.connect(initial_load_worker.deleteLater)
        initial_load_thread.finished.connect(initial_load_thread.deleteLater)
        initial_load_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
        initial_load_thread.finished.connect(self._on_initial_load_finished)
        
        # Start the thread
        initial_load_thread.start()

    def _on_sessions_loaded(self, sessions, message):
        """Handle loaded sessions from worker thread."""
        self.sessions = sessions
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

    def _on_laps_loaded(self, laps, message):
        """Handle loaded laps from worker thread."""
        self.laps = laps
        self._update_lap_combos()

    def _on_initial_load_error(self, error_message):
        """Handle initial load errors."""
        logger.error(f"Initial load error: {error_message}")
        self.loading_label.setText(f"Error loading data: {error_message}")

    def _on_initial_load_finished(self):
        """Handle initial load completion."""
        self.loading_label.setVisible(False)

    def _format_session_display(self, session):
        """Format session data for display in combo box."""
        try:
            track_name = session.get('track_name', 'Unknown Track')
            car_name = session.get('car_name', 'Unknown Car')
            created_at = session.get('created_at', '')
            
            # Format date
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                display_text = f"{timestamp.strftime('%Y-%m-%d %H:%M')} - {track_name} ({car_name})"
            except:
                display_text = f"{created_at} - {track_name} ({car_name})"
            
            return display_text
        except Exception as e:
            logger.error(f"Error formatting session display: {e}")
            return f"Session {session.get('id', 'Unknown')}"

    def _update_lap_combos(self):
        """Update lap combo boxes with current lap data."""
        self.left_lap_combo.clear()
        self.right_lap_combo.clear()
        
        if self.laps:
            for lap in self.laps:
                lap_num = lap.get('lap_number', 0)
                lap_time = lap.get('lap_time', 0)
                lap_state = lap.get('lap_state', 'unknown')
                display_text = self._format_lap_display(lap_num, lap_time, lap_state)
                
                self.left_lap_combo.addItem(display_text, lap)
                self.right_lap_combo.addItem(display_text, lap)
            
            # Select different laps by default if possible
            if self.left_lap_combo.count() > 0:
                self.left_lap_combo.setCurrentIndex(0)
            if self.right_lap_combo.count() > 1:
                self.right_lap_combo.setCurrentIndex(1)
        else:
            self.left_lap_combo.addItem("No laps available", None)
            self.right_lap_combo.addItem("No laps available", None)

    def _format_lap_display(self, lap_num, lap_time, lap_state=None):
        """Format lap data for display."""
        time_str = self._format_time(lap_time) if lap_time > 0 else "Invalid"
        display_text = f"Lap {lap_num} - {time_str}"
        
        if lap_state and lap_state != 'complete':
            display_text += f" ({lap_state})"
        
        return display_text

    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if time_in_seconds is None or time_in_seconds < 0:
            return "--:--.---"
        minutes = int(time_in_seconds // 60)
        seconds = time_in_seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"

    def on_session_changed(self):
        """Handle session selection change."""
        current_data = self.session_combo.currentData()
        if current_data:
            self.current_session_id = current_data.get('id')
            self._load_laps_for_session(self.current_session_id)

    def on_lap_selection_changed(self):
        """Handle lap selection change - automatically compare."""
        left_data = self.left_lap_combo.currentData()
        right_data = self.right_lap_combo.currentData()
        
        if left_data and right_data:
            left_lap_id = left_data.get('id')
            right_lap_id = right_data.get('id')
            
            if left_lap_id and right_lap_id:
                self._compare_laps(left_lap_id, right_lap_id)

    def _load_laps_for_session(self, session_id):
        """Load laps for the selected session."""
        if not session_id:
            return
            
        try:
            from Supabase.database import get_laps
            logger.info(f"Loading laps for session: {session_id}")
            
            # get_laps returns (data, message) tuple
            laps_result = get_laps(session_id=session_id)
            logger.info(f"get_laps returned: data={laps_result[0] is not None}, message='{laps_result[1]}'")
            
            if laps_result[0] is not None:  # Check if data is not None
                self.laps = laps_result[0]  # Extract data from tuple
                logger.info(f"Found {len(self.laps)} laps for session {session_id}")
                if self.laps:
                    for i, lap in enumerate(self.laps[:3]):  # Log first 3 laps for debugging
                        logger.info(f"Lap {i}: id={lap.get('id')}, lap_number={lap.get('lap_number')}, lap_time={lap.get('lap_time')}, is_valid={lap.get('is_valid')}")
            else:
                logger.warning(f"get_laps returned None for session {session_id}: {laps_result[1]}")
                self.laps = []
            self._update_lap_combos()
        except Exception as e:
            logger.error(f"Error loading laps: {e}")
            self.laps = []
            self._update_lap_combos()

    def _compare_laps(self, left_lap_id, right_lap_id):
        """Compare two laps by fetching their telemetry data."""
        if self._is_being_destroyed:
            return
            
        # Show loading state
        self.graph_status_label.setText("Loading telemetry data...")
        self.graph_status_label.setVisible(True)
        
        # Create worker thread
        telemetry_thread = QThread()
        telemetry_worker = TelemetryFetchWorker(left_lap_id, right_lap_id)
        telemetry_worker.moveToThread(telemetry_thread)
        
        # Track this thread
        thread_id = f'telemetry_{id(telemetry_thread)}'
        self.active_threads.append((thread_id, telemetry_thread, telemetry_worker))
        
        # Connect signals
        telemetry_thread.started.connect(telemetry_worker.run)
        telemetry_worker.finished.connect(self._on_telemetry_loaded)
        telemetry_worker.error.connect(self._on_telemetry_error)
        telemetry_worker.finished.connect(telemetry_thread.quit)
        telemetry_worker.finished.connect(telemetry_worker.deleteLater)
        telemetry_thread.finished.connect(telemetry_thread.deleteLater)
        telemetry_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
        
        # Start the thread
        telemetry_thread.start()

    def _on_telemetry_loaded(self, left_data, right_data):
        """Handle loaded telemetry data."""
        self.graph_status_label.setVisible(False)
        
        # Get track length for the graphs
        track_length = self.get_track_length() or 1000  # Default to 1000m if not available
        
        # Prepare lap data format for graph widgets with field mapping
        left_lap_data = None
        right_lap_data = None
        
        if left_data and left_data.get('points'):
            # Map database field names to what graph widgets expect
            mapped_points = []
            for point in left_data['points']:
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
                    # Raw values like 0.167 are appropriate for the -1 to 1 graph range
                    raw_steering = mapped_point['steering']
                    if raw_steering is not None:
                        # Clamp to -1 to 1 range but don't scale since values are already appropriate
                        normalized_steering = max(-1.0, min(1.0, raw_steering))
                        mapped_point['Steering'] = normalized_steering
                    else:
                        mapped_point['Steering'] = 0.0
                if 'speed' in mapped_point:
                    mapped_point['Speed'] = mapped_point['speed']
                
                # Set defaults for titlecase fields
                mapped_point.setdefault('Throttle', 0)
                mapped_point.setdefault('Brake', 0) 
                mapped_point.setdefault('Steering', 0)
                mapped_point.setdefault('Speed', 0)
                mapped_point.setdefault('timestamp', 0)
                mapped_point.setdefault('rpm', 0)
                
                mapped_points.append(mapped_point)
            
            left_lap_data = {'points': mapped_points}
            logger.info(f"Mapped {len(mapped_points)} points for left lap (first point LapDist: {mapped_points[0].get('LapDist', 'missing') if mapped_points else 'no points'})")
            
        if right_data and right_data.get('points'):
            # Map database field names to what graph widgets expect
            mapped_points = []
            for point in right_data['points']:
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
                    # Raw values like 0.167 are appropriate for the -1 to 1 graph range
                    raw_steering = mapped_point['steering']
                    if raw_steering is not None:
                        # Clamp to -1 to 1 range but don't scale since values are already appropriate
                        normalized_steering = max(-1.0, min(1.0, raw_steering))
                        mapped_point['Steering'] = normalized_steering
                    else:
                        mapped_point['Steering'] = 0.0
                if 'speed' in mapped_point:
                    mapped_point['Speed'] = mapped_point['speed']
                
                # Set defaults for titlecase fields
                mapped_point.setdefault('Throttle', 0)
                mapped_point.setdefault('Brake', 0)
                mapped_point.setdefault('Steering', 0)
                mapped_point.setdefault('Speed', 0)
                mapped_point.setdefault('timestamp', 0)
                mapped_point.setdefault('rpm', 0)
                
                mapped_points.append(mapped_point)
            
            right_lap_data = {'points': mapped_points}
            logger.info(f"Mapped {len(mapped_points)} points for right lap (first point LapDist: {mapped_points[0].get('LapDist', 'missing') if mapped_points else 'no points'})")
        
        # Update graphs based on whether we have comparison data or single lap
        if left_lap_data and right_lap_data:
            # Log first point data for debugging
            if left_lap_data['points']:
                first_point = left_lap_data['points'][0]
                logger.info(f"DEBUG: First left lap point fields: {list(first_point.keys())}")
                logger.info(f"DEBUG: First left lap point values - Throttle: {first_point.get('Throttle', 'MISSING')}, Brake: {first_point.get('Brake', 'MISSING')}, Steering: {first_point.get('Steering', 'MISSING')}, Speed: {first_point.get('Speed', 'MISSING')}")
            
            # Comparison mode - update all graphs with both laps
            if hasattr(self, 'throttle_graph'):
                self.throttle_graph.update_graph_comparison(left_lap_data, right_lap_data, track_length)
            
            if hasattr(self, 'brake_graph'):
                self.brake_graph.update_graph_comparison(left_lap_data, right_lap_data, track_length)
                
            if hasattr(self, 'steering_graph'):
                self.steering_graph.update_graph_comparison(left_lap_data, right_lap_data, track_length)
                
            if hasattr(self, 'speed_graph'):
                self.speed_graph.update_graph_comparison(left_lap_data, right_lap_data, track_length)
                
        elif left_lap_data:
            # Single lap mode - just show left lap
            if hasattr(self, 'throttle_graph'):
                self.throttle_graph.update_graph(left_lap_data, track_length)
            
            if hasattr(self, 'brake_graph'):
                self.brake_graph.update_graph(left_lap_data, track_length)
                
            if hasattr(self, 'steering_graph'):
                self.steering_graph.update_graph(left_lap_data, track_length)
                
            if hasattr(self, 'speed_graph'):
                self.speed_graph.update_graph(left_lap_data, track_length)
        else:
            # No valid data - clear graphs
            logger.warning("No valid telemetry data to display")
            self.graph_status_label.setText("No valid telemetry data")
            self.graph_status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            self.graph_status_label.setVisible(True)

    def _on_telemetry_error(self, left_error, right_error):
        """Handle telemetry loading errors."""
        error_msg = "Error loading telemetry: "
        if left_error:
            error_msg += f"Left lap: {left_error} "
        if right_error:
            error_msg += f"Right lap: {right_error}"
        
        self.graph_status_label.setText(error_msg)
        self.graph_status_label.setStyleSheet("color: #FF5555; font-weight: bold;")

    def refresh_session_and_lap_lists(self):
        """Refresh both session and lap lists."""
        self._start_initial_data_loading()

    def reset_iracing_connection(self):
        """Reset iRacing connection - delegate to parent if available."""
        if hasattr(self.parent_widget, 'reset_iracing_connection'):
            self.parent_widget.reset_iracing_connection()
        else:
            QMessageBox.information(self, "Reset Connection", 
                                  "iRacing connection reset functionality not available in this context.")

    def get_track_length(self):
        """Get track length from current session if available."""
        if self.current_session_id and self.sessions:
            for session in self.sessions:
                if session.get('id') == self.current_session_id:
                    return session.get('track_length', None)
        return None

    def _remove_thread_from_tracking(self, thread_id):
        """Remove a thread from the active threads list."""
        self.active_threads = [(tid, t, w) for tid, t, w in self.active_threads if tid != thread_id]

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