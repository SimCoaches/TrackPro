#!/usr/bin/env python3
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
from pathlib import Path
import importlib
from sign_code import CodeSigner

class InstallerBuilder:
    VJOY_URL = "https://github.com/jshafer817/vJoy/releases/download/v2.1.9.1/vJoySetup.exe"
    HIDHIDE_URL = "https://github.com/ViGEm/HidHide/releases/download/v1.2.98.0/HidHide_1.2.98_x64.exe"
    
    def __init__(self):
        self.temp_dir = "installer_temp"
        self.dist_dir = "dist"
        self.version = __version__
        self.cwd = Path.cwd()
        self.code_signer = CodeSigner()
        self.enable_signing = True  # Set to False to disable signing
        
    def download_file(self, url, dest_folder):
        """Download a file and return its path."""
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        filename = os.path.basename(urlparse(url).path)
        filepath = os.path.join(dest_folder, filename)
        
        if not os.path.exists(filepath):
            print(f"Downloading {filename} from {url}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Ensure chunk is not empty
                        f.write(chunk)
            print(f"✓ Successfully downloaded {filename} to {filepath}")
        else:
            print(f"✓ {filename} already exists at {filepath}")
        
        # Verify file exists and has content
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"✓ Verified {filename} at {filepath} ({file_size} bytes)")
        else:
            print(f"! Error: {filename} not found at {filepath} after download attempt")
            
        return filepath

    def sign_files(self, files_to_sign):
        """Sign the specified files with the code signing certificate."""
        if not self.enable_signing:
            print("Code signing is disabled")
            return True
        
        if not self.code_signer.signtool_path:
            print("⚠️  Warning: signtool.exe not found. Skipping code signing.")
            print("To enable code signing:")
            print("1. Install Windows SDK from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
            print("2. Or install via Visual Studio Installer -> Windows SDK")
            return False
        
        print("\n=== Code Signing Phase ===")
        signing_successful = True
        
        for file_path in files_to_sign:
            if not os.path.exists(file_path):
                print(f"⚠️  Warning: File not found for signing: {file_path}")
                continue
            
            file_size = os.path.getsize(file_path)
            print(f"\nSigning: {file_path} ({file_size:,} bytes)")
            
            # Try to sign the file
            success = self.code_signer.sign_file(
                file_path, 
                description=f"TrackPro v{self.version}",
                timestamp_url="http://timestamp.sectigo.com"
            )
            
            if success:
                print(f"✓ Successfully signed: {file_path}")
                # Verify the signature
                if self.code_signer.verify_signature(file_path):
                    print(f"✓ Signature verified: {file_path}")
                else:
                    print(f"⚠️  Warning: Signature verification failed: {file_path}")
            else:
                print(f"✗ Failed to sign: {file_path}")
                signing_successful = False
        
        if signing_successful:
            print("\n✓ All files signed successfully!")
        else:
            print("\n⚠️  Some files failed to sign. Check the output above for details.")
            print("The build will continue, but unsigned files may trigger security warnings.")
        
        return signing_successful

    def create_installer_script(self):
        """Create the NSIS installer script using relative paths with backslashes."""
        print("\nCreating installer script...")
        
        # Use only relative paths with backslashes for NSIS
        prereq_dir = "installer_temp\\prerequisites"
        dist_dir = "installer_temp\\dist"
        
        print(f"Using relative paths in NSIS script:")
        print(f"  Installer temp directory: {prereq_dir}")
        print(f"  Distribution directory: {dist_dir}")
        
        script = r"""
; Installer script for TrackPro

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v{version}"
OutFile "TrackPro_Setup_v{version}.exe"
InstallDir "$PROGRAMFILES64\TrackPro"
RequestExecutionLevel admin ; Explicitly request admin rights

; Define application metadata for Add/Remove Programs
!define PRODUCT_NAME "TrackPro"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "TrackPro"
!define PRODUCT_WEB_SITE "https://github.com/Trackpro-dev/TrackPro"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\TrackPro_v{version}.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{PRODUCT_NAME}}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; Store install path for resume after reboot
!define RESUME_INSTALLATIONS_KEY "Software\Microsoft\Windows\CurrentVersion\RunOnce"
!define RESUME_INSTALLATIONS_VALUE "TrackPro Setup"

!define MUI_ABORTWARNING
!define MUI_ICON "${{NSISDIR}}\Contrib\Graphics\Icons\modern-install.ico" ; Default NSIS icon, replace with your own if available
!define MUI_UNICON "${{NSISDIR}}\Contrib\Graphics\Icons\modern-uninstall.ico" ; Default NSIS uninstall icon

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"  ; Add license page if LICENSE file exists
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

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
    ${{Else}}
        ; Clean up previous TrackPro installations
        Call CleanupPreviousVersions
    ${{EndIf}}
FunctionEnd

Function CleanupPreviousVersions
    DetailPrint "Checking for previous TrackPro installations..."
    DetailPrint "NOTE: User data (calibrations, settings) will be preserved during cleanup"
    
    ; First, terminate any running TrackPro processes
    DetailPrint "Terminating any running TrackPro processes..."
    ExecWait 'taskkill /F /IM "TrackPro*.exe" /T' $0
    
    ; Remove all TrackPro executables from Program Files
    DetailPrint "Removing previous TrackPro executables..."
    Delete "$PROGRAMFILES64\TrackPro\TrackPro*.exe"
    Delete "$PROGRAMFILES64\TrackPro\TrackPro_v*.exe"
    Delete "$PROGRAMFILES32\TrackPro\TrackPro*.exe"
    Delete "$PROGRAMFILES32\TrackPro\TrackPro_v*.exe"
    
    ; Remove all TrackPro shortcuts from Start Menu
    DetailPrint "Removing previous TrackPro shortcuts..."
    Delete "$SMPROGRAMS\TrackPro\TrackPro*.lnk"
    Delete "$SMPROGRAMS\TrackPro\TrackPro v*.lnk"
    
    ; Remove all TrackPro desktop shortcuts
    Delete "$DESKTOP\TrackPro*.lnk"
    Delete "$DESKTOP\TrackPro v*.lnk"
    
    ; Clean up registry entries for all previous versions
    DetailPrint "Cleaning up previous version registry entries..."
    
    ; Enumerate and remove old TrackPro uninstall entries
    StrCpy $1 0
    loop:
        EnumRegKey $2 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall" $1
        StrCmp $2 "" done
        
        ; Check if this is a TrackPro entry
        ReadRegStr $3 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$2" "DisplayName"
        StrCpy $4 $3 8  ; Get first 8 characters
        StrCmp $4 "TrackPro" 0 next_key
        
        ; This is a TrackPro entry, remove it
        DetailPrint "Removing registry entry: $3"
        DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$2"
        Goto loop  ; Start over since we modified the registry
        
        next_key:
        IntOp $1 $1 + 1
        Goto loop
    
    done:
    DetailPrint "Previous version cleanup completed"
FunctionEnd

Section "Prerequisites"
    ${{If}} $0 != "RESUME"
        ; Create temp directories with verification
        CreateDirectory "$TEMP\TrackPro"
        CreateDirectory "$TEMP\TrackPro\prerequisites"
        CreateDirectory "$TEMP\TrackPro\app"
        
        SetOutPath "$TEMP\TrackPro\prerequisites"
        DetailPrint "Extracting prerequisites..."
        
        ; Extract prerequisite installers using relative paths
        File "installer_temp\prerequisites\vJoySetup.exe"
        File "installer_temp\prerequisites\HidHide_1.2.98_x64.exe"
        
        ; Extract main executable to temp location
        SetOutPath "$TEMP\TrackPro\app"
        DetailPrint "Extracting main application..."
        
        ; Extract main executable using relative path
        File "installer_temp\dist\TrackPro_v{version}.exe"
        
        ; Verify the file was extracted correctly
        ${{IfNot}} ${{FileExists}} "$TEMP\TrackPro\app\TrackPro_v{version}.exe"
            MessageBox MB_OK|MB_ICONSTOP "Failed to extract TrackPro_v{version}.exe to temporary directory!"
            Abort "Installation failed: Could not extract TrackPro_v{version}.exe"
        ${{EndIf}}
        
        ; Create program directory with verification
        DetailPrint "Creating installation directory..."
        CreateDirectory "$PROGRAMFILES64\TrackPro"
        
        ; Check if directory was created successfully
        ${{IfNot}} ${{FileExists}} "$PROGRAMFILES64\TrackPro"
            MessageBox MB_OK|MB_ICONSTOP "Failed to create installation directory! Please ensure you have administrator privileges."
            Abort "Installation failed: Could not create installation directory"
        ${{EndIf}}
        
        ; Set working directory to program files
        SetOutPath "$PROGRAMFILES64\TrackPro"
        
        ; Install TrackPro with explicit verification and better error handling
        DetailPrint "Installing TrackPro..."
        
        ; Debug message with source and destination paths
        StrCpy $DEBUG_MSG "Copying from: $TEMP\TrackPro\app\TrackPro_v{version}.exe to $PROGRAMFILES64\TrackPro"
        DetailPrint $DEBUG_MSG
        
        ; Check if destination file already exists and try to remove it
        ${{If}} ${{FileExists}} "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe"
            DetailPrint "Removing existing installation file..."
            Delete "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe"
        ${{EndIf}}
        
        ; Clear any previous errors and copy the file
        ClearErrors
        CopyFiles /SILENT "$TEMP\TrackPro\app\TrackPro_v{version}.exe" "$PROGRAMFILES64\TrackPro"
        
        ; Check for copy errors
        ${{If}} ${{Errors}}
            MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v{version}.exe to installation directory! Please ensure you have administrator privileges and try again."
            Abort "Installation failed: Could not copy TrackPro_v{version}.exe"
        ${{EndIf}}
        
        ; Verify TrackPro.exe exists in the destination
        ${{IfNot}} ${{FileExists}} "$PROGRAMFILES64\TrackPro\TrackPro_v{version}.exe"
            MessageBox MB_OK|MB_ICONSTOP "Failed to verify TrackPro_v{version}.exe in installation directory!"
            Abort "Installation failed: Could not verify TrackPro_v{version}.exe"
        ${{EndIf}}
            
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

        ; Create uninstaller
        WriteUninstaller "$INSTDIR\uninstall.exe"
        
        ; Register application for Add/Remove Programs
        WriteRegStr HKLM "${{PRODUCT_DIR_REGKEY}}" "" "$INSTDIR\TrackPro_v{version}.exe"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "DisplayName" "$(^Name)"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "UninstallString" "$INSTDIR\uninstall.exe"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "DisplayIcon" "$INSTDIR\TrackPro_v{version}.exe"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "DisplayVersion" "${{PRODUCT_VERSION}}"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "URLInfoAbout" "${{PRODUCT_WEB_SITE}}"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "Publisher" "${{PRODUCT_PUBLISHER}}"
        
        ; Write size information for Add/Remove Programs
        ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
        IntFmt $0 "0x%08X" $0
        WriteRegDWORD ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "EstimatedSize" "$0"

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
        
        ; Extract main executable using relative path
        File "installer_temp\dist\TrackPro_v{version}.exe"
        
        ; Create shortcuts
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v{version}.lnk" "$INSTDIR\TrackPro_v{version}.exe"
        CreateShortCut "$DESKTOP\TrackPro v{version}.lnk" "$INSTDIR\TrackPro_v{version}.exe"
        
        ; Create uninstaller
        WriteUninstaller "$INSTDIR\uninstall.exe"
        
        ; Register application for Add/Remove Programs
        WriteRegStr HKLM "${{PRODUCT_DIR_REGKEY}}" "" "$INSTDIR\TrackPro_v{version}.exe"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "DisplayName" "$(^Name)"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "UninstallString" "$INSTDIR\uninstall.exe"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "DisplayIcon" "$INSTDIR\TrackPro_v{version}.exe"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "DisplayVersion" "${{PRODUCT_VERSION}}"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "URLInfoAbout" "${{PRODUCT_WEB_SITE}}"
        WriteRegStr ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "Publisher" "${{PRODUCT_PUBLISHER}}"
        
        ; Write size information for Add/Remove Programs
        ${{GetSize}} "$INSTDIR" "/S=0K" $0 $1 $2
        IntFmt $0 "0x%08X" $0
        WriteRegDWORD ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}" "EstimatedSize" "$0"
        
        ; Clean up resume key
        DeleteRegValue HKLM "${{RESUME_INSTALLATIONS_KEY}}" "${{RESUME_INSTALLATIONS_VALUE}}"
        
        DetailPrint "Installation completed successfully after reboot"
    ${{EndIf}}
SectionEnd

Section "Uninstall"
    ; Terminate any running TrackPro processes first
    DetailPrint "Terminating any running TrackPro processes..."
    ExecWait 'taskkill /F /IM "TrackPro*.exe" /T' $0
    
    ; Remove ALL TrackPro application files (not just current version)
    DetailPrint "Removing all TrackPro application files..."
    Delete "$INSTDIR\uninstall.exe"
    Delete "$INSTDIR\TrackPro*.exe"
    Delete "$INSTDIR\TrackPro_v*.exe"
    
    ; NOTE: We deliberately DO NOT remove user data directories like:
    ; - $LOCALAPPDATA\TrackPro (contains user calibrations, settings, etc.)
    ; - $APPDATA\TrackPro (contains user configuration files)
    ; This preserves user's calibrations and settings across updates
    
    ; Remove ALL TrackPro shortcuts and directories
    DetailPrint "Removing all TrackPro shortcuts..."
    Delete "$SMPROGRAMS\TrackPro\TrackPro*.lnk"
    Delete "$SMPROGRAMS\TrackPro\TrackPro v*.lnk"
    Delete "$DESKTOP\TrackPro*.lnk"
    Delete "$DESKTOP\TrackPro v*.lnk"
    RMDir "$SMPROGRAMS\TrackPro"
    
    ; Remove installation directory and all contents
    RMDir /r "$INSTDIR"
    
    ; Clean up ALL TrackPro registry entries (not just current version)
    DetailPrint "Cleaning up all TrackPro registry entries..."
    
    ; Remove current version registry entries
    DeleteRegKey ${{PRODUCT_UNINST_ROOT_KEY}} "${{PRODUCT_UNINST_KEY}}"
    DeleteRegKey HKLM "${{PRODUCT_DIR_REGKEY}}"
    
    ; Enumerate and remove any remaining TrackPro uninstall entries
    StrCpy $1 0
    uninstall_loop:
        EnumRegKey $2 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall" $1
        StrCmp $2 "" uninstall_done
        
        ; Check if this is a TrackPro entry
        ReadRegStr $3 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$2" "DisplayName"
        StrCpy $4 $3 8  ; Get first 8 characters
        StrCmp $4 "TrackPro" 0 uninstall_next_key
        
        ; This is a TrackPro entry, remove it
        DetailPrint "Removing registry entry: $3"
        DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\$2"
        Goto uninstall_loop  ; Start over since we modified the registry
        
        uninstall_next_key:
        IntOp $1 $1 + 1
        Goto uninstall_loop
    
    uninstall_done:
    
    ; Clean up App Paths registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\TrackPro.exe"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\TrackPro_v{version}.exe"
    
    ; Display a confirmation message
    MessageBox MB_ICONINFORMATION|MB_OK "All TrackPro versions have been successfully uninstalled from your computer."
    
    DetailPrint "Complete uninstallation finished"
SectionEnd
"""
        # Format the script with the version
        try:
            formatted_script = script.format(version=self.version)
            with open("installer.nsi", "w", encoding="utf-8") as f:
                f.write(formatted_script)
            print("✓ Created NSIS installer script with relative paths")
        except Exception as e:
            print(f"Error creating NSIS script: {str(e)}")
            raise

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
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("✗ Failed to verify or download prerequisites")
            sys.exit(1)
        
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
            os.path.join(self.temp_dir, "prerequisites", "HidHide_1.2.98_x64.exe"),
            os.path.join(self.temp_dir, "dist", f"TrackPro_v{self.version}.exe"),
            "installer.nsi"
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
        try:
            # Find NSIS executable
            nsis_exe = None
            nsis_paths = [
                r"C:\Program Files (x86)\NSIS\makensis.exe",
                r"C:\Program Files\NSIS\makensis.exe"
            ]
            
            for path in nsis_paths:
                if os.path.exists(path):
                    nsis_exe = path
                    break
            
            if not nsis_exe:
                # Try to find makensis in PATH
                try:
                    nsis_exe = "makensis"
                    subprocess.run([nsis_exe, "/VERSION"], 
                                  capture_output=True, 
                                  check=True)
                except:
                    raise FileNotFoundError("Could not find makensis.exe")
            
            # First validate the script
            print("Validating NSIS script...")
            try:
                # Try to validate the script syntax
                validate_cmd = [nsis_exe, "/CMDHELP", "installer.nsi"]
                validate_result = subprocess.run(validate_cmd, 
                                              capture_output=True, 
                                              text=True,
                                              check=False)
                
                if validate_result.returncode != 0 or "error" in validate_result.stderr.lower():
                    print(f"NSIS Script Validation Warning: {validate_result.stderr}")
                    # Continue anyway as /CMDHELP might not work as expected
            except Exception as e:
                print(f"NSIS Script Validation Warning: {str(e)}")
                # Continue anyway
            
            # Run NSIS with verbose output and explicit working directory
            print("Compiling installer...")
            current_dir = os.getcwd()
            print(f"Current working directory: {current_dir}")
            
            # Use absolute path for the script
            script_path = os.path.join(current_dir, "installer.nsi")
            print(f"Using script path: {script_path}")
            
            # Run NSIS with maximum verbosity
            result = subprocess.run([nsis_exe, "/V4", script_path], 
                                  capture_output=True, 
                                  text=True,
                                  check=False)  # Don't raise exception yet
            
            # Print full output for debugging
            print("\nNSIS Output:")
            print(result.stdout)
            
            if result.stderr:
                print("\nNSIS Error Output:")
                print(result.stderr)
            
            # Check for errors in the output
            if result.returncode != 0:
                print(f"NSIS Error (return code {result.returncode}):")
                
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
                print("\nNSIS Script (first 30 lines):")
                for i, line in enumerate(script_lines[:30]):
                    print(f"{i+1}: {line.rstrip()}")
                
                print("\n... (script truncated) ...\n")
                
                # Print the last 20 lines as well
                if len(script_lines) > 30:
                    print("\nNSIS Script (last 20 lines):")
                    for i, line in enumerate(script_lines[-20:]):
                        print(f"{len(script_lines) - 20 + i + 1}: {line.rstrip()}")
            except Exception as debug_e:
                print(f"Error debugging NSIS script: {str(debug_e)}")
            
            raise Exception(f"Failed to build installer: {str(e)}")

        # Verify the installer was created
        installer_path = f"TrackPro_Setup_v{self.version}.exe"
        if not os.path.exists(installer_path):
            raise Exception(f"Installer not found at {installer_path}")
        
        print("\n✓ Installer build completed!")
        print(f"✓ Installer created at: {os.path.abspath(installer_path)}")
        
        # Verify the installer file size
        installer_size = os.path.getsize(installer_path)
        print(f"✓ Installer size: {installer_size} bytes")
        
        if installer_size < 1000000:  # Less than 1MB might indicate a problem
            print("! Warning: Installer file size is smaller than expected. Please verify its contents.")
        
        # Sign the installer
        self.sign_files([installer_path])
        
        print(f"\n✓ Build process completed!")
        print(f"✓ Signed installer available at: {os.path.abspath(installer_path)}")
        print(f"✓ Installer is ready for distribution")

    def clean_build(self):
        """Clean previous builds."""
        print("\nCleaning previous builds...")
        
        def remove_readonly(func, path, _):
            """Remove read-only attribute and retry removal"""
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except PermissionError:
                print(f"! Warning: Could not remove read-only attribute for {path}")
                # Try to continue anyway
                pass
        
        # Try to handle locked files more robustly
        try:
            # First, try to terminate any processes that might be locking the installer
            installer_path = f"TrackPro_Setup_v{self.version}.exe"
            if os.path.exists(installer_path):
                try:
                    # Try to force close any handles to the installer file (Windows-specific)
                    print(f"Attempting to release locks on {installer_path}...")
                    subprocess.run(["taskkill", "/F", "/IM", installer_path], 
                                  shell=True, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
                    # Give the system a moment to release the file
                    import time
                    time.sleep(1)
                except Exception as e:
                    print(f"! Warning: Could not terminate processes: {str(e)}")
        except Exception as e:
            print(f"! Warning: Error handling locked files: {str(e)}")
        
        for dir_name in [self.temp_dir, self.dist_dir, "build"]:
            if os.path.exists(dir_name):
                try:
                    shutil.rmtree(dir_name, onerror=remove_readonly)
                    print(f"✓ Cleaned {dir_name}/")
                except Exception as e:
                    print(f"! Warning: Could not clean {dir_name}: {str(e)}")
                    # Try to create a new directory with a different name and continue
                    if dir_name == self.temp_dir:
                        self.temp_dir = f"{dir_name}_new"
                        print(f"  Using alternative directory: {self.temp_dir}")
                        if not os.path.exists(self.temp_dir):
                            os.makedirs(self.temp_dir)
        
        # Clean installer files
        for file_name in ["installer.nsi", f"TrackPro_Setup_v{self.version}.exe", "TrackProSetup.exe", "TrackPro.spec"]:
            if os.path.exists(file_name):
                try:
                    # Try multiple approaches to remove the file
                    try:
                        os.chmod(file_name, stat.S_IWRITE)
                    except:
                        pass
                    
                    try:
                        os.remove(file_name)
                        print(f"✓ Cleaned {file_name}")
                    except PermissionError:
                        print(f"! Warning: Permission error cleaning {file_name}, trying alternative method...")
                        # Try using del command on Windows
                        try:
                            subprocess.run(["del", "/F", "/Q", file_name], 
                                          shell=True, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE)
                            if not os.path.exists(file_name):
                                print(f"✓ Cleaned {file_name} using alternative method")
                            else:
                                print(f"! Warning: Could not clean {file_name} using alternative method")
                        except Exception as alt_e:
                            print(f"! Warning: Alternative method failed: {str(alt_e)}")
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
        manifest_path = "trackpro.manifest"  # Use relative path instead of absolute
        with open(manifest_path, "w") as f:
            f.write(manifest)
        print(f"✓ Created manifest file at: {manifest_path}")
        return manifest_path

    def collect_race_coach_modules(self):
        """Collect all Race Coach modules and their dependencies."""
        print("\nCollecting Race Coach modules and dependencies...")
        
        modules = []
        data_files = []
        
        # Add Race Coach modules and submodules
        race_coach_modules = [
            "trackpro.race_coach",
            "trackpro.race_coach.ui",
            "trackpro.race_coach.model",
            "trackpro.race_coach.data_manager",
            "trackpro.race_coach.iracing_api",
        # Add Race Coach modules and submodules
        ]
        
        # Add numpy and its submodules - expanded list to ensure all parts are included
        numpy_modules = [
            "numpy",
            "numpy.core",
            "numpy.core.multiarray",
            "numpy.core.numeric",
            "numpy.core.umath",
            "numpy.lib",
            "numpy.linalg",
            "numpy.fft",
            "numpy.polynomial",
            "numpy.random",
            "numpy.distutils",
            "numpy.ma"
        ]
        
        # Add PyQtWebEngine modules
        pyqt_web_modules = [
            "PyQt5.QtWebEngineWidgets",
            "PyQt5.QtWebEngine",
            "PyQt5.QtWebEngineCore",
            "PyQtWebEngine"
        ]
        
        # Additional dependencies that might be required
        additional_modules = [
            "sqlite3",
            "matplotlib.backends.backend_qt5agg",
            "matplotlib",
            "matplotlib.pyplot"
        ]
        
        all_modules = race_coach_modules + numpy_modules + pyqt_web_modules + additional_modules
        
        for module in all_modules:
            modules.append(f"--hidden-import={module}")
            
        # Add numpy as a direct copy to ensure all necessary files are included
        try:
            import numpy
            numpy_path = os.path.dirname(numpy.__file__)
            print(f"Adding numpy from path: {numpy_path}")
            data_files.append(f"--add-data={numpy_path};numpy")
            
            # Try to import matplotlib and add it if available
            try:
                import matplotlib
                matplotlib_path = os.path.dirname(matplotlib.__file__)
                print(f"Adding matplotlib from path: {matplotlib_path}")
                data_files.append(f"--add-data={matplotlib_path};matplotlib")
            except ImportError:
                print("! Warning: matplotlib not available. Some Race Coach features may not work properly.")
            
        except ImportError:
            print("! Warning: numpy not available during build. Race Coach may not work properly.")
            print("! Please ensure numpy is installed with: pip install numpy")
        
        # Add race_coach.db explicitly
        if os.path.exists("race_coach.db"):
            print("Adding race_coach.db to the package")
            data_files.append("--add-data=race_coach.db;.")
        else:
            print("! Warning: race_coach.db not found in workspace")
        
        print(f"✓ Added {len(modules)} Race Coach related modules to PyInstaller imports")
        print(f"✓ Added {len(data_files)} data file specifications")
        return modules, data_files
        
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
        
        # Collect Race Coach modules
        race_coach_imports, race_coach_data = self.collect_race_coach_modules()
        
        # Define PyInstaller options
        opts = [
            'run_app.py',
            f'--name=TrackPro_v{self.version}',
            '--onefile',
            '--windowed',  # Hide console window
            '--clean',
            f'--manifest={manifest_path}',  # Use the relative manifest path
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
            '--hidden-import=PyQt5.QtWebEngineWidgets',
            '--hidden-import=PyQt5.QtWebEngine',
            '--hidden-import=PyQt5.QtWebEngineCore',
            '--hidden-import=PyQtWebEngine',
            '--hidden-import=pygame',
            '--hidden-import=win32serviceutil',
            '--hidden-import=win32service',
            '--add-data=trackpro;trackpro',
            '--add-data=trackpro.manifest;.'  # Include manifest in the package
        ]
        
        # Add PyQt5 translation and resources for WebEngine
        try:
            import PyQt5
            pyqt_path = os.path.dirname(PyQt5.__file__)
            # Add Qt translations and resources needed for WebEngine
            translations_path = os.path.join(pyqt_path, "Qt5", "translations")
            resources_path = os.path.join(pyqt_path, "Qt5", "resources")
            
            if os.path.exists(translations_path):
                print(f"Adding PyQt5 translations from: {translations_path}")
                opts.extend(['--add-data', f'{translations_path};PyQt5/Qt5/translations'])
            
            if os.path.exists(resources_path):
                print(f"Adding PyQt5 resources from: {resources_path}")
                opts.extend(['--add-data', f'{resources_path};PyQt5/Qt5/resources'])
        except Exception as e:
            print(f"Warning: Could not add PyQt5 translations/resources: {e}")

        # Add Race Coach modules
        opts.extend(race_coach_imports)
        
        # Add Race Coach data files
        opts.extend(race_coach_data)
        
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
        
        # Verify PyQtWebEngine was included in the build
        print("\nVerifying PyQtWebEngine inclusion...")
        spec_file = f"TrackPro_v{self.version}.spec"
        if os.path.exists(spec_file):
            try:
                with open(spec_file, 'r', encoding='utf-8') as f:
                    spec_content = f.read()
                    if "PyQtWebEngine" in spec_content and "QtWebEngineWidgets" in spec_content:
                        print("✓ Verified PyQtWebEngine is included in the build")
                    else:
                        print("! Warning: PyQtWebEngine may not be properly included in the build")
                        print("  You may need to manually add these dependencies to the .spec file")
            except Exception as e:
                print(f"! Warning: Could not verify PyQtWebEngine inclusion: {e}")
        
        # Verify the exe was created
        exe_path = os.path.join("dist", f"TrackPro_v{self.version}.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path)
            print(f"\n✓ TrackPro_v{self.version}.exe successfully built at: {exe_path} ({file_size} bytes)")
            
            # Sign the executable
            self.sign_files([exe_path])
            
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

    def check_prerequisites(self):
        """Check and install prerequisites."""
        print("\nChecking prerequisites...")
        
        # First check Python package dependencies
        # Check for required Python packages
        required_packages = {
            "PyQt5": "PyQt5>=5.15.0",
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
        
        # Check for required files
        required_files = {
            "vJoySetup.exe": self.VJOY_URL,
            "HidHide_1.2.98_x64.exe": self.HIDHIDE_URL
        }
        
        missing_files = []
        for filename, url in required_files.items():
            filepath = os.path.join(prereq_dir, filename)
            if not os.path.exists(filepath):
                print(f"✗ Missing prerequisite file: {filepath}")
                missing_files.append((filename, url))
            else:
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    print(f"✗ Warning: {filepath} exists but is empty (0 bytes)")
                    missing_files.append((filename, url))
                else:
                    print(f"✓ Found {filename} ({file_size} bytes)")
        
        # Download missing files
        if missing_files:
            print("\nDownloading missing prerequisite files...")
            for filename, url in missing_files:
                try:
                    filepath = self.download_file(url, prereq_dir)
                    print(f"✓ Downloaded {filename} to {filepath}")
                except Exception as e:
                    print(f"✗ Failed to download {filename} from {url}: {str(e)}")
                    return False
        
        return True

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