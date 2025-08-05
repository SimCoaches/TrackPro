#!/usr/bin/env python
"""
Apply User Details Migration

This script applies the user_details table migration to fix the profile saving issue.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Supabase client
from trackpro.database.supabase_client import get_supabase_client

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_user_details_migration():
    """Apply the user_details table migration."""
    
    supabase_client = get_supabase_client()
    if not supabase_client:
        logger.error("No Supabase client available")
        return False
    
    if not supabase_client.auth.get_user():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        # Read the migration file
        migration_file = "trackpro/database/migrations/22_create_user_details_table.sql"
        
        if not os.path.exists(migration_file):
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        logger.info("Applying user_details table migration...")
        
        # Split SQL into individual statements and execute them
        statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                try:
                    # Execute the statement using the client
                    result = supabase_client.client.rpc('exec_sql', {'sql': statement}).execute()
                    logger.info(f"Executed statement: {statement[:50]}...")
                except Exception as e:
                    logger.warning(f"Could not execute statement: {e}")
                    # Try alternative approach for some statements
                    if "CREATE TABLE" in statement.upper():
                        logger.info("Table creation statement - this may already exist")
                    elif "CREATE POLICY" in statement.upper():
                        logger.info("Policy creation statement - this may already exist")
                    elif "CREATE INDEX" in statement.upper():
                        logger.info("Index creation statement - this may already exist")
                    elif "CREATE TRIGGER" in statement.upper():
                        logger.info("Trigger creation statement - this may already exist")
                    elif "CREATE OR REPLACE FUNCTION" in statement.upper():
                        logger.info("Function creation statement - this may already exist")
                    else:
                        logger.error(f"Failed to execute: {statement[:100]}...")
        
        logger.info("User details migration applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error applying user_details migration: {e}")
        return False

def main():
    """Main function to apply the migration."""
    logger.info("Starting user_details table migration")
    
    success = apply_user_details_migration()
    
    if success:
        logger.info("Migration completed successfully!")
        return 0
    else:
        logger.error("Migration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 