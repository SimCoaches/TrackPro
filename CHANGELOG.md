# Changelog

## 1.5.0 - 2025-01-15
- **MAJOR FIX**: Resolved critical issue where previous versions weren't deleted during updates
- Added automatic cleanup of old TrackPro versions during installation
- Enhanced installer to remove previous executables, shortcuts, and registry entries before installing new version
- User data (calibrations, settings, race data) is now properly preserved during updates
- Improved update process with better user feedback and progress indication
- Added version cleanup test script for verification
- Updated to version 1.5.0

## 1.4.8 - 2025-05-17
- Updated version to 1.4.8
- Fixed lap classification and recording to be BULLETPROOF
- Enhanced reliability of lap timing and data recording
- Improved session monitoring and lap detection accuracy

## 1.4.6 - 2025-04-26
- Fixed OAuth callback issues when signing up with Google
- Fixed connection errors during email signup
- Improved error handling for network connections
- Enhanced port conflict detection and handling
- Fixed 'err_empty_response' and 'err_connection_failed' errors

## 1.4.4 - 2025-04-25
- Updated version to 1.4.4
- Bug fixes and performance improvements

## 1.4.3 - 2025-04-20
- Updated version to 1.4.3
- [Insert other changes here]

## 1.4.2 - 2025-03-27
- Updated version to 1.4.2
- [Insert other changes here]

## 1.4.1 - 2025-03-21
- Updated version to 1.4.1
- [Insert other changes here]

## 1.3.8 - 2025-03-19
- Updated version to 1.3.8
- Added new image to README.md

## 1.3.6 - 2025-03-11
- Updated to version 1.3.6
- Bug fixes and performance improvements

## 1.3.5 - 2025-03-10
- Updated to version 1.3.5
- Bug fixes and performance improvements

## 1.3.4 - 2025-03-04
- Updated to version 1.3.4
- Updated documentation and version references
- Ensured consistent versioning across all project files

## 1.3.1 - 2025-03-01
- Updated to version 1.3.1
- Improved Windows Defender compatibility during updates
- Enhanced security handling for downloaded installers
- Added better error handling for system security warnings
- Fixed issues with executable detection after installation

## 1.3.0 - 2025-02-24
- Major version update to 1.3.0
- Comprehensive code cleanup and optimization
- Enhanced update process with interactive interface
- Improved installer detection and verification
- Added support for detecting TrackPro executables in multiple locations
- Fixed Windows Defender false positive detection during updates
- Added workarounds for security software blocking installation
- Improved download process to use more trusted locations
- Fixed various minor bugs and improved stability

## 1.2.24 - 2025-02-24
- Version update to 1.2.24
- Improved update process with enhanced debugging and error handling
- Fixed issue with installer detection during the update process
- Added support for detecting TrackPro executables in multiple locations

## 1.2.14 - 2025-02-14

### Added
- Version update to 1.2.14

## [1.2.13] - 2025-02-03

### Added
- Improved logging for HidHide operations
- Enhanced error handling for device management

### Fixed
- Simplified device unhiding process for better reliability
- Fixed issue with HidHide cloaking not being properly disabled on application exit
- Improved update process to ensure devices remain visible after updates
- Optimized cleanup process for more reliable operation

## [1.2.12] - 2025-02-03

### Added
- Enhanced updater testing functionality
- Improved uninstaller process for cleaner version transitions
- Added additional logging for update and uninstall operations

### Fixed
- Fixed critical issue where updates were installing to different locations
- Ensured old versions are properly deleted during the update process
- Fixed edge case in version comparison during update checks
- Improved cleanup of previous version files during updates
- Enhanced error handling during installation process

## [1.2.11] - 2025-02-01

### Added
- Enhanced uninstallation process for previous versions
- Added desktop shortcut option during installation
- Improved update process with better error handling

### Fixed
- Fixed issue where previous versions weren't properly uninstalled during updates
- Enhanced process termination for more reliable updates
- Improved shortcut management during version upgrades

## [1.2.9] - 2025-02-01

### Added
- Test version for updater functionality verification
- Enhanced version detection for update process

### Fixed
- Minor improvements to update notification system
- Optimized version comparison logic

## [1.2.8] - 2025-01-31

### Added
- Implemented direct HidHide driver integration using Windows API
- Added comprehensive device management for pedal visibility
- Enhanced logging for device hiding/unhiding operations

### Fixed
- Fixed critical issue with device visibility after application updates
- Improved device cleanup process during application exit
- Added verification step to ensure devices are properly unhidden
- Enhanced error handling for HidHide driver communication

## [1.2.7] - 2025-01-28

### Added
- Enhanced update notification system with improved user feedback
- Added detailed progress tracking for update downloads
- Improved logging for troubleshooting update issues

### Fixed
- Fixed issue with update detection when comparing version numbers
- Improved error handling during update installation process
- Enhanced parent window reference handling for update notifications
- Fixed issue where pedals remained hidden after application restart or update
- Added robust device cleanup to ensure pedals are properly unhidden on exit

## [1.2.6] - 2025-01-24

### Added
- Added download progress dialog for updates
- Enhanced device management during application updates

### Fixed
- Fixed issue where pedals remained hidden after application restart
- Improved update process to properly replace previous versions
- Added proper cleanup of devices before application exit

## [1.2.5] - 2025-01-24

### Added
- Improved error handling for update checks
- Added more detailed user feedback for update process
- Enhanced logging throughout the update checking process

### Fixed
- Fixed issue with update notification not showing proper feedback
- Resolved GitHub repository access for update checks
- Improved error messages when update server cannot be reached

## [1.2.4] - 2025-01-20

### Added
- Added File menu with "Exit" and "Check for Updates" options
- Added manual update check functionality
- Added non-intrusive update notification indicator at the bottom left

### Changed
- Improved auto-updater to allow manual update checks
- Changed update behavior to show notification instead of automatic prompt

## [1.2.3] - 2025-01-20

### Fixed
- Fixed clutch axis inversion issue - clutch now behaves consistently with throttle and brake axes
- Removed unnecessary axis inversion logic for more predictable behavior

## [1.2.2] - 2025-01-14

### Fixed
- Improved UI alignment of Reset and Linear buttons to be on the same plane as Set Min/Max buttons
- Added labels above Reset and Linear controls for better visual consistency

## [1.2.1] - 2025-01-13

### Fixed
- Fixed issue with calibration not persisting after application restart
- Improved error handling for device detection
- Fixed UI layout issues on high DPI displays

## [1.2.0] - 2025-01-12

### Added
- Support for multiple controller inputs
- Improved calibration wizard with automatic axis detection
- Enhanced curve editing with draggable control points
- Debug information panel for troubleshooting

### Changed
- Redesigned UI with dark theme for better visibility
- Improved performance for real-time input processing
- Updated documentation with detailed setup instructions

## [1.1.0] - 2025-01-11

### Added
- Curve management system for saving and loading custom curves
- Ability to save unlimited custom curves for each pedal (throttle, brake, clutch)
- Curve management UI with save, load, and delete functionality
- Default curve presets for each pedal type:
  - Throttle: Racing, Smooth, Aggressive
  - Brake: Hard Braking, Progressive
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

## [1.0.2] - 2025-01-10

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