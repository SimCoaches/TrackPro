#!/usr/bin/env python3
"""
Minimal Supabase client test that avoids importing the full trackpro module.
This test directly imports only the necessary components to avoid pygame initialization.
"""

import os
import sys
import logging

# Add the project root to the path so we can import modules directly
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_supabase_direct_import():
    """Test Supabase client with direct imports to avoid pygame."""
    print("🧪 Testing Supabase client with minimal imports...")
    
    try:
        # Import config directly without going through trackpro.__init__
        from trackpro.config import config
        print("✅ Successfully imported config")
        
        # Import supabase client directly
        from trackpro.database.supabase_client import get_supabase_client
        print("✅ Successfully imported supabase_client")
        
        # Get the client
        client = get_supabase_client()
        if client:
            print("✅ Supabase client created successfully")
            
            # Test basic connection
            try:
                session = client.auth.get_session()
                if session and hasattr(session, 'user') and session.user:
                    print(f"✅ Connected to Supabase with user: {session.user.email}")
                else:
                    print("✅ Connected to Supabase (no active session)")
            except Exception as e:
                print(f"⚠️ Connection test failed: {e}")
        else:
            print("❌ Failed to create Supabase client")
            
    except Exception as e:
        print(f"❌ Error during minimal test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_supabase_direct_import()
    print("\n🏁 Test completed - script should exit cleanly") 