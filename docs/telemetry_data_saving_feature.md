# Telemetry Data Saving Feature for Race Coach App

We need to enhance our existing Python-based Race Coach application to save telemetry data per lap so users can review complete lap data later. Below are the details and requirements for this feature.

## Current State
- Our app already collects and displays telemetry data in real-time, including:
  - Throttle pressure
  - Brake pressure
  - Steering angle
  - Lap time
  - Best lap
  - Lap count
- The app is fully written in Python.

## Goal
- Save telemetry data for each lap.
- Allow users to go back and review data for individual laps.
- Lap timing starts when the user crosses the start line and ends when they cross the finish line, defining one complete lap.

## Requirements
### 1. Lap Detection
- Implement a mechanism to detect when a lap starts and ends.
- Use a "start/finish line" trigger to mark the beginning and end of a lap.
- Reset the lap time and start collecting data for a new lap when the start/finish line is crossed again.

### 2. Data Storage Structure
- Store telemetry data in a structured format for each lap.
- Each lap's data should include:
  - Throttle pressure (time-series data for the lap)
  - Brake pressure (time-series data for the lap)
  - Steering angle (time-series data for the lap)
  - Lap time (total time for the lap)
  - Lap number
  - Timestamp (optional, for reference)
- Ensure data is saved with enough granularity.

### 3. Saving Data
- Save the lap data in memory during the session.
- Write the data to a persistent storage format at the end of each lap or session.
- Ensure the file/storage is organized by session and lap number.

### 4. Data Retrieval
- Create a function to load and display saved lap data.
- Allow users to select a specific lap and view its telemetry data.
- Display the data in the app similar to how real-time data is currently shown.

### 5. Integration with Existing App
- Ensure this feature integrates seamlessly with the current telemetry display system.
- Update the lap count and best lap logic to work with the saved data.

## Implementation Progress
- [ ] Lap Detection Logic
- [ ] Data Collection
- [ ] Data Saving
- [ ] Data Retrieval
- [ ] UI Integration 