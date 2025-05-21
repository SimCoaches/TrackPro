import threading
import queue
import logging
import time
from copy import deepcopy

# Setup logging
logger = logging.getLogger(__name__)

class ThreadedLapSaver:
    """
    Handles saving laps in a separate thread to prevent blocking telemetry collection.
    Works as a wrapper around the original IRacingLapSaver class.
    """
    def __init__(self, lap_saver):
        """
        Initialize the threaded saver with an existing lap saver instance.
        
        Args:
            lap_saver: The IRacingLapSaver instance to wrap
        """
        self.lap_saver = lap_saver
        self.save_queue = queue.Queue()
        self.save_thread = None
        self._stop_event = threading.Event()
        self._is_processing = False
        
        # Start the worker thread
        self._start_worker()
        
    def _start_worker(self):
        """Start the worker thread to process lap saves."""
        if self.save_thread is not None and self.save_thread.is_alive():
            logger.info("Save thread already running")
            return
            
        self._stop_event.clear()
        self.save_thread = threading.Thread(target=self._save_worker, daemon=True)
        self.save_thread.start()
        logger.info("Started lap save worker thread")
        
    def _save_worker(self):
        """Worker thread function for processing lap saves."""
        logger.info("Lap save worker thread started")
        while not self._stop_event.is_set():
            try:
                # Wait for items from the queue with a timeout
                try:
                    save_job = self.save_queue.get(timeout=1.0)
                    self._is_processing = True
                except queue.Empty:
                    continue
                
                # Process the save job
                logger.info(f"Processing lap save job: {save_job['type']}")
                
                if save_job['type'] == 'lap':
                    # Extract the job parameters
                    lap_number = save_job['lap_number']
                    lap_time = save_job['lap_time']
                    lap_frames = save_job['frames']
                    
                    # Call the original save method
                    start_time = time.time()
                    result = self.lap_saver._save_lap_data(lap_number, lap_time, lap_frames)
                    elapsed = time.time() - start_time
                    
                    logger.info(f"Lap {lap_number} save completed in {elapsed:.2f}s with result: {result}")
                    
                elif save_job['type'] == 'telemetry':
                    # Process telemetry directly
                    telemetry = save_job['telemetry']
                    self.lap_saver.process_telemetry(telemetry)
                    
                elif save_job['type'] == 'end_session':
                    # End session
                    result = self.lap_saver.end_session()
                    logger.info(f"Session end processed with result: {result}")
                    
                self.save_queue.task_done()
                self._is_processing = False
                
            except Exception as e:
                logger.error(f"Error in lap save worker: {e}", exc_info=True)
                self._is_processing = False
                # Continue processing other items
        
        logger.info("Lap save worker thread stopped")
        
    def process_telemetry(self, telemetry_data):
        """
        Process incoming telemetry data.
        
        This method both forwards the telemetry to the lap saver immediately 
        for lap detection and also queues any lap saves that are needed.
        
        Args:
            telemetry_data: Dictionary containing telemetry data
            
        Returns:
            Tuple of (is_new_lap, lap_number, lap_time) if a new lap is detected, None otherwise
        """
        # First, let the underlying lap_saver process the telemetry for lap detection
        # This call to process_telemetry will update the lap indexer but NOT save laps
        # as we're handling that in our threaded implementation
        self.lap_saver.lap_indexer.on_frame(telemetry_data)
        
        # Check if new laps are ready from lap indexer
        newly_completed_laps_from_indexer = self.lap_saver.lap_indexer.get_laps()
        
        # Filter for only laps that haven't been processed yet
        new_laps = []
        for indexed_lap in newly_completed_laps_from_indexer:
            sdk_lap_number = indexed_lap["lap_number_sdk"]
            if sdk_lap_number not in self.lap_saver._processed_lap_indexer_lap_numbers:
                new_laps.append(indexed_lap)
        
        # Queue any new laps for saving in the worker thread
        laps_to_return_to_ui = []
        for indexed_lap in new_laps:
            sdk_lap_number = indexed_lap["lap_number_sdk"]
            lap_duration = indexed_lap["duration_seconds"]
            lap_telemetry_frames = indexed_lap["telemetry_frames"]
            is_valid_from_indexer = indexed_lap.get("is_valid_from_sdk", True)
            
            if is_valid_from_indexer:
                logger.info(f"[ThreadedLapSaver] Queuing lap {sdk_lap_number} for saving (time: {lap_duration:.3f}s, {len(lap_telemetry_frames)} frames)")
                
                # Create a deep copy of the frames to ensure no interference
                frames_copy = deepcopy(lap_telemetry_frames)
                
                # Queue the lap for saving
                self.save_queue.put({
                    'type': 'lap',
                    'lap_number': sdk_lap_number,
                    'lap_time': lap_duration,
                    'frames': frames_copy
                })
                
                # Mark as processed immediately to avoid duplicate processing
                self.lap_saver._processed_lap_indexer_lap_numbers.add(sdk_lap_number)
                
                # Add to the list of laps to return to the UI
                laps_to_return_to_ui.append((True, sdk_lap_number, lap_duration))
            else:
                logger.info(f"[ThreadedLapSaver] Lap {sdk_lap_number} was marked invalid by LapIndexer. Skipping save.")
                self.lap_saver._processed_lap_indexer_lap_numbers.add(sdk_lap_number)
        
        # Return the first new lap info if any were detected
        if laps_to_return_to_ui:
            return laps_to_return_to_ui[0]
            
        return None
        
    def end_session(self):
        """End the current session and save any remaining lap data."""
        logger.info("[ThreadedLapSaver] Processing session end")
        
        # Call finalize on lap indexer directly to stop tracking
        self.lap_saver.lap_indexer.finalize()
        
        # Queue the session end job
        self.save_queue.put({
            'type': 'end_session'
        })
        
        return "Session end queued for processing"
        
    def shutdown(self):
        """Shut down the worker thread."""
        logger.info("Shutting down threaded lap saver")
        self._stop_event.set()
        
        # Wait for the worker thread to finish with a timeout
        if self.save_thread and self.save_thread.is_alive():
            logger.info("Waiting for lap save worker to finish...")
            self.save_thread.join(timeout=5.0)
            if self.save_thread.is_alive():
                logger.warning("Lap save worker did not finish in time")
                
        logger.info("Threaded lap saver shutdown complete")
        
    def start_session(self, track_name, car_name, session_type, track_id=None, car_id=None):
        """
        Start a new telemetry session.
        
        Args:
            track_name: The name of the track
            car_name: The name of the car
            session_type: The type of session (race, qualify, practice)
            track_id: Optional database ID of the track
            car_id: Optional database ID of the car
            
        Returns:
            str: The session ID
        """
        # Forward call directly to the wrapped lap saver
        if hasattr(self.lap_saver, 'start_session'):
            return self.lap_saver.start_session(track_name, car_name, session_type, track_id, car_id)
        return None
        
    def set_user_id(self, user_id):
        """Set the current user ID for associating data."""
        if hasattr(self.lap_saver, 'set_user_id'):
            self.lap_saver.set_user_id(user_id)
            logger.info(f"Forwarded user ID to wrapped lap saver: {user_id}")
            
    def set_supabase_client(self, client):
        """Set the Supabase client instance."""
        if hasattr(self.lap_saver, 'set_supabase_client'):
            self.lap_saver.set_supabase_client(client)
            logger.info(f"Forwarded Supabase client to wrapped lap saver")
            
    def __del__(self):
        """Ensure worker thread is stopped when object is deleted."""
        try:
            self.shutdown()
        except:
            pass 