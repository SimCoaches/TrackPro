#!/usr/bin/env python3
"""
Test Discord integration with improved scaling and server locking.
"""

import sys
import os

def main():
    try:
        from PyQt5.QtWidgets import QApplication
        from trackpro.community.discord_integration import DiscordIntegrationWidget
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Create Discord widget
        widget = DiscordIntegrationWidget()
        widget.setWindowTitle("TrackPro Discord Integration - Testing")
        widget.resize(1200, 800)
        
        # Show the widget
        widget.show()
        
        print("🎮 Discord integration test started!")
        print("✨ New features:")
        print("   • Improved scaling (90% zoom to prevent overlapping)")
        print("   • Direct server linking (goes to your server, not Discord home)")
        print("   • CSS fixes for server list width")
        print("   • Zoom controls (🔍+ and 🔍- buttons)")
        print("   • Mode toggle button (Widget ↔ Web App)")
        print("   • Hidden server switching elements")
        print("\n🎯 Your server: Sim Coaches Drivers Lounge")
        print("📋 Server ID: 680606980875747344")
        print("\nClose this window when done testing.")
        
        # Run the app
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    main() 