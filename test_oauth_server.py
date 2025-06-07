#!/usr/bin/env python3
"""
Test script to verify OAuth server setup works correctly.
This tests the new dynamic port allocation and error handling.
"""

import sys
import os
import socket
import time
import threading
import logging

# Add the trackpro directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_port_availability():
    """Test if we can detect port availability correctly."""
    logger.info("Testing port availability detection...")
    
    # Test with a port that should be available
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 8888))
        sock.close()
        logger.info("✓ Port 8888 is available")
    except socket.error as e:
        logger.error(f"✗ Port 8888 unavailable: {e}")
    
    # Test with a port that's likely in use (if any)
    for test_port in [80, 443, 3000]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', test_port))
            sock.close()
            logger.info(f"✓ Port {test_port} is available")
        except socket.error:
            logger.info(f"✓ Port {test_port} is in use (as expected)")

def test_oauth_handler_setup():
    """Test the OAuth handler setup with our improvements."""
    logger.info("Testing OAuth handler setup...")
    
    try:
        from auth.oauth_handler import OAuthHandler
        
        # Create OAuth handler
        oauth_handler = OAuthHandler()
        logger.info("✓ OAuth handler created successfully")
        
        # Test callback server setup on default port
        try:
            server = oauth_handler.setup_callback_server(port=3000)
            if server:
                logger.info(f"✓ OAuth callback server started on port {oauth_handler.oauth_port}")
                # Test that the port is stored correctly
                if hasattr(oauth_handler, 'oauth_port') and oauth_handler.oauth_port == 3000:
                    logger.info("✓ OAuth port stored correctly")
                else:
                    logger.error("✗ OAuth port not stored correctly")
                
                # Shutdown the server
                oauth_handler.shutdown_callback_server(server)
                logger.info("✓ OAuth server shutdown successfully")
            else:
                logger.error("✗ OAuth callback server failed to start")
                
        except Exception as e:
            logger.error(f"✗ Error setting up OAuth callback server: {e}")
            
    except ImportError as e:
        logger.error(f"✗ Failed to import OAuth handler: {e}")
    except Exception as e:
        logger.error(f"✗ Unexpected error in OAuth handler test: {e}")

def test_port_conflict_handling():
    """Test how the system handles port conflicts."""
    logger.info("Testing port conflict handling...")
    
    # Create a dummy server on port 3000 to simulate a conflict
    try:
        dummy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        dummy_server.bind(('127.0.0.1', 3000))
        dummy_server.listen(1)
        logger.info("✓ Created dummy server on port 3000 to simulate conflict")
        
        try:
            from auth.oauth_handler import OAuthHandler
            
            # Try to create OAuth handler - should use alternative port
            oauth_handler = OAuthHandler()
            
            # Simulate the port checking logic from main.py
            port_available = False
            oauth_port = 3000
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', 3000))
                sock.close()
                logger.info("Port 3000 is available")
                port_available = True
            except socket.error:
                logger.info("Port 3000 is in use, trying alternatives...")
                # Try alternative ports
                for alt_port in [3001, 3002, 3003, 8080, 8081]:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.bind(('127.0.0.1', alt_port))
                        sock.close()
                        logger.info(f"✓ Using alternative port {alt_port}")
                        oauth_port = alt_port
                        port_available = True
                        break
                    except socket.error:
                        continue
            
            if port_available:
                # Test server setup on alternative port
                server = oauth_handler.setup_callback_server(port=oauth_port)
                if server:
                    logger.info(f"✓ OAuth server started successfully on alternative port {oauth_port}")
                    oauth_handler.shutdown_callback_server(server)
                else:
                    logger.error("✗ OAuth server failed to start on alternative port")
            else:
                logger.error("✗ No alternative ports available")
                
        except ImportError as e:
            logger.error(f"✗ Failed to import OAuth handler: {e}")
        except Exception as e:
            logger.error(f"✗ Error in port conflict test: {e}")
        finally:
            # Clean up dummy server
            dummy_server.close()
            logger.info("✓ Cleaned up dummy server")
            
    except Exception as e:
        logger.error(f"✗ Failed to create dummy server: {e}")

def main():
    """Run all OAuth server tests."""
    logger.info("=" * 50)
    logger.info("TrackPro OAuth Server Test Suite")
    logger.info("=" * 50)
    
    test_port_availability()
    logger.info("-" * 30)
    
    test_oauth_handler_setup()
    logger.info("-" * 30)
    
    test_port_conflict_handling()
    logger.info("-" * 30)
    
    logger.info("OAuth server tests completed!")

if __name__ == "__main__":
    main() 