from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QGroupBox, QButtonGroup, QRadioButton,
    QProgressBar, QMessageBox, QWidget, QWizard, QWizardPage,
    QSizePolicy, QSpacerItem, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap
import pygame
import logging
from ..database import supabase

logger = logging.getLogger(__name__)

# Define Wizard Pages First
class IntroPage(QWizardPage):
    """Introduction page of the calibration wizard."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Remove any default QWizardPage margin/padding
        self.setContentsMargins(0, 0, 0, 0)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)  # Minimal top/bottom margins
        layout.setSpacing(10)  # Reduced spacing between elements

        title_label = QLabel("Welcome to Pedal Calibration")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        info_label = QLabel("""This wizard will guide you through calibrating your throttle, brake, and clutch pedals.

Ensure your pedals are connected and recognized by the system.

Follow the instructions on each page carefully.

Click 'Next' to begin.""")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        info_label.setStyleSheet("font-size: 11pt;")  # Color already set in wizard stylesheet
        layout.addWidget(info_label)

    # Ensure the page properly fits its contents
    def sizeHint(self):
        return QSize(500, 280)

class BasePedalPage(QWizardPage):
    """Base class for pedal calibration pages."""
    def __init__(self, pedal_name, hardware_input, parent=None):
        super().__init__(parent)
        self.pedal_name = pedal_name
        self.hardware_input = hardware_input
        self.setTitle(f"{pedal_name.capitalize()} Pedal Calibration")
        
        # Axis detection state
        self.calibration_stage = "detect_axis" # detect_axis, set_min, set_max
        self.detected_axis = -1
        self.min_value = 0
        self.max_value = 65535
        self.current_value = 0
        self.last_significant_value = 0
        
        # UI Elements
        layout = QVBoxLayout(self)
        self.instructions = QLabel(f"Press and release the {pedal_name} pedal to detect the axis.")
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)
        
        self.status = QLabel("Status: Waiting for pedal movement...")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 65535)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        value_layout = QHBoxLayout()
        self.value_label = QLabel("Current: 0")
        self.min_label = QLabel("Min: 0")
        self.max_label = QLabel("Max: 65535")
        value_layout.addWidget(self.value_label)
        value_layout.addStretch()
        value_layout.addWidget(self.min_label)
        value_layout.addStretch()
        value_layout.addWidget(self.max_label)
        layout.addLayout(value_layout)
        
        # Register fields to be updated by the wizard
        self.registerField(f"{pedal_name}_min*", self.min_label, "text")
        self.registerField(f"{pedal_name}_max*", self.max_label, "text")
        self.registerField(f"{pedal_name}_axis*", self.status, "text") # Using status to store axis info temporarily

        # Timer for input updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_input)
        self.timer.start(50) # 20 Hz

    def initializePage(self):
        """Called when the page is shown."""
        logger.info(f"Initializing page for {self.pedal_name}")
        self.calibration_stage = "detect_axis"
        self.detected_axis = -1
        self.min_value = 0
        self.max_value = 65535
        self.instructions.setText(f"Press and release the {self.pedal_name} pedal several times to detect its axis.")
        self.status.setText("Status: Waiting for pedal movement...")
        self.progress_bar.setValue(0)
        self.value_label.setText("Current: 0")
        self.min_label.setText("Min: 0")
        self.max_label.setText("Max: 65535")
        self.last_significant_value = 0 # Reset last significant value

    def cleanupPage(self):
        """Called when leaving the page."""
        logger.info(f"Cleaning up page for {self.pedal_name}")
        self.timer.stop()

    def update_input(self):
        """Read hardware input and update UI."""
        # Access attributes directly from self.hardware_input
        if not self.hardware_input or not self.hardware_input.joystick:
            self.status.setText("Status: Joystick not connected.")
            return
            
        pygame.event.pump() # Update pygame events
        joystick = self.hardware_input.joystick
        
        try:
            current_raw_values = [int((joystick.get_axis(i) + 1) * 32767.5) for i in range(joystick.get_numaxes())]
        except pygame.error as e:
            logger.error(f"Pygame error reading axes: {e}")
            self.status.setText("Status: Error reading joystick.")
            return

        if self.calibration_stage == "detect_axis":
            # Simple detection: find axis with largest change from center (32767)
            max_deviation = 0
            detected_axis = -1
            for i, val in enumerate(current_raw_values):
                 # Ignore axes near center
                deviation = abs(val - 32767)
                if deviation > 5000 and deviation > max_deviation: # Require significant initial deviation
                     max_deviation = deviation
                     detected_axis = i
                     
            if detected_axis != -1:
                 self.detected_axis = detected_axis
                 self.status.setText(f"Status: Axis {self.detected_axis} detected. Press Next.")
                 self.calibration_stage = "set_min"
                 self.instructions.setText(f"Release the {self.pedal_name} pedal completely, then press Next.")
                 # Update progress bar for the detected axis
                 self.current_value = current_raw_values[self.detected_axis]
                 self.progress_bar.setValue(self.current_value)
                 self.value_label.setText(f"Current: {self.current_value}")
                 self.setField(f"{self.pedal_name}_axis", f"Axis {self.detected_axis}") # Store detected axis info
                 self.completeChanged.emit() # Enable Next button

        elif self.calibration_stage in ["set_min", "set_max"]:
            if self.detected_axis == -1 or self.detected_axis >= len(current_raw_values):
                self.status.setText("Status: Axis detection lost. Go back and try again.")
                return 
                
            self.current_value = current_raw_values[self.detected_axis]
            self.progress_bar.setValue(self.current_value)
            self.value_label.setText(f"Current: {self.current_value}")

            if self.calibration_stage == "set_min":
                 # Min value is captured when user clicks Next
                 pass # Value is read in validatePage
            elif self.calibration_stage == "set_max":
                 # Max value is captured when user clicks Next
                 pass # Value is read in validatePage

    def isComplete(self):
        """Enable Next button only when an axis is detected or min/max is set."""
        return self.calibration_stage != "detect_axis"

    def validatePage(self):
        """Called when clicking Next."""
        if self.calibration_stage == "set_min":
            # Capture the current value as the minimum
            self.min_value = self.current_value
            self.min_label.setText(f"Min: {self.min_value}")
            self.setField(f"{self.pedal_name}_min", self.min_value) # Store min value
            logger.info(f"{self.pedal_name} Min value set to: {self.min_value}")
            # Proceed to set max stage
            self.calibration_stage = "set_max"
            self.instructions.setText(f"Press the {self.pedal_name} pedal fully down, then press Next.")
            self.completeChanged.emit() # Keep Next enabled
            return False # Stay on this page to set max

        elif self.calibration_stage == "set_max":
            # Capture the current value as the maximum
            self.max_value = self.current_value
            # Basic validation: max should be greater than min
            if self.max_value <= self.min_value:
                 QMessageBox.warning(self, "Calibration Error", "Maximum value must be greater than minimum value. Please press the pedal fully.")
                 return False # Stay on page
                 
            self.max_label.setText(f"Max: {self.max_value}")
            self.setField(f"{self.pedal_name}_max", self.max_value) # Store max value
            logger.info(f"{self.pedal_name} Max value set to: {self.max_value}")
            self.instructions.setText(f"{self.pedal_name} calibration complete!")
            # Proceed to the next page (implicitly by returning True)
            return True
        
        # If still in detect_axis stage, Next shouldn't be enabled, but handle just in case
        elif self.calibration_stage == "detect_axis":
            QMessageBox.warning(self, "Axis Not Detected", "Please press and release the pedal until an axis is detected.")
            return False
            
        return True # Should not be reached


class ThrottlePage(BasePedalPage):
    """Calibration page for the throttle pedal."""
    def __init__(self, hardware_input, parent=None):
        super().__init__("throttle", hardware_input, parent)

    def nextId(self):
        """Return the ID of the next page."""
        return CalibrationWizard.PAGE_BRAKE


class BrakePage(BasePedalPage):
    """Calibration page for the brake pedal."""
    def __init__(self, hardware_input, parent=None):
        super().__init__("brake", hardware_input, parent)

    def nextId(self):
        """Return the ID of the next page."""
        return CalibrationWizard.PAGE_CLUTCH


class ClutchPage(BasePedalPage):
    """Calibration page for the clutch pedal."""
    def __init__(self, hardware_input, parent=None):
        super().__init__("clutch", hardware_input, parent)
        
    def nextId(self):
        """Return the ID of the next page."""
        return CalibrationWizard.PAGE_FINISH


class FinishPage(QWizardPage):
    """Final page summarizing the calibration."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Calibration Complete")
        
        layout = QVBoxLayout(self)
        self.summary_label = QLabel("Calibration Summary:\n")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

    def initializePage(self):
        """Show the summary of calibration results."""
        throttle_min = self.field("throttle_min")
        throttle_max = self.field("throttle_max")
        throttle_axis = self.field("throttle_axis")
        
        brake_min = self.field("brake_min")
        brake_max = self.field("brake_max")
        brake_axis = self.field("brake_axis")
        
        clutch_min = self.field("clutch_min")
        clutch_max = self.field("clutch_max")
        clutch_axis = self.field("clutch_axis")
        
        summary = "Calibration Summary:\n\n"
        summary += f"Throttle: {throttle_axis}, Min={throttle_min}, Max={throttle_max}\n"
        summary += f"Brake:    {brake_axis}, Min={brake_min}, Max={brake_max}\n"
        summary += f"Clutch:   {clutch_axis}, Min={clutch_min}, Max={clutch_max}\n\n"
        summary += "Click 'Finish' to save these settings."
        
        self.summary_label.setText(summary)

    def nextId(self):
        """No next page after finish."""
        return -1

