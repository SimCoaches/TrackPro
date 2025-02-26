"""
Authentication client for TrackPro using Supabase directly.
"""

import os
import json
import logging
from pathlib import Path
from supabase import create_client, Client
from typing import Optional, Dict, Any

# Set up logging
log_dir = os.path.join(os.path.expanduser("~"), ".trackpro", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "auth.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("trackpro.auth")

class AuthClient:
    """Client for handling authentication and user management."""
    
    def __init__(self):
        """Initialize the auth client."""
        # Get Supabase credentials from environment variables
        self.supabase_url = os.environ.get("SUPABASE_URL", "https://xjpewnaxszuqluhdhusf.supabase.co")
        self.supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhqcGV3bmF4c3p1cWx1aGRodXNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA1MTI4NzUsImV4cCI6MjA1NjA4ODg3NX0.2RcZ2m1kMm7S41de-xm")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.current_user = None
        self.session = None
        
        # Load any existing session
        self._load_session()

    def register(self, email: str, password: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: User's password
            profile_data: Additional profile information
            
        Returns:
            Dict containing user information
        """
        try:
            # Register with Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if auth_response.user:
                # Create profile
                profile_data["id"] = auth_response.user.id
                self.supabase.table("profiles").insert(profile_data).execute()
                
                self.current_user = auth_response.user
                self.session = auth_response.session
                self._save_session()
                
                logger.info(f"Successfully registered user: {email}")
                return {"user": auth_response.user}
            
            raise Exception("Registration failed: No user data received")
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Log in an existing user.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dict containing session information
        """
        try:
            # Login with Supabase Auth
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response.session:
                self.session = auth_response.session
                self.current_user = auth_response.user
                self._save_session()
                
                logger.info(f"Successfully logged in user: {email}")
                return {
                    "session": auth_response.session,
                    "user": auth_response.user
                }
            
            raise Exception("Login failed: No session data received")
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise

    def logout(self) -> None:
        """Log out the current user."""
        try:
            self.supabase.auth.sign_out()
            self.current_user = None
            self.session = None
            self._clear_session()
            logger.info("Successfully logged out")
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's profile information.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dict containing profile information
        """
        try:
            response = self.supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            raise

    def refresh_session(self) -> Optional[Dict[str, Any]]:
        """
        Refresh the current session.
        
        Returns:
            Dict containing new session information if successful, None otherwise
        """
        if not self.session:
            return None

        try:
            auth_response = self.supabase.auth.refresh_session()
            
            if auth_response.session:
                self.session = auth_response.session
                self.current_user = auth_response.user
                self._save_session()
                logger.info("Successfully refreshed session")
                return {
                    "session": auth_response.session,
                    "user": auth_response.user
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Session refresh error: {str(e)}")
            return None

    def _save_session(self) -> None:
        """Save the current session to a file."""
        if not self.session:
            return

        try:
            session_dir = Path.home() / ".trackpro"
            session_dir.mkdir(exist_ok=True)
            session_file = session_dir / "session.json"
            
            session_data = {
                "session": self.session,
                "user": self.current_user
            }
            
            with open(session_file, "w") as f:
                json.dump(session_data, f)
                
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")

    def _load_session(self) -> None:
        """Load a saved session from file."""
        try:
            session_file = Path.home() / ".trackpro" / "session.json"
            
            if not session_file.exists():
                return
                
            with open(session_file, "r") as f:
                session_data = json.load(f)
                
            self.session = session_data.get("session")
            self.current_user = session_data.get("user")
            
            if self.session:
                self.refresh_session()
                
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")

    def _clear_session(self) -> None:
        """Clear the saved session file."""
        try:
            session_file = Path.home() / ".trackpro" / "session.json"
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}") 