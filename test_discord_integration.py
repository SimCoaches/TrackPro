#!/usr/bin/env python3
"""
Test script to verify Discord integration is working properly in TrackPro.
Run this to check if all dependencies and components are available.
"""

import sys
import traceback

def test_imports():
    """Test if all required imports work."""
    print("🔍 Testing imports...")
    
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
        print("✅ PyQtWebEngine import successful")
    except ImportError as e:
        print(f"❌ PyQtWebEngine import failed: {e}")
        return False
    
    try:
        from trackpro.community.discord_integration import DiscordIntegrationWidget
        print("✅ Discord integration widget import successful")
    except ImportError as e:
        print(f"❌ Discord integration widget import failed: {e}")
        return False
    
    try:
        from trackpro.community.discord_setup_dialog import DiscordSetupDialog
        print("✅ Discord setup dialog import successful")
    except ImportError as e:
        print(f"❌ Discord setup dialog import failed: {e}")
        return False
    
    return True

def test_config_file():
    """Test if configuration file exists and is readable."""
    print("\n📁 Testing configuration...")
    
    import os
    import json
    
    config_path = os.path.join(os.path.dirname(__file__), "trackpro", "community", "discord_config.json")
    
    if os.path.exists(config_path):
        print("✅ Discord config file exists")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                print(f"✅ Config file is valid JSON")
                
                server_id = config.get('server_id', '')
                if server_id:
                    print(f"✅ Server ID configured: {server_id}")
                else:
                    print("⚠️  Server ID not configured (expected for first-time setup)")
                
                use_widget_mode = config.get('use_widget_mode', True)
                print(f"ℹ️  Widget mode: {'Enabled' if use_widget_mode else 'Disabled'}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Config file has invalid JSON: {e}")
            return False
    else:
        print("⚠️  Discord config file not found (will be created on first setup)")
    
    return True

def test_widget_creation():
    """Test if Discord widget can be created (requires QApplication)."""
    print("\n🏗️  Testing widget creation...")
    
    try:
        from PyQt5.QtWidgets import QApplication
        
        # Create QApplication if one doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        from trackpro.community.discord_integration import DiscordIntegrationWidget
        
        # Create widget (should work even without configuration)
        widget = DiscordIntegrationWidget()
        print("✅ Discord widget created successfully")
        
        # Check if widget has expected attributes
        if hasattr(widget, 'discord_server_id'):
            print("✅ Widget has server ID attribute")
        
        if hasattr(widget, 'setup_ui'):
            print("✅ Widget has setup_ui method")
        
        if hasattr(widget, 'show_setup_dialog'):
            print("✅ Widget has setup dialog method")
        
        return True
        
    except Exception as e:
        print(f"❌ Widget creation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 TrackPro Discord Integration Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Imports
    if test_imports():
        tests_passed += 1
    
    # Test 2: Configuration
    if test_config_file():
        tests_passed += 1
    
    # Test 3: Widget creation
    if test_widget_creation():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Discord integration is ready.")
        print("\n📋 Next steps:")
        print("1. Open TrackPro")
        print("2. Go to Community → Discord")
        print("3. Follow the setup dialog to configure your Discord server")
        print("4. Enjoy integrated Discord chat!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 