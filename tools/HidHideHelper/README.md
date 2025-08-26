# HidHide Helper

A simple .NET console application to automate HidHide configuration for TrackPro.

## Building

Requires .NET 7.0 SDK or later.

```bash
dotnet restore
dotnet publish -c Release -r win-x64 --self-contained false
```

The built executable will be in `bin/Release/net7.0-windows/win-x64/publish/HidHideHelper.exe`

## Usage

```bash
HidHideHelper.exe --enable
HidHideHelper.exe --whitelist-add "C:\Path\To\TrackPro.exe"
HidHideHelper.exe --whitelist-print
HidHideHelper.exe --disable
```

## Integration

TrackPro automatically calls this helper on startup to:
1. Enable HidHide device hiding
2. Whitelist the TrackPro executable
3. Optionally whitelist additional feeder applications

This eliminates the need for manual HidHide configuration each time devices are connected.
