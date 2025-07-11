
; Minimal test installer for TrackPro (no prerequisites)

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v1.5.2 (Test)"
OutFile "TrackPro_Setup_v1.5.2_Test.exe"
InstallDir "$LOCALAPPDATA\TrackPro"
RequestExecutionLevel user

; Show details for debugging
ShowInstDetails show
ShowUnInstDetails show

; Define application metadata
!define PRODUCT_NAME "TrackPro"
!define PRODUCT_VERSION "1.5.2"
!define PRODUCT_PUBLISHER "TrackPro"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
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
    ${IfNot} ${FileExists} "$INSTDIR"
        DetailPrint "ERROR: Failed to create installation directory"
        MessageBox MB_OK|MB_ICONSTOP "Failed to create installation directory: $INSTDIR"
        Abort
    ${EndIf}
    
    ; Set output path
    SetOutPath "$INSTDIR"
    DetailPrint "Set output path to: $INSTDIR"
    
    ; Install main executable
    DetailPrint "Installing TrackPro executable..."
    File "installer_temp\dist\TrackPro_v1.5.2.exe"
    
    ; Verify file was installed
    ${IfNot} ${FileExists} "$INSTDIR\TrackPro_v1.5.2.exe"
        DetailPrint "ERROR: TrackPro executable not found after installation"
        MessageBox MB_OK|MB_ICONSTOP "Failed to install TrackPro executable"
        Abort
    ${EndIf}
    
    DetailPrint "TrackPro executable installed successfully"
    
    ; Create shortcuts
    DetailPrint "Creating shortcuts..."
    CreateDirectory "$SMPROGRAMS\TrackPro"
    CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v1.5.2 (Test).lnk" "$INSTDIR\TrackPro_v1.5.2.exe"
    CreateShortCut "$DESKTOP\TrackPro v1.5.2 (Test).lnk" "$INSTDIR\TrackPro_v1.5.2.exe"
    
    DetailPrint "Shortcuts created successfully"
    
    ; Create uninstaller
    DetailPrint "Creating uninstaller..."
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Register application
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "TrackPro v1.5.2 (Test)"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\TrackPro_v1.5.2.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    
    DetailPrint "Registration completed"
    
    ; Show success message
    MessageBox MB_OK|MB_ICONINFORMATION "TrackPro v1.5.2 test installation completed successfully!$\n$\nLocation: $INSTDIR"
    
    DetailPrint "Installation completed successfully!"
SectionEnd

Section "Uninstall"
    DetailPrint "Uninstalling TrackPro..."
    
    ; Remove files
    Delete "$INSTDIR\TrackPro_v1.5.2.exe"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\TrackPro\TrackPro v1.5.2 (Test).lnk"
    Delete "$DESKTOP\TrackPro v1.5.2 (Test).lnk"
    RMDir "$SMPROGRAMS\TrackPro"
    
    ; Remove registry entries
    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
    
    ; Remove installation directory
    RMDir "$INSTDIR"
    
    DetailPrint "Uninstallation completed"
SectionEnd
        