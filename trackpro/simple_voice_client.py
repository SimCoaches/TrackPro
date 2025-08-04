"""
Simple Voice Chat Client

A reliable, simplified voice chat client that actually works.
"""

import asyncio
import websockets
import json
import logging
import threading
import time
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class SimpleVoiceClient(QObject):
    """Simple and reliable voice chat client."""
    
    voice_data_received = pyqtSignal(bytes)
    user_joined_voice = pyqtSignal(str)
    user_left_voice = pyqtSignal(str)
    voice_error = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.websocket = None
        self.voice_thread = None
        self.is_connected = False
        self.server_url = ""
        self.channel_id = ""
        self.user_name = "User"
        
    def start_voice_chat(self, server_url: str, channel_id: str, user_name: str = "User"):
        """Start voice chat connection."""
        self.server_url = server_url
        self.channel_id = channel_id
        self.user_name = user_name
        
        # Start voice client in separate thread
        self.voice_thread = threading.Thread(target=self._run_voice_client, daemon=True)
        self.voice_thread.start()
        
        logger.info(f"Starting voice chat: {server_url}/voice/{channel_id}")
    
    def _run_voice_client(self, server_url: str = None, channel_id: str = None):
        """Run voice client in separate thread."""
        if server_url is None:
            server_url = self.server_url
        if channel_id is None:
            channel_id = self.channel_id
            
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
        """Voice client WebSocket loop."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Connect to the correct URL format
                websocket_url = f"{server_url}/voice/{channel_id}"
                logger.info(f"Connecting to: {websocket_url}")
                
                async with websockets.connect(
                    websocket_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                ) as websocket:
                    self.websocket = websocket
                    self.is_connected = True
                    self.connected.emit()
                    
                    logger.info(f"Successfully connected to voice channel: {channel_id}")
                    
                    # Send user info
                    await websocket.send(json.dumps({
                        'type': 'user_info',
                        'user_name': self.user_name
                    }))
                    
                    # Handle incoming messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self.handle_message(data)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON received: {message}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"WebSocket connection closed: {e}")
                self.is_connected = False
                self.disconnected.emit()
                break
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"WebSocket connection error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)
                    continue
                else:
                    self.voice_error.emit(f"Voice chat connection error after {max_retries} retries: {str(e)}")
                    break
            except websockets.exceptions.InvalidURI:
                self.voice_error.emit("WebSocket error: Invalid server URL. Please check the voice server configuration.")
                break
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)
                    continue
                else:
                    self.voice_error.emit(f"Voice chat connection error after {max_retries} retries: {str(e)}")
                    break
            except Exception as e:
                logger.error(f"Unexpected voice chat error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying voice connection ({retry_count}/{max_retries})...")
                    await asyncio.sleep(2)
                    continue
                else:
                    self.voice_error.emit(f"Voice chat error after {max_retries} retries: {str(e)}")
                    break
    
    async def handle_message(self, data: dict):
        """Handle incoming messages from server."""
        message_type = data.get('type')
        
        if message_type == 'welcome':
            logger.info(f"Welcome message received: {data}")
            
        elif message_type == 'voice_data':
            # Handle incoming voice data
            audio_data = data.get('audio', [])
            if audio_data:
                # Convert to bytes for processing
                audio_bytes = bytes(audio_data)
                self.voice_data_received.emit(audio_bytes)
                
        elif message_type == 'user_joined':
            user_id = data.get('user_id')
            self.user_joined_voice.emit(str(user_id))
            logger.info(f"User joined: {user_id}")
            
        elif message_type == 'user_left':
            user_id = data.get('user_id')
            self.user_left_voice.emit(str(user_id))
            logger.info(f"User left: {user_id}")
            
        elif message_type == 'pong':
            # Handle pong response
            pass
            
        else:
            logger.info(f"Received message: {data}")
    
    async def send_voice_data(self, audio_data: bytes):
        """Send voice data to server."""
        if self.websocket and self.is_connected:
            try:
                # Convert bytes to list for JSON serialization
                audio_list = list(audio_data)
                await self.websocket.send(json.dumps({
                    'type': 'voice_data',
                    'audio': audio_list,
                    'timestamp': time.time()
                }))
            except Exception as e:
                logger.error(f"Error sending voice data: {e}")
    
    def send_voice_data_sync(self, audio_data: bytes):
        """Send voice data synchronously (for use from non-async code)."""
        if self.websocket and self.is_connected:
            # Create a new event loop for this thread if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Schedule the send operation
            asyncio.create_task(self.send_voice_data(audio_data))
    
    def stop_voice_chat(self):
        """Stop voice chat connection."""
        if self.websocket:
            try:
                # Close the WebSocket connection
                asyncio.create_task(self.websocket.close())
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        self.is_connected = False
        self.websocket = None
        logger.info("Voice chat stopped")
    
    def is_connected(self) -> bool:
        """Check if connected to voice server."""
        return self.is_connected
    
    def get_connection_status(self) -> str:
        """Get connection status string."""
        if self.is_connected:
            return f"Connected to {self.channel_id}"
        else:
            return "Disconnected" 