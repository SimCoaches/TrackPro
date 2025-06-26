"""Eye tracking manager for Race Coach - Captures gaze data during racing sessions.

This module integrates EyeTrax webcam-based eye tracking with TrackPro's telemetry
system to provide gaze data for driver coaching and analysis.

Key Features:
- Configuration-based control (can be disabled)
- Only records during active racing sessions
- Automatic session start/stop based on iRacing state
- Requires calibration before recording (configurable)
"""

import logging
import time
import threading
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

# Import configuration
from trackpro.config import config

logger = logging.getLogger(__name__)

try:
    from eyetrax import GazeEstimator, run_9_point_calibration
    # Try to import additional calibration methods
    try:
        from eyetrax import run_13_point_calibration
        ENHANCED_CALIBRATION = True
    except ImportError:
        ENHANCED_CALIBRATION = False
        
    EYETRAX_AVAILABLE = True
    logger.info("✅ EyeTrax imported successfully")
except ImportError as e:
    EYETRAX_AVAILABLE = False
    ENHANCED_CALIBRATION = False
    logger.warning(f"❌ EyeTrax import failed: {e}")
except Exception as e:
    EYETRAX_AVAILABLE = False
    ENHANCED_CALIBRATION = False
    logger.error(f"❌ EyeTrax import error: {e}")


class EyeTrackingCalibrationDialog(QDialog):
    """Dialog for eye tracking calibration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Eye Tracking Calibration Setup")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("Eye Tracking Calibration Setup")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Setup instructions
        setup_text = QLabel("""
<b>⚠️ ENHANCED CALIBRATION WITH OPTIMAL LIGHTING:</b>

<b>🎯 NEW: PRE-CALIBRATION LIGHTING OPTIMIZATION!</b>
• A bright white full-screen will appear first
• This provides professional face lighting for 3 seconds
• Then standard EyeTrax calibration begins
• Much better consistency than ambient lighting!

<b>1. POSITION SETUP:</b>
• Sit 50-70cm (20-28 inches) from your monitor
• Look straight at the screen (not tilted)
• Camera should be centered above/below your monitor
• Make sure your WHOLE FACE is visible to the camera

<b>2. WHAT WILL HAPPEN:</b>
• First: 3-second white screen (face lighting optimization)
• Then: Standard calibration points appear
• Look DIRECTLY at each calibration point
• Keep your head COMPLETELY STILL - only move your EYES

<b>3. WHY THIS WORKS BETTER:</b>
• Eliminates lighting inconsistencies
• Provides even face illumination
• Uses proven EyeTrax calibration algorithms
• Combines lighting control with reliable calibration

<b>4. REALISTIC EXPECTATIONS:</b>
• With good setup: 1-2 inch accuracy possible
• Poor head position: May still be 3-5 inches off
• This approach maximizes webcam eye tracking potential

