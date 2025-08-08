## TrackPro Voice Chat (WebRTC + LiveKit) — TODO Checklist

Use this to enable Discord‑like, global voice chat with Opus and built‑in echo/noise controls. Minimal infra, works worldwide.

### Prerequisites
- LiveKit Cloud account (or self‑hosted LiveKit)
- Supabase project access (TrackPro‑Auth)

### 1) Create LiveKit project
- Create a LiveKit Cloud project
- Note these values:
  - LIVEKIT_HOST (example: wss://<your-livekit-host>)
  - LIVEKIT_API_KEY
  - LIVEKIT_API_SECRET

### 2) Configure Supabase Edge Function (token minting)
- Function deployed: livekit_token
  - Endpoint: https://xbfotxwpntqplvvsffrr.functions.supabase.co/livekit_token
- In Supabase → Project Settings → Functions → Secrets, set:
  - LIVEKIT_API_KEY: <your key>
  - LIVEKIT_API_SECRET: <your secret>
  - LIVEKIT_HOST: <your host URL>
- Ensure “Verify JWT” is enabled for the function (default: enabled)

### 3) Configure the TrackPro app
Set environment variables (or mirror these in config):

```
TRACKPRO_VOICE_WEBRTC=true
TRACKPRO_LIVEKIT_HOST_URL=wss://<your-livekit-host>
TRACKPRO_LIVEKIT_TOKEN_URL=https://xbfotxwpntqplvvsffrr.functions.supabase.co/livekit_token
```

Notes:
- When WebRTC is enabled, the app uses an embedded WebRTC client (LiveKit) instead of the local WebSocket server.
- The token function uses the current user’s Supabase JWT (if available) to set identity.

### 4) Test
1. Launch TrackPro
2. Open Community → Join a voice channel
3. You should see a small “Connecting voice…” window and a mic prompt; accept it
4. Join the same channel from another machine to verify global audio

### 5) Optional enhancements (later)
- Hook mute/deafen buttons to LiveKit track mute
- Speaking indicators via LiveKit participant events
- Room permissions (moderators)
- Analytics/quality stats

### 6) Dev fallback (local WebSocket voice)
- If you set `TRACKPRO_VOICE_WEBRTC=false` (or leave it unset), the app falls back to the existing WebSocket voice server.
- Local dev URL is read from config/env (default: ws://localhost:8080).


