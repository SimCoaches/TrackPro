# Twilio 2FA Setup Guide

Your 2FA implementation is complete! You just need to get Twilio credentials.

## Step 1: Create Twilio Account

1. Go to https://www.twilio.com/try-twilio
2. Sign up for a free account (gets $15 credit)
3. Verify your phone number during signup

## Step 2: Get Your Credentials

After signing up, go to your Twilio Console:

1. **Account SID** - Found on your main Console Dashboard
2. **Auth Token** - Found on your main Console Dashboard (click "view" to reveal)

## Step 3: Create Verify Service

1. In Twilio Console, go to "Verify" → "Services"
2. Click "Create new Verify Service"
3. Give it a name like "TrackPro 2FA"
4. Copy the **Service SID**

## Step 4: Add to TrackPro Config

Edit your `config.ini` file and fill in the credentials:

```ini
[twilio]
account_sid = ACxxxxxxxxxxxxxxxxxxxxxxxxx
auth_token = your_auth_token_here
verify_service_sid = VAxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Step 5: Test the Implementation

1. Restart TrackPro
2. Go to Account settings
3. Enter your phone number and test verification
4. Enable 2FA
5. Log out and back in to test the login flow

## Cost Information

- Twilio Verify: ~$0.05 per SMS verification
- Free trial includes $15 credit (300+ verifications)
- Production pricing is very reasonable for SMS 2FA

## That's It!

Your complete 2FA system will now work exactly like any major website:
- Users set up 2FA in Account settings
- Login requires SMS code when 2FA is enabled
- Works with both email/password and OAuth logins 