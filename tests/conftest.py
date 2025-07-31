"""Pytest configuration and fixtures."""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to Python path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_db():
    """Provide a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_wave_data():
    """Provide sample wave data for tests."""
    return {
        "wave_id": "localhost!w+test123",
        "creator": "test@localhost",
        "wavelets": [
            {
                "wavelet_id": "localhost!conv+root",
                "creator": "test@localhost",
                "participants": ["test@localhost", "other@localhost"],
                "version": 1,
                "docs": {
                    "main": {
                        "docId": "main",
                        "contributors": ["test@localhost"],
                        "content": ["Hello, World!"]
                    }
                }
            }
        ]
    }


@pytest.fixture
def mock_inbox_data():
    """Provide sample inbox data for tests."""
    return [
        {
            "wave_id": "localhost!w+wave1",
            "title": "Test Wave 1",
            "snippet": "This is a test wave",
            "unread": 2,
            "last_modified": "2024-01-01T12:00:00"
        },
        {
            "wave_id": "localhost!w+wave2", 
            "title": "Test Wave 2",
            "snippet": "Another test wave",
            "unread": 0,
            "last_modified": "2024-01-01T11:00:00"
        }
    ]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # If we had any singleton patterns, we'd reset them here
    yield