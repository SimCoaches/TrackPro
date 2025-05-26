#!/usr/bin/env python3
"""
Test script for TrackPro Community Integration
This script tests the community UI components and integration.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QMessageBox

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

def test_community_imports():
    """Test that all community UI components can be imported."""
    try:
        print("Testing community UI imports...")
        
        # Test main community UI
        from trackpro.ui.main_community_ui import (
            CommunityIntegrationDialog,
            CommunityMainInterface,
            open_community_dialog
        )
        print("✓ Main community UI imported successfully")
        
        # Test community components
        from trackpro.ui.community_ui import (
            CommunityMainWidget,
            CommunityTheme,
            TeamCard,
            ClubCard,
            EventCard
        )
        print("✓ Community components imported successfully")
        
        # Test content management
        from trackpro.ui.content_management_ui import (
            ContentManagementMainWidget,
            ContentCard,
            ContentBrowserWidget
        )
        print("✓ Content management UI imported successfully")
        
        # Test social UI
        from trackpro.ui.social_ui import (
            SocialMainWidget,
            SocialTheme
        )
        print("✓ Social UI imported successfully")
        
        # Test achievements UI
        from trackpro.ui.achievements_ui import (
            GamificationMainWidget,
            AchievementCard
        )
        print("✓ Achievements UI imported successfully")
        
        # Test user account UI
        from trackpro.ui.user_account_ui import (
            UserAccountMainWidget,
            ProfileEditDialog
        )
        print("✓ User account UI imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_main_window_integration():
    """Test that the main window has community integration."""
    try:
        print("Testing main window community integration...")
        
        # Import the main window from the correct location (the .py file, not the package)
        from trackpro.ui import MainWindow
        
        # Create a test instance (without showing it)
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create main window
        window = MainWindow()
        
        # Check if community methods exist
        required_methods = [
            'open_community_interface',
            'open_social_features', 
            'open_community_features',
            'open_content_management',
            'open_achievements',
            'open_account_settings',
            'get_community_managers',
            'get_current_user_id'
        ]
        
        for method in required_methods:
            if not hasattr(window, method):
                print(f"✗ Missing method: {method}")
                return False
        
        print("✓ All required community methods found in MainWindow")
        
        # Check if community buttons exist
        if hasattr(window, 'community_btn'):
            print("✓ Community button found in UI")
        else:
            print("✗ Community button not found in UI")
            return False
            
        if hasattr(window, 'account_btn'):
            print("✓ Account button found in UI")
        else:
            print("✗ Account button not found in UI")
            return False
        
        # Check if community menu action exists
        if hasattr(window, 'community_action'):
            print("✓ Community menu action found")
        else:
            print("✗ Community menu action not found")
            return False
        
        print("✓ Main window community integration verified")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Note: MainWindow should be imported from trackpro.ui module")
        return False
    except Exception as e:
        print(f"✗ Error testing main window: {e}")
        return False

def test_community_dialog():
    """Test opening the community dialog."""
    try:
        from trackpro.ui.main_community_ui import CommunityIntegrationDialog
        
        # Mock managers
        managers = {
            'user_manager': None,
            'friends_manager': None,
            'messaging_manager': None,
            'activity_manager': None,
            'community_manager': None,
            'content_manager': None,
            'achievements_manager': None,
            'reputation_manager': None
        }
        
        # Create the dialog
        dialog = CommunityIntegrationDialog(managers, 'test_user')
        dialog.setWindowTitle("TrackPro Community - Test")
        
        print("✓ Community dialog created successfully")
        return dialog
        
    except Exception as e:
        print(f"✗ Error creating community dialog: {e}")
        return None

def main():
    """Main test function."""
    print("=" * 60)
    print("TrackPro Community Integration Test")
    print("=" * 60)
    
    # Test imports first
    if not test_community_imports():
        print("\n✗ Import tests failed. Cannot continue.")
        return 1
    
    print("\n✓ All community UI imports successful!")
    
    # Test main window integration
    if not test_main_window_integration():
        print("\n✗ Main window integration tests failed.")
        return 1
    
    print("\n✓ Main window integration successful!")
    
    # Test community dialog creation
    dialog = test_community_dialog()
    if dialog is None:
        print("\n✗ Community dialog test failed.")
        return 1
    
    print("\n✓ Community dialog test successful!")
    
    print("\n🎉 All tests passed! Community integration is working correctly.")
    print("\nThe community features are now integrated into TrackPro:")
    print("- Community button in top-right of main window")
    print("- Account button for logged-in users")
    print("- Community menu item in menu bar")
    print("- All community UI components are importable")
    print("- Main window has all required community methods")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 