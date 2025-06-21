"""
Logging configuration for TrackPro Backend API Server
"""
import logging
import logging.handlers
import os
from typing import Optional
from .config import settings

def setup_logging(log_level: Optional[str] = None) -> None:
    """Set up logging configuration for the backend server"""
    
    level = getattr(logging, (log_level or settings.LOG_LEVEL).upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            logging.handlers.RotatingFileHandler(
                filename=f"logs/{settings.LOG_FILE}",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("fastapi").setLevel(level)
    logging.getLogger("websockets").setLevel(level)
    
    # Reduce noise from some third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)