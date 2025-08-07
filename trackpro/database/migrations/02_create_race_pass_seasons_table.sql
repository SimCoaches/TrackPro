-- Migration: Create race_pass_seasons table
-- This table defines seasons for the Race Pass with start/end dates and number of tiers

CREATE TABLE IF NOT EXISTS "race_pass_seasons" (
    "season_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" TEXT NOT NULL,
    "description" TEXT,
    "start_date" TIMESTAMP WITH TIME ZONE NOT NULL,
    "end_date" TIMESTAMP WITH TIME ZONE NOT NULL,
    "tier_count" INTEGER NOT NULL DEFAULT 50,
    "xp_per_tier" INTEGER NOT NULL DEFAULT 1000,
    "background_url" TEXT,
    "theme_color" TEXT,
    "upsell_copy" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "is_active" BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Ensure start_date is before end_date
    CONSTRAINT start_before_end CHECK (start_date < end_date)
);

-- Create function to get current active season
CREATE OR REPLACE FUNCTION get_current_season()
RETURNS UUID AS $$
DECLARE
    current_season_id UUID;
BEGIN
    SELECT season_id INTO current_season_id
    FROM race_pass_seasons
    WHERE is_active = TRUE
    AND NOW() BETWEEN start_date AND end_date
    ORDER BY start_date DESC
    LIMIT 1;
    
    RETURN current_season_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add RLS policies for race_pass_seasons
ALTER TABLE "race_pass_seasons" ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to view race pass seasons
CREATE POLICY "Users can view race pass seasons" 
    ON "race_pass_seasons" FOR SELECT 
    TO authenticated
    USING (TRUE);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_race_pass_seasons_timestamp
BEFORE UPDATE ON race_pass_seasons
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 