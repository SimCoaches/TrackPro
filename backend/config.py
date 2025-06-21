"""
Backend configuration for TrackPro Hybrid API Server
"""
import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Server Configuration
    HOST: str = "localhost"
    PORT: int = 8000
    DEBUG: bool = True
    
    # WebSocket Configuration
    WS_PING_INTERVAL: int = 30
    WS_PING_TIMEOUT: int = 10
    WS_MAX_CONNECTIONS: int = 100
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite:///./race_coach.db"
    
    # TrackPro Module Paths
    TRACKPRO_ROOT: str = "../trackpro"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "backend.log"
    
    # CORS Origins
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "app://localhost",        # Electron app
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()