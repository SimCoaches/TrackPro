-- Add phone number and 2FA verification columns to user_details table
-- This migration adds the 2FA columns to the correct table (user_details)

-- Add phone_number column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_details' AND column_name='phone_number'
    ) THEN
        ALTER TABLE user_details ADD COLUMN phone_number TEXT;
        COMMENT ON COLUMN user_details.phone_number IS 'User phone number for SMS 2FA verification';
    END IF;
END $$;

-- Add twilio_verified column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_details' AND column_name='twilio_verified'
    ) THEN
        ALTER TABLE user_details ADD COLUMN twilio_verified BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN user_details.twilio_verified IS 'Whether the phone number has been verified via Twilio SMS';
    END IF;
END $$;

-- Add is_2fa_enabled column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_details' AND column_name='is_2fa_enabled'
    ) THEN
        ALTER TABLE user_details ADD COLUMN is_2fa_enabled BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN user_details.is_2fa_enabled IS 'Whether two-factor authentication is enabled for the user';
    END IF;
END $$;

-- Create index on phone_number for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_details_phone_number ON user_details(phone_number) WHERE phone_number IS NOT NULL;

-- Create index on 2FA enabled status for faster filtering
CREATE INDEX IF NOT EXISTS idx_user_details_2fa_enabled ON user_details(is_2fa_enabled) WHERE is_2fa_enabled = TRUE; 