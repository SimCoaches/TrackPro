#!/usr/bin/env python3
"""
TrackPro Immediate Lap Save Integration

This script demonstrates how to integrate the new immediate lap saving system
with the existing IRacingLapSaver, completely eliminating the N+1 polling lag.

BEFORE (LAGGY):
IRacingLapSaver.process_telemetry() → lap_indexer.on_frame() → lap_indexer.get_laps() → process new laps

AFTER (IMMEDIATE):
lap_indexer.on_frame() → IMMEDIATE CALLBACK → IRacingLapSaver._save_lap_data() → Supabase

This eliminates the polling delay and ensures laps are saved the instant they complete.
"""

import logging
from typing import Dict, Any

# Setup logging  
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImmediateLapSaverIntegration:
    """
    Integration wrapper that connects LapIndexer immediate saving to IRacingLapSaver.
    
    This class acts as a bridge between the new immediate saving system and 
    the existing TrackPro lap saving infrastructure.
    """
    
    def __init__(self, lap_indexer, iracing_lap_saver):
        """
        Initialize the integration.
        
        Args:
            lap_indexer: The LapIndexer instance with immediate saving capability
            iracing_lap_saver: The existing IRacingLapSaver instance
        """
        self.lap_indexer = lap_indexer
        self.iracing_lap_saver = iracing_lap_saver
        
        # Statistics
        self.immediate_saves_processed = 0
        self.immediate_saves_successful = 0
        self.immediate_saves_failed = 0
        
        logger.info("🔌 Immediate Lap Save Integration initialized")
        
    def setup_immediate_saving(self):
        """
        Wire up the immediate saving system.
        
        This replaces the old polling system with immediate callbacks.
        """
        # 1. Set up the immediate save callback
        self.lap_indexer.set_immediate_save_callback(self._immediate_save_callback)
        
        # 2. Start the background save worker
        self.lap_indexer.start_save_worker()
        
        # 3. Disable the old polling system in IRacingLapSaver (optional)
        if hasattr(self.iracing_lap_saver, '_use_immediate_saving'):
            self.iracing_lap_saver._use_immediate_saving = True
            
        logger.info("✅ Immediate saving system activated")
        logger.info("📈 Benefits: Zero lag, perfect synchronization, no N+1 dependency")
        
    def _immediate_save_callback(self, lap_data: Dict[str, Any]) -> None:
        """
        Immediate callback that gets triggered when a lap completes.
        
        This is called by the LapIndexer immediately when a lap finishes,
        eliminating the polling delay that caused synchronization issues.
        
        Args:
            lap_data: Complete lap dictionary with all telemetry data
        """
        try:
            self.immediate_saves_processed += 1
            
            # Extract key information
            lap_number = lap_data.get("lap_number_sdk", -1)
            lap_time = lap_data.get("duration_seconds", 0.0)
            lap_state = lap_data.get("lap_state", "UNKNOWN")
            frame_count = len(lap_data.get("telemetry_frames", []))
            
            logger.info(f"⚡ IMMEDIATE SAVE: Lap {lap_number} ({lap_state}) - {lap_time:.3f}s, {frame_count} frames")
            
            # CRITICAL: Use the existing IRacingLapSaver._save_lap_data method
            # This preserves all existing validation, session tracking, and Supabase logic
            success = self._save_via_existing_saver(lap_data)
            
            if success:
                self.immediate_saves_successful += 1
                logger.info(f"✅ IMMEDIATE SAVE SUCCESS: Lap {lap_number}")
            else:
                self.immediate_saves_failed += 1
                logger.error(f"❌ IMMEDIATE SAVE FAILED: Lap {lap_number}")
                
        except Exception as e:
            self.immediate_saves_failed += 1
            logger.error(f"💥 IMMEDIATE SAVE ERROR: {e}", exc_info=True)
            
    def _save_via_existing_saver(self, lap_data: Dict[str, Any]) -> bool:
        """
        Save lap using the existing IRacingLapSaver infrastructure.
        
        This method interfaces with the existing lap saver to maintain
        all current functionality while using immediate triggering.
        
        Args:
            lap_data: Complete lap data from LapIndexer
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Extract the necessary data for the existing saver
            lap_number = lap_data["lap_number_sdk"]
            lap_time = lap_data["duration_seconds"] 
            lap_frames = lap_data["telemetry_frames"]
            
            # Ensure session is set up
            if not self.iracing_lap_saver._current_session_id:
                logger.warning(f"No active session for immediate save of lap {lap_number}")
                return False
                
            # CRITICAL: Use the existing _save_lap_data method to maintain all logic
            # This includes session tracking, car/track association, validation, etc.
            saved_lap_id = self.iracing_lap_saver._save_lap_data(
                lap_number=lap_number,
                lap_time=lap_time, 
                lap_frames_from_indexer=lap_frames
            )
            
            if saved_lap_id:
                # Update the saver's internal tracking (thread-safe)
                self.iracing_lap_saver._mark_lap_as_processed(lap_number, success=True)
                
                # Update statistics
                self.iracing_lap_saver._total_laps_saved += 1
                
                return True
            else:
                # Mark as failed for retry handling
                self.iracing_lap_saver._mark_lap_as_processed(lap_number, success=False)
                return False
                
        except Exception as e:
            logger.error(f"Error in existing saver interface: {e}", exc_info=True)
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "immediate_saves_processed": self.immediate_saves_processed,
            "immediate_saves_successful": self.immediate_saves_successful, 
            "immediate_saves_failed": self.immediate_saves_failed,
            "success_rate": (self.immediate_saves_successful / max(1, self.immediate_saves_processed)) * 100,
            "indexer_stats": {
                "worker_running": self.lap_indexer._save_worker_running,
                "queue_size": self.lap_indexer._immediate_save_queue.qsize()
            }
        }
    
    def shutdown(self):
        """Clean shutdown of immediate saving system."""
        logger.info("🛑 Shutting down immediate save integration")
        
        # Stop the immediate save worker
        self.lap_indexer.stop_save_worker()
        
        # Log final statistics
        stats = self.get_statistics()
        logger.info(f"📊 Final stats: {stats['immediate_saves_successful']}/{stats['immediate_saves_processed']} "
                   f"saves successful ({stats['success_rate']:.1f}%)")
        
        logger.info("✅ Immediate save integration shutdown complete")


def integrate_immediate_saving(lap_indexer, iracing_lap_saver):
    """
    Main integration function - call this to set up immediate saving.
    
    Args:
        lap_indexer: Your LapIndexer instance
        iracing_lap_saver: Your IRacingLapSaver instance
        
    Returns:
        ImmediateLapSaverIntegration instance for monitoring and control
    """
    logger.info("🚀 INTEGRATING IMMEDIATE LAP SAVING SYSTEM")
    logger.info("🔧 This will eliminate N+1 polling lag and ensure perfect synchronization")
    
    # Create the integration
    integration = ImmediateLapSaverIntegration(lap_indexer, iracing_lap_saver)
    
    # Set up immediate saving
    integration.setup_immediate_saving()
    
    logger.info("🎉 IMMEDIATE SAVING INTEGRATION COMPLETE!")
    logger.info("💡 Laps will now save instantly when they complete")
    
    return integration


if __name__ == "__main__":
    print("""
    🔌 TrackPro Immediate Lap Save Integration
    ==========================================
    
    This script demonstrates how to integrate immediate lap saving
    with your existing IRacingLapSaver to eliminate polling lag.
    
    USAGE:
    ------
    from iracing_lap_saver_immediate_integration import integrate_immediate_saving
    
    # Your existing instances
    lap_indexer = LapIndexer()
    iracing_lap_saver = IRacingLapSaver()
    
    # Integrate immediate saving
    integration = integrate_immediate_saving(lap_indexer, iracing_lap_saver)
    
    # Your normal telemetry processing
    while racing:
        telemetry = get_iracing_data()
        lap_indexer.on_frame(telemetry)  # Laps save immediately!
        
    # Clean shutdown
    integration.shutdown()
    
    🎉 BENEFITS:
    -----------
    ✅ Zero lag - laps save instantly when completed
    ✅ Perfect synchronization with iRacing lap timing
    ✅ No more frame assignment to wrong laps  
    ✅ Maintains all existing validation and session logic
    ✅ Thread-safe background processing
    ✅ Compatible with existing TrackPro infrastructure
    """) 