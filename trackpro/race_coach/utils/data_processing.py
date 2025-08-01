"""
Data Processing Utilities for TrackPro

This module contains utilities for processing and normalizing telemetry data
to ensure consistent visualization and analysis.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Union

def smooth_data(data: List[float], window_size: int = 5) -> List[float]:
    """
    Apply moving average smoothing to data.
    
    Args:
        data: List of data points to smooth
        window_size: Size of the smoothing window (must be odd)
        
    Returns:
        List of smoothed data points
    """
    if len(data) < window_size:
        return data
        
    # Ensure window size is odd
    if window_size % 2 == 0:
        window_size += 1
        
    # Use numpy's convolve function for moving average
    kernel = np.ones(window_size) / window_size
    # Use 'same' mode to keep the output the same length as input
    smoothed = np.convolve(data, kernel, mode='same')
    
    # Fix edge effects by using original data at edges
    half_window = window_size // 2
    smoothed[:half_window] = data[:half_window]
    smoothed[-half_window:] = data[-half_window:]
    
    return smoothed.tolist()

def normalize_throttle_brake(throttle_data: List[float], brake_data: List[float]) -> Tuple[List[float], List[float]]:
    """
    Normalize throttle and brake data for visualization.
    
    Args:
        throttle_data: List of throttle values (0-1)
        brake_data: List of brake values (0-1)
        
    Returns:
        Tuple of (normalized_throttle, normalized_brake)
    """
    # Ensure all values are between 0 and 1
    throttle_normalized = np.clip(throttle_data, 0, 1)
    brake_normalized = np.clip(brake_data, 0, 1)
    
    # Ensure they don't overlap significantly (driver can't be at full throttle and brake)
    for i in range(len(throttle_normalized)):
        if throttle_normalized[i] > 0.2 and brake_normalized[i] > 0.2:
            # If both throttle and brake have significant values, reduce the smaller one
            if throttle_normalized[i] >= brake_normalized[i]:
                brake_normalized[i] *= 0.5
            else:
                throttle_normalized[i] *= 0.5
    
    return throttle_normalized.tolist(), brake_normalized.tolist()

def resample_telemetry(telemetry_points: List[Dict[str, Any]], 
                      target_points: int = 500,
                      smooth_window: int = 5) -> List[Dict[str, Any]]:
    """
    Resample telemetry data to have a consistent number of points with smoothing.
    This is critical for proper visualization and comparison.
    
    Args:
        telemetry_points: List of telemetry point dictionaries
        target_points: Desired number of points after resampling
        smooth_window: Window size for smoothing
        
    Returns:
        List of resampled and smoothed telemetry dictionaries
    """
    if not telemetry_points:
        return []
        
    # If we have fewer points than target, don't reduce resolution
    if len(telemetry_points) <= target_points:
        # Just apply smoothing
        for key in ['throttle', 'brake']:
            if all(key in point for point in telemetry_points):
                values = [point[key] for point in telemetry_points]
                smoothed = smooth_data(values, smooth_window)
                for i, point in enumerate(telemetry_points):
                    point[key] = smoothed[i]
        return telemetry_points
    
    # Sort by LapDist if available, otherwise by track_position
    if 'LapDist' in telemetry_points[0]:
        telemetry_points.sort(key=lambda p: p['LapDist'])
    elif 'track_position' in telemetry_points[0]:
        telemetry_points.sort(key=lambda p: p['track_position'])
    
    # Extract the distance values (either LapDist or track_position)
    if 'LapDist' in telemetry_points[0]:
        distances = np.array([point['LapDist'] for point in telemetry_points])
    else:
        distances = np.array([point['track_position'] for point in telemetry_points])
    
    # Create evenly spaced distances for resampling
    min_dist = distances.min()
    max_dist = distances.max()
    new_distances = np.linspace(min_dist, max_dist, target_points)
    
    # Create new dictionary to hold resampled data
    resampled_points = []
    
    # Identify the fields we need to resample
    numeric_fields = []
    for key in telemetry_points[0].keys():
        # Only resample numeric fields
        try:
            if isinstance(telemetry_points[0][key], (int, float)):
                numeric_fields.append(key)
        except:
            pass
            
    # Prepare interpolation for each field
    field_values = {}
    for field in numeric_fields:
        try:
            values = np.array([point.get(field, 0) for point in telemetry_points])
            # Interpolate to new distances
            interp_values = np.interp(new_distances, distances, values)
            field_values[field] = interp_values
        except Exception as e:
            print(f"Error interpolating field {field}: {e}")
    
    # Apply smoothing to throttle and brake
    if 'throttle' in field_values and 'brake' in field_values:
        field_values['throttle'] = smooth_data(field_values['throttle'], smooth_window)
        field_values['brake'] = smooth_data(field_values['brake'], smooth_window)
        
        # Normalize throttle and brake values
        field_values['throttle'], field_values['brake'] = normalize_throttle_brake(
            field_values['throttle'], field_values['brake']
        )
    
    # Create new points with resampled values
    for i in range(target_points):
        new_point = {}
        for field in numeric_fields:
            if field in field_values:
                new_point[field] = field_values[field][i]
        
        # Set the correct distance field
        if 'LapDist' in telemetry_points[0]:
            new_point['LapDist'] = new_distances[i]
        if 'track_position' in telemetry_points[0]:
            new_point['track_position'] = new_distances[i]
        
        resampled_points.append(new_point)
    
    return resampled_points 