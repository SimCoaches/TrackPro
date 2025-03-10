import sys
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLabel, QCheckBox
from PyQt5.QtCore import QTimer, QPointF, Qt
import logging
import pygame
import os
import traceback

from .hardware_input import HardwareInput
from .output import VirtualJoystick
from .ui import MainWindow
from .hidhide import HidHideClient
from .updater import Updater

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
        """Initialize the application."""
        self.app = QApplication(sys.argv)
        
        # Suppress any version or build information dialogs at startup
        if os.environ.get('TRACKPRO_DISABLE_VERSION_DIALOG') == '1':
            # Override any default QMessageBox behavior at startup by setting a timer
            # to close any message boxes that might appear within 100ms of startup
            def close_startup_dialogs():
                for widget in self.app.topLevelWidgets():
                    if isinstance(widget, QMessageBox) and "v3" in widget.text():
                        widget.close()
            QTimer.singleShot(100, close_startup_dialogs)
            
        self.window = MainWindow()
        
        # Setup debug log handler for debug window
        self.debug_window = None
        
        # Add button to open debug window
        self.window.add_debug_button(self.show_debug_window)
        
        # Setup hardware input and output
        try:
            self.hardware = HardwareInput(test_mode)
            self.output = VirtualJoystick()
            
            # Create default curve presets if they don't exist
            if hasattr(self.hardware, '_create_default_curve_presets'):
                try:
                    self.hardware._create_default_curve_presets()
                except Exception as e:
                    logger.error(f"Error creating default curve presets: {e}")
            
            # Set a reference to the hardware in the UI
            self.window.set_hardware(self.hardware)
            
            # Load calibration from file
            self.load_calibration()
            
            # Make sure to refresh the curve lists after everything is loaded
            QTimer.singleShot(1000, self.window.refresh_curve_lists)
        except Exception as e:
            logger.error(f"Error initializing hardware: {e}")
            QMessageBox.critical(self.window, "Hardware Initialization Error", str(e))
            # Continue but in a limited mode
            self.hardware = None
        
        # Create HidHide client for device management with fail_silently=True
        # This allows the app to run even if HidHide has issues
        try:
            self.hidhide = HidHideClient(fail_silently=True)
            
            if self.hidhide.functioning:
                logger.info("HidHide client initialized successfully")
            else:
                logger.warning(f"HidHide initialized with limited functionality. Error context: {self.hidhide.error_context}")
                
                # Show a non-blocking warning to the user
                self.show_hidhide_warning(self.hidhide.error_context)
        except Exception as e:
            logger.error(f"Error initializing HidHide client: {e}")
            self.hidhide = None
            
        # Connect window signals
        self.window.calibration_updated.connect(self.on_calibration_updated)
        
        # Setup timer for input polling
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_input)
        self.timer.setInterval(8)  # ~120Hz input polling rate (was 16ms ~60Hz)
        
        # Setup connection check timer (checks every 5 seconds)
        self.connection_check_timer = QTimer()
        self.connection_check_timer.timeout.connect(self.check_pedal_connection)
        self.connection_check_timer.setInterval(5000)
        
        # Create updater
        self.updater = Updater(self.window)
        
        # Setup cleanup on exit
        self.app.aboutToQuit.connect(self.cleanup)
    
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
                
                processed_values[pedal] = {
                    'raw': raw_value,
                    'output_vjoy': output,
                    'output_ui': output
                }
            
            # Update virtual joystick first (minimize output lag)
            # Check if each axis is available before sending values
            throttle_value = processed_values['throttle']['output_vjoy'] if self.hardware.THROTTLE_AXIS >= 0 else 0
            brake_value = processed_values['brake']['output_vjoy'] if self.hardware.BRAKE_AXIS >= 0 else 0
            clutch_value = processed_values['clutch']['output_vjoy'] if self.hardware.CLUTCH_AXIS >= 0 else 0
            
            self.output.update_axis(throttle_value, brake_value, clutch_value)
            
            # Update UI with the fresh values
            # With our new integrated chart system, just setting the input is sufficient
            for pedal, values in processed_values.items():
                self.window.set_input_value(pedal, values['raw'])
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
    
    def check_pedal_connection(self):
        """Check if pedals are connected and update UI if status changed."""
        if not self.hardware:
            return
            
        try:
            # Store the current connection state
            was_connected = self.hardware.pedals_connected
            
            # Refresh joystick list to detect newly connected devices
            pygame.joystick.quit()
            pygame.joystick.init()
            
            # Check for P1 Pro Pedals
            self.hardware.pedals_connected = False
            for i in range(pygame.joystick.get_count()):
                try:
                    joy = pygame.joystick.Joystick(i)
                    joy.init()
                    if "Sim Coaches P1 Pro Pedals" in joy.get_name():
                        # Update joystick reference if pedals are now connected
                        self.hardware.joystick = joy
                        self.hardware.pedals_connected = True
                        self.hardware.available_axes = joy.get_numaxes()
                        logger.info(f"Pedals connected: {joy.get_name()} with {joy.get_numaxes()} axes")
                        break
                except Exception as e:
                    logger.warning(f"Error checking joystick {i}: {e}")
            
            # Update UI if connection state changed
            if was_connected != self.hardware.pedals_connected:
                logger.info(f"Pedal connection status changed: {self.hardware.pedals_connected}")
                self.window.update_pedal_connection_status(self.hardware.pedals_connected)
        except Exception as e:
            logger.error(f"Error checking pedal connection: {e}")
    
    def cleanup(self, force_unhide=True):
        """Clean up resources before exit."""
        logger.info("Cleaning up resources...")
        
        # Stop the timer
        if hasattr(self, 'timer'):
            self.timer.stop()
        
        # Clean up output resources (vJoy)
        if hasattr(self, 'output') and self.output:
            try:
                # Explicitly delete the output object to trigger __del__ method
                logger.info("Releasing vJoy device...")
                output = self.output
                self.output = None
                del output
            except Exception as e:
                logger.error(f"Error releasing vJoy device: {e}")
        
        # Disable HidHide cloaking - PRIORITIZE CLI --cloak-off approach
        if hasattr(self, 'hidhide'):
            logger.info("Disabling HidHide cloaking using CLI --cloak-off command...")
            try:
                # Use CLI as primary method - most reliable
                cli_result = self.hidhide._run_cli(["--cloak-off"])
                logger.info(f"Cloak disabled via CLI: {cli_result}")
                
                # Also try to unhide specific devices as a backup
                device_name = "Sim Coaches P1 Pro Pedals"
                matching_devices = self.hidhide.find_all_matching_devices(device_name)
                for device_path in matching_devices:
                    try:
                        unhide_result = self.hidhide._run_cli(["--unhide-by-id", device_path])
                        logger.info(f"Unhid device via CLI: {unhide_result}")
                    except Exception as e2:
                        logger.error(f"Error unhiding device via CLI: {e2}")
                
                # Try API methods as backup
                try:
                    success = self.hidhide.set_cloak_state(False)
                    if success:
                        logger.info("Successfully disabled HidHide cloaking via API")
                    else:
                        logger.warning("Failed to disable HidHide cloaking via API method")
                except Exception as e:
                    logger.error(f"Error disabling cloaking via API: {e}")
            except Exception as e:
                logger.error(f"Error disabling cloaking via CLI: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Last resort: try to run the CLI directly
                try:
                    logger.info("Attempting to run HidHideCLI directly as last resort...")
                    # Try to find the CLI executable
                    cli_path = None
                    if hasattr(self.hidhide, '_cli_path') and self.hidhide._cli_path:
                        cli_path = self.hidhide._cli_path
                    else:
                        # Check common locations
                        possible_paths = [
                            os.path.join(os.path.dirname(os.path.abspath(__file__)), "HidHideCLI.exe"),
                            r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
                            r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
                        ]
                        for path in possible_paths:
                            if os.path.exists(path):
                                cli_path = path
                                break
                    
                    if cli_path:
                        # Use CREATE_NO_WINDOW flag to hide console window
                        CREATE_NO_WINDOW = 0x08000000
                        # Also use DETACHED_PROCESS for maximum hiding
                        creationflags = CREATE_NO_WINDOW | 0x00000008  # DETACHED_PROCESS
                        subprocess.run(
                            [cli_path, "--cloak-off"], 
                            check=False,  # Don't raise exceptions on non-zero exit
                            creationflags=creationflags,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL
                        )
                        logger.info("Successfully ran HidHideCLI directly to disable cloaking")
                except Exception as e:
                    logger.error(f"Failed to run HidHideCLI directly: {e}")
        
        # Try hardware reference as a backup
        if hasattr(self, 'hardware') and hasattr(self.hardware, 'hidhide'):
            logger.info("Attempting to disable HidHide cloaking via hardware reference...")
            try:
                # Try CLI method first
                if hasattr(self.hardware.hidhide, '_run_cli'):
                    cli_result = self.hardware.hidhide._run_cli(["--cloak-off"])
                    logger.info(f"Cloak disabled via hardware.hidhide CLI: {cli_result}")
            except Exception as e:
                logger.error(f"Error disabling HidHide cloaking via hardware CLI: {e}")
        
        # Save calibration
        if hasattr(self, 'hardware'):
            try:
                logger.info("Saving calibration...")
                self.hardware.save_calibration(self.hardware.calibration)
            except Exception as e:
                logger.error(f"Error saving calibration: {e}")
        
        logger.info("Cleanup completed")
    
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
    
    def show_hidhide_warning(self, error_context):
        """Show a non-blocking warning about HidHide issues."""
        if not error_context:
            return
            
        error_messages = {
            "driver_not_installed": "HidHide driver is not installed. Some features may not work properly.",
            "service_not_installed": "HidHide service is not installed. Some features may not work properly.",
            "service_start_failed": "Failed to start HidHide service. Some features may not work properly.",
            "access_denied_service": "Access denied when accessing HidHide. Try running as administrator.",
            "cli_not_found": "HidHideCLI.exe not found. Some features may not work properly.",
            "app_registration_failed": "Failed to register application with HidHide. Try running as administrator.",
            "cli_access_denied": "Access denied when using HidHide CLI. Try running as administrator."
        }
        
        message = error_messages.get(error_context, "HidHide issues detected. Some features may not work properly.")
        
        # Create a non-blocking warning dialog
        QTimer.singleShot(1000, lambda: self.show_nonblocking_warning("HidHide Warning", message))
    
    def show_nonblocking_warning(self, title, message):
        """Show a non-blocking warning dialog."""
        warning = QMessageBox(self.window)
        warning.setIcon(QMessageBox.Warning)
        warning.setWindowTitle(title)
        warning.setText(message)
        warning.setStandardButtons(QMessageBox.Ok)
        warning.setWindowModality(Qt.NonModal)
        warning.show()
    
    def run(self):
        """Run the application."""
        # Show the main window
        self.window.show()
        
        # Start the input polling timer
        if self.hardware and self.output:
            self.timer.start()
            self.connection_check_timer.start()
            
            # Run initial pedal value update
            self.process_input()
        
        # Check for updates silently
        self.updater.check_for_updates(silent=True)
        
        # Run the application event loop
        return self.app.exec_()

def main():
    """Main application entry point."""
    # Check for test mode
    test_mode = "--test" in sys.argv
    # Set environment variable to disable startup version dialogs
    os.environ['TRACKPRO_DISABLE_VERSION_DIALOG'] = '1'
    
    # Create QApplication instance first to ensure it exists
    app_instance = QApplication.instance() or QApplication(sys.argv)
    
    # Try to ensure HidHide cloaking is disabled before starting
    # Use fail_silently=True to continue even if HidHide has issues
    try:
        logger.info("Initializing HidHide to disable cloaking before startup...")
        from .hidhide import HidHideClient
        
        # Initialize with fail_silently=True so the app can continue even if HidHide fails
        hidhide = HidHideClient(fail_silently=True)
        
        # Try multiple approaches to ensure cloaking is disabled
        if hidhide.functioning:
            # Try CLI first (most reliable)
            cli_result = hidhide._run_cli(["--cloak-off"], retry_count=3)
            logger.info(f"Cloak disabled via CLI before startup: {cli_result}")
            
            # Try API method as backup
            api_result = hidhide.set_cloak_state(False)
            logger.info(f"Cloak disabled via API before startup: {api_result}")
            
            # If device name is known, try to unhide specific devices
            if hasattr(hidhide, 'config') and hidhide.config.get('device_name'):
                device_name = hidhide.config.get('device_name')
            else:
                # Fallback to common device names
                device_name = "Sim Coaches P1 Pro Pedals"
            
            logger.info(f"Finding all devices matching: {device_name}")
            matching_devices = hidhide.find_all_matching_devices(device_name)
            if matching_devices:
                for device_path in matching_devices:
                    try:
                        # Try unhide by instance path
                        unhide_result = hidhide.unhide_device(device_path)
                        logger.info(f"Unhid device '{device_path}' via API: {unhide_result}")
                    except Exception as e:
                        logger.warning(f"Error unhiding device via API: {e}")
                        
                        # Fallback to CLI if available
                        try:
                            unhide_cmd_result = hidhide._run_cli(["--dev-unhide", device_path])
                            logger.info(f"Unhid device via CLI: {unhide_cmd_result}")
                        except Exception as e2:
                            logger.error(f"Error unhiding device via CLI: {e2}")
        else:
            logger.warning(f"HidHide not functioning, skipping pre-startup cloaking control. Error context: {hidhide.error_context}")
            
    except Exception as e:
        logger.error(f"Error during HidHide pre-startup: {e}")
        # Continue anyway, we'll attempt to initialize again in the app
    
    try:
        # Create and run the application
        app = TrackProApp(test_mode)
        return app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        
        # Display error in message box
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("TrackPro Error")
        error_box.setText(f"Fatal error: {e}")
        error_box.setDetailedText(traceback.format_exc())
        error_box.exec_()
        return 1

if __name__ == "__main__":
    main() 