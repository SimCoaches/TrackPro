import logging
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple, Optional
import json
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Corner:
    """Represents a corner segment on the track."""
    corner_number: int
    name: str
    entry_position: float  # Normalized track position (0.0-1.0)
    apex_position: float
    exit_position: float
    entry_distance: float  # Distance in meters
    apex_distance: float
    exit_distance: float
    min_speed: float  # Minimum speed through corner
    max_steering_angle: float  # Maximum steering angle in corner
    corner_type: str  # 'left', 'right', 'chicane'
    severity: str  # 'slow', 'medium', 'fast'

class CornerSegmentation:
    """Task 2.2 - Corner Segmentation
    
    Identifies corners automatically using speed drops and steering angle increases.
    Labels corners (Turn 1, Turn 2, etc.) with entry/exit distance markers.
    """
    
    def __init__(self, track_length_meters: Optional[float] = None):
        """Initialize the corner segmentation system.
        
        Args:
            track_length_meters: Length of track in meters (optional)
        """
        self.track_length_meters = track_length_meters or 3000  # Default 3km
        self.corners = []  # List of detected corners
        self.telemetry_data = []  # Stored telemetry for analysis
        self.is_analyzed = False
        
        # Analysis parameters
        self.speed_threshold_factor = 0.85  # Speed must drop to 85% of local max
        self.steering_threshold = 0.1  # Minimum steering angle for corner detection
        self.min_corner_duration = 30  # Minimum points for a valid corner
        self.smoothing_window = 15  # Points to smooth data over
        
        logger.info("Corner Segmentation system initialized")
    
    def add_telemetry_data(self, telemetry_points: List[Dict[str, Any]]) -> None:
        """Add telemetry data for corner analysis.
        
        Args:
            telemetry_points: List of telemetry dictionaries
        """
        valid_points = 0
        
        for point in telemetry_points:
            # Check for required fields
            if (point.get('track_position') is not None and 
                point.get('speed') is not None and 
                point.get('steering') is not None):
                
                self.telemetry_data.append(point)
                valid_points += 1
        
        logger.info(f"Added {valid_points}/{len(telemetry_points)} valid telemetry points for corner analysis")
    
    def analyze_corners(self) -> bool:
        """Analyze telemetry data to identify corners.
        
        Returns:
            bool: True if corner analysis was successful
        """
        if len(self.telemetry_data) < 100:
            logger.warning(f"Insufficient data for corner analysis: {len(self.telemetry_data)} points")
            return False
        
        # Extract data arrays for analysis
        positions = [p.get('track_position', 0) for p in self.telemetry_data]
        speeds = [p.get('speed', 0) for p in self.telemetry_data]
        steering = [abs(p.get('steering', 0)) for p in self.telemetry_data]  # Use absolute steering
        
        # Smooth the data to reduce noise
        speeds_smooth = self._smooth_data(speeds)
        steering_smooth = self._smooth_data(steering)
        
        # Find potential corner regions
        corner_regions = self._find_corner_regions(positions, speeds_smooth, steering_smooth)
        
        # Process each corner region
        self.corners = []
        for i, region in enumerate(corner_regions):
            corner = self._analyze_corner_region(region, positions, speeds_smooth, steering_smooth, i + 1)
            if corner:
                self.corners.append(corner)
        
        self.is_analyzed = True
        logger.info(f"Corner analysis complete: {len(self.corners)} corners detected")
        
        return True
    
    def _smooth_data(self, data: List[float]) -> List[float]:
        """Apply smoothing to data array.
        
        Args:
            data: Input data array
            
        Returns:
            Smoothed data array
        """
        if len(data) < self.smoothing_window:
            return data
        
        smoothed = []
        half_window = self.smoothing_window // 2
        
        for i in range(len(data)):
            start_idx = max(0, i - half_window)
            end_idx = min(len(data), i + half_window + 1)
            
            window_data = data[start_idx:end_idx]
            smoothed_value = sum(window_data) / len(window_data)
            smoothed.append(smoothed_value)
        
        return smoothed
    
    def _find_corner_regions(self, positions: List[float], speeds: List[float], 
                           steering: List[float]) -> List[Tuple[int, int]]:
        """Find potential corner regions using speed and steering analysis.
        
        Args:
            positions: Track position data
            speeds: Speed data (smoothed)
            steering: Steering data (smoothed, absolute values)
            
        Returns:
            List of (start_index, end_index) tuples for corner regions
        """
        corner_regions = []
        
        # Calculate local speed maxima for reference
        local_speed_max = self._calculate_local_maxima(speeds, window=60)
        
        in_corner = False
        corner_start = 0
        
        for i in range(len(speeds)):
            current_speed = speeds[i]
            current_steering = steering[i]
            local_max_speed = local_speed_max[i]
            
            # Corner entry criteria: speed drops AND steering increases
            speed_drop = current_speed < (local_max_speed * self.speed_threshold_factor)
            steering_active = current_steering > self.steering_threshold
            
            if not in_corner and speed_drop and steering_active:
                # Potential corner entry
                corner_start = i
                in_corner = True
                
            elif in_corner and (not speed_drop or not steering_active):
                # Potential corner exit
                corner_end = i
                
                # Validate corner duration
                if corner_end - corner_start >= self.min_corner_duration:
                    corner_regions.append((corner_start, corner_end))
                
                in_corner = False
        
        # Handle case where corner extends to end of data
        if in_corner and len(speeds) - corner_start >= self.min_corner_duration:
            corner_regions.append((corner_start, len(speeds) - 1))
        
        logger.info(f"Found {len(corner_regions)} potential corner regions")
        return corner_regions
    
    def _calculate_local_maxima(self, data: List[float], window: int = 60) -> List[float]:
        """Calculate local maxima for speed reference.
        
        Args:
            data: Input data array
            window: Window size for local maximum calculation
            
        Returns:
            Array of local maximum values
        """
        local_maxima = []
        half_window = window // 2
        
        for i in range(len(data)):
            start_idx = max(0, i - half_window)
            end_idx = min(len(data), i + half_window + 1)
            
            window_data = data[start_idx:end_idx]
            local_max = max(window_data) if window_data else data[i]
            local_maxima.append(local_max)
        
        return local_maxima
    
    def _analyze_corner_region(self, region: Tuple[int, int], positions: List[float], 
                             speeds: List[float], steering: List[float], 
                             corner_number: int) -> Optional[Corner]:
        """Analyze a corner region to extract corner properties.
        
        Args:
            region: (start_index, end_index) tuple
            positions: Track position data
            speeds: Speed data
            steering: Steering data (absolute values)
            corner_number: Sequential corner number
            
        Returns:
            Corner object or None if analysis fails
        """
        start_idx, end_idx = region
        
        # Extract corner data
        corner_positions = positions[start_idx:end_idx + 1]
        corner_speeds = speeds[start_idx:end_idx + 1]
        corner_steering = steering[start_idx:end_idx + 1]
        
        if not corner_positions or not corner_speeds or not corner_steering:
            return None
        
        # Find apex (minimum speed point)
        min_speed_idx = corner_speeds.index(min(corner_speeds))
        apex_idx = start_idx + min_speed_idx
        
        # Calculate corner properties
        entry_position = positions[start_idx]
        apex_position = positions[apex_idx]
        exit_position = positions[end_idx]
        
        entry_distance = entry_position * self.track_length_meters
        apex_distance = apex_position * self.track_length_meters
        exit_distance = exit_position * self.track_length_meters
        
        min_speed = min(corner_speeds)
        max_steering_angle = max(corner_steering)
        
        # Determine corner type (left/right based on original steering data)
        # Need to look at original steering data (not absolute) for direction
        original_steering = []
        for i in range(start_idx, end_idx + 1):
            if i < len(self.telemetry_data):
                original_steering.append(self.telemetry_data[i].get('steering', 0))
        
        if original_steering:
            avg_steering = sum(original_steering) / len(original_steering)
            corner_type = 'left' if avg_steering > 0 else 'right'
        else:
            corner_type = 'unknown'
        
        # Determine corner severity based on minimum speed
        if min_speed < 30:
            severity = 'slow'
        elif min_speed < 60:
            severity = 'medium'
        else:
            severity = 'fast'
        
        corner = Corner(
            corner_number=corner_number,
            name=f"Turn {corner_number}",
            entry_position=entry_position,
            apex_position=apex_position,
            exit_position=exit_position,
            entry_distance=entry_distance,
            apex_distance=apex_distance,
            exit_distance=exit_distance,
            min_speed=min_speed,
            max_steering_angle=max_steering_angle,
            corner_type=corner_type,
            severity=severity
        )
        
        logger.debug(f"Analyzed {corner.name}: {corner.corner_type} {corner.severity} corner, "
                    f"apex at {corner.apex_distance:.1f}m, min speed {corner.min_speed:.1f}")
        
        return corner
    
    def get_corners_list(self) -> List[Dict[str, Any]]:
        """Get list of detected corners with entry/exit distance markers.
        
        Returns:
            List of corner dictionaries
        """
        if not self.is_analyzed:
            logger.warning("Corner analysis not performed yet")
            return []
        
        corners_list = []
        
        for corner in self.corners:
            corner_dict = {
                'corner_number': corner.corner_number,
                'name': corner.name,
                'type': corner.corner_type,
                'severity': corner.severity,
                'entry_distance_m': corner.entry_distance,
                'apex_distance_m': corner.apex_distance,
                'exit_distance_m': corner.exit_distance,
                'entry_position': corner.entry_position,
                'apex_position': corner.apex_position,
                'exit_position': corner.exit_position,
                'min_speed': corner.min_speed,
                'max_steering_angle': corner.max_steering_angle,
                'length_m': corner.exit_distance - corner.entry_distance
            }
            corners_list.append(corner_dict)
        
        return corners_list
    
    def plot_corner_analysis(self, save_path: Optional[str] = None) -> bool:
        """Plot corner analysis visualization.
        
        Args:
            save_path: Optional path to save the plot
            
        Returns:
            bool: True if plot was created successfully
        """
        if not self.is_analyzed or not self.telemetry_data:
            logger.warning("Cannot plot corner analysis: No data or analysis not performed")
            return False
        
        try:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))
            
            # Extract data for plotting
            positions = [p.get('track_position', 0) for p in self.telemetry_data]
            speeds = [p.get('speed', 0) for p in self.telemetry_data]
            steering = [p.get('steering', 0) for p in self.telemetry_data]
            distances = [p * self.track_length_meters for p in positions]
            
            # Plot 1: Speed vs Distance
            ax1.plot(distances, speeds, 'b-', linewidth=1, alpha=0.7, label='Speed')
            ax1.set_xlabel('Distance (m)')
            ax1.set_ylabel('Speed')
            ax1.set_title('Speed Profile with Corner Markers')
            ax1.grid(True, alpha=0.3)
            
            # Mark corners on speed plot
            for corner in self.corners:
                ax1.axvline(x=corner.entry_distance, color='red', linestyle='--', alpha=0.7)
                ax1.axvline(x=corner.apex_distance, color='orange', linestyle='-', alpha=0.7)
                ax1.axvline(x=corner.exit_distance, color='green', linestyle='--', alpha=0.7)
                
                # Add corner labels
                ax1.text(corner.apex_distance, max(speeds) * 0.9, corner.name, 
                        rotation=90, verticalalignment='bottom', fontsize=8)
            
            # Plot 2: Steering vs Distance
            ax2.plot(distances, steering, 'r-', linewidth=1, alpha=0.7, label='Steering Angle')
            ax2.set_xlabel('Distance (m)')
            ax2.set_ylabel('Steering Angle')
            ax2.set_title('Steering Profile with Corner Markers')
            ax2.grid(True, alpha=0.3)
            
            # Mark corners on steering plot
            for corner in self.corners:
                ax2.axvline(x=corner.entry_distance, color='red', linestyle='--', alpha=0.7)
                ax2.axvline(x=corner.apex_distance, color='orange', linestyle='-', alpha=0.7)
                ax2.axvline(x=corner.exit_distance, color='green', linestyle='--', alpha=0.7)
            
            # Plot 3: Corner Summary
            ax3.axis('off')
            corner_summary = "Detected Corners:\n\n"
            
            for corner in self.corners:
                corner_summary += (f"{corner.name}: {corner.corner_type.title()} {corner.severity} corner\n"
                                 f"  Entry: {corner.entry_distance:.0f}m, "
                                 f"Apex: {corner.apex_distance:.0f}m, "
                                 f"Exit: {corner.exit_distance:.0f}m\n"
                                 f"  Min Speed: {corner.min_speed:.1f}, "
                                 f"Max Steering: {corner.max_steering_angle:.3f}\n\n")
            
            ax3.text(0.05, 0.95, corner_summary, transform=ax3.transAxes, 
                    verticalalignment='top', fontfamily='monospace', fontsize=10)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"Corner analysis plot saved to: {save_path}")
            else:
                plt.show()
            
            plt.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating corner analysis plot: {e}")
            return False
    
    def save_corners_data(self, file_path: str) -> bool:
        """Save corner analysis data to file.
        
        Args:
            file_path: Path to save the corner data
            
        Returns:
            bool: True if saved successfully
        """
        if not self.is_analyzed:
            logger.warning("Cannot save corner data: Analysis not performed")
            return False
        
        try:
            corners_data = {
                'track_length_meters': self.track_length_meters,
                'analysis_parameters': {
                    'speed_threshold_factor': self.speed_threshold_factor,
                    'steering_threshold': self.steering_threshold,
                    'min_corner_duration': self.min_corner_duration,
                    'smoothing_window': self.smoothing_window
                },
                'corners': self.get_corners_list(),
                'summary': {
                    'total_corners': len(self.corners),
                    'left_corners': sum(1 for c in self.corners if c.corner_type == 'left'),
                    'right_corners': sum(1 for c in self.corners if c.corner_type == 'right'),
                    'slow_corners': sum(1 for c in self.corners if c.severity == 'slow'),
                    'medium_corners': sum(1 for c in self.corners if c.severity == 'medium'),
                    'fast_corners': sum(1 for c in self.corners if c.severity == 'fast')
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(corners_data, f, indent=2)
            
            logger.info(f"Corner analysis data saved to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving corner data: {e}")
            return False


def test_corner_segmentation():
    """Test function for Task 2.2 - Corner Segmentation"""
    logger.info("🧪 Testing Corner Segmentation...")
    
    # Create test telemetry data with realistic corner patterns
    test_telemetry = []
    track_length = 2000  # 2km track
    
    # Simulate telemetry data with 4 corners
    corner_positions = [0.2, 0.4, 0.6, 0.8]  # Corner positions around track
    corner_severities = [0.5, 0.7, 0.3, 0.6]  # Speed reduction factors
    
    for i in range(600):  # 10 seconds at 60Hz
        position = i / 600.0
        
        # Base speed
        speed = 80.0
        steering = 0.0
        
        # Apply corner effects
        for j, corner_pos in enumerate(corner_positions):
            # Distance to corner center
            corner_distance = min(abs(position - corner_pos), 
                                abs(position - corner_pos + 1.0),
                                abs(position - corner_pos - 1.0))
            
            if corner_distance < 0.05:  # Within corner influence
                # Reduce speed and add steering
                severity = corner_severities[j]
                influence = 1.0 - (corner_distance / 0.05)  # Stronger closer to center
                
                speed_reduction = severity * influence
                speed *= (1.0 - speed_reduction)
                
                # Add steering (alternate left/right)
                steering_direction = 1 if j % 2 == 0 else -1
                steering = steering_direction * 0.5 * influence
        
        test_point = {
            'track_position': position,
            'speed': speed,
            'steering': steering,
            'timestamp': i / 60.0,
            'throttle': 0.8 if speed > 60 else 0.4,
            'brake': 0.0 if speed > 60 else 0.3
        }
        test_telemetry.append(test_point)
    
    # Test the corner segmentation
    segmentation = CornerSegmentation(track_length_meters=track_length)
    
    # Add telemetry data
    segmentation.add_telemetry_data(test_telemetry)
    
    # Analyze corners
    success = segmentation.analyze_corners()
    
    if success:
        # Get corners list
        corners = segmentation.get_corners_list()
        
        print(f"✅ Corner Segmentation Successful!")
        print(f"   - Detected {len(corners)} corners")
        
        # Print corner details
        for corner in corners:
            print(f"   - {corner['name']}: {corner['type'].title()} {corner['severity']} corner")
            print(f"     Entry: {corner['entry_distance_m']:.0f}m, "
                  f"Apex: {corner['apex_distance_m']:.0f}m, "
                  f"Exit: {corner['exit_distance_m']:.0f}m")
            print(f"     Min Speed: {corner['min_speed']:.1f}, "
                  f"Length: {corner['length_m']:.0f}m")
        
        # Test plotting
        plot_path = "test_corner_analysis.png"
        plot_success = segmentation.plot_corner_analysis(save_path=plot_path)
        
        if plot_success:
            print(f"✅ Corner analysis plot saved to: {plot_path}")
        
        # Test saving
        save_path = "test_corners.json"
        save_success = segmentation.save_corners_data(save_path)
        
        if save_success:
            print(f"✅ Corner data saved to: {save_path}")
        
        return True
    else:
        print(f"❌ Corner Segmentation Failed")
        return False


if __name__ == "__main__":
    # Run test when script is executed directly
    test_corner_segmentation()