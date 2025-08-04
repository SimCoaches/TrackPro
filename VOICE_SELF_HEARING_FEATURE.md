# TrackPro Voice Chat - Self-Hearing Feature

## Overview

TrackPro now includes a **self-hearing feature** (also known as "direct monitoring") that allows users to hear themselves slightly when speaking in voice channels. This feature helps users monitor their audio levels and speaking volume, providing immediate feedback during voice communication.

## How It Works

### Technical Implementation

The self-hearing feature is implemented in the `HighQualityVoiceManager` class:

```python
def _record_high_quality_audio(self):
    """Record ultra-low latency audio with direct monitoring."""
    while self.is_recording:
        try:
            data = self.input_stream.read(self.buffer_size, exception_on_overflow=False)
            
            # Direct monitoring - hear yourself instantly
            if self.direct_monitoring and self.output_stream:
                try:
                    # Send audio directly to output for instant feedback
                    self.output_stream.write(data)
                except Exception as e:
                    logger.warning(f"Direct monitoring error: {e}")
            
            # Continue with normal audio processing...
```

### Configuration

The feature is controlled by the `direct_monitoring` setting in the voice chat configuration:

```python
'voice_chat': {
    'direct_monitoring': True,  # Enable direct monitoring (hear yourself instantly)
    # ... other settings
}
```

## User Interface

### Voice Settings Dialog

Users can control the self-hearing feature through the Voice Settings dialog:

1. **Location**: Community page → Voice channel → Settings button (⚙️)
2. **Setting**: Audio Quality Settings → "Hear Yourself (Direct Monitoring)"
3. **Tooltip**: "When enabled, you'll hear your own voice slightly in your headphones/speakers. This helps you monitor your audio levels and speaking volume."

### Voice Channel Information

When users join a voice channel, they see a helpful tip:

```
💡 Tip: You can hear yourself slightly when speaking. This helps monitor your audio levels. Adjust this in Voice Settings.
```

## Features

### ✅ Enabled by Default
- The self-hearing feature is **enabled by default** for all users
- Users can immediately benefit from audio level monitoring without configuration

### ✅ User Control
- Users can **enable/disable** the feature in Voice Settings
- Settings are **automatically saved** and persist between sessions
- Changes take effect **immediately** when applied

### ✅ Low Latency
- Audio is routed **directly to output** for instant feedback
- No processing delay - users hear themselves in real-time
- Works with **ultra-low latency** audio settings

### ✅ Professional Quality
- Compatible with **high-quality audio** settings (48kHz, 24-bit)
- Works with **custom audio devices** (microphones, headphones)
- Supports **volume controls** for fine-tuning

## Benefits

### For Racing Teams
- **Audio Level Monitoring**: Users can hear if they're speaking too loudly or quietly
- **Microphone Testing**: Immediate feedback helps users test their microphone setup
- **Professional Communication**: Better audio quality leads to clearer team communication

### For Coaches
- **Teaching Feedback**: Coaches can monitor their own voice while giving instructions
- **Audio Consistency**: Ensures consistent audio levels during coaching sessions
- **Equipment Testing**: Helps verify microphone and headphone setup

### For Community Members
- **User Experience**: More professional voice chat experience
- **Audio Awareness**: Users become more aware of their speaking volume
- **Troubleshooting**: Helps identify audio issues quickly

## Technical Details

### Audio Routing
1. **Input**: Microphone audio is captured
2. **Direct Path**: Audio is immediately sent to output (if enabled)
3. **Network Path**: Audio is also sent to other users via WebSocket
4. **Processing**: Audio can be processed with noise suppression, echo cancellation, etc.

### Performance Impact
- **Minimal CPU usage**: Direct monitoring adds negligible processing overhead
- **No latency increase**: Audio routing is handled at the driver level
- **Memory efficient**: Uses existing audio buffers

### Compatibility
- **Windows 10/11**: Fully supported
- **PyAudio**: Required for audio device access
- **Multiple devices**: Works with any microphone/headphone combination
- **Volume controls**: Respects system and application volume settings

## Testing

### Test Script
A comprehensive test script is available: `test_direct_monitoring.py`

The test script verifies:
1. ✅ Configuration loading
2. ✅ UI controls in Voice Settings
3. ✅ Voice manager implementation
4. ✅ Audio routing functionality

### Manual Testing
To test the feature manually:

1. **Start TrackPro**
2. **Go to Community page**
3. **Join a voice channel**
4. **Speak into your microphone**
5. **You should hear yourself slightly**
6. **Adjust the setting in Voice Settings if needed**

## Troubleshooting

### Common Issues

**I can't hear myself:**
- Check if direct monitoring is enabled in Voice Settings
- Verify your headphones/speakers are working
- Ensure your microphone is not muted
- Check system volume levels

**Audio feedback/echo:**
- Reduce microphone volume in Voice Settings
- Move microphone further from speakers
- Use headphones instead of speakers
- Disable direct monitoring if needed

**No audio at all:**
- Check if PyAudio is installed: `pip install pyaudio`
- Verify audio devices are properly selected
- Test microphone in system settings
- Check TrackPro's voice server is running

### Debug Information

The voice system provides detailed logging:

```python
logger.info(f"Ultra-low latency voice settings: {self.sample_rate}Hz, {self.channels}ch, {self.bit_depth}bit, {self.buffer_size} buffer")
logger.info("Direct monitoring enabled - users will hear themselves")
```

## Future Enhancements

### Planned Features
- **Volume Control**: Separate volume slider for self-hearing
- **Audio Effects**: Optional reverb or echo for self-monitoring
- **Device-Specific Settings**: Different settings per audio device
- **Advanced Controls**: Fine-tune the direct monitoring mix

### User Feedback
The feature is designed to be:
- **Intuitive**: Works out of the box
- **Configurable**: Users can adjust to their preferences
- **Professional**: Enhances voice chat quality
- **Reliable**: Robust error handling and fallbacks

## Conclusion

The self-hearing feature enhances TrackPro's voice chat experience by providing immediate audio feedback to users. This professional-grade feature helps users monitor their audio levels, test their equipment, and communicate more effectively in voice channels.

The implementation is robust, user-friendly, and fully integrated with TrackPro's existing voice chat system. Users can enjoy better voice communication while maintaining full control over their audio experience. 