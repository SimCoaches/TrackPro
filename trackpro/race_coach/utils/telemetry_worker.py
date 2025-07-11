import logging
import threading
import queue
import time
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from trackpro.race_coach.utils.telemetry_validation import validate_lap_telemetry
from trackpro.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class TelemetrySaveWorker(QObject):
    """Worker for processing and saving telemetry data with validation."""
    
    # Signal emitted when save operation completes
    finished = pyqtSignal(bool, str, object)  # success, message, diagnostics
    
    # Signal for progress updates
    progress = pyqtSignal(int, str)  # percentage, status message
    
    def __init__(self, lap_data, telemetry_points):
        """Initialize the worker with lap data and telemetry points.
        
        Args:
            lap_data: Dictionary with lap header information
            telemetry_points: List of telemetry data points
        """
        super().__init__()
        self.lap_data = lap_data
        self.telemetry_points = telemetry_points
        self.is_cancelled = False
    
    def run(self):
        """Run the telemetry processing and saving operation."""
        try:
            self.progress.emit(10, "Validating telemetry data...")
            
            # Validate telemetry coverage
            is_valid, message, diagnostics = validate_lap_telemetry(self.telemetry_points)
            
            if not is_valid:
                logger.warning(f"Lap validation failed: {message}")
                self.finished.emit(False, message, diagnostics)
                return
                
            if self.is_cancelled:
                self.finished.emit(False, "Operation cancelled", None)
                return
                
            # Get Supabase client
            self.progress.emit(30, "Connecting to database...")
            client = get_supabase_client()
            
            if not client:
                logger.error("Failed to get Supabase client")
                self.finished.emit(False, "Database connection failed", None)
                return
            
            if self.is_cancelled:
                self.finished.emit(False, "Operation cancelled", None)
                return
                
            # Save lap header
            self.progress.emit(50, "Saving lap data...")
            
            # Add validation metadata to lap data
            self.lap_data['is_complete'] = True
            self.lap_data['validation_status'] = message
            
            try:
                # Insert lap and get back the ID
                response = client.table('laps').insert(self.lap_data).execute()
                
                if not response.data or len(response.data) == 0:
                    logger.error("Failed to save lap: No response data")
                    self.finished.emit(False, "Failed to save lap data", None)
                    return
                    
                lap_id = response.data[0].get('id')
                
                if not lap_id:
                    logger.error("Failed to save lap: No lap ID returned")
                    self.finished.emit(False, "Failed to get lap ID", None)
                    return
                    
            except Exception as e:
                logger.error(f"Error saving lap data: {e}")
                self.finished.emit(False, f"Error saving lap: {str(e)}", None)
                return
                
            if self.is_cancelled:
                # Try to delete the partial lap if cancelled mid-operation
                try:
                    client.table('laps').delete().eq('id', lap_id).execute()
                except:
                    pass
                self.finished.emit(False, "Operation cancelled", None)
                return
                
            # Save telemetry points in batches
            self.progress.emit(70, "Saving telemetry points...")
            
            # Prepare telemetry points with lap_id
            for point in self.telemetry_points:
                point['lap_id'] = lap_id
                
            # Save in batches of 100 points
            batch_size = 100
            num_batches = (len(self.telemetry_points) + batch_size - 1) // batch_size
            
            for i in range(num_batches):
                if self.is_cancelled:
                    # Try to delete the partial data
                    try:
                        client.table('telemetry_points').delete().eq('lap_id', lap_id).execute()
                        client.table('laps').delete().eq('id', lap_id).execute()
                    except:
                        pass
                    self.finished.emit(False, "Operation cancelled", None)
                    return
                    
                batch = self.telemetry_points[i * batch_size:(i + 1) * batch_size]
                
                try:
                    client.table('telemetry_points').insert(batch).execute()
                    progress = 70 + (i + 1) * 25 // num_batches
                    self.progress.emit(progress, f"Saving telemetry points ({i+1}/{num_batches})...")
                except Exception as e:
                    logger.error(f"Error saving telemetry batch {i+1}: {e}")
                    # Continue with next batch despite error
            
            self.progress.emit(100, "Save completed")
            
            # Add final diagnostics for reporting
            diagnostics["lap_id"] = lap_id
            diagnostics["points_saved"] = len(self.telemetry_points)
            
            self.finished.emit(True, "Lap saved successfully", diagnostics)
            
        except Exception as e:
            logger.error(f"Error in telemetry save worker: {e}", exc_info=True)
            self.finished.emit(False, f"Unexpected error: {str(e)}", None)
    
    def cancel(self):
        """Cancel the current operation."""
        self.is_cancelled = True
        logger.info("Telemetry save operation cancelled")


