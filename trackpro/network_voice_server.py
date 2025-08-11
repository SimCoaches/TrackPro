#!/usr/bin/env python3
"""
Network Voice Server for TrackPro

A standalone voice chat server that runs on the network so multiple users
on the same WiFi can connect and chat together.

Usage:
    python trackpro/network_voice_server.py

This server will:
- Bind to all network interfaces (0.0.0.0)
- Display the local IP address for other users to connect
- Run continuously until stopped with Ctrl+C
- Support multiple voice channels
- Handle high-quality audio with speaking detection
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
import socket
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

class NetworkVoiceServer:
    """Network-accessible voice chat server for TrackPro."""
    
    def __init__(self):
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_channels: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.user_info: Dict[websockets.WebSocketServerProtocol, dict] = {}
        self.speaking_users: Dict[str, Set[str]] = {}
        self.user_names: Dict[websockets.WebSocketServerProtocol, str] = {}
        
        # Server statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_received': 0,
            'voice_data_broadcasted': 0,
            'errors': 0,
            'channels': {}
        }
        
        # Audio settings
        self.sample_rate = 48000
        self.channels = 2
        self.bit_depth = 24
        self.buffer_size = 512
        
        # Performance settings
        self.max_clients_per_channel = 50
        self.connection_timeout = 30
        self.speaking_threshold = 0.05
        self.speaking_timeout = 2.0
        
        logger.info("Network voice server initialized")
    
    def get_local_ip(self):
        """Get the local IP address for network access."""
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "0.0.0.0"
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections."""
        try:
            # Extract channel ID from path
            if path.startswith('/voice/'):
                channel_id = path[7:]  # Remove '/voice/' prefix
            else:
                channel_id = 'general'
            
            logger.info(f"New client connection to channel: {channel_id}")
            self.stats['total_connections'] += 1
            
            # Check channel capacity
            if channel_id in self.clients and len(self.clients[channel_id]) >= self.max_clients_per_channel:
                logger.warning(f"Channel {channel_id} is full, rejecting connection")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Channel is full'
                }))
                return
            
            # Add client to channel
            if channel_id not in self.clients:
                # This is the first user joining this channel - create the room
                self.clients[channel_id] = set()
                self.stats['channels'][channel_id] = {
                    'clients': 0,
                    'messages': 0,
                    'voice_data': 0
                }
                logger.info(f"[NEW] Created new voice channel: {channel_id} (first user joining)")
            else:
                logger.info(f"User joining existing voice channel: {channel_id}")
                
            self.clients[channel_id].add(websocket)
            self.user_channels[websocket] = channel_id
            self.stats['active_connections'] += 1
            self.stats['channels'][channel_id]['clients'] += 1
            
            # Initialize user info
            user_id = id(websocket)
            self.user_info[websocket] = {
                'id': user_id,
                'channel': channel_id,
                'joined_at': datetime.now(),
                'last_activity': time.time(),
                'speaking': False,
                'last_speaking': 0
            }
            
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
            
            logger.info(f"Client connected to channel {channel_id} (User ID: {user_id}, Total clients: {len(self.clients[channel_id])})")
            
            # Send welcome message
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
                    self.stats['messages_received'] += 1
                    self.stats['channels'][channel_id]['messages'] += 1
                    
                    try:
                        data = json.loads(message)
                        await self.handle_message(websocket, channel_id, data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                        self.stats['errors'] += 1
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
                        self.stats['errors'] += 1
                        
            except websockets.exceptions.ConnectionClosedError:
                logger.info(f"Client {user_id} disconnected from {channel_id}")
            except Exception as e:
                logger.error(f"Error in client message loop: {e}")
                self.stats['errors'] += 1
            finally:
                # Clean up client
                await self.remove_client(websocket)
                
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
            self.stats['errors'] += 1
    
    async def handle_message(self, websocket, channel_id: str, data: dict):
        """Handle incoming messages."""
        message_type = data.get('type')
        
        if message_type == 'voice_data':
            await self.handle_voice_data(websocket, channel_id, data)
        elif message_type == 'join_channel':
            new_channel = data.get('channel_id', 'general')
            await self.switch_channel(websocket, new_channel)
        elif message_type == 'ping':
            await websocket.send(json.dumps({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            }))
        elif message_type == 'mute_status':
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_mute_status',
                'user_id': id(websocket),
                'muted': data.get('muted', False),
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
        elif message_type == 'user_info':
            user_name = data.get('user_name', f'User_{id(websocket)}')
            self.user_names[websocket] = user_name
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_info_update',
                'user_id': id(websocket),
                'user_name': user_name,
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
    
    async def handle_voice_data(self, websocket, channel_id: str, data: dict):
        """Handle voice data with speaking detection."""
        try:
            audio_data = data.get('audio', [])
            user_id = id(websocket)
            user_name = self.user_names.get(websocket, f'User_{user_id}')
            
            # Detect if user is speaking
            audio_level = self._calculate_audio_level(audio_data)
            is_speaking = audio_level > self.speaking_threshold
            
            # Update speaking status
            await self._update_speaking_status(websocket, channel_id, user_name, is_speaking)
            
            # Broadcast to other clients in the same channel
            await self.broadcast_to_channel(channel_id, {
                'type': 'voice_data',
                'user_id': user_id,
                'user_name': user_name,
                'audio': audio_data,
                'timestamp': datetime.now().isoformat(),
                'speaking': is_speaking
            }, exclude={websocket})
            
            self.stats['voice_data_broadcasted'] += 1
            self.stats['channels'][channel_id]['voice_data'] += 1
            
        except Exception as e:
            logger.error(f"Error processing voice data: {e}")
            self.stats['errors'] += 1
    
    def _calculate_audio_level(self, audio_data: list) -> float:
        """Calculate audio level from audio data."""
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
            
            return level
            
        except Exception as e:
            logger.error(f"Error calculating audio level: {e}")
            return 0.0
    
    async def _update_speaking_status(self, websocket, channel_id: str, user_name: str, is_speaking: bool):
        """Update speaking status and broadcast to all clients."""
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
                    
        except Exception as e:
            logger.error(f"Error updating speaking status: {e}")
            self.stats['errors'] += 1
    
    async def switch_channel(self, websocket, new_channel_id: str):
        """Switch client to a different channel."""
        try:
            old_channel_id = self.user_channels.get(websocket)
            user_id = id(websocket)
            user_name = self.user_names.get(websocket, f'User_{user_id}')
            
            logger.info(f"User {user_name} switching from {old_channel_id} to {new_channel_id}")
            
            # Remove from old channel
            if old_channel_id and old_channel_id in self.clients:
                self.clients[old_channel_id].discard(websocket)
                self.stats['channels'][old_channel_id]['clients'] -= 1
                
                # Notify others in old channel
                await self.broadcast_to_channel(old_channel_id, {
                    'type': 'user_left',
                    'user_id': user_id,
                    'user_name': user_name,
                    'timestamp': datetime.now().isoformat()
                }, exclude={websocket})
            
            # Add to new channel
            if new_channel_id not in self.clients:
                self.clients[new_channel_id] = set()
                self.stats['channels'][new_channel_id] = {
                    'clients': 0,
                    'messages': 0,
                    'voice_data': 0
                }
            
            self.clients[new_channel_id].add(websocket)
            self.user_channels[websocket] = new_channel_id
            self.stats['channels'][new_channel_id]['clients'] += 1
            
            # Update user info
            self.user_info[websocket]['channel'] = new_channel_id
            
            # Notify others in new channel
            await self.broadcast_to_channel(new_channel_id, {
                'type': 'user_joined',
                'user_id': user_id,
                'user_name': user_name,
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
            
        except Exception as e:
            logger.error(f"Error switching channel: {e}")
            self.stats['errors'] += 1
    
    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude: set = None):
        """Broadcast message to all clients in a channel."""
        try:
            if channel_id not in self.clients:
                return
            
            exclude = exclude or set()
            
            # Send message to all clients in channel (except excluded ones)
            disconnected_clients = set()
            
            for client in self.clients[channel_id]:
                if client in exclude:
                    continue
                    
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosedError:
                    disconnected_clients.add(client)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    disconnected_clients.add(client)
            
            # Clean up disconnected clients
            for client in disconnected_clients:
                await self.remove_client(client)
            
        except Exception as e:
            logger.error(f"Error broadcasting to channel {channel_id}: {e}")
            self.stats['errors'] += 1
    
    async def remove_client(self, websocket):
        """Remove client from server."""
        try:
            user_id = id(websocket)
            user_name = self.user_names.get(websocket, f'User_{user_id}')
            channel_id = self.user_channels.get(websocket)
            
            logger.info(f"Removing client {user_name} ({user_id}) from {channel_id}")
            
            # Remove from channel
            if channel_id and channel_id in self.clients:
                self.clients[channel_id].discard(websocket)
                self.stats['channels'][channel_id]['clients'] -= 1
                
                # Notify others that user left
                await self.broadcast_to_channel(channel_id, {
                    'type': 'user_left',
                    'user_id': user_id,
                    'user_name': user_name,
                    'timestamp': datetime.now().isoformat()
                }, exclude={websocket})
            
            # Clean up user data
            self.user_channels.pop(websocket, None)
            self.user_info.pop(websocket, None)
            self.user_names.pop(websocket, None)
            
            # Update active connections count
            self.stats['active_connections'] -= 1
            
        except Exception as e:
            logger.error(f"Error removing client: {e}")
            self.stats['errors'] += 1
    
    async def cleanup_inactive_clients(self):
        """Clean up inactive clients."""
        try:
            current_time = time.time()
            inactive_clients = []
            
            for websocket, user_info in self.user_info.items():
                if current_time - user_info['last_activity'] > self.connection_timeout:
                    inactive_clients.append(websocket)
            
            if inactive_clients:
                logger.info(f"Cleaning up {len(inactive_clients)} inactive clients")
                for client in inactive_clients:
                    await self.remove_client(client)
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive clients: {e}")
            self.stats['errors'] += 1
    
    def get_server_stats(self) -> dict:
        """Get server statistics."""
        try:
            stats = {
                'total_connections': self.stats['total_connections'],
                'active_connections': self.stats['active_connections'],
                'messages_received': self.stats['messages_received'],
                'voice_data_broadcasted': self.stats['voice_data_broadcasted'],
                'errors': self.stats['errors'],
                'channels': {},
                'speaking_users': {}
            }
            
            # Add channel statistics
            for channel_id, channel_stats in self.stats['channels'].items():
                stats['channels'][channel_id] = {
                    'clients': channel_stats['clients'],
                    'messages': channel_stats['messages'],
                    'voice_data': channel_stats['voice_data']
                }
            
            # Add speaking users per channel
            for channel_id, speaking_set in self.speaking_users.items():
                stats['speaking_users'][channel_id] = list(speaking_set)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting server stats: {e}")
            return {}

async def main():
    """Main server function."""
    try:
        logger.info("Starting network voice server (on-demand mode)...")
        
        # Create server instance
        server = NetworkVoiceServer()
        
        # Get local IP and port from environment variable
        local_ip = server.get_local_ip()
        server_port = int(os.environ.get('VOICE_SERVER_PORT', 8080))
        
        # Start WebSocket server on all interfaces
        start_server = websockets.serve(
            server.handle_client,
            "0.0.0.0",  # Bind to all interfaces
            server_port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"Network voice server started successfully!")
        logger.info(f"Local access: ws://localhost:{server_port}")
        logger.info(f"Network access: ws://{local_ip}:{server_port}")
        logger.info(f"Other users on same WiFi can connect using: {local_ip}")
        logger.info(f"Channels will be created automatically when first user joins")
        logger.info(f"Press Ctrl+C to stop the server")
        
        # Start cleanup task
        async def cleanup_task():
            while True:
                await asyncio.sleep(30)  # Clean up every 30 seconds
                await server.cleanup_inactive_clients()
                
                # Log server stats periodically
                stats = server.get_server_stats()
                active_channels = len([c for c in stats['channels'].values() if c['clients'] > 0])
                logger.info(f"Server status: {stats['active_connections']} active connections, {active_channels} active channels, {stats['messages_received']} messages")
        
        # Run server and cleanup task
        await asyncio.gather(
            start_server,
            cleanup_task()
        )
        
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    # Set up logging
    try:
        from .logging_config import setup_logging
        setup_logging()
    except Exception:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("TrackPro Network Voice Server")
    print("=" * 40)
    print("This server allows multiple users on the same WiFi network")
    print("to connect and chat together in voice channels.")
    print()
    
    try:
        # Run server
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVoice server stopped by user")
    except Exception as e:
        print(f"Voice server error: {e}")
        import traceback
        traceback.print_exc() 