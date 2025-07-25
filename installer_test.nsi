
; Enhanced installer for TrackPro with better error handling and fallback mechanisms

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v1.5.3"
OutFile "TrackPro_Setup_v1.5.3_Enhanced.exe"

; Try multiple installation paths in order of preference
!define PREFERRED_INSTDIR "$LOCALAPPDATA\TrackPro"
!define FALLBACK1_INSTDIR "$APPDATA\TrackPro"
!define FALLBACK2_INSTDIR "$TEMP\TrackPro"
!define FALLBACK3_INSTDIR "$DESKTOP\TrackPro"

InstallDir "${PREFERRED_INSTDIR}"
RequestExecutionLevel user

; Enhanced install details
ShowInstDetails show
ShowUnInstDetails show

; Define application metadata
!define PRODUCT_NAME "TrackPro"
!define PRODUCT_VERSION "1.5.3"
!define PRODUCT_PUBLISHER "TrackPro"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

!define MUI_ABORTWARNING

; Custom function to detect antivirus interference
!define ANTIVIRUS_DETECTION_TIMEOUT 10

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

; Global variables
Var ACTUAL_INSTDIR
Var ANTIVIRUS_DETECTED
Var PERMISSION_ISSUE

Function .onInit
    DetailPrint "=== TrackPro Enhanced Installation Started ==="
    
    ; Initialize variables
    StrCpy $ANTIVIRUS_DETECTED "false"
    StrCpy $PERMISSION_ISSUE "false"
    
    ; Kill any existing TrackPro processes
    DetailPrint "Terminating existing TrackPro processes..."
    ExecWait 'taskkill /F /IM "TrackPro*.exe" /T' $0
    ${If} $0 == 0
        DetailPrint "Existing processes terminated successfully"
    ${Else}
        DetailPrint "No existing processes found or termination failed (this is usually normal)"
    ${EndIf}
    
    ; Run antivirus detection
    Call DetectAntivirusInterference
    
    ; Test write permissions to preferred directory
    Call TestInstallationPaths
FunctionEnd

; Function to detect potential antivirus interference
Function DetectAntivirusInterference
    DetailPrint "Checking for potential antivirus interference..."
    
    ; Check Windows Defender status
    nsExec::ExecToStack 'powershell -Command "Get-MpComputerStatus | Select-Object -Property AntivirusEnabled" 2>nul'
    Pop $0 ; Return code
    Pop $1 ; Output
    
    ${If} $0 == 0
        ${If} ${StrLoc} $1 "True" 0
            DetailPrint "Windows Defender detected as active"
            StrCpy $ANTIVIRUS_DETECTED "true"
        ${Else}
            DetailPrint "Windows Defender status: Unknown or disabled"
        ${EndIf}
    ${Else}
        DetailPrint "Could not check Windows Defender status"
    ${EndIf}
    
    ; Check for common antivirus processes
    DetailPrint "Scanning for common antivirus processes..."
    nsExec::ExecToStack 'tasklist /FI "IMAGENAME eq avp.exe" /FO CSV 2>nul | find "avp.exe"'
    Pop $0
    ${If} $0 == 0
        DetailPrint "Kaspersky antivirus detected"
        StrCpy $ANTIVIRUS_DETECTED "true"
    ${EndIf}
    
    nsExec::ExecToStack 'tasklist /FI "IMAGENAME eq avgui.exe" /FO CSV 2>nul | find "avgui.exe"'
    Pop $0
    ${If} $0 == 0
        DetailPrint "AVG antivirus detected"
        StrCpy $ANTIVIRUS_DETECTED "true"
    ${EndIf}
    
    nsExec::ExecToStack 'tasklist /FI "IMAGENAME eq mcshield.exe" /FO CSV 2>nul | find "mcshield.exe"'
    Pop $0
    ${If} $0 == 0
        DetailPrint "McAfee antivirus detected"
        StrCpy $ANTIVIRUS_DETECTED "true"
    ${EndIf}
    
    ${If} $ANTIVIRUS_DETECTED == "true"
        DetailPrint "WARNING: Active antivirus detected - may interfere with installation"
    ${Else}
        DetailPrint "No major antivirus interference detected"
    ${EndIf}
FunctionEnd

