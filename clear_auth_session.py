#!/usr/bin/env python3
"""
Script to clear invalid authentication session and help with proper login.
"""

import os
import json
import sys

def clear_auth_session():
    """Clear the invalid authentication session."""
    auth_file = os.path.expanduser("~/.trackpro/auth.json")
    
    if os.path.exists(auth_file):
        print(f"🗑️  Found invalid auth session at: {auth_file}")
        
        # Read current content
        try:
            with open(auth_file, 'r') as f:
                current_data = json.load(f)
            print(f"📄 Current session data: {current_data}")
        except Exception as e:
            print(f"❌ Error reading auth file: {e}")
            return False
        
        # Check if session is invalid
        if (current_data.get('access_token') is None and 
            current_data.get('refresh_token') is None):
            print("❌ Session is invalid (all tokens are null)")
            
            # Clear the session
            try:
                os.remove(auth_file)
                print("✅ Cleared invalid auth session")
                return True
            except Exception as e:
                print(f"❌ Error clearing auth session: {e}")
                return False
        else:
            print("✅ Session appears valid")
            return True
    else:
        print("ℹ️  No auth session file found")
        return True

def main():
    """Main function."""
    print("🔧 TrackPro Authentication Session Cleaner")
    print("=" * 50)
    
    if clear_auth_session():
        print("\n✅ Session cleared successfully!")
        print("\n📋 Next steps:")
        print("1. Open TrackPro application")
        print("2. Go to Account page")
        print("3. Log in with your credentials")
        print("4. Try accessing the community chat again")
        print("\n💡 The community chat should now recognize you as logged in.")
    else:
        print("\n❌ Failed to clear session")
        print("💡 You may need to manually delete the auth file or restart TrackPro")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main() 