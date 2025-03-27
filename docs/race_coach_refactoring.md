# Race Coach Module Refactoring

## Overview

The Race Coach module has been refactored from a large, monolithic `ui.py` file into multiple, more manageable files. This refactoring improves code maintainability and organization without changing functionality.

## Changes Made

1. Split the original code into logical components:
   - `gauges.py`: Contains gauge widget classes (GaugeBase, SpeedGauge, RPMGauge)
   - `input_trace.py`: Contains the InputTraceWidget for visualizing driver inputs
   - `telemetry_comparison.py`: Contains the TelemetryComparisonWidget for lap comparison
   - `race_coach.py`: Contains the main RaceCoachWidget

2. Updated imports and dependencies to maintain the same functionality

3. Added proper documentation in each file and a README.md in the race_coach directory

4. Updated the main `__init__.py` files to maintain backward compatibility:
   - `trackpro/__init__.py`: Now imports RaceCoachWidget from the race_coach module
   - `trackpro/race_coach/__init__.py`: Provides all necessary exports and helper functions

## Benefits

- **Improved Maintainability**: Each file now has a single responsibility and is much shorter
- **Better Organization**: Code is logically grouped by functionality
- **Easier Navigation**: Developers can find relevant code more quickly
- **Cleaner Dependencies**: Each file only imports what it needs
- **Backward Compatible**: Existing code using the old structure still works

## How to Use

The API remains largely unchanged:

```python
# Old way (still supported)
from trackpro.ui import RaceCoachWidget  # Still works through forwarding

# New way (preferred)
from trackpro.race_coach import RaceCoachWidget

# Or use the convenience function
from trackpro.race_coach import create_race_coach_widget
widget = create_race_coach_widget()
```

## Future Work

- Consider removing the old `ui.py` implementation once all code has been updated
- Further modularize telemetry analysis code
- Improve test coverage for the refactored components 