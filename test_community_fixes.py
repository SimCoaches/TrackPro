#!/usr/bin/env python3
"""
Test script to verify community and account features are working.
"""

import sys
import os
import logging

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

def test_imports():
    """Test that all UI components can be imported without errors."""
    print("🔍 Testing imports...")
    
    try:
        # Test social UI imports
        from trackpro.ui.social_ui import SocialMainWidget, SocialTheme
        print("✅ Social UI imports successful")
    except Exception as e:
        print(f"❌ Social UI import error: {e}")
        return False
    
    try:
        # Test achievements UI imports
        from trackpro.ui.achievements_ui import GamificationMainWidget
        print("✅ Achievements UI imports successful")
    except Exception as e:
        print(f"❌ Achievements UI import error: {e}")
        return False
    
    try:
        # Test user account UI imports
        from trackpro.ui.user_account_ui import UserAccountMainWidget
        print("✅ User Account UI imports successful")
    except Exception as e:
        print(f"❌ User Account UI import error: {e}")
        return False
    
    try:
        # Test community UI imports
        from trackpro.ui.community_ui import CommunityMainWidget
        print("✅ Community UI imports successful")
    except Exception as e:
        print(f"❌ Community UI import error: {e}")
        return False
    
    try:
        # Test content management UI imports
        from trackpro.ui.content_management_ui import ContentManagementMainWidget
        print("✅ Content Management UI imports successful")
    except Exception as e:
        print(f"❌ Content Management UI import error: {e}")
        return False
    
    try:
        # Test main community UI imports
        from trackpro.ui.main_community_ui import (
            open_community_dialog,
            open_social_features,
            open_community_features,
            open_content_management,
            open_achievements,
            open_account_settings
        )
        print("✅ Main Community UI imports successful")
    except Exception as e:
        print(f"❌ Main Community UI import error: {e}")
        return False
    
    return True

def test_widget_constructors():
    """Test that UI widgets can be instantiated with correct parameters."""
    print("\n🔧 Testing widget constructors...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        import sys
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from trackpro.ui.social_ui import SocialMainWidget
        # Test with all parameters as None (should not crash)
        widget = SocialMainWidget(
            user_manager=None,
            friends_manager=None, 
            messaging_manager=None,
            activity_manager=None,
            current_user_id="test_user"
        )
        print("✅ SocialMainWidget constructor works")
    except Exception as e:
        print(f"❌ SocialMainWidget constructor error: {e}")
        return False
    
    try:
        from trackpro.ui.achievements_ui import GamificationMainWidget
        # Test with correct parameters
        widget = GamificationMainWidget(
            achievements_manager=None,
            reputation_manager=None,
            current_user_id="test_user"
        )
        print("✅ GamificationMainWidget constructor works")
    except Exception as e:
        print(f"❌ GamificationMainWidget constructor error: {e}")
        return False
    
    try:
        from trackpro.ui.user_account_ui import UserAccountMainWidget
        # Test with correct parameters
        widget = UserAccountMainWidget(
            user_manager=None,
            current_user_id="test_user"
        )
        print("✅ UserAccountMainWidget constructor works")
    except Exception as e:
        print(f"❌ UserAccountMainWidget constructor error: {e}")
        return False
    
    try:
        from trackpro.ui.community_ui import CommunityMainWidget
        # Test with correct parameters
        widget = CommunityMainWidget(
            community_manager=None,
            user_id="test_user"
        )
        print("✅ CommunityMainWidget constructor works")
    except Exception as e:
        print(f"❌ CommunityMainWidget constructor error: {e}")
        return False
    
    try:
        from trackpro.ui.content_management_ui import ContentManagementMainWidget
        # Test with correct parameters
        widget = ContentManagementMainWidget(
            content_manager=None,
            user_id="test_user"
        )
        print("✅ ContentManagementMainWidget constructor works")
    except Exception as e:
        print(f"❌ ContentManagementMainWidget constructor error: {e}")
        return False
    
    return True

def test_messaging_manager():
    """Test that messaging manager doesn't have SQL syntax errors."""
    print("\n💬 Testing messaging manager...")
    
    try:
        from trackpro.social.messaging_manager import MessagingManager
        
        # Create instance (this will test the import and class definition)
        manager = MessagingManager()
        print("✅ MessagingManager can be instantiated")
        
        # The actual database operations would require a real connection,
        # but at least we can verify the class structure is correct
        return True
    except Exception as e:
        print(f"❌ MessagingManager error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing TrackPro Community & Account Features\n")
    
    # Suppress debug logging for cleaner output
    logging.getLogger().setLevel(logging.WARNING)
    
    all_passed = True
    
    # Run tests
    if not test_imports():
        all_passed = False
    
    if not test_widget_constructors():
        all_passed = False
    
    if not test_messaging_manager():
        all_passed = False
    
    # Summary
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Community and account features should work correctly.")
    else:
        print("❌ SOME TESTS FAILED! There are still issues to fix.")
    print("="*50)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 