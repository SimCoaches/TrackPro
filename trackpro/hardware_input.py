import pygame
import logging
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class HardwareInput:
    def __init__(self):
        """Initialize hardware input handling."""
        pygame.init()
        pygame.joystick.init()
        
        # Find our pedal device
        self.joystick = None
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            if "Sim Coaches P1 Pro Pedals" in joy.get_name():
                self.joystick = joy
                logger.info(f"Found pedals: {joy.get_name()}")
                break
        
        if not self.joystick:
            raise RuntimeError("Could not find Sim Coaches P1 Pro Pedals")
            
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
        
        # Set axis properties based on mappings
        self.THROTTLE_AXIS = self.axis_mappings['throttle']
        self.BRAKE_AXIS = self.axis_mappings['brake']
        self.CLUTCH_AXIS = self.axis_mappings['clutch']
        
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
        pygame.event.pump()
        
        # Read current values and update ranges
        for axis_name, axis_num in [
            ('throttle', self.THROTTLE_AXIS),
            ('brake', self.BRAKE_AXIS),
            ('clutch', self.CLUTCH_AXIS)
        ]:
            raw_value = self.joystick.get_axis(axis_num)
            scaled_value = int((raw_value + 1) * 32767)  # Convert from -1,1 to 0,65535
            
            # Update ranges
            self.axis_ranges[axis_name] = {
                'min': min(scaled_value, self.axis_ranges[axis_name]['min']),
                'max': max(scaled_value, self.axis_ranges[axis_name]['max'])
            }
        
        # Save the ranges
        self.save_axis_ranges()

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
        pygame.event.pump()  # Process events to get fresh values
        
        try:
            values = {}
            # Read and scale each axis
            for axis_name, axis_num in [
                ('throttle', self.THROTTLE_AXIS),
                ('brake', self.BRAKE_AXIS),
                ('clutch', self.CLUTCH_AXIS)
            ]:
                # Get raw value (-1 to 1)
                raw_value = self.joystick.get_axis(axis_num)
                
                # Convert to 0-65535 range
                scaled_value = int((raw_value + 1) * 32767)
                
                # Apply axis range scaling
                axis_range = self.axis_ranges[axis_name]
                if axis_range['max'] > axis_range['min']:
                    normalized_value = (scaled_value - axis_range['min']) / (axis_range['max'] - axis_range['min'])
                    values[axis_name] = int(normalized_value * 65535)
                else:
                    values[axis_name] = scaled_value
            
            self.last_values = values
            return values
            
        except Exception as e:
            logger.error(f"Error reading pedal values: {e}")
            return self.last_values  # Return last known values on error
    
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
        
        # Normalize input value to 0-100 range (percentage)
        if input_max > input_min:
            normalized = ((raw_value - input_min) / (input_max - input_min)) * 100
        else:
            normalized = (raw_value / 65535) * 100
            
        # Clamp to 0-100 range
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