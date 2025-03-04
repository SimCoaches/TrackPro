# Changelog

All notable changes to TrackPro will be documented in this file.

## [1.2.2] - 2025-03-02

### Fixed
- Fixed clutch axis inversion issue - clutch now behaves consistently with throttle and brake axes
- Removed unnecessary axis inversion logic for more predictable behavior

## [1.2.1] - 2025-02-27

### Fixed
- Improved UI alignment of Reset and Linear buttons to be on the same plane as Set Min/Max buttons
- Added labels above Reset and Linear controls for better visual consistency

## [1.2.0] - 2025-02-26

### Added
- Support for multiple controller inputs
- Improved calibration wizard with automatic axis detection
- Enhanced curve editing with draggable control points
- Debug information panel for troubleshooting

### Changed
- Redesigned UI with dark theme for better visibility
- Improved performance for real-time input processing
- Updated documentation with detailed setup instructions

## [1.1.0] - 2025-01-15

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

## [1.0.2] - 2025-01-13

### Fixed
- Fixed issue with calibration not persisting after application restart
- Improved error handling for device detection
- Fixed UI layout issues on high DPI displays

## [1.0.1] - 2025-01-09

### Added
- Initial public release
- Custom response curves for throttle, brake, and clutch pedals
- Real-time visualization of pedal inputs and outputs
- Drag-and-drop calibration
- Multiple curve types (Linear, Exponential, Logarithmic, S-Curve)
- Device hiding to prevent double inputs
- Persistent settings
- Low latency input processing 