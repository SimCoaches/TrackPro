import logging
import time
import threading
import json
import os
import ctypes
from pathlib import Path

logger = logging.getLogger(__name__)

class IRacingAPI:
    """Interface for communication with the iRacing API."""
    
    def __init__(self):
        """Initialize the iRacing API interface."""
        self.connected = False
        self.session_info = None
        self.telemetry_data = {}
        self.current_track = None
        self.current_car = None
        self.driver_id = None
        self.session_type = None
        self.connection_thread = None
        self.stop_thread = False
        
        # Callbacks
        self.on_connected = None
        self.on_disconnected = None
        self.on_telemetry_update = None
        self.on_session_info_update = None
        
        logger.info("iRacing API interface initialized")
    
    def is_iracing_running(self):
        """Check if iRacing is actually running on the system."""
        try:
            # Use Windows API to check if iRacing process is running
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            
            titles = []
            
            def foreach_window(hwnd, lParam):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    titles.append(buff.value)
                return True
            
            EnumWindows(EnumWindowsProc(foreach_window), 0)
            
            # Check if any window title contains 'iRacing'
            return any('iRacing' in title for title in titles)
        except Exception as e:
            logger.error(f"Error checking if iRacing is running: {e}")
            return False
    
    def connect(self):
        """Connect to the iRacing API."""
        if self.connected:
            logger.warning("Already connected to iRacing API")
            return True
        
        logger.info("Connecting to iRacing API...")
        
        # First, check if iRacing is actually running
        if not self.is_iracing_running():
            logger.error("iRacing is not running")
            return False
        
        # Start a background thread to handle the connection and data retrieval
        self.stop_thread = False
        self.connection_thread = threading.Thread(target=self._connection_worker)
        self.connection_thread.daemon = True
        self.connection_thread.start()
        
        return True
    
    def disconnect(self):
        """Disconnect from the iRacing API."""
        if not self.connected:
            logger.warning("Not connected to iRacing API")
            return
        
        logger.info("Disconnecting from iRacing API...")
        self.stop_thread = True
        
        if self.connection_thread and self.connection_thread.is_alive():
            self.connection_thread.join(timeout=1.0)
        
        self.connected = False
        
        if self.on_disconnected:
            self.on_disconnected()
        
        logger.info("Disconnected from iRacing API")
    
    def _connection_worker(self):
        """Background worker thread to handle iRacing API communication."""
        # Check if iRacing is still running
        if not self.is_iracing_running():
            logger.error("Lost connection to iRacing")
            return
        
        # Set connection state
        self.connected = True
        
        # Retrieve real session info from iRacing (in a real implementation)
        # Here we're using placeholder data for demonstration
        self.current_track = "Watkins Glen"
        self.current_car = "Porsche 911 GT3 Cup"
        self.driver_id = 12345
        self.session_type = "Practice"
        
        # Call connection callback
        if self.on_connected:
            self.on_connected(self.current_track, self.current_car)
        
        # Telemetry updates in a loop
        lap_number = 1
        
        while not self.stop_thread:
            # Check if iRacing is still running
            if not self.is_iracing_running():
                logger.error("Lost connection to iRacing")
                self.connected = False
                if self.on_disconnected:
                    self.on_disconnected()
                break
            
            # Simulate telemetry data (in a real implementation, get this from iRacing)
            timestamp = time.time()
            self.telemetry_data = {
                'timestamp': timestamp,
                'lap_number': lap_number,
                'speed': 120 + (timestamp % 10) * 5,
                'rpm': 5000 + (timestamp % 8) * 500,
                'gear': 4,
                'Throttle': 0.8 + (timestamp % 5) * 0.05,
                'Brake': 0.0,
                'Clutch': 0.0,
                'steering': 0.1 * (timestamp % 7 - 3),
                'position_x': 100 + timestamp % 100,
                'position_y': 200 + timestamp % 50,
                'position_z': 0,
                'lap_time': 90.0 + (timestamp % 5),
                'last_lap_time': 92.5,
                'best_lap_time': 89.8,
            }
            
            # Call telemetry update callback
            if self.on_telemetry_update:
                self.on_telemetry_update(self.telemetry_data)
            
            # Simulate occasional lap completion
            if timestamp % 20 < 0.1:
                lap_number += 1
                logger.debug(f"Completed lap {lap_number-1}")
                
                # Simulate session info update
                if self.on_session_info_update:
                    session_info = {
                        'track': self.current_track,
                        'car': self.current_car,
                        'driver_id': self.driver_id,
                        'session_type': self.session_type,
                        'lap_number': lap_number,
                        'total_laps': lap_number,
                        'best_lap_time': min(89.8, 90.0 - (lap_number % 5) * 0.2),
                    }
                    self.on_session_info_update(session_info)
            
            # Sleep for a short time to simulate telemetry update frequency
            time.sleep(0.1)
    
    def get_current_track(self):
        """Get the current track name."""
        return self.current_track
    
    def get_current_car(self):
        """Get the current car name."""
        return self.current_car
    
    def get_telemetry(self):
        """Get the latest telemetry data."""
        return self.telemetry_data
    
    def get_session_info(self):
        """Get the current session information."""
        return self.session_info 