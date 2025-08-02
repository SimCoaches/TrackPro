# EmailJS Setup Guide - Fixing the 403 Errors

## The Problem

You're getting EmailJS 403 errors with the message: **"API calls in strict mode, but no private key was passed"**

This happens because your EmailJS service is configured in **strict mode**, which requires both a public key AND a private key for security.

## Root Cause Analysis

From the logs:
```
Status Code: 403
Content: API calls in strict mode, but no private key was passed
```

The current implementation only uses:
- ✅ Public Key: `F--CQZB5CgvQm0GNs`
- ❌ Private Key: **MISSING**

## Solutions

### Option 1: Add Private Key (Recommended)

1. **Get your private key from EmailJS dashboard:**
   - Go to https://dashboard.emailjs.com/
   - Navigate to your service settings
   - Find your **Private Key** (different from public key)

2. **Update the config file:**
   ```json
   {
     "service_id": "service_qnihili",
     "template_id": "template_mohsuap", 
     "public_key": "F--CQZB5CgvQm0GNs",
     "private_key": "YOUR_ACTUAL_PRIVATE_KEY_HERE"
   }
   ```

3. **The code will automatically:**
   - Detect the private key
   - Switch to strict mode (JSON API)
   - Use proper authentication

### Option 2: Disable Strict Mode

If you have access to EmailJS dashboard:
1. Go to your service settings
2. Look for "Strict Mode" or "Security Settings"
3. Disable strict mode
4. Keep using only the public key

### Option 3: Environment Variables

Instead of the config file, you can use environment variables:
```bash
EMAILJS_SERVICE_ID=service_qnihili
EMAILJS_TEMPLATE_ID=template_mohsuap
EMAILJS_PUBLIC_KEY=F--CQZB5CgvQm0GNs
EMAILJS_PRIVATE_KEY=your_private_key_here
```

## What I Fixed

✅ **Updated EmailJS Client:**
- Added private key support
- Automatic strict mode detection
- Proper API endpoint selection
- Better error logging

✅ **Smart Mode Selection:**
- **With private key:** Uses `/send` endpoint with JSON + strict mode
- **Without private key:** Uses `/send-form` endpoint with form data

✅ **Enhanced Configuration:**
- Config file now supports private key
- Environment variable fallback
- Better debugging information

## Testing the Fix

1. **Add your private key to config file**
2. **Test with a support ticket**
3. **Check logs for:**
   ```
   📨 [EMAILJS DEBUG] Using strict mode with private key
   📨 [EMAILJS DEBUG] Sending POST request to EmailJS API (strict mode)...
   Status Code: 200
   ```

## Next Steps

**Immediate:** Get your EmailJS private key and update the config file.

**Alternative:** If you can't get the private key, disable strict mode in EmailJS dashboard.

The EmailJS errors will stop once you have proper authentication configured!