#!/usr/bin/env python
"""
Test Profile Saving

This script tests the profile saving functionality with the new public system.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_profile_saving():
    """Test profile saving functionality."""
    
    try:
        # Import the user manager
        from trackpro.social.user_manager import EnhancedUserManager
        
        # Create user manager instance
        user_manager = EnhancedUserManager()
        
        # Test data for profile update
        test_profile_data = {
            'display_name': 'Test Driver',
            'username': 'testdriver',
            'bio': 'This is a test bio for the public profile system.',
            'avatar_url': 'https://example.com/avatar.jpg',
            'share_data': True,  # Make profile public
            'first_name': 'Test',
            'last_name': 'Driver',
            'location': 'Test City',
            'privacy_settings': {
                'profile_visibility': 'public',
                'show_online_status': True
            }
        }
        
        # Get current user
        current_user = user_manager.get_complete_user_profile()
        if not current_user:
            logger.error("No authenticated user found. Please log in first.")
            return False
        
        user_id = current_user['user_id']
        logger.info(f"Testing profile update for user: {user_id}")
        
        # Update profile
        success = user_manager.update_user_profile(user_id, test_profile_data)
        if success:
            logger.info("Profile updated successfully!")
            
            # Test getting public profile
            public_profile = user_manager.get_public_user_profile(user_id)
            if public_profile:
                logger.info(f"Public profile retrieved: {public_profile.get('display_name')}")
            else:
                logger.warning("Could not retrieve public profile")
            
            # Test online status update
            online_success = user_manager.update_online_status(user_id, True, "1.0.0", "Windows")
            if online_success:
                logger.info("Online status updated successfully!")
            else:
                logger.warning("Failed to update online status")
            
            # Test getting online users
            online_users = user_manager.get_online_users(10)
            logger.info(f"Found {len(online_users)} online users")
            
            return True
        else:
            logger.error("Failed to update profile")
            return False
            
    except Exception as e:
        logger.error(f"Error testing profile saving: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_profile_saving()
    if success:
        print("Profile saving test completed successfully!")
    else:
        print("Profile saving test failed!")
        sys.exit(1) 