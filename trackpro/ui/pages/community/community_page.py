"""Community page with Discord-inspired design and voice chat functionality."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame, 
    QSizePolicy, QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QSplitter, QTabWidget, QLineEdit, QComboBox, QSlider, QCheckBox
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

logger = logging.getLogger(__name__)

# Optional imports for voice chat functionality
PYAUDIO_AVAILABLE = False
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    logger.warning("pyaudio not available - voice chat functionality will be disabled")
except Exception as e:
    logger.warning(f"Error importing pyaudio: {e} - voice chat functionality will be disabled")

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
    
    def __init__(self):
        super().__init__()
        self.audio = None
        self.is_recording = False
        self.is_playing = False
        self.websocket = None
        self.voice_thread = None
        
        # Audio settings
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
            
        try:
            self.voice_thread = threading.Thread(
                target=self._run_voice_client,
                args=(server_url, channel_id)
            )
            self.voice_thread.daemon = True
            self.voice_thread.start()
        except Exception as e:
            self.voice_error.emit(f"Failed to start voice chat: {str(e)}")
    
    def _run_voice_client(self, server_url: str, channel_id: str):
        """Run voice client in separate thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._voice_client_loop(server_url, channel_id))
        except Exception as e:
            self.voice_error.emit(f"Voice client error: {str(e)}")
        finally:
            if 'loop' in locals():
                loop.close()
    
    async def _voice_client_loop(self, server_url: str, channel_id: str):
        """Voice client WebSocket loop."""
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
        """Start audio recording."""
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
        """Record audio and send to WebSocket."""
        while self.is_recording:
            try:
                data = self.stream_in.read(self.CHUNK)
                if self.websocket:
                    # Use the current event loop instead of asyncio.run
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
        """Start audio playback."""
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
        self.setup_ui()
    
    def create_avatar(self):
        """Create a circular avatar with user initials."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background
        name = self.message_data.get('sender_name', 'U')
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
        username_label = QLabel(self.message_data.get('sender_name', 'Unknown'))
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
                
            # Start voice chat connection
            self.voice_manager.start_voice_chat(
                server_url="ws://localhost:8080",  # Replace with your WebSocket server
                channel_id=self.channel_data.get('id', '')
            )
            logger.info(f"Successfully joined voice channel: {self.channel_data.get('id', '')}")
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}")
            # Show error to user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Voice Chat Error", 
                              f"Failed to join voice channel: {str(e)}\n\nVoice chat requires a WebSocket server running on localhost:8080")
    
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
                from ...community.community_manager import CommunityManager
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
        
        # Channel list
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
        
        # Load channels from database
        self.load_channels_from_database()
        
        self.channel_list.itemClicked.connect(self.on_channel_selected)
        server_layout.addWidget(self.channel_list)
        
        parent_layout.addWidget(server_widget)
    
    def create_main_content(self, parent_layout):
        """Create the main content area."""
        self.content_stack = QWidget()
        self.content_stack.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        # Default to general channel
        self.show_channel("general")
        
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
    
    def show_channel(self, channel_id):
        """Show a specific channel."""
        logger.info(f"🔄 Switching to channel: {channel_id}")
        
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
                logger.info(f"🔊 Creating voice channel widget for: {channel_id}")
                voice_widget = VoiceChannelWidget({
                    'id': channel_id,
                    'name': channel_id.replace('voice-', '').title(),
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
                logger.info(f"💬 Creating chat channel widget for: {channel_id}")
                chat_widget = ChatChannelWidget({
                    'id': channel_id,
                    'name': channel_id
                })
                chat_widget.message_sent.connect(self.on_message_sent)
                logger.info(f"✅ Chat channel widget created, adding to layout")
                layout.addWidget(chat_widget)
                
                # Load messages from database if community manager is available
                if self.community_manager:
                    try:
                        messages = self.community_manager.get_messages(channel_id)
                        self.chat_history[channel_id] = messages
                        
                        # Add messages to the chat widget
                        logger.info(f"📨 Adding {len(messages)} messages to chat")
                        for message in messages:
                            chat_widget.add_message(message)
                        logger.info(f"✅ Chat channel widget created and populated successfully")
                    except Exception as e:
                        logger.error(f"Error loading messages from database: {e}")
                        # Use empty messages list as fallback
                        self.chat_history[channel_id] = []
                else:
                    logger.warning("Community manager not available, using empty chat history")
                    self.chat_history[channel_id] = []
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
        
        # Send message to database if community manager is available
        if self.community_manager:
            try:
                success = self.community_manager.send_message(self.current_channel, message_text)
                
                if not success:
                    logger.error("Failed to send message to database")
                    # Fallback to local storage
                    self._add_message_locally(message_text)
            except Exception as e:
                logger.error(f"Error sending message to database: {e}")
                # Fallback to local storage
                self._add_message_locally(message_text)
        else:
            logger.warning("Community manager not available, using local storage")
            self._add_message_locally(message_text)
    
    def _add_message_locally(self, message_text):
        """Add message to local storage as fallback."""
        try:
            # Get current user info
            user_name = "You"  # Default for authenticated user
            try:
                from ...auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    user_name = user.name or "You"
            except Exception as e:
                logger.debug(f"Could not get user name: {e}")
            
            # Create new message
            new_message = {
                'sender_name': user_name,
                'content': message_text,
                'created_at': datetime.now().isoformat()
            }
            
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
    
    def on_page_activated(self):
        """Called when page is activated."""
        pass
    
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
    
    def set_current_user(self):
        """Set the current authenticated user in the community manager."""
        try:
            if not self.community_manager:
                logger.warning("Community manager not available")
                return
                
            from ...auth.user_manager import get_current_user
            user = get_current_user()
            if user and user.is_authenticated:
                self.community_manager.set_current_user(user.id)
        except Exception as e:
            logger.warning(f"Failed to set current user: {e}")
    
    def on_message_received(self, message_data):
        """Handle new message received from database."""
        channel_id = message_data.get('channel_id')
        if channel_id and channel_id in self.chat_history:
            # Add message to chat history
            self.chat_history[channel_id].append(message_data)
            
            # Update UI if this channel is currently displayed
            if self.current_channel == channel_id:
                self.add_message_to_ui(message_data)
    
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
        if hasattr(self, 'current_chat_widget') and self.current_chat_widget:
            self.current_chat_widget.add_message(message_data)
    
    def load_channels_from_database(self):
        """Load channels from database instead of hardcoded list."""
        try:
            if not self.community_manager:
                logger.warning("Community manager not available, using fallback channels")
                self.load_fallback_channels()
                return
                
            channels = self.community_manager.get_channels()
            self.channel_list.clear()
            
            for channel in channels:
                channel_name = channel['name']
                channel_type = channel['channel_type']
                
                # Format display name
                if channel_type == 'text':
                    display_name = f"# {channel_name}"
                else:
                    display_name = f"🔊 {channel_name}"
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'id': channel['channel_id'],
                    'name': channel_name,
                    'type': channel_type
                })
                self.channel_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading channels from database: {e}")
            # Fallback to hardcoded channels
            self.load_fallback_channels()
    
    def load_fallback_channels(self):
        """Load fallback channels when database is unavailable."""
        channels = [
            ("# general", "general", "text"),
            ("# racing", "racing", "text"),
            ("# tech-support", "tech-support", "text"),
            ("# events", "events", "text"),
            ("🔊 Voice General", "voice-general", "voice"),
            ("🔊 Voice Racing", "voice-racing", "voice")
        ]
        
        for channel_name, channel_id, channel_type in channels:
            item = QListWidgetItem(channel_name)
            item.setData(Qt.ItemDataRole.UserRole, {
                'id': channel_id,
                'name': channel_name.replace('# ', '').replace('🔊 ', ''),
                'type': channel_type
            })
            self.channel_list.addItem(item) 