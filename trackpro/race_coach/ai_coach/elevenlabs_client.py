"""Client for interacting with the ElevenLabs API and playing audio."""

import os
import threading
import sounddevice as sd
import soundfile as sf
import io
import logging
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

logger = logging.getLogger(__name__)

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

def text_to_speech_stream(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM", model: str = "eleven_turbo_v2"):
    """
    Generates an audio stream from text using ElevenLabs API.

    Args:
        text (str): The text to convert to speech.
        voice_id (str): The ID of the voice to use. Defaults to a standard voice.
        model (str): The model to use for generation.

    Yields:
        bytes: Chunks of audio data.
    """
    api_key = get_api_key()
    if not api_key:
        return

    try:
        client = ElevenLabs(api_key=api_key)
        
        # Generate audio stream using the new API
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_22050_32",
            text=text,
            model_id=model,
        )
        
        for chunk in audio_generator:
            yield chunk
    except Exception as e:
        logger.error(f"ElevenLabs API Error: {e}")
        logger.error(f"An unexpected error occurred in text_to_speech_stream: {e}")

def _play_stream_worker(audio_stream):
    """
    Worker function to play an audio stream in the background.
    """
    try:
        # Buffer the stream into memory
        buffer = io.BytesIO()
        for chunk in audio_stream:
            buffer.write(chunk)
        buffer.seek(0)
        
        # Save as temporary file and play with pygame or use pydub
        import tempfile
        import pygame
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(buffer.getvalue())
            temp_file_path = temp_file.name
        
        # Play the audio file
        pygame.mixer.music.load(temp_file_path)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        # Stop the mixer and clean up
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        
        # Clean up - try with delay on Windows
        import os
        import time
        try:
            time.sleep(0.1)  # Small delay to let Windows release the file
            os.unlink(temp_file_path)
        except OSError:
            # If we can't delete immediately, that's okay for temp files
            pass
        
    except Exception as e:
        logger.error(f"Failed to play audio stream: {e}", exc_info=True)

def play_audio_stream(audio_stream):
    """
    Plays an audio stream in a separate thread to avoid blocking.

    Args:
        audio_stream: The audio stream to play.
    """
    if audio_stream:
        playback_thread = threading.Thread(target=_play_stream_worker, args=(audio_stream,))
        playback_thread.daemon = True
        playback_thread.start()

if __name__ == '__main__':
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing ElevenLabs client...")
    
    test_text = "Hello, this is a test of the real-time AI voice coach."
    
    # Check for API key first
    if not get_api_key():
        logger.error("Cannot run test: ELEVENLABS_API_KEY is not set.")
        logger.info("Please set the environment variable and try again.")
    else:
        logger.info(f"Generating speech for text: '{test_text}'")
        audio_stream = text_to_speech_stream(test_text)
        
        if audio_stream:
            logger.info("Audio stream generated. Playing...")
            play_audio_stream(audio_stream)
            # Keep the main thread alive while the audio plays
            import time
            time.sleep(5)
            logger.info("Test finished.")
        else:
            logger.error("Failed to generate audio stream.") 