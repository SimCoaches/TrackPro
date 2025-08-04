#!/usr/bin/env python3
"""Test Supabase client initialization."""

import sys
import os
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import get_supabase_client
from trackpro.config import config

def test_supabase_init():
    """Test Supabase client initialization."""
    print("🧪 Testing Supabase Client Initialization...")
    
    try:
        # Check config
        print(f"Supabase enabled: {config.supabase_enabled}")
        print(f"Supabase URL: {config.supabase_url[:50]}..." if config.supabase_url else "No URL")
        print(f"Supabase key: {config.supabase_key[:20]}..." if config.supabase_key else "No key")
        
        # Get client
        print("\nGetting Supabase client...")
        client = get_supabase_client()
        
        if client:
            print("✅ Supabase client created successfully")
            
            # Test a simple operation
            print("Testing connection...")
            try:
                # Try to get the current user
                user = client.auth.get_user()
                if user and user.user:
                    print(f"✅ Connected with user: {user.user.email}")
                else:
                    print("✅ Connected but no user session")
            except Exception as e:
                print(f"⚠️ Connection test failed: {e}")
        else:
            print("❌ Failed to create Supabase client")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_supabase_init() 