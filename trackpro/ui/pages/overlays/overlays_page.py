"""Overlays page - hosting track builder and other overlay features."""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QPushButton, 
    QLabel, QGroupBox, QProgressBar, QTextEdit, QMessageBox,
    QFrame, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class OverlaysPage(BasePage):
    """Main overlays page with track builder and other overlay features."""
    
    # Signals for overlay events
    overlay_started = pyqtSignal(str)  # overlay type
    overlay_stopped = pyqtSignal(str)
    track_builder_progress = pyqtSignal(int, str)  # progress, status
    
    def __init__(self, global_managers=None):
        self.track_map_overlay_manager = None
        self.track_builder_thread = None
        super().__init__("overlays", global_managers)
    
    def init_page(self):
        """Initialize the overlays page UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Page title
        title = QLabel("🎯 Overlays")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #fefefe;
                margin: 10px 0px;
            }
        """)
        layout.addWidget(title)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Ultimate Track Builder Section
        self.setup_track_builder_section(scroll_layout)
        
        # Track Map Overlay Section  
        self.setup_track_map_section(scroll_layout)
        
        # Placeholder for future overlays
        self.setup_future_overlays_section(scroll_layout)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
    
    def setup_track_builder_section(self, layout):
        """Setup the Ultimate Track Builder section."""
        # Track Builder Group
        builder_group = QGroupBox("🏗️ Ultimate Track Builder")
        builder_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #fefefe;
                border: 2px solid #40444b;
                border-radius: 8px;
                margin: 10px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        
        builder_layout = QVBoxLayout(builder_group)
        
        # Description
        desc_label = QLabel(
            "Build custom track maps using iRacing telemetry data. "
            "Drive 3 laps to automatically generate a centerline track map."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #c0c0c0; font-size: 12px; margin: 5px 0px;")
        builder_layout.addWidget(desc_label)
        
        # Status and progress
        status_layout = QVBoxLayout()
        
        self.builder_status_label = QLabel("Ready to build track map")
        self.builder_status_label.setStyleSheet("color: #fefefe; font-size: 12px; margin: 5px 0px;")
        status_layout.addWidget(self.builder_status_label)
        
        self.builder_progress_bar = QProgressBar()
        self.builder_progress_bar.setMaximum(3)  # 3 laps
        self.builder_progress_bar.setValue(0)
        self.builder_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #40444b;
                border-radius: 4px;
                background-color: #252525;
                text-align: center;
                color: #fefefe;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #5865f2;
                border-radius: 3px;
            }
        """)
        status_layout.addWidget(self.builder_progress_bar)
        
        builder_layout.addLayout(status_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.start_builder_btn = QPushButton("🚀 Start Track Builder")
        self.start_builder_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:disabled {
                background-color: #40444b;
                color: #888;
            }
        """)
        self.start_builder_btn.clicked.connect(self.start_track_builder)
        
        self.stop_builder_btn = QPushButton("⏹️ Stop Builder")
        self.stop_builder_btn.setEnabled(False)
        self.stop_builder_btn.setStyleSheet("""
            QPushButton {
                background-color: #ed4245;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:disabled {
                background-color: #40444b;
                color: #888;
            }
        """)
        self.stop_builder_btn.clicked.connect(self.stop_track_builder)
        
        buttons_layout.addWidget(self.start_builder_btn)
        buttons_layout.addWidget(self.stop_builder_btn)
        buttons_layout.addStretch()
        
        builder_layout.addLayout(buttons_layout)
        layout.addWidget(builder_group)
    
    def setup_track_map_section(self, layout):
        """Setup the Track Map Overlay section."""
        # Track Map Overlay Group
        overlay_group = QGroupBox("🗺️ Track Map Overlay")
        overlay_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #fefefe;
                border: 2px solid #40444b;
                border-radius: 8px;
                margin: 10px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        
        overlay_layout = QVBoxLayout(overlay_group)
        
        # Description
        desc_label = QLabel(
            "Display a real-time track map overlay showing your position and track layout. "
            "Requires existing track map data."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #c0c0c0; font-size: 12px; margin: 5px 0px;")
        overlay_layout.addWidget(desc_label)
        
        # Status
        self.overlay_status_label = QLabel("No overlay active")
        self.overlay_status_label.setStyleSheet("color: #fefefe; font-size: 12px; margin: 5px 0px;")
        overlay_layout.addWidget(self.overlay_status_label)
        
        # Buttons
        overlay_buttons_layout = QHBoxLayout()
        
        self.start_overlay_btn = QPushButton("🎯 Start Track Overlay")
        self.start_overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #57f287;
                color: #252525;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3ba55c;
                color: white;
            }
            QPushButton:disabled {
                background-color: #40444b;
                color: #888;
            }
        """)
        self.start_overlay_btn.clicked.connect(self.start_track_overlay)
        
        self.stop_overlay_btn = QPushButton("⏹️ Stop Overlay")
        self.stop_overlay_btn.setEnabled(False)
        self.stop_overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #ed4245;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:disabled {
                background-color: #40444b;
                color: #888;
            }
        """)
        self.stop_overlay_btn.clicked.connect(self.stop_track_overlay)
        
        self.overlay_settings_btn = QPushButton("⚙️ Overlay Settings")
        self.overlay_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #40444b;
                color: #fefefe;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5865f2;
            }
        """)
        self.overlay_settings_btn.clicked.connect(self.show_overlay_settings)
        
        overlay_buttons_layout.addWidget(self.start_overlay_btn)
        overlay_buttons_layout.addWidget(self.stop_overlay_btn)
        overlay_buttons_layout.addWidget(self.overlay_settings_btn)
        overlay_buttons_layout.addStretch()
        
        overlay_layout.addLayout(overlay_buttons_layout)
        layout.addWidget(overlay_group)
    
    def setup_future_overlays_section(self, layout):
        """Setup section for future overlay types."""
        # Future Overlays Group
        future_group = QGroupBox("🚧 Coming Soon")
        future_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #fefefe;
                border: 2px solid #40444b;
                border-radius: 8px;
                margin: 10px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        
        future_layout = QVBoxLayout(future_group)
        
        future_overlays = [
            "📊 Telemetry Data Overlay",
            "🏁 Sector Timing Overlay", 
            "👁️ Eye Tracking Overlay",
            "📈 Performance Comparison Overlay"
        ]
        
        for overlay_name in future_overlays:
            overlay_label = QLabel(overlay_name)
            overlay_label.setStyleSheet("color: #888; font-size: 12px; margin: 2px 0px;")
            future_layout.addWidget(overlay_label)
        
        layout.addWidget(future_group)
    
    def start_track_builder(self):
        """Start the Ultimate Track Builder."""
        try:
            # Check for iRacing connection
            if not self.iracing_monitor:
                QMessageBox.warning(self, "iRacing Required", 
                                   "iRacing connection is required for track building.")
                return
            
            # Import and start the track builder
            from ....race_coach.ui.track_map_overlay_settings import TrackBuilderThread
            
            self.track_builder_thread = TrackBuilderThread(self.iracing_monitor)
            
            # Connect signals
            self.track_builder_thread.status_updated.connect(self.on_builder_status_updated)
            self.track_builder_thread.progress_updated.connect(self.on_builder_progress_updated)
            self.track_builder_thread.error_occurred.connect(self.on_builder_error)
            self.track_builder_thread.finished.connect(self.on_builder_finished)
            
            # Start the thread
            self.track_builder_thread.start()
            
            # Update UI
            self.start_builder_btn.setEnabled(False)
            self.stop_builder_btn.setEnabled(True)
            self.builder_status_label.setText("🔌 Starting track builder...")
            self.builder_progress_bar.setValue(0)
            
            logger.info("🏗️ Ultimate Track Builder started from Overlays page")
            
        except Exception as e:
            logger.error(f"Error starting track builder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start track builder: {str(e)}")
    
    def stop_track_builder(self):
        """Stop the track builder."""
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.track_builder_thread.should_stop = True
            self.track_builder_thread.quit()
            self.track_builder_thread.wait(3000)  # Wait up to 3 seconds
            
        # Update UI
        self.start_builder_btn.setEnabled(True)
        self.stop_builder_btn.setEnabled(False)
        self.builder_status_label.setText("Track builder stopped")
        
        logger.info("🛑 Track builder stopped")
    
    def start_track_overlay(self):
        """Start the track map overlay."""
        try:
            # Initialize overlay manager if needed
            if not self.track_map_overlay_manager:
                from ....race_coach.track_map_overlay import TrackMapOverlayManager
                self.track_map_overlay_manager = TrackMapOverlayManager(self.iracing_monitor)
            
            # Start the overlay
            success = self.track_map_overlay_manager.start_overlay()
            
            if success:
                # Update UI
                self.start_overlay_btn.setEnabled(False)
                self.stop_overlay_btn.setEnabled(True)
                self.overlay_status_label.setText("Track overlay active")
                logger.info("🎯 Track map overlay started")
            else:
                QMessageBox.warning(self, "Overlay Failed", 
                                   "Failed to start track overlay. Check if track data is available.")
                
        except Exception as e:
            logger.error(f"Error starting track overlay: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start track overlay: {str(e)}")
    
    def stop_track_overlay(self):
        """Stop the track map overlay."""
        if self.track_map_overlay_manager and self.track_map_overlay_manager.is_active:
            self.track_map_overlay_manager.stop_overlay()
            
            # Update UI
            self.start_overlay_btn.setEnabled(True)
            self.stop_overlay_btn.setEnabled(False)
            self.overlay_status_label.setText("No overlay active")
            
            logger.info("🛑 Track map overlay stopped")
    
    def show_overlay_settings(self):
        """Show the track map overlay settings dialog."""
        try:
            from ....race_coach.ui.track_map_overlay_settings import TrackMapOverlaySettingsDialog
            
            dialog = TrackMapOverlaySettingsDialog(self)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing overlay settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open overlay settings: {str(e)}")
    
    def on_builder_status_updated(self, status):
        """Handle track builder status updates."""
        self.builder_status_label.setText(status)
        self.track_builder_progress.emit(self.builder_progress_bar.value(), status)
    
    def on_builder_progress_updated(self, completed_laps, total_laps):
        """Handle track builder progress updates."""
        self.builder_progress_bar.setValue(completed_laps)
        status = f"Lap {completed_laps}/{total_laps} completed"
        self.builder_status_label.setText(status)
        self.track_builder_progress.emit(completed_laps, status)
    
    def on_builder_error(self, error_message):
        """Handle track builder errors."""
        self.builder_status_label.setText(f"❌ Error: {error_message}")
        QMessageBox.critical(self, "Track Builder Error", error_message)
        self.stop_track_builder()
    
    def on_builder_finished(self):
        """Handle track builder completion."""
        self.start_builder_btn.setEnabled(True)
        self.stop_builder_btn.setEnabled(False)
        self.builder_status_label.setText("✅ Track building completed!")
        
        # Show completion message
        QMessageBox.information(self, "Track Builder Complete", 
                               "Track building completed successfully! "
                               "You can now use the track overlay.")
        
        logger.info("✅ Track builder completed successfully")
    
    def on_page_activated(self):
        """Called when the page is activated."""
        super().on_page_activated()
        
        # Check iRacing connection status
        if self.iracing_monitor:
            if hasattr(self.iracing_monitor, 'is_connected') and self.iracing_monitor.is_connected():
                status_text = "iRacing connected - ready for track building"
            else:
                status_text = "iRacing not connected - connect to enable track building"
        else:
            status_text = "iRacing monitor not available"
        
        # Update status if no active operations
        if self.builder_status_label.text() == "Ready to build track map":
            self.builder_status_label.setText(status_text)
    
    def cleanup(self):
        """Clean up resources when page is destroyed."""
        # Stop track builder if running
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.stop_track_builder()
        
        # Stop overlay if active
        if self.track_map_overlay_manager and self.track_map_overlay_manager.is_active:
            self.stop_track_overlay()
        
        super().cleanup()