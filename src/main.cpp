#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <uxtheme.h>
#include <vssym32.h>
#include <dinput.h>
#include <vector>
#include <string>
#include <iostream>
#include <cmath>
#include "D:\TrackPro\TrackPro\TrackPro\include\RegistryHandler.h"

// Link necessary libraries
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "uxtheme.lib")
#pragma comment(lib, "dinput8.lib")
#pragma comment(lib, "dxguid.lib")

#pragma comment(linker,"\"/manifestdependency:type='win32' \
name='Microsoft.Windows.Common-Controls' version='6.0.0.0' \
processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

// Debug output macro
#define DEBUG_PRINT(msg, ...) { \
    wchar_t dbgBuffer[256]; \
    swprintf_s(dbgBuffer, 256, msg, __VA_ARGS__); \
    std::wcout << dbgBuffer << std::endl; \
}

// Window Classes
#define BAR_CLASS L"ModernAxisBar"
#define BUTTON_CLASS L"ModernButton"

// Control IDs
#define ID_RESET_CALIBRATION 101
#define ID_X_SET_MIN 102
#define ID_X_SET_MAX 103
#define ID_Z_SET_MIN 104
#define ID_Z_SET_MAX 105
#define ID_RY_SET_MIN 106
#define ID_RY_SET_MAX 107
#define ID_X_RAW_BAR 108
#define ID_X_CAL_BAR 109
#define ID_Z_RAW_BAR 110
#define ID_Z_CAL_BAR 111
#define ID_RY_RAW_BAR 112
#define ID_RY_CAL_BAR 113

// Modern color scheme
const COLORREF WINDOW_BG_COLOR = RGB(250, 250, 250);    // Light gray background
const COLORREF TEXT_COLOR = RGB(33, 33, 33);            // Dark gray text
const COLORREF BAR_BG_COLOR = RGB(240, 240, 240);       // Bar background
const COLORREF RAW_BAR_COLOR = RGB(79, 70, 229);        // Indigo
const COLORREF CAL_BAR_COLOR = RGB(16, 185, 129);       // Teal
const COLORREF BUTTON_COLOR = RGB(99, 102, 241);        // Button normal
const COLORREF BUTTON_HOVER = RGB(129, 140, 248);       // Button hover
const COLORREF BUTTON_PRESS = RGB(67, 56, 202);         // Button pressed

// Global variables
LPDIRECTINPUT8 g_pDI = nullptr;
LPDIRECTINPUTDEVICE8 g_pDevice = nullptr;
bool g_running = true;
HFONT g_hModernFont = NULL;

// Window handles
HWND g_hwndXValue = NULL;
HWND g_hwndZValue = NULL;
HWND g_hwndRYValue = NULL;
HWND g_hwndXRawBar = NULL;
HWND g_hwndXCalBar = NULL;
HWND g_hwndZRawBar = NULL;
HWND g_hwndZCalBar = NULL;
HWND g_hwndRYRawBar = NULL;
HWND g_hwndRYCalBar = NULL;

// Current raw values 
LONG g_currentXRaw = 0;
LONG g_currentZRaw = 0;
LONG g_currentRYRaw = 0;

// Calibration ranges
struct AxisRange {
    LONG min;
    LONG max;
};

AxisRange g_xRange = { 0, 4095 };
AxisRange g_zRange = { 0, 4095 };
AxisRange g_ryRange = { 0, 4095 };

// Function prototypes
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
LRESULT CALLBACK BarWindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
LRESULT CALLBACK ModernButtonProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
DWORD WINAPI UpdateThread(LPVOID lpParam);
BOOL CALLBACK EnumDevicesCallback(LPCDIDEVICEINSTANCE lpddi, LPVOID pvRef);
void SaveAxisCalibration(int axisIndex);
void ResetCalibration();
HFONT CreateModernFont(int size = 14, bool bold = false);

// Create modern font
HFONT CreateModernFont(int size, bool bold) {
    return CreateFont(
        -size,                    // Height
        0,                        // Width
        0,                        // Escapement
        0,                        // Orientation
        bold ? FW_SEMIBOLD : FW_NORMAL, // Weight
        FALSE,                    // Italic
        FALSE,                    // Underline
        FALSE,                    // StrikeOut
        DEFAULT_CHARSET,          // CharSet
        OUT_DEFAULT_PRECIS,       // OutPrecision
        CLIP_DEFAULT_PRECIS,      // ClipPrecision
        CLEARTYPE_QUALITY,        // Quality
        DEFAULT_PITCH | FF_DONTCARE, // Pitch and Family
        L"Segoe UI"              // Face Name
    );
}

