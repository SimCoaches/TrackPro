# TrackPro Community System

A Discord-inspired community system with voice chat functionality for TrackPro.

## Features

### 🎨 Discord-Inspired Design
- **Clean, professional interface** with dark theme
- **Role-based color coding** for usernames
- **Channel categories** (General, Racing, Tech Support, Events, Voice)
- **Real-time messaging** with persistent storage

### 🎤 Voice Chat System
- **Real-time voice communication** using PyAudio and WebSocket
- **Multiple voice channels** (General, Racing)
- **Voice controls** (Mute, Deafen, Volume)
- **Participant management** with visual indicators

### 👥 Role-Based Hierarchy
- **Admin** (Red) - Full control and moderation
- **Moderator** (Orange) - Content moderation
- **Racing Pro** (Blue) - Verified racing achievements
- **Racer** (Green) - Active community member
- **Newbie** (Gray) - New member

### 🛡️ Moderation Tools
- **User banning** and temporary suspensions
- **Message deletion** and editing
- **Content filtering** and spam protection
- **User role management**

## Database Structure

### Chat System Tables
- `chat_channels` - Channel information and settings
- `chat_messages` - Message storage with metadata
- `user_roles` - Role assignments and permissions

### Voice Chat Tables
- `voice_sessions` - Active voice chat sessions
- `voice_participants` - Participant management

### Moderation Tables
- `user_bans` - User ban records
- `message_reports` - Content moderation reports

## Installation

### 1. Install Dependencies
```bash
pip install -r voice_chat_requirements.txt
```

### 2. Database Setup
The database tables are automatically created when you run the application. The system uses Supabase for data persistence.

### 3. Voice Chat Server
Start the voice chat WebSocket server:
```bash
python trackpro/voice_chat_server.py
```

## Usage

### Starting the Community Page
```python
from trackpro.ui.pages.community.community_page import CommunityPage

# Create the community page
community_page = CommunityPage()
```

### Testing the Interface
Run the test script to see the community interface:
```bash
python test_community_page.py
```

## Voice Chat Implementation

### Client-Side (PyQt6)
- Uses `PyAudio` for audio capture and playback
- `websockets` for real-time communication
- Threading for non-blocking audio processing

### Server-Side (WebSocket)
- Handles multiple voice channels
- Broadcasts audio data to channel participants
- Manages user connections and disconnections

### Audio Settings
- **Sample Rate**: 44.1 kHz
- **Channels**: Mono (1 channel)
- **Format**: 16-bit PCM
- **Chunk Size**: 1024 samples

## File Structure

```
trackpro/
├── ui/pages/community/
│   ├── __init__.py
│   └── community_page.py      # Main community interface
├── voice_chat_server.py       # WebSocket voice server
└── database/migrations/       # Database schema

test_community_page.py         # Test script
voice_chat_requirements.txt    # Dependencies
```

## Key Components

### CommunityPage
Main interface with Discord-inspired layout:
- **Left Sidebar**: Channel list
- **Center**: Chat/voice area
- **Right Sidebar**: Members panel with role colors

### VoiceChatManager
Handles voice chat functionality:
- Audio recording and playback
- WebSocket communication
- Thread management

### ChatMessageWidget
Individual message display with:
- User avatars with initials
- Role-based username colors
- Timestamp formatting

### VoiceChannelWidget
Voice channel interface with:
- Participant list
- Mute/Deafen controls
- Volume slider

## Role Colors

| Role | Color | Description |
|------|-------|-------------|
| Admin | #ff4444 (Red) | Full control and moderation |
| Moderator | #ff8800 (Orange) | Content moderation |
| Racing Pro | #4488ff (Blue) | Verified racing achievements |
| Racer | #44ff44 (Green) | Active community member |
| Newbie | #888888 (Gray) | New member |

## Voice Chat Channels

### Default Channels
- **# general** - General community discussion
- **# racing** - Racing discussion and tips
- **# tech-support** - Technical support and help
- **# events** - Community events and announcements
- **🔊 Voice General** - General voice chat
- **🔊 Voice Racing** - Racing voice chat

## Moderation Features

### User Management
- Role assignment and removal
- Temporary and permanent bans
- User activity monitoring

### Content Moderation
- Message reporting system
- Automated spam detection
- Content filtering

### Voice Chat Moderation
- Mute individual users
- Deafen users (prevent hearing)
- Channel management

## Security Considerations

### Voice Chat
- Audio data is transmitted in real-time
- No persistent storage of voice data
- WebSocket connections use standard security

### Chat Messages
- Messages stored in Supabase database
- Row Level Security (RLS) enabled
- User permissions enforced

## Performance Optimization

### Voice Chat
- Audio compression for bandwidth efficiency
- Chunked transmission for low latency
- Background processing to prevent UI blocking

### Chat Interface
- Virtual scrolling for large message lists
- Lazy loading of message history
- Efficient avatar generation

## Future Enhancements

### Planned Features
- **File sharing** in chat channels
- **Message reactions** and threading
- **Advanced voice effects** (noise suppression, echo cancellation)
- **Screen sharing** during voice calls
- **Mobile app** integration

### Technical Improvements
- **End-to-end encryption** for voice chat
- **Better audio codecs** (Opus, WebRTC)
- **Scalable WebSocket clustering**
- **Advanced moderation AI**

## Troubleshooting

### Voice Chat Issues
1. **No audio input**: Check microphone permissions
2. **No audio output**: Check speaker/headphone connection
3. **Connection errors**: Ensure voice server is running
4. **High latency**: Check network connection

### Chat Issues
1. **Messages not loading**: Check database connection
2. **Role colors not showing**: Verify user role assignments
3. **Permission errors**: Check user authentication

## Development

### Adding New Channels
```python
# Add to channel list in CommunityPage.create_server_list()
channels = [
    ("# new-channel", "new-channel", "text"),
    ("🔊 Voice New", "voice-new", "voice")
]
```

### Adding New Roles
```python
# Add to ROLE_COLORS in community_page.py
ROLE_COLORS = {
    'new_role': '#color_code',
    # ... existing roles
}
```

### Customizing Voice Settings
```python
# Modify in VoiceChatManager.__init__()
self.RATE = 48000  # Higher sample rate
self.CHANNELS = 2  # Stereo audio
```

## Support

For issues or questions about the community system:
1. Check the troubleshooting section
2. Review the database schema
3. Test with the provided test script
4. Check voice server logs for WebSocket issues

---

**Note**: This system is designed to be scalable and can be extended with additional features as needed. The voice chat functionality requires a running WebSocket server for full functionality. 