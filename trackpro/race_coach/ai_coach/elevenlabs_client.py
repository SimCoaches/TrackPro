"""Client for interacting with the ElevenLabs API and playing audio."""

import os
import threading
import queue
import time
import io
import logging
import tempfile
import json
import struct
from typing import Optional, Generator
try:
    # Try new API structure first (v1.0+)
    from elevenlabs import ElevenLabsAPI as ElevenLabs
except ImportError:
    try:
        # Try direct import (v0.2.x)
        from elevenlabs import API as ElevenLabs
    except ImportError:
        # Fallback to old structure
        from elevenlabs.client import ElevenLabs

try:
    from elevenlabs import VoiceSettings
except ImportError:
    # Create a dummy VoiceSettings if not available
    class VoiceSettings:
        def __init__(self, **kwargs):
            pass

logger = logging.getLogger(__name__)

class AudioManager:
    """
    Singleton audio manager to handle all audio playback safely.
    Prevents resource conflicts and manages audio queue.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.current_thread = None
        self.pygame_initialized = False
        self.stop_current = threading.Event()
        
        # Volume control (0.0 to 2.0) 
        self.volume = 0.8  # Default to 80% volume
        self.volume_file = "ai_coach_volume.json"
        self._load_volume_settings()
        
        # Volume change callbacks for UI updates
        self.volume_callbacks = []
        
        # Track original system volume for restoration
        self._original_system_volume = None
        
        # Start the audio worker thread
        self.worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"🔊 [AUDIO MANAGER] Singleton audio manager initialized with volume: {self.volume:.2f}")
    
    def _load_volume_settings(self):
        """Load volume settings from file."""
        try:
            if os.path.exists(self.volume_file):
                with open(self.volume_file, 'r') as f:
                    data = json.load(f)
                    self.volume = max(0.0, min(2.0, data.get('volume', 0.8)))
                    logger.info(f"🔊 [VOLUME] Loaded volume setting: {self.volume:.2f}")
            else:
                logger.info(f"🔊 [VOLUME] No volume file found, using default: {self.volume:.2f}")
        except Exception as e:
            logger.warning(f"🔊 [VOLUME] Failed to load volume settings: {e}")
            self.volume = 0.8
    
    def _save_volume_settings(self):
        """Save volume settings to file."""
        try:
            data = {'volume': self.volume}
            with open(self.volume_file, 'w') as f:
                json.dump(data, f)
            logger.info(f"🔊 [VOLUME] Saved volume setting: {self.volume:.2f}")
        except Exception as e:
            logger.warning(f"🔊 [VOLUME] Failed to save volume settings: {e}")
    
    def set_volume(self, volume: float):
        """
        Set the playback volume.
        
        Args:
            volume: Volume level from 0.0 (mute) to 2.0 (200% - for loud racing environments)
        """
        # Clamp volume to valid range (allow up to 200% for racing)
        volume = max(0.0, min(2.0, volume))
        
        old_volume = self.volume
        self.volume = volume
        
        logger.info(f"🔊 [VOLUME] Volume changed from {old_volume:.2f} to {volume:.2f}")
        
        # Update pygame volume if initialized
        if self.pygame_initialized:
            try:
                import pygame
                pygame.mixer.music.set_volume(volume)
                logger.info(f"🔊 [VOLUME] Updated pygame mixer volume to {volume:.2f}")
            except Exception as e:
                logger.warning(f"🔊 [VOLUME] Failed to update pygame volume: {e}")
        
        # Save the setting
        self._save_volume_settings()
        
        # Notify UI callbacks
        for callback in self.volume_callbacks:
            try:
                callback(volume)
            except Exception as e:
                logger.warning(f"🔊 [VOLUME] Volume callback failed: {e}")
    
    def get_volume(self) -> float:
        """Get the current volume level."""
        return self.volume
    
    def add_volume_callback(self, callback):
        """Add a callback to be notified when volume changes."""
        self.volume_callbacks.append(callback)
        logger.info(f"🔊 [VOLUME] Added volume callback")
    
    def remove_volume_callback(self, callback):
        """Remove a volume change callback."""
        if callback in self.volume_callbacks:
            self.volume_callbacks.remove(callback)
            logger.info(f"🔊 [VOLUME] Removed volume callback")
    
    def _initialize_pygame(self):
        """Initialize pygame mixer once, safely."""
        if self.pygame_initialized:
            return True
            
        try:
            import pygame
            
            # Try to initialize with optimized settings for voice
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.init()
            
            # Set the volume immediately after initialization
            pygame.mixer.music.set_volume(self.volume)
            
            self.pygame_initialized = True
            logger.info(f"🔊 [AUDIO MANAGER] Pygame mixer initialized successfully with volume: {self.volume:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"🔊 [AUDIO MANAGER] Failed to initialize pygame: {e}")
            return False
    
    def _audio_worker(self):
        """Worker thread that processes audio queue sequentially."""
        logger.info("🔊 [AUDIO WORKER] Audio worker thread started")
        
        while True:
            try:
                # Get next audio item from queue (blocking)
                audio_data, callback = self.audio_queue.get(timeout=1.0)
                
                if audio_data is None:  # Shutdown signal
                    break
                
                self.is_playing = True
                self.stop_current.clear()
                
                logger.info(f"🔊 [AUDIO WORKER] Starting audio playback at volume {self.volume:.2f}")
                
                # Play the audio
                success = self._play_audio_data(audio_data)
                
                # Call callback if provided
                if callback:
                    callback(success)
                
                self.is_playing = False
                self.audio_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"🔊 [AUDIO WORKER] Error in audio worker: {e}")
                self.is_playing = False
    
    def _play_audio_data(self, audio_data: bytes) -> bool:
        """Play audio data with REAL amplification for volumes > 100%."""
        if not self._initialize_pygame():
            return self._fallback_audio_playback(audio_data)
        
        try:
            import pygame
            
            # Verify pygame mixer is still initialized
            if not pygame.mixer.get_init():
                logger.warning("🔊 [AUDIO PLAYBACK] Pygame mixer lost, reinitializing...")
                if not self._initialize_pygame():
                    return self._fallback_audio_playback(audio_data)
            
            # NEW APPROACH: Make 100% much louder, and amplify more aggressively
            # 100% = 1.5x the original volume (was too quiet)
            # 200% = 4.0x the original volume (much more aggressive)
            
            if self.volume >= 1.0:
                # Calculate aggressive amplification factor
                if self.volume == 1.0:
                    amplification_factor = 1.8  # Make 100% much louder
                else:
                    # Scale aggressively above 100%
                    amplification_factor = 1.8 + (self.volume - 1.0) * 2.5  # Much more aggressive scaling
                
                logger.info(f"🔊 [REAL BOOST] Applying AGGRESSIVE amplification: {self.volume:.1f}x → {amplification_factor:.1f}x actual")
                amplified_data = amplify_audio_data(audio_data, amplification_factor)
                playback_data = amplified_data
                pygame_volume = 1.0  # Always play amplified audio at 100% pygame volume
            else:
                # For volumes below 100%, scale normally but still boost baseline
                amplification_factor = self.volume * 1.8  # Boost baseline even for sub-100%
                logger.info(f"🔊 [BOOST] Boosting baseline volume: {self.volume:.1f}x → {amplification_factor:.1f}x actual")
                amplified_data = amplify_audio_data(audio_data, amplification_factor)
                playback_data = amplified_data
                pygame_volume = 1.0
            
            # Create temporary file for pygame
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(playback_data)
                temp_file_path = temp_file.name
            
            try:
                # Always use music player for consistency, but with amplified audio data
                pygame.mixer.music.load(temp_file_path)
                pygame.mixer.music.set_volume(pygame_volume)
                pygame.mixer.music.play()
                
                logger.info(f"🔊 [AUDIO PLAYBACK] Playing AMPLIFIED audio: {self.volume:.1f}x setting → {amplification_factor:.1f}x actual amplification")
                
                # Wait for playback to finish or stop signal
                while pygame.mixer.music.get_busy() and not self.stop_current.is_set():
                    time.sleep(0.1)
                
                # Stop if requested
                if self.stop_current.is_set():
                    pygame.mixer.music.stop()
                    logger.info("🔊 [AUDIO PLAYBACK] Audio stopped by request")
                else:
                    logger.info("🔊 [AUDIO PLAYBACK] Audio completed naturally")
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            logger.info(f"🔊 [AUDIO PLAYBACK] Audio playback completed: {self.volume:.1f}x → {amplification_factor:.1f}x actual")
            return True
            
        except Exception as e:
            logger.error(f"🔊 [AUDIO PLAYBACK] Audio playback failed: {e}")
            return self._fallback_audio_playback(audio_data)
    
    def _fallback_audio_playback(self, audio_data: bytes) -> bool:
        """Fallback audio playback using system player."""
        try:
            import subprocess
            
            logger.info("🔊 [AUDIO FALLBACK] Using system audio player")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Play with system default
            if os.name == 'nt':  # Windows
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(['start', '', temp_file_path], shell=True, creationflags=CREATE_NO_WINDOW)
            else:  # Unix-like systems
                subprocess.Popen(['xdg-open', temp_file_path])
            
            logger.info("🔊 [AUDIO FALLBACK] Audio sent to system player")
            
            # Clean up after delay
            def cleanup():
                time.sleep(3)
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            threading.Thread(target=cleanup, daemon=True).start()
            return True
            
        except Exception as e:
            logger.error(f"🔊 [AUDIO FALLBACK] System playback failed: {e}")
            return False
    
    def play_audio(self, audio_data: bytes, interrupt_current: bool = True, callback=None):
        """
        Queue audio for playback.
        
        Args:
            audio_data: Raw audio bytes to play
            interrupt_current: Whether to stop current audio and clear queue
            callback: Function to call when playback completes
        """
        if interrupt_current:
            # Stop current audio and clear queue
            self.stop_current.set()
            
            # Clear the queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.task_done()
                except queue.Empty:
                    break
            
            logger.info("🔊 [AUDIO QUEUE] Interrupted current audio and cleared queue")
        
        # Add new audio to queue
        self.audio_queue.put((audio_data, callback))
        logger.info(f"🔊 [AUDIO QUEUE] Added audio to queue (queue size: {self.audio_queue.qsize()})")
    
    def is_audio_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self.is_playing
    
    def shutdown(self):
        """Shutdown the audio manager."""
        logger.info("🔊 [AUDIO MANAGER] Shutting down audio manager")
        self.stop_current.set()
        self.audio_queue.put((None, None))  # Shutdown signal
        
        if self.pygame_initialized:
            try:
                import pygame
                pygame.mixer.quit()
                logger.info("🔊 [AUDIO MANAGER] Pygame mixer shut down")
            except:
                pass
    
    def _get_system_volume(self):
        """Get current system volume (Windows only)."""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Windows API to get master volume
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)
            
            # Get the default audio endpoint
            from ctypes import POINTER, HRESULT
            import comtypes
            
            # This is complex, so for now just return None
            # We'll use pygame volume scaling instead
            return None
        except:
            return None
    
    def _set_system_volume_boost(self, boost_factor: float):
        """Temporarily boost system volume for louder playback."""
        if boost_factor <= 1.0:
            return False
            
        try:
            # For now, we'll use pygame's channel volume which can be boosted
            # This is a simpler approach that should work
            return True
        except:
            return False

# Global audio manager instance
_audio_manager = None

def get_audio_manager() -> AudioManager:
    """Get the global audio manager instance."""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioManager()
    return _audio_manager

def get_api_key() -> str:
    """
    Retrieves the ElevenLabs API key from environment variables.

    Returns:
        The API key or None if not found.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY environment variable not set.")
    return api_key

