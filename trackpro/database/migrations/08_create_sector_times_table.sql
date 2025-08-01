-- Migration: Create sector_times table for storing sector timing data
-- This table stores individual sector times for each lap

CREATE TABLE IF NOT EXISTS "sector_times" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "lap_id" UUID NOT NULL REFERENCES "laps"(id) ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "sector_number" INTEGER NOT NULL CHECK (sector_number > 0),
    "sector_time" REAL NOT NULL CHECK (sector_time > 0),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Ensure each lap can only have one time per sector
    UNIQUE (lap_id, sector_number)
);

-- Add RLS policies for sector_times
ALTER TABLE "sector_times" ENABLE ROW LEVEL SECURITY;

-- Users can view their own sector times
CREATE POLICY "Users can view own sector times" 
    ON "sector_times" FOR SELECT 
    USING (auth.uid() = user_id);

-- Users can insert their own sector times
CREATE POLICY "Users can insert own sector times" 
    ON "sector_times" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS "idx_sector_times_lap_id" ON "sector_times"(lap_id);
CREATE INDEX IF NOT EXISTS "idx_sector_times_user_id" ON "sector_times"(user_id);
CREATE INDEX IF NOT EXISTS "idx_sector_times_sector_number" ON "sector_times"(sector_number);

-- Function to get best sector times for a track/car combination
CREATE OR REPLACE FUNCTION get_best_sector_times(
    p_track_id UUID,
    p_car_id UUID,
    p_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    sector_number INTEGER,
    best_time REAL,
    lap_id UUID,
    user_id UUID
) AS $$
BEGIN
    RETURN QUERY
    WITH ranked_sectors AS (
        SELECT 
            st.sector_number,
            st.sector_time,
            st.lap_id,
            st.user_id,
            ROW_NUMBER() OVER (
                PARTITION BY st.sector_number 
                ORDER BY st.sector_time ASC
            ) as rn
        FROM sector_times st
        JOIN laps l ON st.lap_id = l.id
        JOIN sessions s ON l.session_id = s.id
        WHERE s.track_id = p_track_id 
        AND s.car_id = p_car_id
        AND l.is_valid = true
        AND l.is_valid_for_leaderboard = true
        AND (p_user_id IS NULL OR st.user_id = p_user_id)
    )
    SELECT 
        rs.sector_number,
        rs.sector_time as best_time,
        rs.lap_id,
        rs.user_id
    FROM ranked_sectors rs
    WHERE rs.rn = 1
    ORDER BY rs.sector_number;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get sector comparison for a specific lap
CREATE OR REPLACE FUNCTION get_sector_comparison(
    p_lap_id UUID,
    p_track_id UUID,
    p_car_id UUID
)
RETURNS TABLE (
    sector_number INTEGER,
    lap_time REAL,
    best_time REAL,
    delta REAL,
    is_personal_best BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH lap_sectors AS (
        SELECT 
            st.sector_number,
            st.sector_time as lap_time
        FROM sector_times st
        WHERE st.lap_id = p_lap_id
    ),
    best_sectors AS (
        SELECT * FROM get_best_sector_times(p_track_id, p_car_id)
    )
    SELECT 
        ls.sector_number,
        ls.lap_time,
        COALESCE(bs.best_time, ls.lap_time) as best_time,
        ls.lap_time - COALESCE(bs.best_time, ls.lap_time) as delta,
        (ls.lap_time <= COALESCE(bs.best_time, ls.lap_time)) as is_personal_best
    FROM lap_sectors ls
    LEFT JOIN best_sectors bs ON ls.sector_number = bs.sector_number
    ORDER BY ls.sector_number;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comment explaining the table
COMMENT ON TABLE "sector_times" IS 'Stores individual sector times for each lap, enabling detailed sector analysis and comparison'; 