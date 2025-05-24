import irsdk
from supabase import Client # Only import Client type hint
import time
import os
import sys
import subprocess
import yaml
import threading # Added for potential stop event
from typing import Optional
import traceback
import json
import datetime
from .connection_manager import iracing_connection_manager

# --- Configuration ---
# Use dynamic path based on current Python environment
IRSDK_EXE_PATH = os.path.join(sys.exec_prefix, 'Scripts', 'irsdk.exe')
DATA_TXT_PATH = "data.txt" # Output file in the script's running directory

# --- iRacing SDK Initialization (kept global for simplicity in the module) ---
# Ensure only one instance if multiple parts of TrackPro might use it
ir = irsdk.IRSDK()

# --- State Variables (module level) ---
# These track the state across monitoring cycles within the thread
last_session_unique_id = -1
is_connected = False
last_processed_iracing_track_id = None
last_processed_iracing_car_id = None
last_processed_track_config = None
last_session_id = None
last_subsession_id = None
current_session_uuid = None

# Event to signal the monitoring thread to stop (optional but good practice)
should_stop = False

# Global reference to monitor thread for cleanup
_monitor_thread = None

def stop_monitoring():
    """Stop the iRacing monitoring loop."""
    global should_stop, _monitor_thread
    print("Monitor: Stopping iRacing monitoring thread...")
    should_stop = True
    
    # Wait for the thread to finish with a timeout
    if _monitor_thread and _monitor_thread.is_alive():
        try:
            print("Monitor: Waiting for monitor thread to finish...")
            _monitor_thread.join(timeout=5.0)
            if _monitor_thread.is_alive():
                print("Monitor: Warning - monitor thread did not finish in time")
            else:
                print("Monitor: Monitor thread stopped successfully")
        except Exception as e:
            print(f"Monitor: Error waiting for monitor thread to finish: {e}")
    
    # Reset the thread reference
    _monitor_thread = None
    print("Monitor: Monitoring stopped")

def _raw_iracing_connection():
    """Raw connection attempt - for use by the smart connection manager."""
    try:
        # First check if iRacing is already connected
        if ir.is_initialized and ir.is_connected:
            return True
            
        # Otherwise try to connect
        startup_result = ir.startup()
        
        # Check both initialized and connected flags
        connection_result = ir.is_initialized and ir.is_connected
        
        if not connection_result:
            ir.shutdown()
            
        return connection_result
    except Exception as e:
        print(f"Error in raw iRacing connection: {str(e)}")
        return False

def is_iracing_available():
    """Check if iRacing is available and can be connected to - Phase 3 Optimized"""
    # BUGFIX: Don't use SmartConnectionManager for connectivity checks during monitoring
    # Only use it for actual connection attempts. For monitoring, do a simple direct check.
    try:
        # Direct check without going through the smart connection manager
        # This avoids false disconnections due to rate limiting/backoff
        if ir.is_initialized and ir.is_connected:
            return True
        else:
            # Only use smart connection manager for actual connection attempts
            return iracing_connection_manager.attempt_connection()
    except Exception as e:
        print(f"Error checking iRacing availability: {e}")
        return False

def get_session_info_update_count():
    """Get the current session info update count from iRacing"""
    try:
        if not ir.is_initialized:
            ir.startup()
        if ir.is_connected:
            # Try to parse data file when session info updates
            if run_irsdk_parse():
                return ir.session_info_update
        return 0
    except Exception as e:
        print(f"Error getting session info update count: {str(e)}")
        return 0

