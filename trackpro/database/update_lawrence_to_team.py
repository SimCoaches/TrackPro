#!/usr/bin/env python
"""
Update Lawrence to TEAM Level

This script immediately updates lawrence@simcoaches.com to TEAM hierarchy level.
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
    """Update Lawrence's account to TEAM level."""
    
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        logger.info("Updating Lawrence to TEAM level...")
        
        # First, get Lawrence's user ID
        result = supabase.client.rpc('execute_sql', {
            'sql': "SELECT id FROM auth.users WHERE email = 'lawrence@simcoaches.com'"
        }).execute()
        
        if not result.data:
            logger.error("Lawrence's user account not found!")
            return False
        
        user_id = result.data[0]['id']
        logger.info(f"Found Lawrence's user ID: {user_id}")
        
        # Update to TEAM level with full permissions
        update_sql = """
        INSERT INTO public.user_hierarchy (
            user_id,
            hierarchy_level, 
            is_dev,
            is_moderator,
            dev_permissions,
            moderator_permissions,
            assigned_by
        ) VALUES (
            %s,
            'TEAM',
            TRUE,
            TRUE,
            '{"all_permissions": true, "user_management": true, "content_moderation": true, "system_admin": true}'::jsonb,
            '{"content_moderation": true, "user_reports": true, "community_management": true}'::jsonb,
            %s
        ) ON CONFLICT (user_id) DO UPDATE SET
            hierarchy_level = 'TEAM',
            is_dev = TRUE,
            is_moderator = TRUE,
            dev_permissions = '{"all_permissions": true, "user_management": true, "content_moderation": true, "system_admin": true}'::jsonb,
            moderator_permissions = '{"content_moderation": true, "user_reports": true, "community_management": true}'::jsonb,
            updated_at = NOW()
        """ % (user_id, user_id)
        
        # Execute the update
        result = supabase.client.rpc('execute_sql', {'sql': update_sql}).execute()
        
        logger.info("Successfully updated Lawrence to TEAM level!")
        
        # Verify the update
        verify_result = supabase.client.rpc('execute_sql', {
            'sql': f"""
            SELECT 
                u.email,
                uh.hierarchy_level,
                uh.is_dev,
                uh.is_moderator
            FROM auth.users u
            LEFT JOIN public.user_hierarchy uh ON u.id = uh.user_id
            WHERE u.email = 'lawrence@simcoaches.com'
            """
        }).execute()
        
        if verify_result.data:
            user_info = verify_result.data[0]
            logger.info(f"Verification - {user_info['email']}: {user_info['hierarchy_level']} (Dev: {user_info['is_dev']}, Mod: {user_info['is_moderator']})")
        
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