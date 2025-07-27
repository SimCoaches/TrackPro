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
            
            # Now get laps filtering for valid laps only
            result = main_supabase.client.table("laps").select("*").eq("session_id", session_id).eq("is_valid", True).order("lap_number").limit(limit).execute()
            
            if result.data:
                # Filter out laps with invalid lap times (lap_time = -1)
                valid_laps = [lap for lap in result.data if lap.get('lap_time', -1) > 0]
                logger.info(f"Found {len(result.data)} database-valid laps for session {session_id}, {len(valid_laps)} have valid lap times")
                return valid_laps, f"Found {len(valid_laps)} valid laps"
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
    logger.info(f"🔍 [DB DEBUG] get_telemetry_points called with lap_id: {lap_id}")
    
    # Use the main authenticated Supabase client from trackpro
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
        logger.info(f"🔍 [DB DEBUG] Main supabase client imported: {main_supabase is not None}")
        
        if main_supabase and main_supabase._client:
            logger.info(f"🔍 [DB DEBUG] Main supabase client available: {main_supabase._client is not None}")
            logger.info(f"🔍 [DB DEBUG] Client offline mode: {getattr(main_supabase, '_offline_mode', 'unknown')}")
            
            # Test authentication status
            try:
                is_authenticated = main_supabase.is_authenticated()
                logger.info(f"🔍 [DB DEBUG] Is authenticated: {is_authenticated}")
                
                if is_authenticated:
                    user = main_supabase.get_user()
                    if user and hasattr(user, 'user') and user.user:
                        logger.info(f"🔍 [DB DEBUG] Authenticated user: {user.user.email}")
                    else:
                        logger.warning(f"🔍 [DB DEBUG] User object: {user}")
                else:
                    logger.warning("🔍 [DB DEBUG] Not authenticated - checking saved auth")
                    if hasattr(main_supabase, '_saved_auth') and main_supabase._saved_auth:
                        logger.info(f"🔍 [DB DEBUG] Saved auth exists with remember_me: {main_supabase._saved_auth.get('remember_me', 'not set')}")
                        # Try to restore session
                        logger.info("🔍 [DB DEBUG] Attempting to restore session for telemetry access")
                        try:
                            session_restored = main_supabase._restore_session_safely()
                            logger.info(f"🔍 [DB DEBUG] Session restoration result: {session_restored}")
                        except Exception as restore_e:
                            logger.error(f"🔍 [DB DEBUG] Session restoration failed: {restore_e}")
                    else:
                        logger.error("🔍 [DB DEBUG] No saved auth available")
            except Exception as auth_e:
                logger.error(f"🔍 [DB DEBUG] Error checking authentication: {auth_e}")
            
            return _execute_telemetry_query(main_supabase._client, lap_id, columns)
        else:
            logger.error("🔍 [DB DEBUG] Main Supabase client not available")
            return None, "Main Supabase client not available"
    except ImportError:
        logger.error("🔍 [DB DEBUG] Could not import main Supabase client")
        return None, "Could not import main Supabase client"

