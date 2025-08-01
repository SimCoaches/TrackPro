#!/usr/bin/env python3
"""
Test script to verify Supabase connection
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

def test_supabase_connection():
    """Test the Supabase connection using credentials from .env file."""
    
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    print("🔍 Testing Supabase Connection...")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key: {SUPABASE_KEY[:20]}..." if SUPABASE_KEY else "Key: Not set")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        print("\n📝 Please update your .env file with your actual Supabase credentials:")
        print("SUPABASE_URL=https://your-project-id.supabase.co")
        print("SUPABASE_KEY=your-anon-key")
        return False
    
    try:
        # Create Supabase client
        print("🔧 Creating Supabase client...")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test connection by accessing auth API
        print("🔍 Testing connection...")
        session = supabase.auth.get_session()
        print("✅ Connection successful!")
        
        # Test database access
        print("🔍 Testing database access...")
        # Try to access a simple table or function
        result = supabase.table("user_profiles").select("count", count="exact").limit(1).execute()
        print("✅ Database access successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    if success:
        print("\n🎉 Supabase connection is working!")
        print("Your MCP Supabase should now be properly connected.")
    else:
        print("\n⚠️  Please check your Supabase credentials and try again.") 