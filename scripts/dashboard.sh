#!/usr/bin/env bash
# Wave Dashboard - tmux session with server and client

set -e

# Session name
SESSION="wave-dashboard"

# Load environment
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Wave Dashboard${NC}"
echo "================="

# Check if tmux session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo -e "${YELLOW}Session '$SESSION' already exists. Attaching...${NC}"
    tmux attach-session -t "$SESSION"
    exit 0
fi

echo -e "${GREEN}Creating new tmux session: $SESSION${NC}"

# Create tmux session with server pane
tmux new-session -d -s "$SESSION" -n "wave" -c "$(pwd)"

# Set up the layout
tmux split-window -h -t "$SESSION:wave" -c "$(pwd)"
tmux split-window -v -t "$SESSION:wave.1" -c "$(pwd)"

# Configure panes
# Pane 0 (left): Wave Server
tmux send-keys -t "$SESSION:wave.0" "echo 'Wave Server - Port 9898'" C-m
tmux send-keys -t "$SESSION:wave.0" "echo '====================='" C-m
tmux send-keys -t "$SESSION:wave.0" "uv run wave-client-server" C-m

# Wait for server to start
sleep 3

# Pane 1 (top-right): Emacs Client
tmux send-keys -t "$SESSION:wave.1" "echo 'Wave Emacs Client'" C-m
tmux send-keys -t "$SESSION:wave.1" "echo '================'" C-m
tmux send-keys -t "$SESSION:wave.1" "echo 'Server: $WAVE_SERVER_URL'" C-m
tmux send-keys -t "$SESSION:wave.1" "echo 'User: $WAVE_CLIENT_USER'" C-m
tmux send-keys -t "$SESSION:wave.1" "echo ''" C-m
tmux send-keys -t "$SESSION:wave.1" "echo 'Starting Emacs...'" C-m
tmux send-keys -t "$SESSION:wave.1" "${EMACS_BIN:-emacs} -nw -Q -l init.el" C-m

# Pane 2 (bottom-right): Server logs/monitoring
tmux send-keys -t "$SESSION:wave.2" "echo 'Server Monitor'" C-m
tmux send-keys -t "$SESSION:wave.2" "echo '============='" C-m
tmux send-keys -t "$SESSION:wave.2" "echo ''" C-m
tmux send-keys -t "$SESSION:wave.2" "echo 'Commands:'" C-m
tmux send-keys -t "$SESSION:wave.2" "echo '  curl http://localhost:9898/              # Check server'" C-m
tmux send-keys -t "$SESSION:wave.2" "echo '  curl http://localhost:9898/api/inbox    # Get inbox'" C-m
tmux send-keys -t "$SESSION:wave.2" "echo '  curl http://localhost:9898/docs         # API docs'" C-m
tmux send-keys -t "$SESSION:wave.2" "echo ''" C-m
tmux send-keys -t "$SESSION:wave.2" "# Server health check" C-m
if command -v jq >/dev/null 2>&1; then
    tmux send-keys -t "$SESSION:wave.2" "watch -n 5 'curl -s http://localhost:9898/health | jq .'" C-m
else
    tmux send-keys -t "$SESSION:wave.2" "watch -n 5 'curl -s http://localhost:9898/health'" C-m
fi

# Set pane titles
tmux select-pane -t "$SESSION:wave.0" -T "Wave Server"
tmux select-pane -t "$SESSION:wave.1" -T "Emacs Client"
tmux select-pane -t "$SESSION:wave.2" -T "Monitor"

# Enable pane borders and titles
tmux set-option -t "$SESSION" pane-border-status top
tmux set-option -t "$SESSION" pane-border-format "#{pane_index}: #{pane_title}"

# Focus on Emacs pane
tmux select-pane -t "$SESSION:wave.1"

# Attach to session
echo -e "${GREEN}Attaching to tmux session...${NC}"
echo ""
echo "Keyboard shortcuts:"
echo "  Ctrl-b %    - Split vertically"
echo "  Ctrl-b \"    - Split horizontally"
echo "  Ctrl-b o    - Switch panes"
echo "  Ctrl-b d    - Detach session"
echo "  Ctrl-b x    - Kill pane"
echo ""

tmux attach-session -t "$SESSION"