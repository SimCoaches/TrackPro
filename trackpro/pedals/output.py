import ctypes
from ctypes import wintypes
import logging
import time
import os
import sys



logger = logging.getLogger(__name__)

# vJoy constants
HID_USAGE_X = 0x30
HID_USAGE_Y = 0x31
HID_USAGE_Z = 0x32

# vJoy device status (per SDK)
# 0: OWN, 1: FREE, 2: BUSY, 3: MISS
VJD_STAT_OWN = 0
VJD_STAT_FREE = 1
VJD_STAT_BUSY = 2
VJD_STAT_MISS = 3

AXIS_MIN = 0
AXIS_MAX = 65535

# vJoy scaling helper for proper range mapping
_VJOY_MIN = 0x0001
_VJOY_MAX = 0x8000  # 32768

def _to_vjoy_i16(x: float) -> int:
    """Clamp 0..1 then map to [1..32768] to satisfy vJoy/pyvjoy expected full range."""
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)
    return int(round(_VJOY_MIN + x * (_VJOY_MAX - _VJOY_MIN)))

class JOYSTICK_POSITION_V2(ctypes.Structure):
    _fields_ = [
        ('bDevice', wintypes.BYTE),
        ('wThrottle', wintypes.LONG),
        ('wRudder', wintypes.LONG),
        ('wAileron', wintypes.LONG),
        ('wAxisX', wintypes.LONG),
        ('wAxisY', wintypes.LONG),
        ('wAxisZ', wintypes.LONG),
        ('wAxisXRot', wintypes.LONG),
        ('wAxisYRot', wintypes.LONG),
        ('wAxisZRot', wintypes.LONG),
        ('wSlider', wintypes.LONG),
        ('wDial', wintypes.LONG),
        ('wWheel', wintypes.LONG),
        ('wAxisVX', wintypes.LONG),
        ('wAxisVY', wintypes.LONG),
        ('wAxisVZ', wintypes.LONG),
        ('wAxisVBRX', wintypes.LONG),
        ('wAxisVBRY', wintypes.LONG),
        ('wAxisVBRZ', wintypes.LONG),
        ('lButtons', wintypes.LONG),
        ('bHats', wintypes.DWORD),
        ('bHatsEx1', wintypes.DWORD),
        ('bHatsEx2', wintypes.DWORD),
        ('bHatsEx3', wintypes.DWORD),
    ]

