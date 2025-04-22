import sys
import os
import traceback
import ctypes
import subprocess
import time
import logging
from datetime import datetime
from PyQt5 import QtWebEngineWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Set higher logging level for noisy HTTP and Supabase libraries
for library in ['urllib3', 'httpcore', 'httpx', 'hpack', 'gotrue', 'postgrest', 'urllib3.connection', 'urllib3.connectionpool', 'urllib3.poolmanager', 'httpcore.connection', 'httpx.client', 'h11', 'h2', 'requests', 'supafunc']:
    logging.getLogger(library).setLevel(logging.CRITICAL)

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

# Set up logging
# File logging has been removed
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("TrackPro_Run")

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.main import main

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

def write_error_to_desktop(error_msg):
    """Write error message to desktop so user can see it"""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        error_file = os.path.join(desktop, "TrackPro_Error.txt")
        
        with open(error_file, 'w') as f:
            f.write(f"TrackPro Error: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(error_msg)
            f.write("\n\nPlease report this error to the TrackPro support team.")
        
        logger.info(f"Error details written to {error_file}")
    except Exception as e:
        logger.error(f"Could not write error file: {e}")

def check_environment():
    """Check environment for potential issues"""
    logger.info("Checking environment...")
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check if trackpro module directory exists
    trackpro_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trackpro")
    if os.path.exists(trackpro_dir):
        logger.info(f"TrackPro module directory exists: {trackpro_dir}")
    else:
        logger.error(f"TrackPro module directory missing: {trackpro_dir}")
    
    # Check if vJoy DLL exists
    vjoy_dll = r"C:\Program Files\vJoy\x64\vJoyInterface.dll"
    if os.path.exists(vjoy_dll):
        logger.info(f"vJoy DLL found: {vjoy_dll}")
    else:
        logger.error(f"vJoy DLL not found: {vjoy_dll}")
    
    # Check if running from PyInstaller bundle
    is_frozen = getattr(sys, 'frozen', False)
    logger.info(f"Running from frozen application: {is_frozen}")
    
    if is_frozen:
        logger.info(f"Executable path: {sys.executable}")
        
    return True

def check_single_instance():
    """Check if another instance of TrackPro is already running.
    
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
    
    # Use a named mutex for instance management
    mutex_name = "TrackProSingleInstanceMutex"
    
    try:
        # Try to create a named mutex
        mutex = win32event.CreateMutex(None, 1, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            # Another instance is already running
            print("Another instance of TrackPro is already running!")
            return False
            
        # Ensure mutex is released on exit
        def release_mutex():
            if mutex:
                win32event.ReleaseMutex(mutex)
        atexit.register(release_mutex)
        
        # Create a lock file as a backup method
        lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
        
        # Check if the lock file exists and is recent
        if os.path.exists(lock_file):
            # Check if the file is recent (less than 1 minute old)
            if (os.path.getmtime(lock_file) > (time.time() - 60)):
                # Try to find a TrackPro process
                try:
                    import psutil
                    for process in psutil.process_iter(['name']):
                        if process.info['name'] == 'python.exe' or process.info['name'] == 'pythonw.exe':
                            try:
                                cmd_line = process.cmdline()
                                if any('trackpro' in arg.lower() for arg in cmd_line) and process.pid != os.getpid():
                                    print(f"Found existing TrackPro process (PID: {process.pid})")
                                    return False
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                continue
                except ImportError:
                    # If psutil is not available, just use the lock file approach
                    pass
        
        # Create or update lock file
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
            
        # Clean up lock file on exit
        def remove_lock_file():
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass
        atexit.register(remove_lock_file)
        
        return True
    except Exception as e:
        print(f"Error in single instance check: {e}")
        # If there's an error in the check, proceed anyway
        return True

def show_error_dialog(message):
    """Show an error dialog that works in windowed mode."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QPushButton, QHBoxLayout
        
        # Set attribute BEFORE creating QApplication implicitly or explicitly
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

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
            
            dialog.exec_()
        else:
            # Standard error dialog for other errors
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("TrackPro Error")
            error_box.setText(message)
            error_box.exec_()
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
        subprocess.Popen(
            ["cmd", "/c", temp_batch],
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        logger.info("Update batch file launched successfully")
        return True
        
    except Exception as e:
        logger.error(f"Update failed: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info(f"Starting TrackPro run script at {datetime.now()}")
    
    # Log initial information
    logger.info(f"Arguments: {sys.argv}")
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
    
    # Verify the environment
    check_environment()
    
    # Import auth module later to avoid initial circular dependencies
    from Supabase import auth as supabase_auth
    
    # Check if another instance is already running
    if not check_single_instance():
        logger.warning("Another instance of TrackPro is already running")
        if "TrackPro_v" in sys.executable:  # Only show message if running from EXE
            from PyQt5.QtWidgets import QApplication, QMessageBox
            # Ensure attribute is set before potentially creating QApplication here
            QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
            app = QApplication([]) # Ensure QApplication exists before showing message box
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("TrackPro is already running")
            msg.setInformativeText("Another instance of TrackPro is already running. Please close it first.")
            msg.setWindowTitle("TrackPro")
            msg.exec_()
        sys.exit(0)
    
    # Set attribute BEFORE potentially creating QApplication in main()
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    try:
        logger.info("Importing trackpro.main module...")
        from trackpro.main import main
        
        logger.info("Starting TrackPro main function...")
        # Main application entry point - Supabase client gets initialized here
        main()
        
        logger.info("TrackPro main function completed normally")
    except ImportError as e:
        error_msg = f"Failed to import TrackPro modules: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        write_error_to_desktop(error_msg)
    except Exception as e:
        error_msg = f"Unhandled exception: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        write_error_to_desktop(error_msg)
    
    logger.info("TrackPro run script exiting")
    # Keep the window open if we're in a console
    try:
        if hasattr(sys, 'frozen') and sys.frozen and 'console' in sys.argv:
            input("Press Enter to exit...")
        elif os.isatty(sys.stdout.fileno()):
            input("Press Enter to exit...")
    except:
        pass  # Not a console 