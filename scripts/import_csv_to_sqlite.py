#!/usr/bin/env python3
"""CSV -> SQLite importer for the personal_health project.

Usage (from repo root):
  uv run python -m src.personal_health.scripts.csv_to_sqlite --csv health_db_entries_export.csv --db data/health.db --backup

Features:
- Reads and executes `src/personal_health/db/schema.sql` to ensure the `entries` table exists.
- Parses CSV rows and converts numeric fields (stress, sleep_hours, pain_level).
- Skips duplicate ids by default; use --replace to replace existing rows.
- Optionally backups the target DB before writing.

This script uses only the Python stdlib.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import shutil
import sqlite3
from collections.abc import Iterable

from personal_health.utils import generate_entry_id

SCRIPT_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
SCHEMA_PATH = os.path.join(ROOT_DIR, "src", "personal_health", "db", "schema.sql")


def _to_int(val: str) -> int | None:
    """Convert a string to int or return None for empty/'none' values."""
    val = val.strip()
    if val == "" or val.lower() == "none":
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


def _to_float(val: str) -> float | None:
    """Convert a string to float or return None for empty/'none' values."""
    val = val.strip()
    if val == "" or val.lower() == "none":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def read_schema(schema_path: str) -> str:
    with open(schema_path, encoding="utf-8") as f:
        return f.read()


def parse_row(row: list[str]) -> tuple:
    """Map CSV row values to the table columns in order:
    id,date,meal,alcohol,stress,sleep_hours,pain_level,notes,created_at
    """
    # Expecting exactly 9 columns
    if len(row) < 9:
        # pad missing columns with empty strings
        row = row + [""] * (9 - len(row))

    id_, date, meal, alcohol, stress, sleep_hours, pain_level, notes, created_at = row[:9]

    stress_i = _to_int(stress)
    sleep_f = _to_float(sleep_hours)
    pain_i = _to_int(pain_level)

    # created_at fallback
    created_at = created_at.strip() or datetime.datetime.now().isoformat(sep=" ")

    # Note: CSV may include an id column but importer will generate its own id.
    return (
        id_.strip(),
        date.strip(),
        meal.strip(),
        alcohol.strip(),
        stress_i,
        sleep_f,
        pain_i,
        notes.strip(),
        created_at,
    )


def iter_csv_rows(csv_path: str) -> Iterable[tuple]:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        # consume header
        next(reader, None)
        for row in reader:
            yield parse_row(row)


def ensure_schema(conn: sqlite3.Connection, schema_sql: str) -> None:
    conn.executescript(schema_sql)


def insert_rows(
    conn: sqlite3.Connection, rows: Iterable[tuple], upsert: bool = True
) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    if upsert:
        stmt = (
            "INSERT INTO entries (id,date,meal,alcohol,stress,sleep_hours,pain_level,notes,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "date=excluded.date, meal=excluded.meal, alcohol=excluded.alcohol, "
            "stress=excluded.stress, sleep_hours=excluded.sleep_hours, "
            "pain_level=excluded.pain_level, notes=excluded.notes"
        )
    else:
        stmt = (
            "INSERT OR IGNORE INTO entries (id,date,meal,alcohol,stress,sleep_hours,pain_level,notes,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)"
        )

    cur = conn.cursor()
    batch: list[tuple] = []
    for r in rows:
        # r is (csv_id, date, meal, alcohol, stress, sleep_hours, pain_level, notes, created_at)
        _, date, meal, alcohol, stress, sleep_hours, pain_level, notes, created_at = r
        # Generate deterministic id using the same fields as add_entry (exclude created_at)
        values_for_id = [date, meal, alcohol, stress, sleep_hours, pain_level, notes]
        entry_id = generate_entry_id(values_for_id)

        batch.append(
            (entry_id, date, meal, alcohol, stress, sleep_hours, pain_level, notes, created_at)
        )
        if len(batch) >= 500:
            cur.executemany(stmt, batch)
            # sqlite3.Cursor.rowcount may be -1 for some executemany; approximate by batch size
            inserted += (
                max(cur.rowcount, 0)
                if cur.rowcount is not None and cur.rowcount >= 0
                else len(batch)
            )
            batch.clear()
    if batch:
        cur.executemany(stmt, batch)
        inserted += (
            max(cur.rowcount, 0) if cur.rowcount is not None and cur.rowcount >= 0 else len(batch)
        )

    conn.commit()
    return inserted, skipped


def backup_db(db_path: str) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import CSV into SQLite using project schema")
    parser.add_argument("--csv", required=True, help="Path to CSV file to import")
    parser.add_argument("--db", required=True, help="Path to sqlite DB file to write")
    parser.add_argument("--schema", default=SCHEMA_PATH, help="Path to schema.sql to execute")
    parser.add_argument(
        "--backup", action="store_true", help="Backup the existing DB before writing"
    )
    parser.add_argument(
        "--no-upsert", action="store_true", help="Disable upsert and use INSERT OR IGNORE instead"
    )
    args = parser.parse_args(argv)

    csv_path = os.path.abspath(args.csv)
    db_path = os.path.abspath(args.db)

    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        return 2

    if args.backup and os.path.exists(db_path):
        dest = backup_db(db_path)
        print(f"Backed up {db_path} -> {dest}")

    schema_sql = read_schema(args.schema)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn, schema_sql)
        rows = iter_csv_rows(csv_path)
        # Determine upsert behavior: default to upsert; --no-upsert disables it
        upsert = not args.no_upsert
        inserted, skipped = insert_rows(conn, rows, upsert=upsert)
        print(f"Inserted approximately {inserted} rows (skipped {skipped} duplicates).")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
