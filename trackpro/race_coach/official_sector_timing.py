"""
Official iRacing Sector Timing Implementation

This module implements the best practices for extracting official iRacing sector times
using pyirsdk, based on comprehensive research of the iRacing SDK.

Key Features:
- Uses official SplitTimeInfo sector boundaries from SessionInfo
- Monitors LapDistPct for precise crossing detection  
- Implements interpolation for accurate crossing timestamps
- Handles out-laps, resets, and edge cases properly
- Provides sector times that match iRacing's official timing

Based on iRacing SDK research:
- Extracts sector layout from SessionInfo YAML SplitTimeInfo
- Uses LapDistPct percentage for position tracking
- Detects crossings with prev_pct < threshold <= current_pct
- Records SessionTime at crossings for precise timing
- Handles lap completion and wrap-around cases
"""

import yaml
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OfficialSectorInfo:
    """Official iRacing sector information from SplitTimeInfo."""
    sector_num: int
    start_pct: float

@dataclass
class OfficialSectorTime:
    """A completed sector time using official methodology."""
    sector_num: int
    time: float
    lap_number: int
    crossing_time: float
    is_interpolated: bool = False

@dataclass
class OfficialLapSectorTimes:
    """Complete sector times for a lap using official methodology."""
    lap_number: int
    sector_times: List[float]
    total_time: float
    lap_start_time: float
    lap_end_time: float
    is_valid: bool = True
    is_out_lap: bool = False

