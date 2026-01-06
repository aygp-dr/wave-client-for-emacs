#!/usr/bin/env bash
# Record a demo session of the Wave dashboard

OUTPUT_FILE="${1:-docs/demo-session.txt}"

echo "Recording Wave Dashboard Demo..."
echo ""

cat > "$OUTPUT_FILE" << 'HEADER'
Wave Client Dashboard Demo
==========================

Automated demo recording
Server: http://localhost:9898

HEADER

# Record dashboard session
echo "=== Dashboard Session ===" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

{
    sleep 1
    echo "inbox"
    sleep 1
    echo "open 1"
    sleep 1
    echo "refresh"
    sleep 1
    echo "back"
    sleep 1
    echo "quit"
} | python3 scripts/wave-dashboard.py 2>&1 | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' | head -100 >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
echo "=== REST API Tests ===" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
python3 scripts/rest-client.py 2>&1 >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
echo "=== WebSocket Tests ===" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
python3 scripts/ws-test.py 2>&1 >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
cat >> "$OUTPUT_FILE" << 'FOOTER'

=== Available Commands ===

gmake server              # Start Wave server
gmake mock-server         # Start mock server (REST only)
gmake wave-dashboard      # TUI dashboard
gmake wave-monitor        # WebSocket monitor
gmake rest-client         # REST API tests
gmake ws-test             # WebSocket tests

FOOTER

echo "Demo recorded to: $OUTPUT_FILE"
