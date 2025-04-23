# TrackPro v1.4.5

![TrackPro Logo](docs/images/logo.png)

## Professional Pedal Response Mapping & Racing Telemetry Suite

TrackPro is a sophisticated software solution designed specifically for competitive sim racers who demand precise control over pedal inputs and professional-grade telemetry analysis. This application transforms how your physical inputs translate to in-game performance through advanced response curve engineering, real-time visualization, and comprehensive data analysis.

## Core Technology

### Input Processing Architecture

TrackPro utilizes a multi-layered processing system to handle pedal inputs with microsecond precision:

1. **High-Resolution Signal Acquisition** - Captures raw pedal position data at 120Hz using direct USB polling to ensure minimal input lag
2. **Dynamic Signal Processing** - Applies customizable response curves to raw inputs in real-time using a proprietary algorithm
3. **Virtual Device Emulation** - Creates a virtual controller using vJoy's direct kernel-mode driver, ensuring the lowest possible latency between physical input and game response
4. **Device Conflict Management** - Uses HidHide's system-level device masking to prevent input duplication in games

The entire signal chain operates with an end-to-end latency of under 10ms, providing instant response that's critical for precise braking points and throttle control.

### Response Curve Engineering

TrackPro's curve processing engine uses mathematical transformations to modify your pedal's physical response characteristics:

- **Interpolation Method**: Piecewise cubic spline interpolation between control points ensures smooth transitions across the entire pedal travel
- **Deadzone Processing**: Independent min/max deadzones with adjustable thresholds to eliminate physical pedal imperfections
- **Control Point System**: Multi-point calibration with adjustable coordinates providing granular control of pedal response at specific positions

Each curve is rendered and processed using efficient computation, allowing for complex response patterns without affecting performance.

## Feature Details

### Advanced Pedal Mapping System

- **Custom Response Curves**: Engineer precisely tailored non-linear pedal responses with multi-point calibration
  - Dynamically adjust the relationship between physical pedal position and in-game input
  - Create precise S-curves for optimal trail braking control
  - Design progressive throttle responses for wet weather conditions
  - Engineer clutch bite-point precision for perfect race starts

- **Drag-and-Drop Control Points**: Manipulate response curves with highly intuitive interface
  - Direct visual representation of input-to-output relationship
  - Real-time preview of changes without requiring game restarts
  - Fine-tuned control over every aspect of pedal behavior

- **Curve Mathematics Library**: Multiple mathematical models for different driving styles
  - **Linear**: Direct 1:1 mapping for predictable, consistent response
  - **Exponential**: Provides increasingly sensitive response toward end of pedal travel
  - **Logarithmic**: Delivers enhanced precision at beginning of pedal travel
  - **S-Curve**: Combines both exponential and logarithmic characteristics for natural feel
  - **Custom**: Fully user-defined response with multiple control points

### Racing Telemetry & Analysis

- **iRacing Integration Engine**: Direct memory-mapped interface with iRacing for precise data capture
  - Automatic track detection and segmentation into sectors
  - Live telemetry capture with timestamp precision
  - Non-invasive integration that complies with iRacing's TOS

- **Comprehensive Data Collection**:
  - **Position Data**: Track position, racing line, and distance measurements
  - **Vehicle Dynamics**: Speed, lateral/longitudinal acceleration
  - **Control Inputs**: Throttle, brake, clutch positions and steering angle
  - **Powertrain**: Engine RPM, gear selection
  - **Timing**: Lap times, sector splits, and comparison deltas

- **Advanced Analysis Tools**:
  - Multi-lap overlay comparison with synchronized position data
  - Heat-map visualization of throttle/brake efficiency across track
  - Optimal braking point detection
  - Racing line optimization suggestions

### Cloud-Based Profile System

- **Synchronized Configuration Storage**: Cloud-based storage of all pedal configurations
  - Automatic profile synchronization
  - Conflict resolution for multi-device setups
  - Offline mode with scheduled synchronization

- **Database Architecture**: Secure Supabase PostgreSQL backend
  - Encryption for all stored configurations
  - Optimized query performance for telemetry datasets
  - Relational structure maintains associations between setups, tracks, and performance data

- **User Management**: Comprehensive account control with OAuth 2.0 integration
  - Google and Discord authentication options with secure token management
  - Fine-grained access controls for team-based sharing
  - Privacy options for performance data

## Technical Specifications

- **Signal Processing**:
  - Input polling rate: 120Hz
  - Processing resolution: 16-bit (65,536 discrete positions)
  - Response time: <10ms end-to-end
  
- **System Integration**:
  - vJoy device compatibility: v2.1.8+ (16-bit)
  - DirectInput/XInput compatibility: Full
  - Windows Game Controllers API integration
  - HidHide hardware masking support
  
- **Telemetry Engine**:
  - Data collection frequency: 60Hz
  - Supported games: iRacing (direct memory integration)
  - Export formats: CSV, JSON, TrackPro analysis format (.tpa)
  - Session data storage: Up to 24 hours of continuous recording

## Installation & Configuration

### System Requirements
- **Operating System**: Windows 10/11 (64-bit)
- **Processor**: Intel Core i3 / AMD Ryzen 3 or better
- **Memory**: 4GB RAM minimum
- **Storage**: 500MB available space
- **Required software**: 
  - vJoy 2.1.8+
  - .NET 6.0 Runtime
  - Visual C++ Redistributable 2019+
  - HidHide (recommended)

