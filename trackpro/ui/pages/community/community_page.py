"""Community page with Discord-inspired design and voice chat functionality."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame, 
    QSizePolicy, QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QSplitter, QTabWidget, QLineEdit, QComboBox, QSlider, QCheckBox,
    QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtMultimedia import QMediaDevices, QAudioInput, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import wave
import threading
import websockets
import asyncio
import json
import numpy as np

from ...modern.shared.base_page import BasePage
from ....community.private_messaging_widget import PrivateConversationListItem, PrivateConversationWidget

logger = logging.getLogger(__name__)

# Optional imports for voice chat functionality
PYAUDIO_AVAILABLE = False
try:
    import pyaudio
    import numpy as np
    PYAUDIO_AVAILABLE = True
except ImportError:
    logger.warning("pyaudio not available - voice chat functionality will be disabled")
except Exception as e:
    logger.warning(f"Error importing pyaudio: {e} - voice chat functionality will be disabled")

# Import high-quality voice components
try:
    from .voice_settings_dialog import VoiceSettingsDialog
    from .high_quality_voice_manager import HighQualityVoiceManager
    from trackpro.voice_server_manager import start_voice_server, stop_voice_server, is_voice_server_running
    VOICE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Voice components not available: {e}")
    VOICE_COMPONENTS_AVAILABLE = False

# Role colors for Discord-inspired design
ROLE_COLORS = {
    'admin': '#ff4444',      # Red
    'moderator': '#ff8800',  # Orange  
    'racing_pro': '#4488ff', # Blue
    'racer': '#44ff44',      # Green
    'newbie': '#888888'      # Gray
}

class VoiceChatManager(QObject):
    """Manages voice chat functionality using PyAudio and WebSocket."""
    
    voice_data_received = pyqtSignal(bytes)
    user_joined_voice = pyqtSignal(str)
    user_left_voice = pyqtSignal(str)
    voice_error = pyqtSignal(str)
    audio_level_changed = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.audio = None
        self.is_recording = False
        self.is_playing = False
        self.websocket = None
        self.voice_thread = None
        
        # Use high-quality voice manager if available
        if VOICE_COMPONENTS_AVAILABLE:
            try:
                self.voice_manager = HighQualityVoiceManager()
                self.use_high_quality = True
                logger.info("Using high-quality voice chat manager")
            except Exception as e:
                logger.error(f"Failed to initialize high-quality voice manager: {e}")
                self.use_high_quality = False
        else:
            self.use_high_quality = False
        
        # Fallback audio settings
        self.CHUNK = 1024
        self.FORMAT = None
        self.CHANNELS = 1
        self.RATE = 44100
        
        # Initialize pyaudio if available
        try:
            global PYAUDIO_AVAILABLE
            if PYAUDIO_AVAILABLE:
                try:
                    self.audio = pyaudio.PyAudio()
                    self.FORMAT = pyaudio.paInt16
                except Exception as e:
                    logger.error(f"Failed to initialize pyaudio: {e}")
                    PYAUDIO_AVAILABLE = False
        except Exception as e:
            logger.error(f"Error in VoiceChatManager initialization: {e}")
            PYAUDIO_AVAILABLE = False
        
    def start_voice_chat(self, server_url: str, channel_id: str):
        """Start voice chat connection."""
        if not PYAUDIO_AVAILABLE:
            self.voice_error.emit("Voice chat not available - pyaudio not installed")
            return
            
        if self.use_high_quality:
            # Use high-quality voice manager
            self.voice_manager.start_voice_chat(server_url, channel_id)
            # Connect signals
            self.voice_manager.voice_data_received.connect(self.voice_data_received.emit)
            self.voice_manager.user_joined_voice.connect(self.user_joined_voice.emit)
            self.voice_manager.user_left_voice.connect(self.user_left_voice.emit)
            self.voice_manager.voice_error.connect(self.voice_error.emit)
            self.voice_manager.audio_level_changed.connect(self.audio_level_changed.emit)
        else:
            # Use fallback implementation
            try:
                self.voice_thread = threading.Thread(
                    target=self._run_voice_client,
                    args=(server_url, channel_id)
                )
                self.voice_thread.daemon = True
                self.voice_thread.start()
            except Exception as e:
                self.voice_error.emit(f"Failed to start voice chat: {str(e)}")
    
    def update_voice_settings(self, settings: dict):
        """Update voice chat settings."""
        if self.use_high_quality:
            self.voice_manager.update_settings(settings)
    
    def get_available_devices(self):
        """Get available audio devices."""
        if self.use_high_quality:
            return self.voice_manager.get_available_devices()
        return {'input': [], 'output': []}
    
    def _run_voice_client(self, server_url: str, channel_id: str):
        """Run voice client in separate thread (fallback)."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._voice_client_loop(server_url, channel_id))
        except Exception as e:
            self.voice_error.emit(f"Voice client error: {str(e)}")
        finally:
            if 'loop' in locals():
                loop.close()
    
    async def _voice_client_loop(self, server_url: str, channel_id: str):
        """Voice client WebSocket loop (fallback)."""
        try:
            async with websockets.connect(f"{server_url}/voice/{channel_id}") as websocket:
                self.websocket = websocket
                
                # Start audio recording
                self._start_recording()
                
                # Start audio playback
                self._start_playback()
                
                # Handle incoming voice data
                async for message in websocket:
                    data = json.loads(message)
                    if data['type'] == 'voice_data':
                        self.voice_data_received.emit(bytes(data['audio']))
                    elif data['type'] == 'user_joined':
                        self.user_joined_voice.emit(data['user_id'])
                    elif data['type'] == 'user_left':
                        self.user_left_voice.emit(data['user_id'])
                        
        except Exception as e:
            self.voice_error.emit(f"WebSocket error: {str(e)}")
    
    def _start_recording(self):
        """Start audio recording (fallback)."""
        if not PYAUDIO_AVAILABLE or not self.audio:
            self.voice_error.emit("Audio recording not available - pyaudio not installed")
            return
            
        try:
            self.stream_in = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            self.is_recording = True
            
            # Start recording thread
            threading.Thread(target=self._record_audio, daemon=True).start()
            
        except Exception as e:
            self.voice_error.emit(f"Failed to start recording: {str(e)}")
    
    def _record_audio(self):
        """Record audio and send to WebSocket (fallback)."""
        while self.is_recording:
            try:
                data = self.stream_in.read(self.CHUNK)
                if self.websocket:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.websocket.send(json.dumps({
                            'type': 'voice_data',
                            'audio': list(data)
                        })))
            except Exception as e:
                logger.error(f"Recording error: {e}")
                break
    
    def _start_playback(self):
        """Start audio playback (fallback)."""
        if not PYAUDIO_AVAILABLE or not self.audio:
            self.voice_error.emit("Audio playback not available - pyaudio not installed")
            return
            
        try:
            self.stream_out = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK
            )
            self.is_playing = True
        except Exception as e:
            self.voice_error.emit(f"Failed to start playback: {str(e)}")
    
    def stop_voice_chat(self):
        """Stop voice chat."""
        if self.use_high_quality:
            self.voice_manager.stop_voice_chat()
        else:
            self.is_recording = False
            self.is_playing = False
            
            if hasattr(self, 'stream_in'):
                self.stream_in.stop_stream()
                self.stream_in.close()
            
            if hasattr(self, 'stream_out'):
                self.stream_out.stop_stream()
                self.stream_out.close()
            
            if self.websocket:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.websocket.close())
                except Exception as e:
                    logger.error(f"Error closing websocket: {e}")
    
    def __del__(self):
        """Cleanup audio resources."""
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()


