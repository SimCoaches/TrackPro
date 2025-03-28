import sys
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLabel, QCheckBox, QProgressBar, QSplashScreen
from PyQt5.QtCore import QTimer, QPointF, Qt
from PyQt5.QtGui import QPixmap
import logging
import pygame
import os
import traceback
import re

from .pedals.hardware_input import HardwareInput
from .pedals.output import VirtualJoystick
from .ui import MainWindow
from .pedals.hidhide import HidHideClient
from .updater import Updater
from .database import supabase
from .auth import LoginDialog

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
        
        # Initialize attributes that will be used later
        self.hardware = None
        self.output = None
        self.hidhide = None
        self.timer = None
        self.updater = None
        self.reconnecting = False
        self.startup_complete = False
        
        # Create and show a splash screen with progress bar
        self.create_startup_progress()
        
        try:
            # Update progress 10%
            self.update_progress(10, "Initializing interface...")
            self.window = MainWindow()
            
            # Connect auth state changed signal
            if hasattr(self.window, 'auth_state_changed'):
                self.window.auth_state_changed.connect(self.handle_auth_state_change)
            
            # Setup debug log handler for debug window
            self.debug_window = None
            
            # Add button to open debug window
            self.window.add_debug_button(self.show_debug_window)
            
            # Update progress 20%
            self.update_progress(20, "Setting up hardware input...")
            
            # Setup hardware input and output
            self.hardware = HardwareInput(test_mode)
            
            # Update progress 30%
            self.update_progress(30, "Initializing virtual joystick...")
            self.output = VirtualJoystick()
            
            # Create default curve presets if they don't exist
            self.update_progress(35, "Creating presets...")
            if hasattr(self.hardware, '_create_default_curve_presets'):
                try:
                    self.hardware._create_default_curve_presets()
                except Exception as e:
                    logger.error(f"Error creating default curve presets: {e}")
            
            # Set a reference to the hardware in the UI
            if hasattr(self.window, 'set_hardware'):
                self.window.set_hardware(self.hardware)
            
            # Update progress 40%
            self.update_progress(40, "Connecting signals...")
            
            # Connect window signals if they exist
            if hasattr(self.window, 'output_changed'):
                self.window.output_changed.connect(self.output.on_output_changed)
            if hasattr(self.window, 'calibration_updated'):
                self.window.calibration_updated.connect(self.on_calibration_updated)
            if hasattr(self.window, 'calibration_wizard_completed'):
                self.window.calibration_wizard_completed.connect(self.on_calibration_wizard_completed)
            
            # Setup HidHide
            self.update_progress(50, "Setting up HidHide...")
            if not hasattr(self, 'hidhide') or self.hidhide is None:
                try:
                    self.hidhide = HidHideClient(fail_silently=True)
                    if hasattr(self.hidhide, 'functioning') and self.hidhide.functioning:
                        logger.info("HidHide client initialized successfully")
                    elif hasattr(self.hidhide, 'error_context') and self.hidhide.error_context:
                        logger.warning(f"HidHide initialized with limited functionality: {self.hidhide.error_context}")
                        self.show_hidhide_warning(self.hidhide.error_context)
                except Exception as e:
                    logger.error(f"Error initializing HidHide client: {e}")
                    self.hidhide = None
            
            # Setup timer for processing input
            self.update_progress(60, "Setting up input processing...")
            self.timer = QTimer()
            self.timer.timeout.connect(self.process_input)
            self.timer.setInterval(8)  # ~120Hz input polling rate
            
            # Load calibration
            self.update_progress(70, "Loading calibration data...")
            self.load_calibration()
            
            # Setup updater
            self.update_progress(80, "Initializing update checker...")
            self.updater = Updater(self.window)
            # Start update check in background after a delay
            QTimer.singleShot(2000, lambda: self.updater.check_for_updates(silent=True))
            
            # Update progress to 90%
            self.update_progress(90, "Finalizing startup...")
            
            # Start the input processing timer
            self.timer.start()
            
            # Mark startup as complete
            self.startup_complete = True
            
            # Update progress to 100% and close splash screen
            self.update_progress(100, "Startup complete")
            QTimer.singleShot(500, self.startup_dialog.close)
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            logger.error(traceback.format_exc())
            
            self.update_progress(100, "Error during initialization")
            QMessageBox.critical(None, "Initialization Error", 
                               f"Error during startup: {str(e)}\n\nTrackPro may not function correctly.")
        
        # Connect quit handler
        self.app.aboutToQuit.connect(self.cleanup)
    
    def create_startup_progress(self):
        """Create and show a startup progress dialog."""
        try:
            # Create the progress dialog
            self.startup_dialog = QDialog(None, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            self.startup_dialog.setWindowTitle("TrackPro Starting")
            self.startup_dialog.setFixedSize(450, 180)
            
            # Center dialog on screen
            screen_geometry = self.app.desktop().screenGeometry()
            x = (screen_geometry.width() - self.startup_dialog.width()) // 2
            y = (screen_geometry.height() - self.startup_dialog.height()) // 2
            self.startup_dialog.move(x, y)
            
            # Set up the layout
            layout = QVBoxLayout(self.startup_dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
            
            # Add title label with version
            title_label = QLabel("TrackPro")
            title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
            title_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(title_label)
            
            # Add version label
            version_label = QLabel("Racing Telemetry System")
            version_label.setStyleSheet("font-size: 12px; color: #7f8c8d;")
            version_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(version_label)
            
            # Add status label
            self.status_label = QLabel("Starting...")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet("font-size: 14px; color: #34495e;")
            layout.addWidget(self.status_label)
            
            # Add progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setFormat("%p%")
            layout.addWidget(self.progress_bar)
            
            # Set dialog style
            self.startup_dialog.setStyleSheet("""
                QDialog {
                    background-color: #f8f9fa;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
                QProgressBar {
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    text-align: center;
                    height: 20px;
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2980b9);
                    border-radius: 5px;
                }
            """)
            
            # Create a pulsating animation effect for the progress bar when it's at 0%
            self.pulse_timer = QTimer()
            self.pulse_timer.setInterval(30)
            self.pulse_direction = 1
            self.pulse_value = 0
            
            def pulse_progress():
                try:
                    if not hasattr(self, 'progress_bar') or not self.progress_bar:
                        # Progress bar no longer exists, stop the timer
                        if hasattr(self, 'pulse_timer') and self.pulse_timer:
                            self.pulse_timer.stop()
                        return
                        
                    if self.progress_bar.value() > 0:
                        # Stop pulsing once real progress starts
                        self.pulse_timer.stop()
                        return
                        
                    self.pulse_value += self.pulse_direction
                    if self.pulse_value >= 100:
                        self.pulse_direction = -1
                    elif self.pulse_value <= 0:
                        self.pulse_direction = 1
                        
                    # Apply a style with gradient offset based on pulse value
                    self.progress_bar.setStyleSheet(f"""
                        QProgressBar::chunk {{
                            background-color: qlineargradient(x1:{self.pulse_value/100}, y1:0, x2:{(self.pulse_value/100)+0.5}, y2:0, 
                                                            stop:0 #3498db, stop:1 #2980b9);
                            border-radius: 5px;
                        }}
                    """)
                except Exception as e:
                    # If there's an error in the pulse timer, just stop it
                    logger.error(f"Error in pulse timer: {e}")
                    if hasattr(self, 'pulse_timer') and self.pulse_timer:
                        self.pulse_timer.stop()
            
            self.pulse_timer.timeout.connect(pulse_progress)
            self.pulse_timer.start()
            
            # Show the dialog
            self.startup_dialog.show()
            
            # Process events to make sure dialog is displayed
            self.app.processEvents()
            
            logger.info("Startup progress dialog created successfully")
        except Exception as e:
            # If there's an error creating the dialog, log it and continue without a progress bar
            logger.error(f"Error creating startup progress dialog: {e}")
            logger.error(traceback.format_exc())
            # Ensure pulse_timer is None to avoid further errors
            self.pulse_timer = None
            self.startup_dialog = None
    
    def update_progress(self, value, status_text):
        """Update the progress bar value and status text."""
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar and hasattr(self, 'status_label') and self.status_label:
                # If this is the first real progress update, stop the pulse animation
                if value > 0 and hasattr(self, 'pulse_timer') and self.pulse_timer and self.pulse_timer.isActive():
                    self.pulse_timer.stop()
                    # Restore normal progress bar style
                    self.progress_bar.setStyleSheet("""
                        QProgressBar::chunk {
                            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2980b9);
                            border-radius: 5px;
                        }
                    """)
                
                self.progress_bar.setValue(value)
                self.status_label.setText(status_text)
                
                # Log progress updates
                logger.debug(f"Progress update: {value}% - {status_text}")
                
                # Process events to update UI
                if hasattr(self, 'app') and self.app:
                    self.app.processEvents()
        except Exception as e:
            # Don't let progress bar errors crash the application
            logger.error(f"Error updating progress: {e}")
            # Continue anyway
    
    def show_debug_window(self):
        """Show the debug window."""
        debug_window = DebugWindow(self.window)
        debug_window.exec_()
    
    def load_calibration(self):
        """Load calibration data into UI."""
        if not hasattr(self, 'hardware') or not self.hardware or not hasattr(self, 'window'):
            logger.warning("Cannot load calibration - hardware or window not available")
            return
            
        if not hasattr(self.hardware, 'calibration'):
            logger.warning("Hardware has no calibration data")
            return
            
        cal = self.hardware.calibration
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in cal:
                points = cal[pedal].get('points', [])
                curve_type = cal[pedal].get('curve', 'Linear')
                
                # Convert points to QPointF objects
                qpoints = [QPointF(x, y) for x, y in points]
                
                # Check if the required methods exist
                if hasattr(self.window, 'set_calibration_points'):
                    self.window.set_calibration_points(pedal, qpoints)
                else:
                    logger.warning(f"MainWindow does not have set_calibration_points method, skipping for {pedal}")
                    
                if hasattr(self.window, 'set_curve_type'):
                    self.window.set_curve_type(pedal, curve_type)
                else:
                    logger.warning(f"MainWindow does not have set_curve_type method, skipping for {pedal}")
                
                # Set min/max range if available
                if hasattr(self.hardware, 'axis_ranges') and pedal in self.hardware.axis_ranges:
                    axis_range = self.hardware.axis_ranges[pedal]
                    if hasattr(self.window, 'set_calibration_range'):
                        self.window.set_calibration_range(pedal, axis_range['min'], axis_range['max'])
                    else:
                        logger.warning(f"MainWindow does not have set_calibration_range method, skipping for {pedal}")
                
                # Check if this axis is available
                axis_num = getattr(self.hardware, f"{pedal.upper()}_AXIS", -1)
                
                # Only proceed if the set_pedal_available method exists
                if hasattr(self.window, 'set_pedal_available'):
                    # Special handling for clutch pedal - show it as available if the pedals are connected
                    if pedal == 'clutch' and self.hardware.pedals_connected:
                        # Enable clutch UI if pedals are connected, even if no specific axis is assigned
                        self.window.set_pedal_available(pedal, True)
                    elif axis_num < 0 or axis_num >= self.hardware.available_axes:
                        # Disable UI elements for unavailable pedals
                        self.window.set_pedal_available(pedal, False)
                    else:
                        self.window.set_pedal_available(pedal, True)
                else:
                    logger.warning(f"MainWindow does not have set_pedal_available method, skipping for {pedal}")
                
                # Update curve selector if it's a custom curve and the required attributes exist
                if curve_type not in ["Linear", "Exponential", "Logarithmic", "S-Curve"]:
                    if hasattr(self.window, '_pedal_data') and pedal in self.window._pedal_data:
                        selector = self.window._pedal_data[pedal].get('curve_selector')
                        if selector:
                            # Add the custom curve type if it's not already in the list
                            if selector.findText(curve_type) == -1:
                                selector.addItem(curve_type)
                            selector.setCurrentText(curve_type)
        
        # Refresh the curve lists if the method exists
        if hasattr(self.window, 'refresh_curve_lists'):
            self.window.refresh_curve_lists()
        else:
            logger.warning("MainWindow does not have refresh_curve_lists method, skipping refresh")
    
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
        """Process input from hardware and update UI."""
        if not self.hardware:
            return
            
        try:
            # If we're in the middle of a reconnection attempt, use last known values to avoid jumps
            if self.reconnecting and hasattr(self.hardware, 'last_values'):
                raw_values = self.hardware.last_values
                logger.debug("Using last known values during reconnection attempt")
            else:
                # Read new values from hardware
                raw_values = self.hardware.read_pedals()
                
                # If we successfully read and had been reconnecting, update UI if needed
                if self.reconnecting and self.hardware.pedals_connected:
                    self.reconnecting = False
                    logger.info("Reconnection successful, resuming normal operation")
                    # Only update UI if connection state actually changed and this isn't startup
                    if hasattr(self, 'startup_complete') and self.startup_complete:
                        self.window.update_pedal_connection_status(self.hardware.pedals_connected)
            
            # Store the processed values
            processed_values = {}
            
            # Process each axis
            for pedal in ['throttle', 'brake', 'clutch']:
                # Get the raw value for this pedal
                raw_value = raw_values.get(pedal, 0)
                
                # Scale the value using calibration
                output_value = self.hardware.apply_calibration(pedal, raw_value)
                
                # Scale for vJoy (0-32767)
                vjoy_value = int(output_value * 32767 / 65535)
                
                # Store the values
                processed_values[pedal] = {
                    'raw': raw_value,
                    'output': output_value,
                    'output_vjoy': vjoy_value
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
            # If we encounter an error processing input, attempt reconnection on next cycle
            if self.hardware and self.hardware.pedals_connected:
                logger.info("Error during input processing, will attempt reconnection on next cycle")
                self.hardware.pedals_connected = False
                self.reconnecting = True
    
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
            "cli_access_denied": "Access denied when using HidHide CLI. Try running as administrator.",
            "no_admin_rights": "TrackPro requires administrator privileges to function properly. Please close TrackPro and run it as administrator."
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
    
    def handle_auth_state_change(self, is_authenticated: bool):
        """Handle changes in authentication state.
        
        Args:
            is_authenticated: Whether the user is now authenticated
        """
        logger.info(f"Authentication state changed: {'authenticated' if is_authenticated else 'not authenticated'}")
        
        # Update protected features
        if hasattr(self, 'window'):
            self.window.update_protected_features(is_authenticated)
    
    def run(self):
        """Run the application."""
        try:
            # Start in offline mode by default if not already authenticated
            if not supabase.is_authenticated():
                logger.info("Starting in offline mode by default")
                # Don't disable Supabase completely, just don't force login
                # This allows the user to login later if they want
            
            # Show the main window immediately
            self.window.show()
            
            # Start the event loop
            return self.app.exec_()
        except Exception as e:
            logger.error(f"Error running application: {e}")
            logger.error(traceback.format_exc())
            return 1

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
    hidhide_client = None
    try:
        logger.info("Initializing HidHide to disable cloaking before startup...")
        # No need to import again, it's already imported at module level
        
        # Initialize with fail_silently=True so the app can continue even if HidHide fails
        hidhide_client = HidHideClient(fail_silently=True)
        
        # Try multiple approaches to ensure cloaking is disabled
        if hidhide_client.functioning:
            # Try CLI first (most reliable)
            cli_result = hidhide_client._run_cli(["--cloak-off"], retry_count=3)
            logger.info(f"Cloak disabled via CLI before startup: {cli_result}")
            
            # Try API method as backup
            api_result = hidhide_client.set_cloak_state(False)
            logger.info(f"Cloak disabled via API before startup: {api_result}")
            
            # If device name is known, try to unhide specific devices
            if hasattr(hidhide_client, 'config') and hidhide_client.config.get('device_name'):
                device_name = hidhide_client.config.get('device_name')
            else:
                # Fallback to common device names
                device_name = "Sim Coaches P1 Pro Pedals"
            
            logger.info(f"Finding all devices matching: {device_name}")
            matching_devices = hidhide_client.find_all_matching_devices(device_name)
            if matching_devices:
                for device_path in matching_devices:
                    try:
                        # Try unhide by instance path
                        unhide_result = hidhide_client.unhide_device(device_path)
                        logger.info(f"Unhid device '{device_path}' via API: {unhide_result}")
                    except Exception as e:
                        logger.warning(f"Error unhiding device via API: {e}")
                        
                        # Fallback to CLI if available
                        try:
                            unhide_cmd_result = hidhide_client._run_cli(["--dev-unhide", device_path])
                            logger.info(f"Unhid device via CLI: {unhide_cmd_result}")
                        except Exception as e2:
                            logger.error(f"Error unhiding device via CLI: {e2}")
        else:
            logger.warning(f"HidHide not functioning, skipping pre-startup cloaking control. Error context: {hidhide_client.error_context}")
            
    except Exception as e:
        logger.error(f"Error during HidHide pre-startup: {e}")
        # Continue anyway, we'll attempt to initialize again in the app
    
    try:
        # Create and run the application
        app = TrackProApp(test_mode)
        
        # Pass the already initialized HidHide client to the app
        if hidhide_client is not None:
            app.hidhide = hidhide_client
            logger.info("Using pre-initialized HidHide client")
        
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