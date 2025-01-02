#include "M:\GPT-APPS\Git-TrackPro\TrackPro\src\RegistryHandler.h"
#include <windows.h>
#include <iostream>
#include <dbt.h>

#pragma pack(1)
struct AxisCalibration {
    DWORD min;        // 4 bytes
    DWORD mid;        // 4 bytes
    DWORD max;        // 4 bytes
    DWORD minDeadzone;  // 4 bytes
    DWORD maxDeadzone;  // 4 bytes
};
#pragma pack()

void refreshDeviceState() {  // Changed to void to match header
    // Create a broadcast to refresh device calibration
    DEV_BROADCAST_DEVICEINTERFACE deviceInterface = { 0 };
    deviceInterface.dbcc_size = sizeof(DEV_BROADCAST_DEVICEINTERFACE);
    deviceInterface.dbcc_devicetype = DBT_DEVTYP_DEVICEINTERFACE;

    // Send a device change event to all windows
    DWORD_PTR dwResult;
    LRESULT result = SendMessageTimeout(
        HWND_BROADCAST,
        WM_DEVICECHANGE,
        DBT_DEVICEARRIVAL,
        (LPARAM)&deviceInterface,
        SMTO_ABORTIFHUNG,
        1000,
        &dwResult
        );

    if (result == 0) {
        std::wcerr << L"Failed to broadcast device change message\n";
        return;
    }

    std::wcout << L"Device state refresh broadcast sent successfully\n";
}

void saveCalibrationToRegistry(const std::wstring& calibrationData, int axisIndex) {
    HKEY hKey;

    // Convert our axis index to the correct registry index
    int registryIndex;
    switch (axisIndex) {
    case 0: registryIndex = 0; break; // X-axis
    case 1: registryIndex = 2; break; // Z-axis
    case 2: registryIndex = 4; break; // RY-axis
    default: registryIndex = 0; break;
    }

    // Directly access the axis registry location
    std::wstring axisPath = L"System\\CurrentControlSet\\Control\\MediaProperties\\PrivateProperties\\DirectInput\\VID_1DD2&PID_2735\\Calibration\\0\\Type\\Axes\\" + std::to_wstring(registryIndex);

    // Parse calibration values
    DWORD min = 0, max = 4095, minDeadzone = 0, maxDeadzone = 0;
    size_t pos = 0, next;

    while ((next = calibrationData.find(L";", pos)) != std::wstring::npos) {
        std::wstring token = calibrationData.substr(pos, next - pos);
        switch (axisIndex) {
        case 0: // X-axis
            if (token.find(L"MinX=") == 0)
                min = std::stoul(token.substr(5));
            else if (token.find(L"MaxX=") == 0)
                max = std::stoul(token.substr(5));
            else if (token.find(L"MinDeadzoneX=") == 0)
                minDeadzone = std::stoul(token.substr(12));
            else if (token.find(L"MaxDeadzoneX=") == 0)
                maxDeadzone = std::stoul(token.substr(12));
            break;
        case 1: // Z-axis
            if (token.find(L"MinZ=") == 0)
                min = std::stoul(token.substr(5));
            else if (token.find(L"MaxZ=") == 0)
                max = std::stoul(token.substr(5));
            else if (token.find(L"MinDeadzoneZ=") == 0)
                minDeadzone = std::stoul(token.substr(12));
            else if (token.find(L"MaxDeadzoneZ=") == 0)
                maxDeadzone = std::stoul(token.substr(12));
            break;
        case 2: // RY-axis
            if (token.find(L"MinRY=") == 0)
                min = std::stoul(token.substr(6));
            else if (token.find(L"MaxRY=") == 0)
                max = std::stoul(token.substr(6));
            else if (token.find(L"MinDeadzoneRY=") == 0)
                minDeadzone = std::stoul(token.substr(13));
            else if (token.find(L"MaxDeadzoneRY=") == 0)
                maxDeadzone = std::stoul(token.substr(13));
            break;
        }
        pos = next + 1;
    }

    DWORD mid = (min + max) / 2;

    // Open the existing key
    LONG result = RegOpenKeyExW(
        HKEY_CURRENT_USER,
        axisPath.c_str(),
        0,
        KEY_SET_VALUE,
        &hKey
        );

    if (result == ERROR_SUCCESS) {
        AxisCalibration axisData = { min, mid, max, minDeadzone, maxDeadzone };

        result = RegSetValueExW(
            hKey,
            L"Calibration",
            0,
            REG_BINARY,
            reinterpret_cast<const BYTE*>(&axisData),
            sizeof(AxisCalibration)
            );

        if (result == ERROR_SUCCESS) {
            std::wcout << L"Wrote calibration for axis " << axisIndex << L":\n"
                       << L"Min: " << min << L" Mid: " << mid << L" Max: " << max << L"\n"
                       << L"Min Deadzone: " << minDeadzone << L" Max Deadzone: " << maxDeadzone << std::endl;
        }
        else {
            std::wcerr << L"Failed to write calibration. Error: " << result << std::endl;
        }

        RegCloseKey(hKey);
    }
    else {
        std::wcerr << L"Failed to open axis registry key. Error: " << result << std::endl;
    }

    refreshDeviceState();
}

void readCalibrationData() {
    for (int axisIndex = 0; axisIndex < 3; axisIndex++) {
        HKEY hKey;
        std::wstring basePath = L"System\\CurrentControlSet\\Control\\MediaProperties\\PrivateProperties\\DirectInput\\VID_1DD2&PID_2735\\Calibration\\0\\Type\\Axes\\";
        std::wstring axisPath = basePath + std::to_wstring(axisIndex);

        if (RegOpenKeyExW(HKEY_CURRENT_USER, axisPath.c_str(), 0, KEY_READ, &hKey) == ERROR_SUCCESS) {
            AxisCalibration axisData;
            DWORD dataSize = sizeof(AxisCalibration);
            DWORD type = REG_BINARY;

            if (RegQueryValueExW(hKey, L"Calibration", NULL, &type,
                                 reinterpret_cast<LPBYTE>(&axisData), &dataSize) == ERROR_SUCCESS) {
                std::wcout << L"Current calibration values for axis " << axisIndex << L":\n"
                           << L"Min: " << axisData.min << L"\n"
                           << L"Mid: " << axisData.mid << L"\n"
                           << L"Max: " << axisData.max << L"\n"
                           << L"Min Deadzone: " << axisData.minDeadzone << L"\n"
                           << L"Max Deadzone: " << axisData.maxDeadzone << L"\n";
            }
            else {
                std::wcerr << L"Failed to read calibration data for axis " << axisIndex << L"\n";
            }

            RegCloseKey(hKey);
        }
    }
}
