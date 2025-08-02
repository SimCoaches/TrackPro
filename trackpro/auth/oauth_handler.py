"""OAuth callback handler for social logins."""

import sys
import base64
import hashlib
import os
import json
import logging
import threading
import webbrowser
import re
from urllib.parse import urlparse, parse_qs
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QObject, QUrl, pyqtSignal, QTimer
from ..database.supabase_client import supabase
# Import User model and setter function
from ..auth.user_manager import User, set_current_user 

logger = logging.getLogger(__name__)

class OAuthHandler(QObject):
    """Handler for OAuth callbacks from social login providers."""
    
    # Signal emitted when authentication is completed
    auth_completed = pyqtSignal(bool, object)
    
    # Signal emitted when a user needs to complete their profile
    profile_completion_required = pyqtSignal(object)
    
    # Signal emitted when password reset is required
    password_reset_required = pyqtSignal(str, str)  # access_token, refresh_token
    
    def __init__(self, parent=None):
        """Initialize the OAuth handler."""
        super().__init__(parent)
        # Store the code verifier for PKCE
        self.code_verifier = None
        self.pending_provider = None
        # Store the OAuth port for use by dialogs
        self.oauth_port = 3000
    
    def register_custom_uri_scheme(self):
        """
        Register 'app://' as a custom URI scheme handler.
        
        This is platform-specific and may require different implementations
        depending on the operating system.
        """
        # This method would register the app as a handler for app:// URLs
        # The implementation varies by platform and would typically be done
        # during application installation
        logger.info("Custom URI scheme registration would happen here")
        
        # For Windows, this would involve registry settings
        # For macOS, this would be in the Info.plist
        # For Linux, this would use .desktop files
        
        # For testing, we could use a localhost server to catch redirects
    
    def generate_code_verifier(self):
        """Generate a code verifier for PKCE."""
        # Generate a random string for PKCE
        # EXACTLY 43 bytes will generate a 58 character base64 string after encoding
        random_bytes = os.urandom(43)
        verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
        verifier = verifier.rstrip('=')  # Remove padding consistently with rstrip
        
        # Store the verifier for later use
        self.code_verifier = verifier
        
        # Log the verifier for debugging (only first 10 chars for security)
        logger.info(f"Generated code verifier for PKCE: {verifier[:10]}... (length: {len(verifier)}, original bytes: {len(random_bytes)})")
        
        return verifier
    
    def generate_code_challenge(self, verifier):
        """Generate a code challenge from the verifier for PKCE."""
        # Create code challenge using SHA256
        challenge_bytes = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8')
        challenge = challenge.rstrip('=')  # Remove padding per RFC 7636
        
        # Log the challenge for debugging
        logger.info(f"Generated code challenge for PKCE: {challenge[:10]}... (length: {len(challenge)}, from verifier: {verifier[:5]}...)")
        
        return challenge
        
    def start_discord_auth(self, redirect_url="http://localhost:3000"):
        """
        Start Discord OAuth flow.
        
        Args:
            redirect_url: URL to redirect to after authentication
            
        Returns:
            Response object with URL to visit for authentication
        """
        try:
            # Store the provider for later use
            self.pending_provider = "discord"
            
            # Use a simpler OAuth approach without PKCE since we keep having issues with code verifiers
            logger.info(f"Starting Discord auth with simplified flow, redirect to {redirect_url}")
            
            # Add more debugging and validation
            if not supabase or not hasattr(supabase, 'client') or not supabase.client:
                logger.warning("Discord auth: Supabase client not initialized, forcing initialization...")
                # Force initialization by accessing the client property
                from ..database.supabase_client import get_supabase_client
                client = get_supabase_client()
                if not client:
                    logger.error("Discord auth failed: Supabase client not initialized")
                    raise ValueError("Supabase client not initialized")
            
            if not hasattr(supabase.client, 'auth'):
                logger.error("Discord auth failed: Supabase client auth module not available")
                raise ValueError("Supabase client auth module not available")
            
            options = {
                "redirect_to": redirect_url,
                # No PKCE parameters since they're causing persistent issues
            }
            
            # Add extra logging for debugging
            logger.info(f"Starting Discord OAuth flow with provider='discord', options={options}")
            
            # Access the underlying client's auth module
            response = supabase.client.auth.sign_in_with_oauth({
                "provider": "discord",
                "options": options
            })
            
            # Validate response
            if not response:
                logger.error("Discord auth failed: Empty response from Supabase")
                raise ValueError("Empty response from Supabase OAuth request")
                
            # Check if URL exists in response
            if not hasattr(response, 'url') or not response.url:
                logger.error(f"Discord auth failed: No URL in response: {response}")
                raise ValueError("No OAuth URL in response")
                
            logger.info(f"Successfully generated Discord OAuth URL: {response.url[:50]}...")
            
            return response
        except Exception as e:
            logger.error(f"Error starting Discord auth: {e}", exc_info=True)
            # Get more specific error details
            error_msg = str(e)
            if "provider not found" in error_msg.lower():
                error_msg = "Discord provider not configured in Supabase. Please configure Discord OAuth in your Supabase dashboard."
            elif "redirect_to" in error_msg.lower():
                redirect_url = redirect_url or "http://localhost:3000"
                error_msg = f"Invalid redirect URL. Please check that your Discord OAuth application has {redirect_url} registered as a redirect URI."
            
            raise ValueError(f"Discord authentication error: {error_msg}")
    
    def start_google_auth(self, redirect_url="http://localhost:3000"):
        """
        Start Google OAuth flow.
        
        Args:
            redirect_url: URL to redirect to after authentication
            
        Returns:
            Response object with URL to visit for authentication
        """
        try:
            # Store the provider for later use
            self.pending_provider = "google"
            
            logger.info(f"Starting Google auth with simplified flow, redirect to {redirect_url}")
            
            # Ensure Supabase client is initialized
            if not supabase or not hasattr(supabase, 'client') or not supabase.client:
                logger.warning("Supabase client not initialized, forcing initialization...")
                # Force initialization by accessing the client property
                from ..database.supabase_client import get_supabase_client
                client = get_supabase_client()
                if not client:
                    logger.error("Cannot sign in with Google - Supabase is not connected")
                    raise ValueError("Supabase client could not be initialized")
            
            options = {
                "redirect_to": redirect_url,
            }
            
            # Access the underlying client's auth module
            response = supabase.client.auth.sign_in_with_oauth({
                "provider": "google",
                "options": options
            })
            
            return response
        except Exception as e:
            logger.error(f"Error starting Google auth: {e}", exc_info=True)
            raise
    
    def handle_callback_url(self, url):
        """
        Handle the callback URL from OAuth providers.
        
        Args:
            url (str): The full callback URL received
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            logger.info(f"Received OAuth callback URL: {url}")
            
            # Parse the URL
            parsed_url = urlparse(url)
            
            # Fix to handle various URL formats
            is_valid_callback = (
                # app://callback format
                (parsed_url.scheme == 'app' and parsed_url.netloc == 'callback') or 
                # localhost format - check for code in query regardless of port
                (parsed_url.scheme == 'http' and 
                 parsed_url.netloc.startswith('localhost') and 
                 parsed_url.path == '/' and 
                 'code=' in parsed_url.query)
            )
            
            if is_valid_callback:
                # Get code from URL
                query_params = parse_qs(parsed_url.query)
                if 'code' in query_params:
                    code = query_params['code'][0]
                    logger.info(f"Extracted auth code: {code[:5]}...")
                    
                    # Without PKCE, we just need to exchange the code
                    params = {
                        "auth_code": code
                    }
                    logger.info(f"Exchanging code without PKCE verification")
                    
                    # Ensure we access auth via client
                    try:
                        result = supabase.client.auth.exchange_code_for_session(params)
                    except Exception as e:
                        logger.error(f"Error exchanging code for session: {e}", exc_info=True)
                        self.auth_completed.emit(False, None)
                        return False
                    
                    if result and hasattr(result, 'user') and result.user:
                        logger.info(f"Social login successful for user: {result.user.email}")
                        self.auth_completed.emit(True, result)
                        return True
                    else:
                        logger.error("Failed to exchange code for session")
                        self.auth_completed.emit(False, None)
                        return False
                else:
                    logger.error("No auth code found in callback URL")
                    self.auth_completed.emit(False, None)
                    return False
            else:
                logger.error(f"Unrecognized callback format: {url}")
                self.auth_completed.emit(False, None)
                return False
                
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            self.auth_completed.emit(False, None)
            return False
    
    def setup_callback_server(self, port=3000):
        """
        Set up a local web server to receive OAuth callbacks.
        
        This is an alternative to custom URI schemes.
        
        Args:
            port (int): The port to listen on
        """
        import http.server
        import threading
        import socketserver
        import sys
        import socket
        import time
        
        # Store the port being used
        self.oauth_port = port
        
        # Check if we're running as a built executable for enhanced error handling
        is_frozen = getattr(sys, 'frozen', False)
        
        # Add comprehensive diagnostics for production builds
        if is_frozen:
            logger.info("Running as built executable - performing OAuth server diagnostics...")
            self._run_oauth_diagnostics()
        
        # Handler for callback requests
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            parent = self  # Reference to the OAuthHandler instance
            
            def log_message(self, format, *args):
                # Custom logging to use our logger instead of printing to stderr
                message = format % args
                logger.info(f"OAuth callback server: {message}")
            
            def do_GET(self):
                try:
                    logger.info(f"Received OAuth callback: {self.path}")

                    # Parse the full callback path properly
                    parsed_path = urlparse(self.path)
                    query_params = parse_qs(parsed_path.query)

                    # Add detailed logging for debugging
                    logger.info(f"Parsed path: {parsed_path.path}")
                    logger.info(f"Query params: {query_params}")
                    logger.info(f"Full URL: {self.path}")

                    # Handle email confirmation route
                    if parsed_path.path == '/auth/confirm':
                        logger.info("Email confirmation callback received")
                        if hasattr(self, 'wfile') and self.wfile is not None:
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            self.wfile.write(self.parent.create_email_confirmation_page().encode('utf-8'))
                        return

                    # Handle password reset route
                    if parsed_path.path == '/auth/reset-password':
                        logger.info("Password reset callback received")
                        if hasattr(self, 'wfile') and self.wfile is not None:
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            self.wfile.write(self.parent.create_password_reset_page().encode('utf-8'))
                        return

                    # Send HTML response that will extract tokens from URL fragment
                    if hasattr(self, 'wfile') and self.wfile is not None:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.send_header('Pragma', 'no-cache')
                        self.send_header('Expires', '0')
                        self.end_headers()
                        
                        # Enhanced HTML page that extracts tokens from URL fragment and sends them to server
                        html_response = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>TrackPro Authentication</title>
                            <meta charset="UTF-8">
                            <style>
                                body {{
                                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    color: white;
                                    margin: 0;
                                    padding: 0;
                                    min-height: 100vh;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                }}
                                .container {{
                                    text-align: center;
                                    background: rgba(255, 255, 255, 0.1);
                                    padding: 2rem;
                                    border-radius: 10px;
                                    backdrop-filter: blur(10px);
                                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                                    max-width: 450px;
                                }}
                                .spinner {{
                                    border: 4px solid rgba(255, 255, 255, 0.3);
                                    border-radius: 50%;
                                    border-top: 4px solid white;
                                    width: 40px;
                                    height: 40px;
                                    animation: spin 1s linear infinite;
                                    margin: 20px auto;
                                }}
                                @keyframes spin {{
                                    0% {{ transform: rotate(0deg); }}
                                    100% {{ transform: rotate(360deg); }}
                                }}
                                .success {{ color: #4CAF50; font-weight: bold; }}
                                .error {{ color: #f44336; font-weight: bold; }}
                                .return-message {{
                                    background: rgba(76, 175, 80, 0.1);
                                    border: 1px solid #4CAF50;
                                    border-radius: 8px;
                                    padding: 1rem;
                                    margin-top: 1rem;
                                    font-size: 14px;
                                    line-height: 1.4;
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>TrackPro Authentication</h1>
                                <div class="spinner" id="spinner"></div>
                                <p id="status">Processing authentication...</p>
                                <p id="details">Please wait while we complete your authentication.</p>
                                <div id="returnMessage" class="return-message" style="display:none;">
                                    <strong>✅ Success!</strong><br>
                                    Please return to the TrackPro application to continue.<br>
                                    You can close this browser window.
                                </div>
                            </div>
                            <script>
                                console.log('TrackPro OAuth callback page loaded');
                                console.log('URL:', window.location.href);
                                console.log('Hash:', window.location.hash);
                                console.log('Search:', window.location.search);
                                
                                // Extract tokens from URL fragment (for implicit flow)
                                const fragment = window.location.hash.slice(1);
                                const params = new URLSearchParams(fragment);
                                
                                console.log('URL fragment:', fragment);
                                console.log('Fragment params:', params);
                                
                                function updateStatus(message, isError = false) {{
                                    const statusEl = document.getElementById('status');
                                    statusEl.textContent = message;
                                    statusEl.className = isError ? 'error' : 'success';
                                    
                                    // Hide spinner when status updates
                                    const spinner = document.getElementById('spinner');
                                    if (spinner) spinner.style.display = 'none';
                                }}
                                
                                function updateDetails(message) {{
                                    document.getElementById('details').textContent = message;
                                }}
                                
                                function showReturnMessage() {{
                                    document.getElementById('returnMessage').style.display = 'block';
                                }}
                                
                                if (params.has('access_token')) {{
                                    console.log('Found access token in fragment');
                                    
                                    // Check if this is a password reset flow
                                    const isPasswordReset = params.get('type') === 'recovery' || 
                                                           window.location.search.includes('type=recovery') ||
                                                           document.referrer.includes('recovery') ||
                                                           params.has('recovery');
                                    
                                    console.log('Is password reset flow:', isPasswordReset);
                                    
                                    const endpoint = isPasswordReset ? '/process_password_reset' : '/process_tokens';
                                    console.log('Using endpoint:', endpoint);
                                    
                                    updateStatus('Processing tokens...');
                                    updateDetails('Sending authentication data to TrackPro...');
                                    
                                    // Send token data to appropriate endpoint
                                    fetch(endpoint, {{
                                        method: 'POST',
                                        headers: {{
                                            'Content-Type': 'application/json',
                                        }},
                                        body: JSON.stringify({{
                                            access_token: params.get('access_token'),
                                            refresh_token: params.get('refresh_token'),
                                            expires_in: params.get('expires_in'),
                                            token_type: params.get('token_type'),
                                            type: params.get('type'),
                                            is_password_reset: isPasswordReset
                                        }})
                                    }}).then(response => {{
                                        console.log('Token processing response:', response.status);
                                        if (response.ok) {{
                                            if (isPasswordReset) {{
                                                updateStatus('Password Reset Ready!');
                                                updateDetails('Your password reset has been processed.');
                                                showReturnMessage();
                                            }} else {{
                                                updateStatus('Authentication Successful!');
                                                updateDetails('You are now logged in to TrackPro!');
                                                showReturnMessage();
                                            }}
                                        }} else {{
                                            updateStatus('Authentication Completed');
                                            updateDetails('');
                                            showReturnMessage();
                                        }}
                                    }}).catch(err => {{
                                        console.error('Error processing tokens:', err);
                                        updateStatus('Authentication Completed');
                                        updateDetails('');
                                        showReturnMessage();
                                    }});
                                }} else {{
                                    console.log('No access token found in fragment, checking for authorization code...');
                                    
                                    // Check for authorization code in query parameters
                                    const urlParams = new URLSearchParams(window.location.search);
                                    if (urlParams.has('code')) {{
                                        console.log('Found authorization code in query parameters');
                                        updateStatus('Authorization Received');
                                        updateDetails('TrackPro is processing your login...');
                                        showReturnMessage();
                                    }} else if (urlParams.has('error')) {{
                                        const error = urlParams.get('error');
                                        const errorDesc = urlParams.get('error_description') || 'No description provided';
                                        console.error('OAuth error:', error, errorDesc);
                                        updateStatus('Authentication Failed', true);
                                        updateDetails(`Error: ${{error}} - ${{errorDesc}}`);
                                        showReturnMessage();
                                    }} else {{
                                        console.log('No tokens or codes found, assuming authentication completed elsewhere');
                                        updateStatus('Authentication Completed');
                                        updateDetails('');
                                        showReturnMessage();
                                    }}
                                }}
                            </script>
                        </body>
                        </html>
                        """
                        
                        self.wfile.write(html_response.encode('utf-8'))
                    else:
                        logger.error("Cannot send response: wfile is None")

                    if 'code' in query_params:
                        code = query_params['code'][0]
                        logger.info(f"✓ SUCCESS: Extracted auth code: {code[:5]}...")

                        # No need to check for code verifier anymore since we're using simplified OAuth flow
                        
                        # Pass code directly to process_callback in a new thread
                        threading.Thread(target=self.process_callback, args=(code,), daemon=True).start()
                    elif 'error' in query_params:
                        error = query_params.get('error', ['Unknown'])[0]
                        error_description = query_params.get('error_description', ['No description provided'])[0]
                        logger.error(f"OAuth Error in callback: {error} - {error_description}")
                        # Optionally trigger a user-facing error
                    else:
                        # Handle cases like /favicon.ico gracefully
                        if self.path == '/favicon.ico':
                            logger.debug("Ignoring favicon request")
                        elif self.path == '/':
                            logger.info("Received root path request - will handle token extraction via JavaScript")
                        else:
                            logger.warning(f"Unexpected callback format or missing code: {self.path}")
                        # No further action needed for favicon or unexpected paths without errors/code

                except Exception as e:
                    logger.error(f"Error in callback server do_GET: {e}", exc_info=True)
                    try:
                        if hasattr(self, 'wfile') and self.wfile is not None:
                            self.send_response(500)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            error_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head><title>TrackPro Authentication Error</title></head>
                            <body>
                                <h1>Authentication Error</h1>
                                <p>An error occurred while processing your authentication.</p>
                                <p>Please return to TrackPro and try again.</p>
                                <p>Error: {str(e)}</p>
                            </body>
                            </html>
                            """
                            self.wfile.write(error_html.encode('utf-8'))
                    except Exception as send_e:
                        logger.error(f"Error sending 500 response: {send_e}")
            
            def do_POST(self):
                try:
                    # Handle token processing from JavaScript
                    if self.path == '/process_tokens':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        token_data = json.loads(post_data.decode('utf-8'))
                        
                        logger.info("✓ SUCCESS: Received tokens from JavaScript")
                        logger.info(f"Access token: {token_data.get('access_token', '')[:20]}...")
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b'{"status": "success"}')
                        
                        # Process the tokens in a separate thread
                        threading.Thread(target=self.process_tokens, args=(token_data,), daemon=True).start()
                    elif self.path == '/process_password_reset':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        token_data = json.loads(post_data.decode('utf-8'))
                        
                        logger.info("✓ SUCCESS: Received password reset tokens from JavaScript")
                        logger.info(f"Access token: {token_data.get('access_token', '')[:20]}...")
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(b'{"status": "success"}')
                        
                        # Process the password reset tokens in a separate thread
                        threading.Thread(target=self.parent.process_password_reset_tokens, args=(token_data,), daemon=True).start()
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    logger.error(f"Error in POST handler: {e}", exc_info=True)
                    try:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status": "error", "message": "Internal server error"}')
                    except:
                        pass
            
            def process_tokens(self, token_data):
                """Process tokens received from implicit flow."""
                try:
                    access_token = token_data.get('access_token')
                    refresh_token = token_data.get('refresh_token')
                    token_type = token_data.get('type')
                    is_password_reset = token_data.get('is_password_reset', False)
                    
                    # Check if this should be routed to password reset handler
                    if token_type == 'recovery' or is_password_reset:
                        logger.info(f"Detected password reset tokens in regular flow, routing to password reset handler")
                        self.process_password_reset_tokens(token_data)
                        return
                    
                    if not access_token:
                        logger.error("No access token provided")
                        self.parent.auth_completed.emit(False, None)
                        return
                    
                    logger.info(f"Processing tokens for implicit flow (OAuth login)")
                    
                    # Create a mock response object for compatibility
                    class MockAuthResponse:
                        def __init__(self, token_data):
                            self.user = MockUser(token_data)
                            self.session = MockSession(token_data)
                    
                    class MockUser:
                        def __init__(self, token_data):
                            # Decode the JWT token to get user info
                            import base64
                            import json
                            try:
                                # Parse JWT payload (middle part)
                                payload = access_token.split('.')[1]
                                # Add padding if needed
                                payload += '=' * (-len(payload) % 4)
                                decoded = base64.urlsafe_b64decode(payload)
                                user_data = json.loads(decoded)
                                
                                self.id = user_data.get('sub')
                                self.email = user_data.get('email')
                                self.user_metadata = user_data.get('user_metadata', {})
                                
                                logger.info(f"Decoded user from JWT: {self.email}")
                            except Exception as e:
                                logger.error(f"Error decoding JWT: {e}")
                                self.id = "unknown"
                                self.email = "unknown@unknown.com"
                                self.user_metadata = {}
                    
                    class MockSession:
                        def __init__(self, token_data):
                            self.access_token = token_data.get('access_token')
                            self.refresh_token = token_data.get('refresh_token')
                            self.expires_in = token_data.get('expires_in')
                            self.token_type = token_data.get('token_type', 'bearer')
                    
                    mock_response = MockAuthResponse(token_data)
                    
                    # Set the session in the Supabase client - with fallback to forcing initialization
                    from ..database.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    if client:
                        try:
                            # Set the session directly in the client
                            client.auth.set_session(access_token, refresh_token)
                            logger.info("Successfully set session in Supabase client")
                        except Exception as e:
                            logger.error(f"Error setting session in client: {e}")
                    else:
                        logger.warning("Supabase client not available - session will be saved for later restoration")
                        # Force initialization by temporarily disabling fast startup
                        import os
                        was_fast_startup = os.environ.get('TRACKPRO_FAST_STARTUP')
                        if was_fast_startup:
                            del os.environ['TRACKPRO_FAST_STARTUP']
                        
                        # Try to get client again
                        client = get_supabase_client() 
                        if client:
                            try:
                                client.auth.set_session(access_token, refresh_token)
                                logger.info("Successfully set session after forcing Supabase initialization")
                            except Exception as e:
                                logger.error(f"Error setting session after forced init: {e}")
                        
                        # Restore fast startup mode if it was set
                        if was_fast_startup:
                            os.environ['TRACKPRO_FAST_STARTUP'] = was_fast_startup
                    
                    # Save session and emit success
                    if hasattr(self.parent, '_save_session'):
                        self.parent._save_session(mock_response, remember_me=True)
                    
                    # Emit auth completed signal
                    self.parent.auth_completed.emit(True, mock_response)
                    
                    # Show success message
                    QTimer.singleShot(1000, lambda: QMessageBox.information(
                        None, 
                        "Authentication Successful", 
                        f"You are now logged in as {mock_response.user.email}!"
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing tokens: {e}", exc_info=True)
                    self.parent.auth_completed.emit(False, None)

            def process_callback(self, code):
                try:
                    logger.info(f"Processing callback for code: {code[:5]}...")

                    # Use simplified OAuth approach without PKCE
                    # Prepare parameters for code exchange - just needs auth_code
                    exchange_params = {
                        "auth_code": code
                    }

                    # Exchange code for session
                    try:
                        # Use the global supabase client directly instead of parent.client
                        from ..database.supabase_client import supabase
                        result = supabase.client.auth.exchange_code_for_session({
                            'auth_code': code
                        })
                        logger.info(f"Code exchange successful: {result is not None}")
                        
                        # Verify that we received a valid session and user
                        if result and hasattr(result, 'user') and result.user:
                            logger.info(f"Successfully authenticated user: {result.user.email}")
                            
                            # *** ADDED: Set the current user in user_manager ***
                            try:
                                authenticated_user = User(
                                    id=result.user.id,
                                    email=result.user.email,
                                    name=result.user.user_metadata.get('name', result.user.email),
                                    is_authenticated=True
                                )
                                set_current_user(authenticated_user)
                                logger.info("Set current user in user_manager successfully")
                            except Exception as user_set_error:
                                logger.error(f"Failed to set user in user_manager: {user_set_error}")
                            # *** END ADDED CODE ***
                            
                            # OPTIMIZATION: Get user details from metadata if available rather than making another query
                            try:
                                user_id = result.user.id
                                # First check user metadata from the auth response
                                user_metadata = result.user.user_metadata or {}
                                
                                has_complete_profile = (
                                    user_metadata.get('first_name') and 
                                    user_metadata.get('last_name') and
                                    user_metadata.get('date_of_birth')
                                )
                                
                                # Only query database if metadata doesn't have what we need
                                if not has_complete_profile:
                                    logger.info(f"Checking profile completeness for user {user_id} (from process_callback)")
                                    user_details = supabase.client.table('user_details').select('*').eq('user_id', user_id).execute()
                                    
                                    if user_details and user_details.data:
                                        profile_data = user_details.data[0]
                                        logger.info(f"User profile for {user_id} is {'complete' if profile_data.get('first_name') and profile_data.get('last_name') and profile_data.get('date_of_birth') else 'incomplete'} (from process_callback). Fields found: {profile_data}")
                                        
                                        has_complete_profile = (
                                            profile_data.get('first_name') and 
                                            profile_data.get('last_name') and
                                            profile_data.get('date_of_birth')
                                        )
                                    else:
                                        logger.info(f"No user_details record found for {user_id}")
                                        has_complete_profile = False
                                else:
                                    logger.info(f"User profile for {user_id} is complete based on auth metadata")
                                
                                # Emit the appropriate signal based on profile completeness
                                if not has_complete_profile:
                                    logger.info(f"Queueing public profile_completion_required emit for user {result.user.email}")
                                    QTimer.singleShot(0, lambda: self.profile_completion_required.emit(result))
                                else:
                                    logger.info(f"User has complete profile, proceeding with normal auth flow")
                            except Exception as profile_e:
                                logger.error(f"Error checking profile completeness: {profile_e}", exc_info=True)
                                # Continue with auth flow on error
                            
                            # Ensure session is saved explicitly to the global client as well
                            if hasattr(supabase, '_save_session'):
                                logger.info("Explicitly saving session to global client with remember_me=True")
                                # Always use remember_me=True for OAuth logins since there's no checkbox
                                supabase._save_session(result, remember_me=True)
                                
                                # Verify the session was properly cached
                                verification = supabase.get_user()
                                if verification and hasattr(verification, 'user') and verification.user:
                                    logger.info(f"Session verification successful: {verification.user.email}")
                                else:
                                    logger.warning("Session verification failed - user not found after saving")
                            
                            # Show success message in separate thread to avoid blocking
                            QTimer.singleShot(500, lambda: QMessageBox.information(None, "Authentication Successful", 
                                                           "You have been successfully signed in!"))
                            
                            # Emit signal to parent
                            self.parent.auth_completed.emit(True, result)

                            # Force update the main window if it exists
                            QTimer.singleShot(1000, lambda: self.update_main_window())
                        else:
                            logger.error("Failed to exchange code for session")
                            error_detail = getattr(result, 'error', 'Unknown error during code exchange')
                            # Show error message in separate thread to avoid blocking
                            QTimer.singleShot(500, lambda: QMessageBox.warning(None, "Authentication Failed",
                                                       f"Failed to complete authentication: {error_detail}. Please try again."))
                            self.parent.auth_completed.emit(False, None)
                    except Exception as e:
                        logger.error(f"Error exchanging code: {e}", exc_info=True)
                        QTimer.singleShot(500, lambda: QMessageBox.critical(None, "Authentication Error", 
                                                  f"Error exchanging code: {str(e)}"))
                        self.parent.auth_completed.emit(False, None)
                        
                except Exception as e:
                    logger.error(f"Error processing callback: {e}", exc_info=True) # Log traceback
                    # Show error message for exceptions
                    QTimer.singleShot(500, lambda: QMessageBox.critical(None, "Authentication Error", 
                                                   f"Error during authentication: {str(e)}"))
                    self.parent.auth_completed.emit(False, None)

            def update_main_window(self):
                """Find and update the main window's auth state."""
                try:
                    # Check if we have a valid user first
                    # Use the globally imported supabase client instance
                    user_response = supabase.get_user()
                    if user_response and hasattr(user_response, 'user') and user_response.user:
                        logger.info(f"User is authenticated: {user_response.user.email}")

                        # Save session explicitly to ensure persistence
                        # Use the globally imported supabase client instance
                        logger.info("Explicitly saving session to global client with remember_me=True")
                        supabase._save_session(user_response, remember_me=True) # Always remember OAuth sessions

                        # Find the main window by looking through top-level widgets
                        from PyQt6.QtWidgets import QApplication, QMessageBox
                        from ..ui import MainWindow
                        
                        # Force reload of auth state to ensure cache is cleared
                        supabase._restore_session()
                        
                        main_window = None
                        for widget in QApplication.topLevelWidgets():
                            if isinstance(widget, MainWindow):
                                main_window = widget
                                logger.info("Found main window, updating auth state")
                                # Force update UI state
                                QApplication.processEvents()
                                widget.update_auth_state()
                                QApplication.processEvents()
                                break
                        
                        # Also try to find and notify the main app instance
                        try:
                            from .. import main
                            app_instances = [obj for obj in QApplication.topLevelWidgets() 
                                           if hasattr(obj, 'app_instance')]
                            for widget in app_instances:
                                if hasattr(widget.app_instance, 'bring_window_to_foreground'):
                                    logger.info("Bringing TrackPro window to foreground after OAuth success")
                                    widget.app_instance.bring_window_to_foreground()
                                    break
                        except Exception as app_e:
                            logger.debug(f"Could not notify main app instance: {app_e}")
                        
                        if main_window:
                            # Show success notification
                            QTimer.singleShot(500, lambda: QMessageBox.information(
                                main_window, 
                                "Login Successful",
                                f"Welcome back! You are now logged in as {user_response.user.email}"
                            ))
                        else:
                            logger.warning("Could not find main window to show success notification")
                    else:
                        logger.warning("Failed to get authenticated user after OAuth callback")

                except Exception as e:
                    logger.error(f"Error updating main window: {e}", exc_info=True) # Log traceback
                    QTimer.singleShot(1000, lambda: QMessageBox.critical(
                        None, 
                        "Error", 
                        f"Error updating authentication state: {str(e)}\n\n"
                        "Please restart the application."
                    ))
        
        # Create the server in a separate thread
        handler = CallbackHandler
        handler.parent = self # Ensure parent is set for access to supabase_manager and code_verifier
        
        class CustomTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
            
            def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
                # Enhanced error handling for production builds
                try:
                    super().__init__(server_address, RequestHandlerClass, bind_and_activate)
                except Exception as e:
                    logger.error(f"Failed to create TCP server on {server_address}: {e}")
                    if is_frozen:
                        logger.error("This is likely due to Windows security restrictions on the built executable")
                    raise
            
            def server_bind(self):
                # Set socket options for better reliability
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, 'SO_REUSEPORT'):
                    try:
                        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    except (AttributeError, OSError):
                        pass  # Not available on all platforms
                super().server_bind()
        
        try:
            # Create the server with enhanced error handling
            logger.info(f"Creating OAuth callback server on 127.0.0.1:{port}")
            httpd = CustomTCPServer(("127.0.0.1", port), handler)
            
            # Set a timeout to prevent hanging
            httpd.timeout = 30
            
            # Start the server in a daemon thread
            def serve_forever_with_exception_handling():
                try:
                    logger.info(f"OAuth callback server starting on port {port}")
                    httpd.serve_forever()
                except Exception as e:
                    logger.error(f"OAuth callback server error: {e}", exc_info=True)
                    if is_frozen:
                        logger.error("Server error in built executable - this may be due to Windows security restrictions")
            
            server_thread = threading.Thread(target=serve_forever_with_exception_handling, daemon=True)
            server_thread.name = f"OAuth-Callback-Server-{port}"
            server_thread.start()
            
            # Give the server a moment to start
            import time
            time.sleep(0.1)
            
            # Verify the server is running by checking if the thread is alive
            if server_thread.is_alive():
                logger.info(f"OAuth callback server started successfully on port {port}")
                
                # Store a reference to the thread for cleanup
                httpd._server_thread = server_thread
                
                return httpd
            else:
                logger.error("OAuth callback server thread failed to start")
                httpd.server_close()
                return None
                
        except Exception as e:
            logger.error(f"Failed to start OAuth callback server on port {port}: {e}", exc_info=True)
            
            if is_frozen:
                logger.error("OAuth server startup failed in built executable. Possible causes:")
                logger.error("- Windows Firewall blocking the application")
                logger.error("- Windows Defender flagging the executable")
                logger.error("- Insufficient network permissions")
                logger.error("- Port already in use by another application")
                logger.error("Solution: Run as Administrator or add TrackPro to Windows Defender exclusions")
            
            return None
    
    def _run_oauth_diagnostics(self):
        """Run comprehensive OAuth diagnostics for production builds."""
        import subprocess
        import platform
        
        logger.info("=== OAuth Diagnostics Report ===")
        
        # Check Windows version
        logger.info(f"Windows version: {platform.platform()}")
        
        # Check if running as admin
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            logger.info(f"Running as administrator: {is_admin}")
        except:
            logger.info("Could not determine admin status")
        
        # Check Windows Defender status
        try:
            result = subprocess.run(['powershell', '-Command', 'Get-MpComputerStatus | Select-Object -Property AntivirusEnabled'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and 'True' in result.stdout:
                logger.warning("Windows Defender is active - may block OAuth server")
            else:
                logger.info("Windows Defender status: Unknown or disabled")
        except:
            logger.info("Could not check Windows Defender status")
        
        # Check firewall status
        try:
            result = subprocess.run(['netsh', 'advfirewall', 'show', 'allprofiles', 'state'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                if 'ON' in result.stdout:
                    logger.warning("Windows Firewall is active - may block OAuth server")
                else:
                    logger.info("Windows Firewall appears to be disabled")
        except:
            logger.info("Could not check Windows Firewall status")
        
        # Check port availability
        ports_to_check = [3000, 3001, 3002, 8080]
        import socket
        available_ports = []
        for port in ports_to_check:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result != 0:  # Port is available
                    available_ports.append(port)
            except:
                pass
        
        logger.info(f"Available OAuth ports: {available_ports}")
        
        if not available_ports:
            logger.warning("No standard OAuth ports are available")
        
        logger.info("=== End OAuth Diagnostics ===")
        
    def create_oauth_fallback_instructions(self):
        """Create instructions for OAuth fallback when server fails."""
        return """
        <div style="background: #2a2a2a; color: white; padding: 20px; border-radius: 8px; font-family: Arial, sans-serif;">
            <h2 style="color: #ff6b6b;">🔒 OAuth Login Unavailable</h2>
            <p>The OAuth login system cannot start due to Windows security restrictions.</p>
            
            <h3 style="color: #4ecdc4;">Quick Solutions:</h3>
            <ol>
                <li><strong>Use Email/Password Login:</strong> Click "Cancel" and use the email/password login instead</li>
                <li><strong>Run as Administrator:</strong> Close TrackPro, right-click the executable, and select "Run as administrator"</li>
                <li><strong>Add to Windows Defender:</strong> Add TrackPro to Windows Defender exclusions</li>
                <li><strong>Allow through Firewall:</strong> Allow TrackPro through Windows Firewall</li>
            </ol>
            
            <h3 style="color: #4ecdc4;">Why this happens:</h3>
            <p>OAuth requires a local web server that Windows security software often blocks in built applications.</p>
            
            <p style="color: #feca57; background: #2d2d2d; padding: 10px; border-radius: 4px;">
                <strong>💡 Tip:</strong> Email/password login works reliably and provides the same features!
            </p>
        </div>
        """
    
    def create_email_confirmation_page(self):
        """Create HTML page for email confirmation."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>TrackPro Email Confirmation</title>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 2rem;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    max-width: 500px;
                }
                .success { color: #4CAF50; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Email Confirmed!</h1>
                <p class="success">Your email address has been successfully confirmed.</p>
                <p>You can now close this window and return to TrackPro to complete your registration.</p>
                </div>
        </body>
        </html>
        """
    
    def create_password_reset_page(self):
        """Create HTML page for password reset."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>TrackPro Password Reset</title>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 2rem;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    max-width: 500px;
                }
                .success { color: #4CAF50; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Password Reset Ready</h1>
                <p class="success">Your password reset request has been processed.</p>
                <p>Please return to TrackPro to set your new password.</p>
                <p>You can close this window now.</p>
            </div>
        </body>
        </html>
        """ 

    def process_password_reset_tokens(self, token_data):
        """Process password reset tokens received from the callback."""
        try:
            logger.info("Processing password reset tokens...")
            
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            
            if not access_token:
                logger.error("No access token in password reset data")
                return
                
            logger.info(f"Password reset access token: {access_token[:20]}...")
            
            # Emit the password_reset_required signal with the tokens
            self.password_reset_required.emit(access_token, refresh_token or "")
            
            logger.info("Password reset signal emitted successfully")
            
        except Exception as e:
            logger.error(f"Error processing password reset tokens: {e}", exc_info=True) 