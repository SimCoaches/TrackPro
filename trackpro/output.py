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
    """Handles virtual joystick output using vJoy."""
    
    def __init__(self):
        """Initialize vJoy device."""
        # Set device name
        self.set_device_name("Sim Coaches P1 Pro Pedals")
        
        # Load vJoy DLL
        dll_paths = [
            os.path.join(os.path.dirname(__file__), "vJoyInterface.dll"),
            r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
            r"C:\Program Files (x86)\vJoy\x64\vJoyInterface.dll",
            r"C:\Windows\System32\vJoyInterface.dll"
        ]
        
        self.vjoy = None
        for path in dll_paths:
            if os.path.exists(path):
                try:
                    self.vjoy = ctypes.WinDLL(path)
                    logger.info(f"Loaded vJoy DLL from {path}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load vJoy DLL from {path}: {e}")
        
        if not self.vjoy:
            raise RuntimeError("Could not find vJoy DLL")
        
        # Initialize vJoy
        if not self.vjoy.vJoyEnabled():
            raise RuntimeError("vJoy driver not enabled")
            
        # Get vJoy version
        self.vjoy.GetvJoyVersion.restype = wintypes.SHORT
        version = self.vjoy.GetvJoyVersion()
        logger.info(f"vJoy Version: {version}")
        
        # Acquire device 1
        self.rID = 1  # Device ID
        status = self.vjoy.GetVJDStatus(self.rID)
        
        if status == VJD_STAT_OWN:
            logger.info("vJoy device already owned by this feeder")
        elif status == VJD_STAT_FREE:
            logger.info("vJoy device is free")
        elif status == VJD_STAT_BUSY:
            raise RuntimeError("vJoy device is already owned by another feeder")
        elif status == VJD_STAT_MISS:
            raise RuntimeError("vJoy device is not installed or disabled")
            
        # Check if required axes are available
        if not all([
            self.vjoy.GetVJDAxisExist(self.rID, HID_USAGE_X),  # Throttle
            self.vjoy.GetVJDAxisExist(self.rID, HID_USAGE_Y),  # Brake
            self.vjoy.GetVJDAxisExist(self.rID, HID_USAGE_Z)   # Clutch
        ]):
            raise RuntimeError("vJoy device missing required axes")
            
        # Acquire the device
        if not self.vjoy.AcquireVJD(self.rID):
            raise RuntimeError("Failed to acquire vJoy device")
            
        # Reset device to default values
        self.vjoy.ResetVJD(self.rID)
        
        # Create position structure
        self.pos = JOYSTICK_POSITION_V2()
        self.pos.bDevice = self.rID
        
        logger.info("Virtual joystick initialized successfully")
        
        # Set initial axis values to mid-point
        self.update_axis(AXIS_MAX//2, AXIS_MAX//2, AXIS_MAX//2)

    def set_device_name(self, name: str):
        """Set the vJoy device name in Windows registry."""
        try:
            # Registry path for vJoy device 1
            reg_path = r"SYSTEM\CurrentControlSet\Control\MediaProperties\PrivateProperties\Joystick\OEM\VID_1234&PID_BEAD"
            
            # Open or create the registry key
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            
            # Set the OEMName value
            winreg.SetValueEx(key, "OEMName", 0, winreg.REG_SZ, name)
            
            # Close the key
            winreg.CloseKey(key)
            logger.info(f"Set vJoy device name to: {name}")
            
        except Exception as e:
            logger.error(f"Failed to set vJoy device name: {e}")
    
    def update_axis(self, throttle: int, brake: int, clutch: int):
        """Update all axis values."""
        try:
            # Ensure values are within valid range
            throttle = max(AXIS_MIN, min(AXIS_MAX, throttle))
            brake = max(AXIS_MIN, min(AXIS_MAX, brake))
            clutch = max(AXIS_MIN, min(AXIS_MAX, clutch))
            
            # Set axis values using HID usage codes
            if not all([
                self.vjoy.SetAxis(throttle, self.rID, HID_USAGE_X),  # Throttle
                self.vjoy.SetAxis(brake, self.rID, HID_USAGE_Y),    # Brake
                self.vjoy.SetAxis(clutch, self.rID, HID_USAGE_Z)    # Clutch (already inverted)
            ]):
                logger.error("Failed to set one or more axes")
                
        except Exception as e:
            logger.error(f"Error updating axis values: {e}")
    
    def __del__(self):
        """Clean up vJoy device."""
        try:
            if hasattr(self, 'vjoy') and self.vjoy:
                self.vjoy.RelinquishVJD(self.rID)
                logger.info("vJoy device released")
        except Exception as e:
            logger.error(f"Error cleaning up vJoy device: {e}") 