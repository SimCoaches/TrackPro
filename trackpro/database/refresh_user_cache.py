#!/usr/bin/env python
"""
Refresh User Cache

This script forces a refresh of the current user's cached data to show updated hierarchy levels.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import required modules
from trackpro.auth.user_manager import logout_current_user, get_current_user
from trackpro.database.supabase_client import supabase

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def refresh_user_cache():
    """Force refresh the current user's cached data."""
    
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        logger.info("Refreshing user cache...")
        
        # Get current user before clearing cache
        old_user = get_current_user()
        if old_user:
            logger.info(f"Current user before refresh: {old_user.email} (Level: {old_user.hierarchy_level})")
        
        # Clear the user cache
        logout_current_user()
        logger.info("Cleared user cache")
        
        # Force a new session check
        try:
            # This will trigger a fresh authentication check
            session = supabase.client.auth.get_session()
            if session and session.user:
                logger.info("Session refreshed successfully")
            else:
                logger.warning("No active session found")
        except Exception as e:
            logger.warning(f"Session refresh warning: {e}")
        
        # Get current user after clearing cache
        new_user = get_current_user()
        if new_user:
            logger.info(f"Current user after refresh: {new_user.email} (Level: {new_user.hierarchy_level})")
            logger.info(f"Dev permissions: {new_user.is_dev}")
            logger.info(f"Moderator permissions: {new_user.is_moderator}")
            
            if new_user.hierarchy_level == "TEAM":
                logger.info("✅ Successfully refreshed to TEAM level!")
                return True
            else:
                logger.warning(f"⚠️ Still showing {new_user.hierarchy_level} level")
                return False
        else:
            logger.error("Failed to get current user after refresh")
            return False
        
    except Exception as e:
        logger.error(f"Failed to refresh user cache: {e}")
        return False

def main():
    """Main function to refresh user cache."""
    logger.info("Starting user cache refresh")
    
    success = refresh_user_cache()
    
    if success:
        logger.info("User cache refresh completed successfully!")
        logger.info("You should now see TEAM level in the UI.")
        logger.info("If you're still seeing PADDOCK, try restarting the app.")
        return 0
    else:
        logger.error("User cache refresh failed!")
        logger.info("Try logging out and logging back in to see the changes.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 