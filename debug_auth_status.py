#!/usr/bin/env python3
"""
Debug script to check and fix authentication status in TrackPro community chat.
"""

import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_auth_status():
    """Check the current authentication status."""
    logger.info("🔍 Checking authentication status...")
    
    try:
        # Check Supabase client
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if client:
            logger.info("✅ Supabase client available")
            
            # Check session
            try:
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    logger.info(f"✅ Supabase session found - User: {session.user.email}")
                    return True
                else:
                    logger.warning("❌ No valid Supabase session found")
            except Exception as e:
                logger.error(f"❌ Error checking Supabase session: {e}")
        else:
            logger.warning("❌ Supabase client not available")
        
        # Check user manager
        try:
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            
            if user and user.is_authenticated:
                logger.info(f"✅ User manager shows authenticated: {user.email}")
                return True
            else:
                logger.warning("❌ User manager shows not authenticated")
        except Exception as e:
            logger.error(f"❌ Error checking user manager: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking authentication: {e}")
        return False

def force_auth_refresh():
    """Force refresh the authentication state."""
    logger.info("🔄 Forcing authentication refresh...")
    
    try:
        # Clear the global user cache
        from trackpro.auth.user_manager import _current_user
        import trackpro.auth.user_manager
        
        # Clear the cached user
        trackpro.auth.user_manager._current_user = None
        logger.info("✅ Cleared user manager cache")
        
        # Force Supabase client refresh
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if client:
            # Try to get fresh session
            try:
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    logger.info(f"✅ Fresh Supabase session: {session.user.email}")
                    
                    # Force user manager to create new user object
                    from trackpro.auth.user_manager import get_current_user
                    user = get_current_user()
                    
                    if user and user.is_authenticated:
                        logger.info(f"✅ User manager refreshed: {user.email}")
                        return True
                    else:
                        logger.warning("❌ User manager still not authenticated after refresh")
                else:
                    logger.warning("❌ No fresh Supabase session available")
            except Exception as e:
                logger.error(f"❌ Error refreshing Supabase session: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error forcing auth refresh: {e}")
        return False

def main():
    """Main function to debug and fix authentication."""
    print("🔧 TrackPro Community Authentication Debug Tool")
    print("=" * 50)
    
    # Check current status
    print("\n1. Checking current authentication status...")
    is_authenticated = check_auth_status()
    
    if is_authenticated:
        print("✅ You appear to be authenticated!")
        print("💡 If the community chat still shows 'Please log in', try refreshing the page.")
    else:
        print("❌ You appear to not be authenticated.")
        print("\n2. Attempting to force authentication refresh...")
        
        if force_auth_refresh():
            print("✅ Authentication refresh successful!")
            print("💡 Try accessing the community chat again.")
        else:
            print("❌ Authentication refresh failed.")
            print("💡 You may need to log in again through the main application.")
    
    print("\n" + "=" * 50)
    print("🔧 Debug complete!")

if __name__ == "__main__":
    main() 