def _find_or_create_base_track(supabase: Client, track_name: str, iracing_track_id: int, location: str = None, length_meters: float = None) -> int:
    """Find or create base track, returning its DB ID."""
    if not supabase or not track_name:
        print("Missing required data for base track lookup/creation")
        return None
    
    try:
        # First, try to get directly using the track ID if available
        if iracing_track_id is not None:
            try:
                # Look for existing base track with this iracing_track_id
                response = supabase.table('tracks') \
                    .select('id, name, location, length_meters') \
                    .eq('iracing_track_id', iracing_track_id) \
                    .is_('config', 'NULL') \
                    .execute()
                
                if response.data and len(response.data) > 0:
                    # Found by iracing_track_id
                    base_id = response.data[0]['id']
                    print(f"Found existing base track with iracing_track_id={iracing_track_id}, id={base_id}")
                    
                    # Update any missing information if we have it
                    if (location or length_meters):
                        update_data = {}
                        if location and not response.data[0].get('location'):
                            update_data['location'] = location
                        if length_meters and not response.data[0].get('length_meters'):
                            update_data['length_meters'] = length_meters
                            
                        if update_data:
                            supabase.table('tracks') \
                                .update(update_data) \
                                .eq('id', base_id) \
                                .execute()
                            print(f"Updated base track ({base_id}) with additional data: {update_data}")
                            
                    return base_id
            except Exception as e:
                print(f"Error finding base track by iRacing ID: {str(e)}")
                # Continue to next search method
        
        # Try to find by name with no config
        try:
            response = supabase.table('tracks') \
                .select('id, name') \
                .eq('name', track_name) \
                .is_('config', 'NULL') \
                .is_('base_track_id', 'NULL') \
                .execute()
                
            if response.data and len(response.data) > 0:
                # Found by name
                base_id = response.data[0]['id']
                print(f"Found existing base track with name={track_name}, id={base_id}")
                return base_id
        except Exception as e:
            print(f"Error finding base track by name: {str(e)}")
            # Continue to creating a new base track
        
        # If we get here, we need to create a new base track
        # Create new base track
        print(f"Creating new base track: '{track_name}'")
        insert_data = {
            'name': track_name,
            'is_default_config': True, # Base tracks represent the 'default'
            'location': location,
            'length_meters': length_meters
        }
        # Only include track ID if it's a base track ID (not a config-specific ID)
        if iracing_track_id is not None:
            insert_data['iracing_track_id'] = iracing_track_id
            
        # Remove None values before insert
        insert_data = {k: v for k, v in insert_data.items() if v is not None}
        
        print(f"Creating base track with data: {insert_data}")
        
        new_base = supabase.table('tracks').insert(insert_data).execute()
        
        # Error handling
        if hasattr(new_base, 'error') and new_base.error:
            print(f"Error creating base track '{track_name}' (Supabase Error): {new_base.error}")
            return None
            
        # Check if data is missing, which also indicates failure
        if not new_base.data or len(new_base.data) == 0:
            print(f"Error creating base track '{track_name}': Insert returned no data.")
            return None
            
        base_id = new_base.data[0]['id']
        print(f"Created new base track with ID: {base_id}")
        return base_id
            
    except Exception as e:
        print(f"Error in _find_or_create_base_track: {str(e)}")
        return None

