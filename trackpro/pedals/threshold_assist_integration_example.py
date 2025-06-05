"""
Example integration of Threshold Braking Assist with TrackPro

This shows how to connect the threshold braking assist system with:
- Pedal hardware input
- iRacing telemetry 
- Virtual joystick output
- UI controls
"""

import logging
import time
from .hardware_input import HardwareInput
from .output import VirtualJoystick
from ..race_coach.simple_iracing import SimpleIRacingAPI

logger = logging.getLogger(__name__)

class ThresholdAssistManager:
    """Manager class that coordinates threshold braking assist with all TrackPro systems."""
    
    def __init__(self):
        """Initialize the threshold assist manager."""
        # Initialize core systems
        self.hardware_input = HardwareInput()
        self.virtual_joystick = VirtualJoystick()
        self.iracing_api = SimpleIRacingAPI()
        
        # Connect telemetry callback
        self.hardware_input.set_telemetry_callback(self.get_current_telemetry)
        
        # Store current telemetry
        self.current_telemetry = {}
        
        # Register for telemetry updates
        self.iracing_api.register_on_telemetry_data(self.on_telemetry_update)
        self.iracing_api.register_on_connection_changed(self.on_connection_changed)
        
        logger.info("Threshold Assist Manager initialized")
    
    def get_current_telemetry(self) -> dict:
        """Get the most recent telemetry data."""
        return self.current_telemetry.copy()
    
    def on_telemetry_update(self, telemetry_data: dict):
        """Handle telemetry updates from iRacing."""
        self.current_telemetry = telemetry_data
        
        # Update track/car context for threshold learning
        track_name = telemetry_data.get('track_name', '')
        car_name = telemetry_data.get('car_name', '')
        if track_name and car_name:
            self.hardware_input.update_track_car_context(track_name, car_name)
    
    def on_connection_changed(self, is_connected: bool, session_info: dict):
        """Handle iRacing connection changes."""
        if is_connected:
            logger.info("iRacing connected - threshold assist ready")
        else:
            logger.info("iRacing disconnected - threshold assist paused")
    
    def process_pedal_inputs(self):
        """Main processing loop for pedal inputs with threshold assist."""
        # Read raw pedal values
        pedal_values = self.hardware_input.read_pedals()
        
        # Get brake value and apply calibration
        raw_brake = pedal_values.get('brake', 0)
        calibrated_brake = self.hardware_input.apply_calibration('brake', raw_brake)
        
        # Apply threshold assist if enabled
        assisted_brake = self.hardware_input.process_brake_with_assist(calibrated_brake)
        
        # Process other pedals normally
        throttle = self.hardware_input.apply_calibration('throttle', pedal_values.get('throttle', 0))
        clutch = self.hardware_input.apply_calibration('clutch', pedal_values.get('clutch', 0))
        
        # Send to virtual joystick
        self.virtual_joystick.update_axis(throttle, assisted_brake, clutch)
        
        # Log assist activity (occasionally)
        if assisted_brake != calibrated_brake:
            logger.debug(f"Threshold assist active: {calibrated_brake} -> {assisted_brake}")
    
    def enable_threshold_assist(self, enabled: bool = True):
        """Enable or disable threshold braking assist."""
        self.hardware_input.enable_threshold_assist(enabled)
    
    def set_assist_reduction(self, percentage: float):
        """Set the brake force reduction percentage (1-10%)."""
        self.hardware_input.set_threshold_reduction(percentage)
    
    def get_assist_status(self) -> dict:
        """Get current status of the threshold assist system."""
        return self.hardware_input.get_threshold_assist_status()
    
    def reset_learning(self, track_car: str = None):
        """Reset threshold learning for current or specified track/car."""
        self.hardware_input.reset_threshold_learning(track_car)
    
    def start_monitoring(self):
        """Start the main processing loop."""
        logger.info("Starting threshold assist monitoring...")
        
        # Connect to iRacing
        self.iracing_api.connect()
        
        try:
            while True:
                # Process pedal inputs with assist
                self.process_pedal_inputs()
                
                # Sleep for ~60Hz update rate
                time.sleep(1/60)
                
        except KeyboardInterrupt:
            logger.info("Stopping threshold assist monitoring...")
        finally:
            # Cleanup
            self.iracing_api.disconnect()

# Example usage functions for UI integration

def create_threshold_assist_ui_controls():
    """Example of how to create UI controls for threshold assist."""
    
    # This would be integrated into your existing UI
    # Here's the structure you'd need:
    
    ui_controls = {
        'enable_checkbox': {
            'label': 'Enable Threshold Braking Assist',
            'default': False,
            'callback': lambda enabled: manager.enable_threshold_assist(enabled)
        },
        'reduction_slider': {
            'label': 'Brake Force Reduction (%)',
            'min': 1.0,
            'max': 10.0,
            'default': 2.0,
            'callback': lambda value: manager.set_assist_reduction(value)
        },
        'status_display': {
            'label': 'Assist Status',
            'update_callback': lambda: manager.get_assist_status()
        },
        'reset_button': {
            'label': 'Reset Learning',
            'callback': lambda: manager.reset_learning()
        }
    }
    
    return ui_controls

def log_assist_performance():
    """Example of how to monitor assist performance."""
    manager = ThresholdAssistManager()
    
    while True:
        status = manager.get_assist_status()
        
        if status['enabled']:
            print(f"Threshold Assist Status:")
            print(f"  Track/Car: {status['current_context']}")
            print(f"  Learning Mode: {status['learning_mode']}")
            print(f"  Optimal Threshold: {status['optimal_threshold']:.3f}")
            print(f"  Confidence: {status['confidence']:.1%}")
            print(f"  ABS Detections: {status['detections']}")
            print(f"  Reduction: {status['reduction_percentage']:.1f}%")
        
        time.sleep(5)  # Update every 5 seconds

if __name__ == "__main__":
    # Example: Start threshold assist system
    manager = ThresholdAssistManager()
    
    # Enable with 2% brake force reduction
    manager.enable_threshold_assist(True)
    manager.set_assist_reduction(2.0)
    
    # Start monitoring
    manager.start_monitoring() 