// Modern button window procedure
LRESULT CALLBACK ModernButtonProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    static bool isHovering = false;
    static bool isPressed = false;

    switch (msg) {
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);

        RECT rect;
        GetClientRect(hwnd, &rect);

        // Select colors based on state
        COLORREF bgColor = isPressed ? BUTTON_PRESS :
            isHovering ? BUTTON_HOVER : BUTTON_COLOR;

        // Create rounded rectangle
        HBRUSH bgBrush = CreateSolidBrush(bgColor);
        HPEN nullPen = CreatePen(PS_NULL, 0, 0);
        SelectObject(hdc, nullPen);
        SelectObject(hdc, bgBrush);
        RoundRect(hdc, rect.left, rect.top, rect.right, rect.bottom, 8, 8);

        // Draw text
        SetBkMode(hdc, TRANSPARENT);
        SetTextColor(hdc, RGB(255, 255, 255));

        wchar_t text[256];
        GetWindowText(hwnd, text, 256);

        HFONT hFont = CreateModernFont(12, true);
        SelectObject(hdc, hFont);
        DrawText(hdc, text, -1, &rect, DT_CENTER | DT_VCENTER | DT_SINGLELINE);

        // Cleanup
        DeleteObject(hFont);
        DeleteObject(bgBrush);
        DeleteObject(nullPen);

        EndPaint(hwnd, &ps);
        return 0;
    }

    case WM_MOUSEMOVE: {
        if (!isHovering) {
            isHovering = true;
            InvalidateRect(hwnd, NULL, FALSE);

            TRACKMOUSEEVENT tme = { sizeof(tme) };
            tme.dwFlags = TME_LEAVE;
            tme.hwndTrack = hwnd;
            TrackMouseEvent(&tme);
        }
        return 0;
    }

    case WM_MOUSELEAVE: {
        isHovering = false;
        InvalidateRect(hwnd, NULL, FALSE);
        return 0;
    }

    case WM_LBUTTONDOWN: {
        isPressed = true;
        InvalidateRect(hwnd, NULL, FALSE);
        return 0;
    }

    case WM_LBUTTONUP: {
        if (isPressed) {
            isPressed = false;
            InvalidateRect(hwnd, NULL, FALSE);
            SendMessage(GetParent(hwnd), WM_COMMAND, GetDlgCtrlID(hwnd), 0);
        }
        return 0;
    }
    }

    return DefWindowProc(hwnd, msg, wParam, lParam);
}

// Modern bar window procedure
LRESULT CALLBACK BarWindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    static int value = 0;
    static COLORREF barColor = RGB(0, 0, 0);

    switch (uMsg) {
    case WM_CREATE: {
        CREATESTRUCT* cs = (CREATESTRUCT*)lParam;
        barColor = (COLORREF)(DWORD_PTR)cs->lpCreateParams;
        return 0;
    }

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);

        RECT rect;
        GetClientRect(hwnd, &rect);

        // Draw background
        HBRUSH bgBrush = CreateSolidBrush(BAR_BG_COLOR);
        HPEN nullPen = CreatePen(PS_NULL, 0, 0);
        SelectObject(hdc, nullPen);
        SelectObject(hdc, bgBrush);
        RoundRect(hdc, rect.left, rect.top, rect.right, rect.bottom, 6, 6);

        // Draw value bar
        if (value > 0) {
            int barWidth = (int)((rect.right - rect.left) * value / 100.0f);
            RECT barRect = rect;
            barRect.right = barRect.left + barWidth;

            HBRUSH barBrush = CreateSolidBrush(barColor);
            SelectObject(hdc, barBrush);
            RoundRect(hdc, barRect.left, barRect.top, barRect.right, barRect.bottom, 6, 6);
            DeleteObject(barBrush);
        }

        DeleteObject(bgBrush);
        DeleteObject(nullPen);
        EndPaint(hwnd, &ps);
        return 0;
    }

    case WM_USER: {
        value = (int)wParam;
        InvalidateRect(hwnd, NULL, FALSE);
        UpdateWindow(hwnd);
        return 0;
    }
    }

    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

