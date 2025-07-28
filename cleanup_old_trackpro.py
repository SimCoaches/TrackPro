#!/usr/bin/env python3
"""
TrackPro Legacy Cleanup Utility
===============================

This utility helps clean up old TrackPro installations and shortcuts that may 
have been left behind from previous versions. 

Run this script if you:
- Have multiple TrackPro versions installed
- Have old shortcuts that don't work
- Want to free up disk space from old installations
- Are experiencing issues with conflicting versions

IMPORTANT: This will NOT delete your calibrations, settings, or user data.
Only executable files, shortcuts, and temporary files are removed.
"""

import os
import sys
import winreg
import shutil
import psutil
import ctypes
from pathlib import Path

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def find_trackpro_processes():
    """Find all running TrackPro processes."""
    trackpro_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if 'trackpro' in proc.info['name'].lower():
                trackpro_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return trackpro_processes

def terminate_trackpro_processes():
    """Terminate all TrackPro processes."""
    processes = find_trackpro_processes()
    if not processes:
        print("✓ No TrackPro processes found running")
        return True
    
    print(f"Found {len(processes)} TrackPro process(es) running:")
    for proc in processes:
        try:
            print(f"  - {proc.info['name']} (PID: {proc.info['pid']})")
        except:
            print(f"  - Unknown process (PID: {proc.info['pid']})")
    
    print("\nTerminating processes...")
    terminated = 0
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            terminated += 1
            print(f"✓ Terminated process PID {proc.info['pid']}")
        except psutil.TimeoutExpired:
            try:
                proc.kill()
                terminated += 1
                print(f"✓ Force-killed process PID {proc.info['pid']}")
            except:
                print(f"✗ Failed to kill process PID {proc.info['pid']}")
        except:
            print(f"✗ Failed to terminate process PID {proc.info['pid']}")
    
    print(f"Successfully terminated {terminated}/{len(processes)} processes")
    return terminated == len(processes)

