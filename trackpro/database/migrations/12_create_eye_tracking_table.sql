-- Migration: Create eye tracking tables
-- This migration adds tables to store eye tracking data alongside telemetry

-- Create eye_tracking_points table to store gaze data
CREATE TABLE IF NOT EXISTS "eye_tracking_points" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "lap_id" UUID NOT NULL REFERENCES "laps"(id) ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "timestamp" REAL NOT NULL,
    "track_position" REAL NOT NULL,
    "gaze_x" REAL NOT NULL,           -- Normalized gaze X coordinate (0.0 to 1.0)
    "gaze_y" REAL NOT NULL,           -- Normalized gaze Y coordinate (0.0 to 1.0)
    "screen_width" INTEGER NOT NULL,   -- Screen resolution width at time of recording
    "screen_height" INTEGER NOT NULL,  -- Screen resolution height at time of recording
    "confidence" REAL,                 -- Eye tracking confidence score (0.0 to 1.0)
    "blink_detected" BOOLEAN DEFAULT false,  -- Whether the driver was blinking
    "eye_features" JSONB,              -- Raw eye tracking features for debugging
    "batch_index" INTEGER,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create eye_tracking_sessions table to store calibration and session metadata
CREATE TABLE IF NOT EXISTS "eye_tracking_sessions" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "session_id" UUID NOT NULL REFERENCES "sessions"(id) ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    "calibration_data" JSONB,          -- Stored calibration model data
    "calibration_timestamp" TIMESTAMP WITH TIME ZONE,
    "camera_settings" JSONB,           -- Camera resolution, FPS, etc.
    "monitor_settings" JSONB,          -- Monitor resolution, position, etc.
    "is_active" BOOLEAN DEFAULT true,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Enable RLS on new tables
ALTER TABLE "eye_tracking_points" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "eye_tracking_sessions" ENABLE ROW LEVEL SECURITY;

-- RLS Policies for eye_tracking_points (users can only see their own)
CREATE POLICY "Users can view own eye tracking points" 
    ON "eye_tracking_points" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own eye tracking points" 
    ON "eye_tracking_points" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- RLS Policies for eye_tracking_sessions (users can only see their own)
CREATE POLICY "Users can view own eye tracking sessions" 
    ON "eye_tracking_sessions" FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own eye tracking sessions" 
    ON "eye_tracking_sessions" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own eye tracking sessions" 
    ON "eye_tracking_sessions" FOR UPDATE 
    USING (auth.uid() = user_id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "idx_eye_tracking_points_lap_id" ON "eye_tracking_points"(lap_id);
CREATE INDEX IF NOT EXISTS "idx_eye_tracking_points_track_position" ON "eye_tracking_points"(track_position);
CREATE INDEX IF NOT EXISTS "idx_eye_tracking_points_timestamp" ON "eye_tracking_points"(timestamp);
CREATE INDEX IF NOT EXISTS "idx_eye_tracking_sessions_session_id" ON "eye_tracking_sessions"(session_id);

-- Create trigger to automatically update updated_at for eye_tracking_sessions
CREATE TRIGGER update_eye_tracking_sessions_updated_at 
    BEFORE UPDATE ON eye_tracking_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); 