#!/usr/bin/env python3
"""
Completely isolated Supabase client test that bypasses the trackpro module structure.
This test imports the supabase_client module directly to avoid any UI-related imports.
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

def test_supabase_isolated():
    """Test Supabase client with completely isolated imports."""
    print("🧪 Testing Supabase client with isolated imports...")
    
    try:
        # Import config directly by path to avoid trackpro.__init__
        sys.path.insert(0, os.path.join(project_root, 'trackpro'))
        from config import config
        print("✅ Successfully imported config directly")
        
        # Import supabase_client directly by path
        sys.path.insert(0, os.path.join(project_root, 'trackpro', 'database'))
        from supabase_client import get_supabase_client
        print("✅ Successfully imported supabase_client directly")
        
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
        print(f"❌ Error during isolated test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_supabase_isolated()
    print("\n🏁 Test completed - script should exit cleanly") 