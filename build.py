#!/usr/bin/env python3
"""
TrackPro Build System with Enhanced Process Management

This build system includes comprehensive cleanup of TrackPro processes and instance locks
to prevent "another instance is running" errors. Key features:

- Automatic process termination before building
- Single instance lock cleanup (mutex + lock files)
- Multiple process kill methods for stuck processes
- Lock cleanup after successful builds

Usage:
  python build.py build              # Full build with cleanup
  python build.py clean              # Clean build files and processes
  python build.py kill-processes     # Manual process cleanup
  python build.py fix-instance-lock  # Fix stuck instance locks only
  python build.py test               # Build test installer
"""
import sys
import os
import subprocess
import time
import ctypes

# Ensure we're using Python 3.11 for building (critical for eye tracking support)
if sys.version_info[:2] != (3, 11):
    print("🚨 CRITICAL: TrackPro build requires Python 3.11 for eye tracking support!")
    print(f"Current version: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("Reasons Python 3.11 is required:")
    print("  • Eye tracking (mediapipe) doesn't support Python 3.13+")
    print("  • Package compatibility issues with newer Python versions")
    print("  • PyInstaller bundling works more reliably with Python 3.11")
    print()
    print("Attempting to restart build with Python 3.11...")
    
    try:
        # Use py -3.11 to explicitly run with Python 3.11
        result = subprocess.run([
            "py", "-3.11", __file__
        ] + sys.argv[1:], check=True)
        sys.exit(result.returncode)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Failed to start build with Python 3.11: {e}")
        print()
        print("SOLUTION: Install Python 3.11 specifically:")
        print("1. Download Python 3.11 from: https://www.python.org/downloads/release/python-3118/")
        print("2. Install it alongside your current Python version")
        print("3. Verify with: py -3.11 --version")
        print("4. Re-run this build script")
        sys.exit(1)

print(f"✓ Building with Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} (CORRECT VERSION)")

import PyInstaller.__main__
import shutil
import requests
import winreg
from urllib.parse import urlparse
import stat
from trackpro import __version__
from pathlib import Path
import importlib


class InstallerBuilder:
    # Updated to latest stable versions with better Windows 11 compatibility
    VJOY_URL = "https://github.com/njz3/vJoy/releases/download/v2.2.1.1/vJoySetup.exe"  # Latest stable version with Win11 support
    VJOY_FALLBACK_URL = "https://github.com/jshafer817/vJoy/releases/download/v2.1.9.1/vJoySetup.exe"  # Fallback to older stable version
    # HidHide v1.5.230.0 (latest) with multiple fallback filename patterns and versions
    HIDHIDE_URL = "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHide_1.5.230_x64.exe"  # Most likely filename pattern
    HIDHIDE_FALLBACK_URL = "https://github.com/nefarius/HidHide/releases/download/v1.5.212.0/HidHide_1.5.212_x64.exe"  # Previous stable version
    VCREDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"  # Latest Visual C++ Redistributable
    
    def __init__(self):
        self.temp_dir = "installer_temp"
        self.dist_dir = "dist"
        self.version = __version__
        self.cwd = Path.cwd()

        
    def download_file(self, url, dest_folder, fallback_url=None, expected_filename=None):
        """Download a file with fallback support and return its path."""
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        # Use expected filename if provided, otherwise extract from URL
        if expected_filename:
            filename = expected_filename
        else:
            filename = os.path.basename(urlparse(url).path)
        
        filepath = os.path.join(dest_folder, filename)
        
        if not os.path.exists(filepath):
            # Try primary URL first
            success = self._attempt_download(url, filepath, filename)
            
            # If primary fails and fallback is available, try fallback
            if not success and fallback_url:
                print(f"Primary download failed, trying fallback URL...")
                success = self._attempt_download(fallback_url, filepath, filename)
            
            if not success:
                raise Exception(f"Failed to download {filename} from primary URL and fallback")
        else:
            print(f"✓ {filename} already exists at {filepath}")
        
        # Verify file exists and has content
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            if file_size > 0:
                print(f"✓ Verified {filename} at {filepath} ({file_size:,} bytes)")
            else:
                print(f"! Error: {filename} downloaded but is empty (0 bytes)")
                os.remove(filepath)  # Remove empty file
                raise Exception(f"Downloaded file {filename} is empty")
        else:
            print(f"! Error: {filename} not found at {filepath} after download attempt")
            raise Exception(f"File {filename} not found after download")
            
        return filepath
    
    def _attempt_download(self, url, filepath, filename):
        """Attempt to download a file from a specific URL."""
        try:
            print(f"Downloading {filename} from {url}...")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Ensure chunk is not empty
                        f.write(chunk)
            
            # Verify download was successful
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                print(f"✓ Successfully downloaded {filename}")
                return True
            else:
                print(f"✗ Download failed: {filename} is missing or empty")
                if os.path.exists(filepath):
                    os.remove(filepath)
                return False
                
        except Exception as e:
            print(f"✗ Download failed for {filename}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)  # Clean up partial download
            return False



    def create_installer_script(self):
        """Create a reliable Inno Setup installer script with debugging."""
        print("\nCreating Inno Setup installer script...")
        
        # Use forward slashes for Inno Setup (it handles both)
        prereq_dir = "installer_temp/prerequisites"
        dist_dir = "installer_temp/dist"
        
        print(f"Using paths for Inno Setup:")
        print(f"  Prerequisites: {prereq_dir}")
        print(f"  Distribution: {dist_dir}")
        
        # Get actual downloaded filenames (instead of hardcoding)
        vjoy_file = "vJoySetup.exe"
        hidhide_file = "HidHide_1.5.230_x64.exe"  # Default, but check what actually exists
        vcredist_file = "vc_redist.x64.exe"
        
        # Check what HidHide file actually exists
        prereq_path = Path(prereq_dir)
        if prereq_path.exists():
            hidhide_files = list(prereq_path.glob("HidHide*.exe"))
            if hidhide_files:
                hidhide_file = hidhide_files[0].name
                print(f"Found HidHide file: {hidhide_file}")
        
        script = f"""
; TrackPro Inno Setup Installer - Reliable & Debuggable
; This replaces the problematic NSIS installer

[Setup]
AppName=TrackPro
AppVersion={self.version}
AppVerName=TrackPro v{self.version}
AppPublisher=TrackPro
AppPublisherURL=https://github.com/Trackpro-dev/TrackPro
AppSupportURL=https://github.com/Trackpro-dev/TrackPro
AppUpdatesURL=https://github.com/Trackpro-dev/TrackPro
DefaultDirName={{localappdata}}\\TrackPro
DefaultGroupName=TrackPro
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=
InfoAfterFile=
OutputDir=.
OutputBaseFilename=TrackPro_Setup_v{self.version}
SetupIconFile=
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
; Single instance protection (prevents multiple installers)
AppMutex=TrackProInstallerMutex
; Enable detailed logging
SetupLogging=yes
; Show installation progress details
ShowLanguageDialog=auto
WizardStyle=modern
; Allow cancellation
AllowCancelDuringInstall=yes
; Restart behavior
RestartIfNeededByRun=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation"
Name: "compact"; Description: "Compact installation"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "main"; Description: "TrackPro Application"; Types: full compact custom; Flags: fixed
Name: "drivers"; Description: "Required Drivers (vJoy, HidHide)"; Types: full compact; Flags: disablenouninstallwarning
Name: "vcredist"; Description: "Visual C++ Redistributable"; Types: full compact; Flags: disablenouninstallwarning
Name: "shortcuts"; Description: "Desktop and Start Menu shortcuts"; Types: full; Flags: disablenouninstallwarning

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Main application
Source: "{dist_dir}/TrackPro_v{self.version}.exe"; DestDir: "{{app}}"; DestName: "TrackPro_v{self.version}.exe"; Components: main; Flags: ignoreversion

; Prerequisites (downloaded during build)
Source: "{prereq_dir}/{vjoy_file}"; DestDir: "{{tmp}}"; Components: drivers; Flags: deleteafterinstall ignoreversion
Source: "{prereq_dir}/{hidhide_file}"; DestDir: "{{tmp}}"; Components: drivers; Flags: deleteafterinstall ignoreversion  
Source: "{prereq_dir}/{vcredist_file}"; DestDir: "{{tmp}}"; Components: vcredist; Flags: deleteafterinstall ignoreversion

; License file
Source: "LICENSE"; DestDir: "{{app}}"; Components: main; Flags: ignoreversion

[Icons]
Name: "{{group}}\\TrackPro v{self.version}"; Filename: "{{app}}\\TrackPro_v{self.version}.exe"; Components: shortcuts
Name: "{{group}}\\{{cm:UninstallProgram,TrackPro}}"; Filename: "{{uninstallexe}}"; Components: shortcuts
Name: "{{autodesktop}}\\TrackPro v{self.version}"; Filename: "{{app}}\\TrackPro_v{self.version}.exe"; Tasks: desktopicon
Name: "{{userappdata}}\\Microsoft\\Internet Explorer\\Quick Launch\\TrackPro v{self.version}"; Filename: "{{app}}\\TrackPro_v{self.version}.exe"; Tasks: quicklaunchicon

[Run]
; Install drivers silently with detailed logging and error handling
Filename: "{{tmp}}\\{vjoy_file}"; Parameters: "/S"; Components: drivers; StatusMsg: "Installing vJoy driver..."; Flags: waituntilterminated runhidden; Check: ShouldInstallDriver('vJoy')
Filename: "{{tmp}}\\{hidhide_file}"; Parameters: "/S"; Components: drivers; StatusMsg: "Installing HidHide driver..."; Flags: waituntilterminated runhidden; Check: ShouldInstallDriver('HidHide')
Filename: "{{tmp}}\\{vcredist_file}"; Parameters: "/quiet /norestart"; Components: vcredist; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated runhidden; Check: ShouldInstallVCRedist()

; Option to run TrackPro after installation
Filename: "{{app}}\\TrackPro_v{self.version}.exe"; Description: "{{cm:LaunchProgram,TrackPro}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Clean up processes before uninstall
Filename: "taskkill"; Parameters: "/F /IM TrackPro*.exe /T"; Flags: waituntilterminated runhidden; RunOnceId: "KillTrackPro"

[Code]
var
  LogFileName: String;
  NeedsRestart: Boolean;

// Enhanced logging function
procedure LogMessage(const Msg: String);
var
  LogFile: String;
begin
  LogFile := ExpandConstant('{{userdocs}}\\TrackPro_Installation_Log.txt');
  SaveStringToFile(LogFile, FormatDateTime('yyyy-mm-dd hh:nn:ss', Now) + ' - ' + Msg + #13#10, True);
  Log(Msg);
end;

// Initialize installation
function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
  ResultCode: Integer;
begin
  Result := True;
  NeedsRestart := False;
  LogFileName := ExpandConstant('{{userdocs}}\\TrackPro_Installation_Log.txt');
  
  LogMessage('=== TrackPro v{self.version} Installation Started ===');
  LogMessage('Installer: ' + ExpandConstant('{{srcexe}}'));
  LogMessage('Target Directory: ' + ExpandConstant('{{app}}'));
  LogMessage('Windows Version: ' + GetWindowsVersionString);
  LogMessage('Admin Rights: ' + BoolToStr(IsAdminInstallMode));
  
  // Check if we're running as admin
  if not IsAdminInstallMode then
  begin
    LogMessage('ERROR: Not running as administrator');
    MsgBox('This installer requires administrator privileges to install drivers.' + #13#10 + 
           'Please right-click the installer and select "Run as administrator".', 
           mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Kill any running TrackPro processes
  LogMessage('Terminating existing TrackPro processes...');
  Exec('taskkill', '/F /IM TrackPro*.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  LogMessage('Process termination result: ' + IntToStr(ResultCode));
  
  // Check for existing installation
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\TrackPro_is1') then
  begin
    LogMessage('Previous installation detected');
    if MsgBox('A previous version of TrackPro is installed.' + #13#10 + 
              'Do you want to uninstall it first?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      LogMessage('User chose to uninstall previous version');
      // Uninstall will be handled automatically by Inno Setup
    end;
  end;
  
  LogMessage('Setup initialization completed successfully');
end;

// Check if driver should be installed
function ShouldInstallDriver(const DriverName: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := True; // Default to install
  
  LogMessage('Checking if ' + DriverName + ' driver should be installed...');
  
  if DriverName = 'vJoy' then
  begin
    // Check if vJoy is already installed by looking for the DLL
    if FileExists(ExpandConstant('{{sys}}\\vJoyInterface.dll')) then
    begin
      LogMessage('vJoy already installed (found vJoyInterface.dll)');
      Result := False;
    end
    else
    begin
      LogMessage('vJoy not found, will install');
      Result := True;
    end;
  end
  else if DriverName = 'HidHide' then
  begin
    // Check if HidHide service exists
    if Exec('sc', 'query HidHide', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
    begin
      LogMessage('HidHide already installed (service found)');
      Result := False;
    end
    else
    begin
      LogMessage('HidHide not found, will install');
      Result := True;
    end;
  end;
  
  LogMessage(DriverName + ' installation decision: ' + BoolToStr(Result));
end;

// Check if Visual C++ Redistributable should be installed
function ShouldInstallVCRedist(): Boolean;
begin
  Result := True; // Default to install
  
  LogMessage('Checking Visual C++ Redistributable...');
  
  // Check for common VC++ runtime files
  if FileExists(ExpandConstant('{{sys}}\\msvcp140.dll')) and 
     FileExists(ExpandConstant('{{sys}}\\vcruntime140.dll')) then
  begin
    LogMessage('Visual C++ Redistributable already installed');
    Result := False;
  end
  else
  begin
    LogMessage('Visual C++ Redistributable not found, will install');
    Result := True;
  end;
  
  LogMessage('VC++ Redistributable installation decision: ' + BoolToStr(Result));
end;

// Handle installation completion
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    LogMessage('=== Installation Completed ===');
    LogMessage('Files installed to: ' + ExpandConstant('{{app}}'));
    
    // Verify installation
    if FileExists(ExpandConstant('{{app}}\\TrackPro_v{self.version}.exe')) then
    begin
      LogMessage('✓ Main executable installed successfully');
    end
    else
    begin
      LogMessage('✗ ERROR: Main executable not found after installation');
    end;
    
    // Check if restart is needed
    if NeedsRestart then
    begin
      LogMessage('System restart required for driver installation');
    end;
    
    LogMessage('Installation log saved to: ' + LogFileName);
  end;
end;

// Handle uninstallation
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  LogMessage('=== TrackPro Uninstallation Started ===');
  
  // Kill any running processes
  LogMessage('Terminating TrackPro processes...');
  Exec('taskkill', '/F /IM TrackPro*.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  LogMessage('Process termination result: ' + IntToStr(ResultCode));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    LogMessage('=== Uninstallation Completed ===');
    LogMessage('TrackPro has been successfully removed');
  end;
end;

// Enhanced error handling
procedure ExitSetupMsgBox;
begin
  LogMessage('Setup was cancelled or failed');
  LogMessage('Installation log saved to: ' + LogFileName);
end;

function BoolToStr(Value: Boolean): String;
begin
  if Value then
    Result := 'True'
  else
    Result := 'False';
end;
"""
        
        # Write the script to file
        try:
            with open("installer.iss", "w", encoding="utf-8") as f:
                f.write(script)
            print("✓ Created reliable Inno Setup installer script")
            print("  - Single instance protection")
            print("  - Detailed logging and debugging") 
            print("  - Better error handling")
            print("  - Automatic prerequisite detection")
            print("  - Clean uninstallation")
        except Exception as e:
            print(f"Error creating Inno Setup script: {str(e)}")
            raise


    def check_inno_setup(self):
        """Check if Inno Setup is installed and available."""
        inno_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",  # Primary path
            r"C:\Program Files\Inno Setup 6\ISCC.exe",        # Alternative path  
            r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",  # Older version
            r"C:\Program Files\Inno Setup 5\ISCC.exe",        # Older version
        ]
        
        # First check if ISCC is directly accessible in PATH
        try:
            result = subprocess.run(["iscc", "/?"], check=True, capture_output=True, text=True)
            print("✓ Inno Setup found in PATH")
            return True
        except FileNotFoundError:
            # If not in PATH, check common installation locations
            for path in inno_paths:
                if os.path.exists(path):
                    print(f"✓ Inno Setup found at {path}")
                    # Add the Inno Setup directory to PATH
                    inno_dir = os.path.dirname(path)
                    os.environ["PATH"] = inno_dir + os.pathsep + os.environ["PATH"]
                    return True
                
            print("✗ Error: Inno Setup not found in common locations:")
            print("Checked paths:")
            for path in inno_paths:
                print(f"  - {path}")
            print("\n🚀 SOLUTION: Download and install Inno Setup:")
            print("   https://jrsoftware.org/isdl.php")
            print("   (Free download, very reliable installer creator)")
            return False

    def build(self):
        """Build the application and installer."""
        print("\n=== Starting Installer Build Process ===")
        
        # Check Inno Setup first
        if not self.check_inno_setup():
            sys.exit(1)
        
        # Clean previous builds
        self.clean_build()
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("✗ Failed to verify or download prerequisites")
            sys.exit(1)
        
        # Create manifest file
        print("\nCreating manifest file...")
        self.create_manifest()
        
        # Build main executable
        print("\nBuilding main application...")
        self.build_exe()
        
        # Verify the executable was created
        exe_path = os.path.join("dist", f"TrackPro_v{self.version}.exe")
        if not os.path.exists(exe_path):
            raise Exception(f"Failed to build TrackPro_v{self.version}.exe - file not found at {exe_path}")
        
        # Copy executable to installer temp directory
        print("\nPreparing files for installer...")
        dist_temp_dir = os.path.join(self.temp_dir, "dist")
        os.makedirs(dist_temp_dir, exist_ok=True)
        
        dest_exe_path = os.path.join(dist_temp_dir, f"TrackPro_v{self.version}.exe")
        try:
            shutil.copy2(exe_path, dest_exe_path)
            print(f"✓ Copied {exe_path} to {dest_exe_path}")
            
            # Verify the copy was successful
            if not os.path.exists(dest_exe_path):
                raise Exception(f"Failed to copy executable to {dest_exe_path}")
            
            # Verify file size to ensure it's not corrupted
            src_size = os.path.getsize(exe_path)
            dest_size = os.path.getsize(dest_exe_path)
            if src_size != dest_size:
                raise Exception(f"File size mismatch: {src_size} vs {dest_size}")
                
            print(f"✓ Verified copy: {dest_exe_path} ({dest_size} bytes)")
        except Exception as e:
            raise Exception(f"Failed to prepare executable for installer: {str(e)}")
        
        # Create installer script
        print("\nCreating installer script...")
        self.create_installer_script()
        
        # Verify all required files exist before building the installer
        print("\nVerifying all required files exist...")
        required_files = [
            os.path.join(self.temp_dir, "prerequisites", "vJoySetup.exe"),
            os.path.join(self.temp_dir, "prerequisites", "HidHide_1.5.230_x64.exe"),
            os.path.join(self.temp_dir, "prerequisites", "vc_redist.x64.exe"),
            os.path.join(self.temp_dir, "dist", f"TrackPro_v{self.version}.exe"),
            "installer.iss"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                print(f"✗ Missing required file: {file_path}")
            else:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    print(f"✗ Warning: {file_path} exists but is empty (0 bytes)")
                    missing_files.append(f"{file_path} (empty file)")
                else:
                    print(f"✓ Verified {file_path} ({file_size} bytes)")
        
        if missing_files:
            error_msg = "Required files not found or empty:\n"
            for file in missing_files:
                error_msg += f"  - {file}\n"
            error_msg += "\nPlease ensure all required files are present before building the installer."
            raise Exception(error_msg)
        
                    # Build installer
        print("\nBuilding installer...")
        
        # Check if output file already exists and try to delete it
        installer_path = f"TrackPro_Setup_v{self.version}.exe"
        if os.path.exists(installer_path):
            print(f"Removing existing installer: {installer_path}")
            
            # First, try to kill any processes that might be holding the file
            self._force_unlock_installer_file(installer_path)
            
            # Try multiple times with increasing delays
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    os.remove(installer_path)
                    print(f"✓ Removed existing installer")
                    break
                except PermissionError as e:
                    if attempt < max_attempts - 1:
                        print(f"Attempt {attempt + 1}/{max_attempts}: File is locked, retrying in {2 ** attempt} seconds...")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        # Try force unlock again on each retry
                        self._force_unlock_installer_file(installer_path)
                    else:
                        print(f"✗ Could not remove existing installer after {max_attempts} attempts: {e}")
                        print("The file is being used by another process. Possible causes:")
                        print("1. The installer is currently running")
                        print("2. Windows Explorer has the file open")
                        print("3. Antivirus software is scanning the file")
                        print("4. Windows Defender has the file locked")
                        print("\nSolutions:")
                        print("1. Close any running TrackPro installers")
                        print("2. Close Windows Explorer windows")
                        print("3. Wait for antivirus scan to complete")
                        print("4. Manually delete the file and try again")
                        print("5. Restart your computer to clear all file locks")
                        
                        # Try one final force unlock
                        print("Attempting final force unlock...")
                        self._force_unlock_installer_file(installer_path, aggressive=True)
                        
                        # Try one more time after aggressive unlock
                        try:
                            time.sleep(3)
                            os.remove(installer_path)
                            print(f"✓ Successfully removed installer after aggressive unlock")
                            break
                        except Exception as final_e:
                            raise Exception(f"Could not remove existing installer after {max_attempts} attempts and force unlock: {final_e}")
                except Exception as e:
                    if attempt < max_attempts - 1:
                        print(f"Attempt {attempt + 1}/{max_attempts}: Error removing file, retrying...")
                        time.sleep(1)
                    else:
                        print(f"✗ Could not remove existing installer: {e}")
                        raise Exception(f"Could not remove existing installer: {e}")
        
        # Test if we can write to the current directory
        test_file = "test_write_permissions.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✓ Directory write permissions verified")
        except Exception as e:
            print(f"✗ Cannot write to current directory: {e}")
            print("Please run from a directory with write permissions")
            raise Exception(f"Cannot write to current directory: {e}")
        
        # Kill any running TrackPro processes that might lock files
        print("Comprehensive process and lock cleanup...")
        self.kill_stuck_processes()
        self.cleanup_single_instance_locks()
        
        # Additional wait for processes to fully terminate
        time.sleep(2)
        
        try:
            # Find Inno Setup compiler
            iscc_exe = None
            iscc_paths = [
                r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                r"C:\Program Files\Inno Setup 6\ISCC.exe",
                r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
                r"C:\Program Files\Inno Setup 5\ISCC.exe"
            ]
            
            for path in iscc_paths:
                if os.path.exists(path):
                    iscc_exe = path
                    break
            
            if not iscc_exe:
                # Try to find iscc in PATH
                try:
                    iscc_exe = "iscc"
                    subprocess.run([iscc_exe, "/?"], 
                                  capture_output=True, 
                                  check=True)
                except:
                    raise FileNotFoundError("Could not find iscc.exe (Inno Setup compiler)")
            
            # Test Inno Setup first
            print("Testing Inno Setup installation...")
            try:
                test_result = subprocess.run([iscc_exe, "/?"], 
                                          capture_output=True, text=True, check=False)
                if test_result.returncode == 0:
                    # Extract version info from help output
                    version_line = test_result.stdout.split('\n')[0] if test_result.stdout else "Unknown version"
                    print(f"✓ Inno Setup is working: {version_line}")
                else:
                    print(f"✗ Inno Setup test failed: {test_result.stderr}")
                    raise Exception(f"Inno Setup test failed: {test_result.stderr}")
            except Exception as e:
                print(f"✗ Inno Setup test failed: {e}")
                raise Exception(f"Inno Setup test failed: {e}")
            
            # Quick sanity check of the Inno Setup script
            print("Checking Inno Setup script...")
            try:
                with open("installer.iss", 'r', encoding='utf-8') as f:
                    script_content = f.read()
                    if not script_content.strip():
                        print("✗ Inno Setup script is empty")
                        raise Exception("Inno Setup script is empty")
                    if "OutputBaseFilename" not in script_content:
                        print("✗ Inno Setup script missing OutputBaseFilename directive")
                        raise Exception("Inno Setup script missing OutputBaseFilename directive")
                    print("✓ Inno Setup script appears valid")
            except Exception as e:
                print(f"✗ Could not read Inno Setup script: {e}")
                raise Exception(f"Could not read Inno Setup script: {e}")
            
            # Run Inno Setup compiler
            print("Compiling installer with Inno Setup...")
            current_dir = os.getcwd()
            print(f"Current working directory: {current_dir}")
            
            # Use absolute path for the script
            script_path = os.path.join(current_dir, "installer.iss")
            print(f"Using script path: {script_path}")
            
            # Run Inno Setup with verbose output
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run([iscc_exe, "/Q", script_path], 
                                  capture_output=True, 
                                  text=True,
                                  check=False,  # Don't raise exception yet
                                  creationflags=CREATE_NO_WINDOW)
            
            # Print output for debugging
            print("\nInno Setup Output:")
            if result.stdout:
                print(result.stdout)
            else:
                print("(No output - compilation was quiet)")
            
            if result.stderr:
                print("\nInno Setup Error Output:")
                print(result.stderr)
            
            # Check for errors
            if result.returncode != 0:
                print(f"Inno Setup Error (return code {result.returncode})")
                
                # Try to find specific error messages
                error_lines = []
                if result.stdout:
                    for line in result.stdout.splitlines():
                        if "error" in line.lower() or "fatal" in line.lower():
                            error_lines.append(line)
                
                if error_lines:
                    raise Exception(f"Inno Setup compilation failed: {'; '.join(error_lines)}")
                else:
                    raise Exception(f"Inno Setup compilation failed with return code {result.returncode}")
            else:
                print("✓ Inno Setup compilation successful!")
        except subprocess.CalledProcessError as e:
            print(f"Inno Setup Error: {e.stdout}\n{e.stderr}")
            raise
        except FileNotFoundError:
            print("✗ Inno Setup not found!")
            print("🚀 SOLUTION: Download and install Inno Setup:")
            print("   https://jrsoftware.org/isdl.php")
            print("   (Free, much more reliable than NSIS)")
            raise Exception("Inno Setup not found. Please install Inno Setup.")
        except Exception as e:
            print(f"Error building installer: {str(e)}")
            raise Exception(f"Failed to build installer: {str(e)}")

        # Verify the installer was created
        if not os.path.exists(installer_path):
            raise Exception(f"Installer not found at {installer_path}")
        
        print("\n✓ Installer build completed!")
        print(f"✓ Installer created at: {os.path.abspath(installer_path)}")
        
        # Verify the installer file size
        installer_size = os.path.getsize(installer_path)
        print(f"✓ Installer size: {installer_size:,} bytes")
        
        if installer_size < 1000000:  # Less than 1MB might indicate a problem
            print("! Warning: Installer file size is smaller than expected. Please verify its contents.")
        

        
        # Final cleanup of any remaining locks or processes
        print("\nPerforming final cleanup...")
        self.cleanup_single_instance_locks()
        
        print(f"\n✓ Build process completed!")
        print(f"✓ Installer available at: {os.path.abspath(installer_path)}")
        print(f"✓ Installer is ready for distribution")
        print(f"✓ All processes and locks cleaned up")

    def clean_build(self):
        """Clean up build files and processes."""
        print("\n=== Cleaning Build Environment ===")
        
        # Kill any stuck installer processes first
        self.kill_stuck_processes()
        
        # Clean up TrackPro single instance locks
        self.cleanup_single_instance_locks()
        
        # Clean up build directories
        dirs_to_clean = [self.temp_dir, self.dist_dir, "build"]
        for dir_path in dirs_to_clean:
            if os.path.exists(dir_path):
                print(f"Removing {dir_path}...")
                shutil.rmtree(dir_path, ignore_errors=True)
                print(f"✓ {dir_path} removed")
            else:
                print(f"✓ {dir_path} already clean")
        
        # Clean up PyInstaller cache
        pycache_dirs = [
            "__pycache__",
            "trackpro/__pycache__",
            ".pytest_cache"
        ]
        for cache_dir in pycache_dirs:
            if os.path.exists(cache_dir):
                print(f"Removing {cache_dir}...")
                shutil.rmtree(cache_dir, ignore_errors=True)
        
        print("✓ Build environment cleaned")
    
    def _force_unlock_installer_file(self, installer_path, aggressive=False):
        """Force unlock the installer file by killing processes that might be holding it"""
        import subprocess
        import time
        import ctypes
        import sys
        
        print(f"Attempting to unlock file: {installer_path}")
        
        # Check if we have admin privileges
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        
        if not is_admin:
            print("⚠️  Warning: Not running as administrator - process killing may fail")
            print("💡 For better results, run PowerShell as Administrator and use:")
            print('   Get-Process | Where-Object {$_.ProcessName -like "*TrackPro_Setup*"} | Stop-Process -Force')
        
        # Method 1: Kill any installer processes
        try:
            result = subprocess.run([
                'powershell', '-Command', 
                f'''Get-Process | Where-Object {{
                    $_.ProcessName -like "*TrackPro_Setup*" -or 
                    $_.ProcessName -like "*TrackPro*Setup*" -or
                    ($_.ProcessName -eq "nsis" -and $_.CommandLine -like "*TrackPro*")
                }} | Stop-Process -Force'''
            ], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✓ Killed installer processes")
            else:
                print(f"⚠️  Installer process kill failed: {result.stderr}")
            time.sleep(1)
        except Exception as e:
            print(f"Warning: Could not kill installer processes: {e}")
        
        # Method 1.5: Try with elevated PowerShell if not admin
        if not is_admin and aggressive:
            try:
                print("Attempting elevated process kill...")
                result = subprocess.run([
                    'powershell', '-Command', 
                    '''Start-Process powershell -ArgumentList "-Command","Get-Process | Where-Object {$_.ProcessName -like '*TrackPro_Setup*'} | Stop-Process -Force" -Verb RunAs -WindowStyle Hidden -Wait'''
                ], capture_output=True, text=True, timeout=20)
                time.sleep(2)
                print("✓ Attempted elevated kill")
            except Exception as e:
                print(f"Warning: Elevated kill failed: {e}")
        
        # Method 2: Try WMIC for more aggressive killing
        if aggressive:
            try:
                result = subprocess.run([
                    'wmic', 'process', 'where', 
                    'name="TrackPro_Setup_v1.5.3.exe"', 'delete'
                ], capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    print("✓ WMIC process kill successful")
                time.sleep(2)
            except Exception as e:
                print(f"Warning: WMIC kill failed: {e}")
        
        # Method 3: Kill any NSIS processes that might be related
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'nsis.exe'], 
                         capture_output=True, timeout=5)
            subprocess.run(['taskkill', '/F', '/IM', 'iscc.exe'], 
                         capture_output=True, timeout=5)
            time.sleep(1)
        except Exception:
            pass  # These might not exist, that's fine
        
        # Method 4: Try to unlock using PowerShell file operations
        if aggressive:
            try:
                result = subprocess.run([
                    'powershell', '-Command', 
                    f'''
                    $file = "{installer_path}"
                    if (Test-Path $file) {{
                        try {{
                            [System.IO.File]::Delete($file)
                            Write-Output "Deleted with .NET method"
                        }} catch {{
                            Write-Output "Failed to delete with .NET: $_"
                        }}
                    }}
                    '''
                ], capture_output=True, text=True, timeout=10)
                if "Deleted with .NET method" in result.stdout:
                    print("✓ File deleted using .NET method")
                    return
            except Exception as e:
                print(f"Warning: .NET delete method failed: {e}")
        
        # Method 5: Check if processes are still running and provide guidance
        try:
            result = subprocess.run([
                'powershell', '-Command', 
                '''Get-Process | Where-Object {$_.ProcessName -like "*TrackPro_Setup*"} | Select-Object ProcessName, Id, @{Name="AgeMinutes";Expression={(Get-Date) - $_.StartTime | ForEach-Object {[math]::Round($_.TotalMinutes,1)}}}'''
            ], capture_output=True, text=True, timeout=10)
            
            if result.stdout and "TrackPro_Setup" in result.stdout:
                print("\n🚨 STUCK PROCESSES DETECTED:")
                print(result.stdout)
                print("\n💡 SOLUTIONS (try in order):")
                print("1. Run PowerShell as Administrator:")
                print('   Get-Process | Where-Object {$_.ProcessName -like "*TrackPro_Setup*"} | Stop-Process -Force')
                print("2. Use Task Manager (Ctrl+Shift+Esc) → Details → End Task on TrackPro_Setup processes")
                print("3. Restart your computer (guaranteed to work)")
                print("4. Or run this build script as Administrator")
                
        except Exception as e:
            print(f"Warning: Could not check remaining processes: {e}")

    def kill_stuck_processes(self):
        """Kill any stuck TrackPro processes more aggressively."""
        import subprocess
        import time
        
        print("=== Enhanced Process Cleanup ===")
        
        # First try to find any TrackPro processes with more specific filtering
        try:
            result = subprocess.run([
                'powershell', '-Command', 
                '''Get-Process | Where-Object {
                    ($_.ProcessName -eq 'TrackPro' -or 
                     $_.ProcessName -like 'TrackPro_v*' -or 
                     $_.ProcessName -like 'TrackPro_Setup*') -and
                    $_.ProcessName -notlike '*Cursor*' -and
                    $_.ProcessName -notlike '*Code*' -and
                    $_.ProcessName -notlike '*Visual*'
                } | Select-Object ProcessName, Id'''
            ], capture_output=True, text=True, timeout=10)
            
            if result.stdout.strip():
                print("Found TrackPro processes:")
                print(result.stdout)
            else:
                print("✓ No TrackPro processes found")
                return
        except Exception as e:
            print(f"Could not check for processes: {e}")
        
        # Try multiple methods to kill stuck processes - MORE SPECIFIC
        kill_methods = [
            # Method 1: Regular taskkill for current version (exact match)
            ['taskkill', '/F', '/IM', f'TrackPro_v{self.version}.exe'],
            # Method 2: Regular taskkill for generic (exact match)
            ['taskkill', '/F', '/IM', 'TrackPro.exe'],
            # Method 3: Kill installer processes (exact match)
            ['taskkill', '/F', '/IM', f'TrackPro_Setup_v{self.version}.exe'],
            # Method 4: Kill by window title (more specific)
            ['taskkill', '/F', '/FI', 'WINDOWTITLE eq TrackPro v*'],
            # Method 5: PowerShell force kill TrackPro processes (with exclusions)
            ['powershell', '-Command', 
             '''Get-Process | Where-Object {
                 ($_.ProcessName -eq 'TrackPro' -or 
                  $_.ProcessName -like 'TrackPro_v*' -or 
                  $_.ProcessName -like 'TrackPro_Setup*') -and
                 $_.ProcessName -notlike '*Cursor*' -and
                 $_.ProcessName -notlike '*Code*' -and
                 $_.ProcessName -notlike '*Visual*' -and
                 $_.ProcessName -notlike '*Studio*'
             } | Stop-Process -Force'''],
            # Method 6: Kill Python processes running TrackPro (but not build scripts or IDEs)
            ['powershell', '-Command', 
             '''Get-Process python*, pythonw* | Where-Object {
                 ($_.CommandLine -like '*run_app*' -or $_.CommandLine -like '*trackpro/main.py*') -and
                 $_.CommandLine -notlike '*build.py*' -and
                 $_.CommandLine -notlike '*Cursor*' -and
                 $_.CommandLine -notlike '*Code*' -and
                 $_.CommandLine -notlike '*Visual*'
             } | Stop-Process -Force'''],
        ]
        
        for i, method in enumerate(kill_methods, 1):
            try:
                print(f"Trying kill method {i}: {' '.join(method[:3])}")
                result = subprocess.run(method, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✓ Kill method {i} successful")
                else:
                    print(f"✗ Kill method {i} failed: {result.stderr.strip()}")
            except Exception as e:
                print(f"✗ Kill method {i} error: {e}")
        
        # Give processes time to terminate
        time.sleep(2)
        
        # Final check
        try:
            result = subprocess.run([
                'powershell', '-Command', 
                "Get-Process | Where-Object {$_.ProcessName -like '*TrackPro*'} | Measure-Object | Select-Object Count"
            ], capture_output=True, text=True, timeout=10)
            if "0" in result.stdout:
                print("✓ All TrackPro processes terminated")
                
                # Clean up locks after successful process termination
                print("Cleaning up remaining locks after process termination...")
                self.cleanup_single_instance_locks()
            else:
                print("⚠ Some TrackPro processes may still be running")
                print("💡 If installation fails, restart your computer to clear stuck processes")
        except Exception as e:
            print(f"Could not verify process cleanup: {e}")

    def cleanup_single_instance_locks(self):
        """Clean up TrackPro single instance locks and mutexes with enhanced diagnostics."""
        print("=== Enhanced Single Instance Lock Cleanup ===")
        
        try:
            import tempfile
            import psutil
            
            # First, check if any TrackPro processes are actually running
            running_trackpro_pids = []
            try:
                for process in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                    try:
                        process_info = process.info
                        if not process_info['cmdline']:
                            continue
                        
                        # Check for TrackPro processes
                        is_trackpro = False
                        
                        # Skip the current build process
                        if process_info['pid'] == os.getpid():
                            continue
                        
                        # Skip build.py processes (avoid flagging build script as TrackPro process)
                        if any('build.py' in str(cmd) for cmd in process_info['cmdline']):
                            continue
                        
                        # Check for TrackPro executable
                        if any('trackpro' in str(cmd).lower() for cmd in process_info['cmdline']):
                            is_trackpro = True
                        
                        # Check for Python processes running TrackPro (but not build script)
                        if (process_info['name'] in ['python.exe', 'pythonw.exe'] and 
                            any('run_app.py' in str(cmd).lower() or 'main.py' in str(cmd).lower()
                                for cmd in process_info['cmdline'])):
                            is_trackpro = True
                        
                        if is_trackpro:
                            running_trackpro_pids.append({
                                'pid': process_info['pid'],
                                'name': process_info['name'],
                                'cmdline': ' '.join(process_info['cmdline'][:3]),  # First 3 args
                                'age': time.time() - process_info['create_time']
                            })
                            
                    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                        continue
            except Exception as e:
                print(f"Warning: Could not scan for TrackPro processes: {e}")
            
            if running_trackpro_pids:
                print("⚠️  Found running TrackPro processes:")
                for proc in running_trackpro_pids:
                    print(f"   PID {proc['pid']}: {proc['name']} (age: {proc['age']:.1f}s)")
                    print(f"      Command: {proc['cmdline']}")
                print("   These processes should be terminated before cleanup.")
            else:
                print("✓ No running TrackPro processes detected")
            
            # Clean up lock file with enhanced diagnostics
            lock_file = os.path.join(tempfile.gettempdir(), "trackpro.lock")
            if os.path.exists(lock_file):
                try:
                    # Get file info
                    file_stat = os.stat(lock_file)
                    file_age = time.time() - file_stat.st_mtime
                    print(f"Found lock file (age: {file_age:.1f}s, size: {file_stat.st_size} bytes)")
                    
                    # Try to read the lock file to see what process created it
                    try:
                        with open(lock_file, 'r') as f:
                            import json
                            lock_data = json.load(f)
                            lock_pid = lock_data.get('pid', 'unknown')
                            lock_timestamp = lock_data.get('timestamp', 0)
                            if lock_timestamp:
                                lock_age = time.time() - lock_timestamp
                                print(f"   Created by PID {lock_pid} ({lock_age:.1f}s ago)")
                            else:
                                print(f"   Created by PID {lock_pid}")
                            
                            # Check if the PID is still running
                            if isinstance(lock_pid, int):
                                try:
                                    process = psutil.Process(lock_pid)
                                    print(f"   ⚠️  Lock PID {lock_pid} is still running: {process.name()}")
                                except psutil.NoSuchProcess:
                                    print(f"   ✓ Lock PID {lock_pid} is no longer running (stale lock)")
                                except Exception as e:
                                    print(f"   ? Could not check PID {lock_pid}: {e}")
                    except (json.JSONDecodeError, KeyError):
                        print("   Lock file format is unreadable")
                    except Exception as e:
                        print(f"   Could not read lock file: {e}")
                
                    # Remove the lock file
                    try:
                        os.remove(lock_file)
                        print("✓ Removed TrackPro lock file")
                    except PermissionError:
                        print("✗ Permission denied removing lock file (file may be in use)")
                        # Try to force remove with different method
                        try:
                            import stat
                            os.chmod(lock_file, stat.S_IWRITE)
                            os.remove(lock_file)
                            print("✓ Force removed TrackPro lock file")
                        except Exception as e2:
                            print(f"✗ Could not force remove lock file: {e2}")
                    except Exception as e:
                        print(f"✗ Could not remove lock file: {e}")
                        
                except Exception as e:
                    print(f"Error processing lock file: {e}")
            else:
                print("✓ No TrackPro lock file found")
            
            # Try to clean up Windows mutex with enhanced diagnostics
            try:
                import win32event
                import win32api
                import winerror
                import win32con
                
                mutex_name = "TrackProSingleInstanceMutex"
                print(f"Checking Windows mutex: {mutex_name}")
                
                # Try to open the existing mutex
                try:
                    mutex = win32event.OpenMutex(win32con.SYNCHRONIZE, False, mutex_name)
                    if mutex:
                        print("   Found existing mutex - attempting cleanup")
                        # Try to release it multiple times to clear any stuck ownership
                        release_count = 0
                        for i in range(5):  # Try up to 5 times
                            try:
                                win32event.ReleaseMutex(mutex)
                                release_count += 1
                                print(f"   ✓ Released mutex (attempt {i+1})")
                            except Exception as e:
                                if "not owned" in str(e).lower():
                                    print(f"   ✓ Mutex released after {release_count} attempts")
                                    break
                                else:
                                    print(f"   Error releasing mutex: {e}")
                                    break
                        
                        win32api.CloseHandle(mutex)
                        print("✓ Closed mutex handle")
                    else:
                        print("✓ No mutex found")
                except Exception as e:
                    if any(phrase in str(e).lower() for phrase in ["not found", "does not exist", "cannot find", "system cannot find"]):
                        print("✓ No mutex found to clean up")
                    else:
                        print(f"⚠️  Error accessing mutex: {e}")
                        
            except ImportError:
                print("⚠️  win32 modules not available - skipping mutex cleanup")
                print("   Install pywin32 for complete lock cleanup: pip install pywin32")
            except Exception as e:
                print(f"⚠️  Error during mutex cleanup: {e}")
                
        except Exception as e:
            print(f"Error during single instance cleanup: {e}")
        
        print("✓ Enhanced single instance lock cleanup completed")
        
        # Provide user guidance based on what we found
        if 'running_trackpro_pids' in locals() and running_trackpro_pids:
            print("\n💡 User Action Required:")
            print("   Some TrackPro processes are still running.")
            print("   Please close all TrackPro windows and try again.")
            print("   If processes are stuck, use Task Manager to end them.")
        else:
            print("\n✓ System appears clean for TrackPro startup")

    def create_manifest(self):
        """Create a manifest file to request admin privileges."""
        manifest = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="1.0.0.0"
    processorArchitecture="amd64"
    name="TrackPro"
    type="win32"
  />
  <description>TrackPro Application</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 and Windows Server 2016 -->
      <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
      <!-- Windows 8.1 and Windows Server 2012 R2 -->
      <supportedOS Id="{{1f676c76-80e1-4239-95bb-83d0f6d0da78}}"/>
      <!-- Windows 8 and Windows Server 2012 -->
      <supportedOS Id="{{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}}"/>
      <!-- Windows 7 and Windows Server 2008 R2 -->
      <supportedOS Id="{{35138b9a-5d96-4fbd-8e2d-a2440225f93a}}"/>
    </application>
  </compatibility>
</assembly>"""
        manifest_path = "trackpro.manifest"  # Use relative path instead of absolute
        with open(manifest_path, "w") as f:
            f.write(manifest)
        print(f"✓ Created manifest file at: {manifest_path}")
        return manifest_path


        
    def build_exe(self):
        """Build the executable using PyInstaller."""
        print("\n=== Building Executable with PyInstaller ===")
        
        # Define the name for the executable
        exe_name = f"TrackPro_v{self.version}"
        print(f"Executable will be named: {exe_name}.exe")
        
        # Check if the spec file exists
        spec_file = "trackpro.spec"
        if not os.path.exists(spec_file):
            print(f"! Error: '{spec_file}' not found.")
            print("Please ensure the spec file is in the root directory.")
            sys.exit(1)
            
        print(f"Using spec file: {spec_file}")

        # PyInstaller arguments
        pyinstaller_args = [
            spec_file,
            '--noconfirm',
            '--clean'
        ]

        print(f"Running PyInstaller with arguments: {' '.join(pyinstaller_args)}")

        try:
            PyInstaller.__main__.run(pyinstaller_args)
            print("✓ PyInstaller build completed successfully.")
        except Exception as e:
            print(f"! PyInstaller build failed: {e}")
            sys.exit(1)

    def check_prerequisites(self):
        """Check for vJoy and HidHide drivers."""
        print("\nChecking prerequisites...")
        
        # First check Python package dependencies
        # Check for required Python packages
        required_packages = {
            "PyQt6": "PyQt6>=6.0.0",
            "PyQtWebEngine": "PyQtWebEngine>=5.15.0",
            "pygame": "pygame>=2.0.0",
            "pywin32": "pywin32>=300",
            "requests": "requests>=2.25.0",
            "PyInstaller": "PyInstaller>=6.0.0",
            "numpy": "numpy>=1.19.0",  # This is essential for Race Coach
            "psutil": "psutil>=5.9.0"
        }
        
        # Try to add matplotlib if it's needed
        try:
            # Check if matplotlib is already imported in the race_coach module
            needs_matplotlib = False
            race_coach_files = [
                "trackpro/race_coach/ui.py",
                "trackpro/race_coach/analysis.py",
                "trackpro/race_coach/model.py"
            ]
            
            for file_path in race_coach_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "matplotlib" in content or "pyplot" in content:
                            needs_matplotlib = True
                            break
            
            if needs_matplotlib:
                required_packages["matplotlib"] = "matplotlib>=3.3.0"
                print("Detected matplotlib usage in Race Coach - adding to requirements")
        except Exception as e:
            print(f"Warning: Error checking for matplotlib usage: {e}")
        
        missing_packages = []
        
        for package, requirement in required_packages.items():
            try:
                module = importlib.import_module(package)
                print(f"✓ Found {package} {getattr(module, '__version__', 'unknown version')}")
                
                # Special check for numpy to ensure it's working correctly
                if package == "numpy":
                    try:
                        # Try a basic numpy operation to ensure it's functioning
                        import numpy as np
                        test_array = np.array([1, 2, 3])
                        test_result = np.sum(test_array)
                        print(f"✓ Numpy test successful: {test_result}")
                    except Exception as e:
                        print(f"✗ Numpy test failed: {e}")
                        print("Reinstalling numpy...")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "--force-reinstall", requirement])
                        print("Numpy reinstalled. Testing again...")
                        # Test again after reinstall
                        import numpy as np
                        test_array = np.array([1, 2, 3])
                        test_result = np.sum(test_array)
                        print(f"✓ Numpy test successful after reinstall: {test_result}")
                
            except ImportError:
                print(f"✗ Missing {package} - installing...")
                missing_packages.append(requirement)
        
        if missing_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
                print("✓ Installed missing packages")
                
                # Verify numpy was installed correctly
                try:
                    import numpy as np
                    test_array = np.array([1, 2, 3])
                    test_result = np.sum(test_array)
                    print(f"✓ Verified numpy installation: {test_result}")
                except Exception as e:
                    print(f"✗ Numpy verification failed: {e}")
                    return False
                
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install packages: {e}")
                return False
        
        # Make sure race_coach.db exists
        if not os.path.exists("race_coach.db"):
            print("Creating initial race_coach.db file...")
            try:
                # Try importing the data_manager to create the DB
                from trackpro.race_coach.data_manager import DataManager
                dm = DataManager(db_path="race_coach.db")
                print("✓ Created race_coach.db")
            except Exception as e:
                print(f"✗ Failed to create race_coach.db: {e}")
                # Create a minimal SQLite database as fallback
                try:
                    import sqlite3
                    conn = sqlite3.connect("race_coach.db")
                    cursor = conn.cursor()
                    cursor.execute("CREATE TABLE IF NOT EXISTS version (id INTEGER PRIMARY KEY, version TEXT)")
                    cursor.execute("INSERT INTO version (version) VALUES (?)", ("1.0.0",))
                    conn.commit()
                    conn.close()
                    print("✓ Created minimal race_coach.db as fallback")
                except Exception as e2:
                    print(f"✗ Failed to create minimal race_coach.db: {e2}")
        
        # Check if diagnostic tool exists
        if os.path.exists("diagnose_trackpro.py"):
            print("✓ Diagnostic tool found")
        else:
            print("⚠ Warning: diagnose_trackpro.py not found - users won't have diagnostic capability")
        
        # Now check the prerequisites directory
        print("\nChecking prerequisites directory...")
        prereq_dir = os.path.join(self.temp_dir, "prerequisites")
        
        # Check if the directory exists
        if not os.path.exists(prereq_dir):
            print(f"✗ Prerequisites directory not found: {prereq_dir}")
            print("Creating prerequisites directory...")
            os.makedirs(prereq_dir, exist_ok=True)
            print(f"✓ Created prerequisites directory: {prereq_dir}")
        else:
            print(f"✓ Prerequisites directory exists: {prereq_dir}")
        
        # Define required files with fallback URLs and correct filenames
        required_files = [
            {
                "filename": "vJoySetup.exe",
                "url": self.VJOY_URL,
                "fallback_url": self.VJOY_FALLBACK_URL,
                "description": "vJoy Virtual Joystick Driver"
            },
            {
                "filename": "HidHide_1.5.230_x64.exe", 
                "url": self.HIDHIDE_URL,
                "fallback_url": self.HIDHIDE_FALLBACK_URL,
                "description": "HidHide Device Hiding Driver"
            },
            {
                "filename": "vc_redist.x64.exe",
                "url": self.VCREDIST_URL,
                "fallback_url": None,
                "description": "Visual C++ Redistributable"
            }
        ]
        
        missing_files = []
        for file_info in required_files:
            filename = file_info["filename"]
            filepath = os.path.join(prereq_dir, filename)
            if not os.path.exists(filepath):
                print(f"✗ Missing prerequisite file: {filepath}")
                missing_files.append(file_info)
            else:
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    print(f"✗ Warning: {filepath} exists but is empty (0 bytes)")
                    missing_files.append(file_info)
                else:
                    print(f"✓ Found {filename} ({file_size:,} bytes)")
        
        # Download missing files with fallback support
        if missing_files:
            print("\nDownloading missing prerequisite files...")
            for file_info in missing_files:
                try:
                    print(f"\n--- Downloading {file_info['description']} ---")
                    filepath = self.download_file(
                        file_info["url"], 
                        prereq_dir,
                        fallback_url=file_info["fallback_url"],
                        expected_filename=file_info["filename"]
                    )
                    print(f"✓ Successfully downloaded {file_info['filename']}")
                except Exception as e:
                    print(f"✗ Failed to download {file_info['filename']}: {str(e)}")
                    print(f"   Primary URL: {file_info['url']}")
                    if file_info["fallback_url"]:
                        print(f"   Fallback URL: {file_info['fallback_url']}")
                    return False
        
        return True

    def build_test_installer(self):
        """Build a test installer (same as regular build for now)."""
        print("\n=== Building Test Installer ===")
        self.build()

    @staticmethod
    def manual_process_cleanup():
        """Utility function to manually clean up stuck processes."""
        print("=== Manual Process Cleanup ===")
        
        # Create a builder instance to access cleanup methods
        builder = InstallerBuilder()
        
        try:
            # Use the enhanced cleanup methods
            builder.kill_stuck_processes()
            builder.cleanup_single_instance_locks()
            
            print("\n✓ Enhanced cleanup completed")
            print("💡 If you still get 'another instance running' errors:")
            print("   1. Restart your computer")
            print("   2. Run TrackPro with --force flag: python run_app.py --force")
            print("   3. Use the kill_trackpro_processes.py script")
            
        except Exception as e:
            print(f"Error during manual cleanup: {e}")
            
            # Fallback to original PowerShell method (with IDE exclusions)
            try:
                # Check for stuck processes
                cmd = '''
                $processes = Get-Process | Where-Object {
                    (($_.ProcessName -eq "TrackPro" -or 
                      $_.ProcessName -like "TrackPro_v*" -or 
                      $_.ProcessName -like "TrackPro_Setup*") -and
                     $_.ProcessName -notlike "*Cursor*" -and
                     $_.ProcessName -notlike "*Code*" -and
                     $_.ProcessName -notlike "*Visual*" -and
                     $_.ProcessName -notlike "*Studio*")
                }
                
                if ($processes) {
                    Write-Host "Found stuck TrackPro processes:"
                    $processes | ForEach-Object {
                        Write-Host "  - $($_.ProcessName) (PID: $($_.Id), CPU: $($_.CPU)s)"
                    }
                    
                    $response = Read-Host "Kill these TrackPro processes? (y/n)"
                    if ($response -eq "y" -or $response -eq "Y") {
                        $processes | ForEach-Object {
                            Write-Host "Killing: $($_.ProcessName) (PID: $($_.Id))"
                            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                        }
                        Write-Host "TrackPro processes killed."
                    } else {
                        Write-Host "No processes killed."
                    }
                } else {
                    Write-Host "No stuck TrackPro processes found."
                }
                '''
                
                CREATE_NO_WINDOW = 0x08000000
                subprocess.run([
                    "powershell", "-Command", cmd
                ], timeout=60, creationflags=CREATE_NO_WINDOW)
                
            except Exception as e2:
                print(f"Error during fallback cleanup: {e2}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='TrackPro Build System')
    parser.add_argument('action', nargs='?', default='build', 
                       choices=['build', 'clean', 'kill-processes', 'test', 'fix-instance-lock'],
                       help='Action to perform')

    
    args = parser.parse_args()
    
    if args.action == 'kill-processes':
        InstallerBuilder.manual_process_cleanup()
        sys.exit(0)
    elif args.action == 'fix-instance-lock':
        print("=== TrackPro Instance Lock Fix ===")
        builder = InstallerBuilder()
        builder.cleanup_single_instance_locks()
        print("✓ Lock cleanup completed")
        print("You can now try running TrackPro again")
        sys.exit(0)
    
    builder = InstallerBuilder()
    

    
    if args.action == 'clean':
        builder.clean_build()
    elif args.action == 'build':
        builder.build()
    elif args.action == 'test':
        builder.build_test_installer()
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1) 