
; TrackPro Inno Setup Installer - Reliable & Debuggable
; This replaces the problematic NSIS installer

[Setup]
AppName=TrackPro
AppVersion=1.5.3
AppVerName=TrackPro v1.5.3
AppPublisher=TrackPro
AppPublisherURL=https://github.com/Trackpro-dev/TrackPro
AppSupportURL=https://github.com/Trackpro-dev/TrackPro
AppUpdatesURL=https://github.com/Trackpro-dev/TrackPro
DefaultDirName={localappdata}\TrackPro
DefaultGroupName=TrackPro
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=
InfoAfterFile=
OutputDir=.
OutputBaseFilename=TrackPro_Setup_v1.5.3
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
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Main application
Source: "installer_temp/dist/TrackPro_v1.5.3.exe"; DestDir: "{app}"; DestName: "TrackPro_v1.5.3.exe"; Components: main; Flags: ignoreversion

; Prerequisites (downloaded during build)
Source: "installer_temp/prerequisites/vJoySetup.exe"; DestDir: "{tmp}"; Components: drivers; Flags: deleteafterinstall ignoreversion
Source: "installer_temp/prerequisites/HidHide_1.5.230_x64.exe"; DestDir: "{tmp}"; Components: drivers; Flags: deleteafterinstall ignoreversion  
Source: "installer_temp/prerequisites/vc_redist.x64.exe"; DestDir: "{tmp}"; Components: vcredist; Flags: deleteafterinstall ignoreversion

; License file
Source: "LICENSE"; DestDir: "{app}"; Components: main; Flags: ignoreversion

[Icons]
Name: "{group}\TrackPro v1.5.3"; Filename: "{app}\TrackPro_v1.5.3.exe"; Components: shortcuts
Name: "{group}\{cm:UninstallProgram,TrackPro}"; Filename: "{uninstallexe}"; Components: shortcuts
Name: "{autodesktop}\TrackPro v1.5.3"; Filename: "{app}\TrackPro_v1.5.3.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\TrackPro v1.5.3"; Filename: "{app}\TrackPro_v1.5.3.exe"; Tasks: quicklaunchicon

[Run]
; Install drivers silently with detailed logging and error handling
Filename: "{tmp}\vJoySetup.exe"; Parameters: "/S"; Components: drivers; StatusMsg: "Installing vJoy driver..."; Flags: waituntilterminated runhidden; Check: ShouldInstallDriver('vJoy')
Filename: "{tmp}\HidHide_1.5.230_x64.exe"; Parameters: "/S"; Components: drivers; StatusMsg: "Installing HidHide driver..."; Flags: waituntilterminated runhidden; Check: ShouldInstallDriver('HidHide')
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /norestart"; Components: vcredist; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated runhidden; Check: ShouldInstallVCRedist()

; Option to run TrackPro after installation
Filename: "{app}\TrackPro_v1.5.3.exe"; Description: "{cm:LaunchProgram,TrackPro}"; Flags: nowait postinstall skipifsilent

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
  LogFile := ExpandConstant('{userdocs}\TrackPro_Installation_Log.txt');
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
  LogFileName := ExpandConstant('{userdocs}\TrackPro_Installation_Log.txt');
  
  LogMessage('=== TrackPro v1.5.3 Installation Started ===');
  LogMessage('Installer: ' + ExpandConstant('{srcexe}'));
  LogMessage('Target Directory: ' + ExpandConstant('{app}'));
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
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TrackPro_is1') then
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
    if FileExists(ExpandConstant('{sys}\vJoyInterface.dll')) then
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
  if FileExists(ExpandConstant('{sys}\msvcp140.dll')) and 
     FileExists(ExpandConstant('{sys}\vcruntime140.dll')) then
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
    LogMessage('Files installed to: ' + ExpandConstant('{app}'));
    
    // Verify installation
    if FileExists(ExpandConstant('{app}\TrackPro_v1.5.3.exe')) then
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
