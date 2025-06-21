"""
WebSocket Connection Manager for TrackPro Backend
Handles WebSocket connections, authentication, and message broadcasting
"""
import asyncio
import json
import uuid
from typing import Dict, Set, Optional, Any, List
from datetime import datetime

from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class Connection:
    """Represents a WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, connection_id: str, user_id: Optional[str] = None):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.subscriptions: Set[str] = set()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary"""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "subscriptions": list(self.subscriptions)
        }

class ConnectionManager:
    """Manages WebSocket connections for the TrackPro backend"""
    
    def __init__(self):
        self.active_connections: Dict[str, Connection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.subscription_groups: Dict[str, Set[str]] = {}  # topic -> connection_ids
        self.ping_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the connection manager"""
        logger.info("Initializing Connection Manager")
        
        # Start ping task to keep connections alive
        self.ping_task = asyncio.create_task(self._ping_loop())
        
    async def shutdown(self):
        """Shutdown the connection manager"""
        logger.info("Shutting down Connection Manager")
        
        # Cancel ping task
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection in list(self.active_connections.values()):
            await self._disconnect_connection(connection)
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """Register a new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        connection = Connection(websocket, connection_id, user_id)
        
        self.active_connections[connection_id] = connection
        
        # Track user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"Connection registered: {connection_id} (user: {user_id})")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            await self._disconnect_connection(connection)
            
    async def _disconnect_connection(self, connection: Connection):
        """Internal method to disconnect a connection"""
        connection_id = connection.connection_id
        user_id = connection.user_id
        
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from subscription groups
        for topic, connections in self.subscription_groups.items():
            connections.discard(connection_id)
        
        # Clean up empty subscription groups
        empty_topics = [topic for topic, connections in self.subscription_groups.items() if not connections]
        for topic in empty_topics:
            del self.subscription_groups[topic]
        
        # Close WebSocket if still open
        try:
            await connection.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket for {connection_id}: {e}")
        
        logger.info(f"Connection disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific connection by ID"""
        if connection_id not in self.active_connections:
            return False
        
        connection = self.active_connections[connection_id]
        try:
            await connection.websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            # Connection is probably dead, remove it
            await self._disconnect_connection(connection)
            return False
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> int:
        """Send message to all connections for a specific user"""
        if user_id not in self.user_connections:
            return 0
        
        connection_ids = list(self.user_connections[user_id])
        sent_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all connected clients"""
        connection_ids = list(self.active_connections.keys())
        sent_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def subscribe(self, connection_id: str, topic: str) -> bool:
        """Subscribe a connection to a topic"""
        if connection_id not in self.active_connections:
            return False
        
        connection = self.active_connections[connection_id]
        connection.subscriptions.add(topic)
        
        if topic not in self.subscription_groups:
            self.subscription_groups[topic] = set()
        self.subscription_groups[topic].add(connection_id)
        
        logger.info(f"Connection {connection_id} subscribed to {topic}")
        return True
    
    async def unsubscribe(self, connection_id: str, topic: str) -> bool:
        """Unsubscribe a connection from a topic"""
        if connection_id not in self.active_connections:
            return False
        
        connection = self.active_connections[connection_id]
        connection.subscriptions.discard(topic)
        
        if topic in self.subscription_groups:
            self.subscription_groups[topic].discard(connection_id)
            if not self.subscription_groups[topic]:
                del self.subscription_groups[topic]
        
        logger.info(f"Connection {connection_id} unsubscribed from {topic}")
        return True
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all connections subscribed to a topic"""
        if topic not in self.subscription_groups:
            return 0
        
        connection_ids = list(self.subscription_groups[topic])
        sent_count = 0
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection"""
        if connection_id not in self.active_connections:
            return None
        
        return self.active_connections[connection_id].to_dict()
    
    def get_connections_for_user(self, user_id: str) -> List[str]:
        """Get all connection IDs for a specific user"""
        return list(self.user_connections.get(user_id, set()))
    
    def get_active_connections_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_topics(self) -> List[str]:
        """Get all active subscription topics"""
        return list(self.subscription_groups.keys())
    
    async def _ping_loop(self):
        """Background task to ping connections and remove dead ones"""
        while True:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                
                dead_connections = []
                
                for connection_id, connection in self.active_connections.items():
                    try:
                        # Send ping
                        await connection.websocket.ping()
                        connection.last_ping = datetime.utcnow()
                    except Exception as e:
                        logger.warning(f"Ping failed for connection {connection_id}: {e}")
                        dead_connections.append(connection)
                
                # Remove dead connections
                for connection in dead_connections:
                    await self._disconnect_connection(connection)
                
                if dead_connections:
                    logger.info(f"Removed {len(dead_connections)} dead connections")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")