def text_to_speech_stream(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM", model: str = "eleven_turbo_v2") -> Optional[bytes]:
    """
    Generates audio data from text using ElevenLabs API.

    Args:
        text (str): The text to convert to speech.
        voice_id (str): The ID of the voice to use. Defaults to a standard voice.
        model (str): The model to use for generation.

    Returns:
        bytes: Complete audio data or None if failed.
    """
    api_key = get_api_key()
    if not api_key:
        logger.error("🎙️ [TTS] No API key available")
        return None

    try:
        logger.info(f"🎙️ [TTS] Generating speech for: '{text[:50]}...'")
        
        client = ElevenLabs(api_key=api_key)
        
        # Generate audio stream using the new API
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_22050_32",
            text=text,
            model_id=model,
        )
        
        # Buffer the complete audio data
        buffer = io.BytesIO()
        for chunk in audio_generator:
            buffer.write(chunk)
        
        audio_data = buffer.getvalue()
        logger.info(f"🎙️ [TTS] Generated {len(audio_data)} bytes of audio data")
        return audio_data
        
    except Exception as e:
        logger.error(f"🎙️ [TTS] ElevenLabs API Error: {e}")
        return None

def play_audio_stream(audio_stream, interrupt_current: bool = True):
    """
    Plays an audio stream using the global audio manager.

    Args:
        audio_stream: The audio data to play (can be generator or bytes).
        interrupt_current: Whether to interrupt currently playing audio.
    """
    try:
        # Convert to bytes if it's a generator
        if hasattr(audio_stream, '__iter__') and not isinstance(audio_stream, bytes):
            buffer = io.BytesIO()
            for chunk in audio_stream:
                buffer.write(chunk)
            audio_data = buffer.getvalue()
        else:
            audio_data = audio_stream
        
        if not audio_data:
            logger.warning("🔊 [PLAY] No audio data to play")
            return
        
        # Use the global audio manager
        manager = get_audio_manager()
        manager.play_audio(audio_data, interrupt_current=interrupt_current)
        
    except Exception as e:
        logger.error(f"🔊 [PLAY] Failed to play audio stream: {e}")

