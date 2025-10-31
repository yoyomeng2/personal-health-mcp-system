"""MCP utilities for data parsing and validation."""

import hashlib
import json

from personal_health.logging_config import get_logger

logger = get_logger(__name__)


def generate_entry_id(values: list) -> str:
    """Generate deterministic ID from ordered list of values.

    Args:
        values (list): Ordered list of values to hash (e.g., [date, meal, stress, ...]).
                       Order matters - caller must maintain consistent field order.

    Returns:
        str: 16-character hex hash.
    """
    # Normalize None to empty string for consistent hashing
    normalized = [v if v is not None else "" for v in values]
    payload = json.dumps(normalized, sort_keys=False)  # Preserve order
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def parse_and_validate_entry(data: dict) -> dict:
    """Parse and validate entry data.

    Args:
        data: Raw entry data.

    Returns:
        Validated entry data.
    """
    # Basic validation - extend as needed
    return data
