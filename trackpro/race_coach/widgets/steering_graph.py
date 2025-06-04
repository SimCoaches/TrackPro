from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import math
import logging
from .graph_base import GraphBase

logger = logging.getLogger(__name__)

class SteeringGraphWidget(GraphBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#161b22')  # Modern dark background to match new design
        self.plot_widget.setTitle("Steering vs Distance")
        self.plot_widget.setLabel('bottom', "Distance (m)")
        
        # Configure Y-Axis for steering (-100% to 100%) with better styling
        left_axis = self.plot_widget.getAxis('left')
        left_axis.setLabel("Steering (%)", color='#e6edf3')
        left_axis.setTextPen('#e6edf3')
        left_axis.setPen('#30363d')
        left_axis.setTicks([[(-1.0, '-100'), (-0.75, '-75'), (-0.5, '-50'), (-0.25, '-25'), 
                             (0, '0'), 
                             (0.25, '25'), (0.5, '50'), (0.75, '75'), (1.0, '100')]])
        
        # Configure X-axis with better styling
        bottom_axis = self.plot_widget.getAxis('bottom')
        bottom_axis.setTextPen('#e6edf3')
        bottom_axis.setPen('#30363d')
        
        # Style the plot title
        title_item = self.plot_widget.plotItem.titleLabel
        title_item.setAttr('color', '#a78bfa')
        
        # Show grid lines for both axes with modern styling
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        
        # Set custom grid for x-axis at intervals
        self.add_distance_grid()
        
        # Disable mouse interaction
        self.plot_widget.plotItem.vb.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.plotItem.vb.disableAutoRange()
        
        # Create a modern legend in the top-right corner
        self.legend = self.plot_widget.addLegend(offset=(-20, 10), labelTextSize='10pt', 
                                                 brush=(22, 27, 34, 180), 
                                                 pen='#30363d')
        
        # Add horizontal line at 0 with better styling
        self.zero_line = pg.InfiniteLine(angle=0, pos=0, pen=pg.mkPen('#6e7681', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.zero_line)
        
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
        
        # Store track markers
        self.track_markers = []
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
        
        # Connect mouse movement to crosshair update
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        
        # Initialize grid lines list for custom grid functionality
        self.grid_lines = []
        
        # Set up the layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)
        
        # Initialize plot items with modern colors matching the new design
        self.steering_curve = self.plot_widget.plot(pen=pg.mkPen('#ff6b6b', width=2.5), name="Lap A Steering", autoDownsample=False, clipToView=False)
        self.steering_curve_b = self.plot_widget.plot(pen=pg.mkPen('#4ecdc4', width=2.5, style=Qt.SolidLine), name="Lap B Steering", autoDownsample=False, clipToView=False)
        
        # Initially hide comparison curve
        self.steering_curve_b.hide()
        
        # Initialize empty plot items list (no longer used directly for curves)
        self.plot_items = []
        
        # Store message text item reference
        self.message_text = None
        
        self.comparison_mode = False # Initialize comparison mode
        
        self.reset_view()
    
    def mouseMoved(self, evt):
        """Handle mouse movement to update crosshairs and tooltip."""
        try:
            # Convert tuple to QPointF if needed (happens with SignalProxy)
            if isinstance(evt, tuple):
                from PyQt5.QtCore import QPointF
                if len(evt) >= 2:
                    pos = QPointF(evt[0], evt[1])
                elif len(evt) == 1:
                    pos = evt[0]
                else:
                    return  # Invalid tuple, skip this event
            else:
                pos = evt
                
            if self.plot_widget.sceneBoundingRect().contains(pos):
                mousePoint = self.plot_widget.plotItem.vb.mapSceneToView(pos)
                x, y = mousePoint.x(), mousePoint.y()
                
                # Update crosshair positions
                self.vLine.setPos(x)
                self.hLine.setPos(y)
                
                # Find the actual steering values at the cursor position
                steering_value_a = None
                steering_value_b = None
                distance = x
                
                # Find the closest data point for Lap A
                if self.steering_curve.xData is not None and len(self.steering_curve.xData) > 0:
                    # Find the closest x point to the cursor
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(self.steering_curve.xData):
                        dist = abs(x_val - x)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0 and closest_idx < len(self.steering_curve.yData):
                        # Get actual steering value from the data
                        steering_value_a = self.steering_curve.yData[closest_idx] * 100  # Convert to percentage
                
                # In comparison mode, also find the closest data point for Lap B
                if self.comparison_mode and self.steering_curve_b.xData is not None and len(self.steering_curve_b.xData) > 0:
                    # Find the closest x point to the cursor
                    closest_idx = -1
                    min_distance = float('inf')
                    
                    for i, x_val in enumerate(self.steering_curve_b.xData):
                        dist = abs(x_val - x)
                        if dist < min_distance:
                            min_distance = dist
                            closest_idx = i
                    
                    if closest_idx >= 0 and closest_idx < len(self.steering_curve_b.yData):
                        # Get actual steering value from the data
                        steering_value_b = self.steering_curve_b.yData[closest_idx] * 100  # Convert to percentage
                
                # Format tooltip text with steering direction and the actual values
                if steering_value_a is not None:
                    # Basic tooltip for single lap
                    if not self.comparison_mode or steering_value_b is None:
                        direction_a = "Right" if steering_value_a > 0 else "Left"
                        if abs(steering_value_a) < 1.0:  # Close to zero
                            direction_a = "Center"
                            
                        tooltip = f"""
                            <div style='background-color: rgba(0, 0, 0, 180); padding: 5px;'>
                                <span style='color: white;'>Dist: {distance:.1f}m</span><br>
                                <span style='color: #00AAFF;'>Steering {direction_a}: {abs(steering_value_a):.0f}%</span>
                            </div>
                        """
                    else:
                        # Enhanced tooltip for comparison
                        direction_a = "Right" if steering_value_a > 0 else "Left"
                        if abs(steering_value_a) < 1.0:
                            direction_a = "Center"
                            
                        direction_b = "Right" if steering_value_b > 0 else "Left"
                        if abs(steering_value_b) < 1.0:
                            direction_b = "Center"
                        
                        tooltip = f"""
                            <div style='background-color: rgba(0, 0, 0, 180); padding: 5px;'>
                                <span style='color: white;'>Dist: {distance:.1f}m</span><br>
                                <span style='color: #00AAFF;'>Lap A: {direction_a} {abs(steering_value_a):.0f}%</span><br>
                                <span style='color: #88CCFF;'>Lap B: {direction_b} {abs(steering_value_b):.0f}%</span>
                            </div>
                        """
                    
                    self.label.setHtml(tooltip)
                    self.label.setPos(x, -0.9)  # Position tooltip at top of graph
        except Exception as e:
            # Silently handle any mouse movement errors to prevent console spam
            pass
    
    def reset_view(self):
        """Reset the view to show the entire lap from start to finish."""
        try:
            # Temporarily enable auto-ranging
            self.plot_widget.plotItem.vb.enableAutoRange()

            # Set FIXED Y range for steering (-100% to 100%) - NO MORE AUTO-RANGING
            self.plot_widget.setYRange(-1, 1, padding=0.02)
            
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
        # Remove all corner markers
        for marker in self.track_markers:
            self.plot_widget.removeItem(marker)
        self.track_markers = []
    
    def add_corner_marker(self, position, corner_number):
        """Add a corner marker at the specified position."""
        # Create corner marker as a vertical line with label
        corner_marker = pg.InfiniteLine(
            angle=90, 
            movable=False,
            pen=pg.mkPen('c', width=1, style=Qt.DotLine),
            label=f"C{corner_number}", 
            labelOpts={'position': 0.9, 'color': 'c', 'fill': (0, 0, 0, 100)}
        )
        corner_marker.setPos(position)
        self.plot_widget.addItem(corner_marker, ignoreBounds=True)
        self.track_markers.append(corner_marker)
    
    def add_distance_marker(self, position, label=None):
        """Add a distance marker at the specified position."""
        # If no label provided, format position as distance
        if label is None:
            label = f"{int(position)}m"

        # Create distance marker as a vertical line with label
        distance_marker = pg.InfiniteLine(
            angle=90, 
            movable=False,
            pen=pg.mkPen('w', width=1, style=Qt.DotLine),
            label=label, 
            labelOpts={'position': 0.05, 'color': 'w', 'fill': (0, 0, 0, 100)}
        )
        distance_marker.setPos(position)
        self.plot_widget.addItem(distance_marker, ignoreBounds=True)
        self.track_markers.append(distance_marker)
    
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

    def update_graph(self, lap_data, track_length, track_context=None):
        """Update the graph with new lap data using distance as X-axis."""
        try:
            # Validate lap data before processing
            is_valid, lap_data, debug_info = self.validate_telemetry_data(lap_data, 'steering')
            
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
            self.steering_curve_b.hide()
            
            # Clear all additional items from the plot (except the main components)
            for item in list(self.plot_widget.items()):
                if item not in [self.steering_curve, self.steering_curve_b, self.vLine, self.hLine, self.label, self.zero_line, self.debug_info_text]:
                    self.plot_widget.removeItem(item)
                    
            # Clear any message text
            if hasattr(self, 'message_text') and self.message_text and self.message_text in self.plot_widget.items():
                self.plot_widget.removeItem(self.message_text)
                self.message_text = None
                
            # Clear all track markers
            self.clear_track_markers()
            
            # Check for valid data
            if not lap_data or not is_valid:
                self.steering_curve.setData([], []) # Clear main curves
                self.display_message("No Valid Lap Data")
                self.reset_view()
                return
                
            # Store track length
            self.track_length = track_length
            
            # Preprocess and resample the telemetry data
            resampled_data = self.preprocess_telemetry_data(lap_data, track_length, ['Steering'])
            if not resampled_data:
                self.steering_curve.setData([], []) # Clear main curves
                self.display_message("Failed to preprocess data")
                self.reset_view()
                return
                
            # Temporarily enable auto-range to allow programmatic updates
            self.plot_widget.plotItem.vb.enableAutoRange()
            
            # Update the plot with resampled data
            self.steering_curve.setData(resampled_data['x_m'], resampled_data['Steering'])
            self.steering_curve.show()
            
            # Use FIXED Y-axis range for steering - consistent -100% to +100%
            # No more complex auto-ranging that causes range to jump around
            self.plot_widget.setYRange(-1, 1, padding=0.02)
            
            # Set X-axis range to track length
            self.plot_widget.setXRange(0, self.track_length, padding=0)
            self.plot_widget.setLabel('bottom', "Distance (m)")
            
            # Disable auto-ranging again immediately after setting ranges
            self.plot_widget.plotItem.vb.disableAutoRange()

            # Process raw data for stopped section detection
            raw_distances = []
            raw_steering = []
            
            points = lap_data.get('points', [])
            for point in points:
                if 'LapDist' in point:
                    dist = point['LapDist']
                elif 'track_position' in point and track_length > 0:
                    dist = point['track_position'] * track_length
                else:
                    continue
                    
                steering = point.get('Steering', point.get('steering', 0))
                raw_distances.append(dist)
                raw_steering.append(steering)
                
            # Detect and add stopped section markers
            stopped_sections = self._detect_stopped_sections(raw_distances, raw_steering)
            for pos, data in stopped_sections:
                self.add_stopped_section_marker(pos, data)

            # Add track context if provided
            self._add_track_context_markers(track_context, self.track_length)
            
            # Ensure grid is visible
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Update title for single lap view
            self.plot_widget.setTitle("Steering vs Distance")
            
            # Update grid based on track length (skip for now to prevent crashes)
            # self.update_grid()
            
        except Exception as e:
            logger.error(f"Error updating steering graph: {e}", exc_info=True)
            self.steering_curve.setData([], [])
            self.display_message("Graph Update Error")
            self.reset_view()

    def update_graph_comparison(self, lap_a_data, lap_b_data, track_length, track_context=None):
        """Update the graph to display a comparison of two laps."""
        logger.info(f"Updating steering graph with comparison data for A:{len(lap_a_data['points']) if lap_a_data else 'None'} and B:{len(lap_b_data['points']) if lap_b_data else 'None'} points")
        
        # Validate lap data (both A and B) before processing
        is_valid_a, lap_a_data, debug_info_a = self.validate_telemetry_data(lap_a_data, 'steering')
        is_valid_b, lap_b_data, debug_info_b = self.validate_telemetry_data(lap_b_data, 'steering')
        
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
        self.steering_curve.setData([], [])
        self.steering_curve_b.setData([], [])
        
        # Reset plot items and state
        if self.legend:
            self.legend.clear()
            
        # Clear all additional items from the plot that might be leftover
        for item in self.plot_widget.items():
            if item not in [self.steering_curve, self.steering_curve_b, self.vLine, self.hLine, self.label, self.zero_line, self.debug_info_text]:
                self.plot_widget.removeItem(item)
                
        # Clear any message text
        if hasattr(self, 'message_text') and self.message_text and self.message_text in self.plot_widget.items():
             self.plot_widget.removeItem(self.message_text)
             self.message_text = None
             
        # Clear all track markers
        self.clear_track_markers()
        # --- END COMPLETE RESET ---

        # --- Ensure curves are visible and legend exists --- 
        self.steering_curve.show()
        self.steering_curve_b.show()
        if self.legend is None:
             # Create a new legend with proper styling if it doesn't exist
             self.legend = self.plot_widget.addLegend(offset=(-20, 10), labelTextSize='10pt', 
                                                      brush=(22, 27, 34, 180), 
                                                      pen='#30363d')
        # ------------------------------------------------
        
        # Store track length
        self.track_length = track_length
        
        # Use FIXED Y-axis range for steering comparison - consistent -100% to +100%
        # No more complex auto-ranging that causes range to jump around
        
        # Process and plot data for Lap A if valid
        if is_valid_a:
            resampled_data_a = self.preprocess_telemetry_data(lap_a_data, track_length, ['Steering'])
            if resampled_data_a:
                # Update plot with resampled data
                self.steering_curve.setData(resampled_data_a['x_m'], resampled_data_a['Steering'])
                logger.info(f"Set Lap A steering data with {len(resampled_data_a['x_m'])} points")
            else:
                logger.warning("Failed to preprocess Lap A data")
                self.steering_curve.hide()
        else:
            logger.warning("No valid data for Lap A")
            self.steering_curve.hide()

        # Process and plot data for Lap B if valid
        if is_valid_b:
            resampled_data_b = self.preprocess_telemetry_data(lap_b_data, track_length, ['Steering'])
            if resampled_data_b:
                # Update plot with resampled data
                self.steering_curve_b.setData(resampled_data_b['x_m'], resampled_data_b['Steering'])
                logger.info(f"Set Lap B steering data with {len(resampled_data_b['x_m'])} points")
            else:
                logger.warning("Failed to preprocess Lap B data")
                self.steering_curve_b.hide()
        else:
            logger.warning("No valid data for Lap B")
            self.steering_curve_b.hide()

        # Ensure the legend is populated AFTER setting data
        if self.legend:
            self.legend.clear()  # Make sure to clear the legend again before adding items
            if is_valid_a:
                 self.legend.addItem(self.steering_curve, "Lap A Steering")
            if is_valid_b:
                 self.legend.addItem(self.steering_curve_b, "Lap B Steering")

        # Temporarily enable auto-range to allow programmatic updates
        self.plot_widget.plotItem.vb.enableAutoRange()
        
        # Use FIXED Y-axis range for steering comparison - consistent -100% to +100%
        self.plot_widget.setYRange(-1, 1, padding=0.02)
        
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
        self.plot_widget.setTitle("Steering vs Distance (Comparison)")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Update grid based on track length (skip for now to prevent crashes)
        # self.update_grid()
        
        # Force a redraw of the plot
        self.plot_widget.update()

    def update_comparison_data(self, main_data, comparison_data):
        """Update the graph with both main lap data and comparison lap data.
        
        Args:
            main_data: Dictionary with stats and points for the main lap
            comparison_data: Dictionary with stats and points for the comparison lap
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.comparison_mode = True
            
            # Clear markers only
            self.clear_track_markers()
            
            # Ensure zero line is present
            self.plot_widget.addItem(self.zero_line)
            
            # Hide message if it exists
            if self.message_text:
                self.message_text.setVisible(False)

            if not main_data and not comparison_data:
                self.steering_curve.setData([], [])
                self.steering_curve_b.setData([], [])
                self.display_message("No valid data for either lap")
                return False
            
            # Store combined max distance
            max_dist_overall = 0
            
            # --- Helper Function to Process Lap ---
            def process_lap(lap_dict):
                nonlocal max_dist_overall
                points = lap_dict.get('points', [])
                if not points: return None, None
                
                distances = []
                steering_values = []
                
                for point in points:
                    # Use 'LapDist' key for distance (meters)
                    if 'LapDist' in point:
                        dist = point['LapDist']
                    elif 'track_position' in point and track_length > 0:
                        # Convert normalized position to actual distance
                        dist = point['track_position'] * track_length
                    else: 
                        continue # Skip if missing distance
                        
                    steering = point.get('steering', point.get('SteeringWheelAngle', 0))
                    steering_norm = self.normalize_steering(steering)
                    
                    distances.append(dist)
                    steering_values.append(steering_norm)
                
                if distances:
                    max_dist_overall = max(max_dist_overall, max(distances))
                    return distances, steering_values
                else:
                    return None, None
            # --- End Helper ---

            # Process main lap (Lap A)
            main_distances, main_steerings = process_lap(main_data)
            if main_distances:
                self.steering_curve.setData(main_distances, main_steerings)
                self.steering_curve.show()
            else:
                self.steering_curve.setData([], [])

            # Process comparison lap (Lap B)
            comp_distances, comp_steerings = process_lap(comparison_data)
            if comp_distances:
                self.steering_curve_b.setData(comp_distances, comp_steerings)
                self.steering_curve_b.show()
            else:
                self.steering_curve_b.setData([], [])
                self.steering_curve_b.hide() # Hide if no data

            # Determine track length
            self.track_length = 0
            track_context = main_data.get('track_context') if main_data else (comparison_data.get('track_context') if comparison_data else None)
            if main_data and main_data.get('track_length'): self.track_length = main_data['track_length']
            elif comparison_data and comparison_data.get('track_length'): self.track_length = comparison_data['track_length']
            display_range_max = self.track_length if self.track_length > 0 else max(max_dist_overall * 1.05, 1000)

            # Update title and axis ranges
            self.plot_widget.setTitle("Steering vs Distance (Comparison)")
            self.plot_widget.setXRange(0, display_range_max, padding=0)
            self.plot_widget.setYRange(-1, 1, padding=0.02)
            
            # Add context markers
            self._add_track_context_markers(track_context, display_range_max)
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            
            # Ensure legend is updated
            if self.legend:
                self.legend.clear()
                self.legend.addItem(self.steering_curve, "Lap A Steering")
                if comp_distances: # Only add comparison item if it has data
                     self.legend.addItem(self.steering_curve_b, "Lap B Steering")

            return True

        except Exception as e:
            print(f"Error updating comparison steering graph: {e}")
            import traceback
            print(traceback.format_exc())
            self.steering_curve.setData([], [])
            self.steering_curve_b.setData([], [])
            self.display_message("Comparison Update Error")
            return False

    def _add_track_context_markers(self, track_context, display_range_max):
        """Adds context markers (corners, distance) to the steering graph."""
        if track_context:
            # No start/finish line on steering graph usually
            if 'corners' in track_context:
                for corner_pos, corner_num in track_context['corners']:
                    self.add_corner_marker(corner_pos, corner_num)
            if 'markers' in track_context:
                for marker in track_context['markers']:
                    self.add_distance_marker(marker[0], marker[1] if isinstance(marker, tuple) else None)
            elif display_range_max > 0: # Auto-generate distance markers
                 marker_interval = 500 if display_range_max <= 5000 else 1000
                 for pos in range(marker_interval, int(display_range_max), marker_interval):
                     self.add_distance_marker(pos)

    def add_stopped_section_marker(self, position, data):
        """Add a marker for sections where the car appears to have stopped."""
        if position <= 0:
            return
            
        # Create an arrow marker at the position
        marker = pg.ArrowItem(pos=(position, 0), angle=-90, headLen=15, 
                              pen=None, brush='r', tailLen=None)
        marker.stopped_data = data  # Attach data for tooltip
        self.plot_widget.addItem(marker)
        self.track_markers.append(marker)  # Add to track_markers for cleanup

    def _detect_stopped_sections(self, distances, steering_values, min_points_stop=10, pos_tolerance=0.5):
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
                # Store steering data for the first point encountered in this bin
                point_data[bin_pos] = {
                    'avg_steering': steering_values[i] if i < len(steering_values) else 0,
                    'count': 0 # We'll update count later
                }

        for pos, count in pos_counts.items():
            if count >= min_points_stop:
                # For the tooltip, add data about this stopped section
                section_data = point_data.get(pos, {'avg_steering': 0})
                section_data['count'] = count # Add the count here
                stopped_sections_output.append((pos, section_data))

        return stopped_sections_output

    def find_max_distance(self, main_points, comparison_points):
        """Find the maximum distance value from both datasets."""
        max_main = max([p.get('track_position', 0) for p in main_points]) if main_points else 0
        max_comp = max([p.get('track_position', 0) for p in comparison_points]) if comparison_points else 0
        return max(max_main, max_comp, 100)  # Default to at least 100m if both are smaller 

    def normalize_steering(self, steering_value):
        """Normalize steering input to a -1.0 to 1.0 range.
        
        Args:
            steering_value: The raw steering value
            
        Returns:
            float: Normalized steering value between -1.0 and 1.0
        """
        # Handle None or invalid values
        if steering_value is None:
            return 0.0
        
        try:
            steering_value = float(steering_value)
        except (ValueError, TypeError):
            return 0.0
        
        # If steering is already in -1.0 to 1.0 range, return it as is
        if -1.0 <= steering_value <= 1.0:
            return steering_value
        
        # If steering is in radians (typically -3pi to 3pi for 1080 degree wheels)
        if abs(steering_value) > 1.0:
            # Use a standard 1080-degree wheel assumption (3 full rotations)
            max_rotation = 3.0 * math.pi  # ~9.42 radians
            # Normalize to -1.0 to 1.0 range
            return max(-1.0, min(1.0, steering_value / max_rotation))
        
        return steering_value

    def display_message(self, message):
        """Display a message on the graph when no data is available.
        
        Args:
            message: Message to display
        """
        # Clear any existing data
        self.steering_curve.setData([], [])
        
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
            
            debug_text = f"Debug Info (Steering):\n"
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
            debug_text = f"Debug Info (Steering):\n"
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