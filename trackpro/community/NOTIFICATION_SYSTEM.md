# TrackPro Community Notification System

## Overview

The Community Notification System provides visual indicators for new messages, friend requests, and other community activities throughout TrackPro. This makes it easy to see when there's new activity without constantly checking the community sections.

## Features

### 📍 Main Community Button Notifications
- **Red notification badge** appears on the main Community button in the toolbar
- **Number counter** shows total unread notifications across all community sections  
- **Animated pulsing effect** draws attention to new notifications
- **Smart tooltip** updates to show notification count

### 🎯 Section-Specific Notifications
Each community section has its own notification badge:
- **👥 Social** - Friend requests, new messages, activity updates
- **🎮 Discord** - Server messages, mentions, voice activity  
- **🏁 Community** - Team invites, event updates, club announcements
- **📁 Content** - New shared content, comments on your uploads
- **🏆 Achievements** - XP gains, level ups, badge unlocks
- **⚙️ Account** - Profile updates, setting changes

### ✨ Smart Behavior
- **Auto-clear on view** - Discord and social notifications clear when you visit those sections
- **Priority handling** - Mentions count as higher priority (worth 2 regular notifications)
- **99+ cap** - Shows "99+" for very high notification counts
- **Real-time updates** - Notifications appear instantly as they occur

## How It Works

### Notification Flow
1. **Event occurs** (Discord message, friend request, etc.)
2. **Notification manager** updates the count for that section
3. **Navigation badges** update to show new counts
4. **Main button badge** updates with total count
5. **Visual effects** draw user attention
6. **Auto-clear** when user views the section

### Integration Points

#### Discord Integration
```python
# Discord widget emits signals for new activity
discord_widget.new_message.emit("general", "Hello everyone!")
discord_widget.new_mention.emit("username", "You were mentioned")

# Notification manager automatically handles these signals
```

#### Manual Notifications
```python
# Get notification manager from community widget
notification_manager = community_widget.get_notification_manager()

# Add notifications programmatically
notification_manager.update_notification_count("social", 3)
notification_manager.update_notification_count("discord", 1)

# Clear specific section
notification_manager.clear_notifications("discord")
```

## Testing the System

### Built-in Test Panel
The Discord section includes a notification testing panel with buttons to:
- **🎮 Test Discord** - Simulates a Discord message or mention
- **👥 Test Social** - Adds a social notification 
- **🔍 Check Discord** - Manually scans Discord for real notifications
- **🗑️ Clear All** - Removes all notifications

### Standalone Test Application
You can also run a standalone tester:
```bash
cd trackpro/community
python test_discord_notifications.py
```
This opens a dedicated test window for comprehensive notification testing.

### Manual Testing
You can also test notifications programmatically:
```python
# Access the community widget
community_widget = main_window.community_widget

# Get the notification manager
notif_manager = community_widget.get_notification_manager()

# Simulate various notifications
notif_manager.update_notification_count("discord", 5)
notif_manager.update_notification_count("social", 2)
notif_manager.update_notification_count("achievements", 1)
```

## Connecting Real Events

### Discord Integration
Real Discord message detection is **automatically enabled** when you use the Discord tab! Here's how it works:

1. **Automatic Detection**: JavaScript is injected into the Discord web view to monitor for new messages
2. **DOM Monitoring**: The system watches for new message elements in Discord's interface
3. **Mention Detection**: Messages containing your username are flagged as higher-priority mentions
4. **Real-time Updates**: Notifications appear within 2-3 seconds of new messages

#### Manual Integration (Advanced)
You can also manually trigger notifications:
```python
# In your Discord monitoring code
discord_widget.new_message.emit(channel_name, message_content)
discord_widget.new_mention.emit(username, message_content)
```

### Database Integration
For other community features:
```python
# When new friend request arrives
notification_manager.update_notification_count("social", current + 1)

# When team invite sent
notification_manager.update_notification_count("community", current + 1)

# When achievement unlocked
notification_manager.update_notification_count("achievements", current + 1)
```

## Customization

### Notification Styles
Modify notification appearance in `community_main_widget.py`:
```python
# Change badge colors
badge.setStyleSheet("""
    QLabel {
        background-color: #FF4444;  # Red background
        color: white;               # White text
        border-radius: 10px;        # Rounded corners
        font-size: 10px;           # Text size
        font-weight: bold;         # Bold text
    }
""")
```