# Now define the Wizard itself
class CalibrationWizard(QWizard):
    """Wizard for calibrating pedals."""
    
    # Define page IDs (makes nextId easier)
    PAGE_INTRO = 0
    PAGE_THROTTLE = 1
    PAGE_BRAKE = 2
    PAGE_CLUTCH = 3
    PAGE_FINISH = 4
    
    calibration_complete = pyqtSignal(dict)
    
    def __init__(self, hardware_input, parent=None):
        """Initialize the calibration wizard."""
        super().__init__(parent)
        
        self.hardware_input = hardware_input
        self.setWindowTitle("Pedal Calibration Wizard")
        
        # Store calibration results (to be populated in handle_finish)
        self.calibration_results = {}
        
        # Set a more modern style with reduced padding
        self.setWizardStyle(QWizard.ModernStyle)
        
        # Customize wizard options to reduce padding and improve layout
        self.setOption(QWizard.IndependentPages, True)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.HaveFinishButtonOnEarlyPages, False)
        self.setOption(QWizard.NoCancelButton, False)
        self.setOption(QWizard.NoDefaultButton, False)
        
        # Remove the header/banner area entirely
        self.setPixmap(QWizard.BannerPixmap, QPixmap())
        self.setPixmap(QWizard.LogoPixmap, QPixmap())
        self.setPixmap(QWizard.WatermarkPixmap, QPixmap())
        self.setTitleFormat(Qt.PlainText)
        self.setSubTitleFormat(Qt.PlainText)
        
        # Set a dark background for the wizard
        self.setStyleSheet("""
            QWizard {
                background-color: #2d2d2d;
            }
            QWizardPage {
                background-color: #2d2d2d;
                margin: 0;
                padding: 0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #505050;
                border-radius: 4px;
                padding: 5px 15px;
                margin: 2px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
            QPushButton#qt_wizard_finish {
                background-color: #2a82da;
                font-weight: bold;
            }
            QPushButton#qt_wizard_finish:hover {
                background-color: #3a92ea;
            }
            QPushButton#qt_wizard_next {
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #505050;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
                width: 10px;
            }
            /* Hide title bar elements */
            QLabel#qt_title_label { 
                font-size: 0px;
                max-height: 0px;
                padding: 0px;
                margin: 0px;
            }
            QFrame#qt_title_bar { 
                max-height: 0px;
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # Create and add pages (QWizard manages layout and display)
        self.addPage(IntroPage())
        self.addPage(ThrottlePage(self.hardware_input))
        self.addPage(BrakePage(self.hardware_input))
        self.addPage(ClutchPage(self.hardware_input))
        self.addPage(FinishPage())
        
        # Connect the finished signal to our handler
        self.finished.connect(self.handle_finish)
        
        # Set initial window properties
        self.resize(520, 340)  # Smaller, more compact size
        self.setMinimumSize(400, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def handle_finish(self, result):
        """Handle wizard completion."""
        if result == QWizard.Accepted:
            logger.info("Calibration wizard finished by user.")
            # Extract results from fields
            try:
                # Helper to safely extract field value, return None if error
                def get_field_value(name):
                    try:
                        # Need to access field from the specific page where it was registered
                        # This approach might be problematic. QWizard fields are global.
                        return self.field(name) 
                    except Exception as e:
                        logger.error(f"Error getting field '{name}': {e}")
                        return None

                # Helper to parse axis number from status text (e.g., "Status: Axis 2 detected...")
                def parse_axis(axis_text):
                    if not axis_text or not isinstance(axis_text, str):
                        return -1 # Default or error value
                    try:
                        parts = axis_text.split()
                        # Find index of "Axis" and get the next part
                        axis_index = -1
                        for i, part in enumerate(parts):
                            if part == "Axis":
                                axis_index = i
                                break
                        if axis_index != -1 and axis_index + 1 < len(parts):
                            return int(parts[axis_index + 1])
                        else:
                             logger.warning(f"Could not find 'Axis' number in text: {axis_text}")
                             return -1
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse axis from text: {axis_text}")
                        return -1 # Default or error value

                # Extract values (using the field names registered in BasePedalPage)
                throttle_min_str = get_field_value("throttle_min")
                throttle_max_str = get_field_value("throttle_max")
                throttle_axis_text = get_field_value("throttle_axis")
                
                brake_min_str = get_field_value("brake_min")
                brake_max_str = get_field_value("brake_max")
                brake_axis_text = get_field_value("brake_axis")

                clutch_min_str = get_field_value("clutch_min")
                clutch_max_str = get_field_value("clutch_max")
                clutch_axis_text = get_field_value("clutch_axis")

                # Safely convert min/max from string ("Min: 123") to int
                def parse_min_max(label_text):
                    if not label_text or not isinstance(label_text, str):
                        return None
                    try:
                        return int(label_text.split(':')[-1].strip())
                    except (ValueError, IndexError):
                         logger.warning(f"Could not parse min/max value from: {label_text}")
                         return None

                throttle_min = parse_min_max(throttle_min_str)
                throttle_max = parse_min_max(throttle_max_str)
                throttle_axis = parse_axis(throttle_axis_text)

                brake_min = parse_min_max(brake_min_str)
                brake_max = parse_min_max(brake_max_str)
                brake_axis = parse_axis(brake_axis_text)

                clutch_min = parse_min_max(clutch_min_str)
                clutch_max = parse_min_max(clutch_max_str)
                clutch_axis = parse_axis(clutch_axis_text)

                # Update results dictionary (ensure values are not None)
                self.calibration_results = {
                    'throttle': {
                        'min': throttle_min if throttle_min is not None else 0,
                        'max': throttle_max if throttle_max is not None else 65535,
                        'axis': throttle_axis
                    },
                    'brake': {
                        'min': brake_min if brake_min is not None else 0,
                        'max': brake_max if brake_max is not None else 65535,
                        'axis': brake_axis
                    },
                    'clutch': {
                        'min': clutch_min if clutch_min is not None else 0,
                        'max': clutch_max if clutch_max is not None else 65535,
                        'axis': clutch_axis
                    }
                }
                logger.info(f"Extracted calibration results: {self.calibration_results}")
                
                # Call the save method (which now needs to use self.calibration_results)
                self.save_calibration()
                
                # Emit signal with the processed results
                self.calibration_complete.emit(self.calibration_results)

            except Exception as e:
                 logger.error(f"Error processing calibration results: {e}", exc_info=True)
                 QMessageBox.critical(self, "Error", f"Failed to process calibration results: {e}")
        else:
             logger.info("Calibration wizard cancelled by user.")
             
    def save_calibration(self):
        """Save the current calibration collected in handle_finish."""
        # This method should now use self.calibration_results instead of self.results
        # Ensure self.calibration_results is populated before calling this
        if not self.calibration_results:
            logger.error("save_calibration called before results were processed.")
            return
            
        try:
            # Use self.hardware_input directly
            if self.hardware_input:
                # Update axis ranges in hardware
                for pedal, data in self.calibration_results.items():
                    if not isinstance(data, dict): continue # Skip if data format is wrong
                    
                    # Get existing deadzones to preserve them
                    existing_ranges = self.hardware_input.axis_ranges.get(pedal, {})
                    min_deadzone = existing_ranges.get('min_deadzone', 0)
                    max_deadzone = existing_ranges.get('max_deadzone', 0)
                    
                    # Update range data, keeping existing deadzones
                    self.hardware_input.axis_ranges[pedal] = {
                        'min': data.get('min', 0),
                        'max': data.get('max', 65535),
                        'min_deadzone': min_deadzone,
                        'max_deadzone': max_deadzone,
                        'axis': data.get('axis', -1) # Store axis mapping here too
                    }
                
                # Save the updated ranges (which now includes axis mapping)
                self.hardware_input.save_axis_ranges()
                logger.info(f"Saved axis ranges: {self.hardware_input.axis_ranges}")
                
                # The old save_calibration call on hardware_input might be redundant
                # if axis ranges contain all necessary info. Check HardwareInput.save_calibration()
                # self.hardware_input.save_calibration(self.calibration_results) # Pass the correct results
                
                # Show success message (moved from old save_calibration)
                if supabase.is_authenticated():
                    QMessageBox.information(
                        self, "Calibration Saved",
                        "Calibration saved successfully and synced to cloud!"
                    )
                else:
                    QMessageBox.information(
                        self, "Calibration Saved",
                        "Calibration saved successfully! Sign in to enable cloud sync."
                    )
            else:
                logger.warning("Cannot save calibration: hardware_input not available")
                QMessageBox.warning(
                    self, "Save Failed", "Hardware interface not accessible."
                )
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Save Failed", f"Failed to save calibration: {str(e)}"
            )

    # Override showEvent to further customize the wizard's appearance when shown
    def showEvent(self, event):
        super().showEvent(event)
        
        # Find and adjust the title bar if it exists
        title_bar = self.findChild(QFrame, "qt_title_bar")
        if title_bar:
            title_bar.setMaximumHeight(0)
            title_bar.setVisible(False)

    # Removed setup_dark_theme
    # Removed create_welcome_page
    # Removed create_pedal_page
    # Removed create_throttle_page
    # Removed create_brake_page
    # Removed create_clutch_page
    # Removed create_finish_page
    # Removed go_next (use super().next() if needed, QWizard handles it)
    # Removed go_back (use super().back() if needed, QWizard handles it)
    # Removed update_navigation_buttons (QWizard handles it)
    # Removed initialize_pedal_calibration (logic moved to BasePedalPage.initializePage)
    # Removed finalize_pedal_calibration (logic moved to BasePedalPage.validatePage)
    # Removed update_summary (logic moved to FinishPage.initializePage)
    # Removed show_all_axes (needs reimplementation in BasePedalPage if desired)
    # Removed update_inputs (logic moved to BasePedalPage.update_input) 