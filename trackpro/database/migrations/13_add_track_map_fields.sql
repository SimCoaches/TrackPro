-- Migration: Add track map and analysis fields to existing tracks table
-- This enhances the tracks table to store track maps and corner analysis data

-- Add track map data field
ALTER TABLE "tracks" ADD COLUMN IF NOT EXISTS "track_map" JSONB;

-- Add track analysis metadata
ALTER TABLE "tracks" ADD COLUMN IF NOT EXISTS "analysis_metadata" JSONB;

-- Add last analysis date
ALTER TABLE "tracks" ADD COLUMN IF NOT EXISTS "last_analysis_date" TIMESTAMP WITH TIME ZONE;

-- Add version field for track data versioning
ALTER TABLE "tracks" ADD COLUMN IF NOT EXISTS "data_version" INTEGER DEFAULT 1;

-- Create index for faster corner queries
CREATE INDEX IF NOT EXISTS "idx_tracks_corners" ON "tracks" USING GIN ("corners");

-- Create index for faster track map queries  
CREATE INDEX IF NOT EXISTS "idx_tracks_track_map" ON "tracks" USING GIN ("track_map");

-- Create index for analysis date queries
CREATE INDEX IF NOT EXISTS "idx_tracks_last_analysis_date" ON "tracks"("last_analysis_date");

-- Comments for documentation
COMMENT ON COLUMN "tracks"."track_map" IS 'JSONB array of track coordinate points for visualization';
COMMENT ON COLUMN "tracks"."corners" IS 'JSONB array of detected corners with position, speed, and steering data';
COMMENT ON COLUMN "tracks"."analysis_metadata" IS 'JSONB metadata about track analysis (detection settings, data quality, etc.)';
COMMENT ON COLUMN "tracks"."last_analysis_date" IS 'Timestamp of last corner detection/track analysis';
COMMENT ON COLUMN "tracks"."data_version" IS 'Version number for track data schema compatibility'; 