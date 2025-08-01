#!/usr/bin/env python3.11
import sys
import os
import subprocess
import traceback
import ctypes
import time
import logging
import argparse
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# CRITICAL: Set Qt attributes BEFORE any QApplication instance can be created AND before importing QtWebEngineWidgets
# This is required for QtWebEngine to work properly in PyQt6
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# Set Qt WebEngine cache directory before creating QApplication
import sys
import os
if getattr(sys, 'frozen', False):
    # Running from PyInstaller bundle - use application directory for cache
    app_dir = os.path.dirname(sys.executable)
    qt_cache_dir = os.path.join(app_dir, "QtWebEngine", "Cache")
    qt_data_dir = os.path.join(app_dir, "QtWebEngine", "Data")
    
    # Create directories if they don't exist
    os.makedirs(qt_cache_dir, exist_ok=True)
    os.makedirs(qt_data_dir, exist_ok=True)
    
    # Set environment variables for Qt WebEngine
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-logging --no-sandbox')
    os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')

# Now it's safe to import QtWebEngineWidgets after Qt attributes are set
from PyQt6 import QtWebEngineWidgets

# CRITICAL: Silence noisy libraries IMMEDIATELY before any other imports
# This prevents massive log spam from matplotlib, HTTP libraries, etc.
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib.backends').setLevel(logging.WARNING)

# Silence other noisy libraries
for library in ['urllib3', 'httpcore', 'httpx', 'hpack', 'gotrue', 'postgrest', 'urllib3.connection', 'urllib3.connectionpool', 'urllib3.poolmanager', 'httpcore.connection', 'httpx.client', 'h11', 'h2', 'requests', 'supafunc']:
    logging.getLogger(library).setLevel(logging.CRITICAL)

# Check if we're running with Python 3.11, but skip if running as exe
is_frozen = getattr(sys, 'frozen', False)
if not is_frozen and sys.version_info < (3, 8):
    print(f"TrackPro requires Python 3.8 or higher.")
    print(f"Current version: Python {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)
elif not is_frozen and sys.version_info[:2] != (3, 11):
    print(f"TrackPro recommends Python 3.11 for full eye tracking support.")
    print(f"Current version: Python {sys.version_info.major}.{sys.version_info.minor}")
    print("Continuing with current Python version - some features may be limited.")
    
    # Only try to restart if user explicitly requests it
    if "--use-python-311" in sys.argv:
        print("Attempting to restart with Python 3.11...")
        try:
            # Use py -3.11 to explicitly run with Python 3.11
            # Add CREATE_NO_WINDOW flag to hide command window
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run([
                "py", "-3.11", __file__
            ] + [arg for arg in sys.argv[1:] if arg != "--use-python-311"], 
            check=True, 
            creationflags=CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            sys.exit(result.returncode)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ Failed to start with Python 3.11: {e}")
            print("Continuing with current Python version...")
elif is_frozen:
    print("Running from packaged executable - Python version switching disabled.")
    print("Eye tracking will use the packaged Python environment.")

# Set higher logging level for noisy HTTP and Supabase libraries (moved to top of file)

# Disable any startup version dialogs or build information popups
os.environ['TRACKPRO_DISABLE_VERSION_DIALOG'] = '1'
os.environ['PYTHONUNBUFFERED'] = '1'  # Ensure unbuffered output

# Prevent NVIDIA GeForce Experience from detecting this app as a game
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '0'
os.environ['__GL_THREADED_OPTIMIZATIONS'] = '0'
os.environ['__GL_SHADER_DISK_CACHE'] = '0'
os.environ['__GL_SHADER_DISK_CACHE_SKIP_CLEANUP'] = '0'
os.environ['__GL_YIELD'] = 'NOTHING'
os.environ['NVIDIA_VISIBLE_DEVICES'] = 'none'

# Try to patch the MessageBox function to suppress specific dialogs
try:
    original_messagebox = ctypes.windll.user32.MessageBoxW
    def patched_messagebox(hwnd, text, caption, type):
        # Check if this is the "Built: v3 release" dialog
        if text and "Built: v3" in str(text):
            return 1  # Return as if user clicked OK
        return original_messagebox(hwnd, text, caption, type)
    ctypes.windll.user32.MessageBoxW = patched_messagebox
except Exception:
    pass  # If patching fails, continue anyway

# Enhanced error logging setup
def setup_enhanced_logging():
    """Set up comprehensive logging to file and console for better debugging."""
    try:
        # Check if logging is already configured to prevent duplicate handlers
        root_logger = logging.getLogger()
        if root_logger.handlers:
            logger = logging.getLogger("TrackPro_Run")
            logger.info("Logging already configured, skipping duplicate setup")
            return logger, None
        
        # Create logs directory
        logs_dir = os.path.join(os.path.expanduser("~"), "Documents", "TrackPro_Logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(logs_dir, f"trackpro_startup_{timestamp}.log")
        
        # Configure logging with both file and console handlers
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger("TrackPro_Run")
        logger.info(f"Enhanced logging initialized. Log file: {log_file}")
        return logger, log_file
    except Exception as e:
        # Check again before fallback to prevent duplicate handlers
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            # Fallback to console only if file logging fails
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout)
                ]
            )
        logger = logging.getLogger("TrackPro_Run")
        logger.warning(f"Could not set up file logging: {e}")
        return logger, None

