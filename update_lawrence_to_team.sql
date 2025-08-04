-- Update Lawrence to TEAM Level
-- Run this in your Supabase SQL Editor

-- First, let's check if Lawrence exists
SELECT id, email FROM auth.users WHERE email = 'lawrence@simcoaches.com';

-- Update Lawrence to TEAM level with full permissions
INSERT INTO public.user_hierarchy (
    user_id,
    hierarchy_level, 
    is_dev,
    is_moderator,
    dev_permissions,
    moderator_permissions,
    assigned_by
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

-- Verify the update
SELECT 
    u.email,
    uh.hierarchy_level,
    uh.is_dev,
    uh.is_moderator
FROM auth.users u
LEFT JOIN public.user_hierarchy uh ON u.id = uh.user_id
WHERE u.email = 'lawrence@simcoaches.com';

-- Also update the trigger function for future @simcoaches.com users
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