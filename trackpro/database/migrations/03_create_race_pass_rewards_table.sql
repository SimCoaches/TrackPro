-- Migration: Create race_pass_rewards table
-- This table defines rewards for each tier of a race pass season

CREATE TABLE IF NOT EXISTS "race_pass_rewards" (
    "reward_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "season_id" UUID NOT NULL REFERENCES "race_pass_seasons"(season_id) ON DELETE CASCADE,
    "tier" INTEGER NOT NULL,
    "is_premium_reward" BOOLEAN NOT NULL DEFAULT FALSE,
    "reward_type" TEXT NOT NULL CHECK (reward_type IN ('title', 'badge', 'cosmetic', 'xp_boost', 'currency')),
    "reward_details" JSONB NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Each tier can have only one premium and one free reward
    UNIQUE (season_id, tier, is_premium_reward)
);

-- Add RLS policies for race_pass_rewards
ALTER TABLE "race_pass_rewards" ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to view race pass rewards
CREATE POLICY "Users can view race pass rewards" 
    ON "race_pass_rewards" FOR SELECT 
    TO authenticated
    USING (TRUE);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_race_pass_rewards_timestamp
BEFORE UPDATE ON race_pass_rewards
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to get user's available rewards
CREATE OR REPLACE FUNCTION get_user_available_rewards(p_user_id UUID)
RETURNS TABLE (
    reward_id UUID,
    season_id UUID,
    tier INTEGER,
    is_premium_reward BOOLEAN,
    reward_type TEXT,
    reward_details JSONB,
    is_unlocked BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH user_progress AS (
        SELECT 
            up.race_pass_season_id, 
            up.race_pass_tier, 
            up.is_premium_pass_active
        FROM user_profiles up
        WHERE up.user_id = p_user_id
    )
    SELECT 
        rpr.reward_id,
        rpr.season_id,
        rpr.tier,
        rpr.is_premium_reward,
        rpr.reward_type,
        rpr.reward_details,
        CASE 
            WHEN rpr.tier <= up.race_pass_tier AND 
                 (NOT rpr.is_premium_reward OR up.is_premium_pass_active) 
            THEN TRUE
            ELSE FALSE
        END AS is_unlocked
    FROM race_pass_rewards rpr
    JOIN user_progress up ON rpr.season_id = up.race_pass_season_id
    ORDER BY rpr.tier, rpr.is_premium_reward;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 