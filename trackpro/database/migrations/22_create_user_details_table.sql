-- Migration: Create user_details table for user account information
-- This table stores user account details like first name, last name, date of birth, etc.

CREATE TABLE IF NOT EXISTS "user_details" (
    "user_id" UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    "first_name" TEXT,
    "last_name" TEXT,
    "date_of_birth" DATE,
    "phone_number" TEXT,
    "twilio_verified" BOOLEAN DEFAULT FALSE,
    "is_2fa_enabled" BOOLEAN DEFAULT FALSE,
    "terms_accepted" BOOLEAN DEFAULT FALSE,
    "terms_version_accepted" TEXT DEFAULT '',
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add RLS (Row Level Security) policies
ALTER TABLE "user_details" ENABLE ROW LEVEL SECURITY;

-- Users can only read, update their own details
CREATE POLICY "Users can view own details" 
    ON "user_details" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own details" 
    ON "user_details" FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own details" 
    ON "user_details" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_details_first_name ON "user_details"(first_name);
CREATE INDEX IF NOT EXISTS idx_user_details_last_name ON "user_details"(last_name);
CREATE INDEX IF NOT EXISTS idx_user_details_phone_number ON "user_details"(phone_number) WHERE phone_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_details_2fa_enabled ON "user_details"(is_2fa_enabled) WHERE is_2fa_enabled = TRUE;

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER trigger_update_user_details_timestamp
    BEFORE UPDATE ON "user_details"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to automatically create user_details on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user_details()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_details (user_id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for creating user details on signup
CREATE TRIGGER on_auth_user_created_details
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_details();

-- Add comments to document the fields
COMMENT ON TABLE "user_details" IS 'User account details and personal information';
COMMENT ON COLUMN "user_details"."first_name" IS 'User first name';
COMMENT ON COLUMN "user_details"."last_name" IS 'User last name';
COMMENT ON COLUMN "user_details"."date_of_birth" IS 'User date of birth';
COMMENT ON COLUMN "user_details"."phone_number" IS 'User phone number for SMS 2FA verification';
COMMENT ON COLUMN "user_details"."twilio_verified" IS 'Whether the phone number has been verified via Twilio SMS';
COMMENT ON COLUMN "user_details"."is_2fa_enabled" IS 'Whether two-factor authentication is enabled for the user';
COMMENT ON COLUMN "user_details"."terms_accepted" IS 'Whether user has accepted terms and conditions';
COMMENT ON COLUMN "user_details"."terms_version_accepted" IS 'Version of terms and conditions accepted by user'; 