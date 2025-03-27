"""Calibration database manager for handling user calibration data."""

import logging
from typing import Any, Dict, List, Optional
from .base import DatabaseManager
from .supabase_client import supabase

logger = logging.getLogger(__name__)

class CalibrationManager(DatabaseManager):
    """Manages calibration-related database operations."""
    
    def __init__(self):
        """Initialize the calibration manager."""
        super().__init__("user_calibrations")
    
    def get_user_calibrations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all calibrations for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of calibration records
        """
        try:
            response = self.client.table(self.table_name).select("*").eq("user", user_id).execute()
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
        try:
            calibration_data = {
                "user": user_id,
                "name": name,
                "data": data
            }
            
            # Check if calibration with this name already exists
            existing = self.client.table(self.table_name)\
                .select("*")\
                .eq("user", user_id)\
                .eq("name", name)\
                .execute()
            
            if existing.data:
                # Update existing calibration
                response = self.client.table(self.table_name)\
                    .update(calibration_data)\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
                logger.info(f"Updated existing calibration '{name}' for user {user_id}")
            else:
                # Create new calibration
                response = self.client.table(self.table_name)\
                    .insert(calibration_data)\
                    .execute()
                logger.info(f"Created new calibration '{name}' for user {user_id}")
            
            return response.data[0]
        except Exception as e:
            logger.error(f"Error saving calibration for user {user_id}: {e}")
            raise
    
    def delete_calibration(self, user_id: str, name: str) -> bool:
        """Delete a calibration.
        
        Args:
            user_id: The ID of the user
            name: The name of the calibration to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.table(self.table_name)\
                .delete()\
                .eq("user", user_id)\
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
            response = self.client.table(self.table_name)\
                .select("*")\
                .eq("user", user_id)\
                .eq("name", name)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting calibration '{name}' for user {user_id}: {e}")
            raise

# Create a global instance
calibration_manager = CalibrationManager() 