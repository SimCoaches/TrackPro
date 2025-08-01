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
    global _current_user, _current_session
    logger.debug("Checking is_logged_in...")
    
    # First check our module state
    if _current_user is not None and _current_session is not None:
        logger.debug(f"Logged in based on module state: User={_current_user.id}, Session exists.")
        return True
    else:
        logger.debug(f"Module state check: _current_user={_current_user}, _current_session={_current_session}")
        
    # If module state doesn't indicate logged in, check directly with Supabase client
    # This serves as a fallback when module state is not synchronized
    if supabase and hasattr(supabase, 'client') and supabase.client and hasattr(supabase.client, 'auth'):
        logger.debug("Checking login status via Supabase client fallback...")
        try:
            # Try to get the current session
            session = supabase.client.auth.get_session()
            if session and session.user:
                # Update our module state while we're at it
                _current_user = session.user
                _current_session = session
                logger.debug(f"Logged in based on client.get_session(): User={_current_user.id}")
                return True
            else:
                logger.debug(f"client.get_session() did not return a valid session/user. Session: {session}")
                
            # Also try the alternative method
            try:
                user_response = supabase.client.auth.get_user()
                # Check the structure of the response carefully
                user = None
                if hasattr(user_response, 'user') and user_response.user:
                    user = user_response.user
                elif hasattr(user_response, 'data') and hasattr(user_response.data, 'user') and user_response.data.user:
                    user = user_response.data.user
                
                if user:
                    # Update our module state
                    _current_user = user
                    # Session might still be None if only user info is available
                    _current_session = session # Keep session from previous check
                    logger.debug(f"Logged in based on client.get_user(): User={_current_user.id}")
                    return True
                else:
                    logger.debug(f"client.get_user() did not return a valid user. Response: {user_response}")
            except Exception as get_user_e:
                logger.debug(f"Error during client.get_user() fallback: {get_user_e}")
                pass
        except Exception as e:
            logger.debug(f"Error checking login status with Supabase client: {e}")
            pass
    else:
        logger.debug("Supabase client not available for fallback check.")
    
    logger.debug("is_logged_in returning False")
    return False

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

def update_auth_state_from_client():
    """Synchronize the module's auth state with the Supabase client's state.
    
    This should be called after initializing the client or restoring a session.
    """
    global _current_user, _current_session
    
    # Access the client instance via the imported manager object
    if not supabase or not hasattr(supabase, 'client') or not supabase.client or not hasattr(supabase.client, 'auth'):
        logger.warning("Cannot update auth state: Supabase client not fully initialized.")
        _current_user = None
        _current_session = None
        return
        
    try:
        # Get the session directly from the client instance
        session = supabase.client.auth.get_session()
        
        if session and session.user:
            logger.info(f"Updating auth state from client. Found session for user: {session.user.email}")
            _current_session = session
            _current_user = session.user
        else:
            # Try an alternative method to check auth state
            # Some versions of Supabase's library return different response formats
            try:
                user = supabase.client.auth.get_user()
                if user and hasattr(user, 'user') and user.user:
                    logger.info(f"Updating auth state from client using get_user. Found user: {user.user.email}")
                    _current_user = user.user
                    _current_session = session  # Even if None, this is correct
                    return
            except Exception as alt_e:
                logger.warning(f"Alternative auth check failed: {alt_e}")
            
            logger.info("Updating auth state from client. No active session found.")
            _current_user = None
            _current_session = None
    except Exception as e:
        logger.error(f"Error updating auth state from client: {e}", exc_info=True)
        _current_user = None
        _current_session = None 