def _execute_telemetry_query(client, lap_id: str, columns: Optional[list[str]] = None):
    """Execute the actual telemetry points query with appropriate error handling."""
    logger.info(f"🔍 [DB DEBUG] _execute_telemetry_query called with lap_id: {lap_id}, columns: {columns}")
    
    if not lap_id:
        logger.error("🔍 [DB DEBUG] lap_id is required but not provided")
        return None, "lap_id is required"

    logger.info(f"🔍 [DB DEBUG] Client type: {type(client)}")
    logger.info(f"🔍 [DB DEBUG] Client has table method: {hasattr(client, 'table')}")

    all_points = []
    current_offset = 0
    # Supabase default limit is 1000, so we use that as page size.
    # This can be configured in Supabase project settings (Settings -> API -> Max Rows)
    # but client-side pagination is safer for potentially very large datasets.
    page_size = 1000
    max_pages = 50  # Safety limit: 50 pages = up to 50,000 points (should handle even Nurburgring)

    try:
        sel = "*" if columns is None else ",".join(columns)
        logger.info(f"🔍 [DB DEBUG] Selection string: {sel}")
        
        page_count = 0
        while True:
            page_count += 1
            
            # Safety check to prevent infinite loops
            if page_count > max_pages:
                logger.warning(f"🔍 [DB DEBUG] Safety limit reached: {max_pages} pages fetched ({len(all_points)} points total). Stopping pagination.")
                break
                
            logger.info(f"🔍 [DB DEBUG] Fetching page {page_count}, offset: {current_offset}, page_size: {page_size}")
            
            try:
                query = (
                    client.table("telemetry_points")
                    .select(sel)
                    .eq("lap_id", lap_id)
                    .order("track_position", desc=False)
                    .order("id", desc=False)  # Ensure consistent deterministic ordering for pagination
                    .range(current_offset, current_offset + page_size - 1)  # Fetch one page - DON'T use .limit() with .range()
                )
                
                logger.info(f"🔍 [DB DEBUG] Executing query for page {page_count} - range({current_offset}, {current_offset + page_size - 1})")
                result = query.execute()
                logger.info(f"🔍 [DB DEBUG] Query executed successfully for page {page_count}")
                logger.info(f"🔍 [DB DEBUG] Result type: {type(result)}")
                logger.info(f"🔍 [DB DEBUG] Result has data: {hasattr(result, 'data')}")
                
                if hasattr(result, 'data') and result.data and len(result.data) > 0:
                    page_points = len(result.data)
                    logger.info(f"🔍 [DB DEBUG] Page {page_count} returned {page_points} points")
                    all_points.extend(result.data)
                    current_offset += len(result.data)
                    logger.info(f"🔍 [DB DEBUG] Moving to next page, new offset: {current_offset}")
                    
                    # Continue to next page - we only stop when we get 0 results on a page
                    # This ensures we fetch ALL telemetry points, even for 50,000+ point tracks
                else:
                    logger.info(f"🔍 [DB DEBUG] Page {page_count} returned no data - pagination complete")
                    # No more data or an error occurred on this page fetch
                    if not all_points: # If no points fetched at all and no data on first page
                        # Check if there was an error message from PostgREST (e.g. in result.error)
                        error_message = "Failed to retrieve telemetry points"
                        if hasattr(result, 'error') and result.error and hasattr(result.error, 'message'):
                            error_message += f": {result.error.message}"
                            logger.error(f"🔍 [DB DEBUG] PostgREST error: {result.error.message}")
                        elif hasattr(result, 'message') and result.message: # some clients might put it here
                             error_message += f": {result.message}"
                             logger.error(f"🔍 [DB DEBUG] Result message: {result.message}")
                        logger.error(f"🔍 [DB DEBUG] No points retrieved on first page, returning error: {error_message}")
                        return None, error_message
                    break # No more data, exit loop
            except Exception as query_e:
                logger.error(f"🔍 [DB DEBUG] Query execution failed on page {page_count}: {query_e}", exc_info=True)
                if not all_points:
                    return None, f"Query execution failed: {str(query_e)}"
                else:
                    logger.warning(f"🔍 [DB DEBUG] Query failed but {len(all_points)} points already retrieved, continuing with partial data")
                    break

        logger.info(f"🔍 [DB DEBUG] Total pages fetched: {page_count}")
        logger.info(f"🔍 [DB DEBUG] Total points retrieved: {len(all_points)}")
        
        if all_points:
            # Log sample of data for debugging
            sample_point = all_points[0]
            logger.info(f"🔍 [DB DEBUG] Sample point fields: {list(sample_point.keys())}")
            logger.info(f"🔍 [DB DEBUG] Sample track position: {sample_point.get('track_position', 'missing')}")
        
        return all_points, f"Retrieved {len(all_points)} telemetry points"
    except Exception as e:
        # Log the full exception for better debugging
        # Consider using logger.exception("Error in _execute_telemetry_query:") if logger is configured
        logger.error(f"🔍 [DB DEBUG] Critical exception in _execute_telemetry_query: {str(e)}", exc_info=True)
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
            # Get user directly from the main client with improved extraction logic
            user_id = None
            
            # Try multiple methods to get the current user ID
            try:
                # Method 1: Try get_user() 
                user = main_supabase.get_user()
                if user:
                    if hasattr(user, 'id'):
                        user_id = user.id
                        logger.info(f"DATABASE DEBUG: Got user_id from user.id: {user_id}")
                    elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                        user_id = user.user.id
                        logger.info(f"DATABASE DEBUG: Got user_id from user.user.id: {user_id}")
                    elif isinstance(user, dict) and 'user' in user and user['user'] and user['user'].get('id'):
                        user_id = user['user']['id']
                        logger.info(f"DATABASE DEBUG: Got user_id from dict user['user']['id']: {user_id}")
                    elif isinstance(user, dict) and user.get('id'):
                        user_id = user['id']
                        logger.info(f"DATABASE DEBUG: Got user_id from dict user['id']: {user_id}")
                
                # Method 2: Try get_session() as fallback
                if not user_id:
                    logger.info("DATABASE DEBUG: get_user() failed, trying get_session()")
                    session = main_supabase.client.auth.get_session()
                    if session and hasattr(session, 'user') and session.user:
                        user_id = session.user.id
                        logger.info(f"DATABASE DEBUG: Got user_id from session.user.id: {user_id}")
                
                # Method 3: Try alternative user extraction
                if not user_id:
                    logger.info("DATABASE DEBUG: session method failed, trying alternative extraction")
                    try:
                        user_response = main_supabase.client.auth.get_user()
                        if hasattr(user_response, 'user') and user_response.user:
                            user_id = user_response.user.id
                            logger.info(f"DATABASE DEBUG: Got user_id from auth.get_user().user.id: {user_id}")
                        elif hasattr(user_response, 'data') and hasattr(user_response.data, 'user') and user_response.data.user:
                            user_id = user_response.data.user.id
                            logger.info(f"DATABASE DEBUG: Got user_id from auth.get_user().data.user.id: {user_id}")
                    except Exception as alt_e:
                        logger.warning(f"DATABASE DEBUG: Alternative user extraction failed: {alt_e}")
            except Exception as e:
                logger.error(f"DATABASE DEBUG: Error during user extraction: {e}")
            
            if user_id:
                # Filter by user_id
                original_count = len(result_data)
                original_sessions = result_data[:]  # Store original sessions before filtering
                result_data = [session for session in result_data if session.get('user_id') == user_id]
                logger.info(f"DATABASE DEBUG: Filtering sessions by user_id: {user_id}")
                logger.info(f"DATABASE DEBUG: Filtered from {original_count} to {len(result_data)} sessions")
                
                # Debug: Show some session user_ids for comparison
                if len(result_data) == 0 and original_count > 0:
                    logger.warning("DATABASE DEBUG: No sessions matched user_id filter!")
                    # Show what user_ids exist in the original sessions for debugging
                    sample_user_ids = set(session.get('user_id') for session in original_sessions[:5])  # First 5 sessions
                    logger.warning(f"DATABASE DEBUG: Sample session user_ids: {sample_user_ids}")
                    logger.warning(f"DATABASE DEBUG: Current user_id: {user_id}")
                    logger.warning("DATABASE DEBUG: This suggests either authentication issue or user_id mismatch")
            else:
                logger.error("get_sessions: user_only=True but could not get user ID from any method")
                logger.error("DATABASE DEBUG: All user extraction methods failed:")
                logger.error(f"DATABASE DEBUG: main_supabase.get_user() returned: {main_supabase.get_user()}")
                try:
                    session = main_supabase.client.auth.get_session()
                    logger.error(f"DATABASE DEBUG: main_supabase.client.auth.get_session() returned: {session}")
                except Exception as session_e:
                    logger.error(f"DATABASE DEBUG: get_session() failed with: {session_e}")
                return [], "Could not determine user ID - authentication may have expired"
        else:
            logger.info("DATABASE DEBUG: Not filtering by user - getting all sessions")
                
        logger.info(f"DATABASE DEBUG: Found {len(result_data)} sessions")

        # Process results to flatten track/car names and include track length
        processed_data = []
        if result_data:
            for session in result_data:
                session_id = session.get('id')
                
                # Keep the nested structure for UI components that expect it,
                # but also provide flattened names for convenience.
                if 'tracks' not in session:
                    session['tracks'] = {}
                if 'cars' not in session:
                    session['cars'] = {}

                session['track_name'] = session.get('tracks', {}).get('name', 'Unknown Track') if session.get('tracks') else 'Unknown Track'
                session['car_name'] = session.get('cars', {}).get('name', 'Unknown Car') if session.get('cars') else 'Unknown Car'
                
                # CRITICAL FIX: Extract and include track length from database
                track_length = session.get('tracks', {}).get('length_meters', None) if session.get('tracks') else None
                if track_length:
                    session['track_length'] = track_length
                
                processed_data.append(session)

        return processed_data, "Sessions retrieved successfully"
    except Exception as e:
        logger.error(f"Error in get_sessions: {e}", exc_info=True)
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
    # Use the main authenticated Supabase client from trackpro
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
        if main_supabase and main_supabase._client:
            return _execute_ml_telemetry_query(main_supabase._client, lap_id, columns)
        else:
            return None, "Main Supabase client not available"
    except ImportError:
        return None, "Could not import main Supabase client"


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
                .order("track_position", desc=False) # Ensure consistent ordering for pagination
                .range(current_offset, current_offset + page_size - 1) # Fetch one page - DON'T use .limit() with .range()
            )
            
            result = query.execute()

            if result.data and len(result.data) > 0:
                all_points.extend(result.data)
                current_offset += len(result.data) # Move to the next page offset
                
                # Continue to next page - we only stop when we get 0 results
                # This ensures we fetch ALL ML telemetry points
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

