"""
Core module for the Real-Time AI Voice Coach.
"""

import logging
import time
import bisect
from typing import List, Dict, Any, Tuple

# Use a try-except block for the import to handle different environments
try:
    from Supabase.database import get_super_lap_telemetry_points
except (ImportError, ModuleNotFoundError):
    # Fallback for when running outside the main app context or if structure changes
    # This assumes a different path or that the function might be moved.
    # For now, we'll log a warning and the class will fail gracefully.
    logging.warning("Could not import 'get_super_lap_telemetry_points' from 'Supabase.database'")
    get_super_lap_telemetry_points = None

from . import openai_client
from . import elevenlabs_client

logger = logging.getLogger(__name__)

class AICoach:
    """
    Analyzes real-time telemetry against a superlap and provides voice coaching.
    """
    def __init__(self, superlap_id: str, advice_interval: float = 2.0):
        """
        Initializes the AI Coach.

        Args:
            superlap_id (str): The UUID of the superlap to use as a benchmark.
            advice_interval (float): Minimum seconds between coaching advice.
        """
        if get_super_lap_telemetry_points is None:
            raise ImportError("AI Coach cannot function without get_super_lap_telemetry_points.")

        self.superlap_id = superlap_id
        self.advice_interval = advice_interval  # Reduced from 8.0 to 2.0 seconds
        
        self.superlap_points: List[Dict[str, Any]] = []
        self.sorted_track_positions: List[float] = []
        
        self._load_superlap_data()
        self.last_advice_time: float = 0
        
        # Track recent advice to avoid repetition
        self.recent_advice_types: List[str] = []
        self.last_track_position: float = 0.0

    def _load_superlap_data(self):
        """
        Fetches and prepares the superlap telemetry data.
        """
        logger.info(f"Loading superlap telemetry data for superlap_id: {self.superlap_id}")
        points, message = get_super_lap_telemetry_points(self.superlap_id)

        if not points:
            logger.error(f"Failed to load superlap data: {message}")
            return

        # Sort points by track position for efficient searching
        self.superlap_points = sorted(points, key=lambda p: p.get('track_position', 0))
        self.sorted_track_positions = [p.get('track_position', 0) for p in self.superlap_points]
        logger.info(f"Successfully loaded and sorted {len(self.superlap_points)} superlap telemetry points.")

    def _find_closest_superlap_point(self, current_track_position: float) -> Dict[str, Any]:
        """
        Finds the closest superlap telemetry point to the current track position.

        Args:
            current_track_position (float): The driver's current track position (0-1).

        Returns:
            The closest superlap telemetry point dictionary, or None if not found.
        """
        if not self.sorted_track_positions:
            return None

        # Find insertion point for current_track_position
        idx = bisect.bisect_left(self.sorted_track_positions, current_track_position)

        # Handle edge cases
        if idx == 0:
            return self.superlap_points[0]
        if idx == len(self.sorted_track_positions):
            return self.superlap_points[-1]

        # Compare the two nearest points
        before = self.superlap_points[idx - 1]
        after = self.superlap_points[idx]
        
        pos_before = before.get('track_position', 0)
        pos_after = after.get('track_position', 0)

        if (current_track_position - pos_before) < (pos_after - current_track_position):
            return before
        else:
            return after

    def process_realtime_telemetry(self, current_telemetry: Dict[str, Any]):
        """
        Processes a real-time telemetry snapshot to decide if coaching is needed.
        Like a real race engineer - immediate feedback on critical issues.
        """
        if not self.superlap_points:
            logger.warning("No superlap data loaded, cannot provide coaching.")
            return

        current_track_pos = current_telemetry.get('track_position')
        if current_track_pos is None:
            logger.debug("No track position in current telemetry.")
            return

        superlap_telemetry = self._find_closest_superlap_point(current_track_pos)
        if not superlap_telemetry:
            return

        current_time = time.time()
        
        # Get telemetry differences
        speed_diff = current_telemetry.get('speed', 0) - superlap_telemetry.get('speed', 0)
        throttle_diff = current_telemetry.get('throttle', 0) - superlap_telemetry.get('throttle', 0)
        brake_diff = current_telemetry.get('brake', 0) - superlap_telemetry.get('brake', 0)
        
        # Determine coaching priority (like a real engineer)
        advice_type, should_coach_now = self._analyze_coaching_priority(
            speed_diff, throttle_diff, brake_diff, current_time
        )
        
        if should_coach_now:
            # Generate context-aware advice
            advice = openai_client.get_coaching_advice(current_telemetry, superlap_telemetry)

            if advice:
                self.last_advice_time = current_time
                self._track_advice_type(advice_type)
                logger.info(f"COACHING ADVICE ({advice_type}): {advice}")
                
                audio_stream = elevenlabs_client.text_to_speech_stream(advice)
                if audio_stream:
                    elevenlabs_client.play_audio_stream(audio_stream)
                else:
                    logger.error("Failed to generate audio stream for advice.")
        
        # Update position tracking
        self.last_track_position = current_track_pos

    def _analyze_coaching_priority(self, speed_diff: float, throttle_diff: float, brake_diff: float, current_time: float) -> Tuple[str, bool]:
        """
        Analyze coaching priority like a real race engineer.
        
        Returns:
            tuple: (advice_type, should_coach_now)
        """
        # CRITICAL: Major speed loss (immediate coaching)
        if speed_diff < -15:  # 15+ km/h slower than optimal
            return "CRITICAL_SPEED_LOSS", True
            
        # HIGH: Significant braking/throttle errors (quick coaching)
        if brake_diff > 0.3 or throttle_diff < -0.3:  # Braking when shouldn't or missing throttle
            time_since_last = current_time - self.last_advice_time
            return "HIGH_PRIORITY", time_since_last > 1.0  # 1 second for high priority
        
        # MEDIUM: Moderate differences (normal interval)
        if abs(speed_diff) > 8 or abs(throttle_diff) > 0.2:
            time_since_last = current_time - self.last_advice_time
            return "MEDIUM_PRIORITY", time_since_last > self.advice_interval  # 2 seconds
        
        # LOW: Minor differences (longer interval)
        if abs(speed_diff) > 5 or abs(throttle_diff) > 0.15:
            time_since_last = current_time - self.last_advice_time
            return "LOW_PRIORITY", time_since_last > (self.advice_interval * 2)  # 4 seconds
        
        return "NO_COACHING", False

    def _track_advice_type(self, advice_type: str):
        """Track recent advice to avoid spam."""
        self.recent_advice_types.append(advice_type)
        # Keep only last 3 advice types
        if len(self.recent_advice_types) > 3:
            self.recent_advice_types.pop(0)

