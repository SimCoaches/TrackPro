"""
Simple Sector Timing - Clean Implementation

Uses our own timer and watches LapDistPct for sector boundary crossings.
No dependency on iRacing's SessionTime or complex calculations.
"""

import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SimpleSectorInfo:
    """Simple sector boundary information."""
    sector_num: int
    start_pct: float

@dataclass
class SimpleSectorTime:
    """A completed sector time with our own timing."""
    sector_num: int
    time: float  # Duration in seconds
    lap_number: int
    start_time: float  # When we entered this sector
    end_time: float    # When we left this sector

@dataclass
class SimpleLapTimes:
    """Complete lap with sector times."""
    lap_number: int
    sector_times: List[float]
    total_time: float
    is_complete: bool

class SimpleSectorTiming:
    """
    Simple, reliable sector timing using our own timer.
    
    Approach:
    1. Use time.time() for our own timing
    2. Watch LapDistPct for sector boundary crossings
    3. Calculate sector durations as: end_time - start_time
    4. No dependency on iRacing's SessionTime
    """
    
    def __init__(self):
        # Sector configuration
        self.sectors: List[SimpleSectorInfo] = []
        self.is_initialized = False
        
        # Current timing state
        self.current_sector = 0
        self.current_lap = 0
        self.sector_start_time = 0.0  # Our own timer
        self.lap_start_time = 0.0
        
        # Current lap data
        self.current_lap_sectors: List[float] = []
        
        # Completed data
        self.completed_laps: List[SimpleLapTimes] = []
        self.best_sector_times: List[Optional[float]] = []
        self.best_lap_time: Optional[float] = None
        
        # Previous telemetry for crossing detection
        self.prev_lap_dist_pct = 0.0
        self.prev_lap_number = 0
        
        logger.info("🔧 Simple Sector Timing initialized - using our own timer")
    
    def set_sectors_from_data_txt(self, data_txt_path: str = "data.txt") -> bool:
        """
        Load sector boundaries from data.txt file.
        
        Args:
            data_txt_path: Path to data.txt file
            
        Returns:
            True if sectors were loaded successfully
        """
        try:
            import os
            if not os.path.exists(data_txt_path):
                logger.error(f"❌ data.txt not found at {data_txt_path}")
                return False
            
            with open(data_txt_path, 'r') as f:
                content = f.read()
            
            logger.info(f"📄 Reading sector data from {data_txt_path}")
            
            # Parse SplitTimeInfo section
            self.sectors = []
            in_split_time_info = False
            in_sectors = False
            
            for line in content.split('\n'):
                line = line.strip()
                
                if line == "SplitTimeInfo:":
                    in_split_time_info = True
                    continue
                elif in_split_time_info and line == "Sectors:":
                    in_sectors = True
                    continue
                elif in_split_time_info and in_sectors:
                    if line.startswith("- SectorNum:"):
                        # Start of a new sector
                        sector_num = int(line.split(":")[1].strip())
                    elif line.startswith("SectorStartPct:"):
                        # Get the start percentage
                        start_pct = float(line.split(":")[1].strip())
                        self.sectors.append(SimpleSectorInfo(sector_num=sector_num, start_pct=start_pct))
                elif in_split_time_info and line and not line.startswith(" ") and not line.startswith("-"):
                    # We've left the SplitTimeInfo section
                    break
            
            if not self.sectors:
                # Fallback to 2-sector setup if parsing failed
                logger.warning("⚠️ Could not parse sectors from data.txt, using 2-sector fallback")
                self.sectors = [
                    SimpleSectorInfo(sector_num=0, start_pct=0.000),
                    SimpleSectorInfo(sector_num=1, start_pct=0.500)
                ]
            
            self.best_sector_times = [None] * len(self.sectors)
            self.is_initialized = True
            
            logger.info(f"✅ Loaded {len(self.sectors)} sectors from data.txt")
            for sector in self.sectors:
                logger.info(f"   🏁 Sector {sector.sector_num + 1}: starts at {sector.start_pct:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading sectors from data.txt: {e}")
            return False
    
    def set_sectors_manual(self, sector_boundaries: List[float]) -> bool:
        """
        Set sector boundaries manually.
        
        Args:
            sector_boundaries: List of LapDistPct values where sectors start
                              e.g., [0.0, 0.333, 0.666] for 3 equal sectors
        
        Returns:
            True if sectors were set successfully
        """
        try:
            self.sectors = []
            for i, start_pct in enumerate(sector_boundaries):
                self.sectors.append(SimpleSectorInfo(sector_num=i, start_pct=start_pct))
            
            self.best_sector_times = [None] * len(self.sectors)
            self.is_initialized = True
            
            logger.info(f"✅ Set {len(self.sectors)} sectors manually")
            for sector in self.sectors:
                logger.info(f"   🏁 Sector {sector.sector_num + 1}: starts at {sector.start_pct:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting sectors manually: {e}")
            return False
    
    def process_telemetry(self, telemetry_data: Dict) -> Optional[SimpleLapTimes]:
        """
        Process telemetry data using our own timing.
        
        Args:
            telemetry_data: Dict containing at least:
                - LapDistPct: Current track position (0.0 to 1.0)
                - Lap: Current lap number
        
        Returns:
            SimpleLapTimes if a lap was completed, None otherwise
        """
        if not self.is_initialized:
            return None
        
        try:
            # Get current time using our own timer
            now = time.time()
            
            # Extract telemetry
            lap_dist_pct = telemetry_data.get('LapDistPct')
            lap_number = telemetry_data.get('Lap', 0)
            
            if lap_dist_pct is None:
                return None
            
            # Handle lap changes
            if lap_number != self.current_lap:
                if lap_number > self.current_lap:
                    # New lap started
                    completed_lap = self._finalize_current_lap(now)
                    self._start_new_lap(lap_number, now)
                    return completed_lap
                else:
                    # Session reset
                    logger.info(f"🔄 Session reset detected")
                    self._reset_timing(lap_number, now)
            
            # Initialize timing on first telemetry
            if self.sector_start_time == 0.0:
                self.sector_start_time = now
                self.lap_start_time = now
                self.current_sector = self._get_current_sector(lap_dist_pct)
                logger.info(f"🏁 Simple timing started in sector {self.current_sector + 1}")
                self.prev_lap_dist_pct = lap_dist_pct
                return None
            
            # Check for sector boundary crossings
            expected_sector = self._get_current_sector(lap_dist_pct)
            
            if expected_sector != self.current_sector:
                # We crossed into a new sector!
                sector_time = now - self.sector_start_time
                
                logger.info(f"🏁 SIMPLE S{self.current_sector + 1}: {sector_time:.3f}s (lap {self.current_lap})")
                
                # Store the sector time
                self.current_lap_sectors.append(sector_time)
                
                # Update best sector time
                if (self.best_sector_times[self.current_sector] is None or 
                    sector_time < self.best_sector_times[self.current_sector]):
                    self.best_sector_times[self.current_sector] = sector_time
                    logger.info(f"✨ New best S{self.current_sector + 1}: {sector_time:.3f}s")
                
                # Move to new sector
                self.current_sector = expected_sector
                self.sector_start_time = now
                
                # Check if we completed a lap
                if self.current_sector == 0 and len(self.current_lap_sectors) == len(self.sectors):
                    return self._finalize_current_lap(now)
            
            # Update previous values
            self.prev_lap_dist_pct = lap_dist_pct
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in simple sector timing: {e}")
            return None
    
    def _get_current_sector(self, lap_dist_pct: float) -> int:
        """Determine which sector we're currently in."""
        # Handle wrap-around
        if lap_dist_pct >= 0.99:
            return len(self.sectors) - 1
        
        for i in range(len(self.sectors)):
            sector_start = self.sectors[i].start_pct
            
            if i == len(self.sectors) - 1:
                sector_end = 1.0
            else:
                sector_end = self.sectors[i + 1].start_pct
            
            if sector_start <= lap_dist_pct < sector_end:
                return i
        
        return 0
    
    def _finalize_current_lap(self, now: float) -> Optional[SimpleLapTimes]:
        """Finalize the current lap and return results."""
        if not self.current_lap_sectors:
            return None
        
        try:
            total_time = sum(self.current_lap_sectors)
            
            lap_times = SimpleLapTimes(
                lap_number=self.current_lap,
                sector_times=self.current_lap_sectors.copy(),
                total_time=total_time,
                is_complete=len(self.current_lap_sectors) == len(self.sectors)
            )
            
            # Update best lap time
            if lap_times.is_complete and (self.best_lap_time is None or total_time < self.best_lap_time):
                self.best_lap_time = total_time
                logger.info(f"✨ New best lap: {total_time:.3f}s")
            
            # Log completion
            sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(self.current_lap_sectors)])
            status = "COMPLETE" if lap_times.is_complete else "PARTIAL"
            logger.info(f"🏁 SIMPLE {status} Lap {self.current_lap}: {sector_str}  LAP {total_time:.3f}s")
            
            self.completed_laps.append(lap_times)
            return lap_times
            
        except Exception as e:
            logger.error(f"❌ Error finalizing lap: {e}")
            return None
    
    def _start_new_lap(self, lap_number: int, now: float):
        """Start timing a new lap."""
        self.current_lap = lap_number
        self.current_lap_sectors = []
        self.current_sector = 0
        self.sector_start_time = now
        self.lap_start_time = now
        logger.info(f"🚀 Started timing lap {lap_number}")
    
    def _reset_timing(self, lap_number: int, now: float):
        """Reset all timing state."""
        self.current_lap = lap_number
        self.current_lap_sectors = []
        self.current_sector = 0
        self.sector_start_time = now
        self.lap_start_time = now
        self.prev_lap_dist_pct = 0.0
        logger.info(f"🔄 Timing reset for lap {lap_number}")
    
    def get_current_progress(self) -> Dict:
        """Get current timing progress."""
        if not self.is_initialized:
            return {
                'initialized': False,
                'current_sector': 0,
                'total_sectors': 0,
                'current_sector_time': 0.0
            }
        
        current_sector_time = 0.0
        if self.sector_start_time > 0:
            current_sector_time = time.time() - self.sector_start_time
        
        return {
            'initialized': True,
            'current_sector': self.current_sector + 1,
            'total_sectors': len(self.sectors),
            'current_sector_time': current_sector_time,
            'completed_sectors': len(self.current_lap_sectors),
            'current_lap_splits': self.current_lap_sectors.copy(),
            'best_sector_times': self.best_sector_times.copy(),
            'best_lap_time': self.best_lap_time,
            'timing_method': 'simple_own_timer'
        }
    
    def get_recent_laps(self, count: int = 5) -> List[SimpleLapTimes]:
        """Get recent completed laps."""
        return self.completed_laps[-count:] if self.completed_laps else [] 