// DirectInput device enumeration callback
BOOL CALLBACK EnumDevicesCallback(LPCDIDEVICEINSTANCE lpddi, LPVOID pvRef) {
    std::wcout << L"\n=== Found Device ===\n";
    std::wcout << L"Instance Name: " << lpddi->tszInstanceName << std::endl;
    std::wcout << L"Product Name: " << lpddi->tszProductName << std::endl;

    WORD vid = HIWORD(lpddi->guidProduct.Data1);
    WORD pid = LOWORD(lpddi->guidProduct.Data1);

    std::wcout << L"VID_PID: " << std::hex << vid << L"_" << pid << std::dec << std::endl;

    if (pid != 0x1DD2 || vid != 0x2735) {
        std::wcout << L"Not our target device (VID_1DD2&PID_2735), continuing search..." << std::endl;
        return DIENUM_CONTINUE;
    }

    std::wcout << L"Found our target device!" << std::endl;

    HRESULT hr = g_pDI->CreateDevice(lpddi->guidInstance, &g_pDevice, NULL);
    if (FAILED(hr)) {
        std::wcerr << L"CreateDevice failed with error: 0x" << std::hex << hr << std::dec << std::endl;
        return DIENUM_CONTINUE;
    }

    hr = g_pDevice->SetDataFormat(&c_dfDIJoystick2);
    if (FAILED(hr)) {
        std::wcerr << L"SetDataFormat failed with error: 0x" << std::hex << hr << std::dec << std::endl;
        g_pDevice->Release();
        g_pDevice = nullptr;
        return DIENUM_CONTINUE;
    }

    return DIENUM_STOP;
}

// Reset calibration to defaults
void ResetCalibration() {
    DEBUG_PRINT(L"Resetting calibration to defaults", L"");
    g_xRange = { 0, 4095 };
    g_zRange = { 0, 4095 };
    g_ryRange = { 0, 4095 };
}

// Save calibration to registry
void SaveAxisCalibration(int axisIndex) {
    std::wstring calibrationData;
    DEBUG_PRINT(L"SaveAxisCalibration called for axis %d", axisIndex);

    switch (axisIndex) {
    case 0:
        calibrationData = L"MinX=" + std::to_wstring(g_xRange.min) +
            L";MaxX=" + std::to_wstring(g_xRange.max) + L";";
        break;
    case 1:
        calibrationData = L"MinZ=" + std::to_wstring(g_zRange.min) +
            L";MaxZ=" + std::to_wstring(g_zRange.max) + L";";
        break;
    case 2:
        calibrationData = L"MinRY=" + std::to_wstring(g_ryRange.min) +
            L";MaxRY=" + std::to_wstring(g_ryRange.max) + L";";
        break;
    }

    saveCalibrationToRegistry(calibrationData, axisIndex);
}

// Update thread function
DWORD WINAPI UpdateThread(LPVOID lpParam) {
    HWND hwnd = (HWND)lpParam;
    while (g_running) {
        SendMessage(hwnd, WM_USER, 0, 0);
        Sleep(10);
    }
    return 0;
}

