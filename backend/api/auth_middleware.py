"""
Authentication Middleware for TrackPro Backend
Handles JWT token verification and user authentication
"""
import sys
import os
from typing import Optional
from datetime import datetime, timedelta
import logging

# Add trackpro to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "trackpro"))

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

class AuthenticationError(Exception):
    """Authentication related errors"""
    pass

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise AuthenticationError("Invalid token")

async def get_current_user_from_token(token: str) -> Optional[str]:
    """Get current user ID from JWT token"""
    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Token missing user ID")
            
        return user_id
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        raise AuthenticationError("Token validation error")

async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate a user with username/password"""
    try:
        # Import here to avoid circular imports
        from auth.user_manager import UserManager
        
        user_manager = UserManager()
        user = await user_manager.get_user_by_username(username)
        
        if not user:
            return None
            
        if not verify_password(password, user.get("password_hash", "")):
            return None
            
        return user
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

async def create_user_session(user_id: str) -> dict:
    """Create a new user session with JWT token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_id": user_id
    }

def extract_token_from_header(authorization: str) -> Optional[str]:
    """Extract JWT token from Authorization header"""
    if not authorization:
        return None
        
    if not authorization.startswith("Bearer "):
        return None
        
    return authorization[7:]  # Remove "Bearer " prefix

async def verify_websocket_token(token: Optional[str]) -> Optional[str]:
    """Verify WebSocket authentication token and return user ID"""
    if not token:
        return None
        
    try:
        return await get_current_user_from_token(token)
    except AuthenticationError:
        return None

# FastAPI dependency for HTTP endpoints
async def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> str:
    """FastAPI dependency to get current authenticated user"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        user_id = await get_current_user_from_token(credentials.credentials)
        if user_id is None:
            raise credentials_exception
        return user_id
        
    except AuthenticationError:
        raise credentials_exception

# Optional authentication dependency
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[str]:
    """FastAPI dependency to get current user (optional)"""
    if not credentials:
        return None
        
    try:
        return await get_current_user_from_token(credentials.credentials)
    except AuthenticationError:
        return None