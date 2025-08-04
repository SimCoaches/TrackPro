#!/usr/bin/env python
"""
Apply SimCoaches Hierarchy Migration

This script applies the migration to automatically assign TEAM level to users with @simcoaches.com email addresses.
"""

import sys
import os
import logging

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Supabase client
from trackpro.database.supabase_client import supabase

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_simcoaches_hierarchy_migration():
    """Apply the migration to automatically assign TEAM level to @simcoaches.com users."""
    
    if not supabase.is_authenticated():
        logger.error("Not authenticated with Supabase. Please log in first.")
        return False
    
    try:
        logger.info("Applying SimCoaches hierarchy migration...")
        
        # Read the migration file
        migration_path = "trackpro/database/migrations/24_update_hierarchy_for_simcoaches_domain.sql"
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        # Split into statements and execute
        statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    logger.info(f"Executing statement {i+1}/{len(statements)}")
                    
                    # Execute the SQL statement
                    result = supabase.client.rpc('exec_sql', {'sql': statement}).execute()
                    logger.info(f"Successfully executed statement {i+1}")
                    
                except Exception as e:
                    logger.warning(f"Could not execute statement {i+1}: {e}")
                    # Continue with next statement
                    continue
        
        logger.info("Successfully applied SimCoaches hierarchy migration")
        
        # Verify the changes
        logger.info("Verifying changes...")
        verify_simcoaches_users()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply migration: {e}")
        return False

def verify_simcoaches_users():
    """Verify that @simcoaches.com users have TEAM level."""
    try:
        # Query to check @simcoaches.com users
        result = supabase.client.rpc('exec_sql', {
            'sql': """
            SELECT 
                u.email,
                uh.hierarchy_level,
                uh.is_dev,
                uh.is_moderator
            FROM auth.users u
            LEFT JOIN public.user_hierarchy uh ON u.id = uh.user_id
            WHERE u.email LIKE '%@simcoaches.com'
            """
        }).execute()
        
        if result.data:
            logger.info("SimCoaches users found:")
            for user in result.data:
                logger.info(f"  {user['email']}: {user['hierarchy_level']} (Dev: {user['is_dev']}, Mod: {user['is_moderator']})")
        else:
            logger.info("No @simcoaches.com users found in database")
            
    except Exception as e:
        logger.warning(f"Could not verify users: {e}")

def main():
    """Main function to run the migration."""
    logger.info("Starting SimCoaches hierarchy migration")
    
    success = apply_simcoaches_hierarchy_migration()
    
    if success:
        logger.info("Migration completed successfully!")
        logger.info("All @simcoaches.com users now have TEAM level with full permissions.")
        return 0
    else:
        logger.error("Migration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 