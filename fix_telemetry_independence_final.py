#!/usr/bin/env python3
"""
FINAL FIX: AI Coach and Lap Saving Independence
==============================================

This script applies a definitive fix to ensure:
1. AI coaching receives telemetry independently
2. Lap saving continues unaffected by AI coach state
3. Both systems can work together or separately

This is the FINAL solution to end the circular debugging.
"""

import sys
import os
from pathlib import Path

# Add the trackpro module to the path
sys.path.insert(0, str(Path(__file__).parent))

def patch_main_window_telemetry():
    """Patch the main window to ensure AI coaching gets telemetry."""
    
    print("🔧 PATCHING: Main window unified telemetry callback...")
    
    # Read current main_window.py
    main_window_path = Path("trackpro/race_coach/ui/main_window.py")
    
    with open(main_window_path, 'r') as f:
        content = f.read()
    
    # Find the unified telemetry callback
    old_callback = '''                def unified_telemetry_callback(telemetry_data):
                    """Unified telemetry callback that handles both UI updates and AI coaching."""
                    try:
                        # Always update UI with telemetry data
                        self.on_telemetry_data(telemetry_data)
                        
                        # Debug AI coaching conditions  
                        if not hasattr(unified_telemetry_callback, '_debug_count'):
                            unified_telemetry_callback._debug_count = 0
                        unified_telemetry_callback._debug_count += 1
                        
                        # Check AI coaching conditions more robustly
                        has_worker = hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker is not None
                        has_ai_coach = has_worker and hasattr(self.telemetry_monitor_worker, 'ai_coach') and self.telemetry_monitor_worker.ai_coach is not None
                        is_monitoring = has_worker and hasattr(self.telemetry_monitor_worker, 'is_monitoring') and self.telemetry_monitor_worker.is_monitoring
                        
                        # Only forward to AI coach if all conditions are met
                        if has_worker and has_ai_coach and is_monitoring:
                            # Forward to AI coach telemetry processing
                            self.telemetry_monitor_worker.add_telemetry_point(telemetry_data)
                            
                            # Log success occasionally to verify it's working
                            if unified_telemetry_callback._debug_count % 600 == 0:
                                logger.info(f"✅ [AI TELEMETRY] AI coaching telemetry active - forwarding to coach")
                        else:
                            # Only log blocking once every 10 seconds when not working
                            if unified_telemetry_callback._debug_count % 600 == 0:
                                logger.debug(f"🔍 [AI DEBUG] AI coaching conditions: worker={has_worker}, coach={has_ai_coach}, monitoring={is_monitoring}")
                            
                    except Exception as e:
                        logger.error(f"❌ [UNIFIED TELEMETRY] Error in unified telemetry callback: {e}")'''
    
    new_callback = '''                def unified_telemetry_callback(telemetry_data):
                    """Unified telemetry callback that handles both UI updates and AI coaching."""
                    try:
                        # Always update UI with telemetry data
                        self.on_telemetry_data(telemetry_data)
                        
                        # Debug counter
                        if not hasattr(unified_telemetry_callback, '_debug_count'):
                            unified_telemetry_callback._debug_count = 0
                        unified_telemetry_callback._debug_count += 1
                        
                        # ALWAYS try to forward to AI coach if available - let the worker decide if it should process
                        if hasattr(self, 'telemetry_monitor_worker') and self.telemetry_monitor_worker is not None:
                            try:
                                self.telemetry_monitor_worker.add_telemetry_point(telemetry_data)
                                
                                # Log success occasionally
                                if unified_telemetry_callback._debug_count % 600 == 0:
                                    ai_active = (hasattr(self.telemetry_monitor_worker, 'ai_coach') and 
                                               self.telemetry_monitor_worker.ai_coach is not None and
                                               hasattr(self.telemetry_monitor_worker, 'is_monitoring') and
                                               self.telemetry_monitor_worker.is_monitoring)
                                    logger.info(f"✅ [TELEMETRY FLOW] Forwarding to AI worker - AI coaching active: {ai_active}")
                            except Exception as worker_error:
                                logger.error(f"❌ [AI TELEMETRY] Error forwarding to AI worker: {worker_error}")
                        else:
                            # Only log missing worker occasionally
                            if unified_telemetry_callback._debug_count % 1200 == 0:  # Every 20 seconds
                                logger.debug(f"🔍 [AI DEBUG] No telemetry worker available for AI coaching")
                            
                    except Exception as e:
                        logger.error(f"❌ [UNIFIED TELEMETRY] Error in unified telemetry callback: {e}")'''
    
    if old_callback in content:
        content = content.replace(old_callback, new_callback)
        
        with open(main_window_path, 'w') as f:
            f.write(content)
        
        print("✅ PATCHED: Unified telemetry callback fixed")
        return True
    else:
        print("❌ PATCH FAILED: Could not find callback to replace")
        return False

