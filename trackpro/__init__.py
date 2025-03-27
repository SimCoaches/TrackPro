"""TrackPro - Advanced Pedal Input Mapping Software"""

__version__ = "1.3.8"
__author__ = "Sim Coaches"
__license__ = "Proprietary"
__copyright__ = "Copyright 2025 Sim Coaches"

import logging
import os
import sys

# Configure logging

# Import main components
from .ui import MainWindow
from .pedals.hardware_input import HardwareInput
from .pedals.output import VirtualJoystick
# Import race_coach module for the Race Coach feature
from .race_coach import RaceCoachWidget

from .main import main 