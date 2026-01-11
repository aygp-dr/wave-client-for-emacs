#!/bin/sh
# Asciinema demo script - runs in tmux with server + Gas Town demo
# Usage: asciinema rec --command "./scripts/asciinema-demo.sh" docs/demo.cast

set -e

SESSION="wave-asciinema"

# Colors
C='\033[0;36m'  # Cyan
G='\033[0;32m'  # Green
Y='\033[1;33m'  # Yellow
N='\033[0m'     # Reset

clear
echo ""
echo "${C}╔══════════════════════════════════════════════════════════════════════════════╗${N}"
echo "${C}║                  Wave Client for Emacs - Gas Town Demo                       ║${N}"
echo "${C}╚══════════════════════════════════════════════════════════════════════════════╝${N}"
echo ""
sleep 2

# Start server in background
echo "${Y}Starting Wave server on localhost:9898...${N}"
uv run uvicorn wave_client_server.wave_server:app --host 0.0.0.0 --port 9898 > /tmp/wave-server.log 2>&1 &
SERVER_PID=$!
sleep 3
echo "${G}Server started (PID: $SERVER_PID)${N}"
echo ""

# Check inbox
echo "${Y}Checking inbox via REST API...${N}"
curl -s http://localhost:9898/api/inbox | python3 -m json.tool 2>/dev/null | head -20
echo ""
sleep 2

# Emacs batch mode
echo "${Y}Fetching inbox via Emacs Lisp batch mode...${N}"
gmake -s elisp-http-inbox 2>/dev/null || echo "(Emacs not configured)"
echo ""
sleep 2

# Gas Town Demo - Sprint Planning
echo "${Y}Running Gas Town Sprint Planning scenario...${N}"
echo ""
sleep 1
python3 scripts/multi-agent-demo.py --scenario sprint --speed 0.2
echo ""
sleep 2

# Gas Town Demo - Incident Response
echo "${Y}Running Gas Town Incident Response scenario...${N}"
echo ""
sleep 1
python3 scripts/multi-agent-demo.py --scenario incident --speed 0.2
echo ""
sleep 2

# Show crew
echo "${C}Gas Town Crew:${N}"
echo "  Leadership:"
echo "    🎩 Goldie Wilson (Mayor) - Back to the Future"
echo "    📖 Shepherd Book (Deacon) - Firefly"
echo "    👁️ Uatu the Watcher (Witness) - Marvel Comics"
echo "  Polecats:"
echo "    👨‍💻 Henry Case - Neuromancer"
echo "    🔒 Molly Millions - Neuromancer"
echo "    🧪 Rick Deckard - Blade Runner"
echo "    🏗️ Samantha OS1 - Her"
echo "    ⚙️ Kaylee Frye - Firefly"
echo "    🚀 Montgomery Scott - Star Trek"
echo "    🤖 Wintermute - Neuromancer"
echo ""
sleep 3

# Cleanup
echo "${G}Demo complete!${N}"
echo ""
echo "Wave protocol enables real-time collaboration between autonomous agents."
echo "See: https://github.com/aygp-dr/wave-client-for-emacs"
echo ""

# Stop server
kill $SERVER_PID 2>/dev/null || true
