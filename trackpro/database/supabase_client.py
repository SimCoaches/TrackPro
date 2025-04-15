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
        return _supabase_manager.client
    except Exception as e:
        logger.error(f"Error getting Supabase client: {e}")
        return None

# DNS cache to avoid repeated lookups
DNS_CACHE = {}
DNS_CACHE_LOCK = threading.Lock()

def resolve_hostname(hostname):
    """Resolve hostname to IP with caching."""
    with DNS_CACHE_LOCK:
        if hostname in DNS_CACHE and DNS_CACHE[hostname]['expiry'] > time.time():
            logger.debug(f"Using cached DNS for {hostname}")
            return DNS_CACHE[hostname]['ips']
    
    try:
        logger.debug(f"Resolving hostname: {hostname}")
        ips = socket.gethostbyname_ex(hostname)[2]
        if ips:
            # Cache for 1 hour with some jitter to avoid synchronized expiry
            expiry = time.time() + 3600 + random.randint(0, 300)
            with DNS_CACHE_LOCK:
                DNS_CACHE[hostname] = {'ips': ips, 'expiry': expiry}
            logger.debug(f"Resolved {hostname} to {ips}")
            return ips
    except Exception as e:
        logger.error(f"Failed to resolve {hostname}: {e}")
    
    return None

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
        
        # Try to restore session from file
        self._restore_session()
        
        # Initialize the client
        self.initialize()
    
    def _restore_session(self):
        """Restore session from file if available."""
        try:
            if os.path.exists(self._auth_file):
                with open(self._auth_file, 'r') as f:
                    auth_data = json.load(f)
                
                if auth_data.get('access_token') and auth_data.get('refresh_token'):
                    logger.info("Found saved authentication session")
                    self._saved_auth = auth_data
                    return True
            
            logger.info("No saved authentication session found")
            self._saved_auth = None
            return False
        except Exception as e:
            logger.error(f"Error restoring authentication session: {e}")
            self._saved_auth = None
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
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._auth_file), exist_ok=True)
            
            # Extract tokens from response
            session = response.session if hasattr(response, 'session') else response
            auth_data = {
                'access_token': session.access_token if hasattr(session, 'access_token') else None,
                'refresh_token': session.refresh_token if hasattr(session, 'refresh_token') else None,
                'expires_at': session.expires_at if hasattr(session, 'expires_at') else None,
                'remember_me': remember_me  # Store the remember_me preference
            }
            
            # Save to file
            with open(self._auth_file, 'w') as f:
                json.dump(auth_data, f)
            
            logger.info(f"Authentication session saved with remember_me={remember_me}")
            self._saved_auth = auth_data
            return True
        except Exception as e:
            logger.error(f"Error saving authentication session: {e}")
            return False
    
    def _clear_session(self):
        """Clear the saved session."""
        try:
            if os.path.exists(self._auth_file):
                os.remove(self._auth_file)
                logger.info("Authentication session cleared")
            self._saved_auth = None
            return True
        except Exception as e:
            logger.error(f"Error clearing authentication session: {e}")
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
            ips = resolve_hostname(self._hostname)
            if ips:
                self._cached_ip = ips[0]
                logger.info(f"Resolved {self._hostname} to {self._cached_ip}")
            
            # Create Supabase client
            logger.info("Initializing Supabase client...")
            try:
                # Use retry strategy for client creation
                def create_and_test_client():
                    # Create client without extra options to avoid 'headers' error
                    client = create_client(url, key)
                    return client
                
                # Explicitly clear old client to avoid reusing
                self._client = None
                
                # Create new client
                self._client = self._retry_strategy.execute(create_and_test_client)
                
                # If we have a saved session, try to restore it
                if self._saved_auth and self._saved_auth.get('access_token'):
                    logger.info("Attempting to restore saved session...")
                    try:
                        # Set the session on the client - include refresh token if available
                        if self._saved_auth.get('refresh_token'):
                            # Fix: Pass access_token and refresh_token as direct parameters
                            # (not as a dictionary) to match the client's API expectations
                            self._client.auth.set_session(
                                self._saved_auth.get('access_token'),
                                self._saved_auth.get('refresh_token')
                            )
                            logger.info("Session restored successfully using access and refresh tokens")
                        else:
                            # Refresh token is missing, cannot restore session reliably
                            logger.warning("Cannot restore session: Refresh token is missing from saved authentication data.")
                            # Do not attempt to set session without refresh token
                            # Let the subsequent get_session() call handle the state
                    except Exception as e:
                        logger.warning(f"Failed to restore session: {e}")
                
                # Test connection with a simple operation
                try:
                    # Just check if we can access the auth API
                    logger.info("Testing connection to Supabase...")
                    self._client.auth.get_session()
                    self._offline_mode = False
                    logger.info("Supabase client initialized and connected successfully")
                except Exception as e:
                    logger.warning(f"Connected but session retrieval failed: {e}")
                    # Still consider it a success if we got this far
                    self._offline_mode = False
                    logger.info("Supabase client initialized (with limited functionality)")
            except Exception as e:
                logger.error(f"Failed to create/test Supabase client after retries: {e}")
                self._offline_mode = True
                self._client = None
                return
            
        except Exception as e:
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
                return self._client.auth.get_user() is not None
            
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
    
    def sign_out(self, force_clear=False):
        """Sign out the current user.
        
        Args:
            force_clear: If True, always clear the saved session regardless of remember_me preference
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign out - Supabase is not connected")
            return
        
        logger.info("Signing out user")
        
        def signout_func():
            self._client.auth.sign_out()
            
            # Check if we should clear the saved session
            should_clear = force_clear
            
            # If not forcing, check the remember_me preference
            if not force_clear and self._saved_auth and 'remember_me' in self._saved_auth:
                remember_me = self._saved_auth.get('remember_me', False)
                # Only clear if remember_me is False
                should_clear = not remember_me
                logger.info(f"Remember me preference is {remember_me}, {'clearing' if should_clear else 'keeping'} session data")
            else:
                # Default to clearing if remember_me not found
                should_clear = True
            
            # Clear saved session if needed
            if should_clear:
                self._clear_session()
                logger.info("Session cleared during sign out")
            else:
                logger.info("Session retained for remember me")
            
            logger.info("Sign out successful")
        
        self._execute_with_retry(signout_func)
    
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

# Create singleton instance
supabase = SupabaseManager() 