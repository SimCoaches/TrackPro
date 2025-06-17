"""Driver Coaching Overview - Performance tracking and insights dashboard.

This module contains the overview tab that displays meaningful performance statistics,
progress tracking, and coaching insights rather than redundant live telemetry data.
"""

import logging
import math
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QSizePolicy, QPushButton, QScrollArea, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPixmap
from .coaching_data_manager import CoachingDataManager

logger = logging.getLogger(__name__)


class OverviewTab(QWidget):
    """Driver coaching overview displaying performance insights and progress tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.current_session_stats = None
        self.historical_data = None
        
        # Initialize data manager
        supabase_client = None
        user_id = None
        if hasattr(parent, 'supabase_client'):
            supabase_client = parent.supabase_client
        if hasattr(parent, 'user_id'):
            user_id = parent.user_id
            
        self.data_manager = CoachingDataManager(supabase_client, user_id)
        
        self.setup_ui()
        
        # Timer to refresh data periodically
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_coaching_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        # Initial data load
        self.refresh_coaching_data()

    def setup_ui(self):
        """Set up the coaching overview UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Title and header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Driver Coaching Overview")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #00ff88;
            padding: 10px 0px;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        refresh_button = QPushButton("Refresh Data")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
        """)
        refresh_button.clicked.connect(self.refresh_coaching_data)
        header_layout.addWidget(refresh_button)
        
        main_layout.addLayout(header_layout)

        # Create scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(20)

        # Session Summary Section
        session_section = self.create_session_summary_section()
        scroll_layout.addWidget(session_section)

        # Performance Metrics Section
        performance_section = self.create_performance_metrics_section()
        scroll_layout.addWidget(performance_section)

        # Progress Tracking Section
        progress_section = self.create_progress_tracking_section()
        scroll_layout.addWidget(progress_section)

        # Coaching Insights Section
        insights_section = self.create_coaching_insights_section()
        scroll_layout.addWidget(insights_section)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def create_session_summary_section(self):
        """Create the current session summary section."""
        section = QFrame()
        section.setFrameStyle(QFrame.StyledPanel)
        section.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border-radius: 8px;
                border: 1px solid #404040;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Section title
        title = QLabel("Current Session")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)

        # Session info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(10)

        self.session_track_label = QLabel("Track: --")
        self.session_car_label = QLabel("Car: --")
        self.session_duration_label = QLabel("Duration: --")
        self.session_laps_label = QLabel("Laps Completed: --")
        self.session_best_label = QLabel("Best Lap: --")
        self.session_avg_label = QLabel("Average Lap: --")

        labels = [
            self.session_track_label, self.session_car_label,
            self.session_duration_label, self.session_laps_label,
            self.session_best_label, self.session_avg_label
        ]

        for i, label in enumerate(labels):
            label.setStyleSheet("color: white; font-size: 14px;")
            row, col = divmod(i, 2)
            info_grid.addWidget(label, row, col)

        layout.addLayout(info_grid)
        return section

    def create_performance_metrics_section(self):
        """Create the performance metrics section."""
        section = QFrame()
        section.setFrameStyle(QFrame.StyledPanel)
        section.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border-radius: 8px;
                border: 1px solid #404040;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Section title
        title = QLabel("Performance Metrics")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)

        # Metrics grid
        metrics_layout = QHBoxLayout()
        
        # Consistency Score
        consistency_widget = self.create_metric_widget(
            "Consistency Score", "85%", "Based on lap time variance", "#3498db"
        )
        metrics_layout.addWidget(consistency_widget)
        
        # Sector Performance
        sector_widget = self.create_metric_widget(
            "Best Sectors", "S1: +0.2s, S2: -0.1s, S3: +0.4s", "vs. Personal Best", "#e74c3c"
        )
        metrics_layout.addWidget(sector_widget)
        
        # Improvement Rate
        improvement_widget = self.create_metric_widget(
            "Session Improvement", "-1.2s", "Time dropped this session", "#2ecc71"
        )
        metrics_layout.addWidget(improvement_widget)

        layout.addLayout(metrics_layout)
        return section

    def create_progress_tracking_section(self):
        """Create the progress tracking section."""
        section = QFrame()
        section.setFrameStyle(QFrame.StyledPanel)
        section.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border-radius: 8px;
                border: 1px solid #404040;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Section title
        title = QLabel("Progress Tracking")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)

        # Progress charts area
        progress_layout = QHBoxLayout()
        
        # Weekly progress
        weekly_widget = self.create_progress_chart("This Week", ["Mon", "Tue", "Wed", "Thu", "Fri"], [85.2, 84.8, 84.5, 84.1, 83.9])
        progress_layout.addWidget(weekly_widget)
        
        # Monthly progress  
        monthly_widget = self.create_progress_chart("This Month", ["W1", "W2", "W3", "W4"], [86.1, 85.2, 84.5, 83.9])
        progress_layout.addWidget(monthly_widget)

        layout.addLayout(progress_layout)
        return section

    def create_coaching_insights_section(self):
        """Create the coaching insights section."""
        section = QFrame()
        section.setFrameStyle(QFrame.StyledPanel)
        section.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border-radius: 8px;
                border: 1px solid #404040;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # Section title
        title = QLabel("Coaching Insights & Recommendations")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)

        # Insights
        insights_layout = QVBoxLayout()
        
        insights = [
            ("🎯", "Focus Area", "Sector 3 consistency - you're losing 0.4s on average compared to your best"),
            ("📈", "Strength", "Excellent braking zones - consistently hitting late braking points"),
            ("⚠️", "Watch Out", "Throttle application could be smoother through technical sections"),
            ("🏆", "Goal", "Target: Break 1:23.5 this session (0.3s improvement needed)")
        ]

        for icon, category, message in insights:
            insight_widget = self.create_insight_widget(icon, category, message)
            insights_layout.addWidget(insight_widget)

        layout.addLayout(insights_layout)
        return section

    def create_metric_widget(self, title, value, subtitle, color):
        """Create a metric display widget."""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: #3C3C3F;
                border-radius: 6px;
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #AAA; font-size: 12px; font-weight: bold;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(value_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #888; font-size: 11px;")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

        return widget

    def create_progress_chart(self, title, labels, values):
        """Create a simple progress chart widget."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #3C3C3F;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)

        # Simple text-based chart for now
        for i, (label, value) in enumerate(zip(labels, values)):
            row = QHBoxLayout()
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #AAA; font-size: 12px;")
            label_widget.setFixedWidth(50)
            row.addWidget(label_widget)
            
            value_widget = QLabel(f"{value:.1f}s")
            value_widget.setStyleSheet("color: white; font-size: 12px;")
            row.addWidget(value_widget)
            
            # Visual progress bar
            progress = QProgressBar()
            progress.setMaximum(100)
            progress.setValue(int((90 - value) * 10))  # Convert lap time to progress
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 3px;
                    text-align: center;
                    height: 10px;
                }
                QProgressBar::chunk {
                    background-color: #00ff88;
                    border-radius: 2px;
                }
            """)
            progress.setTextVisible(False)
            row.addWidget(progress)
            
            layout.addLayout(row)

        return widget

    def create_insight_widget(self, icon, category, message):
        """Create an insight display widget."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #3C3C3F;
                border-radius: 6px;
                margin-bottom: 5px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        icon_label.setFixedWidth(30)
        layout.addWidget(icon_label)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        category_label = QLabel(category)
        category_label.setStyleSheet("color: #00ff88; font-size: 12px; font-weight: bold;")
        content_layout.addWidget(category_label)

        message_label = QLabel(message)
        message_label.setStyleSheet("color: white; font-size: 13px;")
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)

        layout.addLayout(content_layout)
        return widget

    def refresh_coaching_data(self):
        """Refresh the coaching data from the database."""
        logger.info("Refreshing coaching data...")
        
        try:
            # Fetch current session data
            session_data = self.data_manager.get_session_summary()
            self.current_session_stats = session_data
            
            # Calculate performance metrics
            performance_data = self.data_manager.get_performance_metrics()
            
            # Get progress data
            progress_data = self.data_manager.get_progress_data()
            
            # Generate coaching insights
            insights = self.data_manager.get_coaching_insights(session_data, performance_data)
            
            # Update the UI
            self.update_session_summary(session_data)
            self.update_performance_metrics(performance_data)
            self.update_progress_tracking(progress_data)
            self.update_coaching_insights(insights)
            
        except Exception as e:
            logger.error(f"Error refreshing coaching data: {e}")

    def update_session_summary(self, session_data=None):
        """Update the session summary with current data."""
        if not session_data:
            return
            
        try:
            self.session_track_label.setText(f"Track: {session_data.get('track_name', '--')}")
            self.session_car_label.setText(f"Car: {session_data.get('car_name', '--')}")
            self.session_duration_label.setText(f"Duration: {session_data.get('duration', '--')}")
            self.session_laps_label.setText(f"Laps Completed: {session_data.get('total_laps', '--')}")
            
            best_lap = session_data.get('best_lap')
            if best_lap:
                self.session_best_label.setText(f"Best Lap: {self._format_time(best_lap)}")
            else:
                self.session_best_label.setText("Best Lap: --")
                
            avg_lap = session_data.get('average_lap')
            if avg_lap:
                self.session_avg_label.setText(f"Average Lap: {self._format_time(avg_lap)}")
            else:
                self.session_avg_label.setText("Average Lap: --")
                
        except Exception as e:
            logger.error(f"Error updating session summary: {e}")

    def update_performance_metrics(self, performance_data=None):
        """Update performance metrics with calculated data."""
        if not performance_data:
            return
            
        # TODO: Update the actual metric widgets with real data
        # For now, the mock data in the widgets will suffice
        logger.info(f"Performance data: {performance_data}")

    def update_progress_tracking(self, progress_data=None):
        """Update progress tracking charts with calculated data."""
        if not progress_data:
            return
            
        # TODO: Update the actual progress chart widgets with real data
        logger.info(f"Progress data: {progress_data}")

    def update_coaching_insights(self, insights=None):
        """Update coaching insights based on performance analysis."""
        if not insights:
            return
            
        # TODO: Update the actual insight widgets with real data
        logger.info(f"Generated {len(insights)} coaching insights")
        
    def _format_time(self, time_seconds: float) -> str:
        """Format time in seconds to MM:SS.mmm format."""
        if time_seconds is None or time_seconds <= 0:
            return "--:--.---"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes:01d}:{seconds:06.3f}"

    def update_telemetry(self, telemetry_data):
        """Override the old telemetry update method - no longer needed."""
        # The new coaching overview doesn't use live telemetry data
        pass

    def clear_telemetry(self):
        """Override the old clear method - no longer needed."""
        # The new coaching overview doesn't use live telemetry data
        pass 