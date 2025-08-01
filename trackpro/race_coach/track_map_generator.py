import logging
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class TrackMapGenerator:
    """Task 2.1 - Track Map Generator
    
    Uses position data from telemetry to generate full track map.
    Identifies lap start/end automatically and stores distance-based position reference.
    """
    
    def __init__(self):
        """Initialize the track map generator."""
        self.track_positions = []  # List of normalized track positions (0.0 to 1.0)
        self.telemetry_points = []  # Associated telemetry data
        self.track_length_meters = None  # Estimated track length in meters
        self.lap_boundaries = []  # List of indices where laps start/end
        self.is_track_mapped = False
        
        logger.info("Track Map Generator initialized")
    
    def add_telemetry_data(self, telemetry_points: List[Dict[str, Any]]) -> None:
        """Add telemetry data for track mapping.
        
        Args:
            telemetry_points: List of telemetry point dictionaries
        """
        valid_points = 0
        
        for point in telemetry_points:
            # Extract track position (required)
            track_pos = point.get('track_position')
            if track_pos is None:
                continue
            
            # Store telemetry point with additional data for position calculation
            telemetry_point = {
                'track_position': track_pos,
                'speed': point.get('speed', 0),
                'steering': point.get('steering', 0),
                'timestamp': point.get('timestamp', 0),
                # Map velocity fields from iRacing format to internal format
                'velocity_x': point.get('VelocityX', point.get('velocity_x', 0)),  # Real X velocity
                'velocity_y': point.get('VelocityY', point.get('velocity_y', 0)),  # Real Y velocity
                'yaw_rate': point.get('YawRate', point.get('yaw_rate', 0))
            }
            
            self.track_positions.append(track_pos)
            self.telemetry_points.append(telemetry_point)
            valid_points += 1
        
        logger.info(f"Added {valid_points}/{len(telemetry_points)} valid telemetry points for track mapping")
    
    def generate_track_map(self) -> bool:
        """Generate full track map from collected telemetry data.
        
        Returns:
            bool: True if track map was successfully generated
        """
        if len(self.track_positions) < 100:
            logger.warning(f"Insufficient data points for track mapping: {len(self.track_positions)}")
            return False
        
        # Identify lap start/end boundaries automatically
        self._identify_lap_boundaries()
        
        # Estimate track length if speed data is available
        self._estimate_track_length()
        
        # Generate distance-based position reference
        self._generate_distance_reference()
        
        self.is_track_mapped = True
        logger.info(f"Track map generated successfully with {len(self.track_positions)} points")
        logger.info(f"Detected {len(self.lap_boundaries)} lap boundaries")
        
        if self.track_length_meters:
            logger.info(f"Estimated track length: {self.track_length_meters:.1f} meters")
        
        return True
    
    def _identify_lap_boundaries(self) -> None:
        """Identify lap start/end automatically using position data."""
        self.lap_boundaries = []
        
        if len(self.track_positions) < 10:
            return
        
        # Method 1: Find large backward jumps in track position (1.0 -> 0.0)
        for i in range(1, len(self.track_positions)):
            prev_pos = self.track_positions[i-1]
            curr_pos = self.track_positions[i]
            
            # Detect crossing from high position back to low position
            if prev_pos > 0.8 and curr_pos < 0.2:
                self.lap_boundaries.append(i)
                logger.debug(f"Lap boundary detected at index {i}: {prev_pos:.3f} -> {curr_pos:.3f}")
        
        # Add start and end boundaries if not already present
        if not self.lap_boundaries or self.lap_boundaries[0] != 0:
            self.lap_boundaries.insert(0, 0)
        
        if not self.lap_boundaries or self.lap_boundaries[-1] != len(self.track_positions) - 1:
            self.lap_boundaries.append(len(self.track_positions) - 1)
        
        logger.info(f"Identified {len(self.lap_boundaries) - 1} complete laps")
    
    def _estimate_track_length(self) -> None:
        """Estimate track length in meters using speed and position data."""
        if not self.telemetry_points:
            return
        
        # Try to use speed data to estimate track length for the most complete lap
        best_lap_length = None
        best_lap_confidence = 0
        
        for i in range(len(self.lap_boundaries) - 1):
            start_idx = self.lap_boundaries[i]
            end_idx = self.lap_boundaries[i + 1]
            
            if end_idx - start_idx < 50:  # Skip very short segments
                continue
            
            lap_points = self.telemetry_points[start_idx:end_idx]
            
            # Calculate distance using speed integration
            total_distance = 0
            valid_segments = 0
            
            for j in range(1, len(lap_points)):
                speed_prev = lap_points[j-1].get('speed', 0)
                speed_curr = lap_points[j].get('speed', 0)
                
                if speed_prev > 0 and speed_curr > 0:
                    # Assume 60Hz data collection
                    time_delta = 1.0 / 60.0  # seconds
                    
                    # Convert speed (likely in m/s or km/h) to distance
                    avg_speed = (speed_prev + speed_curr) / 2
                    
                    # Handle different speed units (detect by magnitude)
                    if avg_speed > 500:  # Likely km/h
                        avg_speed_ms = avg_speed / 3.6  # Convert km/h to m/s
                    else:  # Likely already m/s
                        avg_speed_ms = avg_speed
                    
                    distance_segment = avg_speed_ms * time_delta
                    total_distance += distance_segment
                    valid_segments += 1
            
            # Calculate confidence based on data completeness
            confidence = valid_segments / max(1, len(lap_points) - 1)
            
            if confidence > best_lap_confidence and total_distance > 0:
                best_lap_confidence = confidence
                best_lap_length = total_distance
        
        if best_lap_length and best_lap_confidence > 0.5:
            self.track_length_meters = best_lap_length
            logger.info(f"Estimated track length: {self.track_length_meters:.1f}m (confidence: {best_lap_confidence:.2f})")
        else:
            # Fallback: use typical track length estimates
            self.track_length_meters = 3000  # Default 3km track
            logger.warning(f"Could not reliably estimate track length, using default: {self.track_length_meters}m")
    
    def _generate_distance_reference(self) -> None:
        """Generate distance-based position reference for the track."""
        if not self.track_length_meters:
            return
        
        # Convert normalized positions to actual distances
        self.distance_reference = []
        
        for pos in self.track_positions:
            distance_meters = pos * self.track_length_meters
            self.distance_reference.append(distance_meters)
        
        logger.info(f"Generated distance reference with {len(self.distance_reference)} points")
    
    def get_track_info(self) -> Dict[str, Any]:
        """Get track information summary.
        
        Returns:
            Dictionary containing track map information
        """
        return {
            'is_mapped': self.is_track_mapped,
            'total_points': len(self.track_positions),
            'track_length_meters': self.track_length_meters,
            'num_laps': len(self.lap_boundaries) - 1 if len(self.lap_boundaries) > 1 else 0,
            'lap_boundaries': self.lap_boundaries.copy(),
            'position_range': {
                'min': min(self.track_positions) if self.track_positions else None,
                'max': max(self.track_positions) if self.track_positions else None
            }
        }
    
    def plot_track_map(self, save_path: Optional[str] = None) -> bool:
        """Plot the track map visually using REAL position data.
        
        Args:
            save_path: Optional path to save the plot image
            
        Returns:
            bool: True if plot was created successfully
        """
        if not self.is_track_mapped or len(self.track_positions) < 10:
            logger.warning("Cannot plot track map: Track not mapped or insufficient data")
            return False
        
        try:
            plt.figure(figsize=(15, 10))
            
            # Plot 1: Track position vs time (existing)
            plt.subplot(2, 2, 1)
            plt.plot(range(len(self.track_positions)), self.track_positions, 'b-', alpha=0.7, linewidth=1)
            plt.title('Track Position vs. Time')
            plt.xlabel('Telemetry Point Index')
            plt.ylabel('Normalized Track Position (0.0 - 1.0)')
            plt.grid(True, alpha=0.3)
            
            # Mark lap boundaries
            for boundary in self.lap_boundaries:
                if 0 <= boundary < len(self.track_positions):
                    plt.axvline(x=boundary, color='red', linestyle='--', alpha=0.7, label='Lap Boundary')
            
            # Remove duplicate labels
            handles, labels = plt.gca().get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            plt.legend(by_label.values(), by_label.keys())
            
            # Plot 2: REAL Track Shape from Velocity Integration
            plt.subplot(2, 2, 2)
            
            if len(self.lap_boundaries) > 1 and len(self.telemetry_points) > 0:
                # Use the first complete lap for track shape
                start_idx = self.lap_boundaries[0]
                end_idx = self.lap_boundaries[1]
                
                lap_telemetry = self.telemetry_points[start_idx:end_idx]
                
                # Calculate REAL track coordinates by integrating velocity
                x_coords, y_coords = self._calculate_real_track_coordinates(lap_telemetry)
                
                if len(x_coords) > 0 and len(y_coords) > 0:
                    plt.plot(x_coords, y_coords, 'g-', linewidth=3, label='REAL Track Shape')
                    plt.scatter(x_coords[0], y_coords[0], color='green', s=150, marker='o', 
                              label='Start/Finish', zorder=5)
                    
                    # Mark corners if available
                    if hasattr(self, '_corner_positions'):
                        for corner_pos in self._corner_positions:
                            # Find closest point in lap
                            closest_idx = min(range(len(lap_telemetry)), 
                                             key=lambda i: abs(lap_telemetry[i]['track_position'] - corner_pos))
                            if closest_idx < len(x_coords):
                                plt.scatter(x_coords[closest_idx], y_coords[closest_idx], 
                                          color='red', s=100, marker='s', alpha=0.8)
                    
                    plt.title('REAL Track Shape (from Velocity Integration)')
                    plt.xlabel('X Position (meters)')
                    plt.ylabel('Y Position (meters)')
                    plt.axis('equal')
                    plt.grid(True, alpha=0.3)
                    plt.legend()
                else:
                    plt.text(0.5, 0.5, 'Unable to calculate\nreal track coordinates\n(no velocity data)', 
                            horizontalalignment='center', verticalalignment='center',
                            transform=plt.gca().transAxes, fontsize=12)
                    plt.title('Real Track Shape - No Velocity Data')
            else:
                plt.text(0.5, 0.5, 'Insufficient lap data\nfor track shape visualization', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=plt.gca().transAxes, fontsize=12)
                plt.title('Track Shape - Insufficient Data')
            
            # Plot 3: Speed vs Position
            plt.subplot(2, 2, 3)
            if self.telemetry_points:
                speeds = [p.get('speed', 0) for p in self.telemetry_points]
                positions = [p.get('track_position', 0) for p in self.telemetry_points]
                plt.plot(positions, speeds, 'r-', alpha=0.6, linewidth=1)
                plt.title('Speed vs Track Position')
                plt.xlabel('Track Position (0.0 - 1.0)')
                plt.ylabel('Speed (m/s)')
                plt.grid(True, alpha=0.3)
            
            # Plot 4: Steering vs Position  
            plt.subplot(2, 2, 4)
            if self.telemetry_points:
                steering = [p.get('steering', 0) for p in self.telemetry_points]
                positions = [p.get('track_position', 0) for p in self.telemetry_points]
                plt.plot(positions, steering, 'purple', alpha=0.6, linewidth=1)
                plt.title('Steering vs Track Position')
                plt.xlabel('Track Position (0.0 - 1.0)')
                plt.ylabel('Steering Angle (rad)')
                plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"Track map plot saved to: {save_path}")
            else:
                plt.show()
            
            plt.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating track map plot: {e}")
            return False
    
    def _calculate_real_track_coordinates(self, lap_telemetry: List[Dict[str, Any]]) -> Tuple[List[float], List[float]]:
        """Calculate real track coordinates by integrating velocity vectors.
        
        Args:
            lap_telemetry: List of telemetry points for one lap
            
        Returns:
            Tuple of (x_coordinates, y_coordinates) lists
        """
        x_coords = []
        y_coords = []
        
        if not lap_telemetry:
            return x_coords, y_coords
        
        # Check if we have velocity data (check both field name formats)
        has_velocity = any(('velocity_x' in point and 'velocity_y' in point) or 
                          ('VelocityX' in point and 'VelocityY' in point)
                          for point in lap_telemetry)
        
        if not has_velocity:
            logger.warning("No velocity data available for real track shape calculation")
            return x_coords, y_coords
        
        # Initialize position
        x, y = 0.0, 0.0
        x_coords.append(x)
        y_coords.append(y)
        
        # Integrate velocity to get position
        for i in range(1, len(lap_telemetry)):
            current = lap_telemetry[i]
            previous = lap_telemetry[i-1]
            
            # Get velocity components (try both field name formats)
            vx = current.get('velocity_x', current.get('VelocityX', 0))
            vy = current.get('velocity_y', current.get('VelocityY', 0))
            
            # Calculate time delta (assume 60Hz if no timestamp)
            dt = 1/60.0  # Default 60Hz
            if 'timestamp' in current and 'timestamp' in previous:
                dt = current['timestamp'] - previous['timestamp']
                if dt <= 0 or dt > 1.0:  # Sanity check
                    dt = 1/60.0
            
            # Integrate position
            x += vx * dt
            y += vy * dt
            
            x_coords.append(x)
            y_coords.append(y)
        
        logger.info(f"Calculated real track coordinates: {len(x_coords)} points, "
                   f"track size: {max(x_coords)-min(x_coords):.1f}m x {max(y_coords)-min(y_coords):.1f}m")
        
        return x_coords, y_coords
    
    def save_track_map(self, file_path: str) -> bool:
        """Save track map data to file.
        
        Args:
            file_path: Path to save the track map data
            
        Returns:
            bool: True if saved successfully
        """
        if not self.is_track_mapped:
            logger.warning("Cannot save track map: Track not mapped")
            return False
        
        try:
            track_data = {
                'track_info': self.get_track_info(),
                'track_positions': self.track_positions,
                'distance_reference': getattr(self, 'distance_reference', []),
                'metadata': {
                    'generator_version': '1.0',
                    'total_telemetry_points': len(self.telemetry_points)
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(track_data, f, indent=2)
            
            logger.info(f"Track map saved to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving track map: {e}")
            return False
    
    def load_track_map(self, file_path: str) -> bool:
        """Load track map data from file.
        
        Args:
            file_path: Path to load the track map data from
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(file_path, 'r') as f:
                track_data = json.load(f)
            
            self.track_positions = track_data.get('track_positions', [])
            self.distance_reference = track_data.get('distance_reference', [])
            
            track_info = track_data.get('track_info', {})
            self.track_length_meters = track_info.get('track_length_meters')
            self.lap_boundaries = track_info.get('lap_boundaries', [])
            self.is_track_mapped = track_info.get('is_mapped', False)
            
            logger.info(f"Track map loaded from: {file_path}")
            logger.info(f"Loaded {len(self.track_positions)} track positions")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading track map: {e}")
            return False


def test_track_map_generator():
    """Test function for Task 2.1"""
    logger.info("🧪 Testing Track Map Generator...")
    
    # Create test telemetry data simulating a few laps
    test_telemetry = []
    
    # Simulate 3 laps of telemetry data at 60Hz (3 seconds per lap = 180 points per lap)
    for lap in range(3):
        for i in range(180):
            # Create smooth position progression from 0.0 to 1.0
            position = i / 180.0
            
            # Add some realistic speed data (50-100 m/s range)
            speed = 50 + 30 * np.sin(position * 2 * np.pi)  # Varying speed around track
            
            test_point = {
                'track_position': position,
                'speed': speed,
                'timestamp': (lap * 180 + i) / 60.0,  # 60Hz timestamps
                'throttle': 0.7 + 0.3 * np.sin(position * 4 * np.pi),  # Varying throttle
            }
            test_telemetry.append(test_point)
    
    # Test the track map generator
    generator = TrackMapGenerator()
    
    # Add telemetry data
    generator.add_telemetry_data(test_telemetry)
    
    # Generate track map
    success = generator.generate_track_map()
    
    if success:
        # Get track info
        track_info = generator.get_track_info()
        print(f"✅ Track Map Generated Successfully!")
        print(f"   - Total Points: {track_info['total_points']}")
        print(f"   - Track Length: {track_info['track_length_meters']:.1f} meters")
        print(f"   - Number of Laps: {track_info['num_laps']}")
        print(f"   - Position Range: {track_info['position_range']['min']:.3f} - {track_info['position_range']['max']:.3f}")
        
        # Test plotting (save to file to avoid display issues)
        plot_path = "test_track_map.png"
        plot_success = generator.plot_track_map(save_path=plot_path)
        
        if plot_success:
            print(f"✅ Track map plot saved to: {plot_path}")
        
        # Test saving and loading
        save_path = "test_track_map.json"
        save_success = generator.save_track_map(save_path)
        
        if save_success:
            print(f"✅ Track map data saved to: {save_path}")
            
            # Test loading
            new_generator = TrackMapGenerator()
            load_success = new_generator.load_track_map(save_path)
            
            if load_success:
                print(f"✅ Track map data loaded successfully")
            else:
                print(f"❌ Failed to load track map data")
        
        return True
    else:
        print(f"❌ Track Map Generation Failed")
        return False


if __name__ == "__main__":
    # Run test when script is executed directly
    test_track_map_generator()