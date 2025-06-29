"""
Sector Timing Widget for TrackPro Race Coach

Displays live sector timing information including:
- Current sector progress
- Best sector times
- Sector comparisons
- Recent lap sector times
"""

import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QFrame, QGridLayout, QScrollArea, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette

logger = logging.getLogger(__name__)

class SectorTimingWidget(QWidget):
    """Widget to display live sector timing information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.iracing_api = None
        self.current_sector_data = {}
        self.best_sector_times = []
        
        self.init_ui()
        
        # Timer to update display
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # Update every 100ms
        
        logger.info("SectorTimingWidget initialized")
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #ffffff;
            }
            QFrame {
                border: 1px solid #333333;
                border-radius: 5px;
                background-color: #2a2a2a;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #333333;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #00ff88;
                border-radius: 3px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Sector Timing")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Current sector progress
        self.create_current_sector_section(main_layout)
        
        # Best sector times
        self.create_best_times_section(main_layout)
        
        # Recent laps
        self.create_recent_laps_section(main_layout)
        
        # Status and controls
        self.create_status_section(main_layout)
        
        main_layout.addStretch()
    
    def create_current_sector_section(self, parent_layout):
        """Create the current sector progress section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        
        # Section title
        title = QLabel("Current Sector")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88;")
        layout.addWidget(title)
        
        # Current sector info
        info_layout = QHBoxLayout()
        
        self.current_sector_label = QLabel("Sector: --")
        self.current_sector_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        info_layout.addWidget(self.current_sector_label)
        
        self.current_time_label = QLabel("Time: --.---")
        self.current_time_label.setFont(QFont("Arial", 14))
        info_layout.addWidget(self.current_time_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Progress bar for current sector
        self.sector_progress = QProgressBar()
        self.sector_progress.setRange(0, 100)
        self.sector_progress.setValue(0)
        self.sector_progress.setFormat("Sector Progress")
        layout.addWidget(self.sector_progress)
        
        parent_layout.addWidget(frame)
    
    def create_best_times_section(self, parent_layout):
        """Create the best sector times section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        
        # Section title
        title = QLabel("Best Sector Times")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88;")
        layout.addWidget(title)
        
        # Grid for sector times
        self.best_times_grid = QGridLayout()
        self.best_sector_labels = []
        
        # Create labels for up to 6 sectors (most tracks have 3-4)
        for i in range(6):
            sector_label = QLabel(f"S{i+1}:")
            sector_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            time_label = QLabel("---.---")
            time_label.setFont(QFont("Arial", 10))
            time_label.setStyleSheet("color: #ffff00;")  # Yellow for best times
            
            self.best_times_grid.addWidget(sector_label, i // 3, (i % 3) * 2)
            self.best_times_grid.addWidget(time_label, i // 3, (i % 3) * 2 + 1)
            
            self.best_sector_labels.append(time_label)
        
        layout.addLayout(self.best_times_grid)
        parent_layout.addWidget(frame)
    
    def create_recent_laps_section(self, parent_layout):
        """Create the recent laps section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        
        # Section title
        title = QLabel("Recent Laps")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88;")
        layout.addWidget(title)
        
        # Scroll area for recent laps
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        self.recent_laps_widget = QWidget()
        self.recent_laps_layout = QVBoxLayout(self.recent_laps_widget)
        self.recent_laps_layout.setSpacing(5)
        
        scroll_area.setWidget(self.recent_laps_widget)
        layout.addWidget(scroll_area)
        
        parent_layout.addWidget(frame)
    
    def create_status_section(self, parent_layout):
        """Create the status section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        
        # Section title
        title = QLabel("Status")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #00ff88;")
        layout.addWidget(title)
        
        # Status label
        self.status_label = QLabel("Waiting for sector data...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Manual retry button
        self.retry_button = QPushButton("Retry")
        self.retry_button.clicked.connect(self.retry_session)
        layout.addWidget(self.retry_button)
        
        parent_layout.addWidget(frame)
    
    def set_iracing_api(self, iracing_api):
        """Set the iRacing API instance."""
        self.iracing_api = iracing_api
        logger.info("iRacing API set for SectorTimingWidget")
    
    def update_display(self):
        """Update the display with current sector timing data."""
        if not self.iracing_api:
            self.status_label.setText("No iRacing API connected")
            return
        
        try:
            # Get sector timing data from API
            sector_data = self.iracing_api.get_sector_timing_data()
            if not sector_data:
                self.status_label.setText("No sector timing data available")
                return
            
            is_initialized = sector_data.get('is_initialized', False)
            if not is_initialized:
                self.status_label.setText("Sector timing initializing...")
                return
            
            # Show active status with more detail
            current_progress = sector_data.get('current_progress', {})
            total_sectors = current_progress.get('total_sectors', 3)
            self.status_label.setText(f"Sector timing active ({total_sectors} sectors)")
            
            # Update current sector progress
            self.update_current_sector(current_progress)
            
            # Update best times
            best_times = current_progress.get('best_sector_times', [])
            self.update_best_times(best_times)
            
            # Update recent laps
            recent_laps = sector_data.get('recent_laps', [])
            self.update_recent_laps(recent_laps)
            
        except Exception as e:
            logger.error(f"Error updating sector timing display: {e}")
            self.status_label.setText(f"Display error: {str(e)}")
    
    def update_current_sector(self, progress_data):
        """Update the current sector progress display."""
        current_sector = progress_data.get('current_sector', 1)
        total_sectors = progress_data.get('total_sectors', 3)
        current_time = progress_data.get('current_sector_time', 0.0)
        completed_sectors = progress_data.get('completed_sectors', 0)
        
        # Update labels
        self.current_sector_label.setText(f"Sector: {current_sector}/{total_sectors}")
        self.current_time_label.setText(f"Time: {current_time:.3f}s")
        
        # Update progress bar
        if total_sectors > 0:
            progress_percent = (completed_sectors / total_sectors) * 100
            self.sector_progress.setValue(int(progress_percent))
            self.sector_progress.setFormat(f"Lap Progress: {completed_sectors}/{total_sectors} sectors")
    
    def update_best_times(self, best_times):
        """Update the best sector times display."""
        for i, label in enumerate(self.best_sector_labels):
            if i < len(best_times) and best_times[i] is not None:
                label.setText(f"{best_times[i]:.3f}")
                label.setStyleSheet("color: #ffff00;")  # Yellow for valid times
            else:
                label.setText("---.---")
                label.setStyleSheet("color: #666666;")  # Gray for no time
    
    def update_recent_laps(self, recent_laps):
        """Update the recent laps display."""
        # Clear existing lap widgets
        for i in reversed(range(self.recent_laps_layout.count())):
            child = self.recent_laps_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add recent laps (show last 5)
        for lap_data in recent_laps[-5:]:
            lap_widget = self.create_lap_widget(lap_data)
            self.recent_laps_layout.addWidget(lap_widget)
        
        # Add stretch to push laps to top
        self.recent_laps_layout.addStretch()
    
    def create_lap_widget(self, lap_data):
        """Create a widget for displaying a single lap's sector times."""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.Box)
        widget.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 3px;
                margin: 2px;
                padding: 5px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 3, 5, 3)
        
        # Handle both dictionary and object formats for lap_data
        if isinstance(lap_data, dict):
            # Dictionary format from SimpleSectorTimingIntegration
            lap_number = lap_data.get('lap_number', 0)
            sector_times = lap_data.get('sector_times', [])
            total_time = lap_data.get('total_time', 0.0)
        else:
            # Object format (legacy support)
            lap_number = getattr(lap_data, 'lap_number', 0)
            sector_times = getattr(lap_data, 'sector_times', [])
            total_time = getattr(lap_data, 'total_time', 0.0)
        
        # Lap number
        lap_label = QLabel(f"Lap {lap_number}")
        lap_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        lap_label.setStyleSheet("color: #00ff88;")
        layout.addWidget(lap_label)
        
        # Sector times
        for i, sector_time in enumerate(sector_times):
            sector_label = QLabel(f"S{i+1}: {sector_time:.3f}")
            sector_label.setFont(QFont("Arial", 8))
            
            # Color code based on whether it's a best time
            if (hasattr(self, 'best_sector_times') and 
                i < len(self.best_sector_times) and 
                self.best_sector_times[i] is not None and 
                abs(sector_time - self.best_sector_times[i]) < 0.001):
                sector_label.setStyleSheet("color: #ffff00;")  # Yellow for best
            else:
                sector_label.setStyleSheet("color: #ffffff;")  # White for normal
            
            layout.addWidget(sector_label)
        
        # Total time
        total_label = QLabel(f"Total: {total_time:.3f}")
        total_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        total_label.setStyleSheet("color: #ff8800;")  # Orange for total time
        layout.addWidget(total_label)
        
        layout.addStretch()
        
        return widget
    
    def on_telemetry_data(self, telemetry_data):
        """Handle incoming telemetry data."""
        # Store current sector data for display updates
        self.current_sector_data = {
            'current_sector': telemetry_data.get('current_sector', 1),
            'current_sector_time': telemetry_data.get('current_sector_time', 0.0),
            'best_sector_times': telemetry_data.get('best_sector_times', [])
        }
        
        # Update best sector times for lap widget coloring
        self.best_sector_times = telemetry_data.get('best_sector_times', [])
    
    def clear_data(self):
        """Clear all sector timing data."""
        if self.iracing_api:
            self.iracing_api.clear_sector_timing()
        
        # Reset display
        self.current_sector_label.setText("Sector: --")
        self.current_time_label.setText("Time: --.---")
        self.sector_progress.setValue(0)
        
        for label in self.best_sector_labels:
            label.setText("---.---")
            label.setStyleSheet("color: #666666;")
        
        # Clear recent laps
        for i in reversed(range(self.recent_laps_layout.count())):
            child = self.recent_laps_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.status_label.setText("Sector timing cleared")
        logger.info("Sector timing display cleared")
    
    def retry_session(self):
        """Handle the manual retry button click."""
        if not self.iracing_api:
            self.status_label.setText("No iRacing API available")
            return
        
        self.status_label.setText("Retrying SessionInfo retrieval...")
        self.retry_button.setEnabled(False)
        
        try:
            # Try to force SessionInfo update
            if hasattr(self.iracing_api, 'force_session_info_update'):
                success = self.iracing_api.force_session_info_update()
                if success:
                    self.status_label.setText("SessionInfo retry successful!")
                else:
                    self.status_label.setText("SessionInfo retry failed - using default sectors")
            else:
                self.status_label.setText("Force update not available")
        except Exception as e:
            self.status_label.setText(f"Retry error: {str(e)}")
        finally:
            self.retry_button.setEnabled(True) 