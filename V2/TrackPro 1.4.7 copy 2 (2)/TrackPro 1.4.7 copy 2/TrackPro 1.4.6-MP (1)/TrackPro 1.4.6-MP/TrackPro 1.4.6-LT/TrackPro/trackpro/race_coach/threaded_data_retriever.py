import threading
import queue
import logging
import time
from PyQt5.QtCore import QObject, pyqtSignal

# Setup logging
logger = logging.getLogger(__name__)

class ThreadedDataRetriever(QObject):
    """
    A threaded wrapper for retrieving data from Supabase.
    Handles fetching telemetry data, sessions, and laps in a separate thread to prevent UI freezes.
    """
    # Define signals for callbacks
    telemetry_fetched = pyqtSignal(str, object, str)  # lap_id, data, message
    laps_fetched = pyqtSignal(str, object, str)       # session_id, data, message
    sessions_fetched = pyqtSignal(object, str)        # data, message
    error = pyqtSignal(str, str, str)                 # operation_type, details, message
    
    def __init__(self):
        """Initialize the threaded data retriever."""
        super().__init__()
        self.fetch_queue = queue.Queue()
        self.fetch_thread = None
        self._stop_event = threading.Event()
        self._is_processing = False
        
        # Start the worker thread
        self._start_worker()
        
    def _start_worker(self):
        """Start the worker thread to process data fetch requests."""
        if self.fetch_thread is not None and self.fetch_thread.is_alive():
            logger.info("Fetch thread already running")
            return
            
        self._stop_event.clear()
        self.fetch_thread = threading.Thread(target=self._fetch_worker, daemon=True)
        self.fetch_thread.start()
        logger.info("Started data retrieval worker thread")
        
    def _fetch_worker(self):
        """Worker thread function for processing data fetches."""
        logger.info("Data retrieval worker thread started")
        while not self._stop_event.is_set():
            try:
                # Wait for items from the queue with a timeout
                try:
                    fetch_job = self.fetch_queue.get(timeout=1.0)
                    self._is_processing = True
                except queue.Empty:
                    self._is_processing = False # Ensure this is reset
                    continue
                
                # Process the fetch job
                logger.info(f"Processing data fetch job: {fetch_job['type']}")
                
                if fetch_job['type'] == 'telemetry':
                    # Extract the job parameters
                    lap_id = fetch_job['lap_id']
                    columns = fetch_job.get('columns')
                    track_length = fetch_job.get('track_length', 0) # Get track_length
                    
                    # Call the data retrieval function
                    try:
                        from Supabase.database import get_telemetry_points
                        data, message = get_telemetry_points(lap_id, columns)
                        if data is not None:
                            logger.info(f"Telemetry fetch for lap {lap_id} completed with {len(data)} points")
                            # Calculate LapDist if missing and track_length is valid
                            if track_length > 0:
                                for point in data:
                                    if 'LapDist' not in point and 'track_position' in point:
                                        try:
                                            # Ensure track_position is float before multiplication
                                            track_pos_float = float(point['track_position'])
                                            point['LapDist'] = track_pos_float * track_length
                                        except (TypeError, ValueError) as e:
                                            logger.warning(f"Could not calculate LapDist for point with timestamp {point.get('timestamp', 'N/A')} in lap {lap_id}: Invalid track_position '{point['track_position']}'. Error: {e}")
                                    elif 'LapDist' not in point: # If LapDist still missing (e.g. track_position was missing)
                                        logger.debug(f"Point with timestamp {point.get('timestamp', 'N/A')} in lap {lap_id} missing 'LapDist' and 'track_position' for calculation.")
                            elif columns and 'track_position' in columns and 'LapDist' not in columns: # Only warn if track_position was requested but track_length is invalid
                                logger.warning(f"track_length is not positive ({track_length}) for lap {lap_id}. Cannot calculate LapDist.")
                                
                                # Even with invalid track_length, create a fallback LapDist using a default scale
                                # to ensure data can still be displayed. This prevents "all\invalid" in the graphs.
                                fallback_track_length = 1000.0  # Use 1km as a reasonable fallback for any track
                                logger.info(f"Using fallback track_length of {fallback_track_length}m to enable data display")
                                
                                for point in data:
                                    if 'LapDist' not in point and 'track_position' in point:
                                        try:
                                            track_pos_float = float(point['track_position'])
                                            point['LapDist'] = track_pos_float * fallback_track_length
                                            # Mark this as a fallback calculation
                                            point['LapDist_fallback'] = True
                                        except (TypeError, ValueError):
                                            pass  # Already logged above, just continue

                            self.telemetry_fetched.emit(lap_id, data, message)
                        else:
                            logger.warning(f"Failed to fetch telemetry for lap {lap_id}: {message}")
                            self.error.emit('telemetry', lap_id, message)
                    except Exception as e:
                        logger.error(f"Exception fetching telemetry for lap {lap_id}: {e}", exc_info=True)
                        self.error.emit('telemetry', lap_id, str(e))
                    
                elif fetch_job['type'] == 'laps':
                    # Extract the job parameters
                    session_id = fetch_job['session_id']
                    limit = fetch_job.get('limit', 50)
                    user_only = fetch_job.get('user_only', True)
                    
                    # Call the data retrieval function
                    try:
                        from Supabase.database import get_laps
                        data, message = get_laps(limit, user_only, session_id)
                        if data is not None:
                            logger.info(f"Laps fetch for session {session_id} completed with {len(data)} laps")
                            self.laps_fetched.emit(session_id, data, message)
                        else:
                            logger.warning(f"Failed to fetch laps for session {session_id}: {message}")
                            self.error.emit('laps', session_id, message)
                    except Exception as e:
                        logger.error(f"Exception fetching laps for session {session_id}: {e}", exc_info=True)
                        self.error.emit('laps', session_id, str(e))
                    
                elif fetch_job['type'] == 'sessions':
                    # Extract the job parameters
                    limit = fetch_job.get('limit', 50)
                    user_only = fetch_job.get('user_only', True)
                    
                    # Call the data retrieval function
                    try:
                        from Supabase.database import get_sessions
                        data, message = get_sessions(limit, user_only)
                        if data is not None:
                            logger.info(f"Sessions fetch completed with {len(data)} sessions")
                            self.sessions_fetched.emit(data, message)
                        else:
                            logger.warning(f"Failed to fetch sessions: {message}")
                            self.error.emit('sessions', '', message)
                    except Exception as e:
                        logger.error(f"Exception fetching sessions: {e}", exc_info=True)
                        self.error.emit('sessions', '', str(e))
                
                self.fetch_queue.task_done()
                self._is_processing = False
                
            except Exception as e: # Catch broader exceptions in the worker loop
                logger.error(f"Critical error in data fetch worker loop: {e}", exc_info=True)
                self._is_processing = False # Reset processing flag
                # Optionally, re-raise or handle specific errors if needed, otherwise continue
                if fetch_job: # If a job was fetched, mark it done to prevent blocking
                    self.fetch_queue.task_done()

        logger.info("Data fetch worker thread stopped")
    
    def fetch_telemetry(self, lap_id, columns=None, track_length=0):
        """
        Queue a request to fetch telemetry points for a lap.
        
        Args:
            lap_id: ID of the lap to fetch telemetry for
            columns: Optional list of column names to fetch
            track_length: The length of the track in meters for LapDist calculation
            
        Returns:
            True if request was queued successfully
        """
        if not lap_id:
            logger.warning("Cannot fetch telemetry: No lap ID provided")
            return False
            
        logger.info(f"Queueing telemetry fetch for lap {lap_id} with track_length {track_length}")
        self.fetch_queue.put({
            'type': 'telemetry',
            'lap_id': lap_id,
            'columns': columns,
            'track_length': track_length # Add track_length to the job
        })
        return True
        
    def fetch_telemetry_for_comparison(self, lap_a_id, lap_b_id, track_length=0):
        """
        Queue requests to fetch telemetry points for two laps for comparison.
        
        Args:
            lap_a_id: ID of the first lap to fetch telemetry for
            lap_b_id: ID of the second lap to fetch telemetry for
            track_length: The length of the track in meters for LapDist calculation
            
        Returns:
            True if requests were queued successfully
        """
        if not lap_a_id or not lap_b_id:
            logger.warning(f"Cannot fetch telemetry for comparison: Missing lap ID (A: {lap_a_id}, B: {lap_b_id})")
            return False
            
        # Validate track_length - if invalid, use a default value
        if track_length <= 0:
            track_length = 1000.0  # Use 1km as a reasonable fallback
            logger.warning(f"Invalid track_length ({track_length}) for comparison. Using fallback value of {track_length}m")
        
        # Always log the track_length being used to help with debugging
        logger.info(f"Queueing telemetry fetch for comparison - Lap A: {lap_a_id}, Lap B: {lap_b_id} with track_length {track_length}")
        
        # Required columns for comparison
        columns = ["timestamp", "throttle", "brake", "track_position", "steering", "speed"]
        
        # Queue both requests
        success_a = self.fetch_telemetry(lap_a_id, columns=columns, track_length=track_length)
        success_b = self.fetch_telemetry(lap_b_id, columns=columns, track_length=track_length)
        
        return success_a and success_b
        
    def fetch_laps(self, session_id, limit=50, user_only=True):
        """
        Queue a request to fetch laps for a session.
        
        Args:
            session_id: ID of the session to fetch laps for
            limit: Maximum number of laps to fetch
            user_only: Whether to fetch only laps belonging to the current user
            
        Returns:
            True if request was queued successfully
        """
        if not session_id:
            logger.warning("Cannot fetch laps: No session ID provided")
            return False
            
        logger.info(f"Queueing laps fetch for session {session_id}")
        self.fetch_queue.put({
            'type': 'laps',
            'session_id': session_id,
            'limit': limit,
            'user_only': user_only
        })
        return True
        
    def fetch_sessions(self, limit=50, user_only=True):
        """
        Queue a request to fetch sessions.
        
        Args:
            limit: Maximum number of sessions to fetch
            user_only: Whether to fetch only sessions belonging to the current user
            
        Returns:
            True if request was queued successfully
        """
        logger.info("Queueing sessions fetch")
        self.fetch_queue.put({
            'type': 'sessions',
            'limit': limit,
            'user_only': user_only
        })
        return True
        
    def shutdown(self):
        """Shut down the worker thread."""
        logger.info("Shutting down threaded data retriever")
        self._stop_event.set()
        
        # Wait for the worker thread to finish with a timeout
        if self.fetch_thread and self.fetch_thread.is_alive():
            # Check if we are trying to join the current thread
            if threading.current_thread().ident == self.fetch_thread.ident:
                logger.warning("Shutdown called from within the fetch worker thread. Skipping join.")
            else:
                logger.info("Waiting for data fetch worker to finish...")
                self.fetch_thread.join(timeout=5.0) # Increased timeout slightly
                if self.fetch_thread.is_alive():
                    logger.warning("Data fetch worker did not finish in time")
                else:
                    logger.info("Data fetch worker finished.")
        else:
            logger.info("Data fetch worker thread was not running or already finished.")
                
        logger.info("Threaded data retriever shutdown complete")
        
    def __del__(self):
        """Ensure worker thread is stopped when object is deleted."""
        try:
            # Only call shutdown if the event loop is still running or thread exists
            if not self._stop_event.is_set() and self.fetch_thread and self.fetch_thread.is_alive():
                self.shutdown()
        except Exception as e: # Broad catch for cleanup
            # Avoid raising exceptions during __del__
            # logger.error(f"Error during ThreadedDataRetriever __del__: {e}", exc_info=False) # Optional logging
            pass 