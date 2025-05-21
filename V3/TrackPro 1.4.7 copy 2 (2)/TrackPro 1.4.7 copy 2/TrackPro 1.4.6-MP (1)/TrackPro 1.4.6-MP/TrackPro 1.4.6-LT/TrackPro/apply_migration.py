#!/usr/bin/env python
"""
Script to apply the lap_type migration.

This script specifically applies the lap_type column migration to the laps table
to support the enhanced lap recording fix.
"""

import os
import sys
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Supabase client
from trackpro.database.supabase_client import supabase
from trackpro.database.run_migrations import read_migration_file

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_lap_type_migration():
    """Apply the lap_type column migration to the laps table."""
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    logger.info("Applying lap_type migration...")
    
    # Read the migration file
    sql = read_migration_file("07_add_lap_type_column.sql")
    if not sql:
        logger.error("Failed to read lap_type migration file")
        return False
    
    # Execute the migration
    try:
        # Try using the run_sql function if it exists
        try:
            logger.info("Attempting to apply migration using run_sql RPC function...")
            supabase.client.rpc('run_sql', {'sql': sql}).execute()
            logger.info("Successfully applied lap_type migration using run_sql")
            return True
        except Exception as e:
            logger.warning(f"Could not use run_sql function: {e}")
            logger.info("Falling back to direct SQL execution...")
            
            # Direct SQL execution fallback
            supabase.client.sql(sql).execute()
            logger.info("Successfully applied lap_type migration using direct SQL")
            return True
            
    except Exception as e:
        logger.error(f"Error applying lap_type migration: {e}")
        return False

def main():
    """Main function to apply the lap_type migration."""
    logger.info("Starting lap_type column migration")
    
    success = apply_lap_type_migration()
    
    if success:
        logger.info("Successfully applied lap_type migration")
        return 0
    else:
        logger.error("Failed to apply lap_type migration")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 