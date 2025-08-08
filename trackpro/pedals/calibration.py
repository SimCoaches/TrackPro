from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QGroupBox, QButtonGroup, QRadioButton,
    QProgressBar, QMessageBox, QWidget, QWizard, QWizardPage,
    QSizePolicy, QSpacerItem, QFrame, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QBrush, QColor
import pygame
import logging
from ..database import supabase

logger = logging.getLogger(__name__)

class PedalSetSelectionPage(QWizardPage):
    """First page to select pedal set type (2 or 3 pedals)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Pedal Set Selection")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("What pedal set do you have?")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Instruction
        instruction_label = QLabel("Please select your pedal configuration:")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction_label.setStyleSheet("""
            font-size: 12pt; 
            margin-bottom: 10px;
            background-color: transparent;
        """)
        layout.addWidget(instruction_label)

        # Create selection area
        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(30)

        # 2-Pedal option
        self.two_pedal_group = QGroupBox()
        self.two_pedal_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #505050;
                border-radius: 10px;
                padding: 20px;
                background-color: #3a3a3a;
            }
            QGroupBox:hover {
                border-color: #2a82da;
                cursor: pointer;
            }
        """)
        # Make the entire group box clickable
        self.two_pedal_group.mousePressEvent = lambda event: self.select_two_pedal()
        # Set cursor to pointer to indicate clickability
        self.two_pedal_group.setCursor(Qt.CursorShape.PointingHandCursor)
        two_pedal_layout = QVBoxLayout(self.two_pedal_group)
        
        # 2-pedal image placeholder (you can replace with actual image)
        two_pedal_image = self.create_pedal_image(2)
        two_pedal_layout.addWidget(two_pedal_image)
        
        # 2-pedal radio button and label
        self.two_pedal_radio = QRadioButton("2-Pedal Set")
        self.two_pedal_radio.setStyleSheet("""
            QRadioButton {
                font-size: 14pt; 
                font-weight: bold;
                background-color: transparent;
                color: #e0e0e0;
            }
        """)
        two_pedal_layout.addWidget(self.two_pedal_radio, alignment=Qt.AlignmentFlag.AlignCenter)
        
        two_pedal_desc = QLabel("Throttle + Brake")
        two_pedal_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        two_pedal_desc.setStyleSheet("""
            font-size: 10pt; 
            color: #b0b0b0;
            background-color: transparent;
        """)
        two_pedal_layout.addWidget(two_pedal_desc)

        # 3-Pedal option
        self.three_pedal_group = QGroupBox()
        self.three_pedal_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #505050;
                border-radius: 10px;
                padding: 20px;
                background-color: #3a3a3a;
            }
            QGroupBox:hover {
                border-color: #2a82da;
                cursor: pointer;
            }
        """)
        # Make the entire group box clickable
        self.three_pedal_group.mousePressEvent = lambda event: self.select_three_pedal()
        # Set cursor to pointer to indicate clickability
        self.three_pedal_group.setCursor(Qt.CursorShape.PointingHandCursor)
        three_pedal_layout = QVBoxLayout(self.three_pedal_group)
        
        # 3-pedal image placeholder
        three_pedal_image = self.create_pedal_image(3)
        three_pedal_layout.addWidget(three_pedal_image)
        
        # 3-pedal radio button and label
        self.three_pedal_radio = QRadioButton("3-Pedal Set")
        self.three_pedal_radio.setStyleSheet("""
            QRadioButton {
                font-size: 14pt; 
                font-weight: bold;
                background-color: transparent;
                color: #e0e0e0;
            }
        """)
        three_pedal_layout.addWidget(self.three_pedal_radio, alignment=Qt.AlignmentFlag.AlignCenter)
        
        three_pedal_desc = QLabel("Throttle + Brake + Clutch")
        three_pedal_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        three_pedal_desc.setStyleSheet("""
            font-size: 10pt; 
            color: #b0b0b0;
            background-color: transparent;
        """)
        three_pedal_layout.addWidget(three_pedal_desc)

        # Add to selection layout
        selection_layout.addWidget(self.two_pedal_group)
        selection_layout.addWidget(self.three_pedal_group)
        layout.addLayout(selection_layout)

        # Create button group for exclusive selection
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.two_pedal_radio, 2)
        self.button_group.addButton(self.three_pedal_radio, 3)
        
        # Connect signals for visual feedback
        self.two_pedal_radio.toggled.connect(self.update_selection_ui)
        self.three_pedal_radio.toggled.connect(self.update_selection_ui)
        
        # Register field for wizard
        self.registerField("pedal_count*", self.two_pedal_radio, "checked")
        
        # Default to 3-pedal
        self.three_pedal_radio.setChecked(True)

    def create_pedal_image(self, pedal_count):
        """Create a simple visual representation of pedal set or load custom image."""
        label = QLabel()
        label.setFixedSize(150, 100)
        # Match the group box background color for seamless look
        label.setStyleSheet("background-color: transparent; border: none;")
        
        # Try to load custom PNG files first
        try:
            from trackpro.utils.resource_utils import get_resource_path
            import os
            
            # Look for custom images in resources/images directory
            if pedal_count == 2:
                image_path = get_resource_path("trackpro/resources/images/2_pedal_set.png")
            else:
                image_path = get_resource_path("trackpro/resources/images/3_pedal_set.png")
            
            if os.path.exists(image_path):
                # Load custom PNG file
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale the image to fit the label while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(150, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled_pixmap)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    return label
        except Exception as e:
            logger.debug(f"Could not load custom pedal image: {e}, using generated image")
        
        # Fall back to programmatically generated image with transparent background
        pixmap = QPixmap(150, 100)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw pedal rectangles
        pedal_width = 20
        pedal_height = 40
        spacing = 25
        start_x = (150 - (pedal_count * pedal_width + (pedal_count - 1) * spacing)) // 2
        start_y = 30
        
        # Set colors for different pedals
        pedal_colors = [QColor("#ff6b6b"), QColor("#4ecdc4"), QColor("#45b7d1")]  # Red, Green, Blue
        
        for i in range(pedal_count):
            x = start_x + i * (pedal_width + spacing)
            painter.fillRect(x, start_y, pedal_width, pedal_height, QBrush(pedal_colors[i]))
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawRect(x, start_y, pedal_width, pedal_height)
        
        painter.end()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def update_selection_ui(self):
        """Update UI based on selection."""
        if self.two_pedal_radio.isChecked():
            self.two_pedal_group.setStyleSheet("""
                QGroupBox {
                    border: 3px solid #2a82da;
                    border-radius: 10px;
                    padding: 20px;
                    background-color: #4a4a4a;
                }
            """)
            self.three_pedal_group.setStyleSheet("""
                QGroupBox {
                    border: 2px solid #505050;
                    border-radius: 10px;
                    padding: 20px;
                    background-color: #3a3a3a;
                }
            """)
        else:
            self.three_pedal_group.setStyleSheet("""
                QGroupBox {
                    border: 3px solid #2a82da;
                    border-radius: 10px;
                    padding: 20px;
                    background-color: #4a4a4a;
                }
            """)
            self.two_pedal_group.setStyleSheet("""
                QGroupBox {
                    border: 2px solid #505050;
                    border-radius: 10px;
                    padding: 20px;
                    background-color: #3a3a3a;
                }
            """)
        
        self.completeChanged.emit()

    def isComplete(self):
        """Page is complete when a selection is made."""
        return self.two_pedal_radio.isChecked() or self.three_pedal_radio.isChecked()
    
    def get_pedal_count(self):
        """Get selected pedal count."""
        return 2 if self.two_pedal_radio.isChecked() else 3

    def select_two_pedal(self):
        """Handle click on the 2-Pedal option."""
        self.two_pedal_radio.setChecked(True)
        self.update_selection_ui()
        self.completeChanged.emit()

    def select_three_pedal(self):
        """Handle click on the 3-Pedal option."""
        self.three_pedal_radio.setChecked(True)
        self.update_selection_ui()
        self.completeChanged.emit()

class PedalCalibrationPage(QWizardPage):
    """Individual pedal calibration page with smooth workflow."""
    def __init__(self, pedal_name, hardware_input, parent=None):
        super().__init__(parent)
        self.pedal_name = pedal_name
        self.hardware_input = hardware_input
        self.setTitle(f"{pedal_name.capitalize()} Calibration")
        
        # Calibration state
        self.calibration_stage = "waiting"  # waiting, calibrating, complete
        self.detected_axis = -1
        self.min_value = 65535
        self.max_value = 0
        self.current_value = 0
        self.values_collected = []
        self.calibration_started = False

        # Axis detection helpers
        self._baseline_ready = False
        self._baseline_samples_needed = 15
        self._baseline_accumulators = []  # running sums per axis
        self._baseline_counts = 0
        self._movement_confirm_frames = 0
        self._candidate_axis = -1
        # Absolute delta in 0..65535 space (lower for brake to reduce "stuck" feel)
        self._movement_threshold = 4000
        if self.pedal_name == "brake":
            self._movement_threshold = 2500
        
        self.setup_ui()
        
        # Timer for input updates (started when page is active)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_input)

    def setup_ui(self):
        """Setup the UI for this calibration page."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Reduced spacing to fit better
        layout.setContentsMargins(30, 20, 30, 20)  # Reduced top/bottom margins

        # Title
        title_label = QLabel(f"Calibrate {self.pedal_name.capitalize()} Pedal")
        title_font = QFont()
        title_font.setPointSize(16)  # Slightly smaller title
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Instructions with better sizing
        self.instructions = QLabel(f"Press the {self.pedal_name.upper()} pedal FULLY and then RELEASE it completely")
        self.instructions.setWordWrap(True)
        self.instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instructions.setStyleSheet("""
            font-size: 13pt; 
            margin: 10px; 
            padding: 12px; 
            background-color: #3a3a3a; 
            border-radius: 8px;
            min-height: 50px;
        """)
        # Ensure the instruction label has enough space
        self.instructions.setMinimumHeight(60)
        layout.addWidget(self.instructions)

        # Status
        self.status = QLabel("Ready to calibrate. Press and release the pedal when ready.")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("font-size: 11pt; color: #b0b0b0; margin: 5px;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 65535)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #505050;
                border-radius: 8px;
                text-align: center;
                font-size: 11pt;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Values display
        values_layout = QHBoxLayout()
        
        self.current_label = QLabel("Current: 0")
        self.current_label.setStyleSheet("font-size: 11pt; font-weight: bold;")
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.min_label = QLabel("Min: --")
        self.min_label.setStyleSheet("font-size: 11pt; color: #ff6b6b;")
        self.min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.max_label = QLabel("Max: --")
        self.max_label.setStyleSheet("font-size: 11pt; color: #4ecdc4;")
        self.max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        values_layout.addWidget(self.current_label)
        values_layout.addWidget(self.min_label)
        values_layout.addWidget(self.max_label)
        layout.addLayout(values_layout)

        # Buttons layout
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.reset_button.clicked.connect(self.reset_calibration)
        
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)

        # Register fields
        self.registerField(f"{self.pedal_name}_min*", self.min_label, "text")
        self.registerField(f"{self.pedal_name}_max*", self.max_label, "text")
        self.registerField(f"{self.pedal_name}_axis*", self.current_label, "text")

    def initializePage(self):
        """Initialize the page when shown."""
        logger.info(f"Initializing calibration for {self.pedal_name}")
        self.reset_calibration()
        # Start timer when the page becomes active
        try:
            if self.timer and not self.timer.isActive():
                self.timer.start(16)
        except Exception:
            pass

    def cleanupPage(self):
        """Called by QWizard when the user leaves this page."""
        try:
            if self.timer and self.timer.isActive():
                self.timer.stop()
        except Exception:
            pass

    def reset_calibration(self):
        """Reset calibration to initial state."""
        self.calibration_stage = "waiting"
        self.detected_axis = -1
        self.min_value = 65535
        self.max_value = 0
        self.values_collected = []
        self.calibration_started = False

        # Reset baseline detection
        self._baseline_ready = False
        self._baseline_samples_needed = 15
        self._baseline_accumulators = []
        self._baseline_counts = 0
        self._movement_confirm_frames = 0
        self._candidate_axis = -1
        
        self.instructions.setText(f"Press the {self.pedal_name.upper()} pedal FULLY and then RELEASE it completely")
        self.status.setText("Ready to calibrate. Press and release the pedal when ready.")
        self.min_label.setText("Min: --")
        self.max_label.setText("Max: --")
        self.progress_bar.setValue(0)
        
        self.completeChanged.emit()

    def update_input(self):
        """Update input values and detect calibration."""
        # Only process input when this page is the active wizard page
        try:
            wiz = self.wizard()
            if wiz and wiz.currentPage() is not self:
                return
        except Exception:
            pass

        if not self.hardware_input or not self.hardware_input.joystick:
            self.status.setText("⚠️ Sim Coaches P1 Pro Pedals not connected")
            return

        # Only proceed if we have Sim Coaches P1 Pro Pedals
        if "Sim Coaches P1 Pro Pedals" not in self.hardware_input.joystick.get_name():
            self.status.setText("⚠️ Please connect Sim Coaches P1 Pro Pedals")
            return

        try:
            pygame.event.pump()
            joystick = self.hardware_input.joystick
            
            # Read all axes
            current_raw_values = []
            for i in range(joystick.get_numaxes()):
                raw_value = joystick.get_axis(i)
                scaled_value = int((raw_value + 1) * 32767.5)
                current_raw_values.append(scaled_value)

            # Build/update baseline for robust axis detection
            if not self._baseline_ready:
                axis_count = len(current_raw_values)
                if not self._baseline_accumulators or len(self._baseline_accumulators) != axis_count:
                    self._baseline_accumulators = [0] * axis_count
                    self._baseline_counts = 0

                for i, value in enumerate(current_raw_values):
                    self._baseline_accumulators[i] += value
                self._baseline_counts += 1

                if self._baseline_counts >= self._baseline_samples_needed:
                    # Convert sums to averages
                    self._baseline_values = [acc // self._baseline_counts for acc in self._baseline_accumulators]
                    self._baseline_ready = True

            # Auto-detect axis during calibration (relative to baseline, excluding already used axes)
            if self.calibration_stage == "waiting" and self._baseline_ready:
                # Exclude axes already assigned in previous pages
                used_axes = set()
                try:
                    wiz = self.wizard()
                    if hasattr(wiz, 'used_axes'):
                        used_axes = wiz.used_axes
                except Exception:
                    used_axes = set()

                chosen_axis = -1
                # Determine candidate by largest movement over threshold among unused axes
                best_delta = 0
                for i, value in enumerate(current_raw_values):
                    if i in used_axes:
                        continue
                    delta = abs(value - self._baseline_values[i])
                    if delta > self._movement_threshold and delta > best_delta:
                        best_delta = delta
                        chosen_axis = i

                # Require a few consecutive frames confirming the same axis to avoid noise
                if chosen_axis >= 0:
                    if self._candidate_axis == chosen_axis:
                        self._movement_confirm_frames += 1
                    else:
                        self._candidate_axis = chosen_axis
                        self._movement_confirm_frames = 1

                    if self._movement_confirm_frames >= 3:
                        self.detected_axis = self._candidate_axis
                        self.calibration_stage = "calibrating"
                        self.calibration_started = True
                        self.status.setText(f"🎯 Axis {self.detected_axis} detected! Continue moving the pedal...")
                        logger.info(f"Auto-detected axis {self.detected_axis} for {self.pedal_name}")
                        # Enable Next button as soon as axis is detected
                        self.completeChanged.emit()

            elif self.calibration_stage == "calibrating":
                if self.detected_axis >= 0 and self.detected_axis < len(current_raw_values):
                    self.current_value = current_raw_values[self.detected_axis]
                    self.current_label.setText(f"Current: {self.current_value}")
                    self.progress_bar.setValue(self.current_value)
                    
                    # Collect values for min/max detection
                    self.values_collected.append(self.current_value)
                    
                    # Update min/max
                    if self.current_value < self.min_value:
                        self.min_value = self.current_value
                        self.min_label.setText(f"Min: {self.min_value}")
                    
                    if self.current_value > self.max_value:
                        self.max_value = self.current_value
                        self.max_label.setText(f"Max: {self.max_value}")
                    
                    # Check if we have good calibration data
                    if len(self.values_collected) > 40:  # ~0.65s of data, quicker completion
                        range_size = self.max_value - self.min_value
                        # Per-pedal required range so pages mark complete reliably
                        required_range = 20000
                        if self.pedal_name == "throttle":
                            required_range = 7500
                        elif self.pedal_name == "brake":
                            required_range = 12000
                        elif self.pedal_name == "clutch":
                            required_range = 15000
                        if range_size > required_range:  # Good range detected
                            self.calibration_stage = "complete"
                            self.status.setText("✅ Calibration complete! Good range detected.")
                            self.instructions.setText(f"✅ {self.pedal_name.capitalize()} calibration successful!")
                            
                            # Store final values
                            self.setField(f"{self.pedal_name}_min", str(self.min_value))
                            self.setField(f"{self.pedal_name}_max", str(self.max_value))
                            self.setField(f"{self.pedal_name}_axis", str(self.detected_axis))

                            # Mark axis as used so subsequent pages don't reuse it
                            try:
                                wiz = self.wizard()
                                if hasattr(wiz, 'used_axes'):
                                    wiz.used_axes.add(self.detected_axis)
                            except Exception:
                                pass
                            
                            self.completeChanged.emit()
                            logger.info(f"Calibration complete for {self.pedal_name}: min={self.min_value}, max={self.max_value}, axis={self.detected_axis}")

            elif self.calibration_stage == "complete":
                # Keep the live percentage/progress updating so the UI doesn't look frozen
                if self.detected_axis >= 0 and self.detected_axis < len(current_raw_values):
                    self.current_value = current_raw_values[self.detected_axis]
                    self.current_label.setText(f"Current: {self.current_value}")
                    self.progress_bar.setValue(self.current_value)

        except Exception as e:
            logger.error(f"Error during calibration: {e}")
            self.status.setText(f"❌ Error: {str(e)}")

    def isComplete(self):
        """Check if calibration is complete."""
        # Allow proceeding once axis has been detected; final values will be committed in validatePage
        return self.calibration_stage in ("calibrating", "complete")

    def validatePage(self):
        """Validate before moving to next page."""
        # If already complete, proceed
        if self.calibration_stage == "complete":
            return True

        # If we're in calibrating state (axis detected), finalize with current observed min/max
        if self.calibration_stage == "calibrating" and self.detected_axis >= 0:
            try:
                # Commit fields so finish handler can persist them
                self.setField(f"{self.pedal_name}_min", str(self.min_value if self.min_value != 65535 else 0))
                self.setField(f"{self.pedal_name}_max", str(self.max_value if self.max_value != 0 else 65535))
                self.setField(f"{self.pedal_name}_axis", str(self.detected_axis))

                # Mark axis as used for subsequent pages
                try:
                    wiz = self.wizard()
                    if hasattr(wiz, 'used_axes'):
                        wiz.used_axes.add(self.detected_axis)
                except Exception:
                    pass

                # Optionally set to complete to keep state consistent
                self.calibration_stage = "complete"
                return True
            except Exception:
                pass

        QMessageBox.information(self, "Calibration Incomplete", 
                                f"Please complete the {self.pedal_name} calibration by pressing and releasing the pedal fully.")
        return False

class CongratulationsPage(QWizardPage):
    """Final congratulations page."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Calibration Complete!")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Success icon (text-based)
        success_label = QLabel("🎉")
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_label.setStyleSheet("font-size: 48pt;")
        layout.addWidget(success_label)

        # Title
        title_label = QLabel("Congratulations!")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #4ecdc4; margin: 20px;")
        layout.addWidget(title_label)

        # Message
        message_label = QLabel("Your pedal calibration has been completed successfully!")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("font-size: 14pt; margin: 10px;")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Summary area
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #3a3a3a;
                border: 1px solid #505050;
                border-radius: 8px;
                padding: 10px;
                font-size: 11pt;
            }
        """)
        layout.addWidget(self.summary_text)

        # Final message
        final_label = QLabel("Your pedals are now ready for racing! Click 'Finish' to complete the setup.")
        final_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        final_label.setStyleSheet("font-size: 12pt; color: #b0b0b0; margin: 20px;")
        final_label.setWordWrap(True)
        layout.addWidget(final_label)

    def initializePage(self):
        """Initialize with calibration summary."""
        try:
            # Get wizard reference
            wizard = self.wizard()
            
            # Get pedal count
            pedal_count = 3  # default
            if hasattr(wizard, 'page') and wizard.page(0):
                selection_page = wizard.page(0)
                if hasattr(selection_page, 'get_pedal_count'):
                    pedal_count = selection_page.get_pedal_count()
            
            # Build summary
            summary = "Calibration Summary:\n\n"
            
            # Always include throttle and brake
            pedals_to_show = ['throttle', 'brake']
            if pedal_count == 3:
                pedals_to_show.append('clutch')
            
            for pedal in pedals_to_show:
                try:
                    min_val = self.field(f"{pedal}_min")
                    max_val = self.field(f"{pedal}_max")
                    axis_val = self.field(f"{pedal}_axis")
                    
                    if min_val and max_val and axis_val:
                        min_num = min_val.replace("Min: ", "") if isinstance(min_val, str) else str(min_val)
                        max_num = max_val.replace("Max: ", "") if isinstance(max_val, str) else str(max_val)
                        range_size = int(max_num) - int(min_num) if max_num.isdigit() and min_num.isdigit() else 0
                        
                        summary += f"{pedal.capitalize()}:\n"
                        summary += f"  • Axis: {axis_val}\n"
                        summary += f"  • Range: {min_num} - {max_num} ({range_size} units)\n\n"
                except:
                    summary += f"{pedal.capitalize()}: Configuration error\n\n"
            
            summary += "All pedals have been successfully calibrated and are ready for use!"
            
            self.summary_text.setPlainText(summary)
            
        except Exception as e:
            logger.error(f"Error creating calibration summary: {e}")
            self.summary_text.setPlainText("Calibration completed successfully!")

