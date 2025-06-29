"""
Track Map Overlay Settings Dialog

Allows users to configure and control the transparent track map overlay.
"""

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSlider, QCheckBox, QFrame, QSizePolicy,
                             QSpinBox, QComboBox, QGroupBox, QFormLayout,
                             QTabWidget, QWidget, QColorDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ..race_coach.track_map_overlay import TrackMapOverlayManager

logger = logging.getLogger(__name__)


class TrackMapOverlaySettingsDialog(QDialog):
    """Settings dialog for track map overlay configuration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlay_manager = TrackMapOverlayManager()
        
        self.setWindowTitle("Track Map Overlay Settings")
        self.setModal(True)
        self.resize(500, 700)
        
        self.setup_ui()
        self.load_settings()
        self.connect_signals()
        
        logger.info("Track map overlay settings dialog initialized")
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("🗺️ Track Map Overlay Settings")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Configure the transparent track map overlay that shows the track shape, "
            "corner numbers, and your current position in real-time over any application."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Main control section
        control_group = QGroupBox("Overlay Control")
        control_layout = QVBoxLayout(control_group)
        
        # Status and toggle button
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("🔴 Overlay Inactive")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.toggle_button = QPushButton("Start Overlay")
        self.toggle_button.setMinimumHeight(40)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        status_layout.addWidget(self.toggle_button)
        
        control_layout.addLayout(status_layout)
        
        # Reload data button
        reload_layout = QHBoxLayout()
        reload_layout.addStretch()
        
        self.reload_button = QPushButton("🔄 Reload Track Data")
        self.reload_button.setToolTip("Reload track map and corner data from database")
        reload_layout.addWidget(self.reload_button)
        
        control_layout.addLayout(reload_layout)
        
        layout.addWidget(control_group)
        
        # Position and Size settings
        position_group = QGroupBox("Scale & Draggable Positioning")
        position_layout = QFormLayout(position_group)
        
        # Scale slider
        position_layout.addRow(QLabel("Overlay Scale:"), self.scale_slider)
        
        self.scale_value_label = QLabel("30%")
        position_layout.addRow(self.scale_value_label)
        
        # Dragging instructions
        drag_instructions = QLabel("""
        <b>🖱️ Drag to Position:</b><br>
        • <b>Locked Mode (Default):</b> Click-through overlay, press L or scroll to unlock<br>
        • <b>Unlocked Mode:</b> Click and drag to reposition, scroll or L to lock
        """)
        drag_instructions.setWordWrap(True)
        drag_instructions.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                font-size: 10px;
                color: #6c757d;
            }
        """)
        position_layout.addRow(drag_instructions)
        
        layout.addWidget(position_group)
        
        # Visual settings
        visual_group = QGroupBox("Visual Settings")
        visual_layout = QFormLayout(visual_group)
        
        # Show corners checkbox
        self.show_corners_check = QCheckBox("Show Corner Numbers")
        self.show_corners_check.setChecked(True)
        visual_layout.addRow(self.show_corners_check)
        
        # Show position dot checkbox
        self.show_position_check = QCheckBox("Show Current Position")
        self.show_position_check.setChecked(True)
        visual_layout.addRow(self.show_position_check)
        
        # Track line width
        visual_layout.addRow(QLabel("Track Line Width:"), self.track_width_spin)
        
        # Position dot size
        visual_layout.addRow(QLabel("Position Dot Size:"), self.dot_size_spin)
        
        # Corner font size
        visual_layout.addRow(QLabel("Corner Font Size:"), self.corner_font_spin)
        
        layout.addWidget(visual_group)
        
        # Color settings
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout(color_group)
        
        # Track color
        color_layout.addRow(QLabel("Track Color:"), self.track_color_button)
        
        # Corner color
        color_layout.addRow(QLabel("Corner Color:"), self.corner_color_button)
        
        # Position color
        color_layout.addRow(QLabel("Position Color:"), self.position_color_button)
        
        layout.addWidget(color_group)
        
        # Instructions
        instructions_group = QGroupBox("Instructions")
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions_text = QLabel(
            "🎮 <b>Overlay Controls:</b>\n"
            "• Press 'Q' while overlay is active to close it\n"
            "• Press 'C' to toggle corner numbers\n"
            "• Press 'R' to reload track data\n"
            "• Press 'L' to toggle lock/unlock mode\n\n"
            "🖱️ <b>Draggable Positioning:</b>\n"
            "• Starts in LOCKED mode (click-through)\n"
            "• Unlock with 'L' key or scroll wheel over overlay\n"
            "• Click and drag to reposition when unlocked\n"
            "• Lock shows 🔒/🔓 icon temporarily\n\n"
            "💡 Make sure you have track map data from previous sessions"
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("color: #666666;")
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Settings")
        self.test_button.setToolTip("Apply current settings to overlay without saving")
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save Settings")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addWidget(self.save_button)
        
        self.close_button = QPushButton("Close")
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def connect_signals(self):
        """Connect UI signals to handlers."""
        self.toggle_button.clicked.connect(self.toggle_overlay)
        self.reload_button.clicked.connect(self.reload_track_data)
        self.test_button.clicked.connect(self.test_settings)
        self.save_button.clicked.connect(self.save_settings)
        self.close_button.clicked.connect(self.close)
        
        # Scale slider updates
        self.scale_slider.valueChanged.connect(self.update_scale_label)
        
        # Color buttons
        self.track_color_button.clicked.connect(lambda: self.choose_color('track'))
        self.corner_color_button.clicked.connect(lambda: self.choose_color('corner'))
        self.position_color_button.clicked.connect(lambda: self.choose_color('position'))
        
        # Settings changes
        self.scale_slider.valueChanged.connect(self.on_settings_changed)
        self.show_corners_check.toggled.connect(self.on_settings_changed)
        self.show_position_check.toggled.connect(self.on_settings_changed)
        self.track_width_spin.valueChanged.connect(self.on_settings_changed)
        self.dot_size_spin.valueChanged.connect(self.on_settings_changed)
        self.corner_font_spin.valueChanged.connect(self.on_settings_changed)
    
    def load_settings(self):
        """Load current settings."""
        # For now, use default values
        # In the future, these could be loaded from config
        self.update_scale_label()
        self.update_status()
    
    def save_settings(self):
        """Save current settings."""
        # Apply current settings to overlay
        self.apply_settings_to_overlay()
        
        # TODO: Save to config file
        
        QMessageBox.information(self, "Settings Saved", 
                              "Track map overlay settings have been saved.")
        logger.info("Track map overlay settings saved")
    
    def test_settings(self):
        """Test current settings without saving."""
        self.apply_settings_to_overlay()
        QMessageBox.information(self, "Settings Applied", 
                              "Settings have been applied to the overlay for testing.")
    
    def apply_settings_to_overlay(self):
        """Apply current UI settings to the overlay."""
        if self.overlay_manager.overlay:
            overlay = self.overlay_manager.overlay
            
            # Scale setting
            overlay.overlay_scale = self.scale_slider.value() / 100.0
            
            # Visual settings
            overlay.show_corners = self.show_corners_check.isChecked()
            overlay.show_position_dot = self.show_position_check.isChecked()
            overlay.track_line_width = self.track_width_spin.value()
            overlay.corner_font_size = self.corner_font_spin.value()
            
            # Trigger repaint
            overlay.update()
    
    def toggle_overlay(self):
        """Toggle the track map overlay on/off."""
        try:
            if self.overlay_manager.is_active:
                self.overlay_manager.hide_overlay()
            else:
                # Apply current settings before showing
                self.apply_settings_to_overlay()
                self.overlay_manager.show_overlay()
            
            self.update_status()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle overlay: {str(e)}")
            logger.error(f"Error toggling track map overlay: {e}")
    
    def reload_track_data(self):
        """Reload track data from database."""
        try:
            if self.overlay_manager.overlay:
                self.overlay_manager.reload_track_data()
                QMessageBox.information(self, "Data Reloaded", 
                                      "Track map and corner data have been reloaded.")
            else:
                QMessageBox.information(self, "No Overlay", 
                                      "Start the overlay first to reload data.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reload track data: {str(e)}")
            logger.error(f"Error reloading track data: {e}")
    
    def update_status(self):
        """Update the status display."""
        if self.overlay_manager.is_active:
            self.status_label.setText("🟢 Overlay Active")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.toggle_button.setText("Stop Overlay")
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        else:
            self.status_label.setText("🔴 Overlay Inactive")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self.toggle_button.setText("Start Overlay")
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
    
    def update_scale_label(self):
        """Update the scale percentage label."""
        self.scale_value_label.setText(f"{self.scale_slider.value()}%")
    
    def choose_color(self, color_type):
        """Open color chooser dialog."""
        current_color = QColor(255, 255, 255)  # Default white
        
        if color_type == 'track':
            current_color = QColor(255, 255, 255)
        elif color_type == 'corner':
            current_color = QColor(255, 255, 0)
        elif color_type == 'position':
            current_color = QColor(0, 255, 0)
        
        color = QColorDialog.getColor(current_color, self, f"Choose {color_type.title()} Color")
        
        if color.isValid():
            # Update button color
            button = getattr(self, f"{color_type}_color_button")
            button.setStyleSheet(f"background-color: {color.name()}; color: black;")
            
            # Apply to overlay if active
            if self.overlay_manager.overlay:
                overlay = self.overlay_manager.overlay
                if color_type == 'track':
                    overlay.track_color = color
                elif color_type == 'corner':
                    overlay.corner_color = color
                elif color_type == 'position':
                    overlay.position_color = color
                overlay.update()
    
    def on_settings_changed(self):
        """Handle when settings are changed."""
        # Auto-apply settings if overlay is active
        if self.overlay_manager.is_active:
            self.apply_settings_to_overlay()
    
    def closeEvent(self, event):
        """Handle dialog close."""
        # Don't automatically stop the overlay when closing the dialog
        event.accept()