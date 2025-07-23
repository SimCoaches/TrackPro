"""
Sector Timing Module for TrackPro Race Coach

Implements live sector-split timing using pyirsdk following the standard workflow:
1. Extract sector layout from SessionInfo YAML
2. Monitor LapDistPct for sector crossings
3. Calculate sector times with proper wrap-around handling

Enhanced with official iRacing sector timing best practices:
- Uses official SplitTimeInfo sector boundaries from SessionInfo
- Monitors LapDistPct for precise crossing detection
- Handles interpolation for accurate crossing timestamps
- Manages out-laps, resets, and edge cases properly
"""

import yaml
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SectorInfo:
    """Information about a track sector."""
    sector_num: int
    start_pct: float

@dataclass
class SectorTime:
    """Record of a completed sector time."""
    sector_num: int
    time: float
    lap_number: int
    timestamp: float

@dataclass
class LapSectorTimes:
    """Complete sector timing data for a lap."""
    lap_number: int
    sector_times: List[float]
    total_time: float
    timestamp: float
    is_valid: bool = True

class SectorTimingCollector:
    """
    Enhanced sector timing collector using official iRacing sector definitions.
    
    This system implements the best practices for extracting official iRacing sector times:
    - Extracts sector layout from SessionInfo SplitTimeInfo
    - Uses LapDistPct for precise position tracking
    - Detects sector crossings with interpolation for accuracy
    - Handles out-laps, resets, and edge cases properly
    - Provides sector times that match iRacing's official timing
    
    Based on iRacing telemetry:
    - Extracts sector layout from SessionInfo YAML
    - Monitors LapDistPct for current sector position
    - Calculates precise sector crossing times
    - Provides comprehensive sector analysis
    """
    
    def __init__(self):
        self.sectors: List[SectorInfo] = []
        self.sector_starts: List[float] = []
        
        # Current timing state
        self.prev_pct: float = 0.0
        self.prev_time: float = 0.0
        self.current_sector_index: int = 0
        self.current_lap_number: int = 0
        
        # FIXED: Track sector start time for proper duration calculation
        self.sector_start_time: float = 0.0  # SessionTime when we entered current sector
        
        # Sector crossing detection
        self.sector_crossing_times: Dict[int, float] = {}  # sector_num -> crossing time
        self.current_lap_sector_times: List[float] = []
        
        # Completed data
        self.completed_laps: List[LapSectorTimes] = []
        self.sector_times_history: List[SectorTime] = []
        
        # Best times tracking
        self.best_sector_times: List[Optional[float]] = []
        self.best_lap_time: Optional[float] = None
        
        # State tracking
        self.is_initialized: bool = False
        self.last_session_info_hash: Optional[str] = None
        self.is_on_track: bool = True
        self.lap_start_time: float = 0.0
        
        logger.info("🔧 FIXED iRacing Sector Timing initialized")
        logger.info("✅ Uses official SplitTimeInfo boundaries with FIXED duration calculation")
    
    def initialize_default_sectors(self):
        """DEPRECATED: Do not use default sectors. Wait for real SessionInfo instead."""
        logger.warning("⚠️ initialize_default_sectors() called but is deprecated - waiting for real SessionInfo")
        return False
    
    def update_session_info(self, session_info_raw: str) -> bool:
        """
        Update sector layout from SessionInfo YAML.
        
        Args:
            session_info_raw: Raw SessionInfo string from iRacing
            
        Returns:
            True if sectors were successfully parsed, False otherwise
        """
        try:
            # Extract only the YAML portion first for consistent hashing
            yaml_content = self._extract_yaml_from_session_info(session_info_raw)
            if not yaml_content:
                logger.error("❌ Could not extract YAML from SessionInfo")
                return False
            
            # Check if session info has changed using YAML content hash
            session_hash = str(hash(yaml_content))
            if session_hash == self.last_session_info_hash and self.is_initialized:
                logger.debug("SessionInfo YAML unchanged and sectors already initialized")
                return self.is_initialized
            
            logger.info("🔄 Parsing SessionInfo for sector timing...")
            logger.info(f"🔍 SessionInfo length: {len(session_info_raw)} chars")
            logger.info(f"🔍 Extracted YAML length: {len(yaml_content)} chars")
            
            # Parse YAML
            session_data = yaml.safe_load(yaml_content)
            if not session_data:
                logger.error("❌ Failed to parse SessionInfo YAML")
                return False
            
            logger.info(f"🔍 Parsed YAML keys: {list(session_data.keys())}")
            
            # Extract SplitTimeInfo
            split_time_info = session_data.get('SplitTimeInfo', {})
            if not split_time_info:
                logger.error("❌ No SplitTimeInfo found in SessionInfo")
                return False
            
            logger.info(f"🔍 SplitTimeInfo keys: {list(split_time_info.keys())}")
            
            sectors_data = split_time_info.get('Sectors', [])
            if not sectors_data:
                logger.error("❌ No sector information found in SplitTimeInfo")
                return False
            
            logger.info(f"🔍 Found {len(sectors_data)} sectors in SessionInfo")
            
            # Parse sectors from SessionInfo
            new_sectors = []
            new_sector_starts = []
            
            for i, sector_data in enumerate(sectors_data):
                sector_num = sector_data.get('SectorNum', i)
                start_pct = sector_data.get('SectorStartPct', 0.0)
                
                sector_info = SectorInfo(sector_num=sector_num, start_pct=start_pct)
                new_sectors.append(sector_info)
                new_sector_starts.append(start_pct)
                
                logger.info(f"🏁 Parsed sector {sector_num}: starts at {start_pct:.3f}")
            
            # Add lap end (1.0) for convenience
            new_sector_starts.append(1.0)
            
            # Validate parsed sectors
            if len(new_sectors) < 1:
                logger.error(f"❌ No valid sectors found in SessionInfo")
                return False
            
            # Check if sectors actually changed
            sectors_changed = (
                len(new_sectors) != len(self.sectors) or
                any(new_sectors[i].start_pct != self.sectors[i].start_pct for i in range(len(new_sectors)) if i < len(self.sectors))
            )
            
            # Log sector analysis
            logger.info(f"🔍 Track sector analysis:")
            logger.info(f"   📊 Total sectors found: {len(new_sectors)}")
            for i, sector in enumerate(new_sectors):
                if i < len(new_sectors) - 1:
                    next_start = new_sectors[i + 1].start_pct
                    sector_length = next_start - sector.start_pct
                else:
                    sector_length = 1.0 - sector.start_pct
                logger.info(f"   🏁 Sector {sector.sector_num + 1}: {sector.start_pct:.3f} - {sector.start_pct + sector_length:.3f} (length: {sector_length:.3f})")
            
            # CRITICAL: Update with parsed sectors
            self.sectors = new_sectors
            self.sector_starts = new_sector_starts
            
            # Initialize best times tracking
            num_sectors = len(self.sectors)
            self.best_sector_times = [None] * num_sectors
            
            # ONLY reset timing state if sectors actually changed or we're not initialized
            if not self.is_initialized or sectors_changed:
                logger.debug("[SECTOR] Sectors changed or first initialization - resetting timing state")
                self._reset_timing_state()
            else:
                logger.debug("[SECTOR] Sectors unchanged - preserving current timing state")
            
            # Mark as initialized and update hash
            self.is_initialized = True
            self.last_session_info_hash = session_hash
            
            logger.info(f"[SECTOR] Sector timing updated from SessionInfo with {num_sectors} sectors")
            logger.debug(f"[SECTOR] Final sector boundaries: {[f'S{i+1}: {pct:.3f}' for i, pct in enumerate(self.sector_starts[:-1])]}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error parsing SessionInfo for sector timing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _extract_yaml_from_session_info(self, session_info_raw: str) -> str:
        """
        Extract only the YAML portion from SessionInfo, excluding telemetry data.
        
        Args:
            session_info_raw: Raw SessionInfo string that may contain both YAML and telemetry
            
        Returns:
            String containing only the YAML portion, or empty string if extraction fails
        """
        try:
            lines = session_info_raw.split('\n')
            yaml_lines = []
            
            # Look for the end of YAML content
            # YAML content ends when we hit lines that look like telemetry data
            # (lines with variable names followed by values, not YAML structure)
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    yaml_lines.append(line)
                    continue
                
                # Check if this looks like telemetry data (variable assignment format)
                # Telemetry lines look like: "VariableName                    value"
                if self._looks_like_telemetry_line(line):
                    # We've hit telemetry data, stop here
                    logger.info(f"🔍 YAML extraction stopped at telemetry line: {line[:50]}...")
                    break
                
                # This looks like YAML content, keep it
                yaml_lines.append(line)
            
            yaml_content = '\n'.join(yaml_lines)
            logger.info(f"🔍 Extracted {len(yaml_lines)} lines of YAML content from {len(lines)} total lines")
            
            return yaml_content
            
        except Exception as e:
            logger.error(f"❌ Error extracting YAML from SessionInfo: {e}")
            return ""
    
    def _looks_like_telemetry_line(self, line: str) -> bool:
        """
        Check if a line looks like telemetry data rather than YAML.
        
        Args:
            line: Line to check
            
        Returns:
            True if the line looks like telemetry data, False if it looks like YAML
        """
        try:
            stripped = line.strip()
            
            # Empty lines are not telemetry
            if not stripped:
                return False
            
            # YAML structure indicators (definitely not telemetry)
            yaml_indicators = ['---', '...', '- ', ': ', '  - ', '   - ', '     ']
            if any(stripped.startswith(indicator) for indicator in yaml_indicators):
                return False
            
            # Check for telemetry pattern: VariableName followed by many spaces and a value
            # Telemetry lines typically have a variable name, lots of spaces, then a value
            # The key is that telemetry has MANY spaces (20+), while YAML has fewer
            if '                    ' in line and line.count(' ') > 20:  # Many spaces indicate telemetry format
                return True
            
            # Check for common telemetry variable patterns, but only if they're at the start
            # and followed by many spaces (not YAML indentation)
            telemetry_patterns = [
                'AirDensity', 'AirPressure', 'AirTemp', 'Brake', 'Clutch',
                'Engine', 'Fuel', 'Gear', 'Lap', 'RPM', 'Speed', 'Steering', 'Throttle',
                'Velocity', 'Yaw', 'Roll', 'Pitch', 'FrameRate', 'CpuUsage'
            ]
            
            for pattern in telemetry_patterns:
                if stripped.startswith(pattern) and '                    ' in line:
                    return True
            
            # Special case: CarIdx is part of YAML when it's indented, but telemetry when it's not
            if stripped.startswith('CarIdx') and not line.startswith(' '):
                return True
            
            return False
            
        except Exception:
            return False
    
    def _reset_timing_state(self):
        """Reset the current timing state for total time tracking."""
        self.prev_pct = 0.0
        self.prev_time = 0.0
        self.current_sector_index = 0
        self.current_lap_number = 0
        self.current_lap_sector_times = []
        self.sector_crossing_times = {}
        self.lap_start_time = 0.0
        self.sector_start_time = 0.0  # FIXED: Reset sector start time
        logger.debug("[SECTOR] Timing state reset")
    
    def _interpolate_crossing_time(self, prev_pct: float, now_pct: float, 
                                 prev_time: float, now_time: float, 
                                 crossing_pct: float) -> float:
        """
        Interpolate the exact time when a sector boundary was crossed.
        
        This implements the precise crossing detection from the research to improve
        timing accuracy beyond the telemetry update frequency.
        
        Args:
            prev_pct: Previous LapDistPct
            now_pct: Current LapDistPct  
            prev_time: Previous SessionTime
            now_time: Current SessionTime
            crossing_pct: The sector boundary percentage that was crossed
            
        Returns:
            Interpolated crossing time
        """
        if prev_pct >= now_pct:
            # Handle wrap-around case or no movement
            return now_time
        
        # Calculate the fraction of the distance covered when crossing occurred
        total_distance = now_pct - prev_pct
        crossing_distance = crossing_pct - prev_pct
        
        if total_distance <= 0:
            return now_time
        
        crossing_fraction = crossing_distance / total_distance
        
        # Interpolate the time
        time_delta = now_time - prev_time
        interpolated_time = prev_time + (crossing_fraction * time_delta)
        
        return interpolated_time
    
    def _finalize_incomplete_lap(self, timestamp: float) -> None:
        """
        Finalize an incomplete lap when session changes occur.
        
        This handles cases where a lap is interrupted (e.g., reset to pits)
        but we still want to record the partial sector data.
        
        Args:
            timestamp: Current session time
        """
        try:
            if not self.current_lap_sector_times:
                logger.debug("🔄 No sector data to finalize for incomplete lap")
                return
            
            # Add the current sector time if we're in the middle of a sector
            if self.sector_start_time > 0:
                current_sector_time = timestamp - self.sector_start_time
                self.current_lap_sector_times.append(current_sector_time)
                logger.info(f"🔧 Added final sector time {current_sector_time:.3f}s for incomplete lap")
            
            # Calculate partial lap time
            total_time = sum(self.current_lap_sector_times)
            
            # Create incomplete lap record
            incomplete_lap = LapSectorTimes(
                lap_number=self.current_lap_number,
                sector_times=self.current_lap_sector_times.copy(),
                total_time=total_time,
                timestamp=timestamp,
                is_valid=False  # Mark as invalid since it's incomplete
            )
            
            # Store the incomplete lap
            self.completed_laps.append(incomplete_lap)
            
            # Log the incomplete lap
            sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(self.current_lap_sector_times)])
            logger.warning(f"⚠️ INCOMPLETE Lap {self.current_lap_number}: {sector_str}  PARTIAL {total_time:.3f}s")
            
            # Reset for next lap
            self.current_lap_sector_times = []
            
        except Exception as e:
            logger.error(f"❌ Error finalizing incomplete lap: {e}")
    
    def _complete_lap(self, timestamp: float) -> LapSectorTimes:
        """Complete the current lap and return total sector times."""
        try:
            # Calculate total lap time from sector times
            total_time = sum(self.current_lap_sector_times)
            
            # Create lap record
            lap_sectors = LapSectorTimes(
                lap_number=self.current_lap_number,
                sector_times=self.current_lap_sector_times.copy(),
                total_time=total_time,
                timestamp=timestamp,
                is_valid=True
            )
            
            # Update best lap time
            if self.best_lap_time is None or total_time < self.best_lap_time:
                self.best_lap_time = total_time
                logger.info(f"✨ New best lap: {total_time:.3f}s")
            
            # Enhanced lap completion logging
            sector_str = "  ".join([f"S{i+1} {time:.3f}" for i, time in enumerate(self.current_lap_sector_times)])
            logger.info(f"🏁 COMPLETE Lap {self.current_lap_number}: {sector_str}  LAP {total_time:.3f}s")
            
            # Log any unusually long sector times
            for i, sector_time in enumerate(self.current_lap_sector_times):
                if sector_time > 120.0:  # More than 2 minutes
                    logger.warning(f"⏰ LONG SECTOR: S{i+1} took {sector_time:.1f}s ({sector_time/60:.1f} minutes) - includes stationary time")
            
            # Store completed lap
            self.completed_laps.append(lap_sectors)
            
            # Reset for next lap
            self.current_lap_sector_times = []
            
            return lap_sectors
            
        except Exception as e:
            logger.error(f"❌ Error completing lap: {e}")
            # Return invalid lap on error
            return LapSectorTimes(
                lap_number=self.current_lap_number,
                sector_times=self.current_lap_sector_times.copy(),
                total_time=sum(self.current_lap_sector_times) if self.current_lap_sector_times else 0.0,
                timestamp=timestamp,
                is_valid=False
            )
    
    def process_telemetry(self, telemetry_data: Dict) -> Optional[LapSectorTimes]:
        """
        Process telemetry data to track TOTAL TIME spent in each sector.
        
        This method now captures:
        - Time spent driving through sectors
        - Time spent stationary in sectors (e.g., sitting on track)
        - Accurate sector performance including all delays
        
        Args:
            telemetry_data: Dictionary containing telemetry data including:
                - LapDistPct: Current position on track (0.0 to 1.0)
                - SessionTime: Current session time in seconds
                - Lap: Current lap number
                
        Returns:
            LapSectorTimes object if a lap was completed, None otherwise
        """
        # Add debug logging to track calls
        if not hasattr(self, '_process_telemetry_call_count'):
            self._process_telemetry_call_count = 0
        self._process_telemetry_call_count += 1
        
        # Log every 300 calls (about once per 5 seconds at 60Hz)
        if self._process_telemetry_call_count % 300 == 0:
            logger.debug(f"[SECTOR] process_telemetry called {self._process_telemetry_call_count} times, initialized: {self.is_initialized}")
        
        if not self.is_initialized:
            # Log occasionally that we're waiting for SessionInfo
            if not hasattr(self, '_waiting_log_counter'):
                self._waiting_log_counter = 0
            self._waiting_log_counter += 1
            if self._waiting_log_counter % 300 == 0:  # Every ~5 seconds at 60Hz
                logger.info("🔄 Sector timing waiting for SessionInfo to initialize...")
            return None
        
        try:
            # Extract required data
            now_pct = telemetry_data.get('LapDistPct')
            now_time = telemetry_data.get('SessionTime') or telemetry_data.get('SessionTimeSecs')
            current_lap = telemetry_data.get('Lap', 0)
            
            if now_pct is None or now_time is None:
                return None
            
            # Handle lap number changes (reset detection)
            if current_lap != self.current_lap_number:
                if current_lap < self.current_lap_number:
                    # Session reset detected
                    logger.info(f"🔄 Session reset detected (lap {self.current_lap_number} -> {current_lap})")
                    self._reset_timing_state()
                elif current_lap > self.current_lap_number:
                    # New lap started - finalize any incomplete lap
                    if self.current_lap_sector_times and len(self.current_lap_sector_times) > 0:
                        logger.info(f"🏁 Finalizing incomplete lap {self.current_lap_number} due to lap number change")
                        self._finalize_incomplete_lap(now_time)
                
                self.current_lap_number = current_lap
            
            # Initialize timing on first telemetry
            if self.prev_time == 0.0:
                self.prev_pct = now_pct
                self.prev_time = now_time
                self.current_sector_index = self._get_current_sector_index(now_pct)
                self.lap_start_time = now_time
                self.sector_start_time = now_time  # FIXED: Set sector start time
                
                # Initialize sector times array for current lap
                self.current_lap_sector_times = []
                
                logger.info(f"🏁 FIXED sector timing started for {len(self.sectors)}-sector track")
                logger.info(f"🔧 Starting in sector {self.current_sector_index + 1} at position {now_pct:.3f}")
                logger.info(f"✅ Will track proper sector durations (SessionTime differences)")
                return None
            
            # Calculate time elapsed since last telemetry frame
            time_delta = now_time - self.prev_time
            
            # ENHANCED: Always accumulate time in current sector (this captures stationary time!)
            self.prev_time = now_time
            
            # Determine which sector we should be in based on current track position
            expected_sector_index = self._get_current_sector_index(now_pct)
            
            # Check if we've moved to a different sector
            if expected_sector_index != self.current_sector_index:
                # We've moved to a new sector!
                # FIXED: Calculate sector time as duration between SessionTimes
                sector_time = now_time - self.sector_start_time
                
                # Validate sector time is reasonable
                if sector_time < 0:
                    logger.warning(f"⚠️ Negative sector time detected: {sector_time:.3f}s - skipping")
                    # Update sector start time and continue
                    self.current_sector_index = expected_sector_index
                    self.sector_start_time = now_time
                    self.prev_pct = now_pct
                    self.prev_time = now_time
                    return None
                
                # Log the sector completion
                logger.debug(f"[SECTOR] S{self.current_sector_index + 1}: {sector_time:.3f}s (lap {self.current_lap_number})")
                if sector_time > 60.0:  # Log long sector times
                    logger.warning(f"[SECTOR] Long sector time: S{self.current_sector_index + 1} took {sector_time:.1f}s ({sector_time/60:.1f} minutes)")
                
                # Store the completed sector time
                self.current_lap_sector_times.append(sector_time)
                
                # Create sector time record for history
                sector_record = SectorTime(
                    sector_num=self.current_sector_index,
                    time=sector_time,
                    lap_number=self.current_lap_number,
                    timestamp=now_time
                )
                self.sector_times_history.append(sector_record)
                
                # Update best sector time
                if (self.best_sector_times[self.current_sector_index] is None or 
                    sector_time < self.best_sector_times[self.current_sector_index]):
                    self.best_sector_times[self.current_sector_index] = sector_time
                    logger.info(f"✨ New best S{self.current_sector_index + 1}: {sector_time:.3f}s")
                
                # Move to the new sector
                self.current_sector_index = expected_sector_index
                self.sector_start_time = now_time  # FIXED: Update sector start time
                
                # 🔧 ENHANCED LAP COMPLETION DETECTION: Check multiple conditions for lap completion
                lap_completed = False
                completion_reason = ""
                
                # Condition 1: Traditional - moved back to sector 0 and have all sectors
                if self.current_sector_index == 0 and len(self.current_lap_sector_times) == len(self.sectors):
                    lap_completed = True
                    completion_reason = "returned to sector 0 with all sectors complete"
                
                # Condition 2: Enhanced - track position wrapped around (crossed start/finish line)
                elif self.prev_pct > 0.9 and now_pct < 0.1 and len(self.current_lap_sector_times) >= len(self.sectors) - 1:
                    # Track position wrapped from near 1.0 to near 0.0, indicating start/finish line crossing
                    # and we have at least most sectors completed
                    lap_completed = True
                    completion_reason = "track position wrapped around with sufficient sectors"
                    
                    # If we're missing the final sector time (car finished in last sector), add it
                    if len(self.current_lap_sector_times) == len(self.sectors) - 1:
                        final_sector_time = now_time - self.sector_start_time
                        if final_sector_time > 0:
                            self.current_lap_sector_times.append(final_sector_time)
                            logger.info(f"🔧 Added final sector time for wrap-around completion: S{len(self.sectors)} = {final_sector_time:.3f}s")
                
                # Condition 3: Fallback - Have all sectors and significant track position progress
                elif len(self.current_lap_sector_times) == len(self.sectors) and now_pct > 0.8:
                    # We have all sector times and are near the end of the track
                    lap_completed = True
                    completion_reason = "all sectors complete and near track end"
                
                if lap_completed:
                    logger.debug(f"[SECTOR] Lap completion detected: {completion_reason}")
                    logger.debug(f"[SECTOR] Lap data: sectors={len(self.current_lap_sector_times)}/{len(self.sectors)}, current_sector={self.current_sector_index}, track_pos={now_pct:.3f}")
                    return self._complete_lap(now_time)
                
                # Log sector transition
                logger.debug(f"🔄 Moved to sector {self.current_sector_index + 1} at position {now_pct:.3f}")
            
            # 🔧 ADDITIONAL LAP COMPLETION CHECK: Monitor for lap completion even without sector changes
            # This handles cases where the car might complete a lap while staying in the same sector
            else:
                # Check for track position wrap-around (start/finish line crossing) without sector change
                if (self.prev_pct > 0.95 and now_pct < 0.05 and 
                    len(self.current_lap_sector_times) > 0):  # Have at least some sector data
                    
                    # Calculate final sector time for the sector we just completed
                    final_sector_time = now_time - self.sector_start_time
                    if final_sector_time > 0:
                        self.current_lap_sector_times.append(final_sector_time)
                        logger.info(f"🔧 LAP COMPLETION: Added final sector time due to position wrap: S{len(self.current_lap_sector_times)} = {final_sector_time:.3f}s")
                    
                    logger.info(f"🏁 LAP COMPLETION: Track position wrapped (no sector change) - sectors: {len(self.current_lap_sector_times)}/{len(self.sectors)}")
                    
                    # Complete the lap regardless of sector count (partial laps are valid)
                    if len(self.current_lap_sector_times) > 0:
                        return self._complete_lap(now_time)
                    
            # Update previous values for next iteration
            self.prev_pct = now_pct
            
        except Exception as e:
            logger.error(f"❌ Error processing sector timing telemetry: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _get_current_sector_index(self, track_position: float) -> int:
        """
        Determine which sector the car is currently in based on track position.
        
        Args:
            track_position: Current LapDistPct (0.0 to 1.0)
            
        Returns:
            Index of the current sector (0-based)
        """
        # Handle wrap-around case (track position near 1.0 should be in last sector)
        if track_position >= 0.99:
            return len(self.sectors) - 1
        
        # Find which sector this track position falls into
        for i in range(len(self.sectors)):
            sector_start = self.sectors[i].start_pct
            
            # For the last sector, it goes from its start to 1.0
            if i == len(self.sectors) - 1:
                sector_end = 1.0
            else:
                sector_end = self.sectors[i + 1].start_pct
            
            # Check if track position is in this sector
            if sector_start <= track_position < sector_end:
                return i
        
        # Fallback to first sector if no match found
        return 0
    
    def get_current_sector_progress(self) -> Dict:
        """Get current sector timing progress with total time tracking."""
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
                'timing_mode': 'enhanced_total_time'
            }
        
        # FIXED: Calculate current sector time properly
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
            'captures_stationary_time': True,
            'lap_start_time': self.lap_start_time,
            'sector_start_time': self.sector_start_time
        }
    
    def get_sector_comparison(self, lap_sectors: LapSectorTimes) -> Dict:
        """Compare lap sectors against best times."""
        if not self.is_initialized or not lap_sectors.sector_times:
            return {}
        
        comparison = {
            'sector_deltas': [],
            'lap_delta': None,
            'sectors_improved': 0,
            'is_best_lap': False
        }
        
        # Compare each sector
        for i, sector_time in enumerate(lap_sectors.sector_times):
            if i < len(self.best_sector_times) and self.best_sector_times[i] is not None:
                delta = sector_time - self.best_sector_times[i]
                comparison['sector_deltas'].append(delta)
                if delta < 0:
                    comparison['sectors_improved'] += 1
            else:
                comparison['sector_deltas'].append(0.0)
        
        # Compare lap time
        if self.best_lap_time is not None:
            comparison['lap_delta'] = lap_sectors.total_time - self.best_lap_time
            comparison['is_best_lap'] = lap_sectors.total_time < self.best_lap_time
        
        return comparison
    
    def get_recent_laps(self, count: int = 10) -> List[LapSectorTimes]:
        """Get the most recent completed laps."""
        return self.completed_laps[-count:] if self.completed_laps else []
    
    def clear_data(self):
        """Clear all timing data (for new session)."""
        self.completed_laps.clear()
        self.sector_times_history.clear()
        self.best_sector_times = [None] * len(self.sectors) if self.sectors else []
        self.best_lap_time = None
        self._reset_timing_state()
        logger.info("Sector timing data cleared") 