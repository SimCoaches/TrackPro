"""
TrackPro WebSocket Connection Manager
Handles WebSocket connections, message routing, and connection health monitoring
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List
from collections import defaultdict, deque
import time

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionInfo:
    """Information about a WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.messages_sent = 0
        self.messages_received = 0
        self.subscriptions: Set[str] = set()
        self.user_id: Optional[str] = None
        self.is_authenticated = False
        
    def update_heartbeat(self):
        """Update the last heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow()
        
    def add_subscription(self, topic: str):
        """Add a subscription topic"""
        self.subscriptions.add(topic)
        
    def remove_subscription(self, topic: str):
        """Remove a subscription topic"""
        self.subscriptions.discard(topic)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection info to dictionary"""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "subscriptions": list(self.subscriptions),
            "is_authenticated": self.is_authenticated
        }

class MessageBuffer:
    """Buffer for batching messages efficiently"""
    
    def __init__(self, max_size: int = 100, flush_interval: float = 0.1):
        self.max_size = max_size
        self.flush_interval = flush_interval
        self.buffer: deque = deque()
        self.last_flush = time.time()
        
    def add_message(self, message: Dict[str, Any]) -> bool:
        """Add message to buffer. Returns True if buffer should be flushed"""
        self.buffer.append(message)
        current_time = time.time()
        
        return (len(self.buffer) >= self.max_size or 
                current_time - self.last_flush >= self.flush_interval)
    
    def flush(self) -> List[Dict[str, Any]]:
        """Flush and return all buffered messages"""
        messages = list(self.buffer)
        self.buffer.clear()
        self.last_flush = time.time()
        return messages

