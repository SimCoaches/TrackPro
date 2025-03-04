import os
import sys
import json
import tempfile
import subprocess
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

# Get the GitHub repository from environment variable or use a default
GITHUB_REPO = os.getenv('TRACKPRO_GITHUB_REPO', 'SimCoaches/TrackPro')
CURRENT_VERSION = "1.2.2"  # This should match your current version
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # version, download_url
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            response = requests.get(UPDATE_CHECK_URL)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release['tag_name'].replace('v', '')
            
            if self._is_newer_version(latest_version, CURRENT_VERSION):
                # Get the .exe asset URL
                for asset in latest_release['assets']:
                    if asset['name'].endswith('.exe'):
                        download_url = asset['browser_download_url']
                        self.update_available.emit(latest_version, download_url)
                        break
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _is_newer_version(self, latest, current):
        latest_parts = [int(x) for x in latest.split('.')]
        current_parts = [int(x) for x in current.split('.')]
        
        for l, c in zip(latest_parts, current_parts):
            if l > c:
                return True
            elif l < c:
                return False
        return False

class Updater:
    def __init__(self, parent=None):
        self.parent = parent
        self.checker = UpdateChecker()
        self.checker.update_available.connect(self._on_update_available)
        self.checker.error_occurred.connect(self._on_error)

    def check_for_updates(self):
        self.checker.start()

    def _on_update_available(self, version, download_url):
        reply = QMessageBox.question(
            self.parent,
            "Update Available",
            f"A new version (v{version}) of TrackPro is available. Would you like to update now?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._download_and_install_update(download_url)

    def _on_error(self, error_message):
        # Silently log the error - no need to bother user about update check failures
        print(f"Update check failed: {error_message}")

    def _download_and_install_update(self, download_url):
        try:
            # Download the new installer
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                installer_path = tmp_file.name

            # Create a batch file to:
            # 1. Wait for the current process to end
            # 2. Run the new installer
            # 3. Clean up temporary files
            batch_content = f'''@echo off
timeout /t 2 /nobreak
start "" "{installer_path}"
del "%~f0"
'''
            batch_path = os.path.join(tempfile.gettempdir(), 'trackpro_update.bat')
            with open(batch_path, 'w') as f:
                f.write(batch_content)

            # Execute the batch file and exit the application
            subprocess.Popen(['cmd', '/c', batch_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            sys.exit(0)

        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Update Error",
                f"Failed to download and install update: {str(e)}"
            ) 