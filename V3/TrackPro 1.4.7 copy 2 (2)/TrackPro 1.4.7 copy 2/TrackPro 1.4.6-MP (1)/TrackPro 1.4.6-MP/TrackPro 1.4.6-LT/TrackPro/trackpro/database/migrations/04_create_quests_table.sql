-- Migration: Create quests table
-- This table defines various quest types that can be assigned to users

CREATE TABLE IF NOT EXISTS "quests" (
    "quest_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "quest_type" TEXT NOT NULL CHECK (quest_type IN ('daily', 'weekly', 'achievement', 'event')),
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "completion_criteria" JSONB NOT NULL,
    "xp_reward" INTEGER NOT NULL DEFAULT 0,
    "race_pass_xp_reward" INTEGER DEFAULT 0,
    "other_reward" JSONB,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    "difficulty" INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 5),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "season_id" UUID REFERENCES "race_pass_seasons"(season_id) ON DELETE SET NULL
);

-- Add RLS policies for quests
ALTER TABLE "quests" ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to view quests
CREATE POLICY "Users can view quests" 
    ON "quests" FOR SELECT 
    TO authenticated
    USING (TRUE);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_quests_timestamp
BEFORE UPDATE ON quests
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create helper function to randomly select quests for assignment
CREATE OR REPLACE FUNCTION get_random_quests(p_quest_type TEXT, p_count INTEGER)
RETURNS SETOF quests AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM quests
    WHERE quest_type = p_quest_type
    AND is_active = TRUE
    AND (season_id IS NULL OR season_id = get_current_season())
    ORDER BY RANDOM()
    LIMIT p_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 