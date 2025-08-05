#!/usr/bin/env python3
"""
Check authentication status to see if Lawrence is properly logged in.
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

def check_auth_status():
    """Check the current authentication status."""
    try:
        from trackpro.auth.user_manager import get_current_user
        from trackpro.database.supabase_client import get_supabase_client
        
        logger.info("🔍 Checking Authentication Status...")
        
        # Check current user
        user = get_current_user()
        if user and user.is_authenticated:
            logger.info(f"✅ Current User: {user.name or user.email} (ID: {user.id})")
            logger.info(f"   Email: {user.email}")
            logger.info(f"   Name: {user.name}")
            logger.info(f"   ID: {user.id}")
        else:
            logger.warning("⚠️ No authenticated user found")
        
        # Check Supabase session
        client = get_supabase_client()
        if client:
            try:
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    user_data = session.user
                    logger.info(f"✅ Supabase Session User: {user_data.user_metadata.get('name', user_data.email)}")
                    logger.info(f"   Email: {user_data.email}")
                    logger.info(f"   ID: {user_data.id}")
                    logger.info(f"   Metadata: {user_data.user_metadata}")
                else:
                    logger.warning("⚠️ No Supabase session found")
            except Exception as e:
                logger.error(f"❌ Error getting Supabase session: {e}")
        
        # Check if Lawrence's user ID matches any messages
        if user and user.is_authenticated:
            from trackpro.community.community_manager import CommunityManager
            community_manager = CommunityManager()
            
            # Get messages and check if Lawrence's ID appears
            channels = community_manager.get_channels()
            if channels:
                first_channel = channels[0]['channel_id']
                messages = community_manager.get_messages(first_channel, limit=5)
                
                logger.info(f"\n📨 Checking if Lawrence's ID ({user.id}) appears in messages:")
                found_lawrence_messages = False
                for message in messages:
                    sender_id = message.get('sender_id')
                    sender_name = message.get('sender_name', 'NOT_FOUND')
                    content = message.get('content', '')[:30]
                    
                    if sender_id == user.id:
                        logger.info(f"  ✅ Found Lawrence's message: {content}... (Name: {sender_name})")
                        found_lawrence_messages = True
                    else:
                        logger.info(f"  ℹ️ Other user message: {content}... (ID: {sender_id}, Name: {sender_name})")
                
                if not found_lawrence_messages:
                    logger.warning("⚠️ No messages found from Lawrence's user ID")
        
    except Exception as e:
        logger.error(f"❌ Error checking auth status: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("🚀 Checking Authentication Status...")
    check_auth_status()
    logger.info("✅ Check completed") 