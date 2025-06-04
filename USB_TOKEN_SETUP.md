# Sectigo USB Token Setup Guide

## ✅ SOLUTION: Install SafeNet Authentication Client

Your Sectigo USB token requires **SafeNet Authentication Client (SAC)** software to work with Windows code signing.

### Step 1: Download SafeNet Authentication Client 10.9

**Direct Download:** [SafeNet Authentication Client 10.9 R1 (GA) - Windows](https://comodoca.my.salesforce.com/sfc/p/1N000002Ljih/a/Uj000002cHeb/EEEcKYWO920vajF4clnEHVzM4esXF5XRw.Lw9WyLS4Q)

### Step 2: Installation Process

1. **🔌 IMPORTANT: Unplug your USB token first**
2. **📥 Download** the SAC zip file from the link above
3. **📁 Extract** the downloaded zip file
4. **📂 Navigate** to extracted folder → `SAC` → `Msi`
5. **⚙️ Run the installer:**
   - For 64-bit Windows: `SafeNetAuthenticationClient-x64-10.9.msi`
   - For 32-bit Windows: `SafeNetAuthenticationClient-x86-10.9.msi`

### Step 3: Installation Wizard

1. Click **Next** on welcome screen
2. Select your language → **Next**
3. Accept license agreement → **Next**
4. Choose installation path → **Next**
5. Select **"Typical"** installation → **Next**
6. Click **Install**
7. Click **Finish**
8. **🔄 Restart your computer**

### Step 4: After Installation

1. **🔌 Plug in your Sectigo USB token**
2. Look for **SafeNet Authentication Client** in:
   - System tray (bottom-right corner)
   - Start menu programs
3. **Test signing** with your updated TrackPro build process

### Step 5: Verify Setup

Run this test after installation:
```bash
python test_usb_signing.py
```

You should now see successful signing! 🎉

## 🎯 Expected Results After Installation

- ✅ **No more 0x8009001e errors**
- ✅ **Successful code signing**
- ✅ **TrackPro signed automatically during build**
- ✅ **Users see "Verified publisher: SIM COACHES LLC"**

## 📞 Support

If you still have issues after installing SAC:
1. Check USB token is properly inserted
2. Restart computer again
3. Try entering PIN when prompted
4. Contact Sectigo support if needed

## 🎉 Success!

Once this is working, your `python build.py` will automatically sign both:
- `TrackPro_v{version}.exe` 
- `TrackPro_Setup_v{version}.exe`

Your software will be production-ready with no Windows security warnings! 