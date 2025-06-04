"""
Supabase Database Module

This module handles database operations, such as creating and retrieving user profiles and details,
using authenticated requests.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from .client import supabase
from . import auth

logger = logging.getLogger(__name__)

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
        if session_id:
            # For specific sessions, get laps and filter out obvious outlaps
            logger.info(f"Fetching laps for session {session_id}")
            
            # First try to get ALL laps for debugging (no filtering)
            result_all = main_supabase.client.table("laps").select("*").eq("session_id", session_id).order("lap_number").limit(limit).execute()
            logger.info(f"Found {len(result_all.data) if result_all.data else 0} total laps in database for session {session_id}")
            
            if result_all.data:
                for i, lap in enumerate(result_all.data[:3]):  # Log first 3 for debugging
                    logger.info(f"DB Lap {i}: id={lap.get('id')}, lap_number={lap.get('lap_number')}, lap_time={lap.get('lap_time')}, is_valid={lap.get('is_valid')}")
            
            # Now get laps with less strict filtering - allow any lap_time and both valid/invalid laps for debugging
            result = main_supabase.client.table("laps").select("*").eq("session_id", session_id).order("lap_number").limit(limit).execute()
            
            if result.data:
                # For debugging, let's be less strict and include all laps for now
                filtered_laps = []
                for lap in result.data:
                    lap_time = lap.get('lap_time', 0)
                    is_valid = lap.get('is_valid', False)
                    # Much more lenient filtering for debugging - include any lap with a reasonable time
                    if lap_time > 0 and lap_time < 600:  # Include laps under 10 minutes (very lenient)
                        filtered_laps.append(lap)
                        logger.debug(f"Included lap {lap.get('lap_number')} with time {lap_time}s, is_valid={is_valid}")
                    else:
                        logger.debug(f"Filtered out lap {lap.get('id')} with lap time {lap_time}s")
                
                logger.info(f"Found {len(filtered_laps)} laps for session {session_id} after lenient filtering (filtered {len(result.data) - len(filtered_laps)} extreme outliers)")
                return filtered_laps, f"Found {len(filtered_laps)} laps"
            else:
                logger.warning(f"No laps found in database for session {session_id}")
                return [], "No laps found for this session"
        else:
            # For general lap queries, get recent valid laps
            logger.info("Fetching recent racing laps")
            
            # Get recent valid laps with reasonable lap times
            query = main_supabase.client.table("laps").select("*").eq("is_valid", True)
            
            # Add time filter for recent laps
            from datetime import datetime, timedelta
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
            query = query.gte("created_at", thirty_days_ago)
            
            # Execute the query
            result = query.order("created_at", desc=True).limit(limit * 2).execute()  # Get more to allow for filtering
            
            if result.data:
                # Filter out obvious outlaps
                filtered_laps = []
                for lap in result.data:
                    lap_time = lap.get('lap_time', 0)
                    # Only include laps with reasonable lap times (5 seconds to 2 minutes)
                    if 5 < lap_time < 120:
                        filtered_laps.append(lap)
                    
                    # Stop when we have enough good laps
                    if len(filtered_laps) >= limit:
                        break
                
                logger.info(f"Found {len(filtered_laps)} recent racing laps after filtering")
                return filtered_laps, f"Found {len(filtered_laps)} racing laps"
            else:
                return [], "No recent laps found"

    except Exception as e:
        logger.error(f"Error fetching laps: {e}")
        return None, f"Database error: {str(e)}"


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
    # Try multiple approaches to get an authenticated Supabase client
    supabase_client = None
    
    # First try direct import from trackpro's client
    try:
        from trackpro.database.supabase_client import supabase as app_supabase
        if app_supabase and app_supabase.is_authenticated():
            supabase_client = app_supabase.client
            return _execute_telemetry_query(supabase_client, lap_id, columns)
    except (ImportError, AttributeError):
        pass
    
    # Then try the module-level supabase client
    try:
        from .client import supabase
        if supabase and hasattr(supabase, 'client') and supabase.client:
            # For diagnostics, try to get session info
            try:
                auth_session = supabase.client.auth.get_session()
                has_user = auth_session and hasattr(auth_session, 'user') and auth_session.user is not None
                if has_user:
                    supabase_client = supabase.client
                    return _execute_telemetry_query(supabase_client, lap_id, columns)
            except Exception:
                pass
    except (ImportError, AttributeError):
        pass
    
    # Try explicit authentication from auth module as last resort
    try:
        from .client import supabase
        from . import auth
        if auth.is_logged_in():
            session_token = auth.get_session_token()
            if session_token and supabase.client:
                # Set session token and check if it's valid
                supabase.auth.set_session(session_token)
                try:
                    # Check if session is valid
                    auth_session = supabase.client.auth.get_session()
                    if auth_session and hasattr(auth_session, 'user') and auth_session.user:
                        # Success - return query result
                        supabase_client = supabase.client
                        return _execute_telemetry_query(supabase_client, lap_id, columns)
                except Exception:
                    pass
    except Exception:
        pass
        
    # If we get here, all attempts to obtain an authenticated client failed
    return None, "Failed to obtain authenticated Supabase client for telemetry access"

def _execute_telemetry_query(client, lap_id: str, columns: Optional[list[str]] = None):
    """Execute the actual telemetry points query with appropriate error handling."""
    if not lap_id:
        return None, "lap_id is required"

    all_points = []
    current_offset = 0
    # Supabase default limit is 1000, so we use that as page size.
    # This can be configured in Supabase project settings (Settings -> API -> Max Rows)
    # but client-side pagination is safer for potentially very large datasets.
    page_size = 1000

    try:
        sel = "*" if columns is None else ",".join(columns)
        
        while True:
            query = (
                client.table("telemetry_points")
                .select(sel)
                .eq("lap_id", lap_id)
                .order("track_position") # Ensure consistent ordering for pagination
                .range(current_offset, current_offset + page_size - 1) # Fetch one page
            )
            
            result = query.execute()

            if result.data:
                all_points.extend(result.data)
                if len(result.data) < page_size:
                    # Last page fetched
                    break
                current_offset += len(result.data) # Move to the next page offset
            else:
                # No more data or an error occurred on this page fetch
                if not all_points: # If no points fetched at all and no data on first page
                    # Check if there was an error message from PostgREST (e.g. in result.error)
                    error_message = "Failed to retrieve telemetry points"
                    if hasattr(result, 'error') and result.error and hasattr(result.error, 'message'):
                        error_message += f": {result.error.message}"
                    elif hasattr(result, 'message') and result.message: # some clients might put it here
                         error_message += f": {result.message}"
                    return None, error_message
                break # No more data, exit loop

        return all_points, f"Retrieved {len(all_points)} telemetry points"
    except Exception as e:
        # Log the full exception for better debugging
        # Consider using logger.exception("Error in _execute_telemetry_query:") if logger is configured
        return None, f"Failed to retrieve telemetry points due to an exception: {str(e)}"

# --- Add missing get_sessions function ---
def get_sessions(limit: int = 50, user_only: bool = False, only_with_laps: bool = False):
    """Fetch sessions from the `sessions` table.

    Args:
        limit: Maximum number of sessions to return (default 50).
        user_only: If True, only return sessions for the currently logged-in user.
        only_with_laps: If True, only return sessions that have at least one lap.

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
        # DEBUGGING: First, let's see what laps exist in the database at all
        all_laps_result = main_supabase.client.table("laps").select("session_id, lap_number, lap_time, is_valid, created_at").limit(100).execute()
        if all_laps_result.data:
            logger.info(f"DATABASE DEBUG: Found {len(all_laps_result.data)} total laps in database")
            # Group by session_id to see which sessions have laps
            session_lap_counts = {}
            for lap in all_laps_result.data:
                session_id = lap.get('session_id')
                if session_id not in session_lap_counts:
                    session_lap_counts[session_id] = 0
                session_lap_counts[session_id] += 1
            
            logger.info(f"DATABASE DEBUG: Sessions with laps: {session_lap_counts}")
            for session_id, count in session_lap_counts.items():
                logger.info(f"DATABASE DEBUG: Session {session_id} has {count} laps")
        else:
            logger.warning("DATABASE DEBUG: No laps found in entire database!")

        # Use the main client for the query
        if only_with_laps:
            # Query sessions that have at least one lap using EXISTS
            # CRITICAL FIX: Include track length_meters in the query
            query = main_supabase.client.table("sessions").select("*, tracks(name, length_meters), cars(name)")
            
            # Add subquery to only include sessions with laps
            # Note: This uses a more complex approach since Supabase doesn't have direct EXISTS support
            # We'll fetch sessions and then filter by checking if they have laps
            all_sessions_result = query.limit(limit * 3).order("created_at", desc=True).execute()  # Get more to allow for filtering
            
            if all_sessions_result.data:
                # Get session IDs that have laps
                sessions_with_laps = set()
                if all_laps_result.data:
                    sessions_with_laps = {lap.get('session_id') for lap in all_laps_result.data if lap.get('session_id')}
                
                # Filter sessions to only include those with laps
                filtered_sessions = []
                for session in all_sessions_result.data:
                    session_id = session.get('id')
                    if session_id in sessions_with_laps:
                        filtered_sessions.append(session)
                        if len(filtered_sessions) >= limit:  # Stop when we have enough
                            break
                
                logger.info(f"DATABASE DEBUG: Filtered to {len(filtered_sessions)} sessions with laps (from {len(all_sessions_result.data)} total sessions)")
                result_data = filtered_sessions
            else:
                result_data = []
        else:
            # Regular query for all sessions
            # CRITICAL FIX: Include track length_meters in the query
            query = main_supabase.client.table("sessions").select("*, tracks(name, length_meters), cars(name)").limit(limit).order("created_at", desc=True)
            result = query.execute()
            result_data = result.data or []
        
        if user_only and result_data:
            # Get user directly from the main client
            user = main_supabase.get_user()
            user_id = None
            if user:
                 if hasattr(user, 'id'):
                     user_id = user.id
                 elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                     user_id = user.user.id
            
            if user_id:
                # Filter by user_id
                result_data = [session for session in result_data if session.get('user_id') == user_id]
                logger.info(f"DATABASE DEBUG: Filtering sessions by user_id: {user_id}")
            else:
                logger.warning("get_sessions: user_only=True but could not get user ID from main client")
                return [], "Could not determine user ID"
        else:
            logger.info("DATABASE DEBUG: Not filtering by user - getting all sessions")
                
        logger.info(f"DATABASE DEBUG: Found {len(result_data)} sessions")

        # Process results to flatten track/car names and include track length
        processed_data = []
        if result_data:
            for session in result_data:
                session_id = session.get('id')
                logger.info(f"DATABASE DEBUG: Session {session_id} - {session.get('created_at')} - {session.get('cars', {}).get('name', 'Unknown')} at {session.get('tracks', {}).get('name', 'Unknown')}")
                
                session['track_name'] = session.get('tracks', {}).get('name', 'Unknown Track') if session.get('tracks') else 'Unknown Track'
                session['car_name'] = session.get('cars', {}).get('name', 'Unknown Car') if session.get('cars') else 'Unknown Car'
                
                # CRITICAL FIX: Extract and include track length from database
                track_length = session.get('tracks', {}).get('length_meters', None) if session.get('tracks') else None
                if track_length:
                    session['track_length'] = track_length
                    logger.info(f"DATABASE DEBUG: Session {session_id} track length: {track_length}m")
                else:
                    logger.warning(f"DATABASE DEBUG: No track length found for session {session_id}")
                
                # Remove nested structures if they exist
                session.pop('tracks', None)
                session.pop('cars', None)
                processed_data.append(session)

        return processed_data, "Sessions retrieved successfully"
    except Exception as e:
        logger.error(f"Error in get_sessions: {e}")
        return None, f"Failed to retrieve sessions: {e}"
