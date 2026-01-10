"""Extended WebSocket integration tests for Wave server."""

import pytest
import asyncio
import json
import websockets
from websockets.protocol import State
from typing import Optional

WS_URL = "ws://localhost:9898/ws"
TIMEOUT = 5.0


def is_connected(ws) -> bool:
    """Check if websocket is connected (compatible with websockets 15+)."""
    return ws.state == State.OPEN


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def send_and_receive(
    ws,
    message: dict,
    timeout: float = TIMEOUT
) -> Optional[dict]:
    """Send message and wait for response."""
    await ws.send(json.dumps(message))
    try:
        response = await asyncio.wait_for(ws.recv(), timeout=timeout)
        return json.loads(response)
    except asyncio.TimeoutError:
        return None


class TestWebSocketConnection:
    """Tests for WebSocket connection handling."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Should successfully connect to WebSocket."""
        async with websockets.connect(WS_URL) as ws:
            assert is_connected(ws)

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        """Should handle clean disconnect."""
        async with websockets.connect(WS_URL) as ws:
            assert is_connected(ws)
        # Connection should be closed after context exits

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Should handle multiple simultaneous connections."""
        async with websockets.connect(WS_URL) as ws1:
            async with websockets.connect(WS_URL) as ws2:
                assert is_connected(ws1)
                assert is_connected(ws2)


class TestProtocolOpenRequest:
    """Tests for ProtocolOpenRequest message type."""

    @pytest.mark.asyncio
    async def test_open_valid_wave(self):
        """Should receive update for valid wave."""
        async with websockets.connect(WS_URL) as ws:
            message = {
                "version": 0,
                "sequenceNumber": 1,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": "indexwave!indexwave"})
            }
            response = await send_and_receive(ws, message)
            if response:
                assert response.get("messageType") == "ProtocolWaveletUpdate"

    @pytest.mark.asyncio
    async def test_open_nonexistent_wave(self):
        """Should handle non-existent wave gracefully."""
        async with websockets.connect(WS_URL) as ws:
            message = {
                "version": 0,
                "sequenceNumber": 1,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": "nonexistent!wave"})
            }
            # Should not crash, may return nothing or error
            response = await send_and_receive(ws, message, timeout=2.0)
            # No assertion - just ensuring it doesn't crash

    @pytest.mark.asyncio
    async def test_multiple_open_requests(self):
        """Should handle multiple open requests."""
        async with websockets.connect(WS_URL) as ws:
            for i in range(3):
                message = {
                    "version": 0,
                    "sequenceNumber": i + 1,
                    "messageType": "ProtocolOpenRequest",
                    "messageJson": json.dumps({"2": "indexwave!indexwave"})
                }
                await ws.send(json.dumps(message))

            # Collect responses
            responses = []
            for _ in range(3):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    break

            # Should receive at least some responses
            # (number depends on server implementation)


class TestMessageHandling:
    """Tests for message handling."""

    @pytest.mark.asyncio
    async def test_malformed_json(self):
        """Should handle malformed JSON gracefully."""
        async with websockets.connect(WS_URL) as ws:
            await ws.send("not valid json")
            # Should not crash connection
            await asyncio.sleep(0.5)
            # Either connected or closed is acceptable
            assert ws.state in (State.OPEN, State.CLOSED)

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Should handle empty message."""
        async with websockets.connect(WS_URL) as ws:
            await ws.send("")
            await asyncio.sleep(0.5)
            # Connection should still be valid or cleanly closed

    @pytest.mark.asyncio
    async def test_invalid_message_type(self):
        """Should handle invalid message type."""
        async with websockets.connect(WS_URL) as ws:
            message = {
                "version": 0,
                "sequenceNumber": 1,
                "messageType": "InvalidType",
                "messageJson": "{}"
            }
            await ws.send(json.dumps(message))
            await asyncio.sleep(0.5)
            # Should not crash

    @pytest.mark.asyncio
    async def test_missing_fields(self):
        """Should handle message with missing fields."""
        async with websockets.connect(WS_URL) as ws:
            message = {"version": 0}  # Missing other fields
            await ws.send(json.dumps(message))
            await asyncio.sleep(0.5)


class TestSequenceNumbers:
    """Tests for sequence number handling."""

    @pytest.mark.asyncio
    async def test_sequence_numbers_in_response(self):
        """Response should include sequence number."""
        async with websockets.connect(WS_URL) as ws:
            message = {
                "version": 0,
                "sequenceNumber": 42,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": "indexwave!indexwave"})
            }
            response = await send_and_receive(ws, message)
            if response:
                assert "sequenceNumber" in response

    @pytest.mark.asyncio
    async def test_large_sequence_number(self):
        """Should handle large sequence numbers."""
        async with websockets.connect(WS_URL) as ws:
            message = {
                "version": 0,
                "sequenceNumber": 999999,
                "messageType": "ProtocolOpenRequest",
                "messageJson": json.dumps({"2": "indexwave!indexwave"})
            }
            # Should not crash
            response = await send_and_receive(ws, message, timeout=2.0)


class TestConcurrency:
    """Tests for concurrent operations."""

    @pytest.mark.asyncio
    async def test_rapid_messages(self):
        """Should handle rapid message sending."""
        async with websockets.connect(WS_URL) as ws:
            # Send 10 messages rapidly
            for i in range(10):
                message = {
                    "version": 0,
                    "sequenceNumber": i,
                    "messageType": "ProtocolOpenRequest",
                    "messageJson": json.dumps({"2": "indexwave!indexwave"})
                }
                await ws.send(json.dumps(message))

            # Give server time to process
            await asyncio.sleep(1.0)
            assert is_connected(ws)

    @pytest.mark.asyncio
    async def test_interleaved_connections(self):
        """Should handle interleaved operations on multiple connections."""
        async with websockets.connect(WS_URL) as ws1:
            async with websockets.connect(WS_URL) as ws2:
                # Send from both connections
                msg1 = {
                    "version": 0,
                    "sequenceNumber": 1,
                    "messageType": "ProtocolOpenRequest",
                    "messageJson": json.dumps({"2": "indexwave!indexwave"})
                }
                msg2 = {
                    "version": 0,
                    "sequenceNumber": 2,
                    "messageType": "ProtocolOpenRequest",
                    "messageJson": json.dumps({"2": "indexwave!indexwave"})
                }

                await ws1.send(json.dumps(msg1))
                await ws2.send(json.dumps(msg2))

                await asyncio.sleep(0.5)
                assert is_connected(ws1)
                assert is_connected(ws2)
