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
        super().__init__("user_details")
    
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
                
            response = self.client.from_("user_details").select("*").eq("user_id", user_id).single().execute()
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
            response = self.client.from_("user_details").select("*").eq("email", email).single().execute()
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
                # Get metadata from user_details table instead of auth.users
                response = self.client.from_("user_details").select("metadata").eq("user_id", user_id).single().execute()
                return response.data.get("metadata", {}) if response.data else {}
            except Exception as e:
                # Get metadata directly from the user object as fallback
                logger.warning(f"Could not get metadata from user_details table: {e}")
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
                return {}
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
            
            # Update in user_details table instead of auth.users
            response = self.client.from_("user_details").update({"metadata": updated_metadata}).eq("user_id", user_id).execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Updated metadata for user {user_id}")
            else:
                logger.warning(f"Failed to update metadata for user {user_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error updating user metadata: {e}")
            return False
    
    def get_user_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details from the user_details table.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            The user details if found, None otherwise
        """
        try:
            # Handle if a user object was passed instead of an ID
            if not isinstance(user_id, str):
                user_id = self._extract_user_id(user_id)
                if not user_id:
                    logger.error(f"Could not extract user ID: {user_id}")
                    return None
            
            response = self.client.from_("user_details").select("*").eq("user_id", user_id).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user details: {e}")
            return None
    
    def get_current_user_details(self) -> Optional[Dict[str, Any]]:
        """Get the currently authenticated user's details from the user_details table.
        
        Returns:
            The user details if found, None otherwise
        """
        user = supabase.get_user()
        if not user:
            return None
        
        user_id = self._extract_user_id(user)
        if not user_id:
            logger.error(f"Could not extract user ID from response: {user}")
            return None
        
        return self.get_user_details(user_id)
    
    def update_user_details(self, user_id: str, details: Dict[str, Any]) -> bool:
        """Update user details in the user_details table.
        
        Args:
            user_id: The ID of the user
            details: The details to update (username, first_name, last_name, date_of_birth)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle if a user object was passed instead of an ID
            if not isinstance(user_id, str):
                user_id = self._extract_user_id(user_id)
                if not user_id:
                    logger.error(f"Could not extract user ID: {user_id}")
                    return False
            
            # Log the update attempt
            logger.info(f"Attempting to update user details for {user_id}")
            logger.debug(f"Update details: {details}")
            
            # Update user details
            response = self.client.from_("user_details").update(details).eq("user_id", user_id).execute()
            
            # Log the response for debugging
            logger.debug(f"Update response: {response}")
            
            success = bool(response.data)
            if success:
                logger.info(f"Updated details for user {user_id}")
            else:
                logger.warning(f"Failed to update details for user {user_id}")
                if hasattr(response, 'error'):
                    logger.error(f"Error from Supabase: {response.error}")
            
            return success
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error updating user details: {error_msg}")
            logger.exception("Exception traceback:")
            return False
    
    def get_complete_user_profile(self) -> Optional[Dict[str, Any]]:
        """Get a complete user profile combining user profiles and user details.
        
        Returns:
            The complete user profile if found, None otherwise
        """
        user = supabase.get_user()
        if not user:
            logger.warning("Cannot get complete profile - no authenticated user")
            return None
        
        user_id = self._extract_user_id(user)
        if not user_id:
            logger.error(f"Could not extract user ID from response: {user}")
            return None
        
        logger.info(f"Getting complete profile for user {user_id}")
        
        try:
            # Get user details
            logger.debug("Querying user_profiles table")
            profile_response = self.client.from_("user_profiles").select("*").eq("user_id", user_id).single().execute()
            logger.debug(f"user_profiles response: {profile_response.data if hasattr(profile_response, 'data') else None}")
            
            logger.debug("Querying user_details table")
            details_response = self.client.from_("user_details").select("*").eq("user_id", user_id).single().execute()
            logger.debug(f"user_details response: {details_response.data if hasattr(details_response, 'data') else None}")
            
            # Get base user info
            base_user = {}
            if hasattr(user, 'email'):
                base_user['email'] = user.email
            
            # Combine data
            profile_data = profile_response.data or {}
            details_data = details_response.data or {}
            
            combined_data = {**base_user, **profile_data, **details_data}
            logger.info(f"Retrieved complete profile for user {user_id}")
            return combined_data
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting complete user profile: {error_msg}")
            logger.exception("Exception traceback:")
            return None

# Create a global instance
user_manager = UserManager() 