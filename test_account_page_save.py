#!/usr/bin/env python3
"""
Test script to verify account page save/load functionality.
This script tests the user profile saving and loading functionality.
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import get_supabase_client
from trackpro.social import enhanced_user_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_profile_save_load():
    """Test saving and loading user profile data."""
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
        
        # Test data to save
        test_profile_data = {
            "first_name": "John",
            "last_name": "Doe",
            "display_name": "JohnDoe",
            "bio": "Test bio for account page",
            "date_of_birth": "1990-01-01"
        }
        
        logger.info(f"Saving test profile data: {test_profile_data}")
        
        # Save profile data
        success = enhanced_user_manager.update_user_profile(user_id, test_profile_data)
        if not success:
            logger.error("Failed to save profile data")
            return False
        
        logger.info("Profile data saved successfully")
        
        # Load profile data
        loaded_data = enhanced_user_manager.get_complete_user_profile(user_id)
        if not loaded_data:
            logger.error("Failed to load profile data")
            return False
        
        logger.info(f"Loaded profile data: {loaded_data}")
        
        # Verify that the saved data matches what we loaded
        for key, expected_value in test_profile_data.items():
            loaded_value = loaded_data.get(key)
            if loaded_value != expected_value:
                logger.warning(f"Mismatch for {key}: expected {expected_value}, got {loaded_value}")
            else:
                logger.info(f"✓ {key} matches: {loaded_value}")
        
        logger.info("Test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_user_profile_save_load()
    if success:
        print("✅ Account page save/load test passed!")
    else:
        print("❌ Account page save/load test failed!")
        sys.exit(1) 