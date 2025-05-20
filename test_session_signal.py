import os
import sys
import json
import time
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import pyqtSignal, QObject

# Path to our active_sessions.json file
documents_path = os.path.expanduser("~\\Documents")
trackpro_path = os.path.join(documents_path, "TrackPro")
sessions_path = os.path.join(trackpro_path, "Sessions")
session_file = os.path.join(sessions_path, "active_sessions.json")

# Create directory if it doesn't exist
os.makedirs(sessions_path, exist_ok=True)

# Simple API class to simulate SimpleIRacingAPI
class SimpleAPI(QObject):
    new_trackpro_session_created = pyqtSignal(str)
    
    def create_new_session(self, session_id):
        print(f"Creating new session with ID: {session_id}")
        self.new_trackpro_session_created.emit(session_id)

# Test UI
class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Session Signal Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Create our simple API
        self.api = SimpleAPI()
        
        # Connect to the signal
        self.api.new_trackpro_session_created.connect(self.on_new_session)
        
        # UI setup
        layout = QVBoxLayout()
        
        # Button to create a new session
        self.create_btn = QPushButton("Create New Test Session")
        self.create_btn.clicked.connect(self.create_session)
        layout.addWidget(self.create_btn)
        
        # Button to check for session file
        self.check_btn = QPushButton("Check Session File")
        self.check_btn.clicked.connect(self.check_session_file)
        layout.addWidget(self.check_btn)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Text area for log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        self.setLayout(layout)
        
        # Log initial file status
        self.add_log(f"Session file path: {session_file}")
        self.check_session_file()
    
    def add_log(self, message):
        """Add a message to the log"""
        self.log.append(message)
        print(message)
    
    def create_session(self):
        """Create a new test session"""
        try:
            # Generate a unique ID
            import uuid
            session_id = f"test-{uuid.uuid4()}"
            
            # Create or update the session file
            try:
                # Load existing sessions if file exists
                sessions_data = {}
                if os.path.exists(session_file):
                    with open(session_file, 'r') as f:
                        sessions_data = json.load(f)
            except Exception as e:
                self.add_log(f"Error loading sessions: {e}")
                sessions_data = {}
            
            # Add the new session
            sessions_data[session_id] = {
                'track_name': "Test Track",
                'car_name': "Test Car",
                'track_config': "Grand Prix",
                'session_type': "Race",
                'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S"),
                'user_id': "test-user-456"
            }
            
            # Save to file
            with open(session_file, 'w') as f:
                json.dump(sessions_data, f)
            
            self.status_label.setText(f"Created session: {session_id}")
            self.add_log(f"Created new session with ID: {session_id}")
            
            # Emit the signal
            self.api.create_new_session(session_id)
            
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
            self.add_log(f"Error creating session: {e}")
    
    def check_session_file(self):
        """Check if the session file exists and display its contents"""
        try:
            if os.path.exists(session_file):
                self.add_log("Session file exists!")
                with open(session_file, 'r') as f:
                    data = json.load(f)
                self.add_log(f"Found {len(data)} sessions in file")
                for session_id, session_data in data.items():
                    self.add_log(f"- Session: {session_id}, Track: {session_data.get('track_name')}, Car: {session_data.get('car_name')}")
            else:
                self.add_log("Session file does not exist")
        except Exception as e:
            self.add_log(f"Error checking session file: {e}")
    
    def on_new_session(self, session_id):
        """Handle the new session signal"""
        self.add_log(f"SIGNAL RECEIVED: New session with ID: {session_id}")
        self.status_label.setText(f"Received signal for session: {session_id}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_()) 