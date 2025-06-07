#!/usr/bin/env python3
"""
Quick test to check what wheel RPM fields are available in iRacing
"""

import irsdk
import time

def check_wheel_fields():
    """Check what wheel-related fields are available in iRacing."""
    print("Connecting to iRacing...")
    
    ir = irsdk.IRSDK()
    result = ir.startup()
    
    if not result or not ir.is_connected:
        print("ERROR: Not connected to iRacing")
        return
    
    print("Connected to iRacing!")
    
    # Get all available variable headers
    headers = ir._var_headers_dict
    if not headers:
        print("ERROR: No headers found")
        return
    
    print(f"Total fields available: {len(headers)}")
    
    # Look for wheel-related fields
    wheel_fields = []
    rpm_fields = []
    
    for name in headers.keys():
        name_lower = name.lower()
        if 'wheel' in name_lower:
            wheel_fields.append(name)
        if 'rpm' in name_lower:
            rpm_fields.append(name)
    
    print(f"\nWheel-related fields ({len(wheel_fields)}):")
    for field in sorted(wheel_fields):
        print(f"  {field}")
    
    print(f"\nRPM-related fields ({len(rpm_fields)}):")
    for field in sorted(rpm_fields):
        print(f"  {field}")
    
    # Test accessing the correct array fields (try multiple variations)
    array_fields = [
        'WheelsRPS', 'WheelRPS', 'WheelRotationSpeed',
        'WheelsSpeed', 'WheelSpeed', 'WheelLinearSpeed', 
        'TireCircumference', 'TireCircumf', 'WheelCircumference'
    ]
    
    print(f"\nTesting iRacing array fields:")
    found_arrays = []
    for field in array_fields:
        try:
            value = ir[field]
            found_arrays.append((field, value))
            print(f"  ✓ {field} = {value}")
            
            # If it's WheelsRPS, show RPM conversion
            if field == 'WheelsRPS' and value is not None:
                import numpy as np
                rps_array = np.array(value) if hasattr(value, '__len__') else [value]
                rpm_array = rps_array * 60.0
                print(f"    → RPM = {rpm_array}")
                print(f"    → LF={rpm_array[0]:.0f}, RF={rpm_array[1]:.0f}, LR={rpm_array[2]:.0f}, RR={rpm_array[3]:.0f}")
                
        except Exception as e:
            print(f"  X {field}: {e}")
    
    # Test individual wheel patterns (legacy check)
    test_fields = ['WheelLFRPM', 'WheelRFRPM', 'WheelLRRPM', 'WheelRRRPM']
    print(f"\nTesting individual wheel RPM fields (should be None):")
    for field in test_fields:
        try:
            value = ir[field]
            print(f"  ✓ {field} = {value}")
        except Exception as e:
            print(f"  X {field}: {e}")
    
    if not found_arrays:
        print("  X No wheel array fields found")
    
    # Try to get current telemetry to see if data is flowing
    print(f"\n=== Current Telemetry Status ===")
    telemetry_fields = ['Speed', 'RPM', 'Gear', 'Throttle', 'Brake', 'OnTrack', 'IsOnTrack']
    
    for field in telemetry_fields:
        try:
            value = ir[field]
            if field == 'Speed' and value and value > 0:
                print(f"  ✓ {field} = {value} m/s ({value * 3.6:.1f} km/h)")
            else:
                print(f"  ✓ {field} = {value}")
        except Exception as e:
            print(f"  X {field}: {e}")
    
    # Check if we're actively driving
    try:
        speed = ir['Speed']
        on_track = ir.get('OnTrack', ir.get('IsOnTrack', 'unknown'))
        
        if speed is None or speed == 0:
            print(f"\n⚠️  WARNING: Speed is {speed} - you may not be driving")
        if on_track is False:
            print(f"⚠️  WARNING: OnTrack is {on_track} - you may be in pits/garage")
            
    except Exception as e:
        print(f"\nCould not check driving status: {e}")
    
    ir.shutdown()
    print("\nDisconnected from iRacing")

if __name__ == "__main__":
    check_wheel_fields() 