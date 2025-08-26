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
from configparser import ConfigParser

# Set up logging
logger = logging.getLogger(__name__)

# Load config for performance settings
_cfg = ConfigParser()
_cfg.read("config.ini")
_MUTE = _cfg.getboolean("Performance", "mute_hidhide_cli_errors", fallback=True)

# Only add handlers if none exist to prevent duplicate logging
if not logger.handlers and not logging.getLogger().handlers:
    logger.setLevel(logging.DEBUG)
    # Create console handler with a higher debug level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

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

def safe_device_io_control(handle, ioctl_code, input_buffer=None, output_buffer_size=0):
    """Safely perform DeviceIoControl operations with proper error handling."""
    try:
        if output_buffer_size > 0:
            output_buffer = bytearray(output_buffer_size)
        else:
            output_buffer = None
        
        # Use win32file.DeviceIoControl with proper parameter handling
        if input_buffer is None:
            result = win32file.DeviceIoControl(
                handle,
                ioctl_code,
                None,
                output_buffer
            )
        else:
            result = win32file.DeviceIoControl(
                handle,
                ioctl_code,
                input_buffer,
                output_buffer
            )
        
        return True, output_buffer
        
    except Exception as e:
        logger.warning(f"DeviceIoControl failed for IOCTL {hex(ioctl_code)}: {e}")
        return False, None

def should_hide_device(dev):
    """Determine if a device should be hidden by HidHide.
    
    Policy: Never hide vJoy devices. Only hide physical Sim Coaches hardware.
    Filter by name/VID/PID; skip anything whose friendly name contains "vJoy" (case-insensitive).
    """
    name = (getattr(dev, 'friendly_name', '') or "").lower()
    hardware_id = (getattr(dev, 'hardware_id', '') or "").lower()
    
    # Never hide vJoy - this is critical for game compatibility
    # Check for vJoy by name (case-insensitive) and known VID/PID
    if "vjoy" in name or "vid_1234&pid_bead" in hardware_id:
        logger.info(f"Refusing to hide vJoy device: {name}")
        return False
    
    # Only hide our physical pedals/handbrake
    return any(tag in name for tag in [
        "sim coaches", "p1 pro", "handbrake"
    ])

