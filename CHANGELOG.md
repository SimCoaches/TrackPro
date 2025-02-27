# Changelog

All notable changes to TrackPro will be documented in this file.

## [1.1.0] - 2023-11-15

### Added
- Curve management system for saving and loading custom curves
- Ability to save unlimited custom curves for each pedal (throttle, brake, clutch)
- Curve management UI with save, load, and delete functionality
- Default curve presets for each pedal type:
  - Throttle: Racing, Smooth, Aggressive
  - Brake: Hard Braking, Progressive, ABS Simulation
  - Clutch: Quick Engage, Gradual, Race Start
- Improved implementation of curve types (Linear, Exponential, Logarithmic, S-Curve)
- Custom curve type for user-defined curves

### Changed
- Updated UI to include curve management controls
- Improved curve selection dropdown to support custom curve types
- Enhanced calibration saving to preserve curve data

### Fixed
- Fixed issue where changing curve types had no effect on the actual curve
- Improved curve point handling for more precise control

## [1.0.2] - 2023-10-30

### Fixed
- Fixed issue with calibration not persisting after application restart
- Improved error handling for device detection
- Fixed UI layout issues on high DPI displays

## [1.0.1] - 2023-10-15

### Added
- Initial public release
- Custom response curves for throttle, brake, and clutch pedals
- Real-time visualization of pedal inputs and outputs
- Drag-and-drop calibration
- Multiple curve types (Linear, Exponential, Logarithmic, S-Curve)
- Device hiding to prevent double inputs
- Persistent settings
- Low latency input processing 