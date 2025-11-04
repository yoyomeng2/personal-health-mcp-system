"""FastAPI dependency injection for shared resources."""

from typing import Annotated

from fastapi import Depends

from personal_health.db import Database, UserProfileRepository
from personal_health.logging_config import get_logger

logger = get_logger(__name__)

# Global instances (initialized once by init_dependencies)
_db: Database | None = None
_user_profile_repo: UserProfileRepository | None = None


def init_dependencies(db_path: str) -> None:
    """Initialize global dependencies.

    Called once during application startup by create_app().

    Args:
        db_path (str): Path to the database file.
    """
    global _db, _user_profile_repo

    logger.info(f"Initializing database: {db_path}")

    _db = Database(db_path)
    _db.init()

    _user_profile_repo = UserProfileRepository(_db)
    logger.info("Dependencies initialized")


def get_db() -> Database:
    """FastAPI dependency to get the Database instance.

    Returns:
        Database: Configured database instance.

    Raises:
        RuntimeError: If dependencies not initialized.
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_dependencies() first.")
    return _db


def get_user_profile_repo() -> UserProfileRepository:
    """FastAPI dependency to get the UserProfileRepository instance.

    Returns:
        UserProfileRepository: User profile repository instance.

    Raises:
        RuntimeError: If dependencies not initialized.
    """
    if _user_profile_repo is None:
        raise RuntimeError("UserProfileRepository not initialized. Call init_dependencies() first.")
    return _user_profile_repo


# Type aliases for dependency injection
DatabaseDep = Annotated[Database, Depends(get_db)]
UserProfileRepoDep = Annotated[UserProfileRepository, Depends(get_user_profile_repo)]
