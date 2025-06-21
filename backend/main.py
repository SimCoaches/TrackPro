"""
TrackPro Hybrid Backend - WebSocket Server
Main entry point for the Python backend with WebSocket API
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Set
import traceback

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api.connection_manager import ConnectionManager
from .api.message_router import MessageRouter
from .api.auth_middleware import AuthMiddleware
from .logging_config import setup_logging

# Initialize logging
logger = setup_logging(__name__)

# Create FastAPI app
app = FastAPI(
    title="TrackPro Backend API",
    description="WebSocket API for TrackPro hybrid application",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components
connection_manager = ConnectionManager()
message_router = MessageRouter()
auth_middleware = AuthMiddleware()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for all client connections"""
    client_id = None
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Register the client
        client_id = await connection_manager.connect(websocket)
        logger.info(f"Client {client_id} connected")
        
        # Send welcome message
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "server_version": "1.0.0"
        }, client_id)
        
        # Main message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Add client context to message
                message["client_id"] = client_id
                message["timestamp"] = datetime.utcnow().isoformat()
                
                # Route the message
                response = await message_router.route_message(message, client_id)
                
                # Send response if provided
                if response:
                    await connection_manager.send_personal_message(response, client_id)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client {client_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }, client_id)
                
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")
                logger.error(traceback.format_exc())
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }, client_id)
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        logger.error(traceback.format_exc())
    finally:
        if client_id:
            await connection_manager.disconnect(client_id)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": len(connection_manager.active_connections),
        "version": "1.0.0"
    }

@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    return {
        "active_connections": len(connection_manager.active_connections),
        "total_messages_sent": connection_manager.total_messages_sent,
        "total_messages_received": connection_manager.total_messages_received,
        "uptime": (datetime.utcnow() - connection_manager.start_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
        log_level="info"
    )