#!/usr/bin/env python3
"""WebSocket test client for Wave server.

Usage:
    python scripts/ws-test.py              # Test connection
    python scripts/ws-test.py --wave ID    # Open specific wave
    python scripts/ws-test.py --interactive # Interactive mode
"""

import argparse
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets


async def test_connection(url: str, wave_id: str = "localhost!w+abc123"):
    """Test WebSocket connection and ProtocolOpenRequest."""
    print(f"Connecting to {url}...")

    try:
        async with websockets.connect(url) as ws:
            print("Connected!")

            # Send ProtocolOpenRequest
            msg = {
                "version": 0,
                "sequenceNumber": 1,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": wave_id})
            }
            print(f"Sending: {json.dumps(msg, indent=2)}")
            await ws.send(json.dumps(msg))

            # Wait for response
            print("Waiting for response...")
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"Received: {json.dumps(json.loads(response), indent=2)}")
            except asyncio.TimeoutError:
                print("No response received within 5 seconds")

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


async def interactive_mode(url: str):
    """Interactive WebSocket session."""
    print(f"Connecting to {url}...")
    print("Commands: open <wave_id>, submit <wave_id> <op>, quit")
    print()

    try:
        async with websockets.connect(url) as ws:
            print("Connected! Type 'quit' to exit.\n")

            # Background task to receive messages
            async def receiver():
                try:
                    async for message in ws:
                        data = json.loads(message)
                        print(f"\n<< Received: {json.dumps(data, indent=2)}")
                        print("> ", end="", flush=True)
                except websockets.ConnectionClosed:
                    pass

            recv_task = asyncio.create_task(receiver())

            # Input loop
            seq = 1
            while True:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("> ")
                    )
                except EOFError:
                    break

                parts = line.strip().split()
                if not parts:
                    continue

                cmd = parts[0].lower()

                if cmd == "quit":
                    break
                elif cmd == "open" and len(parts) > 1:
                    wave_id = parts[1]
                    msg = {
                        "version": 0,
                        "sequenceNumber": seq,
                        "messageType": "ProtocolOpenRequest",
                        "messageJson": json.dumps({"2": wave_id})
                    }
                    seq += 1
                    print(f">> Sending: {json.dumps(msg)}")
                    await ws.send(json.dumps(msg))
                elif cmd == "ping":
                    msg = {"type": "ping"}
                    await ws.send(json.dumps(msg))
                    print(">> Sent ping")
                else:
                    print("Unknown command. Try: open <wave_id>, ping, quit")

            recv_task.cancel()

    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Wave WebSocket test client")
    parser.add_argument("--url", default="ws://localhost:9898/ws", help="WebSocket URL")
    parser.add_argument("--wave", default="indexwave!indexwave", help="Wave ID to open")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    if args.interactive:
        asyncio.run(interactive_mode(args.url))
    else:
        success = asyncio.run(test_connection(args.url, args.wave))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
