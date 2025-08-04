# TrackPro High-Quality Voice Chat System

## Overview

TrackPro now features a **professional-grade voice chat system** with high-quality audio, advanced device selection, and real-time communication capabilities. This system provides crystal-clear voice communication for racing teams, coaches, and community members.

## Key Features

### 🎯 High-Quality Audio
- **48kHz Sample Rate** - Professional audio quality
- **24-bit Audio Depth** - Superior dynamic range
- **Stereo Support** - Full spatial audio experience
- **Low Latency** - 512ms buffer for real-time communication

### 🎤 Advanced Device Selection
- **Microphone Selection** - Choose your preferred input device
- **Speaker/Headphone Selection** - Select your audio output
- **Volume Controls** - Independent input/output volume
- **Audio Testing** - Test your microphone and speakers

### 🔧 Audio Processing
- **Noise Suppression** - Automatic background noise reduction
- **Echo Cancellation** - Prevents audio feedback
- **Automatic Gain Control** - Maintains consistent audio levels
- **Real-time Audio Level Meters** - Visual feedback for audio input

### 🌐 Network Features
- **WebSocket Communication** - Real-time voice transmission
- **Automatic Server Management** - Server starts automatically
- **Channel Support** - Multiple voice channels
- **User Presence** - See who's in each channel

## Installation Requirements

### Required Dependencies
```bash
pip install pyaudio numpy websockets
```

### Windows-Specific Installation
If PyAudio installation fails on Windows:
```bash
# Method 1: Use pipwin
pip install pipwin
pipwin install pyaudio

# Method 2: Download wheel file
# Download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/
# Example: pip install PyAudio-0.2.11-cp39-cp39-win_amd64.whl
```

### System Requirements
- **Windows 10/11** (64-bit)
- **Python 3.8+** (3.11 recommended)
- **Microphone** (USB or 3.5mm)
- **Speakers/Headphones** (for audio output)
- **Internet Connection** (for voice transmission)

## How to Use

### 1. Access Voice Chat
1. Open TrackPro
2. Navigate to the **Community** page
3. Select a **Voice Channel** (channels with 🔊 icon)
4. Click **"Join Channel"**

### 2. Configure Audio Settings
1. Click the **"⚙️ Settings"** button in voice channels
2. Select your **microphone** from the dropdown
3. Choose your **speakers/headphones**
4. Adjust **input/output volume**
5. Test your audio with **"Test Microphone"** and **"Test Speakers"**
6. Click **"Apply Settings"**

### 3. Voice Chat Controls
- **🎤 Mute** - Mute your microphone
- **🔊 Deafen** - Mute incoming audio
- **Volume Slider** - Adjust output volume
- **Audio Level Meter** - Visual indicator of your input level

## Technical Architecture

### Components

#### 1. Voice Settings Dialog (`voice_settings_dialog.py`)
- **Device Enumeration** - Lists available audio devices
- **Audio Quality Settings** - Sample rate, bit depth, channels
- **Volume Controls** - Input/output volume sliders
- **Audio Testing** - Microphone and speaker test functions

#### 2. High-Quality Voice Manager (`high_quality_voice_manager.py`)
- **Audio Processing** - Noise suppression, echo cancellation
- **Device Management** - Input/output device selection
- **Real-time Audio** - Low-latency audio streaming
- **Quality Enhancement** - Automatic gain control

#### 3. Voice Server (`high_quality_voice_server.py`)
- **WebSocket Server** - Real-time communication
- **Audio Broadcasting** - Multi-user voice transmission
- **Channel Management** - Multiple voice channels
- **Connection Monitoring** - Automatic cleanup

#### 4. Server Manager (`voice_server_manager.py`)
- **Automatic Startup** - Server starts with TrackPro
- **Process Management** - Monitors server health
- **Error Handling** - Graceful failure recovery

### Audio Quality Specifications

| Setting | Value | Description |
|---------|-------|-------------|
| Sample Rate | 48kHz | Professional audio standard |
| Bit Depth | 24-bit | High dynamic range |
| Channels | Stereo (2) | Full spatial audio |
| Buffer Size | 512 samples | Low latency |
| Format | PCM | Uncompressed audio |

