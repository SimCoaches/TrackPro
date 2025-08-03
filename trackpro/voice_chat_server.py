"""Simple WebSocket server for voice chat functionality."""

import asyncio
import websockets
import json
import logging
from typing import Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class VoiceChatServer:
    """WebSocket server for voice chat."""
    
    def __init__(self):
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_channels: Dict[websockets.WebSocketServerProtocol, str] = {}
    
    async def handle_client(self, websocket, path):
        """Handle individual client connections."""
        try:
            # Extract channel ID from path
            if path.startswith('/voice/'):
                channel_id = path[7:]  # Remove '/voice/' prefix
            else:
                channel_id = 'general'
            
            # Add client to channel
            if channel_id not in self.clients:
                self.clients[channel_id] = set()
            self.clients[channel_id].add(websocket)
            self.user_channels[websocket] = channel_id
            
            # Notify others that user joined
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_joined',
                'user_id': id(websocket),
                'timestamp': datetime.now().isoformat()
            }, exclude={websocket})
            
            logger.info(f"Client connected to channel {channel_id}")
            
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
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            # Clean up client
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
        for client in self.clients[channel_id] - exclude:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                # Client disconnected, will be cleaned up later
                pass
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
    
    async def remove_client(self, websocket):
        """Remove client from all channels and notify others."""
        channel_id = self.user_channels.get(websocket)
        
        if channel_id and channel_id in self.clients:
            self.clients[channel_id].discard(websocket)
            if not self.clients[channel_id]:
                del self.clients[channel_id]
        
        if websocket in self.user_channels:
            del self.user_channels[websocket]
        
        # Notify others that user left
        if channel_id:
            await self.broadcast_to_channel(channel_id, {
                'type': 'user_left',
                'user_id': id(websocket),
                'timestamp': datetime.now().isoformat()
            })
        
        logger.info(f"Client removed from channel {channel_id}")


async def main():
    """Start the voice chat server."""
    server = VoiceChatServer()
    
    # Start WebSocket server
    start_server = websockets.serve(
        server.handle_client,
        "localhost",
        8080,
        ping_interval=30,
        ping_timeout=10
    )
    
    logger.info("Voice chat server starting on ws://localhost:8080")
    
    async with start_server:
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 