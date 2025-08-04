"""
Voice Server Manager

Automatically starts and manages the high-quality voice chat server.
"""

import asyncio
import threading
import logging
import subprocess
import sys
import os
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class VoiceServerManager(QObject):
    """Manages the voice chat server process."""
    
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    server_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.server_process = None
        self.server_thread = None
        self.is_running = False
        self.server_port = 8080
        
    def start_server(self):
        """Start the voice chat server in a separate process."""
        try:
            # Get the path to the voice server script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            server_script = os.path.join(current_dir, "high_quality_voice_server.py")
            
            if not os.path.exists(server_script):
                logger.error(f"Voice server script not found: {server_script}")
                self.server_error.emit("Voice server script not found")
                return
            
            # Start the server process
            self.server_process = subprocess.Popen([
                sys.executable, server_script
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.is_running = True
            logger.info("Voice chat server started successfully")
            self.server_started.emit()
            
            # Start monitoring thread
            self.server_thread = threading.Thread(target=self._monitor_server, daemon=True)
            self.server_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start voice server: {e}")
            self.server_error.emit(f"Failed to start voice server: {str(e)}")
    
    def stop_server(self):
        """Stop the voice chat server."""
        try:
            if self.server_process:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.server_process = None
            
            self.is_running = False
            logger.info("Voice chat server stopped")
            self.server_stopped.emit()
            
        except Exception as e:
            logger.error(f"Failed to stop voice server: {e}")
            self.server_error.emit(f"Failed to stop voice server: {str(e)}")
    
    def _monitor_server(self):
        """Monitor the server process and handle output."""
        try:
            while self.is_running and self.server_process:
                # Check if process is still running
                if self.server_process.poll() is not None:
                    logger.warning("Voice server process terminated unexpectedly")
                    self.is_running = False
                    self.server_error.emit("Voice server process terminated unexpectedly")
                    break
                
                # Read output (non-blocking)
                try:
                    stdout = self.server_process.stdout.readline()
                    if stdout:
                        logger.info(f"Voice server: {stdout.decode().strip()}")
                except:
                    pass
                
                try:
                    stderr = self.server_process.stderr.readline()
                    if stderr:
                        logger.error(f"Voice server error: {stderr.decode().strip()}")
                except:
                    pass
                
                # Sleep to prevent busy waiting
                import time
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error monitoring voice server: {e}")
    
    def is_server_running(self) -> bool:
        """Check if the voice server is running."""
        if self.server_process:
            return self.server_process.poll() is None
        return False
    
    def get_server_url(self) -> str:
        """Get the voice server WebSocket URL."""
        return f"ws://localhost:{self.server_port}"
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop_server()


# Global voice server manager instance
_voice_server_manager = None

def get_voice_server_manager() -> VoiceServerManager:
    """Get the global voice server manager instance."""
    global _voice_server_manager
    if _voice_server_manager is None:
        _voice_server_manager = VoiceServerManager()
    return _voice_server_manager

def start_voice_server():
    """Start the voice chat server."""
    manager = get_voice_server_manager()
    manager.start_server()
    return manager

def stop_voice_server():
    """Stop the voice chat server."""
    manager = get_voice_server_manager()
    manager.stop_server()

def is_voice_server_running() -> bool:
    """Check if the voice server is running."""
    manager = get_voice_server_manager()
    return manager.is_server_running() 