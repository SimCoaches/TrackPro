# TrackPro Network Voice Server

This allows multiple users on the same WiFi network to connect and chat together in voice channels.

## Quick Start

### Option 1: Use the Launcher (Recommended)
```bash
python start_network_voice_server.py
```

### Option 2: Run the Server Directly
```bash
python trackpro/network_voice_server.py
```

## How It Works

1. **Start the server** on one computer (the "host")
2. **Note the IP address** shown when the server starts
3. **Other users** on the same WiFi network can connect using that IP address
4. **All users** connect through TrackPro's community page

## Server Features

- **Network Accessible**: Binds to all network interfaces (0.0.0.0)
- **Multiple Channels**: Support for different voice channels
- **Speaking Detection**: Shows who is currently speaking
- **High Quality Audio**: 48kHz, 24-bit audio processing
- **Automatic Cleanup**: Removes inactive connections
- **Real-time Stats**: Shows active connections and usage

## Connection Details

- **Protocol**: WebSocket (ws://)
- **Port**: 8080
- **Local Access**: `ws://localhost:8080`
- **Network Access**: `ws://YOUR_IP:8080`

## For Other Users

1. **Must be on the same WiFi network** as the server host
2. **Use the IP address** shown when the server starts
3. **Connect through TrackPro** - the app will automatically use the network server
4. **No additional setup** required on their end

## Example

```
🎤 TrackPro Network Voice Server
==========================================
This server allows multiple users on the same WiFi network
to connect and chat together in voice channels.

🎤 Network voice server started!
🎤 Local access: ws://localhost:8080
🎤 Network access: ws://192.168.1.100:8080
🎤 Other users on same WiFi can connect using: 192.168.1.100
🎤 Press Ctrl+C to stop the server
```

In this example, other users would connect to `192.168.1.100:8080`.

## Troubleshooting

### Server Won't Start
- Check if port 8080 is already in use
- Try a different port by editing the server script
- Make sure you have the required Python packages

### Users Can't Connect
- Verify they're on the same WiFi network
- Check Windows Firewall settings
- Try using the local IP address instead of localhost

### Audio Issues
- Check microphone permissions
- Verify audio input/output devices
- Try adjusting the speaking threshold in the server code

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Technical Details

- **WebSocket Server**: Built with `websockets` library
- **Audio Processing**: Uses `numpy` for audio level detection
- **Network Binding**: Binds to `0.0.0.0` for all interfaces
- **Connection Management**: Automatic cleanup of inactive clients
- **Channel Support**: Multiple voice channels with user tracking

## Security Note

This server is designed for local WiFi networks only. It's not suitable for internet-wide deployment without additional security measures. 