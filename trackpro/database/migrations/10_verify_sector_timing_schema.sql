-- Migration: Verify and fix sector timing schema
-- This migration ensures all required tables and columns exist for the sector timing functionality

-- Verify base tables exist and create if missing
DO $$
BEGIN
    -- Check if tracks table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tracks') THEN
        RAISE EXCEPTION 'Base table "tracks" does not exist. Please run 00_create_base_tables.sql first.';
    END IF;
    
    -- Check if cars table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cars') THEN
        RAISE EXCEPTION 'Base table "cars" does not exist. Please run 00_create_base_tables.sql first.';
    END IF;
    
    -- Check if sessions table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions') THEN
        RAISE EXCEPTION 'Base table "sessions" does not exist. Please run 00_create_base_tables.sql first.';
    END IF;
    
    -- Check if laps table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'laps') THEN
        RAISE EXCEPTION 'Base table "laps" does not exist. Please run 00_create_base_tables.sql first.';
    END IF;
    
    -- Check if telemetry_points table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'telemetry_points') THEN
        RAISE EXCEPTION 'Base table "telemetry_points" does not exist. Please run 00_create_base_tables.sql first.';
    END IF;
    
    -- Check if sector_times table exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sector_times') THEN
        RAISE EXCEPTION 'Table "sector_times" does not exist. Please run 08_create_sector_times_table.sql first.';
    END IF;
    
    RAISE NOTICE 'All required base tables exist.';
END
$$;

-- Verify required columns exist in laps table
DO $$
BEGIN
    -- Check lap_type column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'laps' AND column_name = 'lap_type'
    ) THEN
        RAISE EXCEPTION 'Column "lap_type" missing from "laps" table. Please run 07_add_lap_type_column.sql first.';
    END IF;
    
    -- Check is_valid_for_leaderboard column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'laps' AND column_name = 'is_valid_for_leaderboard'
    ) THEN
        RAISE EXCEPTION 'Column "is_valid_for_leaderboard" missing from "laps" table. Please run 07_add_lap_type_column.sql first.';
    END IF;
    
    RAISE NOTICE 'All required columns exist in "laps" table.';
END
$$;

-- Verify required columns exist in telemetry_points table
DO $$
BEGIN
    -- Check current_sector column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'telemetry_points' AND column_name = 'current_sector'
    ) THEN
        RAISE EXCEPTION 'Column "current_sector" missing from "telemetry_points" table. Please run 09_add_sector_columns_to_telemetry.sql first.';
    END IF;
    
    -- Check current_sector_time column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'telemetry_points' AND column_name = 'current_sector_time'
    ) THEN
        RAISE EXCEPTION 'Column "current_sector_time" missing from "telemetry_points" table. Please run 09_add_sector_columns_to_telemetry.sql first.';
    END IF;
    
    RAISE NOTICE 'All required columns exist in "telemetry_points" table.';
END
$$;

-- Verify required columns exist in sector_times table
DO $$
BEGIN
    -- Check all required columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sector_times' AND column_name = 'lap_id'
    ) THEN
        RAISE EXCEPTION 'Column "lap_id" missing from "sector_times" table.';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sector_times' AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION 'Column "user_id" missing from "sector_times" table.';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sector_times' AND column_name = 'sector_number'
    ) THEN
        RAISE EXCEPTION 'Column "sector_number" missing from "sector_times" table.';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sector_times' AND column_name = 'sector_time'
    ) THEN
        RAISE EXCEPTION 'Column "sector_time" missing from "sector_times" table.';
    END IF;
    
    RAISE NOTICE 'All required columns exist in "sector_times" table.';
END
$$;

-- Verify required indexes exist
DO $$
BEGIN
    -- Check sector timing indexes
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'sector_times' AND indexname = 'idx_sector_times_lap_id'
    ) THEN
        RAISE NOTICE 'Creating missing index "idx_sector_times_lap_id"';
        CREATE INDEX "idx_sector_times_lap_id" ON "sector_times"("lap_id");
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'telemetry_points' AND indexname = 'idx_telemetry_points_current_sector'
    ) THEN
        RAISE NOTICE 'Creating missing index "idx_telemetry_points_current_sector"';
        CREATE INDEX "idx_telemetry_points_current_sector" ON "telemetry_points"("current_sector");
    END IF;
    
    RAISE NOTICE 'All required indexes verified.';
END
$$;

-- Verify required functions exist
DO $$
BEGIN
    -- Check if get_best_sector_times function exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_name = 'get_best_sector_times'
    ) THEN
        RAISE EXCEPTION 'Function "get_best_sector_times" does not exist. Please run 08_create_sector_times_table.sql first.';
    END IF;
    
    -- Check if get_sector_comparison function exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_name = 'get_sector_comparison'
    ) THEN
        RAISE EXCEPTION 'Function "get_sector_comparison" does not exist. Please run 08_create_sector_times_table.sql first.';
    END IF;
    
    -- Check if get_lap_sector_telemetry function exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_name = 'get_lap_sector_telemetry'
    ) THEN
        RAISE EXCEPTION 'Function "get_lap_sector_telemetry" does not exist. Please run 09_add_sector_columns_to_telemetry.sql first.';
    END IF;
    
    RAISE NOTICE 'All required functions exist.';
END
$$;

-- Final verification message
DO $$
BEGIN
    RAISE NOTICE '✅ Sector timing schema verification complete! All required tables, columns, indexes, and functions are in place.';
    RAISE NOTICE '📊 The following functionality is now available:';
    RAISE NOTICE '   • Live sector timing collection during races';
    RAISE NOTICE '   • Sector time storage in the sector_times table';
    RAISE NOTICE '   • Sector data attached to telemetry points';
    RAISE NOTICE '   • Best sector time queries and comparisons';
    RAISE NOTICE '   • Sector-specific telemetry analysis';
END
$$; 