# --- End get_sessions function ---

# --- ML Lap helpers ---

def get_ml_laps(limit: int = 50, user_only: bool = False):
    """Fetch ML-optimized laps from the `laps_ml` table.

    Args:
        limit: Maximum number of ML laps to return (default 50).
        user_only: If True, only return ML laps based on the currently logged-in user's original laps.

    Returns:
        Tuple of (list[dict] | None, str): Data and status message.
    """
    # Import the main authenticated client
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
    except ImportError:
        logger.error("Could not import main Supabase client in get_ml_laps")
        return None, "Internal error: Cannot access database client"

    # Check authentication using the main client
    if not main_supabase.is_authenticated():
        return None, "Not logged in. Please log in to view ML laps"

    try:
        # Use the main client for the query
        query = main_supabase.client.table("laps_ml").select("*").limit(limit).order("created_at", desc=True)
        
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
                logger.warning("get_ml_laps: user_only=True but could not get user ID from main client")
                return [], "Could not determine user ID"
                
        result = query.execute()
        return result.data, "ML laps retrieved successfully"
    except Exception as e:
        return None, f"Failed to retrieve ML laps: {e}"


def get_ml_telemetry_points(lap_id: str, columns: Optional[list[str]] = None):
    """Retrieve ML telemetry points for a given ML lap from Supabase.

    Args:
        lap_id: UUID of the ML lap to fetch telemetry for.
        columns: Optional list of columns to select – if None, selects all.

    Returns:
        Tuple[list[dict] | None, str]
    """
    # Try multiple approaches to get an authenticated Supabase client
    supabase_client = None
    
    # First try direct import from trackpro's client
    try:
        from trackpro.database.supabase_client import supabase as app_supabase
        if app_supabase and app_supabase.is_authenticated():
            supabase_client = app_supabase.client
            return _execute_ml_telemetry_query(supabase_client, lap_id, columns)
    except (ImportError, AttributeError):
        pass
    
    # Then try the module-level supabase client
    try:
        from .client import supabase
        if supabase and hasattr(supabase, 'client') and supabase.client:
            # For diagnostics, try to get session info
            try:
                auth_session = supabase.client.auth.get_session()
                has_user = auth_session and hasattr(auth_session, 'user') and auth_session.user is not None
                if has_user:
                    supabase_client = supabase.client
                    return _execute_ml_telemetry_query(supabase_client, lap_id, columns)
            except Exception:
                pass
    except (ImportError, AttributeError):
        pass
    
    # Try explicit authentication from auth module as last resort
    try:
        from .client import supabase
        from . import auth
        if auth.is_logged_in():
            session_token = auth.get_session_token()
            if session_token and supabase.client:
                # Set session token and check if it's valid
                supabase.auth.set_session(session_token)
                try:
                    # Check if session is valid
                    auth_session = supabase.client.auth.get_session()
                    if auth_session and hasattr(auth_session, 'user') and auth_session.user:
                        # Success - return query result
                        supabase_client = supabase.client
                        return _execute_ml_telemetry_query(supabase_client, lap_id, columns)
                except Exception:
                    pass
    except Exception:
        pass
        
    # If we get here, all attempts to obtain an authenticated client failed
    return None, "Failed to obtain authenticated Supabase client for ML telemetry access"


