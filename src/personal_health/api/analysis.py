"""MCP analysis module for correlations and summaries."""

from datetime import datetime, timedelta
from statistics import mean, median, stdev

from personal_health.api.schemas import MetricStats, SummaryData, SummaryMetrics
from personal_health.logging_config import get_logger
from personal_health.ml.features import LagFeature

logger = get_logger(__name__)


def _compute_metric(values: list[float | int]) -> MetricStats:
    """Compute metrics for a given list of values.

    Args:
        values (list): List of numeric values.

    Returns:
        MetricStats: The computed metrics with avg, min, max, median, std, and count.
    """
    if not values:
        return MetricStats(
            avg=None,
            min=None,
            max=None,
            median=None,
            std=None,
            count=0,
        )

    # Calculate standard deviation (requires at least 2 values)
    std_value = None
    if len(values) >= 2:
        std_value = float(round(stdev(values), 2))

    return MetricStats(
        avg=float(round(mean(values), 2)),
        min=min(values),
        max=max(values),
        median=float(round(median(values), 2)),
        std=std_value,
        count=len(values),
    )


def compute_summary(entries: list[dict], window_days: int = 7) -> SummaryData:
    """Compute summary statistics for entries within a time window.

    Args:
        entries (list[dict]): List of entry dictionaries. Each entry should include
            the keys "date" (ISO YYYY-MM-DD), and optionally numeric fields
            "stress", "sleep_hours", and "pain_level".
        window_days (int, optional): Number of days (ending today) to include
            in the summary. Defaults to 7.

    Returns:
        SummaryData: Pydantic model with count, window_days, and metrics.
    """
    if not entries:
        return _get_empty_summary(window_days)

    # Filter entries by date window
    cutoff_date = (datetime.now() - timedelta(days=window_days)).date()
    filtered_entries = []

    for e in entries:
        try:
            entry_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
            if entry_date >= cutoff_date:
                filtered_entries.append(e)
        except (ValueError, KeyError) as err:
            entry_id = e.get("id", "unknown")
            logger.warning(
                f"Skipping entry with malformed or missing date: id={entry_id}, date={e.get('date', 'N/A')} - {err}"
            )
            continue

    if not filtered_entries:
        return _get_empty_summary(window_days)

    # Extract numeric values, filtering out None
    stress_values = [
        e[LagFeature.STRESS.value]
        for e in filtered_entries
        if e.get(LagFeature.STRESS.value) is not None
    ]
    sleep_values = [
        e[LagFeature.SLEEP_HOURS.value]
        for e in filtered_entries
        if e.get(LagFeature.SLEEP_HOURS.value) is not None
    ]
    pain_values = [
        e[LagFeature.PAIN_LEVEL.value]
        for e in filtered_entries
        if e.get(LagFeature.PAIN_LEVEL.value) is not None
    ]

    return SummaryData(
        count=len(filtered_entries),
        window_days=window_days,
        metrics=SummaryMetrics(
            stress=_compute_metric(stress_values),
            sleep_hours=_compute_metric(sleep_values),
            pain_level=_compute_metric(pain_values),
        ),
    )


def compute_correlations(entries: list) -> dict:
    """Compute correlations between health variables.

    Args:
        entries: List of health entries.

    Returns:
        Correlation matrix.
    """
    return {"status": "not implemented"}


def _get_empty_summary(window_days: int = 7) -> SummaryData:
    """Return empty summary structure.

    Args:
        window_days (int, optional): Number of days for the window. Defaults to 7.

    Returns:
        SummaryData: Empty summary with all metrics set to None/0.
    """
    empty_metric = MetricStats(avg=None, min=None, max=None, median=None, std=None, count=0)

    return SummaryData(
        count=0,
        window_days=window_days,
        metrics=SummaryMetrics(
            stress=empty_metric,
            sleep_hours=empty_metric,
            pain_level=empty_metric,
        ),
    )
