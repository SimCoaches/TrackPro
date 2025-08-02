-- Migration: Add basic profile fields to user_profiles table
-- This adds personal information fields that users can fill out in their profile

ALTER TABLE "user_profiles" 
ADD COLUMN IF NOT EXISTS "email" TEXT,
ADD COLUMN IF NOT EXISTS "first_name" TEXT,
ADD COLUMN IF NOT EXISTS "last_name" TEXT,
ADD COLUMN IF NOT EXISTS "display_name" TEXT,
ADD COLUMN IF NOT EXISTS "bio" TEXT;

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON "user_profiles" (email);

-- Create index on display_name for search functionality
CREATE INDEX IF NOT EXISTS idx_user_profiles_display_name ON "user_profiles" (display_name);

-- Add policy for users to insert their own profile (needed for upsert operations)
CREATE POLICY "Users can insert own profile" 
    ON "user_profiles" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Update the handle_new_user function to also set email from auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add a comment to document the new fields
COMMENT ON COLUMN "user_profiles"."email" IS 'User email address from authentication';
COMMENT ON COLUMN "user_profiles"."first_name" IS 'User first name';
COMMENT ON COLUMN "user_profiles"."last_name" IS 'User last name';
COMMENT ON COLUMN "user_profiles"."display_name" IS 'User preferred display name (optional)';
COMMENT ON COLUMN "user_profiles"."bio" IS 'User biography or description (optional)';