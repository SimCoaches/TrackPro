[Setup]
AppName=TrackPro
AppVersion=0.2.1
AppPublisher=Lawrence Thomas - Sim Coaches LLC
DefaultDirName={pf}\TrackPro
DefaultGroupName=TrackPro
OutputDir=Output
OutputBaseFilename=TrackProV0.2.1
UninstallDisplayIcon={app}\TrackPro.exe
VersionInfoCompany=Sim Coaches LLC
VersionInfoCopyright=Lawrence Thomas
VersionInfoDescription=TrackPRO
VersionInfoVersion=0.2.1
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin

[Files]
; Main executable
Source: "release\TrackPro.exe"; DestDir: "{app}"; Flags: ignoreversion

; Qt DLLs - adjust paths as needed
Source: "C:\Qt\6.8.0\mingw_64\bin\Qt6Core.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Qt\6.8.0\mingw_64\bin\Qt6Gui.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Qt\6.8.0\mingw_64\bin\Qt6Widgets.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Qt\6.8.0\mingw_64\bin\Qt6Charts.dll"; DestDir: "{app}"; Flags: ignoreversion

; MinGW Runtime
Source: "C:\Qt\6.8.0\mingw_64\bin\libgcc_s_seh-1.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Qt\6.8.0\mingw_64\bin\libstdc++-6.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Qt\6.8.0\mingw_64\bin\libwinpthread-1.dll"; DestDir: "{app}"; Flags: ignoreversion

; Qt Platform Plugin
Source: "C:\Qt\6.8.0\mingw_64\plugins\platforms\qwindows.dll"; DestDir: "{app}\platforms\"; Flags: ignoreversion

; Qt Style Plugin
Source: "C:\Qt\6.8.0\mingw_64\plugins\styles\qwindowsvistastyle.dll"; DestDir: "{app}\styles\"; Flags: ignoreversion

[Icons]
Name: "{group}\TrackPro"; Filename: "{app}\TrackPro.exe"
Name: "{commondesktop}\TrackPro"; Filename: "{app}\TrackPro.exe"

[Run]
Filename: "{app}\TrackPro.exe"; Description: "Launch TrackPro"; Flags: postinstall nowait runascurrentuser

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
  
  // Check and install Visual C++ Redistributable
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

  // Check and install DirectX Runtime
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