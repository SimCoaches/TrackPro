import sys
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLabel
from PyQt5.QtCore import QTimer, QPointF, Qt
import logging
import pygame
import os
import traceback

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

# Create a custom handler that will store log messages for the debug window
class DebugLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_records = []
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def emit(self, record):
        self.log_records.append(self.formatter.format(record))
    
    def get_logs(self):
        return self.log_records

# Create the debug log handler
debug_handler = DebugLogHandler()
debug_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(debug_handler)

class DebugWindow(QDialog):
    """Debug window to display detailed information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TrackPro Debug Information")
        self.setMinimumSize(800, 600)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add header
        header = QLabel("Debug Information")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)
        
        # Create text area for logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Add system information
        system_info = self.get_system_info()
        self.log_text.append("=== SYSTEM INFORMATION ===")
        for key, value in system_info.items():
            self.log_text.append(f"{key}: {value}")
        self.log_text.append("\n=== LOG MESSAGES ===")
        
        # Add logs
        for log in debug_handler.get_logs():
            self.log_text.append(log)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_logs)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Set up timer to refresh logs
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(1000)  # Refresh every second
    
    def get_system_info(self):
        """Get system information."""
        info = {}
        
        # Python version
        info["Python Version"] = sys.version.split()[0]
        
        # OS information
        info["OS"] = sys.platform
        
        # Check for HidHide service
        try:
            import win32serviceutil
            import win32service
            status = win32serviceutil.QueryServiceStatus('HidHide')
            status_text = "Unknown"
            if status[1] == win32service.SERVICE_RUNNING:
                status_text = "Running"
            elif status[1] == win32service.SERVICE_STOPPED:
                status_text = "Stopped"
            elif status[1] == win32service.SERVICE_START_PENDING:
                status_text = "Starting"
            elif status[1] == win32service.SERVICE_STOP_PENDING:
                status_text = "Stopping"
            info["HidHide Service"] = status_text
        except Exception as e:
            info["HidHide Service"] = f"Error: {str(e)}"
        
        # Check for HidHide registry
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\HidHide") as key:
                info["HidHide Registry"] = "Found"
        except Exception as e:
            info["HidHide Registry"] = f"Not found: {str(e)}"
        
        # Check for HidHide device
        try:
            import win32file
            import win32con
            device_path = r"\\.\HidHide"
            handle = win32file.CreateFile(
                device_path,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            win32file.CloseHandle(handle)
            info["HidHide Device"] = "Accessible"
        except Exception as e:
            info["HidHide Device"] = f"Not accessible: {str(e)}"
        
        # Check for HidHideCLI.exe
        try:
            bundled_cli = os.path.join(os.path.dirname(__file__), "HidHideCLI.exe")
            if os.path.exists(bundled_cli):
                info["HidHideCLI.exe"] = f"Found at {bundled_cli}"
            else:
                # Check common installation paths
                common_paths = [
                    r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
                    r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        info["HidHideCLI.exe"] = f"Found at {path}"
                        break
                else:
                    info["HidHideCLI.exe"] = "Not found in common locations"
        except Exception as e:
            info["HidHideCLI.exe"] = f"Error checking: {str(e)}"
        
        # Check for admin privileges
        try:
            import ctypes
            info["Admin Privileges"] = "Yes" if ctypes.windll.shell32.IsUserAnAdmin() else "No"
        except Exception as e:
            info["Admin Privileges"] = f"Error checking: {str(e)}"
        
        return info
    
    def refresh_logs(self):
        """Refresh the log display."""
        # Store current scroll position
        scrollbar = self.log_text.verticalScrollBar()
        was_at_bottom = scrollbar.value() == scrollbar.maximum()
        
        # Clear and repopulate
        self.log_text.clear()
        
        # Add system information
        system_info = self.get_system_info()
        self.log_text.append("=== SYSTEM INFORMATION ===")
        for key, value in system_info.items():
            self.log_text.append(f"{key}: {value}")
        self.log_text.append("\n=== LOG MESSAGES ===")
        
        # Add logs
        for log in debug_handler.get_logs():
            self.log_text.append(log)
        
        # Restore scroll position if was at bottom
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
    
    def copy_to_clipboard(self):
        """Copy all text to clipboard."""
        self.log_text.selectAll()
        self.log_text.copy()
        self.log_text.moveCursor(self.log_text.textCursor().Start)
        self.log_text.ensureCursorVisible()

class TrackProApp:
    """Main application class."""
    
    def __init__(self, test_mode=False):
        """Initialize the application and all its components."""
        self.app = QApplication(sys.argv)
        self.test_mode = test_mode
        
        try:
            # Initialize hardware input
            logger.info("Checking for input devices...")
            self.hardware = HardwareInput(test_mode=test_mode)
            
            # Initialize virtual joystick
            logger.info("Initializing virtual joystick...")
            self.output = VirtualJoystick(test_mode=test_mode)
            
            # Initialize HidHide client
            logger.info("Initializing HidHide client...")
            try:
                self.hidhide = HidHideClient()
                logger.info("HidHide client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize HidHide client: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                if not test_mode:
                    # Show debug window with detailed information
                    debug_window = DebugWindow()
                    debug_window.exec_()
                    
                    # Re-raise the exception to stop initialization
                    raise RuntimeError(f"Cannot Initialize with HIDHIDE: {str(e)}")
                else:
                    logger.warning("Continuing in test mode despite HidHide initialization failure")
            
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
            
            # Set hardware reference in the window
            self.window.set_hardware(self.hardware)
            
            # Add debug button to the window
            self.window.add_debug_button(self.show_debug_window)
            
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
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Show debug window with detailed information
            debug_window = DebugWindow()
            debug_window.exec_()
            
            QMessageBox.critical(None, "Initialization Error", str(e))
            sys.exit(1)
    
    def show_debug_window(self):
        """Show the debug window."""
        debug_window = DebugWindow(self.window)
        debug_window.exec_()
    
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
                
                # Check if this axis is available
                axis_num = getattr(self.hardware, f"{pedal.upper()}_AXIS", -1)
                if axis_num < 0 or axis_num >= self.hardware.available_axes:
                    # Disable UI elements for unavailable pedals
                    self.window.set_pedal_available(pedal, False)
                else:
                    self.window.set_pedal_available(pedal, True)
                
                # Update curve selector if it's a custom curve
                if curve_type not in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
                    selector = self.window._pedal_data[pedal].get('curve_selector')
                    if selector:
                        # Add the custom curve type if it's not already in the list
                        if selector.findText(curve_type) == -1:
                            selector.addItem(curve_type)
                        selector.setCurrentText(curve_type)
        
        # Refresh the curve lists
        self.window.refresh_curve_lists()
    
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
                        'raw': raw_value,  # Store the raw, unmodified value
                        'output_vjoy': 65535 - output,  # Inverted for vJoy
                        'output_ui': output             # Non-inverted for UI
                    }
                else:
                    processed_values[pedal] = {
                        'raw': raw_value,  # Store the raw, unmodified value
                        'output_vjoy': output,  # Same for vJoy
                        'output_ui': output     # Same for UI
                    }
            
            # Update virtual joystick first (minimize output lag)
            # Check if each axis is available before sending values
            throttle_value = processed_values['throttle']['output_vjoy'] if self.hardware.THROTTLE_AXIS >= 0 else 0
            brake_value = processed_values['brake']['output_vjoy'] if self.hardware.BRAKE_AXIS >= 0 else 0
            clutch_value = processed_values['clutch']['output_vjoy'] if self.hardware.CLUTCH_AXIS >= 0 else 0
            
            self.output.update_axis(throttle_value, brake_value, clutch_value)
            
            # Then update UI for all pedals - first set input values for all pedals
            for pedal, values in processed_values.items():
                # Update UI with raw values - these should be the direct hardware readings
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
    # Check for test mode
    test_mode = "--test" in sys.argv
    
    if test_mode:
        logger.info("Running in test mode")
    
    app = TrackProApp(test_mode=test_mode)
    return app.run()

if __name__ == "__main__":
    main() 