from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import logging
from .graph_base import GraphBase

logger = logging.getLogger(__name__)

class BrakeGraphWidget(GraphBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the plot widget with anti-aliasing enabled
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#161b22')  # Modern dark background to match new design
        # Remove title and bottom label for compact layout
        
        # Enable anti-aliasing for smoother lines
        self.plot_widget.setAntialiasing(True)
        
        # Configure Y-Axis for brake (0-100%) with fixed range
        left_axis = self.plot_widget.getAxis('left')
        left_axis.setLabel("Brake (%)", color='#e6edf3')
        left_axis.setTextPen('#e6edf3')
        left_axis.setPen('#30363d')
        
        # Set fixed Y-axis range to always show 0% to 100%
        self.plot_widget.setYRange(0, 1.0, padding=0)
        
        # Hide bottom axis for compact layout
        bottom_axis = self.plot_widget.getAxis('bottom')
        bottom_axis.setStyle(showValues=False)
        bottom_axis.setPen('#30363d')
        
        # Style the plot title
        title_item = self.plot_widget.plotItem.titleLabel
        title_item.setAttr('color', '#fca5a5')
        
        # Show grid lines for both axes with modern styling
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        
        # Disable mouse interaction
        self.plot_widget.plotItem.vb.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.plotItem.vb.disableAutoRange()
        
        # Legend removed - using centralized legend instead
        self.legend = None
        
        # Create crosshair lines with modern styling
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#58a6ff', width=1, style=Qt.PenStyle.DotLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#58a6ff', width=1, style=Qt.PenStyle.DotLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        # Create text label for coordinates with modern styling
        self.label = pg.TextItem(text='', color='#e6edf3', anchor=(0, 1),
                                fill=pg.mkBrush(22, 27, 34, 180),
                                border=pg.mkPen('#30363d'))
        self.label.setPos(10, 10)
        self.plot_widget.addItem(self.label, ignoreBounds=True)
        
        # Track context elements
        self.start_finish_line = pg.InfiniteLine(
            angle=90, 
            movable=False, 
            pen=pg.mkPen('y', width=2, style=Qt.PenStyle.DashLine),
            label="Start/Finish", 
            labelOpts={'position': 0.9, 'color': 'y'}
        )
        self.plot_widget.addItem(self.start_finish_line, ignoreBounds=True)
        self.start_finish_line.hide()  # Hide initially
        
        # Container for corner and distance markers
        self.corner_markers = []
        self.distance_markers = []
        self.stopped_section_markers = []
        self.grid_lines = []  # Initialize grid_lines list
        
        # Track parameters
        self.track_length = 0
        
        # Add debug info text item
        self.debug_info_text = pg.TextItem(
            text='', 
            color=(150, 150, 150),
            anchor=(0, 0),
            fill=(20, 20, 20, 150)
        )
        self.plot_widget.addItem(self.debug_info_text, ignoreBounds=True)
        self.debug_info_text.setPos(10, 0.9)
        self.debug_info_text.hide()  # Hide initially
        
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
        # Default labels (can be overridden in update methods)
        self.label_a = "Lap A"
        self.label_b = "Lap B"
        # Use professional racing telemetry colors for better readability
        smooth_pen_a = pg.mkPen('#00BFFF', width=2.5, cosmetic=True)  # DeepSkyBlue - professional reference color
        smooth_pen_b = pg.mkPen('#FF8C00', width=2.5, style=Qt.PenStyle.SolidLine, cosmetic=True)  # DarkOrange - professional comparison color
        
        self.brake_curve = self.plot_widget.plot(pen=smooth_pen_a, autoDownsample=False, clipToView=False, antialias=True)
        self.brake_curve_b = self.plot_widget.plot(pen=smooth_pen_b, autoDownsample=False, clipToView=False, antialias=True)
        
        # Initially hide comparison curves
        self.brake_curve_b.hide()
        
        # Initialize empty data list for plot items (no longer used directly for curves)
        self.plot_items = [] 
        
        # Store message text item reference
        self.message_text = None
        
        self.comparison_mode = False # Initialize comparison mode
        
        self.reset_view()
        
    def mouseMoved(self, pos):
        """Handle mouse movement to update crosshairs and tooltip."""
        try:
            # Convert tuple to QPointF if needed (happens with SignalProxy)
            if isinstance(pos, tuple):
                from PyQt6.QtCore import QPointF
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
                
                # Find the actual brake values at the cursor position
                brake_value_a = None
                brake_value_b = None
                distance = x
                
                # Find the closest data point from Lap A
                if self.brake_curve.xData is not None and len(self.brake_curve.xData) > 0:
                    # Find the closest x point to the cursor
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(self.brake_curve.xData):
                        dist = abs(x_val - x)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0:
                        # Get actual brake value from the data
                        if closest_idx < len(self.brake_curve.yData):
                            brake_value_a = self.brake_curve.yData[closest_idx] * 100  # Convert to percentage

                # In comparison mode, also get data from Lap B
                if self.comparison_mode and self.brake_curve_b.xData is not None and len(self.brake_curve_b.xData) > 0:
                    # Find the closest x point to the cursor
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(self.brake_curve_b.xData):
                        dist = abs(x_val - x)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0:
                        # Get actual brake value from the data
                        if closest_idx < len(self.brake_curve_b.yData):
                            brake_value_b = self.brake_curve_b.yData[closest_idx] * 100  # Convert to percentage
                
                # Emit hover data to centralized hover info widget instead of showing tooltip
                if brake_value_a is not None:
                    lap_a_data = {'brake': f"{brake_value_a:.1f}%"}
                    lap_b_data = {}
                    
                    if brake_value_b is not None:
                        lap_b_data = {'brake': f"{brake_value_b:.1f}%"}
                    
                    # Emit the hover data signal
                    self.hover_data_changed.emit(distance, lap_a_data, lap_b_data)
                    
                    # Hide the individual tooltip
                    self.label.setText("")
        except Exception as e:
            # Silently handle any mouse movement errors to prevent console spam
            pass

    def reset_view(self):
        """Reset the view to show the entire lap from start to finish."""
        try:
            # Temporarily enable auto-ranging
            self.plot_widget.plotItem.vb.enableAutoRange()

            # Set fixed Y range for inputs (0-100%)
            self.plot_widget.setYRange(0, 1, padding=0)
            
            # Set X range to track length if available, otherwise use a default
            if self.track_length and self.track_length > 0:
                self.plot_widget.setXRange(0, self.track_length, padding=0)
            else:
                self.plot_widget.setXRange(0, 1000, padding=0)

            # Disable auto-ranging again
            self.plot_widget.plotItem.vb.disableAutoRange()
        except Exception as e:
            print(f"Error in reset_view: {e}")
            # Ensure auto-range is disabled on error
            try:
                self.plot_widget.plotItem.vb.disableAutoRange()
            except Exception: # Handle potential nested errors
                pass

    def clear_track_markers(self):
        """Clear all track context markers from the graph."""
        # Hide start/finish line
        self.start_finish_line.hide()
        
        # Remove all corner markers
        for marker in self.corner_markers:
            self.plot_widget.removeItem(marker)
        self.corner_markers = []
        
        # Remove all distance markers
        for marker in self.distance_markers:
            self.plot_widget.removeItem(marker)
        self.distance_markers = []
        
        # Remove all stopped section markers
        for marker in self.stopped_section_markers:
            self.plot_widget.removeItem(marker)
        self.stopped_section_markers = []
        
    def add_start_finish_line(self, position=0.0):
        """Add or update start/finish line at the specified position."""
        self.start_finish_line.setPos(position)
        self.start_finish_line.show()
        
    def add_corner_marker(self, position, corner_number):
        """Add a corner marker at the specified position."""
        # Create corner marker as a vertical line with label
        corner_marker = pg.InfiniteLine(
            angle=90, 
            movable=False,
            pen=pg.mkPen('c', width=1, style=Qt.PenStyle.DotLine),
            label=f"C{corner_number}", 
            labelOpts={'position': 0.1, 'color': 'c', 'fill': (0, 0, 0, 100)}
        )
        corner_marker.setPos(position)
        self.plot_widget.addItem(corner_marker, ignoreBounds=True)
        self.corner_markers.append(corner_marker)
        
    def add_distance_marker(self, position, label=None):
        """Add a distance marker at the specified position."""
        # If no label provided, format position as distance
        if label is None:
            label = f"{int(position)}m"
            
        # Create distance marker as a vertical line with label
        distance_marker = pg.InfiniteLine(
            angle=90, 
            movable=False,
            pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DotLine),
            label=label, 
            labelOpts={'position': 0.05, 'color': 'w', 'fill': (0, 0, 0, 100)}
        )
        distance_marker.setPos(position)
        self.plot_widget.addItem(distance_marker, ignoreBounds=True)
        self.distance_markers.append(distance_marker)
    
    def add_stopped_section_marker(self, position, data):
        """Add a marker for sections where the car appears to have stopped."""
        if position <= 0:
            return
            
        # Create an arrow marker at the position
        marker = pg.ArrowItem(pos=(position, 0), angle=-90, headLen=15, 
                             pen=None, brush='r', tailLen=None)
        marker.stopped_data = data  # Attach data for tooltip
        self.plot_widget.addItem(marker)
        self.stopped_section_markers.append(marker)
    
    def _detect_stopped_sections(self, distances, brakes, min_points_stop=10, pos_tolerance=0.5):
        """Detect sections where the car appears to have stopped based on distance data."""
        stopped_sections_output = []
        if not distances or len(distances) < min_points_stop:
            return stopped_sections_output

        pos_counts = {}
        point_data = {} # Store first point's data for each bin

        for i, dist in enumerate(distances):
            bin_pos = round(dist / pos_tolerance) * pos_tolerance
            pos_counts[bin_pos] = pos_counts.get(bin_pos, 0) + 1
            if bin_pos not in point_data:
                 # Store brake data for the first point encountered in this bin
                 point_data[bin_pos] = {
                     'avg_brake': brakes[i] if i < len(brakes) else 0,
                     'count': 0 # We'll update count later
                 }

        for pos, count in pos_counts.items():
            if count >= min_points_stop:
                # For the tooltip, let's calculate average brake in the stopped section
                section_data = point_data.get(pos, {'avg_brake': 0})
                section_data['count'] = count # Add the count here
                stopped_sections_output.append((pos, section_data))

        return stopped_sections_output

    def _add_track_context_markers(self, track_context, track_length):
        """Helper method to add all track context markers."""
        # Add start/finish line
        start_finish_pos = track_context.get('start_finish', 0) if track_context else 0
        self.add_start_finish_line(start_finish_pos)

        if track_context:
            # Add corner markers
            if 'corners' in track_context:
                for corner_pos, corner_num in track_context['corners']:
                    self.add_corner_marker(corner_pos, corner_num)

            # Add distance markers (specific ones if provided)
            if 'markers' in track_context:
                 for marker in track_context['markers']:
                     if isinstance(marker, tuple):
                         self.add_distance_marker(marker[0], marker[1])
                     else:
                         self.add_distance_marker(marker)
            # Auto-generate distance markers if none provided and track_length is known
            elif track_length > 0:
                marker_interval = 500  # Default: every 500m
                if track_length > 10000: marker_interval = 2000 # Very Long
                elif track_length > 5000: marker_interval = 1000 # Long
                elif track_length > 2000: marker_interval = 500 # Medium (already set)
                else: marker_interval = 200 # Short

                for pos in range(marker_interval, int(track_length), marker_interval):
                    # Avoid placing marker too close to start/finish
                    if abs(pos - start_finish_pos) > marker_interval * 0.5:
                         self.add_distance_marker(pos)
        # Always add a marker at the very end if track length is known
        if track_length > 0:
             self.add_distance_marker(track_length, f"{int(track_length)}m")

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
                pen=pg.mkPen((80, 80, 80), width=1, style=Qt.PenStyle.DashLine),
                movable=False
            )
            self.plot_widget.addItem(line)
            self.grid_lines.append(line)

    def update_graph(self, lap_data, track_length, track_context=None):
        """Update the graph with new lap data using distance as X-axis."""
        try:
            # Validate lap data before processing
            is_valid, lap_data, debug_info = self.validate_telemetry_data(lap_data, 'brake')
            
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
            self.brake_curve_b.hide()
            
            # Clear all additional items from the plot (except the main components)
            for item in list(self.plot_widget.items()):
                if item not in [self.brake_curve, self.brake_curve_b, self.vLine, self.hLine, self.label, self.start_finish_line, self.debug_info_text]:
                    self.plot_widget.removeItem(item)
                    
            # Clear any message text
            if hasattr(self, 'message_text') and self.message_text and self.message_text in self.plot_widget.items():
                self.plot_widget.removeItem(self.message_text)
                self.message_text = None
                
            # Clear all track markers
            self.clear_track_markers()
            
            # Check for valid data
            if not lap_data or not is_valid:
                self.brake_curve.setData([], []) # Clear main curves
                self.display_message("No Valid Lap Data")
                self.reset_view()
                return
                
            # Store track length
            self.track_length = track_length
            
            # Preprocess and resample the telemetry data
            resampled_data = self.preprocess_telemetry_data(lap_data, track_length, ['Brake'])
            if not resampled_data:
                self.brake_curve.setData([], []) # Clear main curves
                self.display_message("Failed to preprocess data")
                self.reset_view()
                return
                
            # Temporarily enable auto-range to allow programmatic updates
            self.plot_widget.plotItem.vb.enableAutoRange()
            
            # Update the plot with resampled data
            self.brake_curve.setData(resampled_data['x_m'], resampled_data['Brake'])
            self.brake_curve.show()
            
            # Keep fixed Y-axis range for brake (0% to 100%)
            
            # Set X-axis range based on actual data range, not just track length
            if len(resampled_data['x_m']) > 0:
                data_x_min = float(min(resampled_data['x_m']))
                data_x_max = float(max(resampled_data['x_m']))
                data_range = data_x_max - data_x_min
                
                # Add some padding to show the full data clearly
                x_padding = max(data_range * 0.02, 50)  # 2% padding or 50m minimum
                x_min = max(0, data_x_min - x_padding)  # Don't go below 0
                x_max = data_x_max + x_padding
                
                logger.info(f"📊 [BRAKE GRAPH] Setting X-axis range to actual data: {x_min:.1f} to {x_max:.1f}m (data range: {data_x_min:.1f} to {data_x_max:.1f}m)")
                self.plot_widget.setXRange(x_min, x_max, padding=0)
            else:
                # Fallback to track length if no data
                self.plot_widget.setXRange(0, self.track_length, padding=0)
                

            
            # Disable auto-ranging again immediately after setting ranges
            self.plot_widget.plotItem.vb.disableAutoRange()

            # Process raw data for stopped section detection
            raw_distances = []
            raw_brakes = []
            
            points = lap_data.get('points', [])
            for point in points:
                if 'LapDist' in point:
                    dist = point['LapDist']
                elif 'track_position' in point and track_length > 0:
                    dist = point['track_position'] * track_length
                else:
                    continue
                    
                brake = point.get('Brake', point.get('brake', 0))
                raw_distances.append(dist)
                raw_brakes.append(brake)
                
            # Detect and add stopped section markers
            stopped_sections = self._detect_stopped_sections(raw_distances, raw_brakes)
            for pos, data in stopped_sections:
                self.add_stopped_section_marker(pos, data)

            # Add track context if provided
            self._add_track_context_markers(track_context, self.track_length)
            
            # Ensure grid is visible
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Update title for single lap view
    
            
            # Update grid based on track length (skip for now to prevent crashes)
            # self.update_grid()
            
        except Exception as e:
            logger.error(f"Error updating brake graph: {e}", exc_info=True)
            self.brake_curve.setData([], [])
            self.display_message("Graph Update Error")
            self.reset_view()

    def set_labels(self, label_a="Lap A", label_b="Lap B"):
        """Set custom labels for the two laps being compared."""
        self.label_a = label_a
        self.label_b = label_b
        # Update curve names immediately
        self.brake_curve.opts['name'] = f"{self.label_a} Brake"
        self.brake_curve_b.opts['name'] = f"{self.label_b} Brake"

    def update_graph_comparison(self, lap_a_data, lap_b_data, track_length, track_context=None, label_a=None, label_b=None):
        """Update the graph to display a comparison of two laps."""
        logger.info(f"Updating brake graph with comparison data for A:{len(lap_a_data['points']) if lap_a_data else 'None'} and B:{len(lap_b_data['points']) if lap_b_data else 'None'} points")
        
        # Set custom labels if provided
        if label_a and label_b:
            self.set_labels(label_a, label_b)
        
        # Validate lap data (both A and B) before processing
        is_valid_a, lap_a_data, debug_info_a = self.validate_telemetry_data(lap_a_data, 'brake')
        is_valid_b, lap_b_data, debug_info_b = self.validate_telemetry_data(lap_b_data, 'brake')
        
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
        self.brake_curve.setData([], [])
        self.brake_curve_b.setData([], [])
        
        # Reset plot items and state
        if self.legend:
            self.legend.clear()
            
        # Clear all additional items from the plot that might be leftover
        for item in self.plot_widget.items():
            if item not in [self.brake_curve, self.brake_curve_b, self.vLine, self.hLine, self.label, self.start_finish_line, self.debug_info_text]:
                self.plot_widget.removeItem(item)
                
        # Clear any message text
        if hasattr(self, 'message_text') and self.message_text and self.message_text in self.plot_widget.items():
             self.plot_widget.removeItem(self.message_text)
             self.message_text = None
             
        # Clear all track markers
        self.clear_track_markers()
        # --- END COMPLETE RESET ---

        # --- Ensure curves are visible and legend exists --- 
        self.brake_curve.show()
        self.brake_curve_b.show()
        # Individual legend removed - using centralized legend instead
        # ------------------------------------------------
        
        # Store track length
        self.track_length = track_length
        
        # Initialize variable for Y-axis limits
        global_y_min, global_y_max = 0, 1.0  # Default for brake
        
        # Process and plot data for Lap A if valid
        if is_valid_a:
            resampled_data_a = self.preprocess_telemetry_data(lap_a_data, track_length, ['Brake'])
            if resampled_data_a:
                # Update plot with resampled data
                self.brake_curve.setData(resampled_data_a['x_m'], resampled_data_a['Brake'])
                
                # Update global min/max values
                y_min_a = np.nanmin(resampled_data_a['Brake'])
                y_max_a = np.nanmax(resampled_data_a['Brake'])
                
                global_y_min = min(global_y_min, y_min_a)
                global_y_max = max(global_y_max, y_max_a)
                
                logger.info(f"Set Lap A brake data with {len(resampled_data_a['x_m'])} points")
            else:
                logger.warning("Failed to preprocess Lap A data")
                self.brake_curve.hide()
        else:
            logger.warning("No valid data for Lap A")
            self.brake_curve.hide()

        # Process and plot data for Lap B if valid
        if is_valid_b:
            resampled_data_b = self.preprocess_telemetry_data(lap_b_data, track_length, ['Brake'])
            if resampled_data_b:
                # Update plot with resampled data
                self.brake_curve_b.setData(resampled_data_b['x_m'], resampled_data_b['Brake'])
                
                # Update global min/max values
                y_min_b = np.nanmin(resampled_data_b['Brake'])
                y_max_b = np.nanmax(resampled_data_b['Brake'])
                
                global_y_min = min(global_y_min, y_min_b)
                global_y_max = max(global_y_max, y_max_b)
                
                logger.info(f"Set Lap B brake data with {len(resampled_data_b['x_m'])} points")
            else:
                logger.warning("Failed to preprocess Lap B data")
                self.brake_curve_b.hide()
        else:
            logger.warning("No valid data for Lap B")
            self.brake_curve_b.hide()

        # Ensure the legend is populated AFTER setting data
        if self.legend:
            self.legend.clear()  # Make sure to clear the legend again before adding items
            if is_valid_a:
                                   self.legend.addItem(self.brake_curve, f"{self.label_a} Brake")
            if is_valid_b:
                 self.legend.addItem(self.brake_curve_b, f"{self.label_b} Brake")

        # Temporarily enable auto-range to allow programmatic updates
        self.plot_widget.plotItem.vb.enableAutoRange()
        
        # Keep fixed Y-axis range for brake (0% to 100%)
        
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
            
            debug_text = f"Debug Info (Brake):\n"
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
            debug_text = f"Debug Info (Brake):\n"
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
        self.brake_curve.setData([], [])
        
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