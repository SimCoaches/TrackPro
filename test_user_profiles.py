#!/usr/bin/env python3
"""
Test script to debug user profile fetching in community manager.
"""

import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_user_profile_fetching():
    """Test user profile fetching directly."""
    try:
        from trackpro.database.supabase_client import get_supabase_client
        
        logger.info("🧪 Testing User Profile Fetching...")
        
        # Get Supabase client
        client = get_supabase_client()
        if not client:
            logger.error("❌ No Supabase client available")
            return
        
        # Test the exact query that the community manager uses
        sender_ids = ['051109b4-6d3a-423c-92ff-437f10b8233a', 'a75dafb2-f1d3-4ff5-83e2-fd19e64f2c62']
        
        logger.info(f"🔍 Testing user profile fetch for sender IDs: {sender_ids}")
        
        try:
            user_response = client.table("user_profiles").select(
                "user_id, username, display_name, avatar_url"
            ).in_("user_id", sender_ids).execute()
            
            users = {user['user_id']: user for user in (user_response.data or [])}
            logger.info(f"✅ Retrieved {len(users)} user profiles: {list(users.keys())}")
            
            for user_id, user_data in users.items():
                logger.info(f"  👤 {user_id}: {user_data}")
                
                # Test the sender_name logic
                sender_name = user_data.get('display_name') or user_data.get('username') or 'Unknown'
                logger.info(f"     sender_name = {sender_name}")
                
        except Exception as e:
            logger.error(f"❌ Error fetching user profiles: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Test the community manager directly
        logger.info("\n🧪 Testing Community Manager...")
        from trackpro.community.community_manager import CommunityManager
        
        community_manager = CommunityManager()
        
        # Get messages from the first channel
        channels = community_manager.get_channels()
        if channels:
            first_channel = channels[0]['channel_id']
            logger.info(f"📋 Testing with channel: {first_channel}")
            
            messages = community_manager.get_messages(first_channel, limit=5)
            logger.info(f"📨 Retrieved {len(messages)} messages")
            
            for message in messages:
                message_id = message.get('message_id', 'unknown')
                sender_id = message.get('sender_id', 'unknown')
                sender_name = message.get('sender_name', 'NOT_FOUND')
                content = message.get('content', '')[:30]
                
                logger.info(f"  📝 Message {message_id}:")
                logger.info(f"     sender_id: {sender_id}")
                logger.info(f"     sender_name: {sender_name}")
                logger.info(f"     content: {content}...")
                
                if 'user_profiles' in message:
                    user_profile = message['user_profiles']
                    logger.info(f"     user_profile: {user_profile}")
                else:
                    logger.warning(f"     ⚠️ No user_profile found!")
        
    except Exception as e:
        logger.error(f"❌ Error in test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("🚀 Testing User Profile Fetching...")
    test_user_profile_fetching()
    logger.info("✅ Test completed") 