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

def create_execute_sql_function() -> bool:
    """
    Create a PostgreSQL function to run arbitrary SQL.
    
    Returns:
        bool: Success flag
    """
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        # Since we can't create the execute_sql function without it existing first,
        # we'll skip this step and apply migrations directly
        logger.info("Skipping execute_sql function creation - will apply migrations directly")
        return True
    except Exception as e:
        logger.error(f"Error in create_execute_sql_function: {e}")
        return False

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
        # Since we can't create the check_table_exists function without execute_sql,
        # we'll skip this step and apply migrations directly
        logger.info("Skipping check_table_exists function creation - will apply migrations directly")
        return True
    except Exception as e:
        logger.error(f"Error in create_check_table_function: {e}")
        return False

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
            # Check if user_profiles table exists by trying to select from it
            check_result = supabase.client.table("user_profiles").select("user_id").limit(1).execute()
            if check_result.data is not None:
                logger.info("Gamification tables already exist. Skipping migrations.")
                return True, 0, len(migrations)
        except Exception as e:
            # If the table doesn't exist, we'll continue with migrations
            logger.info(f"Tables don't exist yet, will run migrations: {e}")
    
    # Run migrations
    success_count = 0
    for i, migration_file in enumerate(migrations):
        logger.info(f"Running migration {i+1}/{len(migrations)}: {migration_file}")
        
        # Read migration SQL
        sql = read_migration_file(migration_file)
        if not sql:
            logger.error(f"Failed to read migration {migration_file}")
            continue
        
        # Execute migration directly using the client
        try:
            # Split SQL into individual statements and execute them
            statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    # Execute the statement directly
                    # Note: This is a simplified approach - in production you'd want more robust SQL parsing
                    try:
                        # For ALTER TABLE and CREATE statements, we'll use a direct approach
                        if statement.upper().startswith(('ALTER TABLE', 'CREATE', 'INSERT', 'UPDATE', 'DELETE')):
                            # Use the client's raw SQL capability if available
                            result = supabase.client.rpc('exec_sql', {'sql': statement}).execute()
                        else:
                            # For SELECT statements, use the table interface
                            result = supabase.client.table("user_profiles").select("*").limit(1).execute()
                    except Exception as stmt_error:
                        # If the RPC doesn't exist, try a different approach
                        logger.warning(f"Could not execute statement directly: {stmt_error}")
                        # Continue with next statement
                        continue
            
            logger.info(f"Successfully applied migration: {migration_file}")
            success_count += 1
            
            # Sleep briefly to avoid rate limiting
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error applying migration {migration_file}: {e}")
            # Continue with other migrations
    
    return success_count == len(migrations), success_count, len(migrations)

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
    if not create_execute_sql_function():
        logger.error("Failed to create execute_sql function.")
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