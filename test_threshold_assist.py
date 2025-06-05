#!/usr/bin/env python3
"""
Test script for Threshold Braking Assist

This script allows you to test the threshold braking assist system
without needing to run the full TrackPro application.
"""

import sys
import os
import time
import logging

# Add the trackpro module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.pedals.hardware_input import HardwareInput
from trackpro.pedals.output import VirtualJoystick
from trackpro.pedals.threshold_braking_assist import ThresholdBrakingAssist

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ThresholdAssistTest")

class ThresholdAssistTester:
    """Test class for threshold braking assist."""
    
    def __init__(self):
        """Initialize the test environment."""
        logger.info("Initializing Threshold Braking Assist Test")
        
        # Initialize hardware (enable test_mode to allow Xbox controller)
        try:
            self.hardware = HardwareInput(test_mode=True)
            if hasattr(self.hardware, 'using_xbox_controller') and self.hardware.using_xbox_controller:
                logger.info("Hardware initialized with Xbox Controller for testing")
            elif self.hardware.pedals_connected:
                logger.info("Hardware initialized with P1 Pro Pedals")
            else:
                logger.info("Hardware initialized in test mode (no controller)")
        except Exception as e:
            logger.warning(f"Hardware initialization failed: {e}")
            self.hardware = HardwareInput(test_mode=True)
        
        # Initialize virtual joystick
        try:
            self.output = VirtualJoystick(test_mode=False)
            logger.info("Virtual joystick initialized successfully")
        except Exception as e:
            logger.warning(f"Virtual joystick initialization failed, using test mode: {e}")
            self.output = VirtualJoystick(test_mode=True)
        
        # Create mock telemetry data generator
        self.mock_abs_active = False
        self.mock_brake_pressure = 0.0
        self.test_track = "Watkins Glen International"
        self.test_car = "Formula Vee"
        
        # Set up telemetry callback
        self.hardware.set_telemetry_callback(self.get_mock_telemetry)
        
        # Set track/car context
        self.hardware.update_track_car_context(self.test_track, self.test_car)
        
        # Configure threshold assist
        self.hardware.enable_threshold_assist(True)
        self.hardware.set_threshold_reduction(2.0)  # 2% reduction
        
        logger.info("Threshold Braking Assist Test initialized")
    
    def get_mock_telemetry(self):
        """Generate mock telemetry data for testing."""
        return {
            'BrakeABSactive': self.mock_abs_active,
            'Brake': self.mock_brake_pressure,
            'track_name': self.test_track,
            'car_name': self.test_car,
            'Speed': 120.5,  # km/h
            'RPM': 6500
        }
    
    def simulate_abs_lockup(self, brake_value):
        """Simulate ABS activation based on brake value."""
        # Simulate ABS activation when brake exceeds 85%
        if brake_value > 0.85:
            self.mock_abs_active = True
            self.mock_brake_pressure = brake_value
            logger.info(f"🚨 SIMULATED ABS ACTIVATION at brake={brake_value:.3f}")
        else:
            self.mock_abs_active = False
            self.mock_brake_pressure = brake_value
    
    def run_interactive_test(self):
        """Run an interactive test session."""
        logger.info("Starting interactive threshold assist test")
        logger.info("Commands:")
        logger.info("  'enable' / 'disable' - Toggle threshold assist")
        logger.info("  'reduction X' - Set reduction percentage (e.g., 'reduction 3')")
        logger.info("  'status' - Show current assist status")
        logger.info("  'reset' - Reset learning data")
        logger.info("  'test' - Run automated test sequence")
        logger.info("  'quit' - Exit test")
        
        while True:
            try:
                # Read pedal values
                pedal_values = self.hardware.read_pedals()
                
                # Get brake value and apply calibration
                raw_brake = pedal_values.get('brake', 0)
                calibrated_brake = self.hardware.apply_calibration('brake', raw_brake)
                
                # Convert to 0.0-1.0 range for simulation
                brake_percent = calibrated_brake / 65535.0
                
                # Simulate ABS based on brake pressure
                self.simulate_abs_lockup(brake_percent)
                
                # Apply threshold assist
                assisted_brake = self.hardware.process_brake_with_assist(calibrated_brake)
                
                # Process other pedals normally
                throttle = self.hardware.apply_calibration('throttle', pedal_values.get('throttle', 0))
                clutch = self.hardware.apply_calibration('clutch', pedal_values.get('clutch', 0))
                
                # Send to virtual joystick (scale to vJoy range)
                throttle_vjoy = int(throttle * 32767 / 65535)
                brake_vjoy = int(assisted_brake * 32767 / 65535)
                clutch_vjoy = int(clutch * 32767 / 65535)
                
                self.output.update_axis(throttle_vjoy, brake_vjoy, clutch_vjoy)
                
                # Show assist activity
                if assisted_brake != calibrated_brake:
                    reduction = calibrated_brake - assisted_brake
                    reduction_percent = (reduction / calibrated_brake) * 100 if calibrated_brake > 0 else 0
                    logger.info(f"🎯 ASSIST ACTIVE: {calibrated_brake} -> {assisted_brake} "
                               f"(reduced by {reduction_percent:.1f}%)")
                
                # Check for user input (non-blocking) - Cross-platform
                command = None
                try:
                    import msvcrt
                    # Windows method
                    if msvcrt.kbhit():
                        command = input().strip().lower()
                except ImportError:
                    # Unix method
                    import select
                    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                        command = input().strip().lower()
                
                if command:
                    
                    if command == 'quit':
                        break
                    elif command == 'enable':
                        self.hardware.enable_threshold_assist(True)
                        logger.info("✅ Threshold assist ENABLED")
                    elif command == 'disable':
                        self.hardware.enable_threshold_assist(False)
                        logger.info("❌ Threshold assist DISABLED")
                    elif command.startswith('reduction '):
                        try:
                            percentage = float(command.split()[1])
                            self.hardware.set_threshold_reduction(percentage)
                            logger.info(f"🎚️ Reduction set to {percentage}%")
                        except (IndexError, ValueError):
                            logger.error("Invalid reduction command. Use: reduction X")
                    elif command == 'status':
                        status = self.hardware.get_threshold_assist_status()
                        logger.info(f"📊 Status: {status}")
                    elif command == 'reset':
                        self.hardware.reset_threshold_learning()
                        logger.info("🔄 Learning data reset")
                    elif command == 'test':
                        self.run_automated_test()
                    else:
                        logger.info("Unknown command")
                
                # Sleep for smooth operation
                time.sleep(1/60)  # 60 FPS
                
            except KeyboardInterrupt:
                logger.info("Test interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error during test: {e}")
    
    def run_automated_test(self):
        """Run an automated test sequence."""
        logger.info("🤖 Starting automated test sequence...")
        
        # Test 1: Learning phase
        logger.info("Test 1: Learning phase - simulating brake lockups")
        self.hardware.reset_threshold_learning()
        
        # Simulate progressive brake applications with lockup
        test_brake_values = [0.7, 0.8, 0.87, 0.9, 0.85, 0.88, 0.86]
        
        for i, brake_val in enumerate(test_brake_values):
            logger.info(f"Simulating brake application {i+1}: {brake_val:.3f}")
            
            # Convert to 16-bit range
            brake_16bit = int(brake_val * 65535)
            
            # Simulate ABS if over threshold
            self.simulate_abs_lockup(brake_val)
            
            # Process with assist
            assisted_brake = self.hardware.process_brake_with_assist(brake_16bit)
            
            # Show results
            if assisted_brake != brake_16bit:
                reduction = (brake_16bit - assisted_brake) / brake_16bit * 100
                logger.info(f"  ➜ Assist applied: {brake_val:.3f} -> {assisted_brake/65535:.3f} "
                           f"(reduced by {reduction:.1f}%)")
            else:
                logger.info(f"  ➜ No assist needed: {brake_val:.3f}")
            
            time.sleep(0.5)
        
        # Show learning status
        status = self.hardware.get_threshold_assist_status()
        logger.info(f"Learning complete: {status}")
        
        # Test 2: Assist phase
        logger.info("Test 2: Assist phase - testing learned threshold")
        
        test_values = [0.5, 0.7, 0.83, 0.9, 0.95]  # Include values above learned threshold
        
        for brake_val in test_values:
            brake_16bit = int(brake_val * 65535)
            assisted_brake = self.hardware.process_brake_with_assist(brake_16bit)
            
            if assisted_brake != brake_16bit:
                reduction = (brake_16bit - assisted_brake) / brake_16bit * 100
                logger.info(f"🎯 {brake_val:.3f} -> {assisted_brake/65535:.3f} "
                           f"(reduced by {reduction:.1f}%)")
            else:
                logger.info(f"✅ {brake_val:.3f} -> {brake_val:.3f} (no assist needed)")
            
            time.sleep(0.3)
        
        logger.info("🏁 Automated test sequence complete!")
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up test environment...")
        
        # Clean up hardware
        if hasattr(self.hardware, 'cleanup'):
            self.hardware.cleanup()
        
        # Clean up output
        if hasattr(self.output, '__del__'):
            del self.output

def main():
    """Main test function."""
    logger.info("🏁 Threshold Braking Assist Test Script")
    logger.info("=" * 50)
    
    tester = None
    try:
        # Create tester
        tester = ThresholdAssistTester()
        
        # Check if we should run automated test
        if len(sys.argv) > 1 and sys.argv[1] == '--auto':
            tester.run_automated_test()
        else:
            # Run interactive test
            tester.run_interactive_test()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if tester:
            tester.cleanup()
        logger.info("Test script finished")

if __name__ == "__main__":
    main() 