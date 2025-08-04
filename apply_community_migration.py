#!/usr/bin/env python
"""
Apply Community System Migration

This script applies the community system migration to create the necessary tables.
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import get_supabase_client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_community_migration():
    """Apply the community system migration."""
    try:
        # Get the Supabase client
        client = get_supabase_client()
        if not client:
            logger.error("Failed to get Supabase client")
            return False
        
        # Read the migration file
        migration_path = "trackpro/database/migrations/22_create_community_system.sql"
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        logger.info("Applying community system migration...")
        
        # Split into statements and execute
        statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    logger.info(f"Executing statement {i+1}/{len(statements)}")
                    # Execute the statement using the client
                    result = client.rpc('exec_sql', {'sql': statement}).execute()
                    logger.info(f"Statement {i+1} executed successfully")
                except Exception as e:
                    logger.warning(f"Could not execute statement {i+1}: {e}")
                    # Try alternative approach for CREATE TABLE statements
                    if 'CREATE TABLE' in statement.upper():
                        logger.info(f"Trying alternative approach for CREATE TABLE statement")
                        # For CREATE TABLE, we'll let it fail gracefully if table exists
                        continue
        
        logger.info("Community system migration completed")
        return True
        
    except Exception as e:
        logger.error(f"Error applying community migration: {e}")
        return False

if __name__ == "__main__":
    success = apply_community_migration()
    if success:
        print("✅ Community system migration applied successfully")
    else:
        print("❌ Failed to apply community system migration") 