def update_supabase_data(supabase, user_id, track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location):
    """Update Supabase with the latest iRacing data."""
    print(f"Updating Supabase with Track: {track_name}, Car: {car_name}, Config: {track_config}")
    
    try:
        # ------------- CAR -------------
        # Get or create car
        car_db_id = None
        
        # First, try to get directly using the iRacing car_id if available
        if car_id is not None:
            # Look for existing car with this iRacing car_id
            try:
                car_response = supabase.table('cars').select('id').eq('iracing_car_id', car_id).execute()
                if car_response.data and len(car_response.data) > 0:
                    car_db_id = car_response.data[0]['id']
                    print(f"Found existing car with iracing_car_id={car_id}, id={car_db_id}")
            except Exception as e:
                print(f"Error querying car by iracing_car_id: {str(e)}")
        
        # If not found by iRacing ID, try by name
        if not car_db_id and car_name:
            try:
                # Look for existing car with this name
                car_response = supabase.table('cars').select('id').eq('name', car_name).execute()
                if car_response.data and len(car_response.data) > 0:
                    car_db_id = car_response.data[0]['id']
                    print(f"Found existing car by name: {car_name}, id={car_db_id}")
            except Exception as e:
                print(f"Error querying car by name: {str(e)}")
        
        # If still not found, create new car
        if not car_db_id and car_name:
            try:
                car_data = {'name': car_name}
                if car_id is not None:
                    car_data['iracing_car_id'] = car_id
                    
                # Insert the car
                car_response = supabase.table('cars').insert(car_data).execute()
                if car_response.data and len(car_response.data) > 0:
                    car_db_id = car_response.data[0]['id']
                    print(f"Created new car: {car_name}, id={car_db_id}")
                else:
                    print(f"Failed to create car record for {car_name}")
            except Exception as e:
                print(f"Error creating car record: {str(e)}")
        
        # ------------- TRACK -------------
        # Get or create base track
        base_track_id = _find_or_create_base_track(
            supabase, 
            track_name, 
            track_id, 
            track_location, 
            track_length
        )
        
        if not base_track_id:
            print(f"Failed to create or find base track: {track_name}")
            return None
            
        # Get or create track configuration if applicable
        track_db_id = None
        if track_config:
            print(f"Checking for track config: '{track_config}' for base track: {track_name}")
            
            # Try to find existing track config
            try:
                config_response = supabase.table('tracks') \
                    .select('id') \
                    .eq('base_track_id', base_track_id) \
                    .eq('config', track_config) \
                    .execute()
                    
                if config_response.data and len(config_response.data) > 0:
                    track_db_id = config_response.data[0]['id']
                    print(f"Found existing track config: {track_name} - {track_config}, id={track_db_id}")
                else:
                    # Create new track config
                    track_db_id = _create_track_config(
                        supabase,
                        base_track_id,
                        track_name,
                        track_config,
                        track_id,
                        None,  # No separate config ID from iRacing
                        track_location,
                        track_length
                    )
            except Exception as e:
                print(f"Error finding or creating track config: {str(e)}")
                track_db_id = None
                
            if not track_db_id:
                print(f"Failed to process track config for {track_name} - {track_config}")
                # Fall back to base track
                track_db_id = base_track_id
                print(f"Using base track ID as fallback: {track_db_id}")
        else:
            # No config, use base track
            track_db_id = base_track_id
            
        if not track_db_id:
            print("Error: Failed to create or find track record")
            return None
            
        # ------------- SESSION -------------
        # Create a new session record
        print(f"Creating new session record: User={user_id}, TrackDB_ID={track_db_id}, CarDB_ID={car_db_id}, Type={session_type}")
        
        session_insert = supabase.table('sessions').insert({
            'user_id': user_id,
            'track_id': track_db_id,
            'car_id': car_db_id,
            'session_type': session_type,
            'session_date': 'now()',
            'created_at': 'now()'
        }).execute()
        
        print(f"Session insert response: {session_insert.data}")
        
        if not session_insert.data or len(session_insert.data) == 0:
            print("Error: Failed to create session record")
            return None
            
        session_id = session_insert.data[0]['id']
        print(f"Session record created successfully. UUID: {session_id}")
        
        # Save the session ID to a local file for persistence between app restarts
        try:
            # Create a directory to store session data
            os.makedirs(os.path.expanduser("~/Documents/TrackPro/Sessions"), exist_ok=True)
            
            # Create or update a file with active sessions
            session_file = os.path.join(os.path.expanduser("~/Documents/TrackPro/Sessions"), "active_sessions.json")
            
            # Load existing sessions if file exists
            sessions_data = {}
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r') as f:
                        sessions_data = json.load(f)
                except json.JSONDecodeError:
                    # File exists but is not valid JSON, start fresh
                    sessions_data = {}
            
            # Add the new session
            sessions_data[session_id] = {
                'track_name': track_name,
                'car_name': car_name,
                'track_config': track_config,
                'session_type': session_type,
                'timestamp': datetime.datetime.now().isoformat(),
                'user_id': user_id
            }
            
            # Write back to file
            with open(session_file, 'w') as f:
                json.dump(sessions_data, f)
                
            print(f"Session {session_id} saved to local persistence file")
        except Exception as e:
            print(f"Warning: Could not save session to local file: {e}")
        
        return session_id

    except Exception as e:
        print(f"Error updating Supabase data: {str(e)}")
        traceback.print_exc()
        return None

def create_supabase_session(supabase: Client, user_id_str, db_track_id, db_car_id, session_type):
    """Creates a new session record and returns its UUID if successful."""
    session_uuid = None # Initialize return value
    if not supabase: # Check passed-in client
        print("Supabase client not provided to create_supabase_session.", file=sys.stderr)
        return session_uuid
    # ... (rest of the function is identical to the previous version) ...
    if not user_id_str or not db_track_id or not db_car_id:
        print("Missing required data for session creation (UserID, TrackDB_ID, CarDB_ID).", file=sys.stderr)
        return session_uuid
    print(f"Creating new session record: User={user_id_str}, TrackDB_ID={db_track_id}, CarDB_ID={db_car_id}, Type={session_type}")
    try:
        session_data = {
            'user_id': user_id_str,
            'track_id': db_track_id,
            'car_id': db_car_id,
            'session_type': session_type,
        }
        response = supabase.table('sessions').insert(session_data).execute()
        print(f"Session insert response: {response.data}")
        if response.data and response.data[0].get('id') is not None:
             session_uuid = response.data[0]['id'] # Get the returned UUID
             print(f"Session record created successfully. UUID: {session_uuid}")
             # return True # Changed to return UUID
        else:
             print(f"Session insert failed or did not return data. Status: {getattr(response, 'status_code', 'N/A')}")
             # return False

    except Exception as e:
        print(f"Error creating Supabase session record: {e}", file=sys.stderr)
        # return False
    return session_uuid # Return the UUID or None


