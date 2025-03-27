"""Logging configuration for TrackPro."""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
    
    # File logging has been removed
    
    return logger 