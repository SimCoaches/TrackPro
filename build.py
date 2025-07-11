#!/usr/bin/env python3
import sys
import os
import subprocess
import time

# Ensure we're using Python 3.11 for building (critical for eye tracking support)
if sys.version_info[:2] != (3, 11):
    print(f"TrackPro build requires Python 3.11 for eye tracking support.")
    print(f"Current version: Python {sys.version_info.major}.{sys.version_info.minor}")
    print("Restarting build with Python 3.11...")
    
    try:
        # Use py -3.11 to explicitly run with Python 3.11
        result = subprocess.run([
            "py", "-3.11", __file__
        ] + sys.argv[1:], check=True)
        sys.exit(result.returncode)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Failed to start build with Python 3.11: {e}")
        print("Please install Python 3.11 or ensure it's available via 'py -3.11'")
        sys.exit(1)

print(f"✓ Building with Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

import PyInstaller.__main__
import shutil
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
    VCREDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"  # Latest Visual C++ Redistributable
    
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
; Installer script for TrackPro - Fixed version to eliminate black command boxes and hanging

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v{version}"
OutFile "TrackPro_Setup_v{version}.exe"
InstallDir "$LOCALAPPDATA\TrackPro"
RequestExecutionLevel user ; Request user rights (not admin)

; Define application metadata for Add/Remove Programs
!define PRODUCT_NAME "TrackPro"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "TrackPro"
!define PRODUCT_WEB_SITE "https://github.com/Trackpro-dev/TrackPro"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\TrackPro_v{version}.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{PRODUCT_NAME}}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

!define MUI_ABORTWARNING
!define MUI_ICON "${{NSISDIR}}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${{NSISDIR}}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Show installation details for better debugging
ShowInstDetails show
ShowUnInstDetails show

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

Var NEEDS_RESTART
Var INSTALL_STATUS

Function .onInit
    StrCpy $NEEDS_RESTART "0"
    StrCpy $INSTALL_STATUS "NORMAL"
    
    ; Kill any existing TrackPro processes silently (no black boxes)
    DetailPrint "Checking for running TrackPro processes..."
    nsExec::ExecToLog 'taskkill /F /IM "TrackPro*.exe" /T 2>nul'
    Pop $0
    ${{If}} $0 == 0
        DetailPrint "Terminated existing TrackPro processes"
    ${{Else}}
        DetailPrint "No TrackPro processes found"
    ${{EndIf}}
    
    ; Clean up previous TrackPro installations
    Call CleanupPreviousVersions
FunctionEnd

Function CleanupPreviousVersions
    DetailPrint "Checking for previous TrackPro installations..."
    DetailPrint "NOTE: User data (calibrations, settings) will be preserved"
    
    ; Remove all TrackPro executables from Program Files
    DetailPrint "Removing previous TrackPro executables..."
    Delete "$PROGRAMFILES64\TrackPro\TrackPro*.exe"
    Delete "$PROGRAMFILES64\TrackPro\TrackPro_v*.exe"
    Delete "$PROGRAMFILES32\TrackPro\TrackPro*.exe"
    Delete "$PROGRAMFILES32\TrackPro\TrackPro_v*.exe"
    
    ; Remove all TrackPro shortcuts
    DetailPrint "Removing previous TrackPro shortcuts..."
    Delete "$SMPROGRAMS\TrackPro\TrackPro*.lnk"
    Delete "$SMPROGRAMS\TrackPro\TrackPro v*.lnk"
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

; Function to install prerequisites with timeout and error handling
Function InstallPrerequisiteWithTimeout
    Pop $R0 ; Command to execute
    Pop $R1 ; Description
    Pop $R2 ; Timeout in seconds
    
    DetailPrint "Installing $R1..."
    
    ; Execute with timeout using nsExec (no black boxes)
    nsExec::ExecToLog '$R0'
    Pop $R3 ; Exit code
    
    ; Check result
    ${{If}} $R3 == 0
        DetailPrint "$R1 installed successfully"
    ${{ElseIf}} $R3 == 3010
        DetailPrint "$R1 installed successfully, restart required"
        StrCpy $NEEDS_RESTART "1"
    ${{ElseIf}} $R3 == 1618
        DetailPrint "$R1 already installed (up to date)"
    ${{ElseIf}} $R3 == 1638
        DetailPrint "$R1 already installed (newer version)"
    ${{ElseIf}} $R3 == -1
        DetailPrint "Warning: $R1 installation timed out or failed"
        DetailPrint "TrackPro may still work without this component"
    ${{Else}}
        DetailPrint "Warning: $R1 installation failed with exit code: $R3"
        DetailPrint "TrackPro may still work without this component"
    ${{EndIf}}
    
    Push $R3 ; Return exit code
