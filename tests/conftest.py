"""Test configuration and fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_health.core import create_app
from personal_health.db import Database


@pytest.fixture
def sample_entry() -> dict:
    """Sample health entry for tests."""
    return {
        "date": "2025-10-24",
        "meal": "tacos",
        "alcohol": "beer",
        "stress": 4,
        "sleep_hours": 7.5,
        "pain_level": 2,
        "notes": "test entry",
    }


@pytest.fixture
def temp_db() -> Generator[Database, None, None]:
    """Create a temporary in-memory test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_health.db"
        db = Database(db_path=db_path)
        db.init()
        yield db


@pytest.fixture
def client(temp_db: Database) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with a temporary database.

    Patches the routes module to use the test database instead of the
    production database.
    """
    app = create_app()
    # Replace the global database instance in the routes module
    from personal_health.api import routes

    routes.db = temp_db
    yield TestClient(app)
