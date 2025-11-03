"""User profile database operations."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

from personal_health.db.schemas import UserProfileSchema
from personal_health.exceptions import DatabaseError
from personal_health.logging_config import get_logger

if TYPE_CHECKING:
    from personal_health.db.manager import SQLiteDatabase

logger = get_logger(__name__)


class UserProfileRepository:
    """Repository for user profile database operations."""

    def __init__(self, db: SQLiteDatabase) -> None:
        """Initialize repository with database instance.

        Args:
            db (SQLiteDatabase): Database instance.
        """
        self.db = db
        self.schema = UserProfileSchema

    def is_stale(self, user_id: str = "default_user", days_threshold: int = 30) -> bool:
        """Check if user profile needs to be refreshed (older than threshold).

        Args:
            user_id (str): User ID. Defaults to 'default_user'.
            days_threshold (int): Number of days before profile is considered stale.
                Defaults to 30.

        Returns:
            bool: True if profile is stale or doesn't exist, False otherwise.

        Raises:
            DatabaseError: If query fails.
        """
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT date_last_confirmed FROM user_profile
                    WHERE id = ?
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return True

                last_updated = row[0]
                if not last_updated:
                    return True

                # Check if older than threshold
                cur.execute(
                    """
                    SELECT (julianday('now') - julianday(?)) > ?
                    """,
                    (last_updated, days_threshold),
                )
                result = cur.fetchone()
                return bool(result[0])
        except sqlite3.Error as e:
            raise DatabaseError(f"Error checking profile staleness: {e}") from e

    def get(self, user_id: str = "default_user") -> dict[str, Any] | None:
        """Retrieve user profile by ID.

        Args:
            user_id (str): User ID. Defaults to 'default_user'.

        Returns:
            dict: User profile data or None if not found.

        Raises:
            DatabaseError: If query fails.
        """
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, dietary_restrictions, allergies, preferences, habits,
                           created_at, updated_at, date_last_confirmed
                    FROM user_profile
                    WHERE id = ?
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return dict(row)
        except sqlite3.Error as e:
            raise DatabaseError(f"Error retrieving user profile: {e}") from e

    def create_or_update(
        self,
        user_id: str = "default_user",
        dietary_restrictions: str | None = None,
        allergies: str | None = None,
        preferences: str | None = None,
        habits: str | None = None,
    ) -> None:
        """Create or update user profile.

        Args:
            user_id (str): User ID. Defaults to 'default_user'.
            dietary_restrictions (str, optional): JSON array of restrictions.
            allergies (str, optional): JSON array of allergies.
            preferences (str, optional): JSON object of preferences.
            habits (str, optional): JSON object of habits.

        Raises:
            DatabaseError: If insert/update fails.
        """
        try:
            # Create model instance with provided data and defaults
            schema = self.schema(
                id=user_id,
                dietary_restrictions=dietary_restrictions or "[]",
                allergies=allergies or "[]",
                preferences=preferences or "{}",
                habits=habits or "{}",
                date_last_confirmed=None,
            )

            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM user_profile WHERE id = ?", (user_id,))
                exists = cur.fetchone() is not None

            if exists:
                self._update(
                    schema,
                    update_only_provided=dietary_restrictions is not None
                    or allergies is not None
                    or preferences is not None
                    or habits is not None,
                )
            else:
                self._create(schema)

            logger.info(f"User profile {'updated' if exists else 'created'}: {user_id}")
        except sqlite3.Error as e:
            raise DatabaseError(f"Error managing user profile: {e}") from e

    def update_timestamp(self, user_id: str = "default_user") -> None:
        """Update the date_last_confirmed timestamp for a user profile.

        Args:
            user_id (str): User ID. Defaults to 'default_user'.

        Raises:
            DatabaseError: If update fails or profile not found.
        """
        try:
            # Get existing profile to preserve current data
            profile_data = self.get(user_id)
            if not profile_data:
                raise DatabaseError(f"Profile not found for user {user_id}")

            # Just pass in the ID and update timestamp
            schema = UserProfileSchema(
                id=profile_data["id"],
                date_last_confirmed=None,
            )

            self._update(schema)
        except sqlite3.Error as e:
            raise DatabaseError(f"Error updating profile timestamp: {e}") from e

    def _update(
        self,
        schema: UserProfileSchema,
        update_only_provided: bool = True,
    ) -> None:
        """Update existing profile.

        Args:
            profile (UserProfileModel): User profile model instance.
            update_only_provided (bool): If True, only update fields that were explicitly
                provided. If False, update all fields from the model.
        """
        # Get all data fields except timestamps
        data = schema.model_dump(exclude={"created_at", "updated_at", "date_last_confirmed", "id"})

        # Build update data - always update timestamps
        update_data = {
            "updated_at": "datetime('now')",
            "date_last_confirmed": "datetime('now')",
        }

        # Add data fields
        update_data.update(data)

        # Generate SQL dynamically from model fields
        set_parts = []
        params = []
        for col, val in update_data.items():
            if val == "datetime('now')":
                # Special handling for datetime functions
                set_parts.append(f"{col} = datetime('now')")
            else:
                set_parts.append(f"{col} = ?")
                params.append(val)

        params.append(schema.id)
        query = f"UPDATE user_profile SET {', '.join(set_parts)} WHERE id = ?"

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(query, params)

    def _create(
        self,
        schema: UserProfileSchema,
    ) -> None:
        """Create new profile.

        Args:
            schema (UserProfileModel): User profile schema instance.
        """
        # Get all fields except timestamps (handled by database defaults)
        data = schema.model_dump(exclude={"created_at", "updated_at", "date_last_confirmed"})
        columns = list(data.keys())
        values = list(data.values())

        # Add timestamp columns with database functions
        columns.extend(["created_at", "updated_at", "date_last_confirmed"])
        placeholders = ["?"] * len(values) + ["datetime('now')"] * 3

        query = f"""
            INSERT INTO user_profile ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
        """

        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute(query, tuple(values))
