#!/usr/bin/env python3
"""
Telemetry Flow Test Script

This script tests the complete telemetry data flow:
1. Database connection and authentication
2. Session and lap data retrieval
3. Telemetry data fetching and processing
4. Graph widget data handling
5. Full integration test

Run this to identify exactly where the telemetry visualization is failing.
"""

import sys
import os
import logging
import traceback
from datetime import datetime
import json

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('telemetry_test.log')
    ]
)

logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported."""
    logger.info("=== TESTING IMPORTS ===")
    
    try:
        # Test PyQt5 imports
        from PyQt5.QtWidgets import QApplication, QWidget
        from PyQt5.QtCore import QTimer
        logger.info("✅ PyQt5 imports successful")
        
        # Test Supabase imports
        from Supabase.database import get_laps, get_telemetry_points, get_sessions
        from trackpro.database.supabase_client import get_supabase_client
        logger.info("✅ Supabase imports successful")
        
        # Test race coach imports
        from trackpro.race_coach.ui import TelemetryFetchWorker
        from trackpro.race_coach.widgets.throttle_graph import ThrottleGraphWidget
        from trackpro.race_coach.widgets.brake_graph import BrakeGraphWidget
        from trackpro.race_coach.widgets.steering_graph import SteeringGraphWidget
        from trackpro.race_coach.widgets.speed_graph import SpeedGraphWidget
        logger.info("✅ Race coach widget imports successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_supabase_connection():
    """Test Supabase connection and authentication."""
    logger.info("=== TESTING SUPABASE CONNECTION ===")
    
    try:
        from trackpro.database.supabase_client import supabase
        
        if supabase is None:
            logger.error("❌ Supabase client is None")
            return False
            
        # Test authentication
        is_authenticated = supabase.is_authenticated()
        logger.info(f"Authentication status: {is_authenticated}")
        
        if not is_authenticated:
            logger.error("❌ Not authenticated with Supabase")
            return False
            
        # Test user info
        user_response = supabase.get_user()
        if user_response and user_response.user:
            user_id = user_response.user.id
            logger.info(f"✅ Authenticated as user: {user_id}")
        else:
            logger.error("❌ Could not get user info")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Supabase connection test failed: {e}")
        traceback.print_exc()
        return False

def test_session_data_retrieval():
    """Test retrieving session data from database."""
    logger.info("=== TESTING SESSION DATA RETRIEVAL ===")
    
    try:
        from Supabase.database import get_sessions
        
        # Get recent sessions
        sessions, msg = get_sessions(limit=10, user_only=True)
        
        if sessions is None:
            logger.error(f"❌ Failed to get sessions: {msg}")
            return None
            
        logger.info(f"✅ Retrieved {len(sessions)} sessions")
        
        for i, session in enumerate(sessions[:3]):  # Show first 3
            logger.info(f"Session {i+1}: ID={session.get('id')}, Track={session.get('track_name')}, Car={session.get('car_name')}")
            
        return sessions
        
    except Exception as e:
        logger.error(f"❌ Session retrieval failed: {e}")
        traceback.print_exc()
        return None

def test_lap_data_retrieval(session_id):
    """Test retrieving lap data for a specific session."""
    logger.info(f"=== TESTING LAP DATA RETRIEVAL FOR SESSION {session_id} ===")
    
    try:
        from Supabase.database import get_laps
        
        # Get laps for the session
        laps, msg = get_laps(limit=20, user_only=True, session_id=session_id)
        
        if laps is None:
            logger.error(f"❌ Failed to get laps: {msg}")
            return None
            
        logger.info(f"✅ Retrieved {len(laps)} laps for session {session_id}")
        
        for i, lap in enumerate(laps[:5]):  # Show first 5
            lap_num = lap.get('lap_number', 'Unknown')
            lap_time = lap.get('lap_time', 0)
            lap_id = lap.get('id')
            is_valid = lap.get('is_valid', False)
            logger.info(f"Lap {i+1}: ID={lap_id}, Number={lap_num}, Time={lap_time:.3f}s, Valid={is_valid}")
            
        return laps
        
    except Exception as e:
        logger.error(f"❌ Lap retrieval failed: {e}")
        traceback.print_exc()
        return None

def test_telemetry_data_retrieval(lap_id):
    """Test retrieving telemetry data for a specific lap."""
    logger.info(f"=== TESTING TELEMETRY DATA RETRIEVAL FOR LAP {lap_id} ===")
    
    try:
        from Supabase.database import get_telemetry_points
        
        # Test with required columns
        required_columns = ["track_position", "speed", "throttle", "brake", "steering", "timestamp"]
        
        # Get telemetry points
        points, msg = get_telemetry_points(lap_id, columns=required_columns)
        
        if points is None:
            logger.error(f"❌ Failed to get telemetry points: {msg}")
            return None
            
        logger.info(f"✅ Retrieved {len(points)} telemetry points for lap {lap_id}")
        
        if len(points) > 0:
            # Analyze the data
            first_point = points[0]
            last_point = points[-1]
            
            logger.info(f"First point: {first_point}")
            logger.info(f"Last point: {last_point}")
            
            # Check for required fields
            missing_fields = []
            for field in required_columns:
                if field not in first_point:
                    missing_fields.append(field)
                    
            if missing_fields:
                logger.warning(f"⚠️ Missing fields in telemetry data: {missing_fields}")
            else:
                logger.info("✅ All required fields present in telemetry data")
                
            # Check data ranges
            speeds = [p.get('speed', 0) for p in points]
            throttles = [p.get('throttle', 0) for p in points]
            brakes = [p.get('brake', 0) for p in points]
            
            logger.info(f"Speed range: {min(speeds):.1f} - {max(speeds):.1f}")
            logger.info(f"Throttle range: {min(throttles):.3f} - {max(throttles):.3f}")
            logger.info(f"Brake range: {min(brakes):.3f} - {max(brakes):.3f}")
            
        return points
        
    except Exception as e:
        logger.error(f"❌ Telemetry retrieval failed: {e}")
        traceback.print_exc()
        return None

def test_telemetry_worker(left_lap_id, right_lap_id):
    """Test the TelemetryFetchWorker class."""
    logger.info(f"=== TESTING TELEMETRY WORKER: {left_lap_id} vs {right_lap_id} ===")
    
    try:
        from trackpro.race_coach.ui import TelemetryFetchWorker
        
        # Create worker
        worker = TelemetryFetchWorker(left_lap_id, right_lap_id)
        
        # Test the _calculate_lap_stats method directly
        logger.info("Testing _calculate_lap_stats method...")
        
        # Get some sample telemetry data
        from Supabase.database import get_telemetry_points
        required_columns = ["track_position", "speed", "throttle", "brake", "steering", "timestamp"]
        
        left_points, _ = get_telemetry_points(left_lap_id, columns=required_columns)
        if left_points:
            result = worker._calculate_lap_stats(left_points)
            if result:
                logger.info(f"✅ _calculate_lap_stats returned: {type(result)}")
                logger.info(f"Stats keys: {result.get('stats', {}).keys() if isinstance(result, dict) else 'Not a dict'}")
                logger.info(f"Points count: {len(result.get('points', [])) if isinstance(result, dict) else 'Unknown'}")
                
                # Check if the field mapping worked
                if isinstance(result, dict) and 'points' in result:
                    mapped_points = result['points']
                    if len(mapped_points) > 0:
                        first_mapped = mapped_points[0]
                        logger.info(f"First mapped point keys: {first_mapped.keys()}")
                        
                        # Check if LapDist field was created
                        if 'LapDist' in first_mapped:
                            logger.info("✅ LapDist field mapping successful")
                        else:
                            logger.error("❌ LapDist field mapping failed")
                            
                return result
            else:
                logger.error("❌ _calculate_lap_stats returned None")
        else:
            logger.error("❌ Could not get telemetry points for testing")
            
        return None
        
    except Exception as e:
        logger.error(f"❌ Telemetry worker test failed: {e}")
        traceback.print_exc()
        return None

def test_graph_widgets():
    """Test the graph widgets with sample data."""
    logger.info("=== TESTING GRAPH WIDGETS ===")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from trackpro.race_coach.widgets.throttle_graph import ThrottleGraphWidget
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            
        # Create a test widget
        throttle_graph = ThrottleGraphWidget()
        
        # Test if the widget has the expected methods
        expected_methods = ['update_graph_comparison', 'validate_telemetry_data']
        
        for method in expected_methods:
            if hasattr(throttle_graph, method):
                logger.info(f"✅ ThrottleGraphWidget has {method} method")
            else:
                logger.error(f"❌ ThrottleGraphWidget missing {method} method")
                
        # Create sample data for testing
        sample_left_data = {
            'stats': {'total_time': 90.5, 'avg_speed': 120.0},
            'points': [
                {'LapDist': 0.0, 'throttle': 0.8, 'brake': 0.0, 'steering': 0.0, 'speed': 100.0, 'timestamp': 0.0},
                {'LapDist': 0.1, 'throttle': 0.9, 'brake': 0.0, 'steering': 0.1, 'speed': 110.0, 'timestamp': 1.0},
                {'LapDist': 0.2, 'throttle': 0.7, 'brake': 0.2, 'steering': 0.0, 'speed': 105.0, 'timestamp': 2.0}
            ]
        }
        
        sample_right_data = {
            'stats': {'total_time': 91.0, 'avg_speed': 118.0},
            'points': [
                {'LapDist': 0.0, 'throttle': 0.7, 'brake': 0.0, 'steering': 0.0, 'speed': 98.0, 'timestamp': 0.0},
                {'LapDist': 0.1, 'throttle': 0.8, 'brake': 0.0, 'steering': 0.05, 'speed': 108.0, 'timestamp': 1.0},
                {'LapDist': 0.2, 'throttle': 0.6, 'brake': 0.3, 'steering': 0.0, 'speed': 102.0, 'timestamp': 2.0}
            ]
        }
        
        # Test the graph update method
        try:
            track_length = 1000.0
            throttle_graph.update_graph_comparison(sample_left_data, sample_right_data, track_length)
            logger.info("✅ Graph widget update_graph_comparison executed without error")
        except Exception as graph_error:
            logger.error(f"❌ Graph widget update failed: {graph_error}")
            traceback.print_exc()
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Graph widget test failed: {e}")
        traceback.print_exc()
        return False

def test_full_integration():
    """Test the complete integration flow."""
    logger.info("=== TESTING FULL INTEGRATION ===")
    
    try:
        # 1. Get sessions
        sessions = test_session_data_retrieval()
        if not sessions:
            logger.error("❌ Cannot proceed - no sessions available")
            return False
            
        # 2. Get laps for first session
        first_session = sessions[0]
        session_id = first_session.get('id')
        laps = test_lap_data_retrieval(session_id)
        
        if not laps or len(laps) < 2:
            logger.error("❌ Cannot proceed - need at least 2 laps for comparison")
            return False
            
        # 3. Get telemetry for first two laps
        left_lap_id = laps[0].get('id')
        right_lap_id = laps[1].get('id')
        
        logger.info(f"Testing integration with laps: {left_lap_id} vs {right_lap_id}")
        
        # 4. Test telemetry retrieval
        left_telemetry = test_telemetry_data_retrieval(left_lap_id)
        right_telemetry = test_telemetry_data_retrieval(right_lap_id)
        
        if not left_telemetry or not right_telemetry:
            logger.error("❌ Cannot proceed - missing telemetry data")
            return False
            
        # 5. Test worker processing
        worker_result = test_telemetry_worker(left_lap_id, right_lap_id)
        
        if not worker_result:
            logger.error("❌ Worker processing failed")
            return False
            
        # 6. Test graph widgets
        graph_result = test_graph_widgets()
        
        if not graph_result:
            logger.error("❌ Graph widget test failed")
            return False
            
        logger.info("✅ Full integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Full integration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting Telemetry Flow Test Suite")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 60)
    
    results = {}
    
    # Run all tests
    results['imports'] = test_imports()
    
    if results['imports']:
        results['supabase'] = test_supabase_connection()
        
        if results['supabase']:
            results['sessions'] = test_session_data_retrieval() is not None
            results['graph_widgets'] = test_graph_widgets()
            results['integration'] = test_full_integration()
        else:
            logger.error("❌ Skipping further tests due to Supabase connection failure")
            results['sessions'] = False
            results['graph_widgets'] = False
            results['integration'] = False
    else:
        logger.error("❌ Skipping all tests due to import failures")
        results['supabase'] = False
        results['sessions'] = False
        results['graph_widgets'] = False
        results['integration'] = False
    
    # Print summary
    logger.info("=" * 60)
    logger.info("🏁 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name.upper()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    logger.info("=" * 60)
    logger.info(f"OVERALL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Telemetry flow is working correctly.")
    else:
        logger.error("💥 Some tests failed. Check the logs above for details.")
        
    logger.info("📝 Detailed logs saved to telemetry_test.log")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 