def speak_text(text: str, interrupt_current: bool = True):
    """
    Convert text to speech and play it immediately.
    
    Args:
        text: Text to speak
        interrupt_current: Whether to interrupt currently playing audio
    """
    try:
        logger.info(f"🎤 [SPEAK] Speaking: '{text[:50]}...'")
        
        # Generate audio
        audio_data = text_to_speech_stream(text)
        if not audio_data:
            logger.error(f"🎤 [SPEAK] Failed to generate audio for: '{text}'")
            return False
        
        # Play audio
        manager = get_audio_manager()
        manager.play_audio(audio_data, interrupt_current=interrupt_current)
        
        logger.info(f"🎤 [SPEAK] Audio queued for playback")
        return True
        
    except Exception as e:
        logger.error(f"🎤 [SPEAK] Failed to speak text: {e}")
        return False

def is_speaking() -> bool:
    """Check if audio is currently playing."""
    manager = get_audio_manager()
    return manager.is_audio_playing()

def set_ai_coach_volume(volume: float):
    """
    Set the AI coach volume.
    
    Args:
        volume: Volume level from 0.0 (mute) to 2.0 (200% max volume for racing)
    """
    manager = get_audio_manager()
    manager.set_volume(volume)

def get_ai_coach_volume() -> float:
    """
    Get the current AI coach volume.
    
    Returns:
        Current volume level (0.0 to 1.0)
    """
    manager = get_audio_manager()
    return manager.get_volume()

