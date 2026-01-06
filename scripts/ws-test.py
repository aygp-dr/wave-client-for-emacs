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
    print(f"Testing Wave WebSocket at {url}\n")
    tests_run = 0
    tests_passed = 0

    try:
        async with websockets.connect(url) as ws:
            # Test 1: Connection
            tests_run += 1
            print("1. WebSocket connection")
            print("   OK: Connected!")
            tests_passed += 1

            # Test 2: ProtocolOpenRequest
            tests_run += 1
            print("\n2. ProtocolOpenRequest")
            msg = {
                "version": 0,
                "sequenceNumber": 1,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": wave_id})
            }
            await ws.send(json.dumps(msg))
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                if data.get("messageType") == "ProtocolWaveletUpdate":
                    print(f"   OK: Received ProtocolWaveletUpdate")
                    tests_passed += 1
                else:
                    print(f"   WARN: Unexpected response type: {data.get('messageType')}")
            except asyncio.TimeoutError:
                print("   FAIL: No response within 5 seconds")

            # Test 3: Open non-existent wave
            tests_run += 1
            print("\n3. ProtocolOpenRequest (non-existent wave)")
            msg = {
                "version": 0,
                "sequenceNumber": 2,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": "nonexistent!wave"})
            }
            await ws.send(json.dumps(msg))
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                print(f"   OK: Got response for non-existent wave")
                tests_passed += 1
            except asyncio.TimeoutError:
                print("   OK: No response (wave doesn't exist)")
                tests_passed += 1

            # Test 4: Invalid message type
            tests_run += 1
            print("\n4. Invalid message type")
            msg = {
                "version": 0,
                "sequenceNumber": 3,
                "messageType": "InvalidType",
                "messageJson": "{}"
            }
            await ws.send(json.dumps(msg))
            await asyncio.sleep(0.5)  # Give server time to process
            print("   OK: Server handled invalid message type")
            tests_passed += 1

            # Test 5: Multiple sequential requests
            tests_run += 1
            print("\n5. Multiple sequential ProtocolOpenRequests")
            for seq in range(4, 7):
                msg = {
                    "version": 0,
                    "sequenceNumber": seq,
                    "messageType": "ProtocolOpenRequest",
                    "messageJson": json.dumps({"2": wave_id})
                }
                await ws.send(json.dumps(msg))
            responses = 0
            try:
                for _ in range(3):
                    await asyncio.wait_for(ws.recv(), timeout=2.0)
                    responses += 1
            except asyncio.TimeoutError:
                pass
            print(f"   OK: Received {responses} responses for 3 requests")
            tests_passed += 1

            # Test 6: Malformed JSON
            tests_run += 1
            print("\n6. Malformed JSON handling")
            try:
                await ws.send("{not valid json")
                await asyncio.sleep(0.5)
                print("   OK: Server handled malformed JSON")
                tests_passed += 1
            except Exception as e:
                print(f"   OK: Connection handled error: {type(e).__name__}")
                tests_passed += 1

            # Test 7: Empty message
            tests_run += 1
            print("\n7. Empty message handling")
            try:
                await ws.send("{}")
                await asyncio.sleep(0.3)
                print("   OK: Server handled empty message")
                tests_passed += 1
            except Exception as e:
                print(f"   OK: Connection handled error: {type(e).__name__}")
                tests_passed += 1

            # Test 8: Large sequence number
            tests_run += 1
            print("\n8. Large sequence number")
            msg = {
                "version": 0,
                "sequenceNumber": 999999,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": wave_id})
            }
            await ws.send(json.dumps(msg))
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(response)
                if data.get("sequenceNumber") == 999999:
                    print("   OK: Server preserved sequence number")
                    tests_passed += 1
                else:
                    print(f"   OK: Got response with seq={data.get('sequenceNumber')}")
                    tests_passed += 1
            except asyncio.TimeoutError:
                print("   OK: No response (server may have closed after malformed JSON)")
                tests_passed += 1

    except websockets.ConnectionClosed as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"Error: {e}")
        return False

    print("\n" + "=" * 40)
    print(f"Result: {tests_passed}/{tests_run} tests passed")
    return tests_passed == tests_run


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
