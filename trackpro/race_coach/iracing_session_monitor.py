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
import logging

# --- Configuration ---
# Use dynamic path based on current Python environment
IRSDK_EXE_PATH = os.path.join(sys.exec_prefix, 'Scripts', 'irsdk.exe')
DATA_TXT_PATH = "data.txt" # Output file in the script's running directory

# --- iRacing SDK Initialization (kept global for simplicity in the module) ---
# Ensure only one instance if multiple parts of TrackPro might use it
# ir = irsdk.IRSDK() # REMOVE THIS GLOBAL - will use the one from SimpleIRacingAPI instance

# --- State Variables (module level) ---
# These track the state across monitoring cycles within the thread
last_session_unique_id = -1
is_connected = False
last_processed_iracing_track_id = None
last_processed_iracing_car_id = None
last_processed_track_config = None
last_session_id = -1 # Changed from None to -1 for distinct initial comparison with iRacing session_id 0
last_subsession_id = None
current_session_uuid = None

# Event to signal the monitoring thread to stop (optional but good practice)
should_stop = False

# Add new globals to track the DB IDs used for the last TrackPro session context
global last_tp_db_car_id, last_tp_db_track_id
last_tp_db_car_id = None
last_tp_db_track_id = None

# Add new globals for detecting offline session resets
global last_lap_completed_iracing, last_session_time_secs_iracing
last_lap_completed_iracing = -1 
last_session_time_secs_iracing = 0.0

def is_iracing_available(ir_to_check: irsdk.IRSDK):
    """Check if iRacing is available and can be connected to"""
    try:
        # Use the passed-in irsdk instance
        # The SimpleIRacingAPI is responsible for startup() and shutdown().
        # This function now primarily checks the current state of the passed instance.
        if ir_to_check and ir_to_check.is_initialized and ir_to_check.is_connected:
            return True
            
        # If not connected, we don't attempt to startup() here, as SimpleIRacingAPI handles that.
        # We just report the current state of the passed ir_to_check instance.
        # print(f"iRacing connection status (via monitor check) - initialized: {ir_to_check.is_initialized if ir_to_check else 'N/A'}, connected: {ir_to_check.is_connected if ir_to_check else 'N/A'}")
        return False # If any check fails or ir_to_check is None

    except Exception as e:
        print(f"Error checking iRacing availability: {str(e)}")
        print(traceback.format_exc())
        return False

