#!/usr/bin/env python3
"""
Session Creation Diagnostic Tool

This script tests the entire session creation pipeline to identify where
telemetry saving is failing.
"""

import sys
import os
import logging
import time
from pathlib import Path
import traceback
from typing import Optional

# Add the trackpro directory to the path so we can import modules
script_dir = Path(__file__).parent
trackpro_dir = script_dir / "trackpro"
sys.path.insert(0, str(script_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('session_diagnostic.log')
    ]
)

logger = logging.getLogger(__name__)

def test_supabase_connection():
    """Test Supabase connection and authentication."""
    logger.info("=" * 60)
    logger.info("TESTING SUPABASE CONNECTION")
    logger.info("=" * 60)
    
    try:
        # Test 1: Import Supabase client
        logger.info("1. Testing Supabase client import...")
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            logger.error("❌ Supabase client is None - connection failed")
            return False
            
        logger.info("✅ Supabase client imported successfully")
        
        # Test 2: Check authentication
        logger.info("2. Testing authentication status...")
        try:
            user = client.auth.get_user()
            if user and hasattr(user, 'user') and user.user:
                logger.info(f"✅ User authenticated: {user.user.email}")
                return True
            else:
                logger.warning("⚠️ No authenticated user found")
                return False
        except Exception as auth_error:
            logger.error(f"❌ Authentication check failed: {auth_error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Supabase connection test failed: {e}")
        return False

