# 10-Sector Timing Integration Guide

This guide explains how to integrate the new 10-sector timing system with your existing TrackPro telemetry processing for consistent cross-track sector analysis and superlap creation.

## Overview

The 10-sector timing system divides every track into 10 equal sectors based on LapDist (track position):
- **Sector 1**: 0.0 - 0.1 (0% - 10%)
- **Sector 2**: 0.1 - 0.2 (10% - 20%)
- **Sector 3**: 0.2 - 0.3 (20% - 30%)
- ...
- **Sector 10**: 0.9 - 1.0 (90% - 100%)

This provides consistent sector timing across all tracks, making it perfect for:
- Cross-track performance comparison
- Superlap creation by combining best sectors
- Consistent sector analysis regardless of track layout

## Files Created

### Core Components
1. **`trackpro/race_coach/simple_ten_sector_timing.py`** - Core 10-sector timing logic
2. **`trackpro/race_coach/ten_sector_integration.py`** - Integration wrapper for telemetry processing
3. **`trackpro/race_coach/ten_sector_example.py`** - Example implementation
4. **`test_ten_sector_timing.py`** - Test script to verify functionality

## Integration Steps

### Step 1: Basic Integration

To integrate 10-sector timing with your existing telemetry processing:

```python
from trackpro.race_coach.ten_sector_integration import TenSectorTimingIntegration

# Initialize the integration
ten_sector_timing = TenSectorTimingIntegration()

# In your telemetry processing loop:
def process_telemetry_frame(telemetry_data):
    # Process through 10-sector timing
    enhanced_frame = ten_sector_timing.process_telemetry_frame(telemetry_data)
    
    # The enhanced frame now contains sector timing data
    # Pass it to your existing lap saver
    lap_saver.process_telemetry(enhanced_frame)
```

### Step 2: Connect to Database Saving

The integration automatically embeds sector timing data into telemetry frames. Your existing `IRacingLapSaver` will detect and save this data:

```python
# Connect the sector timing system to the lap saver
lap_saver.set_sector_timing_system(ten_sector_timing)
```

### Step 3: Database Schema

The sector times are saved directly to the `laps` table:

```sql
-- The laps table has been extended to include 10 sector time columns
ALTER TABLE "laps" 
ADD COLUMN "sector4_time" DOUBLE PRECISION,
ADD COLUMN "sector5_time" DOUBLE PRECISION,
ADD COLUMN "sector6_time" DOUBLE PRECISION,
ADD COLUMN "sector7_time" DOUBLE PRECISION,
ADD COLUMN "sector8_time" DOUBLE PRECISION,
ADD COLUMN "sector9_time" DOUBLE PRECISION,
ADD COLUMN "sector10_time" DOUBLE PRECISION;

-- Existing columns: sector1_time, sector2_time, sector3_time
-- Each column represents the time for that sector (0-1 track position divided into 10 equal parts)
```

## Data Flow

1. **Telemetry Input**: Raw telemetry data with `track_position` (0.0-1.0)
2. **Sector Processing**: 10-sector timing system calculates current sector and times
3. **Frame Enhancement**: Sector data is embedded into telemetry frames
4. **Database Saving**: Enhanced frames are processed by `IRacingLapSaver`
5. **Sector Storage**: Sector times are saved directly to `laps` table columns (`sector1_time` through `sector10_time`)

## Enhanced Telemetry Frame Structure

The integration adds these fields to each telemetry frame:

```python
enhanced_frame = {
    # Original telemetry data...
    'track_position': 0.15,
    'speed': 60.0,
    # ... other telemetry fields
    
    # Added sector timing data:
    'sector_timing_initialized': True,
    'sector_timing_method': '10_equal_sectors',
    'current_sector': 2,  # 1-10
    'total_sectors': 10,
    'current_sector_time': 1.5,  # Time in current sector
    'completed_sectors_count': 1,
    'current_lap_sector_times': [2.5],  # Completed sector times
    'best_sector_times': [2.5, None, None, ...],  # Best time per sector
    'best_lap_time': 25.3,
    'sector_boundaries': [(0.0, 0.1), (0.1, 0.2), ...],
    
    # When a lap completes:
    'sector_times': [2.5, 2.8, 3.1, ...],  # All 10 sector times
    'sector_total_time': 25.3,
    'sector_lap_complete': True,
    'sector_lap_valid': True,
    'completed_lap_number': 1,
    
    # Direct lap table columns for database saving:
    'sector1_time': 2.5,
    'sector2_time': 2.8,
    'sector3_time': 3.1,
    'sector4_time': 2.9,
    'sector5_time': 3.2,
    'sector6_time': 2.7,
    'sector7_time': 3.0,
    'sector8_time': 2.6,
    'sector9_time': 2.8,
    'sector10_time': 2.9
}
```

## Usage Examples

### Get Current Sector Status
```python
status = ten_sector_timing.get_current_sector_info()
print(f"Current sector: {status['current_sector']}/10")
print(f"Sector time: {status['current_sector_time']:.3f}s")
```

