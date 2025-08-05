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
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen
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
        
        # Debug logging to see the message data structure
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 ChatMessageWidget received message_data: {message_data}")
        logger.info(f"🔍 Message sender_name: {message_data.get('sender_name', 'NOT_FOUND')}")
        logger.info(f"🔍 Message user_profiles: {message_data.get('user_profiles', 'NOT_FOUND')}")
        
        self.setup_ui()
    
    def create_avatar(self):
        """Create a circular avatar with user profile picture or initials."""
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Get user data from message - check multiple sources for avatar URL
        avatar_url = None
        
        # Check user_profiles first (most common)
        user_profiles = self.message_data.get('user_profiles', {})
        if user_profiles and user_profiles.get('avatar_url'):
            avatar_url = user_profiles['avatar_url']
        
        # Check user_display_info if not found in user_profiles
        if not avatar_url:
            user_display_info = self.message_data.get('user_display_info', {})
            if user_display_info and user_display_info.get('avatar_url'):
                avatar_url = user_display_info['avatar_url']
        
        # Check direct avatar_url field
        if not avatar_url:
            avatar_url = self.message_data.get('avatar_url')
        
        # Load avatar from URL if available
        if avatar_url:
            return self.load_avatar_from_url(avatar_url, size)
        
        # Fallback to initials if no avatar URL
        # Get user name from multiple sources
        name = self.message_data.get('sender_name', 'U')
        
        # Try to get from user_profiles
        user_profiles = self.message_data.get('user_profiles', {})
        if name == 'U' and user_profiles:
            name = user_profiles.get('display_name') or user_profiles.get('username') or 'U'
        
        # Try to get from user_display_info
        if name == 'U':
            user_display_info = self.message_data.get('user_display_info', {})
            if user_display_info:
                name = user_display_info.get('display_name') or user_display_info.get('username') or 'U'
        
        # For current user, try to get from user manager
        if not name or name == 'U':
            try:
                from trackpro.auth.user_manager import get_current_user
                user = get_current_user()
                if user and user.is_authenticated:
                    # Check if this is the current user's message
                    if self.message_data.get('sender_id') == user.id:
                        name = user.name or user.email or 'You'
                    else:
                        name = 'U'
                else:
                    name = 'U'
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Could not get current user for avatar: {e}")
                name = 'U'
        
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in name.split()][:2])
        
        # Create pixmap for avatar
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        return pixmap
    
    def load_avatar_from_url(self, url: str, size: int = 32) -> QPixmap:
        """Load and display avatar from URL."""
        try:
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt6.QtCore import QUrl
            
            # Create network manager if it doesn't exist
            if not hasattr(self, 'network_manager'):
                self.network_manager = QNetworkAccessManager(self)
            
            # Download image
            request = QNetworkRequest(QUrl(url))
            reply = self.network_manager.get(request)
            
            def on_avatar_downloaded():
                try:
                    if reply.error() == reply.NetworkError.NoError:
                        image_data = reply.readAll()
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        
                        # Scale and crop to circle
                        if not pixmap.isNull():
                            # Scale to fit avatar size
                            scaled_pixmap = pixmap.scaled(
                                size, size, 
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation
                            )
                            
                            # Create circular mask
                            circular_pixmap = QPixmap(size, size)
                            circular_pixmap.fill(Qt.GlobalColor.transparent)
                            
                            try:
                                painter = QPainter(circular_pixmap)
                                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                                painter.setBrush(QBrush(scaled_pixmap))
                                painter.setPen(QPen(Qt.GlobalColor.transparent))
                                painter.drawEllipse(0, 0, size, size)
                                painter.end()
                            except RuntimeError:
                                # Painting device might be destroyed, create a simple fallback
                                circular_pixmap = self.create_fallback_avatar(size)
                            
                            # Update avatar display if this widget is still valid
                            if hasattr(self, 'avatar_label') and self.avatar_label and not self.isHidden():
                                try:
                                    self.avatar_label.setPixmap(circular_pixmap)
                                except RuntimeError:
                                    # Widget might be destroyed, ignore the error
                                    pass
                    
                    reply.deleteLater()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing downloaded avatar: {e}")
                    # Fallback to initials
                    fallback_pixmap = self.create_fallback_avatar(size)
                    if hasattr(self, 'avatar_label') and self.avatar_label and not self.isHidden():
                        try:
                            self.avatar_label.setPixmap(fallback_pixmap)
                        except RuntimeError:
                            # Widget might be destroyed, ignore the error
                            pass
            
            reply.finished.connect(on_avatar_downloaded)
            
            # Return a placeholder pixmap while loading
            placeholder = QPixmap(size, size)
            placeholder.fill(Qt.GlobalColor.transparent)
            return placeholder
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading avatar from URL: {e}")
            # Fallback to initials
            return self.create_fallback_avatar(size)
    
    def create_fallback_avatar(self, size: int = 32) -> QPixmap:
        """Create a fallback avatar with initials when image loading fails."""
        # Get user name from message data
        name = self.message_data.get('sender_name', 'U')
        
        # Try to get from user_profiles
        user_profiles = self.message_data.get('user_profiles', {})
        if name == 'U' and user_profiles:
            name = user_profiles.get('display_name') or user_profiles.get('username') or 'U'
        
        # Try to get from user_display_info
        if name == 'U':
            user_display_info = self.message_data.get('user_display_info', {})
            if user_display_info:
                name = user_display_info.get('display_name') or user_display_info.get('username') or 'U'
        
        # Generate initials from the name
        initials = ''.join([word[0].upper() for word in name.split()][:2])
        
        # Create pixmap for avatar
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        try:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw circle background using TrackPro colors
            colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
            color_index = hash(name) % len(colors)
            painter.setBrush(QBrush(QColor(colors[color_index])))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, size, size)
            
            # Draw initials
            painter.setPen(QColor('#ffffff'))
            font = painter.font()
            font.setPixelSize(size // 3)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
            
            painter.end()
        except RuntimeError:
            # If painting fails, create a simple colored square
            pixmap.fill(QColor('#3498db'))
        return pixmap
    
    def setup_ui(self):
        """Setup the message UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # User avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(32, 32)
        self.avatar_label.setPixmap(self.create_avatar())
        layout.addWidget(self.avatar_label)
        
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
        
        # If we still don't have a name, use a default
        if not sender_name:
            sender_name = 'Unknown'
            logger.info(f"🔍 Username display - using default: {sender_name}")
            
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
            
            # Check if voice components are available
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
            
            # Start voice chat with the HighQualityVoiceManager
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
    
    def clear_messages(self):
        """Clear all messages from the chat display."""
        try:
            # Clear all items from the QListWidget
            self.messages_list.clear()
            
            logger.info("✅ Cleared all messages from chat display")
            
        except Exception as e:
            logger.error(f"❌ Error clearing messages: {e}")


class CommunityPage(BasePage):
    """Community page with Discord-inspired design and voice chat."""
    
    # Class-level flags to prevent multiple initializations during startup
    _global_initialization_in_progress = False
    _instance_count = 0
    _heavy_components_initialized = False  # Add flag to prevent duplicate heavy initialization
    _channels_loaded = False  # Class-level flag to prevent duplicate channel loading
    _private_messages_loaded = False  # Class-level flag to prevent duplicate private message loading
    _initialization_lock = threading.Lock()  # Thread safety for initialization
    
    def __init__(self, global_managers=None):
        super().__init__("community", global_managers)
        
        # Initialize instance counter
        with self._initialization_lock:
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
        self.chat_history = {}  # Track chat history for each channel
        
        # Initialize state flags
        self._initialization_complete = False
        self._user_state_refreshed = False
        self._activation_complete = False
        
        # Initialize UI
        self.setup_ui()
        
        # Set up authentication state
        self.set_current_user()
        
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
        with cls._initialization_lock:
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
                background-color: #3498db;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                margin: 4px 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f5f35;
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
        requests_header = QLabel("FRIEND REQUESTS")
        requests_header.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            font-weight: bold; 
            padding: 8px 16px 4px 16px;
            background-color: #1e1e1e;
        """)
        scroll_layout.addWidget(requests_header)
        
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
                        # Scroll to bottom to show newest messages
                        chat_widget.messages_list.scrollToBottom()
                    except Exception as e:
                        logger.error(f"Error loading messages for channel {channel_id}: {e}")
                else:
                    # Fallback: load from local chat history
                    if channel_id in self.chat_history:
                        for message in self.chat_history[channel_id]:
                            chat_widget.add_message(message)
                        logger.info(f"✅ Loaded {len(self.chat_history[channel_id])} local messages for channel {channel_id}")
                        # Scroll to bottom to show newest messages
                        chat_widget.messages_list.scrollToBottom()
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
        # Reset the flag to allow updates
        self._input_field_updated = False
        
        try:
            # Check if user is authenticated
            from trackpro.auth.user_manager import get_current_user
            user = get_current_user()
            
            is_authenticated = False
            if user and user.is_authenticated:
                is_authenticated = True
                logger.info(f"✅ User authenticated via user manager: {user.email}")
            else:
                # Try to get user from Supabase session directly
                try:
                    from trackpro.database.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    if client and hasattr(client, 'auth') and client.auth.get_session():
                        session = client.auth.get_session()
                        if session and hasattr(session, 'user'):
                            is_authenticated = True
                            logger.info(f"✅ User authenticated via Supabase session: {session.user.email}")
                        else:
                            logger.warning("❌ Supabase session found but no user")
                    else:
                        logger.warning("❌ No Supabase session found")
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
                        logger.info("✅ Input field enabled for authenticated user")
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
                        logger.warning("❌ Input field disabled - user not authenticated")
            
            self._input_field_updated = True
        except Exception as e:
            logger.error(f"Error updating input field state: {e}")
            self._input_field_updated = True  # Mark as done even on error
    
    def on_page_activated(self):
        """Called when the page is activated."""
        try:
            logger.info("🚀 Community page activated")
            
            # Force authentication refresh first
            self.force_auth_refresh()
            
            # Test database connection and user authentication
            self.test_database_connection()
            
            # Set current user again to ensure it's properly set
            self.set_current_user()
            
            # Refresh user state
            self.refresh_user_state()
            
            # Load channels and messages if not already loaded
            if not hasattr(self, '_channels_loaded') or not self._channels_loaded:
                self.load_channels_from_database()
            
            if not hasattr(self, '_private_messages_loaded') or not self._private_messages_loaded:
                self.load_private_messages()
            
            # Load friends list and friend requests
            self.load_friends_list()
            self.load_friend_requests()
            
            # Start message polling when page is active
            self._start_message_polling()
            
            logger.info("✅ Community page activation complete")
            
        except Exception as e:
            logger.error(f"❌ Error during community page activation: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def force_auth_refresh(self):
        """Force refresh the authentication state."""
        try:
            logger.info("🔄 Forcing authentication refresh...")
            
            # Clear user manager cache
            import trackpro.auth.user_manager
            trackpro.auth.user_manager._current_user = None
            logger.info("✅ Cleared user manager cache")
            
            # Force Supabase client refresh
            from trackpro.database.supabase_client import get_supabase_client
            client = get_supabase_client()
            
            if client:
                try:
                    session = client.auth.get_session()
                    if session and hasattr(session, 'user'):
                        logger.info(f"✅ Fresh Supabase session: {session.user.email}")
                        
                        # Force user manager to create new user object
                        from trackpro.auth.user_manager import get_current_user
                        user = get_current_user()
                        
                        if user and user.is_authenticated:
                            logger.info(f"✅ User manager refreshed: {user.email}")
                        else:
                            logger.warning("❌ User manager still not authenticated after refresh")
                    else:
                        logger.warning("❌ No fresh Supabase session available")
                except Exception as e:
                    logger.error(f"❌ Error refreshing Supabase session: {e}")
            
            # Reset input field update flag to force refresh
            self._input_field_updated = False
            
        except Exception as e:
            logger.error(f"❌ Error forcing auth refresh: {e}")
    
    def on_page_deactivated(self):
        """Called when the page is deactivated."""
        try:
            logger.info("🛑 Community page deactivated")
            
            # Stop message polling when page is not active
            self._stop_message_polling()
            
            logger.info("✅ Community page deactivation complete")
            
        except Exception as e:
            logger.error(f"❌ Error during community page deactivation: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def _initialize_heavy_components(self):
        """Initialize heavy components that were deferred during construction."""
        # Prevent duplicate initialization
        if CommunityPage._heavy_components_initialized:
            logger.info("🔄 Heavy components already initialized, skipping")
            return
            
        try:
            logger.info("🏗️ Initializing heavy community components...")
            
            # Initialize community manager
            try:
                logger.info("🔧 Attempting to initialize CommunityManager...")
                from trackpro.community.community_manager import CommunityManager
                
                # Use singleton pattern
                self.community_manager = CommunityManager()
                logger.info("✅ CommunityManager instance created successfully")
                
            except ImportError as import_error:
                logger.error(f"❌ Failed to import CommunityManager: {import_error}")
                self.community_manager = None
            except Exception as e:
                logger.error(f"❌ Failed to initialize community manager: {e}")
                import traceback
                logger.error(f"📋 Traceback: {traceback.format_exc()}")
                self.community_manager = None
            
            # Set current user
            self.set_current_user()
            
            # START VOICE SERVER DURING PRE-LOADING FOR FASTER ACCESS
            if VOICE_COMPONENTS_AVAILABLE:
                try:
                    if not is_voice_server_running():
                        logger.info("🎤 Starting voice server during pre-loading...")
                        start_voice_server()
                        logger.info("✅ Voice server startup initiated during pre-loading")
                    else:
                        logger.info("✅ Voice server is already running")
                except Exception as e:
                    logger.error(f"❌ Failed to start voice server during pre-loading: {e}")
            
            # LOAD DATA DURING PRE-LOADING FOR FASTER ACCESS
            try:
                logger.info("📋 Loading channels and messages during pre-loading...")
                self.load_channels_from_database()
                self.load_private_messages()
                logger.info("✅ Data loading completed during pre-loading")
            except Exception as e:
                logger.error(f"❌ Failed to load data during pre-loading: {e}")
            
            self._initialization_complete = True
            CommunityPage._heavy_components_initialized = True  # Set global flag
            logger.info("✅ Heavy components initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize heavy components: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            CommunityPage._heavy_components_initialized = True  # Set flag even on error to prevent retries
    
    def refresh_user_state(self):
        """Refresh user authentication state and set current user."""
        # Prevent multiple refreshes
        if hasattr(self, '_user_state_refreshed') and self._user_state_refreshed:
            logger.info("🔄 User state already refreshed, skipping")
            return
            
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
        
        # Cleanup message polling timer
        try:
            self._stop_message_polling()
        except Exception as e:
            logger.error(f"Error cleaning up message polling: {e}")
    
    def set_current_user(self):
        """Set the current authenticated user in the community manager."""
        try:
            # During initialization, access _community_manager directly to avoid recursion
            community_manager = getattr(self, '_community_manager', None)
            if not community_manager:
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
                
                # Verify the user is properly set in the community manager
                if hasattr(community_manager, 'current_user_id') and community_manager.current_user_id:
                    logger.info(f"✅ Community manager current_user_id verified: {community_manager.current_user_id}")
                else:
                    logger.warning("⚠️ Community manager current_user_id not set properly")
            else:
                logger.warning("❌ User not authenticated")
                
        except Exception as e:
            logger.warning(f"❌ Failed to set current user: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
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
                self.refresh_private_messages()
            else:
                logger.error("Failed to send private message")
                
        except Exception as e:
            logger.error(f"Error sending private message: {e}")
    
    def on_new_private_message_clicked(self):
        """Handle new private message button click."""
        try:
            # Show an enhanced dialog to select a user to message
            from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                        QLineEdit, QPushButton, QMessageBox, QTabWidget,
                                        QListWidget, QListWidgetItem, QFrame, QSplitter)
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont, QColor
            from trackpro.social.friends_manager import FriendsManager
            from trackpro.social.user_manager import EnhancedUserManager
            
            dialog = QDialog(self)
            dialog.setWindowTitle("New Private Message")
            dialog.setFixedSize(500, 400)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                }
                QLineEdit {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border: 1px solid #3498db;
                }
                QPushButton {
                    background-color: #3498db;
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:disabled {
                    background-color: #4f545c;
                    color: #72767d;
                }
                QTabWidget::pane {
                    border: 1px solid #404040;
                    background-color: #2d2d2d;
                }
                QTabBar::tab {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    padding: 8px 16px;
                    border: 1px solid #404040;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background-color: #2d2d2d;
                }
                QListWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #404040;
                    color: #ffffff;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #404040;
                }
                QListWidget::item:selected {
                    background-color: #3498db;
                }
                QListWidget::item:hover {
                    background-color: #2980b9;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Title
            title_label = QLabel("Start a private conversation:")
            title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            layout.addWidget(title_label)
            
            # Search input
            search_layout = QHBoxLayout()
            search_label = QLabel("Search:")
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Search friends or users...")
            self.search_input.textChanged.connect(self.on_search_text_changed)
            search_layout.addWidget(search_label)
            search_layout.addWidget(self.search_input)
            layout.addLayout(search_layout)
            
            # Tab widget for friends and search results
            self.tab_widget = QTabWidget()
            
            # Friends tab
            self.friends_tab = QWidget()
            friends_layout = QVBoxLayout(self.friends_tab)
            friends_label = QLabel("Your Friends:")
            self.friends_list = QListWidget()
            self.friends_list.itemClicked.connect(self.on_user_selected)
            friends_layout.addWidget(friends_label)
            friends_layout.addWidget(self.friends_list)
            self.tab_widget.addTab(self.friends_tab, "Friends")
            
            # Search results tab
            self.search_tab = QWidget()
            search_results_layout = QVBoxLayout(self.search_tab)
            search_results_label = QLabel("Search Results:")
            self.search_results_list = QListWidget()
            self.search_results_list.itemClicked.connect(self.on_user_selected)
            search_results_layout.addWidget(search_results_label)
            search_results_layout.addWidget(self.search_results_list)
            self.tab_widget.addTab(self.search_tab, "Search Results")
            
            layout.addWidget(self.tab_widget)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            start_btn = QPushButton("Start Conversation")
            start_btn.clicked.connect(lambda: self.start_private_conversation_from_dialog(dialog))
            button_layout.addWidget(start_btn)
            
            layout.addLayout(button_layout)
            
            # Initialize data
            self.selected_user = None
            self.load_friends_list()
            
            # Show dialog
            result = dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing new private message dialog: {e}")
    
    def load_friends_list(self):
        """Load the current user's friends list."""
        try:
            from trackpro.social.friends_manager import FriendsManager
            
            friends_manager = FriendsManager()
            current_user_id = self.get_current_user_id()
            
            if not current_user_id:
                logger.error("No authenticated user found")
                return
            
            friends = friends_manager.get_friends_list(current_user_id, include_online_status=True)
            self.friends_list.clear()
            
            for friend in friends:
                item = QListWidgetItem()
                widget = self.create_user_list_item(friend)
                item.setSizeHint(widget.sizeHint())
                self.friends_list.addItem(item)
                self.friends_list.setItemWidget(item, widget)
                
        except Exception as e:
            logger.error(f"Error loading friends list: {e}")
    
    def on_add_friend_clicked(self):
        """Handle add friend button click."""
        try:
            logger.info("🔄 Add friend button clicked")
            
            # Create a dialog for adding friends
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Friend")
            dialog.setFixedSize(400, 500)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                }
                QLineEdit {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 1px solid #3498db;
                }
                QPushButton {
                    background-color: #3498db;
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #1f5f35;
                }
                QListWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    color: #ffffff;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #3d3d3d;
                }
                QListWidget::item:selected {
                    background-color: #3498db;
                }
                QListWidget::item:hover {
                    background-color: #3d3d3d;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Title
            title_label = QLabel("Add Friend")
            title_label.setStyleSheet("font-size: 16px; margin-bottom: 16px;")
            layout.addWidget(title_label)
            
            # Search input
            search_label = QLabel("Search users:")
            layout.addWidget(search_label)
            
            search_input = QLineEdit()
            search_input.setPlaceholderText("Enter username or email...")
            search_input.textChanged.connect(lambda text: self.on_add_friend_search_changed(text, users_list))
            layout.addWidget(search_input)
            
            # Users list
            users_label = QLabel("Available users:")
            layout.addWidget(users_label)
            
            users_list = QListWidget()
            users_list.itemClicked.connect(lambda item: self.on_add_friend_user_selected(item, dialog))
            layout.addWidget(users_list)
            
            # Load users into the list
            self.load_users_for_add_friend(users_list)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            add_friend_btn = QPushButton("Add Friend")
            add_friend_btn.clicked.connect(lambda: self.on_add_friend_button_clicked(users_list, dialog))
            button_layout.addWidget(add_friend_btn)
            
            layout.addLayout(button_layout)
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                logger.info("✅ Add friend dialog accepted")
            else:
                logger.info("❌ Add friend dialog cancelled")
                
        except Exception as e:
            logger.error(f"❌ Error showing add friend dialog: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def on_friend_selected(self, item):
        """Handle friend selection."""
        try:
            logger.info(f"🔄 Friend selected: {item.text()}")
            
            # Get friend data from item
            friend_data = item.data(Qt.ItemDataRole.UserRole)
            if friend_data:
                # Show friend profile or start conversation
                self.show_friend_profile(friend_data)
            else:
                logger.warning("⚠️ No friend data found in selected item")
                
        except Exception as e:
            logger.error(f"❌ Error handling friend selection: {e}")
    
    def on_friend_request_selected(self, item):
        """Handle friend request selection."""
        try:
            logger.info(f"🔄 Friend request selected: {item.text()}")
            
            # Get request data from item
            request_data = item.data(Qt.ItemDataRole.UserRole)
            if request_data:
                # Show accept/decline options
                self.show_friend_request_actions(request_data)
            else:
                logger.warning("⚠️ No request data found in selected item")
                
        except Exception as e:
            logger.error(f"❌ Error handling friend request selection: {e}")
    
    def show_friend_profile(self, friend_data):
        """Show friend profile dialog."""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Friend Profile")
            dialog.setFixedSize(300, 200)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #3498db;
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Friend info
            name_label = QLabel(f"Name: {friend_data.get('friend_username', 'Unknown')}")
            status_label = QLabel(f"Status: {'🟢 Online' if friend_data.get('is_online', False) else '⚫ Offline'}")
            
            layout.addWidget(name_label)
            layout.addWidget(status_label)
            
            # Action buttons
            button_layout = QHBoxLayout()
            
            message_btn = QPushButton("Send Message")
            message_btn.clicked.connect(lambda: self.start_conversation_with_friend(friend_data))
            button_layout.addWidget(message_btn)
            
            remove_btn = QPushButton("Remove Friend")
            remove_btn.setStyleSheet("background-color: #e74c3c;")
            remove_btn.clicked.connect(lambda: self.remove_friend(friend_data))
            button_layout.addWidget(remove_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"❌ Error showing friend profile: {e}")
    
    def show_friend_request_actions(self, request_data):
        """Show friend request action dialog."""
        try:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Friend Request")
            dialog.setFixedSize(300, 150)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                }
                QPushButton {
                    border: none;
                    border-radius: 4px;
                    color: #ffffff;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Request info
            requester_name = request_data.get('user_profiles', {}).get('username', 'Unknown')
            info_label = QLabel(f"{requester_name} wants to be your friend")
            layout.addWidget(info_label)
            
            # Action buttons
            button_layout = QHBoxLayout()
            
            accept_btn = QPushButton("Accept")
            accept_btn.setStyleSheet("background-color: #27ae60;")
            accept_btn.clicked.connect(lambda: self.accept_friend_request(request_data))
            button_layout.addWidget(accept_btn)
            
            decline_btn = QPushButton("Decline")
            decline_btn.setStyleSheet("background-color: #e74c3c;")
            decline_btn.clicked.connect(lambda: self.decline_friend_request(request_data))
            button_layout.addWidget(decline_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"❌ Error showing friend request actions: {e}")
    
    def load_users_for_add_friend(self, users_list):
        """Load users for add friend dialog."""
        try:
            # Import friends manager and user manager
            from trackpro.social.friends_manager import FriendsManager
            from trackpro.social.user_manager import EnhancedUserManager
            
            friends_manager = FriendsManager()
            user_manager = EnhancedUserManager()
            
            # Get current user ID
            current_user_id = self.get_current_user_id()
            if not current_user_id:
                logger.warning("⚠️ No current user ID available")
                return
            
            # Get all users from database
            all_users = user_manager.get_all_users()
            
            # Get existing friends to filter out
            friends = friends_manager.get_friends_list(current_user_id, include_online_status=False)
            friend_ids = {friend['friend_id'] for friend in friends}
            
            # Filter out current user and existing friends
            available_users = []
            for user in all_users:
                user_id = user.get('user_id')
                if user_id and user_id != current_user_id and user_id not in friend_ids:
                    available_users.append(user)
            
            # Add users to list
            for user in available_users:
                display_name = user.get('display_name', user.get('username', 'Unknown'))
                username = user.get('username', 'unknown')
                item = QListWidgetItem(f"{display_name} (@{username})")
                item.setData(Qt.ItemDataRole.UserRole, user)
                users_list.addItem(item)
                
            logger.info(f"✅ Loaded {len(available_users)} available users for friend requests")
                
        except Exception as e:
            logger.error(f"❌ Error loading users for add friend: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def start_conversation_with_friend(self, friend_data):
        """Start a conversation with a friend."""
        try:
            logger.info(f"🔄 Starting conversation with friend: {friend_data.get('friend_username', 'Unknown')}")
            # This would open the messaging interface with the friend
            # Implementation would depend on the messaging system
            
        except Exception as e:
            logger.error(f"❌ Error starting conversation with friend: {e}")
    
    def remove_friend(self, friend_data):
        """Remove a friend."""
        try:
            from trackpro.social.friends_manager import FriendsManager
            friends_manager = FriendsManager()
            
            current_user_id = self.get_current_user_id()
            friend_id = friend_data.get('friend_id')
            
            if current_user_id and friend_id:
                result = friends_manager.remove_friend(current_user_id, friend_id)
                if result['success']:
                    logger.info("✅ Friend removed successfully")
                    self.load_friends_list()  # Refresh friends list
                else:
                    logger.error(f"❌ Failed to remove friend: {result['message']}")
            else:
                logger.warning("⚠️ Missing user ID or friend ID")
                
        except Exception as e:
            logger.error(f"❌ Error removing friend: {e}")
    
    def accept_friend_request(self, request_data):
        """Accept a friend request."""
        try:
            from trackpro.social.friends_manager import FriendsManager
            friends_manager = FriendsManager()
            
            current_user_id = self.get_current_user_id()
            request_id = request_data.get('id')
            
            if current_user_id and request_id:
                result = friends_manager.respond_to_friend_request(request_id, current_user_id, True)
                if result['success']:
                    logger.info("✅ Friend request accepted")
                    self.load_friends_list()  # Refresh friends list
                    self.load_friend_requests()  # Refresh requests list
                else:
                    logger.error(f"❌ Failed to accept friend request: {result['message']}")
            else:
                logger.warning("⚠️ Missing user ID or request ID")
                
        except Exception as e:
            logger.error(f"❌ Error accepting friend request: {e}")
    
    def decline_friend_request(self, request_data):
        """Decline a friend request."""
        try:
            from trackpro.social.friends_manager import FriendsManager
            friends_manager = FriendsManager()
            
            current_user_id = self.get_current_user_id()
            request_id = request_data.get('id')
            
            if current_user_id and request_id:
                result = friends_manager.respond_to_friend_request(request_id, current_user_id, False)
                if result['success']:
                    logger.info("✅ Friend request declined")
                    self.load_friend_requests()  # Refresh requests list
                else:
                    logger.error(f"❌ Failed to decline friend request: {result['message']}")
            else:
                logger.warning("⚠️ Missing user ID or request ID")
                
        except Exception as e:
            logger.error(f"❌ Error declining friend request: {e}")
    
    def load_friend_requests(self):
        """Load friend requests into the UI."""
        try:
            from trackpro.social.friends_manager import FriendsManager
            friends_manager = FriendsManager()
            
            current_user_id = self.get_current_user_id()
            if not current_user_id:
                logger.warning("⚠️ No current user ID available")
                return
            
            # Get pending friend requests
            requests = friends_manager.get_pending_friend_requests(current_user_id, sent=False)
            
            # Clear existing items
            self.friend_requests_list.clear()
            
            # Add requests to list
            for request in requests:
                requester_name = request.get('user_profiles', {}).get('username', 'Unknown')
                item = QListWidgetItem(f"Friend request from {requester_name}")
                item.setData(Qt.ItemDataRole.UserRole, request)
                self.friend_requests_list.addItem(item)
                
        except Exception as e:
            logger.error(f"❌ Error loading friend requests: {e}")
    
    def create_user_list_item(self, user_data: dict) -> QWidget:
        """Create a user list item widget."""
        widget = QFrame()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Store user data in the widget
        widget.user_data = user_data
        
        # Avatar placeholder
        avatar = QLabel("👤")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                border: 2px solid #5865f2;
                border-radius: 16px;
                background-color: #40444b;
            }
        """)
        
        # User info
        info_layout = QVBoxLayout()
        username = user_data.get('friend_username', user_data.get('username', 'Unknown'))
        username_label = QLabel(username)
        username_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        status_text = "🟢 Online" if user_data.get('is_online', False) else "⚫ Offline"
        status_label = QLabel(status_text)
        status_label.setStyleSheet("color: #72767d; font-size: 11px;")
        
        info_layout.addWidget(username_label)
        info_layout.addWidget(status_label)
        
        layout.addWidget(avatar)
        layout.addLayout(info_layout)
        layout.addStretch()
        
        return widget
    
    def on_search_text_changed(self, text: str):
        """Handle search text changes."""
        if len(text) < 2:
            self.search_results_list.clear()
            self.tab_widget.setCurrentIndex(0)  # Switch to friends tab
            return
        
        try:
            from trackpro.social.user_manager import EnhancedUserManager
            
            user_manager = EnhancedUserManager()
            users = user_manager.search_users(text, limit=20)
            
            self.search_results_list.clear()
            
            for user in users:
                if user.get('user_id') != self.get_current_user_id():
                    item = QListWidgetItem()
                    widget = self.create_user_list_item(user)
                    item.setSizeHint(widget.sizeHint())
                    self.search_results_list.addItem(item)
                    self.search_results_list.setItemWidget(item, widget)
            
            # Switch to search results tab if we have results
            if users:
                self.tab_widget.setCurrentIndex(1)
                
        except Exception as e:
            logger.error(f"Error searching users: {e}")
    
    def on_add_friend_search_changed(self, text: str, users_list):
        """Handle search text changes in add friend dialog."""
        try:
            if len(text) < 2:
                # Reload all users when search is cleared
                users_list.clear()
                self.load_users_for_add_friend(users_list)
                return
            
            from trackpro.social.user_manager import EnhancedUserManager
            from trackpro.social.friends_manager import FriendsManager
            
            user_manager = EnhancedUserManager()
            friends_manager = FriendsManager()
            
            current_user_id = self.get_current_user_id()
            if not current_user_id:
                return
            
            # Search for users
            search_results = user_manager.search_users(text, limit=20)
            
            # Get existing friends to filter out
            friends = friends_manager.get_friends_list(current_user_id, include_online_status=False)
            friend_ids = {friend['friend_id'] for friend in friends}
            
            # Filter results
            available_users = []
            for user in search_results:
                user_id = user.get('user_id')
                if user_id and user_id != current_user_id and user_id not in friend_ids:
                    available_users.append(user)
            
            # Update the list
            users_list.clear()
            for user in available_users:
                display_name = user.get('display_name', user.get('username', 'Unknown'))
                username = user.get('username', 'unknown')
                item = QListWidgetItem(f"{display_name} (@{username})")
                item.setData(Qt.ItemDataRole.UserRole, user)
                users_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error searching users in add friend dialog: {e}")
    
    def on_add_friend_user_selected(self, item, dialog):
        """Handle user selection in add friend dialog."""
        try:
            user_data = item.data(Qt.ItemDataRole.UserRole)
            if user_data:
                # Store selected user for the add friend button
                dialog.selected_user = user_data
                logger.info(f"Selected user for friend request: {user_data.get('username', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error selecting user in add friend dialog: {e}")
    
    def on_add_friend_button_clicked(self, users_list, dialog):
        """Handle add friend button click in dialog."""
        try:
            selected_user = getattr(dialog, 'selected_user', None)
            if not selected_user:
                # Try to get the first selected item
                current_item = users_list.currentItem()
                if current_item:
                    selected_user = current_item.data(Qt.ItemDataRole.UserRole)
            
            if selected_user:
                user_id = selected_user.get('user_id')
                username = selected_user.get('username', 'Unknown')
                
                if user_id:
                    from trackpro.social.friends_manager import FriendsManager
                    friends_manager = FriendsManager()
                    
                    current_user_id = self.get_current_user_id()
                    if current_user_id:
                        result = friends_manager.send_friend_request(current_user_id, user_id)
                        if result['success']:
                            logger.info(f"✅ Friend request sent to {username}")
                            dialog.accept()
                        else:
                            logger.error(f"❌ Failed to send friend request: {result['message']}")
                            
                            # Show specific popup for already sent friend request
                            if result['message'] == "Friend request already sent":
                                from PyQt6.QtWidgets import QMessageBox
                                QMessageBox.information(
                                    dialog, 
                                    "Friend Request", 
                                    "You've already sent this user a request!"
                                )
                            else:
                                # Show generic error for other cases
                                from PyQt6.QtWidgets import QMessageBox
                                QMessageBox.warning(
                                    dialog, 
                                    "Friend Request Error", 
                                    result['message']
                                )
                    else:
                        logger.warning("⚠️ No current user ID available")
                else:
                    logger.warning("⚠️ No user ID found in selected user data")
            else:
                logger.warning("⚠️ No user selected for friend request")
                
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    def on_user_selected(self, item):
        """Handle user selection from either friends or search results."""
        try:
            # Get the widget associated with the selected item
            widget = self.tab_widget.currentWidget()
            list_widget = widget.findChild(QListWidget)
            
            # Clear previous selection visual indicators
            self.clear_selection_indicators()
            
            if list_widget == self.friends_list:
                # Get friend data from friends list
                item_widget = self.friends_list.itemWidget(item)
                if item_widget and hasattr(item_widget, 'user_data'):
                    self.selected_user = item_widget.user_data
                    # Update search input with selected username
                    username = item_widget.user_data.get('friend_username', item_widget.user_data.get('username', ''))
                    self.search_input.setText(username)
                    # Highlight the selected item
                    item.setBackground(QColor('#5865f2'))
            elif list_widget == self.search_results_list:
                # Get user data from search results
                item_widget = self.search_results_list.itemWidget(item)
                if item_widget and hasattr(item_widget, 'user_data'):
                    self.selected_user = item_widget.user_data
                    # Update search input with selected username
                    username = item_widget.user_data.get('username', '')
                    self.search_input.setText(username)
                    # Highlight the selected item
                    item.setBackground(QColor('#5865f2'))
                
        except Exception as e:
            logger.error(f"Error selecting user: {e}")
    
    def clear_selection_indicators(self):
        """Clear visual selection indicators from all lists."""
        try:
            # Clear friends list selection indicators
            for i in range(self.friends_list.count()):
                item = self.friends_list.item(i)
                item.setBackground(QColor('transparent'))
            
            # Clear search results list selection indicators
            for i in range(self.search_results_list.count()):
                item = self.search_results_list.item(i)
                item.setBackground(QColor('transparent'))
        except Exception as e:
            logger.error(f"Error clearing selection indicators: {e}")
    
    def start_private_conversation_from_dialog(self, dialog):
        """Start a new private conversation from the enhanced dialog."""
        try:
            # Try to get selected user first
            if self.selected_user:
                # Use user_id if available, otherwise fall back to username
                user_id = self.selected_user.get('user_id') or self.selected_user.get('friend_id')
                username = self.selected_user.get('username') or self.selected_user.get('friend_username')
                
                if user_id:
                    # Use user ID for conversation creation
                    conversation_id = self.community_manager.get_or_create_conversation(user_id)
                elif username:
                    # Use username for conversation creation
                    conversation_id = self.community_manager.get_or_create_conversation(username)
                else:
                    QMessageBox.warning(dialog, "Error", "Invalid user data selected.")
                    return
            else:
                # Fall back to search input
                username = self.search_input.text().strip()
                if not username:
                    QMessageBox.warning(dialog, "Error", "Please select a user or enter a username.")
                    return
                
                conversation_id = self.community_manager.get_or_create_conversation(username)
            
            if conversation_id:
                dialog.accept()
                # Load and show the conversation
                self.on_private_conversation_selected(conversation_id)
            else:
                QMessageBox.warning(dialog, "Error", f"Could not find user or create conversation.")
                
        except Exception as e:
            logger.error(f"Error starting private conversation: {e}")
            QMessageBox.critical(dialog, "Error", f"An error occurred: {str(e)}")
    
    def get_current_user_id(self):
        """Get the current user ID."""
        try:
            if hasattr(self, 'community_manager') and self.community_manager:
                return self.community_manager.get_current_user_id()
            return None
        except Exception as e:
            logger.error(f"Error getting current user ID: {e}")
            return None
    
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
        """Show private conversation in the main content area."""
        # Clear current content
        for i in reversed(range(self.content_stack.count())):
            self.content_stack.removeWidget(self.content_stack.widget(i))
        
        # Add conversation widget
        self.content_stack.addWidget(conversation_widget)
        conversation_widget.show()
    
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
        # Return the manager (may be None if initialization failed)
        return self._community_manager
    
    @community_manager.setter
    def community_manager(self, value):
        """Set the community manager."""
        self._community_manager = value
        
        # Connect signals when community manager is set
        if value:
            try:
                # Check if signals are already connected to prevent duplicates
                if not hasattr(self, '_signals_connected'):
                    # Connect message received signal
                    value.message_received.connect(self.on_message_received)
                    value.user_joined_channel.connect(self.on_user_joined_channel)
                    value.user_left_channel.connect(self.on_user_left_channel)
                    value.user_status_changed.connect(self.on_user_status_changed)
                    self._signals_connected = True
                    logger.info("✅ Connected community manager signals")
                else:
                    logger.info("🔄 Signals already connected, skipping")
                
                # Message polling will be started when page is activated
                
            except Exception as e:
                logger.error(f"❌ Error connecting community manager signals: {e}")
    
    def _start_message_polling(self):
        """Start polling for new messages since real-time subscriptions are disabled."""
        try:
            if not hasattr(self, '_message_polling_timer'):
                from PyQt6.QtCore import QTimer
                self._message_polling_timer = QTimer()
                self._message_polling_timer.timeout.connect(self._poll_for_new_messages)
                self._message_polling_timer.start(5000)  # Poll every 5 seconds
                logger.info("✅ Started message polling timer (5 second interval)")
            elif not self._message_polling_timer.isActive():
                # Timer exists but is not active, restart it
                self._message_polling_timer.start(5000)
                logger.info("✅ Restarted message polling timer (5 second interval)")
            else:
                logger.info("🔄 Message polling timer already running")
        except Exception as e:
            logger.error(f"❌ Error starting message polling: {e}")
    
    def _poll_for_new_messages(self):
        """Poll for new messages in the current channel."""
        try:
            if not self.community_manager or not self.current_channel:
                logger.debug("🔄 Skipping message poll - no community manager or current channel")
                return
            
            # Get the latest message ID for this channel to avoid duplicates
            latest_message_id = None
            if hasattr(self, 'chat_history') and self.current_channel in self.chat_history:
                if self.chat_history[self.current_channel]:
                    latest_message = self.chat_history[self.current_channel][-1]
                    latest_message_id = latest_message.get('message_id')
            
            # Fetch only recent messages from database (last 5 to reduce load)
            messages = self.community_manager.get_messages(self.current_channel, limit=5)
            
            # Find truly new messages by comparing message IDs
            new_messages = []
            seen_message_ids = set()
            
            # Build set of existing message IDs to avoid duplicates
            if hasattr(self, 'chat_history') and self.current_channel in self.chat_history:
                seen_message_ids = {msg.get('message_id') for msg in self.chat_history[self.current_channel]}
            
            for message in messages:
                message_id = message.get('message_id')
                if message_id and message_id not in seen_message_ids:
                    new_messages.append(message)
            
            # Only add new messages to UI if we found any
            if new_messages:
                logger.info(f"📨 Found {len(new_messages)} new messages in channel {self.current_channel}")
                for message in new_messages:
                    if self.current_channel == message.get('channel_id'):
                        self.on_message_received(message)
            else:
                logger.debug(f"📭 No new messages found in channel {self.current_channel}")
                    
        except Exception as e:
            logger.error(f"❌ Error polling for new messages: {e}")
    
    def _stop_message_polling(self):
        """Stop the message polling timer."""
        try:
            if hasattr(self, '_message_polling_timer'):
                self._message_polling_timer.stop()
                logger.info("✅ Stopped message polling timer")
        except Exception as e:
            logger.error(f"❌ Error stopping message polling: {e}")
    
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
    
    def test_database_connection(self):
        """Test the database connection and user authentication."""
        try:
            logger.info("🔍 Testing database connection and user authentication...")
            
            # Test Supabase client
            from trackpro.database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if client:
                logger.info("✅ Supabase client available")
                
                # Test session
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    user_data = session.user
                    logger.info(f"✅ User session found: {user_data.email} (ID: {user_data.id})")
                    
                    # Test user_profiles table
                    response = client.table("user_profiles").select("user_id, email, display_name").eq("user_id", user_data.id).execute()
                    if response.data:
                        user_profile = response.data[0]
                        logger.info(f"✅ User profile found: {user_profile}")
                    else:
                        logger.warning("❌ No user profile found in database")
                else:
                    logger.warning("❌ No user session found")
            else:
                logger.error("❌ Supabase client not available")
            
            # Test community manager
            community_manager = getattr(self, '_community_manager', None)
            if community_manager:
                logger.info(f"✅ Community manager available")
                if hasattr(community_manager, 'current_user_id') and community_manager.current_user_id:
                    logger.info(f"✅ Community manager current_user_id: {community_manager.current_user_id}")
                else:
                    logger.warning("❌ Community manager current_user_id not set")
                
                if hasattr(community_manager, 'client') and community_manager.client:
                    logger.info("✅ Community manager has Supabase client")
                else:
                    logger.warning("❌ Community manager has no Supabase client")
            else:
                logger.error("❌ Community manager not available")
                
        except Exception as e:
            logger.error(f"❌ Error testing database connection: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    def set_current_user(self):
        """Set the current authenticated user in the community manager."""
        try:
            # During initialization, access _community_manager directly to avoid recursion
            community_manager = getattr(self, '_community_manager', None)
            if not community_manager:
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
                
                # Verify the user is properly set in the community manager
                if hasattr(community_manager, 'current_user_id') and community_manager.current_user_id:
                    logger.info(f"✅ Community manager current_user_id verified: {community_manager.current_user_id}")
                else:
                    logger.warning("⚠️ Community manager current_user_id not set properly")
            else:
                logger.warning("❌ User not authenticated")
                
        except Exception as e:
            logger.warning(f"❌ Failed to set current user: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    

    

    

    

    

    
    def force_refresh_messages(self):
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
                self.refresh_private_messages()
            else:
                logger.error("Failed to send private message")
                
        except Exception as e:
            logger.error(f"Error sending private message: {e}")
    
    def on_new_private_message_clicked(self):
        """Handle new private message button click."""
        try:
            # Show an enhanced dialog to select a user to message
            from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                        QLineEdit, QPushButton, QMessageBox, QTabWidget,
                                        QListWidget, QListWidgetItem, QFrame, QSplitter)
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont
            from trackpro.social.friends_manager import FriendsManager
            from trackpro.social.user_manager import EnhancedUserManager
            
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
                    background-color: #40444b;
                }
                QTabBar::tab {
                    background-color: #2f3136;
                    color: #dcddde;
                    padding: 8px 16px;
                    border: 1px solid #202225;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background-color: #40444b;
                }
                QListWidget {
                    background-color: #40444b;
                    border: 1px solid #202225;
                    color: #dcddde;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #202225;
                }
                QListWidget::item:selected {
                    background-color: #5865f2;
                }
                QListWidget::item:hover {
                    background-color: #4752c4;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # Title
            title_label = QLabel("Start a private conversation:")
            title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            layout.addWidget(title_label)
            
            # Search input
            search_layout = QHBoxLayout()
            search_label = QLabel("Search:")
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Search friends or users...")
            self.search_input.textChanged.connect(self.on_search_text_changed)
            search_layout.addWidget(search_label)
            search_layout.addWidget(self.search_input)
            layout.addLayout(search_layout)
            
            # Tab widget for friends and search results
            self.tab_widget = QTabWidget()
            
            # Friends tab
            self.friends_tab = QWidget()
            friends_layout = QVBoxLayout(self.friends_tab)
            friends_label = QLabel("Your Friends:")
            self.friends_list = QListWidget()
            self.friends_list.itemClicked.connect(self.on_user_selected)
            friends_layout.addWidget(friends_label)
            friends_layout.addWidget(self.friends_list)
            self.tab_widget.addTab(self.friends_tab, "Friends")
            
            # Search results tab
            self.search_tab = QWidget()
            search_results_layout = QVBoxLayout(self.search_tab)
            search_results_label = QLabel("Search Results:")
            self.search_results_list = QListWidget()
            self.search_results_list.itemClicked.connect(self.on_user_selected)
            search_results_layout.addWidget(search_results_label)
            search_results_layout.addWidget(self.search_results_list)
            self.tab_widget.addTab(self.search_tab, "Search Results")
            
            layout.addWidget(self.tab_widget)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            start_btn = QPushButton("Start Conversation")
            start_btn.clicked.connect(lambda: self.start_private_conversation_from_dialog(dialog))
            button_layout.addWidget(start_btn)
            
            layout.addLayout(button_layout)
            
            # Initialize data
            self.selected_user = None
            self.load_friends_list()
            
            # Show dialog
            result = dialog.exec()
            
        except Exception as e:
            logger.error(f"Error showing new private message dialog: {e}")
    
    def load_friends_list(self):
        """Load the current user's friends list."""
        try:
            from trackpro.social.friends_manager import FriendsManager
            
            friends_manager = FriendsManager()
            current_user_id = self.get_current_user_id()
            
            if not current_user_id:
                logger.error("No authenticated user found")
                return
            
            friends = friends_manager.get_friends_list(current_user_id, include_online_status=True)
            self.friends_list.clear()
            
            for friend in friends:
                item = QListWidgetItem()
                widget = self.create_user_list_item(friend)
                item.setSizeHint(widget.sizeHint())
                self.friends_list.addItem(item)
                self.friends_list.setItemWidget(item, widget)
                
        except Exception as e:
            logger.error(f"Error loading friends list: {e}")
    
    def create_user_list_item(self, user_data: dict) -> QWidget:
        """Create a user list item widget."""
        widget = QFrame()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Store user data in the widget
        widget.user_data = user_data
        
        # Avatar placeholder
        avatar = QLabel("👤")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                border: 2px solid #5865f2;
                border-radius: 16px;
                background-color: #40444b;
            }
        """)
        
        # User info
        info_layout = QVBoxLayout()
        username = user_data.get('friend_username', user_data.get('username', 'Unknown'))
        username_label = QLabel(username)
        username_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        status_text = "🟢 Online" if user_data.get('is_online', False) else "⚫ Offline"
        status_label = QLabel(status_text)
        status_label.setStyleSheet("color: #72767d; font-size: 11px;")
        
        info_layout.addWidget(username_label)
        info_layout.addWidget(status_label)
        
        layout.addWidget(avatar)
        layout.addLayout(info_layout)
        layout.addStretch()
        
        return widget
    
    def on_search_text_changed(self, text: str):
        """Handle search text changes."""
        if len(text) < 2:
            self.search_results_list.clear()
            self.tab_widget.setCurrentIndex(0)  # Switch to friends tab
            return
        
        try:
            from trackpro.social.user_manager import EnhancedUserManager
            
            user_manager = EnhancedUserManager()
            users = user_manager.search_users(text, limit=20)
            
            self.search_results_list.clear()
            
            for user in users:
                if user.get('user_id') != self.get_current_user_id():
                    item = QListWidgetItem()
                    widget = self.create_user_list_item(user)
                    item.setSizeHint(widget.sizeHint())
                    self.search_results_list.addItem(item)
                    self.search_results_list.setItemWidget(item, widget)
            
            # Switch to search results tab if we have results
            if users:
                self.tab_widget.setCurrentIndex(1)
                
        except Exception as e:
            logger.error(f"Error searching users: {e}")
    
    def on_user_selected(self, item):
        """Handle user selection from either friends or search results."""
        try:
            # Get the widget associated with the selected item
            widget = self.tab_widget.currentWidget()
            list_widget = widget.findChild(QListWidget)
            
            if list_widget == self.friends_list:
                # Get friend data from friends list
                item_widget = self.friends_list.itemWidget(item)
                if item_widget and hasattr(item_widget, 'user_data'):
                    self.selected_user = item_widget.user_data
                    # Update search input with selected username
                    username = item_widget.user_data.get('friend_username', item_widget.user_data.get('username', ''))
                    self.search_input.setText(username)
            elif list_widget == self.search_results_list:
                # Get user data from search results
                item_widget = self.search_results_list.itemWidget(item)
                if item_widget and hasattr(item_widget, 'user_data'):
                    self.selected_user = item_widget.user_data
                    # Update search input with selected username
                    username = item_widget.user_data.get('username', '')
                    self.search_input.setText(username)
                
        except Exception as e:
            logger.error(f"Error selecting user: {e}")
    
    def start_private_conversation_from_dialog(self, dialog):
        """Start a new private conversation from the enhanced dialog."""
        try:
            # Try to get selected user first
            if self.selected_user:
                username = self.selected_user.get('username')
            else:
                # Fall back to search input
                username = self.search_input.text().strip()
            
            if not username:
                QMessageBox.warning(dialog, "Error", "Please select a user or enter a username.")
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
    
    def get_current_user_id(self):
        """Get the current user ID."""
        try:
            if hasattr(self, 'community_manager') and self.community_manager:
                return self.community_manager.get_current_user_id()
            return None
        except Exception as e:
            logger.error(f"Error getting current user ID: {e}")
            return None
    
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
        """Show private conversation in the main content area."""
        # Clear current content
        for i in reversed(range(self.content_stack.count())):
            self.content_stack.removeWidget(self.content_stack.widget(i))
        
        # Add conversation widget
        self.content_stack.addWidget(conversation_widget)
        conversation_widget.show()
    
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
    

    
