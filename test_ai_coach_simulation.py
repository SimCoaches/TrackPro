#!/usr/bin/env python3
"""
Simulate AI Coach initialization to debug the exact failure point.
This test runs the AI coach setup process without needing iRacing.
"""

import logging
import sys
import os

# Add the TrackPro directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup detailed logging to see our debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def simulate_ai_coach_initialization():
    """Simulate the AI coach initialization process."""
    print("🧪 SIMULATING AI COACH INITIALIZATION")
    print("=" * 60)
    
    try:
        # Import required modules
        print("📦 Step 1: Importing modules...")
        from trackpro.race_coach.utils.telemetry_worker import TelemetryMonitorWorker
        from trackpro.race_coach.ai_coach.ai_coach import AICoach
        print("✅ Modules imported successfully")
        
        # Create telemetry worker (like in main_window.py)
        print("\n🔧 Step 2: Creating TelemetryMonitorWorker...")
        telemetry_monitor_worker = TelemetryMonitorWorker()
        print(f"✅ TelemetryMonitorWorker created: {telemetry_monitor_worker}")
        print(f"   Initial ai_coach: {getattr(telemetry_monitor_worker, 'ai_coach', 'MISSING')}")
        print(f"   Initial is_monitoring: {getattr(telemetry_monitor_worker, 'is_monitoring', 'MISSING')}")
        
        # Use the SuperLap ID from the logs (this was working in the real app)
        superlap_id = "e5c615d9-73fa-4e28-8499-3541a037ce77"
        print(f"\n🤖 Step 3: Testing AI Coach creation with SuperLap ID: {superlap_id}")
        
        # Simulate the exact code from start_ai_coaching method
        logger.info(f"🤖 [AI COACH START] Starting AI coaching with superlap_id: {superlap_id}")
        logger.info(f"🤖 [AI COACH START] TelemetryMonitorWorker available: {telemetry_monitor_worker is not None}")
        
        # Check authentication (like in real code)
        print("\n🔐 Step 4: Checking authentication...")
        try:
            from trackpro.database.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()
            if not supabase_client:
                print("❌ No authenticated Supabase client available")
                return False
            print("✅ Authenticated Supabase client available")
        except Exception as auth_error:
            print(f"❌ Authentication check failed: {auth_error}")
            return False
        
        # Now run the exact code from our updated start_ai_coaching method
        print(f"\n🤖 Step 5: Running AI Coach initialization (with new debugging)...")
        
        try:
            # Initialize AI coach with the superlap
            logger.info(f"🤖 [AI COACH START] Creating AICoach with superlap_id: {superlap_id}")
            
            # Add detailed debugging around AI coach creation
            logger.info(f"🔧 [AI DEBUG] About to call AICoach constructor...")
            
            try:
                ai_coach_instance = AICoach(superlap_id=superlap_id)
                logger.info(f"🔧 [AI DEBUG] AICoach constructor completed successfully")
                logger.info(f"🔧 [AI DEBUG] AI coach type: {type(ai_coach_instance)}")
                logger.info(f"🔧 [AI DEBUG] AI coach superlap_points: {len(getattr(ai_coach_instance, 'superlap_points', []))}")
                print(f"✅ AI Coach constructor completed successfully")
                print(f"   Type: {type(ai_coach_instance)}")
                print(f"   SuperLap points loaded: {len(getattr(ai_coach_instance, 'superlap_points', []))}")
                
            except Exception as constructor_error:
                logger.error(f"❌ [AI DEBUG] AICoach constructor failed: {constructor_error}")
                logger.error(f"❌ [AI DEBUG] Constructor exception type: {type(constructor_error)}")
                import traceback
                logger.error(f"❌ [AI DEBUG] Constructor traceback: {traceback.format_exc()}")
                print(f"❌ AI Coach constructor FAILED: {constructor_error}")
                print(f"   Exception type: {type(constructor_error)}")
                traceback.print_exc()
                return False
            
            # Try to assign the AI coach to the worker
            logger.info(f"🔧 [AI DEBUG] About to assign AI coach to telemetry worker...")
            logger.info(f"🔧 [AI DEBUG] Worker before assignment: {telemetry_monitor_worker}")
            logger.info(f"🔧 [AI DEBUG] Worker ai_coach before: {getattr(telemetry_monitor_worker, 'ai_coach', 'MISSING')}")
            
            try:
                telemetry_monitor_worker.ai_coach = ai_coach_instance
                logger.info(f"🔧 [AI DEBUG] AI coach assignment completed")
                logger.info(f"🔧 [AI DEBUG] Worker ai_coach after: {getattr(telemetry_monitor_worker, 'ai_coach', 'MISSING')}")
                print(f"✅ AI Coach assignment completed")
                print(f"   Worker ai_coach after assignment: {getattr(telemetry_monitor_worker, 'ai_coach', 'MISSING') is not None}")
                
            except Exception as assignment_error:
                logger.error(f"❌ [AI DEBUG] AI coach assignment failed: {assignment_error}")
                import traceback
                logger.error(f"❌ [AI DEBUG] Assignment traceback: {traceback.format_exc()}")
                print(f"❌ AI Coach assignment FAILED: {assignment_error}")
                traceback.print_exc()
                return False
            
            # Verify the AI coach loaded data successfully
            if not ai_coach_instance.superlap_points:
                logger.error(f"❌ AI Coach failed to load superlap data for ID: {superlap_id}")
                print(f"❌ AI Coach failed to load superlap data")
                return False
            
            logger.info(f"✅ AI Coach initialized with superlap_id: {superlap_id} ({len(ai_coach_instance.superlap_points)} points)")
            print(f"✅ AI Coach data validation passed ({len(ai_coach_instance.superlap_points)} points)")
            
            # Start monitoring to enable coaching
            logger.info(f"🤖 [AI COACH START] Starting telemetry monitoring (independent of lap saving)...")
            
            try:
                logger.info(f"🔧 [AI DEBUG] About to call start_monitoring()...")
                logger.info(f"🔧 [AI DEBUG] Worker is_monitoring before: {getattr(telemetry_monitor_worker, 'is_monitoring', 'MISSING')}")
                
                telemetry_monitor_worker.start_monitoring()
                
                logger.info(f"🔧 [AI DEBUG] start_monitoring() completed")
                logger.info(f"🔧 [AI DEBUG] Worker is_monitoring after: {getattr(telemetry_monitor_worker, 'is_monitoring', 'MISSING')}")
                print(f"✅ Monitoring started successfully")
                print(f"   Worker is_monitoring: {getattr(telemetry_monitor_worker, 'is_monitoring', 'MISSING')}")
                
            except Exception as monitoring_error:
                logger.error(f"❌ [AI DEBUG] start_monitoring() failed: {monitoring_error}")
                import traceback
                logger.error(f"❌ [AI DEBUG] Monitoring traceback: {traceback.format_exc()}")
                print(f"❌ start_monitoring() FAILED: {monitoring_error}")
                traceback.print_exc()
                return False
            
            logger.info("✅ AI coaching started - driver will receive real-time voice guidance")
            logger.info("🔧 [AI INDEPENDENT] AI coaching is now completely independent of lap saving")
            print("✅ AI coaching initialization COMPLETE!")
            
            # Final verification - test the unified callback conditions
            print(f"\n🔍 Step 6: Testing unified callback conditions...")
            has_worker = telemetry_monitor_worker is not None
            worker_exists = has_worker and telemetry_monitor_worker
            has_ai_coach = worker_exists and telemetry_monitor_worker.ai_coach
            is_monitoring = has_ai_coach and telemetry_monitor_worker.is_monitoring
            
            print(f"   has_worker: {has_worker}")
            print(f"   worker_exists: {worker_exists}")
            print(f"   has_ai_coach: {has_ai_coach}")
            print(f"   is_monitoring: {is_monitoring}")
            
            if has_worker and worker_exists and has_ai_coach and is_monitoring:
                print("✅ ALL CONDITIONS PASS - Telemetry should flow to AI coach!")
                return True
            else:
                print("❌ CONDITIONS FAIL - This is why AI coach doesn't get telemetry")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to start AI coaching: {e}")
            import traceback
            logger.error(traceback.format_exc())
            print(f"❌ Overall AI coaching setup FAILED: {e}")
            traceback.print_exc()
            return False
    
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting AI Coach initialization simulation...")
    success = simulate_ai_coach_initialization()
    print(f"\n{'='*60}")
    if success:
        print("🎉 SIMULATION PASSED - AI Coach should work in real app!")
    else:
        print("💔 SIMULATION FAILED - Found the exact problem!")
    print("="*60) 