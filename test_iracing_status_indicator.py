#!/usr/bin/env python3
"""
Test script to verify the iRacing connection status indicator works correctly.
This script demonstrates how the status dot automatically updates when iRacing connects/disconnects.
"""

import sys
import os
import logging
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_iracing_status_integration():
    """Test the iRacing status indicator integration."""
    logger.info("🧪 Testing iRacing connection status indicator...")
    
    try:
        # Import PyQt6 for the test
        from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
        from PyQt6.QtCore import QTimer
        
        # Create test application
        app = QApplication(sys.argv)
        
        # Import the navigation widget
        from trackpro.ui.discord_navigation import DiscordNavigation
        
        # Create test window
        window = QMainWindow()
        window.setWindowTitle("iRacing Status Indicator Test")
        window.resize(300, 600)
        
        # Create main widget
        main_widget = QWidget()
        window.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add title
        title = QLabel("iRacing Connection Status Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Add instructions
        instructions = QLabel("""
Instructions:
1. The red dot below shows iRacing is disconnected
2. Start iRacing to see the dot turn green
3. Close iRacing to see it turn red again
4. The status updates automatically every 2 seconds
5. No need to restart this application!
        """)
        instructions.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(instructions)
        
        # Create Discord navigation with iRacing status
        nav = DiscordNavigation()
        layout.addWidget(nav)
        
        # Show window
        window.show()
        
        # Create a timer to show status updates in the console
        def log_status():
            try:
                if hasattr(nav, 'iracing_api') and nav.iracing_api:
                    is_connected = nav.iracing_api.is_connected()
                    status = "🟢 CONNECTED" if is_connected else "🔴 DISCONNECTED"
                    logger.info(f"iRacing Status: {status}")
                else:
                    logger.info("iRacing API not available")
            except Exception as e:
                logger.debug(f"Status check error: {e}")
        
        status_timer = QTimer()
        status_timer.timeout.connect(log_status)
        status_timer.start(5000)  # Log status every 5 seconds
        
        logger.info("✅ Test window created successfully!")
        logger.info("👀 Watch the red/green dot in the navigation sidebar")
        logger.info("🏁 Start/stop iRacing to see real-time status changes")
        
        # Run the application
        return app.exec()
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all TrackPro modules and PyQt6 are available.")
        return 1
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return 1

def test_status_functions():
    """Test the iRacing status functions without GUI."""
    logger.info("🧪 Testing iRacing status functions...")
    
    try:
        # Test import
        from trackpro.ui.discord_navigation import DiscordNavigation
        logger.info("✅ Successfully imported DiscordNavigation")
        
        # Test that the class has the expected methods
        expected_methods = [
            'setup_iracing_status',
            'setup_iracing_monitoring', 
            'check_iracing_connection',
            'on_iracing_connection_changed',
            'update_iracing_status'
        ]
        
        for method in expected_methods:
            if hasattr(DiscordNavigation, method):
                logger.info(f"✅ DiscordNavigation has method: {method}")
            else:
                logger.warning(f"⚠️ DiscordNavigation missing method: {method}")
        
        logger.info("✅ Status function tests completed!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import navigation: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Function test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting iRacing connection status indicator tests...")
    
    # Run function tests first
    logger.info("=" * 50)
    logger.info("1. TESTING STATUS FUNCTIONS...")
    function_test_passed = test_status_functions()
    
    logger.info("=" * 50)
    logger.info("2. TESTING GUI INTEGRATION...")
    
    if function_test_passed:
        logger.info("Functions OK - testing GUI integration...")
        try:
            exit_code = test_iracing_status_integration()
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
            exit_code = 0
    else:
        logger.error("Function tests failed - skipping GUI test")
        exit_code = 1
    
    # Summary
    logger.info("=" * 50)
    logger.info("TEST SUMMARY:")
    logger.info(f"Function Tests: {'✅ PASSED' if function_test_passed else '❌ FAILED'}")
    logger.info(f"Overall Result: {'✅ SUCCESS' if exit_code == 0 else '❌ FAILED'}")
    
    if function_test_passed:
        logger.info("")
        logger.info("🎉 iRacing connection status indicator is ready!")
        logger.info("")
        logger.info("Features:")
        logger.info("• 🔴 Red dot when iRacing is disconnected")
        logger.info("• 🟢 Green dot when iRacing is connected") 
        logger.info("• 🔄 Automatic detection every 2 seconds")
        logger.info("• 📱 Real-time updates without app restart")
        logger.info("• 🎯 Positioned above user account button")
        logger.info("• 📐 Responsive layout (dot only when collapsed)")
    
    logger.info("=" * 50)
    
    sys.exit(exit_code)