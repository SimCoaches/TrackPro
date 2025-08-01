"""Script to display statistics about collected telemetry data."""

from ..database.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

def count_telemetry_points() -> int:
    """Count the total number of telemetry points in the database.
    
    Returns:
        int: Total number of telemetry points, or 0 if query fails
    """
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        if not supabase:
            logger.error("Failed to get Supabase client")
            return 0
            
        # Query the telemetry_points table
        response = supabase.table('telemetry_points').select('count', count='exact').execute()
        
        # Extract count from response
        count = response.count if hasattr(response, 'count') else 0
        return count
        
    except Exception as e:
        logger.error(f"Error counting telemetry points: {e}")
        return 0

def display_telemetry_stats():
    """Display telemetry statistics in the console."""
    total_points = count_telemetry_points()
    print(f"\nTotal data points collected: {total_points:,}")

if __name__ == "__main__":
    display_telemetry_stats() 