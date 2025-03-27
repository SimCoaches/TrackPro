-- Supabase Schema for TrackPro
-- Run this in the SQL Editor in the Supabase Dashboard to set up the tables

-- User profiles table to store additional user information
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Enable Row Level Security
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Create policies for user_profiles table
-- Users can view their own profile
CREATE POLICY "Users can view their own profile" 
ON public.user_profiles FOR SELECT 
USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update their own profile" 
ON public.user_profiles FOR UPDATE 
USING (auth.uid() = id);

-- Create diagnostics table for testing
CREATE TABLE public.test_diagnostics (
    id SERIAL PRIMARY KEY,
    name TEXT,
    status TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Allow anonymous access to test_diagnostics for testing
ALTER TABLE public.test_diagnostics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous access to test_diagnostics" 
ON public.test_diagnostics 
FOR ALL USING (true);

-- Function to handle user creation
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, display_name)
  VALUES (new.id, new.email, COALESCE(new.raw_user_meta_data->>'display_name', new.email));
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create user profile when a new user signs up
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Verify authentication settings
DO $$
BEGIN
  -- Check if email auth is enabled
  IF NOT EXISTS (
    SELECT 1 FROM auth.providers WHERE provider = 'email'
  ) THEN
    RAISE NOTICE 'Email authentication is not enabled. Enable it in the Authentication settings.';
  END IF;
  
  -- Check if auto-confirm is enabled
  -- This is appropriate for development but might want email confirmation for production
  IF NOT EXISTS (
    SELECT 1 FROM auth.identities LIMIT 1
  ) THEN
    RAISE NOTICE 'No users exist. Sign up a test user to verify authentication is working.';
  END IF;
END $$; 