#!/usr/bin/env python3
"""
Test script to diagnose AI coaching issues:
1. Why superlap telemetry shows 0.000s times
2. Why AI coach isn't providing feedback
3. Verify telemetry is reaching the AI coach
"""

import logging
import time
import sys
import os

# Add the TrackPro directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_superlap_loading():
    """Test loading superlap data to see what's in it."""
    print("\n" + "="*60)
    print("TESTING SUPERLAP DATA LOADING")
    print("="*60)
    
    try:
        from Supabase.database import get_super_lap_telemetry_points
        
        # Test superlap ID from the logs
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        
        print(f"\nLoading superlap: {superlap_id}")
        points, message = get_super_lap_telemetry_points(superlap_id)
        
        if points:
            print(f"✅ Loaded {len(points)} telemetry points")
            print(f"Message: {message}")
            
            # Analyze the data
            print("\n📊 SUPERLAP DATA ANALYSIS:")
            
            # Check first 5 points
            print("\nFirst 5 points:")
            for i, point in enumerate(points[:5]):
                print(f"  Point {i}: pos={point.get('track_position', 'N/A'):.3f}, "
                      f"time={point.get('current_time', 'N/A'):.3f}s, "
                      f"speed={point.get('speed', 'N/A'):.1f} km/h, "
                      f"throttle={point.get('throttle', 'N/A'):.2f}")
            
            # Check speed distribution
            speeds = [p.get('speed', 0) for p in points if 'speed' in p]
            if speeds:
                avg_speed = sum(speeds) / len(speeds)
                max_speed = max(speeds)
                min_speed = min(speeds)
                zero_speed_count = sum(1 for s in speeds if s == 0)
                print(f"\n📊 Speed Analysis:")
                print(f"  Average: {avg_speed:.1f} km/h")
                print(f"  Max: {max_speed:.1f} km/h") 
                print(f"  Min: {min_speed:.1f} km/h")
                print(f"  Zero speeds: {zero_speed_count}/{len(speeds)}")
                
                if zero_speed_count == len(speeds):
                    print("  ⚠️ WARNING: All speeds are 0! This explains why AI coach isn't working!")
            else:
                print("  ❌ No speed data in telemetry points!")
            
            # Check if essential fields exist
            sample_point = points[0] if points else {}
            print(f"\n🔍 Fields in telemetry point:")
            for key in sorted(sample_point.keys()):
                print(f"  - {key}: {type(sample_point[key]).__name__}")
                
        else:
            print(f"❌ Failed to load superlap: {message}")
            
    except Exception as e:
        print(f"❌ Error testing superlap: {e}")
        import traceback
        traceback.print_exc()

def test_ai_coach_initialization():
    """Test AI coach initialization with the superlap."""
    print("\n" + "="*60)
    print("TESTING AI COACH INITIALIZATION")
    print("="*60)
    
    try:
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        print(f"\nInitializing AI Coach with superlap: {superlap_id}")
        
        coach = AICoach(superlap_id=superlap_id)
        
        print(f"✅ AI Coach initialized")
        print(f"  - Superlap points loaded: {len(coach.superlap_points)}")
        print(f"  - Advice interval: {coach.advice_interval}s")
        
        # Check superlap data quality
        if coach.superlap_points:
            sample = coach.superlap_points[len(coach.superlap_points)//2]  # Middle point
            print(f"\n📊 Sample superlap point (middle of lap):")
            print(f"  Position: {sample.get('track_position', 'N/A')}")
            print(f"  Speed: {sample.get('speed', 'N/A')} km/h")
            print(f"  Throttle: {sample.get('throttle', 'N/A')}")
            print(f"  Brake: {sample.get('brake', 'N/A')}")
            
            # Test finding closest point
            test_position = 0.5
            closest = coach._find_closest_superlap_point(test_position)
            if closest:
                print(f"\n🔍 Closest point to position {test_position}:")
                print(f"  Position: {closest.get('track_position', 'N/A')}")
                print(f"  Speed: {closest.get('speed', 'N/A')} km/h")
            
        return coach
        
    except Exception as e:
        print(f"❌ Error initializing AI coach: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_ai_coach_processing():
    """Test AI coach with simulated telemetry."""
    print("\n" + "="*60)
    print("TESTING AI COACH TELEMETRY PROCESSING")
    print("="*60)
    
    coach = test_ai_coach_initialization()
    if not coach:
        print("❌ Cannot test processing - AI coach initialization failed")
        return
    
    # Simulate some telemetry points
    test_telemetry_points = [
        {'track_position': 0.1, 'speed': 120, 'throttle': 0.8, 'brake': 0.0, 'steering': 0.1},
        {'track_position': 0.3, 'speed': 150, 'throttle': 1.0, 'brake': 0.0, 'steering': -0.05},
        {'track_position': 0.5, 'speed': 80, 'throttle': 0.0, 'brake': 0.8, 'steering': 0.2},
        {'track_position': 0.7, 'speed': 140, 'throttle': 0.9, 'brake': 0.0, 'steering': 0.0},
        {'track_position': 0.9, 'speed': 100, 'throttle': 0.3, 'brake': 0.5, 'steering': 0.15},
    ]
    
    print("\nProcessing test telemetry points...")
    for i, point in enumerate(test_telemetry_points):
        print(f"\n📍 Test point {i+1}: pos={point['track_position']:.1f}, speed={point['speed']} km/h")
        
        # Process with AI coach
        coach.process_realtime_telemetry(point)
        
        # Give it time to speak if coaching was triggered
        time.sleep(2)
        
def check_database_connection():
    """Check if we can connect to the database."""
    print("\n" + "="*60)
    print("CHECKING DATABASE CONNECTION")
    print("="*60)
    
    try:
        from trackpro.database.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if client:
            print("✅ Successfully connected to Supabase")
            
            # Try a simple query
            try:
                result = client.table("super_laps_ml").select("id,name").limit(1).execute()
                if result.data:
                    print(f"✅ Can query database - found {len(result.data)} superlaps")
                else:
                    print("⚠️ Database query returned no data")
            except Exception as e:
                print(f"❌ Error querying database: {e}")
        else:
            print("❌ Failed to get Supabase client")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def check_api_keys():
    """Check if API keys are configured."""
    print("\n" + "="*60)
    print("CHECKING API KEYS")
    print("="*60)
    
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    elevenlabs_key = os.environ.get('ELEVENLABS_API_KEY', '')
    
    print(f"OpenAI API Key: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"ElevenLabs API Key: {'✅ Set' if elevenlabs_key else '❌ Not set'}")
    
    if not openai_key or not elevenlabs_key:
        print("\n⚠️ Missing API keys will prevent AI coaching from working!")
        print("Set them as environment variables:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("  export ELEVENLABS_API_KEY='your-key-here'")

if __name__ == "__main__":
    print("\n🤖 AI COACH DIAGNOSTIC TEST")
    print("This will help diagnose why AI coaching isn't working properly")
    
    # Run all tests
    check_api_keys()
    check_database_connection()
    test_superlap_loading()
    # Only test processing if the data looks good
    # test_ai_coach_processing()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60) 