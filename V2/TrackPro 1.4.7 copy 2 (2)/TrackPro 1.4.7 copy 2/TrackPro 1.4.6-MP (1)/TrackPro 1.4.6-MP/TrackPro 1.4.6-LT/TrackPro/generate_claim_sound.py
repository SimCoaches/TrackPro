"""generate_claim_sound.py
Creates a short "champion" fanfare that feels more orchestral (drum + brass + bell).
It writes the WAV to trackpro/resources/sounds/quest_claim.wav.
"""

import os
import numpy as np
import soundfile as sf

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

SAMPLE_RATE = 44100
DURATION = 1.1  # total duration in seconds

# Utility to ensure parent folders exist (re-added after accidental removal)
def ensure_directories(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

# ---------------------------------------------------------------------------
# Basic wave helpers
# ---------------------------------------------------------------------------

def sine_wave(freq: float, duration: float, volume: float = 1.0) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return volume * np.sin(2 * np.pi * freq * t)


def brass_wave(freq: float, duration: float, volume: float = 1.0) -> np.ndarray:
    """Saw-like brass tone with 4 harmonics and a quick decay envelope."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    harmonics = sum((1 / n) * np.sin(2 * np.pi * freq * n * t) for n in range(1, 5))
    # Envelope: fast attack, medium decay
    env = np.concatenate([
        np.linspace(0, 1, int(0.02 * SAMPLE_RATE)),
        np.exp(-3 * (t[int(0.02 * SAMPLE_RATE):] - 0.02))
    ])
    return volume * harmonics[: len(t)] * env


def drum_hit(duration: float = 0.35, base_freq: float = 70.0, volume: float = 1.0) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    sine_part = np.sin(2 * np.pi * base_freq * t)
    noise_part = np.random.uniform(-1, 1, size=t.shape) * 0.3
    env = np.exp(-4 * t)
    return volume * (sine_part + noise_part) * env


def cymbal_swell(duration: float = 0.6, volume: float = 0.6) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    noise = np.random.uniform(-1, 1, size=t.shape)
    lp = np.convolve(noise, np.ones(30)/30, mode="same")
    hp_noise = noise - lp
    env = np.minimum(t / duration * 1.4, 1) * np.exp(-2 * t)
    return volume * hp_noise * env


def fade_in_out(audio: np.ndarray, fade_duration: float = 0.05) -> np.ndarray:
    fade_samples = int(SAMPLE_RATE * fade_duration)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    audio[:fade_samples] *= fade_in
    audio[-fade_samples:] *= fade_out
    return audio

# ---------------------------------------------------------------------------
# Build champion sound
# ---------------------------------------------------------------------------

def generate_champion_sound() -> np.ndarray:
    buffer = np.zeros(int(DURATION * SAMPLE_RATE))

    # 1) Drum + cymbal
    drum = drum_hit(0.35, 65, 1.0)
    cymbal = cymbal_swell(0.7, 0.7)
    buffer[: len(drum)] += drum
    cym_start = int(0.05 * SAMPLE_RATE)
    buffer[cym_start : cym_start + len(cymbal)] += cymbal

    # 2) Rising brass arpeggio C-E-G (C major)
    arpeggio = [523.25, 659.25, 783.99]
    note_dur = 0.1
    for idx, f in enumerate(arpeggio):
        note = brass_wave(f, note_dur, 0.8)
        start = int((0.25 + idx * note_dur) * SAMPLE_RATE)
        buffer[start : start + len(note)] += note

    # 3) Final triumphant chord (C-E-G-C6)
    chord_freqs = [523.25, 659.25, 783.99, 1046.50]
    chord = sum(brass_wave(f, 0.45, 0.6) for f in chord_freqs)
    chord_start = int(0.45 * SAMPLE_RATE)
    if chord_start + len(chord) > len(buffer):
        buffer = np.pad(buffer, (0, chord_start + len(chord) - len(buffer)))
    buffer[chord_start : chord_start + len(chord)] += chord

    # 4) Sparkle bells tail
    bell = sine_wave(1046.50, 0.25, 0.25) * np.linspace(1, 0, int(0.25 * SAMPLE_RATE))
    tail_start = int(0.8 * SAMPLE_RATE)
    if tail_start + len(bell) > len(buffer):
        buffer = np.pad(buffer, (0, tail_start + len(bell) - len(buffer)))
    buffer[tail_start : tail_start + len(bell)] += bell

    # Normalize
    max_val = np.max(np.abs(buffer))
    if max_val > 0:
        buffer /= max_val
    return buffer

# ---------------------------------------------------------------------------
# Write file
# ---------------------------------------------------------------------------

OUTPUT_PATH = os.path.join("trackpro", "resources", "sounds", "quest_claim.wav")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
champion = generate_champion_sound()
sf.write(OUTPUT_PATH, champion.astype(np.float32), SAMPLE_RATE)
print(f"Champion fanfare written to: {OUTPUT_PATH}")
