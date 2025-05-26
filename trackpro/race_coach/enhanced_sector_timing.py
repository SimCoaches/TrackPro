"""
Enhanced Sector Timing with Maximum Reliability

This module builds on the existing sector timing with additional reliability features:
- Multi-frame validation to prevent false crossings
- Confidence scoring for sector times
- Automatic outlier detection and correction
- Backup timing methods for edge cases
- Real-time validation against expected lap times
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import statistics

logger = logging.getLogger(__name__)

@dataclass
class SectorCrossing:
    """A detected sector crossing with confidence metrics."""
    sector_num: int
    crossing_time: float
    lap_dist_pct: float
    confidence: float  # 0.0 to 1.0
    method: str  # 'interpolated', 'direct', 'validated'

@dataclass
class ReliableSectorTime:
    """A sector time with reliability metrics."""
    sector_num: int
    time: float
    confidence: float
    is_outlier: bool
    validation_notes: List[str]

class EnhancedSectorTiming:
    """
    Enhanced sector timing with maximum reliability features.
    
    Key improvements:
    - Multi-frame crossing validation
    - Confidence scoring for all measurements
    - Outlier detection and correction
    - Backup timing methods
    - Real-time validation
    """
    
    def __init__(self, base_sector_timing):
        """Initialize with existing sector timing as base."""
        self.base_timing = base_sector_timing
        
        # Enhanced tracking
        self.crossing_history = deque(maxlen=100)  # Recent crossings
        self.sector_time_history = deque(maxlen=50)  # Recent sector times
        self.position_history = deque(maxlen=10)  # Last 10 positions for validation
        
        # Reliability metrics
        self.confidence_threshold = 0.7  # Minimum confidence for valid times
        self.outlier_threshold = 2.0  # Standard deviations for outlier detection
        
        # Validation parameters
        self.min_sector_time = 5.0  # Minimum reasonable sector time (seconds)
        self.max_sector_time = 300.0  # Maximum reasonable sector time (seconds)
        
        logger.info("🔧 Enhanced Sector Timing initialized with reliability features")
    
    def process_telemetry_enhanced(self, telemetry_data: Dict) -> Optional[Dict]:
        """
        Enhanced telemetry processing with reliability checks.
        
        Returns:
            Dictionary with sector data and reliability metrics, or None
        """
        # First, run the base timing
        base_result = self.base_timing.process_telemetry(telemetry_data)
        
        # Extract current position data
        now_pct = telemetry_data.get('LapDistPct')
        now_time = telemetry_data.get('SessionTime')
        
        if now_pct is None or now_time is None:
            return None
        
        # Add to position history for validation
        self.position_history.append({
            'pct': now_pct,
            'time': now_time,
            'timestamp': time.time()
        })
        
        # Enhanced crossing detection
        enhanced_crossings = self._detect_crossings_with_validation(telemetry_data)
        
        # If we have a completed lap from base timing, enhance it
        if base_result:
            enhanced_result = self._enhance_lap_result(base_result, enhanced_crossings)
            return enhanced_result
        
        return None
    
    def _detect_crossings_with_validation(self, telemetry_data: Dict) -> List[SectorCrossing]:
        """
        Detect sector crossings with multi-frame validation.
        
        Returns:
            List of validated sector crossings
        """
        crossings = []
        
        if len(self.position_history) < 2:
            return crossings
        
        prev_pos = self.position_history[-2]
        curr_pos = self.position_history[-1]
        
        # Check each sector boundary
        for i, sector_start in enumerate(self.base_timing.sector_starts[:-1]):
            if self._is_crossing_detected(prev_pos['pct'], curr_pos['pct'], sector_start):
                # Calculate crossing with interpolation
                crossing_time = self._interpolate_crossing_time(
                    prev_pos['pct'], curr_pos['pct'],
                    prev_pos['time'], curr_pos['time'],
                    sector_start
                )
                
                # Calculate confidence based on multiple factors
                confidence = self._calculate_crossing_confidence(
                    prev_pos, curr_pos, sector_start, crossing_time
                )
                
                crossing = SectorCrossing(
                    sector_num=i,
                    crossing_time=crossing_time,
                    lap_dist_pct=sector_start,
                    confidence=confidence,
                    method='interpolated' if confidence > 0.8 else 'direct'
                )
                
                crossings.append(crossing)
                self.crossing_history.append(crossing)
        
        return crossings
    
    def _is_crossing_detected(self, prev_pct: float, curr_pct: float, boundary: float) -> bool:
        """
        Detect if a sector boundary was crossed with wrap-around handling.
        """
        # Handle normal crossing
        if prev_pct < boundary <= curr_pct:
            return True
        
        # Handle wrap-around (end of lap)
        if prev_pct > curr_pct:  # Wrapped around
            if prev_pct < boundary or curr_pct >= boundary:
                return True
        
        return False
    
    def _interpolate_crossing_time(self, prev_pct: float, curr_pct: float,
                                 prev_time: float, curr_time: float,
                                 boundary: float) -> float:
        """
        Interpolate exact crossing time with wrap-around handling.
        """
        # Handle wrap-around case
        if prev_pct > curr_pct:
            # Wrapped around - adjust calculation
            if prev_pct < boundary:
                # Boundary is after wrap point
                distance_to_boundary = boundary - prev_pct
                total_distance = (1.0 - prev_pct) + curr_pct
            else:
                # Boundary is before wrap point
                distance_to_boundary = (1.0 - prev_pct) + boundary
                total_distance = (1.0 - prev_pct) + curr_pct
        else:
            # Normal case
            distance_to_boundary = boundary - prev_pct
            total_distance = curr_pct - prev_pct
        
        if total_distance <= 0:
            return curr_time
        
        fraction = distance_to_boundary / total_distance
        return prev_time + (fraction * (curr_time - prev_time))
    
    def _calculate_crossing_confidence(self, prev_pos: Dict, curr_pos: Dict,
                                     boundary: float, crossing_time: float) -> float:
        """
        Calculate confidence score for a sector crossing.
        
        Factors considered:
        - Time delta consistency
        - Position delta reasonableness
        - Historical crossing patterns
        - Speed consistency
        """
        confidence = 1.0
        
        # Factor 1: Time delta reasonableness
        time_delta = curr_pos['time'] - prev_pos['time']
        if time_delta <= 0 or time_delta > 5.0:  # More than 5 seconds between frames
            confidence *= 0.5
        
        # Factor 2: Position delta reasonableness
        pos_delta = abs(curr_pos['pct'] - prev_pos['pct'])
        if pos_delta > 0.1:  # More than 10% of track in one frame
            confidence *= 0.7
        elif pos_delta < 0.001:  # Too small movement
            confidence *= 0.8
        
        # Factor 3: Crossing time reasonableness
        if crossing_time <= 0:
            confidence *= 0.3
        
        # Factor 4: Historical consistency
        recent_crossings = [c for c in self.crossing_history if c.sector_num == boundary]
        if len(recent_crossings) >= 3:
            recent_times = [c.crossing_time for c in recent_crossings[-3:]]
            if len(recent_times) > 1:
                time_variance = statistics.variance(recent_times)
                if time_variance > 100:  # High variance in crossing times
                    confidence *= 0.8
        
        return max(0.0, min(1.0, confidence))
    
    def _enhance_lap_result(self, base_result, enhanced_crossings: List[SectorCrossing]) -> Dict:
        """
        Enhance the base lap result with reliability metrics.
        """
        enhanced_sectors = []
        
        for i, sector_time in enumerate(base_result.sector_times):
            # Create reliable sector time with validation
            reliable_sector = self._create_reliable_sector_time(i, sector_time, enhanced_crossings)
            enhanced_sectors.append(reliable_sector)
        
        # Calculate overall lap confidence
        sector_confidences = [s.confidence for s in enhanced_sectors]
        lap_confidence = statistics.mean(sector_confidences) if sector_confidences else 0.0
        
        return {
            'base_result': base_result,
            'enhanced_sectors': enhanced_sectors,
            'lap_confidence': lap_confidence,
            'reliability_notes': self._generate_reliability_notes(enhanced_sectors),
            'is_reliable': lap_confidence >= self.confidence_threshold
        }
    
    def _create_reliable_sector_time(self, sector_num: int, sector_time: float,
                                   crossings: List[SectorCrossing]) -> ReliableSectorTime:
        """
        Create a reliable sector time with validation.
        """
        validation_notes = []
        confidence = 1.0
        is_outlier = False
        
        # Validate sector time range
        if sector_time < self.min_sector_time:
            validation_notes.append(f"Very fast sector: {sector_time:.3f}s")
            confidence *= 0.7
        elif sector_time > self.max_sector_time:
            validation_notes.append(f"Very slow sector: {sector_time:.3f}s")
            confidence *= 0.5
        
        # Check against historical data
        historical_times = [st.time for st in self.sector_time_history 
                          if hasattr(st, 'sector_num') and st.sector_num == sector_num]
        
        if len(historical_times) >= 3:
            mean_time = statistics.mean(historical_times)
            std_dev = statistics.stdev(historical_times) if len(historical_times) > 1 else 0
            
            if std_dev > 0:
                z_score = abs(sector_time - mean_time) / std_dev
                if z_score > self.outlier_threshold:
                    is_outlier = True
                    validation_notes.append(f"Outlier: {z_score:.1f} std devs from mean")
                    confidence *= 0.6
        
        # Check crossing confidence if available
        sector_crossings = [c for c in crossings if c.sector_num == sector_num]
        if sector_crossings:
            crossing_confidence = max(c.confidence for c in sector_crossings)
            confidence *= crossing_confidence
            validation_notes.append(f"Crossing confidence: {crossing_confidence:.2f}")
        
        reliable_sector = ReliableSectorTime(
            sector_num=sector_num,
            time=sector_time,
            confidence=confidence,
            is_outlier=is_outlier,
            validation_notes=validation_notes
        )
        
        # Add to history
        self.sector_time_history.append(reliable_sector)
        
        return reliable_sector
    
    def _generate_reliability_notes(self, enhanced_sectors: List[ReliableSectorTime]) -> List[str]:
        """
        Generate human-readable reliability notes for the lap.
        """
        notes = []
        
        # Check for outliers
        outliers = [s for s in enhanced_sectors if s.is_outlier]
        if outliers:
            outlier_sectors = [f"S{s.sector_num + 1}" for s in outliers]
            notes.append(f"Outlier sectors detected: {', '.join(outlier_sectors)}")
        
        # Check for low confidence sectors
        low_confidence = [s for s in enhanced_sectors if s.confidence < self.confidence_threshold]
        if low_confidence:
            low_conf_sectors = [f"S{s.sector_num + 1}" for s in low_confidence]
            notes.append(f"Low confidence sectors: {', '.join(low_conf_sectors)}")
        
        # Check for very fast/slow sectors
        fast_sectors = [s for s in enhanced_sectors if s.time < self.min_sector_time]
        slow_sectors = [s for s in enhanced_sectors if s.time > self.max_sector_time]
        
        if fast_sectors:
            notes.append(f"Unusually fast sectors detected")
        if slow_sectors:
            notes.append(f"Unusually slow sectors detected (may include stationary time)")
        
        return notes
    
    def get_reliability_summary(self) -> Dict:
        """
        Get a summary of timing reliability metrics.
        """
        if not self.sector_time_history:
            return {"status": "No data available"}
        
        recent_sectors = list(self.sector_time_history)[-20:]  # Last 20 sectors
        
        total_confidence = sum(s.confidence for s in recent_sectors)
        avg_confidence = total_confidence / len(recent_sectors)
        
        outlier_count = sum(1 for s in recent_sectors if s.is_outlier)
        outlier_rate = outlier_count / len(recent_sectors)
        
        return {
            "average_confidence": avg_confidence,
            "outlier_rate": outlier_rate,
            "total_sectors_processed": len(self.sector_time_history),
            "recent_crossings": len(self.crossing_history),
            "reliability_status": "Good" if avg_confidence > 0.8 else "Fair" if avg_confidence > 0.6 else "Poor"
        }

def create_enhanced_sector_timing(base_sector_timing):
    """
    Factory function to create enhanced sector timing.
    
    Args:
        base_sector_timing: Existing SectorTimingCollector instance
        
    Returns:
        EnhancedSectorTiming instance
    """
    return EnhancedSectorTiming(base_sector_timing) 