class ConnectionManager:
    """Manages WebSocket connections with advanced features"""
    
    def __init__(self):
        # Connection tracking
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.topic_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self.start_time = datetime.utcnow()
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_connections = 0
        
        # Message batching
        self.message_buffers: Dict[str, MessageBuffer] = {}
        self.high_frequency_topics = {"telemetry", "pedal_data", "real_time_updates"}
        
        # Health monitoring
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 60  # seconds
        self._heartbeat_task = None
        
    async def connect(self, websocket: WebSocket) -> str:
        """Register a new WebSocket connection"""
        client_id = str(uuid.uuid4())
        connection_info = ConnectionInfo(websocket, client_id)
        
        self.active_connections[client_id] = connection_info
        self.total_connections += 1
        
        # Initialize message buffer for this connection
        self.message_buffers[client_id] = MessageBuffer()
        
        # Start heartbeat monitoring if not already running
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        
        logger.info(f"New connection registered: {client_id}")
        return client_id
    
    async def disconnect(self, client_id: str):
        """Disconnect and clean up a WebSocket connection"""
        if client_id in self.active_connections:
            connection_info = self.active_connections[client_id]
            
            # Remove from user connections
            if connection_info.user_id:
                self.user_connections[connection_info.user_id].discard(client_id)
                if not self.user_connections[connection_info.user_id]:
                    del self.user_connections[connection_info.user_id]
            
            # Remove from topic subscriptions
            for topic in connection_info.subscriptions:
                self.topic_subscriptions[topic].discard(client_id)
                if not self.topic_subscriptions[topic]:
                    del self.topic_subscriptions[topic]
            
            # Clean up
            del self.active_connections[client_id]
            if client_id in self.message_buffers:
                del self.message_buffers[client_id]
            
            logger.info(f"Connection disconnected: {client_id}")
    
    async def authenticate_connection(self, client_id: str, user_id: str):
        """Authenticate a connection with a user ID"""
        if client_id in self.active_connections:
            connection_info = self.active_connections[client_id]
            connection_info.user_id = user_id
            connection_info.is_authenticated = True
            self.user_connections[user_id].add(client_id)
            logger.info(f"Connection {client_id} authenticated as user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send a message to a specific client"""
        if client_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent client: {client_id}")
            return
        
        connection_info = self.active_connections[client_id]
        
        try:
            # Determine if this should be buffered
            message_type = message.get("type", "")
            if message_type in self.high_frequency_topics:
                # Use message batching for high-frequency data
                buffer = self.message_buffers.get(client_id)
                if buffer and buffer.add_message(message):
                    await self._flush_message_buffer(client_id)
            else:
                # Send immediately for low-frequency messages
                await connection_info.websocket.send_text(json.dumps(message))
                connection_info.messages_sent += 1
                self.total_messages_sent += 1
                
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self.disconnect(client_id)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections for a specific user"""
        if user_id in self.user_connections:
            for client_id in list(self.user_connections[user_id]):
                await self.send_personal_message(message, client_id)
    
    async def broadcast_to_topic(self, message: Dict[str, Any], topic: str):
        """Broadcast a message to all clients subscribed to a topic"""
        if topic in self.topic_subscriptions:
            for client_id in list(self.topic_subscriptions[topic]):
                await self.send_personal_message(message, client_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        for client_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, client_id)
    
    async def subscribe_to_topic(self, client_id: str, topic: str):
        """Subscribe a client to a topic"""
        if client_id in self.active_connections:
            connection_info = self.active_connections[client_id]
            connection_info.add_subscription(topic)
            self.topic_subscriptions[topic].add(client_id)
            logger.info(f"Client {client_id} subscribed to topic: {topic}")
    
    async def unsubscribe_from_topic(self, client_id: str, topic: str):
        """Unsubscribe a client from a topic"""
        if client_id in self.active_connections:
            connection_info = self.active_connections[client_id]
            connection_info.remove_subscription(topic)
            self.topic_subscriptions[topic].discard(client_id)
            if not self.topic_subscriptions[topic]:
                del self.topic_subscriptions[topic]
            logger.info(f"Client {client_id} unsubscribed from topic: {topic}")
    
    async def _flush_message_buffer(self, client_id: str):
        """Flush the message buffer for a client"""
        if client_id not in self.active_connections or client_id not in self.message_buffers:
            return
        
        connection_info = self.active_connections[client_id]
        buffer = self.message_buffers[client_id]
        
        messages = buffer.flush()
        if messages:
            try:
                # Send batched messages
                batch_message = {
                    "type": "message_batch",
                    "messages": messages,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await connection_info.websocket.send_text(json.dumps(batch_message))
                connection_info.messages_sent += len(messages)
                self.total_messages_sent += len(messages)
                
            except Exception as e:
                logger.error(f"Error flushing message buffer for client {client_id}: {e}")
                await self.disconnect(client_id)
    
    async def _heartbeat_monitor(self):
        """Monitor connection health and send heartbeat pings"""
        while True:
            try:
                current_time = datetime.utcnow()
                disconnected_clients = []
                
                for client_id, connection_info in self.active_connections.items():
                    # Check for timed out connections
                    time_since_heartbeat = (current_time - connection_info.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.connection_timeout:
                        logger.warning(f"Connection {client_id} timed out")
                        disconnected_clients.append(client_id)
                    elif time_since_heartbeat > self.heartbeat_interval:
                        # Send heartbeat ping
                        try:
                            await connection_info.websocket.ping()
                            connection_info.update_heartbeat()
                        except Exception as e:
                            logger.error(f"Heartbeat failed for client {client_id}: {e}")
                            disconnected_clients.append(client_id)
                
                # Disconnect timed out clients
                for client_id in disconnected_clients:
                    await self.disconnect(client_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "authenticated_connections": sum(1 for conn in self.active_connections.values() if conn.is_authenticated),
            "total_connections": self.total_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "topic_subscriptions": {topic: len(clients) for topic, clients in self.topic_subscriptions.items()},
            "user_connections": {user_id: len(clients) for user_id, clients in self.user_connections.items()}
        }
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific client"""
        if client_id in self.active_connections:
            return self.active_connections[client_id].to_dict()
        return None