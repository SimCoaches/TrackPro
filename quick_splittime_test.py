#!/usr/bin/env python3
"""
SIMPLE SplitTimeInfo Test - Just tell us what's in there!

This script connects to iRacing and immediately dumps the SplitTimeInfo
content so we can see if sector times are there or not.
"""

import sys
import os
import time

# Add the trackpro module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trackpro'))

try:
    from trackpro.race_coach.pyirsdk import irsdk
except ImportError:
    try:
        import irsdk
    except ImportError:
        print("❌ Error: pyirsdk not found")
        sys.exit(1)

def main():
    print("🔬 SIMPLE SplitTimeInfo Test")
    print("=" * 40)
    
    # Connect to iRacing
    ir = irsdk.IRSDK()
    if not ir.startup():
        print("❌ iRacing not running")
        return
    
    if not ir.is_connected:
        print("❌ Not connected to iRacing session")
        return
    
    print("✅ Connected to iRacing!")
    
    # Wait for a lap completion
    print("🏁 Waiting for lap completion...")
    last_lap_completed = ir['LapCompleted']
    print(f"📊 Current lap completed: {last_lap_completed}")
    
    # Monitor for lap completion
    while ir.is_connected:
        ir.freeze_var_buffer_latest()
        current_lap_completed = ir['LapCompleted']
        
        if current_lap_completed > last_lap_completed:
            print(f"\n🏁 LAP COMPLETED: {last_lap_completed} -> {current_lap_completed}")
            
            # Try multiple methods to get SplitTimeInfo
            print("🔍 Checking SplitTimeInfo content...")
            
            # Method 1: Try _get_session_info with SplitTimeInfo key
            try:
                split_info = ir._get_session_info('SplitTimeInfo')
                if split_info:
                    print("✅ Method 1 SUCCESS: _get_session_info('SplitTimeInfo')")
                    print(f"📊 SplitTimeInfo keys: {list(split_info.keys())}")
                    
                    # Check for timing fields
                    timing_fields = ['LastLapTime', 'BestLapTime', 'CurrentLapTime']
                    for field in timing_fields:
                        if field in split_info:
                            print(f"   ⏱️ {field}: {split_info[field]}")
                    
                    # Check sectors
                    sectors = split_info.get('Sectors', [])
                    print(f"📊 Found {len(sectors)} sectors:")
                    
                    for i, sector in enumerate(sectors):
                        print(f"   🏁 Sector {i}: {sector}")
                        
                        # Look for timing in sectors
                        if isinstance(sector, dict):
                            timing_keys = [k for k in sector.keys() if 'time' in k.lower() or 'split' in k.lower()]
                            if timing_keys:
                                print(f"      ⏱️ TIMING FOUND: {timing_keys}")
                                for key in timing_keys:
                                    print(f"         {key}: {sector[key]}")
                            else:
                                print(f"      ❌ No timing keys in sector")
                    
                    break  # Found what we need
                else:
                    print("❌ Method 1 FAILED: No SplitTimeInfo returned")
            except Exception as e:
                print(f"❌ Method 1 FAILED: {e}")
            
            # Method 2: Try dictionary access
            try:
                session_info_raw = ir['SessionInfo']
                if session_info_raw and 'SplitTimeInfo' in session_info_raw:
                    print("✅ Method 2: Found SplitTimeInfo in SessionInfo")
                    # Extract just the SplitTimeInfo section
                    lines = session_info_raw.split('\n')
                    in_split_section = False
                    split_lines = []
                    
                    for line in lines:
                        if line.strip() == 'SplitTimeInfo:':
                            in_split_section = True
                            split_lines.append(line)
                        elif in_split_section:
                            if line.startswith(' ') or line.startswith('\t'):
                                split_lines.append(line)
                            else:
                                break
                    
                    if split_lines:
                        print("📊 Raw SplitTimeInfo section:")
                        for line in split_lines[:20]:  # Show first 20 lines
                            print(f"   {line}")
                        
                        # Look for timing keywords
                        split_text = '\n'.join(split_lines)
                        timing_keywords = ['Time:', 'Split:', 'Best:', 'Last:', 'Current:']
                        found_timing = []
                        
                        for keyword in timing_keywords:
                            if keyword in split_text:
                                found_timing.append(keyword)
                        
                        if found_timing:
                            print(f"⏱️ TIMING KEYWORDS FOUND: {found_timing}")
                        else:
                            print("❌ No timing keywords found")
                else:
                    print("❌ Method 2 FAILED: No SplitTimeInfo in SessionInfo")
            except Exception as e:
                print(f"❌ Method 2 FAILED: {e}")
            
            break
        
        time.sleep(0.1)
    
    print("\n🏁 Test complete!")
    ir.shutdown()

if __name__ == "__main__":
    main() 