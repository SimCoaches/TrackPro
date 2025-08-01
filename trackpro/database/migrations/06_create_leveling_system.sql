-- Migration: Create leveling system functions
-- These functions handle XP calculations, level progression, and XP rewarding

-- Function to calculate XP needed for a specific level
CREATE OR REPLACE FUNCTION calculate_xp_for_level(p_level INTEGER)
RETURNS INTEGER AS $$
DECLARE
    base_xp INTEGER := 100;
    exponent FLOAT := 1.5;
BEGIN
    -- Formula: required_xp = base_xp * (level ^ exponent)
    RETURN FLOOR(base_xp * POWER(p_level, exponent))::INTEGER;
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;

-- Function to check if user should level up and apply level up if needed
CREATE OR REPLACE FUNCTION check_and_apply_level_up()
RETURNS TRIGGER AS $$
DECLARE
    next_level INTEGER;
    xp_needed_for_next_level INTEGER;
BEGIN
    -- Only run if XP has increased
    IF NEW.current_xp > OLD.current_xp THEN
        -- Initialize variables
        next_level := NEW.level + 1;
        xp_needed_for_next_level := calculate_xp_for_level(next_level);
        
        -- Update total_xp_needed for current level progress bar
        NEW.total_xp_needed := xp_needed_for_next_level;
        
        -- Check if should level up (potentially multiple times)
        WHILE NEW.current_xp >= xp_needed_for_next_level LOOP
            -- Level up
            NEW.level := next_level;
            
            -- Calculate next level requirements
            next_level := NEW.level + 1;
            xp_needed_for_next_level := calculate_xp_for_level(next_level);
            NEW.total_xp_needed := xp_needed_for_next_level;
        END LOOP;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to automatically check for level up when XP changes
CREATE TRIGGER check_level_up_trigger
BEFORE UPDATE ON user_profiles
FOR EACH ROW
WHEN (OLD.current_xp IS DISTINCT FROM NEW.current_xp)
EXECUTE FUNCTION check_and_apply_level_up();

-- Function to check if race pass tier should increase and apply if needed
CREATE OR REPLACE FUNCTION check_and_apply_race_pass_tier_up()
RETURNS TRIGGER AS $$
DECLARE
    season_record RECORD;
    xp_per_tier INTEGER := 1000; -- Default value, could be made configurable per season
BEGIN
    -- Only run if race pass XP has increased
    IF NEW.race_pass_xp > OLD.race_pass_xp AND NEW.race_pass_season_id IS NOT NULL THEN
        -- Get season data
        SELECT * INTO season_record
        FROM race_pass_seasons
        WHERE season_id = NEW.race_pass_season_id;
        
        IF FOUND THEN
            -- Calculate new tier based on XP
            NEW.race_pass_tier := LEAST(
                FLOOR(NEW.race_pass_xp / xp_per_tier)::INTEGER,
                season_record.tier_count
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to automatically check for race pass tier up when XP changes
CREATE TRIGGER check_race_pass_tier_up_trigger
BEFORE UPDATE ON user_profiles
FOR EACH ROW
WHEN (OLD.race_pass_xp IS DISTINCT FROM NEW.race_pass_xp)
EXECUTE FUNCTION check_and_apply_race_pass_tier_up();

-- Function to award XP for completing activities
CREATE OR REPLACE FUNCTION award_xp(
    p_user_id UUID,
    p_xp_amount INTEGER,
    p_race_pass_xp INTEGER DEFAULT 0
)
RETURNS BOOLEAN AS $$
DECLARE
    success BOOLEAN := FALSE;
BEGIN
    -- Update user XP
    UPDATE user_profiles
    SET 
        current_xp = current_xp + p_xp_amount,
        race_pass_xp = race_pass_xp + COALESCE(p_race_pass_xp, 0)
    WHERE user_id = p_user_id;
    
    GET DIAGNOSTICS success = ROW_COUNT;
    RETURN success;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 