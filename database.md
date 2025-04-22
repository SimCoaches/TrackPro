# Race Coach: Lap vs Lap Telemetry Comparison Feature

This document tracks the development progress for the lap comparison feature in the Race Coach application.

## Goal

Allow users to select two laps (their own or others') and view a visual comparison of key telemetry channels (speed, delta time, inputs) side-by-side within the Telemetry tab.

## Implementation Roadmap

### PHASE ➊ – Data pipeline from Supabase

1.  [ ] **Telemetry schema sanity‑check**: Verify `laps` and `telemetry_points` tables have necessary columns (`id`, `lap_id`, `track_position`, `speed`, etc.) and indexes (`lap_id`, `track_position`).
2.  [ ] **Python DB helper layer (`Supabase/database.py`)**:
    *   [X] `get_laps(limit, user_only)`
    *   [X] `get_telemetry_points(lap_id, cols=None)`
    *   [ ] `get_lap_summary(lap_id)` (returning lap_time, driver, etc.)
3.  [ ] **Optional: Pre‑compute/streamlined view**: Consider `telemetry_points_compact` view or RPC/Edge Function for efficiency.

### PHASE ➋ – UI wiring in `RaceCoachWidget`

4.  [ ] **Lap selection controls**: Add `QComboBox`es for Lap A/B and "Compare" button in Telemetry tab. Populate via `refresh_lap_list()`.
5.  [ ] **Fetch & align telemetry on click**: Implement `on_compare_clicked()` using background thread (`QThread`). Align samples (resampling if needed). Build data arrays (`speed_left`, `speed_right`, `delta`).
6.  [ ] **Propagate to visualisation widgets**: Call `TelemetryComparisonWidget.set_speed_data()`, `set_delta_data()`. Update driver panels via `set_driver_data()` and `update_driver_display()`.

### PHASE ➌ – UX & performance polish

7.  [ ] **Non‑blocking fetch & error handling**: Use `QThread` + signals, show loading indicator, handle errors gracefully (e.g., `QMessageBox`).
8.  [ ] **Caching & memoisation**: Implement simple in-memory cache for fetched telemetry (`{lap_id: data}`).
9.  [ ] **Additional channels (future)**: Extend data fetching and visualization for throttle, brake, gear, etc.
10. [ ] **Track map overlay (future)**: Draw car traces using telemetry XY or track position + SVG map.

### PHASE ➍ – Testing & QA

11. [ ] **Unit tests**: Add `pytest` tests for Supabase helpers.
12. [ ] **UI smoke tests**: Basic script to load/compare laps.
13. [ ] **Profiling**: Check performance with large datasets.

### PHASE ➎ – Stretch goals

14. [ ] Serverless `compare_laps` RPC.
15. [ ] Shareable comparison links.
16. [ ] Export to PNG/CSV.

## Immediate Coding Tasks (Current Sprint)

*   [X] **A: Finalise lap selector UI** (combo boxes + refresh)
*   [X] **B: Move telemetry fetch into background thread**
*   [ ] **C: Align arrays, compute delta, push to widgets**
*   [ ] **D: QA with real Supabase data** 