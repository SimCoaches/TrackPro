import pygame
import logging
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox
from datetime import datetime as dt
import ctypes
import time
from ..database import calibration_manager, supabase
from trackpro.database.user_manager import user_manager

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
                'throttle': 0,
                'brake': 1,
                'clutch': 2
            }
        
        # Validate axis mappings against available axes
        self._validate_axis_mappings()
        
        # Set axis properties based on mappings
        self.THROTTLE_AXIS = self.axis_mappings.get('throttle', -1)
        self.BRAKE_AXIS = self.axis_mappings.get('brake', -1)
        self.CLUTCH_AXIS = self.axis_mappings.get('clutch', -1)
        
        # Initialize last known values
        self.last_values = {
            'throttle': 0,
            'brake': 0,
            'clutch': 0
        }
        
        # Initialize axis ranges (will be calibrated)
        self.axis_ranges = {
            'throttle': {'min': 0, 'max': 65535},
            'brake': {'min': 0, 'max': 65535},
            'clutch': {'min': 0, 'max': 65535}
        }
        
        # Load or calibrate axis ranges
        self._init_axis_ranges()
        
        # Create default curve presets if they don't exist
        self._create_default_curve_presets()
        
        # Sync with cloud if user is authenticated
        self._sync_with_cloud()

    def _sync_with_cloud(self):
        """Sync calibration data with cloud if user is authenticated."""
        if not supabase.is_authenticated():
            logger.info("Not syncing with cloud - user not authenticated")
            return
        
        try:
            user = supabase.get_user()
            if not user:
                logger.warning("Could not get user information")
                return
                
            # Extract user ID
            user_id = user_manager._extract_user_id(user)
            if not user_id:
                logger.error(f"Could not extract user ID from response: {user}")
                return
                
            # Get user's calibrations
            user_calibrations = calibration_manager.get_user_calibrations(user_id)
            
            # Process cloud calibrations
            for calibration in user_calibrations:
                name = calibration.get('name', '')
                data = calibration.get('data', {})
                
                # Handle normal calibration data (pedal_default)
                if name.endswith('_default'):
                    pedal = name.split('_')[0]
                    if pedal in self.calibration:
                        # Update local calibration with cloud data if needed
                        # Only update if no local calibration exists or if explicitly requested
                        # This preserves local calibrations by default
                        if 'points' not in self.calibration[pedal] or not self.calibration[pedal]['points']:
                            logger.info(f"Updating local {pedal} calibration with cloud data")
                            self.calibration[pedal] = data
                
                # Handle curve presets (pedal_curvename)
                elif '_' in name:
                    parts = name.split('_', 1)
                    if len(parts) == 2:
                        pedal, curve_name = parts
                        if pedal in ['throttle', 'brake', 'clutch']:
                            # Save cloud curve to local storage if it doesn't exist locally
                            curves_dir = self.get_pedal_curves_directory(pedal)
                            curve_file = curves_dir / f"{curve_name}.json"
                            
                            # Only save if the file doesn't exist locally
                            if not curve_file.exists():
                                logger.info(f"Saving cloud curve '{curve_name}' to local storage for {pedal}")
                                curves_dir.mkdir(parents=True, exist_ok=True)
                                with open(curve_file, 'w') as f:
                                    # Store only the necessary fields for local storage
                                    save_data = {
                                        'points': data.get('points', []),
                                        'curve_type': data.get('curve_type', curve_name)
                                    }
                                    json.dump(save_data, f, indent=2)

            # Save the combined calibration data
            self._save_calibration_to_file(self.calibration)
            logger.info("Synced calibration with cloud")
        except Exception as e:
            logger.error(f"Error syncing with cloud: {e}")

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
            for axis_name in ['throttle', 'brake', 'clutch']:
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
                    for axis_name in ['throttle', 'brake', 'clutch']:
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
            for axis_name in ['throttle', 'brake', 'clutch']:
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
            for axis_name in ['throttle', 'brake', 'clutch']:
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
        for pedal in ['throttle', 'brake', 'clutch']:
            pedal_dir = config_dir / pedal
            pedal_dir.mkdir(exist_ok=True)
        
        return config_dir

    def get_pedal_curves_directory(self, pedal: str) -> Path:
        """Get the directory for a specific pedal's curves."""
        return self._get_curves_directory() / pedal

    def list_available_curves(self, pedal: str) -> list:
        """List all available curves for a specific pedal."""
        try:
            # First get all local curves
            curves_dir = self.get_pedal_curves_directory(pedal)
            logger.info(f"Looking for curves in directory: {curves_dir}")
            
            # Ensure the directory exists
            if not curves_dir.exists():
                logger.warning(f"Curves directory does not exist: {curves_dir}")
                curves_dir.mkdir(exist_ok=True)
                logger.info(f"Created curves directory: {curves_dir}")
                local_curves = []
            else:
                # Get all JSON files in the directory
                curve_files = list(curves_dir.glob("*.json"))
                logger.info(f"Found {len(curve_files)} curve files: {[f.name for f in curve_files]}")
                
                # Validate each curve file to ensure it's readable
                local_curves = []
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
                                                        local_curves.append(file.stem)
                                                        logger.info(f"Added fixed curve: {file.stem}")
                                                        break
                                    except Exception as fix_error:
                                        logger.error(f"Failed to fix corrupted curve file: {fix_error}")
                                    continue
                                    
                                # Parse the JSON
                                curve_data = json.loads(content)
                                
                                # More lenient validation - only check if it's a dictionary with at least points
                                # or the filename can be used as the curve name
                                if not isinstance(curve_data, dict):
                                    logger.warning(f"Skipping invalid curve file (not a JSON object): {file}")
                                    continue
                                    
                                # If file has points but no required fields, it's still usable
                                if 'points' in curve_data:
                                    local_curves.append(file.stem)
                                    logger.debug(f"Validated curve file: {file.name}")
                                else:
                                    logger.warning(f"Skipping curve file without points: {file}")
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"Skipping invalid JSON in curve file: {file}")
                                continue
                    except Exception as e:
                        logger.warning(f"Error reading curve file {file}: {e}")
                        continue
            
            # Now get cloud curves if user is authenticated
            cloud_curves = []
            if supabase.is_authenticated():
                try:
                    user = supabase.get_user()
                    if user:
                        user_id = user_manager._extract_user_id(user)
                        if user_id:
                            # Get user's calibrations
                            user_calibrations = calibration_manager.get_user_calibrations(user_id)
                            
                            # Extract curve names
                            for calibration in user_calibrations:
                                name = calibration.get('name', '')
                                if name.startswith(f"{pedal}_") and not name.endswith("_default"):
                                    # Extract curve name (after pedal_ prefix)
                                    curve_name = name.split('_', 1)[1]
                                    # Add if not already in local curves
                                    if curve_name not in local_curves:
                                        cloud_curves.append(curve_name)
                except Exception as e:
                    logger.error(f"Error getting cloud curves: {e}")
            
            # Combine local and cloud curves
            all_curves = sorted(local_curves + cloud_curves)
            logger.info(f"Found {len(all_curves)} valid curves for {pedal}: {all_curves}")
            return all_curves
        except Exception as e:
            logger.error(f"Error listing available curves: {e}", exc_info=True)
            return []

    def save_custom_curve(self, pedal: str, name: str, points: list, curve_type: str) -> bool:
        """Save a custom curve configuration.
        
        Args:
            pedal: The pedal name ('throttle', 'brake', 'clutch')
            name: The name of the curve
            points: List of (x, y) tuples representing curve points
            curve_type: The type of curve
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Save locally
            curves_dir = self.get_pedal_curves_directory(pedal)
            curves_dir.mkdir(parents=True, exist_ok=True)
            
            curve_data = {
                'points': points,
                'curve_type': curve_type
            }
            
            # Save to local file
            curve_file = curves_dir / f"{name}.json"
            with open(curve_file, 'w') as f:
                json.dump(curve_data, f)
            
            # Save to cloud if authenticated
            if supabase.is_authenticated():
                user = supabase.get_user()
                if user:
                    calibration_manager.save_calibration(
                        user_id=user.id,
                        name=f"{pedal}_{name}",
                        data=curve_data
                    )
                    logger.info(f"Saved curve '{name}' to cloud for {pedal}")
            
            logger.info(f"Saved custom curve '{name}' for {pedal}")
            return True
        except Exception as e:
            logger.error(f"Failed to save custom curve: {e}")
            return False

    def load_custom_curve(self, pedal: str, curve_name: str) -> dict:
        """Load a custom curve configuration.
        
        Args:
            pedal: The pedal name ('throttle', 'brake', 'clutch')
            curve_name: The name of the curve to load
            
        Returns:
            dict: The curve data if found, None otherwise
        """
        local_curve = None
        cloud_curve = None
        
        try:
            # First check if local curve exists
            curves_dir = self.get_pedal_curves_directory(pedal)
            curve_file = curves_dir / f"{curve_name}.json"
            
            if curve_file.exists():
                try:
                    with open(curve_file) as f:
                        curve_data = json.load(f)
                    
                    # Handle different file structures
                    if not isinstance(curve_data, dict):
                        logger.warning(f"Invalid curve data format in {curve_file} - not a dictionary")
                    else:
                        # Ensure required fields exist
                        normalized_data = {}
                        
                        # Handle points field - required
                        if 'points' in curve_data:
                            normalized_data['points'] = curve_data['points']
                            
                            # Handle curve_type field - use name, curve_type, or filename
                            if 'curve_type' in curve_data:
                                normalized_data['curve_type'] = curve_data['curve_type']
                            elif 'name' in curve_data:
                                normalized_data['curve_type'] = curve_data['name']
                            else:
                                normalized_data['curve_type'] = curve_name
                            
                            local_curve = normalized_data
                            logger.info(f"Loaded curve '{curve_name}' from local file for {pedal}")
                except Exception as e:
                    logger.warning(f"Error loading local curve {curve_file}: {e}")
            
            # Now try cloud if authenticated
            if supabase.is_authenticated():
                try:
                    user = supabase.get_user()
                    if user:
                        user_id = user_manager._extract_user_id(user)
                        if user_id:
                            cloud_curve_data = calibration_manager.get_calibration(
                                user_id=user_id,
                                name=f"{pedal}_{curve_name}"
                            )
                            if cloud_curve_data and 'data' in cloud_curve_data:
                                cloud_curve = cloud_curve_data['data']
                                logger.info(f"Loaded curve '{curve_name}' from cloud for {pedal}")
                except Exception as e:
                    logger.warning(f"Error loading cloud curve '{curve_name}' for {pedal}: {e}")
            
            # Return local curve if it exists, otherwise cloud curve
            if local_curve:
                return local_curve
            elif cloud_curve:
                # If cloud curve is found but not local, save it locally for future use
                if curve_file and not curve_file.exists():
                    try:
                        curves_dir.mkdir(parents=True, exist_ok=True)
                        with open(curve_file, 'w') as f:
                            # Store only the necessary fields for local storage
                            save_data = {
                                'points': cloud_curve.get('points', []),
                                'curve_type': cloud_curve.get('curve_type', curve_name)
                            }
                            json.dump(save_data, f, indent=2)
                        logger.info(f"Saved cloud curve '{curve_name}' to local storage for {pedal}")
                    except Exception as e:
                        logger.error(f"Error saving cloud curve locally: {e}")
                return cloud_curve
            
            # Neither local nor cloud curve found
            logger.warning(f"Custom curve '{curve_name}' not found for {pedal}")
            return None
        except Exception as e:
            logger.error(f"Failed to load custom curve: {e}")
            return None

    def delete_custom_curve(self, pedal: str, name: str) -> bool:
        """Delete a custom curve for a specific pedal."""
        try:
            # Delete from local file
            curves_dir = self.get_pedal_curves_directory(pedal)
            curve_file = curves_dir / f"{name}.json"
            
            if curve_file.exists():
                curve_file.unlink()
                logger.info(f"Deleted local curve '{name}' for {pedal}")
            
            # Delete from cloud if authenticated
            if supabase.is_authenticated():
                user = supabase.get_user()
                if user:
                    calibration_manager.delete_calibration(
                        user_id=user.id,
                        name=f"{pedal}_{name}"
                    )
                    logger.info(f"Deleted cloud curve '{name}' for {pedal}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete custom curve: {e}")
            return False

    def apply_curve_to_calibration(self, pedal: str, curve_name: str) -> bool:
        """Apply a custom curve to the current calibration.
        
        Args:
            pedal: The pedal name ('throttle', 'brake', 'clutch')
            curve_name: The name of the custom curve
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            curve_data = self.load_custom_curve(pedal, curve_name)
            if not curve_data:
                return False
            
            # Make sure we have valid points and curve_type
            points = curve_data.get('points', [])
            curve_type = curve_data.get('curve_type', curve_name)
            
            if not points:
                logger.error(f"Cannot apply curve '{curve_name}' - no points data")
                return False
            
            # Update calibration with the loaded curve
            self.calibration[pedal] = {
                'points': points,
                'curve': curve_type
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
        """Load calibration from file or return defaults."""
        try:
            cal_file = self._get_calibration_file()
            if cal_file.exists():
                with open(cal_file) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load calibration: {e}")
            
        # Return default calibration
        return {
            'throttle': {'points': [], 'curve': 'Linear'},
            'brake': {'points': [], 'curve': 'Linear'},
            'clutch': {'points': [], 'curve': 'Linear'}
        }
    
    def _load_axis_mappings(self) -> dict:
        """Load axis mappings from file or return defaults."""
        try:
            mappings_file = self._get_axis_mappings_file()
            if mappings_file.exists():
                with open(mappings_file) as f:
                    mappings = json.load(f)
                logger.info(f"Loaded axis mappings: {mappings}")
                return mappings
        except Exception as e:
            logger.warning(f"Failed to load axis mappings: {e}")
            
        # Return default mappings
        return {
            'throttle': 0,
            'brake': 1,
            'clutch': 2
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
            if pedal == 'throttle':
                self.THROTTLE_AXIS = axis
            elif pedal == 'brake':
                self.BRAKE_AXIS = axis
            elif pedal == 'clutch':
                self.CLUTCH_AXIS = axis
            
            # Save the updated mappings
            self.save_axis_mappings()
            logger.info(f"Updated {pedal} axis mapping to {axis}")
            return True
        return False
    
    def save_calibration(self, calibration: dict):
        """Save calibration data to file and cloud."""
        try:
            # Save to local file first
            self._save_calibration_to_file(calibration)
            logger.info("Calibration saved locally")
            
            # Create or reset the cloud upload timer
            if hasattr(self, '_cloud_save_timer') and self._cloud_save_timer:
                try:
                    self._cloud_save_timer.cancel()
                except:
                    pass
            
            # Store the calibration data for delayed upload
            self._pending_cloud_calibration = calibration.copy()
            
            # Create a new timer for cloud upload with 1 minute delay
            import threading
            self._cloud_save_timer = threading.Timer(60.0, self._delayed_cloud_save)
            self._cloud_save_timer.daemon = True
            self._cloud_save_timer.start()
            logger.info("Cloud save scheduled in 60 seconds")
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
            raise
    
    def _delayed_cloud_save(self):
        """Save calibration to cloud after delay period."""
        try:
            # Only proceed if we have pending calibration data
            if not hasattr(self, '_pending_cloud_calibration') or not self._pending_cloud_calibration:
                return
                
            # Get the pending calibration
            calibration = self._pending_cloud_calibration
                
            # Save to cloud if authenticated
            if supabase.is_authenticated():
                user = supabase.get_user()
                if user:
                    # Extract user ID properly
                    user_id = user_manager._extract_user_id(user)
                    if not user_id:
                        logger.error(f"Could not extract user ID from response: {user}")
                        raise ValueError("Could not extract user ID from response")
                    
                    # Save each pedal's calibration
                    for pedal, data in calibration.items():
                        calibration_manager.save_calibration(
                            user_id=user_id,
                            name=f"{pedal}_default",
                            data=data
                        )
                    logger.info("Calibration saved to cloud")
        except Exception as e:
            logger.error(f"Failed to save calibration to cloud: {e}")

    def read_pedals(self):
        """Read current pedal values."""
        # Process events to get fresh values if pedals are connected
        if self.pedals_connected:
            try:
                pygame.event.pump()
            except Exception as e:
                logger.warning(f"Error pumping pygame events: {e}, connection might be unstable")
                # Don't mark as disconnected here, let the connection checker handle it
        
        try:
            # Initialize with last known values (if available) to provide continuity
            if hasattr(self, 'last_values') and self.last_values:
                values = self.last_values.copy()
            else:
                values = {
                    'throttle': 0,
                    'brake': 0,
                    'clutch': 0
                }
            
            # Read and scale each axis
            for axis_name, axis_num in [
                ('throttle', self.THROTTLE_AXIS),
                ('brake', self.BRAKE_AXIS),
                ('clutch', self.CLUTCH_AXIS)
            ]:
                # Skip unavailable axes
                if axis_num < 0 or axis_num >= self.available_axes:
                    continue  # Keep last known value instead of resetting
                
                if not self.pedals_connected:
                    # When pedals not connected, use mock values or last values
                    # Keep the last value by default (values was initialized with last_values)
                    continue
                else:
                    # Get raw value (-1 to 1)
                    try:
                        raw_value = self.joystick.get_axis(axis_num)
                        
                        # Convert to 0-65535 range (16-bit)
                        # Note: The hardware is 12-bit (0-4096), but we scale to 16-bit for better resolution
                        # This is the RAW value that should be displayed in the UI
                        scaled_value = int((raw_value + 1) * 32767)
                        
                        # Store the raw scaled value without applying calibration range
                        values[axis_name] = scaled_value
                    except Exception as e:
                        logger.warning(f"Error reading {axis_name} axis: {e}, using last value")
                        # Keep last value, don't modify values[axis_name]
            
            self.last_values = values
            return values
            
        except Exception as e:
            logger.error(f"Error reading pedal values: {e}")
            # Return last_values if available, otherwise create default values
            if hasattr(self, 'last_values') and self.last_values:
                return self.last_values
            else:
                self.last_values = {
                    'throttle': 0,
                    'brake': 0,
                    'clutch': 0
                }
                return self.last_values

    def apply_calibration(self, pedal: str, raw_value: int) -> int:
        """Apply calibration to a raw pedal value."""
        # Get calibration data
        cal = self.calibration.get(pedal, {})
        points = cal.get('points', [])
        curve_type = cal.get('curve', 'Linear')
        
        # Get min/max range
        axis_range = self.axis_ranges[pedal]
        input_min = axis_range['min']
        input_max = axis_range['max']
        
        # Get deadzone values (default to 0 if not present for backward compatibility)
        min_deadzone = axis_range.get('min_deadzone', 0)
        max_deadzone = axis_range.get('max_deadzone', 0)
        
        # Calculate range size
        range_size = input_max - input_min
        
        # Normalize input value to 0-100 range (percentage)
        if input_max > input_min:
            # Standard linear normalization - maintain linearity regardless of range size
            normalized = ((raw_value - input_min) / range_size) * 100
        else:
            normalized = (raw_value / 65535) * 100
            
        # Clamp to 0-100 range
        normalized = max(0.0, min(100.0, normalized))
        
        # Apply deadzone at minimum (if pedal is barely pressed, treat as not pressed)
        if normalized < min_deadzone:
            # Return 0 immediately for values in the minimum deadzone
            return 0
        
        # Apply deadzone at maximum (if pedal is almost fully pressed, treat as fully pressed)
        if normalized > (100.0 - max_deadzone):
            normalized = 100.0
            
        # If between min_deadzone and (100 - max_deadzone), rescale to full range
        if min_deadzone > 0 or max_deadzone > 0:
            if normalized > min_deadzone and normalized < 100:
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
                'throttle': [
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
                    },
                    # New throttle profiles
                    {
                        'name': 'Drift Control',
                        'points': [(0, 0), (20, 15), (40, 45), (60, 90), (80, 95), (100, 100)],
                        'curve_type': 'Drift Control'
                    },
                    {
                        'name': 'F1 Style',
                        'points': [(0, 0), (10, 3), (20, 8), (40, 20), (60, 40), (80, 70), (100, 100)],
                        'curve_type': 'F1 Style'
                    },
                    {
                        'name': 'Rally',
                        'points': [(0, 0), (20, 25), (40, 40), (60, 60), (80, 85), (100, 100)],
                        'curve_type': 'Rally'
                    },
                    {
                        'name': 'Dirt Track',
                        'points': [(0, 0), (20, 10), (40, 30), (60, 45), (80, 70), (100, 90)],
                        'curve_type': 'Dirt Track'
                    },
                    {
                        'name': 'Super Precise',
                        'points': [(0, 0), (10, 2), (25, 5), (50, 15), (75, 35), (85, 65), (95, 85), (100, 100)],
                        'curve_type': 'Super Precise'
                    },
                    # Wet Weather Racing presets
                    {
                        'name': 'Wet Weather Racing',
                        'points': [(0, 0), (15, 5), (30, 12), (45, 20), (60, 30), (75, 45), (90, 70), (100, 85)],
                        'curve_type': 'Wet Weather Racing'
                    },
                    {
                        'name': 'Light Rain',
                        'points': [(0, 0), (20, 10), (40, 22), (60, 38), (80, 65), (100, 90)],
                        'curve_type': 'Light Rain'
                    },
                    {
                        'name': 'Extreme Wet',
                        'points': [(0, 0), (15, 3), (30, 8), (45, 15), (60, 25), (75, 40), (90, 60), (100, 75)],
                        'curve_type': 'Extreme Wet'
                    }
                ],
                'brake': [
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
                    # Enhanced ABS variations
                    {
                        'name': 'ABS Racing',
                        'points': [(0, 0), (20, 25), (40, 45), (60, 60), (80, 75), (100, 85)],
                        'curve_type': 'ABS Racing'
                    },
                    {
                        'name': 'ABS Competition',
                        'points': [(0, 0), (15, 20), (30, 40), (50, 60), (70, 75), (90, 85), (100, 90)],
                        'curve_type': 'ABS Competition'
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
                    # Enhanced Threshold Braking variations
                    {
                        'name': 'Precision Threshold',
                        'points': [(0, 0), (15, 8), (30, 18), (45, 35), (60, 65), (75, 85), (85, 95), (100, 100)],
                        'curve_type': 'Precision Threshold'
                    },
                    {
                        'name': 'Race Threshold',
                        'points': [(0, 0), (10, 5), (25, 15), (40, 30), (55, 55), (70, 80), (85, 95), (100, 100)],
                        'curve_type': 'Race Threshold'
                    },
                    {
                        'name': 'Wet Weather',
                        'points': [(0, 0), (20, 5), (40, 15), (60, 30), (80, 60), (100, 85)],
                        'curve_type': 'Wet Weather'
                    },
                    # Additional Wet Weather variations
                    {
                        'name': 'Wet Racing',
                        'points': [(0, 0), (15, 7), (30, 18), (45, 32), (60, 50), (75, 70), (90, 85), (100, 92)],
                        'curve_type': 'Wet Racing'
                    },
                    {
                        'name': 'Wet Circuit',
                        'points': [(0, 0), (20, 10), (35, 22), (50, 38), (65, 55), (80, 75), (100, 90)],
                        'curve_type': 'Wet Circuit'
                    },
                    {
                        'name': 'Extreme Wet Braking',
                        'points': [(0, 0), (15, 5), (30, 12), (45, 20), (60, 35), (75, 55), (90, 75), (100, 85)],
                        'curve_type': 'Extreme Wet Braking'
                    },
                    {
                        'name': 'Initial Bite',
                        'points': [(0, 0), (10, 20), (30, 45), (50, 65), (70, 80), (100, 100)],
                        'curve_type': 'Initial Bite'
                    },
                    # New brake profiles
                    {
                        'name': 'GT3 Racing',
                        'points': [(0, 0), (5, 15), (15, 35), (30, 60), (50, 80), (75, 95), (100, 100)],
                        'curve_type': 'GT3 Racing'
                    },
                    {
                        'name': 'Endurance',
                        'points': [(0, 0), (20, 15), (40, 30), (60, 50), (80, 75), (100, 95)],
                        'curve_type': 'Endurance'
                    },
                    {
                        'name': 'Technical Circuit',
                        'points': [(0, 0), (15, 10), (30, 25), (45, 45), (60, 70), (75, 90), (100, 100)],
                        'curve_type': 'Technical Circuit'
                    },
                    {
                        'name': 'Oval Track',
                        'points': [(0, 0), (30, 20), (50, 45), (70, 80), (85, 95), (100, 100)],
                        'curve_type': 'Oval Track'
                    },
                    {
                        'name': 'Street Car',
                        'points': [(0, 0), (25, 25), (50, 50), (75, 75), (100, 100)],
                        'curve_type': 'Street Car'
                    }
                ],
                'clutch': [
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
                    },
                    # New clutch profiles
                    {
                        'name': 'Performance Launch',
                        'points': [(0, 0), (35, 15), (45, 40), (50, 70), (55, 90), (65, 98), (100, 100)],
                        'curve_type': 'Performance Launch'
                    },
                    {
                        'name': 'Drag Racing',
                        'points': [(0, 0), (30, 10), (40, 30), (45, 50), (48, 80), (50, 95), (100, 100)],
                        'curve_type': 'Drag Racing'
                    },
                    {
                        'name': 'Heel-Toe',
                        'points': [(0, 0), (20, 5), (40, 15), (65, 60), (85, 90), (100, 100)],
                        'curve_type': 'Heel-Toe'
                    },
                    {
                        'name': 'Rally Start',
                        'points': [(0, 0), (30, 25), (45, 55), (55, 85), (65, 95), (100, 100)],
                        'curve_type': 'Rally Start'
                    },
                    {
                        'name': 'Half Clutch Control',
                        'points': [(0, 0), (40, 20), (47, 40), (50, 60), (53, 80), (60, 95), (100, 100)],
                        'curve_type': 'Half Clutch Control'
                    },
                    # Wet Weather clutch presets
                    {
                        'name': 'Wet Weather Launch',
                        'points': [(0, 0), (30, 15), (40, 35), (50, 65), (60, 85), (70, 95), (100, 100)],
                        'curve_type': 'Wet Weather Launch'
                    },
                    {
                        'name': 'Wet Track Control',
                        'points': [(0, 0), (25, 10), (40, 25), (50, 50), (60, 75), (75, 95), (100, 100)],
                        'curve_type': 'Wet Track Control'
                    },
                    {
                        'name': 'Wet Engagement',
                        'points': [(0, 0), (35, 20), (45, 45), (55, 75), (65, 90), (75, 98), (100, 100)],
                        'curve_type': 'Wet Engagement'
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

    def _save_calibration_to_file(self, calibration: dict):
        """Save calibration data to local file."""
        cal_file = self._get_calibration_file()
        with open(cal_file, 'w') as f:
            json.dump(calibration, f) 