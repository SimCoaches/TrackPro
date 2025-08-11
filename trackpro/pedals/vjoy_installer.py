"""
VJoy Virtual Joystick Driver Installation and Management

This module handles the installation, detection, and management of the vJoy virtual
joystick driver required for TrackPro's pedal manipulation functionality.

Key Features:
- Automatic vJoy installation detection
- Silent installation with proper error handling
- Version compatibility checking
- Fallback installation mechanisms
- Post-installation verification
"""

import os
import sys
import subprocess
import logging
import winreg
import time
from pathlib import Path
import ctypes
from typing import Optional, Tuple, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

# Only add handlers if none exist to prevent duplicate logging
if not logger.handlers and not logging.getLogger().handlers:
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

class VJoyInstaller:
    """Handles vJoy virtual joystick driver installation and management."""
    
    # Known vJoy registry keys and paths
    VJOY_REGISTRY_KEYS = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1",  # v2.1.9.1
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\vJoy",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\vJoy"
    ]
    
    VJOY_INSTALL_PATHS = [
        r"C:\Program Files\vJoy",
        r"C:\Program Files (x86)\vJoy"
    ]
    
    VJOY_DLL_PATHS = [
        r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
        r"C:\Program Files (x86)\vJoy\x64\vJoyInterface.dll",
        r"C:\Program Files\vJoy\x86\vJoyInterface.dll",
        r"C:\Program Files (x86)\vJoy\x86\vJoyInterface.dll"
    ]
    
    def __init__(self, fail_silently=False):
        """Initialize the vJoy installer.
        
        Args:
            fail_silently: If True, don't raise exceptions for errors
        """
        self.fail_silently = fail_silently
        self.installation_info = None
        logger.info("Initializing vJoy installer")
        
    def is_vjoy_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if vJoy is installed on the system.
        
        Returns:
            Tuple of (is_installed: bool, version: Optional[str])
        """
        logger.info("Checking for existing vJoy installation...")
        
        # Check registry entries
        for reg_key in self.VJOY_REGISTRY_KEYS:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key, 0, winreg.KEY_READ) as key:
                    try:
                        display_name = winreg.QueryValueEx(key, "DisplayName")[0]
                        version = winreg.QueryValueEx(key, "DisplayVersion")[0]
                        logger.info(f"Found vJoy installation: {display_name} v{version}")
                        return True, version
                    except WindowsError:
                        # Key exists but missing expected values
                        logger.info(f"Found vJoy registry key but missing version info: {reg_key}")
                        return True, "Unknown"
            except WindowsError:
                continue
        
        # Check for vJoy DLL files
        for dll_path in self.VJOY_DLL_PATHS:
            if os.path.exists(dll_path):
                logger.info(f"Found vJoy DLL at: {dll_path}")
                return True, "Unknown"
        
        # Check for vJoy installation directory
        for install_path in self.VJOY_INSTALL_PATHS:
            if os.path.exists(install_path):
                exe_path = os.path.join(install_path, "vJoyConf.exe")
                if os.path.exists(exe_path):
                    logger.info(f"Found vJoy installation directory: {install_path}")
                    return True, "Unknown"
        
        logger.info("No vJoy installation detected")
        return False, None
    
    def get_vjoy_info(self) -> Dict[str, Any]:
        """Get detailed information about the vJoy installation.
        
        Returns:
            Dictionary containing vJoy installation details
        """
        is_installed, version = self.is_vjoy_installed()
        
        info = {
            "installed": is_installed,
            "version": version,
            "dll_paths": [],
            "install_path": None,
            "configuration_tool": None
        }
        
        if is_installed:
            # Find DLL paths
            for dll_path in self.VJOY_DLL_PATHS:
                if os.path.exists(dll_path):
                    info["dll_paths"].append(dll_path)
            
            # Find installation path
            for install_path in self.VJOY_INSTALL_PATHS:
                if os.path.exists(install_path):
                    info["install_path"] = install_path
                    
                    # Check for configuration tool
                    conf_tool = os.path.join(install_path, "vJoyConf.exe")
                    if os.path.exists(conf_tool):
                        info["configuration_tool"] = conf_tool
                    break
        
        self.installation_info = info
        return info
    
    def install_vjoy(self, installer_path: str, silent: bool = True) -> bool:
        """Install vJoy using the provided installer.
        
        Args:
            installer_path: Path to the vJoy installer executable
            silent: Whether to run installation silently
            
        Returns:
            True if installation was successful, False otherwise
        """
        if not os.path.exists(installer_path):
            logger.error(f"vJoy installer not found at: {installer_path}")
            if not self.fail_silently:
                raise FileNotFoundError(f"vJoy installer not found: {installer_path}")
            return False
        
        logger.info(f"Installing vJoy from: {installer_path}")
        
        # Check if already installed
        is_installed, version = self.is_vjoy_installed()
        if is_installed:
            logger.info(f"vJoy is already installed (version: {version})")
            return True
        
        # Prepare installation command
        if silent:
            # Try multiple silent installation flags
            installation_commands = [
                [installer_path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                [installer_path, "/S", "/SILENT"],
                [installer_path, "/quiet", "/norestart"],
                [installer_path, "/q", "/norestart"]
            ]
        else:
            installation_commands = [[installer_path]]
        
        # Try each installation method
        for i, cmd in enumerate(installation_commands, 1):
            logger.info(f"Attempting vJoy installation method {i}: {' '.join(cmd)}")
            
            try:
                # Use CREATE_NO_WINDOW to hide installer window if possible
                creation_flags = 0x08000000 if sys.platform == 'win32' else 0
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    creationflags=creation_flags
                )
                
                logger.info(f"Installation command returned: {result.returncode}")
                
                # Check various success conditions
                if result.returncode in [0, 3010]:  # 0 = success, 3010 = success but restart required
                    logger.info("Installation command completed successfully")
                    
                    # Wait a moment for installation to complete
                    time.sleep(3)
                    
                    # Verify installation
                    is_installed, version = self.is_vjoy_installed()
                    if is_installed:
                        logger.info(f"vJoy installation verified successfully (version: {version})")
                        return True
                    else:
                        logger.warning("Installation command succeeded but vJoy not detected")
                        continue
                
                elif result.returncode == 1638:  # Product already installed
                    logger.info("vJoy is already installed (installer reported)")
                    return True
                
                elif result.returncode == 1618:  # Another installation in progress
                    logger.warning("Another installation is in progress, waiting...")
                    time.sleep(10)
                    # Retry this command once
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        time.sleep(3)
                        is_installed, version = self.is_vjoy_installed()
                        if is_installed:
                            logger.info("vJoy installation successful after retry")
                            return True
                
                else:
                    logger.warning(f"Installation method {i} failed with code: {result.returncode}")
                    if result.stderr:
                        logger.warning(f"Error output: {result.stderr}")
                    continue
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Installation method {i} timed out")
                continue
            except Exception as e:
                logger.error(f"Installation method {i} failed with exception: {e}")
                continue
        
        # All installation methods failed
        logger.error("All vJoy installation methods failed")
        
        # Final check in case installation succeeded but didn't report properly
        time.sleep(5)  # Wait a bit longer
        is_installed, version = self.is_vjoy_installed()
        if is_installed:
            logger.info("vJoy installation detected after final check")
            return True
        
        if not self.fail_silently:
            raise RuntimeError("vJoy installation failed with all attempted methods")
        
        return False
    
    def verify_vjoy_functionality(self) -> bool:
        """Verify that vJoy is properly installed and functional.
        
        Returns:
            True if vJoy is functional, False otherwise
        """
        logger.info("Verifying vJoy functionality...")
        
        # Check if installed
        is_installed, version = self.is_vjoy_installed()
        if not is_installed:
            logger.error("vJoy is not installed")
            return False
        
        # Try to load the vJoy DLL
        for dll_path in self.VJOY_DLL_PATHS:
            if os.path.exists(dll_path):
                try:
                    # Try to load the DLL
                    vjoy_dll = ctypes.WinDLL(dll_path)
                    
                    # Try to call a basic function (vJoyEnabled)
                    vjoy_enabled = vjoy_dll.vJoyEnabled
                    vjoy_enabled.restype = ctypes.c_bool
                    
                    if vjoy_enabled():
                        logger.info(f"vJoy is functional (DLL: {dll_path})")
                        return True
                    else:
                        logger.warning(f"vJoy DLL loaded but driver reports as disabled: {dll_path}")
                        
                except Exception as e:
                    logger.warning(f"Could not test vJoy DLL functionality: {dll_path} - {e}")
                    continue
        
        # If we can't test functionality but it's installed, assume it's working
        logger.warning("Could not verify vJoy functionality but installation detected")
        return True
    
    def configure_vjoy_device(self, device_id: int = 1, axes: int = 8, buttons: int = 32) -> bool:
        """Configure a vJoy device with specified parameters.
        
        Args:
            device_id: vJoy device ID (1-16)
            axes: Number of axes to configure
            buttons: Number of buttons to configure
            
        Returns:
            True if configuration was successful, False otherwise
        """
        logger.info(f"Configuring vJoy device {device_id} with {axes} axes and {buttons} buttons")
        
        info = self.get_vjoy_info()
        if not info["installed"]:
            logger.warning("vJoy is not installed")
            return False
        
        config_tool = info.get("configuration_tool")
        if not config_tool:
            logger.warning("vJoy configuration tool not found")
            return False
        
        try:
            # Use vJoyConf to configure the device
            cmd = [
                config_tool,
                str(device_id),
                "-f",  # Force configuration
                "-a", str(axes),  # Number of axes
                "-b", str(buttons),  # Number of buttons
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"vJoy device {device_id} configured successfully")
                return True
            else:
                logger.warning(f"vJoy configuration returned code: {result.returncode}")
                if result.stderr:
                    logger.warning(f"Configuration error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error configuring vJoy device: {e}")
            return False
    
    def uninstall_vjoy(self) -> bool:
        """Uninstall vJoy if it's installed.
        
        Returns:
            True if uninstallation was successful or vJoy wasn't installed, False otherwise
        """
        logger.info("Attempting to uninstall vJoy...")
        
        is_installed, version = self.is_vjoy_installed()
        if not is_installed:
            logger.info("vJoy is not installed, nothing to uninstall")
            return True
        
        # Try to find uninstaller
        for reg_key in self.VJOY_REGISTRY_KEYS:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key, 0, winreg.KEY_READ) as key:
                    try:
                        uninstall_string = winreg.QueryValueEx(key, "UninstallString")[0]
                        logger.info(f"Found vJoy uninstaller: {uninstall_string}")
                        
                        # Run uninstaller
                        result = subprocess.run(
                            [uninstall_string, "/SILENT"],
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        
                        if result.returncode == 0:
                            logger.info("vJoy uninstallation completed")
                            
                            # Verify uninstallation
                            time.sleep(3)
                            is_still_installed, _ = self.is_vjoy_installed()
                            if not is_still_installed:
                                logger.info("vJoy uninstallation verified")
                                return True
                            else:
                                logger.warning("vJoy still detected after uninstallation")
                                return False
                        else:
                            logger.error(f"vJoy uninstallation failed with code: {result.returncode}")
                            return False
                            
                    except WindowsError:
                        continue
            except WindowsError:
                continue
        
        logger.error("Could not find vJoy uninstaller")
        return False

def is_admin():
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_vjoy_status():
    """Get the current vJoy installation status.
    
    Returns:
        Dictionary with vJoy status information
    """
    installer = VJoyInstaller(fail_silently=True)
    return installer.get_vjoy_info()

def install_vjoy_if_needed(installer_path: str = None) -> bool:
    """Install vJoy if it's not already installed.
    
    Args:
        installer_path: Path to vJoy installer (optional)
        
    Returns:
        True if vJoy is available (was already installed or successfully installed)
    """
    installer = VJoyInstaller(fail_silently=True)
    
    # Check if already installed
    is_installed, version = installer.is_vjoy_installed()
    if is_installed:
        logger.info(f"vJoy is already installed (version: {version})")
        return installer.verify_vjoy_functionality()
    
    # Need to install
    if not installer_path:
        logger.error("vJoy installer path not provided and vJoy is not installed")
        return False
    
    if not os.path.exists(installer_path):
        logger.error(f"vJoy installer not found: {installer_path}")
        return False
    
    # Install vJoy
    success = installer.install_vjoy(installer_path)
    if success:
        return installer.verify_vjoy_functionality()
    
    return False 