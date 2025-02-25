
; Installer script for TrackPro

!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "TrackPro v1.0.0"
OutFile "TrackPro_Setup_v1.0.0.exe"
InstallDir "$PROGRAMFILES64\TrackPro"

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

Function .onInit
    StrCpy $NEEDS_RESTART "0"
    
    ; Check if we're resuming after reboot
    ReadRegStr $R0 HKLM "${RESUME_INSTALLATIONS_KEY}" "${RESUME_INSTALLATIONS_VALUE}"
    ${If} $R0 != ""
        ; Skip driver installation if we're resuming
        StrCpy $0 "RESUME"
    ${EndIf}
FunctionEnd

Section "Prerequisites"
    ${If} $0 != "RESUME"
        SetOutPath "$TEMP\TrackPro\prerequisites"
        
        ; Extract prerequisite installers
        File /r "installer_temp\prerequisites\*"
        
        ; Create program directory
        CreateDirectory "$PROGRAMFILES64\TrackPro"
        SetOutPath "$PROGRAMFILES64\TrackPro"
        
        ; Install TrackPro first with explicit verification
        DetailPrint "Installing TrackPro..."
        CopyFiles /SILENT "$TEMP\TrackPro\dist\TrackPro_v1.0.0.exe" "$PROGRAMFILES64\TrackPro"
        
        ; Verify TrackPro.exe exists
        IfFileExists "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.0.exe" +3
            MessageBox MB_OK|MB_ICONSTOP "Failed to copy TrackPro_v1.0.0.exe to installation directory!"
            Abort "Installation failed: Could not copy TrackPro_v1.0.0.exe"
            
        ; Create shortcuts with verification
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v1.0.0.lnk" "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.0.exe"
        CreateShortCut "$DESKTOP\TrackPro v1.0.0.lnk" "$PROGRAMFILES64\TrackPro\TrackPro_v1.0.0.exe"
        
        DetailPrint "TrackPro installation complete"

        ; Run HidHide installer with wait
        DetailPrint "Installing HidHide..."
        ExecWait '"$TEMP\TrackPro\prerequisites\HidHide_1.2.98_x64.exe" /quiet /norestart' $1
        DetailPrint "HidHide installation complete"
        ${If} $1 == 3010
            StrCpy $NEEDS_RESTART "1"
        ${EndIf}

        ; Run vJoy installer silently and wait
        DetailPrint "Installing vJoy..."
        ; Save the installation path for resume
        WriteRegStr HKLM "${RESUME_INSTALLATIONS_KEY}" "${RESUME_INSTALLATIONS_VALUE}" "$EXEPATH"
        ExecWait '"$TEMP\TrackPro\prerequisites\vJoySetup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /TYPE=MINIMAL' $0
        DetailPrint "vJoy installation complete"
        ${If} $0 == 3010
            StrCpy $NEEDS_RESTART "1"
        ${EndIf}

        ; Clean up temp files
        SetOutPath "$TEMP"
        RMDir /r "$TEMP\TrackPro"

        ; Show installation paths at the end
        MessageBox MB_OK|MB_ICONINFORMATION \
            "TrackPro v1.0.0 has been installed to:$\n\
            $PROGRAMFILES64\TrackPro\TrackPro_v1.0.0.exe$\n\n\
            Shortcuts have been created:$\n\
            - Start Menu: $SMPROGRAMS\TrackPro\TrackPro v1.0.0.lnk$\n\
            - Desktop: $DESKTOP\TrackPro v1.0.0.lnk$\n\n\
            Please verify these locations after installation."
    ${EndIf}
SectionEnd

Section "MainApplication"
    ; Only run this section if we're resuming after a reboot
    ${If} $0 == "RESUME"
        SetOutPath "$INSTDIR"
        File "dist\TrackPro_v1.0.0.exe"
        CreateDirectory "$SMPROGRAMS\TrackPro"
        CreateShortCut "$SMPROGRAMS\TrackPro\TrackPro v1.0.0.lnk" "$INSTDIR\TrackPro_v1.0.0.exe"
        WriteUninstaller "$INSTDIR\Uninstall.exe"
        
        ; Clean up resume key
        DeleteRegValue HKLM "${RESUME_INSTALLATIONS_KEY}" "${RESUME_INSTALLATIONS_VALUE}"
    ${EndIf}
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    Delete "$INSTDIR\TrackPro_v1.0.0.exe"
    RMDir "$INSTDIR"
    
    Delete "$SMPROGRAMS\TrackPro\TrackPro v1.0.0.lnk"
    RMDir "$SMPROGRAMS\TrackPro"
SectionEnd
