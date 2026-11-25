"""The spec must be where restish discovers it, and say what restish needs."""

from fastapi.testclient import TestClient

from wave_client_server._version import __version__
from wave_client_server.wave_server import app

client = TestClient(app)


def test_openapi_served_at_root_and_under_api():
    root = client.get("/openapi.json")
    legacy = client.get("/api/openapi.json")  # /docs reads this one
    assert root.status_code == legacy.status_code == 200
    assert root.json() == legacy.json()


def test_spec_has_servers_and_readable_operation_ids():
    spec = client.get("/openapi.json").json()
    assert spec["servers"][0]["url"]
    operation_ids = {op["operationId"] for path in spec["paths"].values() for op in path.values()}
    assert {"root", "health_check", "get_inbox", "get_wave", "submit_delta"} <= operation_ids
    assert "/openapi.json" not in spec["paths"]


def test_version_is_single_sourced():
    assert client.get("/").json()["version"] == __version__
    assert client.get("/openapi.json").json()["info"]["version"] == __version__
