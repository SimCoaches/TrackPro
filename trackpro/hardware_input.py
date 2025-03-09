import pygame
import logging
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox
import datetime

logger = logging.getLogger(__name__)

class HardwareInput:
    def __init__(self, test_mode=False):
        """Initialize hardware input handling."""
        pygame.init()
        pygame.joystick.init()
        
        # Connection status flags
        self.joystick = None
        self.pedals_connected = False
        
        # Find our pedal device
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            if "Sim Coaches P1 Pro Pedals" in joy.get_name():
                self.joystick = joy
                self.pedals_connected = True
                logger.info(f"Found P1 Pro Pedals: {joy.get_name()}")
                break
        
        if not self.pedals_connected:
            logger.warning("P1 Pro Pedals not connected. Running in fallback mode.")
            
            # Setup mock values for when no pedals are connected
            self.available_axes = 3
            self.axis_values = [0.0, 0.0, 0.0]  # Default values for throttle, brake, clutch
        else:
            self.available_axes = self.joystick.get_numaxes()
            logger.info(f"Detected {self.available_axes} axes on the pedals")
        
        # Load calibration data
        self.calibration = self._load_calibration()
        
        # Load axis mappings
        self.axis_mappings = self._load_axis_mappings()
        
        # Default axis mappings if not loaded
        if not self.axis_mappings:
            self.axis_mappings = {
                'Throttle': 0,
                'Brake': 1,
                'Clutch': 2
            }
        
        # Validate axis mappings against available axes
        self._validate_axis_mappings()
        
        # Set axis properties based on mappings
        self.THROTTLE_AXIS = self.axis_mappings.get('Throttle', -1)
        self.BRAKE_AXIS = self.axis_mappings.get('Brake', -1)
        self.CLUTCH_AXIS = self.axis_mappings.get('Clutch', -1)
        
        # Initialize last known values
        self.last_values = {
            'Throttle': 0,
            'Brake': 0,
            'Clutch': 0
        }
        
        # Initialize pedal values
        self.pedal_values = {
            'Throttle': 0,
            'Brake': 0,
            'Clutch': 0
        }
        
        # Initialize axis ranges (will be calibrated)
        self.axis_ranges = {
            'Throttle': {'min': 0, 'max': 65535},
            'Brake': {'min': 0, 'max': 65535},
            'Clutch': {'min': 0, 'max': 65535}
        }
        
        # Load or calibrate axis ranges
        self._init_axis_ranges()
        
        # Create default curve presets if they don't exist
        self._create_default_curve_presets()

    def _validate_axis_mappings(self):
        """Validate axis mappings against available axes and adjust if needed."""
        valid_mappings = {}
        for pedal, axis in self.axis_mappings.items():
            if axis < self.available_axes:
                valid_mappings[pedal] = axis
            else:
                logger.warning(f"{pedal.capitalize()} axis {axis} is not available (device has {self.available_axes} axes)")
                # Set to -1 to indicate unavailable
                valid_mappings[pedal] = -1
        
        self.axis_mappings = valid_mappings
        # Save the validated mappings
        self.save_axis_mappings()

    def _init_axis_ranges(self):
        """Initialize or load axis ranges."""
        try:
            # Try to load saved ranges
            cal_file = self._get_calibration_file().parent / "axis_ranges.json"
            if cal_file.exists():
                with open(cal_file) as f:
                    self.axis_ranges = json.load(f)
                logger.info("Loaded axis ranges from file")
            else:
                # Perform initial range detection
                self._calibrate_ranges()
                
        except Exception as e:
            logger.warning(f"Failed to initialize axis ranges: {e}")
            self._calibrate_ranges()

    def _calibrate_ranges(self):
        """Calibrate the axis ranges by reading current values."""
        if not self.pedals_connected:
            # If pedals not connected, use default ranges
            for axis_name in ['Throttle', 'Brake', 'Clutch']:
                self.axis_ranges[axis_name] = {
                    'min': 0,
                    'max': 65535,
                    'min_deadzone': 0,  # Default to no deadzone
                    'max_deadzone': 0   # Default to no deadzone
                }
            logger.info("Using default axis ranges in fallback mode")
            return
            
        # Pedals are connected, attempt to detect ranges
        try:
            pygame.event.pump()
            
            # Read initial values
            raw_values = {}
            for i in range(self.available_axes):
                raw_values[i] = self.joystick.get_axis(i)
            
            # Monitor changes over time to determine which axis maps to which pedal
            for _ in range(5):  # Read a few times to get stable readings
                pygame.event.pump()
                
                for i in range(self.available_axes):
                    value = self.joystick.get_axis(i)
                    # Convert from -1 to 1 range to 0-65535 range
                    scaled_value = int((value + 1) * 32767)
                    
                    # If this is a new axis in axis_ranges, initialize it
                    for axis_name in ['Throttle', 'Brake', 'Clutch']:
                        axis_idx = self.axis_mappings.get(axis_name, -1)
                        if axis_idx == i:
                            if axis_name not in self.axis_ranges:
                                self.axis_ranges[axis_name] = {
                                    'min': scaled_value,
                                    'max': scaled_value,
                                    'min_deadzone': 0,  # Default to no deadzone
                                    'max_deadzone': 0   # Default to no deadzone
                                }
                            else:
                                # Update existing entry
                                self.axis_ranges[axis_name] = {
                                    'min': min(scaled_value, self.axis_ranges[axis_name]['min']),
                                    'max': max(scaled_value, self.axis_ranges[axis_name]['max']),
                                    'min_deadzone': self.axis_ranges[axis_name].get('min_deadzone', 0),
                                    'max_deadzone': self.axis_ranges[axis_name].get('max_deadzone', 0)
                                }
                
                # Small delay for readability in debug output
                # If we wait too long, the initialization process will be slower
                # If we don't wait at all, we might get redundant readings
                # 50ms is a good compromise that still gives meaningful readings
                # pygame.time.wait(50) # Commented out to make initialization faster
                
            # Ensure all pedals have range data
            for axis_name in ['Throttle', 'Brake', 'Clutch']:
                if axis_name not in self.axis_ranges:
                    self.axis_ranges[axis_name] = {
                        'min': 0,
                        'max': 65535,
                        'min_deadzone': 0,  # Default to no deadzone
                        'max_deadzone': 0   # Default to no deadzone
                    }
            
            self.save_axis_ranges()
            logger.info(f"Calibrated axis ranges: {self.axis_ranges}")
                
        except Exception as e:
            logger.error(f"Error during calibration: {e}")
            # If error occurs, set default ranges
            for axis_name in ['Throttle', 'Brake', 'Clutch']:
                self.axis_ranges[axis_name] = {
                    'min': 0,
                    'max': 65535,
                    'min_deadzone': 0,  # Default to no deadzone
                    'max_deadzone': 0   # Default to no deadzone
                }
            logger.warning("Using default axis ranges due to calibration error")

    def save_axis_ranges(self):
        """Save axis ranges to file."""
        try:
            cal_file = self._get_calibration_file().parent / "axis_ranges.json"
            with open(cal_file, 'w') as f:
                json.dump(self.axis_ranges, f)
            logger.info("Saved axis ranges")
        except Exception as e:
            logger.error(f"Failed to save axis ranges: {e}")

    def _get_calibration_file(self) -> Path:
        """Get path to calibration file."""
        config_dir = Path.home() / ".trackpro"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "calibration.json"

    def _get_curves_directory(self) -> Path:
        """Get path to the curves directory."""
        config_dir = Path.home() / ".trackpro" / "curves"
        config_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for each pedal
        for pedal in ['Throttle', 'Brake', 'Clutch']:
            pedal_dir = config_dir / pedal
            pedal_dir.mkdir(exist_ok=True)
        
        return config_dir

    def get_pedal_curves_directory(self, pedal: str) -> Path:
        """Get the directory for a specific pedal's curves."""
        return self._get_curves_directory() / pedal

    def list_available_curves(self, pedal: str) -> list:
        """List all available curves for a specific pedal."""
        try:
            curves_dir = self.get_pedal_curves_directory(pedal)
            logger.info(f"Looking for curves in directory: {curves_dir}")
            
            # Ensure the directory exists
            if not curves_dir.exists():
                logger.warning(f"Curves directory does not exist: {curves_dir}")
                curves_dir.mkdir(exist_ok=True, parents=True)
                logger.info(f"Created curves directory: {curves_dir}")
                return []
            
            # Get all JSON files in the directory
            curve_files = list(curves_dir.glob("*.json"))
            logger.info(f"Found {len(curve_files)} curve files: {[f.name for f in curve_files]}")
            
            # Validate each curve file to ensure it's readable
            valid_curves = []
            for file in curve_files:
                try:
                    # Skip temporary files
                    if ".tmp." in file.name:
                        logger.debug(f"Skipping temporary file: {file.name}")
                        continue
                        
                    with open(file) as f:
                        try:
                            # Try to parse the JSON
                            content = f.read()
                            
                            # Check for corrupted files with multiple JSON objects
                            if content.count('"name"') > 1:
                                logger.warning(f"Detected corrupted curve file with multiple JSON objects: {file}")
                                # Try to fix the file
                                try:
                                    # Find the first complete JSON object
                                    first_brace = content.find('{')
                                    if first_brace >= 0:
                                        # Find the matching closing brace
                                        brace_count = 0
                                        for i, char in enumerate(content[first_brace:]):
                                            if char == '{':
                                                brace_count += 1
                                            elif char == '}':
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    # We found the end of the first complete JSON object
                                                    valid_json = content[first_brace:first_brace+i+1]
                                                    curve_data = json.loads(valid_json)
                                                    
                                                    # Save the fixed file
                                                    with open(file, 'w') as fix_file:
                                                        json.dump(curve_data, fix_file, indent=2)
                                                    
                                                    logger.info(f"Fixed corrupted curve file: {file}")
                                                    
                                                    # Add to valid curves
                                                    valid_curves.append(file.stem)
                                                    logger.info(f"Added fixed curve: {file.stem}")
                                                    break
                                except Exception as fix_error:
                                    logger.error(f"Failed to fix corrupted curve file: {fix_error}")
                                continue
                                
                            # Parse the JSON
                            curve_data = json.loads(content)
                            
                            # Validate basic structure
                            if not isinstance(curve_data, dict) or 'name' not in curve_data or 'points' not in curve_data:
                                logger.warning(f"Skipping invalid curve file (missing required fields): {file}")
                                continue
                                
                            # Add to valid curves
                            valid_curves.append(file.stem)
                            logger.debug(f"Validated curve file: {file.name}")
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON in curve file: {file}")
                            continue
                except Exception as e:
                    logger.warning(f"Error reading curve file {file}: {e}")
                    continue
            
            logger.info(f"Found {len(valid_curves)} valid curves for {pedal}: {valid_curves}")
            return sorted(valid_curves)
        except Exception as e:
            logger.error(f"Error listing available curves: {e}", exc_info=True)
            return []

    def save_custom_curve(self, pedal: str, name: str, points: list, curve_type: str = "Custom") -> bool:
        """Save a custom curve for a specific pedal."""
        try:
            # Sanitize the name to be a valid filename
            safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
            if not safe_name:
                safe_name = "Unnamed"
                logger.warning(f"Invalid curve name '{name}', using '{safe_name}' instead")
            
            curves_dir = self.get_pedal_curves_directory(pedal)
            logger.info(f"Saving curve '{name}' to directory: {curves_dir}")
            
            # Ensure the directory exists
            if not curves_dir.exists():
                logger.warning(f"Curves directory does not exist: {curves_dir}")
                curves_dir.mkdir(exist_ok=True, parents=True)
                logger.info(f"Created curves directory: {curves_dir}")
            
            curve_file = curves_dir / f"{safe_name}.json"
            logger.info(f"Curve will be saved to: {curve_file}")
            
            # Validate points data
            if not isinstance(points, list) or len(points) < 2:
                logger.error(f"Invalid points data for curve '{name}': {points}")
                return False
            
            # Ensure all points are valid (x,y) pairs
            valid_points = []
            for point in points:
                if isinstance(point, (list, tuple)) and len(point) == 2:
                    x, y = point
                    try:
                        # Convert to float to ensure they're numeric
                        x_float = float(x)
                        y_float = float(y)
                        valid_points.append([x_float, y_float])
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping invalid point in curve '{name}': {point}")
                else:
                    logger.warning(f"Skipping invalid point format in curve '{name}': {point}")
            
            if len(valid_points) < 2:
                logger.error(f"Not enough valid points for curve '{name}' after validation")
                return False
            
            # Create curve data
            curve_data = {
                "name": name,
                "points": valid_points,
                "curve_type": curve_type
            }
            
            # Save to file - use a temporary file first to avoid corruption
            temp_file = curves_dir / f"{safe_name}.tmp.json"
            try:
                with open(temp_file, 'w') as f:
                    json.dump(curve_data, f, indent=2)
                
                # If successful, rename to the final filename
                if temp_file.exists():
                    # Remove existing file if it exists
                    if curve_file.exists():
                        curve_file.unlink()
                    temp_file.rename(curve_file)
            except Exception as e:
                logger.error(f"Error writing curve file: {e}")
                if temp_file.exists():
                    temp_file.unlink()  # Clean up temp file
                return False
            
            # Verify the file was created
            if curve_file.exists():
                file_size = curve_file.stat().st_size
                logger.info(f"Successfully saved curve '{name}' to {curve_file} ({file_size} bytes)")
                
                # Verify the file can be read back
                try:
                    with open(curve_file) as f:
                        test_data = json.load(f)
                    if 'points' in test_data and len(test_data['points']) == len(valid_points):
                        logger.info(f"Verified curve file '{name}' can be read back successfully")
                    else:
                        logger.warning(f"Curve file '{name}' was saved but verification failed")
                except Exception as verify_error:
                    logger.warning(f"Curve file '{name}' was saved but verification failed: {verify_error}")
                
                return True
            else:
                logger.error(f"Failed to save curve: File {curve_file} does not exist after save attempt")
                return False
        except Exception as e:
            logger.error(f"Failed to save custom curve: {e}", exc_info=True)
            return False

    def load_custom_curve(self, pedal: str, name: str) -> dict:
        """Load a custom curve for a specific pedal."""
        try:
            curves_dir = self.get_pedal_curves_directory(pedal)
            curve_file = curves_dir / f"{name}.json"
            
            logger.info(f"Attempting to load curve '{name}' from {curve_file}")
            
            if not curve_file.exists():
                logger.warning(f"Custom curve '{name}' not found for {pedal}")
                return None
            
            try:
                with open(curve_file) as f:
                    file_content = f.read()
                    
                    # Check for duplicate JSON objects (corrupted file)
                    if file_content.count('"name"') > 1:
                        logger.warning(f"Detected corrupted curve file with multiple JSON objects: {curve_file}")
                        
                        # Try to extract just the first valid JSON object
                        try:
                            # Find the first complete JSON object
                            first_brace = file_content.find('{')
                            if first_brace >= 0:
                                # Find the matching closing brace
                                brace_count = 0
                                for i, char in enumerate(file_content[first_brace:]):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            # We found the end of the first complete JSON object
                                            valid_json = file_content[first_brace:first_brace+i+1]
                                            curve_data = json.loads(valid_json)
                                            
                                            # Save the fixed file
                                            with open(curve_file, 'w') as fix_file:
                                                json.dump(curve_data, fix_file, indent=2)
                                            
                                            logger.info(f"Fixed corrupted curve file: {curve_file}")
                                            break
                        except Exception as fix_error:
                            logger.error(f"Failed to fix corrupted curve file: {fix_error}")
                            return None
                    else:
                        # Normal case - parse the JSON directly
                        curve_data = json.loads(file_content)
            except json.JSONDecodeError as json_error:
                logger.error(f"Invalid JSON in curve file {curve_file}: {json_error}")
                return None
            
            # Validate the curve data
            if not isinstance(curve_data, dict):
                logger.error(f"Invalid curve data format in {curve_file}: not a dictionary")
                return None
            
            if 'points' not in curve_data:
                logger.error(f"Invalid curve data in {curve_file}: missing 'points' key")
                return None
            
            if not isinstance(curve_data['points'], list):
                logger.error(f"Invalid curve data in {curve_file}: 'points' is not a list")
                return None
            
            logger.info(f"Loaded custom curve '{name}' for {pedal}: {len(curve_data.get('points', []))} points, type: {curve_data.get('curve_type', 'Unknown')}")
            return curve_data
        except Exception as e:
            logger.error(f"Failed to load custom curve: {e}", exc_info=True)
            return None

    def delete_custom_curve(self, pedal: str, name: str) -> bool:
        """Delete a custom curve for a specific pedal."""
        try:
            curves_dir = self.get_pedal_curves_directory(pedal)
            curve_file = curves_dir / f"{name}.json"
            
            logger.info(f"Attempting to delete curve '{name}' from {curve_file}")
            
            if not curve_file.exists():
                logger.warning(f"Custom curve '{name}' not found for {pedal}")
                return False
            
            curve_file.unlink()
            logger.info(f"Deleted custom curve '{name}' for {pedal}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete custom curve: {e}", exc_info=True)
            return False

    def apply_curve_to_calibration(self, pedal: str, curve_name: str) -> bool:
        """Apply a custom curve to the current calibration.
        
        Args:
            pedal: The pedal name ('Throttle', 'Brake', 'Clutch')
            curve_name: The name of the custom curve
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            curve_data = self.load_custom_curve(pedal, curve_name)
            if not curve_data:
                return False
            
            # Update calibration with the loaded curve
            self.calibration[pedal] = {
                'points': curve_data['points'],
                'curve': curve_data['curve_type']
            }
            
            # Save the updated calibration
            self.save_calibration(self.calibration)
            
            logger.info(f"Applied custom curve '{curve_name}' to {pedal}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply custom curve: {e}")
            return False

    def _get_axis_mappings_file(self) -> Path:
        """Get path to axis mappings file."""
        config_dir = Path.home() / ".trackpro"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "axis_mappings.json"

    def _load_calibration(self) -> dict:
        """Load calibration data from file or return defaults."""
        try:
            cal_file = self._get_calibration_file()
            if cal_file.exists():
                with open(cal_file) as f:
                    calibration = json.load(f)
                
                # Handle transition from lowercase to capitalized pedal names
                updated_calibration = {}
                for key, value in calibration.items():
                    # Convert lowercase keys to capitalized
                    if key in ['throttle', 'brake', 'clutch']:
                        updated_key = key.capitalize()
                        updated_calibration[updated_key] = value
                    else:
                        updated_calibration[key] = value
                
                # If we made changes, save the updated calibration
                if updated_calibration != calibration:
                    self.save_calibration(updated_calibration)
                    calibration = updated_calibration
                
                return calibration
        except Exception as e:
            logger.warning(f"Failed to load calibration: {e}")
            
        # Return default calibration
        return {
            'Throttle': {'points': [], 'curve': 'Linear'},
            'Brake': {'points': [], 'curve': 'Linear'},
            'Clutch': {'points': [], 'curve': 'Linear'}
        }
    
    def _load_axis_mappings(self) -> dict:
        """Load axis mappings from file or return defaults."""
        try:
            mappings_file = self._get_axis_mappings_file()
            if mappings_file.exists():
                with open(mappings_file) as f:
                    mappings = json.load(f)
                
                # Handle transition from lowercase to capitalized pedal names
                updated_mappings = {}
                for key, value in mappings.items():
                    # Convert lowercase keys to capitalized
                    if key in ['throttle', 'brake', 'clutch']:
                        updated_key = key.capitalize()
                        updated_mappings[updated_key] = value
                    else:
                        updated_mappings[key] = value
                
                # If we made changes, save the updated mappings
                if updated_mappings != mappings:
                    self.save_axis_mappings(updated_mappings)
                    mappings = updated_mappings
                
                logger.info(f"Loaded axis mappings: {mappings}")
                return mappings
        except Exception as e:
            logger.warning(f"Failed to load axis mappings: {e}")
            
        # Return default mappings
        return {
            'Throttle': 0,
            'Brake': 1,
            'Clutch': 2
        }
    
    def save_axis_mappings(self, mappings=None):
        """Save axis mappings to file."""
        if mappings is None:
            mappings = self.axis_mappings
        
        try:
            mappings_file = self._get_axis_mappings_file()
            with open(mappings_file, 'w') as f:
                json.dump(mappings, f)
            logger.info(f"Saved axis mappings: {mappings}")
        except Exception as e:
            logger.error(f"Failed to save axis mappings: {e}")
    
    def update_axis_mapping(self, pedal, axis):
        """Update the axis mapping for a pedal."""
        if pedal in self.axis_mappings:
            # Check if the axis is valid
            if axis >= self.available_axes:
                logger.warning(f"Cannot map {pedal} to axis {axis} - device only has {self.available_axes} axes")
                return False
                
            self.axis_mappings[pedal] = axis
            
            # Update the axis constants
            if pedal == 'Throttle':
                self.THROTTLE_AXIS = axis
            elif pedal == 'Brake':
                self.BRAKE_AXIS = axis
            elif pedal == 'Clutch':
                self.CLUTCH_AXIS = axis
            
            # Save the updated mappings
            self.save_axis_mappings()
            logger.info(f"Updated {pedal} axis mapping to {axis}")
            return True
        return False
    
    def save_calibration(self, calibration: dict):
        """Save calibration data to file."""
        try:
            cal_file = self._get_calibration_file()
            with open(cal_file, 'w') as f:
                json.dump(calibration, f)
            logger.info("Calibration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            raise
    
    def read_pedals(self):
        """Read current pedal values."""
        # Process events to get fresh values if pedals are connected
        if self.pedals_connected:
            pygame.event.pump()
        
        try:
            values = {
                'Throttle': 0,  # Initialize with defaults for all pedals
                'Brake': 0,
                'Clutch': 0
            }
            
            # Read and scale each axis
            for axis_name, axis_num in [
                ('Throttle', self.THROTTLE_AXIS),
                ('Brake', self.BRAKE_AXIS),
                ('Clutch', self.CLUTCH_AXIS)
            ]:
                # Skip unavailable axes
                if axis_num < 0 or axis_num >= self.available_axes:
                    values[axis_name] = 0  # Default value for unavailable axis
                    continue
                
                if not self.pedals_connected:
                    # When pedals not connected, use mock values
                    if hasattr(self, 'axis_values') and len(self.axis_values) > axis_num:
                        raw_value = self.axis_values[axis_num]
                    else:
                        # Default to zero if axis_values not properly initialized
                        raw_value = 0.0
                else:
                    # Get raw value (-1 to 1)
                    try:
                        raw_value = self.joystick.get_axis(axis_num)
                    except Exception as e:
                        logger.warning(f"Error reading {axis_name} axis: {e}, using 0.0")
                        raw_value = 0.0
                
                # Convert to 0-65535 range (16-bit)
                # Note: The hardware is 12-bit (0-4096), but we scale to 16-bit for better resolution
                # This is the RAW value that should be displayed in the UI
                scaled_value = int((raw_value + 1) * 32767)
                
                # Store the raw scaled value without applying calibration range
                values[axis_name] = scaled_value
            
            self.last_values = values
            return values
            
        except Exception as e:
            logger.error(f"Error reading pedal values: {e}")
            # If last_values is empty or not initialized, create default values
            if not hasattr(self, 'last_values') or not self.last_values:
                self.last_values = {
                    'Throttle': 0,
                    'Brake': 0,
                    'Clutch': 0
                }
            return self.last_values  # Return last known values on error
    
    def apply_calibration(self, pedal: str, raw_value: int) -> int:
        """Apply calibration to a raw pedal value."""
        # Get calibration data
        cal = self.calibration.get(pedal, {})
        points = cal.get('points', [])
        curve_type = cal.get('curve', 'Linear')
        
        # Get min/max range with defensive checks
        if pedal not in self.axis_ranges:
            # If pedal not in axis_ranges, initialize with default values
            self.axis_ranges[pedal] = {
                'min': 0,
                'max': 65535,
                'min_deadzone': 0,
                'max_deadzone': 0
            }
            logger.warning(f"Missing axis range for {pedal}, using defaults")
            
        axis_range = self.axis_ranges[pedal]
        input_min = axis_range.get('min', 0)
        input_max = axis_range.get('max', 65535)
        
        # Get deadzone values (default to 0 if not present for backward compatibility)
        min_deadzone = axis_range.get('min_deadzone', 0)
        max_deadzone = axis_range.get('max_deadzone', 0)
        
        # Calculate range size
        range_size = input_max - input_min
        
        # Normalize input value to 0-100 range (percentage)
        if input_max > input_min and range_size != 0:
            # Standard linear normalization - maintain linearity regardless of range size
            normalized = ((raw_value - input_min) / range_size) * 100
        else:
            normalized = (raw_value / 65535) * 100
            
        # Clamp to 0-100 range
        normalized = max(0.0, min(100.0, normalized))
        
        # Apply deadzone at minimum (if pedal is barely pressed, treat as not pressed)
        if normalized < min_deadzone:
            normalized = 0.0
        
        # Apply deadzone at maximum (if pedal is almost fully pressed, treat as fully pressed)
        if normalized > (100.0 - max_deadzone):
            normalized = 100.0
            
        # If between min_deadzone and (100 - max_deadzone), rescale to full range
        if min_deadzone > 0 or max_deadzone > 0:
            if normalized > 0 and normalized < 100:
                # Rescale the value between deadzones to use full range (0-100)
                usable_range = 100.0 - min_deadzone - max_deadzone
                if usable_range > 0:  # Prevent division by zero
                    normalized = ((normalized - min_deadzone) / usable_range) * 100.0
                    normalized = max(0.0, min(100.0, normalized))
        
        # Apply curve if we have calibration points
        if points:
            # Points are already in 0-100 percentage space from the UI
            norm_points = points
            norm_points.sort(key=lambda p: p[0])
            
            # Find surrounding points
            output_percentage = 0
            for i in range(len(norm_points)-1):
                if normalized <= norm_points[i+1][0]:
                    x1, y1 = norm_points[i]
                    x2, y2 = norm_points[i+1]
                    
                    # Linear interpolation between points
                    if x2 != x1:
                        t = (normalized - x1) / (x2 - x1)
                        output_percentage = y1 + t * (y2 - y1)
                    else:
                        output_percentage = y1
                    break
            else:
                # If we're beyond the last point, use the last point's y value
                if norm_points:
                    output_percentage = norm_points[-1][1]
        else:
            # No calibration points, use linear mapping
            output_percentage = normalized
        
        # Convert back to raw range (0-65535)
        output = int((output_percentage / 100) * 65535)
        output = max(0, min(65535, output))  # Ensure within valid range
        
        return output 

    def _create_default_curve_presets(self):
        """Create default curve presets for each pedal if they don't exist."""
        try:
            # Define default presets for each pedal
            default_presets = {
                'Throttle': [
                    {
                        'name': 'Racing',
                        'points': [(0, 0), (25, 10), (50, 30), (75, 60), (100, 100)],
                        'curve_type': 'Racing'
                    },
                    {
                        'name': 'Smooth',
                        'points': [(0, 0), (25, 35), (50, 65), (75, 85), (100, 100)],
                        'curve_type': 'Smooth'
                    },
                    {
                        'name': 'Aggressive',
                        'points': [(0, 0), (25, 5), (50, 15), (75, 40), (100, 100)],
                        'curve_type': 'Aggressive'
                    },
                    {
                        'name': 'Precision Control',
                        'points': [(0, 0), (20, 5), (40, 15), (60, 35), (80, 70), (100, 100)],
                        'curve_type': 'Precision Control'
                    },
                    {
                        'name': 'Traction Limited',
                        'points': [(0, 0), (25, 10), (50, 25), (75, 45), (90, 75), (100, 100)],
                        'curve_type': 'Traction Limited'
                    },
                    {
                        'name': 'Quick Response',
                        'points': [(0, 0), (15, 25), (40, 65), (60, 85), (100, 100)],
                        'curve_type': 'Quick Response'
                    },
                    {
                        'name': 'Rain Mode',
                        'points': [(0, 0), (25, 8), (50, 20), (75, 35), (90, 60), (100, 80)],
                        'curve_type': 'Rain Mode'
                    }
                ],
                'Brake': [
                    {
                        'name': 'Hard Braking',
                        'points': [(0, 0), (25, 40), (50, 70), (75, 90), (100, 100)],
                        'curve_type': 'Hard Braking'
                    },
                    {
                        'name': 'Progressive',
                        'points': [(0, 0), (25, 15), (50, 40), (75, 75), (100, 100)],
                        'curve_type': 'Progressive'
                    },
                    {
                        'name': 'ABS Simulation',
                        'points': [(0, 0), (25, 30), (50, 50), (75, 65), (100, 80)],
                        'curve_type': 'ABS Simulation'
                    },
                    {
                        'name': 'Trail Braking',
                        'points': [(0, 0), (15, 5), (30, 20), (50, 45), (70, 75), (85, 95), (100, 100)],
                        'curve_type': 'Trail Braking'
                    },
                    {
                        'name': 'Threshold Braking',
                        'points': [(0, 0), (20, 10), (40, 25), (60, 50), (80, 90), (90, 98), (100, 100)],
                        'curve_type': 'Threshold Braking'
                    },
                    {
                        'name': 'Wet Weather',
                        'points': [(0, 0), (20, 5), (40, 15), (60, 30), (80, 60), (100, 85)],
                        'curve_type': 'Wet Weather'
                    },
                    {
                        'name': 'Initial Bite',
                        'points': [(0, 0), (10, 20), (30, 45), (50, 65), (70, 80), (100, 100)],
                        'curve_type': 'Initial Bite'
                    }
                ],
                'Clutch': [
                    {
                        'name': 'Quick Engage',
                        'points': [(0, 0), (25, 60), (50, 85), (75, 95), (100, 100)],
                        'curve_type': 'Quick Engage'
                    },
                    {
                        'name': 'Gradual',
                        'points': [(0, 0), (25, 20), (50, 50), (75, 80), (100, 100)],
                        'curve_type': 'Gradual'
                    },
                    {
                        'name': 'Race Start',
                        'points': [(0, 0), (25, 40), (50, 70), (60, 85), (70, 95), (100, 100)],
                        'curve_type': 'Race Start'
                    },
                    {
                        'name': 'Slip Control',
                        'points': [(0, 0), (20, 10), (40, 30), (50, 60), (60, 80), (70, 95), (100, 100)],
                        'curve_type': 'Slip Control'
                    },
                    {
                        'name': 'Bite Point Focus',
                        'points': [(0, 0), (30, 20), (45, 40), (50, 70), (55, 90), (60, 95), (100, 100)],
                        'curve_type': 'Bite Point Focus'
                    },
                    {
                        'name': 'Drift Initiation',
                        'points': [(0, 0), (20, 30), (40, 75), (60, 90), (100, 100)],
                        'curve_type': 'Drift Initiation'
                    },
                    {
                        'name': 'Smooth Launch',
                        'points': [(0, 0), (15, 5), (30, 20), (45, 45), (60, 80), (75, 95), (100, 100)],
                        'curve_type': 'Smooth Launch'
                    }
                ]
            }
            
            # Check if presets already exist
            for pedal, presets in default_presets.items():
                existing_curves = self.list_available_curves(pedal)
                
                for preset in presets:
                    # Only create if it doesn't exist
                    if preset['name'] not in existing_curves:
                        self.save_custom_curve(
                            pedal=pedal,
                            name=preset['name'],
                            points=preset['points'],
                            curve_type=preset['curve_type']
                        )
                        logger.info(f"Created default '{preset['name']}' curve preset for {pedal}")
            
            logger.info("Default curve presets created")
        except Exception as e:
            logger.error(f"Failed to create default curve presets: {e}")

    def set_test_axis_value(self, axis, value):
        """Set a mock axis value for when pedals are not connected."""
        # Only allow setting values when pedals are not connected
        if not self.pedals_connected and 0 <= axis < self.available_axes:
            # Value should be between -1.0 and 1.0
            self.axis_values[axis] = max(-1.0, min(1.0, value))
            logger.debug(f"Set mock axis {axis} to {self.axis_values[axis]}")
            return True
        return False 