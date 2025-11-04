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

    Uses FastAPI's dependency override to inject test database.
    """
    from personal_health.api.dependencies import get_db, get_user_profile_repo

    app = create_app()

    # Create test user profile repository
    test_repo = UserProfileRepository(db)

    # Override FastAPI dependencies to use test database
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_user_profile_repo] = lambda: test_repo

    # so that pydantic validation errors are returned as 422 Unprocessable Entity and don't kill pytest
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()
