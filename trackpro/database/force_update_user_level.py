#!/usr/bin/env python
"""
Force Update User Level

This script directly forces the current user's level to TEAM in the cache.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import required modules
from trackpro.auth.user_manager import get_current_user, set_current_user
from trackpro.auth.user_manager import User
from trackpro.database.supabase_client import supabase

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def force_update_user_level():
    """Force update the current user's level to TEAM."""
    
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        logger.info("Forcing user level update...")
        
        # Get current user
        current_user = get_current_user()
        if not current_user:
            logger.error("No current user found!")
            return False
        
        logger.info(f"Current user: {current_user.email} (Level: {current_user.hierarchy_level})")
        
        # Create a new user object with TEAM level
        updated_user = User(
            id=current_user.id,
            email=current_user.email,
            name=current_user.name,
            is_authenticated=True,
            hierarchy_level="TEAM",
            is_dev=True,
            is_moderator=True
        )
        
        # Set the updated user
        set_current_user(updated_user)
        
        # Verify the update
        new_user = get_current_user()
        if new_user:
            logger.info(f"Updated user: {new_user.email} (Level: {new_user.hierarchy_level})")
            logger.info(f"Dev permissions: {new_user.is_dev}")
            logger.info(f"Moderator permissions: {new_user.is_moderator}")
            
            if new_user.hierarchy_level == "TEAM":
                logger.info("✅ Successfully updated to TEAM level!")
                return True
            else:
                logger.warning(f"⚠️ Still showing {new_user.hierarchy_level} level")
                return False
        else:
            logger.error("Failed to get updated user")
            return False
        
    except Exception as e:
        logger.error(f"Failed to update user level: {e}")
        return False

def main():
    """Main function to force update user level."""
    logger.info("Starting force user level update")
    
    success = force_update_user_level()
    
    if success:
        logger.info("User level update completed successfully!")
        logger.info("You should now see TEAM level in the UI.")
        logger.info("Try refreshing the account page in TrackPro.")
        return 0
    else:
        logger.error("User level update failed!")
        logger.info("Try restarting the TrackPro app.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 