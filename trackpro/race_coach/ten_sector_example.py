"""
Example integration of 10-sector timing with TrackPro's telemetry processing.

This script demonstrates how to integrate the new 10-sector timing system
with your existing telemetry processing pipeline.
"""

import logging
import time
from pathlib import Path

# Import the new 10-sector timing integration
from .ten_sector_integration import TenSectorTimingIntegration

# Import existing components
from .iracing_lap_saver import IRacingLapSaver
from .simple_iracing import SimpleIRacingAPI

logger = logging.getLogger(__name__)

class TenSectorTelemetryProcessor:
    """
    Example telemetry processor that integrates 10-sector timing.
    
    This shows how to modify your existing telemetry processing to include
    the new 10-sector timing system for consistent cross-track analysis.
    """
    
    def __init__(self, supabase_client=None, user_id=None):
        """Initialize the telemetry processor with 10-sector timing."""
        
        # Initialize the 10-sector timing integration
        self.ten_sector_timing = TenSectorTimingIntegration()
        
        # Initialize existing components
        self.lap_saver = IRacingLapSaver(supabase_client=supabase_client, user_id=user_id)
        self.iracing_api = SimpleIRacingAPI()
        
        # Connect the sector timing system to the lap saver
        self.lap_saver.set_sector_timing_system(self.ten_sector_timing)
        
        # State tracking
        self.is_processing = False
        self.session_active = False
        
        logger.info("🔧 TenSectorTelemetryProcessor initialized")
        logger.info("✅ 10-sector timing connected to lap saver")
    
    def start_processing(self):
        """Start telemetry processing with 10-sector timing."""
        if self.is_processing:
            logger.warning("Telemetry processing already active")
            return
        
        logger.info("🚀 Starting telemetry processing with 10-sector timing")
        
        # Reset for new session
        self.ten_sector_timing.reset_session_data()
        
        # Connect to telemetry signals
        self.iracing_api.telemetry_updated.connect(self._process_telemetry_frame)
        
        # Start the iRacing API
        self.iracing_api.start()
        
        self.is_processing = True
        logger.info("✅ 10-sector telemetry processing started")
    
    def stop_processing(self):
        """Stop telemetry processing."""
        if not self.is_processing:
            return
        
        logger.info("🛑 Stopping telemetry processing")
        
        # Stop the iRacing API
        self.iracing_api.stop()
        
        # Disconnect signals
        self.iracing_api.telemetry_updated.disconnect(self._process_telemetry_frame)
        
        # End the session
        if self.session_active:
            self.lap_saver.end_session()
            self.session_active = False
        
        self.is_processing = False
        logger.info("✅ Telemetry processing stopped")
    
    def _process_telemetry_frame(self, telemetry_data):
        """
        Process a telemetry frame through the 10-sector timing system.
        
        This is the key integration point where telemetry data gets enhanced
        with 10-sector timing information.
        """
        try:
            # Ensure we have a session
            if not self.session_active:
                self._setup_session(telemetry_data)
            
            # Process the frame through 10-sector timing
            enhanced_frame = self.ten_sector_timing.process_telemetry_frame(telemetry_data)
            
            # Send enhanced frame to lap saver (which will detect sector data and save it)
            self.lap_saver.process_telemetry(enhanced_frame)
            
            # Log sector timing info periodically
            if enhanced_frame.get('sector_lap_complete'):
                self._log_completed_lap(enhanced_frame)
            
        except Exception as e:
            logger.error(f"Error processing telemetry frame: {e}")
    
    def _setup_session(self, telemetry_data):
        """Set up a new session with track and car information."""
        try:
            # Extract session info
            track_name = telemetry_data.get('TrackDisplayName', 'Unknown Track')
            car_name = telemetry_data.get('CarName', 'Unknown Car')
            session_type = telemetry_data.get('SessionType', 'Practice')
            
            logger.info(f"🏁 Setting up session: {track_name} | {car_name} | {session_type}")
            
            # Setup session (this will create database records)
            # Note: You may need to modify this based on your existing session setup
            
            self.session_active = True
            logger.info("✅ Session setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up session: {e}")
    
    def _log_completed_lap(self, enhanced_frame):
        """Log information about a completed lap."""
        lap_number = enhanced_frame.get('completed_lap_number', 0)
        sector_times = enhanced_frame.get('sector_times', [])
        total_time = enhanced_frame.get('sector_total_time', 0.0)
        
        logger.info(f"🏁 LAP {lap_number} COMPLETED")
        logger.info(f"📊 Total time: {total_time:.3f}s")
        logger.info(f"🔢 Sector times: {[f'S{i+1}: {t:.3f}s' for i, t in enumerate(sector_times)]}")
        
        # Get comparison with best times
        comparison = self.ten_sector_timing.get_sector_comparison_for_lap(lap_number)
        if comparison and not comparison['is_theoretical_best']:
            total_delta = comparison['total_delta']
            logger.info(f"🔍 vs Personal Best: {total_delta:+.3f}s")
    
    def get_current_sector_status(self):
        """Get current sector timing status for UI display."""
        return self.ten_sector_timing.get_current_sector_info()
    
    def get_session_statistics(self):
        """Get comprehensive session statistics."""
        sector_stats = self.ten_sector_timing.get_statistics()
        
        # Add lap saver statistics if available
        if hasattr(self.lap_saver, 'get_processing_status'):
            lap_saver_stats = self.lap_saver.get_processing_status()
            sector_stats['lap_saver'] = lap_saver_stats
        
        return sector_stats
    
    def get_theoretical_best_lap(self):
        """Get the theoretical best lap from sector times."""
        return self.ten_sector_timing.get_theoretical_best_lap()
    
    def get_lap_sector_analysis(self, lap_number):
        """Get detailed sector analysis for a specific lap."""
        return self.ten_sector_timing.get_lap_sector_breakdown(lap_number)


