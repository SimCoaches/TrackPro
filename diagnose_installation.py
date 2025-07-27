#!/usr/bin/env python3
"""
TrackPro Installation Diagnostics Tool

This tool helps diagnose and troubleshoot issues with HidHide and VJoy installations
that are required for TrackPro's pedal manipulation functionality.

Usage:
    python diagnose_installation.py
"""

import os
import sys
import subprocess
import winreg
import json
import time
from pathlib import Path
import requests
from urllib.parse import urlparse

# Add the trackpro directory to path so we can import the modules
sys.path.insert(0, 'trackpro')

try:
    from trackpro.pedals.hidhide import HidHideClient
    from trackpro.pedals.vjoy_installer import VJoyInstaller, get_vjoy_status
except ImportError as e:
    print(f"Warning: Could not import TrackPro modules: {e}")
    HidHideClient = None
    VJoyInstaller = None
    get_vjoy_status = None

class InstallationDiagnostics:
    """Comprehensive diagnostics for TrackPro installation issues."""
    
    def __init__(self):
        self.results = {}
        
    def run_all_diagnostics(self):
        """Run all diagnostic checks."""
        print("=" * 60)
        print("TrackPro Installation Diagnostics")
        print("=" * 60)
        print()
        
        # System information
        self.check_system_info()
        print()
        
        # Windows version compatibility
        self.check_windows_compatibility()
        print()
        
        # HidHide diagnostics
        self.check_hidhide_installation()
        print()
        
        # VJoy diagnostics
        self.check_vjoy_installation()
        print()
        
        # Download URL verification
        self.check_download_urls()
        print()
        
        # Administrative privileges
        self.check_admin_privileges()
        print()
        
        # Generate summary
        self.generate_summary()
        
    def check_system_info(self):
        """Check basic system information."""
        print("--- System Information ---")
        
        try:
            import platform
            system_info = {
                'OS': platform.system(),
                'Version': platform.version(),
                'Release': platform.release(),
                'Architecture': platform.architecture()[0],
                'Machine': platform.machine(),
                'Python Version': platform.python_version()
            }
            
            for key, value in system_info.items():
                print(f"  {key}: {value}")
                
            self.results['system_info'] = system_info
            
        except Exception as e:
            print(f"  ❌ Error getting system info: {e}")
            self.results['system_info'] = {'error': str(e)}
    
    def check_windows_compatibility(self):
        """Check Windows version compatibility."""
        print("--- Windows Compatibility ---")
        
        try:
            import platform
            windows_version = platform.version()
            release = platform.release()
            
            # Check for Windows 10/11
            if "10." in windows_version:
                build_number = int(windows_version.split('.')[-1])
                
                if build_number >= 22000:  # Windows 11
                    print(f"  ✅ Windows 11 detected (Build {build_number})")
                    compatibility = "excellent"
                elif build_number >= 19041:  # Windows 10 2004+
                    print(f"  ✅ Windows 10 (Build {build_number}) - Good compatibility")
                    compatibility = "good"
                elif build_number >= 18362:  # Windows 10 1903+
                    print(f"  ⚠️  Windows 10 (Build {build_number}) - May have issues")
                    compatibility = "fair"
                else:
                    print(f"  ❌ Windows 10 (Build {build_number}) - Likely compatibility issues")
                    compatibility = "poor"
            else:
                print(f"  ❌ Unsupported Windows version: {release}")
                compatibility = "unsupported"
                
            self.results['windows_compatibility'] = {
                'version': windows_version,
                'release': release,
                'compatibility': compatibility
            }
            
        except Exception as e:
            print(f"  ❌ Error checking Windows compatibility: {e}")
            self.results['windows_compatibility'] = {'error': str(e)}
    
    def check_hidhide_installation(self):
        """Check HidHide installation status."""
        print("--- HidHide Installation ---")
        
        try:
            if HidHideClient is None:
                print("  ❌ HidHide module could not be imported")
                self.results['hidhide'] = {'error': 'module_import_failed'}
                return
            
            try:
                hidhide = HidHideClient(fail_silently=True)
                
                # Check if HidHide is installed
                service_running = hidhide.check_hidhide_service()
                print(f"  HidHide Service Running: {'✅ Yes' if service_running else '❌ No'}")
                
                # Check for CLI tool
                cli_path = hidhide._find_cli()
                if cli_path:
                    print(f"  ✅ HidHide CLI found: {cli_path}")
                    cli_found = True
                else:
                    print("  ❌ HidHide CLI not found")
                    cli_found = False
                
                # Check if functioning
                functioning = hidhide.functioning
                print(f"  HidHide Functioning: {'✅ Yes' if functioning else '❌ No'}")
                
                # Try to get device list
                try:
                    hidden_devices = hidhide._run_cli(["--dev-list"], check_output=True, ignore_errors=True)
                    if hidden_devices:
                        device_count = len([line for line in hidden_devices.splitlines() if line.strip()])
                        print(f"  ✅ Hidden devices: {device_count}")
                    else:
                        print("  ℹ️  No devices currently hidden")
                except Exception as e:
                    print(f"  ⚠️  Could not get device list: {e}")
                
                self.results['hidhide'] = {
                    'service_running': service_running,
                    'cli_found': cli_found,
                    'cli_path': cli_path,
                    'functioning': functioning
                }
                
            except Exception as e:
                print(f"  ❌ Error checking HidHide: {e}")
                self.results['hidhide'] = {'error': str(e)}
                
        except Exception as e:
            print(f"  ❌ Critical error with HidHide diagnostics: {e}")
            self.results['hidhide'] = {'critical_error': str(e)}
    
    def check_vjoy_installation(self):
        """Check VJoy installation status."""
        print("--- VJoy Installation ---")
        
        try:
            if VJoyInstaller is None or get_vjoy_status is None:
                print("  ❌ VJoy module could not be imported")
                self.results['vjoy'] = {'error': 'module_import_failed'}
                return
            
            try:
                vjoy_info = get_vjoy_status()
                
                if vjoy_info['installed']:
                    print(f"  ✅ VJoy installed (Version: {vjoy_info.get('version', 'Unknown')})")
                    
                    if vjoy_info['dll_paths']:
                        print(f"  ✅ VJoy DLLs found: {len(vjoy_info['dll_paths'])} locations")
                        for dll_path in vjoy_info['dll_paths']:
                            print(f"    - {dll_path}")
                    else:
                        print("  ⚠️  No VJoy DLLs found")
                    
                    if vjoy_info['install_path']:
                        print(f"  ✅ Install path: {vjoy_info['install_path']}")
                    
                    if vjoy_info['configuration_tool']:
                        print(f"  ✅ Configuration tool: {vjoy_info['configuration_tool']}")
                    else:
                        print("  ⚠️  Configuration tool not found")
                        
                    # Test functionality
                    try:
                        installer = VJoyInstaller(fail_silently=True)
                        functional = installer.verify_vjoy_functionality()
                        print(f"  VJoy Functionality: {'✅ Working' if functional else '❌ Not working'}")
                        vjoy_info['functional'] = functional
                    except Exception as e:
                        print(f"  ⚠️  Could not test VJoy functionality: {e}")
                        vjoy_info['functional'] = None
                        
                else:
                    print("  ❌ VJoy is not installed")
                
                self.results['vjoy'] = vjoy_info
                
            except Exception as e:
                print(f"  ❌ Error checking VJoy: {e}")
                self.results['vjoy'] = {'error': str(e)}
                
        except Exception as e:
            print(f"  ❌ Critical error with VJoy diagnostics: {e}")
            self.results['vjoy'] = {'critical_error': str(e)}
    
    def check_download_urls(self):
        """Verify that download URLs are accessible."""
        print("--- Download URL Verification ---")
        
        # URLs to check
        urls = {
            "VJoy (Primary)": "https://github.com/njz3/vJoy/releases/download/v2.2.1.1/vJoySetup.exe",
            "VJoy (Fallback)": "https://github.com/jshafer817/vJoy/releases/download/v2.1.9.1/vJoySetup.exe",
            "HidHide (Primary)": "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHide_1.5.230_x64.exe",
            "HidHide (Fallback)": "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/HidHideSetup.exe",
            "Visual C++ Redistributable": "https://aka.ms/vs/17/release/vc_redist.x64.exe"
        }
        
        url_results = {}
        
        for name, url in urls.items():
            try:
                print(f"  Checking {name}...", end="")
                response = requests.head(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    size = response.headers.get('content-length')
                    if size:
                        size_mb = int(size) / (1024 * 1024)
                        print(f" ✅ Available ({size_mb:.1f} MB)")
                        url_results[name] = {'status': 'available', 'size_mb': size_mb}
                    else:
                        print(" ✅ Available (size unknown)")
                        url_results[name] = {'status': 'available', 'size_mb': None}
                else:
                    print(f" ❌ HTTP {response.status_code}")
                    url_results[name] = {'status': f'http_{response.status_code}'}
                    
            except requests.exceptions.Timeout:
                print(" ⚠️  Timeout")
                url_results[name] = {'status': 'timeout'}
            except requests.exceptions.ConnectionError:
                print(" ❌ Connection error")
                url_results[name] = {'status': 'connection_error'}
            except Exception as e:
                print(f" ❌ Error: {e}")
                url_results[name] = {'status': 'error', 'error': str(e)}
        
        self.results['download_urls'] = url_results
    
    def check_admin_privileges(self):
        """Check administrative privileges."""
        print("--- Administrative Privileges ---")
        
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            
            if is_admin:
                print("  ✅ Running with administrator privileges")
            else:
                print("  ⚠️  Not running with administrator privileges")
                print("     (May be required for driver installation)")
            
            self.results['admin_privileges'] = is_admin
            
        except Exception as e:
            print(f"  ❌ Error checking admin privileges: {e}")
            self.results['admin_privileges'] = {'error': str(e)}
    
    def generate_summary(self):
        """Generate a summary of findings."""
        print("=" * 60)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 60)
        
        issues = []
        warnings = []
        good_items = []
        
        # Analyze results
        if 'windows_compatibility' in self.results:
            compat = self.results['windows_compatibility'].get('compatibility', 'unknown')
            if compat in ['poor', 'unsupported']:
                issues.append("Windows version may not be compatible")
            elif compat == 'fair':
                warnings.append("Windows version has limited compatibility")
            else:
                good_items.append("Windows version is compatible")
        
        if 'hidhide' in self.results:
            hidhide = self.results['hidhide']
            if hidhide.get('error') or hidhide.get('critical_error'):
                issues.append("HidHide has critical errors")
            elif not hidhide.get('service_running', False):
                issues.append("HidHide service is not running")
            elif not hidhide.get('cli_found', False):
                issues.append("HidHide CLI tool not found")
            elif not hidhide.get('functioning', False):
                warnings.append("HidHide may not be functioning properly")
            else:
                good_items.append("HidHide is working correctly")
        
        if 'vjoy' in self.results:
            vjoy = self.results['vjoy']
            if vjoy.get('error') or vjoy.get('critical_error'):
                issues.append("VJoy has critical errors")
            elif not vjoy.get('installed', False):
                warnings.append("VJoy is not installed")
            elif vjoy.get('functional') == False:
                warnings.append("VJoy is installed but not functional")
            elif vjoy.get('installed', False):
                good_items.append("VJoy is working correctly")
        
        if 'admin_privileges' in self.results:
            if not self.results['admin_privileges']:
                warnings.append("Not running with administrator privileges")
        
        # Print summary
        if good_items:
            print("\n✅ WORKING CORRECTLY:")
            for item in good_items:
                print(f"   • {item}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings:
                print(f"   • {warning}")
        
        if issues:
            print("\n❌ CRITICAL ISSUES:")
            for issue in issues:
                print(f"   • {issue}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        if issues or warnings:
            if any("HidHide" in issue for issue in issues):
                print("   1. Reinstall HidHide from: https://github.com/nefarius/HidHide/releases")
                print("   2. Reboot after installation")
            
            if any("VJoy" in warning for warning in warnings):
                print("   3. Install VJoy from: https://github.com/njz3/vJoy/releases")
                print("   4. Configure VJoy after installation")
            
            if any("administrator" in warning.lower() for warning in warnings):
                print("   5. Run TrackPro installer as Administrator")
            
            if any("Windows" in issue for issue in issues):
                print("   6. Consider upgrading to Windows 10 (build 19041+) or Windows 11")
        else:
            print("   • All systems appear to be working correctly!")
        
        # Save results to file
        try:
            results_file = "trackpro_diagnostics.json"
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\n📄 Detailed results saved to: {results_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save results file: {e}")

def main():
    """Main diagnostic function."""
    print("TrackPro Installation Diagnostics Tool")
    print("This tool will check for common installation issues with HidHide and VJoy")
    print()
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    diagnostics = InstallationDiagnostics()
    diagnostics.run_all_diagnostics()
    
    print("\n" + "=" * 60)
    print("Diagnostics complete!")
    print("\nIf you're still experiencing issues:")
    print("1. Share the generated 'trackpro_diagnostics.json' file with support")
    print("2. Try running the installer as Administrator")
    print("3. Temporarily disable antivirus software during installation")
    print("4. Check Windows Event Logs for additional error details")

if __name__ == "__main__":
    main() 