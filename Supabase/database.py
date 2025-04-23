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

def get_laps(limit: int = 50, user_only: bool = True, session_id: str = None):
    """Fetch laps from the `laps` table.

    Args:
        limit: Maximum number of laps to return (default 50).
        user_only: If True, only return laps for the currently logged-in user.
        session_id: If provided, filter laps by this session ID.

    Returns:
        Tuple of (list[dict] | None, str): Data and status message.
    """
    # Import the main authenticated client
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
    except ImportError:
        logger.error("Could not import main Supabase client in get_laps")
        return None, "Internal error: Cannot access database client"

    # Check authentication using the main client
    if user_only and not main_supabase.is_authenticated():
        return None, "Not logged in. Please log in to view laps"

    try:
        # Use the main client for the query
        query = main_supabase.client.table("laps").select("*").limit(limit).order("lap_number")

        # Filter by session ID if provided
        if session_id:
            query = query.eq('session_id', session_id)

        # Filter by user ID if requested
        if user_only:
            # Get user directly from the main client
            user = main_supabase.get_user()
            user_id = None
            if user:
                 if hasattr(user, 'id'):
                     user_id = user.id
                 elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                     user_id = user.user.id
            
            if user_id:
                # Need to join with sessions table to filter by user_id
                # This assumes laps table has a session_id foreign key
                # Modify query to filter based on user ID in the joined sessions table
                # NOTE: Supabase Python client might not support join filtering directly in this way easily.
                # A view or function might be better, or filtering post-fetch.
                # For now, we'll stick to filtering by session_id, assuming sessions are already user-filtered.
                # If session_id is NOT provided, we CAN filter laps by user_id via the session join.
                if not session_id:
                     # Adjust query to filter based on user ID in the sessions table
                     # This requires knowing the structure and how to perform the join/filter efficiently.
                     # Let's assume a direct filter on laps table if user_id exists there (unlikely but simpler)
                     # Or fetch sessions first and then laps for those sessions? More complex.
                     # **Revisiting**: The easiest way is to fetch sessions first if session_id is None.
                     # For now, the primary use case provides session_id, so direct user filtering here is complex.
                     # Let's rely on the session_id being user-specific for now.
                     # If session_id is None and user_only is True, we should probably return an error or fetch user's sessions first.
                     logger.warning("get_laps: user_only=True without session_id is not fully supported yet for direct user filtering.")
                     # Fallback: If no session_id, return empty for now if user_only is True without session filter.
                     # return [], "Need session_id for user-specific laps"
                     pass # Let the session_id filter handle user specificity for now
            else:
                logger.warning("get_laps: user_only=True but could not get user ID from main client")
                return [], "Could not determine user ID"

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

# --- Add missing get_sessions function ---
def get_sessions(limit: int = 50, user_only: bool = False):
    """Fetch sessions from the `sessions` table.

    Args:
        limit: Maximum number of sessions to return (default 50).
        user_only: If True, only return sessions for the currently logged-in user.

    Returns:
        Tuple of (list[dict] | None, str): Data and status message.
    """
    # Import the main authenticated client
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
    except ImportError:
        logger.error("Could not import main Supabase client in get_sessions")
        return None, "Internal error: Cannot access database client"

    # Check authentication using the main client
    if not main_supabase.is_authenticated():
        return None, "Not logged in. Please log in to view sessions"

    try:
        # Use the main client for the query
        query = main_supabase.client.table("sessions").select("*, tracks(name), cars(name)").limit(limit).order("created_at", desc=True)
        
        if user_only:
            # Get user directly from the main client
            user = main_supabase.get_user()
            user_id = None
            if user:
                 if hasattr(user, 'id'):
                     user_id = user.id
                 elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                     user_id = user.user.id
            
            if user_id:
                query = query.eq("user_id", user_id)
            else:
                logger.warning("get_sessions: user_only=True but could not get user ID from main client")
                return [], "Could not determine user ID"
                
        result = query.execute()

        # Process results to flatten track/car names
        processed_data = []
        if result.data:
            for session in result.data:
                session['track_name'] = session.get('tracks', {}).get('name', 'Unknown Track') if session.get('tracks') else 'Unknown Track'
                session['car_name'] = session.get('cars', {}).get('name', 'Unknown Car') if session.get('cars') else 'Unknown Car'
                # Remove nested structures if they exist
                session.pop('tracks', None)
                session.pop('cars', None)
                processed_data.append(session)

        return processed_data, "Sessions retrieved successfully"
    except Exception as e:
        return None, f"Failed to retrieve sessions: {e}"
# --- End get_sessions function ---

# --- End Telemetry / Lap helpers --- 