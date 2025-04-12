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

-- iRacing Database Schema
-- Tracks table to store information about racing tracks
CREATE TABLE public.tracks (
    id SERIAL PRIMARY KEY,
    iracing_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    config TEXT,
    location TEXT,
    length_km NUMERIC(10, 3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Cars table to store information about racing cars
CREATE TABLE public.cars (
    id SERIAL PRIMARY KEY,
    iracing_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    class TEXT,
    year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Sessions table to store information about racing sessions
CREATE TABLE public.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    track_id INTEGER REFERENCES public.tracks(id),
    car_id INTEGER REFERENCES public.cars(id),
    session_type TEXT, -- Qualifying, Race, Practice, etc.
    weather_conditions JSONB,
    session_date TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Laps table to store lap time information
CREATE TABLE public.laps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    lap_number INTEGER NOT NULL,
    lap_time NUMERIC(10, 3) NOT NULL, -- in seconds
    sector1_time NUMERIC(10, 3),
    sector2_time NUMERIC(10, 3),
    sector3_time NUMERIC(10, 3),
    is_valid BOOLEAN DEFAULT true,
    is_personal_best BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb -- Additional metadata like fuel, tires, etc.
);

-- Telemetry data points table (for detailed lap analysis)
CREATE TABLE public.telemetry_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lap_id UUID REFERENCES public.laps(id) ON DELETE CASCADE,
    track_position NUMERIC(5, 4) NOT NULL, -- 0.0000 to 1.0000 around the track
    speed NUMERIC(10, 2), -- km/h
    rpm NUMERIC(10, 2),
    gear INTEGER,
    throttle NUMERIC(5, 4), -- 0.0000 to 1.0000
    brake NUMERIC(5, 4), -- 0.0000 to 1.0000
    clutch NUMERIC(5, 4), -- 0.0000 to 1.0000
    steering NUMERIC(10, 6), -- Steering angle in radians
    timestamp NUMERIC(15, 3), -- Timestamp relative to lap start in seconds
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

-- Index for faster queries
CREATE INDEX idx_laps_session_id ON public.laps(session_id);
CREATE INDEX idx_laps_user_id ON public.laps(user_id);
CREATE INDEX idx_telemetry_lap_id ON public.telemetry_points(lap_id);
CREATE INDEX idx_telemetry_track_position ON public.telemetry_points(track_position);

-- Enable Row Level Security on the new tables
ALTER TABLE public.tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cars ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.laps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telemetry_points ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Tracks and Cars are read-only for all authenticated users
CREATE POLICY "Allow read access to tracks" ON public.tracks FOR SELECT USING (true);
CREATE POLICY "Allow read access to cars" ON public.cars FOR SELECT USING (true);

-- Allow authenticated users to read any session
CREATE POLICY "Allow read access to all sessions" ON public.sessions FOR SELECT USING (auth.role() = 'authenticated');

-- Allow users to insert, update and delete their own sessions
CREATE POLICY "Allow insert of own sessions" ON public.sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Allow update of own sessions" ON public.sessions FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Allow delete of own sessions" ON public.sessions FOR DELETE USING (auth.uid() = user_id);

-- Allow authenticated users to read any lap
CREATE POLICY "Allow read access to all laps" ON public.laps FOR SELECT USING (auth.role() = 'authenticated');

-- Allow users to insert, update and delete their own laps
CREATE POLICY "Allow insert of own laps" ON public.laps FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Allow update of own laps" ON public.laps FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Allow delete of own laps" ON public.laps FOR DELETE USING (auth.uid() = user_id);

-- Telemetry points are accessible based on the lap's ownership
CREATE POLICY "Allow read access to telemetry of accessible laps" 
ON public.telemetry_points FOR SELECT 
USING (EXISTS (
    SELECT 1 FROM public.laps 
    WHERE public.laps.id = public.telemetry_points.lap_id 
    AND auth.role() = 'authenticated'
));

CREATE POLICY "Allow insert of telemetry for own laps" 
ON public.telemetry_points FOR INSERT 
WITH CHECK (EXISTS (
    SELECT 1 FROM public.laps 
    WHERE public.laps.id = public.telemetry_points.lap_id 
    AND auth.uid() = public.laps.user_id
));

CREATE POLICY "Allow delete of telemetry for own laps" 
ON public.telemetry_points FOR DELETE 
USING (EXISTS (
    SELECT 1 FROM public.laps 
    WHERE public.laps.id = public.telemetry_points.lap_id 
    AND auth.uid() = public.laps.user_id
)); 