def get_super_lap_telemetry_points(super_lap_id: str, columns: Optional[list[str]] = None):
    """Get reconstructed telemetry points for a SuperLap by combining sector data from different laps."""
    if not super_lap_id:
        return None, "super_lap_id is required"

    # Use the main authenticated Supabase client from trackpro
    try:
        from trackpro.database.supabase_client import supabase as main_supabase
        if main_supabase and main_supabase._client:
            return _execute_super_lap_telemetry_query(main_supabase._client, super_lap_id, columns)
        else:
            return None, "Main Supabase client not available"
    except ImportError:
        return None, "Could not import main Supabase client"


def _execute_super_lap_telemetry_query(client, super_lap_id: str, columns: Optional[list[str]] = None):
    """Execute SuperLap telemetry reconstruction using the EXACT same pattern as _execute_telemetry_query."""
    if not super_lap_id:
        return None, "super_lap_id is required"

    try:
        # First, get the SuperLap data to understand its sector combination
        super_lap_query = client.table("super_laps_ml").select("*").eq("id", super_lap_id)
        super_lap_result = super_lap_query.execute()
        
        if not super_lap_result.data:
            return None, f"SuperLap with ID {super_lap_id} not found"
        
        super_lap = super_lap_result.data[0]
        sector_combination = super_lap.get('sector_combination')
        
        print(f"SuperLap {super_lap_id}: {super_lap.get('name', 'Unknown')}")
        
        # Handle array-based sector combination
        if isinstance(sector_combination, list) and len(sector_combination) > 0:
            result, message = _get_sector_telemetry_using_working_method(client, sector_combination, columns)
            if result is None:
                # Sector reconstruction failed - try fallback
                logger.warning(f"🚨 SUPERLAP DEBUG: Sector reconstruction failed ({message}), trying fallback method")
                return _get_fallback_telemetry_for_superlap(client, super_lap, columns)
            return result, message
        
        # Handle time-based format - use fallback
        elif isinstance(sector_combination, dict):
            print("Time-based sector format - trying fallback")
            return _get_fallback_telemetry_for_superlap(client, super_lap, columns)
        
        else:
            return None, f"Invalid sector_combination format: {type(sector_combination)}"
            
    except Exception as e:
        return None, f"Failed to retrieve SuperLap telemetry due to an exception: {str(e)}"


