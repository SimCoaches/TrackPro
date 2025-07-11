"""
Subprocess utilities for TrackPro to ensure consistent behavior across the application.
Provides functions to run subprocesses without showing command windows.
"""

import subprocess
import sys
import os
from typing import List, Optional, Union, Any, Dict


def get_subprocess_kwargs(hide_window: bool = True) -> Dict[str, Any]:
    """
    Get consistent subprocess keyword arguments for Windows.
    
    Args:
        hide_window: Whether to hide command windows (default: True)
    
    Returns:
        Dict containing subprocess keyword arguments
    """
    kwargs = {}
    
    if sys.platform == 'win32' and hide_window:
        # CREATE_NO_WINDOW flag to hide command windows
        CREATE_NO_WINDOW = 0x08000000
        kwargs['creationflags'] = CREATE_NO_WINDOW
    
    return kwargs


def run_subprocess(
    cmd: List[str],
    hide_window: bool = True,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    timeout: Optional[float] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with consistent window hiding behavior.
    
    Args:
        cmd: Command to run as a list of strings
        hide_window: Whether to hide command windows (default: True)
        capture_output: Whether to capture stdout/stderr (default: True)
        text: Whether to return text output (default: True)
        check: Whether to raise exception on non-zero exit (default: False)
        timeout: Timeout in seconds (default: None)
        **kwargs: Additional subprocess.run arguments
    
    Returns:
        CompletedProcess object
    """
    # Get standard subprocess kwargs
    subprocess_kwargs = get_subprocess_kwargs(hide_window)
    
    # Add user-provided kwargs
    subprocess_kwargs.update(kwargs)
    
    # Set default parameters
    subprocess_kwargs.setdefault('capture_output', capture_output)
    subprocess_kwargs.setdefault('text', text)
    subprocess_kwargs.setdefault('check', check)
    
    if timeout is not None:
        subprocess_kwargs['timeout'] = timeout
    
    return subprocess.run(cmd, **subprocess_kwargs)


def run_subprocess_popen(
    cmd: Union[str, List[str]],
    hide_window: bool = True,
    shell: bool = False,
    **kwargs
) -> subprocess.Popen:
    """
    Create a subprocess.Popen with consistent window hiding behavior.
    
    Args:
        cmd: Command to run (string or list)
        hide_window: Whether to hide command windows (default: True)
        shell: Whether to use shell (default: False)
        **kwargs: Additional subprocess.Popen arguments
    
    Returns:
        Popen object
    """
    # Get standard subprocess kwargs
    subprocess_kwargs = get_subprocess_kwargs(hide_window)
    
    # Add user-provided kwargs
    subprocess_kwargs.update(kwargs)
    
    # Set shell parameter
    subprocess_kwargs['shell'] = shell
    
    return subprocess.Popen(cmd, **subprocess_kwargs)


def run_command_hidden(
    cmd: List[str],
    timeout: Optional[float] = None
) -> tuple[bool, str, str]:
    """
    Run a command with hidden window and return success status and output.
    
    Args:
        cmd: Command to run as a list of strings
        timeout: Timeout in seconds (default: None)
    
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        result = run_subprocess(
            cmd,
            hide_window=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", "Command timed out")
    except Exception as e:
        return (False, "", str(e))


def run_powershell_hidden(
    script: str,
    timeout: Optional[float] = None
) -> tuple[bool, str, str]:
    """
    Run a PowerShell script with hidden window.
    
    Args:
        script: PowerShell script to run
        timeout: Timeout in seconds (default: None)
    
    Returns:
        Tuple of (success, stdout, stderr)
    """
    cmd = ["powershell", "-Command", script]
    return run_command_hidden(cmd, timeout)


# Compatibility aliases for common use cases
def run_hidden(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Alias for run_subprocess with hide_window=True"""
    return run_subprocess(cmd, hide_window=True, **kwargs)


def run_visible(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Alias for run_subprocess with hide_window=False"""
    return run_subprocess(cmd, hide_window=False, **kwargs) 