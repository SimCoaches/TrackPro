#!/usr/bin/env python3
"""
Integrated Track Builder Dialog - PyQt Interface for Ultimate Track Builder
This provides a GUI interface for the 3-lap centerline track building functionality.
"""

import sys
import os
import time
import numpy as np
import json
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QTextEdit, QFrame,
                             QGridLayout, QMessageBox, QGroupBox, QSpinBox)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont

# Track builder functionality is now integrated into the main TrackPro interface
# This dialog redirects users to the integrated track builder
ULTIMATE_TRACK_BUILDER_AVAILABLE = False  # Always redirect to integrated version

# Import database functionality
try:
    from ...database.supabase_client import SupabaseClient
except ImportError:
    print("Warning: Supabase client not available")
    SupabaseClient = None


class TrackBuilderWorker(QThread):
    """Worker thread for running the track builder to avoid blocking the UI"""
    
    position_updated = pyqtSignal(float, float)  # x, y position
    lap_completed = pyqtSignal(int)  # lap number
    centerline_generated = pyqtSignal(object)  # centerline data
    status_updated = pyqtSignal(str)  # status message
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.track_builder = None
        self.running = False
        
    def start_building(self):
        """Start the track building process"""
        if not ULTIMATE_TRACK_BUILDER_AVAILABLE:
            self.error_occurred.emit("Integrated track builder not available")
            return
            
        # This should never be reached since ULTIMATE_TRACK_BUILDER_AVAILABLE is always False
        pass
    
    def stop_building(self):
        """Stop the track building process"""
        self.running = False
        self.wait()
    
    def run(self):
        """Main worker thread loop"""
        last_update = time.time()
        
        while self.running and self.track_builder:
            try:
                if not self.track_builder.ir.is_connected:
                    self.error_occurred.emit("Lost connection to iRacing")
                    break
                
                # Get current telemetry and update track
                speed = self.track_builder.ir['Speed'] or 0.0
                
                if speed > 1.0:  # Only update when moving
                    # Update track builder (this calls update_track internally)
                    self.track_builder.update_track(0)  # frame number not used
                    
                    # Get current position
                    if self.track_builder.track_builder.track_points:
                        pos = self.track_builder.track_builder.track_points[-1]
                        self.position_updated.emit(pos[0], pos[1])
                    
                    # Check for lap completion
                    completed_laps = len(self.track_builder.track_builder.laps)
                    if hasattr(self, '_last_lap_count'):
                        if completed_laps > self._last_lap_count:
                            self.lap_completed.emit(completed_laps)
                    self._last_lap_count = completed_laps
                    
                    # Check for centerline generation
                    if (self.track_builder.centerline_track is not None and 
                        not getattr(self, '_centerline_emitted', False)):
                        self.centerline_generated.emit(self.track_builder.centerline_track)
                        self._centerline_emitted = True
                    
                    # Update status
                    if completed_laps >= 3:
                        self.status_updated.emit("3 laps completed - Centerline ready!")
                    else:
                        self.status_updated.emit(f"Collecting lap {completed_laps + 1}/3...")
                
                # Update at ~30 FPS
                time.sleep(0.033)
                
            except Exception as e:
                self.error_occurred.emit(f"Error in track building: {str(e)}")
                break
        
        self.running = False


class IntegratedTrackBuilderDialog(QDialog):
    """Main dialog for the integrated track builder"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TrackPro - 3-Lap Centerline Builder")
        self.setMinimumSize(800, 500)
        
        # Initialize components
        self.worker = TrackBuilderWorker()
        self.supabase_client = None
        self.current_track_data = None
        
        self.setup_ui()
        self.connect_signals()
        
        # Try to initialize Supabase client
        if SupabaseClient:
            try:
                self.supabase_client = SupabaseClient()
            except:
                print("Warning: Could not initialize Supabase client")
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("TrackPro - 3-Lap Centerline Builder")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Drive 3 complete laps to generate a perfect centerline track map.")
        layout.addWidget(desc)
        
        # Status group
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready to start - Connect to iRacing and start driving")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 3)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Track Building")
        self.start_button.clicked.connect(self.start_building)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_building)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.save_button = QPushButton("Save Track Map")
        self.save_button.clicked.connect(self.save_track_map)
        self.save_button.setEnabled(False)
        control_layout.addWidget(self.save_button)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Log area
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def connect_signals(self):
        """Connect worker signals to UI slots"""
        self.worker.position_updated.connect(self.on_position_updated)
        self.worker.lap_completed.connect(self.on_lap_completed)
        self.worker.centerline_generated.connect(self.on_centerline_generated)
        self.worker.status_updated.connect(self.on_status_updated)
        self.worker.error_occurred.connect(self.on_error_occurred)
    
    @pyqtSlot()
    def start_building(self):
        """Start the track building process"""
        if not ULTIMATE_TRACK_BUILDER_AVAILABLE:
            QMessageBox.information(self, "Use Integrated Track Builder", 
                                  "The track building functionality is now integrated into TrackPro!\n\n"
                                  "To build track maps:\n"
                                  "1. Go to Race Coach → Track Map Overlay Settings\n"
                                  "2. Use the 'Track Builder' tab\n"
                                  "3. Click 'Start Track Builder'\n\n"
                                  "This provides the same 3-lap centerline generation with enhanced features!")
            return
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.save_button.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.log("Starting track building...")
        
        self.worker.start_building()
    
    @pyqtSlot()
    def stop_building(self):
        """Stop the track building process"""
        self.worker.stop_building()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        self.log("Track building stopped.")
    
    @pyqtSlot(float, float)
    def on_position_updated(self, x, y):
        """Handle position updates from the worker"""
        pass  # Could update a mini track display if needed
    
    @pyqtSlot(int)
    def on_lap_completed(self, lap_number):
        """Handle lap completion"""
        self.progress_bar.setValue(lap_number)
        self.log(f"Lap {lap_number} completed!")
    
    @pyqtSlot(object)
    def on_centerline_generated(self, centerline_data):
        """Handle centerline generation"""
        self.current_track_data = centerline_data
        self.save_button.setEnabled(True)
        
        self.log("Centerline generated successfully!")
        self.log(f"Track map contains {len(centerline_data)} points")
    
    @pyqtSlot(str)
    def on_status_updated(self, status):
        """Handle status updates"""
        self.status_label.setText(status)
    
    @pyqtSlot(str)
    def on_error_occurred(self, error_msg):
        """Handle errors"""
        self.log(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
        
        # Reset buttons on error
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def log(self, message):
        """Add a message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    @pyqtSlot()
    def save_track_map(self):
        """Save the track map to a local file"""
        if self.current_track_data is None:
            QMessageBox.warning(self, "Warning", "No track data to save")
            return
        
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"track_map_{timestamp}.json"
            
            # Convert numpy array to list for JSON serialization
            track_data = {
                "track_map": self.current_track_data.tolist(),
                "timestamp": timestamp,
                "lap_count": 3,
                "point_count": len(self.current_track_data)
            }
            
            with open(filename, 'w') as f:
                json.dump(track_data, f, indent=2)
            
            self.log(f"Track map saved to {filename}")
            QMessageBox.information(self, "Success", f"Track map saved to {filename}")
            
        except Exception as e:
            error_msg = f"Failed to save track map: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.worker.running:
            self.worker.stop_building()
        event.accept()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = IntegratedTrackBuilderDialog()
    dialog.show()
    sys.exit(app.exec_())