class ChatMessageWidget(QWidget):
    """Individual chat message widget with role-based colors."""
    
    def __init__(self, message_data, user_role='newbie'):
        super().__init__()
        self.message_data = message_data
        self.user_role = user_role
        
        # Debug logging to see the message data structure
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 ChatMessageWidget received message_data: {message_data}")
        logger.info(f"🔍 Message sender_name: {message_data.get('sender_name', 'NOT_FOUND')}")
        logger.info(f"🔍 Message user_profiles: {message_data.get('user_profiles', 'NOT_FOUND')}")
        
        self.setup_ui()
    
    def create_avatar(self):
        """Create a circular avatar with user initials."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background
        # Handle both flat sender_name and nested sender structure
        import logging
        logger = logging.getLogger(__name__)
        
        name = self.message_data.get('sender_name')
        logger.info(f"🔍 Avatar creation - sender_name: {name}")
        
        # Try to get name from user_profiles first
        if not name and self.message_data.get('user_profiles'):
            user_profile = self.message_data['user_profiles']
            name = user_profile.get('display_name') or user_profile.get('username') or 'U'
            logger.info(f"🔍 Avatar creation - from user_profiles: {name}")
        
        # If still no name, try to get from current user context
        if not name:
            try:
                from trackpro.auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    # Check if this is the current user's message
                    if self.message_data.get('sender_id') == user.id:
                        name = user.name or user.email or 'You'
                        logger.info(f"🔍 Avatar creation - current user: {name}")
                    else:
                        name = 'U'
                        logger.info(f"🔍 Avatar creation - unknown user: {name}")
                else:
                    name = 'U'
                    logger.info(f"🔍 Avatar creation - no current user: {name}")
            except Exception as e:
                logger.debug(f"Could not get current user for avatar: {e}")
                name = 'U'
                logger.info(f"🔍 Avatar creation - using fallback: {name}")
            
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 32, 32)
        
        # Draw initials
        initials = ''.join([word[0].upper() for word in name.split()][:2])
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        return pixmap
    
    def setup_ui(self):
        """Setup the message UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # User avatar
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        avatar_label.setPixmap(self.create_avatar())
        layout.addWidget(avatar_label)
        
        # Message content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        # Username with role color
        # Handle both flat sender_name and nested sender structure
        import logging
        logger = logging.getLogger(__name__)
        
        sender_name = self.message_data.get('sender_name')
        logger.info(f"🔍 Username display - sender_name: {sender_name}")
        
        # Try to get name from user_profiles first
        if not sender_name and self.message_data.get('user_profiles'):
            user_profile = self.message_data['user_profiles']
            sender_name = user_profile.get('display_name') or user_profile.get('username') or 'Unknown'
            logger.info(f"🔍 Username display - from user_profiles: {sender_name}")
        
        # If still no name, try to get from current user context
        if not sender_name:
            try:
                from trackpro.auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    # Check if this is the current user's message
                    if self.message_data.get('sender_id') == user.id:
                        sender_name = user.name or user.email or 'You'
                        logger.info(f"🔍 Username display - current user: {sender_name}")
                    else:
                        sender_name = 'Unknown'
                        logger.info(f"🔍 Username display - unknown user: {sender_name}")
                else:
                    sender_name = 'Unknown'
                    logger.info(f"🔍 Username display - no current user: {sender_name}")
            except Exception as e:
                logger.debug(f"Could not get current user for username: {e}")
                sender_name = 'Unknown'
                logger.info(f"🔍 Username display - using fallback: {sender_name}")
            
        username_label = QLabel(sender_name)
        role_color = ROLE_COLORS.get(self.user_role, ROLE_COLORS['newbie'])
        username_label.setStyleSheet(f"color: {role_color}; font-weight: bold; font-size: 14px;")
        
        # Timestamp
        timestamp = self.message_data.get('created_at', '')
        if timestamp:
            time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%H:%M')
            time_label = QLabel(time_str)
            time_label.setStyleSheet("color: #888888; font-size: 11px;")
            username_layout = QHBoxLayout()
            username_layout.addWidget(username_label)
            username_layout.addWidget(time_label)
            username_layout.addStretch()
            content_layout.addLayout(username_layout)
        else:
            content_layout.addWidget(username_label)
        
        # Message text
        message_label = QLabel(self.message_data.get('content', ''))
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #ffffff; font-size: 13px; line-height: 1.4;")
        content_layout.addWidget(message_label)
        
        layout.addLayout(content_layout, 1)
        
        # Set background
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)


