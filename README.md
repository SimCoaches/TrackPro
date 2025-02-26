# TrackPro v1.0.1

![TrackPro Logo](docs/images/logo.png)

## Advanced Pedal Input Mapping Software with Customizable Response Curves

TrackPro is a powerful application designed for sim racing enthusiasts who want precise control over their pedal inputs. It allows you to create custom response curves for throttle, brake, and clutch pedals, providing a tailored driving experience across different racing simulators.

## Features

- **Custom Response Curves**: Create and fine-tune non-linear response curves for each pedal
- **Real-time Visualization**: See your pedal inputs and outputs in real-time
- **Drag-and-Drop Calibration**: Easily adjust calibration points by dragging them on the graph
- **Multiple Curve Types**: Choose from Linear, Exponential, Logarithmic, and S-Curve presets
- **Device Hiding**: Automatically hides the physical device to prevent double inputs
- **Persistent Settings**: Your calibration settings are saved between sessions
- **Low Latency**: Designed for minimal input lag, critical for racing applications
- **Admin Mode**: Runs with administrator privileges to ensure proper device access

## Requirements

- Windows 10 or 11
- [vJoy Driver](https://github.com/jshafer817/vJoy/releases) (included in installer)
- [HidHide](https://github.com/ViGEm/HidHide/releases) (included in installer)
- Sim Coaches P1 Pro Pedals (or compatible USB pedals)

## Installation

### Option 1: Installer (Recommended)

1. Download the latest installer from the [Releases](https://github.com/yourusername/trackpro/releases) page
2. Run `TrackPro_Setup_v1.0.1.exe` and follow the installation instructions
3. The installer will automatically install vJoy and HidHide if they are not already installed
4. A system restart may be required after installation to complete driver setup

### Option 2: Manual Installation

1. Install [vJoy Driver](https://github.com/jshafer817/vJoy/releases) manually
2. Install [HidHide](https://github.com/ViGEm/HidHide/releases) manually
3. Download the standalone executable from the [Releases](https://github.com/yourusername/trackpro/releases) page
4. Run `TrackPro_v1.0.1.exe` as administrator

## Quick Start Guide

1. **Connect your pedals** to your PC via USB
2. **Launch TrackPro** from the Start Menu or Desktop shortcut
3. **Set Min/Max values** for each pedal by pressing them fully and clicking "Set Min" and "Set Max"
4. **Adjust the response curve** by dragging the red points on the graph
5. **Test your settings** by pressing the pedals and observing the green dot moving along the blue line
6. Your settings are automatically saved when you exit the application

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
- **Output Monitor**: Shows the processed output value sent to games

### Response Curve Types

- **Linear**: Direct 1:1 mapping between input and output
- **Exponential**: Provides finer control at the beginning of pedal travel
- **Logarithmic**: Provides more sensitivity at the end of pedal travel
- **S-Curve**: Combines aspects of both exponential and logarithmic for a balanced feel

### Advanced Configuration

TrackPro stores its configuration files in the following location:
```
%USERPROFILE%\.trackpro\
```

The main configuration files are:
- `calibration.json`: Contains the calibration points and curve types
- `axis_ranges.json`: Contains the min/max ranges for each pedal
- `hidhide.log`: Log file for HidHide operations

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
- `dist/TrackPro_v1.0.1.exe`: Standalone executable
- `TrackPro_Setup_v1.0.1.exe`: Full installer with dependencies

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

Project Link: [https://github.com/yourusername/trackpro](https://github.com/yourusername/trackpro) "Test push" 
