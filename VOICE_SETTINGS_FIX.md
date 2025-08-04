# Voice Settings Fix Guide

## Issue
When trying to access voice settings in TrackPro, you get the error:
```
Failed to open voice settings: name 'VoiceSettingsDialog' is not defined
```

## Cause
This error occurs because PyAudio is not installed on your system. PyAudio is required for voice chat functionality in TrackPro.

## Solution

### Option 1: Automatic Installation (Recommended)
Run the voice dependencies installer:
```bash
python install_voice_dependencies.py
```

### Option 2: Manual Installation

#### Step 1: Install PyAudio
```bash
pip install --user pyaudio
```

If that fails on Windows, try:
```bash
pip install --user pipwin
pipwin install pyaudio
```

#### Step 2: Install other dependencies
```bash
pip install --user numpy websockets
```

### Option 3: Download PyAudio Wheel (Windows)
1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/
2. Download the correct PyAudio wheel for your Python version
3. Install with: `pip install --user <downloaded-file>.whl`

## Verification
After installation, restart TrackPro and try accessing voice settings again. The error should be resolved.

## Troubleshooting
- If you still get errors, try running the installer script: `python install_voice_dependencies.py`
- Make sure you have microphone permissions enabled in Windows settings
- Ensure you're using Python 3.8+ (3.11 recommended)

## Next Steps
Once PyAudio is installed:
1. Go to the Community page in TrackPro
2. Join a voice channel
3. Click the settings gear icon to configure voice settings
4. Test your microphone and speakers 