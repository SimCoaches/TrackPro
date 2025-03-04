"""TrackPro - Racing Pedal Calibration Software"""

__version__ = "1.2.4"
__author__ = "Lawrence Thomas"

# Import main components
from .ui import MainWindow
from .hardware_input import HardwareInput
from .output import VirtualJoystick

from .main import main 