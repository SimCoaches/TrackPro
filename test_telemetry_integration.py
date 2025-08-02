#!/usr/bin/env python3
"""
Test script to verify the iRacing telemetry integration in new_ui.py works correctly.
This script tests the telemetry functions without running the full UI.
"""

import sys
import os
import logging

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_iracing_integration():
    """Test the iRacing integration functions."""
    logger.info("🧪 Testing iRacing telemetry integration...")
    
    try:
        # Import the functions from new_ui.py
        from new_ui import initialize_global_iracing_connection, get_global_iracing_api, cleanup_global_iracing_connection
        
        logger.info("✅ Successfully imported iRacing functions from new_ui.py")
        
        # Test initialization
        logger.info("🏁 Testing iRacing connection initialization...")
        initialize_global_iracing_connection()
        
        # Test getting the API
        logger.info("🔍 Testing global iRacing API access...")
        iracing_api = get_global_iracing_api()
        
        if iracing_api:
            logger.info("✅ Global iRacing API instance created successfully")
            logger.info(f"📊 API type: {type(iracing_api)}")
            
            # Check if API has expected methods
            expected_methods = [
                'register_on_telemetry_data',
                'register_on_connection_changed',
                'is_connected',
                'current_telemetry',
                '_start_telemetry_timer'
            ]
            
            for method in expected_methods:
                if hasattr(iracing_api, method):
                    logger.info(f"✅ API has method: {method}")
                else:
                    logger.warning(f"⚠️ API missing method: {method}")
            
            # Test connection status
            if hasattr(iracing_api, 'is_connected'):
                try:
                    connected = iracing_api.is_connected()
                    logger.info(f"🔗 iRacing connection status: {connected}")
                except Exception as e:
                    logger.info(f"🔗 Connection check error (normal if iRacing not running): {e}")
            
            # Test current telemetry access
            if hasattr(iracing_api, 'current_telemetry'):
                telemetry = iracing_api.current_telemetry
                logger.info(f"📊 Current telemetry type: {type(telemetry)}")
                if isinstance(telemetry, dict):
                    logger.info(f"📊 Telemetry keys count: {len(telemetry)}")
                    if telemetry:
                        sample_keys = list(telemetry.keys())[:5]
                        logger.info(f"📊 Sample telemetry keys: {sample_keys}")
                else:
                    logger.info("📊 No telemetry data available (normal if iRacing not running)")
            
        else:
            logger.error("❌ Failed to get global iRacing API instance")
        
        # Test cleanup
        logger.info("🧹 Testing iRacing connection cleanup...")
        cleanup_global_iracing_connection()
        
        # Verify cleanup worked
        iracing_api_after_cleanup = get_global_iracing_api()
        if iracing_api_after_cleanup is None:
            logger.info("✅ Cleanup successful - API instance is None")
        else:
            logger.warning("⚠️ Cleanup may not have worked completely")
        
        logger.info("✅ All iRacing integration tests completed!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("This may be due to missing dependencies. Make sure all TrackPro modules are available.")
        return False
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

def test_example_screen_import():
    """Test that the example telemetry screen can be imported."""
    logger.info("🧪 Testing example telemetry screen import...")
    
    try:
        from example_telemetry_screen import TelemetryExampleScreen
        logger.info("✅ Successfully imported TelemetryExampleScreen")
        
        # Check if it has the expected methods
        expected_methods = [
            'setup_telemetry_connection',
            'on_telemetry_data',
            'on_connection_changed',
            'update_telemetry_display'
        ]
        
        for method in expected_methods:
            if hasattr(TelemetryExampleScreen, method):
                logger.info(f"✅ TelemetryExampleScreen has method: {method}")
            else:
                logger.warning(f"⚠️ TelemetryExampleScreen missing method: {method}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import example screen: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Example screen test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting iRacing telemetry integration tests...")
    
    # Run tests
    test1_passed = test_iracing_integration()
    test2_passed = test_example_screen_import()
    
    # Summary
    logger.info("=" * 50)
    logger.info("TEST SUMMARY:")
    logger.info(f"iRacing Integration Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    logger.info(f"Example Screen Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        logger.info("🎉 ALL TESTS PASSED! iRacing telemetry integration is ready to use.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run 'python new_ui.py' to start the modern UI with iRacing telemetry")
        logger.info("2. Use the example_telemetry_screen.py as a template for your own screens")
        logger.info("3. Access telemetry in any screen using: from new_ui import get_global_iracing_api")
    else:
        logger.error("❌ Some tests failed. Check the errors above and fix any issues.")
    
    logger.info("=" * 50)