"""Racing Engineer's Debrief - Post-session analysis and next session planning.

This module provides comprehensive analysis of the last racing session and intelligent
recommendations for the next session, like having a personal racing engineer.
"""

import logging
import math
import statistics
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QComboBox, QSpinBox, QSlider, QGroupBox, QTextEdit, QScrollArea,
    QFrame, QSizePolicy, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen, QBrush, QColor, QPixmap
from .coaching_data_manager import CoachingDataManager

logger = logging.getLogger(__name__)


class SessionSummaryCard(QFrame):
    """Widget showing last session summary like a racing debrief."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 6px;
                border: 2px solid #2a82da;
            }
        """)
        
        # Set fixed height to make container compact
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel("🏁 LAST SESSION")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin: 0px;
            padding: 1px 0px;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Session date/time
        self.session_time_label = QLabel("")
        self.session_time_label.setStyleSheet("color: #888; font-size: 10px;")
        header_layout.addWidget(self.session_time_label)
        
        layout.addLayout(header_layout)
        
        # Main session info
        info_layout = QGridLayout()
        info_layout.setSpacing(2)
        
        self.track_car_label = QLabel("Track & Car: Loading...")
        self.track_car_label.setStyleSheet("font-size: 18px; color: #e0e0e0; font-weight: bold;")
        info_layout.addWidget(self.track_car_label, 0, 0, 1, 2)
        
        self.duration_label = QLabel("Duration: --")
        self.laps_label = QLabel("Laps: --")
        self.best_lap_label = QLabel("Best: --:--.---")
        self.improvement_label = QLabel("Improvement: --")
        
        labels = [self.duration_label, self.laps_label, self.best_lap_label, self.improvement_label]
        for i, label in enumerate(labels):
            label.setStyleSheet("color: #e0e0e0; font-size: 18px;")
            row, col = divmod(i, 2)
            info_layout.addWidget(label, row + 1, col)
        
        layout.addLayout(info_layout)


class PerformanceAnalysisWidget(QFrame):
    """Detailed performance analysis like a racing engineer's report."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #505050;
            }
        """)
        
        # Set fixed height to make container compact
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        
        # Title
        title = QLabel("📊 PERFORMANCE")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin: 0px;
            padding: 1px 0px;
        """)
        layout.addWidget(title)
        
        # Analysis content
        self.analysis_layout = QVBoxLayout()
        self.analysis_layout.setSpacing(1)
        layout.addLayout(self.analysis_layout)


class NextSessionPlannerWidget(QFrame):
    """Next session goals and recommendations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #505050;
            }
        """)
        
        # Set fixed height to make container compact
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        
        # Title
        title = QLabel("🎯 NEXT SESSION")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin: 0px;
            padding: 1px 0px;
        """)
        layout.addWidget(title)
        
        # Goals and recommendations
        self.planner_layout = QVBoxLayout()
        self.planner_layout.setSpacing(1)
        layout.addLayout(self.planner_layout)


class AchievementsWidget(QFrame):
    """Achievements and progress celebration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #505050;
            }
        """)
        
        # Set fixed height to make container compact
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        
        # Title
        title = QLabel("🏆 HIGHLIGHTS")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin: 0px;
            padding: 1px 0px;
        """)
        layout.addWidget(title)
        
        # Achievements content
        self.achievements_layout = QVBoxLayout()
        self.achievements_layout.setSpacing(1)
        layout.addLayout(self.achievements_layout)


class ProgressTrackingWidget(QFrame):
    """Long-term progress tracking."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #505050;
            }
        """)
        
        # Set fixed height to make container compact
        self.setFixedHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        
        # Title
        title = QLabel("📈 PROGRESS")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2a82da;
            margin: 0px;
            padding: 1px 0px;
        """)
        layout.addWidget(title)
        
        # Progress content
        self.progress_layout = QVBoxLayout()
        self.progress_layout.setSpacing(1)
        layout.addLayout(self.progress_layout)


