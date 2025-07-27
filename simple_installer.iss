[Setup]
AppName=TrackPro
AppVersion=1.5.3
DefaultDirName={localappdata}\TrackPro
DisableDirPage=no
AllowNoIcons=no
OutputBaseFilename=TrackPro_Setup_v1.5.3
OutputDir=.
PrivilegesRequired=admin
SetupLogging=yes
Compression=lzma2/max
SolidCompression=yes
CreateAppDir=yes

[Files]
Source: "installer_temp\dist\TrackPro_v1.5.3.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer_temp\prerequisites\vJoySetup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "installer_temp\prerequisites\HidHide_1.5.230_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "installer_temp\prerequisites\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Code]
procedure LogCustom(Message: String);
var
  LogFile: String;
begin
  LogFile := ExpandConstant('{tmp}') + '\TrackPro_Install_Debug.txt';
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
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Services\vjoy') then
  begin
    // If the service key exists, let's also check for the driver file itself.
    // An incomplete uninstall might leave the key but remove the file.
    if FileExists(ExpandConstant('{win}\System32\drivers\vjoy.sys')) then
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
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-68D8DA846DB0}') then
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
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Services\HidHide') then
  begin
    // Also check for the driver file.
    if FileExists(ExpandConstant('{win}\System32\drivers\HidHide.sys')) then
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
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{0C713C5A-F072-4BD7-A714-0E0CC6BD5497}') then
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
  Result := RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64', 'Version', Value) and
           (Value >= '14.0');
  
  // Also check WOW64 path for compatibility
  if not Result then
    Result := RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\X64', 'Version', Value) and
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
  AppDir := ExpandConstant('{app}');
  QtCacheDir := AppDir + '\QtWebEngine\Cache';
  QtDataDir := AppDir + '\QtWebEngine\Data';
  
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
  LogFile := ExpandConstant('{tmp}') + '\TrackPro_Install_Debug.txt';
  LogCustom('=== TrackPro Installation Started ===');
  LogCustom('Installer version: 1.5.3');
  LogCustom('Temp directory: ' + ExpandConstant('{tmp}'));
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
    LogCustom('TrackPro application will be installed to: ' + ExpandConstant('{app}'));
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
                ExpandConstant('{app}') + #13#10 + #13#10 + 
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
      
    LogFile := ExpandConstant('{tmp}') + '\TrackPro_Install_Debug.txt';
    
    // Copy debug log to application directory for easy access
    try
      FileCopy(LogFile, ExpandConstant('{app}') + '\TrackPro_Install_Debug.txt', False);
      StatusMsg := StatusMsg + #13#10 + 'Debug log saved to: ' + ExpandConstant('{app}') + '\TrackPro_Install_Debug.txt' + #13#10 + #13#10;
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
Filename: "{tmp}\vJoySetup.exe"; StatusMsg: "Installing vJoy..."; Flags: waituntilterminated; Check: not IsVJoyInstalled; BeforeInstall: LogPrereqStart('vJoy'); AfterInstall: LogPrereqEnd('vJoy')
Filename: "{tmp}\HidHide_1.5.230_x64.exe"; StatusMsg: "Installing HidHide..."; Flags: waituntilterminated; Check: not IsHidHideInstalled; BeforeInstall: LogPrereqStart('HidHide'); AfterInstall: LogPrereqEnd('HidHide')
Filename: "{tmp}\vc_redist.x64.exe"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated; Check: not IsVCRedistInstalled; BeforeInstall: LogPrereqStart('Visual C++'); AfterInstall: LogPrereqEnd('Visual C++')

[Icons]
Name: "{group}\TrackPro"; Filename: "{app}\TrackPro_v1.5.3.exe"; WorkingDir: "{app}"; Comment: "TrackPro Racing Coach Application"
Name: "{commondesktop}\TrackPro"; Filename: "{app}\TrackPro_v1.5.3.exe"; WorkingDir: "{app}"; Comment: "TrackPro Racing Coach Application"; Tasks: desktopicon; Flags: createonlyiffileexists

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