### Auto-Clear Behavior
Modify which sections auto-clear in `CommunityNavigationWidget.on_section_clicked()`:
```python
def on_section_clicked(self, section_id):
    self.section_changed.emit(section_id)
    
    # Custom auto-clear rules
    if section_id == "discord":
        QTimer.singleShot(1000, self.notification_manager.mark_discord_read)
    elif section_id == "social":
        QTimer.singleShot(1000, self.notification_manager.mark_social_read)
    # Add more sections as needed
```

### Notification Priorities
Adjust notification weights in Discord integration:
```python
def handle_new_mention(self, username, message):
    if self.notification_manager:
        current = self.notification_manager.get_notification_count("discord")
        # Mentions are worth 3x regular messages
        self.notification_manager.update_notification_count("discord", current + 3)
```

## Architecture

### Components
- **`CommunityNotificationManager`** - Central notification state management
- **`CommunityNavigationWidget`** - Navigation with notification badges
- **`CommunityMainWidget`** - Main container with notification signals
- **`DiscordIntegrationWidget`** - Discord-specific notification handling
- **`MainWindow`** - Main app integration and badge animation

### Signals & Slots
```python
# Notification manager signals
notification_updated = pyqtSignal(str, int)      # section_id, count
total_notifications_updated = pyqtSignal(int)    # total count

# Community widget signals
notification_count_changed = pyqtSignal(int)     # total count

# Discord widget signals  
new_message = pyqtSignal(str, str)               # channel, message
new_mention = pyqtSignal(str, str)               # username, message
```

### Data Flow
```
Discord/Community Event
         ↓
  Notification Manager
         ↓
   Section Badge Update
         ↓
   Total Count Update
         ↓
  Main Button Badge Update
         ↓
    Visual Animation
```

## Best Practices

### 🎯 Do's
- **Use appropriate priorities** - Mentions > messages > general activity
- **Clear notifications** when users view content
- **Provide visual feedback** for notification state changes
- **Cap large numbers** at 99+ to avoid UI overflow
- **Test thoroughly** with the built-in test panel

### ❌ Don'ts
- **Don't spam notifications** - Batch similar events when possible
- **Don't interrupt workflows** - Keep notifications subtle and non-blocking
- **Don't persist indefinitely** - Clear old notifications appropriately
- **Don't ignore performance** - Limit notification check frequency

## Troubleshooting

### Common Issues

#### Notifications Not Appearing
1. Check notification manager is properly connected
2. Verify signals are being emitted correctly
3. Test with the built-in test panel

#### Real Discord Messages Not Detected
1. **Switch to Web App Mode**: In Discord settings, switch from Widget Mode to Web App Mode
2. **Wait for initialization**: Give Discord 5-10 seconds to fully load before expecting detection
3. **Use manual check**: Click the "🔍 Check Discord" button to force a scan for notifications
4. **Check browser console**: Open Discord web view and look for these messages:
   - `TrackPro: Discord message monitoring active`
   - `TrackPro: Monitoring initialization complete`
5. **Debug with JavaScript**: In the Discord web view console, type:
   - `window.trackproStatus()` - Shows monitoring status
   - `window.trackproManualCheck()` - Forces a notification check
6. **Test with a simple message**: Send a test message in the Discord channel to verify detection

#### Badges Not Clearing
1. Ensure auto-clear timers are properly set
2. Check if `clear_notifications()` is being called
3. Verify section IDs match exactly

#### Animation Issues
1. Check if graphics effects are supported
2. Verify animation objects aren't being garbage collected
3. Test on different platforms

### Debug Tools
```python
# Enable notification debugging
notification_manager.notification_updated.connect(
    lambda section, count: print(f"Notification: {section} = {count}")
)

# Check current state
for section in ["social", "discord", "community", "content", "achievements"]:
    count = notification_manager.get_notification_count(section)
    print(f"{section}: {count}")
```

## Future Enhancements

### Planned Features
- **Sound notifications** for high-priority events
- **Desktop notifications** when TrackPro is minimized
- **Notification history** with detailed event logs
- **Custom notification rules** per user
- **Integration with system notifications**

### Extension Points
- **Plugin system** for custom notification sources
- **Webhook support** for external integrations
- **Mobile app notifications** via push service
- **Email digest** for offline notifications

## Contributing

When adding new notification sources:

1. **Emit appropriate signals** when events occur
2. **Connect to notification manager** in the parent widget
3. **Add auto-clear logic** if appropriate
4. **Test with various notification counts**
5. **Document the new notification type**

For questions or contributions, see the main TrackPro documentation. 