"""Eye tracking settings dialog for TrackPro."""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QCheckBox, QSlider, QGroupBox, QFormLayout, QTextEdit, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from trackpro.config import config

logger = logging.getLogger(__name__)


class EyeTrackingSettingsDialog(QDialog):
    """Dialog for configuring eye tracking settings."""
    
    # Signals for test completion
    test_completed_success = pyqtSignal()
    test_completed_error = pyqtSignal(str)
    
    def __init__(self, parent=None, eye_tracking_manager=None):
        super().__init__(parent)
        self.eye_tracking_manager = eye_tracking_manager
        self.setWindowTitle("Eye Tracking Settings")
        self.setModal(True)
        self.resize(500, 400)
        self.setup_ui()
        self.load_current_settings()
        
        # Connect test completion signals
        self.test_completed_success.connect(self.on_test_success)
        self.test_completed_error.connect(self.on_test_error)
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        
        # Main settings group
        main_group = QGroupBox("Eye Tracking Configuration")
        main_layout = QFormLayout()
        
        # Enable/disable eye tracking
        self.enabled_checkbox = QCheckBox("Enable Eye Tracking")
        self.enabled_checkbox.stateChanged.connect(self.on_enabled_changed)
        main_layout.addRow("Status:", self.enabled_checkbox)
        
        # Auto-start with session
        self.auto_start_checkbox = QCheckBox("Auto-start recording during racing sessions")
        main_layout.addRow("Recording:", self.auto_start_checkbox)
        
        # Require calibration
        self.require_calibration_checkbox = QCheckBox("Require calibration before recording")
        main_layout.addRow("Calibration:", self.require_calibration_checkbox)
        
        # Camera selection
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["Camera 0 (Default)", "Camera 1", "Camera 2", "Camera 3"])
        main_layout.addRow("Camera:", self.camera_combo)
        
        # Recording FPS
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(10, 60)
        self.fps_spinbox.setSuffix(" FPS")
        main_layout.addRow("Recording Rate:", self.fps_spinbox)
        
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Advanced settings group
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QFormLayout()
        
        # Auto-calibrate on startup
        self.auto_calibrate_checkbox = QCheckBox("Prompt for calibration when TrackPro starts")
        advanced_layout.addRow("Startup:", self.auto_calibrate_checkbox)
        
        # Show gaze overlay
        self.show_overlay_checkbox = QCheckBox("Show real-time gaze overlay & camera debug (performance impact)")
        advanced_layout.addRow("Overlay:", self.show_overlay_checkbox)
        
        # Save raw video
        self.save_video_checkbox = QCheckBox("Save raw camera video (large files)")
        advanced_layout.addRow("Video:", self.save_video_checkbox)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # Status and test section
        status_group = QGroupBox("Status & Testing")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Eye tracking status will appear here")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        # Test buttons
        button_layout = QHBoxLayout()
        
        self.test_camera_button = QPushButton("Test Camera")
        self.test_camera_button.clicked.connect(self.test_camera)
        button_layout.addWidget(self.test_camera_button)
        
        self.calibrate_button = QPushButton("Calibrate Now")
        self.calibrate_button.clicked.connect(self.calibrate_now)
        button_layout.addWidget(self.calibrate_button)
        
        self.test_gaze_button = QPushButton("Test Gaze Tracking")
        self.test_gaze_button.clicked.connect(self.test_gaze_tracking)
        button_layout.addWidget(self.test_gaze_button)
        
        # Add gaming overlay toggle button
        self.overlay_toggle_button = QPushButton("Start Gaming Overlay")
        self.overlay_toggle_button.clicked.connect(self.toggle_gaming_overlay)
        self.overlay_toggle_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        button_layout.addWidget(self.overlay_toggle_button)
        
        status_layout.addLayout(button_layout)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Update status and button states
        self.update_status()
        self.update_overlay_button_state()
    
    def load_current_settings(self):
        """Load current settings from configuration."""
        self.enabled_checkbox.setChecked(config.eye_tracking_enabled)
        self.auto_start_checkbox.setChecked(config.eye_tracking_auto_start)
        self.require_calibration_checkbox.setChecked(config.eye_tracking_require_calibration)
        self.camera_combo.setCurrentIndex(config.eye_tracking_camera_index)
        self.fps_spinbox.setValue(config.eye_tracking_fps)
        self.auto_calibrate_checkbox.setChecked(config.eye_tracking_auto_calibrate)
        self.show_overlay_checkbox.setChecked(config.eye_tracking_show_overlay)
        self.save_video_checkbox.setChecked(config.eye_tracking_save_video)
    
    def on_enabled_changed(self, state):
        """Handle enable/disable state change."""
        enabled = state == Qt.CheckState.Checked
        
        # Enable/disable other controls based on enabled state
        self.auto_start_checkbox.setEnabled(enabled)
        self.require_calibration_checkbox.setEnabled(enabled)
        self.camera_combo.setEnabled(enabled)
        self.fps_spinbox.setEnabled(enabled)
        self.auto_calibrate_checkbox.setEnabled(enabled)
        self.show_overlay_checkbox.setEnabled(enabled)
        self.save_video_checkbox.setEnabled(enabled)
        self.test_camera_button.setEnabled(enabled)
        self.calibrate_button.setEnabled(enabled)
        self.test_gaze_button.setEnabled(enabled)
        self.overlay_toggle_button.setEnabled(enabled)
        
        self.update_status()
    
    def update_status(self):
        """Update the status display."""
        if not self.enabled_checkbox.isChecked():
            self.status_label.setText("Eye tracking is disabled.")
            return
        
        if not self.eye_tracking_manager:
            self.status_label.setText("Eye tracking manager not available.")
            return
        
        status_parts = []
        
        if self.eye_tracking_manager.is_available():
            status_parts.append("✅ Eye tracking available")
        else:
            status_parts.append("❌ Eye tracking not available")
        
        if self.eye_tracking_manager.is_calibrated:
            status_parts.append("✅ Calibrated")
            status_parts.append("🎯 Ready for gaze tracking test")
        else:
            status_parts.append("⚠️ Not calibrated")
        
        if self.eye_tracking_manager.is_recording:
            status_parts.append("🔴 Currently recording")
        else:
            status_parts.append("⚫ Not recording")
        
        # Check gaming overlay status
        if hasattr(self.eye_tracking_manager, 'is_overlay_active') and self.eye_tracking_manager.is_overlay_active:
            status_parts.append("🎮 Gaming overlay active")
        else:
            status_parts.append("🎮 Gaming overlay inactive")
        
        self.status_label.setText("\n".join(status_parts))
        
        # Update overlay button state
        self.update_overlay_button_state()
    
    def test_camera(self):
        """Test camera access."""
        try:
            import cv2
            camera_index = self.camera_combo.currentIndex()
            
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    QMessageBox.information(self, "Camera Test", f"Camera {camera_index} is working correctly!")
                else:
                    QMessageBox.warning(self, "Camera Test", f"Camera {camera_index} opened but failed to capture frame.")
            else:
                QMessageBox.warning(self, "Camera Test", f"Failed to open camera {camera_index}.")
        except Exception as e:
            QMessageBox.critical(self, "Camera Test", f"Camera test failed: {str(e)}")
    
    def calibrate_now(self):
        """Start calibration process."""
        if not self.eye_tracking_manager or not self.eye_tracking_manager.is_available():
            QMessageBox.warning(self, "Calibration", "Eye tracking not available for calibration.")
            return
        
        reply = QMessageBox.question(
            self, "Eye Tracking Calibration",
            "This will start the eye tracking calibration process.\n\n"
            "Make sure you're seated comfortably and have good lighting.\n"
            "The calibration will take about 30 seconds.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.eye_tracking_manager.calibrate(self)
            if success:
                QMessageBox.information(self, "Calibration", "Calibration started. Please follow the on-screen instructions.")
            else:
                QMessageBox.warning(self, "Calibration", "Failed to start calibration.")
            
            # Update status after calibration attempt
            self.update_status()
    
    def test_gaze_tracking(self):
        """Test gaze tracking."""
        if not self.eye_tracking_manager or not self.eye_tracking_manager.is_available():
            QMessageBox.warning(self, "Test Failed", "Eye tracking not available for testing.")
            return
        
        if not self.eye_tracking_manager.is_calibrated:
            QMessageBox.warning(self, "Test Failed", 
                               "Please calibrate eye tracking before testing.\n\n"
                               "Click 'Calibrate Now' first, then try testing again.")
            return
        
        reply = QMessageBox.question(
            self, "Test Gaze Tracking",
            "This will start a 30-second gaze tracking test.\n\n"
            "🎯 NEW: Enhanced with white-screen calibration!\n\n"
            "You will see:\n"
            "• A green dot showing where you're looking\n"
            "• Camera feed with debug info\n"
            "• Real-time FPS and status\n"
            "• Improved accuracy from optimal lighting calibration\n\n"
            "Look around your screen and watch the dot follow your gaze!\n"
            "Press 'q' anytime to stop early.\n\n"
            "Start test?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Show progress dialog during test
                from PyQt6.QtCore import QTimer
                
                # Start the test in a separate thread to avoid blocking UI
                import threading
                
                def run_test():
                    try:
                        success = self.eye_tracking_manager.test_gaze_tracking(30)
                        if success:
                            self.test_completed_success.emit()
                        else:
                            self.test_completed_error.emit("Test failed")
                    except Exception as e:
                        self.test_completed_error.emit(str(e))
                
                # Signals are already connected in __init__
                
                QMessageBox.information(
                    self, "Test Starting",
                    "Gaze tracking test is starting!\n\n"
                    "Look around your screen and watch the green dot.\n"
                    "Two windows will open:\n"
                    "1. 'Gaze Tracking Test' - shows where you're looking\n"
                    "2. 'Eye Tracking Camera Test' - shows camera feed\n\n"
                    "Test will run for 30 seconds or until you press 'q'."
                )
                
                # Start test thread
                test_thread = threading.Thread(target=run_test)
                test_thread.daemon = True
                test_thread.start()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start gaze tracking test: {str(e)}")
    
    def on_test_success(self):
        """Handle successful test completion."""
        QMessageBox.information(
            self, "Test Complete", 
            "Gaze tracking test completed successfully!\n\n"
            "Did you see the green dot following your gaze?\n"
            "If the tracking seemed accurate, your eye tracking is working well!"
        )
    
    def on_test_error(self, error_message):
        """Handle test error."""
        QMessageBox.warning(
            self, "Test Error", 
            f"Gaze tracking test encountered an error:\n\n{error_message}"
        )
    
    def toggle_gaming_overlay(self):
        """Toggle the gaming-style transparent overlay on/off."""
        if not self.eye_tracking_manager or not self.eye_tracking_manager.is_available():
            QMessageBox.warning(self, "Gaming Overlay Failed", "Eye tracking not available for gaming overlay.")
            return
        
        if not self.eye_tracking_manager.is_calibrated:
            QMessageBox.warning(self, "Gaming Overlay Failed", 
                               "Please calibrate eye tracking before using gaming overlay.\n\n"
                               "Click 'Calibrate Now' first, then try the gaming overlay again.")
            return
        
        # Check if overlay is currently running
        if hasattr(self.eye_tracking_manager, 'is_overlay_active') and self.eye_tracking_manager.is_overlay_active:
            # Stop overlay
            try:
                self.eye_tracking_manager.stop_persistent_overlay()
                self.overlay_toggle_button.setText("Start Gaming Overlay")
                self.overlay_toggle_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
                QMessageBox.information(
                    self, "Gaming Overlay Stopped", 
                    "🎮 Gaming overlay has been stopped.\n\n"
                    "The transparent gaze dot is no longer visible."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to stop gaming overlay: {str(e)}")
        else:
            # Start overlay
            try:
                success = self.eye_tracking_manager.start_persistent_overlay()
                if success:
                    self.overlay_toggle_button.setText("Stop Gaming Overlay")
                    self.overlay_toggle_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
                    QMessageBox.information(
                        self, "Gaming Overlay Started", 
                        "🎮 Gaming overlay is now active!\n\n"
                        "✨ A transparent gaze dot will follow your eyes\n"
                        "🎯 The dot appears over ALL applications (including games)\n"
                        "👀 Green dot = tracking your gaze\n"
                        "🔴 Red dot = blinking detected\n"
                        "🖱️ Click-through - won't interfere with your games\n\n"
                        "Perfect for:\n"
                        "• Racing in iRacing and seeing where you look\n"
                        "• Real-time gaze feedback during gameplay\n"
                        "• Checking calibration accuracy\n\n"
                        "Press 'Q' on your keyboard or click 'Stop Gaming Overlay' to turn it off."
                    )
                else:
                    QMessageBox.warning(self, "Gaming Overlay Failed", "Failed to start gaming overlay.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start gaming overlay: {str(e)}")
        
        # Update button state and status
        self.update_status()
        self.update_overlay_button_state()
    
    def update_overlay_button_state(self):
        """Update the gaming overlay button text and style based on current state."""
        if hasattr(self, 'overlay_toggle_button'):
            if hasattr(self.eye_tracking_manager, 'is_overlay_active') and self.eye_tracking_manager.is_overlay_active:
                self.overlay_toggle_button.setText("Stop Gaming Overlay")
                self.overlay_toggle_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
            else:
                self.overlay_toggle_button.setText("Start Gaming Overlay")
                self.overlay_toggle_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
    
    def accept(self):
        """Save settings and close dialog."""
        try:
            # Save all settings
            config.set('eye_tracking.enabled', self.enabled_checkbox.isChecked())
            config.set('eye_tracking.auto_start_with_session', self.auto_start_checkbox.isChecked())
            config.set('eye_tracking.require_calibration', self.require_calibration_checkbox.isChecked())
            config.set('eye_tracking.camera_index', self.camera_combo.currentIndex())
            config.set('eye_tracking.recording_fps', self.fps_spinbox.value())
            config.set('eye_tracking.auto_calibrate_on_startup', self.auto_calibrate_checkbox.isChecked())
            config.set('eye_tracking.show_gaze_overlay', self.show_overlay_checkbox.isChecked())
            config.set('eye_tracking.save_raw_video', self.save_video_checkbox.isChecked())
            
            # Update eye tracking manager if available
            if self.eye_tracking_manager:
                self.eye_tracking_manager.enabled = config.eye_tracking_enabled
                self.eye_tracking_manager.auto_start = config.eye_tracking_auto_start
                self.eye_tracking_manager.require_calibration = config.eye_tracking_require_calibration
                self.eye_tracking_manager.camera_index = config.eye_tracking_camera_index
                self.eye_tracking_manager.recording_fps = config.eye_tracking_fps
            
            QMessageBox.information(
                self, "Settings Saved",
                "Eye tracking settings have been saved.\n\n"
                "Some changes may require restarting TrackPro to take effect."
            )
            
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
            logger.error(f"Failed to save eye tracking settings: {e}") 