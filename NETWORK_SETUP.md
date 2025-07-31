# Network Setup Clarification

## What Uses What

### Environment Variables Used by SERVER (FastAPI/Python)
- `DATABASE_URL` - Where to store the SQLite database
- The server ALWAYS listens on `0.0.0.0:9898` (all network interfaces)

### Environment Variables Used by CLIENT (Emacs)
- `WAVE_CLIENT_USER` - Your username in Wave (e.g., "jwalsh@nexushive")
- `WAVE_CLIENT_DOMAIN` - Domain suffix (usually empty for local)
- `WAVE_SERVER_URL` - HTTP endpoint to connect to
- `WAVE_WS_URL` - WebSocket endpoint to connect to

## Testing Scenarios

### 1. Local Testing on nexushive (RECOMMENDED TO START)
Both server and client run on the same machine.

```bash
# Use the local config
cp .env.nexushive-local .env

# Terminal 1: Start server
make server

# Terminal 2: Start Emacs client
make dashboard
# OR
emacs -nw -Q -l init.el
```

### 2. Remote Access to nexushive
Server runs on nexushive, client on another machine.

On nexushive:
```bash
# Start server (it listens on all interfaces)
make server
```

On your other machine:
```bash
# Use the remote config
cp .env.nexushive-remote .env

# Start Emacs client
emacs -nw -Q -l init.el
```

## Quick Test

To verify the server is accessible:

```bash
# On nexushive (local test)
curl http://localhost:9898/
curl http://localhost:9898/api/inbox

# From another machine (remote test)
curl http://nexushive.lan:9898/
curl http://nexushive.lan:9898/api/inbox
```

## The Server Always Binds to All Interfaces

The FastAPI server is hardcoded to bind to `0.0.0.0:9898`, which means:
- It's accessible as `localhost:9898` from the same machine
- It's accessible as `nexushive.lan:9898` from other machines on your network
- No server configuration changes needed for network access