#!/usr/bin/env python
"""
Check and set Lawrence Thomas's avatar URL in the database.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from trackpro.database.supabase_client import supabase

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_lawrence_avatar():
    """Check Lawrence's avatar URL in the database."""
    
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        logger.info("Checking Lawrence's avatar URL...")
        
        # First, get Lawrence's user ID
        result = supabase.client.rpc('execute_sql', {
            'sql': "SELECT id FROM auth.users WHERE email = 'lawrence@simcoaches.com'"
        }).execute()
        
        if not result.data:
            logger.error("Lawrence's user account not found!")
            return False
        
        user_id = result.data[0]['id']
        logger.info(f"Found Lawrence's user ID: {user_id}")
        
        # Check Lawrence's profile in user_profiles table
        profile_result = supabase.client.rpc('execute_sql', {
            'sql': f"SELECT user_id, username, display_name, avatar_url FROM user_profiles WHERE user_id = '{user_id}'"
        }).execute()
        
        if profile_result.data:
            profile = profile_result.data[0]
            logger.info(f"Lawrence's profile: {profile}")
            
            avatar_url = profile.get('avatar_url')
            if avatar_url:
                logger.info(f"✅ Lawrence has avatar URL: {avatar_url}")
                return True
            else:
                logger.warning("❌ Lawrence has no avatar URL set")
                
                # Set a default avatar URL for Lawrence (the yellow "S" avatar)
                # This should be the same avatar that's showing in the main user interface
                default_avatar_url = "https://your-supabase-project.supabase.co/storage/v1/object/public/avatars/lawrence_avatar.png"
                
                # Update Lawrence's profile with avatar URL
                update_result = supabase.client.rpc('execute_sql', {
                    'sql': f"UPDATE user_profiles SET avatar_url = '{default_avatar_url}' WHERE user_id = '{user_id}'"
                }).execute()
                
                logger.info("✅ Updated Lawrence's avatar URL")
                return True
        else:
            logger.warning("Lawrence's profile not found in user_profiles table")
            
            # Create Lawrence's profile with avatar URL
            insert_result = supabase.client.rpc('execute_sql', {
                'sql': f"""
                INSERT INTO user_profiles (user_id, username, display_name, avatar_url) 
                VALUES ('{user_id}', 'lawrence', 'Lawrence Thomas', 'https://your-supabase-project.supabase.co/storage/v1/object/public/avatars/lawrence_avatar.png')
                """
            }).execute()
            
            logger.info("✅ Created Lawrence's profile with avatar URL")
            return True
        
    except Exception as e:
        logger.error(f"Failed to check Lawrence's avatar: {e}")
        return False

def main():
    """Main function."""
    success = check_lawrence_avatar()
    if success:
        logger.info("✅ Lawrence's avatar check completed successfully")
    else:
        logger.error("❌ Lawrence's avatar check failed")

if __name__ == "__main__":
    main() 