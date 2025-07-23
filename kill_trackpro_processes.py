#!/usr/bin/env python3
"""
Standalone utility to kill stuck TrackPro processes.
Run this if you get "Another instance of TrackPro is already running" error.
"""

import subprocess
import time
import sys

def kill_trackpro_processes():
    """Kill any stuck TrackPro processes aggressively."""
    print("=== TrackPro Process Killer ===")
    print("This utility will terminate all TrackPro processes and clean up locks.")
    print()
    
    # First clean up lock files
    try:
        import tempfile
        import os
        
        lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("✓ Removed TrackPro lock file")
        else:
            print("✓ No lock file found")
    except Exception as e:
        print(f"! Could not remove lock file: {e}")
    
    # Then try to find any TrackPro processes
    try:
        result = subprocess.run([
            'powershell', '-Command', 
            "Get-Process | Where-Object {$_.ProcessName -like '*TrackPro*'} | Select-Object ProcessName, Id"
        ], capture_output=True, text=True, timeout=10)
        
        if result.stdout.strip():
            print("Found TrackPro processes:")
            print(result.stdout)
            print()
        else:
            print("✓ No TrackPro processes found")
            
            # Also check for Python processes running TrackPro
            python_result = subprocess.run([
                'powershell', '-Command', 
                "Get-Process python*, pythonw* | Where-Object {$_.CommandLine -like '*trackpro*' -or $_.CommandLine -like '*run_app*'} | Select-Object ProcessName, Id, CommandLine"
            ], capture_output=True, text=True, timeout=10)
            
            if python_result.stdout.strip():
                print("Found Python processes running TrackPro:")
                print(python_result.stdout)
                print()
            else:
                print("✓ No Python TrackPro processes found")
                print("✓ All locks and processes cleaned up successfully!")
                return True
                
    except Exception as e:
        print(f"Could not check for processes: {e}")
        return False
    
    # Ask for confirmation
    try:
        response = input("Do you want to kill these processes? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            return False
    except KeyboardInterrupt:
        print("\\nOperation cancelled.")
        return False
    
    print("\\nKilling TrackPro processes...")
    
    # Try multiple methods to kill stuck processes
    kill_methods = [
        # Method 1: Regular taskkill
        (['taskkill', '/F', '/IM', 'TrackPro_v1.5.3.exe'], "Standard taskkill v1.5.3"),
        (['taskkill', '/F', '/IM', 'TrackPro.exe'], "Standard taskkill generic"),
        # Method 2: Kill by window title
        (['taskkill', '/F', '/FI', 'WINDOWTITLE eq TrackPro*'], "Kill by window title"),
        # Method 3: PowerShell force kill
        (['powershell', '-Command', 
          "Get-Process | Where-Object {$_.ProcessName -like '*TrackPro*'} | Stop-Process -Force"], 
         "PowerShell force kill"),
    ]
    
    success_count = 0
    for i, (method, description) in enumerate(kill_methods, 1):
        try:
            print(f"Trying method {i}: {description}...")
            result = subprocess.run(method, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✓ Method {i} successful")
                success_count += 1
            else:
                error_msg = result.stderr.strip() if result.stderr.strip() else "No error message"
                print(f"✗ Method {i} failed: {error_msg}")
        except Exception as e:
            print(f"✗ Method {i} error: {e}")
    
    # Give processes time to terminate
    print("\\nWaiting for processes to terminate...")
    time.sleep(3)
    
    # Final check and cleanup
    try:
        result = subprocess.run([
            'powershell', '-Command', 
            "Get-Process | Where-Object {$_.ProcessName -like '*TrackPro*'} | Measure-Object | Select-Object Count"
        ], capture_output=True, text=True, timeout=10)
        
        if "0" in result.stdout or not result.stdout.strip():
            print("✓ All TrackPro processes terminated successfully!")
            
            # Final lock cleanup
            try:
                import tempfile
                import os
                
                lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    print("✓ Final cleanup: Removed lock file")
                
                print("\\n🎉 All processes and locks cleaned up! You can now run TrackPro normally.")
            except Exception as e:
                print(f"! Could not perform final lock cleanup: {e}")
                print("\\n🎉 Processes terminated. You can now run TrackPro normally.")
            
            return True
        else:
            print("⚠ Some TrackPro processes may still be running")
            print("\\n💡 Recommendations:")
            print("   1. Restart your computer to clear all stuck processes")
            print("   2. Run TrackPro with --force flag: python run_app.py --force")
            print("   3. Check Task Manager for any remaining TrackPro processes")
            return False
    except Exception as e:
        print(f"Could not verify process cleanup: {e}")
        return False

def main():
    """Main function."""
    try:
        success = kill_trackpro_processes()
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\\n\\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 