def find_trackpro_installations():
    """Find all TrackPro installation directories."""
    installation_paths = []
    
    # Common installation locations
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\TrackPro"),
        os.path.expandvars(r"%PROGRAMFILES%\TrackPro"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\TrackPro"),
        os.path.expandvars(r"%APPDATA%\TrackPro"),
        os.path.expandvars(r"%APPDATA%\Local\TrackPro"),
        os.path.expanduser(r"~\AppData\Local\TrackPro"),
        os.path.expanduser(r"~\AppData\Roaming\TrackPro"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            installation_paths.append(path)
    
    return installation_paths

def find_trackpro_shortcuts():
    """Find all TrackPro shortcuts."""
    shortcuts = []
    
    # Common shortcut locations
    shortcut_locations = [
        (os.path.expandvars(r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs"), "Start Menu (All Users)"),
        (os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"), "Start Menu (Current User)"),
        (os.path.expandvars(r"%PUBLIC%\Desktop"), "Desktop (All Users)"),
        (os.path.expanduser(r"~\Desktop"), "Desktop (Current User)"),
    ]
    
    for location, description in shortcut_locations:
        if not os.path.exists(location):
            continue
            
        # Look for TrackPro shortcuts
        for file in Path(location).rglob("*TrackPro*.lnk"):
            shortcuts.append((str(file), description))
    
    return shortcuts

def cleanup_installation(install_path):
    """Clean up a TrackPro installation directory."""
    print(f"\nCleaning up installation: {install_path}")
    
    if not os.path.exists(install_path):
        print(f"✓ Directory doesn't exist: {install_path}")
        return True
    
    cleaned_files = 0
    errors = 0
    
    try:
        # Remove TrackPro executables
        for exe_file in Path(install_path).glob("TrackPro*.exe"):
            try:
                os.remove(exe_file)
                print(f"✓ Removed executable: {exe_file.name}")
                cleaned_files += 1
            except Exception as e:
                print(f"✗ Failed to remove {exe_file.name}: {e}")
                errors += 1
        
        # Remove uninstaller files
        for unins_file in Path(install_path).glob("unins*.exe"):
            try:
                os.remove(unins_file)
                print(f"✓ Removed uninstaller: {unins_file.name}")
                cleaned_files += 1
            except Exception as e:
                print(f"✗ Failed to remove {unins_file.name}: {e}")
                errors += 1
        
        for unins_file in Path(install_path).glob("unins*.dat"):
            try:
                os.remove(unins_file)
                print(f"✓ Removed uninstaller data: {unins_file.name}")
                cleaned_files += 1
            except Exception as e:
                print(f"✗ Failed to remove {unins_file.name}: {e}")
                errors += 1
        
        # Remove log files
        for log_file in Path(install_path).glob("*.log"):
            try:
                os.remove(log_file)
                print(f"✓ Removed log file: {log_file.name}")
                cleaned_files += 1
            except Exception as e:
                print(f"✗ Failed to remove {log_file.name}: {e}")
                errors += 1
        
        # Remove temporary files
        for tmp_file in Path(install_path).glob("*.tmp"):
            try:
                os.remove(tmp_file)
                print(f"✓ Removed temp file: {tmp_file.name}")
                cleaned_files += 1
            except Exception as e:
                print(f"✗ Failed to remove {tmp_file.name}: {e}")
                errors += 1
        
        # Try to remove the directory if it's empty
        try:
            if not any(Path(install_path).iterdir()):
                os.rmdir(install_path)
                print(f"✓ Removed empty directory: {install_path}")
            else:
                print(f"ℹ Directory not empty, preserving user data: {install_path}")
        except Exception as e:
            print(f"ℹ Could not remove directory (may contain user data): {e}")
    
    except Exception as e:
        print(f"✗ Error accessing directory: {e}")
        return False
    
    print(f"Cleanup summary: {cleaned_files} files removed, {errors} errors")
    return errors == 0

def cleanup_shortcuts(shortcuts):
    """Clean up TrackPro shortcuts."""
    if not shortcuts:
        print("✓ No TrackPro shortcuts found")
        return True
    
    print(f"\nFound {len(shortcuts)} TrackPro shortcut(s):")
    for shortcut_path, location in shortcuts:
        print(f"  - {os.path.basename(shortcut_path)} ({location})")
    
    print("\nRemoving shortcuts...")
    removed = 0
    errors = 0
    
    for shortcut_path, location in shortcuts:
        try:
            os.remove(shortcut_path)
            print(f"✓ Removed: {os.path.basename(shortcut_path)}")
            removed += 1
        except Exception as e:
            print(f"✗ Failed to remove {os.path.basename(shortcut_path)}: {e}")
            errors += 1
    
    print(f"Shortcut cleanup summary: {removed} removed, {errors} errors")
    return errors == 0

def main():
    print("TrackPro Legacy Cleanup Utility")
    print("=" * 50)
    print()
    print("This utility will clean up old TrackPro installations and shortcuts.")
    print("Your calibrations, settings, and user data will be preserved.")
    print()
    
    if not is_admin():
        print("⚠️  WARNING: Running without administrator privileges.")
        print("   Some files may not be removable if they're in system directories.")
        print("   For best results, right-click and 'Run as administrator'.")
        print()
    
    # Check for running processes
    print("🔍 Checking for running TrackPro processes...")
    if not terminate_trackpro_processes():
        print("\n⚠️  Warning: Some TrackPro processes could not be terminated.")
        print("   This may prevent some files from being deleted.")
        response = input("\nContinue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("Cleanup cancelled.")
            return
    
    # Find installations
    print("\n🔍 Searching for TrackPro installations...")
    installations = find_trackpro_installations()
    
    if installations:
        print(f"Found {len(installations)} installation(s):")
        for install_path in installations:
            print(f"  - {install_path}")
        
        print("\nStarting installation cleanup...")
        success_count = 0
        for install_path in installations:
            if cleanup_installation(install_path):
                success_count += 1
        
        print(f"\nInstallation cleanup complete: {success_count}/{len(installations)} successful")
    else:
        print("✓ No TrackPro installations found")
    
    # Find shortcuts
    print("\n🔍 Searching for TrackPro shortcuts...")
    shortcuts = find_trackpro_shortcuts()
    cleanup_shortcuts(shortcuts)
    
    # Summary
    print("\n" + "=" * 50)
    print("CLEANUP COMPLETE")
    print("=" * 50)
    print()
    print("Summary:")
    if installations:
        print(f"  • Cleaned {len(installations)} installation director{'ies' if len(installations) > 1 else 'y'}")
    if shortcuts:
        print(f"  • Cleaned {len(shortcuts)} shortcut{'s' if len(shortcuts) > 1 else ''}")
    if not installations and not shortcuts:
        print("  • No old TrackPro files found - system is already clean!")
    
    print()
    print("Your calibrations, settings, and user data have been preserved.")
    print("You can now install the latest version of TrackPro cleanly.")
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCleanup cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        input("Press Enter to exit...") 