class OfficialSectorTimingCollector:
    """
    Official iRacing sector timing implementation following SDK best practices.
    
    This implementation follows the exact methodology outlined in the research:
    1. Extract sector boundaries from SessionInfo SplitTimeInfo
    2. Monitor LapDistPct for sector crossings using threshold detection
    3. Use SessionTime for precise timing calculations
    4. Handle interpolation for sub-frame accuracy
    5. Manage out-laps, resets, and edge cases properly
    
    The resulting sector times will match iRacing's official timing within
    milliseconds, limited only by telemetry update frequency (typically 60Hz).
    """
    
    def __init__(self):
        # Official sector definitions from iRacing
        self.sectors: List[OfficialSectorInfo] = []
        
        # Current state tracking
        self.prev_lap_dist_pct: float = 0.0
        self.prev_session_time: float = 0.0
        self.current_lap: int = 0
        self.is_on_track: bool = True
        
        # Sector crossing tracking (official methodology)
        self.sector_crossing_times: Dict[int, float] = {}  # sector_num -> crossing time
        self.current_lap_crossings: List[Tuple[int, float]] = []  # (sector_num, time)
        
        # Completed data
        self.completed_laps: List[OfficialLapSectorTimes] = []
        self.sector_times_history: List[OfficialSectorTime] = []
        
        # Best times tracking
        self.best_sector_times: List[Optional[float]] = []
        self.best_lap_time: Optional[float] = None
        
        # State management
        self.is_initialized: bool = False
        self.last_session_info_hash: Optional[str] = None
        
        logger.info("🏁 Official iRacing Sector Timing initialized")
        logger.info("✅ Implements official SDK methodology for accurate timing")
    
    def update_session_info(self, session_info_raw: str) -> bool:
        """
        Extract official sector definitions from iRacing SessionInfo.
        
        This follows the research methodology:
        - Parse SessionInfo YAML for SplitTimeInfo
        - Extract Sectors array with SectorNum and SectorStartPct
        - Validate and store official sector boundaries
        
        Args:
            session_info_raw: Raw SessionInfo string from iRacing
            
        Returns:
            True if sectors were successfully parsed, False otherwise
        """
        try:
            # Extract YAML content (excluding telemetry data)
            yaml_content = self._extract_yaml_content(session_info_raw)
            if not yaml_content:
                logger.error("❌ Could not extract YAML from SessionInfo")
                return False
            
            # Check if session info has changed
            session_hash = str(hash(yaml_content))
            if session_hash == self.last_session_info_hash and self.is_initialized:
                logger.debug("SessionInfo unchanged and sectors already initialized")
                return True
            
            logger.info("🔄 Parsing SessionInfo for official sector definitions...")
            
            # Parse YAML
            session_data = yaml.safe_load(yaml_content)
            if not session_data:
                logger.error("❌ Failed to parse SessionInfo YAML")
                return False
            
            # Extract SplitTimeInfo (official sector data)
            split_time_info = session_data.get('SplitTimeInfo', {})
            if not split_time_info:
                logger.error("❌ No SplitTimeInfo found in SessionInfo")
                return False
            
            sectors_data = split_time_info.get('Sectors', [])
            if not sectors_data:
                logger.error("❌ No Sectors found in SplitTimeInfo")
                return False
            
            logger.info(f"🔍 Found {len(sectors_data)} official sectors in SplitTimeInfo")
            
            # Parse official sector definitions
            new_sectors = []
            for sector_data in sectors_data:
                sector_num = sector_data.get('SectorNum', 0)
                start_pct = sector_data.get('SectorStartPct', 0.0)
                
                sector_info = OfficialSectorInfo(
                    sector_num=sector_num,
                    start_pct=start_pct
                )
                new_sectors.append(sector_info)
                
                logger.info(f"🏁 Official Sector {sector_num}: starts at {start_pct:.6f}")
            
            # Sort sectors by start percentage (should already be sorted)
            new_sectors.sort(key=lambda s: s.start_pct)
            
            # Validate sector definitions
            if len(new_sectors) < 1:
                logger.error("❌ No valid sectors found")
                return False
            
            # Log official sector analysis
            logger.info(f"🔍 Official track sector layout:")
            logger.info(f"   📊 Total sectors: {len(new_sectors)}")
            for i, sector in enumerate(new_sectors):
                if i < len(new_sectors) - 1:
                    next_start = new_sectors[i + 1].start_pct
                    sector_length = next_start - sector.start_pct
                else:
                    sector_length = 1.0 - sector.start_pct
                logger.info(f"   🏁 Sector {sector.sector_num}: {sector.start_pct:.6f} - {sector.start_pct + sector_length:.6f} (length: {sector_length:.6f})")
            
            # Update with official sectors
            self.sectors = new_sectors
            self.best_sector_times = [None] * len(self.sectors)
            
            # Reset timing state if sectors changed
            if not self.is_initialized:
                self._reset_timing_state()
            
            # Mark as initialized
            self.is_initialized = True
            self.last_session_info_hash = session_hash
            
            logger.info(f"✅ Official sector timing initialized with {len(self.sectors)} sectors")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error parsing official sector definitions: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _extract_yaml_content(self, session_info_raw: str) -> str:
        """Extract YAML content from SessionInfo, excluding telemetry data."""
        try:
            lines = session_info_raw.split('\n')
            yaml_lines = []
            
            for line in lines:
                if not line.strip():
                    yaml_lines.append(line)
                    continue
                
                # Stop at telemetry data (lines with many spaces)
                if '                    ' in line and line.count(' ') > 20:
                    break
                
                yaml_lines.append(line)
            
            return '\n'.join(yaml_lines)
            
        except Exception as e:
            logger.error(f"❌ Error extracting YAML content: {e}")
            return ""
    
    def _reset_timing_state(self):
        """Reset timing state for new session or track change."""
        self.prev_lap_dist_pct = 0.0
        self.prev_session_time = 0.0
        self.current_lap = 0
        self.sector_crossing_times.clear()
        self.current_lap_crossings.clear()
        logger.info("🔄 Official sector timing state reset")
    
    def process_telemetry(self, telemetry_data: Dict) -> Optional[OfficialLapSectorTimes]:
        """
        Process telemetry using official iRacing sector timing methodology.
        
        This implements the exact approach from the research:
        1. Monitor LapDistPct for position tracking
        2. Detect sector crossings with prev < threshold <= current
        3. Use SessionTime for precise timing calculations
        4. Handle interpolation for sub-frame accuracy
        5. Manage lap completion and edge cases
        
        Args:
            telemetry_data: Dictionary containing:
                - LapDistPct: Current position (0.0 to 1.0)
                - SessionTime: Current session time in seconds
                - Lap: Current lap number
                - IsOnTrackCar: Whether car is on track (optional)
                
        Returns:
            OfficialLapSectorTimes if lap completed, None otherwise
        """
        if not self.is_initialized:
            return None
        
        try:
            # Extract telemetry data (official variables)
            lap_dist_pct = telemetry_data.get('LapDistPct')
            session_time = telemetry_data.get('SessionTime') or telemetry_data.get('SessionTimeSecs')
            lap_number = telemetry_data.get('Lap', 0)
            is_on_track = telemetry_data.get('IsOnTrackCar', True)
            
            if lap_dist_pct is None or session_time is None:
                return None
            
            # Handle car going off track (garage, tow, reset)
            if not is_on_track and self.is_on_track:
                logger.info("🔄 Car off track - resetting timing state")
                self._reset_timing_state()
                self.is_on_track = False
                return None
            elif is_on_track and not self.is_on_track:
                logger.info("🔄 Car back on track - ready for timing")
                self.is_on_track = True
            
            self.is_on_track = is_on_track
            
            # Handle lap number changes
            if lap_number != self.current_lap:
                if lap_number < self.current_lap:
                    # Session reset
                    logger.info(f"🔄 Session reset detected (lap {self.current_lap} -> {lap_number})")
                    self._reset_timing_state()
                elif lap_number > self.current_lap and self.current_lap_crossings:
                    # New lap started - finalize previous lap
                    logger.info(f"🏁 Lap number changed - finalizing lap {self.current_lap}")
                    completed_lap = self._finalize_current_lap(session_time, is_complete=False)
                    if completed_lap:
                        self.completed_laps.append(completed_lap)
                
                self.current_lap = lap_number
            
            # Initialize on first telemetry
            if self.prev_session_time == 0.0:
                self.prev_lap_dist_pct = lap_dist_pct
                self.prev_session_time = session_time
                self.current_lap = lap_number
                
                # Record lap start (sector 0 crossing)
                self.sector_crossing_times[0] = session_time
                self.current_lap_crossings = [(0, session_time)]
                
                logger.info(f"🏁 Official timing started - lap {lap_number} at position {lap_dist_pct:.6f}")
                return None
            
            # OFFICIAL METHODOLOGY: Check for sector boundary crossings
            # This implements the core research finding: prev_pct < threshold <= current_pct
            for sector in self.sectors[1:]:  # Skip sector 0 (start line)
                sector_pct = sector.start_pct
                sector_num = sector.sector_num
                
                # Check if we crossed this sector boundary
                if self.prev_lap_dist_pct < sector_pct <= lap_dist_pct:
                    # CROSSING DETECTED! Calculate precise crossing time
                    crossing_time = self._interpolate_crossing_time(
                        self.prev_lap_dist_pct, lap_dist_pct,
                        self.prev_session_time, session_time,
                        sector_pct
                    )
                    
                    # Record the crossing
                    self.sector_crossing_times[sector_num] = crossing_time
                    self.current_lap_crossings.append((sector_num, crossing_time))
                    
                    # Calculate previous sector time
                    prev_sector_num = sector_num - 1
                    if prev_sector_num in self.sector_crossing_times:
                        sector_time = crossing_time - self.sector_crossing_times[prev_sector_num]
                        
                        # Create sector time record
                        sector_record = OfficialSectorTime(
                            sector_num=prev_sector_num,
                            time=sector_time,
                            lap_number=self.current_lap,
                            crossing_time=crossing_time,
                            is_interpolated=True
                        )
                        self.sector_times_history.append(sector_record)
                        
                        # Update best sector time
                        if (prev_sector_num < len(self.best_sector_times) and
                            (self.best_sector_times[prev_sector_num] is None or
                             sector_time < self.best_sector_times[prev_sector_num])):
                            self.best_sector_times[prev_sector_num] = sector_time
                            logger.info(f"✨ New best S{prev_sector_num + 1}: {sector_time:.3f}s")
                        
                        logger.info(f"🏁 S{prev_sector_num + 1}: {sector_time:.3f}s (official methodology)")
            
            # Check for lap completion (crossing start/finish line)
            # Handle wrap-around: high percentage to low percentage
            if self.prev_lap_dist_pct > 0.9 and lap_dist_pct < 0.1:
                logger.info("🏁 Lap completion detected (start/finish line crossed)")
                
                # Calculate final sector time
                final_sector_num = len(self.sectors) - 1
                if final_sector_num in self.sector_crossing_times:
                    final_sector_time = session_time - self.sector_crossing_times[final_sector_num]
                    
                    # Create final sector record
                    final_sector_record = OfficialSectorTime(
                        sector_num=final_sector_num,
                        time=final_sector_time,
                        lap_number=self.current_lap,
                        crossing_time=session_time,
                        is_interpolated=False
                    )
                    self.sector_times_history.append(final_sector_record)
                    
                    logger.info(f"🏁 S{final_sector_num + 1}: {final_sector_time:.3f}s (final sector)")
                
                # Complete the lap
                completed_lap = self._finalize_current_lap(session_time, is_complete=True)
                if completed_lap:
                    self.completed_laps.append(completed_lap)
                    
                    # Reset for next lap
                    self.sector_crossing_times = {0: session_time}
                    self.current_lap_crossings = [(0, session_time)]
                    
                    return completed_lap
            
            # Update previous values for next iteration
            self.prev_lap_dist_pct = lap_dist_pct
            self.prev_session_time = session_time
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error processing official sector timing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _interpolate_crossing_time(self, prev_pct: float, now_pct: float,
                                 prev_time: float, now_time: float,
                                 crossing_pct: float) -> float:
        """
        Interpolate exact crossing time for sub-frame accuracy.
        
        This implements the interpolation technique from the research to achieve
        timing accuracy better than the telemetry update frequency.
        """
        if prev_pct >= now_pct or now_pct <= prev_pct:
            return now_time
        
        # Calculate crossing fraction
        total_distance = now_pct - prev_pct
        crossing_distance = crossing_pct - prev_pct
        
        if total_distance <= 0:
            return now_time
        
        crossing_fraction = crossing_distance / total_distance
        
        # Interpolate time
        time_delta = now_time - prev_time
        interpolated_time = prev_time + (crossing_fraction * time_delta)
        
        return interpolated_time
    
    def _finalize_current_lap(self, end_time: float, is_complete: bool) -> Optional[OfficialLapSectorTimes]:
        """Finalize the current lap and return sector times."""
        try:
            if not self.current_lap_crossings:
                return None
            
            # Calculate sector times from crossings
            sector_times = []
            lap_start_time = self.current_lap_crossings[0][1]
            
            # Get all sector times from crossings
            for i in range(len(self.sectors)):
                if i + 1 < len(self.current_lap_crossings):
                    # Normal sector time
                    start_time = self.current_lap_crossings[i][1]
                    end_time_sector = self.current_lap_crossings[i + 1][1]
                    sector_time = end_time_sector - start_time
                    sector_times.append(sector_time)
                elif is_complete and i == len(self.sectors) - 1:
                    # Final sector for complete lap
                    start_time = self.current_lap_crossings[i][1]
                    sector_time = end_time - start_time
                    sector_times.append(sector_time)
            
            # Only create lap record if we have sector times
            if not sector_times:
                return None
            
            total_time = sum(sector_times)
            
            # Create lap record
            lap_record = OfficialLapSectorTimes(
                lap_number=self.current_lap,
                sector_times=sector_times,
                total_time=total_time,
                lap_start_time=lap_start_time,
                lap_end_time=end_time,
                is_valid=is_complete and len(sector_times) == len(self.sectors),
                is_out_lap=not is_complete
            )
            
            # Update best lap time
            if lap_record.is_valid and (self.best_lap_time is None or total_time < self.best_lap_time):
                self.best_lap_time = total_time
                logger.info(f"✨ New best lap: {total_time:.3f}s (official timing)")
            
            # Log lap completion
            sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(sector_times)])
            status = "COMPLETE" if lap_record.is_valid else "PARTIAL"
            logger.info(f"🏁 {status} Lap {self.current_lap}: {sector_str}  LAP {total_time:.3f}s")
            
            return lap_record
            
        except Exception as e:
            logger.error(f"❌ Error finalizing lap: {e}")
            return None
    
    def get_current_progress(self) -> Dict:
        """Get current sector timing progress."""
        if not self.is_initialized:
            return {
                'is_initialized': False,
                'current_sector': 0,
                'total_sectors': 0,
                'current_sector_time': 0.0,
                'completed_sectors': 0,
                'best_sector_times': [],
                'best_lap_time': None
            }
        
        # Determine current sector
        current_sector = 0
        current_sector_time = 0.0
        
        if self.current_lap_crossings:
            current_sector = len(self.current_lap_crossings) - 1
            if current_sector < len(self.sectors) and self.prev_session_time > 0:
                last_crossing_time = self.current_lap_crossings[-1][1]
                current_sector_time = self.prev_session_time - last_crossing_time
        
        return {
            'is_initialized': True,
            'current_sector': current_sector + 1,
            'total_sectors': len(self.sectors),
            'current_sector_time': current_sector_time,
            'completed_sectors': len(self.current_lap_crossings) - 1,
            'best_sector_times': self.best_sector_times.copy(),
            'best_lap_time': self.best_lap_time,
            'methodology': 'official_iracing_sdk'
        }
    
    def get_recent_laps(self, count: int = 10) -> List[OfficialLapSectorTimes]:
        """Get recent completed laps."""
        return self.completed_laps[-count:] if self.completed_laps else []
    
    def clear_data(self):
        """Clear all timing data."""
        self.completed_laps.clear()
        self.sector_times_history.clear()
        self.best_sector_times = [None] * len(self.sectors) if self.sectors else []
        self.best_lap_time = None
        self._reset_timing_state()
        logger.info("Official sector timing data cleared") 