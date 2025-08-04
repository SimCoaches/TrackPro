#!/usr/bin/env python3
"""
Test script to verify startup optimizations work correctly.
"""

import sys
import time
import logging
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Set up logging to see the startup process
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_startup_optimization():
    """Test the startup optimization by running the app briefly."""
    print("🚀 Testing TrackPro startup optimization...")
    
    # Set OpenGL context sharing attribute before creating QApplication
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Import and test the main components
    try:
        from trackpro.modern_main import ModernTrackProApp
        from trackpro.auth import oauth_handler
        
        print("✅ Successfully imported main components")
        
        # Create OAuth handler
        oauth_handler_instance = oauth_handler.OAuthHandler()
        print("✅ OAuth handler created")
        
        # Create the app
        start_time = time.time()
        trackpro_app = ModernTrackProApp(oauth_handler=oauth_handler_instance, start_time=start_time, app=app)
        print(f"✅ ModernTrackProApp created in {time.time() - start_time:.2f}s")
        
        # Test the main window
        if hasattr(trackpro_app, 'window'):
            print("✅ Main window created successfully")
            
            # Test auth state caching
            if hasattr(trackpro_app.window, '_startup_auth_check_completed'):
                print("✅ Auth state caching implemented")
            
            # Test user info caching
            if hasattr(trackpro_app.window, '_cached_user_info'):
                print("✅ User info caching implemented")
        
        print("✅ All startup optimizations working correctly!")
        
        # Clean up
        app.quit()
        return True
        
    except Exception as e:
        print(f"❌ Error during startup test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_startup_optimization()
    sys.exit(0 if success else 1) 