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
import random
import time
import socket

from ...modern.shared.base_page import BasePage
from ....community.private_messaging_widget import PrivateConversationListItem, PrivateConversationWidget
logger = logging.getLogger(__name__)

# Import simple voice client
try:
    from trackpro.simple_voice_client import SimpleVoiceClient
    SIMPLE_VOICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Simple voice client not available: {e}")
    SIMPLE_VOICE_AVAILABLE = False

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

# Import voice server manager
try:
    from trackpro.voice_server_manager import start_voice_server, stop_voice_server, is_voice_server_running
    VOICE_SERVER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Voice server manager not available: {e}")
    VOICE_SERVER_AVAILABLE = False

# Import high-quality voice manager
try:
    from .high_quality_voice_manager import HighQualityVoiceManager
    from .voice_settings_dialog import VoiceSettingsDialog
    VOICE_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"High-quality voice manager not available: {e}")
    VOICE_COMPONENTS_AVAILABLE = False
    VoiceSettingsDialog = None  # Set to None so we can check for it

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
    user_speaking_start = pyqtSignal(str)  # Signal when user starts speaking
    user_speaking_stop = pyqtSignal(str)   # Signal when user stops speaking
    user_info_update = pyqtSignal(str, str)  # Signal for user info updates (user_id, user_name)
    
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
        try:
            if self.voice_thread and self.voice_thread.is_alive():
                logger.warning("Voice chat already running")
                return
            
            # Start voice client in separate thread
            self.voice_thread = threading.Thread(
                target=self._run_voice_client,
                args=(server_url, channel_id),
                daemon=True
            )
            self.voice_thread.start()
            
            logger.info(f"Voice chat started for channel: {channel_id}")
            
        except Exception as e:
            logger.error(f"Failed to start voice chat: {e}")
            self.voice_error.emit(f"Failed to start voice chat: {str(e)}")
    
    def update_voice_settings(self, settings: dict):
        """Update voice settings."""
        try:
            if self.use_high_quality and hasattr(self, 'voice_manager'):
                self.voice_manager.update_settings(settings)
                logger.info("Voice settings updated")
        except Exception as e:
            logger.error(f"Failed to update voice settings: {e}")
    
    def get_available_devices(self):
        """Get available audio devices."""
        if self.use_high_quality and hasattr(self, 'voice_manager'):
            return self.voice_manager.get_available_devices()
        return {'input': [], 'output': []}
    
    def _run_voice_client(self, server_url: str, channel_id: str):
        """Run voice client in separate thread (fallback)."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Store the loop for use in recording thread
            self._voice_loop = loop
            loop.run_until_complete(self._voice_client_loop(server_url, channel_id))
        except Exception as e:
            self.voice_error.emit(f"Voice client error: {str(e)}")
        finally:
            if 'loop' in locals():
                loop.close()
    
    async def _voice_client_loop(self, server_url: str, channel_id: str):
        """Voice client WebSocket loop (fallback)."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with websockets.connect(f"{server_url}/voice/{channel_id}", 
                                           ping_interval=20, 
                                           ping_timeout=10,
                                           close_timeout=5) as websocket:
                    self.websocket = websocket
                
                # Send user info to server
                try:
                    from trackpro.auth.user_manager import get_current_user
                    user = get_current_user()
                    if user and user.is_authenticated:
                        user_name = user.name or user.email or 'Unknown'
                    else:
                        user_name = 'Unknown'
                except Exception:
                    user_name = 'Unknown'
                
                # Send user info to server
                await websocket.send(json.dumps({
                    'type': 'user_info',
                    'user_name': user_name
                }))
                
                # Start audio recording
                self._start_recording()
                
                # Start audio playback
                self._start_playback()
                
                # Handle incoming voice data
                async for message in websocket:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    if message_type == 'voice_data':
                        self.voice_data_received.emit(bytes(data['audio']))
                        
                        # Handle speaking status
                        if data.get('speaking', False):
                            user_name = data.get('user_name', 'Unknown')
                            self.user_speaking_start.emit(user_name)
                        else:
                            user_name = data.get('user_name', 'Unknown')
                            self.user_speaking_stop.emit(user_name)
                            
                    elif message_type == 'user_joined':
                        self.user_joined_voice.emit(data['user_id'])
                        
                    elif message_type == 'user_left':
                        self.user_left_voice.emit(data['user_id'])
                        
                    elif message_type == 'user_speaking_start':
                        user_name = data.get('user_name', 'Unknown')
                        self.user_speaking_start.emit(user_name)
                        
                    elif message_type == 'user_speaking_stop':
                        user_name = data.get('user_name', 'Unknown')
                        self.user_speaking_stop.emit(user_name)
                        
                    elif message_type == 'user_info_update':
                        user_id = data.get('user_id', '')
                        user_name = data.get('user_name', 'Unknown')
                        self.user_info_update.emit(user_id, user_name)
                        
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"WebSocket connection closed: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    self.voice_error.emit(f"Voice chat connection lost after {max_retries} retries: {str(e)}\n\nThis may be due to network issues or server restart.")
                    break
            except websockets.exceptions.ConnectionClosedError as e:
                if "refused" in str(e).lower():
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    else:
                        self.voice_error.emit("WebSocket error: [WinError 1225] The remote computer refused the network connection.\n\nThis usually means the voice server is not running or is not accessible on port 8080.")
                        break
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    else:
                        self.voice_error.emit(f"Voice chat connection lost after {max_retries} retries: {str(e)}\n\nThis may be due to network issues or server restart.")
                        break
            except websockets.exceptions.InvalidURI:
                self.voice_error.emit("WebSocket error: Invalid server URL. Please check the voice server configuration.")
                break
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    self.voice_error.emit(f"Voice chat connection error after {max_retries} retries: {str(e)}")
                    break
            except Exception as e:
                logger.error(f"Unexpected voice chat error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    self.voice_error.emit(f"Voice chat error after {max_retries} retries: {str(e)}")
                    break
    
    def _start_recording(self):
        """Start audio recording (fallback)."""
        if not PYAUDIO_AVAILABLE or not self.audio:
            return
        
        try:
            self.is_recording = True
            self.recording_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
            self.recording_thread.start()
            
            logger.info("Audio recording started")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.voice_error.emit(f"Failed to start recording: {str(e)}")
    
    def _record_audio(self):
        """Record audio and send to server (fallback)."""
        try:
            while self.is_recording and self.websocket:
                if self.recording_stream:
                    data = self.recording_stream.read(self.CHUNK, exception_on_overflow=False)
                    
                    # Convert to list for JSON serialization
                    audio_list = list(data)
                    
                    # Send to server using the correct event loop
                    if self.websocket and hasattr(self, '_voice_loop') and self._voice_loop:
                        try:
                            # Check if websocket is still open before sending
                            if not self._voice_loop.is_closed() and not self.websocket.closed:
                                self._voice_loop.call_soon_threadsafe(
                                    lambda: asyncio.create_task(
                                        self.websocket.send(json.dumps({
                                            'type': 'voice_data',
                                            'audio': audio_list
                                        }))
                                    )
                                )
                            else:
                                logger.warning("WebSocket connection closed, stopping audio transmission")
                                break
                        except websockets.exceptions.ConnectionClosedError:
                            logger.warning("WebSocket connection closed during audio transmission")
                            break
                        except Exception as e:
                            logger.error(f"Error sending audio data: {e}")
                            break
                        
        except Exception as e:
            logger.error(f"Recording error: {e}")
            self.voice_error.emit(f"Recording error: {str(e)}")
    
    def _start_playback(self):
        """Start audio playback (fallback)."""
        if not PYAUDIO_AVAILABLE or not self.audio:
            return
        
        try:
            self.is_playing = True
            self.playback_stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK
            )
            
            logger.info("Audio playback started")
            
        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            self.voice_error.emit(f"Failed to start playback: {str(e)}")
    
    def stop_voice_chat(self):
        """Stop voice chat connection."""
        try:
            self.is_recording = False
            self.is_playing = False
            
            # Stop recording stream
            if hasattr(self, 'recording_stream') and self.recording_stream:
                self.recording_stream.stop_stream()
                self.recording_stream.close()
            
            # Stop playback stream
            if hasattr(self, 'playback_stream') and self.playback_stream:
                self.playback_stream.stop_stream()
                self.playback_stream.close()
            
            # Close WebSocket using the correct event loop
            if self.websocket and hasattr(self, '_voice_loop') and self._voice_loop:
                try:
                    if not self._voice_loop.is_closed():
                        self._voice_loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(self.websocket.close())
                        )
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")
            
            logger.info("Voice chat stopped")
            
        except Exception as e:
            logger.error(f"Error stopping voice chat: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.stop_voice_chat()
        except Exception:
            pass


class ChatMessageWidget(QWidget):
    """Individual chat message widget with role-based colors."""
    
    def __init__(self, message_data, user_role='newbie'):
        super().__init__()
        self.message_data = message_data
        self.user_role = user_role
        self._context_menu_enabled = True
        
        # Debug logging to see the message data structure
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 ChatMessageWidget received message_data: {message_data}")
        logger.info(f"🔍 Message sender_name: {message_data.get('sender_name', 'NOT_FOUND')}")
        logger.info(f"🔍 Message user_profiles: {message_data.get('user_profiles', 'NOT_FOUND')}")
        
        self.setup_ui()

    def contextMenuEvent(self, event):
        try:
            if not self._context_menu_enabled:
                return
            from PyQt6.QtWidgets import QMenu
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Message")
            action = menu.exec(event.globalPos())
            if action == delete_action:
                message_id = self.message_data.get("message_id")
                if message_id:
                    # Check current user permissions via hierarchy_manager
                    can_delete = False
                    try:
                        from trackpro.auth.user_manager import get_current_user
                        from trackpro.auth.hierarchy_manager import hierarchy_manager
                        user = get_current_user()
                        if user and user.is_authenticated:
                            # Admin/TEAM users can delete any message
                            if hierarchy_manager.is_admin(user.email):
                                can_delete = True
                            else:
                                # Allow deleting own messages
                                can_delete = (self.message_data.get("sender_id") == user.id)
                    except Exception:
                        can_delete = False

                    if can_delete:
                        try:
                            # Execute deletion through community manager
                            from trackpro.community.community_manager import CommunityManager
                            mgr = CommunityManager()
                            if mgr.delete_message(message_id):
                                # Remove from UI list
                                try:
                                    from PyQt6.QtWidgets import QListWidget
                                    parent_list = self.parent()
                                    # Walk up to find QListWidget item
                                    while parent_list and not isinstance(parent_list, QListWidget):
                                        parent_list = parent_list.parent()
                                    if parent_list:
                                        # Find the item hosting this widget
                                        for idx in range(parent_list.count()):
                                            itm = parent_list.item(idx)
                                            if parent_list.itemWidget(itm) is self:
                                                parent_list.takeItem(idx)
                                                break
                                except Exception:
                                    pass
                        except Exception:
                            pass
        except Exception:
            pass
    
    def create_avatar(self):
        """Create or load avatar using centralized manager (cached + async)."""
        from ...avatar_manager import AvatarManager
        size = 32
        avatar_url = None
        if self.message_data.get('user_display_info'):
            avatar_url = self.message_data['user_display_info'].get('avatar_url')
        elif self.message_data.get('user_profiles'):
            avatar_url = self.message_data['user_profiles'].get('avatar_url')
        elif self.message_data.get('sender_avatar_url'):
            avatar_url = self.message_data['sender_avatar_url']

        name = self.message_data.get('sender_name')
        if not name and self.message_data.get('user_profiles'):
            user_profile = self.message_data['user_profiles']
            name = user_profile.get('display_name') or user_profile.get('username') or 'U'
        if not name:
            name = 'U'

        return AvatarManager.instance().get_cached_pixmap(avatar_url or "", name, size=size)
    
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
    
    def __init__(self, channel_data, voice_manager=None, parent_page=None):
        super().__init__()
        self.channel_data = channel_data
        self.parent_page = parent_page
        
        # Use provided voice manager or create a new one
        if voice_manager is not None:
            self.voice_manager = voice_manager
            logger.info("Using provided voice manager")
        else:
            # Use high-quality voice manager for better audio processing
            try:
                from .high_quality_voice_manager import HighQualityVoiceManager
                self.voice_manager = HighQualityVoiceManager()
                logger.info("Using high-quality voice chat manager")
                
                # Track the voice manager with parent page if available
                if parent_page and hasattr(parent_page, '_voice_managers'):
                    parent_page._voice_managers.append(self.voice_manager)
                    logger.info("Added voice manager to parent tracking list")
            except Exception as e:
                logger.warning(f"HighQualityVoiceManager not available, falling back to VoiceChatManager: {e}")
                self.voice_manager = VoiceChatManager()
        
        self.participants = []  # List of users in the voice channel
        self.speaking_users = set()  # Set of users currently speaking
        self.is_push_to_talk = False  # Push-to-talk mode
        
        # Connect voice manager signals
        self.voice_manager.audio_level_changed.connect(self.update_audio_level)
        self.voice_manager.voice_error.connect(self.on_voice_error)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the voice channel UI."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)
        
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
        
        self.main_layout.addLayout(header_layout)
        
        # Information about self-hearing feature
        info_label = QLabel("💡 Tip: You can hear yourself slightly when speaking. This helps monitor your audio levels. Adjust this in Voice Settings.")
        info_label.setStyleSheet("""
            color: #888888; 
            font-size: 11px; 
            padding: 8px 16px;
            background-color: #252525;
            border-radius: 4px;
            margin: 8px 0px;
        """)
        info_label.setWordWrap(True)
        self.main_layout.addWidget(info_label)
        
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
        self.main_layout.addWidget(self.participants_list)
        
        # Voice controls
        self.setup_voice_controls()
    
    def setup_voice_controls(self):
        """Setup voice chat controls."""
        controls_layout = QHBoxLayout()
        
        # Join/Leave Channel button
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
        
        # Push-to-Talk toggle
        self.ptt_button = QPushButton("🎤 Open Mic")
        self.ptt_button.setCheckable(True)
        self.ptt_button.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #27ae60;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
        """)
        self.ptt_button.toggled.connect(self.toggle_push_to_talk)
        controls_layout.addWidget(self.ptt_button)
        
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
        self.settings_button.setToolTip("Configure voice chat settings including microphone, speakers, and self-hearing options")
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.settings_button.clicked.connect(self.open_voice_settings)
        controls_layout.addWidget(self.settings_button)
        
        # Audio level indicator
        self.audio_level_label = QLabel("🎤")
        self.audio_level_label.setStyleSheet("color: #666; font-size: 16px; margin-left: 8px;")
        self.audio_level_label.setToolTip("Microphone level indicator")
        controls_layout.addWidget(self.audio_level_label)
        
        # Add controls to the main layout
        self.main_layout.addLayout(controls_layout)
    
    def toggle_push_to_talk(self, enabled):
        """Toggle push-to-talk mode."""
        self.is_push_to_talk = enabled
        if enabled:
            self.ptt_button.setText("🎤 Push-to-Talk")
            self.ptt_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            # Implement push-to-talk logic
            logger.info("Push-to-talk mode enabled")
        else:
            self.ptt_button.setText("🎤 Open Mic")
            self.ptt_button.setStyleSheet("""
                QPushButton {
                    background-color: #252525;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #2d2d2d;
                }
            """)
            # Implement open mic logic
            logger.info("Open mic mode enabled")
    
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
        """Join the voice channel with on-demand server startup."""
        try:
            channel_id = self.channel_data.get('id', 'general')
            logger.info(f"Attempting to join voice channel: {channel_id}")
            
            # If WebRTC is enabled, skip PyAudio dependency checks
            webrtc_enabled = False
            try:
                from trackpro.config import config
                webrtc_enabled = getattr(config, 'voice_chat_webrtc_enabled', False) and bool(config.voice_chat_livekit_token_url)
            except Exception:
                webrtc_enabled = False

            # Check if voice components are available only when not using WebRTC
            if not webrtc_enabled:
                if not VOICE_COMPONENTS_AVAILABLE:
                    logger.warning("Voice components not available")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Voice Chat", 
                                          "Voice chat components are not available. Please install required dependencies.")
                    return
            
            # Get user name from current user
            try:
                from trackpro.auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    user_name = user.name or user.email or 'Unknown'
                else:
                    user_name = 'Unknown'
            except Exception:
                user_name = 'Unknown'
            
            # If using WebRTC, skip starting local websocket server
            if not webrtc_enabled:
                # Check if voice server is running
                if not is_voice_server_running():
                    logger.info(f"Voice server not running - starting on-demand for channel: {channel_id}")
                    try:
                        # Start the voice server on-demand
                        start_voice_server()
                        import time
                        time.sleep(3)  # Give more time for network server to start
                        
                        if not is_voice_server_running():
                            raise Exception("Voice server failed to start on-demand")
                        
                        logger.info(f"Voice server started on-demand for channel: {channel_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to start voice server on-demand: {e}")
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "Voice Chat Error", 
                                          f"Failed to start voice server on-demand: {str(e)}")
                        return
                else:
                    logger.info(f"Voice server already running - joining channel: {channel_id}")
            
            # Prefer WebRTC when enabled (LiveKit)
            if webrtc_enabled:
                try:
                    # Launch WebRTC voice (embedded web view)
                    self.start_webrtc_voice(channel_id)
                    logger.info("Started WebRTC voice for channel via LiveKit")
                    # Add current user to participants and update UI before returning
                    self.add_current_user_to_participants()
                    self.play_join_notification()
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
                    logger.info(f"Successfully joined WebRTC voice channel: {channel_id}")
                    return
                except Exception as _e:
                    logger.debug(f"WebRTC not enabled or failed to initialize: {_e}")

            # Fallback to WebSocket voice server
            try:
                from trackpro.config import config
                server_url = config.voice_chat_server_url
            except Exception:
                server_url = "ws://localhost:8080"
            
            logger.info(f"Starting voice chat - Server: {server_url}, Channel: {channel_id}, User: {user_name}")
            
            # Use the existing HighQualityVoiceManager instead of creating a new SimpleVoiceClient
            if hasattr(self, 'voice_manager') and self.voice_manager:
                logger.info("Using existing HighQualityVoiceManager for voice chat")
                
                # Connect signals to the voice manager
                self.voice_manager.user_joined_voice.connect(self.on_user_joined_voice)
                self.voice_manager.user_left_voice.connect(self.on_user_left_voice)
                self.voice_manager.voice_error.connect(self.on_voice_error)
                self.voice_manager.connected.connect(self.on_voice_connected)
                self.voice_manager.disconnected.connect(self.on_voice_disconnected)
                
                # Start voice chat with the HighQualityVoiceManager
                self.voice_manager.start_voice_chat(server_url, channel_id)
                
                # Store reference to voice manager as voice_client for compatibility
                self.voice_client = self.voice_manager
                
            else:
                logger.warning("No voice manager available, falling back to SimpleVoiceClient")
                # Fallback to SimpleVoiceClient if no voice manager is available
                self.voice_client = SimpleVoiceClient()
                
                # Connect signals
                self.voice_client.user_joined_voice.connect(self.on_user_joined_voice)
                self.voice_client.user_left_voice.connect(self.on_user_left_voice)
                self.voice_client.voice_error.connect(self.on_voice_error)
                self.voice_client.connected.connect(self.on_voice_connected)
                self.voice_client.disconnected.connect(self.on_voice_disconnected)
                
                # Start voice chat - this will create the room on the server
                self.voice_client.start_voice_chat(server_url, channel_id, user_name)
            
            # Add current user to participants
            self.add_current_user_to_participants()
            
            # Play join notification
            self.play_join_notification()
            
            # Update UI to show connected status
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
            
            logger.info(f"Successfully joined voice channel: {channel_id} (room created on server)")
            
        except Exception as e:
            logger.error(f"Failed to join voice channel: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Voice Chat Error", 
                              f"Failed to join voice channel: {str(e)}")

    def start_webrtc_voice(self, channel_id: str):
        """Start WebRTC voice using an embedded QWebEngineView with LiveKit JS.

        Assumes a Supabase Edge Function (or similar) provides a LiveKit access token
        at config.voice_chat_livekit_token_url. This keeps the API secret off clients.
        """
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from PyQt6.QtCore import QUrl
            from trackpro.config import config

            token_url = config.voice_chat_livekit_token_url
            host_url = config.voice_chat_livekit_host_url
            if not token_url or not host_url:
                raise RuntimeError("LiveKit token or host URL not configured")

            # Fetch LiveKit token on the Python side to avoid browser CORS issues
            livekit_token = None
            try:
                import requests
                params = {"room": channel_id}
                headers = {}
                try:
                    # Attempt to add Supabase auth bearer if available
                    from trackpro.database.supabase_client import get_supabase_client
                    sb = get_supabase_client()
                    if sb and hasattr(sb, 'auth'):
                        sess = sb.auth.get_session()
                        access_token = getattr(sess, 'access_token', None) if sess else None
                        if access_token:
                            headers['Authorization'] = f"Bearer {access_token}"
                except Exception:
                    pass
                resp = requests.get(token_url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                livekit_token = data.get('token') or data.get('access_token')
                if not livekit_token:
                    raise RuntimeError('Token endpoint did not return token')
            except Exception as fetch_err:
                raise RuntimeError(f"Failed to fetch LiveKit token: {fetch_err}")

            # Inline HTML: minimal LiveKit client (token injected)
            html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>TrackPro Voice</title>
  <script src='https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.min.js'></script>
  <style>body{{margin:0;background:#1e1f22;color:#fff;font:14px sans-serif}}</style>
  <script>
    async function start() {{
      try {{
        const channelId = {json.dumps(channel_id)};
        const token = {json.dumps(livekit_token)};

        const room = new LiveKit.Room();
        room.on(LiveKit.RoomEvent.TrackSubscribed, (track, publication, participant) => {{
          if (track.kind === 'audio') {{ track.attach(); }}
        }});
        await room.connect('{host_url}', token);
        const localStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        await room.localParticipant.publishTrack(localStream.getAudioTracks()[0]);
        window._room = room;
      }} catch (e) {{
        document.body.innerText = 'Voice error: ' + e;
      }}
    }}
    window.addEventListener('load', start);
  </script>
</head>
<body>Connecting voice...</body>
</html>
"""

            view = QWebEngineView(self)
            view.setHtml(html, QUrl("about:blank"))
            # Keep a reference to avoid GC
            self._webrtc_view = view
            # Display or embed as needed in your UI (minimal integration; can refine later)
            view.setWindowTitle("TrackPro Voice")
            view.resize(480, 240)
            view.show()
        except Exception as e:
            logger.error(f"Failed to start WebRTC voice: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Voice Chat Error", f"WebRTC initialization failed: {str(e)}")
    
    def on_voice_connected(self):
        """Handle voice connection established."""
        logger.info("Voice chat connected successfully")
        # Update UI to show connected status
        
    def on_voice_disconnected(self):
        """Handle voice connection lost."""
        logger.info("Voice chat disconnected")
        # Update UI to show disconnected status
    
    def on_user_joined_voice(self, user_id):
        """Handle user joining voice channel."""
        logger.info(f"User joined voice: {user_id}")
        # Add user to participants if not already present
        # This would typically come from the server with user info
    
    def on_user_left_voice(self, user_id):
        """Handle user leaving voice channel."""
        logger.info(f"User left voice: {user_id}")
        # Remove user from participants
        # This would typically come from the server with user info
    
    def on_user_speaking_start(self, user_name):
        """Handle user starting to speak."""
        logger.info(f"User started speaking: {user_name}")
        self.add_speaking_user(user_name)
    
    def on_user_speaking_stop(self, user_name):
        """Handle user stopping speaking."""
        logger.info(f"User stopped speaking: {user_name}")
        self.remove_speaking_user(user_name)
    
    def on_user_info_update(self, user_id, user_name):
        """Handle user info updates."""
        logger.info(f"User info update: {user_id} -> {user_name}")
        # Update user information in participants list
        # This could be used to update user names or other info
    
    def on_voice_error(self, error_message):
        """Handle voice chat errors."""
        logger.error(f"🎤 Voice chat error: {error_message}")
        
        # Show error to user
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Voice Chat Error", error_message)
    
    def update_participants_list(self):
        """Update the participants list display with speaking indicators."""
        self.participants_list.clear()
        
        for participant in self.participants:
            # Create participant item with enhanced status indicators
            name = participant['name']
            status = participant['status']
            muted = participant.get('muted', False)
            
            # Determine status icon and color
            if name in self.speaking_users:
                status_icon = "🔊"  # Speaking indicator
                status_color = '#3498db'  # TrackPro blue for speaking
                status_text = "Speaking"
            elif status == 'online':
                status_icon = "🟢"
                status_color = '#ffffff'  # White for normal
                status_text = "Online"
            else:
                status_icon = "🟡"
                status_color = '#888888'  # Gray for away
                status_text = "Away"
            
            # Add mute indicator
            mute_icon = "🔇" if muted else ""
            
            # Create display text with status
            display_name = f"{status_icon} {name} {mute_icon}".strip()
            if name in self.speaking_users:
                display_name += " 🔊"  # Additional speaking indicator
            
            item = QListWidgetItem(display_name)
            
            # Set color based on status
            if name in self.speaking_users:
                item.setForeground(QColor(status_color))
                # Add bold font for speaking users
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            elif muted:
                item.setForeground(QColor('#888888'))  # Gray for muted
            else:
                item.setForeground(QColor(status_color))
            
            self.participants_list.addItem(item)
    
    def update_speaking_status(self, user_name, is_speaking):
        """Update the speaking status of a user."""
        # Only log significant changes, not every update
        was_speaking = user_name in self.speaking_users
        
        if is_speaking:
            self.speaking_users.add(user_name)
        else:
            self.speaking_users.discard(user_name)
        
        # Only log if the speaking status actually changed
        if was_speaking != is_speaking:
            logger.info(f"🎤 Speaking status changed: {user_name} -> {'speaking' if is_speaking else 'not speaking'}")
        
        # Update the display
        self.update_participants_list()
    
    def add_speaking_user(self, user_name):
        """Add a user to the speaking list."""
        self.update_speaking_status(user_name, True)
    
    def remove_speaking_user(self, user_name):
        """Remove a user from the speaking list."""
        self.update_speaking_status(user_name, False)
    
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
        # Stop WebRTC view if present
        if hasattr(self, '_webrtc_view') and self._webrtc_view:
            try:
                self._webrtc_view.deleteLater()
            except Exception:
                pass
            self._webrtc_view = None

        # Stop legacy/WebSocket voice if present
        if hasattr(self, 'voice_client') and self.voice_client:
            self.voice_client.stop_voice_chat()
        self.remove_current_user_from_participants()
        # Clear speaking users when leaving
        self.speaking_users.clear()
        self.update_participants_list()
    
    def remove_current_user_from_participants(self):
        """Remove the current user from the participants list."""
        try:
            current_user_name = 'Lawrence Thomas'  # This should come from user manager
            
            # Remove user from participants
            self.participants = [p for p in self.participants if p['name'] != current_user_name]
            # Remove from speaking users
            self.speaking_users.discard(current_user_name)
            self.update_participants_list()
            self.update_participant_count()
            
            logger.info(f"Removed user from voice channel participants: {current_user_name}")
            
        except Exception as e:
            logger.error(f"Failed to remove current user from participants: {e}")
    
    def play_join_notification(self):
        """Play a pleasant join notification sound."""
        try:
            import numpy as np
            import pyaudio
            
            # Generate a pleasant join notification sound
            sample_rate = 48000
            duration = 0.5  # Short notification
            frequency = 1000  # Pleasant frequency
            
            # Generate a pleasant ding
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = (0.6 * np.sin(2 * np.pi * frequency * t) + 
                   0.4 * np.sin(2 * np.pi * frequency * 2 * t))
            
            # Apply smooth envelope
            envelope = np.exp(-5 * t)
            tone = tone * envelope
            
            # Apply fade in/out
            fade_samples = int(0.02 * sample_rate)
            tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
            tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            # Convert to 16-bit audio
            tone = (tone * 16383).astype(np.int16)
            
            # Play the notification
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True
            )
            
            stream.write(tone.tobytes())
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
        except Exception as e:
            logger.error(f"Failed to play join notification: {e}")
    
    def add_current_user_to_participants(self):
        """Add the current user to the participants list."""
        try:
            # Get current user info from the community page
            from trackpro.config import config
            current_user = {
                'name': 'Lawrence Thomas',  # This should come from user manager
                'status': 'online',
                'muted': False,
                'deafened': False
            }
            
            # Check if user is already in the list
            for participant in self.participants:
                if participant['name'] == current_user['name']:
                    return  # Already in the list
            
            # Add user to participants
            self.participants.append(current_user)
            self.update_participants_list()
            self.update_participant_count()
            
            logger.info(f"Added user to voice channel participants: {current_user['name']}")
            
        except Exception as e:
            logger.error(f"Failed to add current user to participants: {e}")
    
    def open_voice_settings(self):
        """Open voice settings dialog."""
        if not VOICE_COMPONENTS_AVAILABLE or VoiceSettingsDialog is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Voice Settings", 
                                  "Voice settings require additional components.\n\n"
                                  "Please ensure pyaudio and numpy are installed for full voice chat functionality.\n\n"
                                  "Install with: pip install pyaudio numpy")
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
        """Handle voice settings changes by delegating to parent page."""
        try:
            logger.info(f"🔄 VoiceChannelWidget: Delegating voice settings update to parent page")
            
            # Delegate to parent page if available
            if self.parent_page and hasattr(self.parent_page, 'on_voice_settings_changed'):
                self.parent_page.on_voice_settings_changed(settings)
            else:
                logger.warning("No parent page available for voice settings update")
                
            # Update our own voice manager if available
            if hasattr(self, 'voice_manager') and self.voice_manager:
                try:
                    if hasattr(self.voice_manager, 'update_settings'):
                        self.voice_manager.update_settings(settings)
                        logger.info("Updated local voice manager settings")
                    elif hasattr(self.voice_manager, 'update_voice_settings'):
                        self.voice_manager.update_voice_settings(settings)
                        logger.info("Updated local voice manager settings")
                except Exception as e:
                    logger.error(f"Failed to update local voice manager settings: {e}")
            
        except Exception as e:
            logger.error(f"Failed to update voice settings: {e}")
    
    def update_audio_level(self, level: float):
        """Update audio level meter display."""
        try:
            # Get current user name
            current_user_name = "Lawrence Thomas"  # This should come from user manager
            
            # Convert level (0-1) to visual indicator
            if level > 0.5:
                self.audio_level_label.setText("🔴")  # High level
                self.audio_level_label.setStyleSheet("color: #ff4444; font-size: 16px;")
                # Update speaking status for current user - only if not muted
                if not self.mute_button.isChecked():
                    self.update_speaking_status(current_user_name, True)
            elif level > 0.2:
                self.audio_level_label.setText("🟡")  # Medium level
                self.audio_level_label.setStyleSheet("color: #ffaa00; font-size: 16px;")
                # Update speaking status for current user - only if not muted
                if not self.mute_button.isChecked():
                    self.update_speaking_status(current_user_name, True)
            elif level > 0.05:
                self.audio_level_label.setText("🟢")  # Low level
                self.audio_level_label.setStyleSheet("color: #44ff44; font-size: 16px;")
                # Update speaking status for current user - only if not muted
                if not self.mute_button.isChecked():
                    self.update_speaking_status(current_user_name, True)
            else:
                self.audio_level_label.setText("🎤")  # No audio
                self.audio_level_label.setStyleSheet("color: #666; font-size: 16px;")
                # Update speaking status for current user - not speaking
                self.update_speaking_status(current_user_name, False)
        except Exception as e:
            logger.error(f"UI: Failed to update audio level: {e}")

