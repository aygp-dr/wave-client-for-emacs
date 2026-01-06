#!/usr/bin/env python3
"""Wave Client TUI Dashboard.

A simple terminal UI for interacting with the Wave server.

Usage:
    python scripts/wave-dashboard.py
    python scripts/wave-dashboard.py --url http://localhost:9898
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets


class WaveClient:
    """Combined REST + WebSocket client."""

    def __init__(self, http_url: str = "http://localhost:9898", ws_url: str = "ws://localhost:9898/ws"):
        self.http_url = http_url.rstrip("/")
        self.ws_url = ws_url
        self.ws = None
        self.current_wave = None
        self.inbox = []
        self.wavelets = {}

    def _http_get(self, endpoint: str) -> dict | list:
        """Make HTTP GET request."""
        url = f"{self.http_url}{endpoint}"
        req = Request(url, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except (HTTPError, URLError) as e:
            return {"error": str(e)}

    def get_inbox(self) -> list:
        """Fetch inbox."""
        result = self._http_get("/api/inbox")
        if isinstance(result, list):
            self.inbox = result
        return result

    def get_wave(self, wave_id: str) -> list:
        """Fetch wave details."""
        encoded_id = wave_id.replace("!", "%21").replace("+", "%2B")
        result = self._http_get(f"/api/waves/{encoded_id}")
        if isinstance(result, list):
            self.wavelets[wave_id] = result
        return result


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header():
    """Print dashboard header."""
    print("=" * 60)
    print("  🌊 WAVE CLIENT DASHBOARD")
    print("=" * 60)
    print()


def print_inbox(inbox: list):
    """Print inbox listing."""
    print("📥 INBOX")
    print("-" * 40)
    if not inbox:
        print("  (empty)")
    else:
        for i, wave in enumerate(inbox, 1):
            unread = wave.get('unread', 0)
            marker = "🔵" if unread > 0 else "  "
            digest = wave.get('digest', 'No subject')[:40]
            print(f"  {marker} [{i}] {digest}")
            print(f"       ID: {wave.get('id', 'unknown')}")
            print(f"       Creator: {wave.get('creator', 'unknown')}")
            if unread > 0:
                print(f"       Unread: {unread}")
            print()
    print()


def print_wave(wave_id: str, wavelets: list):
    """Print wave details."""
    print(f"📄 WAVE: {wave_id}")
    print("-" * 40)
    if not wavelets:
        print("  (no wavelets)")
    else:
        for wavelet in wavelets:
            name = wavelet.get('waveletName', {})
            print(f"  Wavelet: {name.get('waveletId', 'unknown')}")
            print(f"  Creator: {wavelet.get('creator', 'unknown')}")
            print(f"  Version: {wavelet.get('version', {}).get('version', 0)}")

            participants = wavelet.get('participants', [])
            print(f"  Participants: {', '.join(participants)}")

            docs = wavelet.get('docs', {})
            if docs:
                print(f"  Documents: {len(docs)}")
                for doc_id, doc in docs.items():
                    content = doc.get('content', [])
                    text_parts = [c for c in content if isinstance(c, str)]
                    text = ' '.join(text_parts)[:60]
                    print(f"    - {doc_id}: {text or '(empty)'}")
            print()
    print()


def print_help():
    """Print help."""
    print("📖 COMMANDS")
    print("-" * 40)
    print("  inbox, i     - Refresh inbox")
    print("  open <n>     - Open wave by number")
    print("  wave <id>    - Open wave by ID")
    print("  refresh, r   - Refresh current view")
    print("  clear, c     - Clear screen")
    print("  help, h, ?   - Show this help")
    print("  quit, q      - Exit")
    print()


def run_dashboard(client: WaveClient):
    """Run interactive dashboard."""
    clear_screen()
    print_header()

    # Initial inbox fetch
    print("Connecting to server...")
    inbox = client.get_inbox()
    if isinstance(inbox, dict) and "error" in inbox:
        print(f"❌ Error: {inbox['error']}")
        print("Make sure the server is running: gmake server")
        return

    clear_screen()
    print_header()
    print_inbox(inbox)
    print_help()

    current_wave_id = None

    while True:
        try:
            cmd = input("wave> ").strip().lower().split()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            break

        if not cmd:
            continue

        action = cmd[0]

        if action in ('quit', 'q', 'exit'):
            print("Goodbye! 👋")
            break

        elif action in ('help', 'h', '?'):
            print_help()

        elif action in ('clear', 'c'):
            clear_screen()
            print_header()
            if current_wave_id:
                wavelets = client.wavelets.get(current_wave_id, [])
                print_wave(current_wave_id, wavelets)
            else:
                print_inbox(client.inbox)

        elif action in ('inbox', 'i', 'list', 'ls'):
            clear_screen()
            print_header()
            inbox = client.get_inbox()
            print_inbox(inbox)
            current_wave_id = None

        elif action in ('refresh', 'r'):
            if current_wave_id:
                wavelets = client.get_wave(current_wave_id)
                clear_screen()
                print_header()
                print_wave(current_wave_id, wavelets)
            else:
                inbox = client.get_inbox()
                clear_screen()
                print_header()
                print_inbox(inbox)

        elif action == 'open' and len(cmd) > 1:
            try:
                idx = int(cmd[1]) - 1
                if 0 <= idx < len(client.inbox):
                    wave_id = client.inbox[idx].get('id')
                    wavelets = client.get_wave(wave_id)
                    clear_screen()
                    print_header()
                    print_wave(wave_id, wavelets)
                    current_wave_id = wave_id
                else:
                    print(f"Invalid index. Use 1-{len(client.inbox)}")
            except ValueError:
                print("Usage: open <number>")

        elif action == 'wave' and len(cmd) > 1:
            wave_id = cmd[1]
            wavelets = client.get_wave(wave_id)
            if isinstance(wavelets, dict) and "error" in wavelets:
                print(f"❌ Error: {wavelets['error']}")
            else:
                clear_screen()
                print_header()
                print_wave(wave_id, wavelets)
                current_wave_id = wave_id

        elif action == 'back' or action == 'b':
            clear_screen()
            print_header()
            print_inbox(client.inbox)
            current_wave_id = None

        else:
            print(f"Unknown command: {action}. Type 'help' for commands.")


async def run_websocket_monitor(client: WaveClient):
    """Monitor WebSocket for real-time updates."""
    print(f"Connecting to WebSocket at {client.ws_url}...")
    try:
        async with websockets.connect(client.ws_url) as ws:
            print("✅ Connected! Waiting for updates...")
            print("Press Ctrl+C to stop\n")

            # Open the index wave
            msg = {
                "version": 0,
                "sequenceNumber": 1,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": "indexwave!indexwave"})
            }
            await ws.send(json.dumps(msg))

            async for message in ws:
                data = json.loads(message)
                timestamp = datetime.now().strftime("%H:%M:%S")
                msg_type = data.get("messageType", "unknown")
                print(f"[{timestamp}] {msg_type}")

                if msg_type == "ProtocolWaveletUpdate":
                    msg_json = json.loads(data.get("messageJson", "{}"))
                    print(f"         Wave: {msg_json.get('1', 'unknown')}")
                    print(f"         Version: {msg_json.get('4', {}).get('1', 0)}")
                print()

    except websockets.ConnectionClosed:
        print("Connection closed")
    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Wave Client Dashboard")
    parser.add_argument("--url", default="http://localhost:9898", help="Server HTTP URL")
    parser.add_argument("--ws", action="store_true", help="WebSocket monitor mode")
    args = parser.parse_args()

    ws_url = args.url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    client = WaveClient(http_url=args.url, ws_url=ws_url)

    if args.ws:
        asyncio.run(run_websocket_monitor(client))
    else:
        run_dashboard(client)


if __name__ == "__main__":
    main()
