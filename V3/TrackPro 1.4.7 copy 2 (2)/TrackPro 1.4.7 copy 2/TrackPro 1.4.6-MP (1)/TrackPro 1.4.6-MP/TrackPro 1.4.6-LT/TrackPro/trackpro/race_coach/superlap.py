import logging
import numpy as np
import json
import os
from pathlib import Path
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

class SuperLap:
    """Generates and manages SUPER LAP data."""
    
    def __init__(self, data_manager=None, model=None):
        """Initialize the SUPER LAP module.
        
        Args:
            data_manager: The data manager instance for accessing stored data
            model: The racing model instance for analyzing data
        """
        self.data_manager = data_manager
        self.model = model
        logger.info("SUPER LAP module initialized")
    
    def generate_super_lap(self, track_id, car_id):
        """Generate a SUPER LAP from the best segments of multiple drivers.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            
        Returns:
            Dictionary with SUPER LAP data, or None if generation failed
        """
        logger.info(f"Generating SUPER LAP for track {track_id}, car {car_id}")
        
        if not self.data_manager:
            logger.error("Cannot generate SUPER LAP: no data manager provided")
            return None
        
        if not self.model:
            logger.error("Cannot generate SUPER LAP: no model provided")
            return None
        
        # Use the model to generate a SUPER LAP
        super_lap = self.model.generate_super_lap(track_id, car_id)
        
        return super_lap
    
    def get_super_lap(self, track_id, car_id):
        """Get the latest SUPER LAP for a track/car combination.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            
        Returns:
            The SUPER LAP data, or None if not found
        """
        if not self.data_manager:
            logger.error("Cannot get SUPER LAP: no data manager provided")
            return None
        
        return self.data_manager.get_super_lap(track_id, car_id)
    
    def compare_with_super_lap(self, lap_telemetry, track_id, car_id):
        """Compare a lap's telemetry with the SUPER LAP.
        
        Args:
            lap_telemetry: The lap telemetry data to compare
            track_id: The track ID
            car_id: The car ID
            
        Returns:
            Dictionary with comparison results, or None if comparison failed
        """
        logger.info("Comparing lap with SUPER LAP")
        
        if not self.data_manager or not self.model:
            logger.error("Cannot compare with SUPER LAP: missing dependencies")
            return None
        
        # Get the SUPER LAP
        super_lap_data = self.data_manager.get_super_lap(track_id, car_id)
        
        if not super_lap_data:
            logger.warning("No SUPER LAP available for comparison")
            return None
        
        # For now, we'll just create a simplified comparison
        # In a real implementation, we would need to align the telemetry data and make a detailed comparison
        
        comparison = {
            'lap_time': lap_telemetry.get('lap_time', 0),
            'super_lap_time': super_lap_data[1],
            'time_diff': lap_telemetry.get('lap_time', 0) - super_lap_data[1],
            'sectors': []
        }
        
        # Compare sectors if available
        if 'sectors' in super_lap_data[2]:
            for sector in super_lap_data[2]['sectors']:
                sector_num = sector['sector_number']
                sector_time = sector['sector_time']
                driver_id = sector['driver_id']
                
                # Get the driver's name
                driver_name = f"Driver {driver_id}"  # Placeholder
                
                # Get the lap's sector time (simulated for now)
                lap_sector_time = sector_time * (1 + np.random.uniform(0, 0.1))
                
                comparison['sectors'].append({
                    'sector': sector_num,
                    'lap_time': lap_sector_time,
                    'super_lap_time': sector_time,
                    'time_diff': lap_sector_time - sector_time,
                    'super_lap_driver': driver_name
                })
        
        return comparison
    
    def create_super_lap_chart(self, track_id, car_id, width=8, height=6):
        """Create a chart visualizing the SUPER LAP.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            A matplotlib Figure object, or None if chart creation failed
        """
        if not self.data_manager:
            logger.error("Cannot create SUPER LAP chart: no data manager provided")
            return None
        
        # Get the SUPER LAP
        super_lap_data = self.data_manager.get_super_lap(track_id, car_id)
        
        if not super_lap_data:
            logger.warning("No SUPER LAP available for chart")
            return None
        
        # Create a figure
        fig = Figure(figsize=(width, height), dpi=100)
        
        # Add a subplot for sector times
        ax1 = fig.add_subplot(211)
        
        # Extract sector data
        sectors = super_lap_data[2].get('sectors', [])
        sector_nums = [s['sector_number'] for s in sectors]
        sector_times = [s['sector_time'] for s in sectors]
        driver_ids = [s['driver_id'] for s in sectors]
        
        # Plot sector times
        bars = ax1.bar(sector_nums, sector_times, color='g')
        
        # Add driver IDs as text on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width()/2.,
                height + 0.1,
                f"Driver {driver_ids[i]}",
                ha='center', va='bottom',
                color='white', fontsize=8
            )
        
        # Configure the chart
        ax1.set_title('SUPER LAP Sector Times')
        ax1.set_xlabel('Sector')
        ax1.set_ylabel('Time (seconds)')
        ax1.set_xticks(sector_nums)
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # Add a subplot for the theoretical vs actual best lap
        ax2 = fig.add_subplot(212)
        
        # Simulated data for the chart
        # In a real implementation, we would retrieve actual data
        theoretical_time = super_lap_data[1]
        
        # In a real implementation, these would be retrieved from the database
        best_overall_time = theoretical_time * 1.01  # Simulated: 1% slower than theoretical
        best_driver_times = [theoretical_time * (1 + np.random.uniform(0.01, 0.05)) for _ in range(3)]
        driver_names = [f"Driver {i+1}" for i in range(3)]
        
        # Plot comparison
        bars = ax2.barh([0] + list(range(1, len(best_driver_times) + 1)), 
                        [theoretical_time] + best_driver_times,
                        color=['g'] + ['b'] * len(best_driver_times))
        
        # Add lap times as text on bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            label = f"{width:.2f}s"
            ax2.text(
                width - 1,
                bar.get_y() + bar.get_height()/2.,
                label,
                ha='right', va='center',
                color='white', fontsize=8
            )
        
        # Configure the chart
        ax2.set_title('SUPER LAP vs Best Driver Laps')
        ax2.set_xlabel('Lap Time (seconds)')
        ax2.set_yticks([0] + list(range(1, len(best_driver_times) + 1)))
        ax2.set_yticklabels(['SUPER LAP'] + driver_names)
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # Style the charts for dark mode
        for ax in [ax1, ax2]:
            ax.set_facecolor('#2a2a2a')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
        
        fig.patch.set_facecolor('#353535')
        fig.tight_layout()
        
        return fig
    
    def export_super_lap(self, track_id, car_id, filepath):
        """Export a SUPER LAP to a file.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            filepath: The file path to export to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.data_manager:
            logger.error("Cannot export SUPER LAP: no data manager provided")
            return False
        
        # Get the SUPER LAP
        super_lap_data = self.data_manager.get_super_lap(track_id, car_id)
        
        if not super_lap_data:
            logger.warning("No SUPER LAP available for export")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Export data
            with open(filepath, 'w') as f:
                json.dump(super_lap_data[2], f, indent=2)
            
            logger.info(f"Exported SUPER LAP to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting SUPER LAP: {e}")
            return False
    
    def import_super_lap(self, track_id, car_id, filepath):
        """Import a SUPER LAP from a file.
        
        Args:
            track_id: The track ID
            car_id: The car ID
            filepath: The file path to import from
            
        Returns:
            The imported SUPER LAP data if successful, None otherwise
        """
        if not self.data_manager:
            logger.error("Cannot import SUPER LAP: no data manager provided")
            return None
        
        try:
            # Load data from file
            with open(filepath, 'r') as f:
                super_lap_data = json.load(f)
            
            # Validate data format
            if not isinstance(super_lap_data, dict) or 'sectors' not in super_lap_data:
                logger.error("Invalid SUPER LAP data format")
                return None
            
            # Calculate theoretical time
            theoretical_time = sum(sector['sector_time'] for sector in super_lap_data.get('sectors', []))
            
            # Save to database
            super_lap_id = self.data_manager.save_super_lap(
                track_id, car_id, theoretical_time, super_lap_data
            )
            
            logger.info(f"Imported SUPER LAP from {filepath}")
            return (super_lap_id, theoretical_time, super_lap_data)
        except Exception as e:
            logger.error(f"Error importing SUPER LAP: {e}")
            return None 