class ChatChannelWidget(QWidget):
    """Chat channel widget with message list and input."""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self, channel_data):
        super().__init__()
        self.channel_data = channel_data
        self._auth_overlay = None
        self.on_request_older = None
        self._is_loading_more = False
        self._has_unseen = False
        self._new_separator_item = None
        self.setup_ui()
        # Build overlay last so it sits above content
        self._create_auth_overlay()
    
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
        try:
            # Detect scroll to top to load older messages
            vbar = self.messages_list.verticalScrollBar()
            vbar.valueChanged.connect(self._on_scroll_changed)
        except Exception:
            pass
        layout.addWidget(self.messages_list)

        # Jump-to-present button (lightweight, only shows when scrolled up or with unseen)
        from PyQt6.QtWidgets import QPushButton
        self.jump_to_present_btn = QPushButton("Jump to Present")
        self.jump_to_present_btn.setVisible(False)
        self.jump_to_present_btn.setFixedHeight(28)
        self.jump_to_present_btn.setStyleSheet(
            """
            QPushButton { background-color: #3ba55c; color: #ffffff; border: none; border-radius: 4px; margin: 6px 12px; }
            QPushButton:hover { background-color: #2d7d46; }
            QPushButton:pressed { background-color: #1f5f35; }
            """
        )
        self.jump_to_present_btn.clicked.connect(self._on_jump_to_present_clicked)
        layout.addWidget(self.jump_to_present_btn)
        
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
    
    def _create_auth_overlay(self):
        """Create a semi-transparent overlay prompting login, covering the chat area."""
        try:
            if self._auth_overlay is not None:
                return
            overlay = QWidget(self)
            overlay.setVisible(False)
            overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            overlay.setStyleSheet(
                """
                QWidget {
                    background-color: rgba(20, 20, 20, 200);
                    border: none;
                }
                """
            )
            # Centered message
            msg = QLabel("Must Be Logged In To Chat", overlay)
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet("color: #bbbbbb; font-size: 16px; font-weight: bold;")
            # Fill overlay and center label using a layout
            v = QVBoxLayout(overlay)
            v.setContentsMargins(0, 0, 0, 0)
            v.addStretch(1)
            v.addWidget(msg, 0, Qt.AlignmentFlag.AlignCenter)
            v.addStretch(1)
            self._auth_overlay = overlay
            # Ensure correct initial geometry
            self._resize_auth_overlay()
        except Exception as e:
            logger.error(f"Error creating auth overlay: {e}")

    def _resize_auth_overlay(self):
        try:
            if self._auth_overlay is not None:
                self._auth_overlay.setGeometry(0, 0, self.width(), self.height())
        except Exception:
            pass

    def resizeEvent(self, event):
        self._resize_auth_overlay()
        return super().resizeEvent(event)

    def show_auth_overlay(self, show: bool):
        """Show or hide the authentication overlay and block interactions when shown."""
        try:
            if self._auth_overlay is None:
                self._create_auth_overlay()
            if self._auth_overlay:
                self._auth_overlay.setVisible(bool(show))
                # When overlay is shown, also ensure input is disabled
                if hasattr(self, 'message_input') and self.message_input:
                    self.message_input.setEnabled(not show)
        except Exception as e:
            logger.error(f"Error toggling auth overlay: {e}")

    def send_message(self):
        """Send a message."""
        text = self.message_input.text().strip()
        if text:
            self.message_sent.emit(text)
            self.message_input.clear()
    
    def add_message(self, message_data):
        """Add a message to the chat."""
        try:
            is_near_bottom = self._is_near_bottom()

            # If user is not at bottom, mark unseen and ensure separator exists before first unseen
            if not is_near_bottom:
                if not self._has_unseen:
                    self._ensure_new_separator()
                self._has_unseen = True
                self.jump_to_present_btn.setVisible(True)

            message_widget = ChatMessageWidget(message_data)
            item = QListWidgetItem()
            item.setSizeHint(message_widget.sizeHint())
            
            self.messages_list.addItem(item)
            self.messages_list.setItemWidget(item, message_widget)
            
            # Auto-scroll only if user is already near the bottom
            if is_near_bottom:
                self.messages_list.scrollToBottom()
        except Exception as e:
            logger.error(f"Error adding message to chat: {e}")

    def add_messages_bulk(self, messages, scroll_to_bottom: bool = True):
        """Add a list of messages efficiently; optionally scroll to bottom once."""
        try:
            for message in messages:
                message_widget = ChatMessageWidget(message)
                item = QListWidgetItem()
                item.setSizeHint(message_widget.sizeHint())
                self.messages_list.addItem(item)
                self.messages_list.setItemWidget(item, message_widget)
            if scroll_to_bottom:
                self.messages_list.scrollToBottom()
        except Exception as e:
            logger.error(f"Error adding messages in bulk: {e}")

    def prepend_messages(self, messages):
        """Prepend older messages at the top while preserving the user's position."""
        try:
            # Remember the item currently at the top (likely visible when at top)
            prev_top_item = self.messages_list.item(0)
            # Insert in order so that the earliest ends up at the very top
            for message in messages:
                message_widget = ChatMessageWidget(message)
                item = QListWidgetItem()
                item.setSizeHint(message_widget.sizeHint())
                self.messages_list.insertItem(0, item)
                self.messages_list.setItemWidget(item, message_widget)
            # Restore previous top item position below newly inserted block
            try:
                from PyQt6.QtWidgets import QAbstractItemView
                if prev_top_item is not None:
                    self.messages_list.scrollToItem(prev_top_item, QAbstractItemView.ScrollHint.PositionAtTop)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error prepending messages: {e}")

    def _on_scroll_changed(self, value: int):
        try:
            # Top reached → load older
            if value == 0 and not self._is_loading_more and callable(self.on_request_older):
                self._is_loading_more = True
                self.on_request_older()
            # Bottom proximity → hide jump, clear unseen and separator
            if self._is_near_bottom():
                self.jump_to_present_btn.setVisible(False)
                self._has_unseen = False
                self._remove_new_separator()
            else:
                if self._has_unseen:
                    self.jump_to_present_btn.setVisible(True)
        except Exception:
            pass

    def notify_load_more_complete(self):
        """Allow more load-more triggers after current load finishes."""
        self._is_loading_more = False

    def _is_near_bottom(self, threshold: int = 20) -> bool:
        try:
            vbar = self.messages_list.verticalScrollBar()
            return (vbar.maximum() - vbar.value()) <= threshold
        except Exception:
            return True

    def _ensure_new_separator(self):
        try:
            if self._new_separator_item is not None:
                return
            from PyQt6.QtWidgets import QLabel
            sep_label = QLabel("— New Messages —")
            sep_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sep_label.setStyleSheet("color: #9aa0a6; padding: 6px 0;")
            item = QListWidgetItem()
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setSizeHint(sep_label.sizeHint())
            self.messages_list.addItem(item)
            self.messages_list.setItemWidget(item, sep_label)
            self._new_separator_item = item
        except Exception:
            pass

    def _remove_new_separator(self):
        try:
            if self._new_separator_item is None:
                return
            row = self.messages_list.row(self._new_separator_item)
            if row >= 0:
                itm = self.messages_list.takeItem(row)
                del itm
            self._new_separator_item = None
        except Exception:
            self._new_separator_item = None

    def _on_jump_to_present_clicked(self):
        try:
            self.messages_list.scrollToBottom()
            self.jump_to_present_btn.setVisible(False)
            self._has_unseen = False
            self._remove_new_separator()
        except Exception:
            pass