def _execute_ml_telemetry_query(client, lap_id: str, columns: Optional[list[str]] = None):
    """Execute the actual ML telemetry points query with appropriate error handling."""
    if not lap_id:
        return None, "lap_id is required"

    all_points = []
    current_offset = 0
    page_size = 1000

    try:
        sel = "*" if columns is None else ",".join(columns)
        
        while True:
            query = (
                client.table("telemetry_points_ml")
                .select(sel)
                .eq("lap_id", lap_id)
                .order("track_position") # Ensure consistent ordering for pagination
                .range(current_offset, current_offset + page_size - 1) # Fetch one page
            )
            
            result = query.execute()

            if result.data:
                all_points.extend(result.data)
                if len(result.data) < page_size:
                    # Last page fetched
                    break
                current_offset += len(result.data) # Move to the next page offset
            else:
                # No more data or an error occurred on this page fetch
                if not all_points: # If no points fetched at all and no data on first page
                    # Check if there was an error message from PostgREST (e.g. in result.error)
                    error_message = "Failed to retrieve ML telemetry points"
                    if hasattr(result, 'error') and result.error and hasattr(result.error, 'message'):
                        error_message += f": {result.error.message}"
                    elif hasattr(result, 'message') and result.message: # some clients might put it here
                         error_message += f": {result.message}"
                    return None, error_message
                break # No more data, exit loop

        return all_points, f"Retrieved {len(all_points)} ML telemetry points"
    except Exception as e:
        # Log the full exception for better debugging
        return None, f"Failed to retrieve ML telemetry points due to an exception: {str(e)}"


def get_ml_optimizations(limit: int = 50, track_id: int = None):
    """Fetch ML optimization records from the `ml_optimizations` table.

    Args:
        limit: Maximum number of optimization records to return (default 50).
        track_id: If provided, filter optimizations by this track ID.

    Returns:
        Tuple of (list[dict] | None, str): Data and status message.
    """
    # Import the main authenticated client
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
    except ImportError:
        logger.error("Could not import main Supabase client in get_ml_optimizations")
        return None, "Internal error: Cannot access database client"

    # Check authentication using the main client
    if not main_supabase.is_authenticated():
        return None, "Not logged in. Please log in to view ML optimizations"

    try:
        # Use the main client for the query
        query = main_supabase.client.table("ml_optimizations").select("*").limit(limit).order("created_at", desc=True)
        
        if track_id:
            query = query.eq("track_id", track_id)
                
        result = query.execute()
        return result.data, "ML optimizations retrieved successfully"
    except Exception as e:
        return None, f"Failed to retrieve ML optimizations: {e}"



# --- End ML Lap helpers ---

# --- End Telemetry / Lap helpers --- 