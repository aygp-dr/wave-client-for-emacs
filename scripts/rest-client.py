#!/usr/bin/env python3
"""Simple REST client for testing Wave API endpoints.

Works with both the real server (port 9898) and mock server (port 4010).

Usage:
    python scripts/rest-client.py              # Test real server
    python scripts/rest-client.py --mock       # Test mock server
    python scripts/rest-client.py --interactive  # Interactive mode
"""

import argparse
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class WaveRestClient:
    """Simple REST client for Wave API."""

    def __init__(self, base_url: str = "http://localhost:9898"):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Make HTTP request and return JSON response."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            return {"error": e.code, "message": e.reason}
        except URLError as e:
            return {"error": "connection", "message": str(e.reason)}

    def get_inbox(self) -> list:
        """Get all waves in inbox."""
        return self._request("GET", "/api/inbox")

    def get_wave(self, wave_id: str) -> list:
        """Get wave details by ID."""
        # URL encode the wave ID
        encoded_id = wave_id.replace("!", "%21").replace("+", "%2B")
        return self._request("GET", f"/api/waves/{encoded_id}")

    def submit_delta(self, wave_id: str, wavelet_id: str, author: str, operations: list) -> dict:
        """Submit delta operations to a wave."""
        encoded_id = wave_id.replace("!", "%21").replace("+", "%2B")
        data = {
            "waveletName": {
                "waveId": wave_id,
                "waveletId": wavelet_id
            },
            "delta": {
                "author": author,
                "operations": operations
            }
        }
        return self._request("POST", f"/api/waves/{encoded_id}/submit", data)

    def add_participant(self, wave_id: str, wavelet_id: str, author: str, participant: str) -> dict:
        """Add a participant to a wave."""
        operations = [{"type": "addParticipant", "participant": participant}]
        return self.submit_delta(wave_id, wavelet_id, author, operations)


def run_tests(client: WaveRestClient) -> bool:
    """Run basic API tests."""
    print(f"Testing Wave API at {client.base_url}\n")
    all_passed = True
    tests_run = 0
    tests_passed = 0

    # Test 1: Get inbox
    tests_run += 1
    print("1. GET /api/inbox")
    result = client.get_inbox()
    if "error" in result:
        print(f"   FAIL: {result}")
        all_passed = False
    else:
        print(f"   OK: {len(result)} waves in inbox")
        tests_passed += 1
        for wave in result[:3]:
            print(f"      - {wave.get('id', 'unknown')}: {wave.get('digest', '')[:40]}")

    # Test 2: Get specific wave
    tests_run += 1
    print("\n2. GET /api/waves/{id}")
    wave_id = "indexwave!indexwave"
    result = client.get_wave(wave_id)
    if "error" in result:
        print(f"   FAIL: {result}")
        all_passed = False
    else:
        print(f"   OK: {len(result)} wavelets returned")
        tests_passed += 1
        if result:
            wavelet = result[0]
            print(f"      - creator: {wavelet.get('creator', 'unknown')}")
            print(f"      - participants: {wavelet.get('participants', [])}")

    # Test 3: Submit delta (add participant)
    tests_run += 1
    print("\n3. POST /api/waves/{id}/submit (add participant)")
    result = client.add_participant(
        wave_id="indexwave!indexwave",
        wavelet_id="indexwave!indexwave",
        author="test@localhost",
        participant="testuser@localhost"
    )
    if "error" in result:
        print(f"   FAIL: {result}")
        all_passed = False
    else:
        print(f"   OK: success={result.get('success')}, version={result.get('version')}")
        tests_passed += 1

    # Test 4: Get non-existent wave (expect 404)
    tests_run += 1
    print("\n4. GET /api/waves/{id} (non-existent - expect 404)")
    result = client.get_wave("nonexistent!wave")
    if "error" in result and result.get("error") == 404:
        print(f"   OK: Got expected 404")
        tests_passed += 1
    elif "error" in result:
        print(f"   OK: Got error (expected): {result}")
        tests_passed += 1
    else:
        print(f"   WARN: Expected 404, got data: {result}")

    # Test 5: Remove participant
    tests_run += 1
    print("\n5. POST /api/waves/{id}/submit (remove participant)")
    result = client.submit_delta(
        wave_id="indexwave!indexwave",
        wavelet_id="indexwave!indexwave",
        author="test@localhost",
        operations=[{"type": "removeParticipant", "participant": "testuser@localhost"}]
    )
    if "error" in result:
        print(f"   FAIL: {result}")
        all_passed = False
    else:
        print(f"   OK: success={result.get('success')}, version={result.get('version')}")
        tests_passed += 1

    # Test 6: Verify participant removed
    tests_run += 1
    print("\n6. GET /api/waves/{id} (verify participant removed)")
    result = client.get_wave("indexwave!indexwave")
    if "error" in result:
        print(f"   FAIL: {result}")
        all_passed = False
    else:
        participants = result[0].get('participants', []) if result else []
        if "testuser@localhost" not in participants:
            print(f"   OK: testuser@localhost not in participants")
            tests_passed += 1
        else:
            print(f"   WARN: testuser@localhost still in participants: {participants}")

    print("\n" + "=" * 40)
    print(f"Result: {tests_passed}/{tests_run} tests passed")
    return all_passed


def interactive_mode(client: WaveRestClient):
    """Interactive REPL for testing API."""
    print(f"Wave REST Client - {client.base_url}")
    print("Commands: inbox, wave <id>, add <wave_id> <participant>, quit")
    print()

    while True:
        try:
            cmd = input("> ").strip().split()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not cmd:
            continue

        if cmd[0] == "quit":
            break
        elif cmd[0] == "inbox":
            result = client.get_inbox()
            print(json.dumps(result, indent=2))
        elif cmd[0] == "wave" and len(cmd) > 1:
            result = client.get_wave(cmd[1])
            print(json.dumps(result, indent=2))
        elif cmd[0] == "add" and len(cmd) > 2:
            result = client.add_participant(
                wave_id=cmd[1],
                wavelet_id=cmd[1].replace("!w+", "!conv+"),
                author="cli@localhost",
                participant=cmd[2]
            )
            print(json.dumps(result, indent=2))
        else:
            print("Unknown command. Try: inbox, wave <id>, add <wave_id> <participant>, quit")


def main():
    parser = argparse.ArgumentParser(description="Wave REST API client")
    parser.add_argument("--mock", action="store_true", help="Use mock server (port 4010)")
    parser.add_argument("--url", help="Custom server URL")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    if args.url:
        base_url = args.url
    elif args.mock:
        base_url = "http://localhost:4010"
    else:
        base_url = "http://localhost:9898"

    client = WaveRestClient(base_url)

    if args.interactive:
        interactive_mode(client)
    else:
        success = run_tests(client)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
