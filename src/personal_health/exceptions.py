"""Custom exception classes for Personal Health MCP System."""


class PersonalHealthError(Exception):
    """Base exception for all Personal Health errors."""

    pass


class ConfigurationError(PersonalHealthError):
    """Raised when configuration is invalid or missing."""

    pass


class DatabaseError(PersonalHealthError):
    """Raised when database operations fail."""

    pass


class DuplicateEntryError(DatabaseError):
    """Raised when attempting to insert a duplicate entry."""

    pass


class ValidationError(PersonalHealthError):
    """Raised when input validation fails."""

    pass


class ModelError(PersonalHealthError):
    """Raised when model operations fail."""

    pass


class AnalysisError(PersonalHealthError):
    """Raised when analysis operations fail."""

    pass
