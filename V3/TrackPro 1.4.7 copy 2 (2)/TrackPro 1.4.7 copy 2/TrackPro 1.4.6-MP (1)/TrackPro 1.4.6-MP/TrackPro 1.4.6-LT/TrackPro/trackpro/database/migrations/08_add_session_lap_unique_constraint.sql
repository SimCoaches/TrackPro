-- Migration: Add unique constraint on (session_id, lap_number) in laps table
-- Description: Ensures no lap can be overwritten by a subsequent lap with the same number
-- This is a fix for the Bullring pit-exit misalignment causing off-by-one laps

-- Function to check if the constraint already exists
DO $$
DECLARE
    constraint_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'laps_session_id_lap_number_unique'
    ) INTO constraint_exists;

    IF NOT constraint_exists THEN
        -- Add the unique constraint
        ALTER TABLE laps 
        ADD CONSTRAINT laps_session_id_lap_number_unique 
        UNIQUE (session_id, lap_number);
        
        -- Log the migration
        RAISE NOTICE 'Added unique constraint on (session_id, lap_number) in laps table';
    ELSE
        RAISE NOTICE 'Unique constraint on (session_id, lap_number) already exists in laps table';
    END IF;
END$$;

-- Update the schema version in the metadata table if one exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_metadata') THEN
        UPDATE schema_metadata 
        SET version = '1.4.7', 
            description = 'Added unique constraint on (session_id, lap_number) in laps table',
            updated_at = NOW();
    END IF;
END$$; 