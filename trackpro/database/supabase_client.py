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
from pathlib import Path
import jwt

# Import secure session manager
try:
    from ..auth.secure_session import SecureSessionManager
    SECURE_SESSION_AVAILABLE = True
except ImportError:
    SECURE_SESSION_AVAILABLE = False
    SecureSessionManager = None

logger = logging.getLogger(__name__)

# Global variables for singleton pattern
_supabase_manager = None
_supabase_manager_lock = threading.Lock()
_initialization_complete = False  # Add flag to prevent duplicate initialization

# Get Supabase configuration
SUPABASE_URL = config.supabase_url
SUPABASE_KEY = config.supabase_key

def get_supabase_client():
    """Get the global Supabase client instance.
    
    Returns:
        Client: The Supabase client instance, or None if not initialized.
    """
    global _supabase_manager, _initialization_complete
    
    # Fast path: if already initialized, return immediately
    if _supabase_manager is not None and _initialization_complete:
        return _supabase_manager.client if _supabase_manager else None
    
    # Slow path: thread-safe initialization with reduced timeout for faster startup
    try:
        # Use much shorter timeout to prevent hanging during startup
        acquired = _supabase_manager_lock.acquire(timeout=1.0)  # Reduced from 2s to 1s
        if not acquired:
            logger.error("⚠️ STARTUP FIX: Supabase initialization timed out - continuing without client")
            return None
        
        try:
            # Double-check pattern: another thread might have initialized it
            if _supabase_manager is None:
                try:
                    logger.info("Initializing Supabase manager for the first time")
                    _supabase_manager = SupabaseManager()
                except Exception as e:
                    logger.error(f"Error initializing Supabase manager: {e}")
                    # Create a dummy manager to prevent repeated initialization attempts
                    _supabase_manager = type('DummyManager', (), {'client': None})()
                    _initialization_complete = True
                    return None
            
            # Force initialization immediately for authentication operations
            if _supabase_manager and hasattr(_supabase_manager, '_initialization_deferred') and _supabase_manager._initialization_deferred:
                logger.info("🔄 Force initializing Supabase client on first access")
                _supabase_manager._initialization_deferred = False
                try:
                    _supabase_manager.initialize()
                    _initialization_complete = True
                    logger.info("✅ Supabase client initialization completed successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {e}")
                    _initialization_complete = True
                    return None
            
            # Return the client (this will trigger initialization if needed)
            client = _supabase_manager.client if _supabase_manager else None
            if client is None and _supabase_manager:
                logger.warning("Supabase manager exists but client is None - attempting reinitialization")
                try:
                    _supabase_manager.initialize()
                    client = _supabase_manager.client
                except Exception as e:
                    logger.error(f"Reinitialization failed: {e}")
            
            return client
        finally:
            _supabase_manager_lock.release()
            
    except Exception as e:
        logger.error(f"⚠️ STARTUP FIX: Unexpected error in Supabase client initialization: {e}")
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
        # Use even shorter timeout for startup optimization
        import socket
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(1.0)  # Reduced to 1 second for ultra-fast startup
        
        # Try to resolve the hostname
        logger.info(f"[DNS] Resolving {hostname} with 1s timeout...")
        start_time = time.time()
        
        # Use faster resolution method
        try:
            # Try simple gethostbyname first (faster)
            ip = socket.gethostbyname(hostname)
            ips = [ip]
        except:
            # Fallback to full resolution
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
        logger.error(f"[DNS] Timeout resolving {hostname} after 1 second")
        return None
    except Exception as e:
        logger.error(f"[DNS] Unexpected error resolving {hostname}: {e}")
        return None
    finally:
        # Reset socket timeout to original value
        socket.setdefaulttimeout(old_timeout)

