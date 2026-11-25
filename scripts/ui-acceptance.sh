#!/usr/bin/env bash
# Generate a synthetic DB that covers every UI feature, serve it on a private
# port, and run the Emacs acceptance suite against it. Leaves no server behind.
# Usage: scripts/ui-acceptance.sh [SEED]   (EMACS, PORT override)
set -euo pipefail
cd "$(dirname "$0")/.."
seed="${1:-1}"
port="${PORT:-9897}"
emacs="${EMACS:-emacs}"
work="$(mktemp -d "${TMPDIR:-/tmp}/wave-ui-acceptance.XXXXXX")"
server_pid=""
cleanup() {
  # $server_pid is uv's; uvicorn is its child and outlives it, so also kill
  # whatever this run left listening on the port.
  if [ -n "$server_pid" ]; then
    kill "$server_pid" 2>/dev/null || true
    lsof -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
  fi
  rm -rf "$work"
}
trap cleanup EXIT

if curl -sf "http://localhost:$port/health" >/dev/null; then
  echo "port $port is already serving; set PORT" >&2; exit 2
fi
uv run --extra test python scripts/gen-synthetic-waves.py --db "$work/synthetic.db" --seed "$seed" \
  --witnesses "$work/witnesses.json" 2>/dev/null | grep -E 'world|witnesses|MISS'
WAVE_DATABASE_URL="sqlite:///$work/synthetic.db" uv run uvicorn wave_client_server.wave_server:app \
  --host 127.0.0.1 --port "$port" >"$work/server.log" 2>&1 &
server_pid=$!
for _ in $(seq 30); do curl -sf "http://localhost:$port/health" >/dev/null && break; sleep 0.5; done
WAVE_WITNESSES="$work/witnesses.json" WAVE_UI_SERVER="http://localhost:$port" \
  "$emacs" -Q --batch -L lisp -l tests/wave-ui-acceptance.el -f ert-run-tests-batch-and-exit 2>&1 \
  | grep -E '^\s+(passed|FAILED|skipped)|^Ran|^Test .* condition' 
