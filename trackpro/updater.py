import os
import sys
import json
import tempfile
import subprocess
import requests
import logging
import ctypes
import psutil
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PyQt6.QtCore import Qt
import time
from trackpro.config import Config

INSTALL_DIR = r"C:\Program Files\TrackPro"

# Configure logger
logger = logging.getLogger(__name__)

# Get the GitHub repository from environment variable or use a default
GITHUB_REPO = "SimCoaches/TrackPro"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "1.5.5"
UPDATE_URL = "https://trackpro.app/api/updates"

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # version, download_url
    no_update_available = pyqtSignal()  # Signal when no update is available
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            logger.info(f"Checking for updates from: {UPDATE_CHECK_URL}")
            logger.info(f"Current version: {CURRENT_VERSION}")
            
            # Add timeout and error handling for network request
            try:
                response = requests.get(UPDATE_CHECK_URL, timeout=5)  # 5 second timeout
                response.raise_for_status()
            except requests.Timeout:
                logger.warning("Update check timed out")
                self.error_occurred.emit("Update check timed out")
                return
            except requests.RequestException as e:
                logger.warning(f"Network error during update check: {e}")
                self.error_occurred.emit("Network error during update check")
                return
            
            latest_release = response.json()
            
            # Log the full release information for debugging
            logger.info(f"GitHub API response: {latest_release.get('name', 'Unknown')} - {latest_release.get('tag_name', 'Unknown')}")
            
            # Check if this is a valid release with a tag
            if 'tag_name' not in latest_release:
                logger.error("Invalid GitHub release format: no tag_name found")
                self.error_occurred.emit("Invalid GitHub release format")
                return
                
            latest_version = latest_release['tag_name'].replace('v', '')
            logger.info(f"Latest version from GitHub: {latest_version}")
            
            # Check if there are assets
            if 'assets' not in latest_release or not latest_release['assets']:
                logger.warning("No assets found in the latest release")
                self.error_occurred.emit("No update assets found")
                return
            
            if self._is_newer_version(latest_version, CURRENT_VERSION):
                logger.info(f"New version available: {latest_version}")
                # Get the .exe asset URL
                download_url = None
                for asset in latest_release.get('assets', []):
                    if asset.get('name', '').endswith('.exe'):
                        download_url = asset.get('browser_download_url')
                        logger.info(f"Download URL: {download_url}")
                        break
                
                if download_url:
                    self.update_available.emit(latest_version, download_url)
                else:
                    logger.error("No .exe asset found in the release")
                    self.error_occurred.emit("No installer found for update")
            else:
                # No update available
                logger.info("No update available")
                self.no_update_available.emit()
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            self.error_occurred.emit(f"Update check failed: {str(e)}")

    def _is_newer_version(self, latest, current):
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            logger.info(f"Comparing versions - Latest: {latest_parts}, Current: {current_parts}")
            
            # Make sure both lists have the same length
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            
            for l, c in zip(latest_parts, current_parts):
                if l > c:
                    logger.info(f"New version detected: {latest} > {current}")
                    return True
                elif l < c:
                    logger.info(f"Current version is newer: {latest} < {current}")
                    return False
            
            logger.info(f"Versions are identical: {latest} == {current}")
            return False
        except Exception as e:
            logger.error(f"Error comparing versions: {str(e)}")
            # In case of error, assume no update is available
            return False

