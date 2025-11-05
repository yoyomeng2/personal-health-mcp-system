"""Unit tests for SQLiteDatabase manager."""

from typing import Any

from personal_health.db import Database


class TestSQLiteDatabase:
    """Tests for SQLiteDatabase class."""

    def test_init_creates_parent_directory(self, tmp_path: Any) -> None:
        """Test that __init__ creates parent directory if it doesn't exist."""
        db_path = tmp_path / "nested" / "dir" / "test.db"
        db = Database(db_path)

        assert db.db_path == db_path
        assert db.db_path.parent.exists()
        assert db._initialized is False

    def test_init_applies_migrations(self, db: Database) -> None:
        """Test that init() applies migrations and sets initialized flag."""
        # db fixture already calls init()
        assert db._initialized is True
        assert db.db_path.exists()

    def test_connect_sets_row_factory(self, db: Database) -> None:
        """Test that connect() sets row_factory for dict-like access."""
        with db.connect() as conn:
            # Insert test data
            conn.execute(
                "INSERT INTO entries (id, date, meal, pain_level) VALUES (?, ?, ?, ?)",
                ("test-id", "2024-01-01", "test", 0),
            )
            conn.commit()

            # Query and verify row_factory works
            cursor = conn.execute("SELECT date, meal FROM entries WHERE id = ?", ("test-id",))
            row = cursor.fetchone()
            assert row["date"] == "2024-01-01"
            assert row["meal"] == "test"

    def test_execute_returns_results(self, db: Database) -> None:
        """Test that execute() runs query and returns results."""
        # Insert data
        db.execute(
            "INSERT INTO entries (id, date, meal, pain_level) VALUES (?, ?, ?, ?)",
            ("exec-test", "2024-01-01", "pasta", 2),
        )

        # Query data
        results = db.execute("SELECT * FROM entries WHERE id = ?", ("exec-test",))
        assert len(results) == 1
        assert results[0]["meal"] == "pasta"
        assert results[0]["pain_level"] == 2

    def test_insert_returns_lastrowid(self, db: Database) -> None:
        """Test that insert() returns the lastrowid."""
        last_id = db.insert(
            "INSERT INTO entries (id, date, meal, pain_level) VALUES (?, ?, ?, ?)",
            ("insert-test", "2024-01-01", "pizza", 1),
        )

        assert isinstance(last_id, int)
        assert last_id > 0

        # Verify data was inserted
        results = db.execute("SELECT * FROM entries WHERE id = ?", ("insert-test",))
        assert len(results) == 1
        assert results[0]["meal"] == "pizza"

    def test_update_returns_rowcount(self, db: Database) -> None:
        """Test that update() modifies data and returns rowcount."""
        # Insert initial data
        db.execute(
            "INSERT INTO entries (id, date, meal, pain_level) VALUES (?, ?, ?, ?)",
            ("update-test", "2024-01-01", "salad", 1),
        )

        # Update data
        rowcount = db.update(
            table="entries",
            set_clause={"meal": "soup", "pain_level": 3},
            where_clause="id = ?",
            where_params=("update-test",),
        )

        assert rowcount == 1

        # Verify update
        results = db.execute("SELECT * FROM entries WHERE id = ?", ("update-test",))
        assert results[0]["meal"] == "soup"
        assert results[0]["pain_level"] == 3
