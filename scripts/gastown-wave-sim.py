#!/usr/bin/env python3
"""
Simulate gastown agent communication via Wave protocol.

This script simulates how gastown agents (mayor, deacon, polecats, witness)
would communicate using Wave as the substrate, based on our actual work session.
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Optional

WAVE_SERVER = "http://localhost:9898"

# Gastown agents as Wave participants
AGENTS = {
    "mayor": "mayor@gastown.local",
    "deacon": "deacon@gastown.local",
    "witness": "witness@gastown.local",
    "refinery": "refinery@gastown.local",
    "polecat-furiosa": "polecat-furiosa@gastown.local",
}

# Our actual work session reconstructed as Wave messages
SESSION_TRANSCRIPT = [
    {
        "from": "mayor",
        "action": "create_wave",
        "wave_id": "gastown!session-2026-01-10",
        "title": "Wave Client Integration Testing Session",
        "participants": ["mayor", "polecat-furiosa", "witness"],
    },
    {
        "from": "mayor",
        "action": "blip",
        "content": "Starting integration test suite. Server running on :9898. 32 tests to run.",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Claiming task: Fix GET /api/waves/{id} 500 error. Investigating...",
    },
    {
        "from": "witness",
        "action": "blip",
        "content": "📊 Observing: polecat-furiosa started wave-client-for-emacs-53e",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Found issue: doc_data is list not dict. Adding type check in get_wave endpoint.",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Also adding missing /health endpoint to wave_server.py",
    },
    {
        "from": "witness",
        "action": "blip",
        "content": "📝 Files modified: src/wave_client_server/wave_server.py",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "✅ GET /api/waves/{id} now returns 200. Running tests...",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "REST tests: 18/18 passing. WebSocket tests: need to fix websockets 15+ API.",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Updated tests to use ws.state instead of ws.open for websockets 15.0.1",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "✅ All tests passing! REST: 18/18, WebSocket: 14/14, Total: 32/32",
    },
    {
        "from": "witness",
        "action": "blip",
        "content": "📊 Test results recorded. Commits: f2497a8, c8d1f1b",
    },
    {
        "from": "mayor",
        "action": "blip",
        "content": "Excellent work! Now let's add screenshots and documentation.",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Creating scripts/wave-screenshot.el for X11 captures...",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Creating scripts/wave-batch-demo.el for terminal output...",
    },
    {
        "from": "witness",
        "action": "blip",
        "content": "📷 Screenshots captured: wave-inbox.png, wave-detail.png (4 files total)",
    },
    {
        "from": "polecat-furiosa",
        "action": "blip",
        "content": "Documentation updated in jwalsh/www.wal.sh/research/wave/index.org",
    },
    {
        "from": "mayor",
        "action": "blip",
        "content": "All work committed and pushed. Creating bead for two-user simulation.",
    },
    {
        "from": "witness",
        "action": "blip",
        "content": "📋 Session complete. Issues: 22 total, 2 completed this session.",
    },
    {
        "from": "mayor",
        "action": "close_wave",
        "reason": "Session objectives completed successfully.",
    },
]


def print_header():
    """Print simulation header."""
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              Gastown Agent Communication via Wave Protocol                   ║")
    print("║                                                                              ║")
    print("║  Simulating multi-agent collaboration from session 2026-01-10                ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()


def print_separator():
    """Print separator line."""
    print("──────────────────────────────────────────────────────────────────────────────────")


def format_agent(agent: str) -> str:
    """Format agent name with emoji."""
    icons = {
        "mayor": "🎩",
        "deacon": "🐺",
        "witness": "🦉",
        "refinery": "🏭",
        "polecat-furiosa": "😺",
    }
    return f"{icons.get(agent, '👤')} {agent}"


def simulate_message(msg: dict, delay: float = 0.3):
    """Simulate a Wave message with formatting."""
    agent = msg["from"]
    action = msg["action"]
    timestamp = datetime.now().strftime("%H:%M:%S")

    if action == "create_wave":
        print_separator()
        print(f"[{timestamp}] {format_agent(agent)} created wave: {msg['wave_id']}")
        print(f"           Title: {msg['title']}")
        print(f"           Participants: {', '.join(msg['participants'])}")
        print_separator()

    elif action == "blip":
        content = msg["content"]
        # Wrap long content
        if len(content) > 70:
            lines = [content[i:i+70] for i in range(0, len(content), 70)]
            print(f"[{timestamp}] {format_agent(agent)}:")
            for line in lines:
                print(f"           {line}")
        else:
            print(f"[{timestamp}] {format_agent(agent)}: {content}")

    elif action == "close_wave":
        print_separator()
        print(f"[{timestamp}] {format_agent(agent)} closed wave")
        print(f"           Reason: {msg['reason']}")
        print_separator()


async def check_server():
    """Check if Wave server is running."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{WAVE_SERVER}/health", timeout=5.0)
            if resp.status_code == 200:
                return True
    except:
        pass
    return False


async def post_to_wave(wave_id: str, author: str, content: str):
    """Post a message to the Wave server."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{WAVE_SERVER}/api/waves/{wave_id}/submit",
                json={
                    "wavelet_name": {
                        "wave_id": wave_id,
                        "wavelet_id": wave_id
                    },
                    "delta": {
                        "author": AGENTS.get(author, author),
                        "operations": [
                            {"type": "noOp"}  # Placeholder - real impl would add blip
                        ]
                    }
                },
                timeout=5.0
            )
            return resp.status_code == 200
    except:
        return False


async def run_simulation(live: bool = False):
    """Run the gastown communication simulation."""
    print_header()

    if live:
        server_ok = await check_server()
        if server_ok:
            print("✓ Wave server is running - posting to real server")
        else:
            print("⚠ Wave server not running - simulation only")
            live = False

    print()
    print("Starting simulation...")
    print()

    for msg in SESSION_TRANSCRIPT:
        simulate_message(msg)

        # If live mode, actually post to Wave server
        if live and msg["action"] == "blip":
            await post_to_wave(
                "gastown!session-2026-01-10",
                msg["from"],
                msg["content"]
            )

        await asyncio.sleep(0.5)  # Simulate real-time delay

    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                         Simulation Complete                                  ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    print("Summary:")
    print(f"  • Messages exchanged: {len(SESSION_TRANSCRIPT)}")
    print(f"  • Agents involved: {len(set(m['from'] for m in SESSION_TRANSCRIPT))}")
    print(f"  • Tasks completed: 2 (API fix, screenshots)")
    print(f"  • Tests passing: 32/32")
    print()


if __name__ == "__main__":
    import sys
    live = "--live" in sys.argv
    asyncio.run(run_simulation(live=live))
