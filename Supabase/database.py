"""
Supabase Database Module

This module handles database operations, such as creating and retrieving user profiles and details,
using authenticated requests.
"""

from typing import Optional, Dict, Any, Tuple
from .client import supabase
from . import auth

# Table names
PROFILES_TABLE = "user_profiles"
DETAILS_TABLE = "user_details"

def create_or_update_profile(username: str, first_name: str = "", last_name: str = "", date_of_birth: str = "") -> Tuple[bool, str]:
    """
    Create or update a user profile.
    
    Args:
        username: The username to set for the profile
        first_name: The user's first name
        last_name: The user's last name
        date_of_birth: The user's date of birth in YYYY-MM-DD format
        
    Returns:
        Tuple[bool, str]: A tuple containing a success flag and a message
    """
    if not auth.is_logged_in():
        return False, "Not logged in. Please log in to create or update your profile"
    
    user = auth.get_current_user()
    user_id = user.id if user else None
    
    if not user_id:
        return False, "User ID not found"
    
    # Set the session token for authenticated requests
    session_token = auth.get_session_token()
    supabase.auth.set_session(session_token)
    
    try:
        # Update user details (username, first name, last name, date of birth)
        details_data = {
            "username": username
        }
        
        # Only include non-empty fields
        if first_name:
            details_data["first_name"] = first_name
        if last_name:
            details_data["last_name"] = last_name
        if date_of_birth:
            details_data["date_of_birth"] = date_of_birth
            
        # Check if user details exist
        existing_details = supabase.table(DETAILS_TABLE) \
            .select("*") \
            .eq("id", user_id) \
            .execute()
        
        if existing_details.data and len(existing_details.data) > 0:
            # Update existing details
            details_result = supabase.table(DETAILS_TABLE) \
                .update(details_data) \
                .eq("id", user_id) \
                .execute()
            
            if not (details_result.data and len(details_result.data) > 0):
                return False, "Failed to update user details"
        else:
            # Create new details (should not happen normally due to trigger)
            details_data["id"] = user_id
            details_result = supabase.table(DETAILS_TABLE) \
                .insert(details_data) \
                .execute()
            
            if not (details_result.data and len(details_result.data) > 0):
                return False, "Failed to create user details"

        return True, "Profile updated successfully"
    except Exception as e:
        return False, f"Database operation failed: {e}"

def get_profile() -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Get the current user's profile including both profile and details.
    
    Returns:
        Tuple[Optional[Dict[str, Any]], str]: A tuple containing the combined profile data (or None) and a message
    """
    if not auth.is_logged_in():
        return None, "Not logged in. Please log in to view your profile"
    
    user = auth.get_current_user()
    user_id = user.id if user else None
    
    if not user_id:
        return None, "User ID not found"
    
    # Set the session token for authenticated requests
    session_token = auth.get_session_token()
    supabase.auth.set_session(session_token)
    
    try:
        # Get user profile
        profile_result = supabase.table(PROFILES_TABLE) \
            .select("*") \
            .eq("id", user_id) \
            .execute()
        
        # Get user details
        details_result = supabase.table(DETAILS_TABLE) \
            .select("*") \
            .eq("id", user_id) \
            .execute()
        
        # Combine the data
        combined_data = {}
        
        if profile_result.data and len(profile_result.data) > 0:
            combined_data.update(profile_result.data[0])
        
        if details_result.data and len(details_result.data) > 0:
            combined_data.update(details_result.data[0])
        
        if combined_data:
            return combined_data, "Profile retrieved successfully"
        else:
            return None, "Profile not found"
    except Exception as e:
        return None, f"Failed to retrieve profile: {e}"

def delete_profile() -> Tuple[bool, str]:
    """
    Delete the current user's profile.
    
    Returns:
        Tuple[bool, str]: A tuple containing a success flag and a message
    """
    if not auth.is_logged_in():
        return False, "Not logged in. Please log in to delete your profile"
    
    user = auth.get_current_user()
    user_id = user.id if user else None
    
    if not user_id:
        return False, "User ID not found"
    
    # Set the session token for authenticated requests
    session_token = auth.get_session_token()
    supabase.auth.set_session(session_token)
    
    try:
        # Delete from both tables
        profile_result = supabase.table(PROFILES_TABLE) \
            .delete() \
            .eq("id", user_id) \
            .execute()
        
        details_result = supabase.table(DETAILS_TABLE) \
            .delete() \
            .eq("id", user_id) \
            .execute()
        
        if profile_result.data is not None and details_result.data is not None:
            return True, "Profile deleted successfully"
        else:
            return False, "Failed to delete profile"
    except Exception as e:
        return False, f"Failed to delete profile: {e}"

# --- New Telemetry / Lap helpers ---

def get_laps(limit: int = 100, user_only: bool = False):
    """Fetch laps from the `laps` table.

    Args:
        limit: Maximum number of laps to return (default 100).
        user_only: If True, only return laps for the currently logged‑in user.

    Returns:
        Tuple of (list[dict] | None, str): Data and status message.
    """
    if not auth.is_logged_in():
        return None, "Not logged in. Please log in to view laps"

    # Ensure we are using an authenticated session
    session_token = auth.get_session_token()
    supabase.auth.set_session(session_token)

    try:
        query = supabase.table("laps").select("*").limit(limit).order("created_at", desc=True)
        if user_only:
            current_user = auth.get_current_user()
            if current_user:
                query = query.eq("user_id", current_user.id)
        result = query.execute()
        return result.data, "Laps retrieved successfully"
    except Exception as e:
        return None, f"Failed to retrieve laps: {e}"


def get_lap(lap_id: str):
    """Get a single lap record by id."""
    if not auth.is_logged_in():
        return None, "Not logged in. Please log in to view lap details"

    session_token = auth.get_session_token()
    supabase.auth.set_session(session_token)

    try:
        result = supabase.table("laps").select("*").eq("id", lap_id).single().execute()
        return result.data, "Lap retrieved successfully"
    except Exception as e:
        return None, f"Failed to retrieve lap: {e}"


def get_telemetry_points(lap_id: str, columns: Optional[list[str]] = None):
    """Retrieve telemetry points for a given lap from Supabase.

    Args:
        lap_id: UUID of the lap to fetch telemetry for.
        columns: Optional list of columns to select – if None, selects all.

    Returns:
        Tuple[list[dict] | None, str]
    """
    if not auth.is_logged_in():
        return None, "Not logged in. Please log in to view telemetry points"

    if not lap_id:
        return None, "lap_id is required"

    session_token = auth.get_session_token()
    supabase.auth.set_session(session_token)

    try:
        sel = "*" if columns is None else ",".join(columns)
        result = (
            supabase.table("telemetry_points")
            .select(sel)
            .eq("lap_id", lap_id)
            .order("track_position")
            .execute()
        )
        return result.data, f"Retrieved {len(result.data) if result.data else 0} telemetry points"
    except Exception as e:
        return None, f"Failed to retrieve telemetry points: {e}"

# --- End Telemetry / Lap helpers --- 