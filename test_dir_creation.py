import os
import json
import shutil
from pathlib import Path

# Test creating the TrackPro sessions directory
print("Testing directory creation...")

# Get the user's home directory and create the paths
home_dir = os.path.expanduser("~")
documents_dir = os.path.join(home_dir, "Documents")
trackpro_dir = os.path.join(documents_dir, "TrackPro")
sessions_dir = os.path.join(trackpro_dir, "Sessions")

# Create the directory structure
print(f"Creating directory: {sessions_dir}")
os.makedirs(sessions_dir, exist_ok=True)

# Create a test session file
test_session_file = os.path.join(sessions_dir, "active_sessions.json")
print(f"Creating test file: {test_session_file}")

# Sample session data
sample_data = {
    "test-session-123": {
        "track_name": "Test Track",
        "car_name": "Test Car",
        "track_config": "Grand Prix",
        "session_type": "Race",
        "timestamp": "2025-05-19T01:58:00.000000",
        "user_id": "test-user-456"
    }
}

# Write test data to the file
with open(test_session_file, 'w') as f:
    json.dump(sample_data, f)
    print("Test data written to file")

# Read the data back to verify
print("Reading test data back...")
try:
    with open(test_session_file, 'r') as f:
        read_data = json.load(f)
        if read_data == sample_data:
            print("Success! Data read matches written data.")
        else:
            print("Error: Read data does not match written data.")
            print(f"Written: {sample_data}")
            print(f"Read: {read_data}")
except Exception as e:
    print(f"Error reading file: {e}")

print(f"\nTest completed. Directory created at: {sessions_dir}")
print(f"Test file created at: {test_session_file}") 