"""
Supabase Client Module

This module initializes the Supabase client using credentials from the .env file.
It provides a singleton instance of the client to be used across the application.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client (singleton)
_supabase_client = None

def get_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Client: The Supabase client instance.
    """
    global _supabase_client
    
    # Get Supabase credentials from environment variables
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # Check if credentials are available
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials not found in .env file. Please ensure SUPABASE_URL and SUPABASE_KEY are set.")
        return None
    
    # Initialize client if not already initialized or if credentials have changed
    if (_supabase_client is None or 
        _supabase_client.supabase_url != SUPABASE_URL or 
        _supabase_client.supabase_key != SUPABASE_KEY):
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info(f"Supabase client initialized with URL: {SUPABASE_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None
            
    return _supabase_client

# Export the client instance
supabase = get_client() 