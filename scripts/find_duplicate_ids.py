#!/usr/bin/env python3
"""Find duplicate entries and show which IDs to delete."""

import sqlite3
from pathlib import Path

from personal_health.utils import generate_entry_id


def find_duplicates() -> None:
    """Find duplicate entries and compute correct IDs."""
    db_path = Path(__file__).parent.parent / "data" / "health.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Get all entries
        cursor.execute(
            """
            SELECT id, date, meal, alcohol, stress, sleep_hours, pain_level, notes
            FROM entries
            ORDER BY date, created_at
            """
        )

        entries = cursor.fetchall()
        seen = {}
        duplicates = []

        for row in entries:
            current_id, date, meal, alcohol, stress, sleep_hours, pain_level, notes = row

            # Generate the correct ID using the same logic as add_entry
            values = [date, meal, alcohol, stress, sleep_hours, pain_level, notes]
            correct_id = generate_entry_id(values)

            key = (date, meal, alcohol, stress, sleep_hours, pain_level, notes)

            if key in seen:
                # This is a duplicate
                duplicates.append(
                    {
                        "current_id": current_id,
                        "correct_id": correct_id,
                        "should_delete": current_id != correct_id,
                        "date": date,
                        "meal": meal,
                    }
                )
            else:
                seen[key] = {
                    "current_id": current_id,
                    "correct_id": correct_id,
                    "should_delete": current_id != correct_id,
                    "date": date,
                    "meal": meal,
                }

    # Print results
    print("\n=== Entries with Wrong IDs (not duplicates, just wrong ID) ===")
    wrong_ids = [entry for entry in seen.values() if entry["should_delete"]]
    if wrong_ids:
        for entry in wrong_ids:
            print(f"Date: {entry['date']}")
            print(f"  Current ID: {entry['current_id']}")
            print(f"  Correct ID: {entry['correct_id']}")
            print()
    else:
        print("None found")

    print("\n=== Duplicate Entries to Delete ===")
    if duplicates:
        print("\n=== DELETE STATEMENTS ===")
        for dup in duplicates:
            print(f"DELETE FROM entries WHERE id = '{dup['current_id']}';")
    else:
        print("None found")

    print(f"\nTotal duplicates to delete: {len(duplicates)}")


if __name__ == "__main__":
    find_duplicates()
