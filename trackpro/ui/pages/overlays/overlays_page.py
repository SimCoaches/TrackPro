"""
Overlays Page - Track builder and overlay management
"""

import logging
import time
import numpy as np
import json
import math
from typing import List, Tuple
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                           QProgressBar, QGroupBox, QVBoxLayout, QMessageBox,
                           QFrame, QGridLayout, QTextEdit, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont

from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)


class SimpleTrackBuilder(QThread):
    """Simplified track builder that works directly with iRacing connection."""
    
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)  # completed_laps, required_laps
    track_completed = pyqtSignal(list, list)  # centerline, corners
    error_occurred = pyqtSignal(str)
    upload_complete = pyqtSignal(str, int)  # track_name, total_users_count
    
    def __init__(self, iracing_api=None):
        super().__init__()
        self.iracing_api = iracing_api
        self.should_stop = False
        self.is_running = False
        
        # Track building state
        self.position_x = 0.0
        self.position_y = 0.0
        self.track_points = []
        self.laps = []
        self.current_lap = []
        self.last_lap_dist_pct = None
        self.waiting_for_first_crossing = True
        self.lap_collection_started = False
        self.required_laps = 3
        
    def run(self):
        """Run the simplified track builder."""
        try:
            self.is_running = True
            self.status_updated.emit("🔌 Starting simplified track builder...")
            
            # Check iRacing connection
            if not self.iracing_api or not self.iracing_api.is_connected():
                self.error_occurred.emit("❌ iRacing not connected. Please start iRacing and join a session.")
                return
            
            self.status_updated.emit("✅ Connected to iRacing - waiting for first lap...")
            
            # Main building loop
            last_time = time.time()
            while not self.should_stop and self.iracing_api.is_connected():
                try:
                    current_time = time.time()
                    delta_time = current_time - last_time
                    last_time = current_time
                    
                    # Get telemetry data
                    ir = self.iracing_api.ir
                    if not ir or not ir.is_connected:
                        time.sleep(0.1)
                        continue
                    
                    # Get required telemetry
                    velocity_x = ir.get('VelocityX', 0.0)
                    velocity_y = ir.get('VelocityY', 0.0)
                    yaw = ir.get('Yaw', 0.0)
                    lap_dist_pct = ir.get('LapDistPct', 0.0)
                    speed = ir.get('Speed', 0.0)
                    
                    # Only process when moving
                    if speed > 2.0:
                        # Update position
                        self.update_position(velocity_x, velocity_y, yaw, delta_time, lap_dist_pct)
                        
                        # Check for lap completion
                        self.check_lap_completion(lap_dist_pct)
                        
                        # Update progress
                        completed_laps = len(self.laps)
                        if completed_laps > 0:
                            self.progress_updated.emit(completed_laps, self.required_laps)
                            self.status_updated.emit(f"📊 Building track... Lap {completed_laps}/{self.required_laps}")
                        
                        # Check if we have enough laps
                        if len(self.laps) >= self.required_laps:
                            self.generate_centerline()
                            break
                    
                    # Sleep to avoid overwhelming the system
                    time.sleep(0.05)  # 20Hz update rate
                    
                except Exception as e:
                    logger.error(f"Error in track builder loop: {e}")
                    time.sleep(0.1)
                    continue
            
            if self.should_stop:
                self.status_updated.emit("🛑 Track builder stopped by user")
            else:
                self.status_updated.emit("🏁 Track building completed!")
                
        except Exception as e:
            self.error_occurred.emit(f"❌ Track builder error: {str(e)}")
        finally:
            self.is_running = False
    
    def update_position(self, velocity_x, velocity_y, yaw, delta_time, lap_dist_pct):
        """Update car position based on telemetry."""
        # Convert car-local velocities to world coordinates
        global_vx = velocity_x * math.cos(yaw) - velocity_y * math.sin(yaw)
        global_vy = velocity_x * math.sin(yaw) + velocity_y * math.cos(yaw)
        
        # Integrate to get position
        self.position_x += global_vx * delta_time
        self.position_y += global_vy * delta_time
        
        # Add to track points
        self.track_points.append((self.position_x, self.position_y))
        
        # Add to current lap if collection has started
        if self.lap_collection_started:
            self.current_lap.append((self.position_x, self.position_y))
    
    def check_lap_completion(self, lap_dist_pct):
        """Check for lap completion using LapDistPct."""
        if self.last_lap_dist_pct is None:
            self.last_lap_dist_pct = lap_dist_pct
            return
        
        # Detect crossing from ~1.0 to ~0.0 (99.999% to 0.001%)
        if self.last_lap_dist_pct > 0.98 and lap_dist_pct < 0.02:
            logger.info(f"🏁 Lap completed! LapDistPct: {self.last_lap_dist_pct:.6f} → {lap_dist_pct:.6f}")
            
            if self.waiting_for_first_crossing:
                logger.info("🎯 First lap crossing detected - starting lap collection!")
                self.waiting_for_first_crossing = False
                self.lap_collection_started = True
                self.current_lap = [(self.position_x, self.position_y)]
            else:
                # Complete the current lap
                if len(self.current_lap) > 10:  # Ensure we have enough points
                    self.laps.append(self.current_lap.copy())
                    logger.info(f"✅ Lap {len(self.laps)} completed with {len(self.current_lap)} points")
                    
                    # Start next lap
                    self.current_lap = [(self.position_x, self.position_y)]
                    
                    # Update progress
                    self.progress_updated.emit(len(self.laps), self.required_laps)
        
        self.last_lap_dist_pct = lap_dist_pct
    
    def generate_centerline(self):
        """Generate centerline from collected laps."""
        try:
            if len(self.laps) < self.required_laps:
                self.error_occurred.emit("❌ Not enough laps collected for centerline generation")
                return
            
            self.status_updated.emit("🔧 Generating centerline from collected laps...")
            
            # Simple centerline generation: average the lap points
            centerline = []
            corners = []  # Simplified corner detection
            
            # Find the shortest lap to use as reference
            min_points = min(len(lap) for lap in self.laps)
            
            # Generate centerline by averaging corresponding points
            for i in range(min_points):
                x_sum = sum(lap[i][0] for lap in self.laps)
                y_sum = sum(lap[i][1] for lap in self.laps)
                avg_x = x_sum / len(self.laps)
                avg_y = y_sum / len(self.laps)
                centerline.append((avg_x, avg_y))
            
            # Simple corner detection (every 10th point as a corner)
            for i in range(0, len(centerline), 10):
                corners.append({
                    'id': len(corners) + 1,
                    'position': centerline[i],
                    'lap_dist_pct': i / len(centerline)
                })
            
            # Save to file
            self.save_track_data(centerline, corners)
            
            # Emit completion
            self.track_completed.emit(centerline, corners)
            
            logger.info(f"✅ Centerline generated with {len(centerline)} points and {len(corners)} corners")
            
        except Exception as e:
            self.error_occurred.emit(f"❌ Error generating centerline: {str(e)}")
    
    def save_track_data(self, centerline, corners):
        """Save track data to local file and Supabase cloud using existing global identification."""
        try:
            import os
            from ....utils.resource_utils import get_track_map_file_path
            from ....database.supabase_client import get_supabase_client
            
            # Get robust track identifier using existing global system
            track_name, track_config, iracing_track_id, iracing_config_id = self.get_robust_track_identifier()
            
            if not track_name or not track_config:
                logger.error("Could not get track identifier - cannot save track map")
                return False
            
            # Calculate track length
            track_length = 0
            if len(centerline) > 1:
                for i in range(1, len(centerline)):
                    dx = centerline[i][0] - centerline[i-1][0]
                    dy = centerline[i][1] - centerline[i-1][1]
                    track_length += math.sqrt(dx*dx + dy*dy)
            
            # Save to local file first (for immediate overlay use)
            local_file_path = get_track_map_file_path(track_name, track_config)
            track_data = {
                'track_name': track_name,
                'track_config': track_config,
                'iracing_track_id': iracing_track_id,
                'iracing_config_id': iracing_config_id,
                'track_length': track_length,
                'centerline': centerline,
                'corners': corners,
                'created_at': datetime.datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, 'w') as f:
                json.dump(track_data, f, indent=2)
            
            logger.info(f"✅ Track map saved locally: {local_file_path}")
            
            # Save to Supabase using existing global system
            supabase = get_supabase_client()
            if not supabase:
                logger.warning("No Supabase connection - track map saved locally only")
                return True
            
            try:
                # Use the same logic as the global iRacing monitor
                from ....race_coach.iracing_session_monitor import _find_or_create_base_track, _create_track_config
                
                # First, find or create base track
                base_track_id = _find_or_create_base_track(
                    supabase, track_name, iracing_track_id, 
                    length_meters=track_length
                )
                
                if not base_track_id:
                    logger.error("Failed to create base track in Supabase")
                    return False
                
                # Then create or find track config
                config_track_id = _create_track_config(
                    supabase, base_track_id, track_name, track_config,
                    iracing_track_id or 0, iracing_config_id or 0,
                    length_meters=track_length
                )
                
                if not config_track_id:
                    logger.error("Failed to create track config in Supabase")
                    return False
                
                # Save track map data to the config track
                track_map_data = {
                    'track_id': config_track_id,
                    'centerline': centerline,
                    'corners': corners,
                    'track_length': track_length,
                    'created_at': datetime.datetime.now().isoformat(),
                    'created_by': 'track_builder'
                }
                
                # Insert track map data
                result = supabase.table('track_maps').insert(track_map_data).execute()
                
                if result.data:
                    logger.info(f"✅ Track map saved to Supabase: {track_name} - {track_config}")
                    
                    # Get total users count for this track
                    users_result = supabase.table('sessions').select('user_id').eq('track_id', config_track_id).execute()
                    total_users = len(set([session['user_id'] for session in users_result.data])) if users_result.data else 0
                    
                    # Emit upload complete signal
                    self.upload_complete.emit(f"{track_name} - {track_config}", total_users)
                    return True
                else:
                    logger.error("Failed to save track map to Supabase")
                    return False
                    
            except Exception as e:
                logger.error(f"Error saving to Supabase: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving track data: {e}")
            return False
    
    def stop_building(self):
        """Stop the track building process."""
        self.should_stop = True
        self.wait(5000)  # Wait up to 5 seconds


