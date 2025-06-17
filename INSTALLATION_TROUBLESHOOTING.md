# TrackPro Installation Troubleshooting Guide

## Issue: TrackPro installs but doesn't open

If TrackPro installs successfully but doesn't open when you click on it, this is typically caused by missing dependencies or system compatibility issues that weren't caught during installation.

## Quick Fix Steps

### 1. Run the Diagnostic Tool (Recommended)
1. Look for "TrackPro Diagnostic Tool" in your Start Menu under TrackPro folder
2. Run the diagnostic tool to automatically check for missing dependencies
3. Follow the recommendations provided by the tool

### 2. Manual Troubleshooting

If the diagnostic tool isn't available, try these steps:

#### Check Error Logs
1. Look for error files on your Desktop:
   - `TrackPro_Error.txt`
   - `TrackPro_Diagnostic_Report.txt`
2. Check the Documents folder for logs:
   - `Documents/TrackPro_Logs/`

#### Verify Dependencies
Run these commands in Command Prompt (as Administrator):

```cmd
python --version
python -c "import PyQt5; print('PyQt5 OK')"
python -c "import numpy; print('NumPy OK')"
python -c "import requests; print('Requests OK')"
python -c "import psutil; print('Psutil OK')"
```

#### Install Missing Dependencies
If any modules are missing, install them:

```cmd
pip install PyQt5 PyQtWebEngine numpy requests psutil pygame matplotlib supabase
```

### 3. System Requirements Check

Ensure your system meets these requirements:
- **Windows 10 or 11** (64-bit)
- **Python 3.8 or newer**
- **4GB RAM minimum** (8GB recommended)
- **500MB free disk space**
- **Administrator privileges** for installation

### 4. Common Issues and Solutions

#### Issue: "Python not found"
**Solution:** Install Python 3.8+ from python.org, make sure to check "Add Python to PATH"

#### Issue: "PyQt5 not found"
**Solution:** Run `pip install PyQt5 PyQtWebEngine` as Administrator

#### Issue: "Access denied" or "Permission errors"
**Solution:** 
1. Right-click on TrackPro and select "Run as Administrator"
2. Disable antivirus temporarily during installation
3. Add TrackPro folder to antivirus exceptions

#### Issue: Silent failure (no error messages)
**Solution:** 
1. Run TrackPro from Command Prompt to see error messages:
   ```cmd
   cd "C:\Program Files\TrackPro"
   TrackPro_v1.5.1.exe
   ```
2. Check Windows Event Viewer for application errors

### 5. Advanced Troubleshooting

#### Enable Console Mode
The latest build includes console output for debugging. If TrackPro still won't start:

1. Open Command Prompt as Administrator
2. Navigate to TrackPro installation directory
3. Run the executable directly to see error messages

#### Clean Installation
1. Uninstall TrackPro completely
2. Delete any remaining TrackPro folders in Program Files
3. Clear TrackPro registry entries
4. Restart computer
5. Reinstall TrackPro as Administrator

#### Antivirus Issues
Some antivirus software may block TrackPro:
1. Add TrackPro installation folder to antivirus exceptions
2. Temporarily disable real-time protection during installation
3. Use Windows Defender instead of third-party antivirus

### 6. Improved Build Features (v1.5.1+)

Recent versions include these improvements to prevent silent failures:

- **Enhanced error logging** - Detailed logs saved to Documents/TrackPro_Logs/
- **Dependency checking** - Automatic verification of required modules
- **Error reporting** - Automatic error report generation on Desktop
- **Console mode** - Better error visibility during startup
- **Diagnostic tool** - Built-in system compatibility checker

### 7. Getting Help

If none of these solutions work:

1. **Run the diagnostic tool** and save the report
2. **Check error logs** in Documents/TrackPro_Logs/
3. **Look for error files** on your Desktop
4. **Contact support** with the following information:
   - Your Windows version
   - Python version (`python --version`)
   - Error logs and diagnostic reports
   - Any error messages you see

## Prevention for Future Builds

For developers building TrackPro:

1. **Use the updated build process** with enhanced dependency checking
2. **Test on clean VMs** without development tools installed
3. **Include the diagnostic tool** in distributions
4. **Enable console mode** for debugging in PyInstaller spec
5. **Bundle all dependencies** properly in the installer

## Technical Details

The main causes of "installs but won't run" issues:

1. **Missing Python modules** - PyInstaller didn't include all dependencies
2. **Missing system DLLs** - Windows runtime libraries not available
3. **Permission issues** - Application can't write to required directories
4. **Antivirus blocking** - Security software preventing execution
5. **Silent exceptions** - Errors occurring without user notification

The improved build process addresses these by:
- More comprehensive dependency collection
- Better error handling and logging
- Automatic system compatibility checking
- User-friendly diagnostic tools 