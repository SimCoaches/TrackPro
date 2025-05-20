#!/usr/bin/env python
"""
Run Supabase Migrations Script

This script runs SQL migrations against a Supabase database to set up the 
gamification system tables and functions.
"""

import os
import sys
import argparse
import logging
import time
from typing import List, Tuple, Optional

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Supabase client
from trackpro.database.supabase_client import supabase
from Supabase import auth

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")

def list_migration_files() -> List[str]:
    """
    List all migration files in the migrations directory, sorted by filename.
    
    Returns:
        List[str]: List of migration filenames
    """
    if not os.path.exists(MIGRATIONS_DIR):
        logger.error(f"Migrations directory not found: {MIGRATIONS_DIR}")
        return []
    
    # Get all .sql files and sort them
    migrations = [f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql')]
    migrations.sort()
    
    return migrations

def read_migration_file(filename: str) -> Optional[str]:
    """
    Read the contents of a migration file.
    
    Args:
        filename: Name of the migration file
        
    Returns:
        Optional[str]: Contents of the file or None if not found
    """
    file_path = os.path.join(MIGRATIONS_DIR, filename)
    
    if not os.path.exists(file_path):
        logger.error(f"Migration file not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading migration file {filename}: {e}")
        return None

def run_migrations(skip_existing: bool = True) -> Tuple[bool, int, int]:
    """
    Run all available migrations against the Supabase database.
    
    Args:
        skip_existing: If True, check for existing tables and skip if found
        
    Returns:
        Tuple[bool, int, int]: Success flag, number of migrations run, total migrations
    """
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False, 0, 0
    
    # List migration files
    migrations = list_migration_files()
    if not migrations:
        logger.warning("No migration files found.")
        return True, 0, 0
    
    logger.info(f"Found {len(migrations)} migration files")
    
    # Check if we need to skip existing tables
    if skip_existing:
        try:
            # Check if user_profiles table exists
            check_result = supabase.client.rpc(
                'check_table_exists', 
                {'p_table_name': 'user_profiles'}
            ).execute()
            
            if check_result.data and check_result.data == True:
                logger.info("Gamification tables already exist. Skipping migrations.")
                return True, 0, len(migrations)
        except Exception as e:
            # If the RPC doesn't exist or fails, we'll just continue with migrations
            logger.warning(f"Could not check for existing tables: {e}")
    
    # Run migrations
    success_count = 0
    for i, migration_file in enumerate(migrations):
        logger.info(f"Running migration {i+1}/{len(migrations)}: {migration_file}")
        
        # Read migration SQL
        sql = read_migration_file(migration_file)
        if not sql:
            logger.error(f"Failed to read migration {migration_file}")
            continue
        
        # Execute migration
        try:
            migration_name = os.path.splitext(migration_file)[0]
            supabase.client.rpc(
                'run_sql', 
                {'sql': sql}
            ).execute()
            
            logger.info(f"Successfully applied migration: {migration_file}")
            success_count += 1
            
            # Sleep briefly to avoid rate limiting
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error applying migration {migration_file}: {e}")
            # Continue with other migrations
    
    return success_count == len(migrations), success_count, len(migrations)

def create_check_table_function() -> bool:
    """
    Create a PostgreSQL function to check if a table exists.
    
    Returns:
        bool: Success flag
    """
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        # Create function to check if a table exists
        sql = """
        CREATE OR REPLACE FUNCTION check_table_exists(p_table_name TEXT)
        RETURNS BOOLEAN AS $$
        DECLARE
            v_exists BOOLEAN;
        BEGIN
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = p_table_name
            ) INTO v_exists;
            
            RETURN v_exists;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        supabase.client.rpc('run_sql', {'sql': sql}).execute()
        return True
    except Exception as e:
        logger.error(f"Error creating check_table_exists function: {e}")
        return False

def create_run_sql_function() -> bool:
    """
    Create a PostgreSQL function to run arbitrary SQL.
    
    Returns:
        bool: Success flag
    """
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        # Create function to run SQL statements
        sql = """
        CREATE OR REPLACE FUNCTION run_sql(sql TEXT)
        RETURNS VOID AS $$
        BEGIN
            EXECUTE sql;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        # Make direct query to create the function
        # Since we're bootstrapping, we need to use the low-level client
        result = supabase.client.postgrest.rpc("run_sql", {"sql": sql}).execute()
        
        if result.get("error"):
            logger.error(f"Error creating run_sql function: {result.get('error')}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error creating run_sql function: {e}")
        return False

def main():
    """Main function to run migrations"""
    parser = argparse.ArgumentParser(description="Run Supabase gamification migrations")
    parser.add_argument("--force", action="store_true", help="Force running migrations even if tables exist")
    args = parser.parse_args()
    
    logger.info("Starting Supabase gamification migrations")
    
    # Check if user is authenticated
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return 1
    
    # Create helper functions
    logger.info("Creating helper functions...")
    if not create_run_sql_function():
        logger.error("Failed to create run_sql function.")
        return 1
    
    if not create_check_table_function():
        logger.error("Failed to create check_table_exists function.")
        return 1
    
    # Run migrations
    logger.info("Running migrations...")
    success, applied, total = run_migrations(skip_existing=not args.force)
    
    if success:
        logger.info(f"Successfully applied {applied}/{total} migrations")
        return 0
    else:
        logger.error(f"Failed to apply all migrations. Applied {applied}/{total}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 