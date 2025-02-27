import sys
import os
import traceback

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.main import main

def show_error_dialog(message):
    """Show an error dialog that works in windowed mode."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QPushButton, QHBoxLayout
        app = QApplication([])
        
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
    # Check for test mode
    test_mode = "--test" in sys.argv
    
    try:
        main()
    except Exception as e:
        error_message = str(e)
        
        # Provide more user-friendly messages for common errors
        if "Invalid joystick axis" in error_message:
            error_message = (
                "Invalid joystick axis detected.\n\n"
                "This may happen if your pedal setup doesn't have all three axes (throttle, brake, clutch).\n\n"
                "Please check your pedal connections and try again. If the issue persists, "
                "try deleting the configuration files in your home directory:\n"
                "- ~/.trackpro/axis_mappings.json\n"
                "- ~/.trackpro/axis_ranges.json"
            )
        elif "Cannot Initialize with HIDHIDE" in error_message:
            error_message = (
                "Cannot Initialize with HidHide\n\n"
                "This error occurs when TrackPro cannot properly initialize the HidHide driver, "
                "which is required to hide your physical pedals from games.\n\n"
                "Possible causes:\n"
                "1. HidHide is not installed\n"
                "2. HidHide service is not running\n"
                "3. You don't have administrator privileges\n"
                "4. HidHideCLI.exe is missing or inaccessible\n\n"
                "See the detailed information below for diagnostics and troubleshooting steps."
            )
        else:
            error_message = f"Error running TrackPro: {error_message}"
            
        # Add traceback for detailed debugging
        error_message += f"\n\nDetailed error information:\n{traceback.format_exc()}"
            
        show_error_dialog(error_message) 