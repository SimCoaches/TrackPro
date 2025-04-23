import sys
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QLabel, QCheckBox, QProgressBar, QSplashScreen
from PyQt5.QtCore import QTimer, QPointF, Qt
from PyQt5.QtGui import QPixmap
import logging
# Defer pygame import
# import pygame
import os
import traceback
import re
import socket

# Defer local imports until needed in __init__ or other methods
# from .pedals.hardware_input import HardwareInput
# from .pedals.output import VirtualJoystick
from .ui import MainWindow # Needed early for window creation
# from .pedals.hidhide import HidHideClient
# from .updater import Updater
from .database import supabase # Potentially needed early depending on auth flow
from .auth import LoginDialog, oauth_handler # Needed early for auth handler

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
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
    
    def closeEvent(self, event):
        """Stop timer when window is closed."""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        super().closeEvent(event)
    
    def accept(self):
        """Stop timer when dialog is accepted."""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        super().accept()
    
    def reject(self):
        """Stop timer when dialog is rejected."""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        super().reject()
        
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
    
    def __init__(self, test_mode=False, start_time=None):
        """Initialize the application."""
        # Store start time if provided
        self.start_time = start_time

        # Ensure QApplication is properly initialized first
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
        
        # Initialize attributes that will be used later
        self.hardware = None
        self.output = None
        self.hidhide = None
        self.timer = None
        self.updater = None
        self.reconnecting = False
        self.startup_complete = False
        self.oauth_callback_server = None
        
        # Set up OAuth handler
        self.setup_oauth_handler()

        # Log time taken before creating splash screen
        if self.start_time:
            time_before_splash = time.time() - self.start_time
            logger.info(f"Time before splash screen creation: {time_before_splash:.4f} seconds")
            # Reset start_time to avoid logging again if init is somehow called twice
            self.start_time = None

        # Create and show a splash screen with progress bar
        self.create_startup_progress()
        
        try:
            # Update progress 10%
            self.update_progress(10, "Initializing interface...")
            self.window = MainWindow(oauth_handler=self.oauth_handler)
            
            # Connect auth state changed signal
            if hasattr(self.window, 'auth_state_changed'):
                self.window.auth_state_changed.connect(self.handle_auth_state_change)
            
            # Setup UI connections between window and app methods
            self.setup_ui_connections()
            
            # Setup debug log handler for debug window
            self.debug_window = None
            
            # Add button to open debug window
            self.window.add_debug_button(self.show_debug_window)
            
            # Update progress 20%
            self.update_progress(20, "Setting up hardware input...")
            
            # Import HardwareInput just before use
            from .pedals.hardware_input import HardwareInput
            # Setup hardware input and output
            self.hardware = HardwareInput(test_mode)
            
            # Update progress 30%
            self.update_progress(30, "Initializing virtual joystick...")
            # Import VirtualJoystick just before use
            from .pedals.output import VirtualJoystick
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
                    # Import HidHideClient just before use
                    from .pedals.hidhide import HidHideClient
                    self.hidhide = HidHideClient(fail_silently=True)
                    if hasattr(self.hidhide, 'functioning') and self.hidhide.functioning:
                        logger.info("HidHide client initialized successfully")
                    elif hasattr(self.hidhide, 'error_context') and self.hidhide.error_context:
                        logger.warning(f"HidHide initialized with limited functionality: {self.hidhide.error_context}")
                        self.show_hidhide_warning(self.hidhide.error_context)
                except Exception as e:
                    logger.error(f"Error initializing HidHide client: {e}")
                    self.hidhide = None
            
            # Update progress 60%
            self.update_progress(60, "Setting up input processing...")
            # Initialize timer but don't start it yet
            self.timer = QTimer()
            self.timer.timeout.connect(self.process_input)
            self.timer.setInterval(8)  # ~120Hz input polling rate
            
            # Load calibration
            self.update_progress(70, "Loading calibration data...")
            self.load_calibration()
            
            # Setup updater
            self.update_progress(80, "Initializing update checker...")
            # Import Updater just before use
            from .updater import Updater
            self.updater = Updater(self.window)
            
            # Update progress to 90%
            self.update_progress(90, "Finalizing startup...")
            
            # Mark startup as complete
            self.startup_complete = True
            
            # Start the input processing timer after startup is complete
            self.timer.start()
            
            # Start update check in background after a delay
            QTimer.singleShot(2000, lambda: self.updater.check_for_updates(silent=True))
            
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
        
        # Refresh the curve lists if the method exists - REMOVING this call
        # if hasattr(self.window, 'refresh_curve_lists'):
        #     self.window.refresh_curve_lists()
        # else:
        #     logger.warning("MainWindow does not have refresh_curve_lists method, skipping refresh")
    
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
        
        # Save calibration - use a single timer to defer save during multiple rapid changes
        if not hasattr(self, '_save_calibration_timer'):
            self._save_calibration_timer = QTimer()
            self._save_calibration_timer.setSingleShot(True)
            self._save_calibration_timer.timeout.connect(lambda: self.hardware.save_calibration(self.hardware.calibration))
        
        # If timer is active, stop it and restart with new timeout
        if self._save_calibration_timer.isActive():
            self._save_calibration_timer.stop()
        
        # Schedule a save after a short delay (500ms)
        self._save_calibration_timer.start(500)
        
        # Immediately reprocess current input to apply the new calibration
        # This ensures changes to the curve are reflected in real-time
        self.process_input()
    
    def process_input(self):
        """Process input from hardware and apply to output."""
        # Check if hardware is available
        if not self.hardware:
            return
        
        # Ensure pygame is initialized if not already (might be needed by hardware.read_pedals)
        try:
            import pygame
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                 pygame.joystick.init()
        except ImportError:
            logger.error("Pygame import failed in process_input")
            return # Cannot process input without pygame
        except Exception as e:
            logger.error(f"Error initializing pygame in process_input: {e}")
            # Optionally return or try to continue if pygame isn't strictly necessary
            # For now, we assume it is necessary for hardware.read_pedals
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
            
            # Throttle UI updates to reduce lag during calibration
            # Only update UI every other frame during calibration changes
            current_time = time.time() * 1000
            should_update_ui = True
            
            if hasattr(self, '_last_ui_update_time'):
                # Apply throttling - only update UI at ~30fps
                if current_time - self._last_ui_update_time < 33:  # ~30fps
                    should_update_ui = False
            
            if should_update_ui:
                # Update UI with the fresh values
                for pedal, values in processed_values.items():
                    self.window.set_input_value(pedal, values['raw'])
                self._last_ui_update_time = current_time
                
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            # If we encounter an error processing input, attempt reconnection on next cycle
            if self.hardware and self.hardware.pedals_connected:
                logger.info("Error during input processing, will attempt reconnection on next cycle")
                self.hardware.pedals_connected = False
                self.reconnecting = True
    
    def update_deadzones(self, pedal, min_deadzone, max_deadzone):
        """Update the deadzones for a pedal.
        
        Args:
            pedal: 'throttle', 'brake', or 'clutch'
            min_deadzone: Minimum deadzone percentage (0-100)
            max_deadzone: Maximum deadzone percentage (0-100)
        """
        # Apply deadzone to hardware
        if self.hardware and pedal in self.hardware.axis_ranges:
            self.hardware.axis_ranges[pedal]['min_deadzone'] = min_deadzone
            self.hardware.axis_ranges[pedal]['max_deadzone'] = max_deadzone
            self.hardware.save_axis_ranges()
        
        # Immediately reprocess current input to apply the new deadzones
        self.process_input()
    
    def show_profile_manager(self):
        """Show the pedal profile manager dialog."""
        try:
            # Import the profile dialog
            from .pedals.profile_dialog import PedalProfileDialog
            
            # Get current calibration data
            calibration_data = {}
            if hasattr(self, 'hardware') and hasattr(self.hardware, 'calibration'):
                for pedal in ['throttle', 'brake', 'clutch']:
                    if pedal in self.hardware.calibration:
                        calibration_data[pedal] = self.hardware.calibration[pedal]
            
            # Create and show dialog
            dialog = PedalProfileDialog(self.window, calibration_data)
            
            # Connect profile selected signal
            dialog.profile_selected.connect(self.apply_profile)
            
            # Show dialog
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing profile manager: {e}")
            if hasattr(self, 'window'):
                QMessageBox.critical(
                    self.window, 
                    "Error", 
                    f"Could not open profile manager: {str(e)}"
                )
    
    def apply_profile(self, profile):
        """Apply a selected pedal profile.
        
        Args:
            profile: The profile data dictionary
        """
        try:
            # Get calibration data from profile
            throttle_calibration = profile.get('throttle_calibration', {})
            brake_calibration = profile.get('brake_calibration', {})
            clutch_calibration = profile.get('clutch_calibration', {})
            
            # Update hardware calibration
            if hasattr(self, 'hardware'):
                # Update calibration for each pedal
                for pedal, data in [
                    ('throttle', throttle_calibration),
                    ('brake', brake_calibration),
                    ('clutch', clutch_calibration)
                ]:
                    if not data:
                        continue
                    
                    # Update calibration data in hardware
                    self.hardware.calibration[pedal] = data
                
                # Save the updated calibration
                self.hardware.save_calibration(self.hardware.calibration)
                
                # Update UI if available
                if hasattr(self, 'window'):
                    self.load_calibration()
            
            # Show confirmation
            profile_name = profile.get('name', 'Selected profile')
            if hasattr(self, 'window'):
                QMessageBox.information(
                    self.window,
                    "Profile Applied",
                    f"{profile_name} has been applied to your pedals."
                )
            
        except Exception as e:
            logger.error(f"Error applying profile: {e}")
            if hasattr(self, 'window'):
                QMessageBox.critical(
                    self.window,
                    "Error",
                    f"Could not apply profile: {str(e)}"
                )
    
    def setup_oauth_handler(self):
        """Set up the OAuth handler for the application."""
        try:
            # Create the shared OAuth handler
            logger.info("Setting up OAuth handler")
            self.oauth_handler = oauth_handler.OAuthHandler()
            
            # Connect to the auth_completed signal
            self.oauth_handler.auth_completed.connect(self.handle_auth_state_change)
            
            # Check if port 3000 is available
            try:
                # Try to bind to the port to check if it's available
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', 3000))
                sock.close()
                logger.info("Port 3000 is available for callback server")
            except socket.error:
                logger.warning("Port 3000 is already in use. OAuth callback may fail.")
                
            # Start the callback server
            self.oauth_callback_server = self.oauth_handler.setup_callback_server()
            
            logger.info("OAuth handler initialized successfully")
        except Exception as e:
            logger.error(f"Error setting up OAuth handler: {e}")
            # Create a placeholder handler just so the UI doesn't crash
            self.oauth_handler = oauth_handler.OAuthHandler()
            self.oauth_callback_server = None
    
    def cleanup(self, force_unhide=True):
        """Clean up resources before application closes."""
        logger.info("Cleaning up resources...")
        
        # Clean up Race Coach resources if it exists
        if hasattr(self, 'window') and hasattr(self.window, 'stacked_widget'):
            try:
                logger.info("Looking for Race Coach widget to clean up...")
                # Find and clean up Race Coach widget if it exists
                for i in range(self.window.stacked_widget.count()):
                    widget = self.window.stacked_widget.widget(i)
                    if widget and hasattr(widget, 'iracing_api') and widget.iracing_api:
                        logger.info("Found Race Coach widget, disconnecting iRacing API...")
                        try:
                            widget.iracing_api.disconnect()
                            logger.info("Successfully disconnected iRacing API")
                        except Exception as e:
                            logger.error(f"Error disconnecting iRacing API: {e}")
            except Exception as e:
                logger.error(f"Error cleaning up Race Coach resources: {e}")
        
        # Stop debug window timers first if it exists
        if hasattr(self, 'debug_window') and self.debug_window:
            try:
                logger.info("Stopping debug window timers...")
                if hasattr(self.debug_window, 'refresh_timer'):
                    self.debug_window.refresh_timer.stop()
            except Exception as e:
                logger.error(f"Error stopping debug window timers: {e}")
        
        # Stop the timer
        if hasattr(self, 'timer') and self.timer:
            logger.info("Stopping main input timer...")
            self.timer.stop()
        
        # Disconnect all signals
        try:
            logger.info("Disconnecting signals...")
            if hasattr(self.window, 'calibration_updated'):
                try:
                    self.window.calibration_updated.disconnect()
                except TypeError:
                    pass  # Already disconnected
            
            if hasattr(self.window, 'output_changed'):
                try: 
                    self.window.output_changed.disconnect()
                except TypeError:
                    pass  # Already disconnected
                    
            if hasattr(self.window, 'calibration_wizard_completed'):
                try:
                    self.window.calibration_wizard_completed.disconnect()
                except TypeError:
                    pass  # Already disconnected
                    
            # Disconnect aboutToQuit signal
            try:
                self.app.aboutToQuit.disconnect()
            except TypeError:
                pass  # Already disconnected
        except Exception as e:
            logger.error(f"Error disconnecting signals: {e}")
        
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
        
        # Save calibration before changing HidHide settings
        if hasattr(self, 'hardware') and self.hardware:
            try:
                logger.info("Saving calibration...")
                self.hardware.save_calibration(self.hardware.calibration)
            except Exception as e:
                logger.error(f"Error saving calibration: {e}")
        
        # Disable HidHide cloaking - PRIORITIZE CLI --cloak-off approach
        if hasattr(self, 'hidhide') and self.hidhide:
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
        
        # Shutdown OAuth callback server
        if hasattr(self, 'oauth_callback_server') and self.oauth_callback_server:
            try:
                logger.info("Shutting down OAuth callback server...")
                if hasattr(self, 'oauth_handler'):
                    self.oauth_handler.shutdown_callback_server(self.oauth_callback_server)
            except Exception as e:
                logger.error(f"Error shutting down OAuth callback server: {e}")
        
        # Clean up pygame resources
        if hasattr(self, 'hardware') and hasattr(self.hardware, 'pedals_connected') and self.hardware.pedals_connected:
            try:
                # Ensure pygame is imported for cleanup
                import pygame
                logger.info("Cleaning up pygame resources...")
                # Release the joystick object first
                if hasattr(self.hardware, 'joystick') and self.hardware.joystick:
                    try:
                        self.hardware.joystick.quit()
                    except:
                        pass
                    self.hardware.joystick = None
                pygame.joystick.quit()
            except Exception as e:
                logger.error(f"Error cleaning up pygame resources: {e}")
        
        logger.info("Cleanup completed")
        
        # Process any remaining events to avoid threading issues on exit
        QApplication.processEvents()
    
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
    
    def handle_auth_state_change(self, is_authenticated):
        """Handles the authentication state change from the OAuth handler or initial load."""
        # Prevent running during initial startup before hardware is ready
        if not self.startup_complete:
            logger.debug("handle_auth_state_change called before startup complete, skipping.")
            return
            
        logger.info(f"Authentication state changed (post-startup): {is_authenticated}")

        # Ensure UI updates first (display login status, etc.) - REMOVED call to break loop
        # if hasattr(self, 'window'):
        #     self.window.update_auth_state() # Let the UI know first

        if is_authenticated:
            logger.info("User authenticated. Attempting to sync calibration and refresh curves.")
            # Sync calibration AFTER login
            if hasattr(self, 'hardware') and self.hardware:
                try:
                    # Call the correct sync method (remove force_download if not supported)
                    if hasattr(self.hardware, '_sync_with_cloud'):
                        logger.info("Calling hardware._sync_with_cloud()...")
                        self.hardware._sync_with_cloud()
                    else:
                        logger.warning("hardware._sync_with_cloud() method not found.")
                        
                    # Load potentially updated calibration into UI
                    self.load_calibration()
                except Exception as e:
                    logger.error(f"Error during post-authentication sync/load: {e}")
            else:
                logger.warning("Hardware not available for post-authentication sync/load.")

            # Refresh curve lists AFTER login and potential sync
            if hasattr(self, 'window') and hasattr(self.window, 'refresh_curve_lists') and self.hardware:
                 logger.info("Refreshing curve lists post-authentication...")
                 try:
                     self.window.refresh_curve_lists() # Refresh lists AFTER login
                 except Exception as e:
                     logger.error(f"Error refreshing curve lists post-authentication: {e}")
            else:
                logger.warning("Window, refresh_curve_lists method, or hardware not available for post-auth refresh.")
        else:
            # Handle logout state if needed (e.g., load default curves/calibration)
            logger.info("User is not authenticated or logged out.")
            # Optionally: Load default calibration or clear user-specific settings
            # self.load_default_calibration()
            # if hasattr(self, 'window') and hasattr(self.window, 'refresh_curve_lists'):
            #    self.window.refresh_curve_lists() # Refresh to show only local/default curves


        # Emit signal for other components (like Race Coach) if needed
        # This was previously inside update_auth_state in the UI, REMOVED here to prevent recursion
        # if hasattr(self, 'window'):
        #     self.window.auth_state_changed.emit(is_authenticated)

    def run(self):
        """Main application execution loop."""
        try:
            # Start in offline mode by default if not already authenticated
            if not supabase.is_authenticated():
                logger.info("Starting in offline mode by default")
                # Don't disable Supabase completely, just don't force login
                # This allows the user to login later if they want
            
            # Show the main window immediately
            self.window.show()
            
            # Start the event loop
            exit_code = self.app.exec_()
            
            # Process any remaining events before we return
            QApplication.processEvents()
            
            # Ensure cleanup
            try:
                if hasattr(self, 'cleanup'):
                    self.cleanup()
            except:
                logger.warning("Error during cleanup on exit")
                
            return exit_code
        except Exception as e:
            logger.error(f"Error running application: {e}")
            logger.error(traceback.format_exc())
            return 1

    def setup_ui_connections(self):
        """Set up connections between UI signals and app methods."""
        if not hasattr(self, 'window'):
            logger.warning("Window not available to set up connections")
            return
            
        # Connect the calibration updated signal to our handler
        if hasattr(self.window, 'calibration_updated'):
            self.window.calibration_updated.connect(self.on_calibration_updated)
        
        # Connect UI buttons to app methods
        if hasattr(self.window, 'save_current_profile'):
            self.window.save_current_profile = self.show_profile_manager
        
        if hasattr(self.window, 'show_profile_manager'):
            self.window.show_profile_manager = self.show_profile_manager

