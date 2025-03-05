"""TrackPro - Advanced Pedal Input Mapping Software"""

__version__ = "1.3.1"
__author__ = "Sim Coaches"
__license__ = "Proprietary"
__copyright__ = "Copyright 2025 Sim Coaches"

import logging
import os
import sys

# Configure logging

# Import main components
from .ui import MainWindow
from .hardware_input import HardwareInput
from .output import VirtualJoystick

from .main import main 