; Function to test installation paths and find the best option
Function TestInstallationPaths
    DetailPrint "Testing installation paths for write permissions..."
    
    ; Test preferred path
    DetailPrint "Testing preferred path: ${PREFERRED_INSTDIR}"
    StrCpy $INSTDIR "${PREFERRED_INSTDIR}"
    Call TestWritePermission
    ${If} $PERMISSION_ISSUE == "false"
        StrCpy $ACTUAL_INSTDIR "${PREFERRED_INSTDIR}"
        DetailPrint "✓ Preferred path is accessible"
        Return
    ${EndIf}
    
    ; Test fallback 1
    DetailPrint "Testing fallback path 1: ${FALLBACK1_INSTDIR}"
    StrCpy $INSTDIR "${FALLBACK1_INSTDIR}"
    Call TestWritePermission
    ${If} $PERMISSION_ISSUE == "false"
        StrCpy $ACTUAL_INSTDIR "${FALLBACK1_INSTDIR}"
        DetailPrint "✓ Using fallback path 1"
        Return
    ${EndIf}
    
    ; Test fallback 2
    DetailPrint "Testing fallback path 2: ${FALLBACK2_INSTDIR}"
    StrCpy $INSTDIR "${FALLBACK2_INSTDIR}"
    Call TestWritePermission
    ${If} $PERMISSION_ISSUE == "false"
        StrCpy $ACTUAL_INSTDIR "${FALLBACK2_INSTDIR}"
        DetailPrint "✓ Using fallback path 2 (temporary location)"
        Return
    ${EndIf}
    
    ; Test fallback 3 (desktop)
    DetailPrint "Testing fallback path 3: ${FALLBACK3_INSTDIR}"
    StrCpy $INSTDIR "${FALLBACK3_INSTDIR}"
    Call TestWritePermission
    ${If} $PERMISSION_ISSUE == "false"
        StrCpy $ACTUAL_INSTDIR "${FALLBACK3_INSTDIR}"
        DetailPrint "✓ Using fallback path 3 (desktop)"
        Return
    ${EndIf}
    
    ; All paths failed
    DetailPrint "ERROR: All installation paths failed permission tests"
    MessageBox MB_OK|MB_ICONSTOP "Installation Error$\n$\nCannot find a writable location for TrackPro installation.$\n$\nThis is usually caused by:$\n• Antivirus software blocking the installer$\n• Corrupted user permissions$\n• Insufficient disk space$\n$\nSolutions:$\n• Run installer as Administrator$\n• Temporarily disable antivirus$\n• Free up disk space$\n• Contact support for assistance"
    Abort
FunctionEnd

; Function to test write permission to current $INSTDIR
Function TestWritePermission
    StrCpy $PERMISSION_ISSUE "false"
    
    ; Create test directory
    CreateDirectory "$INSTDIR"
    ${IfNot} ${FileExists} "$INSTDIR"
        DetailPrint "Cannot create directory: $INSTDIR"
        StrCpy $PERMISSION_ISSUE "true"
        Return
    ${EndIf}
    
    ; Test file write
    FileOpen $0 "$INSTDIR\test_write.tmp" w
    ${If} $0 == ""
        DetailPrint "Cannot write test file to: $INSTDIR"
        StrCpy $PERMISSION_ISSUE "true"
        Return
    ${EndIf}
    
    FileWrite $0 "test"
    FileClose $0
    
    ; Test file read
    ${IfNot} ${FileExists} "$INSTDIR\test_write.tmp"
        DetailPrint "Test file was not created in: $INSTDIR"
        StrCpy $PERMISSION_ISSUE "true"
        Return
    ${EndIf}
    
    ; Cleanup
    Delete "$INSTDIR\test_write.tmp"
    DetailPrint "Write permission test passed for: $INSTDIR"
FunctionEnd