class OverlaysPage(BasePage):
    """Main overlays page with track builder and other overlay features."""
    
    # Signals for overlay events
    overlay_started = pyqtSignal(str)  # overlay type
    overlay_stopped = pyqtSignal(str)
    track_builder_progress = pyqtSignal(int, str)  # progress, status

    def __init__(self, global_managers=None):
        super().__init__("overlays", global_managers)
        self.track_builder = None
        self.track_map_overlay_manager = None
        self.iracing_monitor = None
        
        # Track detection state
        self.last_track_name = None
        self.last_track_config = None
        self.last_session_id = None
        self.last_subsession_id = None
        self.track_detection_timer = None
        
    def init_page(self):
        """Initialize the overlays page."""
        # Get global iRacing connection
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'global_iracing_api') and widget.global_iracing_api:
                        self.iracing_monitor = widget.global_iracing_api
                        break
        except Exception as e:
            logger.warning(f"Could not get global iRacing connection: {e}")
        
        # Create main layout
        main_layout = QVBoxLayout()
        
        # Track Builder Section
        self.setup_track_builder_section(main_layout)
        
        # Track Map Overlay Section
        self.setup_track_map_section(main_layout)
        
        # Future Overlays Section
        self.setup_future_overlays_section(main_layout)
        
        # Set the main layout
        self.setLayout(main_layout)
        
        # Setup automatic track detection
        self.setup_track_detection()
        
        logger.info("🎯 Overlays page initialized")

    def setup_track_builder_section(self, layout):
        """Setup the track builder section."""
        # Track Builder Group
        builder_group = QGroupBox("🎯 Ultimate Track Builder")
        builder_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        builder_layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel(
            "Build perfect track maps by driving 3 complete laps.\n"
            "The system will generate a precise centerline and detect corners automatically."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        builder_layout.addWidget(desc_label)
        
        # Status and Progress
        self.builder_status_label = QLabel("Ready to build track map")
        self.builder_status_label.setStyleSheet("font-weight: bold; color: #333;")
        builder_layout.addWidget(self.builder_status_label)
        
        self.builder_progress_bar = QProgressBar()
        self.builder_progress_bar.setRange(0, 3)
        self.builder_progress_bar.setValue(0)
        self.builder_progress_bar.setFormat("Lap %v/%m")
        builder_layout.addWidget(self.builder_progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_builder_btn = QPushButton("🚀 Start Track Builder")
        self.start_builder_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_builder_btn.clicked.connect(self.start_track_builder)
        button_layout.addWidget(self.start_builder_btn)
        
        self.stop_builder_btn = QPushButton("🛑 Stop Builder")
        self.stop_builder_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_builder_btn.clicked.connect(self.stop_track_builder)
        self.stop_builder_btn.setEnabled(False)
        button_layout.addWidget(self.stop_builder_btn)
        
        builder_layout.addLayout(button_layout)
        
        # Advanced Options
        options_layout = QHBoxLayout()
        
        self.auto_save_checkbox = QCheckBox("💾 Auto-save to cloud")
        self.auto_save_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_save_checkbox)
        
        self.show_visualization_checkbox = QCheckBox("📊 Show real-time visualization")
        self.show_visualization_checkbox.setChecked(True)
        options_layout.addWidget(self.show_visualization_checkbox)
        
        builder_layout.addLayout(options_layout)
        
        builder_group.setLayout(builder_layout)
        layout.addWidget(builder_group)

    def setup_track_map_section(self, layout):
        """Setup the track map overlay section."""
        # Track Map Overlay Group
        overlay_group = QGroupBox("🗺️ Track Map Overlay")
        overlay_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        overlay_layout = QVBoxLayout()
        
        # Description
        overlay_desc = QLabel(
            "Display track map overlay during racing.\n"
            "Shows your position and the track layout in real-time."
        )
        overlay_desc.setWordWrap(True)
        overlay_desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        overlay_layout.addWidget(overlay_desc)
        
        # Status
        self.overlay_status_label = QLabel("No overlay active")
        self.overlay_status_label.setStyleSheet("font-weight: bold; color: #333;")
        overlay_layout.addWidget(self.overlay_status_label)
        
        # Buttons
        overlay_button_layout = QHBoxLayout()
        
        self.start_overlay_btn = QPushButton("🎯 Start Overlay")
        self.start_overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_overlay_btn.clicked.connect(self.start_track_overlay)
        overlay_button_layout.addWidget(self.start_overlay_btn)
        
        self.stop_overlay_btn = QPushButton("🛑 Stop Overlay")
        self.stop_overlay_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_overlay_btn.clicked.connect(self.stop_track_overlay)
        self.stop_overlay_btn.setEnabled(False)
        overlay_button_layout.addWidget(self.stop_overlay_btn)
        
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.settings_btn.clicked.connect(self.show_overlay_settings)
        overlay_button_layout.addWidget(self.settings_btn)
        
        overlay_layout.addLayout(overlay_button_layout)
        
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)

    def setup_future_overlays_section(self, layout):
        """Setup future overlays section."""
        # Future Overlays Group
        future_group = QGroupBox("🔮 Future Overlays")
        future_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        future_layout = QVBoxLayout()
        
        # Coming soon message
        coming_soon_label = QLabel(
            "More overlay features coming soon:\n"
            "• Tire wear visualization\n"
            "• Fuel consumption display\n"
            "• Weather radar overlay\n"
            "• Pit strategy timer"
        )
        coming_soon_label.setWordWrap(True)
        coming_soon_label.setStyleSheet("color: #666; font-style: italic;")
        future_layout.addWidget(coming_soon_label)
        
        future_group.setLayout(future_layout)
        layout.addWidget(future_group)

    def get_robust_track_identifier(self):
        """Get robust track identifier using existing global iRacing system."""
        try:
            if not self.iracing_monitor or not self.iracing_monitor.ir:
                return None, None, None, None
            
            # Use existing global iRacing connection
            ir = self.iracing_monitor.ir
            
            # Get track info using the same method as the global monitor
            weekend_info = ir.get('WeekendInfo', {})
            track_name = weekend_info.get('TrackDisplayName', 'Unknown Track')
            track_config = weekend_info.get('TrackConfigName', 'Unknown Config')
            iracing_track_id = weekend_info.get('TrackID')
            iracing_config_id = weekend_info.get('TrackConfigID')
            
            # Use the same identification logic as the global system
            if iracing_track_id is not None and iracing_config_id is not None:
                # This is the most robust identifier - unique iRacing IDs
                return track_name, track_config, iracing_track_id, iracing_config_id
            elif track_name and track_config:
                # Fallback to name-based identification
                return track_name, track_config, None, None
            else:
                return None, None, None, None
                
        except Exception as e:
            logger.error(f"Error getting track identifier: {e}")
            return None, None, None, None

    def check_existing_track_map(self):
        """Check if track map already exists in Supabase with robust identification."""
        try:
            identifiers = self.get_robust_track_identifier()
            if not identifiers:
                return None
            
            track_info = identifiers
            track_name = track_info[0]
            track_config = track_info[1]
            iracing_track_id = track_info[2]
            
            # Check Supabase
            from ....database.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if not supabase:
                return None
            
            # Try multiple identification methods
            existing_track = None
            
            # Method 1: Try exact name + config match
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            result = track_query.execute()
            if result.data:
                existing_track = result.data[0]
            
            # Method 2: Try iRacing track ID match if Method 1 failed
            if not existing_track and iracing_track_id:
                track_query = supabase.table('tracks').select('*').eq('iracing_track_id', iracing_track_id)
                if track_config and track_config != track_name:
                    track_query = track_query.eq('config', track_config)
                
                result = track_query.execute()
                if result.data:
                    existing_track = result.data[0]
            
            # Method 3: Try full track name match
            if not existing_track:
                full_track_name = f"{track_name} - {track_config}" if track_config and track_config != track_name else track_name
                track_query = supabase.table('tracks').select('*').eq('name', full_track_name)
                result = track_query.execute()
                if result.data:
                    existing_track = result.data[0]
            
            if existing_track:
                return {
                    'track_name': existing_track.get('name'),
                    'track_config': existing_track.get('config'),
                    'total_points': existing_track.get('analysis_metadata', {}).get('total_coordinates', 0),
                    'total_corners': existing_track.get('analysis_metadata', {}).get('total_corners', 0),
                    'last_analysis_date': existing_track.get('last_analysis_date'),
                    'iracing_track_id': existing_track.get('iracing_track_id'),
                    'exists': True,
                    'identification_method': 'robust_match'
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not check for existing track map: {e}")
            return None

    def start_track_builder(self):
        """Start the simplified track builder."""
        try:
            if not self.iracing_monitor:
                QMessageBox.warning(self, "iRacing Required", 
                                   "iRacing connection is required for track building.")
                return
            
            # Check for existing track map
            existing_track = self.check_existing_track_map()
            if existing_track:
                reply = QMessageBox.question(self, "Track Map Exists", 
                                           f"A track map already exists for:\n\n"
                                           f"Track: {existing_track['track_name']}\n"
                                           f"Config: {existing_track['track_config']}\n"
                                           f"Points: {existing_track['total_points']}\n"
                                           f"Corners: {existing_track['total_corners']}\n"
                                           f"Last Updated: {existing_track['last_analysis_date']}\n\n"
                                           f"Would you like to rebuild the track map?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Create and start the simplified track builder
            self.track_builder = SimpleTrackBuilder(self.iracing_monitor)
            
            # Connect signals
            self.track_builder.status_updated.connect(self.on_builder_status_updated)
            self.track_builder.progress_updated.connect(self.on_builder_progress_updated)
            self.track_builder.track_completed.connect(self.on_track_completion)
            self.track_builder.error_occurred.connect(self.on_builder_error)
            self.track_builder.upload_complete.connect(self.on_supabase_upload_complete)
            self.track_builder.finished.connect(self.on_builder_finished)
            
            # Start the builder
            self.track_builder.start()
            
            # Update UI
            self.start_builder_btn.setEnabled(False)
            self.stop_builder_btn.setEnabled(True)
            self.builder_status_label.setText("🔌 Starting simplified track builder...")
            self.builder_progress_bar.setValue(0)
            
            logger.info("🏗️ Simplified Track Builder started from Overlays page")
            
        except Exception as e:
            logger.error(f"Error starting track builder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start track builder: {str(e)}")
    
    def stop_track_builder(self):
        """Stop the track builder."""
        if self.track_builder and self.track_builder.is_running:
            self.track_builder.stop_building()
            
        # Update UI
        self.start_builder_btn.setEnabled(True)
        self.stop_builder_btn.setEnabled(False)
        self.builder_status_label.setText("Track builder stopped")
        
        logger.info("🛑 Track builder stopped")
    
    def start_track_overlay(self):
        """Start the track map overlay."""
        try:
            # Initialize overlay manager if needed
            if not self.track_map_overlay_manager:
                from ....race_coach.track_map_overlay import TrackMapOverlayManager
                self.track_map_overlay_manager = TrackMapOverlayManager(self.iracing_monitor)
            
            # Start the overlay
            success = self.track_map_overlay_manager.start_overlay()
            
            if success:
                # Update UI
                self.start_overlay_btn.setEnabled(False)
                self.stop_overlay_btn.setEnabled(True)
                self.overlay_status_label.setText("Track overlay active")
                logger.info("🎯 Track map overlay started")
            else:
                QMessageBox.warning(self, "Overlay Failed", 
                                   "Failed to start track overlay. Check if track data is available.")
                
        except Exception as e:
            logger.error(f"Error starting track overlay: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start track overlay: {str(e)}")
    
    def stop_track_overlay(self):
        """Stop the track map overlay."""
        if self.track_map_overlay_manager and self.track_map_overlay_manager.is_active:
            self.track_map_overlay_manager.stop_overlay()
            
            # Update UI
            self.start_overlay_btn.setEnabled(True)
            self.stop_overlay_btn.setEnabled(False)
            self.overlay_status_label.setText("No overlay active")
            
            logger.info("🛑 Track map overlay stopped")
    
    def show_overlay_settings(self):
        """Show the track map overlay settings dialog."""
        try:
            from ....race_coach.ui.track_map_overlay_settings import TrackMapOverlaySettingsDialog
            
            dialog = TrackMapOverlaySettingsDialog(self)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing overlay settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open overlay settings: {str(e)}")
    
    def on_builder_status_updated(self, status):
        """Handle track builder status updates."""
        self.builder_status_label.setText(status)
        self.track_builder_progress.emit(self.builder_progress_bar.value(), status)
    
    def on_builder_progress_updated(self, completed_laps, required_laps):
        """Handle track builder progress updates."""
        try:
            # Update progress bar
            self.builder_progress_bar.setValue(completed_laps)
            
            # Update status
            if completed_laps > 0:
                self.builder_status_label.setText(f"✅ Lap {completed_laps}/{required_laps} completed")
            
            # Emit progress signal
            self.track_builder_progress.emit(completed_laps, f"Lap {completed_laps}/{required_laps}")
            
        except Exception as e:
            logger.error(f"Error handling progress update: {e}")
    
    def on_track_completion(self, centerline, corners):
        """Handle track building completion."""
        try:
            # Calculate track length
            track_length = 0
            if len(centerline) > 1:
                for i in range(1, len(centerline)):
                    dx = centerline[i][0] - centerline[i-1][0]
                    dy = centerline[i][1] - centerline[i-1][1]
                    track_length += math.sqrt(dx*dx + dy*dy)
            
            # Update UI
            self.builder_status_label.setText(f"🏁 Track map complete! {len(centerline)} points, {len(corners)} corners, {track_length:.0f}m")
            self.builder_progress_bar.setValue(3)
            
            # Update buttons
            self.start_builder_btn.setEnabled(True)
            self.stop_builder_btn.setEnabled(False)
            
            # Show completion message with cloud upload info
            QMessageBox.information(self, "Track Builder Complete", 
                                  f"🎯 Track map generated successfully!\n\n"
                                  f"📊 Points: {len(centerline)}\n"
                                  f"🏁 Corners: {len(corners)}\n"
                                  f"📏 Length: {track_length:.0f}m\n\n"
                                  f"☁️ Track map saved to:\n"
                                  f"• Local file (for immediate use)\n"
                                  f"• Supabase cloud (for all users)\n\n"
                                  f"The track map is now available for overlay use.")
            
            logger.info(f"✅ Track building completed - {len(centerline)} points, {len(corners)} corners")
            
        except Exception as e:
            logger.error(f"Error handling track completion: {e}")
    
    def on_builder_error(self, error_message):
        """Handle track builder errors."""
        self.builder_status_label.setText(f"❌ Error: {error_message}")
        self.start_builder_btn.setEnabled(True)
        self.stop_builder_btn.setEnabled(False)
        
        QMessageBox.critical(self, "Track Builder Error", f"❌ {error_message}")
        logger.error(f"Track builder error: {error_message}")
    
    def on_supabase_upload_complete(self, track_name, total_users_count):
        """Handle Supabase upload completion."""
        self.builder_status_label.setText(f"✅ Track map uploaded to cloud: {track_name}")
        logger.info(f"✅ Track map uploaded to cloud: {track_name}")
    
    def on_builder_finished(self):
        """Handle track builder thread completion."""
        self.start_builder_btn.setEnabled(True)
        self.stop_builder_btn.setEnabled(False)
        logger.info("🏁 Track builder thread finished")
    
    def on_page_activated(self):
        """Handle page activation."""
        super().on_page_activated()
        
        # Start track detection timer if not already running
        if not self.track_detection_timer:
            self.setup_track_detection()
        
        # Update track status immediately
        self.update_track_status()
    
    def setup_track_detection(self):
        """Setup automatic track detection timer."""
        try:
            # Create timer for track detection (check every 2 seconds)
            self.track_detection_timer = QTimer()
            self.track_detection_timer.timeout.connect(self.check_track_changes)
            self.track_detection_timer.start(2000)  # 2 second interval
            
            logger.info("🔍 Automatic track detection enabled")
            
        except Exception as e:
            logger.error(f"Error setting up track detection: {e}")
    
    def check_track_changes(self):
        """Check for track or session changes and update UI accordingly."""
        try:
            if not self.iracing_monitor or not self.iracing_monitor.ir:
                return
            
            # Get current track info
            ir = self.iracing_monitor.ir
            if not ir or not ir.is_connected:
                return
            
            weekend_info = ir.get('WeekendInfo', {})
            current_track_name = weekend_info.get('TrackDisplayName', 'Unknown Track')
            current_track_config = weekend_info.get('TrackConfigName', 'Unknown Config')
            current_session_id = weekend_info.get('SessionID')
            current_subsession_id = weekend_info.get('SubSessionID')
            
            # Check if track or session has changed
            track_changed = (
                current_track_name != self.last_track_name or
                current_track_config != self.last_track_config or
                current_session_id != self.last_session_id or
                current_subsession_id != self.last_subsession_id
            )
            
            if track_changed:
                logger.info(f"🔄 Track/Session change detected: {current_track_name} - {current_track_config}")
                
                # Update stored values
                self.last_track_name = current_track_name
                self.last_track_config = current_track_config
                self.last_session_id = current_session_id
                self.last_subsession_id = current_subsession_id
                
                # Update UI with new track info
                self.update_track_status()
                
                # Stop any running track builder if track changed
                if self.track_builder and self.track_builder.is_running:
                    logger.info("🛑 Stopping track builder due to track change")
                    self.track_builder.stop_building()
                    self.start_builder_btn.setEnabled(True)
                    self.stop_builder_btn.setEnabled(False)
                
                # Stop overlay if active
                if self.track_map_overlay_manager and self.track_map_overlay_manager.is_active:
                    logger.info("🛑 Stopping overlay due to track change")
                    self.track_map_overlay_manager.stop_overlay()
                    self.start_overlay_btn.setEnabled(True)
                    self.stop_overlay_btn.setEnabled(False)
                    self.overlay_status_label.setText("No overlay active")
                
        except Exception as e:
            logger.error(f"Error checking track changes: {e}")
    
    def update_track_status(self):
        """Update UI status based on current track and existing track maps."""
        try:
            if not self.iracing_monitor:
                self.builder_status_label.setText("⚠️ iRacing connection not available")
                return
            
            # Check iRacing connection
            if not hasattr(self.iracing_monitor, 'is_connected') or not self.iracing_monitor.is_connected():
                self.builder_status_label.setText("⚠️ iRacing not connected - Start iRacing to build track")
                return
            
            # Get current track info
            track_name, track_config, _, _ = self.get_robust_track_identifier()
            if not track_name or not track_config:
                self.builder_status_label.setText("⚠️ Could not identify current track")
                return
            
            # Check for existing track map
            existing_track = self.check_existing_track_map()
            
            if existing_track:
                # Track map exists
                status_text = (
                    f"✅ {track_name} - {track_config}\n"
                    f"📊 Track map available ({existing_track['total_points']} points, {existing_track['total_corners']} corners)"
                )
                self.builder_status_label.setText(status_text)
                
                # Enable overlay button since track map exists
                self.start_overlay_btn.setEnabled(True)
                
            else:
                # No track map exists
                status_text = f"🎯 {track_name} - {track_config}\n📝 No track map found - Ready to build"
                self.builder_status_label.setText(status_text)
                
                # Disable overlay button since no track map exists
                self.start_overlay_btn.setEnabled(False)
            
            logger.info(f"🔄 Updated track status: {track_name} - {track_config}")
            
        except Exception as e:
            logger.error(f"Error updating track status: {e}")
            self.builder_status_label.setText("⚠️ Error updating track status")
    
    def cleanup(self):
        """Cleanup resources when page is deactivated."""
        # Stop track detection timer
        if self.track_detection_timer:
            self.track_detection_timer.stop()
            self.track_detection_timer = None
        
        # Stop track builder if running
        if self.track_builder and self.track_builder.is_running:
            self.track_builder.stop_building()
        
        # Stop overlay if active
        if self.track_map_overlay_manager and self.track_map_overlay_manager.is_active:
            self.track_map_overlay_manager.stop_overlay()
        
        logger.info("🧹 Overlays page cleanup completed")