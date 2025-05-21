# Lap-Detection & Persistence Fix Plan

*(Issue: Bullring pit-exit mis-alignment causes off-by-one laps and overwriting of the prior timed lap)*

---

## 1  Problem Snapshot

| Symptom                                                                                                  | Diagnosed Cause                                                                                                                                      |
|-----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| • Last timed lap (e.g. lap 43) is overwritten by the following out-lap.<br>• All subsequent laps appear one number ahead of iRacing. | LapIndexer continues writing to the current lap while `OnPitRoad == True`.  On The Bullring the pit-stall is ≈0.31 `LapDistPct`, so the first 31 % of the next lap appends to the previous lap.  When `OnPitRoad` finally turns **False** (≈0.35), the collector closes the lap (coverage ≈0.69) and labels it **OUT**, overwriting the correct timed lap in the DB. |

---

## 2  Goal

1. Detect every crossing of the S/F line—even if the car is still flagged as *On Pit Road*.
2. Detect a *Reset / Tow* instantly and start a dedicated OUT-lap buffer.
3. Never allow a later lap to overwrite an already-validated row in the database.

---

## 3  Implementation Checklist (code pointers only)

| Area / File                                           | Change Summary |
|-------------------------------------------------------|----------------|
| `trackpro/race_coach/lap_indexer.py`                  | **close_if_needed( )** – add rule: *if `LapDistPct` drops by ≥0.95* (wrap-around) then close lap regardless of pit-state.<br>Use 0.02 hysteresis to avoid jitter near 1.00. |
| _same file_                                           | **handle_reset( )** *(new)* – detect teleport: `(prev_speed > 2 m/s  && speed < 0.5)` **and** `(ΔLapDistPct > 0.20)` while `OnPitRoad == True`; immediately close lap and start a new OUT-lap beginning at the teleport frame (`LapDistPct≈0.30`). |
| `trackpro/race_coach/simple_iracing.py::_on_telemetry`| Call `lap_indexer.handle_reset()` **before** existing lap-close logic so the reset event is handled first. |
| `trackpro/race_coach/storage/saver.py`                | Replace *upsert* on `(session_id, lap_number)` with **insert-only by `lap_uuid`**.<br>Add a unique DB constraint on `(session_id, lap_number)` so duplicates raise an error instead of silently overwriting. |

---

## 4  Test Suite (pytest – no iRacing needed)

### 4.1  Utility
```python
# tests/helpers.py
from collections import namedtuple
Frame = namedtuple("Frame", "dist_pct speed on_pit lap lap_completed")

def make_frame(dist, speed=30, on_pit=False, lap=0, completed=0):
    return {
        "LapDistPct": dist,
        "Speed": speed,
        "OnPitRoad": on_pit,
        "Lap": lap,
        "LapCompleted": completed,
        "SessionTimeSecs": 0.0,
    }
```

### 4.2  Unit Cases
| Test | Scenario | Assertions |
|------|----------|------------|
| `test_green_flag_lap()` | Feed frames 0.00→1.00, `OnPitRoad=False`. | One lap saved, `type==TIMED`, `coverage≈1.0`. |
| `test_reset_does_not_shift()` | Timed lap 0.00→1.00 then teleport frame 0.98→0.31 (`speed≈0`, `on_pit=True`) then 0.35→1.00. | Lap A saved *before* teleport, `TIMED` coverage≈1.0.<br>Lap B saved as `OUT`, coverage≈0.65.<br>No lap-number shift. |
| `test_outlap_classified_correctly()` | Start in pit-stall 0.30 (`on_pit=True`)→ blend 0.35 (`on_pit=False`) →1.00. | Lap classified `OUT`, coverage≈0.65, lap-number matches iRacing completed+1. |
| `test_db_unique_violation()` | Insert two laps with same `(session_id, lap_number)` via mocked saver. | UniqueViolation raised (ensures no overwrite). |

### 4.3  Integration Replay
Replay the 2 390-frame JSON captured from the log through the new pipeline; expect:
```python
laps = lap_indexer.get_laps()
assert [l.type for l in laps[:3]] == ["TIMED", "OUT", "TIMED"]
```

### 4.4  Performance Guard
Stream 10 min synthetic telemetry at 60 Hz through the pipeline; must finish in <2× realtime.

---

## 5  Manual In-Game Checklist
1. Drive one timed lap, press **Reset** just after S/F.
2. Exit pit, complete out-lap, then one hot-lap.
3. Verify in UI:
   * Lap N – `TIMED`, full distance.
   * Lap N+1 – `OUT`, ~65 % distance.
   * Lap N+2 – `TIMED`.
4. Check Supabase: three distinct UUIDs, unique `(session, lap_number)` rows.

---

## 6  Deployment Order
1. Write failing tests (RED).
2. Implement code (handle_reset, wrap-close, DB change) → all tests GREEN.
3. Run perf guard, lint & mypy.
4. Apply DB migration (unique constraint).
5. Push to staging & perform manual run.
6. Deploy to production once validated.

---

*Contact: dev-ops@trackpro  |  Owner: @race-coach-team  |  Last updated: <!-- CURSOR -->* 