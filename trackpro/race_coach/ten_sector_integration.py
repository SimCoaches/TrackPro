"""
Integration wrapper for the 10-sector timing system with TrackPro telemetry processing.

This module integrates the SimpleTenSectorTiming system with the existing telemetry 
processing pipeline, ensuring sector times are embedded in telemetry frames and 
saved to the database.
"""

import logging
import time
from typing import Dict, List, Optional, Any

from .simple_ten_sector_timing import SimpleTenSectorTiming, TenSectorLapTimes

logger = logging.getLogger(__name__)

class TenSectorTimingIntegration:
    """
    Integration wrapper that connects the 10-sector timing system with telemetry processing.
    
    This class:
    - Processes telemetry data through the 10-sector timing system
    - Embeds sector timing data into telemetry frames
    - Provides sector data to the IRacingLapSaver for database storage
    - Offers real-time sector timing information
    """
    
    def __init__(self):
        """Initialize the 10-sector timing integration."""
        self.sector_timing = SimpleTenSectorTiming()
        
        # Integration state
        self.is_active = True
        self.last_telemetry_timestamp = 0.0
        
        # Completed lap storage for retrieval
        self.completed_laps = []
        self.latest_completed_lap = None
        
        # Current session state
        self.current_session_data = {
            'total_laps_processed': 0,
            'total_sectors_completed': 0,
            'session_start_time': time.time()
        }
        
        # Statistics
        self.stats = {
            'telemetry_frames_processed': 0,
            'sector_crossings_detected': 0,
            'laps_completed': 0,
            'integration_errors': 0
        }
        
        logger.info("🔧 10-Sector Timing Integration initialized")
        logger.info("📊 Ready to process telemetry with 10 equal sectors (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)")
    
    def process_telemetry_frame(self, telemetry_data: Dict) -> Dict:
        """
        Process a telemetry frame through the 10-sector timing system.
        
        This method enhances the telemetry frame with sector timing data that can
        be used by the IRacingLapSaver for database storage.
        
        Args:
            telemetry_data: Raw telemetry data frame
            
        Returns:
            Enhanced telemetry frame with sector timing data embedded
        """
        try:
            self.stats['telemetry_frames_processed'] += 1
            self.last_telemetry_timestamp = telemetry_data.get('timestamp', time.time())
            
            # Create a copy to avoid modifying the original
            enhanced_frame = telemetry_data.copy()
            
            # Process through the 10-sector timing system
            completed_lap = self.sector_timing.process_telemetry(telemetry_data)
            
            # Get current sector timing progress
            sector_progress = self.sector_timing.get_current_progress()
            
            # Embed sector timing data into the frame for IRacingLapSaver
            enhanced_frame.update({
                # Current sector timing state
                'sector_timing_initialized': True,
                'sector_timing_method': '10_equal_sectors',
                'current_sector': sector_progress['current_sector'],  # 1-10
                'total_sectors': sector_progress['total_sectors'],  # 10
                'current_sector_time': sector_progress['current_sector_time'],
                'completed_sectors_count': sector_progress['completed_sectors'],
                'current_lap_sector_times': sector_progress['current_lap_splits'],
                
                # Best times for comparison
                'best_sector_times': sector_progress['best_sector_times'],
                'best_lap_time': sector_progress['best_lap_time'],
                
                # Sector boundaries for reference
                'sector_boundaries': sector_progress['sector_boundaries']
            })
            
            # If a lap was completed, add the completed sector data
            if completed_lap:
                self.stats['laps_completed'] += 1
                self.stats['sector_crossings_detected'] += len(completed_lap.sector_times)
                
                # Store the completed lap
                self.completed_laps.append(completed_lap)
                self.latest_completed_lap = completed_lap
                
                # Add completed lap data to the frame for direct saving to laps table
                sector_data = {}
                for i, sector_time in enumerate(completed_lap.sector_times):
                    sector_data[f'sector{i+1}_time'] = sector_time
                
                enhanced_frame.update({
                    'sector_times': completed_lap.sector_times,
                    'sector_total_time': completed_lap.total_time,
                    'sector_lap_complete': True,
                    'sector_lap_valid': completed_lap.is_valid,
                    'completed_lap_number': completed_lap.lap_number,
                    **sector_data  # Add sector1_time through sector10_time directly
                })
                
                # Update session statistics
                self.current_session_data['total_laps_processed'] += 1
                self.current_session_data['total_sectors_completed'] += len(completed_lap.sector_times)
                
                logger.info(f"✅ 10-SECTOR LAP COMPLETE: Lap {completed_lap.lap_number}")
                logger.info(f"📊 Sector times: {[f'S{i+1}: {t:.3f}s' for i, t in enumerate(completed_lap.sector_times)]}")
                logger.info(f"⏱️  Total time: {completed_lap.total_time:.3f}s")
                
                # Log sector comparison if we have best times
                comparison = self.sector_timing.get_sector_comparison(completed_lap)
                if comparison and not comparison['is_theoretical_best']:
                    deltas = [s['delta'] for s in comparison['sectors'] if s['best_time'] is not None]
                    if deltas:
                        total_delta = sum(deltas)
                        logger.info(f"🔍 vs Personal Best: {total_delta:+.3f}s total delta")
            
            # Log sector crossings for debugging
            if enhanced_frame.get('completed_sectors_count', 0) != sector_progress.get('completed_sectors', 0):
                sector_num = sector_progress['current_sector']
                logger.debug(f"🏁 Sector {sector_num} crossed (10-sector system)")
                self.stats['sector_crossings_detected'] += 1
            
            return enhanced_frame
            
        except Exception as e:
            self.stats['integration_errors'] += 1
            logger.error(f"❌ Error in 10-sector timing integration: {e}")
            
            # Return original frame on error to prevent breaking the pipeline
            error_frame = telemetry_data.copy()
            error_frame['sector_timing_error'] = str(e)
            return error_frame
    
    def get_recent_laps(self, count: int = 5) -> List[Dict]:
        """
        Get recent completed laps in a format compatible with IRacingLapSaver fallback.
        
        Args:
            count: Number of recent laps to return
            
        Returns:
            List of lap dictionaries with sector timing data
        """
        recent_sector_laps = self.sector_timing.get_recent_laps(count)
        
        # Convert to dictionary format for compatibility
        lap_dicts = []
        for lap in recent_sector_laps:
            lap_dict = {
                'lap_number': lap.lap_number,
                'sector_times': lap.sector_times,
                'total_time': lap.total_time,
                'timestamp': lap.timestamp,
                'is_complete': lap.is_complete,
                'is_valid': lap.is_valid,
                'num_sectors': len(lap.sector_times),
                'sector_method': '10_equal_sectors'
            }
            lap_dicts.append(lap_dict)
        
        return lap_dicts
    
    def get_current_sector_info(self) -> Dict:
        """
        Get current sector timing information for UI display.
        
        Returns:
            Dictionary with current sector timing status
        """
        progress = self.sector_timing.get_current_progress()
        
        return {
            'current_sector': progress['current_sector'],  # 1-10
            'current_sector_time': progress['current_sector_time'],
            'completed_sectors': progress['completed_sectors'],
            'current_lap_splits': progress['current_lap_splits'],
            'best_sector_times': progress['best_sector_times'],
            'best_lap_time': progress['best_lap_time'],
            'timing_method': '10 Equal Sectors',
            'sector_boundaries': progress['sector_boundaries'],
            'is_initialized': True
        }
    
    def get_sector_comparison_for_lap(self, lap_number: int) -> Optional[Dict]:
        """
        Get sector comparison data for a specific lap.
        
        Args:
            lap_number: The lap number to get comparison for
            
        Returns:
            Dictionary with sector comparison data or None if lap not found
        """
        # Find the lap in completed laps
        for completed_lap in self.completed_laps:
            if completed_lap.lap_number == lap_number:
                return self.sector_timing.get_sector_comparison(completed_lap)
        
        return None
    
    def get_theoretical_best_lap(self) -> Optional[Dict]:
        """
        Get the theoretical best lap using best sector times.
        
        Returns:
            Dictionary with theoretical best lap data or None if no data
        """
        theoretical_best = self.sector_timing.create_theoretical_best_lap()
        
        if theoretical_best:
            return {
                'lap_number': -1,  # Special indicator for theoretical best
                'sector_times': theoretical_best.sector_times,
                'total_time': theoretical_best.total_time,
                'is_theoretical': True,
                'num_sectors': len(theoretical_best.sector_times),
                'sector_method': '10_equal_sectors'
            }
        
        return None
    
    def get_best_sector_times(self) -> List[Optional[float]]:
        """
        Get the best time for each sector.
        
        Returns:
            List of best sector times (None for sectors without times yet)
        """
        return self.sector_timing.get_best_sector_times()
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive statistics about the sector timing integration.
        
        Returns:
            Dictionary with integration statistics
        """
        session_duration = time.time() - self.current_session_data['session_start_time']
        
        stats = self.stats.copy()
        stats.update({
            'session_duration_seconds': session_duration,
            'session_laps_processed': self.current_session_data['total_laps_processed'],
            'session_sectors_completed': self.current_session_data['total_sectors_completed'],
            'telemetry_rate_hz': self.stats['telemetry_frames_processed'] / max(session_duration, 1),
            'error_rate_percent': (self.stats['integration_errors'] / max(self.stats['telemetry_frames_processed'], 1)) * 100,
            'latest_lap_time': self.latest_completed_lap.total_time if self.latest_completed_lap else None,
            'best_lap_time': self.sector_timing.best_lap_time,
            'last_telemetry_timestamp': self.last_telemetry_timestamp,
            'integration_active': self.is_active
        })
        
        return stats
    
    def reset_session_data(self):
        """Reset data for a new session."""
        logger.info("🔄 Resetting 10-sector timing integration for new session")
        
        # Clear sector timing data
        self.sector_timing.clear_data()
        
        # Reset integration state
        self.completed_laps = []
        self.latest_completed_lap = None
        
        # Reset session data
        self.current_session_data = {
            'total_laps_processed': 0,
            'total_sectors_completed': 0,
            'session_start_time': time.time()
        }
        
        # Reset stats (keep lifetime totals)
        self.stats = {
            'telemetry_frames_processed': 0,
            'sector_crossings_detected': 0,
            'laps_completed': 0,
            'integration_errors': 0
        }
        
        logger.info("✅ 10-sector timing integration reset complete")
    
    def set_active(self, active: bool):
        """Enable or disable the sector timing integration.
        
        Args:
            active: Whether to process telemetry through sector timing
        """
        self.is_active = active
        logger.info(f"🔧 10-sector timing integration {'activated' if active else 'deactivated'}")
    
    def get_lap_sector_breakdown(self, lap_number: int) -> Optional[Dict]:
        """
        Get detailed sector breakdown for a specific lap.
        
        Args:
            lap_number: The lap number to analyze
            
        Returns:
            Dictionary with detailed sector analysis or None if lap not found
        """
        # Find the requested lap
        target_lap = None
        for completed_lap in self.completed_laps:
            if completed_lap.lap_number == lap_number:
                target_lap = completed_lap
                break
        
        if not target_lap:
            return None
        
        # Get sector comparison
        comparison = self.sector_timing.get_sector_comparison(target_lap)
        best_times = self.get_best_sector_times()
        
        breakdown = {
            'lap_number': lap_number,
            'total_time': target_lap.total_time,
            'is_valid': target_lap.is_valid,
            'is_complete': target_lap.is_complete,
            'sectors': []
        }
        
        for i, sector_time in enumerate(target_lap.sector_times):
            sector_info = {
                'sector_number': i + 1,
                'time': sector_time,
                'best_time': best_times[i],
                'delta': sector_time - best_times[i] if best_times[i] else 0.0,
                'is_personal_best': best_times[i] is None or sector_time <= best_times[i] + 0.001,
                'percentage_of_lap': (sector_time / target_lap.total_time) * 100,
                'sector_boundaries': {
                    'start': i * 0.1,
                    'end': (i + 1) * 0.1 if i < 9 else 1.0
                }
            }
            breakdown['sectors'].append(sector_info)
        
        # Add summary statistics
        if comparison:
            breakdown['total_delta'] = comparison['total_delta']
            breakdown['is_theoretical_best'] = comparison['is_theoretical_best']
            breakdown['personal_best_sectors'] = sum(1 for s in breakdown['sectors'] if s['is_personal_best'])
        
        return breakdown 