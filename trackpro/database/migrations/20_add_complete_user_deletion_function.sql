-- Migration to add comprehensive user data deletion function
-- This ensures all user data is deleted in a single transaction for data consistency

-- Create a function that deletes ALL user data from ALL tables
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
    -- Dependencies first, then main tables
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
                    -- Delete friendships where user is either requester or addressee
                    sql_statement := format('DELETE FROM %I WHERE requester_id = %L OR addressee_id = %L', table_name, user_uuid, user_uuid);
                WHEN 'reputation_events' THEN
                    -- Delete reputation events given by or to this user
                    sql_statement := format('DELETE FROM %I WHERE user_id = %L OR given_by = %L', table_name, user_uuid, user_uuid);
                WHEN 'teams', 'clubs', 'community_events', 'community_challenges', 'conversations' THEN
                    -- Delete items created by this user
                    sql_statement := format('DELETE FROM %I WHERE created_by = %L', table_name, user_uuid);
                ELSE
                    -- Standard deletion by user_id
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
                -- Table doesn't exist, record as skipped
                table_results := jsonb_set(table_results, ARRAY[table_name], to_jsonb('table_not_exists'));
                RAISE NOTICE 'Table % does not exist, skipping', table_name;
            WHEN OTHERS THEN
                -- Other error, record but continue
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
        -- If anything fails, the transaction will rollback
        RAISE EXCEPTION 'Failed to delete user data for %: %', user_uuid, SQLERRM;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.delete_user_data_complete(UUID) TO authenticated;

-- Add comment for documentation
COMMENT ON FUNCTION public.delete_user_data_complete(UUID) IS 
'Deletes ALL user data from ALL tables in a single transaction. Returns a summary of the deletion process. Used for complete account deletion compliance.';

-- Create a convenience function that does both data and auth deletion
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