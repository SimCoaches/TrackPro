# 🔊 AI Coach Volume Control Guide

## Overview

Your AI coach now has full volume control! This feature allows you to adjust the AI coach's audio level to match your game audio perfectly.

## ✅ What's New

### 🎚️ **Volume Control Slider**
- Located in the Race Coach status bar (top of the interface)
- Drag the slider to adjust volume from 0% (mute) to 100% (max)
- Real-time volume adjustment - changes apply immediately
- Shows current volume percentage next to the slider

### 🔇 **Mute/Unmute Button**
- Quick mute toggle with a single click
- Remembers your previous volume when unmuting
- Visual feedback - icon changes based on mute state

### 🧪 **Test Button**
- Instantly test the current volume level
- Plays a random AI coach phrase at the selected volume
- Perfect for fine-tuning without needing to trigger actual coaching

### 💾 **Persistent Settings**
- Volume settings automatically save and restore between sessions
- No need to readjust volume every time you start TrackPro
- Settings stored in `ai_coach_volume.json` in your TrackPro folder

## 🎮 How to Use

### Basic Volume Adjustment
1. **Start TrackPro** and open the Race Coach
2. **Locate the volume controls** in the status bar: `🔊 AI Coach: [slider] 80% 🔇 Test`
3. **Drag the slider** left (quieter) or right (louder) to adjust volume
4. **Click "Test"** to hear the AI coach at the current volume
5. **Adjust as needed** until it matches your game audio level

### Quick Mute/Unmute
- **Click the 🔊 button** to instantly mute the AI coach
- **Click the 🔇 button** to unmute and restore previous volume

### Recommended Settings
- **Start with 80%** (default) and adjust from there
- **For loud game audio**: Try 90-100% AI coach volume
- **For quiet game audio**: Try 60-80% AI coach volume
- **During practice**: Use the Test button frequently to find your perfect level

## 🔧 Technical Details

### Audio System Improvements
- **Singleton audio manager** prevents conflicts
- **Real-time volume control** during playback
- **Thread-safe implementation** prevents crashes
- **Persistent volume storage** for seamless experience

### Volume Range
- **Minimum**: 0.0 (completely muted)
- **Maximum**: 1.0 (full volume)
- **Default**: 0.8 (80% - good starting point)
- **Precision**: Volume stored to 2 decimal places

### File Storage
- Volume settings saved to: `ai_coach_volume.json`
- Format: `{"volume": 0.8}`
- Automatically created on first use

## 🎯 Pro Tips

1. **Find Your Sweet Spot**: Test different volumes during practice sessions to find what works best for your setup

2. **Use the Test Button**: Don't wait for actual coaching - use the test button to dial in your perfect volume

3. **Consider Your Audio Setup**: 
   - Headphones: Usually need higher AI coach volume (85-100%)
   - Speakers: May need lower AI coach volume (60-85%)
   - Gaming headsets: Start with 80% and adjust

4. **Race vs Practice**: You might want different volumes for intense racing vs casual practice

5. **Quick Mute for Team Chat**: Use the mute button during team communications, then unmute when done

## 🐛 Troubleshooting

### Volume Not Saving
- Check if `ai_coach_volume.json` exists in your TrackPro folder
- Ensure TrackPro has write permissions to its folder
- Try setting volume again if file gets corrupted

### Volume Control Not Visible
- Restart TrackPro if the volume controls don't appear
- Check the logs for any volume control initialization errors

### Audio Still Too Quiet/Loud
- Remember this only controls AI coach volume, not game volume
- Adjust your overall system/game audio separately
- Consider your audio device's individual volume settings

## 🎉 Enjoy!

The AI coach volume control makes it easy to get the perfect audio balance for your racing experience. No more straining to hear coaching advice or being startled by loud AI feedback!

**Happy Racing!** 🏁 