"""
Sector Time Validation Module

This module provides validation logic to ensure sector times are accurate by:
- Comparing sum of sector times to official iRacing lap time
- Detecting timing discrepancies and errors
- Providing correction suggestions
- Flagging unreliable sector data
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LapTimeValidation:
    """Results of lap time validation."""
    is_valid: bool
    sector_sum: float
    official_lap_time: float
    discrepancy: float  # Difference between sector sum and official time
    discrepancy_percentage: float
    validation_notes: List[str]
    confidence_score: float  # 0.0 to 1.0

class SectorTimeValidator:
    """
    Validates sector times against official iRacing lap times.
    
    This ensures that:
    - Sum of sector times matches official lap time
    - Detects timing errors and discrepancies
    - Provides reliability scoring
    - Suggests corrections when possible
    """
    
    def __init__(self):
        # Validation thresholds
        self.max_discrepancy_seconds = 0.5  # Maximum allowed difference (500ms)
        self.max_discrepancy_percentage = 1.0  # Maximum allowed percentage difference (1%)
        self.warning_threshold_seconds = 0.1  # Warning threshold (100ms)
        
        # Historical tracking for pattern detection
        self.validation_history = []
        self.systematic_error_threshold = 5  # Number of consistent errors to detect systematic issues
        
        logger.info("🔧 Sector Time Validator initialized")
        logger.info(f"   📊 Max discrepancy: {self.max_discrepancy_seconds}s ({self.max_discrepancy_percentage}%)")
    
    def validate_lap_timing(self, sector_times: List[float], official_lap_time: float, 
                          lap_number: int = None) -> LapTimeValidation:
        """
        Validate sector times against official iRacing lap time.
        
        Args:
            sector_times: List of sector times in seconds
            official_lap_time: Official lap time from iRacing telemetry
            lap_number: Optional lap number for tracking
            
        Returns:
            LapTimeValidation with detailed validation results
        """
        validation_notes = []
        
        # Calculate sector sum
        sector_sum = sum(sector_times)
        discrepancy = abs(sector_sum - official_lap_time)
        discrepancy_percentage = (discrepancy / official_lap_time) * 100 if official_lap_time > 0 else 100
        
        # Determine if validation passes
        is_valid = (
            discrepancy <= self.max_discrepancy_seconds and 
            discrepancy_percentage <= self.max_discrepancy_percentage
        )
        
        # Generate validation notes
        if discrepancy > self.warning_threshold_seconds:
            if discrepancy > self.max_discrepancy_seconds:
                validation_notes.append(f"CRITICAL: Large timing discrepancy ({discrepancy:.3f}s)")
            else:
                validation_notes.append(f"WARNING: Timing discrepancy detected ({discrepancy:.3f}s)")
        
        if discrepancy_percentage > 0.5:
            validation_notes.append(f"Percentage error: {discrepancy_percentage:.2f}%")
        
        # Check for systematic errors
        systematic_error = self._detect_systematic_error(discrepancy, sector_sum > official_lap_time)
        if systematic_error:
            validation_notes.append(f"Systematic error detected: {systematic_error}")
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(discrepancy, discrepancy_percentage)
        
        # Add specific sector analysis
        sector_analysis = self._analyze_individual_sectors(sector_times, official_lap_time)
        validation_notes.extend(sector_analysis)
        
        validation = LapTimeValidation(
            is_valid=is_valid,
            sector_sum=sector_sum,
            official_lap_time=official_lap_time,
            discrepancy=discrepancy,
            discrepancy_percentage=discrepancy_percentage,
            validation_notes=validation_notes,
            confidence_score=confidence_score
        )
        
        # Store in history for pattern detection
        self.validation_history.append({
            'lap_number': lap_number,
            'discrepancy': discrepancy,
            'is_over': sector_sum > official_lap_time,
            'validation': validation
        })
        
        # Keep only recent history
        if len(self.validation_history) > 20:
            self.validation_history = self.validation_history[-20:]
        
        # Log validation results
        self._log_validation_results(validation, lap_number)
        
        return validation
    
    def _detect_systematic_error(self, discrepancy: float, is_over: bool) -> Optional[str]:
        """
        Detect systematic timing errors from historical data.
        
        Args:
            discrepancy: Current discrepancy
            is_over: Whether sector sum is over or under official time
            
        Returns:
            Description of systematic error if detected, None otherwise
        """
        if len(self.validation_history) < self.systematic_error_threshold:
            return None
        
        recent_validations = self.validation_history[-self.systematic_error_threshold:]
        
        # Check for consistent over/under timing
        consistent_over = all(v['is_over'] for v in recent_validations)
        consistent_under = all(not v['is_over'] for v in recent_validations)
        
        if consistent_over:
            avg_discrepancy = sum(v['discrepancy'] for v in recent_validations) / len(recent_validations)
            return f"Consistently over by ~{avg_discrepancy:.3f}s (possible timing offset)"
        elif consistent_under:
            avg_discrepancy = sum(v['discrepancy'] for v in recent_validations) / len(recent_validations)
            return f"Consistently under by ~{avg_discrepancy:.3f}s (possible missing time)"
        
        # Check for increasing discrepancy trend
        discrepancies = [v['discrepancy'] for v in recent_validations]
        if len(discrepancies) >= 3:
            trend = discrepancies[-1] - discrepancies[0]
            if trend > 0.2:  # Increasing by more than 200ms
                return f"Increasing timing error trend (+{trend:.3f}s over {len(discrepancies)} laps)"
        
        return None
    
    def _calculate_confidence_score(self, discrepancy: float, discrepancy_percentage: float) -> float:
        """
        Calculate confidence score based on timing accuracy.
        
        Args:
            discrepancy: Absolute discrepancy in seconds
            discrepancy_percentage: Percentage discrepancy
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        # Start with perfect confidence
        confidence = 1.0
        
        # Reduce confidence based on absolute discrepancy
        if discrepancy > 0.05:  # 50ms
            confidence *= max(0.1, 1.0 - (discrepancy / self.max_discrepancy_seconds))
        
        # Reduce confidence based on percentage discrepancy
        if discrepancy_percentage > 0.1:  # 0.1%
            confidence *= max(0.1, 1.0 - (discrepancy_percentage / self.max_discrepancy_percentage))
        
        # Boost confidence for very accurate timing
        if discrepancy < 0.01:  # Within 10ms
            confidence = min(1.0, confidence * 1.1)
        
        return max(0.0, min(1.0, confidence))
    
    def _analyze_individual_sectors(self, sector_times: List[float], official_lap_time: float) -> List[str]:
        """
        Analyze individual sectors for potential issues.
        
        Args:
            sector_times: List of sector times
            official_lap_time: Official lap time
            
        Returns:
            List of analysis notes
        """
        notes = []
        
        # Check for unreasonably fast/slow sectors
        for i, sector_time in enumerate(sector_times):
            if sector_time < 5.0:
                notes.append(f"S{i+1} very fast: {sector_time:.3f}s")
            elif sector_time > official_lap_time * 0.6:  # Single sector > 60% of lap
                notes.append(f"S{i+1} very slow: {sector_time:.3f}s (may include stationary time)")
        
        # Check sector balance (no single sector should dominate unless it's a very long sector)
        if len(sector_times) >= 2:
            max_sector = max(sector_times)
            min_sector = min(sector_times)
            ratio = max_sector / min_sector if min_sector > 0 else float('inf')
            
            if ratio > 10:  # One sector is 10x longer than another
                max_idx = sector_times.index(max_sector)
                min_idx = sector_times.index(min_sector)
                notes.append(f"Large sector imbalance: S{max_idx+1} ({max_sector:.3f}s) vs S{min_idx+1} ({min_sector:.3f}s)")
        
        return notes
    
    def _log_validation_results(self, validation: LapTimeValidation, lap_number: Optional[int]):
        """Log validation results with appropriate level."""
        lap_info = f"Lap {lap_number}" if lap_number else "Lap"
        
        if validation.is_valid:
            if validation.discrepancy < 0.05:  # Very accurate
                logger.info(f"✅ {lap_info}: Excellent timing accuracy ({validation.discrepancy:.3f}s discrepancy)")
            else:
                logger.info(f"✅ {lap_info}: Good timing accuracy ({validation.discrepancy:.3f}s discrepancy)")
        else:
            logger.warning(f"⚠️ {lap_info}: Timing validation FAILED ({validation.discrepancy:.3f}s discrepancy)")
            logger.warning(f"   📊 Sector sum: {validation.sector_sum:.3f}s, Official: {validation.official_lap_time:.3f}s")
        
        # Log any validation notes
        for note in validation.validation_notes:
            if "CRITICAL" in note:
                logger.error(f"   🚨 {note}")
            elif "WARNING" in note:
                logger.warning(f"   ⚠️ {note}")
            else:
                logger.info(f"   📝 {note}")
    
    def get_validation_summary(self) -> Dict:
        """
        Get summary of validation performance.
        
        Returns:
            Dictionary with validation statistics
        """
        if not self.validation_history:
            return {"status": "No validation data available"}
        
        recent_validations = [v['validation'] for v in self.validation_history[-10:]]
        
        valid_count = sum(1 for v in recent_validations if v.is_valid)
        total_count = len(recent_validations)
        success_rate = (valid_count / total_count) * 100 if total_count > 0 else 0
        
        avg_discrepancy = sum(v.discrepancy for v in recent_validations) / total_count
        avg_confidence = sum(v.confidence_score for v in recent_validations) / total_count
        
        return {
            "validation_success_rate": success_rate,
            "average_discrepancy": avg_discrepancy,
            "average_confidence": avg_confidence,
            "total_validations": len(self.validation_history),
            "recent_validations": total_count,
            "status": "Excellent" if success_rate > 90 else "Good" if success_rate > 75 else "Poor"
        }
    
    def suggest_correction(self, validation: LapTimeValidation) -> Optional[Dict]:
        """
        Suggest corrections for timing discrepancies.
        
        Args:
            validation: Failed validation result
            
        Returns:
            Dictionary with correction suggestions, or None if no correction possible
        """
        if validation.is_valid:
            return None
        
        suggestions = {
            "discrepancy": validation.discrepancy,
            "correction_needed": validation.discrepancy,
            "suggestions": []
        }
        
        # Suggest proportional correction
        if validation.sector_sum > 0:
            correction_factor = validation.official_lap_time / validation.sector_sum
            suggestions["proportional_correction_factor"] = correction_factor
            suggestions["suggestions"].append(
                f"Apply proportional correction factor: {correction_factor:.6f}"
            )
        
        # Suggest specific sector adjustments
        if validation.discrepancy < 1.0:  # Only for small discrepancies
            per_sector_adjustment = validation.discrepancy / len(validation.validation_notes) if validation.validation_notes else 0
            suggestions["per_sector_adjustment"] = per_sector_adjustment
            suggestions["suggestions"].append(
                f"Distribute {validation.discrepancy:.3f}s across sectors: ~{per_sector_adjustment:.3f}s per sector"
            )
        
        return suggestions

def create_sector_validator() -> SectorTimeValidator:
    """
    Factory function to create a sector time validator.
    
    Returns:
        SectorTimeValidator instance
    """
    return SectorTimeValidator() 