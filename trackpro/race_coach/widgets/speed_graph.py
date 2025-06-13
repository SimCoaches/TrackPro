from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import logging
from .graph_base import GraphBase

logger = logging.getLogger(__name__)

class SpeedGraphWidget(GraphBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#161b22')  # Modern dark background to match new design
        self.plot_widget.setTitle("Speed vs Distance")
        self.plot_widget.setLabel('bottom', "Distance (m)")
        
        # Configure Y-Axis for speed with better styling
        left_axis = self.plot_widget.getAxis('left')
        left_axis.setLabel("Speed (km/h)", color='#e6edf3')
        left_axis.setTextPen('#e6edf3')
        left_axis.setPen('#30363d')
        
        # Configure X-axis with better styling
        bottom_axis = self.plot_widget.getAxis('bottom')
        bottom_axis.setTextPen('#e6edf3')
        bottom_axis.setPen('#30363d')
        
        # Style the plot title
        title_item = self.plot_widget.plotItem.titleLabel
        title_item.setAttr('color', '#34d399')
        
        # Show grid lines for both axes with modern styling
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        
        # Disable mouse interaction
        self.plot_widget.plotItem.vb.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.plotItem.vb.disableAutoRange()
        
        # Create a modern legend in the top-right corner
        self.legend = self.plot_widget.addLegend(offset=(-20, 10), labelTextSize='10pt',
                                                 brush=(22, 27, 34, 180), 
                                                 pen='#30363d')
        
        # Create crosshair lines with modern styling
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#58a6ff', width=1, style=Qt.DotLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#58a6ff', width=1, style=Qt.DotLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        # Create text label for coordinates with modern styling
        self.label = pg.TextItem(text='', color='#e6edf3', anchor=(0, 1),
                                fill=pg.mkBrush(22, 27, 34, 180),
                                border=pg.mkPen('#30363d'))
        self.label.setPos(10, 10)
        self.plot_widget.addItem(self.label, ignoreBounds=True)
        
        # Create debug info text display
        self.debug_info_text = pg.TextItem(html="", anchor=(0, 0))
        self.debug_info_text.setPos(10, 10)
        self.plot_widget.addItem(self.debug_info_text)
        self.debug_info_text.hide()  # Initially hidden

        # Track context markers
        self.corner_markers = []
        self.distance_markers = []
        self.stopped_section_markers = []
        self.start_finish_line = pg.InfiniteLine(
            angle=90, 
            movable=False, 
            pen=pg.mkPen('g', width=2),
            label="Start/Finish", 
            labelOpts={'position': 0.1, 'color': 'g', 'fill': (0, 0, 0, 80)}
        )
        self.plot_widget.addItem(self.start_finish_line)
        self.start_finish_line.hide()  # Initially hidden
        
        # Track parameters
        self.track_length = 0
        
        # Connect mouse movement for crosshair
        self.plot_widget.scene().sigMouseMoved.connect(self.mouseMoved)
        
        # Connect mouse movement to crosshair update
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        
        # Initialize grid lines list for custom grid functionality
        self.grid_lines = []
        
        # Setup layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
        # Initialize plot items - these will be updated by update_graph/update_comparison_data
        self.speed_curve = self.plot_widget.plot(pen=pg.mkPen('#ff6b6b', width=2.5), name="Your Speed", autoDownsample=False, clipToView=False)
        self.speed_curve_b = self.plot_widget.plot(pen=pg.mkPen('#4ecdc4', width=2.5, style=Qt.SolidLine), name="Super Lap Speed", autoDownsample=False, clipToView=False)
        
        # Initially hide comparison curves
        self.speed_curve_b.hide()
        
        # Initialize empty data list for plot items (no longer used directly for curves)
        self.plot_items = [] 
        
        # Store message text item reference
        self.message_text = None
        
        self.comparison_mode = False # Initialize comparison mode
        
        self.reset_view()

        # Show grid lines for both axes
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Set custom grid for x-axis at intervals
        self.add_distance_grid()

    def mouseMoved(self, pos):
        """Handle mouse movement to update crosshairs and tooltip."""
        try:
            # Convert tuple to QPointF if needed (happens with SignalProxy)
            if isinstance(pos, tuple):
                from PyQt5.QtCore import QPointF
                if len(pos) >= 2:
                    pos = QPointF(pos[0], pos[1])
                elif len(pos) == 1:
                    pos = pos[0]
                else:
                    return  # Invalid tuple, skip this event
            
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
                x, y = mousePoint.x(), mousePoint.y()
                
                # Update crosshair positions
                self.vLine.setPos(x)
                self.hLine.setPos(y)
                
                # Find the actual speed values at the cursor position
                speed_value_a = None
                speed_value_b = None
                distance = x
                
                # Find the closest data point from Lap A
                if self.speed_curve.xData is not None and len(self.speed_curve.xData) > 0:
                    # Find the closest x point to the cursor
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(self.speed_curve.xData):
                        dist = abs(x_val - x)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0:
                        # Get actual speed value from the data
                        if closest_idx < len(self.speed_curve.yData):
                            speed_value_a = self.speed_curve.yData[closest_idx]

                # In comparison mode, also get data from Lap B
                if self.comparison_mode and self.speed_curve_b.xData is not None and len(self.speed_curve_b.xData) > 0:
                    # Find the closest x point to the cursor
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(self.speed_curve_b.xData):
                        dist = abs(x_val - x)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0:
                        # Get actual speed value from the data
                        if closest_idx < len(self.speed_curve_b.yData):
                            speed_value_b = self.speed_curve_b.yData[closest_idx]
                
                # Update tooltip label with data
                tooltip_text = f"Distance: {distance:.1f}m"
                
                if speed_value_a is not None:
                    tooltip_text += f"\nYour Speed: {speed_value_a:.1f} km/h"
                    
                if speed_value_b is not None:
                    tooltip_text += f"\nSuper Lap Speed: {speed_value_b:.1f} km/h"
                    
                    if speed_value_a is not None:
                        # Calculate and display delta
                        delta = speed_value_b - speed_value_a
                        tooltip_text += f"\nDelta: {delta:+.1f} km/h"
                    
                self.label.setText(tooltip_text)
                self.label.setPos(x, y)
        except Exception as e:
            # Silently handle any mouse movement errors to prevent console spam
            pass
        
    def reset_view(self):
        """Reset the view to default parameters."""
        # Set default view ranges for a new/empty plot
        self.plot_widget.setXRange(0, 1000, padding=0)  # Default to 1km track
        
        # Find a reasonable range for Y axis (0 to some max speed)
        self.plot_widget.setYRange(0, 300, padding=0.02)  # Default to max speed 300 km/h
        
    def clear_track_markers(self):
        """Clear all track-related markers."""
        # Remove corner markers
        for marker in self.corner_markers:
            if marker in self.plot_widget.items():
                self.plot_widget.removeItem(marker)
        self.corner_markers = []
        
        # Remove distance markers
        for marker in self.distance_markers:
            if marker in self.plot_widget.items():
                self.plot_widget.removeItem(marker)
        self.distance_markers = []
        
        # Remove stopped section markers
        for marker in self.stopped_section_markers:
            if marker in self.plot_widget.items():
                self.plot_widget.removeItem(marker)
        self.stopped_section_markers = []
        
        # Hide start/finish line
        self.start_finish_line.hide()
    
    def _add_track_context_markers(self, track_context, display_range_max):
        """Add track context markers to the graph.
        
        Args:
            track_context: Dictionary with track information
            display_range_max: Maximum display range for X axis
        """
        if not track_context:
            return
            
        self.clear_track_markers()
        
        # Add track corners
        corners = track_context.get('corners', {})
        if isinstance(corners, dict):
            for corner_num, corner_data in corners.items():
                distance = corner_data.get('distance', -1)
                if distance >= 0:
                    # Add vertical line for corner
                    corner_line = pg.InfiniteLine(
                        angle=90, 
                        movable=False, 
                        pen=pg.mkPen('b', width=1, style=Qt.DashLine),
                        label=f"T{corner_num}", 
                        labelOpts={'position': 0.05, 'color': 'b', 'fill': (0, 0, 0, 80)}
                    )
                    corner_line.setPos(distance)
                    self.plot_widget.addItem(corner_line)
                    self.corner_markers.append(corner_line)
        elif isinstance(corners, list):
            for i, corner_data in enumerate(corners):
                if isinstance(corner_data, tuple) and len(corner_data) >= 2:
                    # Handle (position, number) tuple format
                    position, number = corner_data
                    corner_line = pg.InfiniteLine(
                        angle=90, 
                        movable=False, 
                        pen=pg.mkPen('b', width=1, style=Qt.DashLine),
                        label=f"T{number}", 
                        labelOpts={'position': 0.05, 'color': 'b', 'fill': (0, 0, 0, 80)}
                    )
                    corner_line.setPos(position)
                    self.plot_widget.addItem(corner_line)
                    self.corner_markers.append(corner_line)
                elif isinstance(corner_data, dict):
                    distance = corner_data.get('distance', -1)
                    if distance >= 0:
                        corner_num = corner_data.get('number', i+1)
                        # Add vertical line for corner
                        corner_line = pg.InfiniteLine(
                            angle=90, 
                            movable=False, 
                            pen=pg.mkPen('b', width=1, style=Qt.DashLine),
                            label=f"T{corner_num}", 
                            labelOpts={'position': 0.05, 'color': 'b', 'fill': (0, 0, 0, 80)}
                        )
                        corner_line.setPos(distance)
                        self.plot_widget.addItem(corner_line)
                        self.corner_markers.append(corner_line)
        
        # Add distance markers (every 100m)
        marker_interval = 100  # meters
        if display_range_max > 5000:
            marker_interval = 500  # Use larger interval for long tracks
        elif display_range_max > 2000:
            marker_interval = 200  # Use medium interval for medium tracks
            
        for distance in range(marker_interval, int(display_range_max), marker_interval):
            # Add vertical line for distance marker
            distance_line = pg.InfiniteLine(
                angle=90, 
                movable=False, 
                pen=pg.mkPen('gray', width=1, style=Qt.DotLine),
                label=f"{distance}m",
                labelOpts={'position': 0.95, 'color': 'gray', 'fill': (0, 0, 0, 50)}
            )
            distance_line.setPos(distance)
            self.plot_widget.addItem(distance_line)
            self.distance_markers.append(distance_line)
            
        # Add start/finish line
        self.start_finish_line.setPos(0)
        self.start_finish_line.show()
    
    def add_stopped_section_marker(self, position, data=None):
        """Add a marker for a section where the car was stopped.
        
        Args:
            position: Distance position along track
            data: Optional dictionary with additional data about the stopped section
        """
        # Create marker to highlight stopped section
        marker = pg.InfiniteLine(
            angle=90, 
            movable=False, 
            pen=pg.mkPen('r', width=2, style=Qt.DotLine),
            label="Stopped", 
            labelOpts={'position': 0.5, 'color': 'r', 'fill': (0, 0, 0, 80)}
        )
        marker.setPos(position)
        self.plot_widget.addItem(marker)
        self.stopped_section_markers.append(marker)
    
    def _detect_stopped_sections(self, distances, speeds, min_points_stop=10, pos_tolerance=0.5):
        """Detect sections where the car appears to have stopped based on distance and speed data."""
        stopped_sections_output = []
        if not distances or len(distances) < min_points_stop:
            return stopped_sections_output

        pos_counts = {}
        point_data = {} # Store first point's data for each bin

        for i, dist in enumerate(distances):
            bin_pos = round(dist / pos_tolerance) * pos_tolerance
            pos_counts[bin_pos] = pos_counts.get(bin_pos, 0) + 1
            if bin_pos not in point_data:
                 # Store speed data for the first point encountered in this bin
                 point_data[bin_pos] = {
                     'avg_speed': speeds[i] if i < len(speeds) else 0,
                     'count': 0 # We'll update count later
                 }

        for pos, count in pos_counts.items():
            if count >= min_points_stop:
                # For the tooltip, let's calculate average speed in the stopped section
                section_data = point_data.get(pos, {'avg_speed': 0})
                section_data['count'] = count # Add the count here
                stopped_sections_output.append((pos, section_data))

        return stopped_sections_output

    def update_graph(self, lap_data, track_length, track_context=None):
        """Update the graph with new lap data using distance as X-axis."""
        try:
            # Validate lap data before processing
            is_valid, lap_data, debug_info = self.validate_telemetry_data(lap_data, 'speed')
            
            # Store debug info
            self.debug_info = debug_info
            self.debug_info['comparison_mode'] = False
            
            # Show debug info if enabled
            if self.debug_enabled:
                self.show_debug_stats()
            
            # Start with clean state - reset all plot elements
            self.comparison_mode = False
            
            # Reset plot items and state
            if self.legend:
                self.legend.clear()
                
            # Hide the comparison curve (not using it in single lap mode)
            self.speed_curve_b.hide()
            
            # Clear all additional items from the plot (except the main components)
            for item in list(self.plot_widget.items()):
                if item not in [self.speed_curve, self.speed_curve_b, self.vLine, self.hLine, self.label, self.start_finish_line, self.debug_info_text]:
                    self.plot_widget.removeItem(item)
                    
            # Clear any message text
            if hasattr(self, 'message_text') and self.message_text and self.message_text in self.plot_widget.items():
                self.plot_widget.removeItem(self.message_text)
                self.message_text = None
                
            # Clear all track markers
            self.clear_track_markers()
            
            # Check for valid data
            if not lap_data or not is_valid:
                self.speed_curve.setData([], []) # Clear main curves
                self.display_message("No Valid Lap Data")
                self.reset_view()
                return
                
            # Store track length
            self.track_length = track_length
            
            # Preprocess and resample the telemetry data
            resampled_data = self.preprocess_telemetry_data(lap_data, track_length, ['Speed'])
            if not resampled_data:
                self.speed_curve.setData([], []) # Clear main curves
                self.display_message("Failed to preprocess data")
                self.reset_view()
                return
                
            # Temporarily enable auto-range to allow programmatic updates
            self.plot_widget.plotItem.vb.enableAutoRange()
            
            # Update the plot with resampled data
            speed_values = resampled_data['Speed']
            
            # Convert to km/h if in m/s (speeds < 100 assumed to be m/s)
            if np.nanmax(speed_values) < 100:
                speed_values = speed_values * 3.6
                
            self.speed_curve.setData(resampled_data['x_m'], speed_values)
            self.speed_curve.show()
            
            # Compute Y-axis limits with margin
            y_min = 0
            y_max = np.nanmax(speed_values)
            # Ensure a reasonable minimum y_max for empty or very slow laps
            y_max = max(y_max, 120)  # At least 120 km/h for scale
            margin = 0.05 * (y_max - y_min)
            self.plot_widget.setYRange(y_min - margin, y_max + margin, padding=0)
            
            # Set X-axis range to track length
            self.plot_widget.setXRange(0, self.track_length, padding=0)
            self.plot_widget.setLabel('bottom', "Distance (m)")
            
            # Disable auto-ranging again immediately after setting ranges
            self.plot_widget.plotItem.vb.disableAutoRange()

            # Process raw data for stopped section detection
            raw_distances = []
            raw_speeds = []
            
            points = lap_data.get('points', [])
            for point in points:
                if 'LapDist' in point:
                    dist = point['LapDist']
                elif 'track_position' in point and track_length > 0:
                    dist = point['track_position'] * track_length
                else:
                    continue
                    
                speed = point.get('Speed', point.get('speed', 0))
                if isinstance(speed, (int, float)) and speed < 100:
                    speed *= 3.6  # Convert to km/h if in m/s
                
                raw_distances.append(dist)
                raw_speeds.append(speed)
                
            # Detect and add stopped section markers
            stopped_sections = self._detect_stopped_sections(raw_distances, raw_speeds)
            for pos, data in stopped_sections:
                self.add_stopped_section_marker(pos, data)

            # Add track context if provided
            self._add_track_context_markers(track_context, self.track_length)
            
            # Ensure grid is visible
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Update title for single lap view
            self.plot_widget.setTitle("Speed vs Distance")
            
            # Update grid based on track length (skip for now to prevent crashes)
            # self.update_grid()
            
        except Exception as e:
            logger.error(f"Error updating speed graph: {e}", exc_info=True)
            self.speed_curve.setData([], [])
            self.display_message("Graph Update Error")
            self.reset_view()

    def update_graph_comparison(self, lap_a_data, lap_b_data, track_length, track_context=None):
        """Update the graph to display a comparison of two laps."""
        logger.info(f"Updating speed graph with comparison data for A:{len(lap_a_data['points']) if lap_a_data else 'None'} and B:{len(lap_b_data['points']) if lap_b_data else 'None'} points")
        
        # Validate lap data (both A and B) before processing
        is_valid_a, lap_a_data, debug_info_a = self.validate_telemetry_data(lap_a_data, 'speed')
        is_valid_b, lap_b_data, debug_info_b = self.validate_telemetry_data(lap_b_data, 'speed')
        
        # Store combined debug info
        self.debug_info = {
            'lap_a': debug_info_a,
            'lap_b': debug_info_b,
            'comparison_mode': True
        }
        
        # Show debug info if enabled
        if self.debug_enabled:
            self.show_debug_stats()
            
        # Set comparison mode flag to True
        self.comparison_mode = True
        
        # --- COMPLETELY RESET PLOT STATE ---
        # Clear both curves by setting empty data arrays
        self.speed_curve.setData([], [])
        self.speed_curve_b.setData([], [])
        
        # Reset plot items and state
        if self.legend:
            self.legend.clear()
            
        # Clear all additional items from the plot that might be leftover
        for item in self.plot_widget.items():
            if item not in [self.speed_curve, self.speed_curve_b, self.vLine, self.hLine, self.label, self.start_finish_line, self.debug_info_text]:
                self.plot_widget.removeItem(item)
                
        # Clear any message text
        if hasattr(self, 'message_text') and self.message_text and self.message_text in self.plot_widget.items():
             self.plot_widget.removeItem(self.message_text)
             self.message_text = None
             
        # Clear all track markers
        self.clear_track_markers()
        # --- END COMPLETE RESET ---

        # --- Ensure curves are visible and legend exists --- 
        self.speed_curve.show()
        self.speed_curve_b.show()
        if self.legend is None:
            # Create a new legend with proper styling if it doesn't exist
            self.legend = self.plot_widget.addLegend(offset=(-20, 10), labelTextSize='10pt')
        # ------------------------------------------------

        # Store track length
        self.track_length = track_length
        
        # Initialize variable for Y-axis limits
        global_y_min, global_y_max = 0, 0  # Default for speed
        
        # Process and plot data for Lap A if valid
        if is_valid_a:
            resampled_data_a = self.preprocess_telemetry_data(lap_a_data, track_length, ['Speed'])
            if resampled_data_a:
                # Get speed values and convert to km/h if needed
                speed_values_a = resampled_data_a['Speed']
                if np.nanmax(speed_values_a) < 100:
                    speed_values_a = speed_values_a * 3.6
                
                # Update plot with resampled data
                self.speed_curve.setData(resampled_data_a['x_m'], speed_values_a)
                
                # Update global min/max values
                y_min_a = np.nanmin(speed_values_a)
                y_max_a = np.nanmax(speed_values_a)
                
                global_y_min = min(global_y_min, y_min_a)
                global_y_max = max(global_y_max, y_max_a)
                
                logger.info(f"Set Lap A speed data with {len(resampled_data_a['x_m'])} points")
            else:
                logger.warning("Failed to preprocess Lap A data")
                self.speed_curve.hide()
        else:
            logger.warning("No valid data for Lap A")
            self.speed_curve.hide()

        # Process and plot data for Lap B if valid
        if is_valid_b:
            resampled_data_b = self.preprocess_telemetry_data(lap_b_data, track_length, ['Speed'])
            if resampled_data_b:
                # Get speed values and convert to km/h if needed
                speed_values_b = resampled_data_b['Speed']
                if np.nanmax(speed_values_b) < 100:
                    speed_values_b = speed_values_b * 3.6
                
                # Update plot with resampled data
                self.speed_curve_b.setData(resampled_data_b['x_m'], speed_values_b)
                
                # Update global min/max values
                y_min_b = np.nanmin(speed_values_b)
                y_max_b = np.nanmax(speed_values_b)
                
                global_y_min = min(global_y_min, y_min_b)
                global_y_max = max(global_y_max, y_max_b)
                
                logger.info(f"Set Lap B speed data with {len(resampled_data_b['x_m'])} points")
            else:
                logger.warning("Failed to preprocess Lap B data")
                self.speed_curve_b.hide()
        else:
            logger.warning("No valid data for Lap B")
            self.speed_curve_b.hide()

        # Ensure the legend is populated AFTER setting data
        if self.legend:
            self.legend.clear()  # Make sure to clear the legend again before adding items
            if is_valid_a:
                 self.legend.addItem(self.speed_curve, "Your Speed")
            if is_valid_b:
                 self.legend.addItem(self.speed_curve_b, "Super Lap Speed")

        # Temporarily enable auto-range to allow programmatic updates
        self.plot_widget.plotItem.vb.enableAutoRange()
        
        # Ensure a reasonable minimum y_max for empty or very slow laps
        global_y_max = max(global_y_max, 120)  # At least 120 km/h for scale
        
        # Add Y-axis margin and set limits
        margin = 0.05 * (global_y_max - global_y_min)
        self.plot_widget.setYRange(global_y_min - margin, global_y_max + margin, padding=0)
        
        # Set X-axis range to track length
        self.plot_widget.setXRange(0, self.track_length, padding=0)
        self.plot_widget.setLabel('bottom', "Distance (m)")
        
        # Disable auto-ranging again immediately after setting ranges
        self.plot_widget.plotItem.vb.disableAutoRange()
        
        # Add track context markers (should be added after curves)
        self._add_track_context_markers(track_context, self.track_length)
        
        # Re-add crosshairs and labels
        if self.vLine not in self.plot_widget.items(): self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        if self.hLine not in self.plot_widget.items(): self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        if self.label not in self.plot_widget.items(): self.plot_widget.addItem(self.label, ignoreBounds=True)
        
        # Update title and ensure grid is visible
        self.plot_widget.setTitle("Speed vs Distance (Comparison)")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Update grid based on track length (skip for now to prevent crashes)
        # self.update_grid()
        
        # Force a redraw of the plot
        self.plot_widget.update()

    def show_debug_stats(self, debug_info=None):
        """Display debug information on the graph."""
        if not self.debug_enabled:
            if hasattr(self, 'debug_info_text'):
                self.debug_info_text.hide()
            return
            
        if debug_info is None:
            debug_info = self.debug_info
            
        if not debug_info:
            return
            
        # Format debug text based on comparison mode
        if debug_info.get('comparison_mode', False) and 'lap_a' in debug_info and 'lap_b' in debug_info:
            # Comparison mode
            debug_a = debug_info['lap_a']
            debug_b = debug_info['lap_b']
            
            debug_text = f"Debug Info (Speed):\n"
            debug_text += f"Lap A: {debug_a['valid_points']}/{debug_a['original_points']} pts ({debug_a['status']})"
            if debug_a.get('repairs_made', 0) > 0:
                debug_text += f", {debug_a['repairs_made']} repaired"
            if debug_a.get('data_gaps', []):
                debug_text += f", {len(debug_a['data_gaps'])} gaps"
                
            debug_text += f"\nLap B: {debug_b['valid_points']}/{debug_b['original_points']} pts ({debug_b['status']})"
            if debug_b.get('repairs_made', 0) > 0:
                debug_text += f", {debug_b['repairs_made']} repaired"
            if debug_b.get('data_gaps', []):
                debug_text += f", {len(debug_b['data_gaps'])} gaps"
        else:
            # Single lap mode
            debug_text = f"Debug Info (Speed):\n"
            debug_text += f"Status: {debug_info.get('status', 'unknown')}\n"
            debug_text += f"Points: {debug_info.get('valid_points', 0)}/{debug_info.get('original_points', 0)}"
            
            # Add info about repairs
            if debug_info.get('repairs_made', 0) > 0:
                debug_text += f", {debug_info['repairs_made']} repaired"
                
            # Add info about data gaps
            if debug_info.get('data_gaps', []):
                debug_text += f"\nGaps: {len(debug_info['data_gaps'])}"
                
            # Add info about missing keys
            if debug_info.get('missing_keys', []):
                debug_text += f"\nMissing: {', '.join(debug_info['missing_keys'])}"
        
        # Update and show debug text
        self.debug_info_text.setHtml(f"<div style='background-color: rgba(0, 0, 0, 120); padding: 4px; font-size: 9pt;'>{debug_text}</div>")
        self.debug_info_text.show()

    def display_message(self, message):
        """Display a message on the graph when no data is available.
        
        Args:
            message: Message to display
        """
        # Clear any existing data
        self.speed_curve.setData([], [])
        
        # Add a text item to the center of the plot
        if not hasattr(self, 'message_text') or self.message_text is None:
            self.message_text = pg.TextItem(
                text=message,
                color=(200, 200, 200),
                anchor=(0.5, 0.5),
                fill=(0, 0, 0, 100)
            )
            self.plot_widget.addItem(self.message_text)
        else:
            self.message_text.setText(message)
            self.message_text.setVisible(True)
        
        # Position text in center
        view_range = self.plot_widget.viewRange()
        x_center = (view_range[0][0] + view_range[0][1]) / 2
        y_center = (view_range[1][0] + view_range[1][1]) / 2
        self.message_text.setPos(x_center, y_center)
        
        # Make sure the plot still has a reasonable display range
        self.reset_view() 

    def add_distance_grid(self):
        """Add distance grid lines at specific intervals."""
        # Create container for grid lines
        self.grid_lines = []
        # We'll draw the actual grid lines when we know the track length

    def update_grid(self):
        """Update grid lines based on track length."""
        # Clear existing grid lines
        for line in self.grid_lines:
            if line in self.plot_widget.items():
                self.plot_widget.removeItem(line)
        self.grid_lines = []
        
        # Skip if no track length available
        if not self.track_length or self.track_length <= 0:
            return
            
        # Calculate appropriate interval based on track length
        if self.track_length > 5000:
            grid_interval = 1000  # 1km for long tracks
        elif self.track_length > 2000:
            grid_interval = 500   # 500m for medium tracks
        else:
            grid_interval = 250   # 250m for short tracks
            
        # Create grid lines at regular intervals
        for pos in range(0, int(self.track_length) + grid_interval, grid_interval):
            if pos == 0:  # Skip the zero position as it's the axis
                continue
                
            line = pg.InfiniteLine(
                pos=pos, 
                angle=90, 
                pen=pg.mkPen((80, 80, 80), width=1, style=Qt.DashLine),
                movable=False
            )
            self.plot_widget.addItem(line)
            self.grid_lines.append(line) 