class VirtualJoystick:
    """Virtual joystick output using vJoy."""
    
    def __init__(self, test_mode=False, retry_count=3, use_alt_devices=True):
        """Initialize the virtual joystick.
        
        Args:
            test_mode (bool): If True, runs in test mode without actual vJoy output
            retry_count (int): Number of times to retry acquiring a vJoy device
            use_alt_devices (bool): If True, will try alternative vJoy device IDs if primary is busy
        """
        self.test_mode = test_mode
        
        if test_mode:
            logger.info("Running in test mode - virtual joystick simulation")
            self.vjoy_device_id = 4
            self.vjoy_acquired = True
            return
            
        # Note: vJoy device name setting removed due to registry permission issues
        # The device will use the default vJoy name in Windows
        
        # Load the vJoy DLL
        self.vjoy_dll = None
        # Try to load the vJoy DLL
        self.vjoy_dll = self._find_vjoy_dll()
        
        # Check if vJoy is enabled
        if not self.vjoy_dll.vJoyEnabled():
            raise RuntimeError("vJoy is not enabled")
            
        # Default device ID
        # Prefer device 1 in production (most users have only ID 1 enabled)
        self.vjoy_device_id = 1 if getattr(sys, 'frozen', False) else 4
        self.vjoy_acquired = False
        
        # Try multiple device IDs
        # Prefer ID 1 first (production default), then fallbacks
        device_ids_to_try = [1, 4, 2, 3, 5, 6, 7, 8] if use_alt_devices else [1]
        
        # Try to acquire a vJoy device
        acquired = False
        last_error = None
        
        for device_id in device_ids_to_try:
            self.vjoy_device_id = device_id
            
            # Try multiple times to acquire this device ID
            for attempt in range(retry_count):
                try:
                    # Get device status
                    status = self.vjoy_dll.GetVJDStatus(device_id)

                    if status == VJD_STAT_OWN:
                        logger.info(f"vJoy Device {device_id} is already owned by this feeder")
                        self.vjoy_acquired = True
                        acquired = True
                        break
                    elif status == VJD_STAT_FREE:
                        if self.vjoy_dll.AcquireVJD(device_id):
                            logger.info(f"Acquired vJoy Device {device_id}")
                            self.vjoy_acquired = True
                            acquired = True
                            break
                        else:
                            last_error = f"Failed to acquire vJoy Device {device_id}"
                            logger.warning(last_error)
                    elif status == VJD_STAT_BUSY:
                        last_error = f"vJoy device {device_id} is already owned by another feeder"
                        logger.warning(last_error)
                        # Wait briefly before retrying
                        import time
                        time.sleep(0.5)
                    elif status == VJD_STAT_MISS:
                        last_error = f"vJoy device {device_id} is not installed or disabled"
                        logger.warning(last_error)
                        break  # No point retrying this device ID
                    else:
                        last_error = f"vJoy device {device_id} has unknown status: {status}"
                        logger.warning(last_error)
                except Exception as e:
                    last_error = f"Error with vJoy device {device_id}: {e}"
                    logger.warning(last_error)
            
            if acquired:
                break
        
        # If we couldn't acquire any device, fall back to test mode
        if not acquired:
            logger.warning(f"Could not acquire vJoy device: {last_error}")
            logger.info("Falling back to test mode - vJoy output will be simulated")
            self.test_mode = True
            self.vjoy_device_id = 4
            self.vjoy_acquired = False
    
    def update_axis(self, throttle: int, brake: int, clutch: int, handbrake: int = 0):
        """Update the virtual joystick axes - ULTRA-FAST VERSION.
        
        Args:
            throttle, brake, clutch, handbrake: Values in 0-65535 range from calibration
        """
        
        if self.test_mode:
            # In test mode, just log the values occasionally
            if not hasattr(self, '_test_log_count'):
                self._test_log_count = 0
            self._test_log_count += 1
            if self._test_log_count % 1000 == 0:  # Log every 1000 calls (1 second at 1000Hz)
                logger.debug(f"🎮 Test mode - Assetto detected, Axis values: T={throttle}, B={brake}, C={clutch}, H={handbrake}")
            return True
            
        if not hasattr(self, 'vjoy_acquired') or not self.vjoy_acquired:
            # Don't log errors frequently as it will slow down the pedal thread
            if not hasattr(self, '_error_log_count'):
                self._error_log_count = 0
            self._error_log_count += 1
            if self._error_log_count % 1000 == 0:  # Log error every 1000 calls
                logger.error("❌ vJoy device not acquired - cannot update axes")
            return False
            
        try:
            # Convert 0-65535 calibrated values to normalized 0.0-1.0, then apply vJoy scaling
            norm_throttle = throttle / 65535.0
            norm_brake = brake / 65535.0
            norm_clutch = clutch / 65535.0
            norm_handbrake = handbrake / 65535.0
            
            # Apply vJoy scaling to get proper range
            vjoy_throttle = _to_vjoy_i16(norm_throttle)
            vjoy_brake = _to_vjoy_i16(norm_brake)
            vjoy_clutch = _to_vjoy_i16(norm_clutch)
            vjoy_handbrake = _to_vjoy_i16(norm_handbrake)
            
            # ULTRA-FAST: Direct API calls with minimal overhead
            # Set X axis (throttle) - critical for acceleration
            if not self.vjoy_dll.SetAxis(vjoy_throttle, self.vjoy_device_id, 0x30):  # HID_USAGE_X
                return False
            
            # Set Y axis (brake) - critical for braking
            if not self.vjoy_dll.SetAxis(vjoy_brake, self.vjoy_device_id, 0x31):  # HID_USAGE_Y
                return False
            
            # Set Z axis (clutch) - less critical but still fast
            if not self.vjoy_dll.SetAxis(vjoy_clutch, self.vjoy_device_id, 0x32):  # HID_USAGE_Z
                return False
            
            # Set RX axis (handbrake) - additional axis for handbrake
            if handbrake > 0:  # Only update if handbrake value is provided
                if not self.vjoy_dll.SetAxis(vjoy_handbrake, self.vjoy_device_id, 0x33):  # HID_USAGE_RX
                    return False
            
            # CRITICAL PERFORMANCE FIX: Remove ALL performance monitoring from hot path
            # This was causing the massive performance degradation at 250Hz
            # Performance logging moved to external monitoring if needed
            
            return True
            
        except Exception as e:
            # CRITICAL: Silent error handling - no logging or counting in hot path
            # This was also causing performance degradation at 250Hz
            return False
    
    def vjoy_sweep_test(self, seconds: float = 3.0, axis="throttle"):
        """Diagnostic method to test the full range of vJoy axis movement.
        
        Args:
            seconds (float): Duration of the sweep test
            axis (str): Which axis to test ("throttle" or "brake")
        """
        if self.test_mode:
            logger.info(f"🎮 Test mode - Simulating {axis} sweep for {seconds} seconds")
            return
            
        if not hasattr(self, 'vjoy_acquired') or not self.vjoy_acquired:
            logger.error("❌ vJoy device not acquired - cannot perform sweep test")
            return
        
        logger.info(f"🔧 Starting {axis} sweep test for {seconds} seconds...")
        
        # Determine which axis to use
        axis_id = 0x30 if axis.startswith("t") else 0x31  # HID_USAGE_X for throttle, HID_USAGE_Y for brake
        
        steps = max(10, int(seconds * 60))
        for i in range(steps + 1):
            x = i / steps
            val = _to_vjoy_i16(x)
            self.vjoy_dll.SetAxis(val, self.vjoy_device_id, axis_id)
            time.sleep(seconds / steps)
        
        # Reset to 0 at the end
        self.vjoy_dll.SetAxis(_to_vjoy_i16(0.0), self.vjoy_device_id, axis_id)
        logger.info(f"✅ {axis} sweep test completed")
    
    def __del__(self):
        """Clean up vJoy device."""
        try:
            if hasattr(self, 'vjoy_dll') and self.vjoy_dll:
                self.vjoy_dll.RelinquishVJD(self.vjoy_device_id)
                logger.info("vJoy device released")
        except Exception as e:
            logger.error(f"Error cleaning up vJoy device: {e}")

    def _find_vjoy_dll(self):
        """Find the vJoy DLL path."""
        import os
        import ctypes
        
        # Try to find the vJoy SDK DLL (dev and production)
        dll_paths = [
            # Standard install locations
            r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
            r"C:\Program Files (x86)\vJoy\x86\vJoyInterface.dll",
            # Dev tree fallbacks
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "vJoyInterface.dll"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vJoyInterface.dll"),
        ]
        # PyInstaller bundle: alongside the executable
        try:
            import sys as _sys
            if getattr(_sys, 'frozen', False):
                dll_paths.insert(0, os.path.join(os.path.dirname(_sys.executable), "vJoyInterface.dll"))
        except Exception:
            pass
        
        for path in dll_paths:
            if os.path.exists(path):
                try:
                    logger.info(f"Found vJoy DLL at {path}")
                    vjoy_dll = ctypes.WinDLL(path)
                    
                    # Define function prototypes
                    vjoy_dll.vJoyEnabled.restype = ctypes.c_bool
                    vjoy_dll.vJoyEnabled.argtypes = []
                    
                    vjoy_dll.GetvJoyVersion.restype = ctypes.c_short
                    vjoy_dll.GetvJoyVersion.argtypes = []
                    
                    vjoy_dll.AcquireVJD.restype = ctypes.c_bool
                    vjoy_dll.AcquireVJD.argtypes = [ctypes.c_uint]
                    
                    vjoy_dll.GetVJDStatus.restype = ctypes.c_int
                    vjoy_dll.GetVJDStatus.argtypes = [ctypes.c_uint]
                    
                    vjoy_dll.SetAxis.restype = ctypes.c_bool
                    vjoy_dll.SetAxis.argtypes = [ctypes.c_long, ctypes.c_uint, ctypes.c_uint]
                    
                    vjoy_dll.RelinquishVJD.restype = ctypes.c_bool
                    vjoy_dll.RelinquishVJD.argtypes = [ctypes.c_uint]
                    
                    # Get vJoy version
                    version = vjoy_dll.GetvJoyVersion()
                    logger.info(f"vJoy Version: {version}")
                    
                    return vjoy_dll
                except Exception as e:
                    logger.warning(f"Error loading vJoy DLL from {path}: {e}")
        
        raise RuntimeError("vJoy DLL not found. Please make sure vJoy is installed correctly.") 