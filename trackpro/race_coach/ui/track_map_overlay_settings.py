"""
Track Map Overlay Settings Dialog
Configuration UI for the transparent track map overlay
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QGroupBox, QSlider, QCheckBox, QSpinBox,
                           QColorDialog, QLineEdit, QTabWidget, QWidget,
                           QMessageBox, QFrame, QGridLayout, QProgressBar,
                           QTextEdit, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QColor, QPalette, QFont

from ..track_map_overlay import TrackMapOverlayManager
import os
import json
import logging

logger = logging.getLogger(__name__)


class TrackBuilderThread(QThread):
    """Thread for running the ultimate track builder."""
    
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)  # completed_laps, required_laps
    centerline_generated = pyqtSignal(str)  # file_path
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
        self.track_builder = None
        
    def run(self):
        """Run the track builder in a separate thread."""
        try:
            # Import the ultimate track builder
            import sys
            import os
            # Add project root to path for importing ultimate_track_builder
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from ultimate_track_builder import UltimateTrackBuilder
            
            self.status_updated.emit("🔌 Connecting to iRacing...")
            
            # Create and configure the track builder
            builder = UltimateTrackBuilder(enable_gui=False)
            self.track_builder = builder
            
            if not builder.connect():
                self.error_occurred.emit("❌ Cannot connect to iRacing. Make sure iRacing is running.")
                return
            
            self.status_updated.emit("✅ Connected! Waiting for movement to start 3-lap collection...")
            
            # Override the update_track method to emit signals
            original_update_track = builder.update_track
            
            def threaded_update_track(frame):
                if self.should_stop:
                    return
                    
                # Call original method
                result = original_update_track(frame)
                
                # Emit progress updates
                completed_laps, required_laps = builder.track_builder.get_lap_progress()
                self.progress_updated.emit(completed_laps, required_laps)
                
                # Check if centerline is generated
                if builder.centerline_track is not None and not hasattr(self, '_centerline_emitted'):
                    self._centerline_emitted = True
                    self.status_updated.emit("🎯 Centerline generated! Saving track map...")
                    
                    # Save the track map locally and to Supabase
                    try:
                        import numpy as np
                        track_length = 0
                        if len(builder.centerline_track) > 1:
                            for i in range(1, len(builder.centerline_track)):
                                dx = builder.centerline_track[i][0] - builder.centerline_track[i-1][0]
                                dy = builder.centerline_track[i][1] - builder.centerline_track[i-1][1]
                                track_length += np.sqrt(dx*dx + dy*dy)
                        
                        import time
                        track_data = {
                            'centerline_positions': builder.centerline_track.tolist(),
                            'source_laps': builder.track_builder.laps,
                            'raw_positions': builder.track_builder.track_points,
                            'length_meters': track_length,
                            'points_count': len(builder.centerline_track),
                            'laps_used': len(builder.track_builder.laps),
                            'method': '3_lap_centerline_averaging',
                            'generation_timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Save locally first
                        file_path = 'centerline_track_map.json'
                        with open(file_path, 'w') as f:
                            json.dump(track_data, f, indent=2)
                        
                        # Save to Supabase for sharing with all users
                        supabase_saved = self._save_to_supabase(builder, track_data, track_length)
                        
                        self.centerline_generated.emit(file_path)
                        
                        if supabase_saved:
                            self.status_updated.emit(f"✅ Track map saved locally & to cloud! ({len(builder.centerline_track)} points, {track_length:.0f}m)")
                        else:
                            self.status_updated.emit(f"✅ Track map saved locally! ({len(builder.centerline_track)} points, {track_length:.0f}m) - Cloud save failed")
                        
                    except Exception as e:
                        self.error_occurred.emit(f"Error saving track map: {str(e)}")
                
                return result
            
            builder.update_track = threaded_update_track
            
            # Run the builder - handle GUI vs non-GUI mode
            try:
                if builder.enable_gui and builder.fig is not None:
                    # GUI mode with matplotlib animation
                    from matplotlib.animation import FuncAnimation
                    import matplotlib.pyplot as plt
                    anim = FuncAnimation(builder.fig, builder.update_track, interval=100, blit=False, cache_frame_data=False)
                    
                    # Keep the thread alive while building
                    while not self.should_stop and not builder.track_builder.centerline_generated:
                        self.msleep(100)
                        
                        # Update status based on current state
                        if builder.building:
                            completed_laps, required_laps = builder.track_builder.get_lap_progress()
                            if builder.track_builder.waiting_for_first_crossing:
                                self.status_updated.emit("🏁 Waiting for start/finish line crossing...")
                            else:
                                self.status_updated.emit(f"🏁 Collecting laps: {completed_laps}/{required_laps}")
                else:
                    # Non-GUI mode - manual update loop (like standalone mode)
                    import time
                    frame_count = 0
                    last_status_time = time.time()
                    
                    while not self.should_stop and not builder.track_builder.centerline_generated:
                        try:
                            # Manually call update_track (this is the key fix!)
                            builder.update_track(frame_count)
                            frame_count += 1
                            
                            # Status updates every 2 seconds
                            current_time = time.time()
                            if current_time - last_status_time > 2.0:
                                completed_laps, required_laps = builder.track_builder.get_lap_progress()
                                if builder.centerline_track is not None:
                                    break  # Centerline complete
                                elif builder.building:
                                    if builder.track_builder.waiting_for_first_crossing:
                                        self.status_updated.emit("🏁 Waiting for start/finish line crossing...")
                                    else:
                                        self.status_updated.emit(f"🏁 Collecting laps: {completed_laps}/{required_laps} - Current: {len(builder.track_builder.current_lap)} pts")
                                else:
                                    self.status_updated.emit("⏳ Waiting for movement to start building...")
                                last_status_time = current_time
                            
                            # Small delay to prevent excessive CPU usage
                            self.msleep(50)  # 20 FPS update rate
                            
                        except Exception as e:
                            self.error_occurred.emit(f"Error in track building loop: {str(e)}")
                            break
                
            except Exception as e:
                self.error_occurred.emit(f"Error during track building: {str(e)}")
            finally:
                if builder.ir:
                    builder.ir.shutdown()
                try:
                    import matplotlib.pyplot as plt
                    plt.close('all')
                except:
                    pass
                
        except ImportError as e:
            self.error_occurred.emit(f"❌ Could not import ultimate track builder: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"❌ Error: {str(e)}")
    
    def stop(self):
        """Stop the track builder thread."""
        self.should_stop = True
        if self.track_builder and hasattr(self.track_builder, 'ir') and self.track_builder.ir:
            self.track_builder.ir.shutdown()

    def _save_to_supabase(self, builder, track_data, track_length):
        """Save the generated track map to Supabase for sharing with all users."""
        try:
            # Import Supabase client
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from trackpro.database.supabase_client import get_supabase_client
            
            # Get track info from iRacing
            if not builder.ir or not builder.ir.is_connected:
                logger.warning("iRacing not connected, cannot get track info for Supabase save")
                return False
            
            track_name = builder.ir['WeekendInfo']['TrackDisplayName']
            track_config = builder.ir['WeekendInfo']['TrackConfigName'] 
            iracing_track_id = builder.ir['WeekendInfo']['TrackID']
            
            # Get Supabase client
            supabase = get_supabase_client()
            if not supabase:
                logger.warning("Could not connect to Supabase")
                return False
            
            # Prepare track map data for Supabase (convert to coordinate format)
            track_map_data = []
            for point in track_data['centerline_positions']:
                track_map_data.append({
                    'x': point[0],
                    'y': point[1]
                })
            
            # Prepare analysis metadata
            analysis_metadata = {
                'generation_method': 'ultimate_track_builder_3_lap_averaging',
                'generation_timestamp': track_data.get('generation_timestamp', ''),
                'total_coordinates': len(track_map_data),
                'track_length_meters': track_length,
                'laps_used_for_generation': track_data.get('laps_used', 3),
                'data_source': 'iracing_velocity_integration_centerline',
                'quality_score': 'high',  # 3-lap averaging provides high quality
                'generation_tool': 'trackpro_ultimate_track_builder'
            }
            
            # Find or create track record
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            existing_tracks = track_query.execute()
            
            if existing_tracks.data:
                # Update existing track
                track_id = existing_tracks.data[0]['id']
                
                update_data = {
                    'track_map': track_map_data,
                    'analysis_metadata': analysis_metadata,
                    'last_analysis_date': 'now()',
                    'length_meters': track_length,
                    'data_version': 2  # Version 2 indicates centerline data
                }
                
                result = supabase.table('tracks').update(update_data).eq('id', track_id).execute()
                
                if result.data:
                    logger.info(f"✅ Updated existing track in Supabase: {track_name}")
                    return True
                else:
                    logger.error(f"Failed to update track in Supabase: {track_name}")
                    return False
                    
            else:
                # Create new track record
                new_track = {
                    'name': track_name,
                    'config': track_config if track_config != track_name else None,
                    'iracing_track_id': iracing_track_id,
                    'length_meters': track_length,
                    'track_map': track_map_data,
                    'analysis_metadata': analysis_metadata,
                    'last_analysis_date': 'now()',
                    'data_version': 2  # Version 2 indicates centerline data
                }
                
                result = supabase.table('tracks').insert(new_track).execute()
                
                if result.data:
                    logger.info(f"✅ Created new track record in Supabase: {track_name}")
                    return True
                else:
                    logger.error(f"Failed to create track record in Supabase: {track_name}")
                    return False
                
        except Exception as e:
            logger.error(f"Error saving track map to Supabase: {str(e)}")
            return False


class ColorButton(QPushButton):
    """Button that displays and allows selection of a color."""
    
    colorChanged = pyqtSignal(QColor)
    
    def __init__(self, color=QColor(255, 255, 255), parent=None):
        super().__init__(parent)
        self.color = color
        self.setText("Choose Color")
        self.clicked.connect(self.choose_color)
        self.update_button_color()
    
    def choose_color(self):
        """Open color dialog to choose a new color."""
        new_color = QColorDialog.getColor(self.color, self, "Choose Color")
        if new_color.isValid():
            self.color = new_color
            self.update_button_color()
            self.colorChanged.emit(new_color)
    
    def update_button_color(self):
        """Update button appearance to show current color."""
        r, g, b, a = self.color.getRgb()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, {a});
                color: {'white' if r + g + b < 384 else 'black'};
                border: 2px solid #ccc;
                padding: 5px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border-color: #999;
            }}
        """)
    
    def get_color(self):
        """Get the current color."""
        return self.color
    
    def set_color(self, color):
        """Set the current color."""
        self.color = color
        self.update_button_color()


