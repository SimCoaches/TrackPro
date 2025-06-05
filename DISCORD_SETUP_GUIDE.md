# Discord Integration Setup Guide for TrackPro

## Quick Setup (Recommended)

### Step 1: Enable Discord Widget in Your Server
1. **Open Discord** and go to your racing server
2. **Right-click the server name** → **Server Settings**
3. **Go to Widget** in the left sidebar
4. **Toggle "Enable Server Widget" ON**
5. **Choose a channel** for the widget (usually #general or #racing)
6. **Save Changes**

### Step 2: Get Your Server ID
**Method A - Using Invite Link (Easiest):**
1. Create a Discord invite: **Server Settings** → **Invites** → **Create Invite**
2. Set it to **Never Expire** and **Unlimited Uses**
3. Copy the invite link (e.g., `https://discord.gg/abc123`)

**Method B - Using Server ID (Advanced):**
1. Enable Developer Mode: **User Settings** → **Advanced** → **Developer Mode ON**
2. Right-click your server name → **Copy Server ID**

### Step 3: Configure TrackPro
1. **Open TrackPro**
2. **Go to Community tab**
3. **Click "🎮 Discord"** in the navigation
4. **Setup dialog will appear** - choose one option:
   - **Paste your invite link** (Method A)
   - **Enter Server ID manually** (Method B)
5. **Choose integration mode:**
   - **Widget Mode**: View-only, lightweight (recommended)
   - **Web App Mode**: Full Discord functionality, requires login
6. **Click OK**

## Integration Modes Explained

### Widget Mode (Recommended)
- ✅ **View live chat messages**
- ✅ **See online members**
- ✅ **Fast and lightweight**
- ✅ **No login required**
- ❌ **Cannot send messages** (read-only)
- ❌ **No voice chat**

### Web App Mode (Full Features)
- ✅ **Complete Discord functionality**
- ✅ **Send messages and join voice**
- ✅ **All Discord features available**
- ❌ **Requires Discord login in TrackPro**
- ❌ **Higher resource usage**

## Troubleshooting

### "Discord integration temporarily unavailable"
**Solution**: Configuration needed. Click the Discord section to start setup.

### "Server Unavailable" in widget
**Cause**: Widget not enabled or channel not set
**Solution**: 
1. Go to Discord **Server Settings** → **Widget**
2. Enable server widget
3. Set a public channel for the widget

### "Could not validate server"
**Cause**: Incorrect server ID or widgets disabled
**Solution**:
1. Verify server ID is correct
2. Ensure widgets are enabled
3. Make sure the server is not private

### Setup dialog not appearing
**Solution**: Click the settings gear ⚙️ icon in the Discord section header

## Manual Configuration

If you prefer to edit the config file directly:

```json
{
  "server_id": "YOUR_SERVER_ID_HERE",
  "channel_id": "OPTIONAL_CHANNEL_ID",
  "widget_theme": "dark",
  "auto_connect": true,
  "show_member_count": true,
  "show_voice_channels": true,
  "use_widget_mode": true
}
```

Save this to: `trackpro/community/discord_config.json`

## Example Discord Server Setup

Here's what a properly configured racing Discord server might look like:

**Channels:**
- 📢 announcements
- 💬 general-chat
- 🏁 racing-discussion
- 🔧 setup-sharing
- 🎮 Voice Channels
  - 🏆 Race Room 1
  - 🏆 Race Room 2
  - 🛠️ Setup Discussion

**Widget Settings:**
- Enable Server Widget: ✅ ON
- Invite Channel: #general-chat
- Server ID: (copied from right-click → Copy Server ID)

## Privacy & Security

- **No TrackPro data sent to Discord** - only displays Discord content
- **Widget Mode**: Completely read-only, no permissions needed
- **Web App Mode**: Uses your existing Discord permissions
- **Local storage**: Configuration saved locally in TrackPro

## Support

If you continue having issues:
1. **Check the Discord section** - click settings ⚙️ to reconfigure
2. **Verify your server has widgets enabled**
3. **Try both Widget and Web App modes**
4. **Check that your Discord server is accessible**

The Discord integration is fully functional - it just needs the initial setup! 