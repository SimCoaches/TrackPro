# Code Signing Setup Guide for TrackPro

This guide will help you set up code signing for TrackPro using your Sectigo EV certificate.

## Prerequisites

### 1. Install Windows SDK

You need `signtool.exe` which comes with the Windows SDK:

**Option A: Download from Microsoft**
1. Go to: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/
2. Download "Windows 11 SDK" or "Windows 10 SDK"
3. Run the installer
4. Select "Windows SDK Signing Tools for Desktop Apps"
5. Complete the installation

**Option B: Install via Visual Studio**
1. Open Visual Studio Installer
2. Modify your Visual Studio installation
3. Go to "Individual Components"
4. Search for "Windows 10 SDK" or "Windows 11 SDK"
5. Check the box and install

### 2. Install Your Sectigo EV Certificate

Your EV certificate from Sectigo can be installed in several ways:

#### Method A: Install from .p12/.pfx file
1. Locate your certificate file (usually named something like `certificate.p12` or `certificate.pfx`)
2. Double-click the file
3. Follow the Certificate Import Wizard:
   - Store Location: Choose "Local Machine" for all users or "Current User" for just you
   - Enter the password when prompted
   - Certificate Store: Select "Personal" 
4. Complete the wizard

#### Method B: Install from certificate manager
1. Press `Win + R`, type `certlm.msc` and press Enter
2. Navigate to "Personal" → "Certificates"
3. Right-click in the certificates area
4. Select "All Tasks" → "Import..."
5. Follow the import wizard

## Verification

### Test the Setup

Run the signing setup test:

```bash
python sign_code.py
```

This will:
- ✅ Check if `signtool.exe` is installed
- ✅ Look for your EV certificate
- ✅ Verify everything is ready for signing

### Manual Certificate Check

You can also manually verify your certificate:

1. Open Certificate Manager (`certlm.msc`)
2. Go to "Personal" → "Certificates"
3. Look for your Sectigo certificate
4. Double-click it to view details
5. Make sure:
   - It has a private key (key icon should be visible)
   - It's not expired
   - It shows "Extended Validation" in the certificate details

## Using Code Signing

### Automatic Signing (Recommended)

Code signing is now integrated into your build process:

```bash
python build.py
```

This will:
1. Build the TrackPro executable
2. **Sign the executable** ✍️
3. Create the installer
4. **Sign the installer** ✍️

### Manual Signing

You can also sign files manually:

```python
from sign_code import CodeSigner

signer = CodeSigner()

# Sign a single file
signer.sign_file("path/to/your/file.exe")

# Sign with PFX file (if not installed in certificate store)
signer.sign_file_with_pfx(
    "path/to/your/file.exe", 
    "path/to/certificate.pfx", 
    "your_certificate_password"
)

# Verify a signature
signer.verify_signature("path/to/your/file.exe")
```

### Disable Signing

If you need to disable signing temporarily:

```python
# In build.py, change this line:
self.enable_signing = False  # Set to False to disable signing
```

## Troubleshooting

### Common Issues

#### "signtool.exe not found"
- Install Windows SDK (see Prerequisites above)
- Make sure the SDK is in your PATH

#### "No certificates found"
- Install your EV certificate (see Prerequisites above)
- Make sure it's in the "Personal" certificate store
- Verify it has a private key

#### "Access denied" or "Permission error"
- Run the build script as Administrator
- EV certificates may require elevated privileges

#### "Certificate not valid for signing"
- Check certificate expiration date
- Verify it's an EV (Extended Validation) certificate
- Make sure the certificate chain is complete

### Certificate Subject Name

If automatic certificate selection fails, you may need to specify the certificate subject name:

1. Open Certificate Manager (`certlm.msc`)
2. Find your certificate in "Personal" → "Certificates"
3. Double-click it
4. Copy the "Issued to" field
5. Use this name when prompted by the signing script

### Timestamp Servers

The build uses Sectigo's timestamp server by default:
- `http://timestamp.sectigo.com`

If this fails, you can try alternatives:
- `http://timestamp.digicert.com`
- `http://timestamp.globalsign.com`

## Security Best Practices

1. **Keep Certificate Secure**: Store your .pfx file in a secure location
2. **Strong Password**: Use a strong password for your certificate
3. **Regular Updates**: Keep Windows SDK updated
4. **Verify Signatures**: Always verify signatures after signing
5. **Backup Certificate**: Keep secure backups of your certificate

## Files That Get Signed

The build process signs:
1. `TrackPro_v{version}.exe` - The main application executable
2. `TrackPro_Setup_v{version}.exe` - The installer

Both files will show as "verified" when users download and run them, eliminating Windows security warnings.

## Support

If you encounter issues:
1. Check this guide first
2. Run `python sign_code.py` to diagnose issues
3. Verify your certificate is properly installed
4. Ensure Windows SDK is installed correctly

## Certificate Information

For reference, here's information about EV certificates:

- **EV (Extended Validation)** certificates provide the highest level of trust
- They show your organization name in green in browsers
- They eliminate Windows SmartScreen warnings
- They're required for certain distribution channels
- **Sectigo** is a trusted Certificate Authority recognized by all major platforms

Your signed software will show:
- ✅ "Verified publisher" in Windows
- ✅ No security warnings when downloaded
- ✅ Trusted by Windows Defender and other antivirus software 