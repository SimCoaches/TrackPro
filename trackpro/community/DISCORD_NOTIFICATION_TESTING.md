# Testing Discord Notifications - Quick Guide

## The Issue
Discord notifications (like "NEW" badges) were visible in Discord but not triggering TrackPro notification badges.

## The Fix
Added comprehensive JavaScript monitoring that detects:
- ✅ "NEW" badges on channels
- ✅ Number badges (like "3" unread messages)
- ✅ Unread indicators
- ✅ Actual new messages in chat
- ✅ Mentions of your username

## How to Test

### Step 1: Restart TrackPro
Close and restart TrackPro to get the latest Discord monitoring code.

### Step 2: Open Discord in Web App Mode
1. Go to **Community → Discord**
2. Click the **gear icon (⚙️)** in the Discord header
3. Make sure you're using **Web App Mode** (not Widget Mode)
4. If in Widget Mode, click "🌐 Switch to Web App Mode"

### Step 3: Wait for Initialization
Wait **5-10 seconds** after Discord loads. You should see a temporary debug message appear in the top-right of Discord saying "TrackPro Discord Monitoring: ACTIVE".

### Step 4: Test with Manual Check
1. Click the **"🔍 Check Discord"** button in the notification testing panel
2. This will scan Discord for any existing notifications
3. If there are "NEW" badges or unread indicators, they should trigger TrackPro notifications

### Step 5: Test with Real Activity
1. Have someone send a message in your Discord server
2. Or send a message yourself from another device/browser
3. Within 2-3 seconds, you should see notifications appear on:
   - The Discord tab (red badge)
   - The main Community button (red badge with number)

## Debugging

### Check Console Messages
Open Discord's browser console (F12) and look for:
```
TrackPro: Discord message monitoring active
TrackPro: Monitoring initialization complete
```

### Manual Debug Commands
In the Discord console, type:
- `window.trackproStatus()` - Shows current monitoring status
- `window.trackproManualCheck()` - Forces a notification check

### Expected Console Output
When notifications are detected, you should see:
```
TrackPro: NEW badge detected
TrackPro: Channel notification badge detected: 3
📨 Discord message detected: Username: Message content
```

## If It Still Doesn't Work

1. **Refresh Discord**: Click the refresh button or reload the Discord tab
2. **Check Mode**: Ensure you're in Web App Mode (not Widget Mode)
3. **Wait Longer**: Give Discord more time to fully load (up to 30 seconds)
4. **Try Different Channels**: Switch to different Discord channels to see if monitoring works there
5. **Restart TrackPro**: Close and reopen TrackPro completely

## What Should Happen

✅ **"NEW" badges** in Discord should trigger TrackPro notifications  
✅ **Number badges** (like "3 unread") should trigger notifications  
✅ **New messages** should trigger notifications within 2-3 seconds  
✅ **Mentions** of your username should trigger higher-priority notifications  
✅ **Notification badges** should appear on both Discord tab and Community button  
✅ **Auto-clear** should happen when you view the Discord tab  

## Success Indicators

- Red notification badge appears on Discord tab in TrackPro navigation
- Red notification badge appears on main Community button
- Badge shows correct number of notifications
- Badge pulses/animates to draw attention
- Notifications clear when you view Discord tab
- Console shows detection messages

If you see these indicators, the Discord notification system is working correctly! 🎉 