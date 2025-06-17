#!/usr/bin/env python3
"""
AI Coach Diagnostic Tool for TrackPro

This script helps diagnose issues with the AI voice coaching system.
Run this to check:
- API key configuration (OpenAI & ElevenLabs)
- Audio system functionality
- Telemetry data availability
- Superlap data accessibility
- Required dependencies

Usage: python diagnose_ai_coach.py [superlap_id]
"""

import os
import sys
import logging
import traceback
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_check(name, status, details=""):
    """Print a formatted check result."""
    status_icon = "✅" if status else "❌"
    print(f"{status_icon} {name}")
    if details:
        print(f"   {details}")

def check_environment_variables():
    """Check for required environment variables."""
    print_section("Environment Variables")
    
    # Check OpenAI API Key
    openai_key = os.getenv("OPENAI_API_KEY")
    print_check(
        "OpenAI API Key", 
        bool(openai_key),
        f"Found: {'Yes' if openai_key else 'No'}" + 
        (f" (Length: {len(openai_key)} chars)" if openai_key else "")
    )
    
    # Check ElevenLabs API Key
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    print_check(
        "ElevenLabs API Key", 
        bool(elevenlabs_key),
        f"Found: {'Yes' if elevenlabs_key else 'No'}" + 
        (f" (Length: {len(elevenlabs_key)} chars)" if elevenlabs_key else "")
    )
    
    return bool(openai_key and elevenlabs_key)

def check_dependencies():
    """Check for required Python dependencies."""
    print_section("Python Dependencies")
    
    dependencies = {
        'openai': 'OpenAI API client',
        'elevenlabs': 'ElevenLabs TTS client', 
        'pygame': 'Audio playback system',
        'sounddevice': 'Audio device interface',
        'soundfile': 'Audio file handling'
    }
    
    all_good = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print_check(module, True, description)
        except ImportError as e:
            print_check(module, False, f"{description} - Import Error: {e}")
            all_good = False
    
    return all_good

