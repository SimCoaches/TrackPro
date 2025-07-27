#!/usr/bin/env python3
"""
Optimized TrackPro Build Script - Fast & Reliable!
Features caching, optimized dependencies, and fixed installer compilation.
"""
import os
import sys
import subprocess
import shutil
import requests
import hashlib
import json
import time
from pathlib import Path

# Check Python version
if sys.version_info[:2] != (3, 11):
    print(f"❌ Need Python 3.11, got {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)

def get_file_hash(file_path):
    """Get SHA256 hash of a file for caching"""
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def download_file_with_cache(url, dest_path, expected_size=None):
    """Download file with caching - skip if already exists and valid"""
    if os.path.exists(dest_path):
        file_size = os.path.getsize(dest_path)
        if file_size > 0:
            if expected_size is None or file_size == expected_size:
                print(f"✓ {dest_path} already exists ({file_size:,} bytes) - skipping download")
                return True
            else:
                print(f"⚠️  {dest_path} size mismatch ({file_size} vs {expected_size}) - re-downloading")
    
    print(f"Downloading {dest_path}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            file_size = os.path.getsize(dest_path)
            print(f"✓ Downloaded {dest_path} ({file_size:,} bytes)")
            return True
        else:
            print(f"✗ Download failed: {dest_path} is missing or empty")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False
            
    except Exception as e:
        print(f"✗ Download failed for {dest_path}: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def check_critical_dependencies():
    """Optimized dependency check - with version verification."""
    # Note: pkg_resources is part of setuptools, which is a standard package.
    try:
        import pkg_resources
    except ImportError:
        print("✗ Could not import pkg_resources. Please ensure setuptools is installed (`pip install setuptools`)")
        return False

    critical_packages = {
        "PyQt6": "PyQt6>=6.0.0",
        "numpy": "numpy==1.26.4",
        "requests": "requests>=2.25.0",
        "PyInstaller": "PyInstaller>=6.0.0"
    }
    
    requirements_to_install = []
    for package, requirement_str in critical_packages.items():
        try:
            # Check if the installed version meets the requirement
            dist = pkg_resources.get_distribution(package)
            if dist not in pkg_resources.Requirement.parse(requirement_str):
                 print(f"⚠️  {package} version {dist.version} does not meet requirement {requirement_str}. Upgrading...")
                 requirements_to_install.append(requirement_str)
            else:
                 print(f"✓ Found {package} {dist.version}, which meets requirement {requirement_str}")

        except pkg_resources.DistributionNotFound:
            print(f"✗ Missing {package}")
            requirements_to_install.append(requirement_str)
        except Exception as e:
            print(f"Error checking {package}: {e}")
            requirements_to_install.append(requirement_str) # Install it to be safe

    if requirements_to_install:
        print(f"Installing/upgrading packages: {requirements_to_install}")
        try:
            # Use --upgrade to ensure the version is changed if it's already installed.
            # Using --no-cache-dir to avoid issues with pip's cache
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir"] + requirements_to_install
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✓ Installed/upgraded packages successfully")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install packages: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return False
            
    return True

def create_optimized_installer():
    """Create installer with optimizations and fixed compilation"""
    from trackpro import __version__
    
    # Check critical dependencies first
    print("Checking critical dependencies...")
    if not check_critical_dependencies():
        return False
    
    # Clean and create directories (but preserve cache if possible)
    print("Preparing directories...")
    if os.path.exists("installer_temp/dist"):
        shutil.rmtree("installer_temp/dist")
    os.makedirs("installer_temp/prerequisites", exist_ok=True)
    os.makedirs("installer_temp/dist", exist_ok=True)
    
    # Download prerequisites with caching and known file sizes
    prereq_dir = "installer_temp/prerequisites"
    files_to_download = [
        {
            "url": "https://github.com/njz3/vJoy/releases/download/v2.2.1.1/vJoySetup.exe",
            "fallback": "https://github.com/jshafer817/vJoy/releases/download/v2.1.9.1/vJoySetup.exe",
            "filename": "vJoySetup.exe",
            "expected_size": 11482272  # Known size
        },
        {
            "url": "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHide_1.5.230_x64.exe",
            "fallback": "https://github.com/nefarius/HidHide/releases/download/v1.5.212.0/HidHide_1.5.212_x64.exe",
            "filename": "HidHide_1.5.230_x64.exe",
            "expected_size": 8078016  # Known size
        },
        {
            "url": "https://aka.ms/vs/17/release/vc_redist.x64.exe",
            "fallback": None,
            "filename": "vc_redist.x64.exe",
            "expected_size": 25635768  # Known size
        }
    ]
    
    download_success = True
    for file_info in files_to_download:
        dest_path = os.path.join(prereq_dir, file_info["filename"])
        
        # Try cached version first
        success = download_file_with_cache(file_info["url"], dest_path, file_info.get("expected_size"))
        
        # Try fallback if primary failed
        if not success and file_info["fallback"]:
            print(f"Trying fallback URL for {file_info['filename']}...")
            success = download_file_with_cache(file_info["fallback"], dest_path, file_info.get("expected_size"))
        
        if not success:
            print(f"✗ Failed to download {file_info['filename']}")
            download_success = False
    
    if not download_success:
        print("✗ Some prerequisite downloads failed.")
        return False
    
    # Build executable with optimized PyInstaller
    print("Building executable with optimized settings...")
    
    try:
        import PyInstaller.__main__
        
        # Use optimized spec file with additional optimizations
        build_args = [
            'simple_trackpro.spec',
            '--noconfirm',
            '--clean',
            '--workpath=build',  # Explicit work path
            '--distpath=dist',   # Explicit dist path
        ]
        
        PyInstaller.__main__.run(build_args)
        print("✓ PyInstaller build completed")
        
    except Exception as e:
        print(f"❌ PyInstaller failed: {e}")
        return False
    
    # Copy exe to installer temp with verification
    exe_name = f"TrackPro_v{__version__}.exe"
    src_exe = os.path.join("dist", exe_name)
    dest_exe = os.path.join("installer_temp", "dist", exe_name)
    
    if not os.path.exists(src_exe):
        print(f"❌ Executable not found: {src_exe}")
        # Try to find any exe in dist folder
        dist_files = [f for f in os.listdir("dist") if f.endswith(".exe")]
        if dist_files:
            print(f"Found these executables in dist: {dist_files}")
            # Use the first one found
            actual_exe = dist_files[0]
            src_exe = os.path.join("dist", actual_exe)
            print(f"Using {actual_exe} instead")
        else:
            print("❌ No executable found in dist folder")
            return False
    
    try:
        shutil.copy2(src_exe, dest_exe)
        # Verify copy
        if os.path.exists(dest_exe):
            dest_size = os.path.getsize(dest_exe)
            print(f"✓ Copied {os.path.basename(dest_exe)} ({dest_size:,} bytes)")
        else:
            print(f"❌ Copy failed: {dest_exe} not found after copy")
            return False
    except Exception as e:
        print(f"❌ Failed to copy executable: {e}")
        return False
    
    # Verify all required files exist
    required_files = [
        dest_exe,
        os.path.join("installer_temp", "prerequisites", "vJoySetup.exe"),
        os.path.join("installer_temp", "prerequisites", "HidHide_1.5.230_x64.exe"),
        os.path.join("installer_temp", "prerequisites", "vc_redist.x64.exe")
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"✗ Missing required file: {file_path}")
            return False
        else:
            file_size = os.path.getsize(file_path)
            print(f"✓ Verified {os.path.basename(file_path)} ({file_size:,} bytes)")

    # Create optimized Inno Setup script with debugging and fixed HidHide
    actual_exe_name = os.path.basename(dest_exe)
    # Use string format to avoid Unicode escape issues with backslashes
    script_content = """[Setup]
AppName=TrackPro
AppVersion={version}
DefaultDirName={{localappdata}}\\TrackPro
DisableDirPage=no
AllowNoIcons=no
OutputBaseFilename=TrackPro_Setup_v{version}
OutputDir=.
PrivilegesRequired=admin
SetupLogging=yes
Compression=lzma2/max
SolidCompression=yes
CreateAppDir=yes

[Files]
Source: "installer_temp\\dist\\{exe_name}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "installer_temp\\prerequisites\\vJoySetup.exe"; DestDir: "{{tmp}}"; Flags: deleteafterinstall
Source: "installer_temp\\prerequisites\\HidHide_1.5.230_x64.exe"; DestDir: "{{tmp}}"; Flags: deleteafterinstall
Source: "installer_temp\\prerequisites\\vc_redist.x64.exe"; DestDir: "{{tmp}}"; Flags: deleteafterinstall

[Code]
procedure LogCustom(Message: String);
var
  LogFile: String;
begin
  LogFile := ExpandConstant('{{tmp}}') + '\\TrackPro_Install_Debug.txt';
  SaveStringToFile(LogFile, GetDateTimeString('hh:nn:ss', '-', ':') + ' - ' + Message + #13#10, True);
end;

procedure LogPrereqStart(Name: String);
begin
  LogCustom('STARTING: ' + Name + ' installation...');
end;

procedure LogPrereqEnd(Name: String);
begin
  LogCustom('COMPLETED: ' + Name + ' installation finished');
end;

function IsVJoyInstalled: Boolean;
begin
  // A robust check for vJoy.
  // Priority 1: Check for the driver service. This is the most reliable indicator.
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Services\\vjoy') then
  begin
    // If the service key exists, let's also check for the driver file itself.
    // An incomplete uninstall might leave the key but remove the file.
    if FileExists(ExpandConstant('{{win}}\\System32\\drivers\\vjoy.sys')) then
    begin
        LogCustom('vJoy detection: FOUND (service and driver file exist)');
        Result := True;
        Exit;
    end
    else
    begin
        LogCustom('vJoy detection: Stale service key found, but vjoy.sys is missing. Assuming NOT installed.');
    end;
  end;

  // Priority 2: Check Uninstall registry key, which is standard practice.
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{{8E31F76F-74C3-47F1-9550-68D8DA846DB0}}') then
  begin
    LogCustom('vJoy detection: FOUND (uninstall entry exists)');
    Result := True;
    Exit;
  end;

  // If all checks fail, it's not installed.
  LogCustom('vJoy detection: NOT FOUND (will need to install)');
  Result := False;
end;

function IsHidHideInstalled: Boolean;
begin
  // A robust check for HidHide.
  // Priority 1: Check for the driver service.
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Services\\HidHide') then
  begin
    // Also check for the driver file.
    if FileExists(ExpandConstant('{{win}}\\System32\\drivers\\HidHide.sys')) then
    begin
        LogCustom('HidHide detection: FOUND (service and driver file exist)');
        Result := True;
        Exit;
    end
    else
    begin
        LogCustom('HidHide detection: Stale service key found, but HidHide.sys is missing. Assuming NOT installed.');
    end;
  end;

  // Priority 2: Check Uninstall registry key.
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{{0C713C5A-F072-4BD7-A714-0E0CC6BD5497}}') then
  begin
    LogCustom('HidHide detection: FOUND (uninstall entry exists)');
    Result := True;
    Exit;
  end;
  
  LogCustom('HidHide detection: NOT FOUND (will need to install)');
  Result := False;
end;

function IsVCRedistInstalled: Boolean;
var
  Value: String;
begin
  // Check for Visual C++ 2015-2022 Redistributable (x64)
  Result := RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\X64', 'Version', Value) and
           (Value >= '14.0');
  
  // Also check WOW64 path for compatibility
  if not Result then
    Result := RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\\WOW6432Node\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\X64', 'Version', Value) and
             (Value >= '14.0');
  
  if Result then
    LogCustom('Visual C++ detection: FOUND (version ' + Value + ' or compatible)')
  else
    LogCustom('Visual C++ detection: NOT FOUND (will need to install)');
end;

procedure CreateQtWebEngineDirectories;
var
  AppDir, QtCacheDir, QtDataDir: String;
begin
  // Create Qt WebEngine cache and data directories with proper permissions
  AppDir := ExpandConstant('{{app}}');
  QtCacheDir := AppDir + '\\QtWebEngine\\Cache';
  QtDataDir := AppDir + '\\QtWebEngine\\Data';
  
  LogCustom('Creating Qt WebEngine directories...');
  
  if not DirExists(QtCacheDir) then
  begin
    if CreateDir(QtCacheDir) then
      LogCustom('Created Qt WebEngine cache directory: ' + QtCacheDir)
    else
      LogCustom('Failed to create Qt WebEngine cache directory: ' + QtCacheDir);
  end;
  
  if not DirExists(QtDataDir) then
  begin
    if CreateDir(QtDataDir) then
      LogCustom('Created Qt WebEngine data directory: ' + QtDataDir)
    else
      LogCustom('Failed to create Qt WebEngine data directory: ' + QtDataDir);
  end;
end;

procedure InitializeWizard;
var
  StatusMsg: String;
  LogFile: String;
begin
  // Initialize debug log
  LogFile := ExpandConstant('{{tmp}}') + '\\TrackPro_Install_Debug.txt';
  LogCustom('=== TrackPro Installation Started ===');
  LogCustom('Installer version: {version}');
  LogCustom('Temp directory: ' + ExpandConstant('{{tmp}}'));
  LogCustom('User privileges: Admin required');
  LogCustom('');
  LogCustom('Starting prerequisite detection...');
  
  StatusMsg := 'TrackPro Installer - Prerequisite Check' + #13#10 + #13#10;
  
  if IsVJoyInstalled then
    StatusMsg := StatusMsg + '+ vJoy: Already installed (will skip)' + #13#10
  else
    StatusMsg := StatusMsg + '- vJoy: Not found (will install)' + #13#10;
    
  if IsHidHideInstalled then
    StatusMsg := StatusMsg + '+ HidHide: Already installed (will skip)' + #13#10
  else
    StatusMsg := StatusMsg + '- HidHide: Not found (will install)' + #13#10;
    
  if IsVCRedistInstalled then
    StatusMsg := StatusMsg + '+ Visual C++: Already installed (will skip)' + #13#10
  else
    StatusMsg := StatusMsg + '- Visual C++: Not found (will install)' + #13#10;
    
  StatusMsg := StatusMsg + #13#10 + 'The default installation path can be changed on the next screen.' + #13#10;
  StatusMsg := StatusMsg + 'A desktop shortcut will be created.' + #13#10 + #13#10;
  StatusMsg := StatusMsg + 'Debug log: ' + LogFile + #13#10 + #13#10 + 'Click OK to continue...';
  
  LogCustom('Prerequisite detection completed. Showing summary to user.');
  
  MsgBox(StatusMsg, mbInformation, MB_OK);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  InstallCount: Integer;
  StatusMsg: String;
  LogFile: String;
begin
  if CurStep = ssInstall then
  begin
    LogCustom('=== Starting installation phase ===');
    LogCustom('TrackPro application will be installed to: ' + ExpandConstant('{{app}}'));
  end;
  
  if CurStep = ssPostInstall then
  begin
    LogCustom('=== Installation phase completed ===');
    
    // Create Qt WebEngine directories
    CreateQtWebEngineDirectories;
    
    LogCustom('Re-checking prerequisites after installation...');
    
    InstallCount := 0;
    StatusMsg := 'Installation completed!' + #13#10 + #13#10 + 
                'TrackPro has been successfully installed to:' + #13#10 + 
                ExpandConstant('{{app}}') + #13#10 + #13#10 + 
                'Prerequisites status:' + #13#10;
    
    if IsVJoyInstalled then begin
      StatusMsg := StatusMsg + '+ vJoy: Available' + #13#10;
      InstallCount := InstallCount + 1;
    end;
    
    if IsHidHideInstalled then begin
      StatusMsg := StatusMsg + '+ HidHide: Available' + #13#10;
      InstallCount := InstallCount + 1;
    end;
    
    if IsVCRedistInstalled then begin
      StatusMsg := StatusMsg + '+ Visual C++: Available' + #13#10;
      InstallCount := InstallCount + 1;
    end;
    
    if InstallCount = 3 then begin
      StatusMsg := StatusMsg + #13#10 + 'All prerequisites are ready!' + #13#10;
      LogCustom('SUCCESS: All 3 prerequisites verified as installed');
    end else begin
      StatusMsg := StatusMsg + #13#10 + 'Some prerequisites may need manual attention.' + #13#10;
      LogCustom('WARNING: Only ' + IntToStr(InstallCount) + ' of 3 prerequisites verified');
    end;
      
    LogFile := ExpandConstant('{{tmp}}') + '\\TrackPro_Install_Debug.txt';
    
    // Copy debug log to application directory for easy access
    try
      FileCopy(LogFile, ExpandConstant('{{app}}') + '\\TrackPro_Install_Debug.txt', False);
      StatusMsg := StatusMsg + #13#10 + 'Debug log saved to: ' + ExpandConstant('{{app}}') + '\\TrackPro_Install_Debug.txt' + #13#10 + #13#10;
      LogCustom('Debug log copied to application directory for user access');
    except
      StatusMsg := StatusMsg + #13#10 + 'Debug log available at: ' + LogFile + #13#10 + #13#10;
      LogCustom('Could not copy debug log to application directory, left in temp');
    end;
    
    StatusMsg := StatusMsg + 'You can now launch TrackPro from the Start Menu or Desktop shortcut!';
    
    LogCustom('=== Installation completed successfully ===');
    
    MsgBox(StatusMsg, mbInformation, MB_OK);
  end;
end;

[Run]
Filename: "{{tmp}}\\vJoySetup.exe"; StatusMsg: "Installing vJoy..."; Flags: waituntilterminated; Check: not IsVJoyInstalled; BeforeInstall: LogPrereqStart('vJoy'); AfterInstall: LogPrereqEnd('vJoy')
Filename: "{{tmp}}\\HidHide_1.5.230_x64.exe"; StatusMsg: "Installing HidHide..."; Flags: waituntilterminated; Check: not IsHidHideInstalled; BeforeInstall: LogPrereqStart('HidHide'); AfterInstall: LogPrereqEnd('HidHide')
Filename: "{{tmp}}\\vc_redist.x64.exe"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated; Check: not IsVCRedistInstalled; BeforeInstall: LogPrereqStart('Visual C++'); AfterInstall: LogPrereqEnd('Visual C++')

[Icons]
Name: "{{group}}\\TrackPro"; Filename: "{{app}}\\{exe_name}"; WorkingDir: "{{app}}"; Comment: "TrackPro Racing Coach Application"
Name: "{{commondesktop}}\\TrackPro"; Filename: "{{app}}\\{exe_name}"; WorkingDir: "{{app}}"; Comment: "TrackPro Racing Coach Application"; Tasks: desktopicon; Flags: createonlyiffileexists

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
""".format(version=__version__, exe_name=actual_exe_name)
    
    iss_script = "simple_installer.iss"
    with open(iss_script, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # Compile with Inno Setup with better error handling
    print("Compiling installer...")
    try:
        # Find Inno Setup
        inno_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\iscc.exe",
            r"C:\Program Files\Inno Setup 6\iscc.exe",
            "iscc"
        ]
        
        inno_exe = None
        for path in inno_paths:
            if path == "iscc":
                                 # Check if iscc is in PATH
                 try:
                     subprocess.run([path, "/?"], capture_output=True, timeout=5)
                     inno_exe = path
                     break
                 except:
                    continue
            elif os.path.exists(path):
                inno_exe = path
                break
        
        if not inno_exe:
            print("❌ Inno Setup not found. Install from: https://jrsoftware.org/isdl.php")
            return False
            
        # Run Inno Setup compiler
        result = subprocess.run([inno_exe, iss_script], 
                               capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"❌ Inno Setup compilation failed (exit code {result.returncode})")
            if result.stdout:
                print(f"STDOUT: {result.stdout}")
            if result.stderr:
                print(f"STDERR: {result.stderr}")
            return False
        
        # Check if installer was created
        installer_name = f"TrackPro_Setup_v{__version__}.exe"
        if os.path.exists(installer_name):
            installer_size = os.path.getsize(installer_name)
            print(f"✓ Installer created: {installer_name} ({installer_size:,} bytes)")
            return True
        else:
            print(f"❌ Installer not found after compilation: {installer_name}")
            print("Checking current directory for any installer files...")
            installer_files = [f for f in os.listdir('.') if f.startswith('TrackPro_Setup') and f.endswith('.exe')]
            if installer_files:
                print(f"Found these installer files: {installer_files}")
                return True
            return False
             
    except subprocess.TimeoutExpired:
        print("❌ Inno Setup compilation timed out")
        return False
    except Exception as e:
        print(f"❌ Inno Setup error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        # Clean build but preserve prerequisite cache
        for path in ["dist", "build"]:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"✓ Cleaned {path}")
        
        # Only clean installer_temp/dist, keep prerequisites cache
        if os.path.exists("installer_temp/dist"):
            shutil.rmtree("installer_temp/dist")
            print("✓ Cleaned installer_temp/dist (kept prerequisites cache)")
    else:
        # Build installer
        print("🚀 Starting optimized build process...")
        start_time = time.time() if 'time' in dir() else None
        
        if create_optimized_installer():
            if start_time:
                build_time = time.time() - start_time
                print(f"🎉 Build successful in {build_time:.1f} seconds!")
            else:
                print("🎉 Build successful!")
        else:
            print("❌ Build failed")
            sys.exit(1) 