class VoiceChannelWidget(QWidget):
    """Voice channel widget with participant list and controls."""
    
    def __init__(self, channel_data):
        super().__init__()
        self.channel_data = channel_data
        self.voice_manager = VoiceChatManager()
        self.participants = []  # List of users in the voice channel
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the voice channel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Channel header
        header_layout = QHBoxLayout()
        
        # Voice icon
        voice_icon = QLabel("🔊")
        voice_icon.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(voice_icon)
        
        # Channel info
        info_layout = QVBoxLayout()
        channel_name = QLabel(self.channel_data.get('name', 'Voice Channel'))
        channel_name.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        
        self.participant_count_label = QLabel("0 participants")
        self.participant_count_label.setStyleSheet("color: #888888; font-size: 12px;")
        
        info_layout.addWidget(channel_name)
        info_layout.addWidget(self.participant_count_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Participants list
        self.participants_list = QListWidget()
        self.participants_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #2d2d2d;
                border-radius: 6px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #252525;
            }
        """)
        layout.addWidget(self.participants_list)
        
        # Add sample participants based on channel
        self.add_sample_participants()
        
        # Voice controls
        self.setup_voice_controls()
    
    def setup_voice_controls(self):
        """Setup voice chat controls."""
        controls_layout = QHBoxLayout()
        
        # Mute button
        self.mute_button = QPushButton("🎤 Mute")
        self.mute_button.setCheckable(True)
        self.mute_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #e74c3c;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
        """)
        self.mute_button.toggled.connect(self.toggle_mute)
        controls_layout.addWidget(self.mute_button)
        
        # Deafen button
        self.deafen_button = QPushButton("🔊 Deafen")
        self.deafen_button.setCheckable(True)
        self.deafen_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #e74c3c;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
        """)
        self.deafen_button.toggled.connect(self.toggle_deafen)
        controls_layout.addWidget(self.deafen_button)
        
        # Volume slider
        volume_label = QLabel("Volume:")
        volume_label.setStyleSheet("color: #ffffff;")
        controls_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #2d2d2d;
                height: 8px;
                background: #1e1e1e;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)
        controls_layout.addWidget(self.volume_slider)
        
        # Voice Settings button
        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.settings_button.clicked.connect(self.open_voice_settings)
        controls_layout.addWidget(self.settings_button)
        
        # Join/Leave button
        self.join_button = QPushButton("Join Channel")
        self.join_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.join_button.clicked.connect(self.toggle_join_channel)
        controls_layout.addWidget(self.join_button)
        
        # Audio Level Meter
        self.audio_level_label = QLabel("🎤")
        self.audio_level_label.setStyleSheet("color: #666; font-size: 16px;")
        controls_layout.addWidget(self.audio_level_label)
        
        self.layout().addLayout(controls_layout)
    
    def toggle_mute(self, muted):
        """Toggle microphone mute."""
        if muted:
            self.mute_button.setText("🔇 Muted")
            # Implement mute logic
        else:
            self.mute_button.setText("🎤 Mute")
            # Implement unmute logic
    
    def toggle_deafen(self, deafened):
        """Toggle audio deafen."""
        if deafened:
            self.deafen_button.setText("🔇 Deafened")
            # Implement deafen logic
        else:
            self.deafen_button.setText("🔊 Deafen")
            # Implement undeafen logic
    
    def join_voice_channel(self):
        """Join the voice channel."""
        try:
            if not PYAUDIO_AVAILABLE:
                logger.warning("Voice chat not available - pyaudio not installed")
                # Show user-friendly message
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Voice Chat", 
                                      "Voice chat requires pyaudio to be installed.\n\nThis is a demo feature - voice chat will be available in future updates.")
                return
            
            # Ensure voice server is running
            if VOICE_COMPONENTS_AVAILABLE and not is_voice_server_running():
                try:
                    start_voice_server()
                    logger.info("Voice server started for voice chat")
                except Exception as e:
                    logger.error(f"Failed to start voice server: {e}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Voice Chat Error", 
                                      f"Failed to start voice server: {str(e)}")
                    return
                
            # Start voice chat connection
            server_url = "ws://localhost:8080"
            channel_id = self.channel_data.get('id', '')
            
            self.voice_manager.start_voice_chat(server_url, channel_id)
            
            # Connect audio level signal
            if hasattr(self.voice_manager, 'audio_level_changed'):
                self.voice_manager.audio_level_changed.connect(self.update_audio_level)
            
            logger.info(f"Successfully joined voice channel: {channel_id}")
            
            # Update UI
            self.join_button.setText("Leave Channel")
            self.join_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}")
            # Show error to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Voice Chat Error", 
                              f"Failed to join voice channel: {str(e)}")
    
    def add_sample_participants(self):
        """Add sample participants to the voice channel."""
        # Start with empty participants list
        self.participants = []
        self.update_participants_list()
        self.update_participant_count()
    
    def update_participants_list(self):
        """Update the participants list display."""
        self.participants_list.clear()
        
        for participant in self.participants:
            # Create participant item with status indicators
            status_icon = "🔊" if participant['status'] == 'speaking' else "🟢" if participant['status'] == 'online' else "🟡"
            mute_icon = "🔇" if participant['muted'] else ""
            
            display_name = f"{status_icon} {participant['name']} {mute_icon}".strip()
            item = QListWidgetItem(display_name)
            
            # Set color based on status
            if participant['status'] == 'speaking':
                item.setForeground(QColor('#3498db'))  # TrackPro blue for speaking
            elif participant['muted']:
                item.setForeground(QColor('#888888'))  # Gray for muted
            else:
                item.setForeground(QColor('#ffffff'))  # White for normal
            
            self.participants_list.addItem(item)
    
    def update_participant_count(self):
        """Update the participant count display."""
        count = len(self.participants)
        if hasattr(self, 'participant_count_label'):
            self.participant_count_label.setText(f"{count} participants")
    
    def toggle_join_channel(self):
        """Toggle joining/leaving the voice channel."""
        if self.join_button.text() == "Join Channel":
            self.join_voice_channel()
            self.join_button.setText("Leave Channel")
            self.join_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
        else:
            self.leave_voice_channel()
            self.join_button.setText("Join Channel")
            self.join_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
    
    def leave_voice_channel(self):
        """Leave the voice channel."""
        self.voice_manager.stop_voice_chat()
    
    def open_voice_settings(self):
        """Open voice settings dialog."""
        if not VOICE_COMPONENTS_AVAILABLE:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Voice Settings", 
                                  "Voice settings require additional components.\n\n"
                                  "Please ensure pyaudio and numpy are installed for full voice chat functionality.")
            return
            
        try:
            dialog = VoiceSettingsDialog(self)
            dialog.settings_changed.connect(self.on_voice_settings_changed)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to open voice settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to open voice settings: {str(e)}")
    
    def on_voice_settings_changed(self, settings: dict):
        """Handle voice settings changes."""
        try:
            # Update voice manager settings
            if hasattr(self, 'voice_manager') and self.voice_manager:
                self.voice_manager.update_voice_settings(settings)
                logger.info("Voice settings updated successfully")
        except Exception as e:
            logger.error(f"Failed to update voice settings: {e}")
    
    def update_audio_level(self, level: float):
        """Update audio level meter display."""
        try:
            # Convert level (0-1) to visual indicator
            if level > 0.7:
                self.audio_level_label.setText("🔴")  # High level
                self.audio_level_label.setStyleSheet("color: #ff4444; font-size: 16px;")
            elif level > 0.3:
                self.audio_level_label.setText("🟡")  # Medium level
                self.audio_level_label.setStyleSheet("color: #ffaa00; font-size: 16px;")
            elif level > 0.1:
                self.audio_level_label.setText("🟢")  # Low level
                self.audio_level_label.setStyleSheet("color: #44ff44; font-size: 16px;")
            else:
                self.audio_level_label.setText("🎤")  # No audio
                self.audio_level_label.setStyleSheet("color: #666; font-size: 16px;")
        except Exception as e:
            logger.error(f"Failed to update audio level: {e}")


class ChatChannelWidget(QWidget):
    """Chat channel widget with message list and input."""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self, channel_data):
        super().__init__()
        self.channel_data = channel_data
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the chat channel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Channel header
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-bottom: 1px solid #2d2d2d;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 16)
        
        # Channel icon and name
        channel_icon = QLabel("#")
        channel_icon.setStyleSheet("color: #888888; font-size: 20px; font-weight: bold;")
        
        channel_name = QLabel(self.channel_data.get('name', 'general'))
        channel_name.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        
        header_layout.addWidget(channel_icon)
        header_layout.addWidget(channel_name)
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
        # Messages area
        self.messages_list = QListWidget()
        self.messages_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
            }
        """)
        layout.addWidget(self.messages_list)
        
        # Message input area
        input_widget = QWidget()
        input_widget.setFixedHeight(80)
        input_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-top: 1px solid #2d2d2d;
            }
        """)
        
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(16, 16, 16, 16)
        
        # Message input
        self.message_input = QLineEdit()
        self.message_input.setFixedHeight(40)
        self.message_input.setPlaceholderText("Message #general")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #2d2d2d;
                border-radius: 4px;
                color: #ffffff;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        
        layout.addWidget(input_widget)
    
    def send_message(self):
        """Send a message."""
        text = self.message_input.text().strip()
        if text:
            self.message_sent.emit(text)
            self.message_input.clear()
    
    def add_message(self, message_data):
        """Add a message to the chat."""
        try:
            message_widget = ChatMessageWidget(message_data)
            item = QListWidgetItem()
            item.setSizeHint(message_widget.sizeHint())
            
            self.messages_list.addItem(item)
            self.messages_list.setItemWidget(item, message_widget)
            
            # Scroll to bottom
            self.messages_list.scrollToBottom()
        except Exception as e:
            logger.error(f"Error adding message to chat: {e}")


class CommunityPage(BasePage):
    """Community page with Discord-inspired design and voice chat."""
    
    def __init__(self, global_managers=None):
        try:
            super().__init__("community", global_managers)
            self.current_channel = None
            self.voice_channels = {}
            self.chat_history = {}  # Store chat messages for each channel
            
            # Initialize community manager
            try:
                from ....community.community_manager import CommunityManager
                self.community_manager = CommunityManager()
                
                # Connect signals
                self.community_manager.message_received.connect(self.on_message_received)
                self.community_manager.user_joined_channel.connect(self.on_user_joined_channel)
                self.community_manager.user_left_channel.connect(self.on_user_left_channel)
                self.community_manager.user_status_changed.connect(self.on_user_status_changed)
                
                # Set current user
                self.set_current_user()
                
            except Exception as e:
                logger.error(f"Failed to initialize community manager: {e}")
                self.community_manager = None
            
            self.setup_ui()
            logger.info("✅ CommunityPage initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize CommunityPage: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            raise
    
    def setup_ui(self):
        """Setup the community page layout."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Server list (left sidebar)
        self.create_server_list(layout)
        
        # Main content area
        self.create_main_content(layout)
        
        self.setLayout(layout)
    
    def create_server_list(self, parent_layout):
        """Create the server/channel list sidebar."""
        server_widget = QWidget()
        server_widget.setFixedWidth(240)
        server_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-right: 1px solid #2d2d2d;
            }
        """)
        
        server_layout = QVBoxLayout(server_widget)
        server_layout.setContentsMargins(0, 0, 0, 0)
        server_layout.setSpacing(0)
        
        # Server header
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-bottom: 1px solid #2d2d2d;
            }
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 16)
        
        server_name = QLabel("TrackPro Community")
        server_name.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(server_name)
        
        server_layout.addWidget(header_widget)
        
        # Create scroll area for channels and private messages
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)
        
        # Voice channels section
        voice_header = QLabel("Voice Channels")
        voice_header.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            font-weight: bold; 
            padding: 8px 16px 4px 16px;
            background-color: #1e1e1e;
        """)
        scroll_layout.addWidget(voice_header)
        
        # Voice channels list
        self.voice_channels_list = QListWidget()
        self.voice_channels_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 8px 16px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #252525;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
        """)
        scroll_layout.addWidget(self.voice_channels_list)
        
        # Text channels section
        text_header = QLabel("Text Channels")
        text_header.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            font-weight: bold; 
            padding: 8px 16px 4px 16px;
            background-color: #1e1e1e;
        """)
        scroll_layout.addWidget(text_header)
        
        # Text channels list
        self.channel_list = QListWidget()
        self.channel_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 8px 16px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #252525;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
        """)
        scroll_layout.addWidget(self.channel_list)
        
        # Private messages section
        private_header = QLabel("PRIVATE MESSAGES")
        private_header.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            font-weight: bold; 
            padding: 8px 16px 4px 16px;
            background-color: #1e1e1e;
        """)
        scroll_layout.addWidget(private_header)
        
        # New Private Message button
        self.new_private_message_btn = QPushButton("+ New Private Message")
        self.new_private_message_btn.setStyleSheet("""
            QPushButton {
                background-color: #3ba55c;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                margin: 4px 16px;
            }
            QPushButton:hover {
                background-color: #2d7d46;
            }
            QPushButton:pressed {
                background-color: #1f5f35;
            }
        """)
        self.new_private_message_btn.clicked.connect(self.on_new_private_message_clicked)
        scroll_layout.addWidget(self.new_private_message_btn)
        
        # Private messages list
        self.private_messages_list = QListWidget()
        self.private_messages_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 0px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #252525;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
        """)
        scroll_layout.addWidget(self.private_messages_list)
        
        scroll_area.setWidget(scroll_content)
        server_layout.addWidget(scroll_area)
        
        # Load channels and private messages
        self.load_channels_from_database()
        self.load_private_messages()
        
        self.channel_list.itemClicked.connect(self.on_channel_selected)
        self.voice_channels_list.itemClicked.connect(self.on_channel_selected)
        self.private_messages_list.itemClicked.connect(self.on_private_message_selected)
        
        parent_layout.addWidget(server_widget)
    
    def create_main_content(self, parent_layout):
        """Create the main content area."""
        self.content_stack = QWidget()
        self.content_stack.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        # Don't show any channel by default - let auto-selection handle it
        # self.show_channel("general")  # This was causing the UUID error
        
        parent_layout.addWidget(self.content_stack, 1)
    

    
    def on_channel_selected(self, item):
        """Handle channel selection."""
        logger.info(f"🎯 Channel selected: {item.text()}")
        
        try:
            channel_data = item.data(Qt.ItemDataRole.UserRole)
            if channel_data:
                logger.info(f"📋 Channel data: {channel_data}")
                
                # Cleanup previous voice channel if switching from voice to voice
                if self.current_channel and self.current_channel.startswith('voice'):
                    logger.info(f"🔊 Cleaning up previous voice channel: {self.current_channel}")
                    if hasattr(self, 'voice_channels') and self.current_channel in self.voice_channels:
                        voice_widget = self.voice_channels[self.current_channel]
                        if hasattr(voice_widget, 'leave_voice_channel'):
                            try:
                                voice_widget.leave_voice_channel()
                                logger.info("✅ Successfully left voice channel")
                            except Exception as e:
                                logger.error(f"❌ Error leaving voice channel: {e}")
                
                self.current_channel = channel_data['id']
                logger.info(f"🔄 Current channel set to: {self.current_channel}")
                self.show_channel(channel_data['id'])
            else:
                logger.warning("⚠️ No channel data found in item")
        except Exception as e:
            logger.error(f"❌ Error selecting channel: {e}")
            # Don't let the error crash the application
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def get_channel_name(self, channel_id):
        """Get the friendly name for a channel ID."""
        try:
            if not self.community_manager:
                return channel_id
            
            # Get all channels and find the matching one
            channels = self.community_manager.get_channels()
            for channel in channels:
                if channel['channel_id'] == channel_id:
                    return channel['name']
            
            # Fallback to channel_id if not found
            return channel_id
            
        except Exception as e:
            logger.error(f"Error getting channel name for {channel_id}: {e}")
            return channel_id
    
    def show_channel(self, channel_id):
        """Show a specific channel."""
        channel_name = self.get_channel_name(channel_id)
        logger.info(f"🔄 Switching to channel: {channel_name} ({channel_id})")
        
        try:
            # Create a completely new content widget each time
            logger.info("🔄 Creating new content widget")
            new_content = QWidget()
            new_content.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                }
            """)
            
            # Create new layout
            logger.info("🏗️ Creating new QVBoxLayout")
            layout = QVBoxLayout(new_content)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            logger.info("✅ New layout created successfully")
            
            # Replace the old content_stack with the new one
            if hasattr(self, 'content_stack') and self.content_stack:
                logger.info("🔄 Replacing old content_stack")
                # Find the content_stack in the parent layout and replace it
                parent_layout = self.layout()
                if parent_layout:
                    for i in range(parent_layout.count()):
                        item = parent_layout.itemAt(i)
                        if item.widget() == self.content_stack:
                            logger.info("🗑️ Removing old content_stack from parent layout")
                            # Store the stretch factor
                            stretch = parent_layout.stretch(i)
                            parent_layout.removeItem(item)
                            self.content_stack.setParent(None)
                            self.content_stack.deleteLater()  # Properly delete the old widget
                            
                            # Add the new content widget to the parent layout with same stretch
                            parent_layout.addWidget(new_content, stretch)
                            logger.info("✅ Added new content widget to parent layout")
                            break
                else:
                    logger.warning("⚠️ No parent layout found")
            
            # Update the content_stack reference
            self.content_stack = new_content
            
        except Exception as e:
            logger.error(f"❌ Error creating new content widget: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            # Fallback: create a simple widget
            logger.info("🔄 Creating fallback content widget")
            self.content_stack = QWidget()
            self.content_stack.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                }
            """)
            layout = QVBoxLayout(self.content_stack)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        
        try:
            if channel_id.startswith('voice'):
                # Voice channel
                channel_name = self.get_channel_name(channel_id)
                logger.info(f"🔊 Creating voice channel widget for: {channel_name} ({channel_id})")
                voice_widget = VoiceChannelWidget({
                    'id': channel_id,
                    'name': channel_name,
                    'participant_count': 0
                })
                logger.info(f"✅ Voice channel widget created, adding to layout")
                layout.addWidget(voice_widget)
                
                # Track voice channels for cleanup
                if not hasattr(self, 'voice_channels'):
                    self.voice_channels = {}
                self.voice_channels[channel_id] = voice_widget
                logger.info(f"✅ Voice channel widget created and tracked successfully")
                
                # Connect voice error signals
                if hasattr(voice_widget, 'voice_manager'):
                    voice_widget.voice_manager.voice_error.connect(self.on_voice_error)
            else:
                # Text channel
                channel_name = self.get_channel_name(channel_id)
                logger.info(f"💬 Creating chat channel widget for: {channel_name} ({channel_id})")
                chat_widget = ChatChannelWidget({
                    'id': channel_id,
                    'name': channel_name
                })
                chat_widget.message_sent.connect(self.on_message_sent)
                logger.info(f"✅ Chat channel widget created, adding to layout")
                layout.addWidget(chat_widget)
                
                # Store reference to current chat widget for real-time updates
                self.current_chat_widget = chat_widget
                
                # Update input field state based on authentication
                self.update_input_field_state()
                
                # Load messages for this channel
                if self.community_manager:
                    try:
                        messages = self.community_manager.get_messages(channel_id)
                        for message in messages:
                            chat_widget.add_message(message)
                        logger.info(f"✅ Loaded {len(messages)} messages for channel {channel_id}")
                    except Exception as e:
                        logger.error(f"Error loading messages for channel {channel_id}: {e}")
                else:
                    # Fallback: load from local chat history
                    if channel_id in self.chat_history:
                        for message in self.chat_history[channel_id]:
                            chat_widget.add_message(message)
                        logger.info(f"✅ Loaded {len(self.chat_history[channel_id])} local messages for channel {channel_id}")
                    else:
                        # Initialize empty chat history for this channel
                        self.chat_history[channel_id] = []
                        logger.info(f"✅ Initialized empty chat history for channel {channel_id}")
        except Exception as e:
            logger.error(f"❌ Error creating channel widget: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def get_channel_default_messages(self, channel_id):
        """Get default messages for each channel."""
        # Start with empty messages for all channels
        return []
    
    def on_message_sent(self, message_text):
        """Handle message sent."""
        logger.info(f"Message sent: {message_text}")
        
        if not self.current_channel:
            logger.warning("No current channel selected")
            return
        
        # Check if user is authenticated before allowing message sending
        try:
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            
            if not user or not user.is_authenticated:
                # Try to get user from Supabase session directly
                from trackpro.database.supabase_client import get_supabase_client
                client = get_supabase_client()
                if client and hasattr(client, 'auth') and client.auth.get_session():
                    session = client.auth.get_session()
                    if session and hasattr(session, 'user'):
                        logger.info("User authenticated via Supabase session")
                    else:
                        logger.warning("User not authenticated - cannot send message")
                        # Show error message to user
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(
                            self, 
                            "Authentication Required", 
                            "You must be logged in to send messages in the community."
                        )
                        return
                else:
                    logger.warning("User not authenticated - cannot send message")
                    # Show error message to user
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self, 
                        "Authentication Required", 
                        "You must be logged in to send messages in the community."
                    )
                    return
            else:
                logger.info(f"User authenticated: {user.email}")
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            # Show error message to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Authentication Error", 
                "Unable to verify authentication. Please log in to send messages."
            )
            return
        
        # Ensure current user is set before sending message
        self.refresh_user_state()
        
        # Send message to database if community manager is available
        if self.community_manager:
            try:
                success = self.community_manager.send_message(self.current_channel, message_text)
                
                if not success:
                    logger.error("Failed to send message to database")
                    # Show error to user
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self, 
                        "Message Error", 
                        "Failed to send message. Please try again."
                    )
            except Exception as e:
                logger.error(f"Error sending message to database: {e}")
                # Show error to user
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, 
                    "Message Error", 
                    "Failed to send message. Please try again."
                )
        else:
            logger.warning("Community manager not available")
            # Show error to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Connection Error", 
                "Unable to connect to community server. Please try again later."
            )
    
    def _add_message_locally(self, message_text):
        """Add message to local storage as fallback."""
        try:
            # Get current user info - simplified approach
            user_name = "You"  # Default fallback
            
            # Try to get user from user manager first
            try:
                from trackpro.auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    user_name = user.name or user.email or "You"
                    logger.info(f"Using user name from user manager: {user_name}")
                else:
                    # Try Supabase session directly
                    from trackpro.database.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    if client and hasattr(client, 'auth') and client.auth.get_session():
                        session = client.auth.get_session()
                        if session and hasattr(session, 'user'):
                            user_data = session.user
                            user_name = user_data.user_metadata.get('name', user_data.email) or "You"
                            logger.info(f"Using user name from Supabase session: {user_name}")
            except Exception as e:
                logger.debug(f"Could not get user name: {e}")
                user_name = "You"
            
            # Create new message with proper structure that matches database format
            new_message = {
                'sender_name': user_name,
                'content': message_text,
                'created_at': datetime.now().isoformat(),
                'message_type': 'text'
            }
            
            logger.info(f"Created local message with sender_name: {user_name}")
            
            # Save to chat history
            if self.current_channel not in self.chat_history:
                self.chat_history[self.current_channel] = []
            
            self.chat_history[self.current_channel].append(new_message)
            
            # Add to current chat widget
            self.add_message_to_ui(new_message)
            
        except Exception as e:
            logger.error(f"Error adding message locally: {e}")
    
    def init_page(self):
        """Initialize the page."""
        pass
    
    def update_input_field_state(self):
        """Update the message input field state based on authentication."""
        try:
            # Check if user is authenticated
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            
            is_authenticated = False
            if user and user.is_authenticated:
                is_authenticated = True
            else:
                # Try to get user from Supabase session directly
                try:
                    from trackpro.database.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    if client and hasattr(client, 'auth') and client.auth.get_session():
                        session = client.auth.get_session()
                        if session and hasattr(session, 'user'):
                            is_authenticated = True
                except Exception as e:
                    logger.debug(f"Could not check Supabase session: {e}")
            
            # Update input field state
            if hasattr(self, 'current_chat_widget') and self.current_chat_widget:
                if hasattr(self.current_chat_widget, 'message_input'):
                    input_field = self.current_chat_widget.message_input
                    if is_authenticated:
                        input_field.setEnabled(True)
                        input_field.setPlaceholderText(f"Message #{self.get_channel_name(self.current_channel) if self.current_channel else 'general'}")
                        input_field.setStyleSheet("""
                            QLineEdit {
                                background-color: #2d2d2d;
                                border: 1px solid #2d2d2d;
                                border-radius: 4px;
                                color: #ffffff;
                                padding: 8px;
                                font-size: 13px;
                            }
                            QLineEdit:focus {
                                border: 1px solid #3498db;
                            }
                        """)
                    else:
                        input_field.setEnabled(False)
                        input_field.setPlaceholderText("Please log in to send messages")
                        input_field.setStyleSheet("""
                            QLineEdit {
                                background-color: #1a1a1a;
                                border: 1px solid #2d2d2d;
                                border-radius: 4px;
                                color: #666666;
                                padding: 8px;
                                font-size: 13px;
                            }
                        """)
                    logger.info(f"Updated input field state - authenticated: {is_authenticated}")
        except Exception as e:
            logger.error(f"Error updating input field state: {e}")
    
    def on_page_activated(self):
        """Called when page is activated."""
        # Refresh user state and set current user for community manager
        self.refresh_user_state()
        
        # Update input field state based on authentication
        self.update_input_field_state()
        
        # Start voice server if not running
        if VOICE_COMPONENTS_AVAILABLE and not is_voice_server_running():
            try:
                start_voice_server()
                logger.info("Voice server started automatically")
            except Exception as e:
                logger.error(f"Failed to start voice server: {e}")
        
        # Load channels and messages
        self.load_channels_from_database()
        self.load_private_messages()
    
    def refresh_user_state(self):
        """Refresh user authentication state and set current user."""
        try:
            # Force refresh of user manager state
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            
            if user and user.is_authenticated:
                logger.info(f"User authenticated: {user.email}")
            else:
                logger.info("User not authenticated or user manager not ready")
            
            # Set current user in community manager
            self.set_current_user()
            
            # Update input field state based on new authentication state
            self.update_input_field_state()
            
        except Exception as e:
            logger.warning(f"Failed to refresh user state: {e}")
    
    def on_voice_error(self, error_message):
        """Handle voice chat errors."""
        logger.error(f"Voice chat error: {error_message}")
        # You could show a user-friendly message here if needed
    
    def cleanup(self):
        """Cleanup resources."""
        # Stop any active voice connections
        try:
            for voice_widget in self.voice_channels.values():
                if hasattr(voice_widget, 'leave_voice_channel'):
                    try:
                        voice_widget.leave_voice_channel()
                    except Exception as e:
                        logger.error(f"Error leaving voice channel: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Cleanup real-time subscriptions
        try:
            if hasattr(self, 'community_manager') and self.community_manager:
                if hasattr(self.community_manager, 'client') and self.community_manager.client:
                    # Unsubscribe from real-time updates
                    self.community_manager.client.remove_all_subscriptions()
                    logger.info("✅ Cleaned up real-time subscriptions")
        except Exception as e:
            logger.error(f"Error cleaning up real-time subscriptions: {e}")
    
    def set_current_user(self):
        """Set the current authenticated user in the community manager."""
        try:
            if not self.community_manager:
                logger.warning("Community manager not available")
                return
                
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            
            if user is None:
                # Try to get user from Supabase session directly
                try:
                    from trackpro.database.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    if client and hasattr(client, 'auth') and client.auth.get_session():
                        session = client.auth.get_session()
                        if session and hasattr(session, 'user'):
                            user_data = session.user
                            # Create a temporary user object
                            from trackpro.auth.user_manager import User
                            temp_user = User(
                                id=user_data.id,
                                email=user_data.email,
                                name=user_data.user_metadata.get('name', user_data.email),
                                is_authenticated=True
                            )
                            self.community_manager.set_current_user(temp_user.id)
                            logger.info(f"Set current user from Supabase session: {temp_user.email}")
                            return
                except Exception as e:
                    logger.debug(f"Could not get user from Supabase session: {e}")
                
                # User manager not ready yet - skip setting current user
                logger.info("🔍 User manager not ready yet - skipping current user setting")
                return
                
            if user and user.is_authenticated:
                self.community_manager.set_current_user(user.id)
                logger.info(f"Set current user: {user.email}")
            else:
                logger.warning("User not authenticated")
                
        except Exception as e:
            logger.warning(f"Failed to set current user: {e}")
    
    def on_message_received(self, message_data):
        """Handle new message received from database."""
        channel_id = message_data.get('channel_id')
        logger.info(f"🔄 Real-time message received for channel: {channel_id}")
        
        # Initialize chat history for this channel if it doesn't exist
        if channel_id and channel_id not in self.chat_history:
            self.chat_history[channel_id] = []
        
        if channel_id:
            # Add message to chat history
            self.chat_history[channel_id].append(message_data)
            logger.info(f"✅ Added message to chat history for channel: {channel_id}")
            
            # Update UI if this channel is currently displayed
            if self.current_channel == channel_id:
                logger.info(f"🔄 Updating UI for current channel: {channel_id}")
                self.add_message_to_ui(message_data)
            else:
                logger.info(f"📝 Message received for different channel (current: {self.current_channel}, message: {channel_id})")
    
    def on_user_joined_channel(self, channel_id, user_data):
        """Handle user joining a voice channel."""
        if channel_id in self.voice_channels:
            voice_widget = self.voice_channels[channel_id]
            voice_widget.add_participant(user_data)
    
    def on_user_left_channel(self, channel_id, user_id):
        """Handle user leaving a voice channel."""
        if channel_id in self.voice_channels:
            voice_widget = self.voice_channels[channel_id]
            voice_widget.remove_participant(user_id)
    
    def on_user_status_changed(self, channel_id, user_id, status_data):
        """Handle user status change in voice channel."""
        if channel_id in self.voice_channels:
            voice_widget = self.voice_channels[channel_id]
            voice_widget.update_participant_status(user_id, status_data)
    
    def add_message_to_ui(self, message_data):
        """Add a message to the current chat UI."""
        try:
            if hasattr(self, 'current_chat_widget') and self.current_chat_widget:
                logger.info(f"📨 Adding message to UI: {message_data.get('content', '')[:50]}...")
                logger.info(f"📨 Message sender_name: {message_data.get('sender_name', 'NOT_FOUND')}")
                logger.info(f"📨 Message user_profiles: {message_data.get('user_profiles', 'NOT_FOUND')}")
                self.current_chat_widget.add_message(message_data)
                logger.info("✅ Message added to UI successfully")
            else:
                logger.warning("⚠️ No current chat widget available for real-time message")
        except Exception as e:
            logger.error(f"❌ Error adding message to UI: {e}")
    
    def load_channels_from_database(self):
        """Load channels from database instead of hardcoded list."""
        try:
            if not self.community_manager:
                logger.warning("Community manager not available, using fallback channels")
                self.load_fallback_channels()
                return
                
            channels = self.community_manager.get_channels()
            self.channel_list.clear()
            self.voice_channels_list.clear()
            
            for channel in channels:
                channel_name = channel['name']
                channel_type = channel['channel_type']
                
                # Format display name
                if channel_type == 'text':
                    display_name = f"# {channel_name}"
                    target_list = self.channel_list
                else:
                    display_name = f"🔊 {channel_name}"
                    target_list = self.voice_channels_list
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'id': channel['channel_id'],
                    'name': channel_name,
                    'type': channel_type
                })
                target_list.addItem(item)
            
            # Auto-select the first text channel if no channel is currently selected
            if self.channel_list.count() > 0 and not self.current_channel:
                first_item = self.channel_list.item(0)
                if first_item:
                    channel_data = first_item.data(Qt.ItemDataRole.UserRole)
                    if channel_data and channel_data['type'] == 'text':
                        self.current_channel = channel_data['id']
                        self.channel_list.setCurrentItem(first_item)
                        self.show_channel(channel_data['id'])
                        logger.info(f"Auto-selected first channel: {channel_data['id']}")
                
        except Exception as e:
            logger.error(f"Error loading channels from database: {e}")
            # Fallback to hardcoded channels
            self.load_fallback_channels()
    
    def load_fallback_channels(self):
        """Load fallback channels when database is unavailable."""
        # Text channels
        text_channels = [
            ("# general", "fallback-general", "text"),
            ("# racing", "fallback-racing", "text"),
            ("# tech-support", "fallback-tech-support", "text"),
            ("# events", "fallback-events", "text")
        ]
        
        for channel_name, channel_id, channel_type in text_channels:
            item = QListWidgetItem(channel_name)
            item.setData(Qt.ItemDataRole.UserRole, {
                'id': channel_id,
                'name': channel_name.replace('# ', '').replace('🔊 ', ''),
                'type': channel_type
            })
            self.channel_list.addItem(item)
        
        # Voice channels
        voice_channels = [
            ("🔊 Voice General", "fallback-voice-general", "voice"),
            ("🔊 Voice Racing", "fallback-voice-racing", "voice")
        ]
        
        for channel_name, channel_id, channel_type in voice_channels:
            item = QListWidgetItem(channel_name)
            item.setData(Qt.ItemDataRole.UserRole, {
                'id': channel_id,
                'name': channel_name.replace('# ', '').replace('🔊 ', ''),
                'type': channel_type
            })
            self.voice_channels_list.addItem(item)
        
        # Auto-select the first text channel if no channel is currently selected
        if self.channel_list.count() > 0 and not self.current_channel:
            first_item = self.channel_list.item(0)
            if first_item:
                channel_data = first_item.data(Qt.ItemDataRole.UserRole)
                if channel_data and channel_data['type'] == 'text':
                    self.current_channel = channel_data['id']
                    self.channel_list.setCurrentItem(first_item)
                    self.show_channel(channel_data['id'])
                    logger.info(f"Auto-selected first fallback channel: {channel_data['id']}")
    
    def load_private_messages(self):
        """Load private messages/conversations."""
        try:
            if not self.community_manager:
                logger.warning("Community manager not available, using fallback private messages")
                self.load_fallback_private_messages()
                return
                
            conversations = self.community_manager.get_private_conversations()
            self.private_messages_list.clear()
            
            for conversation in conversations:
                # Create conversation list item widget
                conversation_widget = PrivateConversationListItem(conversation)
                conversation_widget.conversation_selected.connect(self.on_private_conversation_selected)
                
                item = QListWidgetItem()
                item.setSizeHint(conversation_widget.sizeHint())
                
                self.private_messages_list.addItem(item)
                self.private_messages_list.setItemWidget(item, conversation_widget)
                
        except Exception as e:
            logger.error(f"Error loading private messages: {e}")
            self.load_fallback_private_messages()
    
    def load_fallback_private_messages(self):
        """Load fallback private messages when database is unavailable."""
        # For now, we'll show a placeholder message
        placeholder_item = QListWidgetItem("No private messages yet")
        # Note: QListWidgetItem doesn't have setStyleSheet, styling is done via the widget
        self.private_messages_list.addItem(placeholder_item)
    
    def on_private_message_selected(self, item):
        """Handle private message selection."""
        logger.info(f"Private message selected: {item.text()}")
    
    def on_private_conversation_selected(self, conversation_id):
        """Handle private conversation selection."""
        logger.info(f"Private conversation selected: {conversation_id}")
        
        try:
            # Get conversation data
            if not self.community_manager:
                logger.warning("Community manager not available")
                return
            
            # Get conversation details and messages
            messages = self.community_manager.get_private_messages(conversation_id)
            
            # Create conversation widget
            # Get conversation data from the list
            conversation_data = None
            for i in range(self.private_messages_list.count()):
                item = self.private_messages_list.item(i)
                widget = self.private_messages_list.itemWidget(item)
                if hasattr(widget, 'conversation_id') and widget.conversation_id == conversation_id:
                    conversation_data = widget.conversation_data
                    break
            
            if not conversation_data:
                logger.warning(f"Conversation data not found for ID: {conversation_id}")
                return
            
            conversation_widget = PrivateConversationWidget(conversation_data)
            conversation_widget.message_sent.connect(lambda text: self.on_private_message_sent(conversation_id, text))
            
            # Add messages to the conversation
            current_user_id = None
            try:
                from ...auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    current_user_id = user.id
            except Exception as e:
                logger.debug(f"Could not get current user: {e}")
            
            for message in messages:
                is_own_message = current_user_id and message.get('user_profiles', {}).get('user_id') == current_user_id
                conversation_widget.add_message(message, is_own_message)
            
            # Show the conversation
            self.show_private_conversation(conversation_widget)
            
        except Exception as e:
            logger.error(f"Error showing private conversation: {e}")
    
    def on_private_message_sent(self, conversation_id, message_text):
        """Handle private message sent."""
        logger.info(f"Private message sent to conversation {conversation_id}: {message_text}")
        
        try:
            if not self.community_manager:
                logger.warning("Community manager not available")
                return
            
            # Send message to database
            success = self.community_manager.send_private_message(conversation_id, message_text)
            
            if success:
                logger.info("Private message sent successfully")
                # Refresh the private messages list
                self.load_private_messages()
            else:
                logger.error("Failed to send private message")
                
        except Exception as e:
            logger.error(f"Error sending private message: {e}")
    
    def on_new_private_message_clicked(self):
        """Handle new private message button click."""
        try:
            # Show a dialog to select a user to message
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("New Private Message")
            dialog.setFixedSize(400, 200)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #2f3136;
                    color: #dcddde;
                }
                QLabel {
                    color: #dcddde;
                    font-size: 14px;
                }
                QLineEdit {
                    background-color: #40444b;
                    border: 1px solid #202225;
                    border-radius: 4px;
                    color: #dcddde;
                    padding: 8px;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #5865f2;
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #4752c4;
                }
                QPushButton:disabled {
                    background-color: #4f545c;
                    color: #72767d;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Title
            title_label = QLabel("Enter username to start a private conversation:")
            layout.addWidget(title_label)
            
            # Username input
            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText("Enter username...")
            layout.addWidget(self.username_input)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            start_btn = QPushButton("Start Conversation")
            start_btn.clicked.connect(lambda: self.start_private_conversation(dialog))
            button_layout.addWidget(start_btn)
            
            layout.addLayout(button_layout)
            
            # Show dialog
            result = dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing new private message dialog: {e}")
    
    def start_private_conversation(self, dialog):
        """Start a new private conversation with the entered username."""
        try:
            username = self.username_input.text().strip()
            if not username:
                QMessageBox.warning(dialog, "Error", "Please enter a username.")
                return
            
            # Get user by username
            if not self.community_manager:
                QMessageBox.warning(dialog, "Error", "Community manager not available.")
                return
            
            # For now, we'll create a mock conversation
            # In a real implementation, you'd look up the user in the database
            conversation_id = self.community_manager.get_or_create_conversation(username)
            
            if conversation_id:
                dialog.accept()
                # Load and show the conversation
                self.on_private_conversation_selected(conversation_id)
            else:
                QMessageBox.warning(dialog, "Error", f"Could not find user '{username}' or create conversation.")
                
        except Exception as e:
            logger.error(f"Error starting private conversation: {e}")
            QMessageBox.critical(dialog, "Error", f"An error occurred: {str(e)}")
    
    def start_private_conversation_with_user(self, user_data):
        """Start a private conversation with a specific user."""
        try:
            if not self.community_manager:
                logger.error("Community manager not available")
                return
            
            user_id = user_data.get('user_id')
            if not user_id:
                logger.error("No user ID provided")
                return
            
            # Get or create conversation
            conversation_id = self.community_manager.get_or_create_conversation(user_id)
            
            if conversation_id:
                # Load and show the conversation
                self.on_private_conversation_selected(conversation_id)
            else:
                logger.error(f"Could not create conversation with user {user_id}")
                
        except Exception as e:
            logger.error(f"Error starting private conversation with user: {e}")
    
    def show_private_conversation(self, conversation_widget):
        """Show a private conversation in the main content area."""
        try:
            # Create a completely new content widget
            new_content = QWidget()
            new_content.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                }
            """)
            
            layout = QVBoxLayout(new_content)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # Replace the old content_stack with the new one
            if hasattr(self, 'content_stack') and self.content_stack:
                parent_layout = self.layout()
                if parent_layout:
                    for i in range(parent_layout.count()):
                        item = parent_layout.itemAt(i)
                        if item.widget() == self.content_stack:
                            stretch = parent_layout.stretch(i)
                            parent_layout.removeItem(item)
                            self.content_stack.setParent(None)
                            self.content_stack.deleteLater()
                            
                            parent_layout.addWidget(new_content, stretch)
                            break
            
            # Update the content_stack reference
            self.content_stack = new_content
            
            # Add the conversation widget
            layout.addWidget(conversation_widget)
            
        except Exception as e:
            logger.error(f"Error showing private conversation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}") 