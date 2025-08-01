-- Migration: Create user_quests table
-- This table tracks quest progress for each user

CREATE TABLE IF NOT EXISTS "user_quests" (
    "user_quest_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "quest_id" UUID NOT NULL REFERENCES quests(quest_id) ON DELETE CASCADE,
    "progress" JSONB NOT NULL DEFAULT '{}'::JSONB,
    "is_complete" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_claimed" BOOLEAN NOT NULL DEFAULT FALSE,
    "assigned_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "expires_at" TIMESTAMP WITH TIME ZONE,
    "completed_at" TIMESTAMP WITH TIME ZONE,
    "claimed_at" TIMESTAMP WITH TIME ZONE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Each user can only have one instance of a specific quest at a time
    UNIQUE (user_id, quest_id)
);

-- Add RLS policies for user_quests
ALTER TABLE "user_quests" ENABLE ROW LEVEL SECURITY;

-- Users can only see and update their own quests
CREATE POLICY "Users can view own quests" 
    ON "user_quests" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own quests" 
    ON "user_quests" FOR UPDATE 
    USING (auth.uid() = user_id);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_user_quests_timestamp
BEFORE UPDATE ON user_quests
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to check if quest is completed based on progress
CREATE OR REPLACE FUNCTION check_quest_completion() 
RETURNS TRIGGER AS $$
DECLARE
    quest_criteria JSONB;
    progress_check BOOLEAN := FALSE;
BEGIN
    -- Get quest completion criteria
    SELECT completion_criteria INTO quest_criteria
    FROM quests
    WHERE quest_id = NEW.quest_id;
    
    -- Evaluate if progress meets completion criteria
    -- This is a simplified version - actual implementation would need more complex logic
    -- comparing progress JSONB against quest_criteria JSONB
    
    -- For now, we just check if progress has a "completed" field set to true
    IF NEW.progress ? 'completed' AND (NEW.progress->>'completed')::BOOLEAN = TRUE THEN
        progress_check := TRUE;
    END IF;
    
    -- Or if current_value >= target_value when both fields exist
    IF NEW.progress ? 'current_value' AND quest_criteria ? 'target_value' THEN
        IF (NEW.progress->>'current_value')::NUMERIC >= (quest_criteria->>'target_value')::NUMERIC THEN
            progress_check := TRUE;
        END IF;
    END IF;
    
    -- Set is_complete and completed_at if quest is now complete
    IF progress_check = TRUE AND NEW.is_complete = FALSE THEN
        NEW.is_complete := TRUE;
        NEW.completed_at := NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to automatically check if a quest is completed when progress is updated
CREATE TRIGGER check_quest_completion_trigger
BEFORE UPDATE ON user_quests
FOR EACH ROW
WHEN (OLD.progress::TEXT IS DISTINCT FROM NEW.progress::TEXT)
EXECUTE FUNCTION check_quest_completion();

-- Function to update user XP when claiming a quest reward
CREATE OR REPLACE FUNCTION claim_quest_reward() 
RETURNS TRIGGER AS $$
DECLARE
    xp_reward INTEGER;
    race_pass_xp_reward INTEGER;
    other_reward JSONB;
BEGIN
    -- Only process if the quest is being claimed now
    IF NEW.is_claimed = TRUE AND OLD.is_claimed = FALSE AND NEW.is_complete = TRUE THEN
        -- Get quest rewards
        SELECT q.xp_reward, q.race_pass_xp_reward, q.other_reward
        INTO xp_reward, race_pass_xp_reward, other_reward
        FROM quests q
        WHERE q.quest_id = NEW.quest_id;
        
        -- Update user's XP
        UPDATE user_profiles
        SET 
            current_xp = current_xp + xp_reward,
            race_pass_xp = race_pass_xp + COALESCE(race_pass_xp_reward, 0)
        WHERE user_id = NEW.user_id;
        
        -- Set claimed timestamp
        NEW.claimed_at := NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to award XP when a quest is claimed
CREATE TRIGGER quest_reward_claim_trigger
BEFORE UPDATE ON user_quests
FOR EACH ROW
WHEN (OLD.is_claimed IS DISTINCT FROM NEW.is_claimed)
EXECUTE FUNCTION claim_quest_reward();

-- Function to get all active quests for a user
CREATE OR REPLACE FUNCTION get_user_quests(p_user_id UUID)
RETURNS TABLE (
    user_quest_id UUID,
    quest_id UUID,
    quest_type TEXT,
    name TEXT,
    description TEXT,
    progress JSONB,
    completion_criteria JSONB,
    xp_reward INTEGER,
    race_pass_xp_reward INTEGER,
    other_reward JSONB,
    is_complete BOOLEAN,
    is_claimed BOOLEAN,
    expires_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        uq.user_quest_id,
        q.quest_id,
        q.quest_type,
        q.name,
        q.description,
        uq.progress,
        q.completion_criteria,
        q.xp_reward,
        q.race_pass_xp_reward,
        q.other_reward,
        uq.is_complete,
        uq.is_claimed,
        uq.expires_at
    FROM user_quests uq
    JOIN quests q ON uq.quest_id = q.quest_id
    WHERE uq.user_id = p_user_id
    AND (uq.expires_at IS NULL OR uq.expires_at > NOW())
    ORDER BY 
        CASE q.quest_type
            WHEN 'daily' THEN 1
            WHEN 'weekly' THEN 2
            WHEN 'event' THEN 3
            WHEN 'achievement' THEN 4
            ELSE 5
        END,
        uq.is_complete,
        uq.is_claimed,
        uq.expires_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 