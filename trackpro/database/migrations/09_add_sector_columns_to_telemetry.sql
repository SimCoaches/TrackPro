-- Migration: Add sector timing columns to telemetry_points table
-- This allows us to track which sector each telemetry point belongs to and the current sector time

-- Add current_sector column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'telemetry_points' 
        AND column_name = 'current_sector'
    ) THEN
        ALTER TABLE "telemetry_points" ADD COLUMN "current_sector" INTEGER;
        COMMENT ON COLUMN "telemetry_points"."current_sector" IS 'The sector number (1, 2, 3, etc.) that this telemetry point belongs to';
    END IF;
END
$$;

-- Add current_sector_time column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'telemetry_points' 
        AND column_name = 'current_sector_time'
    ) THEN
        ALTER TABLE "telemetry_points" ADD COLUMN "current_sector_time" REAL;
        COMMENT ON COLUMN "telemetry_points"."current_sector_time" IS 'The elapsed time in the current sector at this telemetry point';
    END IF;
END
$$;

-- Create index for sector-based queries
CREATE INDEX IF NOT EXISTS "idx_telemetry_points_current_sector" ON "telemetry_points"(current_sector);

-- Function to get telemetry data for a specific sector of a lap
CREATE OR REPLACE FUNCTION get_lap_sector_telemetry(
    p_lap_id UUID,
    p_sector_number INTEGER
)
RETURNS TABLE (
    timestamp REAL,
    track_position REAL,
    speed REAL,
    throttle REAL,
    brake REAL,
    steering REAL,
    current_sector_time REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tp.timestamp,
        tp.track_position,
        tp.speed,
        tp.throttle,
        tp.brake,
        tp.steering,
        tp.current_sector_time
    FROM telemetry_points tp
    WHERE tp.lap_id = p_lap_id
    AND tp.current_sector = p_sector_number
    ORDER BY tp.track_position;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 