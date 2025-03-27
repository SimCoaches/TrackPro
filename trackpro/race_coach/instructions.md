# F1-Style Telemetry Comparison Implementation Guide

## Overview
This document outlines the steps to transform the current telemetry review UI into a clean, F1-style telemetry comparison visualization like the Monza Qualifying Analysis reference.

## Goals
- Remove unnecessary UI elements (crossed out in red)
- Create a focused telemetry visualization experience
- Match the F1 style layout with speed traces and delta time analysis
- Provide a clean interface for comparing two driver laps

## Implementation Plan

### 1. Clean Up Existing UI
- [x] Remove the top connection status bar and "Connect to iRacing" button
- [x] Remove "Telemetry Review" header and description text
- [x] Remove session selection dropdown and refresh button
- [x] Remove reference/comparison lap selection UI
- [x] Remove "Compare Laps" button
- [x] Redesign UI to focus solely on visualization components

### 2. Implement F1-Style Layout Structure
- [x] Arrange driver panels on left and right sides (already working)
- [x] Ensure driver names, lap times, and gaps are properly displayed
- [x] Center the track map between driver panels
- [x] Add dedicated space below for speed trace graph
- [x] Add dedicated space at bottom for delta visualization
- [x] Set appropriate sizing and spacing for all elements

### 3. Driver Information Panels (Left & Right)
- [x] Position number (1, 2)
- [x] Driver name with team color (LECLERC in red, SAINZ in yellow)
- [x] Team name (FERRARI)
- [x] Lap time display (1:23.456)
- [x] Gap display (-0.321s / +0.321s)
- [x] Performance metrics with horizontal bars:
  - [x] Full throttle percentage (81%)
  - [x] Heavy braking percentage (5%)
  - [x] Add cornering percentage (14%)

### 4. Track Map (Center)
- [x] Replace placeholder with proper track map rendering
- [x] Implement track map visualization with turn markers
- [x] Color-code track sections by speed (LOW/MEDIUM/HIGH)
- [x] Highlight sector boundaries
- [x] Add turn numbers at appropriate positions

### 5. Speed Trace Graph
- [ ] Implement speed visualization (similar to F1 example)
- [ ] Show both drivers' speed traces (red and yellow lines)
- [ ] Add horizontal grid lines with speed values (km/h)
- [ ] Add vertical sections with speed category labels (LOW/HIGH/MEDIUM SPEED)
- [ ] Add turn markers at the top of the graph (TURN 1, 2, 3, etc.)
- [ ] Ensure proper scaling of speed data

### 6. Delta Time Visualization
- [ ] Implement delta time graph at bottom
- [ ] Show time differences between drivers (red/green for slower/faster)
- [ ] Add delta values under each turn (-0.123, +0.321, etc.)
- [ ] Include "FASTER/SLOWER" scale indicator
- [ ] Ensure proper scale and readability

### 7. Data Processing
- [ ] Modify the data loading mechanism to work without UI controls
- [ ] Create API for programmatically setting comparison data
- [ ] Implement normalization for different length telemetry datasets
- [ ] Add functions to calculate delta values at key points

### 8. Visual Styling
- [ ] Use proper F1-style dark background (#111111)
- [ ] Apply consistent typography (condensed sans-serif fonts)
- [ ] Use official team colors (Ferrari red #FF0000, Ferrari yellow #FFCC00)
- [ ] Add subtle grid lines and section dividers
- [ ] Ensure consistent padding and alignment

### 9. Interaction
- [ ] Consider adding minimal non-intrusive controls for lap selection
- [ ] Implement hover effects on graph points to show detailed information
- [ ] Add ability to toggle between different metrics
- [ ] Consider adding quick lap selection mechanism

### 10. Testing and Refinement
- [ ] Test with real telemetry data from multiple laps
- [ ] Ensure proper handling of edge cases (missing data, large gaps)
- [ ] Optimize rendering performance for smooth display
- [ ] Validate visual accuracy compared to F1 reference

## Implementation Notes
- Focus on visual accuracy first, then add interactivity
- Leverage existing TelemetryComparisonWidget as the foundation
- Use QPainter for custom drawing of graphs and track map
- Consider creating reusable components for each visualization element
- Maintain consistent color scheme and styling throughout

## Technical Details
- The paintEvent method should be fully custom for proper rendering
- Use proper scaling for all data to ensure good visualization at any size
- Consider adding a dedicated handler for loading telemetry data 