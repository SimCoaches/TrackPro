#!/usr/bin/env python3
"""
iRacing Xbox Controller Brake Tester

Real-time testing of Xbox controller brake input with threshold assist.
Connects to live iRacing data to test with real cars (ABS vs non-ABS).
Features AUTOMATIC lockup detection using physics analysis.
"""

import sys
import os
import time
import pygame
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QLabel, QSlider, QCheckBox, 
                           QTextEdit, QGroupBox, QGridLayout, QComboBox, QMessageBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPainter, QColor

# Add the trackpro module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from trackpro.pedals.threshold_braking_assist import RealTimeBrakingAssist
    from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
    from trackpro.pedals.output import VirtualJoystick
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    print("Creating dummy classes for testing.")
    
# Local fallback classes removed - using real RealTimeBrakingAssist from trackpro.pedals.threshold_braking_assist
    
    class SimpleIRacingAPI:
        def __init__(self):
            self.connected = False
            self.current_telemetry = {}
        
        def connect(self): 
            self.connected = False
            return False
        
        def disconnect(self):
            self.connected = False
        
        def get_telemetry(self): 
            return {}
        
        def register_on_telemetry_data(self, callback):
            pass

class BrakeVisualizationWidget(QWidget):
    """Widget to visualize brake input and lockup detection"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 400)
        
        # Data for visualization
        self.brake_input = 0.0
        self.brake_output = 0.0
        self.reduction_percentage = 0.0
        self.lockup_detected = False
        self.lockup_method = ""
        
    def update_data(self, brake_input, brake_output, reduction_percentage, lockup_detected, lockup_method=""):
        """Update the visualization data"""
        self.brake_input = brake_input
        self.brake_output = brake_output
        self.reduction_percentage = reduction_percentage
        self.lockup_detected = lockup_detected
        self.lockup_method = lockup_method
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event for visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        # Title
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(20, 30, "🚗 Real-Time Brake Threshold Assistant")
        
        # Input brake bar
        input_width = int(self.brake_input * 350)
        painter.fillRect(50, 80, 350, 40, QColor(60, 60, 60))
        painter.fillRect(50, 80, input_width, 40, QColor(100, 150, 255))
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 12))
        painter.drawText(50, 75, f"Your Brake Input: {self.brake_input:.1%}")
        painter.drawText(420, 100, f"{self.brake_input:.1%}")
        
        # Output brake bar (what goes to iRacing)
        output_width = int(self.brake_output * 350)
        output_color = QColor(255, 100, 100) if self.lockup_detected else QColor(100, 255, 100)
        painter.fillRect(50, 150, 350, 40, QColor(60, 60, 60))
        painter.fillRect(50, 150, output_width, 40, output_color)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(50, 145, f"Output to iRacing: {self.brake_output:.1%}")
        painter.drawText(420, 170, f"{self.brake_output:.1%}")
        
        # Reduction indicator
        if self.reduction_percentage > 0:
            painter.setPen(QColor(255, 200, 100))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(50, 220, f"⚡ ACTIVE: Reducing by {self.reduction_percentage:.1f}%")
            if self.lockup_method:
                painter.setFont(QFont("Arial", 10))
                painter.drawText(50, 240, f"Detection: {self.lockup_method}")
        else:
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(50, 220, "✅ No lockup detected - full brake power")
        
        # Lockup indicator
        if self.lockup_detected:
            painter.setPen(QColor(255, 100, 100))
            painter.setFont(QFont("Arial", 16, QFont.Bold))
            painter.drawText(450, 100, "🚨 LOCKUP!")
            painter.drawText(450, 130, "CORRECTING...")

class SimpleBrakeTester(QMainWindow):
    """iRacing Xbox controller brake tester with real telemetry and automatic lockup detection"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TrackPro - Real-Time Brake Threshold Assistant")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize Xbox controller
        self.init_xbox_controller()
        
        # Initialize vJoy virtual joystick for output to iRacing
        self.init_virtual_joystick()
        
        # Initialize iRacing connection
        self.iracing_api = SimpleIRacingAPI()
        self.iracing_connected = False
        self.current_telemetry = {}
        self.current_track = "Unknown"
        self.current_car = "Unknown"
        self.latest_telemetry = {}  # Store latest telemetry from callback
        
        # Initialize NEW ABS-style braking assist (PRACTICAL RACING SETTINGS)
        self.threshold_assist = RealTimeBrakingAssist(
            lockup_reduction=18.0,  # 18% emergency drop for real racing
            recovery_rate=2.0       # Not used in new system but required for compatibility
        )
        self.threshold_assist.set_enabled(True)
        
        # Controller settings
        self.brake_axis = -1  # -1 means auto-detect
        
        # Setup UI
        self.setup_ui()
        
        # Start update timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(33)  # ~30 FPS
        
        self.iracing_timer = QTimer()
        self.iracing_timer.timeout.connect(self.update_iracing_connection)
        self.iracing_timer.start(1000)  # Check connection every second
        
        # Setup logging
        self.setup_logging()
        
        self.logger.info("🎮 iRacing brake tester started!")
        self.logger.info("🔌 Start iRacing and click 'Connect to iRacing' to begin")
        self.logger.info("🔍 AUTOMATIC lockup detection enabled - no manual input required!")
    
    def init_xbox_controller(self):
        """Initialize Xbox controller with pygame"""
        pygame.init()
        pygame.joystick.init()
        
        self.joystick = None
        self.controller_list = []
        
        # Detect all available controllers
        num_controllers = pygame.joystick.get_count()
        print(f"Found {num_controllers} controller(s):")
        
        # Find Xbox controller (prefer Xbox over others)
        xbox_controller = None
        controller_name = "Unknown"
        
        for i in range(num_controllers):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            name = joystick.get_name().lower()
            
            # Prefer Xbox controllers
            if 'xbox' in name or ('controller' in name and 'vjoy' not in name):
                xbox_controller = joystick
                controller_name = joystick.get_name()
                print(f"✅ Using Xbox controller: {controller_name}")
                break
        
        # If no Xbox controller found, check for vJoy or other controllers
        if not xbox_controller:
            for i in range(num_controllers):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                name = joystick.get_name().lower()
                
                # Accept vJoy as fallback for manual testing
                if 'vjoy' in name:
                    xbox_controller = joystick
                    controller_name = joystick.get_name()
                    print(f"⚠️  Using vJoy device for manual testing: {controller_name}")
                    print(f"💡 Note: Connect a wired Xbox controller for normal use")
                    break
                # Or any other controller
                else:
                    xbox_controller = joystick
                    controller_name = joystick.get_name()
                    print(f"⚠️  Using controller: {controller_name}")
                    break
        
        if not xbox_controller:
            print("❌ No controller found - using simulation mode")
        else:
            self.joystick = xbox_controller
            print(f"ℹ Controller axes: {self.joystick.get_numaxes()}")
            print(f"ℹ Controller buttons: {self.joystick.get_numbuttons()}")
    
    def init_virtual_joystick(self):
        """Initialize vJoy virtual joystick for output to iRacing"""
        print("🔧 DEBUG: Starting vJoy initialization...")
        try:
            print("🔧 DEBUG: Creating VirtualJoystick(test_mode=False)...")
            self.virtual_joystick = VirtualJoystick(test_mode=False)
            self.vjoy_active = True
            print("✅ vJoy virtual joystick initialized successfully")
            print("🎮 iRacing will see brake input from vJoy device")
            print(f"🔧 DEBUG: vJoy status - virtual_joystick: {self.virtual_joystick}, vjoy_active: {self.vjoy_active}")
        except Exception as e:
            print(f"⚠ vJoy initialization failed: {e}")
            print(f"🔧 DEBUG: Exception type: {type(e).__name__}")
            print(f"🔧 DEBUG: Exception details: {str(e)}")
            print("🔄 Falling back to test mode - brake output will be simulated")
            try:
                print("🔧 DEBUG: Trying VirtualJoystick(test_mode=True)...")
                self.virtual_joystick = VirtualJoystick(test_mode=True)
                self.vjoy_active = False
                print("✅ vJoy test mode initialized")
                print(f"🔧 DEBUG: Test mode status - virtual_joystick: {self.virtual_joystick}, vjoy_active: {self.vjoy_active}")
            except Exception as e2:
                print(f"❌ Even test mode failed: {e2}")
                print(f"🔧 DEBUG: Test mode exception: {type(e2).__name__}: {str(e2)}")
                self.virtual_joystick = None
                self.vjoy_active = False
                print(f"🔧 DEBUG: Final fallback - virtual_joystick: {self.virtual_joystick}, vjoy_active: {self.vjoy_active}")
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("iRacing Xbox Controller Brake Tester with Real-Time Lockup Correction")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #27ae60;")
        layout.addWidget(title)
        
        # iRacing connection section
        iracing_group = QGroupBox("iRacing Connection")
        iracing_grid = QGridLayout(iracing_group)
        
        iracing_grid.addWidget(QLabel("Status:"), 0, 0)
        self.iracing_status_label = QLabel("❌ Disconnected")
        self.iracing_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        iracing_grid.addWidget(self.iracing_status_label, 0, 1)
        
        iracing_grid.addWidget(QLabel("Track:"), 1, 0)
        self.track_label = QLabel("Unknown")
        self.track_label.setStyleSheet("color: #888888; font-weight: bold;")
        iracing_grid.addWidget(self.track_label, 1, 1)
        
        iracing_grid.addWidget(QLabel("Car:"), 2, 0)
        self.car_label = QLabel("Unknown")
        self.car_label.setStyleSheet("color: #888888; font-weight: bold;")
        iracing_grid.addWidget(self.car_label, 2, 1)
        
        iracing_grid.addWidget(QLabel("ABS Available:"), 3, 0)
        self.abs_available_label = QLabel("Unknown")
        self.abs_available_label.setStyleSheet("color: #888888; font-weight: bold;")
        iracing_grid.addWidget(self.abs_available_label, 3, 1)
        
        self.connect_button = QPushButton("Connect to iRacing")
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.connect_button.clicked.connect(self.toggle_iracing_connection)
        iracing_grid.addWidget(self.connect_button, 4, 0, 1, 2)
        
        layout.addWidget(iracing_group)
        
        # Status section
        status_layout = QHBoxLayout()
        
        # Current values
        status_group = QGroupBox("Live Status")
        status_grid = QGridLayout(status_group)
        
        status_grid.addWidget(QLabel("Raw Brake:"), 0, 0)
        self.raw_brake_label = QLabel("0.000")
        self.raw_brake_label.setStyleSheet("color: #ff6464; font-weight: bold; font-size: 14px;")
        status_grid.addWidget(self.raw_brake_label, 0, 1)
        
        status_grid.addWidget(QLabel("Assisted Brake:"), 1, 0)
        self.assisted_brake_label = QLabel("0.000")
        self.assisted_brake_label.setStyleSheet("color: #64ff64; font-weight: bold; font-size: 14px;")
        status_grid.addWidget(self.assisted_brake_label, 1, 1)
        
        status_grid.addWidget(QLabel("Lockup Active:"), 2, 0)
        self.abs_status_label = QLabel("NO")
        self.abs_status_label.setStyleSheet("color: #888888; font-weight: bold;")
        status_grid.addWidget(self.abs_status_label, 2, 1)
        
        status_grid.addWidget(QLabel("Assist Active:"), 3, 0)
        self.assist_status_label = QLabel("NO")
        self.assist_status_label.setStyleSheet("color: #888888; font-weight: bold;")
        status_grid.addWidget(self.assist_status_label, 3, 1)
        
        status_grid.addWidget(QLabel("ABS State:"), 4, 0)
        self.abs_state_label = QLabel("🎯 READY")
        self.abs_state_label.setStyleSheet("color: #44ff44; font-weight: bold;")
        status_grid.addWidget(self.abs_state_label, 4, 1)
        
        status_grid.addWidget(QLabel("Lockup Pressure:"), 5, 0)
        self.lockup_pressure_label = QLabel("0.000")
        self.lockup_pressure_label.setStyleSheet("color: #888888; font-weight: bold;")
        status_grid.addWidget(self.lockup_pressure_label, 5, 1)
        
        status_grid.addWidget(QLabel("Target Threshold:"), 6, 0)
        self.target_threshold_label = QLabel("0.000")
        self.target_threshold_label.setStyleSheet("color: #888888; font-weight: bold;")
        status_grid.addWidget(self.target_threshold_label, 6, 1)
        
        status_grid.addWidget(QLabel("Efficiency:"), 7, 0)
        self.efficiency_label = QLabel("0.0%")
        self.efficiency_label.setStyleSheet("color: #888888; font-weight: bold;")
        status_grid.addWidget(self.efficiency_label, 7, 1)
        
        status_grid.addWidget(QLabel("vJoy Output:"), 8, 0)
        self.vjoy_status_label = QLabel("❌ DISCONNECTED")
        self.vjoy_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        status_grid.addWidget(self.vjoy_status_label, 8, 1)
        
        status_layout.addWidget(status_group)
        
        # Settings
        settings_group = self.create_settings_panel()
        status_layout.addWidget(settings_group)
        
        layout.addLayout(status_layout)
        
        # Controls
        controls_group = self.create_controls_panel()
        layout.addWidget(controls_group)
        
        # Live axis values
        self.axis_display = QLabel("Controller axis values will appear here...")
        self.axis_display.setStyleSheet("background-color: #2d2d2d; color: #ffffff; font-family: monospace; padding: 10px;")
        self.axis_display.setMinimumHeight(60)
        layout.addWidget(self.axis_display)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(200)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: monospace;")
        layout.addWidget(self.log_output)
    
    def create_settings_panel(self):
        """Create the settings panel"""
        group = QGroupBox("Settings")
        layout = QGridLayout(group)
        
        # Controller selection
        layout.addWidget(QLabel("Controller:"), 0, 0)
        self.controller_combo = QComboBox()
        self.controller_combo.addItem("Auto-detect")
        for i, name, joystick in self.controller_list:
            display_name = name
            if 'vjoy' in name.lower():
                display_name += " ⚠ (vJoy)"
            self.controller_combo.addItem(f"{i}: {display_name}")
        self.controller_combo.currentIndexChanged.connect(self.select_controller)
        layout.addWidget(self.controller_combo, 0, 1, 1, 2)
        
        # Brake axis selection
        layout.addWidget(QLabel("Brake Axis:"), 1, 0)
        self.axis_combo = QComboBox()
        self.axis_combo.addItem("Auto-detect")
        if self.joystick:
            for axis in range(self.joystick.get_numaxes()):
                self.axis_combo.addItem(f"Axis {axis}")
        self.axis_combo.currentIndexChanged.connect(self.select_brake_axis)
        layout.addWidget(self.axis_combo, 1, 1, 1, 2)
        
        # Reduction percentage
        layout.addWidget(QLabel("Brake Reduction:"), 2, 0)
        self.reduction_slider = QSlider(Qt.Horizontal)
        self.reduction_slider.setRange(20, 120)  # 2.0% to 12.0%
        self.reduction_slider.setValue(50)  # Default 5.0%
        self.reduction_slider.valueChanged.connect(self.update_reduction_percentage)
        layout.addWidget(self.reduction_slider, 2, 1)
        
        self.reduction_label = QLabel("5.0%")
        layout.addWidget(self.reduction_label, 2, 2)
        
        return group
    
    def create_controls_panel(self):
        """Create the controls panel"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout(group)
        
        # Enable/disable assist
        self.assist_enabled = QCheckBox("Threshold Assist Enabled")
        self.assist_enabled.setChecked(True)
        self.assist_enabled.stateChanged.connect(self.toggle_assist)
        layout.addWidget(self.assist_enabled)
        
        # Reset reductions
        reset_btn = QPushButton("Reset Active Reductions")
        reset_btn.clicked.connect(self.reset_learning)
        layout.addWidget(reset_btn)
        
        # REMOVED: Manual lockup button - drivers need to focus on driving!
        # System now uses only automatic detection via telemetry
        
        return group
    
    def setup_logging(self):
        """Setup logging to display in the UI"""
        class UILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.append(msg)
                # Keep only last 50 lines
                if self.text_widget.document().lineCount() > 50:
                    cursor = self.text_widget.textCursor()
                    cursor.movePosition(cursor.Start)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
        
        # Setup logging
        logger = logging.getLogger("BrakeTester")
        logger.setLevel(logging.INFO)
        
        handler = UILogHandler(self.log_output)
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        self.logger = logger
    
    def get_xbox_brake_input(self) -> float:
        """Get brake input from Xbox controller or vJoy device"""
        if self.joystick:
            pygame.event.pump()
            
            try:
                controller_name = self.joystick.get_name().lower()
                
                # Use selected axis for brake input
                if self.brake_axis >= 0:
                    raw_value = self.joystick.get_axis(self.brake_axis)
                    
                    # Handle different trigger types
                    if self.brake_axis in [4, 5]:  # Trigger axes (usually -1 to 1, neutral at -1)
                        brake_raw = (raw_value + 1.0) / 2.0
                    else:  # Regular axes (-1 to 1, neutral at 0)
                        brake_raw = max(0.0, abs(raw_value))
                    
                    return max(0.0, min(1.0, brake_raw))
                
                # Auto-detect brake input based on controller type
                num_axes = self.joystick.get_numaxes()
                
                if 'vjoy' in controller_name:
                    # vJoy Device: Use axis 0 (X-axis) for brake input for manual testing
                    # User can move the X-axis to simulate brake input
                    if num_axes > 0:
                        axis_value = self.joystick.get_axis(0)
                        # Convert from -1..1 to 0..1 (right movement = brake)
                        brake_raw = max(0.0, axis_value)
                    else:
                        brake_raw = 0.0
                elif num_axes > 5:
                    # Xbox 360/One Controller - Right trigger is axis 5
                    trigger_value = self.joystick.get_axis(5)
                    brake_raw = (trigger_value + 1.0) / 2.0
                elif num_axes > 4:
                    # Some controllers - Left trigger is axis 4
                    trigger_value = self.joystick.get_axis(4)  
                    brake_raw = (trigger_value + 1.0) / 2.0
                elif num_axes > 3:
                    # Alternative: Right stick Y-axis
                    stick_value = self.joystick.get_axis(3)
                    brake_raw = max(0.0, -stick_value)
                else:
                    brake_raw = 0.0
                
                return max(0.0, min(1.0, brake_raw))
                
            except Exception as e:
                print(f"Error reading controller: {e}")
                return 0.0
        else:
            # Simulate brake input with sine wave for testing
            return max(0.0, abs(time.time() % 6 - 3) / 3.0)
    
    def get_throttle_input(self) -> float:
        """Get throttle input from Xbox controller or vJoy device for passthrough"""
        if self.joystick:
            try:
                pygame.event.pump()
                controller_name = self.joystick.get_name().lower()
                
                if 'vjoy' in controller_name:
                    # vJoy Device: Use axis 1 (Y-axis) for throttle input for manual testing
                    if self.joystick.get_numaxes() > 1:
                        axis_value = self.joystick.get_axis(1)
                        # Convert from -1..1 to 0..1 (up movement = throttle)
                        return max(0.0, -axis_value)
                    return 0.0
                else:
                    # Xbox controller: Right trigger is typically axis 5
                    if self.joystick.get_numaxes() > 5:
                        trigger_value = self.joystick.get_axis(5)
                        return max(0.0, (trigger_value + 1.0) / 2.0)
                    elif self.joystick.get_numaxes() > 4:
                        # Alternative mapping
                        trigger_value = self.joystick.get_axis(4)
                        return max(0.0, (trigger_value + 1.0) / 2.0)
                    return 0.0
            except:
                return 0.0
        return 0.0
    
    def get_clutch_input(self) -> float:
        """Get clutch input from Xbox controller or vJoy device for passthrough"""
        if self.joystick:
            try:
                pygame.event.pump()
                controller_name = self.joystick.get_name().lower()
                
                if 'vjoy' in controller_name:
                    # vJoy Device: Use axis 2 for clutch input for manual testing
                    if self.joystick.get_numaxes() > 2:
                        axis_value = self.joystick.get_axis(2)
                        # Convert from -1..1 to 0..1
                        return max(0.0, (axis_value + 1.0) / 2.0)
                    return 0.0
                else:
                    # Xbox controller: Left stick Y-axis is typically axis 1
                    if self.joystick.get_numaxes() > 1:
                        stick_value = self.joystick.get_axis(1)
                        return max(0.0, (stick_value + 1.0) / 2.0)
                    return 0.0
            except:
                return 0.0
        return 0.0
    
    def update_data(self):
        """Update brake data and UI"""
        # DEBUG: Check if update_data is being called
        if not hasattr(self, '_update_call_count'):
            self._update_call_count = 0
        self._update_call_count += 1
        
        # Log debug info every 300 calls (~10 seconds)
        if self._update_call_count % 300 == 1:
            print(f"🔧 DEBUG UPDATE #{self._update_call_count}: virtual_joystick={getattr(self, 'virtual_joystick', 'NOT_SET')}")
            print(f"🔧 DEBUG UPDATE #{self._update_call_count}: vjoy_active={getattr(self, 'vjoy_active', 'NOT_SET')}")
            print(f"🔧 DEBUG UPDATE #{self._update_call_count}: hasattr virtual_joystick={hasattr(self, 'virtual_joystick')}")
        
        # Get brake input
        raw_brake = self.get_xbox_brake_input()
        
        # Get real iRacing telemetry data
        if self.iracing_connected and self.latest_telemetry:
            self.current_telemetry = self.latest_telemetry.copy()
        else:
            # No iRacing connection - use minimal telemetry
            self.current_telemetry = {
                'BrakeABSactive': False,
                'Brake': 0.0,
                'Speed': 0.0,
                'RPM': 0,
                'LongAccel': 0.0
            }
        
        # Process with NEW ABS-style threshold assist using REAL iRacing telemetry
        assisted_brake = self.threshold_assist.apply_assist(raw_brake, self.current_telemetry)
        assist_active = abs(assisted_brake - raw_brake) > 0.001
        
        # Get real ABS status from iRacing (not simulated)
        abs_active = self.current_telemetry.get('BrakeABSactive', False)
        
        # Send brake output to vJoy - THIS IS THE KEY PART!
        has_virtual_joystick = hasattr(self, 'virtual_joystick')
        virtual_joystick_value = getattr(self, 'virtual_joystick', None)
        vjoy_active_value = getattr(self, 'vjoy_active', None)
        
        # Debug every 300 calls (~10 seconds)
        if self._update_call_count % 300 == 1:
            self.logger.info(f"🔧 VJOY DEBUG: has_virtual_joystick={has_virtual_joystick}, virtual_joystick={virtual_joystick_value}, vjoy_active={vjoy_active_value}")
        
        if has_virtual_joystick and virtual_joystick_value:
            # Only log vJoy status occasionally (every 2 seconds)
            if self._update_call_count % 40 == 1:
                self.logger.info(f"🔧 vJoy status - active: {vjoy_active_value}, device exists: {has_virtual_joystick}")
            
            # ===== CRITICAL: vJoy OUTPUT TO iRacing =====
            try:
                # Get all controller inputs for passthrough
                throttle_input = self.get_throttle_input()
                clutch_input = self.get_clutch_input()
                
                # Only log inputs when significant changes occur
                if abs(raw_brake - getattr(self, '_last_raw_brake', 0)) > 0.1 or assist_active or self._update_call_count % 40 == 1:
                    self.logger.info(f"🎮 Input: T={throttle_input:.2f} B={raw_brake:.2f}→{assisted_brake:.2f} C={clutch_input:.2f} {'⚡ASSIST' if assist_active else ''}")
                    self._last_raw_brake = raw_brake
                
                # Convert to vJoy range (0.0-1.0 → 0-65535 integers)
                throttle_vjoy = int(throttle_input * 65535)  # 0.0-1.0 → 0-65535 integer
                brake_vjoy = int(assisted_brake * 65535)     # Use ASSISTED brake value → 0-65535 integer
                clutch_vjoy = int(clutch_input * 65535)      # 0.0-1.0 → 0-65535 integer
                
                # Send to vJoy - iRacing will see these values
                self.virtual_joystick.update_axis(throttle_vjoy, brake_vjoy, clutch_vjoy)
                
                # Success logging only for significant changes
                if abs(raw_brake - getattr(self, '_last_output_brake', 0)) > 0.05 or assist_active or self._update_call_count % 40 == 1:
                    self.logger.info(f"✅ vJoy OUTPUT: T={throttle_input:.2f} B={assisted_brake:.2f} C={clutch_input:.2f}")
                    self._last_output_brake = raw_brake
                
                # Log vJoy output when assist is active
                if assist_active and hasattr(self, '_vjoy_log_count'):
                    self._vjoy_log_count = getattr(self, '_vjoy_log_count', 0) + 1
                    if self._vjoy_log_count % 60 == 1:  # Log every ~2 seconds when active
                        self.logger.info(f"🎮 vJoy ASSIST OUTPUT: Brake reduced from {raw_brake:.3f} to {assisted_brake:.3f} (-{((raw_brake-assisted_brake)/raw_brake*100):.1f}%)")
                elif not hasattr(self, '_vjoy_log_count'):
                    self._vjoy_log_count = 0
                
            except Exception as e:
                self.logger.error(f"❌ vJoy OUTPUT FAILED: {e}")
                self.logger.error(f"❌ vJoy error details: {type(e).__name__}: {str(e)}")
        else:
            # Debug why vJoy is not available every ~10 seconds
            if self._update_call_count % 300 == 1:
                self.logger.warning(f"⚠ vJoy not available - has_virtual_joystick: {has_virtual_joystick}, virtual_joystick: {virtual_joystick_value}")
        
        # Update status labels
        self.raw_brake_label.setText(f"{raw_brake:.3f}")
        self.assisted_brake_label.setText(f"{assisted_brake:.3f}")
        
        # Get NEW ABS system status for display
        status = self.threshold_assist.get_status()
        
        # Update status indicators
        if abs_active:
            self.abs_status_label.setText("🚨 YES")
            self.abs_status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        else:
            self.abs_status_label.setText("NO")
            self.abs_status_label.setStyleSheet("color: #888888; font-weight: bold;")
        
        if assist_active:
            self.assist_status_label.setText("🎯 YES")
            self.assist_status_label.setStyleSheet("color: #44ff44; font-weight: bold;")
        else:
            self.assist_status_label.setText("NO")
            self.assist_status_label.setStyleSheet("color: #888888; font-weight: bold;")
        
        # Update NEW ABS state with color coding
        abs_state = status.get('abs_state', 'READY')
        self.abs_state_label.setText(abs_state)
        
        # Color code the ABS state
        if abs_state == "READY":
            self.abs_state_label.setStyleSheet("color: #44ff44; font-weight: bold;")  # Green
        elif abs_state == "LOCKUP_DETECTED":
            self.abs_state_label.setStyleSheet("color: #ff4444; font-weight: bold;")  # Red
        elif abs_state == "PRESSURE_DROP":
            self.abs_state_label.setStyleSheet("color: #ffff44; font-weight: bold;")  # Yellow
        elif abs_state == "RECOVERY":
            self.abs_state_label.setStyleSheet("color: #44ffff; font-weight: bold;")  # Cyan
        elif abs_state == "THRESHOLD_MAINTAIN":
            self.abs_state_label.setStyleSheet("color: #ff44ff; font-weight: bold;")  # Magenta
        
        # Update ABS system information
        self.lockup_pressure_label.setText(f"{status.get('lockup_pressure', 0.0):.3f}")
        self.target_threshold_label.setText(f"{status.get('target_threshold', 0.0):.3f}")
        self.efficiency_label.setText(f"{status.get('threshold_efficiency', 0.0):.1f}%")
        
        # Update vJoy status
        if hasattr(self, 'vjoy_active') and self.vjoy_active:
            self.vjoy_status_label.setText("✅ ACTIVE")
            self.vjoy_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        elif hasattr(self, 'virtual_joystick') and self.virtual_joystick:
            self.vjoy_status_label.setText("⚠ TEST MODE")
            self.vjoy_status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        else:
            self.vjoy_status_label.setText("❌ DISCONNECTED")
            self.vjoy_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # Update axis values display
        if self.joystick:
            pygame.event.pump()
            try:
                axis_text = []
                for axis in range(min(8, self.joystick.get_numaxes())):  # Show first 8 axes
                    value = self.joystick.get_axis(axis)
                    if self.brake_axis == axis:
                        axis_text.append(f"Axis {axis}: {value:+.3f} ← BRAKE")
                    else:
                        axis_text.append(f"Axis {axis}: {value:+.3f}")
                
                controller_info = f"Controller: {self.joystick.get_name()}\n"
                controller_info += " | ".join(axis_text)
                self.axis_display.setText(controller_info)
                
            except Exception as e:
                self.axis_display.setText(f"Error reading controller: {e}")
        else:
            self.axis_display.setText("No controller connected - using simulation mode")
        
        # Log significant events
        if abs_active and assist_active:
            self.logger.info(f"🚨 LOCKUP + 🎯 ASSIST: {raw_brake:.3f} → {assisted_brake:.3f}")
        elif abs_active:
            self.logger.info(f"🚨 WHEEL LOCKUP detected at brake={raw_brake:.3f}")
    
    def select_controller(self, index):
        """Select a specific controller"""
        if index == 0:  # Auto-detect
            self.init_xbox_controller()
            self.logger.info("Controller: Auto-detect mode")
        else:
            controller_index = index - 1
            if controller_index < len(self.controller_list):
                i, name, joystick = self.controller_list[controller_index]
                self.joystick = joystick
                self.logger.info(f"Selected controller: {name}")
                
                # Update axis combo box
                self.axis_combo.clear()
                self.axis_combo.addItem("Auto-detect")
                for axis in range(self.joystick.get_numaxes()):
                    self.axis_combo.addItem(f"Axis {axis}")
    
    def select_brake_axis(self, index):
        """Select a specific brake axis"""
        if index == 0:  # Auto-detect
            self.brake_axis = -1
            self.logger.info("Brake axis: Auto-detect mode")
        else:
            self.brake_axis = index - 1
            self.logger.info(f"Selected brake axis: {self.brake_axis}")
    
    def update_reduction_percentage(self, value):
        """Update emergency brake pressure drop percentage"""
        percentage = value / 10.0
        self.threshold_assist.set_lockup_reduction(percentage)
        self.reduction_label.setText(f"{percentage:.1f}%")
        self.logger.info(f"Emergency pressure drop set to {percentage:.1f}%")
    
    def toggle_assist(self, state):
        """Toggle threshold assist"""
        enabled = state == Qt.Checked
        self.threshold_assist.set_enabled(enabled)
        self.logger.info(f"Threshold assist {'enabled' if enabled else 'disabled'}")
    
    def reset_learning(self):
        """Reset ABS learning data"""
        # Reset active reductions for current track/car context
        context = f"{self.current_track}_{self.current_car}"
        self.threshold_assist.reset_reductions(context)
        
        # Reset ABS state machine
        if hasattr(self.threshold_assist, 'abs_state'):
            self.threshold_assist.abs_state = "READY"
            
        self.logger.info("🔄 NEW ABS system reset - ready for lockup detection")
    
# REMOVED: Manual lockup detection - drivers need to focus on driving!
    
    def toggle_iracing_connection(self):
        """Toggle iRacing connection"""
        if not self.iracing_connected:
            try:
                # Use the correct method name: connect() not start_connection()
                result = self.iracing_api.connect()
                if result:
                    self.iracing_connected = True
                    self.iracing_status_label.setText("✅ Connected")
                    self.iracing_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                    self.connect_button.setText("Disconnect from iRacing")
                    self.connect_button.setStyleSheet("""
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
                        QPushButton:pressed {
                            background-color: #a93226;
                        }
                    """)
                    
                    # Register telemetry callback for both data storage and automatic lockup detection
                    self.iracing_api.register_on_telemetry_data(self.on_telemetry_update)
                    
                    # Force start the telemetry monitoring (since we're not using the monitor thread)
                    self.force_start_telemetry_monitoring()
                    
                    self.logger.info("✅ Connected to iRacing!")
                    self.logger.info("🔍 Automatic lockup detection enabled")
                else:
                    self.logger.error("❌ Failed to connect to iRacing")
            except Exception as e:
                self.logger.error(f"❌ iRacing connection error: {e}")
        else:
            # Disconnect
            try:
                self.iracing_api.disconnect()
                self.iracing_connected = False
                self.iracing_status_label.setText("❌ Disconnected")
                self.iracing_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.connect_button.setText("Connect to iRacing")
                self.connect_button.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #229954;
                    }
                    QPushButton:pressed {
                        background-color: #1e8449;
                    }
                """)
                self.logger.info("🔌 Disconnected from iRacing")
            except Exception as e:
                self.logger.error(f"❌ Disconnect error: {e}")
    
    def force_start_telemetry_monitoring(self):
        """Force start telemetry monitoring without waiting for monitor thread"""
        try:
            import irsdk
            
            # Manually set connection state
            self.iracing_api._is_connected = True
            self.iracing_api.state.ir_connected = True
            
            # Initialize irsdk connection
            if not hasattr(self.iracing_api, 'ir') or not self.iracing_api.ir:
                self.iracing_api.ir = irsdk.IRSDK()
            
            # Start irsdk
            startup_result = self.iracing_api.ir.startup()
            self.logger.info(f"iRacing startup result: {startup_result}")
            
            if startup_result:
                # Set up a dummy telemetry saver to ensure callbacks are triggered
                self.setup_dummy_telemetry_saver()
                
                # Start telemetry timer
                self.iracing_api._start_telemetry_timer()
                self.logger.info("🚀 Telemetry monitoring force-started!")
                return True
            else:
                self.logger.error("❌ Failed to start iRacing - is iRacing running?")
                self.iracing_api._is_connected = False
                self.iracing_api.state.ir_connected = False
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error force-starting telemetry: {e}")
            self.iracing_api._is_connected = False
            self.iracing_api.state.ir_connected = False
            return False
    
    def setup_dummy_telemetry_saver(self):
        """Set up a minimal telemetry saver to ensure callbacks are triggered"""
        class DummyTelemetrySaver:
            def process_telemetry(self, telemetry):
                # Return minimal lap info to trigger callbacks
                return (False, 0, 0.0)  # is_new_lap, lap_number, lap_time
        
        self.iracing_api.telemetry_saver = DummyTelemetrySaver()
        self.logger.info("📡 Dummy telemetry saver set up to enable callbacks")
    
    def on_telemetry_update(self, telemetry):
        """Callback method to receive telemetry updates from iRacing"""
        # Debug: Log that we received telemetry (occasionally)
        if not hasattr(self, '_callback_count'):
            self._callback_count = 0
        self._callback_count += 1
        
        if self._callback_count % 300 == 1:  # Log every ~5 seconds
            brake = telemetry.get('Brake', 'N/A')
            speed = telemetry.get('Speed', 'N/A')
            abs_active = telemetry.get('BrakeABSactive', 'N/A')
            long_accel = telemetry.get('LongAccel', 'N/A')
            self.logger.info(f"📡 CALLBACK #{self._callback_count}: Brake={brake}, Speed={speed}, ABS={abs_active}, LongAccel={long_accel}")
        
        # Store the latest telemetry data
        self.latest_telemetry = telemetry.copy()
        self._last_telemetry_time = time.time()  # Track when we last received telemetry
        
        # Update track/car info if available  
        track = telemetry.get('track_name', self.current_track)
        car = telemetry.get('car_name', self.current_car)
        
        if track != "Unknown" and track != self.current_track:
            self.current_track = track
            self.track_label.setText(track)
            self.track_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.logger.info(f"🏁 Track: {track}")
            
            # Update threshold assist context
            self.threshold_assist.set_track_car_context(track, car)
        
        if car != "Unknown" and car != self.current_car:
            self.current_car = car
            self.car_label.setText(car)
            self.car_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.logger.info(f"🏎️ Car: {car}")
            
            # Detect and display ABS availability
            has_abs = self.detect_abs_availability(car)
            if has_abs:
                self.abs_available_label.setText("✅ YES")
                self.abs_available_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.logger.info("✅ Car has ABS - automatic detection enabled")
            else:
                self.abs_available_label.setText("❌ NO")
                self.abs_available_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.logger.info("❌ Car has no ABS - using physics-based detection")
            
            # Update threshold assist context
            self.threshold_assist.set_track_car_context(track, car)
        
        # Call automatic lockup detection
        self.detect_automatic_lockup(telemetry)
    
    def detect_automatic_lockup(self, telemetry):
        """Automatic lockup detection using physics analysis"""
        try:
            current_time = time.time()
            
            # Get current telemetry values
            brake_input = telemetry.get('Brake', 0.0)
            speed = telemetry.get('Speed', 0.0)
            long_accel = telemetry.get('LongAccel', 0.0)
            abs_active = telemetry.get('BrakeABSactive', False)
            
            # Debug logging every 60 calls when braking
            if not hasattr(self, '_lockup_debug_count'):
                self._lockup_debug_count = 0
            self._lockup_debug_count += 1
            
            if brake_input > 0.1 and self._lockup_debug_count % 60 == 1:
                self.logger.info(f"🔍 LOCKUP DEBUG: brake={brake_input:.3f}, speed={speed:.1f}, abs={abs_active}, accel={long_accel:.1f}")
            
            # Only analyze when actively braking
            if brake_input < 0.1:
                # Reset analysis data when not braking
                if hasattr(self, '_brake_analysis_data'):
                    delattr(self, '_brake_analysis_data')
                return
            
            # Initialize analysis data structure
            if not hasattr(self, '_brake_analysis_data'):
                self._brake_analysis_data = {
                    'start_time': current_time,
                    'start_speed': speed,
                    'start_brake': brake_input,
                    'speed_history': [],
                    'brake_history': [],
                    'accel_history': [],
                    'lockup_detected': False,
                    'last_efficiency_check': 0.0
                }
            
            data = self._brake_analysis_data
            
            # Add current data to history (keep last 30 samples ~0.5 seconds)
            data['speed_history'].append((current_time, speed))
            data['brake_history'].append((current_time, brake_input))
            data['accel_history'].append((current_time, long_accel))
            
            # Keep only recent history
            cutoff_time = current_time - 0.5
            data['speed_history'] = [(t, v) for t, v in data['speed_history'] if t > cutoff_time]
            data['brake_history'] = [(t, v) for t, v in data['brake_history'] if t > cutoff_time]
            data['accel_history'] = [(t, v) for t, v in data['accel_history'] if t > cutoff_time]
            
            # Method 1: ABS activation (most reliable)
            if abs_active and not data['lockup_detected']:
                self.logger.info(f"🚨 ABS LOCKUP DETECTED: brake={brake_input:.3f}, speed={speed:.1f}")
                # REMOVED: manual_lockup_detected - system is now fully automatic
                data['lockup_detected'] = True
                return
            
            # Debug: Log ABS status occasionally when braking
            if brake_input > 0.5 and self._lockup_debug_count % 120 == 1:
                self.logger.info(f"🔍 ABS STATUS: active={abs_active}, brake={brake_input:.3f}")
            
            # Method 2: Excessive deceleration analysis (for non-ABS cars)
            if len(data['accel_history']) >= 10 and current_time - data['last_efficiency_check'] > 0.1:
                data['last_efficiency_check'] = current_time
                
                # Calculate average deceleration over recent history
                recent_accels = [acc for _, acc in data['accel_history'][-10:]]
                avg_decel = sum(recent_accels) / len(recent_accels)
                
                # Detect excessive deceleration (lockup threshold)
                # Normal max deceleration is around -1.0 to -1.2g (-9.8 to -11.8 m/s²)
                # Make it more sensitive: lockup often beyond -1.1g (-10.8 m/s²)
                excessive_decel_threshold = -10.8  # m/s² (more sensitive)
                
                # Debug: Log deceleration occasionally
                if brake_input > 0.5 and self._lockup_debug_count % 180 == 1:
                    self.logger.info(f"🔍 DECEL: {avg_decel:.1f} m/s² (threshold: {excessive_decel_threshold})")
                
                if avg_decel < excessive_decel_threshold and not data['lockup_detected']:
                    self.logger.info(f"🚨 DECEL LOCKUP DETECTED: {avg_decel:.1f} m/s² at brake={brake_input:.3f}")
                    # REMOVED: manual_lockup_detected - system is now fully automatic
                    data['lockup_detected'] = True
                    return
                
                # Method 3: Brake efficiency analysis
                if len(data['brake_history']) >= 10 and len(data['speed_history']) >= 10:
                    # Calculate brake efficiency: deceleration per unit brake input
                    time_span = data['accel_history'][-1][0] - data['accel_history'][-10][0]
                    if time_span > 0.05:  # At least 50ms of data
                        avg_brake = sum(brake for _, brake in data['brake_history'][-10:]) / 10
                        brake_efficiency = abs(avg_decel) / max(avg_brake, 0.1)
                        
                        # Store efficiency for comparison
                        if not hasattr(self, '_efficiency_baseline'):
                            self._efficiency_baseline = brake_efficiency
                            self._efficiency_samples = [brake_efficiency]
                        else:
                            self._efficiency_samples.append(brake_efficiency)
                            # Keep rolling average of efficiency
                            if len(self._efficiency_samples) > 20:
                                self._efficiency_samples = self._efficiency_samples[-20:]
                            
                            baseline_efficiency = sum(self._efficiency_samples[:-5]) / max(len(self._efficiency_samples[:-5]), 1)
                            
                            # Detect significant efficiency drop (lockup indication)
                            efficiency_drop_threshold = 0.3  # 30% drop in efficiency
                            if baseline_efficiency > 0 and brake_efficiency < baseline_efficiency * (1 - efficiency_drop_threshold):
                                if not data['lockup_detected'] and avg_brake > 0.3:  # Only when braking hard
                                    self.logger.info(f"🚨 LOCKUP DETECTED: Brake efficiency drop {brake_efficiency:.2f} vs {baseline_efficiency:.2f}!")
                                    # REMOVED: manual_lockup_detected - system is now fully automatic
                                    data['lockup_detected'] = True
                                    return
                
        except Exception as e:
            self.logger.error(f"Error in automatic lockup detection: {e}")
    
    def update_iracing_connection(self):
        """Update iRacing connection status"""
        # Connection status and track/car info is now handled by telemetry callback
        # This method just ensures we maintain connection state
        if self.iracing_connected:
            # Check if we're still getting telemetry updates
            if not hasattr(self, '_last_telemetry_time'):
                self._last_telemetry_time = time.time()
            
            # If no telemetry for 5 seconds, log a warning
            if time.time() - self._last_telemetry_time > 5.0:
                if not hasattr(self, '_no_telemetry_logged'):
                    callback_count = getattr(self, '_callback_count', 0)
                    self.logger.warning(f"⚠️ No telemetry updates received (callbacks: {callback_count}) - check iRacing connection")
                    self._no_telemetry_logged = True
            elif hasattr(self, '_no_telemetry_logged'):
                # Clear the flag if we're getting telemetry again
                delattr(self, '_no_telemetry_logged')
    
    def detect_abs_availability(self, car_name):
        """Detect if car has ABS based on car name (heuristic)"""
        if not car_name or car_name == "Unknown":
            return False  # Default to no ABS for unknown cars
        car_lower = car_name.lower()
        
        # Modern GT cars, touring cars, and prototypes typically have ABS
        abs_indicators = [
            'gt3', 'gte', 'gtd', 'lmp', 'dpi', 'prototype',
            'touring', 'btcc', 'wtcr', 'tcr',
            'mercedes', 'bmw', 'audi', 'porsche', 'ferrari', 'lamborghini',
            'acura', 'cadillac', 'ford gt', 'corvette c8'
        ]
        
        # Classic cars, open wheel, and NASCAR typically don't have ABS
        no_abs_indicators = [
            'f1', 'formula', 'indycar', 'indy',
            'nascar', 'cup series', 'xfinity', 'truck',
            'skip barber', 'formula vee', 'pro mazda',
            'dirt', 'sprint car', 'late model',
            'legends', 'street stock'
        ]
        
        # Check for no-ABS indicators first (more specific)
        for indicator in no_abs_indicators:
            if indicator in car_lower:
                return False
        
        # Then check for ABS indicators
        for indicator in abs_indicators:
            if indicator in car_lower:
                return True
        
        # Default assumption for unknown cars
        return False

def main():
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 5px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLabel {
            color: #ffffff;
        }
        QPushButton {
            background-color: #404040;
            border: 1px solid #666666;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #303030;
        }
        QCheckBox {
            color: #ffffff;
        }
        QSlider::groove:horizontal {
            border: 1px solid #666666;
            height: 8px;
            background: #404040;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #888888;
            border: 1px solid #666666;
            width: 18px;
            border-radius: 9px;
        }
        QComboBox {
            background-color: #404040;
            border: 1px solid #666666;
            padding: 3px;
            border-radius: 3px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
    """)
    
    window = SimpleBrakeTester()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 