-- Migration: Update hierarchy assignment for @simcoaches.com domain
-- This migration updates the user hierarchy trigger to automatically assign TEAM level to @simcoaches.com users

-- =====================================================
-- UPDATE HIERARCHY TRIGGER FOR SIMCOACHES DOMAIN
-- =====================================================

-- Update the function to automatically assign TEAM level to @simcoaches.com users
CREATE OR REPLACE FUNCTION public.handle_new_user_hierarchy()
RETURNS TRIGGER AS $$
DECLARE
    user_hierarchy_level VARCHAR(20);
    user_is_dev BOOLEAN;
    user_is_moderator BOOLEAN;
    dev_permissions JSONB;
    moderator_permissions JSONB;
BEGIN
    -- Check if user has @simcoaches.com email
    IF NEW.email LIKE '%@simcoaches.com' THEN
        -- Assign TEAM level with full permissions
        user_hierarchy_level := 'TEAM';
        user_is_dev := TRUE;
        user_is_moderator := TRUE;
        dev_permissions := '{"all_permissions": true, "user_management": true, "content_moderation": true, "system_admin": true}'::jsonb;
        moderator_permissions := '{"content_moderation": true, "user_reports": true, "community_management": true}'::jsonb;
    ELSE
        -- Default to PADDOCK level for other users
        user_hierarchy_level := 'PADDOCK';
        user_is_dev := FALSE;
        user_is_moderator := FALSE;
        dev_permissions := '{}'::jsonb;
        moderator_permissions := '{}'::jsonb;
    END IF;
    
    -- Insert user hierarchy with appropriate level
    INSERT INTO public.user_hierarchy (
        user_id, 
        hierarchy_level, 
        is_dev, 
        is_moderator, 
        dev_permissions, 
        moderator_permissions,
        assigned_by
    ) VALUES (
        NEW.id, 
        user_hierarchy_level,
        user_is_dev,
        user_is_moderator,
        dev_permissions,
        moderator_permissions,
        NEW.id  -- Self-assigned
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- UPDATE EXISTING SIMCOACHES USERS
-- =====================================================

-- Update any existing @simcoaches.com users to TEAM level
UPDATE public.user_hierarchy 
SET 
    hierarchy_level = 'TEAM',
    is_dev = TRUE,
    is_moderator = TRUE,
    dev_permissions = '{"all_permissions": true, "user_management": true, "content_moderation": true, "system_admin": true}'::jsonb,
    moderator_permissions = '{"content_moderation": true, "user_reports": true, "community_management": true}'::jsonb,
    updated_at = NOW()
WHERE user_id IN (
    SELECT id FROM auth.users 
    WHERE email LIKE '%@simcoaches.com'
);

-- =====================================================
-- VERIFICATION QUERY
-- =====================================================

-- This query can be run to verify the setup:
-- SELECT 
--     u.email,
--     uh.hierarchy_level,
--     uh.is_dev,
--     uh.is_moderator
-- FROM auth.users u
-- LEFT JOIN public.user_hierarchy uh ON u.id = uh.user_id
-- WHERE u.email LIKE '%@simcoaches.com'; 