def main():
    """Main entry point for the application."""
    start_time = time.time()  # Record start time
    logger.info("TrackPro Application Starting...")

    # --- Argument Parsing (Optional) ---
    # If you need command-line arguments, parse them here.
    # For now, we'll assume no special arguments are needed.
    test_mode = False # Set to True for testing without hardware perhaps

    # --- Ensure Single Instance (Optional but Recommended for GUI apps) ---
    # Implement single instance lock if needed (e.g., using a lock file or QSharedMemory)

    # --- Exception Handling ---
    try:
        # Set application details (optional but good practice)
        QApplication.setApplicationName("TrackPro")
        # TODO: Read version from a central place (e.g., __init__.py or config file)
        QApplication.setApplicationVersion("1.4.5")

        # Initialize and run the application
        trackpro_app = TrackProApp(test_mode=test_mode, start_time=start_time)
        trackpro_app.run()

    except Exception as e:
        # Log the exception
        logger.critical(f"Unhandled exception occurred: {e}", exc_info=True)

        # Attempt to show an error message box (might fail if QApplication isn't running)
        try:
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setWindowTitle("TrackPro Critical Error")
            error_dialog.setText("A critical error occurred and TrackPro must exit.")
            error_dialog.setDetailedText(traceback.format_exc())
            error_dialog.setStandardButtons(QMessageBox.Ok)
            error_dialog.exec_()
        except Exception as msg_e:
            logger.error(f"Could not display the error message box: {msg_e}")

        sys.exit(1) # Exit with an error code

if __name__ == '__main__':
    main() 