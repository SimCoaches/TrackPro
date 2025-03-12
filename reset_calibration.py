import os
import json
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrackPro_Reset")

def get_config_dir() -> Path:
    """Get the TrackPro config directory."""
    return Path.home() / ".trackpro"

def reset_calibration():
    """Reset all calibration data to defaults."""
    config_dir = get_config_dir()
    
    # Check if the directory exists
    if not config_dir.exists():
        logger.info(f"Config directory {config_dir} does not exist, creating it")
        config_dir.mkdir(exist_ok=True)
    
    # Reset calibration file
    cal_file = config_dir / "calibration.json"
    default_cal = {
        'throttle': {'points': [], 'curve': 'Linear'},
        'brake': {'points': [], 'curve': 'Linear'},
        'clutch': {'points': [], 'curve': 'Linear'}
    }
    
    try:
        # Create backup
        if cal_file.exists():
            backup_file = cal_file.with_suffix('.json.bak')
            shutil.copy(cal_file, backup_file)
            logger.info(f"Backed up calibration to {backup_file}")
        
        # Write default calibration
        with open(cal_file, 'w') as f:
            json.dump(default_cal, f, indent=2)
        logger.info(f"Reset calibration file {cal_file}")
    except Exception as e:
        logger.error(f"Error resetting calibration: {e}")
    
    # Reset axis mappings
    mappings_file = config_dir / "axis_mappings.json"
    default_mappings = {
        'throttle': 0,
        'brake': 1,
        'clutch': -1  # Disable clutch for 2-axis setup
    }
    
    try:
        # Create backup
        if mappings_file.exists():
            backup_file = mappings_file.with_suffix('.json.bak')
            shutil.copy(mappings_file, backup_file)
            logger.info(f"Backed up axis mappings to {backup_file}")
        
        # Write default mappings
        with open(mappings_file, 'w') as f:
            json.dump(default_mappings, f, indent=2)
        logger.info(f"Reset axis mappings file {mappings_file}")
    except Exception as e:
        logger.error(f"Error resetting axis mappings: {e}")
    
    # Reset axis ranges
    ranges_file = config_dir / "axis_ranges.json"
    default_ranges = {
        'throttle': {
            'min': 0,
            'max': 65535,
            'min_deadzone': 0,
            'max_deadzone': 0
        },
        'brake': {
            'min': 0,
            'max': 65535,
            'min_deadzone': 0,
            'max_deadzone': 0
        },
        'clutch': {
            'min': 0,
            'max': 65535,
            'min_deadzone': 0,
            'max_deadzone': 0
        }
    }
    
    try:
        # Create backup
        if ranges_file.exists():
            backup_file = ranges_file.with_suffix('.json.bak')
            shutil.copy(ranges_file, backup_file)
            logger.info(f"Backed up axis ranges to {backup_file}")
        
        # Write default ranges
        with open(ranges_file, 'w') as f:
            json.dump(default_ranges, f, indent=2)
        logger.info(f"Reset axis ranges file {ranges_file}")
    except Exception as e:
        logger.error(f"Error resetting axis ranges: {e}")
    
    # Done!
    logger.info("Calibration reset complete. Please restart TrackPro.")

if __name__ == "__main__":
    logger.info("Starting TrackPro calibration reset")
    reset_calibration() 