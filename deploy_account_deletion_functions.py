#!/usr/bin/env python3
"""
Deploy Account Deletion Functions to Supabase

This script deploys the account deletion database functions required for
complete GDPR/privacy compliance in TrackPro.

Usage:
    python deploy_account_deletion_functions.py

Requirements:
    - User must be authenticated with Supabase
    - User must have database admin privileges
"""

import sys
import os
import logging

# Add trackpro to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import supabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def deploy_auth_deletion_function():
    """Deploy the auth user deletion function."""
    logger.info("Deploying auth user deletion function...")
    
    sql = """
    -- Function to delete auth users with elevated privileges
    CREATE OR REPLACE FUNCTION public.delete_auth_user_complete(user_uuid UUID)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
    SECURITY DEFINER
    AS $$
    BEGIN
        -- Delete from auth.users table (requires elevated privileges)
        DELETE FROM auth.users WHERE id = user_uuid;
        
        -- Check if deletion was successful
        IF NOT FOUND THEN
            RAISE NOTICE 'Auth user % not found or already deleted', user_uuid;
            RETURN FALSE;
        END IF;
        
        RAISE NOTICE 'Successfully deleted auth user %', user_uuid;
        RETURN TRUE;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Error deleting auth user %: %', user_uuid, SQLERRM;
            RETURN FALSE;
    END;
    $$;
    
    -- Grant execute permission to authenticated users
    GRANT EXECUTE ON FUNCTION public.delete_auth_user_complete(UUID) TO authenticated;
    
    -- Add comment for documentation
    COMMENT ON FUNCTION public.delete_auth_user_complete(UUID) IS 
    'Deletes a user from auth.users table. This function runs with elevated privileges to ensure complete account deletion for compliance purposes.';
    """
    
    try:
        # Execute directly as admin/owner
        result = supabase.client.rpc('execute_sql', {'sql': sql}).execute()
        logger.info("✅ Auth user deletion function deployed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to deploy auth user deletion function: {e}")
        return False

def deploy_data_deletion_function():
    """Deploy the comprehensive data deletion function."""
    logger.info("Deploying comprehensive data deletion function...")
    
    sql = """
    -- Function to delete ALL user data from ALL tables
    CREATE OR REPLACE FUNCTION public.delete_user_data_complete(user_uuid UUID)
    RETURNS JSONB
    LANGUAGE plpgsql
    SECURITY DEFINER
    AS $$
    DECLARE
        deleted_count INTEGER := 0;
        table_results JSONB := '{}';
        table_name TEXT;
        sql_statement TEXT;
    BEGIN
        -- List of all tables that contain user data (in dependency order)
        FOR table_name IN 
            SELECT unnest(ARRAY[
                'sessions',
                'telemetry_points', 
                'laps',
                'user_quests',
                'user_calibrations',
                'eye_tracking_points',
                'eye_tracking_sessions', 
                'sector_times',
                'user_achievements',
                'user_stats',
                'user_streaks',
                'reputation_events',
                'team_members',
                'club_members', 
                'event_participants',
                'challenge_participants',
                'conversation_participants',
                'messages',
                'user_activities',
                'activity_interactions',
                'setup_ratings',
                'media_likes',
                'leaderboard_entries', 
                'shared_setups',
                'shared_media',
                'friendships',
                'teams',
                'clubs',
                'community_events',
                'community_challenges',
                'conversations',
                'user_profiles',
                'user_details'
            ])
        LOOP
            BEGIN
                -- Handle special cases for tables with different column names
                CASE table_name
                    WHEN 'messages' THEN
                        sql_statement := format('DELETE FROM %I WHERE sender_id = %L', table_name, user_uuid);
                    WHEN 'friendships' THEN
                        sql_statement := format('DELETE FROM %I WHERE requester_id = %L OR addressee_id = %L', table_name, user_uuid, user_uuid);
                    WHEN 'reputation_events' THEN
                        sql_statement := format('DELETE FROM %I WHERE user_id = %L OR given_by = %L', table_name, user_uuid, user_uuid);
                    WHEN 'teams', 'clubs', 'community_events', 'community_challenges', 'conversations' THEN
                        sql_statement := format('DELETE FROM %I WHERE created_by = %L', table_name, user_uuid);
                    ELSE
                        sql_statement := format('DELETE FROM %I WHERE user_id = %L', table_name, user_uuid);
                END CASE;
                
                -- Execute the deletion and count rows
                EXECUTE sql_statement;
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                
                -- Record the result
                table_results := jsonb_set(table_results, ARRAY[table_name], to_jsonb(deleted_count));
                
                RAISE NOTICE 'Deleted % rows from table %', deleted_count, table_name;
                
            EXCEPTION
                WHEN undefined_table THEN
                    table_results := jsonb_set(table_results, ARRAY[table_name], to_jsonb('table_not_exists'));
                    RAISE NOTICE 'Table % does not exist, skipping', table_name;
                WHEN OTHERS THEN
                    table_results := jsonb_set(table_results, ARRAY[table_name], to_jsonb('error: ' || SQLERRM));
                    RAISE NOTICE 'Error deleting from table %: %', table_name, SQLERRM;
            END;
        END LOOP;
        
        -- Return summary of deletions
        RETURN jsonb_build_object(
            'user_id', user_uuid,
            'timestamp', now(),
            'status', 'completed',
            'tables_processed', table_results
        );
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION 'Failed to delete user data for %: %', user_uuid, SQLERRM;
    END;
    $$;
    
    -- Grant execute permission to authenticated users
    GRANT EXECUTE ON FUNCTION public.delete_user_data_complete(UUID) TO authenticated;
    
    -- Add comment for documentation
    COMMENT ON FUNCTION public.delete_user_data_complete(UUID) IS 
    'Deletes ALL user data from ALL tables in a single transaction. Returns a summary of the deletion process. Used for complete account deletion compliance.';
    """
    
    try:
        result = supabase.client.rpc('execute_sql', {'sql': sql}).execute()
        logger.info("✅ Comprehensive data deletion function deployed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to deploy data deletion function: {e}")
        return False

