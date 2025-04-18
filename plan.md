# iRacing Telemetry Data Storage Plan

## Overview

This plan outlines the strategy for storing and managing high-frequency iRacing telemetry data for potentially hundreds of users within a Supabase project, leveraging the TimescaleDB extension for efficient time-series data handling.

## 1. Database Setup

*   **Platform:** Supabase Project
*   **Extension:** Enable the `timescaledb` extension via the Supabase Dashboard (Database -> Extensions).
*   **Tables:**
    *   **`sessions` Table:** Stores metadata for each racing session.
        *   `session_id` (SERIAL PRIMARY KEY or UUID)
        *   `user_id` (UUID, FK to `auth.users`)
        *   `start_time` (TIMESTAMPTZ NOT NULL DEFAULT now())
        *   `car_id` (TEXT) - Optional: Track car used
        *   `track_id` (TEXT) - Optional: Track location
        *   *Other relevant session metadata*
    *   **`telemetry` Hypertable:** Stores raw, high-frequency telemetry data points.
        *   `timestamp` (TIMESTAMPTZ NOT NULL) - Primary time column for hypertable.
        *   `session_id` (INTEGER or UUID, FK to `sessions`, NOT NULL) - Partitioning key.
        *   `lap_number` (INTEGER) - Derived from iRacing data.
        *   `speed` (FLOAT)
        *   `throttle` (FLOAT)
        *   `brake` (FLOAT)
        *   *Other core telemetry variables as FLOAT/NUMERIC columns.*
        *   *Optional:* `extra_data` (JSONB) - For less common or dynamic variables.
    *   **`lap_statistics` Table:** Stores pre-calculated statistics for each lap.
        *   `session_id` (INTEGER or UUID, FK to `sessions`)
        *   `lap_number` (INTEGER)
        *   `lap_time_ms` (BIGINT) - Lap time in milliseconds.
        *   `avg_speed` (FLOAT)
        *   `max_speed` (FLOAT)
        *   `min_throttle` (FLOAT)
        *   `max_brake` (FLOAT)
        *   *Other relevant lap aggregate statistics.*
        *   PRIMARY KEY (`session_id`, `lap_number`)
*   **Hypertable Creation:**
  ```sql
    -- Convert the telemetry table into a hypertable partitioned by time and session
    SELECT create_hypertable('telemetry', 'timestamp', 'session_id', chunk_time_interval => interval '1 day');
    -- Adjust chunk_time_interval based on expected data volume per session/day
    ```
*   **Indexing:**
    *   TimescaleDB automatically creates indexes on `timestamp` and `session_id` for the hypertable.
    *   Consider composite index on `telemetry` table: `CREATE INDEX ON telemetry (session_id, lap_number, timestamp);`
    *   Index on `sessions(user_id)`.
    *   Indexes on specific telemetry columns if frequently used in WHERE clauses.

## 2. Data Ingestion Strategy

*   **Client-Side:**
    *   Batch telemetry data points locally (e.g., collect data for 1 second / 60 samples).
    *   Send the batch as a single JSON payload to a serverless function endpoint.
    ```json
    // Example Payload
    {
      "session_id": 123,
      "data": [
        {"timestamp": "2023-10-27T10:00:01.000Z", "lap": 1, "speed": 50.1, ...},
        {"timestamp": "2023-10-27T10:00:01.016Z", "lap": 1, "speed": 50.2, ...},
        // ... 58 more points
      ]
    }
    ```
*   **Server-Side (Supabase Function):**
    *   Create a Supabase Edge Function (e.g., `/ingest-telemetry`) to receive POST requests.
    *   Validate the incoming payload (`session_id`, data format).
    *   Perform a bulk `INSERT` operation into the `telemetry` hypertable using the received batch. Use `unnest` or equivalent technique for efficient bulk insertion from JSON.

## 3. Data Processing & Aggregation

*   **Lap Statistics Population:** Populate the `lap_statistics` table. Choose one method:
    *   **TimescaleDB Continuous Aggregates (Recommended):** Define aggregates to automatically calculate lap stats as data arrives.
  ```sql
        -- Example Continuous Aggregate (adjust metrics and grouping)
        CREATE MATERIALIZED VIEW lap_stats_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            session_id,
            lap_number,
            time_bucket('1 hour', timestamp) as bucket, -- Aggregate hourly or by session end
            MIN(timestamp) as lap_start_time,
            MAX(timestamp) as lap_end_time,
            EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) * 1000 as lap_time_ms,
            AVG(speed) as avg_speed,
            MAX(speed) as max_speed
            -- Add other aggregates
        FROM telemetry
        GROUP BY session_id, lap_number, bucket;

        -- Add policy to refresh continuously
        SELECT add_continuous_aggregate_policy('lap_stats_hourly', ...);

        -- Query this view or potentially insert into lap_statistics table from the view periodically.
        ```
    *   **Post-Session Function:** Trigger a function upon session completion (requires a reliable trigger mechanism). Query raw `telemetry` data for the session, compute stats per lap, and insert into `lap_statistics`.

