@echo off
echo Building HidHide Helper...
dotnet restore
dotnet publish -c Release -r win-x64 --self-contained false
echo.
if exist "bin\Release\net7.0-windows\win-x64\publish\HidHideHelper.exe" (
    echo ✅ HidHide Helper built successfully!
    echo Location: bin\Release\net7.0-windows\win-x64\publish\HidHideHelper.exe
) else (
    echo ❌ Build failed - executable not found
)
pause
