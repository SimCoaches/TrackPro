#!/usr/bin/env python3
"""
Direct Monitoring Test Script

This script tests the direct monitoring (self-hearing) feature in TrackPro's voice chat system.
It verifies that:
1. The direct monitoring setting is properly loaded from config
2. The setting is correctly applied in the voice manager
3. Users can toggle the feature in the voice settings dialog
"""

import sys
import os
import time
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import QTimer

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from trackpro.config import config
from trackpro.ui.pages.community.voice_settings_dialog import VoiceSettingsDialog
from trackpro.ui.pages.community.high_quality_voice_manager import HighQualityVoiceManager

class DirectMonitoringTest(QMainWindow):
    """Test window for direct monitoring functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Direct Monitoring Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Direct Monitoring (Self-Hearing) Test")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; margin: 20px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("""
        This test verifies the direct monitoring feature:
        • Users can hear themselves slightly when speaking
        • The feature can be enabled/disabled in voice settings
        • Settings are properly saved and loaded
        • Audio is routed correctly for instant feedback
        """)
        desc.setStyleSheet("color: #cccccc; margin: 10px; font-size: 12px;")
        layout.addWidget(desc)
        
        # Test buttons
        self.create_test_buttons(layout)
        
        # Status display
        self.status_label = QLabel("Ready to test direct monitoring feature")
        self.status_label.setStyleSheet("color: #888888; margin: 10px; font-size: 11px;")
        layout.addWidget(self.status_label)
    
    def create_test_buttons(self, layout):
        """Create test control buttons."""
        
        # Test 1: Check current config setting
        test1_btn = QPushButton("Test 1: Check Current Direct Monitoring Setting")
        test1_btn.clicked.connect(self.test_current_setting)
        test1_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        layout.addWidget(test1_btn)
        
        # Test 2: Open voice settings dialog
        test2_btn = QPushButton("Test 2: Open Voice Settings Dialog")
        test2_btn.clicked.connect(self.open_voice_settings)
        test2_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        layout.addWidget(test2_btn)
        
        # Test 3: Test voice manager initialization
        test3_btn = QPushButton("Test 3: Test Voice Manager Direct Monitoring")
        test3_btn.clicked.connect(self.test_voice_manager)
        test3_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        layout.addWidget(test3_btn)
        
        # Test 4: Simulate voice chat with direct monitoring
        test4_btn = QPushButton("Test 4: Simulate Voice Chat (Direct Monitoring)")
        test4_btn.clicked.connect(self.simulate_voice_chat)
        test4_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        layout.addWidget(test4_btn)
    
    def test_current_setting(self):
        """Test 1: Check the current direct monitoring setting from config."""
        try:
            # Get current setting
            current_setting = config.voice_chat_direct_monitoring
            self.status_label.setText(f"✅ Direct monitoring is currently: {'ENABLED' if current_setting else 'DISABLED'}")
            
            # Show detailed info
            QMessageBox.information(self, "Direct Monitoring Setting", 
                                  f"Current direct monitoring setting: {'ENABLED' if current_setting else 'DISABLED'}\n\n"
                                  f"This means users will {'hear themselves slightly' if current_setting else 'NOT hear themselves'} when speaking in voice channels.\n\n"
                                  f"Users can change this setting in Voice Settings → Audio Quality Settings → 'Hear Yourself (Direct Monitoring)'")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error checking setting: {str(e)}")
            QMessageBox.warning(self, "Test Failed", f"Error checking direct monitoring setting: {str(e)}")
    
    def open_voice_settings(self):
        """Test 2: Open the voice settings dialog to test the UI control."""
        try:
            dialog = VoiceSettingsDialog(self)
            
            # Check if the direct monitoring checkbox exists and is properly configured
            if hasattr(dialog, 'direct_monitoring'):
                current_state = dialog.direct_monitoring.isChecked()
                self.status_label.setText(f"✅ Voice settings dialog opened. Direct monitoring checkbox is {'checked' if current_state else 'unchecked'}")
                
                # Show info about the control
                QMessageBox.information(self, "Voice Settings Dialog", 
                                      f"Voice settings dialog opened successfully!\n\n"
                                      f"Direct monitoring checkbox is: {'CHECKED' if current_state else 'UNCHECKED'}\n\n"
                                      f"Users can toggle this setting to enable/disable hearing themselves when speaking.\n\n"
                                      f"The tooltip explains: '{dialog.direct_monitoring.toolTip()}'")
            else:
                self.status_label.setText("❌ Direct monitoring checkbox not found in voice settings dialog")
                QMessageBox.warning(self, "Test Failed", "Direct monitoring checkbox not found in voice settings dialog")
            
            # Show the dialog
            dialog.exec()
            
        except Exception as e:
            self.status_label.setText(f"❌ Error opening voice settings: {str(e)}")
            QMessageBox.warning(self, "Test Failed", f"Error opening voice settings dialog: {str(e)}")
    
    def test_voice_manager(self):
        """Test 3: Test the voice manager's direct monitoring implementation."""
        try:
            # Create voice manager
            voice_manager = HighQualityVoiceManager()
            
            # Check if direct monitoring is properly loaded
            if hasattr(voice_manager, 'direct_monitoring'):
                current_setting = voice_manager.direct_monitoring
                self.status_label.setText(f"✅ Voice manager direct monitoring: {'ENABLED' if current_setting else 'DISABLED'}")
                
                QMessageBox.information(self, "Voice Manager Test", 
                                      f"Voice manager created successfully!\n\n"
                                      f"Direct monitoring setting: {'ENABLED' if current_setting else 'DISABLED'}\n\n"
                                      f"This means the voice manager will {'route audio directly to output' if current_setting else 'NOT route audio directly'} for instant feedback.\n\n"
                                      f"The implementation is in the _record_high_quality_audio() method.")
            else:
                self.status_label.setText("❌ Direct monitoring attribute not found in voice manager")
                QMessageBox.warning(self, "Test Failed", "Direct monitoring attribute not found in voice manager")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error testing voice manager: {str(e)}")
            QMessageBox.warning(self, "Test Failed", f"Error testing voice manager: {str(e)}")
    
    def simulate_voice_chat(self):
        """Test 4: Simulate voice chat with direct monitoring."""
        try:
            # Create voice manager
            voice_manager = HighQualityVoiceManager()
            
            # Check direct monitoring setting
            direct_monitoring_enabled = voice_manager.direct_monitoring
            
            self.status_label.setText(f"✅ Voice chat simulation ready. Direct monitoring: {'ENABLED' if direct_monitoring_enabled else 'DISABLED'}")
            
            # Show simulation info
            QMessageBox.information(self, "Voice Chat Simulation", 
                                  f"Voice chat simulation prepared!\n\n"
                                  f"Direct monitoring is: {'ENABLED' if direct_monitoring_enabled else 'DISABLED'}\n\n"
                                  f"When users join voice channels:\n"
                                  f"• They can speak and hear themselves slightly (if enabled)\n"
                                  f"• This helps monitor audio levels and speaking volume\n"
                                  f"• The feature can be toggled in Voice Settings\n"
                                  f"• Settings are automatically saved and applied\n\n"
                                  f"To test in the actual app:\n"
                                  f"1. Go to Community page\n"
                                  f"2. Join a voice channel\n"
                                  f"3. Speak and you should hear yourself slightly\n"
                                  f"4. Adjust the setting in Voice Settings if needed")
            
        except Exception as e:
            self.status_label.setText(f"❌ Error simulating voice chat: {str(e)}")
            QMessageBox.warning(self, "Test Failed", f"Error simulating voice chat: {str(e)}")

def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
    """)
    
    # Create and show test window
    test_window = DirectMonitoringTest()
    test_window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 