class TrackMapOverlaySettingsDialog(QDialog):
    """Settings dialog for track map overlay configuration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlay_manager = TrackMapOverlayManager()
        self.setWindowTitle("Track Map Overlay Settings")
        self.setModal(True)
        self.resize(600, 700)
        
        # Current settings
        self.settings = self.get_default_settings()
        
        # Track builder thread
        self.track_builder_thread = None
        
        self.setup_ui()
        self.load_settings()
        self.connect_signals()
    
    def get_default_settings(self):
        """Get default overlay settings."""
        return {
            'overlay_scale': 0.3,
            'show_corners': True,
            'show_position_dot': True,
            'track_line_width': 3,
            'corner_font_size': 12,
            'track_color': QColor(255, 255, 255, 200),
            'corner_color': QColor(255, 255, 0, 200),
            'position_color': QColor(0, 255, 0, 255)
        }
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Set dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3c3c;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
                color: #ffffff;
                border-bottom: 2px solid #4a90e2;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4a90e2;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5ba0f2;
            }
            QPushButton:pressed {
                background-color: #3a80d2;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #555555;
                background-color: #2b2b2b;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4a90e2;
                background-color: #4a90e2;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                border: 1px solid #4a90e2;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSpinBox {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                color: #ffffff;
                padding: 4px;
                border-radius: 3px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 2px;
            }
        """)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Position & Size Tab
        pos_tab = QWidget()
        tab_widget.addTab(pos_tab, "Position & Size")
        self.setup_position_tab(pos_tab)
        
        # Visual Settings Tab
        visual_tab = QWidget()
        tab_widget.addTab(visual_tab, "Visual Settings")
        self.setup_visual_tab(visual_tab)
        
        # Colors Tab
        colors_tab = QWidget()
        tab_widget.addTab(colors_tab, "Colors")
        self.setup_colors_tab(colors_tab)
        
        # Track Builder Tab - NEW!
        builder_tab = QWidget()
        tab_widget.addTab(builder_tab, "🎯 Track Builder")
        self.setup_track_builder_tab(builder_tab)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Overlay")
        self.test_button.clicked.connect(self.test_overlay)
        control_layout.addWidget(self.test_button)
        
        self.start_button = QPushButton("Start Overlay")
        self.start_button.clicked.connect(self.start_overlay)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Overlay")
        self.stop_button.clicked.connect(self.stop_overlay)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        control_layout.addStretch()
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        control_layout.addWidget(self.apply_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        control_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        control_layout.addWidget(self.cancel_button)
        
        layout.addLayout(control_layout)
        
        # Status label
        self.status_label = QLabel("Configure your track map overlay settings below.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("QLabel { color: #bbbbbb; font-style: italic; padding: 5px; }")
        layout.addWidget(self.status_label)

    def setup_track_builder_tab(self, parent):
        """Set up the track builder tab."""
        layout = QVBoxLayout(parent)
        
        # Title and description
        title_label = QLabel("🎯 Ultimate Track Builder")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        desc_label = QLabel(
            "Build perfect track maps by driving 3 clean laps. The system will automatically "
            "generate a precise centerline by averaging your laps, eliminating all drift and "
            "inconsistencies. This creates the perfect track map for the transparent overlay."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #cccccc; margin: 10px 0px; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # Instructions group
        instructions_group = QGroupBox("📋 How It Works")
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions_text = QLabel(
            "1️⃣ Make sure iRacing is running and you're on track\n"
            "2️⃣ Click 'Start Track Builder' below\n"
            "3️⃣ Drive 3 complete laps at any pace (consistency matters more than speed)\n"
            "4️⃣ Each lap will be shown in a different color (Red → Green → Blue)\n"
            "5️⃣ After 3 laps, a perfect GOLD centerline will be generated\n"
            "6️⃣ The track map will be automatically saved and ready for overlay use\n\n"
            "✨ Benefits:\n"
            "• Perfect centerline from statistical averaging\n"
            "• Eliminates driver inconsistencies and telemetry drift\n"
            "• Single clean line guaranteed for overlay\n"
            "• Works with any track in iRacing"
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("font-family: 'Segoe UI'; color: #ffffff; background: #4a4a4a; padding: 12px; border-radius: 5px; border: 1px solid #666666; font-size: 11px; line-height: 16px;")
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_group)
        
        # Progress group
        progress_group = QGroupBox("📊 Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(3)  # 3 laps required
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Laps Completed: %v / %m")
        progress_layout.addWidget(self.progress_bar)
        
        # Status text
        self.builder_status_label = QLabel("Ready to build track map. Click 'Start Track Builder' to begin.")
        self.builder_status_label.setWordWrap(True)
        self.builder_status_label.setStyleSheet("font-weight: bold; color: #4CAF50; padding: 5px;")
        progress_layout.addWidget(self.builder_status_label)
        
        layout.addWidget(progress_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_builder_button = QPushButton("🏁 Start Track Builder")
        self.start_builder_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5DBF61;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        self.start_builder_button.clicked.connect(self.start_track_builder)
        button_layout.addWidget(self.start_builder_button)
        
        self.stop_builder_button = QPushButton("⏹️ Stop Builder")
        self.stop_builder_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #f66356;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        self.stop_builder_button.clicked.connect(self.stop_track_builder)
        self.stop_builder_button.setEnabled(False)
        button_layout.addWidget(self.stop_builder_button)
        
        layout.addLayout(button_layout)
        
        # Load existing track maps group
        existing_group = QGroupBox("📁 Existing Track Maps")
        existing_layout = QVBoxLayout(existing_group)
        
        existing_desc = QLabel("Load previously generated track maps for the overlay:")
        existing_desc.setWordWrap(True)
        existing_layout.addWidget(existing_desc)
        
        load_button_layout = QHBoxLayout()
        
        self.load_track_button = QPushButton("📂 Load Track Map File")
        self.load_track_button.clicked.connect(self.load_track_map_file)
        load_button_layout.addWidget(self.load_track_button)
        
        self.refresh_tracks_button = QPushButton("🔄 Refresh Available Maps")
        self.refresh_tracks_button.clicked.connect(self.refresh_available_maps)
        load_button_layout.addWidget(self.refresh_tracks_button)
        
        existing_layout.addLayout(load_button_layout)
        
        # Show current track map info
        self.current_track_info = QLabel("No track map loaded")
        self.current_track_info.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
        existing_layout.addWidget(self.current_track_info)
        
        # Show cloud track map availability
        self.cloud_track_info = QLabel("Checking cloud track maps...")
        self.cloud_track_info.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
        existing_layout.addWidget(self.cloud_track_info)
        
        layout.addWidget(existing_group)
        
        layout.addStretch()

    def start_track_builder(self):
        """Start the track builder in a separate thread."""
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            QMessageBox.warning(self, "Already Running", "Track builder is already running!")
            return
        
        # Check if required dependencies are available
        try:
            import matplotlib
            import numpy as np
            from scipy.interpolate import interp1d
            from sklearn.cluster import DBSCAN
            from filterpy.kalman import KalmanFilter
        except ImportError as e:
            QMessageBox.critical(self, "Missing Dependencies", 
                               f"Track builder requires additional packages:\n\n"
                               f"pip install matplotlib numpy scipy scikit-learn filterpy\n\n"
                               f"Missing: {str(e)}")
            return
        
        # Start the builder thread
        self.track_builder_thread = TrackBuilderThread()
        self.track_builder_thread.status_updated.connect(self.on_builder_status_updated)
        self.track_builder_thread.progress_updated.connect(self.on_builder_progress_updated)
        self.track_builder_thread.centerline_generated.connect(self.on_centerline_generated)
        self.track_builder_thread.error_occurred.connect(self.on_builder_error)
        self.track_builder_thread.finished.connect(self.on_builder_finished)
        
        self.track_builder_thread.start()
        
        # Update UI
        self.start_builder_button.setEnabled(False)
        self.stop_builder_button.setEnabled(True)
        self.builder_status_label.setText("🔌 Starting track builder...")
        self.progress_bar.setValue(0)
        
        QMessageBox.information(self, "Track Builder Started", 
                              "🎯 Track builder is now running!\n\n"
                              "A separate window will open showing your track being built in real-time.\n"
                              "Drive 3 complete laps to generate the perfect centerline.\n\n"
                              "The window will show:\n"
                              "• Gray line: Raw telemetry data\n"
                              "• Red line: Lap 1\n" 
                              "• Green line: Lap 2\n"
                              "• Blue line: Lap 3\n"
                              "• Gold line: Perfect centerline (after 3 laps)\n\n"
                              "You can minimize this dialog and continue using TrackPro while building.")

    def stop_track_builder(self):
        """Stop the track builder."""
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.track_builder_thread.stop()
            self.track_builder_thread.wait(5000)  # Wait up to 5 seconds
            
        self.on_builder_finished()

    def on_builder_status_updated(self, status):
        """Handle status updates from the track builder."""
        self.builder_status_label.setText(status)

    def on_builder_progress_updated(self, completed_laps, required_laps):
        """Handle progress updates from the track builder."""
        self.progress_bar.setValue(completed_laps)
        self.progress_bar.setFormat(f"Laps Completed: {completed_laps} / {required_laps}")

    def on_centerline_generated(self, file_path):
        """Handle when centerline is generated."""
        QMessageBox.information(self, "Track Map Complete!", 
                              f"🎯 Perfect track map generated!\n\n"
                              f"📁 Saved to: {file_path}\n\n"
                              f"✅ The track map is now ready for use with the overlay.\n"
                              f"You can start the overlay to see your perfect centerline!")
        
        # Update the current track info
        self.refresh_current_track_info()

    def on_builder_error(self, error_message):
        """Handle errors from the track builder."""
        QMessageBox.critical(self, "Track Builder Error", error_message)
        self.builder_status_label.setText(f"❌ Error: {error_message}")

    def on_builder_finished(self):
        """Handle when the track builder finishes."""
        self.start_builder_button.setEnabled(True)
        self.stop_builder_button.setEnabled(False)
        
        if not self.builder_status_label.text().startswith("✅"):
            self.builder_status_label.setText("Track builder stopped. Ready to start again.")

    def load_track_map_file(self):
        """Load a track map file for the overlay."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Track Map", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    track_data = json.load(f)
                
                # Validate the track data
                if 'centerline_positions' not in track_data:
                    QMessageBox.warning(self, "Invalid File", "This file doesn't contain valid track map data.")
                    return
                
                # Load the track data into the overlay
                if self.overlay_manager.overlay:
                    self.overlay_manager.overlay.track_coordinates = [
                        (point[0], point[1]) for point in track_data['centerline_positions']
                    ]
                    self.overlay_manager.overlay._calculate_track_bounds()
                    self.overlay_manager.overlay.update()
                
                QMessageBox.information(self, "Track Map Loaded", 
                                      f"✅ Track map loaded successfully!\n\n"
                                      f"📊 Points: {len(track_data['centerline_positions'])}\n"
                                      f"📏 Length: {track_data.get('length_meters', 'Unknown')}m\n"
                                      f"🏁 Method: {track_data.get('method', 'Unknown')}")
                
                self.current_track_info.setText(f"Loaded: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load track map: {str(e)}")

    def refresh_available_maps(self):
        """Refresh the list of available track maps."""
        self.refresh_current_track_info()
        QMessageBox.information(self, "Refreshed", "Available track maps refreshed.")

    def refresh_current_track_info(self):
        """Refresh the current track map information."""
        # Check for the default centerline file
        if os.path.exists('centerline_track_map.json'):
            try:
                with open('centerline_track_map.json', 'r') as f:
                    track_data = json.load(f)
                
                points = len(track_data.get('centerline_positions', []))
                length = track_data.get('length_meters', 'Unknown')
                method = track_data.get('method', 'Unknown')
                
                self.current_track_info.setText(
                    f"📍 centerline_track_map.json - {points} points, {length}m ({method})"
                )
            except:
                self.current_track_info.setText("❌ Error reading centerline_track_map.json")
        else:
            self.current_track_info.setText("No local track map found. Build one using the Track Builder above!")
        
        # Check for cloud track maps
        self.check_cloud_track_maps()

    def check_cloud_track_maps(self):
        """Check for available track maps in the cloud."""
        try:
            # Try to get current track from iRacing
            from ..track_map_overlay import TrackMapOverlayManager
            manager = TrackMapOverlayManager()
            current_track_info = manager._get_current_iracing_track()
            
            if current_track_info:
                track_name, track_config = current_track_info
                
                # Check Supabase for existing track maps
                from ...database.supabase_client import get_supabase_client
                supabase = get_supabase_client()
                
                if supabase:
                    # Query for track data
                    track_query = supabase.table('tracks').select('name, config, track_map, analysis_metadata, last_analysis_date').eq('name', track_name)
                    if track_config and track_config != track_name:
                        track_query = track_query.eq('config', track_config)
                    
                    result = track_query.execute()
                    
                    if result.data and result.data[0].get('track_map'):
                        track_data = result.data[0]
                        points = len(track_data['track_map']) if track_data['track_map'] else 0
                        metadata = track_data.get('analysis_metadata', {})
                        method = metadata.get('generation_method', 'unknown')
                        last_updated = track_data.get('last_analysis_date', 'unknown')
                        
                        full_name = track_name
                        if track_config and track_config != track_name:
                            full_name += f" - {track_config}"
                        
                        self.cloud_track_info.setText(
                            f"☁️ Cloud: {full_name} - {points} points ({method}) - Updated: {last_updated[:10] if last_updated != 'unknown' else 'unknown'}"
                        )
                        self.cloud_track_info.setStyleSheet("color: #4CAF50; font-style: italic; padding: 5px;")
                    else:
                        full_name = track_name
                        if track_config and track_config != track_name:
                            full_name += f" - {track_config}"
                        self.cloud_track_info.setText(f"☁️ No cloud track map for {full_name}. Build one to share with community!")
                        self.cloud_track_info.setStyleSheet("color: #ff9800; font-style: italic; padding: 5px;")
                else:
                    self.cloud_track_info.setText("☁️ Cloud connection unavailable")
                    self.cloud_track_info.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
            else:
                self.cloud_track_info.setText("☁️ iRacing not connected - cannot check current track")
                self.cloud_track_info.setStyleSheet("color: #888; font-style: italic; padding: 5px;")
                
        except Exception as e:
            self.cloud_track_info.setText(f"☁️ Error checking cloud maps: {str(e)}")
            self.cloud_track_info.setStyleSheet("color: #f44336; font-style: italic; padding: 5px;")
    
    def setup_position_tab(self, parent):
        """Set up the position and size settings tab."""
        layout = QVBoxLayout(parent)
        
        # Scale group
        scale_group = QGroupBox("Overlay Scale")
        scale_layout = QGridLayout(scale_group)
        
        scale_layout.addWidget(QLabel("Scale:"), 0, 0)
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setMinimum(10)
        self.scale_slider.setMaximum(100)
        self.scale_slider.setValue(30)
        scale_layout.addWidget(self.scale_slider, 0, 1)
        
        self.scale_value_label = QLabel("30%")
        scale_layout.addWidget(self.scale_value_label, 0, 2)
        
        layout.addWidget(scale_group)
        
        # Dragging instructions group
        drag_group = QGroupBox("🖱️ Draggable Positioning")
        drag_layout = QVBoxLayout(drag_group)
        
        instructions = QLabel("""<b>How to position the overlay:</b><br><br>

<b>🔒 Locked Mode (Default):</b><br>
• Overlay is click-through - you can interact with games normally<br>
• Press <b>L</b> key or <b>scroll wheel</b> over overlay to unlock<br><br>

<b>🔓 Unlocked Mode:</b><br>
• Click and drag the overlay to reposition it<br>
• Scroll wheel or press <b>L</b> key to lock back in place<br>
• Overlay shows lock/unlock icon when changing modes<br><br>

<i>Note: Position coordinates have been replaced with intuitive dragging!</i>""")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("""
            QLabel {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 15px;
                font-size: 12px;
                color: #ffffff;
                line-height: 18px;
            }
        """)
        drag_layout.addWidget(instructions)
        
        layout.addWidget(drag_group)
        
        layout.addStretch()
    
    def setup_visual_tab(self, parent):
        """Set up the visual settings tab."""
        layout = QVBoxLayout(parent)
        
        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QGridLayout(display_group)
        
        self.show_corners_checkbox = QCheckBox("Show Corner Numbers")
        self.show_corners_checkbox.setChecked(True)
        display_layout.addWidget(self.show_corners_checkbox, 0, 0)
        
        self.show_position_checkbox = QCheckBox("Show Position Dot")
        self.show_position_checkbox.setChecked(True)
        display_layout.addWidget(self.show_position_checkbox, 0, 1)
        
        layout.addWidget(display_group)
        
        # Line settings
        line_group = QGroupBox("Line Settings")
        line_layout = QGridLayout(line_group)
        
        line_layout.addWidget(QLabel("Track Line Width:"), 0, 0)
        self.line_width_spinbox = QSpinBox()
        self.line_width_spinbox.setMinimum(1)
        self.line_width_spinbox.setMaximum(10)
        self.line_width_spinbox.setValue(3)
        line_layout.addWidget(self.line_width_spinbox, 0, 1)
        
        line_layout.addWidget(QLabel("Corner Font Size:"), 1, 0)
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setMinimum(8)
        self.font_size_spinbox.setMaximum(24)
        self.font_size_spinbox.setValue(12)
        line_layout.addWidget(self.font_size_spinbox, 1, 1)
        
        layout.addWidget(line_group)
        
        layout.addStretch()

    def setup_colors_tab(self, parent):
        """Set up the colors settings tab."""
        layout = QVBoxLayout(parent)
        
        # Color settings
        color_group = QGroupBox("Colors")
        color_layout = QGridLayout(color_group)
        
        color_layout.addWidget(QLabel("Track Color:"), 0, 0)
        self.track_color_button = ColorButton(QColor(255, 255, 255, 200))
        color_layout.addWidget(self.track_color_button, 0, 1)
        
        color_layout.addWidget(QLabel("Corner Color:"), 1, 0)
        self.corner_color_button = ColorButton(QColor(255, 255, 0, 200))
        color_layout.addWidget(self.corner_color_button, 1, 1)
        
        color_layout.addWidget(QLabel("Position Color:"), 2, 0)
        self.position_color_button = ColorButton(QColor(0, 255, 0, 255))
        color_layout.addWidget(self.position_color_button, 2, 1)
        
        layout.addWidget(color_group)
        
        layout.addStretch()

    def connect_signals(self):
        """Connect UI signals to handlers."""
        # Scale slider updates
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        
        # Settings changes
        self.scale_slider.valueChanged.connect(self.update_settings_from_ui)
        self.show_corners_checkbox.toggled.connect(self.update_settings_from_ui)
        self.show_position_checkbox.toggled.connect(self.update_settings_from_ui)
        self.line_width_spinbox.valueChanged.connect(self.update_settings_from_ui)
        self.font_size_spinbox.valueChanged.connect(self.update_settings_from_ui)
        
        # Color changes
        self.track_color_button.colorChanged.connect(self.update_settings_from_ui)
        self.corner_color_button.colorChanged.connect(self.update_settings_from_ui)
        self.position_color_button.colorChanged.connect(self.update_settings_from_ui)

    def on_scale_changed(self, value):
        """Handle scale slider changes."""
        self.scale_value_label.setText(f"{value}%")
        self.update_settings_from_ui()

    def update_settings_from_ui(self):
        """Update settings from UI controls."""
        self.settings = {
            'overlay_scale': self.scale_slider.value() / 100.0,
            'show_corners': self.show_corners_checkbox.isChecked(),
            'show_position_dot': self.show_position_checkbox.isChecked(),
            'track_line_width': self.line_width_spinbox.value(),
            'corner_font_size': self.font_size_spinbox.value(),
            'track_color': self.track_color_button.get_color(),
            'corner_color': self.corner_color_button.get_color(),
            'position_color': self.position_color_button.get_color()
        }

    def load_settings(self):
        """Load settings into UI controls."""
        # This would typically load from saved settings
        # For now, use defaults
        settings = self.get_default_settings()
        
        self.scale_slider.setValue(int(settings['overlay_scale'] * 100))
        self.show_corners_checkbox.setChecked(settings['show_corners'])
        self.show_position_checkbox.setChecked(settings['show_position_dot'])
        self.line_width_spinbox.setValue(settings['track_line_width'])
        self.font_size_spinbox.setValue(settings['corner_font_size'])
        self.track_color_button.set_color(settings['track_color'])
        self.corner_color_button.set_color(settings['corner_color'])
        self.position_color_button.set_color(settings['position_color'])
        
        self.update_settings_from_ui()
        
        # Refresh track info on load
        self.refresh_current_track_info()

    def apply_settings(self):
        """Apply current settings to the overlay."""
        self.overlay_manager.update_settings(self.settings)
        self.status_label.setText("Settings applied to overlay.")

    def test_overlay(self):
        """Test the overlay with current settings."""
        self.apply_settings()
        
        if not self.overlay_manager.is_active:
            success = self.overlay_manager.start_overlay()
            if success:
                self.status_label.setText("Test overlay started. Press 'Q' on overlay to close, or use Stop button.")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
            else:
                self.status_label.setText("Failed to start test overlay.")
        else:
            self.status_label.setText("Overlay is already running.")

    def start_overlay(self):
        """Start the overlay."""
        if not self.overlay_manager.is_active:
            self.apply_settings()
            
            # Try to load the centerline track map if it exists
            if os.path.exists('centerline_track_map.json'):
                try:
                    with open('centerline_track_map.json', 'r') as f:
                        track_data = json.load(f)
                    
                    # Pre-load the track data into the overlay
                    success = self.overlay_manager.start_overlay()
                    if success and self.overlay_manager.overlay:
                        self.overlay_manager.overlay.track_coordinates = [
                            (point[0], point[1]) for point in track_data['centerline_positions']
                        ]
                        self.overlay_manager.overlay._calculate_track_bounds()
                        self.overlay_manager.overlay.update()
                        
                        self.status_label.setText("Track map overlay started with centerline data!")
                        self.start_button.setEnabled(False)
                        self.stop_button.setEnabled(True)
                        
                        QMessageBox.information(
                            self, "Overlay Started",
                            "🗺️ Track map overlay is now active!\n\n"
                            "✨ Using high-quality centerline track map\n"
                            "🎯 Green dot shows your current position on track\n"
                            "☁️ Track map automatically loaded from cloud or local file\n"
                            "🖱️ Click-through - won't interfere with games\n\n"
                            "Controls:\n"
                            "• Press 'Q' to close overlay\n"
                            "• Press 'C' to toggle corner numbers\n"
                            "• Press 'R' to reload track data\n\n"
                            "Perfect for:\n"
                            "• Real-time position awareness during races\n"
                            "• Learning track layouts\n"
                            "• Monitoring your racing line\n\n"
                            "💡 If no track map exists, use the Track Builder tab to create one!"
                        )
                    else:
                        self.status_label.setText("Failed to start overlay. Check if iRacing is running.")
                        
                except Exception as e:
                    logger.error(f"Error loading centerline data: {e}")
                    # Fall back to normal overlay start
                    success = self.overlay_manager.start_overlay()
                    if success:
                        self.status_label.setText("Track map overlay started (no centerline data found).")
                        self.start_button.setEnabled(False)
                        self.stop_button.setEnabled(True)
                    else:
                        self.status_label.setText("Failed to start overlay. Check if iRacing is running.")
            else:
                # No centerline data available
                success = self.overlay_manager.start_overlay()
                if success:
                    self.status_label.setText("Track map overlay started (no track data - use Track Builder to create one!).")
                    self.start_button.setEnabled(False)
                    self.stop_button.setEnabled(True)
                    
                    QMessageBox.information(
                        self, "Overlay Started",
                        "🗺️ Track map overlay is now active!\n\n"
                        "ℹ️ No track map data found.\n"
                        "🎯 Use the 'Track Builder' tab to create a perfect track map\n"
                        "   by driving 3 laps, then restart the overlay.\n\n"
                        "Current overlay shows:\n"
                        "• Green dot for your current position\n"
                        "• Track outline (if available from database)\n\n"
                        "For the best experience, build a track map first!"
                    )
                else:
                    self.status_label.setText("Failed to start overlay. Check if iRacing is running.")
        else:
            self.status_label.setText("Overlay is already running.")

    def stop_overlay(self):
        """Stop the overlay."""
        if self.overlay_manager.is_active:
            self.overlay_manager.stop_overlay()
            self.status_label.setText("Track map overlay stopped.")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        else:
            self.status_label.setText("Overlay is not running.")

    def accept(self):
        """Handle OK button click."""
        self.apply_settings()
        if self.overlay_manager.is_active:
            reply = QMessageBox.question(
                self, "Overlay Running",
                "Track map overlay is currently running. Keep it running?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.stop_overlay()
        
        # Stop track builder if running
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.stop_track_builder()
        
        super().accept()

    def reject(self):
        """Handle Cancel button click."""
        if self.overlay_manager.is_active:
            reply = QMessageBox.question(
                self, "Overlay Running",
                "Track map overlay is currently running. Stop it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_overlay()
        
        # Stop track builder if running
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.stop_track_builder()
        
        super().reject()

    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop track builder if running
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.stop_track_builder()
        
        # Don't stop overlay when dialog closes - let user keep it running
        event.accept()