def run_irsdk_parse():
    """Parse iRacing data directly using the irsdk Python module instead of an external executable."""
    try:
        # If not initialized, try to initialize
        if not ir.is_initialized:
            ir.startup()
            
        # If successfully connected, get the latest data
        if ir.is_connected:
            # Parse data directly to a file
            ir.parse_to(DATA_TXT_PATH)
            print("Successfully parsed iRacing data to file using Python module")
            return True
        else:
            print("Failed to connect to iRacing for parsing")
            return False
    except Exception as e:
        print(f"Error parsing iRacing data: {e}", file=sys.stderr)
        print(traceback.format_exc())
        return False

def parse_data_file():
    """Parse the data.txt file to get track and car info."""
    track_name = None
    car_name = None
    track_id = None
    car_id = None
    session_type = None
    session_id = None
    subsession_id = None
    track_config = None
    track_length = None
    track_location = None
    
    try:
        with open(DATA_TXT_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract YAML section
        yaml_end_marker = '...'
        yaml_section = content
        if yaml_end_marker in content:
            yaml_section = content.split(yaml_end_marker, 1)[0]
        else:
            print("Warning: YAML end marker '...' not found. Attempting heuristic split.")
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if i > 0 and not line.startswith(' ') and '   ' in line:
                    yaml_section = "\n".join(lines[:i])
                    break

        if not yaml_section.strip():
            print("Warning: Extracted YAML section is empty.")
            return track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location

        data = yaml.safe_load(yaml_section)
        if not data:
            print("Warning: Parsed YAML data is empty or invalid.")
            return track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location

        weekend_info = data.get('WeekendInfo', {})
        driver_info = data.get('DriverInfo', {})
        session_info_wrapper = data.get('SessionInfo', {})
        sessions_list = session_info_wrapper.get('Sessions', [])

        # Get session identifiers
        session_id = weekend_info.get('SessionID')  # Unique identifier for this session
        subsession_id = weekend_info.get('SubSessionID')  # Unique identifier for this subsession

        # Get track information
        track_name = weekend_info.get('TrackDisplayName')
        track_id = weekend_info.get('TrackID')
        track_length = weekend_info.get('TrackLength')
        track_location = weekend_info.get('TrackCity')
        
        if not track_location and weekend_info.get('TrackCountry'):
            track_location = weekend_info.get('TrackCountry')
            
        # Convert track length to meters if needed (iRacing uses kilometers)
        if track_length:
            try:
                # Remove 'km' and any spaces before converting
                if isinstance(track_length, str):
                    track_length = track_length.replace('km', '').strip()
                track_length = float(track_length) * 1000  # Convert km to meters
            except (ValueError, TypeError):
                print(f"Warning: Failed to convert track length '{track_length}' to float")
                track_length = None
        
        # Extract track configuration
        track_config = weekend_info.get('TrackConfigName', '')
        if not track_config:
            # Try to extract from track name if format is "Track Name - Config"
            if track_name and ' - ' in track_name:
                track_parts = track_name.split(' - ', 1)
                if len(track_parts) == 2:
                    track_name = track_parts[0].strip()
                    track_config = track_parts[1].strip()
        
        # Default to "Grand Prix" if no config is found but track name suggests it's a full circuit
        if not track_config and track_name and any(term in track_name.lower() for term in ['circuit', 'international']):
            track_config = "Grand Prix"

        player_car_idx = driver_info.get('DriverCarIdx', -1)
        drivers = driver_info.get('Drivers', [])
        if 0 <= player_car_idx < len(drivers):
            player_driver_info = drivers[player_car_idx]
            car_name = player_driver_info.get('CarScreenName')
            car_id = player_driver_info.get('CarID')

        current_session_num = session_info_wrapper.get('CurrentSessionNum', -1)
        if 0 <= current_session_num < len(sessions_list):
            session_type = sessions_list[current_session_num].get('SessionType')

    except Exception as e:
        print(f"Error parsing data file: {e}", file=sys.stderr)

    return track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location

def _create_track_config(supabase: Client, base_track_id: int, track_name: str, config_name: str, 
                     iracing_track_id: int, iracing_config_id: int, track_location: str = None, 
                     track_length_meters: float = None) -> Optional[int]:
    """Creates a new track configuration record and returns its ID."""
    if not supabase or not base_track_id or not track_name or not config_name:
        print(f"Missing required data for track config creation")
        return None
    
    try:
        # Create display name with config
        display_name = f"{track_name} - {config_name}"
        
        # Debug
        print(f"Creating new track config: {display_name}")
        print(f"Base track ID: {base_track_id}, Length: {track_length_meters} meters")
        
        # Prepare insert data
        insert_data = {
            'name': display_name,
            'config': config_name,
            'base_track_id': base_track_id,
            'iracing_track_id': iracing_track_id,
            'iracing_config_id': iracing_config_id,
            'location': track_location,
            # Ensure we're storing the length in meters
            'length_meters': track_length_meters
        }
        
        # Remove None values before insert
        insert_data = {k: v for k, v in insert_data.items() if v is not None}
        
        # Insert the record
        config_response = supabase.table('tracks').insert(insert_data).execute()
        
        # Check for errors
        if hasattr(config_response, 'error') and config_response.error:
            print(f"Error creating track config '{display_name}': {config_response.error}")
            return None
        
        # Check if data returned
        if not config_response.data or len(config_response.data) == 0:
            print(f"Error creating track config '{display_name}': No data returned")
            return None
        
        # Get the new config ID
        config_id = config_response.data[0]['id']
        print(f"Created track config with ID: {config_id}")
        return config_id
        
    except Exception as e:
        print(f"Error creating track config: {str(e)}")
        return None

def _monitor_loop(supabase_client: Client, logged_in_user_id: str, lap_saver_instance, simple_api_instance):
    """The actual monitoring loop, designed to be run in a thread."""
    global last_session_unique_id, is_connected, last_processed_iracing_track_id, last_processed_iracing_car_id, last_processed_track_config
    global last_session_id, last_subsession_id, current_session_uuid

    # Add safety check for API instance
    if simple_api_instance is None:
        print("Monitor: SimpleIRacingAPI instance is None, cannot start monitor loop")
        return
    
    # Check if the thread should exit
    thread_should_stop = False

    # Main monitoring loop
    while not should_stop and not thread_should_stop:
        try:
            previous_connected = is_connected
            
            # Safety check: Verify that SimpleIRacingAPI instance is still valid
            api_valid = True
            try:
                # Check if the object has been deleted
                if not simple_api_instance or not hasattr(simple_api_instance, 'update_info_from_monitor'):
                    print("Monitor: API instance is no longer valid (object deleted or missing method)")
                    api_valid = False
                    thread_should_stop = True
            except RuntimeError as re:
                if "wrapped C/C++ object" in str(re):
                    print(f"Monitor: SimpleIRacingAPI C++ object has been deleted: {re}")
                    api_valid = False
                    thread_should_stop = True
                else:
                    raise
            
            # If API is no longer valid, exit the thread safely
            if not api_valid:
                print("Monitor: Stopping monitor thread due to invalid API object")
                break
            
            # Try to read the latest iRacing data file
            # If iRacing is not running, this will silently fail
            is_iracing_running = is_iracing_available()
            
            # If we transitioned from connected to disconnected
            if previous_connected and not is_iracing_running:
                # Signal as DISCONNECTED
                is_connected = False
                print("Monitor: iRacing DISCONNECTED.")
                
                # Update the API connection status (disconnected) with safety checks
                if api_valid:
                    try:
                        simple_api_instance.update_info_from_monitor({}, is_connected=False)
                    except RuntimeError as re:
                        if "wrapped C/C++ object" in str(re):
                            print(f"Monitor: SimpleIRacingAPI C++ object deleted during disconnect notification: {re}")
                            api_valid = False
                            thread_should_stop = True
                        else:
                            raise
                
                # When disconnected, save the current lap data if available
                if lap_saver_instance and hasattr(lap_saver_instance, 'end_session'):
                    try:
                        print("Monitor: Saving any remaining lap data on disconnect")
                        lap_saver_instance.end_session()
                    except Exception as e:
                        print(f"Monitor: Error ending session on disconnect: {e}")
                
                # Wait a bit longer when disconnected
                time.sleep(1)
                continue
                
            # If iRacing was just detected
            if not previous_connected and is_iracing_running:
                print("Monitor: iRacing detected, attempting initial data parse...")
                
            # If we reach here, iRacing is available
            # But we still need to parse the session info to check for valid data
            if is_iracing_running:
                # Check if the session info has been updated
                current_session_info_update_count = get_session_info_update_count()
                if current_session_info_update_count > 0:
                    print(f"Monitor: Session info update detected (Counter: {current_session_info_update_count})")
                    
                    # Parse the full data file to extract track, car, session info
                    (track_name, car_name, iracing_track_id, iracing_car_id, 
                     session_type, session_id, subsession_id, 
                     track_config, track_length, track_location) = parse_data_file()
                    
                    # Check if we got valid essential data
                    if track_name and car_name:
                        # If was previously disconnected, signal as CONNECTED now
                        if not previous_connected:
                            is_connected = True
                            print("Monitor: First successful parse. Signaling API as CONNECTED.")

                        # Create the session info dict to send to the API
                        monitor_update_info = {
                            'current_track': track_name,
                            'current_car': car_name,
                            'current_config': track_config,
                            'session_type': session_type,
                            'session_id': session_id,
                            'subsession_id': subsession_id,
                            'track_id': iracing_track_id,
                            'car_id': iracing_car_id,
                            'track_length': track_length,
                            'track_location': track_location
                        }
                        
                        # Debug output
                        print(f"Monitor: Updating SimpleAPI state: {monitor_update_info}")
                        
                        # Update the API's state with safety checks
                        if api_valid:
                            try:
                                simple_api_instance.update_info_from_monitor(monitor_update_info, is_connected=True)
                            except RuntimeError as re:
                                if "wrapped C/C++ object" in str(re):
                                    print(f"Monitor: SimpleIRacingAPI C++ object deleted during update: {re}")
                                    api_valid = False
                                    thread_should_stop = True
                                    continue  # Skip the rest of this loop iteration
                                else:
                                    raise

                        # Create new session if session ID changes OR track/config changes
                        session_changed = (session_id != last_session_id or subsession_id != last_subsession_id)
                        track_changed = (iracing_track_id != last_processed_iracing_track_id or track_config != last_processed_track_config)
                        
                        if session_changed or track_changed:
                            # First, properly end the previous session if there was one
                            if last_session_id is not None and lap_saver_instance and hasattr(lap_saver_instance, 'end_session'):
                                try:
                                    print("Monitor: Ending previous session before starting new one")
                                    lap_saver_instance.end_session()
                                except Exception as e:
                                    print(f"Monitor: Error ending previous session: {e}")
                                    
                            change_type = "session" if session_changed else "track/config" 
                            print(f"Monitor: New {change_type} detected (ID: {session_id}, SubID: {subsession_id}, Track: {track_name}, Config: {track_config})")
                            
                            # Update Supabase with new session data
                            if supabase_client and logged_in_user_id:
                                try:
                                    # Create the session record
                                    session_uuid = update_supabase_data(
                                        supabase_client, 
                                        logged_in_user_id, 
                                        track_name, 
                                        car_name, 
                                        iracing_track_id, 
                                        iracing_car_id,
                                        session_type,
                                        session_id,
                                        subsession_id,
                                        track_config,
                                        track_length,
                                        track_location
                                    )
                                    
                                    if session_uuid:
                                        print(f"Monitor: Creating new session. UUID: {session_uuid}")
                                        # Update the currently tracked session
                                        current_session_uuid = session_uuid
                                        
                                        # Reset session tracking variables
                                        last_processed_iracing_track_id = iracing_track_id
                                        last_processed_iracing_car_id = iracing_car_id
                                        last_processed_track_config = track_config
                                        last_session_id = session_id
                                        last_subsession_id = subsession_id
                                        
                                        # Notify the lap saver of the new session with safety check
                                        if lap_saver_instance:
                                            try:
                                                # Reset all lap saver variables for new session
                                                lap_saver_instance._current_session_id = session_uuid
                                                lap_saver_instance._current_track_id = last_processed_iracing_track_id
                                                lap_saver_instance._current_car_id = last_processed_iracing_car_id
                                                lap_saver_instance._current_session_type = session_type
                                                lap_saver_instance._current_lap_number = 0
                                                lap_saver_instance._is_first_telemetry = True
                                                lap_saver_instance._current_lap_data = []
                                                lap_saver_instance._best_lap_time = float('inf')
                                                lap_saver_instance._current_lap_id = None
                                                
                                                # Also ensure the session is explicitly initialized in the IRacingLapSaver
                                                if hasattr(lap_saver_instance, 'start_session'):
                                                    print(f"Monitor: Explicitly starting new session in lap saver")
                                                    lap_saver_instance.start_session(track_name, car_name, session_type)
                                            except RuntimeError as re:
                                                if "wrapped C/C++ object" in str(re):
                                                    print(f"Monitor: LapSaver C++ object deleted during session reset: {re}")
                                                else:
                                                    raise
                                    else:
                                        print("Monitor: Failed to create new session record in Supabase")
                                except Exception as e:
                                    print(f"Monitor: Error updating Supabase: {str(e)}")
                                    traceback.print_exc()
                            else:
                                print("Monitor: Using existing session.")
                        else:
                            print("Monitor: No session change detected, continuing with current session")
                    else:
                        print("Monitor: Skipping update: Failed to parse essential data.")
        except RuntimeError as re:
            if "wrapped C/C++ object" in str(re):
                print(f"Monitor: C++ object deleted during monitor loop: {re}")
                thread_should_stop = True
                break
            else:
                print(f"Monitor: Runtime error in main loop: {re}", file=sys.stderr)
                time.sleep(1)
        except Exception as e:
            print(f"Monitor: Error in main loop: {e}", file=sys.stderr)
            if is_connected:
                print("Monitor: Error caused disconnect.")
                is_connected = False
                if api_valid:
                    try:
                        simple_api_instance.update_info_from_monitor({}, is_connected=False)
                    except RuntimeError as re:
                        if "wrapped C/C++ object" in str(re):
                            print(f"Monitor: SimpleIRacingAPI C++ object deleted during error handling: {re}")
                            api_valid = False
                            thread_should_stop = True
                        else:
                            raise
                    except Exception as e2:
                        print(f"Monitor: Error during disconnect notification: {e2}")
                last_session_unique_id = -1
                # Don't reset session IDs on errors
                if lap_saver_instance:
                    try:
                        lap_saver_instance._is_first_telemetry = True
                        lap_saver_instance._current_lap_data = []
                    except RuntimeError as re:
                        if "wrapped C/C++ object" in str(re):
                            print(f"Monitor: LapSaver C++ object deleted during error handling: {re}")
                        else:
                            raise
                print("Monitor: Resetting connection state due to error.")
            time.sleep(10)

        time.sleep(3)
    
    print("Monitor: Monitor thread exiting.")

def start_monitoring(supabase_client: Client, user_id: str, lap_saver, simple_api):
    """Starts the iRacing monitoring loop in a background daemon thread."""
    global _monitor_thread, should_stop
    
    # Reset stop flag
    should_stop = False
    
    # Add simple_api parameter
    if not isinstance(supabase_client, Client):
         print("Error starting monitor: Invalid Supabase client provided.", file=sys.stderr)
         return None
    if not user_id or not isinstance(user_id, str):
         print("Error starting monitor: Invalid User ID provided.", file=sys.stderr)
         return None
    if lap_saver is None: # Check lap_saver
        print("Error starting monitor: Lap Saver instance not provided.", file=sys.stderr)
        return None
    if simple_api is None: # Check simple_api
        print("Error starting monitor: Simple API instance not provided.", file=sys.stderr)
        return None

    print("Starting iRacing background monitor thread...")
    _monitor_thread = threading.Thread(
        target=_monitor_loop,
        args=(supabase_client, user_id, lap_saver, simple_api), # Pass lap_saver and simple_api
        daemon=True # Ensures thread exits when the main app exits
    )
    _monitor_thread.start()
    print("iRacing monitor thread started.")
    return _monitor_thread # Return the thread object

# --- Initialize Smart Connection Manager (Phase 3 Optimization) ---
# Register the raw connection function with the smart manager
iracing_connection_manager.register_connection_function(_raw_iracing_connection)

# --- No longer running automatically, needs to be called from TrackPro ---
# if __name__ == "__main__":
#     print("This module is not intended to be run directly.")
#     print("Import and call start_monitoring(supabase_client, user_id) from your main application.") 