class CalibrationWizard(QWizard):
    """Redesigned pedal calibration wizard with smooth workflow."""
    
    # Page IDs
    PAGE_SELECTION = 0
    PAGE_THROTTLE = 1
    PAGE_BRAKE = 2
    PAGE_CLUTCH = 3
    PAGE_COMPLETE = 4  # No longer used (final page removed)
    
    calibration_complete = pyqtSignal(dict)
    
    def __init__(self, hardware_input, parent=None):
        super().__init__(parent)
        
        self.hardware_input = hardware_input
        self.setWindowTitle("Pedal Calibration Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Store calibration results
        self.calibration_results = {}

        # Track which physical axes have already been assigned by prior pages
        self.used_axes = set()
        
        # Wizard options
        self.setOption(QWizard.WizardOption.IndependentPages, False)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.WizardOption.HaveFinishButtonOnEarlyPages, False)
        self.setOption(QWizard.WizardOption.NoCancelButton, False)
        
        # Modern dark styling
        self.setStyleSheet("""
            QWizard {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QWizardPage {
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #505050;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11pt;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #2a82da;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
            QPushButton#qt_wizard_finish {
                background-color: #27ae60;
                font-weight: bold;
            }
            QPushButton#qt_wizard_finish:hover {
                background-color: #2ecc71;
            }
            QPushButton#qt_wizard_next {
                background-color: #2a82da;
                font-weight: bold;
            }
            QPushButton#qt_wizard_next:hover {
                background-color: #3498db;
            }
            QPushButton#qt_wizard_back {
                background-color: #7f8c8d;
            }
            QPushButton#qt_wizard_back:hover {
                background-color: #95a5a6;
            }
            QProgressBar {
                border: 2px solid #505050;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 6px;
            }
            QRadioButton {
                color: #e0e0e0;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #505050;
                border-radius: 8px;
                background-color: #3a3a3a;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #2a82da;
                border-radius: 8px;
                background-color: #2a82da;
            }
        """)

        # Add pages (remove the final congratulations page per UX request)
        self.addPage(PedalSetSelectionPage(self))
        self.addPage(PedalCalibrationPage("throttle", self.hardware_input, self))
        self.addPage(PedalCalibrationPage("brake", self.hardware_input, self))
        self.addPage(PedalCalibrationPage("clutch", self.hardware_input, self))
        
        # Connect signals
        self.finished.connect(self.handle_finish)
        # If there is no final page, make the Finish button appear on the last calibration step
        self.setOption(QWizard.WizardOption.HaveFinishButtonOnEarlyPages, True)
        
        # Set size
        self.resize(600, 500)
        self.setMinimumSize(500, 400)
    
    def nextId(self):
        """Determine next page based on current page and selections."""
        current_id = self.currentId()
        
        if current_id == self.PAGE_SELECTION:
            return self.PAGE_THROTTLE
        elif current_id == self.PAGE_THROTTLE:
            return self.PAGE_BRAKE
        elif current_id == self.PAGE_BRAKE:
            # Check if user selected 3-pedal set
            selection_page = self.page(self.PAGE_SELECTION)
            if hasattr(selection_page, 'get_pedal_count') and selection_page.get_pedal_count() == 3:
                return self.PAGE_CLUTCH
            else:
                return -1
        elif current_id == self.PAGE_CLUTCH:
            return -1
        else:
            return -1

    def handle_finish(self, result):
        """Handle wizard completion."""
        if result == QWizard.DialogCode.Accepted:
            logger.info("Pedal calibration wizard completed successfully")
            
            try:
                # Extract calibration results
                selection_page = self.page(self.PAGE_SELECTION)
                pedal_count = selection_page.get_pedal_count() if hasattr(selection_page, 'get_pedal_count') else 3
                
                # Build results dictionary
                results = {}
                
                # Always include throttle and brake
                pedals_to_process = ['throttle', 'brake']
                if pedal_count == 3:
                    pedals_to_process.append('clutch')
                
                for pedal in pedals_to_process:
                    try:
                        min_field = self.field(f"{pedal}_min")
                        max_field = self.field(f"{pedal}_max")
                        
                        # Parse min/max from fields (labels)
                        min_val = int(min_field.replace("Min: ", "")) if isinstance(min_field, str) and "Min: " in min_field else int(min_field) if min_field else 0
                        max_val = int(max_field.replace("Max: ", "")) if isinstance(max_field, str) and "Max: " in max_field else int(max_field) if max_field else 65535

                        # Read axis directly from the corresponding page attribute to avoid label parsing issues
                        page_for_axis = {
                            'throttle': self.page(self.PAGE_THROTTLE),
                            'brake': self.page(self.PAGE_BRAKE),
                            'clutch': self.page(self.PAGE_CLUTCH)
                        }.get(pedal)
                        axis_val = int(getattr(page_for_axis, 'detected_axis', -1)) if page_for_axis else -1
                        
                        results[pedal] = {
                            'min': min_val,
                            'max': max_val,
                            'axis': axis_val
                        }
                        
                        logger.info(f"Extracted {pedal}: min={min_val}, max={max_val}, axis={axis_val}")
                    except Exception as e:
                        logger.error(f"Error extracting {pedal} calibration: {e}")
                        results[pedal] = {'min': 0, 'max': 65535, 'axis': -1}
                
                # Save calibration
                self.save_calibration(results)
                
                # Emit completion signal
                self.calibration_complete.emit(results)

                # Proactively stop the per-page timers after finishing to avoid handle leaks
                try:
                    for page_id in [self.PAGE_THROTTLE, self.PAGE_BRAKE, self.PAGE_CLUTCH]:
                        page = self.page(page_id)
                        if page and hasattr(page, 'timer') and page.timer.isActive():
                            page.timer.stop()
                except Exception:
                    pass
                
            except Exception as e:
                logger.error(f"Error processing calibration results: {e}")
                QMessageBox.critical(self, "Error", f"Failed to process calibration results: {e}")
        else:
            logger.info("Pedal calibration wizard cancelled")

    def save_calibration(self, results):
        """Save calibration results to hardware and storage."""
        try:
            if self.hardware_input:
                # Update axis ranges in hardware
                for pedal, data in results.items():
                    if pedal in ['throttle', 'brake', 'clutch'] and isinstance(data, dict):
                        # Update axis ranges
                        existing_ranges = self.hardware_input.axis_ranges.get(pedal, {})
                        self.hardware_input.axis_ranges[pedal] = {
                            'min': data.get('min', 0),
                            'max': data.get('max', 65535),
                            'min_deadzone': existing_ranges.get('min_deadzone', 0),
                            'max_deadzone': existing_ranges.get('max_deadzone', 0),
                            'axis': data.get('axis', -1)
                        }
                        
                        # Update axis mappings
                        if data.get('axis', -1) >= 0:
                            self.hardware_input.axis_mappings[pedal] = data['axis']
                
                # Save both axis ranges and mappings
                self.hardware_input.save_axis_ranges()
                self.hardware_input.save_axis_mappings()
                
                logger.info("Calibration saved successfully")
                
                # Show success message
                if supabase.is_authenticated():
                    QMessageBox.information(self, "Success", "Calibration saved successfully and synced to cloud!")
                else:
                    QMessageBox.information(self, "Success", "Calibration saved successfully!")
            else:
                logger.error("Cannot save calibration: hardware_input not available")
                QMessageBox.warning(self, "Error", "Hardware interface not available")
                
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save calibration: {e}") 