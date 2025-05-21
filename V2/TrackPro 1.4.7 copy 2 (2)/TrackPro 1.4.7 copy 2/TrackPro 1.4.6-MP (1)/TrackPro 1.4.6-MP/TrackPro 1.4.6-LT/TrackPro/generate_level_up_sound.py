#!/usr/bin/env python
"""
Generate a level-up sound file for TrackPro.
This script creates a simple level-up sound and saves it to the sounds directory.
"""

import os
import numpy as np
from scipy.io import wavfile

def generate_level_up_sound():
    """Generate a triumphant level-up sound."""
    # Set sample rate
    sample_rate = 44100
    
    # Generate a rising chord sequence - triumphant sound
    # Base frequency for notes
    base_freq = 440.0  # A4 note
    
    # Create a rising frequency pattern for the level-up sound
    duration = 1.0  # 1 second total
    samples = int(duration * sample_rate)
    
    # Create buffer
    level_up_buffer = np.zeros((samples, 2), dtype=np.int16)
    
    # Generate main chord progression
    for i in range(samples):
        t = i / sample_rate  # Time in seconds
        
        # First part: rising notes
        if t < 0.3:
            # Start with a simple note
            freq1 = base_freq * 1.0
            freq2 = base_freq * 1.25  # Perfect fifth
            
            # Amplitude envelope (start soft, get louder)
            amp = np.minimum(1.0, t * 10) * 0.3
            
        # Second part: triumphant chord
        elif t < 0.7:
            # Major chord frequencies
            freq1 = base_freq * 1.0  # Root note
            freq2 = base_freq * 1.25  # Perfect fifth
            # Add higher octave for brightness
            freq3 = base_freq * 2.0  # Octave
            
            # Rising pitch for triumphant feel
            pitch_increase = (t - 0.3) * 0.5
            freq1 *= (1.0 + pitch_increase)
            freq2 *= (1.0 + pitch_increase)
            freq3 *= (1.0 + pitch_increase)
            
            # Full amplitude
            amp = 0.6
            
        # Final part: fade out
        else:
            # Major chord frequencies with higher notes
            freq1 = base_freq * 1.5  # Higher root
            freq2 = base_freq * 2.0  # Octave
            freq3 = base_freq * 2.5  # Higher fifth
            
            # Fade out
            amp = 0.6 * (1.0 - (t - 0.7) / 0.3)
        
        # Generate the sound waves
        value1 = np.sin(2 * np.pi * freq1 * t) * amp * 32767
        value2 = np.sin(2 * np.pi * freq2 * t) * amp * 32767
        
        # Add a third frequency in the second part
        if t >= 0.3:
            value3 = np.sin(2 * np.pi * freq3 * t) * amp * 32767
            # Mix all frequencies
            value = (value1 + value2 + value3) / 3
        else:
            # Mix just the two frequencies in the first part
            value = (value1 + value2) / 2
            
        # Apply slight vibrato effect in the middle section
        if 0.3 <= t < 0.7:
            vibrato = np.sin(2 * np.pi * 8 * t) * 0.02  # 8 Hz vibrato, 2% depth
            value *= (1.0 + vibrato)
        
        # Set both channels (stereo)
        level_up_buffer[i][0] = int(value)
        level_up_buffer[i][1] = int(value)
    
    # Create the sounds directory if it doesn't exist
    sounds_dir = os.path.join("trackpro", "resources", "sounds")
    os.makedirs(sounds_dir, exist_ok=True)
    
    # Save the sound to a WAV file using scipy.io.wavfile
    sound_path = os.path.join(sounds_dir, "level_up.wav")
    wavfile.write(sound_path, sample_rate, level_up_buffer)
    
    print(f"Generated level-up sound and saved to {sound_path}")

if __name__ == "__main__":
    try:
        generate_level_up_sound()
        print("Level-up sound generation completed successfully.")
    except Exception as e:
        print(f"Error generating level-up sound: {e}") 