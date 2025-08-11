"""
User management module for TrackPro.

Provides functions to get and manage the current user.
"""

import logging
import threading
import uuid
from dataclasses import dataclass
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class User:
    """Simple user class to store user information."""
    id: str
    email: str = None
    name: str = None
    is_authenticated: bool = False
    hierarchy_level: str = "PADDOCK"
    is_dev: bool = False
    is_moderator: bool = False

# Global variable to store the current user
_current_user = None

def get_current_user():
    """Get the currently logged-in user or create a dummy user if none exists.
    
    Returns:
        User: The current user object, or None if no user is logged in.
    """
    global _current_user
    
    if _current_user is None:
        # During startup, don't perform authentication checks that could hang
        # This prevents the splash screen from freezing on "Setting up authentication system..."
        try:
            # First, require that a saved session exists to trust any auth state
            # This prevents stale in-memory sessions from re-authenticating after logout
            from ..database.supabase_client import supabase as supabase_manager, get_supabase_client
            try:
                if not supabase_manager.is_authenticated():
                    return None
            except Exception:
                # If we cannot verify, be conservative and treat as not authenticated
                return None

            client = get_supabase_client()
            if client and hasattr(client, 'auth') and client.auth.get_session():
                session = client.auth.get_session()
                if session and hasattr(session, 'user'):
                    user_data = session.user
                    
                    # Create user without hierarchy check during startup to prevent hanging
                    _current_user = User(
                        id=user_data.id,
                        email=user_data.email,
                        name=user_data.user_metadata.get('name', user_data.email),
                        is_authenticated=True,
                        hierarchy_level='PADDOCK',  # Default during startup
                        is_dev=False,  # Default during startup
                        is_moderator=False  # Default during startup
                    )
                    # Hardcode top-level privileges for Lawrence regardless of DB state
                    try:
                        if (_current_user.email or '').lower() == 'lawrence@simcoaches.com':
                            _current_user.hierarchy_level = 'TEAM'
                            _current_user.is_dev = True
                            _current_user.is_moderator = True
                    except Exception:
                        pass
                    logger.info(f"Found authenticated user from Supabase: {_current_user.email} (using default hierarchy during startup)")

                    # Schedule a background hierarchy refresh to avoid UI thread hangs
                    try:
                        threading.Thread(target=_update_user_hierarchy_async, daemon=True).start()
                    except Exception as e:
                        logger.warning(f"Failed to schedule hierarchy update: {e}")

                    return _current_user
        except Exception as e:
            logger.warning(f"Error getting user from Supabase: {e}")
        
        # Don't create anonymous user during startup - return None instead
        # This prevents early authentication checks that slow down startup
        return None
    
    return _current_user

def _update_user_hierarchy_async():
    """Update user hierarchy information asynchronously after startup."""
    global _current_user
    
    if _current_user and _current_user.is_authenticated:
        try:
            # Get hierarchy information
            hierarchy_info = _get_user_hierarchy_info(_current_user.id)
            
            # Update user with correct hierarchy
            _current_user.hierarchy_level = hierarchy_info.get('hierarchy_level', 'PADDOCK')
            _current_user.is_dev = hierarchy_info.get('is_dev', False)
            _current_user.is_moderator = hierarchy_info.get('is_moderator', False)
            
            logger.info(f"Updated user hierarchy: {_current_user.email} (Level: {_current_user.hierarchy_level})")
        except Exception as e:
            logger.warning(f"Error updating user hierarchy: {e}")

def _get_user_hierarchy_info(user_id: str) -> dict:
    """Get user hierarchy information from database.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with hierarchy information
    """
    try:
        from .hierarchy_manager import hierarchy_manager
        hierarchy = hierarchy_manager.get_user_hierarchy(user_id)
        
        if hierarchy:
            return {
                'hierarchy_level': hierarchy.hierarchy_level.value,
                'is_dev': hierarchy.is_dev,
                'is_moderator': hierarchy.is_moderator
            }
        
        return {
            'hierarchy_level': 'PADDOCK',
            'is_dev': False,
            'is_moderator': False
        }
        
    except Exception as e:
        logger.warning(f"Error getting user hierarchy info: {e}")
        return {
            'hierarchy_level': 'PADDOCK',
            'is_dev': False,
            'is_moderator': False
        }

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
        # Use the Supabase manager to ensure proper sign-out and session clearing
        from ..database.supabase_client import supabase as supabase_manager
        # For explicit logout actions, force clear the session regardless of remember_me setting
        supabase_manager.sign_out(force_clear=True, respect_remember_me=False)
        logger.info("Signed out from Supabase (forced clear for explicit logout)")
    except Exception as e:
        logger.warning(f"Error signing out from Supabase: {e}")

def is_current_user_dev() -> bool:
    """Check if the current user has dev permissions.
    
    Returns:
        True if current user is a dev, False otherwise
    """
    user = get_current_user()
    if not user:
        return False
    
    try:
        from .hierarchy_manager import hierarchy_manager
        return hierarchy_manager.is_user_dev(user.id, user.email)
    except Exception as e:
        logger.warning(f"Error checking dev status: {e}")
        return user.is_dev if user else False

def is_current_user_moderator() -> bool:
    """Check if the current user has moderator permissions.
    
    Returns:
        True if current user is a moderator, False otherwise
    """
    user = get_current_user()
    if not user:
        return False
    
    try:
        from .hierarchy_manager import hierarchy_manager
        return hierarchy_manager.is_user_moderator(user.id, user.email)
    except Exception as e:
        logger.warning(f"Error checking moderator status: {e}")
        return user.is_moderator if user else False

def get_current_user_hierarchy_level() -> str:
    """Get the current user's hierarchy level.
    
    Returns:
        User's hierarchy level (defaults to PADDOCK)
    """
    user = get_current_user()
    return user.hierarchy_level if user else "PADDOCK"

def check_current_user_permission(permission: str) -> bool:
    """Check if the current user has a specific permission.
    
    Args:
        permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    user = get_current_user()
    if not user:
        return False
    
    try:
        from .hierarchy_manager import hierarchy_manager
        return hierarchy_manager.check_permission(user.id, permission, user.email)
    except Exception as e:
        logger.warning(f"Error checking user permission: {e}")
        return False 