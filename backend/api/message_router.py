"""
Message Router for TrackPro Backend
Routes WebSocket messages to appropriate handlers with type safety
"""
import asyncio
import json
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """Supported message types"""
    # Connection management
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_REFRESH = "auth.refresh"
    
    # Pedals
    PEDALS_GET_STATUS = "pedals.get_status"
    PEDALS_CALIBRATE = "pedals.calibrate"
    PEDALS_SAVE_PROFILE = "pedals.save_profile"
    PEDALS_LOAD_PROFILE = "pedals.load_profile"
    PEDALS_STREAM_DATA = "pedals.stream_data"
    
    # Race Coach
    RACE_COACH_START_SESSION = "race_coach.start_session"
    RACE_COACH_STOP_SESSION = "race_coach.stop_session"
    RACE_COACH_GET_TELEMETRY = "race_coach.get_telemetry"
    RACE_COACH_AI_COACH = "race_coach.ai_coach"
    
    # Gamification
    GAMIFICATION_GET_XP = "gamification.get_xp"
    GAMIFICATION_GET_QUESTS = "gamification.get_quests"
    GAMIFICATION_CLAIM_REWARD = "gamification.claim_reward"
    
    # Community
    COMMUNITY_GET_FEED = "community.get_feed"
    COMMUNITY_POST_MESSAGE = "community.post_message"
    COMMUNITY_GET_LEADERBOARD = "community.get_leaderboard"
    
    # Database
    DATABASE_GET_SETTINGS = "database.get_settings"
    DATABASE_SET_SETTING = "database.set_setting"
    DATABASE_GET_USER_DATA = "database.get_user_data"

class MessageHandler:
    """Base class for message handlers"""
    
    def __init__(self, handler_func: Callable[[Dict[str, Any], str, Optional[str]], Awaitable[Optional[Dict[str, Any]]]]):
        self.handler_func = handler_func
        
    async def handle(self, message: Dict[str, Any], connection_id: str, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Handle the message"""
        try:
            return await self.handler_func(message, connection_id, user_id)
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            return {
                "type": "error",
                "message": f"Handler error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

class MessageRouter:
    """Routes WebSocket messages to appropriate handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {}
        self.default_handler: Optional[MessageHandler] = None
        
    async def initialize(self):
        """Initialize the message router"""
        logger.info("Initializing Message Router")
        
        # Register built-in handlers
        await self._register_builtin_handlers()
        
    async def shutdown(self):
        """Shutdown the message router"""
        logger.info("Shutting down Message Router")
        self.handlers.clear()
        
    def register_handler(self, message_type: str, handler_func: Callable[[Dict[str, Any], str, Optional[str]], Awaitable[Optional[Dict[str, Any]]]]):
        """Register a handler for a specific message type"""
        self.handlers[message_type] = MessageHandler(handler_func)
        logger.info(f"Registered handler for message type: {message_type}")
        
    def set_default_handler(self, handler_func: Callable[[Dict[str, Any], str, Optional[str]], Awaitable[Optional[Dict[str, Any]]]]):
        """Set the default handler for unknown message types"""
        self.default_handler = MessageHandler(handler_func)
        logger.info("Set default message handler")
        
    async def route_message(self, message: Dict[str, Any], connection_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Route a message to the appropriate handler"""
        
        # Validate message format
        if not isinstance(message, dict):
            return {
                "type": "error",
                "message": "Message must be a JSON object",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        message_type = message.get("type")
        if not message_type:
            return {
                "type": "error", 
                "message": "Message must have a 'type' field",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        logger.debug(f"Routing message type '{message_type}' from connection {connection_id}")
        
        # Find handler
        handler = self.handlers.get(message_type)
        if not handler:
            handler = self.default_handler
            
        if not handler:
            return {
                "type": "error",
                "message": f"No handler registered for message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Execute handler
        try:
            response = await handler.handle(message, connection_id, user_id)
            
            # Add metadata to response if it exists
            if response and isinstance(response, dict):
                response.setdefault("timestamp", datetime.utcnow().isoformat())
                response.setdefault("request_id", message.get("request_id"))
                
            return response
            
        except Exception as e:
            logger.error(f"Error routing message '{message_type}': {e}")
            return {
                "type": "error",
                "message": f"Routing error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _register_builtin_handlers(self):
        """Register built-in message handlers"""
        
        # Connection management handlers
        self.register_handler(MessageType.PING, self._handle_ping)
        self.register_handler(MessageType.SUBSCRIBE, self._handle_subscribe)
        self.register_handler(MessageType.UNSUBSCRIBE, self._handle_unsubscribe)
        
        # Set default handler
        self.set_default_handler(self._handle_unknown)
        
    async def _handle_ping(self, message: Dict[str, Any], connection_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle ping messages"""
        return {
            "type": MessageType.PONG,
            "message": "pong",
            "connection_id": connection_id
        }
        
    async def _handle_subscribe(self, message: Dict[str, Any], connection_id: str, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Handle subscription requests"""
        topic = message.get("topic")
        if not topic:
            return {
                "type": "error",
                "message": "Subscribe message must include 'topic' field"
            }
            
        # TODO: Implement subscription logic with connection manager
        # This will be connected when we wire everything together
        logger.info(f"Connection {connection_id} wants to subscribe to {topic}")
        
        return {
            "type": "subscription_confirmed",
            "topic": topic,
            "message": f"Subscribed to {topic}"
        }
        
    async def _handle_unsubscribe(self, message: Dict[str, Any], connection_id: str, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Handle unsubscription requests"""
        topic = message.get("topic")
        if not topic:
            return {
                "type": "error",
                "message": "Unsubscribe message must include 'topic' field"
            }
            
        # TODO: Implement unsubscription logic with connection manager
        logger.info(f"Connection {connection_id} wants to unsubscribe from {topic}")
        
        return {
            "type": "unsubscription_confirmed",
            "topic": topic,
            "message": f"Unsubscribed from {topic}"
        }
        
    async def _handle_unknown(self, message: Dict[str, Any], connection_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        """Handle unknown message types"""
        message_type = message.get("type", "unknown")
        logger.warning(f"Unknown message type '{message_type}' from connection {connection_id}")
        
        return {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "supported_types": list(self.handlers.keys())
        }