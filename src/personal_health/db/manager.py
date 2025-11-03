"""Database manager for Personal Health MCP System."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from personal_health.exceptions import DatabaseError, DuplicateEntryError
from personal_health.logging_config import get_logger

logger = get_logger(__name__)


class SQLiteDatabase:
    """SQLite database manager."""

    def __init__(self, db_path: Path | str = "data/health.db") -> None:
        """Initialize database connection.

        Args:
            db_path (Path | str): Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    def init(self) -> None:
        """Initialize database schema and apply pending migrations."""
        self._apply_pending_migrations()
        self._initialized = True
        logger.info(f"Database ready: {self.db_path}")

    def _apply_pending_migrations(self) -> None:
        """Apply pending migrations from the migrations/ directory.

        The initial schema is migration 000_initial_schema.sql and runs first.
        All migrations are tracked in the _migrations table to prevent re-execution.
        """
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        if not migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return

        migration_files = sorted(migrations_dir.glob("*.sql"))
        if not migration_files:
            logger.debug("No migration files found")
            return

        with self.connect() as conn:
            cursor = conn.cursor()

            # Create migrations tracking table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT UNIQUE NOT NULL,
                    executed_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.commit()

            for migration_file in migration_files:
                migration_name = migration_file.name

                # Check if migration already ran
                cursor.execute(
                    "SELECT 1 FROM _migrations WHERE migration_name = ?", (migration_name,)
                )
                if cursor.fetchone():
                    logger.debug(f"Migration already applied: {migration_name}")
                    continue

                # Run migration
                try:
                    logger.info(f"Applying migration: {migration_name}")
                    cursor.executescript(migration_file.read_text())

                    cursor.execute(
                        "INSERT INTO _migrations (migration_name) VALUES (?)",
                        (migration_name,),
                    )
                    conn.commit()
                    logger.info(f"Migration completed: {migration_name}")

                except sqlite3.Error as e:
                    logger.error(f"Migration failed: {migration_name}")
                    conn.rollback()
                    raise DatabaseError(f"Failed to apply migration {migration_name}: {e}") from e

    @contextmanager
    def connect(self) -> Any:
        """Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection.

        Raises:
            DatabaseError: If connection fails.
        """
        try:
            if not self._initialized and self.db_path.exists():
                self._initialized = True
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        except sqlite3.Error as e:
            raise DatabaseError(f"Database connection error: {e}") from e

    def execute(self, query: str, params: tuple | None = None) -> Any:
        """Execute a query and return results.

        Args:
            query (str): SQL query string.
            params (tuple, optional): Query parameters.

        Returns:
            Any: Query results.

        Raises:
            DatabaseError: If query execution fails.
            DuplicateEntryError: If INSERT violates PRIMARY KEY constraint.
        """
        with self.connect() as conn:
            cur = conn.cursor()
            try:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                conn.commit()
                result = cur.fetchall()
                return result
            except sqlite3.IntegrityError as e:
                # Check if it's a PRIMARY KEY constraint violation
                if "UNIQUE constraint failed" in str(e) or "PRIMARY KEY" in str(e):
                    raise DuplicateEntryError(f"Duplicate entry: {e}") from e
                raise DatabaseError(f"Integrity constraint violation: {e}") from e
            except sqlite3.Error as e:
                raise DatabaseError(f"Query execution error: {e}") from e

    def insert(self, query: str, params: tuple) -> int:
        """Insert data into database.

        Args:
            query (str): SQL INSERT query.
            params (tuple): Query parameters.

        Returns:
            int: ID of inserted row.

        Raises:
            DatabaseError: If insert fails.
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                last_id = cur.lastrowid
                if last_id is None:
                    raise DatabaseError("Insert did not return a lastrowid")
                return int(last_id)
        except sqlite3.Error as e:
            raise DatabaseError(f"Insert error: {e}") from e
