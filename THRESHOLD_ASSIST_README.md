# Threshold Braking Assist - Testing Guide

## 🎯 Overview

The Threshold Braking Assist system automatically learns your brake lockup points and prevents you from exceeding them, ensuring you always brake at the optimal threshold for maximum stopping power without ABS activation.

## ✨ Key Features

- **Intelligent Learning**: Monitors `BrakeABSactive` from iRacing telemetry
- **Context-Aware**: Different thresholds per track/car combination  
- **Smooth Operation**: Gradual force reduction instead of hard cuts
- **Safety Limits**: Multiple safeguards prevent dangerous operation
- **Real-time Feedback**: Visual indicators show when assist is active

## 🚀 How It Works

### Learning Phase
1. Driver brakes normally while threshold assist monitors
2. When ABS activates (`BrakeABSactive = True`), system records brake input level
3. Calculates optimal threshold (default 2% below lockup point)
4. After 5+ ABS detections, graduates to assist mode

### Assist Phase  
1. When brake input exceeds learned threshold, system automatically limits force
2. Gradual reduction provides smooth, natural feel
3. No matter how hard you brake, you stay at perfect threshold

## 🛠️ Testing Options

### Option 1: Standalone Command Line Test
```bash
python test_threshold_assist.py
```
**Features:**
- Interactive commands (enable/disable, adjust settings, status)
- Automated test sequence with `--auto` flag
- Real-time brake processing with simulated ABS
- Command line interface for easy testing

### Option 2: Standalone UI Test
```bash
python test_threshold_ui.py
```
**Features:**
- Beautiful graphical interface
- Real-time status monitoring
- Learning progress indicator  
- Simulate ABS button for testing
- Visual activity indicators

### Option 3: Full TrackPro Integration
1. Run TrackPro normally: `python run_app.py`
2. The threshold assist is now integrated into the main pedal processing
3. Use Race Coach to connect to iRacing for real telemetry data
4. Settings are automatically saved per track/car combination

## 🎮 Testing Instructions

### Basic Testing (Without iRacing)
1. **Run a test script**: Choose option 1 or 2 above
2. **Enable threshold assist**: Check the enable box or type `enable`
3. **Press your brake pedal**: System will process your inputs
4. **Simulate ABS**: Click button or trigger simulation to test learning
5. **Watch the magic**: System learns and applies assist automatically

### Advanced Testing (With iRacing)
1. **Run full TrackPro**: `python run_app.py`
2. **Connect to iRacing**: Use Race Coach module
3. **Enable threshold assist**: Through main UI (when added)
4. **Drive normally**: System learns your car's brake characteristics
5. **Brake hard**: When you lockup, system learns and prevents future lockups

## 📊 User Interface Elements

### Threshold Assist Panel
- **Enable Checkbox**: Toggle assist on/off
- **Reduction Slider**: Adjust brake force reduction (1-10%)
- **Learning Progress**: Shows confidence level (0-100%)
- **Status Display**: Real-time system information
- **Reset Button**: Clear learning data for current track/car
- **Activity Indicator**: Shows when assist is actively reducing brake force

### Status Information
- **Current Context**: Track and car combination
- **Learning Mode**: Whether system is still learning or actively assisting
- **Optimal Threshold**: Learned brake threshold value
- **Confidence Level**: How confident the system is in its learning
- **ABS Detections**: Number of lockups detected for learning

## ⚙️ Configuration

### Default Settings
- **Reduction Percentage**: 2% (adjustable 1-10%)
- **Learning Rate**: 10% (how quickly it adapts)
- **Minimum Brake Threshold**: 30% (doesn't assist below this)
- **Maximum Reduction**: 15% (safety limit)

### Safety Features
- **Never reduces brake force by more than 15%**
- **Only activates above 30% brake input**
- **Can be instantly disabled**
- **Separate thresholds per track/car**
- **Gradual reduction prevents sudden changes**

## 🔧 Technical Details

### Files Modified/Added
- `trackpro/pedals/threshold_braking_assist.py` - Core assist system
- `trackpro/pedals/hardware_input.py` - Integration with pedal processing
- `trackpro/main.py` - Main app integration
- `trackpro/ui/threshold_assist_panel.py` - UI controls
- `test_threshold_assist.py` - Command line test
- `test_threshold_ui.py` - GUI test

### Integration Points
- **Pedal Processing**: Applied after calibration, before vJoy output
- **Telemetry**: Monitors `BrakeABSactive` from iRacing
- **Settings**: Saved with pedal calibration data
- **UI**: Real-time status and controls

## 🎯 Expected Results

### Learning Phase (First ~5 lockups)
```
🚨 SIMULATED ABS ACTIVATION at brake=0.870
🎯 ASSIST ACTIVE: 56831 -> 55294 (reduced by 2.7%)
📊 Road Atlanta_Mazda MX-5 Cup | Learning | Threshold: 0.852 | Detections: 3
```

### Assist Phase (After learning)
```
✅ 0.700 -> 0.700 (no assist needed)
🎯 0.900 -> 0.852 (reduced by 5.3%)
✅ Normal braking
🎯 ASSIST ACTIVE: 5.3% reduction
```

## 🐛 Troubleshooting

### Common Issues
1. **"Hardware initialization failed"** - Normal if no pedals connected, uses test mode
2. **"Virtual joystick initialization failed"** - Normal if vJoy not installed, uses test mode
3. **No assist activity** - Check that assist is enabled and brake input > 30%
4. **Learning not progressing** - Trigger ABS simulation or real lockups in iRacing

### Debug Tips
- Check console logs for detailed information
- Use `status` command in CLI test to see current state
- Verify telemetry connection in full TrackPro app
- Reset learning data if behavior seems incorrect

## 🏁 What's Next?

This implementation provides the foundation for threshold braking assist. Future enhancements could include:

- **Tire temperature compensation**
- **Weather condition adaptation** 
- **Track surface learning**
- **Brake fade detection**
- **Multi-corner threshold mapping**

The system is designed to be easily extensible for these advanced features!

---

**Ready to test?** Start with `python test_threshold_ui.py` for the best visual experience! 🎮 