def _get_sector_telemetry_using_working_method(client, sector_combination, columns: Optional[list[str]] = None):
    """Get telemetry for each sector and rebuild a continuous lap by recalculating time and distance."""
    reconstructed_points = []
    page_size = 1000
    
    # Keep track of the total time and distance of the reconstructed lap
    total_lap_time = 0.0
    total_lap_distance = 0.0
    
    # Store sector data for proper distance normalization
    all_sector_data = []
    
    try:
        sel = "*" if columns is None else ",".join(columns)
        
        # Debug: Log sector combination details
        logger.info(f"🔍 SUPERLAP DEBUG: Processing sector combination with {len(sector_combination)} sectors")
        for i, sector_ref in enumerate(sector_combination):
            logger.info(f"  Sector {i+1}: lap_id={sector_ref.get('lap_id')}, sector_number={sector_ref.get('sector_number')}")
        
        # First pass: Collect all sector data without modifying distances
        for i, sector_ref in enumerate(sector_combination):
            lap_id = sector_ref.get('lap_id')
            sector_number = sector_ref.get('sector_number')
            
            if not lap_id or not sector_number:
                logger.warning(f"🚨 SUPERLAP DEBUG: Skipping invalid sector {i+1} - missing lap_id or sector_number")
                continue
            
            logger.info(f"🔍 SUPERLAP DEBUG: Processing sector {sector_number} from lap {lap_id}")
            
            # First check if the lap exists
            lap_check = client.table("laps").select("id").eq("id", lap_id).limit(1).execute()
            if not lap_check.data:
                logger.error(f"❌ SUPERLAP DEBUG: Lap {lap_id} does not exist in database - skipping sector {sector_number}")
                continue
            
            # Fetch all telemetry points for the current source sector
            current_offset = 0
            sector_points = []
            while True:
                query = (
                    client.table("telemetry_points")
                    .select(sel)
                    .eq("lap_id", lap_id)
                    .eq("current_sector", sector_number)
                    .order("track_position", desc=False)
                    .range(current_offset, current_offset + page_size - 1)  # DON'T use .limit() with .range()
                )
                result = query.execute()

                if result.data and len(result.data) > 0:
                    sector_points.extend(result.data)
                    current_offset += len(result.data)
                    # Continue to next page - we only stop when we get 0 results
                    # This ensures we fetch ALL telemetry points for each sector
                else:
                    break
            
            if sector_points:
                logger.info(f"✅ SUPERLAP DEBUG: Found {len(sector_points)} telemetry points for sector {sector_number}")
                
                # Store sector data with metadata for normalization
                sector_data = {
                    'sector_number': sector_number,
                    'points': sector_points,
                    'start_time': sector_points[0].get('current_time', 0.0),
                    'end_time': sector_points[-1].get('current_time', 0.0),
                    'start_distance': sector_points[0].get('track_position', 0.0),
                    'end_distance': sector_points[-1].get('track_position', 0.0)
                }
                all_sector_data.append(sector_data)
                
                logger.info(f"📊 SUPERLAP DEBUG: Sector {sector_number} spans time {sector_data['start_time']:.3f}s to {sector_data['end_time']:.3f}s, distance {sector_data['start_distance']:.1f}m to {sector_data['end_distance']:.1f}m")
            else:
                logger.error(f"❌ SUPERLAP DEBUG: No telemetry points found for sector {sector_number} from lap {lap_id}")

        if not all_sector_data:
            logger.warning("🚨 SUPERLAP DEBUG: No valid sector data found")
            return None, "SuperLap telemetry reconstruction failed - no valid sector data"
        
        # Get track length for proper scaling
        track_length = None
        if all_sector_data:
            # Try to get track length from one of the sector's session
            first_sector = all_sector_data[0]
            if first_sector['points']:
                try:
                    # Try to get the session to find track length
                    sample_point = first_sector['points'][0]
                    if 'lap_id' in sample_point:
                        lap_query = client.table("laps").select("session_id").eq("id", sample_point['lap_id']).limit(1).execute()
                        if lap_query.data:
                            session_id = lap_query.data[0]['session_id']
                            session_query = client.table("sessions").select("tracks(length_meters)").eq("id", session_id).limit(1).execute()
                            if session_query.data and session_query.data[0].get('tracks'):
                                track_length = session_query.data[0]['tracks'].get('length_meters')
                                logger.info(f"🏁 SUPERLAP DEBUG: Retrieved track length: {track_length}m")
                except Exception as e:
                    logger.warning(f"Could not retrieve track length: {e}")
        
        # Calculate original distance span of all sectors
        min_original_distance = min(sector['start_distance'] for sector in all_sector_data)
        max_original_distance = max(sector['end_distance'] for sector in all_sector_data)
        original_distance_span = max_original_distance - min_original_distance
        
        logger.info(f"🔍 SUPERLAP DEBUG: Original distance span: {min_original_distance:.1f}m to {max_original_distance:.1f}m (span: {original_distance_span:.1f}m)")
        
        # If we have track length, use it for scaling, otherwise use the original span
        target_track_length = track_length if track_length and track_length > 0 else original_distance_span
        
        # Calculate scaling factor to ensure superlap spans full track length
        if original_distance_span > 0:
            distance_scale_factor = target_track_length / original_distance_span
        else:
            distance_scale_factor = 1.0
            
        logger.info(f"🔧 SUPERLAP DEBUG: Using track length {target_track_length}m with scale factor {distance_scale_factor:.3f}")
        
        # Second pass: Build the reconstructed lap with proper scaling
        for i, sector_data in enumerate(all_sector_data):
            sector_number = sector_data['sector_number']
            sector_points = sector_data['points']
            
            # Calculate time offset for this sector
            sector_start_time = sector_data['start_time']
            sector_duration = sector_data['end_time'] - sector_start_time
            
            # Calculate distance offset and scaling for this sector
            sector_start_distance = sector_data['start_distance']
            
            # Process each point with proper scaling
            for point in sector_points:
                # Time calculation (incremental as before)
                time_in_sector = point.get('current_time', 0.0) - sector_start_time
                new_time = total_lap_time + time_in_sector
                
                # Distance calculation with proper scaling
                original_distance_in_sector = point.get('track_position', 0.0) - sector_start_distance
                # Normalize to 0-based distance for this point relative to the whole superlap
                normalized_distance_from_start = (point.get('track_position', 0.0) - min_original_distance) * distance_scale_factor
                
                # Create new point with scaled values
                new_point = point.copy()
                new_point['current_time'] = new_time
                new_point['track_position'] = normalized_distance_from_start
                reconstructed_points.append(new_point)
            
            # Update totals
            total_lap_time += sector_duration
            
            logger.info(f"✅ SUPERLAP DEBUG: Sector {sector_number} processed. Duration: {sector_duration:.3f}s")
        
        # Calculate final distance span
        if reconstructed_points:
            final_min_distance = min(p['track_position'] for p in reconstructed_points)
            final_max_distance = max(p['track_position'] for p in reconstructed_points)
            final_distance_span = final_max_distance - final_min_distance
            
            logger.info(f"🏁 SUPERLAP DEBUG: Reconstruction complete. Total points: {len(reconstructed_points)}, Final time: {total_lap_time:.3f}s")
            logger.info(f"🏁 SUPERLAP DEBUG: Final distance span: {final_min_distance:.1f}m to {final_max_distance:.1f}m (span: {final_distance_span:.1f}m)")
            
            return reconstructed_points, f"Retrieved {len(reconstructed_points)} SuperLap telemetry points spanning {final_distance_span:.1f}m"
        else:
            logger.warning("🚨 SUPERLAP DEBUG: No telemetry points could be reconstructed")
            return None, "SuperLap telemetry reconstruction failed - no points generated"
            
    except Exception as e:
        logger.error(f"Error reconstructing SuperLap telemetry: {e}", exc_info=True)
        return None, f"Failed to retrieve SuperLap telemetry due to an exception: {str(e)}"


