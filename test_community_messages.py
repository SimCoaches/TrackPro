#!/usr/bin/env python
"""
Test Community Message Functionality

This script tests the community message sending functionality to ensure it works correctly.
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

def test_community_messages():
    """Test community message functionality."""
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
        if not community_manager:
            logger.error("❌ Failed to initialize community manager")
            return False
        
        # Set current user
        community_manager.set_current_user(user.id)
        logger.info("✅ Community manager initialized with current user")
        
        # Test getting channels
        channels = community_manager.get_channels()
        logger.info(f"✅ Found {len(channels)} channels: {[c['name'] for c in channels]}")
        
        # Test sending a message to the general channel
        general_channel = None
        for channel in channels:
            if channel['name'] == 'general':
                general_channel = channel
                break
        
        if not general_channel:
            logger.error("❌ General channel not found")
            return False
        
        logger.info(f"✅ Found general channel: {general_channel['channel_id']}")
        
        # Test sending a message
        test_message = "Test message from automated test script"
        result = community_manager.send_message(
            channel_id=general_channel['channel_id'],
            content=test_message,
            user_id=user.id
        )
        
        if result:
            logger.info("✅ Message sent successfully!")
            
            # Test getting messages
            messages = community_manager.get_messages(general_channel['channel_id'])
            logger.info(f"✅ Retrieved {len(messages)} messages from general channel")
            
            # Check if our test message is there
            test_message_found = any(msg['content'] == test_message for msg in messages)
            if test_message_found:
                logger.info("✅ Test message found in channel messages")
            else:
                logger.warning("⚠️ Test message not found in retrieved messages")
            
            return True
        else:
            logger.error("❌ Failed to send message")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing community messages: {e}")
        return False

def test_database_connection():
    """Test database connection and table existence."""
    try:
        client = get_supabase_client()
        if not client:
            logger.error("❌ Failed to get Supabase client")
            return False
        
        # Test querying community tables
        result = client.table('community_channels').select('*').execute()
        logger.info(f"✅ Community channels table accessible: {len(result.data)} channels")
        
        result = client.table('community_messages').select('*').execute()
        logger.info(f"✅ Community messages table accessible: {len(result.data)} messages")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🧪 Starting community message tests...")
    
    # Test database connection
    if not test_database_connection():
        logger.error("❌ Database connection test failed")
        sys.exit(1)
    
    # Test community messages
    if test_community_messages():
        logger.info("✅ All community message tests passed!")
    else:
        logger.error("❌ Community message tests failed")
        sys.exit(1) 