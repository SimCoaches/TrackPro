[Setup]
AppName=TrackPro
AppVersion=0.1.9
AppPublisher=Lawrence Thomas - Sim Coaches LLC
DefaultDirName={pf}\TrackPro
DefaultGroupName=TrackPro
OutputDir=Output
OutputBaseFilename=TrackProV0.1.9
UninstallDisplayIcon={app}\GUI.exe
VersionInfoCompany=Sim Coaches LLC
VersionInfoCopyright=Lawrence Thomas
VersionInfoDescription=TrackPRO
VersionInfoVersion=0.1.9
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin

[Files]
; Main Qt executable and dependencies
Source: "D:\TrackPro\TrackPro\TrackProV0.1.3\TrackPro\GUI\build\Desktop_Qt_6_8_0_MinGW_64_bit-Release\GUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\TrackPro\TrackPro\TrackProV0.1.3\TrackPro\GUI\build\Desktop_Qt_6_8_0_MinGW_64_bit-Release\*.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\TrackPro\TrackPro\TrackProV0.1.3\TrackPro\GUI\build\Desktop_Qt_6_8_0_MinGW_64_bit-Release\platforms\*"; DestDir: "{app}\platforms\"; Flags: ignoreversion recursesubdirs
Source: "D:\TrackPro\TrackPro\TrackProV0.1.3\TrackPro\GUI\build\Desktop_Qt_6_8_0_MinGW_64_bit-Release\styles\*"; DestDir: "{app}\styles\"; Flags: ignoreversion recursesubdirs

; Documentation
Source: "D:\TrackPro\TrackPro\GitHub\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\TrackPro\TrackPro\GitHub\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\TrackPro\TrackPro\GitHub\CHANGELOG.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TrackPro"; Filename: "{app}\GUI.exe"
Name: "{commondesktop}\TrackPro"; Filename: "{app}\GUI.exe"

[Run]
Filename: "{app}\GUI.exe"; Description: "Launch TrackPro"; Flags: postinstall nowait runascurrentuser

[Code]
const
  DirectXDLL = '{sys}\d3dx9_43.dll';
  MSVCDLL = '{sys}\msvcp140.dll';

function IsDirectXInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant(DirectXDLL));
end;

function IsMSVCInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant(MSVCDLL));
end;

function InitializeSetup: Boolean;
var
  InstallErrCode: Integer;
begin
  Result := True;
  
  if not IsMSVCInstalled then
  begin
    MsgBox('Visual C++ Redistributable 2015-2022 x64 is required but not installed. It will be installed now.', mbInformation, MB_OK);
    ShellExec('', ExpandConstant('{tmp}\vc_redist.x64.exe'), '/quiet /norestart', '', SW_SHOW, ewWaitUntilTerminated, InstallErrCode);
    if InstallErrCode <> 0 then
    begin
      MsgBox('Visual C++ Redistributable installation failed. Please install it manually.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
  
  if not IsDirectXInstalled then
  begin
    MsgBox('DirectX Runtime is required but not installed. It will be installed now.', mbInformation, MB_OK);
    ShellExec('', ExpandConstant('{tmp}\directx_Jun2010_redist.exe'), '/Q', '', SW_SHOW, ewWaitUntilTerminated, InstallErrCode);
    if InstallErrCode <> 0 then
    begin
      if MsgBox('DirectX installation failed. Do you want to skip this step and proceed?', mbConfirmation, MB_YESNO) = IDYES then
        Result := True
      else
        Result := False;
      Exit;
    end;
  end;
end;