def _get_fallback_telemetry_for_superlap(client, super_lap, columns: Optional[list[str]] = None):
    """Get fallback telemetry for time-based SuperLaps by finding the best lap for this car/track."""
    try:
        # First try the human benchmark lap if it exists
        benchmark_lap_id = super_lap.get('human_benchmark_lap_id')
        if benchmark_lap_id:
            print(f"Using human benchmark lap {benchmark_lap_id}")
            return get_telemetry_points(benchmark_lap_id, columns)
        
        # Get car and track IDs from the SuperLap
        car_id = super_lap.get('car_id')
        track_id = super_lap.get('track_id')
        
        if not car_id or not track_id:
            return None, "SuperLap missing car_id or track_id for fallback lookup"
        
        print(f"Searching for best lap for car_id={car_id}, track_id={track_id}")
        
        # Find the best lap for this car/track combination using a simple, working query
        # Use the same approach as the working telemetry queries
        sessions_result = client.table("sessions").select("id").eq("car_id", car_id).eq("track_id", track_id).execute()
        
        if not sessions_result.data:
            return None, f"No sessions found for car_id={car_id}, track_id={track_id}"
        
        # Get session IDs
        session_ids = [s['id'] for s in sessions_result.data]
        print(f"Found {len(session_ids)} sessions for this car/track combo")
        
        # Find best lap from these sessions
        best_lap = None
        best_time = float('inf')
        
        for session_id in session_ids:
            laps_result = client.table("laps").select("id, lap_time").eq(
                "session_id", session_id
            ).eq("is_valid", True).order("lap_time").limit(5).execute()
            
            if laps_result.data:
                for lap in laps_result.data:
                    lap_time = lap.get('lap_time', float('inf'))
                    if lap_time < best_time:
                        best_time = lap_time
                        best_lap = lap
        
        if best_lap:
            best_lap_id = best_lap['id']
            print(f"Using best lap {best_lap_id} (time: {best_time:.3f}s) as SuperLap fallback")
            return get_telemetry_points(best_lap_id, columns)
        else:
            return None, f"No valid laps found for car_id={car_id}, track_id={track_id}"
            
    except Exception as e:
        print(f"Error in fallback telemetry lookup: {e}")
        return None, f"Error getting fallback telemetry: {str(e)}"

# --- End Telemetry / Lap helpers --- 