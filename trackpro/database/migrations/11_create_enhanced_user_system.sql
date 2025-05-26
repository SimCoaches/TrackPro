-- Enhanced User Account System Migration
-- This migration creates all tables needed for the comprehensive user account system
-- as outlined in USER-ACCOUNT.MD

-- =====================================================
-- ENHANCED USER PROFILES
-- =====================================================

-- Enhanced user profiles table (extends existing user_profiles)
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS username VARCHAR(50) UNIQUE;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS location VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS avatar_frame_id UUID;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS profile_theme VARCHAR(50) DEFAULT 'default';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS social_xp BIGINT DEFAULT 0;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS prestige_level INTEGER DEFAULT 0;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS reputation_score INTEGER DEFAULT 0;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS privacy_settings JSONB DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';

-- User statistics and metrics
CREATE TABLE IF NOT EXISTS user_stats (
    user_id UUID PRIMARY KEY REFERENCES user_profiles(user_id),
    total_laps INTEGER DEFAULT 0,
    total_distance_km DECIMAL DEFAULT 0,
    total_time_seconds BIGINT DEFAULT 0,
    best_lap_time DECIMAL,
    favorite_track_id INTEGER,
    favorite_car_id INTEGER,
    consistency_rating DECIMAL DEFAULT 0,
    improvement_rate DECIMAL DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Avatar frames system
CREATE TABLE IF NOT EXISTS avatar_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    image_url TEXT,
    rarity VARCHAR(20) DEFAULT 'common',
    unlock_requirements JSONB DEFAULT '{}',
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- SOCIAL SYSTEM
-- =====================================================

-- Friends system
CREATE TABLE IF NOT EXISTS friendships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id UUID REFERENCES user_profiles(user_id),
    addressee_id UUID REFERENCES user_profiles(user_id),
    status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, blocked
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(requester_id, addressee_id)
);

-- Messaging system
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(20) DEFAULT 'direct', -- direct, group
    name VARCHAR(100), -- for group chats
    created_by UUID REFERENCES user_profiles(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_participants (
    conversation_id UUID REFERENCES conversations(id),
    user_id UUID REFERENCES user_profiles(user_id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_read_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (conversation_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    sender_id UUID REFERENCES user_profiles(user_id),
    content TEXT,
    message_type VARCHAR(20) DEFAULT 'text', -- text, image, file, telemetry
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    edited_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Activity feed
CREATE TABLE IF NOT EXISTS user_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(user_id),
    activity_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    privacy_level VARCHAR(20) DEFAULT 'friends', -- public, friends, private
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS activity_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id UUID REFERENCES user_activities(id),
    user_id UUID REFERENCES user_profiles(user_id),
    interaction_type VARCHAR(20) NOT NULL, -- like, comment, share
    content TEXT, -- for comments
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(activity_id, user_id, interaction_type)
);

-- =====================================================
-- COMMUNITY FEATURES
-- =====================================================

-- Racing teams
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    logo_url TEXT,
    color_scheme JSONB DEFAULT '{}',
    created_by UUID REFERENCES user_profiles(user_id),
    max_members INTEGER DEFAULT 50,
    privacy_level VARCHAR(20) DEFAULT 'public',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id UUID REFERENCES teams(id),
    user_id UUID REFERENCES user_profiles(user_id),
    role VARCHAR(20) DEFAULT 'member', -- owner, admin, member
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

-- Racing clubs
CREATE TABLE IF NOT EXISTS clubs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50), -- GT3, Formula, Oval, etc.
    logo_url TEXT,
    created_by UUID REFERENCES user_profiles(user_id),
    member_count INTEGER DEFAULT 0,
    privacy_level VARCHAR(20) DEFAULT 'public',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS club_members (
    club_id UUID REFERENCES clubs(id),
    user_id UUID REFERENCES user_profiles(user_id),
    role VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (club_id, user_id)
);

-- Community events
CREATE TABLE IF NOT EXISTS community_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    event_type VARCHAR(50), -- time_trial, race, championship
    track_id INTEGER,
    car_id INTEGER,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES user_profiles(user_id),
    max_participants INTEGER,
    entry_requirements JSONB DEFAULT '{}',
    prizes JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'upcoming',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_participants (
    event_id UUID REFERENCES community_events(id),
    user_id UUID REFERENCES user_profiles(user_id),
    registration_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'registered',
    PRIMARY KEY (event_id, user_id)
);

-- =====================================================
-- ENHANCED GAMIFICATION
-- =====================================================

-- Enhanced achievements system
CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50),
    rarity VARCHAR(20) DEFAULT 'common', -- common, rare, epic, legendary
    icon_url TEXT,
    xp_reward INTEGER DEFAULT 0,
    requirements JSONB DEFAULT '{}',
    is_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id UUID REFERENCES user_profiles(user_id),
    achievement_id UUID REFERENCES achievements(id),
    progress JSONB DEFAULT '{}',
    unlocked_at TIMESTAMP WITH TIME ZONE,
    is_showcased BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, achievement_id)
);

