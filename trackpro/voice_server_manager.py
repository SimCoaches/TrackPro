"""
Voice Server Manager

Automatically starts and manages the simple voice chat server.
"""

import asyncio
import threading
import logging
import subprocess
import sys
import os
import socket
import time
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
        self._startup_attempted = False  # Prevent duplicate startup attempts
        self._startup_lock = threading.Lock()  # Thread safety for startup
        
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return False
    
    def _find_available_port(self, start_port: int = 8080, max_attempts: int = 10) -> int:
        """Find an available port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            if self._is_port_available(port):
                return port
        return start_port  # Fallback to original port
    
    def start_server(self):
        """Start the voice chat server in a separate process (on-demand)."""
        with self._startup_lock:
            # Prevent duplicate startup attempts
            if self._startup_attempted:
                logger.info("Voice server startup already attempted, skipping")
                return
            
            if self.is_running:
                logger.info("Voice server is already running")
                return
            
            self._startup_attempted = True
            
        try:
            logger.info("Starting network voice server on-demand...")
            
            # Check if port is already in use
            if not self._is_port_available(self.server_port):
                logger.warning(f"Port {self.server_port} is already in use, attempting to find alternative")
                new_port = self._find_available_port(self.server_port + 1)
                if new_port != self.server_port:
                    self.server_port = new_port
                    logger.info(f"Using alternative port: {self.server_port}")
                else:
                    logger.error("No available ports found for voice server")
                    self.server_error.emit("No available ports found for voice server")
                    return
            
            # Get the path to the network voice server script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            server_script = os.path.join(current_dir, "network_voice_server.py")
            
            if not os.path.exists(server_script):
                logger.error(f"Network voice server script not found: {server_script}")
                self.server_error.emit("Network voice server script not found")
                return
            
            # Start the server process with port as environment variable
            logger.info("Launching network voice server process...")
            env = os.environ.copy()
            env['VOICE_SERVER_PORT'] = str(self.server_port)
            
            self.server_process = subprocess.Popen([
                sys.executable, server_script
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            
            # Wait for the process to start and initialize
            logger.info("Waiting for network voice server to initialize...")
            time.sleep(2.0)  # Reduced wait time
            
            # Check if process started successfully
            if self.server_process.poll() is not None:
                # Process terminated immediately
                stdout, stderr = self.server_process.communicate()
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Network voice server startup error: {error_msg}")
                raise Exception(f"Network voice server failed to start: {error_msg}")
            
            # Verify server is responding
            if self._verify_server_running():
                self.is_running = True
                logger.info(f"Network voice chat server started successfully on port {self.server_port}")
                self.server_started.emit()
                
                # Start monitoring thread
                self.server_thread = threading.Thread(target=self._monitor_server, daemon=True)
                self.server_thread.start()
            else:
                raise Exception("Voice server failed to respond after startup")
            
        except Exception as e:
            logger.error(f"Failed to start voice server on-demand: {e}")
            self.server_error.emit(f"Failed to start voice server on-demand: {str(e)}")
            self._startup_attempted = False  # Allow retry on failure
    
    def _verify_server_running(self) -> bool:
        """Verify that the voice server is responding."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('localhost', self.server_port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.warning(f"Could not verify network voice server status: {e}")
            return False
    
    def stop_server(self):
        """Stop the voice chat server."""
        try:
            if self.server_process:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    self.server_process.wait()
                self.server_process = None
            
            self.is_running = False
            self._startup_attempted = False  # Reset for next startup
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
_voice_server_lock = threading.Lock()

def get_voice_server_manager() -> VoiceServerManager:
    """Get the global voice server manager instance."""
    global _voice_server_manager
    with _voice_server_lock:
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