def test_session_creation():
    """Test manual session creation."""
    logger.info("=" * 60)
    logger.info("TESTING SESSION CREATION")
    logger.info("=" * 60)
    
    try:
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            logger.error("❌ Cannot test session creation - no Supabase client")
            return False
        
        # Get current user
        user = client.auth.get_user()
        if not user or not hasattr(user, 'user') or not user.user:
            logger.error("❌ Cannot test session creation - no authenticated user")
            return False
            
        user_id = user.user.id
        logger.info(f"Creating test session for user: {user_id}")
        
        # Test data for session creation
        test_session_data = {
            'user_id': user_id,
            'track_id': '00000000-0000-0000-0000-000000000001',  # Dummy track ID
            'car_id': '00000000-0000-0000-0000-000000000001',    # Dummy car ID
            'session_type': 'Test Session',
            'session_date': 'now()',
            'created_at': 'now()'
        }
        
        logger.info("Attempting to create test session...")
        response = client.table('sessions').insert(test_session_data).execute()
        
        if response.data and len(response.data) > 0:
            session_id = response.data[0].get('id')
            logger.info(f"✅ Test session created successfully: {session_id}")
            
            # Clean up test session
            logger.info("Cleaning up test session...")
            client.table('sessions').delete().eq('id', session_id).execute()
            logger.info("✅ Test session cleaned up")
            return True
        else:
            logger.error(f"❌ Session creation failed: {response}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Session creation test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_iracing_monitor_setup():
    """Test iRacing monitor setup."""
    logger.info("=" * 60)
    logger.info("TESTING IRACING MONITOR SETUP")
    logger.info("=" * 60)
    
    try:
        # Test monitor imports
        logger.info("1. Testing monitor imports...")
        from trackpro.race_coach.iracing_session_monitor import start_monitoring, stop_monitoring
        from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
        from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
        logger.info("✅ Monitor imports successful")
        
        # Test lap saver initialization
        logger.info("2. Testing lap saver initialization...")
        lap_saver = IRacingLapSaver()
        logger.info(f"✅ Lap saver created: {lap_saver}")
        
        # Check lap saver's session state
        logger.info("3. Checking lap saver session state...")
        logger.info(f"   Session ID: {getattr(lap_saver, '_current_session_id', 'NOT SET')}")
        logger.info(f"   Track ID: {getattr(lap_saver, '_current_track_id', 'NOT SET')}")
        logger.info(f"   Car ID: {getattr(lap_saver, '_current_car_id', 'NOT SET')}")
        logger.info(f"   User ID: {getattr(lap_saver, '_user_id', 'NOT SET')}")
        
        if not getattr(lap_saver, '_current_session_id', None):
            logger.warning("⚠️ Lap saver has no session ID - this is why telemetry isn't being saved!")
            return False
            
        logger.info("✅ Lap saver has session ID")
        return True
        
    except Exception as e:
        logger.error(f"❌ Monitor setup test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_telemetry_processing():
    """Test telemetry processing pipeline."""
    logger.info("=" * 60)
    logger.info("TESTING TELEMETRY PROCESSING")
    logger.info("=" * 60)
    
    try:
        from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
        
        # Create lap saver
        lap_saver = IRacingLapSaver()
        
        # Test with dummy telemetry data
        dummy_telemetry = {
            'SessionTimeSecs': 120.0,
            'LapDistPct': 0.5,
            'Speed': 100.0,
            'RPM': 6000,
            'Throttle': 0.8,
            'Brake': 0.0,
            'Lap': 2,
            'LapCompleted': 1,
            'LapLastLapTime': 85.5
        }
        
        logger.info("Testing telemetry processing with dummy data...")
        result = lap_saver.process_telemetry(dummy_telemetry)
        
        if result:
            logger.info(f"✅ Telemetry processing returned: {result}")
            return True
        else:
            logger.warning("⚠️ Telemetry processing returned nothing")
            return False
            
    except Exception as e:
        logger.error(f"❌ Telemetry processing test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_database_tables():
    """Check if required database tables exist."""
    logger.info("=" * 60)
    logger.info("CHECKING DATABASE TABLES")
    logger.info("=" * 60)
    
    try:
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            logger.error("❌ Cannot check tables - no Supabase client")
            return False
        
        # Test each required table
        required_tables = ['sessions', 'laps', 'telemetry_points', 'tracks', 'cars']
        
        for table in required_tables:
            try:
                logger.info(f"Checking table: {table}")
                response = client.table(table).select("*").limit(1).execute()
                logger.info(f"✅ Table {table} exists and is accessible")
            except Exception as table_error:
                logger.error(f"❌ Table {table} issue: {table_error}")
                return False
        
        logger.info("✅ All required tables exist and are accessible")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database table check failed: {e}")
        return False

def create_manual_session():
    """Manually create a session for testing."""
    logger.info("=" * 60)
    logger.info("CREATING MANUAL SESSION FOR TESTING")
    logger.info("=" * 60)
    
    try:
        from trackpro.database.supabase_client import get_supabase_client
        from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
        
        client = get_supabase_client()
        if not client:
            logger.error("❌ Cannot create session - no Supabase client")
            return None
        
        # Get current user
        user = client.auth.get_user()
        if not user or not hasattr(user, 'user') or not user.user:
            logger.error("❌ Cannot create session - no authenticated user")
            return None
            
        user_id = user.user.id
        
        # Create or get a test track
        logger.info("Creating/finding test track...")
        track_response = client.table('tracks').select('id').eq('name', 'Test Track').execute()
        
        if track_response.data and len(track_response.data) > 0:
            track_id = track_response.data[0]['id']
            logger.info(f"Using existing track: {track_id}")
        else:
            # Create test track
            track_data = {
                'name': 'Test Track',
                'config': 'Test Config',
                'iracing_track_id': 999999,
                'iracing_config_id': 999999,
                'length_meters': 5000.0
            }
            track_response = client.table('tracks').insert(track_data).execute()
            if track_response.data and len(track_response.data) > 0:
                track_id = track_response.data[0]['id']
                logger.info(f"Created test track: {track_id}")
            else:
                logger.error("❌ Failed to create test track")
                return None
        
        # Create or get a test car
        logger.info("Creating/finding test car...")
        car_response = client.table('cars').select('id').eq('name', 'Test Car').execute()
        
        if car_response.data and len(car_response.data) > 0:
            car_id = car_response.data[0]['id']
            logger.info(f"Using existing car: {car_id}")
        else:
            # Create test car
            car_data = {
                'name': 'Test Car',
                'class': 'Test Class',
                'iracing_car_id': 999999
            }
            car_response = client.table('cars').insert(car_data).execute()
            if car_response.data and len(car_response.data) > 0:
                car_id = car_response.data[0]['id']
                logger.info(f"Created test car: {car_id}")
            else:
                logger.error("❌ Failed to create test car")
                return None
        
        # Create test session
        logger.info("Creating test session...")
        session_data = {
            'user_id': user_id,
            'track_id': track_id,
            'car_id': car_id,
            'session_type': 'Diagnostic Test',
        }
        
        session_response = client.table('sessions').insert(session_data).execute()
        
        if session_response.data and len(session_response.data) > 0:
            session_id = session_response.data[0]['id']
            logger.info(f"✅ Test session created: {session_id}")
            
            # Now set up the lap saver with this session
            logger.info("Setting up lap saver with test session...")
            lap_saver = IRacingLapSaver()
            lap_saver._current_session_id = session_id
            lap_saver._current_track_id = track_id
            lap_saver._current_car_id = car_id
            lap_saver._user_id = user_id
            
            logger.info("✅ Lap saver configured with test session")
            return session_id
        else:
            logger.error("❌ Failed to create test session")
            return None
            
    except Exception as e:
        logger.error(f"❌ Manual session creation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def check_race_coach_monitoring():
    """Check if Race Coach monitoring is properly started and authenticated."""
    try:
        logger.info("============================================================")
        logger.info("CHECKING RACE COACH MONITORING")
        logger.info("============================================================")
        
        # Check if user is authenticated
        from trackpro.auth.user_manager import get_current_user
        user = get_current_user()
        
        if user and hasattr(user, 'id') and user.is_authenticated:
            logger.info(f"✅ User authenticated: {user.id}")
            user_id = user.id
        else:
            logger.error("❌ No authenticated user - this is why monitoring isn't starting!")
            logger.error("   Solution: User needs to login to TrackPro first")
            return {"status": "FAIL", "reason": "No authenticated user"}
        
        # Check if SimpleIRacingAPI has monitoring parameters
        try:
            from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
            # Create a test instance to check monitoring setup
            test_api = SimpleIRacingAPI()
            
            if hasattr(test_api, '_deferred_monitor_params'):
                params = test_api._deferred_monitor_params
                logger.info(f"✅ Monitoring parameters found: {params.keys()}")
                
                if 'user_id' in params and 'supabase_client' in params and 'lap_saver' in params:
                    logger.info("✅ All required monitoring parameters present")
                else:
                    logger.warning("⚠️ Missing some monitoring parameters")
                    
            else:
                logger.warning("⚠️ No deferred monitoring parameters set")
                
        except Exception as api_error:
            logger.error(f"❌ Error checking SimpleIRacingAPI: {api_error}")
            
        # Check if monitoring thread is actually running
        try:
            from trackpro.race_coach import iracing_session_monitor
            
            # Check if monitor thread exists
            if hasattr(iracing_session_monitor, '_monitor_thread'):
                thread = iracing_session_monitor._monitor_thread
                if thread and thread.is_alive():
                    logger.info("✅ Session monitor thread is running")
                else:
                    logger.warning("⚠️ Session monitor thread is not running")
            else:
                logger.warning("⚠️ No session monitor thread found")
                
        except Exception as monitor_error:
            logger.error(f"❌ Error checking session monitor: {monitor_error}")
            
        return {"status": "PASS", "user_id": user_id}
        
    except Exception as e:
        logger.error(f"❌ Error checking race coach monitoring: {e}")
        traceback.print_exc()
        return {"status": "FAIL", "reason": str(e)}

def attempt_manual_monitor_start():
    """Attempt to manually start the monitoring with proper authentication."""
    try:
        logger.info("============================================================")
        logger.info("ATTEMPTING MANUAL MONITOR START")
        logger.info("============================================================")
        
        # Get authenticated user
        from trackpro.auth.user_manager import get_current_user
        user = get_current_user()
        
        if not (user and hasattr(user, 'id') and user.is_authenticated):
            logger.error("❌ Cannot start monitoring - no authenticated user")
            return False
            
        user_id = user.id
        logger.info(f"✅ User authenticated: {user_id}")
        
        # Get Supabase client
        from trackpro.database.supabase_client import get_supabase_client
        supabase_client = get_supabase_client()
        
        if not supabase_client:
            logger.error("❌ Cannot start monitoring - no Supabase client")
            return False
            
        logger.info("✅ Supabase client available")
        
        # Create lap saver
        from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
        lap_saver = IRacingLapSaver()
        lap_saver.set_supabase_client(supabase_client)
        lap_saver.set_user_id(user_id)
        logger.info("✅ Lap saver created and configured")
        
        # Create SimpleIRacingAPI
        from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
        simple_api = SimpleIRacingAPI()
        logger.info("✅ SimpleIRacingAPI created")
        
        # Start monitoring
        from trackpro.race_coach.iracing_session_monitor import start_monitoring
        result = start_monitoring(supabase_client, user_id, lap_saver, simple_api)
        
        if result:
            logger.info("✅ Monitoring thread started successfully!")
            return True
        else:
            logger.error("❌ Failed to start monitoring thread")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error starting manual monitoring: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests."""
    logger.info("Starting TrackPro Session Creation Diagnostic")
    logger.info("This will help identify why telemetry data is not being saved")
    
    results = {}
    
    # Test 1: Supabase Connection
    results['supabase_connection'] = test_supabase_connection()
    
    # Test 2: Database Tables
    results['database_tables'] = check_database_tables()
    
    # Test 3: Session Creation
    results['session_creation'] = test_session_creation()
    
    # Test 4: iRacing Monitor Setup
    results['monitor_setup'] = test_iracing_monitor_setup()
    
    # Test 5: Telemetry Processing
    results['telemetry_processing'] = test_telemetry_processing()
    
    # Test 6: Manual Session Creation
    manual_session_id = create_manual_session()
    results['manual_session'] = manual_session_id is not None
    
    # Test 7: Race Coach Monitoring
    results['race_coach_monitoring'] = check_race_coach_monitoring()
    
    # Test 8: Manual Monitor Start
    results['manual_monitor_start'] = attempt_manual_monitor_start()
    
    # Summary
    logger.info("=" * 60)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        if test_name == 'race_coach_monitoring':
            status = "✅ PASS" if result.get('status') == 'PASS' else "❌ FAIL"
        else:
            status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    # Check if tests passed
    failed_tests = []
    for name, result in results.items():
        if name == 'race_coach_monitoring':
            if result.get('status') != 'PASS':
                failed_tests.append(name)
        elif not result:
            failed_tests.append(name)
    
    if not failed_tests:
        logger.info("🎉 All tests passed! Session creation should work.")
        if manual_session_id:
            logger.info(f"Manual session created for testing: {manual_session_id}")
            logger.info("Try running TrackPro now - telemetry should be saved!")
    else:
        logger.error("❌ Some tests failed. This explains why telemetry is not being saved.")
        logger.info("Check the failed tests above to fix the issues.")
        
        # Specific guidance
        if 'race_coach_monitoring' in failed_tests:
            logger.info("")
            logger.info("💡 SOLUTION: The user needs to login to TrackPro first!")
            logger.info("   1. Open TrackPro")
            logger.info("   2. Click the login button") 
            logger.info("   3. Login with Google/Discord")
            logger.info("   4. Then start iRacing and the telemetry will be saved")
            logger.info("")
    
    return results

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Diagnostic failed with unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1) 