"""
FIXED Sector Timing - Proper Duration Calculation

This fixes the critical bug where sector times were calculated as:
sector_time = SessionTime - LapDistPct (WRONG!)

Instead of:
sector_time = current_SessionTime - sector_start_SessionTime (CORRECT!)
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SectorInfo:
    """Information about a track sector."""
    sector_num: int
    start_pct: float

@dataclass
class SectorTime:
    """A completed sector time."""
    sector_num: int
    time: float
    lap_number: int
    timestamp: float

@dataclass
class LapSectorTimes:
    """Complete sector times for a lap."""
    lap_number: int
    sector_times: List[float]  # Times for each sector
    total_time: float
    timestamp: float
    is_valid: bool = True

class FixedSectorTimingCollector:
    """
    FIXED Sector Timing Collector that properly calculates sector durations.
    
    Key Fix:
    - Tracks sector_start_time (SessionTime when entering sector)
    - Calculates sector_time = current_SessionTime - sector_start_time
    - No longer mixes timestamps with percentages!
    """
    
    def __init__(self):
        # Sector configuration
        self.sectors: List[SectorInfo] = []
        self.sector_starts: List[float] = []
        self.is_initialized = False
        
        # Current timing state
        self.current_sector_index = 0
        self.current_lap_number = 0
        self.sector_start_time = 0.0  # ✅ FIXED: Track when we entered current sector
        self.lap_start_time = 0.0
        
        # Current lap tracking
        self.current_lap_sector_times = []
        
        # Historical data
        self.completed_laps: List[LapSectorTimes] = []
        self.sector_times_history: List[SectorTime] = []
        self.best_sector_times: List[Optional[float]] = []
        self.best_lap_time: Optional[float] = None
        
        # Previous telemetry for comparison
        self.prev_pct = 0.0
        self.prev_time = 0.0
        
        logger.info("🔧 FIXED Sector Timing Collector initialized")
    
    def update_session_info(self, session_info_raw: str) -> bool:
        """Update sector configuration from SessionInfo."""
        try:
            import yaml
            
            # Extract YAML portion
            yaml_content = self._extract_yaml_from_session_info(session_info_raw)
            if not yaml_content:
                logger.error("❌ No YAML content found in SessionInfo")
                return False
            
            # Parse YAML
            session_data = yaml.safe_load(yaml_content)
            if not session_data or 'SplitTimeInfo' not in session_data:
                logger.error("❌ No SplitTimeInfo found in SessionInfo")
                return False
            
            # Extract sectors
            split_info = session_data['SplitTimeInfo']
            if 'Sectors' not in split_info:
                logger.error("❌ No Sectors found in SplitTimeInfo")
                return False
            
            # Parse sector boundaries
            sectors_data = split_info['Sectors']
            new_sectors = []
            
            for sector_data in sectors_data:
                sector = SectorInfo(
                    sector_num=sector_data['SectorNum'],
                    start_pct=sector_data['SectorStartPct']
                )
                new_sectors.append(sector)
            
            # Sort by sector number
            new_sectors.sort(key=lambda s: s.sector_num)
            
            # Update sectors
            self.sectors = new_sectors
            self.sector_starts = [s.start_pct for s in self.sectors] + [1.0]  # Add finish line
            self.best_sector_times = [None] * len(self.sectors)
            
            # Reset timing state
            self._reset_timing_state()
            self.is_initialized = True
            
            logger.info(f"✅ FIXED sector timing initialized with {len(self.sectors)} sectors")
            for i, sector in enumerate(self.sectors):
                logger.info(f"   🏁 Sector {i+1}: starts at {sector.start_pct:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating session info: {e}")
            return False
    
    def _extract_yaml_from_session_info(self, session_info_raw: str) -> str:
        """Extract YAML portion from SessionInfo."""
        try:
            lines = session_info_raw.split('\n')
            yaml_lines = []
            
            for line in lines:
                if not line.strip():
                    yaml_lines.append(line)
                    continue
                
                # Stop at telemetry data
                if '                    ' in line and line.count(' ') > 20:
                    break
                
                yaml_lines.append(line)
            
            return '\n'.join(yaml_lines)
            
        except Exception as e:
            logger.error(f"❌ Error extracting YAML: {e}")
            return ""
    
    def _reset_timing_state(self):
        """Reset timing state."""
        self.prev_pct = 0.0
        self.prev_time = 0.0
        self.current_sector_index = 0
        self.current_lap_number = 0
        self.current_lap_sector_times = []
        self.sector_start_time = 0.0  # ✅ FIXED: Reset sector start time
        self.lap_start_time = 0.0
        logger.info("🔄 FIXED timing state reset")
    
    def process_telemetry(self, telemetry_data: Dict) -> Optional[LapSectorTimes]:
        """
        ✅ FIXED: Process telemetry with proper sector duration calculation.
        """
        if not self.is_initialized:
            return None
        
        try:
            # Extract telemetry
            now_pct = telemetry_data.get('LapDistPct')
            now_time = telemetry_data.get('SessionTime') or telemetry_data.get('SessionTimeSecs')
            current_lap = telemetry_data.get('Lap', 0)
            
            if now_pct is None or now_time is None:
                return None
            
            # Handle lap changes
            if current_lap != self.current_lap_number:
                if current_lap < self.current_lap_number:
                    logger.info(f"🔄 Session reset detected")
                    self._reset_timing_state()
                elif current_lap > self.current_lap_number and self.current_lap_sector_times:
                    logger.info(f"🏁 Finalizing incomplete lap {self.current_lap_number}")
                    self._finalize_incomplete_lap(now_time)
                
                self.current_lap_number = current_lap
            
            # Initialize on first telemetry
            if self.prev_time == 0.0:
                self.prev_pct = now_pct
                self.prev_time = now_time
                self.current_sector_index = self._get_current_sector_index(now_pct)
                self.sector_start_time = now_time  # ✅ FIXED: Set sector start time
                self.lap_start_time = now_time
                self.current_lap_sector_times = []
                
                logger.info(f"🏁 FIXED timing started in sector {self.current_sector_index + 1}")
                return None
            
            # Check for sector changes
            expected_sector_index = self._get_current_sector_index(now_pct)
            
            if expected_sector_index != self.current_sector_index:
                # ✅ FIXED: Calculate sector time properly!
                sector_time = now_time - self.sector_start_time
                
                logger.info(f"🏁 FIXED S{self.current_sector_index + 1}: {sector_time:.3f}s (lap {self.current_lap_number})")
                
                # Validate sector time is reasonable
                if sector_time < 0:
                    logger.warning(f"⚠️ Negative sector time detected: {sector_time:.3f}s - skipping")
                    return None
                
                if sector_time > 300:  # 5 minutes
                    logger.warning(f"⚠️ Very long sector time: {sector_time:.1f}s ({sector_time/60:.1f} minutes)")
                
                # Store sector time
                self.current_lap_sector_times.append(sector_time)
                
                # Update best sector time
                if (self.best_sector_times[self.current_sector_index] is None or 
                    sector_time < self.best_sector_times[self.current_sector_index]):
                    self.best_sector_times[self.current_sector_index] = sector_time
                    logger.info(f"✨ New best S{self.current_sector_index + 1}: {sector_time:.3f}s")
                
                # Move to new sector
                self.current_sector_index = expected_sector_index
                self.sector_start_time = now_time  # ✅ FIXED: Update sector start time
                
                # Check for lap completion
                if self.current_sector_index == 0 and len(self.current_lap_sector_times) == len(self.sectors):
                    return self._complete_lap(now_time)
            
            # Update previous values
            self.prev_pct = now_pct
            self.prev_time = now_time
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in FIXED sector timing: {e}")
            return None
    
    def _get_current_sector_index(self, track_position: float) -> int:
        """Determine current sector from track position."""
        if track_position >= 0.99:
            return len(self.sectors) - 1
        
        for i in range(len(self.sectors)):
            sector_start = self.sectors[i].start_pct
            sector_end = self.sectors[i + 1].start_pct if i + 1 < len(self.sectors) else 1.0
            
            if sector_start <= track_position < sector_end:
                return i
        
        return 0
    
    def _complete_lap(self, timestamp: float) -> LapSectorTimes:
        """Complete the current lap."""
        try:
            total_time = sum(self.current_lap_sector_times)
            
            lap_sectors = LapSectorTimes(
                lap_number=self.current_lap_number,
                sector_times=self.current_lap_sector_times.copy(),
                total_time=total_time,
                timestamp=timestamp,
                is_valid=True
            )
            
            # Update best lap
            if self.best_lap_time is None or total_time < self.best_lap_time:
                self.best_lap_time = total_time
                logger.info(f"✨ New best lap: {total_time:.3f}s")
            
            # Log completion
            sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(self.current_lap_sector_times)])
            logger.info(f"🏁 FIXED COMPLETE Lap {self.current_lap_number}: {sector_str}  LAP {total_time:.3f}s")
            
            # Store and reset
            self.completed_laps.append(lap_sectors)
            self.current_lap_sector_times = []
            
            return lap_sectors
            
        except Exception as e:
            logger.error(f"❌ Error completing lap: {e}")
            return LapSectorTimes(
                lap_number=self.current_lap_number,
                sector_times=self.current_lap_sector_times.copy(),
                total_time=sum(self.current_lap_sector_times) if self.current_lap_sector_times else 0.0,
                timestamp=timestamp,
                is_valid=False
            )
    
    def _finalize_incomplete_lap(self, timestamp: float):
        """Handle incomplete laps."""
        if not self.current_lap_sector_times:
            return
        
        # Add current sector time if in progress
        if self.sector_start_time > 0:
            current_sector_time = timestamp - self.sector_start_time
            self.current_lap_sector_times.append(current_sector_time)
            logger.info(f"🔧 Added final sector time {current_sector_time:.3f}s for incomplete lap")
        
        total_time = sum(self.current_lap_sector_times)
        
        incomplete_lap = LapSectorTimes(
            lap_number=self.current_lap_number,
            sector_times=self.current_lap_sector_times.copy(),
            total_time=total_time,
            timestamp=timestamp,
            is_valid=False
        )
        
        self.completed_laps.append(incomplete_lap)
        
        sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(self.current_lap_sector_times)])
        logger.warning(f"⚠️ INCOMPLETE Lap {self.current_lap_number}: {sector_str}  PARTIAL {total_time:.3f}s")
        
        self.current_lap_sector_times = []
    
    def get_current_sector_progress(self) -> Dict:
        """Get current progress with FIXED calculations."""
        if not self.is_initialized:
            return {
                'current_sector': 0,
                'total_sectors': 0,
                'current_sector_time': 0.0,
                'completed_sectors': 0,
                'current_lap_splits': [],
                'best_sector_times': [],
                'best_lap_time': None,
                'is_initialized': False,
                'timing_mode': 'FIXED_duration_calculation'
            }
        
        # ✅ FIXED: Calculate current sector time properly
        current_sector_time = self.prev_time - self.sector_start_time if self.sector_start_time > 0 else 0.0
        
        return {
            'current_sector': self.current_sector_index + 1,
            'total_sectors': len(self.sectors),
            'current_sector_time': current_sector_time,
            'completed_sectors': len(self.current_lap_sector_times),
            'current_lap_splits': self.current_lap_sector_times.copy(),
            'best_sector_times': self.best_sector_times.copy(),
            'best_lap_time': self.best_lap_time,
            'is_initialized': True,
            'timing_mode': 'FIXED_duration_calculation',
            'sector_start_time': self.sector_start_time,
            'current_time': self.prev_time
        }

def create_fixed_sector_timing() -> FixedSectorTimingCollector:
    """Factory function to create fixed sector timing."""
    return FixedSectorTimingCollector() 