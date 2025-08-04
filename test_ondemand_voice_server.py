#!/usr/bin/env python3
"""
Test script to demonstrate on-demand voice server startup.

This script simulates the behavior where the voice server is only started
when the first user joins a voice channel, and rooms are created at that moment.
"""

import time
import logging
import subprocess
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

# Add the trackpro directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'trackpro'))

# Import voice server manager
try:
    from trackpro.voice_server_manager import start_voice_server, stop_voice_server, is_voice_server_running
    VOICE_SERVER_AVAILABLE = True
except ImportError as e:
    print(f"Voice server manager not available: {e}")
    VOICE_SERVER_AVAILABLE = False

# Import simple voice client
try:
    from trackpro.simple_voice_client import SimpleVoiceClient
    SIMPLE_VOICE_AVAILABLE = True
except ImportError as e:
    print(f"Simple voice client not available: {e}")
    SIMPLE_VOICE_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceServerTester(QObject):
    """Test class to demonstrate on-demand voice server startup."""
    
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.voice_client = None
        self.test_channel = "test-channel-1"
        self.test_user = "TestUser"
        
    def test_ondemand_startup(self):
        """Test the on-demand server startup functionality."""
        try:
            self.status_updated.emit("🎤 Testing on-demand voice server startup...")
            
            # Check if voice server is currently running
            if is_voice_server_running():
                self.status_updated.emit("⚠️ Voice server is already running")
                return
            
            self.status_updated.emit("🎤 Voice server not running - this is expected")
            
            # Simulate joining a voice channel (this should start the server)
            self.status_updated.emit("🎤 Simulating first user joining voice channel...")
            
            # Start voice server on-demand
            if VOICE_SERVER_AVAILABLE:
                start_voice_server()
                time.sleep(3)  # Wait for server to start
                
                if is_voice_server_running():
                    self.status_updated.emit("✅ Voice server started on-demand successfully!")
                else:
                    self.status_updated.emit("❌ Voice server failed to start on-demand")
                    return
            else:
                self.status_updated.emit("❌ Voice server manager not available")
                return
            
            # Test connecting to the voice channel (this should create the room)
            if SIMPLE_VOICE_AVAILABLE:
                self.status_updated.emit("🎤 Testing voice channel connection...")
                
                self.voice_client = SimpleVoiceClient()
                server_url = "ws://localhost:8080"
                
                # Connect to voice channel - this should create the room
                self.voice_client.start_voice_chat(server_url, self.test_channel, self.test_user)
                
                self.status_updated.emit("✅ Voice channel connection successful!")
                self.status_updated.emit(f"🎤 Room '{self.test_channel}' created on server")
                
                # Wait a bit then disconnect
                time.sleep(2)
                if self.voice_client:
                    self.voice_client.stop_voice_chat()
                    self.status_updated.emit("🎤 Disconnected from voice channel")
                
            else:
                self.status_updated.emit("❌ Simple voice client not available")
            
            # Test stopping the server
            self.status_updated.emit("🎤 Testing server shutdown...")
            if VOICE_SERVER_AVAILABLE:
                stop_voice_server()
                time.sleep(1)
                
                if not is_voice_server_running():
                    self.status_updated.emit("✅ Voice server stopped successfully!")
                else:
                    self.status_updated.emit("⚠️ Voice server may still be running")
            
        except Exception as e:
            self.status_updated.emit(f"❌ Error during test: {str(e)}")
            logger.error(f"Test error: {e}")

class TestWindow(QMainWindow):
    """Simple test window to demonstrate the functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("On-Demand Voice Server Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Add title
        title = QLabel("On-Demand Voice Server Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Add description
        description = QLabel(
            "This test demonstrates how the voice server is only started\n"
            "when the first user joins a voice channel, and rooms are\n"
            "created automatically at that moment."
        )
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)
        
        # Add test button
        self.test_button = QPushButton("Run On-Demand Test")
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.test_button.clicked.connect(self.run_test)
        layout.addWidget(self.test_button)
        
        # Add status display
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.status_display)
        
        # Create tester
        self.tester = VoiceServerTester()
        self.tester.status_updated.connect(self.update_status)
        
        # Add initial status
        self.update_status("🚀 Ready to test on-demand voice server startup")
        
    def run_test(self):
        """Run the on-demand voice server test."""
        self.test_button.setEnabled(False)
        self.test_button.setText("Running Test...")
        self.status_display.clear()
        self.update_status("🎬 Starting on-demand voice server test...")
        
        # Run test in a separate thread to avoid blocking UI
        QTimer.singleShot(100, self.tester.test_ondemand_startup)
        
        # Re-enable button after test
        QTimer.singleShot(10000, self.reset_button)
    
    def reset_button(self):
        """Reset the test button."""
        self.test_button.setEnabled(True)
        self.test_button.setText("Run On-Demand Test")
    
    def update_status(self, message):
        """Update the status display."""
        timestamp = time.strftime("%H:%M:%S")
        self.status_display.append(f"[{timestamp}] {message}")

def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)
    
    # Check if required components are available
    if not VOICE_SERVER_AVAILABLE:
        print("❌ Voice server manager not available")
        return
    
    if not SIMPLE_VOICE_AVAILABLE:
        print("❌ Simple voice client not available")
        return
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 