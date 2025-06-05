#!/usr/bin/env python3
"""
Xbox Controller Brake Threshold Visual Tester

Real-time visual testing of threshold braking assist system using Xbox controller.
Shows live brake input, lockup detection, and threshold intervention.
"""

import sys
import os
import time
import math
import logging
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

# Add the trackpro module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pygame
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QLabel, QSlider, QCheckBox, 
                           QProgressBar, QTextEdit, QGroupBox, QGridLayout, QSpinBox, QComboBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor

from trackpro.pedals.threshold_braking_assist import RealTimeBrakingAssist

@dataclass
class BrakeDataPoint:
    """Single data point for brake input visualization"""
    timestamp: float
    raw_brake: float
    assisted_brake: float
    abs_active: bool
    assist_active: bool

class BrakeVisualizationWidget(QWidget):
    """Custom widget for visualizing brake input over time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 300)
        
        # Data storage (last 10 seconds at 60fps = 600 points)
        self.data_points: deque = deque(maxlen=600)
        self.current_brake = 0.0
        self.current_assisted = 0.0
        self.current_abs = False
        self.current_assist = False
        
        # Visual settings
        self.bg_color = QColor(20, 20, 30)
        self.grid_color = QColor(60, 60, 80)
        self.brake_color = QColor(255, 100, 100)  # Red for raw brake
        self.assist_color = QColor(100, 255, 100)  # Green for assisted brake  
        self.abs_color = QColor(255, 255, 0)      # Yellow for ABS
        self.threshold_color = QColor(255, 165, 0)  # Orange for threshold line
        
    def add_data_point(self, raw_brake: float, assisted_brake: float, 
                      abs_active: bool, assist_active: bool):
        """Add a new data point to the visualization"""
        self.data_points.append(BrakeDataPoint(
            timestamp=time.time(),
            raw_brake=raw_brake,
            assisted_brake=assisted_brake,
            abs_active=abs_active,
            assist_active=assist_active
        ))
        
        self.current_brake = raw_brake
        self.current_assisted = assisted_brake
        self.current_abs = abs_active
        self.current_assist = assist_active
        
        self.update()
    
    def paintEvent(self, event):
        """Paint the brake visualization"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.bg_color)
        
        if not self.data_points:
            # Draw empty state
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, "Waiting for brake input...")
            return
        
        width = self.width()
        height = self.height()
        margin = 40
        
        # Draw grid
        self._draw_grid(painter, width, height, margin)
        
        # Draw brake data
        self._draw_brake_data(painter, width, height, margin)
        
        # Draw current status
        self._draw_current_status(painter, width, height, margin)
        
        # Draw legend
        self._draw_legend(painter, width, height)
    
    def _draw_grid(self, painter, width, height, margin):
        """Draw background grid"""
        painter.setPen(QPen(self.grid_color, 1))
        
        # Horizontal lines (brake percentage)
        for i in range(0, 101, 20):
            y = int(height - margin - (i / 100.0) * (height - 2 * margin))
            painter.drawLine(margin, y, width - margin, y)
            
            # Labels
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(5, y + 5, f"{i}%")
            painter.setPen(QPen(self.grid_color, 1))
        
        # Vertical lines (time)
        num_vertical_lines = 10
        for i in range(num_vertical_lines + 1):
            x = int(margin + (i / num_vertical_lines) * (width - 2 * margin))
            painter.drawLine(x, margin, x, height - margin)
    
    def _draw_brake_data(self, painter, width, height, margin):
        """Draw the brake input data over time"""
        if len(self.data_points) < 2:
            return
        
        # Calculate time range
        current_time = time.time()
        time_window = 10.0  # Show last 10 seconds
        
        # Convert data points to screen coordinates
        raw_points = []
        assisted_points = []
        abs_markers = []
        assist_markers = []
        
        for point in self.data_points:
            # Calculate x position (time)
            time_offset = current_time - point.timestamp
            if time_offset > time_window:
                continue
                
            x = int(width - margin - (time_offset / time_window) * (width - 2 * margin))
            
            # Calculate y positions (brake values)
            raw_y = int(height - margin - point.raw_brake * (height - 2 * margin))
            assisted_y = int(height - margin - point.assisted_brake * (height - 2 * margin))
            
            raw_points.append((x, raw_y))
            assisted_points.append((x, assisted_y))
            
            # Mark ABS and assist events
            if point.abs_active:
                abs_markers.append((x, raw_y))
            if point.assist_active:
                assist_markers.append((x, assisted_y))
        
        # Draw raw brake line
        if len(raw_points) > 1:
            painter.setPen(QPen(self.brake_color, 2))
            for i in range(len(raw_points) - 1):
                painter.drawLine(raw_points[i][0], raw_points[i][1],
                               raw_points[i+1][0], raw_points[i+1][1])
        
        # Draw assisted brake line
        if len(assisted_points) > 1:
            painter.setPen(QPen(self.assist_color, 2))
            for i in range(len(assisted_points) - 1):
                painter.drawLine(assisted_points[i][0], assisted_points[i][1],
                               assisted_points[i+1][0], assisted_points[i+1][1])
        
        # Draw ABS markers
        painter.setPen(QPen(self.abs_color, 3))
        painter.setBrush(QBrush(self.abs_color))
        for x, y in abs_markers:
            painter.drawEllipse(int(x - 4), int(y - 4), 8, 8)
        
        # Draw assist intervention markers
        painter.setPen(QPen(self.assist_color, 2))
        painter.setBrush(QBrush(self.assist_color))
        for x, y in assist_markers:
            painter.drawRect(int(x - 3), int(y - 3), 6, 6)
    
    def _draw_current_status(self, painter, width, height, margin):
        """Draw current brake status indicators"""
        # Current brake value bar
        bar_width = 30
        bar_height = height - 2 * margin
        bar_x = width - margin - bar_width - 10
        
        # Background
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(bar_x, margin, bar_width, bar_height)
        
        # Raw brake level
        raw_fill_height = int(self.current_brake * bar_height)
        painter.setBrush(QBrush(self.brake_color))
        painter.drawRect(bar_x, int(height - margin - raw_fill_height), 
                        bar_width // 2, raw_fill_height)
        
        # Assisted brake level
        assisted_fill_height = int(self.current_assisted * bar_height)
        painter.setBrush(QBrush(self.assist_color))
        painter.drawRect(bar_x + bar_width // 2, int(height - margin - assisted_fill_height),
                        bar_width // 2, assisted_fill_height)
        
        # Status indicators
        status_y = margin - 20
        if self.current_abs:
            painter.setPen(QPen(self.abs_color, 2))
            painter.drawText(bar_x - 100, status_y, "🚨 ABS ACTIVE")
        
        if self.current_assist:
            painter.setPen(QPen(self.assist_color, 2))
            painter.drawText(bar_x - 200, status_y, "🎯 ASSIST ACTIVE")
    
    def _draw_legend(self, painter, width, height):
        """Draw the legend"""
        legend_x = 10
        legend_y = height - 120
        
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setFont(QFont("Arial", 9))
        
        # Legend items
        items = [
            (self.brake_color, "Raw Brake Input"),
            (self.assist_color, "Assisted Brake Output"), 
            (self.abs_color, "● ABS Lockup"),
            (QColor(255, 255, 255), "□ Assist Intervention")
        ]
        
        for i, (color, text) in enumerate(items):
            y = legend_y + i * 20
            painter.setPen(QPen(color, 2))
            painter.drawLine(legend_x, y, legend_x + 20, y)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(legend_x + 30, y + 5, text)

class XboxThresholdTester(QMainWindow):
    """Main window for Xbox controller threshold testing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xbox Controller Brake Threshold Tester")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize Xbox controller
        self.init_xbox_controller()
        
        # Initialize NEW ABS-style threshold assist
        self.threshold_assist = RealTimeBrakingAssist(
            lockup_reduction=18.0,  # 18% emergency drop
            recovery_rate=2.0       # Not used in new system but required for compatibility
        )
        self.threshold_assist.set_enabled(True)
        self.threshold_assist.set_track_car_context("Test_Track", "Xbox_Controller")
        
        # Simulation settings
        self.abs_threshold = 0.85  # Simulate ABS above 85%
        self.lockup_detected = False
        
        # Setup UI
        self.setup_ui()
        
        # Start update timer (60 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(16)  # ~60 FPS
        
        # Logging
        self.setup_logging()
        
    def init_xbox_controller(self):
        """Initialize Xbox controller with pygame"""
        pygame.init()
        pygame.joystick.init()
        
        self.joystick = None
        self.controller_list = []
        
        # Detect all available controllers
        num_controllers = pygame.joystick.get_count()
        print(f"Found {num_controllers} controller(s):")
        
        for i in range(num_controllers):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            controller_name = joystick.get_name().lower()
            print(f"  {i}: {joystick.get_name()}")
            self.controller_list.append((i, joystick.get_name(), joystick))
            
            # Try to find a real Xbox controller (not vJoy)
            if any(keyword in controller_name for keyword in ['xbox', 'controller', 'gamepad']) and 'vjoy' not in controller_name:
                self.joystick = joystick
                print(f"Selected Xbox controller: {joystick.get_name()}")
                break
        
        # If no Xbox controller found, use the first non-vJoy controller
        if not self.joystick and self.controller_list:
            for i, name, joystick in self.controller_list:
                if 'vjoy' not in name.lower():
                    self.joystick = joystick
                    print(f"Selected controller: {name}")
                    break
        
        # Fallback to first controller if still nothing
        if not self.joystick and self.controller_list:
            self.joystick = self.controller_list[0][2]
            print(f"Fallback to: {self.controller_list[0][1]}")
        
        if not self.joystick:
            print("No Xbox controller found - using simulation mode")
        else:
            # Print controller info
            print(f"Controller axes: {self.joystick.get_numaxes()}")
            print(f"Controller buttons: {self.joystick.get_numbuttons()}")
            print(f"Controller hats: {self.joystick.get_numhats()}")
            
            # Test all axes to find the right one
            print("Testing controller axes...")
            pygame.event.pump()
            for axis in range(self.joystick.get_numaxes()):
                value = self.joystick.get_axis(axis)
                print(f"  Axis {axis}: {value:.3f}")
                
        self.selected_controller_index = 0 if self.joystick else -1
            
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Xbox Controller Brake Threshold Tester")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Main visualization
        self.brake_viz = BrakeVisualizationWidget()
        layout.addWidget(self.brake_viz)
        
        # Controls section
        controls_layout = QHBoxLayout()
        
        # Left controls
        left_controls = self.create_control_panel()
        controls_layout.addWidget(left_controls)
        
        # Status display
        status_controls = self.create_status_panel()
        controls_layout.addWidget(status_controls)
        
        # Right controls  
        right_controls = self.create_settings_panel()
        controls_layout.addWidget(right_controls)
        
        layout.addLayout(controls_layout)
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: monospace;")
        layout.addWidget(self.log_output)
    
    def create_control_panel(self):
        """Create the main control panel"""
        group = QGroupBox("Controls")
        layout = QVBoxLayout(group)
        
        # Enable/disable assist
        self.assist_enabled = QCheckBox("Threshold Assist Enabled")
        self.assist_enabled.setChecked(True)
        self.assist_enabled.stateChanged.connect(self.toggle_assist)
        layout.addWidget(self.assist_enabled)
        
        # Reset learning
        reset_btn = QPushButton("Reset Learning Data")
        reset_btn.clicked.connect(self.reset_learning)
        layout.addWidget(reset_btn)
        
        # Test sequence
        test_btn = QPushButton("Run Test Sequence")
        test_btn.clicked.connect(self.run_test_sequence)
        layout.addWidget(test_btn)
        
        return group
    
    def create_status_panel(self):
        """Create the status display panel"""
        group = QGroupBox("Status")
        layout = QGridLayout(group)
        
        # Current values
        layout.addWidget(QLabel("Raw Brake:"), 0, 0)
        self.raw_brake_label = QLabel("0.000")
        self.raw_brake_label.setStyleSheet("color: #ff6464; font-weight: bold;")
        layout.addWidget(self.raw_brake_label, 0, 1)
        
        layout.addWidget(QLabel("Assisted Brake:"), 1, 0)
        self.assisted_brake_label = QLabel("0.000")
        self.assisted_brake_label.setStyleSheet("color: #64ff64; font-weight: bold;")
        layout.addWidget(self.assisted_brake_label, 1, 1)
        
        layout.addWidget(QLabel("ABS State:"), 2, 0)
        self.abs_state_label = QLabel("READY")
        self.abs_state_label.setStyleSheet("color: #64ff64; font-weight: bold;")
        layout.addWidget(self.abs_state_label, 2, 1)
        
        layout.addWidget(QLabel("Lockup Pressure:"), 3, 0)
        self.lockup_pressure_label = QLabel("0.000")
        layout.addWidget(self.lockup_pressure_label, 3, 1)
        
        layout.addWidget(QLabel("Target Threshold:"), 4, 0)
        self.threshold_label = QLabel("0.000")
        layout.addWidget(self.threshold_label, 4, 1)
        
        layout.addWidget(QLabel("Efficiency:"), 5, 0)
        self.efficiency_label = QLabel("0.0%")
        layout.addWidget(self.efficiency_label, 5, 1)
        
        layout.addWidget(QLabel("Consecutive Lockups:"), 6, 0)
        self.lockups_label = QLabel("0")
        layout.addWidget(self.lockups_label, 6, 1)
        
        return group
    
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
                display_name += " (vJoy - Skip)"
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
        layout.addWidget(QLabel("Reduction %:"), 2, 0)
        self.reduction_slider = QSlider(Qt.Horizontal)
        self.reduction_slider.setRange(1, 10)
        self.reduction_slider.setValue(3)
        self.reduction_slider.valueChanged.connect(self.update_reduction)
        layout.addWidget(self.reduction_slider, 2, 1)
        
        self.reduction_label = QLabel("3%")
        layout.addWidget(self.reduction_label, 2, 2)
        
        # ABS simulation threshold
        layout.addWidget(QLabel("ABS Threshold:"), 3, 0)
        self.abs_slider = QSlider(Qt.Horizontal)
        self.abs_slider.setRange(70, 95)
        self.abs_slider.setValue(85)
        self.abs_slider.valueChanged.connect(self.update_abs_threshold)
        layout.addWidget(self.abs_slider, 3, 1)
        
        self.abs_label = QLabel("85%")
        layout.addWidget(self.abs_label, 3, 2)
        
        # Live axis values for debugging
        layout.addWidget(QLabel("Live Values:"), 4, 0)
        self.live_values_label = QLabel("No controller")
        self.live_values_label.setStyleSheet("color: #888888; font-size: 9px; font-family: monospace;")
        layout.addWidget(self.live_values_label, 4, 1, 1, 2)
        
        # Initialize brake axis
        self.brake_axis = -1  # -1 means auto-detect
        
        return group
    
    def setup_logging(self):
        """Setup logging to display in the UI"""
        # Create a custom handler to redirect logs to the UI
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
        logger = logging.getLogger("ThresholdAssist")
        logger.setLevel(logging.INFO)
        
        handler = UILogHandler(self.log_output)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        self.logger = logger
    
    def get_xbox_brake_input(self) -> float:
        """Get brake input from Xbox controller or simulate"""
        if self.joystick:
            pygame.event.pump()
            
            try:
                # Use the selected axis for brake input
                if hasattr(self, 'brake_axis') and self.brake_axis >= 0:
                    raw_value = self.joystick.get_axis(self.brake_axis)
                    
                    # Handle different trigger types
                    if self.brake_axis in [4, 5]:  # Trigger axes (usually -1 to 1, neutral at -1)
                        brake_raw = (raw_value + 1.0) / 2.0
                    else:  # Regular axes (-1 to 1, neutral at 0)
                        brake_raw = max(0.0, abs(raw_value))
                    
                    return max(0.0, min(1.0, brake_raw))
                
                # Auto-detect brake input from common Xbox controller axes
                brake_raw = 0.0
                
                # Try different common Xbox controller mappings
                num_axes = self.joystick.get_numaxes()
                
                if num_axes > 5:
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
                
                return max(0.0, min(1.0, brake_raw))
                
            except Exception as e:
                self.logger.warning(f"Error reading controller: {e}")
                return 0.0
        else:
            # Simulate brake input with sine wave for testing
            return max(0.0, math.sin(time.time() * 0.5) * 0.9)
    
    def simulate_abs_detection(self, brake_value: float) -> bool:
        """Simulate ABS activation based on brake value"""
        return brake_value > self.abs_threshold
    
    def update_data(self):
        """Update brake data and visualization with NEW ABS system"""
        # Get brake input
        raw_brake = self.get_xbox_brake_input()
        
        # Simulate telemetry with enhanced physics for the new ABS system
        abs_active = self.simulate_abs_detection(raw_brake)
        speed_kmh = 80.0  # Simulate 80 km/h
        speed_ms = speed_kmh / 3.6  # Convert to m/s
        
        # Simulate deceleration - more realistic for new system
        if raw_brake > 0.8:
            long_accel = -12.0 if abs_active else -9.0  # Heavy decel when locking
        elif raw_brake > 0.5:
            long_accel = -8.0
        else:
            long_accel = -4.0 * raw_brake
        
        telemetry = {
            'BrakeABSactive': abs_active,
            'Brake': raw_brake,
            'Speed': speed_ms,  # m/s for new system
            'LongAccel': long_accel,  # m/s² for lockup detection
            'RPM': 6500
        }
        
        # Process with NEW ABS-style threshold assist
        assisted_brake = self.threshold_assist.apply_assist(raw_brake, telemetry)
        
        # Check if assist is active
        assist_active = abs(assisted_brake - raw_brake) > 0.001
        
        # Update visualization
        self.brake_viz.add_data_point(raw_brake, assisted_brake, abs_active, assist_active)
        
        # Update status labels
        self.raw_brake_label.setText(f"{raw_brake:.3f}")
        self.assisted_brake_label.setText(f"{assisted_brake:.3f}")
        
        # Update NEW ABS status information
        status = self.threshold_assist.get_status()
        
        # ABS State with color coding
        abs_state = status.get('abs_state', 'READY')
        self.abs_state_label.setText(abs_state)
        
        # Color code the ABS state
        if abs_state == "READY":
            self.abs_state_label.setStyleSheet("color: #64ff64; font-weight: bold;")  # Green
        elif abs_state == "LOCKUP_DETECTED":
            self.abs_state_label.setStyleSheet("color: #ff6464; font-weight: bold;")  # Red
        elif abs_state == "PRESSURE_DROP":
            self.abs_state_label.setStyleSheet("color: #ffff64; font-weight: bold;")  # Yellow
        elif abs_state == "RECOVERY":
            self.abs_state_label.setStyleSheet("color: #64ffff; font-weight: bold;")  # Cyan
        elif abs_state == "THRESHOLD_MAINTAIN":
            self.abs_state_label.setStyleSheet("color: #ff64ff; font-weight: bold;")  # Magenta
        
        # Update other status fields
        self.lockup_pressure_label.setText(f"{status.get('lockup_pressure', 0.0):.3f}")
        self.threshold_label.setText(f"{status.get('target_threshold', 0.0):.3f}")
        self.efficiency_label.setText(f"{status.get('threshold_efficiency', 0.0):.1f}%")
        self.lockups_label.setText(str(status.get('consecutive_lockups', 0)))
        
        # Update live axis values for debugging
        if self.joystick:
            pygame.event.pump()
            try:
                axis_values = []
                for axis in range(min(6, self.joystick.get_numaxes())):  # Show first 6 axes
                    value = self.joystick.get_axis(axis)
                    axis_values.append(f"A{axis}:{value:+.2f}")
                
                live_text = " | ".join(axis_values)
                if hasattr(self, 'brake_axis') and self.brake_axis >= 0:
                    live_text += f" | Brake(A{self.brake_axis}):{raw_brake:.3f}"
                else:
                    live_text += f" | Brake(auto):{raw_brake:.3f}"
                    
                if hasattr(self, 'live_values_label'):
                    self.live_values_label.setText(live_text)
            except Exception as e:
                if hasattr(self, 'live_values_label'):
                    self.live_values_label.setText(f"Error: {e}")
        else:
            if hasattr(self, 'live_values_label'):
                self.live_values_label.setText("No controller - using simulation")
        
        # Log significant ABS events
        if abs_active and not self.lockup_detected:
            self.logger.info(f"🚨 ABS LOCKUP detected at brake={raw_brake:.3f} | State: {abs_state}")
            self.lockup_detected = True
        elif not abs_active:
            self.lockup_detected = False
            
        if assist_active:
            reduction = (raw_brake - assisted_brake) / raw_brake * 100 if raw_brake > 0 else 0
            self.logger.info(f"🎯 NEW ABS: {raw_brake:.3f} -> {assisted_brake:.3f} (-{reduction:.1f}%) | {abs_state}")
    
    def toggle_assist(self, state):
        """Toggle threshold assist on/off"""
        enabled = state == Qt.Checked
        self.threshold_assist.set_enabled(enabled)
        self.logger.info(f"Threshold assist {'ENABLED' if enabled else 'DISABLED'}")
    
    def reset_learning(self):
        """Reset ABS learning data"""
        self.threshold_assist.reset_reductions()  # Reset active reductions
        # Reset any stored ABS state
        if hasattr(self.threshold_assist, 'abs_state'):
            self.threshold_assist.abs_state = "READY"
        self.logger.info("🔄 ABS system reset - ready for new lockup detection")
    
    def update_reduction(self, value):
        """Update emergency pressure drop percentage"""
        self.threshold_assist.set_lockup_reduction(value)
        if hasattr(self, 'reduction_label'):
            self.reduction_label.setText(f"{value}%")
        self.logger.info(f"Emergency pressure drop set to {value}%")
    
    def update_abs_threshold(self, value):
        """Update ABS simulation threshold"""
        self.abs_threshold = value / 100.0
        self.abs_label.setText(f"{value}%")
        self.logger.info(f"ABS threshold set to {value}%")
    
    def select_controller(self, index):
        """Select a specific controller"""
        if index == 0:  # Auto-detect
            self.init_xbox_controller()
            self.logger.info("Controller selection: Auto-detect mode")
        else:
            # Manual selection
            controller_index = index - 1
            if controller_index < len(self.controller_list):
                i, name, joystick = self.controller_list[controller_index]
                self.joystick = joystick
                self.selected_controller_index = i
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
            # Manual selection
            self.brake_axis = index - 1
            self.logger.info(f"Selected brake axis: {self.brake_axis}")
    
    def run_test_sequence(self):
        """Run automated test sequence"""
        self.logger.info("🤖 Starting automated test sequence...")
        # This could be expanded to run predefined brake patterns
        self.logger.info("Manual testing - apply brake pressure and watch for lockup detection!")

def main():
    """Main function"""
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QGroupBox {
            background-color: #3c3c3c;
            border: 2px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #4c4c4c;
            border: 1px solid #666666;
            padding: 8px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #5c5c5c;
        }
        QPushButton:pressed {
            background-color: #3c3c3c;
        }
        QLabel {
            color: #ffffff;
        }
        QCheckBox {
            color: #ffffff;
        }
    """)
    
    window = XboxThresholdTester()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 