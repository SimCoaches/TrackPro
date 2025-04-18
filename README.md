# TrackPro v1.4.4

![TrackPro Logo](docs/images/logo.png)

## Advanced Pedal Input Mapping Software with Customizable Response Curves

TrackPro is a powerful application designed for sim racing enthusiasts who want precise control over their pedal inputs. It allows you to create custom response curves for throttle, brake, and clutch pedals, providing a tailored driving experience across different racing simulators.

## Features

- **Custom Response Curves**: Create and fine-tune non-linear response curves for each pedal
- **Curve Management**: Save, load, and manage multiple custom curves for each pedal
- **Cloud Sync Profiles**: Save your pedal profiles online and access them from any computer
- **Real-time Visualization**: See your pedal inputs and outputs in real-time
- **Drag-and-Drop Calibration**: Easily adjust calibration points by dragging them on the graph
- **Multiple Curve Types**: Choose from Linear, Exponential, Logarithmic, and S-Curve presets
- **Device Hiding**: Automatically hides the physical device to prevent double inputs
- **Persistent Settings**: Your calibration settings are saved between sessions
- **Low Latency**: Designed for minimal input lag, critical for racing applications
- **Admin Mode**: Runs with administrator privileges to ensure proper device access
- **iRacing Lap Time Tracking**: Save and analyze your lap times from iRacing in a Supabase database
- **Telemetry Analysis**: Compare your driving inputs across different laps to improve your racing lines

## Requirements

