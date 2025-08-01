-- Migration: Add check constraint for lap_type column validation
-- Description: Ensures lap_type can only be one of the valid values: OUT, TIMED, IN, or INCOMPLETE

-- Add check constraint if it doesn't exist
DO $$
BEGIN
    -- Check if the constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_lap_type'
    ) THEN
        -- Add the check constraint
        ALTER TABLE "laps" 
        ADD CONSTRAINT "check_lap_type" 
        CHECK ("lap_type" IN ('OUT', 'TIMED', 'IN', 'INCOMPLETE'));
        
        RAISE NOTICE 'Added check constraint for lap_type column';
    ELSE
        RAISE NOTICE 'Check constraint for lap_type already exists';
    END IF;
END
$$;

-- Verify the constraint was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_lap_type'
    ) THEN
        RAISE NOTICE '✅ lap_type check constraint is active and will validate values';
    ELSE
        RAISE EXCEPTION 'Failed to add lap_type check constraint';
    END IF;
END
$$; 