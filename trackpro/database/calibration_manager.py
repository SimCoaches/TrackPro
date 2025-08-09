"""Calibration database manager for handling user calibration data."""

import logging
import time # Add import for time.sleep
from typing import Any, Dict, List, Optional
from .base import DatabaseManager
from .supabase_client import supabase

logger = logging.getLogger(__name__)

class CalibrationManager(DatabaseManager):
    """Manages calibration-related database operations."""
    
    def __init__(self):
        """Initialize the calibration manager."""
        super().__init__("user_calibrations")
        self._pending_saves = {}  # Track pending calibration saves by user/name
        self._save_timers = {}    # Track save timers by user/name
    
    def get_user_calibrations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all calibrations for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of calibration records
        """
        try:
            client = self.client
            if client is None:
                raise RuntimeError("Supabase client is not available for get_user_calibrations")
            response = client.table(self.table_name).select("*").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting calibrations for user {user_id}: {e}")
            raise
    
    def save_calibration(self, user_id: str, name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a calibration for a user.
        
        Args:
            user_id: The ID of the user
            name: The name of the calibration
            data: The calibration data
            
        Returns:
            The saved calibration record
        """
        # Create a unique key for this calibration
        save_key = f"{user_id}_{name}"
        
        # Store the pending data
        self._pending_saves[save_key] = {
            "user_id": user_id,
            "name": name,
            "data": data
        }
        
        # If there's already a timer for this calibration, cancel it
        if save_key in self._save_timers and self._save_timers[save_key]:
            try:
                self._save_timers[save_key].cancel()
            except:
                pass
        
        # Schedule the actual save after a delay of 60 seconds (1 minute)
        import threading
        timer = threading.Timer(60.0, self._perform_save, args=[save_key])
        timer.daemon = True
        self._save_timers[save_key] = timer
        timer.start()
        
        # Return empty dict for now - actual save happens later
        return {}
    
    def _perform_save(self, save_key: str):
        """Actually perform the save operation after debounce period.
        
        Args:
            save_key: The key identifying which calibration to save
        """
        if save_key not in self._pending_saves:
            return
            
        # Get the pending save data
        pending = self._pending_saves.pop(save_key)
        user_id = pending["user_id"]
        name = pending["name"]
        data = pending["data"]
        
        # Clear the timer reference
        if save_key in self._save_timers:
            self._save_timers[save_key] = None
        
        # Add retry logic for Supabase operations
        max_retries = 3
        retry_delay = 1 # seconds
        last_exception = None

        for attempt in range(max_retries):
            try:
                calibration_data = {
                    "user_id": user_id,
                    "name": name,
                    "data": data
                }
                
                # Check if calibration with this name already exists
                # Only select the ID field and limit to 1 result for efficiency
                # Resolve client at save-time to ensure we don't use a stale or None client
                client = self.client
                if client is None:
                    raise RuntimeError("Supabase client is not available for calibration save")

                existing = client.table(self.table_name)\
                    .select("id")\
                    .eq("user_id", user_id)\
                    .eq("name", name)\
                    .limit(1)\
                    .execute()
                
                if existing.data:
                    # Update existing calibration
                    response = client.table(self.table_name)\
                        .update(calibration_data)\
                        .eq("id", existing.data[0]["id"])\
                        .execute()
                    logger.info(f"Attempt {attempt+1}: Updated existing calibration '{name}' for user {user_id}")
                else:
                    # Create new calibration
                    response = client.table(self.table_name)\
                        .insert(calibration_data)\
                        .execute()
                    logger.info(f"Attempt {attempt+1}: Created new calibration '{name}' for user {user_id}")
                
                # Success, return the data (ensure data exists)
                if response.data:
                    return response.data[0]
                else:
                    # Handle cases where insert/update might not return data as expected
                    logger.warning(f"Calibration '{name}' for user {user_id} saved/updated, but no data returned in response.")
                    return calibration_data # Return the input data as fallback

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt+1} failed to save calibration '{name}' for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    logger.error(f"Failed to save calibration '{name}' for user {user_id} after {max_retries} attempts.")
                    # Re-raise the last exception after all retries failed
                    raise last_exception
        
        # Should not be reached if successful, but needed if loop finishes unexpectedly
        logger.error(f"_perform_save for calibration '{name}' completed loop without success or expected error.")
        if last_exception:
             raise last_exception
        else:
             # Raise a generic error if no exception was caught but still failed
             raise RuntimeError(f"Failed to save calibration '{name}' after retries, unknown reason.")
    
    def delete_calibration(self, user_id: str, name: str) -> bool:
        """Delete a calibration.
        
        Args:
            user_id: The ID of the user
            name: The name of the calibration to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self.client
            if client is None:
                raise RuntimeError("Supabase client is not available for delete_calibration")
            response = client.table(self.table_name)\
                .delete()\
                .eq("user_id", user_id)\
                .eq("name", name)\
                .execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Deleted calibration '{name}' for user {user_id}")
            else:
                logger.warning(f"No calibration '{name}' found for user {user_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error deleting calibration '{name}' for user {user_id}: {e}")
            raise
    
    def get_calibration(self, user_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific calibration.
        
        Args:
            user_id: The ID of the user
            name: The name of the calibration
            
        Returns:
            The calibration data if found, None otherwise
        """
        try:
            client = self.client
            if client is None:
                raise RuntimeError("Supabase client is not available for get_calibration")
            response = client.table(self.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("name", name)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting calibration '{name}' for user {user_id}: {e}")
            raise

# Create a global instance
calibration_manager = CalibrationManager() 