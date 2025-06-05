#!/usr/bin/env python3
"""
Clear fake social data from TrackPro database
This script removes all fake/test activity data from the user_activities table
"""

import os
import sys

# Add the TrackPro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

from trackpro.database.supabase_client import get_supabase_client

def clear_fake_social_data():
    """Clear fake social data from the database."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Could not connect to database")
            return False
        
        print("🧹 Clearing fake social data from database...")
        
        # Delete all test activities - we want ONLY real racing achievements
        # Delete activities that look like test data
        test_keywords = [
            'Set first lap time at Silverstone',
            'Testing speed to post',
            'How is this working',
            'test',
            'demo',
            'sample',
            'fake',
            'placeholder'
        ]
        
        total_deleted = 0
        
        # Delete activities with test-like titles or descriptions
        for keyword in test_keywords:
            # Delete by title
            result = supabase.from_("user_activities").delete().ilike("title", f"%{keyword}%").execute()
            if result.data:
                deleted_count = len(result.data)
                total_deleted += deleted_count
                print(f"✅ Deleted {deleted_count} activities with '{keyword}' in title")
            
            # Delete by description
            result = supabase.from_("user_activities").delete().ilike("description", f"%{keyword}%").execute()
            if result.data:
                deleted_count = len(result.data)
                total_deleted += deleted_count
                print(f"✅ Deleted {deleted_count} activities with '{keyword}' in description")
        
        # Also delete any activities that are clearly test data based on activity type
        test_activity_types = [
            'test',
            'demo',
            'sample',
            'placeholder',
            'update'  # Generic updates from manual posting
        ]
        
        for activity_type in test_activity_types:
            result = supabase.from_("user_activities").delete().eq("activity_type", activity_type).execute()
            if result.data:
                deleted_count = len(result.data)
                total_deleted += deleted_count
                print(f"✅ Deleted {deleted_count} activities of type '{activity_type}'")
        
        print(f"🎉 Successfully deleted {total_deleted} fake/test activities!")
        print("✨ Live Achievements feed is now clean - ready for real racing data!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing fake data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🗑️ TrackPro Fake Data Cleaner")
    print("=" * 50)
    
    success = clear_fake_social_data()
    
    if success:
        print("\n✅ Database cleaned successfully!")
        print("🏁 Your Live Achievements feed is now ready for real racing data!")
    else:
        print("\n❌ Failed to clean database")
        sys.exit(1) 