[Setup]
AppName=TrackPro
AppVersion=1.5.4
DefaultDirName={localappdata}\TrackPro
DisableDirPage=no
AllowNoIcons=no
OutputBaseFilename=TrackPro_Setup_v1.5.4
OutputDir=.
PrivilegesRequired=admin
SetupLogging=yes
Compression=lzma2/max
SolidCompression=yes
CreateAppDir=yes
UninstallDisplayName=TrackPro v1.5.4
UninstallDisplayIcon={app}\TrackPro_v1.5.4.exe

[InstallDelete]
; Clean up old TrackPro executables from all possible installation locations
Type: files; Name: "{localappdata}\TrackPro\TrackPro*.exe"
Type: files; Name: "{localappdata}\TrackPro\TrackPro_v*.exe"
Type: files; Name: "{pf}\TrackPro\TrackPro*.exe"
Type: files; Name: "{pf}\TrackPro\TrackPro_v*.exe"
Type: files; Name: "{pf32}\TrackPro\TrackPro*.exe"
Type: files; Name: "{pf32}\TrackPro\TrackPro_v*.exe"
Type: files; Name: "{userappdata}\TrackPro\TrackPro*.exe"
Type: files; Name: "{userappdata}\TrackPro\TrackPro_v*.exe"

; Clean up old installation logs and temporary files
Type: files; Name: "{app}\TrackPro_Install_Debug.txt"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"

; Clean up old uninstaller files
Type: files; Name: "{app}\unins*.exe"
Type: files; Name: "{app}\unins*.dat"

[UninstallDelete]
; Remove all TrackPro related files during uninstall
Type: filesandordirs; Name: "{app}"
Type: files; Name: "{localappdata}\TrackPro\*.log"
Type: files; Name: "{localappdata}\TrackPro\*.tmp"
Type: files; Name: "{userappdata}\TrackPro\*.log"
Type: files; Name: "{userappdata}\TrackPro\*.tmp"

[Files]
Source: "installer_temp\dist\TrackPro_v1.5.4.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer_temp\prerequisites\vJoySetup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "installer_temp\prerequisites\HidHide_1.5.230_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "installer_temp\prerequisites\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Code]
// Windows API function declarations
function GetTickCount: DWORD;
external 'GetTickCount@kernel32.dll stdcall';

procedure LogCustom(Message: String);
var
  LogFile: String;
