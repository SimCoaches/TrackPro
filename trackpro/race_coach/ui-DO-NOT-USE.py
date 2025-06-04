import sys
import os
import logging
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTabWidget,
    QGroupBox,
    QSplitter,
    QComboBox,
    QStatusBar,
    QMainWindow,
    QMessageBox,
    QApplication,
    QGridLayout,
    QFrame,
    QFormLayout,
    QCheckBox,
    QProgressBar,
    QSizePolicy,
    QSpacerItem,
    QScrollArea,
    QStackedWidget,
    QLineEdit,
    QSlider,
    QTabBar,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QUrl  # Import QUrl
from PyQt5.QtGui import (
    QFont,
    QColor,
    QPalette,
    QPainter,
    QPen,
    QBrush,
    QLinearGradient,
    QRadialGradient,
    QConicalGradient,
    QPixmap,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView  # Add direct import

# ---------------------------------------------

from .widgets.throttle_graph import ThrottleGraphWidget  # Import our throttle graph widget
from .widgets.brake_graph import BrakeGraphWidget  # Import our brake graph widget
from .widgets.steering_graph import SteeringGraphWidget  # Import our steering graph widget
from .widgets.speed_graph import SpeedGraphWidget  # Import our speed graph widget

import time
import threading
import weakref
import numpy as np  # Add numpy import for array handling
import json
import platform
import math
import random  # Import random module for demo animations
from datetime import datetime, timedelta
from pathlib import Path  # Add Path import for file handling
from trackpro.race_coach.utils.data_processing import resample_telemetry  # Import the telemetry processing function

# Need QObject and QThread for background tasks
from PyQt5.QtCore import QObject, QThread

# Import the auth update function directly here as well
from Supabase.auth import update_auth_state_from_client, is_logged_in

# Add our own telemetry validation utilities
from .utils.telemetry_validation import validate_lap_telemetry, calculate_coverage_percentage


# Supabase helpers for laps and telemetry
try:
    from Supabase.database import get_laps, get_telemetry_points, get_sessions  # Add get_sessions import
    from trackpro.database.supabase_client import get_supabase_client  # ADD THIS IMPORT
except Exception as _sup_err:
    logger = logging.getLogger(__name__)
    logger.warning(f"Supabase import failed ({_sup_err}), using fallback functions.")

    # When Supabase is not configured (offline demo) we still want UI to load.
    def get_laps(*_args, **_kwargs):
        return None, "Supabase unavailable"

    def get_telemetry_points(*_args, **_kwargs):
        return None, "Supabase unavailable"

    # Add fallback for get_sessions
    def get_sessions(*_args, **_kwargs):
        # Return some dummy session data for offline testing
        logger.info("Using fallback get_sessions")
        now = datetime.now()
        sessions = [
            {
                "id": "session_1",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "track_name": "Demo Track 1",
                "car_name": "Demo Car A",
            },
            {
                "id": "session_2",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "track_name": "Demo Track 2",
                "car_name": "Demo Car B",
            },
            {
                "id": "session_3",
                "created_at": (now - timedelta(days=2)).isoformat(),
                "track_name": "Demo Track 1",
                "car_name": "Demo Car C",
            },
        ]
        return sessions, "Using fallback data"

    # Add fallback for get_supabase_client if needed
    def get_supabase_client(*_args, **_kwargs):
        logger.warning("Using fallback get_supabase_client")
        return None


# Try to import QPointF and QRectF from QtCore
try:
    from PyQt5.QtCore import QPointF, QRectF, QSizeF
except ImportError:
    # Define fallback classes if imports fail
    class QPointF:
        """Simple replacement for QPointF when not available."""

        def __init__(self, x, y):
            self._x = x
            self._y = y

        def x(self):
            return self._x

        def y(self):
            return self._y

    class QRectF:
        """Simple replacement for QRectF when not available."""

        def __init__(self, *args):
            if len(args) == 4:  # (x, y, width, height)
                self._x = args[0]
                self._y = args[1]
                self._width = args[2]
                self._height = args[3]
            elif len(args) == 2:  # (QPointF, QSizeF)
                point, size = args
                self._x = point.x() if hasattr(point, "x") and callable(point.x) else point.x
                self._y = point.y() if hasattr(point, "y") and callable(point.y) else point.y
                self._width = size.width() if hasattr(size, "width") and callable(size.width) else size.width
                self._height = size.height() if hasattr(size, "height") and callable(size.height) else size.height
            else:
                raise TypeError("QRectF requires either (x, y, width, height) or (QPointF, QSizeF)")

        def left(self):
            return self._x

        def top(self):
            return self._y

        def width(self):
            return self._width

        def height(self):
            return self._height

    class QSizeF:
        """Simple replacement for QSizeF when not available."""

        def __init__(self, width, height):
            self._width = width
            self._height = height

        def width(self):
            return self._width

        def height(self):
            return self._height


# Try to import QPainterPath
try:
    from PyQt5.QtGui import QPainterPath
except ImportError:
    # This is more complex to replace, might need more involved fallback
    class QPainterPath:
        """Simple replacement for QPainterPath - limited functionality."""

        def __init__(self):
            self._points = []
            self._current_point = (0, 0)

        def moveTo(self, x, y=None):
            """Move to position without drawing a line."""
            if y is None and isinstance(x, (QPointF, tuple)):
                # Handle QPointF or tuple
                if isinstance(x, QPointF):
                    x_val = x.x() if callable(x.x) else x.x
                    y_val = x.y() if callable(x.y) else x.y
                else:
                    x_val, y_val = x
            else:
                x_val, y_val = x, y

            self._current_point = (x_val, y_val)
            self._points = [self._current_point]

        def lineTo(self, x, y=None):
            """Draw line from current position to specified point."""
            if y is None and isinstance(x, (QPointF, tuple)):
                # Handle QPointF or tuple
                if isinstance(x, QPointF):
                    x_val = x.x() if callable(x.x) else x.x
                    y_val = x.y() if callable(x.y) else x.y
                else:
                    x_val, y_val = x
            else:
                x_val, y_val = x, y

            self._current_point = (x_val, y_val)
            self._points.append(self._current_point)

        def closeSubpath(self):
            """Close the current subpath by drawing a line to the beginning point."""
            if self._points and len(self._points) > 0:
                self._points.append(self._points[0])
                self._current_point = self._points[0]

        def isEmpty(self):
            """Return True if the path contains no elements."""
            return len(self._points) == 0

        def elementCount(self):
            """Return the number of path elements."""
            return len(self._points)


logger = logging.getLogger(__name__)


# --- Worker for Background Telemetry Fetching (Phase 3, Step 7) ---
class TelemetryFetchWorker(QObject):
    # finished = pyqtSignal(object, object) # Pass two results (left_pts, right_pts) - Original
    # Modified finished signal to emit dictionaries containing stats and points
    finished = pyqtSignal(object, object)
    error = pyqtSignal(str, str)  # Pass two error messages

    def __init__(self, left_lap_id, right_lap_id):
        super().__init__()
        self.left_lap_id = left_lap_id
        self.right_lap_id = right_lap_id
        self.is_cancelled = False

        # Store a reference to the main client module
        try:
            from trackpro.database.supabase_client import supabase as app_supabase

            self.app_supabase = app_supabase
            logger.info("TelemetryFetchWorker: Got main Supabase client reference")
        except ImportError:
            self.app_supabase = None
            logger.error("TelemetryFetchWorker: Could not import main Supabase client")

    def _calculate_lap_stats(self, telemetry_points):
        """Calculate statistics from a list of telemetry points."""
        if not telemetry_points or len(telemetry_points) < 2:
            return None  # Not enough data

        # **FIX: Map database field names to what graphs expect**
        mapped_points = []
        for point in telemetry_points:
            mapped_point = point.copy()  # Copy the original point
        
            # Map track_position to LapDist (what graphs expect)
            if 'track_position' in mapped_point:
                mapped_point['LapDist'] = mapped_point['track_position']
        
            # Ensure we have all the required fields
            mapped_point.setdefault('LapDist', 0)
            mapped_point.setdefault('throttle', 0)
            mapped_point.setdefault('brake', 0)
            mapped_point.setdefault('steering', 0)
            mapped_point.setdefault('speed', 0)
            mapped_point.setdefault('timestamp', 0)
        
            mapped_points.append(mapped_point)
    
        # Sort points by timestamp just in case
        mapped_points.sort(key=lambda p: p.get("timestamp", 0))

        total_time = mapped_points[-1].get("timestamp", 0) - mapped_points[0].get("timestamp", 0)
        if total_time <= 0:
            return None  # Invalid time range

        full_throttle_time = 0
        heavy_braking_time = 0
        cornering_time = 0

        # Define thresholds
        THROTTLE_THRESHOLD = 0.98
        BRAKE_THRESHOLD = 0.80
        STEERING_THRESHOLD = 0.1  # Radians, adjust as needed

        speeds = []
        track_positions = []
        timestamps = []

        # Store the previous timestamp for duration calculations
        prev_timestamp = mapped_points[0].get("timestamp", 0)

        # Track current segment
        in_full_throttle = False
        in_heavy_braking = False
        in_cornering = False

        for point in mapped_points:
            timestamp = point.get("timestamp", 0)
            throttle = point.get("throttle", 0)
            brake = point.get("brake", 0)
            steering = abs(point.get("steering", 0))
            speed = point.get("speed", 0)
            track_position = point.get("LapDist", point.get("track_position", 0))  # Use mapped field

            # Duration of this segment
            duration = timestamp - prev_timestamp

            # Only count if duration is reasonable
            if 0 < duration < 1.0:  # Reasonable duration between telemetry points
                # Track full throttle time
                if throttle >= THROTTLE_THRESHOLD:
                    if not in_full_throttle:
                        in_full_throttle = True
                    full_throttle_time += duration
                else:
                    in_full_throttle = False

                # Track heavy braking time
                if brake >= BRAKE_THRESHOLD:
                    if not in_heavy_braking:
                        in_heavy_braking = True
                    heavy_braking_time += duration
                else:
                    in_heavy_braking = False

                # Track cornering time (significant steering input)
                if steering >= STEERING_THRESHOLD:
                    if not in_cornering:
                        in_cornering = True
                    cornering_time += duration
                else:
                    in_cornering = False

            # Collect data for analysis
            speeds.append(speed)
            track_positions.append(track_position)
            timestamps.append(timestamp)

            # Update previous timestamp
            prev_timestamp = timestamp

        # Calculate speed statistics
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0

        # Calculate percentage of time spent in each zone
        full_throttle_pct = (full_throttle_time / total_time) * 100 if total_time > 0 else 0
        heavy_braking_pct = (heavy_braking_time / total_time) * 100 if total_time > 0 else 0
        cornering_pct = (cornering_time / total_time) * 100 if total_time > 0 else 0

        # Create stats and points data structure
        stats = {
            "total_time": total_time,
            "avg_speed": avg_speed,
            "max_speed": max_speed,
            "full_throttle_pct": full_throttle_pct,
            "heavy_braking_pct": heavy_braking_pct,
            "cornering_pct": cornering_pct,
        }

        # **IMPORTANT: Return the mapped points, not the original ones**
        return {"stats": stats, "points": mapped_points}

    def run(self):
        """Fetch telemetry data for both laps and calculate stats."""
        logger.info(f"Worker thread starting fetch for {self.left_lap_id} and {self.right_lap_id}")
        left_data, right_data = None, None
        left_error, right_error = "", ""

        # Ensure we have a valid Supabase client
        supabase_client = None

        # Try getting an authenticated client from multiple sources
        try:
            # First, try using the app-level Supabase client reference
            if hasattr(self, "app_supabase") and self.app_supabase and self.app_supabase.is_authenticated():
                logger.info("TelemetryFetchWorker: Using main app Supabase client")
                supabase_client = self.app_supabase

            # As a fallback, try direct import from database client
            if not supabase_client:
                from trackpro.database.supabase_client import supabase

                if supabase and supabase.is_authenticated():
                    logger.info("TelemetryFetchWorker: Using imported Supabase client")
                    supabase_client = supabase

            # Last resort, try from Supabase module
            if not supabase_client:
                import Supabase.client

                if hasattr(Supabase.client, "supabase") and Supabase.client.supabase:
                    logger.info("TelemetryFetchWorker: Using Supabase module client")
                    supabase_client = Supabase.client.supabase

        except Exception as e:
            logger.error(f"TelemetryFetchWorker: Error getting Supabase client: {e}")

        # If we still don't have a client, use a direct approach
        if not supabase_client:
            try:
                import Supabase.auth

                if not Supabase.auth.is_logged_in():
                    logger.warning("TelemetryFetchWorker: User not logged in according to auth module")
            except Exception as e:
                logger.error(f"TelemetryFetchWorker: Error accessing Supabase auth module: {e}")

        # Define columns needed for calculation and graphs
        required_columns = ["track_position", "speed", "throttle", "brake", "steering", "timestamp"]

        try:
            # Fetch left lap
            if not self.is_cancelled:
                try:
                    # Fetch all required columns
                    from Supabase.database import get_telemetry_points

                    left_pts, msg_left = get_telemetry_points(self.left_lap_id, columns=required_columns)
                    if left_pts is None:
                        left_error = msg_left or "Failed to fetch telemetry"
                        logger.warning(f"Failed fetching left lap telemetry: {left_error}")
                    else:
                        logger.info(f"Fetched {len(left_pts)} points for left lap {self.left_lap_id}")
                        left_data = self._calculate_lap_stats(left_pts)
                        if not left_data:
                            left_error = "Stat calculation failed (left)"
                            logger.warning(f"Could not calculate stats for left lap {self.left_lap_id}")
                except Exception as e:
                    left_error = f"Exception: {str(e)}"
                    logger.error(f"Exception fetching left lap telemetry: {e}")

            # Fetch right lap
            if not self.is_cancelled:
                try:
                    # Fetch all required columns
                    from Supabase.database import get_telemetry_points

                    right_pts, msg_right = get_telemetry_points(self.right_lap_id, columns=required_columns)
                    if right_pts is None:
                        right_error = msg_right or "Failed to fetch telemetry"
                        logger.warning(f"Failed fetching right lap telemetry: {right_error}")
                    else:
                        logger.info(f"Fetched {len(right_pts)} points for right lap {self.right_lap_id}")
                        right_data = self._calculate_lap_stats(right_pts)
                        if not right_data:
                            right_error = "Stat calculation failed (right)"
                            logger.warning(f"Could not calculate stats for right lap {self.right_lap_id}")
                except Exception as e:
                    right_error = f"Exception: {str(e)}"
                    logger.error(f"Exception fetching right lap telemetry: {e}")

            # Check results and emit appropriate signal
            if self.is_cancelled:
                logger.info("Telemetry fetch cancelled.")
                self.error.emit("Operation Cancelled", "Operation Cancelled")
            elif left_data is None and right_data is None:
                self.error.emit(left_error or "Fetch/Calc failed", right_error or "Fetch/Calc failed")
            else:
                # Emit results (dictionaries with stats and points) even if one failed
                logger.info(
                    f"Emitting finished signal. Left valid: {left_data is not None}, Right valid: {right_data is not None}"
                )
                self.finished.emit(left_data, right_data)

        except Exception as e:
            logger.error(f"Exception in TelemetryFetchWorker: {e}", exc_info=True)
            self.error.emit(f"Worker Error: {e}", f"Worker Error: {e}")

    def cancel(self):
        self.is_cancelled = True

    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- End Worker ---


# --- Worker for Background Initial Data Loading ---
class InitialLoadWorker(QObject):
    """Worker to load initial session and lap lists in the background."""

    sessions_loaded = pyqtSignal(list, str)  # (sessions_data, message)
    laps_loaded = pyqtSignal(list, str)  # (laps_data, message)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_cancelled = False

    def run(self):
        """Fetch initial sessions and laps, filtering sessions that have laps."""
        logger.info("InitialLoadWorker started.")

        try:
            # 1. Check Authentication
            from trackpro.database.supabase_client import supabase as main_supabase

            is_authenticated = False
            user_id = None
            try:
                is_authenticated = main_supabase.is_authenticated()
                if is_authenticated:
                    # Corrected: Call get_user directly on the manager instance
                    user_response = main_supabase.get_user()
                    if user_response and user_response.user:
                        user_id = user_response.user.id
                    else:
                        logger.warning("InitialLoadWorker: is_authenticated is True, but get_user returned no user.")
                        is_authenticated = False  # Treat as not authenticated if user object is missing
                logger.info(f"InitialLoadWorker: Auth check via main client: {is_authenticated}, UserID: {user_id}")
            except Exception as auth_err:
                # Log the specific error, check if it's the expected 'auth' attribute error
                logger.error(f"Error checking auth state in InitialLoadWorker: {auth_err}", exc_info=True)
                # Attempt to continue if possible, otherwise emit error
                if "'SupabaseManager' object has no attribute 'auth'" in str(auth_err):
                    logger.warning("Caught known auth attribute error, attempting recovery...")
                    # Maybe try alternative ways to check auth or just proceed cautiously
                    is_authenticated = False  # Assume not authenticated if specific check fails
                else:
                    self.error.emit(f"Authentication check failed: {auth_err}")
                    self.finished.emit()
                    return

            if self.is_cancelled:
                return

            # If authentication failed (either initially or during user fetch), exit
            if not is_authenticated or not user_id:
                logger.warning("InitialLoadWorker: User not authenticated or user ID not found.")
                self.sessions_loaded.emit([], "User not logged in")
                self.laps_loaded.emit([], "User not logged in")
                self.finished.emit()
                return

            # 2. Fetch User's Sessions from Supabase (limit to reduce initial load time)
            logger.info("InitialLoadWorker: Fetching user sessions from Supabase...")
            sessions, msg_sess = get_sessions(limit=50, user_only=True)  # Reduced limit for faster initial load

            # Also check for cached session data in local file (but limit processing)
            local_sessions = []
            try:
                import os
                import json

                local_session_file = os.path.join(
                    os.path.expanduser("~/Documents/TrackPro/Sessions"), "active_sessions.json"
                )

                if os.path.exists(local_session_file):
                    logger.info(f"InitialLoadWorker: Found local session cache file: {local_session_file}")
                    with open(local_session_file, "r") as f:
                        cached_sessions = json.load(f)

                    # Convert cached sessions to format expected by UI (limit to recent sessions)
                    processed_count = 0
                    max_local_sessions = 20  # Limit local sessions to speed up loading
                    
                    for session_id, session_data in cached_sessions.items():
                        if processed_count >= max_local_sessions:
                            break
                            
                        # Ensure the session belongs to this user
                        if session_data.get("user_id") == user_id:
                            # Check if this session is already in sessions list from Supabase
                            if not any(s.get("id") == session_id for s in sessions if sessions):
                                # Format the session data to match Supabase format
                                formatted_session = {
                                    "id": session_id,
                                    "user_id": user_id,
                                    "track_name": session_data.get("track_name", "Unknown Track"),
                                    "car_name": session_data.get("car_name", "Unknown Car"),
                                    "session_type": session_data.get("session_type", "Race"),
                                    "track_config": session_data.get("track_config", ""),
                                    "session_date": session_data.get("timestamp", ""),
                                    "is_local_cache": True,  # Flag to indicate it came from local cache
                                }
                                local_sessions.append(formatted_session)
                                processed_count += 1

                    logger.info(f"InitialLoadWorker: Loaded {len(local_sessions)} additional sessions from local cache")
            except Exception as cache_error:
                logger.error(f"InitialLoadWorker: Error loading local session cache: {cache_error}", exc_info=True)

            if self.is_cancelled:
                return

            # Combine Supabase sessions and local sessions
            if sessions is None:
                sessions = []

            # Add local sessions to the list
            combined_sessions = sessions + local_sessions

            if not combined_sessions:
                logger.info("InitialLoadWorker: No sessions found for the user.")
                self.sessions_loaded.emit([], "No sessions found")
                self.laps_loaded.emit([], "No sessions found")
                self.finished.emit()
                return

            # 3. Efficiently Find Session IDs with Laps (optimized for speed)
            logger.info(f"InitialLoadWorker: Checking which of the {len(combined_sessions)} sessions have laps...")
            session_ids = [s["id"] for s in combined_sessions if s.get("id")]  # Get IDs of fetched sessions
            lap_session_ids = set()

            if session_ids:
                try:
                    # Limit the query to reduce load time - check only recent sessions first
                    recent_session_ids = session_ids[:30]  # Check only first 30 sessions for speed
                    
                    # Query laps table only for the session IDs we are interested in
                    laps_query = (
                        main_supabase.client.table("laps")
                        .select("session_id")
                        .in_("session_id", recent_session_ids)
                        .limit(100)  # Limit results for faster query
                        .execute()
                    )

                    if laps_query.data:
                        lap_session_ids = {lap["session_id"] for lap in laps_query.data if lap.get("session_id")}
                        logger.info(f"InitialLoadWorker: Found {len(lap_session_ids)} session IDs with laps.")
                    else:
                        logger.info("InitialLoadWorker: No laps found for any of the fetched sessions.")

                except Exception as lap_fetch_err:
                    logger.error(f"InitialLoadWorker: Error fetching lap session IDs: {lap_fetch_err}")
                    # Proceed without filtering if this fails, but log the error
                    lap_session_ids = set(recent_session_ids)  # Assume recent sessions have laps if query fails

            # 4. Filter Sessions (optimized)
            # Include both sessions with laps and sessions from local cache (newer sessions might not have laps yet)
            valid_sessions = [
                s for s in combined_sessions if s.get("id") in lap_session_ids or s.get("is_local_cache", False)
            ]

            # Sort sessions by date (newest first) and limit to reduce UI load
            valid_sessions.sort(key=lambda s: s.get("session_date", ""), reverse=True)

            # Limit to most recent sessions for faster initial load
            if len(valid_sessions) > 25:
                valid_sessions = valid_sessions[:25]
                logger.info(f"InitialLoadWorker: Limited to {len(valid_sessions)} most recent sessions for faster loading.")
            else:
                logger.info(f"InitialLoadWorker: Filtered down to {len(valid_sessions)} sessions.")

            # Emit filtered sessions
            self.sessions_loaded.emit(valid_sessions, msg_sess or "Sessions loaded")
            if self.is_cancelled:
                return

            # 5. Fetch Laps for the First Valid Session (if any) - optimized
            first_session_id = None
            if valid_sessions:
                first_session_id = valid_sessions[0].get("id")

            if first_session_id:
                logger.info(f"InitialLoadWorker: Fetching laps for first valid session: {first_session_id}")
                laps, msg_laps = get_laps(limit=20, user_only=True, session_id=first_session_id)  # Reduced limit for faster load
                if self.is_cancelled:
                    return

                if laps is None:
                    logger.error(f"InitialLoadWorker: Failed to fetch laps for first session: {msg_laps}")
                    self.laps_loaded.emit([], f"Failed to load laps: {msg_laps}")
                else:
                    logger.info(f"InitialLoadWorker: Fetched {len(laps)} laps for the first valid session.")
                    self.laps_loaded.emit(laps, msg_laps or "Laps loaded")
            else:
                logger.info("InitialLoadWorker: No valid sessions with laps found, skipping initial lap load.")
                self.laps_loaded.emit([], "No sessions with laps found")

            self.finished.emit()
            logger.info("InitialLoadWorker finished.")

        except Exception as e:
            logger.error(f"Exception in InitialLoadWorker: {e}", exc_info=True)
            self.error.emit(f"Worker Error: {e}")
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True
        logger.info("InitialLoadWorker cancellation requested.")
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- End Initial Load Worker ---


# --- SuperLap Session Worker ---
class SuperLapSessionWorker(QObject):
    """Worker to load SuperLap sessions in the background."""
    
    sessions_loaded = pyqtSignal(list)  # (sessions_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.is_cancelled = False

    def run(self):
        """Load sessions with ML data available."""
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                self.error.emit("Authentication required")
                self.finished.emit()
                return
            
            # Get user sessions with car/track info
            # CRITICAL FIX: Include track length_meters in the query
            sessions_result = (
                main_supabase.client.table("sessions")
                .select("id,car_id,track_id,created_at,cars(name),tracks(name, length_meters)")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            
            if not sessions_result.data:
                self.sessions_loaded.emit([])
                self.finished.emit()
                return
            
            # Filter sessions that have matching ML data available
            valid_sessions = []
            
            for session in sessions_result.data:
                if self.is_cancelled:
                    return
                    
                car_id = session.get('car_id')
                track_id = session.get('track_id')
                
                if car_id and track_id:
                    # Check if ML data exists for this car/track combo
                    try:
                        ml_check = (
                            main_supabase.client.table("laps_ml")
                            .select("id")
                            .eq("car_id", car_id)
                            .eq("track_id", track_id)
                            .limit(1)
                            .execute()
                        )
                        
                        if ml_check.data:  # ML data exists for this car/track
                            valid_sessions.append(session)
                    except Exception as ml_error:
                        print(f"Error checking ML data for session {session.get('id')}: {ml_error}")
                        # Include session anyway for now during development
                        valid_sessions.append(session)
                        continue
            
            # Sort sessions by date (newest first) and limit
            valid_sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
            
            if len(valid_sessions) > 25:
                valid_sessions = valid_sessions[:25]
            
            self.sessions_loaded.emit(valid_sessions)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- End SuperLap Session Worker ---


# --- SuperLap User Lap Worker ---
class SuperLapUserLapWorker(QObject):
    """Worker to load user laps for a session in the background."""
    
    laps_loaded = pyqtSignal(list)  # (laps_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self, session_id):
        super().__init__()
        self.session_id = session_id
        self.is_cancelled = False

    def run(self):
        """Load user laps for the session."""
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                self.error.emit("Authentication required")
                self.finished.emit()
                return
            
            # Get laps for this session
            laps_result = (
                main_supabase.client.table("laps")
                .select("id,lap_number,lap_time,is_valid")
                .eq("session_id", self.session_id)
                .eq("is_valid", True)  # Only show valid laps
                .order("lap_number")
                .execute()
            )
            
            if self.is_cancelled:
                return
            
            if laps_result.data:
                self.laps_loaded.emit(laps_result.data)
            else:
                self.laps_loaded.emit([])
            
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- End SuperLap User Lap Worker ---


# --- SuperLap ML Lap Worker ---
class SuperLapMLLapWorker(QObject):
    """Worker to load ML laps for a car/track combination in the background."""
    
    laps_loaded = pyqtSignal(list)  # (ml_laps_data)
    error = pyqtSignal(str)  # (error_message)
    finished = pyqtSignal()

    def __init__(self, car_id, track_id):
        super().__init__()
        self.car_id = car_id
        self.track_id = track_id
        self.is_cancelled = False

    def run(self):
        """Load ML laps for the car/track combination."""
        try:
            ml_laps_data = self._get_filtered_ml_laps(self.car_id, self.track_id)
            
            if self.is_cancelled:
                return
            
            self.laps_loaded.emit(ml_laps_data)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def _get_filtered_ml_laps(self, car_id, track_id):
        """Get ML laps filtered by car and track from Supabase laps_ml table."""
        if not car_id or not track_id:
            return []
            
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available for ML laps")
                return []
            
            # Query the laps_ml table for ML-optimized laps matching this car/track combo
            ml_laps_result = (
                main_supabase.client.table("laps_ml")
                .select("*")
                .eq("car_id", car_id)
                .eq("track_id", track_id)
                .order("confidence_score", desc=True)  # Best confidence first
                .limit(10)  # Limit to top 10 ML laps
                .execute()
            )
            
            if not ml_laps_result.data:
                print(f"No ML laps found for car_id={car_id}, track_id={track_id}")
                return []
            
            ml_laps = []
            for ml_lap in ml_laps_result.data:
                if self.is_cancelled:
                    return []
                
                # Get additional optimization details if available
                optimization_details = {}
                
                # Try to get brake points from ml_optimizations table
                try:
                    opt_result = (
                        main_supabase.client.table("ml_optimizations")
                        .select("optimization_type,details")
                        .eq("ml_lap_id", ml_lap.get("id"))
                        .execute()
                    )
                    
                    if opt_result.data:
                        for opt in opt_result.data:
                            opt_type = opt.get("optimization_type")
                            details = opt.get("details", {})
                            
                            if isinstance(details, str):
                                import json
                                try:
                                    details = json.loads(details)
                                except:
                                    details = {}
                            
                            if opt_type == "brake_points":
                                optimization_details["brake_points"] = details.get("points", [])
                            elif opt_type == "throttle_points":
                                optimization_details["throttle_points"] = details.get("points", [])
                            elif opt_type == "racing_line":
                                optimization_details["racing_line"] = details.get("sections", [])
                                
                except Exception as opt_error:
                    print(f"Error fetching optimization details: {opt_error}")
                
                # Build the ML lap data structure
                ml_lap_data = {
                    'id': ml_lap.get('id'),
                    'lap_time': ml_lap.get('lap_time', 0),
                    'predicted_improvement_ms': ml_lap.get('predicted_improvement_ms', 0),
                    'confidence_score': ml_lap.get('confidence_score', 0),
                    'optimization_method': ml_lap.get('optimization_method', 'ml_analysis'),
                    'model_used': ml_lap.get('model_used', 'AI Model'),
                    'car_id': car_id,
                    'track_id': track_id,
                    'created_at': ml_lap.get('created_at'),
                    **optimization_details  # Add brake_points, throttle_points, racing_line
                }
                
                ml_laps.append(ml_lap_data)
            
            print(f"Found {len(ml_laps)} ML laps for car_id={car_id}, track_id={track_id}")
            return ml_laps
            
        except Exception as e:
            print(f"Error fetching ML laps from Supabase: {e}")
            return []

    def cancel(self):
        self.is_cancelled = True
        
    def stop_monitoring(self):
        """Alias for cancel to match cleanup interface."""
        self.cancel()


# --- End SuperLap ML Lap Worker ---


class GaugeBase(QWidget):
    """Base class for custom gauge widgets."""

    def __init__(self, min_value=0, max_value=100, parent=None):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value

        # Appearance settings
        self.gauge_color = QColor(0, 122, 204)  # #007ACC
        self.background_color = QColor(45, 45, 48)  # #2D2D30
        self.text_color = QColor(255, 255, 255)  # White

        # Set minimum size for proper rendering
        self.setMinimumSize(200, 150)

    def set_value(self, value):
        """Set the current value of the gauge."""
        # Clamp value to range
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()  # Trigger a repaint

    def get_normalized_value(self):
        """Get the normalized value (0-1) for drawing."""
        range_value = self.max_value - self.min_value
        if range_value == 0:
            return 0
        return (self.value - self.min_value) / range_value

    def paintEvent(self, event):
        """Override to implement custom painting."""
        # Base class does nothing - override in subclasses
        pass


class SpeedGauge(GaugeBase):
    """Custom gauge widget for displaying vehicle speed."""

    def __init__(self, parent=None):
        super().__init__(0, 300, parent)  # Speed from 0-300 km/h
        self.setObjectName("SpeedGauge")
        self.title = "Speed"
        self.units = "km/h"

        # Special colors for speed display
        self.low_speed_color = QColor(0, 150, 200)
        self.high_speed_color = QColor(255, 50, 50)

    def paintEvent(self, event):
        """Paint the speed gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Enforce minimum size for proper rendering
        if width < 100 or height < 50:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.background_color))
            painter.drawRect(0, 0, width, height)

            # Draw a simple horizontal bar for speed
            normalized = self.get_normalized_value()
            if normalized > 0:
                fill_width = int(normalized * width)

                # Simple gradient from blue to red
                gradient = QLinearGradient(0, 0, width, 0)
                gradient.setColorAt(0, self.low_speed_color)
                gradient.setColorAt(1, self.high_speed_color)

                painter.setBrush(QBrush(gradient))
                painter.drawRect(0, 0, fill_width, height)

            # Add basic speed text if there's enough room
            if width >= 40 and height >= 20:
                painter.setPen(QPen(self.text_color))
                painter.drawText(0, 0, width, height, Qt.AlignCenter, f"{self.value:.0f}")

            return

        # Regular rendering for normal sizes
        # Calculate dimensions
        padding = max(5, min(10, width / 20))  # Adaptive padding
        gauge_width = width - (padding * 2)
        gauge_height = max(10, min(30, height / 5))  # Adaptive height

        # Draw gauge background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.background_color.darker(120)))
        painter.drawRoundedRect(padding, height - gauge_height - padding, gauge_width, gauge_height, 5, 5)

        # Draw gauge fill - gradient from blue to red based on speed
        normalized = self.get_normalized_value()
        if normalized > 0:
            # Create gradient
            gradient = QLinearGradient(padding, 0, padding + gauge_width, 0)
            gradient.setColorAt(0, self.low_speed_color)
            gradient.setColorAt(1, self.high_speed_color)

            painter.setBrush(QBrush(gradient))
            fill_width = int(normalized * gauge_width)
            painter.drawRoundedRect(padding, height - gauge_height - padding, fill_width, gauge_height, 5, 5)

        # Draw title if there's enough room
        if height >= 80:
            title_font = painter.font()
            title_font.setPointSize(max(8, min(12, width / 20)))  # Adaptive font size
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QPen(self.text_color))
            painter.drawText(padding, padding, gauge_width, 30, Qt.AlignLeft | Qt.AlignVCenter, self.title)

        # Draw value with adaptive font size
        value_font = painter.font()
        value_font.setPointSize(max(10, min(22, width / 10)))  # Adaptive font size
        value_font.setBold(True)
        painter.setFont(value_font)
        value_text = f"{self.value:.1f} {self.units}"
        painter.drawText(padding, 40, gauge_width, 50, Qt.AlignCenter, value_text)

        # Only draw tick marks if there's enough room
        if width >= 200 and height >= 100:
            painter.setPen(QPen(self.text_color.lighter(150), 1))
            tick_y = height - gauge_height - padding - 5

            # Major ticks every 50 km/h
            for speed in range(0, int(self.max_value) + 1, 50):
                tick_x = padding + (speed / self.max_value) * gauge_width
                painter.drawLine(int(tick_x), tick_y, int(tick_x), tick_y - 10)

                # Draw tick label
                painter.drawText(int(tick_x) - 15, tick_y - 15, 30, 20, Qt.AlignCenter, str(speed))

            # Minor ticks every 10 km/h
            painter.setPen(QPen(self.text_color.lighter(120), 0.5))
            for speed in range(0, int(self.max_value) + 1, 10):
                if speed % 50 != 0:  # Skip major ticks
                    tick_x = padding + (speed / self.max_value) * gauge_width
                    painter.drawLine(int(tick_x), tick_y, int(tick_x), tick_y - 5)


class RPMGauge(GaugeBase):
    """Custom gauge widget for displaying engine RPM."""

    def __init__(self, parent=None):
        super().__init__(0, 10000, parent)  # RPM from 0-10000
        self.setObjectName("RPMGauge")
        self.title = "RPM"
        self.redline = 7500  # Default redline

    def set_redline(self, redline):
        """Set the redline RPM value."""
        self.redline = redline
        self.update()

    def paintEvent(self, event):
        """Paint the RPM gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Enforce minimum size for proper rendering
        if width < 100 or height < 100:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.background_color))
            painter.drawRect(0, 0, width, height)

            # Draw a simple arc for RPM if possible
            if width >= 40 and height >= 40:
                center_x = width / 2
                center_y = height / 2
                radius = min(width, height) / 2 - 2

                # Draw background arc
                arc_rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
                painter.setPen(QPen(self.text_color.darker(120), 2))
                painter.drawArc(arc_rect, 135 * 16, 270 * 16)

                # Draw filled arc for current RPM
                normalized = self.get_normalized_value()
                if normalized > 0:
                    redline_normalized = (self.redline - self.min_value) / (self.max_value - self.min_value)

                    # Determine color based on whether RPM is approaching redline
                    if normalized < redline_normalized * 0.8:
                        gauge_color = QColor(0, 150, 200)  # Blue for normal operation
                    elif normalized < redline_normalized:
                        gauge_color = QColor(255, 150, 0)  # Orange for approaching redline
                    else:
                        gauge_color = QColor(255, 50, 50)  # Red for at/beyond redline

                    # Draw filled arc
                    painter.setPen(QPen(gauge_color, 2, Qt.SolidLine, Qt.RoundCap))
                    span = normalized * 270
                    painter.drawArc(arc_rect, 135 * 16, int(span * 16))

            # Add basic RPM text
            painter.setPen(QPen(self.text_color))
            rpm_text = f"{self.value/1000:.1f}k"
            painter.drawText(0, 0, width, height, Qt.AlignCenter, rpm_text)

            return

        # Regular rendering for normal sizes
        # Calculate dimensions and center point
        margin = max(5, min(10, width / 20))  # Adaptive margin
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - margin

        # Draw gauge background - arc from 135° to 405° (270° span)
        start_angle = 135
        span_angle = 270
        arc_rect = QRectF(QPointF(center_x - radius, center_y - radius), QSizeF(radius * 2, radius * 2))

        # Draw outer ring
        painter.setPen(QPen(self.text_color.darker(120), 5))
        painter.drawArc(arc_rect, start_angle * 16, span_angle * 16)

        # Calculate normalized position for current value and redline
        normalized = self.get_normalized_value()
        redline_normalized = (self.redline - self.min_value) / (self.max_value - self.min_value)

        # Draw filled arc for current RPM
        if normalized > 0:
            # Determine color based on whether RPM is approaching redline
            if normalized < redline_normalized * 0.8:
                gauge_color = QColor(0, 150, 200)  # Blue for normal operation
            elif normalized < redline_normalized:
                gauge_color = QColor(255, 150, 0)  # Orange for approaching redline
            else:
                gauge_color = QColor(255, 50, 50)  # Red for at/beyond redline

            # Draw filled arc
            pen_width = max(5, min(10, width / 30))  # Adaptive pen width
            painter.setPen(QPen(gauge_color, pen_width, Qt.SolidLine, Qt.RoundCap))
            span = normalized * span_angle
            painter.drawArc(arc_rect, start_angle * 16, int(span * 16))

        # Draw redline marker
        if redline_normalized > 0 and redline_normalized <= 1:
            redline_angle = start_angle + (redline_normalized * span_angle)
            redline_x = center_x + radius * 0.95 * math.cos(math.radians(redline_angle))
            redline_y = center_y + radius * 0.95 * math.sin(math.radians(redline_angle))

            painter.setPen(QPen(QColor(255, 0, 0), 3))  # Thick red pen
            painter.drawLine(int(center_x), int(center_y), int(redline_x), int(redline_y))

        # Draw RPM text in center
        value_font = painter.font()
        value_font.setPointSize(18)
        value_font.setBold(True)
        painter.setFont(value_font)
        painter.setPen(QPen(self.text_color))

        # Format RPM text - show in thousands with one decimal place
        rpm_text = f"{self.value/1000:.1f}k"
        painter.drawText(arc_rect, Qt.AlignCenter, rpm_text)

        # Draw title text
        title_font = painter.font()
        title_font.setPointSize(12)
        painter.setFont(title_font)
        title_rect = QRectF(arc_rect.left(), arc_rect.top() + arc_rect.height() // 2 + 10, arc_rect.width(), 30)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)


class SteeringWheelWidget(GaugeBase):
    """Widget for steering wheel visualization."""

    def __init__(self, parent=None):
        super().__init__(-1.0, 1.0, parent)  # Steering ranges from -1.0 to 1.0
        self.setObjectName("SteeringWheelWidget")
        self.title = "Steering"

        # Special colors and settings for the steering display
        self.wheel_color = QColor(50, 50, 50)  # Dark gray for wheel
        self.wheel_rim_color = QColor(80, 80, 80)  # Lighter gray for rim
        self.wheel_marker_color = QColor(255, 0, 0)  # Red for center marker
        self.steering_angle = 0.0  # Current steering angle in radians
        # Set max rotation to handle 1080-degree wheels (convert to radians)
        # 1080 degrees = 3 * 360 degrees = 3 * 2π radians ≈ 18.85 radians
        self.max_rotation = 3.0 * math.pi  # Maximum steering wheel rotation in radians (1080 degrees)

        # Set minimum size for proper rendering
        self.setMinimumSize(180, 180)

        # Performance optimization: cache the rendered wheel
        self._cached_wheel = None
        self._last_size = (0, 0)
        self._last_angle = None

    def set_value(self, value):
        """Set the current steering wheel angle (-1.0 to 1.0)."""
        # Call the parent method to handle normalization
        old_value = self.value
        super().set_value(value)

        # Only update the angle if the value has actually changed
        if old_value != self.value:
            self.steering_angle = value * self.max_rotation
            self._last_angle = None  # Invalidate the cache when angle changes
            self.update()  # Trigger a repaint

    def set_max_rotation(self, max_rotation):
        """Set the maximum rotation angle in radians."""
        if self.max_rotation != max_rotation:
            self.max_rotation = max_rotation
            self._last_angle = None  # Invalidate the cache
            self.update()

    def paintEvent(self, event):
        """Paint the steering wheel visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Enforce minimum size for proper rendering
        if width < 100 or height < 100:
            # Draw a simplified version for very small sizes
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.background_color))
            painter.drawRect(0, 0, width, height)

            # Draw a simple line indicating steering direction
            if width >= 40 and height >= 40:
                center_x = width / 2
                center_y = height / 2
                line_length = min(width, height) / 2 - 5

                # Calculate the steering angle for visualization
                angle = self.steering_angle

                # Line endpoint
                end_x = center_x + line_length * math.sin(angle)
                end_y = center_y - line_length * math.cos(angle)

                # Draw the line
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawLine(int(center_x), int(center_y), int(end_x), int(end_y))

            return

        # Regular rendering for normal sizes
        # Calculate dimensions and center point
        center_x = width / 2
        center_y = height / 2

        # Check if we need to redraw the cached wheel
        current_size = (width, height)
        if self._cached_wheel is None or self._last_size != current_size or self._last_angle != self.steering_angle:
            # Clear the old cache if size changed
            if self._last_size != current_size:
                self._cached_wheel = None

            self._last_size = current_size
            self._last_angle = self.steering_angle

            # Create new pixmap cache for the wheel at current size and angle
            self._cached_wheel = QPixmap(width, height)
            self._cached_wheel.fill(Qt.transparent)

            # Create a painter for the cached wheel
            cache_painter = QPainter(self._cached_wheel)
            cache_painter.setRenderHint(QPainter.Antialiasing)

            # Draw the wheel on the cached pixmap
            self._draw_wheel(cache_painter, width, height, center_x, center_y)

            # End painting on the cache
            cache_painter.end()

        # Draw the cached wheel to the widget
        painter.drawPixmap(0, 0, self._cached_wheel)

        # Draw the steering angle indicator and bar - always draw these directly
        self._draw_angle_indicator(painter, width, height, center_x, center_y)

    def _draw_wheel(self, painter, width, height, center_x, center_y):
        """Draw the steering wheel on the given painter."""
        wheel_radius = min(width, height) / 2 * 0.85  # 85% of the available space

        # Save the painter state to restore later
        painter.save()

        # Set up transformation for wheel rotation
        painter.translate(center_x, center_y)
        painter.rotate(-self.steering_angle * 180 / math.pi)  # Convert to degrees for rotate()

        # Draw steering wheel outer rim
        pen_width = max(2, min(5, wheel_radius / 20))
        painter.setPen(QPen(self.wheel_rim_color, pen_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), wheel_radius, wheel_radius)

        # Draw wheel spokes
        spoke_width = max(2, min(4, wheel_radius / 30))
        painter.setPen(QPen(self.wheel_rim_color, spoke_width))

        # Cross spokes
        inner_radius = wheel_radius * 0.2  # Small central hub

        # Horizontal spoke
        painter.drawLine(int(-wheel_radius), 0, int(-inner_radius), 0)
        painter.drawLine(int(inner_radius), 0, int(wheel_radius), 0)

        # Vertical spoke
        painter.drawLine(0, int(-wheel_radius), 0, int(-inner_radius))
        painter.drawLine(0, int(inner_radius), 0, int(wheel_radius))

        # Diagonal spokes
        angle = math.pi / 4  # 45 degrees
        x1 = wheel_radius * math.cos(angle)
        y1 = wheel_radius * math.sin(angle)
        x2 = inner_radius * math.cos(angle)
        y2 = inner_radius * math.sin(angle)

        # Draw 4 diagonal spokes
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        painter.drawLine(int(-x1), int(y1), int(-x2), int(y2))
        painter.drawLine(int(x1), int(-y1), int(x2), int(-y2))
        painter.drawLine(int(-x1), int(-y1), int(-x2), int(-y2))

        # Draw central hub
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.wheel_color))
        painter.drawEllipse(QPointF(0, 0), inner_radius, inner_radius)

        # Draw center marker
        painter.setPen(QPen(self.wheel_marker_color, spoke_width))
        marker_size = inner_radius * 0.6
        painter.drawLine(0, int(-marker_size), 0, int(marker_size))

        # Restore painter state
        painter.restore()

    def _draw_angle_indicator(self, painter, width, height, center_x, center_y):
        """Draw the angle indicator and steering bar."""
        wheel_radius = min(width, height) / 2 * 0.85

        # Draw steering angle indicator outside the wheel
        angle_text = f"{(self.steering_angle * 180 / math.pi):.1f}°"
        painter.setPen(QPen(self.text_color))
        painter.setFont(QFont("Arial", 10))

        # Position text below the wheel
        text_y = center_y + wheel_radius + 20
        painter.drawText(0, int(text_y), width, 20, Qt.AlignCenter, angle_text)

        # Draw title
        title_font = painter.font()
        title_font.setPointSize(12)
        painter.setFont(title_font)
        painter.drawText(0, 15, width, 20, Qt.AlignCenter, self.title)

        # Draw steering angle bar at the bottom
        bar_width = width * 0.8
        bar_height = max(8, min(12, height / 20))
        bar_x = (width - bar_width) / 2
        bar_y = height - bar_height - 10

        # Draw the bar background
        painter.setPen(QPen(QColor(60, 60, 60)))
        painter.setBrush(QBrush(QColor(30, 30, 30)))
        painter.drawRect(int(bar_x), int(bar_y), int(bar_width), int(bar_height))

        # Draw the center line
        center_line_x = bar_x + bar_width / 2
        painter.setPen(QPen(QColor(150, 150, 150)))
        painter.drawLine(int(center_line_x), int(bar_y - 3), int(center_line_x), int(bar_y + bar_height + 3))

        # Draw the current position indicator
        # Apply a visualization scaling factor to make the bar more responsive
        # This makes the bar show more reasonable deflection for typical steering inputs
        # Most racing games only use a fraction of the wheel's physical rotation range
        visualization_scale = 0.4  # This means full bar deflection at 40% of max rotation

        # Map the range [-max_rotation*visualization_scale, +max_rotation*visualization_scale] to [0, 1]
        # This provides better visual feedback for actual in-game steering
        if self.max_rotation > 0:
            scaled_rotation = self.max_rotation * visualization_scale
            true_normalized = (self.steering_angle / scaled_rotation + 1.0) / 2.0
            # Clamp to ensure the bar stays within bounds
            true_normalized = max(0.0, min(1.0, true_normalized))
        else:
            true_normalized = 0.5  # Center if max_rotation is zero

        position = bar_x + bar_width * true_normalized

        # Use different colors for left and right
        if self.steering_angle < 0:
            indicator_color = QColor(0, 150, 255)  # Blue for left turns
        else:
            indicator_color = QColor(255, 100, 0)  # Orange for right turns

        indicator_width = bar_width / 10
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(indicator_color))
        painter.drawRect(int(center_line_x), int(bar_y), int((position - center_line_x)), int(bar_height))


# Import the required classes here
import math


class InputTraceWidget(QWidget):
    """Widget to display a history of driver inputs as a small graph."""

    # Add a signal for safer threaded updates
    data_updated = pyqtSignal()

    def __init__(self, parent=None, max_points=100):
        """Initialize the input trace widget."""
        super().__init__(parent)

        # Settings
        self.max_points = max_points
        self.throttle_color = QColor("#4CAF50")  # Green
        self.brake_color = QColor("#FF5252")  # Red
        self.clutch_color = QColor("#FFC107")  # Amber
        self.background_color = QColor(30, 30, 30, 180)
        self.grid_color = QColor(70, 70, 70, 100)

        # Initialize data arrays
        self.throttle_data = np.zeros(max_points, dtype=float)
        self.brake_data = np.zeros(max_points, dtype=float)
        self.clutch_data = np.zeros(max_points, dtype=float)

        # Set minimum size
        self.setMinimumSize(300, 120)

        # Visual settings
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, self.background_color)
        self.setPalette(palette)

        # Use a mutex to protect the data during updates
        self._data_mutex = threading.Lock()

        # Connect our signal to trigger update
        self.data_updated.connect(self.update)

    def add_data_point(self, throttle, brake, clutch):
        """Add a new data point to the trace display.

        Args:
            throttle: Throttle input (0-1)
            brake: Brake input (0-1)
            clutch: Clutch input (0-1)
        """
        # Lock the data during update
        with self._data_mutex:
            # Shift arrays and add new values
            self.throttle_data = np.roll(self.throttle_data, -1)
            self.brake_data = np.roll(self.brake_data, -1)
            self.clutch_data = np.roll(self.clutch_data, -1)

            self.throttle_data[-1] = throttle
            self.brake_data[-1] = brake
            # Reverse clutch value to make it display in the same direction as throttle and brake
            self.clutch_data[-1] = 1.0 - clutch  # Reverse the clutch value

        # Emit signal to trigger a repaint on the main thread
        self.data_updated.emit()

    def clear_data(self):
        """Clear all data from the trace display."""
        with self._data_mutex:
            self.throttle_data[:] = 0
            self.brake_data[:] = 0
            self.clutch_data[:] = 0

        # Emit signal to trigger a repaint on the main thread
        self.data_updated.emit()

    def paintEvent(self, event):
        """Paint the input trace visualization."""
        # Create a copy of the data to avoid threading issues during paint
        with self._data_mutex:
            throttle_data = self.throttle_data.copy()
            brake_data = self.brake_data.copy()
            clutch_data = self.clutch_data.copy()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        # Calculate drawing area - increase padding for better spacing
        padding = 20
        left_padding = 35  # More space for y-axis labels
        right_padding = 15
        top_padding = 20  # More space for title
        bottom_padding = 25  # More space for x-axis label

        graph_width = width - (left_padding + right_padding)
        graph_height = height - (top_padding + bottom_padding)

        # Draw background (already handled by palette)

        # Draw title text at top with better positioning
        title_font = painter.font()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QPen(Qt.white))
        painter.drawText(int(width / 2 - 75), 15, "Input Trace")

        # Draw axis labels
        axis_font = painter.font()
        axis_font.setPointSize(8)
        painter.setFont(axis_font)

        # Y-axis labels with better positioning
        painter.drawText(5, top_padding - 5, "100%")
        painter.drawText(5, int(top_padding + graph_height / 2), "50%")
        painter.drawText(5, top_padding + graph_height + 5, "0%")

        # X-axis label - Time with better positioning
        painter.drawText(int(width / 2 - 15), height - 5, "Time →")

        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1, Qt.DashLine))

        # Horizontal grid lines at 25%, 50%, 75%
        for y_pct in [0.25, 0.5, 0.75]:
            y = top_padding + (1.0 - y_pct) * graph_height
            painter.drawLine(left_padding, int(y), left_padding + graph_width, int(y))

        # Vertical grid lines every 25% of width
        for x_pct in [0.25, 0.5, 0.75]:
            x = left_padding + x_pct * graph_width
            painter.drawLine(int(x), top_padding, int(x), top_padding + graph_height)

        # Draw border
        painter.setPen(QPen(self.grid_color.lighter(120), 1))
        painter.drawRect(left_padding, top_padding, graph_width, graph_height)

        # Draw data traces if we have any data
        if np.max(throttle_data) > 0 or np.max(brake_data) > 0 or np.max(clutch_data) > 0:
            # Calculate points for each data set
            data_len = len(throttle_data)
            x_step = graph_width / (data_len - 1) if data_len > 1 else graph_width

            # Draw throttle trace
            throttle_pen = QPen(self.throttle_color, 2)
            painter.setPen(throttle_pen)

            for i in range(data_len - 1):
                x1 = left_padding + i * x_step
                y1 = top_padding + graph_height - (throttle_data[i] * graph_height)
                x2 = left_padding + (i + 1) * x_step
                y2 = top_padding + graph_height - (throttle_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Draw brake trace
            brake_pen = QPen(self.brake_color, 2)
            painter.setPen(brake_pen)

            for i in range(data_len - 1):
                x1 = left_padding + i * x_step
                y1 = top_padding + graph_height - (brake_data[i] * graph_height)
                x2 = left_padding + (i + 1) * x_step
                y2 = top_padding + graph_height - (brake_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Draw clutch trace
            clutch_pen = QPen(self.clutch_color, 2)
            painter.setPen(clutch_pen)

            for i in range(data_len - 1):
                x1 = left_padding + i * x_step
                y1 = top_padding + graph_height - (clutch_data[i] * graph_height)
                x2 = left_padding + (i + 1) * x_step
                y2 = top_padding + graph_height - (clutch_data[i + 1] * graph_height)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw legend with better positioning and spacing
        legend_width = 80
        legend_padding = 10
        legend_height = 15
        legend_spacing = 15
        # Move legend to top-left corner instead of right side
        legend_x = left_padding + 10
        legend_y = top_padding + 10

        # Draw legend background for better visibility
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(30, 30, 30, 180)))
        painter.drawRect(legend_x - 5, legend_y - 5, legend_width, 3 * legend_height + 2 * legend_spacing + 10)

        # Throttle
        painter.setPen(self.throttle_color)
        painter.drawLine(legend_x, legend_y, legend_x + 15, legend_y)
        painter.drawText(legend_x + 20, legend_y + 5, "Throttle")

        # Brake
        painter.setPen(self.brake_color)
        painter.drawLine(
            legend_x,
            legend_y + legend_height + legend_spacing,
            legend_x + 15,
            legend_y + legend_height + legend_spacing,
        )
        painter.drawText(legend_x + 20, legend_y + legend_height + legend_spacing + 5, "Brake")

        # Clutch
        painter.setPen(self.clutch_color)
        painter.drawLine(
            legend_x,
            legend_y + 2 * (legend_height + legend_spacing),
            legend_x + 15,
            legend_y + 2 * (legend_height + legend_spacing),
        )
        painter.drawText(legend_x + 20, legend_y + 2 * (legend_height + legend_spacing) + 5, "Clutch")


# --- New Widget for Speed Trace Graph ---
class SpeedTraceGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_data_left = []
        self.speed_data_right = []
        self.left_driver_color = QColor(255, 0, 0)
        self.right_driver_color = QColor(255, 215, 0)
        self.left_driver_name = "Driver 1"
        self.right_driver_name = "Driver 2"
        self.setMinimumHeight(200)
        self.setStyleSheet(
            """
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """
        )

    def set_data(self, speed_left, speed_right, left_color, right_color, left_name, right_name):
        self.speed_data_left = speed_left
        self.speed_data_right = speed_right
        self.left_driver_color = left_color
        self.right_driver_color = right_color
        self.left_driver_name = left_name
        self.right_driver_name = right_name
        self.update()  # Trigger repaint when data changes

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()

        # Define graph area (relative to this widget's coordinates)
        speed_top = 0
        speed_height = height
        speed_bottom = height

        # Draw background is handled by stylesheet

        # Add subtle grid pattern for F1 style
        painter.setPen(QPen(QColor(40, 40, 40, 180), 1))
        grid_spacing_h = width / 20 if width > 0 else 0
        for i in range(21):
            x = i * grid_spacing_h
            painter.drawLine(int(x), int(speed_top), int(x), int(speed_bottom))

        # Draw speed trace labels (every 50 km/h)
        max_speed = 350  # Default headroom
        # Safely calculate max_speed
        all_speeds = []
        if self.speed_data_left:
            all_speeds.extend(filter(lambda x: isinstance(x, (int, float)), self.speed_data_left))
        if self.speed_data_right:
            all_speeds.extend(filter(lambda x: isinstance(x, (int, float)), self.speed_data_right))
        if all_speeds:
            max_speed = max(max_speed, max(all_speeds) * 1.1)
        max_speed = math.ceil(max_speed / 50.0) * 50 if max_speed > 0 else 50

        painter.setPen(QPen(QColor(70, 70, 70)))
        painter.setFont(QFont("Arial", 8))
        if max_speed > 0:
            for speed in range(0, int(max_speed) + 50, 50):
                y = speed_bottom - (speed / max_speed) * speed_height
                painter.drawLine(0, int(y), width, int(y))
                painter.setPen(QPen(QColor(180, 180, 180)))
                painter.drawText(5, int(y - 2), f"{speed}")
                painter.setPen(QPen(QColor(70, 70, 70)))

        # Label the speed trace
        painter.setPen(QPen(QColor(220, 220, 220)))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(10, int(speed_top + 20), "SPEED (km/h)")

        # Draw segment labels for speed categories
        segment_labels = ["LOW SPEED", "MEDIUM SPEED", "HIGH SPEED", "HIGH SPEED", "MEDIUM SPEED", "LOW SPEED"]
        if width > 0 and len(segment_labels) > 0:
            segment_width = width / len(segment_labels)
            segment_colors = {
                "LOW SPEED": QColor(200, 40, 40, 20),
                "MEDIUM SPEED": QColor(200, 200, 40, 20),
                "HIGH SPEED": QColor(40, 200, 40, 20),
            }
            painter.setFont(QFont("Arial", 8))
            for i, label in enumerate(segment_labels):
                x = i * segment_width
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(segment_colors.get(label, QColor(0, 0, 0, 0))))
                painter.drawRect(int(x), int(speed_top), int(segment_width), int(speed_height))
                painter.setPen(QPen(QColor(180, 180, 180)))
                text_width = painter.fontMetrics().width(label)
                painter.drawText(int(x + (segment_width - text_width) / 2), int(speed_top + 15), label)
                if i > 0:
                    painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
                    painter.drawLine(int(i * segment_width), int(speed_top), int(i * segment_width), int(speed_bottom))

        # Draw speed traces with improved styling
        line_width = 3
        # Check if data exists and has enough points
        has_left_data = self.speed_data_left and len(self.speed_data_left) > 1
        has_right_data = self.speed_data_right and len(self.speed_data_right) > 1

        if not has_left_data or not has_right_data:
            painter.setPen(QPen(QColor(240, 240, 240)))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(QRectF(0, speed_top, width, speed_height), Qt.AlignCenter, "Speed Comparison Data Missing")
        else:
            # Draw left driver's speed trace
            if max_speed > 0:
                try:
                    points = []
                    x_step = width / (len(self.speed_data_left) - 1)
                    for i, speed in enumerate(self.speed_data_left):
                        # Ensure speed is a number before calculating y
                        if isinstance(speed, (int, float)):
                            y = speed_bottom - (speed / max_speed) * speed_height
                            points.append((i * x_step, y))
                        else:
                            logger.warning(f"Non-numeric speed value in left data at index {i}: {speed}")

                    shadow_pen = QPen(QColor(0, 0, 0, 150), line_width + 2)
                    painter.setPen(shadow_pen)
                    for i in range(len(points) - 1):
                        painter.drawLine(
                            int(points[i][0]), int(points[i][1]) + 2, int(points[i + 1][0]), int(points[i + 1][1]) + 2
                        )
                    left_color = QColor(self.left_driver_color)
                    left_color.setAlpha(255)
                    painter.setPen(QPen(left_color, line_width))
                    for i in range(len(points) - 1):
                        painter.drawLine(
                            int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1])
                        )
                except Exception as e:
                    logger.error(f"Error drawing left driver speed trace: {e}")

            # Draw right driver's speed trace
            if max_speed > 0:
                try:
                    points = []
                    x_step = width / (len(self.speed_data_right) - 1)
                    for i, speed in enumerate(self.speed_data_right):
                        # Ensure speed is a number before calculating y
                        if isinstance(speed, (int, float)):
                            y = speed_bottom - (speed / max_speed) * speed_height
                            points.append((i * x_step, y))
                        else:
                            logger.warning(f"Non-numeric speed value in right data at index {i}: {speed}")

                    shadow_pen = QPen(QColor(0, 0, 0, 150), line_width + 2)
                    painter.setPen(shadow_pen)
                    for i in range(len(points) - 1):
                        painter.drawLine(
                            int(points[i][0]), int(points[i][1]) + 2, int(points[i + 1][0]), int(points[i + 1][1]) + 2
                        )
                    right_color = QColor(self.right_driver_color)
                    right_color.setAlpha(255)
                    painter.setPen(QPen(right_color, line_width))
                    for i in range(len(points) - 1):
                        painter.drawLine(
                            int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1])
                        )
                except Exception as e:
                    logger.error(f"Error drawing right driver speed trace: {e}")

            # Add driver color indicators
            try:
                legend_y = speed_top + 20
                legend_width = 30
                legend_height = 2
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.left_driver_color))
                painter.drawRect(int(width - 120), int(legend_y), legend_width, legend_height)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawText(int(width - 120 + legend_width + 5), int(legend_y + 4), self.left_driver_name)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(self.right_driver_color))
                painter.drawRect(int(width - 120), int(legend_y + 15), legend_width, legend_height)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawText(int(width - 120 + legend_width + 5), int(legend_y + 19), self.right_driver_name)
            except Exception as e:
                logger.error(f"Error drawing speed trace legend: {e}")


# --- End New Widget ---


class TelemetryComparisonWidget(QWidget):
    """Widget to display F1-style telemetry comparison between two laps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.left_driver = {}
        self.right_driver = {}
        self.track_map_points = []
        self.track_turns = {}
        self.track_sectors = {}
        self.setup_ui()

    def setup_ui(self):
        """Set up the comparison layout UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Top section with track map
        top_section = QHBoxLayout()

        # Track map widget in center
        track_map_widget = QFrame()
        track_map_widget.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        track_map_widget.setStyleSheet(
            """
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """
        )

        # Add track map to top layout - now it takes full width
        top_section.addWidget(track_map_widget, 1)

        # Add top section to main layout
        main_layout.addLayout(top_section)

    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if time_in_seconds is None:
            return "--:--.---"
        minutes = int(time_in_seconds // 60)
        seconds = time_in_seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"

    def get_track_length(self):
        """Get the current track length in meters."""
        # Try to get track length from session info
        if hasattr(self, "session_info") and self.session_info:
            track_length = self.session_info.get("track_length", 0)
            if track_length > 0:
                return track_length

        # Fall back to checking context of currently loaded data
        if hasattr(self, "throttle_graph") and hasattr(self.throttle_graph, "track_length"):
            graph_track_length = self.throttle_graph.track_length
            if graph_track_length > 0:
                return graph_track_length

        # Default value if we can't find track length anywhere
        return 1000  # 1000 meters default

    def set_driver_data(self, is_left_driver, data):
        """Set driver data and update display.

        Args:
            is_left_driver: True if setting left driver data, False for right
            data: Dictionary containing driver data
        """
        if is_left_driver:
            self.left_driver = data
        else:
            self.right_driver = data
        # No longer need to update driver display

    def update_driver_display(self, is_left_driver):
        """Update the display for a driver's data.

        Args:
            is_left_driver: True to update left driver display, False for right
        """
        # Method kept for backward compatibility but no longer updates UI
        pass

    def set_track_data(self, track_map_points, turn_data, sector_data):
        """Set the track map data.

        Args:
            track_map_points: List of (x, y) points defining the track outline
            turn_data: Dictionary mapping turn numbers to track positions
            sector_data: Dictionary defining speed sectors
        """
        self.track_map_points = track_map_points
        self.track_turns = turn_data
        self.track_sectors = sector_data
        self.update()

    def paintEvent(self, event):
        """Paint the comparison widget with real data."""
        try:
            super().paintEvent(event)

            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Get widget dimensions
            width = self.width()
            height = self.height()

            # Draw track map in the center top area
            track_map_top = height * 0.05
            track_map_height = height * 0.45
            track_map_bottom = track_map_top + track_map_height
            track_map_left = width * 0.1  # Adjusted to use more width
            track_map_width = width * 0.8  # Increased width for track map
            track_map_right = track_map_left + track_map_width

            # Background for track map
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(25, 25, 25)))
            painter.drawRect(int(track_map_left), int(track_map_top), int(track_map_width), int(track_map_height))

            # Draw track outline if we have points
            if self.track_map_points:
                # Calculate scale and offset to fit track in view
                x_coords = [p[0] for p in self.track_map_points]
                y_coords = [p[1] for p in self.track_map_points]

                track_width = max(x_coords) - min(x_coords)
                track_height = max(y_coords) - min(y_coords)

                # Scale to fit with padding
                padding = 20
                scale_x = (track_map_width - padding * 2) / track_width if track_width > 0 else 1
                scale_y = (track_map_height - padding * 2) / track_height if track_height > 0 else 1
                scale = min(scale_x, scale_y)

                # Center the track
                offset_x = track_map_left + track_map_width / 2 - (max(x_coords) + min(x_coords)) * scale / 2
                offset_y = track_map_top + track_map_height / 2 - (max(y_coords) + min(y_coords)) * scale / 2

                # Draw track outline
                track_path = QPainterPath()
                first_point = True
                for x, y in self.track_map_points:
                    screen_x = offset_x + x * scale
                    screen_y = offset_y + y * scale
                    if first_point:
                        track_path.moveTo(screen_x, screen_y)
                        first_point = False
                    else:
                        track_path.lineTo(screen_x, screen_y)
                track_path.closeSubpath()

                # Draw track with shadow effect
                shadow_color = QColor(0, 0, 0, 100)
                shadow_offset = 3
                painter.setPen(QPen(shadow_color, 3))
                painter.drawPath(track_path.translated(shadow_offset, shadow_offset))

                # Draw actual track
                painter.setPen(QPen(QColor(200, 200, 200), 2))
                painter.drawPath(track_path)

                # Draw turn markers and numbers
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.setFont(QFont("Arial", 8))

                for turn_num, turn_data in self.track_turns.items():
                    if "position" in turn_data:
                        x, y = turn_data["position"]
                        screen_x = offset_x + x * scale
                        screen_y = offset_y + y * scale

                        # Draw turn marker
                        painter.setBrush(QBrush(QColor(200, 200, 200)))
                        painter.drawEllipse(int(screen_x - 3), int(screen_y - 3), 6, 6)

                        # Draw turn number
                        painter.drawText(int(screen_x + 5), int(screen_y + 3), str(turn_num))

        except Exception as e:
            # Log error but don't crash the application
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error in TelemetryComparisonWidget.paintEvent: {e}")
            import traceback

            logger.error(traceback.format_exc())


# --- New Widget for Delta Graph ---
class DeltaGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.delta_data = []
        self.setMinimumHeight(50)
        self.setStyleSheet(
            """
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
        """
        )

    def set_data(self, delta_data):
        # Ensure delta_data is a list of numbers, handle potential None or non-numeric values
        if isinstance(delta_data, list):
            self.delta_data = [d for d in delta_data if isinstance(d, (int, float))]
        else:
            self.delta_data = []
            logger.warning(f"Received non-list delta_data: {type(delta_data)}")
        self.update()  # Trigger repaint when data changes

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()

        # Define graph area (relative to this widget's coordinates)
        delta_top = 0
        delta_height = height
        delta_bottom = height

        # Draw background is handled by stylesheet

        # Add subtle grid pattern for delta graph too
        painter.setPen(QPen(QColor(40, 40, 40, 180), 1))
        grid_spacing_h = width / 20 if width > 0 else 0
        for i in range(21):
            x = i * grid_spacing_h
            painter.drawLine(int(x), int(delta_top), int(x), int(delta_bottom))

        # Draw delta graph with F1-style enhancements
        line_width = 3
        # Check if delta_data exists and has enough points
        if not self.delta_data or len(self.delta_data) <= 1:
            painter.setPen(QPen(QColor(240, 240, 240)))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(QRectF(0, delta_top, width, delta_height), Qt.AlignCenter, "Delta Time Data Missing")
        else:
            # Find max delta for scaling
            max_delta = 0.5  # Default scale
            try:
                min_val = min(self.delta_data)
                max_val = max(self.delta_data)
                max_abs_delta = max(abs(min_val), abs(max_val))
                max_delta = max(max_abs_delta, 0.5)
                max_delta = math.ceil(max_delta / 0.5) * 0.5
            except (ValueError, TypeError):
                logger.warning(f"Could not calculate max delta from data: {self.delta_data[:10]}...")
                pass  # Keep default max_delta

            # Draw horizontal bands
            band_colors = [QColor(0, 150, 0, 15), QColor(150, 0, 0, 15)]  # Green band for faster  # Red band for slower
            painter.setPen(Qt.NoPen)
            zero_y = delta_top + delta_height / 2
            painter.setBrush(band_colors[0])
            painter.drawRect(0, int(zero_y), int(width), int(delta_height / 2))
            painter.setBrush(band_colors[1])
            painter.drawRect(0, int(delta_top), int(width), int(delta_height / 2))

            # Draw horizontal line at zero
            painter.setPen(QPen(QColor(220, 220, 220), 1))
            painter.drawLine(0, int(zero_y), width, int(zero_y))

            # Labels
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(10, int(delta_top + 15), "DELTA (seconds)")
            painter.setFont(QFont("Arial", 8))
            painter.setPen(QPen(QColor(0, 200, 0)))
            painter.drawText(int(width - 70), int(delta_bottom - 5), "FASTER")
            painter.setPen(QPen(QColor(200, 0, 0)))
            painter.drawText(int(width - 70), int(delta_top + 15), "SLOWER")
            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.drawText(5, int(delta_top + 15), f"+{max_delta:.2f}")
            painter.drawText(5, int(delta_bottom - 5), f"-{max_delta:.2f}")
            painter.drawText(5, int(zero_y + 4), "0.00")

            # Horizontal grid lines
            painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))
            if max_delta > 0:
                step = max_delta / 2
                for i in range(1, 3):
                    y_pos = zero_y - (i * step / max_delta) * (delta_height / 2)
                    painter.drawLine(0, int(y_pos), width, int(y_pos))
                    y_neg = zero_y + (i * step / max_delta) * (delta_height / 2)
                    painter.drawLine(0, int(y_neg), width, int(y_neg))

            # Draw the delta line segments
            if width > 0 and max_delta > 0:
                x_step = width / (len(self.delta_data) - 1) if len(self.delta_data) > 1 else 0
                current_segment = []
                last_state = None

                for i, delta in enumerate(self.delta_data):
                    x = i * x_step
                    # Calculate y-position: zero in the middle, negative (faster) below, positive (slower) above
                    y = zero_y - (delta / max_delta) * (delta_height / 2)

                    # Determine point state for coloring
                    state = "zero" if abs(delta) < 0.01 else "positive" if delta > 0 else "negative"

                    # If state changes or first point, start a new segment
                    if state != last_state or i == 0:
                        if current_segment:
                            # Draw the segment with a color based on its state
                            if last_state == "positive":
                                painter.setPen(QPen(QColor(200, 50, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                            elif last_state == "negative":
                                painter.setPen(QPen(QColor(50, 200, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                            else:
                                painter.setPen(QPen(QColor(200, 200, 200), line_width, Qt.SolidLine, Qt.RoundCap))

                            # Draw lines between points in the segment
                            for j in range(len(current_segment) - 1):
                                p1, p2 = current_segment[j], current_segment[j + 1]
                                painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

                        # Start new segment
                        current_segment = [(x, y)]
                        last_state = state
                    else:
                        # Continue the segment
                        current_segment.append((x, y))

                # Draw the final segment if any
                if current_segment:
                    if last_state == "positive":
                        painter.setPen(QPen(QColor(200, 50, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                    elif last_state == "negative":
                        painter.setPen(QPen(QColor(50, 200, 50), line_width, Qt.SolidLine, Qt.RoundCap))
                    else:
                        painter.setPen(QPen(QColor(200, 200, 200), line_width, Qt.SolidLine, Qt.RoundCap))

                    for j in range(len(current_segment) - 1):
                        p1, p2 = current_segment[j], current_segment[j + 1]
                        painter.drawLine(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))

    def load_demo_data(self):
        """Load demo telemetry data for visualization testing."""
        try:
            import random
            import math

            logger.info("Loading F1-style demo visualization data")

            # Set driver information
            left_driver_info = {
                "name": "CHARLES",
                "lastname": "LECLERC",
                "team": "FERRARI",
                "position": "1",
                "lap_time": 83.456,
                "gap": -0.321,
                "full_throttle": 81,
                "heavy_braking": 5,
                "cornering": 14,
                "color": QColor(255, 0, 0),
            }
            right_driver_info = {
                "name": "CARLOS",
                "lastname": "SAINZ",
                "team": "FERRARI",
                "position": "2",
                "lap_time": 83.777,
                "gap": 0.321,
                "full_throttle": 79,
                "heavy_braking": 6,
                "cornering": 15,
                "color": QColor(255, 215, 0),
            }

            # Update the driver displays
            self.set_driver_data(True, left_driver_info)
            self.set_driver_data(False, right_driver_info)

            # Generate track data
            track_points = []
            num_points = 100
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                x = 200 * math.cos(angle) * (1 + 0.3 * math.cos(2 * angle))
                y = 150 * math.sin(angle) * (1 + 0.1 * math.sin(2 * angle))
                track_points.append((x, y))

            # Generate turn data
            turn_data = {}
            for turn in range(1, 12):
                idx = (turn - 1) * (num_points // 11)
                turn_data[turn] = {"position": track_points[idx], "name": f"Turn {turn}"}

            # Set track data
            sector_data = {}  # Would populate in a real implementation
            self.set_track_data(track_points, turn_data, sector_data)

            # Generate speed data
            base_profile = []
            num_speed_points = 200
            for i in range(num_speed_points):
                angle = i / num_speed_points * 2 * math.pi
                speed = 250 + 70 * math.sin(angle) - 50 * math.sin(2 * angle)
                speed += random.uniform(-5, 5)
                speed = max(speed, 80)
                base_profile.append(speed)

            speed_data_left = base_profile[:]
            speed_data_right = [
                s + math.sin(i / num_speed_points * 2 * math.pi * 3) * 10 for i, s in enumerate(base_profile)
            ]

            # Generate delta data
            delta_data = [0]
            if speed_data_left and speed_data_right:
                min_len = min(len(speed_data_left), len(speed_data_right))
                for i in range(1, min_len):
                    # Avoid division by zero for delta calculation
                    speed_l = max(1, speed_data_left[i])
                    speed_r = max(1, speed_data_right[i])
                    segment_time_left = 1 / speed_l
                    segment_time_right = 1 / speed_r
                    segment_delta = segment_time_right - segment_time_left
                    delta_data.append(delta_data[-1] + segment_delta)

                # Scale delta
                max_abs_delta = max(abs(min(delta_data)), abs(max(delta_data)))
                if max_abs_delta > 0:
                    scale = 0.5 / max_abs_delta
                    delta_data = [d * scale for d in delta_data]

            # Pass data to the child widgets
            if hasattr(self, "speed_trace_widget") and self.speed_trace_widget:
                self.speed_trace_widget.set_data(
                    speed_data_left,
                    speed_data_right,
                    left_driver_info["color"],
                    right_driver_info["color"],
                    left_driver_info["name"],
                    right_driver_info["name"],
                )

            if hasattr(self, "delta_widget") and self.delta_widget:
                self.delta_widget.set_data(delta_data)

            # Update display
            self.update()
            QApplication.processEvents()

            logger.info("F1-style demo visualization data loaded")

        except Exception as e:
            logger.error(f"Error in load_demo_data: {e}")
            import traceback

            logger.error(traceback.format_exc())


# --- End New Widget ---


class VideosTab(QWidget):
    """Tab for displaying video courses in a Kajabi-like interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_course = None
        self.current_video = None
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create stacked widget to switch between course browser and course view
        self.stacked_widget = QStackedWidget()
        
        # Create course browser
        self.course_browser = self.create_course_browser()
        self.stacked_widget.addWidget(self.course_browser)
        
        # Create course view
        self.course_view = self.create_course_view()
        self.stacked_widget.addWidget(self.course_view)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Load sample courses
        self.load_sample_courses()

    def create_course_browser(self):
        """Create the main course browsing interface."""
        browser = QWidget()
        layout = QVBoxLayout(browser)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("RaceFlix - Video Coaching")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #e67e22;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search courses...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 14px;
                min-width: 250px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_courses)
        header_layout.addWidget(self.search_bar)
        
        layout.addLayout(header_layout)

        # Filter tabs
        filter_layout = QHBoxLayout()
        
        self.filter_buttons = {}
        filters = ["All", "Beginner", "Intermediate", "Advanced", "New"]
        
        for filter_name in filters:
            btn = QPushButton(filter_name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: #ccc;
                    font-weight: bold;
                    margin-right: 5px;
                }
                QPushButton:checked {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QPushButton:checked:hover {
                    background-color: #2980b9;
                }
            """)
            btn.clicked.connect(lambda checked, f=filter_name: self.apply_filter(f))
            self.filter_buttons[filter_name] = btn
            filter_layout.addWidget(btn)
        
        # Set "All" as default
        self.filter_buttons["All"].setChecked(True)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Course grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #333;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #666;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #777;
            }
        """)

        self.course_grid_widget = QWidget()
        self.course_grid_layout = QGridLayout(self.course_grid_widget)
        self.course_grid_layout.setSpacing(20)
        self.course_grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area.setWidget(self.course_grid_widget)
        layout.addWidget(scroll_area)

        return browser

    def create_course_view(self):
        """Create the detailed course view with video player."""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with back button
        header = QWidget()
        header.setStyleSheet("background-color: #2c3e50; padding: 15px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        self.back_button = QPushButton("← Back to Courses")
        self.back_button.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #3498db;
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                color: #2980b9;
                text-decoration: underline;
            }
        """)
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.clicked.connect(self.show_course_browser)
        header_layout.addWidget(self.back_button)
        
        header_layout.addStretch()
        
        # Course progress
        self.progress_label = QLabel("Progress: 0/0 completed")
        self.progress_label.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        header_layout.addWidget(self.progress_label)
        
        layout.addWidget(header)

        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Video player and details
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        # Video player
        self.video_player = QWebEngineView()
        self.video_player.setMinimumHeight(400)
        self.video_player.setStyleSheet("""
            QWebEngineView {
                background-color: #000;
                border-radius: 8px;
                border: 2px solid #34495e;
            }
        """)
        
        # Load placeholder
        self.load_video_placeholder()
        left_layout.addWidget(self.video_player)

        # Video info
        video_info_widget = QWidget()
        video_info_layout = QVBoxLayout(video_info_widget)
        video_info_layout.setContentsMargins(0, 0, 0, 0)
        video_info_layout.setSpacing(10)

        self.video_title = QLabel("Select a lesson to start")
        self.video_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 5px;
        """)
        video_info_layout.addWidget(self.video_title)

        self.video_description = QLabel("")
        self.video_description.setStyleSheet("""
            color: #bdc3c7;
            font-size: 14px;
            line-height: 1.4;
        """)
        self.video_description.setWordWrap(True)
        video_info_layout.addWidget(self.video_description)

        # Video controls
        controls_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setStyleSheet(self.get_button_style())
        self.prev_button.clicked.connect(self.previous_video)
        controls_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next →")
        self.next_button.setStyleSheet(self.get_button_style())
        self.next_button.clicked.connect(self.next_video)
        controls_layout.addWidget(self.next_button)
        
        controls_layout.addStretch()
        
        self.mark_complete_button = QPushButton("Mark as Complete")
        self.mark_complete_button.setStyleSheet(self.get_button_style("#27ae60", "#229954"))
        self.mark_complete_button.clicked.connect(self.mark_video_complete)
        controls_layout.addWidget(self.mark_complete_button)
        
        video_info_layout.addLayout(controls_layout)
        left_layout.addWidget(video_info_widget)

        # Comments section
        comments_widget = self.create_comments_section()
        left_layout.addWidget(comments_widget)

        content_splitter.addWidget(left_panel)

        # Right side - Course modules
        right_panel = self.create_course_modules_panel()
        content_splitter.addWidget(right_panel)

        # Set splitter proportions (70% video, 30% modules)
        content_splitter.setSizes([700, 300])
        
        layout.addWidget(content_splitter)

        return view

    def create_course_modules_panel(self):
        """Create the course modules panel."""
        panel = QWidget()
        panel.setStyleSheet("background-color: #34495e;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Course info
        self.course_title_label = QLabel("Course Title")
        self.course_title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.course_title_label)

        self.course_instructor = QLabel("Instructor: ")
        self.course_instructor.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        layout.addWidget(self.course_instructor)

        # Course stats
        stats_layout = QHBoxLayout()
        
        self.course_level = QLabel("Level: ")
        self.course_level.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        stats_layout.addWidget(self.course_level)
        
        self.course_duration = QLabel("Duration: ")
        self.course_duration.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        stats_layout.addWidget(self.course_duration)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Modules list
        modules_label = QLabel("Course Modules")
        modules_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            margin-top: 15px;
            margin-bottom: 10px;
        """)
        layout.addWidget(modules_label)

        # Modules scroll area
        modules_scroll = QScrollArea()
        modules_scroll.setWidgetResizable(True)
        modules_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2c3e50;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #7f8c8d;
                border-radius: 4px;
            }
        """)

        self.modules_widget = QWidget()
        self.modules_layout = QVBoxLayout(self.modules_widget)
        self.modules_layout.setContentsMargins(0, 0, 0, 0)
        self.modules_layout.setSpacing(8)
        
        modules_scroll.setWidget(self.modules_widget)
        layout.addWidget(modules_scroll)

        return panel

    def create_comments_section(self):
        """Create the comments section."""
        comments_widget = QWidget()
        comments_layout = QVBoxLayout(comments_widget)
        comments_layout.setContentsMargins(0, 0, 0, 0)
        comments_layout.setSpacing(15)

        # Comments header
        comments_header = QLabel("Discussion")
        comments_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            margin-top: 20px;
            margin-bottom: 10px;
        """)
        comments_layout.addWidget(comments_header)

        # Add comment form
        comment_form = QWidget()
        comment_form_layout = QVBoxLayout(comment_form)
        comment_form_layout.setContentsMargins(0, 0, 0, 0)
        comment_form_layout.setSpacing(10)

        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText("Share your thoughts or ask a question...")
        self.comment_input.setMaximumHeight(80)
        self.comment_input.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        comment_form_layout.addWidget(self.comment_input)

        comment_buttons_layout = QHBoxLayout()
        comment_buttons_layout.addStretch()
        
        self.post_comment_button = QPushButton("Post Comment")
        self.post_comment_button.setStyleSheet(self.get_button_style("#3498db", "#2980b9"))
        self.post_comment_button.clicked.connect(self.post_comment)
        comment_buttons_layout.addWidget(self.post_comment_button)
        
        comment_form_layout.addLayout(comment_buttons_layout)
        comments_layout.addWidget(comment_form)

        # Comments list
        comments_scroll = QScrollArea()
        comments_scroll.setWidgetResizable(True)
        comments_scroll.setMaximumHeight(300)
        comments_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #34495e;
                border-radius: 6px;
                background-color: #2c3e50;
            }
            QScrollBar:vertical {
                background: #34495e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #7f8c8d;
                border-radius: 4px;
            }
        """)

        self.comments_widget = QWidget()
        self.comments_layout = QVBoxLayout(self.comments_widget)
        self.comments_layout.setContentsMargins(10, 10, 10, 10)
        self.comments_layout.setSpacing(10)
        self.comments_layout.addStretch()
        
        comments_scroll.setWidget(self.comments_widget)
        comments_layout.addWidget(comments_scroll)

        return comments_widget

    def get_button_style(self, bg_color="#3498db", hover_color="#2980b9"):
        """Get consistent button styling."""
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #7f8c8d;
                color: #bdc3c7;
            }}
        """

    def load_sample_courses(self):
        """Load sample course data."""
        self.courses = [
            {
                "id": 1,
                "title": "Racing Fundamentals",
                "description": "Master the basics of racing with proper racing lines, braking techniques, and throttle control.",
                "instructor": "Alex Johnson",
                "level": "beginner",
                "duration": "2h 30m",
                "lessons": 8,
                "modules": [
                    {
                        "id": 1,
                        "title": "Introduction to Racing Lines",
                        "description": "Learn the optimal path around a race track for maximum speed and efficiency.",
                        "duration": "15:30",
                        "video_id": "dQw4w9WgXcQ",  # Sample YouTube ID
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Braking Techniques",
                        "description": "Master threshold braking and trail braking for better corner entry.",
                        "duration": "18:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 3,
                        "title": "Throttle Control",
                        "description": "Smooth throttle application for optimal traction and speed.",
                        "duration": "20:15",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 2,
                "title": "Advanced Cornering",
                "description": "Take your cornering to the next level with advanced techniques and car control.",
                "instructor": "Sarah Martinez",
                "level": "intermediate",
                "duration": "3h 15m",
                "lessons": 12,
                "modules": [
                    {
                        "id": 1,
                        "title": "Trail Braking Mastery",
                        "description": "Advanced trail braking techniques for faster corner entry.",
                        "duration": "22:30",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Oversteer and Understeer",
                        "description": "Understanding and correcting handling characteristics.",
                        "duration": "25:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 3,
                        "title": "Weight Transfer Dynamics",
                        "description": "Master how weight transfer affects your car's handling.",
                        "duration": "19:20",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 3,
                "title": "Race Strategy & Mental Game",
                "description": "Develop winning strategies and mental toughness for competitive racing.",
                "instructor": "Mike Thompson",
                "level": "advanced",
                "duration": "4h 20m",
                "lessons": 15,
                "modules": [
                    {
                        "id": 1,
                        "title": "Race Start Strategies",
                        "description": "Maximize your race starts and first lap positioning.",
                        "duration": "28:15",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Overtaking Techniques",
                        "description": "Safe and effective overtaking in different scenarios.",
                        "duration": "24:30",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 4,
                "title": "Car Setup Fundamentals",
                "description": "Learn how to tune your car for optimal performance on any track.",
                "instructor": "David Chen",
                "level": "intermediate",
                "duration": "2h 45m",
                "lessons": 10,
                "modules": [
                    {
                        "id": 1,
                        "title": "Suspension Basics",
                        "description": "Understanding springs, dampers, and anti-roll bars.",
                        "duration": "16:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Aerodynamics Setup",
                        "description": "Balancing downforce and drag for different tracks.",
                        "duration": "21:30",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 5,
                "title": "Tire Management",
                "description": "Master tire temperatures, pressures, and compound selection.",
                "instructor": "Emma Rodriguez",
                "level": "beginner",
                "duration": "1h 50m",
                "lessons": 6,
                "modules": [
                    {
                        "id": 1,
                        "title": "Understanding Tire Compounds",
                        "description": "Different tire types and when to use them.",
                        "duration": "18:20",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Tire Pressure Optimization",
                        "description": "Finding the perfect pressure for maximum grip.",
                        "duration": "15:40",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            },
            {
                "id": 6,
                "title": "Data Analysis Mastery",
                "description": "Use telemetry data to find speed and improve your driving.",
                "instructor": "Alex Johnson",
                "level": "advanced",
                "duration": "3h 30m",
                "lessons": 14,
                "modules": [
                    {
                        "id": 1,
                        "title": "Reading Telemetry Data",
                        "description": "Understanding speed traces, throttle, and brake data.",
                        "duration": "26:15",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    },
                    {
                        "id": 2,
                        "title": "Comparing Lap Times",
                        "description": "Analyzing differences between fast and slow laps.",
                        "duration": "23:45",
                        "video_id": "dQw4w9WgXcQ",
                        "completed": False
                    }
                ]
            }
        ]
        
        self.display_courses()

    def display_courses(self):
        """Display courses in the grid."""
        # Clear existing courses
        for i in reversed(range(self.course_grid_layout.count())):
            child = self.course_grid_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

        # Add courses to grid
        row, col = 0, 0
        max_cols = 3

        for course in self.courses:
            if self.should_show_course(course):
                course_card = EnhancedCourseCard(course)
                course_card.clicked.connect(lambda checked, c=course: self.open_course(c))
                
                self.course_grid_layout.addWidget(course_card, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        # Add stretch to push cards to top
        self.course_grid_layout.setRowStretch(row + 1, 1)

    def should_show_course(self, course):
        """Check if course should be shown based on current filters."""
        # Check search filter
        search_text = self.search_bar.text().lower()
        if search_text and search_text not in course["title"].lower() and search_text not in course["description"].lower():
            return False
        
        # Check level filter
        active_filter = None
        for filter_name, button in self.filter_buttons.items():
            if button.isChecked():
                active_filter = filter_name
                break
        
        if active_filter and active_filter != "All":
            if active_filter.lower() != course["level"]:
                return False
        
        return True

    def filter_courses(self):
        """Filter courses based on search text."""
        self.display_courses()

    def apply_filter(self, filter_name):
        """Apply level filter."""
        # Uncheck other filters
        for name, button in self.filter_buttons.items():
            if name != filter_name:
                button.setChecked(False)
        
        self.display_courses()

    def open_course(self, course):
        """Open a course in the course view."""
        self.current_course = course
        self.current_video = None
        
        # Update course info
        self.course_title_label.setText(course["title"])
        self.course_instructor.setText(f"Instructor: {course['instructor']}")
        self.course_level.setText(f"Level: {course['level'].capitalize()}")
        self.course_duration.setText(f"Duration: {course['duration']}")
        
        # Update progress
        completed_count = sum(1 for module in course["modules"] if module.get("completed", False))
        total_count = len(course["modules"])
        self.progress_label.setText(f"Progress: {completed_count}/{total_count} completed")
        
        # Clear and populate modules
        self.clear_modules()
        for i, module in enumerate(course["modules"]):
            module_card = VideoModuleCard(module, i + 1)
            module_card.clicked.connect(lambda checked, m=module: self.play_video(m))
            self.modules_layout.addWidget(module_card)
        
        self.modules_layout.addStretch()
        
        # Switch to course view
        self.stacked_widget.setCurrentIndex(1)
        
        # Load first video if available
        if course["modules"]:
            self.play_video(course["modules"][0])

    def play_video(self, module):
        """Play a video module."""
        self.current_video = module
        
        # Update video info
        self.video_title.setText(module["title"])
        self.video_description.setText(module["description"])
        
        # Update navigation buttons
        current_index = self.get_current_video_index()
        self.prev_button.setEnabled(current_index > 0)
        self.next_button.setEnabled(current_index < len(self.current_course["modules"]) - 1)
        
        # Update complete button
        if module.get("completed", False):
            self.mark_complete_button.setText("Completed ✓")
            self.mark_complete_button.setEnabled(False)
        else:
            self.mark_complete_button.setText("Mark as Complete")
            self.mark_complete_button.setEnabled(True)
        
        # Load video
        video_id = module.get("video_id", "")
        if video_id:
            self.load_youtube_video(video_id)
        else:
            self.load_video_placeholder()
        
        # Load comments for this video
        self.load_comments(module["id"])

    def load_youtube_video(self, video_id):
        """Load a YouTube video in the player."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background: #000;
                    overflow: hidden;
                }}
                .video-container {{
                    position: relative;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
                .error-message {{
                    display: none;
                    color: #fff;
                    text-align: center;
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="video-container">
                <iframe 
                    id="videoFrame"
                    src="https://www.youtube.com/embed/{video_id}?autoplay=0&rel=0&modestbranding=1&showinfo=0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen>
                </iframe>
                <div id="errorMessage" class="error-message">
                    <h3>Unable to load video</h3>
                    <p>Please check your internet connection and try again.</p>
                </div>
            </div>
            <script>
                // Error handling
                document.getElementById('videoFrame').onerror = function() {{
                    document.getElementById('videoFrame').style.display = 'none';
                    document.getElementById('errorMessage').style.display = 'block';
                }};
            </script>
        </body>
        </html>
        """
        self.video_player.setHtml(html_content)

    def load_video_placeholder(self):
        """Load placeholder when no video is available."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(135deg, #2c3e50, #34495e);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-family: Arial, sans-serif;
                }
                .placeholder {
                    text-align: center;
                    color: #bdc3c7;
                }
                .play-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                    opacity: 0.7;
                }
                .text {
                    font-size: 18px;
                    margin-bottom: 10px;
                }
                .subtext {
                    font-size: 14px;
                    opacity: 0.8;
                }
            </style>
        </head>
        <body>
            <div class="placeholder">
                <div class="play-icon">▶️</div>
                <div class="text">Select a lesson to start learning</div>
                <div class="subtext">Choose from the course modules on the right</div>
            </div>
        </body>
        </html>
        """
        self.video_player.setHtml(html_content)

    def get_current_video_index(self):
        """Get the index of the current video in the course."""
        if not self.current_course or not self.current_video:
            return -1
        
        for i, module in enumerate(self.current_course["modules"]):
            if module["id"] == self.current_video["id"]:
                return i
        return -1

    def previous_video(self):
        """Play the previous video."""
        current_index = self.get_current_video_index()
        if current_index > 0:
            self.play_video(self.current_course["modules"][current_index - 1])

    def next_video(self):
        """Play the next video."""
        current_index = self.get_current_video_index()
        if current_index < len(self.current_course["modules"]) - 1:
            self.play_video(self.current_course["modules"][current_index + 1])

    def mark_video_complete(self):
        """Mark the current video as complete."""
        if self.current_video:
            self.current_video["completed"] = True
            self.mark_complete_button.setText("Completed ✓")
            self.mark_complete_button.setEnabled(False)
            
            # Update progress
            completed_count = sum(1 for module in self.current_course["modules"] if module.get("completed", False))
            total_count = len(self.current_course["modules"])
            self.progress_label.setText(f"Progress: {completed_count}/{total_count} completed")
            
            # Update module card appearance
            self.refresh_module_cards()

    def refresh_module_cards(self):
        """Refresh the appearance of module cards."""
        for i in range(self.modules_layout.count() - 1):  # -1 for stretch
            item = self.modules_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'update_completion_status'):
                    widget.update_completion_status()

    def clear_modules(self):
        """Clear all module widgets."""
        while self.modules_layout.count() > 0:
            item = self.modules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def show_course_browser(self):
        """Return to the course browser."""
        self.stacked_widget.setCurrentIndex(0)

    def load_comments(self, video_id):
        """Load comments for a video."""
        # Clear existing comments
        while self.comments_layout.count() > 1:  # Keep the stretch
            item = self.comments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Sample comments (in a real app, these would come from a database)
        sample_comments = [
            {
                "id": 1,
                "author": "RacingPro42",
                "text": "Great explanation of racing lines! This really helped me understand the concept better.",
                "timestamp": "2 hours ago",
                "likes": 5
            },
            {
                "id": 2,
                "author": "SpeedDemon",
                "text": "I've been struggling with this technique. The visual examples make it so much clearer.",
                "timestamp": "1 day ago",
                "likes": 3
            }
        ]
        
        for comment in sample_comments:
            comment_widget = self.create_comment_widget(comment)
            self.comments_layout.insertWidget(self.comments_layout.count() - 1, comment_widget)

    def create_comment_widget(self, comment):
        """Create a widget for displaying a comment."""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #34495e;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 5px;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Header with author and timestamp
        header_layout = QHBoxLayout()
        
        author_label = QLabel(comment["author"])
        author_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(author_label)
        
        header_layout.addStretch()
        
        timestamp_label = QLabel(comment["timestamp"])
        timestamp_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        header_layout.addWidget(timestamp_label)
        
        layout.addLayout(header_layout)
        
        # Comment text
        text_label = QLabel(comment["text"])
        text_label.setStyleSheet("color: #ecf0f1; font-size: 14px; line-height: 1.4;")
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Footer with likes
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        likes_label = QLabel(f"👍 {comment['likes']}")
        likes_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        footer_layout.addWidget(likes_label)
        
        layout.addLayout(footer_layout)
        
        return widget

    def post_comment(self):
        """Post a new comment."""
        comment_text = self.comment_input.toPlainText().strip()
        if not comment_text:
            return
        
        # Create new comment
        new_comment = {
            "id": len(self.comments_layout) + 1,
            "author": "You",
            "text": comment_text,
            "timestamp": "Just now",
            "likes": 0
        }
        
        # Add comment widget
        comment_widget = self.create_comment_widget(new_comment)
        self.comments_layout.insertWidget(self.comments_layout.count() - 1, comment_widget)
        
        # Clear input
        self.comment_input.clear()
        
        # Scroll to bottom
        QTimer.singleShot(100, lambda: self.scroll_comments_to_bottom())

    def scroll_comments_to_bottom(self):
        """Scroll comments to bottom."""
        # Find the scroll area parent
        scroll_area = self.comments_widget.parent()
        if hasattr(scroll_area, 'verticalScrollBar'):
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())


class EnhancedCourseCard(QFrame):
    """Enhanced course card widget with better styling."""
    
    clicked = pyqtSignal(bool)

    def __init__(self, course_data, parent=None):
        super().__init__(parent)
        self.course_data = course_data
        
        self.setFixedSize(320, 400)
        self.setStyleSheet("""
            EnhancedCourseCard {
                background-color: #2c3e50;
                border-radius: 12px;
                border: 2px solid transparent;
            }
            EnhancedCourseCard:hover {
                border-color: #3498db;
                background-color: #34495e;
            }
        """)
        
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Thumbnail
        thumbnail = QLabel()
        thumbnail.setFixedHeight(180)
        thumbnail.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #3498db, stop:1 #2980b9);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)
        
        # Add level badge to thumbnail
        badge_text = course_data["level"].upper()
        badge_color = {
            "beginner": "#27ae60",
            "intermediate": "#f39c12", 
            "advanced": "#e74c3c"
        }.get(course_data["level"], "#3498db")
        
        thumbnail_layout = QVBoxLayout(thumbnail)
        thumbnail_layout.setContentsMargins(15, 15, 15, 15)
        
        level_badge = QLabel(badge_text)
        level_badge.setStyleSheet(f"""
            background-color: {badge_color};
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        level_badge.setAlignment(Qt.AlignCenter)
        level_badge.setMaximumWidth(80)
        
        thumbnail_layout.addWidget(level_badge)
        thumbnail_layout.addStretch()
        
        # Play icon
        play_icon = QLabel("▶")
        play_icon.setStyleSheet("""
            color: white;
            font-size: 32px;
            background-color: rgba(0, 0, 0, 0.6);
            border-radius: 25px;
            padding: 10px;
        """)
        play_icon.setAlignment(Qt.AlignCenter)
        play_icon.setFixedSize(50, 50)
        
        thumbnail_layout.addWidget(play_icon, 0, Qt.AlignCenter)
        thumbnail_layout.addStretch()
        
        layout.addWidget(thumbnail)
        
        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(10)
        
        # Title
        title = QLabel(course_data["title"])
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            margin-bottom: 5px;
        """)
        title.setWordWrap(True)
        content_layout.addWidget(title)
        
        # Instructor
        instructor = QLabel(f"by {course_data['instructor']}")
        instructor.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        content_layout.addWidget(instructor)
        
        # Description
        description = QLabel(course_data["description"])
        description.setStyleSheet("""
            color: #95a5a6;
            font-size: 13px;
            line-height: 1.3;
        """)
        description.setWordWrap(True)
        description.setMaximumHeight(60)
        content_layout.addWidget(description)
        
        # Stats
        stats_layout = QHBoxLayout()
        
        duration_label = QLabel(f"🕒 {course_data['duration']}")
        duration_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        stats_layout.addWidget(duration_label)
        
        lessons_label = QLabel(f"📚 {course_data['lessons']} lessons")
        lessons_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        stats_layout.addWidget(lessons_label)
        
        stats_layout.addStretch()
        content_layout.addLayout(stats_layout)
        
        layout.addWidget(content)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        self.clicked.emit(True)


class VideoModuleCard(QFrame):
    """Widget for displaying a video module in the course view."""
    
    clicked = pyqtSignal(bool)

    def __init__(self, module_data, module_number, parent=None):
        super().__init__(parent)
        self.module_data = module_data
        self.module_number = module_number
        
        self.setStyleSheet("""
            VideoModuleCard {
                background-color: #2c3e50;
                border-radius: 8px;
                border: 2px solid transparent;
                padding: 5px;
            }
            VideoModuleCard:hover {
                border-color: #3498db;
                background-color: #34495e;
            }
        """)
        
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Module number
        self.number_label = QLabel(str(module_number))
        self.number_label.setStyleSheet("""
            background-color: #3498db;
            color: white;
            border-radius: 18px;
            font-weight: bold;
            font-size: 14px;
            min-width: 36px;
            max-width: 36px;
            min-height: 36px;
            max-height: 36px;
            qproperty-alignment: AlignCenter;
        """)
        layout.addWidget(self.number_label)
        
        # Module info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.title_label = QLabel(module_data["title"])
        self.title_label.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 15px;
        """)
        info_layout.addWidget(self.title_label)
        
        duration_label = QLabel(f"Duration: {module_data['duration']}")
        duration_label.setStyleSheet("color: #bdc3c7; font-size: 12px;")
        info_layout.addWidget(duration_label)
        
        layout.addLayout(info_layout, 1)
        
        # Status icon
        self.status_icon = QLabel("▶")
        self.status_icon.setStyleSheet("""
            color: #3498db;
            font-size: 18px;
            padding: 5px;
        """)
        layout.addWidget(self.status_icon)
        
        self.update_completion_status()

    def update_completion_status(self):
        """Update the visual status based on completion."""
        if self.module_data.get("completed", False):
            self.status_icon.setText("✓")
            self.status_icon.setStyleSheet("""
                color: #27ae60;
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
            """)
            self.number_label.setStyleSheet("""
                background-color: #27ae60;
                color: white;
                border-radius: 18px;
                font-weight: bold;
                font-size: 14px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                qproperty-alignment: AlignCenter;
            """)
        else:
            self.status_icon.setText("▶")
            self.status_icon.setStyleSheet("""
                color: #3498db;
                font-size: 18px;
                padding: 5px;
            """)

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        self.clicked.emit(True)


class SuperLapWidget(QWidget):
    """Advanced SuperLap analysis widget - helping drivers understand exactly how to improve."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.ml_laps = []
        self.user_laps = []
        self.current_user_lap = None
        self.current_ml_lap = None
        self.current_session_info = None
        
        # Track active threads for cleanup
        self.active_threads = []
        self._is_being_destroyed = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the comprehensive SuperLap analysis UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Compact header section with session context
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        header_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(3)
        
        # Title
        title_label = QLabel("SuperLap Analysis")
        title_label.setStyleSheet("""
            color: #00ff88;
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 2px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Session context
        self.session_context_label = QLabel("Select a session to see AI-optimized racing lines for your car/track combo")
        self.session_context_label.setStyleSheet("""
            color: #cccccc;
            font-size: 12px;
            font-style: normal;
            background-color: transparent;
        """)
        self.session_context_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.session_context_label)
        
        main_layout.addWidget(header_frame)
        
        # Combined session and lap selection in one compact frame
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        controls_frame.setStyleSheet("""
            background-color: #111;
            border: 1px solid #444;
            border-radius: 5px;
            padding: 8px;
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(6)
        
        # Session selection row
        session_row = QHBoxLayout()
        session_label = QLabel("Session:")
        session_label.setStyleSheet("color: #DDD; font-weight: bold; min-width: 70px;")
        session_row.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
            }
        """)
        self.session_combo.currentTextChanged.connect(self.on_session_changed)
        session_row.addWidget(self.session_combo, 1)
        
        # Refresh button
        refresh_button = QPushButton("🔄")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px 8px;
                min-width: 30px;
                max-width: 30px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        refresh_button.clicked.connect(self.refresh_data)
        session_row.addWidget(refresh_button)
        
        # Add iRacing connection reset button
        self.reset_connection_button = QPushButton("🔌 Reset iRacing")
        self.reset_connection_button.setToolTip("Reset iRacing connection if showing as disconnected")
        self.reset_connection_button.setStyleSheet("padding: 5px 10px; background-color: #444; color: #FFA500;")
        self.reset_connection_button.clicked.connect(self._reset_iracing_connection)
        session_row.addWidget(self.reset_connection_button)
        
        controls_layout.addLayout(session_row)
        
        # Lap selection row
        lap_row = QHBoxLayout()
        
        # User lap selection
        user_lap_label = QLabel("Your Lap:")
        user_lap_label.setStyleSheet("color: #DDD; font-weight: bold; min-width: 70px;")
        lap_row.addWidget(user_lap_label)
        
        self.user_lap_combo = QComboBox()
        self.user_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
            }
        """)
        self.user_lap_combo.currentTextChanged.connect(self.on_user_lap_changed)
        lap_row.addWidget(self.user_lap_combo, 1)
        
        lap_row.addSpacing(10)
        
        # ML lap selection
        ml_lap_label = QLabel("SuperLap:")
        ml_lap_label.setStyleSheet("color: #00ff88; font-weight: bold; min-width: 70px;")
        lap_row.addWidget(ml_lap_label)
        
        self.ml_lap_combo = QComboBox()
        self.ml_lap_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a3d1a;
                color: #00ff88;
                border: 1px solid #00ff88;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #00ff88;
            }
        """)
        self.ml_lap_combo.currentTextChanged.connect(self.on_ml_lap_changed)
        lap_row.addWidget(self.ml_lap_combo, 1)
        
        lap_row.addSpacing(10)
        
        # Analyze button (renamed from Compare)
        self.compare_button = QPushButton("Analyze Performance")
        self.compare_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff88;
                color: black;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #00cc6a;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        self.compare_button.clicked.connect(self.analyze_performance)
        self.compare_button.setEnabled(False)
        lap_row.addWidget(self.compare_button)
        
        controls_layout.addLayout(lap_row)
        
        main_layout.addWidget(controls_frame)
        
        # Create tabbed analysis view with reduced margins
        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #111;
                border-radius: 3px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background-color: #333;
                color: #CCC;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background-color: #444;
                color: #00ff88;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # Performance Overview Tab
        self.overview_tab = self.create_overview_tab()
        self.analysis_tabs.addTab(self.overview_tab, "Overview")
        
        # Sector Analysis Tab
        self.sector_tab = self.create_sector_analysis_tab()
        self.analysis_tabs.addTab(self.sector_tab, "Sectors")
        
        # Driving Technique Tab
        self.technique_tab = self.create_technique_analysis_tab()
        self.analysis_tabs.addTab(self.technique_tab, "Technique")
        
        # Telemetry Comparison Tab
        self.telemetry_tab = self.create_telemetry_comparison_tab()
        self.analysis_tabs.addTab(self.telemetry_tab, "Telemetry")
        
        main_layout.addWidget(self.analysis_tabs)
        
        # Load initial data
        self.refresh_data()
    
    def create_overview_tab(self):
        """Create the performance overview tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Performance metrics grid
        metrics_frame = QFrame()
        metrics_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        metrics_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setSpacing(8)
        
        # Lap time comparison
        self.user_time_label = QLabel("Your Time: --:--.---")
        self.user_time_label.setStyleSheet("color: #DDDDDD; font-size: 16px; font-weight: bold; background-color: transparent;")
        metrics_layout.addWidget(self.user_time_label, 0, 0)
        
        self.ml_time_label = QLabel("SuperLap Time: --:--.---")
        self.ml_time_label.setStyleSheet("color: #00ff88; font-size: 16px; font-weight: bold; background-color: transparent;")
        metrics_layout.addWidget(self.ml_time_label, 0, 1)
        
        self.time_diff_label = QLabel("Potential Improvement: --:--.---")
        self.time_diff_label.setStyleSheet("color: #ff6666; font-size: 16px; font-weight: bold; background-color: transparent;")
        metrics_layout.addWidget(self.time_diff_label, 0, 2)
        
        # AI Analysis info
        self.confidence_label = QLabel("AI Confidence: --%")
        self.confidence_label.setStyleSheet("color: #ffaa00; font-size: 12px; background-color: transparent;")
        metrics_layout.addWidget(self.confidence_label, 1, 0)
        
        self.method_label = QLabel("Analysis Method: --")
        self.method_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        metrics_layout.addWidget(self.method_label, 1, 1)
        
        self.model_label = QLabel("AI Model: --")
        self.model_label.setStyleSheet("color: #cccccc; font-size: 12px; background-color: transparent;")
        metrics_layout.addWidget(self.model_label, 1, 2)
        
        layout.addWidget(metrics_frame)
        
        # Create a horizontal layout for insights and breakdown to use space more efficiently
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # Key insights section
        insights_frame = QFrame()
        insights_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        insights_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        insights_layout = QVBoxLayout(insights_frame)
        insights_layout.setSpacing(5)
        
        insights_title = QLabel("🎯 Key Areas for Improvement")
        insights_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        insights_layout.addWidget(insights_title)
        
        self.insights_list = QLabel("Select laps to see personalized improvement suggestions")
        self.insights_list.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.insights_list.setWordWrap(True)
        insights_layout.addWidget(self.insights_list)
        
        content_layout.addWidget(insights_frame, 1)
        
        # Performance breakdown
        breakdown_frame = QFrame()
        breakdown_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        breakdown_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        breakdown_layout = QVBoxLayout(breakdown_frame)
        breakdown_layout.setSpacing(5)
        
        breakdown_title = QLabel("📊 Performance Breakdown")
        breakdown_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        breakdown_layout.addWidget(breakdown_title)
        
        # Create progress bars for different aspects
        self.create_performance_bars(breakdown_layout)
        
        content_layout.addWidget(breakdown_frame, 1)
        
        layout.addLayout(content_layout)
        
        layout.addStretch()
        return tab
    
    def create_performance_bars(self, layout):
        """Create performance comparison bars."""
        aspects = [
            ("Braking Efficiency", "brake_efficiency"),
            ("Cornering Speed", "cornering_speed"), 
            ("Throttle Application", "throttle_application"),
            ("Racing Line", "racing_line"),
            ("Consistency", "consistency")
        ]
        
        self.performance_bars = {}
        
        for aspect_name, aspect_key in aspects:
            aspect_layout = QHBoxLayout()
            
            # Label
            label = QLabel(aspect_name)
            label.setStyleSheet("color: #dddddd; font-size: 12px; min-width: 120px; background-color: transparent;")
            aspect_layout.addWidget(label)
            
            # Progress bar
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(0)
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 3px;
                    background-color: #333;
                    color: white;
                    text-align: center;
                    font-weight: bold;
                    height: 16px;
                    font-size: 10px;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #ff4444, stop:0.5 #ffaa00, stop:1 #00ff88);
                    border-radius: 3px;
                }
            """)
            aspect_layout.addWidget(progress)
            
            # Score label
            score_label = QLabel("--/100")
            score_label.setStyleSheet("color: #cccccc; font-size: 10px; min-width: 50px; background-color: transparent;")
            aspect_layout.addWidget(score_label)
            
            self.performance_bars[aspect_key] = (progress, score_label)
            layout.addLayout(aspect_layout)
    
    def create_sector_analysis_tab(self):
        """Create the sector analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Sector comparison table
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        table_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setSpacing(5)
        
        table_title = QLabel("🏁 Sector-by-Sector Analysis")
        table_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        table_layout.addWidget(table_title)
        
        self.sector_table = QTableWidget()
        self.sector_table.setColumnCount(5)
        self.sector_table.setHorizontalHeaderLabels(["Sector", "Your Time", "SuperLap Time", "Difference", "Improvement"])
        self.sector_table.setStyleSheet("""
            QTableWidget {
                background-color: #222;
                color: white;
                gridline-color: #444;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333;
            }
            QTableWidget::item:selected {
                background-color: #444;
            }
            QHeaderView::section {
                background-color: #333;
                color: #00ff88;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        self.sector_table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.sector_table)
        
        layout.addWidget(table_frame)
        
        # Sector insights
        insights_frame = QFrame()
        insights_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        insights_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        insights_layout = QVBoxLayout(insights_frame)
        insights_layout.setSpacing(5)
        
        insights_title = QLabel("💡 Sector-Specific Tips")
        insights_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        insights_layout.addWidget(insights_title)
        
        self.sector_tips = QLabel("Analyze your laps to see specific tips for each sector")
        self.sector_tips.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.sector_tips.setWordWrap(True)
        insights_layout.addWidget(self.sector_tips)
        
        layout.addWidget(insights_frame)
        
        layout.addStretch()
        return tab
    
    def create_technique_analysis_tab(self):
        """Create the driving technique analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Brake points analysis
        brake_frame = QFrame()
        brake_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        brake_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        brake_layout = QVBoxLayout(brake_frame)
        brake_layout.setSpacing(5)
        
        brake_title = QLabel("🛑 Braking Analysis")
        brake_title.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        brake_layout.addWidget(brake_title)
        
        self.brake_analysis = QLabel("Brake point analysis will appear here")
        self.brake_analysis.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.brake_analysis.setWordWrap(True)
        brake_layout.addWidget(self.brake_analysis)
        
        layout.addWidget(brake_frame)
        
        # Throttle analysis
        throttle_frame = QFrame()
        throttle_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        throttle_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        throttle_layout = QVBoxLayout(throttle_frame)
        throttle_layout.setSpacing(5)
        
        throttle_title = QLabel("⚡ Throttle Application")
        throttle_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        throttle_layout.addWidget(throttle_title)
        
        self.throttle_analysis = QLabel("Throttle application analysis will appear here")
        self.throttle_analysis.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.throttle_analysis.setWordWrap(True)
        throttle_layout.addWidget(self.throttle_analysis)
        
        layout.addWidget(throttle_frame)
        
        # Racing line analysis
        line_frame = QFrame()
        line_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        line_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        line_layout = QVBoxLayout(line_frame)
        line_layout.setSpacing(5)
        
        line_title = QLabel("🏎️ Racing Line")
        line_title.setStyleSheet("color: #ffaa00; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        line_layout.addWidget(line_title)
        
        self.line_analysis = QLabel("Racing line analysis will appear here")
        self.line_analysis.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4; background-color: transparent;")
        self.line_analysis.setWordWrap(True)
        line_layout.addWidget(self.line_analysis)
        
        layout.addWidget(line_frame)
        
        layout.addStretch()
        return tab
    
    def create_telemetry_comparison_tab(self):
        """Create the telemetry comparison tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Placeholder for telemetry graphs
        graphs_frame = QFrame()
        graphs_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        graphs_frame.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        """)
        graphs_layout = QVBoxLayout(graphs_frame)
        graphs_layout.setSpacing(5)
        
        graphs_title = QLabel("📈 Telemetry Comparison")
        graphs_title.setStyleSheet("color: #00ff88; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        graphs_layout.addWidget(graphs_title)
        
        self.telemetry_placeholder = QLabel("Detailed telemetry comparison graphs will be displayed here.\nThis will include throttle, brake, steering, and speed traces overlaid with the SuperLap data.")
        self.telemetry_placeholder.setStyleSheet("""
            color: #666;
            font-size: 12px;
            font-style: italic;
            padding: 30px;
            text-align: center;
        """)
        self.telemetry_placeholder.setAlignment(Qt.AlignCenter)
        graphs_layout.addWidget(self.telemetry_placeholder)
        
        layout.addWidget(graphs_frame)
        
        layout.addStretch()
        return tab
    
    def refresh_data(self):
        """Refresh the session and lap data from Supabase asynchronously."""
        try:
            # Load sessions asynchronously to avoid blocking UI
            QTimer.singleShot(0, self.load_sessions_async)
        except Exception as e:
            print(f"Error refreshing SuperLap data: {e}")
    
    def load_sessions_async(self):
        """Load user sessions asynchronously to avoid blocking the UI."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if session loading is already in progress
        if self._is_thread_running('session_load'):
            logger.info("Session loading already in progress, skipping duplicate request")
            return
            
        # Create a worker thread to handle the database operations
        session_load_thread = QThread()
        session_load_worker = SuperLapSessionWorker()
        session_load_worker.moveToThread(session_load_thread)
        
        # Track this thread for cleanup with unique identifier
        thread_id = f'session_load_{id(session_load_thread)}'
        self.active_threads.append((thread_id, session_load_thread, session_load_worker))
        
        # Connect signals
        session_load_thread.started.connect(session_load_worker.run)
        session_load_worker.sessions_loaded.connect(self.on_sessions_loaded)
        session_load_worker.error.connect(self.on_sessions_error)
        session_load_worker.finished.connect(session_load_thread.quit)
        session_load_worker.finished.connect(session_load_worker.deleteLater)
        session_load_thread.finished.connect(session_load_thread.deleteLater)
        session_load_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
        
        # Start the thread
        session_load_thread.start()
    
    def _on_sessions_loaded(self, sessions, message):
        """Handle loaded sessions from worker thread."""
        try:
            if hasattr(self, 'session_combo'):
                # Temporarily block signals to prevent on_session_changed during programmatic population
                self.session_combo.blockSignals(True) # <--- ADD/ENSURE THIS LINE
                
                self.session_combo.clear() # Clear after blocking
                
                if sessions:
                    for session in sessions:
                        display_text = self._format_session_display(session)
                        self.sessiimage.pngbddItem(display_text, session)
                    
                    # Select first session by default
                    if self.session_combo.count() > 0:
                        self.session_combo.setCurrentIndex(0)
                        # DO NOT call self.on_session_changed() here.
                        # The InitialLoadWorker's _on_laps_loaded method will handle loading laps for this first session.
                else:
                    self.session_combo.addItem("No sessions found", None)
                
                self.session_combo.blockSignals(False) # <--- ADD/ENSURE THIS LINE (Unblock signals)
                    
            logger.info(f"Loaded {len(sessions) if sessions else 0} sessions")
            
        except Exception as e:
            logger.error(f"Error handling loaded sessions: {e}")

    
    def on_sessions_error(self, error_message):
        """Handle session loading errors."""
        self.session_combo.clear()
        self.session_combo.addItem(f"Error: {error_message}", None)
        self.session_context_label.setText("Error loading session data. Please try again.")

    def load_sessions(self):
        """Load user sessions that match car/track combinations with available SuperLaps."""
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available")
                self.session_combo.clear()
                self.session_combo.addItem("Authentication required", None)
                return
            
            # Get user sessions with car/track info
            # CRITICAL FIX: Include track length_meters in the query
            sessions_result = (
                main_supabase.client.table("sessions")
                .select("id,car_id,track_id,created_at,cars(name),tracks(name, length_meters)")
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            
            self.session_combo.clear()
            
            if sessions_result.data:
                # Filter sessions that have matching ML data available
                valid_sessions = []
                
                for session in sessions_result.data:
                    car_id = session.get('car_id')
                    track_id = session.get('track_id')
                    
                    if car_id and track_id:
                        # Check if ML data exists for this car/track combo
                        try:
                            ml_check = (
                                main_supabase.client.table("laps_ml")
                                .select("id")
                                .eq("car_id", car_id)
                                .eq("track_id", track_id)
                                .limit(1)
                                .execute()
                            )
                            
                            if ml_check.data:  # ML data exists for this car/track
                                valid_sessions.append(session)
                        except Exception as ml_error:
                            print(f"Error checking ML data for session {session.get('id')}: {ml_error}")
                            # Include session anyway for now during development
                            valid_sessions.append(session)
                            continue
                
                # Add valid sessions to combo box
                if valid_sessions:
                    for session in valid_sessions:
                        car_name = session.get('cars', {}).get('name', 'Unknown Car') if session.get('cars') else 'Unknown Car'
                        track_name = session.get('tracks', {}).get('name', 'Unknown Track') if session.get('tracks') else 'Unknown Track'
                    created_at = session.get('created_at', '')
                    
                    try:
                        from datetime import datetime
                        timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        display_text = f"{timestamp.strftime('%Y-%m-%d %H:%M')} - {track_name} ({car_name})"
                    except (ValueError, TypeError):
                        display_text = f"{created_at} - {track_name} ({car_name})"
                    
                    self.session_combo.addItem(display_text, session)
                
                if self.session_combo.count() > 0:
                    self.session_combo.setCurrentIndex(0)
                    self.on_session_changed()
                else:
                    self.session_combo.addItem("No sessions with ML data available", None)
                    self.session_context_label.setText("No SuperLap data available for your car/track combinations yet. Our ML model is continuously analyzing new data.")
            else:
                self.session_combo.addItem("No sessions found", None)
                self.session_context_label.setText("No racing sessions found. Complete some laps to see SuperLap analysis.")
                
        except Exception as e:
            print(f"Error loading sessions: {e}")
            self.session_combo.addItem("Error loading sessions", None)
    
    def on_session_changed(self):
        """Handle session selection change."""
        current_session = self.session_combo.currentData()
        if current_session:
            self.current_session_info = current_session
            # Extract car and track names from the nested objects
            car_name = current_session.get('cars', {}).get('name', 'Unknown Car') if current_session.get('cars') else 'Unknown Car'
            track_name = current_session.get('tracks', {}).get('name', 'Unknown Track') if current_session.get('tracks') else 'Unknown Track'
            
            self.session_context_label.setText(f"Analyzing: {car_name} at {track_name}")
            
            # Load laps for this session
            self.load_user_laps()
            self.load_ml_laps()
        else:
            self.current_session_info = None
            self.session_context_label.setText("Select a session to see AI-optimized racing lines")
            self.user_lap_combo.clear()
            self.ml_lap_combo.clear()
    
    def load_user_laps(self):
        """Load user laps for the selected session asynchronously."""
        if not self.current_session_info:
            return
        
        # Use QTimer to defer the database operation
        QTimer.singleShot(0, self._load_user_laps_async)
    
    def _load_user_laps_async(self):
        """Load user laps asynchronously to avoid blocking UI."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if user lap loading is already in progress
        if self._is_thread_running('user_lap'):
            logger.info("User lap loading already in progress, skipping duplicate request")
            return
            
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available for user laps")
                self.user_lap_combo.clear()
                self.user_lap_combo.addItem("Authentication required", None)
                return
            
            session_id = self.current_session_info.get('id')
            
            # Show loading state
            self.user_lap_combo.clear()
            self.user_lap_combo.addItem("Loading laps...", None)
            
            # Create worker for lap loading
            user_lap_thread = QThread()
            user_lap_worker = SuperLapUserLapWorker(session_id)
            user_lap_worker.moveToThread(user_lap_thread)
            
            # Track this thread for cleanup with unique identifier
            thread_id = f'user_lap_{id(user_lap_thread)}'
            self.active_threads.append((thread_id, user_lap_thread, user_lap_worker))
            
            # Connect signals
            user_lap_thread.started.connect(user_lap_worker.run)
            user_lap_worker.laps_loaded.connect(self.on_user_laps_loaded)
            user_lap_worker.error.connect(self.on_user_laps_error)
            user_lap_worker.finished.connect(user_lap_thread.quit)
            user_lap_worker.finished.connect(user_lap_worker.deleteLater)
            user_lap_thread.finished.connect(user_lap_thread.deleteLater)
            user_lap_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
            
            # Start the thread
            user_lap_thread.start()
                
        except Exception as e:
            print(f"Error loading user laps: {e}")
            self.user_lap_combo.clear()
            self.user_lap_combo.addItem("Error loading laps", None)
    
    def on_user_laps_loaded(self, laps):
        """Handle loaded user laps."""
        self.user_lap_combo.clear()
        
        if laps:
            self.user_laps = laps
            for lap in laps:
                    lap_number = lap.get('lap_number', 0)
                    lap_time = lap.get('lap_time', 0)
                    time_str = self._format_time(lap_time) if lap_time > 0 else "Invalid"
                    display_text = f"Lap {lap_number} - {time_str}"
                    self.user_lap_combo.addItem(display_text, lap['id'])
            else:
                self.user_laps = []
            self.user_lap_combo.addItem("No valid laps available", None)
    
    def on_user_laps_error(self, error_message):
        """Handle user lap loading errors."""
        self.user_lap_combo.clear()
        self.user_lap_combo.addItem(f"Error: {error_message}", None)
    
    def load_ml_laps(self):
        """Load ML-optimized laps that match the current session's car/track combination asynchronously."""
        if not self.current_session_info:
            return
        
        # Use QTimer to defer the database operation
        QTimer.singleShot(0, self._load_ml_laps_async)
    
    def _load_ml_laps_async(self):
        """Load ML laps asynchronously to avoid blocking UI."""
        # Don't start new threads if widget is being destroyed
        if self._is_being_destroyed:
            return
        
        # Check if ML lap loading is already in progress
        if self._is_thread_running('ml_lap'):
            logger.info("ML lap loading already in progress, skipping duplicate request")
            return
            
        try:
            # Get car and track IDs from session
            car_id = self.current_session_info.get('car_id')
            track_id = self.current_session_info.get('track_id')
            
            # Show loading state
            self.ml_lap_combo.clear()
            self.ml_lap_combo.addItem("Loading SuperLaps...", None)
            
            # Create worker for ML lap loading
            ml_lap_thread = QThread()
            ml_lap_worker = SuperLapMLLapWorker(car_id, track_id)
            ml_lap_worker.moveToThread(ml_lap_thread)
            
            # Track this thread for cleanup with unique identifier
            thread_id = f'ml_lap_{id(ml_lap_thread)}'
            self.active_threads.append((thread_id, ml_lap_thread, ml_lap_worker))
            
            # Connect signals
            ml_lap_thread.started.connect(ml_lap_worker.run)
            ml_lap_worker.laps_loaded.connect(self.on_ml_laps_loaded)
            ml_lap_worker.error.connect(self.on_ml_laps_error)
            ml_lap_worker.finished.connect(ml_lap_thread.quit)
            ml_lap_worker.finished.connect(ml_lap_worker.deleteLater)
            ml_lap_thread.finished.connect(ml_lap_thread.deleteLater)
            ml_lap_thread.finished.connect(lambda: self._remove_thread_from_tracking(thread_id))
            
            # Start the thread
            ml_lap_thread.start()
            
        except Exception as e:
            print(f"Error loading ML laps: {e}")
            self.ml_lap_combo.clear()
            self.ml_lap_combo.addItem("Error loading SuperLaps", None)
    
    def on_ml_laps_loaded(self, ml_laps_data):
        """Handle loaded ML laps."""
        self.ml_lap_combo.clear()
        
        if ml_laps_data:
            self.ml_laps = ml_laps_data
            for lap in ml_laps_data:
                lap_time = lap.get('lap_time', 0)
                improvement = lap.get('predicted_improvement_ms', 0)
                confidence = lap.get('confidence_score', 0)
                model = lap.get('model_used', 'AI Model')
                
                time_str = self._format_time(lap_time) if lap_time > 0 else "Invalid"
                improvement_str = f"-{improvement/1000:.3f}s" if improvement > 0 else "No improvement"
                display_text = f"{model}: {time_str} ({improvement_str}, {confidence*100:.0f}% confidence)"
                self.ml_lap_combo.addItem(display_text, lap['id'])
        else:
            self.ml_laps = []
            self.ml_lap_combo.addItem("No SuperLaps available for this car/track", None)
    
    def on_ml_laps_error(self, error_message):
        """Handle ML lap loading errors."""
        self.ml_lap_combo.clear()
        self.ml_lap_combo.addItem(f"Error: {error_message}", None)
    
    def get_filtered_ml_laps(self, car_id, track_id):
        """Get ML laps filtered by car and track from Supabase laps_ml table."""
        if not car_id or not track_id:
            return []
            
        try:
            from trackpro.database.supabase_client import supabase as main_supabase
            
            if not main_supabase or not main_supabase.is_authenticated():
                print("No authenticated Supabase client available for ML laps")
                return []
            
            # Query the laps_ml table for ML-optimized laps matching this car/track combo
            ml_laps_result = (
                main_supabase.client.table("laps_ml")
                .select("*")
                .eq("car_id", car_id)
                .eq("track_id", track_id)
                .order("confidence_score", desc=True)  # Best confidence first
                .limit(10)  # Limit to top 10 ML laps
                .execute()
            )
            
            if not ml_laps_result.data:
                print(f"No ML laps found for car_id={car_id}, track_id={track_id}")
                return []
            
            ml_laps = []
            for ml_lap in ml_laps_result.data:
                # Get additional optimization details if available
                optimization_details = {}
                
                # Try to get brake points from ml_optimizations table
                try:
                    opt_result = (
                        main_supabase.client.table("ml_optimizations")
                        .select("optimization_type,details")
                        .eq("ml_lap_id", ml_lap.get("id"))
                        .execute()
                    )
                    
                    if opt_result.data:
                        for opt in opt_result.data:
                            opt_type = opt.get("optimization_type")
                            details = opt.get("details", {})
                            
                            if isinstance(details, str):
                                import json
                                try:
                                    details = json.loads(details)
                                except:
                                    details = {}
                            
                            if opt_type == "brake_points":
                                optimization_details["brake_points"] = details.get("points", [])
                            elif opt_type == "throttle_points":
                                optimization_details["throttle_points"] = details.get("points", [])
                            elif opt_type == "racing_line":
                                optimization_details["racing_line"] = details.get("sections", [])
                                
                except Exception as opt_error:
                    print(f"Error fetching optimization details: {opt_error}")
                
                # Build the ML lap data structure
                ml_lap_data = {
                    'id': ml_lap.get('id'),
                    'lap_time': ml_lap.get('lap_time', 0),
                    'predicted_improvement_ms': ml_lap.get('predicted_improvement_ms', 0),
                    'confidence_score': ml_lap.get('confidence_score', 0),
                    'optimization_method': ml_lap.get('optimization_method', 'ml_analysis'),
                    'model_used': ml_lap.get('model_used', 'AI Model'),
                'car_id': car_id,
                'track_id': track_id,
                    'created_at': ml_lap.get('created_at'),
                    **optimization_details  # Add brake_points, throttle_points, racing_line
                }
                
                ml_laps.append(ml_lap_data)
            
            print(f"Found {len(ml_laps)} ML laps for car_id={car_id}, track_id={track_id}")
            return ml_laps
            
        except Exception as e:
            print(f"Error fetching ML laps from Supabase: {e}")
            return []


class RaceCoachWidget(QWidget):
    """Main container widget for Race Coach functionality.

    This widget integrates iRacing telemetry data with AI-powered analysis and visualization.
    """

    def __init__(self, parent=None, iracing_api=None):
        super().__init__(parent)
        self.setObjectName("RaceCoachWidget")
        
        logger.info("🔍 RaceCoachWidget.__init__() called")
        logger.info(f"🔍 iracing_api parameter: {iracing_api}")

        # Lazy initialization flags (using old working system)
        self._lazy_init_completed = False
        self._lazy_init_in_progress = False

        # Store reference to the iRacing API (may be None for lazy init)
        self.iracing_api = iracing_api
        logger.info(f"🔍 Set self.iracing_api to: {self.iracing_api}")

        # Track connection state
        self.is_connected = False
        self.session_info = {}

        # Attributes for background telemetry fetching
        self.telemetry_fetch_thread = None
        self.telemetry_fetch_worker = None

        # Attributes for background initial data loading
        self.initial_load_thread = None
        self.initial_load_worker = None
        self._is_initial_loading = False

        # Flag to track if initial lap list load has happened
        self._initial_lap_load_done = False

        # Flags to prevent duplicate operations
        self._initial_load_in_progress = False
        self._show_event_in_progress = False
        self._initialization_complete = False
        self._initial_connection_attempted = False

        # Initialize UI (always safe to do)
        logger.info("🔍 Calling setup_ui()...")
        self.setup_ui()
        logger.info("✅ setup_ui() completed")

        # Mark basic initialization as complete
        self._initialization_complete = True
        logger.info("✅ Basic initialization complete")

        # Only connect to iRacing API if we have one (non-lazy mode)
        if self.iracing_api is not None:
            logger.info("🔍 Non-lazy mode: setting up iRacing API connections...")
            self._setup_iracing_api_connections()
        else:
            logger.info("🔍 RaceCoachWidget created in lazy initialization mode")
            # Start lazy initialization immediately
            logger.info("🔍 Starting lazy initialization work...")
            self._do_lazy_initialization_work()

    def showEvent(self, event):
        """Handle the widget being shown - start deferred monitoring if needed."""
        logger.info("🔍 RaceCoachWidget.showEvent() called - widget is being shown")
        super().showEvent(event)
        
        # Debug: Check all the conditions for starting monitoring
        logger.info(f"🔍 Debug showEvent conditions:")
        logger.info(f"  - hasattr(self, 'iracing_api'): {hasattr(self, 'iracing_api')}")
        logger.info(f"  - self.iracing_api is not None: {getattr(self, 'iracing_api', None) is not None}")
        logger.info(f"  - hasattr(iracing_api, 'start_deferred_monitoring'): {hasattr(getattr(self, 'iracing_api', None), 'start_deferred_monitoring') if hasattr(self, 'iracing_api') else False}")
        logger.info(f"  - not hasattr(self, '_monitoring_started'): {not hasattr(self, '_monitoring_started')}")
        logger.info(f"  - _monitoring_started value: {getattr(self, '_monitoring_started', 'NOT_SET')}")
        
        # Start deferred monitoring if we have an iRacing API and haven't started monitoring yet
        if (hasattr(self, 'iracing_api') and self.iracing_api and 
            hasattr(self.iracing_api, 'start_deferred_monitoring') and
            not hasattr(self, '_monitoring_started')):
            
            logger.info("🚀 Race Coach widget shown - starting deferred iRacing monitoring...")
            try:
                # Check if deferred params are available
                if hasattr(self.iracing_api, '_deferred_monitor_params'):
                    logger.info(f"🔍 Deferred monitor params available: {self.iracing_api._deferred_monitor_params is not None}")
                    if self.iracing_api._deferred_monitor_params:
                        params = self.iracing_api._deferred_monitor_params
                        logger.info(f"🔍 Deferred params contents: supabase_client={params.get('supabase_client') is not None}, user_id={params.get('user_id')}, lap_saver={params.get('lap_saver') is not None}")
                else:
                    logger.warning("🔍 No _deferred_monitor_params attribute found on iracing_api")
                
                success = self.iracing_api.start_deferred_monitoring()
                if success:
                    logger.info("✅ Deferred iRacing monitoring started successfully")
                    self._monitoring_started = True
                else:
                    logger.warning("⚠️ Failed to start deferred iRacing monitoring")
            except Exception as e:
                logger.error(f"❌ Error starting deferred monitoring: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.info("🔍 Skipping deferred monitoring start - conditions not met")
            if not hasattr(self, 'iracing_api'):
                logger.info("  - No iracing_api attribute")
            elif not self.iracing_api:
                logger.info("  - iracing_api is None")
            elif not hasattr(self.iracing_api, 'start_deferred_monitoring'):
                logger.info("  - iracing_api has no start_deferred_monitoring method")
            elif hasattr(self, '_monitoring_started'):
                logger.info("  - Monitoring already started")

    def _setup_iracing_api_connections(self):
        """Set up connections to the iRacing API."""
        try:
            # Try SimpleIRacingAPI method names first
            if hasattr(self.iracing_api, "register_on_connection_changed"):
                logger.info("Using SimpleIRacingAPI callback methods")
                self.iracing_api.register_on_connection_changed(self.on_iracing_connected)
                self.iracing_api.register_on_telemetry_data(self.on_telemetry_data)

                # Connect the new signal
                if hasattr(self.iracing_api, "sessionInfoUpdated"):
                    logger.info("Connecting sessionInfoUpdated signal to UI update slot.")
                    self.iracing_api.sessionInfoUpdated.connect(self._update_connection_status)
                else:
                    logger.warning("iRacing API instance does not have sessionInfoUpdated signal.")

                logger.info("Deferring iRacing connection until Race Coach tab is shown")

            # Fall back to IRacingAPI method names
            elif hasattr(self.iracing_api, "register_connection_callback"):
                logger.warning("Legacy IRacingAPI callback registration attempted - this might not work as expected.")
            else:
                logger.warning("Unable to register callbacks with iRacing API - incompatible implementation")
        except Exception as e:
            logger.error(f"Error setting up callbacks for iRacing API: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _do_lazy_initialization_work(self):
        """Do the actual heavy initialization work in the background."""
        logger.info("🔍 Starting _do_lazy_initialization_work()")
        try:
            # Create data manager
            try:
                logger.info("🔍 Creating DataManager...")
                from .data_manager import DataManager
                self.data_manager = DataManager()
                logger.info("✅ DataManager initialized successfully")
            except Exception as data_error:
                logger.error(f"❌ Error initializing DataManager: {data_error}")
                self.data_manager = None

            # Create TelemetrySaver for local saving
            try:
                logger.info("🔍 Creating TelemetrySaver...")
                from .telemetry_saver import TelemetrySaver
                self.telemetry_saver = TelemetrySaver(data_manager=self.data_manager)
                logger.info("✅ TelemetrySaver initialized successfully")
            except Exception as telemetry_error:
                logger.error(f"❌ Error initializing TelemetrySaver: {telemetry_error}")
                self.telemetry_saver = None
                
            # Create a Supabase client for lap saving
            try:
                from ..database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                if supabase_client:
                    logger.info("Created Supabase client for lap saving")
                else:
                    logger.warning("Failed to create Supabase client")
                    
                from .iracing_lap_saver import IRacingLapSaver
                self.iracing_lap_saver = IRacingLapSaver()
                if supabase_client:
                    self.iracing_lap_saver.set_supabase_client(supabase_client)
                    logger.info("Successfully passed Supabase client to IRacingLapSaver")
                else:
                    logger.warning("Could not pass Supabase client to IRacingLapSaver")
                logger.info("IRacingLapSaver initialized successfully")
                
                logger.info("🎯 IMMEDIATE SAVING AUTOMATICALLY ACTIVATED - Zero lag lap saving enabled!")
            except Exception as e:
                logger.error(f"Failed to initialize IRacingLapSaver: {e}")
                self.iracing_lap_saver = None
            
            # Create IRacingAPI
            try:
                logger.info("🔍 Attempting to initialize SimpleIRacingAPI...")
                from .simple_iracing import SimpleIRacingAPI
                self.iracing_api = SimpleIRacingAPI()
                
                logger.info("✅ SimpleIRacingAPI initialized successfully")
                logger.info(f"🔍 SimpleIRacingAPI object: {self.iracing_api}")
                logger.info(f"🔍 Has start_deferred_monitoring method: {hasattr(self.iracing_api, 'start_deferred_monitoring')}")
                
                # Connect the data manager to the API for telemetry saving
                if self.data_manager is not None:
                    try:
                        self.iracing_api.set_data_manager(self.data_manager)
                        logger.info("Connected data manager to SimpleIRacingAPI for telemetry saving")
                    except Exception as connect_error:
                        logger.error(f"Error connecting data manager to SimpleIRacingAPI: {connect_error}")
                
                # Connect the telemetry saver to the API
                if self.telemetry_saver is not None:
                    try:
                        self.iracing_api.set_telemetry_saver(self.telemetry_saver)
                        logger.info("Connected telemetry saver to SimpleIRacingAPI")
                    except Exception as ts_error:
                        logger.error(f"Error connecting telemetry saver to SimpleIRacingAPI: {ts_error}")
                
                # Connect the Supabase lap saver to the API
                if self.iracing_lap_saver is not None:
                    try:
                        from ..auth.user_manager import get_current_user
                        user = get_current_user()
                        if user and hasattr(user, 'id') and user.is_authenticated:
                            user_id = user.id
                            self.iracing_lap_saver.set_user_id(user_id)
                            logger.info(f"Set user ID for lap saver: {user_id}")

                            # Store the parameters needed to start monitoring later
                            self.iracing_api._deferred_monitor_params = {
                                'supabase_client': supabase_client,
                                'user_id': user_id,
                                'lap_saver': self.iracing_lap_saver
                            }
                            logger.info("✅ Deferred iRacing session monitor thread start until needed")
                            logger.info(f"🔍 Stored deferred params: supabase_client={supabase_client is not None}, user_id={user_id}, lap_saver={self.iracing_lap_saver is not None}")

                            if hasattr(self.iracing_api, '_session_info'):
                                self.iracing_api._session_info['user_id'] = user_id
                                logger.debug(f"Added user_id to session_info: {user_id}")
                        else:
                            logger.warning("No authenticated user available from auth module")
                    except Exception as user_error:
                        logger.error(f"Error getting current user for lap saver: {user_error}")
                    
                    try:
                        if hasattr(self.iracing_api, 'set_lap_saver'):
                            result = self.iracing_api.set_lap_saver(self.iracing_lap_saver)
                            if result:
                                logger.info("Successfully connected Supabase lap saver to SimpleIRacingAPI")
                            else:
                                logger.error("Failed to connect lap saver to SimpleIRacingAPI")
                    except Exception as ls_error:
                        logger.error(f"Error connecting Supabase lap saver to SimpleIRacingAPI: {ls_error}")
                
                # Set up API connections
                self._setup_iracing_api_connections()
                
                # Connect sector timing widget to iRacing API
                if hasattr(self, 'sector_timing_widget'):
                    self.sector_timing_widget.set_iracing_api(self.iracing_api)
                    logger.info("Connected sector timing widget to iRacing API")

                
            except Exception as simple_api_error:
                logger.error(f"Error initializing SimpleIRacingAPI: {simple_api_error}")
                # Fall back to original IRacingAPI if SimpleIRacingAPI fails
                try:
                    logger.info("Falling back to IRacingAPI...")
                    from .iracing_api import IRacingAPI
                    self.iracing_api = IRacingAPI()
                    logger.info("IRacingAPI initialized successfully")
                    self._setup_iracing_api_connections()
                except Exception as api_error:
                    logger.error(f"Error initializing IRacingAPI: {api_error}")
                    self.iracing_api = None
            
            # Mark lazy initialization as complete
            self._lazy_init_completed = True
            self._lazy_init_in_progress = False
            
            # Hide loading message
            if hasattr(self, 'loading_label'):
                self.loading_label.setVisible(False)
            
            logger.info("Lazy initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during lazy initialization: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._lazy_init_in_progress = False

    def setup_ui(self):
        """Set up the race coach UI components."""
        main_layout = QVBoxLayout(self)

        # Status bar at the top
        self.status_bar = QWidget()
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(5, 5, 5, 5)

        self.connection_label = QLabel("iRacing: Disconnected")
        self.connection_label.setStyleSheet(
            """
            color: red;
            font-weight: bold;
        """
        )
        status_layout.addWidget(self.connection_label)

        self.driver_label = QLabel("No Driver")
        status_layout.addWidget(self.driver_label)

        self.track_label = QLabel("No Track")
        status_layout.addWidget(self.track_label)

        status_layout.addStretch()

        # Add diagnostic mode toggle button
        self.diagnostic_mode_button = QPushButton("🔍 Diagnostics: OFF")
        self.diagnostic_mode_button.setStyleSheet(
            """
            background-color: #333;
            color: #AAA;
            padding: 5px 10px;
            border-radius: 3px;
        """
        )
        self.diagnostic_mode_button.setToolTip("Toggle detailed lap detection diagnostics")
        self.diagnostic_mode_button.clicked.connect(self.toggle_diagnostic_mode)
        status_layout.addWidget(self.diagnostic_mode_button)

        # Add lap debug button
        self.lap_debug_button = QPushButton("🏁 Lap Debug")
        self.lap_debug_button.setStyleSheet(
            """
            background-color: #333;
            color: #AAA;
            padding: 5px 10px;
            border-radius: 3px;
        """
        )
        self.lap_debug_button.setToolTip("View lap recording status and save partial laps")
        self.lap_debug_button.clicked.connect(self.show_lap_debug_dialog)
        status_layout.addWidget(self.lap_debug_button)

        main_layout.addWidget(self.status_bar)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #222;
                border-radius: 3px;
            }
            QTabBar::tab {
                background-color: #333;
                color: #CCC;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #444;
                color: white;
            }
        """
        )

        # Create the Overview Tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)

        # Add some basic information to the overview tab
        overview_info = QLabel("Race Coach Overview")
        overview_info.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            color: white;
            padding: 10px;
        """
        )
        overview_layout.addWidget(overview_info)

        # Add a simple dashboard to the overview tab
        dashboard_frame = QFrame()
        dashboard_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        dashboard_frame.setStyleSheet("background-color: #2D2D30; border-radius: 5px;")
        dashboard_layout = QVBoxLayout(dashboard_frame)

        # Create a descriptive text - update to remove mention of demo button
        dashboard_info = QLabel("Connect to iRacing to see telemetry visualization in the Telemetry tab.")
        dashboard_info.setWordWrap(True)
        dashboard_info.setStyleSheet("color: #CCC; font-size: 14px;")
        dashboard_layout.addWidget(dashboard_info)

        # Add dashboard to overview layout
        overview_layout.addWidget(dashboard_frame)

        overview_layout.addStretch()

        # Create the Telemetry Tab
        overview_layout.addStretch()

        # Create the Telemetry Tab
        telemetry_tab = QWidget()
        telemetry_layout = QVBoxLayout(telemetry_tab)
        telemetry_layout.setSpacing(8)  # Reduce the default spacing from 15 to 8
        telemetry_layout.setContentsMargins(8, 8, 8, 8)  # Reduce margins from 10 to 8

        # -------- Lap selection controls (Phase 2, Step 4) --------
        controls_frame = QFrame()  # Changed from lap_select_frame
        controls_layout = QGridLayout(controls_frame)  # Use GridLayout for better arrangement
        controls_layout.setContentsMargins(5, 5, 5, 5)
        controls_layout.setHorizontalSpacing(15)  # Add horizontal spacing

        # -- Row 0: Session Selection --
        session_label = QLabel("Session:")
        session_label.setStyleSheet("color:#DDD")
        self.session_combo = QComboBox()
        self.session_combo.setStyleSheet("background-color:#333;color:#EEE; padding: 3px;")
        self.session_combo.setMinimumWidth(400)  # Give session combo more space
        self.session_combo.currentIndexChanged.connect(self.on_session_changed)  # Connect signal

        self.refresh_button = QPushButton("🔄 Refresh All")  # Combined refresh button
        self.refresh_button.setToolTip("Refresh session and lap lists from database")
        self.refresh_button.setStyleSheet("padding: 5px 10px;")
        self.refresh_button.clicked.connect(self.refresh_session_and_lap_lists)  # Updated connection

        # Add iRacing connection reset button
        self.reset_connection_button = QPushButton("🔌 Reset iRacing")
        self.reset_connection_button.setToolTip("Reset iRacing connection if showing as disconnected")
        self.reset_connection_button.setStyleSheet("padding: 5px 10px; background-color: #444; color: #FFA500;")
        self.reset_connection_button.clicked.connect(self.reset_iracing_connection)

        controls_layout.addWidget(session_label, 0, 0)
        controls_layout.addWidget(self.session_combo, 0, 1)
        controls_layout.addWidget(self.refresh_button, 0, 2)
        controls_layout.addWidget(self.reset_connection_button, 0, 3)

        # Add warning label for incomplete lap data directly under the refresh button
        self.graph_status_label = QLabel()
        self.graph_status_label.setAlignment(Qt.AlignLeft)
        self.graph_status_label.setStyleSheet("color: #FFA500; font-weight: bold; padding-left: 10px;")
        self.graph_status_label.setVisible(False)  # Hidden by default
        controls_layout.addWidget(self.graph_status_label, 0, 5)

        # -- Row 1: Lap Selection --
        left_label = QLabel("Lap A:")
        left_label.setStyleSheet("color:#DDD")
        self.left_lap_combo = QComboBox()
        self.left_lap_combo.setStyleSheet("background-color:#333;color:#EEE; padding: 3px;")
        self.left_lap_combo.setMinimumWidth(200)
        self.left_lap_combo.currentIndexChanged.connect(self.on_lap_selection_changed)  # Add this line

        right_label = QLabel("Lap B:")
        right_label.setStyleSheet("color:#DDD")
        self.right_lap_combo = QComboBox()
        self.right_lap_combo.setStyleSheet("background-color:#333;color:#EEE; padding: 3px;")
        self.right_lap_combo.setMinimumWidth(200)
        self.right_lap_combo.currentIndexChanged.connect(self.on_lap_selection_changed)  # Add this line

        # Restore compare button (but keep it hidden)
        self.compare_button = QPushButton("Compare Laps")
        self.compare_button.setStyleSheet("padding: 5px 10px;")
        self.compare_button.clicked.connect(self.on_compare_clicked)
        self.compare_button.setVisible(False)  # Hide the compare button

        # Adjust the layout to keep controls closer together
        controls_layout.addWidget(left_label, 1, 0)
        controls_layout.addWidget(self.left_lap_combo, 1, 1)
        controls_layout.addWidget(right_label, 1, 2)
        controls_layout.addWidget(self.right_lap_combo, 1, 3, 1, 2)  # Span 2 columns for better spacing
        # Don't add the compare button to the layout since it's hidden
        # controls_layout.addWidget(self.compare_button, 1, 5)

        telemetry_layout.addWidget(controls_frame)  # Add the controls frame

        # Telemetry comparison widget
        self.telemetry_widget = TelemetryComparisonWidget(self)
        telemetry_layout.addWidget(self.telemetry_widget)

        # --- Loading Indicator (Phase 2 adjustment) ---
        self.loading_label = QLabel("🔄 Loading sessions...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #AAA; font-style: italic; padding: 10px;")
        self.loading_label.setVisible(False)  # Hidden initially
        telemetry_layout.insertWidget(1, self.loading_label)  # Insert below controls
        # --- End Loading Indicator ---

        # Add telemetry graph settings - common setup for proper scaling in small windows
        plot_settings = """
            padding-left: 5px;
            padding-right: 5px;
            padding-top: 5px;
            padding-bottom: 5px;
        """

        # UNIFORM SETTINGS FOR ALL GRAPHS
        uniform_min_height = 180  # New LARGER minimum height
        uniform_max_height = 200  # New LARGER maximum height
        uniform_spacing = 15
        uniform_margins = (5, 5, 5, 5)  # top, right, bottom, left
        uniform_stretch_factor = 1

        # Add throttle graph widget
        self.throttle_graph = ThrottleGraphWidget(self)
        self.throttle_graph.setMinimumHeight(uniform_min_height)
        self.throttle_graph.setMaximumHeight(uniform_max_height)
        self.throttle_graph.setContentsMargins(*uniform_margins)
        self.throttle_graph.setStyleSheet(
            f"border: 1px solid #444; border-radius: 4px; background-color: #222; {plot_settings}"
        )
        telemetry_layout.addWidget(self.throttle_graph, uniform_stretch_factor)

        telemetry_layout.addSpacing(uniform_spacing)

        # Add brake graph widget
        self.brake_graph = BrakeGraphWidget(self)
        self.brake_graph.setMinimumHeight(uniform_min_height)
        self.brake_graph.setMaximumHeight(uniform_max_height)
        self.brake_graph.setContentsMargins(*uniform_margins)
        self.brake_graph.setStyleSheet(
            f"border: 1px solid #444; border-radius: 4px; background-color: #222; {plot_settings}"
        )
        telemetry_layout.addWidget(self.brake_graph, uniform_stretch_factor)

        telemetry_layout.addSpacing(uniform_spacing)

        # Add the steering graph widget
        self.steering_graph = SteeringGraphWidget(self)
        self.steering_graph.setMinimumHeight(uniform_min_height)
        self.steering_graph.setMaximumHeight(uniform_max_height)
        self.steering_graph.setContentsMargins(*uniform_margins)
        self.steering_graph.setStyleSheet(
            f"border: 1px solid #444; border-radius: 4px; background-color: #222; {plot_settings}"
        )
        telemetry_layout.addWidget(self.steering_graph, uniform_stretch_factor)

        telemetry_layout.addSpacing(uniform_spacing)

        # Add the speed graph widget
        self.speed_graph = SpeedGraphWidget(self)
        self.speed_graph.setMinimumHeight(uniform_min_height)
        self.speed_graph.setMaximumHeight(uniform_max_height)
        self.speed_graph.setContentsMargins(*uniform_margins)
        self.speed_graph.setStyleSheet(
            f"border: 1px solid #444; border-radius: 4px; background-color: #222; {plot_settings}"
        )
        telemetry_layout.addWidget(self.speed_graph, uniform_stretch_factor)

        telemetry_layout.addSpacing(uniform_spacing)



        # Add a stretchable spacer at the end to push graphs together in small windows
        telemetry_layout.addStretch(1)  # Stretch factor 1 is fine here, can be 0 if preferred

        # Set size policies for all graphs to make them shrink/grow properly
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.throttle_graph.setSizePolicy(size_policy)
        self.brake_graph.setSizePolicy(size_policy)
        self.steering_graph.setSizePolicy(size_policy)
        self.speed_graph.setSizePolicy(size_policy)

        # Create the SuperLap Tab (replacing Live Telemetry) - with lazy loading
        superlap_tab = QWidget()  # Placeholder widget initially
        superlap_layout = QVBoxLayout(superlap_tab)
        superlap_placeholder = QLabel("SuperLap analysis will load when you switch to this tab")
        superlap_placeholder.setAlignment(Qt.AlignCenter)
        superlap_placeholder.setStyleSheet("color: #666; font-style: italic; padding: 50px;")
        superlap_layout.addWidget(superlap_placeholder)
        
        # Store reference for lazy loading later
        self._superlap_tab_widget = superlap_tab
        self._superlap_widget = None  # Will be created when needed

        # --- Loading Indicator (Phase 2 adjustment) ---
        self.loading_label = QLabel("🔄 Loading sessions...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #AAA; font-style: italic; padding: 10px;")
        self.loading_label.setVisible(False)  # Hidden initially
        telemetry_layout.insertWidget(1, self.loading_label)  # Insert below controls
        # --- End Loading Indicator ---

        # Create the Sector Timing Tab
        from trackpro.race_coach.widgets.sector_timing_widget import SectorTimingWidget
        self.sector_timing_widget = SectorTimingWidget(self)
        
        # Create the Videos Tab
        videos_tab = VideosTab(self)

        # Add tabs to the tab widget
        self.tab_widget.addTab(overview_tab, "Overview")
        self.tab_widget.addTab(telemetry_tab, "Telemetry")
        self.tab_widget.addTab(self.sector_timing_widget, "Sector Timing")
        self.tab_widget.addTab(superlap_tab, "SuperLap")
        self.tab_widget.addTab(videos_tab, "RaceFlix")  # Renamed tab

        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Connect tab change signal for lazy loading
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Initialize with demo data if not connected
        if not self.is_connected:
            # QTimer.singleShot(500, self.load_demo_data) # Demo data loading disabled
            pass




        # Save operation progress indicator
        self.save_progress_dialog = None

    def _on_tab_changed(self, index):
        """Handle tab changes to implement lazy loading for SuperLap tab."""
        try:
            # Check if this is the SuperLap tab (index 3, since we added Sector Timing at index 2)
            if index == 3 and self._superlap_widget is None:
                logger.info("SuperLap tab accessed for first time - creating widget asynchronously")
                
                # Check network connectivity first
                try:
                    from trackpro.database.supabase_client import supabase as main_supabase
                    if not main_supabase or not main_supabase.is_authenticated():
                        # Show offline message instead of trying to load
                        self._show_superlap_offline_message()
                        return
                except Exception as connectivity_error:
                    logger.warning(f"SuperLap: Network connectivity issue, showing offline mode: {connectivity_error}")
                    self._show_superlap_offline_message()
                    return
                
                # Create a loading placeholder first
                loading_widget = QWidget()
                loading_layout = QVBoxLayout(loading_widget)
                loading_label = QLabel("🔄 Loading SuperLap Analysis...")
                loading_label.setAlignment(Qt.AlignCenter)
                loading_label.setStyleSheet("color: #00ff88; font-size: 18px; font-weight: bold; padding: 50px;")
                loading_layout.addWidget(loading_label)
                
                # Replace placeholder with loading widget immediately
                while self._superlap_tab_widget.layout().count():
                    child = self._superlap_tab_widget.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                self._superlap_tab_widget.layout().addWidget(loading_widget)
                
                # Use QTimer to defer the actual widget creation to avoid blocking
                QTimer.singleShot(100, self._create_superlap_widget_deferred)
                
        except Exception as e:
            logger.error(f"Error in _on_tab_changed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _show_superlap_offline_message(self):
        """Show offline message for SuperLap tab."""
        try:
            offline_widget = QWidget()
            offline_layout = QVBoxLayout(offline_widget)
            offline_layout.setAlignment(Qt.AlignCenter)
            
            # Icon
            icon_label = QLabel("🌐")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 48px; margin-bottom: 20px;")
            offline_layout.addWidget(icon_label)
            
            # Title
            title_label = QLabel("SuperLap Analysis - Offline Mode")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("color: #ffaa00; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
            offline_layout.addWidget(title_label)
            
            # Message
            message_label = QLabel("SuperLap analysis requires an internet connection to access AI-powered lap optimization data.\n\nPlease check your connection and try again.")
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setStyleSheet("color: #cccccc; font-size: 14px; line-height: 1.5; padding: 20px;")
            message_label.setWordWrap(True)
            offline_layout.addWidget(message_label)
            
            # Retry button
            retry_button = QPushButton("Retry Connection")
            retry_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            retry_button.clicked.connect(self._retry_superlap_connection)
            offline_layout.addWidget(retry_button, 0, Qt.AlignCenter)
            
            # Replace placeholder with offline widget
            while self._superlap_tab_widget.layout().count():
                child = self._superlap_tab_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            self._superlap_tab_widget.layout().addWidget(offline_widget)
            
        except Exception as e:
            logger.error(f"Error showing SuperLap offline message: {e}")

    def _retry_superlap_connection(self):
        """Retry SuperLap connection."""
        try:
            # Reset the widget state
            self._superlap_widget = None
            
            # Trigger tab change again to retry loading
            self._on_tab_changed(3)  # SuperLap tab index (updated for new tab order)
            
        except Exception as e:
            logger.error(f"Error retrying SuperLap connection: {e}")

    def _create_superlap_widget_deferred(self):
        """Create the SuperLap widget in a deferred manner to avoid blocking the UI."""
        try:
            logger.info("Creating SuperLap widget in deferred execution")
            
            # Create the actual SuperLap widget
            self._superlap_widget = SuperLapWidget(self)
            
            # Replace the loading widget with the real widget
            while self._superlap_tab_widget.layout().count():
                child = self._superlap_tab_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # Add the real SuperLap widget
            self._superlap_tab_widget.layout().addWidget(self._superlap_widget)
            
            logger.info("SuperLap widget created and added to tab successfully")
            
        except Exception as e:
            logger.error(f"Error creating SuperLap widget: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Show error message in the tab
            error_widget = QWidget()
            error_layout = QVBoxLayout(error_widget)
            error_label = QLabel(f"❌ Error loading SuperLap: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #ff6666; font-size: 16px; padding: 50px;")
            error_layout.addWidget(error_label)
            
            # Replace with error widget
            while self._superlap_tab_widget.layout().count():
                child = self._superlap_tab_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            self._superlap_tab_widget.layout().addWidget(error_widget)

    def _update_telemetry(self, telemetry_data):
        """Process telemetry data and update visualizations."""
        if not telemetry_data or not isinstance(telemetry_data, dict):
            return
            
        # Log telemetry data periodically to check if it's being received properly
        if not hasattr(self, "_telemetry_log_count"):
            self._telemetry_log_count = 0
        
        self._telemetry_log_count += 1
        # Greatly reduce telemetry logging - only log every 10 minutes instead of every second
        if self._telemetry_log_count % 36000 == 0:  # Log once every 10 minutes at 60Hz
            logger.info(f"Telemetry update (10min): {telemetry_data.get('Lap', 'N/A')} laps, {telemetry_data.get('Speed', 0):.0f} speed")

        # Update input trace
        if hasattr(self, "input_trace") and telemetry_data:
            # Make sure we're using the right keys for the telemetry data
            throttle = telemetry_data.get("Throttle", telemetry_data.get("throttle", 0))
            brake = telemetry_data.get("Brake", telemetry_data.get("brake", 0))
            clutch = telemetry_data.get("Clutch", telemetry_data.get("clutch", 0))

            # Remove driver inputs logging completely - too verbose
            # if self._telemetry_log_count % 60 == 0:
            #     logger.info(f"Driver inputs: Throttle={throttle:.2f}, Brake={brake:.2f}, Clutch={clutch:.2f}")

            self.input_trace.add_data_point(throttle, brake, clutch)

            # Update current values and gauges
            speed = telemetry_data.get("Speed", telemetry_data.get("speed", 0))
            if isinstance(speed, (int, float)) and speed > 0:
                speed *= 3.6  # Convert to km/h

            rpm = telemetry_data.get("RPM", telemetry_data.get("rpm", 0))
            gear = telemetry_data.get("Gear", telemetry_data.get("gear", 0))
            gear_text = "R" if gear == -1 else "N" if gear == 0 else str(gear)
            lap = telemetry_data.get("Lap", telemetry_data.get("lap_count", 0))
            laptime = telemetry_data.get("LapCurrentLapTime", telemetry_data.get("lap_time", 0))

            # Get steering data - keys could be different depending on source
            steering = telemetry_data.get(
                "steering",
                telemetry_data.get(
                    "SteeringWheelAngle", telemetry_data.get("Steer", telemetry_data.get("steer", 0))
                ),
            )

            # Update text values
            self.speed_value.setText(f"{speed:.1f} km/h")
            self.throttle_value.setText(f"{throttle*100:.0f}%")
            self.brake_value.setText(f"{brake*100:.0f}%")
            self.clutch_value.setText(f"{(1-clutch)*100:.0f}%")  # Invert clutch for display
            self.gear_value.setText(gear_text)
            self.rpm_value.setText(f"{rpm:.0f}")
            self.lap_value.setText(str(lap))
            self.laptime_value.setText(self._format_time(laptime))

            # Update gauges
            if hasattr(self, "speed_gauge"):
                self.speed_gauge.set_value(speed)

            if hasattr(self, "rpm_gauge"):
                self.rpm_gauge.set_value(rpm)
                # Check if we have session info for redline
                if hasattr(self, "session_info") and "DriverInfo" in self.session_info:
                    driver_info = self.session_info["DriverInfo"]
                    if "DriverCarRedLine" in driver_info:
                        redline = driver_info["DriverCarRedLine"]
                        self.rpm_gauge.set_redline(redline)

            # Update steering wheel widget
            if hasattr(self, "steering_wheel"):
                # Normalize steering value to -1.0 to 1.0 range if needed
                # Some APIs provide steering in radians, others in a normalized range
                if abs(steering) > 1.0:
                    # Convert from radians to normalized value
                    # For 1080-degree wheels (3 full rotations), max rotation is 3*pi radians
                    # Use max rotation value from the SteeringWheelAngleMax if available,
                    # or calculate based on 1080 degrees (3*pi) as default for sim racing wheels
                    max_rotation = telemetry_data.get(
                        "SteeringWheelAngleMax", telemetry_data.get("steering_max", 3.0 * math.pi)
                    )

                    # Ensure max_rotation is positive and reasonable
                    if max_rotation > 0:
                        # Clamp steering angle to max_rotation to prevent bar overflow
                        clamped_steering = max(-max_rotation, min(max_rotation, steering))
                        steering_normalized = clamped_steering / max_rotation

                        # Make sure steering_normalized stays in [-1, 1] range
                        steering_normalized = max(-1.0, min(1.0, steering_normalized))

                        self.steering_wheel.set_max_rotation(max_rotation)
                        self.steering_wheel.set_value(steering_normalized)

                        # Remove steering logging - too verbose
                        # if self._telemetry_log_count % 60 == 0:
                        #     logger.info(
                        #         f"Steering (rad): {steering:.2f}, MaxRotation: {max_rotation:.2f}, "
                        #         + f"Normalized: {steering_normalized:.2f}, Clamped: {clamped_steering:.2f}"
                        #     )
                else:
                    # Already normalized between -1 and 1
                    # Still clamp to ensure it's within range
                    steering_normalized = max(-1.0, min(1.0, steering))
                    self.steering_wheel.set_value(steering_normalized)

                    # Remove steering logging - too verbose  
                    # if self._telemetry_log_count % 60 == 0:
                    #     logger.info(f"Steering (normalized): {steering_normalized:.2f}")

        # TODO: Process telemetry for telemetry comparison if needed

        try:
            # Extra try block to catch any unexpected exceptions during UI updates
            pass
        except Exception as e:
            logger.error(f"Error updating telemetry: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_iracing_connected(self, is_connected, session_info=None):
        """Handle connection status changes from iRacing API."""
        # This can still be called by the API's connection logic (e.g., via update_info_from_monitor)
        logger.info(f"UI: on_iracing_connected called with is_connected={is_connected}")
        self.is_connected = is_connected
        # No longer need to update session_info here, signal handler does it
        # if session_info:
        #     self.session_info = session_info
        self._update_connection_status()  # Update UI based on new connection state

    def on_session_info_changed(self, session_info):
        """(Legacy/Fallback) Handle session info changes from iRacing API callbacks."""
        logger.info("UI: on_session_info_changed (legacy callback) called.")
        self.session_info = session_info  # Store locally just in case
        # Let the signal handler _update_connection_status handle the UI update
        # self._update_session_info_ui(session_info)

    def _update_connection_status(self, payload: dict):
        """Update UI based on connection status and session info signal payload."""
        logger.debug(f"UI received update signal with payload: {payload}")
        # Extract info from the payload sent by the signal
        is_connected = payload.get("is_connected", False)
        session_info = payload.get("session_info", {})

        # Update internal state
        self.is_connected = is_connected
        self.session_info = session_info  # Store the latest info

        if self.is_connected:
            self.connection_label.setText("iRacing: Connected")
            self.connection_label.setStyleSheet("color: green; font-weight: bold;")

            # Get latest track/car/config from the received session_info dictionary
            track_name = session_info.get("current_track", "No Track")
            config_name = session_info.get("current_config")  # Get config name (might be None or empty)
            car_name = session_info.get("current_car", "No Car")
            # TODO: Get driver name if added to session_info
            driver_name = "N/A"  # Placeholder

            # Format track display text
            track_display_text = f"Track: {track_name}"
            if config_name and config_name != "Default":  # Don't show (Default)
                track_display_text += f" ({config_name})"  # Add config in parentheses if it exists

            # Also update any track-related fields in the main UI if they exist
            if hasattr(self, "track_info_label") and self.track_info_label:
                self.track_info_label.setText(track_display_text)

            # If there's a session header or title that displays track info, update it too
            if hasattr(self, "session_title_label") and self.session_title_label:
                session_type = session_info.get("session_type", "Session")
                self.session_title_label.setText(
                    f"{session_type} at {track_name}{' ('+config_name+')' if config_name and config_name != 'Default' else ''}"
                )

            # Update labels in the status bar
            self.track_label.setText(track_display_text)  # Ensure this is the correct label for the status bar
            self.driver_label.setText(f"Car: {car_name}")

        else:
            # Disconnected state
            self.connection_label.setText("iRacing: Disconnected")
            self.driver_label.setText("No Driver")
            self.track_label.setText("No Track")

            # Clear additional UI elements if they exist
            if hasattr(self, "track_info_label") and self.track_info_label:
                self.track_info_label.setText("No Track")

            if hasattr(self, "session_title_label") and self.session_title_label:
                self.session_title_label.setText("Not Connected")

    # def _update_session_info_ui(self, session_info):
    #    """(Deprecated) Update UI with session information."""
    #    # This logic is now merged into _update_connection_status
    #    pass

    def set_driver_data(self, is_left_driver, data):
        """Update driver data and refresh display.

        Args:
            is_left_driver: True for left driver, False for right driver
            data: Dictionary with driver data
        """
        driver = self.left_driver if is_left_driver else self.right_driver

        # Update driver data
        if "name" in data:
            name_parts = data["name"].split()
            if len(name_parts) > 1:
                driver["name"] = name_parts[0]
                driver["lastname"] = " ".join(name_parts[1:])
            else:
                driver["name"] = data["name"]
                driver["lastname"] = ""

        if "team" in data:
            driver["team"] = data["team"]

        if "position" in data:
            driver["position"] = data["position"]

        if "lap_time" in data:
            driver["lap_time"] = data["lap_time"]

        if "gap" in data:
            driver["gap"] = data["gap"]

        if "full_throttle" in data:
            driver["full_throttle"] = data["full_throttle"]

        if "heavy_braking" in data:
            driver["heavy_braking"] = data["heavy_braking"]

        if "cornering" in data:
            driver["cornering"] = data["cornering"]

        # Refresh UI
        self.update_driver_display(is_left_driver)

    def update_driver_display(self, is_left_driver):
        """Update the UI display for a driver.

        Args:
            is_left_driver: True for left driver, False for right driver
        """
        driver = self.left_driver if is_left_driver else self.right_driver

        if is_left_driver:
            # Update left driver display
            self.left_position_label.setText(str(driver["position"]))
            self.left_driver_name.setText(driver["name"].upper())
            self.left_driver_lastname.setText(driver["lastname"].upper())
            self.left_driver_team.setText(driver["team"].upper())

            # Format lap time as M:SS.MMM
            self.left_lap_time.setText(self._format_time(driver["lap_time"]))

            # Format gap
            if driver["gap"] <= 0:
                self.left_gap.setText(f"{driver['gap']:.3f}s")
            else:
                self.left_gap.setText(f"+{driver['gap']:.3f}s")

            # Update stats
            self.left_throttle_value.setText(f"{driver['full_throttle']}%")
            self.left_braking_value.setText(f"{driver['heavy_braking']}%")
            self.left_cornering_value.setText(f"{driver['cornering']}%")
        else:
            # Update right driver display
            self.right_position_label.setText(str(driver["position"]))
            self.right_driver_name.setText(driver["name"].upper())
            self.right_driver_lastname.setText(driver["lastname"].upper())
            self.right_driver_team.setText(driver["team"].upper())

            # Format lap time as M:SS.MMM
            self.right_lap_time.setText(self._format_time(driver["lap_time"]))

            # Format gap
            if driver["gap"] <= 0:
                self.right_gap.setText(f"{driver['gap']:.3f}s")
            else:
                self.right_gap.setText(f"+{driver['gap']:.3f}s")

            # Update stats
            self.right_throttle_value.setText(f"{driver['full_throttle']}%")
            self.right_braking_value.setText(f"{driver['heavy_braking']}%")
            self.right_cornering_value.setText(f"{driver['cornering']}%")

    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        minutes = int(time_in_seconds // 60)
        seconds = int(time_in_seconds % 60)
        milliseconds = int((time_in_seconds % 1) * 1000)
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"

    def _format_lap_display(self, lap_num, lap_time, lap_state=None):
        """Format lap number and time for display in UI, showing 'Out lap' instead of 'Lap 0'."""
        # Handle negative times (invalid laps) or None
        if lap_time is None or lap_time < 0:
            time_str = "(Invalid)"
        else:
            time_str = self._format_time(lap_time) if lap_time else "(No Time)"

        # Format special laps differently
        if lap_num == 0:
            base_display = f"Out lap  -  {time_str}"
        else:
            base_display = f"Lap {lap_num}  -  {time_str}"

        # Add lap state for debugging if provided
        if lap_state:
            base_display = f"{base_display}  -  {lap_state}"

        return base_display

    def set_speed_data(self, left_data, right_data):
        """Set the speed data for both drivers and update the child widget."""
        self.speed_data_left = left_data
        self.speed_data_right = right_data

        # Pass data to the child widget
        if hasattr(self, "speed_trace_widget"):
            self.speed_trace_widget.set_data(
                self.speed_data_left,
                self.speed_data_right,
                self.left_driver.get("color", QColor(255, 0, 0)),
                self.right_driver.get("color", QColor(255, 215, 0)),
                self.left_driver.get("name", "Driver 1"),
                self.right_driver.get("name", "Driver 2"),
            )

        # Auto analyze the telemetry when new data is set (if needed)
        # self.analyze_telemetry()
        self.update()  # Update parent widget if necessary

    def set_delta_data(self, delta_data):
        """Set the delta time data and update the child widget."""
        self.delta_data = delta_data

        # Pass data to the child widget
        if hasattr(self, "delta_widget"):
            self.delta_widget.set_data(delta_data)

        # Re-analyze with new delta data (if needed)
        # self.analyze_telemetry()
        self.update()  # Update parent widget if necessary

    def set_track_data(self, track_map_points, turn_data, sector_data):
        """Set the track map data.

        Args:
            track_map_points: List of (x, y) points defining the track outline
            turn_data: Dictionary mapping turn numbers to track positions
            sector_data: Dictionary defining speed sectors
        """
        self.track_map_points = track_map_points
        self.track_turns = turn_data
        self.track_sectors = sector_data
        self.update()

    def analyze_telemetry(self):
        """Analyze the speed data to generate enhanced telemetry visualization.

        This method:
        1. Identifies key sections of the track based on speed profiles
        2. Calculates sector-specific delta times
        3. Auto-categorizes track sections by speed (LOW/MEDIUM/HIGH)
        """
        if not hasattr(self, "speed_data_left") or not self.speed_data_left:
            return
        
        if not hasattr(self, "speed_data_right") or not self.speed_data_right:
            return

        # Normalize data lengths if needed
        min_length = min(len(self.speed_data_left), len(self.speed_data_right))
        if min_length == 0:
            return

        self.speed_data_left = self.speed_data_left[:min_length]
        self.speed_data_right = self.speed_data_right[:min_length]

        # Calculate the average speed at each point
        avg_speeds = [(self.speed_data_left[i] + self.speed_data_right[i]) / 2 for i in range(min_length)]

        # Find the max speed to determine thresholds
        max_speed = max(avg_speeds)

        # Define thresholds for speed categories
        low_speed_threshold = max_speed * 0.4  # Below 40% of max speed
        high_speed_threshold = max_speed * 0.8  # Above 80% of max speed

        # Identify continuous sections by speed category
        current_category = "MEDIUM SPEED"  # Default
        section_start = 0
        sections = []

        for i, speed in enumerate(avg_speeds):
            category = "MEDIUM SPEED"
            if speed < low_speed_threshold:
                category = "LOW SPEED"
            elif speed > high_speed_threshold:
                category = "HIGH SPEED"

            # If category changes, end the previous section
            if category != current_category or i == len(avg_speeds) - 1:
                sections.append(
                    {
                        "start": section_start,
                        "end": i - 1 if i < len(avg_speeds) - 1 else i,
                        "category": current_category,
                    }
                )
                section_start = i
                current_category = category

        # Combine small sections (less than 5% of track) with neighbors
        min_section_size = min_length * 0.05
        cleaned_sections = []
        i = 0

        while i < len(sections):
            section = sections[i]
            size = section["end"] - section["start"] + 1

            # If section is too small and not the only section
            if size < min_section_size and len(sections) > 1:
                # If not the first section, merge with previous
                if i > 0:
                    prev_section = cleaned_sections[-1]
                    prev_section["end"] = section["end"]
                # If last section, merge with next
                elif i < len(sections) - 1:
                    next_section = sections[i + 1]
                    next_section["start"] = section["start"]
                    cleaned_sections.append(next_section)
                    i += 1
            else:
                cleaned_sections.append(section)
            i += 1

        # Update the track sectors data structure
        self.track_sectors = {}

        for i, section in enumerate(cleaned_sections):
            start_idx = section["start"]
            end_idx = section["end"]
            category = section["category"]

            # Create track sector data
            # In a real implementation, we'd map this to actual track points
            self.track_sectors[i] = {
                "speed_category": category,
                "start_idx": start_idx,
                "end_idx": end_idx,
                "points": [],  # This would be filled with actual track points in a full implementation
            }

        # Now calculate delta time per section
        if hasattr(self, "delta_data") and self.delta_data:
            for sector_id, sector in self.track_sectors.items():
                start_idx = sector["start_idx"]
                end_idx = sector["end_idx"]

                if start_idx < len(self.delta_data) and end_idx < len(self.delta_data):
                    # Calculate delta gain/loss in this sector
                    sector_delta = self.delta_data[end_idx] - (self.delta_data[start_idx] if start_idx > 0 else 0)
                    self.track_sectors[sector_id]["delta"] = sector_delta

        self.update()  # Refresh the display

    def paintEvent(self, event):
        """Paint the comparison widget with real data.

        This will draw:
        1. Speed trace with custom rendering
        2. Track map (when implemented)
        3. Delta time graph
        """
        try:
            super().paintEvent(event)

            # Only proceed if we have data to display
            if not hasattr(self, "speed_data_left") or not hasattr(self, "speed_data_right"):
                return

            if not self.speed_data_left or not self.speed_data_right:
                return

            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Get widget dimensions
            width = self.width()
            height = self.height()

            # Draw track map in the center top area
            track_map_top = height * 0.05
            track_map_height = height * 0.45
            track_map_bottom = track_map_top + track_map_height
            track_map_left = width * 0.1  # Adjusted to use more width
            track_map_width = width * 0.8  # Increased width for track map
            track_map_right = track_map_left + track_map_width

            # Background for track map
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(25, 25, 25)))
            painter.drawRect(int(track_map_left), int(track_map_top), int(track_map_width), int(track_map_height))

            # Draw track outline if we have points
            if self.track_map_points:
                # Calculate scale and offset to fit track in view
                x_coords = [p[0] for p in self.track_map_points]
                y_coords = [p[1] for p in self.track_map_points]

                track_width = max(x_coords) - min(x_coords)
                track_height = max(y_coords) - min(y_coords)

                # Scale to fit with padding
                padding = 20
                scale_x = (track_map_width - padding * 2) / track_width if track_width > 0 else 1
                scale_y = (track_map_height - padding * 2) / track_height if track_height > 0 else 1
                scale = min(scale_x, scale_y)

                # Center the track
                offset_x = track_map_left + track_map_width / 2 - (max(x_coords) + min(x_coords)) * scale / 2
                offset_y = track_map_top + track_map_height / 2 - (max(y_coords) + min(y_coords)) * scale / 2

                # Draw track outline
                track_path = QPainterPath()
                first_point = True

                for x, y in self.track_map_points:
                    screen_x = offset_x + x * scale
                    screen_y = offset_y + y * scale

                    if first_point:
                        try:
                            track_path.moveTo(screen_x, screen_y)
                        except Exception as e:
                            # If our fallback implementation fails, draw directly
                            first_point_coords = (screen_x, screen_y)
                            polygon_points = [first_point_coords]
                            break
                        first_point = False
                    else:
                        try:
                            track_path.lineTo(screen_x, screen_y)
                        except Exception as e:
                            # If our fallback implementation fails, collect points for direct drawing
                            polygon_points.append((screen_x, screen_y))

                # Close the path
                try:
                    track_path.closeSubpath()

                    # Draw track outline
                    painter.setPen(QPen(QColor(100, 100, 100), 2))
                    painter.setBrush(QBrush(QColor(40, 40, 40)))
                    painter.drawPath(track_path)
                except Exception as e:
                    # Fallback: Draw as polygon if QPainterPath fails
                    if "polygon_points" in locals():
                        # Close the polygon
                        if polygon_points[0] != polygon_points[-1]:
                            polygon_points.append(polygon_points[0])

                        # Draw as lines
                        painter.setPen(QPen(QColor(100, 100, 100), 2))
                        painter.setBrush(QBrush(QColor(40, 40, 40)))

                        # Draw the polygon as a series of lines
                        for i in range(len(polygon_points) - 1):
                            painter.drawLine(
                                int(polygon_points[i][0]),
                                int(polygon_points[i][1]),
                                int(polygon_points[i + 1][0]),
                                int(polygon_points[i + 1][1]),
                            )

                # Draw speed sectors if available
                if hasattr(self, "track_sectors") and self.track_sectors:
                    # Define colors for different speed categories
                    speed_colors = {
                        "LOW": QColor(255, 0, 0, 60),  # Red with transparency
                        "MEDIUM": QColor(255, 165, 0, 60),  # Orange with transparency
                        "HIGH": QColor(0, 255, 0, 60),  # Green with transparency
                    }

                    # Draw each sector with appropriate color
                    for sector_id, sector_data in self.track_sectors.items():
                        if "speed_category" in sector_data and "points" in sector_data:
                            category = sector_data["speed_category"]
                            sector_points = sector_data["points"]

                            if category in speed_colors and len(sector_points) > 2:
                                # Create path for this sector
                                sector_path = QPainterPath()
                                first_point = True

                                for x, y in sector_points:
                                    screen_x = offset_x + x * scale
                                    screen_y = offset_y + y * scale

                                    if first_point:
                                        sector_path.moveTo(screen_x, screen_y)
                                        first_point = False
                                    else:
                                        sector_path.lineTo(screen_x, screen_y)

                                sector_path.closeSubpath()

                                # Draw colored sector
                                painter.setPen(Qt.NoPen)
                                painter.setBrush(QBrush(speed_colors[category]))
                                painter.drawPath(sector_path)

                # Draw turn markers and numbers if available
                if hasattr(self, "track_turns") and self.track_turns:
                    painter.setPen(QPen(QColor(255, 255, 255)))
                    painter.setFont(QFont("Arial", 8, QFont.Bold))

                    for turn_num, turn_data in self.track_turns.items():
                        if "position" in turn_data:
                            x, y = turn_data["position"]
                            screen_x = offset_x + x * scale
                            screen_y = offset_y + y * scale

                            # Draw turn marker
                            painter.setBrush(QBrush(QColor(200, 200, 200)))
                            painter.drawEllipse(int(screen_x - 3), int(screen_y - 3), 6, 6)

                            # Draw turn number
                            painter.drawText(int(screen_x + 5), int(screen_y + 3), str(turn_num))

            # Define areas for speed and delta graphs (These are now handled by child widgets)
            # speed_top = track_map_bottom + 20
            # speed_height = height * 0.25
            # speed_bottom = speed_top + speed_height

            # delta_top = speed_bottom + 10
            # delta_height = height * 0.15
            # delta_bottom = delta_top + delta_height

            # --- Speed and Delta graph drawing logic is now in child widgets ---
            # --- REMOVED all drawing code from here down related to speed/delta graphs ---

        except Exception as e:
            # Log error but don't crash the application
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error in TelemetryComparisonWidget.paintEvent: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def _update_lap_sync_debug(self, telemetry_data):
        """Update lap synchronization debug display to show iRacing vs. internal lap mapping.
        
        This display helps identify mismatches between iRacing's lap numbers and internal lap numbering,
        which is crucial for proper lap data recording and classification.
        
        Args:
            telemetry_data: Current telemetry data frame from iRacing
        """
        # Check if debug mode is enabled
        if not hasattr(self, "debug_mode"):
            self.debug_mode = True  # Enable debug by default for testing
            
        if not self.debug_mode:
            return
            
        # Create debug label if it doesn't exist
        if not hasattr(self, "lap_sync_debug_label"):
            self.lap_sync_debug_label = QLabel("Lap Sync: Initializing...")
            self.lap_sync_debug_label.setStyleSheet("color: #FFA500; font-size: 11px;")
            
            # Find a place to add it in the UI
            if hasattr(self, "debug_container"):
                # If we already have a debug container, add it there
                if hasattr(self, "debug_layout"):
                    self.debug_layout.addWidget(self.lap_sync_debug_label)
            else:
                # Create a container for debug info
                self.debug_container = QWidget()
                self.debug_layout = QVBoxLayout(self.debug_container)
                self.debug_layout.setContentsMargins(5, 2, 5, 2)
                self.debug_layout.addWidget(self.lap_sync_debug_label)
                
                # Add to the main layout - try different potential locations
                if hasattr(self, "main_layout"):
                    self.main_layout.addWidget(self.debug_container)
                elif hasattr(self, "telemetry_layout"):
                    self.telemetry_layout.addWidget(self.debug_container)
                elif hasattr(self, "status_layout"):
                    self.status_layout.addWidget(self.debug_container)
        
        # Extract relevant lap data from telemetry
        ir_lap = telemetry_data.get("Lap", -1)  # Current lap (N+1)
        ir_lap_completed = telemetry_data.get("LapCompleted", -1)  # Last completed lap (N)
        lap_dist = telemetry_data.get("LapDistPct", -1.0)
        lap_time = telemetry_data.get("LapCurrentLapTime", -1.0)
        lap_invalidated = telemetry_data.get("LapInvalidated", False)
        
        # Get internal lap info
        internal_lap = telemetry_data.get("internal_lap_number", ir_lap_completed)
        is_new_lap = telemetry_data.get("is_new_lap", False)
        completed_lap_number = telemetry_data.get("completed_lap_number", -1)
        
        # Get lap state if available
        lap_state = telemetry_data.get("lap_state", "UNKNOWN")
        
        # Format the debug text
        debug_text = (
            f"Lap Sync: iRacing [Lap={ir_lap}, Completed={ir_lap_completed}] -> "
            f"Internal [Current={internal_lap}, Last Completed={completed_lap_number}] | "
            f"Pos={lap_dist:.3f}, Time={lap_time:.2f}s"
        )
        
        # Check for sync issues
        if ir_lap_completed > 0 and ir_lap_completed != internal_lap and internal_lap > 0:
            diff = ir_lap_completed - internal_lap
            debug_text += f" | SYNC ISSUE: Off by {diff}"
            self.lap_sync_debug_label.setStyleSheet("color: #FF0000; font-size: 11px; font-weight: bold;")
        else:
            self.lap_sync_debug_label.setStyleSheet("color: #00FF00; font-size: 11px;")
        
        # Add lap state and validation status
        debug_text += f" | State: {lap_state}"
        if lap_invalidated:
            debug_text += " | INVALID"
            
        # Highlight new laps
        if is_new_lap:
            debug_text += " | NEW LAP"
        
        # Update the label
        self.lap_sync_debug_label.setText(debug_text)
        
        # Log to console for new laps or sync issues
        if is_new_lap or (ir_lap_completed > 0 and ir_lap_completed != internal_lap and internal_lap > 0):
            logger.info(f"[LAP SYNC DEBUG] {debug_text}")

    def on_telemetry_data(self, telemetry_data):
        """Handle telemetry data updates from iRacing API."""
        # First, update the existing telemetry visuals
        self._update_telemetry(telemetry_data)
        
        # Update lap synchronization debug display
        self._update_lap_sync_debug(telemetry_data)

        # Then feed telemetry to the monitor for coverage tracking
        # Convert the telemetry data format to the expected format for the monitor
        track_position = telemetry_data.get("track_position", telemetry_data.get("LapDist", 0))

        # Normalize track position if LapDist is used (convert from meters to 0-1 range)
        if "LapDist" in telemetry_data and "TrackLength" in telemetry_data:
            try:
                track_length = float(telemetry_data["TrackLength"])
                if track_length > 0:
                    track_position = float(telemetry_data["LapDist"]) / track_length
            except (ValueError, TypeError):
                pass

        # Create a telemetry point in our internal format
        telemetry_point = {
            "timestamp": telemetry_data.get("timestamp", time.time()),
            "track_position": track_position,
            "throttle": telemetry_data.get("Throttle", telemetry_data.get("throttle", 0)),
            "brake": telemetry_data.get("Brake", telemetry_data.get("brake", 0)),
            "steering": telemetry_data.get(
                "steering",
                telemetry_data.get("SteeringWheelAngle", telemetry_data.get("Steer", telemetry_data.get("steer", 0))),
            ),
            "speed": telemetry_data.get("Speed", telemetry_data.get("speed", 0)),
            "rpm": telemetry_data.get("RPM", telemetry_data.get("rpm", 0)),
            "gear": telemetry_data.get("Gear", telemetry_data.get("gear", 0)),
            "lap_number": telemetry_data.get("Lap", telemetry_data.get("lap_count", 0)),
        }

        # Add any other fields that might be useful
        for key, value in telemetry_data.items():
            if key not in telemetry_point and isinstance(value, (int, float, str, bool)):
                telemetry_point[key] = value

    def reset_iracing_connection(self):
        """Reset the iRacing connection manager and force a fresh connection attempt."""
        try:
            logger.info("🔄 Resetting iRacing connection manager...")
            print("🔄 Resetting iRacing connection manager...")
            
            # First, try to start deferred monitoring if we have the API
            if hasattr(self, 'iracing_api') and self.iracing_api:
                logger.info("🔍 Attempting to start deferred monitoring first...")
                try:
                    success = self.iracing_api.start_deferred_monitoring()
                    if success:
                        logger.info("✅ Deferred monitoring started successfully!")
                        print("✅ Deferred monitoring started successfully!")
                        QMessageBox.information(self, "Connection Reset", "iRacing monitoring started successfully!")
                        return
                    else:
                        logger.warning("⚠️ Deferred monitoring failed, trying connection manager...")
                        print("⚠️ Deferred monitoring failed, trying connection manager...")
                except Exception as e:
                    logger.error(f"❌ Error in deferred monitoring: {e}")
                    print(f"❌ Error in deferred monitoring: {e}")
            else:
                logger.warning("⚠️ No iRacing API available, trying connection manager...")
                print("⚠️ No iRacing API available, trying connection manager...")
            
            # Import the connection manager and monitor
            from trackpro.race_coach.connection_manager import iracing_connection_manager
            from trackpro.race_coach.iracing_session_monitor import _raw_iracing_connection
            
            # Register the connection function if not already registered
            iracing_connection_manager.register_connection_function(_raw_iracing_connection)
            logger.info("✅ Connection function registered")
            print("✅ Connection function registered")
            
            # Get current stats
            stats = iracing_connection_manager.get_connection_stats()
            logger.info(f"🔍 Current connection stats: {stats}")
            print(f"🔍 Current connection stats: {stats}")
            
            # Reset the backoff timer
            iracing_connection_manager.reset_backoff()
            logger.info("✅ Backoff timer reset successfully")
            print("✅ Backoff timer reset successfully")
            
            # Force a fresh connection attempt
            logger.info("🚀 Attempting fresh iRacing connection...")
            print("🚀 Attempting fresh iRacing connection...")
            result = iracing_connection_manager.attempt_connection()
            
            if result:
                logger.info("✅ Successfully connected to iRacing!")
                print("✅ Successfully connected to iRacing!")
                QMessageBox.information(self, "Connection Reset", "Successfully connected to iRacing!")
            else:
                logger.warning("❌ Failed to connect to iRacing")
                print("❌ Failed to connect to iRacing")
                QMessageBox.warning(self, "Connection Reset", "Failed to connect to iRacing.\nMake sure iRacing is running and you're in a session.")
                
            # Show updated stats
            new_stats = iracing_connection_manager.get_connection_stats()
            logger.info(f"🔍 Updated connection stats: {new_stats}")
            print(f"🔍 Updated connection stats: {new_stats}")
            
        except Exception as e:
            logger.error(f"❌ Error resetting connection: {e}")
            print(f"❌ Error resetting connection: {e}")
            QMessageBox.critical(self, "Error", f"Error resetting iRacing connection:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_diagnostic_mode(self):
        """Toggle diagnostic mode for detailed lap detection diagnostics."""
        if not hasattr(self, 'diagnostic_mode'):
            self.diagnostic_mode = False
        
        self.diagnostic_mode = not self.diagnostic_mode
        
        if self.diagnostic_mode:
            self.diagnostic_mode_button.setText("🔍 Diagnostics: ON")
            self.diagnostic_mode_button.setStyleSheet("""
                background-color: #4CAF50;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            """)
            logger.info("Diagnostic mode enabled - detailed lap detection logging activated")
        else:
            self.diagnostic_mode_button.setText("🔍 Diagnostics: OFF")
            self.diagnostic_mode_button.setStyleSheet("""
                background-color: #333;
                color: #AAA;
                padding: 5px 10px;
                border-radius: 3px;
            """)
            logger.info("Diagnostic mode disabled")
        
        # Update any lap saver instances if they exist
        if hasattr(self, 'iracing_lap_saver') and self.iracing_lap_saver:
            try:
                self.iracing_lap_saver.set_diagnostic_mode(self.diagnostic_mode)
            except Exception as e:
                logger.error(f"Error setting diagnostic mode on lap saver: {e}")

    def show_lap_debug_dialog(self):
        """Show lap recording status and debug information."""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Lap Debug Information")
            dialog.setModal(True)
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Create text area for debug info
            debug_text = QTextEdit()
            debug_text.setReadOnly(True)
            debug_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    border: 1px solid #444;
                }
            """)
            
            # Gather debug information
            debug_info = []
            debug_info.append("=== LAP DEBUG INFORMATION ===\n")
            debug_info.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Connection status
            debug_info.append(f"\n--- CONNECTION STATUS ---")
            debug_info.append(f"iRacing Connected: {self.is_connected}")
            debug_info.append(f"Session Info Available: {bool(self.session_info)}")
            
            if self.session_info:
                debug_info.append(f"Current Track: {self.session_info.get('current_track', 'Unknown')}")
                debug_info.append(f"Current Car: {self.session_info.get('current_car', 'Unknown')}")
                debug_info.append(f"Session Type: {self.session_info.get('session_type', 'Unknown')}")
            
            # Lap saver status
            debug_info.append(f"\n--- LAP SAVER STATUS ---")
            if hasattr(self, 'iracing_lap_saver') and self.iracing_lap_saver:
                try:
                    lap_saver_info = self.iracing_lap_saver.get_debug_info()
                    for key, value in lap_saver_info.items():
                        debug_info.append(f"{key}: {value}")
                except Exception as e:
                    debug_info.append(f"Error getting lap saver info: {e}")
            else:
                debug_info.append("Lap saver not initialized")
            
            # API status
            debug_info.append(f"\n--- API STATUS ---")
            if hasattr(self, 'iracing_api') and self.iracing_api:
                try:
                    api_info = self.iracing_api.get_debug_info() if hasattr(self.iracing_api, 'get_debug_info') else {}
                    if api_info:
                        for key, value in api_info.items():
                            debug_info.append(f"{key}: {value}")
                    else:
                        debug_info.append("API debug info not available")
                except Exception as e:
                    debug_info.append(f"Error getting API info: {e}")
            else:
                debug_info.append("iRacing API not initialized")
            
            # Diagnostic mode status
            debug_info.append(f"\n--- DIAGNOSTIC MODE ---")
            debug_info.append(f"Diagnostic Mode: {'ON' if getattr(self, 'diagnostic_mode', False) else 'OFF'}")
            
            debug_text.setText('\n'.join(debug_info))
            layout.addWidget(debug_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            refresh_button = QPushButton("Refresh")
            refresh_button.clicked.connect(lambda: self.show_lap_debug_dialog())
            refresh_button.clicked.connect(dialog.close)
            button_layout.addWidget(refresh_button)
            
            if hasattr(self, 'iracing_lap_saver') and self.iracing_lap_saver:
                save_partial_button = QPushButton("Save Partial Lap")
                save_partial_button.setToolTip("Force save current lap data even if incomplete")
                save_partial_button.clicked.connect(self.save_partial_lap)
                button_layout.addWidget(save_partial_button)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.close)
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing lap debug dialog: {e}")
            QMessageBox.critical(self, "Error", f"Error showing debug dialog:\n{str(e)}")

    def save_partial_lap(self):
        """Force save current partial lap data."""
        try:
            if hasattr(self, 'iracing_lap_saver') and self.iracing_lap_saver:
                result = self.iracing_lap_saver.force_save_current_lap()
                if result:
                    QMessageBox.information(self, "Partial Lap Saved", "Current lap data has been saved successfully.")
                else:
                    QMessageBox.warning(self, "Save Failed", "No lap data available to save or save operation failed.")
            else:
                QMessageBox.warning(self, "Not Available", "Lap saver not initialized.")
        except Exception as e:
            logger.error(f"Error saving partial lap: {e}")
            QMessageBox.critical(self, "Error", f"Error saving partial lap:\n{str(e)}")

    def refresh_session_and_lap_lists(self):
        """Refresh both session and lap lists from the database."""
        try:
            print(f"[MANUAL_DEBUG_V3] In refresh_session_and_lap_lists: hasattr(self, '_start_initial_data_loading') = {hasattr(self, '_start_initial_data_loading')}")
            logger.info("Refreshing session and lap lists...")
            
            # Show loading indicator
            if hasattr(self, 'loading_label'):
                self.loading_label.setVisible(True)
                self.loading_label.setText("🔄 Refreshing data...")
            
            # Clear existing data
            if hasattr(self, 'session_combo'):
                self.session_combo.clear()
                self.session_combo.addItem("Loading sessions...", None)
            
            if hasattr(self, 'left_lap_combo'):
                self.left_lap_combo.clear()
                self.left_lap_combo.addItem("Select session first", None)
            
            if hasattr(self, 'right_lap_combo'):
                self.right_lap_combo.clear()
                self.right_lap_combo.addItem("Select session first", None)
            
            # Start background loading
            self._start_initial_data_loading()
            
        except Exception as e:
            logger.error(f"Error refreshing session and lap lists: {e}")
            if hasattr(self, 'loading_label'):
                self.loading_label.setText("❌ Error refreshing data")

    def on_session_changed(self):
        """Handle session selection change."""
        try:
            if not hasattr(self, 'session_combo'):
                return
                
            current_session = self.session_combo.currentData()
            if current_session is None:
                return
                
            logger.info(f"Session changed to: {current_session.get('id', 'Unknown')}")
            
            # Clear lap combos
            if hasattr(self, 'left_lap_combo'):
                self.left_lap_combo.clear()
                self.left_lap_combo.addItem("Loading laps...", None)
            
            if hasattr(self, 'right_lap_combo'):
                self.right_lap_combo.clear()
                self.right_lap_combo.addItem("Loading laps...", None)
            
            # Load laps for this session
            self._load_laps_for_session(current_session.get('id'))
            
        except Exception as e:
            logger.error(f"Error handling session change: {e}")

    def on_lap_selection_changed(self):
        """Handle lap selection change for comparison."""
        try:
            if not hasattr(self, 'left_lap_combo') or not hasattr(self, 'right_lap_combo'):
                return
                
            left_lap = self.left_lap_combo.currentData()
            right_lap = self.right_lap_combo.currentData()
            
            # Auto-compare when both laps are selected
            if left_lap is not None and right_lap is not None:
                logger.info(f"Auto-comparing laps: {left_lap} vs {right_lap}")
                self._compare_laps(left_lap, right_lap)
            
        except Exception as e:
            logger.error(f"Error handling lap selection change: {e}")

    def on_compare_clicked(self):
        """Handle compare button click."""
        try:
            if not hasattr(self, 'left_lap_combo') or not hasattr(self, 'right_lap_combo'):
                return
                
            left_lap = self.left_lap_combo.currentData()
            right_lap = self.right_lap_combo.currentData()
            
            if left_lap is None or right_lap is None:
                QMessageBox.warning(self, "Selection Required", "Please select both laps to compare.")
                return
                
            self._compare_laps(left_lap, right_lap)
            
        except Exception as e:
            logger.error(f"Error comparing laps: {e}")
            QMessageBox.critical(self, "Error", f"Error comparing laps:\n{str(e)}")
    def _start_initial_data_loading(self):
        """Start loading initial session and lap data in background."""
        try:
            # Prevent multiple simultaneous loads
            if hasattr(self, '_initial_load_in_progress') and self._initial_load_in_progress:
                logger.info("Initial data loading already in progress, skipping duplicate request")
                return
                
            self._initial_load_in_progress = True
            
            # Create and start worker thread
            self.initial_load_thread = QThread()
            self.initial_load_worker = InitialLoadWorker()
            self.initial_load_worker.moveToThread(self.initial_load_thread)
            
            # Connect signals
            self.initial_load_thread.started.connect(self.initial_load_worker.run)
            self.initial_load_worker.sessions_loaded.connect(self._on_sessions_loaded)
            self.initial_load_worker.laps_loaded.connect(self._on_laps_loaded)
            self.initial_load_worker.error.connect(self._on_initial_load_error)
            self.initial_load_worker.finished.connect(self.initial_load_thread.quit)
            self.initial_load_worker.finished.connect(self.initial_load_worker.deleteLater)
            self.initial_load_thread.finished.connect(self.initial_load_thread.deleteLater)
            self.initial_load_thread.finished.connect(self._on_initial_load_finished)
            
            # Start the thread
            self.initial_load_thread.start()
            logger.info("Started initial data loading thread")
            
        except Exception as e:
            logger.error(f"Error starting initial data loading: {e}")
            self._initial_load_in_progress = False

    def _on_sessions_loaded(self, sessions, message):
        """Handle loaded sessions from worker thread."""
        try:
            if hasattr(self, 'session_combo'):
                self.session_combo.clear()
                
                if sessions:
                    for session in sessions:
                        display_text = self._format_session_display(session)
                        self.session_combo.addItem(display_text, session)
                    
                    # Select first session by default
                    if self.session_combo.count() > 0:
                        self.session_combo.setCurrentIndex(0)
                        self.on_session_changed()
                else:
                    self.session_combo.addItem("No sessions found", None)
                    
            logger.info(f"Loaded {len(sessions) if sessions else 0} sessions")
            
        except Exception as e:
            logger.error(f"Error handling loaded sessions: {e}")

    def _on_laps_loaded(self, laps, message):
        """Handle loaded laps from worker thread."""
        try:
            if hasattr(self, 'left_lap_combo') and hasattr(self, 'right_lap_combo'):
                self.left_lap_combo.clear()
                self.right_lap_combo.clear()
                
                if laps:
                    for lap in laps:
                        display_text = self._format_lap_display(
                            lap.get('lap_number', 0),
                            lap.get('lap_time', 0),
                            lap.get('is_valid', True)
                        )
                        self.left_lap_combo.addItem(display_text, lap.get('id'))
                        self.right_lap_combo.addItem(display_text, lap.get('id'))
                else:
                    self.left_lap_combo.addItem("No laps found", None)
                    self.right_lap_combo.addItem("No laps found", None)
                    
            logger.info(f"Loaded {len(laps) if laps else 0} laps")
            
        except Exception as e:
            logger.error(f"Error handling loaded laps: {e}")

    def _on_initial_load_error(self, error_message):
        """Handle initial load errors."""
        logger.error(f"Initial load error: {error_message}")
        if hasattr(self, 'loading_label'):
            self.loading_label.setText(f"❌ Error: {error_message}")

    def _on_initial_load_finished(self):
        """Handle initial load completion."""
        self._initial_load_in_progress = False
        if hasattr(self, 'loading_label'):
            self.loading_label.setVisible(False)
        logger.info("Initial data loading completed")

    def _format_session_display(self, session):
        """Format session data for display in combo box."""
        try:
            track_name = session.get('track_name', 'Unknown Track')
            car_name = session.get('car_name', 'Unknown Car')
            session_date = session.get('session_date', session.get('created_at', ''))
            
            if session_date:
                try:
                    from datetime import datetime
                    if 'T' in session_date:
                        dt = datetime.fromisoformat(session_date.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        date_str = session_date[:16]  # Truncate to reasonable length
                except:
                    date_str = session_date[:16]
            else:
                date_str = "Unknown Date"
                
            return f"{date_str} - {track_name} ({car_name})"
            
        except Exception as e:
            logger.error(f"Error formatting session display: {e}")
            return f"Session {session.get('id', 'Unknown')}"

    def _load_laps_for_session(self, session_id):
        """Load laps for a specific session."""
        try:
            if not session_id:
                logger.warning("No session ID provided for lap loading")
                if hasattr(self, 'left_lap_combo') and hasattr(self, 'right_lap_combo'):
                    self.left_lap_combo.clear()
                    self.right_lap_combo.clear()
                    self.left_lap_combo.addItem("No session selected", None)
                    self.right_lap_combo.addItem("No session selected", None)
                return
                
            logger.info(f"Loading laps for session: {session_id}")
            
            # Use the existing get_laps function to query for laps for this specific session
            try:
                laps, msg_laps = get_laps(limit=50, user_only=True, session_id=session_id)
                
                if hasattr(self, 'left_lap_combo') and hasattr(self, 'right_lap_combo'):
                    self.left_lap_combo.clear()
                    self.right_lap_combo.clear()
                    
                    if laps:
                        for lap in laps:
                            display_text = self._format_lap_display(
                                lap.get('lap_number', 0),
                                lap.get('lap_time', 0),
                                lap.get('is_valid', True)
                            )
                            self.left_lap_combo.addItem(display_text, lap.get('id'))
                            self.right_lap_combo.addItem(display_text, lap.get('id'))
                        
                        # Auto-select first two laps for comparison if available
                        if len(laps) >= 2:
                            self.left_lap_combo.setCurrentIndex(0)
                            self.right_lap_combo.setCurrentIndex(1)
                            self.on_lap_selection_changed()
                        elif len(laps) == 1:
                            self.left_lap_combo.setCurrentIndex(0)
                            self.right_lap_combo.setCurrentIndex(0)
                            self.on_lap_selection_changed()
                        
                        logger.info(f"Successfully loaded {len(laps)} laps for session {session_id}")
                    else:
                        self.left_lap_combo.addItem("No laps found for this session", None)
                        self.right_lap_combo.addItem("No laps found for this session", None)
                        logger.info(f"No laps found for session {session_id}")
                        
            except Exception as query_error:
                logger.error(f"Error querying laps for session {session_id}: {query_error}")
                if hasattr(self, 'left_lap_combo') and hasattr(self, 'right_lap_combo'):
                    self.left_lap_combo.clear()
                    self.right_lap_combo.clear()
                    self.left_lap_combo.addItem("Error loading laps", None)
                    self.right_lap_combo.addItem("Error loading laps", None)
            
        except Exception as e:
            logger.error(f"Error loading laps for session {session_id}: {e}")
            if hasattr(self, 'left_lap_combo') and hasattr(self, 'right_lap_combo'):
                self.left_lap_combo.clear()
                self.right_lap_combo.clear()
                self.left_lap_combo.addItem("Error loading laps", None)
                self.right_lap_combo.addItem("Error loading laps", None)

    def _simulate_lap_loading(self, session_id):
        """REMOVED: This placeholder method was causing the 'No laps available' issue.
        
        This method has been removed because it was a placeholder that always showed
        "No laps available" regardless of whether laps actually existed for the session.
        The proper lap loading is now handled directly in _load_laps_for_session.
        """
        logger.info(f"_simulate_lap_loading called but this method has been disabled - proper lap loading now handled by _load_laps_for_session for session {session_id}")
        # This method is now a no-op to prevent the "No laps available" issue
        pass

    def _compare_laps(self, left_lap_id, right_lap_id):
        """Compare two laps and update telemetry visualization."""
        try:
            logger.info(f"Comparing laps: {left_lap_id} vs {right_lap_id}")
            
            if left_lap_id is None or right_lap_id is None:
                logger.warning("Cannot compare laps - one or both lap IDs are None")
                return
            
            # Show loading status
            if hasattr(self, 'graph_status_label'):
                self.graph_status_label.setText("Loading telemetry data...")
                self.graph_status_label.setVisible(True)
            
            # Cancel any existing telemetry fetch operation
            if self.telemetry_fetch_thread is not None and self.telemetry_fetch_thread.isRunning():
                if hasattr(self.telemetry_fetch_worker, 'cancel'):
                    self.telemetry_fetch_worker.cancel()
                self.telemetry_fetch_thread.quit()
                self.telemetry_fetch_thread.wait(1000)  # Wait up to 1 second
            
            # Create and start worker thread to load telemetry data
            self.telemetry_fetch_thread = QThread()
            self.telemetry_fetch_worker = TelemetryFetchWorker(left_lap_id, right_lap_id)
            self.telemetry_fetch_worker.moveToThread(self.telemetry_fetch_thread)
            
            # Connect signals
            self.telemetry_fetch_thread.started.connect(self.telemetry_fetch_worker.run)
            self.telemetry_fetch_worker.finished.connect(self._on_telemetry_loaded)
            self.telemetry_fetch_worker.error.connect(self._on_telemetry_error)
            self.telemetry_fetch_worker.finished.connect(self.telemetry_fetch_thread.quit)
            self.telemetry_fetch_worker.finished.connect(self.telemetry_fetch_worker.deleteLater)
            self.telemetry_fetch_thread.finished.connect(self.telemetry_fetch_thread.deleteLater)
            
            # Start the thread
            self.telemetry_fetch_thread.start()
            logger.info(f"Started telemetry fetch for laps {left_lap_id} and {right_lap_id}")
            
        except Exception as e:
            logger.error(f"Error comparing laps: {e}")
            if hasattr(self, 'graph_status_label'):
                self.graph_status_label.setText(f"Error loading data: {str(e)}")
                self.graph_status_label.setVisible(True)
                QTimer.singleShot(3000, lambda: self.graph_status_label.setVisible(False))

    def get_track_length(self):
        """Get the current track length in meters."""
        # Try to get track length from session info
        if hasattr(self, "session_info") and self.session_info:
            track_length = self.session_info.get("track_length", 0)
            if track_length > 0:
                return track_length

        # Fall back to checking context of currently loaded data
        if hasattr(self, "throttle_graph") and hasattr(self.throttle_graph, "track_length"):
            graph_track_length = self.throttle_graph.track_length
            if graph_track_length > 0:
                return graph_track_length

        # Default value if we can't find track length anywhere
        return 1000  # 1000 meters default

    def _on_telemetry_loaded(self, left_data, right_data):
        """Handle loaded telemetry data and update graphs."""
        try:
            logger.info("Telemetry data loaded successfully, updating graphs...")
        
            # Hide loading status
            if hasattr(self, 'graph_status_label'):
                self.graph_status_label.setVisible(False)
        
            # Check if we have valid data
            if not left_data or not right_data:
                logger.warning("No telemetry data received")
                if hasattr(self, 'graph_status_label'):
                    self.graph_status_label.setText("No telemetry data available")
                    self.graph_status_label.setVisible(True)
                    QTimer.singleShot(3000, lambda: self.graph_status_label.setVisible(False))
                return
        
            # Extract telemetry points from the data
            left_points = left_data.get('points', []) if isinstance(left_data, dict) else left_data
            right_points = right_data.get('points', []) if isinstance(right_data, dict) else right_data
        
            logger.info(f"Processing {len(left_points)} left points and {len(right_points)} right points")
        
            # Get track length from session data or lap data
            track_length = self.get_track_length()
            if not track_length:
                logger.warning("No track length available, using default")
                track_length = 1000  # Default fallback
        
            # Update all graph widgets with comparison data using the correct method
            try:
                if hasattr(self, 'throttle_graph') and self.throttle_graph:
                    self.throttle_graph.update_graph_comparison(left_data, right_data, track_length)
                    logger.info("Updated throttle graph")
            
                if hasattr(self, 'brake_graph') and self.brake_graph:
                    self.brake_graph.update_graph_comparison(left_data, right_data, track_length)
                    logger.info("Updated brake graph")
            
                if hasattr(self, 'steering_graph') and self.steering_graph:
                    self.steering_graph.update_graph_comparison(left_data, right_data, track_length)
                    logger.info("Updated steering graph")
            
                if hasattr(self, 'speed_graph') and self.speed_graph:
                    self.speed_graph.update_graph_comparison(left_data, right_data, track_length)
                    logger.info("Updated speed graph")
            
                logger.info("All graphs updated successfully!")
            
            except Exception as graph_error:
                logger.error(f"Error updating graphs: {graph_error}")
                import traceback
                logger.error(traceback.format_exc())
                if hasattr(self, 'graph_status_label'):
                    self.graph_status_label.setText(f"Error updating graphs: {graph_error}")
                    self.graph_status_label.setVisible(True)
                
        except Exception as e:
            logger.error(f"Error handling loaded telemetry: {e}")
            import traceback
            logger.error(traceback.format_exc())
            if hasattr(self, 'graph_status_label'):
                self.graph_status_label.setText(f"Error processing data: {str(e)}")
                self.graph_status_label.setVisible(True)
                QTimer.singleShot(5000, lambda: self.graph_status_label.setVisible(False))

    def _on_telemetry_error(self, left_error, right_error):
        """Handle telemetry loading errors."""
        logger.error(f"Telemetry loading error - Left: {left_error}, Right: {right_error}")
        
        if hasattr(self, 'graph_status_label'):
            error_msg = "Failed to load telemetry data"
            if left_error and right_error:
                error_msg = f"Error loading both laps: {left_error}"
            elif left_error:
                error_msg = f"Error loading Lap A: {left_error}"
            elif right_error:
                error_msg = f"Error loading Lap B: {right_error}"
            
            self.graph_status_label.setText(error_msg)
            self.graph_status_label.setVisible(True)
            QTimer.singleShot(5000, lambda: self.graph_status_label.setVisible(False))
