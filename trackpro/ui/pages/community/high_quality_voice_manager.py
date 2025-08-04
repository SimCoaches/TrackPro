"""
High-Quality Voice Chat Manager

Provides professional-grade voice chat with advanced audio processing,
noise suppression, echo cancellation, and high-quality audio settings.
"""

import logging
import threading
import asyncio
import json
import queue
import numpy as np
import pyaudio
import websockets
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class HighQualityVoiceManager(QObject):
    """Advanced voice chat manager with high-quality audio processing."""
    
    voice_data_received = pyqtSignal(bytes)
    user_joined_voice = pyqtSignal(str)
    user_left_voice = pyqtSignal(str)
    voice_error = pyqtSignal(str)
    audio_level_changed = pyqtSignal(float)  # Input level for UI meters
    connected = pyqtSignal()  # Signal when WebSocket connects
    disconnected = pyqtSignal()  # Signal when WebSocket disconnects
    
    def __init__(self):
        super().__init__()
        self.audio = None
        self.is_recording = False
        self.is_playing = False
        self.websocket = None
        self.voice_thread = None
        
        # Load settings from config
        self.load_settings_from_config()
        
        # Audio processing buffers
        self.input_buffer = queue.Queue(maxsize=100)
        self.output_buffer = queue.Queue(maxsize=100)
        self.echo_buffer = []  # For echo cancellation
        
        # Audio streams
        self.input_stream = None
        self.output_stream = None
        
        # Debug counters
        self.debug_stats = {
            'audio_sent': 0,
            'audio_received': 0,
            'audio_played': 0,
            'websocket_messages': 0,
            'errors': 0
        }
        
        # Connect signals for audio playback
        self.voice_data_received.connect(self._play_incoming_audio)
        
        # Initialize PyAudio
        self.setup_audio()
        
        logger.info("🎤 HighQualityVoiceManager initialized with debugging enabled")
    
    def load_settings_from_config(self):
        """Load voice chat settings from config."""
        try:
            from trackpro.config import config
            
            # Ultra-low latency audio settings
            self.sample_rate = config.voice_chat_sample_rate
            self.channels = config.voice_chat_channels
            self.bit_depth = config.voice_chat_bit_depth
            self.buffer_size = config.voice_chat_buffer_size
            
            # Device settings
            self.input_device = config.voice_chat_input_device
            self.output_device = config.voice_chat_output_device
            self.input_volume = config.voice_chat_input_volume / 100.0
            self.output_volume = config.voice_chat_output_volume / 100.0
            
            # Audio processing settings (disabled for ultra-low latency)
            self.noise_suppression = config.voice_chat_noise_suppression
            self.echo_cancellation = config.voice_chat_echo_cancellation
            self.automatic_gain = config.voice_chat_automatic_gain
            
            # Ultra-low latency settings
            self.ultra_low_latency = config.voice_chat_ultra_low_latency
            self.direct_monitoring = config.voice_chat_direct_monitoring
            self.priority_threading = config.voice_chat_priority_threading
            
            # Update format type based on bit depth
            if self.bit_depth == 16:
                self.format_type = pyaudio.paInt16
            elif self.bit_depth == 24:
                self.format_type = pyaudio.paInt24
            else:
                self.format_type = pyaudio.paInt32
                
            logger.info(f"🎤 Ultra-low latency voice settings: {self.sample_rate}Hz, {self.channels}ch, {self.bit_depth}bit, {self.buffer_size} buffer")
            logger.info(f"🎤 Audio devices - Input: {self.input_device}, Output: {self.output_device}")
            logger.info(f"🎤 Volume settings - Input: {self.input_volume:.2f}, Output: {self.output_volume:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to load voice settings from config: {e}")
            # Use ultra-low latency defaults if config loading fails
            self.sample_rate = 48000  # Professional standard
            self.channels = 1  # Mono - most microphones are mono
            self.bit_depth = 16  # Reduced for lower latency
            self.buffer_size = 128  # Ultra-low latency
            self.format_type = pyaudio.paInt16
            
            # Device settings
            self.input_device = None
            self.output_device = None
            self.input_volume = 0.8
            self.output_volume = 0.8
            
            # Audio processing settings
            self.noise_suppression = False
            self.echo_cancellation = False
            self.automatic_gain = False
            self.ultra_low_latency = True
            self.direct_monitoring = True
            self.priority_threading = True
    
    def setup_audio(self):
        """Initialize PyAudio with debugging."""
        try:
            self.audio = pyaudio.PyAudio()
            logger.info("🎤 PyAudio initialized successfully")
            
            # Log available devices for debugging
            device_count = self.audio.get_device_count()
            logger.info(f"🎤 Found {device_count} audio devices")
            
            for i in range(device_count):
                try:
                    device_info = self.audio.get_device_info_by_index(i)
                    logger.info(f"🎤 Device {i}: {device_info['name']} (Input: {device_info['maxInputChannels']}, Output: {device_info['maxOutputChannels']})")
                except Exception as e:
                    logger.warning(f"🎤 Could not get info for device {i}: {e}")
                    
        except Exception as e:
            logger.error(f"🎤 Failed to initialize PyAudio: {e}")
            self.voice_error.emit(f"Audio system not available: {str(e)}")
    
    def _play_incoming_audio(self, audio_data: bytes):
        """Play incoming audio data - this is the missing piece!"""
        try:
            self.debug_stats['audio_received'] += 1
            
            if not audio_data:
                logger.warning("🎤 Received empty audio data")
                return
                
            if not self.output_stream or not self.is_playing:
                logger.warning("🎤 Output stream not ready, cannot play audio")
                return
                
            # Process incoming audio
            processed_audio = self._process_incoming_audio(audio_data)
            
            # Play the audio
            try:
                self.output_stream.write(processed_audio)
                self.debug_stats['audio_played'] += 1
                logger.debug(f"🎤 Played incoming audio: {len(processed_audio)} bytes")
            except Exception as e:
                logger.error(f"🎤 Failed to play audio: {e}")
                self.debug_stats['errors'] += 1
                
        except Exception as e:
            logger.error(f"🎤 Error in _play_incoming_audio: {e}")
            self.debug_stats['errors'] += 1
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update voice chat settings with debugging."""
        try:
            logger.info(f"🎤 Updating voice settings: {settings}")
            
            # Track if we need to restart audio streams
            restart_audio = False
            
            # Update audio settings
            if 'sample_rate' in settings:
                self.sample_rate = settings['sample_rate']
                restart_audio = True
            if 'channels' in settings:
                self.channels = settings['channels']
                restart_audio = True
            if 'bit_depth' in settings:
                self.bit_depth = settings['bit_depth']
                # Update format type
                if self.bit_depth == 16:
                    self.format_type = pyaudio.paInt16
                elif self.bit_depth == 24:
                    self.format_type = pyaudio.paInt24
                else:
                    self.format_type = pyaudio.paInt32
                restart_audio = True
            if 'buffer_size' in settings:
                self.buffer_size = settings['buffer_size']
                restart_audio = True
            
            # Update device settings
            if 'input_device' in settings:
                self.input_device = settings['input_device']
                restart_audio = True
            if 'output_device' in settings:
                self.output_device = settings['output_device']
                restart_audio = True
            if 'input_volume' in settings:
                self.input_volume = settings['input_volume'] / 100.0
            if 'output_volume' in settings:
                self.output_volume = settings['output_volume'] / 100.0
            
            # Update processing settings
            if 'noise_suppression' in settings:
                self.noise_suppression = settings['noise_suppression']
            if 'echo_cancellation' in settings:
                self.echo_cancellation = settings['echo_cancellation']
            if 'automatic_gain' in settings:
                self.automatic_gain = settings['automatic_gain']
            if 'ultra_low_latency' in settings:
                self.ultra_low_latency = settings['ultra_low_latency']
            if 'direct_monitoring' in settings:
                self.direct_monitoring = settings['direct_monitoring']
            
            # Restart audio streams if device settings changed
            if restart_audio and (self.is_recording or self.is_playing):
                logger.info("🎤 Restarting audio streams due to device settings change")
                self._restart_audio_streams()
            
            logger.info(f"🎤 Settings updated successfully")
            
        except Exception as e:
            logger.error(f"🎤 Failed to update settings: {e}")
    
    def _restart_audio_streams(self):
        """Restart audio streams with new device settings."""
        try:
            logger.info("🎤 Restarting audio streams...")
            
            # Stop current streams
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None
                self.is_recording = False
            
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None
                self.is_playing = False
            
            # Restart streams if they were active
            if self.is_recording:
                self._start_high_quality_recording()
            
            if self.is_playing:
                self._start_high_quality_playback()
            
            logger.info("🎤 Audio streams restarted successfully")
            
        except Exception as e:
            logger.error(f"🎤 Failed to restart audio streams: {e}")
    
    def start_voice_chat(self, server_url: str, channel_id: str):
        """Start high-quality voice chat with debugging."""
        try:
            logger.info(f"🎤 Starting voice chat: {server_url}/voice/{channel_id}")
            
            # Ensure we're using current settings
            self._ensure_current_settings()
            
            # Reset debug stats
            self.debug_stats = {
                'audio_sent': 0,
                'audio_received': 0,
                'audio_played': 0,
                'websocket_messages': 0,
                'errors': 0
            }
            
            # Start voice client in separate thread
            self.voice_thread = threading.Thread(
                target=self._run_voice_client,
                args=(server_url, channel_id),
                daemon=True
            )
            self.voice_thread.start()
            
            logger.info("🎤 Voice chat thread started")
            
        except Exception as e:
            logger.error(f"🎤 Failed to start voice chat: {e}")
            self.voice_error.emit(f"Failed to start voice chat: {str(e)}")
    
    def _ensure_current_settings(self):
        """Ensure audio streams are using current settings."""
        try:
            # Reload settings from config to ensure we have the latest
            self.load_settings_from_config()
            logger.info("🎤 Reloaded settings from config")
        except Exception as e:
            logger.error(f"🎤 Failed to reload settings: {e}")
    
    def _run_voice_client(self, server_url: str, channel_id: str):
        """Run voice client with debugging."""
        try:
            logger.info(f"🎤 Running voice client for channel: {channel_id}")
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self._voice_client_loop(server_url, channel_id))
            except Exception as e:
                logger.error(f"🎤 Voice client loop error: {e}")
                self.voice_error.emit(f"Voice chat error: {str(e)}")
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"🎤 Voice client thread error: {e}")
            self.voice_error.emit(f"Voice chat thread error: {str(e)}")
    
    async def _voice_client_loop(self, server_url: str, channel_id: str):
        """High-quality voice client WebSocket loop with debugging."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"🎤 Connecting to voice server: {server_url}/voice/{channel_id}")
                
                # Create WebSocket connection and store it properly
                websocket = await websockets.connect(f"{server_url}/voice/{channel_id}",
                                                   ping_interval=20,
                                                   ping_timeout=10,
                                                   close_timeout=5)
                self.websocket = websocket
                self._voice_loop = asyncio.get_event_loop()
                logger.info("🎤 WebSocket connected successfully")
                
                # Emit connected signal
                self.connected.emit()
                
                # Start high-quality audio recording
                self._start_high_quality_recording()
                
                # Start high-quality audio playback
                self._start_high_quality_playback()
                
                # Handle incoming voice data
                async for message in websocket:
                    self.debug_stats['websocket_messages'] += 1
                    
                    try:
                        data = json.loads(message)
                        logger.debug(f"🎤 Received WebSocket message: {data.get('type', 'unknown')}")
                        
                        if data['type'] == 'voice_data':
                            # Process incoming audio with high quality
                            audio_data = bytes(data['audio'])
                            logger.debug(f"🎤 Received voice data: {len(audio_data)} bytes")
                            processed_audio = self._process_incoming_audio(audio_data)
                            self.voice_data_received.emit(processed_audio)
                        elif data['type'] == 'user_joined':
                            logger.info(f"🎤 User joined: {data.get('user_id')}")
                            self.user_joined_voice.emit(data['user_id'])
                        elif data['type'] == 'user_left':
                            logger.info(f"🎤 User left: {data.get('user_id')}")
                            self.user_left_voice.emit(data['user_id'])
                        elif data['type'] == 'welcome':
                            logger.info(f"🎤 Welcome message: {data}")
                        else:
                            logger.debug(f"🎤 Unknown message type: {data.get('type')}")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"🎤 Failed to parse WebSocket message: {e}")
                        self.debug_stats['errors'] += 1
                    except Exception as e:
                        logger.error(f"🎤 Error processing WebSocket message: {e}")
                        self.debug_stats['errors'] += 1
                        
            except websockets.exceptions.ConnectionClosedError as e:
                if "refused" in str(e).lower():
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"🎤 Retrying voice connection ({retry_count}/{max_retries})...")
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    else:
                        self.voice_error.emit("WebSocket error: [WinError 1225] The remote computer refused the network connection.\n\nThis usually means the voice server is not running or is not accessible on port 8080.")
                        self.disconnected.emit()
                        break
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"🎤 Retrying voice connection ({retry_count}/{max_retries})...")
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    else:
                        self.voice_error.emit(f"Voice chat connection lost after {max_retries} retries: {str(e)}\n\nThis may be due to network issues or server restart.")
                        self.disconnected.emit()
                        break
            except websockets.exceptions.InvalidURI:
                self.voice_error.emit("WebSocket error: Invalid server URL. Please check the voice server configuration.")
                self.disconnected.emit()
                break
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"🎤 WebSocket error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"🎤 Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    self.voice_error.emit(f"Voice chat connection error after {max_retries} retries: {str(e)}")
                    self.disconnected.emit()
                    break
            except Exception as e:
                logger.error(f"🎤 Unexpected voice chat error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"🎤 Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    self.voice_error.emit(f"Voice chat error after {max_retries} retries: {str(e)}")
                    self.disconnected.emit()
                    break
    
    def _start_high_quality_recording(self):
        """Start high-quality audio recording with device selection and debugging."""
        if not self.audio:
            logger.error("🎤 Audio recording not available - PyAudio not initialized")
            self.voice_error.emit("Audio recording not available")
            return
            
        try:
            # Use selected input device or default
            input_device_index = self.input_device if self.input_device is not None else None
            logger.info(f"🎤 Starting recording with device: {input_device_index}")
            
            # Auto-detect channel count for the selected device
            actual_channels = self._get_device_channel_count(input_device_index)
            if actual_channels != self.channels:
                logger.info(f"🎤 Adjusting channels from {self.channels} to {actual_channels} for device compatibility")
                self.channels = actual_channels
            
            self.input_stream = self.audio.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.buffer_size
            )
            self.is_recording = True
            logger.info("🎤 Audio recording started successfully")
            
            # Start ultra-low latency recording thread with priority
            if self.priority_threading:
                # Use high-priority thread for audio processing
                import threading
                audio_thread = threading.Thread(target=self._record_high_quality_audio, daemon=True)
                audio_thread.start()
                
                # Set thread priority if possible (Windows)
                try:
                    import win32api
                    import win32process
                    import win32con
                    thread_id = audio_thread.ident
                    if thread_id:
                        win32api.SetThreadPriority(win32api.OpenThread(win32con.THREAD_ALL_ACCESS, False, thread_id), 
                                                  win32process.THREAD_PRIORITY_TIME_CRITICAL)
                        logger.info("🎤 Audio thread set to TIME_CRITICAL priority")
                except ImportError:
                    logger.info("🎤 win32api not available, using default thread priority")
                except Exception as e:
                    logger.warning(f"🎤 Could not set thread priority: {e}")
            else:
                # Use regular thread
                threading.Thread(target=self._record_high_quality_audio, daemon=True).start()
            
        except Exception as e:
            logger.error(f"🎤 Failed to start recording: {e}")
            self.voice_error.emit(f"Failed to start recording: {str(e)}")
    
    def _get_device_channel_count(self, device_index: Optional[int]) -> int:
        """Get the actual channel count for a device, with fallback to mono."""
        try:
            if device_index is not None:
                device_info = self.audio.get_device_info_by_index(device_index)
                max_channels = device_info.get('maxInputChannels', 1)
                logger.info(f"🎤 Device {device_index} supports {max_channels} input channels")
                return max_channels
            else:
                # Default device - try to find a good default
                device_count = self.audio.get_device_count()
                for i in range(device_count):
                    try:
                        device_info = self.audio.get_device_info_by_index(i)
                        if device_info.get('maxInputChannels', 0) > 0:
                            max_channels = device_info.get('maxInputChannels', 1)
                            logger.info(f"🎤 Default device {i} supports {max_channels} input channels")
                            return max_channels
                    except Exception as e:
                        logger.warning(f"🎤 Could not get info for device {i}: {e}")
                        continue
                
                # Fallback to mono
                logger.info("🎤 No suitable device found, using mono (1 channel)")
                return 1
        except Exception as e:
            logger.error(f"🎤 Error detecting device channels: {e}")
            return 1  # Fallback to mono
    
    def _record_high_quality_audio(self):
        """Record ultra-low latency audio with direct monitoring and debugging."""
        logger.info("🎤 Audio recording thread started")
        
        while self.is_recording:
            try:
                data = self.input_stream.read(self.buffer_size, exception_on_overflow=False)
                
                # Direct monitoring - hear yourself instantly
                if self.direct_monitoring and self.output_stream:
                    try:
                        # Send audio directly to output for instant feedback
                        self.output_stream.write(data)
                        logger.debug("🎤 Direct monitoring: sent audio to output")
                    except Exception as e:
                        logger.warning(f"🎤 Direct monitoring error: {e}")
                        # Try to restart output stream if it failed
                        try:
                            if self.output_stream:
                                self.output_stream.stop_stream()
                                self.output_stream.close()
                            self._start_high_quality_playback()
                        except Exception as restart_error:
                            logger.error(f"🎤 Failed to restart output stream: {restart_error}")
                
                # Minimal processing for ultra-low latency
                if self.ultra_low_latency:
                    # Skip heavy processing, just send raw audio
                    processed_data = data
                    logger.debug("🎤 Ultra-low latency mode: sending raw audio")
                else:
                    # Process audio with enhancements (if not in ultra-low latency mode)
                    processed_data = self._process_outgoing_audio(data)
                    logger.debug("🎤 Standard mode: processed audio")
                
                # Calculate audio level for UI
                level = self._calculate_audio_level(data)
                self.audio_level_changed.emit(level)
                
                # Send to WebSocket with minimal delay
                if self.websocket and hasattr(self, '_voice_loop') and self._voice_loop:
                    try:
                        # Check if websocket is still open before sending
                        if not self._voice_loop.is_closed() and not self.websocket.closed:
                            logger.debug(f"🎤 Sending audio data: {len(processed_data)} bytes, level: {level:.3f}")
                            self._voice_loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(
                                    self.websocket.send(json.dumps({
                                        'type': 'voice_data',
                                        'audio': list(processed_data)
                                    }))
                                )
                            )
                            self.debug_stats['audio_sent'] += 1
                            logger.debug(f"🎤 Sent audio data: {len(processed_data)} bytes")
                        else:
                            logger.warning("🎤 WebSocket connection closed, stopping audio transmission")
                            break
                    except websockets.exceptions.ConnectionClosedError:
                        logger.warning("🎤 WebSocket connection closed during audio transmission")
                        break
                    except Exception as e:
                        logger.error(f"🎤 Error sending audio data: {e}")
                        self.debug_stats['errors'] += 1
                        break
                else:
                    logger.warning("🎤 WebSocket not available for sending audio data")
                    break
                        
            except Exception as e:
                logger.error(f"🎤 Recording error: {e}")
                self.debug_stats['errors'] += 1
                break
        
        logger.info("🎤 Audio recording thread stopped")
    
    def _start_high_quality_playback(self):
        """Start high-quality audio playback with device selection and debugging."""
        if not self.audio:
            logger.error("🎤 Audio playback not available - PyAudio not initialized")
            self.voice_error.emit("Audio playback not available")
            return
            
        try:
            # Use selected output device or default
            output_device_index = self.output_device if self.output_device is not None else None
            logger.info(f"🎤 Starting playback with device: {output_device_index}")
            
            # Check device capabilities
            if output_device_index is not None:
                device_info = self.audio.get_device_info_by_index(output_device_index)
                max_channels = device_info['maxOutputChannels']
                if self.channels > max_channels:
                    logger.warning(f"🎤 Output device only supports {max_channels} channels, using {max_channels}")
                    self.channels = max_channels
            
            self.output_stream = self.audio.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=output_device_index,
                frames_per_buffer=self.buffer_size
            )
            self.is_playing = True
            logger.info("🎤 Audio playback started successfully")
            
        except Exception as e:
            logger.error(f"🎤 Failed to start playback: {e}")
            self.voice_error.emit(f"Failed to start playback: {str(e)}")
    
    def _process_outgoing_audio(self, audio_data: bytes) -> bytes:
        """Process outgoing audio with high-quality enhancements and debugging."""
        try:
            # Convert to numpy array for processing
            if self.bit_depth == 16:
                dtype = np.int16
                max_val = 32767
            elif self.bit_depth == 24:
                dtype = np.int32
                max_val = 8388607
            else:
                dtype = np.int32
                max_val = 2147483647
                
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            
            # Apply input volume
            audio_array = audio_array * self.input_volume
            
            # Noise suppression
            if self.noise_suppression:
                audio_array = self._apply_noise_suppression(audio_array)
                logger.debug("🎤 Applied noise suppression")
            
            # Automatic gain control
            if self.automatic_gain:
                audio_array = self._apply_automatic_gain(audio_array, max_val)
                logger.debug("🎤 Applied automatic gain")
            
            # Echo cancellation
            if self.echo_cancellation:
                audio_array = self._apply_echo_cancellation(audio_array)
                logger.debug("🎤 Applied echo cancellation")
            
            # Convert back to bytes
            processed_data = audio_array.astype(dtype).tobytes()
            logger.debug(f"🎤 Processed outgoing audio: {len(audio_data)} -> {len(processed_data)} bytes")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"🎤 Outgoing audio processing error: {e}")
            return audio_data
    
    def _process_incoming_audio(self, audio_data: bytes) -> bytes:
        """Process incoming audio with high-quality enhancements and debugging."""
        try:
            # Convert to numpy array for processing
            if self.bit_depth == 16:
                dtype = np.int16
                max_val = 32767
            elif self.bit_depth == 24:
                dtype = np.int32
                max_val = 8388607
            else:
                dtype = np.int32
                max_val = 2147483647
                
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            
            # Echo cancellation
            if self.echo_cancellation and self.echo_buffer:
                audio_array = self._apply_echo_cancellation(audio_array)
                logger.debug("🎤 Applied echo cancellation to incoming audio")
            
            # Apply output volume
            audio_array = audio_array * self.output_volume
            
            # Convert back to bytes
            processed_data = audio_array.astype(dtype).tobytes()
            logger.debug(f"🎤 Processed incoming audio: {len(audio_data)} -> {len(processed_data)} bytes")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"🎤 Incoming audio processing error: {e}")
            return audio_data
    
    def _apply_noise_suppression(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply noise suppression using spectral subtraction."""
        try:
            # Simple noise gate implementation
            threshold = np.std(audio_array) * 0.1
            mask = np.abs(audio_array) > threshold
            audio_array = audio_array * mask
            
            return audio_array
        except Exception as e:
            logger.error(f"🎤 Noise suppression error: {e}")
            return audio_array
    
    def _apply_automatic_gain(self, audio_array: np.ndarray, max_val: int) -> np.ndarray:
        """Apply automatic gain control."""
        try:
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_array**2))
            if rms > 0:
                # Target RMS level (adjust for desired loudness)
                target_rms = max_val * 0.3
                gain = target_rms / rms
                # Limit gain to prevent distortion
                gain = min(gain, 3.0)
                audio_array = audio_array * gain
                
            return audio_array
        except Exception as e:
            logger.error(f"🎤 Automatic gain error: {e}")
            return audio_array
    
    def _apply_echo_cancellation(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply echo cancellation using stored echo buffer."""
        try:
            if not self.echo_buffer:
                return audio_array
                
            # Simple echo cancellation - subtract recent echo
            echo = np.mean(self.echo_buffer, axis=0)
            # Scale echo cancellation
            cancellation_strength = 0.3
            audio_array = audio_array - (echo * cancellation_strength)
            
            return audio_array
        except Exception as e:
            logger.error(f"🎤 Echo cancellation error: {e}")
            return audio_array
    
    def _calculate_audio_level(self, audio_data: bytes) -> float:
        """Calculate audio level for UI meters with improved sensitivity."""
        try:
            if self.bit_depth == 16:
                dtype = np.int16
                max_val = 32767
            elif self.bit_depth == 24:
                dtype = np.int32
                max_val = 8388607
            else:
                dtype = np.int32
                max_val = 2147483647
                
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            
            # Calculate RMS (Root Mean Square) for better level detection
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # Normalize to 0-1 range with improved sensitivity
            level = min(rms / max_val, 1.0)
            
            # Apply logarithmic scaling for better visual feedback
            if level > 0:
                level = np.log10(1 + level * 9) / np.log10(10)
            
            logger.debug(f"🎤 Audio level calculated: {level:.3f} (RMS: {rms:.1f})")
            return level
        except Exception as e:
            logger.error(f"🎤 Audio level calculation error: {e}")
            return 0.0
    
    def stop_voice_chat(self):
        """Stop voice chat with debugging."""
        try:
            logger.info("🎤 Stopping voice chat")
            
            # Stop recording
            if self.is_recording:
                self.is_recording = False
                if self.input_stream:
                    self.input_stream.stop_stream()
                    self.input_stream.close()
                    logger.info("🎤 Recording stopped")
            
            # Stop playback
            if self.is_playing:
                self.is_playing = False
                if self.output_stream:
                    self.output_stream.stop_stream()
                    self.output_stream.close()
                    logger.info("🎤 Playback stopped")
            
            # Close WebSocket with proper error handling
            if self.websocket:
                try:
                    # Check if we're in an event loop and it's still running
                    try:
                        loop = asyncio.get_running_loop()
                        if not loop.is_closed():
                            # Use call_soon_threadsafe to schedule the close
                            loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(self.websocket.close())
                            )
                            logger.info("🎤 WebSocket close scheduled")
                        else:
                            logger.warning("🎤 Event loop is closed, cannot schedule WebSocket close")
                    except RuntimeError:
                        # No running event loop
                        logger.warning("🎤 No running event loop, cannot close WebSocket properly")
                    except Exception as e:
                        logger.warning(f"🎤 Error scheduling WebSocket close: {e}")
                        
                except Exception as e:
                    logger.warning(f"🎤 Error closing WebSocket: {e}")
            
            # Emit disconnected signal
            self.disconnected.emit()
            
            # Log debug stats
            logger.info(f"🎤 Voice chat debug stats: {self.debug_stats}")
            
        except Exception as e:
            logger.error(f"🎤 Error stopping voice chat: {e}")
    
    def force_cleanup(self):
        """Force cleanup during application shutdown - bypasses normal WebSocket cleanup."""
        try:
            logger.info("🎤 Force cleaning up voice manager")
            
            # Stop recording and playback immediately
            self.is_recording = False
            self.is_playing = False
            
            if self.input_stream:
                try:
                    self.input_stream.stop_stream()
                    self.input_stream.close()
                except Exception as e:
                    logger.warning(f"🎤 Error closing input stream: {e}")
            
            if self.output_stream:
                try:
                    self.output_stream.stop_stream()
                    self.output_stream.close()
                except Exception as e:
                    logger.warning(f"🎤 Error closing output stream: {e}")
            
            # Don't try to close WebSocket during shutdown - just clear the reference
            if self.websocket:
                self.websocket = None
                logger.info("🎤 WebSocket reference cleared")
            
            # Emit disconnected signal
            try:
                self.disconnected.emit()
            except Exception as e:
                logger.warning(f"🎤 Error emitting disconnected signal: {e}")
            
            logger.info("🎤 Force cleanup completed")
            
        except Exception as e:
            logger.error(f"🎤 Error during force cleanup: {e}")
    
    def get_available_devices(self) -> Dict[str, list]:
        """Get available audio devices with debugging."""
        devices = {'input': [], 'output': []}
        
        if not self.audio:
            logger.warning("🎤 PyAudio not initialized, cannot get devices")
            return devices
        
        try:
            device_count = self.audio.get_device_count()
            logger.info(f"🎤 Enumerating {device_count} audio devices")
            
            for i in range(device_count):
                try:
                    device_info = self.audio.get_device_info_by_index(i)
                    device_name = device_info['name']
                    
                    # Check if device supports input
                    if device_info['maxInputChannels'] > 0:
                        devices['input'].append({
                            'index': i,
                            'name': device_name,
                            'channels': device_info['maxInputChannels'],
                            'sample_rate': int(device_info['defaultSampleRate'])
                        })
                        logger.debug(f"🎤 Input device {i}: {device_name}")
                    
                    # Check if device supports output
                    if device_info['maxOutputChannels'] > 0:
                        devices['output'].append({
                            'index': i,
                            'name': device_name,
                            'channels': device_info['maxOutputChannels'],
                            'sample_rate': int(device_info['defaultSampleRate'])
                        })
                        logger.debug(f"🎤 Output device {i}: {device_name}")
                        
                except Exception as e:
                    logger.warning(f"🎤 Could not get info for device {i}: {e}")
            
            logger.info(f"🎤 Found {len(devices['input'])} input devices and {len(devices['output'])} output devices")
            return devices
            
        except Exception as e:
            logger.error(f"🎤 Error getting audio devices: {e}")
            return devices
    
    def get_debug_stats(self) -> Dict[str, Any]:
        """Get current debug statistics."""
        return self.debug_stats.copy()
    
    def __del__(self):
        """Cleanup with debugging."""
        try:
            if self.audio:
                self.audio.terminate()
                logger.info("🎤 PyAudio terminated")
        except Exception as e:
            logger.error(f"🎤 Error during cleanup: {e}") 