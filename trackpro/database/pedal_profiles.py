"""Module for managing user pedal profiles in Supabase."""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from .supabase_client import supabase

logger = logging.getLogger(__name__)

class PedalProfileManager:
    """Class for managing pedal profiles in Supabase."""
    
    @staticmethod
    def save_profile(
        name: str, 
        description: str, 
        throttle_calibration: Dict[str, Any], 
        brake_calibration: Dict[str, Any], 
        clutch_calibration: Dict[str, Any],
        profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save a pedal profile to Supabase.
        
        Args:
            name: The name of the profile
            description: Optional description of the profile
            throttle_calibration: Throttle calibration data
            brake_calibration: Brake calibration data
            clutch_calibration: Clutch calibration data
            profile_id: Optional existing profile ID to update
        
        Returns:
            The saved profile data
        
        Raises:
            Exception: If saving fails
        """
        try:
            # Make sure we're authenticated
            if not supabase.is_authenticated():
                raise Exception("User must be logged in to save profiles")
            
            # Get the current user
            user_response = supabase.get_user()
            if not user_response or not hasattr(user_response, 'user') or not user_response.user.id:
                raise Exception("Failed to get current user")
            
            user_id = user_response.user.id
            
            # Prepare the data
            profile_data = {
                "user_id": user_id,
                "name": name,
                "description": description or "",
                "throttle_calibration": json.dumps(throttle_calibration),
                "brake_calibration": json.dumps(brake_calibration),
                "clutch_calibration": json.dumps(clutch_calibration)
            }
            
            # Save to Supabase
            if profile_id:
                # Update existing profile
                response = supabase.client.table("pedal_profiles") \
                    .update(profile_data) \
                    .eq("id", profile_id) \
                    .execute()
                logger.info(f"Updated pedal profile {profile_id}")
            else:
                # Create new profile
                response = supabase.client.table("pedal_profiles") \
                    .insert(profile_data) \
                    .execute()
                logger.info("Created new pedal profile")
            
            if hasattr(response, 'data') and response.data:
                return response.data[0]
            
            raise Exception("Failed to save profile")
            
        except Exception as e:
            logger.error(f"Error saving pedal profile: {e}")
            raise
    
    @staticmethod
    def get_profiles() -> List[Dict[str, Any]]:
        """Get all pedal profiles for the current user.
        
        Returns:
            List of pedal profiles
        
        Raises:
            Exception: If retrieval fails
        """
        try:
            # Make sure we're authenticated
            if not supabase.is_authenticated():
                return []
            
            # Get the current user's profiles
            response = supabase.client.rpc('get_user_pedal_profiles').execute()
            
            if hasattr(response, 'data'):
                profiles = response.data or []
                
                # Parse JSONB fields back to dictionaries
                for profile in profiles:
                    for field in ['throttle_calibration', 'brake_calibration', 'clutch_calibration']:
                        if profile.get(field) and isinstance(profile[field], str):
                            try:
                                profile[field] = json.loads(profile[field])
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse {field} for profile {profile.get('id')}")
                
                return profiles
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting pedal profiles: {e}")
            return []
    
    @staticmethod
    def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pedal profile by ID.
        
        Args:
            profile_id: The ID of the profile to retrieve
            
        Returns:
            The profile data or None if not found
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            # Make sure we're authenticated
            if not supabase.is_authenticated():
                return None
            
            # Get the specific profile
            response = supabase.client.table("pedal_profiles") \
                .select("*") \
                .eq("id", profile_id) \
                .execute()
            
            if hasattr(response, 'data') and response.data:
                profile = response.data[0]
                
                # Parse JSONB fields back to dictionaries
                for field in ['throttle_calibration', 'brake_calibration', 'clutch_calibration']:
                    if profile.get(field) and isinstance(profile[field], str):
                        try:
                            profile[field] = json.loads(profile[field])
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse {field} for profile {profile.get('id')}")
                
                return profile
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting pedal profile {profile_id}: {e}")
            return None
    
    @staticmethod
    def delete_profile(profile_id: str) -> bool:
        """Delete a pedal profile.
        
        Args:
            profile_id: The ID of the profile to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure we're authenticated
            if not supabase.is_authenticated():
                return False
            
            # Delete the profile
            response = supabase.client.table("pedal_profiles") \
                .delete() \
                .eq("id", profile_id) \
                .execute()
            
            if hasattr(response, 'data') and response.data:
                logger.info(f"Deleted pedal profile {profile_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting pedal profile {profile_id}: {e}")
            return False 