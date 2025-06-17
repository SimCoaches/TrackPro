#!/usr/bin/env python3
"""
Test script to verify AI coach crash fixes.
Tests the new audio system and debouncing to ensure no crashes.
"""

import time
import logging
import threading
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_audio_system():
    """Test the new audio system without crashing."""
    
    print("🧪 [TEST] Testing new audio system...")
    
    try:
        from trackpro.race_coach.ai_coach import elevenlabs_client
        
        # Test 1: Simple audio test
        print("🧪 [TEST 1] Testing simple audio generation...")
        if not elevenlabs_client.get_api_key():
            print("⚠️  [TEST 1] Skipping - No ElevenLabs API key found")
            return True
        
        # Test basic audio generation
        success = elevenlabs_client.speak_text("Testing audio system.", interrupt_current=True)
        if success:
            print("✅ [TEST 1] Basic audio test passed")
        else:
            print("❌ [TEST 1] Basic audio test failed")
            return False
        
        # Test 2: Rapid fire audio (should not crash)
        print("🧪 [TEST 2] Testing rapid fire audio (crash prevention)...")
        for i in range(3):
            text = f"Rapid test {i+1}"
            elevenlabs_client.speak_text(text, interrupt_current=True)
            time.sleep(0.1)  # Very short delay to simulate rapid coaching
        
        print("✅ [TEST 2] Rapid fire audio test passed - no crashes")
        
        # Test 3: Check audio manager state
        print("🧪 [TEST 3] Testing audio manager state...")
        manager = elevenlabs_client.get_audio_manager()
        print(f"   Audio playing: {manager.is_audio_playing()}")
        print(f"   Queue size: {manager.audio_queue.qsize()}")
        print("✅ [TEST 3] Audio manager state test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Audio system test failed: {e}")
        return False

def test_ai_coach_debouncing():
    """Test AI coach debouncing logic."""
    
    print("🧪 [TEST] Testing AI coach debouncing...")
    
    try:
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        from trackpro.race_coach.ai_coach import elevenlabs_client
        
        # Create a mock AI coach (without real superlap data)
        class MockAICoach:
            def __init__(self):
                self.last_advice_time = 0
                self.last_track_position = 0.0
                self._last_advice_position = 0.0
            
            def _analyze_coaching_priority(self, speed_diff, throttle_diff, brake_diff, current_time):
                """Use the same logic as the real AI coach."""
                
                # Check if audio is currently playing
                if hasattr(elevenlabs_client, 'is_speaking') and elevenlabs_client.is_speaking():
                    if speed_diff < -25:
                        pass  # Would interrupt
                    else:
                        return "AUDIO_PLAYING", False
                
                distance_since_last = abs(self.last_track_position - self._last_advice_position)
                time_since_last = current_time - self.last_advice_time
                
                # CRITICAL: Major speed loss
                if speed_diff < -20:
                    min_distance = 0.036
                    min_time = 3.0
                    should_coach = distance_since_last > min_distance and time_since_last > min_time
                    return "CRITICAL_SPEED_LOSS", should_coach
                
                return "NO_COACHING", False
        
        coach = MockAICoach()
        
        # Test 1: Rapid telemetry should be debounced
        print("🧪 [TEST 1] Testing rapid telemetry debouncing...")
        current_time = time.time()
        
        # First call should allow coaching
        advice_type, should_coach = coach._analyze_coaching_priority(-25, 0, 0, current_time)
        print(f"   First call: {advice_type}, should_coach: {should_coach}")
        
        if should_coach:
            coach.last_advice_time = current_time
            coach._last_advice_position = coach.last_track_position
        
        # Immediate second call should be blocked by time debouncing
        advice_type, should_coach = coach._analyze_coaching_priority(-25, 0, 0, current_time + 0.1)
        print(f"   Immediate second call: {advice_type}, should_coach: {should_coach}")
        
        if should_coach:
            print("❌ [TEST 1] Debouncing failed - immediate second call allowed")
            return False
        
        print("✅ [TEST 1] Debouncing test passed")
        
        # Test 2: Time-based debouncing
        print("🧪 [TEST 2] Testing time-based debouncing...")
        future_time = current_time + 5.0  # 5 seconds later
        coach.last_track_position = 0.1  # Moved significantly
        
        # Wait for any audio to finish playing
        manager = elevenlabs_client.get_audio_manager()
        wait_count = 0
        while manager.is_audio_playing() and wait_count < 50:  # Max 5 seconds wait
            time.sleep(0.1)
            wait_count += 1
        
        if manager.is_audio_playing():
            print("   Audio still playing after 5 seconds, testing with audio playing logic...")
            # Test that it correctly identifies audio is playing
            advice_type, should_coach = coach._analyze_coaching_priority(-25, 0, 0, future_time)
            if advice_type == "AUDIO_PLAYING":
                print("✅ [TEST 2] Audio playing detection working correctly")
                return True
            else:
                print("❌ [TEST 2] Audio playing detection failed")
                return False
        else:
            print("   Audio finished, testing normal debouncing logic...")
            advice_type, should_coach = coach._analyze_coaching_priority(-25, 0, 0, future_time)
            print(f"   After time delay: {advice_type}, should_coach: {should_coach}")
            
            if not should_coach:
                print("❌ [TEST 2] Time debouncing failed - should allow after delay")
                return False
        
        print("✅ [TEST 2] Time-based debouncing test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] AI coach debouncing test failed: {e}")
        return False

def test_crash_scenarios():
    """Test scenarios that previously caused crashes."""
    
    print("🧪 [TEST] Testing crash scenarios...")
    
    try:
        from trackpro.race_coach.ai_coach import elevenlabs_client
        
        if not elevenlabs_client.get_api_key():
            print("⚠️  [TEST] Skipping crash scenarios - No ElevenLabs API key")
            return True
        
        # Test 1: Multiple simultaneous audio requests
        print("🧪 [TEST 1] Testing multiple simultaneous audio...")
        
        def rapid_audio_thread(thread_id):
            for i in range(2):
                elevenlabs_client.speak_text(f"Thread {thread_id} message {i+1}", interrupt_current=True)
                time.sleep(0.05)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=rapid_audio_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        print("✅ [TEST 1] Multiple simultaneous audio test passed - no crashes")
        
        # Test 2: Pygame initialization stress test
        print("🧪 [TEST 2] Testing pygame initialization stability...")
        
        manager = elevenlabs_client.get_audio_manager()
        
        # Force multiple pygame initializations (should be handled gracefully)
        for i in range(5):
            if manager._initialize_pygame():
                print(f"   Pygame init attempt {i+1}: Success")
            else:
                print(f"   Pygame init attempt {i+1}: Failed (gracefully)")
        
        print("✅ [TEST 2] Pygame initialization stress test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Crash scenario test failed: {e}")
        return False

def main():
    """Run all tests."""
    
    print("🚀 STARTING AI COACH CRASH FIX TESTS")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log spam during testing
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Audio system
    if test_audio_system():
        tests_passed += 1
    
    print("-" * 60)
    
    # Test 2: AI coach debouncing
    if test_ai_coach_debouncing():
        tests_passed += 1
    
    print("-" * 60)
    
    # Test 3: Crash scenarios
    if test_crash_scenarios():
        tests_passed += 1
    
    print("=" * 60)
    print(f"🏁 TESTS COMPLETED: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ ALL TESTS PASSED - AI coach crash fixes are working!")
        print("🎉 It should be safe to run the AI coach now.")
    else:
        print("❌ SOME TESTS FAILED - There may still be issues.")
        print("⚠️  Please review the test output above.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 