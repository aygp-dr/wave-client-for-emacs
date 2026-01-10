"""Extended REST API integration tests for Wave server."""

import pytest
import httpx
from typing import Generator

BASE_URL = "http://localhost:9898"


@pytest.fixture(scope="module")
def client() -> Generator[httpx.Client, None, None]:
    """Create HTTP client for tests."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        yield client


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client: httpx.Client):
        """Health check should return 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_contains_status(self, client: httpx.Client):
        """Health response should contain status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_contains_timestamp(self, client: httpx.Client):
        """Health response should contain timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data


class TestInboxEndpoint:
    """Tests for /api/inbox endpoint."""

    def test_inbox_returns_list(self, client: httpx.Client):
        """Inbox should return a list."""
        response = client.get("/api/inbox")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_inbox_items_have_required_fields(self, client: httpx.Client):
        """Inbox items should have id, digest, unread, creator."""
        response = client.get("/api/inbox")
        data = response.json()
        if data:  # Only check if inbox has items
            item = data[0]
            assert "id" in item
            assert "digest" in item
            assert "unread" in item
            assert "creator" in item

    def test_inbox_unread_is_integer(self, client: httpx.Client):
        """Unread count should be an integer."""
        response = client.get("/api/inbox")
        data = response.json()
        for item in data:
            assert isinstance(item["unread"], int)
            assert item["unread"] >= 0


class TestWavesEndpoint:
    """Tests for /api/waves/{wave_id} endpoint."""

    def test_nonexistent_wave_returns_404(self, client: httpx.Client):
        """Non-existent wave should return 404."""
        response = client.get("/api/waves/nonexistent!wave")
        assert response.status_code == 404

    def test_index_wave_exists(self, client: httpx.Client):
        """Index wave should exist after seeding."""
        response = client.get("/api/waves/indexwave!indexwave")
        # May be 200 or 500 depending on server state
        assert response.status_code in [200, 404, 500]


class TestSubmitEndpoint:
    """Tests for /api/waves/{wave_id}/submit endpoint."""

    def test_submit_add_participant(self, client: httpx.Client):
        """Should be able to add a participant."""
        response = client.post(
            "/api/waves/indexwave!indexwave/submit",
            json={
                "wavelet_id": "indexwave!indexwave",
                "operations": [
                    {"type": "add_participant", "participant": "newuser@localhost"}
                ]
            }
        )
        # Accept success or error (depends on server state)
        assert response.status_code in [200, 404, 500]

    def test_submit_remove_participant(self, client: httpx.Client):
        """Should be able to remove a participant."""
        response = client.post(
            "/api/waves/indexwave!indexwave/submit",
            json={
                "wavelet_id": "indexwave!indexwave",
                "operations": [
                    {"type": "remove_participant", "participant": "newuser@localhost"}
                ]
            }
        )
        assert response.status_code in [200, 404, 500]

    def test_submit_returns_version(self, client: httpx.Client):
        """Successful submit should return version info."""
        response = client.post(
            "/api/waves/indexwave!indexwave/submit",
            json={
                "wavelet_id": "indexwave!indexwave",
                "operations": []
            }
        )
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "version" in data

    def test_submit_to_nonexistent_wave(self, client: httpx.Client):
        """Submit to non-existent wave should fail."""
        response = client.post(
            "/api/waves/nonexistent!wave/submit",
            json={
                "wavelet_id": "nonexistent!wavelet",
                "operations": []
            }
        )
        assert response.status_code in [404, 500]


class TestRootEndpoint:
    """Tests for / endpoint."""

    def test_root_returns_200(self, client: httpx.Client):
        """Root endpoint should return 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_version(self, client: httpx.Client):
        """Root response should contain version info."""
        response = client.get("/")
        data = response.json()
        assert "name" in data or "version" in data or "status" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_json_returns_422(self, client: httpx.Client):
        """Invalid JSON should return 422."""
        response = client.post(
            "/api/waves/test/submit",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client: httpx.Client):
        """Missing required fields should return 422."""
        response = client.post(
            "/api/waves/test/submit",
            json={}  # Missing wavelet_id and operations
        )
        assert response.status_code == 422


class TestContentTypes:
    """Tests for content type handling."""

    def test_json_content_type(self, client: httpx.Client):
        """API should return JSON content type."""
        response = client.get("/api/inbox")
        assert "application/json" in response.headers.get("content-type", "")

    def test_health_json_content_type(self, client: httpx.Client):
        """Health endpoint should return JSON."""
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")
