import ctypes
from ctypes import wintypes
import logging
import os
import winreg
import json
from pathlib import Path
import sys
import win32serviceutil
import win32service
import win32file
import win32con
import win32api
import win32security
import time
import subprocess

# Set up detailed logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler with a higher debug level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create file handler which logs even debug messages
log_file = Path.home() / ".trackpro" / "hidhide.log"
log_file.parent.mkdir(exist_ok=True)
file_handler = logging.FileHandler(str(log_file))
file_handler.setLevel(logging.DEBUG)

# Create formatters and add them to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# HidHide Control Device IOCTLs
IOCTL_GET_BLACKLIST = 0x80002000
IOCTL_SET_BLACKLIST = 0x80002004
IOCTL_GET_WHITELIST = 0x80002008
IOCTL_SET_WHITELIST = 0x8000200C
IOCTL_GET_ACTIVE = 0x80002010
IOCTL_SET_ACTIVE = 0x80002014

def is_admin():
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_hidhide_service():
    """Check if the HidHide service is running."""
    try:
        status = win32serviceutil.QueryServiceStatus('HidHide')
        return status[1] == win32service.SERVICE_RUNNING
    except:
        return False

def to_double_null_terminated_string(strings):
    """Convert a list of strings to a double-null-terminated wide-char string."""
    if not strings:
        return b'\x00\x00'
    
    # Convert each string to UTF-16LE and add null terminator
    encoded_strings = []
    for s in strings:
        # Normalize path to single backslashes
        s = s.replace("/", "\\")
        s = s.replace("\\\\", "\\")
        
        # Encode as UTF-16LE with null terminator
        encoded = s.encode('utf-16le') + b'\x00\x00'
        encoded_strings.append(encoded)
    
    # Concatenate all encoded strings
    result = b''.join(encoded_strings)
    # Add final null terminator if not already present
    if not result.endswith(b'\x00\x00'):
        result += b'\x00\x00'
    return result

def from_double_null_terminated_string(buffer):
    """Convert a double-null-terminated wide-char string to a list of strings."""
    if not buffer or len(buffer) < 2:
        return []
    
    try:
        # Remove trailing nulls
        while buffer and buffer[-2:] == b'\x00\x00':
            buffer = buffer[:-2]
        
        # Split on double nulls and decode each string
        strings = []
        for part in buffer.split(b'\x00\x00'):
            if part:
                try:
                    decoded = part.decode('utf-16le').rstrip('\x00')
                    if decoded:
                        strings.append(decoded)
                except:
                    continue
        return strings
    except:
        return []

