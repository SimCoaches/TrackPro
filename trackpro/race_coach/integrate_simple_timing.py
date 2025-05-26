"""
Integration script to use Simple Sector Timing in the main TrackPro application.

This replaces the complex sector timing with our simple, reliable approach.
"""

import logging
from typing import Dict, Optional
from .simple_sector_timing import SimpleSectorTiming, SimpleLapTimes

logger = logging.getLogger(__name__)

class SimpleSectorTimingIntegration:
    """
    Integration wrapper for Simple Sector Timing in TrackPro.
    
    This provides a drop-in replacement for the existing sector timing
    with the same interface but using our reliable simple approach.
    """
    
    def __init__(self):
        self.timing = SimpleSectorTiming()
        self.is_enabled = False
        logger.info("🔧 Simple Sector Timing Integration initialized")
    
    def initialize_from_data_txt(self, data_txt_path: str = "data.txt") -> bool:
        """Initialize sectors from data.txt file."""
        try:
            if self.timing.set_sectors_from_data_txt(data_txt_path):
                self.is_enabled = True
                logger.info("✅ Simple sector timing enabled from data.txt")
                return True
            else:
                logger.error("❌ Failed to initialize from data.txt")
                return False
        except Exception as e:
            logger.error(f"❌ Error initializing simple timing: {e}")
            return False
    
    def initialize_manual(self, sector_boundaries: list) -> bool:
        """Initialize sectors manually."""
        try:
            if self.timing.set_sectors_manual(sector_boundaries):
                self.is_enabled = True
                logger.info(f"✅ Simple sector timing enabled with {len(sector_boundaries)} sectors")
                return True
            else:
                logger.error("❌ Failed to initialize manually")
                return False
        except Exception as e:
            logger.error(f"❌ Error initializing simple timing manually: {e}")
            return False
    
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
            # Process with simple timing
            completed_lap = self.timing.process_telemetry(telemetry_data)
            
            # Get current progress
            progress = self.timing.get_current_progress()
            
            # Format response to match existing interface
            result = {
                'current_sector': progress['current_sector'],
                'total_sectors': progress['total_sectors'],
                'current_sector_time': progress['current_sector_time'],
                'completed_sectors': progress['completed_sectors'],
                'current_lap_splits': progress['current_lap_splits'],
                'best_sector_times': progress['best_sector_times'],
                'best_lap_time': progress['best_lap_time'],
                'is_initialized': True,
                'timing_method': 'simple_own_timer',
                'completed_lap': None
            }
            
            # Add completed lap info if available
            if completed_lap:
                result['completed_lap'] = {
                    'lap_number': completed_lap.lap_number,
                    'sector_times': completed_lap.sector_times,
                    'total_time': completed_lap.total_time,
                    'is_complete': completed_lap.is_complete
                }
                
                # Log the completed lap
                sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(completed_lap.sector_times)])
                status = "COMPLETE" if completed_lap.is_complete else "PARTIAL"
                logger.info(f"🏁 SIMPLE {status} Lap {completed_lap.lap_number}: {sector_str}  LAP {completed_lap.total_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing telemetry in simple timing: {e}")
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
            self.timing = SimpleSectorTiming()
            self.is_enabled = False
            logger.info("🔄 Simple sector timing reset")
        except Exception as e:
            logger.error(f"❌ Error resetting simple timing: {e}")
    
    def get_status(self) -> Dict:
        """Get current status of the timing system."""
        if not self.is_enabled:
            return {
                'enabled': False,
                'sectors': 0,
                'current_sector': 0,
                'timing_method': 'simple_own_timer'
            }
        
        progress = self.timing.get_current_progress()
        return {
            'enabled': True,
            'sectors': progress['total_sectors'],
            'current_sector': progress['current_sector'],
            'timing_method': progress['timing_method'],
            'best_sector_times': progress['best_sector_times'],
            'best_lap_time': progress['best_lap_time']
        }

# Global instance for easy access
simple_timing_integration = SimpleSectorTimingIntegration()

def initialize_simple_timing(data_txt_path: str = "data.txt") -> bool:
    """
    Initialize the simple sector timing system.
    
    Args:
        data_txt_path: Path to data.txt file
        
    Returns:
        True if initialization was successful
    """
    return simple_timing_integration.initialize_from_data_txt(data_txt_path)

def process_simple_timing(telemetry_data: Dict) -> Optional[Dict]:
    """
    Process telemetry data with simple timing.
    
    Args:
        telemetry_data: Dict containing LapDistPct, Lap, etc.
        
    Returns:
        Dict with timing info or None
    """
    return simple_timing_integration.process_telemetry(telemetry_data)

def get_simple_timing_status() -> Dict:
    """Get current status of simple timing."""
    return simple_timing_integration.get_status()

def get_simple_recent_laps(count: int = 5) -> list:
    """Get recent laps from simple timing."""
    return simple_timing_integration.get_recent_laps(count) 