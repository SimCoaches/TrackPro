import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPointF
from PyQt6.QtGui import QMouseEvent
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

# Try to import pyqtgraph, but don't fail if it's not available
try:
    import pyqtgraph as pg
    PYTQTGRAPH_AVAILABLE = True
except ImportError:
    PYTQTGRAPH_AVAILABLE = False
    pg = None

class HandbrakeCurveEditor:
    """Interactive curve editor for handbrake response curves."""
    
    def __init__(self, parent=None):
        if not PYTQTGRAPH_AVAILABLE:
            raise ImportError("pyqtgraph is required for the curve editor")
        
        self.plot_widget = pg.PlotWidget(parent)
        self.dragging = False
        self.dragging_point = None
        self.curve_x = [0, 25, 50, 75, 100]
        self.curve_y = [0, 25, 50, 75, 100]
        self.scatter = None
        self.curve_line = None
        self.on_curve_changed = None
        self.pg = pg
        
        # Override mouse events
        self.plot_widget.mousePressEvent = self.mousePressEvent
        self.plot_widget.mouseMoveEvent = self.mouseMoveEvent
        self.plot_widget.mouseReleaseEvent = self.mouseReleaseEvent
        
        # Setup the plot
        self.setup_plot()
        
    def setup_plot(self):
        """Setup the plot widget with proper styling."""
        self.plot_widget.setLabel('left', 'Output %')
        self.plot_widget.setLabel('bottom', 'Input %')
        self.plot_widget.setTitle('Handbrake Response Curve')
        self.plot_widget.setBackground('#252525')
        self.plot_widget.getAxis('left').setPen('#fefefe')
        self.plot_widget.getAxis('bottom').setPen('#fefefe')
        self.plot_widget.getAxis('left').setTextPen('#fefefe')
        self.plot_widget.getAxis('bottom').setTextPen('#fefefe')
        
        # Set axis ranges
        self.plot_widget.setXRange(0, 100)
        self.plot_widget.setYRange(0, 100)
        
        # Add grid
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Disable chart dragging/zooming but keep scatter points interactive
        self.plot_widget.setMouseEnabled(x=False, y=False)
        
        # Enable mouse tracking for better drag detection
        self.plot_widget.setMouseTracking(True)
        
    def set_curve_data(self, x, y, on_curve_changed=None):
        """Set the curve data and callback for when curve changes."""
        self.curve_x = list(x)
        self.curve_y = list(y)
        self.on_curve_changed = on_curve_changed
        
        # Clear existing items
        self.plot_widget.clear()
        
        # Plot the line
        self.curve_line = self.plot_widget.plot(self.curve_x, self.curve_y, 
                                               pen=self.pg.mkPen('#e74c3c', width=2))
        
        # Create scatter points
        self.scatter = self.pg.ScatterPlotItem(x=self.curve_x, y=self.curve_y,
                                          symbol='o', symbolBrush='#00ff00', symbolSize=12,
                                          pen=self.pg.mkPen('#00ff00', width=2))
        self.plot_widget.addItem(self.scatter)
        
    def find_nearest_point(self, mouse_x, mouse_y):
        """Find the nearest control point to the mouse position."""
        if not self.curve_x:
            return -1
            
        min_distance = float('inf')
        nearest_point = -1
        
        for i, (x, y) in enumerate(zip(self.curve_x, self.curve_y)):
            distance = ((mouse_x - x) ** 2 + (mouse_y - y) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_point = i
        
        # Use a threshold of 8 units (8% of chart size)
        threshold = 8.0
        if min_distance <= threshold:
            return nearest_point
        return -1
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Get mouse position in chart coordinates
            pos = event.pos()
            view_box = self.plot_widget.getViewBox()
            pos_f = QPointF(pos.x(), pos.y())
            chart_pos = view_box.mapSceneToView(pos_f)
            
            # Find nearest point
            nearest_point = self.find_nearest_point(chart_pos.x(), chart_pos.y())
            
            if nearest_point >= 0:
                self.dragging = True
                self.dragging_point = nearest_point
                event.accept()
                return
                
        # If we didn't handle it, pass to parent
        super(self.plot_widget.__class__, self.plot_widget).mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.dragging and self.dragging_point is not None:
            # Get mouse position in chart coordinates
            pos = event.pos()
            view_box = self.plot_widget.getViewBox()
            pos_f = QPointF(pos.x(), pos.y())
            chart_pos = view_box.mapSceneToView(pos_f)
            
            # Constrain to chart bounds (0-100)
            x = max(0, min(100, chart_pos.x()))
            y = max(0, min(100, chart_pos.y()))
            
            # Apply constraints to prevent crossing over other dots
            constrained_x, constrained_y = self.constrain_point_position(self.dragging_point, x, y)
            
            # Update the point directly using the dragging_point index
            if self.dragging_point < len(self.curve_x):
                self.curve_x[self.dragging_point] = constrained_x
                self.curve_y[self.dragging_point] = constrained_y
                
                # Update the scatter plot
                self.scatter.setData(self.curve_x, self.curve_y)
                
                # Update the line
                self.curve_line.setData(self.curve_x, self.curve_y)
                
                # Call callback if provided
                if self.on_curve_changed:
                    self.on_curve_changed(self.curve_x, self.curve_y)
            
            event.accept()
            return
            
        # If we didn't handle it, pass to parent
        super(self.plot_widget.__class__, self.plot_widget).mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if self.dragging:
            self.dragging = False
            self.dragging_point = None
            event.accept()
            return
            
        # If we didn't handle it, pass to parent
        super(self.plot_widget.__class__, self.plot_widget).mouseReleaseEvent(event)
        
    def constrain_point_position(self, point_index, x, y):
        """Constrain a point's position to prevent crossing over other points."""
        if len(self.curve_x) < 2:
            return x, y
            
        # Special constraints for first and last points
        if point_index == 0:
            # First point must stay at x=0
            return 0, max(0, min(100, y))
        elif point_index == len(self.curve_x) - 1:
            # Last point must stay at x=100
            return 100, max(0, min(100, y))
        
        # Get the x-coordinates of all other points
        other_x_coords = [self.curve_x[i] for i in range(len(self.curve_x)) if i != point_index]
        
        # Find the closest points on either side
        left_points = [cx for cx in other_x_coords if cx < x]
        right_points = [cx for cx in other_x_coords if cx > x]
        
        # Constrain x position
        min_x = max(left_points) if left_points else 0
        max_x = min(right_points) if right_points else 100
        
        # Apply constraints with a small buffer
        buffer = 2.0  # 2% buffer to prevent overlap
        constrained_x = max(min_x + buffer, min(max_x - buffer, x))
        
        # Constrain y to reasonable bounds
        constrained_y = max(0, min(100, y))
        
        return constrained_x, constrained_y

class HandbrakeCurveManagerWidget(QWidget):
    curve_changed = pyqtSignal(str)  # curve_name
    curve_edited = pyqtSignal(list, list)  # x_points, y_points
    
    def __init__(self, handbrake_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.handbrake_name = handbrake_name
        self.global_managers = global_managers
        
        self.current_curve = "Linear (Default)"
        self.available_curves = [
            "Linear (Default)",
            "Progressive", 
            "Aggressive",
            "Smooth"
        ]
        
        self.curve_editor = None
        self.curve_combo = None
        self.curve_description = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Curve selection group
        group = QGroupBox("Response Curve")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout()
        
        # Curve selection
        curve_layout = QHBoxLayout()
        
        curve_label = QLabel("Curve Type:")
        curve_label.setMinimumWidth(80)
        curve_label.setStyleSheet("color: #fefefe; font-size: 11px;")
        
        self.curve_combo = QComboBox()
        self.curve_combo.addItems(self.available_curves)
        self.curve_combo.setCurrentText(self.current_curve)
        self.curve_combo.currentTextChanged.connect(self.on_curve_changed)
        self.curve_combo.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 3px;
                color: #fefefe;
                font-size: 11px;
                padding: 4px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #fefefe;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #252525;
                border: 1px solid #444444;
                color: #fefefe;
                selection-background-color: #e74c3c;
            }
        """)
        
        save_btn = QPushButton("Save Curve")
        save_btn.setMaximumWidth(80)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.save_curve)
        
        curve_layout.addWidget(curve_label)
        curve_layout.addWidget(self.curve_combo)
        curve_layout.addWidget(save_btn)
        curve_layout.addStretch()
        
        # Curve description
        self.curve_description = QLabel(self.get_curve_description(self.current_curve))
        self.curve_description.setStyleSheet("""
            QLabel {
                color: #bdc3c7;
                font-size: 10px;
                font-style: italic;
                padding: 2px;
            }
        """)
        
        group_layout.addLayout(curve_layout)
        group_layout.addWidget(self.curve_description)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        # Curve editor group
        self.create_curve_editor(layout)
    
    def create_curve_editor(self, parent_layout):
        """Create the interactive curve editor."""
        editor_group = QGroupBox("Curve Editor")
        editor_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        editor_layout = QVBoxLayout()
        
        # Try to create the interactive chart
        try:
            if PYTQTGRAPH_AVAILABLE:
                self.curve_editor = HandbrakeCurveEditor()
                self.curve_editor.set_curve_data(
                    [0, 25, 50, 75, 100], 
                    [0, 25, 50, 75, 100],
                    self.on_curve_points_changed
                )
                editor_layout.addWidget(self.curve_editor.plot_widget)
                logger.info(f"Created interactive curve editor for {self.handbrake_name}")
            else:
                chart_placeholder = QLabel("Curve editor not available - pyqtgraph not installed")
                chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chart_placeholder.setMinimumHeight(200)
                chart_placeholder.setStyleSheet("color: #fefefe; font-size: 11px;")
                editor_layout.addWidget(chart_placeholder)
                logger.warning(f"No charting library available for {self.handbrake_name}")
        except Exception as e:
            chart_placeholder = QLabel(f"Curve editor error: {str(e)}")
            chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_placeholder.setMinimumHeight(200)
            chart_placeholder.setStyleSheet("color: #fefefe; font-size: 11px;")
            editor_layout.addWidget(chart_placeholder)
            logger.error(f"Failed to create curve editor: {e}")
        
        editor_group.setLayout(editor_layout)
        parent_layout.addWidget(editor_group)
    
    def on_curve_points_changed(self, x_points, y_points):
        """Handle curve point changes from the editor."""
        logger.debug(f"Curve points changed: {x_points}, {y_points}")
        self.curve_edited.emit(x_points, y_points)
    
    def get_curve_description(self, curve_name: str) -> str:
        """Get description for the selected curve."""
        descriptions = {
            "Linear (Default)": "Direct 1:1 response - no modification",
            "Progressive": "Gentle start, stronger at the end",
            "Aggressive": "Strong start, levels off quickly", 
            "Smooth": "Smooth progressive response curve"
        }
        return descriptions.get(curve_name, "Custom response curve")
    
    def get_curve_points(self, curve_name: str):
        """Get the points for a specific curve."""
        curve_definitions = {
            "Linear (Default)": ([0, 25, 50, 75, 100], [0, 25, 50, 75, 100]),
            "Progressive": ([0, 25, 50, 75, 100], [0, 15, 35, 65, 100]),
            "Aggressive": ([0, 25, 50, 75, 100], [0, 40, 70, 90, 100]),
            "Smooth": ([0, 20, 40, 60, 80, 100], [0, 10, 25, 45, 70, 100])
        }
        return curve_definitions.get(curve_name, curve_definitions["Linear (Default)"])
    
    def on_curve_changed(self, curve_name: str):
        """Handle curve selection change."""
        self.current_curve = curve_name
        self.curve_description.setText(self.get_curve_description(curve_name))
        
        # Update the curve editor with new curve points
        if self.curve_editor:
            x_points, y_points = self.get_curve_points(curve_name)
            self.curve_editor.set_curve_data(x_points, y_points, self.on_curve_points_changed)
        
        self.curve_changed.emit(curve_name)
        logger.info(f"Handbrake curve changed to: {curve_name}")
    
    def save_curve(self):
        """Save the current curve settings."""
        # This would save the curve to the calibration system
        logger.info(f"Saving handbrake curve: {self.current_curve}")
        
        # Emit signal to notify parent
        self.curve_changed.emit(self.current_curve)
    
    def set_curve(self, curve_name: str):
        """Set the curve from external source."""
        if curve_name in self.available_curves:
            self.current_curve = curve_name
            self.curve_combo.blockSignals(True)
            self.curve_combo.setCurrentText(curve_name)
            self.curve_combo.blockSignals(False)
            self.curve_description.setText(self.get_curve_description(curve_name))
            
            # Update the curve editor
            if self.curve_editor:
                x_points, y_points = self.get_curve_points(curve_name)
                self.curve_editor.set_curve_data(x_points, y_points, self.on_curve_points_changed)
    
    def get_current_curve(self) -> str:
        """Get the currently selected curve."""
        return self.current_curve
    
    def get_current_curve_points(self):
        """Get the current curve points from the editor."""
        if self.curve_editor:
            return self.curve_editor.curve_x, self.curve_editor.curve_y
        return [0, 25, 50, 75, 100], [0, 25, 50, 75, 100]
    
    def add_custom_curve(self, curve_name: str):
        """Add a custom curve to the available options."""
        if curve_name not in self.available_curves:
            self.available_curves.append(curve_name)
            self.curve_combo.addItem(curve_name)
            logger.info(f"Added custom handbrake curve: {curve_name}")
    
    def remove_curve(self, curve_name: str):
        """Remove a curve from available options."""
        if curve_name in self.available_curves and curve_name != "Linear (Default)":
            self.available_curves.remove(curve_name)
            index = self.curve_combo.findText(curve_name)
            if index >= 0:
                self.curve_combo.removeItem(index)
            
            # If we removed the current curve, switch to linear
            if self.current_curve == curve_name:
                self.set_curve("Linear (Default)")
            
            logger.info(f"Removed handbrake curve: {curve_name}")
    
    def get_curve_settings(self):
        """Get current curve settings."""
        return {
            'curve_type': self.current_curve,
            'available_curves': self.available_curves.copy(),
            'curve_points': self.get_current_curve_points()
        }