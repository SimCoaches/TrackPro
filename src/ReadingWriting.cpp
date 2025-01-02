#include "CalibrationHandler.h"
#include "RegistryHandler.h"
#include <iostream>

// Function for testing calibration handling
void testCalibrationHandling() {
    // Read existing calibration data
    readCalibrationData();

    // Define test calibration data
    std::wstring testData = L"MinX=440;MaxX=3790;MinY=0;MaxY=4096;Deadzone=0;";

    // Save calibration data for a specific axis (e.g., 0 for X-axis)
    saveCalibrationToRegistry(testData, 0);  // Pass axis index (0 for X-axis, 1 for Z-axis, etc.)
}