begin
  LogFile := ExpandConstant('{tmp}') + '\TrackPro_Install_Debug.txt';
  SaveStringToFile(LogFile, GetDateTimeString('hh:nn:ss', '-', ':') + ' - ' + Message + #13#10, True);
end;

// UTILITY FUNCTIONS - Must be defined first since they're called by other functions
function ProcessExists(ProcessName: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := not Exec(ExpandConstant('{sys}\tasklist.exe'), '/FI "IMAGENAME eq ' + ProcessName + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 1);
end;

function KillVJoySetupProcesses: Boolean;
var
  ResultCode: Integer;
begin
  LogCustom('Checking for hung vJoy installer processes...');
  
  // Kill any hanging vJoySetup.exe processes
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM vJoySetup.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  // Also kill any vJoy installer related processes that might be hanging
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "vJoy*"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  Result := True;
  LogCustom('vJoy process cleanup completed');
end;

procedure LogPrereqStart(Name: String);
begin
  LogCustom('STARTING: ' + Name + ' installation...');
end;

procedure LogPrereqEnd(Name: String);
begin
  LogCustom('COMPLETED: ' + Name + ' installation finished');
  
  // Special handling for vJoy to clean up any hanging processes
  if Name = 'vJoy' then
  begin
    LogCustom('Performing vJoy post-installation cleanup...');
    Sleep(2000); // Wait 2 seconds for any dialogs to appear
    KillVJoySetupProcesses;
    Sleep(1000); // Wait another second for cleanup to complete
    LogCustom('vJoy post-installation cleanup completed');
  end;
end;

procedure CleanupOldShortcuts;
var
  OldShortcuts: TStringList;
  I: Integer;
  ShortcutPath: String;
begin
  LogCustom('=== Starting Old Shortcut Cleanup ===');
  
  OldShortcuts := TStringList.Create;
  try
    // Common Start Menu locations for TrackPro shortcuts
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro.lnk');
    OldShortcuts.Add(ExpandConstant('{commonstartmenu}') + '\Programs\TrackPro.lnk');
    OldShortcuts.Add(ExpandConstant('{commonstartmenu}') + '\Programs\TrackPro\TrackPro.lnk');
    OldShortcuts.Add(ExpandConstant('{userstartmenu}') + '\Programs\TrackPro.lnk');
    OldShortcuts.Add(ExpandConstant('{userstartmenu}') + '\Programs\TrackPro\TrackPro.lnk');
    
    // Common Desktop locations for TrackPro shortcuts
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro.lnk');
    
    // Check for shortcuts with version numbers (e.g., TrackPro v1.5.4.lnk)
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro v1.5.4.lnk');
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro v1.5.4.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro v1.5.4.lnk');
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro v1.5.3.lnk');
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro v1.5.3.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro v1.5.3.lnk');
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro v1.5.2.lnk');
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro v1.5.2.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro v1.5.2.lnk');
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro v1.5.1.lnk');
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro v1.5.1.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro v1.5.1.lnk');
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro v1.5.0.lnk');
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro v1.5.0.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro v1.5.0.lnk');
    OldShortcuts.Add(ExpandConstant('{group}') + '\TrackPro v1.4.9.lnk');
    OldShortcuts.Add(ExpandConstant('{commondesktop}') + '\TrackPro v1.4.9.lnk');
    OldShortcuts.Add(ExpandConstant('{userdesktop}') + '\TrackPro v1.4.9.lnk');
    
    for I := 0 to OldShortcuts.Count - 1 do
    begin
      ShortcutPath := OldShortcuts[I];
      if FileExists(ShortcutPath) then
      begin
        LogCustom('Removing old shortcut: ' + ShortcutPath);
        try
          DeleteFile(ShortcutPath);
          LogCustom('Successfully removed: ' + ShortcutPath);
        except
          LogCustom('Failed to remove: ' + ShortcutPath);
        end;
      end;
    end;
    
    // Also clean up empty TrackPro folders in Start Menu
    try
      RemoveDir(ExpandConstant('{commonstartmenu}') + '\Programs\TrackPro');
      RemoveDir(ExpandConstant('{userstartmenu}') + '\Programs\TrackPro');
      LogCustom('Cleaned up empty TrackPro Start Menu folders');
    except
      LogCustom('Note: Could not remove TrackPro Start Menu folders (may not be empty)');
    end;
    
  finally
    OldShortcuts.Free;
  end;
  
  LogCustom('=== Old Shortcut Cleanup Completed ===');
end;

procedure CleanupOldInstallations;
var
  OldInstallPaths: TStringList;
  I, J: Integer;
  InstallPath, ExePath: String;
  FindRec: TFindRec;
begin
  LogCustom('=== Starting Old Installation Cleanup ===');
  
  OldInstallPaths := TStringList.Create;
  try
    // Common installation directories where TrackPro might be installed
    OldInstallPaths.Add(ExpandConstant('{localappdata}') + '\TrackPro');
    OldInstallPaths.Add(ExpandConstant('{pf}') + '\TrackPro');
    OldInstallPaths.Add(ExpandConstant('{pf32}') + '\TrackPro');
    OldInstallPaths.Add(ExpandConstant('{userappdata}') + '\TrackPro');
    OldInstallPaths.Add(ExpandConstant('{userappdata}') + '\Local\TrackPro');
    
    for I := 0 to OldInstallPaths.Count - 1 do
    begin
      InstallPath := OldInstallPaths[I];
      LogCustom('Checking installation path: ' + InstallPath);
      
      if DirExists(InstallPath) then
      begin
        LogCustom('Found existing TrackPro installation at: ' + InstallPath);
        
        // Find and remove old TrackPro executables
        if FindFirst(InstallPath + '\TrackPro*.exe', FindRec) then
        begin
          try
            repeat
              ExePath := InstallPath + '\' + FindRec.Name;
              LogCustom('Removing old executable: ' + ExePath);
              try
                DeleteFile(ExePath);
                LogCustom('Successfully removed: ' + ExePath);
              except
                LogCustom('Failed to remove: ' + ExePath + ' (may be in use)');
              end;
            until not FindNext(FindRec);
          finally
            FindClose(FindRec);
          end;
        end;
        
        // Remove old uninstaller files
        if FileExists(InstallPath + '\unins000.exe') then
        begin
          LogCustom('Removing old uninstaller: ' + InstallPath + '\unins000.exe');
          try
            DeleteFile(InstallPath + '\unins000.exe');
            DeleteFile(InstallPath + '\unins000.dat');
          except
            LogCustom('Could not remove old uninstaller files');
          end;
        end;
        
        // Remove old log files
        if FindFirst(InstallPath + '\*.log', FindRec) then
        begin
          try
            repeat
              LogCustom('Removing old log file: ' + InstallPath + '\' + FindRec.Name);
              DeleteFile(InstallPath + '\' + FindRec.Name);
            until not FindNext(FindRec);
          finally
            FindClose(FindRec);
          end;
        end;
      end;
    end;
    
  finally
    OldInstallPaths.Free;
  end;
  
  LogCustom('=== Old Installation Cleanup Completed ===');
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

function InstallVJoyWithTimeout: Boolean;
var
  ResultCode: Integer;
  StartTime: DWORD;
  TimeoutMs: DWORD;
  ProcessID: DWORD;
begin
  Result := False;
  TimeoutMs := 300000; // 5 minute timeout
  
  LogCustom('Starting vJoy installation with timeout handling...');
  
  try
    StartTime := GetTickCount;
    
    // Try silent installation first
    LogCustom('Attempting silent vJoy installation...');
    if Exec(ExpandConstant('{tmp}\vJoySetup.exe'), '/S', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
      begin
        LogCustom('vJoy silent installation succeeded');
        Result := True;
        Exit;
      end
      else
      begin
        LogCustom('vJoy silent installation failed with code: ' + IntToStr(ResultCode));
      end;
    end;
    
    // If silent failed, try with minimal UI
    LogCustom('Silent installation failed, trying with minimal UI...');
    if Exec(ExpandConstant('{tmp}\vJoySetup.exe'), '/VERYSILENT /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
      begin
        LogCustom('vJoy installation with minimal UI succeeded');
        Result := True;
        Exit;
      end
      else
      begin
        LogCustom('vJoy installation with minimal UI failed with code: ' + IntToStr(ResultCode));
      end;
    end;
    
    // If all else fails, try normal installation but with process monitoring
    LogCustom('Previous attempts failed, trying normal installation with monitoring...');
    if Exec(ExpandConstant('{tmp}\vJoySetup.exe'), '', '', SW_SHOW, ewNoWait, ResultCode) then
    begin
      LogCustom('vJoy installer started, monitoring for completion...');
      
      // Wait for installation to complete or timeout
      while (GetTickCount - StartTime) < TimeoutMs do
      begin
        Sleep(5000); // Check every 5 seconds
        
        // Check if vJoy is now installed
        if IsVJoyInstalled then
        begin
          LogCustom('vJoy installation detected as complete');
          KillVJoySetupProcesses; // Clean up any hanging processes
          Result := True;
          Exit;
        end;
        
        // Check if installer process is still running
        if not ProcessExists('vJoySetup.exe') then
        begin
          LogCustom('vJoy installer process no longer running');
          if IsVJoyInstalled then
          begin
            LogCustom('vJoy installation successful');
            Result := True;
          end
          else
          begin
            LogCustom('vJoy installation may have failed');
          end;
          Exit;
        end;
      end;
      
      // Timeout reached
      LogCustom('vJoy installation timeout reached, cleaning up...');
      KillVJoySetupProcesses;
      
      // Check one more time if it's installed
      if IsVJoyInstalled then
      begin
        LogCustom('vJoy installation completed despite timeout');
        Result := True;
      end
      else
      begin
        LogCustom('vJoy installation failed - timeout exceeded');
      end;
    end;
    
  except
    LogCustom('Exception during vJoy installation');
    KillVJoySetupProcesses;
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
  LogCustom('Installer version: 1.5.4');
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
    
  StatusMsg := StatusMsg + #13#10 + 'IMPORTANT: This installer will automatically remove ALL previous' + #13#10;
  StatusMsg := StatusMsg + 'TrackPro versions and shortcuts before installing the new version.' + #13#10;
  StatusMsg := StatusMsg + 'This ensures a clean installation and prevents disk space issues.' + #13#10 + #13#10;
  StatusMsg := StatusMsg + 'YOUR USER DATA WILL BE PRESERVED:' + #13#10;
  StatusMsg := StatusMsg + '- Calibrations and settings will NOT be deleted' + #13#10;
  StatusMsg := StatusMsg + '- Only old executable files and shortcuts are removed' + #13#10 + #13#10;
  StatusMsg := StatusMsg + 'The default installation path can be changed on the next screen.' + #13#10;
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
  VJoyInstallSuccess: Boolean;
begin
  if CurStep = ssInstall then
  begin
    LogCustom('=== Starting installation phase ===');
    LogCustom('TrackPro application will be installed to: ' + ExpandConstant('{app}'));
    
    // Perform cleanup of old installations and shortcuts
    CleanupOldInstallations;
    CleanupOldShortcuts;
    
    // Install prerequisites with enhanced vJoy handling
    if not IsVJoyInstalled then
    begin
      LogCustom('vJoy not detected, starting installation...');
      VJoyInstallSuccess := InstallVJoyWithTimeout;
      if VJoyInstallSuccess then
        LogCustom('vJoy installation completed successfully')
      else
        LogCustom('vJoy installation encountered issues but may still be functional');
    end
    else
    begin
      LogCustom('vJoy already installed, skipping');
    end;
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
                'OLD VERSION CLEANUP:' + #13#10 + 
                'All previous TrackPro versions and shortcuts have been removed.' + #13#10 + 
                'User data (calibrations, settings) has been preserved.' + #13#10 + #13#10 + 
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
; vJoy installation is now handled in CurStepChanged for better control
Filename: "{tmp}\HidHide_1.5.230_x64.exe"; StatusMsg: "Installing HidHide..."; Flags: waituntilterminated; Check: not IsHidHideInstalled; BeforeInstall: LogPrereqStart('HidHide'); AfterInstall: LogPrereqEnd('HidHide')
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated; Check: not IsVCRedistInstalled; BeforeInstall: LogPrereqStart('Visual C++'); AfterInstall: LogPrereqEnd('Visual C++')

[Icons]
Name: "{group}\TrackPro"; Filename: "{app}\TrackPro_v1.5.4.exe"; WorkingDir: "{app}"; Comment: "TrackPro Racing Coach Application"
Name: "{commondesktop}\TrackPro"; Filename: "{app}\TrackPro_v1.5.4.exe"; WorkingDir: "{app}"; Comment: "TrackPro Racing Coach Application"; Tasks: desktopicon; Flags: createonlyiffileexists

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
