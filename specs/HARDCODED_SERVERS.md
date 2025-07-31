# Hardcoded Server Configuration in Emacs Lisp Client

The Wave Emacs client has several hardcoded server URLs that need to be considered:

## WebSocket Configuration
- **File**: `lisp/wave-client-websocket.el`
- **Line 42**: `(defvar wave-client-ws-url "ws://127.0.0.1:9898"`
- **Note**: This is already pointing to localhost:9898, which matches our server's WebSocket port

## Browser Channel Configuration  
- **File**: `lisp/wave-client-browser-channel.el`
- **Line 40**: `(defcustom wave-client-server "https://wave.google.com"`
- **Note**: This would need to be changed to `http://localhost:9898` for local testing

## Domain Configuration
- **File**: `lisp/wave-client.el`
- **Line 71**: Default domain is `"googlewave.com"`
- **Note**: Can be overridden by setting `wave-client-domain` to `nil` or `"localhost"`

## Recommended Changes for Local Testing

To use the Emacs client with our local server without modifying the source:

1. Set these variables in your Emacs configuration:
```elisp
(setq wave-client-ws-url "ws://localhost:9898/ws")
(setq wave-client-server "http://localhost:9898")
(setq wave-client-domain nil)
(setq wave-client-connection-method 'websocket)
```

2. Or start Emacs with:
```bash
emacs --eval '(setq wave-client-ws-url "ws://localhost:9898/ws")' \
      --eval '(setq wave-client-server "http://localhost:9898")' \
      --eval '(setq wave-client-domain nil)'
```