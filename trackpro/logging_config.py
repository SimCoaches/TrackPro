"""Logging configuration for TrackPro."""

import os
import logging
import sys
import configparser
from logging.handlers import RotatingFileHandler
from pathlib import Path

def load_config():
    """Load configuration from config.ini file."""
    config = configparser.ConfigParser()
    
    # Try to read config.ini from current directory and project root
    config_paths = [
        "config.ini",
        os.path.join(os.path.dirname(__file__), "..", "config.ini"),
        os.path.join(os.path.dirname(__file__), "..", "..", "config.ini")
    ]
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            config.read(config_path)
            print(f"Loaded config from: {config_path}")
            return config
    
    return None

def apply_config_logging_levels(config):
    """Apply logging levels from configuration."""
    if not config or 'logging' not in config:
        return
    
    logging_config = config['logging']
    
    for logger_name, level_str in logging_config.items():
        # Skip obviously non-level values (e.g., app name or version accidentally placed here)
        if not isinstance(level_str, str):
            continue
        upper = level_str.upper()
        if upper not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}:
            # Avoid noisy prints for invalid entries
            continue
        try:
            level = getattr(logging, upper)
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            print(f"Set {logger_name} log level to {upper}")
        except Exception:
            # Ignore any edge case errors silently
            pass

def silence_noisy_libraries():
    """Silence excessively verbose third-party libraries."""
    # CRITICAL: Silence matplotlib font manager - this is the main culprit
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
    logging.getLogger('matplotlib.backends').setLevel(logging.WARNING)
    
    # Silence other noisy libraries
    noisy_libraries = [
        'urllib3', 'httpcore', 'httpx', 'hpack', 'gotrue', 'postgrest', 
        'urllib3.connection', 'urllib3.connectionpool', 'urllib3.poolmanager',
        'httpcore.connection', 'httpx.client', 'h11', 'h2', 'requests', 
        'supafunc', 'pyqtgraph', 'PIL', 'cv2', 'mediapipe'
    ]
    
    for library in noisy_libraries:
        logging.getLogger(library).setLevel(logging.WARNING)
    
    print("Silenced noisy third-party libraries")

def setup_logging():
    """Configure logging with env-driven levels and rotating file logs.
    Always reconfigure the root logger to ensure consistent behavior even if
    basicConfig was called earlier during package import.
    """
    silence_noisy_libraries()

    root_logger = logging.getLogger()
    # Remove any pre-existing handlers to avoid duplicate or inconsistent output
    for handler in list(root_logger.handlers):
        try:
            root_logger.removeHandler(handler)
        except Exception:
            pass

    # Determine log levels
    env_level = os.getenv('TRACKPRO_LOG_LEVEL', 'INFO').upper()
    # Default console to INFO so we can see what's happening by default
    console_level = os.getenv('TRACKPRO_CONSOLE_LOG_LEVEL', 'INFO').upper()
    try:
        root_level = getattr(logging, env_level)
    except AttributeError:
        root_level = logging.INFO
    try:
        console_level_val = getattr(logging, console_level)
    except AttributeError:
        console_level_val = logging.WARNING

    root_logger.setLevel(root_level)
    logging.getLogger('trackpro').setLevel(root_level)

    # Target log directory
    try:
        local_appdata = os.getenv('LOCALAPPDATA') or os.path.join(Path.home(), 'AppData', 'Local')
        logs_dir = Path(local_appdata) / 'TrackPro' / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / 'trackpro.log'
    except Exception:
        log_path = Path.cwd() / 'trackpro.log'

    # Handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level_val)

    file_handler = RotatingFileHandler(str(log_path), maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(root_level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Ensure TrackPro and Supabase-related modules are INFO for better diagnostics
    for name in [
        'trackpro',
        'trackpro.race_coach.ui',
        'trackpro.race_coach.simple_iracing',
        'trackpro.race_coach.lap_indexer',
        'trackpro.race_coach.telemetry_saver',
        'trackpro.race_coach.iracing_lap_saver',
        'trackpro.race_coach.telemetry',
        'Supabase',
        'supabase',
        'gotrue',
        'postgrest',
    ]:
        logging.getLogger(name).setLevel(logging.INFO)

    config = load_config()
    if config:
        apply_config_logging_levels(config)

    return root_logger

def configure_logging():
    """Configure logging for the application."""
    # Check if logging is already configured
    root_logger = logging.getLogger()
    if root_logger.handlers:
        print("Logging already configured, skipping duplicate setup")
        return logging.getLogger('trackpro')
    
    # First, silence noisy libraries
    silence_noisy_libraries()
    
    # Create logger
    logger = logging.getLogger('trackpro')
    logger.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Ensure TrackPro and Supabase-related modules are INFO for better diagnostics
    for name in [
        'trackpro',
        'trackpro.race_coach.ui',
        'trackpro.race_coach.simple_iracing',
        'trackpro.race_coach.lap_indexer',
        'trackpro.race_coach.telemetry',
        'Supabase',
        'supabase',
        'gotrue',
        'postgrest',
    ]:
        logging.getLogger(name).setLevel(logging.INFO)
    
    return logger 