FunctionEnd

Section "MainInstallation"
    ; Create temp directories with verification
    DetailPrint "Setting up installation environment..."
    CreateDirectory "$TEMP\TrackPro"
    CreateDirectory "$TEMP\TrackPro\prerequisites"
    CreateDirectory "$TEMP\TrackPro\app"
    
    SetOutPath "$TEMP\TrackPro\prerequisites"
    DetailPrint "Extracting prerequisites..."
    
    ; Extract prerequisite installers using relative paths
    File "installer_temp\prerequisites\vJoySetup.exe"
    File "installer_temp\prerequisites\HidHide_1.2.98_x64.exe"
    File "installer_temp\prerequisites\vc_redist.x64.exe"
    
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
    DetailPrint "Creating installation directory: $INSTDIR"
    CreateDirectory "$INSTDIR"
    
    ; Check if directory was created successfully
    ${{IfNot}} ${{FileExists}} "$INSTDIR"
        MessageBox MB_OK|MB_ICONSTOP "Failed to create installation directory!"
        Abort "Installation failed: Could not create installation directory"
    ${{EndIf}}
    
    ; Set working directory to installation directory
    SetOutPath "$INSTDIR"
    
    ; Install TrackPro with explicit verification and better error handling
    DetailPrint "Installing TrackPro application..."
    
    ; Check if destination file already exists and try to remove it
    ${{If}} ${{FileExists}} "$INSTDIR\TrackPro_v{version}.exe"
        DetailPrint "Removing existing installation file..."
        Delete "$INSTDIR\TrackPro_v{version}.exe"
    ${{EndIf}}
    
    ; Clear any previous errors and copy the file
    ClearErrors
    CopyFiles /SILENT "$TEMP\TrackPro\app\TrackPro_v{version}.exe" "$INSTDIR"
    
    ; Check for copy errors
    ${{If}} ${{Errors}}
        MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v{version}.exe to installation directory!"
        Abort "Installation failed: Could not copy TrackPro_v{version}.exe"
    ${{EndIf}}
    
    ; Verify TrackPro.exe exists in the destination
    ${{IfNot}} ${{FileExists}} "$INSTDIR\TrackPro_v{version}.exe"
        MessageBox MB_OK|MB_ICONSTOP "Failed to verify TrackPro_v{version}.exe in installation directory!"
        Abort "Installation failed: Could not verify TrackPro_v{version}.exe"
    ${{EndIf}}
        
    ; Create shortcuts with verification
    DetailPrint "Creating shortcuts..."
    CreateDirectory "$SMPROGRAMS\TrackPro"
    CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v{version}.lnk" "$INSTDIR\TrackPro_v{version}.exe"
    CreateShortCut "$DESKTOP\TrackPro v{version}.lnk" "$INSTDIR\TrackPro_v{version}.exe"
    
    DetailPrint "TrackPro application installation complete"

    ; Install Visual C++ Redistributable (no black boxes)
    Push '"$TEMP\TrackPro\prerequisites\vc_redist.x64.exe" /quiet /norestart'
    Push "Visual C++ Redistributable"
    Push "60"
    Call InstallPrerequisiteWithTimeout
    Pop $2

    ; Install HidHide (no black boxes) 
    Push '"$TEMP\TrackPro\prerequisites\HidHide_1.2.98_x64.exe" /quiet /norestart'
    Push "HidHide"
    Push "60"
    Call InstallPrerequisiteWithTimeout
    Pop $1

    ; Check if vJoy is already installed before attempting installation
    DetailPrint "Checking for existing vJoy installation..."
    
    ; Check registry for vJoy
    ReadRegStr $R0 HKLM "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}}_is1" "DisplayName"
    ${{If}} $R0 != ""
        DetailPrint "Found existing vJoy installation: $R0"
        DetailPrint "Skipping vJoy installation to prevent conflicts"
        Goto vjoy_done
    ${{EndIf}}
    
    ; Check for vJoy files in common locations
    ${{If}} ${{FileExists}} "$PROGRAMFILES64\vJoy\x64\vJoyInterface.dll"
        DetailPrint "Found existing vJoy files in Program Files"
        DetailPrint "Skipping vJoy installation to prevent conflicts"
        Goto vjoy_done
    ${{EndIf}}
    
    ${{If}} ${{FileExists}} "$PROGRAMFILES32\vJoy\x86\vJoyInterface.dll"
        DetailPrint "Found existing vJoy files in Program Files (x86)"
        DetailPrint "Skipping vJoy installation to prevent conflicts"
        Goto vjoy_done
    ${{EndIf}}

    ; Install vJoy with better error handling (no black boxes)
    Push '"$TEMP\TrackPro\prerequisites\vJoySetup.exe" /SILENT /SUPPRESSMSGBOXES /NORESTART'
    Push "vJoy Virtual Joystick"
    Push "120"
    Call InstallPrerequisiteWithTimeout
    Pop $0
    
    ; If silent installation failed, try alternative method
    ${{If}} $0 != 0
    ${{AndIf}} $0 != 3010
    ${{AndIf}} $0 != 1618
    ${{AndIf}} $0 != 1638
        DetailPrint "Trying alternative vJoy installation method..."
        Push '"$TEMP\TrackPro\prerequisites\vJoySetup.exe" /S'
        Push "vJoy Virtual Joystick (Alternative Method)"
        Push "120"
        Call InstallPrerequisiteWithTimeout
        Pop $0
        
        ${{If}} $0 != 0
        ${{AndIf}} $0 != 3010
        ${{AndIf}} $0 != 1618
        ${{AndIf}} $0 != 1638
            DetailPrint "vJoy installation failed with both methods"
            MessageBox MB_OK|MB_ICONINFORMATION "vJoy installation failed. TrackPro will work in test mode without virtual joystick support."
        ${{EndIf}}
    ${{EndIf}}
    
    vjoy_done:
    DetailPrint "Prerequisites installation phase completed"

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

    ; Show installation completion message
    DetailPrint "Installation completed successfully!"
    
    ; Check if we need to restart
    ${{If}} $NEEDS_RESTART == "1"
        MessageBox MB_YESNO|MB_ICONQUESTION "A system restart is required to complete the installation. Would you like to restart now?" IDNO +2
            Reboot
    ${{EndIf}}
