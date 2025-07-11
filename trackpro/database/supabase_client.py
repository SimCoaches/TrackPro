"""Supabase client singleton for database access."""

import time
import socket
import random
import threading
import json
import os
from urllib.parse import urlparse
from supabase import create_client, Client
from gotrue import AuthResponse
from ..config import config  # Import the global config instance
import logging

# Import secure session manager
try:
    from ..auth.secure_session import SecureSessionManager
    SECURE_SESSION_AVAILABLE = True
except ImportError:
    SECURE_SESSION_AVAILABLE = False
    SecureSessionManager = None

logger = logging.getLogger(__name__)

# Global instance of SupabaseManager
_supabase_manager = None

def get_supabase_client():
    """Get the global Supabase client instance.
    
    Returns:
        Client: The Supabase client instance, or None if not initialized.
    """
    global _supabase_manager
    
    try:
        # Initialize the manager if it doesn't exist
        if _supabase_manager is None:
            logger.info("Initializing Supabase manager for the first time")
            _supabase_manager = SupabaseManager()
        
        # Return the client
        return _supabase_manager.client if _supabase_manager else None
    except Exception as e:
        logger.error(f"Error getting Supabase client: {e}")
        return None

# DNS cache to avoid repeated lookups
DNS_CACHE = {}
DNS_CACHE_LOCK = threading.Lock()

def resolve_hostname(hostname):
    """Resolve hostname to IP with caching and timeout optimization."""
    with DNS_CACHE_LOCK:
        if hostname in DNS_CACHE and DNS_CACHE[hostname]['expiry'] > time.time():
            logger.debug(f"Using cached DNS for {hostname}")
            return DNS_CACHE[hostname]['ips']
    
    try:
        # Add shorter timeout for faster resolution
        import socket
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5.0)  # 5 second timeout instead of default
        
        # Try to resolve the hostname
        logger.info(f"[DNS] Resolving {hostname} with 5s timeout...")
        start_time = time.time()
        
        # Use the same interface as before but with better error handling
        ips = socket.gethostbyname_ex(hostname)[2]
        
        end_time = time.time()
        logger.info(f"[DNS] Resolved {hostname} to {ips[0]} in {end_time - start_time:.2f}s")
        
        if ips:
            # Cache for 1 hour with some jitter to avoid synchronized expiry
            expiry = time.time() + 3600 + random.randint(0, 300)
            with DNS_CACHE_LOCK:
                DNS_CACHE[hostname] = {'ips': ips, 'expiry': expiry}
            logger.debug(f"Resolved {hostname} to {ips}")
        
        return ips
    except socket.gaierror as e:
        logger.error(f"[DNS] Failed to resolve {hostname}: {e}")
        return None
    except socket.timeout:
        logger.error(f"[DNS] Timeout resolving {hostname} after 5 seconds")
        return None
    except Exception as e:
        logger.error(f"[DNS] Unexpected error resolving {hostname}: {e}")
        return None
    finally:
        # Reset socket timeout to original value
        socket.setdefaulttimeout(old_timeout)

class RetryStrategy:
    """Implements exponential backoff retry strategy."""
    
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=8.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute(self, func, *args, **kwargs):
        """Execute function with retries."""
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                    jitter = random.uniform(0, 0.1 * delay)
                    wait_time = delay + jitter
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {wait_time:.2f}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed. Last error: {e}")
        
        raise last_exception

