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
    
    def _save_session(self, response):
        """Save session to file for persistence between app restarts."""
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
                'expires_at': session.expires_at if hasattr(session, 'expires_at') else None
            }
            
            # Save to file
            with open(self._auth_file, 'w') as f:
                json.dump(auth_data, f)
            
            logger.info("Authentication session saved")
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
            
            if not url or not key:
                logger.warning("Supabase credentials not configured")
                self._offline_mode = True
                return
            
            logger.info(f"Got Supabase URL: {url[:30]}...")  # Only log first part of URL for security
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
                
                self._client = self._retry_strategy.execute(create_and_test_client)
                
                # Test connection with a simple operation
                try:
                    # Just check if we can access the auth API
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
    
    def sign_up(self, email: str, password: str) -> AuthResponse:
        """Sign up a new user.
        
        Args:
            email: The user's email
            password: The user's password
            
        Returns:
            AuthResponse: The signup response
        """
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign up - Supabase is not connected")
            return None
        
        logger.info(f"Attempting signup for email: {email}")
        
        def signup_func():
            response = self._client.auth.sign_up({
                "email": email,
                "password": password
            })
            logger.info("Signup successful")
            # Save session for persistence
            self._save_session(response)
            return response
        
        try:
            return self._execute_with_retry(signup_func)
        except Exception as e:
            # Check if this is an email format error
            if "invalid" in str(e).lower() and "email" in str(e).lower():
                logger.error(f"Email format error: {e}")
                raise ValueError(f"Invalid email format: {email}. Try using a standard email address like yourname@gmail.com")
            # Other errors
            logger.error(f"Signup error: {e}")
            raise
    
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
    
    def sign_out(self):
        """Sign out the current user."""
        if self._offline_mode or not self._client:
            logger.warning("Cannot sign out - Supabase is not connected")
            return
        
        logger.info("Signing out user")
        
        def signout_func():
            self._client.auth.sign_out()
            # Clear saved session
            self._clear_session()
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