def demonstrate_ten_sector_usage():
    """
    Demonstration function showing how to use the 10-sector timing system.
    """
    logger.info("🎯 DEMONSTRATING 10-SECTOR TIMING INTEGRATION")
    
    # Initialize the processor
    processor = TenSectorTelemetryProcessor()
    
    # Example: Simulate some telemetry data to show sector timing
    example_telemetry_frames = [
        # Lap start
        {'track_position': 0.05, 'timestamp': 100.0, 'lap_count': 1, 'speed': 45.0},
        {'track_position': 0.15, 'timestamp': 105.0, 'lap_count': 1, 'speed': 60.0},  # Sector 1 -> 2
        {'track_position': 0.25, 'timestamp': 110.0, 'lap_count': 1, 'speed': 75.0},  # Sector 2 -> 3
        {'track_position': 0.35, 'timestamp': 115.0, 'lap_count': 1, 'speed': 80.0},  # Sector 3 -> 4
        {'track_position': 0.45, 'timestamp': 120.0, 'lap_count': 1, 'speed': 82.0},  # Sector 4 -> 5
        {'track_position': 0.55, 'timestamp': 125.0, 'lap_count': 1, 'speed': 78.0},  # Sector 5 -> 6
        {'track_position': 0.65, 'timestamp': 130.0, 'lap_count': 1, 'speed': 75.0},  # Sector 6 -> 7
        {'track_position': 0.75, 'timestamp': 135.0, 'lap_count': 1, 'speed': 70.0},  # Sector 7 -> 8
        {'track_position': 0.85, 'timestamp': 140.0, 'lap_count': 1, 'speed': 65.0},  # Sector 8 -> 9
        {'track_position': 0.95, 'timestamp': 145.0, 'lap_count': 1, 'speed': 60.0},  # Sector 9 -> 10
        {'track_position': 0.05, 'timestamp': 150.0, 'lap_count': 1, 'speed': 55.0},  # Lap complete
        
        # Second lap for comparison
        {'track_position': 0.15, 'timestamp': 154.0, 'lap_count': 2, 'speed': 62.0},  # Faster sector 1
        {'track_position': 0.25, 'timestamp': 158.5, 'lap_count': 2, 'speed': 77.0},  # Faster sector 2
        # ... etc
    ]
    
    logger.info("📊 Processing example telemetry frames...")
    
    for i, frame in enumerate(example_telemetry_frames):
        enhanced_frame = processor.ten_sector_timing.process_telemetry_frame(frame)
        
        # Show sector progress
        if enhanced_frame.get('sector_lap_complete'):
            logger.info(f"✅ Lap completed in frame {i}")
            break
        elif enhanced_frame.get('completed_sectors_count', 0) > 0:
            current_sector = enhanced_frame.get('current_sector', 0)
            sector_time = enhanced_frame.get('current_sector_time', 0)
            logger.info(f"🏁 Frame {i}: In sector {current_sector}, current time: {sector_time:.3f}s")
    
    # Show final statistics
    stats = processor.ten_sector_timing.get_statistics()
    logger.info(f"📈 Final statistics: {stats}")
    
    # Show theoretical best if available
    theoretical_best = processor.get_theoretical_best_lap()
    if theoretical_best:
        logger.info(f"🏆 Theoretical best lap: {theoretical_best['total_time']:.3f}s")
    
    logger.info("✅ 10-sector timing demonstration complete")


if __name__ == "__main__":
    # Run demonstration
    logging.basicConfig(level=logging.INFO)
    demonstrate_ten_sector_usage() 