"""
High-Quality Voice Chat Server

Provides professional-grade voice chat server with advanced audio processing,
low latency, and high-quality audio transmission.
"""

import asyncio
import websockets
import json
import logging
import numpy as np
from typing import Dict, Set, Optional
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

class HighQualityVoiceServer:
    """High-quality WebSocket server for voice chat."""
    
    def __init__(self):
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_channels: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.user_info: Dict[websockets.WebSocketServerProtocol, dict] = {}
        self.audio_buffers: Dict[websockets.WebSocketServerProtocol, list] = {}
        self.speaking_users: Dict[str, Set[str]] = {}  # Track speaking users per channel
        self.user_names: Dict[websockets.WebSocketServerProtocol, str] = {}  # Track user names
        
        # Debug statistics
        self.debug_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_received': 0,
            'voice_data_broadcasted': 0,
            'errors': 0,
            'channels': {}
        }
        
        # Audio quality settings
        self.sample_rate = 48000
        self.channels = 2
        self.bit_depth = 24
        self.buffer_size = 512
        
        # Performance settings
        self.max_clients_per_channel = 50
        self.audio_buffer_size = 1000  # ms
        self.connection_timeout = 30  # seconds
        
        # Speaking detection settings
        self.speaking_threshold = 0.05  # Lower threshold for more sensitive speaking detection
        self.speaking_timeout = 2.0  # Seconds to keep speaking status after audio stops
        
        logger.info("🎤 High-quality voice server initialized with debugging")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections with high-quality audio and debugging."""
        try:
            # Extract channel ID from path
            if path.startswith('/voice/'):
                channel_id = path[7:]  # Remove '/voice/' prefix
            else:
                channel_id = 'general'
            
            logger.info(f"🎤 New client connection to channel: {channel_id}")
            self.debug_stats['total_connections'] += 1
            
            # Check channel capacity
            if channel_id in self.clients and len(self.clients[channel_id]) >= self.max_clients_per_channel:
                logger.warning(f"🎤 Channel {channel_id} is full, rejecting connection")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Channel is full'
                }))
                return
            
            # Add client to channel
            if channel_id not in self.clients:
                self.clients[channel_id] = set()
                self.debug_stats['channels'][channel_id] = {
                    'clients': 0,
                    'messages': 0,
                    'voice_data': 0
                }
            self.clients[channel_id].add(websocket)
            self.user_channels[websocket] = channel_id
            self.debug_stats['active_connections'] += 1
            self.debug_stats['channels'][channel_id]['clients'] += 1
            
            # Initialize user info
            user_id = id(websocket)
            self.user_info[websocket] = {
                'id': user_id,
                'channel': channel_id,
                'joined_at': datetime.now(),
                'last_activity': time.time(),
                'audio_quality': 'high',
                'speaking': False,
                'last_speaking': 0
            }
            
            # Initialize audio buffer
            self.audio_buffers[websocket] = []
            
            # Initialize speaking users tracking for channel
            if channel_id not in self.speaking_users:
                self.speaking_users[channel_id] = set()
            
            # Notify others that user joined
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_joined',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'channel': channel_id
            }, exclude={websocket})
            
            logger.info(f"🎤 Client connected to channel {channel_id} (User ID: {user_id}, Total clients: {len(self.clients[channel_id])})")
            
            # Send welcome message with server info
            await websocket.send(json.dumps({
                'type': 'welcome',
                'channel_id': channel_id,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'server_info': {
                    'sample_rate': self.sample_rate,
                    'channels': self.channels,
                    'bit_depth': self.bit_depth,
                    'buffer_size': self.buffer_size
                }
            }))
            
            # Handle messages from this client
            try:
                async for message in websocket:
                    self.debug_stats['messages_received'] += 1
                    self.debug_stats['channels'][channel_id]['messages'] += 1
                    
                    try:
                        data = json.loads(message)
                        logger.debug(f"🎤 Received message from {user_id} in {channel_id}: {data.get('type', 'unknown')}")
                        await self.handle_message(websocket, channel_id, data)
                    except json.JSONDecodeError as e:
                        logger.error(f"🎤 Failed to parse message from {user_id}: {e}")
                        self.debug_stats['errors'] += 1
                    except Exception as e:
                        logger.error(f"🎤 Error handling message from {user_id}: {e}")
                        self.debug_stats['errors'] += 1
                        
            except websockets.exceptions.ConnectionClosedError:
                logger.info(f"🎤 Client {user_id} disconnected from {channel_id}")
            except Exception as e:
                logger.error(f"🎤 Error in client message loop for {user_id}: {e}")
                self.debug_stats['errors'] += 1
            finally:
                # Clean up client
                await self.remove_client(websocket)
                
        except Exception as e:
            logger.error(f"🎤 Error handling client connection: {e}")
            self.debug_stats['errors'] += 1
    
    async def handle_message(self, websocket, channel_id: str, data: dict):
        """Handle incoming messages with high-quality audio processing and debugging."""
        message_type = data.get('type')
        
        if message_type == 'voice_data':
            # Process high-quality voice data with speaking detection
            await self.handle_voice_data(websocket, channel_id, data)
            
        elif message_type == 'join_channel':
            # Handle channel switching
            new_channel = data.get('channel_id', 'general')
            await self.switch_channel(websocket, new_channel)
            
        elif message_type == 'ping':
            # Respond to ping
            await websocket.send(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
            
        elif message_type == 'audio_settings':
            # Update client audio settings
            await self.update_client_audio_settings(websocket, data)
            
        elif message_type == 'mute_status':
            # Handle mute/unmute status
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_mute_status',
                'user_id': id(websocket),
                'muted': data.get('muted', False),
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
            
        elif message_type == 'user_info':
            # Handle user information (name, etc.)
            user_name = data.get('user_name', f'User_{id(websocket)}')
            self.user_names[websocket] = user_name
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_info_update',
                'user_id': id(websocket),
                'user_name': user_name,
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
        else:
            logger.debug(f"🎤 Unknown message type: {message_type}")
    
    async def handle_voice_data(self, websocket, channel_id: str, data: dict):
        """Handle high-quality voice data with speaking detection and debugging."""
        try:
            audio_data = data.get('audio', [])
            user_id = id(websocket)
            user_name = self.user_names.get(websocket, f'User_{user_id}')
            
            logger.info(f"🎤 SERVER: Processing voice data from {user_name} ({user_id}): {len(audio_data)} samples")
            
            # Detect if user is speaking based on audio level
            audio_level = self._calculate_audio_level(audio_data)
            is_speaking = audio_level > self.speaking_threshold
            
            logger.info(f"🎤 SERVER: Audio level={audio_level:.3f}, threshold={self.speaking_threshold}, speaking={is_speaking}")
            
            if is_speaking:
                logger.info(f"🎤 SERVER: User {user_name} is speaking (level: {audio_level:.3f})")
            
            # Update speaking status
            await self._update_speaking_status(websocket, channel_id, user_name, is_speaking)
            
            # Process audio data for quality
            processed_audio = self._process_audio_data(audio_data)
            
            # Count recipients for debugging
            recipients = len(self.clients[channel_id]) - 1  # Exclude sender
            logger.info(f"🎤 SERVER: Broadcasting voice data to {recipients} recipients in {channel_id}")
            
            # Broadcast to other clients in the same channel
            await self.broadcast_to_channel(channel_id, {
                'type': 'voice_data',
                'user_id': user_id,
                'user_name': user_name,
                'audio': processed_audio,
                'timestamp': datetime.now().isoformat(),
                'quality': 'high',
                'speaking': is_speaking
            }, exclude={websocket})
            
            self.debug_stats['voice_data_broadcasted'] += 1
            self.debug_stats['channels'][channel_id]['voice_data'] += 1
            
        except Exception as e:
            logger.error(f"🎤 SERVER: Error processing voice data: {e}")
            self.debug_stats['errors'] += 1
    
    def _calculate_audio_level(self, audio_data: list) -> float:
        """Calculate audio level from audio data with debugging."""
        try:
            if not audio_data:
                return 0.0
            
            # Convert list to numpy array for processing
            audio_array = np.array(audio_data, dtype=np.int16)
            
            # Calculate RMS (Root Mean Square) for audio level
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            # Normalize to 0-1 range (16-bit audio max value is 32767)
            level = min(rms / 32767.0, 1.0)
            
            # Apply logarithmic scaling for better sensitivity
            if level > 0:
                level = np.log10(1 + level * 9) / np.log10(10)
            
            logger.debug(f"🎤 Server audio level calculated: {level:.3f} (RMS: {rms:.1f})")
            return level
            
        except Exception as e:
            logger.error(f"🎤 Error calculating audio level: {e}")
            return 0.0
    
    async def _update_speaking_status(self, websocket, channel_id: str, user_name: str, is_speaking: bool):
        """Update speaking status and broadcast to all clients with debugging."""
        try:
            current_time = time.time()
            user_id = id(websocket)
            
            if is_speaking:
                # Add user to speaking set
                self.speaking_users[channel_id].add(user_name)
                self.user_info[websocket]['speaking'] = True
                self.user_info[websocket]['last_speaking'] = current_time
                
                # Broadcast speaking status
                await self.broadcast_to_channel(channel_id, {
                    'type': 'user_speaking',
                    'user_id': user_id,
                    'user_name': user_name,
                    'speaking': True,
                    'timestamp': datetime.now().isoformat()
                }, exclude={websocket})
                
                logger.debug(f"🎤 User {user_name} started speaking in {channel_id}")
                
            else:
                # Check if user should stop speaking (timeout)
                last_speaking = self.user_info[websocket]['last_speaking']
                if current_time - last_speaking > self.speaking_timeout:
                    # Remove from speaking set
                    self.speaking_users[channel_id].discard(user_name)
                    self.user_info[websocket]['speaking'] = False
                    
                    # Broadcast speaking status
                    await self.broadcast_to_channel(channel_id, {
                        'type': 'user_speaking',
                        'user_id': user_id,
                        'user_name': user_name,
                        'speaking': False,
                        'timestamp': datetime.now().isoformat()
                    }, exclude={websocket})
                    
                    logger.debug(f"🎤 User {user_name} stopped speaking in {channel_id}")
                    
        except Exception as e:
            logger.error(f"🎤 Error updating speaking status: {e}")
            self.debug_stats['errors'] += 1
    
    def _process_audio_data(self, audio_data: list) -> list:
        """Process audio data for quality with debugging."""
        try:
            # Convert to numpy array for processing
            audio_array = np.array(audio_data, dtype=np.float32)
            
            # Apply basic audio processing (noise reduction, normalization)
            # For now, just return the original data
            processed_data = audio_data
            
            logger.debug(f"🎤 Processed audio data: {len(audio_data)} samples")
            return processed_data
            
        except Exception as e:
            logger.error(f"🎤 Error processing audio data: {e}")
            return audio_data
    
    async def switch_channel(self, websocket, new_channel_id: str):
        """Switch client to a different channel with debugging."""
        try:
            old_channel_id = self.user_channels.get(websocket)
            user_id = id(websocket)
            user_name = self.user_names.get(websocket, f'User_{user_id}')
            
            logger.info(f"🎤 User {user_name} switching from {old_channel_id} to {new_channel_id}")
            
            # Remove from old channel
            if old_channel_id and old_channel_id in self.clients:
                self.clients[old_channel_id].discard(websocket)
                self.debug_stats['channels'][old_channel_id]['clients'] -= 1
                
                # Notify others in old channel
                await self.broadcast_to_channel(old_channel_id, {
                    'type': 'user_left',
                    'user_id': user_id,
                    'user_name': user_name,
                    'timestamp': datetime.now().isoformat()
                }, exclude={websocket})
                
                logger.info(f"🎤 User {user_name} left channel {old_channel_id}")
            
            # Add to new channel
            if new_channel_id not in self.clients:
                self.clients[new_channel_id] = set()
                self.debug_stats['channels'][new_channel_id] = {
                    'clients': 0,
                    'messages': 0,
                    'voice_data': 0
                }
            
            self.clients[new_channel_id].add(websocket)
            self.user_channels[websocket] = new_channel_id
            self.debug_stats['channels'][new_channel_id]['clients'] += 1
            
            # Update user info
            self.user_info[websocket]['channel'] = new_channel_id
            
            # Notify others in new channel
            await self.broadcast_to_channel(new_channel_id, {
                'type': 'user_joined',
                'user_id': user_id,
                'user_name': user_name,
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
            
            logger.info(f"🎤 User {user_name} joined channel {new_channel_id}")
            
        except Exception as e:
            logger.error(f"🎤 Error switching channel: {e}")
            self.debug_stats['errors'] += 1
    
    async def update_client_audio_settings(self, websocket, data: dict):
        """Update client audio settings with debugging."""
        try:
            user_id = id(websocket)
            logger.info(f"🎤 Updating audio settings for user {user_id}: {data}")
            
            # Store settings in user info
            self.user_info[websocket]['audio_settings'] = data
            
        except Exception as e:
            logger.error(f"🎤 Error updating audio settings: {e}")
            self.debug_stats['errors'] += 1
    
    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude: set = None):
        """Broadcast message to all clients in a channel with debugging."""
        try:
            if channel_id not in self.clients:
                logger.warning(f"🎤 Channel {channel_id} not found for broadcast")
                return
            
            exclude = exclude or set()
            recipients = len(self.clients[channel_id]) - len(exclude)
            
            if recipients <= 0:
                logger.debug(f"🎤 No recipients for broadcast in {channel_id}")
                return
            
            # Send message to all clients in channel (except excluded ones)
            disconnected_clients = set()
            
            for client in self.clients[channel_id]:
                if client in exclude:
                    continue
                    
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosedError:
                    logger.debug(f"🎤 Client disconnected during broadcast")
                    disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"🎤 Error broadcasting to client: {e}")
                    disconnected_clients.add(client)
            
            # Clean up disconnected clients
            for client in disconnected_clients:
                await self.remove_client(client)
            
            logger.debug(f"🎤 Broadcasted {message.get('type', 'unknown')} to {recipients} clients in {channel_id}")
            
        except Exception as e:
            logger.error(f"🎤 Error broadcasting to channel {channel_id}: {e}")
            self.debug_stats['errors'] += 1
    
    async def remove_client(self, websocket):
        """Remove client from server with debugging."""
        try:
            user_id = id(websocket)
            user_name = self.user_names.get(websocket, f'User_{user_id}')
            channel_id = self.user_channels.get(websocket)
            
            logger.info(f"🎤 Removing client {user_name} ({user_id}) from {channel_id}")
            
            # Remove from channel
            if channel_id and channel_id in self.clients:
                self.clients[channel_id].discard(websocket)
                self.debug_stats['channels'][channel_id]['clients'] -= 1
                
                # Notify others that user left
                await self.broadcast_to_channel(channel_id, {
                    'type': 'user_left',
                    'user_id': user_id,
                    'user_name': user_name,
                    'timestamp': datetime.now().isoformat()
                }, exclude={websocket})
                
                logger.info(f"🎤 User {user_name} left channel {channel_id}")
            
            # Clean up user data
            self.user_channels.pop(websocket, None)
            self.user_info.pop(websocket, None)
            self.audio_buffers.pop(websocket, None)
            self.user_names.pop(websocket, None)
            
            # Update active connections count
            self.debug_stats['active_connections'] -= 1
            
            logger.info(f"🎤 Client {user_name} removed successfully")
            
        except Exception as e:
            logger.error(f"🎤 Error removing client: {e}")
            self.debug_stats['errors'] += 1
    
    async def cleanup_inactive_clients(self):
        """Clean up inactive clients with debugging."""
        try:
            current_time = time.time()
            inactive_clients = []
            
            for websocket, user_info in self.user_info.items():
                if current_time - user_info['last_activity'] > self.connection_timeout:
                    inactive_clients.append(websocket)
            
            if inactive_clients:
                logger.info(f"🎤 Cleaning up {len(inactive_clients)} inactive clients")
                for client in inactive_clients:
                    await self.remove_client(client)
            
        except Exception as e:
            logger.error(f"🎤 Error cleaning up inactive clients: {e}")
            self.debug_stats['errors'] += 1
    
    def get_server_stats(self) -> dict:
        """Get server statistics with debugging."""
        try:
            stats = {
                'total_connections': self.debug_stats['total_connections'],
                'active_connections': self.debug_stats['active_connections'],
                'messages_received': self.debug_stats['messages_received'],
                'voice_data_broadcasted': self.debug_stats['voice_data_broadcasted'],
                'errors': self.debug_stats['errors'],
                'channels': {},
                'speaking_users': {}
            }
            
            # Add channel statistics
            for channel_id, channel_stats in self.debug_stats['channels'].items():
                stats['channels'][channel_id] = {
                    'clients': channel_stats['clients'],
                    'messages': channel_stats['messages'],
                    'voice_data': channel_stats['voice_data']
                }
            
            # Add speaking users per channel
            for channel_id, speaking_set in self.speaking_users.items():
                stats['speaking_users'][channel_id] = list(speaking_set)
            
            logger.info(f"🎤 Server stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"🎤 Error getting server stats: {e}")
            return {}

async def main():
    """Main server function with debugging."""
    try:
        logger.info("🎤 Starting high-quality voice server...")
        
        # Create server instance
        server = HighQualityVoiceServer()
        
        # Get local IP address for network access
        import socket
        def get_local_ip():
            try:
                # Connect to a remote address to determine local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                return local_ip
            except Exception:
                return "0.0.0.0"  # Fallback to all interfaces
        
        local_ip = get_local_ip()
        server_port = 8080
        
        # Start WebSocket server on all interfaces
        start_server = websockets.serve(
            server.handle_client,
            "0.0.0.0",  # Bind to all interfaces
            server_port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"🎤 Voice server started on ws://{local_ip}:{server_port}")
        logger.info(f"🎤 Network accessible at ws://0.0.0.0:{server_port}")
        logger.info(f"🎤 Other users on same WiFi can connect using your IP: {local_ip}")
        
        # Start cleanup task
        async def cleanup_task():
            while True:
                await asyncio.sleep(30)  # Clean up every 30 seconds
                await server.cleanup_inactive_clients()
                
                # Log server stats periodically
                stats = server.get_server_stats()
                logger.info(f"🎤 Server status: {stats['active_connections']} active connections, {stats['messages_received']} messages")
        
        # Run server and cleanup task
        await asyncio.gather(
            start_server,
            cleanup_task()
        )
        
    except Exception as e:
        logger.error(f"🎤 Server error: {e}")

if __name__ == "__main__":
    # Set up logging
    try:
        from .logging_config import setup_logging
        setup_logging()
    except Exception:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Run server
    asyncio.run(main())