#!/usr/bin/env python3
"""
Test script to verify account data loading from Supabase
"""
import logging
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_account_data_loading():
    """Test loading account data from Supabase"""
    try:
        from trackpro.database.supabase_client import get_supabase_client
        from trackpro.social.user_manager import EnhancedUserManager
        
        logger.info("Testing account data loading...")
        
        # Get Supabase client
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("❌ Supabase client not available")
            return False
            
        # Get current user
        user_response = supabase_client.auth.get_user()
        if not user_response or not user_response.user:
            logger.error("❌ No authenticated user")
            return False
            
        user_id = user_response.user.id
        logger.info(f"✅ Authenticated user: {user_id}")
        
        # Test direct query to user_profiles
        try:
            profile_data = supabase_client.from_("user_profiles").select("username, display_name, bio").eq("user_id", user_id).single().execute()
            if profile_data and profile_data.data:
                logger.info(f"✅ Direct user_profiles query successful:")
                logger.info(f"   Username: '{profile_data.data.get('username', 'NOT SET')}'")
                logger.info(f"   Display Name: '{profile_data.data.get('display_name', 'NOT SET')}'")
                logger.info(f"   Bio: '{profile_data.data.get('bio', 'NOT SET')}'")
            else:
                logger.warning("⚠️ No data found in user_profiles table")
        except Exception as e:
            logger.error(f"❌ Error querying user_profiles: {e}")
            
        # Test EnhancedUserManager
        try:
            mgr = EnhancedUserManager()
            profile = mgr.get_complete_user_profile()
            if profile:
                logger.info(f"✅ EnhancedUserManager query successful:")
                logger.info(f"   Username: '{profile.get('username', 'NOT SET')}'")
                logger.info(f"   Display Name: '{profile.get('display_name', 'NOT SET')}'")
                logger.info(f"   Bio: '{profile.get('bio', 'NOT SET')}'")
            else:
                logger.warning("⚠️ No data returned from EnhancedUserManager")
        except Exception as e:
            logger.error(f"❌ Error with EnhancedUserManager: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_account_data_loading()
    if success:
        print("\n✅ Account data loading test completed successfully!")
    else:
        print("\n❌ Account data loading test failed!")
        sys.exit(1)
