"""Test configuration and fixtures."""

import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_health.core import create_app
from personal_health.db import Database
from personal_health.db.user_profile import UserProfileRepository


@pytest.fixture
def sample_entry() -> dict:
    """Sample health entry for tests."""
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "meal": "tacos",
        "alcohol": "beer",
        "stress": 4,
        "sleep_hours": 7.5,
        "pain_level": 2,
        "notes": "test entry",
    }


@pytest.fixture
def db() -> Generator[Database, None, None]:
    """Create a temporary in-memory test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_health.db"
        db = Database(db_path=db_path)
        db.init()
        yield db


@pytest.fixture
def repo(db: Database) -> UserProfileRepository:
    """Create a UserProfileRepository instance with test database."""
    return UserProfileRepository(db)


@pytest.fixture
def client(db: Database) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with a temporary database.

    Patches the routes module to use the test database instead of the
    production database.
    """
    app = create_app()
    # Replace the global database instance in the routes module
    from personal_health.api import routes

    routes.db = db
    routes.user_profile_repo = routes.UserProfileRepository(db)

    # so that pydantic validation errors are returned as 422 Unprocessable Entity and don't kill pytest
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
