import pygame
import logging
import json
import os
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from datetime import datetime as dt
import ctypes
import time
from ..database import calibration_manager, supabase
from trackpro.database.user_manager import user_manager
from ..race_coach.debouncer import trackpro_debouncer
from .curve_cache import curve_cache

logger = logging.getLogger(__name__)

class HandbrakeInput:
    """Hardware input handling specifically for the P1 Pro Handbrake (Arduino Leonardo)."""
    
    def __init__(self, test_mode=False):
        """Initialize handbrake input handling."""
        pygame.init()
        pygame.joystick.init()
        
        # Connection status flags
        self.joystick = None
        self.handbrake_connected = False
        
        # Add time tracking for dt calculation
        self._last_process_time = time.time()
        
        # Find our handbrake device (Arduino Leonardo)
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            device_name = joy.get_name()
            
            if "Arduino Leonardo" in device_name:
                self.joystick = joy
                self.handbrake_connected = True
                logger.info(f"Found P1 Pro Handbrake: {device_name}")
                break
        
        if not self.handbrake_connected:
            logger.warning("P1 Pro Handbrake (Arduino Leonardo) not connected. Running in fallback mode.")
            
            # Setup mock values for when no handbrake is connected
            self.available_axes = 1
            self.axis_values = [0.0]  # Default value for handbrake
        else:
            self.available_axes = self.joystick.get_numaxes()
            logger.info(f"Detected {self.available_axes} axes on the handbrake")
        
        # Load calibration data
        self.calibration = self._load_calibration()
        
        # Default axis mapping for handbrake (typically axis 0)
        self.axis_mappings = {
            'handbrake': 0
        }
        
        # Validate axis mappings against available axes
        self._validate_axis_mappings()
        
        # Set axis properties based on mappings
        self.HANDBRAKE_AXIS = self.axis_mappings.get('handbrake', 0)
        
        # Initialize last known values
        self.last_values = {
            'handbrake': 0
        }
        
        # Initialize axis ranges (will be calibrated)
        self.axis_ranges = {
            'handbrake': {'min': 0, 'max': 65535}
        }
        
        # Load or calibrate axis ranges
        self._init_axis_ranges()
        
        # OPTIMIZATION: Defer heavy operations to avoid blocking startup
        self._curves_initialized = False
        self._cloud_synced = False
        
        # Setup debounced calibration operations
        trackpro_debouncer.setup_calibration_operations(self._execute_calibration_save)
        
        logger.info("Handbrake input initialized")

    def ensure_curves_initialized(self):
        """Ensure curves are initialized (called lazily when needed)."""
        if not self._curves_initialized:
            if hasattr(self, '_initializing_curves') and self._initializing_curves:
                return
            
            self._initializing_curves = True
            logger.info("Initializing handbrake curves on first access...")
            try:
                self._create_default_curve_presets()
                self._curves_initialized = True
            finally:
                self._initializing_curves = False
    
    def ensure_cloud_synced(self):
        """Ensure cloud sync has been performed (called lazily when needed)."""
        if not self._cloud_synced:
            logger.info("Performing handbrake cloud sync on first access...")
            self._sync_with_cloud()
            self._cloud_synced = True

    def _sync_with_cloud(self):
        """Sync handbrake calibration data with cloud if user is authenticated."""
        if not supabase.is_authenticated():
            logger.info("Not syncing handbrake with cloud - user not authenticated")
            return
        
        try:
            user = supabase.get_user()
            if not user:
                logger.warning("Could not get user information for handbrake sync")
                return
                
            # Extract user ID
            user_id = user_manager._extract_user_id(user)
            if not user_id:
                logger.error(f"Could not extract user ID from response: {user}")
                return
                
            # Get user's handbrake calibrations
            user_calibrations = calibration_manager.get_user_calibrations(user_id, device_type='handbrake')
            
            # Process cloud calibrations
            for calibration in user_calibrations:
                name = calibration.get('name', '')
                data = calibration.get('data', {})
                
                if 'handbrake' in data:
                    logger.info(f"Loading handbrake calibration from cloud: {name}")
                    self.axis_ranges['handbrake'] = data['handbrake']
                    
        except Exception as e:
            logger.error(f"Error syncing handbrake calibration with cloud: {e}")

    def _validate_axis_mappings(self):
        """Validate that axis mappings are within range of available axes."""
        if self.handbrake_connected:
            max_axis = self.available_axes - 1
            for control, axis in self.axis_mappings.items():
                if axis > max_axis:
                    logger.warning(f"Handbrake axis mapping for {control} ({axis}) exceeds available axes ({max_axis})")
                    self.axis_mappings[control] = 0  # Default to first axis

    def _load_calibration(self):
        """Load handbrake calibration data from file."""
        calibration_file = Path.home() / "Documents" / "TrackPro" / "handbrake_calibration.json"
        
        if calibration_file.exists():
            try:
                with open(calibration_file, 'r') as f:
                    calibration = json.load(f)
                logger.info("Loaded handbrake calibration from file")
                return calibration
            except Exception as e:
                logger.error(f"Error loading handbrake calibration: {e}")
        
        # Return default calibration
        return {
            'handbrake': {
                'min': 0,
                'max': 65535,
                'curve': 'linear',
                'deadzone_min': 0,
                'deadzone_max': 0,
                'sensitivity': 1.0
            }
        }

    def _init_axis_ranges(self):
        """Initialize axis ranges from calibration data."""
        if self.calibration and 'handbrake' in self.calibration:
            handbrake_cal = self.calibration['handbrake']
            self.axis_ranges['handbrake'] = {
                'min': handbrake_cal.get('min', 0),
                'max': handbrake_cal.get('max', 65535)
            }

    def _create_default_curve_presets(self):
        """Create default curve presets for handbrake."""
        # This would create default curves specific to handbrake
        # For now, we'll use the same curve system as pedals
        pass

    def _execute_calibration_save(self, calibration_data):
        """Execute the actual save operation for calibration data."""
        try:
            calibration_file = Path.home() / "Documents" / "TrackPro" / "handbrake_calibration.json"
            calibration_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(calibration_file, 'w') as f:
                json.dump(calibration_data, f, indent=2)
            
            logger.info("Handbrake calibration saved successfully")
        except Exception as e:
            logger.error(f"Error saving handbrake calibration: {e}")

    def read_handbrake(self):
        """Read the current handbrake value - ULTRA HIGH PERFORMANCE."""
        if not self.handbrake_connected:
            # Return mock data when no handbrake is connected
            return {'handbrake': 0}
        
        # PERFORMANCE FIX: Only pump pygame events every 5 calls (20Hz from 100Hz)
        if not hasattr(self, '_pump_counter'):
            self._pump_counter = 0
        self._pump_counter += 1
        
        try:
            # Update joystick state less frequently
            if self._pump_counter % 5 == 0:  # Every 5 calls = 20Hz
                pygame.event.pump()
            
            # Read handbrake axis (typically axis 0 on Arduino Leonardo)
            if self.HANDBRAKE_AXIS < self.joystick.get_numaxes():
                raw_value = self.joystick.get_axis(self.HANDBRAKE_AXIS)
                # Convert from -1.0 to 1.0 range to 0-65535 range
                normalized_value = int((raw_value + 1.0) * 32767.5)
                # Clamp to valid range
                normalized_value = max(0, min(65535, normalized_value))
            else:
                normalized_value = 0
            
            self.last_values['handbrake'] = normalized_value
            return {'handbrake': normalized_value}
            
        except Exception as e:
            logger.error(f"Error reading handbrake: {e}")
            return {'handbrake': self.last_values.get('handbrake', 0)}

    def apply_calibration(self, control: str, raw_value: float) -> float:
        """Apply calibration to handbrake input value."""
        if control != 'handbrake':
            return raw_value
        
        if not self.calibration or 'handbrake' not in self.calibration:
            return raw_value
        
        cal = self.calibration['handbrake']
        
        # Apply range calibration
        min_val = cal.get('min', 0)
        max_val = cal.get('max', 65535)
        
        # Normalize to 0-1 range
        if max_val > min_val:
            normalized = (raw_value - min_val) / (max_val - min_val)
        else:
            normalized = 0.0
        
        # Clamp to 0-1 range
        normalized = max(0.0, min(1.0, normalized))
        
        # Apply deadzone
        deadzone_min = cal.get('deadzone_min', 0) / 100.0
        deadzone_max = cal.get('deadzone_max', 0) / 100.0
        
        if normalized <= deadzone_min:
            normalized = 0.0
        elif normalized >= (1.0 - deadzone_max):
            normalized = 1.0
        else:
            # Scale the middle range
            usable_range = 1.0 - deadzone_min - deadzone_max
            if usable_range > 0:
                normalized = (normalized - deadzone_min) / usable_range
            else:
                normalized = 0.0
        
        # Apply sensitivity curve
        sensitivity = cal.get('sensitivity', 1.0)
        if sensitivity != 1.0:
            normalized = pow(normalized, sensitivity)
        
        # Convert back to 0-65535 range for vJoy
        return int(normalized * 65535)

    def get_handbrake_status(self):
        """Get handbrake connection status."""
        return {
            'connected': self.handbrake_connected,
            'device_name': self.joystick.get_name() if self.joystick else None,
            'axes': self.available_axes if self.handbrake_connected else 0
        }

    def save_calibration(self, calibration_data):
        """Save calibration data using debounced operation."""
        # Use debounced save to avoid too frequent writes
        trackpro_debouncer.schedule_calibration_save(calibration_data)

    def cleanup(self):
        """Clean up handbrake resources."""
        if self.joystick:
            try:
                self.joystick.quit()
            except:
                pass
        
        pygame.joystick.quit()
        logger.info("Handbrake input cleaned up")