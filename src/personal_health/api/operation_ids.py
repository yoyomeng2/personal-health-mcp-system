"""Operation ID constants for FastAPI MCP integration."""

from enum import Enum


class OperationId(str, Enum):
    """Operation IDs for API endpoints.

    These IDs are used by FastAPI MCP to identify which operations to expose.
    They must match the operation_id parameter in route decorators.
    """

    ADD_ENTRY = "add_entry"
    UPDATE_ENTRY = "update_entry"
    GET_ENTRY = "get_entry"
    GET_ENTRIES = "get_entries"
    GET_SUMMARY = "get_summary"
    GET_PREDICTION = "get_prediction"
    ANALYZE_TRIGGERS = "analyze_triggers"
    RESET_DATABASE = "reset_database"
