#!/usr/bin/env python3
"""
Investigate why other users show as Unknown while Lawrence shows correctly.
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

def investigate_user_messages():
    """Investigate all messages and their sender information."""
    try:
        from trackpro.community.community_manager import CommunityManager
        from trackpro.database.supabase_client import get_supabase_client
        
        logger.info("🔍 Investigating User Messages...")
        
        # Get community manager
        community_manager = CommunityManager()
        
        # Get all channels
        channels = community_manager.get_channels()
        logger.info(f"✅ Found {len(channels)} channels")
        
        # Check each channel for messages
        for channel in channels:
            channel_id = channel['channel_id']
            channel_name = channel['name']
            
            logger.info(f"\n📋 Channel: {channel_name} ({channel_id})")
            
            # Get messages for this channel
            messages = community_manager.get_messages(channel_id, limit=10)
            logger.info(f"  Found {len(messages)} messages")
            
            # Group messages by sender
            sender_messages = {}
            for message in messages:
                sender_id = message.get('sender_id')
                sender_name = message.get('sender_name', 'NOT_FOUND')
                content = message.get('content', '')[:50]
                
                if sender_id not in sender_messages:
                    sender_messages[sender_id] = {
                        'name': sender_name,
                        'count': 0,
                        'sample_content': content
                    }
                sender_messages[sender_id]['count'] += 1
            
            # Report on each sender
            for sender_id, info in sender_messages.items():
                logger.info(f"  👤 Sender ID: {sender_id}")
                logger.info(f"     Name: {info['name']}")
                logger.info(f"     Message Count: {info['count']}")
                logger.info(f"     Sample: {info['sample_content']}...")
                
                if info['name'] == 'Unknown':
                    logger.warning(f"     ⚠️ This sender shows as Unknown!")
                elif info['name'] == 'Lawrence Thomas':
                    logger.info(f"     ✅ This is Lawrence's messages")
                else:
                    logger.info(f"     ℹ️ This is another user: {info['name']}")
        
        # Check current user
        try:
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            if user and user.is_authenticated:
                logger.info(f"\n👤 Current User: {user.name or user.email} (ID: {user.id})")
            else:
                logger.warning("⚠️ No authenticated user found")
        except Exception as e:
            logger.error(f"❌ Error getting current user: {e}")
        
        # Check database for user profiles
        client = get_supabase_client()
        if client:
            try:
                response = client.table("user_profiles").select("user_id, username, display_name").limit(10).execute()
                logger.info(f"\n📊 User Profiles in Database: {len(response.data)}")
                for profile in response.data:
                    logger.info(f"  - {profile.get('display_name', profile.get('username', 'Unknown'))} (ID: {profile.get('user_id')})")
            except Exception as e:
                logger.error(f"❌ Error querying user profiles: {e}")
        
    except Exception as e:
        logger.error(f"❌ Error investigating messages: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("🚀 Investigating User Messages...")
    investigate_user_messages()
    logger.info("✅ Investigation completed") 