"""
iRacing API module - placeholder implementation that redirects to the SimpleIRacingAPI.

This file exists to maintain backwards compatibility with code that imports
IRacingAPI from this module.
"""

import logging
from .simple_iracing import SimpleIRacingAPI

# Set up logging
logger = logging.getLogger(__name__)

class IRacingAPI(SimpleIRacingAPI):
    """IRacingAPI class that inherits from SimpleIRacingAPI for compatibility.
    
    This class exists to maintain backwards compatibility with code that
    imports IRacingAPI from the iracing_api module.
    """
    
    def __init__(self, *args, **kwargs):
        logger.info("Using IRacingAPI (wrapper around SimpleIRacingAPI)")
        super().__init__(*args, **kwargs) 