// Main window procedure
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_CREATE: {
        // Create modern font
        g_hModernFont = CreateModernFont(14);

        // Create reset button
        HWND resetButton = CreateWindowEx(
            0, BUTTON_CLASS, L"Reset Calibration",
            WS_CHILD | WS_VISIBLE,
            20, 20, 150, 35, hwnd, (HMENU)ID_RESET_CALIBRATION,
            NULL, NULL);

        // X-axis controls
        HWND xLabel = CreateWindowW(L"STATIC", L"X-Axis Raw:",
            WS_CHILD | WS_VISIBLE,
            20, 70, 100, 20, hwnd, NULL, NULL, NULL);
        SendMessage(xLabel, WM_SETFONT, (WPARAM)g_hModernFont, TRUE);

        g_hwndXValue = CreateWindowW(L"STATIC", L"0",
            WS_CHILD | WS_VISIBLE | SS_LEFT,
            130, 70, 150, 20, hwnd, NULL, NULL, NULL);
        SendMessage(g_hwndXValue, WM_SETFONT, (WPARAM)g_hModernFont, TRUE);

        // X axis buttons
        CreateWindowEx(0, BUTTON_CLASS, L"Set Min",
            WS_CHILD | WS_VISIBLE,
            290, 70, 80, 30, hwnd, (HMENU)ID_X_SET_MIN, NULL, NULL);
        CreateWindowEx(0, BUTTON_CLASS, L"Set Max",
            WS_CHILD | WS_VISIBLE,
            380, 70, 80, 30, hwnd, (HMENU)ID_X_SET_MAX, NULL, NULL);

        // X axis bars
        g_hwndXRawBar = CreateWindowEx(0, BAR_CLASS, NULL,
            WS_CHILD | WS_VISIBLE,
            130, 95, 220, 20, hwnd, (HMENU)ID_X_RAW_BAR,
            NULL, (LPVOID)RAW_BAR_COLOR);
        g_hwndXCalBar = CreateWindowEx(0, BAR_CLASS, NULL,
            WS_CHILD | WS_VISIBLE,
            130, 120, 220, 20, hwnd, (HMENU)ID_X_CAL_BAR,
            NULL, (LPVOID)CAL_BAR_COLOR);

        // Z-axis controls
        HWND zLabel = CreateWindowW(L"STATIC", L"Z-Axis Raw:",
            WS_CHILD | WS_VISIBLE,
            20, 160, 100, 20, hwnd, NULL, NULL, NULL);
        SendMessage(zLabel, WM_SETFONT, (WPARAM)g_hModernFont, TRUE);

        g_hwndZValue = CreateWindowW(L"STATIC", L"0",
            WS_CHILD | WS_VISIBLE | SS_LEFT,
            130, 160, 150, 20, hwnd, NULL, NULL, NULL);
        SendMessage(g_hwndZValue, WM_SETFONT, (WPARAM)g_hModernFont, TRUE);

        // Z axis buttons
        CreateWindowEx(0, BUTTON_CLASS, L"Set Min",
            WS_CHILD | WS_VISIBLE,
            290, 160, 80, 30, hwnd, (HMENU)ID_Z_SET_MIN, NULL, NULL);
        CreateWindowEx(0, BUTTON_CLASS, L"Set Max",
            WS_CHILD | WS_VISIBLE,
            380, 160, 80, 30, hwnd, (HMENU)ID_Z_SET_MAX, NULL, NULL);

        // Z axis bars
        g_hwndZRawBar = CreateWindowEx(0, BAR_CLASS, NULL,
            WS_CHILD | WS_VISIBLE,
            130, 185, 220, 20, hwnd, (HMENU)ID_Z_RAW_BAR,
            NULL, (LPVOID)RAW_BAR_COLOR);
        g_hwndZCalBar = CreateWindowEx(0, BAR_CLASS, NULL,
            WS_CHILD | WS_VISIBLE,
            130, 210, 220, 20, hwnd, (HMENU)ID_Z_CAL_BAR,
            NULL, (LPVOID)CAL_BAR_COLOR);

        // RY-axis controls
        HWND ryLabel = CreateWindowW(L"STATIC", L"RY-Axis Raw:",
            WS_CHILD | WS_VISIBLE,
            20, 250, 100, 20, hwnd, NULL, NULL, NULL);
        SendMessage(ryLabel, WM_SETFONT, (WPARAM)g_hModernFont, TRUE);

        g_hwndRYValue = CreateWindowW(L"STATIC", L"0",
            WS_CHILD | WS_VISIBLE | SS_LEFT,
            130, 250, 150, 20, hwnd, NULL, NULL, NULL);
        SendMessage(g_hwndRYValue, WM_SETFONT, (WPARAM)g_hModernFont, TRUE);

        // RY axis buttons
        CreateWindowEx(0, BUTTON_CLASS, L"Set Min",
            WS_CHILD | WS_VISIBLE,
            290, 250, 80, 30, hwnd, (HMENU)ID_RY_SET_MIN, NULL, NULL);
        CreateWindowEx(0, BUTTON_CLASS, L"Set Max",
            WS_CHILD | WS_VISIBLE,
            380, 250, 80, 30, hwnd, (HMENU)ID_RY_SET_MAX, NULL, NULL);

        // RY axis bars
        g_hwndRYRawBar = CreateWindowEx(0, BAR_CLASS, NULL,
            WS_CHILD | WS_VISIBLE,
            130, 275, 220, 20, hwnd, (HMENU)ID_RY_RAW_BAR,
            NULL, (LPVOID)RAW_BAR_COLOR);
        g_hwndRYCalBar = CreateWindowEx(0, BAR_CLASS, NULL,
            WS_CHILD | WS_VISIBLE,
            130, 300, 220, 20, hwnd, (HMENU)ID_RY_CAL_BAR,
            NULL, (LPVOID)CAL_BAR_COLOR);

        break;
    }

    case WM_CTLCOLORSTATIC: {
        HDC hdcStatic = (HDC)wParam;
        SetTextColor(hdcStatic, TEXT_COLOR);
        SetBkColor(hdcStatic, WINDOW_BG_COLOR);
        return (LRESULT)GetStockObject(WHITE_BRUSH);
    }

    case WM_ERASEBKGND: {
        HDC hdc = (HDC)wParam;
        RECT rect;
        GetClientRect(hwnd, &rect);
        HBRUSH brush = CreateSolidBrush(WINDOW_BG_COLOR);
        FillRect(hdc, &rect, brush);
        DeleteObject(brush);
        return TRUE;
    }

    case WM_COMMAND: {
        switch (LOWORD(wParam)) {
        case ID_RESET_CALIBRATION:
            ResetCalibration();
            SaveAxisCalibration(0);
            SaveAxisCalibration(1);
            SaveAxisCalibration(2);
            break;

        case ID_X_SET_MIN:
            g_xRange.min = g_currentXRaw;
            SaveAxisCalibration(0);
            break;

        case ID_X_SET_MAX:
            g_xRange.max = g_currentXRaw;
            SaveAxisCalibration(0);
            break;

        case ID_Z_SET_MIN:
            g_zRange.min = g_currentZRaw;
            SaveAxisCalibration(1);
            break;

        case ID_Z_SET_MAX:
            g_zRange.max = g_currentZRaw;
            SaveAxisCalibration(1);
            break;

        case ID_RY_SET_MIN:
            g_ryRange.min = g_currentRYRaw;
            SaveAxisCalibration(2);
            break;

        case ID_RY_SET_MAX:
            g_ryRange.max = g_currentRYRaw;
            SaveAxisCalibration(2);
            break;
        }
        break;
    }

    case WM_USER: {
        if (g_pDevice) {
            DIJOYSTATE2 js;
            HRESULT hr = g_pDevice->Poll();
            if (FAILED(hr)) {
                g_pDevice->Acquire();
                hr = g_pDevice->Poll();
            }

            if (SUCCEEDED(g_pDevice->GetDeviceState(sizeof(DIJOYSTATE2), &js))) {
                // Update raw values
                g_currentXRaw = static_cast<LONG>(js.lX * (4095.0 / 65535.0));
                g_currentZRaw = static_cast<LONG>(js.lZ * (4095.0 / 65535.0));
                g_currentRYRaw = static_cast<LONG>(js.lRy * (4095.0 / 65535.0));

                // Calculate percentages
                int xRawPercent = (g_currentXRaw * 100) / 4095;
                int zRawPercent = (g_currentZRaw * 100) / 4095;
                int ryRawPercent = (g_currentRYRaw * 100) / 4095;

                // Calculate calibrated percentages
                int xCalPercent = (g_currentXRaw <= g_xRange.min) ? 0 :
                    (g_currentXRaw >= g_xRange.max) ? 100 :
                    ((g_currentXRaw - g_xRange.min) * 100) / (g_xRange.max - g_xRange.min);

                int zCalPercent = (g_currentZRaw <= g_zRange.min) ? 0 :
                    (g_currentZRaw >= g_zRange.max) ? 100 :
                    ((g_currentZRaw - g_zRange.min) * 100) / (g_zRange.max - g_zRange.min);

                int ryCalPercent = (g_currentRYRaw <= g_ryRange.min) ? 0 :
                    (g_currentRYRaw >= g_ryRange.max) ? 100 :
                    ((g_currentRYRaw - g_ryRange.min) * 100) / (g_ryRange.max - g_ryRange.min);

                // Update bars
                SendMessage(g_hwndXRawBar, WM_USER, xRawPercent, 0);
                SendMessage(g_hwndXCalBar, WM_USER, xCalPercent, 0);
                SendMessage(g_hwndZRawBar, WM_USER, zRawPercent, 0);
                SendMessage(g_hwndZCalBar, WM_USER, zCalPercent, 0);
                SendMessage(g_hwndRYRawBar, WM_USER, ryRawPercent, 0);
                SendMessage(g_hwndRYCalBar, WM_USER, ryCalPercent, 0);

                // Update text values
                wchar_t buffer[50];
                swprintf_s(buffer, 50, L"%d (%d%%)", g_currentXRaw, xRawPercent);
                SetWindowTextW(g_hwndXValue, buffer);
                swprintf_s(buffer, 50, L"%d (%d%%)", g_currentZRaw, zRawPercent);
                SetWindowTextW(g_hwndZValue, buffer);
                swprintf_s(buffer, 50, L"%d (%d%%)", g_currentRYRaw, ryRawPercent);
                SetWindowTextW(g_hwndRYValue, buffer);
            }
        }
        break;
    }

    case WM_DESTROY:
        if (g_hModernFont) DeleteObject(g_hModernFont);
        g_running = false;
        PostQuitMessage(0);
        break;

    default:
        return DefWindowProc(hwnd, uMsg, wParam, lParam);
    }
    return 0;
}

