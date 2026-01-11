"""Unit tests for Wave Server implementation."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from wave_client_server.wave_server import (
    ConnectionManager,
    Wave,
    Wavelet,
    WaveServer,
    app,
)


class TestWave:
    """Test Wave model."""

    def test_wave_creation(self):
        """Test creating a new wave."""
        wave = Wave(
            wave_id="test!w+123", creator="user@example.com", created_at=datetime.now()
        )
        assert wave.wave_id == "test!w+123"
        assert wave.creator == "user@example.com"
        assert isinstance(wave.created_at, datetime)


class TestWavelet:
    """Test Wavelet model."""

    def test_wavelet_creation(self):
        """Test creating a new wavelet."""
        wavelet = Wavelet(
            wave_id="test!w+123",
            wavelet_id="test!conv+root",
            creator="user@example.com",
            creation_time=datetime.now(),
            version=1,
            history_hash="hash123",
            last_modified_time=datetime.now(),
            participants=["user@example.com"],
            docs={"main": {"content": ["Hello"]}},
        )
        assert wavelet.wave_id == "test!w+123"
        assert wavelet.wavelet_id == "test!conv+root"
        assert wavelet.version == 1
        assert "user@example.com" in wavelet.participants


class TestConnectionManager:
    """Test WebSocket connection management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConnectionManager()
        self.mock_websocket = Mock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.send_json = AsyncMock()

    async def test_connect(self):
        """Test connecting a WebSocket."""
        channel_id = await self.manager.connect(self.mock_websocket)
        assert channel_id in self.manager.active_connections
        assert self.manager.active_connections[channel_id] == self.mock_websocket

    async def test_disconnect(self):
        """Test disconnecting a WebSocket."""
        channel_id = await self.manager.connect(self.mock_websocket)
        self.manager.disconnect(channel_id)
        assert channel_id not in self.manager.active_connections

    async def test_send_personal_message(self):
        """Test sending a message to a specific connection."""
        channel_id = await self.manager.connect(self.mock_websocket)
        test_message = {"type": "test", "data": "hello"}

        await self.manager.send_personal_message(test_message, channel_id)
        self.mock_websocket.send_json.assert_called_once_with(test_message)

    async def test_broadcast(self):
        """Test broadcasting to all connections."""
        # Connect multiple websockets
        ws1 = Mock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.send_text = AsyncMock()

        channel1 = await self.manager.connect(ws1)
        channel2 = await self.manager.connect(ws2)

        message = "broadcast message"
        await self.manager.broadcast(message)

        ws1.send_text.assert_called_once_with(message)
        ws2.send_text.assert_called_once_with(message)


