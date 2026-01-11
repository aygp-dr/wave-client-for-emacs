"""HTTP API integration tests using the .http files."""

from pathlib import Path

import httpx
import pytest

HTTP_TEST_DIR = Path(__file__).parent.parent / "http"
BASE_URL = "http://localhost:9898"


class TestHTTPAPI:
    """Test HTTP API using the .http file definitions."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create HTTP client."""
        return httpx.Client(base_url=BASE_URL)

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_create_wave(self, client):
        """Test wave creation."""
        response = client.post("/api/waves", json={"creator": "test@localhost"})
        assert response.status_code == 200
        data = response.json()
        assert "wave_id" in data
        assert data["creator"] == "test@localhost"
        return data["wave_id"]

    def test_get_inbox(self, client):
        """Test inbox retrieval."""
        response = client.get("/api/inbox/test@localhost")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_wave_lifecycle(self, client):
        """Test complete wave lifecycle."""
        # Create wave
        create_response = client.post("/api/waves", json={"creator": "test@localhost"})
        wave_id = create_response.json()["wave_id"]

        # Get wave
        get_response = client.get(f"/api/waves/{wave_id}")
        assert get_response.status_code == 200

        # Create wavelet
        wavelet_response = client.post(
            f"/api/waves/{wave_id}/wavelets",
            json={
                "wavelet_id": "localhost!conv+root",
                "creator": "test@localhost",
                "participants": ["test@localhost"],
                "docs": {"main": {"content": ["Test"]}},
            },
        )
        assert wavelet_response.status_code == 200

        # Update wavelet
        update_response = client.put(
            f"/api/waves/{wave_id}/wavelets/localhost!conv+root",
            json={"version": 2, "docs": {"main": {"content": ["Updated"]}}},
        )
        assert update_response.status_code == 200
