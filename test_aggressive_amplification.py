#!/usr/bin/env python3
"""
Quick test for aggressive audio amplification.
Tests the new scaling: 100% = 1.8x, 160% = 3.3x, 200% = 4.3x
"""

import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_aggressive_volumes():
    """Test the new aggressive volume scaling."""
    
    print("🔊 TESTING AGGRESSIVE VOLUME SCALING")
    print("=" * 50)
    print("NEW SCALING:")
    print("  100% = 1.8x actual amplification")
    print("  130% = 2.55x actual amplification") 
    print("  160% = 3.3x actual amplification")
    print("  200% = 4.3x actual amplification")
    print()
    print("You should hear MAJOR differences between each level!")
    print()
    
    try:
        from trackpro.race_coach.ai_coach import elevenlabs_client
        
        # Check API key
        if not elevenlabs_client.get_api_key():
            print("❌ No ElevenLabs API key - cannot test")
            return False
        
        # Test volumes with new scaling
        test_volumes = [
            (1.0, "One hundred percent - should be much louder than before"),
            (1.3, "One thirty percent - should be noticeably louder than 100%"),
            (1.6, "One sixty percent - should be significantly louder"),
            (2.0, "Two hundred percent - should be very loud")
        ]
        
        for volume, message in test_volumes:
            # Calculate what the actual amplification will be
            if volume == 1.0:
                actual_amp = 1.8
            else:
                actual_amp = 1.8 + (volume - 1.0) * 2.5
            
            percent = int(volume * 100)
            print(f"🔊 {percent}% (actual {actual_amp:.1f}x amplification): {message}")
            
            # Set volume and play
            elevenlabs_client.set_ai_coach_volume(volume)
            success = elevenlabs_client.speak_text(message, interrupt_current=True)
            
            if success:
                print(f"   ✅ Playing at {percent}% → {actual_amp:.1f}x actual")
                time.sleep(4)  # Let it play
                print(f"   ✅ Completed {percent}%")
            else:
                print(f"   ❌ Failed at {percent}%")
                return False
            
            print()
        
        print("🎉 AGGRESSIVE AMPLIFICATION TEST COMPLETED!")
        print()
        print("❓ RESULTS:")
        print("  - Did 100% sound much louder than the old 100%?")
        print("  - Was there a clear progression from 100% → 130% → 160% → 200%?")
        print("  - Did 200% sound SIGNIFICANTLY louder than 100%?")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    input("Press ENTER when ready to test the new aggressive amplification...")
    success = test_aggressive_volumes()
    
    if success:
        print("\n✅ Test completed! The new amplification should be much more noticeable.")
    else:
        print("\n❌ Test failed - there may still be issues with amplification.") 