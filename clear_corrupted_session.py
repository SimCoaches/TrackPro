#!/usr/bin/env python
"""
Clear corrupted authentication session
"""

import sys
import os
import logging
import json

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_corrupted_session():
    """Clear the corrupted authentication session."""
    
    try:
        # Path to the auth file
        auth_file = os.path.expanduser("~/.trackpro/auth.json")
        
        if os.path.exists(auth_file):
            logger.info(f"Found auth file at: {auth_file}")
            
            # Read the current auth data
            with open(auth_file, 'r') as f:
                auth_data = json.load(f)
            
            logger.info(f"Current auth data: {auth_data}")
            
            # Clear the auth data
            auth_data = {
                "access_token": None,
                "refresh_token": None,
                "remember_me": False
            }
            
            # Write the cleared auth data
            with open(auth_file, 'w') as f:
                json.dump(auth_data, f, indent=2)
            
            logger.info("✅ Cleared corrupted authentication session")
            logger.info("You will need to log in again when you start TrackPro")
            
        else:
            logger.info("No auth file found - session already cleared")
        
        return True
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    clear_corrupted_session() 