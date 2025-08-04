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
        
        # Audio quality settings
        self.sample_rate = 48000
        self.channels = 2
        self.bit_depth = 24
        self.buffer_size = 512
        
        # Performance settings
        self.max_clients_per_channel = 50
        self.audio_buffer_size = 1000  # ms
        self.connection_timeout = 30  # seconds
        
        logger.info("High-quality voice server initialized")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections with high-quality audio."""
        try:
            # Extract channel ID from path
            if path.startswith('/voice/'):
                channel_id = path[7:]  # Remove '/voice/' prefix
            else:
                channel_id = 'general'
            
            # Check channel capacity
            if channel_id in self.clients and len(self.clients[channel_id]) >= self.max_clients_per_channel:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Channel is full'
                }))
                return
            
            # Add client to channel
            if channel_id not in self.clients:
                self.clients[channel_id] = set()
            self.clients[channel_id].add(websocket)
            self.user_channels[websocket] = channel_id
            
            # Initialize user info
            user_id = id(websocket)
            self.user_info[websocket] = {
                'id': user_id,
                'channel': channel_id,
                'joined_at': datetime.now(),
                'last_activity': time.time(),
                'audio_quality': 'high'
            }
            
            # Initialize audio buffer
            self.audio_buffers[websocket] = []
            
            # Notify others that user joined
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_joined',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'channel': channel_id
            }, exclude={websocket})
            
            logger.info(f"Client connected to channel {channel_id} (User ID: {user_id})")
            
            # Send welcome message with server info
            await websocket.send(json.dumps({
                'type': 'welcome',
                'server_info': {
                    'sample_rate': self.sample_rate,
                    'channels': self.channels,
                    'bit_depth': self.bit_depth,
                    'buffer_size': self.buffer_size
                },
                'channel_id': channel_id,
                'user_id': user_id
            }))
            
            # Handle messages from client
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, channel_id, data)
                    # Update last activity
                    self.user_info[websocket]['last_activity'] = time.time()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            # Clean up client
            await self.remove_client(websocket)
    
    async def handle_message(self, websocket, channel_id: str, data: dict):
        """Handle incoming messages with high-quality audio processing."""
        message_type = data.get('type')
        
        if message_type == 'voice_data':
            # Process high-quality voice data
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
    
    async def handle_voice_data(self, websocket, channel_id: str, data: dict):
        """Handle high-quality voice data with processing."""
        try:
            audio_data = data.get('audio', [])
            user_id = id(websocket)
            
            # Process audio data for quality
            processed_audio = self._process_audio_data(audio_data)
            
            # Broadcast to other clients in the same channel
            await self.broadcast_to_channel(channel_id, {
                'type': 'voice_data',
                'user_id': user_id,
                'audio': processed_audio,
                'timestamp': datetime.now().isoformat(),
                'quality': 'high'
            }, exclude={websocket})
            
        except Exception as e:
            logger.error(f"Error processing voice data: {e}")
    
    def _process_audio_data(self, audio_data: list) -> list:
        """Process audio data for high quality transmission."""
        try:
            # Convert to numpy for processing
            audio_array = np.array(audio_data, dtype=np.int32)
            
            # Apply basic audio enhancement
            # Normalize audio levels
            if np.max(np.abs(audio_array)) > 0:
                audio_array = audio_array / np.max(np.abs(audio_array)) * 0.8
            
            # Convert back to list
            return audio_array.tolist()
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            return audio_data
    
    async def switch_channel(self, websocket, new_channel_id: str):
        """Switch client to a different channel."""
        old_channel_id = self.user_channels.get(websocket)
        
        if old_channel_id:
            # Remove from old channel
            if old_channel_id in self.clients:
                self.clients[old_channel_id].discard(websocket)
                if not self.clients[old_channel_id]:
                    del self.clients[old_channel_id]
            
            # Notify others in old channel
            await self.broadcast_to_channel(old_channel_id, {
                'type': 'user_left',
                'user_id': id(websocket),
                'timestamp': datetime.now().isoformat(),
                'channel': old_channel_id
            }, exclude={websocket})
        
        # Check new channel capacity
        if new_channel_id in self.clients and len(self.clients[new_channel_id]) >= self.max_clients_per_channel:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Channel is full'
            }))
            return
        
        # Add to new channel
        if new_channel_id not in self.clients:
            self.clients[new_channel_id] = set()
        self.clients[new_channel_id].add(websocket)
        self.user_channels[websocket] = new_channel_id
        
        # Update user info
        if websocket in self.user_info:
            self.user_info[websocket]['channel'] = new_channel_id
        
        # Notify others in new channel
        await self.broadcast_to_channel(new_channel_id, {
            'type': 'user_joined',
            'user_id': id(websocket),
            'timestamp': datetime.now().isoformat(),
            'channel': new_channel_id
        }, exclude={websocket})
        
        logger.info(f"Client switched from {old_channel_id} to {new_channel_id}")
    
    async def update_client_audio_settings(self, websocket, data: dict):
        """Update client audio settings."""
        if websocket in self.user_info:
            self.user_info[websocket].update({
                'audio_quality': data.get('quality', 'high'),
                'sample_rate': data.get('sample_rate', 48000),
                'channels': data.get('channels', 2),
                'bit_depth': data.get('bit_depth', 24)
            })
            
            logger.info(f"Updated audio settings for user {id(websocket)}")
    
    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude: set = None):
        """Broadcast message to all clients in a channel with error handling."""
        if channel_id not in self.clients:
            return
        
        exclude = exclude or set()
        message_json = json.dumps(message)
        
        # Send to all clients in channel except excluded ones
        disconnected_clients = set()
        
        for client in self.clients[channel_id] - exclude:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            await self.remove_client(client)
    
    async def remove_client(self, websocket):
        """Remove client from all channels and notify others."""
        channel_id = self.user_channels.get(websocket)
        
        if channel_id and channel_id in self.clients:
            self.clients[channel_id].discard(websocket)
            if not self.clients[channel_id]:
                del self.clients[channel_id]
        
        # Clean up user info and audio buffers
        if websocket in self.user_channels:
            del self.user_channels[websocket]
        if websocket in self.user_info:
            del self.user_info[websocket]
        if websocket in self.audio_buffers:
            del self.audio_buffers[websocket]
        
        # Notify others that user left
        if channel_id:
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_left',
                'user_id': id(websocket),
                'timestamp': datetime.now().isoformat(),
                'channel': channel_id
            })
        
        logger.info(f"Client removed from channel {channel_id}")
    
    async def cleanup_inactive_clients(self):
        """Periodically cleanup inactive clients."""
        while True:
            try:
                current_time = time.time()
                inactive_clients = []
                
                for websocket, user_info in self.user_info.items():
                    if current_time - user_info['last_activity'] > self.connection_timeout:
                        inactive_clients.append(websocket)
                
                for websocket in inactive_clients:
                    logger.info(f"Removing inactive client {id(websocket)}")
                    await self.remove_client(websocket)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)
    
    def get_server_stats(self) -> dict:
        """Get server statistics."""
        total_clients = sum(len(clients) for clients in self.clients.values())
        total_channels = len(self.clients)
        
        return {
            'total_clients': total_clients,
            'total_channels': total_channels,
            'channels': {
                channel_id: len(clients) 
                for channel_id, clients in self.clients.items()
            },
            'server_info': {
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'bit_depth': self.bit_depth,
                'max_clients_per_channel': self.max_clients_per_channel
            }
        }


async def main():
    """Start the high-quality voice chat server."""
    server = HighQualityVoiceServer()
    
    # Start cleanup task
    cleanup_task = asyncio.create_task(server.cleanup_inactive_clients())
    
    # Start WebSocket server
    start_server = websockets.serve(
        server.handle_client,
        "localhost",
        8080,
        ping_interval=30,
        ping_timeout=10,
        max_size=1024 * 1024  # 1MB max message size
    )
    
    logger.info("High-quality voice chat server starting on ws://localhost:8080")
    logger.info(f"Audio settings: {server.sample_rate}Hz, {server.channels}ch, {server.bit_depth}bit")
    
    async with start_server:
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main()) 