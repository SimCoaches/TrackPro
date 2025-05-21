-- Migration to add lap_type column to laps table

-- First check if the column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'laps' 
        AND column_name = 'lap_type'
    ) THEN
        -- Add the lap_type column if it doesn't exist
        ALTER TABLE laps ADD COLUMN lap_type TEXT DEFAULT 'TIMED';
        
        -- Add a comment explaining the possible values
        COMMENT ON COLUMN laps.lap_type IS 'Type of lap: OUT (outlap), TIMED (normal racing lap), IN (inlap), or INCOMPLETE';
    END IF;
END
$$;

-- Check for is_valid_for_leaderboard column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'laps' 
        AND column_name = 'is_valid_for_leaderboard'
    ) THEN
        -- Add the is_valid_for_leaderboard column if it doesn't exist
        ALTER TABLE laps ADD COLUMN is_valid_for_leaderboard BOOLEAN DEFAULT false;
        
        -- Set initial values based on existing data
        -- Only TIMED laps that are valid should be valid for leaderboard
        UPDATE laps 
        SET is_valid_for_leaderboard = is_valid AND (lap_type = 'TIMED' OR lap_type IS NULL);
        
        -- Add a comment explaining the column
        COMMENT ON COLUMN laps.is_valid_for_leaderboard IS 'Whether this lap should be shown on leaderboards (only valid TIMED laps)';
    END IF;
END
$$; 