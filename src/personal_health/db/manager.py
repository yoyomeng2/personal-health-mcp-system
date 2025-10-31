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
        """Initialize database schema."""
        schema_path = Path(__file__).resolve().parent / "schema.sql"
        try:
            with open(schema_path) as f:
                schema = f.read()

            with self.connect() as conn:
                conn.executescript(schema)
                conn.commit()
                self._initialized = True
                logger.info(f"Database initialized: {self.db_path}")
        except FileNotFoundError as e:
            raise DatabaseError(f"Schema file not found: {schema_path}") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

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
