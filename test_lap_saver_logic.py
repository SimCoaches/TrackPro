# test_lap_saver_logic.py
import logging
import sys # Required to setup a basic logger if not already configured
from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver

# --- Basic Logger Setup ---
# This is to prevent "No handlers found for logger..." errors if IRacingLapSaver tries to log
# and no global logger is configured. TrackPro normally sets this up.
logger = logging.getLogger('trackpro.race_coach.iracing_lap_saver')
if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Or logging.DEBUG for more detail


# --- Test Data ---
# Test case 1: Good coverage using LapDistPct
mock_lap_frames_good_coverage = []
for i in range(100): # Simulate points covering most of the lap
    mock_lap_frames_good_coverage.append({'LapDistPct': i / 100.0, 'Speed': 50 + i, 'RPM': 3000 + i*50})

# Test case 2: Poor coverage
mock_lap_frames_poor_coverage = [
    {'LapDistPct': 0.01, 'Speed': 30, 'RPM': 2000},
    {'LapDistPct': 0.05, 'Speed': 32, 'RPM': 2100},
    {'LapDistPct': 0.10, 'Speed': 35, 'RPM': 2200},
] * 5 # Make it 15 points, so it's not rejected for too few points, but still poor coverage

# Test case 3: Mixed keys and missing data for some points
mock_lap_frames_mixed_keys = [
    {'track_position': 0.01, 'Speed': 30, 'RPM': 2000}, # Original key
    {'LapDistPct': 0.15, 'Speed': 30, 'RPM': 2000},     # Fallback key
    {'LapDistPct': 0.30, 'Speed': 30, 'RPM': 2000},
    {'some_other_key': 0.45, 'Speed': 30, 'RPM': 2000}, # Missing position data
    {'LapDistPct': 0.60, 'Speed': 30, 'RPM': 2000},
] * 4 # 20 points total

# Test case 4: Data that should pass validation (if not out/in lap)
# More than 20 points, good coverage, valid speed
mock_lap_frames_should_pass = []
for i in range(80): # 80 points
    mock_lap_frames_should_pass.append({'LapDistPct': i / 100.0, 'Speed': 60 + i, 'RPM': 3500 + i*40})


# --- Test Execution ---
if __name__ == "__main__":
    saver = IRacingLapSaver()
    # Note: The saver's internal state like _user_id, _current_session_id, etc.,
    # are not set here, as we are testing specific methods in isolation.
    # _validate_lap_data doesn't directly use them but _save_lap_data would.

    print("--- Testing _calculate_track_coverage ---")
    coverage1 = saver._calculate_track_coverage(mock_lap_frames_good_coverage)
    print(f"Coverage for 'good_coverage' data: {coverage1:.2f}")

    coverage2 = saver._calculate_track_coverage(mock_lap_frames_poor_coverage)
    print(f"Coverage for 'poor_coverage' data: {coverage2:.2f}")

    coverage3 = saver._calculate_track_coverage(mock_lap_frames_mixed_keys)
    print(f"Coverage for 'mixed_keys' data: {coverage3:.2f}")

    print("\n--- Testing _validate_lap_data ---")
    # Test with a "normal" lap number (e.g., lap 1)
    
    # Test 1: Good coverage, should be valid if it were a normal lap
    is_valid1, reason1 = saver._validate_lap_data(mock_lap_frames_good_coverage, lap_number_for_validation=1)
    print(f"Validation for 'good_coverage' (Lap 1): Valid={is_valid1}, Reason='{reason1}'")

    # Test 2: Poor coverage, should be invalid
    is_valid2, reason2 = saver._validate_lap_data(mock_lap_frames_poor_coverage, lap_number_for_validation=2)
    print(f"Validation for 'poor_coverage' (Lap 2): Valid={is_valid2}, Reason='{reason2}'")

    # Test 3: Mixed keys, should calculate coverage based on available data
    is_valid3, reason3 = saver._validate_lap_data(mock_lap_frames_mixed_keys, lap_number_for_validation=3)
    print(f"Validation for 'mixed_keys' (Lap 3): Valid={is_valid3}, Reason='{reason3}'")

    # Test 4: "Should pass" data
    is_valid4, reason4 = saver._validate_lap_data(mock_lap_frames_should_pass, lap_number_for_validation=4)
    print(f"Validation for 'should_pass' (Lap 4): Valid={is_valid4}, Reason='{reason4}'")

    # Test 5: Too few points (less than 20)
    mock_lap_frames_too_few = [{'LapDistPct': 0.1 * i, 'Speed': 50, 'RPM': 3000} for i in range(5)] # 5 points
    is_valid5, reason5 = saver._validate_lap_data(mock_lap_frames_too_few, lap_number_for_validation=5)
    print(f"Validation for 'too_few_points' (Lap 5): Valid={is_valid5}, Reason='{reason5}'") 