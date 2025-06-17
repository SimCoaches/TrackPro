#!/usr/bin/env python3
"""
TrackPro Diagnostic Tool
This script helps diagnose why TrackPro might not be starting on your system.
Run this before reporting issues to quickly identify common problems.
"""

import sys
import os
import traceback
import platform
import subprocess
from datetime import datetime

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n--- {title} ---")

def check_item(description, check_func):
    """Check an item and report status."""
    try:
        result = check_func()
        if result:
            print(f"✓ {description}")
            return True
        else:
            print(f"✗ {description}")
            return False
    except Exception as e:
        print(f"✗ {description} - Error: {e}")
        return False

def check_python_version():
    """Check if Python version is adequate."""
    version = sys.version_info
    if version >= (3, 8):
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (Good)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False

def check_module(module_name):
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

def check_vjoy():
    """Check if vJoy is installed."""
    paths = [
        r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
        r"C:\Program Files (x86)\vJoy\x64\vJoyInterface.dll"
    ]
    for path in paths:
        if os.path.exists(path):
            return True
    return False

def check_hidhide():
    """Check if HidHide is installed."""
    try:
        import win32serviceutil
        status = win32serviceutil.QueryServiceStatus('HidHide')
        return True
    except:
        return False

def check_system_resources():
    """Check system resources."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        print(f"  Memory: {memory.total // (1024**3)}GB total, {memory.available // (1024**3)}GB available")
        print(f"  Disk: {disk.total // (1024**3)}GB total, {disk.free // (1024**3)}GB free")
        
        if memory.available < 512 * 1024 * 1024:
            print("  ⚠ Warning: Low memory (less than 512MB available)")
            return False
        
        if disk.free < 100 * 1024 * 1024:
            print("  ⚠ Warning: Low disk space (less than 100MB free)")
            return False
            
        return True
    except ImportError:
        print("  Could not check system resources (psutil not available)")
        return True

def check_admin_rights():
    """Check if running with admin rights."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def try_import_trackpro():
    """Try to import TrackPro modules."""
    try:
        import trackpro
        print(f"✓ TrackPro module imported successfully (version: {trackpro.__version__})")
        return True
    except Exception as e:
        print(f"✗ TrackPro module import failed: {e}")
        return False

def main():
    print_header("TrackPro Diagnostic Tool")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Architecture: {platform.architecture()}")
    
    all_checks_passed = True
    
    # Basic System Checks
    print_section("System Information")
    all_checks_passed &= check_python_version()
    all_checks_passed &= check_item("Admin rights", check_admin_rights)
    all_checks_passed &= check_item("System resources", check_system_resources)
    
    # Python Module Checks
    print_section("Python Modules")
    required_modules = [
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtWebEngineWidgets',
        'numpy', 'requests', 'psutil', 'pygame', 'matplotlib'
    ]
    
    for module in required_modules:
        all_checks_passed &= check_item(f"{module} module", lambda m=module: check_module(m))
    
    # Windows-specific modules
    if sys.platform == 'win32':
        print_section("Windows Modules")
        win_modules = ['win32api', 'win32serviceutil', 'win32service']
        for module in win_modules:
            all_checks_passed &= check_item(f"{module} module", lambda m=module: check_module(m))
    
    # Hardware Dependencies
    print_section("Hardware Dependencies")
    check_item("vJoy DLL", check_vjoy)  # Not critical for startup
    check_item("HidHide service", check_hidhide)  # Not critical for startup
    
    # TrackPro Specific Checks
    print_section("TrackPro Application")
    all_checks_passed &= check_item("TrackPro module import", try_import_trackpro)
    
    # File Checks
    print_section("Required Files")
    required_files = [
        'run_app.py',
        'trackpro/__init__.py',
        'trackpro/main.py',
        'trackpro/ui.py'
    ]
    
    for file_path in required_files:
        all_checks_passed &= check_item(f"{file_path}", lambda f=file_path: os.path.exists(f))
    
    # Final Report
    print_header("Diagnostic Results")
    if all_checks_passed:
        print("✓ All critical checks passed! TrackPro should be able to start.")
        print("\nIf TrackPro still won't start, try:")
        print("1. Running as Administrator")
        print("2. Checking antivirus software isn't blocking TrackPro")
        print("3. Restarting your computer")
    else:
        print("✗ Some checks failed. TrackPro may not start properly.")
        print("\nTo fix issues:")
        print("1. Install missing Python modules with: pip install <module_name>")
        print("2. Run as Administrator")
        print("3. Install vJoy and HidHide if using pedals")
        print("4. Check system requirements")
    
    # Save report to desktop
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        report_file = os.path.join(desktop, "TrackPro_Diagnostic_Report.txt")
        
        # Capture all output
        import io
        import contextlib
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            # Re-run all checks to capture output
            main()
        
        with open(report_file, 'w') as file:
            file.write(f.getvalue())
        
        print(f"\n📄 Full diagnostic report saved to: {report_file}")
    except Exception as e:
        print(f"\n⚠ Could not save diagnostic report: {e}")
    
    print("\n" + "="*60)
    input("Press Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nDiagnostic tool failed: {e}")
        print(traceback.format_exc())
        input("Press Enter to exit...") 