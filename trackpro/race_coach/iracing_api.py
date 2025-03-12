import logging
import time
import threading
import json
import os
import ctypes
import traceback
from pathlib import Path
import sys
import io

# Add irsdk import
try:
    import irsdk
except ImportError:
    logging.error("irsdk module not found. Please install it using 'pip install pyirsdk'")

logger = logging.getLogger(__name__)

class IRacingAPI:
    """Interface for communication with the iRacing API."""
    
    def __init__(self):
        """Initialize the iRacing API interface."""
        self.connected = False
        self.session_info_str = None
        self.telemetry_data = {}
        self.current_track = None
        self.current_car = None
        self.driver_id = None
        self.session_type = None
        self.connection_thread = None
        self.stop_thread = False
        self.last_session_update = 0
        
        # Initialize iRacing SDK
        try:
            self.ir = irsdk.IRSDK()
            logger.info("iRacing SDK initialized")
        except Exception as e:
            logger.error(f"Failed to initialize iRacing SDK: {e}")
            self.ir = None
        
        # Callbacks
        self.on_connected = None
        self.on_disconnected = None
        self.on_telemetry_update = None
        self.on_session_info_update = None
        
        logger.info("iRacing API interface initialized")
    
    def is_iracing_running(self):
        """Check if iRacing is actually running on the system."""
        if self.ir:
            try:
                # First try to establish or check connection
                is_connected = self.ir.startup()
                logger.debug(f"ir.startup() returned: {is_connected}")
                
                # If connected, check if properly initialized
                if is_connected:
                    is_initialized = self.ir.is_initialized
                    is_connected_status = self.ir.is_connected
                    logger.debug(f"iRacing status - initialized: {is_initialized}, connected: {is_connected_status}")
                    return is_initialized and is_connected_status
                return False
            except Exception as e:
                logger.error(f"Error checking iRacing connection via SDK: {e}")
                logger.error(traceback.format_exc())
                return False
        else:
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
                has_iracing = any('iRacing' in title for title in titles)
                logger.debug(f"Window check for iRacing: {has_iracing}")
                return has_iracing
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
            logger.error("iRacing is not running or not properly detected")
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
        
        # Shutdown iRacing SDK connection
        if self.ir:
            try:
                self.ir.shutdown()
                logger.info("iRacing SDK shutdown completed")
            except Exception as e:
                logger.error(f"Error shutting down iRacing SDK: {e}")
        
        if self.on_disconnected:
            self.on_disconnected()
        
        logger.info("Disconnected from iRacing API")
    
    def _connection_worker(self):
        """Background worker thread to handle iRacing API communication."""
        logger.info("Connection worker thread started")
        
        # Check if iRacing is still running
        if not self.is_iracing_running():
            logger.error("Lost connection to iRacing before worker thread started")
            return
        
        # Set connection state
        self.connected = True
        logger.info("Connection state set to connected")
        
        # Ensure we have a valid iRacing SDK connection
        if not self.ir:
            logger.error("iRacing SDK not initialized")
            self.connected = False
            return
        
        # Get initial session information and establish connection
        try:
            # Get available variables
            if hasattr(self.ir, 'var_headers_names'):
                var_headers = self.ir.var_headers_names
                logger.info(f"Available telemetry variables: {var_headers[:10]}... (showing first 10)")
            
            # Start session update callback
            self.update_session_info()
            
            # Keep trying to get track and car info for a bit
            max_attempts = 30  # Try for 3 seconds
            for attempt in range(max_attempts):
                self.update_session_info()
                if self.current_track and self.current_car:
                    break
                time.sleep(0.1)
            
            # Check if we got the info
            if self.current_track and self.current_car:
                logger.info(f"Connected to iRacing - Track: {self.current_track}, Car: {self.current_car}")
                if self.on_connected:
                    self.on_connected(self.current_track, self.current_car)
            else:
                logger.warning("Connected to iRacing but couldn't get track or car info")
                # Set defaults if we couldn't get the real info
                if not self.current_track:
                    self.current_track = "Unknown Track"
                    logger.warning("Using default track name")
                if not self.current_car:
                    self.current_car = "Unknown Car"
                    logger.warning("Using default car name")
                if self.on_connected:
                    logger.info("Calling on_connected callback with default values")
                    self.on_connected(self.current_track, self.current_car)
                    
        except Exception as e:
            logger.error(f"Error in connection setup: {e}")
            logger.error(traceback.format_exc())
            self.current_track = "Error retrieving track"
            self.current_car = "Error retrieving car"
            self.session_type = "Unknown"
            if self.on_connected:
                logger.info("Calling on_connected callback with error values")
                self.on_connected(self.current_track, self.current_car)
        
        logger.info("Entering telemetry update loop")
        # Telemetry updates in a loop
        update_counter = 0
        while not self.stop_thread:
            # Check if we're still connected to iRacing
            if not (self.ir.is_initialized and self.ir.is_connected):
                logger.error("Lost connection to iRacing during telemetry loop")
                self.connected = False
                if self.on_disconnected:
                    self.on_disconnected()
                break
            
            # Get real telemetry data from iRacing
            try:
                # Freeze the buffer to ensure consistent data
                self.ir.freeze_var_buffer_latest()
                
                # Update session info periodically
                if update_counter % 100 == 0:  # Check every ~10 seconds
                    self.update_session_info()
                
                # Build telemetry data dictionary from iRacing SDK
                self.telemetry_data = self.get_telemetry_data()
                
                # Call telemetry update callback
                if self.on_telemetry_update:
                    self.on_telemetry_update(self.telemetry_data)
                
                # Create session info object with current state
                session_info = {
                    'track': self.current_track,
                    'car': self.current_car,
                    'driver_id': self.driver_id,
                    'session_type': self.session_type,
                    'lap_number': self.ir['Lap'] if 'Lap' in self.ir else 0,
                    'total_laps': self.ir['SessionLapsTotal'] if 'SessionLapsTotal' in self.ir else 0,
                    'best_lap_time': self.ir['LapBestLapTime'] if 'LapBestLapTime' in self.ir else 0,
                }
                
                # Call session info update callback
                if self.on_session_info_update:
                    self.on_session_info_update(session_info)
                
                # Unfreeze buffer
                self.ir.unfreeze_var_buffer_latest()
                
                update_counter += 1
            except Exception as e:
                logger.error(f"Error retrieving telemetry data: {e}")
                logger.error(traceback.format_exc())
            
            # Sleep for a short time to not overload the CPU
            time.sleep(0.1)  # 100ms to avoid excessive CPU usage
    
    def get_telemetry_data(self):
        """Get current telemetry data as a dictionary."""
        data = {}
        
        try:
            # Add timestamp
            data['timestamp'] = time.time()
            
            # Standard telemetry values
            keys_to_check = [
                'Lap', 'Speed', 'RPM', 'Gear', 'Throttle', 'Brake', 'Clutch', 
                'SteeringWheelAngle', 'LapCurrentLapTime', 'LapLastLapTime', 
                'LapBestLapTime', 'SessionLapsTotal'
            ]
            
            for key in keys_to_check:
                if key in self.ir:
                    # Check if it's a numeric value and convert if needed
                    value = self.ir[key]
                    if key == 'Speed':
                        # Convert to km/h
                        value = value * 3.6 if value is not None else 0
                    data[key] = value
                else:
                    data[key] = 0  # Default value
            
            # Handle special cases
            if 'CarIdxLapDistPct' in self.ir:
                value = self.ir['CarIdxLapDistPct']
                # Check if it's a list/array and get our driver's value
                if isinstance(value, list) and len(value) > 0:
                    driver_idx = self.ir['DriverInfo']['DriverCarIdx'] if 'DriverInfo' in self.ir and 'DriverCarIdx' in self.ir['DriverInfo'] else 0
                    if 0 <= driver_idx < len(value):
                        data['position_x'] = value[driver_idx]
                    else:
                        data['position_x'] = 0
                else:
                    data['position_x'] = 0
            else:
                data['position_x'] = 0
            
            # Add y and z positions as 0 for now
            data['position_y'] = 0
            data['position_z'] = 0
            
            # Rename some keys to match the expected format
            data['lap_number'] = data.get('Lap', 0)
            data['lap_time'] = data.get('LapCurrentLapTime', 0)
            data['last_lap_time'] = data.get('LapLastLapTime', 0)
            data['best_lap_time'] = data.get('LapBestLapTime', 0)
            data['steering'] = data.get('SteeringWheelAngle', 0)
            
        except Exception as e:
            logger.error(f"Error building telemetry data: {e}")
            logger.error(traceback.format_exc())
        
        return data
    
    def update_session_info(self):
        """Update session information using the correct API method."""
        try:
            # Check if session info has been updated
            current_update = self.ir.session_info_update if hasattr(self.ir, 'session_info_update') else 0
            last_update = self.last_session_update
            
            if current_update != last_update:
                logger.info(f"Session info update detected: {last_update} -> {current_update}")
                self.last_session_update = current_update
                
                # First try direct dictionary access as it's more reliable
                yaml_string = ""
                yaml_parsing_successful = False
                
                # Try direct access method first
                try:
                    logger.info("Trying direct dictionary access for session info")
                    
                    # Try accessing session info as a dictionary
                    for key in ['WeekendInfo', 'DriverInfo', 'SessionInfo']:
                        if key in self.ir:
                            logger.info(f"Direct access to {key} succeeded")
                    
                    if 'WeekendInfo' in self.ir and 'TrackDisplayName' in self.ir['WeekendInfo']:
                        self.current_track = self.ir['WeekendInfo']['TrackDisplayName']
                        logger.info(f"Found track via direct access: {self.current_track}")
                        
                    if 'DriverInfo' in self.ir and 'DriverCarIdx' in self.ir['DriverInfo'] and 'Drivers' in self.ir['DriverInfo']:
                        idx = self.ir['DriverInfo']['DriverCarIdx']
                        if 0 <= idx < len(self.ir['DriverInfo']['Drivers']):
                            driver = self.ir['DriverInfo']['Drivers'][idx]
                            if 'CarScreenName' in driver:
                                self.current_car = driver['CarScreenName']
                                logger.info(f"Found car via direct access: {self.current_car}")
                            if 'UserID' in driver:
                                self.driver_id = driver['UserID']
                        
                    if 'SessionInfo' in self.ir and 'Sessions' in self.ir['SessionInfo'] and len(self.ir['SessionInfo']['Sessions']) > 0:
                        if 'SessionType' in self.ir['SessionInfo']['Sessions'][0]:
                            self.session_type = self.ir['SessionInfo']['Sessions'][0]['SessionType']
                    
                    # If we got all the information we need, consider it successful
                    if self.current_track and self.current_car and self.session_type:
                        logger.info("Successfully retrieved all session info via direct dictionary access")
                        return
                except Exception as e:
                    logger.error(f"Error with direct dictionary access: {e}")
                
                # If direct access didn't get everything, try YAML parsing as fallback
                if not self.current_track or not self.current_car or not self.session_type:
                    try:
                        # Get the YAML session string
                        yaml_string = self.get_yaml_session_info()
                        
                        if yaml_string:
                            logger.info(f"Got YAML session info ({len(yaml_string)} characters)")
                            # Store session info string
                            self.session_info_str = yaml_string
                            
                            # Extract track and car info from YAML string
                            try:
                                # Extract track name
                                import re
                                track_match = re.search(r'TrackDisplayName: (.+?)\n', yaml_string)
                                if track_match:
                                    self.current_track = track_match.group(1).strip()
                                    logger.info(f"Found track: {self.current_track}")
                                
                                # Extract car name - this is more complex as we need to find our car
                                driver_idx_match = re.search(r'DriverCarIdx: (\d+)', yaml_string)
                                if driver_idx_match:
                                    driver_idx = int(driver_idx_match.group(1))
                                    
                                    # Find the car name for this driver idx
                                    driver_section_match = re.search(r'CarIdx: ' + str(driver_idx) + r'[\s\S]+?CarScreenName: (.+?)\n', yaml_string)
                                    if driver_section_match:
                                        self.current_car = driver_section_match.group(1).strip()
                                        logger.info(f"Found car: {self.current_car}")
                                    
                                    # Try to find driver ID
                                    driver_id_match = re.search(r'CarIdx: ' + str(driver_idx) + r'[\s\S]+?UserID: (\d+)', yaml_string)
                                    if driver_id_match:
                                        self.driver_id = int(driver_id_match.group(1))
                                        logger.debug(f"Found driver ID: {self.driver_id}")
                                
                                # Extract session type
                                session_match = re.search(r'SessionType: (.+?)\n', yaml_string)
                                if session_match:
                                    self.session_type = session_match.group(1).strip()
                                    logger.info(f"Found session type: {self.session_type}")
                            except Exception as e:
                                logger.error(f"Error extracting info from YAML: {e}")
                            else:
                                logger.warning("Failed to get YAML session info, using direct access only")
                    except Exception as e:
                        logger.error(f"Error getting session info: {e}")
                        logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Error updating session info: {e}")
            logger.error(traceback.format_exc())
    
    def get_yaml_session_info(self):
        """Use python's built-in io.StringIO to capture YAML output"""
        try:
            # Create a StringIO object to capture the output
            buffer = io.StringIO()
            
            # Try different approaches to get session info
            if hasattr(self.ir, 'parse_yaml_async'):
                # Check if parse_yaml_async is callable before trying to call it
                if callable(self.ir.parse_yaml_async):
                    # Try parse_yaml_async method if available (newer versions)
                    self.ir.parse_yaml_async(buffer)
                    return buffer.getvalue()
                else:
                    logger.warning("parse_yaml_async exists but is not callable")
            elif hasattr(self.ir, 'parse_to'):
                # Check if parse_to is callable before trying to call it
                if callable(self.ir.parse_to):
                    # Use the parse_to method with the correct file path
                    # Create a temporary file to write to
                    import tempfile
                    temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yaml')
                    temp_path = temp_file.name
                    temp_file.close()  # Close it so irsdk can write to it
                    
                    try:
                        # Parse to the temporary file
                        self.ir.parse_to(temp_path)
                        
                        # Read the file contents
                        with open(temp_path, 'r') as f:
                            content = f.read()
                        
                        # Clean up
                        os.unlink(temp_path)
                        return content
                    except Exception as e:
                        logger.error(f"Error parsing to file: {e}")
                        # Clean up even on error
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                else:
                    logger.warning("parse_to exists but is not callable")
            
            # Try direct access method for session info
            logger.info("Attempting to get session info through direct access")
            # First check if session_info is available directly
            if hasattr(self.ir, 'session_info'):
                session_info = self.ir.session_info
                if session_info:
                    # Convert to string if it's not already a string
                    if isinstance(session_info, str):
                        return session_info
                    else:
                        return str(session_info)
            
            # Fallback: Try to access ir._ir_sdk.yaml_file directly (but this is unsafe)
            if hasattr(self.ir, '_ir_sdk') and hasattr(self.ir._ir_sdk, 'yaml_file'):
                yaml_str = self.ir._ir_sdk.yaml_file
                if yaml_str:
                    return yaml_str
            
            # Another fallback: Try to use the __str__ representation
            yaml_str = str(self.ir)
            if yaml_str and len(yaml_str) > 100:  # Basic sanity check
                return yaml_str
                
            return ""
        except Exception as e:
            logger.error(f"Error getting YAML session info: {e}")
            logger.warning("Failed to get YAML session info")
            return ""
    
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
        return self.session_info_str 