def test_audio_system():
    """Test audio system functionality."""
    print_section("Audio System Test")
    
    try:
        import pygame
        pygame.mixer.init()
        print_check("Pygame Mixer", True, "Initialized successfully")
        
        # Test basic audio capabilities
        try:
            # Create a simple beep for testing
            import numpy as np
            import tempfile
            import wave
            
            # Generate a 440Hz tone for 0.5 seconds
            sample_rate = 22050
            duration = 0.5
            frequency = 440
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_data = np.sin(2 * np.pi * frequency * t)
            audio_data = (audio_data * 32767).astype(np.int16)
            
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_wav_path = tmp_file.name
                
            with wave.open(temp_wav_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            # Test playback
            print("🔊 Testing audio playback (you should hear a short beep)...")
            pygame.mixer.music.load(temp_wav_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            import time
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            pygame.mixer.quit()
            os.unlink(temp_wav_path)
            
            print_check("Audio Playback Test", True, "Test tone played successfully")
            return True
            
        except Exception as e:
            print_check("Audio Playback Test", False, f"Error: {e}")
            return False
            
    except ImportError:
        print_check("Pygame", False, "Module not available")
        return False
    except Exception as e:
        print_check("Audio System", False, f"Error: {e}")
        return False

def test_openai_api():
    """Test OpenAI API connectivity."""
    print_section("OpenAI API Test")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print_check("API Connectivity", False, "No API key provided")
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a cheaper model for testing
            messages=[{"role": "user", "content": "Say 'API test successful'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print_check("OpenAI API", True, f"Response: {result}")
        return True
        
    except Exception as e:
        print_check("OpenAI API", False, f"Error: {e}")
        return False

def test_elevenlabs_api():
    """Test ElevenLabs API connectivity."""
    print_section("ElevenLabs API Test")
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print_check("API Connectivity", False, "No API key provided")
        return False
    
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        
        # Test with a simple TTS generation
        print("🎙️ Testing text-to-speech generation...")
        audio_generator = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice
            output_format="mp3_22050_32",
            text="API test successful",
            model_id="eleven_turbo_v2",
        )
        
        # Try to get the first chunk
        first_chunk = next(audio_generator)
        print_check("ElevenLabs API", True, f"Generated audio chunk ({len(first_chunk)} bytes)")
        return True
        
    except Exception as e:
        print_check("ElevenLabs API", False, f"Error: {e}")
        return False

def test_superlap_data(superlap_id=None):
    """Test superlap data accessibility."""
    print_section("Superlap Data Test")
    
    if not superlap_id:
        print_check("Superlap ID", False, "No superlap ID provided")
        return False
    
    try:
        # Try to import the database function
        sys.path.append(str(Path(__file__).parent))
        from Supabase.database import get_super_lap_telemetry_points
        
        print(f"🔍 Testing superlap data for ID: {superlap_id}")
        points, message = get_super_lap_telemetry_points(superlap_id)
        
        if points:
            print_check("Superlap Data", True, f"Found {len(points)} telemetry points")
            
            # Check data quality
            if len(points) > 0:
                sample_point = points[0]
                required_fields = ['track_position', 'speed', 'throttle', 'brake', 'steering']
                missing_fields = [field for field in required_fields if field not in sample_point]
                
                if missing_fields:
                    print_check("Data Quality", False, f"Missing fields: {missing_fields}")
                else:
                    print_check("Data Quality", True, "All required fields present")
            
            return True
        else:
            print_check("Superlap Data", False, f"No data found: {message}")
            return False
            
    except ImportError as e:
        print_check("Database Access", False, f"Cannot import database module: {e}")
        return False
    except Exception as e:
        print_check("Superlap Data", False, f"Error: {e}")
        return False

def test_ai_coach_integration(superlap_id=None):
    """Test the full AI coach integration."""
    print_section("AI Coach Integration Test")
    
    if not superlap_id:
        print_check("Integration Test", False, "No superlap ID provided for testing")
        return False
    
    try:
        # Import AI coach components
        sys.path.append(str(Path(__file__).parent / "trackpro" / "race_coach"))
        from ai_coach.ai_coach import AICoach
        
        print(f"🤖 Initializing AI Coach with superlap ID: {superlap_id}")
        coach = AICoach(superlap_id=superlap_id, advice_interval=1.0)
        
        # Test with mock telemetry
        mock_telemetry = {
            'track_position': 0.1,
            'speed': 150.0,
            'throttle': 0.8,
            'brake': 0.0,
            'steering': 0.05
        }
        
        print("🏁 Testing telemetry processing...")
        coach.process_realtime_telemetry(mock_telemetry)
        
        print_check("AI Coach Integration", True, "Successfully processed telemetry")
        return True
        
    except Exception as e:
        print_check("AI Coach Integration", False, f"Error: {e}")
        traceback.print_exc()
        return False

def provide_recommendations():
    """Provide recommendations based on test results."""
    print_section("Recommendations")
    
    print("📋 Based on the diagnostic results above, here are the steps to fix issues:")
    print()
    
    print("1. 🔑 Set up API Keys (if missing):")
    print("   - Get OpenAI API key from: https://platform.openai.com/api-keys")
    print("   - Get ElevenLabs API key from: https://elevenlabs.io/app/settings/api-keys")
    print("   - Set environment variables:")
    print("     Windows: setx OPENAI_API_KEY \"your_key_here\"")
    print("     Windows: setx ELEVENLABS_API_KEY \"your_key_here\"")
    print("   - Restart TrackPro after setting environment variables")
    print()
    
    print("2. 📦 Install missing dependencies:")
    print("   pip install openai elevenlabs pygame sounddevice soundfile")
    print()
    
    print("3. 🔊 Audio issues:")
    print("   - Check Windows audio settings")
    print("   - Ensure default audio device is working")
    print("   - Try running TrackPro as administrator")
    print()
    
    print("4. 🏁 Superlap issues:")
    print("   - Verify the superlap ID is correct")
    print("   - Check that the superlap has telemetry data")
    print("   - Try creating a new superlap if the current one is corrupted")
    print()
    
    print("5. 🔌 iRacing connection:")
    print("   - Make sure iRacing is running and in a session")
    print("   - Check that telemetry is enabled in iRacing settings")
    print("   - Verify TrackPro is receiving live telemetry data")

def main():
    """Main diagnostic function."""
    print("🔧 TrackPro AI Coach Diagnostic Tool")
    print("="*60)
    
    # Get superlap ID from command line if provided
    superlap_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Run all diagnostic tests
    env_ok = check_environment_variables()
    deps_ok = check_dependencies()
    audio_ok = test_audio_system()
    openai_ok = test_openai_api() if env_ok else False
    elevenlabs_ok = test_elevenlabs_api() if env_ok else False
    superlap_ok = test_superlap_data(superlap_id) if superlap_id else True
    integration_ok = test_ai_coach_integration(superlap_id) if (env_ok and superlap_id) else False
    
    # Summary
    print_section("Summary")
    all_tests = [env_ok, deps_ok, audio_ok, openai_ok, elevenlabs_ok, superlap_ok, integration_ok]
    passed_tests = sum(all_tests)
    total_tests = len([t for t in all_tests if t is not None])
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! AI Coach should be working properly.")
    else:
        print(f"⚠️  {passed_tests}/{total_tests} tests passed. See recommendations below.")
    
    provide_recommendations()
    
    print(f"\n🔧 To run this diagnostic with a specific superlap ID:")
    print(f"   python diagnose_ai_coach.py YOUR_SUPERLAP_ID")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Diagnostic cancelled by user")
    except Exception as e:
        print(f"\n❌ Diagnostic script error: {e}")
        traceback.print_exc() 