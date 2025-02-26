import sys
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, QPointF
import logging
import pygame
import os

from .hardware_input import HardwareInput
from .output import VirtualJoystick
from .ui import MainWindow
from .hidhide import HidHideClient

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TrackProApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application and all its components."""
        self.app = QApplication(sys.argv)
        
        try:
            # Initialize hardware input
            logger.info("Checking for input devices...")
            self.hardware = HardwareInput()
            
            # Initialize virtual joystick
            logger.info("Initializing virtual joystick...")
            self.output = VirtualJoystick()
            
            # Initialize HidHide client
            logger.info("Initializing HidHide client...")
            self.hidhide = HidHideClient()
            
            # Define the device name we're looking for
            device_name = "Sim Coaches P1 Pro Pedals"
            
            # First unhide any matching devices that might already be hidden
            # This ensures we can find the device properly
            logger.info("Checking for already hidden devices...")
            self.hidhide.unhide_all_matching_devices(device_name)
            
            # Now find all matching devices
            logger.info("Finding all matching devices...")
            matching_devices = self.hidhide.find_all_matching_devices(device_name)
            
            if matching_devices:
                # Use the first matching device
                instance_path = matching_devices[0]
                logger.info(f"Using device instance path: {instance_path}")
                
                # Hide the device now that we've found it
                if self.hidhide.hide_device(instance_path):
                    logger.info(f"Successfully hid {device_name}")
                else:
                    logger.warning(f"Failed to hide {device_name}")
            else:
                logger.warning(f"Could not find any devices matching {device_name}")
                # Show a warning to the user
                QMessageBox.warning(
                    None, 
                    "Device Not Found", 
                    f"Could not find {device_name}. Make sure the device is connected and recognized by Windows."
                )
            
            # Create and show UI
            logger.info("Creating user interface...")
            self.window = MainWindow()
            
            # Connect signals
            for pedal in ['throttle', 'brake', 'clutch']:
                self.window.calibration_updated.connect(self.on_calibration_updated)
            
            # Connect to the calibration wizard signal
            self.window.calibration_wizard_completed = self.on_calibration_wizard_completed
            
            self.window.show()
            
            # Load calibration into UI
            self.load_calibration()
            
            # Setup update timer for reading inputs
            self.input_timer = QTimer()
            self.input_timer.timeout.connect(self.process_input)
            self.input_timer.start(16)  # ~60Hz update rate
            
            # Setup cleanup on exit
            self.app.aboutToQuit.connect(self.cleanup)
            
        except Exception as e:
            logger.error(f"Failed to initialize: {str(e)}")
            QMessageBox.critical(None, "Initialization Error", str(e))
            sys.exit(1)
    
    def load_calibration(self):
        """Load calibration data into UI."""
        cal = self.hardware.calibration
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in cal:
                points = cal[pedal].get('points', [])
                curve_type = cal[pedal].get('curve', 'Linear')
                
                # Convert points to QPointF objects
                qpoints = [QPointF(x, y) for x, y in points]
                self.window.set_calibration_points(pedal, qpoints)
                self.window.set_curve_type(pedal, curve_type)
                
                # Set min/max range
                axis_range = self.hardware.axis_ranges[pedal]
                self.window.set_calibration_range(pedal, axis_range['min'], axis_range['max'])
    
    def on_calibration_updated(self, pedal: str):
        """Handle calibration updates from UI."""
        # Get calibration points
        points = self.window.get_calibration_points(pedal)
        curve_type = self.window.get_curve_type(pedal)
        
        # Convert QPointF objects to tuples of percentages (0-100 scale)
        point_tuples = [(p.x(), p.y()) for p in points]
        
        # Update hardware calibration
        self.hardware.calibration[pedal] = {
            'points': point_tuples,
            'curve': curve_type
        }
        
        # Update axis ranges
        min_val, max_val = self.window.get_calibration_range(pedal)
        self.hardware.axis_ranges[pedal] = {
            'min': min_val,
            'max': max_val
        }
        
        # Save calibration
        self.hardware.save_calibration(self.hardware.calibration)
        
        # Immediately reprocess current input to apply the new calibration
        # This ensures changes to the curve are reflected in real-time
        self.process_input()
    
    def process_input(self):
        """Process input and update output."""
        try:
            # Read pedal values
            values = self.hardware.read_pedals()
            
            # Process all pedals first (calculate outputs) before updating UI
            processed_values = {}
            
            for pedal, raw_value in values.items():
                # Apply calibration
                output = self.hardware.apply_calibration(pedal, raw_value)
                
                # For clutch, we need to show the non-inverted value in the UI
                # but send the inverted value to the virtual joystick
                if pedal == 'clutch':
                    processed_values[pedal] = {
                        'raw': raw_value,
                        'output_vjoy': 65535 - output,  # Inverted for vJoy
                        'output_ui': output             # Non-inverted for UI
                    }
                else:
                    processed_values[pedal] = {
                        'raw': raw_value,
                        'output_vjoy': output,  # Same for vJoy
                        'output_ui': output     # Same for UI
                    }
            
            # Update virtual joystick first (minimize output lag)
            self.output.update_axis(
                processed_values['throttle']['output_vjoy'],
                processed_values['brake']['output_vjoy'],
                processed_values['clutch']['output_vjoy']
            )
            
            # Then update UI for all pedals - first set input values for all pedals
            for pedal, values in processed_values.items():
                # Update UI with raw values
                self.window.set_input_value(pedal, values['raw'])
            
            # Then update output values for all pedals
            for pedal, values in processed_values.items():
                # Update UI with processed values
                self.window.set_output_value(pedal, values['output_ui'])
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
    
    def cleanup(self):
        """Clean up resources before exit."""
        logger.info("Cleaning up...")
        try:
            # Save calibration
            self.hardware.save_calibration(self.hardware.calibration)
            
            # Unhide the original controller
            device_name = "Sim Coaches P1 Pro Pedals"
            
            # First check if the device is hidden
            is_hidden, hidden_path = self.hidhide.is_device_hidden(device_name)
            
            if is_hidden and hidden_path:
                # Use the path we already know
                logger.info(f"Found hidden device at path: {hidden_path}")
                if self.hidhide.unhide_device(hidden_path):
                    logger.info(f"Successfully unhid {device_name}")
                else:
                    logger.warning(f"Failed to unhide {device_name}")
            else:
                # Try to find all matching devices
                matching_devices = self.hidhide.find_all_matching_devices(device_name)
                
                if matching_devices:
                    # Unhide all matching devices to be safe
                    for device_path in matching_devices:
                        if self.hidhide.unhide_device(device_path):
                            logger.info(f"Successfully unhid device: {device_path}")
                        else:
                            logger.warning(f"Failed to unhide device: {device_path}")
                else:
                    logger.warning(f"Could not find any devices matching {device_name} during cleanup")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def on_calibration_wizard_completed(self, results):
        """Handle calibration wizard results."""
        logger.info(f"Calibration wizard completed with results: {results}")
        
        # Update axis mappings if they changed
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in results and 'axis' in results[pedal]:
                new_axis = results[pedal]['axis']
                self.hardware.update_axis_mapping(pedal, new_axis)
                logger.info(f"Updated {pedal} axis mapping to {new_axis}")
        
        # Update min/max ranges
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in results:
                min_val = results[pedal].get('min', 0)
                max_val = results[pedal].get('max', 65535)
                
                # Update hardware ranges
                self.hardware.axis_ranges[pedal] = {
                    'min': min_val,
                    'max': max_val
                }
                
                # Save the updated ranges
                self.hardware.save_axis_ranges()
                
                logger.info(f"Updated {pedal} range: min={min_val}, max={max_val}")
        
        # Reload calibration into UI
        self.load_calibration()
    
    def run(self):
        """Run the application."""
        return self.app.exec_()

def main():
    """Main application entry point."""
    app = TrackProApp()
    return app.run()

if __name__ == "__main__":
    main() 