#!/usr/bin/env python3
"""
Voice Chat Debug Test Script

This script tests the voice chat functionality to help debug audio playback issues.
"""

import logging
import sys
import time
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PyQt6.QtCore import QTimer

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_voice_manager():
    """Test the voice manager functionality."""
    try:
        logger.info("🎤 Testing voice manager...")
        
        # Import voice manager
        from trackpro.ui.pages.community.high_quality_voice_manager import HighQualityVoiceManager
        
        # Create voice manager
        voice_manager = HighQualityVoiceManager()
        logger.info("✅ Voice manager created successfully")
        
        # Test device enumeration
        devices = voice_manager.get_available_devices()
        logger.info(f"🎤 Found {len(devices.get('input', []))} input devices and {len(devices.get('output', []))} output devices")
        
        # Test debug stats
        stats = voice_manager.get_debug_stats()
        logger.info(f"🎤 Debug stats: {stats}")
        
        # Test voice chat start (without actually connecting)
        logger.info("🎤 Testing voice chat start...")
        voice_manager.start_voice_chat("ws://localhost:8080", "test-channel")
        
        # Wait a bit for initialization
        time.sleep(2)
        
        # Get updated stats
        stats = voice_manager.get_debug_stats()
        logger.info(f"🎤 Updated debug stats: {stats}")
        
        # Stop voice chat
        voice_manager.stop_voice_chat()
        logger.info("✅ Voice manager test completed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Voice manager test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

def test_voice_server():
    """Test the voice server functionality."""
    try:
        logger.info("🎤 Testing voice server...")
        
        # Import voice server
        from trackpro.high_quality_voice_server import HighQualityVoiceServer
        
        # Create server instance
        server = HighQualityVoiceServer()
        logger.info("✅ Voice server created successfully")
        
        # Test server stats
        stats = server.get_server_stats()
        logger.info(f"🎤 Server stats: {stats}")
        
        logger.info("✅ Voice server test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Voice server test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

def test_audio_devices():
    """Test audio device enumeration."""
    try:
        logger.info("🎤 Testing audio devices...")
        
        import pyaudio
        
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        logger.info(f"🎤 Found {device_count} audio devices")
        
        for i in range(device_count):
            try:
                device_info = audio.get_device_info_by_index(i)
                logger.info(f"🎤 Device {i}: {device_info['name']} (Input: {device_info['maxInputChannels']}, Output: {device_info['maxOutputChannels']})")
            except Exception as e:
                logger.warning(f"🎤 Could not get info for device {i}: {e}")
        
        audio.terminate()
        logger.info("✅ Audio device test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Audio device test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

class VoiceChatDebugWindow(QMainWindow):
    """Simple debug window for testing voice chat."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Chat Debug Tool")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Voice Chat Debug Tool")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Test buttons
        test_voice_manager_btn = QPushButton("Test Voice Manager")
        test_voice_manager_btn.clicked.connect(self.test_voice_manager)
        layout.addWidget(test_voice_manager_btn)
        
        test_voice_server_btn = QPushButton("Test Voice Server")
        test_voice_server_btn.clicked.connect(self.test_voice_server)
        layout.addWidget(test_voice_server_btn)
        
        test_audio_devices_btn = QPushButton("Test Audio Devices")
        test_audio_devices_btn.clicked.connect(self.test_audio_devices)
        layout.addWidget(test_audio_devices_btn)
        
        # Output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)
        
        # Clear button
        clear_btn = QPushButton("Clear Output")
        clear_btn.clicked.connect(self.output_area.clear)
        layout.addWidget(clear_btn)
    
    def log_output(self, message):
        """Add message to output area."""
        self.output_area.append(f"{time.strftime('%H:%M:%S')} - {message}")
    
    def test_voice_manager(self):
        """Test voice manager in GUI."""
        self.log_output("🎤 Testing voice manager...")
        
        def run_test():
            try:
                result = test_voice_manager()
                if result:
                    self.log_output("✅ Voice manager test passed")
                else:
                    self.log_output("❌ Voice manager test failed")
            except Exception as e:
                self.log_output(f"❌ Voice manager test error: {e}")
        
        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    def test_voice_server(self):
        """Test voice server in GUI."""
        self.log_output("🎤 Testing voice server...")
        
        def run_test():
            try:
                result = test_voice_server()
                if result:
                    self.log_output("✅ Voice server test passed")
                else:
                    self.log_output("❌ Voice server test failed")
            except Exception as e:
                self.log_output(f"❌ Voice server test error: {e}")
        
        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    def test_audio_devices(self):
        """Test audio devices in GUI."""
        self.log_output("🎤 Testing audio devices...")
        
        def run_test():
            try:
                result = test_audio_devices()
                if result:
                    self.log_output("✅ Audio device test passed")
                else:
                    self.log_output("❌ Audio device test failed")
            except Exception as e:
                self.log_output(f"❌ Audio device test error: {e}")
        
        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()

def main():
    """Main function."""
    print("🎤 Voice Chat Debug Tool")
    print("=" * 50)
    
    # Test without GUI first
    print("\n1. Testing voice manager...")
    test_voice_manager()
    
    print("\n2. Testing voice server...")
    test_voice_server()
    
    print("\n3. Testing audio devices...")
    test_audio_devices()
    
    print("\n✅ All tests completed!")
    
    # Ask if user wants GUI
    try:
        response = input("\nWould you like to open the GUI debug tool? (y/n): ")
        if response.lower() in ['y', 'yes']:
            app = QApplication(sys.argv)
            window = VoiceChatDebugWindow()
            window.show()
            sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main() 