### Audio Processing Pipeline

```
Microphone Input → PyAudio Capture → Audio Processing → WebSocket → Server → Other Users
                                                                    ↓
User Output ← PyAudio Playback ← Audio Processing ← WebSocket ← Server ← Other Users
```

## Troubleshooting

### Common Issues

#### 1. "PyAudio not available" Error
**Solution:**
```bash
# Windows
pip install pipwin
pipwin install pyaudio

# Alternative
pip install PyAudio --force-reinstall
```

#### 2. No Audio Input/Output
**Check:**
- Windows microphone permissions
- Device selection in voice settings
- Volume levels in Windows settings
- Test audio devices in voice settings

#### 3. High Latency
**Solutions:**
- Reduce buffer size in voice settings
- Check internet connection
- Close other audio applications
- Use wired connection instead of WiFi

#### 4. Audio Quality Issues
**Solutions:**
- Increase sample rate to 48kHz
- Use 24-bit audio depth
- Enable noise suppression
- Check microphone quality

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Audio system not available" | PyAudio not installed | Install PyAudio |
| "Voice server not found" | Server script missing | Check file paths |
| "Device not found" | Audio device disconnected | Reconnect device |
| "Connection failed" | Network issues | Check internet connection |

## Advanced Configuration

### Custom Audio Settings
Edit voice settings for optimal performance:

```python
# High-quality settings
settings = {
    'sample_rate': 48000,      # 48kHz
    'channels': 2,             # Stereo
    'bit_depth': 24,           # 24-bit
    'buffer_size': 512,        # Low latency
    'noise_suppression': True,
    'echo_cancellation': True,
    'automatic_gain': True
}
```

### Server Configuration
Modify server settings in `high_quality_voice_server.py`:

```python
# Performance settings
self.max_clients_per_channel = 50
self.audio_buffer_size = 1000  # ms
self.connection_timeout = 30   # seconds
```

## Performance Optimization

### For Best Audio Quality
1. **Use USB Microphone** - Better quality than built-in
2. **Wired Internet** - Lower latency than WiFi
3. **Close Other Apps** - Reduce CPU usage
4. **Update Audio Drivers** - Latest drivers for best performance

### For Low Latency
1. **Reduce Buffer Size** - 256 or 512 samples
2. **Use Mono Audio** - Less data to transmit
3. **16-bit Audio** - Smaller packet size
4. **Local Network** - Lower ping times

## Security Considerations

### Voice Data
- **No Persistent Storage** - Voice data not saved
- **Real-time Only** - No recording capabilities
- **Local Processing** - Audio processed on your device
- **Secure Transmission** - WebSocket encryption

### Privacy
- **User Consent** - Users control their audio
- **Mute Controls** - Easy to mute/unmute
- **Device Permissions** - Windows microphone permissions
- **No Recording** - Voice chat is live only

## Future Enhancements

### Planned Features
- **End-to-End Encryption** - Secure voice transmission
- **Advanced Codecs** - Opus/WebRTC support
- **Screen Sharing** - Share screen during voice calls
- **Mobile Support** - iOS/Android apps
- **Cloud Recording** - Optional voice recording
- **AI Noise Reduction** - Machine learning noise suppression

### Technical Improvements
- **WebRTC Integration** - Better audio codecs
- **Scalable Architecture** - Multiple server support
- **Advanced Moderation** - AI-powered content filtering
- **Quality Adaptation** - Automatic quality adjustment

## Support

### Getting Help
1. **Check Troubleshooting** - Common solutions above
2. **Test Audio Devices** - Use voice settings testing
3. **Check Logs** - Look for error messages
4. **Update Dependencies** - Ensure latest versions

### Reporting Issues
When reporting voice chat issues, include:
- **Error Messages** - Exact error text
- **Audio Devices** - Microphone and speaker models
- **System Info** - Windows version, Python version
- **Steps to Reproduce** - How to trigger the issue

---

**Note:** The voice chat system is designed for professional use with high-quality audio. For best results, use quality audio equipment and a stable internet connection. 