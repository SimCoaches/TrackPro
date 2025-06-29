"""
Track Map Overlay Settings Dialog
Configuration UI for the transparent track map overlay
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QGroupBox, QSlider, QCheckBox, QSpinBox,
                           QColorDialog, QLineEdit, QTabWidget, QWidget,
                           QMessageBox, QFrame, QGridLayout, QProgressBar,
                           QTextEdit, QFileDialog, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMetaObject
from PyQt6.QtGui import QColor, QPalette, QFont

from ..track_map_overlay import TrackMapOverlayManager
from .track_visualization_window import TrackVisualizationWindow
import os
import json
import logging

logger = logging.getLogger(__name__)


class TrackBuilderThread(QThread):
    """Thread for running the ultimate track builder."""
    
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)  # completed_laps, required_laps
    track_update = pyqtSignal(object)  # ADDED: Forward track_builder object from manager
    centerline_generated = pyqtSignal(str)  # file_path
    error_occurred = pyqtSignal(str)
    track_manager_ready = pyqtSignal(object)  # NEW: Emitted when manager is ready

    def __init__(self, simple_iracing_api=None):
        super().__init__()
        self.should_stop = False
        self.track_builder_manager = None
        self.simple_iracing_api = simple_iracing_api  # Store global connection
    
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
            
            from ..integrated_track_builder import IntegratedTrackBuilderWorker, IntegratedTrackBuilderManager
            
            self.status_updated.emit("🔌 Starting integrated track builder...")
            
            # Create and configure the integrated track builder
            print("🐛 DEBUG: TrackBuilderThread creating IntegratedTrackBuilderManager...")
            print(f"🔗 DEBUG: TrackBuilderThread has global iRacing connection: {self.simple_iracing_api is not None}")
            
            self.track_builder_manager = IntegratedTrackBuilderManager(self.simple_iracing_api)
            print("🐛 DEBUG: IntegratedTrackBuilderManager created successfully")
            
            # Connect internal signals - FIXED: Proper signal forwarding
            print("🐛 DEBUG: Connecting internal signals...")
            self.track_builder_manager.status_update.connect(self.status_updated)
            
            # FIXED: Forward progress_update properly with lap count extraction
            self.track_builder_manager.progress_update.connect(self._forward_progress_update)
            
            # ADDED: Forward track_update signal
            self.track_builder_manager.track_update.connect(self.track_update)
            
            self.track_builder_manager.completion_ready.connect(self._on_internal_completion)
            self.track_builder_manager.error_occurred.connect(self.error_occurred)
            print("🐛 DEBUG: Internal signals connected")
            
            # Emit signal that manager is ready for external connections
            print("🐛 DEBUG: Emitting track_manager_ready signal...")
            self.track_manager_ready.emit(self.track_builder_manager)
            
            # Start the track building process
            print("🐛 DEBUG: Starting track building process...")
            self.track_builder_manager.start_building()
            print("🐛 DEBUG: Track builder process started successfully")
            
            self.status_updated.emit("✅ Track builder started! Drive 3 laps to generate centerline...")
            
            # Keep the thread alive while the worker is running
            while not self.should_stop and self.track_builder_manager.is_running:
                self.msleep(100)  # Sleep for 100ms
                
        except Exception as e:
            import traceback
            error_msg = f"Failed to start track builder: {str(e)}\n{traceback.format_exc()}"
            print(f"❌ TrackBuilderThread error: {error_msg}")
            self.error_occurred.emit(error_msg)
    
    def _forward_progress_update(self, status_message, progress_value):
        """Forward progress_update from manager to thread's progress_updated signal."""
        try:
            print(f"🔄 DEBUG: Forwarding progress - '{status_message}', value: {progress_value}")
            
            # Extract lap count from progress_value (it should be the completed laps)
            completed_laps = progress_value if isinstance(progress_value, int) else 0
            required_laps = 3
            
            # Emit the old-style progress_updated signal that UI expects
            self.progress_updated.emit(completed_laps, required_laps)
            
            print(f"✅ DEBUG: Forwarded progress_updated({completed_laps}, {required_laps})")
            
        except Exception as e:
            print(f"❌ DEBUG: Error forwarding progress: {e}")

    def _on_completion_ready(self, centerline, corners):
        """Handle completion of track building."""
        try:
            import numpy as np
            import time
            import json
            
            # Calculate track length
            track_length = 0
            if len(centerline) > 1:
                for i in range(1, len(centerline)):
                    dx = centerline[i][0] - centerline[i-1][0]
                    dy = centerline[i][1] - centerline[i-1][1]
                    track_length += np.sqrt(dx*dx + dy*dy)
            
            # Prepare track data for saving
            track_data = {
                'centerline_positions': [[point[0], point[1]] for point in centerline],
                'length_meters': track_length,
                'points_count': len(centerline),
                'corners_count': len(corners),
                'laps_used': 3,
                'method': 'integrated_track_builder_3_lap_averaging',
                'generation_timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save locally first with proper encoding
            file_path = 'centerline_track_map.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(track_data, f, indent=2, ensure_ascii=False)
            
            # Emit completion signals
            self.centerline_generated.emit(file_path)
            self.status_updated.emit(f"✅ Track map complete! ({len(centerline)} points, {len(corners)} corners, {track_length:.0f}m)")
            
        except Exception as e:
            self.error_occurred.emit(f"Error saving track map: {str(e)}")
    
    def stop(self):
        """Stop the track builder thread."""
        print("🐛 DEBUG: Stopping TrackBuilderThread...")
        self.should_stop = True
        if self.track_builder_manager:
            self.track_builder_manager.stop_building()
        self.wait()  # Wait for thread to finish

    def _on_internal_completion(self, centerline, corners):
        """Handle internal completion and emit signals for both thread and UI."""
        print(f"🐛 DEBUG: Internal completion - {len(centerline)} points, {len(corners)} corners")
        
        # Emit the centerline_generated signal for the thread (expected by existing code)
        self.centerline_generated.emit("centerline_track_map.json")  # File path as expected
        
        # Store completion data for the UI (will be handled by the manager ready connection)
        self.completion_data = (centerline, corners)

    # Note: Supabase saving is now handled automatically by the integrated track builder


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
        
        # Track visualization window
        self.visualization_window = None
        
        self.setup_ui()
        self.load_settings()
        self.connect_signals()
    
    def _load_json_file_safely(self, file_path):
        """Safely load JSON file with null byte cleaning."""
        try:
            # Read file with null byte cleaning
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Remove null bytes that can cause SyntaxError
            cleaned_content = file_content.replace('\x00', '')
            
            # Parse the cleaned JSON
            return json.loads(cleaned_content)
        except Exception as e:
            logger.error(f"Error loading JSON file {file_path}: {e}")
            # Try to recover by backing up corrupted file
            self._backup_corrupted_file(file_path)
            raise
    
    def _backup_corrupted_file(self, file_path):
        """Backup a corrupted JSON file for recovery."""
        try:
            import shutil
            import time
            backup_path = f"{file_path}.corrupted_{int(time.time())}"
            shutil.move(file_path, backup_path)
            logger.info(f"Moved corrupted file to: {backup_path}")
            
            QMessageBox.warning(
                self, "Corrupted File Detected",
                f"🛠️ **File Corruption Fixed**\n\n"
                f"The file '{file_path}' contained null bytes (data corruption) and has been safely moved to:\n"
                f"{backup_path}\n\n"
                f"**What this means:**\n"
                f"• Your track map file got corrupted (possibly during a previous crash)\n"
                f"• TrackPro automatically detected and fixed this issue\n"
                f"• You can rebuild your track map using the Track Builder\n\n"
                f"**Next steps:**\n"
                f"• Use 'Track Builder' tab to create a new track map\n"
                f"• Drive 3 clean laps to generate a perfect centerline"
            )
        except Exception as backup_error:
            logger.error(f"Failed to backup corrupted file: {backup_error}")
    
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
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
            "2️⃣ Click 'Show Live View' to see the track being built in real-time\n"
            "3️⃣ Click 'Start Track Builder' to begin\n"
            "4️⃣ Drive 3 complete laps at any pace (consistency matters more than speed)\n"
            "5️⃣ Watch the live view as each lap is traced in different colors\n"
            "6️⃣ After 3 laps, a perfect GOLD centerline will be generated\n"
            "7️⃣ The track map will be automatically saved and ready for overlay use\n\n"
            "✨ Features:\n"
            "• Live visualization window shows track building progress\n"
            "• Perfect centerline from statistical averaging\n"
            "• Eliminates driver inconsistencies and telemetry drift\n"
            "• Single clean line guaranteed for overlay\n"
            "• Works with any track in iRacing"
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("font-family: 'Segoe UI'; color: #ffffff; background: #4a4a4a; padding: 12px; border-radius: 5px; border: 1px solid #666666; font-size: 11px; line-height: 16px;")
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_group)
        
        # Status label and progress bar
        status_layout = QHBoxLayout()
        self.builder_status_label = QLabel("Ready to build track map")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.builder_status_label)
        status_layout.addWidget(self.progress_bar)
        layout.addLayout(status_layout)
        
        # ADDED: Track map availability status
        self.track_availability_label = QLabel("🔍 Checking for existing track maps...")
        self.track_availability_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(self.track_availability_label)
        
        # Check for existing track maps on startup
        QTimer.singleShot(1000, self.check_track_availability_status)

        # Log output

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
        
        # Add visualization button
        self.show_viz_button = QPushButton("📊 Show Live View")
        self.show_viz_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #FFB74D;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        self.show_viz_button.clicked.connect(self.show_track_visualization)
        button_layout.addWidget(self.show_viz_button)
        
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
        """Start the ultimate track builder."""
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            QMessageBox.warning(self, "Track Builder Running", 
                               "Track builder is already running. Please wait for it to complete or stop it first.")
            return

        # ADDED: Check for existing track map before starting
        existing_track_data = self.check_existing_track_map()
        if existing_track_data:
            self.handle_existing_track_map(existing_track_data)
            return

        # Reset progress
        self.progress_bar.setValue(0)
        self.builder_status_label.setText("Starting track builder...")
        
        # Get global iRacing connection from parent if available
        simple_iracing_api = None
        try:
            # Access the global iRacing connection through the main window
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                # Get the main window
                main_window = None
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'iracing_api') and widget.iracing_api:
                        main_window = widget
                        simple_iracing_api = widget.iracing_api
                        print(f"🔗 DEBUG: Found global iRacing connection from main window: {simple_iracing_api is not None}")
                        break
                
                if not simple_iracing_api:
                    print("⚠️ DEBUG: No global iRacing connection found, worker will create its own")
            else:
                print("⚠️ DEBUG: No QApplication instance found")
        except Exception as e:
            print(f"⚠️ DEBUG: Error accessing global iRacing connection: {e}")
        
        # Start the builder thread with the global connection (or None for fallback)
        self.track_builder_thread = TrackBuilderThread(simple_iracing_api)
        print("🐛 DEBUG: Connecting thread signals...")
        
        # Connect standard thread signals - SIMPLIFIED: One clean signal path
        self.track_builder_thread.status_updated.connect(self.on_builder_status_updated)
        self.track_builder_thread.progress_updated.connect(self.on_builder_progress_updated)
        self.track_builder_thread.track_update.connect(self._on_track_update)  # ADDED: Direct track updates
        self.track_builder_thread.centerline_generated.connect(self.on_centerline_generated)
        self.track_builder_thread.error_occurred.connect(self.on_builder_error)
        self.track_builder_thread.finished.connect(self.on_builder_finished)
        
        print("🐛 DEBUG: All thread signals connected directly - no manager bypass needed")
        
        # DIRECT CONNECTION: Connect straight to the worker when it's ready
        self.track_builder_thread.track_manager_ready.connect(self._connect_directly_to_worker)
        
        # Connect visualization window if it exists
        self._connect_visualization_to_builder()
        
        print("🐛 DEBUG: Essential signals connected, starting thread...")
        
        self.track_builder_thread.start()
        
        # Update UI
        self.start_builder_button.setEnabled(False)
        self.stop_builder_button.setEnabled(True)
        self.builder_status_label.setText("🔌 Starting track builder...")
        self.progress_bar.setValue(0)
        print("🐛 DEBUG: UI updated, track builder starting...")
        
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

    def _connect_directly_to_worker(self, manager):
        """Connect directly to the worker, bypassing all complex forwarding."""
        print(f"🔗 DEBUG: Connecting DIRECTLY to worker, bypassing all signal forwarding...")
        try:
            # Get the actual worker from the manager
            worker = manager.worker
            if worker:
                # Connect DIRECTLY to worker signals - bypass all forwarding
                worker.track_update.connect(self._on_track_update_direct, Qt.QueuedConnection)
                worker.progress_update.connect(self._on_progress_update_direct, Qt.QueuedConnection)
                worker.completion_ready.connect(self._on_track_completion, Qt.QueuedConnection)
                
                print(f"✅ DEBUG: Connected DIRECTLY to worker - no more signal forwarding!")
            else:
                print(f"❌ DEBUG: No worker found in manager")
                
        except Exception as e:
            print(f"❌ DEBUG: Error connecting directly to worker: {e}")
            import traceback
            traceback.print_exc()

    def _on_track_update_direct(self, track_builder):
        """Direct track update handler - bypasses all forwarding."""
        try:
            completed_laps = len(track_builder.laps)
            current_points = len(track_builder.current_lap)
            print(f"🔥 DEBUG: DIRECT track update received - {completed_laps} laps, {current_points} points - WORKING!")
            
            # Update UI directly
            self.update_progress_ui(completed_laps, current_points)
            
        except Exception as e:
            print(f"❌ DEBUG: Error in direct track update: {e}")
            import traceback
            traceback.print_exc()

    def _on_progress_update_direct(self, status_message, progress_value):
        """Direct progress update handler - bypasses all forwarding."""
        try:
            print(f"🔥 DEBUG: DIRECT progress update received - '{status_message}', value: {progress_value} - WORKING!")
            
            # Convert to the format expected by the UI
            completed_laps = progress_value if isinstance(progress_value, int) else 0
            
            # Update progress bar directly 
            self.progress_bar.setValue(completed_laps)
            self.builder_status_label.setText(status_message)
            
            # Force UI refresh
            self.progress_bar.repaint()
            self.builder_status_label.repaint()
            QApplication.processEvents()
            
        except Exception as e:
            print(f"❌ DEBUG: Error in direct progress update: {e}")

    def _on_track_update(self, track_builder):
        """Handle track updates and update the UI progress bar."""
        try:
            completed_laps = len(track_builder.completed_laps)
            current_points = len(track_builder.current_lap_points)
            required_laps = 3
            
            print(f"🐛 DEBUG: _on_track_update called - {completed_laps}/{required_laps} laps, {current_points} current points")
            
            # Call the UI update method directly (should work with QueuedConnection)
            self.update_progress_ui(completed_laps, current_points)
            
        except Exception as e:
            print(f"❌ DEBUG: Error in _on_track_update: {e}")
            import traceback
            traceback.print_exc()

    def update_progress_ui(self, completed_laps, current_points):
        """Update the UI progress bar and status - called from main thread."""
        try:
            required_laps = 3
            
            # Update progress bar
            self.progress_bar.setValue(completed_laps)
            self.progress_bar.setFormat(f"Laps Completed: {completed_laps} / {required_laps}")
            
            # Update status with real-time info
            if completed_laps < required_laps:
                status = f"🚗 Driving lap {completed_laps + 1}/3 - {current_points} points collected"
            else:
                status = "🎯 Processing 3 laps into track map..."
            
            self.builder_status_label.setText(status)
            
            # Force repaint
            self.progress_bar.repaint()
            self.builder_status_label.repaint()
            QApplication.processEvents()
            
            print(f"✅ DEBUG: UI updated successfully - {completed_laps}/{required_laps} laps, {current_points} points")
            
        except Exception as e:
            print(f"❌ DEBUG: Error in update_progress_ui: {e}")

    def _on_track_completion(self, centerline, corners):
        """Handle track completion and show visual proof."""
        try:
            print(f"🐛 DEBUG: Track completion received - {len(centerline)} centerline points, {len(corners)} corners")
            
            # Update UI to show completion
            self.progress_bar.setValue(3)
            self.progress_bar.setFormat("✅ Track Map Created!")
            self.builder_status_label.setText(f"✅ Track map created: {len(centerline)} points, {len(corners)} corners")
            
            # Show visual proof with track details
            track_info = f"""
✅ TRACK MAP SUCCESSFULLY CREATED!

📍 Track: The Bullring
📊 Centerline Points: {len(centerline)}
🎯 Corners Detected: {len(corners)}
📏 Track Length: {self._calculate_track_length(centerline):.0f} meters

The track map has been saved and is ready for use in:
• Race Coach analysis
• Track Map Overlay
• Corner detection system
            """
            
            # Show success message box with track details
            QMessageBox.information(self, "Track Map Created!", track_info.strip())
            
            # Re-enable the build button for future use
            if hasattr(self, 'build_button'):
                self.build_button.setText("🏗️ Build Track Map")
                self.build_button.setEnabled(True)
                
        except Exception as e:
            print(f"❌ DEBUG: Error in _on_track_completion: {e}")

    def _calculate_track_length(self, centerline):
        """Calculate approximate track length from centerline points."""
        try:
            import math
            total_length = 0
            for i in range(1, len(centerline)):
                dx = centerline[i][0] - centerline[i-1][0]
                dy = centerline[i][1] - centerline[i-1][1]
                total_length += math.sqrt(dx*dx + dy*dy)
            return total_length
        except:
            return 0

    def stop_track_builder(self):
        """Stop the track builder."""
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.track_builder_thread.stop()
            self.track_builder_thread.wait(5000)  # Wait up to 5 seconds
            
        self.on_builder_finished()
    
    def show_track_visualization(self):
        """Show the live track building visualization window."""
        if self.visualization_window is None:
            self.visualization_window = TrackVisualizationWindow(self)
        
        # Always try to connect to any running track builder
        self._connect_visualization_to_builder()
        
        self.visualization_window.show()
        self.visualization_window.raise_()
        self.visualization_window.activateWindow()
        
        QMessageBox.information(self, "Live Track View", 
                              "🎯 Live track visualization window opened!\n\n"
                              "This window will show your track being built in real-time:\n"
                              "• Gray dots: All collected telemetry points\n"
                              "• Red line: Current lap being driven\n"
                              "• Blue/Green/Purple: Completed laps\n"
                              "• Green marker: Start/finish line\n"
                              "• Yellow dashed line: Generated centerline\n\n"
                              "If you already have track builder running, it should start updating immediately!")
    
    def _connect_visualization_to_builder(self):
        """Connect visualization window to any running track builder."""
        if not self.visualization_window:
            return
            
        # Try to connect to thread-level signals
        if self.track_builder_thread and hasattr(self.track_builder_thread, 'track_update'):
            try:
                # Disconnect any existing connections to avoid duplicates
                self.track_builder_thread.track_update.disconnect(self.visualization_window.update_track_data)
            except:
                pass  # No existing connection
            
            # Connect to thread signal
            self.track_builder_thread.track_update.connect(
                self.visualization_window.update_track_data, Qt.QueuedConnection
            )
            print("🔗 Connected visualization to track builder thread signals")
        
        # Also try to connect to manager signals if available
        if (self.track_builder_thread and 
            hasattr(self.track_builder_thread, 'track_builder_manager') and 
            self.track_builder_thread.track_builder_manager):
            
            manager = self.track_builder_thread.track_builder_manager
            if hasattr(manager, 'track_update'):
                try:
                    # Disconnect any existing connections
                    manager.track_update.disconnect(self.visualization_window.update_track_data)
                except:
                    pass
                
                # Connect to manager signal
                manager.track_update.connect(
                    self.visualization_window.update_track_data, Qt.QueuedConnection
                )
                print("🔗 Connected visualization to track builder manager signals")
            
            # Connect to worker signals if available
            if hasattr(manager, 'worker') and manager.worker:
                worker = manager.worker
                if hasattr(worker, 'track_update'):
                    try:
                        # Disconnect any existing connections
                        worker.track_update.disconnect(self.visualization_window.update_track_data)
                    except:
                        pass
                    
                    # Connect to worker signal
                    worker.track_update.connect(
                        self.visualization_window.update_track_data, Qt.QueuedConnection
                    )
                    print("🔗 Connected visualization to track builder worker signals")

    def on_builder_status_updated(self, status):
        """Handle status updates from the track builder."""
        print(f"🐛 DEBUG: on_builder_status_updated called with: {status}")
        self.builder_status_label.setText(status)

    def on_builder_progress_updated(self, completed_laps, required_laps):
        """Handle progress updates from the track builder thread."""
        print(f"🎯 DEBUG: on_builder_progress_updated called - {completed_laps}/{required_laps} laps")
        
        self.progress_bar.setValue(completed_laps)
        self.progress_bar.setMaximum(required_laps)
        
        # Force UI refresh
        self.progress_bar.repaint()
        QApplication.processEvents()
        
        print(f"✅ DEBUG: Progress bar updated to {completed_laps}/{required_laps}")

    def on_centerline_generated(self, file_path):
        """Handle when centerline is generated."""
        print(f"🐛 DEBUG: on_centerline_generated called with: {file_path}")
        QMessageBox.information(self, "Track Map Complete!", 
                              f"🎯 Perfect track map generated!\n\n"
                              f"📁 Saved to: {file_path}\n\n"
                              f"✅ The track map is now ready for use with the overlay.\n"
                              f"You can start the overlay to see your perfect centerline!")
        
        # Update the current track info
        self.refresh_current_track_info()

    def on_builder_error(self, error_message):
        """Handle errors from the track builder."""
        print(f"🐛 DEBUG: on_builder_error called with: {error_message}")
        QMessageBox.critical(self, "Track Builder Error", error_message)
        self.builder_status_label.setText(f"❌ Error: {error_message}")

    def on_builder_finished(self):
        """Handle when the track builder finishes."""
        print("🐛 DEBUG: on_builder_finished called")
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
                # Load track data safely with null byte cleaning
                track_data = self._load_json_file_safely(file_path)
                
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
                # Load track data safely with null byte cleaning
                track_data = self._load_json_file_safely('centerline_track_map.json')
                
                points = len(track_data.get('centerline_positions', []))
                length = track_data.get('length_meters', 'Unknown')
                method = track_data.get('method', 'Unknown')
                
                self.current_track_info.setText(
                    f"📍 centerline_track_map.json - {points} points, {length}m ({method})"
                )
            except Exception as e:
                self.current_track_info.setText(f"❌ Error reading centerline_track_map.json: {str(e)}")
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
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
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
            # Get current track info to pass to overlay manager
            current_track_info = self.get_current_track_info()
            if current_track_info:
                track_name, track_config = current_track_info
                logger.info(f"🔍 Starting test overlay with track: {track_name} ({track_config})")
                success = self.overlay_manager.start_overlay(track_name, track_config)
            else:
                logger.warning("🔍 No current track info available, starting overlay without track data")
                success = self.overlay_manager.start_overlay()
                
            if success:
                self.status_label.setText("✅ Test overlay active! Press 'Q' on overlay to close, or use buttons below.")
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # Mark that this is a test overlay so dialog doesn't ask about stopping it
                self._is_test_overlay = True
                
                QMessageBox.information(
                    self, "Test Overlay Active",
                    "🗺️ Test overlay is now running!\n\n"
                    "✅ Your new track map is loaded\n"
                    "🎯 Green dot shows your position\n"
                    "🔄 The overlay will stay active when you close this dialog\n\n"
                    "To stop the overlay:\n"
                    "• Click 'Stop Overlay' button below, OR\n"
                    "• Press 'Q' key while overlay is focused\n\n"
                    "You can now close this dialog and test the overlay!"
                )
            else:
                self.status_label.setText("Failed to start test overlay.")
        else:
            self.status_label.setText("Overlay is already running.")

    def start_overlay(self):
        """Start the overlay."""
        # Clear test overlay flag when using regular start
        self._is_test_overlay = False
        
        if not self.overlay_manager.is_active:
            self.apply_settings()
            
            # Get current track info to pass to overlay manager
            current_track_info = self.get_current_track_info()
            
            # Try to load the centerline track map if it exists
            if os.path.exists('centerline_track_map.json'):
                try:
                    # Load track data safely with null byte cleaning
                    track_data = self._load_json_file_safely('centerline_track_map.json')
                    
                    # Validate required fields
                    if 'centerline_positions' not in track_data:
                        raise KeyError("Missing 'centerline_positions' in track data")
                    
                    # Start overlay with current track info (important for auto-detection)
                    if current_track_info:
                        track_name, track_config = current_track_info
                        logger.info(f"🔍 Starting overlay with track: {track_name} ({track_config})")
                        success = self.overlay_manager.start_overlay(track_name, track_config)
                    else:
                        logger.warning("🔍 No current track info available, starting overlay without track data")
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
                    # Fall back to normal overlay start with track info
                    if current_track_info:
                        track_name, track_config = current_track_info
                        logger.info(f"🔍 Fallback: Starting overlay with track: {track_name} ({track_config})")
                        success = self.overlay_manager.start_overlay(track_name, track_config)
                    else:
                        logger.warning("🔍 Fallback: No current track info available")
                        success = self.overlay_manager.start_overlay()
                        
                    if success:
                        self.status_label.setText("Track map overlay started (no centerline data found).")
                        self.start_button.setEnabled(False)
                        self.stop_button.setEnabled(True)
                    else:
                        self.status_label.setText("Failed to start overlay. Check if iRacing is running.")
            else:
                # No centerline data available - start with current track info from database
                if current_track_info:
                    track_name, track_config = current_track_info
                    logger.info(f"🔍 No centerline file: Starting overlay with track: {track_name} ({track_config})")
                    success = self.overlay_manager.start_overlay(track_name, track_config)
                else:
                    logger.warning("🔍 No centerline file and no current track info available")
                    success = self.overlay_manager.start_overlay()
                    
                if success:
                    if current_track_info:
                        track_name, track_config = current_track_info
                        full_name = track_name
                        if track_config and track_config != track_name:
                            full_name = f"{track_name} - {track_config}"
                        self.status_label.setText(f"Track map overlay started for {full_name}!")
                    else:
                        self.status_label.setText("Track map overlay started (no track data - use Track Builder to create one!).")
                    
                    self.start_button.setEnabled(False)
                    self.stop_button.setEnabled(True)
                    
                    QMessageBox.information(
                        self, "Overlay Started",
                        "🗺️ Track map overlay is now active!\n\n"
                        "ℹ️ Loading track map from database...\n"
                        "🎯 Use the 'Track Builder' tab to create a perfect track map\n"
                        "   if no existing map is found.\n\n"
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
            
            # Clear test overlay flag
            self._is_test_overlay = False
        else:
            self.status_label.setText("Overlay is not running.")

    def accept(self):
        """Handle OK button click."""
        self.apply_settings()
        
        # If it's a test overlay, don't ask - just keep it running
        if self.overlay_manager.is_active and not getattr(self, '_is_test_overlay', False):
            reply = QMessageBox.question(
                self, "Overlay Running",
                "Track map overlay is currently running. Keep it running?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.stop_overlay()
        elif getattr(self, '_is_test_overlay', False):
            # For test overlays, show a helpful message
            QMessageBox.information(
                self, "Test Overlay Active",
                "✅ Test overlay will continue running!\n\n"
                "To stop it:\n"
                "• Press 'Q' on the overlay, OR\n"
                "• Reopen this dialog and click 'Stop Overlay'"
            )
        
        # Stop track builder if running
        if self.track_builder_thread and self.track_builder_thread.isRunning():
            self.stop_track_builder()
        
        super().accept()

    def reject(self):
        """Handle Cancel button click."""
        # If it's a test overlay, don't ask - just keep it running
        if self.overlay_manager.is_active and not getattr(self, '_is_test_overlay', False):
            reply = QMessageBox.question(
                self, "Overlay Running",
                "Track map overlay is currently running. Stop it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_overlay()
        elif getattr(self, '_is_test_overlay', False):
            # For test overlays, show a helpful message
            QMessageBox.information(
                self, "Test Overlay Active",
                "✅ Test overlay will continue running!\n\n"
                "To stop it:\n"
                "• Press 'Q' on the overlay, OR\n"
                "• Reopen this dialog and click 'Stop Overlay'"
            )
        
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

    def check_existing_track_map(self):
        """Check if a track map already exists in the database for the current track."""
        try:
            # Import here to avoid issues if not installed
            from trackpro.database.supabase_client import get_supabase_client
            
            # Get current track info from iRacing
            current_track_info = self.get_current_track_info()
            if not current_track_info:
                print("🔍 No current track info available for database check")
                return None
            
            track_name, track_config = current_track_info
            print(f"🔍 Checking database for existing track map: {track_name} ({track_config})")
            
            # Query Supabase for existing track map
            supabase = get_supabase_client()
            if not supabase:
                print("⚠️ Supabase client not available")
                return None
            
            # Build query
            query = supabase.table('tracks').select('id, name, config, track_map, corners, last_analysis_date, analysis_metadata')
            query = query.eq('name', track_name)
            
            if track_config and track_config != track_name:
                query = query.eq('config', track_config)
            
            # Execute query
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                track_data = result.data[0]
                
                # Check if it has a track map
                if track_data.get('track_map') and len(track_data.get('track_map', [])) > 0:
                    print(f"✅ Found existing track map with {len(track_data['track_map'])} points")
                    print(f"📅 Last analyzed: {track_data.get('last_analysis_date', 'Unknown')}")
                    return track_data
                else:
                    print(f"📍 Track exists but no map data available")
                    return None
            else:
                print(f"📍 No existing track record found for {track_name}")
                return None
                
        except Exception as e:
            print(f"⚠️ Error checking existing track map: {e}")
            return None

    def handle_existing_track_map(self, track_data):
        """Handle when an existing track map is found - offer to load or rebuild."""
        track_name = track_data.get('name', 'Unknown Track')
        config = track_data.get('config')
        last_analysis = track_data.get('last_analysis_date', 'Unknown')
        track_map_points = len(track_data.get('track_map', []))
        corners_count = len(track_data.get('corners', []))
        
        # Build display text
        full_name = track_name
        if config and config != track_name:
            full_name = f"{track_name} - {config}"
        
        # Create detailed dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Existing Track Map Found")
        msg.setIcon(QMessageBox.Icon.Question)
        
        msg.setText(f"<h3>Track Map Available</h3>"
                   f"<b>{full_name}</b><br><br>"
                   f"📊 <b>{track_map_points:,}</b> centerline points<br>"
                   f"🎯 <b>{corners_count}</b> corners detected<br>"
                   f"📅 Last updated: <b>{last_analysis}</b><br><br>"
                   f"What would you like to do?")
        
        # Add custom buttons
        load_button = msg.addButton("🚀 Load Existing Map", QMessageBox.AcceptRole)
        rebuild_button = msg.addButton("🔄 Rebuild New Map", QMessageBox.ButtonRole.RejectRole)
        cancel_button = msg.addButton("❌ Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(load_button)
        msg.exec()
        
        if msg.clickedButton() == load_button:
            self.load_existing_track_map(track_data)
        elif msg.clickedButton() == rebuild_button:
            print("🔄 User chose to rebuild - continuing with track builder...")
            self.continue_track_builder_start()
        else:
            print("❌ User cancelled track map operation")

    def load_existing_track_map(self, track_data):
        """Load an existing track map from the database."""
        try:
            print(f"🚀 Loading existing track map...")
            
            track_map = track_data.get('track_map', [])
            corners = track_data.get('corners', [])
            
            if not track_map:
                QMessageBox.warning(self, "Load Error", "Track map data is empty or invalid.")
                return
            
            # Convert track map to the format expected by the UI
            centerline_track = [(point['x'], point['y']) for point in track_map]
            
            # Convert corners to corner objects if needed
            corner_objects = []
            for corner_data in corners:
                corner_objects.append(corner_data)  # Already in dict format
            
            # Update UI with loaded data
            self.builder_status_label.setText(f"✅ Loaded existing track map ({len(centerline_track)} points, {len(corner_objects)} corners)")
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Track Map Loaded")
            
            # Simulate completion signal for loaded data
            self.on_centerline_generated_from_load(centerline_track, corner_objects, track_data)
            
            print(f"✅ Successfully loaded existing track map with {len(centerline_track)} points and {len(corner_objects)} corners")
            
        except Exception as e:
            error_msg = f"Error loading existing track map: {str(e)}"
            print(f"❌ {error_msg}")
            QMessageBox.critical(self, "Load Error", error_msg)

    def continue_track_builder_start(self):
        """Continue with the normal track builder start process (for rebuild option)."""
        # Reset progress
        self.progress_bar.setValue(0)
        self.builder_status_label.setText("Starting track builder...")
        
        # Continue with the original track builder startup logic
        # Get global iRacing connection from parent if available
        simple_iracing_api = None
        try:
            if hasattr(self.parent(), 'global_iracing_api'):
                simple_iracing_api = self.parent().global_iracing_api
                print("🔗 Using global iRacing connection for track builder")
        except Exception as e:
            print(f"Warning: Could not get global iRacing connection: {e}")

        # Create track builder thread
        self.track_builder_thread = TrackBuilderThread(simple_iracing_api)

        # Connect standard thread signals - SIMPLIFIED: One clean signal path
        self.track_builder_thread.status_updated.connect(self.on_builder_status_updated)
        self.track_builder_thread.progress_updated.connect(self.on_builder_progress_updated)
        self.track_builder_thread.track_update.connect(self._on_track_update)  # ADDED: Direct track updates
        self.track_builder_thread.centerline_generated.connect(self.on_centerline_generated)
        self.track_builder_thread.error_occurred.connect(self.on_builder_error)
        self.track_builder_thread.finished.connect(self.on_builder_finished)
        
        # DIRECT CONNECTION: Connect straight to the worker when it's ready
        self.track_builder_thread.track_manager_ready.connect(self._connect_directly_to_worker)
        
        print("🐛 DEBUG: Essential signals connected, starting thread...")
        
        self.track_builder_thread.start()

    def get_current_track_info(self):
        """Get current track name and configuration from iRacing."""
        try:
            # Try to get from global iRacing connection first
            simple_iracing_api = None
            if hasattr(self.parent(), 'global_iracing_api'):
                simple_iracing_api = self.parent().global_iracing_api
            
            if simple_iracing_api and simple_iracing_api.ir and simple_iracing_api.ir.is_connected:
                track_name = simple_iracing_api.ir['WeekendInfo']['TrackDisplayName']
                track_config = simple_iracing_api.ir['WeekendInfo']['TrackConfigName']
                print(f"🔍 Got track info from global connection: {track_name} ({track_config})")
                return track_name, track_config
            else:
                # Fallback: create temporary connection
                import irsdk
                ir = irsdk.IRSDK()
                if ir.startup() and ir.is_connected:
                    track_name = ir['WeekendInfo']['TrackDisplayName']
                    track_config = ir['WeekendInfo']['TrackConfigName']
                    ir.shutdown()
                    print(f"🔍 Got track info from temporary connection: {track_name} ({track_config})")
                    return track_name, track_config
                
        except Exception as e:
            print(f"⚠️ Error getting track info: {e}")
        
        return None

    def on_centerline_generated_from_load(self, centerline_track, corners, track_data):
        """Handle centerline generation from loaded data (not real-time generation)."""
        try:
            print(f"📊 Processing loaded track map: {len(centerline_track)} points, {len(corners)} corners")
            
            # Store the loaded data in the same way as generated data
            self.current_centerline = centerline_track
            self.current_corners = corners
            
            # Update the track builder log
            track_name = track_data.get('name', 'Unknown Track')
            config = track_data.get('config')
            full_name = track_name
            if config and config != track_name:
                full_name = f"{track_name} - {config}"
            
            log_entry = f"🚀 LOADED: {full_name}\n"
            log_entry += f"📊 Centerline: {len(centerline_track)} points\n"
            log_entry += f"🎯 Corners: {len(corners)} detected\n"
            log_entry += f"📅 Last Updated: {track_data.get('last_analysis_date', 'Unknown')}\n"
            log_entry += "=" * 50 + "\n"
            
            self.builder_log.append(log_entry)
            
            # Enable track map overlay if not already enabled
            if not self.track_map_enabled_checkbox.isChecked():
                self.track_map_enabled_checkbox.setChecked(True)
                print("✅ Automatically enabled track map overlay for loaded data")
            
            # Update the parent overlay if it exists
            if hasattr(self.parent(), 'overlay_widget') and self.parent().overlay_widget:
                self.parent().overlay_widget.set_track_map(centerline_track)
                self.parent().overlay_widget.set_corners(corners)
                print("🗺️ Updated overlay with loaded track map")
            
            QMessageBox.information(self, "Track Map Loaded", 
                                   f"Successfully loaded track map for {full_name}!\n\n"
                                   f"📊 {len(centerline_track)} centerline points\n"
                                   f"🎯 {len(corners)} corners")
            
        except Exception as e:
            error_msg = f"Error processing loaded track map: {str(e)}"
            print(f"❌ {error_msg}")
            QMessageBox.critical(self, "Processing Error", error_msg)

    def check_track_availability_status(self):
        """Check and display track map availability status for the current track."""
        try:
            current_track_info = self.get_current_track_info()
            if not current_track_info:
                self.track_availability_label.setText("⚠️ Not connected to iRacing - cannot check track maps")
                self.track_availability_label.setStyleSheet("color: #FFA500; font-style: italic; padding: 5px;")
                return
            
            track_name, track_config = current_track_info
            full_name = track_name
            if track_config and track_config != track_name:
                full_name = f"{track_name} - {track_config}"
            
            # Check for existing track map
            existing_track_data = self.check_existing_track_map()
            
            if existing_track_data:
                track_map_points = len(existing_track_data.get('track_map', []))
                corners_count = len(existing_track_data.get('corners', []))
                last_analysis = existing_track_data.get('last_analysis_date', 'Unknown')
                
                self.track_availability_label.setText(
                    f"✅ <b>{full_name}</b> track map available "
                    f"({track_map_points:,} points, {corners_count} corners, updated {last_analysis})"
                )
                self.track_availability_label.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 5px;")
            else:
                self.track_availability_label.setText(
                    f"📍 <b>{full_name}</b> - No existing track map (will create new)"
                )
                self.track_availability_label.setStyleSheet("color: #2196F3; font-style: italic; padding: 5px;")
                
        except Exception as e:
            print(f"⚠️ Error checking track availability: {e}")
            self.track_availability_label.setText("⚠️ Could not check track map availability")
            self.track_availability_label.setStyleSheet("color: #FFA500; font-style: italic; padding: 5px;")
