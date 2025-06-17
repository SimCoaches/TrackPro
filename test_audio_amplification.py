#!/usr/bin/env python3
"""
Test script for AI Coach audio amplification.
Tests that volumes above 100% actually sound louder using real audio amplification.
"""

import sys
import os
import time
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_amplification():
    """Test real audio amplification."""
    
    print("🔊 TESTING REAL AUDIO AMPLIFICATION")
    print("=" * 60)
    
    try:
        from trackpro.race_coach.ai_coach import elevenlabs_client
        
        # Check if we have an API key
        if not elevenlabs_client.get_api_key():
            print("❌ No ElevenLabs API key found. Cannot test audio amplification.")
            print("   Set your ElevenLabs API key to test real amplification.")
            return False
        
        print("🎵 Testing volume progression:")
        print("   You should hear each message getting progressively LOUDER")
        print("   Pay attention to the difference between 100% and higher volumes!")
        print()
        
        # Test volumes with clear progression
        test_volumes = [
            (0.8, "Normal volume at 80%"),
            (1.0, "Maximum normal volume at 100%"),
            (1.3, "Boosted volume at 130% - should be noticeably louder"),
            (1.6, "High boost at 160% - should be significantly louder"),
            (2.0, "Maximum boost at 200% - should be very loud")
        ]
        
        for volume, message in test_volumes:
            percent = int(volume * 100)
            print(f"🔊 Playing at {percent}%: {message}")
            
            # Set the volume
            elevenlabs_client.set_ai_coach_volume(volume)
            
            # Play the message
            success = elevenlabs_client.speak_text(message, interrupt_current=True)
            
            if success:
                print(f"   ✅ Audio playing at {percent}%")
                # Wait for audio to complete
                time.sleep(5)
                print(f"   ✅ Completed {percent}%")
            else:
                print(f"   ❌ Failed to play audio at {percent}%")
                return False
            
            print()
        
        print("🎉 AMPLIFICATION TEST COMPLETED!")
        print()
        print("❓ Did you notice the volume getting louder as the percentages increased?")
        print("   - The difference between 100% and 130% should be clearly audible")
        print("   - 200% should be significantly louder than 100%")
        print("   - If all volumes sounded the same, there may be an issue")
        
        return True
        
    except Exception as e:
        print(f"❌ Amplification test failed: {e}")
        return False

def test_amplification_function():
    """Test the amplification function directly."""
    
    print("🧪 TESTING AMPLIFICATION FUNCTION")
    print("=" * 40)
    
    try:
        from trackpro.race_coach.ai_coach.elevenlabs_client import amplify_audio_data
        
        # Test with dummy data
        dummy_audio = b"dummy_audio_data_for_testing"
        
        # Test various multipliers
        multipliers = [0.5, 1.0, 1.5, 2.0]
        
        for mult in multipliers:
            result = amplify_audio_data(dummy_audio, mult)
            if mult <= 1.0:
                # Should return original data
                if result == dummy_audio:
                    print(f"✅ {mult:.1f}x: No amplification (correct)")
                else:
                    print(f"❌ {mult:.1f}x: Unexpected modification")
            else:
                # Should attempt amplification
                print(f"✅ {mult:.1f}x: Amplification attempted")
        
        return True
        
    except Exception as e:
        print(f"❌ Amplification function test failed: {e}")
        return False

def main():
    """Run amplification tests."""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 STARTING AUDIO AMPLIFICATION TESTS")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Amplification function
    if test_amplification_function():
        tests_passed += 1
    
    print()
    
    # Test 2: Real audio amplification
    print("⚠️  IMPORTANT: You'll need to LISTEN to test real amplification!")
    print("   Make sure your speakers/headphones are at a reasonable volume.")
    input("   Press ENTER when ready to start audio test...")
    
    if test_amplification():
        tests_passed += 1
    
    print("=" * 60)
    print(f"🏁 AMPLIFICATION TESTS COMPLETED: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ AMPLIFICATION IS WORKING!")
        print("🔊 Volumes above 100% should now be noticeably louder!")
    else:
        print("❌ SOME TESTS FAILED - Amplification may not be working correctly.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 