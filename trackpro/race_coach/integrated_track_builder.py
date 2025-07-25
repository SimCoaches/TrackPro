"""
Integrated Track Builder - Ultimate track building with corner detection
Combines the 3-lap centerline builder with corner detection and Supabase integration
"""

import time
import numpy as np
import json
import math
from typing import List, Tuple, Dict, Optional, Any
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .pyirsdk import irsdk
from ..database.supabase_client import get_supabase_client

# Import advanced libraries with fallback
try:
    from scipy.interpolate import interp1d
    from sklearn.cluster import DBSCAN
    from filterpy.kalman import KalmanFilter
    ADVANCED_LIBS_AVAILABLE = True
    print("🎯 Advanced libraries available: scipy, sklearn, filterpy")
except ImportError:
    ADVANCED_LIBS_AVAILABLE = False
    print("⚠️ Advanced libraries not available - using basic mode")


class TrackMapBuilder:
    """Ultimate track map builder with 3-lap centerline generation."""
    
    def __init__(self):
        self.position_x = 0.0
        self.position_y = 0.0
        self.track_points = []
        self.laps = []
        self.current_lap = []
        self.centerline_track = None
        self.centerline_generated = False
        self.required_laps = 3
        
        # NEW: Proper start/finish detection using LapDistPct
        self.last_lap_dist_pct = None
        self.start_finish_position = None
        self.start_finish_marked = False
        
        # NEW: Wait for first start/finish crossing before starting lap collection
        self.waiting_for_first_crossing = True
        self.lap_collection_started = False
        
        # Advanced processing settings
        self.use_advanced_processing = ADVANCED_LIBS_AVAILABLE
        
    def update_position(self, velocity_x, velocity_y, yaw, delta_time, lap_dist_pct):
        # Convert car-local velocities to world coordinates
        global_vx = velocity_x * math.cos(yaw) - velocity_y * math.sin(yaw)
        global_vy = velocity_x * math.sin(yaw) + velocity_y * math.cos(yaw)
        
        # Integrate to get position
        self.position_x += global_vx * delta_time
        self.position_y += global_vy * delta_time

        # Always add to track_points for display
        self.track_points.append((self.position_x, self.position_y))
        
        # Check for start/finish line crossing using LapDistPct
        self.check_start_finish_lapdist(lap_dist_pct, self.position_x, self.position_y)
        
        # Only add to current_lap if lap collection has started
        if self.lap_collection_started:
            self.current_lap.append((self.position_x, self.position_y))

        return self.position_x, self.position_y

    def check_start_finish_lapdist(self, lap_dist_pct, position_x, position_y):
        """Check for start/finish line crossing using LapDistPct - PRECISE METHOD"""
        if self.last_lap_dist_pct is None:
            self.last_lap_dist_pct = lap_dist_pct
            return False
        
        # Detect crossing from ~1.0 to ~0.0 (99.999% to 0.001%)
        if self.last_lap_dist_pct > 0.98 and lap_dist_pct < 0.02:
            print(f"🏁 START/FINISH DETECTED! LapDistPct: {self.last_lap_dist_pct:.6f} → {lap_dist_pct:.6f}")
            print(f"📍 Marking start/finish at: ({position_x:.1f}, {position_y:.1f})")
            
            # Mark the EXACT start/finish position
            self.start_finish_position = (position_x, position_y)
            self.start_finish_marked = True
            
            # FIXED: Handle first crossing vs subsequent crossings
            if self.waiting_for_first_crossing:
                print(f"🎯 FIRST start/finish crossing detected - starting lap collection!")
                self.waiting_for_first_crossing = False
                self.lap_collection_started = True
                # Start lap 1 from this precise position
                self.current_lap = [(position_x, position_y)]
            else:
                # Complete current lap if we have enough points and lap collection has started
                if self.lap_collection_started and len(self.current_lap) > 100:
                    self.laps.append(self.current_lap[:-1])  # exclude crossing point
                    print(f"🏁 LAP {len(self.laps)} COMPLETED! ({len(self.current_lap)} points)")
                    
                    # Check if we have enough laps for centerline generation
                    if len(self.laps) >= self.required_laps and not self.centerline_generated:
                        print(f"🎯 {self.required_laps} laps completed! Ready to generate centerline...")
                
                # Start new lap from start/finish position
                self.current_lap = [(position_x, position_y)]
            
            self.last_lap_dist_pct = lap_dist_pct
            return True
        
        self.last_lap_dist_pct = lap_dist_pct
        return False

    def generate_centerline(self):
        """Generate centerline from collected laps using advanced algorithms."""
        if len(self.laps) < self.required_laps or self.centerline_generated:
            return None
        
        print(f"🎯 Generating centerline from {len(self.laps)} laps...")
        
        if self.use_advanced_processing:
            self.centerline_track = self._generate_centerline_advanced()
        else:
            self.centerline_track = self._generate_centerline_basic()
        
        if self.centerline_track:
            self.centerline_generated = True
            print(f"✅ Centerline generated! {len(self.centerline_track)} points")
        
        return self.centerline_track

    def _generate_centerline_advanced(self):
        """Advanced centerline generation using statistical methods."""
        try:
            print("🔬 Using advanced centerline generation...")
            
            # Resample all laps to the same number of points
            target_points = 1000
            resampled_laps = []
            
            for i, lap in enumerate(self.laps[:self.required_laps]):
                if len(lap) < 50:
                    continue
                
                # Extract x, y coordinates
                x_coords = [p[0] for p in lap]
                y_coords = [p[1] for p in lap]
                
                # Create parameter array (0 to 1)
                t_original = np.linspace(0, 1, len(lap))
                t_new = np.linspace(0, 1, target_points)
                
                # Interpolate to get consistent point count
                f_x = interp1d(t_original, x_coords, kind='cubic')
                f_y = interp1d(t_original, y_coords, kind='cubic')
                
                x_resampled = f_x(t_new)
                y_resampled = f_y(t_new)
                
                resampled_lap = list(zip(x_resampled, y_resampled))
                resampled_laps.append(resampled_lap)
                print(f"📊 Lap {i+1}: {len(lap)} → {len(resampled_lap)} points")
            
            if len(resampled_laps) < self.required_laps:
                print("⚠️ Not enough valid laps for advanced processing")
                return self._generate_centerline_basic()
            
            # Calculate centerline by averaging corresponding points
            centerline = []
            for i in range(target_points):
                x_sum = sum(lap[i][0] for lap in resampled_laps)
                y_sum = sum(lap[i][1] for lap in resampled_laps)
                
                avg_x = x_sum / len(resampled_laps)
                avg_y = y_sum / len(resampled_laps)
                
                centerline.append((avg_x, avg_y))
            
            print(f"✨ Advanced centerline complete: {len(centerline)} points")
            return centerline
            
        except Exception as e:
            print(f"⚠️ Advanced processing failed: {e}")
            return self._generate_centerline_basic()

    def _generate_centerline_basic(self):
        """Basic centerline generation by simple averaging."""
        print("🔧 Using basic centerline generation...")
        
        # Find the shortest lap to avoid index errors
        min_length = min(len(lap) for lap in self.laps[:self.required_laps])
        
        centerline = []
        for i in range(min_length):
            x_sum = sum(lap[i][0] for lap in self.laps[:self.required_laps])
            y_sum = sum(lap[i][1] for lap in self.laps[:self.required_laps])
            
            avg_x = x_sum / self.required_laps
            avg_y = y_sum / self.required_laps
            
            centerline.append((avg_x, avg_y))
        
        print(f"✅ Basic centerline complete: {len(centerline)} points")
        return centerline