class TelemetryMonitorWorker(QThread):
    """Dedicated thread worker for AI coaching telemetry processing.
    
    This worker runs in its own thread completely independent of the main telemetry flow.
    The main telemetry callback only queues data here - no blocking operations.
    """
    
    # Signal emitted with coverage updates
    coverage_updated = pyqtSignal(float, object)  # coverage percentage, diagnostics
    
    def __init__(self, buffer_size=5000):
        """Initialize the telemetry monitor thread.
        
        Args:
            buffer_size: Maximum number of telemetry points to keep in buffer
        """
        super().__init__()
        self.telemetry_buffer = []
        self.buffer_size = buffer_size
        self.is_monitoring = False
        self.should_stop = False
        
        # Thread-safe queue for telemetry data
        self.telemetry_queue = queue.Queue()
        
        # AI coach instance
        self._ai_coach = None
        
        # Counters for debugging
        self._telemetry_point_count = 0
        self._queue_drops = 0
        
        # Performance tracking
        self._last_process_time = time.time()
        
        # Start the dedicated thread
        self.start()
        logger.info("🧵 [AI WORKER THREAD] Dedicated AI coaching thread started")

    @property
    def ai_coach(self):
        """Get the AI coach instance."""
        return self._ai_coach
    
    @ai_coach.setter
    def ai_coach(self, value):
        """Set the AI coach instance with debug logging."""
        logger.info(f"🎙️ [AI COACH ASSIGNMENT] Setting AI coach: {value is not None}")
        if value is not None:
            logger.info(f"🎙️ [AI COACH ASSIGNMENT] AI coach type: {type(value)}")
            if hasattr(value, 'superlap_points'):
                logger.info(f"🎙️ [AI COACH ASSIGNMENT] AI coach has {len(getattr(value, 'superlap_points', []))} superlap points")
        self._ai_coach = value

    def add_telemetry_point(self, point):
        """Add a new telemetry point to the processing queue.
        
        This method is called from the main telemetry thread and MUST be non-blocking.
        It only queues the data - all processing happens in the dedicated AI thread.
        
        Args:
            point: Dictionary with telemetry data
        """
        try:
            # Non-blocking queue add with immediate return
            self.telemetry_queue.put_nowait(point)
            
            # Occasional debug logging (every 10 seconds worth of data)
            self._telemetry_point_count += 1
            if self._telemetry_point_count % 600 == 0:  # Every 10 seconds at ~60Hz
                queue_size = self.telemetry_queue.qsize()
                logger.info(f"🚀 [AI QUEUE] Point #{self._telemetry_point_count} queued - Queue size: {queue_size}, Drops: {self._queue_drops}")
                print(f"🧵 [AI THREAD] Telemetry queued: #{self._telemetry_point_count}, Queue: {queue_size}")
                
        except queue.Full:
            # Queue is full - drop this point to prevent blocking
            self._queue_drops += 1
            if self._queue_drops % 100 == 0:  # Log every 100 drops
                logger.warning(f"⚠️ [AI QUEUE] Dropped {self._queue_drops} telemetry points - AI thread overloaded")
    
    def run(self):
        """Main thread loop for processing AI coaching telemetry.
        
        This runs in a dedicated thread completely separate from the main telemetry flow.
        """
        logger.info("🧵 [AI THREAD] AI coaching telemetry thread started")
        
        last_log_time = time.time()
        points_processed = 0
        
        while not self.should_stop:
            try:
                # Wait for telemetry data (blocking, but only in AI thread)
                try:
                    point = self.telemetry_queue.get(timeout=1.0)  # 1 second timeout
                except queue.Empty:
                    continue  # No data available, check if should stop
                
                points_processed += 1
                
                # Only process if we're actively monitoring
                if self.is_monitoring:
                    # Add to buffer for coverage calculation
                    self.telemetry_buffer.append(point)
                    
                    # Trim buffer if it exceeds max size
                    if len(self.telemetry_buffer) > self.buffer_size:
                        self.telemetry_buffer = self.telemetry_buffer[-self.buffer_size:]
                    
                    # Calculate coverage (emits signal to main thread)
                    self._calculate_coverage()
                    
                    # Process for AI coaching if available
                    if self._ai_coach:
                        self._process_ai_coaching(point, points_processed)
                
                # Debug logging every 10 seconds
                current_time = time.time()
                if current_time - last_log_time >= 10.0:
                    queue_size = self.telemetry_queue.qsize()
                    processing_rate = points_processed / (current_time - last_log_time)
                    
                    ai_status = "ACTIVE" if (self._ai_coach and self.is_monitoring) else "INACTIVE"
                    logger.info(f"🧵 [AI THREAD] Processed {points_processed} points in 10s ({processing_rate:.1f}/s) - Queue: {queue_size}, AI: {ai_status}")
                    
                    if self._ai_coach and self.is_monitoring:
                        print(f"🎯 [AI COACHING] Processing at {processing_rate:.1f} points/sec - Queue: {queue_size}")
                    
                    last_log_time = current_time
                    points_processed = 0
                
                # Mark task as done
                self.telemetry_queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ [AI THREAD] Error in AI coaching thread: {e}")
                
        logger.info("🧵 [AI THREAD] AI coaching telemetry thread stopped")
    
    def _process_ai_coaching(self, point, point_number):
        """Process telemetry for AI coaching.
        
        This runs in the dedicated AI thread - safe to do blocking operations.
        """
        try:
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
                # Log every 5 seconds instead of every second (300 points at ~60Hz)
                if point_number % 300 == 0:
                    logger.info(f"✅ [AI TELEMETRY ACTIVE] Point #{point_number} -> AI Coach: pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f} km/h")
                    print(f"🎙️ [AI COACHING] Processing: pos={ai_coach_point['track_position']:.3f}, speed={ai_coach_point['speed']:.1f} km/h")
                
                # Process with AI coach (safe to block in dedicated thread)
                self._ai_coach.process_realtime_telemetry(ai_coach_point)
                
            else:
                # Log missing data less frequently
                if point_number % 600 == 0:  # Every 10 seconds instead of 5
                    logger.debug(f"⚠️ [AI COACH] Skipping - no track position data. Keys: {list(point.keys())}")
                    
        except Exception as e:
            logger.error(f"❌ [AI COACH ERROR] Error processing telemetry: {e}")
    
    def start_monitoring(self):
        """Start monitoring telemetry coverage and coaching."""
        logger.info(f"🎙️ [MONITOR START] start_monitoring() called")
        logger.info(f"🎙️ [MONITOR START] AI coach available: {self._ai_coach is not None}")
        logger.info(f"🎙️ [MONITOR START] Current monitoring state: {self.is_monitoring}")
        
        self.is_monitoring = True
        logger.info("🧵 [AI THREAD] Telemetry coverage monitoring and coaching started")
        logger.info(f"🎙️ [MONITOR START] New monitoring state: {self.is_monitoring}")
        
        # Clear any old buffer data
        self.telemetry_buffer = []
        
        # Return True to signal successful start
        return True
    
    def stop_monitoring(self):
        """Stop monitoring telemetry coverage and coaching."""
        logger.info(f"🎙️ [MONITOR STOP] stop_monitoring() called")
        logger.info(f"🎙️ [MONITOR STOP] AI coach available: {self._ai_coach is not None}")
        logger.info(f"🎙️ [MONITOR STOP] Current monitoring state: {self.is_monitoring}")
        
        self.is_monitoring = False
        logger.info("🧵 [AI THREAD] Telemetry coverage monitoring and coaching stopped")
        logger.info(f"🎙️ [MONITOR STOP] New monitoring state: {self.is_monitoring}")
        
        # Return True to signal successful stop
        return True
    
    def stop_thread(self):
        """Stop the AI coaching thread."""
        logger.info("🧵 [AI THREAD] Stopping AI coaching thread...")
        self.should_stop = True
        
        # Wait for thread to finish (with timeout)
        if self.wait(5000):  # 5 second timeout
            logger.info("🧵 [AI THREAD] AI coaching thread stopped cleanly")
        else:
            logger.warning("⚠️ [AI THREAD] AI coaching thread stop timeout - forcing termination")
            self.terminate()
    
    def clear_buffer(self):
        """Clear the telemetry buffer."""
        self.telemetry_buffer = []
        logger.info("🧵 [AI THREAD] Telemetry buffer cleared")
    
    def get_buffer_copy(self):
        """Get a copy of the current telemetry buffer.
        
        Returns:
            list: Copy of current telemetry points
        """
        return self.telemetry_buffer.copy()
    
    def _calculate_coverage(self):
        """Calculate current telemetry coverage and emit signal."""
        buffer_copy = self.telemetry_buffer.copy()
        
        # Extract track positions
        positions = [p.get('track_position') for p in buffer_copy if p.get('track_position') is not None]
        
        if not positions:
            self.coverage_updated.emit(0.0, {"min_pos": None, "max_pos": None})
            return
        
        min_pos = min(positions)
        max_pos = max(positions)
        coverage = (max_pos - min_pos) * 100
        
        # Cap at 100%
        coverage = min(coverage, 100.0)
        
        # Create diagnostics
        diagnostics = {
            "min_pos": min_pos,
            "max_pos": max_pos,
            "total_points": len(buffer_copy),
            "is_complete": min_pos <= 0.02 and max_pos >= 0.98,
            "queue_size": self.telemetry_queue.qsize(),
            "drops": self._queue_drops
        }
        
        self.coverage_updated.emit(coverage, diagnostics) 