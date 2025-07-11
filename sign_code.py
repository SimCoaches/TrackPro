#!/usr/bin/env python3
"""
Code Signing Script for TrackPro
Handles signing executables and installers with EV certificate
"""

import os
import sys
import subprocess
import winreg
from pathlib import Path

class CodeSigner:
    def __init__(self):
        self.signtool_path = self.find_signtool()
        self.certificate_info = None
        self.cert_file_path = self.find_local_certificate()
        
    def find_signtool(self):
        """Find signtool.exe in common Windows SDK locations."""
        print("Looking for signtool.exe...")
        
        # Try to find in PATH first
        try:
            result = subprocess.run(["where", "signtool"], 
                                  capture_output=True, text=True, check=True)
            path = result.stdout.strip().split('\n')[0]
            if os.path.exists(path):
                print(f"✓ Found signtool.exe in PATH: {path}")
                return path
        except subprocess.CalledProcessError:
            pass
        
        # Common Windows SDK locations
        sdk_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x64\signtool.exe",
            r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
            r"C:\Program Files\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
            r"C:\Program Files\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
            r"C:\Program Files\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
            r"C:\Program Files\Windows Kits\10\bin\10.0.18362.0\x64\signtool.exe",
            r"C:\Program Files\Windows Kits\10\bin\x64\signtool.exe",
        ]
        
        for path in sdk_paths:
            if os.path.exists(path):
                print(f"✓ Found signtool.exe at: {path}")
                return path
        
        print("✗ signtool.exe not found!")
        print("\nTo install Windows SDK (includes signtool.exe):")
        print("1. Go to: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
        print("2. Download and install Windows 10/11 SDK")
        print("3. Or install via Visual Studio Installer -> Individual Components -> Windows 10/11 SDK")
        return None
    
    def find_local_certificate(self):
        """Find certificate files in the local docs/cert directory."""
        cert_paths = [
            "docs/cert/simcoaches.cer",
            "docs/cert/simcoaches.pfx", 
            "docs/cert/simcoaches.p12",
            "docs/cert/certificate.pfx",
            "docs/cert/certificate.p12",
            "docs/cert/certificate.cer"
        ]
        
        for cert_path in cert_paths:
            if os.path.exists(cert_path):
                print(f"✓ Found local certificate file: {cert_path}")
                return cert_path
        
        return None
    
    def find_certificate(self, subject_name=None):
        """Find the EV certificate in the certificate store."""
        print("\nLooking for EV certificate...")
        
        if not self.signtool_path:
            print("✗ Cannot check certificates without signtool.exe")
            return False
        
        try:
            # List available certificates
            cmd = [self.signtool_path, "sign", "/?"]
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            # Try to find certificates in the personal store
            store_cmd = ["powershell", "-Command", 
                        "Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object {$_.HasPrivateKey -eq $true -and $_.NotAfter -gt (Get-Date)} | Select-Object Subject, Thumbprint, NotAfter"]
            
            cert_result = subprocess.run(store_cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            
            if cert_result.returncode == 0 and cert_result.stdout.strip():
                print("Available certificates:")
                print(cert_result.stdout)
                
                # Look for EV certificate indicators (Sectigo, EV, etc.)
                lines = cert_result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line.upper() for keyword in ['SECTIGO', 'COMODO', 'EV', 'EXTENDED']):
                        print(f"✓ Potential EV certificate found: {line}")
                        return True
                
                return True
            else:
                print("No certificates found in CurrentUser\\My store")
                
                # Also check LocalMachine store
                machine_cmd = ["powershell", "-Command", 
                              "Get-ChildItem -Path Cert:\\LocalMachine\\My | Where-Object {$_.HasPrivateKey -eq $true -and $_.NotAfter -gt (Get-Date)} | Select-Object Subject, Thumbprint, NotAfter"]
                
                machine_result = subprocess.run(machine_cmd, capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
                if machine_result.returncode == 0 and machine_result.stdout.strip():
                    print("Certificates in LocalMachine store:")
                    print(machine_result.stdout)
                    return True
                
                return False
                
        except Exception as e:
            print(f"Error checking certificates: {e}")
            return False
    
    def sign_file(self, file_path, description="TrackPro Application", timestamp_url="http://timestamp.sectigo.com"):
        """Sign a file with the EV certificate."""
        if not self.signtool_path:
            print("✗ Cannot sign file: signtool.exe not found")
            return False
        
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            return False
        
        print(f"\nSigning file: {file_path}")
        
        # Method 1: Try using local certificate file if it's a PFX/P12
        if self.cert_file_path and self.cert_file_path.lower().endswith(('.pfx', '.p12')):
            print(f"Attempting to sign with local certificate file: {self.cert_file_path}")
            password = input(f"Enter password for {self.cert_file_path}: ").strip()
            if password:
                success = self.sign_file_with_pfx(file_path, self.cert_file_path, password, description)
                if success:
                    return True
                else:
                    print("Failed to sign with local certificate file, trying certificate store...")
        
        # Method 2: Try different approaches for EV certificates
        
        # First try: No timestamp (EV certs often have timestamp issues)
        cmd = [
            self.signtool_path,
            "sign",
            "/a",  # Automatically select the best signing certificate
            "/fd", "SHA256",  # Use SHA256 digest algorithm
            "/d", description,
            "/du", "https://github.com/Trackpro-dev/TrackPro",
            "/v",
            file_path
        ]
        
        try:
            print(f"Running: {' '.join(cmd)}")
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                print("✓ File signed successfully!")
                print(result.stdout)
                return True
            else:
                print(f"✗ Signing failed with exit code {result.returncode}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
                # Method 2b: Try without timestamp (for EV cert issues)
                print("\nTrying signing without timestamp...")
                cmd_no_timestamp = [
                    self.signtool_path,
                    "sign",
                    "/a",
                    "/fd", "SHA256",
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v",
                    file_path
                ]
                
                try:
                    print(f"Running: {' '.join(cmd_no_timestamp)}")
                    result2 = subprocess.run(cmd_no_timestamp, capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
                    
                    if result2.returncode == 0:
                        print("✓ File signed successfully (without timestamp)!")
                        print(result2.stdout)
                        return True
                    else:
                        print(f"✗ Signing without timestamp also failed with exit code {result2.returncode}")
                        print("STDOUT:", result2.stdout)
                        print("STDERR:", result2.stderr)
                
                except Exception as e2:
                    print(f"✗ Error during signing without timestamp: {e2}")
                
                # Method 3: Try with specific subject name
                print("\nTrying with certificate subject name...")
                return self.sign_file_with_subject(file_path, description, timestamp_url)
                
        except Exception as e:
            print(f"✗ Error during signing: {e}")
            return False
    
    def sign_file_with_subject(self, file_path, description, timestamp_url):
        """Sign file using certificate subject name."""
        
        # First try with the known subject name
        print("Trying with known certificate subject: 'SIM COACHES LLC'")
        
        cmd = [
            self.signtool_path,
            "sign",
            "/n", "SIM COACHES LLC",  # Certificate subject name
            "/fd", "SHA256",  # Use SHA256 digest algorithm
            "/d", description,
            "/du", "https://github.com/Trackpro-dev/TrackPro",
            "/v",  # No timestamp for now
            file_path
        ]
        
        try:
            print(f"Running: {' '.join(cmd)}")
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                print("✓ File signed successfully with subject name!")
                print(result.stdout)
                return True
            else:
                print(f"✗ Signing with subject name failed with exit code {result.returncode}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
                # Try with certificate thumbprint (more reliable for EV certs)
                print("\nTrying with certificate thumbprint...")
                return self.sign_file_with_thumbprint(file_path, description)
                
        except Exception as e:
            print(f"✗ Error during signing: {e}")
            return False
    
    def sign_file_with_thumbprint(self, file_path, description):
        """Sign file using certificate thumbprint (most reliable for EV certs)."""
        
        # Get the thumbprint from the previous output
        thumbprint = "A968614D442AE56DC98A81FD5B45711F0CE470FC"  # From the build output
        
        print(f"Trying with certificate thumbprint: {thumbprint}")
        print("🔑 Make sure your Sectigo USB token is plugged in!")
        
        # Try different approaches for USB tokens
        methods = [
            # Method 1: Standard thumbprint
            {
                "name": "Standard thumbprint",
                "cmd": [
                    self.signtool_path, "sign",
                    "/sha1", thumbprint,
                    "/fd", "SHA256",
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v", file_path
                ]
            },
            # Method 2: With eToken CSP and correct container name
            {
                "name": "With eToken Base CSP and container",
                "cmd": [
                    self.signtool_path, "sign",
                    "/fd", "SHA256",
                    "/csp", "eToken Base Cryptographic Provider",
                    "/k", "Sectigo_20250324080056",  # Correct container name
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v", file_path
                ]
            },
            # Method 3: Alternative with subject name and CSP
            {
                "name": "With subject and eToken CSP",
                "cmd": [
                    self.signtool_path, "sign",
                    "/n", "SIM COACHES LLC",
                    "/fd", "SHA256",
                    "/csp", "eToken Base Cryptographic Provider",
                    "/k", "Sectigo_20250324080056",  # Correct container name
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v", file_path
                ]
            }
        ]
        
        for method in methods:
            print(f"\n🔄 Trying: {method['name']}")
            try:
                print(f"Running: {' '.join(method['cmd'])}")
                CREATE_NO_WINDOW = 0x08000000
                result = subprocess.run(method['cmd'], capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    print(f"✓ File signed successfully with {method['name']}!")
                    print(result.stdout)
                    return True
                else:
                    print(f"✗ {method['name']} failed with exit code {result.returncode}")
                    if "token" in method['name'].lower() or "smart" in method['name'].lower():
                        print("STDOUT:", result.stdout)
                        print("STDERR:", result.stderr)
                        # Check for PIN requirement
                        if "pin" in result.stderr.lower() or "password" in result.stderr.lower():
                            print("🔐 USB token may require a PIN!")
                            return self.sign_with_token_pin(file_path, description, thumbprint)
                            
            except Exception as e:
                print(f"✗ Error with {method['name']}: {e}")
                continue
        
        # If all methods failed, try PIN-based signing
        print("\n🔐 All standard methods failed. Trying PIN-based signing...")
        return self.sign_with_token_pin(file_path, description, thumbprint)
    
    def sign_with_token_pin(self, file_path, description, thumbprint):
        """Sign with USB token - PIN entry will be prompted by Windows if needed."""
        print("\n" + "="*50)
        print("🔑 USB TOKEN SIGNING")
        print("="*50)
        print("Trying USB token signing methods...")
        print("💡 Windows may prompt for your USB token PIN automatically")
        
        # USB tokens typically work better with certificate store access
        # Try multiple methods for USB token signing
        methods = [
            # Method 1: Simple thumbprint (Windows will prompt for PIN if needed)
            {
                "name": "Direct thumbprint access",
                "cmd": [
                    self.signtool_path, "sign",
                    "/sha1", thumbprint,
                    "/fd", "SHA256",
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v", file_path
                ]
            },
            # Method 2: Automatic certificate selection
            {
                "name": "Automatic certificate selection",
                "cmd": [
                    self.signtool_path, "sign",
                    "/a",  # Automatically select best certificate
                    "/fd", "SHA256",
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v", file_path
                ]
            },
            # Method 3: Subject name
            {
                "name": "Subject name selection",
                "cmd": [
                    self.signtool_path, "sign",
                    "/n", "SIM COACHES LLC",
                    "/fd", "SHA256",
                    "/d", description,
                    "/du", "https://github.com/Trackpro-dev/TrackPro",
                    "/v", file_path
                ]
            }
        ]
        
        for method in methods:
            print(f"\n🔄 Trying: {method['name']}")
            try:
                print(f"Running: {' '.join(method['cmd'])}")
                print("⏳ Please wait... Windows may prompt for USB token PIN")
                
                CREATE_NO_WINDOW = 0x08000000
                result = subprocess.run(method['cmd'], capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    print(f"✓ File signed successfully with {method['name']}!")
                    print(result.stdout)
                    return True
                else:
                    print(f"✗ {method['name']} failed with exit code {result.returncode}")
                    print("STDOUT:", result.stdout)
                    print("STDERR:", result.stderr)
                    
            except Exception as e:
                print(f"✗ Error with {method['name']}: {e}")
                continue
        
        # All methods failed
        print("\n" + "="*50)
        print("🆘 USB TOKEN TROUBLESHOOTING")
        print("="*50)
        print("All automatic methods failed. This could mean:")
        print("1. USB token drivers need to be installed")
        print("2. Token needs to be activated/unlocked")
        print("3. Different CSP (Cryptographic Service Provider) needed")
        print("4. Token software/middleware required")
        print("\n💡 Next steps:")
        print("1. Contact Sectigo support for USB token setup")
        print("2. Check if token software is installed")
        print("3. Try manual signing via Windows certificate manager")
        return False
    
    def sign_file_with_pfx(self, file_path, pfx_path, pfx_password, description="TrackPro Application"):
        """Sign file using PFX/P12 certificate file."""
        if not self.signtool_path:
            print("✗ Cannot sign file: signtool.exe not found")
            return False
        
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            return False
            
        if not os.path.exists(pfx_path):
            print(f"✗ PFX file not found: {pfx_path}")
            return False
        
        print(f"\nSigning file with PFX: {file_path}")
        
        cmd = [
            self.signtool_path,
            "sign",
            "/f", pfx_path,  # Certificate file
            "/p", pfx_password,  # Certificate password
            "/fd", "SHA256",  # Use SHA256 digest algorithm
            "/d", description,
            "/du", "https://github.com/Trackpro-dev/TrackPro",
            "/t", "http://timestamp.sectigo.com",
            "/v",
            file_path
        ]
        
        try:
            # Don't print the password in the command
            safe_cmd = cmd.copy()
            safe_cmd[safe_cmd.index("/p") + 1] = "***"
            print(f"Running: {' '.join(safe_cmd)}")
            
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                print("✓ File signed successfully with PFX!")
                print(result.stdout)
                return True
            else:
                print(f"✗ Signing failed with exit code {result.returncode}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            print(f"✗ Error during signing: {e}")
            return False
    
    def verify_signature(self, file_path):
        """Verify the digital signature of a file."""
        if not self.signtool_path:
            print("✗ Cannot verify signature: signtool.exe not found")
            return False
        
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            return False
        
        print(f"\nVerifying signature: {file_path}")
        
        cmd = [self.signtool_path, "verify", "/pa", "/v", file_path]
        
        try:
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                print("✓ Signature verified successfully!")
                print(result.stdout)
                return True
            else:
                print(f"✗ Signature verification failed with exit code {result.returncode}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
                
        except Exception as e:
            print(f"✗ Error during verification: {e}")
            return False

def main():
    """Main function for testing the code signing."""
    signer = CodeSigner()
    
    if not signer.signtool_path:
        print("\n" + "="*50)
        print("WINDOWS SDK INSTALLATION REQUIRED")
        print("="*50)
        print("To use code signing, you need to install Windows SDK:")
        print("1. Go to: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
        print("2. Download 'Windows 11 SDK' or 'Windows 10 SDK'")
        print("3. Run the installer and select 'Windows SDK Signing Tools for Desktop Apps'")
        print("4. Re-run this script after installation")
        sys.exit(1)
    
    # Check for local certificate file first
    local_cert_found = signer.cert_file_path is not None
    store_cert_found = signer.find_certificate()
    
    if local_cert_found:
        print("\n" + "="*50)
        print("LOCAL CERTIFICATE FILE FOUND")
        print("="*50)
        print(f"✓ Found certificate file: {signer.cert_file_path}")
        
        if signer.cert_file_path.lower().endswith('.cer'):
            print("\n⚠️  WARNING: .cer file detected")
            print("This appears to be a public certificate file (.cer).")
            print("For code signing, you typically need a .pfx or .p12 file with the private key.")
            print("\nOptions:")
            print("1. If you have the .pfx/.p12 file, place it in docs/cert/ folder")
            print("2. Install the certificate with private key in Windows Certificate Store")
            print("3. Contact Sectigo for the complete certificate with private key")
            
            if not store_cert_found:
                print("\nNo certificates found in Windows Certificate Store either.")
                print("Please obtain the complete certificate (.pfx/.p12) for code signing.")
                sys.exit(1)
        elif signer.cert_file_path.lower().endswith(('.pfx', '.p12')):
            print("✓ This is a complete certificate file (.pfx/.p12) that should work for signing!")
    
    # Check for certificates in Windows Certificate Store
    if not store_cert_found and not (local_cert_found and signer.cert_file_path.lower().endswith(('.pfx', '.p12'))):
        print("\n" + "="*50)
        print("CERTIFICATE SETUP REQUIRED")
        print("="*50)
        print("No valid certificates found. Please:")
        print("1. Install your Sectigo EV certificate (.p12/.pfx file)")
        print("2. Double-click the .p12/.pfx file to install it")
        print("3. Follow the Certificate Import Wizard")
        print("4. Make sure to install it in 'Personal' certificate store")
        print("5. Re-run this script after installation")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("CODE SIGNING SETUP COMPLETE")
    print("="*50)
    print("✓ signtool.exe found")
    if local_cert_found and signer.cert_file_path.lower().endswith(('.pfx', '.p12')):
        print(f"✓ Local certificate file ready: {signer.cert_file_path}")
    if store_cert_found:
        print("✓ Certificate(s) found in Windows Certificate Store")
    print("\nYou can now integrate code signing into your build process!")

if __name__ == "__main__":
    main() 