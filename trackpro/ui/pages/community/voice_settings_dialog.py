"""
Voice Chat Settings Dialog

Provides comprehensive audio device selection and configuration for high-quality voice chat.
"""

import logging
import pyaudio
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QSlider, QGroupBox,
                            QCheckBox, QSpinBox, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)

class VoiceSettingsDialog(QDialog):
    """Dialog for configuring voice chat audio settings."""
    
    settings_changed = pyqtSignal(dict)  # Emitted when settings change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio = None
        self.test_recording = False
        self.test_playback = False
        self.setup_audio()
        self.setup_ui()
        self.load_current_settings()
        
    def setup_audio(self):
        """Initialize PyAudio for device enumeration."""
        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            self.audio = None
    
    def setup_ui(self):
        """Setup the voice settings UI."""
        self.setWindowTitle("Voice Chat Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Voice Chat Audio Configuration")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Audio Quality Settings
        self.create_quality_group(layout)
        
        # Input Device Settings
        self.create_input_group(layout)
        
        # Output Device Settings  
        self.create_output_group(layout)
        
        # Test Controls
        self.create_test_group(layout)
        
        # Buttons
        self.create_buttons(layout)
        
    def create_quality_group(self, parent_layout):
        """Create audio quality configuration group."""
        group = QGroupBox("Audio Quality Settings")
        layout = QVBoxLayout(group)
        
        # Sample Rate
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(QLabel("Sample Rate:"))
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100 Hz", "48000 Hz", "96000 Hz"])
        self.sample_rate_combo.setCurrentText("48000 Hz")  # High quality default
        rate_layout.addWidget(self.sample_rate_combo)
        layout.addLayout(rate_layout)
        
        # Channels
        channels_layout = QHBoxLayout()
        channels_layout.addWidget(QLabel("Channels:"))
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["Mono (1)", "Stereo (2)"])
        self.channels_combo.setCurrentText("Stereo (2)")
        channels_layout.addWidget(self.channels_combo)
        layout.addLayout(channels_layout)
        
        # Bit Depth
        bit_layout = QHBoxLayout()
        bit_layout.addWidget(QLabel("Bit Depth:"))
        self.bit_depth_combo = QComboBox()
        self.bit_depth_combo.addItems(["16-bit", "24-bit", "32-bit"])
        self.bit_depth_combo.setCurrentText("24-bit")  # High quality
        bit_layout.addWidget(self.bit_depth_combo)
        layout.addLayout(bit_layout)
        
        # Buffer Size
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("Buffer Size:"))
        self.buffer_size_combo = QComboBox()
        self.buffer_size_combo.addItems(["256", "512", "1024", "2048"])
        self.buffer_size_combo.setCurrentText("512")  # Low latency
        buffer_layout.addWidget(self.buffer_size_combo)
        layout.addLayout(buffer_layout)
        
        # High Quality Options
        self.noise_suppression = QCheckBox("Enable Noise Suppression")
        self.noise_suppression.setChecked(True)
        layout.addWidget(self.noise_suppression)
        
        self.echo_cancellation = QCheckBox("Enable Echo Cancellation")
        self.echo_cancellation.setChecked(True)
        layout.addWidget(self.echo_cancellation)
        
        self.automatic_gain = QCheckBox("Enable Automatic Gain Control")
        self.automatic_gain.setChecked(True)
        layout.addWidget(self.automatic_gain)
        
        parent_layout.addWidget(group)
        
    def create_input_group(self, parent_layout):
        """Create input device configuration group."""
        group = QGroupBox("Microphone Settings")
        layout = QVBoxLayout(group)
        
        # Input Device Selection
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Microphone:"))
        self.input_device_combo = QComboBox()
        self.populate_input_devices()
        input_layout.addWidget(self.input_device_combo)
        
        self.refresh_input_btn = QPushButton("Refresh")
        self.refresh_input_btn.clicked.connect(self.populate_input_devices)
        input_layout.addWidget(self.refresh_input_btn)
        layout.addLayout(input_layout)
        
        # Input Volume
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Input Volume:"))
        self.input_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.input_volume_slider.setMinimum(0)
        self.input_volume_slider.setMaximum(100)
        self.input_volume_slider.setValue(80)
        self.input_volume_slider.valueChanged.connect(self.on_input_volume_changed)
        volume_layout.addWidget(self.input_volume_slider)
        
        self.input_volume_label = QLabel("80%")
        self.input_volume_label.setMinimumWidth(40)
        volume_layout.addWidget(self.input_volume_label)
        layout.addLayout(volume_layout)
        
        # Input Level Meter
        self.input_level_label = QLabel("Input Level: --")
        self.input_level_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.input_level_label)
        
        parent_layout.addWidget(group)
        
    def create_output_group(self, parent_layout):
        """Create output device configuration group."""
        group = QGroupBox("Speaker/Headphone Settings")
        layout = QVBoxLayout(group)
        
        # Output Device Selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Audio Output:"))
        self.output_device_combo = QComboBox()
        self.populate_output_devices()
        output_layout.addWidget(self.output_device_combo)
        
        self.refresh_output_btn = QPushButton("Refresh")
        self.refresh_output_btn.clicked.connect(self.populate_output_devices)
        output_layout.addWidget(self.refresh_output_btn)
        layout.addLayout(output_layout)
        
        # Output Volume
        out_volume_layout = QHBoxLayout()
        out_volume_layout.addWidget(QLabel("Output Volume:"))
        self.output_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.output_volume_slider.setMinimum(0)
        self.output_volume_slider.setMaximum(100)
        self.output_volume_slider.setValue(80)
        self.output_volume_slider.valueChanged.connect(self.on_output_volume_changed)
        out_volume_layout.addWidget(self.output_volume_slider)
        
        self.output_volume_label = QLabel("80%")
        self.output_volume_label.setMinimumWidth(40)
        out_volume_layout.addWidget(self.output_volume_label)
        layout.addLayout(out_volume_layout)
        
        parent_layout.addWidget(group)
        
    def create_test_group(self, parent_layout):
        """Create audio testing controls."""
        group = QGroupBox("Audio Testing")
        layout = QVBoxLayout(group)
        
        # Test Controls
        test_layout = QHBoxLayout()
        
        self.test_mic_btn = QPushButton("Test Microphone")
        self.test_mic_btn.clicked.connect(self.test_microphone)
        test_layout.addWidget(self.test_mic_btn)
        
        self.test_speaker_btn = QPushButton("Test Speakers")
        self.test_speaker_btn.clicked.connect(self.test_speakers)
        test_layout.addWidget(self.test_speaker_btn)
        
        layout.addLayout(test_layout)
        
        # Test Status
        self.test_status_label = QLabel("Ready to test audio devices")
        self.test_status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.test_status_label)
        
        parent_layout.addWidget(group)
        
    def create_buttons(self, parent_layout):
        """Create dialog buttons."""
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.clicked.connect(self.apply_settings)
        self.apply_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        parent_layout.addLayout(button_layout)
        
    def populate_input_devices(self):
        """Populate input device dropdown."""
        if not self.audio:
            return
            
        self.input_device_combo.clear()
        
        try:
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:  # Has input capability
                    name = device_info['name']
                    self.input_device_combo.addItem(f"{name} (Device {i})", i)
        except Exception as e:
            logger.error(f"Error enumerating input devices: {e}")
            self.input_device_combo.addItem("Default Microphone", 0)
            
    def populate_output_devices(self):
        """Populate output device dropdown."""
        if not self.audio:
            return
            
        self.output_device_combo.clear()
        
        try:
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxOutputChannels'] > 0:  # Has output capability
                    name = device_info['name']
                    self.output_device_combo.addItem(f"{name} (Device {i})", i)
        except Exception as e:
            logger.error(f"Error enumerating output devices: {e}")
            self.output_device_combo.addItem("Default Speakers", 0)
            
    def on_input_volume_changed(self, value):
        """Handle input volume slider change."""
        self.input_volume_label.setText(f"{value}%")
        
    def on_output_volume_changed(self, value):
        """Handle output volume slider change."""
        self.output_volume_label.setText(f"{value}%")
        
    def test_microphone(self):
        """Test the selected microphone."""
        if not self.audio:
            QMessageBox.warning(self, "Error", "Audio system not available")
            return
            
        try:
            device_index = self.input_device_combo.currentData()
            if device_index is None:
                device_index = 0
                
            # Get audio format
            sample_rate = int(self.sample_rate_combo.currentText().split()[0])
            channels = 2 if "Stereo" in self.channels_combo.currentText() else 1
            bit_depth = int(self.bit_depth_combo.currentText().split('-')[0])
            
            if bit_depth == 16:
                format_type = pyaudio.paInt16
            elif bit_depth == 24:
                format_type = pyaudio.paInt24
            else:
                format_type = pyaudio.paInt32
                
            # Start recording test
            stream = self.audio.open(
                format=format_type,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            
            self.test_status_label.setText("Recording... Speak into your microphone")
            self.test_status_label.setStyleSheet("color: #FF5722; font-weight: bold;")
            
            # Record for 3 seconds
            frames = []
            for _ in range(0, int(sample_rate / 1024 * 3)):  # 3 seconds
                data = stream.read(1024)
                frames.append(data)
                
            stream.stop_stream()
            stream.close()
            
            # Play back the recording
            self.test_status_label.setText("Playing back recording...")
            
            output_stream = self.audio.open(
                format=format_type,
                channels=channels,
                rate=sample_rate,
                output=True,
                frames_per_buffer=1024
            )
            
            for frame in frames:
                output_stream.write(frame)
                
            output_stream.stop_stream()
            output_stream.close()
            
            self.test_status_label.setText("Microphone test completed")
            self.test_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            QMessageBox.information(self, "Test Complete", 
                                  "Microphone test completed. You should have heard your voice played back.")
                                  
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            QMessageBox.warning(self, "Test Failed", f"Microphone test failed: {str(e)}")
            self.test_status_label.setText("Test failed")
            self.test_status_label.setStyleSheet("color: #F44336;")
            
    def test_speakers(self):
        """Test the selected speakers/headphones."""
        if not self.audio:
            QMessageBox.warning(self, "Error", "Audio system not available")
            return
            
        try:
            device_index = self.output_device_combo.currentData()
            if device_index is None:
                device_index = 0
                
            # Generate test tone
            import numpy as np
            
            sample_rate = int(self.sample_rate_combo.currentText().split()[0])
            channels = 2 if "Stereo" in self.channels_combo.currentText() else 1
            bit_depth = int(self.bit_depth_combo.currentText().split('-')[0])
            
            if bit_depth == 16:
                format_type = pyaudio.paInt16
                dtype = np.int16
                max_val = 32767
            elif bit_depth == 24:
                format_type = pyaudio.paInt24
                dtype = np.int32
                max_val = 8388607
            else:
                format_type = pyaudio.paInt32
                dtype = np.int32
                max_val = 2147483647
                
            # Generate 1 second of test tone
            duration = 1.0
            frequency = 440.0  # A4 note
            samples = int(sample_rate * duration)
            
            # Generate sine wave
            t = np.linspace(0, duration, samples, False)
            tone = max_val * 0.3 * np.sin(2 * np.pi * frequency * t)
            
            if channels == 2:
                # Stereo - same tone on both channels
                tone = np.column_stack((tone, tone))
                
            # Convert to bytes
            audio_data = tone.astype(dtype).tobytes()
            
            # Play test tone
            stream = self.audio.open(
                format=format_type,
                channels=channels,
                rate=sample_rate,
                output=True,
                output_device_index=device_index,
                frames_per_buffer=1024
            )
            
            self.test_status_label.setText("Playing test tone...")
            self.test_status_label.setStyleSheet("color: #FF5722; font-weight: bold;")
            
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            
            self.test_status_label.setText("Speaker test completed")
            self.test_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            QMessageBox.information(self, "Test Complete", 
                                  "Speaker test completed. You should have heard a test tone.")
                                  
        except Exception as e:
            logger.error(f"Speaker test failed: {e}")
            QMessageBox.warning(self, "Test Failed", f"Speaker test failed: {str(e)}")
            self.test_status_label.setText("Test failed")
            self.test_status_label.setStyleSheet("color: #F44336;")
            
    def load_current_settings(self):
        """Load current voice chat settings."""
        # This would load from a settings file or database
        # For now, use defaults
        pass
        
    def apply_settings(self):
        """Apply the current settings."""
        settings = {
            'sample_rate': int(self.sample_rate_combo.currentText().split()[0]),
            'channels': 2 if "Stereo" in self.channels_combo.currentText() else 1,
            'bit_depth': int(self.bit_depth_combo.currentText().split('-')[0]),
            'buffer_size': int(self.buffer_size_combo.currentText()),
            'input_device': self.input_device_combo.currentData(),
            'output_device': self.output_device_combo.currentData(),
            'input_volume': self.input_volume_slider.value(),
            'output_volume': self.output_volume_slider.value(),
            'noise_suppression': self.noise_suppression.isChecked(),
            'echo_cancellation': self.echo_cancellation.isChecked(),
            'automatic_gain': self.automatic_gain.isChecked()
        }
        
        self.settings_changed.emit(settings)
        self.accept()
        
    def closeEvent(self, event):
        """Clean up audio resources on close."""
        if self.audio:
            self.audio.terminate()
        super().closeEvent(event) 