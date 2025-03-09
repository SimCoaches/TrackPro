"""TrackPro Race Coach - AI-powered racing coach and performance analyzer"""

__version__ = "0.1.0"

# Import main components
from .ui import RaceCoachWidget
from .iracing_api import IRacingAPI
from .data_manager import DataManager
from .model import RacingModel
from .analysis import LapAnalysis
from .superlap import SuperLap 