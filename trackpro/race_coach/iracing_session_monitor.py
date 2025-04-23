import irsdk
from supabase import Client # Only import Client type hint
import time
import os
import sys
import subprocess
import yaml
import threading # Added for potential stop event

# --- Configuration ---
# Consider moving these to a config file or passing them if they vary
IRSDK_EXE_PATH = "C:\\Users\\lawre\\AppData\\Local\\Programs\\Python\\Python313\\Scripts\\irsdk.exe" # Make sure this path is correct
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

# Event to signal the monitoring thread to stop (optional but good practice)
# stop_event = threading.Event()

def update_supabase_data(supabase: Client, track_name, car_name, track_id, car_id):
    # (Keep the existing logic from update_supabase_data, ensure it takes supabase client as arg)
    # ... (exact code from previous version) ...
    db_track_id = None
    db_car_id = None
    if not supabase: # Check passed-in client
        print("Supabase client not provided to update_supabase_data.", file=sys.stderr)
        return db_track_id, db_car_id
    # ... (rest of the function is identical to the previous version) ...
    print(f"Updating/Checking Supabase: Track={track_name} (iRacing ID: {track_id}), Car={car_name} (iRacing ID: {car_id})")
    try:
        track_response = supabase.table('tracks').upsert(
             {'iracing_id': track_id, 'name': track_name},
             on_conflict='iracing_id'
         ).execute()
        print(f"Track Upsert Response Data: {track_response.data}")
        if track_response.data and track_response.data[0].get('id') is not None:
             db_track_id = track_response.data[0]['id']
             print(f"Upserted/Found track: {track_response.data[0]['name']} (DB ID: {db_track_id})")
        else:
              print(f"Track Upsert failed or did not return expected data. Status: {getattr(track_response, 'status_code', 'N/A')}")

        car_response = supabase.table('cars').upsert(
             {'iracing_id': car_id, 'name': car_name},
              on_conflict='iracing_id'
         ).execute()
        print(f"Car Upsert Response Data: {car_response.data}")
        if car_response.data and car_response.data[0].get('id') is not None:
              db_car_id = car_response.data[0]['id']
              print(f"Upserted/Found car: {car_response.data[0]['name']} (DB ID: {db_car_id})")
        else:
              print(f"Car Upsert failed or did not return expected data. Status: {getattr(car_response, 'status_code', 'N/A')}")

    except Exception as e:
         print(f"Error during Supabase upsert: {e}", file=sys.stderr)

    return db_track_id, db_car_id


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
    # (Keep the existing logic from run_irsdk_parse)
    # ... (exact code from previous version) ...
    print(f"Running: {IRSDK_EXE_PATH} --parse {DATA_TXT_PATH}")
    try:
        result = subprocess.run(
            [IRSDK_EXE_PATH, "--parse", DATA_TXT_PATH],
            capture_output=True, text=True, check=True, timeout=10
        )
        print("irsdk.exe parse successful.")
        return True
    except FileNotFoundError:
        print(f"Error: irsdk.exe not found at {IRSDK_EXE_PATH}", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error running irsdk.exe: Exit code {e.returncode}\nstderr: {e.stderr}", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print(f"Error: irsdk.exe command timed out after 10 seconds.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred running irsdk.exe: {e}", file=sys.stderr)
        return False

def parse_data_file():
    # (Keep the existing logic from parse_data_file)
    # ... (exact code from previous version) ...
    print(f"Attempting to read and parse {DATA_TXT_PATH}...")
    track_name, car_name, track_id, car_id, session_type = None, None, None, None, None
    try:
        with open(DATA_TXT_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                print("Warning: data.txt is empty.")
                return track_name, car_name, track_id, car_id, session_type

        yaml_end_marker = "\n...\n"
        yaml_section = content
        if yaml_end_marker in content:
            yaml_section = content.split(yaml_end_marker, 1)[0]
            # print("Found YAML end marker '...', parsing section before it.") # Less verbose
        else:
            print("Warning: YAML end marker '...' not found. Attempting heuristic split.")
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if i > 0 and not line.startswith(' ') and '   ' in line:
                    yaml_section = "\n".join(lines[:i])
                    break

        if not yaml_section.strip():
            print("Warning: Extracted YAML section is empty.")
            return track_name, car_name, track_id, car_id, session_type

        if not yaml_section.strip().startswith('WeekendInfo:') and not yaml_section.strip().startswith('---'):
             print(f"Warning: Extracted YAML section may lack expected start.")

        data = yaml.safe_load(yaml_section)
        if not data:
            print("Warning: Parsed YAML data is empty or invalid.")
            return track_name, car_name, track_id, car_id, session_type

        # print("YAML parsed successfully.") # Less verbose

        weekend_info = data.get('WeekendInfo', {})
        driver_info = data.get('DriverInfo', {})
        session_info_wrapper = data.get('SessionInfo', {})
        sessions_list = session_info_wrapper.get('Sessions', [])

        track_name = weekend_info.get('TrackDisplayName')
        track_id = weekend_info.get('TrackID') # iRacing ID

        player_car_idx = driver_info.get('DriverCarIdx', -1)
        drivers = driver_info.get('Drivers', [])
        if 0 <= player_car_idx < len(drivers):
             player_driver_info = drivers[player_car_idx]
             car_name = player_driver_info.get('CarScreenName')
             car_id = player_driver_info.get('CarID') # iRacing ID
        # else: print(f"Warning: Invalid PlayerCarIdx") # Less verbose

        current_session_num = data.get('SessionInfo', {}).get('CurrentSessionNum', -1)
        if 0 <= current_session_num < len(sessions_list):
              session_type = sessions_list[current_session_num].get('SessionType')
        # else: print(f"Warning: Cannot determine session type") # Less verbose

        # print(f"Parsed Data -> ...") # Less verbose

    except FileNotFoundError:
        print(f"Error: {DATA_TXT_PATH} not found.", file=sys.stderr)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML from {DATA_TXT_PATH}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred parsing {DATA_TXT_PATH}: {e}", file=sys.stderr)

    return track_name, car_name, track_id, car_id, session_type

def _monitor_loop(supabase_client: Client, logged_in_user_id: str, lap_saver_instance, simple_api_instance):
    """The actual monitoring loop, designed to be run in a thread."""
    # Add simple_api_instance parameter
    global last_session_unique_id, is_connected, last_processed_iracing_track_id, last_processed_iracing_car_id

    print(f"iRacing monitor thread started for user: {logged_in_user_id}")

    if lap_saver_instance is None or simple_api_instance is None:
        print("CRITICAL ERROR: Lap Saver or Simple API instance not provided to monitor thread.", file=sys.stderr)
        return # Stop the thread

    while True: # Consider adding stop_event.is_set() check here if using stop_event
        try:
            # Check connection status FIRST
            is_now_connected = ir.startup(test_file=None)

            # Handle change in connection status (mainly for disconnect)
            if is_now_connected != is_connected:
                if not is_now_connected:
                    # --- Handle Disconnect --- #
                    print("Monitor: iRacing DISCONNECTED.")
                    is_connected = False
                    if hasattr(simple_api_instance, 'update_info_from_monitor'):
                        simple_api_instance.update_info_from_monitor({}, is_connected=False)
                    last_session_unique_id = -1
                    last_processed_iracing_track_id = None
                    last_processed_iracing_car_id = None
                    if lap_saver_instance:
                        lap_saver_instance._current_session_id = None
                else:
                    # --- Handle Initial Connect --- #
                    # We only set is_connected = True AFTER the first successful data parse below
                    # to ensure irsdk is fully ready.
                    print("Monitor: iRacing detected, attempting initial data parse...")
                    last_session_unique_id = -1 # Force parse on connect
                    last_processed_iracing_track_id = None
                    last_processed_iracing_car_id = None

            # If potentially connected (or was just connected), check for session updates
            if is_now_connected:
                current_session_update = ir.session_info_update

                # Trigger parse if counter changed OR if we just connected (is_connected is still False)
                if current_session_update != last_session_unique_id or not is_connected:
                    print(f"Monitor: Session info update detected (Counter: {current_session_update}, Connected Flag: {is_connected}).")
                    last_session_unique_id = current_session_update # Update counter

                    if run_irsdk_parse():
                        track_name, car_name, iracing_track_id, iracing_car_id, session_type = parse_data_file()

                        if track_name is not None and car_name is not None and iracing_track_id is not None and iracing_car_id is not None:

                            # --- First successful parse after connect? Update API state --- #
                            if not is_connected:
                                print("Monitor: First successful parse. Signaling API as CONNECTED.")
                                is_connected = True # NOW set internal flag

                            monitor_update_info = {
                                'current_track': track_name,
                                'current_car': car_name,
                                'session_type': session_type
                            }
                            if hasattr(simple_api_instance, 'update_info_from_monitor'):
                                print(f"Monitor: Updating SimpleAPI state: {monitor_update_info}")
                                simple_api_instance.update_info_from_monitor(monitor_update_info, is_connected=True)
                            else:
                                print("Monitor: Warning - Cannot find update_info_from_monitor method.")
                            # --- End SimpleAPI Update --- #

                            # --- Handle Session Creation/Update --- #
                            if iracing_track_id != last_processed_iracing_track_id or iracing_car_id != last_processed_iracing_car_id:
                                print("Monitor: Change detected in Track/Car IDs.")
                                db_track_id, db_car_id = update_supabase_data(supabase_client, track_name, car_name, iracing_track_id, iracing_car_id)
                                if db_track_id is not None and db_car_id is not None:
                                    new_session_uuid = create_supabase_session(supabase_client, logged_in_user_id, db_track_id, db_car_id, session_type)
                                    if new_session_uuid:
                                        print(f"Monitor: Updating lap saver state. Session UUID: {new_session_uuid}...")
                                        lap_saver_instance._current_session_id = new_session_uuid
                                        lap_saver_instance._current_track_id = db_track_id
                                        lap_saver_instance._current_car_id = db_car_id
                                        lap_saver_instance._current_session_type = session_type
                                        lap_saver_instance._current_lap_number = 0
                                        lap_saver_instance._is_first_telemetry = True
                                        lap_saver_instance._current_lap_data = []
                                        lap_saver_instance._best_lap_time = float('inf')
                                        lap_saver_instance._current_lap_id = None
                                        last_processed_iracing_track_id = iracing_track_id
                                        last_processed_iracing_car_id = iracing_car_id
                                    else: print("Monitor: Failed to create session record.")
                                else: print("Monitor: Skipping session creation: Failed to get DB IDs.")
                            else: print("Monitor: No change detected in Track/Car IDs.")
                        else: print("Monitor: Skipping update: Failed to parse essential data.")
                    else: print("Monitor: Skipping processing due to irsdk.exe error.")

        except Exception as e:
            print(f"Monitor: Error in main loop: {e}", file=sys.stderr)
            if is_connected:
                # Ensure disconnected state is propagated
                print("Monitor: Error caused disconnect.")
                is_connected = False
                if hasattr(simple_api_instance, 'update_info_from_monitor'):
                    simple_api_instance.update_info_from_monitor({}, is_connected=False)
                last_session_unique_id = -1
                last_processed_iracing_track_id = None
                last_processed_iracing_car_id = None
                if lap_saver_instance:
                    lap_saver_instance._current_session_id = None
                print("Monitor: Resetting connection state due to error.")
            time.sleep(10) # Longer sleep on error

        time.sleep(3) # Check every 3 seconds

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