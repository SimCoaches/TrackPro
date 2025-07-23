"""
Track Map Overlay System - Real-time transparent track map with car position
Shows track shape, corner numbers, and live car position as a transparent overlay
"""

import logging
import math
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont

from .simple_iracing import SimpleIRacingAPI
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class TrackMapOverlayWorker(QThread):
    """Worker thread that handles real-time telemetry data for track map overlay."""
    
    position_updated = pyqtSignal(float)  # track_position
    connection_status = pyqtSignal(bool)  # is_connected
    
    def __init__(self, shared_iracing_api=None):
        super().__init__()
        self.running = False
        self.iracing_api = shared_iracing_api
        
        # Only create a new iRacing API if no shared one is provided
        if not self.iracing_api:
            try:
                self.iracing_api = SimpleIRacingAPI()
                logger.info("🗺️ Created new iRacing API for overlay worker")
            except Exception as e:
                logger.warning(f"🗺️ iRacing API not available for overlay worker: {e}")
                self.iracing_api = None
        else:
            logger.info("🗺️ Using shared iRacing API for overlay worker")
    
    def run(self):
        """Main thread loop for telemetry monitoring."""
        self.running = True
        logger.info("🗺️ Track map overlay worker started")
        
        # Only register for telemetry if iRacing API is available
        if self.iracing_api:
            try:
                # Ensure we're working with the correct API object
                if not hasattr(self.iracing_api, 'register_on_telemetry_data'):
                    logger.error("🗺️ iRacing API missing required methods")
                    self.connection_status.emit(False)
                    return
                
                # Register for telemetry updates with proper error handling
                logger.info("🗺️ Registering for telemetry callbacks...")
                self.iracing_api.register_on_telemetry_data(self._on_telemetry_data)
                self.iracing_api.register_on_connection_changed(self._on_connection_changed)
                
                # Check initial connection status
                is_connected = False
                if hasattr(self.iracing_api, 'is_connected'):
                    is_connected = self.iracing_api.is_connected()
                elif hasattr(self.iracing_api, '_is_connected'):
                    is_connected = self.iracing_api._is_connected
                
                self.connection_status.emit(is_connected)
                logger.info(f"🗺️ Registered for iRacing telemetry updates, initial connection: {is_connected}")
                
            except Exception as e:
                logger.error(f"🗺️ Failed to register for iRacing updates: {e}")
                import traceback
                logger.error(f"🗺️ Full traceback: {traceback.format_exc()}")
                self.iracing_api = None
                self.connection_status.emit(False)
        else:
            logger.warning("🗺️ Running without iRacing connection - overlay will work but no live position updates")
            self.connection_status.emit(False)
        
        # Main worker loop with proper exception handling
        try:
            while self.running:
                self.msleep(100)  # Update every 100ms
        except Exception as e:
            logger.error(f"🗺️ Error in worker loop: {e}")
        
        logger.info("🗺️ Track map overlay worker stopped")
    
    def stop(self):
        """Stop the worker thread."""
        logger.info("🗺️ Stopping track map overlay worker...")
        self.running = False
        self.wait()
    
    def _on_telemetry_data(self, telemetry_data):
        """Process telemetry data and emit position updates."""
        if not telemetry_data:
            return
        
        # Add debug logging occasionally to help diagnose issues
        if not hasattr(self, '_last_telemetry_debug_time') or (time.time() - self._last_telemetry_debug_time) > 10.0:
            logger.debug(f"🗺️ Worker received telemetry data with keys: {list(telemetry_data.keys())}")
            self._last_telemetry_debug_time = time.time()
        
        try:
            track_position = telemetry_data.get('LapDistPct', telemetry_data.get('track_position'))
            if track_position is not None:
                # Validate track position value
                if not isinstance(track_position, (int, float)):
                    logger.warning(f"🗺️ Invalid track position type: {type(track_position)}")
                    return
                    
                # Ensure position is in valid range
                track_position = max(0.0, min(1.0, float(track_position)))
                
                # Only emit signal if position changed significantly (reduce spam and Qt overhead)
                if not hasattr(self, '_last_logged_position') or abs(track_position - self._last_logged_position) > 0.01:
                    self._last_logged_position = track_position
                    logger.debug(f"🗺️ Emitting position update: {track_position:.3f}")
                    
                    # Emit signal with error handling for Qt6 thread safety
                    try:
                        self.position_updated.emit(track_position)
                    except Exception as signal_error:
                        logger.error(f"🗺️ Error emitting position signal: {signal_error}")
                        
            else:
                # Log if we're not getting track position data (but limit frequency)
                if not hasattr(self, '_last_no_position_log') or (time.time() - self._last_no_position_log) > 5.0:
                    logger.debug(f"🗺️ No track position in telemetry data. Keys: {list(telemetry_data.keys())}")
                    self._last_no_position_log = time.time()
                    
        except Exception as e:
            logger.error(f"🗺️ Error processing telemetry data: {e}")
            import traceback
            logger.error(f"🗺️ Telemetry processing traceback: {traceback.format_exc()}")
    
    def _on_connection_changed(self, is_connected):
        """Handle iRacing connection status changes."""
        try:
            logger.info(f"🗺️ iRacing connection changed: {'CONNECTED' if is_connected else 'DISCONNECTED'}")
            
            # Emit signal with error handling for Qt6 thread safety
            try:
                self.connection_status.emit(is_connected)
            except Exception as signal_error:
                logger.error(f"🗺️ Error emitting connection status signal: {signal_error}")
                
        except Exception as e:
            logger.error(f"🗺️ Error handling connection change: {e}")
            import traceback
            logger.error(f"🗺️ Connection change traceback: {traceback.format_exc()}")


