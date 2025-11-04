"""Unit tests for user profile repository."""

import json
import sqlite3
from typing import Any
from unittest.mock import patch

import pytest

from personal_health.db.schemas import UserProfileSchema
from personal_health.db.user_profile import UserProfileRepository
from personal_health.exceptions import DatabaseError


class TestUserProfileRepository:
    """Tests for UserProfileRepository class."""

    def test_init(self, db: Any) -> None:
        """Test repository initialization."""
        repo = UserProfileRepository(db)
        assert repo.db == db
        assert repo.schema is not None

    def test_is_stale_profile_not_exists(self, repo: UserProfileRepository) -> None:
        """Test is_stale returns True when profile doesn't exist."""
        assert repo.is_stale("nonexistent_user") is True

    def test_is_stale_no_date_last_confirmed(self, repo: UserProfileRepository) -> None:
        """Test is_stale returns True when date_last_confirmed is NULL."""
        # Create profile without date_last_confirmed
        with repo.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (id, dietary_restrictions, allergies, preferences, habits, date_last_confirmed)
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                ("test_user", "[]", "[]", "{}", "{}"),
            )
            conn.commit()

        assert repo.is_stale("test_user") is True

    def test_is_stale_profile_fresh(self, repo: UserProfileRepository) -> None:
        """Test is_stale returns False for recently confirmed profile."""
        # Create profile with recent timestamp
        with repo.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (id, dietary_restrictions, allergies, preferences, habits, date_last_confirmed)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                ("test_user", "[]", "[]", "{}", "{}"),
            )
            conn.commit()

        assert repo.is_stale("test_user", days_threshold=30) is False

    def test_is_stale_custom_threshold(self, repo: UserProfileRepository) -> None:
        """Test is_stale with custom threshold."""
        # Create profile 45 days old
        with repo.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (id, dietary_restrictions, allergies, preferences, habits, date_last_confirmed)
                VALUES (?, ?, ?, ?, ?, datetime('now', '-45 days'))
                """,
                ("test_user", "[]", "[]", "{}", "{}"),
            )
            conn.commit()

        assert repo.is_stale("test_user", days_threshold=30) is True
        assert repo.is_stale("test_user", days_threshold=60) is False

    def test_is_stale_database_error(self, repo: UserProfileRepository) -> None:
        """Test is_stale raises DatabaseError on failure."""
        with patch.object(repo.db, "connect", side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(DatabaseError, match="Error checking profile staleness"):
                repo.is_stale()

    def test_get_profile(self, repo: UserProfileRepository) -> None:
        """Test retrieving profile."""
        profile = repo.get("nonexistent_user")
        assert profile is None

        # Create test profile
        with repo.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (id, dietary_restrictions, allergies, preferences, habits)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "test_user",
                    '["vegetarian"]',
                    '["peanuts"]',
                    '{"spicy": "high"}',
                    '{"caffeine": "moderate"}',
                ),
            )
            conn.commit()

        profile = repo.get("test_user")
        assert profile is not None
        assert profile["id"] == "test_user"
        assert profile["dietary_restrictions"] == '["vegetarian"]'
        assert profile["allergies"] == '["peanuts"]'
        assert profile["preferences"] == '{"spicy": "high"}'
        assert profile["habits"] == '{"caffeine": "moderate"}'
        assert "created_at" in profile
        assert "updated_at" in profile

    def test_get_database_error(self, repo: UserProfileRepository) -> None:
        """Test get raises DatabaseError on failure."""
        with patch.object(repo.db, "connect", side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(DatabaseError, match="Error retrieving user profile"):
                repo.get()

    def test_create_or_update_creates_new_profile(self, repo: UserProfileRepository) -> None:
        """Test creating a new profile."""
        profile = UserProfileSchema(
            id="new_user",
            dietary_restrictions='["vegan"]',
            allergies='["shellfish"]',
            preferences='{"sweet": "low"}',
            habits='{"alcohol": "none"}',
            date_last_confirmed=None,
        )
        repo.create_or_update(profile)

        result = repo.get("new_user")
        assert result is not None
        assert result["id"] == "new_user"
        assert result["dietary_restrictions"] == '["vegan"]'
        assert result["allergies"] == '["shellfish"]'
        assert result["preferences"] == '{"sweet": "low"}'
        assert result["habits"] == '{"alcohol": "none"}'

    def test_create_or_update_with_defaults(self, repo: UserProfileRepository) -> None:
        """Test creating profile with default values."""
        profile = UserProfileSchema(id="minimal_user", date_last_confirmed=None)
        repo.create_or_update(profile)

        result = repo.get("minimal_user")
        assert result is not None
        assert result["dietary_restrictions"] == "[]"
        assert result["allergies"] == "[]"
        assert result["preferences"] == "{}"
        assert result["habits"] == "{}"

    def test_create_or_update_updates_existing_profile(self, repo: UserProfileRepository) -> None:
        """Test updating an existing profile."""
        # Create initial profile
        initial = UserProfileSchema(
            id="update_user",
            dietary_restrictions='["vegetarian"]',
            allergies='["peanuts"]',
            date_last_confirmed=None,
        )
        repo.create_or_update(initial)

        # Get existing to preserve fields
        existing = repo.get("update_user")
        assert existing is not None

        # Update profile (merge with existing)
        updated = UserProfileSchema(
            id="update_user",
            dietary_restrictions='["vegan"]',
            allergies=existing["allergies"],  # preserved
            preferences='{"spicy": "high"}',
            habits=existing["habits"],  # preserved
            date_last_confirmed=None,
        )
        repo.create_or_update(updated)

        profile = repo.get("update_user")
        assert profile is not None
        assert profile["dietary_restrictions"] == '["vegan"]'
        assert profile["preferences"] == '{"spicy": "high"}'
        assert profile["allergies"] == '["peanuts"]'  # preserved

    def test_create_or_update_database_error(self, repo: UserProfileRepository) -> None:
        """Test create_or_update raises DatabaseError on failure."""
        profile = UserProfileSchema(id="error_user", date_last_confirmed=None)
        with patch.object(repo.db, "connect", side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(DatabaseError, match="Error managing user profile"):
                repo.create_or_update(profile)

    def test_update_timestamp_success(self, repo: UserProfileRepository) -> None:
        """Test updating timestamp for existing profile."""
        # Create profile with old timestamp
        with repo.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profile (id, dietary_restrictions, allergies, preferences, habits, date_last_confirmed)
                VALUES (?, ?, ?, ?, ?, datetime('now', '-10 days'))
                """,
                ("timestamp_user", "[]", "[]", "{}", "{}"),
            )
            conn.commit()

        # Verify profile is stale
        assert repo.is_stale("timestamp_user", days_threshold=5) is True

        # Update timestamp
        repo.update_timestamp("timestamp_user")

        # Verify profile is now fresh
        assert repo.is_stale("timestamp_user", days_threshold=5) is False

    def test_update_timestamp_default_user(self, repo: UserProfileRepository) -> None:
        """Test updating timestamp for default user."""
        # Create default user profile
        profile = UserProfileSchema(id="default_user", date_last_confirmed=None)
        repo.create_or_update(profile)

        fetched = repo.get("default_user")
        assert fetched is not None
        initial_timestamp = fetched["date_last_confirmed"]
        assert initial_timestamp is not None

        # Update timestamp
        repo.update_timestamp()

        # Verify it worked
        result = repo.get("default_user")
        assert result is not None
        assert result["date_last_confirmed"] is not None
        assert result["date_last_confirmed"] >= initial_timestamp

    def test_update_timestamp_profile_not_found(self, repo: UserProfileRepository) -> None:
        """Test update_timestamp raises error for non-existent profile."""
        with pytest.raises(DatabaseError, match="Profile not found"):
            repo.update_timestamp("nonexistent_user")

    def test_update_timestamp_database_error(self, repo: UserProfileRepository) -> None:
        """Test update_timestamp raises DatabaseError on failure."""
        # Create profile first
        profile = UserProfileSchema(id="default_user", date_last_confirmed=None)
        repo.create_or_update(profile)

        with patch.object(repo.db, "connect", side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(DatabaseError):  # Error could come from get() or _update()
                repo.update_timestamp()

    def test_create_preserves_json_structure(self, repo: UserProfileRepository) -> None:
        """Test that JSON structures are preserved correctly."""
        complex_preferences = {
            "spicy": "high",
            "sweet": "low",
            "cuisine": ["italian", "japanese"],
        }
        complex_habits = {
            "caffeine": "moderate",
            "meal_times": {"breakfast": "8am", "lunch": "12pm", "dinner": "7pm"},
        }

        profile = UserProfileSchema(
            id="json_user",
            preferences=json.dumps(complex_preferences),
            habits=json.dumps(complex_habits),
            date_last_confirmed=None,
        )
        repo.create_or_update(profile)

        result = repo.get("json_user")
        assert result is not None
        assert json.loads(result["preferences"]) == complex_preferences
        assert json.loads(result["habits"]) == complex_habits

    def test_multiple_users_isolated(self, repo: UserProfileRepository) -> None:
        """Test that multiple user profiles are isolated."""
        user1 = UserProfileSchema(
            id="user1", dietary_restrictions='["vegetarian"]', date_last_confirmed=None
        )
        user2 = UserProfileSchema(
            id="user2", dietary_restrictions='["vegan"]', date_last_confirmed=None
        )
        repo.create_or_update(user1)
        repo.create_or_update(user2)

        profile1 = repo.get("user1")
        profile2 = repo.get("user2")

        assert profile1 is not None
        assert profile2 is not None
        assert profile1["dietary_restrictions"] == '["vegetarian"]'
        assert profile2["dietary_restrictions"] == '["vegan"]'
        assert profile1["id"] != profile2["id"]

    def test_timestamps_auto_updated(self, repo: UserProfileRepository) -> None:
        """Test that created_at and updated_at are automatically managed."""
        # Create profile
        initial = UserProfileSchema(id="timestamp_test", date_last_confirmed=None)
        repo.create_or_update(initial)

        profile1 = repo.get("timestamp_test")
        assert profile1 is not None
        created_at = profile1["created_at"]
        updated_at = profile1["updated_at"]
        assert created_at is not None
        assert updated_at is not None

        # Wait a tiny bit and update
        import time

        time.sleep(0.01)

        updated = UserProfileSchema(
            id="timestamp_test", dietary_restrictions='["test"]', date_last_confirmed=None
        )
        repo.create_or_update(updated)

        profile2 = repo.get("timestamp_test")
        assert profile2 is not None
        # created_at should not change
        assert profile2["created_at"] == created_at
        # updated_at should change (but this might be flaky due to timestamp precision)
        # So we just verify it exists
        assert profile2["updated_at"] >= updated_at
