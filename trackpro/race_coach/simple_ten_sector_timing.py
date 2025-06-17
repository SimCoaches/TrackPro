"""
Simple 10-Sector Timing for TrackPro

This module implements a simple sector timing system that divides every track into 10 equal sectors:
- Sector 1: 0.0 - 0.1
- Sector 2: 0.1 - 0.2
- Sector 3: 0.2 - 0.3
- ...
- Sector 10: 0.9 - 1.0

This provides consistent sector timing across all tracks for easy comparison and superlap creation.
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TenSectorTime:
    """A completed sector time with timing data."""
    sector_number: int  # 1-10
    sector_time: float  # Duration in seconds
    lap_number: int
    start_time: float   # Timestamp when sector started
    end_time: float     # Timestamp when sector ended

@dataclass
class TenSectorLapTimes:
    """Complete lap with 10 sector times."""
    lap_number: int
    sector_times: List[float]  # 10 sector times in seconds
    total_time: float
    timestamp: float
    is_complete: bool
    is_valid: bool

class SimpleTenSectorTiming:
    """
    Simple, consistent 10-sector timing system.
    
    Divides every track into 10 equal sectors based on LapDist:
    - Uses time.time() for reliable timing
    - Watches LapDist (track_position) for sector boundary crossings
    - Provides consistent sector comparison across all tracks
    - Perfect for superlap creation and performance analysis
    """
    
    def __init__(self):
        # 10 equal sectors from 0.0 to 1.0
        self.sector_boundaries = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        self.num_sectors = 10
        
        # Current timing state
        self.current_sector = 0  # 0-9 (sector 1-10)
        self.current_lap = 0
        self.sector_start_time = 0.0  # Timestamp when current sector started
        self.lap_start_time = 0.0
        
        # Current lap data
        self.current_lap_sector_times: List[float] = []
        self.current_lap_sector_records: List[TenSectorTime] = []
        
        # Completed data
        self.completed_laps: List[TenSectorLapTimes] = []
        self.best_sector_times: List[Optional[float]] = [None] * self.num_sectors
        self.best_lap_time: Optional[float] = None
        
        # Previous telemetry for crossing detection
        self.prev_track_position = 0.0
        self.prev_lap_number = 0
        
        # State tracking
        self.is_initialized = True  # Always ready
        self.first_telemetry = True
        
        logger.info("🔧 Simple 10-Sector Timing initialized")
        logger.info("📊 Using 10 equal sectors: S1(0.0-0.1), S2(0.1-0.2), ..., S10(0.9-1.0)")
    
    def get_sector_for_position(self, track_position: float) -> int:
        """
        Get the sector number (0-9) for a given track position.
        
        Args:
            track_position: Track position from 0.0 to 1.0
            
        Returns:
            Sector index from 0-9 (representing sectors 1-10)
        """
        # Clamp position to valid range
        track_position = max(0.0, min(0.999999, track_position))
        
        # Calculate sector (0-9)
        sector = int(track_position * 10)
        return min(sector, 9)  # Ensure we don't exceed sector 9
    
    def get_sector_boundaries(self) -> List[Tuple[float, float]]:
        """
        Get the start and end positions for each sector.
        
        Returns:
            List of (start, end) tuples for each sector
        """
        boundaries = []
        for i in range(self.num_sectors):
            start = i * 0.1
            end = (i + 1) * 0.1 if i < 9 else 1.0
            boundaries.append((start, end))
        return boundaries
    
    def process_telemetry(self, telemetry_data: Dict) -> Optional[TenSectorLapTimes]:
        """
        Process telemetry data using position-based lap detection (independent of lap number delays).
        
        Args:
            telemetry_data: Dict containing at least:
                - LapDistPct: Current track position (0.0 to 1.0)
                - Lap: Current lap number (for reference only)
        
        Returns:
            TenSectorLapTimes if a lap was completed, None otherwise
        """
        try:
            # Get current time using our own timer
            now = time.time()
            
            # Extract telemetry
            track_position = telemetry_data.get('LapDistPct')
            lap_number = telemetry_data.get('Lap', 0)  # Reference only, not used for timing decisions
            
            if track_position is None:
                return None
            
            # Initialize timing on first telemetry
            if self.first_telemetry:
                self.sector_start_time = now
                self.lap_start_time = now
                self.current_sector = self.get_sector_for_position(track_position)
                self.current_lap = lap_number  # Set initial lap number
                logger.info(f"🏁 10-Sector timing started in sector {self.current_sector + 1} at position {track_position:.6f}")
                logger.info(f"🔍 [INIT DEBUG] LapDistPct={telemetry_data.get('LapDistPct')}, track_position={track_position}, calculated_sector={self.current_sector + 1}")
                self.prev_track_position = track_position
                self.first_telemetry = False
                return None
            
            # PRIORITY 1: Handle wrap-around at finish line (IMMEDIATE lap boundary detection)
            # This happens BEFORE normal sector crossing detection to ensure proper timing
            if self.prev_track_position > 0.9 and track_position < 0.1:
                logger.info(f"🏁 [LAP BOUNDARY] Finish line crossed! Position: {self.prev_track_position:.6f} → {track_position:.6f}")
                
                # Complete the current sector (final sector of the lap)
                if self.sector_start_time > 0:
                    sector_time = now - self.sector_start_time
                    self._complete_current_sector(sector_time, now)
                    logger.info(f"🏁 [FINAL SECTOR] Completed final sector: {sector_time:.3f}s")
                
                # Complete the lap if we have all 10 sectors
                completed_lap = None
                if len(self.current_lap_sector_times) == self.num_sectors:
                    completed_lap = self._finalize_current_lap(now)
                    logger.info(f"🏁 [LAP COMPLETE] Finalized lap {self.current_lap} with {self.num_sectors} sectors")
                else:
                    logger.warning(f"⚠️ [LAP INCOMPLETE] Lap {self.current_lap} only has {len(self.current_lap_sector_times)}/{self.num_sectors} sectors")
                
                # IMMEDIATELY start new lap timing (no delay!)
                # Use the telemetry lap number instead of incrementing our own counter
                new_lap_number = lap_number  # Use iRacing's actual lap number
                self._start_new_lap_immediate(new_lap_number, now, track_position)
                logger.info(f"🚀 [IMMEDIATE START] Started timing lap {new_lap_number} immediately at position {track_position:.6f}")
                logger.info(f"🔧 [LAP NUMBER FIX] Using iRacing lap number {new_lap_number} instead of incrementing counter")
                
                # Update previous position and return completed lap
                self.prev_track_position = track_position
                return completed_lap
            
            # PRIORITY 2: Handle session resets (lap number goes backwards)
            if lap_number < self.current_lap and lap_number >= 0:
                logger.info(f"🔄 [SESSION RESET] Lap number decreased: {self.current_lap} → {lap_number}")
                self._reset_timing_immediate(lap_number, now, track_position)
                self.prev_track_position = track_position
                return None
            
            # PRIORITY 3: Check for normal sector crossings
            expected_sector = self.get_sector_for_position(track_position)
            
            if expected_sector != self.current_sector:
                # We crossed into a new sector!
                sector_time = now - self.sector_start_time
                self._complete_current_sector(sector_time, now)
                
                # Move to new sector
                self.current_sector = expected_sector
                self.sector_start_time = now
                logger.info(f"🚀 [SECTOR CHANGE] Moved to sector {self.current_sector + 1} at position {track_position:.6f}")
            
            # Update previous values
            self.prev_track_position = track_position
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in 10-sector timing: {e}")
            return None
    
    def _complete_current_sector(self, sector_time: float, end_time: float):
        """Complete the current sector and record its time."""
        try:
            sector_num = self.current_sector + 1  # 1-10 for display
            
            logger.info(f"🏁 10-SECTOR S{sector_num}: {sector_time:.3f}s (lap {self.current_lap})")
            
            # Store the sector time
            self.current_lap_sector_times.append(sector_time)
            
            # Create sector record
            sector_record = TenSectorTime(
                sector_number=sector_num,
                sector_time=sector_time,
                lap_number=self.current_lap,
                start_time=self.sector_start_time,
                end_time=end_time
            )
            self.current_lap_sector_records.append(sector_record)
            
            # Update best sector time
            sector_index = self.current_sector
            if (self.best_sector_times[sector_index] is None or 
                sector_time < self.best_sector_times[sector_index]):
                self.best_sector_times[sector_index] = sector_time
                logger.info(f"✨ New best S{sector_num}: {sector_time:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Error completing sector: {e}")
    
    def _finalize_current_lap(self, now: float) -> Optional[TenSectorLapTimes]:
        """Finalize the current lap and return results."""
        if not self.current_lap_sector_times:
            return None
        
        try:
            total_time = sum(self.current_lap_sector_times)
            is_complete = len(self.current_lap_sector_times) == self.num_sectors
            
            lap_times = TenSectorLapTimes(
                lap_number=self.current_lap,
                sector_times=self.current_lap_sector_times.copy(),
                total_time=total_time,
                timestamp=now,
                is_complete=is_complete,
                is_valid=is_complete and total_time > 10.0  # Basic validation
            )
            
            # Update best lap time
            if lap_times.is_valid and (self.best_lap_time is None or total_time < self.best_lap_time):
                self.best_lap_time = total_time
                logger.info(f"✨ New best lap: {total_time:.3f}s")
            
            # Log completion
            sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(self.current_lap_sector_times)])
            status = "COMPLETE" if is_complete else f"PARTIAL({len(self.current_lap_sector_times)}/10)"
            logger.info(f"🏁 10-SECTOR {status} Lap {self.current_lap}: {sector_str}  LAP {total_time:.3f}s")
            
            self.completed_laps.append(lap_times)
            return lap_times
            
        except Exception as e:
            logger.error(f"❌ Error finalizing lap: {e}")
            return None
    
    def _start_new_lap(self, lap_number: int, now: float, track_position: float):
        """Start timing a new lap."""
        self.current_lap = lap_number
        self.current_lap_sector_times = []
        self.current_lap_sector_records = []
        self.current_sector = self.get_sector_for_position(track_position)
        self.sector_start_time = now
        self.lap_start_time = now
        logger.info(f"🚀 Started timing 10-sector lap {lap_number}")
    
    def _start_new_lap_immediate(self, lap_number: int, now: float, track_position: float):
        """
        Start timing a new lap immediately (used for position-based lap detection).
        
        This method starts sector timing immediately when a lap boundary is crossed,
        independent of any lap processing delays from the lap indexer.
        """
        self.current_lap = lap_number  # Use the actual iRacing lap number
        self.current_lap_sector_times = []
        self.current_lap_sector_records = []
        
        # Always start in sector 1 (index 0) for new laps at the start/finish line
        self.current_sector = 0
        self.sector_start_time = now
        self.lap_start_time = now
        
        logger.info(f"🚀 [IMMEDIATE] Started timing lap {lap_number} in sector 1 at position {track_position:.6f}")
        logger.info(f"⚡ [SECTOR TIMING FIX] No 3-second delay - timing starts immediately!")
        logger.info(f"🔧 [LAP NUMBER SYNC] Current lap set to iRacing lap number: {lap_number}")
    
    def _reset_timing(self, lap_number: int, now: float, track_position: float):
        """Reset all timing state."""
        self.current_lap = lap_number
        self.current_lap_sector_times = []
        self.current_lap_sector_records = []
        self.current_sector = self.get_sector_for_position(track_position)
        self.sector_start_time = now
        self.lap_start_time = now
        self.prev_track_position = track_position
        logger.info(f"🔄 10-sector timing reset for lap {lap_number}")
    
    def _reset_timing_immediate(self, lap_number: int, now: float, track_position: float):
        """
        Reset all timing state immediately (used for session resets).
        
        This method resets timing state immediately when a session reset is detected,
        ensuring clean state for the new session.
        """
        self.current_lap = lap_number
        self.current_lap_sector_times = []
        self.current_lap_sector_records = []
        self.current_sector = self.get_sector_for_position(track_position)
        self.sector_start_time = now
        self.lap_start_time = now
        self.prev_track_position = track_position
        
        logger.info(f"🔄 [IMMEDIATE RESET] Timing reset for lap {lap_number} at position {track_position:.6f}")
        logger.info(f"⚡ [SESSION RESET] Clean timing state established")
    
    def get_current_progress(self) -> Dict:
        """Get current timing progress."""
        current_sector_time = 0.0
        if self.sector_start_time > 0:
            current_sector_time = time.time() - self.sector_start_time
        
        return {
            'initialized': True,
            'current_sector': self.current_sector + 1,  # 1-10
            'total_sectors': self.num_sectors,
            'current_sector_time': current_sector_time,
            'completed_sectors': len(self.current_lap_sector_times),
            'current_lap_splits': self.current_lap_sector_times.copy(),
            'best_sector_times': self.best_sector_times.copy(),
            'best_lap_time': self.best_lap_time,
            'timing_method': '10_equal_sectors',
            'sector_boundaries': self.get_sector_boundaries()
        }
    
    def get_recent_laps(self, count: int = 5) -> List[TenSectorLapTimes]:
        """Get recent completed laps."""
        return self.completed_laps[-count:] if self.completed_laps else []
    
    def get_best_sector_times(self) -> List[Optional[float]]:
        """Get best times for each sector."""
        return self.best_sector_times.copy()
    
    def get_sector_comparison(self, lap_times: TenSectorLapTimes) -> Dict:
        """
        Compare lap sector times against best sector times.
        
        Args:
            lap_times: Completed lap to compare
            
        Returns:
            Dictionary with sector comparison data
        """
        comparison = {
            'lap_number': lap_times.lap_number,
            'sectors': [],
            'total_delta': 0.0,
            'is_theoretical_best': True
        }
        
        total_delta = 0.0
        
        for i, sector_time in enumerate(lap_times.sector_times):
            best_time = self.best_sector_times[i]
            
            if best_time is not None:
                delta = sector_time - best_time
                total_delta += delta
                is_best = delta <= 0.001  # Within 1ms
            else:
                delta = 0.0
                is_best = True
            
            comparison['sectors'].append({
                'sector_number': i + 1,
                'time': sector_time,
                'best_time': best_time,
                'delta': delta,
                'is_personal_best': is_best
            })
            
            if not is_best:
                comparison['is_theoretical_best'] = False
        
        comparison['total_delta'] = total_delta
        
        return comparison
    
    def create_theoretical_best_lap(self) -> Optional[TenSectorLapTimes]:
        """
        Create a theoretical best lap using the best time from each sector.
        
        Returns:
            TenSectorLapTimes representing the theoretical best lap, or None if no data
        """
        if not any(time is not None for time in self.best_sector_times):
            return None
        
        # Use best times, fallback to 0.0 for missing sectors
        best_times = [time if time is not None else 0.0 for time in self.best_sector_times]
        total_time = sum(best_times)
        
        return TenSectorLapTimes(
            lap_number=-1,  # Special lap number for theoretical best
            sector_times=best_times,
            total_time=total_time,
            timestamp=time.time(),
            is_complete=True,
            is_valid=True
        )
    
    def clear_data(self):
        """Clear all timing data."""
        self.completed_laps = []
        self.best_sector_times = [None] * self.num_sectors
        self.best_lap_time = None
        self.current_lap_sector_times = []
        self.current_lap_sector_records = []
        logger.info("🔄 10-sector timing data cleared") 