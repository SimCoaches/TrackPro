"""
Windows Startup Management for TrackPro.

This module handles adding/removing TrackPro from Windows startup
and checking if it's currently set to start with Windows.
"""

import os
import sys
import winreg
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class WindowsStartupManager:
    """Manages Windows startup functionality for TrackPro."""
    
    def __init__(self):
        """Initialize the Windows startup manager."""
        self.app_name = "TrackPro"
        self.registry_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    def get_executable_path(self) -> Optional[str]:
        """Get the path to the TrackPro executable."""
        try:
            if getattr(sys, 'frozen', False):
                # Running as built executable
                return sys.executable
            else:
                # Running in development - use the main script
                script_path = Path(__file__).parent.parent.parent / "modern_main.py"
                if script_path.exists():
                    return str(script_path)
                else:
                    # Fallback to sys.argv[0]
                    return sys.argv[0]
        except Exception as e:
            logger.error(f"Error getting executable path: {e}")
            return None
    
    def is_startup_enabled(self) -> bool:
        """Check if TrackPro is set to start with Windows."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key_path, 0, winreg.KEY_READ) as key:
                try:
                    # Check if TrackPro entry exists
                    winreg.QueryValueEx(key, self.app_name)
                    return True
                except FileNotFoundError:
                    return False
        except Exception as e:
            logger.error(f"Error checking startup status: {e}")
            return False
    
    def enable_startup(self, start_minimized: bool = True) -> bool:
        """Enable TrackPro to start with Windows."""
        try:
            executable_path = self.get_executable_path()
            if not executable_path:
                logger.error("Could not determine executable path")
                return False
            
            # Create the command with minimized flag if requested
            if start_minimized and executable_path.endswith('.exe'):
                command = f'"{executable_path}" --minimized'
            else:
                command = f'"{executable_path}"'
            
            # Add to Windows registry
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
            
            logger.info(f"✅ TrackPro startup enabled with command: {command}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling startup: {e}")
            return False
    
    def disable_startup(self) -> bool:
        """Disable TrackPro from starting with Windows."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key_path, 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, self.app_name)
            
            logger.info("✅ TrackPro startup disabled")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling startup: {e}")
            return False
    
    def toggle_startup(self, enabled: bool, start_minimized: bool = True) -> bool:
        """Toggle TrackPro startup on or off."""
        if enabled:
            return self.enable_startup(start_minimized)
        else:
            return self.disable_startup()
    
    def get_startup_command(self) -> Optional[str]:
        """Get the current startup command if TrackPro is enabled."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key_path, 0, winreg.KEY_READ) as key:
                command = winreg.QueryValueEx(key, self.app_name)[0]
                return command
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting startup command: {e}")
            return None 