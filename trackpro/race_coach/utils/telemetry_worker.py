import logging
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread

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


class TelemetryMonitorWorker(QObject):
    """Worker for monitoring real-time telemetry coverage during a lap."""
    
    # Signal emitted with coverage updates
    coverage_updated = pyqtSignal(float, object)  # coverage percentage, diagnostics
    
    def __init__(self, buffer_size=5000):
        """Initialize the telemetry monitor.
        
        Args:
            buffer_size: Maximum number of telemetry points to keep in buffer
        """
        super().__init__()
        self.telemetry_buffer = []
        self.buffer_size = buffer_size
        self.is_running = False
        self.lock = threading.Lock()
    
    def add_telemetry_point(self, point):
        """Add a new telemetry point to the buffer.
        
        Args:
            point: Dictionary with telemetry data
        """
        with self.lock:
            self.telemetry_buffer.append(point)
            
            # Trim buffer if it exceeds max size
            if len(self.telemetry_buffer) > self.buffer_size:
                self.telemetry_buffer = self.telemetry_buffer[-self.buffer_size:]
            
            # If monitoring is active, calculate coverage
            if self.is_running:
                self._calculate_coverage()
    
    def start_monitoring(self):
        """Start monitoring telemetry coverage."""
        self.is_running = True
        logger.info("Telemetry coverage monitoring started")
        self._calculate_coverage()
    
    def stop_monitoring(self):
        """Stop monitoring telemetry coverage."""
        self.is_running = False
        logger.info("Telemetry coverage monitoring stopped")
    
    def clear_buffer(self):
        """Clear the telemetry buffer."""
        with self.lock:
            self.telemetry_buffer = []
            logger.info("Telemetry buffer cleared")
    
    def get_buffer_copy(self):
        """Get a copy of the current telemetry buffer.
        
        Returns:
            list: Copy of current telemetry points
        """
        with self.lock:
            return self.telemetry_buffer.copy()
    
    def _calculate_coverage(self):
        """Calculate current telemetry coverage and emit signal."""
        with self.lock:
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
            "is_complete": min_pos <= 0.02 and max_pos >= 0.98
        }
        
        self.coverage_updated.emit(coverage, diagnostics) 