SectionEnd

Section "Uninstall"
    ; Terminate any running TrackPro processes first (no black boxes)
    DetailPrint "Checking for running TrackPro processes..."
    nsExec::ExecToLog 'taskkill /F /IM "TrackPro*.exe" /T 2>nul'
    Pop $0
    ${{If}} $0 == 0
        DetailPrint "Terminated running TrackPro processes"
    ${{Else}}
        DetailPrint "No TrackPro processes found"
    ${{EndIf}}
    
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

    def create_test_installer_script(self):
        """Create a minimal test installer script without prerequisites."""
        print("\nCreating test installer script...")
        
        script = r"""
; Minimal test installer for TrackPro (no prerequisites)

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v{version} (Test)"
OutFile "TrackPro_Setup_v{version}_Test.exe"
InstallDir "$LOCALAPPDATA\TrackPro"
RequestExecutionLevel user

; Show details for debugging
ShowInstDetails show
ShowUnInstDetails show

; Define application metadata
!define PRODUCT_NAME "TrackPro"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "TrackPro"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{PRODUCT_NAME}}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

Function .onInit
    DetailPrint "Starting TrackPro test installation..."
    
    ; Kill any existing TrackPro processes
    DetailPrint "Terminating existing TrackPro processes..."
    ExecWait 'taskkill /F /IM "TrackPro*.exe" /T' $0
    DetailPrint "Process cleanup completed"
FunctionEnd

Section "MainProgram"
    DetailPrint "Installing TrackPro..."
    
    ; Create installation directory
    DetailPrint "Creating installation directory: $INSTDIR"
    CreateDirectory "$INSTDIR"
    
    ; Verify directory was created
    ${{IfNot}} ${{FileExists}} "$INSTDIR"
        DetailPrint "ERROR: Failed to create installation directory"
        MessageBox MB_OK|MB_ICONSTOP "Failed to create installation directory: $INSTDIR"
        Abort
    ${{EndIf}}
    
    ; Set output path
    SetOutPath "$INSTDIR"
    DetailPrint "Set output path to: $INSTDIR"
    
    ; Install main executable
    DetailPrint "Installing TrackPro executable..."
    File "installer_temp\dist\TrackPro_v{version}.exe"
    
    ; Verify file was installed
    ${{IfNot}} ${{FileExists}} "$INSTDIR\TrackPro_v{version}.exe"
        DetailPrint "ERROR: TrackPro executable not found after installation"
        MessageBox MB_OK|MB_ICONSTOP "Failed to install TrackPro executable"
        Abort
    ${{EndIf}}
    
    DetailPrint "TrackPro executable installed successfully"
    
    ; Create shortcuts
    DetailPrint "Creating shortcuts..."
    CreateDirectory "$SMPROGRAMS\TrackPro"
    CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v{version} (Test).lnk" "$INSTDIR\TrackPro_v{version}.exe"
    CreateShortCut "$DESKTOP\TrackPro v{version} (Test).lnk" "$INSTDIR\TrackPro_v{version}.exe"
    
    DetailPrint "Shortcuts created successfully"
    
    ; Create uninstaller
    DetailPrint "Creating uninstaller..."
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Register application
    WriteRegStr HKLM "${{PRODUCT_UNINST_KEY}}" "DisplayName" "TrackPro v{version} (Test)"
    WriteRegStr HKLM "${{PRODUCT_UNINST_KEY}}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${{PRODUCT_UNINST_KEY}}" "DisplayIcon" "$INSTDIR\TrackPro_v{version}.exe"
    WriteRegStr HKLM "${{PRODUCT_UNINST_KEY}}" "DisplayVersion" "${{PRODUCT_VERSION}}"
    WriteRegStr HKLM "${{PRODUCT_UNINST_KEY}}" "Publisher" "${{PRODUCT_PUBLISHER}}"
    
    DetailPrint "Registration completed"
    
    ; Show success message
    MessageBox MB_OK|MB_ICONINFORMATION "TrackPro v{version} test installation completed successfully!$\n$\nLocation: $INSTDIR"
    
    DetailPrint "Installation completed successfully!"
SectionEnd

Section "Uninstall"
    DetailPrint "Uninstalling TrackPro..."
    
    ; Remove files
    Delete "$INSTDIR\TrackPro_v{version}.exe"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\TrackPro\TrackPro v{version} (Test).lnk"
    Delete "$DESKTOP\TrackPro v{version} (Test).lnk"
    RMDir "$SMPROGRAMS\TrackPro"
    
    ; Remove registry entries
    DeleteRegKey HKLM "${{PRODUCT_UNINST_KEY}}"
    
    ; Remove installation directory
    RMDir "$INSTDIR"
    
    DetailPrint "Uninstallation completed"
SectionEnd
        """.format(version=self.version)
        
        with open("installer_test.nsi", "w", encoding="utf-8") as f:
            f.write(script)
        
        print("✓ Test installer script created: installer_test.nsi")
        return "installer_test.nsi"
    
    def build_test_installer(self):
        """Build a test installer without prerequisites."""
        print("\n=== Building Test Installer ===")
        
        # Kill any stuck processes first
        self.kill_stuck_processes()
        
        # Create temp directory and copy files
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        dist_temp = os.path.join(self.temp_dir, "dist")
        if not os.path.exists(dist_temp):
            os.makedirs(dist_temp)
        
        # Copy the main executable
        exe_name = f"TrackPro_v{self.version}.exe"
        src_exe = os.path.join(self.dist_dir, exe_name)
        dst_exe = os.path.join(dist_temp, exe_name)
        
        if os.path.exists(src_exe):
            shutil.copy2(src_exe, dst_exe)
            print(f"✓ Copied {exe_name} to installer temp")
        else:
            print(f"✗ Executable not found: {src_exe}")
            print("Please build the executable first with: python build.py")
            return False
        
        # Create test installer script
        nsis_script = self.create_test_installer_script()
        
        # Check NSIS
        if not self.check_nsis():
            return False
        
        # Build installer
        print("\nBuilding test installer...")
        try:
            result = subprocess.run([
                "makensis", 
                f"/V3",  # Verbose output
                nsis_script
            ], capture_output=True, text=True, cwd=self.cwd)
            
            if result.returncode == 0:
                print("✓ Test installer built successfully!")
                output_file = f"TrackPro_Setup_v{self.version}_Test.exe"
                print(f"✓ Test installer created: {output_file}")
                return True
            else:
                print(f"✗ NSIS build failed with exit code {result.returncode}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            print(f"✗ Error building test installer: {e}")
            return False

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
            os.path.join(self.temp_dir, "prerequisites", "HidHide_1.2.98_x64.exe"),
            os.path.join(self.temp_dir, "prerequisites", "vc_redist.x64.exe"),
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
        
        # Check if output file already exists and try to delete it
        installer_path = f"TrackPro_Setup_v{self.version}.exe"
        if os.path.exists(installer_path):
            print(f"Removing existing installer: {installer_path}")
            
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
                        raise Exception(f"Could not remove existing installer after {max_attempts} attempts: {e}")
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
        print("Checking for running TrackPro processes...")
        try:
            # Kill TrackPro processes
            result = subprocess.run(['taskkill', '/F', '/IM', 'TrackPro*.exe'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print("✓ Terminated running TrackPro processes")
            else:
                print("✓ No running TrackPro processes found")
            
            # Also check for installer processes
            installer_result = subprocess.run(['taskkill', '/F', '/IM', f'TrackPro_Setup_v{self.version}.exe'], 
                                            capture_output=True, text=True, check=False)
            if installer_result.returncode == 0:
                print("✓ Terminated running installer process")
                
        except Exception as e:
            print(f"Warning: Could not check for running processes: {e}")
        
        # Wait a moment for processes to fully terminate
        time.sleep(2)
        
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
            
            # Test NSIS first with a simple command
            print("Testing NSIS installation...")
            try:
                test_result = subprocess.run([nsis_exe, "/VERSION"], 
                                          capture_output=True, text=True, check=False)
                if test_result.returncode == 0:
                    print(f"✓ NSIS is working: {test_result.stdout.strip()}")
                else:
                    print(f"✗ NSIS test failed: {test_result.stderr}")
                    raise Exception(f"NSIS test failed: {test_result.stderr}")
            except Exception as e:
                print(f"✗ NSIS test failed: {e}")
                raise Exception(f"NSIS test failed: {e}")
            
            # Quick sanity check of the NSIS script
            print("Checking NSIS script...")
            try:
                with open("installer.nsi", 'r', encoding='utf-8') as f:
                    script_content = f.read()
                    if not script_content.strip():
                        print("✗ NSIS script is empty")
                        raise Exception("NSIS script is empty")
                    if "OutFile" not in script_content:
                        print("✗ NSIS script missing OutFile directive")
                        raise Exception("NSIS script missing OutFile directive")
                    print("✓ NSIS script appears valid")
            except Exception as e:
                print(f"✗ Could not read NSIS script: {e}")
                raise Exception(f"Could not read NSIS script: {e}")
            
            # Try creating a temporary file with the same name as the installer
            print("Testing installer filename...")
            try:
                temp_installer = f"temp_{installer_path}"
                with open(temp_installer, 'w') as f:
                    f.write("test")
                os.remove(temp_installer)
                print(f"✓ Can create files with installer name pattern")
            except Exception as e:
                print(f"✗ Cannot create installer filename: {e}")
                raise Exception(f"Cannot create installer filename: {e}")
            
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
        if not os.path.exists(installer_path):
            raise Exception(f"Installer not found at {installer_path}")
        
        print("\n✓ Installer build completed!")
        print(f"✓ Installer created at: {os.path.abspath(installer_path)}")
        
        # Verify the installer file size
        installer_size = os.path.getsize(installer_path)
        print(f"✓ Installer size: {installer_size:,} bytes")
        
        if installer_size < 1000000:  # Less than 1MB might indicate a problem
            print("! Warning: Installer file size is smaller than expected. Please verify its contents.")
        
        # Sign the installer
        self.sign_files([installer_path])
        
        print(f"\n✓ Build process completed!")
        print(f"✓ Signed installer available at: {os.path.abspath(installer_path)}")
        print(f"✓ Installer is ready for distribution")

    def clean_build(self):
        """Clean up build files and processes."""
        print("\n=== Cleaning Build Environment ===")
        
        # Kill any stuck installer processes first
        self.kill_stuck_processes()
        
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
    
    def kill_stuck_processes(self):
        """Kill any stuck TrackPro installer or setup processes."""
        print("\n=== Killing Stuck Processes ===")
        
        try:
            # Use PowerShell to find and kill stuck processes
            cmd = '''
            $processes = Get-Process | Where-Object {
                $_.ProcessName -like "*TrackPro*" -or 
                $_.ProcessName -like "*Setup*" -or 
                $_.ProcessName -like "*install*"
            }
            
            if ($processes) {
                $processes | ForEach-Object {
                    Write-Host "Killing process: $($_.ProcessName) (PID: $($_.Id))"
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                }
            } else {
                Write-Host "No stuck processes found"
            }
            '''
            
            result = subprocess.run([
                "powershell", "-Command", cmd
            ], capture_output=True, text=True, timeout=30)
            
            if result.stdout.strip():
                print(result.stdout.strip())
            if result.stderr.strip():
                print(f"Warning: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print("⚠️  Process cleanup timed out")
        except Exception as e:
            print(f"⚠️  Error during process cleanup: {e}")
        
        print("✓ Process cleanup completed")

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
            "PyQt6.QtWebEngineWidgets",
            "PyQt6.QtWebEngine",
            "PyQt6.QtWebEngineCore",
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
        
        # Check for required files
        required_files = {
            "vJoySetup.exe": self.VJOY_URL,
            "HidHide_1.2.98_x64.exe": self.HIDHIDE_URL,
            "vc_redist.x64.exe": self.VCREDIST_URL
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

    def manual_process_cleanup():
        """Utility function to manually clean up stuck processes."""
        print("=== Manual Process Cleanup ===")
        
        try:
            # Check for stuck processes
            cmd = '''
            $processes = Get-Process | Where-Object {
                $_.ProcessName -like "*TrackPro*" -or 
                $_.ProcessName -like "*Setup*" -or 
                $_.ProcessName -like "*install*"
            }
            
            if ($processes) {
                Write-Host "Found stuck processes:"
                $processes | ForEach-Object {
                    Write-Host "  - $($_.ProcessName) (PID: $($_.Id), CPU: $($_.CPU)s)"
                }
                
                $response = Read-Host "Kill these processes? (y/n)"
                if ($response -eq "y" -or $response -eq "Y") {
                    $processes | ForEach-Object {
                        Write-Host "Killing: $($_.ProcessName) (PID: $($_.Id))"
                        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                    }
                    Write-Host "Processes killed."
                } else {
                    Write-Host "No processes killed."
                }
            } else {
                Write-Host "No stuck processes found."
            }
            '''
            
            subprocess.run([
                "powershell", "-Command", cmd
            ], timeout=60)
            
        except Exception as e:
            print(f"Error during manual cleanup: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='TrackPro Build System')
    parser.add_argument('action', nargs='?', default='build', 
                       choices=['build', 'clean', 'kill-processes', 'test'],
                       help='Action to perform')
    parser.add_argument('--sign', action='store_true', 
                       help='Enable code signing')
    parser.add_argument('--no-sign', action='store_true', 
                       help='Disable code signing')
    
    args = parser.parse_args()
    
    if args.action == 'kill-processes':
        InstallerBuilder.manual_process_cleanup()
        sys.exit(0)
    
    builder = InstallerBuilder()
    
    # Override signing settings if specified
    if args.sign:
        builder.enable_signing = True
    elif args.no_sign:
        builder.enable_signing = False
    
    if args.action == 'clean':
        builder.clean_build()
    elif args.action == 'build':
        builder.build()
    elif args.action == 'test':
        builder.build_test_installer()
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1) 