def check_system_dependencies():
    """Check if all required system dependencies are available."""
    logger = logging.getLogger("TrackPro_Run")
    missing_deps = []
    
    try:
        # Check Python version
        python_version = sys.version_info
        logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        if python_version < (3, 8):
            missing_deps.append(f"Python 3.8+ required, found {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check for required Python modules
        required_modules = [
            'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtWebEngineWidgets',
            'numpy', 'requests', 'psutil', 'supabase', 'matplotlib'
        ]
        
        for module in required_modules:
            try:
                __import__(module)
                logger.debug(f"✓ Module {module} available")
            except ImportError as e:
                missing_deps.append(f"Missing Python module: {module} ({e})")
                logger.error(f"✗ Module {module} missing: {e}")
        
        # Check for Windows-specific dependencies
        if sys.platform == 'win32':
            try:
                import win32api
                import win32serviceutil
                logger.debug("✓ Windows API modules available")
            except ImportError as e:
                missing_deps.append(f"Missing Windows module: {e}")
                logger.error(f"✗ Windows modules missing: {e}")
        
        # Check for vJoy DLL
        vjoy_paths = [
            r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
            r"C:\Program Files (x86)\vJoy\x64\vJoyInterface.dll"
        ]
        
        vjoy_found = False
        for path in vjoy_paths:
            if os.path.exists(path):
                vjoy_found = True
                logger.info(f"✓ vJoy DLL found at: {path}")
                break
        
        if not vjoy_found:
            logger.warning("⚠ vJoy DLL not found - pedal functionality may be limited")
        
        # Check system resources
        try:
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            logger.info(f"System Memory: {memory.total // (1024**3)}GB total, {memory.available // (1024**3)}GB available")
            logger.info(f"Disk Space: {disk.total // (1024**3)}GB total, {disk.free // (1024**3)}GB free")
            
            if memory.available < 512 * 1024 * 1024:  # Less than 512MB
                missing_deps.append("Insufficient memory (less than 512MB available)")
            
            if disk.free < 100 * 1024 * 1024:  # Less than 100MB
                missing_deps.append("Insufficient disk space (less than 100MB free)")
                
        except ImportError:
            logger.warning("Could not check system resources - psutil not available")
        
        if missing_deps:
            logger.error("System dependency check failed:")
            for dep in missing_deps:
                logger.error(f"  - {dep}")
            return False, missing_deps
        else:
            logger.info("✓ All system dependencies check passed")
            return True, []
            
    except Exception as e:
        logger.error(f"Error during dependency check: {e}")
        logger.error(traceback.format_exc())
        return False, [f"Dependency check error: {e}"]

# Set up logging
logger, log_file = setup_enhanced_logging()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def is_admin():
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

def run_as_admin(args=None):
    """Re-run the script with admin privileges."""
    if not is_admin():
        if args is None:
            args = sys.argv[:]
        
        # Windows-specific elevation
        if sys.platform == 'win32':
            # Quote the arguments to handle spaces
            args = [f'"{arg}"' if ' ' in arg and not arg.startswith('"') else arg for arg in args]
            args_str = ' '.join(args)
            
            logger.info(f"Requesting admin privileges with command: {sys.executable} {args_str}")
            
            # Use SW_HIDE (0) instead of SW_SHOWNORMAL (1) to hide the command window
            # This prevents the command window from appearing during privilege elevation
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args_str, None, 0)
            
            if ret <= 32:  # ShellExecute returns a value <= 32 on error
                logger.error(f"Admin elevation failed with return code: {ret}")
                
            return ret
        else:
            # Unix-like systems would use sudo or equivalent
            logger.warning("Admin elevation requested on non-Windows platform - not supported")
            return 0
    
    return 1  # Already admin

