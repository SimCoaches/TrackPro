#!/usr/bin/env python
"""
Update Lawrence to TEAM Level (Direct Method)

This script directly updates lawrence@simcoaches.com to TEAM hierarchy level using table operations.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import required modules
from trackpro.database.supabase_client import supabase
from trackpro.auth.hierarchy_manager import HierarchyLevel

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_lawrence_to_team():
    """Update Lawrence's account to TEAM level using direct table operations."""
    
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        logger.info("Updating Lawrence to TEAM level...")
        
        # First, get Lawrence's user ID from auth.users
        auth_result = supabase.client.auth.get_user()
        if not auth_result.user:
            logger.error("No authenticated user found!")
            return False
        
        user_id = auth_result.user.id
        logger.info(f"Found Lawrence's user ID: {user_id}")
        
        # Update to TEAM level with full permissions using direct table operations
        update_data = {
            "hierarchy_level": "TEAM",
            "is_dev": True,
            "is_moderator": True,
            "dev_permissions": {
                "all_permissions": True,
                "user_management": True,
                "content_moderation": True,
                "system_admin": True
            },
            "moderator_permissions": {
                "content_moderation": True,
                "user_reports": True,
                "community_management": True
            },
            "assigned_by": user_id
        }
        
        # Try to update existing record
        try:
            result = supabase.client.table("user_hierarchy").update(update_data).eq("user_id", user_id).execute()
            logger.info("Updated existing hierarchy record")
        except Exception as e:
            logger.info(f"Could not update existing record: {e}")
            # Try to insert new record
            try:
                insert_data = update_data.copy()
                insert_data["user_id"] = user_id
                result = supabase.client.table("user_hierarchy").insert(insert_data).execute()
                logger.info("Inserted new hierarchy record")
            except Exception as insert_e:
                logger.error(f"Could not insert new record: {insert_e}")
                return False
        
        logger.info("Successfully updated Lawrence to TEAM level!")
        
        # Verify the update
        try:
            verify_result = supabase.client.table("user_hierarchy").select("*").eq("user_id", user_id).execute()
            if verify_result.data:
                user_info = verify_result.data[0]
                logger.info(f"Verification - Hierarchy Level: {user_info['hierarchy_level']} (Dev: {user_info['is_dev']}, Mod: {user_info['is_moderator']})")
        except Exception as verify_e:
            logger.warning(f"Could not verify update: {verify_e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update Lawrence: {e}")
        return False

def main():
    """Main function to update Lawrence's account."""
    logger.info("Starting Lawrence to TEAM level update")
    
    success = update_lawrence_to_team()
    
    if success:
        logger.info("Update completed successfully!")
        logger.info("Lawrence now has TEAM level with full permissions.")
        logger.info("You can now log out and log back in to see the changes.")
        return 0
    else:
        logger.error("Update failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 