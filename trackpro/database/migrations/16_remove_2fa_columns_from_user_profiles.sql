-- Remove phone number and 2FA verification columns from user_profiles table
-- These columns were incorrectly added to user_profiles and should be in user_details

-- Drop indexes first
DROP INDEX IF EXISTS idx_user_profiles_phone_number;
DROP INDEX IF EXISTS idx_user_profiles_2fa_enabled;

-- Remove phone_number column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_profiles' AND column_name='phone_number'
    ) THEN
        ALTER TABLE user_profiles DROP COLUMN phone_number;
    END IF;
END $$;

-- Remove twilio_verified column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_profiles' AND column_name='twilio_verified'
    ) THEN
        ALTER TABLE user_profiles DROP COLUMN twilio_verified;
    END IF;
END $$;

-- Remove is_2fa_enabled column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_profiles' AND column_name='is_2fa_enabled'
    ) THEN
        ALTER TABLE user_profiles DROP COLUMN is_2fa_enabled;
    END IF;
END $$; 