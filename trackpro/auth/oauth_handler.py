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
from PyQt6.QtWidgets import QMessageBox, QApplication
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
        
        # Store the port being used
        self.oauth_port = port
        
        # Handler for callback requests
        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            parent = self  # Reference to the OAuthHandler instance
            
            def do_GET(self):
                try:
                    logger.info(f"Received callback: {self.path}")

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

                    # Send HTML response that will extract tokens from URL fragment
                    if hasattr(self, 'wfile') and self.wfile is not None:
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        
                        # HTML page that extracts tokens from URL fragment and sends them to server
                        html_response = """
                        <html>
                        <head><title>Authentication Processing...</title></head>
                        <body>
                            <h1>Processing authentication...</h1>
                            <p>Please wait while we complete your authentication.</p>
                            <script>
                                // Extract tokens from URL fragment (for implicit flow)
                                const fragment = window.location.hash.slice(1);
                                const params = new URLSearchParams(fragment);
                                
                                console.log('URL fragment:', fragment);
                                console.log('Fragment params:', params);
                                
                                if (params.has('access_token')) {
                                    console.log('Found access token in fragment');
                                    
                                    // Send token data to our callback endpoint
                                    fetch('/process_tokens', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                        },
                                        body: JSON.stringify({
                                            access_token: params.get('access_token'),
                                            refresh_token: params.get('refresh_token'),
                                            expires_in: params.get('expires_in'),
                                            token_type: params.get('token_type'),
                                            type: params.get('type')
                                        })
                                    }).then(response => {
                                        console.log('Token processing response:', response.status);
                                        if (response.ok) {
                                            document.body.innerHTML = '<h1>Authentication successful!</h1><p>You can close this window now.</p>';
                                            setTimeout(() => window.close(), 2000);
                                        } else {
                                            document.body.innerHTML = '<h1>Authentication completed</h1><p>Please return to the application.</p>';
                                        }
                                    }).catch(err => {
                                        console.error('Error processing tokens:', err);
                                        document.body.innerHTML = '<h1>Authentication completed</h1><p>Please return to the application.</p>';
                                    });
                                } else {
                                    console.log('No access token found in fragment');
                                    document.body.innerHTML = '<h1>Authentication completed</h1><p>Please return to the application.</p>';
                                }
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
                        threading.Thread(target=self.process_callback, args=(code,)).start()
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
                            self.end_headers()
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
                        self.end_headers()
                        self.wfile.write(b'{"status": "success"}')
                        
                        # Process the tokens in a separate thread
                        threading.Thread(target=self.process_tokens, args=(token_data,)).start()
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    logger.error(f"Error in POST handler: {e}")
                    try:
                        self.send_response(500)
                        self.end_headers()
                    except:
                        pass
            
            def process_tokens(self, token_data):
                """Process tokens received from implicit flow."""
                try:
                    access_token = token_data.get('access_token')
                    refresh_token = token_data.get('refresh_token')
                    
                    if not access_token:
                        logger.error("No access token provided")
                        self.parent.auth_completed.emit(False, None)
                        return
                    
                    logger.info(f"Processing tokens for implicit flow")
                    
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
                    
                    # Set the session in the Supabase client
                    from ..database.supabase_client import supabase
                    if supabase and supabase.client:
                        try:
                            # Set the session directly in the client
                            supabase.client.auth.set_session(access_token, refresh_token)
                            logger.info("Successfully set session in Supabase client")
                        except Exception as e:
                            logger.error(f"Error setting session in client: {e}")
                    
                    # Save session and emit success
                    if hasattr(self.parent, '_save_session'):
                        self.parent._save_session(mock_response, remember_me=True)
                    
                    # Emit auth completed signal
                    self.parent.auth_completed.emit(True, mock_response)
                    
                    # Show success message
                    QTimer.singleShot(100, lambda: QMessageBox.information(
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
                            QTimer.singleShot(100, lambda: QMessageBox.information(None, "Authentication Successful", 
                                                           "You have been successfully signed in!"))
                            
                            # Emit signal to parent
                            self.parent.auth_completed.emit(True, result)

                            # Force update the main window if it exists
                            QTimer.singleShot(100, lambda: self.update_main_window())
                        else:
                            logger.error("Failed to exchange code for session")
                            error_detail = getattr(result, 'error', 'Unknown error during code exchange')
                            # Show error message in separate thread to avoid blocking
                            QTimer.singleShot(100, lambda: QMessageBox.warning(None, "Authentication Failed",
                                                       f"Failed to complete authentication: {error_detail}. Please try again."))
                            self.parent.auth_completed.emit(False, None)
                    except Exception as e:
                        logger.error(f"Error exchanging code: {e}", exc_info=True)
                        QTimer.singleShot(100, lambda: QMessageBox.critical(None, "Authentication Error", 
                                                  f"Error exchanging code: {str(e)}"))
                        self.parent.auth_completed.emit(False, None)
                        
                except Exception as e:
                    logger.error(f"Error processing callback: {e}", exc_info=True) # Log traceback
                    # Show error message for exceptions
                    QTimer.singleShot(100, lambda: QMessageBox.critical(None, "Authentication Error", 
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
                        
                        if main_window:
                            # Force an explicit UI refresh with a message
                            QTimer.singleShot(100, lambda: QMessageBox.information(
                                main_window, 
                                "Authentication Successful", 
                                f"You are now logged in as {user_response.user.email}.\n\n"
                                f"If the UI doesn't update, please use the 'Refresh Login State' option from the File menu or restart the application."
                            ))
                        else:
                            QTimer.singleShot(100, lambda: QMessageBox.information(
                                None, 
                                "Authentication Successful", 
                                f"You are now logged in as {user_response.user.email}.\n\n"
                                f"Please restart the application to see the changes."
                            ))
                    else:
                        # More specific logging
                        error_info = getattr(user_response, 'error', 'No user object found in response') if user_response else "No response from get_user"
                        logger.warning(f"User authentication response exists but no valid user found. Details: {error_info}")
                        QTimer.singleShot(100, lambda: QMessageBox.warning(
                            None, 
                            "Authentication Issue", 
                            "You appear to be authenticated but we couldn't retrieve your user details.\n\n"
                            "Please restart the application."
                        ))
                except Exception as e:
                    logger.error(f"Error updating main window: {e}", exc_info=True) # Log traceback
                    QTimer.singleShot(100, lambda: QMessageBox.critical(
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
        
        httpd = CustomTCPServer(("127.0.0.1", port), handler)
        
        try:
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            logger.info(f"Started callback server on port {port}")
            return httpd
        except Exception as e:
            logger.error(f"Failed to start callback server on port {port}: {e}")
            return None
    
    def shutdown_callback_server(self, server):
        """
        Shutdown the callback server.
        
        Args:
            server: The server instance to shutdown
        """
        if server:
            server.shutdown()
            logger.info("Callback server shut down")
    
    def create_email_confirmation_page(self):
        """Create a simple HTML page for email confirmation."""
        return """
        <html>
        <head>
            <title>Email Confirmed - TrackPro</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f0f0f0; }
                .container { max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .success { color: #28a745; font-size: 24px; margin-bottom: 20px; }
                .message { color: #333; font-size: 16px; line-height: 1.6; }
                .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✅ Email Confirmed!</div>
                <div class="message">
                    Your email address has been successfully verified.<br><br>
                    You can now close this window and return to the TrackPro application to sign in.
                </div>
                <a href="#" onclick="window.close()" class="button">Close Window</a>
            </div>
        </body>
        </html>
        """ 