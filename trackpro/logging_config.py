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

def setup_logging():
    """Configure logging for the application."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Create trackpro logger (this will be the parent for all our module loggers)
    trackpro_logger = logging.getLogger('trackpro')
    trackpro_logger.setLevel(logging.DEBUG)  # Keep general debugging enabled
    
    # Create specific module loggers with default levels
    ui_logger = logging.getLogger('trackpro.race_coach.ui')
    ui_logger.setLevel(logging.ERROR)  # Change from WARNING to ERROR to eliminate pedal input debug noise
    
    # Add telemetry logger with even higher level to reduce noise
    telemetry_logger = logging.getLogger('trackpro.race_coach.telemetry')
    telemetry_logger.setLevel(logging.ERROR)  # Only log errors and above
    
    # ABS loggers removed
    
    # ABS controller logger removed - module deleted
    
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
        # ABS logging references removed
    
    return root_logger

def configure_logging():
    """Configure logging for the application."""
    # Create logger
    logger = logging.getLogger('trackpro')
    logger.setLevel(logging.DEBUG)
    
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
    logging.getLogger('trackpro.race_coach.ui').setLevel(logging.ERROR)  # Change from WARNING to ERROR to eliminate pedal input noise
    logging.getLogger('trackpro.race_coach.simple_iracing').setLevel(logging.ERROR)
    
    return logger 