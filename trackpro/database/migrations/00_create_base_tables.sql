-- Migration: Create base tables for TrackPro
-- This migration creates all the core tables needed for the application

-- Create tracks table
CREATE TABLE IF NOT EXISTS "tracks" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" TEXT NOT NULL,
    "config" TEXT,
    "base_track_id" UUID REFERENCES "tracks"(id),
    "iracing_track_id" INTEGER,
    "iracing_config_id" INTEGER,
    "location" TEXT,
    "country" TEXT,
    "length_meters" REAL,
    "corners" JSONB,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create cars table
CREATE TABLE IF NOT EXISTS "cars" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" TEXT NOT NULL,
    "class" TEXT,
    "iracing_car_id" INTEGER,
    "manufacturer" TEXT,
    "category" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS "sessions" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "track_id" UUID NOT NULL REFERENCES "tracks"(id) ON DELETE CASCADE,
    "car_id" UUID NOT NULL REFERENCES "cars"(id) ON DELETE CASCADE,
    "session_type" TEXT,
    "session_date" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "iracing_session_id" INTEGER,
    "iracing_subsession_id" INTEGER,
    "metadata" JSONB,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create laps table
CREATE TABLE IF NOT EXISTS "laps" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "session_id" UUID NOT NULL REFERENCES "sessions"(id) ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "lap_number" INTEGER NOT NULL,
    "lap_time" REAL NOT NULL,
    "is_valid" BOOLEAN DEFAULT true,
    "is_valid_for_leaderboard" BOOLEAN DEFAULT false,
    "lap_type" TEXT DEFAULT 'TIMED',
    "is_personal_best" BOOLEAN DEFAULT false,
    "metadata" JSONB,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Ensure each session can only have one lap per lap number
    UNIQUE (session_id, lap_number)
);

-- Create telemetry_points table
CREATE TABLE IF NOT EXISTS "telemetry_points" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "lap_id" UUID NOT NULL REFERENCES "laps"(id) ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "timestamp" REAL NOT NULL,
    "track_position" REAL NOT NULL,
    "speed" REAL,
    "rpm" REAL,
    "gear" INTEGER,
    "throttle" REAL,
    "brake" REAL,
    "clutch" REAL,
    "steering" REAL,
    "lat_accel" REAL,
    "long_accel" REAL,
    "batch_index" INTEGER,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Enable RLS on all tables
ALTER TABLE "tracks" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "cars" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "sessions" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "laps" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "telemetry_points" ENABLE ROW LEVEL SECURITY;

-- RLS Policies for tracks (public read, authenticated users can insert)
CREATE POLICY "Anyone can view tracks" 
    ON "tracks" FOR SELECT 
    USING (true);

CREATE POLICY "Authenticated users can insert tracks" 
    ON "tracks" FOR INSERT 
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can update tracks" 
    ON "tracks" FOR UPDATE 
    USING (auth.role() = 'authenticated');

-- RLS Policies for cars (public read, authenticated users can insert)
CREATE POLICY "Anyone can view cars" 
    ON "cars" FOR SELECT 
    USING (true);

CREATE POLICY "Authenticated users can insert cars" 
    ON "cars" FOR INSERT 
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can update cars" 
    ON "cars" FOR UPDATE 
    USING (auth.role() = 'authenticated');

-- RLS Policies for sessions (users can only see their own)
CREATE POLICY "Users can view own sessions" 
    ON "sessions" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions" 
    ON "sessions" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" 
    ON "sessions" FOR UPDATE 
    USING (auth.uid() = user_id);

-- RLS Policies for laps (users can only see their own)
CREATE POLICY "Users can view own laps" 
    ON "laps" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own laps" 
    ON "laps" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own laps" 
    ON "laps" FOR UPDATE 
    USING (auth.uid() = user_id);

-- RLS Policies for telemetry_points (users can only see their own)
CREATE POLICY "Users can view own telemetry" 
    ON "telemetry_points" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own telemetry" 
    ON "telemetry_points" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "idx_tracks_iracing_track_id" ON "tracks"(iracing_track_id);
CREATE INDEX IF NOT EXISTS "idx_tracks_base_track_id" ON "tracks"(base_track_id);
CREATE INDEX IF NOT EXISTS "idx_cars_iracing_car_id" ON "cars"(iracing_car_id);
CREATE INDEX IF NOT EXISTS "idx_sessions_user_id" ON "sessions"(user_id);
CREATE INDEX IF NOT EXISTS "idx_sessions_track_id" ON "sessions"(track_id);
CREATE INDEX IF NOT EXISTS "idx_sessions_car_id" ON "sessions"(car_id);
CREATE INDEX IF NOT EXISTS "idx_laps_session_id" ON "laps"(session_id);
CREATE INDEX IF NOT EXISTS "idx_laps_user_id" ON "laps"(user_id);
CREATE INDEX IF NOT EXISTS "idx_laps_lap_number" ON "laps"(lap_number);
CREATE INDEX IF NOT EXISTS "idx_telemetry_points_lap_id" ON "telemetry_points"(lap_id);
CREATE INDEX IF NOT EXISTS "idx_telemetry_points_track_position" ON "telemetry_points"(track_position);
CREATE INDEX IF NOT EXISTS "idx_telemetry_points_timestamp" ON "telemetry_points"(timestamp);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_tracks_updated_at 
    BEFORE UPDATE ON tracks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cars_updated_at 
    BEFORE UPDATE ON cars 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at 
    BEFORE UPDATE ON sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_laps_updated_at 
    BEFORE UPDATE ON laps 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 