class Corner:
    """Represents a detected corner with entry, apex, and exit points."""
    
    def __init__(self, corner_id: int, entry_idx: int, apex_idx: int, exit_idx: int):
        self.id = corner_id
        self.entry_idx = entry_idx
        self.apex_idx = apex_idx
        self.exit_idx = exit_idx
        self.min_speed = None
        self.max_steering = None
        self.length = None
        self.entry_lap_dist_pct = None
        self.apex_lap_dist_pct = None
        self.exit_lap_dist_pct = None


class IntegratedTrackBuilderWorker(QThread):
    """Worker thread that builds track map and detects corners simultaneously."""
    
    # Signals
    progress_update = pyqtSignal(str, int)
    status_update = pyqtSignal(str)
    track_update = pyqtSignal(object)  # Track builder object
    corner_detected = pyqtSignal(int, str)
    completion_ready = pyqtSignal(list, list)  # centerline_track, corners
    error_occurred = pyqtSignal(str)
    upload_complete = pyqtSignal(str, int)  # track_name, total_users_count
    
    def __init__(self, simple_iracing_api=None):
        super().__init__()
        self.track_builder = TrackMapBuilder()
        self.simple_iracing_api = simple_iracing_api  # Use existing global connection
        self.ir = None  # Will be set from the global connection
        self.is_running = False
        self.telemetry_data = []
        self.last_time = None
        
        # Corner detection parameters
        self.speed_drop_threshold = 5.0
        self.steering_threshold = 0.1
        self.min_corner_duration = 1.0
        
    def run(self):
        """Main integrated building process."""
        try:
            self.is_running = True
            
            # Use existing global iRacing connection instead of creating new one
            if not self.connect_to_existing_iracing():
                return
            
            # Real-time track building and data collection
            self.real_time_building()
            
        except Exception as e:
            self.error_occurred.emit(f"Track building error: {str(e)}")
    
    def connect_to_existing_iracing(self) -> bool:
        """Connect to existing global iRacing connection instead of creating new one."""
        self.progress_update.emit("Using existing iRacing connection...", 5)
        
        if self.simple_iracing_api:
            # Use the existing global connection
            self.ir = self.simple_iracing_api.ir
            if self.ir and self.ir.is_connected:
                self.progress_update.emit("Connected to existing iRacing session", 10)
                print("🔗 Worker using existing global iRacing connection")
                return True
            else:
                self.error_occurred.emit("Global iRacing connection not available")
                return False
        else:
            # Fallback: create own connection if no global one provided
            print("⚠️ No global iRacing connection provided, creating own connection")
            return self.connect_to_iracing_fallback()
    
    def connect_to_iracing_fallback(self) -> bool:
        """Fallback: DISABLED - Use shared SDK instance only to prevent conflicts."""
        print("⚠️ FALLBACK DISABLED: Cannot create own iRacing connection - would conflict with shared SDK")
        self.error_occurred.emit("No shared iRacing connection available. Please ensure iRacing is connected in the main application.")
        return False
    
    def real_time_building(self):
        """Real-time track building with corner detection."""
        self.progress_update.emit("Starting real-time track building...", 15)
        print(f"🎯 Worker starting real-time building with connection: {self.ir is not None}")
        
        while self.ir and self.ir.is_connected and self.is_running:
            try:
                # Get telemetry data from the shared connection
                current_time = time.time()
                
                if self.last_time is None:
                    self.last_time = current_time
                    continue
                
                delta_time = current_time - self.last_time
                self.last_time = current_time
                
                # Get required telemetry
                velocity_x = self.ir['VelocityX'] or 0.0
                velocity_y = self.ir['VelocityY'] or 0.0
                yaw = self.ir['Yaw'] or 0.0
                lap_dist_pct = self.ir['LapDistPct'] or 0.0
                speed = self.ir['Speed'] or 0.0
                steering = self.ir['SteeringWheelAngle'] or 0.0
                
                # Only process when moving
                if speed > 2.0:
                    # Update track position
                    pos_x, pos_y = self.track_builder.update_position(
                        velocity_x, velocity_y, yaw, delta_time, lap_dist_pct
                    )
                    
                    # Store telemetry for corner detection
                    self.telemetry_data.append({
                        'timestamp': current_time,
                        'speed': speed,
                        'steering': steering,
                        'lap_dist_pct': lap_dist_pct,
                        'position_x': pos_x,
                        'position_y': pos_y
                    })
                    
                    # Emit track update for visualization at reasonable frequency (4Hz)
                    if not hasattr(self, '_last_track_update_time'):
                        self._last_track_update_time = 0
                    
                    if current_time - self._last_track_update_time >= 0.25:  # 4Hz update rate
                        completed_laps = len(self.track_builder.laps)
                        current_points = len(self.track_builder.current_lap)
                        
                        # Only print occasionally to avoid log spam
                        if current_points % 50 == 0:  # Print every 50 points
                            print(f"🎯 Track update: Lap {completed_laps + 1}/3 - {current_points} points")
                        
                        self.track_update.emit(self.track_builder)
                        self.progress_update.emit(f"Lap {completed_laps + 1}/3 - {current_points} points", completed_laps)
                        self._last_track_update_time = current_time
                    
                    # Check if centerline generation is ready
                    if (len(self.track_builder.laps) >= self.track_builder.required_laps and 
                        not self.track_builder.centerline_generated):
                        
                        centerline = self.track_builder.generate_centerline()
                        if centerline:
                            # Detect corners from centerline and telemetry
                            corners = self.detect_corners()
                            
                            # Save to Supabase and emit completion
                            self.save_results(centerline, corners)
                            self.completion_ready.emit(centerline, corners)
                            break
                
                time.sleep(0.05)  # 20Hz update rate
                
            except Exception as e:
                print(f"Error in real-time building: {e}")
                continue
    
    def detect_corners(self) -> List[Corner]:
        """Detect corners from collected telemetry data."""
        if len(self.telemetry_data) < 100:
            return []
        
        print(f"🔍 Detecting corners from {len(self.telemetry_data)} telemetry points...")
        
        # Extract speed and steering data
        speeds = [d['speed'] for d in self.telemetry_data]
        steerings = [abs(d['steering']) for d in self.telemetry_data]
        
        # Smooth data
        speeds = self.smooth_data(speeds, 10)
        steerings = self.smooth_data(steerings, 10)
        
        corners = []
        corner_id = 1
        i = 0
        
        while i < len(speeds) - 50:
            # Look for speed drop + steering increase
            if speeds[i] > 10.0:  # Only consider when moving
                speed_drop = speeds[i] - min(speeds[i:i+30])
                max_steering = max(steerings[i:i+30])
                
                if speed_drop > self.speed_drop_threshold and max_steering > self.steering_threshold:
                    # Find corner points
                    entry_idx = i
                    apex_idx = i + speeds[i:i+30].index(min(speeds[i:i+30]))
                    exit_idx = min(apex_idx + 20, len(speeds) - 1)
                    
                    # Create corner
                    corner = Corner(corner_id, entry_idx, apex_idx, exit_idx)
                    corner.min_speed = speeds[apex_idx]
                    corner.max_steering = steerings[apex_idx]
                    corner.entry_lap_dist_pct = self.telemetry_data[entry_idx]['lap_dist_pct']
                    corner.apex_lap_dist_pct = self.telemetry_data[apex_idx]['lap_dist_pct']
                    corner.exit_lap_dist_pct = self.telemetry_data[exit_idx]['lap_dist_pct']
                    
                    corners.append(corner)
                    self.corner_detected.emit(corner_id, f"Corner {corner_id} at {corner.apex_lap_dist_pct:.1%}")
                    
                    corner_id += 1
                    i = exit_idx + 10  # Skip ahead to avoid duplicate detection
                else:
                    i += 5
            else:
                i += 1
        
        print(f"✅ Detected {len(corners)} corners")
        return corners
    
    def smooth_data(self, data: List[float], window: int) -> List[float]:
        """Smooth data using moving average."""
        if len(data) < window:
            return data
        
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end = min(len(data), i + window // 2 + 1)
            smoothed.append(sum(data[start:end]) / (end - start))
        
        return smoothed
    
    def save_results(self, centerline: List[Tuple[float, float]], corners: List[Corner]):
        """Save track map and corners to Supabase."""
        try:
            # Get track info
            track_name = self.ir['WeekendInfo']['TrackDisplayName']
            track_config = self.ir['WeekendInfo']['TrackConfigName']
            
            self.progress_update.emit(f"💾 Uploading track map to cloud...", 90)
            
            # Prepare data for Supabase
            track_map_data = [{'x': x, 'y': y} for x, y in centerline]
            corners_data = []
            
            for corner in corners:
                corners_data.append({
                    'id': corner.id,
                    'entry_idx': corner.entry_idx,
                    'apex_idx': corner.apex_idx,
                    'exit_idx': corner.exit_idx,
                    'min_speed': corner.min_speed,
                    'max_steering': corner.max_steering,
                    'entry_lap_dist_pct': corner.entry_lap_dist_pct,
                    'apex_lap_dist_pct': corner.apex_lap_dist_pct,
                    'exit_lap_dist_pct': corner.exit_lap_dist_pct
                })
            
            # Save local centerline file first (for overlay use)
            self._save_local_centerline_file(track_map_data, track_name, track_config)
            
            # Save to Supabase
            supabase = get_supabase_client()
            if not supabase:
                self.status_update.emit("⚠️ Supabase connection not available - track map saved locally only")
                return
            
            # Find or create track record
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            existing_tracks = track_query.execute()
            
            update_data = {
                'track_map': track_map_data,
                'corners': corners_data,
                'analysis_metadata': {
                    'generation_method': 'integrated_3lap_centerline',
                    'total_coordinates': len(track_map_data),
                    'total_corners': len(corners_data),
                    'generation_timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'iracing_track_name': track_name,
                    'iracing_config_name': track_config
                },
                'last_analysis_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'data_version': 2
            }
            
            if existing_tracks.data:
                # Update existing track map
                track_id = existing_tracks.data[0]['id']
                result = supabase.table('tracks').update(update_data).eq('id', track_id).execute()
                
                if result.data:
                    print(f"✅ Updated existing track map: {track_name}")
                    self.status_update.emit(f"✅ Track map updated in cloud - accessible by ALL USERS!")
                    self.upload_complete.emit(track_name, 999999)  # Signal successful upload
                else:
                    print(f"⚠️ Failed to update track: {track_name}")
                    self.status_update.emit("⚠️ Failed to update track map in cloud")
            else:
                # Create new track map
                new_track = {
                    'name': track_name,
                    'config': track_config if track_config != track_name else None,
                    **update_data
                }
                result = supabase.table('tracks').insert(new_track).execute()
                
                if result.data:
                    print(f"✅ Created new track map: {track_name}")
                    self.status_update.emit(f"✅ New track map uploaded to cloud - available to ALL USERS!")
                    self.upload_complete.emit(track_name, 999999)  # Signal successful upload
                else:
                    print(f"⚠️ Failed to create track: {track_name}")
                    self.status_update.emit("⚠️ Failed to upload track map to cloud")
            
            # Verify the upload by checking what we uploaded
            summary_msg = (f"📊 Track Map Summary:\n"
                          f"• Track: {track_name} ({track_config})\n"
                          f"• Coordinates: {len(track_map_data):,} points\n"
                          f"• Corners: {len(corners_data)} detected\n"
                          f"• Status: {'Updated' if existing_tracks.data else 'Created'} in cloud database\n"
                          f"• Available to: ALL TrackPro users worldwide 🌍")
            print(summary_msg)
            
        except Exception as e:
            error_msg = f"❌ Failed to upload track map to cloud: {str(e)}"
            print(error_msg)
            self.status_update.emit("❌ Cloud upload failed - track map saved locally only")
    
    def stop_building(self):
        """Stop the building process."""
        self.is_running = False
    
    def _save_local_centerline_file(self, track_map_data, track_name, track_config):
        """Save centerline data to local file for overlay use."""
        try:
            import json
            import os
            from ...utils.resource_utils import get_track_map_file_path
            
            # Create the local centerline file format
            centerline_data = {
                'track_name': track_name,
                'track_config': track_config,
                'centerline_positions': track_map_data,
                'generated_timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_points': len(track_map_data)
            }
            
            # Use production-safe track map file path
            file_path = get_track_map_file_path()
            
            # Write new file (overwrite existing without backup)
            with open(file_path, 'w') as f:
                json.dump(centerline_data, f, indent=2)
            
            print(f"💾 Saved new centerline data to {file_path}")
            print(f"🎯 Track: {track_name} ({track_config})")
            print(f"📊 Points: {len(track_map_data)}")
            
        except Exception as e:
            print(f"⚠️ Error saving local centerline file: {e}")


class IntegratedTrackBuilderManager(QObject):
    """Manager for the integrated track builder."""
    
    # Signals
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(str, int)
    track_update = pyqtSignal(object)
    completion_ready = pyqtSignal(list, list)
    error_occurred = pyqtSignal(str)
    upload_complete = pyqtSignal(str, int)
    
    def __init__(self, simple_iracing_api=None):
        super().__init__()
        self.worker = None
        self.is_running = False
        self.simple_iracing_api = simple_iracing_api  # Store global iRacing connection
    
    def start_building(self):
        """Start the track building process."""
        if self.is_running:
            return
        
        self.is_running = True
        # Pass the global iRacing connection to the worker
        self.worker = IntegratedTrackBuilderWorker(self.simple_iracing_api)
        
        print(f"🔗 Manager creating worker with global iRacing connection: {self.simple_iracing_api is not None}")
        
        # Connect signals
        self.worker.status_update.connect(self.status_update)
        self.worker.progress_update.connect(self.progress_update)
        self.worker.track_update.connect(self.track_update)
        self.worker.completion_ready.connect(self.completion_ready)
        self.worker.error_occurred.connect(self.error_occurred)
        self.worker.upload_complete.connect(self.upload_complete)
        self.worker.finished.connect(self._on_worker_finished)
        
        # ADDED: Debug the signal connections
        print(f"🐛 DEBUG: Manager connected all worker signals - progress_update forwarded")
        
        # Start worker
        self.worker.start()
        self.status_update.emit("Starting integrated track builder...")
    
    def stop_building(self):
        """Stop the track building process."""
        if self.worker and self.is_running:
            self.worker.stop_building()
            self.worker.wait(5000)  # Wait up to 5 seconds
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(2000)
            self.is_running = False
            self.status_update.emit("Track building stopped.")
    
    def _on_worker_finished(self):
        """Handle worker completion."""
        self.is_running = False
        self.worker = None 