def add_volume_change_callback(callback):
    """
    Add a callback function to be called when volume changes.
    
    Args:
        callback: Function that takes volume (float) as parameter
    """
    manager = get_audio_manager()
    manager.add_volume_callback(callback)

def remove_volume_change_callback(callback):
    """
    Remove a volume change callback.
    
    Args:
        callback: The callback function to remove
    """
    manager = get_audio_manager()
    manager.remove_volume_callback(callback)

def amplify_audio_data(audio_data: bytes, volume_multiplier: float) -> bytes:
    """
    REAL audio amplification by modifying the audio samples directly.
    This bypasses all pygame/system volume limitations.
    """
    if volume_multiplier <= 1.0:
        return audio_data  # No amplification needed
    
    try:
        import numpy as np
        import soundfile as sf
        import io
        import tempfile
        import os
        
        logger.info(f"🔊 [REAL AMPLIFY] Starting AGGRESSIVE audio amplification: {volume_multiplier:.1f}x")
        
        # Write audio data to temporary file for processing
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as input_temp:
            input_temp.write(audio_data)
            input_temp_path = input_temp.name
        
        try:
            # Convert MP3 to WAV for sample manipulation
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_temp:
                wav_temp_path = wav_temp.name
            
            # First try to read the MP3 directly
            try:
                # Read audio data and sample rate
                audio_samples, sample_rate = sf.read(input_temp_path)
                logger.info(f"🔊 [REAL AMPLIFY] Loaded audio: {len(audio_samples)} samples at {sample_rate}Hz")
                
                # Check original audio levels
                original_max = np.max(np.abs(audio_samples))
                logger.info(f"🔊 [REAL AMPLIFY] Original audio max amplitude: {original_max:.3f}")
                
                # Amplify the samples directly - MORE AGGRESSIVE
                amplified_samples = audio_samples * volume_multiplier
                
                # Check amplified levels before clipping
                amplified_max = np.max(np.abs(amplified_samples))
                logger.info(f"🔊 [REAL AMPLIFY] Amplified audio max amplitude: {amplified_max:.3f} ({volume_multiplier:.1f}x)")
                
                # Prevent severe clipping but allow some for loudness
                # Use softer clipping at 0.98 instead of 0.95 for more headroom
                amplified_samples = np.clip(amplified_samples, -0.98, 0.98)
                
                final_max = np.max(np.abs(amplified_samples))
                logger.info(f"🔊 [REAL AMPLIFY] Final audio max amplitude: {final_max:.3f}")
                
                # Write amplified audio to WAV
                sf.write(wav_temp_path, amplified_samples, sample_rate, format='WAV')
                
                # Read the amplified WAV back as bytes
                with open(wav_temp_path, 'rb') as wav_file:
                    amplified_audio_data = wav_file.read()
                
                # Verify we actually created different data
                if len(amplified_audio_data) > len(audio_data):
                    logger.info(f"🔊 [REAL AMPLIFY] ✅ Successfully amplified audio: {len(audio_data)} → {len(amplified_audio_data)} bytes")
                else:
                    logger.warning(f"🔊 [REAL AMPLIFY] ⚠️ Audio size unchanged - amplification may have failed")
                
                return amplified_audio_data
                
            except Exception as sf_error:
                logger.error(f"🔊 [REAL AMPLIFY] Soundfile processing failed: {sf_error}")
                
                # Fallback: Try with pydub if available
                try:
                    from pydub import AudioSegment
                    
                    # Load with pydub
                    audio_segment = AudioSegment.from_mp3(input_temp_path)
                    
                    # Convert volume multiplier to dB gain - MORE AGGRESSIVE
                    # 2.0x = +6dB, but let's be more aggressive
                    db_gain = 20 * np.log10(volume_multiplier)
                    db_gain = min(db_gain, 20)  # Allow up to +20dB for maximum loudness
                    
                    logger.info(f"🔊 [REAL AMPLIFY] Applying +{db_gain:.1f}dB gain using pydub")
                    
                    # Apply gain
                    amplified_segment = audio_segment + db_gain
                    
                    # Export as WAV
                    amplified_segment.export(wav_temp_path, format="wav")
                    
                    # Read back as bytes
                    with open(wav_temp_path, 'rb') as wav_file:
                        amplified_audio_data = wav_file.read()
                    
                    logger.info(f"🔊 [REAL AMPLIFY] ✅ Applied +{db_gain:.1f}dB gain using pydub")
                    return amplified_audio_data
                    
                except ImportError:
                    logger.error("🔊 [REAL AMPLIFY] ❌ Neither soundfile nor pydub could process the audio")
                    return audio_data
                except Exception as pydub_error:
                    logger.error(f"🔊 [REAL AMPLIFY] ❌ Pydub fallback failed: {pydub_error}")
                    return audio_data
                    
        finally:
            # Clean up temporary files
            try:
                os.unlink(input_temp_path)
                if os.path.exists(wav_temp_path):
                    os.unlink(wav_temp_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"🔊 [REAL AMPLIFY] ❌ Real amplification failed: {e}")
        return audio_data  # Return original on error

if __name__ == '__main__':
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing ElevenLabs client with new audio manager...")
    
    test_text = "Hello, this is a test of the improved AI voice coach audio system."
    
    # Check for API key first
    if not get_api_key():
        logger.error("Cannot run test: ELEVENLABS_API_KEY is not set.")
        logger.info("Please set the environment variable and try again.")
    else:
        logger.info("Testing new speak_text function...")
        success = speak_text(test_text)
        
        if success:
            logger.info("Audio generation successful. Waiting for playback...")
            # Keep the main thread alive while the audio plays
            time.sleep(10)
            logger.info("Test finished.")
        else:
            logger.error("Failed to generate or play audio.") 