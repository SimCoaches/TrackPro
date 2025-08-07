#!/usr/bin/env python3
"""
Test script to debug user profile fetching in community manager.
"""

import sys
import os
import logging
import os as _os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Ensure headless-friendly Qt setup for QPixmap usage in tests
# Keep a strong reference to the QApplication to avoid GC during the test run
QT_APP = None
try:
    if not _os.environ.get("QT_QPA_PLATFORM"):
        _os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt6.QtWidgets import QApplication as _QApplication
    _existing = _QApplication.instance()
    if _existing is None:
        QT_APP = _QApplication([])
    else:
        QT_APP = _existing
except Exception:
    pass

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

def _ensure_qapp():
    try:
        from PyQt6.QtWidgets import QApplication
        import sys
        global QT_APP
        app = QApplication.instance()
        if app is None:
            QT_APP = QApplication(sys.argv)
        else:
            QT_APP = app
    except Exception:
        pass


def test_avatar_bucket_and_users():
    """Validate avatars bucket access and avatar URLs for known users."""
    from trackpro.database.supabase_client import get_supabase_client
    from trackpro.ui.avatar_manager import AvatarManager
    import requests

    _ensure_qapp()

    client = get_supabase_client()
    if not client:
        logger.error("❌ No Supabase client available")
        return

    # Bucket accessible
    try:
        files = client.storage.from_("avatars").list()
        logger.info(f"✅ Avatars bucket accessible, {len(files)} items listed")
    except Exception as e:
        logger.error(f"❌ Cannot access avatars bucket: {e}")

    # Known users to check
    candidates = [
        {"email": "lawrence@simcoaches.com", "username": "lawrence"},
        {"email": None, "username": "keepkonraddrifting"},
    ]

    for c in candidates:
        profile = None
        try:
            if c["email"]:
                resp = client.table("user_profiles").select(
                    "user_id, username, display_name, avatar_url, email"
                ).eq("email", c["email"]).single().execute()
                profile = resp.data
            if not profile and c["username"]:
                resp = client.table("user_profiles").select(
                    "user_id, username, display_name, avatar_url"
                ).eq("username", c["username"]).single().execute()
                profile = resp.data
        except Exception as e:
            logger.warning(f"Lookup failed for {c}: {e}")

        if not profile:
            logger.warning(f"⚠️ No profile found for {c}")
            continue

        logger.info(f"👤 Found profile: {profile}")
        url = profile.get("avatar_url")
        if not url:
            logger.warning("❌ avatar_url is empty")
            continue

        # URL responds
        try:
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                logger.error(f"❌ Avatar URL not reachable: HTTP {r.status_code}")
            else:
                logger.info("✅ Avatar URL reachable")
        except Exception as e:
            logger.error(f"❌ Error fetching avatar URL: {e}")

        # Loads into pixmap via manager cache path
        try:
            pix = AvatarManager.instance().get_cached_pixmap(url, profile.get("display_name") or profile.get("username") or "User", size=64)
            if pix is None or pix.isNull():
                logger.error("❌ Pixmap failed to load from avatar URL")
            else:
                logger.info("✅ Pixmap loaded from avatar URL or fallback")
        except Exception as e:
            logger.error(f"❌ Error creating pixmap: {e}")


def test_avatar_manager_invalid_url_fallback():
    """Ensure invalid URLs do not crash and fallback initials are used."""
    from trackpro.ui.avatar_manager import AvatarManager

    _ensure_qapp()
    pix = AvatarManager.instance().get_cached_pixmap("https://invalid.invalid/nope.png", "Test User", size=48)
    if pix is None or pix.isNull():
        logger.error("❌ Fallback pixmap was null for invalid URL")
    else:
        logger.info("✅ Fallback pixmap generated for invalid URL")


if __name__ == "__main__":
    # Force UTF-8 to avoid console encoding issues on Windows
    try:
        import os
        os.environ["PYTHONIOENCODING"] = "utf-8"
    except Exception:
        pass

    logger.info("Starting profile and avatar tests...")
    test_user_profile_fetching()
    logger.info("Testing Avatars bucket and known users...")
    test_avatar_bucket_and_users()
    logger.info("Testing AvatarManager invalid URL fallback...")
    test_avatar_manager_invalid_url_fallback()
    logger.info("Tests completed.")