-- Streak system
CREATE TABLE IF NOT EXISTS user_streaks (
    user_id UUID REFERENCES user_profiles(user_id),
    streak_type VARCHAR(50),
    current_count INTEGER DEFAULT 0,
    best_count INTEGER DEFAULT 0,
    last_activity_date DATE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, streak_type)
);

-- Reputation system
CREATE TABLE IF NOT EXISTS reputation_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(user_id),
    given_by UUID REFERENCES user_profiles(user_id),
    event_type VARCHAR(50), -- helpful, sportsmanlike, toxic, etc.
    points INTEGER,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Content sharing
CREATE TABLE IF NOT EXISTS shared_setups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(user_id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    car_id INTEGER,
    track_id INTEGER,
    setup_data JSONB,
    rating DECIMAL DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    tags TEXT[],
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS setup_ratings (
    setup_id UUID REFERENCES shared_setups(id),
    user_id UUID REFERENCES user_profiles(user_id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (setup_id, user_id)
);

-- Media sharing
CREATE TABLE IF NOT EXISTS shared_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(user_id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    media_type VARCHAR(20), -- screenshot, video, replay
    file_url TEXT,
    thumbnail_url TEXT,
    track_id INTEGER,
    car_id INTEGER,
    lap_time DECIMAL,
    tags TEXT[],
    like_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS media_likes (
    media_id UUID REFERENCES shared_media(id),
    user_id UUID REFERENCES user_profiles(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (media_id, user_id)
);

-- =====================================================
-- LEADERBOARDS AND RANKINGS
-- =====================================================

-- Global leaderboards
CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(user_id),
    leaderboard_type VARCHAR(50), -- track_time, consistency, improvement
    track_id INTEGER,
    car_id INTEGER,
    value DECIMAL,
    metadata JSONB DEFAULT '{}',
    season VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Community challenges
CREATE TABLE IF NOT EXISTS community_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    challenge_type VARCHAR(50), -- time_attack, consistency, improvement
    track_id INTEGER,
    car_id INTEGER,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    requirements JSONB DEFAULT '{}',
    rewards JSONB DEFAULT '{}',
    participant_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES user_profiles(user_id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS challenge_participants (
    challenge_id UUID REFERENCES community_challenges(id),
    user_id UUID REFERENCES user_profiles(user_id),
    best_result DECIMAL,
    submission_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_submission TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (challenge_id, user_id)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- User profiles indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);
CREATE INDEX IF NOT EXISTS idx_user_profiles_reputation ON user_profiles(reputation_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_profiles_level ON user_profiles(level DESC);

-- Social system indexes
CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester_id);
CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX IF NOT EXISTS idx_friendships_status ON friendships(status);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_created_at ON user_activities(created_at DESC);

-- Community indexes
CREATE INDEX IF NOT EXISTS idx_teams_created_by ON teams(created_by);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_clubs_category ON clubs(category);
CREATE INDEX IF NOT EXISTS idx_community_events_start_time ON community_events(start_time);

-- Gamification indexes
CREATE INDEX IF NOT EXISTS idx_achievements_category ON achievements(category);
CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_user_streaks_user_id ON user_streaks(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_entries_type_track ON leaderboard_entries(leaderboard_type, track_id);

-- =====================================================
-- TRIGGERS AND FUNCTIONS
-- =====================================================

-- Function to update user stats
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE user_stats 
    SET last_active = NOW(), updated_at = NOW()
    WHERE user_id = NEW.user_id;
    
    IF NOT FOUND THEN
        INSERT INTO user_stats (user_id, last_active, updated_at)
        VALUES (NEW.user_id, NOW(), NOW());
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update user stats on activity
CREATE TRIGGER trigger_update_user_stats
    AFTER INSERT ON user_activities
    FOR EACH ROW
    EXECUTE FUNCTION update_user_stats();

-- Function to update club member count
CREATE OR REPLACE FUNCTION update_club_member_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE clubs 
        SET member_count = member_count + 1
        WHERE id = NEW.club_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE clubs 
        SET member_count = member_count - 1
        WHERE id = OLD.club_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers for club member count
CREATE TRIGGER trigger_club_member_count_insert
    AFTER INSERT ON club_members
    FOR EACH ROW
    EXECUTE FUNCTION update_club_member_count();

CREATE TRIGGER trigger_club_member_count_delete
    AFTER DELETE ON club_members
    FOR EACH ROW
    EXECUTE FUNCTION update_club_member_count();

-- Function to update media like count
CREATE OR REPLACE FUNCTION update_media_like_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE shared_media 
        SET like_count = like_count + 1
        WHERE id = NEW.media_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE shared_media 
        SET like_count = like_count - 1
        WHERE id = OLD.media_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Triggers for media like count
CREATE TRIGGER trigger_media_like_count_insert
    AFTER INSERT ON media_likes
    FOR EACH ROW
    EXECUTE FUNCTION update_media_like_count();

CREATE TRIGGER trigger_media_like_count_delete
    AFTER DELETE ON media_likes
    FOR EACH ROW
    EXECUTE FUNCTION update_media_like_count();

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default avatar frames
INSERT INTO avatar_frames (name, description, image_url, rarity, unlock_requirements) VALUES
('Default', 'Basic avatar frame', '/avatars/frames/default.png', 'common', '{}'),
('Bronze Racer', 'For completing your first race', '/avatars/frames/bronze.png', 'common', '{"races_completed": 1}'),
('Silver Speedster', 'For achieving 10 personal bests', '/avatars/frames/silver.png', 'rare', '{"personal_bests": 10}'),
('Gold Champion', 'For winning 5 community events', '/avatars/frames/gold.png', 'epic', '{"events_won": 5}'),
('Legendary Driver', 'For reaching prestige level 1', '/avatars/frames/legendary.png', 'legendary', '{"prestige_level": 1}')
ON CONFLICT (name) DO NOTHING;

-- Insert default achievements
INSERT INTO achievements (name, description, category, rarity, icon_url, xp_reward, requirements) VALUES
('First Steps', 'Complete your first lap', 'racing', 'common', '/achievements/first_steps.png', 100, '{"laps_completed": 1}'),
('Speed Demon', 'Achieve a lap time under 2 minutes', 'racing', 'rare', '/achievements/speed_demon.png', 500, '{"best_lap_time": 120}'),
('Social Butterfly', 'Add 10 friends', 'social', 'common', '/achievements/social_butterfly.png', 200, '{"friends_count": 10}'),
('Team Player', 'Join a racing team', 'community', 'common', '/achievements/team_player.png', 150, '{"teams_joined": 1}'),
('Consistency King', 'Complete 10 laps within 1% of each other', 'racing', 'epic', '/achievements/consistency_king.png', 1000, '{"consistent_laps": 10}'),
('Community Leader', 'Create a racing club', 'community', 'rare', '/achievements/community_leader.png', 750, '{"clubs_created": 1}'),
('Mentor', 'Help 5 new drivers improve their times', 'social', 'epic', '/achievements/mentor.png', 1500, '{"drivers_helped": 5}'),
('Track Master', 'Set personal bests on 20 different tracks', 'racing', 'legendary', '/achievements/track_master.png', 2500, '{"tracks_mastered": 20}')
ON CONFLICT (name) DO NOTHING;

-- Insert default streak types
INSERT INTO user_streaks (user_id, streak_type, current_count, best_count, last_activity_date, started_at)
SELECT user_id, 'daily_login', 0, 0, CURRENT_DATE, NOW()
FROM user_profiles
WHERE NOT EXISTS (
    SELECT 1 FROM user_streaks 
    WHERE user_streaks.user_id = user_profiles.user_id 
    AND streak_type = 'daily_login'
);

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for user profile with stats
CREATE OR REPLACE VIEW user_profile_complete AS
SELECT 
    up.*,
    us.total_laps,
    us.total_distance_km,
    us.total_time_seconds,
    us.best_lap_time,
    us.consistency_rating,
    us.improvement_rate,
    us.last_active,
    af.name as avatar_frame_name,
    af.image_url as avatar_frame_url
FROM user_profiles up
LEFT JOIN user_stats us ON up.user_id = us.user_id
LEFT JOIN avatar_frames af ON up.avatar_frame_id = af.id;

-- View for friend relationships
CREATE OR REPLACE VIEW user_friends AS
SELECT 
    f.requester_id as user_id,
    f.addressee_id as friend_id,
    up.username as friend_username,
    up.display_name as friend_display_name,
    up.avatar_url as friend_avatar_url,
    f.created_at as friendship_date
FROM friendships f
JOIN user_profiles up ON f.addressee_id = up.user_id
WHERE f.status = 'accepted'
UNION
SELECT 
    f.addressee_id as user_id,
    f.requester_id as friend_id,
    up.username as friend_username,
    up.display_name as friend_display_name,
    up.avatar_url as friend_avatar_url,
    f.created_at as friendship_date
FROM friendships f
JOIN user_profiles up ON f.requester_id = up.user_id
WHERE f.status = 'accepted';

-- View for leaderboards
CREATE OR REPLACE VIEW track_leaderboards AS
SELECT 
    le.*,
    up.username,
    up.display_name,
    up.avatar_url,
    ROW_NUMBER() OVER (PARTITION BY le.track_id, le.car_id ORDER BY le.value ASC) as rank
FROM leaderboard_entries le
JOIN user_profiles up ON le.user_id = up.user_id
WHERE le.leaderboard_type = 'track_time';

COMMENT ON TABLE user_profiles IS 'Enhanced user profiles with social features';
COMMENT ON TABLE friendships IS 'Friend relationships between users';
COMMENT ON TABLE conversations IS 'Chat conversations (direct and group)';
COMMENT ON TABLE messages IS 'Messages within conversations';
COMMENT ON TABLE user_activities IS 'User activity feed entries';
COMMENT ON TABLE teams IS 'Racing teams created by users';
COMMENT ON TABLE clubs IS 'Racing clubs for community interaction';
COMMENT ON TABLE community_events IS 'Community-organized racing events';
COMMENT ON TABLE achievements IS 'Available achievements in the system';
COMMENT ON TABLE user_achievements IS 'User progress on achievements';
COMMENT ON TABLE user_streaks IS 'User streak tracking (daily login, etc.)';
COMMENT ON TABLE reputation_events IS 'Reputation system events';
COMMENT ON TABLE shared_setups IS 'User-shared car setups';
COMMENT ON TABLE shared_media IS 'User-shared media (screenshots, videos)';
COMMENT ON TABLE leaderboard_entries IS 'Global leaderboard entries';
COMMENT ON TABLE community_challenges IS 'Community challenges and competitions'; 