"""CSV export utility for health entries.

This script exports health entries to CSV format for exploratory data analysis (EDA).
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from personal_health.db import Database
from personal_health.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def export_to_csv(
    output_path: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Export health entries to CSV file.

    Args:
        output_path (str): Path to output CSV file.
        start_date (str, optional): Filter entries on or after this date (YYYY-MM-DD).
        end_date (str, optional): Filter entries on or before this date (YYYY-MM-DD).

    Raises:
        ValueError: If date formats are invalid.
    """
    # Initialize logging
    setup_logging()

    # Validate date formats
    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid start_date format. Expected YYYY-MM-DD, got: {start_date}"
            ) from e

    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid end_date format. Expected YYYY-MM-DD, got: {end_date}"
            ) from e

    # Build query
    db = Database()
    query = "SELECT * FROM entries"
    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY date ASC"

    logger.info(f"Executing query: {query}")
    logger.info(f"Parameters: {params}")

    # Fetch entries
    rows = db.execute(query, tuple(params) if params else ())

    if not rows:
        logger.warning("No entries found matching criteria")
        return

    # Write to CSV
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "date",
        "meal",
        "alcohol",
        "stress",
        "sleep_hours",
        "pain_level",
        "notes",
        "created_at",
    ]

    with output_file.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow(fieldnames)

        # Write rows
        writer.writerows(rows)

    logger.info(f"Exported {len(rows)} entries to {output_path}")
    print(f"✓ Exported {len(rows)} entries to {output_path}")


def main() -> None:
    """CLI entrypoint for CSV export."""
    parser = argparse.ArgumentParser(
        description="Export health entries to CSV for exploratory data analysis"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="data/health_export.csv",
        help="Output CSV file path (default: data/health_export.csv)",
    )
    parser.add_argument(
        "-s",
        "--start-date",
        help="Filter entries on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-e",
        "--end-date",
        help="Filter entries on or before this date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    try:
        export_to_csv(
            output_path=args.output,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    except ValueError as e:
        print(f"✗ Validation Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
