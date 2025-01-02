// RegistryHandler.h
#ifndef REGISTRY_HANDLER_H
#define REGISTRY_HANDLER_H

#include <windows.h>
#include <string>

void saveCalibrationToRegistry(const std::wstring& calibrationData, int axisIndex);
void refreshDeviceState();  // Keep as void to match existing code
void readCalibrationData();

struct AxisRange {
    LONG min;
    LONG max;
};

#endif // REGISTRY_HANDLER_H
