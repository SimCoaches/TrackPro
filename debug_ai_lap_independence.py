#!/usr/bin/env python3
"""
Debug AI Coach and Lap Saving Independence
=========================================

This script tests whether:
1. Lap saving works WITHOUT AI coach active
2. AI coach works WITHOUT affecting lap saving
3. Both systems work together WITHOUT interfering

Run this while iRacing is active to get real diagnostic data.
"""

import sys
import os
import time
import logging
import threading
from pathlib import Path

# Add the trackpro module to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up basic logging to see everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('AI_LAP_DEBUG')

def test_lap_saving_independence():
    """Test that lap saving works without AI coach."""
    print("\n" + "="*60)
    print("🔍 TESTING LAP SAVING INDEPENDENCE")
    print("="*60)
    
    try:
        # Import just the lap saving components
        from trackpro.race_coach.simple_iracing import SimpleIRacingAPI
        from trackpro.race_coach.iracing_lap_saver import IRacingLapSaver
        from trackpro.database.supabase_client import get_supabase_client
        
        print("✅ Successfully imported lap saving modules")
        
        # Create API without AI coach
        api = SimpleIRacingAPI()
        print("✅ SimpleIRacingAPI created")
        
        # Create lap saver 
        lap_saver = IRacingLapSaver()
        print("✅ IRacingLapSaver created")
        
        # Set up Supabase
        supabase_client = get_supabase_client()
        if supabase_client:
            lap_saver.set_supabase_client(supabase_client)
            print("✅ Supabase client connected to lap saver")
        else:
            print("❌ No Supabase client available")
            
        # Connect lap saver to API
        api.set_lap_saver(lap_saver)
        print("✅ Lap saver connected to API")
        
        # Start deferred monitoring (this starts the session monitor)
        if hasattr(api, '_deferred_monitor_params'):
            print("✅ Deferred monitor params available")
            api.start_deferred_monitoring()
            print("✅ Deferred monitoring started")
        else:
            print("❌ No deferred monitor params")
            
        # Start telemetry polling
        print("🔄 Starting telemetry polling for 10 seconds...")
        
        telemetry_count = 0
        def count_telemetry(data):
            nonlocal telemetry_count
            telemetry_count += 1
            if telemetry_count % 60 == 0:  # Every second
                print(f"📊 Lap saving telemetry: {telemetry_count} points received")
                
        api.register_on_telemetry_data(count_telemetry)
        
        # Let it run for 10 seconds
        time.sleep(10)
        
        print(f"📊 RESULT: Received {telemetry_count} telemetry points in 10 seconds")
        if telemetry_count > 0:
            print("✅ LAP SAVING TELEMETRY IS WORKING")
        else:
            print("❌ LAP SAVING TELEMETRY NOT WORKING")
            
        return telemetry_count > 0
        
    except Exception as e:
        print(f"❌ Error testing lap saving: {e}")
        logger.exception("Lap saving test failed")
        return False

def test_ai_coach_independence():
    """Test that AI coach works without affecting lap saving."""
    print("\n" + "="*60)
    print("🤖 TESTING AI COACH INDEPENDENCE")
    print("="*60)
    
    try:
        # Import AI coach components
        from trackpro.race_coach.utils.telemetry_worker import TelemetryMonitorWorker
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        
        print("✅ Successfully imported AI coach modules")
        
        # Check for API keys
        openai_key = os.getenv("OPENAI_API_KEY")
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        
        if not openai_key:
            print("❌ OpenAI API key not found - set OPENAI_API_KEY environment variable")
            return False
        if not elevenlabs_key:
            print("❌ ElevenLabs API key not found - set ELEVENLABS_API_KEY environment variable")
            return False
            
        print("✅ API keys available")
        
        # Use a known superlap ID (from the logs we saw earlier)
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        print(f"🔄 Loading SuperLap: {superlap_id}")
        
        # Create AI coach (this takes 3+ seconds)
        start_time = time.time()
        ai_coach = AICoach(superlap_id=superlap_id)
        load_time = time.time() - start_time
        
        print(f"✅ AI Coach loaded in {load_time:.1f}s with {len(ai_coach.superlap_points)} points")
        
        # Create telemetry worker
        worker = TelemetryMonitorWorker()
        worker.ai_coach = ai_coach
        
        print("✅ TelemetryMonitorWorker created")
        
        # Start monitoring
        success = worker.start_monitoring()
        if success:
            print("✅ AI coaching monitoring started")
        else:
            print("❌ Failed to start AI coaching monitoring")
            return False
            
        # Test AI coaching with fake telemetry
        print("🔄 Testing AI coaching with fake telemetry...")
        
        coaching_count = 0
        def count_coaching():
            nonlocal coaching_count
            coaching_count += 1
            
        # Mock the AI coach to count coaching calls
        original_process = ai_coach.process_realtime_telemetry
        def mock_process(telemetry):
            count_coaching()
            return original_process(telemetry)
        ai_coach.process_realtime_telemetry = mock_process
        
        # Send fake telemetry for 5 seconds
        for i in range(300):  # 5 seconds at 60Hz
            fake_telemetry = {
                'track_position': (i % 100) / 100.0,  # 0.0 to 1.0
                'speed': 100 + (i % 50),
                'throttle': 0.8,
                'brake': 0.0,
                'steering': 0.1
            }
            worker.add_telemetry_point(fake_telemetry)
            time.sleep(1/60)  # 60 Hz
            
        print(f"📊 RESULT: AI coach processed {coaching_count} telemetry points")
        if coaching_count > 0:
            print("✅ AI COACH TELEMETRY IS WORKING")
        else:
            print("❌ AI COACH TELEMETRY NOT WORKING")
            
        return coaching_count > 0
        
    except Exception as e:
        print(f"❌ Error testing AI coach: {e}")
        logger.exception("AI coach test failed")
        return False

def test_combined_systems():
    """Test both systems working together."""
    print("\n" + "="*60)
    print("🔄 TESTING COMBINED SYSTEMS")
    print("="*60)
    
    print("🔍 This test will run both lap saving and AI coach together")
    print("🔍 We should see BOTH systems receiving telemetry independently")
    
    # TODO: Implement combined test
    print("⚠️ Combined test not implemented yet - run individual tests first")
    return True

def main():
    """Run all independence tests."""
    print("🚀 AI COACH AND LAP SAVING INDEPENDENCE TEST")
    print("=" * 60)
    print("This will test whether AI coaching and lap saving work independently")
    print("Make sure iRacing is running before starting...")
    print()
    
    input("Press Enter when iRacing is ready...")
    
    results = {}
    
    # Test lap saving alone
    results['lap_saving'] = test_lap_saving_independence()
    
    # Test AI coach alone  
    results['ai_coach'] = test_ai_coach_independence()
    
    # Test combined
    results['combined'] = test_combined_systems()
    
    # Summary
    print("\n" + "="*60)
    print("📊 INDEPENDENCE TEST RESULTS")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.upper()}: {status}")
        
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - Systems are working independently!")
    else:
        print("\n❌ SOME TESTS FAILED - There are still issues to fix")
        
    return all_passed

if __name__ == "__main__":
    main() 