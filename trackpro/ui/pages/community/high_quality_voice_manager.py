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
    
    def __init__(self):
        super().__init__()
        self.audio = None
        self.is_recording = False
        self.is_playing = False
        self.websocket = None
        self.voice_thread = None
        
        # High-quality audio settings
        self.sample_rate = 48000  # Professional standard
        self.channels = 2  # Stereo
        self.bit_depth = 24  # High quality
        self.buffer_size = 512  # Low latency
        self.format_type = pyaudio.paInt24
        
        # Device settings
        self.input_device = None
        self.output_device = None
        self.input_volume = 0.8
        self.output_volume = 0.8
        
        # Audio processing settings
        self.noise_suppression = True
        self.echo_cancellation = True
        self.automatic_gain = True
        
        # Audio processing buffers
        self.input_buffer = queue.Queue(maxsize=100)
        self.output_buffer = queue.Queue(maxsize=100)
        self.echo_buffer = []  # For echo cancellation
        
        # Audio streams
        self.input_stream = None
        self.output_stream = None
        
        # Initialize PyAudio
        self.setup_audio()
        
    def setup_audio(self):
        """Initialize PyAudio with high-quality settings."""
        try:
            self.audio = pyaudio.PyAudio()
            logger.info("High-quality voice manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            self.voice_error.emit(f"Audio system not available: {str(e)}")
            
    def update_settings(self, settings: Dict[str, Any]):
        """Update voice chat settings."""
        self.sample_rate = settings.get('sample_rate', 48000)
        self.channels = settings.get('channels', 2)
        self.bit_depth = settings.get('bit_depth', 24)
        self.buffer_size = settings.get('buffer_size', 512)
        self.input_device = settings.get('input_device')
        self.output_device = settings.get('output_device')
        self.input_volume = settings.get('input_volume', 80) / 100.0
        self.output_volume = settings.get('output_volume', 80) / 100.0
        self.noise_suppression = settings.get('noise_suppression', True)
        self.echo_cancellation = settings.get('echo_cancellation', True)
        self.automatic_gain = settings.get('automatic_gain', True)
        
        # Update format type based on bit depth
        if self.bit_depth == 16:
            self.format_type = pyaudio.paInt16
        elif self.bit_depth == 24:
            self.format_type = pyaudio.paInt24
        else:
            self.format_type = pyaudio.paInt32
            
        logger.info(f"Voice settings updated: {self.sample_rate}Hz, {self.channels}ch, {self.bit_depth}bit")
        
    def start_voice_chat(self, server_url: str, channel_id: str):
        """Start high-quality voice chat connection."""
        if not self.audio:
            self.voice_error.emit("Audio system not available")
            return
            
        try:
            self.voice_thread = threading.Thread(
                target=self._run_voice_client,
                args=(server_url, channel_id)
            )
            self.voice_thread.daemon = True
            self.voice_thread.start()
        except Exception as e:
            self.voice_error.emit(f"Failed to start voice chat: {str(e)}")
    
    def _run_voice_client(self, server_url: str, channel_id: str):
        """Run voice client in separate thread."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._voice_client_loop(server_url, channel_id))
        except Exception as e:
            self.voice_error.emit(f"Voice client error: {str(e)}")
        finally:
            if 'loop' in locals():
                loop.close()
    
    async def _voice_client_loop(self, server_url: str, channel_id: str):
        """High-quality voice client WebSocket loop."""
        try:
            async with websockets.connect(f"{server_url}/voice/{channel_id}") as websocket:
                self.websocket = websocket
                
                # Start high-quality audio recording
                self._start_high_quality_recording()
                
                # Start high-quality audio playback
                self._start_high_quality_playback()
                
                # Handle incoming voice data
                async for message in websocket:
                    data = json.loads(message)
                    if data['type'] == 'voice_data':
                        # Process incoming audio with high quality
                        processed_audio = self._process_incoming_audio(bytes(data['audio']))
                        self.voice_data_received.emit(processed_audio)
                    elif data['type'] == 'user_joined':
                        self.user_joined_voice.emit(data['user_id'])
                    elif data['type'] == 'user_left':
                        self.user_left_voice.emit(data['user_id'])
                        
        except Exception as e:
            self.voice_error.emit(f"WebSocket error: {str(e)}")
    
    def _start_high_quality_recording(self):
        """Start high-quality audio recording with device selection."""
        if not self.audio:
            self.voice_error.emit("Audio recording not available")
            return
            
        try:
            # Use selected input device or default
            input_device_index = self.input_device if self.input_device is not None else None
            
            self.input_stream = self.audio.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.buffer_size
            )
            self.is_recording = True
            
            # Start high-quality recording thread
            threading.Thread(target=self._record_high_quality_audio, daemon=True).start()
            
        except Exception as e:
            self.voice_error.emit(f"Failed to start recording: {str(e)}")
    
    def _record_high_quality_audio(self):
        """Record high-quality audio with processing."""
        while self.is_recording:
            try:
                data = self.input_stream.read(self.buffer_size, exception_on_overflow=False)
                
                # Process audio with high-quality enhancements
                processed_data = self._process_outgoing_audio(data)
                
                # Calculate audio level for UI
                level = self._calculate_audio_level(data)
                self.audio_level_changed.emit(level)
                
                if self.websocket:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.websocket.send(json.dumps({
                            'type': 'voice_data',
                            'audio': list(processed_data)
                        })))
                        
            except Exception as e:
                logger.error(f"Recording error: {e}")
                break
    
    def _start_high_quality_playback(self):
        """Start high-quality audio playback with device selection."""
        if not self.audio:
            self.voice_error.emit("Audio playback not available")
            return
            
        try:
            # Use selected output device or default
            output_device_index = self.output_device if self.output_device is not None else None
            
            self.output_stream = self.audio.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=output_device_index,
                frames_per_buffer=self.buffer_size
            )
            self.is_playing = True
            
        except Exception as e:
            self.voice_error.emit(f"Failed to start playback: {str(e)}")
    
    def _process_outgoing_audio(self, audio_data: bytes) -> bytes:
        """Process outgoing audio with high-quality enhancements."""
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
            
            # Automatic gain control
            if self.automatic_gain:
                audio_array = self._apply_automatic_gain(audio_array, max_val)
            
            # Echo cancellation (store for incoming audio)
            if self.echo_cancellation:
                self.echo_buffer.append(audio_array.copy())
                if len(self.echo_buffer) > 10:  # Keep last 10 buffers
                    self.echo_buffer.pop(0)
            
            # Convert back to bytes
            return audio_array.astype(dtype).tobytes()
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            return audio_data
    
    def _process_incoming_audio(self, audio_data: bytes) -> bytes:
        """Process incoming audio with high-quality enhancements."""
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
            
            # Apply output volume
            audio_array = audio_array * self.output_volume
            
            # Write to output stream
            if self.output_stream and self.is_playing:
                self.output_stream.write(audio_array.astype(dtype).tobytes())
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Incoming audio processing error: {e}")
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
            logger.error(f"Noise suppression error: {e}")
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
            logger.error(f"Automatic gain error: {e}")
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
            logger.error(f"Echo cancellation error: {e}")
            return audio_array
    
    def _calculate_audio_level(self, audio_data: bytes) -> float:
        """Calculate audio level for UI meters."""
        try:
            if self.bit_depth == 16:
                dtype = np.int16
            elif self.bit_depth == 24:
                dtype = np.int32
            else:
                dtype = np.int32
                
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            rms = np.sqrt(np.mean(audio_array**2))
            
            # Normalize to 0-1 range
            max_val = 32767 if self.bit_depth == 16 else 8388607
            level = min(rms / max_val, 1.0)
            
            return level
        except Exception as e:
            logger.error(f"Audio level calculation error: {e}")
            return 0.0
    
    def stop_voice_chat(self):
        """Stop high-quality voice chat."""
        self.is_recording = False
        self.is_playing = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.websocket:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.websocket.close())
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
    
    def get_available_devices(self) -> Dict[str, list]:
        """Get available audio devices."""
        devices = {'input': [], 'output': []}
        
        if not self.audio:
            return devices
            
        try:
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                name = device_info['name']
                
                if device_info['maxInputChannels'] > 0:
                    devices['input'].append({
                        'index': i,
                        'name': name,
                        'channels': device_info['maxInputChannels']
                    })
                    
                if device_info['maxOutputChannels'] > 0:
                    devices['output'].append({
                        'index': i,
                        'name': name,
                        'channels': device_info['maxOutputChannels']
                    })
                    
        except Exception as e:
            logger.error(f"Error enumerating devices: {e}")
            
        return devices
    
    def __del__(self):
        """Cleanup audio resources."""
        if self.audio:
            self.audio.terminate() 