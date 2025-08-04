#!/usr/bin/env python3
"""
Voice Chat Debug Script

This script tests all components of the voice chat system:
1. Voice server connection
2. Audio device detection
3. Microphone input
4. Audio level detection
5. WebSocket communication
"""

import asyncio
import websockets
import json
import logging
import time
import pyaudio
import numpy as np
from trackpro.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_audio_devices():
    """Test audio device detection."""
    print("\n=== AUDIO DEVICE TEST ===")
    try:
        audio = pyaudio.PyAudio()
        device_count = audio.get_device_count()
        print(f"Found {device_count} audio devices:")
        
        for i in range(device_count):
            try:
                device_info = audio.get_device_info_by_index(i)
                print(f"  Device {i}: {device_info['name']}")
                print(f"    Input channels: {device_info['maxInputChannels']}")
                print(f"    Output channels: {device_info['maxOutputChannels']}")
                print(f"    Sample rate: {device_info['defaultSampleRate']}")
            except Exception as e:
                print(f"  Device {i}: Error - {e}")
        
        audio.terminate()
        return True
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

def test_microphone_input():
    """Test microphone input and audio level detection."""
    print("\n=== MICROPHONE INPUT TEST ===")
    try:
        audio = pyaudio.PyAudio()
        
        # Open input stream
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=48000,
            input=True,
            frames_per_buffer=512
        )
        
        print("🎤 Speak into your microphone for 5 seconds...")
        
        start_time = time.time()
        while time.time() - start_time < 5:
            try:
                data = stream.read(512, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                level = min(rms / 32767.0, 1.0)
                
                # Visual indicator
                if level > 0.5:
                    indicator = "🔴"
                elif level > 0.2:
                    indicator = "🟡"
                elif level > 0.05:
                    indicator = "🟢"
                else:
                    indicator = "🎤"
                
                print(f"\r{indicator} Audio Level: {level:.3f} ({rms:.1f})", end="", flush=True)
                
            except Exception as e:
                print(f"\n❌ Error reading microphone: {e}")
                break
        
        print("\n✅ Microphone test completed")
        stream.stop_stream()
        stream.close()
        audio.terminate()
        return True
        
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False

async def test_voice_server():
    """Test voice server connection and communication."""
    print("\n=== VOICE SERVER TEST ===")
    try:
        print("Connecting to voice server...")
        async with websockets.connect('ws://localhost:8080/voice/general') as websocket:
            print("✅ Connected to voice server")
            
            # Send user info
            user_info = {
                'type': 'user_info',
                'user_name': 'DebugUser'
            }
            await websocket.send(json.dumps(user_info))
            print("✅ Sent user info")
            
            # Wait for welcome message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✅ Received: {data.get('type')}")
            
            # Send test voice data
            test_audio = [0] * 512  # Silent audio for testing
            voice_data = {
                'type': 'voice_data',
                'audio': test_audio
            }
            await websocket.send(json.dumps(voice_data))
            print("✅ Sent test voice data")
            
            # Wait for any response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(response)
                print(f"✅ Received response: {data.get('type')}")
            except asyncio.TimeoutError:
                print("⏰ No response received (this is normal for test data)")
            
            print("✅ Voice server test completed")
            return True
            
    except Exception as e:
        print(f"❌ Voice server test failed: {e}")
        return False

async def test_voice_manager():
    """Test the voice manager directly."""
    print("\n=== VOICE MANAGER TEST ===")
    try:
        from trackpro.ui.pages.community.high_quality_voice_manager import HighQualityVoiceManager
        
        voice_manager = HighQualityVoiceManager()
        print("✅ Voice manager created")
        
        # Test device detection
        devices = voice_manager.get_available_devices()
        print(f"✅ Found {len(devices['input'])} input devices and {len(devices['output'])} output devices")
        
        # Test audio level calculation
        test_audio = bytes([0] * 1024)  # Silent audio
        level = voice_manager._calculate_audio_level(test_audio)
        print(f"✅ Audio level calculation: {level:.3f}")
        
        print("✅ Voice manager test completed")
        return True
        
    except Exception as e:
        print(f"❌ Voice manager test failed: {e}")
        return False

async def main():
    """Run all voice chat tests."""
    print("🎤 VOICE CHAT DEBUG SCRIPT")
    print("=" * 50)
    
    # Test 1: Audio devices
    audio_devices_ok = test_audio_devices()
    
    # Test 2: Microphone input
    microphone_ok = test_microphone_input()
    
    # Test 3: Voice server
    server_ok = await test_voice_server()
    
    # Test 4: Voice manager
    manager_ok = await test_voice_manager()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎤 TEST SUMMARY")
    print("=" * 50)
    print(f"Audio Devices: {'✅' if audio_devices_ok else '❌'}")
    print(f"Microphone Input: {'✅' if microphone_ok else '❌'}")
    print(f"Voice Server: {'✅' if server_ok else '❌'}")
    print(f"Voice Manager: {'✅' if manager_ok else '❌'}")
    
    if all([audio_devices_ok, microphone_ok, server_ok, manager_ok]):
        print("\n🎉 All tests passed! Voice chat should work properly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        
        if not audio_devices_ok:
            print("  - Check if audio devices are properly connected")
        if not microphone_ok:
            print("  - Check microphone permissions and settings")
        if not server_ok:
            print("  - Check if voice server is running on port 8080")
        if not manager_ok:
            print("  - Check voice manager dependencies")

if __name__ == "__main__":
    asyncio.run(main()) 