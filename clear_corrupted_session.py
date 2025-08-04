#!/usr/bin/env python3
"""
Script to clear corrupted session data that's causing Supabase authentication issues.
"""

import os
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_corrupted_session():
    """Clear corrupted session data."""
    try:
        # Get the user's home directory
        home_dir = Path.home()
        
        # Look for session files in common locations
        session_locations = [
            home_dir / "Documents" / "TrackPro" / "auth_session.json",
            home_dir / ".trackpro" / "auth_session.json",
            Path.cwd() / "auth_session.json"
        ]
        
        cleared_count = 0
        
        for session_file in session_locations:
            if session_file.exists():
                try:
                    # Read the session data
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Check if the access token is corrupted
                    access_token = session_data.get('access_token', '')
                    if isinstance(access_token, str) and ('+00:00' in access_token or len(access_token) < 50):
                        logger.info(f"Found corrupted session at: {session_file}")
                        
                        # Backup the corrupted file
                        backup_file = session_file.with_suffix('.json.corrupted')
                        session_file.rename(backup_file)
                        logger.info(f"Backed up corrupted session to: {backup_file}")
                        
                        cleared_count += 1
                    else:
                        logger.info(f"Session at {session_file} appears to be valid")
                        
                except Exception as e:
                    logger.warning(f"Error processing {session_file}: {e}")
        
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} corrupted session file(s)")
            logger.info("You will need to re-authenticate when you next start TrackPro")
        else:
            logger.info("No corrupted session files found")
            
    except Exception as e:
        logger.error(f"Error clearing corrupted sessions: {e}")

if __name__ == "__main__":
    clear_corrupted_session() 