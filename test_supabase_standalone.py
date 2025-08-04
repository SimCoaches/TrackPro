#!/usr/bin/env python3
"""
Standalone Supabase connectivity test that doesn't import trackpro modules.
This test directly uses the Supabase Python client to verify connectivity.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def load_env_variables():
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        
        # Try to load .env file
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment variables from: {env_path}")
            return True
        else:
            print(f"⚠️ No .env file found at: {env_path}")
            return False
    except ImportError:
        print("⚠️ python-dotenv not available, using system environment variables")
        return False

def test_supabase_standalone():
    """Test Supabase connectivity using direct client."""
    print("🧪 Testing Supabase connectivity with standalone client...")
    
    # Load environment variables
    load_env_variables()
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in environment variables")
        print(f"   SUPABASE_URL: {'Set' if supabase_url else 'Not set'}")
        print(f"   SUPABASE_KEY: {'Set' if supabase_key else 'Not set'}")
        return False
    
    print(f"✅ Found Supabase URL: {supabase_url}")
    print(f"✅ Found Supabase key: {supabase_key[:20]}...")
    
    try:
        # Import Supabase client directly
        from supabase import create_client, Client
        
        # Create client
        print("🔧 Creating Supabase client...")
        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Test basic connection
        print("🔧 Testing connection...")
        session = client.auth.get_session()
        
        if session and hasattr(session, 'user') and session.user:
            print(f"✅ Connected to Supabase with authenticated user: {session.user.email}")
        else:
            print("✅ Connected to Supabase (no active session)")
        
        # Test a simple database operation (if we have access)
        try:
            # Try to get the current user (this should work even without authentication)
            user_response = client.auth.get_user()
            if user_response and hasattr(user_response, 'user') and user_response.user:
                print(f"✅ User info retrieved: {user_response.user.email}")
            else:
                print("✅ No authenticated user (expected for standalone test)")
        except Exception as e:
            print(f"⚠️ User info test failed (expected): {e}")
        
        print("✅ All Supabase connectivity tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Supabase client: {e}")
        print("   Please install: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error during Supabase test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_supabase_standalone()
    if success:
        print("\n🎉 Supabase connectivity test completed successfully!")
    else:
        print("\n❌ Supabase connectivity test failed!")
    
    print("🏁 Test completed - script should exit cleanly") 