"""App tracking utility for TrackPro - tracks online status and sessions via Supabase."""

import asyncio
import json
import platform
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading
import logging

from trackpro.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class AppTracker:
    """Tracks TrackPro app status and sessions via Supabase."""
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.supabase = get_supabase_client()
        self.session_id = str(uuid.uuid4())
        self.is_running = False
        self.heartbeat_thread = None
        self.heartbeat_interval = 30  # seconds
        
        # Get app info
        self.app_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "app_version": "1.5.6",  # Update this with your actual version
        }
    
    def start_session(self, user_id: Optional[str] = None) -> bool:
        """Start tracking a new app session."""
        try:
            # Set user_id if provided
            if user_id:
                self.user_id = user_id
                logger.info(f"Starting app session with user_id: {user_id}")
            else:
                logger.warning("No user_id provided for app session - will run in anonymous mode")
            
            # Check if Supabase client is available
            if not self.supabase:
                logger.warning("Supabase client not available - skipping app tracking")
                return False
            
            # Insert session start
            session_data = {
                "user_id": self.user_id,  # This can be None for anonymous sessions
                "session_start": datetime.utcnow().isoformat(),
                "app_version": self.app_info["app_version"],
                "platform": self.app_info["platform"],
                "device_info": self.app_info,
                "is_active": True
            }
            
            result = self.supabase.table("app_sessions").insert(session_data).execute()
            
            if result.data:
                logger.info(f"Started app session tracking for user {self.user_id}")
                self.is_running = True
                
                # Start heartbeat if user is logged in
                if self.user_id:
                    self._start_heartbeat()
                    # Also update online status immediately
                    self.update_online_status(True)
                
                return True
            else:
                logger.error("Failed to start app session tracking")
                return False
                
        except Exception as e:
            logger.error(f"Error starting app session: {e}")
            return False
    
    def end_session(self) -> bool:
        """End the current app session."""
        try:
            if not self.is_running:
                return True
            
            # Update session end time
            update_data = {
                "session_end": datetime.utcnow().isoformat(),
                "is_active": False
            }
            
            # Find the active session for this user
            result = self.supabase.table("app_sessions").update(update_data).eq(
                "user_id", self.user_id
            ).eq("is_active", True).execute()
            
            # Stop heartbeat
            self._stop_heartbeat()
            self.is_running = False
            
            logger.info(f"Ended app session for user {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error ending app session: {e}")
            return False
    
    def update_user_id(self, user_id: str) -> bool:
        """Update the user_id for an existing session (when user logs in)."""
        try:
            if not user_id:
                logger.warning("No user_id provided for update")
                return False
            
            old_user_id = self.user_id
            self.user_id = user_id
            
            logger.info(f"Updated user_id from {old_user_id} to {user_id}")
            
            # Update the current session with the new user_id
            if self.is_running:
                try:
                    # Update the active session
                    update_data = {"user_id": user_id}
                    result = self.supabase.table("app_sessions").update(update_data).eq(
                        "session_id", self.session_id
                    ).eq("is_active", True).execute()
                    
                    if result.data:
                        logger.info(f"Updated session with user_id: {user_id}")
                        
                        # Start heartbeat for the authenticated user
                        self._start_heartbeat()
                        
                        # Update online status
                        self.update_online_status(True)
                        
                        return True
                    else:
                        logger.warning("Failed to update session with user_id")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error updating session with user_id: {e}")
                    return False
            else:
                # If session is not running, start a new session for the authenticated user
                logger.info(f"Starting new session for authenticated user: {user_id}")
                return self.start_session(user_id)
            
        except Exception as e:
            logger.error(f"Error updating user_id: {e}")
            return False

    def update_online_status(self, is_online: bool = True) -> bool:
        """Update user's online status."""
        try:
            if not self.user_id:
                return False
            
            # Check if Supabase client is available
            if not self.supabase:
                logger.warning("Supabase client not available - skipping online status update")
                return False
            
            status_data = {
                "user_id": self.user_id,
                "is_online": is_online,
                "last_seen": datetime.utcnow().isoformat(),
                "app_version": self.app_info["app_version"],
                "platform": self.app_info["platform"],
                "device_info": self.app_info
            }
            
            # Upsert online status
            result = self.supabase.table("online_status").upsert(status_data).execute()
            
            if result.data:
                logger.debug(f"Updated online status: {is_online} for user {self.user_id}")
                return True
            else:
                logger.error("Failed to update online status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating online status: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send a heartbeat to indicate the app is still running."""
        try:
            if not self.user_id:
                return False
            
            # Check if Supabase client is available
            if not self.supabase:
                logger.warning("Supabase client not available - skipping heartbeat")
                return False
            
            heartbeat_data = {
                "user_id": self.user_id,
                "heartbeat_time": datetime.utcnow().isoformat(),
                "app_version": self.app_info["app_version"],
                "platform": self.app_info["platform"],
                "device_info": self.app_info,
                "session_id": self.session_id
            }
            
            result = self.supabase.table("app_heartbeats").insert(heartbeat_data).execute()
            
            if result.data:
                logger.debug(f"Sent heartbeat for user {self.user_id}")
                return True
            else:
                logger.error("Failed to send heartbeat")
                return False
                
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False
    
    def _start_heartbeat(self):
        """Start the heartbeat thread."""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logger.info("Started heartbeat thread")
    
    def _stop_heartbeat(self):
        """Stop the heartbeat thread."""
        self.is_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        logger.info("Stopped heartbeat thread")
    
    def _heartbeat_loop(self):
        """Heartbeat loop that runs in a separate thread."""
        logger.info(f"💓 Heartbeat loop started for user {self.user_id}")
        while self.is_running:
            try:
                # Send heartbeat
                heartbeat_success = self.send_heartbeat()
                
                # Update online status
                status_success = self.update_online_status(True)
                
                if heartbeat_success and status_success:
                    logger.debug(f"💓 Heartbeat sent successfully for user {self.user_id}")
                else:
                    logger.warning(f"💓 Heartbeat failed for user {self.user_id} - heartbeat: {heartbeat_success}, status: {status_success}")
                
                # Wait for next heartbeat
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info(f"💓 Heartbeat loop stopped for user {self.user_id}")
    
    def get_online_users(self) -> list:
        """Get list of currently online users."""
        try:
            # Check if Supabase client is available
            if not self.supabase:
                logger.warning("Supabase client not available - returning empty online users list")
                return []
            
            # Get users online in the last 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            result = self.supabase.table("online_status").select(
                "user_id, last_seen, app_version, platform"
            ).gte("last_seen", cutoff_time.isoformat()).eq("is_online", True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return []
    
    def get_user_session_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get session statistics for a user."""
        try:
            target_user = user_id or self.user_id
            if not target_user:
                return {}
            
            # Check if Supabase client is available
            if not self.supabase:
                logger.warning("Supabase client not available - returning empty session stats")
                return {}
            
            # Get total sessions
            sessions_result = self.supabase.table("app_sessions").select(
                "session_start, session_end, is_active"
            ).eq("user_id", target_user).execute()
            
            sessions = sessions_result.data if sessions_result.data else []
            
            # Calculate stats
            total_sessions = len(sessions)
            active_sessions = len([s for s in sessions if s.get("is_active", False)])
            
            total_duration = 0
            for session in sessions:
                start = datetime.fromisoformat(session["session_start"].replace("Z", "+00:00"))
                end = session.get("session_end")
                if end:
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    total_duration += (end_dt - start).total_seconds()
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_duration_hours": round(total_duration / 3600, 2),
                "last_session": sessions[-1]["session_start"] if sessions else None
            }
            
        except Exception as e:
            logger.error(f"Error getting user session stats: {e}")
            return {}


# Global app tracker instance
_app_tracker: Optional[AppTracker] = None


def get_app_tracker(user_id: Optional[str] = None) -> AppTracker:
    """Get or create the global app tracker instance."""
    global _app_tracker
    
    if _app_tracker is None:
        _app_tracker = AppTracker(user_id)
    
    return _app_tracker


def start_app_tracking(user_id: Optional[str] = None) -> bool:
    """Start tracking the app session."""
    tracker = get_app_tracker(user_id)
    return tracker.start_session(user_id)


def stop_app_tracking() -> bool:
    """Stop tracking the app session."""
    global _app_tracker
    
    if _app_tracker:
        success = _app_tracker.end_session()
        _app_tracker = None
        return success
    
    return True


def update_user_online_status(user_id: str, is_online: bool = True) -> bool:
    """Update a user's online status."""
    tracker = get_app_tracker(user_id)
    return tracker.update_online_status(is_online)

def force_heartbeat(user_id: str) -> bool:
    """Force a heartbeat for testing purposes."""
    tracker = get_app_tracker(user_id)
    if tracker.user_id:
        logger.info(f"💓 Forcing heartbeat for user {user_id}")
        heartbeat_success = tracker.send_heartbeat()
        status_success = tracker.update_online_status(True)
        return heartbeat_success and status_success
    return False

def get_heartbeat_status(user_id: str) -> Dict[str, Any]:
    """Get heartbeat status for a user."""
    tracker = get_app_tracker(user_id)
    return {
        "user_id": tracker.user_id,
        "is_running": tracker.is_running,
        "heartbeat_thread_alive": tracker.heartbeat_thread.is_alive() if tracker.heartbeat_thread else False,
        "session_id": tracker.session_id,
        "heartbeat_interval": tracker.heartbeat_interval
    }


def update_app_tracker_user_id(user_id: str) -> bool:
    """Update the user_id for the global app tracker (when user logs in)."""
    global _app_tracker
    if _app_tracker:
        return _app_tracker.update_user_id(user_id)
    else:
        # If no tracker exists, create one with the user_id
        _app_tracker = AppTracker(user_id)
        return _app_tracker.start_session(user_id)


def get_online_users() -> list:
    """Get list of currently online users."""
    tracker = get_app_tracker()
    return tracker.get_online_users()


def get_user_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get session statistics for a user."""
    tracker = get_app_tracker(user_id)
    return tracker.get_user_session_stats(user_id) 