if __name__ == '__main__':
    # This is an example of how to use the AICoach.
    # It requires a valid superlap_id and API keys set as environment variables.
    logging.basicConfig(level=logging.INFO)
    
    SUPERLAP_ID_TO_TEST = os.getenv("TEST_SUPERLAP_ID", "a-valid-superlap-uuid")
    
    if "a-valid-superlap-uuid" in SUPERLAP_ID_TO_TEST:
        logger.warning("Please set the TEST_SUPERLAP_ID environment variable for a meaningful test.")
    else:
        logger.info("Initializing AI Coach for testing...")
        try:
            coach = AICoach(superlap_id=SUPERLAP_ID_TO_TEST)
            
            if coach.superlap_points:
                logger.info("AI Coach initialized successfully.")
                
                # Simulate receiving a few telemetry points
                mock_telemetry_points = [
                    {'track_position': 0.15, 'speed': 120, 'throttle': 1.0, 'brake': 0.0, 'steering': 0.1},
                    {'track_position': 0.50, 'speed': 200, 'throttle': 1.0, 'brake': 0.0, 'steering': -0.05},
                    {'track_position': 0.85, 'speed': 90, 'throttle': 0.1, 'brake': 0.9, 'steering': 0.2},
                ]
                
                for point in mock_telemetry_points:
                    logger.info(f"--- Processing mock telemetry at track position: {point['track_position']} ---")
                    coach.process_realtime_telemetry(point)
                    time.sleep(2) # Wait a bit between points

            else:
                logger.error("AI Coach failed to initialize or load superlap data.")

        except ImportError as e:
            logger.error(f"Could not run test due to import error: {e}")
        except Exception as e:
            logger.error(f"An error occurred during testing: {e}", exc_info=True) 