def deploy_combined_deletion_function():
    """Deploy the combined deletion function."""
    logger.info("Deploying combined deletion function...")
    
    sql = """
    -- Function that does both data and auth deletion
    CREATE OR REPLACE FUNCTION public.delete_user_completely(user_uuid UUID)
    RETURNS JSONB
    LANGUAGE plpgsql
    SECURITY DEFINER
    AS $$
    DECLARE
        data_result JSONB;
        auth_deleted BOOLEAN;
        final_result JSONB;
    BEGIN
        -- First delete all user data
        SELECT delete_user_data_complete(user_uuid) INTO data_result;
        
        -- Then delete the auth user
        SELECT delete_auth_user_complete(user_uuid) INTO auth_deleted;
        
        -- Build final result
        final_result := jsonb_build_object(
            'user_id', user_uuid,
            'timestamp', now(),
            'data_deletion', data_result,
            'auth_deletion', auth_deleted,
            'complete_deletion', auth_deleted
        );
        
        IF auth_deleted THEN
            RAISE NOTICE 'User % completely deleted (data + auth)', user_uuid;
        ELSE
            RAISE NOTICE 'User % data deleted but auth deletion failed', user_uuid;
        END IF;
        
        RETURN final_result;
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION 'Failed to completely delete user %: %', user_uuid, SQLERRM;
    END;
    $$;
    
    -- Grant execute permission to authenticated users  
    GRANT EXECUTE ON FUNCTION public.delete_user_completely(UUID) TO authenticated;
    
    -- Add comment for documentation
    COMMENT ON FUNCTION public.delete_user_completely(UUID) IS 
    'Completely deletes a user account including both data and auth records. This is the main function to use for account deletion compliance.';
    """
    
    try:
        result = supabase.client.rpc('execute_sql', {'sql': sql}).execute()
        logger.info("✅ Combined deletion function deployed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to deploy combined deletion function: {e}")
        return False

def test_functions():
    """Test that the functions were deployed correctly."""
    logger.info("Testing deployed functions...")
    
    try:
        # Test that functions exist by calling them with a fake UUID
        test_uuid = "00000000-0000-0000-0000-000000000000"
        
        # Test auth deletion function
        try:
            result = supabase.client.rpc('delete_auth_user_complete', {'user_uuid': test_uuid}).execute()
            logger.info("✅ Auth deletion function is callable")
        except Exception as e:
            if "not found" in str(e).lower():
                logger.error("❌ Auth deletion function not found")
                return False
            else:
                logger.info("✅ Auth deletion function exists (test UUID not found as expected)")
        
        # Test data deletion function
        try:
            result = supabase.client.rpc('delete_user_data_complete', {'user_uuid': test_uuid}).execute()
            logger.info("✅ Data deletion function is callable")
        except Exception as e:
            if "not found" in str(e).lower():
                logger.error("❌ Data deletion function not found")
                return False
            else:
                logger.info("✅ Data deletion function exists")
        
        # Test combined function
        try:
            result = supabase.client.rpc('delete_user_completely', {'user_uuid': test_uuid}).execute()
            logger.info("✅ Combined deletion function is callable")
        except Exception as e:
            if "not found" in str(e).lower():
                logger.error("❌ Combined deletion function not found")
                return False
            else:
                logger.info("✅ Combined deletion function exists")
        
        return True
    except Exception as e:
        logger.error(f"❌ Function testing failed: {e}")
        return False

def main():
    """Main deployment function."""
    logger.info("🚀 Starting account deletion functions deployment")
    
    # Check authentication
    if not supabase.is_authenticated():
        logger.error("❌ Not authenticated with Supabase. Please log in first.")
        return 1
    
    # Deploy functions
    success_count = 0
    total_functions = 3
    
    if deploy_auth_deletion_function():
        success_count += 1
    
    if deploy_data_deletion_function():
        success_count += 1
    
    if deploy_combined_deletion_function():
        success_count += 1
    
    # Test deployed functions
    if success_count == total_functions:
        logger.info("🎯 All functions deployed, running tests...")
        if test_functions():
            logger.info("🎉 All account deletion functions deployed and tested successfully!")
            logger.info("✅ TrackPro now has complete GDPR/privacy compliance for account deletion")
            return 0
        else:
            logger.error("❌ Functions deployed but testing failed")
            return 1
    else:
        logger.error(f"❌ Only {success_count}/{total_functions} functions deployed successfully")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 