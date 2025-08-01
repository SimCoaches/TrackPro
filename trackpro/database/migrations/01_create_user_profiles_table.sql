-- Migration: Create user_profiles table for gamification
-- This table tracks user progress in the gamification system including level, XP, and race pass progression

CREATE TABLE IF NOT EXISTS "user_profiles" (
    "user_id" UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    "level" INTEGER NOT NULL DEFAULT 1,
    "current_xp" INTEGER NOT NULL DEFAULT 0,
    "total_xp_needed" INTEGER NOT NULL DEFAULT 100,
    "race_pass_season_id" UUID REFERENCES "race_pass_seasons"(season_id) NULL,
    "race_pass_tier" INTEGER NOT NULL DEFAULT 0,
    "race_pass_xp" INTEGER NOT NULL DEFAULT 0,
    "is_premium_pass_active" BOOLEAN NOT NULL DEFAULT FALSE,
    "selected_title" TEXT NULL,
    "unlocked_titles" JSONB DEFAULT '[]'::JSONB NOT NULL,
    "unlocked_cosmetics" JSONB DEFAULT '[]'::JSONB NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add RLS (Row Level Security) policies
ALTER TABLE "user_profiles" ENABLE ROW LEVEL SECURITY;

-- Users can only read, update their own profile
CREATE POLICY "Users can view own profile" 
    ON "user_profiles" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" 
    ON "user_profiles" FOR UPDATE 
    USING (auth.uid() = user_id);

-- Create function to automatically create user_profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for creating user profile on signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Create trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_profiles_timestamp
BEFORE UPDATE ON user_profiles
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 