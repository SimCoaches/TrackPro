"""
Simple Voice Chat Server

A reliable, simplified voice chat server that actually works.
"""

import asyncio
import websockets
import json
import logging
import time
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleVoiceServer:
    """Simple and reliable WebSocket server for voice chat."""
    
    def __init__(self):
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_channels: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.user_info: Dict[websockets.WebSocketServerProtocol, dict] = {}
        
        logger.info("Simple voice server initialized")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections."""
        try:
            # Extract channel ID from path
            if path.startswith('/voice/'):
                channel_id = path[7:]  # Remove '/voice/' prefix
            else:
                channel_id = 'general'
            
            logger.info(f"Client connecting to channel: {channel_id}")
            
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
                'last_activity': time.time()
            }
            
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'welcome',
                'channel_id': channel_id,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }))
            
            # Notify others that user joined
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_joined',
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
            
            logger.info(f"Client connected to channel {channel_id} (User ID: {user_id})")
            
            # Handle messages from client
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, channel_id, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            await self.remove_client(websocket)
    
    async def handle_message(self, websocket, channel_id: str, data: dict):
        """Handle incoming messages from clients."""
        message_type = data.get('type')
        
        if message_type == 'voice_data':
            # Broadcast voice data to other clients in the same channel
            await self.broadcast_to_channel(channel_id, {
                'type': 'voice_data',
                'user_id': id(websocket),
                'audio': data.get('audio', []),
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
            
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
            
        elif message_type == 'user_info':
            # Handle user information
            user_name = data.get('user_name', f'User_{id(websocket)}')
            self.user_info[websocket]['name'] = user_name
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_info_update',
                'user_id': id(websocket),
                'user_name': user_name,
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
    
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
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
        
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
            'timestamp': datetime.now().isoformat()
        }, exclude={websocket})
        
        logger.info(f"Client switched from {old_channel_id} to {new_channel_id}")
    
    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude: set = None):
        """Broadcast message to all clients in a channel."""
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
        
        # Clean up user info
        if websocket in self.user_channels:
            del self.user_channels[websocket]
        if websocket in self.user_info:
            del self.user_info[websocket]
        
        # Notify others that user left
        if channel_id:
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_left',
                'user_id': id(websocket),
                'timestamp': datetime.now().isoformat()
            })
        
        logger.info(f"Client removed from channel {channel_id}")


async def main():
    """Start the simple voice chat server."""
    server = SimpleVoiceServer()
    
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
        ping_interval=30,
        ping_timeout=10
    )
    
    logger.info(f"Simple voice chat server starting on ws://{local_ip}:{server_port}")
    logger.info(f"Network accessible at ws://0.0.0.0:{server_port}")
    logger.info(f"Other users on same WiFi can connect using your IP: {local_ip}")
    
    async with start_server:
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("Starting simple voice chat server...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Voice server stopped by user")
    except Exception as e:
        print(f"Voice server error: {e}")
        import traceback
        traceback.print_exc() 