#!/usr/bin/env python
"""
Simple Community Message Test

This script tests the basic community message functionality.
"""

import sys
import os
import logging

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import get_supabase_client
from trackpro.auth.user_manager import get_current_user
from trackpro.community.community_manager import CommunityManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_message():
    """Test simple message sending."""
    try:
        # Get Supabase client
        client = get_supabase_client()
        if not client:
            logger.error("❌ Failed to get Supabase client")
            return False
        
        # Get current user
        user = get_current_user()
        if not user or not user.is_authenticated:
            logger.error("❌ No authenticated user found")
            return False
        
        logger.info(f"✅ Authenticated user: {user.name} ({user.id})")
        
        # Initialize community manager
        community_manager = CommunityManager()
        community_manager.set_current_user(user.id)
        logger.info("✅ Community manager initialized")
        
        # Get channels
        channels = community_manager.get_channels()
        logger.info(f"✅ Found {len(channels)} channels")
        
        # Find general channel
        general_channel = None
        for channel in channels:
            if channel['name'] == 'general':
                general_channel = channel
                break
        
        if not general_channel:
            logger.error("❌ General channel not found")
            return False
        
        logger.info(f"✅ Found general channel: {general_channel['channel_id']}")
        
        # Send test message
        test_message = "Test message from simple test script"
        success = community_manager.send_message(
            channel_id=general_channel['channel_id'],
            content=test_message
        )
        
        if success:
            logger.info("✅ Message sent successfully!")
            
            # Get messages to verify
            messages = community_manager.get_messages(general_channel['channel_id'])
            logger.info(f"✅ Retrieved {len(messages)} messages")
            
            # Check if our message is there
            test_message_found = any(msg['content'] == test_message for msg in messages)
            if test_message_found:
                logger.info("✅ Test message found in database!")
                return True
            else:
                logger.warning("⚠️ Test message not found in retrieved messages")
                return False
        else:
            logger.error("❌ Failed to send message")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in simple test: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("🧪 Starting simple community message test...")
    
    if test_simple_message():
        logger.info("✅ Simple test passed!")
    else:
        logger.error("❌ Simple test failed!")
        sys.exit(1) 