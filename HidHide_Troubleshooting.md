# HidHide Troubleshooting Guide

## Overview

HidHide is a device driver that allows TrackPro to hide your physical pedals from games while still allowing TrackPro to read the input. This prevents games from receiving duplicate inputs from both your physical pedals and the virtual pedals created by TrackPro.

If you're experiencing issues with HidHide, this guide will help you troubleshoot common problems.

## Common Issues and Solutions

### "Access is denied" Errors

**Symptoms:**
- Error messages containing "Access is denied" or "Error code 0x0005"
- TrackPro shows warnings about HidHide not functioning properly
- Pedals are not hidden from games properly

**Solutions:**
1. **Run as Administrator**: Right-click TrackPro and select "Run as Administrator"
2. **Restart HidHide Service**:
   - Press `Win + R`, type `services.msc` and press Enter
   - Find "HidHide" in the list
   - Right-click it and select "Restart"
3. **Restart Windows**: Sometimes a full system restart is needed to resolve permission issues

### HidHide Installation Issues

**Symptoms:**
- Error messages about HidHide not being installed
- TrackPro fails to initialize HidHide

**Solutions:**
1. **Install/Reinstall HidHide**:
   - Download the latest version from [GitHub](https://github.com/ViGEm/HidHide/releases)
   - Uninstall any existing HidHide installation first
   - Install as Administrator
   - Restart your computer
2. **Verify Service**:
   - Press `Win + R`, type `services.msc` and press Enter
   - Ensure "HidHide" service exists and is set to "Automatic" startup
   - If it exists but isn't running, right-click and select "Start"

### Device Cloak State Issues

**Symptoms:**
- Error messages about "parameter is incorrect" or "Error setting cloak state"
- Games can still see your physical pedals even when TrackPro is running

**Solutions:**
1. **Manual Cloak Control**:
   - Press `Win + R`, type `cmd`, right-click and select "Run as Administrator"
   - Navigate to the HidHide installation folder (typically `C:\Program Files\Nefarius Software Solutions\HidHide\x64\`)
   - Run `HidHideCLI.exe --cloak-off` to disable cloaking
   - Restart TrackPro and let it manage cloaking
2. **Register TrackPro with HidHide**:
   - Press `Win + R`, type `cmd`, right-click and select "Run as Administrator"
   - Navigate to the HidHide installation folder
   - Run `HidHideCLI.exe --app-reg "C:\Program Files\TrackPro\TrackPro_v1.3.0.exe"` (adjust path to your installation)

### Persistent Device Hiding

**Symptoms:**
- Pedals remain hidden even after TrackPro is closed
- Unable to use pedals in other applications

**Solutions:**
1. **Manually Unhide Devices**:
   - Open Command Prompt as Administrator
   - Navigate to HidHide installation folder
   - Run `HidHideCLI.exe --cloak-off` to disable cloaking
   - Run `HidHideCLI.exe --dev-list` to see hidden devices
   - Run `HidHideCLI.exe --dev-unhide "DEVICE_ID"` for each device (replace DEVICE_ID with the actual ID from --dev-list)
2. **Restart Computer**:
   - A full system restart will typically reset HidHide's cloaking state

## Advanced Troubleshooting

### Check HidHide Status
1. Open TrackPro's debug window by clicking the "Debug" button in the UI
2. Look for log messages related to HidHide
3. Note any error codes or messages

### Manual Device Management
If TrackPro can't automatically manage your devices:

1. Use HidHideCLI.exe manually:
   ```
   HidHideCLI.exe --dev-list          # List hidden devices
   HidHideCLI.exe --dev-gaming        # List all gaming devices
   HidHideCLI.exe --cloak-off         # Disable cloaking
   HidHideCLI.exe --dev-unhide "ID"   # Unhide specific device
   ```

2. Check the Windows Device Manager:
   - Press `Win + X` and select "Device Manager"
   - Look under "Human Interface Devices" for your pedals
   - If they show with a yellow exclamation mark, there may be a driver issue

## Complete Reset Procedure

If all else fails, try this complete reset procedure:

1. Close TrackPro
2. Unplug your pedals
3. Open Command Prompt as Administrator
4. Navigate to HidHide installation folder
5. Run `HidHideCLI.exe --cloak-off`
6. Run `HidHideCLI.exe --dev-list` and unhide any listed devices
7. Restart your computer
8. Plug in your pedals
9. Start TrackPro as Administrator

## Getting Help

If you're still experiencing issues after trying these solutions, please:

1. Gather the following information:
   - TrackPro version
   - Windows version
   - HidHide version
   - Log files from the debug window
   - Device names/models

2. Contact support with this information through:
   - GitHub Issues: [TrackPro Issues](https://github.com/TrackPro/issues)
   - Discord: [TrackPro Community](https://discord.gg/trackpro) 