class HidHideClient:
    """Interface to HidHide using the CLI tool."""
    
    def __init__(self, fail_silently=False):
        """Initialize HidHide client.
        
        Args:
            fail_silently: If True, don't raise exceptions for errors
        """
        logger.info("Initializing HidHide client")
        self.cli_path = None
        self.error_context = None
        self.functioning = True
        self.fail_silently = fail_silently
        self.config_file = Path.home() / "AppData" / "Local" / "TrackPro" / "hidhide_config.json"
        self.config = None
        
        # Check admin privileges early - required for HidHide operations
        # If elevation is missing, do nothing silently; do not try to register anything
        if not is_admin():
            logger.info("HidHide not elevated; skipping device registration (safe default).")
            self.functioning = False
            return
        
        try:
            # Check if HidHide is installed
            if not self._is_hidhide_installed():
                self._handle_error(
                    "HidHide driver is not installed on this system. "
                    "Please install HidHide from https://github.com/ViGEm/HidHide/releases "
                    "and restart the application.",
                    "driver_not_installed"
                )
                return
            
            # Check HidHide service
            try:
                status = win32serviceutil.QueryServiceStatus('HidHide')
                logger.info(f"HidHide service status: {status[1]}")
                
                # Check if service is running
                if status[1] != win32service.SERVICE_RUNNING:
                    # Try to start the service
                    logger.info("HidHide service is not running. Attempting to start...")
                    win32serviceutil.StartService('HidHide')
                    
                    # Wait for service to start
                    for _ in range(5):  # 5 attempts
                        time.sleep(1)  # Wait 1 second between checks
                        status = win32serviceutil.QueryServiceStatus('HidHide')
                        if status[1] == win32service.SERVICE_RUNNING:
                            logger.info("Successfully started HidHide service")
                            break
                    
                    # If still not running after attempts, fail
                    if status[1] != win32service.SERVICE_RUNNING:
                        self._handle_error(
                            "Failed to start HidHide service. "
                            "Please try reinstalling HidHide or restart your computer.",
                            "service_start_failed"
                        )
                        return
            except win32service.error as e:
                if e.winerror == 1060:  # Service does not exist
                    self._handle_error(
                        "HidHide service is not installed. "
                        "Please install HidHide from https://github.com/ViGEm/HidHide/releases "
                        "and restart the application.",
                        "service_not_installed"
                    )
                    return
                else:
                    self._handle_error(
                        f"HidHide service error: {e}",
                        "service_error"
                    )
                    return
            except Exception as e:
                self._handle_error(
                    f"Unexpected error with HidHide service: {e}",
                    "service_unexpected_error"
                )
                return
            
            logger.info("HidHide service is running")
            
            # Find HidHideCLI.exe
            self.cli_path = self._find_cli()
            if not self.cli_path:
                self._handle_error(
                    "Could not find HidHideCLI.exe. "
                    "Please make sure HidHide is properly installed.",
                    "cli_not_found"
                )
                return
            
            # Load configuration
            try:
                self.load_config()
            except Exception as e:
                logger.warning(f"Failed to load HidHide configuration: {e}")
                # Create default configuration
                self.config = {'hidden_devices': []}

            # Clean up old temporary registrations
            try:
                self.cleanup_temp_registrations()
            except Exception as e:
                logger.warning(f"Failed to clean up temporary registrations: {e}")
                # Continue anyway, this is not critical
            
            # Register our application - use CLI method which is more reliable
            app_path = os.path.abspath(sys.argv[0])
            logger.info(f"Registering application path: {app_path}")
            try:
                if not self.register_application_cli(app_path):
                    self._handle_error(
                        "Failed to register application with HidHide. "
                        "Please try running the application as administrator.",
                        "app_registration_failed",
                        raise_error=not self.fail_silently
                    )
            except Exception as e:
                self._handle_error(
                    f"Error registering application with HidHide: {e}",
                    "app_registration_error",
                    raise_error=not self.fail_silently
                )
            
        except Exception as e:
            if fail_silently:
                logger.error(f"HidHide initialization failed but continuing: {e}")
                self.functioning = False
                return
            raise  # Re-raise the exception if we're not failing silently
    
    def _handle_error(self, error_msg, error_context, raise_error=True):
        """Handle errors consistently in the HidHide client.
        
        Args:
            error_msg: Error message to log
            error_context: Error context to set
            raise_error: Whether to raise a RuntimeError (if not failing silently)
        """
        logger.error(error_msg)
        self.error_context = error_context
        
        if self.fail_silently:
            self.functioning = False
            return
        
        if raise_error:
            raise RuntimeError(error_msg)
    
    def _is_hidhide_installed(self):
        """Check if HidHide is installed by looking for its registry keys."""
        try:
            # Check for HidHide registry key
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\HidHide") as key:
                return True
        except WindowsError:
            return False
        
        # Also check for the device interface
        try:
            # Try to open the device
            device_path = r"\\.\HidHide"
            handle = win32file.CreateFile(
                device_path,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            win32file.CloseHandle(handle)
            return True
        except Exception:
            return False
    
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
    
    def _run_cli_once(self, args, check_output=False) -> bool:
        """Run HidHideCLI once without retries."""
        try:
            cmd = [self.cli_path] + args
            logger.debug(f"Running command: {cmd}")
            
            # Set up subprocess run parameters
            run_kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 5
            }
            
            # Hide console window on Windows
            if sys.platform == "win32":
                CREATE_NO_WINDOW = 0x08000000
                run_kwargs['creationflags'] = CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, **run_kwargs)
            
            if result.returncode != 0:
                if not _MUTE:
                    logger.error(f"CLI command failed with code {result.returncode}")
                return False
            
            if check_output:
                return result.stdout
            return True
            
        except PermissionError:
            if _MUTE:
                # do not retry; log once and continue so we don't starve vJoy/UI
                logger.warning("HidHide CLI access denied; continuing without automation.")
                return False
            raise
        except Exception as e:
            if not _MUTE:
                logger.error(f"CLI command error: {e}")
            return False

    def _run_cli(self, args, check_output=False, retry_count=2, ignore_errors=False):
        """Run HidHideCLI with given arguments.
        
        Args:
            args: List of command arguments
            check_output: Whether to return output (True) or success status (False)
            retry_count: Number of times to retry on failure
            ignore_errors: Whether to ignore errors and return empty/false instead of failing
        """
        if not self.functioning or not self.cli_path:
            logger.warning(f"HidHide not functioning, skipping CLI command: {args}")
            return None if check_output else False
        
        # Use single attempt when muted to prevent stalling
        if _MUTE:
            result = self._run_cli_once(args, check_output)
            return result if result else (None if check_output else False)
            
        original_retry = retry_count
        while retry_count >= 0:
            try:
                cmd = [self.cli_path] + args
                logger.debug(f"Running command: {cmd}")
                
                # Set up subprocess run parameters
                run_kwargs = {
                    'capture_output': True,
                    'text': True,
                    'timeout': 5
                }
                
                # Add creationflags only on Windows
                if sys.platform == 'win32':
                    # Use CREATE_NO_WINDOW to hide command windows
                    CREATE_NO_WINDOW = 0x08000000
                    run_kwargs['creationflags'] = CREATE_NO_WINDOW
                
                result = subprocess.run(cmd, **run_kwargs)
                
                if result.returncode != 0:
                    logger.error(f"CLI command failed with code {result.returncode}")
                    if retry_count > 0:
                        logger.info(f"Retrying command (attempts left: {retry_count})...")
                        retry_count -= 1
                        time.sleep(0.5)  # Add a short delay between retries
                        continue
                    
                    if ignore_errors:
                        return None if check_output else False
                    
                    if "Access is denied" in result.stderr:
                        # Special handling for access denied errors
                        logger.error("Access denied error when running HidHide CLI")
                        self.error_context = "cli_access_denied"
                        self.functioning = False
                        return None if check_output else False
                    
                    return None if check_output else False
                
                return result.stdout if check_output else True
                
            except (subprocess.TimeoutExpired, Exception) as e:
                error_type = "timeout" if isinstance(e, subprocess.TimeoutExpired) else "error"
                logger.error(f"CLI command {error_type}: {e}")
                
                if retry_count > 0:
                    logger.info(f"Retrying command (attempts left: {retry_count})...")
                    retry_count -= 1
                    time.sleep(0.5)  # Add a short delay between retries
                    continue
                
                return None if check_output else False
        
        # If we reach here, all retries have failed
        logger.error(f"Command failed after {original_retry + 1} attempts")
        return None if check_output else False
    
    def register_application_cli(self, app_path):
        """Register application with HidHide using CLI method only."""
        if not self.functioning:
            logger.warning("HidHide not functioning, skipping application registration")
            return False
        
        # Check admin privileges
        if not is_admin():
            logger.warning("HidHide requires elevation to register applications; skipping.")
            return False
            
        logger.info(f"Registering application: {app_path}")
        
        # Normalize the path to ensure proper format
        app_path = os.path.normpath(app_path)
        
        # First check if already registered
        registered_apps = self._run_cli(["--app-list"], check_output=True, ignore_errors=True)
        if registered_apps and app_path in registered_apps:
            logger.info("Application already registered")
            return True
        
        # Register using CLI
        result = self._run_cli(["--app-reg", app_path])
        if result:
            logger.info("Successfully registered application with HidHide")
            return True
        else:
            logger.error("Failed to register application with HidHide")
            return False
    
    def register_application(self, app_path):
        """Register application with HidHide."""
        # Use the CLI-only method which is more reliable
        return self.register_application_cli(app_path)
    
    def is_device_hidden(self, device_name_or_path):
        """Check if a device is hidden by name or path."""
        logger.info(f"Checking if device is hidden: {device_name_or_path}")
        
        # Get list of hidden devices
        hidden_devices = self._run_cli(["--dev-list"], check_output=True)
        if not hidden_devices:
            logger.info("No devices are currently hidden")
            return False, None
        
        # Check if the device is in the list by path
        for line in hidden_devices.splitlines():
            if device_name_or_path in line:
                logger.info(f"Device is hidden: {line}")
                return True, line.strip()
        
        # If we're looking for a device by name, we need to check all hidden devices
        if "HID\\" not in device_name_or_path and "USB\\" not in device_name_or_path:
            # This is a name, not a path, so we need to check device properties
            logger.info("Checking hidden devices for matching name")
            
            # Get all hidden devices and check their properties
            for line in hidden_devices.splitlines():
                if line.strip():
                    # Try to get device properties from registry
                    try:
                        # Convert HID path to registry path
                        reg_path = line.replace("HID\\", "SYSTEM\\CurrentControlSet\\Enum\\HID\\")
                        reg_path = reg_path.replace("USB\\", "SYSTEM\\CurrentControlSet\\Enum\\USB\\")
                        
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ) as key:
                            try:
                                for prop_name in ["DeviceDesc", "FriendlyName"]:
                                    try:
                                        value = winreg.QueryValueEx(key, prop_name)[0]
                                        if device_name_or_path in value:
                                            logger.info(f"Found hidden device matching name: {line}")
                                            return True, line.strip()
                                    except WindowsError:
                                        continue
                            except WindowsError:
                                pass
                    except Exception as e:
                        logger.debug(f"Error checking device properties: {e}")
        
        logger.info(f"Device is not hidden: {device_name_or_path}")
        return False, None
    
    def unhide_all_matching_devices(self, device_name):
        """Unhide all devices that match the given name."""
        logger.info(f"Unhiding all devices matching: {device_name}")
        
        # Get list of hidden devices
        hidden_devices = self._run_cli(["--dev-list"], check_output=True)
        if not hidden_devices:
            logger.info("No devices are currently hidden")
            return True
        
        # Keep track of whether we found and unhid any devices
        found_devices = False
        
        # Check each hidden device
        for line in hidden_devices.splitlines():
            if line.strip():
                # Try to get device properties from registry
                try:
                    # Convert HID path to registry path
                    reg_path = line.replace("HID\\", "SYSTEM\\CurrentControlSet\\Enum\\HID\\")
                    reg_path = reg_path.replace("USB\\", "SYSTEM\\CurrentControlSet\\Enum\\USB\\")
                    
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ) as key:
                        try:
                            for prop_name in ["DeviceDesc", "FriendlyName"]:
                                try:
                                    value = winreg.QueryValueEx(key, prop_name)[0]
                                    if device_name in value:
                                        logger.info(f"Found hidden device matching name: {line}")
                                        # Unhide this device
                                        if self.unhide_device(line.strip()):
                                            logger.info(f"Successfully unhid device: {line}")
                                            found_devices = True
                                        else:
                                            logger.warning(f"Failed to unhide device: {line}")
                                        break
                                except WindowsError:
                                    continue
                        except WindowsError:
                            pass
                except Exception as e:
                    logger.debug(f"Error checking device properties: {e}")
        
        if not found_devices:
            logger.info(f"No hidden devices found matching: {device_name}")
        
        return True
    
    def hide_device(self, instance_path):
        """Hide a device by its instance path."""
        logger.info(f"Hiding device: {instance_path}")
        
        # Check admin privileges
        if not is_admin():
            logger.warning("HidHide requires elevation to hide devices; skipping.")
            return False
        
        # Normalize the path to ensure proper format
        instance_path = instance_path.replace('"', '')
        
        # Safety check: Never hide vJoy devices (case-insensitive)
        if "vjoy" in instance_path.lower():
            logger.warning(f"Refusing to hide vJoy device: {instance_path}")
            return False
        
        # Additional VID/PID safety check for vJoy
        if "vid_1234&pid_bead" in instance_path.lower():
            logger.warning(f"Refusing to hide vJoy device by VID/PID: {instance_path}")
            return False
        
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
            
            # First check if the device is already hidden
            is_hidden, hidden_path = self.is_device_hidden(device_name)
            if is_hidden and hidden_path:
                logger.info(f"Device is already hidden, using path: {hidden_path}")
                return hidden_path
            
            # If not hidden, try using HidHide's gaming devices list
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
        # Ensure the directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
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
            # Ensure the directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
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
    
    def find_all_matching_devices(self, device_name):
        """Find all devices matching a name, whether hidden or not."""
        logger.info(f"Finding all devices matching: {device_name}")
        
        matching_devices = []
        
        # First check hidden devices
        is_hidden, hidden_path = self.is_device_hidden(device_name)
        if is_hidden and hidden_path:
            matching_devices.append(hidden_path)
        
        # Then check gaming devices
        gaming_devices = self._run_cli(["--dev-gaming"], check_output=True)
        if gaming_devices:
            # Parse the JSON output
            import json
            try:
                devices = json.loads(gaming_devices)
                # Look for our device in the list
                for device_group in devices:
                    if device_name in device_group.get("friendlyName", ""):
                        # Get all devices in the group
                        if device_group.get("devices"):
                            for device in device_group["devices"]:
                                path = device.get("deviceInstancePath")
                                if path and path not in matching_devices:
                                    matching_devices.append(path)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse HidHide JSON output: {e}")
        
        # Finally check registry
        target_vids = ["1DD2"]  # Sim Coaches VID
        
        reg_paths = [
            r"SYSTEM\CurrentControlSet\Enum\HID",
            r"SYSTEM\CurrentControlSet\Enum\USB"
        ]
        
        for reg_path in reg_paths:
            logger.debug(f"Searching in registry path: {reg_path}")
            try:
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
                                                            if device_name in value:
                                                                # Format path with single backslashes and proper prefix
                                                                path = f"HID\\{vendor_name}\\{instance_name}"
                                                                path = path.replace('/', '\\')
                                                                while '\\\\' in path:
                                                                    path = path.replace('\\\\', '\\')
                                                                
                                                                if path not in matching_devices:
                                                                    matching_devices.append(path)
                                                                
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
            except Exception as e:
                logger.error(f"Error searching registry: {e}")
        
        if matching_devices:
            logger.info(f"Found {len(matching_devices)} matching devices: {matching_devices}")
        else:
            logger.warning(f"No devices found matching: {device_name}")
        
        return matching_devices
    
    def set_cloak_state(self, active):
        """Set the global cloaking state of HidHide.
        
        Args:
            active (bool): True to enable cloaking, False to disable it.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.functioning:
            logger.warning("HidHide not functioning, skipping set_cloak_state")
            return False
            
        logger.info(f"Setting HidHide cloak state to: {'active' if active else 'inactive'}")
        
        # Use CLI method only (most reliable)
        cli_result = self._run_cli(["--cloak-on" if active else "--cloak-off"], retry_count=2)
        if cli_result:
            logger.info(f"Set cloak state via CLI: {active}")
            return True
        else:
            logger.warning(f"Failed to set cloak state via CLI: {active}")
            return False 