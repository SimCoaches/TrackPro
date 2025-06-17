"""
Core module for the Real-Time AI Voice Coach.
"""

import logging
import os
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

        print(f"🤖 [AI COACH INIT] Initializing AI Coach with SuperLap: {superlap_id}")
        self.superlap_id = superlap_id
        self.advice_interval = advice_interval  # Reduced from 8.0 to 2.0 seconds
        
        self.superlap_points: List[Dict[str, Any]] = []
        self.sorted_track_positions: List[float] = []
        
        self._load_superlap_data()
        self.last_advice_time: float = 0
        
        # Track recent advice to avoid repetition
        self.recent_advice_types: List[str] = []
        self.last_track_position: float = 0.0
        
        if self.superlap_points:
            print(f"✅ [AI COACH READY] AI Coach loaded with {len(self.superlap_points)} reference points")
            print(f"🎙️ [AI COACH READY] Will provide coaching every {advice_interval}s when needed")
        else:
            print(f"❌ [AI COACH ERROR] Failed to load SuperLap data!")
        
        # Initialize position tracking for distance-based coaching
        self._last_advice_position = 0.0

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
        # Only log entry on first call or every 5 seconds
        if not hasattr(self, '_telemetry_count'):
            self._telemetry_count = 0
            logger.info(f"🎙️ [AI COACH STARTED] Beginning real-time telemetry processing")
            
        self._telemetry_count += 1
        
        # Only log occasionally instead of every frame
        if self._telemetry_count == 1 or self._telemetry_count % 300 == 0:  # First time and every 5 seconds at 60Hz
            logger.debug(f"🎙️ [AI COACH ENTRY] process_realtime_telemetry called with: {current_telemetry}")
        
        if not self.superlap_points:
            logger.warning("🎙️ [AI COACH ERROR] No superlap data loaded, cannot provide coaching.")
            print("🎙️ [AI COACH ERROR] No superlap data loaded, cannot provide coaching.")
            return

        current_track_pos = current_telemetry.get('track_position')
        if current_track_pos is None:
            logger.debug(f"🎙️ [AI COACH ERROR] No track position in current telemetry. Keys: {list(current_telemetry.keys())}")
            return
        
        # Only log processing details occasionally
        if self._telemetry_count % 300 == 0:  # Every 5 seconds at 60Hz
            logger.debug(f"🎙️ [AI COACH DEBUG] Processing telemetry #{self._telemetry_count}: track_pos={current_track_pos:.3f}, speed={current_telemetry.get('speed', 0):.1f}")
            print(f"🤖 [AI COACH ACTIVE] Processing telemetry #{self._telemetry_count}: position={current_track_pos:.3f}, speed={current_telemetry.get('speed', 0):.1f} km/h")

        superlap_telemetry = self._find_closest_superlap_point(current_track_pos)
        if not superlap_telemetry:
            return

        current_time = time.time()
        
        # Get telemetry differences
        speed_diff = current_telemetry.get('speed', 0) - superlap_telemetry.get('speed', 0)
        throttle_diff = current_telemetry.get('throttle', 0) - superlap_telemetry.get('throttle', 0)
        brake_diff = current_telemetry.get('brake', 0) - superlap_telemetry.get('brake', 0)
        
        # Add detailed debug every 60 frames (1 second at 60Hz) only for significant differences
        if self._telemetry_count % 60 == 0 and (abs(speed_diff) > 5 or abs(throttle_diff) > 0.1 or abs(brake_diff) > 0.1):
            logger.info(f"🎯 [AI COACH COMPARE] Position {current_track_pos:.3f}:")
            logger.info(f"   You: Speed={current_telemetry.get('speed', 0):.1f} km/h, Throttle={current_telemetry.get('throttle', 0):.2f}, Brake={current_telemetry.get('brake', 0):.2f}")
            logger.info(f"   Ref: Speed={superlap_telemetry.get('speed', 0):.1f} km/h, Throttle={superlap_telemetry.get('throttle', 0):.2f}, Brake={superlap_telemetry.get('brake', 0):.2f}")
            logger.info(f"   Diff: Speed={speed_diff:+.1f} km/h, Throttle={throttle_diff:+.2f}, Brake={brake_diff:+.2f}")
        
        # Only show console output for very significant differences (reduce spam)
        if abs(speed_diff) > 20:  # Increased threshold from 10 to 20 km/h
            print(f"🏁 [MAJOR SPEED DIFF] You: {current_telemetry.get('speed', 0):.1f} km/h | SuperLap: {superlap_telemetry.get('speed', 0):.1f} km/h | Diff: {speed_diff:+.1f} km/h")
        
        # Determine coaching priority (like a real engineer)
        advice_type, should_coach_now = self._analyze_coaching_priority(
            speed_diff, throttle_diff, brake_diff, current_time
        )
        
        # Only log analysis for meaningful differences or occasionally
        if should_coach_now or self._telemetry_count % 300 == 0:
            logger.debug(f"🎙️ [AI COACH ANALYSIS] Speed diff: {speed_diff:.1f} km/h, Throttle diff: {throttle_diff:.2f}, Brake diff: {brake_diff:.2f}")
            logger.debug(f"🎙️ [AI COACH DECISION] Advice type: {advice_type}, Should coach: {should_coach_now}")
        
        # Add more detailed logging when coaching is NOT triggered (less frequent)
        if not should_coach_now and self._telemetry_count % 600 == 0:  # Every 10 seconds instead of 3
            distance_since_last = abs(current_track_pos - getattr(self, '_last_advice_position', 0.0))
            logger.info(f"📊 [AI COACH STATUS] Not coaching - Type: {advice_type}, Distance since last: {distance_since_last*550:.1f}m (track: 550m)")
        
        if should_coach_now:
            logger.info(f"🎙️ [AI COACH TRIGGER] Generating coaching advice for {advice_type}")
            print(f"\n🎙️ [AI COACH TRIGGER] Generating coaching advice for {advice_type}")
            print(f"   Speed diff: {speed_diff:+.1f} km/h | Throttle diff: {throttle_diff:+.2f} | Brake diff: {brake_diff:+.2f}")
            
            # Calculate and show distance since last advice
            distance_since_last = abs(current_track_pos - getattr(self, '_last_advice_position', 0.0))
            print(f"   Distance since last advice: {distance_since_last*550:.1f}m")
            
            # Generate context-aware advice
            advice = openai_client.get_coaching_advice(current_telemetry, superlap_telemetry)

            if advice:
                self.last_advice_time = current_time
                self._track_advice_type(advice_type)
                logger.info(f"🎙️ [COACHING ADVICE] ({advice_type}): {advice}")
                
                # CONSOLE OUTPUT - This is what we want to see!
                print(f"🗣️ [AI COACH SAYS]: \"{advice}\"")
                
                logger.debug(f"🎙️ [TTS] Generating audio for: {advice}")
                print(f"🔊 [AUDIO] Generating speech for: \"{advice}\"")
                
                # Use the new improved audio system with crash protection
                try:
                    success = elevenlabs_client.speak_text(advice, interrupt_current=True)
                    if success:
                        logger.info(f"🎙️ [TTS SUCCESS] Audio queued for playback")
                        print(f"🔊 [AUDIO SUCCESS] Audio queued successfully")
                    else:
                        logger.error("🎙️ [TTS ERROR] Failed to queue audio for playback")
                        print(f"❌ [AUDIO ERROR] Failed to queue audio")
                except Exception as e:
                    logger.error(f"🎙️ [TTS EXCEPTION] Audio system error: {e}")
                    print(f"❌ [AUDIO EXCEPTION] Audio system error: {e}")
            else:
                logger.error(f"🎙️ [OPENAI ERROR] Failed to generate coaching advice")
                print(f"❌ [OPENAI ERROR] Failed to generate coaching advice")
        
        # Update position tracking
        self.last_track_position = current_track_pos

    def _analyze_coaching_priority(self, speed_diff: float, throttle_diff: float, brake_diff: float, current_time: float) -> Tuple[str, bool]:
        """
        Analyze coaching priority like a real race engineer - now with improved debouncing!
        
        Returns:
            tuple: (advice_type, should_coach_now)
        """
        # Check if audio is currently playing - don't interrupt unless critical
        if hasattr(elevenlabs_client, 'is_speaking') and elevenlabs_client.is_speaking():
            # Only interrupt for extremely critical issues
            if speed_diff < -25:  # Only if 25+ km/h slower (was 15)
                logger.info("🎙️ [PRIORITY] Interrupting audio for critical speed loss")
            else:
                return "AUDIO_PLAYING", False
        
        # Enhanced distance-based debouncing
        distance_since_last = abs(self.last_track_position - getattr(self, '_last_advice_position', 0.0))
        
        # Time-based debouncing as backup (increased minimums)
        time_since_last = current_time - self.last_advice_time
        
        # CRITICAL: Major speed loss (immediate coaching but less frequent)
        if speed_diff < -20:  # Increased threshold from -15 to -20 km/h
            min_distance = 0.036  # ~20m at 550m track (was 10m)
            min_time = 3.0  # Minimum 3 seconds between critical advice
            should_coach = distance_since_last > min_distance and time_since_last > min_time
            return "CRITICAL_SPEED_LOSS", should_coach
            
        # HIGH: Significant braking/throttle errors (less frequent)
        if brake_diff > 0.4 or throttle_diff < -0.4:  # Increased thresholds
            min_distance = 0.073  # ~40m at 550m track (was 30m)
            min_time = 4.0  # Minimum 4 seconds
            should_coach = distance_since_last > min_distance and time_since_last > min_time
            return "HIGH_PRIORITY", should_coach
        
        # MEDIUM: Moderate differences (much less frequent)
        if abs(speed_diff) > 12 or abs(throttle_diff) > 0.3:  # Increased thresholds
            min_distance = 0.109  # ~60m at 550m track (was 50m)
            min_time = 6.0  # Minimum 6 seconds
            should_coach = distance_since_last > min_distance and time_since_last > min_time
            return "MEDIUM_PRIORITY", should_coach
        
        # LOW: Minor differences (much longer interval)
        if abs(speed_diff) > 8 or abs(throttle_diff) > 0.25:  # Increased thresholds
            min_distance = 0.182  # ~100m at 550m track
            min_time = 10.0  # Minimum 10 seconds
            should_coach = distance_since_last > min_distance and time_since_last > min_time
            return "LOW_PRIORITY", should_coach
        
        return "NO_COACHING", False

    def _track_advice_type(self, advice_type: str):
        """Track recent advice to avoid spam."""
        self.recent_advice_types.append(advice_type)
        # Keep only last 3 advice types
        if len(self.recent_advice_types) > 3:
            self.recent_advice_types.pop(0)
        
        # Store position where advice was given
        self._last_advice_position = self.last_track_position

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