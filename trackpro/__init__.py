"""TrackPro - Advanced Pedal Input Mapping Software"""

__version__ = "1.5.1"
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
# Import MainWindow directly from ui.py file to avoid conflict with ui/ directory
import sys
import os
import importlib.util

# Get the path to the ui.py file and import it directly
ui_file_path = os.path.join(os.path.dirname(__file__), 'ui.py')
spec = importlib.util.spec_from_file_location("trackpro.ui", ui_file_path)
ui_module = importlib.util.module_from_spec(spec)

# Add the trackpro package to sys.modules so relative imports work
sys.modules['trackpro.ui'] = ui_module
spec.loader.exec_module(ui_module)
MainWindow = ui_module.MainWindow
from .pedals.hardware_input import HardwareInput
from .pedals.output import VirtualJoystick
# Import race_coach module for the Race Coach feature
from .race_coach import RaceCoachWidget

from .main import main 