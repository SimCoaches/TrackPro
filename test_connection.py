#!/usr/bin/env python3
"""
Test TrackPro Database Connection
Simple script to test if the Supabase connection is working
"""

import sys
import os

# Add the trackpro module to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_supabase_connection():
    """Test the Supabase connection"""
    try:
        print("Testing TrackPro Supabase connection...")
        
        # Import the database client
        from trackpro.database.supabase_client import get_supabase_client
        
        # Get the client
        client = get_supabase_client()
        
        if client is None:
            print("❌ Failed: Supabase client is None")
            return False
            
        print("✅ Supabase client created successfully")
        
        # Test basic connection by checking auth status
        try:
            session = client.auth.get_session()
            print(f"✅ Auth connection successful (session: {session is not None})")
        except Exception as e:
            print(f"⚠️  Auth test failed: {e}")
        
        # Test database connection by listing tables
        try:
            # Simple query to test database connectivity
            response = client.table('user_profiles').select('user_id').limit(1).execute()
            print("✅ Database connection successful")
            print(f"   Query executed successfully (returned {len(response.data) if response.data else 0} rows)")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
            
        # Test community managers
        try:
            from trackpro.community.database_managers import create_community_managers
            managers = create_community_managers(client)
            print("✅ Community managers created successfully")
            print(f"   Available managers: {list(managers.keys())}")
        except Exception as e:
            print(f"❌ Community managers creation failed: {e}")
            return False
            
        print("\n🎉 All tests passed! Database connection is working.")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    if success:
        print("\n✨ Your TrackPro app should now be able to connect to the community features!")
        print("   Try opening the Community tab in TrackPro to see it in action.")
    else:
        print("\n⚠️  There are still connection issues. Check the error messages above.")
    
    sys.exit(0 if success else 1) 