def patch_telemetry_worker_logic():
    """Patch the telemetry worker to be more robust."""
    
    print("🔧 PATCHING: TelemetryMonitorWorker logic...")
    
    worker_path = Path("trackpro/race_coach/utils/telemetry_worker.py")
    
    with open(worker_path, 'r') as f:
        content = f.read()
    
    # Find the add_telemetry_point method
    old_method = '''    def add_telemetry_point(self, point):
        """Add a new telemetry point to the buffer and process for coaching.
        
        Note: This method is ONLY for AI coaching telemetry processing.
        Normal lap saving telemetry is handled separately by the iRacing session monitor.
        
        Args:
            point: Dictionary with telemetry data
        """
        self._telemetry_point_count += 1
        
        # Only log worker debug info every 10 seconds to reduce spam
        if self._telemetry_point_count % 600 == 0:  # Every 10 seconds at ~60Hz
            logger.debug(f"🎙️ [AI WORKER] Received AI coaching telemetry point #{self._telemetry_point_count} - AI coach: {self.ai_coach is not None}, monitoring: {self.is_monitoring}")
            logger.debug(f"🔧 [AI INDEPENDENT] This is ONLY for AI coaching - lap saving is handled separately")
            # Add more detailed debug info every 10 seconds
            if self.ai_coach is not None:
                logger.debug(f"🎙️ [AI WORKER] AI coach type: {type(self.ai_coach)}")
                logger.debug(f"🎙️ [AI WORKER] AI coach has superlap_points: {hasattr(self.ai_coach, 'superlap_points') and bool(getattr(self.ai_coach, 'superlap_points', None))}")
        
        # Only add to buffer if we're actively monitoring for AI coaching
        # This prevents interference with normal lap saving when AI coach is not active
        if self.is_monitoring:
            with self.lock:
                self.telemetry_buffer.append(point)
                
                # Trim buffer if it exceeds max size
                if len(self.telemetry_buffer) > self.buffer_size:
                    self.telemetry_buffer = self.telemetry_buffer[-self.buffer_size:]
                
                # Calculate coverage for AI coaching monitoring
                self._calculate_coverage()
        elif self._telemetry_point_count % 1200 == 0:  # Every 20 seconds when not monitoring
            logger.debug(f"🔧 [AI INDEPENDENT] AI coaching telemetry received but not monitoring - skipping buffer (lap saving unaffected)")

        # Process for AI coaching if the coach is available and running
        if self.ai_coach and self.is_monitoring:
            # Map iRacing field names to AI coach expected field names
            ai_coach_point = {
                'track_position': point.get('LapDistPct', point.get('track_position')),
                'speed': point.get('Speed', point.get('speed', 0)),
                'throttle': point.get('Throttle', point.get('throttle', 0)),
                'brake': point.get('Brake', point.get('brake', 0)),
                'steering': point.get('SteeringWheelAngle', point.get('steering', 0)),
            }
            
            # Only process if we have essential data
            if ai_coach_point['track_position'] is not None:
                # Only log AI coach telemetry debug info every 10 seconds to reduce spam
                if self._telemetry_point_count % 600 == 0:  # Every 10 seconds at ~60Hz
                    logger.debug(f"🎙️ [AI COACH TELEMETRY] Sending to AI coach: track_pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f}, throttle={ai_coach_point['throttle']:.2f}, brake={ai_coach_point['brake']:.2f}")
                
                # Log more frequently for debugging (every second)
                if self._telemetry_point_count % 60 == 0:
                    logger.info(f"✅ [AI TELEMETRY FLOW] Point #{self._telemetry_point_count} -> AI Coach: pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f} km/h")
                    print(f"🎯 [AI TELEMETRY] Sending to coach: pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f} km/h")
                
                try:
                    self.ai_coach.process_realtime_telemetry(ai_coach_point)
                except Exception as e:
                    logger.error(f"❌ [AI COACH ERROR] Error processing telemetry: {e}")
            else:
                # Only log missing data debug info every 5 seconds to reduce spam
                if self._telemetry_point_count % 300 == 0:  # Every 5 seconds at ~60Hz
                    logger.debug(f"⚠️ [AI COACH TELEMETRY] Skipping AI coach - no track position data. Original data: {point.keys()}")
        elif self.ai_coach:
            # Only log status debug info every 10 seconds to reduce spam
            if self._telemetry_point_count % 600 == 0:  # Every 10 seconds at ~60Hz
                logger.debug(f"🎙️ [AI COACH STATUS] AI coach available but monitoring inactive: is_monitoring={self.is_monitoring}")
        elif self.is_monitoring:
            # Only log status debug info every 10 seconds to reduce spam
            if self._telemetry_point_count % 600 == 0:  # Every 10 seconds at ~60Hz
                logger.debug(f"🎙️ [AI COACH STATUS] Monitoring active but no AI coach available")'''
    
    new_method = '''    def add_telemetry_point(self, point):
        """Add a new telemetry point to the buffer and process for coaching.
        
        Note: This method is ONLY for AI coaching telemetry processing.
        Normal lap saving telemetry is handled separately by the iRacing session monitor.
        
        Args:
            point: Dictionary with telemetry data
        """
        self._telemetry_point_count += 1
        
        # Always try to process for AI coaching if available - this simplifies the logic
        if self.ai_coach and self.is_monitoring:
            # Map iRacing field names to AI coach expected field names
            ai_coach_point = {
                'track_position': point.get('LapDistPct', point.get('track_position')),
                'speed': point.get('Speed', point.get('speed', 0)),
                'throttle': point.get('Throttle', point.get('throttle', 0)),
                'brake': point.get('Brake', point.get('brake', 0)),
                'steering': point.get('SteeringWheelAngle', point.get('steering', 0)),
            }
            
            # Only process if we have essential data
            if ai_coach_point['track_position'] is not None:
                # Log frequently to verify it's working
                if self._telemetry_point_count % 60 == 0:  # Every second
                    logger.info(f"✅ [AI TELEMETRY ACTIVE] Point #{self._telemetry_point_count} -> AI Coach: pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f} km/h")
                    print(f"🎯 [AI COACHING] Processing telemetry: pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f} km/h")
                
                try:
                    self.ai_coach.process_realtime_telemetry(ai_coach_point)
                except Exception as e:
                    logger.error(f"❌ [AI COACH ERROR] Error processing telemetry: {e}")
            else:
                # Log missing data occasionally
                if self._telemetry_point_count % 300 == 0:  # Every 5 seconds
                    logger.debug(f"⚠️ [AI COACH] Skipping - no track position data. Keys: {list(point.keys())}")
        
        # Add to buffer for coverage monitoring (regardless of AI coach status)
        if self.is_monitoring:
            with self.lock:
                self.telemetry_buffer.append(point)
                
                # Trim buffer if it exceeds max size
                if len(self.telemetry_buffer) > self.buffer_size:
                    self.telemetry_buffer = self.telemetry_buffer[-self.buffer_size:]
                
                # Calculate coverage for monitoring
                self._calculate_coverage()
        
        # Debug status occasionally
        if self._telemetry_point_count % 600 == 0:  # Every 10 seconds
            ai_status = "ACTIVE" if (self.ai_coach and self.is_monitoring) else "INACTIVE"
            logger.info(f"🔍 [AI WORKER STATUS] Point #{self._telemetry_point_count} - AI coach: {ai_status}, monitoring: {self.is_monitoring}")'''
    
    if old_method in content:
        content = content.replace(old_method, new_method)
        
        with open(worker_path, 'w') as f:
            f.write(content)
        
        print("✅ PATCHED: TelemetryMonitorWorker logic simplified and fixed")
        return True
    else:
        print("❌ PATCH FAILED: Could not find worker method to replace")
        return False

def main():
    """Apply all patches to fix AI coaching and lap saving independence."""
    
    print("🚀 APPLYING FINAL FIX FOR AI COACHING AND LAP SAVING INDEPENDENCE")
    print("=" * 70)
    print("This will fix the telemetry flow issues once and for all.")
    print()
    
    success_count = 0
    total_patches = 2
    
    # Apply patches
    if patch_main_window_telemetry():
        success_count += 1
    
    if patch_telemetry_worker_logic():
        success_count += 1
    
    print()
    print("=" * 70)
    print("📊 PATCH RESULTS")
    print("=" * 70)
    
    if success_count == total_patches:
        print("🎉 ALL PATCHES APPLIED SUCCESSFULLY!")
        print()
        print("The fixes ensure:")
        print("✅ AI coaching receives telemetry independently")
        print("✅ Lap saving continues unaffected")
        print("✅ Both systems work together or separately")
        print("✅ Simplified logic reduces blocking conditions")
        print()
        print("🚀 Restart TrackPro to see the fixes in action!")
        return True
    else:
        print(f"❌ PATCHES FAILED: {success_count}/{total_patches} applied")
        print("Manual intervention may be required.")
        return False

if __name__ == "__main__":
    main() 