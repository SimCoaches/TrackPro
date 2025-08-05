-- Migration: Create public user display info table
-- This table stores public display information that should be accessible to all authenticated users
-- No RLS protection since display names are meant to be public

CREATE TABLE IF NOT EXISTS "public_user_display_info" (
    "user_id" UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    "display_name" TEXT,
    "username" TEXT,
    "avatar_url" TEXT,
    "is_online" BOOLEAN DEFAULT FALSE,
    "last_seen" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- No RLS on this table since it's meant to be public
-- This allows community messages to always show proper sender names

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_public_user_display_info_display_name ON "public_user_display_info"(display_name);
CREATE INDEX IF NOT EXISTS idx_public_user_display_info_username ON "public_user_display_info"(username);
CREATE INDEX IF NOT EXISTS idx_public_user_display_info_is_online ON "public_user_display_info"(is_online);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_public_user_display_info_timestamp
    BEFORE UPDATE ON "public_user_display_info"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to automatically create public display info on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user_display_info()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.public_user_display_info (user_id, display_name, username)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.email), COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for creating public display info on signup
CREATE TRIGGER on_auth_user_created_display_info
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_display_info(); 