class CommunityPage(BasePage):
    """Community page with Discord-inspired design and voice chat."""
    
    # Class-level flag to prevent multiple initializations during startup
    _global_initialization_in_progress = False
    _instance_count = 0
    _heavy_components_initialized = False  # Add flag to prevent duplicate heavy initialization
    _channels_loaded = False  # Class-level flag to prevent duplicate channel loading
    _private_messages_loaded = False  # Class-level flag to prevent duplicate private message loading
    
    def __init__(self, global_managers=None):
        super().__init__("community", global_managers)
        
        # Initialize instance counter
        CommunityPage._instance_count += 1
        self.instance_id = CommunityPage._instance_count
        
        logger.info(f"🔄 Initializing CommunityPage (instance #{self.instance_id})")
        
        # Set global managers
        self.global_managers = global_managers or {}
        
        # Initialize community manager
        self._community_manager = None
        
        # Initialize central voice manager
        self._central_voice_manager = None
        self._voice_managers = []  # Track all voice managers
        
        # Initialize UI components
        self.channels = []
        self.current_channel = None
        self.private_messages = []
        self.current_private_conversation = None
        self.voice_channels = {}  # Track voice channels for cleanup
        
        # Initialize state flags
        self._initialization_complete = False
        self._user_state_refreshed = False
        self._activation_complete = False
        
        # Initialize message caching and lazy loading
        self._message_cache = {}  # Cache for loaded messages by channel_id
        self._message_cache_timestamps = {}  # Track when cache was last updated
        self._lazy_loading_enabled = True  # Enable lazy loading by default
        self._messages_per_page = 50  # Number of messages to load per page (newest window)
        self._loaded_message_counts = {}  # Track how many messages loaded per channel
        self._max_messages_in_ui = 500  # Cap to keep UI responsive
        # Local chat history fallback (used if DB manager unavailable or for realtime append)
        self.chat_history = {}
        self._auth_signal_connected = False
        
        # Initialize UI
        self.setup_ui()
        
        # Set up authentication state
        self.set_current_user()
        # Attempt to connect to global auth state changes right after construction
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._ensure_auth_signal_connected)
        except Exception:
            pass
        
        # START HEAVY INITIALIZATION IMMEDIATELY FOR FASTER LOADING
        # This moves the heavy work from activation to pre-loading
        # Only initialize heavy components once globally
        if not CommunityPage._heavy_components_initialized:
            logger.info("🚀 Starting heavy initialization during pre-loading for faster community page access...")
            
            # Start heavy initialization in background to avoid blocking UI
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._initialize_heavy_components)
        else:
            logger.info("🔄 Heavy components already initialized, skipping")
        
        logger.info(f"✅ CommunityPage initialized (instance #{self.instance_id})")
    
    @classmethod
    def reset_instance_counter(cls):
        """Reset the instance counter (for testing purposes)."""
        cls._instance_count = 0
        cls._heavy_components_initialized = False
        cls._channels_loaded = False
        cls._private_messages_loaded = False
    
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
        # Context menu for local actions (e.g., Delete Chat)
        try:
            self.private_messages_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.private_messages_list.customContextMenuRequested.connect(self.on_private_messages_context_menu)
        except Exception:
            pass
        scroll_layout.addWidget(self.private_messages_list)
        
        # Friends section
        friends_header = QLabel("FRIENDS")
        friends_header.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            font-weight: bold; 
            padding: 8px 16px 4px 16px;
            background-color: #1e1e1e;
        """)
        scroll_layout.addWidget(friends_header)
        
        # Add Friend button
        self.add_friend_btn = QPushButton("+ Add Friend")
        self.add_friend_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                margin: 4px 16px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
        """)
        self.add_friend_btn.clicked.connect(self.on_add_friend_clicked)
        scroll_layout.addWidget(self.add_friend_btn)
        
        # Friends list
        self.friends_list = QListWidget()
        self.friends_list.setStyleSheet("""
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
        scroll_layout.addWidget(self.friends_list)
        
        # Friend requests section
        friend_requests_header = QLabel("FRIEND REQUESTS")
        friend_requests_header.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            font-weight: bold; 
            padding: 8px 16px 4px 16px;
            background-color: #1e1e1e;
        """)
        scroll_layout.addWidget(friend_requests_header)
        
        # Friend requests list
        self.friend_requests_list = QListWidget()
        self.friend_requests_list.setStyleSheet("""
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
        scroll_layout.addWidget(self.friend_requests_list)
        
        scroll_area.setWidget(scroll_content)
        server_layout.addWidget(scroll_area)
        
        # Data loading is now handled during heavy initialization to prevent multiple loads
        # self.load_channels_from_database()
        # self.load_private_messages()
        
        self.channel_list.itemClicked.connect(self.on_channel_selected)
        self.voice_channels_list.itemClicked.connect(self.on_channel_selected)
        self.private_messages_list.itemClicked.connect(self.on_private_message_selected)
        self.friends_list.itemClicked.connect(self.on_friend_selected)
        self.friend_requests_list.itemClicked.connect(self.on_friend_request_selected)
        
        parent_layout.addWidget(server_widget)
    
    def create_main_content(self, parent_layout):
        """Create the main content area."""
        # Create a tab widget to host Chat (existing), Events, and Setup
        from PyQt6.QtWidgets import QTabWidget, QVBoxLayout, QWidget, QLabel

        self.content_tabs = QTabWidget()
        self.content_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #202225; background-color: #1e1e1e; }
            QTabBar::tab { background-color: #2a2a2a; color: #dcddde; padding: 8px 14px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #3a3a3a; color: #ffffff; }
            QTabBar::tab:hover:!selected { background-color: #333333; }
        """)

        # Chat tab content contains the legacy content stack which channels render into
        chat_tab = QWidget()
        chat_tab_layout = QVBoxLayout(chat_tab)
        chat_tab_layout.setContentsMargins(0, 0, 0, 0)
        chat_tab_layout.setSpacing(0)

        self.content_stack = QWidget()
        self.content_stack.setStyleSheet("""
            QWidget { background-color: #1e1e1e; }
        """)
        # Ensure the content area always has a layout so children expand properly
        try:
            from PyQt6.QtWidgets import QVBoxLayout
            self.content_stack_layout = QVBoxLayout(self.content_stack)
            self.content_stack_layout.setContentsMargins(0, 0, 0, 0)
            self.content_stack_layout.setSpacing(0)
        except Exception:
            self.content_stack_layout = None
        chat_tab_layout.addWidget(self.content_stack)

        self.content_tabs.addTab(chat_tab, "💬 Chat")

        # Events tab
        try:
            events_tab = self.create_events_tab()
        except Exception as _e:
            # Fall back to simple placeholder if creation fails
            events_tab = QWidget()
            _lt = QVBoxLayout(events_tab)
            _lt.setContentsMargins(16, 16, 16, 16)
            _label = QLabel("Events are unavailable")
            _label.setStyleSheet("color: #dcddde;")
            _lt.addWidget(_label)
        self.content_tabs.addTab(events_tab, "📅 Events")

        # Setup tab
        setup_tab = self.create_setup_tab()
        self.content_tabs.addTab(setup_tab, "🛠️ Setup")

        parent_layout.addWidget(self.content_tabs, 1)
    

    
    def on_channel_selected(self, item):
        """Handle channel selection."""
        logger.info(f"🎯 Channel selected: {item.text()}")
        
        try:
            channel_data = item.data(Qt.ItemDataRole.UserRole)
            if channel_data:
                logger.info(f"📋 Channel data: {channel_data}")
                
                # Cleanup previous voice channel if switching from voice to voice
                if self.current_channel:
                    # Check if current channel is a voice channel
                    current_channel_type = None
                    if self.community_manager:
                        channels = self.community_manager.get_channels()
                        for channel in channels:
                            if channel['channel_id'] == self.current_channel:
                                current_channel_type = channel['channel_type']
                                break
                    
                    if current_channel_type == 'voice':
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
            
            # Replace the old content_stack with the new one inside its actual parent layout (Chat tab)
            if hasattr(self, 'content_stack') and self.content_stack:
                logger.info("🔄 Replacing old content_stack")
                parent_widget = self.content_stack.parentWidget()
                parent_layout = parent_widget.layout() if parent_widget else self.layout()
                if parent_layout:
                    try:
                        parent_layout.replaceWidget(self.content_stack, new_content)
                        self.content_stack.setParent(None)
                        self.content_stack.deleteLater()
                        logger.info("✅ Replaced content_stack in parent layout")
                    except Exception as _repl_err:
                        # Fallback manual replace
                        for i in range(parent_layout.count()):
                            item = parent_layout.itemAt(i)
                            if item and item.widget() == self.content_stack:
                                logger.info("🗑️ Removing old content_stack from parent layout (fallback)")
                                parent_layout.removeWidget(self.content_stack)
                                self.content_stack.setParent(None)
                                self.content_stack.deleteLater()
                                parent_layout.insertWidget(i, new_content)
                                logger.info("✅ Inserted new content widget into parent layout (fallback)")
                                break
                else:
                    logger.warning("⚠️ No parent layout found for content_stack")
            
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
            # Get channel type from database or fallback channels
            channel_type = None
            
            # First try to get from community manager database
            if self.community_manager:
                channels = self.community_manager.get_channels()
                for channel in channels:
                    if channel['channel_id'] == channel_id:
                        channel_type = channel['channel_type']
                        break
            
            # If not found in database, check fallback channels
            if channel_type is None:
                # Check voice channels list
                for i in range(self.voice_channels_list.count()):
                    item = self.voice_channels_list.item(i)
                    item_data = item.data(Qt.ItemDataRole.UserRole)
                    if item_data and item_data['id'] == channel_id:
                        channel_type = item_data['type']
                        logger.info(f"🔍 Found channel type from voice channels list: {channel_type}")
                        break
                
                # Check text channels list if not found in voice channels
                if channel_type is None:
                    for i in range(self.channel_list.count()):
                        item = self.channel_list.item(i)
                        item_data = item.data(Qt.ItemDataRole.UserRole)
                        if item_data and item_data['id'] == channel_id:
                            channel_type = item_data['type']
                            logger.info(f"🔍 Found channel type from text channels list: {channel_type}")
                            break
            
            logger.info(f"🎯 Channel type detection result: {channel_type} for channel {channel_id}")
            
            if channel_type == 'voice':
                # Voice channel
                channel_name = self.get_channel_name(channel_id)
                logger.info(f"🔊 Creating voice channel widget for: {channel_name} ({channel_id})")
                
                # Get or create central voice manager
                central_voice_manager = self.get_central_voice_manager()
                
                voice_widget = VoiceChannelWidget({
                    'id': channel_id,
                    'name': channel_name,
                    'participant_count': 0
                }, voice_manager=central_voice_manager, parent_page=self)
                
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
                # Text channel (default if type is None or 'text')
                channel_name = self.get_channel_name(channel_id)
                logger.info(f"💬 Creating chat channel widget for: {channel_name} ({channel_id})")
                chat_widget = ChatChannelWidget({
                    'id': channel_id,
                    'name': channel_name
                })
                chat_widget.message_sent.connect(self.on_message_sent)
                # Enable infinite scroll upwards (load older on top reach)
                try:
                    chat_widget.on_request_older = lambda cid=channel_id, cw=chat_widget: self.load_more_messages_for_channel(cid, cw)
                except Exception:
                    pass
                logger.info(f"✅ Chat channel widget created, adding to layout")
                layout.addWidget(chat_widget)
                
                # Store reference to current chat widget for real-time updates
                self.current_chat_widget = chat_widget
                
                # Update input field state based on authentication
                self.update_input_field_state()
                
                # Load messages for this channel using lazy loading (latest window)
                self.load_messages_for_channel(channel_id, chat_widget)
        except Exception as e:
            logger.error(f"❌ Error creating channel widget: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")

    def create_events_tab(self):
        """Create the Events tab content."""
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
        try:
            # Prefer using the existing EventsWidget if available
            from ...community_ui import EventsWidget  # type: ignore
            events_container = QWidget()
            layout = QVBoxLayout(events_container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            user_id = None
            try:
                if self.community_manager:
                    user_id = self.community_manager.get_current_user_id()
            except Exception:
                user_id = None

            self.events_widget = EventsWidget(self.community_manager, user_id)
            layout.addWidget(self.events_widget)
            return events_container
        except Exception as e:
            logger.warning(f"EventsWidget unavailable, using placeholder: {e}")
            placeholder = QWidget()
            pl = QVBoxLayout(placeholder)
            pl.setContentsMargins(16, 16, 16, 16)
            lbl = QLabel("Community events coming soon")
            lbl.setStyleSheet("color: #dcddde;")
            pl.addWidget(lbl)
            return placeholder

    def create_setup_tab(self):
        """Create the Setup tab content (placeholder for iRacing car setups)."""
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
        setup = QWidget()
        layout = QVBoxLayout(setup)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        title = QLabel("Car Setups (iRacing)")
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        desc = QLabel("Manage and share your iRacing setups here. This feature is coming soon.")
        desc.setStyleSheet("color: #cccccc;")
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return setup

    def switch_to_sub_tab(self, tab_name: str):
        """Switch community sub-tab: 'chat' | 'events' | 'setup'."""
        try:
            if not hasattr(self, 'content_tabs') or not self.content_tabs:
                return
            name = (tab_name or '').strip().lower()
            for i in range(self.content_tabs.count()):
                text = self.content_tabs.tabText(i).lower()
                if (name == 'chat' and 'chat' in text) or \
                   (name == 'events' and 'events' in text) or \
                   (name == 'setup' and 'setup' in text):
                    self.content_tabs.setCurrentIndex(i)
                    break
        except Exception as e:
            logger.debug(f"switch_to_sub_tab error: {e}")
    
    def get_channel_default_messages(self, channel_id):
        """Get default messages for each channel."""
        # Start with empty messages for all channels
        return []
    
    def load_messages_for_channel(self, channel_id: str, chat_widget=None):
        """Load messages for a channel using lazy loading and caching."""
        try:
            logger.info(f"🔄 Loading messages for channel {channel_id} using lazy loading")
            
            # Check if we have cached messages that are recent (within 30 seconds)
            cache_timestamp = self._message_cache_timestamps.get(channel_id, 0)
            current_time = time.time()
            cache_age = current_time - cache_timestamp
            
            if channel_id in self._message_cache and cache_age < 30:
                # Use cached messages
                cached_messages = self._message_cache[channel_id]
                logger.info(f"📋 Using cached messages for channel {channel_id} ({len(cached_messages)} messages)")
                
                if chat_widget:
                    for message in cached_messages:
                        chat_widget.add_message(message)
                
                return cached_messages
            
            # Load messages from database with pagination (newest window)
            if self.community_manager:
                try:
                    # Load only the most recent messages initially
                    messages = self.community_manager.get_messages(channel_id, limit=self._messages_per_page)
                    
                    # Cache the messages
                    self._message_cache[channel_id] = messages
                    self._message_cache_timestamps[channel_id] = current_time
                    self._loaded_message_counts[channel_id] = len(messages)
                    
                    logger.info(f"✅ Loaded {len(messages)} messages for channel {channel_id} (lazy loading)")
                    
                    # Add messages to UI if widget provided
                    if chat_widget:
                        # Add in bulk for efficiency and scroll once
                        if hasattr(chat_widget, 'add_messages_bulk'):
                            chat_widget.add_messages_bulk(messages, scroll_to_bottom=True)
                        else:
                            for message in messages:
                                chat_widget.add_message(message)
                    
                    return messages
                    
                except Exception as e:
                    logger.error(f"Error loading messages for channel {channel_id}: {e}")
                    return []
            else:
                # Fallback: load from local chat history
                if channel_id in self.chat_history:
                    messages = self.chat_history[channel_id]
                    logger.info(f"✅ Loaded {len(messages)} local messages for channel {channel_id}")
                    
                    if chat_widget:
                        for message in messages:
                            chat_widget.add_message(message)
                    
                    return messages
                else:
                    # Initialize empty chat history for this channel
                    self.chat_history[channel_id] = []
                    logger.info(f"✅ Initialized empty chat history for channel {channel_id}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error in load_messages_for_channel: {e}")
            return []
    
    def load_more_messages_for_channel(self, channel_id: str, chat_widget=None):
        """Load older messages for a channel (pagination upwards)."""
        try:
            logger.info(f"🔄 Loading more messages for channel {channel_id}")
            
            if not self.community_manager:
                logger.warning("Community manager not available for loading more messages")
                return
            
            # Determine the 'before' cursor as the oldest currently cached message
            oldest_ts = None
            cached = self._message_cache.get(channel_id, [])
            if not cached:
                logger.info("No cached messages yet; skipping load-more to avoid duplicates")
                if chat_widget and hasattr(chat_widget, 'notify_load_more_complete'):
                    chat_widget.notify_load_more_complete()
                return []
            if cached:
                first = cached[0]
                oldest_ts = first.get('created_at')
            
            additional_messages = self.community_manager.get_messages(
                channel_id,
                limit=self._messages_per_page,
                before=oldest_ts
            )
            
            if additional_messages:
                # Prepend to cache
                if channel_id in self._message_cache:
                    self._message_cache[channel_id] = additional_messages + self._message_cache[channel_id]
                else:
                    self._message_cache[channel_id] = additional_messages
                
                self._loaded_message_counts[channel_id] = len(self._message_cache[channel_id])
                
                logger.info(f"✅ Loaded {len(additional_messages)} additional messages for channel {channel_id}")
                
                # Add messages to UI if widget provided
                if chat_widget:
                    if hasattr(chat_widget, 'prepend_messages'):
                        chat_widget.prepend_messages(additional_messages)
                    else:
                        # Fallback: re-render all (less ideal)
                        for message in additional_messages:
                            chat_widget.add_message(message)
                    if hasattr(chat_widget, 'notify_load_more_complete'):
                        chat_widget.notify_load_more_complete()
                
                return additional_messages
            else:
                logger.info(f"📭 No more messages available for channel {channel_id}")
                if chat_widget and hasattr(chat_widget, 'notify_load_more_complete'):
                    chat_widget.notify_load_more_complete()
                return []
                
        except Exception as e:
            logger.error(f"Error loading more messages for channel {channel_id}: {e}")
            try:
                if chat_widget and hasattr(chat_widget, 'notify_load_more_complete'):
                    chat_widget.notify_load_more_complete()
            except Exception:
                pass
            return []
    
    def clear_message_cache(self, channel_id: str = None):
        """Clear message cache for a specific channel or all channels."""
        try:
            if channel_id:
                if channel_id in self._message_cache:
                    del self._message_cache[channel_id]
                if channel_id in self._message_cache_timestamps:
                    del self._message_cache_timestamps[channel_id]
                if channel_id in self._loaded_message_counts:
                    del self._loaded_message_counts[channel_id]
                logger.info(f"🗑️ Cleared message cache for channel {channel_id}")
            else:
                self._message_cache.clear()
                self._message_cache_timestamps.clear()
                self._loaded_message_counts.clear()
                logger.info("🗑️ Cleared all message caches")
        except Exception as e:
            logger.error(f"Error clearing message cache: {e}")
    
    def refresh_messages_for_channel(self, channel_id: str, chat_widget=None):
        """Refresh messages for a channel (clear cache and reload)."""
        try:
            logger.info(f"🔄 Refreshing messages for channel {channel_id}")
            
            # Clear cache for this channel
            self.clear_message_cache(channel_id)
            
            # Reload messages
            return self.load_messages_for_channel(channel_id, chat_widget)
            
        except Exception as e:
            logger.error(f"Error refreshing messages for channel {channel_id}: {e}")
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
        # Prevent multiple updates
        if hasattr(self, '_input_field_updated') and self._input_field_updated:
            logger.info("🔄 Input field state already updated, skipping")
            return
        
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
                    # Also toggle the auth overlay for clearer UX
                    if hasattr(self.current_chat_widget, 'show_auth_overlay'):
                        self.current_chat_widget.show_auth_overlay(not is_authenticated)
                    logger.info(f"Updated input field state - authenticated: {is_authenticated}")
            
            self._input_field_updated = True
        except Exception as e:
            logger.error(f"Error updating input field state: {e}")
            self._input_field_updated = True  # Mark as done even on error

    def _ensure_auth_signal_connected(self):
        """Connect to the main window's auth_state_changed signal once."""
        if getattr(self, '_auth_signal_connected', False):
            return
        try:
            main_window = self.window()
            if hasattr(main_window, 'auth_state_changed'):
                main_window.auth_state_changed.connect(self.on_auth_state_changed)
                self._auth_signal_connected = True
                logger.info("✅ Connected community page to global auth_state_changed signal")
        except Exception as e:
            logger.error(f"Error connecting auth_state_changed signal: {e}")

    def on_auth_state_changed(self, authenticated: bool | None = None):
        """Handle login/logout while the community page is open."""
        try:
            if authenticated is None:
                try:
                    from trackpro.auth.user_manager import get_current_user
                    user = get_current_user()
                    authenticated = bool(user and user.is_authenticated)
                except Exception:
                    authenticated = False
            logger.info(f"🔄 Community page received auth change: authenticated={authenticated}")
            # Force re-evaluation of input/overlay state
            self._input_field_updated = False
            self.update_input_field_state()
            # Ensure community manager has the current user after login
            if authenticated:
                try:
                    self.set_current_user()
                except Exception:
                    pass
            # If now authenticated and a chat is open, ensure it is ready without page change
            if authenticated and hasattr(self, 'current_chat_widget') and self.current_chat_widget:
                # Optionally refresh messages or UI elements if needed; keep light
                pass
        except Exception as e:
            logger.error(f"Error handling auth state change on community page: {e}")
    
    def on_page_activated(self):
        """Called when the page is activated."""
        logger.info("🔄 Community page activated")
        # Ensure we are listening for auth changes
        self._ensure_auth_signal_connected()
        
        # Add a small delay to prevent rapid-fire initialization attempts
        import time
        if hasattr(self, '_last_activation_time'):
            time_since_last = time.time() - self._last_activation_time
            if time_since_last < 1.0:  # Less than 1 second since last activation
                logger.info(f"🔄 Activation too soon ({time_since_last:.2f}s), skipping")
                return
        self._last_activation_time = time.time()
        
        # Initialize heavy components if not already done
        if not getattr(self, '_initialization_complete', False):
            logger.info("🔧 Heavy components not initialized; starting initialization now...")
            try:
                self._initialize_heavy_components()
            except Exception as e:
                logger.error(f"❌ Error during heavy initialization on activation: {e}")
            # Small grace period for async startup pieces
            try:
                import time as _time
                _time.sleep(0.2)
            except Exception:
                pass
        
        # Only proceed with activation-specific tasks if not already done
        if not hasattr(self, '_activation_complete') or not self._activation_complete:
            # Refresh user state and set current user for community manager
            self.refresh_user_state()
            
            # Update input field state based on authentication
            self.update_input_field_state()
            
            # Refresh friends list to ensure it's loaded properly
            logger.info("🔄 Refreshing friends list on page activation...")
            self.load_friends_list()
            self.load_friend_requests()
            
            # Check voice server status (already started during pre-loading)
            if VOICE_COMPONENTS_AVAILABLE:
                try:
                    if is_voice_server_running():
                        logger.info("✅ Voice server is running (started during pre-loading)")
                    else:
                        logger.warning("⚠️ Voice server not running, may need manual start")
                except Exception as e:
                    logger.error(f"❌ Failed to check voice server status: {e}")
            
            # Data already loaded during pre-loading
            logger.info("📋 Channels and messages already loaded during pre-loading")
            
            self._activation_complete = True
            logger.info("✅ Community page activation completed")
        else:
            logger.info("🔄 Community page already activated, skipping re-initialization")
    
    def _initialize_heavy_components(self):
        """Initialize heavy components that were deferred during construction."""
        
        try:
            logger.info("🏗️ Initializing heavy community components...")
            # Initialize Community Manager safely
            try:
                logger.info("🔧 Attempting to initialize CommunityManager...")
                from trackpro.community.community_manager import CommunityManager
                # Prefer singleton if provided; otherwise construct
                if hasattr(CommunityManager, 'get_instance'):
                    self.community_manager = CommunityManager.get_instance()
                    logger.info("✅ CommunityManager instance created using singleton pattern")
                else:
                    self.community_manager = CommunityManager()
                    logger.info("✅ CommunityManager instance created normally")
                if not self._community_manager:
                    logger.error("❌ CommunityManager creation returned None")
            except Exception as import_error:
                logger.error(f"❌ Failed to initialize community manager: {import_error}")
                self.community_manager = None

            # Set current user (best-effort)
            try:
                self.set_current_user()
            except Exception as e:
                logger.warning(f"Could not set current user during init: {e}")

            # Verify user set; retry once briefly
            try:
                import time as _time
                current_user_id = None
                if hasattr(self, '_community_manager') and self._community_manager:
                    current_user_id = self._community_manager.get_current_user_id()
                if not current_user_id:
                    logger.info("🔁 Current user not set, retrying once...")
                    self.set_current_user()
                    _time.sleep(0.2)
            except Exception as e:
                logger.debug(f"User verification step failed: {e}")

            # Start voice server early if components available
            if VOICE_COMPONENTS_AVAILABLE:
                try:
                    if not is_voice_server_running():
                        logger.info("🎤 Starting voice server during initialization...")
                        start_voice_server()
                    else:
                        logger.info("✅ Voice server already running")
                except Exception as e:
                    logger.error(f"❌ Failed to start voice server: {e}")

            # Load core data
            try:
                logger.info("📋 Loading channels, private messages, friends, and requests...")
                self.load_channels_from_database()
                self.load_private_messages()
                self.load_friends_list()
                self.load_friend_requests()
                logger.info("✅ Community data loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load community data: {e}")

            self._initialization_complete = True
            CommunityPage._heavy_components_initialized = True
            logger.info("✅ Heavy components initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize heavy components: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            CommunityPage._heavy_components_initialized = True  # Set flag even on error to prevent retries
    
    def refresh_user_state(self):
        """Refresh user authentication state and set current user."""
        # Prevent unnecessary repeats, but allow if current_user_id is still missing
        if hasattr(self, '_user_state_refreshed') and self._user_state_refreshed:
            try:
                current_user_id = None
                if hasattr(self, '_community_manager') and self._community_manager:
                    current_user_id = self._community_manager.get_current_user_id()
                if current_user_id:
                    logger.info("🔄 User state already refreshed, skipping")
                    return
                else:
                    logger.info("🔁 User state was refreshed earlier but no current user set; retrying")
            except Exception:
                pass
            
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
            
            self._user_state_refreshed = True
            
        except Exception as e:
            logger.warning(f"Failed to refresh user state: {e}")
            self._user_state_refreshed = True  # Mark as done even on error
    
    def on_voice_error(self, error_message):
        """Handle voice chat errors."""
        logger.error(f"🎤 Voice chat error: {error_message}")
        
        # Show error to user
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Voice Chat Error", error_message)
    
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
        
        # Cleanup all voice managers
        try:
            # Cleanup central voice manager
            if hasattr(self, '_central_voice_manager') and self._central_voice_manager:
                try:
                    # Use force cleanup during application shutdown
                    if hasattr(self._central_voice_manager, 'force_cleanup'):
                        self._central_voice_manager.force_cleanup()
                    else:
                        self._central_voice_manager.stop_voice_chat()
                    logger.info("✅ Central voice manager cleaned up")
                except Exception as e:
                    logger.error(f"Error cleaning up central voice manager: {e}")
            
            # Cleanup all voice managers in the list
            for voice_manager in getattr(self, '_voice_managers', []):
                try:
                    if hasattr(voice_manager, 'force_cleanup'):
                        voice_manager.force_cleanup()
                    elif hasattr(voice_manager, 'stop_voice_chat'):
                        voice_manager.stop_voice_chat()
                except Exception as e:
                    logger.error(f"Error cleaning up voice manager: {e}")
            
            logger.info("✅ All voice managers cleaned up")
        except Exception as e:
            logger.error(f"Error during voice manager cleanup: {e}")
        
        # Cleanup real-time subscriptions
        try:
            if hasattr(self, 'community_manager') and self.community_manager:
                if hasattr(self.community_manager, 'client') and self.community_manager.client:
                    # Check if client has the remove_all_subscriptions method
                    if hasattr(self.community_manager.client, 'remove_all_subscriptions'):
                        # Unsubscribe from real-time updates
                        self.community_manager.client.remove_all_subscriptions()
                        logger.info("✅ Cleaned up real-time subscriptions")
                    else:
                        logger.warning("Client does not have remove_all_subscriptions method")
        except Exception as e:
            logger.error(f"Error cleaning up real-time subscriptions: {e}")
    
    def set_current_user(self):
        """Set the current authenticated user in the community manager."""
        try:
            # During initialization, access _community_manager directly to avoid recursion
            community_manager = getattr(self, '_community_manager', None)
            if not community_manager:
                logger.warning("Community manager not available")
                return
                
            logger.info("🔄 Setting current user in community manager...")
            
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
                            community_manager.set_current_user(temp_user.id)
                            logger.info(f"✅ Set current user from Supabase session: {temp_user.email} (ID: {temp_user.id})")
                            return
                except Exception as e:
                    logger.debug(f"Could not get user from Supabase session: {e}")
                
                # User manager not ready yet - skip setting current user
                logger.info("🔍 User manager not ready yet - skipping current user setting")
                return
                
            if user and user.is_authenticated:
                community_manager.set_current_user(user.id)
                logger.info(f"✅ Set current user: {user.email} (ID: {user.id})")
            else:
                logger.warning("User not authenticated")
                
        except Exception as e:
            logger.warning(f"Failed to set current user: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def on_message_received(self, message_data):
        """Handle new message received from database."""
        channel_id = message_data.get('channel_id')
        logger.info(f"🔄 Real-time message received for channel: {channel_id}")
        
        # Initialize chat history for this channel if it doesn't exist
        if not hasattr(self, 'chat_history'):
            self.chat_history = {}
        if channel_id and channel_id not in self.chat_history:
            self.chat_history[channel_id] = []
        
        if channel_id:
            # Add message to chat history
            self.chat_history[channel_id].append(message_data)
            logger.info(f"✅ Added message to chat history for channel: {channel_id}")
            
            # Update UI if this channel is currently displayed
            if self.current_channel == channel_id:
                logger.info(f"🔄 Updating UI for current channel: {channel_id}")
                # Append to UI and prune old messages beyond cap
                self.add_message_to_ui(message_data)
                try:
                    cached = self._message_cache.get(channel_id, [])
                    if cached:
                        cached.append(message_data)
                        if len(cached) > self._max_messages_in_ui:
                            overflow = len(cached) - self._max_messages_in_ui
                            self._message_cache[channel_id] = cached[overflow:]
                            # Optionally, prune UI items as well
                            if hasattr(self, 'current_chat_widget') and getattr(self, 'current_chat_widget', None):
                                to_remove = min(overflow, self.current_chat_widget.messages_list.count())
                                for _ in range(to_remove):
                                    itm = self.current_chat_widget.messages_list.takeItem(0)
                                    del itm
                    else:
                        self._message_cache[channel_id] = [message_data]
                except Exception:
                    pass
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
        # Prevent multiple loads using class-level flag
        if CommunityPage._channels_loaded:
            logger.info("🔄 Channels already loaded, skipping")
            return
            
        try:
            # During initialization, access _community_manager directly to avoid recursion
            community_manager = getattr(self, '_community_manager', None)
            if not community_manager:
                logger.warning("Community manager not available, using fallback channels")
                self.load_fallback_channels()
                CommunityPage._channels_loaded = True
                return
                
            logger.info("Loading channels from database...")
            channels = community_manager.get_channels()
            logger.info(f"Received {len(channels)} channels from community manager")
            
            logger.info(f"🧹 Clearing channel lists - Text channels: {self.channel_list.count()}, Voice channels: {self.voice_channels_list.count()}")
            self.channel_list.clear()
            self.voice_channels_list.clear()
            logger.info("✅ Channel lists cleared")
            
            # Check if we got any channels from the database
            if not channels:
                logger.warning("No channels returned from database, using fallback channels")
                self.load_fallback_channels()
                return
            
            text_channels_count = 0
            voice_channels_count = 0
            
            for channel in channels:
                channel_name = channel['name']
                channel_type = channel['channel_type']
                
                logger.info(f"📋 Processing channel: {channel_name} (type: {channel_type})")
                
                # Format display name
                if channel_type == 'text':
                    display_name = f"# {channel_name}"
                    target_list = self.channel_list
                    text_channels_count += 1
                    logger.info(f"📝 Added text channel: {display_name}")
                else:
                    display_name = f"🔊 {channel_name}"
                    target_list = self.voice_channels_list
                    voice_channels_count += 1
                    logger.info(f"🔊 Added voice channel: {display_name}")
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'id': channel['channel_id'],
                    'name': channel_name,
                    'type': channel_type
                })
                target_list.addItem(item)
            
            logger.info(f"Loaded {text_channels_count} text channels and {voice_channels_count} voice channels")
            logger.info(f"📊 Final state - Text channels: {self.channel_list.count()}, Voice channels: {self.voice_channels_list.count()}")
            
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
            
            # Mark as loaded using class-level flag
            CommunityPage._channels_loaded = True
                
        except Exception as e:
            logger.error(f"Error loading channels from database: {e}")
            # Fallback to hardcoded channels
            self.load_fallback_channels()
            CommunityPage._channels_loaded = True
    
    def load_fallback_channels(self):
        """Load fallback channels when database is unavailable."""
        logger.info("Loading fallback channels...")
        
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
            logger.info(f"🔊 Adding fallback voice channel: {channel_name}")
            item = QListWidgetItem(channel_name)
            item.setData(Qt.ItemDataRole.UserRole, {
                'id': channel_id,
                'name': channel_name.replace('# ', '').replace('🔊 ', ''),
                'type': channel_type
            })
            self.voice_channels_list.addItem(item)
        
        logger.info(f"Loaded {len(text_channels)} text channels and {len(voice_channels)} voice channels as fallback")
        
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
        # Prevent multiple loads using class-level flag
        if CommunityPage._private_messages_loaded:
            logger.info("🔄 Private messages already loaded, skipping")
            return
            
        try:
            # During initialization, access _community_manager directly to avoid recursion
            community_manager = getattr(self, '_community_manager', None)
            if not community_manager:
                logger.warning("Community manager not available, using fallback private messages")
                self.load_fallback_private_messages()
                CommunityPage._private_messages_loaded = True
                return
                
            conversations = community_manager.get_private_conversations()
            self.private_messages_list.clear()
            
            for conversation in conversations:
                # Respect local deletion cutoff for last_message preview
                try:
                    cutoff = self._get_local_delete_cutoff(conversation.get('conversation_id'))
                    if cutoff:
                        last_msg = conversation.get('last_message') or {}
                        created_at = last_msg.get('created_at')
                        if created_at and not self._is_after_cutoff(created_at, cutoff):
                            conversation['last_message'] = None
                except Exception:
                    pass
                # Create conversation list item widget
                conversation_widget = PrivateConversationListItem(conversation)
                conversation_widget.conversation_selected.connect(self.on_private_conversation_selected)
                
                item = QListWidgetItem()
                item.setSizeHint(conversation_widget.sizeHint())
                
                self.private_messages_list.addItem(item)
                self.private_messages_list.setItemWidget(item, conversation_widget)
            
            # Mark as loaded using class-level flag
            CommunityPage._private_messages_loaded = True
                
        except Exception as e:
            logger.error(f"Error loading private messages: {e}")
            self.load_fallback_private_messages()
            CommunityPage._private_messages_loaded = True
    
    def load_fallback_private_messages(self):
        """Load fallback private messages when database is unavailable."""
        # For now, we'll show a placeholder message
        placeholder_item = QListWidgetItem("No private messages yet")
        # Note: QListWidgetItem doesn't have setStyleSheet, styling is done via the widget
        self.private_messages_list.addItem(placeholder_item)
    
    def refresh_private_messages(self):
        """Refresh private messages list (bypasses the class-level flag for updates)."""
        try:
            if not self.community_manager:
                logger.warning("Community manager not available, cannot refresh private messages")
                return
                
            conversations = self.community_manager.get_private_conversations()
            self.private_messages_list.clear()
            
            for conversation in conversations:
                # Respect local deletion cutoff for last_message preview
                try:
                    cutoff = self._get_local_delete_cutoff(conversation.get('conversation_id'))
                    if cutoff:
                        last_msg = conversation.get('last_message') or {}
                        created_at = last_msg.get('created_at')
                        if created_at and not self._is_after_cutoff(created_at, cutoff):
                            conversation['last_message'] = None
                except Exception:
                    pass
                # Create conversation list item widget
                conversation_widget = PrivateConversationListItem(conversation)
                conversation_widget.conversation_selected.connect(self.on_private_conversation_selected)
                
                item = QListWidgetItem()
                item.setSizeHint(conversation_widget.sizeHint())
                
                self.private_messages_list.addItem(item)
                self.private_messages_list.setItemWidget(item, conversation_widget)
                
        except Exception as e:
            logger.error(f"Error refreshing private messages: {e}")
    
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
            
            # Always get conversation data from database for reliability
            logger.info(f"🔍 Fetching conversation data for ID: {conversation_id}")
            conversation_data = self.community_manager.get_conversation_data(conversation_id)
            
            if not conversation_data:
                logger.error(f"Conversation data not found for ID: {conversation_id}")
                return
            
            logger.info(f"✅ Got conversation data: {conversation_data.get('conversation_id', 'No ID')}")
            
            # Create conversation widget with proper user data (parented to content area)
            conversation_widget = PrivateConversationWidget(conversation_data, parent=self.content_stack)
            conversation_widget.message_sent.connect(lambda text: self.on_private_message_sent(conversation_id, text))
            
            # Add messages to the conversation with proper user data
            current_user_id = None
            try:
                from ...auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    current_user_id = user.id
            except Exception as e:
                logger.debug(f"Could not get current user: {e}")
            
            # Apply local deletion cutoff to message history (client-side only)
            try:
                cutoff = self._get_local_delete_cutoff(conversation_id)
                if cutoff:
                    messages = [m for m in messages if self._is_after_cutoff(m.get('created_at'), cutoff)]
            except Exception:
                pass

            for message in messages:
                is_own_message = current_user_id and message.get('sender_id') == current_user_id
                # Ensure message has proper user data
                if not message.get('user_profiles'):
                    # Try to get user data from the conversation data
                    sender_id = message.get('sender_id')
                    if sender_id == current_user_id:
                        # This is the current user's message
                        message['user_profiles'] = {
                            'user_id': sender_id,
                            'display_name': 'You',
                            'username': 'You'
                        }
                    else:
                        # This is the other user's message
                        other_user = conversation_data.get('other_user', {})
                        message['user_profiles'] = other_user
                
                conversation_widget.add_message(message, is_own_message)
            
            # Show the conversation inline
            logger.info("🔄 About to show private conversation inline")
            self.show_private_conversation(conversation_widget)
            logger.info("✅ Private conversation should now be displayed inline")
            
        except Exception as e:
            logger.error(f"Error showing private conversation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
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
                self.refresh_private_messages()
            else:
                logger.error("Failed to send private message")
                
        except Exception as e:
            logger.error(f"Error sending private message: {e}")

    # ----------------------------
    # Local-only Delete Chat support
    # ----------------------------
    def on_private_messages_context_menu(self, pos):
        try:
            from PyQt6.QtWidgets import QMenu
            item = self.private_messages_list.itemAt(pos)
            if not item:
                return
            widget = self.private_messages_list.itemWidget(item)
            conversation_id = getattr(widget, 'conversation_id', None) or getattr(widget, 'conversation_data', {}).get('conversation_id')
            if not conversation_id:
                return
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Chat")
            action = menu.exec(self.private_messages_list.mapToGlobal(pos))
            if action == delete_action:
                self._mark_chat_deleted_locally(conversation_id)
                # If this conversation is currently open, clear the view
                try:
                    if getattr(self, 'current_conversation_widget', None) and self.current_conversation_widget.conversation_id == conversation_id:
                        lst = self.current_conversation_widget.messages_list
                        lst.clear()
                except Exception:
                    pass
                # Refresh sidebar
                self.refresh_private_messages()
        except Exception:
            pass

    def _get_local_delete_cutoff(self, conversation_id: str):
        try:
            import json, os
            from ...utils.resource_utils import get_data_directory
            # Identify current user
            try:
                from ...auth.user_manager import get_current_user
                user = get_current_user()
                uid = user.id if (user and getattr(user, 'is_authenticated', False)) else None
            except Exception:
                uid = None
            if not uid:
                return None
            path = os.path.join(get_data_directory(), 'deleted_private_chats.json')
            if not os.path.exists(path):
                return None
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            return (data.get(str(uid)) or {}).get(str(conversation_id))
        except Exception:
            return None

    def _mark_chat_deleted_locally(self, conversation_id: str):
        try:
            import json, os
            from datetime import datetime as _dt
            from ...utils.resource_utils import get_data_directory
            # Identify current user
            try:
                from ...auth.user_manager import get_current_user
                user = get_current_user()
                uid = user.id if (user and getattr(user, 'is_authenticated', False)) else None
            except Exception:
                uid = None
            if not uid:
                return
            path = os.path.join(get_data_directory(), 'deleted_private_chats.json')
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
            data.setdefault(str(uid), {})[str(conversation_id)] = _dt.utcnow().isoformat() + 'Z'
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _is_after_cutoff(self, created_at: str, cutoff_iso: str) -> bool:
        try:
            from datetime import datetime as _dt
            if not created_at:
                return False
            # Normalize ISO strings
            def _parse(s: str):
                try:
                    return _dt.fromisoformat(s.replace('Z', '+00:00'))
                except Exception:
                    return None
            msg_dt = _parse(created_at)
            cut_dt = _parse(cutoff_iso)
            if not msg_dt or not cut_dt:
                return False
            return msg_dt > cut_dt
        except Exception:
            return False
    
    def on_new_private_message_clicked(self):
        """Handle new private message button click."""
        try:
            # Show an enhanced dialog to select a user to message
            from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                        QLineEdit, QPushButton, QMessageBox, QTabWidget,
                                        QListWidget, QListWidgetItem, QFrame, QSplitter)
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont, QColor
            
            dialog = QDialog(self)
            dialog.setWindowTitle("New Private Message")
            dialog.setFixedSize(500, 400)
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
                QTabWidget::pane {
                    border: 1px solid #202225;
                    background-color: #2f3136;
                }
                QTabBar::tab {
                    background-color: #40444b;
                    color: #dcddde;
                    padding: 8px 16px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #5865f2;
                }
                QListWidget {
                    background-color: #40444b;
                    border: 1px solid #202225;
                    color: #dcddde;
                }
                QListWidget::item {
                    padding: 8px;
                    border: none;
                }
                QListWidget::item:selected {
                    background-color: #5865f2;
                }
                QListWidget::item:hover {
                    background-color: #4752c4;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Create tab widget
            tab_widget = QTabWidget()
            
            # Tab 1: Friends
            friends_tab = QWidget()
            friends_layout = QVBoxLayout(friends_tab)
            
            friends_label = QLabel("Select a friend to start a conversation:")
            friends_layout.addWidget(friends_label)
            
            self.friends_selection_list = QListWidget()
            friends_layout.addWidget(self.friends_selection_list)
            
            # Load friends into the list
            self.load_friends_for_selection()
            
            tab_widget.addTab(friends_tab, "Friends")
            
            # Tab 2: Username
            username_tab = QWidget()
            username_layout = QVBoxLayout(username_tab)
            
            username_label = QLabel("Enter username to start a conversation:")
            username_layout.addWidget(username_label)
            
            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText("Enter username...")
            username_layout.addWidget(self.username_input)
            
            tab_widget.addTab(username_tab, "Username")
            
            layout.addWidget(tab_widget)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            start_btn = QPushButton("Start Conversation")
            start_btn.clicked.connect(lambda: self.start_private_conversation_from_dialog(dialog))
            button_layout.addWidget(start_btn)
            
            layout.addLayout(button_layout)
            
            # Show dialog
            result = dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing new private message dialog: {e}")
    
    def load_friends_for_selection(self):
        """Load friends into the selection list."""
        try:
            self.friends_selection_list.clear()
            
            if not self.community_manager:
                logger.warning("Community manager not available for loading friends")
                return
            
            # Get real friends from database
            friends = self.community_manager.get_friends()
            
            for friend in friends:
                display_name = friend.get('display_name', 'Unknown User')
                status = friend.get('status', 'Offline')
                item = QListWidgetItem(f"{display_name} ({status})")
                item.setData(Qt.ItemDataRole.UserRole, friend)
                self.friends_selection_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading friends for selection: {e}")
    
    def start_private_conversation_from_dialog(self, dialog):
        """Start a private conversation from the dialog."""
        try:
            # Check which tab is active
            current_tab = dialog.findChild(QTabWidget).currentIndex()
            
            if current_tab == 0:  # Friends tab
                # Get selected friend
                selected_items = self.friends_selection_list.selectedItems()
                if not selected_items:
                    QMessageBox.warning(dialog, "Error", "Please select a friend.")
                return
            
                friend_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
                username = friend_data.get('username')
                
            else:  # Username tab
                username = self.username_input.text().strip()
                if not username:
                    QMessageBox.warning(dialog, "Error", "Please enter a username.")
                    return
            
            # Get user by username
            if not self.community_manager:
                QMessageBox.warning(dialog, "Error", "Community manager not available.")
                return
            
            # Create conversation
            conversation_id = self.community_manager.get_or_create_conversation(username)
            
            if conversation_id:
                dialog.accept()
                # Load and show the conversation
                self.on_private_conversation_selected(conversation_id)
            else:
                QMessageBox.warning(dialog, "Error", f"Could not find user '{username}' or create conversation.")
                
        except Exception as e:
            logger.error(f"Error starting private conversation from dialog: {e}")
            QMessageBox.critical(dialog, "Error", f"An error occurred: {str(e)}")
    
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
    
    def on_add_friend_clicked(self):
        """Handle add friend button click."""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
            from PyQt6.QtCore import Qt
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Friend")
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
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Title
            title_label = QLabel("Enter username to add as friend:")
            layout.addWidget(title_label)
            
            # Username input
            self.add_friend_input = QLineEdit()
            self.add_friend_input.setPlaceholderText("Enter username...")
            layout.addWidget(self.add_friend_input)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            add_btn = QPushButton("Add Friend")
            add_btn.clicked.connect(lambda: self.add_friend_from_dialog(dialog))
            button_layout.addWidget(add_btn)
            
            layout.addLayout(button_layout)
            
            # Show dialog
            result = dialog.exec()
                
        except Exception as e:
            logger.error(f"Error showing add friend dialog: {e}")
    
    def add_friend_from_dialog(self, dialog):
        """Add friend from dialog."""
        try:
            username = self.add_friend_input.text().strip()
            if not username:
                QMessageBox.warning(dialog, "Error", "Please enter a username.")
                return
            
            if not self.community_manager:
                logger.error("Community manager not available for sending friend request")
                QMessageBox.warning(dialog, "Error", "Community manager not available.")
                return
            
            # Send friend request using the community manager
            success = self.community_manager.send_friend_request(username)
            
            if success:
                logger.info(f"Friend request sent to {username}")
                QMessageBox.information(dialog, "Success", f"Friend request sent to {username}")
                dialog.accept()
            else:
                logger.error(f"Failed to send friend request to {username}")
                QMessageBox.warning(dialog, "Error", f"Failed to send friend request to {username}. User may not exist or request already sent.")
            
        except Exception as e:
            logger.error(f"Error adding friend: {e}")
            QMessageBox.critical(dialog, "Error", f"An error occurred: {str(e)}")
    
    def on_friend_selected(self, item):
        """Handle friend selection."""
        try:
            friend_data = item.data(Qt.ItemDataRole.UserRole)
            if friend_data:
                # Start a private conversation with the friend
                self.start_private_conversation_with_user(friend_data)
            else:
                logger.warning("No friend data found in selected item")
        except Exception as e:
            logger.error(f"Error handling friend selection: {e}")
    
    def on_friend_request_selected(self, item):
        """Handle friend request selection."""
        try:
            request_data = item.data(Qt.ItemDataRole.UserRole)
            if request_data:
                # Show friend request actions
                self.show_friend_request_actions(request_data)
            else:
                logger.warning("No request data found in selected item")
        except Exception as e:
            logger.error(f"Error handling friend request selection: {e}")
    
    def show_friend_request_actions(self, request_data):
        """Show actions for a friend request."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            username = request_data.get('username', 'Unknown')
            message = f"Friend request from {username}\n\nAccept or decline?"
            
            reply = QMessageBox.question(
                self, 
                "Friend Request", 
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.accept_friend_request(request_data)
            else:
                self.decline_friend_request(request_data)
            
        except Exception as e:
            logger.error(f"Error showing friend request actions: {e}")
    
    def accept_friend_request(self, request_data):
        """Accept a friend request."""
        try:
            friendship_id = request_data.get('friendship_id')
            display_name = request_data.get('display_name', 'Unknown')
            
            if not friendship_id:
                logger.error("No friendship ID provided for accepting friend request")
                return
            
            if not self.community_manager:
                logger.error("Community manager not available for accepting friend request")
                return
            
            # Accept the friend request using the community manager
            success = self.community_manager.accept_friend_request(friendship_id)
            
            if success:
                logger.info(f"Friend request from {display_name} accepted!")
                QMessageBox.information(self, "Success", f"Friend request from {display_name} accepted!")
                # Refresh the friend requests list
                self.load_friend_requests()
                # Refresh the friends list
                self.load_friends_list()
            else:
                logger.error(f"Failed to accept friend request from {display_name}")
                QMessageBox.warning(self, "Error", f"Failed to accept friend request from {display_name}")
                
        except Exception as e:
            logger.error(f"Error accepting friend request: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def decline_friend_request(self, request_data):
        """Decline a friend request."""
        try:
            friendship_id = request_data.get('friendship_id')
            display_name = request_data.get('display_name', 'Unknown')
            
            if not friendship_id:
                logger.error("No friendship ID provided for declining friend request")
                return
            
            if not self.community_manager:
                logger.error("Community manager not available for declining friend request")
                return
            
            # Decline the friend request using the community manager
            success = self.community_manager.decline_friend_request(friendship_id)
            
            if success:
                logger.info(f"Friend request from {display_name} declined!")
                QMessageBox.information(self, "Success", f"Friend request from {display_name} declined.")
                # Refresh the friend requests list
                self.load_friend_requests()
            else:
                logger.error(f"Failed to decline friend request from {display_name}")
                QMessageBox.warning(self, "Error", f"Failed to decline friend request from {display_name}")
                
        except Exception as e:
            logger.error(f"Error declining friend request: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def load_friends_list(self):
        """Load friends list."""
        try:
            self.friends_list.clear()
            
            if not self.community_manager:
                logger.warning("Community manager not available for loading friends")
                return
            
            logger.info("🔄 Loading friends list from database...")
            
            # Get real friends from database
            friends = self.community_manager.get_friends()
            logger.info(f"📋 Retrieved {len(friends)} friends from database")
            
            if not friends:
                logger.warning("⚠️ No friends found in database")
                # Add a placeholder item to show "No friends" message
                empty_item = QListWidgetItem("No friends found")
                empty_item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
                self.friends_list.addItem(empty_item)
                return
            
            for friend in friends:
                display_name = friend.get('display_name', 'Unknown User')
                status = friend.get('status', 'Offline')
                user_id = friend.get('user_id', 'Unknown')
                avatar_url = friend.get('avatar_url')
                
                logger.info(f"👤 Adding friend: {display_name} ({status}) - ID: {user_id}")
                
                # Create friend item with status indicator
                status_icon = "🟢" if status == "Online" else "⚫"
                item_text = f"{status_icon} {display_name}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, friend)
                
                # Set color based on status
                if status == "Online":
                    item.setForeground(QColor('#44ff44'))  # Green for online
                else:
                    item.setForeground(QColor('#888888'))  # Gray for offline
                
                self.friends_list.addItem(item)
            
            logger.info(f"✅ Successfully loaded {len(friends)} friends")
                
        except Exception as e:
            logger.error(f"❌ Error loading friends list: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            
            # Add error item to show something went wrong
            error_item = QListWidgetItem("Error loading friends")
            error_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.friends_list.addItem(error_item)
    
    def load_friend_requests(self):
        """Load friend requests list."""
        try:
            self.friend_requests_list.clear()
            
            if not self.community_manager:
                logger.warning("Community manager not available for loading friend requests")
                return
                
            # Get real friend requests from database
            requests = self.community_manager.get_friend_requests()
            
            for request in requests:
                display_name = request.get('display_name', 'Unknown User')
                status = request.get('status', 'Pending')
                item = QListWidgetItem(f"{display_name} ({status})")
                item.setData(Qt.ItemDataRole.UserRole, request)
                self.friend_requests_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading friend requests: {e}")
    
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
    
    def start_direct_private_message(self, user_data):
        """Start a direct private message with a user (called from other widgets)."""
        try:
            logger.info(f"🔄 Starting direct private message with user: {user_data.get('display_name', 'Unknown')}")
            
            # Switch to community page first
            main_window = self.window()
            if main_window and hasattr(main_window, 'switch_to_page'):
                main_window.switch_to_page("community")
            
            # Start the private conversation
            self.start_private_conversation_with_user(user_data)
            
        except Exception as e:
            logger.error(f"Error starting direct private message: {e}")
    
    def show_private_conversation(self, conversation_widget):
        """Show private conversation in the main content area like a regular channel."""
        try:
            logger.info("🔄 Switching to private conversation view")
            
            # Store the conversation widget for potential reuse
            self.current_conversation_widget = conversation_widget
            
            # Ensure a single persistent layout on content_stack
            try:
                from PyQt6.QtWidgets import QVBoxLayout
                # Always get the actual current layout from the live widget
                layout = self.content_stack.layout()
                if layout is None:
                    layout = QVBoxLayout(self.content_stack)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(0)
                # Keep a reference for future use but don't rely on it
                self.content_stack_layout = layout
                # Clear existing widgets from the layout
                while layout.count() > 0:
                    item = layout.takeAt(0)
                    if item and item.widget():
                        item.widget().setParent(None)
                # Add the conversation widget with stretch so it fills the area
                layout.addWidget(conversation_widget, 1)
            except Exception:
                # Fallback: show the widget directly
                conversation_widget.setParent(self.content_stack)
                conversation_widget.show()
            
            conversation_widget.show()
            
            # Update the channel display to show it's a private conversation
            self.update_channel_display_for_private_conversation(conversation_widget)
            
            logger.info("✅ Private conversation view displayed inline")
            # Ensure the Chat tab is active and input focused
            try:
                if hasattr(self, 'content_tabs'):
                    self.content_tabs.setCurrentIndex(0)
            except Exception:
                pass
            try:
                if hasattr(conversation_widget, 'message_input'):
                    conversation_widget.message_input.setFocus()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Error showing private conversation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def update_channel_display_for_private_conversation(self, conversation_widget):
        """Update the channel display area to show private conversation info."""
        try:
            # Get conversation data from the widget
            conversation_data = getattr(conversation_widget, 'conversation_data', {})
            other_user = conversation_data.get('other_user', {})
            
            # Update the channel name display
            if hasattr(self, 'channel_name_label'):
                user_name = other_user.get('display_name') or other_user.get('username') or 'Unknown User'
                self.channel_name_label.setText(f"💬 {user_name}")
                self.channel_name_label.setStyleSheet("""
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 10px;
                    background-color: #2c2f33;
                    border-bottom: 1px solid #404040;
                """)
            
            # Update the channel description
            if hasattr(self, 'channel_description_label'):
                self.channel_description_label.setText("Private conversation")
                self.channel_description_label.setStyleSheet("""
                    color: #888888;
                    font-size: 12px;
                    padding: 5px 10px;
                """)
                
        except Exception as e:
            logger.error(f"Error updating channel display for private conversation: {e}")
    
    def show_voice_debug_info(self):
        """Show debug information about voice chat status."""
        try:
            debug_info = []
            
            # Check voice server status
            if VOICE_SERVER_AVAILABLE:
                server_running = is_voice_server_running()
                debug_info.append(f"Voice Server: {'✅ Running' if server_running else '❌ Not Running'}")
            else:
                debug_info.append("Voice Server: ❌ Not Available")
            
            # Check voice components
            debug_info.append(f"Voice Components: {'✅ Available' if VOICE_COMPONENTS_AVAILABLE else '❌ Not Available'}")
            debug_info.append(f"Simple Voice Client: {'✅ Available' if SIMPLE_VOICE_AVAILABLE else '❌ Not Available'}")
            debug_info.append(f"PyAudio: {'✅ Available' if PYAUDIO_AVAILABLE else '❌ Not Available'}")
            
            # Check current voice connection
            if hasattr(self, 'voice_client'):
                connected = self.voice_client.is_connected()
                debug_info.append(f"Voice Client: {'✅ Connected' if connected else '❌ Disconnected'}")
            else:
                debug_info.append("Voice Client: ❌ Not Initialized")
            
            # Check voice server connection
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 8080))
                sock.close()
                debug_info.append(f"Server Port 8080: {'✅ Accessible' if result == 0 else '❌ Not Accessible'}")
            except Exception as e:
                debug_info.append(f"Server Port 8080: ❌ Error checking - {e}")
            
            # Show debug info
            debug_text = "\n".join(debug_info)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Voice Chat Debug Info", 
                                  f"Voice Chat Status:\n\n{debug_text}")
            
        except Exception as e:
            logger.error(f"Error showing voice debug info: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Debug Error", f"Error getting debug info: {str(e)}")
    
    def add_debug_button(self):
        """Add debug button to the UI for troubleshooting."""
        # Removed debug button to avoid layout issues
        # The community page already has proper error handling and logging
        pass
    
    @property
    def community_manager(self):
        """Safely access the community manager, initializing if needed."""
        # Only initialize if not already complete and not currently initializing
        # Also check if we're not already in the initialization process to prevent recursion
        if (not self._initialization_complete and 
            not CommunityPage._heavy_components_initialized and 
            not hasattr(self, '_initializing')):
            logger.info("🔄 Community manager requested but not initialized, triggering initialization...")
            self._initializing = True
            try:
                self._initialize_heavy_components()
            finally:
                self._initializing = False
        # If still not available due to heavy init being skipped, create lazily now
        if self._community_manager is None:
            try:
                from ....community.community_manager import CommunityManager
                self.community_manager = CommunityManager()
                # Ensure current user is set for messaging
                try:
                    self.set_current_user()
                except Exception as e:
                    logger.debug(f"Could not set current user on lazy init: {e}")
            except Exception as e:
                logger.error(f"❌ Failed to lazily create CommunityManager: {e}")
        # Return the manager (may be None if initialization failed)
        return self._community_manager
    
    @community_manager.setter
    def community_manager(self, value):
        """Set the community manager."""
        self._community_manager = value
        # Connect signals when community manager is set
        if value:
            try:
                if not hasattr(self, '_signals_connected') or not self._signals_connected:
                    value.message_received.connect(self.on_message_received)
                    value.user_joined_channel.connect(self.on_user_joined_channel)
                    value.user_left_channel.connect(self.on_user_left_channel)
                    value.user_status_changed.connect(self.on_user_status_changed)
                    self._signals_connected = True
                    logger.info("✅ Connected community manager signals for realtime updates")
                else:
                    logger.info("🔄 Community manager signals already connected")
            except Exception as e:
                logger.error(f"❌ Error connecting community manager signals: {e}")
    
    def test_voice_server_connection(self):
        """Test voice server connection and provide detailed feedback."""
        try:
            debug_info = []
            
            # Test 1: Check if voice server is running
            if VOICE_SERVER_AVAILABLE:
                server_running = is_voice_server_running()
                debug_info.append(f"1. Voice Server Status: {'✅ Running' if server_running else '❌ Not Running'}")
                
                if not server_running:
                    debug_info.append("   → Attempting to start voice server...")
                    try:
                        start_voice_server()
                        import time
                        time.sleep(3)
                        
                        if is_voice_server_running():
                            debug_info.append("   ✅ Voice server started successfully")
                        else:
                            debug_info.append("   ❌ Voice server failed to start")
                    except Exception as e:
                        debug_info.append(f"   ❌ Error starting voice server: {e}")
            else:
                debug_info.append("1. Voice Server: ❌ Not Available")
            
            # Test 2: Check port accessibility
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', 8080))
                sock.close()
                
                if result == 0:
                    debug_info.append("2. Port 8080: ✅ Accessible")
                else:
                    debug_info.append("2. Port 8080: ❌ Not Accessible")
                    debug_info.append("   → Voice server may not be running or port is blocked")
            except Exception as e:
                debug_info.append(f"2. Port 8080: ❌ Error checking - {e}")
            
            # Test 3: Check voice components
            debug_info.append(f"3. Voice Components: {'✅ Available' if VOICE_COMPONENTS_AVAILABLE else '❌ Not Available'}")
            debug_info.append(f"4. Simple Voice Client: {'✅ Available' if SIMPLE_VOICE_AVAILABLE else '❌ Not Available'}")
            debug_info.append(f"5. PyAudio: {'✅ Available' if PYAUDIO_AVAILABLE else '❌ Not Available'}")
            
            # Test 4: Try to create a simple voice client
            if SIMPLE_VOICE_AVAILABLE:
                try:
                    test_client = SimpleVoiceClient()
                    debug_info.append("6. Voice Client Creation: ✅ Successful")
                except Exception as e:
                    debug_info.append(f"6. Voice Client Creation: ❌ Failed - {e}")
            else:
                debug_info.append("6. Voice Client Creation: ❌ Not Available")
            
            # Show results
            debug_text = "\n".join(debug_info)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Voice Server Connection Test", 
                                  f"Voice Server Connection Test Results:\n\n{debug_text}")
            
        except Exception as e:
            logger.error(f"Error testing voice server connection: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Test Error", f"Error running connection test: {str(e)}")
    
    def test_supabase_connection(self):
        """Test Supabase connection and provide detailed feedback."""
        try:
            debug_info = []
            
            # Test 1: Check if Supabase client can be imported
            try:
                from ....database.supabase_client import get_supabase_client
                debug_info.append("1. Supabase Client Import: ✅ Successful")
            except ImportError as e:
                debug_info.append(f"1. Supabase Client Import: ❌ Failed - {e}")
                return
            
            # Test 2: Try to get Supabase client
            try:
                client = get_supabase_client()
                if client:
                    debug_info.append("2. Supabase Client Creation: ✅ Successful")
                else:
                    debug_info.append("2. Supabase Client Creation: ❌ Failed - client is None")
                    debug_info.append("   → This usually means Supabase configuration is missing or incorrect")
            except Exception as e:
                debug_info.append(f"2. Supabase Client Creation: ❌ Failed - {e}")
            
            # Test 3: Check config
            try:
                from ....config import config
                debug_info.append(f"3. Config Check: ✅ Available")
                debug_info.append(f"   → Supabase URL: {'✅ Set' if config.supabase_url else '❌ Missing'}")
                debug_info.append(f"   → Supabase Key: {'✅ Set' if config.supabase_anon_key else '❌ Missing'}")
            except Exception as e:
                debug_info.append(f"3. Config Check: ❌ Failed - {e}")
            
            # Test 4: Try to create CommunityManager
            try:
                from ....community.community_manager import CommunityManager
                cm = CommunityManager()
                if cm:
                    debug_info.append("4. CommunityManager Creation: ✅ Successful")
                    
                    # Test database connection
                    try:
                        channels = cm.get_channels()
                        debug_info.append(f"5. Database Query: ✅ Successful - {len(channels)} channels")
                    except Exception as db_error:
                        debug_info.append(f"5. Database Query: ❌ Failed - {db_error}")
                else:
                    debug_info.append("4. CommunityManager Creation: ❌ Failed - returned None")
            except Exception as e:
                debug_info.append(f"4. CommunityManager Creation: ❌ Failed - {e}")
            
            # Show results
            debug_text = "\n".join(debug_info)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Supabase Connection Test", 
                                  f"Supabase Connection Test Results:\n\n{debug_text}")
            
        except Exception as e:
            logger.error(f"Error testing Supabase connection: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Test Error", f"Error running Supabase test: {str(e)}")

    def get_central_voice_manager(self):
        """Get or create the central voice manager."""
        if self._central_voice_manager is None:
            try:
                from .high_quality_voice_manager import HighQualityVoiceManager
                self._central_voice_manager = HighQualityVoiceManager()
                self._voice_managers.append(self._central_voice_manager)
                logger.info("Created central voice manager")
            except Exception as e:
                logger.warning(f"HighQualityVoiceManager not available: {e}")
                self._central_voice_manager = None
        return self._central_voice_manager

    def on_voice_settings_changed(self, settings: dict):
        """Handle voice settings changes."""
        try:
            logger.info(f"🔄 Updating voice settings for all voice managers")
            
            # Update all tracked voice managers
            for voice_manager in self._voice_managers:
                try:
                    if hasattr(voice_manager, 'update_settings'):
                        voice_manager.update_settings(settings)
                        logger.info(f"Updated voice manager settings")
                    elif hasattr(voice_manager, 'update_voice_settings'):
                        voice_manager.update_voice_settings(settings)
                        logger.info(f"Updated voice manager settings")
                except Exception as e:
                    logger.error(f"Failed to update voice manager settings: {e}")
            
            # Update voice managers in voice channels
            for channel_id, voice_widget in self.voice_channels.items():
                if hasattr(voice_widget, 'voice_manager') and voice_widget.voice_manager:
                    try:
                        if hasattr(voice_widget.voice_manager, 'update_settings'):
                            voice_widget.voice_manager.update_settings(settings)
                        elif hasattr(voice_widget.voice_manager, 'update_voice_settings'):
                            voice_widget.voice_manager.update_voice_settings(settings)
                        logger.info(f"Updated voice manager in channel {channel_id}")
                    except Exception as e:
                        logger.error(f"Failed to update voice manager in channel {channel_id}: {e}")
            
            logger.info("✅ Voice settings updated for all voice managers")
            
        except Exception as e:
            logger.error(f"Failed to update voice settings: {e}")

    def create_new_voice_manager(self):
        """Create a new voice manager and track it for settings updates."""
        try:
            from .high_quality_voice_manager import HighQualityVoiceManager
            voice_manager = HighQualityVoiceManager()
            self._voice_managers.append(voice_manager)
            logger.info("Created new voice manager and added to tracking list")
            return voice_manager
        except Exception as e:
            logger.warning(f"HighQualityVoiceManager not available: {e}")
            return None
    
    def debug_friends_loading(self):
        """Debug method to test friends loading."""
        try:
            logger.info("🔍 DEBUG: Testing friends loading...")
            
            if not self.community_manager:
                logger.error("❌ Community manager not available")
                return
            
            # Check current user ID
            current_user_id = self.community_manager.get_current_user_id()
            logger.info(f"🔍 Current user ID: {current_user_id}")
            
            if not current_user_id:
                logger.error("❌ No current user ID set")
                return
            
            # Test friends loading
            friends = self.community_manager.get_friends()
            logger.info(f"📋 DEBUG: Retrieved {len(friends)} friends")
            
            for friend in friends:
                logger.info(f"👤 DEBUG Friend: {friend}")
            
            # Refresh the UI
            self.load_friends_list()
            
        except Exception as e:
            logger.error(f"❌ Error in debug friends loading: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def add_debug_button(self):
        """Add a debug button to test friends loading."""
        try:
            debug_button = QPushButton("🔍 Debug Friends")
            debug_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 12px;
                    margin: 4px 16px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            debug_button.clicked.connect(self.debug_friends_loading)
            
            # Add to the friends section
            # Find the friends section in the scroll area
            scroll_area = self.findChild(QScrollArea)
            if scroll_area:
                scroll_widget = scroll_area.widget()
                if scroll_widget:
                    layout = scroll_widget.layout()
                    if layout:
                        # Insert after the Add Friend button
                        layout.insertWidget(layout.indexOf(self.add_friend_btn) + 1, debug_button)
                        logger.info("✅ Added debug button to friends section")
            
        except Exception as e:
            logger.error(f"❌ Error adding debug button: {e}")