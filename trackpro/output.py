import ctypes
from ctypes import wintypes
import logging
import time
import os
import winreg

logger = logging.getLogger(__name__)

# vJoy constants
HID_USAGE_X = 0x30
HID_USAGE_Y = 0x31
HID_USAGE_Z = 0x32
VJD_STAT_FREE = 0
VJD_STAT_OWN = 1
VJD_STAT_BUSY = 2
VJD_STAT_MISS = 3
AXIS_MIN = 0
AXIS_MAX = 65535

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
    
    def __init__(self, test_mode=False):
        """Initialize the virtual joystick."""
        self.test_mode = test_mode
        
        if test_mode:
            logger.info("Running in test mode - virtual joystick simulation")
            self.vjoy_device_id = 1
            self.vjoy_acquired = True
            return
            
        # Try to set the device name
        try:
            # Set the device name to make it easier to identify in games
            import win32api
            import win32con
            
            # Open the registry key
            key_path = r"SYSTEM\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_1234&PID_BEAD"
            try:
                key = win32api.RegOpenKeyEx(win32con.HKEY_LOCAL_MACHINE, key_path, 0, win32con.KEY_SET_VALUE)
                win32api.RegSetValueEx(key, "OEMName", 0, win32con.REG_SZ, "TrackPro Virtual Pedals")
                win32api.RegCloseKey(key)
                logger.info("Set vJoy device name to 'TrackPro Virtual Pedals'")
            except Exception as e:
                logger.error(f"Failed to set vJoy device name: {e}")
        except ImportError:
            logger.warning("win32api not available, skipping device name setting")
        
        # Load the vJoy DLL
        self.vjoy_dll_path = self._find_vjoy_dll()
        if not self.vjoy_dll_path:
            raise RuntimeError("vJoy DLL not found")
            
        logger.info(f"Loaded vJoy DLL from {self.vjoy_dll_path}")
        
        # Initialize vJoy
        try:
            import ctypes
            self.vjoy_dll = ctypes.WinDLL(self.vjoy_dll_path)
            
            # Define function prototypes
            self.vjoy_dll.vJoyEnabled.restype = ctypes.c_bool
            self.vjoy_dll.vJoyEnabled.argtypes = []
            
            self.vjoy_dll.GetvJoyVersion.restype = ctypes.c_short
            self.vjoy_dll.GetvJoyVersion.argtypes = []
            
            self.vjoy_dll.AcquireVJD.restype = ctypes.c_bool
            self.vjoy_dll.AcquireVJD.argtypes = [ctypes.c_uint]
            
            self.vjoy_dll.GetVJDStatus.restype = ctypes.c_int
            self.vjoy_dll.GetVJDStatus.argtypes = [ctypes.c_uint]
            
            self.vjoy_dll.SetAxis.restype = ctypes.c_bool
            self.vjoy_dll.SetAxis.argtypes = [ctypes.c_long, ctypes.c_uint, ctypes.c_uint]
            
            # Check if vJoy is enabled
            if not self.vjoy_dll.vJoyEnabled():
                raise RuntimeError("vJoy is not enabled")
                
            # Get vJoy version
            version = self.vjoy_dll.GetvJoyVersion()
            logger.info(f"vJoy Version: {version}")
            
            # Acquire vJoy device
            self.vjoy_device_id = 1  # Use first device
            
            # Check device status
            status = self.vjoy_dll.GetVJDStatus(self.vjoy_device_id)
            if status == 0:  # VJD_STAT_OWN
                logger.info(f"vJoy Device {self.vjoy_device_id} is already owned by this feeder")
                self.vjoy_acquired = True
            elif status == 1:  # VJD_STAT_FREE
                if self.vjoy_dll.AcquireVJD(self.vjoy_device_id):
                    logger.info(f"Acquired vJoy Device {self.vjoy_device_id}")
                    self.vjoy_acquired = True
                else:
                    raise RuntimeError(f"Failed to acquire vJoy Device {self.vjoy_device_id}")
            elif status == 2:  # VJD_STAT_BUSY
                raise RuntimeError("vJoy device is already owned by another feeder")
            elif status == 3:  # VJD_STAT_MISS
                raise RuntimeError("vJoy device is not installed or disabled")
            else:
                raise RuntimeError(f"vJoy device has unknown status: {status}")
                
        except Exception as e:
            logger.error(f"Failed to initialize vJoy: {e}")
            raise
    
    def update_axis(self, throttle: int, brake: int, clutch: int):
        """Update the virtual joystick axes."""
        if self.test_mode:
            # In test mode, just log the values
            logger.debug(f"Test mode - Axis values: Throttle={throttle}, Brake={brake}, Clutch={clutch}")
            return True
            
        if not hasattr(self, 'vjoy_acquired') or not self.vjoy_acquired:
            logger.error("Cannot update axes: vJoy device not acquired")
            return False
            
        try:
            # Set X axis (throttle)
            self.vjoy_dll.SetAxis(throttle, self.vjoy_device_id, 0x30)  # HID_USAGE_X
            
            # Set Y axis (brake)
            self.vjoy_dll.SetAxis(brake, self.vjoy_device_id, 0x31)  # HID_USAGE_Y
            
            # Set Z axis (clutch)
            self.vjoy_dll.SetAxis(clutch, self.vjoy_device_id, 0x32)  # HID_USAGE_Z
            
            return True
        except Exception as e:
            logger.error(f"Failed to update vJoy axes: {e}")
            return False
    
    def __del__(self):
        """Clean up vJoy device."""
        try:
            if hasattr(self, 'vjoy_dll') and self.vjoy_dll:
                self.vjoy_dll.RelinquishVJD(self.vjoy_device_id)
                logger.info("vJoy device released")
        except Exception as e:
            logger.error(f"Error cleaning up vJoy device: {e}")

    def _find_vjoy_dll(self):
        """Find the path to the vJoy DLL."""
        dll_paths = [
            os.path.join(os.path.dirname(__file__), "vJoyInterface.dll"),
            r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
            r"C:\Program Files (x86)\vJoy\x64\vJoyInterface.dll",
            r"C:\Windows\System32\vJoyInterface.dll"
        ]
        
        for path in dll_paths:
            if os.path.exists(path):
                return path
        return None 