# TrackPro SMS-based 2FA Setup Instructions

## Overview
TrackPro now supports SMS-based Two-Factor Authentication (2FA) using Twilio for enhanced account security.

## Prerequisites
1. A Twilio account (https://www.twilio.com/try-twilio)
2. Twilio Verify Service configured
3. Valid phone number for testing

## Setup Steps

### 1. Create Twilio Account
1. Sign up at https://www.twilio.com/try-twilio
2. Verify your account and get free trial credits
3. Note your Account SID and Auth Token from the Console Dashboard

### 2. Create Verify Service
1. Go to Twilio Console > Verify > Services
2. Click "Create new Service"
3. Enter service name: "TrackPro 2FA"
4. Save and note the Service SID

### 3. Configure TrackPro

#### Option A: Environment Variables (Recommended)
Set these environment variables in your system:
```bash
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_VERIFY_SERVICE_SID=your_verify_service_sid_here
```

#### Option B: Config File
Edit `config.ini` and add your Twilio credentials:
```ini
[twilio]
account_sid = your_account_sid_here
auth_token = your_auth_token_here
verify_service_sid = your_verify_service_sid_here
```

### 4. Test the Setup
1. Start TrackPro
2. Log in to your account
3. Go to Account Settings
4. Enable 2FA and add your phone number
5. Verify the SMS code

## Features

### For Users
- **Account Security**: Add SMS-based 2FA to your account
- **Easy Setup**: Simple phone number verification process
- **Optional**: 2FA is optional but recommended
- **Profile Completion**: New users are guided through account setup

### For Developers
- **Twilio Integration**: Professional SMS service with reliable delivery
- **Error Handling**: Comprehensive error handling and user feedback
- **Configurable**: Flexible configuration via environment variables or config file
- **Modular Design**: Clean separation of concerns with TwilioService

## Database Schema

The following fields have been added to the `user_profiles` table:
- `phone_number` (TEXT) - User's phone number
- `twilio_verified` (BOOLEAN) - Whether phone number is verified
- `is_2fa_enabled` (BOOLEAN) - Whether user has 2FA enabled

## Troubleshooting

### Common Issues

1. **"SMS service is not available"**
   - Check that Twilio credentials are configured
   - Verify the `twilio` library is installed: `pip install twilio`

2. **"Failed to send verification code"**
   - Check Twilio account balance/trial credits
   - Verify phone number format (+1234567890)
   - Check Twilio service logs

3. **"Invalid verification code"**
   - Codes expire after 5 minutes
   - Each code can only be used once
   - Check for typos in the 6-digit code

### Support
- Check TrackPro logs for detailed error messages
- Visit Twilio Console > Monitor > Logs for SMS delivery status
- Ensure phone number includes country code (e.g., +1 for US)

## Security Notes
- SMS codes expire after 5 minutes
- Maximum 3 verification attempts before lockout
- Phone numbers are encrypted in database
- 2FA can be disabled by users if needed

## Testing
For development/testing:
- Use Twilio trial account (free credits)
- Test with verified phone numbers
- Check Twilio Console for delivery logs

---

**Note**: 2FA is optional but highly recommended for account security. Users can enable/disable it at any time in their account settings. 