def write_error_to_desktop(error_msg, log_file_path=None):
    """Write error message to desktop so user can see it"""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        error_file = os.path.join(desktop, "TrackPro_Error.txt")
        
        with open(error_file, 'w') as f:
            f.write(f"TrackPro Error Report\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Python Version: {sys.version}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write(f"Working Directory: {os.getcwd()}\n")
            f.write(f"Admin Rights: {is_admin()}\n")
            if log_file_path:
                f.write(f"Detailed Log File: {log_file_path}\n")
            f.write("\n" + "="*50 + "\n")
            f.write("ERROR DETAILS:\n")
            f.write("="*50 + "\n")
            f.write(error_msg)
            f.write("\n\n" + "="*50 + "\n")
            f.write("TROUBLESHOOTING STEPS:\n")
            f.write("="*50 + "\n")
            f.write("1. Try running as Administrator\n")
            f.write("2. Check if all dependencies are installed\n")
            f.write("3. Verify system requirements (Windows 10+, 4GB RAM)\n")
            f.write("4. Check antivirus software isn't blocking TrackPro\n")
            f.write("5. Try reinstalling TrackPro\n")
            f.write("6. Contact support with this error report\n")
        
        logger.info(f"Error details written to {error_file}")
    except Exception as e:
        logger.error(f"Could not write error file: {e}")

def check_environment():
    """Check environment for potential issues"""
    logger.info("="*50)
    logger.info("ENVIRONMENT CHECK")
    logger.info("="*50)
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check if running from PyInstaller bundle
    is_frozen = getattr(sys, 'frozen', False)
    logger.info(f"Running from frozen application: {is_frozen}")
    
    if is_frozen:
        logger.info(f"Executable path: {sys.executable}")
        logger.info(f"Executable directory: {os.path.dirname(sys.executable)}")
    
    # Check if trackpro module directory exists
    trackpro_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trackpro")
    if os.path.exists(trackpro_dir):
        logger.info(f"✓ TrackPro module directory exists: {trackpro_dir}")
        
        # List key files in trackpro directory
        try:
            key_files = ['__init__.py', 'main.py']
            for file in key_files:
                file_path = os.path.join(trackpro_dir, file)
                if os.path.exists(file_path):
                    logger.info(f"  ✓ {file} found")
                else:
                    logger.error(f"  ✗ {file} missing")
            
            # Check for ui module - can be either ui.py or ui/ directory with __init__.py
            ui_file_path = os.path.join(trackpro_dir, "ui.py")
            ui_dir_path = os.path.join(trackpro_dir, "ui", "__init__.py")
            
            if os.path.exists(ui_file_path):
                logger.info(f"  ✓ ui.py found")
            elif os.path.exists(ui_dir_path):
                logger.info(f"  ✓ ui module found (ui/__init__.py)")
            else:
                logger.error(f"  ✗ ui module missing (neither ui.py nor ui/__init__.py found)")
                
        except Exception as e:
            logger.error(f"Error checking trackpro files: {e}")
    else:
        logger.error(f"✗ TrackPro module directory missing: {trackpro_dir}")
    
    # Check if vJoy DLL exists
    vjoy_dll = r"C:\Program Files\vJoy\x64\vJoyInterface.dll"
    if os.path.exists(vjoy_dll):
        logger.info(f"✓ vJoy DLL found: {vjoy_dll}")
    else:
        logger.warning(f"⚠ vJoy DLL not found: {vjoy_dll}")
    
    # Check system dependencies
    deps_ok, missing_deps = check_system_dependencies()
    if not deps_ok:
        logger.error("System dependency check failed!")
        for dep in missing_deps:
            logger.error(f"  - {dep}")
        return False
    
    logger.info("✓ Environment check completed successfully")
    return True

def check_single_instance():
    """Check if another instance of TrackPro is already running with automatic cleanup of stale locks.
    
    Returns:
        bool: True if this is the only instance, False if another instance is running
    """
    # For development purposes, always allow multiple instances
    if "--dev" in sys.argv or "--force" in sys.argv:
        logger.info("Development mode: Skipping single instance check")
        return True
        
    import win32event
    import win32api
    import winerror
    import tempfile
    import atexit
    import psutil
    
    # Use a named mutex for instance management
    mutex_name = "TrackProSingleInstanceMutex"
    lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
    
    def cleanup_stale_locks():
        """Clean up stale locks and mutexes from crashed instances."""
        logger.info("Cleaning up stale locks...")
        
        # Check for actual TrackPro processes
        trackpro_processes = []
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    process_info = process.info
                    if not process_info['cmdline']:
                        continue
                    
                    # Check for TrackPro executable or Python running TrackPro
                    is_trackpro = False
                    
                    # Skip the current process
                    if process_info['pid'] == os.getpid():
                        continue
                    
                    # Skip build.py processes (avoid flagging build script as TrackPro process)
                    if any('build.py' in str(cmd) for cmd in process_info['cmdline']):
                        continue
                    
                    # Check for TrackPro executable
                    if any('trackpro' in str(cmd).lower() for cmd in process_info['cmdline']):
                        is_trackpro = True
                    
                    # Check for Python processes running TrackPro (but not build script)
                    if (process_info['name'] in ['python.exe', 'pythonw.exe'] and 
                        any('run_app.py' in str(cmd).lower() or 'main.py' in str(cmd).lower()
                            for cmd in process_info['cmdline'])):
                        is_trackpro = True
                    
                    if is_trackpro:
                        trackpro_processes.append(process_info['pid'])
                        
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.warning(f"Error checking for TrackPro processes: {e}")
        
        # If no actual TrackPro processes found, clean up stale locks
        if not trackpro_processes:
            # Remove stale lock file
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info("Removed stale lock file")
                except Exception as e:
                    logger.warning(f"Could not remove stale lock file: {e}")
            
            return True
        else:
            logger.info(f"Found {len(trackpro_processes)} running TrackPro processes: {trackpro_processes}")
            return False
    
    try:
        # First attempt to create mutex
        mutex = win32event.CreateMutex(None, 1, mutex_name)
        last_error = win32api.GetLastError()
        
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            # Mutex exists - check if it's from a real process
            logger.info("Mutex exists, checking for actual running processes...")
            
            if cleanup_stale_locks():
                # No actual processes found, try to create mutex again
                logger.info("No running processes found, attempting to acquire mutex...")
                try:
                    # Release the existing mutex handle
                    win32api.CloseHandle(mutex)
                    
                    # Try to create a new mutex
                    mutex = win32event.CreateMutex(None, 1, mutex_name)
                    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                        logger.warning("Mutex still exists after cleanup")
                        return False
                    
                    logger.info("Successfully acquired mutex after cleanup")
                except Exception as e:
                    logger.error(f"Error acquiring mutex after cleanup: {e}")
                    return False
            else:
                # Real processes found
                logger.info("Another instance of TrackPro is already running!")
                return False
        
        # Successfully created mutex or acquired it after cleanup
        # Ensure mutex is released on exit
        def release_mutex():
            try:
                if mutex:
                    win32event.ReleaseMutex(mutex)
                    win32api.CloseHandle(mutex)
                    logger.info("Released mutex on exit")
            except Exception as e:
                logger.warning(f"Error releasing mutex: {e}")
        
        atexit.register(release_mutex)
        
        # Create lock file with process info
        try:
            lock_data = {
                'pid': os.getpid(),
                'timestamp': time.time(),
                'executable': sys.executable,
                'args': sys.argv
            }
            
            with open(lock_file, 'w') as f:
                import json
                json.dump(lock_data, f, indent=2)
            
            logger.info(f"Created lock file with PID {os.getpid()}")
            
            # Clean up lock file on exit
            def remove_lock_file():
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                        logger.info("Removed lock file on exit")
                    except Exception as e:
                        logger.warning(f"Error removing lock file: {e}")
            
            atexit.register(remove_lock_file)
            
        except Exception as e:
            logger.warning(f"Could not create lock file: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in single instance check: {e}")
        # If there's an error in the check, try cleanup and proceed
        try:
            cleanup_stale_locks()
        except:
            pass
        return True

def show_error_dialog(message):
    """Show an error dialog that works in windowed mode."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QPushButton, QHBoxLayout
        
        # Create QApplication instance if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # For HidHide errors, show a more detailed dialog
        if "HidHide" in message:
            dialog = QDialog()
            dialog.setWindowTitle("TrackPro Error - HidHide Issue")
            dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Add error message
            error_text = QTextEdit()
            error_text.setReadOnly(True)
            error_text.setPlainText(message)
            layout.addWidget(error_text)
            
            # Add detailed information about HidHide
            detail_text = QTextEdit()
            detail_text.setReadOnly(True)
            detail_text.setPlainText(get_hidhide_info())
            layout.addWidget(detail_text)
            
            # Add buttons
            button_layout = QHBoxLayout()
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)
            
            dialog.exec()
        else:
            # Standard error dialog for other errors
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("TrackPro Error")
            error_box.setText(message)
            error_box.exec()
    except Exception:
        # Fallback to console if PyQt fails
        print(message)
        input("Press Enter to exit...")

def get_hidhide_info():
    """Get detailed information about HidHide installation."""
    info = []
    info.append("=== HIDHIDE DIAGNOSTIC INFORMATION ===")
    
    # Check for HidHide service
    try:
        import win32serviceutil
        import win32service
        status = win32serviceutil.QueryServiceStatus('HidHide')
        status_text = {
            win32service.SERVICE_RUNNING: "Running",
            win32service.SERVICE_STOPPED: "Stopped",
            win32service.SERVICE_START_PENDING: "Starting",
            win32service.SERVICE_STOP_PENDING: "Stopping"
        }.get(status[1], f"Unknown ({status[1]})")
        info.append(f"HidHide Service: {status_text}")
    except Exception as e:
        info.append(f"HidHide Service: Error - {str(e)}")
    
    # Check for HidHide registry
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\HidHide") as key:
            info.append("HidHide Registry: Found")
    except Exception as e:
        info.append(f"HidHide Registry: Not found - {str(e)}")
    
    # Check for HidHide device
    try:
        import win32file
        import win32con
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
        info.append("HidHide Device: Accessible")
    except Exception as e:
        info.append(f"HidHide Device: Not accessible - {str(e)}")
    
    # Check for HidHideCLI.exe
    try:
        bundled_cli = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trackpro", "HidHideCLI.exe")
        if os.path.exists(bundled_cli):
            info.append(f"HidHideCLI.exe: Found at {bundled_cli}")
        else:
            # Check common installation paths
            common_paths = [
                r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
                r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    info.append(f"HidHideCLI.exe: Found at {path}")
                    break
            else:
                info.append("HidHideCLI.exe: Not found in common locations")
    except Exception as e:
        info.append(f"HidHideCLI.exe: Error checking - {str(e)}")
    
    # Check for admin privileges
    try:
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            info.append("Admin Privileges: Yes")
        else:
            info.append("Admin Privileges: No - This may be causing the HidHide issue")
    except Exception as e:
        info.append(f"Admin Privileges: Error checking - {str(e)}")
    
    # Add troubleshooting steps
    info.append("\n=== TROUBLESHOOTING STEPS ===")
    info.append("1. Make sure HidHide is installed - Download from https://github.com/ViGEm/HidHide/releases")
    info.append("2. Check if the HidHide service is running in Windows Services")
    info.append("3. Try running TrackPro as Administrator")
    info.append("4. Restart your computer")
    info.append("5. Reinstall HidHide")
    
    return "\n".join(info)

def update_trackpro(update_path):
    """Update TrackPro by replacing files."""
    logger.info(f"Updating TrackPro from {update_path}")
    
    try:
        import shutil
        import tempfile
        
        # Current executable path
        current_exe = os.path.abspath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0])
        logger.info(f"Current executable: {current_exe}")
        
        # Current directory
        current_dir = os.path.dirname(current_exe)
        logger.info(f"Current directory: {current_dir}")
        
        # Create a temporary batch file that will:
        # 1. Wait for our process to exit
        # 2. Copy the update file over the existing file
        # 3. Start the new version
        
        temp_batch = os.path.join(tempfile.gettempdir(), "trackpro_update.bat")
        
        with open(temp_batch, "w") as f:
            f.write("@echo off\n")
            f.write("echo TrackPro Updater\n")
            f.write(f"echo Waiting for process to exit (PID: {os.getpid()})...\n")
            f.write(f"timeout /t 2 /nobreak > nul\n")  # Small initial delay
            f.write(f"taskkill /f /pid {os.getpid()} 2>nul\n")  # Try to force kill the process
            f.write(f"echo Copying update file...\n")
            f.write(f"copy /Y \"{update_path}\" \"{current_exe}\"\n")
            f.write(f"echo Starting new version...\n")
            f.write(f"start \"\" \"{current_exe}\"\n")
            f.write(f"echo Cleanup...\n")
            f.write(f"del \"{update_path}\"\n")
            f.write(f"del \"%~f0\"\n")  # Delete this batch file
        
        logger.info(f"Created update batch file: {temp_batch}")
        
        # Run the batch file with hidden window
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            ["cmd", "/c", temp_batch],
            shell=True,
            creationflags=CREATE_NO_WINDOW
        )
        
        logger.info("Update batch file launched successfully")
        return True
        
    except Exception as e:
        logger.error(f"Update failed: {e}")
        logger.error(traceback.format_exc())
        return False

def show_early_splash():
    """Show an early splash screen immediately to give user feedback."""
    try:
        from PyQt6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QLinearGradient, QBrush
        from trackpro.utils.resource_utils import get_resource_path
        import os
        
        # Try to load our custom logo first
        logo_path = get_resource_path("trackpro/resources/images/trackpro_logo_small.png")
        
        # Debug: Print the exact path being tried
        print(f"DEBUG: Trying to load splash image from: {logo_path}")
        print(f"DEBUG: File exists: {os.path.exists(logo_path)}")
        
        # If packaged, also debug the _MEIPASS contents
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            print(f"DEBUG: Running as packaged app, _MEIPASS = {sys._MEIPASS}")
            try:
                meipass_contents = os.listdir(sys._MEIPASS)
                print(f"DEBUG: _MEIPASS contents: {meipass_contents[:10]}...")  # First 10 items
                # Check for trackpro directory
                trackpro_path = os.path.join(sys._MEIPASS, "trackpro")
                if os.path.exists(trackpro_path):
                    print(f"DEBUG: trackpro directory exists")
                    resources_path = os.path.join(trackpro_path, "resources")
                    if os.path.exists(resources_path):
                        print(f"DEBUG: resources directory exists")
                        images_path = os.path.join(resources_path, "images")
                        if os.path.exists(images_path):
                            print(f"DEBUG: images directory exists")
                            images = os.listdir(images_path)
                            print(f"DEBUG: Images in directory: {images}")
                        else:
                            print(f"DEBUG: images directory missing")
                    else:
                        print(f"DEBUG: resources directory missing")
                else:
                    print(f"DEBUG: trackpro directory missing")
            except Exception as e:
                print(f"DEBUG: Error listing _MEIPASS: {e}")
        
        if os.path.exists(logo_path):
            print(f"DEBUG: Successfully found logo at {logo_path}")
            # Use our custom logo
            splash_pixmap = QPixmap(logo_path)
            if splash_pixmap.isNull():
                print(f"DEBUG: QPixmap failed to load image from {logo_path}")
                raise Exception("QPixmap is null")
            # Scale to appropriate size if needed
            if splash_pixmap.width() > 400 or splash_pixmap.height() > 200:
                splash_pixmap = splash_pixmap.scaled(400, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            print(f"DEBUG: Logo not found, creating programmatic splash screen")
            # Fallback: Create an enhanced splash screen programmatically
            splash_pixmap = QPixmap(500, 300)
            
            # Create gradient background
            painter = QPainter(splash_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Background gradient
            gradient = QLinearGradient(0, 0, 0, 300)
            gradient.setColorAt(0, QColor(40, 44, 52))      # Dark top
            gradient.setColorAt(0.5, QColor(60, 64, 72))    # Mid
            gradient.setColorAt(1, QColor(30, 34, 42))      # Dark bottom
            painter.fillRect(splash_pixmap.rect(), QBrush(gradient))
            
            # Add racing stripes
            painter.setPen(QColor(220, 50, 47, 60))  # Semi-transparent red
            for i in range(0, 600, 40):
                painter.drawLine(int(i), 0, int(i - 300), 300)
            
            # Draw main title with shadow
            title_font = QFont("Arial", 32, QFont.Weight.Bold)
            painter.setFont(title_font)
            
            # Shadow
            painter.setPen(QColor(0, 0, 0, 150))
            painter.drawText(252, 122, "TrackPro")
            
            # Main text
            painter.setPen(QColor(248, 248, 242))  # Off-white
            painter.drawText(250, 120, "TrackPro")
            
            # Subtitle
            subtitle_font = QFont("Arial", 14)
            painter.setFont(subtitle_font)
            painter.setPen(QColor(38, 139, 210))  # Tech blue
            painter.drawText(250, 145, "Racing Telemetry System")
            
            # Status text
            status_font = QFont("Arial", 12)
            painter.setFont(status_font)
            painter.setPen(QColor(255, 193, 7))  # Gold
            painter.drawText(250, 170, "Initializing...")
            
            # Add speedometer icon
            center_x, center_y = 100, 150
            radius = 40
            
            # Outer circle
            painter.setPen(QColor(38, 139, 210, 200))
            painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
            
            # Gauge marks
            painter.setPen(QColor(255, 193, 7))
            import math
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                inner_x = center_x + (radius - 10) * math.cos(rad)
                inner_y = center_y + (radius - 10) * math.sin(rad)
                outer_x = center_x + (radius - 5) * math.cos(rad)
                outer_y = center_y + (radius - 5) * math.sin(rad)
                painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))
            
            # Needle
            needle_angle = math.radians(45)
            needle_x = center_x + (radius - 8) * math.cos(needle_angle)
            needle_y = center_y + (radius - 8) * math.sin(needle_angle)
            painter.setPen(QColor(220, 50, 47))
            painter.drawLine(int(center_x), int(center_y), int(needle_x), int(needle_y))
            
            # Center dot
            painter.setBrush(QBrush(QColor(220, 50, 47)))
            painter.drawEllipse(center_x - 3, center_y - 3, 6, 6)
            
            # Add checkered flag pattern
            flag_x, flag_y = 420, 20
            square_size = 8
            for row in range(4):
                for col in range(4):
                    if (row + col) % 2 == 0:
                        painter.fillRect(flag_x + col * square_size, flag_y + row * square_size,
                                       square_size, square_size, QColor(255, 255, 255, 180))
            
            painter.end()
        
        splash = QSplashScreen(splash_pixmap)
        splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        
        # Add subtle pulsing effect (much less transparent)
        splash._opacity = 1.0
        splash._fade_direction = -0.01  # Much slower and less transparent
        
        def pulse_effect():
            try:
                if hasattr(splash, '_opacity'):
                    splash._opacity += splash._fade_direction
                    if splash._opacity <= 0.9:  # Only fade to 90% opacity (much less transparent)
                        splash._fade_direction = 0.01
                    elif splash._opacity >= 1.0:
                        splash._fade_direction = -0.01
                    splash.setWindowOpacity(splash._opacity)
            except:
                pass
        
        # Create timer for subtle pulsing effect
        pulse_timer = QTimer()
        pulse_timer.timeout.connect(pulse_effect)
        pulse_timer.start(100)  # Slower pulse intervals
        
        # Store timer reference to prevent garbage collection
        splash._pulse_timer = pulse_timer
        
        splash.show()
        
        # Process events to ensure splash is shown
        QApplication.processEvents()
        
        return splash
    except Exception as e:
        logger.error(f"Error creating early splash screen: {e}")
        return None

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='TrackPro - Racing Telemetry System')
    # Xbox controller arguments removed
    parser.add_argument('--dev', action='store_true',
                       help='Development mode (allows multiple instances)')
    parser.add_argument('--force', action='store_true',
                       help='Force start (allows multiple instances)')
    parser.add_argument('--console', action='store_true',
                       help='Keep console window open')
    
    return parser.parse_args()

if __name__ == "__main__":
    # Global declaration for lazy import
    global trackpro_main
    trackpro_main = None
    
    logger.info(f"Starting TrackPro run script at {datetime.now()}")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Log initial information
    logger.info(f"Arguments: {sys.argv}")
    # Xbox controller functionality removed
    logger.info(f"Running as admin: {is_admin()}")
    
    # Check for update mode
    if "/update" in sys.argv:
        try:
            logger.info("Running in update mode...")
            update_path = sys.argv[sys.argv.index("/update") + 1]
            logger.info(f"Update path: {update_path}")
            
            # Replace the executable
            if os.path.exists(update_path):
                update_trackpro(update_path)
            else:
                logger.error(f"Update file not found: {update_path}")
                
            sys.exit(0)
        except Exception as e:
            error_msg = f"Update failed: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            write_error_to_desktop(error_msg)
            sys.exit(1)
            
    # Check if we need to elevate privileges - always require admin
    # Commenting out admin check to allow running without admin privileges
    # if not is_admin():
    #     logger.info("Not running as admin, requesting elevation...")
    #     run_as_admin()
    #     sys.exit(0)
    
    # If we get here, we have admin rights or we're skipping the check
    logger.info("Running the application")
    
    # Verify the environment - exit early if critical issues found
    if not check_environment():
        error_msg = "Critical system dependencies missing. TrackPro cannot start."
        logger.error(error_msg)
        write_error_to_desktop(error_msg, log_file)
        
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("TrackPro cannot start")
            msg.setInformativeText("Critical system dependencies are missing.\n\nPlease check the error report on your desktop for details.")
            msg.setWindowTitle("TrackPro System Check Failed")
            msg.exec()
        except Exception:
            pass
        sys.exit(1)
    
    # Set attribute BEFORE potentially creating QApplication in main()
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    
    # Create QApplication early for splash screen
    app = QApplication(sys.argv)
    app._start_time = time.time()  # Track start time for startup optimizations
    
    # Show early splash screen immediately
    early_splash = show_early_splash()
    
    # Import auth module later to avoid initial circular dependencies
    from Supabase import auth as supabase_auth
    
    # Check if another instance is already running (unless dev/force mode)
    if not (args.dev or args.force) and not check_single_instance():
        logger.warning("Another instance of TrackPro is already running")
        if early_splash:
            early_splash.close()
        if "TrackPro_v" in sys.executable:  # Only show message if running from EXE
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("TrackPro is already running")
            msg.setInformativeText("Another instance of TrackPro is already running. Please close it first.")
            msg.setWindowTitle("TrackPro")
            msg.exec()
        sys.exit(0)
    
    try:
        logger.info("Importing trackpro.main module...")
        # Lazy import to reduce initial load time
        if trackpro_main is None:
            from trackpro.main import main as trackpro_main
        
        # Close early splash before starting main app
        if early_splash:
            early_splash.close()
        
        logger.info("Starting TrackPro main function...")
        # Main application entry point - Supabase client gets initialized here
        trackpro_main()
        
        logger.info("TrackPro main function completed normally")
    except ImportError as e:
        if early_splash:
            early_splash.close()
        error_msg = f"Failed to import TrackPro modules: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        write_error_to_desktop(error_msg, log_file)
        
        # Show error dialog for import errors
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("TrackPro failed to start")
            msg.setInformativeText(f"Missing required modules or dependencies.\n\nError: {str(e)}\n\nPlease check the error report on your desktop for details.")
            msg.setWindowTitle("TrackPro Startup Error")
            msg.exec()
        except Exception:
            pass
            
    except Exception as e:
        if early_splash:
            early_splash.close()
        error_msg = f"Unhandled exception: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        write_error_to_desktop(error_msg, log_file)
        
        # Show error dialog for other exceptions
        try:
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("TrackPro encountered an error")
            msg.setInformativeText(f"An unexpected error occurred during startup.\n\nError: {str(e)}\n\nPlease check the error report on your desktop for details.")
            msg.setWindowTitle("TrackPro Error")
            msg.exec()
        except Exception:
            pass
    
    logger.info("TrackPro run script exiting")
    # Keep the window open if we're in a console
    try:
        if hasattr(sys, 'frozen') and sys.frozen and 'console' in sys.argv:
            input("Press Enter to exit...")
        elif os.isatty(sys.stdout.fileno()):
            input("Press Enter to exit...")
    except:
        pass 