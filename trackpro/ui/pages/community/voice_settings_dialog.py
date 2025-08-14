"""
Voice Chat Settings Dialog

Provides comprehensive audio device selection and configuration for high-quality voice chat.
"""

import logging
import pyaudio
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QSlider, QGroupBox,
                            QCheckBox, QSpinBox, QMessageBox, QFrame, QProgressBar)
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
        
        # Direct Monitoring (Hear Yourself)
        self.direct_monitoring = QCheckBox("Hear Yourself (Direct Monitoring)")
        self.direct_monitoring.setToolTip("When enabled, you'll hear your own voice slightly in your headphones/speakers. This helps you monitor your audio levels and speaking volume.")
        self.direct_monitoring.setChecked(True)  # Enabled by default
        layout.addWidget(self.direct_monitoring)
        
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
        
        self.test_mic_btn = QPushButton("🎤 Test Microphone (Real-time)")
        self.test_mic_btn.clicked.connect(self.test_microphone_realtime)
        self.test_mic_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; font-weight: bold;")
        test_layout.addWidget(self.test_mic_btn)
        
        self.test_speaker_btn = QPushButton("🔊 Test Speakers")
        self.test_speaker_btn.clicked.connect(self.test_speakers)
        test_layout.addWidget(self.test_speaker_btn)
        
        layout.addLayout(test_layout)
        
        # Real-time Voice Level Indicator
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Voice Level:"))
        
        self.voice_level_bar = QProgressBar()
        self.voice_level_bar.setMinimum(0)
        self.voice_level_bar.setMaximum(100)
        self.voice_level_bar.setValue(0)
        self.voice_level_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:0.5 #FFC107, stop:1 #F44336);
            }
        """)
        level_layout.addWidget(self.voice_level_bar)
        
        self.voice_level_label = QLabel("🎤")
        self.voice_level_label.setStyleSheet("font-size: 16px; color: #666;")
        level_layout.addWidget(self.voice_level_label)
        
        layout.addLayout(level_layout)
        
        # Test Status
        self.test_status_label = QLabel("Ready to test audio devices")
        self.test_status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.test_status_label)
        
        # Real-time test variables
        self.is_testing_mic = False
        self.test_stream = None
        self.test_timer = None
        
        parent_layout.addWidget(group)
        
    def create_buttons(self, parent_layout):
        """Create dialog buttons."""
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.clicked.connect(self.apply_settings)
        self.apply_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_dialog)
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
        
    def test_microphone_realtime(self):
        """Test microphone with real-time feedback and instant monitoring."""
        if not self.audio:
            QMessageBox.warning(self, "Error", "Audio system not available")
            return
            
        if self.is_testing_mic:
            # Stop testing
            self.stop_microphone_test()
            return
            
        try:
            device_index = self.input_device_combo.currentData()
            if device_index is None:
                # Pick a concrete mic: skip Windows mapper/primary aliases
                try:
                    chosen = None
                    for i in range(self.audio.get_device_count()):
                        info = self.audio.get_device_info_by_index(i)
                        name = str(info.get('name', '')).lower()
                        if info.get('maxInputChannels', 0) > 0 and 'mapper' not in name and 'primary sound' not in name:
                            chosen = i
                            break
                    if chosen is None:
                        for i in range(self.audio.get_device_count()):
                            info = self.audio.get_device_info_by_index(i)
                            if info.get('maxInputChannels', 0) > 0:
                                chosen = i
                                break
                    device_index = chosen if chosen is not None else 0
                except Exception:
                    device_index = 0
                
            # Get device info to check capabilities
            device_info = self.audio.get_device_info_by_index(device_index)
            max_channels = device_info['maxInputChannels']
            
            # Get audio format
            sample_rate = int(self.sample_rate_combo.currentText().split()[0])
            channels = 2 if "Stereo" in self.channels_combo.currentText() else 1
            
            # Ensure we don't exceed device capabilities
            if channels > max_channels:
                channels = max_channels
                logger.warning(f"Device only supports {max_channels} channels, using {channels}")
            
            bit_depth = int(self.bit_depth_combo.currentText().split('-')[0])
            
            if bit_depth == 16:
                format_type = pyaudio.paInt16
            elif bit_depth == 24:
                format_type = pyaudio.paInt24
            else:
                format_type = pyaudio.paInt32
                
            # Start real-time recording with fallback attempts
            def try_open_test(fmt, ch, rate, dev):
                return self.audio.open(
                    format=fmt,
                    channels=ch,
                    rate=rate,
                    input=True,
                    input_device_index=dev,
                    frames_per_buffer=256,
                    stream_callback=self._audio_callback
                )

            opened = False
            last_err = None
            # Build sample-rate candidates: current, device default, common fallbacks
            rate_opts = []
            def _push_rate(val):
                try:
                    r = int(val)
                    if r > 0 and r not in rate_opts:
                        rate_opts.append(r)
                except Exception:
                    pass
            _push_rate(sample_rate)
            try:
                dinfo = self.audio.get_device_info_by_index(device_index)
                _push_rate(dinfo.get('defaultSampleRate'))
            except Exception:
                pass
            _push_rate(48000)
            _push_rate(44100)
            _push_rate(32000)
            _push_rate(16000)
            ch_opts = [min(channels, max_channels)]
            if 1 not in ch_opts:
                ch_opts.append(1)
            fmt_opts = [format_type]
            if format_type != pyaudio.paInt16:
                fmt_opts.append(pyaudio.paInt16)

            for r in rate_opts:
                for ch in ch_opts:
                    for fmt in fmt_opts:
                        try:
                            # Probe when available
                            if hasattr(self.audio, 'is_format_supported'):
                                try:
                                    self.audio.is_format_supported(r, input_device=device_index, input_channels=ch, input_format=fmt)
                                except Exception as probe_err:
                                    last_err = probe_err
                                    continue
                            self.test_stream = try_open_test(fmt, ch, r, device_index)
                            opened = True
                            # Keep monitor in same format
                            self.monitor_stream = self.audio.open(
                                format=fmt,
                                channels=ch,
                                rate=r,
                                output=True,
                                frames_per_buffer=256
                            )
                            # Persist last working input format for join to reuse
                            try:
                                from trackpro.config import config
                                def _bits_from_fmt(f):
                                    if f == pyaudio.paInt16:
                                        return 16
                                    if f == pyaudio.paInt24:
                                        return 24
                                    return 32
                                config.set('voice_chat.last_working_input_device', device_index)
                                config.set('voice_chat.last_working_sample_rate', r)
                                config.set('voice_chat.last_working_channels', ch)
                                config.set('voice_chat.last_working_bit_depth', _bits_from_fmt(fmt))
                                config.save()
                            except Exception:
                                pass
                            break
                        except Exception as e:
                            last_err = e
                    if opened:
                        break
                if opened:
                    break

            if not opened:
                raise RuntimeError(f"No supported mic format on device {device_index}: {last_err}")
            
            # Start output stream for instant monitoring
            self.monitor_stream = self.audio.open(
                format=format_type,
                channels=channels,
                rate=sample_rate,
                output=True,
                frames_per_buffer=256
            )
            
            self.is_testing_mic = True
            self.test_stream.start_stream()
            
            # Update UI
            self.test_mic_btn.setText("🛑 Stop Test")
            self.test_mic_btn.setStyleSheet("background-color: #F44336; color: white; padding: 8px; font-weight: bold;")
            self.test_status_label.setText("🎤 Speak into your microphone - you'll hear yourself instantly!")
            self.test_status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            
            # Start timer for real-time level updates
            self.test_timer = QTimer()
            self.test_timer.timeout.connect(self._update_voice_level)
            self.test_timer.start(50)  # Update every 50ms for smooth animation
            
            logger.info("Real-time microphone test started")
            
        except Exception as e:
            logger.error(f"Real-time microphone test failed: {e}")
            QMessageBox.warning(self, "Test Failed", f"Microphone test failed: {str(e)}")
            self.test_status_label.setText("Test failed")
            self.test_status_label.setStyleSheet("color: #F44336;")
    
    def stop_microphone_test(self):
        """Stop the real-time microphone test."""
        if self.test_timer:
            self.test_timer.stop()
            self.test_timer = None
            
        if self.test_stream:
            try:
                if self.test_stream.is_active():
                    self.test_stream.stop_stream()
            except Exception:
                pass
            try:
                self.test_stream.close()
            except Exception:
                pass
            self.test_stream = None
            
        if hasattr(self, 'monitor_stream') and self.monitor_stream:
            try:
                if self.monitor_stream.is_active():
                    self.monitor_stream.stop_stream()
            except Exception:
                pass
            try:
                self.monitor_stream.close()
            except Exception:
                pass
            self.monitor_stream = None
            
        self.is_testing_mic = False
        
        # Reset UI
        self.test_mic_btn.setText("🎤 Test Microphone (Real-time)")
        self.test_mic_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px; font-weight: bold;")
        self.test_status_label.setText("Ready to test audio devices")
        self.test_status_label.setStyleSheet("color: #666; font-style: italic;")
        
        # Reset voice level
        self.voice_level_bar.setValue(0)
        self.voice_level_label.setText("🎤")
        self.voice_level_label.setStyleSheet("font-size: 16px; color: #666;")
        
        logger.info("Real-time microphone test stopped")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for real-time processing."""
        try:
            # Calculate audio level
            import numpy as np
            audio_array = np.frombuffer(in_data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            level = min(rms / 32767.0, 1.0)  # Normalize to 0-1

            # Store level for UI update
            self.current_audio_level = level

            # DEBUG: Log audio level during testing
            if hasattr(self, '_last_test_debug_time'):
                import time
                current_time = time.time()
                if current_time - self._last_test_debug_time > 0.5:  # Log every 0.5 seconds
                    logger.info(f"🎤 TEST DEBUG: Level={level:.3f}, RMS={rms:.1f}, Buffer={len(in_data)}")
                    self._last_test_debug_time = current_time
            else:
                import time
                self._last_test_debug_time = time.time()

            # Send to monitor stream for instant feedback
            if hasattr(self, 'monitor_stream') and self.monitor_stream:
                try:
                    self.monitor_stream.write(in_data)
                except Exception:
                    pass

            return (in_data, pyaudio.paContinue)

        except Exception as e:
            logger.error(f"Audio callback error: {e}")
            return (None, pyaudio.paComplete)
    
    def _update_voice_level(self):
        """Update the voice level indicator."""
        try:
            if hasattr(self, 'current_audio_level'):
                level = self.current_audio_level
                level_percent = int(level * 100)
                
                # Update progress bar
                self.voice_level_bar.setValue(level_percent)
                
                # Update label with color coding
                if level > 0.7:
                    self.voice_level_label.setText("🔴")
                    self.voice_level_label.setStyleSheet("font-size: 16px; color: #F44336;")
                elif level > 0.3:
                    self.voice_level_label.setText("🟡")
                    self.voice_level_label.setStyleSheet("font-size: 16px; color: #FFC107;")
                elif level > 0.1:
                    self.voice_level_label.setText("🟢")
                    self.voice_level_label.setStyleSheet("font-size: 16px; color: #4CAF50;")
                else:
                    self.voice_level_label.setText("🎤")
                    self.voice_level_label.setStyleSheet("font-size: 16px; color: #666;")
                    
        except Exception as e:
            logger.error(f"Voice level update error: {e}")
    
    def test_microphone(self):
        """Legacy microphone test (kept for compatibility)."""
        QMessageBox.information(self, "New Feature", 
                              "The microphone test has been upgraded to real-time testing!\n\n"
                              "Click '🎤 Test Microphone (Real-time)' for instant feedback with voice level indicator.")
            
    def test_speakers(self):
        """Test the selected speakers/headphones."""
        if not self.audio:
            QMessageBox.warning(self, "Error", "Audio system not available")
            return
            
        try:
            device_index = self.output_device_combo.currentData()
            if device_index is None:
                device_index = 0
                
            # Get device info to check capabilities
            device_info = self.audio.get_device_info_by_index(device_index)
            max_channels = device_info['maxOutputChannels']
            
            # Generate test tone
            import numpy as np
            
            sample_rate = int(self.sample_rate_combo.currentText().split()[0])
            channels = 2 if "Stereo" in self.channels_combo.currentText() else 1
            
            # Ensure we don't exceed device capabilities
            if channels > max_channels:
                channels = max_channels
                logger.warning(f"Device only supports {max_channels} channels, using {channels}")
            
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
                
            # Generate a pleasant test tone (gentle bell-like sound)
            duration = 1.5  # Slightly longer for better experience
            frequency = 1000.0  # Pleasant frequency (same as join notification)
            samples = int(sample_rate * duration)
            
            # Generate a gentle bell-like sound with smooth harmonics
            t = np.linspace(0, duration, samples, False)
            
            # Create a pleasant ding with gentle harmonics
            tone = (0.6 * np.sin(2 * np.pi * frequency * t) + 
                   0.3 * np.sin(2 * np.pi * frequency * 1.5 * t) + 
                   0.1 * np.sin(2 * np.pi * frequency * 2.5 * t))
            
            # Apply very smooth envelope for gentle sound
            envelope = np.exp(-2.5 * t)  # Slower decay for gentler sound
            tone = tone * envelope
            
            # Apply longer fade in/out to avoid any harsh edges
            fade_samples = int(0.08 * sample_rate)  # Longer fade
            tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
            tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            # Get volume from output volume slider for comfortable testing
            volume_percent = self.output_volume_slider.value() / 100.0
            volume_multiplier = 0.1 + (volume_percent * 0.2)  # Range from 0.1 to 0.3
            
            # Scale to proper range with user-controlled volume
            tone = max_val * volume_multiplier * tone
            
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
            
            self.test_status_label.setText("Playing gentle test tone...")
            self.test_status_label.setStyleSheet("color: #FF5722; font-weight: bold;")
            
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            
            self.test_status_label.setText("Speaker test completed ✓")
            self.test_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            
            QMessageBox.information(self, "Test Complete", 
                                  f"Speaker test completed successfully!\n\n"
                                  f"You should have heard a gentle bell-like tone.\n"
                                  f"Volume used: {self.output_volume_slider.value()}%\n\n"
                                  f"If the volume was too loud or quiet, adjust the Output Volume slider and test again.")
                                  
        except Exception as e:
            logger.error(f"Speaker test failed: {e}")
            try:
                QMessageBox.warning(self, "Test Failed", f"Speaker test failed: {str(e)}")
            except Exception:
                pass
            self.test_status_label.setText("Test failed")
            self.test_status_label.setStyleSheet("color: #F44336;")
            
    def load_current_settings(self):
        """Load current voice chat settings from config."""
        try:
            from trackpro.config import config
            
            # Load sample rate
            sample_rate = config.voice_chat_sample_rate
            if sample_rate == 44100:
                self.sample_rate_combo.setCurrentText("44100 Hz")
            elif sample_rate == 96000:
                self.sample_rate_combo.setCurrentText("96000 Hz")
            else:
                self.sample_rate_combo.setCurrentText("48000 Hz")
            
            # Load channels
            channels = config.voice_chat_channels
            if channels == 1:
                self.channels_combo.setCurrentText("Mono (1)")
            else:
                self.channels_combo.setCurrentText("Stereo (2)")
            
            # Load bit depth
            bit_depth = config.voice_chat_bit_depth
            if bit_depth == 16:
                self.bit_depth_combo.setCurrentText("16-bit")
            elif bit_depth == 32:
                self.bit_depth_combo.setCurrentText("32-bit")
            else:
                self.bit_depth_combo.setCurrentText("24-bit")
            
            # Load buffer size
            buffer_size = config.voice_chat_buffer_size
            self.buffer_size_combo.setCurrentText(str(buffer_size))
            
            # Load input device
            input_device = config.voice_chat_input_device
            if input_device is not None:
                # Find the device in the combo box
                for i in range(self.input_device_combo.count()):
                    if self.input_device_combo.itemData(i) == input_device:
                        self.input_device_combo.setCurrentIndex(i)
                        break
            
            # Load output device
            output_device = config.voice_chat_output_device
            if output_device is not None:
                # Find the device in the combo box
                for i in range(self.output_device_combo.count()):
                    if self.output_device_combo.itemData(i) == output_device:
                        self.output_device_combo.setCurrentIndex(i)
                        break
            
            # Load volumes
            input_volume = config.voice_chat_input_volume
            self.input_volume_slider.setValue(input_volume)
            self.input_volume_label.setText(f"{input_volume}%")
            
            output_volume = config.voice_chat_output_volume
            self.output_volume_slider.setValue(output_volume)
            self.output_volume_label.setText(f"{output_volume}%")
            
            # Load processing settings
            self.noise_suppression.setChecked(config.voice_chat_noise_suppression)
            self.echo_cancellation.setChecked(config.voice_chat_echo_cancellation)
            self.automatic_gain.setChecked(config.voice_chat_automatic_gain)
            
            # Load direct monitoring setting
            self.direct_monitoring.setChecked(config.voice_chat_direct_monitoring)
            
            logger.info("Voice settings loaded from config")
            
        except Exception as e:
            logger.error(f"Failed to load voice settings: {e}")
            # Use defaults if loading fails
        
    def cancel_dialog(self):
        """Cancel the dialog and clean up audio resources."""
        # Stop any active microphone test
        if hasattr(self, 'is_testing_mic') and self.is_testing_mic:
            self.stop_microphone_test()
            
        if self.audio:
            self.audio.terminate()
            
        self.reject()
        
    def apply_settings(self):
        """Apply the current settings and save to config."""
        try:
            from trackpro.config import config
            
            # Stop any active microphone test before applying settings (ignore stop errors)
            if hasattr(self, 'is_testing_mic') and self.is_testing_mic:
                try:
                    self.stop_microphone_test()
                except Exception:
                    pass
            
            # Get current settings
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
                'automatic_gain': self.automatic_gain.isChecked(),
                'direct_monitoring': self.direct_monitoring.isChecked()
            }
            
            # Save to config
            config.set('voice_chat.sample_rate', settings['sample_rate'])
            config.set('voice_chat.channels', settings['channels'])
            config.set('voice_chat.bit_depth', settings['bit_depth'])
            config.set('voice_chat.buffer_size', settings['buffer_size'])
            config.set('voice_chat.input_device', settings['input_device'])
            config.set('voice_chat.output_device', settings['output_device'])
            config.set('voice_chat.input_volume', settings['input_volume'])
            config.set('voice_chat.output_volume', settings['output_volume'])
            config.set('voice_chat.noise_suppression', settings['noise_suppression'])
            config.set('voice_chat.echo_cancellation', settings['echo_cancellation'])
            config.set('voice_chat.automatic_gain', settings['automatic_gain'])
            config.set('voice_chat.direct_monitoring', settings['direct_monitoring'])
            
            # Save config to file
            config.save()
            
            logger.info("Voice settings saved to config")
            
            # Emit settings changed signal
            self.settings_changed.emit(settings)
            
            # Clean up audio resources before accepting
            if self.audio:
                try:
                    self.audio.terminate()
                except Exception:
                    pass
                
            self.accept()
            
        except Exception as e:
            logger.error(f"Failed to save voice settings: {e}")
            # Still emit settings but don't save to config
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
                'automatic_gain': self.automatic_gain.isChecked(),
                'direct_monitoring': self.direct_monitoring.isChecked()
            }
            self.settings_changed.emit(settings)
            
            # Clean up audio resources before accepting
            if self.audio:
                try:
                    self.audio.terminate()
                except Exception:
                    pass
                
            self.accept()
        
    def closeEvent(self, event):
        """Clean up audio resources on close."""
        # Stop any active microphone test
        if hasattr(self, 'is_testing_mic') and self.is_testing_mic:
            self.stop_microphone_test()
            
        if self.audio:
            self.audio.terminate()
        super().closeEvent(event) 