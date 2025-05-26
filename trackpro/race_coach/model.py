import logging
import numpy as np
import json
import os
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class RacingModel:
    """Machine Learning model for race data analysis and improvement suggestions."""
    
    def __init__(self, data_manager=None):
        """Initialize the racing model.
        
        Args:
            data_manager: The data manager instance for accessing stored data
        """
        self.data_manager = data_manager
        self.model_path = None
        
        logger.info("Racing model initialized")
    
    def analyze_lap(self, lap_telemetry):
        """Analyze a lap's telemetry data.
        
        Args:
            lap_telemetry: Dictionary containing telemetry data for a lap
            
        Returns:
            Dictionary with analysis results
        """
        # This is a placeholder implementation that will be replaced with actual ML
        # For now, we'll implement a simple analysis based on basic principles
        
        logger.info("Analyzing lap telemetry data")
        
        # Extract relevant data from telemetry
        speed_data = self._extract_from_telemetry(lap_telemetry, 'speed')
        throttle_data = self._extract_from_telemetry(lap_telemetry, 'Throttle')
        brake_data = self._extract_from_telemetry(lap_telemetry, 'Brake')
        steering_data = self._extract_from_telemetry(lap_telemetry, 'steering')
        position_data = self._extract_position_data(lap_telemetry)
        
        # Simple analysis
        analysis = {
            'max_speed': np.max(speed_data) if len(speed_data) > 0 else 0,
            'avg_speed': np.mean(speed_data) if len(speed_data) > 0 else 0,
            'throttle_usage': np.mean(throttle_data) if len(throttle_data) > 0 else 0,
            'brake_usage': np.mean(brake_data) if len(brake_data) > 0 else 0,
            'steering_consistency': np.std(steering_data) if len(steering_data) > 0 else 0,
            'track_segments': self._segment_track(position_data) if len(position_data) > 0 else [],
        }
        
        # Identify potential improvement areas (simplified for now)
        improvement_areas = []
        
        # Check for excessive braking
        if np.mean(brake_data) > 0.3:  # Arbitrary threshold
            improvement_areas.append({
                'type': 'excessive_braking',
                'description': 'Excessive Brake usage detected. Consider using more trail braking techniques.',
                'confidence': 0.7
            })
        
        # Check for poor throttle application
        if np.mean(throttle_data) < 0.6:  # Arbitrary threshold
            improvement_areas.append({
                'type': 'poor_throttle',
                'description': 'Throttle usage below optimal levels. Consider earlier application out of corners.',
                'confidence': 0.65
            })
        
        # Check for inconsistent steering
        if np.std(steering_data) > 0.2:  # Arbitrary threshold
            improvement_areas.append({
                'type': 'inconsistent_steering',
                'description': 'Steering inputs are inconsistent. Focus on smoother inputs for better balance.',
                'confidence': 0.8
            })
        
        analysis['improvement_areas'] = improvement_areas
        
        return analysis
    
    def _extract_from_telemetry(self, telemetry, key):
        """Extract a specific data series from telemetry.
        
        Args:
            telemetry: Telemetry data dictionary
            key: The key to extract
            
        Returns:
            Numpy array of values
        """
        if not telemetry or key not in telemetry:
            return np.array([])
            
        # If telemetry is a time series dictionary
        if isinstance(telemetry[key], (list, np.ndarray)):
            return np.array(telemetry[key])
        
        # If telemetry is a list of data points
        if isinstance(telemetry, list) and len(telemetry) > 0 and key in telemetry[0]:
            return np.array([point[key] for point in telemetry if key in point])
            
        return np.array([])
    
    def _extract_position_data(self, telemetry):
        """Extract position data from telemetry.
        
        Args:
            telemetry: Telemetry data dictionary
            
        Returns:
            List of position tuples (x, y, z)
        """
        positions = []
        
        # If telemetry has individual position keys
        if 'position_x' in telemetry and 'position_y' in telemetry:
            x_data = self._extract_from_telemetry(telemetry, 'position_x')
            y_data = self._extract_from_telemetry(telemetry, 'position_y')
            z_data = self._extract_from_telemetry(telemetry, 'position_z')
            
            # Ensure all arrays are the same length
            min_len = min(len(x_data), len(y_data))
            if z_data.size > 0:
                min_len = min(min_len, len(z_data))
            
            for i in range(min_len):
                z_val = z_data[i] if z_data.size > i else 0
                positions.append((x_data[i], y_data[i], z_val))
                
        # If telemetry has position as objects
        elif 'position' in telemetry:
            pos_data = telemetry['position']
            if isinstance(pos_data, list):
                for pos in pos_data:
                    if isinstance(pos, dict) and 'x' in pos and 'y' in pos:
                        x, y = pos['x'], pos['y']
                        z = pos.get('z', 0)
                        positions.append((x, y, z))
        
        return positions
    
    def _segment_track(self, position_data, num_segments=20):
        """Segment the track into sections based on position data.
        
        Args:
            position_data: List of position tuples (x, y, z)
            num_segments: Number of segments to divide the track into
            
        Returns:
            List of segments with average properties
        """
        if not position_data or len(position_data) < num_segments:
            return []
            
        # Simple approach: divide data into equal chunks
        chunk_size = len(position_data) // num_segments
        segments = []
        
        for i in range(num_segments):
            start_idx = i * chunk_size
            end_idx = (i + 1) * chunk_size if i < num_segments - 1 else len(position_data)
            
            segment_positions = position_data[start_idx:end_idx]
            
            # Calculate average position (center of segment)
            if segment_positions:
                avg_x = sum(pos[0] for pos in segment_positions) / len(segment_positions)
                avg_y = sum(pos[1] for pos in segment_positions) / len(segment_positions)
                
                segments.append({
                    'id': i,
                    'position': (avg_x, avg_y),
                    'length': len(segment_positions)
                })
        
        return segments
    
    def compare_laps(self, reference_lap, comparison_lap):
        """Compare two laps to identify differences.
        
        Args:
            reference_lap: Telemetry data for the reference lap
            comparison_lap: Telemetry data for the lap to compare
            
        Returns:
            Dictionary with comparison results
        """
        logger.info("Comparing laps")
        
        # Simple comparison for now
        ref_speed = self._extract_from_telemetry(reference_lap, 'speed')
        comp_speed = self._extract_from_telemetry(comparison_lap, 'speed')
        
        # Resample to the same length if needed
        if len(ref_speed) != len(comp_speed) and len(ref_speed) > 0 and len(comp_speed) > 0:
            # Use the shorter one as reference for resampling
            if len(ref_speed) < len(comp_speed):
                comp_speed = self._resample_array(comp_speed, len(ref_speed))
            else:
                ref_speed = self._resample_array(ref_speed, len(comp_speed))
        
        # Calculate speed differences
        speed_diff = []
        if len(ref_speed) == len(comp_speed) and len(ref_speed) > 0:
            speed_diff = comp_speed - ref_speed
            
        # Find sections where comparison lap is faster/slower
        faster_sections = []
        slower_sections = []
        
        if len(speed_diff) > 0:
            # Simple approach: identify continuous sections with significant differences
            threshold = 5.0  # Speed difference threshold in mph/kph
            current_section = None
            
            for i, diff in enumerate(speed_diff):
                if diff > threshold and current_section != 'faster':
                    if current_section == 'slower':
                        slower_sections.append({
                            'start_idx': section_start,
                            'end_idx': i - 1,
                            'avg_diff': np.mean(speed_diff[section_start:i])
                        })
                    current_section = 'faster'
                    section_start = i
                elif diff < -threshold and current_section != 'slower':
                    if current_section == 'faster':
                        faster_sections.append({
                            'start_idx': section_start,
                            'end_idx': i - 1,
                            'avg_diff': np.mean(speed_diff[section_start:i])
                        })
                    current_section = 'slower'
                    section_start = i
                elif abs(diff) < threshold/2 and current_section is not None:
                    # End current section
                    if current_section == 'faster':
                        faster_sections.append({
                            'start_idx': section_start,
                            'end_idx': i - 1,
                            'avg_diff': np.mean(speed_diff[section_start:i])
                        })
                    elif current_section == 'slower':
                        slower_sections.append({
                            'start_idx': section_start,
                            'end_idx': i - 1,
                            'avg_diff': np.mean(speed_diff[section_start:i])
                        })
                    current_section = None
            
            # Handle the last section if still open
            if current_section == 'faster':
                faster_sections.append({
                    'start_idx': section_start,
                    'end_idx': len(speed_diff) - 1,
                    'avg_diff': np.mean(speed_diff[section_start:])
                })
            elif current_section == 'slower':
                slower_sections.append({
                    'start_idx': section_start,
                    'end_idx': len(speed_diff) - 1,
                    'avg_diff': np.mean(speed_diff[section_start:])
                })
        
        return {
            'ref_lap_time': reference_lap.get('lap_time', 0),
            'comp_lap_time': comparison_lap.get('lap_time', 0),
            'time_diff': comparison_lap.get('lap_time', 0) - reference_lap.get('lap_time', 0),
            'avg_speed_diff': np.mean(speed_diff) if len(speed_diff) > 0 else 0,
            'faster_sections': faster_sections,
            'slower_sections': slower_sections,
        }
    
    def _resample_array(self, arr, target_length):
        """Resample a numpy array to a target length.
        
        Args:
            arr: The input array
            target_length: The desired length
            
        Returns:
            Resampled array
        """
        if len(arr) == 0 or target_length == 0:
            return np.array([])
            
        # Simple linear interpolation
        indices = np.linspace(0, len(arr) - 1, target_length)
        return np.interp(indices, np.arange(len(arr)), arr)
    
    def generate_super_lap(self, track_id, car_id):
        """Generate a SUPER LAP from the best segments of multiple drivers.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            
        Returns:
            Dictionary with SUPER LAP data
        """
        if not self.data_manager:
            logger.error("Cannot generate SUPER LAP: no data manager provided")
            return None
        
        logger.info(f"Generating SUPER LAP for track_id={track_id}, car_id={car_id}")
        
        # Get best sectors
        best_sectors = self.data_manager.get_best_sectors(track_id, car_id)
        
        if not best_sectors:
            logger.warning("No sector data available to generate SUPER LAP")
            return None
        
        # Calculate theoretical best lap time
        theoretical_time = sum(sector[1] for sector in best_sectors)
        
        # Get the lap IDs for the best sectors
        lap_ids = []
        driver_ids = []
        
        for sector in best_sectors:
            sector_num, sector_time, driver_id = sector
            driver_ids.append(driver_id)
            
            # In a real implementation, we would have a way to get the lap_id from the sector
            # For now, we'll use a placeholder
            lap_id = None  # This would be fetched from the database
            lap_ids.append(lap_id)
        
        # For now, we'll create a simulated SUPER LAP
        super_lap = {
            'track_id': track_id,
            'car_id': car_id,
            'lap_time': theoretical_time,
            'sectors': [
                {
                    'sector_number': sector[0],
                    'sector_time': sector[1],
                    'driver_id': sector[2]
                }
                for sector in best_sectors
            ],
            'created_at': time.time()
        }
        
        # Save the SUPER LAP
        if self.data_manager:
            super_lap_id = self.data_manager.save_super_lap(
                track_id, car_id, theoretical_time, super_lap
            )
            super_lap['id'] = super_lap_id
        
        return super_lap
    
    def get_improvement_suggestions(self, driver_id, track_id, car_id):
        """Get personalized improvement suggestions for a driver.
        
        Args:
            driver_id: The driver ID
            track_id: The track ID
            car_id: The car ID
            
        Returns:
            List of improvement suggestions
        """
        logger.info(f"Generating improvement suggestions for driver_id={driver_id}, track_id={track_id}, car_id={car_id}")
        
        if not self.data_manager:
            return []
        
        # Get the driver's best lap
        driver_best = self.data_manager.get_best_lap(track_id, car_id, driver_id)
        
        # Get the overall best lap
        overall_best = self.data_manager.get_best_lap(track_id, car_id)
        
        # Get the SUPER LAP
        super_lap = self.data_manager.get_super_lap(track_id, car_id)
        
        suggestions = []
        
        # If the driver hasn't set a lap time yet
        if not driver_best:
            suggestions.append({
                'type': 'general',
                'priority': 'high',
                'description': 'No lap data available yet. Focus on completing clean laps to establish a baseline.',
                'confidence': 0.9
            })
            return suggestions
        
        # If there's an overall best lap that's better than the driver's best
        if overall_best and overall_best[0] != driver_best[0] and overall_best[1] < driver_best[1]:
            time_delta = driver_best[1] - overall_best[1]
            
            suggestions.append({
                'type': 'lap_time',
                'priority': 'medium',
                'description': f'Your best lap is {time_delta:.2f} seconds slower than the track record. Focus on consistency and smooth inputs.',
                'confidence': 0.8
            })
        
        # If there's a SUPER LAP
        if super_lap:
            super_lap_id, super_lap_time, super_lap_data = super_lap
            
            if super_lap_time < driver_best[1]:
                time_delta = driver_best[1] - super_lap_time
                
                suggestions.append({
                    'type': 'super_lap',
                    'priority': 'high',
                    'description': f'The theoretical best lap is {time_delta:.2f} seconds faster than your best. Study the SUPER LAP to identify improvement areas.',
                    'confidence': 0.9
                })
                
                # Add specific sector suggestions
                for sector in super_lap_data.get('sectors', []):
                    suggestions.append({
                        'type': 'sector',
                        'sector': sector['sector_number'],
                        'priority': 'medium',
                        'description': f'In sector {sector["sector_number"]}, the best time is {sector["sector_time"]:.2f} seconds.',
                        'confidence': 0.7
                    })
        
        # Add some general driving technique suggestions
        suggestions.append({
            'type': 'technique',
            'priority': 'low',
            'description': 'Focus on smooth Throttle application when exiting corners to maximize acceleration.',
            'confidence': 0.6
        })
        
        suggestions.append({
            'type': 'technique',
            'priority': 'low',
            'description': 'Practice trail braking to carry more speed into corners while maintaining stability.',
            'confidence': 0.6
        })
        
        return suggestions 