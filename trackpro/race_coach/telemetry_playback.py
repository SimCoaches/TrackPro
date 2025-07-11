import logging
import os
import json
import time
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class TelemetryPlaybackEngine(QObject):
    '''Task 1.3: Telemetry Playback Engine
    
    Loads saved telemetry files and replays them as real-time stream to analysis systems.
    Can simulate live data feed from stored sessions.
    '''
    
    # Signals for playback events
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_resumed = pyqtSignal()
    telemetry_frame = pyqtSignal(dict)  # Emits telemetry data frames
    lap_completed = pyqtSignal(int, float)  # lap_number, lap_time
    session_completed = pyqtSignal()
    
    def __init__(self, telemetry_directory=None):
        '''Initialize the playback engine.'''
        super().__init__()
        
        # Set up telemetry directory
        if telemetry_directory is None:
            self.telemetry_directory = Path(os.path.expanduser("~/Documents/TrackPro/Telemetry"))
        else:
            self.telemetry_directory = Path(telemetry_directory)
            
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.playback_speed = 1.0  # 1.0 = real-time, 2.0 = 2x speed, 0.5 = half speed
        self.current_session = None
        self.current_lap_index = 0
        self.current_frame_index = 0
        
        # Data storage
        self.session_data = []  # List of lap data dictionaries
        self.current_lap_data = []  # Current lap's telemetry points
        
        # Threading
        self.playback_thread = None
        self.stop_event = threading.Event()
        
        # Registered callbacks (for compatibility with existing telemetry systems)
        self.telemetry_callbacks = []
        
        logger.info(f"Telemetry playback engine initialized with directory: {self.telemetry_directory}")

    def get_available_sessions(self):
        """Get list of available session folders for playback."""
        if not self.telemetry_directory.exists():
            logger.warning(f"Telemetry directory does not exist: {self.telemetry_directory}")
            return []
        
        session_folders = [d for d in self.telemetry_directory.iterdir() if d.is_dir()]
        session_folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Sort by modification time (newest first)
        
        logger.info(f"Found {len(session_folders)} available sessions for playback")
        return session_folders
    
    def load_session(self, session_path):
        """Load a session for playback."""
        try:
            session_path = Path(session_path)
            
            if not session_path.exists():
                logger.error(f"Session path does not exist: {session_path}")
                return False
            
            # Find all lap files in the session
            lap_files = sorted(session_path.glob("lap_*.json"))
            
            if not lap_files:
                logger.error(f"No lap files found in session: {session_path}")
                return False
            
            # Load all lap data
            self.session_data = []
            total_frames = 0
            
            for lap_file in lap_files:
                try:
                    with open(lap_file, 'r') as f:
                        lap_data = json.load(f)
                        self.session_data.append(lap_data)
                        
                        # Count telemetry frames for this lap
                        if 'data' in lap_data:
                            frame_count = len(lap_data['data'])
                        else:
                            # Fallback to legacy format
                            frame_count = len(lap_data.get('timestamps', []))
                        
                        total_frames += frame_count
                        
                except Exception as e:
                    logger.error(f"Error loading lap file {lap_file}: {e}")
                    continue
            
            if not self.session_data:
                logger.error(f"No valid lap data loaded from session: {session_path}")
                return False
            
            self.current_session = session_path
            self.current_lap_index = 0
            self.current_frame_index = 0
            
            # Extract session info from first lap metadata
            first_lap = self.session_data[0]
            metadata = first_lap.get('metadata', {})
            track_name = metadata.get('track_name', 'Unknown Track')
            car_name = metadata.get('car_name', 'Unknown Car')
            
            logger.info(f"Loaded session: {session_path.name}")
            logger.info(f"Track: {track_name}, Car: {car_name}")
            logger.info(f"Laps: {len(self.session_data)}, Total frames: {total_frames}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading session {session_path}: {e}")
            return False
    
    def start_playback(self, loop=False, start_from_lap=0):
        """Start telemetry playback."""
        if not self.session_data:
            logger.error("No session data loaded for playback")
            return False
        
        if self.is_playing:
            logger.warning("Playback already in progress")
            return False
        
        self.current_lap_index = max(0, min(start_from_lap, len(self.session_data) - 1))
        self.current_frame_index = 0
        self.is_playing = True
        self.is_paused = False
        self.stop_event.clear()
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=self._playback_worker, args=(loop,), daemon=True)
        self.playback_thread.start()
        
        self.playback_started.emit()
        logger.info(f"Started telemetry playback from lap {start_from_lap}")
        return True
    
    def stop_playback(self):
        """Stop telemetry playback."""
        if not self.is_playing:
            return
        
        self.is_playing = False
        self.is_paused = False
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        
        self.playback_stopped.emit()
        logger.info("Stopped telemetry playback")
    
    def pause_playback(self):
        """Pause telemetry playback."""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.playback_paused.emit()
            logger.info("Paused telemetry playback")
    
    def resume_playback(self):
        """Resume telemetry playback."""
        if self.is_playing and self.is_paused:
            self.is_paused = False
            self.playback_resumed.emit()
            logger.info("Resumed telemetry playback")
    
    def set_playback_speed(self, speed):
        """Set playback speed multiplier."""
        self.playback_speed = max(0.1, min(10.0, speed))  # Clamp between 0.1x and 10x
        logger.info(f"Set playback speed to {self.playback_speed}x")
    
    def seek_to_lap(self, lap_number):
        """Seek to a specific lap."""
        if not self.session_data:
            return False
        
        lap_number = max(0, min(lap_number, len(self.session_data) - 1))
        self.current_lap_index = lap_number
        self.current_frame_index = 0
        
        logger.info(f"Seeked to lap {lap_number}")
        return True
    
    def register_telemetry_callback(self, callback):
        """Register a callback function to receive telemetry data."""
        if callback not in self.telemetry_callbacks:
            self.telemetry_callbacks.append(callback)
            logger.info(f"Registered telemetry callback: {callback.__name__}")
    
    def unregister_telemetry_callback(self, callback):
        """Unregister a telemetry callback."""
        if callback in self.telemetry_callbacks:
            self.telemetry_callbacks.remove(callback)
            logger.info(f"Unregistered telemetry callback: {callback.__name__}")
    
    def get_session_info(self):
        """Get information about the currently loaded session."""
        if not self.session_data:
            return None
        
        first_lap = self.session_data[0]
        metadata = first_lap.get('metadata', {})
        
        return {
            'session_path': str(self.current_session) if self.current_session else None,
            'lap_count': len(self.session_data),
            'track_name': metadata.get('track_name', 'Unknown Track'),
            'car_name': metadata.get('car_name', 'Unknown Car'),
            'total_frames': sum(len(lap.get('data', lap.get('timestamps', []))) for lap in self.session_data),
            'session_id': metadata.get('session_id'),
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_lap': self.current_lap_index,
            'playback_speed': self.playback_speed
        }
    
    def _playback_worker(self, loop=False):
        """Worker thread for telemetry playback."""
        try:
            while self.is_playing and not self.stop_event.is_set():
                # Check if we've finished all laps
                if self.current_lap_index >= len(self.session_data):
                    if loop:
                        self.current_lap_index = 0
                        self.current_frame_index = 0
                        logger.info("Looping session playback")
                    else:
                        logger.info("Session playback completed")
                        self.session_completed.emit()
                        break
                
                # Get current lap data
                current_lap = self.session_data[self.current_lap_index]
                
                # Use new format if available, otherwise fall back to legacy format
                if 'data' in current_lap:
                    telemetry_frames = current_lap['data']
                else:
                    # Convert legacy format to new format
                    telemetry_frames = self._convert_legacy_format(current_lap)
                
                # Check if we've finished this lap
                if self.current_frame_index >= len(telemetry_frames):
                    # Emit lap completed signal
                    metadata = current_lap.get('metadata', {})
                    lap_number = metadata.get('lap_number', self.current_lap_index)
                    lap_time = metadata.get('lap_time', 0.0)
                    
                    self.lap_completed.emit(lap_number, lap_time)
                    
                    # Move to next lap
                    self.current_lap_index += 1
                    self.current_frame_index = 0
                    continue
                
                # Wait if paused
                while self.is_paused and self.is_playing:
                    time.sleep(0.1)
                    if self.stop_event.is_set():
                        return
                
                # Get current telemetry frame
                telemetry_frame = telemetry_frames[self.current_frame_index].copy()
                
                # Add playback metadata
                telemetry_frame['_playback'] = True
                telemetry_frame['_playback_lap'] = self.current_lap_index
                telemetry_frame['_playback_frame'] = self.current_frame_index
                telemetry_frame['_playback_speed'] = self.playback_speed
                
                # Calculate timing for real-time simulation
                frame_time = 1.0 / 60.0  # Assume 60Hz capture rate
                sleep_time = frame_time / self.playback_speed
                
                # Emit telemetry data
                self.telemetry_frame.emit(telemetry_frame)
                
                # Call registered callbacks
                for callback in self.telemetry_callbacks:
                    try:
                        callback(telemetry_frame)
                    except Exception as e:
                        logger.error(f"Error in telemetry callback {callback.__name__}: {e}")
                
                # Move to next frame
                self.current_frame_index += 1
                
                # Sleep to maintain timing
                time.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Error in playback worker: {e}")
        finally:
            self.is_playing = False
    
    def _convert_legacy_format(self, lap_data):
        """Convert legacy lap data format to new format."""
        frames = []
        
        # Extract arrays from legacy format
        timestamps = lap_data.get('timestamps', [])
        throttle = lap_data.get('throttle', [])
        brake = lap_data.get('brake', [])
        steering = lap_data.get('steering', [])
        speed = lap_data.get('speed', [])
        track_position = lap_data.get('track_position', [])
        session_time = lap_data.get('session_time', [])
        rpm = lap_data.get('rpm', [])
        
        # Convert to frame format
        for i in range(len(timestamps)):
            frame = {
                'timestamp': timestamps[i] if i < len(timestamps) else 0,
                'throttle': throttle[i] if i < len(throttle) else 0,
                'brake': brake[i] if i < len(brake) else 0,
                'steering': steering[i] if i < len(steering) else 0,
                'speed': speed[i] if i < len(speed) else 0,
                'track_position': track_position[i] if i < len(track_position) else 0,
                'session_time': session_time[i] if i < len(session_time) else 0,
                'rpm': rpm[i] if i < len(rpm) else 0,
                'clutch': 0  # Not available in legacy format
            }
            frames.append(frame)
        
        return frames
