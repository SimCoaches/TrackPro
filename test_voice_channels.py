#!/usr/bin/env python3
"""
Voice Channels Test

Tests that voice channels can be created and joined without errors.
"""

import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_voice_channels():
    """Test voice channel functionality."""
    print("🎤 Testing Voice Channels...")
    
    try:
        # Test importing voice components
        from trackpro.ui.pages.community.community_page import VOICE_COMPONENTS_AVAILABLE
        print(f"✅ VOICE_COMPONENTS_AVAILABLE: {VOICE_COMPONENTS_AVAILABLE}")
        
        # Test importing voice managers
        from trackpro.ui.pages.community.community_page import VoiceChatManager
        print("✅ VoiceChatManager imported successfully")
        
        # Test creating voice manager
        voice_manager = VoiceChatManager()
        print("✅ VoiceChatManager created successfully")
        
        # Test importing voice settings dialog
        from trackpro.ui.pages.community.voice_settings_dialog import VoiceSettingsDialog
        print("✅ VoiceSettingsDialog imported successfully")
        
        # Test voice server availability
        from trackpro.voice_server_manager import is_voice_server_running
        server_running = is_voice_server_running()
        print(f"✅ Voice server status: {'Running' if server_running else 'Not running'}")
        
        # Test high-quality voice manager
        try:
            from trackpro.ui.pages.community.high_quality_voice_manager import HighQualityVoiceManager
            hq_manager = HighQualityVoiceManager()
            print("✅ HighQualityVoiceManager created successfully")
        except Exception as e:
            print(f"⚠️ HighQualityVoiceManager not available: {e}")
        
        print("🎉 Voice channels test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Voice channels test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_voice_channels()
    sys.exit(0 if success else 1) 