class Updater:
    def __init__(self, parent=None):
        self.parent = parent
        self.checker = UpdateChecker()
        self.checker.update_available.connect(self._on_update_available)
        self.checker.no_update_available.connect(self._on_no_update_available)
        self.checker.error_occurred.connect(self._on_error)
        self.is_checking = False
        self.latest_version = None
        self.download_url = None
        logger.info(f"Updater initialized with current version: {CURRENT_VERSION}")

    def check_for_updates(self, silent=False, manual_check=False):
        """
        Check for updates to the application.
        
        Args:
            silent (bool): If True, don't show any message boxes, just perform the check silently
            manual_check (bool): If True, this is a manual check, so show a "No updates available" message
        """
        if self.is_checking:
            logger.info("Update check already in progress")
            return
            
        self.is_checking = True
        
        logger.info(f"Starting update check - Silent: {silent}, Manual: {manual_check}")
        # Store parameters for later
        self.check_silent = silent
        self.check_manual = manual_check
        
        # Start the update check thread with a delay to not block startup
        QThread.msleep(100)  # Small delay to ensure UI is responsive
        self.checker.start()
    
    def _on_update_available(self, version, download_url):
        logger.info(f"_on_update_available called with version {version}")
        self.latest_version = version
        self.download_url = download_url
        self.is_checking = False
        
        logger.info(f"Update available: v{version}")
        
        # Store the version and download URL for later use
        self.latest_version = version
        self.download_url = download_url
        
        # If we have a parent window, show the update notification in the UI
        if self.parent:
            if not self.check_silent:
                self._show_update_prompt()
            else:
                self.parent.show_update_notification(version)
    
    def _show_update_prompt(self):
        if not self.parent or not self.latest_version or not self.download_url:
            logger.warning("Cannot show update prompt - missing parent, version or download URL")
            return
        
        logger.info(f"Showing update prompt for version v{self.latest_version}")
        
        # Create message box to notify the user of the update
        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Update Available")
        msg.setText(
            f"A new version (v{self.latest_version}) of TrackPro is available.\n\n"
            f"You are currently running v{CURRENT_VERSION}.\n\n"
            "Would you like to download and install the update now?"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        msg.setIcon(QMessageBox.Icon.Information)
        
        choice = msg.exec()
        
        if choice == QMessageBox.StandardButton.Yes:
            logger.info("User chose to update now")
            # Start the download and installation process
            self._download_and_install_update(self.download_url)
        else:
            logger.info("User chose not to update now")
            # Just show the notification that an update is available
            if self.parent:
                self.parent.show_update_notification(self.latest_version)
    
    def _on_no_update_available(self):
        self.is_checking = False
        logger.info("No update available")
        
        # Only show a message if this was a manual check
        if self.check_manual and not self.check_silent and self.parent:
            QMessageBox.information(
                self.parent,
                "No Update Available",
                f"You are running the latest version (v{CURRENT_VERSION}) of TrackPro."
            )
    
    def _on_error(self, error_message):
        """Handle errors during update check."""
        self.is_checking = False
        logger.error(f"Update check error: {error_message}")
        
        # Only show error message if this was a manual check
        if self.check_manual and not self.check_silent and self.parent:
            QMessageBox.warning(
                self.parent,
                "Update Check Failed",
                f"Could not check for updates:\n{error_message}"
            )

    def _download_and_install_update(self, download_url):
        try:
            logger.info(f"Downloading update from: {download_url}")
            
            # Create a progress dialog
            progress = QProgressDialog("Downloading update...", "Cancel", 0, 100, self.parent)
            progress.setWindowTitle("TrackPro Update")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            
            # Get the intended version for better filename
            version_str = self.latest_version if hasattr(self, 'latest_version') else "latest"
            
            # Download the new installer - use Documents folder (less likely to be flagged than temp)
            docs_folder = os.path.expanduser("~/Documents")
            installer_filename = f"TrackPro_Setup_v{version_str}.exe"
            installer_path = os.path.join(docs_folder, installer_filename)
            
            logger.info(f"Downloading installer to user Documents: {installer_path}")
            
            # Download with progress updates
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_length = int(response.headers.get('content-length', 0))
            
            # Use binary mode to ensure the file is written correctly
            with open(installer_path, 'wb') as out_file:
                logger.info(f"Saving installer to: {installer_path}")
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if progress.wasCanceled():
                        logger.info("Download canceled by user")
                        out_file.close()
                        # Delete the partial file
                        try:
                            os.unlink(installer_path)
                        except Exception as e:
                            logger.error(f"Error deleting partial file: {e}")
                        return
                    
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_length > 0:
                        percent = int((downloaded / total_length) * 100)
                        progress.setValue(percent)
                        progress.setLabelText(f"Downloading update... {percent}% ({downloaded/1024/1024:.1f} MB / {total_length/1024/1024:.1f} MB)")
                    else:
                        progress.setLabelText(f"Downloading update... ({downloaded/1024/1024:.1f} MB downloaded)")
            
            progress.setValue(100)
            progress.setLabelText("Download complete!")
            
            logger.info(f"Download complete: {downloaded} bytes to {installer_path}")
            
            # Show a special message if Windows Defender might block the file
            msg = (f"The update has been downloaded successfully to:\n\n{installer_path}\n\n"
                   f"Do you want to install TrackPro v{self.latest_version} now?\n\n"
                   f"The application will need to close during installation.\n\n")
            
            # Add a note about Windows Defender
            msg += ("NOTE: If Windows Defender blocks the installation, you may need to:\n"
                   "1. Click 'More info' then 'Run anyway' in the security dialog\n"
                   "2. Temporarily disable real-time protection in Windows Security settings\n"
                   "3. Add an exclusion for the installer in Windows Security")
            
            # Ask user if they want to proceed with the installation
            proceed = QMessageBox.question(
                self.parent,
                "Ready to Install Update",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if proceed == QMessageBox.StandardButton.No:
                logger.info("User chose to postpone the installation")
                QMessageBox.information(
                    self.parent,
                    "Update Postponed",
                    f"The update has been downloaded but not installed.\n\n"
                    f"You can install it manually by running:\n{installer_path}",
                    QMessageBox.StandardButton.Ok
                )
                return
            
            # Close progress dialog
            progress.close()
            
            # Ensure devices are unhidden before continuing
            logger.info("Disabling HidHide cloaking before update")
            try:
                from trackpro.modern_main import ModernTrackProApp
                if hasattr(QApplication.instance(), 'trackpro_app'):
                    app = QApplication.instance().trackpro_app
                    
                    # First try direct CLI approach - most reliable
                    if hasattr(app, 'hidhide') and hasattr(app.hidhide, '_run_cli'):
                        logger.info("Using direct CLI --cloak-off command")
                        try:
                            cli_result = app.hidhide._run_cli(["--cloak-off"])
                            logger.info(f"Cloak disabled via direct CLI: {cli_result}")
                        except Exception as e:
                            logger.error(f"Error using direct CLI approach: {e}")
                    
                    # Then try the cleanup method as backup
                    logger.info("Calling cleanup with force_unhide=True")
                    app.cleanup(force_unhide=True)
            except Exception as e:
                logger.error(f"Error disabling HidHide cloaking before update: {e}")
            
            # Give Windows a moment to process the cleanup
            import time
            time.sleep(2)
            
            # Create a batch script to handle antivirus exclusions and run the installer
            batch_content = f'''@echo off
echo TrackPro Update Process Started
echo ===================================
echo Current time: %date% %time%
echo Installer path: {installer_path}
echo Target directory: {INSTALL_DIR}
echo New version: {self.latest_version}
echo Current version: {CURRENT_VERSION}
echo ===================================
echo.
echo IMPORTANT: This installer will automatically remove ALL previous
echo TrackPro versions before installing the new version. This ensures
echo a clean installation and prevents disk space issues.
echo.
echo YOUR USER DATA WILL BE PRESERVED:
echo - Calibrations and settings will NOT be deleted
echo - Only old executable files and shortcuts are removed
echo ===================================

echo.
echo Step 1: Terminating all TrackPro processes
echo This is required to allow file deletion and cleanup...
taskkill /F /IM "TrackPro*.exe" 2>NUL
taskkill /F /IM "trackpro*.exe" 2>NUL
taskkill /F /IM "run_app.exe" 2>NUL
echo TrackPro processes terminated
timeout /t 3 /nobreak >NUL

echo.
echo Step 2: Releasing file locks and preparing for installation
echo Waiting for any remaining file handles to be released...
timeout /t 2 /nobreak >NUL

echo.
echo Step 3: Windows Security Check
echo.
echo Checking if Windows Defender might block the installer...
echo.
echo NOTE FOR USERS:
echo If Windows Defender blocks the installation, you have several options:
echo 1. Click "More info" then "Run anyway" in the security dialog
echo 2. Temporarily disable real-time protection in Windows Security
echo 3. Add an exclusion for the installer in Windows Security
echo.
echo Attempting to run Windows Defender scan on installer before execution...
start /wait "Windows Defender Scan" powershell -Command "Start-Process -FilePath 'C:\\Program Files\\Windows Defender\\MpCmdRun.exe' -ArgumentList '-Scan -ScanType 3 -File \"{installer_path}\"' -Verb RunAs -Wait" 2>NUL

echo.
echo Step 4: Preparing Installation Environment
echo The new installer includes automatic cleanup of previous versions.
echo This means it will remove old TrackPro executables, shortcuts, and registry
echo entries before installing the new version. USER DATA (calibrations, settings)
echo will be preserved. This should resolve the issue where previous versions
echo weren't being properly removed.

echo.
echo Step 5: Running installer...
echo This may take a few moments...
echo.
echo IMPORTANT: If Windows Defender shows a warning, select "More info" and then "Run anyway"
echo.
echo Running: "{installer_path}"

REM Open Explorer to the folder containing the installer
explorer /select,"{installer_path}"

REM Try to run the installer with admin privileges
echo.
echo Method 1: Running installer with PowerShell (Admin)...
powershell -Command "Start-Process -FilePath '{installer_path}' -Verb RunAs -Wait"

echo.
echo Step 6: Post-Installation Check
echo.
echo The installer should have completed. Checking for the new version...

REM Check for executable files in various possible locations
echo.
echo 1. Checking AppData\\Local\\TrackPro directory:
if exist "%LOCALAPPDATA%\\TrackPro" (
    echo Contents of %LOCALAPPDATA%\\TrackPro:
    dir "%LOCALAPPDATA%\\TrackPro\\TrackPro*.exe" /b 2>NUL
    if exist "%LOCALAPPDATA%\\TrackPro\\TrackPro*.exe" (
        echo Found TrackPro executable in AppData Local!
        for %%f in ("%LOCALAPPDATA%\\TrackPro\\TrackPro*.exe") do (
            echo Starting new version: %%f
            start "" "%%f"
            goto :success
        )
    )
) else (
    echo Directory not found: %LOCALAPPDATA%\\TrackPro
)

echo.
echo 2. Checking main Program Files directory:
if exist "C:\\Program Files\\TrackPro" (
    echo Contents of C:\\Program Files\\TrackPro:
    dir "C:\\Program Files\\TrackPro\\TrackPro*.exe" /b 2>NUL
    if exist "C:\\Program Files\\TrackPro\\TrackPro*.exe" (
        echo Found TrackPro executable in Program Files!
        for %%f in ("C:\\Program Files\\TrackPro\\TrackPro*.exe") do (
            echo Starting new version: %%f
            start "" "%%f"
            goto :success
        )
    )
) else (
    echo Directory not found: C:\\Program Files\\TrackPro
)

echo.
echo 3. Checking Program Files (x86) directory:
if exist "C:\\Program Files (x86)\\TrackPro" (
    echo Contents of C:\\Program Files (x86)\\TrackPro:
    dir "C:\\Program Files (x86)\\TrackPro\\TrackPro*.exe" /b 2>NUL
    if exist "C:\\Program Files (x86)\\TrackPro\\TrackPro*.exe" (
        echo Found TrackPro executable in Program Files (x86)!
        for %%f in ("C:\\Program Files (x86)\\TrackPro\\TrackPro*.exe") do (
            echo Starting new version: %%f
            start "" "%%f"
            goto :success
        )
    )
) else (
    echo Directory not found: C:\\Program Files (x86)\\TrackPro
)

REM If we get here, installation may have failed
echo.
echo Step 7: Installation Status Check
echo.
echo No TrackPro executable found after installation
echo.
echo This could be due to:
echo 1. Windows Defender blocked the installation
echo 2. The installation was canceled
echo 3. The installer failed to extract files
echo.
echo Please try one of these solutions:
echo 1. Run the installer manually from: {installer_path}
echo 2. Temporarily disable Windows Defender and try again
echo 3. Download the latest version directly from GitHub
echo.
echo Opening the installer one more time for manual installation...
start "" "{installer_path}"
echo.
echo After installation, you can find TrackPro in the Start Menu.
echo.
echo Press any key to exit...
pause
exit /b 1

:success
echo.
echo ===================================
echo TrackPro update completed successfully!
echo The new version should be starting now.
echo ===================================
echo.
echo Press any key to exit...
pause
exit /b 0
'''
            # Save the batch file
            batch_path = os.path.join(os.path.expanduser("~/Documents"), 'trackpro_update.bat')
            with open(batch_path, 'w') as f:
                f.write(batch_content)
            
            logger.info(f"Created interactive batch file: {batch_path}")
            
            # Run the batch file with a visible console to show progress
            cmd_command = f'start "TrackPro Update Process" cmd /k "{batch_path}"'
            
            logger.info(f"Executing command: {cmd_command}")
            # Note: We intentionally don't use CREATE_NO_WINDOW here because we want the user to see the update progress
            subprocess.Popen(cmd_command, shell=True)
            
            # Wait a moment to ensure the process starts
            time.sleep(1)
            
            # Inform user we're closing the application now
            QMessageBox.information(
                self.parent,
                "Update in Progress",
                "The update process is running in a separate window.\n\n"
                "TrackPro will close now. The update will guide you through the installation.\n\n"
                "NOTE: If Windows Security blocks the installer, select 'More info' then 'Run anyway'.",
                QMessageBox.StandardButton.Ok
            )
            
            # Exit the application to allow the update to complete
            logger.info("Exiting application for update to complete")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error during update process: {e}")
            QMessageBox.critical(
                self.parent,
                "Update Failed",
                f"Failed to download and install the update:\n\n{str(e)}\n\n"
                f"Please try updating manually or contact support.",
                QMessageBox.StandardButton.Ok
            )

    def _is_admin(self):
        """Check if the current process has admin privileges."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False 