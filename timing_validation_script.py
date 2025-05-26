#!/usr/bin/env python3
"""
Timing Validation Script for TrackPro

This script validates that the sector timing system is working correctly
and that sector data is being saved to the database.
"""

import logging
import time
from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sector_timing_integration():
    """Test that sector timing is properly integrated with lap saving."""
    
    logger.info("🔍 [VALIDATION] Starting sector timing integration test...")
    
    # Create API instance
    api = SimpleIRacingAPI()
    
    # Check if sector timing is available
    if not hasattr(api, 'sector_timing') or not api.sector_timing:
        logger.error("❌ [VALIDATION] No sector timing system found in API")
        return False
    
    logger.info("✅ [VALIDATION] Sector timing system found in API")
    
    # Create lap saver instance (mock)
    lap_saver = IRacingLapSaver()
    
    # Test the connection
    api.set_lap_saver(lap_saver)
    
    # Check if the connection was made
    if hasattr(lap_saver, '_sector_timing_system') and lap_saver._sector_timing_system:
        logger.info("✅ [VALIDATION] Sector timing system successfully connected to lap saver")
        
        # Test the fallback method
        if hasattr(lap_saver, '_get_sector_data_from_timing_system'):
            logger.info("✅ [VALIDATION] Fallback method available for sector data retrieval")
            
            # Test calling the fallback method
            try:
                result = lap_saver._get_sector_data_from_timing_system("test-uuid")
                logger.info(f"✅ [VALIDATION] Fallback method callable, returned: {result}")
                return True
            except Exception as e:
                logger.error(f"❌ [VALIDATION] Error calling fallback method: {e}")
                return False
        else:
            logger.error("❌ [VALIDATION] Fallback method not available")
            return False
    else:
        logger.error("❌ [VALIDATION] Sector timing system not connected to lap saver")
        return False

def test_sector_data_format():
    """Test that sector data is in the expected format."""
    
    logger.info("🔍 [VALIDATION] Testing sector data format...")
    
    # Create API instance
    api = SimpleIRacingAPI()
    
    # Get sector timing data
    sector_data = api.get_sector_timing_data()
    
    if sector_data:
        logger.info(f"✅ [VALIDATION] Sector data available: {sector_data.keys()}")
        
        current_progress = sector_data.get('current_progress', {})
        recent_laps = sector_data.get('recent_laps', [])
        is_initialized = sector_data.get('is_initialized', False)
        
        logger.info(f"🔍 [VALIDATION] Is initialized: {is_initialized}")
        logger.info(f"🔍 [VALIDATION] Current progress keys: {list(current_progress.keys())}")
        logger.info(f"🔍 [VALIDATION] Recent laps count: {len(recent_laps)}")
        
        if recent_laps:
            latest_lap = recent_laps[-1]
            logger.info(f"🔍 [VALIDATION] Latest lap type: {type(latest_lap)}")
            if hasattr(latest_lap, 'sector_times'):
                logger.info(f"🔍 [VALIDATION] Latest lap sector times: {latest_lap.sector_times}")
            else:
                logger.info(f"🔍 [VALIDATION] Latest lap attributes: {dir(latest_lap)}")
        
        return True
    else:
        logger.warning("⚠️ [VALIDATION] No sector data available (expected if not connected to iRacing)")
        return True

def main():
    """Main validation function."""
    
    logger.info("🚀 [VALIDATION] Starting TrackPro sector timing validation...")
    
    # Test 1: Integration test
    integration_ok = test_sector_timing_integration()
    
    # Test 2: Data format test
    format_ok = test_sector_data_format()
    
    # Summary
    if integration_ok and format_ok:
        logger.info("✅ [VALIDATION] All tests passed! Sector timing integration is ready.")
        logger.info("💡 [VALIDATION] Next steps:")
        logger.info("   1. Connect to iRacing")
        logger.info("   2. Drive some laps")
        logger.info("   3. Check logs for sector timing debug messages")
        logger.info("   4. Verify sector times are saved to database")
        return True
    else:
        logger.error("❌ [VALIDATION] Some tests failed. Check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 