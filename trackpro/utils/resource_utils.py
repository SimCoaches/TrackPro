import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """Get the absolute path to a resource, works for both development and packaged apps.
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        logger.debug(f"Running as packaged app, using base path: {base_path}")
    except AttributeError:
        # Running in development mode
        # Go up 3 levels: resource_utils.py -> utils -> trackpro -> TrackPro-1 (project root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logger.debug(f"Running in development mode, using base path: {base_path}")
    
    full_path = os.path.join(base_path, relative_path)
    logger.debug(f"Resource path resolved: {relative_path} -> {full_path}")
    return full_path

def get_data_directory():
    """Get the directory for storing user data files.
    
    Returns:
        Path to user data directory (Documents/TrackPro)
    """
    try:
        # Use user's Documents folder for data storage
        docs_path = Path(os.path.expanduser("~/Documents/TrackPro"))
        docs_path.mkdir(parents=True, exist_ok=True)
        return str(docs_path)
    except Exception as e:
        logger.warning(f"Could not create Documents/TrackPro directory: {e}")
        # Fall back to application directory
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        fallback_path = os.path.join(base_path, "data")
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path

def get_database_path(db_name="race_coach.db"):
    """Get the path for database files.
    
    Args:
        db_name: Name of the database file
        
    Returns:
        Full path to the database file
    """
    data_dir = get_data_directory()
    return os.path.join(data_dir, db_name)

def get_config_path(config_name="config.ini"):
    """Get the path for configuration files.
    
    Args:
        config_name: Name of the config file
        
    Returns:
        Full path to the config file
    """
    data_dir = get_data_directory()
    return os.path.join(data_dir, config_name)

def get_telemetry_directory():
    """Get the directory for storing telemetry data.
    
    Returns:
        Path to telemetry data directory
    """
    data_dir = get_data_directory()
    telemetry_dir = os.path.join(data_dir, "Telemetry")
    os.makedirs(telemetry_dir, exist_ok=True)
    return telemetry_dir

def get_cache_directory():
    """Get the directory for storing cache files.
    
    Returns:
        Path to cache directory
    """
    data_dir = get_data_directory()
    cache_dir = os.path.join(data_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def is_packaged_app():
    """Check if the application is running as a packaged executable.
    
    Returns:
        True if running as packaged app, False if running from source
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_track_map_file_path():
    """Get the path for the main track map file.
    
    Returns:
        Full path to centerline_track_map.json
    """
    data_dir = get_data_directory()
    return os.path.join(data_dir, "centerline_track_map.json")

def ensure_writable_path(file_path):
    """Ensure the directory for a file path exists and is writable.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if directory exists and is writable, False otherwise
    """
    try:
        directory = os.path.dirname(file_path)
        os.makedirs(directory, exist_ok=True)
        
        # Test write access
        test_file = os.path.join(directory, ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        return True
    except Exception as e:
        logger.error(f"Path not writable: {file_path} - {e}")
        return False

def get_temp_directory():
    """Get a temporary directory for the application.
    
    Returns:
        Path to temp directory
    """
    import tempfile
    app_temp = os.path.join(tempfile.gettempdir(), "TrackPro")
    os.makedirs(app_temp, exist_ok=True)
    return app_temp

def copy_resource_to_data_if_missing(resource_relative_path, data_filename=None):
    """Copy a resource file to the data directory if it doesn't exist there.
    
    Args:
        resource_relative_path: Path to resource relative to app root
        data_filename: Optional different filename in data directory
        
    Returns:
        Path to file in data directory
    """
    if data_filename is None:
        data_filename = os.path.basename(resource_relative_path)
    
    data_dir = get_data_directory()
    data_file_path = os.path.join(data_dir, data_filename)
    
    # If file doesn't exist in data directory, copy from resources
    if not os.path.exists(data_file_path):
        try:
            resource_path = get_resource_path(resource_relative_path)
            if os.path.exists(resource_path):
                import shutil
                shutil.copy2(resource_path, data_file_path)
                logger.info(f"Copied resource {resource_relative_path} to {data_file_path}")
        except Exception as e:
            logger.warning(f"Could not copy resource {resource_relative_path}: {e}")
    
    return data_file_path 