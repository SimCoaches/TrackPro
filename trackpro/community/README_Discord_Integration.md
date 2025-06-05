# Discord Integration for TrackPro

## Overview

The Discord integration allows TrackPro users to access their Discord server directly within the application, enabling seamless communication between racers without needing to switch applications.

## Features

### Current Implementation
- **Discord Widget Embedding**: Embed Discord server chat via Discord's widget API
- **Full Discord Web App**: Option to embed the complete Discord web application
- **Server Configuration**: Easy setup with Discord invite links or manual server ID
- **Visual Integration**: Discord interface matches TrackPro's theme and styling
- **Multiple View Modes**: Separate tabs for server chat, voice channels, and member lists

### Supported Modes

#### 1. Widget Mode (Recommended for Most Users)
- ✅ View server messages in real-time
- ✅ See online members and their status
- ✅ Lightweight and fast loading
- ❌ Cannot send messages (read-only)
- ❌ No voice chat functionality
- ❌ Limited to widget-enabled servers

#### 2. Web App Mode (Full Functionality)
- ✅ Complete Discord functionality including sending messages
- ✅ Voice and video chat support
- ✅ All Discord features available
- ✅ Works with any Discord server
- ❌ Requires Discord login within TrackPro
- ❌ Higher resource usage

## Setup Instructions

### Prerequisites
1. **Discord Server**: You need a Discord server for your racing community
2. **Server Admin Access**: Required to enable widgets (for Widget Mode)
3. **TrackPro v5.30+**: Discord integration is available in TrackPro 5.30 and later

### Quick Setup (Recommended)

1. **Open TrackPro** and navigate to Community → Discord
2. **Get Discord Invite Link**:
   - Go to your Discord server
   - Create a permanent invite link: Server Settings → Invites → Create Invite
   - Set it to never expire and unlimited uses
3. **Paste Invite Link** in TrackPro's Discord setup dialog
4. **Validate Server** - TrackPro will extract server information automatically
5. **Choose Mode**:
   - Widget Mode: Limited but lightweight
   - Web App Mode: Full functionality, requires login

### Manual Setup (Advanced Users)

1. **Enable Developer Mode** in Discord:
   - User Settings → Advanced → Developer Mode (ON)
2. **Get Server ID**:
   - Right-click your server name
   - Click "Copy Server ID"
3. **Enable Widget** (for Widget Mode):
   - Server Settings → Widget
   - Toggle "Enable Server Widget" ON
   - Choose a public channel for the widget
4. **Configure in TrackPro**:
   - Use Manual Setup tab
   - Enter your Server ID
   - Optionally specify a default channel ID

## Server Requirements

### For Widget Mode
- Server widgets must be enabled
- At least one public channel must be set as the widget channel
- Server must be discoverable or have a public invite

### For Web App Mode
- No special server configuration required
- Works with any Discord server you have access to
- Users need Discord accounts and server membership

## Integration Details

### Files Added
- `trackpro/community/discord_integration.py` - Main Discord widget
- `trackpro/community/discord_setup_dialog.py` - Configuration dialog
- `trackpro/community/discord_config.json` - Saved configuration (auto-generated)

### Dependencies
The Discord integration uses existing TrackPro dependencies:
- `PyQt5` - UI framework
- `PyQtWebEngine` - Web content embedding
- `requests` - Discord API validation

No additional packages required!

## Usage

### Accessing Discord
1. Open TrackPro
2. Go to Community tab
3. Click "🎮 Discord" in the navigation
4. If not configured, the setup dialog will appear

### Features Available

#### Server Chat Tab
- View real-time messages from your Discord server
- See message history
- Click "Open in Browser" to reply in Discord

#### Voice Channels Tab
- View active voice channels
- See who's in each channel
- Join voice chat (Web App Mode only)

#### Members Tab
- View online server members
- See member status and activities
- Member list updates in real-time

### Keyboard Shortcuts
- `Ctrl+Shift+D` - Quick switch to Discord tab
- `Ctrl+B` - Open Discord in external browser

## Troubleshooting

### Common Issues

#### "Discord integration temporarily unavailable"
- **Cause**: Setup not completed or configuration error
- **Solution**: Click settings gear icon and reconfigure server

#### "Could not validate server"
- **Cause**: Server widgets disabled or incorrect server ID
- **Solution**: Enable widgets in Discord Server Settings → Widget

#### "Invalid Discord invite link format"
- **Cause**: Wrong invite link format
- **Solution**: Use format like `https://discord.gg/yourcode`

#### Widget shows "Server Unavailable"
- **Cause**: Widget channel not set or server privacy settings
- **Solution**: Set a widget channel in Server Settings → Widget

#### Login required repeatedly (Web App Mode)
- **Cause**: Discord cookies cleared or session expired
- **Solution**: This is normal; login will be remembered after first time

### Advanced Troubleshooting

#### Check Configuration File
Configuration is stored in: `trackpro/community/discord_config.json`

Example configuration:
```json
{
  "server_id": "123456789012345678",
  "channel_id": "123456789012345678",
  "widget_theme": "dark",
  "auto_connect": true,
  "show_member_count": true,
  "show_voice_channels": true
}
```

#### Reset Discord Integration
1. Delete `discord_config.json` file
2. Restart TrackPro
3. Reconfigure Discord integration

## Privacy & Security

### Data Handling
- **No TrackPro data sent to Discord**: Integration only displays Discord content
- **Standard web requests**: Only normal Discord API calls are made
- **Local configuration**: Server settings stored locally in TrackPro

### Discord Permissions
- **Widget Mode**: No Discord permissions required (read-only)
- **Web App Mode**: Uses your existing Discord account and permissions

## Future Enhancements

Planned features for future releases:
- **Rich Presence**: Show TrackPro racing status in Discord
- **Bot Integration**: TrackPro bot for Discord servers
- **Race Notifications**: Discord notifications for TrackPro events
- **Voice Chat Integration**: Direct voice integration without full Discord
- **Multiple Server Support**: Connect to multiple Discord servers

## Support

### Getting Help
1. **TrackPro Community**: Ask in TrackPro's community forums
2. **Discord Support**: For Discord-specific issues, check Discord's help center
3. **GitHub Issues**: Report bugs in the TrackPro repository

### Known Limitations
- Widget Mode is read-only
- Voice chat requires Web App Mode
- Some Discord features may not work in embedded mode
- Mobile Discord features not supported

## API References

### Discord Widget API
- **Documentation**: https://discord.com/developers/docs/resources/guild#get-guild-widget
- **Widget URL Format**: `https://discord.com/widget?id=SERVER_ID&theme=THEME`

### Discord Web App
- **URL**: https://discord.com/app
- **Requirements**: Discord account and JavaScript enabled 