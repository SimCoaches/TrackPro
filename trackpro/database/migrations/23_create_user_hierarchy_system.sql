-- Migration: Create user hierarchy system
-- This migration creates the user hierarchy system with roles and permissions

-- =====================================================
-- USER HIERARCHY SYSTEM
-- =====================================================

-- Create user hierarchy table
CREATE TABLE IF NOT EXISTS "user_hierarchy" (
    "user_id" UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    "hierarchy_level" VARCHAR(20) NOT NULL DEFAULT 'PADDOCK',
    "is_dev" BOOLEAN DEFAULT FALSE,
    "is_moderator" BOOLEAN DEFAULT FALSE,
    "dev_permissions" JSONB DEFAULT '{}',
    "moderator_permissions" JSONB DEFAULT '{}',
    "assigned_by" UUID REFERENCES auth.users(id),
    "assigned_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add RLS (Row Level Security) policies
ALTER TABLE "user_hierarchy" ENABLE ROW LEVEL SECURITY;

-- Users can view their own hierarchy
CREATE POLICY "Users can view own hierarchy" 
    ON "user_hierarchy" FOR SELECT 
    USING (auth.uid() = user_id);

-- Only dev users can modify hierarchy
CREATE POLICY "Dev users can modify hierarchy" 
    ON "user_hierarchy" FOR ALL 
    USING (
        EXISTS (
            SELECT 1 FROM "user_hierarchy" 
            WHERE user_id = auth.uid() AND is_dev = TRUE
        )
    );

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_hierarchy_level ON "user_hierarchy"(hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_user_hierarchy_is_dev ON "user_hierarchy"(is_dev);
CREATE INDEX IF NOT EXISTS idx_user_hierarchy_is_moderator ON "user_hierarchy"(is_moderator);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_user_hierarchy_timestamp
    BEFORE UPDATE ON "user_hierarchy"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to automatically create user hierarchy on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user_hierarchy()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_hierarchy (user_id, hierarchy_level)
    VALUES (NEW.id, 'PADDOCK');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for creating user hierarchy on signup
CREATE TRIGGER on_auth_user_created_hierarchy
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_hierarchy();

-- =====================================================
-- HIERARCHY LEVEL ENUMERATION
-- =====================================================

-- Create enum for hierarchy levels
DO $$ BEGIN
    CREATE TYPE hierarchy_level_enum AS ENUM ('TEAM', 'SPONSORED_DRIVERS', 'DRIVERS', 'PADDOCK');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =====================================================
-- INITIAL SETUP FOR LAWRENCE@SIMCOACHES.COM
-- =====================================================

-- Insert the initial DEV user with MODERATOR controls
INSERT INTO "user_hierarchy" (
    "user_id",
    "hierarchy_level", 
    "is_dev",
    "is_moderator",
    "dev_permissions",
    "moderator_permissions",
    "assigned_by"
) VALUES (
    (SELECT id FROM auth.users WHERE email = 'lawrence@simcoaches.com'),
    'TEAM',
    TRUE,
    TRUE,
    '{"all_permissions": true, "user_management": true, "content_moderation": true, "system_admin": true}'::jsonb,
    '{"content_moderation": true, "user_reports": true, "community_management": true}'::jsonb,
    (SELECT id FROM auth.users WHERE email = 'lawrence@simcoaches.com')
) ON CONFLICT (user_id) DO UPDATE SET
    hierarchy_level = 'TEAM',
    is_dev = TRUE,
    is_moderator = TRUE,
    dev_permissions = '{"all_permissions": true, "user_management": true, "content_moderation": true, "system_admin": true}'::jsonb,
    moderator_permissions = '{"content_moderation": true, "user_reports": true, "community_management": true}'::jsonb,
    updated_at = NOW();

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to check if user has dev permissions
CREATE OR REPLACE FUNCTION public.is_user_dev(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_hierarchy 
        WHERE user_id = user_uuid AND is_dev = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user has moderator permissions
CREATE OR REPLACE FUNCTION public.is_user_moderator(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_hierarchy 
        WHERE user_id = user_uuid AND is_moderator = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user hierarchy level
CREATE OR REPLACE FUNCTION public.get_user_hierarchy_level(user_uuid UUID)
RETURNS VARCHAR(20) AS $$
DECLARE
    level VARCHAR(20);
BEGIN
    SELECT hierarchy_level INTO level
    FROM user_hierarchy 
    WHERE user_id = user_uuid;
    
    RETURN COALESCE(level, 'PADDOCK');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user can modify another user's hierarchy
CREATE OR REPLACE FUNCTION public.can_modify_hierarchy(modifier_uuid UUID, target_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Dev users can modify anyone
    IF public.is_user_dev(modifier_uuid) THEN
        RETURN TRUE;
    END IF;
    
    -- Moderators can modify users below them in hierarchy
    IF public.is_user_moderator(modifier_uuid) THEN
        RETURN public.get_user_hierarchy_level(modifier_uuid) > public.get_user_hierarchy_level(target_uuid);
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE "user_hierarchy" IS 'User hierarchy system with roles and permissions';
COMMENT ON COLUMN "user_hierarchy"."hierarchy_level" IS 'User hierarchy level: TEAM, SPONSORED_DRIVERS, DRIVERS, PADDOCK';
COMMENT ON COLUMN "user_hierarchy"."is_dev" IS 'Whether user has developer permissions';
COMMENT ON COLUMN "user_hierarchy"."is_moderator" IS 'Whether user has moderator permissions';
COMMENT ON COLUMN "user_hierarchy"."dev_permissions" IS 'JSON object containing specific dev permissions';
COMMENT ON COLUMN "user_hierarchy"."moderator_permissions" IS 'JSON object containing specific moderator permissions'; 