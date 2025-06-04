"""
Integration script to use 10-Sector Timing in the main TrackPro application.

This replaces the complex sector timing with our simple, reliable 10-sector approach.
"""

import logging
from typing import Dict, Optional
from .simple_ten_sector_timing import SimpleTenSectorTiming, TenSectorLapTimes

logger = logging.getLogger(__name__)

class SimpleSectorTimingIntegration:
    """
    Integration wrapper for 10-Sector Timing in TrackPro.
    
    This provides a drop-in replacement for the existing sector timing
    with the same interface but using our reliable 10-sector approach.
    """
    
    def __init__(self):
        self.timing = SimpleTenSectorTiming()
        self.is_enabled = True  # Always enabled - no setup needed
        self.frame_count = 0
        self.last_sector = 0
        self.last_completed_sectors = 0
        logger.info("🔧 10-Sector Timing Integration initialized")
        logger.info("📊 Using 10 equal sectors: 0.0-0.1, 0.1-0.2, 0.2-0.3, ..., 0.9-1.0")
    
    def initialize_from_data_txt(self, data_txt_path: str = "data.txt") -> bool:
        """Initialize - always returns True since 10-sector timing doesn't need external data."""
        logger.info("✅ 10-sector timing enabled - no external data needed")
        return True
    
    def initialize_manual(self, sector_boundaries: list) -> bool:
        """Initialize - always returns True since 10-sector timing uses fixed boundaries."""
        logger.info("✅ 10-sector timing enabled with fixed 10 equal sectors")
        return True
    
    def process_telemetry(self, telemetry_data: Dict) -> Optional[Dict]:
        """
        Process telemetry data and return sector timing information.
        
        Args:
            telemetry_data: Dict containing LapDistPct, Lap, etc.
            
        Returns:
            Dict with sector timing info, or None if not ready
        """
        if not self.is_enabled:
            return None
        
        try:
            self.frame_count += 1
            
            # Extract telemetry data for debugging
            lap_dist_pct = telemetry_data.get('LapDistPct', 0.0)
            current_lap = telemetry_data.get('Lap', 0)
            
            # Process with 10-sector timing
            completed_lap = self.timing.process_telemetry(telemetry_data)
            
            # Get current progress
            progress = self.timing.get_current_progress()
            current_sector = progress['current_sector']
            completed_sectors = progress['completed_sectors']
            
            # Debug: Log when we cross each 1/10th boundary (every 50 frames to reduce spam)
            if self.frame_count % 50 == 0:
                logger.info(f"🎯 [10-SECTOR DEBUG] Lap {current_lap}: Position {lap_dist_pct:.3f} → "
                           f"Sector {current_sector}/10, Completed: {completed_sectors}/10")
            
            # Debug: Log when sectors complete
            if completed_sectors > self.last_completed_sectors:
                logger.info(f"✅ [10-SECTOR COMPLETION] Sector {completed_sectors}/10 completed! "
                           f"Current splits: {progress['current_lap_splits']}")
                self.last_completed_sectors = completed_sectors
            
            # Debug: Log when entering new sectors
            if current_sector != self.last_sector:
                logger.info(f"🚀 [10-SECTOR BOUNDARY] Lap {current_lap}: Crossed into Sector {current_sector}/10 "
                           f"at position {lap_dist_pct:.3f}")
                self.last_sector = current_sector
            
            # Format response to match existing interface
            result = {
                'current_sector': current_sector,
                'total_sectors': progress['total_sectors'],
                'current_sector_time': progress['current_sector_time'],
                'completed_sectors': completed_sectors,
                'current_lap_splits': progress['current_lap_splits'],
                'best_sector_times': progress['best_sector_times'],
                'best_lap_time': progress['best_lap_time'],
                'is_initialized': True,
                'timing_method': '10_equal_sectors',
                'completed_lap': None,
                
                # Add 10-sector timing debug info to every frame
                'ten_sector_active': True,
                'ten_sector_current_sector': current_sector,
                'ten_sector_lap_dist': lap_dist_pct,
                'ten_sector_current_lap': current_lap,
                'ten_sector_progress': f"Sector {current_sector}/10 at {lap_dist_pct:.3f}",
                'ten_sector_completed_this_lap': completed_sectors
            }
            
            # Add completed lap info if available
            if completed_lap:
                result['completed_lap'] = {
                    'lap_number': completed_lap.lap_number,
                    'sector_times': completed_lap.sector_times,
                    'total_time': completed_lap.total_time,
                    'is_complete': completed_lap.is_complete
                }
                
                # Add sector times to the result for database saving
                # The lap saver expects sector1_time through sector10_time fields
                for i, sector_time in enumerate(completed_lap.sector_times):
                    result[f'sector{i+1}_time'] = sector_time
                
                # Also add to the main result for immediate frame processing
                result.update({
                    'sector_lap_complete': True,
                    'sector_lap_valid': completed_lap.is_valid,
                    'completed_lap_number': completed_lap.lap_number
                })
                
                # Log the completed lap with detailed sector breakdown
                sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(completed_lap.sector_times)])
                status = "COMPLETE" if completed_lap.is_complete else f"PARTIAL({len(completed_lap.sector_times)}/10)"
                logger.info(f"🏁 10-SECTOR {status} Lap {completed_lap.lap_number}: {sector_str}  LAP {completed_lap.total_time:.3f}s")
                
                # Log database fields for verification
                db_fields = [f"sector{i+1}_time={time:.3f}" for i, time in enumerate(completed_lap.sector_times)]
                logger.info(f"💾 [DATABASE] Lap {completed_lap.lap_number} sector fields: {', '.join(db_fields)}")
                
                # Reset completed sectors counter for next lap
                self.last_completed_sectors = 0
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing telemetry in 10-sector timing: {e}")
            return None
    
    def get_recent_laps(self, count: int = 5) -> list:
        """Get recent completed laps."""
        if not self.is_enabled:
            return []
        
        try:
            recent = self.timing.get_recent_laps(count)
            return [
                {
                    'lap_number': lap.lap_number,
                    'sector_times': lap.sector_times,
                    'total_time': lap.total_time,
                    'is_complete': lap.is_complete
                }
                for lap in recent
            ]
        except Exception as e:
            logger.error(f"❌ Error getting recent laps: {e}")
            return []
    
    def reset(self):
        """Reset the timing system."""
        try:
            self.timing = SimpleTenSectorTiming()
            self.frame_count = 0
            self.last_sector = 0
            self.last_completed_sectors = 0
            logger.info("🔄 10-sector timing reset")
        except Exception as e:
            logger.error(f"❌ Error resetting 10-sector timing: {e}")
    
    def get_status(self) -> Dict:
        """Get current status of the timing system."""
        if not self.is_enabled:
            return {
                'enabled': False,
                'sectors': 0,
                'current_sector': 0,
                'timing_method': '10_equal_sectors'
            }
        
        progress = self.timing.get_current_progress()
        return {
            'enabled': True,
            'sectors': progress['total_sectors'],
            'current_sector': progress['current_sector'],
            'timing_method': '10_equal_sectors',
            'best_sector_times': progress['best_sector_times'],
            'best_lap_time': progress['best_lap_time'],
            'frames_processed': self.frame_count
        }

# Global instance for easy access
simple_timing_integration = SimpleSectorTimingIntegration()

def initialize_simple_timing(data_txt_path: str = "data.txt") -> bool:
    """
    Initialize the 10-sector timing system.
    
    Args:
        data_txt_path: Path to data.txt file (ignored - 10-sector doesn't need external data)
        
    Returns:
        True if initialization was successful
    """
    return simple_timing_integration.initialize_from_data_txt(data_txt_path)

def process_simple_timing(telemetry_data: Dict) -> Optional[Dict]:
    """
    Process telemetry data with 10-sector timing.
    
    Args:
        telemetry_data: Dict containing LapDistPct, Lap, etc.
        
    Returns:
        Dict with timing info or None
    """
    return simple_timing_integration.process_telemetry(telemetry_data)

def get_simple_timing_status() -> Dict:
    """Get current status of 10-sector timing."""
    return simple_timing_integration.get_status()

def get_simple_recent_laps(count: int = 5) -> list:
    """Get recent laps from 10-sector timing."""
    return simple_timing_integration.get_recent_laps(count) 