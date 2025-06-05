import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RealTimeData:
    """Data structure for advanced ABS-style brake pressure management"""
    # Current brake pressure management
    current_reduction: float = 0.0  # Current active reduction (0.0 = no reduction, 0.18 = 18% reduction)
    last_brake_input: float = 0.0
    
    # ABS state machine
    abs_state: str = "READY"  # READY → LOCKUP_DETECTED → PRESSURE_DROP → RECOVERY → THRESHOLD
    
    # Lockup detection and recording
    lockup_pressure: float = 0.0  # Exact pressure where lockup occurred
    target_threshold: float = 0.0  # Target threshold pressure (97% of lockup)
    lockup_detected_time: float = 0.0
    lockup_count: int = 0  # Total lockups detected
    consecutive_lockups: int = 0  # Consecutive lockups without brake release
    
    # Recovery parameters
    pressure_recovery_rate: float = 0.005  # How fast to restore pressure per update
    lockup_reduction_amount: float = 0.18  # Base reduction when lockup detected (18%)
    min_recovery_time: float = 0.2  # Minimum time before starting recovery
    
    # Tire state tracking
    last_lockup_time: float = 0.0
    threshold_found: bool = False
    last_successful_brake: float = 0.0

class RealTimeBrakingAssist:
    """
    Real-Time Braking Assist System
    
    Instead of learning thresholds, this system detects lockup in real-time
    and immediately reduces brake pressure to restore wheel rotation,
    then gradually allows pressure recovery.
    
    Perfect for high downforce cars where optimal braking changes with speed.
    """
    
    def __init__(self, lockup_reduction=10.0, recovery_rate=1.0):
        # Threshold assist parameters
        self.lockup_reduction = lockup_reduction  # Percentage to reduce brake when lockup detected
        self.recovery_rate = recovery_rate  # Percentage per second to recover
        self.enabled = True
        
        # State tracking
        self.is_reducing = False
        self.current_reduction = 0.0
        self.last_update_time = time.time()
        
        # Missing attributes that were causing crashes
        self.lockup_count = 0
        self.previous_accel = 0.0
        self.consecutive_lockups = 0  # Track consecutive lockups for safety
        
        # CRITICAL: Add missing threshold tracking attributes
        self.safe_brake_threshold = 1.0  # Default to full brake initially
        
        # ABS-STYLE PUMP ACTION STATE MACHINE
        self.pump_state = "TESTING"  # TESTING -> RELEASING -> RE_APPLYING -> MAINTAINING
        self.pump_start_time = 0.0
        self.release_pressure = 0.3  # Drop to 30% when lockup detected
        self.release_duration = 0.3  # Hold low pressure for 300ms
        self.reapply_duration = 0.5  # Take 500ms to re-apply to safe level
        self.lockup_brake_level = 1.0  # Where lockup occurred
        
        # Lockup detection parameters (AUTOMATIC ONLY - no manual input) - TESTING MODE
        self.lockup_decel_threshold = -6.0  # m/s² - LOWERED for easier testing
        self.lockup_detection_min_speed = 3.0  # m/s - LOWERED for easier testing
        self.lockup_detection_min_brake = 0.2  # LOWERED - assist at 20% brake for testing
        
        # Learning system - REACTIVE MODE (cleared for fresh start)
        self.lockup_history = {}  # Dict[context, List[brake_levels]]
        self.learned_thresholds = {}  # Dict[context, threshold]
        self.current_context = "default"  # Will be track_car combination
        self.current_track_car = "default"
        
        # Real-time data tracking for different track/car combinations
        self.realtime_data = {}  # Dict[track_car, RealTimeData]
        
        # Clear any existing learned data for fresh testing
        self.reset_learned_data()
        
        # Brake efficiency tracking for lockup detection
        self.brake_efficiency_history = []
        self.max_efficiency_samples = 10
        
        logger.info(f"🚀 RealTimeBrakingAssist initialized: {lockup_reduction}% reduction, {recovery_rate}%/sec recovery - REACTIVE MODE")
    
    def reset_learned_data(self):
        """Reset all learned thresholds for fresh testing"""
        self.lockup_history.clear()
        self.learned_thresholds.clear()
        self.current_reduction = 0.0
        self.is_reducing = False
        logger.info("🧹 TESTING: Cleared all learned brake thresholds")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the assist system."""
        self.enabled = enabled
        logger.info(f"Real-Time Braking Assist {'enabled' if enabled else 'disabled'}")
    
    def set_lockup_reduction(self, percentage: float):
        """Set the immediate reduction percentage when lockup detected."""
        self.lockup_reduction = percentage / 100.0
        logger.info(f"Lockup reduction set to {percentage}%")
    
    def set_recovery_rate(self, rate: float):
        """Set the pressure recovery rate (% per second)."""
        self.recovery_rate = rate / 100.0
        logger.info(f"Pressure recovery rate set to {rate}%/s")
    
    def set_track_car_context(self, track_name: str, car_name: str):
        """Set the current track/car combination."""
        self.current_track_car = f"{track_name}_{car_name}"
        
        if self.current_track_car not in self.realtime_data:
            self.realtime_data[self.current_track_car] = RealTimeData()
            self.realtime_data[self.current_track_car].lockup_reduction_amount = self.lockup_reduction
            self.realtime_data[self.current_track_car].pressure_recovery_rate = self.recovery_rate / 50.0  # Per update cycle
            logger.info(f"Created real-time brake data for {self.current_track_car}")
    
    def process_brake_input(self, raw_brake_input: float, telemetry: Dict) -> float:
        """
        Process brake input with ABS-style pump action.
        This method now calls apply_assist() which contains the new pump logic.
        """
        return self.apply_assist(raw_brake_input, telemetry)
    
    def _detect_automatic_lockup(self, telemetry: Dict) -> bool:
        """
        ADVANCED tire lockup detection using multiple physics-based methods.
        
        Key insight: Locked tires behave very differently than rolling tires:
        1. Rolling tires: Deceleration proportional to brake pressure (linear relationship)
        2. Locked tires: Deceleration plateaus/decreases despite more brake pressure
        3. Transition point: Where efficiency drops dramatically
        """
        if not telemetry:
            return False
            
        # Get telemetry data
        speed = telemetry.get('Speed', 0)  # m/s
        long_accel = telemetry.get('LongAccel', 0)  # m/s² (negative = deceleration)
        brake = telemetry.get('Brake', 0)  # 0.0-1.0
        abs_active = telemetry.get('BrakeABSactive', False)
        
        # Don't detect at very low speeds (lockup doesn't matter much)
        if speed < self.lockup_detection_min_speed:
            return False
        
        # Don't detect at low brake pressures
        if brake < self.lockup_detection_min_brake:
            return False
        
        # METHOD 1: iRacing's built-in ABS detection (100% reliable when available)
        if abs_active:
            logger.debug(f"🚨 iRACING ABS: speed={speed:.1f}m/s")
            return True
        
        # Store history for trend analysis
        if not hasattr(self, 'decel_history'):
            self.decel_history = []
            self.brake_history = []
            self.efficiency_history = []
            self.previous_accel = 0
        
        # METHOD 2: Brake efficiency analysis (key physics indicator)
        # Rolling tires: More brake pressure = more deceleration (good efficiency)
        # Locked tires: More brake pressure = same/less deceleration (poor efficiency)
        max_theoretical_decel = -15.0  # Theoretical max deceleration for racing tires
        current_efficiency = abs(long_accel) / (brake * abs(max_theoretical_decel)) if brake > 0 else 0
        
        # Track efficiency over time
        self.efficiency_history.append(current_efficiency)
        self.decel_history.append(long_accel)
        self.brake_history.append(brake)
        
        # Keep only recent samples
        if len(self.efficiency_history) > 10:
            self.efficiency_history.pop(0)
            self.decel_history.pop(0)
            self.brake_history.pop(0)
        
        # METHOD 3: Efficiency drop detection (most accurate for threshold)
        if len(self.efficiency_history) >= 3:
            recent_efficiency = sum(self.efficiency_history[-3:]) / 3
            
            # Locked tire indicators:
            # 1. High brake pressure but poor efficiency
            # 2. Efficiency below 70% (locked tires waste energy)
            if brake > 0.5 and recent_efficiency < 0.7 and abs(long_accel) > 8.0:
                logger.debug(f"🚨 EFFICIENCY LOCKUP: brake={brake:.3f}, efficiency={recent_efficiency:.2f}, decel={long_accel:.1f}")
                return True
        
        # METHOD 4: Deceleration plateau detection
        # Rolling tires: More pressure = more deceleration
        # Locked tires: Deceleration plateaus despite increasing pressure
        if len(self.brake_history) >= 5:
            # Check if brake pressure increased but deceleration didn't improve
            brake_trend = self.brake_history[-1] - self.brake_history[-3]  # Pressure change
            decel_trend = self.decel_history[-1] - self.decel_history[-3]  # Decel change
            
            # If brake increased significantly but deceleration got worse = lockup
            if brake_trend > 0.1 and decel_trend > -1.0 and brake > 0.6:
                logger.debug(f"🚨 PLATEAU LOCKUP: brake+{brake_trend:.2f}, decel+{decel_trend:.1f}")
                return True
        
        # METHOD 5: Sudden deceleration spike (rapid lockup)
        decel_change = long_accel - self.previous_accel
        self.previous_accel = long_accel
        
        # Massive sudden deceleration change indicates instant lockup
        if decel_change < -8.0 and brake > 0.4:
            logger.debug(f"🚨 SPIKE LOCKUP: decel spike {decel_change:.1f} m/s² at brake={brake:.3f}")
            return True
        
        # METHOD 6: Physics impossibility check
        # If deceleration exceeds what's physically possible for rolling tires
        max_rolling_decel = -13.0  # Max deceleration for rolling racing tires
        if long_accel < max_rolling_decel and brake > 0.5:
            logger.debug(f"🚨 PHYSICS LOCKUP: impossible decel {long_accel:.1f} m/s² (max rolling: {max_rolling_decel})")
            return True
        
        return False
    
    def _handle_realtime_lockup(self, brake_input: float, current_time: float, data: RealTimeData, telemetry: Dict):
        """
        Handle lockup detection with minimal pressure reduction to stay at threshold.
        """
        # Check if this is a new lockup (not rapid-fire detection)
        time_since_last_lockup = current_time - data.last_lockup_time
        if time_since_last_lockup < 0.1:  # Ignore lockups within 100ms of each other
            return
        
        data.last_lockup_time = current_time
        data.lockup_detected_time = current_time
        data.consecutive_lockups += 1
        
        # CONSERVATIVE reduction - just enough to get below lockup point
        base_reduction = data.lockup_reduction_amount  # Default 5%
        
        # Only increase reduction slightly for repeated lockups
        if data.consecutive_lockups > 1:
            # Each additional lockup adds just 1% more reduction
            adaptive_reduction = base_reduction + (0.01 * (data.consecutive_lockups - 1))
            adaptive_reduction = min(adaptive_reduction, 0.12)  # Cap at 12% total
            logger.info(f"🔄 Consecutive lockup #{data.consecutive_lockups}: micro-adjustment to {adaptive_reduction*100:.1f}%")
        else:
            adaptive_reduction = base_reduction
        
        # Apply minimal reduction - we want to stay RIGHT at the threshold
        data.current_reduction = max(data.current_reduction, adaptive_reduction)
        data.threshold_found = True  # We've found where lockup occurs
        
        speed_mph = telemetry.get('Speed', 0) * 2.237  # Convert m/s to mph for logging
        logger.info(f"⚡ MINIMAL LOCKUP CORRECTION: {brake_input:.3f} -> reducing by {adaptive_reduction*100:.1f}% "
                   f"(speed: {speed_mph:.0f}mph) - staying at threshold!")
    
    def _update_pressure_recovery(self, data: RealTimeData, raw_brake_input: float, current_time: float):
        """
        Intelligently recover brake pressure to creep back to threshold.
        """
        if data.current_reduction <= 0:
            return
        
        time_since_lockup = current_time - data.lockup_detected_time
        
        # Wait minimum time before starting recovery
        if time_since_lockup < data.min_recovery_time:
            return
        
        # Reset system if brake has been released significantly
        if raw_brake_input < 0.2:
            data.consecutive_lockups = 0
            data.current_reduction = 0
            data.threshold_found = False
            data.last_successful_brake = 0.0
            logger.debug("Brake released - resetting threshold system")
            return
        
        # Store the last successful brake value (current effective brake)
        effective_brake = raw_brake_input * (1.0 - data.current_reduction)
        data.last_successful_brake = effective_brake
        
        # VERY gradual pressure recovery - creep back to threshold
        # Slower recovery means we stay closer to optimal threshold
        recovery_amount = data.pressure_recovery_rate  # 0.5% per update
        data.current_reduction = max(0, data.current_reduction - recovery_amount)
        
        if data.current_reduction <= 0.005:  # Less than 0.5% reduction
            data.current_reduction = 0
            logger.debug(f"Threshold found: {data.last_successful_brake:.3f} - ready for next threshold hunt")
    
    def _apply_realtime_reduction(self, raw_brake_input: float, data: RealTimeData) -> float:
        """
        Apply minimal pressure reduction to stay at threshold.
        """
        if data.current_reduction <= 0:
            return raw_brake_input
        
        # Apply minimal reduction
        reduced_brake = raw_brake_input * (1.0 - data.current_reduction)
        
        # Much more conservative minimum limits - we want maximum braking performance
        if raw_brake_input > 0.9:
            reduced_brake = max(reduced_brake, 0.85)  # Never reduce below 85% when driver wants 90%+
        elif raw_brake_input > 0.8:
            reduced_brake = max(reduced_brake, 0.75)  # Never reduce below 75% when driver wants 80%+
        elif raw_brake_input > 0.6:
            reduced_brake = max(reduced_brake, 0.55)  # Never reduce below 55% when driver wants 60%+
        
        return reduced_brake
    
    def manual_lockup_detected(self, brake_input: float):
        """
        DEPRECATED: Manual lockup detection removed.
        Drivers need to focus on driving, not pressing buttons!
        The system now uses only automatic detection via telemetry.
        """
        logger.warning("⚠️  Manual lockup detection is DISABLED - drivers need to focus on driving!")
        logger.warning("⚠️  System uses automatic detection only via telemetry analysis")
    
    def get_status(self) -> Dict:
        """Get current status including ABS state and advanced brake analysis."""
        # Get current track/car data
        if self.current_track_car not in self.realtime_data:
            return {
                'enabled': self.enabled,
                'abs_state': 'READY',
                'lockup_count': 0,
                'current_reduction': 0.0,
                'target_threshold': 0.0,
                'brake_efficiency': 1.0,
                'context': self.current_track_car,
                'learned_contexts': 0
            }
        
        data = self.realtime_data[self.current_track_car]
        
        # Calculate current brake efficiency if we have history
        current_efficiency = 1.0
        if hasattr(self, 'efficiency_history') and self.efficiency_history:
            current_efficiency = self.efficiency_history[-1] if self.efficiency_history else 1.0
        
        return {
            'enabled': self.enabled,
            'abs_state': data.abs_state,
            'lockup_count': data.lockup_count,
            'lockup_pressure': data.lockup_pressure,
            'target_threshold': data.target_threshold,
            'current_reduction': data.current_reduction * 100,  # Convert to percentage
            'brake_efficiency': current_efficiency,
            'consecutive_lockups': data.consecutive_lockups,
            'context': self.current_track_car,
            'learned_contexts': len(self.realtime_data),
            'threshold_found': data.threshold_found
        }
    
    def reset_reductions(self, track_car: Optional[str] = None):
        """Reset all active reductions."""
        target = track_car or self.current_track_car
        if target in self.realtime_data:
            self.realtime_data[target].current_reduction = 0
            self.realtime_data[target].consecutive_lockups = 0
            logger.info(f"Reset active reductions for {target}")
    
    def export_settings(self) -> Dict:
        """Export settings for saving."""
        return {
            'enabled': self.enabled,
            'lockup_reduction': self.lockup_reduction * 100,
            'recovery_rate': self.recovery_rate * 100,
            'lockup_decel_threshold': self.lockup_decel_threshold,
            'lockup_detection_min_speed': self.lockup_detection_min_speed,
            'lockup_detection_min_brake': self.lockup_detection_min_brake
        }
    
    def import_settings(self, settings: Dict):
        """Import settings from saved data."""
        self.enabled = settings.get('enabled', False)
        self.lockup_reduction = settings.get('lockup_reduction', 25.0) / 100.0
        self.recovery_rate = settings.get('recovery_rate', 2.0) / 100.0
        self.lockup_decel_threshold = settings.get('lockup_decel_threshold', -10.8)
        self.lockup_detection_min_speed = settings.get('lockup_detection_min_speed', 5.0)
        self.lockup_detection_min_brake = settings.get('lockup_detection_min_brake', 0.3)
        
        logger.info(f"Imported real-time braking assist settings")

    def _record_lockup(self, brake_level: float):
        """
        Learn from lockup: Record brake level where lockup occurred.
        Set safe threshold to be slightly below this level.
        """
        # Initialize history for this context
        if self.current_context not in self.lockup_history:
            self.lockup_history[self.current_context] = []
        
        # Record this lockup
        self.lockup_history[self.current_context].append(brake_level)
        
        # Keep only recent lockups (last 10)
        if len(self.lockup_history[self.current_context]) > 10:
            self.lockup_history[self.current_context] = self.lockup_history[self.current_context][-10:]
        
        # Calculate safe threshold - 5% below average recent lockup level
        recent_lockups = self.lockup_history[self.current_context]
        if len(recent_lockups) >= 1:
            avg_lockup_level = sum(recent_lockups) / len(recent_lockups)
            new_threshold = avg_lockup_level * 0.95  # 5% safety margin
            
            # Only lower the threshold, never raise it (be conservative)
            if new_threshold < self.safe_brake_threshold:
                old_threshold = self.safe_brake_threshold
                self.safe_brake_threshold = new_threshold
                self.learned_thresholds[self.current_context] = new_threshold
                
                logger.info(f"🧠 LEARNED: Threshold {old_threshold:.3f} → {new_threshold:.3f} (based on {len(recent_lockups)} lockups)")
            else:
                logger.info(f"🧠 LEARNING: Threshold {self.safe_brake_threshold:.3f} maintained (lockup at {brake_level:.3f})")
    
    def apply_assist(self, raw_brake_input: float, telemetry: Dict) -> float:
        """
        IMPROVED ABS-Style Brake Pressure Management System
        
        Phase 1: Apply user input IMMEDIATELY (no delays)
        Phase 2: ADVANCED lockup detection using multiple physics methods
        Phase 3: Minimal pressure drop to stay RIGHT at threshold
        Phase 4: SMART recovery using rolling tire detection
        Phase 5: Maintain optimal threshold pressure for maximum braking
        """
        current_time = time.time()
        
        # Get current track/car context data
        if self.current_track_car not in self.realtime_data:
            self.set_track_car_context("Unknown_Track", "Unknown_Car")
        
        data = self.realtime_data[self.current_track_car]
        
        # Track our ACTUAL output pressure for accurate detection
        # This is crucial because telemetry shows user input, not our modified output
        actual_output_pressure = raw_brake_input * (1.0 - data.current_reduction)
        
        # Create modified telemetry with our actual output pressure for detection
        modified_telemetry = telemetry.copy()
        modified_telemetry['Brake'] = actual_output_pressure
        
        # Calculate current brake efficiency for status display
        speed = telemetry.get('Speed', 0)
        long_accel = telemetry.get('LongAccel', 0)
        current_efficiency = self._calculate_brake_efficiency(raw_brake_input, long_accel)
        
        # PHASE 1: Immediate application - ZERO delay
        if not self.enabled or raw_brake_input < 0.05:
            # Reset state when not braking
            data.current_reduction = 0.0
            data.abs_state = "READY"
            data.consecutive_lockups = 0
            return raw_brake_input
        
        # PHASE 2: ADVANCED lockup detection using ACTUAL output pressure
        is_locked = self._detect_automatic_lockup(modified_telemetry)
        is_rolling = self._detect_tires_rolling(modified_telemetry)
        
        # State machine with improved logic
        if data.abs_state == "READY":
            if is_locked:
                # LOCKUP DETECTED - Record exact pressure
                data.abs_state = "LOCKUP_DETECTED"
                data.lockup_pressure = raw_brake_input
                data.lockup_detected_time = current_time
                data.lockup_count += 1
                data.consecutive_lockups += 1
                
                # Calculate adaptive reduction based on lockup count
                base_reduction = 0.18  # Start with 18%
                adaptive_reduction = min(base_reduction + (data.consecutive_lockups - 1) * 0.02, 0.25)  # Max 25%
                
                data.current_reduction = adaptive_reduction
                data.target_threshold = data.lockup_pressure * 0.97  # 97% of lockup pressure
                
                speed_mph = speed * 2.237
                logger.info(f"🚨 LOCKUP #{data.lockup_count}: EXACT pressure {data.lockup_pressure:.3f} recorded! (Speed: {speed_mph:.0f}mph)")
                logger.info(f"⚡ EMERGENCY DROP: {data.lockup_pressure:.3f} → {raw_brake_input * (1-adaptive_reduction):.3f} (-{adaptive_reduction*100:.1f}%) Target threshold: {data.target_threshold:.3f}")
                
                data.abs_state = "PRESSURE_DROP"
        
        elif data.abs_state == "PRESSURE_DROP":
            # Stay in pressure drop for minimum time
            if current_time - data.lockup_detected_time > 0.2:  # 200ms minimum
                if is_rolling and not is_locked:
                    # Wheels are rolling again - start recovery
                    data.abs_state = "RECOVERY"
                    logger.info("✅ WHEELS ROLLING: Starting recovery to threshold " + f"{data.target_threshold:.3f}")
                elif current_time - data.lockup_detected_time > 0.4:  # Force recovery after 400ms
                    data.abs_state = "RECOVERY"
                    logger.warning("⚠️  FORCED RECOVERY: Moving to recovery phase after 200ms")
        
        elif data.abs_state == "RECOVERY":
            if is_locked:
                # Lockup during recovery - restart cycle
                data.abs_state = "LOCKUP_DETECTED"
                data.lockup_detected_time = current_time
                data.consecutive_lockups += 1
                logger.warning("🔄 LOCKUP DURING RECOVERY: Restarting ABS cycle")
            else:
                # Gradually increase pressure towards threshold
                effective_pressure = raw_brake_input * (1.0 - data.current_reduction)
                
                if effective_pressure < data.target_threshold:
                    # Reduce the reduction (increase pressure)
                    data.current_reduction *= 0.95  # 5% reduction decrease per update
                    
                    if data.current_reduction < 0.02:  # Within 2% of target
                        data.abs_state = "THRESHOLD"
                        logger.info(f"🎯 THRESHOLD REACHED: Maintaining {data.target_threshold:.3f} (97% of lockup)")
        
        elif data.abs_state == "THRESHOLD":
            if is_locked:
                # At threshold but still locking - reduce slightly
                data.target_threshold *= 0.99  # Reduce threshold by 1%
                data.current_reduction += 0.01  # Add 1% more reduction
                logger.warning(f"🔧 THRESHOLD ADJUSTMENT: Lowering to {data.target_threshold:.3f}")
            elif current_efficiency > 0.85 and is_rolling:
                # Good efficiency and rolling - try to increase threshold
                data.target_threshold *= 1.005  # Increase threshold by 0.5%
                data.current_reduction = max(0, data.current_reduction - 0.005)
            
            # Maintain threshold pressure
            target_reduction = 1.0 - (data.target_threshold / raw_brake_input) if raw_brake_input > 0 else 0
            data.current_reduction = max(0, min(target_reduction, 0.3))  # Cap at 30% reduction
        
        # Apply the calculated reduction
        final_pressure = raw_brake_input * (1.0 - data.current_reduction)
        
        # Safety limits
        final_pressure = max(final_pressure, 0.0)
        final_pressure = min(final_pressure, 1.0)
        
        # Store current state for next iteration
        data.last_brake_input = raw_brake_input
        
        return final_pressure

    def _detect_tires_rolling(self, telemetry: Dict) -> bool:
        """
        CONSERVATIVE tire rolling detection - only return True when we're SURE tires are rolling.
        
        The key insight: Locked tires vs Rolling tires have very different characteristics:
        - Rolling: Brake pressure produces proportional, smooth deceleration
        - Locked: Erratic deceleration, poor brake efficiency, sliding behavior
        
        BE CONSERVATIVE: When in doubt, assume tires are still locked.
        """
        if not telemetry:
            return False  # Conservative: assume locked if no data
            
        speed = telemetry.get('Speed', 0) * 2.237  # Convert to mph
        long_accel = telemetry.get('LongAccel', 0)  # m/s²
        brake = telemetry.get('Brake', 0)
        abs_active = telemetry.get('BrakeABSactive', False)
        
        # If iRacing's ABS is active, definitely not rolling smoothly
        if abs_active:
            return False
        
        # If very low speed, be extremely conservative
        if speed < 5.0:  # Under 5 mph
            # Only consider rolling if barely any brake pressure
            return brake < 0.15 and abs(long_accel) < 2.0
        
        # If no meaningful brake pressure, assume rolling
        if brake < 0.05:
            return True
            
        # **KEY: CONSERVATIVE BRAKE EFFICIENCY CHECK**
        # Rolling tires: Good efficiency (brake pressure → proportional deceleration)
        # Locked tires: Poor efficiency (more brake ≠ more deceleration)
        
        if brake > 0.2:  # Only check efficiency with meaningful brake pressure
            # Expected deceleration for rolling tires at this brake pressure
            max_possible_decel = 11.0  # m/s² realistic max for most cars
            expected_decel_rolling = brake * max_possible_decel * 0.75  # 75% efficiency expected for rolling
            actual_decel = abs(long_accel)
            
            # Calculate efficiency ratio
            efficiency = actual_decel / (brake * max_possible_decel) if brake > 0.1 else 0.0
            
            # CONSERVATIVE THRESHOLDS:
            # Only declare "rolling" if efficiency is clearly good
            if efficiency > 0.55:  # Good efficiency = rolling
                # Double-check: deceleration should be reasonably close to expected
                if actual_decel >= expected_decel_rolling * 0.7:  # Within 30% of expected
                    return True
            
            # If efficiency is poor, definitely locked
            if efficiency < 0.35:
                return False
        
        # **CONSERVATIVE DEFAULT**: If we can't clearly determine, assume still locked
        # This prevents premature recovery and repeated lockup cycles
        return False

    def _calculate_brake_efficiency(self, brake: float, long_accel: float) -> float:
        """
        Calculate current brake efficiency (how well brake pressure converts to deceleration).
        
        Perfect efficiency = 1.0 (all brake pressure converts to deceleration)
        Poor efficiency < 0.7 (locked tires waste energy)
        """
        if brake <= 0:
            return 1.0  # No braking = perfect efficiency
        
        # Theoretical maximum deceleration with perfect tires
        max_theoretical = -15.0  # Racing tires theoretical limit
        expected_decel = brake * abs(max_theoretical)
        
        # Calculate efficiency
        if expected_decel > 0:
            efficiency = abs(long_accel) / expected_decel
            return min(efficiency, 1.0)  # Cap at 100%
        
        return 1.0

# Keep the old class for compatibility but mark as deprecated
class ThresholdBrakingAssist(RealTimeBrakingAssist):
    """DEPRECATED: Use RealTimeBrakingAssist instead."""
    
    def __init__(self, reduction_percentage: float = 25.0, learning_rate: float = 2.0):
        logger.warning("ThresholdBrakingAssist is deprecated - using RealTimeBrakingAssist instead")
        super().__init__(lockup_reduction=reduction_percentage, recovery_rate=learning_rate)
        
        # Map old methods to new ones for compatibility
        self.set_reduction_percentage = self.set_lockup_reduction
        self.process_brake_input = super().process_brake_input 