"""Unit tests for analysis module."""

from datetime import datetime, timedelta
from typing import Any

from personal_health.api.analysis import compute_summary


class TestComputeSummary:
    """Tests for compute_summary function."""

    def test_empty_entries_returns_empty_summary(self) -> None:
        """Test that empty entries list returns empty summary."""
        result = compute_summary([]).model_dump()
        assert result["count"] == 0
        assert result["window_days"] == 7
        assert result["metrics"]["stress"]["avg"] is None
        assert result["metrics"]["stress"]["min"] is None
        assert result["metrics"]["stress"]["max"] is None
        assert result["metrics"]["stress"]["median"] is None
        assert result["metrics"]["stress"]["std"] is None
        assert result["metrics"]["stress"]["count"] == 0

    def test_single_entry_summary(self) -> None:
        """Test summary with a single entry."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {
                "date": today,
                "meal": "pizza",
                "alcohol": "wine",
                "stress": 5,
                "sleep_hours": 8,
                "pain_level": 2,
                "notes": "test",
            }
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["count"] == 1
        assert result["metrics"]["stress"]["avg"] == 5
        assert result["metrics"]["stress"]["min"] == 5
        assert result["metrics"]["stress"]["max"] == 5
        assert result["metrics"]["sleep_hours"]["avg"] == 8
        assert result["metrics"]["pain_level"]["avg"] == 2

    def test_multiple_entries_average(self) -> None:
        """Test that average is computed correctly across multiple entries."""
        today = datetime.now()
        entries: list[dict[str, Any]] = [
            {
                "date": (today - timedelta(days=i)).strftime("%Y-%m-%d"),
                "meal": "food",
                "alcohol": "drink",
                "stress": i + 1,  # 1, 2, 3
                "sleep_hours": 7 + i,  # 7, 8, 9
                "pain_level": 1,
                "notes": "test",
            }
            for i in range(3)
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["count"] == 3
        assert result["metrics"]["stress"]["avg"] == 2.0
        assert result["metrics"]["stress"]["min"] == 1
        assert result["metrics"]["stress"]["max"] == 3
        assert result["metrics"]["sleep_hours"]["avg"] == 8.0
        assert result["metrics"]["sleep_hours"]["min"] == 7
        assert result["metrics"]["sleep_hours"]["max"] == 9

    def test_window_days_filter(self) -> None:
        """Test that entries outside window are filtered."""
        today = datetime.now()
        entries: list[dict[str, Any]] = [
            {
                "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
                "stress": 3,
                "sleep_hours": 8,
                "pain_level": 1,
            },
            {
                "date": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
                "stress": 9,  # Outside 7-day window
                "sleep_hours": 5,
                "pain_level": 5,
            },
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        # Only the first entry should be included
        assert result["count"] == 1
        assert result["metrics"]["stress"]["avg"] == 3

    def test_missing_numeric_fields_ignored(self) -> None:
        """Test that missing numeric fields are ignored."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"date": today, "stress": 5, "sleep_hours": None, "pain_level": 2},
            {"date": today, "stress": None, "sleep_hours": 8, "pain_level": 1},
            {"date": today, "stress": 4, "sleep_hours": 7, "pain_level": None},
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["count"] == 3
        # Stress: 5, 4 (avg 4.5)
        assert result["metrics"]["stress"]["avg"] == 4.5
        assert result["metrics"]["stress"]["count"] == 2
        # Sleep: 8, 7 (avg 7.5)
        assert result["metrics"]["sleep_hours"]["avg"] == 7.5
        assert result["metrics"]["sleep_hours"]["count"] == 2
        # Pain: 2, 1 (avg 1.5)
        assert result["metrics"]["pain_level"]["avg"] == 1.5
        assert result["metrics"]["pain_level"]["count"] == 2

    def test_all_entries_outside_window(self) -> None:
        """Test when all entries are outside the window."""
        today = datetime.now()
        entries: list[dict[str, Any]] = [
            {
                "date": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
                "stress": 5,
                "sleep_hours": 8,
                "pain_level": 2,
            }
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["count"] == 0
        assert result["metrics"]["stress"]["avg"] is None

    def test_summary_structure(self) -> None:
        """Test that summary has expected structure."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"date": today, "stress": 5, "sleep_hours": 8, "pain_level": 2}
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert "count" in result
        assert "window_days" in result
        assert "metrics" in result
        assert set(result["metrics"].keys()) == {"stress", "sleep_hours", "pain_level"}
        for metric in result["metrics"].values():
            assert set(metric.keys()) == {
                "avg",
                "min",
                "max",
                "median",
                "std",
                "count",
            }

    def test_zero_values_in_metrics(self) -> None:
        """Test that zero values are handled correctly."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"date": today, "stress": 0, "sleep_hours": 0, "pain_level": 0}
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["metrics"]["stress"]["avg"] == 0
        assert result["metrics"]["sleep_hours"]["avg"] == 0
        assert result["metrics"]["pain_level"]["avg"] == 0

    def test_rounding_to_two_decimals(self) -> None:
        """Test that averages are rounded to 2 decimal places."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"date": today, "stress": 1},
            {"date": today, "stress": 2},
            {"date": today, "stress": 3},
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        # (1 + 2 + 3) / 3 = 2.0
        assert result["metrics"]["stress"]["avg"] == 2.0
        assert isinstance(result["metrics"]["stress"]["avg"], float)

    def test_median_calculation(self) -> None:
        """Test that median is calculated correctly."""
        today = datetime.now().strftime("%Y-%m-%d")
        # Odd number of values: [1, 2, 3] -> median = 2
        entries: list[dict[str, Any]] = [
            {"date": today, "stress": 1, "sleep_hours": 7.0, "pain_level": 1},
            {"date": today, "stress": 2, "sleep_hours": 8.0, "pain_level": 2},
            {"date": today, "stress": 3, "sleep_hours": 9.0, "pain_level": 3},
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["metrics"]["stress"]["median"] == 2.0
        assert result["metrics"]["sleep_hours"]["median"] == 8.0
        assert result["metrics"]["pain_level"]["median"] == 2.0

    def test_median_even_count(self) -> None:
        """Test median with even number of values."""
        today = datetime.now().strftime("%Y-%m-%d")
        # Even number of values: [1, 2, 3, 4] -> median = 2.5
        entries: list[dict[str, Any]] = [
            {"date": today, "pain_level": 1},
            {"date": today, "pain_level": 2},
            {"date": today, "pain_level": 3},
            {"date": today, "pain_level": 4},
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["metrics"]["pain_level"]["median"] == 2.5

    def test_std_deviation_calculation(self) -> None:
        """Test that standard deviation is calculated correctly."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"date": today, "stress": 2},
            {"date": today, "stress": 4},
            {"date": today, "stress": 6},
            {"date": today, "stress": 8},
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        # std([2, 4, 6, 8]) ≈ 2.58
        assert result["metrics"]["stress"]["std"] is not None
        assert 2.0 <= result["metrics"]["stress"]["std"] <= 3.0

    def test_std_single_value_is_none(self) -> None:
        """Test that std is None for single value (requires at least 2)."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [{"date": today, "stress": 5}]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["metrics"]["stress"]["std"] is None

    def test_malformed_date_skipped_with_warning(self, caplog: Any) -> None:
        """Test that entries with malformed dates are skipped."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"date": "invalid-date", "stress": 5},  # Bad date
            {"date": today, "stress": 3},  # Good date
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        # Only the valid entry should be counted
        assert result["count"] == 1
        assert result["metrics"]["stress"]["avg"] == 3.0
        # Check warning was logged
        assert "malformed or missing date" in caplog.text.lower()

    def test_missing_date_field_skipped(self, caplog: Any) -> None:
        """Test that entries without date field are skipped."""
        today = datetime.now().strftime("%Y-%m-%d")
        entries: list[dict[str, Any]] = [
            {"stress": 5},  # No date field
            {"date": today, "stress": 3},
        ]
        result = compute_summary(entries, window_days=7).model_dump()
        assert result["count"] == 1
        assert "malformed or missing date" in caplog.text.lower()
