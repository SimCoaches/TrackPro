"""
TrackPro Hybrid Backend API Server
Main entry point for the FastAPI + WebSocket server
"""
import sys
import os
import json
import asyncio
from typing import Dict, Set, Optional, Any
from datetime import datetime

# Add trackpro to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "trackpro"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import logging

from config import settings
from logging_config import setup_logging, get_logger
from api.connection_manager import ConnectionManager
from api.message_router import MessageRouter, MessageType
from api.auth_middleware import verify_token
from api import (
    pedals_api,
    race_coach_api, 
    auth_api,
    gamification_api,
    community_api,
    database_api
)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TrackPro Hybrid API",
    description="WebSocket API server for TrackPro desktop application",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize connection manager and message router
connection_manager = ConnectionManager()
message_router = MessageRouter()

# Security
security = HTTPBearer()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting TrackPro Backend API Server...")
    
    # Initialize background services
    await connection_manager.initialize()
    await message_router.initialize()
    
    logger.info(f"Server started on {settings.HOST}:{settings.PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down TrackPro Backend API Server...")
    
    await connection_manager.shutdown()
    await message_router.shutdown()
    
    logger.info("Server shutdown complete")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "TrackPro Backend API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "connections": len(connection_manager.active_connections),
        "uptime": "TODO: implement uptime tracking",
        "memory_usage": "TODO: implement memory tracking"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Main WebSocket endpoint for real-time communication"""
    
    # Accept connection first
    await websocket.accept()
    
    try:
        # Authenticate connection if token provided
        user_id = None
        if token:
            try:
                user_id = await verify_token(token)
                logger.info(f"Authenticated WebSocket connection for user {user_id}")
            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {e}")
                await websocket.close(code=1008, reason="Authentication failed")
                return
        
        # Register connection
        connection_id = await connection_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Send welcome message
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
        # Message handling loop
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Route message through message router
                response = await message_router.route_message(
                    message, connection_id, user_id
                )
                
                # Send response if any
                if response:
                    await connection_manager.send_personal_message(
                        response, websocket
                    )
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {connection_id}: {data}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
                
            except Exception as e:
                logger.error(f"Error processing message from {connection_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error", 
                    "message": f"Server error: {str(e)}"
                }, websocket)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id if 'connection_id' in locals() else 'unknown'}")
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        
    finally:
        # Ensure cleanup
        if 'connection_id' in locals():
            await connection_manager.disconnect(connection_id)

# Include API routers
app.include_router(auth_api.router, prefix="/api/auth", tags=["authentication"])
app.include_router(pedals_api.router, prefix="/api/pedals", tags=["pedals"])
app.include_router(race_coach_api.router, prefix="/api/race-coach", tags=["race-coach"])
app.include_router(gamification_api.router, prefix="/api/gamification", tags=["gamification"])
app.include_router(community_api.router, prefix="/api/community", tags=["community"])
app.include_router(database_api.router, prefix="/api/database", tags=["database"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )