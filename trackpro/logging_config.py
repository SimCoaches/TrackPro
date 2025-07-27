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
        try:
            level = getattr(logging, level_str.upper())
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            print(f"Set {logger_name} log level to {level_str.upper()}")
        except AttributeError:
            print(f"Invalid log level '{level_str}' for logger '{logger_name}'")

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
    """Configure logging for the application."""
    # First, silence noisy libraries BEFORE any other configuration
    silence_noisy_libraries()
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Check if handlers are already configured (prevents duplicate logging)
    if root_logger.handlers:
        print("Logging already configured, skipping duplicate setup")
        return root_logger
    
    root_logger.setLevel(logging.INFO)
    
    # Create trackpro logger (this will be the parent for all our module loggers)
    trackpro_logger = logging.getLogger('trackpro')
    trackpro_logger.setLevel(logging.INFO)  # Changed from DEBUG to INFO to reduce spam
    
    # Create specific module loggers with appropriate levels
    ui_logger = logging.getLogger('trackpro.race_coach.ui')
    ui_logger.setLevel(logging.ERROR)  # Only errors for UI
    
    # Set race coach modules to INFO instead of DEBUG
    race_coach_logger = logging.getLogger('trackpro.race_coach')
    race_coach_logger.setLevel(logging.INFO)  # Changed from DEBUG
    
    # Specific problematic modules that generate too much output
    logging.getLogger('trackpro.race_coach.simple_iracing').setLevel(logging.WARNING)
    logging.getLogger('trackpro.race_coach.lap_indexer').setLevel(logging.WARNING)
    logging.getLogger('trackpro.race_coach.telemetry_saver').setLevel(logging.WARNING)
    logging.getLogger('trackpro.race_coach.iracing_lap_saver').setLevel(logging.WARNING)
    
    # Add telemetry logger with even higher level to reduce noise
    telemetry_logger = logging.getLogger('trackpro.race_coach.telemetry')
    telemetry_logger.setLevel(logging.ERROR)  # Only log errors and above
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add formatters to handlers
    console_handler.setFormatter(detailed_formatter)
    
    # Add handlers to loggers
    root_logger.addHandler(console_handler)
    
    # Load configuration and apply logging levels
    config = load_config()
    if config:
        apply_config_logging_levels(config)
        print("Applied logging configuration from config.ini")
    else:
        print("No config.ini found, using default logging levels")
        print("To enable debug logging, create config.ini and set:")
        print("  [logging]")
        print("  trackpro = DEBUG")
    
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
    logger.setLevel(logging.INFO)  # Changed from DEBUG
    
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Set specific module loggers to higher levels to reduce console spam
    logging.getLogger('trackpro.race_coach.ui').setLevel(logging.ERROR)
    logging.getLogger('trackpro.race_coach.simple_iracing').setLevel(logging.WARNING)
    logging.getLogger('trackpro.race_coach.lap_indexer').setLevel(logging.WARNING)
    
    return logger 