class TrackMapGamingOverlay(QWidget):
    overlay_closed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Add debug flag - disabled now that we have global connection
        self.debug_mode = False  # Disable debug mode now that we use shared connection
        if self.debug_mode:
            logger.info("🐛 DEBUG MODE ENABLED for TrackMapGamingOverlay")

        self.track_coordinates = []
        self.corner_data = []
        self.track_bounds = {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0}
        self.current_track_position = 0.0
        self.current_screen_x = 0
        self.current_screen_y = 0
        
        self.fixed_window_width = 800  # fixed window size
        self.fixed_window_height = 600
        self.padding_fraction = 0.05  # 5% padding inside normalized space

        self.is_locked = True
        self.drag_start_pos = None

        self.show_hover_controls = False
        self.hover_controls_timer = QTimer()
        self.hover_controls_timer.timeout.connect(self._hide_hover_controls)
        self.hover_controls_timer.setSingleShot(True)

        self.lock_button_rect = None
        self.close_button_rect = None
        self.hover_lock_button = False
        self.hover_close_button = False

        # Load saved settings
        self._load_settings()
        
        # Set defaults if not loaded from settings
        if not hasattr(self, 'show_corners'):
            self.show_corners = True
        if not hasattr(self, 'show_position_dot'):
            self.show_position_dot = True
        if not hasattr(self, 'show_start_finish_line'):
            self.show_start_finish_line = False  # Make it subtle by default
        if not hasattr(self, 'track_line_width'):
            self.track_line_width = 3
        if not hasattr(self, 'corner_font_size'):
            self.corner_font_size = 12
        if not hasattr(self, 'overlay_scale'):
            self.overlay_scale = 0.3  # Match default settings (30%)
        
        # Colors - set defaults if not loaded
        if not hasattr(self, 'track_color'):
            self.track_color = QColor(255, 255, 255, 200)
        if not hasattr(self, 'corner_color'):
            self.corner_color = QColor(255, 255, 0, 200)
        if not hasattr(self, 'position_color'):
            self.position_color = QColor(0, 255, 0, 255)
        if not hasattr(self, 'start_finish_color'):
            self.start_finish_color = QColor(255, 255, 255, 120)  # Subtle white line

        self.position_pulse_timer = QTimer()
        self.position_pulse_timer.timeout.connect(self._pulse_position_dot)
        self.position_pulse_timer.start(500)
        self.position_pulse_scale = 1.0
        
        self.setup_overlay()
        logger.info("🗺️ Track map floating overlay initialized")
    
    def _load_settings(self):
        """Load overlay settings from persistent storage."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings('TrackPro', 'TrackMapOverlay')
            
            # Load overlay scale
            self.overlay_scale = settings.value('overlay_scale', 0.3, type=float)
            
            # Load visual settings
            self.show_corners = settings.value('show_corners', True, type=bool)
            self.show_position_dot = settings.value('show_position_dot', True, type=bool)
            self.show_start_finish_line = settings.value('show_start_finish_line', False, type=bool)
            self.track_line_width = settings.value('track_line_width', 3, type=int)
            self.corner_font_size = settings.value('corner_font_size', 12, type=int)
            
            # Load colors
            self.track_color = QColor(settings.value('track_color', QColor(255, 255, 255, 200)))
            self.corner_color = QColor(settings.value('corner_color', QColor(255, 255, 0, 200)))
            self.position_color = QColor(settings.value('position_color', QColor(0, 255, 0, 255)))
            self.start_finish_color = QColor(settings.value('start_finish_color', QColor(255, 255, 255, 120)))
            
            logger.info(f"🗺️ Loaded overlay settings - Scale: {self.overlay_scale:.1f}")
            
        except Exception as e:
            logger.warning(f"🗺️ Could not load overlay settings: {e}")
            # Settings will use defaults set in constructor
    
    def _save_settings(self):
        """Save overlay settings to persistent storage."""
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings('TrackPro', 'TrackMapOverlay')
            
            # Save overlay scale
            settings.setValue('overlay_scale', self.overlay_scale)
            
            # Save visual settings
            settings.setValue('show_corners', self.show_corners)
            settings.setValue('show_position_dot', self.show_position_dot)
            settings.setValue('show_start_finish_line', self.show_start_finish_line)
            settings.setValue('track_line_width', self.track_line_width)
            settings.setValue('corner_font_size', self.corner_font_size)
            
            # Save colors
            settings.setValue('track_color', self.track_color)
            settings.setValue('corner_color', self.corner_color)
            settings.setValue('position_color', self.position_color)
            settings.setValue('start_finish_color', self.start_finish_color)
            
            logger.info(f"🗺️ Saved overlay settings - Scale: {self.overlay_scale:.1f}")
            
        except Exception as e:
            logger.warning(f"🗺️ Could not save overlay settings: {e}")
    
    def setup_overlay(self):
        if self.debug_mode:
            logger.info("🐛 DEBUG: Setting up overlay window...")
            
        # Window flags for floating transparent window
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        self.setWindowFlags(flags)
        
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: Window flags set: {flags}")
            
        # Make window transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # CRITICAL: Make sure mouse events are NOT blocked
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        if self.debug_mode:
            logger.info("🐛 DEBUG: Window attributes set - TranslucentBackground=True, TransparentForMouseEvents=False")
            
        # Set focus policy to accept keyboard input
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        if self.debug_mode:
            logger.info("🐛 DEBUG: Focus policy set to StrongFocus")
            
        # Position and size window
        self.setGeometry(100, 100, self.fixed_window_width, self.fixed_window_height)
        self.setWindowTitle("TrackPro Track Map Overlay")
        
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: Window geometry set: x=100, y=100, w={self.fixed_window_width}, h={self.fixed_window_height}")
            logger.info(f"🐛 DEBUG: Window title set: {self.windowTitle()}")
            
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        if self.debug_mode:
            logger.info("🐛 DEBUG: Mouse tracking enabled")
            logger.info(f"🐛 DEBUG: Initial lock state: {'LOCKED' if self.is_locked else 'UNLOCKED'}")
            
        logger.info(f"🗺️ Fixed overlay window initialized: {self.fixed_window_width}x{self.fixed_window_height}")

    def load_centerline_track_data(self, file_path: str = None):
        try:
            import json, os
            if not file_path:
                file_path = 'centerline_track_map.json'
            if not os.path.exists(file_path):
                logger.warning(f"Centerline file not found: {file_path}")
                return False
            with open(file_path, 'r') as f:
                data = json.load(f)
            positions = data.get('centerline_positions', [])
            if positions:
                self.track_coordinates = [(p[0], p[1]) for p in positions]
                self._calculate_track_bounds()
                logger.info(f"🎯 Loaded {len(self.track_coordinates)} coordinates from {file_path}")
                return True
            else:
                logger.error("Centerline file missing positions")
                return False
        except Exception as e:
            logger.error(f"Error loading centerline: {e}")
            return False

    def _calculate_track_bounds(self):
        if not self.track_coordinates:
            return
        xs, ys = zip(*self.track_coordinates)
        self.track_bounds = {
            'min_x': min(xs), 'max_x': max(xs),
            'min_y': min(ys), 'max_y': max(ys)
        }
        logger.debug(f"Calculated track bounds: {self.track_bounds}")
        
        # Auto-resize window to fit track after bounds are calculated
        self._resize_window_to_fit_track()

    def _resize_window_to_fit_track(self):
        """Automatically resize window to fit track with current scale and padding."""
        if not self.track_coordinates or not self.track_bounds:
            return
        
        # Calculate track dimensions
        track_width = self.track_bounds['max_x'] - self.track_bounds['min_x']
        track_height = self.track_bounds['max_y'] - self.track_bounds['min_y']
        
        if track_width <= 0 or track_height <= 0:
            return
        
        # Calculate aspect ratio
        track_aspect = track_width / track_height
        
        # Base size for window (this determines the overall scale)
        base_size = 400  # Base dimension in pixels
        
        # Calculate window dimensions based on track aspect ratio and scale
        if track_aspect > 1:  # Wider than tall
            window_width = int(base_size * self.overlay_scale)
            window_height = int(base_size / track_aspect * self.overlay_scale)
        else:  # Taller than wide
            window_width = int(base_size * track_aspect * self.overlay_scale)
            window_height = int(base_size * self.overlay_scale)
        
        # Add padding for hover controls and margins
        padding = 80  # Extra space for controls and margins
        window_width += padding
        window_height += padding
        
        # Ensure minimum size
        window_width = max(window_width, 200)
        window_height = max(window_height, 150)
        
        # Ensure maximum size (don't let it get too big)
        max_size = 1000
        if window_width > max_size or window_height > max_size:
            scale_factor = max_size / max(window_width, window_height)
            window_width = int(window_width * scale_factor)
            window_height = int(window_height * scale_factor)
        
        # Store current position before resizing
        current_pos = self.pos()
        
        # Resize the window
        self.resize(window_width, window_height)
        
        # Keep the window in the same position (top-left corner)
        self.move(current_pos)
        
        logger.info(f"🗺️ Window resized to fit track: {window_width}x{window_height} (scale: {self.overlay_scale:.1f})")

    def update_scale(self, new_scale: float):
        """Update the overlay scale and resize window accordingly."""
        self.overlay_scale = new_scale
        self._resize_window_to_fit_track()
        self._save_settings()  # Save settings when scale changes
        self.update()  # Trigger repaint

    def update_car_position(self, track_position: float):
        # Ensure this method runs on the main thread for Qt6 compatibility
        if not self.thread() == QApplication.instance().thread():
            logger.warning("🗺️ update_car_position called from wrong thread - Qt6 may have issues")
        
        # Add debug logging occasionally to help diagnose issues
        if not hasattr(self, '_last_position_debug_time') or (time.time() - self._last_position_debug_time) > 5.0:
            logger.debug(f"🚗 Updating car position: track_position={track_position:.3f}, track_coordinates_loaded={len(self.track_coordinates) if self.track_coordinates else 0}")
            self._last_position_debug_time = time.time()
            
        # Only log position updates if they changed significantly to reduce spam
        if not hasattr(self, '_last_position_update') or abs(track_position - self._last_position_update) > 0.01:
            self._last_position_update = track_position
            
        try:
            self.current_track_position = track_position
            x, y = self._track_position_to_screen(track_position)
            self.current_screen_x, self.current_screen_y = x, y
            
            # Trigger repaint safely for Qt6
            self.update()
            
        except Exception as e:
            logger.error(f"🗺️ Error updating car position: {e}")
            import traceback
            logger.error(f"🗺️ Position update traceback: {traceback.format_exc()}")

    def _track_position_to_screen(self, track_position: float) -> Tuple[int, int]:
        if not self.track_coordinates:
            return 0, 0
        
        num_points = len(self.track_coordinates)
        if num_points < 2:
            return 0, 0
        
        # Handle track position with interpolation for smoother movement
        # Track position is typically 0.0 to 1.0, but handle edge cases
        track_position = max(0.0, min(1.0, track_position))
        
        # Calculate the exact position between two points
        exact_idx = track_position * (num_points - 1)
        idx = int(exact_idx)
        fraction = exact_idx - idx
        
        # Handle edge case where we're at the very end
        if idx >= num_points - 1:
            idx = num_points - 1
            fraction = 0.0
        
        # Get current point
        world_x, world_y = self.track_coordinates[idx]
        
        # If we have a fraction, interpolate with the next point
        if fraction > 0.0 and idx < num_points - 1:
            next_x, next_y = self.track_coordinates[idx + 1]
            world_x = world_x + fraction * (next_x - world_x)
            world_y = world_y + fraction * (next_y - world_y)
        
        return self._world_to_screen(world_x, world_y)

    def _world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        b = self.track_bounds
        if b['max_x'] == b['min_x'] or b['max_y'] == b['min_y']:
            return self.width()//2, self.height()//2
        # Normalize to 0-1 range
        nx = (wx - b['min_x']) / (b['max_x'] - b['min_x'])
        ny = (wy - b['min_y']) / (b['max_y'] - b['min_y'])
        # Apply padding inside normalized space
        pad = self.padding_fraction
        nx = pad + (1 - 2*pad) * nx
        ny = pad + (1 - 2*pad) * ny
        # Convert to screen coordinates (scale is already applied during window resize)
        screen_x = int(nx * self.width())
        screen_y = int((1 - ny) * self.height())
        return screen_x, screen_y

    def _pulse_position_dot(self):
        self.position_pulse_scale = 1.0 + 0.3 * math.sin(time.time() * 4)
        if self.show_position_dot:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            if self.track_coordinates:
                self._draw_track(p)
            if self.show_position_dot:
                self._draw_position_dot(p)
            if self.show_hover_controls:
                self._draw_hover_controls(p)
        finally:
            p.end()

    def _draw_track(self, p):
        if not self.track_coordinates or len(self.track_coordinates) < 2:
            return
            
        # Set up pen for track drawing
        track_pen = QPen(self.track_color, self.track_line_width)
        p.setPen(track_pen)
        
        # Convert all world coordinates to screen coordinates first
        screen_points = []
        for coord in self.track_coordinates:
            x, y = self._world_to_screen(*coord)
            screen_points.append((x, y))
        
        # Remove duplicate consecutive points to prevent overlaps
        filtered_points = [screen_points[0]]
        for i in range(1, len(screen_points)):
            curr_x, curr_y = screen_points[i]
            prev_x, prev_y = filtered_points[-1]
            distance = math.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
            # Only add point if it's more than 1 pixel away from previous point
            if distance > 1:
                filtered_points.append((curr_x, curr_y))
        
        # Draw track segments
        for i in range(len(filtered_points)-1):
            x1, y1 = filtered_points[i]
            x2, y2 = filtered_points[i+1]
            p.drawLine(x1, y1, x2, y2)
        
        # Close the loop if needed
        if len(filtered_points) > 2:
            first_x, first_y = filtered_points[0]
            last_x, last_y = filtered_points[-1]
            
            # Calculate distance between first and last points
            gap_distance = math.sqrt((first_x - last_x)**2 + (first_y - last_y)**2)
            
            # Only draw closing line if there's a significant gap (more than 3 pixels)
            if gap_distance > 3:
                p.drawLine(last_x, last_y, first_x, first_y)
                
                # Optionally draw a start/finish line indicator
                if hasattr(self, 'show_start_finish_line') and self.show_start_finish_line:
                    self._draw_start_finish_line(p, first_x, first_y, last_x, last_y)

    def _draw_start_finish_line(self, p, first_x, first_y, last_x, last_y):
        """Draw a subtle start/finish line indicator across the gap."""
        # Calculate midpoint of the gap
        mid_x = (first_x + last_x) // 2
        mid_y = (first_y + last_y) // 2
        
        # Calculate perpendicular direction for the line
        dx = first_x - last_x
        dy = first_y - last_y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length > 0:
            # Normalize and get perpendicular vector
            perp_x = -dy / length
            perp_y = dx / length
            
            # Much shorter line - just a small subtle indicator
            line_length = self.track_line_width * 3  # Reduced from 8 to 3
            
            # Calculate line endpoints
            start_x = int(mid_x - perp_x * line_length)
            start_y = int(mid_y - perp_y * line_length)
            end_x = int(mid_x + perp_x * line_length)
            end_y = int(mid_y + perp_y * line_length)
            
            # Draw a very subtle start/finish line - just slightly thicker than track
            pen = QPen(self.start_finish_color, max(1, self.track_line_width - 1))
            p.setPen(pen)
            p.drawLine(start_x, start_y, end_x, end_y)

    def _draw_position_dot(self, p):
        # Check if we have valid track coordinates and position data
        if not self.track_coordinates or self.current_track_position < 0:
            return
            
        # Add debug logging occasionally to help diagnose issues
        if not hasattr(self, '_last_dot_debug_time') or (time.time() - self._last_dot_debug_time) > 5.0:
            logger.debug(f"🎯 Drawing position dot at screen ({self.current_screen_x}, {self.current_screen_y}) for track position {self.current_track_position:.3f}")
            self._last_dot_debug_time = time.time()
            
        pen = QPen(self.position_color, 2)
        p.setPen(pen)
        p.setBrush(QBrush(self.position_color))
        dot_size = int(8 * self.position_pulse_scale)
        p.drawEllipse(self.current_screen_x - dot_size, self.current_screen_y - dot_size, dot_size*2, dot_size*2)

    # --- MOUSE EVENTS WITH DEBUGGING ---

    def mousePressEvent(self, event):
        if self.debug_mode:
            logger.debug(f"[OVERLAY] mousePressEvent - Button: {event.button()}, Pos: ({event.x()}, {event.y()})")
            
        if event.button() == Qt.MouseButton.LeftButton:

                
            # Check if clicking on hover controls first
            if self.show_hover_controls:
                if self._is_over_lock_button(event.pos()):
                    self._toggle_lock()
                    event.accept()
                    return
                elif self._is_over_close_button(event.pos()):
                    self.close()
                    event.accept()
                    return
            
            # Handle window dragging when unlocked
            if not self.is_locked:
                self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self.debug_mode and hasattr(self, '_last_mouse_log_time'):
            import time
            # Only log mouse moves every 500ms to avoid spam
            if time.time() - self._last_mouse_log_time > 0.5:
                logger.info(f"🐛 DEBUG: mouseMoveEvent - Pos: ({event.x()}, {event.y()}), Lock: {'LOCKED' if self.is_locked else 'UNLOCKED'}")
                self._last_mouse_log_time = time.time()
        elif self.debug_mode:
            import time
            self._last_mouse_log_time = time.time()
            logger.info(f"🐛 DEBUG: First mouseMoveEvent - Pos: ({event.x()}, {event.y()})")
            
        # Always show hover controls when mouse moves inside window
        if not self.show_hover_controls:
            if self.debug_mode:
                logger.info("🐛 DEBUG: Showing hover controls due to mouse movement")
            self._show_hover_controls()
        
        # Update button hover states
        old_hover_lock = self.hover_lock_button
        old_hover_close = self.hover_close_button
        self.hover_lock_button = self._is_over_lock_button(event.pos())
        self.hover_close_button = self._is_over_close_button(event.pos())
        
        if self.debug_mode and (old_hover_lock != self.hover_lock_button or old_hover_close != self.hover_close_button):
            logger.info(f"🐛 DEBUG: Button hover states - Lock: {self.hover_lock_button}, Close: {self.hover_close_button}")
        
        # Handle window dragging
        if not self.is_locked and event.buttons() == Qt.MouseButton.LeftButton and self.drag_start_pos:
            if self.debug_mode:
                logger.info(f"🐛 DEBUG: Dragging window to: {event.globalPos() - self.drag_start_pos}")
            self.move(event.globalPos() - self.drag_start_pos)
            event.accept()
        else:
            event.ignore()
            
        # Update cursor based on state
        if self.hover_lock_button or self.hover_close_button:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif not self.is_locked:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        self.update()  # Update to show hover effects

    def mouseReleaseEvent(self, event):
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: mouseReleaseEvent - Button: {event.button()}")
            
        if event.button() == Qt.MouseButton.LeftButton:
            if self.debug_mode:
                logger.info("🐛 DEBUG: Ending drag operation")
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.drag_start_pos = None
            event.accept()
        else:
            event.ignore()

    # --- KEYBOARD EVENTS WITH DEBUGGING ---

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_L:
            self._toggle_lock()
            event.accept()
        elif event.key() == Qt.Key.Key_Q:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    # --- FOCUS EVENTS WITH DEBUGGING ---

    def focusInEvent(self, event):
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: focusInEvent - Reason: {event.reason()}")
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: focusOutEvent - Reason: {event.reason()}")
        super().focusOutEvent(event)

    # --- HOVER EVENTS WITH DEBUGGING ---

    def enterEvent(self, event):
        if self.debug_mode:
            logger.info("🐛 DEBUG: enterEvent - Mouse entered window")
        self._show_hover_controls()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.debug_mode:
            logger.info("🐛 DEBUG: leaveEvent - Mouse left window")
        if self.show_hover_controls:
            self.hover_controls_timer.start(500)  # Hide controls after 500ms
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    # --- HELPER METHODS WITH DEBUGGING ---

    def _toggle_lock(self):
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: _toggle_lock called - Current state: {'LOCKED' if self.is_locked else 'UNLOCKED'}")
            
        self.is_locked = not self.is_locked
        
        # Reset cursor and dragging state
        if self.is_locked:
            self.drag_start_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        self.update()
        
        status = "🔒 LOCKED" if self.is_locked else "🔓 UNLOCKED"
        logger.info(f"🗺️ Track map overlay {status} - {'Click-through mode' if self.is_locked else 'Draggable mode'}")
        
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: Lock toggle complete - New state: {'LOCKED' if self.is_locked else 'UNLOCKED'}")

    def _show_hover_controls(self):
        if self.debug_mode and not self.show_hover_controls:
            logger.info("🐛 DEBUG: _show_hover_controls - Showing controls")
            
        if not self.show_hover_controls:
            self.show_hover_controls = True
            self.update()
        self.hover_controls_timer.stop()  # Cancel any pending hide

    def _hide_hover_controls(self):
        if self.debug_mode:
            logger.info("🐛 DEBUG: _hide_hover_controls - Hiding controls")
            
        self.show_hover_controls = False
        self.hover_lock_button = False
        self.hover_close_button = False
        self.update()

    def _calculate_control_positions(self):
        """Calculate positions for hover control buttons."""
        window_width = self.width()
        window_height = self.height()
        
        button_size = 40  # Made bigger for easier clicking
        padding = 15
        
        # Lock button (top-left)
        lock_x = padding
        lock_y = padding
        self.lock_button_rect = (lock_x, lock_y, button_size, button_size)
        
        # Close button (top-right)
        close_x = window_width - button_size - padding
        close_y = padding
        self.close_button_rect = (close_x, close_y, button_size, button_size)
        
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: Control positions - Lock: {self.lock_button_rect}, Close: {self.close_button_rect}")

    def _is_over_lock_button(self, pos):
        """Check if position is over the lock button."""
        if not self.lock_button_rect:
            self._calculate_control_positions()
        x, y, w, h = self.lock_button_rect
        is_over = x <= pos.x() <= x + w and y <= pos.y() <= y + h
        if self.debug_mode and is_over:
            logger.info(f"🐛 DEBUG: Mouse is over LOCK button at {pos}")
        return is_over

    def _is_over_close_button(self, pos):
        """Check if position is over the close button."""
        if not self.close_button_rect:
            self._calculate_control_positions()
        x, y, w, h = self.close_button_rect
        is_over = x <= pos.x() <= x + w and y <= pos.y() <= y + h
        if self.debug_mode and is_over:
            logger.info(f"🐛 DEBUG: Mouse is over CLOSE button at {pos}")
        return is_over

    def _draw_hover_controls(self, painter):
        """Draw hover control buttons (lock and close)."""
        if self.debug_mode:
            logger.info("🐛 DEBUG: _draw_hover_controls called")
            
        self._calculate_control_positions()
        
        # Draw lock button
        lock_x, lock_y, lock_w, lock_h = self.lock_button_rect
        
        # Lock button background
        lock_bg_color = QColor(70, 130, 180, 200) if self.hover_lock_button else QColor(50, 50, 50, 180)
        painter.setBrush(QBrush(lock_bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        painter.drawRoundedRect(lock_x, lock_y, lock_w, lock_h, 5, 5)
        
        # Lock icon
        lock_symbol = "🔒" if self.is_locked else "🔓"
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(255, 255, 255, 255)))
        text_rect = painter.boundingRect(lock_x, lock_y, lock_w, lock_h, Qt.AlignmentFlag.AlignCenter, lock_symbol)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, lock_symbol)
        
        # Draw close button
        close_x, close_y, close_w, close_h = self.close_button_rect
        
        # Close button background
        close_bg_color = QColor(220, 53, 69, 200) if self.hover_close_button else QColor(50, 50, 50, 180)
        painter.setBrush(QBrush(close_bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        painter.drawRoundedRect(close_x, close_y, close_w, close_h, 5, 5)
        
        # Close icon (X)
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(255, 255, 255, 255)))
        text_rect = painter.boundingRect(close_x, close_y, close_w, close_h, Qt.AlignmentFlag.AlignCenter, "✕")
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "✕")
        
        if self.debug_mode:
            logger.info(f"🐛 DEBUG: Drew hover controls - Lock: {lock_symbol}, Hover states: Lock={self.hover_lock_button}, Close={self.hover_close_button}")

    def show_overlay(self):
        """Show the track map overlay."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Force focus to ensure keyboard events work
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        
        logger.info("🗺️ Track map overlay shown")

    def hide_overlay(self):
        """Hide the track map overlay."""
        self.hide()
        logger.info("🗺️ Track map overlay hidden")

    def closeEvent(self, event):
        # Add debugging to track when window is being closed
        import traceback
        logger.warning("🐛 OVERLAY WINDOW CLOSE EVENT! Stack trace:")
        for line in traceback.format_stack():
            logger.warning(f"🐛 {line.strip()}")
            
        if self.debug_mode:
            logger.info("🐛 DEBUG: closeEvent called")
        
        # Save settings before closing
        self._save_settings()
        
        self.position_pulse_timer.stop()
        logger.info("Overlay closed")
        self.overlay_closed.emit()
        event.accept()
    
    def load_track_data(self, track_name: str, track_config: str = None):
        """Load track coordinates and corner data from Supabase."""
        try:
            from ..database.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if not supabase:
                logger.error("Could not connect to Supabase")
                return False
            
            # Query for track data
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            result = track_query.execute()
            
            if not result.data:
                logger.warning(f"No track data found for: {track_name}")
                return False
            
            track_data = result.data[0]
            
            # Load track coordinates - check both possible field names
            track_coordinates = track_data.get('track_coordinates', track_data.get('track_map', []))
            if track_coordinates:
                self.track_coordinates = [(point['x'], point['y']) for point in track_coordinates]
                self._calculate_track_bounds()
                logger.info(f"Loaded {len(self.track_coordinates)} track coordinates")
            
            # Load corner data
            corners = track_data.get('corners', [])
            if corners:
                self.corner_data = corners
                logger.info(f"Loaded {len(self.corner_data)} corners")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading track data: {e}")
            return False

