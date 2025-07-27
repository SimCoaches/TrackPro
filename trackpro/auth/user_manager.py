"""
User management module for TrackPro.

Provides functions to get and manage the current user.
"""

import logging
import uuid
from dataclasses import dataclass

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class User:
    """Simple user class to store user information."""
    id: str
    email: str = None
    name: str = None
    is_authenticated: bool = False

# Global variable to store the current user
_current_user = None

def get_current_user():
    """Get the currently logged-in user or create a dummy user if none exists.
    
    Returns:
        User: The current user object, or None if no user is logged in.
    """
    global _current_user
    
    if _current_user is None:
        # Check if we can get the user from Supabase
        try:
            from ..database.supabase_client import get_supabase_client
            client = get_supabase_client()
            if client and hasattr(client, 'auth') and client.auth.get_session():
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    user_data = session.user
                    _current_user = User(
                        id=user_data.id,
                        email=user_data.email,
                        name=user_data.user_metadata.get('name', user_data.email),
                        is_authenticated=True
                    )
                    logger.info(f"Found authenticated user from Supabase: {_current_user.email}")
                    return _current_user
        except Exception as e:
            logger.warning(f"Error getting user from Supabase: {e}")
        
        # If no user is found, create a dummy user with a temporary ID
        temp_id = str(uuid.uuid4())
        _current_user = User(
            id=temp_id,
            email="anonymous@trackpro.local",
            name="Anonymous User",
            is_authenticated=False
        )
        logger.warning(f"Created anonymous user with temporary ID: {temp_id}")
    
    return _current_user

def set_current_user(user):
    """Set the current user.
    
    Args:
        user (User): The user to set as current.
    """
    global _current_user
    _current_user = user
    logger.info(f"Set current user: {user.email if user else None}")

def logout_current_user():
    """Log out the current user."""
    global _current_user
    _current_user = None
    logger.info("Logged out current user")

    try:
        from ..database.supabase_client import get_supabase_client
        client = get_supabase_client()
        if client and hasattr(client, 'auth'):
            # For explicit logout actions, force clear the session regardless of remember_me setting
            # But give users the option to preserve credentials if they want
            client.sign_out(force_clear=True, respect_remember_me=False)
            logger.info("Signed out from Supabase (forced clear for explicit logout)")
    except Exception as e:
        logger.warning(f"Error signing out from Supabase: {e}") 