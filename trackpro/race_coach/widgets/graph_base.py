from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)

class GraphBase(QWidget):
    """Base class for telemetry graph widgets with common debugging functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Child classes should initialize their own plot widgets and data structures
        
        # Debugging settings - DISABLED for clean interface like RaceStudio3
        self.debug_enabled = False  # Changed from True to False to hide debug info bars
        self.debug_info = {}  # Store debugging info for the current graph
        
    def preprocess_telemetry_data(self, lap_data, track_length, channel_names=None, resolution=1):
        """Preprocess and resample telemetry data onto a uniform distance grid.
        
        Args:
            lap_data: Dictionary containing lap telemetry data
            track_length: Track length in meters
            channel_names: List of telemetry channels to preprocess (defaults to standard channels)
            resolution: Distance resolution in meters (defaults to 1m resolution)
            
        Returns:
            Dictionary containing resampled telemetry data with x_m and channel arrays
        """
        if not lap_data or not lap_data.get('points'):
            logger.warning("No telemetry data points to preprocess")
            return None
            
        # Default channel names if not specified
        if channel_names is None:
            channel_names = ['Throttle', 'Brake', 'Steering', 'Speed']
        
        points = lap_data.get('points', [])
        
        # Log basic processing info
        if len(points) > 0:
            logger.debug(f"Processing {len(points)} telemetry points for channels: {channel_names}")
        
        # Extract raw data arrays
        raw_distances = []
        raw_data = {channel: [] for channel in channel_names}
        
        # First pass: determine if we should use track_position or LapDist and calculate track length if needed
        has_lap_dist = any('LapDist' in point for point in points)
        has_track_position = any('track_position' in point for point in points)
        
        # Check if distance data is normalized (0-1) or actual distance
        sample_distances = []
        
        # Get a better sample spread - sample from beginning, middle, and end
        total_points = len(points)
        sample_indices = []
        if total_points >= 10:
            # Sample from different parts of the lap for better detection
            sample_indices = [
                0, 1, 2,  # Start
                total_points // 4, total_points // 4 + 1,  # Quarter
                total_points // 2, total_points // 2 + 1,  # Middle  
                3 * total_points // 4, 3 * total_points // 4 + 1,  # Three quarters
                total_points - 1  # End
            ]
        else:
            sample_indices = list(range(min(total_points, 10)))
        
        for i in sample_indices:
            if i < total_points:
                point = points[i]
                if has_lap_dist and 'LapDist' in point:
                    sample_distances.append(point['LapDist'])
                elif has_track_position and 'track_position' in point:
                    sample_distances.append(point['track_position'])
        
        # Determine if data is normalized or actual distance
        is_normalized = False
        if sample_distances:
            max_sample_dist = max(sample_distances)
            min_sample_dist = min(sample_distances)
            
            # More robust detection: if ALL values are between 0-1, it's normalized
            # Even if the range is small, if all values are 0-1, it's normalized
            all_values_0_to_1 = all(0.0 <= d <= 1.0 for d in sample_distances)
            has_reasonable_spread = (max_sample_dist - min_sample_dist) > 0.05  # Lower threshold
            
            if all_values_0_to_1:
                is_normalized = True
                logger.debug(f"Detected NORMALIZED distance data (all values 0-1). Range: {min_sample_dist:.3f} to {max_sample_dist:.3f}")
            else:
                is_normalized = False
                logger.debug(f"Detected ACTUAL distance data (values outside 0-1). Range: {min_sample_dist:.1f}m to {max_sample_dist:.1f}m")
        
        # Set appropriate track length
        if not track_length or track_length <= 0:
            if is_normalized:
                # For normalized data, use a reasonable track length based on track type
                # Most road courses are 2-6km, ovals are 1-4km
                track_length = 3000  # Default 3km
                logger.debug(f"Using default track length for normalized data: {track_length}m")
            else:
                # For actual distance data, estimate from the data range
                track_length = max(sample_distances) if sample_distances else 1000
                logger.debug(f"Estimated track length from actual distance data: {track_length}m")
        
        for point in points:
            # Get distance value with improved logic
            dist = None
            
            if has_lap_dist and 'LapDist' in point:
                raw_dist = point['LapDist']
            elif has_track_position and 'track_position' in point:
                raw_dist = point['track_position']
            else:
                continue  # Skip points without distance data
                
            # Convert to actual distance if normalized
            if is_normalized:
                dist = raw_dist * track_length  # Convert 0-1 to actual meters
            else:
                dist = raw_dist  # Already in meters
            
            if dist is None or dist < 0:
                continue  # Skip invalid distances
                
            raw_distances.append(dist)
            
            # Extract channel values, checking both original and lowercase key names
            for channel in channel_names:
                value = point.get(channel, point.get(channel.lower(), np.nan))
                raw_data[channel].append(value)
        
        if not raw_distances:
            logger.warning("No valid distance values found in telemetry data")
            return None
        
        # Log distance range for debugging
        min_dist = min(raw_distances)
        max_dist = max(raw_distances)
        logger.debug(f"Final distance range: {min_dist:.1f}m to {max_dist:.1f}m (track_length: {track_length}m)")
        
        for channel in channel_names:
            if raw_data[channel]:
                values = [v for v in raw_data[channel] if v is not None and not np.isnan(v)]
                if values:
                    min_val = min(values)
                    max_val = max(values)
                    avg_val = sum(values) / len(values)
                    logger.debug(f"{channel} range: {min_val:.3f} to {max_val:.3f} (avg: {avg_val:.3f}) from {len(values)} valid points")
                else:
                    logger.warning(f"{channel} has no valid values")
            else:
                logger.warning(f"{channel} has no data points")
            
        # Create uniform distance grid with specified resolution
        # For proper interpolation, use the actual data range
        grid_start = min_dist
        grid_end = max_dist
        
        # Ensure we have a reasonable number of points for interpolation
        distance_span = grid_end - grid_start
        if distance_span > 0:
            # Use resolution that gives us 500-1000 points for good detail
            effective_resolution = max(1.0, distance_span / 800)  # Aim for ~800 points
            num_points = max(100, int(distance_span / effective_resolution) + 1)  # At least 100 points
        else:
            # Fallback for edge case
            grid_start = 0
            grid_end = track_length
            num_points = 1000
            effective_resolution = track_length / 1000
            
        x_m = np.linspace(grid_start, grid_end, num_points)
        
        logger.debug(f"Created distance grid: {len(x_m)} points from {grid_start:.1f}m to {grid_end:.1f}m (resolution: {effective_resolution:.2f}m)")
        
        # Preprocess and resample each channel
        resampled_data = {'x_m': x_m}
        
        for channel in channel_names:
            if not raw_data[channel]:
                logger.warning(f"No data for channel {channel}")
                resampled_data[channel] = np.full_like(x_m, np.nan)
                continue
                
            # Convert to numpy arrays for processing
            x_raw = np.array(raw_distances)
            y_raw = np.array(raw_data[channel])
            
            # Remove NaN values for interpolation
            valid_indices = ~np.isnan(y_raw)
            if not np.any(valid_indices):
                logger.warning(f"No valid data points for channel {channel}")
                resampled_data[channel] = np.full_like(x_m, np.nan)
                continue
                
            x_valid = x_raw[valid_indices]
            y_valid = y_raw[valid_indices]
            
            # Sort by distance for proper interpolation
            sort_idx = np.argsort(x_valid)
            x_valid = x_valid[sort_idx]
            y_valid = y_valid[sort_idx]
            
            # Remove duplicate x values by averaging y values
            if len(x_valid) > 1:
                unique_x, unique_indices, unique_counts = np.unique(x_valid, return_index=True, return_counts=True)
                if len(unique_x) < len(x_valid):  # We have duplicates
                    unique_y = np.zeros_like(unique_x)
                    for i, (idx, count) in enumerate(zip(unique_indices, unique_counts)):
                        if count == 1:
                            unique_y[i] = y_valid[idx]
                        else:
                            # Average the duplicate values
                            end_idx = idx + count
                            unique_y[i] = np.mean(y_valid[idx:end_idx])
                    x_valid = unique_x
                    y_valid = unique_y
                    logger.debug(f"Removed {len(x_raw) - len(x_valid)} duplicate distance values for {channel}")
            
            # Perform linear interpolation to the uniform grid
            try:
                # Ensure we have at least 2 points for interpolation
                if len(x_valid) < 2:
                    logger.warning(f"Not enough valid points for {channel} interpolation: {len(x_valid)}")
                    resampled_data[channel] = np.full_like(x_m, y_valid[0] if len(y_valid) > 0 else np.nan)
                else:
                    # Use numpy's interp function for linear interpolation
                    # Only interpolate within the data range, extrapolate with boundary values
                    resampled_values = np.interp(x_m, x_valid, y_valid, left=y_valid[0], right=y_valid[-1])
                    resampled_data[channel] = resampled_values
                
                # Log resampled data ranges for debugging
                final_values = resampled_data[channel]
                min_resampled = np.nanmin(final_values)
                max_resampled = np.nanmax(final_values)
                avg_resampled = np.nanmean(final_values)
                logger.debug(f"{channel} resampled range: {min_resampled:.3f} to {max_resampled:.3f} (avg: {avg_resampled:.3f})")
                
                logger.debug(f"Resampled {channel} data: {len(x_valid)} raw points to {len(x_m)} interpolated points")
            except Exception as e:
                logger.error(f"Error resampling {channel} data: {e}")
                resampled_data[channel] = np.full_like(x_m, np.nan)
                
        return resampled_data
        
    def validate_telemetry_data(self, lap_data, graph_type):
        """Validate and debug telemetry data before visualization.
        
        Args:
            lap_data: Dictionary containing lap telemetry data or a list of telemetry points
            graph_type: String identifier of the graph type (e.g., 'throttle', 'brake', 'steering', 'speed')
            
        Returns:
            Tuple of (is_valid, cleaned_data, debug_info)
        """
        start_time = time.time()
        
        # Initialize debug info
        debug_info = {
            'graph_type': graph_type,
            'status': 'valid',
            'messages': [],
            'original_points': 0,
            'valid_points': 0,
            'missing_keys': [],
            'value_ranges': {},
            'validation_time_ms': 0,
            'data_gaps': [],
            'repairs_made': 0
        }
        
        # Basic data structure validation
        if not lap_data:
            debug_info['status'] = 'empty'
            debug_info['messages'].append("Empty lap data")
            logger.warning(f"[{graph_type}] Empty lap data provided")
            return False, lap_data, debug_info
        
        # Extract points array - handle both dictionary and list formats
        if isinstance(lap_data, list):
            points = lap_data
            # Create a dict structure for cleaned_data to maintain return format consistency
            cleaned_data = {'points': []}
        else:
            # Original behavior for dictionary format
            points = lap_data.get('points', [])
            cleaned_data = lap_data.copy()
            
        debug_info['original_points'] = len(points)
        
        if not points:
            debug_info['status'] = 'no_points'
            debug_info['messages'].append("No telemetry points in lap data")
            logger.warning(f"[{graph_type}] No telemetry points in lap data")
            return False, lap_data, debug_info
        
        # Validate data keys based on graph type
        required_keys = ['LapDist']  # Common for all graph types
        
        # Add type-specific keys
        if graph_type == 'throttle':
            required_keys.append('Throttle')
        elif graph_type == 'brake':
            required_keys.append('Brake')
        elif graph_type == 'steering':
            required_keys.append('Steering')
        elif graph_type == 'speed':
            required_keys.append('Speed')
        
        # Check for missing keys
        missing_keys = set()
        for point in points:
            for key in required_keys:
                if key not in point and key.lower() not in point:
                    missing_keys.add(key)
        
        if missing_keys:
            debug_info['missing_keys'] = list(missing_keys)
            debug_info['status'] = 'missing_keys'
            debug_info['messages'].append(f"Missing required keys: {', '.join(missing_keys)}")
            logger.warning(f"[{graph_type}] Missing required keys in telemetry data: {missing_keys}")
        
        # Validate data points and attempt to fix issues
        valid_points = []
        value_ranges = {key: {'min': float('inf'), 'max': float('-inf')} for key in required_keys}
        last_valid_distance = -1
        
        for i, point in enumerate(points):
            point_valid = True
            
            # Look for keys in both regular and lowercase versions
            for key in required_keys:
                value = point.get(key, point.get(key.lower(), None))
                
                if value is None:
                    point_valid = False
                    continue
                
                # Update value ranges
                if key in value_ranges:
                    try:
                        value_ranges[key]['min'] = min(value_ranges[key]['min'], float(value))
                        value_ranges[key]['max'] = max(value_ranges[key]['max'], float(value))
                    except (TypeError, ValueError):
                        point_valid = False
                        debug_info['messages'].append(f"Invalid value for {key} at point {i}: {value}")
            
            # Distance validation
            lap_dist = point.get('LapDist', point.get('lapdist', None))
            if lap_dist is not None:
                try:
                    lap_dist = float(lap_dist)
                    
                    # Check for non-increasing distance (issue with telemetry)
                    if lap_dist <= last_valid_distance:
                        point_valid = False
                        debug_info['messages'].append(f"Non-increasing distance at point {i}: {lap_dist} <= {last_valid_distance}")
                    else:
                        last_valid_distance = lap_dist
                        
                        # Check for gaps in distance data
                        if valid_points and lap_dist - valid_points[-1].get('LapDist', 0) > 10:  # Gap > 10m
                            debug_info['data_gaps'].append({
                                'start_idx': len(valid_points) - 1,
                                'end_idx': i,
                                'start_dist': valid_points[-1].get('LapDist', 0),
                                'end_dist': lap_dist
                            })
                except (TypeError, ValueError):
                    point_valid = False
                    debug_info['messages'].append(f"Invalid distance value at point {i}: {lap_dist}")
            
            # Add valid point or fix if possible
            if point_valid:
                valid_points.append(point)
            else:
                # Try to repair point with interpolation if we have neighbors
                if len(valid_points) > 0 and i < len(points) - 1:
                    repaired_point = self._interpolate_point(valid_points[-1], points[i+1], point, required_keys)
                    if repaired_point:
                        valid_points.append(repaired_point)
                        debug_info['repairs_made'] += 1
        
        debug_info['valid_points'] = len(valid_points)
        debug_info['value_ranges'] = value_ranges
        
        # Set overall status based on validation results
        if debug_info['valid_points'] == 0:
            debug_info['status'] = 'all_invalid'
            debug_info['messages'].append("All telemetry points are invalid")
            logger.warning(f"[{graph_type}] All telemetry points are invalid")
            result_valid = False
        elif debug_info['valid_points'] < debug_info['original_points'] * 0.5:
            debug_info['status'] = 'mostly_invalid'
            debug_info['messages'].append(f"Only {debug_info['valid_points']} of {debug_info['original_points']} points are valid")
            logger.warning(f"[{graph_type}] Only {debug_info['valid_points']} of {debug_info['original_points']} points are valid")
            result_valid = True  # Still return as valid but with warning
        else:
            debug_info['status'] = 'valid'
            result_valid = True
        
        # Create a new lap_data with validated points
        cleaned_data['points'] = valid_points
        
        # Track time taken for validation
        debug_info['validation_time_ms'] = round((time.time() - start_time) * 1000, 2)
        
        # Log summary
        if debug_info['status'] != 'valid':
            logger.warning(f"[{graph_type}] Telemetry validation completed: {debug_info['status']} - "
                         f"{debug_info['valid_points']}/{debug_info['original_points']} points valid, "
                         f"{debug_info['repairs_made']} repairs made, {len(debug_info['data_gaps'])} gaps found")
        else:
            logger.info(f"[{graph_type}] Telemetry validation completed: {debug_info['valid_points']}/{debug_info['original_points']} "
                      f"points valid in {debug_info['validation_time_ms']}ms")
        
        self.debug_info = debug_info
        return result_valid, cleaned_data, debug_info

    def _interpolate_point(self, prev_point, next_point, current_point, required_keys):
        """Attempt to interpolate values for an invalid point based on neighbors.
        
        Args:
            prev_point: The valid point before the current point
            next_point: The valid point after the current point
            current_point: The current invalid point
            required_keys: List of required keys
            
        Returns:
            Fixed point dictionary or None if interpolation is not possible
        """
        try:
            # Ensure both neighbors have required distance values
            if 'LapDist' not in prev_point or 'LapDist' not in next_point:
                return None
            
            # Create a new point based on the current one
            fixed_point = current_point.copy()
            
            # Get distance values
            prev_dist = float(prev_point['LapDist'])
            next_dist = float(next_point['LapDist'])
            current_dist = fixed_point.get('LapDist', None)
            
            # If we have a valid current distance, use it for interpolation weight
            if current_dist is not None:
                try:
                    current_dist = float(current_dist)
                    if current_dist > prev_dist and current_dist < next_dist:
                        # Calculate interpolation weight based on distance
                        weight = (current_dist - prev_dist) / (next_dist - prev_dist)
                    else:
                        # Invalid distance, use middle position
                        current_dist = (prev_dist + next_dist) / 2
                        weight = 0.5
                except (TypeError, ValueError):
                    # Invalid distance value, use middle position
                    current_dist = (prev_dist + next_dist) / 2
                    weight = 0.5
            else:
                # No current distance, use middle position
                current_dist = (prev_dist + next_dist) / 2
                weight = 0.5
            
            # Update the distance
            fixed_point['LapDist'] = current_dist
            
            # Interpolate other required values
            for key in required_keys:
                if key == 'LapDist':
                    continue  # Already handled
                    
                # Look for values in both regular and lowercase keys
                prev_value = prev_point.get(key, prev_point.get(key.lower(), None))
                next_value = next_point.get(key, next_point.get(key.lower(), None))
                
                if prev_value is not None and next_value is not None:
                    try:
                        # Linear interpolation
                        fixed_point[key] = prev_value + weight * (next_value - prev_value)
                    except (TypeError, ValueError):
                        # If we can't interpolate, use the previous value
                        fixed_point[key] = prev_value
                elif prev_value is not None:
                    fixed_point[key] = prev_value
                elif next_value is not None:
                    fixed_point[key] = next_value
                else:
                    # Can't fix this value
                    return None
            
            return fixed_point
        except Exception as e:
            logger.error(f"Error interpolating point: {e}")
            return None
    
    def display_message(self, message):
        """Display a message on the graph when no data is available.
        
        Args:
            message: Message to display
        """
        # This is a utility method that should be available to all graph widgets.
        # It requires self.plot_widget to be initialized in the subclass.
        if not hasattr(self, 'plot_widget'):
            logger.error("Cannot display message: plot_widget not initialized")
            return
            
        # Clear any existing data
        # Subclass should ensure the curve variable is properly set (e.g., self.throttle_curve, self.brake_curve)
        for item in self.plot_widget.listDataItems():
            item.setData([], [])
        
        # Add a text item to the center of the plot
        if not hasattr(self, 'message_text') or self.message_text is None:
            self.message_text = pg.TextItem(
                text=message,
                color=(200, 200, 200),
                anchor=(0.5, 0.5),
                fill=(0, 0, 0, 100)
            )
            self.plot_widget.addItem(self.message_text)
        else:
            self.message_text.setText(message)
            self.message_text.setVisible(True)
        
        # Position text in center
        view_range = self.plot_widget.viewRange()
        x_center = (view_range[0][0] + view_range[0][1]) / 2
        y_center = (view_range[1][0] + view_range[1][1]) / 2
        self.message_text.setPos(x_center, y_center)
        
        # Reset view - subclasses should implement this method if needed
        if hasattr(self, 'reset_view'):
            self.reset_view()
            
    def show_debug_stats(self, debug_info=None):
        """Display debug information on the graph.
        
        Args:
            debug_info: Debug information dictionary or None to use the stored debug_info
        """
        # Child classes should implement this to display debug stats on their graph
        pass 