// Entry point
int WINAPI wWinMain(
    _In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPWSTR lpCmdLine,
    _In_ int nCmdShow)
{
    AllocConsole();
    FILE* dummy;
    freopen_s(&dummy, "CONOUT$", "w", stdout);
    freopen_s(&dummy, "CONOUT$", "w", stderr);

    // Register the modern button class
    WNDCLASSW wcButton = {};
    wcButton.lpfnWndProc = ModernButtonProc;
    wcButton.hInstance = hInstance;
    wcButton.lpszClassName = BUTTON_CLASS;
    wcButton.hCursor = LoadCursor(NULL, IDC_HAND);
    RegisterClassW(&wcButton);

    // Register the bar class
    WNDCLASSW wcBar = {};
    wcBar.lpfnWndProc = BarWindowProc;
    wcBar.hInstance = hInstance;
    wcBar.lpszClassName = BAR_CLASS;
    RegisterClassW(&wcBar);

    // Register main window class
    WNDCLASSW wc = {};
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"ModernCalibration";
    wc.hbrBackground = CreateSolidBrush(WINDOW_BG_COLOR);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    RegisterClassW(&wc);

    // Initialize DirectInput
    HRESULT hr = DirectInput8Create(hInstance, DIRECTINPUT_VERSION, IID_IDirectInput8, (VOID**)&g_pDI, NULL);
    if (FAILED(hr)) {
        MessageBoxW(NULL, L"Failed to initialize DirectInput", L"Error", MB_OK | MB_ICONERROR);
        return 1;
    }

    // Create main window
    HWND hwnd = CreateWindowExW(
        0, L"ModernCalibration",
        L"Modern Axis Calibration",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, CW_USEDEFAULT,
        500, 400,
        NULL, NULL, hInstance, NULL);

    ShowWindow(hwnd, nCmdShow);
    UpdateWindow(hwnd);

    // Setup DirectInput device
    hr = g_pDI->EnumDevices(DI8DEVCLASS_GAMECTRL, EnumDevicesCallback, NULL, DIEDFL_ATTACHEDONLY);
    if (g_pDevice) {
        g_pDevice->SetCooperativeLevel(hwnd, DISCL_BACKGROUND | DISCL_NONEXCLUSIVE);
        g_pDevice->Acquire();
    }
    else {
        MessageBoxW(NULL, L"No game controller found", L"Warning", MB_OK | MB_ICONWARNING);
    }

    // Create update thread
    CreateThread(NULL, 0, UpdateThread, hwnd, 0, NULL);

    // Message loop
    MSG msg = {};
    while (GetMessage(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    // Cleanup
    if (g_pDevice) {
        g_pDevice->Unacquire();
        g_pDevice->Release();
    }
    if (g_pDI) g_pDI->Release();
    FreeConsole();

    return 0;
}