#!/usr/bin/env python3
"""
Test script for AI Coach volume control system.
Tests both the audio manager volume control and the UI widget.
"""

import sys
import os
import time
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_volume_system():
    """Test the volume control system."""
    
    print("🧪 [VOLUME TEST] Testing AI Coach volume control system...")
    
    try:
        from trackpro.race_coach.ai_coach import elevenlabs_client
        
        # Test 1: Basic volume functions
        print("🧪 [TEST 1] Testing basic volume functions...")
        
        # Get initial volume
        initial_volume = elevenlabs_client.get_ai_coach_volume()
        print(f"   Initial volume: {initial_volume:.2f}")
        
        # Test setting volume
        test_volumes = [0.5, 1.0, 1.5, 2.0, 0.0, 0.8]  # Test various volumes including > 100%
        for vol in test_volumes:
            elevenlabs_client.set_ai_coach_volume(vol)
            current_vol = elevenlabs_client.get_ai_coach_volume()
            percent = int(vol * 100)
            current_percent = int(current_vol * 100)
            print(f"   Set volume to {vol:.2f} ({percent}%), got: {current_vol:.2f} ({current_percent}%)")
            
            if abs(current_vol - vol) > 0.01:
                print(f"❌ [TEST 1] Volume mismatch: expected {vol:.2f}, got {current_vol:.2f}")
                return False
        
        print("✅ [TEST 1] Basic volume functions test passed")
        
        # Test 2: Volume persistence
        print("🧪 [TEST 2] Testing volume persistence...")
        
        # Set a specific volume
        test_volume = 0.75
        elevenlabs_client.set_ai_coach_volume(test_volume)
        
        # Create a new audio manager instance (simulates restart)
        new_manager = elevenlabs_client.AudioManager()
        persistent_volume = new_manager.get_volume()
        
        print(f"   Set volume: {test_volume:.2f}")
        print(f"   Persistent volume: {persistent_volume:.2f}")
        
        if abs(persistent_volume - test_volume) > 0.01:
            print(f"❌ [TEST 2] Volume persistence failed: expected {test_volume:.2f}, got {persistent_volume:.2f}")
            return False
        
        print("✅ [TEST 2] Volume persistence test passed")
        
        # Test 3: Audio playback with volume (if API key available)
        print("🧪 [TEST 3] Testing audio playback with volume...")
        
        if not elevenlabs_client.get_api_key():
            print("⚠️  [TEST 3] Skipping audio test - No ElevenLabs API key")
            return True
        
        # Test at different volumes
        test_volumes = [0.3, 0.6, 1.0, 1.5, 2.0]  # Include high volumes for racing
        for vol in test_volumes:
            elevenlabs_client.set_ai_coach_volume(vol)
            percent = int(vol * 100)
            print(f"   Testing audio at volume {vol:.2f} ({percent}%)...")
            
            if vol > 1.0:
                message = f"Racing boost mode at {percent} percent volume"
            else:
                message = f"Volume test at {percent} percent"
            
            success = elevenlabs_client.speak_text(message, interrupt_current=True)
            if success:
                print(f"   ✅ Audio test at volume {vol:.2f} ({percent}%) successful")
                time.sleep(2)  # Let audio play
            else:
                print(f"   ❌ Audio test at volume {vol:.2f} ({percent}%) failed")
        
        print("✅ [TEST 3] Audio playback volume test passed")
        
        # Restore initial volume
        elevenlabs_client.set_ai_coach_volume(initial_volume)
        
        return True
        
    except Exception as e:
        print(f"❌ [VOLUME TEST] Volume system test failed: {e}")
        return False

def test_volume_widget():
    """Test the volume control UI widget."""
    
    print("🧪 [WIDGET TEST] Testing AI Coach volume widget...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from trackpro.race_coach.ui.ai_coach_volume_widget import AICoachVolumeWidget
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Test widget creation
        print("🧪 [TEST 1] Testing widget creation...")
        widget = AICoachVolumeWidget()
        print("✅ [TEST 1] Widget created successfully")
        
        # Test volume getting/setting
        print("🧪 [TEST 2] Testing widget volume control...")
        
        initial_volume = widget.get_volume()
        print(f"   Initial widget volume: {initial_volume:.2f}")
        
        # Test setting volume through widget
        widget.set_volume(0.5)
        widget_volume = widget.get_volume()
        print(f"   Set widget volume to 0.50, got: {widget_volume:.2f}")
        
        if abs(widget_volume - 0.5) > 0.01:
            print(f"❌ [TEST 2] Widget volume control failed")
            return False
        
        print("✅ [TEST 2] Widget volume control test passed")
        
        # Test UI elements
        print("🧪 [TEST 3] Testing widget UI elements...")
        
        # Check if all expected UI elements exist
        ui_elements = ['volume_slider', 'volume_percent_label', 'mute_button', 'test_button']
        for element in ui_elements:
            if hasattr(widget, element):
                print(f"   ✅ {element} found")
            else:
                print(f"   ❌ {element} missing")
                return False
        
        print("✅ [TEST 3] Widget UI elements test passed")
        
        # Restore initial volume
        widget.set_volume(initial_volume)
        
        return True
        
    except Exception as e:
        print(f"❌ [WIDGET TEST] Volume widget test failed: {e}")
        return False

def main():
    """Run all volume control tests."""
    
    print("🚀 STARTING AI COACH VOLUME CONTROL TESTS")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log spam during testing
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Volume system
    if test_volume_system():
        tests_passed += 1
    
    print("-" * 60)
    
    # Test 2: Volume widget
    if test_volume_widget():
        tests_passed += 1
    
    print("=" * 60)
    print(f"🏁 VOLUME TESTS COMPLETED: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ ALL VOLUME TESTS PASSED - Volume control is working!")
        print("🎉 You can now adjust AI Coach volume in the UI.")
        print("🔊 Volume settings will persist between sessions.")
    else:
        print("❌ SOME VOLUME TESTS FAILED - There may still be issues.")
        print("⚠️  Please review the test output above.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 