## 4. Storage Management

*   **Compression:** Enable and configure TimescaleDB's native compression on the `telemetry` hypertable after some data has been ingested.
    ```sql
    -- Enable compression
    ALTER TABLE telemetry SET (timescaledb.compress, timescaledb.compress_segmentby = 'session_id');
    -- Optionally add: timescaledb.compress_orderby = 'timestamp'
    -- Add a policy to compress old chunks
    SELECT add_compression_policy('telemetry', compress_after => interval '7 days');
    ```
*   **Data Retention:** Implement policies to automatically drop old data chunks from the `telemetry` hypertable to manage storage costs. Retain `lap_statistics` or continuous aggregates for longer periods.
  ```sql
    -- Drop raw telemetry chunks older than 90 days
    SELECT add_retention_policy('telemetry', drop_after => interval '90 days');
    ```

## 5. Querying and Analysis

*   **Direct Queries:** Use standard SQL to query `telemetry` and `lap_statistics`, filtering by `session_id`, `lap_number`, `timestamp` ranges. Hypertable partitioning ensures efficiency.
*   **TimescaleDB Functions:** Utilize functions like `time_bucket()`, `first()`, `last()`, `locf()` for time-based analysis and aggregations.
*   **Database Functions:** Create custom `plpgsql` functions within Supabase for complex calculations (e.g., comparing laps, finding theoretical best lap) and expose them via RPC.

## 6. Scalability & Considerations

*   **Concurrency:** Monitor Supabase function invocation limits, database connection pool size, and insertion performance under load.
*   **Resource Scaling:** Be prepared to scale Supabase compute resources if performance degrades with user growth.
*   **Lap Detection:** Ensure the logic for determining `lap_number` (client-side or server-side) is robust against edge cases (pit stops, off-tracks).
*   **Session Lifecycle:** Clearly define how sessions are started and ended to trigger relevant processes (like post-session aggregation if used).
*   **Variable Schema:** Decide between fixed columns for telemetry variables vs. JSONB based on the expected stability and query patterns. Fixed columns are generally faster for querying but less flexible.

## 7. User Access & Visualization

### 7.1 API Design

*   **Core API Endpoints:** Implement the following Supabase endpoints for client access:
    *   **Sessions List:** `GET /api/sessions` - Returns list of a user's sessions with basic metadata.
        *   **Parameters:** Optional filters (date range, track, car, etc.)
        *   **Response:** Array of session objects with ID, date, track, car, duration, best lap time
    *   **Session Details:** `GET /api/sessions/{session_id}` - Returns detailed metadata for a session.
        *   **Response:** Session object with all metadata, including lap summary statistics
    *   **Lap List:** `GET /api/sessions/{session_id}/laps` - Returns all laps for a session.
        *   **Response:** Array of lap objects with number, time, and aggregate stats
    *   **Lap Telemetry:** `GET /api/sessions/{session_id}/laps/{lap_number}/telemetry` - Returns telemetry data for a specific lap.
        *   **Parameters:** 
            *   `channels` (array of channel names to include)
            *   `resolution` (points per second or total points to return)
        *   **Response:** Array of telemetry data points, potentially downsampled
    *   **Lap Comparison:** `GET /api/sessions/{session_id}/compare` - Compare multiple laps.
        *   **Parameters:** `lap_numbers` (array of lap numbers to compare)
        *   **Response:** Aligned telemetry data from multiple laps for comparison

*   **Implementation Approaches:**
    *   **PostgREST Direct Access:** Configure Supabase's auto-generated REST API with appropriate views and RLS policies.
    *   **Edge Functions:** Create custom Supabase Edge Functions for endpoints requiring complex logic.
    *   **RPC Functions:** Implement PostgreSQL functions for complex queries (like lap comparisons) and expose via Supabase RPC.

*   **Performance Optimizations:**
    *   **Data Downsampling:** For visualizing telemetry over time:
  ```sql
        -- Example downsampling function using time_bucket
        CREATE OR REPLACE FUNCTION get_downsampled_lap_telemetry(
            p_session_id INT, 
            p_lap_number INT,
            p_resolution INT DEFAULT 60 -- points per second (or lap)
        ) RETURNS TABLE (
            timestamp TIMESTAMPTZ,
            speed FLOAT,
            throttle FLOAT,
            brake FLOAT
            -- other channels
        ) AS $$
        DECLARE
            lap_duration INTERVAL;
            bucket_size INTERVAL;
        BEGIN
            -- Get lap duration
            SELECT (MAX(timestamp) - MIN(timestamp)) INTO lap_duration
            FROM telemetry
            WHERE session_id = p_session_id AND lap_number = p_lap_number;
            
            -- Calculate bucket size based on desired resolution
            bucket_size := lap_duration / p_resolution;
            
            -- Return downsampled data
            RETURN QUERY
            SELECT 
                time_bucket(bucket_size, timestamp) as timestamp,
                AVG(speed) as speed,
                AVG(throttle) as throttle,
                AVG(brake) as brake
                -- other channels
            FROM telemetry
            WHERE session_id = p_session_id AND lap_number = p_lap_number
            GROUP BY 1
            ORDER BY 1;
        END;
        $$ LANGUAGE plpgsql;
        ```
    *   **Progressive Loading:** Implement pagination or dynamic resolution adjustment as users zoom in/out.
    *   **Channel Selection:** Allow users to request only the specific telemetry channels they need.

