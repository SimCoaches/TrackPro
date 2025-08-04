#!/usr/bin/env python3
"""
Debug script to test profile save functionality.
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import get_supabase_client
from trackpro.social import enhanced_user_manager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_profile_save():
    """Test saving profile data."""
    try:
        # Get Supabase client
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("Failed to get Supabase client")
            return False
        
        # Check if user is authenticated
        user_response = supabase_client.auth.get_user()
        if not user_response or not user_response.user:
            logger.error("No authenticated user found")
            return False
        
        user_id = user_response.user.id
        logger.info(f"Testing with user ID: {user_id}")
        logger.info(f"User email: {user_response.user.email}")
        
        # Test data to save
        test_profile_data = {
            "first_name": "LAWRENCE",
            "last_name": "THOMAS", 
            "display_name": "Lawrence",
            "bio": "love innovating. send me a DM if you have ways to improve this app.",
            "date_of_birth": "1994-01-28"
        }
        
        logger.info(f"Saving test profile data: {test_profile_data}")
        
        # Test database connection first
        try:
            # Test user_profiles table
            logger.info("Testing user_profiles table access...")
            profile_response = supabase_client.from_("user_profiles").select("user_id").eq("user_id", user_id).limit(1).execute()
            logger.info(f"user_profiles query result: {profile_response.data}")
            
            # Test user_details table
            logger.info("Testing user_details table access...")
            details_response = supabase_client.from_("user_details").select("user_id").eq("user_id", user_id).limit(1).execute()
            logger.info(f"user_details query result: {details_response.data}")
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        
        # Save profile data
        logger.info("Attempting to save profile data...")
        success = enhanced_user_manager.update_user_profile(user_id, test_profile_data)
        if not success:
            logger.error("Failed to save profile data")
            return False
        
        logger.info("Profile data saved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_profile_save()
    if success:
        print("✅ Profile save test passed!")
    else:
        print("❌ Profile save test failed!")
        sys.exit(1) 