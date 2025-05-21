# Lap Recording Discrepancy Fix

## Problem Description

We've identified an issue in TrackPro where lap counting is inconsistent with iRacing:

1. **Missing laps**: Lap 5 appears to be missing from the recorded laps despite being shown in telemetry logs
2. **Count discrepancy**: TrackPro shows 6 laps while iRacing shows only 4 recorded laps
3. **User confusion**: This inconsistency creates a confusing experience for users

## Root Causes

1. **Lap Indexing Mismatch**:
   - iRacing uses 0-based indexing (lap 0 is the out lap)
   - TrackPro counts the out lap (lap 0) as lap 1, creating a +1 offset

2. **Validation Issues**:
   - Laps are validated based on track coverage and quality metrics
   - Current thresholds may be rejecting valid laps:
     ```python
     effective_threshold = 0.5  # Only 50% coverage required for most laps
     if is_out_lap or is_in_lap:
         effective_threshold = 0.4  # 40% coverage for out/in laps
     ```

3. **Lap Counting Logic**:
   - Code only saves laps if `completed_lap_number >= 1`
   - This correctly skips out laps but creates a counting offset
   - TrackPro may count laps that iRacing marks as invalid (e.g., "--" in lap display)

4. **UI Confusion**:
   - Lap 0 is displayed numerically rather than as "Out lap" in the UI
   - This increases confusion about lap count alignment with iRacing

## Implementation Rules and Constraints

The following rules must be strictly followed during implementation:

1. **Do Not Change Telemetry UI** 
   - The telemetry UI is working perfectly and must not be modified
   - Any UI changes should only apply to lap selection and display, not the telemetry graphs/charts

2. **Preserve iRacing Connection**
   - All changes must preserve the stability of the iRacing connection
   - No modifications to the core data collection routines that might disrupt the data feed

3. **Protect Session Saving**
   - Changes must not interfere with saving new sessions
   - Previous issues with session saving have occurred, and this functionality must remain stable

4. **Test in Isolation**
   - All changes should be tested in isolation before being merged
   - Create a separate test branch to validate changes before integrating with main code

5. **Backward Compatibility**
   - All changes must maintain backward compatibility with existing saved lap data
   - Users should not lose access to previously recorded sessions/laps

## Implementation Plan

### Phase 1: Fix Lap Counting Consistency
- [x] **PHASE 1 COMPLETE**

1. Modify `iracing_lap_saver.py` to use the same indexing system as iRacing:
- [ ] Update `iracing_lap_saver.py` to use iRacing's indexing
- [ ] Test changes in isolation

```python
# When initializing lap number, use iRacing value without adjustment
self._current_lap_number = iracing_current_lap  # directly use iRacing's value
```

2. Update lap display in UI to clearly label out laps vs. timed laps:
- [ ] Modify lap display formatting
- [ ] Verify changes don't affect telemetry UI

```python
# In lap display formatting
display_text = f"Lap {lap_num if lap_num > 0 else 'Out lap'}  -  {self._format_time(lap_time)}"
```

3. **Critical UI Change**: Replace all instances of "Lap 0" with "Out lap" throughout the interface:
- [ ] Identify all locations where "Lap 0" appears
- [ ] Replace with "Out lap" consistently
- [ ] Test UI display

```python
# In UI.py where laps are displayed in comboboxes or lists
def format_lap_display(lap_num, lap_time):
    if lap_num == 0:
        return f"Out lap  -  {self._format_time(lap_time)}"
    else:
        return f"Lap {lap_num}  -  {self._format_time(lap_time)}"
```

**Testing**:
- [ ] Run a test session with TrackPro
- [ ] Verify that lap numbers in TrackPro match iRacing
- [ ] Check that out laps are properly labeled as "Out lap" in the UI
- [ ] Confirm the same number of laps appear in both systems
- [ ] Specifically verify that users never see "Lap 0" anywhere in the interface

### Phase 2: Improve Lap Validation and Logging
- [ ] **PHASE 2 COMPLETE**

1. Add enhanced diagnostic logging to track lap validation:
- [ ] Implement detailed logging
- [ ] Verify log output is helpful for troubleshooting

```python
# In lap validation function
logger.info(f"Detailed validation for lap {completed_lap_number}: Coverage={coverage:.2f}, " +
           f"Required={effective_threshold}, Points={len(self._current_lap_data)}, " +
           f"Speed data valid: {max(speeds) > 0}")
```

2. Consider adjusting validation thresholds if needed:
- [ ] Review current thresholds
- [ ] Test various threshold values
- [ ] Implement adjusted thresholds

```python
# Updated thresholds if necessary
self._track_coverage_threshold = 0.5  # Lowered from 0.6
# For outlaps/inlaps
effective_threshold = 0.35  # Slightly more permissive
```

**Testing**:
- [ ] Run a test session collecting comprehensive logs
- [ ] Analyze logs to see why specific laps (like lap 5) are being rejected
- [ ] Check validation decisions make sense for the quality of data
- [ ] Verify all valid laps are being saved properly

### Phase 3: Enhance User Feedback
- [ ] **PHASE 3 COMPLETE**

1. Add clear indications in the UI for skipped/invalid laps:
- [ ] Update UI to mark invalid laps
- [ ] Test display formatting

```python
# When displaying laps in the UI
if not lap.get("is_valid", True):
    display_text = f"Lap {lap_num}  -  {self._format_time(lap_time)} [INVALID]" 
```

2. Add tooltips explaining validation issues:
- [ ] Implement tooltips
- [ ] Test tooltip display and content

```python
lap_item = self.left_lap_combo.addItem(display_text, lap_id)
if not lap.get("is_valid", True):
    validation_msg = lap.get("metadata", {}).get("validation_message", "Invalid lap")
    self.left_lap_combo.setItemData(
        self.left_lap_combo.count()-1, 
        validation_msg, 
        Qt.ToolTipRole
    )
```

3. Create a help dialog explaining lap counting differences:
- [ ] Create help dialog function
- [ ] Add menu item or button to access it
- [ ] Test dialog content and display

```python
# In a new help menu item or info button
def show_lap_counting_info(self):
    QMessageBox.information(
        self,
        "About Lap Counting",
        "TrackPro numbers laps the same way as iRacing:\n\n"
        "• Out lap: First time onto track (what iRacing calls 'Lap 0')\n"
        "• Lap 1: First timed lap\n\n"
        "Invalid laps may be marked or not shown based on data quality."
    )
```

**Testing**:
- [ ] Run a test session with the updated UI
- [ ] Verify invalid laps are clearly marked
- [ ] Check that tooltips show the correct validation messages
- [ ] Test the help dialog to ensure information is clear and accurate
- [ ] Confirm "Out lap" appears consistently instead of "Lap 0"

### Phase 4: Final Validation
- [ ] **PHASE 4 COMPLETE**

1. Run a full session with multiple laps including:
- [ ] Out lap
- [ ] Clean laps
- [ ] Laps with stops or issues
- [ ] In lap

2. Verify:
- [ ] TrackPro and iRacing show the same number of laps
- [ ] Lap numbering is consistent between both systems
- [ ] Invalid laps are clearly marked
- [ ] User feedback is clear and helpful
- [ ] The term "Out lap" is used consistently throughout the UI

3. Document results:
- [ ] Document any remaining discrepancies
- [ ] Address remaining issues
- [ ] Final sign-off on implementation

## Future Improvements

Consider these enhancements for future updates:

- [ ] Add option to save invalid laps but mark them as such
- [ ] Implement lap recovery features for partial data
- [ ] Improve validation algorithms for better lap quality detection
- [ ] Add visual track coverage maps to show where data is missing 