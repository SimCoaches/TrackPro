"""User database manager for handling user-related operations."""

import logging
from typing import Any, Dict, List, Optional
from .base import DatabaseManager
from .supabase_client import supabase

logger = logging.getLogger(__name__)

class UserManager(DatabaseManager):
    """Manages user-related database operations."""
    
    def __init__(self):
        """Initialize the user manager."""
        super().__init__("auth.users")
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the currently authenticated user's data.
        
        Returns:
            The user's data if found, None otherwise
        """
        user = supabase.get_user()
        if not user:
            return None
        
        try:
            # Extract user ID, handling different response types
            user_id = self._extract_user_id(user)
            if not user_id:
                logger.error(f"Could not extract user ID from response: {user}")
                return None
                
            response = self.client.from_("auth.users").select("*").eq("id", user_id).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting current user data: {e}")
            return None
    
    def _extract_user_id(self, user_obj: Any) -> Optional[str]:
        """Extract user ID from various Supabase response types.
        
        Args:
            user_obj: The user object from Supabase
            
        Returns:
            The user ID if found, None otherwise
        """
        # Handle different types of user objects from Supabase
        if hasattr(user_obj, 'id'):
            return user_obj.id
        elif hasattr(user_obj, 'user') and hasattr(user_obj.user, 'id'):
            return user_obj.user.id
        elif isinstance(user_obj, dict) and 'id' in user_obj:
            return user_obj['id']
        elif isinstance(user_obj, dict) and 'user' in user_obj and isinstance(user_obj['user'], dict) and 'id' in user_obj['user']:
            return user_obj['user']['id']
        
        # If we can't find an ID, log the structure and return None
        logger.warning(f"Unknown user object structure: {type(user_obj)}, {user_obj}")
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by their email address.
        
        Args:
            email: The email address to search for
            
        Returns:
            The user data if found, None otherwise
        """
        try:
            response = self.client.from_("auth.users").select("*").eq("email", email).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_metadata(self, user_id: str) -> Dict[str, Any]:
        """Get a user's metadata.
        
        Args:
            user_id: The ID of the user or a user object
            
        Returns:
            The user's metadata
        """
        try:
            # Handle if a user object was passed instead of an ID
            if not isinstance(user_id, str):
                user_id = self._extract_user_id(user_id)
                if not user_id:
                    logger.error(f"Could not extract user ID: {user_id}")
                    return {}
            
            try:
                response = self.client.from_("auth.users").select("raw_user_meta_data").eq("id", user_id).single().execute()
                return response.data.get("raw_user_meta_data", {}) if response.data else {}
            except Exception as e:
                # Check if this is a missing table error
                error_str = str(e)
                if "relation" in error_str and "does not exist" in error_str:
                    logger.warning("Table 'auth.users' does not exist, attempting alternate approach")
                    # Try to get metadata directly from the user object
                    user = supabase.get_user()
                    if user:
                        if hasattr(user, 'user_metadata'):
                            return user.user_metadata or {}
                        elif hasattr(user, 'user') and hasattr(user.user, 'user_metadata'):
                            return user.user.user_metadata or {}
                        elif isinstance(user, dict) and 'user_metadata' in user:
                            return user['user_metadata'] or {}
                        elif isinstance(user, dict) and 'user' in user and isinstance(user['user'], dict) and 'user_metadata' in user['user']:
                            return user['user']['user_metadata'] or {}
                # Rethrow other errors
                raise
        except Exception as e:
            logger.error(f"Error getting user metadata: {e}")
            return {}
    
    def update_user_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """Update a user's metadata.
        
        Args:
            user_id: The ID of the user
            metadata: The metadata to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current metadata
            current_metadata = self.get_user_metadata(user_id)
            
            # Merge with new metadata
            updated_metadata = {**current_metadata, **metadata}
            
            # Update via auth API
            response = self.client.auth.admin.update_user_by_id(
                user_id,
                {"raw_user_meta_data": updated_metadata}
            )
            
            success = bool(response)
            if success:
                logger.info(f"Updated metadata for user {user_id}")
            else:
                logger.warning(f"Failed to update metadata for user {user_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error updating user metadata: {e}")
            return False

# Create a global instance
user_manager = UserManager() 