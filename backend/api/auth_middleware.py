"""
TrackPro Authentication Middleware
Handles authentication and authorization for WebSocket connections
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List
import jwt
import hashlib
import secrets

logger = logging.getLogger(__name__)

class AuthToken:
    """Represents an authentication token"""
    
    def __init__(self, user_id: str, token: str, expires_at: datetime):
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    def refresh_last_used(self):
        """Update last used timestamp"""
        self.last_used = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "token": self.token,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat()
        }

class AuthMiddleware:
    """Authentication middleware for WebSocket connections"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.token_expiry_hours = 24
        self.refresh_token_expiry_days = 30
        
        # Token storage (in production, use Redis or database)
        self.active_tokens: Dict[str, AuthToken] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        
        # Authentication stats
        self.auth_stats = {
            "total_authentications": 0,
            "successful_authentications": 0,
            "failed_authentications": 0,
            "active_sessions": 0,
            "token_refreshes": 0
        }
    
    def generate_token(self, user_id: str, user_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a JWT token for a user"""
        expires_at = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
        
        payload = {
            "user_id": user_id,
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if user_data:
            payload.update(user_data)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token
        auth_token = AuthToken(user_id, token, expires_at)
        self.active_tokens[token] = auth_token
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(token)
        
        self.auth_stats["total_authentications"] += 1
        self.auth_stats["successful_authentications"] += 1
        self.auth_stats["active_sessions"] = len(self.active_tokens)
        
        logger.info(f"Generated token for user {user_id}")
        return token
    
    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a refresh token"""
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expiry_days)
        
        payload = {
            "user_id": user_id,
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        refresh_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return refresh_token
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token and return user data"""
        try:
            # Check if token exists in active tokens
            if token not in self.active_tokens:
                logger.warning("Token not found in active tokens")
                self.auth_stats["failed_authentications"] += 1
                return None
            
            auth_token = self.active_tokens[token]
            
            # Check if token is expired
            if auth_token.is_expired():
                logger.warning(f"Token expired for user {auth_token.user_id}")
                await self.revoke_token(token)
                self.auth_stats["failed_authentications"] += 1
                return None
            
            # Decode JWT to get payload
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Update last used
            auth_token.refresh_last_used()
            
            logger.debug(f"Token validated for user {payload['user_id']}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token signature expired")
            await self.revoke_token(token)
            self.auth_stats["failed_authentications"] += 1
            return None
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            self.auth_stats["failed_authentications"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            self.auth_stats["failed_authentications"] += 1
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresh an access token using a refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh":
                logger.warning("Token is not a refresh token")
                return None
            
            user_id = payload["user_id"]
            new_token = self.generate_token(user_id)
            
            self.auth_stats["token_refreshes"] += 1
            logger.info(f"Token refreshed for user {user_id}")
            return new_token
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expired")
            return None
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None
    
    async def revoke_token(self, token: str):
        """Revoke a specific token"""
        if token in self.active_tokens:
            auth_token = self.active_tokens[token]
            user_id = auth_token.user_id
            
            # Remove from active tokens
            del self.active_tokens[token]
            
            # Remove from user sessions
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(token)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            
            self.auth_stats["active_sessions"] = len(self.active_tokens)
            logger.info(f"Token revoked for user {user_id}")
    
    async def revoke_user_tokens(self, user_id: str):
        """Revoke all tokens for a specific user"""
        if user_id in self.user_sessions:
            tokens_to_revoke = list(self.user_sessions[user_id])
            for token in tokens_to_revoke:
                await self.revoke_token(token)
            
            logger.info(f"All tokens revoked for user {user_id}")
    
    async def authenticate_connection(self, token: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Authenticate a WebSocket connection"""
        user_data = await self.validate_token(token)
        
        if user_data:
            logger.info(f"Connection {client_id} authenticated as user {user_data['user_id']}")
            return user_data
        else:
            logger.warning(f"Authentication failed for connection {client_id}")
            return None
    
    async def require_authentication(self, message: Dict[str, Any], client_id: str) -> bool:
        """Check if a message requires authentication"""
        # Define message types that require authentication
        protected_message_types = {
            "get_user_data", "save_user_data", "start_telemetry", 
            "save_profile", "load_profile", "get_lap_data",
            "start_ai_coaching", "get_community_data"
        }
        
        message_type = message.get("type", "")
        return message_type in protected_message_types
    
    async def authorize_action(self, user_id: str, action: str, resource: Optional[str] = None) -> bool:
        """Check if a user is authorized to perform an action"""
        # Basic authorization logic - expand as needed
        if not user_id:
            return False
        
        # Define action permissions
        user_permissions = {
            "read_own_data": True,
            "write_own_data": True,
            "read_telemetry": True,
            "write_telemetry": True,
            "manage_profiles": True,
            "use_ai_coaching": True,
            "access_community": True
        }
        
        return user_permissions.get(action, False)
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            **self.auth_stats,
            "active_sessions": len(self.active_tokens),
            "users_with_sessions": len(self.user_sessions)
        }
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        if user_id not in self.user_sessions:
            return []
        
        sessions = []
        for token in self.user_sessions[user_id]:
            if token in self.active_tokens:
                sessions.append(self.active_tokens[token].to_dict())
        
        return sessions
    
    async def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        current_time = datetime.utcnow()
        expired_tokens = []
        
        for token, auth_token in self.active_tokens.items():
            if auth_token.is_expired():
                expired_tokens.append(token)
        
        for token in expired_tokens:
            await self.revoke_token(token)
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
    
    async def start_cleanup_task(self):
        """Start periodic cleanup of expired tokens"""
        while True:
            try:
                await self.cleanup_expired_tokens()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Error in token cleanup task: {e}")
                await asyncio.sleep(3600)