### Installation Process
1. Download the latest TrackPro installer from the Releases page
2. Run the installer and follow the on-screen instructions
3. Install vJoy driver if not already present (installer will prompt)
4. Optional: Install HidHide for device conflict management
5. Launch TrackPro and complete the initial setup wizard

### First-Time Setup
1. Connect your pedals and ensure they are recognized in Windows Game Controllers
2. Launch TrackPro and create your user account (or use OAuth with Google/Discord)
3. Follow the guided calibration wizard to configure your pedals
4. Create your first profile or select from pre-configured templates
5. Configure your output device settings for vJoy

## Detailed Usage Guide

### Calibration Workflow
1. **Initial Physical Calibration**:
   - Ensure pedals are properly connected and recognized
   - Use the Devices panel to verify raw input signals are being received
   - Perform full range calibration by pressing pedals to maximum and minimum positions
   - Adjust physical deadzone settings if necessary

2. **Response Curve Configuration**:
   - Select the pedal you wish to configure (Throttle, Brake, Clutch)
   - Choose a base curve type or start with Linear for a clean baseline
   - Add control points as needed by clicking on the curve
   - Drag points to adjust the response characteristics
   - Use the real-time preview to test changes immediately
   - Save your configuration with a descriptive name

3. **Game Integration Testing**:
   - Ensure vJoy is properly configured as a game controller
   - Verify TrackPro is outputting to the correct vJoy device
   - Launch your sim racing game and configure controls to use vJoy device
   - Test pedal response in-game and make fine adjustments as needed

### Pedal-Specific Tuning Guides

**Brake Pedal Optimization**:
- For load cell brakes: Use a logarithmic or S-curve for enhanced precision at higher brake pressures
- For potentiometer brakes: Consider an exponential curve to simulate progressive resistance
- Recommended settings: 5-10% deadzone at start of travel, subtle S-curve for trail braking

**Throttle Pedal Optimization**:
- For precise throttle control: Use a slight exponential curve (1.2-1.5 exponent)
- For wet weather racing: Stronger exponential curve (1.5-2.0) to prevent wheelspin
- For maximum acceleration: Linear curve with small initial deadzone (3-5%)

**Clutch Pedal Optimization**:
- For H-pattern shifting: Configure S-curve with pronounced middle section around bite point
- For standing starts: Adjust control point density around 30-40% travel for bite point precision
- For heel-toe technique: Consider a logarithmic curve for predictable engagement

## Performance Optimization

### System Tuning for Minimum Latency
- **Windows Settings Optimization**:
  - Disable USB selective suspend in Power Options
  - Set Windows power plan to High Performance
  - Disable Game Bar and Game Mode
  - Disable unnecessary background applications
  
- **Application Configuration**:
  - Enable "Performance Mode" in TrackPro settings
  - Adjust polling rate to match your USB controller capabilities
  - Disable telemetry collection when not actively analyzing performance
  - Use automatic profile switching only when necessary

### Racing Performance Impact
- **Braking Optimization**: Properly configured brake curves can reduce braking distances by up to 5-10 meters in heavy braking zones
- **Throttle Control**: Enhanced throttle mapping can improve corner exit speeds by 1-3 km/h through precise traction management
- **Consistency Improvement**: Users report lap time consistency improvements of up to 0.3 seconds through optimized pedal response

## Troubleshooting Advanced Issues

### Diagnostic Tools
- Built-in Input Analyzer: Visualizes raw input signals and processing steps
- Device Connection Tester: Verifies USB connectivity and polling rate
- vJoy Output Monitor: Confirms proper signal output to virtual controller
- System Performance Metrics: Monitors CPU usage and processing latency

### Common Issues & Solutions

**Input Lag or Stuttering**:
- Check USB port (use USB 3.0 ports when possible)
- Verify CPU usage is below 80% during operation
- Disable unnecessary background applications
- Ensure Windows Game DVR is disabled

**Profile Sync Failures**:
- Verify internet connection
- Check Supabase service status
- Try manual sync through profile menu
- Export local backup of profiles

**vJoy Device Not Detected**:
- Reinstall vJoy with administrator privileges
- Verify vJoy Control Panel shows configured device
- Check Windows Game Controllers for vJoy device
- Restart TrackPro with administrator privileges

## Community & Support

### Resources for Optimal Usage
- Official Documentation: [docs.trackpro.io](https://docs.trackpro.io)
- Video Tutorials: [TrackPro YouTube Channel](https://youtube.com/trackpro)
- Setup Guides: [Community Wiki](https://wiki.trackpro.io)

### Community Forums
- Official Discord Server: [discord.gg/trackpro](https://discord.gg/trackpro)
- Community Profile Sharing: Browse and download professionally tuned profiles
- Racing Team Integration: Special features for organized racing teams

### Support Channels
- Technical Support: [support@trackpro.io](mailto:support@trackpro.io)
- Bug Reports: [GitHub Issues](https://github.com/trackpro/issues)
- Feature Requests: [UserVoice Forum](https://trackpro.uservoice.com)

---

## License and Credits

TrackPro is proprietary software developed by Sim Coaches.

### Dependencies and Acknowledgments
- **vJoy**: Used for virtual controller emulation
- **HidHide**: Provides system-level device masking
- **Supabase**: Backend infrastructure for cloud features
- **PyQt5**: UI framework for cross-platform compatibility
- **iRacing SDK**: Telemetry data capture for Race Coach module

### Contact

Lawrence Thomas - [lawrence@simcoaches.com](mailto:lawrence@simcoaches.com)

Project Link: [https://github.com/SimCoaches/TrackPro](https://github.com/SimCoaches/TrackPro)
