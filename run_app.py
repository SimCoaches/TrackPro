import sys
import os
import traceback
import ctypes
import subprocess
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.main import main

def is_admin():
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin(args=None):
    """Re-run the script with admin privileges."""
    if not is_admin():
        if args is None:
            args = sys.argv[:]
        
        # Quote the arguments to handle spaces
        args = [f'"{arg}"' if ' ' in arg and not arg.startswith('"') else arg for arg in args]
        args_str = ' '.join(args)
        
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args_str, None, 1)
        return True
    return False

def check_single_instance():
    """Check if another instance of TrackPro is already running.
    
    Returns:
        bool: True if this is the only instance, False if another instance is running
    """
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
        status_text = "Unknown"
        if status[1] == win32service.SERVICE_RUNNING:
            status_text = "Running"
        elif status[1] == win32service.SERVICE_STOPPED:
            status_text = "Stopped"
        elif status[1] == win32service.SERVICE_START_PENDING:
            status_text = "Starting"
        elif status[1] == win32service.SERVICE_STOP_PENDING:
            status_text = "Stopping"
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

if __name__ == "__main__":
    # Check for update mode
    if "/update" in sys.argv:
        # When running in update mode, we need admin privileges
        if not is_admin() and run_as_admin():
            sys.exit(0)
        
        # Get the batch path from command line arguments
        batch_path = None
        for i, arg in enumerate(sys.argv):
            if arg == "/update" and i + 1 < len(sys.argv):
                batch_path = sys.argv[i + 1].strip('"')
                break
        
        if batch_path and os.path.exists(batch_path):
            print(f"Running update batch file with admin privileges: {batch_path}")
            
            # Show a message to confirm admin privileges are active
            try:
                from PyQt5.QtWidgets import QApplication, QMessageBox
                # Create QApplication instance if it doesn't exist
                app = QApplication.instance()
                if app is None:
                    app = QApplication(sys.argv)
                
                QMessageBox.information(
                    None,
                    "TrackPro Update - Admin Mode",
                    "TrackPro is now running with administrator privileges.\n\n"
                    "The update will be installed in the same location as your current version.\n\n"
                    f"Installation directory: {os.path.dirname(os.path.abspath(__file__))}\n\n"
                    "Please wait while the update is being installed..."
                )
            except Exception as e:
                print(f"Could not show admin confirmation dialog: {e}")
            
            # Run the batch file
            subprocess.Popen(['cmd', '/c', batch_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            sys.exit(0)
        else:
            print(f"Error: Update batch file not found or invalid: {batch_path}")
            try:
                from PyQt5.QtWidgets import QApplication, QMessageBox
                # Create QApplication instance if it doesn't exist
                app = QApplication.instance()
                if app is None:
                    app = QApplication(sys.argv)
                
                QMessageBox.critical(
                    None,
                    "TrackPro Update Error",
                    f"The update batch file was not found or is invalid:\n{batch_path}\n\n"
                    "Please try updating again or download the latest version manually from:\n"
                    "https://github.com/TrackPro/releases/latest"
                )
            except Exception:
                pass
            sys.exit(1)
    
    # Try to ensure HidHide cloaking is disabled before starting
    try:
        print("Initializing HidHide to disable cloaking before startup...")
        # Try to import and initialize HidHide
        from trackpro.hidhide import HidHideClient
        
        # Initialize with fail_silently=True so the app can continue even if HidHide fails
        hidhide = HidHideClient(fail_silently=True)
        
        # Try multiple approaches to ensure cloaking is disabled
        if hidhide.functioning:
            # Try CLI first (most reliable)
            cli_result = hidhide._run_cli(["--cloak-off"], retry_count=3)
            print(f"Cloak disabled via CLI before startup: {cli_result}")
            
            # Try API method as backup
            api_result = hidhide.set_cloak_state(False)
            print(f"Cloak disabled via API before startup: {api_result}")
            
            # If device name is known, try to unhide specific devices
            if hasattr(hidhide, 'config') and hidhide.config.get('device_name'):
                device_name = hidhide.config.get('device_name')
            else:
                # Fallback to common device names
                device_name = "Sim Coaches P1 Pro Pedals"
            
            print(f"Finding all devices matching: {device_name}")
            matching_devices = hidhide.find_all_matching_devices(device_name)
            if matching_devices:
                for device_path in matching_devices:
                    try:
                        # Try unhide by instance path
                        unhide_result = hidhide.unhide_device(device_path)
                        print(f"Unhid device '{device_path}' via API: {unhide_result}")
                    except Exception as e:
                        print(f"Error unhiding device via API: {e}")
                        
                        # Fallback to CLI if available
                        try:
                            unhide_cmd_result = hidhide._run_cli(["--dev-unhide", device_path])
                            print(f"Unhid device via CLI: {unhide_cmd_result}")
                        except Exception as e2:
                            print(f"Error unhiding device via CLI: {e2}")
        else:
            print(f"HidHide not functioning, skipping pre-startup cloaking control. Error context: {hidhide.error_context}")
        
    except Exception as e:
        print(f"Error during HidHide pre-startup: {e}")
        # Try direct CLI execution as last resort
        try:
            # Try to find the CLI executable
            cli_path = None
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "trackpro", "HidHideCLI.exe"),
                r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
                r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    cli_path = path
                    break
            
            if cli_path:
                # Use CREATE_NO_WINDOW flag to hide console window
                CREATE_NO_WINDOW = 0x08000000
                # Also use DETACHED_PROCESS for maximum hiding
                creationflags = CREATE_NO_WINDOW | 0x00000008  # DETACHED_PROCESS
                
                # Try to disable cloaking and unhide devices
                subprocess.run([cli_path, "--cloak-off"], creationflags=creationflags, timeout=5)
                print("Disabled HidHide cloaking via direct CLI execution")
                
                # Try to find and unhide specific devices
                try:
                    dev_list_result = subprocess.run(
                        [cli_path, "--dev-list"],
                        creationflags=creationflags,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if dev_list_result.returncode == 0 and dev_list_result.stdout:
                        for line in dev_list_result.stdout.splitlines():
                            if "VID_1DD2" in line and "PID_2735" in line:  # Match Sim Coaches P1 Pro Pedals
                                device_id = line.split('"')[1] if '"' in line else line.strip()
                                subprocess.run(
                                    [cli_path, "--dev-unhide", device_id],
                                    creationflags=creationflags,
                                    timeout=5
                                )
                                print(f"Unhid device via direct CLI: {device_id}")
                except Exception as e2:
                    print(f"Error unhiding devices via direct CLI: {e2}")
        except Exception as e2:
            print(f"Failed to run HidHideCLI directly before startup: {e2}")
            # Continue anyway, as the main app will try to initialize HidHide properly

    # Check for test mode
    test_mode = "--test" in sys.argv
    
    # Check if another instance is already running
    if not check_single_instance() and "--force" not in sys.argv:
        # Show a message about the existing instance
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            # Create QApplication instance if it doesn't exist
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            result = QMessageBox.question(
                None, 
                "TrackPro Already Running",
                "Another instance of TrackPro is already running.\n\n"
                "Running multiple instances can cause conflicts with vJoy devices.\n\n"
                "Do you want to continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result == QMessageBox.No:
                sys.exit(0)
                
        except Exception as e:
            print(f"Error showing instance warning: {e}")
            # Just print a message and exit
            print("Another instance of TrackPro is already running. Exiting.")
            sys.exit(0)
    
    try:
        # Run the main application
        sys.exit(main())
    except Exception as e:
        error_message = f"Unhandled error: {str(e)}\n\n{traceback.format_exc()}"
        print(error_message)
        show_error_dialog(error_message)
        sys.exit(1) 