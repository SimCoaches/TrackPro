
; Installer script for TrackPro

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "TrackPro v1.0.1"
OutFile "TrackPro_Setup_v1.0.1.exe"
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
    ${If} $0 != "admin"
        MessageBox MB_OK|MB_ICONSTOP "Administrator rights required! Please right-click and select 'Run as administrator'."
        Abort "Installation aborted: Administrator rights required"
    ${EndIf}
    
    ; Check if we're resuming after reboot
    ReadRegStr $R0 HKLM "${RESUME_INSTALLATIONS_KEY}" "${RESUME_INSTALLATIONS_VALUE}"
    ${If} $R0 != ""
        ; Skip driver installation if we're resuming
        StrCpy $0 "RESUME"
    ${EndIf}
FunctionEnd

Section "Prerequisites"
    ${If} $0 != "RESUME"
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
        File "installer_temp\dist\TrackPro_v1.0.1.exe"
        
        ; Verify the file was extracted correctly
        IfFileExists "$TEMP\TrackPro\app\TrackPro_v1.0.1.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to extract TrackPro_v1.0.1.exe to temporary directory!"
            Abort "Installation failed: Could not extract TrackPro_v1.0.1.exe"
        
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
        StrCpy $DEBUG_MSG "Copying from: $TEMP\TrackPro\app\TrackPro_v1.0.1.exe to $PROGRAMFILES64\TrackPro"
        DetailPrint $DEBUG_MSG
        
        ; Check if destination file already exists and try to remove it
        IfFileExists "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.1.exe" 0 +3
            DetailPrint "Removing existing installation file..."
            Delete "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.1.exe"
        
        ; Clear any previous errors and copy the file
        ClearErrors
        CopyFiles /SILENT "$TEMP\TrackPro\app\TrackPro_v1.0.1.exe" "$PROGRAMFILES64\TrackPro"
        
        ; Check for copy errors
        IfErrors 0 +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v1.0.1.exe to installation directory! Please ensure you have administrator privileges and try again."
            Abort "Installation failed: Could not copy TrackPro_v1.0.1.exe"
        
        ; Verify TrackPro.exe exists in the destination
        IfFileExists "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.1.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to verify TrackPro_v1.0.1.exe in installation directory!"
            Abort "Installation failed: Could not verify TrackPro_v1.0.1.exe"
            
        ; Create shortcuts with verification
        DetailPrint "Creating shortcuts..."
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v1.0.1.lnk" "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.1.exe"
        CreateShortCut "$DESKTOP\TrackPro v1.0.1.lnk" "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.1.exe"
        
        DetailPrint "TrackPro installation complete"

        ; Run HidHide installer with wait
        DetailPrint "Installing HidHide..."
        ExecWait '"$TEMP\TrackPro\prerequisites\HidHide_1.2.98_x64.exe" /quiet /norestart' $1
        DetailPrint "HidHide installation complete with exit code: $1"
        ${If} $1 == 3010
            StrCpy $NEEDS_RESTART "1"
            DetailPrint "HidHide requires a system restart"
        ${EndIf}

        ; Run vJoy installer silently and wait
        DetailPrint "Installing vJoy..."
        ; Save the installation path for resume
        WriteRegStr HKLM "${RESUME_INSTALLATIONS_KEY}" "${RESUME_INSTALLATIONS_VALUE}" "$EXEPATH"
        ExecWait '"$TEMP\TrackPro\prerequisites\vJoySetup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /TYPE=MINIMAL' $0
        DetailPrint "vJoy installation complete with exit code: $0"
        ${If} $0 == 3010
            StrCpy $NEEDS_RESTART "1"
            DetailPrint "vJoy requires a system restart"
        ${EndIf}

        ; Clean up temp files AFTER all installations are complete
        DetailPrint "Cleaning up temporary files..."
        SetOutPath "$TEMP"
        RMDir /r "$TEMP\TrackPro"

        ; Show installation paths at the end
        MessageBox MB_OK|MB_ICONINFORMATION \
            "TrackPro v1.0.1 has been installed to:$\n\
            $PROGRAMFILES64\TrackPro\TrackPro_v1.0.1.exe$\n\n\
            Shortcuts have been created:$\n\
            - Start Menu: $SMPROGRAMS\TrackPro\TrackPro v1.0.1.lnk$\n\
            - Desktop: $DESKTOP\TrackPro v1.0.1.lnk$\n\n\
            Please verify these locations after installation."
            
        ; Check if we need to restart
        ${If} $NEEDS_RESTART == "1"
            MessageBox MB_YESNO|MB_ICONQUESTION "A system restart is required to complete the installation. Would you like to restart now?" IDNO +2
                Reboot
        ${EndIf}
    ${EndIf}
SectionEnd

Section "MainApplication"
    ; Only run this section if we're resuming after a reboot
    ${If} $0 == "RESUME"
        DetailPrint "Resuming installation after reboot..."
        SetOutPath "$INSTDIR"
        
        ; Check if the file exists in the package
        IfFileExists "dist\TrackPro_v1.0.1.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Could not find TrackPro_v1.0.1.exe in the installer package!"
            Abort "Resume installation failed: Missing executable file"
            
        ; Copy the main executable
        ClearErrors
        File "dist\TrackPro_v1.0.1.exe"
        
        ; Check for errors
        IfErrors 0 +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v1.0.1.exe during resume!"
            Abort "Resume installation failed: Could not copy executable"
        
        ; Create shortcuts
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v1.0.1.lnk" "$INSTDIR\TrackPro_v1.0.1.exe"
        CreateShortCut "$DESKTOP\TrackPro v1.0.1.lnk" "$INSTDIR\TrackPro_v1.0.1.exe"
        
        ; Create uninstaller
        WriteUninstaller "$INSTDIR\Uninstall.exe"
        
        ; Clean up resume key
        DeleteRegValue HKLM "${RESUME_INSTALLATIONS_KEY}" "${RESUME_INSTALLATIONS_VALUE}"
        
        DetailPrint "Installation completed successfully after reboot"
    ${EndIf}
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    Delete "$INSTDIR\TrackPro_v1.0.1.exe"
    RMDir "$INSTDIR"
    
    Delete "$SMPROGRAMS\TrackPro\TrackPro v1.0.1.lnk"
    Delete "$DESKTOP\TrackPro v1.0.1.lnk"
    RMDir "$SMPROGRAMS\TrackPro"
    
    DetailPrint "Uninstallation complete"
SectionEnd
