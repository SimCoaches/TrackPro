# File Reorganization Changes

This document tracks the reorganization of files in the TrackPro-v1.3.8 project to improve the structure.

## Created Directories
- `trackpro/pedals/` - For all pedal-related functionality files

## Moved Files
| Original Location | New Location | Description |
|-------------------|--------------|-------------|
| trackpro/calibration.py | trackpro/pedals/calibration.py | Pedal calibration wizard |
| trackpro/hardware_input.py | trackpro/pedals/hardware_input.py | Hardware input handling for pedals |
| trackpro/hidhide.py | trackpro/pedals/hidhide.py | HidHide driver integration |
| trackpro/output.py | trackpro/pedals/output.py | Virtual joystick output |
| trackpro/HidHideClient.exe | trackpro/pedals/HidHideClient.exe | HidHide client executable |
| trackpro/HidHideCLI.exe | trackpro/pedals/HidHideCLI.exe | HidHide command-line executable |

## Path Updates
| File | Changes Made |
|------|-------------|
| trackpro/__init__.py | Updated imports to use `.pedals.hardware_input` and `.pedals.output` |
| trackpro/main.py | Updated imports to use `.pedals.hardware_input`, `.pedals.output`, and `.pedals.hidhide` |
| trackpro/ui.py | Updated import to use `.pedals.calibration` |
| trackpro/pedals/__init__.py | Created new file to expose the pedals module classes |

## Notes
- All original files are preserved in their original locations
- Import paths have been updated to maintain functionality
- The race_coach directory structure was already in place and remains unchanged 