class HidHideClient:
    """Interface to HidHide using the CLI tool."""
    
    def __init__(self):
        """Initialize HidHide client."""
        logger.info("Initializing HidHide client...")
        
        # Check HidHide service
        try:
            status = win32serviceutil.QueryServiceStatus('HidHide')
            logger.info(f"HidHide service status: {status[1]}")
            
            if status[1] != win32service.SERVICE_RUNNING:
                logger.info("HidHide service not running, attempting to start...")
                win32serviceutil.StartService('HidHide')
                # Wait for it to start
                for i in range(10):  # Wait up to 10 seconds
                    status = win32serviceutil.QueryServiceStatus('HidHide')
                    if status[1] == win32service.SERVICE_RUNNING:
                        logger.info(f"HidHide service started after {i+1} seconds")
                        break
                    time.sleep(1)
                if status[1] != win32service.SERVICE_RUNNING:
                    raise RuntimeError("Failed to start HidHide service")
        except Exception as e:
            logger.error(f"HidHide service error: {e}")
            raise RuntimeError(f"HidHide service error: {e}")
        
        logger.info("HidHide service is running")
        
        # Store configuration file path
        self.config_file = Path.home() / ".trackpro" / "hidhide_config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Load or create configuration
        self.load_config()
        
        # Find HidHideCLI.exe
        self.cli_path = self._find_cli()
        if not self.cli_path:
            raise RuntimeError("Could not find HidHideCLI.exe")
        
        # Clean up old temporary registrations
        self.cleanup_temp_registrations()
        
        # Register our application
        app_path = os.path.abspath(sys.argv[0])
        logger.info(f"Registering application path: {app_path}")
        if not self.register_application(app_path):
            raise RuntimeError("Failed to register application with HidHide")
    
    def _find_cli(self):
        """Find the HidHideCLI.exe executable."""
        # First check if it's bundled with our application
        bundled_cli = os.path.join(os.path.dirname(__file__), "HidHideCLI.exe")
        if os.path.exists(bundled_cli):
            logger.info(f"Found bundled HidHideCLI at: {bundled_cli}")
            return bundled_cli
        
        # Check common installation paths
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Nefarius Software Solutions e.U.\HidHide", 0, winreg.KEY_READ) as key:
                install_path = winreg.QueryValueEx(key, "Path")[0]
                cli_path = os.path.join(install_path, "x64", "HidHideCLI.exe")
                if os.path.exists(cli_path):
                    logger.info(f"Found HidHideCLI at: {cli_path}")
                    return cli_path
        except WindowsError:
            pass
        
        # Check common paths
        common_paths = [
            r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
            r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found HidHideCLI at: {path}")
                return path
        
        logger.error("Could not find HidHideCLI.exe")
        return None
    
    def _run_cli(self, args, check_output=False):
        """Run HidHideCLI with given arguments."""
        try:
            cmd = [self.cli_path] + args
            logger.debug(f"Running command: {cmd}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Log output regardless of success
            if result.stdout:
                logger.debug(f"CLI stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"CLI stderr: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"CLI command failed with code {result.returncode}")
                return None if check_output else False
            
            return result.stdout if check_output else True
            
        except Exception as e:
            logger.error(f"Error running CLI command: {e}")
            return None if check_output else False
    
    def register_application(self, app_path):
        """Register application with HidHide."""
        logger.info(f"Registering application: {app_path}")
        
        # Normalize the path to ensure proper format
        app_path = os.path.normpath(app_path)
        
        # First check if already registered
        registered_apps = self._run_cli(["--app-list"], check_output=True)
        if registered_apps and app_path in registered_apps:
            logger.info("Application already registered")
            return True
        
        # Register the application without adding extra quotes
        return self._run_cli(["--app-reg", app_path])
    
    def hide_device(self, instance_path):
        """Hide a device by its instance path."""
        logger.info(f"Hiding device: {instance_path}")
        
        # Normalize the path to ensure proper format
        instance_path = instance_path.replace('"', '')
        
        # First check if already hidden
        hidden_devices = self._run_cli(["--dev-list"], check_output=True)
        if hidden_devices:
            # Check if device is already hidden
            if any(instance_path in device for device in hidden_devices.splitlines()):
                logger.info("Device already hidden")
                # Make sure cloaking is enabled
                cloak_result = self._run_cli(["--cloak-on"])
                logger.info(f"Cloak enabled: {cloak_result}")
                # Verify cloaking status
                self.verify_cloaking_status()
                return cloak_result
        
        # Hide the device and enable cloaking
        hide_result = self._run_cli(["--dev-hide", instance_path])
        if hide_result:
            # Update our config
            if instance_path not in self.config['hidden_devices']:
                self.config['hidden_devices'].append(instance_path)
                self.save_config()
            # Enable cloaking and verify it's enabled
            cloak_result = self._run_cli(["--cloak-on"])
            logger.info(f"Cloak enabled: {cloak_result}")
            
            # Verify cloaking status
            self.verify_cloaking_status()
            
            # Verify the device is actually hidden
            hidden_devices = self._run_cli(["--dev-list"], check_output=True)
            if hidden_devices:
                if any(instance_path in device for device in hidden_devices.splitlines()):
                    logger.info("Verified device is hidden")
                    return True
                else:
                    logger.error("Device not found in hidden devices list after hiding")
                    return False
            else:
                logger.error("Failed to get hidden devices list after hiding")
                return False
        else:
            logger.error("Failed to hide device")
            return False
    
    def unhide_device(self, instance_path):
        """Unhide a device by its instance path."""
        logger.info(f"Unhiding device: {instance_path}")
        
        # Normalize the path to ensure proper format
        instance_path = instance_path.replace('"', '')
        
        # First check if actually hidden
        hidden_devices = self._run_cli(["--dev-list"], check_output=True)
        if not hidden_devices or not any(instance_path in device for device in hidden_devices.splitlines()):
            logger.info("Device not hidden")
            return True
        
        # Unhide the device
        unhide_result = self._run_cli(["--dev-unhide", instance_path])
        if unhide_result:
            # Update our config
            if instance_path in self.config['hidden_devices']:
                self.config['hidden_devices'].remove(instance_path)
                self.save_config()
            
            # Check if any devices are still hidden
            hidden_devices = self._run_cli(["--dev-list"], check_output=True)
            if not hidden_devices or hidden_devices.strip() == "":
                # If no devices are hidden, turn off cloaking
                cloak_result = self._run_cli(["--cloak-off"])
                logger.info(f"Cloak disabled: {cloak_result}")
                return cloak_result
            return True
        else:
            logger.error("Failed to unhide device")
            return False
    
    def get_device_instance_path(self, device_name):
        """Get the device instance path for a given device name."""
        try:
            logger.info(f"Looking for device instance path for: {device_name}")
            
            # First try using HidHide's gaming devices list
            gaming_devices = self._run_cli(["--dev-gaming"], check_output=True)
            if gaming_devices:
                # Parse the JSON output
                import json
                try:
                    devices = json.loads(gaming_devices)
                    # Look for our device in the list
                    for device_group in devices:
                        if "Sim Coaches P1 Pro Pedals" in device_group.get("friendlyName", ""):
                            # Get the first device in the group
                            if device_group.get("devices"):
                                device = device_group["devices"][0]
                                path = device.get("deviceInstancePath")
                                
                                # Use the HID device path as it's what HidHide expects
                                if path:
                                    logger.info(f"Found HID device path via HidHide: {path}")
                                    return path
                                    
                                # Only fallback to base container path if HID path not found
                                base_path = device.get("baseContainerDeviceInstancePath")
                                if base_path:
                                    logger.warning(f"Using fallback base device path: {base_path}")
                                    return base_path
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse HidHide JSON output: {e}")
            
            # Fallback to registry search if HidHide didn't find it
            logger.debug("Falling back to registry search...")
            
            # Look for specific VID/PID combinations that might be the pedals
            target_vids = ["1DD2"]  # Sim Coaches VID
            
            reg_paths = [
                r"SYSTEM\CurrentControlSet\Enum\HID",
                r"SYSTEM\CurrentControlSet\Enum\USB"
            ]
            
            for reg_path in reg_paths:
                logger.debug(f"Searching in registry path: {reg_path}")
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            vendor_name = winreg.EnumKey(key, i)
                            vendor_path = f"{reg_path}\\{vendor_name}"
                            
                            # Check if this is one of our target VIDs
                            if any(vid in vendor_name.upper() for vid in target_vids):
                                logger.debug(f"Found potential matching VID: {vendor_name}")
                                
                                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, vendor_path, 0, winreg.KEY_READ) as vendor_key:
                                    j = 0
                                    while True:
                                        try:
                                            instance_name = winreg.EnumKey(vendor_key, j)
                                            instance_path = f"{vendor_path}\\{instance_name}"
                                            
                                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, instance_path, 0, winreg.KEY_READ) as instance_key:
                                                try:
                                                    # Check device properties
                                                    for prop_name in ["DeviceDesc", "FriendlyName"]:
                                                        try:
                                                            value = winreg.QueryValueEx(instance_key, prop_name)[0]
                                                            logger.debug(f"Found device property {prop_name}: {value}")
                                                            
                                                            # If this is a game controller with our target VID, it's likely our device
                                                            if "Sim Coaches" in value:
                                                                # Format path with single backslashes and proper prefix
                                                                path = f"HID\\{vendor_name}\\{instance_name}"
                                                                path = path.replace('/', '\\')
                                                                while '\\\\' in path:
                                                                    path = path.replace('\\\\', '\\')
                                                                logger.info(f"Found device path via registry: {path}")
                                                                return path
                                                                
                                                        except WindowsError:
                                                            continue
                                                except WindowsError:
                                                    pass
                                            j += 1
                                        except WindowsError:
                                            break
                            i += 1
                        except WindowsError:
                            break
            
            logger.warning(f"Could not find device instance path for: {device_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting device instance path: {e}")
            return None
    
    def load_config(self):
        """Load HidHide configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    self.config = json.load(f)
                logger.info("Loaded HidHide configuration")
                return
            except Exception as e:
                logger.warning(f"Failed to load HidHide configuration: {e}")
        
        # Default configuration
        self.config = {
            'hidden_devices': []  # List of device instance paths to hide
        }
        self.save_config()
    
    def save_config(self):
        """Save HidHide configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f)
            logger.info("Saved HidHide configuration")
        except Exception as e:
            logger.error(f"Failed to save HidHide configuration: {e}")
    
    def cleanup_temp_registrations(self):
        """Clean up old temporary registrations from previous runs."""
        logger.info("Cleaning up old temporary registrations...")
        
        # Get list of registered applications
        registered_apps = self._run_cli(["--app-list"], check_output=True)
        if not registered_apps:
            logger.warning("Could not get list of registered applications")
            return
        
        # Look for temporary paths that might be from previous runs
        temp_paths = []
        for line in registered_apps.splitlines():
            if "--app-reg" in line and "Temp\\_MEI" in line and "trackpro\\HidHideCLI.exe" in line:
                # Extract the path
                path = line.split("--app-reg")[1].strip()
                # Remove quotes if present
                if path.startswith('"') and path.endswith('"'):
                    path = path[1:-1]
                
                # Check if this is from a previous run (not our current path)
                if self.cli_path not in path:
                    temp_paths.append(path)
        
        # Unregister old temporary paths
        for path in temp_paths:
            logger.info(f"Unregistering old temporary path: {path}")
            self._run_cli(["--app-unreg", path])
        
        if temp_paths:
            logger.info(f"Cleaned up {len(temp_paths)} old temporary registrations")
        else:
            logger.info("No old temporary registrations found")
    
    def verify_cloaking_status(self):
        """Verify that cloaking is enabled and working properly."""
        try:
            # Check if cloaking is enabled
            cloak_status = self._run_cli(["--cloak-state"], check_output=True)
            if cloak_status:
                if "on" in cloak_status.lower():
                    logger.info("Cloaking is enabled")
                    return True
                else:
                    logger.warning(f"Cloaking appears to be disabled: {cloak_status}")
                    # Try to enable it again
                    self._run_cli(["--cloak-on"])
                    # Check again
                    cloak_status = self._run_cli(["--cloak-state"], check_output=True)
                    if cloak_status and "on" in cloak_status.lower():
                        logger.info("Successfully enabled cloaking")
                        return True
                    else:
                        logger.error("Failed to enable cloaking")
                        return False
            else:
                logger.warning("Could not determine cloaking status")
                return False
        except Exception as e:
            logger.error(f"Error verifying cloaking status: {e}")
            return False 