### Get Theoretical Best Lap
```python
theoretical_best = ten_sector_timing.get_theoretical_best_lap()
if theoretical_best:
    print(f"Theoretical best: {theoretical_best['total_time']:.3f}s")
    for i, time in enumerate(theoretical_best['sector_times']):
        print(f"S{i+1}: {time:.3f}s")
```

### Compare Lap Performance
```python
comparison = ten_sector_timing.get_sector_comparison_for_lap(lap_number)
if comparison:
    print(f"Total delta vs best: {comparison['total_delta']:+.3f}s")
    for sector in comparison['sectors']:
        if sector['best_time']:
            delta = sector['delta']
            print(f"S{sector['sector_number']}: {delta:+.3f}s")
```

### Get Detailed Sector Breakdown
```python
breakdown = ten_sector_timing.get_lap_sector_breakdown(lap_number)
if breakdown:
    for sector in breakdown['sectors']:
        print(f"S{sector['sector_number']}: {sector['time']:.3f}s "
              f"({sector['percentage_of_lap']:.1f}% of lap)")
```

## Integration with Existing Code

### Modify Your Telemetry Processor

Replace your existing telemetry processing with:

```python
class YourTelemetryProcessor:
    def __init__(self):
        # Add 10-sector timing
        self.ten_sector_timing = TenSectorTimingIntegration()
        
        # Your existing components
        self.lap_saver = IRacingLapSaver(...)
        
        # Connect them
        self.lap_saver.set_sector_timing_system(self.ten_sector_timing)
    
    def process_telemetry(self, telemetry_data):
        # Process through sector timing first
        enhanced_frame = self.ten_sector_timing.process_telemetry_frame(telemetry_data)
        
        # Then pass to existing processing
        self.lap_saver.process_telemetry(enhanced_frame)
```

### Session Management

```python
def start_new_session(self):
    # Reset sector timing for new session
    self.ten_sector_timing.reset_session_data()
    
    # Your existing session setup...

def end_session(self):
    # Get final statistics
    stats = self.ten_sector_timing.get_statistics()
    logger.info(f"Session completed: {stats['laps_completed']} laps, "
                f"{stats['session_sectors_completed']} sectors")
```

## Superlap Creation

With consistent 10-sector timing, you can create superlaps by combining the best sector times:

```python
def create_superlap(self):
    # Get theoretical best lap
    superlap = ten_sector_timing.get_theoretical_best_lap()
    
    if superlap:
        # This represents the fastest possible lap using best sector times
        total_time = superlap['total_time']
        sector_times = superlap['sector_times']
        
        # You can now use this for:
        # 1. Performance targets
        # 2. Telemetry splicing (combine telemetry from best sectors)
        # 3. Analysis of improvement potential
        
        return {
            'total_time': total_time,
            'sector_times': sector_times,
            'improvement_potential': current_best_lap - total_time
        }

# Query sector times directly from database for analysis
def get_best_sector_times_from_db(session_id):
    """Get best sector times for a session from the laps table."""
    return {
        'sector1_best': "MIN(sector1_time) WHERE sector1_time IS NOT NULL",
        'sector2_best': "MIN(sector2_time) WHERE sector2_time IS NOT NULL",
        # ... etc for all 10 sectors
        # Use these to create theoretical best lap times
    }
```

## Testing

Run the test script to verify everything works:

```bash
python test_ten_sector_timing.py
```

This will test:
- Basic 10-sector timing functionality
- Integration wrapper
- Sector comparison and theoretical best calculation
- Database integration structure
- Statistics and session management

## Performance Considerations

- **Minimal Overhead**: The system adds minimal processing time to telemetry frames
- **Memory Efficient**: Only stores completed sector times and best times
- **Database Optimized**: Uses existing database schema and indexes

## Troubleshooting

### Common Issues

1. **No sector data in database**
   - Verify `set_sector_timing_system()` was called
   - Check that telemetry frames contain `track_position` field
   - Ensure `track_position` is in 0.0-1.0 range

2. **Incorrect sector boundaries**
   - The system uses exactly 10 equal sectors (0.0-0.1, 0.1-0.2, etc.)
   - Track-specific sectors are not used - this is intentional for consistency

3. **Missing lap completions**
   - Verify lap detection is working in your existing system
   - Check that `lap_count` or `Lap` field is present in telemetry

### Debug Information

Enable debug logging to see sector timing activity:

```python
import logging
logging.getLogger('trackpro.race_coach.simple_ten_sector_timing').setLevel(logging.DEBUG)
logging.getLogger('trackpro.race_coach.ten_sector_integration').setLevel(logging.DEBUG)
```

## Next Steps

1. **Integrate with your main telemetry processing**
2. **Add UI components to display sector timing**
3. **Implement superlap creation features**
4. **Add sector-based performance analysis**

The system is now ready for production use and will automatically save sector timing data to your database for all future laps! 