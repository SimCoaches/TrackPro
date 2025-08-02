# iRacing Telemetry Integration for New UI

## Overview

Your `new_ui.py` application now includes the **same global iRacing telemetry system** that the original `run_app.py` uses. This means all screens within your modern UI can access real-time telemetry data from iRacing, just like the original TrackPro application.

## What Was Added

### 1. Global iRacing Connection (`new_ui.py`)

- **Global API Instance**: A shared `SimpleIRacingAPI` instance that all screens can access
- **Automatic Initialization**: iRacing connection starts when the app launches
- **Telemetry Saving**: Automatically saves telemetry data to Supabase (if authenticated)
- **Session Monitoring**: Background monitoring for lap saving and session tracking
- **Clean Shutdown**: Proper cleanup when the application exits

### 2. Access Functions

```python
# Import the access function
from new_ui import get_global_iracing_api

# Get the global iRacing API instance
iracing_api = get_global_iracing_api()

# Check if connected
if iracing_api and iracing_api.is_connected():
    # Access real-time telemetry data
    speed = iracing_api.current_telemetry.get('Speed', 0)
```

### 3. Example Implementation

The `example_telemetry_screen.py` file shows exactly how to create a screen that displays live iRacing telemetry data:

- Real-time speed, RPM, throttle, brake, gear, etc.
- Session information (track name, car, session type)
- Connection status monitoring
- Proper callback registration and cleanup

## How to Use in Your Screens

### Step 1: Import the API Access Function

```python
from new_ui import get_global_iracing_api
```

### Step 2: Get the Global iRacing API Instance

```python
def setup_telemetry_connection(self):
    self.iracing_api = get_global_iracing_api()
```

### Step 3: Register for Telemetry Callbacks

```python
def on_telemetry_data(self, telemetry):
    """Called every time new telemetry data arrives."""
    speed = telemetry.get('Speed', 0)  # Speed in m/s
    throttle = telemetry.get('Throttle', 0)  # 0.0 to 1.0
    brake = telemetry.get('Brake', 0)  # 0.0 to 1.0
    # Process your telemetry data here...

# Register the callback
self.iracing_api.register_on_telemetry_data(self.on_telemetry_data)
```

### Step 4: Monitor Connection Status

```python
def on_connection_changed(self, is_connected, session_info):
    """Called when iRacing connection status changes."""
    if is_connected:
        print("✅ Connected to iRacing!")
        # Access session info like track name, car, etc.
        track_name = session_info.get('WeekendInfo', {}).get('TrackDisplayName', 'Unknown')
    else:
        print("❌ Disconnected from iRacing")

# Register the callback
self.iracing_api.register_on_connection_changed(self.on_connection_changed)
```

### Step 5: Access Current Telemetry Data Directly

```python
def update_display(self):
    """Update your UI with current telemetry data."""
    if self.iracing_api and self.iracing_api.current_telemetry:
        telemetry = self.iracing_api.current_telemetry
        
        # Get any telemetry value
        speed_ms = telemetry.get('Speed', 0)
        speed_mph = speed_ms * 2.237  # Convert m/s to mph
        
        rpm = telemetry.get('RPM', 0)
        gear = telemetry.get('Gear', 0)
        
        # Update your UI elements...
```

## Key Features

### ✅ Automatic iRacing Detection
- Automatically connects when iRacing is running
- Gracefully handles when iRacing is not running
- No manual connection/disconnection needed

### ✅ Real-Time Telemetry
- All iRacing telemetry data available in real-time
- Speed, RPM, throttle, brake, gear, track position, etc.
- Session information (track, car, session type)

### ✅ Data Persistence
- Automatically saves telemetry data to Supabase (if authenticated)
- Lap saving and session tracking
- Same data saving as the original TrackPro

### ✅ Global Access
- One connection shared by all screens
- No need for each screen to create its own connection
- Efficient resource usage

### ✅ Proper Cleanup
- Automatic cleanup when app shuts down
- No memory leaks or hanging connections

## Testing

Run the test script to verify everything is working:

```bash
python test_telemetry_integration.py
```

This will test:
- iRacing connection initialization
- API access functions
- Example screen imports
- Cleanup functionality

## Example Screen

The `example_telemetry_screen.py` file provides a complete working example that you can:

1. **Use as-is**: Add it directly to your UI to display telemetry data
2. **Use as template**: Copy and modify for your own screens
3. **Learn from**: See exactly how to implement telemetry in any screen

## Integration with Your UI

To add telemetry to any of your existing screens:

1. Import the global API access function
2. Get the API instance in your screen's `__init__` method
3. Register for telemetry callbacks
4. Update your UI when new data arrives
5. Handle connection status changes

The system is designed to be exactly like the original TrackPro - if you know how telemetry works in the original app, it works the same way here.

## What This Gives You

Your new modern UI now has **the same telemetry capabilities** as the original TrackPro:

- 🏁 **Real-time iRacing data** for any screen that needs it
- 📊 **All telemetry parameters** (speed, inputs, position, car data, etc.)
- 💾 **Automatic data saving** to Supabase cloud storage
- 🔄 **Session monitoring** and lap tracking
- 🎯 **Race Coach compatibility** - can use the same data sources
- 📈 **Track map overlays** - position data for live track visualization

This creates a unified telemetry system where all your screens can access the same high-quality iRacing data that powers the original TrackPro application.