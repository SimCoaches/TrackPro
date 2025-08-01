import logging

logger = logging.getLogger(__name__)

def validate_lap_telemetry(telemetry_points, min_points=10):
    """
    Validates if telemetry data covers a complete lap (0-100% track position).
    
    Args:
        telemetry_points: List of telemetry point dictionaries
        min_points: Minimum number of points required for valid telemetry
        
    Returns:
        tuple: (is_valid, message, diagnostics_dict)
    """
    diagnostics = {
        "total_points": len(telemetry_points) if telemetry_points else 0,
        "min_position": None,
        "max_position": None,
        "max_gap": None,
        "gaps": []
    }
    
    # Check for minimum number of points
    if not telemetry_points or len(telemetry_points) < min_points:
        return False, f"Insufficient telemetry points ({len(telemetry_points) if telemetry_points else 0}/{min_points})", diagnostics
    
    # Extract track positions
    track_positions = []
    for point in telemetry_points:
        pos = point.get('track_position')
        if pos is not None and isinstance(pos, (int, float)) and 0 <= pos <= 1:
            track_positions.append(pos)
    
    if not track_positions:
        return False, "No valid track position data", diagnostics
    
    # Calculate basic statistics
    min_pos = min(track_positions)
    max_pos = max(track_positions)
    diagnostics["min_position"] = min_pos
    diagnostics["max_position"] = max_pos
    
    # Check coverage at start and end
    if min_pos > 0.02:  # Allow 2% tolerance at start
        return False, f"Missing start section (starts at {min_pos:.2f})", diagnostics
        
    if max_pos < 0.98:  # Allow 2% tolerance at end
        return False, f"Missing finish section (ends at {max_pos:.2f})", diagnostics
    
    # Check for large gaps in data
    sorted_positions = sorted(track_positions)
    max_gap = 0
    gaps = []
    
    for i in range(1, len(sorted_positions)):
        gap = sorted_positions[i] - sorted_positions[i-1]
        if gap > 0.01:  # Only track significant gaps (>1%)
            gaps.append((sorted_positions[i-1], sorted_positions[i], gap))
        max_gap = max(max_gap, gap)
    
    diagnostics["max_gap"] = max_gap
    diagnostics["gaps"] = gaps
    
    if max_gap > 0.05:  # 5% maximum allowed gap
        return False, f"Data gap of {max_gap*100:.1f}% detected between positions {gaps[-1][0]:.2f} and {gaps[-1][1]:.2f}", diagnostics
    
    # Check for sparse data overall
    if len(track_positions) < 100:
        return True, "Lap data complete but sparse", diagnostics
    
    return True, "Lap data complete", diagnostics

def calculate_coverage_percentage(telemetry_points):
    """
    Calculates the overall track coverage percentage.
    
    Args:
        telemetry_points: List of telemetry points
        
    Returns:
        float: Percentage of track covered (0-100)
    """
    if not telemetry_points:
        return 0.0
        
    # Extract valid track positions
    positions = [p.get('track_position', 0) for p in telemetry_points 
                if p.get('track_position') is not None 
                and isinstance(p.get('track_position'), (int, float))
                and 0 <= p.get('track_position') <= 1]
    
    if not positions:
        return 0.0
    
    min_pos = min(positions)
    max_pos = max(positions)
    
    # Calculate coverage percentage
    coverage = (max_pos - min_pos) * 100
    
    return min(coverage, 100.0)  # Cap at 100% 