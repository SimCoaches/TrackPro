from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QGroupBox, QButtonGroup, QRadioButton,
    QProgressBar, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt, QTimer
import pygame
import logging

logger = logging.getLogger(__name__)

class CalibrationWizard(QDialog):
    """Calibration wizard dialog for all pedals."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Pedal Calibration Wizard")
        self.setMinimumSize(600, 400)
        
        # Set up dark theme
        self.setup_dark_theme()
        
        # Initialize results dictionary
        self.results = {
            'throttle': {'min': 0, 'max': 65535},
            'brake': {'min': 0, 'max': 65535},
            'clutch': {'min': 0, 'max': 65535}
        }
        
        # Get hardware input from parent
        if hasattr(parent, 'hardware'):
            self.hardware = parent.hardware
        else:
            # For testing without parent
            from .hardware_input import HardwareInput
            self.hardware = HardwareInput()
        
        # Initialize axis movement history for better detection
        self.axis_movement_history = {}
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create stacked widget for wizard pages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Create wizard pages
        self.create_welcome_page()
        self.create_throttle_page()
        self.create_brake_page()
        self.create_clutch_page()
        self.create_finish_page()
        
        # Create navigation buttons
        button_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.go_next)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.next_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize timer for reading inputs
        self.input_timer = QTimer()
        self.input_timer.timeout.connect(self.update_inputs)
        self.input_timer.start(50)  # 20Hz update rate
        
        # Track current page and pedal being calibrated
        self.current_page = 0
        self.current_pedal = None
        self.calibration_stage = None
        
        # Track detected axis values
        self.detected_axes = {}
        self.axis_values = {}
        self.axis_min_values = {}
        self.axis_max_values = {}
        
        # Update UI
        self.update_navigation_buttons()

    def setup_dark_theme(self):
        """Set up dark theme for the dialog."""
        self.setStyleSheet("""
            QDialog {
                background-color: #353535;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #444444;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                color: white;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #777777;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 2px;
                text-align: center;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
            QRadioButton {
                color: #ffffff;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }
            QRadioButton::indicator:checked {
                background-color: #2a82da;
                border: 2px solid #ffffff;
                border-radius: 7px;
            }
            QRadioButton::indicator:unchecked {
                background-color: #353535;
                border: 2px solid #ffffff;
                border-radius: 7px;
            }
        """)

    def create_welcome_page(self):
        """Create the welcome page of the wizard."""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Title
        title = QLabel("Pedal Calibration Wizard")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        description = QLabel(
            "This wizard will guide you through calibrating your pedals.\n\n"
            "The process will detect which axis corresponds to each pedal and set the minimum and maximum values.\n\n"
            "For each pedal, you will be asked to:\n"
            "1. Press and release the pedal to detect which axis it uses\n"
            "2. Release the pedal completely to set the minimum value\n"
            "3. Press the pedal fully to set the maximum value\n\n"
            "Click 'Next' to begin calibrating the throttle pedal."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # Add page to stack
        self.stack.addWidget(page)

    def create_pedal_page(self, pedal_name):
        """Create a calibration page for a specific pedal."""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Title
        title = QLabel(f"{pedal_name.capitalize()} Pedal Calibration")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions label
        instructions = QLabel(f"Press the {pedal_name} pedal fully and then release it completely to detect which axis it uses.")
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        setattr(self, f"{pedal_name}_instructions", instructions)
        
        # Status label
        status = QLabel("Waiting for pedal movement...")
        status.setWordWrap(True)
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("font-weight: bold; color: #2a82da;")
        layout.addWidget(status)
        setattr(self, f"{pedal_name}_status", status)
        
        # Add a "Force Manual Selection" button at the top
        force_manual_btn = QPushButton("Skip Auto-Detection & Select Manually")
        force_manual_btn.clicked.connect(lambda: self.show_all_axes(pedal_name))
        force_manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        force_manual_btn.setToolTip("Skip automatic detection and manually select the axis")
        layout.addWidget(force_manual_btn)
        
        # Progress bar for current value
        progress = QProgressBar()
        progress.setRange(0, 65535)
        progress.setValue(0)
        layout.addWidget(progress)
        setattr(self, f"{pedal_name}_progress", progress)
        
        # Value label
        value_label = QLabel("Current Value: 0")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        setattr(self, f"{pedal_name}_value", value_label)
        
        # Min/Max labels
        min_max_layout = QHBoxLayout()
        
        min_label = QLabel("Min: 0")
        min_label.setAlignment(Qt.AlignCenter)
        min_max_layout.addWidget(min_label)
        setattr(self, f"{pedal_name}_min", min_label)
        
        max_label = QLabel("Max: 65535")
        max_label.setAlignment(Qt.AlignCenter)
        min_max_layout.addWidget(max_label)
        setattr(self, f"{pedal_name}_max", max_label)
        
        layout.addLayout(min_max_layout)
        
        # Axis selection group
        axis_group = QGroupBox("Detected Axis")
        axis_layout = QVBoxLayout(axis_group)
        
        # Add a label to explain manual selection
        manual_selection_label = QLabel("If automatic detection selects the wrong axis, manually select the correct one:")
        manual_selection_label.setWordWrap(True)
        axis_layout.addWidget(manual_selection_label)
        
        # Create radio buttons for axis selection - create a separate button group for each pedal
        axis_buttons = QButtonGroup()
        setattr(self, f"{pedal_name}_axis_buttons", axis_buttons)
        
        # Create a horizontal layout for axis buttons to display them in a grid
        axis_buttons_layout = QHBoxLayout()
        axis_grid = QVBoxLayout()
        current_row = QHBoxLayout()
        
        for i in range(8):  # Support up to 8 axes
            radio = QRadioButton(f"Axis {i}")
            axis_buttons.addButton(radio, i)
            
            # Add to current row
            current_row.addWidget(radio)
            
            # Create a new row after every 4 buttons
            if (i + 1) % 4 == 0:
                axis_grid.addLayout(current_row)
                current_row = QHBoxLayout()
            
            # Hide all buttons initially
            radio.setVisible(False)
        
        # Add the last row if it has any buttons
        if current_row.count() > 0:
            axis_grid.addLayout(current_row)
        
        axis_buttons_layout.addLayout(axis_grid)
        axis_layout.addLayout(axis_buttons_layout)
        
        # Add buttons layout
        buttons_layout = QHBoxLayout()
        
        # Add a "Show All Axes" button
        manual_btn = QPushButton("Show All Axes")
        manual_btn.clicked.connect(lambda: self.show_all_axes(pedal_name))
        manual_btn.setToolTip("Show all available axes for manual selection")
        buttons_layout.addWidget(manual_btn)
        
        # Add a "Try Again" button to reset detection
        retry_btn = QPushButton("Try Again")
        retry_btn.clicked.connect(lambda: self.initialize_pedal_calibration(pedal_name))
        retry_btn.setToolTip("Reset axis detection and try again")
        buttons_layout.addWidget(retry_btn)
        
        axis_layout.addLayout(buttons_layout)
        
        layout.addWidget(axis_group)
        setattr(self, f"{pedal_name}_axis_group", axis_group)
        
        # Add page to stack
        self.stack.addWidget(page)
        return page

    def create_throttle_page(self):
        """Create the throttle calibration page."""
        self.throttle_page = self.create_pedal_page("throttle")
    
    def create_brake_page(self):
        """Create the brake calibration page."""
        self.brake_page = self.create_pedal_page("brake")
    
    def create_clutch_page(self):
        """Create the clutch calibration page."""
        self.clutch_page = self.create_pedal_page("clutch")

    def create_finish_page(self):
        """Create the finish page of the wizard."""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Title
        title = QLabel("Calibration Complete")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        description = QLabel(
            "All pedals have been successfully calibrated.\n\n"
            "Click 'Finish' to apply the calibration settings."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # Summary
        summary = QLabel("")
        summary.setWordWrap(True)
        summary.setAlignment(Qt.AlignCenter)
        layout.addWidget(summary)
        self.summary_label = summary
        
        # Add page to stack
        self.stack.addWidget(page)
        
    def go_next(self):
        """Go to the next page in the wizard."""
        current = self.stack.currentIndex()
        
        # Handle special cases for pedal pages
        if current == 1:  # Throttle page
            if not self.finalize_pedal_calibration("throttle"):
                return
        elif current == 2:  # Brake page
            if not self.finalize_pedal_calibration("brake"):
                return
        elif current == 3:  # Clutch page
            if not self.finalize_pedal_calibration("clutch"):
                return
        elif current == 4:  # Finish page
            # Change Next button to Finish on the last page
            self.accept()
            return
        
        # Move to next page
        self.stack.setCurrentIndex(current + 1)
        self.current_page = current + 1
        
        # Initialize the new page
        if self.current_page == 1:  # Throttle page
            self.initialize_pedal_calibration("throttle")
        elif self.current_page == 2:  # Brake page
            self.initialize_pedal_calibration("brake")
        elif self.current_page == 3:  # Clutch page
            self.initialize_pedal_calibration("clutch")
        elif self.current_page == 4:  # Finish page
            self.update_summary()
            self.next_btn.setText("Finish")
        
        # Update navigation buttons
        self.update_navigation_buttons()
    
    def go_back(self):
        """Go to the previous page in the wizard."""
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.current_page = current - 1
            
            # Reset Next button text if going back from finish page
            if current == 4:
                self.next_btn.setText("Next")
            
            # Update navigation buttons
            self.update_navigation_buttons()
    
    def update_navigation_buttons(self):
        """Update the state of navigation buttons."""
        current = self.stack.currentIndex()
        self.back_btn.setEnabled(current > 0)
        
    def initialize_pedal_calibration(self, pedal):
        """Initialize calibration for a specific pedal."""
        self.current_pedal = pedal
        self.calibration_stage = "detect_axis"
        
        # Reset detection flags
        if hasattr(self, '_logged_axes'):
            delattr(self, '_logged_axes')
        
        # Reset baseline values
        if hasattr(self, 'baseline_values'):
            delattr(self, 'baseline_values')
        
        # Reset movement history
        self.axis_movement_history = {}
        
        # Reset detected values
        self.detected_axes = {}
        self.axis_values = {}
        self.axis_min_values = {}
        self.axis_max_values = {}
        
        # Update instructions with clearer guidance
        instructions = getattr(self, f"{pedal}_instructions")
        instructions.setText(f"Press the {pedal} pedal fully and then release it completely to detect which axis it uses.")
        
        # Update status
        status = getattr(self, f"{pedal}_status")
        status.setText("Waiting for pedal movement...")
        
        # Hide all axis radio buttons initially and uncheck them
        axis_group = getattr(self, f"{pedal}_axis_group")
        axis_buttons = getattr(self, f"{pedal}_axis_buttons")
        for button in axis_buttons.buttons():
            button.setVisible(False)
            button.setChecked(False)
            button.setText(f"Axis {axis_buttons.id(button)}")  # Reset button text
        
        # Reset progress bar and value labels
        progress = getattr(self, f"{pedal}_progress")
        progress.setValue(0)
        
        value_label = getattr(self, f"{pedal}_value")
        value_label.setText("Current Value: 0")
        
        min_label = getattr(self, f"{pedal}_min")
        min_label.setText("Min: 0")
        
        max_label = getattr(self, f"{pedal}_max")
        max_label.setText("Max: 65535")
        
        # Force an immediate input read to establish baseline values
        self.update_inputs()
    
    def finalize_pedal_calibration(self, pedal):
        """Finalize calibration for a specific pedal."""
        # Check if an axis was selected
        axis_buttons = getattr(self, f"{pedal}_axis_buttons")
        selected_axis = axis_buttons.checkedId()
        if selected_axis == -1:
            # Try to auto-select an axis if none is selected
            if hasattr(self, 'detected_axes') and self.detected_axes:
                # Find the axis with the largest change from baseline
                largest_change = 0
                best_axis = -1
                
                if hasattr(self, 'baseline_values'):
                    for axis, value in self.detected_axes.items():
                        if axis in self.baseline_values:
                            change = abs(value - self.baseline_values[axis])
                            if change > largest_change:
                                largest_change = change
                                best_axis = axis
                
                # If we found a good candidate, use it
                if best_axis != -1 and largest_change > 3000:
                    selected_axis = best_axis
                    logger.info(f"Auto-selected axis {best_axis} for {pedal} based on largest change ({largest_change})")
                # Otherwise try to find the axis with the largest range
                else:
                    largest_range = 0
                    for axis in self.axis_min_values.keys():
                        if axis in self.axis_max_values:
                            axis_range = self.axis_max_values[axis] - self.axis_min_values[axis]
                            if axis_range > largest_range:
                                largest_range = axis_range
                                best_axis = axis
                    
                    if best_axis != -1 and largest_range > 3000:
                        selected_axis = best_axis
                        logger.info(f"Auto-selected axis {best_axis} for {pedal} based on largest range ({largest_range})")
            
            # If we still don't have an axis, show an error and suggest manual selection
            if selected_axis == -1:
                QMessageBox.warning(self, "Calibration Error", 
                                  f"No axis selected for the {pedal} pedal.\n\n"
                                  f"Please click 'Show All Axes' and manually select the axis for your {pedal} pedal.")
                return False
        
        # Ensure we have min/max values for the selected axis
        if selected_axis not in self.axis_min_values or selected_axis not in self.axis_max_values:
            self.axis_min_values[selected_axis] = 0
            self.axis_max_values[selected_axis] = 65535
            logger.warning(f"Using default min/max values for axis {selected_axis}")
        
        # Validate the min/max values
        min_val = self.axis_min_values[selected_axis]
        max_val = self.axis_max_values[selected_axis]
        
        # If min and max are too close, use defaults
        if abs(max_val - min_val) < 1000:
            logger.warning(f"Min and max values are too close for axis {selected_axis}, using defaults")
            min_val = 0
            max_val = 65535
        
        # Store the results
        self.results[pedal] = {
            'axis': selected_axis,
            'min': min_val,
            'max': max_val
        }
        
        # Show confirmation message
        status = getattr(self, f"{pedal}_status")
        status.setText(f"Successfully calibrated {pedal} pedal using Axis {selected_axis}.")
        status.setStyleSheet("font-weight: bold; color: #00aa00;")  # Green color for success
        
        logger.info(f"Finalized calibration for {pedal}: axis={selected_axis}, min={min_val}, max={max_val}")
        return True
        
    def update_summary(self):
        """Update the summary on the finish page."""
        summary_text = "Calibration Summary:\n\n"
        
        for pedal in ['throttle', 'brake', 'clutch']:
            if pedal in self.results:
                result = self.results[pedal]
                summary_text += f"{pedal.capitalize()} Pedal:\n"
                if 'axis' in result:
                    summary_text += f"  - Axis: {result['axis']}\n"
                summary_text += f"  - Min Value: {result['min']}\n"
                summary_text += f"  - Max Value: {result['max']}\n\n"
        
        self.summary_label.setText(summary_text)
        
    def show_all_axes(self, pedal_name):
        """Show all available axes for manual selection."""
        if not hasattr(self, 'hardware') or not self.hardware:
            return
        
        try:
            # Get joystick
            joystick = self.hardware.joystick
            num_axes = joystick.get_numaxes()
            
            # Get the button group for this pedal
            axis_buttons = getattr(self, f"{pedal_name}_axis_buttons")
            
            # Show all axes
            for i in range(min(num_axes, 8)):  # Limit to 8 axes max
                for button in axis_buttons.buttons():
                    if axis_buttons.id(button) == i:
                        button.setVisible(True)
                        # Show current value next to button
                        if i in self.axis_values:
                            button.setText(f"Axis {i} (Current: {self.axis_values[i]})")
            
            # Update status
            status = getattr(self, f"{pedal_name}_status")
            status.setText("Manual selection mode activated. Press each pedal to see which axis changes.")
            status.setStyleSheet("font-weight: bold; color: #ff9900;")  # Orange color for manual mode
            
            # Update instructions
            instructions = getattr(self, f"{pedal_name}_instructions")
            instructions.setText(f"Press the {pedal_name} pedal to see which axis changes, then select that axis and press Next.")
            
            # Move to set_min_max stage to allow manual selection
            self.calibration_stage = "set_min_max"
            
            # Force an update to show current values
            self.update_inputs()
            
            # If no axis is currently selected, try to make a best guess
            if not any(btn.isChecked() for btn in axis_buttons.buttons()):
                # Find the axis with the largest range (max-min)
                largest_range = 0
                best_axis = -1
                
                for i in range(min(num_axes, 8)):
                    if i in self.axis_min_values and i in self.axis_max_values:
                        axis_range = self.axis_max_values[i] - self.axis_min_values[i]
                        if axis_range > largest_range:
                            largest_range = axis_range
                            best_axis = i
                
                # Select the best axis if found
                if best_axis != -1:
                    for button in axis_buttons.buttons():
                        if axis_buttons.id(button) == best_axis:
                            button.setVisible(True)
                            button.setChecked(True)
                            logger.info(f"Auto-selected axis {best_axis} for {pedal_name} based on range")
                # Otherwise select the first axis as a fallback
                elif num_axes > 0:
                    for button in axis_buttons.buttons():
                        if axis_buttons.id(button) == 0:
                            button.setVisible(True)
                            button.setChecked(True)
                            logger.info(f"Selected first axis as fallback for {pedal_name}")
        
        except Exception as e:
            logger.error(f"Error showing all axes: {e}")

    def update_inputs(self):
        """Update input values from hardware."""
        if not hasattr(self, 'hardware') or not self.hardware:
            return
        
        try:
            # Read all axes directly
            pygame.event.pump()
            joystick = self.hardware.joystick
            
            # Log the number of axes for debugging
            if self.current_pedal and self.calibration_stage == "detect_axis" and not hasattr(self, '_logged_axes'):
                num_axes = joystick.get_numaxes()
                logger.info(f"Calibration wizard detected {num_axes} axes on the joystick")
                self._logged_axes = True
                # Initialize baseline values for all axes
                self.baseline_values = {}
                for i in range(joystick.get_numaxes()):
                    raw_value = joystick.get_axis(i)
                    self.baseline_values[i] = int((raw_value + 1) * 32767)
                logger.info(f"Baseline values: {self.baseline_values}")
                
                # Reset movement history
                self.axis_movement_history = {}
            
            # Track the axis with the largest change
            largest_change = 0
            largest_change_axis = -1
            
            # Keep track of which axes have changed significantly in this update
            changed_axes = set()
            
            # Process all available axes
            for i in range(joystick.get_numaxes()):
                # Get raw value (-1 to 1)
                raw_value = joystick.get_axis(i)
                
                # Convert to 0-65535 range
                scaled_value = int((raw_value + 1) * 32767)
                
                # Store the value
                self.axis_values[i] = scaled_value
                
                # Update min/max values
                if i not in self.axis_min_values:
                    self.axis_min_values[i] = scaled_value
                    self.axis_max_values[i] = scaled_value
                else:
                    self.axis_min_values[i] = min(self.axis_min_values[i], scaled_value)
                    self.axis_max_values[i] = max(self.axis_max_values[i], scaled_value)
                
                # Detect significant changes
                significant_change = False
                change_amount = 0
                
                # Check if this is a new axis or if there's been a significant change
                if i not in self.detected_axes:
                    self.detected_axes[i] = scaled_value
                    # Consider this a significant change if the value is not near center
                    if abs(scaled_value - 32767) > 5000:
                        significant_change = True
                        change_amount = abs(scaled_value - 32767)
                        logger.info(f"Initial significant value on axis {i}: {scaled_value}")
                else:
                    prev_value = self.detected_axes[i]
                    change_amount = abs(scaled_value - prev_value)
                    
                    # Check for significant change with a lower threshold for better detection
                    if change_amount > 2000:  
                        significant_change = True
                        changed_axes.add(i)  # Mark this axis as changed
                        logger.info(f"Detected change on axis {i}: {prev_value} -> {scaled_value} (change: {change_amount})")
                
                # If we have baseline values, also check for significant deviation from baseline
                if hasattr(self, 'baseline_values') and i in self.baseline_values:
                    baseline_deviation = abs(scaled_value - self.baseline_values[i])
                    if baseline_deviation > 3000 and not significant_change:
                        significant_change = True
                        changed_axes.add(i)  # Mark this axis as changed
                        change_amount = baseline_deviation
                        logger.info(f"Detected deviation from baseline on axis {i}: {self.baseline_values[i]} -> {scaled_value} (deviation: {baseline_deviation})")
                
                # Update movement history for this axis
                if significant_change:
                    if i not in self.axis_movement_history:
                        self.axis_movement_history[i] = []
                    
                    # Add this change to history (up to 10 most recent changes)
                    self.axis_movement_history[i].append(change_amount)
                    if len(self.axis_movement_history[i]) > 10:
                        self.axis_movement_history[i].pop(0)
                    
                    # Calculate total movement for this axis
                    total_movement = sum(self.axis_movement_history[i])
                    
                    # If this axis has more total movement, it's likely the one being used
                    if total_movement > largest_change:
                        largest_change = total_movement
                        largest_change_axis = i
                        logger.info(f"Axis {i} has the most movement history: {total_movement}")
                
                # If we detected a significant change
                if significant_change and self.current_pedal and self.calibration_stage == "detect_axis":
                    # Get the button group for the current pedal
                    current_axis_buttons = getattr(self, f"{self.current_pedal}_axis_buttons")
                    
                    # Show this axis as an option
                    for button in current_axis_buttons.buttons():
                        if current_axis_buttons.id(button) == i:
                            button.setVisible(True)
                            # Don't auto-select yet, we'll select the axis with the largest change below
                    
                    # Update status to show we detected movement
                    status = getattr(self, f"{self.current_pedal}_status")
                    status.setText(f"Detected movement on Axis {i}. Press and release the pedal again if needed.")
                
                # Store current value for change detection
                self.detected_axes[i] = scaled_value
                
                # Update button text for all visible buttons to show current values
                if self.current_pedal:
                    current_axis_buttons = getattr(self, f"{self.current_pedal}_axis_buttons")
                    for button in current_axis_buttons.buttons():
                        if button.isVisible() and current_axis_buttons.id(button) == i:
                            # Highlight buttons for axes that changed in this update
                            if i in changed_axes:
                                button.setText(f"Axis {i} (Current: {scaled_value}) ← CHANGED")
                                button.setStyleSheet("color: #00ff00; font-weight: bold;")  # Green text for changed axes
                            else:
                                button.setText(f"Axis {i} (Current: {scaled_value})")
                                button.setStyleSheet("")  # Reset style
            
            # After processing all axes, select the one with the largest change if we're in detect_axis stage
            if largest_change_axis != -1 and self.current_pedal and self.calibration_stage == "detect_axis":
                # Get the button group for the current pedal
                current_axis_buttons = getattr(self, f"{self.current_pedal}_axis_buttons")
                
                # Auto-select the axis with the largest change
                for button in current_axis_buttons.buttons():
                    if current_axis_buttons.id(button) == largest_change_axis:
                        button.setVisible(True)
                        button.setChecked(True)
                        logger.info(f"Auto-selected axis {largest_change_axis} for {self.current_pedal} (largest change: {largest_change})")
                
                # Update status
                status = getattr(self, f"{self.current_pedal}_status")
                status.setText(f"Detected movement on Axis {largest_change_axis}. Select the correct axis and press Next.")
                
                # Update instructions
                instructions = getattr(self, f"{self.current_pedal}_instructions")
                instructions.setText("Select the correct axis, then fully release the pedal and press Next.")
                
                # Move to next stage
                self.calibration_stage = "set_min_max"
            
            # Update UI for current pedal if we're on a pedal page
            if self.current_pedal:
                # Get the button group for the current pedal
                current_axis_buttons = getattr(self, f"{self.current_pedal}_axis_buttons")
                
                # Get the selected axis
                selected_axis = current_axis_buttons.checkedId()
                if selected_axis != -1 and selected_axis in self.axis_values:
                    # Update progress bar
                    progress = getattr(self, f"{self.current_pedal}_progress")
                    progress.setValue(self.axis_values[selected_axis])
                    
                    # Update value label
                    value_label = getattr(self, f"{self.current_pedal}_value")
                    value_label.setText(f"Current Value: {self.axis_values[selected_axis]}")
                    
                    # Update min/max labels
                    min_label = getattr(self, f"{self.current_pedal}_min")
                    min_label.setText(f"Min: {self.axis_min_values.get(selected_axis, 0)}")
                    
                    max_label = getattr(self, f"{self.current_pedal}_max")
                    max_label.setText(f"Max: {self.axis_max_values.get(selected_axis, 65535)}")
                    
                    # If we're in set_min_max stage, update instructions based on pedal position
                    if self.calibration_stage == "set_min_max":
                        current_value = self.axis_values[selected_axis]
                        min_value = self.axis_min_values.get(selected_axis, 0)
                        max_value = self.axis_max_values.get(selected_axis, 65535)
                        
                        # Calculate how far the pedal is pressed (0-100%)
                        if max_value > min_value:
                            percentage = ((current_value - min_value) / (max_value - min_value)) * 100
                        else:
                            percentage = 0
                        
                        instructions = getattr(self, f"{self.current_pedal}_instructions")
                        if percentage < 10:
                            instructions.setText("Good! Pedal is released. Now press the pedal fully and then press Next.")
                        elif percentage > 90:
                            instructions.setText("Good! Pedal is fully pressed. Press Next to continue.")
                        else:
                            instructions.setText("Please fully release the pedal, then press it fully before continuing.")
        
        except Exception as e:
            logger.error(f"Error updating inputs: {e}") 