- Windows 10 or 11
- [vJoy Driver](https://github.com/jshafer817/vJoy/releases) (included in installer)
- [HidHide](https://github.com/ViGEm/HidHide/releases) (included in installer)
- Sim Coaches P1 Pro Pedals (or compatible USB pedals)

## Installation

### Standard Installation (Recommended)

1. Download the latest installer from [GitHub Releases](https://github.com/SimCoaches/TrackPro/releases/latest)
2. Run `TrackPro_Setup_v1.4.4.exe` and follow the installation instructions
3. If prompted, install any required dependencies
4. Run `TrackPro_v1.4.4.exe` as administrator

### Portable Installation (Advanced)

1. Download the portable version from [GitHub Releases](https://github.com/SimCoaches/TrackPro/releases/latest) 
2. Extract the ZIP file to a location of your choice
3. Install vJoy if not already installed
4. Run `TrackPro_v1.4.4.exe` as administrator

## Technical Notes

### Race Coach Module Refactoring

The Race Coach module has been refactored to improve maintainability. The module has been split from a single large file into multiple smaller files with specific responsibilities. See [Race Coach Refactoring Documentation](docs/race_coach_refactoring.md) for details.

## Quick Start Guide

1. **Connect your pedals** to your PC via USB
2. **Launch TrackPro** from the Start Menu or Desktop shortcut
3. **Set Min/Max values** for each pedal by pressing them fully and clicking "Set Min" and "Set Max"
4. **Adjust the response curve** by dragging the red points on the graph
5. **Save your custom curve** by entering a name and clicking "Save Curve"
6. **Test your settings** by pressing the pedals and observing the green dot moving along the blue line
7. Your settings are automatically saved when you exit the application

## Detailed Usage

### Calibration

Each pedal has its own calibration section with the following controls:

- **Input Monitor**: Shows the raw input value from the pedal
- **Calibration Graph**: 
  - Blue line: The response curve
  - Red points: Draggable calibration points
  - Green dot: Current pedal position
- **Min/Max Controls**: Set the minimum and maximum values for each pedal
- **Reset Button**: Resets the calibration to default linear response
- **Curve Type Selector**: Choose between different response curve types
- **Curve Management**: Save, load, and delete custom curves
- **Output Monitor**: Shows the processed output value sent to games

### Response Curve Types

- **Linear**: Direct 1:1 mapping between input and output
- **Exponential**: Provides finer control at the beginning of pedal travel
- **Logarithmic**: Provides more sensitivity at the end of pedal travel
- **S-Curve**: Combines aspects of both exponential and logarithmic for a balanced feel
- **Custom**: Create your own curve by dragging points to your preferred positions

### Curve Management

New in version 1.1.0, TrackPro allows you to save and manage multiple custom curves for each pedal:

1. **Save a Custom Curve**:
   - Adjust the curve points to your liking
   - Enter a name in the "Curve Name" field
   - Click "Save Curve"

2. **Load a Custom Curve**:
   - Select a saved curve from the dropdown list
   - Click "Load"
   - The curve will be applied immediately

3. **Delete a Custom Curve**:
   - Select a saved curve from the dropdown list
   - Click "Delete"
   - Confirm the deletion

Each pedal has its own set of saved curves, allowing you to create specific profiles for different racing games or driving styles.

### Cloud Pedal Profiles

New in version 1.4.4, TrackPro now supports cloud-synced pedal profiles:

1. **Save Pedal Profiles to the Cloud**:
   - Create an account or sign in via the "Login" option
   - Configure your pedals with your preferred settings
   - Go to File > Pedal Profiles > Save Current Settings as Profile
   - Enter a name and description for your profile
   - Your profile will be saved to your account

2. **Manage Profiles**:
   - Go to File > Pedal Profiles > Manage Profiles
   - View, load, update, or delete your saved profiles
   - Your profiles are accessible from any computer with TrackPro installed

3. **Load a Profile**:
   - Open the Manage Profiles dialog
   - Select the profile you want to load
   - Click "Load Selected Profile"
   - Your pedal settings will be updated immediately

This feature allows you to maintain consistent pedal response across different computers and easily switch between different setups for different games or tracks.

### iRacing Lap Time Tracking

New in version 1.4.4, TrackPro includes a powerful lap time tracking system for iRacing:

1. **Automatic Lap Detection**:
   - TrackPro automatically detects and records laps while you're racing in iRacing
   - All lap data is saved to a Supabase database for easy access and analysis
   - Includes lap times, sector times, and validity status

2. **Detailed Telemetry Recording**:
   - Full telemetry data is captured for each lap including:
     - Speed, RPM, and gear at each track position
     - Throttle, brake, and clutch inputs throughout the lap
     - Steering angle data for analyzing racing lines
   - Telemetry points are stored at multiple points around the track for detailed analysis

3. **View and Compare Lap Data**:
   - Compare your best laps to see where you can improve
   - Analyze throttle, brake, and steering inputs to optimize your driving technique
   - Track your progress over time as you improve your skills

4. **Access Your Data Anywhere**:
   - All lap data is stored in the cloud via Supabase
   - Access your lap history from any computer with TrackPro installed
   - Share your lap data with teammates or coaches for feedback

5. **Track and Car Database**:
   - Automatically organizes your lap data by track and car
   - Easily filter and find your best laps for specific track/car combinations
   - Compare performance across different cars on the same track

To use this feature, simply race in iRacing while TrackPro is running. Lap data will be automatically saved to your Supabase account. Access your lap history through the Race Coach tab in TrackPro.

### Preset Curves

TrackPro comes with several preset curves for each pedal:

- **Throttle**: Racing, Smooth, Aggressive
- **Brake**: Hard Braking, Progressive, ABS Simulation
- **Clutch**: Quick Engage, Gradual, Race Start

These presets provide a good starting point for customization.

### Advanced Configuration

TrackPro stores its configuration files in the following location:
```
%USERPROFILE%\.trackpro\
```

The main configuration files are:
- `calibration.json`: Contains the calibration points and curve types
- `axis_ranges.json`: Contains the min/max ranges for each pedal
- `hidhide.log`: Log file for HidHide operations
- `curves/`: Directory containing saved custom curves for each pedal

## Troubleshooting

### Common Issues

1. **Pedals not detected**
   - Ensure your pedals are properly connected via USB
   - Try a different USB port
   - Check if the pedals appear in Windows Game Controllers

2. **Double inputs in games**
   - Verify HidHide is properly installed and running
   - Check if the physical device is properly hidden in HidHide

3. **vJoy device not available**
   - Ensure vJoy is properly installed
   - Configure vJoy to have at least 3 axes (X, Y, Z)
   - Restart your computer after vJoy installation

4. **Application won't start**
   - Run the application as administrator
   - Check the Windows Event Viewer for error details
   - Verify that both vJoy and HidHide are installed

5. **Custom curves not appearing**
   - Check if the curves directory exists at `%USERPROFILE%\.trackpro\curves\`
   - Ensure you have write permissions to this directory
   - Try saving a new curve to see if it creates the necessary directories

### Logs

TrackPro logs detailed information that can help diagnose issues:
- Main log: Console output when running in non-windowed mode
- HidHide log: `%USERPROFILE%\.trackpro\hidhide.log`

## Building from Source

### Prerequisites

- Python 3.6+
- PyQt5
- pygame
- pywin32
- PyInstaller (for building the executable)

### Setup Development Environment

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/trackpro.git
   cd trackpro
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run_app.py
   ```

### Building the Executable

To build the standalone executable and installer:

```
python build.py
```

This will create:
- `dist/TrackPro_v1.1.0.exe`: Standalone executable
- `TrackPro_Setup_v1.1.0.exe`: Full installer with dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [vJoy](https://github.com/jshafer817/vJoy) for the virtual joystick driver
- [HidHide](https://github.com/ViGEm/HidHide) for the device hiding functionality
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) for the UI framework
- [pygame](https://www.pygame.org/) for joystick input handling

## Contact

Lawrence Thomas - [lawrence@simcoaches.com](mailto:lawrence@simcoaches.com)

Project Link: [https://github.com/SimCoaches/TrackPro](https://github.com/SimCoaches/TrackPro)
