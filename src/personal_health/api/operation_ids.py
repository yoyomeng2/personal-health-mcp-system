"""Operation ID constants for FastAPI MCP integration."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Operation:
    """Operation metadata for API endpoints."""

    id: str
    allow_mcp: bool = True


class OperationId(Enum):
    """Operation IDs for API endpoints.

    These IDs are used by FastAPI MCP to identify which operations to expose.
    They must match the operation_id parameter in route decorators.
    """

    ADD_ENTRY = Operation("add_entry", allow_mcp=True)
    UPDATE_ENTRY = Operation("update_entry", allow_mcp=True)
    GET_ENTRY = Operation("get_entry", allow_mcp=True)
    GET_ENTRIES = Operation("get_entries", allow_mcp=True)
    EXTRACT_FEATURES = Operation("extract_features", allow_mcp=True)
    GET_SUMMARY = Operation("get_summary", allow_mcp=True)
    GET_PREDICTION = Operation("get_prediction", allow_mcp=True)
    ANALYZE_TRIGGERS = Operation("analyze_triggers", allow_mcp=True)
    GET_USER_PROFILE = Operation("get_user_profile", allow_mcp=True)
    UPDATE_USER_PROFILE = Operation("update_user_profile", allow_mcp=True)
    RESET_DATABASE = Operation("reset_database", allow_mcp=False)

    def __str__(self) -> str:
        """Return the operation ID string for FastAPI compatibility.

        Returns:
            str: The operation ID.
        """
        return self.value.id

    @property
    def operation_id(self) -> str:
        """Get the operation ID string."""
        return self.value.id

    @property
    def allow_mcp(self) -> bool:
        """Check if this operation should be exposed via MCP."""
        return self.value.allow_mcp


def get_mcp_operations() -> list[str]:
    """Get list of operation IDs that should be exposed via MCP."""
    return [op.operation_id for op in OperationId if op.allow_mcp]
