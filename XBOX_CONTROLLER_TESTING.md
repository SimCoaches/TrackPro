# 🎮 Xbox Controller Testing Guide

## Quick Setup

Your Xbox controller can now be used to test the Threshold Braking Assist system!

### Controller Mapping:
- **🎯 Left Trigger (LT)** = Brake Pedal 
- **⚡ Right Trigger (RT)** = Throttle Pedal
- **🔄 Right Stick (Y-axis)** = Clutch Pedal

### How to Test:

1. **Connect your Xbox controller** to your PC
2. **Run the test UI**: `python test_threshold_ui.py`
3. **Check the console** - you should see:
   ```
   Hardware initialized with Xbox Controller for testing
   Xbox Controller mapping: RT=Throttle, LT=Brake, RStick=Clutch
   ```

### Testing the Threshold Assist:

1. **Enable the assist**: Check the "Enable Threshold Braking Assist" box
2. **Press Left Trigger** to simulate braking
3. **Press harder** to trigger the simulated ABS (at ~85% brake force)
4. **Watch the learning**: The system will learn your "lockup" point
5. **Test the assist**: After a few lockups, the system will limit your brake force automatically

### What You'll See:

**Learning Phase:**
- Green "Normal braking" when pressing lightly
- 🚨 "Simulated ABS activation" when pressing hard
- Learning progress increases with each lockup

**Assist Phase:**
- 🎯 "ASSIST ACTIVE: X% reduction" when pressing too hard
- Brake force is automatically limited to prevent lockup
- Perfect threshold braking every time!

### Real-time Feedback:

The status bar shows your current brake pressure and assist activity:
- `Brake: 45.2% | No assist needed` - Normal braking
- `Brake: 89.1% | Assist Active: 3.2% reduction` - Assist limiting force

## Alternative: Command Line Test

If you prefer command line testing:
```bash
python test_threshold_assist.py
```

Commands:
- `enable` - Enable threshold assist
- `status` - Show current status  
- `test` - Run automated test sequence
- `quit` - Exit

---

**🎯 Perfect for development and testing without needing actual racing pedals!** 