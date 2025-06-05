#!/usr/bin/env python3
"""
Standalone UI test for Threshold Braking Assist

This script creates a simple window to test the threshold braking assist UI
and functionality without running the full TrackPro application.
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# Add the trackpro module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import directly from the file to avoid ui.py vs ui/ conflict
import sys
import os
threshold_panel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trackpro', 'ui', 'threshold_assist_panel.py')
import importlib.util
spec = importlib.util.spec_from_file_location("threshold_assist_panel", threshold_panel_path)
threshold_assist_panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(threshold_assist_panel)
ThresholdAssistPanel = threshold_assist_panel.ThresholdAssistPanel
from trackpro.pedals.hardware_input import HardwareInput
from trackpro.pedals.output import VirtualJoystick

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ThresholdAssistUITest")

class MockApp:
    """Mock application instance to simulate the main TrackPro app."""
    
    def __init__(self):
        """Initialize mock app with hardware."""
        logger.info("Initializing mock application for threshold assist testing")
        
        # Initialize hardware (enable test_mode to allow Xbox controller)
        try:
            self.hardware = HardwareInput(test_mode=True)
            if hasattr(self.hardware, 'using_xbox_controller') and self.hardware.using_xbox_controller:
                logger.info("Hardware initialized with Xbox Controller for testing")
            elif self.hardware.pedals_connected:
                logger.info("Hardware initialized with P1 Pro Pedals")
            else:
                logger.info("Hardware initialized in test mode (no controller)")
        except Exception as e:
            logger.warning(f"Hardware initialization failed: {e}")
            self.hardware = HardwareInput(test_mode=True)
        
        # Initialize virtual joystick
        try:
            self.output = VirtualJoystick(test_mode=False)
            logger.info("Virtual joystick initialized successfully")
        except Exception as e:
            logger.warning(f"Virtual joystick initialization failed, using test mode: {e}")
            self.output = VirtualJoystick(test_mode=True)
        
        # Set up mock telemetry
        self.mock_abs_active = False
        self.test_track = "Road Atlanta"
        self.test_car = "Mazda MX-5 Cup"
        
        # Configure threshold assist
        self.setup_threshold_assist()
        
        logger.info("Mock application initialized")
    
    def setup_threshold_assist(self):
        """Set up threshold braking assist system."""
        # Set up telemetry callback
        self.hardware.set_telemetry_callback(self.get_mock_telemetry)
        
        # Set track/car context
        self.hardware.update_track_car_context(self.test_track, self.test_car)
        
        # Configure with defaults
        self.hardware.enable_threshold_assist(False)  # Start disabled
        self.hardware.set_threshold_reduction(2.0)
        
        logger.info("Threshold assist configured")
    
    def get_mock_telemetry(self):
        """Generate mock telemetry data."""
        return {
            'BrakeABSactive': self.mock_abs_active,
            'Brake': 0.5,  # Mock brake pressure
            'track_name': self.test_track,
            'car_name': self.test_car,
            'Speed': 85.3,
            'RPM': 4200
        }
    
    def enable_threshold_assist(self, enabled):
        """Enable or disable threshold assist."""
        self.hardware.enable_threshold_assist(enabled)
        logger.info(f"Threshold assist {'enabled' if enabled else 'disabled'}")
    
    def set_threshold_reduction(self, percentage):
        """Set threshold reduction percentage."""
        self.hardware.set_threshold_reduction(percentage)
        logger.info(f"Threshold reduction set to {percentage}%")
    
    def get_threshold_assist_status(self):
        """Get current threshold assist status."""
        return self.hardware.get_threshold_assist_status()
    
    def reset_threshold_learning(self):
        """Reset threshold learning data."""
        self.hardware.reset_threshold_learning()
        logger.info("Threshold learning data reset")
    
    def simulate_abs_lockup(self):
        """Simulate ABS activation for testing."""
        self.mock_abs_active = True
        logger.info("🚨 Simulated ABS activation")
        
        # Reset after 1 second
        QTimer.singleShot(1000, lambda: setattr(self, 'mock_abs_active', False))

class ThresholdAssistTestWindow(QMainWindow):
    """Main test window for threshold braking assist."""
    
    def __init__(self):
        super().__init__()
        self.mock_app = MockApp()
        self.setup_ui()
        
        # Start input processing timer
        self.input_timer = QTimer()
        self.input_timer.timeout.connect(self.process_input)
        self.input_timer.start(16)  # ~60 FPS
        
        logger.info("Test window initialized")
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Threshold Braking Assist - Test UI")
        self.setGeometry(100, 100, 600, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test controls
        test_controls = QWidget()
        test_layout = QHBoxLayout(test_controls)
        
        simulate_abs_btn = QPushButton("Simulate ABS Lockup")
        simulate_abs_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        simulate_abs_btn.clicked.connect(self.mock_app.simulate_abs_lockup)
        test_layout.addWidget(simulate_abs_btn)
        
        # Add some spacing
        test_layout.addStretch()
        
        layout.addWidget(test_controls)
        
        # Threshold assist panel
        self.threshold_panel = ThresholdAssistPanel()
        self.threshold_panel.set_app_instance(self.mock_app)
        layout.addWidget(self.threshold_panel)
        
        # Status bar
        self.statusBar().showMessage("Ready - Use your brake pedal to test threshold assist")
    
    def process_input(self):
        """Process pedal input and apply threshold assist."""
        try:
            # Read pedal values
            pedal_values = self.mock_app.hardware.read_pedals()
            
            # Process brake with assist
            raw_brake = pedal_values.get('brake', 0)
            calibrated_brake = self.mock_app.hardware.apply_calibration('brake', raw_brake)
            assisted_brake = self.mock_app.hardware.process_brake_with_assist(calibrated_brake)
            
            # Process other pedals normally
            throttle = self.mock_app.hardware.apply_calibration('throttle', pedal_values.get('throttle', 0))
            clutch = self.mock_app.hardware.apply_calibration('clutch', pedal_values.get('clutch', 0))
            
            # Send to virtual joystick
            throttle_vjoy = int(throttle * 32767 / 65535)
            brake_vjoy = int(assisted_brake * 32767 / 65535)
            clutch_vjoy = int(clutch * 32767 / 65535)
            
            self.mock_app.output.update_axis(throttle_vjoy, brake_vjoy, clutch_vjoy)
            
            # Update UI with assist activity
            self.threshold_panel.show_assist_activity(calibrated_brake, assisted_brake)
            
            # Update status bar with real-time values
            brake_percent = calibrated_brake / 65535.0 * 100
            if assisted_brake != calibrated_brake:
                reduction = (calibrated_brake - assisted_brake) / calibrated_brake * 100
                self.statusBar().showMessage(
                    f"Brake: {brake_percent:.1f}% | Assist Active: {reduction:.1f}% reduction"
                )
            else:
                self.statusBar().showMessage(f"Brake: {brake_percent:.1f}% | No assist needed")
                
        except Exception as e:
            logger.error(f"Error processing input: {e}")
    
    def closeEvent(self, event):
        """Clean up when window is closed."""
        if hasattr(self, 'input_timer'):
            self.input_timer.stop()
        
        # Clean up hardware
        if hasattr(self.mock_app, 'hardware'):
            try:
                del self.mock_app.hardware
            except:
                pass
        
        if hasattr(self.mock_app, 'output'):
            try:
                del self.mock_app.output
            except:
                pass
        
        super().closeEvent(event)

def main():
    """Main entry point."""
    logger.info("🎯 Starting Threshold Braking Assist UI Test")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Threshold Assist Test")
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    window = ThresholdAssistTestWindow()
    window.show()
    
    logger.info("UI Test window displayed")
    logger.info("Instructions:")
    logger.info("1. Use your brake pedal to test the system")
    logger.info("2. Enable threshold assist using the checkbox")
    logger.info("3. Adjust reduction percentage with the slider")  
    logger.info("4. Click 'Simulate ABS Lockup' to test learning")
    logger.info("5. Watch the real-time activity indicator")
    
    # Run the application
    try:
        exit_code = app.exec_()
        logger.info("UI Test completed")
        return exit_code
    except Exception as e:
        logger.error(f"Error running UI test: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 