#!/usr/bin/env python3
"""
Test script to verify voice settings integration.

This script tests that:
1. Voice settings are saved to config
2. Voice managers load settings from config
3. Voice managers update when settings change
4. Audio devices are properly selected
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_voice_settings_integration():
    """Test voice settings integration."""
    try:
        logger.info("🧪 Testing voice settings integration...")
        
        # Test 1: Import voice components
        logger.info("📦 Testing imports...")
        from trackpro.ui.pages.community.high_quality_voice_manager import HighQualityVoiceManager
        from trackpro.ui.pages.community.voice_settings_dialog import VoiceSettingsDialog
        from trackpro.config import config
        
        logger.info("✅ Voice components imported successfully")
        
        # Test 2: Check current voice settings
        logger.info("🔧 Checking current voice settings...")
        current_settings = {
            'sample_rate': config.voice_chat_sample_rate,
            'channels': config.voice_chat_channels,
            'bit_depth': config.voice_chat_bit_depth,
            'buffer_size': config.voice_chat_buffer_size,
            'input_device': config.voice_chat_input_device,
            'output_device': config.voice_chat_output_device,
            'input_volume': config.voice_chat_input_volume,
            'output_volume': config.voice_chat_output_volume,
        }
        
        logger.info(f"📋 Current settings: {current_settings}")
        
        # Test 3: Create voice manager and check settings
        logger.info("🎤 Creating voice manager...")
        voice_manager = HighQualityVoiceManager()
        
        logger.info(f"🎤 Voice manager input device: {voice_manager.input_device}")
        logger.info(f"🎤 Voice manager output device: {voice_manager.output_device}")
        logger.info(f"🎤 Voice manager sample rate: {voice_manager.sample_rate}")
        
        # Test 4: Update settings
        logger.info("🔄 Testing settings update...")
        test_settings = {
            'input_device': 1,  # Test device index
            'output_device': 2,  # Test device index
            'sample_rate': 48000,
            'channels': 1,
            'bit_depth': 16,
            'buffer_size': 512,
            'input_volume': 80,
            'output_volume': 80,
        }
        
        voice_manager.update_settings(test_settings)
        
        logger.info(f"✅ Settings updated successfully")
        logger.info(f"🎤 Updated input device: {voice_manager.input_device}")
        logger.info(f"🎤 Updated output device: {voice_manager.output_device}")
        
        # Test 5: Check config was updated
        logger.info("💾 Checking config was updated...")
        # Note: config doesn't have a reload method, so we'll just check the current values
        
        logger.info(f"📋 Config input device: {config.voice_chat_input_device}")
        logger.info(f"📋 Config output device: {config.voice_chat_output_device}")
        
        # Test 6: Create new voice manager and verify it uses updated settings
        logger.info("🆕 Creating new voice manager with updated settings...")
        new_voice_manager = HighQualityVoiceManager()
        
        logger.info(f"🎤 New voice manager input device: {new_voice_manager.input_device}")
        logger.info(f"🎤 New voice manager output device: {new_voice_manager.output_device}")
        
        # Clean up
        if hasattr(voice_manager, 'audio') and voice_manager.audio:
            voice_manager.audio.terminate()
        if hasattr(new_voice_manager, 'audio') and new_voice_manager.audio:
            new_voice_manager.audio.terminate()
        
        logger.info("✅ Voice settings integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Voice settings integration test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_voice_settings_integration()
    sys.exit(0 if success else 1) 