#!/usr/bin/env bash
# Capture screenshots of Wave client in Emacs
# Requires: Xvfb, scrot, Emacs with X11 support

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SCREENSHOT_DIR="$PROJECT_DIR/docs/screenshots"
EMACS="${EMACS:-emacs}"

mkdir -p "$SCREENSHOT_DIR"

echo "=== Wave Client Screenshot Capture ==="
echo "Project: $PROJECT_DIR"
echo "Screenshots: $SCREENSHOT_DIR"
echo ""

# Check if server is running
if ! curl -s http://localhost:9898/health > /dev/null 2>&1; then
    echo "ERROR: Wave server not running on localhost:9898"
    echo "Start with: gmake server"
    exit 1
fi

echo "✓ Server is running"

# Function to capture screenshot
capture_screenshot() {
    local name="$1"
    local delay="${2:-1}"
    sleep "$delay"
    scrot -u "$SCREENSHOT_DIR/${name}.png" 2>/dev/null || \
    scrot "$SCREENSHOT_DIR/${name}.png" 2>/dev/null || \
    echo "Warning: Could not capture $name"
    echo "  Captured: $name.png"
}

# Check if we have a display
if [ -z "$DISPLAY" ]; then
    echo "No DISPLAY set, using Xvfb..."
    Xvfb :99 -screen 0 1280x800x24 &
    XVFB_PID=$!
    export DISPLAY=:99
    sleep 2
    CLEANUP_XVFB=1
fi

echo "Using DISPLAY=$DISPLAY"
echo ""

# Launch Emacs with Wave demo
echo "Launching Emacs with Wave inbox..."
$EMACS -Q \
    --eval "(setq inhibit-startup-screen t)" \
    --eval "(setq initial-scratch-message nil)" \
    --eval "(load-file \"$SCRIPT_DIR/wave-screenshot.el\")" \
    --eval "(wave-demo-buffer)" \
    --eval "(set-frame-size (selected-frame) 100 35)" \
    --eval "(redisplay t)" &
EMACS_PID=$!

# Wait for Emacs to start and capture inbox
sleep 3
capture_screenshot "wave-inbox" 1

# Show wave detail
$EMACS -Q \
    --eval "(setq inhibit-startup-screen t)" \
    --eval "(setq initial-scratch-message nil)" \
    --eval "(load-file \"$SCRIPT_DIR/wave-screenshot.el\")" \
    --eval "(wave-demo-wave-detail)" \
    --eval "(set-frame-size (selected-frame) 100 40)" \
    --eval "(redisplay t)" &
EMACS_PID2=$!

sleep 3
capture_screenshot "wave-detail" 1

# Cleanup
kill $EMACS_PID 2>/dev/null || true
kill $EMACS_PID2 2>/dev/null || true

if [ -n "$CLEANUP_XVFB" ]; then
    kill $XVFB_PID 2>/dev/null || true
fi

echo ""
echo "=== Screenshots captured ==="
ls -la "$SCREENSHOT_DIR"/*.png 2>/dev/null || echo "No screenshots found"
