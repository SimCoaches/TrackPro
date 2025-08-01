#!/usr/bin/env python3
"""
Track Visualization Window - Live track building visualization
Shows the track being traced in real-time during track building process.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QWidget, QGroupBox)
from PyQt6.QtCore import pyqtSlot, QTimer
from PyQt6.QtGui import QFont
import time


class TrackVisualizationWindow(QDialog):
    """Window that shows live track building visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TrackPro - Live Track Building Visualization")
        self.setMinimumSize(900, 700)
        
        # Track data
        self.track_builder = None
        self.all_points = []
        self.completed_laps = []
        self.current_lap_points = []
        self.start_finish_point = None
        
        # Setup UI
        self.setup_ui()
        
        # Auto-refresh timer - PERFORMANCE FIX: Reduced frequency to prevent blocking pedal thread
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plot)
        self.refresh_timer.start(250)  # Update every 250ms (4Hz) instead of 100ms to reduce CPU load
        
        self.last_update_time = time.time()
        
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Live Track Building Visualization")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Status info
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Waiting for track building to start...")
        status_layout.addWidget(self.status_label)
        
        self.lap_info_label = QLabel("Laps: 0/3 | Current lap: 0 points")
        status_layout.addWidget(self.lap_info_label)
        
        layout.addWidget(status_group)
        
        # Matplotlib canvas
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear View")
        self.clear_button.clicked.connect(self.clear_visualization)
        control_layout.addWidget(self.clear_button)
        
        self.zoom_fit_button = QPushButton("Zoom to Fit")
        self.zoom_fit_button.clicked.connect(self.zoom_to_fit)
        control_layout.addWidget(self.zoom_fit_button)
        
        control_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        control_layout.addWidget(self.close_button)
        
        layout.addLayout(control_layout)
        
        # Initialize plot
        self.init_plot()
    
    def init_plot(self):
        """Initialize the matplotlib plot."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Live Track Map Building", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("X Position (m)")
        self.ax.set_ylabel("Y Position (m)")
        self.ax.grid(True, alpha=0.3)
        self.ax.set_aspect('equal')
        
        # Initialize empty line plots
        self.all_points_line, = self.ax.plot([], [], 'lightgray', alpha=0.5, linewidth=1, label='All Points')
        self.completed_laps_lines = []
        self.current_lap_line, = self.ax.plot([], [], 'red', linewidth=3, label='Current Lap')
        self.start_finish_point_plot, = self.ax.plot([], [], 'go', markersize=12, markeredgecolor='black', 
                                                     markeredgewidth=2, label='Start/Finish')
        
        self.ax.legend(loc='upper right')
        self.canvas.draw()
    
    @pyqtSlot(object)
    def update_track_data(self, track_builder):
        """Update visualization with new track data from the builder."""
        self.track_builder = track_builder
        
        if track_builder:
            # Update status
            completed_laps = len(track_builder.laps)
            current_lap_points = len(track_builder.current_lap)
            total_points = len(track_builder.track_points)
            
            status_text = f"Building track - {total_points} total points collected"
            if track_builder.waiting_for_first_crossing:
                status_text += " (Waiting for start/finish line crossing)"
            elif track_builder.lap_collection_started:
                status_text += " (Collecting lap data)"
            
            self.status_label.setText(status_text)
            self.lap_info_label.setText(f"Laps: {completed_laps}/3 | Current lap: {current_lap_points} points")
            
            # Store data for plotting
            self.all_points = track_builder.track_points.copy()
            self.completed_laps = [lap.copy() for lap in track_builder.laps]
            self.current_lap_points = track_builder.current_lap.copy()
            
            # Mark start/finish point if available
            if track_builder.start_finish_position:
                self.start_finish_point = track_builder.start_finish_position
            
            # Check if centerline is generated
            if track_builder.centerline_generated and track_builder.centerline_track:
                self.status_label.setText(f"✅ Centerline generated! ({len(track_builder.centerline_track)} points)")
        
        self.last_update_time = time.time()
    
    def refresh_plot(self):
        """Refresh the plot with current data."""
        # PERFORMANCE FIX: Skip refresh if no new data
        current_time = time.time()
        if current_time - self.last_update_time < 0.2:  # Only refresh if data updated in last 200ms
            return
        if not self.track_builder:
            return
        
        try:
            # Clear previous plots
            self.ax.clear()
            self.ax.set_title("Live Track Map Building", fontsize=14, fontweight='bold')
            self.ax.set_xlabel("X Position (m)")
            self.ax.set_ylabel("Y Position (m)")
            self.ax.grid(True, alpha=0.3)
            self.ax.set_aspect('equal')
            
            # Plot all collected points (very faint)
            if self.all_points:
                x_all = [p[0] for p in self.all_points]
                y_all = [p[1] for p in self.all_points]
                self.ax.plot(x_all, y_all, 'lightgray', alpha=0.3, linewidth=0.5, label='All Points')
            
            # Plot completed laps with different colors
            colors = ['blue', 'green', 'purple', 'orange', 'brown']
            for i, lap in enumerate(self.completed_laps):
                if lap:
                    x_lap = [p[0] for p in lap]
                    y_lap = [p[1] for p in lap]
                    color = colors[i % len(colors)]
                    self.ax.plot(x_lap, y_lap, color=color, linewidth=2, alpha=0.8, 
                               label=f'Lap {i+1} (Complete)')
            
            # Plot current lap being traced (bright red)
            if self.current_lap_points:
                x_current = [p[0] for p in self.current_lap_points]
                y_current = [p[1] for p in self.current_lap_points]
                self.ax.plot(x_current, y_current, 'red', linewidth=4, alpha=1.0, 
                           label=f'Current Lap ({len(self.current_lap_points)} pts)')
                
                # Show current position with a marker
                if len(self.current_lap_points) > 0:
                    current_pos = self.current_lap_points[-1]
                    self.ax.plot(current_pos[0], current_pos[1], 'ro', markersize=8, 
                               markeredgecolor='yellow', markeredgewidth=2)
            
            # Plot start/finish line
            if self.start_finish_point:
                self.ax.plot(self.start_finish_point[0], self.start_finish_point[1], 
                           'go', markersize=15, markeredgecolor='black', markeredgewidth=3,
                           label='Start/Finish Line')
            
            # Plot centerline if generated
            if (hasattr(self.track_builder, 'centerline_track') and 
                self.track_builder.centerline_track):
                x_center = [p[0] for p in self.track_builder.centerline_track]
                y_center = [p[1] for p in self.track_builder.centerline_track]
                self.ax.plot(x_center, y_center, 'yellow', linewidth=3, alpha=0.9,
                           label='Generated Centerline', linestyle='--')
            
            # Add legend and refresh
            self.ax.legend(loc='upper right', fontsize=10)
            
            # Auto-zoom to fit data
            if self.all_points or self.current_lap_points:
                all_coords = []
                if self.all_points:
                    all_coords.extend(self.all_points)
                if self.current_lap_points:
                    all_coords.extend(self.current_lap_points)
                
                if all_coords:
                    x_coords = [p[0] for p in all_coords]
                    y_coords = [p[1] for p in all_coords]
                    
                    if x_coords and y_coords:
                        margin = max(abs(max(x_coords) - min(x_coords)), 
                                   abs(max(y_coords) - min(y_coords))) * 0.1
                        
                        self.ax.set_xlim(min(x_coords) - margin, max(x_coords) + margin)
                        self.ax.set_ylim(min(y_coords) - margin, max(y_coords) + margin)
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error refreshing plot: {e}")
    
    def clear_visualization(self):
        """Clear the visualization."""
        self.all_points = []
        self.completed_laps = []
        self.current_lap_points = []
        self.start_finish_point = None
        self.track_builder = None
        
        self.status_label.setText("Visualization cleared - waiting for new data...")
        self.lap_info_label.setText("Laps: 0/3 | Current lap: 0 points")
        
        self.init_plot()
    
    def zoom_to_fit(self):
        """Zoom to fit all track data."""
        if not (self.all_points or self.current_lap_points):
            return
        
        all_coords = []
        if self.all_points:
            all_coords.extend(self.all_points)
        if self.current_lap_points:
            all_coords.extend(self.current_lap_points)
        
        if all_coords:
            x_coords = [p[0] for p in all_coords]
            y_coords = [p[1] for p in all_coords]
            
            if x_coords and y_coords:
                margin = max(abs(max(x_coords) - min(x_coords)), 
                           abs(max(y_coords) - min(y_coords))) * 0.1
                
                self.ax.set_xlim(min(x_coords) - margin, max(x_coords) + margin)
                self.ax.set_ylim(min(y_coords) - margin, max(y_coords) + margin)
                self.canvas.draw()
    
    def closeEvent(self, event):
        """Handle close event."""
        self.refresh_timer.stop()
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = TrackVisualizationWindow()
    window.show()
    sys.exit(app.exec()) 