#!/usr/bin/env python3
"""
Clear Telemetry Data Script

This script clears all telemetry data from:
1. Local SQLite database (race_coach.db)
2. Supabase database (if configured)
3. Telemetry files stored on filesystem

The table structures are preserved, only the data is deleted.
"""

import sqlite3
import os
import shutil
import json
import logging
from pathlib import Path
from trackpro.database.supabase_client import get_supabase_client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelemetryDataCleaner:
    """Handles clearing of all telemetry data while preserving table structures."""
    
    def __init__(self):
        """Initialize the cleaner."""
        self.sqlite_db_path = None
        self.telemetry_dir = None
        self.supabase_client = None
        
        # Find the SQLite database
        self._find_database()
        
        # Try to get Supabase client
        try:
            self.supabase_client = get_supabase_client()
            if self.supabase_client:
                logger.info("Supabase client available - will clean cloud data too")
            else:
                logger.info("Supabase client not available - will only clean local data")
        except Exception as e:
            logger.warning(f"Could not connect to Supabase: {e}")
            self.supabase_client = None
    
    def _find_database(self):
        """Find the race_coach.db file."""
        possible_paths = [
            "race_coach.db",  # Current directory
            Path(os.path.expanduser("~/Documents/TrackPro/race_coach.db")),  # Default location
            Path("trackpro/race_coach.db"),  # In trackpro folder
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.sqlite_db_path = str(path)
                self.telemetry_dir = os.path.join(os.path.dirname(self.sqlite_db_path), "telemetry")
                logger.info(f"Found database at: {self.sqlite_db_path}")
                return
        
        logger.error("Could not find race_coach.db file!")
        raise FileNotFoundError("race_coach.db not found")
    
    def clear_sqlite_data(self):
        """Clear all data from SQLite database tables while preserving structure."""
        logger.info("Clearing SQLite database data...")
        
        if not os.path.exists(self.sqlite_db_path):
            logger.error(f"Database file not found: {self.sqlite_db_path}")
            return False
        
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Get list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"Found tables: {tables}")
            
            # Delete data from tables in the correct order (respecting foreign key constraints)
            delete_order = [
                'sectors',      # References laps
                'laps',         # References sessions
                'super_laps',   # References tracks and cars
                'sessions',     # References drivers, tracks, cars
                'drivers',      # No dependencies
                'tracks',       # No dependencies
                'cars'          # No dependencies
            ]
            
            # Disable foreign key constraints temporarily
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            cleared_tables = []
            for table in delete_order:
                if table in tables:
                    # Count records before deletion
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count_before = cursor.fetchone()[0]
                    
                    # Delete all data
                    cursor.execute(f"DELETE FROM {table}")
                    
                    # Reset auto-increment counter
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                    
                    cleared_tables.append(f"{table} ({count_before} records)")
                    logger.info(f"Cleared table '{table}': {count_before} records deleted")
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            logger.info(f"SQLite cleanup complete. Cleared tables: {', '.join(cleared_tables)}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing SQLite data: {e}")
            return False
    
    def clear_telemetry_files(self):
        """Clear telemetry files from the filesystem."""
        logger.info("Clearing telemetry files...")
        
        if not self.telemetry_dir:
            logger.info("No telemetry directory found")
            return True
        
        if not os.path.exists(self.telemetry_dir):
            logger.info(f"Telemetry directory does not exist: {self.telemetry_dir}")
            return True
        
        try:
            # Count files before deletion
            file_count = 0
            for root, dirs, files in os.walk(self.telemetry_dir):
                file_count += len(files)
            
            if file_count == 0:
                logger.info("No telemetry files to delete")
                return True
            
            # Remove the entire telemetry directory and its contents
            shutil.rmtree(self.telemetry_dir)
            logger.info(f"Deleted telemetry directory and {file_count} files: {self.telemetry_dir}")
            
            # Recreate the empty directory
            os.makedirs(self.telemetry_dir, exist_ok=True)
            logger.info(f"Recreated empty telemetry directory: {self.telemetry_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing telemetry files: {e}")
            return False
    
    def clear_supabase_data(self):
        """Clear telemetry data from Supabase while preserving table structure."""
        if not self.supabase_client:
            logger.info("Skipping Supabase cleanup - client not available")
            return True
        
        logger.info("Clearing Supabase telemetry data...")
        
        try:
            # Tables to clear in Supabase (order matters for foreign keys)
            supabase_tables = [
                'telemetry_points',  # Main telemetry data
                'laps',              # Lap records (if using Supabase for laps)
                'sessions',          # Session records (if using Supabase)
            ]
            
            cleared_tables = []
            
            for table in supabase_tables:
                try:
                    # Count records before deletion
                    count_response = self.supabase_client.table(table).select('*', count='exact').execute()
                    count_before = count_response.count if hasattr(count_response, 'count') else 0
                    
                    if count_before > 0:
                        # Delete all records from the table
                        # Note: Supabase doesn't have a direct "DELETE ALL" so we need to delete in batches
                        batch_size = 1000
                        total_deleted = 0
                        
                        while True:
                            # Get a batch of records
                            response = self.supabase_client.table(table).select('id').limit(batch_size).execute()
                            
                            if not response.data:
                                break
                            
                            # Extract IDs
                            ids = [record['id'] for record in response.data]
                            
                            # Delete this batch
                            delete_response = self.supabase_client.table(table).delete().in_('id', ids).execute()
                            
                            deleted_count = len(delete_response.data) if delete_response.data else 0
                            total_deleted += deleted_count
                            
                            logger.info(f"Deleted {deleted_count} records from {table} (total: {total_deleted}/{count_before})")
                            
                            # If we deleted fewer than batch_size, we're done
                            if deleted_count < batch_size:
                                break
                        
                        cleared_tables.append(f"{table} ({total_deleted} records)")
                        logger.info(f"Cleared Supabase table '{table}': {total_deleted} records deleted")
                    else:
                        logger.info(f"Table '{table}' is already empty")
                        cleared_tables.append(f"{table} (0 records)")
                        
                except Exception as e:
                    logger.error(f"Error clearing Supabase table '{table}': {e}")
                    # Continue with other tables
                    continue
            
            logger.info(f"Supabase cleanup complete. Cleared tables: {', '.join(cleared_tables)}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing Supabase data: {e}")
            return False
    
    def run_cleanup(self):
        """Run the complete cleanup process."""
        logger.info("=== Starting Telemetry Data Cleanup ===")
        
        success = True
        
        # 1. Clear SQLite data
        logger.info("\n1. Clearing local SQLite database...")
        if not self.clear_sqlite_data():
            success = False
        
        # 2. Clear telemetry files
        logger.info("\n2. Clearing telemetry files...")
        if not self.clear_telemetry_files():
            success = False
        
        # 3. Clear Supabase data
        logger.info("\n3. Clearing Supabase data...")
        if not self.clear_supabase_data():
            success = False
        
        if success:
            logger.info("\n=== Cleanup completed successfully! ===")
            logger.info("All telemetry data has been cleared while preserving table structures.")
            logger.info("You can now start fresh with clean data.")
        else:
            logger.error("\n=== Cleanup completed with errors ===")
            logger.error("Some parts of the cleanup may have failed. Check the logs above.")
        
        return success

def main():
    """Main function."""
    print("TrackPro Telemetry Data Cleaner")
    print("===============================")
    print()
    print("This script will clear ALL telemetry data from:")
    print("- Local SQLite database (race_coach.db)")
    print("- Supabase cloud database (if configured)")
    print("- Telemetry files on filesystem")
    print()
    print("Table structures will be preserved - only data will be deleted.")
    print()
    
    # Confirm with user
    confirm = input("Are you sure you want to proceed? This action cannot be undone! (type 'yes' to confirm): ")
    
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    print("\nStarting cleanup...")
    
    try:
        cleaner = TelemetryDataCleaner()
        success = cleaner.run_cleanup()
        
        if success:
            print("\n✅ All telemetry data has been successfully cleared!")
            print("You can now restart TrackPro and begin with fresh, clean data.")
        else:
            print("\n❌ Cleanup completed with some errors. Check the logs above for details.")
            
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {e}")
        print(f"\n❌ Cleanup failed: {e}")

if __name__ == "__main__":
    main() 