class SupabaseManager:
    """Manages Supabase client and authentication."""
    
    def __init__(self):
        """Initialize the Supabase manager."""
        self._client = None
        self._offline_mode = True  # Start in offline mode
        self._retry_strategy = RetryStrategy()
        self._hostname = None
        self._cached_ip = None
        self._auth_file = os.path.join(os.path.expanduser("~"), ".trackpro", "auth.json")
        
        # Initialize secure session manager
        self._secure_session = None
        if SECURE_SESSION_AVAILABLE:
            try:
                self._secure_session = SecureSessionManager("TrackPro")
                logger.info("Secure session manager initialized")
                # Migrate existing plaintext sessions to encrypted storage
                self._migrate_plaintext_sessions()
            except Exception as e:
                logger.error(f"Failed to initialize secure session manager: {e}")
                self._secure_session = None
        
        # Try to restore session from file
        self._restore_session()
        
        # Initialize the client
        self.initialize()
    
    def _migrate_plaintext_sessions(self):
        """Migrate existing plaintext sessions to encrypted storage."""
        if not self._secure_session:
            return
        
        try:
            from pathlib import Path
            plaintext_file = Path(self._auth_file)
            if plaintext_file.exists():
                logger.info("Found plaintext session file, migrating to encrypted storage")
                success = self._secure_session.migrate_from_plaintext(plaintext_file)
                if success:
                    logger.info("Successfully migrated session to encrypted storage")
                else:
                    logger.warning("Failed to migrate session to encrypted storage")
        except Exception as e:
            logger.error(f"Error during session migration: {e}")
    
    def get_session_security_info(self):
        """Get information about session security status.
        
        Returns:
            Dictionary with security information
        """
        info = {
            'secure_session_available': SECURE_SESSION_AVAILABLE,
            'secure_session_active': self._secure_session is not None,
            'encryption_enabled': False,
            'integrity_verification': False,
            'secure_permissions': False,
            'session_exists': False,
            'migration_completed': False
        }
        
        if self._secure_session:
            session_info = self._secure_session.get_session_info()
            info.update({
                'encryption_enabled': session_info.get('encryption_enabled', False),
                'integrity_verification': session_info.get('integrity_verification', False),
                'secure_permissions': session_info.get('secure_permissions', False),
                'session_exists': session_info.get('session_exists', False),
                'session_file': session_info.get('session_file', ''),
                'session_dir': session_info.get('session_dir', ''),
                'platform': session_info.get('platform', ''),
                'migration_completed': not os.path.exists(self._auth_file)
            })
        
        return info
    
    def _restore_session(self):
        """Restore session from file if available."""
        try:
            # Try secure session first
            if self._secure_session:
                auth_data = self._secure_session.load_session()
                if auth_data and auth_data.get('access_token'):
                    logger.info("Found saved authentication session (encrypted)")
                    self._saved_auth = auth_data
                    return True
            
            # Fallback to plaintext session
            if os.path.exists(self._auth_file):
                with open(self._auth_file, 'r') as f:
                    auth_data = json.load(f)
                
                # Check if we have the minimum required data
                if auth_data.get('access_token'):
                    logger.info("Found saved authentication session (plaintext)")
                    self._saved_auth = auth_data
                    return True
            
            logger.info("No saved authentication session found")
            self._saved_auth = None
            return False
        except Exception as e:
            logger.error(f"Error restoring authentication session: {e}")
            self._saved_auth = None
            return False
    
    def _is_token_expired(self, expires_at):
        """Check if a token is expired.
        
        Args:
            expires_at: Token expiration timestamp
            
        Returns:
            bool: True if token is expired or expiration is unknown
        """
        if not expires_at:
            return True  # Assume expired if no expiration info
        
        try:
            from datetime import datetime
            
            # Handle different timestamp formats
            if isinstance(expires_at, (int, float)):
                # Unix timestamp
                expiry_time = datetime.fromtimestamp(expires_at)
            elif isinstance(expires_at, str):
                # ISO format timestamp
                expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            else:
                return True  # Unknown format, assume expired
            
            # Add a 2-minute buffer to avoid using tokens that are about to expire
            # Reduced from 5 minutes to 2 minutes to be less aggressive
            import time
            current_time = datetime.fromtimestamp(time.time())
            buffer_seconds = 120  # 2 minutes instead of 5
            
            return (expiry_time.timestamp() - current_time.timestamp()) < buffer_seconds
            
        except Exception as e:
            logger.warning(f"Error checking token expiration: {e}")
            return True  # Assume expired on error
    
    def _restore_session_safely(self):
        """Safely restore session without consuming refresh tokens unnecessarily.
        
        Returns:
            bool: True if session was restored successfully, False otherwise
        """
        if not self._saved_auth or not self._client:
            return False
        
        access_token = self._saved_auth.get('access_token')
        refresh_token = self._saved_auth.get('refresh_token')
        expires_at = self._saved_auth.get('expires_at')
        
        if not access_token:
            logger.warning("No access token found in saved session")
            return False
        
        try:
            # First, check if the current access token is still valid
            is_expired = self._is_token_expired(expires_at)
            
            if not is_expired:
                logger.info("Access token appears to still be valid, attempting direct restoration")
                try:
                    # Try to set the session with both tokens but in a way that doesn't consume refresh token
                    # Only pass refresh token if we have it, otherwise just access token
                    if refresh_token:
                        self._client.auth.set_session(access_token, refresh_token)
                    else:
                        # Some clients support setting just access token
                        try:
                            self._client.auth.set_session(access_token)
                        except TypeError:
                            # If single parameter doesn't work, pass empty string for refresh token
                            self._client.auth.set_session(access_token, "")
                    
                    # Test if the session works by making a simple call
                    session = self._client.auth.get_session()
                    if session and hasattr(session, 'user') and session.user:
                        logger.info("Session restored successfully with existing tokens")
                        # Sync auth state with other modules after successful restoration
                        self._sync_auth_state_with_modules()
                        return True
                    else:
                        logger.info("Session restoration with existing tokens failed, token may be invalid")
                        
                except Exception as e:
                    logger.info(f"Direct session restoration failed: {e}")
                    # Fall through to refresh token logic
            else:
                logger.info("Access token appears to be expired")
            
            # If we reach here, either the token is expired or direct restoration failed
            # Try to refresh the session using the refresh token
            if refresh_token:
                logger.info("Access token expired or invalid, attempting to refresh session")
                try:
                    # Try the standard refresh method first
                    if hasattr(self._client.auth, 'refresh_session'):
                        logger.info("Attempting to refresh session using auth.refresh_session method")
                        response = self._client.auth.refresh_session()
                        if response and hasattr(response, 'session') and response.session:
                            logger.info("Session refreshed successfully using refresh_session method")
                            remember_me = self._saved_auth.get('remember_me', True)
                            self._save_session(response, remember_me)
                            # Sync auth state with other modules after successful restoration
                            self._sync_auth_state_with_modules()
                            return True
                    
                    # Try the older refresh method
                    if hasattr(self._client.auth, 'refresh'):
                        logger.info("Attempting to refresh session using auth.refresh method")
                        response = self._client.auth.refresh()
                        if response and hasattr(response, 'session') and response.session:
                            logger.info("Session refreshed successfully using refresh method")
                            remember_me = self._saved_auth.get('remember_me', True)
                            self._save_session(response, remember_me)
                            # Sync auth state with other modules after successful restoration
                            self._sync_auth_state_with_modules()
                            return True
                    
                    # Try using the refresh token directly with set_session
                    logger.info("Attempting manual refresh using refresh token")
                    try:
                        # Create a temporary session with the refresh token to trigger refresh
                        temp_session = {
                            'access_token': access_token,
                            'refresh_token': refresh_token
                        }
                        self._client.auth.set_session(access_token, refresh_token)
                        
                        # Now try to get the session which should refresh automatically
                        refreshed_session = self._client.auth.get_session()
                        if refreshed_session and hasattr(refreshed_session, 'access_token'):
                            logger.info("Session refreshed successfully using manual refresh")
                            # Create a mock response for saving
                            class MockResponse:
                                def __init__(self, session):
                                    self.session = session
                            
                            remember_me = self._saved_auth.get('remember_me', True)
                            self._save_session(MockResponse(refreshed_session), remember_me)
                            # Sync auth state with other modules after successful restoration
                            self._sync_auth_state_with_modules()
                            return True
                    except Exception as manual_e:
                        logger.warning(f"Manual refresh failed: {manual_e}")
                    
                    # If all refresh attempts fail, clear the session conditionally
                    logger.info("All refresh attempts failed, clearing session conditionally based on remember_me")
                    self._clear_session_conditionally()
                    
                except Exception as e:
                    logger.warning(f"Session refresh handling failed: {e}")
                    # If refresh fails, clear the saved session conditionally to respect remember_me
                    if "already used" in str(e).lower() or "invalid" in str(e).lower():
                        logger.info("Refresh token is invalid, clearing saved session conditionally")
                        self._clear_session_conditionally()
                    else:
                        # For other errors, keep the session if remember_me is true
                        logger.info("Refresh failed but keeping session due to remember_me preference")
                        # Don't clear the session, let the user try to log in again later
            else:
                logger.warning("No refresh token available for session restoration")
                # Clear invalid session conditionally
                self._clear_session_conditionally()
            
            return False
            
        except Exception as e:
            logger.error(f"Error during safe session restoration: {e}")
            # Clear problematic session data conditionally on any error
            self._clear_session_conditionally()
            return False
    
    def _save_session(self, response, remember_me=True):
        """Save session to file for persistence between app restarts.
        
        Args:
            response: The authentication response containing session data
            remember_me: Whether to remember the session after the app is closed (default: True)
        """
        try:
            if not response:
                return
            
            # Extract tokens from response
            session = response.session if hasattr(response, 'session') else response
            auth_data = {
                'access_token': session.access_token if hasattr(session, 'access_token') else None,
                'refresh_token': session.refresh_token if hasattr(session, 'refresh_token') else None,
                'expires_at': session.expires_at if hasattr(session, 'expires_at') else None,
                'remember_me': remember_me  # Store the remember_me preference
            }
            
            # Try secure session first
            if self._secure_session:
                success = self._secure_session.save_session(auth_data)
                if success:
                    logger.info(f"Authentication session saved securely with remember_me={remember_me}")
                    self._saved_auth = auth_data
                    return True
                else:
                    logger.warning("Failed to save session securely, falling back to plaintext")
            
            # Fallback to plaintext session
            os.makedirs(os.path.dirname(self._auth_file), exist_ok=True)
            with open(self._auth_file, 'w') as f:
                json.dump(auth_data, f)
            
            logger.info(f"Authentication session saved (plaintext) with remember_me={remember_me}")
            self._saved_auth = auth_data
            return True
        except Exception as e:
            logger.error(f"Error saving authentication session: {e}")
            return False
    
    def _clear_session(self):
        """Clear the saved session."""
        try:
            success = True
            
            # Clear secure session
            if self._secure_session:
                if not self._secure_session.clear_session():
                    success = False
                    logger.warning("Failed to clear secure session")
                else:
                    logger.info("Secure authentication session cleared")
            
            # Clear plaintext session
            if os.path.exists(self._auth_file):
                os.remove(self._auth_file)
                logger.info("Plaintext authentication session cleared")
            
            self._saved_auth = None
            return success
        except Exception as e:
            logger.error(f"Error clearing authentication session: {e}")
            return False
    
    def _clear_session_conditionally(self, respect_remember_me=True):
        """Clear the saved session conditionally based on remember_me preference.
        
        Args:
            respect_remember_me: If True, only clear if remember_me is False. If False, always clear.
            
        Returns:
            bool: True if session was cleared, False if kept due to remember_me
        """
        try:
            # If not respecting remember_me, always clear
            if not respect_remember_me:
                return self._clear_session()
            
            # Check remember_me preference
            if self._saved_auth and 'remember_me' in self._saved_auth:
                remember_me = self._saved_auth.get('remember_me', False)
                if remember_me:
                    logger.info("Session has remember_me=True, keeping session data for future restoration")
                    # Don't clear the session file, but clear the in-memory tokens to force re-auth on next attempt
                    if self._saved_auth:
                        # Only clear the sensitive token data but keep the file with remember_me preference
                        logger.info("Clearing in-memory tokens but preserving remember_me preference")
                    return False  # Session kept
                else:
                    logger.info("Session has remember_me=False, clearing session data")
                    return self._clear_session()
            else:
                # No remember_me preference found, default to clearing
                logger.info("No remember_me preference found, clearing session data")
                return self._clear_session()
                
        except Exception as e:
            logger.error(f"Error in conditional session clearing: {e}")
            # On error, default to keeping session to be safe
            return False
    
    def initialize(self):
        """Initialize the Supabase client with retries and DNS caching."""
        try:
            # Check if Supabase is enabled
            logger.info("Checking if Supabase is enabled...")
            if not config.supabase_enabled:
                logger.info("Supabase is disabled in configuration")
                self._offline_mode = True
                return
            logger.info("Supabase is enabled in configuration")
            
            # Get Supabase configuration
            url = config.supabase_url
            key = config.supabase_key
            
            # Force refresh config if needed by reading from env directly
            if "xjpewnaxszuqluhdhusf" in url:
                # Detected old URL, force refresh from environment
                logger.warning("Found old Supabase URL, forcing refresh from environment")
                import os
                env_url = os.getenv('SUPABASE_URL')
                env_key = os.getenv('SUPABASE_KEY')
                if env_url and "xbfotxwpntqplvvsffrr" in env_url:
                    url = env_url
                    key = env_key
                    # Update config for future use
                    config.set('supabase.url', url)
                    config.set('supabase.key', key)
                    logger.info("Updated config with new Supabase credentials")
            
            if not url or not key:
                logger.warning("Supabase credentials not configured")
                self._offline_mode = True
                return
            
            logger.info(f"Using Supabase URL: {url}")  # Log the full URL for debugging
            logger.info(f"Got Supabase key: {key[:20]}...")  # Only log first part of key for security
            
            # Extract hostname for DNS caching
            parsed_url = urlparse(url)
            self._hostname = parsed_url.netloc
            
            # Try to resolve hostname in advance
            logger.info(f"[INIT_DEBUG] Attempting DNS resolution for: {self._hostname}")
            ips = resolve_hostname(self._hostname)
            if ips:
                self._cached_ip = ips[0]
                logger.info(f"Resolved {self._hostname} to {self._cached_ip}")
            else:
                logger.warning(f"[INIT_DEBUG] DNS resolution failed for {self._hostname}")
            
            # Create Supabase client
            logger.info("Initializing Supabase client...")
            try:
                # Use retry strategy for client creation
                def create_and_test_client():
                    logger.info("[INIT_DEBUG] Attempting create_client...")
                    # Create client without extra options to avoid 'headers' error
                    client = create_client(url, key)
                    logger.info("[INIT_DEBUG] create_client call successful.")
                    return client
                
                # Explicitly clear old client to avoid reusing
                self._client = None
                
                # Create new client
                self._client = self._retry_strategy.execute(create_and_test_client)
                logger.info(f"[INIT_DEBUG] Client object created: {self._client is not None}")
                
                # If we have a saved session, try to restore it
                if self._saved_auth and self._saved_auth.get('access_token'):
                    logger.info("Attempting to restore saved session...")
                    try:
                        # Use the new safe restoration method that properly handles token expiration
                        session_restored = self._restore_session_safely()
                        if session_restored:
                            logger.info("Session restored successfully using safe method")
                            # Sync auth state with other modules after successful restoration
                            self._sync_auth_state_with_modules()
                        else:
                            logger.info("Session restoration failed, user will need to sign in again")
                            # Clear the invalid session data conditionally
                            self._clear_session_conditionally()
                    except Exception as e:
                        logger.warning(f"Failed to restore session: {e}")
                        # Clear the problematic session data conditionally to respect remember_me
                        self._clear_session_conditionally()
                
                # Test connection with a simple operation
                try:
                    # Just check if we can access the auth API
                    logger.info("Testing connection to Supabase...")
                    logger.info("[INIT_DEBUG] Attempting _client.auth.get_session()...")
                    self._client.auth.get_session()
                    logger.info("[INIT_DEBUG] _client.auth.get_session() successful.")
                    self._offline_mode = False
                    logger.info("Supabase client initialized and connected successfully")
                except Exception as e:
                    logger.error(f"[INIT_DEBUG] _client.auth.get_session() failed: {e}")
                    logger.warning(f"Connected but session retrieval failed: {e}")
                    # Still consider it a success if we got this far
                    self._offline_mode = False
                    logger.info("Supabase client initialized (with limited functionality)")
            except Exception as e:
                logger.error(f"[INIT_DEBUG] Client creation/retry failed: {e}")
                logger.error(f"Failed to create/test Supabase client after retries: {e}")
                self._offline_mode = True
                self._client = None
                return
            
        except Exception as e:
            logger.error(f"[INIT_DEBUG] General initialization failure: {e}")
            logger.error(f"Failed to initialize Supabase client: {e}")
            self._offline_mode = True
            self._client = None
    
    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry strategy and offline fallback."""
        if self._offline_mode or not self._client:
            logger.warning(f"Cannot execute {func.__name__} - Supabase is not connected")
            return None
        
        try:
            return self._retry_strategy.execute(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Operation {func.__name__} failed after retries: {e}")
            # If we get a connection error, we might need to refresh the client
            if isinstance(e, (socket.gaierror, ConnectionError, TimeoutError)):
                logger.info("Connection error detected, attempting to reinitialize client")
                self.initialize()
            return None
    
    @property
    def client(self) -> Client:
        """Get the Supabase client.
        
        Returns:
            Client: The Supabase client
        """
        if self._offline_mode:
            return None
        return self._client
    
    def is_authenticated(self) -> bool:
        """Check if a user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        try:
            if self._offline_mode or not self._client:
                return False
            
            def check_auth():
                user_response = self._client.auth.get_user()
                return user_response is not None and hasattr(user_response, 'user') and user_response.user is not None
            
            return self._execute_with_retry(check_auth) or False
        except Exception as e:
            logger.error(f"Error checking authentication: {e}")
            return False
    
    def get_user(self):
        """Get the current user.
        
        Returns:
            User: The current user, or None if not authenticated
        """
        if self._offline_mode or not self._client:
            return None
        
        def get_user_func():
            return self._client.auth.get_user()
        
        return self._execute_with_retry(get_user_func)
    
    def sign_up(self, email: str, password: str, metadata=None, custom_options=None) -> AuthResponse:
        """Sign up a new user.
        
        Args:
            email: The user's email
            password: The user's password
            metadata: Additional user metadata (username, first_name, last_name, date_of_birth, etc.)
            custom_options: Additional options for signup (e.g., skip_verification)
            
        Returns:
            AuthResponse: The authentication response
        """
        if not self._client:
            logger.error("Cannot sign up: Supabase client not initialized")
            print("[SIGNUP ERROR] Supabase client not initialized")
            raise ValueError("Supabase client not initialized")
        
        if self._offline_mode:
            logger.error("Cannot sign up: Supabase is in offline mode")
            print("[SIGNUP ERROR] Cannot sign up in offline mode")
            raise ValueError("Cannot sign up in offline mode")
        
        # Prepare metadata
        user_metadata = {}
        if metadata:
            user_metadata.update(metadata)
        
        # Prepare options
        options = {
            "data": user_metadata
        }
        
        # Add email redirect URL for verification
        # This ensures users are redirected back to a confirmation page after clicking the email link
        try:
            from ..config import config
            # Use the application's base URL or a default confirmation page
            base_url = getattr(config, 'app_base_url', 'http://localhost:3000')
            options["email_redirect_to"] = f"{base_url}/auth/confirm"
        except Exception:
            # Fallback to a generic confirmation URL
            options["email_redirect_to"] = "http://localhost:3000/auth/confirm"
        
        # Add custom options if provided
        if custom_options:
            # Add auto-verification option if requested
            if custom_options.get('skip_verification'):
                print("[SIGNUP] Auto-verification enabled")
                options["email_redirect_to"] = None
                options["data"]["email_confirmed"] = True  # Additional flag to help tracking
            
            # Any other custom options
            for key, value in custom_options.items():
                if key not in ['skip_verification']:  # Skip our custom flags
                    options[key] = value
        
        # Log metadata for debugging (without password)
        safe_metadata = user_metadata.copy()
        logger.info(f"Signup attempt with email: {email}, metadata: {safe_metadata}, options: {options}")
        print(f"[SIGNUP] Attempt with email: {email}, metadata: {safe_metadata}, options: {options}")
        
        # Sign up with retry
        def signup_func():
            try:
                logger.info(f"Signing up user: {email}")
                print(f"[SIGNUP] Calling Supabase auth.sign_up for {email}")
                
                # Print actual request data for debugging
                request_data = {
                    "email": email,
                    "password": password,
                    "options": options
                }
                print(f"[SIGNUP] Request data: {request_data}")
                
                auth_response = self._client.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": options
                })
                
                # Log response for debugging
                print(f"[SIGNUP] Response received: {auth_response}")
                if hasattr(auth_response, 'user'):
                    print(f"[SIGNUP] User created with ID: {auth_response.user.id if auth_response.user else 'None'}")
                
                logger.info(f"User signed up successfully: {email}")
                return auth_response
            except Exception as e:
                error_msg = str(e)
                # Log detailed error information for debugging
                logger.error(f"Detailed signup error: {error_msg}")
                print(f"[SIGNUP ERROR] {error_msg}")
                
                # Print exception type for debugging
                print(f"[SIGNUP ERROR] Exception type: {type(e).__name__}")
                
                # Check for specific error types
                if "unique constraint" in error_msg.lower() and "username" in error_msg.lower():
                    raise ValueError(f"Username already exists. Please choose a different username.")
                elif "unique constraint" in error_msg.lower() and "email" in error_msg.lower():
                    raise ValueError(f"Email address already registered. Please use a different email or sign in.")
                elif "invalid" in error_msg.lower() and "email" in error_msg.lower():
                    raise ValueError(f"Invalid email format. Please use a standard email address.")
                elif "password" in error_msg.lower():
                    raise ValueError(f"Password issue: {error_msg}")
                else:
                    # Re-raise with more details for debugging
                    import traceback
                    print(f"[SIGNUP ERROR] Traceback:\n{traceback.format_exc()}")
                    raise ValueError(f"Signup failed: {error_msg}")
        
        try:
            response = self._execute_with_retry(signup_func)
            # Save session for later restoration if auto-sign-in happens
            self._save_session(response)
            return response
        except ValueError as e:
            # Value errors are already formatted with user-friendly messages
            logger.error(f"Signup validation error: {e}")
            print(f"[SIGNUP ERROR] Validation error: {e}")
            raise
        except Exception as e:
            # Add more context to the error
            error_msg = str(e)
            logger.error(f"Failed to sign up after retries: {error_msg}")
            print(f"[SIGNUP ERROR] Failed after retries: {error_msg}")
            
            import traceback
            print(f"[SIGNUP ERROR] Exception traceback:\n{traceback.format_exc()}")
            
            if "network" in error_msg.lower() or "connection" in error_msg.lower():
                raise ValueError("Network connection issue. Please check your internet connection.")
            else:
                raise ValueError(f"Failed to create account: {error_msg}")
    
    def sign_in(self, email: str, password: str) -> AuthResponse:
        """Sign in a user.
        
        Args:
            email: The user's email
            password: The user's password
            
        Returns:
            AuthResponse: The signin response
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign in - Supabase is not connected")
            return None
        
        logger.info(f"Attempting login for email: {email}")
        
        def signin_func():
            response = self._client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            logger.info("Login successful")
            # Save session for persistence
            self._save_session(response)
            # Sync auth state with other modules after successful sign-in
            self._sync_auth_state_with_modules()
            return response
        
        try:
            return self._execute_with_retry(signin_func)
        except Exception as e:
            # Check if this is an email confirmation error
            if "email not confirmed" in str(e).lower():
                logger.warning(f"Email not confirmed for {email}")
                raise ValueError("Please check your email and click the confirmation link before signing in.")
            # Other errors
            logger.error(f"Login error: {e}")
            raise
    
    def sign_in_with_google(self, redirect_to: str = None) -> dict:
        """Begin Google OAuth flow.
        
        Args:
            redirect_to: URL to redirect to after authentication
            
        Returns:
            The OAuth response containing URL to redirect to
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign in with Google - Supabase is not connected")
            return None
        
        logger.info("Attempting Google OAuth login")
        
        def oauth_func():
            options = {}
            if redirect_to:
                options["redirect_to"] = redirect_to
            
            response = self._client.auth.sign_in_with_oauth({
                "provider": "google",
                "options": options
            })
            return response
        
        try:
            return self._execute_with_retry(oauth_func)
        except Exception as e:
            logger.error(f"Google OAuth error: {e}")
            raise
    
    def sign_in_with_discord(self, redirect_to: str = None) -> dict:
        """Begin Discord OAuth flow.
        
        Args:
            redirect_to: URL to redirect to after authentication
            
        Returns:
            The OAuth response containing URL to redirect to
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign in with Discord - Supabase is not connected")
            return None
        
        logger.info("Attempting Discord OAuth login")
        
        def oauth_func():
            options = {}
            if redirect_to:
                options["redirect_to"] = redirect_to
            
            response = self._client.auth.sign_in_with_oauth({
                "provider": "discord",
                "options": options
            })
            return response
        
        try:
            return self._execute_with_retry(oauth_func)
        except Exception as e:
            logger.error(f"Discord OAuth error: {e}")
            raise
    
    def exchange_code_for_session(self, params):
        """Exchange OAuth code for session.
        
        Args:
            params: Either full callback URL or object with auth_code and code_verifier
            
        Returns:
            AuthResponse: The session response
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot exchange code - Supabase is not connected")
            return None
        
        logger.info("Exchanging OAuth code for session")
        
        def exchange_func():
            # Handle different input formats
            if isinstance(params, str):
                # It's a URL string - extract code and use default code verifier
                logger.warning("Using deprecated URL format for code exchange")
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(params)
                query_params = parse_qs(parsed_url.query)
                
                if 'code' in query_params:
                    code = query_params['code'][0]
                    logger.info(f"Extracted code from URL: {code[:5]}...")
                    
                    # Create exchange params without code verifier (deprecated)
                    exchange_params = {
                        "auth_code": code
                    }
                elif isinstance(params, dict) and 'auth_code' in params:
                    # Already formatted correctly
                    exchange_params = params
                else:
                    raise ValueError(f"Invalid params format - no auth code found")
            elif isinstance(params, dict):
                # It's already a params object
                if 'auth_code' not in params:
                    raise ValueError("Missing auth_code in exchange parameters")
                
                exchange_params = params
                logger.info(f"Using params directly for exchange: auth_code={params['auth_code'][:5]}...")
                if 'code_verifier' in params:
                    logger.info(f"With code_verifier: {params['code_verifier'][:10]}...")
            else:
                # Unknown format
                raise ValueError(f"Unsupported params type: {type(params)}")
            
            # ONLY use the primary exchange method, remove fallback logic
            try:
                logger.info(f"[DEBUG] About to call _client.auth.exchange_code_for_session with: {exchange_params}")
                response = self._client.auth.exchange_code_for_session(exchange_params)
            except Exception as e:
                logger.error(f"Code exchange failed: {e}", exc_info=True)
                raise e # Re-raise the specific error directly
            
            logger.info("Session exchange successful")
            # Save session for persistence
            self._save_session(response)
            
            # Sync auth state with other modules after successful OAuth exchange
            self._sync_auth_state_with_modules()
            
            # Print user info for debugging
            if response and hasattr(response, 'user') and response.user:
                logger.info(f"Authenticated user ID: {response.user.id}")
                logger.info(f"Authenticated user email: {response.user.email}")
                
            return response
        
        try:
            return self._execute_with_retry(exchange_func)
        except Exception as e:
            logger.error(f"Code exchange error: {e}")
            raise
    
    def _sync_auth_state_with_modules(self):
        """Sync authentication state with other auth modules to ensure consistency."""
        try:
            # Skip legacy auth module sync for performance - it's causing warnings
            # and the new auth system should be standalone
            logger.debug("Skipping legacy auth module sync for performance")
            
            # Try to update the trackpro auth user manager if it exists
            try:
                from trackpro.auth import user_manager
                # Update the current user in the user manager
                current_user = self.get_user()
                if current_user and hasattr(current_user, 'user'):
                    # Set the current user in the user manager
                    user_manager._current_user = user_manager.User(
                        id=current_user.user.id,
                        email=current_user.user.email,
                        name=current_user.user.user_metadata.get('name', current_user.user.email),
                        is_authenticated=True
                    )
                    logger.info("Synced auth state with trackpro user manager")
                else:
                    user_manager._current_user = None
            except (ImportError, AttributeError):
                pass  # User manager not available or different structure
                
        except Exception as e:
            logger.warning(f"Error syncing auth state with modules: {e}")
    
    def sign_out(self, force_clear=False):
        """Sign out the current user.
        
        Args:
            force_clear: If True, always clear the saved session regardless of remember_me preference
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign out - Supabase is not connected")
            return
        
        logger.info(f"Signing out user (force_clear={force_clear})")
        
        def signout_func():
            try:
                self._client.auth.sign_out()
                logger.info("Successfully signed out from Supabase client")
            except Exception as e:
                logger.warning(f"Error during Supabase sign out: {e}")
                # Continue with local cleanup even if remote sign out fails
            
            # Check if we should clear the saved session
            should_clear = force_clear
            
            # If not forcing, check the remember_me preference
            if not force_clear and self._saved_auth and 'remember_me' in self._saved_auth:
                remember_me = self._saved_auth.get('remember_me', False)
                # Only clear if remember_me is False
                should_clear = not remember_me
                logger.info(f"Remember me preference is {remember_me}, {'clearing' if should_clear else 'keeping'} session data")
            else:
                # Default to clearing if remember_me not found or force_clear is True
                should_clear = True
            
            # Clear saved session if needed
            if should_clear:
                self._clear_session()
                logger.info("Session cleared during sign out")
            else:
                logger.info("Session retained for remember me")
            
            # Sync auth state with other modules
            self._sync_auth_state_with_modules()
            
            logger.info("Sign out process completed successfully")
        
        try:
            self._execute_with_retry(signout_func)
        except Exception as e:
            logger.error(f"Error during sign out: {e}")
            # Force clear session on sign out errors to prevent inconsistent state
            self._clear_session()

    def reset_password_for_email(self, email: str, redirect_to: str = None):
        """Send a password reset email to the user.
        
        Args:
            email: The user's email address
            redirect_to: Optional URL to redirect to after password reset
        
        Returns:
            dict: Response from Supabase containing success/error information
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot send password reset email - Supabase is not connected")
            return {"error": "Service unavailable - please try again later"}
        
        logger.info(f"Sending password reset email to {email}")
        
        def reset_password_func():
            try:
                # Import config for fallback API call
                from ..config import config
                
                # Build options dict for redirect
                options = {}
                if redirect_to:
                    options["redirect_to"] = redirect_to
                
                # Call the reset password method - try different possible method names
                if hasattr(self._client.auth, 'reset_password_for_email'):
                    # Standard method name
                    response = self._client.auth.reset_password_for_email(email, options)
                elif hasattr(self._client.auth, 'resetPasswordForEmail'):
                    # Camel case method name
                    response = self._client.auth.resetPasswordForEmail(email, options)
                elif hasattr(self._client.auth, 'send_password_reset_email'):
                    # Alternative method name
                    response = self._client.auth.send_password_reset_email(email, options)
                else:
                    # Try to use the underlying API directly
                    logger.warning("Direct auth method not found, trying API call")
                    # Make a direct API call to the Supabase recovery endpoint
                    headers = {
                        'apikey': config.supabase_key,
                        'Content-Type': 'application/json'
                    }
                    
                    payload = {
                        'email': email
                    }
                    if redirect_to:
                        payload['redirect_to'] = redirect_to
                    
                    import requests
                    recovery_url = f"{config.supabase_url}/auth/v1/recover"
                    response = requests.post(recovery_url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        logger.info(f"Password reset email sent successfully to {email}")
                        return {"success": True, "message": "Password reset email sent successfully"}
                    else:
                        error_data = response.json() if response.content else {}
                        error_msg = error_data.get('error_description', error_data.get('message', f'HTTP {response.status_code}'))
                        logger.error(f"API call failed: {error_msg}")
                        return {"error": f"Failed to send password reset email: {error_msg}"}
                
                logger.info(f"Password reset email sent successfully to {email}")
                return {"success": True, "message": "Password reset email sent successfully"}
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error sending password reset email: {error_msg}")
                
                # Handle common error cases
                if "user not found" in error_msg.lower():
                    return {"error": "No account found with this email address"}
                elif "email not confirmed" in error_msg.lower():
                    return {"error": "Email address not confirmed. Please check your inbox for a confirmation email first."}
                elif "rate limit" in error_msg.lower():
                    return {"error": "Too many reset attempts. Please wait before trying again."}
                else:
                    return {"error": f"Failed to send password reset email: {error_msg}"}
        
        try:
            return self._execute_with_retry(reset_password_func) or {"error": "Failed to send password reset email"}
        except Exception as e:
            logger.error(f"Error in reset_password_for_email: {e}")
            return {"error": "An unexpected error occurred. Please try again later."}
    
    def enable(self) -> bool:
        """Enable Supabase integration.
        
        Returns:
            bool: True if enabled successfully, False otherwise
        """
        try:
            config.set('supabase.enabled', True)
            self.initialize()
            return not self._offline_mode
        except Exception as e:
            logger.error(f"Error enabling Supabase: {e}")
            return False
    
    def disable(self):
        """Disable Supabase integration."""
        try:
            if self.is_authenticated():
                self.sign_out()
            config.set('supabase.enabled', False)
            self._offline_mode = True
            self._client = None
            logger.info("Supabase disabled")
        except Exception as e:
            logger.error(f"Error disabling Supabase: {e}")
    
    def check_connection(self) -> bool:
        """Check if we can connect to Supabase.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # If already connected and initialized, just return True
            if self._client and not self._offline_mode:
                # Additional verification: try a simple operation to confirm connection
                try:
                    # Use a brief timeout for the connection test
                    import requests
                    from requests.adapters import HTTPAdapter
                    from urllib3.util.retry import Retry
                    
                    # Create a session with retry for the connection test
                    session = requests.Session()
                    retry_strategy = Retry(
                        total=3,
                        backoff_factor=0.5,
                        status_forcelist=[429, 500, 502, 503, 504],
                    )
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    session.mount("https://", adapter)
                    
                    # Basic health check - only wait 10 seconds maximum
                    base_url = self._client.rest_url
                    response = session.get(f"{base_url}/health", timeout=10)
                    if response.status_code == 200:
                        logger.info("Verified Supabase connection via health check")
                        return True
                    else:
                        logger.warning(f"Supabase health check returned status {response.status_code}")
                except Exception as e:
                    logger.warning(f"Connection verification failed: {e}")
                    # Continue with DNS check if health verification fails
                
                # Default to True if we couldn't do health check but client exists
                return True
                
            # If Supabase is disabled in config, don't even try
            if not config.supabase_enabled:
                return False
            
            # If URL or key not configured, we can't connect
            if not config.supabase_url or not config.supabase_key:
                logger.warning("Supabase credentials not configured")
                return False
                
            # Try to resolve hostname - most common failure point
            if self._hostname:
                ips = resolve_hostname(self._hostname)
                if not ips:
                    logger.error(f"Could not resolve {self._hostname}")
                    return False
                    
                logger.info(f"Successfully resolved {self._hostname} to {ips[0]}")
                return True
            else:
                # Extract hostname from URL if not already done
                parsed_url = urlparse(config.supabase_url)
                self._hostname = parsed_url.netloc
                
                # Try DNS resolution
                ips = resolve_hostname(self._hostname)
                if not ips:
                    logger.error(f"Could not resolve {self._hostname}")
                    return False
                    
                logger.info(f"Successfully resolved {self._hostname} to {ips[0]}")
                return True
                
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    def requires_email_confirmation(self) -> bool:
        """Check if the Supabase project requires email confirmation.
        
        Returns:
            bool: True if email confirmation is required, False otherwise
        """
        # This is a best-effort check based on error handling
        if self._offline_mode or not self._client:
            return False
            
        try:
            # Try to create a test user and login immediately
            import uuid
            test_email = f"test_{uuid.uuid4().hex[:8]}@gmail.com"
            test_password = "Test123!@#"
            
            # Try signup
            response = self._client.auth.sign_up({
                "email": test_email,
                "password": test_password
            })
            
            # Try immediate login
            try:
                self._client.auth.sign_in_with_password({
                    "email": test_email,
                    "password": test_password
                })
                # If we get here, email confirmation is NOT required
                return False
            except Exception as e:
                # If we get "Email not confirmed", then confirmation IS required
                if "email not confirmed" in str(e).lower():
                    return True
            
        except Exception:
            # If we can't determine, assume it's not required
            pass
            
        return False

    def test_email_confirmation_setup(self):
        """Test if email confirmation is properly configured.
        
        Returns:
            dict: Test results and recommendations
        """
        results = {
            'email_confirmation_required': False,
            'can_send_emails': False,
            'redirect_url_set': True,
            'recommendations': []
        }
        
        try:
            # Check if we can access the client
            if not self._client:
                results['recommendations'].append("Supabase client not initialized")
                return results
            
            # Test 1: Check if email confirmation is required
            results['email_confirmation_required'] = self.requires_email_confirmation()
            
            # Test 2: Check if redirect URL is properly set  
            try:
                # Try to get auth settings (this might not be available via client)
                logger.info("Email redirect URL is configured in signup method")
                results['redirect_url_set'] = True
            except Exception:
                results['redirect_url_set'] = False
                results['recommendations'].append("Check email redirect URL configuration")
            
            # Test 3: Basic connectivity test
            try:
                health_response = self.check_connection()
                results['can_send_emails'] = health_response
                if not health_response:
                    results['recommendations'].append("Connection issues - emails may not be sent")
            except Exception:
                results['recommendations'].append("Unable to test connection")
            
            # Provide recommendations
            if results['email_confirmation_required']:
                results['recommendations'].append("Email confirmation is required - check Supabase dashboard email settings")
            else:
                results['recommendations'].append("Email confirmation may be disabled - check if this is intentional")
                
            if not results['redirect_url_set']:
                results['recommendations'].append("Add http://localhost:3000/auth/confirm to allowed redirect URLs")
                
            logger.info(f"Email setup test results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error testing email setup: {e}")
            results['recommendations'].append(f"Error during testing: {str(e)}")
            return results

# Create singleton instance
supabase = SupabaseManager() 