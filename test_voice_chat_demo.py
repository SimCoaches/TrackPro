#!/usr/bin/env python3
"""
Voice Chat Demo Script

This script demonstrates the enhanced voice chat functionality with:
- User name highlighting when speaking
- Multiple simultaneous users
- Push-to-talk toggle
- Real-time speaking status updates
"""

import sys
import os
import time
import random
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from trackpro.ui.pages.community.community_page import VoiceChannelWidget

class VoiceChatDemo(QMainWindow):
    """Demo window for voice chat functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TrackPro Voice Chat Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("TrackPro Voice Chat Demo")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff; margin: 20px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("""
        This demo shows the enhanced voice chat features:
        • User names highlight when speaking (blue color + bold)
        • Multiple users can speak simultaneously
        • Push-to-talk toggle button
        • Real-time speaking status updates
        • Mute/Deafen controls
        """)
        desc.setStyleSheet("color: #cccccc; margin: 10px; font-size: 14px;")
        layout.addWidget(desc)
        
        # Create voice channel widget
        channel_data = {
            'id': 'demo_channel',
            'name': 'Racing Team Voice',
            'type': 'voice'
        }
        
        self.voice_widget = VoiceChannelWidget(channel_data)
        layout.addWidget(self.voice_widget)
        
        # Demo controls
        demo_layout = QVBoxLayout()
        
        # Demo speaking simulation
        self.simulate_speaking_btn = QPushButton("Simulate User Speaking")
        self.simulate_speaking_btn.clicked.connect(self.simulate_speaking)
        self.simulate_speaking_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        demo_layout.addWidget(self.simulate_speaking_btn)
        
        # Stop speaking simulation
        self.stop_speaking_btn = QPushButton("Stop Speaking Simulation")
        self.stop_speaking_btn.clicked.connect(self.stop_speaking_simulation)
        self.stop_speaking_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        demo_layout.addWidget(self.stop_speaking_btn)
        
        # Add multiple speakers
        self.multiple_speakers_btn = QPushButton("Simulate Multiple Speakers")
        self.multiple_speakers_btn.clicked.connect(self.simulate_multiple_speakers)
        self.multiple_speakers_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        demo_layout.addWidget(self.multiple_speakers_btn)
        
        layout.addLayout(demo_layout)
        
        # Status label
        self.status_label = QLabel("Ready to demo voice chat features")
        self.status_label.setStyleSheet("color: #888888; margin: 10px; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # Demo variables
        self.speaking_simulation_active = False
        self.speaking_thread = None
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def simulate_speaking(self):
        """Simulate a user speaking."""
        if not self.voice_widget.participants:
            self.status_label.setText("No participants to simulate speaking")
            return
        
        # Pick a random participant
        participant = random.choice(self.voice_widget.participants)
        user_name = participant['name']
        
        # Add to speaking users
        self.voice_widget.add_speaking_user(user_name)
        self.status_label.setText(f"Simulated {user_name} speaking")
        
        # Auto-remove after 3 seconds
        QTimer.singleShot(3000, lambda: self.voice_widget.remove_speaking_user(user_name))
    
    def stop_speaking_simulation(self):
        """Stop all speaking simulation."""
        self.voice_widget.speaking_users.clear()
        self.voice_widget.update_participants_list()
        self.status_label.setText("Stopped all speaking simulation")
    
    def simulate_multiple_speakers(self):
        """Simulate multiple users speaking simultaneously."""
        if not self.voice_widget.participants:
            self.status_label.setText("No participants to simulate speaking")
            return
        
        # Start speaking simulation thread
        if not self.speaking_simulation_active:
            self.speaking_simulation_active = True
            self.speaking_thread = threading.Thread(target=self._run_speaking_simulation, daemon=True)
            self.speaking_thread.start()
            self.status_label.setText("Started multiple speakers simulation")
        else:
            self.speaking_simulation_active = False
            self.status_label.setText("Stopped multiple speakers simulation")
    
    def _run_speaking_simulation(self):
        """Run the speaking simulation in a separate thread."""
        while self.speaking_simulation_active:
            try:
                # Pick random participants to speak
                num_speakers = random.randint(1, min(3, len(self.voice_widget.participants)))
                speakers = random.sample(self.voice_widget.participants, num_speakers)
                
                # Add speakers
                for participant in speakers:
                    self.voice_widget.add_speaking_user(participant['name'])
                
                # Wait 2-4 seconds
                time.sleep(random.uniform(2, 4))
                
                # Remove speakers
                for participant in speakers:
                    self.voice_widget.remove_speaking_user(participant['name'])
                
                # Wait 1-3 seconds before next round
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Error in speaking simulation: {e}")
                break

def main():
    """Run the voice chat demo."""
    app = QApplication(sys.argv)
    
    # Create and show the demo window
    demo = VoiceChatDemo()
    demo.show()
    
    print("TrackPro Voice Chat Demo")
    print("Features demonstrated:")
    print("• User names highlight when speaking (blue color + bold)")
    print("• Multiple users can speak simultaneously")
    print("• Push-to-talk toggle button")
    print("• Real-time speaking status updates")
    print("• Mute/Deafen controls")
    print("\nUse the demo buttons to simulate different scenarios!")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 