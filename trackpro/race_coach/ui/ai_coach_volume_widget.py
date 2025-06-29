"""
AI Coach Volume Control Widget

Provides a clean volume slider for adjusting AI coach audio levels.
"""

import logging
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                            QSlider, QPushButton, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

logger = logging.getLogger(__name__)

class AICoachVolumeWidget(QWidget):
    """Simple, clean volume control widget for AI coach audio."""
    
    volume_changed = pyqtSignal(float)  # Emitted when volume changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_volume = 0.8  # Default volume
        self.setup_ui()
        self.setup_audio_manager()
    
    def setup_ui(self):
        """Setup the simplified volume control UI."""
        self.setMaximumHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)
        
        # Volume icon/label - simpler text
        self.volume_label = QLabel("🔊 Volume:")
        self.volume_label.setMinimumWidth(70)
        self.volume_label.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 13px;")
        layout.addWidget(self.volume_label)
        
        # Volume slider - larger and easier to use
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(200)  # Allow up to 200% for racing environments
        self.volume_slider.setValue(80)  # 80% default
        self.volume_slider.setToolTip("Adjust AI Coach volume (0-200% for loud racing environments)")
        self.volume_slider.valueChanged.connect(self._on_slider_changed)
        
        # Make slider larger and easier to grab
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E0E0E0, stop:1 #F0F0F0);
                margin: 2px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2196F3, stop:1 #1976D2);
                border: 2px solid #1976D2;
                width: 20px;
                height: 20px;
                margin: -5px 0;
                border-radius: 12px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #42A5F5, stop:1 #2196F3);
                border: 2px solid #2196F3;
            }
            QSlider::handle:horizontal:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1976D2, stop:1 #0D47A1);
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
                border: 1px solid #1976D2;
                height: 10px;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.volume_slider)
        
        # Volume percentage display - larger and clearer
        self.volume_percent_label = QLabel("80%")
        self.volume_percent_label.setMinimumWidth(50)  # Wider for 3-digit percentages like 200%
        self.volume_percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_percent_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 14px; 
            color: #333; 
            background-color: #F5F5F5; 
            border-radius: 4px; 
            padding: 2px 4px;
        """)
        layout.addWidget(self.volume_percent_label)
    
    def setup_audio_manager(self):
        """Connect to the AI coach audio manager."""
        try:
            from trackpro.race_coach.ai_coach import elevenlabs_client
            
            # Get current volume from audio manager
            self.current_volume = elevenlabs_client.get_ai_coach_volume()
            self._update_ui_from_volume(self.current_volume)
            
            # Add callback to be notified of volume changes from other sources
            elevenlabs_client.add_volume_change_callback(self._on_volume_changed_externally)
            
            logger.info(f"🔊 [VOLUME WIDGET] Connected to audio manager, current volume: {self.current_volume:.2f}")
            
        except Exception as e:
            logger.error(f"🔊 [VOLUME WIDGET] Failed to connect to audio manager: {e}")
    
    def _on_slider_changed(self, value):
        """Handle slider value changes."""
        volume = value / 100.0  # Convert 0-200 to 0.0-2.0
        self._set_volume(volume, update_slider=False)
    
    def _set_volume(self, volume: float, update_slider: bool = True):
        """Set the volume and update UI."""
        try:
            from trackpro.race_coach.ai_coach import elevenlabs_client
            
            self.current_volume = volume
            
            # Update the audio manager
            elevenlabs_client.set_ai_coach_volume(volume)
            
            # Update UI
            if update_slider:
                self.volume_slider.setValue(int(volume * 100))
            
            volume_percent = int(volume * 100)
            self.volume_percent_label.setText(f"{volume_percent}%")
            
            # Dynamic styling based on volume level
            if volume == 0:
                self.volume_percent_label.setStyleSheet("""
                    font-weight: bold; 
                    font-size: 14px; 
                    color: #888; 
                    background-color: #F0F0F0; 
                    border-radius: 4px; 
                    padding: 2px 4px;
                """)
                self.volume_label.setText("🔇 Volume:")
            elif volume < 0.3:
                self.volume_percent_label.setStyleSheet("""
                    font-weight: bold; 
                    font-size: 14px; 
                    color: #666; 
                    background-color: #F5F5F5; 
                    border-radius: 4px; 
                    padding: 2px 4px;
                """)
                self.volume_label.setText("🔉 Volume:")
            elif volume > 1.5:  # Above 150% - racing boost mode
                self.volume_percent_label.setStyleSheet("""
                    font-weight: bold; 
                    font-size: 14px; 
                    color: #FF6B35; 
                    background-color: #FFF3E0; 
                    border-radius: 4px; 
                    padding: 2px 4px;
                """)
                self.volume_label.setText("🔊 Boost:")
            elif volume > 1.0:  # Above 100% - high volume
                self.volume_percent_label.setStyleSheet("""
                    font-weight: bold; 
                    font-size: 14px; 
                    color: #FF9500; 
                    background-color: #FFF8E1; 
                    border-radius: 4px; 
                    padding: 2px 4px;
                """)
                self.volume_label.setText("🔊 High:")
            else:
                self.volume_percent_label.setStyleSheet("""
                    font-weight: bold; 
                    font-size: 14px; 
                    color: #333; 
                    background-color: #F5F5F5; 
                    border-radius: 4px; 
                    padding: 2px 4px;
                """)
                self.volume_label.setText("🔊 Volume:")
            
            # Emit signal for other components
            self.volume_changed.emit(volume)
            
            logger.info(f"🔊 [VOLUME WIDGET] Volume set to {volume:.2f} ({volume_percent}%)")
            
        except Exception as e:
            logger.error(f"🔊 [VOLUME WIDGET] Failed to set volume: {e}")
    
    def _on_volume_changed_externally(self, volume: float):
        """Handle volume changes from external sources."""
        self._update_ui_from_volume(volume)
    
    def _update_ui_from_volume(self, volume: float):
        """Update UI components from volume value."""
        self.current_volume = volume
        self.volume_slider.setValue(int(volume * 100))
        
        volume_percent = int(volume * 100)
        self.volume_percent_label.setText(f"{volume_percent}%")
        
        # Update volume icon based on level
        if volume == 0:
            self.volume_label.setText("🔇 Volume:")
        elif volume < 0.3:
            self.volume_label.setText("🔉 Volume:")
        elif volume > 1.5:  # Above 150% - racing boost mode
            self.volume_label.setText("🔊 Boost:")
        elif volume > 1.0:  # Above 100% - high volume
            self.volume_label.setText("🔊 High:")
        else:
            self.volume_label.setText("🔊 Volume:")
    
    def get_volume(self) -> float:
        """Get current volume."""
        return self.current_volume
    
    def set_volume(self, volume: float):
        """Set volume from external source."""
        self._set_volume(volume)

if __name__ == "__main__":
    """Test the volume widget standalone."""
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("AI Coach Volume Control Test")
    window.resize(400, 100)
    
    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Add volume widget
    volume_widget = AICoachVolumeWidget()
    layout.addWidget(volume_widget)
    
    window.setCentralWidget(central_widget)
    window.show()
    
    sys.exit(app.exec()) 