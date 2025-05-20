"""Base database manager for common database operations."""

import logging
from typing import Any, Dict, List, Optional
from .supabase_client import supabase

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Base class for database operations."""
    
    def __init__(self, table_name: str):
        """Initialize the database manager.
        
        Args:
            table_name: Name of the table this manager handles
        """
        self.table_name = table_name
        self.client = supabase.client
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all records from the table.
        
        Returns:
            List of records
        """
        try:
            response = self.client.table(self.table_name).select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting all records from {self.table_name}: {e}")
            raise
    
    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a record by its ID.
        
        Args:
            record_id: The ID of the record to retrieve
            
        Returns:
            The record if found, None otherwise
        """
        try:
            response = self.client.table(self.table_name).select("*").eq("id", record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting record {record_id} from {self.table_name}: {e}")
            raise
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record.
        
        Args:
            data: The data for the new record
            
        Returns:
            The created record
        """
        try:
            response = self.client.table(self.table_name).insert(data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error creating record in {self.table_name}: {e}")
            raise
    
    def update(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record.
        
        Args:
            record_id: The ID of the record to update
            data: The updated data
            
        Returns:
            The updated record
        """
        try:
            response = self.client.table(self.table_name).update(data).eq("id", record_id).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Error updating record {record_id} in {self.table_name}: {e}")
            raise
    
    def delete(self, record_id: str) -> bool:
        """Delete a record.
        
        Args:
            record_id: The ID of the record to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.table(self.table_name).delete().eq("id", record_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error deleting record {record_id} from {self.table_name}: {e}")
            raise
    
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a custom query on the table.
        
        Args:
            query_params: Dictionary of query parameters
            
        Returns:
            List of matching records
        """
        try:
            query = self.client.table(self.table_name).select("*")
            
            for key, value in query_params.items():
                if isinstance(value, (list, tuple)):
                    query = query.in_(key, value)
                else:
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Error executing query on {self.table_name}: {e}")
            raise 