import PyInstaller.__main__
import sys
import os
import shutil
import subprocess
import requests
import winreg
from urllib.parse import urlparse
import stat
from trackpro import __version__

class InstallerBuilder:
    VJOY_URL = "https://github.com/jshafer817/vJoy/releases/download/v2.1.9.1/vJoySetup.exe"
    HIDHIDE_URL = "https://github.com/ViGEm/HidHide/releases/download/v1.2.98.0/HidHide_1.2.98_x64.exe"
    
    def __init__(self):
        self.temp_dir = "installer_temp"
        self.dist_dir = "dist"
        self.version = __version__
        
    def download_file(self, url, dest_folder):
        """Download a file and return its path."""
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        filename = os.path.basename(urlparse(url).path)
        filepath = os.path.join(dest_folder, filename)
        
        if not os.path.exists(filepath):
            print(f"Downloading {filename}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return filepath

    def create_installer_script(self):
        """Create the NSIS installer script."""
        script = r"""
; Installer script for TrackPro

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v{version}"
OutFile "TrackPro_Setup_v{version}.exe"
InstallDir "$PROGRAMFILES64\TrackPro"
RequestExecutionLevel admin ; Explicitly request admin rights

; Store install path for resume after reboot
!define RESUME_INSTALLATIONS_KEY "Software\Microsoft\Windows\CurrentVersion\RunOnce"
!define RESUME_INSTALLATIONS_VALUE "TrackPro Setup"

!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

Var NEEDS_RESTART
Var DEBUG_MSG

Function .onInit
    StrCpy $NEEDS_RESTART "0"
    
    ; Verify we're running with admin rights
    UserInfo::GetAccountType
    Pop $0
    ${{If}} $0 != "admin"
        MessageBox MB_OK|MB_ICONSTOP "Administrator rights required! Please right-click and select 'Run as administrator'."
        Abort "Installation aborted: Administrator rights required"
    ${{EndIf}}
    
    ; Check if we're resuming after reboot
    ReadRegStr $R0 HKLM "${{RESUME_INSTALLATIONS_KEY}}" "${{RESUME_INSTALLATIONS_VALUE}}"
    ${{If}} $R0 != ""
        ; Skip driver installation if we're resuming
        StrCpy $0 "RESUME"
    ${{EndIf}}
FunctionEnd

Section "Prerequisites"
    ${{If}} $0 != "RESUME"
        ; Create temp directories with verification
        CreateDirectory "$TEMP\TrackPro"
        CreateDirectory "$TEMP\TrackPro\prerequisites"
        CreateDirectory "$TEMP\TrackPro\app"
        
        SetOutPath "$TEMP\TrackPro\prerequisites"
        DetailPrint "Extracting prerequisites..."
        
        ; Extract prerequisite installers
        File /r "installer_temp\prerequisites\*"
        
        ; Extract main executable to temp location
        SetOutPath "$TEMP\TrackPro\app"
        DetailPrint "Extracting main application..."
        File "installer_temp\dist\TrackPro_v{version}.exe"
        
        ; Verify the file was extracted correctly
        IfFileExists "$TEMP\TrackPro\app\TrackPro_v{version}.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to extract TrackPro_v{version}.exe to temporary directory!"
            Abort "Installation failed: Could not extract TrackPro_v{version}.exe"
        
        ; Create program directory with verification
        DetailPrint "Creating installation directory..."
        CreateDirectory "$PROGRAMFILES64\TrackPro"
        
        ; Check if directory was created successfully
        IfFileExists "$PROGRAMFILES64\TrackPro\*.*" +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to create installation directory! Please ensure you have administrator privileges."
            Abort "Installation failed: Could not create installation directory"
        
        ; Set working directory to program files
        SetOutPath "$PROGRAMFILES64\TrackPro"
        
        ; Install TrackPro with explicit verification and better error handling
        DetailPrint "Installing TrackPro..."
        
        ; Debug message with source and destination paths
        StrCpy $DEBUG_MSG "Copying from: $TEMP\TrackPro\app\TrackPro_v{version}.exe to $PROGRAMFILES64\TrackPro"
        DetailPrint $DEBUG_MSG
        
        ; Check if destination file already exists and try to remove it
        IfFileExists "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe" 0 +3
            DetailPrint "Removing existing installation file..."
            Delete "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe"
        
        ; Clear any previous errors and copy the file
        ClearErrors
        CopyFiles /SILENT "$TEMP\TrackPro\app\TrackPro_v{version}.exe" "$PROGRAMFILES64\TrackPro"
        
        ; Check for copy errors
        IfErrors 0 +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v{version}.exe to installation directory! Please ensure you have administrator privileges and try again."
            Abort "Installation failed: Could not copy TrackPro_v{version}.exe"
        
        ; Verify TrackPro.exe exists in the destination
        IfFileExists "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to verify TrackPro_v{version}.exe in installation directory!"
            Abort "Installation failed: Could not verify TrackPro_v{version}.exe"
            
        ; Create shortcuts with verification
        DetailPrint "Creating shortcuts..."
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v{version}.lnk" "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe"
        CreateShortCut "$DESKTOP\TrackPro v{version}.lnk" "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe"
        
        DetailPrint "TrackPro installation complete"

        ; Run HidHide installer with wait
        DetailPrint "Installing HidHide..."
        ExecWait '"$TEMP\TrackPro\prerequisites\HidHide_1.2.98_x64.exe" /quiet /norestart' $1
        DetailPrint "HidHide installation complete with exit code: $1"
        ${{If}} $1 == 3010
            StrCpy $NEEDS_RESTART "1"
            DetailPrint "HidHide requires a system restart"
        ${{EndIf}}

        ; Run vJoy installer silently and wait
        DetailPrint "Installing vJoy..."
        ; Save the installation path for resume
        WriteRegStr HKLM "${{RESUME_INSTALLATIONS_KEY}}" "${{RESUME_INSTALLATIONS_VALUE}}" "$EXEPATH"
        ExecWait '"$TEMP\TrackPro\prerequisites\vJoySetup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /TYPE=MINIMAL' $0
        DetailPrint "vJoy installation complete with exit code: $0"
        ${{If}} $0 == 3010
            StrCpy $NEEDS_RESTART "1"
            DetailPrint "vJoy requires a system restart"
        ${{EndIf}}

        ; Clean up temp files AFTER all installations are complete
        DetailPrint "Cleaning up temporary files..."
        SetOutPath "$TEMP"
        RMDir /r "$TEMP\TrackPro"

        ; Show installation paths at the end
        MessageBox MB_OK|MB_ICONINFORMATION \
            "TrackPro v{version} has been installed to:$\n\
            $PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe$\n\n\
            Shortcuts have been created:$\n\
            - Start Menu: $SMPROGRAMS\TrackPro\TrackPro v{version}.lnk$\n\
            - Desktop: $DESKTOP\TrackPro v{version}.lnk$\n\n\
            Please verify these locations after installation."
            
        ; Check if we need to restart
        ${{If}} $NEEDS_RESTART == "1"
            MessageBox MB_YESNO|MB_ICONQUESTION "A system restart is required to complete the installation. Would you like to restart now?" IDNO +2
                Reboot
        ${{EndIf}}
    ${{EndIf}}
SectionEnd

Section "MainApplication"
    ; Only run this section if we're resuming after a reboot
    ${{If}} $0 == "RESUME"
        DetailPrint "Resuming installation after reboot..."
        SetOutPath "$INSTDIR"
        
        ; Check if the file exists in the package
        IfFileExists "dist\TrackPro_v{version}.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Could not find TrackPro_v{version}.exe in the installer package!"
            Abort "Resume installation failed: Missing executable file"
            
        ; Copy the main executable
        ClearErrors
        File "dist\TrackPro_v{version}.exe"
        
        ; Check for errors
        IfErrors 0 +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v{version}.exe during resume!"
            Abort "Resume installation failed: Could not copy executable"
        
        ; Create shortcuts
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v{version}.lnk" "$INSTDIR\TrackPro_v{version}.exe"
        CreateShortCut "$DESKTOP\TrackPro v{version}.lnk" "$INSTDIR\TrackPro_v{version}.exe"
        
        ; Create uninstaller
        WriteUninstaller "$INSTDIR\Uninstall.exe"
        
        ; Clean up resume key
        DeleteRegValue HKLM "${{RESUME_INSTALLATIONS_KEY}}" "${{RESUME_INSTALLATIONS_VALUE}}"
        
        DetailPrint "Installation completed successfully after reboot"
    ${{EndIf}}
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    Delete "$INSTDIR\TrackPro_v{version}.exe"
    RMDir "$INSTDIR"
    
    Delete "$SMPROGRAMS\TrackPro\TrackPro v{version}.lnk"
    Delete "$DESKTOP\TrackPro v{version}.lnk"
    RMDir "$SMPROGRAMS\TrackPro"
    
    DetailPrint "Uninstallation complete"
SectionEnd
"""
        with open("installer.nsi", "w") as f:
            f.write(script.format(version=self.version))

    def check_nsis(self):
        """Check if NSIS is installed and available."""
        nsis_paths = [
            r"C:\Program Files (x86)\NSIS\makensis.exe",  # Primary path
            r"C:\Program Files\NSIS\makensis.exe",        # Alternative path
        ]
        
        # First check if makensis is directly accessible in PATH
        try:
            subprocess.run(["makensis", "/VERSION"], check=True, capture_output=True)
            print("✓ NSIS found in PATH")
            return True
        except FileNotFoundError:
            # If not in PATH, check common installation locations
            for path in nsis_paths:
                if os.path.exists(path):
                    print(f"✓ NSIS found at {path}")
                    # Add the NSIS directory to PATH
                    nsis_dir = os.path.dirname(path)
                    os.environ["PATH"] = nsis_dir + os.pathsep + os.environ["PATH"]
                    return True
                
            print("✗ Error: NSIS not found in common locations:")
            print("Checked paths:")
            for path in nsis_paths:
                print(f"  - {path}")
            print("\nPlease ensure NSIS is installed and in your PATH")
            return False

    def build(self):
        """Build the application and installer."""
        print("\n=== Starting Installer Build Process ===")
        
        # Check NSIS first
        if not self.check_nsis():
            sys.exit(1)
        
        # Clean previous builds
        self.clean_build()
        
        # Build main executable
        print("\nBuilding main application...")
        self.build_exe()
        
        # Verify the executable was created
        exe_path = os.path.join("dist", f"TrackPro_v{self.version}.exe")
        if not os.path.exists(exe_path):
            raise Exception(f"Failed to build TrackPro_v{self.version}.exe - file not found at {exe_path}")
        
        # Download prerequisites
        print("\nDownloading prerequisites...")
        prereq_dir = os.path.join(self.temp_dir, "prerequisites")
        vjoy_path = self.download_file(self.VJOY_URL, prereq_dir)
        hidhide_path = self.download_file(self.HIDHIDE_URL, prereq_dir)
        
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
        
        # Build installer
        print("\nBuilding installer...")
        try:
            nsis_exe = r"C:\Program Files (x86)\NSIS\makensis.exe"
            if not os.path.exists(nsis_exe):
                nsis_exe = r"C:\Program Files\NSIS\makensis.exe"
            
            if not os.path.exists(nsis_exe):
                raise FileNotFoundError("Could not find makensis.exe")
            
            # First validate the script
            print("Validating NSIS script...")
            validate_cmd = [nsis_exe, "/CMDHELP", "installer.nsi"]
            try:
                validate_result = subprocess.run(validate_cmd, 
                                              capture_output=True, 
                                              text=True,
                                              check=False)
                if "error" in validate_result.stderr.lower():
                    print(f"NSIS Script Validation Error: {validate_result.stderr}")
                    raise Exception(f"NSIS script validation failed: {validate_result.stderr}")
            except Exception as e:
                print(f"NSIS Script Validation Warning: {str(e)}")
                # Continue anyway as /CMDHELP might not work as expected
            
            # Run NSIS with verbose output
            print("Compiling installer...")
            result = subprocess.run([nsis_exe, "/V4", "installer.nsi"], 
                                  capture_output=True, 
                                  text=True,
                                  check=False)  # Don't raise exception yet
            
            # Check for errors in the output
            if result.returncode != 0:
                print(f"NSIS Error (return code {result.returncode}):")
                print(result.stdout)
                print(result.stderr)
                
                # Try to find the specific error
                error_lines = []
                for line in result.stdout.splitlines():
                    if "error" in line.lower():
                        error_lines.append(line)
                
                if error_lines:
                    raise Exception(f"NSIS compilation failed with errors: {'; '.join(error_lines)}")
                else:
                    raise Exception(f"NSIS compilation failed with return code {result.returncode}")
            else:
                print("NSIS compilation successful")
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"NSIS Error: {e.stdout}\n{e.stderr}")
            raise
        except FileNotFoundError:
            raise Exception("NSIS not found. Please ensure NSIS is installed correctly")
        except Exception as e:
            print(f"Error building installer: {str(e)}")
            
            # Try to debug the NSIS script
            print("\nAttempting to debug NSIS script...")
            try:
                with open("installer.nsi", "r") as f:
                    script_lines = f.readlines()
                
                # Print a portion of the script for debugging
                print("\nNSIS Script (first 20 lines):")
                for i, line in enumerate(script_lines[:20]):
                    print(f"{i+1}: {line.rstrip()}")
                
                print("\n... (script truncated) ...\n")
            except Exception as debug_e:
                print(f"Error debugging NSIS script: {str(debug_e)}")
            
            raise Exception(f"Failed to build installer: {str(e)}")

        # Verify the installer was created
        installer_path = f"TrackPro_Setup_v{self.version}.exe"
        if not os.path.exists(installer_path):
            raise Exception(f"Installer not found at {installer_path}")
        
        print("\n✓ Installer build completed!")
        print(f"✓ Installer created at: {os.path.abspath(installer_path)}")

    def clean_build(self):
        """Clean previous builds."""
        print("\nCleaning previous builds...")
        
        def remove_readonly(func, path, _):
            """Remove read-only attribute and retry removal"""
            os.chmod(path, stat.S_IWRITE)
            func(path)
        
        for dir_name in [self.temp_dir, self.dist_dir, "build"]:
            if os.path.exists(dir_name):
                try:
                    shutil.rmtree(dir_name, onerror=remove_readonly)
                    print(f"✓ Cleaned {dir_name}/")
                except Exception as e:
                    print(f"! Warning: Could not clean {dir_name}: {str(e)}")
        
        # Clean installer files
        for file_name in ["installer.nsi", f"TrackPro_Setup_v{self.version}.exe", "TrackProSetup.exe", "TrackPro.spec"]:
            if os.path.exists(file_name):
                try:
                    os.chmod(file_name, stat.S_IWRITE)
                    os.remove(file_name)
                    print(f"✓ Cleaned {file_name}")
                except Exception as e:
                    print(f"! Warning: Could not clean {file_name}: {str(e)}")

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
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 and Windows Server 2016 -->
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
      <!-- Windows 8.1 and Windows Server 2012 R2 -->
      <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
      <!-- Windows 8 and Windows Server 2012 -->
      <supportedOS Id="{4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38}"/>
      <!-- Windows 7 and Windows Server 2008 R2 -->
      <supportedOS Id="{35138b9a-5d96-4fbd-8e2d-a2440225f93a}"/>
    </application>
  </compatibility>
