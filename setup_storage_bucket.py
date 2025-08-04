#!/usr/bin/env python3
"""
Supabase Storage Bucket Setup Script

This script helps set up the required storage buckets for TrackPro.
Run this if you're getting storage bucket errors.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from trackpro.database.supabase_client import get_supabase_client
from trackpro.config import config

def setup_storage_buckets():
    """Set up required storage buckets in Supabase."""
    print("🔧 Setting up Supabase storage buckets for TrackPro...")
    
    # Get Supabase client
    supabase_client = get_supabase_client()
    if not supabase_client:
        print("❌ Error: Could not connect to Supabase")
        print("Please check your SUPABASE_URL and SUPABASE_KEY environment variables")
        return False
    
    try:
        # List existing buckets
        print("📋 Checking existing storage buckets...")
        buckets = supabase_client.storage.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        print(f"Found buckets via list_buckets(): {bucket_names}")
        
        # Also try to directly access the avatars bucket
        try:
            print("🔍 Attempting to directly access 'avatars' bucket...")
            files = supabase_client.storage.from_('avatars').list()
            print(f"✅ Successfully accessed 'avatars' bucket! Contains {len(files)} files")
            return True
        except Exception as direct_access_error:
            print(f"❌ Cannot directly access 'avatars' bucket: {direct_access_error}")
        
        # Check if avatars bucket exists in the list
        if 'avatars' in bucket_names:
            print("✅ 'avatars' bucket found in bucket list!")
            return True
        
        print("❌ 'avatars' bucket not found in bucket list")
        print("\n📝 To create the 'avatars' bucket manually:")
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to Storage")
        print("3. Click 'Create a new bucket'")
        print("4. Name it exactly 'avatars'")
        print("5. Set it to 'Public' (so avatars can be accessed)")
        print("6. Click 'Create bucket'")
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking storage buckets: {e}")
        return False

def test_avatar_upload():
    """Test avatar upload functionality."""
    print("\n🧪 Testing avatar upload functionality...")
    
    supabase_client = get_supabase_client()
    if not supabase_client:
        print("❌ No Supabase client available")
        return False
    
    try:
        # Test if we can access the avatars bucket directly
        try:
            files = supabase_client.storage.from_('avatars').list()
            print(f"✅ Can access avatars bucket directly (contains {len(files)} files)")
            return True
        except Exception as e:
            print(f"❌ Cannot access avatars bucket directly: {e}")
            
        # Fallback: check bucket list
        buckets = supabase_client.storage.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        
        if 'avatars' in bucket_names:
            print("✅ 'avatars' bucket found in bucket list - uploads should work")
            return True
        
        print("❌ 'avatars' bucket not found - uploads will fail")
        return False
            
    except Exception as e:
        print(f"❌ Error testing avatar upload: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TrackPro Storage Setup")
    print("=" * 40)
    
    # Check Supabase connection
    print("🔗 Checking Supabase connection...")
    if not config.supabase_enabled:
        print("❌ Supabase is disabled in configuration")
        sys.exit(1)
    
    print(f"✅ Supabase enabled: {config.supabase_enabled}")
    print(f"✅ Supabase URL: {config.supabase_url}")
    print(f"✅ Supabase key: {config.supabase_key[:20]}...")
    
    # Set up storage buckets
    setup_success = setup_storage_buckets()
    
    # Test avatar upload
    upload_success = test_avatar_upload()
    
    print("\n" + "=" * 40)
    if setup_success and upload_success:
        print("✅ All storage setup completed successfully!")
        print("You should now be able to upload avatars in TrackPro.")
    else:
        print("⚠️  Storage setup incomplete")
        print("Please follow the manual setup instructions above.")
        print("After creating the 'avatars' bucket, restart TrackPro and try again.") 