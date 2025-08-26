#!/usr/bin/env python3
"""
Build script for HidHide Helper .NET application.
Requires .NET 7.0 SDK or later.
"""
import os
import subprocess
import sys

def build_hidhide_helper():
    """Build the HidHide helper executable."""
    print("🔧 Building HidHide Helper...")
    
    # Check if .NET SDK is available
    try:
        result = subprocess.run(['dotnet', '--version'], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("❌ .NET SDK not found. Please install .NET 7.0 SDK or later.")
            print("   Download from: https://dotnet.microsoft.com/download")
            return False
        print(f"✅ .NET SDK version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ .NET SDK not found. Please install .NET 7.0 SDK or later.")
        print("   Download from: https://dotnet.microsoft.com/download")
        return False
    
    # Change to the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    try:
        # Restore packages
        print("📦 Restoring NuGet packages...")
        subprocess.run(['dotnet', 'restore'], check=True)
        
        # Build and publish
        print("🔨 Building and publishing...")
        subprocess.run([
            'dotnet', 'publish', 
            '-c', 'Release', 
            '-r', 'win-x64', 
            '--self-contained', 'false'
        ], check=True)
        
        # Check if the executable was created
        exe_path = os.path.join(project_dir, "bin", "Release", "net7.0-windows", "win-x64", "publish", "HidHideHelper.exe")
        if os.path.exists(exe_path):
            print(f"✅ HidHide Helper built successfully: {exe_path}")
            return True
        else:
            print("❌ HidHide Helper executable not found after build")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = build_hidhide_helper()
    sys.exit(0 if success else 1)
