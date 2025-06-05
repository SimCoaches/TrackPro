"""
Threshold Braking Assist UI Panel

Provides controls for enabling/configuring the threshold braking assist system.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QCheckBox, QSlider, QLabel, QPushButton, QTextEdit,
                           QProgressBar, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import logging

logger = logging.getLogger(__name__)

class ThresholdAssistPanel(QWidget):
    """UI panel for threshold braking assist controls."""
    
    # Signals
    assist_enabled_changed = pyqtSignal(bool)
    reduction_changed = pyqtSignal(float)
    learning_reset = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_instance = None  # Will be set by main app
        self.setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(100)  # Update every 100ms
        
        logger.info("Threshold Assist Panel initialized")
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Threshold Braking Assist")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #268bd2;
                padding: 10px;
                background-color: rgba(38, 139, 210, 0.1);
                border-radius: 8px;
                border: 2px solid rgba(38, 139, 210, 0.3);
            }
        """)
        layout.addWidget(title)
        
        # Main controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QGridLayout(controls_group)
        
        # Enable/Disable checkbox
        self.enable_checkbox = QCheckBox("Enable Threshold Braking Assist")
        self.enable_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border: 2px solid #219a52;
            }
            QCheckBox::indicator:unchecked {
                background-color: #e74c3c;
                border: 2px solid #c0392b;
            }
        """)
        self.enable_checkbox.toggled.connect(self.on_enable_toggled)
        controls_layout.addWidget(self.enable_checkbox, 0, 0, 1, 2)
        
        # Reduction slider
        reduction_label = QLabel("Brake Force Reduction:")
        reduction_label.setStyleSheet("font-weight: bold;")
        controls_layout.addWidget(reduction_label, 1, 0)
        
        self.reduction_slider = QSlider(Qt.Horizontal)
        self.reduction_slider.setRange(10, 100)  # 1.0% to 10.0%
        self.reduction_slider.setValue(20)  # Default 2.0%
        self.reduction_slider.setTickPosition(QSlider.TicksBelow)
        self.reduction_slider.setTickInterval(10)
        self.reduction_slider.valueChanged.connect(self.on_reduction_changed)
        controls_layout.addWidget(self.reduction_slider, 1, 1)
        
        self.reduction_value_label = QLabel("2.0%")
        self.reduction_value_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #268bd2;
                background-color: rgba(38, 139, 210, 0.1);
                padding: 5px 10px;
                border-radius: 4px;
                min-width: 50px;
            }
        """)
        self.reduction_value_label.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(self.reduction_value_label, 1, 2)
        
        # Reset learning button
        self.reset_button = QPushButton("Reset Learning Data")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
        """)
        self.reset_button.clicked.connect(self.on_reset_learning)
        controls_layout.addWidget(self.reset_button, 2, 0, 1, 3)
        
        layout.addWidget(controls_group)
        
        # Status group
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(120)
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        status_layout.addWidget(self.status_text)
        
        # Learning progress
        progress_layout = QHBoxLayout()
        
        progress_label = QLabel("Learning Progress:")
        progress_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(progress_label)
        
        self.learning_progress = QProgressBar()
        self.learning_progress.setRange(0, 100)
        self.learning_progress.setValue(0)
        self.learning_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 8px;
                text-align: center;
                background-color: #2c2c2c;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #27ae60, stop:1 #2ecc71);
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.learning_progress)
        
        status_layout.addLayout(progress_layout)
        layout.addWidget(status_group)
        
        # Activity indicator
        activity_group = QGroupBox("Real-time Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_label = QLabel("Monitoring brake input...")
        self.activity_label.setAlignment(Qt.AlignCenter)
        self.activity_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #34495e;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        activity_layout.addWidget(self.activity_label)
        
        layout.addWidget(activity_group)
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def set_app_instance(self, app_instance):
        """Set reference to the main application instance."""
        self.app_instance = app_instance
        logger.info("App instance set for threshold assist panel")
    
    def on_enable_toggled(self, checked):
        """Handle enable/disable toggle."""
        if self.app_instance:
            self.app_instance.enable_threshold_assist(checked)
        self.assist_enabled_changed.emit(checked)
        
        status = "ENABLED" if checked else "DISABLED"
        color = "#27ae60" if checked else "#e74c3c"
        self.activity_label.setText(f"Threshold Assist {status}")
        self.activity_label.setStyleSheet(f"""
            QLabel {{
                padding: 10px;
                background-color: {color};
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }}
        """)
    
    def on_reduction_changed(self, value):
        """Handle reduction percentage change."""
        percentage = value / 10.0  # Convert to decimal percentage
        self.reduction_value_label.setText(f"{percentage:.1f}%")
        
        if self.app_instance:
            self.app_instance.set_threshold_reduction(percentage)
        self.reduction_changed.emit(percentage)
    
    def on_reset_learning(self):
        """Handle reset learning button click."""
        if self.app_instance:
            self.app_instance.reset_threshold_learning()
        self.learning_reset.emit()
        
        # Show feedback
        self.status_text.append("🔄 Learning data reset")
        self.learning_progress.setValue(0)
    
    def update_status(self):
        """Update the status display."""
        if not self.app_instance:
            return
        
        try:
            status = self.app_instance.get_threshold_assist_status()
            
            # Update learning progress
            confidence = status.get('confidence', 0.0)
            progress = int(confidence * 100)
            self.learning_progress.setValue(progress)
            
            # Update status text (limit to last 10 lines)
            current_lines = self.status_text.toPlainText().split('\n')
            if len(current_lines) > 10:
                # Keep only the last 9 lines and add new one
                self.status_text.clear()
                for line in current_lines[-9:]:
                    self.status_text.append(line)
            
            # Add current status if significant change
            if hasattr(self, '_last_status') and self._last_status != status:
                if status.get('enabled'):
                    context = status.get('current_context', 'Unknown')
                    learning = "Learning" if status.get('learning_mode') else "Active"
                    threshold = status.get('optimal_threshold', 0.0)
                    detections = status.get('detections', 0)
                    
                    self.status_text.append(
                        f"📊 {context} | {learning} | "
                        f"Threshold: {threshold:.3f} | "
                        f"Detections: {detections}"
                    )
                
                self._last_status = status.copy()
                
                # Auto-scroll to bottom
                scrollbar = self.status_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        
        except Exception as e:
            logger.debug(f"Error updating threshold assist status: {e}")
    
    def show_assist_activity(self, original_value, assisted_value):
        """Show real-time assist activity."""
        if assisted_value != original_value:
            reduction = (original_value - assisted_value) / original_value * 100
            self.activity_label.setText(f"🎯 ASSIST ACTIVE: {reduction:.1f}% reduction")
            self.activity_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #e67e22;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
            """)
        else:
            self.activity_label.setText("✅ Normal braking")
            self.activity_label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #27ae60;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                }
            """)
    
    def closeEvent(self, event):
        """Clean up when panel is closed."""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        super().closeEvent(event) 