Section "MainProgram"
    DetailPrint "=== Installing TrackPro ==="
    
    ; Set the final installation directory
    StrCpy $INSTDIR $ACTUAL_INSTDIR
    DetailPrint "Final installation directory: $INSTDIR"
    
    ; Ensure directory exists
    CreateDirectory "$INSTDIR"
    ${IfNot} ${FileExists} "$INSTDIR"
        DetailPrint "CRITICAL ERROR: Cannot create final installation directory"
        
        ; Show detailed error message
        ${If} $ANTIVIRUS_DETECTED == "true"
            MessageBox MB_OK|MB_ICONSTOP "Installation Failed$\n$\nAntivirus software is blocking the installation.$\n$\nSolutions:$\n• Temporarily disable antivirus during installation$\n• Add installer to antivirus exclusions$\n• Run installer as Administrator$\n$\nDirectory: $INSTDIR"
        ${Else}
            MessageBox MB_OK|MB_ICONSTOP "Installation Failed$\n$\nCannot create installation directory.$\n$\nThis may be due to:$\n• Insufficient permissions$\n• Disk space issues$\n• Windows security restrictions$\n$\nDirectory: $INSTDIR"
        ${EndIf}
        Abort
    ${EndIf}
    
    ; Set output path
    SetOutPath "$INSTDIR"
    
    ; Install main executable with retry mechanism
    DetailPrint "Installing TrackPro executable..."
    
    ; Retry file installation up to 3 times
    StrCpy $0 0
    retry_install:
        File "installer_temp\dist\TrackPro_v1.5.3.exe"
        
        ; Verify installation
        ${If} ${FileExists} "$INSTDIR\TrackPro_v1.5.3.exe"
            DetailPrint "✓ TrackPro executable installed successfully"
            Goto install_success
        ${EndIf}
        
        ; Retry logic
        IntOp $0 $0 + 1
        ${If} $0 <= 3
            DetailPrint "Installation attempt $0 failed, retrying in 2 seconds..."
            Sleep 2000
            Goto retry_install
        ${Else}
            DetailPrint "CRITICAL ERROR: Failed to install executable after 3 attempts"
            
            ${If} $ANTIVIRUS_DETECTED == "true"
                MessageBox MB_OK|MB_ICONSTOP "Installation Failed$\n$\nThe executable could not be installed after multiple attempts.$\n$\nThis is typically caused by antivirus software.$\n$\nSolutions:$\n• Temporarily disable real-time protection$\n• Add TrackPro to antivirus exclusions$\n• Try running installer as Administrator"
            ${Else}
                MessageBox MB_OK|MB_ICONSTOP "Installation Failed$\n$\nThe executable could not be installed.$\n$\nPossible causes:$\n• Insufficient disk space$\n• File corruption during download$\n• Windows security restrictions$\n$\nTry downloading the installer again."
            ${EndIf}
            Abort
        ${EndIf}
    
    install_success:
    
    ; Create shortcuts with error handling
    DetailPrint "Creating application shortcuts..."
    
    ClearErrors
    CreateDirectory "$SMPROGRAMS\TrackPro"
    ${If} ${Errors}
        DetailPrint "Warning: Could not create Start Menu folder"
    ${Else}
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v1.5.3.lnk" "$INSTDIR\TrackPro_v1.5.3.exe"
        ${If} ${Errors}
            DetailPrint "Warning: Could not create Start Menu shortcut"
        ${Else}
            DetailPrint "✓ Start Menu shortcut created"
        ${EndIf}
    ${EndIf}
    
    ClearErrors
    CreateShortCut "$DESKTOP\TrackPro v1.5.3.lnk" "$INSTDIR\TrackPro_v1.5.3.exe"
    ${If} ${Errors}
        DetailPrint "Warning: Could not create Desktop shortcut"
    ${Else}
        DetailPrint "✓ Desktop shortcut created"
    ${EndIf}
    
    ; Create uninstaller
    DetailPrint "Creating uninstaller..."
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Register application (optional - may fail on some systems)
    ClearErrors
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "TrackPro v1.5.3"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\TrackPro_v1.5.3.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    
    ${If} ${Errors}
        DetailPrint "Note: Could not register application (this is not critical)"
    ${Else}
        DetailPrint "✓ Application registered successfully"
    ${EndIf}
    
    ; Final success message
    DetailPrint "=== Installation Completed Successfully ==="
    
    ${If} $ANTIVIRUS_DETECTED == "true"
        MessageBox MB_OK|MB_ICONINFORMATION "TrackPro v1.5.3 installed successfully!$\n$\nLocation: $INSTDIR$\n$\nNote: Antivirus software was detected. If TrackPro has issues starting, you may need to add it to your antivirus exclusions.$\n$\nFor best performance, add the entire TrackPro folder to your antivirus exclusions."
    ${Else}
        MessageBox MB_OK|MB_ICONINFORMATION "TrackPro v1.5.3 installed successfully!$\n$\nLocation: $INSTDIR$\n$\nYou can now launch TrackPro from your Desktop or Start Menu."
    ${EndIf}
SectionEnd

Section "Uninstall"
    DetailPrint "=== Uninstalling TrackPro ==="
    
    ; Remove files
    Delete "$INSTDIR\TrackPro_v1.5.3.exe"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\TrackPro\TrackPro v1.5.3.lnk"
    Delete "$DESKTOP\TrackPro v1.5.3.lnk"
    RMDir "$SMPROGRAMS\TrackPro"
    
    ; Remove registry entries
    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
    
    ; Remove installation directory
    RMDir "$INSTDIR"
    
    DetailPrint "=== Uninstallation completed ==="
SectionEnd
        