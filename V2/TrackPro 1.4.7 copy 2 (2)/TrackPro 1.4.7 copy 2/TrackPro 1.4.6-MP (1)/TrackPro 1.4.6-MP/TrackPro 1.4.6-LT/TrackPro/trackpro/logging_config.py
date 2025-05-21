"""Logging configuration for TrackPro."""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    """Configure logging for the application."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Create trackpro logger (this will be the parent for all our module loggers)
    trackpro_logger = logging.getLogger('trackpro')
    trackpro_logger.setLevel(logging.DEBUG)  # Keep general debugging enabled
    
    # Create specific module loggers with custom levels
    ui_logger = logging.getLogger('trackpro.race_coach.ui')
    ui_logger.setLevel(logging.ERROR)  # Change from WARNING to ERROR to eliminate pedal input debug noise
    
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