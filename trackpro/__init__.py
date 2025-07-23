"""TrackPro - Advanced Pedal Input Mapping Software"""

__version__ = "1.5.3"
__author__ = "Sim Coaches"
__license__ = "Proprietary"
__copyright__ = "Copyright 2025 Sim Coaches"

import logging
import os
import sys
from pathlib import Path

# Set higher logging level for noisy HTTP and Supabase libraries
for library in ['urllib3', 'httpcore', 'httpx', 'hpack', 'gotrue', 'postgrest']:
    logging.getLogger(library).setLevel(logging.WARNING)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import main components
# Import MainWindow from the new ui module structure
from .ui import MainWindow
from .pedals.hardware_input import HardwareInput
from .pedals.output import VirtualJoystick
# Import race_coach module for the Race Coach feature
from .race_coach import RaceCoachWidget

from .main import main 