class RetryStrategy:
    """Implements exponential backoff retry strategy."""
    
    def __init__(self, max_retries=2, base_delay=0.5, max_delay=2.0):  # Faster for startup
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
        # Start online when Supabase is enabled and credentials are present
        try:
            credentials_present = bool(config.supabase_url) and bool(config.supabase_key)
            self._offline_mode = not (config.supabase_enabled and credentials_present)
            if self._offline_mode:
                logger.info("Supabase starting in offline mode (disabled or missing credentials)")
            else:
                logger.info("Supabase starting in online mode (credentials found and enabled)")
        except Exception as init_flag_err:
            logger.warning(f"Could not determine startup online state, defaulting offline: {init_flag_err}")
            self._offline_mode = True
        self._retry_strategy = RetryStrategy()
        self._hostname = None
        self._cached_ip = None
        self._auth_file = os.path.join(os.path.expanduser("~"), ".trackpro", "auth.json")
        self._saved_auth = None  # Initialize to None to prevent AttributeError
        self._realtime_channels_supported = False
        
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
        
        # REMOVED: Don't restore session during initialization to prevent hanging
        # Session restoration will happen when client is first accessed
        # self._restore_session()
        
        # Defer initialization to speed up startup - client will be created on first use
        self._initialization_deferred = True
        # Token monitor state
        self._token_monitor_thread = None
        self._token_monitor_stop = False
    
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
                    # Auto-heal: back up corrupted plaintext and remove to prevent repeated errors
                    try:
                        backup_path = plaintext_file.with_suffix(plaintext_file.suffix + ".bak")
                        try:
                            if backup_path.exists():
                                backup_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        plaintext_file.rename(backup_path)
                        logger.info(f"Backed up corrupted plaintext session to {backup_path}")
                    except Exception as backup_err:
                        logger.warning(f"Could not back up corrupted plaintext session: {backup_err}")
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
    
    def _load_session(self):
        """Load session from file."""
        try:
            # Try secure session first
            if self._secure_session:
                auth_data = self._secure_session.load_session()
                if auth_data and auth_data.get('access_token'):
                    logger.info("✅ Found saved authentication session (encrypted)")
                    return auth_data
            
            # Fallback to plaintext session
            if os.path.exists(self._auth_file):
                logger.info(f"📁 Found auth file at: {self._auth_file}")
                try:
                    with open(self._auth_file, 'r') as f:
                        auth_data = json.load(f)
                except Exception as json_err:
                    logger.error(f"❌ Error loading authentication session: {json_err}")
                    # Auto-heal corrupted plaintext: back up and ignore
                    try:
                        from pathlib import Path as _Path
                        p = _Path(self._auth_file)
                        backup = p.with_suffix(p.suffix + ".bak")
                        try:
                            if backup.exists():
                                backup.unlink(missing_ok=True)
                        except Exception:
                            pass
                        p.rename(backup)
                        logger.info(f"Backed up corrupted auth.json to {backup}")
                    except Exception as _bke:
                        logger.warning(f"Could not back up corrupted auth.json: {_bke}")
                    return None
                
                # Debug logging
                logger.info(f"📄 Loaded auth data: access_token={'present' if auth_data.get('access_token') else 'missing'}, refresh_token={'present' if auth_data.get('refresh_token') else 'missing'}, remember_me={auth_data.get('remember_me', 'not set')}")
                
                # Check if we have the minimum required data
                if auth_data.get('access_token'):
                    logger.info("✅ Found saved authentication session (plaintext)")
                    return auth_data
                else:
                    logger.warning("❌ Auth file exists but has no access token")
            else:
                logger.info(f"📁 No auth file found at: {self._auth_file}")
            
            logger.info(f"No saved authentication session found at: {self._auth_file}")
            return None
        except Exception as e:
            logger.error(f"❌ Error loading authentication session: {e}")
            return None
    
    def _restore_session(self):
        """Attempt to restore a saved session."""
        try:
            logger.info("Attempting to restore saved session...")
            
            # Check if we have a saved session
            session_data = self._load_session()
            if not session_data:
                logger.info("No saved session found")
                return False
            
            # Validate session data before attempting restoration
            access_token = session_data.get('access_token')
            refresh_token = session_data.get('refresh_token')
            
            if not access_token:
                logger.warning("No access token found in session data")
                return False
            
            # Check if the access token appears to be corrupted
            if isinstance(access_token, str) and ('+00:00' in access_token or len(access_token) < 50):
                logger.warning("Access token appears to be corrupted - clearing session")
                self._clear_session()
                return False
            
            # Ensure client is available before attempting session restoration
            if not self._client:
                logger.warning("Client not available for session restoration")
                return False
            
            # Check if session is expired
            if self._is_token_expired(session_data.get('expires_at')):
                logger.info("Access token appears to be expired")
                logger.info("Access token expired or invalid, attempting to refresh session")
                
                # Try to refresh the session - only attempt once to avoid multiple failures
                if not self._attempt_session_refresh(session_data):
                    logger.warning("Session refresh failed - user will need to re-authenticate")
                    # Clear the corrupted session data
                    self._clear_session()
                    return False
            
            # Set the session
            try:
                if refresh_token:
                    self._client.auth.set_session(access_token, refresh_token)
                else:
                    # Try with just access token if no refresh token
                    try:
                        self._client.auth.set_session(access_token)
                    except TypeError:
                        # Fallback to empty refresh token
                        self._client.auth.set_session(access_token, "")
                
                logger.info("Session restored successfully")
                return True
            except Exception as e:
                logger.error(f"Error setting session: {e}")
                # Clear corrupted session data
                self._clear_session()
                return False
                
        except Exception as e:
            logger.error(f"Error restoring session: {e}")
            return False
    
    def _attempt_session_refresh(self, session_data):
        """Attempt to refresh the session - only try once to avoid multiple failures."""
        refresh_token = session_data.get('refresh_token')
        if not refresh_token:
            logger.warning("No refresh token available")
            return False
        
        # Check if refresh token appears to be corrupted
        if isinstance(refresh_token, str) and ('+00:00' in refresh_token or len(refresh_token) < 50):
            logger.warning("Refresh token appears to be corrupted")
            return False
        
        # Only try one refresh method to avoid multiple failed attempts
        try:
            logger.info("Attempting session refresh using manual_refresh")
            response = self._client.auth.refresh_session(refresh_token)
            if response and response.session:
                logger.info("Session refresh successful")
                return True
        except Exception as e:
            error_msg = str(e)
            if "Already Used" in error_msg or "invalid" in error_msg.lower():
                logger.warning(f"Refresh token is invalid or already used: {e}")
                # Clear the corrupted session data
                self._clear_session()
            else:
                logger.warning(f"Manual session refresh failed: {e}")
        
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
                # Check if this is a JWT token instead of a timestamp
                if expires_at.count('.') == 2 and len(expires_at) > 100:
                    # This appears to be a JWT token, not a timestamp
                    logger.warning("Received JWT token instead of timestamp for expiration check")
                    return True  # Assume expired for corrupted tokens
                
                # Try to parse as ISO format timestamp
                try:
                    # Clean up any corrupted characters that might be in the timestamp
                    cleaned_timestamp = expires_at.replace('+00:00', '').replace('+00', '')
                    expiry_time = datetime.fromisoformat(cleaned_timestamp.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid timestamp format: {expires_at}")
                    return True  # Assume expired for invalid timestamps
            else:
                return True  # Unknown format, assume expired
            
            # CRITICAL FIX: Reduce buffer to 30 seconds to avoid premature token invalidation
            # The previous 2-minute buffer was too aggressive and was causing unnecessary re-authentication
            import time
            current_time = datetime.fromtimestamp(time.time())
            buffer_seconds = 30  # Only 30 seconds buffer instead of 2 minutes
            
            is_expired = (expiry_time.timestamp() - current_time.timestamp()) < buffer_seconds
            
            if is_expired:
                logger.info(f"Token expired: current={current_time}, expiry={expiry_time}, buffer={buffer_seconds}s")
            else:
                remaining_seconds = expiry_time.timestamp() - current_time.timestamp()
                logger.debug(f"Token valid for {remaining_seconds:.0f} more seconds")
            
            return is_expired
            
        except Exception as e:
            logger.warning(f"Error checking token expiration: {e}")
            return True  # Assume expired on error
    
    def _restore_session_safely(self):
        """Safely restore session without consuming refresh tokens unnecessarily.
        
        Returns:
            bool: True if session was restored successfully, False otherwise
        """
        # Ensure a client exists
        if not self._client:
            return False

        # If we have a secure/plaintext session on disk but _saved_auth is empty,
        # load it now so we can restore the session for auth checks.
        if not self._saved_auth:
            try:
                loaded = self._load_session()
                if loaded and loaded.get('access_token'):
                    self._saved_auth = loaded
                    logger.info("Loaded saved session into memory for restoration")
                else:
                    # No saved auth available
                    return False
            except Exception as e:
                logger.warning(f"Failed to load saved session: {e}")
                return False
        
        access_token = self._saved_auth.get('access_token')
        refresh_token = self._saved_auth.get('refresh_token')
        expires_at = self._saved_auth.get('expires_at')
        remember_me = self._saved_auth.get('remember_me', True)  # Default to True for backward compatibility
        
        if not access_token:
            logger.warning("No access token found in saved session")
            return False
        
        logger.info(f"Attempting session restoration (remember_me={remember_me})")
        
        try:
            # First, check if the current access token is still valid
            is_expired = self._is_token_expired(expires_at)
            
            if not is_expired:
                logger.info("Access token appears to still be valid, attempting direct restoration")
                try:
                    # STARTUP OPTIMIZATION: Use faster session restoration method
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
                    except Exception as session_error:
                        logger.warning(f"Session restoration failed: {session_error}")
                        # Don't just pass - attempt refresh token restoration below
                        raise session_error
                    
                    # Test if the session works by making a simple call
                    session = self._client.auth.get_session()
                    if session and hasattr(session, 'user') and session.user:
                        logger.info("Session restored successfully with existing tokens")
                        # Update session data if needed (in case tokens were refreshed)
                        if hasattr(session, 'access_token') and session.access_token != access_token:
                            logger.info("Session tokens were automatically refreshed during restoration")
                            self._save_session(session, remember_me)
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
                refresh_success = False
                
                # Try multiple refresh methods with retry logic
                refresh_attempts = [
                    ("refresh_session", lambda: getattr(self._client.auth, 'refresh_session', lambda: None)()),
                    ("refresh", lambda: getattr(self._client.auth, 'refresh', lambda: None)()),
                    ("manual_refresh", self._attempt_manual_refresh)
                ]
                
                for method_name, refresh_func in refresh_attempts:
                    if refresh_success:
                        break
                        
                    try:
                        logger.info(f"Attempting session refresh using {method_name}")
                        if method_name == "manual_refresh":
                            result = refresh_func(access_token, refresh_token)
                        else:
                            result = refresh_func()
                        
                        if result and hasattr(result, 'session') and result.session:
                            logger.info(f"Session refreshed successfully using {method_name}")
                            self._save_session(result, remember_me)
                            self._sync_auth_state_with_modules()
                            refresh_success = True
                            return True
                        elif result and hasattr(result, 'access_token'):
                            # Handle case where result is the session directly
                            logger.info(f"Session refreshed successfully using {method_name} (direct session)")
                            # Create a mock response for saving
                            class MockResponse:
                                def __init__(self, session):
                                    self.session = session
                            self._save_session(MockResponse(result), remember_me)
                            self._sync_auth_state_with_modules()
                            refresh_success = True
                            return True
                    except Exception as e:
                        logger.warning(f"Session refresh using {method_name} failed: {e}")
                        continue
                
                if not refresh_success:
                    logger.warning("All session refresh attempts failed")
                    
                    # CRITICAL FIX: If remember_me is True, don't clear the session completely
                    # Instead, preserve the session data for future attempts while clearing active session
                    if remember_me:
                        logger.info("remember_me=True: Preserving session data for future login attempts")
                        # Clear the client session but keep the saved auth data
                        try:
                            self._client.auth.sign_out()
                        except:
                            pass
                        # Don't call _clear_session_conditionally which might remove the session file
                        return False
                    else:
                        logger.info("remember_me=False: Clearing session data after refresh failure")
                        self._clear_session_conditionally()
                        return False
            else:
                logger.warning("No refresh token available for session restoration")
                
                # If remember_me is True, preserve the session for manual re-authentication
                if remember_me:
                    logger.info("remember_me=True: No refresh token but preserving session data")
                    return False
                else:
                    logger.info("remember_me=False: Clearing session due to missing refresh token")
                    self._clear_session_conditionally()
                    return False
                    
        except Exception as e:
            logger.error(f"Unexpected error during session restoration: {e}")
            # On unexpected errors, preserve remember_me sessions but clear others
            if remember_me:
                logger.info("remember_me=True: Preserving session data despite restoration error")
                return False
            else:
                logger.info("remember_me=False: Clearing session due to restoration error")
                self._clear_session_conditionally()
                return False
        finally:
            # After any restoration attempt, (re)propagate auth and start token monitor
            try:
                self._set_realtime_auth_token_if_available()
            except Exception:
                pass
            try:
                self._start_token_monitor()
            except Exception as monitor_err:
                logger.debug(f"Token monitor start failed: {monitor_err}")
    
    def _attempt_manual_refresh(self, access_token, refresh_token):
        """Attempt manual session refresh using tokens.
        
        Returns:
            Session object if successful, None otherwise
        """
        try:
            # Create a temporary session with the refresh token to trigger refresh
            self._client.auth.set_session(access_token, refresh_token)
            
            # Now try to get the session which should refresh automatically
            refreshed_session = self._client.auth.get_session()
            if refreshed_session and hasattr(refreshed_session, 'access_token'):
                logger.info("Manual session refresh successful")
                return refreshed_session
            return None
        except Exception as e:
            logger.warning(f"Manual session refresh failed: {e}")
            return None
    
    def _save_session(self, response, remember_me=True):
        """Save session to file for persistence between app restarts.
        
        Args:
            response: The authentication response containing session data
            remember_me: Whether to remember the session after the app is closed (default: True)
        """
        try:
            if not response:
                logger.warning("No response provided to _save_session")
                return False
            
            # Extract tokens from response
            session = response.session if hasattr(response, 'session') else response
            auth_data = {
                'access_token': session.access_token if hasattr(session, 'access_token') else None,
                'refresh_token': session.refresh_token if hasattr(session, 'refresh_token') else None,
                'expires_at': session.expires_at if hasattr(session, 'expires_at') else None,
                'remember_me': remember_me  # Store the remember_me preference
            }
            
            # Debug logging
            logger.info(f"🔐 SAVING SESSION: access_token={'present' if auth_data['access_token'] else 'missing'}, refresh_token={'present' if auth_data['refresh_token'] else 'missing'}, remember_me={remember_me}")
            
            # Validate that we have the required data
            if not auth_data['access_token']:
                logger.error("❌ Cannot save session - no access token found in response")
                return False
            
            # Try secure session first
            if self._secure_session:
                success = self._secure_session.save_session(auth_data)
                if success:
                    logger.info(f"✅ Authentication session saved securely with remember_me={remember_me}")
                    self._saved_auth = auth_data
                    return True
                else:
                    logger.warning("Failed to save session securely, falling back to plaintext")
            
            # Fallback to plaintext session
            os.makedirs(os.path.dirname(self._auth_file), exist_ok=True)
            with open(self._auth_file, 'w') as f:
                json.dump(auth_data, f)
            
            logger.info(f"✅ Authentication session saved (plaintext) with remember_me={remember_me} to {self._auth_file}")
            self._saved_auth = auth_data
            return True
        except Exception as e:
            logger.error(f"❌ Error saving authentication session: {e}")
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
                logger.info("Forcing session clear (ignoring remember_me preference)")
                return self._clear_session()
            
            # Check remember_me preference
            if self._saved_auth and 'remember_me' in self._saved_auth:
                remember_me = self._saved_auth.get('remember_me', False)
                if remember_me:
                    logger.info("Session has remember_me=True, preserving session data for future authentication")
                    # CRITICAL IMPROVEMENT: Don't clear the session file, but clear the in-memory client session
                    # This allows users to re-authenticate without re-entering credentials
                    try:
                        if self._client and hasattr(self._client, 'auth'):
                            self._client.auth.sign_out()
                            logger.info("Cleared active client session but preserved login credentials")
                    except Exception as e:
                        logger.warning(f"Error clearing active client session: {e}")
                    
                    # Sync auth state to reflect signed-out status while keeping credentials
                    self._sync_auth_state_with_modules()
                    return False  # Session file kept
                else:
                    logger.info("Session has remember_me=False, clearing all session data")
                    return self._clear_session()
            else:
                # No remember_me preference found - for backward compatibility, be conservative
                # and keep the session (assume remember_me=True for existing sessions)
                logger.info("No remember_me preference found - defaulting to preserve session for compatibility")
                try:
                    if self._client and hasattr(self._client, 'auth'):
                        self._client.auth.sign_out()
                        logger.info("Cleared active client session but preserved login credentials (compatibility mode)")
                except Exception as e:
                    logger.warning(f"Error clearing active client session: {e}")
                
                self._sync_auth_state_with_modules()
                return False  # Session file kept
                
        except Exception as e:
            logger.error(f"Error in conditional session clearing: {e}")
            # On error, be very conservative and keep the session to avoid data loss
            logger.info("Error during conditional clearing - preserving session data to be safe")
            return False
    
    def initialize(self):
        """Initialize the Supabase client."""
        try:
            logger.info("Initializing Supabase client...")
            
            # Create the client
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # If client creation was successful, disable offline mode
            if self._client:
                self._offline_mode = False
                logger.info("✅ Supabase client created successfully, disabled offline mode")

                # Detect realtime channel support for Discord-like messaging
                try:
                    has_channel = hasattr(self._client, 'channel')
                    has_realtime_channel = hasattr(getattr(self._client, 'realtime', None), 'channel')
                    self._realtime_channels_supported = bool(has_channel or has_realtime_channel)
                    if self._realtime_channels_supported:
                        logger.info("✅ Realtime channels supported by client (channel API available)")
                    else:
                        logger.info("ℹ️ Realtime channels not exposed by client (channel API missing) - polling fallback will be used")
                except Exception:
                    self._realtime_channels_supported = False
            
            # REMOVED: Don't attempt session restoration during initialization
            # This can cause hanging if there are network issues
            # Session restoration will happen when client is first accessed
            # try:
            #     self._restore_session()
            # except Exception as e:
            #     logger.warning(f"Failed to restore session during initialization: {e}")
            
            # REMOVED: Don't test connection during initialization
            # This can cause hanging if there are network issues
            # try:
            #     self.check_connection()
            # except Exception as e:
            #     logger.warning(f"Connection test failed during initialization: {e}")
            
            logger.info("Supabase client initialized successfully")
            
            # Attempt to propagate auth token to realtime (safe if no session yet)
            try:
                self._set_realtime_auth_token_if_available()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}")
            # Don't set _client to None on error - keep the client even if some operations fail
            if self._client is None:
                logger.info("Supabase client initialization failed - client not available")
            else:
                logger.info("Supabase client initialized (with limited functionality)")
    
    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry strategy and offline fallback."""
        if self._offline_mode:
            logger.warning(f"Cannot execute {func.__name__} - Supabase is in offline mode")
            return None
        
        # Ensure client is available
        client = self.client
        if not client:
            logger.warning(f"Cannot execute {func.__name__} - Supabase client is not available")
            return None
        
        try:
            return self._retry_strategy.execute(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Operation {func.__name__} failed after retries: {e}")
            # If we get a connection error, we might need to refresh the client
            if isinstance(e, (socket.gaierror, ConnectionError, TimeoutError)):
                logger.info("Connection error detected, attempting to reinitialize client")
                self.initialize()
            else:
                # Handle JWT expired reactively and retry once
                try:
                    from postgrest.exceptions import APIError
                    if isinstance(e, APIError):
                        code = None
                        try:
                            code = e.code
                        except Exception:
                            msg = str(e)
                            code = 'PGRST301' if ('PGRST301' in msg or 'JWT expired' in msg) else None
                        if code == 'PGRST301':
                            logger.info("🔐 Detected JWT expired (PGRST301) – refreshing session and retrying")
                            try:
                                self._restore_session_safely()
                                self._set_realtime_auth_token_if_available()
                                try:
                                    from trackpro.community.community_manager import CommunityManager
                                    CommunityManager().refresh_realtime()
                                except Exception:
                                    pass
                                return self._retry_strategy.execute(func, *args, **kwargs)
                            except Exception as refresh_err:
                                logger.warning(f"JWT refresh retry failed: {refresh_err}")
                except Exception:
                    pass
            return None
    
    @property
    def client(self) -> Client:
        """Get the Supabase client.
        
        Returns:
            Client: The Supabase client, or None if not available
        """
        if self._offline_mode:
            return None
        
        # Deferred initialization - only initialize when first accessed
        if hasattr(self, '_initialization_deferred') and self._initialization_deferred:
            logger.info("🚀 STARTUP OPTIMIZATION: Performing deferred Supabase initialization on first access")
            self._initialization_deferred = False
            try:
                self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client during deferred initialization: {e}")
                return None
        
        # Force initialization if client is None but we're not in offline mode
        if self._client is None and not self._offline_mode:
            logger.info("🔄 Force initializing Supabase client")
            try:
                self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client during force initialization: {e}")
                return None
        
        # If we still don't have a client after initialization, something went wrong
        if self._client is None:
            logger.warning("Supabase client is None after initialization attempts")
            return None
        
        # Attempt session restoration when client is first accessed (non-blocking)
        if self._client and not hasattr(self, '_session_restored'):
            self._session_restored = True
            try:
                logger.info("🔄 Attempting safe session restoration on first client access")
                # Use the safer restoration flow that preserves refresh tokens and respects remember_me
                restored = self._restore_session_safely()
                if not restored:
                    logger.info("Safe session restoration did not complete; will rely on on-demand auth checks.")
                # After restoration attempt, propagate auth token to realtime if available
                try:
                    self._set_realtime_auth_token_if_available()
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Session restoration failed on first access: {e}")
        
        return self._client

    def _set_realtime_auth_token_if_available(self) -> None:
        """Propagate current auth access token to the realtime client if supported.

        This is required for Postgres Changes with RLS-protected tables to stream.
        Safe to call even if no session exists or the API is missing.
        """
        try:
            client = self._client
            if not client:
                return
            rt = getattr(client, 'realtime', None)
            if not rt or not hasattr(rt, 'set_auth'):
                return
            token = None
            auth = getattr(client, 'auth', None)
            if auth:
                # Try multiple shapes across versions
                try:
                    sess = auth.get_session()
                    token = getattr(sess, 'access_token', None) or (sess.get('access_token') if isinstance(sess, dict) else None)
                except Exception:
                    token = None
                if not token:
                    try:
                        current = getattr(auth, 'current_session', None)
                        if current:
                            token = getattr(current, 'access_token', None)
                    except Exception:
                        pass
            if token:
                try:
                    rt.set_auth(token)
                    logger.info("✅ Realtime auth token propagated to client")
                except Exception as e:
                    logger.debug(f"Realtime set_auth failed: {e}")
        except Exception:
            pass

    def _start_token_monitor(self) -> None:
        """Start a lightweight background thread to refresh tokens before expiry."""
        if self._token_monitor_thread and self._token_monitor_thread.is_alive():
            return

        def _monitor():
            try:
                while not self._token_monitor_stop:
                    try:
                        if not self._client:
                            time.sleep(5)
                            continue
                        sess = None
                        try:
                            sess = self._client.auth.get_session()
                        except Exception:
                            sess = None
                        if not sess:
                            time.sleep(15)
                            continue
                        expires_at = getattr(sess, 'expires_at', None)
                        if not expires_at:
                            time.sleep(30)
                            continue
                        from datetime import datetime
                        now_ts = time.time()
                        try:
                            exp_ts = float(expires_at)
                        except Exception:
                            try:
                                exp_ts = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00')).timestamp()
                            except Exception:
                                exp_ts = now_ts + 3600
                        seconds_left = exp_ts - now_ts
                        # Refresh if < 120s remaining
                        if seconds_left < 120:
                            logger.info(f"🔐 Token near expiry ({int(seconds_left)}s left) – refreshing session")
                            try:
                                self._restore_session_safely()
                                self._set_realtime_auth_token_if_available()
                                try:
                                    from trackpro.community.community_manager import CommunityManager
                                    CommunityManager().refresh_realtime()
                                except Exception:
                                    pass
                            except Exception as e:
                                logger.warning(f"Background token refresh failed: {e}")
                            time.sleep(30)
                            continue
                        time.sleep(max(5, min(30, int(seconds_left - 60))))
                    except Exception:
                        time.sleep(15)
            except Exception:
                pass

        self._token_monitor_stop = False
        import threading as _threading
        self._token_monitor_thread = _threading.Thread(target=_monitor, name="SupabaseTokenMonitor", daemon=True)
        self._token_monitor_thread.start()
    
    def is_authenticated(self) -> bool:
        """Check if a user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        try:
            # If we're in offline mode but configuration says Supabase is enabled and
            # credentials are present, attempt a quick initialization to recover.
            if self._offline_mode:
                try:
                    if config.supabase_enabled and config.supabase_url and config.supabase_key:
                        logger.info("Auth check: offline mode detected with credentials present; attempting initialization")
                        self.initialize()
                except Exception as init_err:
                    logger.warning(f"Auth check: initialization attempt while offline failed: {init_err}")
                # If still offline after attempt, bail out early
                if self._offline_mode:
                    return False

            # Fast path: check secure session first, then plaintext session
            has_secure_session = False
            if self._secure_session:
                try:
                    sec_info = self._secure_session.get_session_info()
                    has_secure_session = bool(sec_info.get('session_exists'))
                except Exception:
                    has_secure_session = False
            has_plain_session = os.path.exists(self._auth_file)

            if not has_secure_session and not has_plain_session:
                logger.info("🔐 Fast path: No saved session (secure or plaintext) - not authenticated")
                return False
            
            # Ensure client initialization AND trigger safe session restoration by
            # accessing the `client` property (it performs deferred init + restore).
            client = self.client
            if self._offline_mode or not client:
                return False
            
            def check_auth():
                user_response = client.auth.get_user()
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
        try:
            def get_user_func():
                return self._client.auth.get_user()
            
            return self._execute_with_retry(get_user_func)
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
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
        try:
            # Ensure client is initialized
            if hasattr(self, '_initialization_deferred') and self._initialization_deferred:
                logger.info("🔐 OAUTH: Triggering deferred Supabase initialization")
                self._initialization_deferred = False
                self.initialize()
            
            if self._offline_mode:
                logger.warning("Cannot sign in with Google - Supabase is in offline mode")
                return None
            
            # Get the client (this will initialize if needed)
            client = self.client
            if not client:
                logger.warning("Cannot sign in with Google - Supabase client is not available")
                return None
            
            logger.info("Attempting Google OAuth login")
            
            def oauth_func():
                options = {}
                if redirect_to:
                    options["redirect_to"] = redirect_to
                
                response = client.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": options
                })
                return response
            
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
        try:
            # Ensure client is initialized
            if hasattr(self, '_initialization_deferred') and self._initialization_deferred:
                logger.info("🔐 OAUTH: Triggering deferred Supabase initialization")
                self._initialization_deferred = False
                self.initialize()
            
            if self._offline_mode:
                logger.warning("Cannot sign in with Discord - Supabase is in offline mode")
                return None
            
            # Get the client (this will initialize if needed)
            client = self.client
            if not client:
                logger.warning("Cannot sign in with Discord - Supabase client is not available")
                return None
            
            logger.info("Attempting Discord OAuth login")
            
            def oauth_func():
                options = {}
                if redirect_to:
                    options["redirect_to"] = redirect_to
                
                response = client.auth.sign_in_with_oauth({
                    "provider": "discord",
                    "options": options
                })
                return response
            
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
        try:
            # Ensure client is initialized
            if hasattr(self, '_initialization_deferred') and self._initialization_deferred:
                logger.info("🔐 OAUTH: Triggering deferred Supabase initialization")
                self._initialization_deferred = False
                self.initialize()
            
            if self._offline_mode:
                logger.warning("Cannot exchange code - Supabase is in offline mode")
                return None
            
            # Get the client (this will initialize if needed)
            client = self.client
            if not client:
                logger.warning("Cannot exchange code - Supabase client is not available")
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
                    
                    auth_code = query_params.get('code', [None])[0]
                    if not auth_code:
                        raise ValueError("No auth code found in URL")
                    
                    # Use default code verifier for backward compatibility
                    code_verifier = "default_code_verifier_for_backward_compatibility"
                    
                    response = client.auth.exchange_code_for_session({
                        "auth_code": auth_code,
                        "code_verifier": code_verifier
                    })
                else:
                    # It's already an object with auth_code and optional code_verifier
                    response = client.auth.exchange_code_for_session(params)
                
                return response
            
            response = self._execute_with_retry(exchange_func)
            # Persist session so other modules relying on saved session (e.g., is_authenticated fast path)
            try:
                if response:
                    # Default to remember_me=True for OAuth logins
                    self._save_session(response, remember_me=True)
                    self._sync_auth_state_with_modules()
            except Exception as save_err:
                logger.warning(f"Failed to persist session after code exchange: {save_err}")
            return response
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
    
    def sign_out(self, force_clear=False, respect_remember_me=True):
        """Sign out the current user.
        
        Args:
            force_clear: If True, always clear the saved session regardless of remember_me preference
            respect_remember_me: If True, preserve sessions when remember_me=True (default). If False, clear all sessions.
        """
        logger.info(f"Signing out user (force_clear={force_clear}, respect_remember_me={respect_remember_me})")
        
        def signout_func():
            try:
                if self._client and hasattr(self._client, 'auth'):
                    self._client.auth.sign_out()
                    logger.info("Successfully signed out from Supabase client")
                else:
                    logger.info("Skipping client sign out (client not available); proceeding with local session clear")
            except Exception as e:
                logger.warning(f"Error during Supabase sign out: {e}")
                # Continue with local cleanup even if remote sign out fails
            
            # Determine if we should clear the saved session
            should_clear = force_clear or not respect_remember_me
            
            # If not forcing, check the remember_me preference
            if not force_clear and respect_remember_me and self._saved_auth and 'remember_me' in self._saved_auth:
                remember_me = self._saved_auth.get('remember_me', False)
                # Only clear if remember_me is False
                should_clear = not remember_me
                logger.info(f"Remember me preference is {remember_me}, {'clearing' if should_clear else 'preserving'} session data")
            elif force_clear:
                logger.info("Force clear requested - clearing all session data")
            elif not respect_remember_me:
                logger.info("Not respecting remember_me - clearing all session data")
            else:
                # Default to clearing if remember_me not found
                should_clear = True
                logger.info("No remember_me preference found - clearing session data")
            
            # Clear saved session if needed
            if should_clear:
                self._clear_session()
                logger.info("Session data cleared during sign out")
            else:
                # Use conditional clearing to preserve remember_me sessions
                cleared = self._clear_session_conditionally(respect_remember_me=True)
                if cleared:
                    logger.info("Session cleared during conditional sign out")
                else:
                    logger.info("Session preserved during sign out due to remember_me preference")
            
            # Sync auth state with other modules
            self._sync_auth_state_with_modules()
            
            logger.info("Sign out process completed successfully")
        
        try:
            # If offline or client missing, still perform local signout logic without retry wrapper
            if self._offline_mode or not self._client:
                logger.warning("Sign out called while offline or client unavailable - performing local session clear")
                signout_func()
            else:
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
                        total=1,  # Reduced from 3 to 1 for faster startup
                        backoff_factor=0.1,  # Reduced from 0.5 to 0.1 for faster startup
                        status_forcelist=[429, 500, 502, 503, 504],
                    )
                    adapter = HTTPAdapter(max_retries=retry_strategy)
                    session.mount("https://", adapter)
                    
                    # Basic health check - only wait 3 seconds maximum for faster startup
                    base_url = self._client.rest_url
                    # Include API key headers to avoid 401s on some PostgREST configs
                    headers = {
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                    }
                    response = session.get(f"{base_url}/health", timeout=3, headers=headers)
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

# Create singleton instance that shares the same manager as get_supabase_client
try:
    with _supabase_manager_lock:
        if _supabase_manager is None or not isinstance(_supabase_manager, SupabaseManager):
            _supabase_manager = SupabaseManager()
    supabase = _supabase_manager
except Exception:
    # Fallback to direct construction if lock/init fails
    supabase = SupabaseManager()