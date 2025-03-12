import sys
import os
import logging
import time
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
from trackpro.main import TrackProApp
from trackpro.ui import MainWindow
from trackpro.hardware_input import HardwareInput
from trackpro.output import VirtualJoystick

# Configure logging to show more detailed information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("trackpro_debug.log")
    ]
)

logger = logging.getLogger("TrackPro_Debug")

class DiagnosticWidget(QDialog):
    """Diagnostic widget to display pedal input values."""
    
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.setWindowTitle("TrackPro Diagnostic")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()
        
        # Info labels
        self.info_label = QLabel("TrackPro Diagnostic Mode")
        layout.addWidget(self.info_label)
        
        # Pedal values
        self.throttle_label = QLabel("Throttle: Raw=0, Scaled=0, Output=0")
        self.brake_label = QLabel("Brake: Raw=0, Scaled=0, Output=0")
        self.clutch_label = QLabel("Clutch: Raw=0, Scaled=0, Output=0")
        
        layout.addWidget(self.throttle_label)
        layout.addWidget(self.brake_label)
        layout.addWidget(self.clutch_label)
        
        # Axis mappings
        self.mappings_label = QLabel("Axis Mappings: Not loaded")
        layout.addWidget(self.mappings_label)
        
        # Calibration info
        self.calibration_label = QLabel("Calibration: Not loaded")
        layout.addWidget(self.calibration_label)
        
        # Raw axis values
        self.raw_axes_label = QLabel("Raw Axes: Not available")
        layout.addWidget(self.raw_axes_label)
        
        # Last values
        self.last_values_label = QLabel("Last Values: Not available")
        layout.addWidget(self.last_values_label)
        
        # Output values
        self.output_values_label = QLabel("Output Values: Not available")
        layout.addWidget(self.output_values_label)
        
        # Run diagnostics button
        self.diagnostic_button = QPushButton("Run Pedal Diagnostics")
        self.diagnostic_button.clicked.connect(self.run_pedal_diagnostics)
        layout.addWidget(self.diagnostic_button)
        
        # Reset calibration button
        self.reset_button = QPushButton("Reset Calibration")
        self.reset_button.clicked.connect(self.reset_calibration)
        layout.addWidget(self.reset_button)
        
        self.setLayout(layout)
        
        # Start update timer
        self.start_timer()
        
    def start_timer(self):
        """Start a timer to update the display."""
        import threading
        self.running = True
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def update_loop(self):
        """Update loop to refresh the display."""
        while self.running:
            try:
                self.update_display()
            except Exception as e:
                logger.error(f"Error updating display: {e}")
            time.sleep(0.1)  # Update at 10Hz
            
    def update_display(self):
        """Update the display with current values."""
        if not hasattr(self.main_app, 'hardware') or not self.main_app.hardware:
            return
            
        hw = self.main_app.hardware
        
        # Update axis mappings
        self.mappings_label.setText(f"Axis Mappings: {hw.axis_mappings}")
        
        # Update calibration info
        cal_info = {}
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in hw.calibration:
                cal_info[pedal] = {
                    'curve': hw.calibration[pedal].get('curve', 'Linear'),
                    'points_count': len(hw.calibration[pedal].get('points', [])),
                    'min': hw.axis_ranges[pedal]['min'],
                    'max': hw.axis_ranges[pedal]['max']
                }
        self.calibration_label.setText(f"Calibration: {cal_info}")
        
        # Update raw axes values
        raw_axes = {}
        if hw.pedals_connected and hw.joystick:
            for i in range(hw.available_axes):
                try:
                    raw_axes[i] = hw.joystick.get_axis(i)
                except:
                    raw_axes[i] = "Error"
        self.raw_axes_label.setText(f"Raw Axes: {raw_axes}")
        
        # Get current pedal values (force a fresh read)
        try:
            values = hw.read_pedals()
            
            # Store these raw values
            raw_values = {}
            for pedal, axis in [('throttle', hw.THROTTLE_AXIS), ('brake', hw.BRAKE_AXIS), ('clutch', hw.CLUTCH_AXIS)]:
                if axis >= 0 and axis < hw.available_axes and hw.joystick:
                    try:
                        raw_val = hw.joystick.get_axis(axis)
                        scaled = int((raw_val + 1) * 32767)
                        output = hw.apply_calibration(pedal, scaled)
                        
                        # Update the label for this pedal
                        if pedal == 'throttle':
                            self.throttle_label.setText(f"Throttle: Raw={raw_val:.2f}, Scaled={scaled}, Output={output}, Axis={axis}")
                        elif pedal == 'brake':
                            self.brake_label.setText(f"Brake: Raw={raw_val:.2f}, Scaled={scaled}, Output={output}, Axis={axis}")
                        elif pedal == 'clutch':
                            self.clutch_label.setText(f"Clutch: Raw={raw_val:.2f}, Scaled={scaled}, Output={output}, Axis={axis}")
                            
                        raw_values[pedal] = raw_val
                    except Exception as e:
                        logger.error(f"Error reading {pedal}: {e}")
            
            # Update last values
            self.last_values_label.setText(f"Last Values: {hw.last_values}")
            
            # Update output values if output exists
            if hasattr(self.main_app, 'output') and self.main_app.output:
                output = self.main_app.output
                
                # Get the mapped vJoy values
                throttle_value = int(values['throttle'] * 32767 / 65535) if 'throttle' in values else 0
                brake_value = int(values['brake'] * 32767 / 65535) if 'brake' in values else 0
                clutch_value = int(values['clutch'] * 32767 / 65535) if 'clutch' in values else 0
                
                self.output_values_label.setText(f"Output Values: Throttle={throttle_value}, Brake={brake_value}, Clutch={clutch_value}")
                
                # Force update the output
                output.update_axis(throttle_value, brake_value, clutch_value)
                
        except Exception as e:
            logger.error(f"Error updating pedal values: {e}")
        
    def run_pedal_diagnostics(self):
        """Run the pedal diagnostics."""
        if not hasattr(self.main_app, 'hardware') or not self.main_app.hardware:
            return
            
        try:
            results = self.main_app.hardware.diagnostic_pedals()
            logger.info(f"Diagnostic results: {results}")
        except Exception as e:
            logger.error(f"Error running diagnostics: {e}")
            
    def reset_calibration(self):
        """Reset the calibration."""
        if not hasattr(self.main_app, 'hardware') or not self.main_app.hardware:
            return
            
        try:
            # Reset axis ranges to default
            for pedal in ['throttle', 'brake', 'clutch']:
                self.main_app.hardware.axis_ranges[pedal] = {
                    'min': 0,
                    'max': 65535,
                    'min_deadzone': 0,
                    'max_deadzone': 0
                }
                
            # Reset calibration to linear
            self.main_app.hardware.calibration = {
                'throttle': {'points': [], 'curve': 'Linear'},
                'brake': {'points': [], 'curve': 'Linear'},
                'clutch': {'points': [], 'curve': 'Linear'}
            }
            
            # Save the changes
            self.main_app.hardware.save_calibration(self.main_app.hardware.calibration)
            self.main_app.hardware.save_axis_ranges()
            
            logger.info("Calibration reset to defaults")
        except Exception as e:
            logger.error(f"Error resetting calibration: {e}")
    
    def closeEvent(self, event):
        """Handle the window close event."""
        self.running = False
        super().closeEvent(event)

def main():
    """Main application function."""
    logger.info("Starting TrackPro Diagnostic Mode")
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Initialize TrackPro app without showing the UI
    trackpro_app = TrackProApp(test_mode=False)
    
    # Create diagnostic widget
    diag_widget = DiagnosticWidget(trackpro_app)
    diag_widget.show()
    
    # Run the app
    return app.exec_()

if __name__ == "__main__":
    main() 