class TestWaveServer:
    """Test WaveServer class."""

    @pytest.fixture
    def server(self, tmp_path):
        """Create a test server instance."""
        db_path = tmp_path / "test.db"
        return WaveServer(str(db_path))

    def test_server_initialization(self, server):
        """Test server initializes with database."""
        assert server.db_path.endswith("test.db")
        # Check that tables were created
        cursor = server.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "waves" in tables
        assert "wavelets" in tables
        assert "wavelet_updates" in tables

    def test_create_wave(self, server):
        """Test creating a new wave."""
        wave_id = server.create_wave("test_user@example.com")
        assert wave_id.startswith("localhost!w+")

        # Verify wave was saved to database
        cursor = server.conn.cursor()
        cursor.execute("SELECT creator FROM waves WHERE wave_id = ?", (wave_id,))
        result = cursor.fetchone()
        assert result[0] == "test_user@example.com"

    def test_get_wave(self, server):
        """Test retrieving a wave."""
        wave_id = server.create_wave("test_user@example.com")
        wave = server.get_wave(wave_id)

        assert wave is not None
        assert wave["wave_id"] == wave_id
        assert wave["creator"] == "test_user@example.com"

    def test_create_wavelet(self, server):
        """Test creating a wavelet."""
        wave_id = server.create_wave("test_user@example.com")
        wavelet_id = "localhost!conv+root"

        server.create_wavelet(
            wave_id=wave_id,
            wavelet_id=wavelet_id,
            creator="test_user@example.com",
            participants=["test_user@example.com"],
            docs={"main": {"content": ["Test content"]}},
        )

        # Verify wavelet was saved
        cursor = server.conn.cursor()
        cursor.execute(
            "SELECT creator FROM wavelets WHERE wave_id = ? AND wavelet_id = ?",
            (wave_id, wavelet_id),
        )
        result = cursor.fetchone()
        assert result[0] == "test_user@example.com"

    def test_get_inbox(self, server):
        """Test retrieving user inbox."""
        # Create some waves
        wave1 = server.create_wave("user1@example.com")
        wave2 = server.create_wave("user2@example.com")

        # Add wavelets with our user as participant
        server.create_wavelet(
            wave_id=wave1,
            wavelet_id="localhost!conv+root",
            creator="user1@example.com",
            participants=["user1@example.com", "test@example.com"],
            docs={"main": {"content": ["Wave 1"]}},
        )

        server.create_wavelet(
            wave_id=wave2,
            wavelet_id="localhost!conv+root",
            creator="user2@example.com",
            participants=["user2@example.com", "test@example.com"],
            docs={"main": {"content": ["Wave 2"]}},
        )

        # Get inbox for test user
        inbox = server.get_inbox("test@example.com")
        assert len(inbox) == 2
        wave_ids = {wave["wave_id"] for wave in inbox}
        assert wave1 in wave_ids
        assert wave2 in wave_ids

    def test_update_wavelet(self, server):
        """Test updating a wavelet."""
        wave_id = server.create_wave("test_user@example.com")
        wavelet_id = "localhost!conv+root"

        server.create_wavelet(
            wave_id=wave_id,
            wavelet_id=wavelet_id,
            creator="test_user@example.com",
            participants=["test_user@example.com"],
            docs={"main": {"content": ["Original"]}},
        )

        # Update the wavelet
        new_docs = {"main": {"content": ["Updated"]}}
        server.update_wavelet(wave_id, wavelet_id, docs=new_docs, version=2)

        # Verify update
        cursor = server.conn.cursor()
        cursor.execute(
            "SELECT docs, version FROM wavelets WHERE wave_id = ? AND wavelet_id = ?",
            (wave_id, wavelet_id),
        )
        result = cursor.fetchone()
        docs = json.loads(result[0])
        assert docs["main"]["content"][0] == "Updated"
        assert result[1] == 2

    def test_record_update(self, server):
        """Test recording wavelet updates."""
        wave_id = "test!w+123"
        wavelet_id = "test!conv+root"
        channel_id = 1
        update_data = {"type": "documentOp", "ops": []}

        server.record_update(wave_id, wavelet_id, channel_id, update_data)

        # Verify update was recorded
        cursor = server.conn.cursor()
        cursor.execute(
            "SELECT update_data FROM wavelet_updates WHERE wave_id = ? AND wavelet_id = ?",
            (wave_id, wavelet_id),
        )
        result = cursor.fetchone()
        assert json.loads(result[0]) == update_data


class TestAPI:
    """Test FastAPI endpoints."""

    @pytest.fixture
    def client(self, tmp_path):
        """Create test client."""
        from fastapi.testclient import TestClient

        # Mock the server instance
        with patch("wave_client_server.wave_server.server") as mock_server:
            mock_server.db_path = str(tmp_path / "test.db")
            yield TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_channel_endpoint(self, client):
        """Test browser channel endpoint."""
        response = client.post("/channel", data={"VER": "8", "RID": "rpc", "t": "1"})
        assert response.status_code == 200

    @patch("wave_client_server.wave_server.server.get_inbox")
    def test_get_inbox_endpoint(self, mock_get_inbox, client):
        """Test inbox retrieval endpoint."""
        mock_get_inbox.return_value = [{"wave_id": "test!w+123", "title": "Test Wave"}]

        response = client.get("/api/inbox/user@example.com")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["wave_id"] == "test!w+123"

    @patch("wave_client_server.wave_server.server.create_wave")
    def test_create_wave_endpoint(self, mock_create_wave, client):
        """Test wave creation endpoint."""
        mock_create_wave.return_value = "localhost!w+newwave"

        response = client.post("/api/waves", json={"creator": "user@example.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["wave_id"] == "localhost!w+newwave"
        assert data["creator"] == "user@example.com"
