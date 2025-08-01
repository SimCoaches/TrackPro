#!/usr/bin/env python3
"""
Test script to verify resource loading works correctly in both dev and packaged modes.
"""
import os
import sys

def test_resource_loading():
    """Test if all critical resources can be loaded."""
    print("="*60)
    print("RESOURCE LOADING TEST")
    print("="*60)
    
    # Check if we're in packaged mode
    is_packaged = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    print(f"Running mode: {'PACKAGED' if is_packaged else 'DEVELOPMENT'}")
    
    if is_packaged:
        print(f"_MEIPASS: {sys._MEIPASS}")
    
    # Import resource utils
    try:
        from trackpro.utils.resource_utils import get_resource_path
        print("✅ Successfully imported resource_utils")
    except ImportError as e:
        print(f"❌ Failed to import resource_utils: {e}")
        return False
    
    # Test critical resources
    critical_resources = [
        "trackpro/resources/images/splash_background.png",
        "trackpro/resources/images/trackpro_logo_small.png", 
        "trackpro/resources/images/2_pedal_set.png",
        "trackpro/resources/images/3_pedal_set.png",
        "trackpro/resources/icons/trackpro_tray.ico"
    ]
    
    print("\nTesting critical resources:")
    print("-" * 40)
    
    all_found = True
    for resource in critical_resources:
        try:
            path = get_resource_path(resource)
            exists = os.path.exists(path)
            status = "✅" if exists else "❌"
            size = f"({os.path.getsize(path)} bytes)" if exists else "(missing)"
            print(f"{status} {resource}")
            print(f"    Path: {path} {size}")
            
            if not exists:
                all_found = False
                
        except Exception as e:
            print(f"❌ {resource}")
            print(f"    Error: {e}")
            all_found = False
    
    # If packaged, show directory structure
    if is_packaged:
        print("\nPackaged app directory structure:")
        print("-" * 40)
        try:
            base = sys._MEIPASS
            for root, dirs, files in os.walk(base):
                level = root.replace(base, '').count(os.sep)
                indent = ' ' * 2 * level
                rel_path = os.path.relpath(root, base)
                if rel_path == '.':
                    rel_path = '<root>'
                print(f"{indent}{rel_path}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # Limit to first 5 files per directory
                    print(f"{subindent}{file}")
                if len(files) > 5:
                    print(f"{subindent}... and {len(files) - 5} more files")
                if level > 3:  # Limit depth
                    break
        except Exception as e:
            print(f"Error walking directory: {e}")
    
    print("\n" + "="*60)
    if all_found:
        print("🎉 ALL RESOURCES FOUND - Build packaging is working correctly!")
    else:
        print("⚠️  SOME RESOURCES MISSING - There may be an issue with the build")
    print("="*60)
    
    return all_found

if __name__ == "__main__":
    success = test_resource_loading()
    sys.exit(0 if success else 1)