<b>Ready for ENHANCED calibration with lighting optimization?</b>
        """)
        setup_text.setStyleSheet("margin: 10px; line-height: 1.4;")
        setup_text.setWordWrap(True)
        layout.addWidget(setup_text)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Calibration")
        self.start_button.clicked.connect(self.accept)
        self.start_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        button_layout.addWidget(self.start_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)


class EyeTrackingManager(QObject):
    """Manages eye tracking data collection and synchronization with telemetry."""
    
    # Signals
    calibration_completed = pyqtSignal(bool, str)  # success, message
    eye_tracking_data = pyqtSignal(dict)  # gaze data
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.estimator = None
        self.is_calibrated = False
        self.is_recording = False
        self.current_session_id = None
        self.current_lap_id = None
        
        # Configuration-based initialization
        self.enabled = config.eye_tracking_enabled
        self.auto_start = config.eye_tracking_auto_start
        self.require_calibration = config.eye_tracking_require_calibration
        
        # Session state tracking
        self.is_in_racing_session = False
        self.session_type = None  # 'practice', 'qualify', 'race', etc.
        self.is_on_track = False
        self.is_driving = False  # Only record when actually driving
        
        # Threading and data collection
        self._recording_thread = None
        self._stop_recording = threading.Event()
        self._gaze_data_buffer = []
        self._buffer_lock = threading.Lock()
        
        # Persistent overlay functionality
        self.is_overlay_active = False
        self._overlay_thread = None
        self._stop_overlay = threading.Event()
        
        # Gaming overlay manager
        from trackpro.race_coach.eye_tracking_overlay import EyeTrackingGamingOverlayManager
        self.gaming_overlay_manager = EyeTrackingGamingOverlayManager()
        
        # Camera and display settings
        self.camera_index = config.eye_tracking_camera_index
        self.capture = None
        self.screen_width = 1920  # Will be updated with actual screen size
        self.screen_height = 1080
        self.recording_fps = config.eye_tracking_fps
        
        # Timing synchronization
        self._last_telemetry_timestamp = 0
        self._recording_start_time = 0
        
        # Only initialize if enabled and EyeTrax is available
        if self.enabled and EYETRAX_AVAILABLE:
            self._initialize_eye_tracking()
            logger.info("Eye tracking enabled and initialized")
        elif not self.enabled:
            logger.info("Eye tracking disabled in configuration")
        else:
            logger.warning("EyeTrax not available - eye tracking will be disabled")
        
        # Always try to initialize estimator for settings access (even if disabled)
        # This allows users to configure and calibrate eye tracking through settings
        if not self.estimator and EYETRAX_AVAILABLE:
            try:
                self._initialize_eye_tracking()
                logger.info("Eye tracking estimator initialized for settings access")
            except Exception as e:
                logger.warning(f"Could not initialize eye tracking estimator for settings: {e}")
    
    def _initialize_eye_tracking(self):
        """Initialize the eye tracking system."""
        try:
            self.estimator = GazeEstimator()
            logger.info("Eye tracking estimator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize eye tracking: {e}")
            self.error_occurred.emit(f"Eye tracking initialization failed: {str(e)}")
    
    def is_available(self):
        """Check if eye tracking is available and properly initialized."""
        # For recording, require enabled + available + estimator
        recording_available = self.enabled and EYETRAX_AVAILABLE and self.estimator is not None
        
        # For settings/calibration, only require available + estimator (even if disabled)
        settings_available = EYETRAX_AVAILABLE and self.estimator is not None
        
        # Return True if estimator is available (allows settings access even when disabled)
        available = settings_available
        
        if not available:
            if not EYETRAX_AVAILABLE:
                logger.debug("Eye tracking not available: EyeTrax library not available")
            elif self.estimator is None:
                logger.debug("Eye tracking not available: estimator not initialized")
        else:
            if recording_available:
                logger.debug("Eye tracking is available and ready for recording")
            else:
                logger.debug("Eye tracking is available for settings/calibration (recording disabled)")
            
        return available
    
    def calibrate(self, parent_widget=None):
        """Perform eye tracking calibration."""
        if not self.is_available():
            self.error_occurred.emit("Eye tracking not available")
            return False
        
        # Show calibration dialog
        dialog = EyeTrackingCalibrationDialog(parent_widget)
        if dialog.exec_() != QDialog.Accepted:
            return False
        
        try:
            # Run calibration in a separate thread to avoid blocking UI
            calibration_thread = threading.Thread(target=self._run_calibration)
            calibration_thread.daemon = True
            calibration_thread.start()
            return True
            
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            self.calibration_completed.emit(False, f"Calibration failed: {str(e)}")
            return False
    
    def _run_calibration(self):
        """Run the calibration process in a separate thread."""
        try:
            # Get screen dimensions
            from PyQt5.QtWidgets import QApplication, QDesktopWidget
            app = QApplication.instance()
            if app:
                desktop = app.desktop()
                screen_rect = desktop.screenGeometry()
                self.screen_width = screen_rect.width()
                self.screen_height = screen_rect.height()
            
            # Run high-precision white background calibration
            logger.info("🎯 Starting HIGH-PRECISION 17-point calibration with white background lighting...")
            success = self._run_white_background_calibration()
            
            if success:
                self.is_calibrated = True
                
                # Run quick accuracy validation test
                logger.info("🧪 Running quick accuracy test (5 points, ~8 seconds)...")
                accuracy_score = self._test_calibration_accuracy()
                
                if accuracy_score >= 0.7:
                    message = f"Calibration successful! Accuracy score: {accuracy_score:.1%}\n\nYour eye tracking should work reasonably well."
                    logger.info(f"Good calibration accuracy: {accuracy_score:.1%}")
                elif accuracy_score >= 0.5:
                    message = f"Calibration completed with moderate accuracy: {accuracy_score:.1%}\n\nEye tracking may be somewhat inaccurate. Consider recalibrating with better lighting/positioning."
                    logger.warning(f"Moderate calibration accuracy: {accuracy_score:.1%}")
                else:
                    message = f"Calibration completed with low accuracy: {accuracy_score:.1%}\n\nEye tracking will likely be quite inaccurate. Try:\n• Better lighting\n• Different head position\n• Recalibrating\n• This system may not work well for your setup"
                    logger.error(f"Poor calibration accuracy: {accuracy_score:.1%}")
                
                # Force status update to ensure UI reflects calibrated state
                logger.info(f"🔄 Final calibration status check: is_calibrated = {self.is_calibrated}")
                logger.info(f"🔄 Eye tracking available: {self.is_available()}")
                
                logger.info("Eye tracking calibration completed successfully")
                self.calibration_completed.emit(True, message)
            else:
                logger.error("White background calibration failed")
                self.calibration_completed.emit(False, "Calibration was cancelled or failed")
            
        except Exception as e:
            logger.error(f"Calibration error: {e}")
            self.calibration_completed.emit(False, f"Calibration failed: {str(e)}")
    
    def _run_white_background_calibration(self):
        """Run 9-point calibration with white background for optimal lighting."""
        import cv2
        import numpy as np
        import time
        
        try:
            # Initialize camera
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                logger.error("Failed to open camera for calibration")
                return False
            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Wait for face detection with white background
            if not self._wait_for_face_white_background(cap):
                cap.release()
                cv2.destroyAllWindows()
                return False
            
            # Define 17-point HIGH-PRECISION calibration grid for maximum accuracy
            order = [
                (2, 2),  # Center first - most important
                (0, 0),  # Corners
                (4, 0),  
                (0, 4),  
                (4, 4),  
                (2, 0),  # Edge centers
                (0, 2),  
                (4, 2),  
                (2, 4),  
                (1, 1),  # Inner ring for better interpolation
                (3, 1),  
                (1, 3),  
                (3, 3),  
                (1, 2),  # Additional precision points
                (3, 2),  
                (2, 1),  
                (2, 3),  
            ]
            
            # Compute calibration points for 5x5 grid for maximum coverage
            margin_ratio = 0.08  # Slightly smaller margin for more coverage  
            max_r, max_c = 4, 4
            mx, my = int(self.screen_width * margin_ratio), int(self.screen_height * margin_ratio)
            gw, gh = self.screen_width - 2 * mx, self.screen_height - 2 * my
            step_x = gw / max_c
            step_y = gh / max_r
            
            points = [(mx + int(c * step_x), my + int(r * step_y)) for r, c in order]
            
            # Run extended calibration with white background
            result = self._pulse_and_capture_white_background(cap, points)
            
            cap.release()
            cv2.destroyAllWindows()
            
            if result is None:
                return False
            
            features, targets = result
            if features and len(features) > 100:  # Ensure we have enough data
                # Train the gaze estimator
                logger.info(f"🔄 Training eye tracking model with {len(features)} data points...")
                try:
                    self.estimator.train(np.array(features), np.array(targets))
                    logger.info(f"✅ HIGH-PRECISION CALIBRATION SUCCESSFUL with {len(features)} data points")
                    logger.info(f"📊 Model trained on 17-point calibration grid with white background lighting")
                    
                    # Ensure calibration status is properly set
                    self.is_calibrated = True
                    logger.info(f"🎯 Calibration status confirmed: {self.is_calibrated}")
                    return True
                except Exception as e:
                    logger.error(f"❌ Training failed: {e}")
                    return False
            else:
                logger.error(f"❌ Insufficient calibration data: only {len(features) if features else 0} samples collected")
                logger.error("❌ Need at least 100 samples for reliable calibration")
                return False
                
        except Exception as e:
            logger.error(f"White background calibration failed: {e}")
            cv2.destroyAllWindows()
            return False
    
    def _wait_for_face_white_background(self, cap, dur=2):
        """Wait for face detection with white background."""
        import cv2
        import numpy as np
        import time
        
        cv2.namedWindow("Eye Tracking Calibration", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("Eye Tracking Calibration", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        fd_start = None
        countdown = False
        brightness = 240  # Slightly less bright for text visibility
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
                
            # Extract features and check for face
            features, blink = self.estimator.extract_features(frame)
            face_detected = features is not None and not blink
            
            # Create white canvas
            canvas = np.ones((self.screen_height, self.screen_width, 3), dtype=np.uint8) * brightness
            
            now = time.time()
            if face_detected:
                if not countdown:
                    fd_start = now
                    countdown = True
                    
                elapsed = now - fd_start
                if elapsed >= dur:
                    return True
                    
                # Draw countdown circle (dark on white background)
                t = elapsed / dur
                ease = t * t * (3 - 2 * t)
                angle = 360 * (1 - ease)
                cv2.ellipse(
                    canvas,
                    (self.screen_width // 2, self.screen_height // 2),
                    (50, 50),
                    0,
                    -90,
                    -90 + angle,
                    (0, 150, 0),  # Dark green on white
                    -1,
                )
                
                # Add instructional text
                cv2.putText(canvas, "Face detected - Hold still for HIGH-PRECISION calibration", 
                          (self.screen_width//2 - 300, self.screen_height//2 - 100), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (50, 50, 50), 2)
            else:
                countdown = False
                fd_start = None
                
                # Show face detection message
                cv2.putText(canvas, "HIGH-PRECISION 17-POINT CALIBRATION", 
                          (self.screen_width//2 - 250, self.screen_height//2 - 80), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, (50, 50, 180), 3)
                cv2.putText(canvas, "Look at the camera and position your face", 
                          (self.screen_width//2 - 250, self.screen_height//2 - 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 50, 50), 2)
                cv2.putText(canvas, "Face not detected", 
                          (self.screen_width//2 - 120, self.screen_height//2 + 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 50, 50), 3)
                cv2.putText(canvas, "Press ESC to cancel", 
                          (self.screen_width//2 - 100, self.screen_height//2 + 100), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            
            cv2.imshow("Eye Tracking Calibration", canvas)
            
            if cv2.waitKey(1) == 27:  # ESC to cancel
                return False
    
    def _pulse_and_capture_white_background(self, cap, points, pulse_duration=0.8, capture_duration=1.7):
        """Calibration point sequence with white background."""
        import cv2
        import numpy as np
        import time
        
        features_list = []
        targets_list = []
        brightness = 240
        
        for i, (x, y) in enumerate(points):
            logger.info(f"High-precision calibration point {i+1}/{len(points)}: ({x}, {y})")
            
            # Pulse phase - growing/shrinking circle  
            pulse_start = time.time()
            final_radius = 25  # Slightly larger for better visibility
            
            while True:
                elapsed = time.time() - pulse_start
                if elapsed > pulse_duration:
                    break
                    
                ok, frame = cap.read()
                if not ok:
                    continue
                
                # Create white canvas
                canvas = np.ones((self.screen_height, self.screen_width, 3), dtype=np.uint8) * brightness
                
                # Pulsing circle (dark red on white background)
                radius = 20 + int(10 * abs(np.sin(4 * np.pi * elapsed)))  # Faster pulse
                final_radius = radius
                cv2.circle(canvas, (x, y), radius, (30, 30, 180), -1)  # Darker blue-red
                
                # Enhanced progress indicator
                progress_text = f"HIGH-PRECISION CALIBRATION: Point {i+1} of {len(points)} (~{len(points)*2.5:.0f}s total)"
                cv2.putText(canvas, progress_text, (50, 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, (50, 50, 50), 3)
                
                cv2.putText(canvas, "Look directly at the pulsing dot", (50, 100), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 50, 50), 2)
                
                # Show overall progress
                progress_percent = int((i / len(points)) * 100)
                cv2.putText(canvas, f"Overall Progress: {progress_percent}%", (50, 150), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 100, 100), 2)
                
                cv2.imshow("Eye Tracking Calibration", canvas)
                
                if cv2.waitKey(1) == 27:  # ESC to cancel
                    return None
            
            # Extended capture phase - collect more gaze data
            capture_start = time.time()
            point_features = []
            point_targets = []
            sample_count = 0
            
            while True:
                elapsed = time.time() - capture_start
                if elapsed > capture_duration:
                    break
                    
                ok, frame = cap.read()
                if not ok:
                    continue
                
                # Create white canvas
                canvas = np.ones((self.screen_height, self.screen_width, 3), dtype=np.uint8) * brightness
                
                # Static circle with countdown ring
                cv2.circle(canvas, (x, y), final_radius, (30, 30, 180), -1)  # Darker blue-red
                
                # Countdown ring
                t = elapsed / capture_duration
                ease = t * t * (3 - 2 * t)
                angle = 360 * (1 - ease)
                cv2.ellipse(canvas, (x, y), (50, 50), 0, -90, -90 + angle, (20, 120, 20), 6)  # Thicker green ring
                
                # Enhanced progress indicator
                remaining = capture_duration - elapsed
                progress_text = f"HIGH-PRECISION: Point {i+1} of {len(points)} - {remaining:.1f}s"
                cv2.putText(canvas, progress_text, (50, 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, (50, 50, 50), 3)
                
                cv2.putText(canvas, "HOLD YOUR GAZE STEADY on the dot", (50, 100), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 50, 50), 2)
                
                # Show sample collection progress
                cv2.putText(canvas, f"Samples collected: {sample_count}", (50, 150), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.9, (50, 100, 50), 2)
                
                # Show overall progress
                progress_percent = int(((i + t) / len(points)) * 100)
                cv2.putText(canvas, f"Overall Progress: {progress_percent}%", (50, 200), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.9, (100, 100, 100), 2)
                
                cv2.imshow("Eye Tracking Calibration", canvas)
                
                if cv2.waitKey(1) == 27:  # ESC to cancel
                    return None
                
                # Collect gaze data with quality check
                features, blink = self.estimator.extract_features(frame)
                if features is not None and not blink:
                    point_features.append(features)
                    point_targets.append([x, y])
                    sample_count += 1
            
            # Add collected data with validation
            if point_features:
                features_list.extend(point_features)
                targets_list.extend(point_targets)
                logger.info(f"Collected {len(point_features)} high-quality samples for point {i+1}")
                
                # Quality check - warn if too few samples
                if len(point_features) < 30:  # Expect ~120 samples at 30 FPS for 4 seconds
                    logger.warning(f"Point {i+1} only collected {len(point_features)} samples - may affect accuracy")
            else:
                logger.error(f"❌ No data collected for point {i+1} - this will significantly hurt accuracy!")
        
        total_samples = len(features_list)
        logger.info(f"🎯 HIGH-PRECISION CALIBRATION COMPLETE: {total_samples} total samples from {len(points)} points")
        
        # Quality assessment (high standards for precision)
        if total_samples >= 1000:
            logger.info(f"✅ Excellent data quality: {total_samples} samples should provide excellent accuracy")
        elif total_samples >= 600:
            logger.info(f"✅ Very good data quality: {total_samples} samples should provide high accuracy")
        elif total_samples >= 400:
            logger.info(f"✅ Good data quality: {total_samples} samples should provide decent accuracy")
        else:
            logger.warning(f"⚠️ Limited data quality: Only {total_samples} samples - accuracy may be lower")
        
        return features_list, targets_list if features_list else None
    
    def _test_calibration_accuracy(self):
        """Test calibration accuracy with white background lighting and visual confirmation."""
        try:
            import cv2
            import numpy as np
            
            # Initialize camera for accuracy test
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                return 0.5  # Default score if can't test
            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            logger.info("🎯 Running accuracy test with white background lighting...")
            logger.info("📝 NOTE: This test measures calibration quality - it does NOT recalibrate!")
            
            # Test points: center and corners (same as some calibration points)
            test_points = [
                (self.screen_width // 2, self.screen_height // 2),  # Center
                (self.screen_width // 4, self.screen_height // 4),  # Top-left quadrant
                (3 * self.screen_width // 4, self.screen_height // 4),  # Top-right quadrant  
                (self.screen_width // 4, 3 * self.screen_height // 4),  # Bottom-left quadrant
                (3 * self.screen_width // 4, 3 * self.screen_height // 4),  # Bottom-right quadrant
            ]
            
            accuracy_scores = []
            brightness = 240
            
            cv2.namedWindow("Calibration Accuracy Test", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("Calibration Accuracy Test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            
            for i, (target_x, target_y) in enumerate(test_points):
                logger.info(f"Testing accuracy at point {i+1}/{len(test_points)}: ({target_x}, {target_y})")
                
                # Show test point with white background for 2 seconds
                samples = []
                start_time = time.time()
                sample_count = 0
                
                while time.time() - start_time < 1.5:  # 1.5 second test per point
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    
                    # Create white canvas (consistent with calibration)
                    canvas = np.ones((self.screen_height, self.screen_width, 3), dtype=np.uint8) * brightness
                    
                    # Draw test point
                    cv2.circle(canvas, (target_x, target_y), 25, (200, 50, 50), -1)  # Red test dot
                    cv2.circle(canvas, (target_x, target_y), 30, (100, 30, 30), 3)   # Dark red outline
                    
                    # Add test instructions
                    elapsed = time.time() - start_time
                    remaining = 1.5 - elapsed
                    cv2.putText(canvas, f"ACCURACY TEST: Look at the red dot", (50, 50), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1.2, (50, 50, 50), 3)
                    cv2.putText(canvas, f"Point {i+1} of {len(test_points)} - {remaining:.1f}s remaining", (50, 100), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 50, 50), 2)
                    cv2.putText(canvas, f"Testing calibration quality (not recalibrating)", (50, 130), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
                    cv2.putText(canvas, f"Samples collected: {sample_count}", (50, 160), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.9, (50, 100, 50), 2)
                    
                    cv2.imshow("Calibration Accuracy Test", canvas)
                    cv2.waitKey(1)
                    
                    # Collect gaze prediction samples
                    features, blink = self.estimator.extract_features(frame)
                    if features is not None and not blink:
                        try:
                            gaze_coords = self.estimator.predict([features])
                            if len(gaze_coords) > 0:
                                pred_x, pred_y = gaze_coords[0]
                                # Clamp predictions to screen bounds
                                pred_x = max(0, min(self.screen_width, pred_x))
                                pred_y = max(0, min(self.screen_height, pred_y))
                                samples.append((pred_x, pred_y))
                                sample_count += 1
                        except Exception as e:
                            logger.warning(f"Prediction failed during accuracy test: {e}")
                
                # Calculate accuracy for this point
                if len(samples) >= 3:  # Need at least a few samples
                    avg_x = sum(x for x, y in samples) / len(samples)
                    avg_y = sum(y for x, y in samples) / len(samples)
                    
                    # Calculate distance error
                    distance = ((avg_x - target_x) ** 2 + (avg_y - target_y) ** 2) ** 0.5
                    
                    # Normalize to screen diagonal for relative accuracy
                    screen_diagonal = (self.screen_width ** 2 + self.screen_height ** 2) ** 0.5
                    normalized_error = distance / screen_diagonal
                    
                    # Convert to accuracy percentage (0-100%)
                    # 0% error = 100% accuracy, higher error = lower accuracy
                    accuracy_percent = max(0, 100 * (1.0 - normalized_error * 8))  # More lenient scale
                    accuracy_scores.append(accuracy_percent / 100.0)  # Store as 0-1 for averaging
                    
                    logger.info(f"Point {i+1}: Distance error {distance:.1f}px, Accuracy: {accuracy_percent:.1f}% ({len(samples)} samples)")
                else:
                    logger.warning(f"Point {i+1}: Insufficient samples ({len(samples)}) for accuracy test")
                    accuracy_scores.append(0.1)  # Low accuracy for insufficient data
            
            cv2.destroyWindow("Calibration Accuracy Test")
            cap.release()
            
            if accuracy_scores:
                final_accuracy = sum(accuracy_scores) / len(accuracy_scores)
                logger.info(f"📊 Overall calibration accuracy: {final_accuracy:.1%} across {len(test_points)} test points")
                return final_accuracy
            else:
                logger.error("❌ No accuracy scores calculated")
                return 0.1  # Very low default
                
        except Exception as e:
            logger.error(f"Accuracy test failed: {e}")
            cv2.destroyAllWindows()
            return 0.2  # Low default if test fails
    
    def start_recording(self, session_id, lap_id=None):
        """Start recording eye tracking data for a session/lap."""
        # For recording, ensure eye tracking is enabled AND available AND calibrated
        if not self.enabled:
            self.error_occurred.emit("Eye tracking is disabled")
            return False
        
        if not self.is_available() or not self.is_calibrated:
            self.error_occurred.emit("Eye tracking not calibrated")
            return False
        
        if self.is_recording:
            self.stop_recording()
        
        self.current_session_id = session_id
        self.current_lap_id = lap_id
        self.is_recording = True
        self._stop_recording.clear()
        self._recording_start_time = time.time()
        
        # Start recording thread
        self._recording_thread = threading.Thread(target=self._recording_loop)
        self._recording_thread.daemon = True
        self._recording_thread.start()
        
        logger.info(f"Started eye tracking recording for session {session_id}")
        return True
    
    def stop_recording(self):
        """Stop recording eye tracking data."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        self._stop_recording.set()
        
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=2.0)
        
        logger.info("Stopped eye tracking recording")
    
    def _recording_loop(self):
        """Main recording loop that captures gaze data."""
        # Initialize camera
        self.capture = cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            self.error_occurred.emit("Failed to open camera for eye tracking")
            return
        
        # Set camera properties for better performance
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capture.set(cv2.CAP_PROP_FPS, 30)
        
        # Gaze overlay window for real-time feedback
        overlay_window = None
        if config.eye_tracking_show_overlay:
            cv2.namedWindow("Gaze Tracking - Where You're Looking", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Gaze Tracking - Where You're Looking", self.screen_width // 3, self.screen_height // 3)
            overlay_window = True
            logger.info("Gaze overlay window created")
        
        # Camera debug window
        if config.eye_tracking_show_overlay:  # Only show if overlay is enabled
            cv2.namedWindow("Eye Tracking Camera Debug", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Eye Tracking Camera Debug", 320, 240)
            logger.info("Camera debug window created")
        
        frame_count = 0
        fps_counter = 0
        fps_start_time = time.time()
        
        try:
            while not self._stop_recording.is_set() and self.is_recording:
                # Capture frame
                ret, frame = self.capture.read()
                if not ret:
                    continue
                
                frame_count += 1
                current_time = time.time()
                
                # Calculate FPS every second
                if current_time - fps_start_time >= 1.0:
                    fps_counter = frame_count
                    frame_count = 0
                    fps_start_time = current_time
                
                # Show camera debug info
                if config.eye_tracking_show_overlay and frame is not None:
                    debug_frame = frame.copy()
                    
                    # Add debug text overlay on camera feed
                    debug_text = [
                        f"Camera: Active ({fps_counter} FPS)",
                        f"Resolution: {debug_frame.shape[1]}x{debug_frame.shape[0]}",
                        f"Eye Tracking: {'Calibrated' if self.is_calibrated else 'Not Calibrated'}",
                        f"Recording: {'Yes' if self.is_recording else 'No'}"
                    ]
                    
                    for i, text in enumerate(debug_text):
                        cv2.putText(debug_frame, text, (10, 30 + i * 25), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.imshow("Eye Tracking Camera Debug", debug_frame)
                
                # Extract eye features
                features, blink = self.estimator.extract_features(frame)
                
                # Predict gaze if features detected and not blinking
                if features is not None:
                    current_time = time.time()
                    relative_time = current_time - self._recording_start_time
                    
                    gaze_data = {
                        'timestamp': relative_time,
                        'blink_detected': blink,
                        'features': features.tolist() if hasattr(features, 'tolist') else features,
                        'screen_width': self.screen_width,
                        'screen_height': self.screen_height,
                        'confidence': 0.8,  # Default confidence, can be improved
                        'session_id': self.current_session_id,
                        'lap_id': self.current_lap_id
                    }
                    
                    if not blink:
                        try:
                            # Predict gaze coordinates
                            gaze_coords = self.estimator.predict([features])
                            if len(gaze_coords) > 0:
                                x, y = gaze_coords[0]
                                
                                # Clamp coordinates to screen bounds
                                x = max(0, min(self.screen_width - 1, x))
                                y = max(0, min(self.screen_height - 1, y))
                                
                                # Store actual pixel coordinates
                                gaze_data['gaze_x_pixel'] = int(x)
                                gaze_data['gaze_y_pixel'] = int(y)
                                
                                # Normalize coordinates to 0-1 range
                                gaze_data['gaze_x'] = x / self.screen_width
                                gaze_data['gaze_y'] = y / self.screen_height
                                
                                # Show gaze overlay if enabled
                                if config.eye_tracking_show_overlay and overlay_window:
                                    self._update_gaze_overlay(x, y, blink)
                                    
                            else:
                                gaze_data['gaze_x'] = 0.5  # Default to center
                                gaze_data['gaze_y'] = 0.5
                                gaze_data['gaze_x_pixel'] = self.screen_width // 2
                                gaze_data['gaze_y_pixel'] = self.screen_height // 2
                        except Exception as e:
                            logger.warning(f"Gaze prediction failed: {e}")
                            gaze_data['gaze_x'] = 0.5
                            gaze_data['gaze_y'] = 0.5
                            gaze_data['gaze_x_pixel'] = self.screen_width // 2
                            gaze_data['gaze_y_pixel'] = self.screen_height // 2
                    else:
                        # During blink, use last known position or center
                        gaze_data['gaze_x'] = 0.5
                        gaze_data['gaze_y'] = 0.5
                        gaze_data['gaze_x_pixel'] = self.screen_width // 2
                        gaze_data['gaze_y_pixel'] = self.screen_height // 2
                        
                        # Show blink in overlay
                        if config.eye_tracking_show_overlay and overlay_window:
                            self._update_gaze_overlay(self.screen_width // 2, self.screen_height // 2, True)
                    
                    # Buffer the data
                    with self._buffer_lock:
                        self._gaze_data_buffer.append(gaze_data)
                    
                    # Emit signal for real-time processing
                    self.eye_tracking_data.emit(gaze_data)
                
                # Handle window events
                if config.eye_tracking_show_overlay:
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("User pressed 'q' - stopping eye tracking")
                        break
                
                # Small delay to control frame rate
                time.sleep(1/30)  # 30 FPS
                
        except Exception as e:
            logger.error(f"Error in eye tracking recording loop: {e}")
            self.error_occurred.emit(f"Eye tracking error: {str(e)}")
        finally:
            # Clean up windows
            if config.eye_tracking_show_overlay:
                cv2.destroyAllWindows()
                logger.info("Closed eye tracking debug windows")
            
            if self.capture:
                self.capture.release()
            self.capture = None
    
    def _update_gaze_overlay(self, gaze_x, gaze_y, is_blink=False):
        """Update the gaze overlay window with current gaze position using white background."""
        try:
            # Create white overlay canvas for consistent lighting
            overlay_canvas = np.ones((self.screen_height // 3, self.screen_width // 3, 3), dtype=np.uint8) * 240
            
            # Scale gaze coordinates to overlay size
            scale_x = (self.screen_width // 3) / self.screen_width
            scale_y = (self.screen_height // 3) / self.screen_height
            
            overlay_x = int(gaze_x * scale_x)
            overlay_y = int(gaze_y * scale_y)
            
            # Draw background grid for reference (darker lines on white)
            grid_spacing = 50
            for i in range(0, self.screen_width // 3, grid_spacing):
                cv2.line(overlay_canvas, (i, 0), (i, self.screen_height // 3), (180, 180, 180), 1)
            for i in range(0, self.screen_height // 3, grid_spacing):
                cv2.line(overlay_canvas, (0, i), (self.screen_width // 3, i), (180, 180, 180), 1)
            
            # Draw crosshairs at center (darker on white)
            center_x = (self.screen_width // 3) // 2
            center_y = (self.screen_height // 3) // 2
            cv2.line(overlay_canvas, (center_x - 20, center_y), (center_x + 20, center_y), (120, 120, 120), 1)
            cv2.line(overlay_canvas, (center_x, center_y - 20), (center_x, center_y + 20), (120, 120, 120), 1)
            
            # Draw gaze point
            if is_blink:
                # Red circle for blink (dark on white)
                cv2.circle(overlay_canvas, (overlay_x, overlay_y), 15, (50, 50, 200), -1)
                cv2.putText(overlay_canvas, "BLINK", (overlay_x - 25, overlay_y - 25), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 200), 2)
            else:
                # Green circle for active gaze (dark on white)
                cv2.circle(overlay_canvas, (overlay_x, overlay_y), 12, (50, 180, 50), -1)
                cv2.circle(overlay_canvas, (overlay_x, overlay_y), 18, (30, 150, 30), 2)
            
            # Add status text (dark on white)
            status_text = f"Gaze: ({int(gaze_x)}, {int(gaze_y)})"
            cv2.putText(overlay_canvas, status_text, (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
            
            cv2.putText(overlay_canvas, "White background = optimal lighting", (10, overlay_canvas.shape[0] - 40), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            cv2.putText(overlay_canvas, "Press 'q' to close", (10, overlay_canvas.shape[0] - 20), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            cv2.imshow("Gaze Tracking - Where You're Looking", overlay_canvas)
            
        except Exception as e:
            logger.warning(f"Error updating gaze overlay: {e}")
    
    def update_telemetry_sync(self, telemetry_data):
        """Update synchronization with telemetry data."""
        if 'timestamp' in telemetry_data:
            self._last_telemetry_timestamp = telemetry_data['timestamp']
    
    def update_lap_id(self, lap_id):
        """Update the current lap ID for data association."""
        self.current_lap_id = lap_id
        logger.debug(f"Updated eye tracking lap ID to: {lap_id}")
    
    def get_buffered_data(self):
        """Get and clear the buffered gaze data."""
        with self._buffer_lock:
            data = self._gaze_data_buffer.copy()
            self._gaze_data_buffer.clear()
        return data
    
    def save_calibration(self, file_path):
        """Save the current calibration to a file."""
        if not self.is_calibrated or not self.estimator:
            return False
        
        try:
            self.estimator.save_model(str(file_path))
            logger.info(f"Eye tracking calibration saved to: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            return False
    
    def load_calibration(self, file_path):
        """Load a calibration from a file."""
        if not self.is_available():
            return False
        
        try:
            self.estimator.load_model(str(file_path))
            self.is_calibrated = True
            logger.info(f"Eye tracking calibration loaded from: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load calibration: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_recording()
        self.stop_persistent_overlay()
        
        # Clean up gaming overlay
        if hasattr(self, 'gaming_overlay_manager'):
            self.gaming_overlay_manager.cleanup()
        
        if self.capture:
            self.capture.release()
            self.capture = None
        logger.info("Eye tracking manager cleaned up")
    
    def update_session_state(self, telemetry_data):
        """Update session state based on telemetry data.
        
        This determines when we should be recording eye tracking data.
        Only record when the driver is actually driving in a session.
        """
        if not self.enabled:
            return
        
        # Extract session information from telemetry
        session_state = telemetry_data.get('SessionState', 4)  # 4 = Invalid
        is_on_track = telemetry_data.get('IsOnTrack', False)
        speed = telemetry_data.get('Speed', 0)
        
        # Update tracking state
        self.is_on_track = is_on_track
        self.is_driving = is_on_track and speed > 5  # Consider driving if on track and moving
        
        # Determine if we're in a racing session
        # SessionState: 0=Invalid, 1=GetInCar, 2=Warmup, 3=ParadeLaps, 4=Racing, 5=Checkered, 6=CoolDown
        racing_states = [2, 3, 4]  # Warmup, ParadeLaps, Racing
        was_in_session = self.is_in_racing_session
        self.is_in_racing_session = session_state in racing_states
        
        # Auto-start/stop recording based on session state
        if self.auto_start and self.is_calibrated:
            should_record = self.is_in_racing_session and self.is_driving
            
            if should_record and not self.is_recording:
                logger.info("Auto-starting eye tracking recording (driver is racing)")
                self.start_recording(self.current_session_id)
            elif not should_record and self.is_recording:
                logger.info("Auto-stopping eye tracking recording (not racing)")
                self.stop_recording()
    
    def set_session_info(self, session_id, session_type=None):
        """Set the current session information."""
        self.current_session_id = session_id
        self.session_type = session_type
        logger.info(f"Eye tracking session info updated: {session_id} ({session_type})")
    
    def is_ready_to_record(self):
        """Check if eye tracking is ready to record."""
        if not self.enabled:
            return False, "Eye tracking is disabled"
        
        if not self.is_available():
            return False, "Eye tracking not available"
        
        if self.require_calibration and not self.is_calibrated:
            return False, "Eye tracking not calibrated"
        
        if not self.current_session_id:
            return False, "No active session"
        
        return True, "Ready to record"
    
    def test_gaze_tracking(self, duration=30):
        """Test gaze tracking with real-time overlay for a specified duration (in seconds)."""
        if not self.is_available():
            self.error_occurred.emit("Eye tracking not available for testing")
            return False
        
        if not self.is_calibrated:
            self.error_occurred.emit("Please calibrate eye tracking before testing")
            return False
        
        logger.info(f"Starting gaze tracking test for {duration} seconds...")
        
        # Initialize camera
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error_occurred.emit("Failed to open camera for testing")
            return False
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Get screen dimensions for overlay
        from PyQt5.QtWidgets import QApplication, QDesktopWidget
        app = QApplication.instance()
        if app:
            desktop = app.desktop()
            screen_rect = desktop.screenGeometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()
        else:
            screen_width = 1920
            screen_height = 1080
        
        # Create windows
        cv2.namedWindow("Gaze Tracking Test - Where You're Looking", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Gaze Tracking Test - Where You're Looking", screen_width // 3, screen_height // 3)
        
        cv2.namedWindow("Eye Tracking Camera Test", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Eye Tracking Camera Test", 320, 240)
        
        start_time = time.time()
        frame_count = 0
        fps_counter = 0
        fps_start_time = time.time()
        
        try:
            logger.info("Test started - look around your screen and watch the green dot follow your gaze!")
            logger.info("Press 'q' or wait 30 seconds to stop the test")
            
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                current_time = time.time()
                elapsed = current_time - start_time
                remaining = duration - elapsed
                
                # Calculate FPS
                if current_time - fps_start_time >= 1.0:
                    fps_counter = frame_count
                    frame_count = 0
                    fps_start_time = current_time
                
                # Show camera debug
                debug_frame = frame.copy()
                debug_text = [
                    f"TEST MODE - Camera Active ({fps_counter} FPS)",
                    f"Resolution: {debug_frame.shape[1]}x{debug_frame.shape[0]}",
                    f"Time Remaining: {remaining:.1f}s",
                    f"Calibrated: {'Yes' if self.is_calibrated else 'No'}",
                    "Press 'q' to stop early"
                ]
                
                for i, text in enumerate(debug_text):
                    cv2.putText(debug_frame, text, (10, 30 + i * 25), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                cv2.imshow("Eye Tracking Camera Test", debug_frame)
                
                # Extract features and predict gaze
                features, blink = self.estimator.extract_features(frame)
                
                if features is not None:
                    try:
                        gaze_coords = self.estimator.predict([features])
                        if len(gaze_coords) > 0:
                            x, y = gaze_coords[0]
                            x = max(0, min(screen_width - 1, x))
                            y = max(0, min(screen_height - 1, y))
                            
                            # Update gaze overlay
                            self._update_test_gaze_overlay(x, y, blink, screen_width, screen_height, remaining)
                        else:
                            # No gaze detected, show center
                            self._update_test_gaze_overlay(screen_width // 2, screen_height // 2, True, screen_width, screen_height, remaining)
                    except Exception as e:
                        logger.warning(f"Gaze prediction failed during test: {e}")
                        self._update_test_gaze_overlay(screen_width // 2, screen_height // 2, True, screen_width, screen_height, remaining)
                
                # Check for exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("Test stopped by user")
                    break
                
                time.sleep(1/30)  # 30 FPS
                
        except Exception as e:
            logger.error(f"Error during gaze tracking test: {e}")
            return False
        finally:
            cap.release()
            cv2.destroyAllWindows()
            logger.info("Gaze tracking test completed")
        
        return True
    
    def start_persistent_overlay(self):
        """Start the gaming-style transparent overlay."""
        if not self.is_available():
            logger.error("Eye tracking not available for gaming overlay")
            return False
        
        if not self.is_calibrated:
            logger.error("Eye tracking not calibrated for gaming overlay")
            return False
        
        if self.is_overlay_active:
            logger.warning("Gaming overlay is already active")
            return True
        
        logger.info("🎮 Starting gaming-style eye tracking overlay...")
        
        try:
            # Start the camera tracking thread
            self._stop_overlay.clear()
            self._overlay_thread = threading.Thread(target=self._gaming_overlay_loop, daemon=True)
            self._overlay_thread.start()
            
            # Show the gaming overlay
            self.gaming_overlay_manager.show_overlay()
            self.is_overlay_active = True
            
            logger.info("✅ Gaming overlay started successfully - transparent dot will follow your gaze!")
            return True
        except Exception as e:
            logger.error(f"Failed to start gaming overlay: {e}")
            self.is_overlay_active = False
            return False
    
    def stop_persistent_overlay(self):
        """Stop the gaming-style transparent overlay."""
        if not self.is_overlay_active:
            logger.warning("Gaming overlay is not active")
            return
        
        logger.info("🎮 Stopping gaming-style eye tracking overlay...")
        
        try:
            # Stop the camera thread
            self._stop_overlay.set()
            self.is_overlay_active = False
            
            if self._overlay_thread and self._overlay_thread.is_alive():
                self._overlay_thread.join(timeout=2.0)
            
            # Hide the gaming overlay
            self.gaming_overlay_manager.hide_overlay()
            
            logger.info("✅ Gaming overlay stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping gaming overlay: {e}")
    
    def _gaming_overlay_loop(self):
        """Main loop for the gaming overlay functionality."""
        logger.info("🎮 Gaming overlay loop starting...")
        
        # Initialize camera
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logger.error("Failed to open camera for gaming overlay")
            self.is_overlay_active = False
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Get screen dimensions
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            desktop = app.desktop()
            screen_rect = desktop.screenGeometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()
        else:
            screen_width = 1920
            screen_height = 1080
        
        frame_count = 0
        fps_counter = 0
        fps_start_time = time.time()
        
        try:
            logger.info("🎮 Gaming overlay active - transparent gaze dot will follow your eyes!")
            
            while not self._stop_overlay.is_set():
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                current_time = time.time()
                
                # Calculate FPS (for internal monitoring)
                if current_time - fps_start_time >= 1.0:
                    fps_counter = frame_count
                    frame_count = 0
                    fps_start_time = current_time
                
                # Extract features and predict gaze
                features, blink = self.estimator.extract_features(frame)
                
                if features is not None:
                    try:
                        gaze_coords = self.estimator.predict([features])
                        if len(gaze_coords) > 0:
                            x, y = gaze_coords[0]
                            x = max(0, min(screen_width - 1, x))
                            y = max(0, min(screen_height - 1, y))
                            
                            # Update gaming overlay with gaze position
                            self.gaming_overlay_manager.update_gaze(x, y, blink)
                        else:
                            # No gaze detected - hide dot
                            self.gaming_overlay_manager.set_tracking_active(False)
                    except Exception as e:
                        logger.warning(f"Gaze prediction failed during gaming overlay: {e}")
                        self.gaming_overlay_manager.set_tracking_active(False)
                else:
                    # No features detected - hide dot
                    self.gaming_overlay_manager.set_tracking_active(False)
                
                # Run at 30 FPS for smooth overlay
                time.sleep(1/30)
                
        except Exception as e:
            logger.error(f"Error in gaming overlay loop: {e}")
        finally:
            cap.release()
            self.is_overlay_active = False
            logger.info("🎮 Gaming overlay loop ended")
    

    
    def _update_test_gaze_overlay(self, gaze_x, gaze_y, is_blink, screen_width, screen_height, time_remaining):
        """Update the test gaze overlay window with white background lighting."""
        try:
            overlay_width = screen_width // 3
            overlay_height = screen_height // 3
            
            # Create white overlay canvas for consistent lighting
            overlay_canvas = np.ones((overlay_height, overlay_width, 3), dtype=np.uint8) * 240
            
            # Scale gaze coordinates
            scale_x = overlay_width / screen_width
            scale_y = overlay_height / screen_height
            
            overlay_x = int(gaze_x * scale_x)
            overlay_y = int(gaze_y * scale_y)
            
            # Draw background grid for reference (darker on white)
            grid_spacing = 50
            for i in range(0, overlay_width, grid_spacing):
                cv2.line(overlay_canvas, (i, 0), (i, overlay_height), (180, 180, 180), 1)
            for i in range(0, overlay_height, grid_spacing):
                cv2.line(overlay_canvas, (0, i), (overlay_width, i), (180, 180, 180), 1)
            
            # Draw crosshairs at center (darker on white)
            center_x = overlay_width // 2
            center_y = overlay_height // 2
            cv2.line(overlay_canvas, (center_x - 20, center_y), (center_x + 20, center_y), (120, 120, 120), 2)
            cv2.line(overlay_canvas, (center_x, center_y - 20), (center_x, center_y + 20), (120, 120, 120), 2)
            
            # Draw gaze point
            if is_blink:
                # Red circle for blink (dark on white)
                cv2.circle(overlay_canvas, (overlay_x, overlay_y), 15, (50, 50, 200), -1)
                cv2.putText(overlay_canvas, "BLINK", (overlay_x - 25, overlay_y - 25), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 200), 2)
            else:
                # Green circle for active gaze (dark on white)
                cv2.circle(overlay_canvas, (overlay_x, overlay_y), 12, (50, 180, 50), -1)
                cv2.circle(overlay_canvas, (overlay_x, overlay_y), 18, (30, 150, 30), 2)
            
            # Add test status info (dark text on white)
            cv2.putText(overlay_canvas, "GAZE TRACKING TEST", (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 180), 2)
            
            status_text = f"Gaze: ({int(gaze_x)}, {int(gaze_y)})"
            cv2.putText(overlay_canvas, status_text, (10, 60), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
            
            time_text = f"Time remaining: {time_remaining:.1f}s"
            cv2.putText(overlay_canvas, time_text, (10, 90), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 50, 50), 2)
            
            cv2.putText(overlay_canvas, "White background = optimal lighting", (10, overlay_height - 40), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            cv2.putText(overlay_canvas, "Press 'q' to stop test early", (10, overlay_height - 20), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            cv2.imshow("Gaze Tracking Test - Where You're Looking", overlay_canvas)
            
        except Exception as e:
            logger.warning(f"Error updating test gaze overlay: {e}") 