class TrackMapOverlayManager(QObject):
    """Manager for the track map overlay system."""
    
    def __init__(self, shared_iracing_api=None):
        super().__init__()
        self.overlay = None
        self.worker = None
        self.is_active = False
        self.current_track_name = None
        self.current_track_config = None
        self.shared_iracing_api = shared_iracing_api
    
    def start_overlay(self, track_name: str = None, track_config: str = None, centerline_file: str = None):
        """Start the track map overlay."""
        if self.is_active:
            logger.warning("Track map overlay already active")
            return False
        
        try:
            # Create overlay
            self.overlay = TrackMapGamingOverlay()
            self.overlay.overlay_closed.connect(self.on_overlay_closed)
            
            # Priority order for loading track data:
            # 1. Explicit centerline file
            # 2. Track data from Supabase (includes centerline if available)
            # 3. Local centerline file
            # 4. Current track from iRacing (auto-detect)
            
            data_loaded = False
            data_source = "no data"
            
            if centerline_file:
                # 1. Load specific centerline file
                if self.overlay.load_centerline_track_data(centerline_file):
                    data_loaded = True
                    data_source = f"centerline file: {centerline_file}"
                    logger.info(f"🎯 Loaded centerline track data from {centerline_file}")
                else:
                    logger.warning(f"Could not load centerline data from {centerline_file}")
            
            if not data_loaded and track_name:
                # 2. Load track data from Supabase (may include centerline)
                self.current_track_name = track_name
                self.current_track_config = track_config
                if self.overlay.load_track_data(track_name, track_config):
                    data_loaded = True
                    data_source = f"Supabase: {track_name}"
                    if track_config and track_config != track_name:
                        data_source += f" - {track_config}"
                    logger.info(f"🗺️ Loaded track data from Supabase: {data_source}")
                else:
                    logger.warning(f"Could not load track data for {track_name}")
            
            if not data_loaded:
                # 3. Try to auto-detect current track from iRacing FIRST
                current_track_info = self._get_current_iracing_track()
                if current_track_info:
                    track_name, track_config = current_track_info
                    self.current_track_name = track_name
                    self.current_track_config = track_config
                    
                    # Try to load from Supabase for current track
                    if self.overlay.load_track_data(track_name, track_config):
                        data_loaded = True
                        data_source = f"auto-detected: {track_name}"
                        if track_config and track_config != track_name:
                            data_source += f" - {track_config}"
                        logger.info(f"🗺️ Auto-detected and loaded track: {data_source}")
            
            if not data_loaded:
                # 4. Fall back to local centerline file (may be for different track)
                if self.overlay.load_centerline_track_data():
                    data_loaded = True
                    data_source = "local centerline file (fallback)"
                    logger.warning("🗺️ Using local centerline file as fallback - may not match current track")
                    logger.info("🎯 Loaded local centerline track data")
            
            # Create and start worker thread with shared iRacing API
            self.worker = TrackMapOverlayWorker(self.shared_iracing_api)
            
            # Connect signals with explicit Qt6-compatible connection types for thread safety
            try:
                self.worker.position_updated.connect(
                    self.overlay.update_car_position, Qt.ConnectionType.QueuedConnection
                )
                self.worker.connection_status.connect(
                    self.on_connection_status, Qt.ConnectionType.QueuedConnection
                )
                logger.info("🗺️ Worker signals connected successfully")
            except Exception as connection_error:
                logger.error(f"🗺️ Error connecting worker signals: {connection_error}")
                return False
            
            # Start worker thread
            try:
                self.worker.start()
                logger.info("🗺️ Worker thread started successfully")
            except Exception as worker_error:
                logger.error(f"🗺️ Error starting worker thread: {worker_error}")
                return False
            
            # Show overlay
            try:
                self.overlay.show_overlay()
                self.is_active = True
                logger.info(f"🗺️ Track map overlay started successfully with {data_source}")
            except Exception as show_error:
                logger.error(f"🗺️ Error showing overlay: {show_error}")
                # Clean up on error
                if self.worker:
                    self.worker.stop()
                    self.worker = None
                if self.overlay:
                    self.overlay.close()
                    self.overlay = None
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start track map overlay: {e}")
            return False
    
    def stop_overlay(self):
        """Stop the track map overlay."""
        if not self.is_active:
            logger.warning("Track map overlay not active")
            return
        
        # Add debugging to track who's calling stop_overlay
        import traceback
        logger.warning("🐛 STOP_OVERLAY CALLED! Stack trace:")
        for line in traceback.format_stack():
            logger.warning(f"🐛 {line.strip()}")
        
        try:
            # Stop worker thread
            if self.worker:
                self.worker.stop()
                self.worker = None
            
            # Hide and cleanup overlay
            if self.overlay:
                self.overlay.hide_overlay()
                self.overlay.close()
                self.overlay = None
            
            self.is_active = False
            logger.info("🗺️ Track map overlay stopped")
            
        except Exception as e:
            logger.error(f"Error stopping track map overlay: {e}")
    
    def toggle_overlay(self):
        """Toggle the track map overlay on/off."""
        if self.is_active:
            self.stop_overlay()
        else:
            self.start_overlay(self.current_track_name, self.current_track_config)
    
    def reload_track_data(self):
        """Reload track data for current track."""
        if self.overlay and self.current_track_name:
            self.overlay.load_track_data(self.current_track_name, self.current_track_config)

    def load_centerline_data(self, file_path: str = None):
        """Load centerline data into the current overlay."""
        if not self.overlay:
            logger.warning("No overlay active to load centerline data into")
            return False
        
        return self.overlay.load_centerline_track_data(file_path)

    def _get_current_iracing_track(self):
        """Get current track info from iRacing."""
        try:
            # First try to use shared iRacing API if available
            if self.shared_iracing_api and hasattr(self.shared_iracing_api, 'ir') and self.shared_iracing_api.ir:
                ir = self.shared_iracing_api.ir
                if ir and ir.is_connected:
                    track_name = ir['WeekendInfo']['TrackDisplayName']
                    track_config = ir['WeekendInfo']['TrackConfigName']
                    logger.info(f"🔍 Current track from shared API: {track_name} ({track_config})")
                    return track_name, track_config
            
            # Fallback: create temporary connection
            from .pyirsdk import irsdk
            ir = irsdk.IRSDK()
            if not ir.startup() or not ir.is_connected:
                return None
            
            track_name = ir['WeekendInfo']['TrackDisplayName']
            track_config = ir['WeekendInfo']['TrackConfigName']
            ir.shutdown()
            
            logger.info(f"🔍 Current track from temp connection: {track_name} ({track_config})")
            return track_name, track_config
            
        except Exception as e:
            logger.error(f"Error getting current iRacing track: {e}")
            return None
    
    def on_overlay_closed(self):
        """Handle overlay being closed by user."""
        # Add debugging to track when overlay is closed
        import traceback
        logger.warning("🐛 OVERLAY_CLOSED SIGNAL! Stack trace:")
        for line in traceback.format_stack():
            logger.warning(f"🐛 {line.strip()}")
            
        self.is_active = False
        if self.worker:
            self.worker.stop()
            self.worker = None
        logger.info("🗺️ Track map overlay closed by user")
    
    def on_connection_status(self, is_connected: bool):
        """Handle iRacing connection status changes."""
        if is_connected:
            logger.info("🗺️ iRacing connected - track map overlay active")
        else:
            logger.info("🗺️ iRacing disconnected - track map overlay inactive")
            
        # Debug: Check if overlay exists and what the current position state is
        if self.overlay:
            logger.debug(f"🗺️ Current overlay position: ({self.overlay.current_screen_x}, {self.overlay.current_screen_y})")
            logger.debug(f"🗺️ Show position dot: {self.overlay.show_position_dot}")
            logger.debug(f"🗺️ Track coordinates loaded: {len(self.overlay.track_coordinates)} points")
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update overlay visual settings."""
        if not self.overlay:
            return
        
        # Handle scale updates specially to trigger window resize
        if 'overlay_scale' in settings:
            scale_value = settings.pop('overlay_scale')  # Remove from dict to avoid double-setting
            self.overlay.update_scale(scale_value)
        
        # Update other overlay settings
        for key, value in settings.items():
            if hasattr(self.overlay, key):
                setattr(self.overlay, key, value)
        
        # Save settings after updating
        self.overlay._save_settings()
        
        # Trigger repaint
        self.overlay.update()
        logger.info("🗺️ Track map overlay settings updated")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_overlay()
        logger.info("🗺️ Track map overlay manager cleaned up")

    def test_connections(self):
        """Test that all signal connections are working properly for Qt6."""
        try:
            logger.info("🧪 Testing track map overlay connections...")
            
            # Test 1: Check if overlay exists
            if not self.overlay:
                logger.error("🧪 TEST FAILED: No overlay created")
                return False
                
            # Test 2: Check if worker exists and is running
            if not self.worker or not self.worker.isRunning():
                logger.error("🧪 TEST FAILED: Worker not running")
                return False
                
            # Test 3: Check if signals are connected
            if not self.worker.position_updated.receivers():
                logger.error("🧪 TEST FAILED: position_updated signal not connected")
                return False
                
            if not self.worker.connection_status.receivers():
                logger.error("🧪 TEST FAILED: connection_status signal not connected")
                return False
                
            # Test 4: Check if overlay has track data
            if not self.overlay.track_coordinates:
                logger.warning("🧪 TEST WARNING: No track coordinates loaded")
            else:
                logger.info(f"🧪 TEST SUCCESS: {len(self.overlay.track_coordinates)} track coordinates loaded")
                
            # Test 5: Try a test position update
            try:
                self.overlay.update_car_position(0.5)  # Test position at halfway point
                logger.info("🧪 TEST SUCCESS: Test position update worked")
            except Exception as position_error:
                logger.error(f"🧪 TEST FAILED: Position update error: {position_error}")
                return False
                
            logger.info("🧪 All track map overlay tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"🧪 TEST ERROR: {e}")
            return False