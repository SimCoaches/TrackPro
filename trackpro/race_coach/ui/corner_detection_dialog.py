"""
Corner Detection Dialog - UI for Track Analysis
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QProgressBar, QTextEdit, QSpinBox, 
                           QGroupBox, QMessageBox, QListWidget, QListWidgetItem, QWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from ..corner_detection_manager import CornerDetectionManager, Corner


class CornerDetectionDialog(QDialog):
    """Dialog for running corner detection analysis."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.corner_manager = CornerDetectionManager()
        self.detected_corners = []
        
        self.setWindowTitle("Corner Detection - Track Analysis")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🏁 Corner Detection - Task 2.2")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Automatically detect corners using speed drops and steering increases.\n"
                     "Corners will be numbered starting from the start/finish line.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Settings group
        settings_group = QGroupBox("Detection Settings")
        settings_layout = QHBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Data Collection Duration:"))
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(30, 300)
        self.duration_spinbox.setValue(120)
        self.duration_spinbox.setSuffix(" seconds")
        settings_layout.addWidget(self.duration_spinbox)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # Status and progress
        status_group = QGroupBox("Detection Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready to start corner detection")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # Detected corners list
        corners_group = QGroupBox("Detected Corners")
        corners_layout = QVBoxLayout(corners_group)
        
        self.corners_list = QListWidget()
        self.corners_list.setMaximumHeight(150)
        corners_layout.addWidget(self.corners_list)
        
        layout.addWidget(corners_group)
        
        # Log output
        log_group = QGroupBox("Detection Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # Control buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        
        self.start_button = QPushButton("🚀 Start Corner Detection")
        self.start_button.clicked.connect(self.start_detection)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ Stop Detection")
        self.stop_button.clicked.connect(self.stop_detection)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addWidget(button_widget)
    
    def connect_signals(self):
        """Connect corner manager signals to UI updates."""
        self.corner_manager.status_update.connect(self.update_status)
        self.corner_manager.progress_update.connect(self.update_progress)
        self.corner_manager.detection_complete.connect(self.on_detection_complete)
        self.corner_manager.error_occurred.connect(self.on_error)
        self.corner_manager.existing_data_found.connect(self.on_existing_data_found)
    
    def start_detection(self, force_regenerate: bool = False):
        """Start the corner detection process."""
        duration = self.duration_spinbox.value()
        
        self.detected_corners.clear()
        self.corners_list.clear()
        self.log_text.clear()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.add_log_entry("Starting corner detection...")
        self.add_log_entry(f"Data collection duration: {duration} seconds")
        self.add_log_entry("Make sure iRacing is running and you're on track!")
        
        self.corner_manager.start_corner_detection(duration, force_regenerate)
    
    def stop_detection(self):
        """Stop the corner detection process."""
        self.corner_manager.stop_corner_detection()
        self.reset_ui_state()
    
    def reset_ui_state(self):
        """Reset UI to initial state."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    def update_status(self, message: str):
        """Update the status label."""
        self.status_label.setText(message)
        self.add_log_entry(message)
    
    def update_progress(self, message: str, progress: int):
        """Update progress bar and status."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self.add_log_entry(f"[{progress}%] {message}")
    
    def add_log_entry(self, message: str):
        """Add an entry to the log."""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_detection_complete(self, corners):
        """Handle detection completion."""
        self.detected_corners = corners
        self.reset_ui_state()
        
        self.corners_list.clear()
        for corner in corners:
            item_text = (f"Turn {corner.id}: "
                        f"Min Speed {corner.min_speed:.1f} m/s, "
                        f"Track Position {corner.apex_lap_dist_pct:.1%}")
            
            item = QListWidgetItem(item_text)
            self.corners_list.addItem(item)
        
        QMessageBox.information(
            self,
            "Corner Detection Complete",
            f"Successfully detected {len(corners)} corners!\n\n"
            f"Results have been saved to the corner_detection_results folder.\n"
            f"These corners are now available for the AI coaching system."
        )
        
        self.add_log_entry(f"✅ Detection complete! Found {len(corners)} corners.")
        self.add_log_entry("📁 Results saved to corner_detection_results/ folder")
    
    def on_existing_data_found(self, existing_data: dict):
        """Handle when existing corner data is found in the database."""
        track_name = existing_data.get('track_name', 'Unknown Track')
        track_config = existing_data.get('track_config', '')
        total_corners = existing_data.get('total_corners', 0)
        last_analysis = existing_data.get('last_analysis_date', 'Unknown')
        
        full_track_name = f"{track_name} - {track_config}" if track_config and track_config != track_name else track_name
        
        # Show dialog asking user what to do
        reply = QMessageBox.question(
            self,
            "Existing Corner Data Found",
            f"Corner data already exists for {full_track_name}:\n\n"
            f"• {total_corners} corners detected\n"
            f"• Last analyzed: {last_analysis}\n\n"
            f"Would you like to:\n"
            f"• Use existing data (recommended)\n"
            f"• Regenerate new corner data\n\n"
            f"Note: Regenerating will overwrite the existing data.",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # Use existing data
            self.load_existing_corners(existing_data)
        elif reply == QMessageBox.No:
            # Regenerate data
            self.add_log_entry("User chose to regenerate corner data...")
            self.start_detection(force_regenerate=True)
        else:
            # Cancel
            self.reset_ui_state()
    
    def load_existing_corners(self, existing_data: dict):
        """Load and display existing corner data."""
        try:
            corners = self.corner_manager.load_corners_from_supabase()
            
            if corners:
                self.detected_corners = corners
                self.corners_list.clear()
                
                for corner in corners:
                    item_text = (f"Turn {corner.id}: "
                                f"Min Speed {corner.min_speed:.1f} m/s, "
                                f"Track Position {corner.apex_lap_dist_pct:.1%}")
                    
                    item = QListWidgetItem(item_text)
                    self.corners_list.addItem(item)
                
                track_name = existing_data.get('track_name', 'Unknown Track')
                track_config = existing_data.get('track_config', '')
                full_track_name = f"{track_name} - {track_config}" if track_config and track_config != track_name else track_name
                
                self.add_log_entry(f"✅ Loaded {len(corners)} corners for {full_track_name}")
                self.add_log_entry("📁 Data loaded from Supabase database")
                self.add_log_entry("🏁 Corner data is ready for AI coaching system")
                
                QMessageBox.information(
                    self,
                    "Corner Data Loaded",
                    f"Successfully loaded {len(corners)} corners for {full_track_name}!\n\n"
                    f"This data is now available for the AI coaching system.\n"
                    f"No new data collection was needed."
                )
            else:
                self.add_log_entry("❌ Failed to load corner data from database")
                
        except Exception as e:
            self.add_log_entry(f"❌ Error loading existing data: {str(e)}")
    
    def on_error(self, error_message: str):
        """Handle detection errors."""
        self.reset_ui_state()
        
        QMessageBox.warning(
            self,
            "Corner Detection Error",
            f"An error occurred during corner detection:\n\n{error_message}"
        )
        
        self.add_log_entry(f"❌ Error: {error_message}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.corner_manager.is_detecting:
            reply = QMessageBox.question(
                self,
                "Corner Detection Running",
                "Corner detection is currently running. Do you want to stop it and close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_detection()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept() 