class OverviewTab(QWidget):
    """Racing Engineer's Debrief - Post-session analysis and planning."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.last_session_data = None
        
        # Initialize data manager
        supabase_client = None
        user_id = None
        if hasattr(parent, 'supabase_client'):
            supabase_client = parent.supabase_client
        if hasattr(parent, 'user_id'):
            user_id = parent.user_id
            
        self.data_manager = CoachingDataManager(supabase_client, user_id)
        
        self.setup_ui()
        
        # Load data when tab is shown
        QTimer.singleShot(500, self.load_session_debrief)

    def setup_ui(self):
        """Set up the racing engineer's debrief UI."""
        # Set background color to match pedal config theme
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Compact header with refresh button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Minimal title
        title_label = QLabel("📊 Debrief")
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2a82da;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Compact refresh button
        refresh_button = QPushButton("🔄 Refresh")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #505050;
                border-radius: 3px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
        """)
        refresh_button.clicked.connect(self.load_session_debrief)
        header_layout.addWidget(refresh_button)
        
        main_layout.addLayout(header_layout)

        # Session Summary (full width, compact)
        self.session_summary = SessionSummaryCard()
        main_layout.addWidget(self.session_summary)

        # Main content in two columns - much more compact
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)
        
        # Left column
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)
        
        self.performance_analysis = PerformanceAnalysisWidget()
        left_layout.addWidget(self.performance_analysis)
        
        self.achievements = AchievementsWidget()
        left_layout.addWidget(self.achievements)
        
        content_layout.addLayout(left_layout)
        
        # Right column
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        
        self.next_session_planner = NextSessionPlannerWidget()
        right_layout.addWidget(self.next_session_planner)
        
        self.progress_tracking = ProgressTrackingWidget()
        right_layout.addWidget(self.progress_tracking)
        
        content_layout.addLayout(right_layout)
        
        main_layout.addLayout(content_layout)

    def load_session_debrief(self):
        """Load and analyze the last session like a racing engineer."""
        logger.info("Loading racing engineer's debrief...")
        
        try:
            # Get last session data
            session_data = self.data_manager.get_session_summary()
            self.last_session_data = session_data
            
            # Update all sections
            self._update_session_summary(session_data)
            self._analyze_performance(session_data)
            self._identify_achievements(session_data)
            self._plan_next_session(session_data)
            self._update_progress_tracking(session_data)
            
        except Exception as e:
            logger.error(f"Error loading session debrief: {e}")
            self._show_no_data_message()

    def _update_session_summary(self, session_data):
        """Update the session summary card."""
        if not session_data or session_data.get('total_laps', 0) == 0:
            self.session_summary.track_car_label.setText("No recent session data available")
            self.session_summary.session_time_label.setText("")
            self.session_summary.duration_label.setText("Duration: --")
            self.session_summary.laps_label.setText("Laps: 0")
            self.session_summary.best_lap_label.setText("Best: --:--.---")
            self.session_summary.improvement_label.setText("Improvement: No data")
            return
        
        # Format track and car info
        track = session_data.get('track_name', 'Unknown Track')
        car = session_data.get('car_name', 'Unknown Car')
        self.session_summary.track_car_label.setText(f"{track} • {car}")
        
        # Session timing
        session_date = session_data.get('session_date')
        if session_date:
            try:
                date_obj = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                time_ago = self._time_ago(date_obj)
                self.session_summary.session_time_label.setText(f"{time_ago}")
            except:
                self.session_summary.session_time_label.setText("")
        
        # Session metrics
        duration = session_data.get('duration', '--')
        total_laps = session_data.get('total_laps', 0)
        valid_laps = session_data.get('valid_laps', 0)
        best_lap = session_data.get('best_lap')
        
        self.session_summary.duration_label.setText(f"Duration: {duration}")
        self.session_summary.laps_label.setText(f"Laps: {total_laps} ({valid_laps} valid)")
        
        if best_lap:
            self.session_summary.best_lap_label.setText(f"Best: {self._format_time(best_lap)}")
        else:
            self.session_summary.best_lap_label.setText("Best: --:--.---")
        
        # Calculate improvement from previous session
        improvement = self._calculate_session_improvement(session_data)
        if improvement:
            self.session_summary.improvement_label.setText(f"Improvement: {improvement}")
        else:
            self.session_summary.improvement_label.setText("Improvement: First session")

    def _analyze_performance(self, session_data):
        """Provide detailed performance analysis like a racing engineer."""
        # Clear previous analysis
        for i in reversed(range(self.performance_analysis.analysis_layout.count())):
            child = self.performance_analysis.analysis_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not session_data or session_data.get('total_laps', 0) == 0:
            no_data = QLabel("Complete a racing session to see analysis.")
            no_data.setStyleSheet("color: #888; font-style: italic; font-size: 18px; padding: 8px;")
            self.performance_analysis.analysis_layout.addWidget(no_data)
            return
        
        # Get performance metrics
        performance_data = self.data_manager.get_performance_metrics()
        
        analysis_points = []
        
        # Consistency Analysis
        consistency = performance_data.get('consistency_score', 0)
        if consistency > 0:
            if consistency > 95:
                analysis_points.append(("🎯", "CONSISTENCY", f"Exceptional: {consistency:.1f}%", "excellent"))
            elif consistency > 85:
                analysis_points.append(("✅", "CONSISTENCY", f"Strong: {consistency:.1f}%", "good"))
            elif consistency > 70:
                analysis_points.append(("⚠️", "CONSISTENCY", f"Moderate: {consistency:.1f}%", "warning"))
            else:
                analysis_points.append(("🔧", "CONSISTENCY", f"Focus area: {consistency:.1f}%", "priority"))
        
        # Pace Analysis
        best_lap = performance_data.get('best_lap')
        avg_lap = performance_data.get('average_lap')
        if best_lap and avg_lap:
            gap = avg_lap - best_lap
            if gap < 0.5:
                analysis_points.append(("🚀", "PACE", f"Excellent control: {gap:.3f}s gap", "excellent"))
            elif gap < 1.0:
                analysis_points.append(("📈", "PACE", f"Good pace: {gap:.3f}s window", "good"))
            else:
                analysis_points.append(("🎯", "PACE", f"Opportunity: {gap:.3f}s to find", "opportunity"))
        
        # Session improvement
        improvement = performance_data.get('session_improvement', 0)
        if improvement > 0.2:
            analysis_points.append(("📈", "PROGRESS", f"+{improvement:.3f}s faster", "excellent"))
        elif improvement < -0.2:
            analysis_points.append(("😴", "PROGRESS", f"Times degraded {abs(improvement):.3f}s", "warning"))
        
        # Add analysis points to UI (limit to top 3-4)
        for icon, category, message, level in analysis_points[:4]:
            analysis_widget = self._create_analysis_widget(icon, category, message, level)
            self.performance_analysis.analysis_layout.addWidget(analysis_widget)

    def _identify_achievements(self, session_data):
        """Identify and celebrate session achievements."""
        # Clear previous achievements
        for i in reversed(range(self.achievements.achievements_layout.count())):
            child = self.achievements.achievements_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not session_data or session_data.get('total_laps', 0) == 0:
            no_achievements = QLabel("Complete a session for highlights!")
            no_achievements.setStyleSheet("color: #888; font-style: italic; font-size: 18px; padding: 8px;")
            self.achievements.achievements_layout.addWidget(no_achievements)
            return
        
        achievements = []
        
        # Session completion achievement
        total_laps = session_data.get('total_laps', 0)
        if total_laps > 0:
            achievements.append(("🏁", "COMPLETED", f"{total_laps} laps"))
        
        # Best lap achievement
        best_lap = session_data.get('best_lap')
        if best_lap:
            achievements.append(("⏱️", "BEST LAP", f"{self._format_time(best_lap)}"))
        
        # Consistency achievements
        performance_data = self.data_manager.get_performance_metrics()
        consistency = performance_data.get('consistency_score', 0)
        if consistency > 95:
            achievements.append(("🎯", "CONSISTENCY", f"{consistency:.1f}% - Exceptional"))
        elif consistency > 85:
            achievements.append(("✅", "CONSISTENCY", f"{consistency:.1f}% - Strong"))
        
        # Improvement achievements
        improvement = performance_data.get('session_improvement', 0)
        if improvement > 0.3:
            achievements.append(("📈", "BIG GAIN", f"+{improvement:.3f}s improvement"))
        
        # Add achievements to UI (limit to 3-4)
        for icon, title, description in achievements[:4]:
            achievement_widget = self._create_achievement_widget(icon, title, description)
            self.achievements.achievements_layout.addWidget(achievement_widget)

    def _plan_next_session(self, session_data):
        """Plan the next session based on analysis."""
        # Clear previous plans
        for i in reversed(range(self.next_session_planner.planner_layout.count())):
            child = self.next_session_planner.planner_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not session_data or session_data.get('total_laps', 0) == 0:
            no_plan = QLabel("Complete session for recommendations!")
            no_plan.setStyleSheet("color: #888; font-style: italic; font-size: 18px; padding: 8px;")
            self.next_session_planner.planner_layout.addWidget(no_plan)
            return
        
        recommendations = []
        
        # Get performance data for recommendations
        performance_data = self.data_manager.get_performance_metrics()
        consistency = performance_data.get('consistency_score', 0)
        best_lap = performance_data.get('best_lap')
        avg_lap = performance_data.get('average_lap')
        
        # Consistency recommendations
        if consistency < 70:
            recommendations.append(("🎯", "FOCUS", "Work on consistency first"))
        elif consistency < 85:
            recommendations.append(("📈", "GOAL", f"Target 85%+ consistency"))
        else:
            recommendations.append(("🚀", "PACE", "Focus on ultimate pace"))
        
        # Pace recommendations
        if best_lap and avg_lap:
            gap = avg_lap - best_lap
            if gap > 1.0:
                target_time = best_lap - 0.1
                recommendations.append(("⏱️", "TARGET", f"Beat {self._format_time(target_time)}"))
            elif gap > 0.5:
                recommendations.append(("🔧", "WINDOW", "Tighten pace window"))
        
        # Session length recommendations
        total_laps = session_data.get('total_laps', 0)
        if total_laps < 15:
            recommendations.append(("⏳", "LENGTH", "Try 20+ lap sessions"))
        
        # Add recommendations to UI (limit to 3-4)
        for icon, category, recommendation in recommendations[:4]:
            rec_widget = self._create_recommendation_widget(icon, category, recommendation)
            self.next_session_planner.planner_layout.addWidget(rec_widget)

    def _update_progress_tracking(self, session_data):
        """Update long-term progress tracking."""
        # Clear previous progress
        for i in reversed(range(self.progress_tracking.progress_layout.count())):
            child = self.progress_tracking.progress_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        progress_items = []
        
        # Session count tracking
        total_laps = session_data.get('total_laps', 0) if session_data else 0
        progress_items.append(("📊", "DATA", f"{total_laps} laps logged"))
        progress_items.append(("🏎️", "CAREER", "Session saved to database"))
        progress_items.append(("🎯", "TRACKING", "Performance metrics recorded"))
        
        # Add progress items to UI (limit to 3)
        for icon, category, description in progress_items[:3]:
            progress_widget = self._create_progress_widget(icon, category, description)
            self.progress_tracking.progress_layout.addWidget(progress_widget)

    def _create_analysis_widget(self, icon, category, message, level):
        """Create a performance analysis widget."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
                margin-bottom: 2px;
                padding: 4px;
                border: 1px solid #505050;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 12px;")
        icon_label.setFixedWidth(16)
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(1)
        
        category_label = QLabel(category)
        color_map = {
            "excellent": "#2a82da",
            "good": "#2a82da", 
            "neutral": "#e0e0e0",
            "warning": "#ff8c00",
            "priority": "#ff5555",
            "opportunity": "#2a82da",
            "suggestion": "#e0e0e0"
        }
        color = color_map.get(level, "#e0e0e0")
        category_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(category_label)

        message_label = QLabel(message)
        message_label.setStyleSheet("color: #e0e0e0; font-size: 18px;")
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)

        layout.addLayout(content_layout)
        return widget

    def _create_achievement_widget(self, icon, title, description):
        """Create an achievement widget."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
                margin-bottom: 2px;
                padding: 4px;
                border-left: 2px solid #2a82da;
                border-top: 1px solid #505050;
                border-right: 1px solid #505050;
                border-bottom: 1px solid #505050;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 12px;")
        icon_label.setFixedWidth(16)
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(1)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #2a82da; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #e0e0e0; font-size: 18px;")
        desc_label.setWordWrap(True)
        content_layout.addWidget(desc_label)

        layout.addLayout(content_layout)
        return widget

    def _create_recommendation_widget(self, icon, category, recommendation):
        """Create a next session recommendation widget."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
                margin-bottom: 2px;
                padding: 4px;
                border-left: 2px solid #2a82da;
                border-top: 1px solid #505050;
                border-right: 1px solid #505050;
                border-bottom: 1px solid #505050;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 12px;")
        icon_label.setFixedWidth(16)
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(1)
        
        category_label = QLabel(category)
        category_label.setStyleSheet("color: #2a82da; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(category_label)

        rec_label = QLabel(recommendation)
        rec_label.setStyleSheet("color: #e0e0e0; font-size: 18px;")
        rec_label.setWordWrap(True)
        content_layout.addWidget(rec_label)

        layout.addLayout(content_layout)
        return widget

    def _create_progress_widget(self, icon, category, description):
        """Create a progress tracking widget."""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
                margin-bottom: 2px;
                padding: 4px;
                border-left: 2px solid #2a82da;
                border-top: 1px solid #505050;
                border-right: 1px solid #505050;
                border-bottom: 1px solid #505050;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 12px;")
        icon_label.setFixedWidth(16)
        layout.addWidget(icon_label)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(1)
        
        category_label = QLabel(category)
        category_label.setStyleSheet("color: #2a82da; font-size: 18px; font-weight: bold;")
        content_layout.addWidget(category_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #e0e0e0; font-size: 18px;")
        desc_label.setWordWrap(True)
        content_layout.addWidget(desc_label)

        layout.addLayout(content_layout)
        return widget

    def _calculate_session_improvement(self, session_data):
        """Calculate improvement from previous session."""
        # This would compare with previous session data
        # For now, return a placeholder
        best_lap = session_data.get('best_lap')
        if best_lap:
            # Mock comparison - would be real with historical data
            return "Personal best"
        return None

    def _time_ago(self, date_obj):
        """Convert datetime to human-readable time ago."""
        now = datetime.now(date_obj.tzinfo) if date_obj.tzinfo else datetime.now()
        diff = now - date_obj
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"

    def _format_time(self, time_seconds: float) -> str:
        """Format time in seconds to MM:SS.mmm format."""
        if time_seconds is None or time_seconds <= 0:
            return "--:--.---"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes:01d}:{seconds:06.3f}"

    def _show_no_data_message(self):
        """Show message when no session data is available."""
        # Clear all widgets and show helpful message
        pass

    def update_telemetry(self, telemetry_data):
        """Handle telemetry updates - not needed for post-session analysis."""
        pass

    def clear_telemetry(self):
        """Clear telemetry data - not needed for post-session analysis."""
        pass 