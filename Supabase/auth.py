"""
Supabase Authentication Module

This module handles all authentication-related operations (signup, login, logout)
and manages the current user's session.
"""

from typing import Optional, Dict, Any, Tuple
from .client import supabase
import logging

logger = logging.getLogger(__name__)

# Global variables to store the current user and session
_current_user = None
_current_session = None

def signup(email: str, password: str, metadata: Dict[str, Any] = None, options: Dict[str, Any] = None) -> Tuple[bool, str]:
    """
    Register a new user with Supabase.
    
    Args:
        email: The user's email address
        password: The user's password
        metadata: Optional metadata to store with the user (username, first_name, last_name, etc.)
        options: Optional parameters like skip_verification
        
    Returns:
        Tuple[bool, str]: A tuple containing a success flag and a message
    """
    if not supabase:
        return False, "Database connection not available"
        
    try:
        signup_data = {
            "email": email,
            "password": password
        }
        
        # Add metadata if provided
        if metadata:
            signup_data["data"] = metadata
            
        # Process signup with options
        if options:
            response = supabase.client.auth.sign_up(signup_data, options)
        else:
            response = supabase.client.auth.sign_up(signup_data)
        
        if response.user:
            return True, "Signup successful, please verify your email"
        else:
            return False, "Signup failed: Unknown error"
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            return False, "Signup failed: Email already registered"
        return False, f"Signup failed: {error_msg}"

def login(email: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate a user with Supabase.
    
    Args:
        email: The user's email address
        password: The user's password
        
    Returns:
        Tuple[bool, str]: A tuple containing a success flag and a message
    """
    global _current_user, _current_session
    
    if not supabase:
        return False, "Database connection not available"
        
    try:
        response = supabase.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            _current_user = response.user
            _current_session = response.session
            return True, "Login successful"
        else:
            return False, "Login failed: Invalid credentials"
    except Exception as e:
        error_msg = str(e)
        if "Email not confirmed" in error_msg:
            return False, "Login failed: Email not confirmed. Please check your inbox"
        elif "Invalid login credentials" in error_msg:
            return False, "Login failed: Invalid credentials"
        return False, f"Login failed: {error_msg}"

def sign_in_with_google(redirect_url: str = None) -> Any:
    """
    Begin the Google OAuth login flow.
    
    Args:
        redirect_url: URL to redirect to after authentication
        
    Returns:
        The OAuth response containing URL to redirect to
    """
    if not supabase:
        logger.error("Database connection not available")
        return None
        
    try:
        options = {}
        if redirect_url:
            options["redirect_to"] = redirect_url
            
        response = supabase.client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": options
        })
        return response
    except Exception as e:
        logger.error(f"Google login error: {e}")
        return None

def sign_in_with_discord(redirect_url: str = None) -> Any:
    """
    Begin the Discord OAuth login flow.
    
    Args:
        redirect_url: URL to redirect to after authentication
        
    Returns:
        The OAuth response containing URL to redirect to
    """
    if not supabase:
        logger.error("Database connection not available")
        return None
        
    try:
        options = {}
        if redirect_url:
            options["redirect_to"] = redirect_url
            
        response = supabase.client.auth.sign_in_with_oauth({
            "provider": "discord",
            "options": options
        })
        return response
    except Exception as e:
        logger.error(f"Discord login error: {e}")
        return None

def handle_auth_callback(url: str) -> Tuple[bool, str]:
    """
    Handle OAuth callback URL to complete social login.
    
    Args:
        url: The callback URL with auth parameters
        
    Returns:
        Tuple[bool, str]: Success status and message
    """
    global _current_user, _current_session
    
    if not supabase:
        return False, "Database connection not available"
        
    try:
        # Extract params from URL and complete the OAuth process
        response = supabase.client.auth.exchange_code_for_session(url)
        
        if response and response.user:
            _current_user = response.user
            _current_session = response.session
            logger.info(f"Social login successful for user: {response.user.email}")
            
            # Force update the current session for all future requests
            if hasattr(supabase.client.auth, 'set_session'):
                supabase.client.auth.set_session(response.session.access_token)
            
            return True, "Social login successful"
        else:
            logger.error("Failed to exchange code for session")
            return False, "Social login failed: Could not complete authentication"
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return False, f"Social login failed: {str(e)}"

def logout() -> bool:
    """
    Log out the current user.
    
    Returns:
        bool: True if logout succeeded, False otherwise
    """
    global _current_user, _current_session
    
    if not supabase:
        return False
        
    try:
        supabase.client.auth.sign_out()
        _current_user = None
        _current_session = None
        return True
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return False

def is_logged_in() -> bool:
    """
    Check if a user is currently logged in.
    
    Returns:
        bool: True if a user is logged in, False otherwise
    """
    return _current_user is not None and _current_session is not None

def get_current_user():
    """
    Get the current authenticated user.
    
    Returns:
        The current user object or None if not logged in
    """
    return _current_user

def get_session_token() -> str:
    """
    Get the current session token.
    
    Returns:
        str: The session token or empty string if not logged in
    """
    if _current_session:
        return _current_session.access_token
    return "" 