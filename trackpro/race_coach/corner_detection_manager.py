"""
Corner Detection Manager - Integrated into TrackPro
Task 2.2: Auto-detect corners using speed drops + steering increases
"""

import time
import numpy as np
import math
import json
import os
from typing import List, Tuple, Dict, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QMessageBox
import matplotlib.pyplot as plt

from .pyirsdk import irsdk
from ..database.supabase_client import get_supabase_client
from .track_map_generator import TrackMapGenerator


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


class CornerDetectionWorker(QThread):
    """Worker thread for corner detection to avoid blocking the UI."""
    
    # Signals
    progress_update = pyqtSignal(str, int)  # message, progress_percentage
    corner_detected = pyqtSignal(int, str)  # corner_id, description
    detection_complete = pyqtSignal(list)   # list of detected corners
    error_occurred = pyqtSignal(str)        # error message
    connection_status = pyqtSignal(bool, str)  # connected, status_message
    
    def __init__(self):
        super().__init__()
        self.ir = None
        self.telemetry_data = []
        self.corners = []
        self.is_running = False
        self.collection_duration = 120  # 2 minutes default
        
        # Corner detection parameters
        self.speed_drop_threshold = 5.0
        self.steering_threshold = 0.1
        self.min_corner_duration = 1.0
        self.smoothing_window = 10
        
        # Track map generator for creating track coordinates
        self.track_map_generator = TrackMapGenerator()
    
    def stop_detection(self):
        """Stop the corner detection process."""
        self.is_running = False
    
    def set_collection_duration(self, seconds: int):
        """Set how long to collect data for."""
        self.collection_duration = seconds
    
    def run(self):
        """Main detection process."""
        try:
            self.is_running = True
            
            # Connect to iRacing
            if not self.connect_to_iracing():
                return
            
            # Collect telemetry data
            if not self.collect_telemetry_data():
                return
            
            # Detect corners
            corners = self.detect_corners()
            
            # Generate track map from velocity data
            track_map_data = self.generate_track_map()
            
            # Save results (corners + track map)
            if corners:
                self.save_results(corners, track_map_data)
                self.detection_complete.emit(corners)
            else:
                self.error_occurred.emit("No corners detected. Make sure you drive through corners during data collection.")
                
        except Exception as e:
            self.error_occurred.emit(f"Corner detection error: {str(e)}")
        finally:
            if self.ir:
                self.ir.shutdown()
    
    def connect_to_iracing(self) -> bool:
        """Connect to iRacing telemetry - DISABLED to prevent conflicts with shared SDK."""
        self.progress_update.emit("Connection disabled - use shared SDK instance only", 5)
        self.error_occurred.emit("Corner detection requires a shared iRacing connection. Please ensure iRacing is connected in the main application.")
        return False
    
    def collect_telemetry_data(self) -> bool:
        """Collect telemetry data for analysis."""
        self.progress_update.emit(f"Collecting telemetry data for {self.collection_duration} seconds...", 15)
        self.progress_update.emit("Drive normally through corners - data recording in progress!", 15)
        
        start_time = time.time()
        self.telemetry_data = []
        
        while (time.time() - start_time < self.collection_duration and 
               self.ir.is_connected and self.is_running):
            
            # Get telemetry - including velocity and yaw for track map generation
            speed = self.ir['Speed'] or 0.0
            steering = self.ir['SteeringWheelAngle'] or 0.0
            throttle = self.ir['Throttle'] or 0.0
            brake = self.ir['Brake'] or 0.0
            lap_dist_pct = self.ir['LapDistPct'] or 0.0
            
            # Get velocity and yaw data for track map generation
            velocity_x = self.ir['VelocityX'] or 0.0
            velocity_y = self.ir['VelocityY'] or 0.0
            yaw = self.ir['Yaw'] or 0.0
            
            # Debug velocity data collection for first few points
            if len(self.telemetry_data) < 5 and (velocity_x != 0 or velocity_y != 0):
                print(f"🚗 [DEBUG] Collecting velocity data - Point {len(self.telemetry_data)}: VelX={velocity_x:.3f}, VelY={velocity_y:.3f}, Yaw={yaw:.3f}")
            
            # Only record when moving
            if speed > 2.0:
                data_point = {
                    'timestamp': time.time(),
                    'speed': speed,
                    'steering': steering,
                    'throttle': throttle,
                    'brake': brake,
                    'lap_dist_pct': lap_dist_pct,
                    # Add velocity and yaw data for track map generation
                    'VelocityX': velocity_x,
                    'VelocityY': velocity_y,
                    'Yaw': yaw
                }
                self.telemetry_data.append(data_point)
            
            # Update progress
            elapsed = time.time() - start_time
            progress = 15 + int((elapsed / self.collection_duration) * 70)  # 15-85%
            
            if len(self.telemetry_data) % 50 == 0 and len(self.telemetry_data) > 0:
                self.progress_update.emit(
                    f"Recording: {elapsed:.1f}s elapsed, {len(self.telemetry_data)} points, Speed: {speed:.1f} m/s", 
                    progress
                )
            
            time.sleep(0.1)  # 10Hz collection rate
        
        if not self.is_running:
            self.error_occurred.emit("Data collection was stopped by user.")
            return False
        
        if len(self.telemetry_data) < 50:
            self.error_occurred.emit("Not enough telemetry data collected. Make sure you're driving during data collection.")
            return False
        
        self.progress_update.emit(f"Data collection complete: {len(self.telemetry_data)} points", 85)
        return True
    
    def find_start_finish_line(self) -> int:
        """Find the start/finish line crossing using LapDistPct."""
        lap_distances = [d['lap_dist_pct'] for d in self.telemetry_data]
        
        # Look for the transition from ~1.0 to ~0.0 (start/finish line crossing)
        for i in range(1, len(lap_distances)):
            prev_dist = lap_distances[i-1]
            curr_dist = lap_distances[i]
            
            # Detect crossing: previous > 0.9 and current < 0.1
            if prev_dist > 0.9 and curr_dist < 0.1:
                return i
        
        return 0  # No crossing found, start from beginning
    
    def smooth_data(self, data: List[float], window: int) -> List[float]:
        """Apply moving average smoothing to data."""
        if len(data) < window:
            return data
        
        smoothed = []
        for i in range(len(data)):
            start_idx = max(0, i - window // 2)
            end_idx = min(len(data), i + window // 2 + 1)
            smoothed.append(sum(data[start_idx:end_idx]) / (end_idx - start_idx))
        
        return smoothed
    
    def detect_corners(self) -> List[Corner]:
        """Detect corners using speed drops and steering angle increases."""
        self.progress_update.emit("Analyzing telemetry for corners...", 90)
        
        # Find start/finish line
        start_finish_idx = self.find_start_finish_line()
        
        if start_finish_idx > 0:
            self.progress_update.emit(f"Found start/finish line crossing - corners will be numbered from there", 92)
        
        # Extract and smooth data
        speeds = [d['speed'] for d in self.telemetry_data]
        steerings = [abs(d['steering']) for d in self.telemetry_data]
        
        speeds_smooth = self.smooth_data(speeds, self.smoothing_window)
        steerings_smooth = self.smooth_data(steerings, self.smoothing_window)
        
        corners = []
        corner_id = 1
        
        # Start corner detection AFTER the start/finish line
        i = start_finish_idx + 10
        
        while i < len(speeds_smooth) - 20 and self.is_running:
            entry_idx = self.find_corner_entry(speeds_smooth, steerings_smooth, i)
            
            if entry_idx is None:
                i += 5
                continue
            
            apex_idx = self.find_corner_apex(speeds_smooth, steerings_smooth, entry_idx)
            if apex_idx is None:
                i = entry_idx + 5
                continue
            
            exit_idx = self.find_corner_exit(speeds_smooth, steerings_smooth, apex_idx)
            if exit_idx is None:
                i = apex_idx + 5
                continue
            
            # Validate corner duration
            entry_time = self.telemetry_data[entry_idx]['timestamp']
            exit_time = self.telemetry_data[exit_idx]['timestamp']
            corner_duration = exit_time - entry_time
            
            if corner_duration >= self.min_corner_duration:
                corner = Corner(corner_id, entry_idx, apex_idx, exit_idx)
                corner.min_speed = min(speeds_smooth[entry_idx:exit_idx+1])
                corner.max_steering = max(steerings_smooth[entry_idx:exit_idx+1])
                corner.length = exit_idx - entry_idx
                corner.entry_lap_dist_pct = self.telemetry_data[entry_idx]['lap_dist_pct']
                corner.apex_lap_dist_pct = self.telemetry_data[apex_idx]['lap_dist_pct']
                corner.exit_lap_dist_pct = self.telemetry_data[exit_idx]['lap_dist_pct']
                
                corners.append(corner)
                
                # Emit corner detected signal
                description = f"Min Speed: {corner.min_speed:.1f} m/s, Track Position: {corner.apex_lap_dist_pct:.1%}"
                self.corner_detected.emit(corner_id, description)
                
                corner_id += 1
                i = exit_idx + 10
            else:
                i = entry_idx + 5
        
        self.corners = corners
        self.progress_update.emit(f"Corner detection complete: Found {len(corners)} corners", 95)
        return corners
    
    def find_corner_entry(self, speeds: List[float], steerings: List[float], start_idx: int) -> Optional[int]:
        """Find corner entry point using speed drop and steering increase."""
        for i in range(start_idx, min(start_idx + 30, len(speeds) - 10)):
            if i >= 5:
                speed_drop = speeds[i-5] - speeds[i+5]
                steering_increase = steerings[i+5] - steerings[i-5]
                
                if (speed_drop >= self.speed_drop_threshold and 
                    steering_increase >= self.steering_threshold):
                    return i
        return None
    
    def find_corner_apex(self, speeds: List[float], steerings: List[float], entry_idx: int) -> Optional[int]:
        """Find corner apex: minimum speed point with high steering."""
        search_end = min(entry_idx + 50, len(speeds))
        
        min_speed = float('inf')
        apex_idx = None
        
        for i in range(entry_idx, search_end):
            if speeds[i] < min_speed and steerings[i] >= self.steering_threshold:
                min_speed = speeds[i]
                apex_idx = i
        
        return apex_idx
    
    def find_corner_exit(self, speeds: List[float], steerings: List[float], apex_idx: int) -> Optional[int]:
        """Find corner exit: speed increase and steering decrease."""
        search_end = min(apex_idx + 40, len(speeds))
        
        for i in range(apex_idx + 5, search_end):
            if i + 5 < len(speeds):
                speed_increase = speeds[i+5] - speeds[i-5]
                steering_decrease = steerings[i-5] - steerings[i+5]
                
                if (speed_increase >= self.speed_drop_threshold * 0.5 and 
                    steering_decrease >= self.steering_threshold * 0.5):
                    return i
        return None
    
    def generate_track_map(self) -> Optional[Dict]:
        """Generate track map coordinates from velocity data using the velocity transformation formula."""
        self.progress_update.emit("Generating track map from velocity data...", 95)
        print("🗺️ [DEBUG] Starting track map generation...")
        
        if not self.telemetry_data:
            print("❌ [DEBUG] No telemetry data available for track map generation")
            return None
        
        print(f"📊 [DEBUG] Processing {len(self.telemetry_data)} telemetry points for track map")
        
        # Check if we have velocity data
        velocity_points = 0
        for point in self.telemetry_data:
            if point.get('VelocityX', 0.0) != 0 or point.get('VelocityY', 0.0) != 0:
                velocity_points += 1
        
        print(f"🚗 [DEBUG] Found {velocity_points}/{len(self.telemetry_data)} points with velocity data")
        
        if velocity_points == 0:
            print("❌ [DEBUG] No velocity data found - cannot generate track map")
            print("💡 [DEBUG] Make sure VelocityX and VelocityY are being collected during telemetry")
            return None
        
        # Convert telemetry data to track map format
        track_coordinates = []
        current_x = 0.0
        current_y = 0.0
        valid_transformations = 0
        
        print("🔄 [DEBUG] Starting velocity integration...")
        
        for i, point in enumerate(self.telemetry_data):
            velocity_x = point.get('VelocityX', 0.0)
            velocity_y = point.get('VelocityY', 0.0) 
            yaw = point.get('Yaw', 0.0)
            
            if velocity_x != 0 or velocity_y != 0:
                # Apply the velocity transformation formula
                global_vx = velocity_x * math.cos(yaw) - velocity_y * math.sin(yaw)
                global_vy = velocity_x * math.sin(yaw) + velocity_y * math.cos(yaw)
                
                # Integrate velocity to get position (assuming 10Hz data collection)
                dt = 0.1  # 10Hz = 0.1 seconds between samples
                current_x += global_vx * dt
                current_y += global_vy * dt
                
                track_coordinates.append({
                    'x': current_x,
                    'y': current_y,
                    'lap_dist_pct': point.get('lap_dist_pct', 0.0)
                })
                
                valid_transformations += 1
                
                # Debug first few transformations
                if i < 5:
                    print(f"   Point {i}: VelX={velocity_x:.3f}, VelY={velocity_y:.3f}, Yaw={yaw:.3f}")
                    print(f"   -> GlobalVX={global_vx:.3f}, GlobalVY={global_vy:.3f}")
                    print(f"   -> Position=({current_x:.2f}, {current_y:.2f})")
        
        print(f"✅ [DEBUG] Generated {valid_transformations} track coordinate points")
        
        if not track_coordinates:
            print("❌ [DEBUG] No track coordinates generated")
            return None
        
        # Calculate track bounds
        x_coords = [coord['x'] for coord in track_coordinates]
        y_coords = [coord['y'] for coord in track_coordinates]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        print(f"📏 [DEBUG] Track bounds: X=[{min_x:.2f}, {max_x:.2f}], Y=[{min_y:.2f}, {max_y:.2f}]")
        print(f"📐 [DEBUG] Track dimensions: {max_x - min_x:.2f}m x {max_y - min_y:.2f}m")
        
        track_map_data = {
            'coordinates': track_coordinates,
            'bounds': {
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y
            },
            'total_points': len(track_coordinates),
            'generation_method': 'velocity_integration'
        }
        
        print("✅ [DEBUG] Track map generation completed successfully")
        return track_map_data
    
    def save_results(self, corners: List[Corner], track_map_data: Optional[Dict] = None):
        """Save corner detection results to files and Supabase."""
        self.progress_update.emit("Saving corner detection results...", 98)
        print("💾 [DEBUG] Starting save process...")
        print(f"📊 [DEBUG] Saving {len(corners)} corners")
        
        if track_map_data:
            print(f"🗺️ [DEBUG] Saving track map with {track_map_data.get('total_points', 0)} coordinates")
            print(f"📏 [DEBUG] Track bounds: {track_map_data.get('bounds', {})}")
        else:
            print("❌ [DEBUG] No track map data to save")
        
        # Save to local files (backup)
        print("📁 [DEBUG] Saving to local files...")
        self._save_to_local_files(corners, track_map_data)
        
        # Save to Supabase
        print("☁️ [DEBUG] Saving to Supabase...")
        self._save_to_supabase(corners, track_map_data)
        
        self.progress_update.emit("Results saved to database and local files", 100)
        print("✅ [DEBUG] Save process completed")
    
    def _save_to_local_files(self, corners: List[Corner], track_map_data: Optional[Dict] = None):
        """Save corner detection results and track map to local files as backup."""
        # Create results directory if it doesn't exist
        results_dir = "corner_detection_results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save corner data and track map to JSON
        corners_data = {
            'detection_timestamp': timestamp,
            'total_corners': len(corners),
            'detection_parameters': {
                'speed_drop_threshold': self.speed_drop_threshold,
                'steering_threshold': math.degrees(self.steering_threshold),
                'min_corner_duration': self.min_corner_duration
            },
            'corners': [],
            'track_map': track_map_data
        }
        
        for corner in corners:
            corner_data = {
                'id': corner.id,
                'entry_idx': corner.entry_idx,
                'apex_idx': corner.apex_idx,
                'exit_idx': corner.exit_idx,
                'min_speed_ms': corner.min_speed,
                'max_steering_degrees': math.degrees(corner.max_steering),
                'entry_lap_dist_pct': corner.entry_lap_dist_pct,
                'apex_lap_dist_pct': corner.apex_lap_dist_pct,
                'exit_lap_dist_pct': corner.exit_lap_dist_pct
            }
            corners_data['corners'].append(corner_data)
        
        # Save to file
        json_filename = os.path.join(results_dir, f"corners_{timestamp}.json")
        with open(json_filename, 'w') as f:
            json.dump(corners_data, f, indent=2)
    
    def _save_to_supabase(self, corners: List[Corner], track_map_data: Optional[Dict] = None):
        """Save corner detection results and track map to Supabase tracks table."""
        try:
            # Get current track info from iRacing
            if not self.ir or not self.ir.is_connected:
                return
            
            track_name = self.ir['WeekendInfo']['TrackDisplayName']
            track_config = self.ir['WeekendInfo']['TrackConfigName'] 
            iracing_track_id = self.ir['WeekendInfo']['TrackID']
            iracing_config_id = self.ir['WeekendInfo'].get('TrackConfigID', None)  # Some tracks might not have this
            
            # Get Supabase client
            supabase = get_supabase_client()
            if not supabase:
                print("Warning: Could not connect to Supabase, corner data saved locally only")
                return
            
            # Prepare corner data for database
            corners_json = []
            for corner in corners:
                corner_data = {
                    'id': corner.id,
                    'entry_lap_dist_pct': corner.entry_lap_dist_pct,
                    'apex_lap_dist_pct': corner.apex_lap_dist_pct,
                    'exit_lap_dist_pct': corner.exit_lap_dist_pct,
                    'min_speed_ms': corner.min_speed,
                    'max_steering_degrees': math.degrees(corner.max_steering),
                    'detection_method': 'speed_drop_steering_increase'
                }
                corners_json.append(corner_data)
            
            # Prepare analysis metadata
            analysis_metadata = {
                'detection_timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_corners': len(corners),
                'detection_parameters': {
                    'speed_drop_threshold': self.speed_drop_threshold,
                    'steering_threshold': math.degrees(self.steering_threshold),
                    'min_corner_duration': self.min_corner_duration
                },
                'data_points_analyzed': len(self.telemetry_data),
                'collection_duration_seconds': self.collection_duration
            }
            
            # Find track record by iRacing track ID (much more reliable than name matching)
            full_track_name = f"{track_name} - {track_config}" if track_config != track_name else track_name
            
            # Check if track exists using iRacing track ID and config ID
            track_query = supabase.table('tracks').select('*').eq('iracing_track_id', iracing_track_id)
            if iracing_config_id is not None:
                track_query = track_query.eq('iracing_config_id', iracing_config_id)
            else:
                # If no config ID, match tracks with null config ID
                track_query = track_query.is_('iracing_config_id', 'null')
            
            existing_tracks = track_query.execute()
            
            if existing_tracks.data:
                # Update existing track
                track_id = existing_tracks.data[0]['id']
                
                update_data = {
                    'corners': corners_json,
                    'analysis_metadata': analysis_metadata,
                    'last_analysis_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'data_version': 1
                }
                
                # Add track map data if available
                if track_map_data:
                    print(f"🗺️ [DEBUG] Adding track map data to update: {len(track_map_data['coordinates'])} points")
                    update_data['track_map'] = track_map_data['coordinates']  # Save to 'track_map' field
                    print(f"📏 [DEBUG] Track bounds being saved: {track_map_data['bounds']}")
                else:
                    print("⚠️ [DEBUG] No track map data available to add to update")
                
                print(f"☁️ [DEBUG] Updating existing track record (ID: {track_id})")
                result = supabase.table('tracks').update(update_data).eq('id', track_id).execute()
                print(f"✅ [DEBUG] Updated corner data for track: {full_track_name}")
                print(f"📝 [DEBUG] Update result: {len(result.data) if result.data else 0} records updated")
                
            else:
                # Create new track record
                new_track = {
                    'name': track_name,
                    'config': track_config if track_config != track_name else None,
                    'iracing_track_id': iracing_track_id,
                    'iracing_config_id': iracing_config_id,
                    'corners': corners_json,
                    'analysis_metadata': analysis_metadata,
                    'last_analysis_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'data_version': 1
                }
                
                # Add track map data if available
                if track_map_data:
                    print(f"🗺️ [DEBUG] Adding track map data to new record: {len(track_map_data['coordinates'])} points")
                    new_track['track_map'] = track_map_data['coordinates']  # Save to 'track_map' field
                    print(f"📏 [DEBUG] Track bounds being saved: {track_map_data['bounds']}")
                else:
                    print("⚠️ [DEBUG] No track map data available to add to new record")
                
                print(f"☁️ [DEBUG] Creating new track record...")
                result = supabase.table('tracks').insert(new_track).execute()
                print(f"✅ [DEBUG] Created new track record with corner data: {full_track_name}")
                print(f"📝 [DEBUG] Insert result: {len(result.data) if result.data else 0} records created")
                
        except Exception as e:
            print(f"Warning: Could not save to Supabase: {str(e)}")
            print("Corner data saved locally only")


class CornerDetectionManager(QObject):
    """Manager class for integrating corner detection into TrackPro."""
    
    # Signals for UI updates
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(str, int)
    detection_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    existing_data_found = pyqtSignal(dict)  # Emitted when existing corner data is found
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.is_detecting = False
    
    def check_existing_corner_data(self) -> Optional[dict]:
        """Check if corner data already exists for the current track."""
        try:
            # Connect to iRacing to get track info
            ir = irsdk.IRSDK()
            if not ir.startup() or not ir.is_connected:
                return None
            
            track_name = ir['WeekendInfo']['TrackDisplayName']
            track_config = ir['WeekendInfo']['TrackConfigName']
            iracing_track_id = ir['WeekendInfo']['TrackID']
            iracing_config_id = ir['WeekendInfo'].get('TrackConfigID', None)
            ir.shutdown()
            
            # Get Supabase client
            supabase = get_supabase_client()
            if not supabase:
                return None
            
            # Query for existing track data using iRacing IDs
            track_query = supabase.table('tracks').select('*').eq('iracing_track_id', iracing_track_id)
            if iracing_config_id is not None:
                track_query = track_query.eq('iracing_config_id', iracing_config_id)
            else:
                track_query = track_query.is_('iracing_config_id', 'null')
            
            result = track_query.execute()
            
            if result.data and result.data[0].get('corners'):
                track_data = result.data[0]
                return {
                    'track_name': track_name,
                    'track_config': track_config,
                    'corners': track_data['corners'],
                    'analysis_metadata': track_data.get('analysis_metadata', {}),
                    'last_analysis_date': track_data.get('last_analysis_date'),
                    'total_corners': len(track_data['corners'])
                }
            
            return None
            
        except Exception as e:
            print(f"Error checking for existing corner data: {str(e)}")
            return None
    
    def load_corners_from_supabase(self) -> List[Corner]:
        """Load corner data from Supabase and convert to Corner objects."""
        existing_data = self.check_existing_corner_data()
        if not existing_data:
            return []
        
        corners = []
        for corner_data in existing_data['corners']:
            corner = Corner(
                corner_data['id'],
                0,  # entry_idx not stored in DB
                0,  # apex_idx not stored in DB  
                0   # exit_idx not stored in DB
            )
            corner.min_speed = corner_data.get('min_speed_ms', 0)
            corner.max_steering = math.radians(corner_data.get('max_steering_degrees', 0))
            corner.entry_lap_dist_pct = corner_data.get('entry_lap_dist_pct', 0)
            corner.apex_lap_dist_pct = corner_data.get('apex_lap_dist_pct', 0)
            corner.exit_lap_dist_pct = corner_data.get('exit_lap_dist_pct', 0)
            corners.append(corner)
        
        return corners

    def start_corner_detection(self, duration_seconds: int = 120, force_regenerate: bool = False):
        """Start the corner detection process."""
        if self.is_detecting:
            self.error_occurred.emit("Corner detection is already running!")
            return
        
        # Check for existing data first (unless forcing regeneration)
        if not force_regenerate:
            existing_data = self.check_existing_corner_data()
            if existing_data:
                self.existing_data_found.emit(existing_data)
                return
        
        self.is_detecting = True
        
        # Create and configure worker thread
        self.worker = CornerDetectionWorker()
        self.worker.set_collection_duration(duration_seconds)
        
        # Connect signals
        self.worker.progress_update.connect(self.progress_update.emit)
        self.worker.corner_detected.connect(self._on_corner_detected)
        self.worker.detection_complete.connect(self._on_detection_complete)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.connection_status.connect(self._on_connection_status)
        
        # Start the worker
        self.worker.start()
        
        self.status_update.emit("Corner detection started...")
    
    def stop_corner_detection(self):
        """Stop the corner detection process."""
        if self.worker and self.is_detecting:
            self.worker.stop_detection()
            self.status_update.emit("Stopping corner detection...")
    
    def _on_corner_detected(self, corner_id: int, description: str):
        """Handle corner detected signal."""
        self.status_update.emit(f"Found Turn {corner_id}: {description}")
    
    def _on_detection_complete(self, corners: List[Corner]):
        """Handle detection complete signal."""
        self.is_detecting = False
        self.status_update.emit(f"Corner detection complete! Found {len(corners)} corners.")
        self.detection_complete.emit(corners)
    
    def _on_error_occurred(self, error_message: str):
        """Handle error signal."""
        self.is_detecting = False
        self.error_occurred.emit(error_message)
    
    def _on_connection_status(self, connected: bool, message: str):
        """Handle connection status updates."""
        self.status_update.emit(message) 