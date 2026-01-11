"""Wave Client Server - Mock server for Wave client integration testing."""

from .wave_server import app

__all__ = ["app"]


def main() -> None:
    import uvicorn

    uvicorn.run(
        "wave_client_server.wave_server:app", host="0.0.0.0", port=9898, reload=True
    )
