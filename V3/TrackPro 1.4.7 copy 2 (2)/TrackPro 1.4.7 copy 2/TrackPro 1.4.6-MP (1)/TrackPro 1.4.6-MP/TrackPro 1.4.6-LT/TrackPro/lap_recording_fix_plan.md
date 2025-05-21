# TrackPro Lap Recording Fix Plan

## 1. Root Cause & Guiding Principles

- [x] Understand the root cause:
  - iRacing writes "lap N" only when the *next* lap starts.
  - If you tow/reset to pits within a second or two of crossing the SF-line, the next-lap start never appears – so lap N never matures and TrackPro thinks the final telemetry frames belong to the *out-lap* that follows.

- [x] Implement a reliable fix with two guarantees:
  1. We *finalise* the just-completed lap as soon as iRacing confirms a valid `LapLastLapTime`, even if the car teleports immediately after.
  2. We cleanly distinguish ► out-laps ► in-laps ► timed laps, so that sequence‐numbers in Supabase stay: "Out-lap, Lap 1, Lap 2, …, IN-lap, Out-lap, Lap k, …".

Note: We already have most of the plumbing (LapIndexer, LapSaver, SessionMonitor). We only need to adjust their hand-off timing + validity rules.

## 2. Signals & Variables We Will Rely On

- [x] Identify and utilize these key signals:
  - `LapLastLapTime` > 0 → iRacing has officially closed a lap.
  - `Lap` (int) → iRacing's *current* lap number.
  - `LapDistPct` (0…1) → Position around the track.
  - `OnPitRoad` (bool) → Car is on pit road.
  - `SessionState` 0..5 → 5 == cool-down, etc.
  - Our LapIndexer's internal `started_on_pit_road`, `ended_on_pit_road`.

## 3. Algorithm Changes

- [x] Step 3.1: Finalise a lap *immediately* when either of these happens (whichever comes first):
  - a) `LapLastLapTime` becomes > 0 for the player car, OR
  - b) `LapDistPct` crosses 0 → 1 and back to < 0.02 **AND** the car *was not* on pit road at either the start or end of that span (this keeps normal lap completion behaviour). (Covered by LapIndexer logic and early finalization by LapLastLapTime)

- [x] Step 3.2: If, after rule 3.1.a, we see `OnPitRoad == True` *within 1 second* and before another valid sample arrives, mark that lap as an **IN-lap**.
  - Save it if desired for analytics, but flag `is_valid_for_leaderboard = False`. (Handled by checking OnPitRoad in the frame where LapLastLapTime appears)

- [x] Step 3.3: The next time `OnPitRoad` transitions **False → False AND** `LapDistPct` starts increasing from 0, mark that as an **OUT-lap** (`started_on_pit_road = True`).
  - Store it, but again `is_valid_for_leaderboard = False`. (Handled by LapIndexer state determination)

- [x] Step 3.4: From the first sample where the car is off pit road and `LapDistPct > 0.05`, start collecting the next **timed lap**. (Handled by LapIndexer state determination)

- [x] Step 3.5: Session end / reset catch-up
  - In `IRacingLapSaver.end_session()` extend LapIndexer to *always* flush the "current" lap if `LapLastLapTime` is non-zero but the lap has not been handed off yet (covers sudden quits or disconnects). (Handled by LapIndexer.finalize() and early finalization logic)

## 4. Concrete Code-Base Touch-Points

- [x] 4.1 `trackpro/race_coach/lap_indexer.py`
  - Add the immediate-finalise rule (3.1) inside the method that checks per-frame state.
  - Maintain a `lap_state` enum: OUT, TIMED, IN, INCOMPLETE.
  - When a lap closes, package that enum + flags in the lap-dict that `get_lap_data_to_save()` returns.

- [x] 4.2 `IRacingLapSaver._validate_lap_data()`
  - Accept IN/OUT laps, but automatically set `is_valid_for_leaderboard = False` (This is handled in _save_lap_data based on lap_state from LapIndexer).
  - Lower the minimum-frames threshold for laps finalised by rule 3.1.a (because an instant tow may yield only a handful of frames). (Addressed by leniency for SDK-timed laps and specific state-based frame count checks).

- [x] 4.3 `IRacingLapSaver._save_lap_data()`
  - Pass the new `lap_state` and `is_valid_for_leaderboard` down into the `lap_payload` so the DB has proper flags.

- [x] 4.4 `SaveLapWorker._save_telemetry_points_to_db()`
  - No functional change; just ensures flags are written. (Actually, `SaveLapWorker.run()` was modified to include `lap_type` in DB insert).

- [x] 4.5 `SimpleIRacingAPI.process_telemetry()`
  - Already pulls all the variables we need; no change.

- [x] 4.6 Unit / integration tests
  - [x] Create a synthetic telemetry trace that simulates: out-lap → 5 timed laps → instant tow → out-lap → 5 laps → tow.
  - [x] Feed it through LapIndexer and assert the resulting lap list equals: OUT(0) TIMED(1)…TIMED(5) IN OUT(6) TIMED(7)…TIMED(11) IN

## 5. Database / Supabase Considerations

- [x] Review current schema:
  - Schema already has `is_valid_for_leaderboard`, `is_complete`, `track_coverage`.
  - Add storage for `lap_type` (OUT / IN / TIMED) – add a TEXT column or use a small int enum.

- [x] Ensure existing queries that build leaderboards filter `is_valid_for_leaderboard == True`.

- [x] Fix Supabase session creation column mismatch:
  - Fixed error where IRacingLapSaver was using column name 'started_at' but the actual schema uses 'session_date'.
  - Updated _create_session_in_db to match the schema used by iracing_session_monitor.py.

## 6. Roll-Out Checklist

- [x] Implement LapIndexer adjustments – cover rules 3.1-3.4.
- [x] Update LapSaver validation and payload.
- [x] Migrate DB (add `lap_type`).
- [x] Write synthetic-trace tests; run them in CI.
- [] Do a live session, verify console logs show: "Finalised lap 5 (TIMED, 78.432 s)" immediately after SF crossing, even though no lap 6 ever started.
- [] Confirm Supabase shows OUT-lap rows where expected and no gap in lap numbers.
- [x] Verify robust handling of irregular data conditions:
  - [x] Correctly detects and logs LapCompleted cycling between laps
  - [x] Prevents invalid lap data from being saved to database
  - [x] Properly handles session time jumps and inconsistencies
- [x] Update UI components (if any) that assume consecutive timed laps. (No issues found with existing UI components)
- [] Push production build.

## 7. Time Estimate

- [x] LapIndexer logic & tests: 4–6 h (Logic implemented, tests passing)
- [x] LapSaver & worker adjustments: 1–2 h
- [x] DB migration + seed data: 0.5 h (Migration done, seed data not applicable here)
- [] Live verification pass: 1 h
- [x] Supabase schema alignment fix: 0.5 h
- [] Final production build and deployment: 0.5 h
- [] Total (with buffer): 1 working day + 0.5 h for unexpected fixes

---

This plan keeps out-laps and in-laps visible (good for coaching) while guaranteeing that every *timed* lap is persisted, even if the driver resets before iRacing starts lap N + 1. 

The system now correctly handles irregular data conditions from iRacing, such as lap cycling, time jumps, and other inconsistencies that can occur during replays, testing, or when players are repeatedly resetting. These situations are properly detected and logged, preventing invalid data from reaching the database. 