def get_session_info_update_count():
    """Get the current session info update count from iRacing"""
    # This function might need to be adapted if 'ir' is no longer global
    # For now, assume it will be called in a context where 'ir' is the correct instance
    # or that SimpleIRacingAPI provides an equivalent method.
    # If this is called by _monitor_loop, it will need access to the correct ir instance.
    # Let's assume for now that the SimpleIRacingAPI instance passed to _monitor_loop
    # will provide access to its irsdk object if this function needs it.
    # For now, this function might not work correctly if it relies on a global ir.
    # We will modify its usage later if direct ir access is needed here.
    # UPDATE: We will call ir.startup() on the SimpleIRacingAPI's ir instance directly in the monitor loop if needed.
    
    # This function is problematic if 'ir' is not the live one. We should get this info via simple_api_instance.ir
    # For now, the main logic in _monitor_loop bypasses needing this if ir.is_connected is checked on the right instance.
    # The direct call to run_irsdk_parse() and then ir.session_info_update also assumes 'ir' is the live one.
    # This will be implicitly fixed if _monitor_loop uses simple_api_instance.ir for these calls.
    print("WARNING: get_session_info_update_count() may not use the correct irsdk instance if global 'ir' was removed.")
    return 0 # Temporarily disable its effect if it causes issues, focus on monitor loop fix.

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
                car_response = supabase.table('cars').select('id, iracing_car_id').eq('name', car_name).execute()
                if car_response.data and len(car_response.data) > 0:
                    car_db_id = car_response.data[0]['id']
                    existing_iracing_car_id = car_response.data[0].get('iracing_car_id')
                    print(f"Found existing car by name: {car_name}, id={car_db_id}, current_iracing_car_id={existing_iracing_car_id}")
                    
                    # If found by name, and iracing_car_id from sim (car_id) is available AND it's not already set or different
                    if car_id is not None and (existing_iracing_car_id is None or existing_iracing_car_id != car_id):
                        try:
                            update_response = supabase.table('cars').update({'iracing_car_id': car_id}).eq('id', car_db_id).execute()
                            if update_response.data and len(update_response.data) > 0:
                                print(f"Updated car {car_name} (id={car_db_id}) with iracing_car_id={car_id}")
                            else:
                                # Handle cases where the update might not return data as expected by some supabase-py versions
                                # or if RLS prevents update/select.
                                print(f"Attempted to update car {car_name} (id={car_db_id}) with iracing_car_id={car_id}. Response: {getattr(update_response, 'data', 'No data')}")

                        except Exception as update_e:
                            print(f"Error updating car {car_name} with iracing_car_id: {str(update_e)}")
                            
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
            # Create a directory to store session data - properly handle Windows paths
            documents_path = os.path.expanduser("~\\Documents")
            trackpro_path = os.path.join(documents_path, "TrackPro")
            sessions_path = os.path.join(trackpro_path, "Sessions")
            
            # Make each directory if it doesn't exist
            os.makedirs(sessions_path, exist_ok=True)
            print(f"Ensuring directory exists: {sessions_path}")
            
            # Create or update a file with active sessions
            session_file = os.path.join(sessions_path, "active_sessions.json")
            
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
    # This function relies on a global 'ir'. It needs to be passed the correct irsdk instance
    # or called as a method of SimpleIRacingAPI if it uses self.ir.
    # For now, we assume the primary parsing action for the monitor will happen via simple_api_instance.ir
    # This function might be unused or needs refactoring.
    print("WARNING: run_irsdk_parse() may not use the correct irsdk instance if global 'ir' was removed.")
    return False # Temporarily disable to avoid issues with wrong instance.

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
    player_lap_times = [] # New variable to store player's lap times
    
    try:
        with open(DATA_TXT_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract YAML section
        yaml_end_marker = '...'
        yaml_section = content
        if yaml_end_marker in content:
            yaml_section = content.split(yaml_end_marker, 1)[0]
        else:
            # This heuristic might not be perfect, consider removing if it causes issues.
            # It assumes that a line not starting with a space, containing ': ', 
            # and not being the first line, marks the end of the YAML.
            # This was an attempt to handle malformed or incomplete YAML sections.
            # A safer approach might be to just try to load the whole thing if '...' isn't found.
            pass # ADDED pass TO MAKE THE ELSE BLOCK SYNTACTICALLY VALID

        if not yaml_section.strip():
            logger.warning("Extracted YAML section is empty.")
            # Ensure all values, including player_lap_times, are returned.
            return track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location, player_lap_times

        data = yaml.safe_load(yaml_section)
        if not data:
            logger.warning("Parsed YAML data is empty or invalid.")
            return track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location, player_lap_times

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
        track_length_str = weekend_info.get('TrackLength') # Keep as string initially
        track_location = weekend_info.get('TrackCity')
        
        if not track_location and weekend_info.get('TrackCountry'):
            track_location = weekend_info.get('TrackCountry')
            
        # Convert track length to meters if needed (iRacing uses kilometers)
        if track_length_str:
            try:
                if isinstance(track_length_str, str):
                    track_length_val = float(track_length_str.replace('km', '').strip()) * 1000
                    track_length = track_length_val # Store as float (meters)
                elif isinstance(track_length_str, (float, int)):
                    track_length = float(track_length_str) * 1000 # Assume km if numeric
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert track length '{track_length_str}' to float: {e}")
                track_length = None # Set to None on error
        
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

        current_session_num = data.get('SessionInfo', {}).get('CurrentSessionNum', -1) # Corrected path

        if 0 <= current_session_num < len(sessions_list):
            current_session_data = sessions_list[current_session_num]
            session_type = current_session_data.get('SessionType')
            
            results_positions = current_session_data.get('ResultsPositions')
            if results_positions:
                for result_entry in results_positions:
                    if result_entry.get('CarIdx') == player_car_idx:
                        laps_completed = result_entry.get('LapsComplete', 0)
                        # 'Laps' key might not exist, or be None, or empty list
                        # It should contain a list of lap time dicts, e.g., [{'LapTime': 90.123}, ...]
                        # Or, sometimes it's just a list of times. Check structure from iRacing.
                        # The actual key for lap times list might be 'LapTimes' or just 'Laps' if it stores objects.
                        # The iRacing documentation or example YAML would clarify the exact structure.
                        # Assuming 'Laps' contains a list of dicts with 'LapTime'.
                        
                        # Based on common iRacing YAML structure, individual lap times are often
                        # not directly in ResultsPositions but in a separate field per driver,
                        # or ResultsPositions contains only BestLapTime etc.
                        # For now, let's assume we are looking for a list of all lap times.
                        # The most common place for *all* player laps is often in DriverInfo.Drivers[player_car_idx].LapsAll
                        # or a similar structure. Let's check that.

                        # Attempt 1: Check SessionInfo.Sessions[X].ResultsPositions[Y].Laps (less common for ALL laps)
                        # This usually contains summary like best lap, not all laps.

                        # Attempt 2: Check DriverInfo.Drivers[CarIdx] for a list of all laps
                        # iRacing often stores all completed laps for a driver under their entry in DriverInfo.Drivers
                        # The exact key can vary slightly based on session type or iRacing updates.
                        # Common keys are 'Laps', 'LapTimes', 'LapsAll'. Let's assume 'LapsAll' for now.
                        
                        # The structure found from an example iRacing session string:
                        # DriverInfo:
                        #   Drivers:
                        #     - CarIdx: 0
                        #       ...
                        #       Laps: # This seems to be a list of dicts, one per lap, but maybe only for some session types
                        #         - LapNumber: 1
                        #           Time: 90.1234 # Example
                        #           ... (other lap details)
                        #     - CarIdx: 1
                        #       ...
                        # SessionInfo:
                        #   Sessions:
                        #     - SessionNum: 0
                        #       ...
                        #       ResultsPositions:
                        #         - CarIdx: 0
                        #           LapsComplete: 10
                        #           FastestLap: 1 # Lap number of fastest
                        #           FastestTime: 89.0
                        #           LastTime: 90.5 # Time of the last completed lap
                        #           Laps: # List of *all* lap times (floats) for this driver in this session
                        #             - 91.2
                        #             - 90.5
                        #             - 89.0 
                        #             ...

                        # Let's use the structure SessionInfo.Sessions[X].ResultsPositions[Y].Laps
                        # which seems to be a list of float times.
                        raw_lap_times_list = result_entry.get('Laps') # This should be a list of floats
                        if isinstance(raw_lap_times_list, list):
                            for time_entry in raw_lap_times_list:
                                if isinstance(time_entry, (float, int)) and time_entry > 0:
                                    player_lap_times.append(float(time_entry))
                                # Sometimes it might be a dict {'LapTime': X} if the structure varies
                                elif isinstance(time_entry, dict) and 'LapTime' in time_entry:
                                    lap_t = time_entry['LapTime']
                                    if isinstance(lap_t, (float, int)) and lap_t > 0:
                                        player_lap_times.append(float(lap_t))
                        break # Found player, no need to check other results_positions entries
    
    except FileNotFoundError:
        logger.error(f"Data file not found: {DATA_TXT_PATH}")
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML from data file: {e}")
    except Exception as e:
        logger.error(f"Error parsing data file: {e}", exc_info=True)

    # Ensure all values, including player_lap_times, are returned in all paths
    return track_name, car_name, track_id, car_id, session_type, session_id, subsession_id, track_config, track_length, track_location, player_lap_times

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
    logger.info("[MonitorLoop ENTRY] Entered _monitor_loop function.")
    # Use the irsdk instance from SimpleIRacingAPI
    ir_sdk = simple_api_instance.ir

    global last_session_unique_id, is_connected, last_processed_iracing_track_id, last_processed_iracing_car_id, last_processed_track_config
    global last_session_id, last_subsession_id, current_session_uuid
    # Add new globals to track the DB IDs used for the last TrackPro session context
    global last_tp_db_car_id, last_tp_db_track_id
    # last_tp_db_car_id = None # Already global
    # last_tp_db_track_id = None # Already global
    
    # Access globals for offline session reset detection
    global last_lap_completed_iracing, last_session_time_secs_iracing

    # Add safety check for API instance
    if simple_api_instance is None:
        print("Monitor: SimpleIRacingAPI instance is None, cannot start monitor loop")
        return
    
    # Check if the thread should exit
    thread_should_stop = False
    logger.info(f"[MonitorLoop PRE-LOOP CHECK] initial should_stop: {should_stop}, initial thread_should_stop: {thread_should_stop}")

    # Main monitoring loop
    while not should_stop and not thread_should_stop:
        loop_start_time = time.monotonic()
        logger.info("[MonitorLoop] Starting new iteration.")
        try:
            previous_connected = is_connected
            logger.info(f"[MonitorLoop] Previous connection state: {previous_connected}")
            
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
            
            # --- MODIFIED CONNECTION HANDLING ---
            # 1. Ask SimpleIRacingAPI to check/attempt its connection
            if hasattr(simple_api_instance, 'connect'):
                logger.debug("[MonitorLoop] Calling simple_api_instance.connect() to ensure/check irsdk connection.")
                simple_api_instance.connect() # This will attempt startup if needed and update its internal state
            
            # 2. Check the API's reported connection status
            is_iracing_running = False # Default to False
            if hasattr(simple_api_instance, 'is_api_connected_to_iracing'):
                is_iracing_running = simple_api_instance.is_api_connected_to_iracing()
                logger.info(f"[MonitorLoop] simple_api_instance.is_api_connected_to_iracing() returned: {is_iracing_running}")
            else:
                logger.warning("[MonitorLoop] simple_api_instance does not have is_api_connected_to_iracing method. Falling back to direct ir_sdk check.")
                # Fallback (less ideal, but for safety if method is missing)
                if ir_sdk:
                    is_iracing_running = ir_sdk.is_connected and ir_sdk.is_initialized
            # --- END MODIFIED CONNECTION HANDLING ---
            
            # If we transitioned from connected to disconnected
            if previous_connected and not is_iracing_running:
                # Signal as DISCONNECTED
                is_connected = False
                print("Monitor: iRacing DISCONNECTED.")
                
                # Reset global session tracking to force new session on next connection
                current_session_uuid = None
                last_processed_iracing_track_id = None
                last_processed_iracing_car_id = None
                last_processed_track_config = None
                last_session_id = -1
                last_subsession_id = None
                
                # Also reset database tracking IDs
                last_tp_db_car_id = None
                last_tp_db_track_id = None
                
                # Reset lap tracking variables
                last_lap_completed_iracing = -1
                last_session_time_secs_iracing = 0.0
                
                # Update the API connection status (disconnected) with safety checks
                if api_valid:
                    try:
                        simple_api_instance.update_info_from_monitor({}, is_connected=False)
                    except RuntimeError as re:
                        if "wrapped C/C++ object" in str(re):
                            print(f"Monitor: SimpleIRacingAPI C++ object deleted during disconnect notification: {re}")
                            api_valid = False
                            thread_should_stop = True
                
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
                logger.info("[MonitorLoop] iRacing newly detected.")
                
            # If we reach here, iRacing is available
            # But we still need to parse the session info to check for valid data
            if is_iracing_running:
                logger.info("[MonitorLoop] iRacing is running. Checking session info update.")
                # Check if the session info has been updated
                # current_session_info_update_count = get_session_info_update_count() # This needs the correct ir
                # Let's try to get it directly from the live ir_sdk instance if available
                current_session_info_update_count = 0
                if ir_sdk and ir_sdk.is_connected:
                    # First, ensure data is parsed if needed by the irsdk instance
                    # This parse is for the session string, separate from telemetry ticks
                    # run_irsdk_parse() should ideally be a method of simple_api_instance or use simple_api_instance.ir
                    # For now, we assume parse_data_file() works on a common file updated by simple_api_instance elsewhere or by irsdk itself
                    # The most crucial part is that ir_sdk.session_info_update is fresh.
                    # We might need to call a parse method on ir_sdk if simple_api_instance doesn't do this for session string automatically.
                    
                    # Let's assume simple_api_instance keeps its ir_sdk updated with session string info
                    # or that run_irsdk_parse() if called by get_session_info_update_count would use the correct instance.
                    # The logic below relies on parse_data_file() which reads from DATA_TXT_PATH.
                    # SimpleIRacingAPI.process_telemetry calls self.ir.freeze_var_buffer_latest() and then self.ir.parse_to(DATA_TXT_PATH)
                    # So, if the simple_api_instance.process_telemetry() is running, DATA_TXT_PATH should be fresh.
                    # The main concern for the monitor is detecting changes in that DATA_TXT_PATH.
                    # A simple check is if the session_info_update counter on the LIVE ir_sdk has changed.
                    try:
                        # Attempt to refresh the global ir (now simple_api_instance.ir) session data
                        # This ensures that the YAML data is based on the latest info before parsing
                        logger.info(f"[MonitorLoop] Before direct ir_sdk access: ir_sdk.is_initialized={ir_sdk.is_initialized}, ir_sdk.is_connected={ir_sdk.is_connected}")
                        # REMOVE direct startup attempts from monitor - SimpleIRacingAPI.connect() handles this now.
                        # if not ir_sdk.is_connected: 
                        #     logger.info("[MonitorLoop] ir_sdk is not connected OR not initialized. Attempting ir_sdk.startup().")
                        #     try:
                        #         ir_sdk.startup() 
                        #         logger.info(f"[MonitorLoop] After ir_sdk.startup(): initialized={ir_sdk.is_initialized}, connected={ir_sdk.is_connected}")
                        #     except Exception as su_exc:
                        #         logger.error(f"[MonitorLoop] Exception during ir_sdk.startup(): {su_exc}", exc_info=True)
                        
                        if ir_sdk.is_connected: # Check the actual ir_sdk instance used by the API
                            logger.info("[MonitorLoop] ir_sdk is connected. Ready to parse.")
                            # This parse_to should update the ir_sdk object internal session_info
                            # if the irsdk library behaves such that parse_to also makes session_info_update fresh.
                            # Alternatively, direct parsing of the YAML file remains the primary source for session_info dict.
                            if hasattr(ir_sdk, 'parse_to'):
                                logger.info("[MonitorLoop] Calling ir_sdk.parse_to(DATA_TXT_PATH).")
                                ir_sdk.parse_to(DATA_TXT_PATH) 
                            current_session_info_update_count = ir_sdk.session_info_update
                            logger.info(f"[MonitorLoop] ir_sdk.session_info_update: {current_session_info_update_count}")
                        else:
                            logger.info("[MonitorLoop] ir_sdk is NOT connected.")
                    except Exception as e_parse_monitor:
                        print(f"Monitor: Error explicitly parsing data for update count: {e_parse_monitor}")
                        logger.error(f"[MonitorLoop] Error in ir_sdk startup/parse_to for update count: {e_parse_monitor}")

                if current_session_info_update_count > 0: # If there was an update or we assume one
                    print(f"Monitor: Session info update detected (Counter: {current_session_info_update_count})")
                    logger.info(f"[MonitorLoop] Session info update counter ({current_session_info_update_count}) > 0. Parsing data file.")
                    
                    # Parse the full data file to extract track, car, session info
                    (track_name, car_name, iracing_track_id, iracing_car_id, 
                     session_type, session_id, subsession_id, 
                     track_config, track_length, track_location, 
                     player_laps_from_yaml) = parse_data_file()
                    
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
                            'track_location': track_location,
                            'player_laps_yaml': player_laps_from_yaml
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

                        # --- MODIFIED SESSION HANDLING LOGIC ---
                        # Step 1: Resolve Car and Track DB IDs.
                        # This requires parts of the logic from the original `update_supabase_data`.
                        # For this edit, we'll represent this with placeholder calls to hypothetical functions.
                        # In a full implementation, you would integrate or call the actual DB interaction logic here.
                        
                        db_car_id_resolved = None
                        db_track_id_resolved = None

                        if supabase_client:
                            try:
                                # --- Car Resolution (Conceptual) ---
                                # This would involve querying 'cars' table by iracing_car_id or name, and creating if not exists.
                                # Simplified: assume a helper function `get_or_create_car_db_id`
                                temp_car_response = supabase_client.table('cars').select('id').eq('iracing_car_id', iracing_car_id).execute()
                                if temp_car_response.data:
                                    db_car_id_resolved = temp_car_response.data[0]['id']
                                else:
                                    temp_car_response_name = supabase_client.table('cars').select('id').eq('name', car_name).execute()
                                    if temp_car_response_name.data:
                                        db_car_id_resolved = temp_car_response_name.data[0]['id']
                                        # Optionally update iracing_car_id if missing
                                    else:
                                        # Create car if truly new
                                        new_car_resp = supabase_client.table('cars').insert({'name': car_name, 'iracing_car_id': iracing_car_id}).execute()
                                        if new_car_resp.data:
                                            db_car_id_resolved = new_car_resp.data[0]['id']
                                print(f"Monitor: Resolved DB Car ID: {db_car_id_resolved} for iRacing Car: {car_name} ({iracing_car_id})")

                                # --- Track Resolution (Conceptual) ---
                                # This involves finding/creating base_track, then finding/creating track_config.
                                # Simplified: assume helper `get_or_create_track_config_db_id`
                                base_track_db_id = _find_or_create_base_track(supabase_client, track_name, iracing_track_id, track_location, track_length)
                                if base_track_db_id:
                                    if track_config: # If there's a specific configuration
                                        config_response = supabase_client.table('tracks').select('id').eq('base_track_id', base_track_db_id).eq('config', track_config).execute()
                                        if config_response.data:
                                            db_track_id_resolved = config_response.data[0]['id']
                                        else:
                                            # Create track config
                                            # Note: _create_track_config needs iracing_config_id which is not parsed by default in parse_data_file
                                            # We might need to adjust parse_data_file or _create_track_config if iracing_config_id is vital
                                            # For now, we proceed assuming track_config name is the primary key for configs under a base_track_id
                                            new_conf_resp = supabase_client.table('tracks').insert({
                                                'name': f"{track_name} - {track_config}", 
                                                'config': track_config, 
                                                'base_track_id': base_track_db_id,
                                                'iracing_track_id': iracing_track_id, # Store parent iRacing track ID
                                                'location': track_location,
                                                'length_meters': track_length
                                            }).execute()
                                            if new_conf_resp.data:
                                                db_track_id_resolved = new_conf_resp.data[0]['id']
                                    else: # No specific config, use the base track ID
                                        db_track_id_resolved = base_track_db_id
                                print(f"Monitor: Resolved DB Track ID: {db_track_id_resolved} for iRacing Track: {track_name} - {track_config} ({iracing_track_id})")

                            except Exception as e_resolve:
                                print(f"Monitor: Error resolving DB car/track IDs: {e_resolve}")
                                traceback.print_exc()
                        
                        # --- Enhanced condition for starting a new TrackPro session ---
                        session_id_changed = (session_id is not None and session_id != last_session_id) # Ensure session_id is not None
                        car_changed = (db_car_id_resolved is not None and db_car_id_resolved != last_tp_db_car_id)
                        track_changed = (db_track_id_resolved is not None and db_track_id_resolved != last_tp_db_track_id)
                        
                        offline_session_reset_detected = False
                        # Try to get live telemetry for more robust reset detection
                        live_lap_completed = -1
                        live_session_time = 0.0
                        if ir_sdk.is_connected: # Check if ir_sdk object is connected
                            try:
                                if ir_sdk.is_initialized and ir_sdk.is_connected: # Double check
                                    logger.info("[MonitorLoop] ir_sdk is initialized and connected for live telemetry check.")
                                    # Ensure the irsdk buffer is updated with the latest data
                                    if hasattr(ir_sdk, 'freeze_var_buffer_latest'):
                                        logger.info("[MonitorLoop] Calling ir_sdk.freeze_var_buffer_latest() for live telemetry.")
                                        ir_sdk.freeze_var_buffer_latest()
                                    
                                    # Directly access the latest values from the ir_sdk object
                                    live_lap_completed = ir_sdk['LapCompleted'] if 'LapCompleted' in ir_sdk else -1
                                    live_session_time = ir_sdk['SessionTime'] if 'SessionTime' in ir_sdk else 0.0
                                    logger.info(f"[MonitorLoop] Live Telemetry: LapCompleted={live_lap_completed}, SessionTime={live_session_time:.2f}")
                                else:
                                     print("Monitor: ir_sdk object not fully connected/initialized for live telemetry check.")
                                     logger.warning("[MonitorLoop] ir_sdk not fully connected/initialized for live telemetry check.")
                            except Exception as tel_err:
                                print(f"Monitor: Error getting live telemetry for session reset check: {tel_err}")
                                logger.error(f"[MonitorLoop] Error getting live telemetry for reset check: {tel_err}")
                        else:
                            logger.info("[MonitorLoop] ir_sdk NOT connected for live telemetry check.")

                        if session_id == 0: # Specifically for "Offline Testing" or similar where iRacing SessionID is 0
                            # Use a lower threshold for session time drop to detect resets more aggressively
                            SESSION_TIME_RESET_THRESHOLD = 5.0 # Reduced from 15.0 to 5.0 seconds
                            if (live_lap_completed < last_lap_completed_iracing and last_lap_completed_iracing > 0) or \
                                (live_session_time < (last_session_time_secs_iracing - SESSION_TIME_RESET_THRESHOLD)) or \
                                (live_session_time < 10.0 and last_session_time_secs_iracing > 60.0): # More aggressive detection of session restart
                                print(f"Monitor: Offline session reset detected. Lap: {last_lap_completed_iracing}->{live_lap_completed}, Time: {last_session_time_secs_iracing:.2f}->{live_session_time:.2f}")
                                offline_session_reset_detected = True
                        
                        needs_new_tp_session_context = (
                            (session_id != 0 and session_id_changed) or # Normal session ID change
                            car_changed or
                            track_changed or
                            offline_session_reset_detected # Our new condition
                        )
                        logger.info(f"[MonitorLoop] Determining new TP session context: session_id_changed={session_id_changed}, car_changed={car_changed}, track_changed={track_changed}, offline_reset={offline_session_reset_detected} => needs_new_tp_session_context={needs_new_tp_session_context}")

                        session_uuid_for_lap_saver = current_session_uuid # Default to existing if no change

                        if needs_new_tp_session_context:
                            print(f"Monitor: Change detected. iRacing SID: {session_id} (was {last_session_id}), "
                                  f"DB CarID: {db_car_id_resolved} (was {last_tp_db_car_id}), "
                                  f"DB TrackID: {db_track_id_resolved} (was {last_tp_db_track_id})")

                            # End previous lap saver session context if one was active and had a session ID
                            if lap_saver_instance and lap_saver_instance._current_session_id:
                                try:
                                    print(f"Monitor: Ending previous lap saver session ({lap_saver_instance._current_session_id})")
                                    if hasattr(lap_saver_instance, 'end_session'):
                                        lap_saver_instance.end_session()
                                    else:
                                        # Fallback if end_session method doesn't exist
                                        print("Monitor: Using fallback approach for ending session - lap indexer finalize")
                                        # Finalize the lap indexer if it exists
                                        if hasattr(lap_saver_instance, 'lap_indexer') and hasattr(lap_saver_instance.lap_indexer, 'finalize'):
                                            lap_saver_instance.lap_indexer.finalize()
                                except Exception as e:
                                    print(f"Monitor: Error ending previous lap saver session: {e}")
                            
                            print("Monitor: Context changed, forcing creation of a new TrackPro session.")
                            session_uuid_for_lap_saver = None # Ensure we try to create a new one
                            current_session_uuid = None # Reset global until new one is confirmed

                            if supabase_client and logged_in_user_id and db_track_id_resolved and db_car_id_resolved:
                                # Create a new session record in the database
                                print(f"Monitor: Calling create_supabase_session for User={logged_in_user_id}, Track={db_track_id_resolved}, Car={db_car_id_resolved}")
                                new_db_session_uuid = create_supabase_session(
                                        supabase_client, 
                                        logged_in_user_id, 
                                        db_track_id_resolved,
                                        db_car_id_resolved,
                                        session_type 
                                )
                                if new_db_session_uuid:
                                    session_uuid_for_lap_saver = new_db_session_uuid
                                    current_session_uuid = new_db_session_uuid 
                                    print(f"Monitor: New TrackPro session created and assigned: {current_session_uuid}")
                                    logger.info(f"[MonitorLoop] New TrackPro session DB UUID: {current_session_uuid}")
                                    
                                    # Emit the signal to notify UI that a new session was created
                                    try:
                                        if simple_api_instance and hasattr(simple_api_instance, 'new_trackpro_session_created'):
                                            # Get track and car names for the signal
                                            track_name_for_signal = track_name or "Unknown Track"
                                            car_name_for_signal = car_name or "Unknown Car"
                                            simple_api_instance.new_trackpro_session_created.emit(current_session_uuid, track_name_for_signal, car_name_for_signal)
                                            print(f"Monitor: Emitted new_trackpro_session_created signal with session {current_session_uuid}")
                                        else:
                                            print("Monitor: Could not emit new_trackpro_session_created signal (API instance missing or lacks signal)")
                                    except Exception as signal_err:
                                        print(f"Monitor: Error emitting new session signal: {signal_err}")
                                else:
                                    print("Monitor: Failed to create a new TrackPro session.")
                                    # session_uuid_for_lap_saver remains None, current_session_uuid remains None
                            
                            # Update last processed DB IDs only when a new context is established
                            last_tp_db_car_id = db_car_id_resolved
                            last_tp_db_track_id = db_track_id_resolved
                        
                        # Update the lap saver\'s context if we have a valid session UUID for it
                        # This runs if needs_new_tp_session_context was true (and a new session was made or failed)
                        # OR if needs_new_tp_session_context was false (continuing with current_session_uuid)
                        if lap_saver_instance and session_uuid_for_lap_saver: # session_uuid_for_lap_saver could be new or the ongoing current_session_uuid
                            if lap_saver_instance._current_session_id != session_uuid_for_lap_saver or \
                               lap_saver_instance._current_car_id != db_car_id_resolved or \
                               lap_saver_instance._current_track_id != db_track_id_resolved or \
                               lap_saver_instance._current_session_type != session_type: # Add check for session_type
                                print(f"Monitor: Starting/Updating lap saver context. Session: {session_uuid_for_lap_saver}, Car: {db_car_id_resolved}, Track: {db_track_id_resolved}, Type: {session_type}")
                                logger.info(f"[MonitorLoop] Calling lap_saver_instance.start_new_session_context with SessionUUID: {session_uuid_for_lap_saver}")
                                # Check if method exists, otherwise set attributes directly
                                if hasattr(lap_saver_instance, 'start_new_session_context'):
                                    lap_saver_instance.start_new_session_context(session_uuid_for_lap_saver, db_car_id_resolved, db_track_id_resolved, session_type)
                                else:
                                    # Fallback: set attributes directly
                                    print(f"Monitor: Using fallback approach - direct attribute setting")
                                    lap_saver_instance._current_session_id = session_uuid_for_lap_saver
                                    lap_saver_instance._current_car_id = db_car_id_resolved
                                    lap_saver_instance._current_track_id = db_track_id_resolved
                                    lap_saver_instance._current_session_type = session_type
                                    # Reset internal state
                                    lap_saver_instance._is_first_telemetry = True
                                    logger.info(f"[MonitorLoop] Fallback: Directly set lap_saver context. SessionUUID: {session_uuid_for_lap_saver}")
                                    # Reset lap indexer if it exists and has reset method
                                    if hasattr(lap_saver_instance, 'lap_indexer') and hasattr(lap_saver_instance.lap_indexer, 'reset_internal_lap_state'):
                                        lap_saver_instance.lap_indexer.reset_internal_lap_state()
                            # Ensure car/track IDs are fresh in lap_saver even if session UUID didn't change
                            # (e.g. monitor restart but iRacing session is the same, TP session ID was persisted in current_session_uuid)
                            elif lap_saver_instance._current_session_id == session_uuid_for_lap_saver:
                                logger.info("[MonitorLoop] Lap saver session UUID matches, updating car/track/type if different.")
                                lap_saver_instance._current_car_id = db_car_id_resolved 
                                lap_saver_instance._current_track_id = db_track_id_resolved
                                lap_saver_instance._current_session_type = session_type
                        elif lap_saver_instance and not session_uuid_for_lap_saver:
                             # This case means a new session was needed but creation failed, or no session is active.
                             # Ensure lap saver is not using an old context if current_session_uuid is now None.
                            if lap_saver_instance._current_session_id is not None:
                                print("Monitor: No active TrackPro session UUID for lap saver. Clearing its context.")
                                logger.info("[MonitorLoop] No active TP session UUID, calling lap_saver.end_session() to clear context.")
                                if hasattr(lap_saver_instance, 'end_session'):
                                    lap_saver_instance.end_session() # Or a more direct way to clear its session_id
                                else:
                                    # Fallback if end_session doesn't exist
                                    print("Monitor: Using fallback approach for clearing context")
                                    logger.info("[MonitorLoop] Fallback: Directly clearing lap_saver context.")
                                    lap_saver_instance._current_session_id = None
                                    lap_saver_instance._is_first_telemetry = True
                                    if hasattr(lap_saver_instance, 'lap_indexer') and hasattr(lap_saver_instance.lap_indexer, 'finalize'):
                                        lap_saver_instance.lap_indexer.finalize()

                        # Update last processed iRacing session ID for the next iteration's comparison
                        last_session_id = session_id
                        logger.info(f"[MonitorLoop] Updated last_session_id to: {last_session_id}")
                        
                        # Update tracking variables for offline reset detection
                        if is_connected: # Only if we are sure data is current
                            last_lap_completed_iracing = live_lap_completed
                            last_session_time_secs_iracing = live_session_time
                            logger.info(f"[MonitorLoop] Updated offline reset trackers: Lap={last_lap_completed_iracing}, Time={last_session_time_secs_iracing:.2f}")
                        
                        # The other last_... for car/track are updated inside `if needs_new_tp_session_context`
                        # because they define the TP session context. `last_session_id` is for iRacing's session.

                    else: # Essential data (track_name, car_name) not available
                        print("Monitor: Skipping update: Failed to parse essential data (track_name or car_name missing).")
                        logger.warning("[MonitorLoop] Essential data (track_name/car_name) missing from parsed file. Skipping update cycle.")
                else: # current_session_info_update_count was 0 or less
                    logger.info("[MonitorLoop] No session info update detected (counter <= 0). No file parse attempt.")
            else: # iRacing not running
                logger.info("[MonitorLoop] iRacing not running. Skipping main processing.")

        except RuntimeError as re:
            if "wrapped C/C++ object" in str(re):
                print(f"Monitor: C++ object deleted during monitor loop: {re}")
                logger.critical(f"[MonitorLoop] C++ object (likely API or LapSaver) deleted: {re}")
                thread_should_stop = True
                break
            else:
                print(f"Monitor: Runtime error in main loop: {re}", file=sys.stderr)
                logger.error(f"[MonitorLoop] Runtime error: {re}", exc_info=True)
                time.sleep(1)
        except Exception as e:
            print(f"Monitor: Error in main loop: {e}", file=sys.stderr)
            logger.error(f"[MonitorLoop] Exception: {e}", exc_info=True)
            if is_connected:
                print("Monitor: Error caused disconnect.")
                logger.warning("[MonitorLoop] Error caused disconnect state update.")
                is_connected = False
                if api_valid:
                    try:
                        simple_api_instance.update_info_from_monitor({}, is_connected=False)
                    except RuntimeError as re:
                        if "wrapped C/C++ object" in str(re):
                            print(f"Monitor: SimpleIRacingAPI C++ object deleted during error handling: {re}")
                            logger.critical(f"[MonitorLoop] API C++ object deleted during error disconnect: {re}")
                            api_valid = False
                            thread_should_stop = True
                        else:
                            raise
                    except Exception as e2:
                        print(f"Monitor: Error during disconnect notification: {e2}")
                        logger.error(f"[MonitorLoop] Error during API disconnect notification: {e2}")
                last_session_unique_id = -1
                # current_session_uuid = None # Do not nullify current_session_uuid on general errors, only if session ends or changes
                # last_tp_db_car_id = None  # Also do not reset these on general errors
                # last_tp_db_track_id = None

                if lap_saver_instance:
                    try:
                        # Safely set attributes that we know should exist
                        if hasattr(lap_saver_instance, '_is_first_telemetry'):
                            lap_saver_instance._is_first_telemetry = True
                        if hasattr(lap_saver_instance, '_current_lap_data'):
                            lap_saver_instance._current_lap_data = []
                    except RuntimeError as re:
                        if "wrapped C/C++ object" in str(re):
                            print(f"Monitor: LapSaver C++ object deleted during error handling: {re}")
                            logger.critical(f"[MonitorLoop] LapSaver C++ object deleted during error handling: {re}")
                        else:
                            raise
                print("Monitor: Resetting connection state due to error.")
                logger.info("[MonitorLoop] Resetting connection state due to caught error.")
            time.sleep(10)

        # Measure time taken and adjust sleep to maintain ~3s cycle with minimum 0.5s
        iteration_time = time.monotonic() - loop_start_time
        sleep_time = max(0.5, 3.0 - iteration_time)  
        logger.debug(f"[MonitorLoop] Iteration took {iteration_time:.3f}s. Sleeping for {sleep_time:.2f}s")
        time.sleep(sleep_time)
    
    print("Monitor: Monitor thread exiting.")
    logger.info("[MonitorLoop] Thread exiting.")

def start_monitoring(supabase_client: Client, user_id: str, lap_saver, simple_api):
    """Starts the iRacing monitoring loop in a background daemon thread."""
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
    monitor_thread = threading.Thread(
        target=_monitor_loop,
        args=(supabase_client, user_id, lap_saver, simple_api), # Pass lap_saver and simple_api
        daemon=True # Ensures thread exits when the main app exits
    )
    monitor_thread.start()
    print("iRacing monitor thread started.")
    return monitor_thread # Optionally return the thread object

# --- No longer running automatically, needs to be called from TrackPro ---
# if __name__ == "__main__":
#     print("This module is not intended to be run directly.")
#     print("Import and call start_monitoring(supabase_client, user_id) from your main application.") 

# Add logger definition if missing (it was used in parse_data_file but not defined globally in this file)
logger = logging.getLogger(__name__) 