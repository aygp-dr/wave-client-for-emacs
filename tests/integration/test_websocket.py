"""Integration tests for WebSocket functionality."""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import patch

from wave_client_server.wave_server import app, server


class TestWebSocketIntegration:
    """Test WebSocket integration scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client with WebSocket support."""
        return TestClient(app)
    
    def test_websocket_connect(self, client):
        """Test WebSocket connection establishment."""
        with client.websocket_connect("/ws") as websocket:
            # Should receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "welcome"
            assert "channelId" in data
    
    def test_websocket_open_wave(self, client):
        """Test opening a wave via WebSocket."""
        with patch.object(server, 'get_wave') as mock_get_wave:
            mock_get_wave.return_value = {
                "wave_id": "test!w+123",
                "creator": "test@example.com",
                "wavelets": [
                    {
                        "wavelet_id": "test!conv+root",
                        "participants": ["test@example.com"],
                        "docs": {"main": {"content": ["Test content"]}}
                    }
                ]
            }
            
            with client.websocket_connect("/ws") as websocket:
                # Receive welcome
                welcome = websocket.receive_json()
                channel_id = welcome["channelId"]
                
                # Send open wave request
                websocket.send_json({
                    "type": "open_wave",
                    "wave_id": "test!w+123"
                })
                
                # Should receive wave data
                response = websocket.receive_json()
                assert response["type"] == "wave_data"
                assert response["wave"]["wave_id"] == "test!w+123"
    
    def test_websocket_submit_delta(self, client):
        """Test submitting a delta via WebSocket."""
        with patch.object(server, 'update_wavelet') as mock_update:
            with patch.object(server, 'record_update') as mock_record:
                with client.websocket_connect("/ws") as websocket:
                    # Receive welcome
                    welcome = websocket.receive_json()
                    channel_id = welcome["channelId"]
                    
                    # Send delta
                    delta = {
                        "type": "submit_delta",
                        "wave_id": "test!w+123",
                        "wavelet_id": "test!conv+root",
                        "delta": {
                            "version": 2,
                            "operations": [
                                {"type": "retain", "count": 5},
                                {"type": "characters", "text": " World"}
                            ]
                        }
                    }
                    websocket.send_json(delta)
                    
                    # Should receive acknowledgment
                    response = websocket.receive_json()
                    assert response["type"] == "delta_acknowledged"
                    assert response["wave_id"] == "test!w+123"
    
    def test_websocket_error_handling(self, client):
        """Test WebSocket error handling."""
        with client.websocket_connect("/ws") as websocket:
            # Receive welcome
            welcome = websocket.receive_json()
            
            # Send invalid message
            websocket.send_json({
                "type": "invalid_type",
                "data": "test"
            })
            
            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Unknown message type" in response["message"]
    
    def test_websocket_disconnect_cleanup(self, client):
        """Test cleanup on WebSocket disconnect."""
        with patch.object(server.manager, 'disconnect') as mock_disconnect:
            with client.websocket_connect("/ws") as websocket:
                welcome = websocket.receive_json()
                channel_id = welcome["channelId"]
            
            # After context exits, disconnect should be called
            mock_disconnect.assert_called_once_with(channel_id)


class TestMultiClientWebSocket:
    """Test multi-client WebSocket scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_broadcast_to_multiple_clients(self, client):
        """Test broadcasting updates to multiple connected clients."""
        with client.websocket_connect("/ws") as ws1:
            with client.websocket_connect("/ws") as ws2:
                # Get channel IDs
                welcome1 = ws1.receive_json()
                welcome2 = ws2.receive_json()
                channel1 = welcome1["channelId"]
                channel2 = welcome2["channelId"]
                
                # Client 1 sends an update
                ws1.send_json({
                    "type": "submit_delta",
                    "wave_id": "test!w+123",
                    "wavelet_id": "test!conv+root",
                    "delta": {"version": 2, "operations": []}
                })
                
                # Both clients should receive the update
                # Client 1 gets acknowledgment
                response1 = ws1.receive_json()
                assert response1["type"] == "delta_acknowledged"
                
                # Client 2 gets the update broadcast
                # (In real implementation, this would happen)
                # This test is simplified - real broadcast logic would be tested
                # with proper async handling