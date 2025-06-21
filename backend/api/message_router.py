"""
TrackPro Message Router
Routes WebSocket messages to appropriate handlers based on message type
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Set
import traceback

logger = logging.getLogger(__name__)

class MessageHandler:
    """Base class for message handlers"""
    
    def __init__(self, handler_name: str):
        self.handler_name = handler_name
        self.handled_message_types: Set[str] = set()
    
    async def handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
        """Handle a message and return a response if needed"""
        raise NotImplementedError("Subclasses must implement handle_message")
    
    def can_handle(self, message_type: str) -> bool:
        """Check if this handler can handle the given message type"""
        return message_type in self.handled_message_types

class SystemMessageHandler(MessageHandler):
    """Handler for system-level messages"""
    
    def __init__(self):
        super().__init__("system")
        self.handled_message_types = {
            "ping", "heartbeat", "subscribe", "unsubscribe", 
            "get_connection_info", "get_server_stats"
        }
    
    async def handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
        """Handle system messages"""
        message_type = message.get("type")
        
        if message_type == "ping":
            return {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id
            }
        
        elif message_type == "heartbeat":
            return {
                "type": "heartbeat_ack",
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id
            }
        
        elif message_type == "subscribe":
            # Handle subscription requests
            topic = message.get("topic")
            if topic:
                # This would integrate with ConnectionManager
                return {
                    "type": "subscription_success",
                    "topic": topic,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        elif message_type == "unsubscribe":
            # Handle unsubscription requests
            topic = message.get("topic")
            if topic:
                return {
                    "type": "unsubscription_success",
                    "topic": topic,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return None

class AuthMessageHandler(MessageHandler):
    """Handler for authentication messages"""
    
    def __init__(self):
        super().__init__("auth")
        self.handled_message_types = {
            "authenticate", "login", "logout", "refresh_token", "register"
        }
    
    async def handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
        """Handle authentication messages"""
        message_type = message.get("type")
        
        if message_type == "authenticate":
            # Handle authentication
            token = message.get("token")
            if token:
                # TODO: Implement actual token validation
                return {
                    "type": "authentication_success",
                    "user_id": "placeholder_user_id",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "type": "authentication_error",
                    "message": "Invalid token",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        elif message_type == "login":
            # Handle login request
            username = message.get("username")
            password = message.get("password")
            
            if username and password:
                # TODO: Implement actual login logic
                return {
                    "type": "login_success",
                    "user_id": f"user_{username}",
                    "token": "placeholder_token",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "type": "login_error",
                    "message": "Invalid credentials",
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return None

class PedalMessageHandler(MessageHandler):
    """Handler for pedal-related messages"""
    
    def __init__(self):
        super().__init__("pedal")
        self.handled_message_types = {
            "get_pedal_data", "start_calibration", "stop_calibration",
            "save_profile", "load_profile", "get_hardware_info"
        }
    
    async def handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
        """Handle pedal messages"""
        message_type = message.get("type")
        
        if message_type == "get_pedal_data":
            # Return current pedal data
            return {
                "type": "pedal_data",
                "data": {
                    "throttle": 0.0,
                    "brake": 0.0,
                    "clutch": 0.0,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        elif message_type == "start_calibration":
            # Start calibration process
            pedal_type = message.get("pedal_type", "throttle")
            return {
                "type": "calibration_started",
                "pedal_type": pedal_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif message_type == "get_hardware_info":
            # Return hardware information
            return {
                "type": "hardware_info",
                "data": {
                    "detected_pedals": [],
                    "connected_devices": [],
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        return None

class TelemetryMessageHandler(MessageHandler):
    """Handler for telemetry and race coach messages"""
    
    def __init__(self):
        super().__init__("telemetry")
        self.handled_message_types = {
            "start_telemetry", "stop_telemetry", "get_session_data",
            "get_lap_data", "start_ai_coaching", "stop_ai_coaching"
        }
    
    async def handle_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
        """Handle telemetry messages"""
        message_type = message.get("type")
        
        if message_type == "start_telemetry":
            # Start telemetry streaming
            return {
                "type": "telemetry_started",
                "session_id": f"session_{datetime.utcnow().timestamp()}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif message_type == "get_session_data":
            # Return current session data
            return {
                "type": "session_data",
                "data": {
                    "session_id": "current_session",
                    "lap_count": 0,
                    "best_lap_time": None,
                    "current_lap_time": None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        
        return None

class MessageRouter:
    """Routes messages to appropriate handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {}
        self.message_type_map: Dict[str, str] = {}
        self.message_stats = {
            "total_messages": 0,
            "messages_by_type": {},
            "errors": 0,
            "last_reset": datetime.utcnow()
        }
        
        # Initialize default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default message handlers"""
        handlers = [
            SystemMessageHandler(),
            AuthMessageHandler(),
            PedalMessageHandler(),
            TelemetryMessageHandler()
        ]
        
        for handler in handlers:
            self.register_handler(handler)
    
    def register_handler(self, handler: MessageHandler):
        """Register a message handler"""
        self.handlers[handler.handler_name] = handler
        
        # Map message types to handler
        for message_type in handler.handled_message_types:
            self.message_type_map[message_type] = handler.handler_name
        
        logger.info(f"Registered handler: {handler.handler_name} for types: {handler.handled_message_types}")
    
    def unregister_handler(self, handler_name: str):
        """Unregister a message handler"""
        if handler_name in self.handlers:
            handler = self.handlers[handler_name]
            
            # Remove message type mappings
            for message_type in handler.handled_message_types:
                if message_type in self.message_type_map:
                    del self.message_type_map[message_type]
            
            # Remove handler
            del self.handlers[handler_name]
            logger.info(f"Unregistered handler: {handler_name}")
    
    async def route_message(self, message: Dict[str, Any], client_id: str) -> Optional[Dict[str, Any]]:
        """Route a message to the appropriate handler"""
        try:
            # Update statistics
            self.message_stats["total_messages"] += 1
            
            message_type = message.get("type")
            if not message_type:
                logger.warning(f"Message from client {client_id} missing 'type' field")
                return {
                    "type": "error",
                    "message": "Message must include 'type' field",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Update type statistics
            if message_type not in self.message_stats["messages_by_type"]:
                self.message_stats["messages_by_type"][message_type] = 0
            self.message_stats["messages_by_type"][message_type] += 1
            
            # Find appropriate handler
            if message_type not in self.message_type_map:
                logger.warning(f"No handler registered for message type: {message_type}")
                return {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            handler_name = self.message_type_map[message_type]
            handler = self.handlers[handler_name]
            
            # Route to handler
            logger.debug(f"Routing message type '{message_type}' to handler '{handler_name}' for client {client_id}")
            response = await handler.handle_message(message, client_id)
            
            return response
            
        except Exception as e:
            self.message_stats["errors"] += 1
            logger.error(f"Error routing message from client {client_id}: {e}")
            logger.error(traceback.format_exc())
            
            return {
                "type": "error",
                "message": "Internal server error while processing message",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about registered handlers"""
        return {
            "handlers": {
                name: {
                    "handler_name": handler.handler_name,
                    "handled_types": list(handler.handled_message_types)
                }
                for name, handler in self.handlers.items()
            },
            "message_type_map": self.message_type_map.copy(),
            "statistics": self.message_stats.copy()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get message routing statistics"""
        return self.message_stats.copy()
    
    def reset_statistics(self):
        """Reset message statistics"""
        self.message_stats = {
            "total_messages": 0,
            "messages_by_type": {},
            "errors": 0,
            "last_reset": datetime.utcnow()
        }