import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
# Prefer unified QtAgg backend (works with PyQt6); fallback to explicit Qt6 backend
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except Exception:  # pragma: no cover - fallback for older Matplotlib
    from matplotlib.backends.backend_qt6agg import FigureCanvasQTAgg as FigureCanvas
import os
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class LapAnalysis:
    """Provides analysis tools for lap data."""
    
    def __init__(self, data_manager=None):
        """Initialize the lap analysis module.
        
        Args:
            data_manager: The data manager instance for accessing stored data
        """
        self.data_manager = data_manager
        logger.info("Lap analysis module initialized")
    
    def analyze_lap_times(self, session_id):
        """Analyze lap times for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with lap time analysis
        """
        if not self.data_manager:
            logger.error("Cannot analyze lap times: no data manager provided")
            return None
        
        # In a real implementation, we would fetch lap times from the database
        # For now, we'll generate some sample data
        
        # Simulated lap times (in seconds) that improve over time with some variation
        lap_times = [95.0]
        for i in range(1, 10):
            improvement = np.random.uniform(0.1, 0.5) if np.random.random() > 0.3 else 0
            lap_times.append(max(85.0, lap_times[-1] - improvement))
        
        # Calculate statistics
        analysis = {
            'lap_times': lap_times,
            'lap_numbers': list(range(1, len(lap_times) + 1)),
            'best_lap': min(lap_times),
            'best_lap_number': lap_times.index(min(lap_times)) + 1,
            'avg_lap': np.mean(lap_times),
            'lap_time_improvement': lap_times[0] - lap_times[-1],
            'consistency': np.std(lap_times)
        }
        
        return analysis
    
    def compare_lap_telemetry(self, telemetry1, telemetry2):
        """Compare two lap telemetry datasets.
        
        Args:
            telemetry1: Telemetry data for the first lap
            telemetry2: Telemetry data for the second lap
            
        Returns:
            Dictionary with comparison results
        """
        # Extract and compare speed data
        speed1 = self._extract_data_series(telemetry1, 'speed')
        speed2 = self._extract_data_series(telemetry2, 'speed')
        
        # Normalize to the same length if needed
        if len(speed1) != len(speed2):
            # Use the shorter one as reference for normalization
            if len(speed1) < len(speed2):
                speed2 = self._normalize_data_length(speed2, len(speed1))
            else:
                speed1 = self._normalize_data_length(speed1, len(speed2))
        
        # Calculate differences
        speed_diff = np.array(speed2) - np.array(speed1)
        
        # Extract and compare throttle/brake data
        throttle1 = self._extract_data_series(telemetry1, 'Throttle')
        throttle2 = self._extract_data_series(telemetry2, 'Throttle')
        brake1 = self._extract_data_series(telemetry1, 'Brake')
        brake2 = self._extract_data_series(telemetry2, 'Brake')
        
        # Normalize to the same length if needed
        if len(throttle1) != len(throttle2):
            if len(throttle1) < len(throttle2):
                throttle2 = self._normalize_data_length(throttle2, len(throttle1))
                brake2 = self._normalize_data_length(brake2, len(brake1))
            else:
                throttle1 = self._normalize_data_length(throttle1, len(throttle2))
                brake1 = self._normalize_data_length(brake1, len(brake2))
        
        # Calculate differences
        throttle_diff = np.array(throttle2) - np.array(throttle1)
        brake_diff = np.array(brake2) - np.array(brake1)
        
        # Analyze differences
        comparison = {
            'speed': {
                'avg_diff': np.mean(speed_diff),
                'max_faster': np.max(speed_diff),
                'max_slower': np.min(speed_diff),
            },
            'Throttle': {
                'avg_diff': np.mean(throttle_diff),
                'earlier_application': np.sum(throttle_diff > 0.2),
                'later_application': np.sum(throttle_diff < -0.2),
            },
            'Brake': {
                'avg_diff': np.mean(brake_diff),
                'earlier_application': np.sum(brake_diff > 0.2),
                'later_application': np.sum(brake_diff < -0.2),
            }
        }
        
        return comparison
    
    def _extract_data_series(self, telemetry, key):
        """Extract a data series from telemetry data.
        
        Args:
            telemetry: The telemetry data
            key: The key to extract
            
        Returns:
            List of values
        """
        # If telemetry is a file path, load it
        if isinstance(telemetry, str) and os.path.isfile(telemetry):
            with open(telemetry, 'r') as f:
                telemetry = json.load(f)
        
        # If telemetry is a dictionary with the key as a list
        if isinstance(telemetry, dict) and key in telemetry and isinstance(telemetry[key], (list, np.ndarray)):
            return telemetry[key]
        
        # If telemetry is a list of data points
        if isinstance(telemetry, list) and len(telemetry) > 0 and key in telemetry[0]:
            return [point[key] for point in telemetry if key in point]
        
        return []
    
    def _normalize_data_length(self, data, target_length):
        """Normalize a data series to a target length.
        
        Args:
            data: The data series to normalize
            target_length: The target length
            
        Returns:
            Normalized data series
        """
        if len(data) == 0 or target_length == 0:
            return []
            
        # Simple linear interpolation
        indices = np.linspace(0, len(data) - 1, target_length)
        return np.interp(indices, np.arange(len(data)), data)
    
    def create_lap_time_chart(self, lap_data, width=8, height=4):
        """Create a lap time chart as a matplotlib figure.
        
        Args:
            lap_data: Dictionary with lap times and lap numbers
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            A matplotlib Figure object
        """
        fig = Figure(figsize=(width, height), dpi=100)
        ax = fig.add_subplot(111)
        
        lap_numbers = lap_data.get('lap_numbers', range(1, len(lap_data.get('lap_times', [])) + 1))
        lap_times = lap_data.get('lap_times', [])
        
        # Plot lap times
        ax.plot(lap_numbers, lap_times, 'b-', marker='o', label='Lap Time')
        
        # Add horizontal line for the best lap time
        best_lap = min(lap_times) if lap_times else 0
        ax.axhline(best_lap, color='g', linestyle='--', label=f'Best: {best_lap:.2f}s')
        
        # Add horizontal line for the average lap time
        avg_lap = np.mean(lap_times) if lap_times else 0
        ax.axhline(avg_lap, color='r', linestyle=':', label=f'Avg: {avg_lap:.2f}s')
        
        # Configure the chart
        ax.set_title('Lap Times')
        ax.set_xlabel('Lap Number')
        ax.set_ylabel('Time (seconds)')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        
        # Style the chart for dark mode
        ax.set_facecolor('#2a2a2a')
        fig.patch.set_facecolor('#353535')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        
        fig.tight_layout()
        return fig
    
    def create_speed_comparison_chart(self, speed1, speed2, label1='Reference', label2='Comparison', width=8, height=4):
        """Create a speed comparison chart as a matplotlib figure.
        
        Args:
            speed1: Speed data for the first lap
            speed2: Speed data for the second lap
            label1: Label for the first lap
            label2: Label for the second lap
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            A matplotlib Figure object
        """
        fig = Figure(figsize=(width, height), dpi=100)
        ax = fig.add_subplot(111)
        
        # Normalize lengths if needed
        if len(speed1) != len(speed2):
            if len(speed1) < len(speed2):
                speed2 = self._normalize_data_length(speed2, len(speed1))
                x_values = np.linspace(0, 100, len(speed1))
            else:
                speed1 = self._normalize_data_length(speed1, len(speed2))
                x_values = np.linspace(0, 100, len(speed2))
        else:
            x_values = np.linspace(0, 100, len(speed1))
        
        # Plot speed data
        ax.plot(x_values, speed1, 'b-', label=label1)
        ax.plot(x_values, speed2, 'r-', label=label2)
        
        # Plot speed difference
        if len(speed1) == len(speed2):
            speed_diff = np.array(speed2) - np.array(speed1)
            ax2 = ax.twinx()
            ax2.plot(x_values, speed_diff, 'g-', alpha=0.5, label='Difference')
            ax2.set_ylabel('Speed Difference (mph/kph)')
            ax2.tick_params(colors='white')
            ax2.yaxis.label.set_color('white')
        
        # Configure the chart
        ax.set_title('Speed Comparison')
        ax.set_xlabel('Lap Distance (%)')
        ax.set_ylabel('Speed (mph/kph)')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(loc='upper left')
        
        # Style the chart for dark mode
        ax.set_facecolor('#2a2a2a')
        fig.patch.set_facecolor('#353535')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        
        fig.tight_layout()
        return fig
    
    def create_input_comparison_chart(self, throttle1, throttle2, brake1, brake2, label1='Reference', label2='Comparison', width=8, height=6):
        """Create an input comparison chart as a matplotlib figure.
        
        Args:
            throttle1: Throttle data for the first lap
            throttle2: Throttle data for the second lap
            brake1: Brake data for the first lap
            brake2: Brake data for the second lap
            label1: Label for the first lap
            label2: Label for the second lap
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            A matplotlib Figure object
        """
        fig = Figure(figsize=(width, height), dpi=100)
        
        # Create subplots for Throttle and Brake
        ax1 = fig.add_subplot(211)  # Throttle
        ax2 = fig.add_subplot(212)  # Brake
        
        # Normalize lengths if needed
        if len(throttle1) != len(throttle2):
            if len(throttle1) < len(throttle2):
                throttle2 = self._normalize_data_length(throttle2, len(throttle1))
                brake2 = self._normalize_data_length(brake2, len(brake1))
                x_values = np.linspace(0, 100, len(throttle1))
            else:
                throttle1 = self._normalize_data_length(throttle1, len(throttle2))
                brake1 = self._normalize_data_length(brake1, len(brake2))
                x_values = np.linspace(0, 100, len(throttle2))
        else:
            x_values = np.linspace(0, 100, len(throttle1))
        
        # Plot throttle data
        ax1.plot(x_values, throttle1, 'g-', label=f'{label1} Throttle')
        ax1.plot(x_values, throttle2, 'g--', label=f'{label2} Throttle')
        ax1.set_title('Throttle Comparison')
        ax1.set_ylabel('Throttle Position')
        ax1.set_ylim(0, 1.1)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend()
        
        # Plot brake data
        ax2.plot(x_values, brake1, 'r-', label=f'{label1} Brake')
        ax2.plot(x_values, brake2, 'r--', label=f'{label2} Brake')
        ax2.set_title('Brake Comparison')
        ax2.set_xlabel('Lap Distance (%)')
        ax2.set_ylabel('Brake Position')
        ax2.set_ylim(0, 1.1)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.legend()
        
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
    
    def create_track_position_chart(self, position_data1, position_data2=None, width=6, height=6):
        """Create a track position chart as a matplotlib figure.
        
        Args:
            position_data1: Position data for the first lap [(x, y, z), ...]
            position_data2: Position data for the second lap (optional)
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            A matplotlib Figure object
        """
        fig = Figure(figsize=(width, height), dpi=100)
        ax = fig.add_subplot(111)
        
        # Extract x and y coordinates
        if position_data1:
            x1 = [p[0] for p in position_data1]
            y1 = [p[1] for p in position_data1]
            ax.plot(x1, y1, 'b-', label='Reference Lap')
        
        if position_data2:
            x2 = [p[0] for p in position_data2]
            y2 = [p[1] for p in position_data2]
            ax.plot(x2, y2, 'r-', label='Comparison Lap')
        
        # Configure the chart
        ax.set_title('Track Position')
        ax.set_xlabel('X Position')
        ax.set_ylabel('Y Position')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.axis('equal')  # Equal aspect ratio
        ax.legend()
        
        # Style the chart for dark mode
        ax.set_facecolor('#2a2a2a')
        fig.patch.set_facecolor('#353535')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        
        fig.tight_layout()
        return fig
    
    def create_sector_analysis_chart(self, sector_times, track_id, car_id, width=8, height=4):
        """Create a sector time comparison chart as a matplotlib figure.
        
        Args:
            sector_times: List of lists of sector times [[s1, s2, s3], ...]
            track_id: The track ID (for getting best sector times)
            car_id: The car ID (for getting best sector times)
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            A matplotlib Figure object
        """
        fig = Figure(figsize=(width, height), dpi=100)
        ax = fig.add_subplot(111)
        
        # Get the number of sectors
        num_sectors = len(sector_times[0]) if sector_times else 0
        
        # Get best sector times (if data manager is available)
        best_sector_times = []
        if self.data_manager:
            best_sectors = self.data_manager.get_best_sectors(track_id, car_id, max_sectors=num_sectors)
            best_sector_times = [sector[1] for sector in best_sectors]
        
        # Create x-values (sector numbers)
        x = np.arange(1, num_sectors + 1)
        width = 0.35  # Bar width
        
        # Plot bars for each lap's sector times
        for i, sectors in enumerate(sector_times):
            ax.bar(x + i*width/len(sector_times), sectors, width/len(sector_times), label=f'Lap {i+1}')
        
        # Plot best sector times if available
        if best_sector_times:
            for i, time in enumerate(best_sector_times):
                ax.axhline(time, xmin=(i)/num_sectors, xmax=(i+1)/num_sectors, color='g', linestyle='--')
        
        # Configure the chart
        ax.set_title('Sector Analysis')
        ax.set_xlabel('Sector')
        ax.set_ylabel('Time (seconds)')
        ax.set_xticks(x + width/2)
        ax.set_xticklabels([f'S{i}' for i in range(1, num_sectors + 1)])
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        
        # Style the chart for dark mode
        ax.set_facecolor('#2a2a2a')
        fig.patch.set_facecolor('#353535')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        
        fig.tight_layout()
        return fig
    
    def save_analysis_report(self, analysis_data, filepath):
        """Save an analysis report to a file.
        
        Args:
            analysis_data: The analysis data
            filepath: The file path to save to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving analysis report: {e}")
            return False 