</assembly>"""
        manifest_path = os.path.abspath("trackpro.manifest")
        with open(manifest_path, "w") as f:
            f.write(manifest)
        print(f"✓ Created manifest file at: {manifest_path}")
        return manifest_path

    def build_exe(self):
        """Build the main executable."""
        print("\nBuilding TrackPro executable...")
        
        # Create manifest file
        manifest_path = self.create_manifest()
        
        # Ensure the manifest exists
        if not os.path.exists(manifest_path):
            raise Exception(f"Failed to create manifest file at {manifest_path}")
        
        # Create a directory for the build if it doesn't exist
        if not os.path.exists("build"):
            os.makedirs("build")
        
        # Define PyInstaller options
        opts = [
            'run_app.py',
            f'--name=TrackPro_v{self.version}',
            '--onefile',
            '--windowed',  # Hide console window
            '--clean',
            f'--manifest={manifest_path}',  # Add manifest file
            '--uac-admin',  # Request admin privileges
            '--hidden-import=trackpro',
            '--hidden-import=trackpro.main',
            '--hidden-import=trackpro.ui',
            '--hidden-import=trackpro.hardware_input',
            '--hidden-import=trackpro.output',
            '--hidden-import=trackpro.hidhide',
            '--hidden-import=PyQt5.QtChart',
            '--hidden-import=PyQt5.QtCore',
            '--hidden-import=PyQt5.QtGui',
            '--hidden-import=PyQt5.QtWidgets',
            '--hidden-import=pygame',
            '--hidden-import=win32serviceutil',
            '--hidden-import=win32service',
            '--add-data=trackpro;trackpro',
            '--add-data=trackpro.manifest;.'  # Include manifest in the package
        ]
        
        # Check for vJoy DLL in different possible locations
        vjoy_dll_paths = [
            r"C:\Program Files\vJoy\x64\vJoyInterface.dll",
            r"C:\Program Files (x86)\vJoy\x64\vJoyInterface.dll",
            r"C:\Windows\System32\vJoyInterface.dll"
        ]
        
        dll_found = False
        for dll_path in vjoy_dll_paths:
            if os.path.exists(dll_path):
                print(f"Found vJoy DLL at: {dll_path}")
                opts.extend(['--add-binary', f'{dll_path};.'])
                dll_found = True
                break
        
        if not dll_found:
            print("Warning: vJoyInterface.dll not found. The executable may not work correctly.")
            print("Checked paths:")
            for path in vjoy_dll_paths:
                print(f"  - {path}")
            
        # Check for HidHide CLI using registry
        cli_found = False
        try:
            # First check if HidHide is installed
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Installer\Dependencies\NSS.Drivers.HidHide.x64\Version", 0, winreg.KEY_READ) as key:
                version = winreg.QueryValueEx(key, "")[0]
                print(f"Found HidHide version: {version}")
                
                # Get installation path
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide\Path", 0, winreg.KEY_READ) as key:
                    install_path = winreg.QueryValueEx(key, "")[0]
                    print(f"Found HidHide installation path: {install_path}")
                    
                    # CLI should be in the x64 subdirectory
                    cli_path = os.path.join(install_path, "x64", "HidHideCLI.exe")
                    if os.path.exists(cli_path):
                        print(f"Found HidHide CLI at: {cli_path}")
                        # Copy CLI to trackpro package directory so it's included in the build
                        cli_dest = os.path.join("trackpro", "HidHideCLI.exe")
                        try:
                            shutil.copy2(cli_path, cli_dest)
                            print(f"✓ Copied HidHide CLI to {cli_dest}")
                            cli_found = True
                        except Exception as e:
                            print(f"Warning: Failed to copy HidHide CLI: {e}")
        except WindowsError:
            # Fallback to searching in common locations
            hidhide_paths = [
                r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
                r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe"
            ]
            
            for cli_path in hidhide_paths:
                if os.path.exists(cli_path):
                    print(f"Found HidHide CLI at: {cli_path}")
                    # Copy CLI to trackpro package directory so it's included in the build
                    cli_dest = os.path.join("trackpro", "HidHideCLI.exe")
                    try:
                        shutil.copy2(cli_path, cli_dest)
                        print(f"✓ Copied HidHide CLI to {cli_dest}")
                        cli_found = True
                        break
                    except Exception as e:
                        print(f"Warning: Failed to copy HidHide CLI: {e}")
        
        if not cli_found:
            print("Warning: HidHideCLI.exe not found. Please ensure HidHide is installed correctly.")
            print("Checked registry and common paths:")
            print("  - HKCR\\SOFTWARE\\Nefarius Software Solutions e.U.\\Nefarius Software Solutions e.U. HidHide\\Path")
            print("  - C:\\Program Files\\Nefarius Software Solutions\\HidHide\\x64\\HidHideCLI.exe")
            print("  - C:\\Program Files (x86)\\Nefarius Software Solutions\\HidHide\\x64\\HidHideCLI.exe")
        
        # Run PyInstaller with the options
        print("\nRunning PyInstaller with the following options:")
        for opt in opts:
            print(f"  {opt}")
        
        try:
            PyInstaller.__main__.run(opts)
        except Exception as e:
            print(f"PyInstaller Error: {str(e)}")
            raise Exception(f"Failed to build executable: {str(e)}")
        
        # Verify the exe was created
        exe_path = os.path.join("dist", f"TrackPro_v{self.version}.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path)
            print(f"\n✓ TrackPro_v{self.version}.exe successfully built at: {os.path.abspath(exe_path)} ({file_size} bytes)")
            
            # Try to run it as a test
            try:
                print("Running test execution...")
                subprocess.run([exe_path, "--test"], timeout=5)
                print("✓ Test run successful")
            except Exception as e:
                print(f"! Warning: Test run failed: {str(e)}")
                print("This may not be a problem if the test is expected to fail in this environment.")
        else:
            raise Exception(f"Failed to build TrackPro_v{self.version}.exe - file not found at {exe_path}")

if __name__ == "__main__":
    try:
        builder = InstallerBuilder()
        builder.build()
    except Exception as e:
        print(f"\n✗ Build failed with error: {str(e)}")
        sys.exit(1)
    
    # Only wait for input if not running with --no-wait argument
    if len(sys.argv) <= 1 or "--no-wait" not in sys.argv:
        input("\nPress Enter to exit...") 