### 7.2 Security & Access Control

*   **Row Level Security Policies:** Implement RLS policies on all tables to ensure users can only access their own data:
    ```sql
    -- Example RLS policy for sessions table
    CREATE POLICY "Users can only view their own sessions"
    ON sessions
    FOR SELECT
    USING (user_id = auth.uid());
    
    -- Example RLS policy for telemetry data
    CREATE POLICY "Users can only view telemetry for their own sessions"
    ON telemetry
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.session_id = telemetry.session_id
            AND sessions.user_id = auth.uid()
        )
    );
    ```

*   **Data Sharing (Optional):**
    *   Implement a system for users to optionally share specific sessions/laps with others.
    *   Create a `shared_sessions` table to track sharing permissions.
    *   Modify RLS policies to check both ownership and sharing permissions.

### 7.3 Frontend Visualization

*   **Dashboard Components:**
    *   **Sessions Overview:** List/grid of recent sessions with key metrics.
    *   **Session Detail View:** Session information with lap table and charts for session-level metrics.
    *   **Lap Analysis View:** Detailed view for analyzing a single lap with multiple visualizations.
    *   **Comparison View:** Side-by-side or overlay comparison of multiple laps.

*   **Chart Types:**
    *   **Time Series Charts:** Plot speed, throttle, brake, etc. over time or distance.
        *   Allow zoom/pan for detailed exploration.
        *   Support for highlighting specific sections (corners, straights).
    *   **Track Map (if position data available):** Visualize the track with color-coded overlays showing speed, throttle, etc.
    *   **Histogram/Distribution Charts:** Show distribution of braking points, speed at specific track segments, etc.
    *   **Correlation Plots:** Show relationships between different variables (e.g., throttle vs. speed).

*   **Implementation Technologies:**
    *   **Chart Libraries:** Plotly.js, Chart.js, D3.js, or similar for flexible, interactive visualizations.
    *   **State Management:** Use client-side state management (Redux, Zustand, etc.) to efficiently cache data and avoid redundant API calls.
    *   **Progressive Web App:** Consider PWA capabilities for offline access to previously viewed sessions.

### 7.4 Insights & Analysis Features

*   **Automated Insights:**
    *   Implement algorithms to detect potential areas for improvement in driving:
        ```sql
        -- Example function to find inconsistent braking points
        CREATE OR REPLACE FUNCTION detect_inconsistent_braking(
            p_session_id INT,
            p_threshold FLOAT DEFAULT 0.2 -- 20% variation threshold
        ) RETURNS TABLE (
            corner_number INT,
            variation_coefficient FLOAT,
            suggestion TEXT
        ) AS $$
        -- Implementation details
        $$ LANGUAGE plpgsql;
        ```
    
*   **Lap Sector Analysis:**
    *   Divide tracks into sectors or corners.
    *   Compare sector times and identify strongest/weakest sectors.
    *   Store track segment definitions in a separate table for reuse.

*   **Reference Lap Construction:**
    *   Create a "theoretical best lap" by combining best sectors from different laps.
    *   Allow comparison against this optimal reference.

*   **Progress Tracking:**
    *   Track improvement over time for the same car/track combination.
    *   Show learning curves and consistency metrics.

### 7.5 Export & Integration

*   **Data Export Options:**
    *   CSV/JSON export of raw telemetry data.
    *   PDF reports with visualization snapshots and key findings.
    *   Direct links to specific lap visualizations for sharing.

*   **Third-party Integrations:**
    *   Consider API integrations with racing community platforms.
    *   Export options compatible with other analysis tools.

### 7.6 Implementation Phases

*   **Phase 1 - Core Access:**
    *   Basic session list and lap summary statistics.
    *   Simple time-series visualization of telemetry for single laps.
    *   User authentication and basic security.

*   **Phase 2 - Enhanced Visualization:**
    *   Lap comparison features.
    *   Track map visualization (if position data available).
    *   More sophisticated downsampling and data optimization.

*   **Phase 3 - Advanced Analytics:**
    *   Automated insights and improvement suggestions.
    *   Sector analysis and reference lap construction.
    *   Progress tracking over time.
    *   Export and sharing capabilities. 